# OptimusAI — Modèle de Données

## Principes
- **Multi-tenant par défaut** : chaque table a un `tenant_id` (sauf `tenants` et `billing_plans`)
- **Soft delete** : `deleted_at` nullable pour les entités critiques
- **Audit trail** : `created_at`, `updated_at`, `created_by` sur toutes les tables
- **UUID partout** : pas d'ID auto-increment exposé
- **JSONB pour l'extensibilité** : metadata, settings, extra_data

## Schéma Logique (ERD simplifié)

```
tenants ──< users
tenants ──< brands
tenants ──< billing_subscriptions
brands ──< social_accounts
brands ──< knowledge_docs
brands ──< campaigns
social_accounts ──< channels
campaigns ──< posts
posts ──< post_assets
posts ──< comments
comments ──< replies
channels ──< conversations
conversations ──< messages
knowledge_docs ──< chunks
chunks ──< embeddings
posts ──< approvals
conversations ──< escalations
tenants ──< audit_events
tenants ──< analytics_events
tenants ──< agent_runs
tenants ──< workflows
users ──< user_roles
```

---

## SQLAlchemy Models

### Base Model

```python
# app/models/base.py
import uuid
from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class TenantMixin:
    """Mixin that adds tenant_id to all multi-tenant models."""
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )


class TimestampMixin:
    """Mixin for created_at / updated_at."""
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("now()"),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("now()"),
        onupdate=text("now()"),
        nullable=False,
    )


class SoftDeleteMixin:
    """Mixin for soft delete."""
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )
```

### Tenants

```python
# app/models/tenant.py
import uuid
from sqlalchemy import String, Boolean, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, SoftDeleteMixin


class Tenant(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "tenants"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    domain: Mapped[str | None] = mapped_column(String(255), nullable=True)  # custom domain
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    settings: Mapped[dict] = mapped_column(JSONB, default=dict)
    # settings: {language, timezone, default_reply_policy, moderation_level, etc.}
    plan_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("billing_plans.id"), nullable=True
    )
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)

    # Relationships
    users = relationship("User", back_populates="tenant")
    brands = relationship("Brand", back_populates="tenant")
```

### Users & Roles

```python
# app/models/user.py
import uuid
from enum import Enum as PyEnum
from sqlalchemy import String, Boolean, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TenantMixin, TimestampMixin, SoftDeleteMixin


class UserRole(str, PyEnum):
    OWNER = "owner"
    ADMIN = "admin"
    MANAGER = "manager"
    EDITOR = "editor"
    VIEWER = "viewer"
    SUPPORT_AGENT = "support_agent"


class User(Base, TenantMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role_enum"), default=UserRole.VIEWER
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_superadmin: Mapped[bool] = mapped_column(Boolean, default=False)
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    preferences: Mapped[dict] = mapped_column(JSONB, default=dict)
    # preferences: {language, notifications, theme}
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    tenant = relationship("Tenant", back_populates="users")


class Permission(Base):
    __tablename__ = "permissions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)


class RolePermission(Base):
    __tablename__ = "role_permissions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole, name="user_role_enum"), nullable=False)
    permission_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("permissions.id"), nullable=False
    )
```

### Brands

```python
# app/models/brand.py
import uuid
from sqlalchemy import String, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TenantMixin, TimestampMixin


class Brand(Base, TenantMixin, TimestampMixin):
    __tablename__ = "brands"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    industry: Mapped[str | None] = mapped_column(String(100), nullable=True)
    logo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    colors: Mapped[dict] = mapped_column(JSONB, default=dict)
    # colors: {primary: "#FF5733", secondary: "#333333", accent: "#00BCD4"}
    tone: Mapped[str] = mapped_column(String(50), default="professional")
    # tone: professional, friendly, inspiring, casual, formal
    language: Mapped[str] = mapped_column(String(10), default="fr")
    target_country: Mapped[str] = mapped_column(String(5), default="BF")
    guidelines: Mapped[dict] = mapped_column(JSONB, default=dict)
    # guidelines: {dos: [...], donts: [...], keywords: [...], banned_words: [...]}

    tenant = relationship("Tenant", back_populates="brands")
    social_accounts = relationship("SocialAccount", back_populates="brand")
    knowledge_docs = relationship("KnowledgeDoc", back_populates="brand")
```

### Social Accounts & Channels

