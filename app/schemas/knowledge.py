import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class DocumentCreate(BaseModel):
    brand_id: uuid.UUID
    title: str = Field(min_length=1, max_length=500)
    doc_type: str = Field(
        ...,
        pattern="^(faq|product_catalog|policy|guide|webpage|custom)$",
    )
    raw_content: str | None = None
    source_url: str | None = None
    language: str = "fr"


class DocumentResponse(BaseModel):
    id: uuid.UUID
    brand_id: uuid.UUID
    title: str
    doc_type: str
    source_url: str | None
    file_url: str | None
    status: str
    chunk_count: int
    language: str
    created_at: datetime

    model_config = {"from_attributes": True}


class KnowledgeSearchRequest(BaseModel):
    query: str = Field(min_length=2, max_length=1000)
    brand_id: uuid.UUID
    top_k: int = Field(default=5, ge=1, le=20)
    min_score: float = Field(default=0.05, ge=0.0, le=1.0)


class SearchResultItem(BaseModel):
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    document_title: str
    content: str
    section_title: str | None
    score: float


class KnowledgeSearchResponse(BaseModel):
    results: list[SearchResultItem]
    query: str
    total: int
