import uuid

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantMixin, TimestampMixin


class Story(Base, TenantMixin, TimestampMixin):
    """Persisted multi-slide story (Instagram/Facebook/WhatsApp)."""

    __tablename__ = "stories"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    brand_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("brands.id"), nullable=True
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )

    title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    brief: Mapped[str] = mapped_column(Text, nullable=False)
    platform: Mapped[str] = mapped_column(String(30), default="instagram")

    # Plan data
    story_plan: Mapped[dict] = mapped_column(JSONB, default=dict)
    total_slides: Mapped[int] = mapped_column(Integer, default=0)
    total_duration_s: Mapped[int] = mapped_column(Integer, default=0)

    # Rendered slide data
    slide_images: Mapped[list] = mapped_column(JSONB, default=list)

    # Video
    video_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    video_s3_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    video_duration_s: Mapped[int | None] = mapped_column(Integer, nullable=True)
    music_mood: Mapped[str | None] = mapped_column(String(30), nullable=True)

    # Status: draft, planned, rendering, rendered, video_ready, published
    status: Mapped[str] = mapped_column(String(30), default="draft")
