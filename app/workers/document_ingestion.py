"""Worker: document ingestion pipeline.

Parses documents, chunks them, generates embeddings, stores in pgvector.
Runs as an async ARQ job.
"""

import asyncio
import uuid

import structlog

logger = structlog.get_logger()

CHUNK_SIZE = 512
CHUNK_OVERLAP = 50


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[dict]:
    """Split text into overlapping chunks by paragraph boundaries."""
    if not text or not text.strip():
        return []

    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks = []
    current_chunk = ""
    current_section = None
    chunk_index = 0

    for para in paragraphs:
        if (
            para.endswith(":")
            or para.startswith("#")
            or (len(para) < 100 and para.upper() == para and len(para) > 3)
        ):
            current_section = para.strip("#: ").strip()
            continue

        estimated_tokens = len(current_chunk + " " + para) // 4

        if estimated_tokens > chunk_size and current_chunk:
            chunks.append({
                "content": current_chunk.strip(),
                "index": chunk_index,
                "section_title": current_section,
            })
            chunk_index += 1
            overlap_chars = overlap * 4
            if len(current_chunk) > overlap_chars:
                current_chunk = current_chunk[-overlap_chars:] + " " + para
            else:
                current_chunk = para
        else:
            current_chunk = (current_chunk + "\n\n" + para).strip()

    if current_chunk.strip():
        chunks.append({
            "content": current_chunk.strip(),
            "index": chunk_index,
            "section_title": current_section,
        })

    return chunks


def parse_faq_csv(content: str) -> list[dict]:
    """Parse FAQ-style CSV (question,answer) into chunks."""
    import csv
    import io

    chunks = []
    reader = csv.reader(io.StringIO(content))
    for i, row in enumerate(reader):
        if len(row) >= 2:
            question = row[0].strip()
            answer = row[1].strip()
            if question and answer:
                chunks.append({
                    "content": f"Question: {question}\nRéponse: {answer}",
                    "index": i,
                    "section_title": question,
                })
    return chunks


async def extract_text_from_file(file_key: str, doc_type: str) -> str | None:
    """Extract raw text from an uploaded file stored in S3/MinIO.

    Supports: TXT, CSV, PDF (via pymupdf), DOCX (via python-docx).
    Falls back gracefully if libraries are missing.
    """
    from app.core.storage import storage_service

    try:
        file_data = await storage_service.download_file(file_key)
    except Exception as e:
        logger.error("file_download_failed", key=file_key, error=str(e))
        return None

    # Detect type from key extension or doc_type
    key_lower = file_key.lower()

    # Plain text
    if key_lower.endswith(".txt") or doc_type == "text":
        return file_data.decode("utf-8", errors="replace")

    # CSV
    if key_lower.endswith(".csv") or doc_type == "faq":
        return file_data.decode("utf-8", errors="replace")

    # PDF
    if key_lower.endswith(".pdf") or doc_type == "pdf":
        try:
            import fitz  # pymupdf

            def _extract_pdf():
                doc = fitz.open(stream=file_data, filetype="pdf")
                text_parts = []
                for page in doc:
                    text_parts.append(page.get_text())
                doc.close()
                return "\n\n".join(text_parts)

            return await asyncio.to_thread(_extract_pdf)
        except ImportError:
            logger.warning("pymupdf_not_installed", hint="pip install pymupdf")
            return None

    # DOCX
    if key_lower.endswith(".docx") or doc_type == "docx":
        try:
            import docx
            import io

            def _extract_docx():
                document = docx.Document(io.BytesIO(file_data))
                return "\n\n".join(p.text for p in document.paragraphs if p.text.strip())

            return await asyncio.to_thread(_extract_docx)
        except ImportError:
            logger.warning("python_docx_not_installed", hint="pip install python-docx")
            return None

    logger.warning("unsupported_file_type", key=file_key, doc_type=doc_type)
    return None


async def ingest_document(ctx: dict, doc_id: str, tenant_id: str) -> dict:
    """ARQ task: ingest a document into the knowledge base.

    Pipeline: load → extract text → chunk → embed → store → update status.
    """
    from app.core.database import async_session_factory
    from app.models.knowledge import Chunk, KnowledgeDoc
    from sqlalchemy import select

    doc_uuid = uuid.UUID(doc_id)
    tenant_uuid = uuid.UUID(tenant_id)

    logger.info("ingestion_started", doc_id=doc_id)

    async with async_session_factory() as session:
        try:
            stmt = select(KnowledgeDoc).where(
                KnowledgeDoc.id == doc_uuid,
                KnowledgeDoc.tenant_id == tenant_uuid,
            )
            result = await session.execute(stmt)
            doc = result.scalar_one_or_none()

            if not doc:
                logger.error("document_not_found", doc_id=doc_id)
                return {"status": "error", "reason": "document_not_found"}

            doc.status = "processing"
            await session.commit()

            # Get text content — from raw_content or by extracting from file
            raw_text = doc.raw_content
            if not raw_text and doc.file_url:
                raw_text = await extract_text_from_file(doc.file_url, doc.doc_type)

            if not raw_text:
                doc.status = "failed"
                doc.metadata_ = {**doc.metadata_, "error": "No content to process"}
                await session.commit()
                return {"status": "error", "reason": "no_content"}

            # Chunk
            if doc.doc_type == "faq" and "," in raw_text[:200]:
                chunks_data = parse_faq_csv(raw_text)
            else:
                chunks_data = chunk_text(raw_text)

            if not chunks_data:
                doc.status = "failed"
                doc.metadata_ = {**doc.metadata_, "error": "No chunks produced"}
                await session.commit()
                return {"status": "error", "reason": "no_chunks"}

            # Generate embeddings (best effort)
            embeddings = None
            try:
                from app.integrations.embeddings import get_embedding_service
                embed_service = get_embedding_service()
                texts = [c["content"] for c in chunks_data]
                embeddings = embed_service.embed(texts)
            except Exception as e:
                logger.warning("embedding_skipped", doc_id=doc_id, error=str(e))

            # Store chunks
            for i, chunk_data in enumerate(chunks_data):
                chunk = Chunk(
                    tenant_id=tenant_uuid,
                    document_id=doc_uuid,
                    content=chunk_data["content"],
                    chunk_index=chunk_data["index"],
                    section_title=chunk_data.get("section_title"),
                    token_count=len(chunk_data["content"]) // 4,
                    embedding=embeddings[i] if embeddings else None,
                )
                session.add(chunk)

            doc.status = "indexed"
            doc.chunk_count = len(chunks_data)
            await session.commit()

            logger.info("ingestion_completed", doc_id=doc_id, chunks=len(chunks_data))
            return {"status": "success", "chunks": len(chunks_data)}

        except Exception as e:
            logger.exception("ingestion_failed", doc_id=doc_id)
            try:
                doc.status = "failed"
                doc.metadata_ = {**doc.metadata_, "error": str(e)}
                await session.commit()
            except Exception:
                pass
            return {"status": "error", "reason": str(e)}
