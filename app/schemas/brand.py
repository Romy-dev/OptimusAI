import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class BrandCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    industry: str | None = None
    logo_url: str | None = None
    colors: dict = Field(default_factory=dict)
    tone: str = "professional"
    language: str = "fr"
    target_country: str = "BF"
    guidelines: dict = Field(default_factory=dict)


class BrandUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    description: str | None = None
    industry: str | None = None
    logo_url: str | None = None
    colors: dict | None = None
    tone: str | None = None
    language: str | None = None
    target_country: str | None = None
    guidelines: dict | None = None


class BrandResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    industry: str | None
    logo_url: str | None
    colors: dict
    tone: str
    language: str
    target_country: str
    guidelines: dict
    created_at: datetime

    model_config = {"from_attributes": True}