```python
# app/models/social_account.py
import uuid
from enum import Enum as PyEnum
from sqlalchemy import String, Boolean, ForeignKey, Enum, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TenantMixin, TimestampMixin


class Platform(str, PyEnum):
    FACEBOOK = "facebook"
    INSTAGRAM = "instagram"
    WHATSAPP = "whatsapp"
    MESSENGER = "messenger"
    TIKTOK = "tiktok"
    LINKEDIN = "linkedin"


class SocialAccount(Base, TenantMixin, TimestampMixin):
    __tablename__ = "social_accounts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    brand_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("brands.id"), nullable=False
    )
    platform: Mapped[Platform] = mapped_column(
        Enum(Platform, name="platform_enum"), nullable=False
    )
    platform_account_id: Mapped[str] = mapped_column(String(255), nullable=False)
    # External ID: Facebook page_id, Instagram business_id, WhatsApp phone_number_id
    account_name: Mapped[str] = mapped_column(String(255), nullable=False)
    access_token_encrypted: Mapped[str] = mapped_column(String(2000), nullable=False)
    refresh_token_encrypted: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    token_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    scopes: Mapped[list] = mapped_column(JSONB, default=list)
    # scopes: ["pages_manage_posts", "pages_read_engagement", ...]
    capabilities: Mapped[dict] = mapped_column(JSONB, default=dict)
    # capabilities: {can_post: true, can_reply_comments: true, can_reply_dm: true, ...}
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)

    brand = relationship("Brand", back_populates="social_accounts")
    channels = relationship("Channel", back_populates="social_account")


class Channel(Base, TenantMixin, TimestampMixin):
    """A channel is a specific communication channel within a social account.
    Example: A Facebook Page has both 'feed' and 'messenger' channels."""
    __tablename__ = "channels"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    social_account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("social_accounts.id"), nullable=False
    )
    channel_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # channel_type: "feed", "messenger", "dm", "comments", "whatsapp", "stories"
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    settings: Mapped[dict] = mapped_column(JSONB, default=dict)
    # settings: {auto_reply: true, reply_delay_seconds: 30, human_hours: "08:00-18:00"}

    social_account = relationship("SocialAccount", back_populates="channels")
    conversations = relationship("Conversation", back_populates="channel")
```

### Posts & Assets

```python
# app/models/post.py
import uuid
from enum import Enum as PyEnum
from datetime import datetime
from sqlalchemy import String, Text, ForeignKey, Enum, DateTime, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TenantMixin, TimestampMixin


class PostStatus(str, PyEnum):
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    SCHEDULED = "scheduled"
    PUBLISHING = "publishing"
    PUBLISHED = "published"
    FAILED = "failed"
    ARCHIVED = "archived"


class Post(Base, TenantMixin, TimestampMixin):
    __tablename__ = "posts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    brand_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("brands.id"), nullable=False
    )
    campaign_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("campaigns.id"), nullable=True
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )

    # Content
    content_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    hashtags: Mapped[list] = mapped_column(JSONB, default=list)
    # Per-channel content variants
    channel_variants: Mapped[dict] = mapped_column(JSONB, default=dict)
    # channel_variants: {"facebook": "Long version...", "instagram": "Short version..."}

    # Status & scheduling
    status: Mapped[PostStatus] = mapped_column(
        Enum(PostStatus, name="post_status_enum"), default=PostStatus.DRAFT
    )
    scheduled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Target channels
    target_channels: Mapped[list] = mapped_column(JSONB, default=list)
    # target_channels: [{"social_account_id": "...", "channel_type": "feed"}]

    # External references after publishing
    external_ids: Mapped[dict] = mapped_column(JSONB, default=dict)
    # external_ids: {"facebook_page_123": "post_456", "instagram_biz_789": "media_012"}

    # AI metadata
    ai_generated: Mapped[bool] = mapped_column(default=False)
    ai_confidence_score: Mapped[float | None] = mapped_column(nullable=True)
    generation_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    assets = relationship("PostAsset", back_populates="post")
    comments = relationship("Comment", back_populates="post")
    approvals = relationship("Approval", back_populates="post")


class PostAsset(Base, TenantMixin, TimestampMixin):
    __tablename__ = "post_assets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    post_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("posts.id", ondelete="CASCADE"), nullable=False
    )
    asset_type: Mapped[str] = mapped_column(String(20), nullable=False)
    # asset_type: "image", "video", "document", "audio"
    file_url: Mapped[str] = mapped_column(String(500), nullable=False)
    thumbnail_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    file_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    alt_text: Mapped[str | None] = mapped_column(String(500), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    ai_generated: Mapped[bool] = mapped_column(default=False)
    generation_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)

    post = relationship("Post", back_populates="assets")
```

