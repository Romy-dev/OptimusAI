"""Chat message model — persistent conversation history with the Concierge."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantMixin, TimestampMixin


class ChatMessage(Base, TenantMixin, TimestampMixin):
    """A message in the Concierge chat."""

    __tablename__ = "chat_messages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    role: Mapped[str] = mapped_column(String(20), nullable=False)  # "user" or "assistant"
    content: Mapped[str] = mapped_column(Text, nullable=False)
    audio_url: Mapped[str | None] = mapped_column(String(500), nullable=True)  # S3 key if voice message

    # Action executed by the concierge
    action_type: Mapped[str | None] = mapped_column(String(50), nullable=True)  # "create_post", "configure_brand", etc.
    action_result: Mapped[dict | None] = mapped_column(JSONB, nullable=True)  # result data
    action_buttons: Mapped[list | None] = mapped_column(JSONB, nullable=True)  # [{label, action, data}]
