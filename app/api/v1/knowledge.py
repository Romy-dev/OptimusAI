import uuid

from fastapi import APIRouter, Depends, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.database import get_session
from app.core.exceptions import NotFoundError
from app.core.permissions import RequirePermission
from app.core.queue import enqueue
from app.models.user import User
from app.schemas.knowledge import (
    DocumentCreate,
    DocumentResponse,
    KnowledgeSearchRequest,
    KnowledgeSearchResponse,
    SearchResultItem,
    URLDocumentRequest,
)
from app.services.knowledge_service import KnowledgeService
from app.services.quota_service import QuotaService

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


def get_knowledge_service(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> KnowledgeService:
    return KnowledgeService(session, tenant_id=user.tenant_id)


@router.get("/documents", response_model=list[DocumentResponse])
async def list_documents(
    brand_id: uuid.UUID | None = None,
    user: User = Depends(RequirePermission("knowledge.read")),
    service: KnowledgeService = Depends(get_knowledge_service),
):
    return await service.list_documents(brand_id=brand_id)


@router.post("/documents", response_model=DocumentResponse, status_code=201)
async def create_document(
    body: DocumentCreate,
    user: User = Depends(RequirePermission("knowledge.write")),
    service: KnowledgeService = Depends(get_knowledge_service),
    session: AsyncSession = Depends(get_session),
):
    quota = QuotaService(session)
    await quota.enforce_quota(user.tenant_id, "documents")

    doc = await service.create_document(
        brand_id=body.brand_id,
        title=body.title,
        doc_type=body.doc_type,
        uploaded_by=user.id,
        raw_content=body.raw_content,
        source_url=body.source_url,
        language=body.language,
    )

    await quota.record_usage(user.tenant_id, "documents")
    await enqueue("ingest_document", str(doc.id), str(user.tenant_id))

    return doc


@router.post("/documents/from-url", response_model=DocumentResponse, status_code=201)
async def create_from_url(
    body: URLDocumentRequest,
    user: User = Depends(RequirePermission("knowledge.write")),
    service: KnowledgeService = Depends(get_knowledge_service),
    session: AsyncSession = Depends(get_session),
):
    """Scrape a URL and add the content as a knowledge document."""
    from app.core.exceptions import InvalidInputError
    from app.services.url_scraper import scrape_url

    quota = QuotaService(session)
    await quota.enforce_quota(user.tenant_id, "documents")

    try:
        scraped = await scrape_url(body.url)
    except ValueError as e:
        raise InvalidInputError(str(e))

    title = body.title or scraped["title"] or body.url

    doc = await service.create_document(
        brand_id=body.brand_id,
        title=title,
        doc_type="url",
        uploaded_by=user.id,
        raw_content=scraped["content"],
        source_url=body.url,
        language=body.language,
        metadata={
            "scraped_title": scraped["title"],
            "scraped_description": scraped["description"],
        },
    )

    await quota.record_usage(user.tenant_id, "documents")
    await enqueue("ingest_document", str(doc.id), str(user.tenant_id))

    return doc


@router.post("/documents/upload", response_model=DocumentResponse, status_code=201)
async def upload_document(
    brand_id: uuid.UUID = Form(...),
    title: str = Form(...),
    doc_type: str = Form(default="custom"),
    file: UploadFile = File(...),
    user: User = Depends(RequirePermission("knowledge.write")),
    service: KnowledgeService = Depends(get_knowledge_service),
    session: AsyncSession = Depends(get_session),
):
    """Upload a file (PDF, DOCX, TXT, CSV) to the knowledge base."""
    quota = QuotaService(session)
    await quota.enforce_quota(user.tenant_id, "documents")

    file_content = await file.read()

    raw_content = None
    if file.content_type in ("text/plain", "text/csv"):
        raw_content = file_content.decode("utf-8", errors="replace")

    from app.core.storage import storage_service
    file_key = await storage_service.upload_file(
        file_data=file_content,
        filename=file.filename or "unknown",
        content_type=file.content_type or "application/octet-stream",
        folder=f"knowledge/{user.tenant_id}",
    )
    file_url = file_key  # Store key, not full URL — download_file uses key

    doc = await service.create_document(
        brand_id=brand_id,
        title=title,
        doc_type=doc_type,
        uploaded_by=user.id,
        raw_content=raw_content,
        file_url=file_url,
    )

    await quota.record_usage(user.tenant_id, "documents")
    await enqueue("ingest_document", str(doc.id), str(user.tenant_id))

    return doc


@router.get("/documents/{doc_id}", response_model=DocumentResponse)
async def get_document(
    doc_id: uuid.UUID,
    user: User = Depends(RequirePermission("knowledge.read")),
    service: KnowledgeService = Depends(get_knowledge_service),
):
    return await service.get_document(doc_id)


@router.delete("/documents/{doc_id}", status_code=204)
async def delete_document(
    doc_id: uuid.UUID,
    user: User = Depends(RequirePermission("knowledge.delete")),
    service: KnowledgeService = Depends(get_knowledge_service),
):
    await service.get_document(doc_id)  # Verify exists + tenant
    deleted = await service.doc_repo.delete(doc_id)
    if not deleted:
        raise NotFoundError("Document not found")


@router.post("/documents/{doc_id}/reindex", response_model=DocumentResponse)
async def reindex_document(
    doc_id: uuid.UUID,
    user: User = Depends(RequirePermission("knowledge.write")),
    service: KnowledgeService = Depends(get_knowledge_service),
):
    doc = await service.get_document(doc_id)
    await service.doc_repo.update(doc_id, status="pending")
    await enqueue("ingest_document", str(doc.id), str(user.tenant_id))
    return await service.get_document(doc_id)


@router.post("/search", response_model=KnowledgeSearchResponse)
async def search_knowledge(
    body: KnowledgeSearchRequest,
    user: User = Depends(get_current_user),
    service: KnowledgeService = Depends(get_knowledge_service),
):
    # Keyword-only search (embedding is optional, handled in worker)
    results = await service.search(
        query=body.query,
        brand_id=body.brand_id,
        top_k=body.top_k,
        min_score=body.min_score,
        embedding_fn=None,
    )

    return KnowledgeSearchResponse(
        results=[
            SearchResultItem(
                chunk_id=r["chunk_id"],
                document_id=r["document_id"],
                document_title=r["document_title"],
                content=r["content"],
                section_title=r.get("section_title"),
                score=r["score"],
            )
            for r in results
        ],
        query=body.query,
        total=len(results),
    )