### Comments & Replies

```python
# app/models/comment.py
import uuid
from sqlalchemy import String, Text, ForeignKey, DateTime, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TenantMixin, TimestampMixin


class Comment(Base, TenantMixin, TimestampMixin):
    __tablename__ = "comments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    post_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("posts.id"), nullable=False
    )
    platform: Mapped[str] = mapped_column(String(50), nullable=False)
    external_comment_id: Mapped[str] = mapped_column(String(255), nullable=False)
    author_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    author_external_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    sentiment: Mapped[str | None] = mapped_column(String(20), nullable=True)
    # sentiment: "positive", "negative", "neutral", "mixed"
    commented_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_hidden: Mapped[bool] = mapped_column(Boolean, default=False)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)

    post = relationship("Post", back_populates="comments")
    replies = relationship("Reply", back_populates="comment")


class Reply(Base, TenantMixin, TimestampMixin):
    __tablename__ = "replies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    comment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("comments.id"), nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    is_ai_generated: Mapped[bool] = mapped_column(Boolean, default=False)
    ai_confidence_score: Mapped[float | None] = mapped_column(nullable=True)
    replied_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    # replied_by is null if AI-generated, set if human
    external_reply_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    platform: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="draft")
    # status: "draft", "approved", "published", "failed"

    comment = relationship("Comment", back_populates="replies")
```

### Conversations & Messages (Inbox Unifiée)

```python
# app/models/conversation.py
import uuid
from enum import Enum as PyEnum
from sqlalchemy import String, Text, ForeignKey, DateTime, Boolean, Integer, Enum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TenantMixin, TimestampMixin


class ConversationStatus(str, PyEnum):
    OPEN = "open"
    AI_HANDLING = "ai_handling"
    HUMAN_HANDLING = "human_handling"
    WAITING_CUSTOMER = "waiting_customer"
    ESCALATED = "escalated"
    RESOLVED = "resolved"
    CLOSED = "closed"


class Conversation(Base, TenantMixin, TimestampMixin):
    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    channel_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("channels.id"), nullable=False
    )
    brand_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("brands.id"), nullable=False
    )

    # Customer info (external)
    customer_external_id: Mapped[str] = mapped_column(String(255), nullable=False)
    customer_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    customer_phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    customer_metadata: Mapped[dict] = mapped_column(JSONB, default=dict)

    # Status
    status: Mapped[ConversationStatus] = mapped_column(
        Enum(ConversationStatus, name="conversation_status_enum"),
        default=ConversationStatus.OPEN,
    )
    assigned_to: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    # assigned_to: human agent if escalated

    # Metadata
    platform: Mapped[str] = mapped_column(String(50), nullable=False)
    subject: Mapped[str | None] = mapped_column(String(500), nullable=True)
    tags: Mapped[list] = mapped_column(JSONB, default=list)
    sentiment: Mapped[str | None] = mapped_column(String(20), nullable=True)
    message_count: Mapped[int] = mapped_column(Integer, default=0)
    last_message_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    channel = relationship("Channel", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", order_by="Message.created_at")
    escalations = relationship("Escalation", back_populates="conversation")


class MessageDirection(str, PyEnum):
    INBOUND = "inbound"    # From customer
    OUTBOUND = "outbound"  # From us (AI or human)


class Message(Base, TenantMixin, TimestampMixin):
    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("conversations.id"), nullable=False
    )
    direction: Mapped[MessageDirection] = mapped_column(
        Enum(MessageDirection, name="message_direction_enum"), nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_type: Mapped[str] = mapped_column(String(20), default="text")
    # content_type: "text", "image", "audio", "video", "document", "location", "template"
    media_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Source tracking
    is_ai_generated: Mapped[bool] = mapped_column(Boolean, default=False)
    ai_confidence_score: Mapped[float | None] = mapped_column(nullable=True)
    sent_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )

    # External reference
    external_message_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    platform: Mapped[str] = mapped_column(String(50), nullable=False)

    # Status
    status: Mapped[str] = mapped_column(String(20), default="sent")
    # status: "pending", "sent", "delivered", "read", "failed"
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # RAG sources used for this response
    sources: Mapped[list] = mapped_column(JSONB, default=list)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)

    conversation = relationship("Conversation", back_populates="messages")
```

