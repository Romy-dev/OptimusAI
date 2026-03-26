import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class PostCreate(BaseModel):
    brand_id: uuid.UUID
    content_text: str = Field(min_length=1, max_length=5000)
    hashtags: list[str] = Field(default_factory=list)
    target_channels: list[dict] = Field(min_length=1)
    campaign_id: uuid.UUID | None = None
    scheduled_at: datetime | None = None


class PostGenerateRequest(BaseModel):
    brand_id: uuid.UUID
    brief: str = Field(min_length=10, max_length=2000)
    channels: list[str] = Field(min_length=1)
    campaign_id: uuid.UUID | None = None
    generate_image: bool = False
    image_style: str | None = None
    variants_count: int = Field(default=1, ge=1, le=3)
    scheduled_at: datetime | None = None
    language: str = "fr"


class AttachImageRequest(BaseModel):
    image_url: str = Field(min_length=1, max_length=2000)
    s3_key: str | None = Field(default=None, max_length=500)
    prompt: str | None = Field(default=None, max_length=2000)
    metadata: dict = Field(default_factory=dict)


class PostUpdate(BaseModel):
    content_text: str | None = Field(default=None, max_length=5000)
    hashtags: list[str] | None = None
    target_channels: list[dict] | None = None
    scheduled_at: datetime | None = None


class PostAssetResponse(BaseModel):
    id: uuid.UUID
    asset_type: str
    file_url: str
    thumbnail_url: str | None
    alt_text: str | None
    ai_generated: bool

    model_config = {"from_attributes": True}


class PostResponse(BaseModel):
    id: uuid.UUID
    brand_id: uuid.UUID
    content_text: str | None
    hashtags: list[str]
    status: str
    channel_variants: dict
    target_channels: list[dict]
    assets: list[PostAssetResponse] = []
    ai_generated: bool
    ai_confidence_score: float | None
    scheduled_at: datetime | None
    published_at: datetime | None
    created_at: datetime
    created_by: uuid.UUID

    model_config = {"from_attributes": True}
