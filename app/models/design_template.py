"""Design template model — stores reference posters and their extracted Design DNA."""

import uuid

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantMixin, TimestampMixin


class DesignTemplate(Base, TenantMixin, TimestampMixin):
    """A reference poster/affiche uploaded by the client, with VLM-extracted Design DNA."""

    __tablename__ = "design_templates"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    brand_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("brands.id"), nullable=False)
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # Reference image
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    image_url: Mapped[str] = mapped_column(String(500), nullable=False)
    s3_key: Mapped[str] = mapped_column(String(500), nullable=False)
    thumbnail_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # VLM analysis status
    analysis_status: Mapped[str] = mapped_column(String(20), default="pending")  # pending, analyzing, completed, failed
    analysis_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Extracted Design DNA (structured JSON from VLM)
    design_dna: Mapped[dict] = mapped_column(JSONB, default=dict)
    # {
    #   layout: { type, text_position, alignment, has_border, border_style, margins },
    #   typography: { headline_style, headline_size_ratio, subheadline_style, font_family, letter_spacing },
    #   colors: { dominant, accent, text_primary, text_secondary, overlay_type, overlay_opacity },
    #   elements: { has_logo, logo_position, has_cta, cta_style, has_price_badge, badge_style, decorative[] },
    #   composition: { rule_of_thirds, visual_weight, whitespace_ratio, image_coverage },
    #   mood: str,
    #   industry_match: str,
    # }

    # Aggregated brand DNA (merged from all templates of this brand)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)  # preferred template
    weight: Mapped[float] = mapped_column(Float, default=1.0)  # influence weight in DNA merge


class BrandDesignDNA(Base, TenantMixin, TimestampMixin):
    """Aggregated Design DNA for a brand — merged from all its templates."""

    __tablename__ = "brand_design_dna"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    brand_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("brands.id"), nullable=False, unique=True)

    # Merged DNA from all templates
    merged_dna: Mapped[dict] = mapped_column(JSONB, default=dict)
    template_count: Mapped[int] = mapped_column(Integer, default=0)

    # Extracted font preferences
    preferred_fonts: Mapped[list] = mapped_column(JSONB, default=list)  # ["Montserrat", "Playfair Display"]
    color_palette: Mapped[list] = mapped_column(JSONB, default=list)  # [{hex, role, frequency}]
    layout_preferences: Mapped[list] = mapped_column(JSONB, default=list)  # ["text_bottom", "centered"]
    mood_keywords: Mapped[list] = mapped_column(JSONB, default=list)  # ["elegant", "bold", "minimal"]
