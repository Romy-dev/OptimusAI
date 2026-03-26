"""Feature flag model — toggle features per tenant or globally."""

import uuid

from sqlalchemy import Boolean, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class FeatureFlag(Base, TimestampMixin):
    """A feature flag that can be toggled globally or per-tenant."""

    __tablename__ = "feature_flags"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    enabled_globally: Mapped[bool] = mapped_column(Boolean, default=False)
    enabled_tenants: Mapped[list | None] = mapped_column(JSONB, default=list)  # list of tenant_id strings
    disabled_tenants: Mapped[list | None] = mapped_column(JSONB, default=list)  # override: disabled even if global
