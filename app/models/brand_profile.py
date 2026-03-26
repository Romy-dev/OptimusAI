"""Extended brand profile — the data that makes AI sound like the business.

Separated from Brand to keep the core model clean.
This holds the detailed personality, rules, and examples that agents use.
"""

import uuid

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TenantMixin, TimestampMixin


class BrandProfile(Base, TenantMixin, TimestampMixin):
    """Deep brand configuration for AI agents."""
    __tablename__ = "brand_profiles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    brand_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("brands.id", ondelete="CASCADE"),
        unique=True, nullable=False,
    )

    # === Voice & Tone ===
    # Default tone + per-channel overrides
    default_tone: Mapped[str] = mapped_column(String(50), default="professional")
    # "professional", "friendly", "casual", "inspiring", "formal", "humorous"
    tone_by_channel: Mapped[dict] = mapped_column(JSONB, default=dict)
    # {"facebook": "friendly", "whatsapp": "casual", "instagram": "inspiring"}
    tone_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Free text: "Nous tutoyons nos clients, on utilise des emojis modérément..."

    # === Language ===
    primary_language: Mapped[str] = mapped_column(String(10), default="fr")
    secondary_languages: Mapped[list] = mapped_column(JSONB, default=list)
    # ["en", "moore", "dioula"]
    language_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    # "Utiliser le français standard, éviter l'argot parisien, OK pour les expressions locales"

    # === Products & Services ===
    products: Mapped[list] = mapped_column(JSONB, default=list)
    # [{"name": "Tissu Wax", "description": "...", "price": "3500 FCFA/m", "category": "textile"}]
    services: Mapped[list] = mapped_column(JSONB, default=list)
    # [{"name": "Livraison", "description": "...", "zones": ["Ouaga", "Bobo"]}]

    # === Response Rules ===
    greeting_style: Mapped[str | None] = mapped_column(Text, nullable=True)
    # "Toujours commencer par 'Bonjour' ou 'Bonsoir' selon l'heure"
    closing_style: Mapped[str | None] = mapped_column(Text, nullable=True)
    # "Terminer par 'Merci de votre confiance' ou 'Belle journée'"
    response_rules: Mapped[list] = mapped_column(JSONB, default=list)
    # [
    #   {"trigger": "prix", "rule": "Toujours donner le prix exact si disponible"},
    #   {"trigger": "livraison", "rule": "Mentionner le délai de 24-48h"},
    #   {"trigger": "réclamation", "rule": "S'excuser d'abord, proposer une solution"}
    # ]

    # === Forbidden Content ===
    banned_words: Mapped[list] = mapped_column(JSONB, default=list)
    # ["concurrent_name", "pas cher", "le meilleur"]
    banned_topics: Mapped[list] = mapped_column(JSONB, default=list)
    # ["politique", "religion", "concurrents"]
    sensitive_topics: Mapped[list] = mapped_column(JSONB, default=list)
    # ["remboursement", "retour produit"] — these trigger escalation, not blocking

    # === Visual Identity ===
    logo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    colors: Mapped[dict] = mapped_column(JSONB, default=dict)
    # {"primary": "#FF5733", "secondary": "#333", "accent": "#00BCD4"}
    font_style: Mapped[str | None] = mapped_column(String(100), nullable=True)
    image_style: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # "photo réaliste", "illustration flat", "minimaliste", "africain coloré"

    # === Example Content ===
    example_posts: Mapped[list] = mapped_column(JSONB, default=list)
    # [{"channel": "facebook", "content": "...", "approved": true}]
    example_replies: Mapped[list] = mapped_column(JSONB, default=list)
    # [{"scenario": "question prix", "reply": "Le prix est de..."}]
    example_support_responses: Mapped[list] = mapped_column(JSONB, default=list)
    # [{"question": "Horaires?", "response": "Nous sommes ouverts de 8h à 18h..."}]

    # === Business Info ===
    business_hours: Mapped[dict] = mapped_column(JSONB, default=dict)
    # {"monday": {"open": "08:00", "close": "18:00"}, ...}
    locations: Mapped[list] = mapped_column(JSONB, default=list)
    # [{"name": "Boutique principale", "address": "...", "phone": "..."}]
    contact_info: Mapped[dict] = mapped_column(JSONB, default=dict)
    # {"phone": "+226...", "email": "...", "whatsapp": "+226..."}

    # === Channel-specific profiles ===
    channel_profiles: Mapped[dict] = mapped_column(JSONB, default=dict)
    # {
    #   "facebook": {"max_length": 2000, "use_hashtags": false, "emoji_level": "moderate"},
    #   "instagram": {"max_length": 2200, "use_hashtags": true, "hashtag_count": 15},
    #   "whatsapp": {"max_length": 1000, "use_emojis": true, "formal": false},
    # }

    # Relationship
    brand: Mapped["Brand"] = relationship()  # noqa: F821


class ChannelCapability(Base, TenantMixin, TimestampMixin):
    """Tracks what each connected channel can and cannot do.
    Auto-populated when a social account is connected.
    """
    __tablename__ = "channel_capabilities"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    social_account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("social_accounts.id", ondelete="CASCADE"),
        nullable=False,
    )
    platform: Mapped[str] = mapped_column(String(50), nullable=False)
    can_publish_text: Mapped[bool] = mapped_column(default=False)
    can_publish_image: Mapped[bool] = mapped_column(default=False)
    can_publish_video: Mapped[bool] = mapped_column(default=False)
    can_schedule: Mapped[bool] = mapped_column(default=False)
    can_read_comments: Mapped[bool] = mapped_column(default=False)
    can_reply_comments: Mapped[bool] = mapped_column(default=False)
    can_receive_messages: Mapped[bool] = mapped_column(default=False)
    can_send_messages: Mapped[bool] = mapped_column(default=False)
    can_read_analytics: Mapped[bool] = mapped_column(default=False)
    message_window_hours: Mapped[int | None] = mapped_column(nullable=True)
    # 24 for WhatsApp/Messenger/Instagram DM, null for no restriction
    requires_template_outside_window: Mapped[bool] = mapped_column(default=False)
    max_post_length: Mapped[int | None] = mapped_column(nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