### Knowledge Base (RAG)

```python
# app/models/knowledge.py
import uuid
from sqlalchemy import String, Text, ForeignKey, Integer, Float
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector

from app.models.base import Base, TenantMixin, TimestampMixin


class KnowledgeDoc(Base, TenantMixin, TimestampMixin):
    __tablename__ = "knowledge_docs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    brand_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("brands.id"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    doc_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # doc_type: "faq", "product_catalog", "policy", "guide", "webpage", "custom"
    source_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    file_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    raw_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    # status: "pending", "processing", "indexed", "failed", "archived"
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    language: Mapped[str] = mapped_column(String(10), default="fr")
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)
    uploaded_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )

    brand = relationship("Brand", back_populates="knowledge_docs")
    chunks = relationship("Chunk", back_populates="document")


class Chunk(Base, TenantMixin, TimestampMixin):
    __tablename__ = "chunks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("knowledge_docs.id", ondelete="CASCADE"), nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    token_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # pgvector embedding
    embedding: Mapped[list] = mapped_column(Vector(768), nullable=True)
    # 768 dimensions = multilingual-e5-large / BGE-M3

    # Metadata for filtering
    section_title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)

    document = relationship("KnowledgeDoc", back_populates="chunks")
```

### Campaigns

```python
# app/models/campaign.py
import uuid
from sqlalchemy import String, Text, ForeignKey, DateTime, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TenantMixin, TimestampMixin


class Campaign(Base, TenantMixin, TimestampMixin):
    __tablename__ = "campaigns"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    brand_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("brands.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    objective: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # objective: "awareness", "engagement", "traffic", "sales", "support"
    status: Mapped[str] = mapped_column(String(20), default="draft")
    # status: "draft", "active", "paused", "completed", "archived"
    start_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    end_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    target_channels: Mapped[list] = mapped_column(JSONB, default=list)
    settings: Mapped[dict] = mapped_column(JSONB, default=dict)
    # settings: {post_frequency: "daily", auto_generate: true, require_approval: true}
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )

    posts = relationship("Post", back_populates="campaign")
```

### Approvals & Escalations

```python
# app/models/approval.py
import uuid
from sqlalchemy import String, Text, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TenantMixin, TimestampMixin


class Approval(Base, TenantMixin, TimestampMixin):
    __tablename__ = "approvals"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    post_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("posts.id"), nullable=False
    )
    requested_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(20), default="pending")
    # status: "pending", "approved", "rejected", "expired"
    review_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    post = relationship("Post", back_populates="approvals")


class Escalation(Base, TenantMixin, TimestampMixin):
    __tablename__ = "escalations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("conversations.id"), nullable=False
    )
    reason: Mapped[str] = mapped_column(String(500), nullable=False)
    priority: Mapped[str] = mapped_column(String(20), default="medium")
    # priority: "low", "medium", "high", "urgent"
    status: Mapped[str] = mapped_column(String(20), default="open")
    # status: "open", "assigned", "in_progress", "resolved", "closed"
    assigned_to: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    ai_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_context: Mapped[dict] = mapped_column(JSONB, default=dict)
    # ai_context: {attempts: [...], confidence_scores: [...], last_response: "..."}
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolution_note: Mapped[str | None] = mapped_column(Text, nullable=True)

    conversation = relationship("Conversation", back_populates="escalations")
```

### Billing

```python
# app/models/billing.py
import uuid
from sqlalchemy import String, Text, ForeignKey, DateTime, Integer, Numeric, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class BillingPlan(Base, TimestampMixin):
    __tablename__ = "billing_plans"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    slug: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    price_monthly_xof: Mapped[int] = mapped_column(Integer, nullable=False)
    # Price in FCFA (XOF) — primary currency for West Africa
    price_monthly_usd: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    features: Mapped[dict] = mapped_column(JSONB, default=dict)
    limits: Mapped[dict] = mapped_column(JSONB, default=dict)
    # limits: {
    #   max_brands: 1, max_social_accounts: 3, max_posts_per_month: 30,
    #   max_ai_generations: 50, max_support_conversations: 100,
    #   max_documents: 10, max_storage_mb: 500, max_users: 3,
    #   max_whatsapp_messages: 500
    # }


class Subscription(Base, TimestampMixin):
    __tablename__ = "subscriptions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), unique=True, nullable=False
    )
    plan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("billing_plans.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(20), default="active")
    # status: "trial", "active", "past_due", "cancelled", "expired"
    current_period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    current_period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    trial_ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    payment_method: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # payment_method: "mobile_money", "card", "bank_transfer", "orange_money"
    external_subscription_id: Mapped[str | None] = mapped_column(String(255), nullable=True)


class UsageRecord(Base, TimestampMixin):
    __tablename__ = "usage_records"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    metric: Mapped[str] = mapped_column(String(50), nullable=False)
    # metric: "ai_generations", "posts_published", "messages_sent", "documents_ingested", etc.
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)
```

