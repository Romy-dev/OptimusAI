"""Import all models so Alembic and SQLAlchemy can discover them."""

from app.models.base import Base, TenantMixin, TimestampMixin, SoftDeleteMixin
from app.models.tenant import Tenant
from app.models.user import User, UserRole
from app.models.brand import Brand
from app.models.social_account import SocialAccount, Channel, Platform
from app.models.post import Post, PostAsset, PostStatus
from app.models.comment import Comment, Reply
from app.models.conversation import Conversation, Message, ConversationStatus, MessageDirection
from app.models.knowledge import KnowledgeDoc, Chunk
from app.models.campaign import Campaign
from app.models.approval import Approval
from app.models.escalation import Escalation
from app.models.billing import BillingPlan, Subscription, UsageRecord
from app.models.analytics import AnalyticsEvent
from app.models.audit import AuditEvent
from app.models.agent_run import AgentRun
from app.models.template import Template
from app.models.workflow import Workflow
from app.models.brand_profile import BrandProfile, ChannelCapability
from app.models.gallery import GeneratedImage
from app.models.customer_profile import CustomerProfile
from app.models.design_template import DesignTemplate, BrandDesignDNA
from app.models.chat import ChatMessage
from app.models.feature_flag import FeatureFlag

__all__ = [
    "Base",
    "Tenant",
    "User",
    "UserRole",
    "Brand",
    "SocialAccount",
    "Channel",
    "Platform",
    "Post",
    "PostAsset",
    "PostStatus",
    "Comment",
    "Reply",
    "Conversation",
    "Message",
    "ConversationStatus",
    "MessageDirection",
    "KnowledgeDoc",
    "Chunk",
    "Campaign",
    "Approval",
    "Escalation",
    "BillingPlan",
    "Subscription",
    "UsageRecord",
    "AnalyticsEvent",
    "AuditEvent",
    "AgentRun",
    "Template",
    "Workflow",
    "BrandProfile",
    "ChannelCapability",
    "GeneratedImage",
    "CustomerProfile",
    "DesignTemplate",
    "BrandDesignDNA",
    "ChatMessage",
]
