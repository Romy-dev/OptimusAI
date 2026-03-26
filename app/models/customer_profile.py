"""Customer profile model — persistent memory of each customer across conversations."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantMixin, TimestampMixin


class CustomerProfile(Base, TenantMixin, TimestampMixin):
    """Enriched customer profile built from conversation history."""

    __tablename__ = "customer_profiles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    brand_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("brands.id"), nullable=False)

    # Identity
    platform: Mapped[str] = mapped_column(String(50), nullable=False)  # whatsapp, facebook, instagram
    platform_user_id: Mapped[str] = mapped_column(String(255), nullable=False)  # unique on platform
    display_name: Mapped[str] = mapped_column(String(255), default="")
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    language: Mapped[str] = mapped_column(String(10), default="fr")

    # Behavior
    total_conversations: Mapped[int] = mapped_column(Integer, default=0)
    total_messages: Mapped[int] = mapped_column(Integer, default=0)
    first_contact_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_contact_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    avg_response_satisfaction: Mapped[float] = mapped_column(Float, default=0.0)

    # Classification
    segment: Mapped[str] = mapped_column(String(50), default="new")  # new, regular, vip, at_risk, churned
    sentiment_trend: Mapped[str] = mapped_column(String(20), default="neutral")  # positive, neutral, negative
    lifetime_value: Mapped[float] = mapped_column(Float, default=0.0)

    # Interests & preferences
    interests: Mapped[list] = mapped_column(JSONB, default=list)  # ["wax fabric", "accessories"]
    preferred_products: Mapped[list] = mapped_column(JSONB, default=list)  # product IDs or names
    purchase_history: Mapped[list] = mapped_column(JSONB, default=list)  # [{product, date, amount}]
    preferred_contact_time: Mapped[str | None] = mapped_column(String(50), nullable=True)  # "morning", "evening"
    preferred_language: Mapped[str] = mapped_column(String(10), default="fr")

    # Notes & context
    notes: Mapped[list] = mapped_column(JSONB, default=list)  # [{date, note, source}]
    tags: Mapped[list] = mapped_column(JSONB, default=list)  # ["vip", "wholesale", "complaint"]
    last_issue: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_issue_resolved: Mapped[bool] = mapped_column(Boolean, default=True)

    # Follow-up
    next_followup_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    followup_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
