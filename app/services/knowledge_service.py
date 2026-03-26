"""Knowledge base service — document ingestion, chunking, embedding, search."""

import uuid
from datetime import datetime, timezone

import structlog
from sqlalchemy import select, text, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.knowledge import Chunk, KnowledgeDoc
from app.repositories.base import BaseRepository

logger = structlog.get_logger()


class KnowledgeDocRepository(BaseRepository[KnowledgeDoc]):
    model = KnowledgeDoc


class ChunkRepository(BaseRepository[Chunk]):
    model = Chunk

    async def vector_search(
        self,
        embedding: list[float],
        brand_id: uuid.UUID,
        limit: int = 10,
    ) -> list[dict]:
        """Search chunks by cosine similarity using pgvector."""
        embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"
        stmt = text("""
            SELECT c.id, c.content, c.section_title, c.document_id,
                   d.title as doc_title,
                   1 - (c.embedding <=> :embedding::vector) as score
            FROM chunks c
            JOIN knowledge_docs d ON c.document_id = d.id
            WHERE c.tenant_id = :tenant_id
              AND d.brand_id = :brand_id
              AND d.status = 'indexed'
              AND c.embedding IS NOT NULL
            ORDER BY c.embedding <=> :embedding::vector
            LIMIT :limit
        """)
        result = await self.session.execute(
            stmt,
            {
                "embedding": embedding_str,
                "tenant_id": str(self.tenant_id),
                "brand_id": str(brand_id),
                "limit": limit,
            },
        )
        rows = result.fetchall()
        return [
            {
                "chunk_id": row.id,
                "content": row.content,
                "section_title": row.section_title,
                "document_id": row.document_id,
                "document_title": row.doc_title,
                "score": float(row.score),
            }
            for row in rows
        ]

    async def keyword_search(
        self,
        query: str,
        brand_id: uuid.UUID,
        limit: int = 10,
    ) -> list[dict]:
        """Full-text search using PostgreSQL tsvector."""
        stmt = text("""
            SELECT c.id, c.content, c.section_title, c.document_id,
                   d.title as doc_title,
                   ts_rank(to_tsvector('french', c.content),
                           plainto_tsquery('french', :query)) as score
            FROM chunks c
            JOIN knowledge_docs d ON c.document_id = d.id
            WHERE c.tenant_id = :tenant_id
              AND d.brand_id = :brand_id
              AND d.status = 'indexed'
              AND to_tsvector('french', c.content) @@ plainto_tsquery('french', :query)
            ORDER BY score DESC
            LIMIT :limit
        """)
        result = await self.session.execute(
            stmt,
            {
                "query": query,
                "tenant_id": str(self.tenant_id),
                "brand_id": str(brand_id),
                "limit": limit,
            },
        )
        rows = result.fetchall()
        return [
            {
                "chunk_id": row.id,
                "content": row.content,
                "section_title": row.section_title,
                "document_id": row.document_id,
                "document_title": row.doc_title,
                "score": float(row.score),
            }
            for row in rows
        ]


class KnowledgeService:
    """Manages document lifecycle and RAG search."""

    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID):
        self.session = session
        self.tenant_id = tenant_id
        self.doc_repo = KnowledgeDocRepository(session, tenant_id)
        self.chunk_repo = ChunkRepository(session, tenant_id)

    # === Document Management ===

    async def create_document(
        self,
        *,
        brand_id: uuid.UUID,
        title: str,
        doc_type: str,
        uploaded_by: uuid.UUID,
        raw_content: str | None = None,
        source_url: str | None = None,
        file_url: str | None = None,
        language: str = "fr",
        metadata: dict | None = None,
    ) -> KnowledgeDoc:
        doc = await self.doc_repo.create(
            brand_id=brand_id,
            title=title,
            doc_type=doc_type,
            uploaded_by=uploaded_by,
            raw_content=raw_content,
            source_url=source_url,
            file_url=file_url,
            language=language,
            status="pending",
            metadata_=metadata or {},
        )
        logger.info(
            "document_created",
            doc_id=str(doc.id),
            brand_id=str(brand_id),
            doc_type=doc_type,
        )
        return doc

    async def get_document(self, doc_id: uuid.UUID) -> KnowledgeDoc:
        doc = await self.doc_repo.get_by_id(doc_id)
        if not doc:
            raise NotFoundError("Document not found")
        return doc

    async def list_documents(
        self, brand_id: uuid.UUID | None = None, **kwargs
    ) -> list[KnowledgeDoc]:
        filters = {}
        if brand_id:
            filters["brand_id"] = brand_id
        return await self.doc_repo.list(**filters, **kwargs)

    async def mark_document_indexed(
        self, doc_id: uuid.UUID, chunk_count: int
    ) -> None:
        await self.doc_repo.update(
            doc_id, status="indexed", chunk_count=chunk_count
        )

    async def mark_document_failed(
        self, doc_id: uuid.UUID, error: str
    ) -> None:
        doc = await self.doc_repo.get_by_id(doc_id)
        if doc:
            metadata = dict(doc.metadata_)
            metadata["error"] = error
            await self.doc_repo.update(doc_id, status="failed", metadata_=metadata)

    # === Search ===

    async def search(
        self,
        query: str,
        brand_id: uuid.UUID,
        top_k: int = 5,
        min_score: float = 0.3,
        embedding_fn=None,
    ) -> list[dict]:
        """Hybrid search: vector + keyword with Reciprocal Rank Fusion."""
        results = []

        # Vector search (if embedding function provided)
        vector_results = []
        if embedding_fn:
            query_embedding = await embedding_fn(query)
            vector_results = await self.chunk_repo.vector_search(
                embedding=query_embedding,
                brand_id=brand_id,
                limit=top_k * 2,
            )

        # Keyword search (always available)
        keyword_results = await self.chunk_repo.keyword_search(
            query=query,
            brand_id=brand_id,
            limit=top_k * 2,
        )

        if vector_results and keyword_results:
            # Hybrid merge via Reciprocal Rank Fusion
            results = self._reciprocal_rank_fusion(
                vector_results, keyword_results
            )
        elif vector_results:
            results = vector_results
        else:
            results = keyword_results

        # Filter by minimum score
        results = [r for r in results if r["score"] >= min_score]

        return results[:top_k]

    @staticmethod
    def _reciprocal_rank_fusion(
        *result_lists: list[dict], k: int = 60
    ) -> list[dict]:
        """Merge ranked lists using RRF: score = sum(1/(k+rank))."""
        scores: dict[str, dict] = {}

        for results in result_lists:
            for rank, result in enumerate(results):
                doc_id = str(result["chunk_id"])
                if doc_id not in scores:
                    scores[doc_id] = {"result": result, "score": 0.0}
                scores[doc_id]["score"] += 1.0 / (k + rank + 1)

        sorted_items = sorted(
            scores.values(), key=lambda x: x["score"], reverse=True
        )
        for item in sorted_items:
            item["result"]["score"] = item["score"]
        return [item["result"] for item in sorted_items]