### Analytics & Audit

```python
# app/models/analytics.py
import uuid
from sqlalchemy import String, ForeignKey, DateTime, Integer, Float
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantMixin, TimestampMixin


class AnalyticsEvent(Base, TenantMixin):
    """Append-only event log for analytics."""
    __tablename__ = "analytics_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    # event_type: "post_published", "post_engagement", "message_received",
    #             "message_responded", "escalation_created", "document_ingested", etc.
    entity_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    brand_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("brands.id"), nullable=True
    )
    platform: Mapped[str | None] = mapped_column(String(50), nullable=True)
    data: Mapped[dict] = mapped_column(JSONB, default=dict)
    # data: {likes: 42, comments: 5, shares: 3, reach: 1200, ...}
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()"), nullable=False
    )


class AuditEvent(Base, TenantMixin, TimestampMixin):
    """Audit trail for security and compliance."""
    __tablename__ = "audit_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    # action: "user.login", "post.create", "post.publish", "social_account.connect",
    #         "knowledge.upload", "escalation.assign", "settings.update", etc.
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False)
    resource_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
    changes: Mapped[dict] = mapped_column(JSONB, default=dict)
    # changes: {before: {...}, after: {...}}
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)
```

### Agent Runs & Workflows

```python
# app/models/agent_run.py
import uuid
from sqlalchemy import String, Text, ForeignKey, DateTime, Integer, Float
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantMixin, TimestampMixin


class AgentRun(Base, TenantMixin, TimestampMixin):
    """Log of every agent execution for debugging and analytics."""
    __tablename__ = "agent_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    task_type: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="running")
    # status: "running", "completed", "failed", "escalated"
    input_data: Mapped[dict] = mapped_column(JSONB, default=dict)
    output_data: Mapped[dict] = mapped_column(JSONB, default=dict)
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    execution_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tokens_used: Mapped[int | None] = mapped_column(Integer, nullable=True)
    model_used: Mapped[str | None] = mapped_column(String(100), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    parent_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agent_runs.id"), nullable=True
    )
    # parent_run_id: for tracking orchestrator → sub-agent chains
    triggered_by: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # triggered_by: "user", "webhook", "cron", "agent"


class Workflow(Base, TenantMixin, TimestampMixin):
    """User-defined automation workflows (future feature)."""
    __tablename__ = "workflows"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    brand_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("brands.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    trigger_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # trigger_type: "new_message", "new_comment", "scheduled", "manual", "keyword"
    trigger_config: Mapped[dict] = mapped_column(JSONB, default=dict)
    actions: Mapped[list] = mapped_column(JSONB, default=list)
    # actions: [{"type": "generate_reply", "config": {...}}, {"type": "send_message", ...}]
    is_active: Mapped[bool] = mapped_column(default=True)
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
```

### Templates

```python
# app/models/template.py
import uuid
from sqlalchemy import String, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantMixin, TimestampMixin


class Template(Base, TenantMixin, TimestampMixin):
    __tablename__ = "templates"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    brand_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("brands.id"), nullable=True
    )
    # brand_id null = system template
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    template_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # template_type: "post", "reply", "support_response", "whatsapp_template", "image_prompt"
    content: Mapped[str] = mapped_column(Text, nullable=False)
    variables: Mapped[list] = mapped_column(JSONB, default=list)
    # variables: ["brand_name", "product_name", "price", "promo_code"]
    channel: Mapped[str | None] = mapped_column(String(50), nullable=True)
    language: Mapped[str] = mapped_column(String(10), default="fr")
    is_system: Mapped[bool] = mapped_column(default=False)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)
```
