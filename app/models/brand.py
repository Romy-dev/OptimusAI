import uuid

from sqlalchemy import String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TenantMixin, TimestampMixin


class Brand(Base, TenantMixin, TimestampMixin):
    __tablename__ = "brands"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    industry: Mapped[str | None] = mapped_column(String(100), nullable=True)
    logo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    colors: Mapped[dict] = mapped_column(JSONB, default=dict)
    tone: Mapped[str] = mapped_column(String(50), default="professional")
    language: Mapped[str] = mapped_column(String(10), default="fr")
    target_country: Mapped[str] = mapped_column(String(5), default="BF")
    guidelines: Mapped[dict] = mapped_column(JSONB, default=dict)

    tenant: Mapped["Tenant"] = relationship(back_populates="brands")  # noqa: F821
    social_accounts: Mapped[list["SocialAccount"]] = relationship(  # noqa: F821
        back_populates="brand"
    )
    knowledge_docs: Mapped[list["KnowledgeDoc"]] = relationship(  # noqa: F821
        back_populates="brand"
    )
