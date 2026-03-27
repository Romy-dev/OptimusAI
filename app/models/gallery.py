import uuid

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantMixin, TimestampMixin


class GeneratedImage(Base, TenantMixin, TimestampMixin):
    """Standalone AI-generated images (gallery)."""

    __tablename__ = "generated_images"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    technical_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_url: Mapped[str] = mapped_column(String(500), nullable=False)
    s3_key: Mapped[str] = mapped_column(String(500), nullable=False)
    aspect_ratio: Mapped[str] = mapped_column(String(10), default="1:1")
    media_type: Mapped[str] = mapped_column(String(20), default="image")  # "image" or "video"
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)
