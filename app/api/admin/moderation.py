"""Admin moderation — flagged posts, escalated conversations."""

from fastapi import APIRouter, Depends
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.admin_auth import require_superadmin
from app.core.database import get_session
from app.models.user import User
from app.models.post import Post, PostStatus
from app.models.conversation import Conversation
from app.models.escalation import Escalation
from app.models.tenant import Tenant

router = APIRouter(prefix="/moderation")


@router.get("/flagged-posts")
async def flagged_posts(
    user: User = Depends(require_superadmin),
    session: AsyncSession = Depends(get_session),
):
    stmt = (
        select(Post, Tenant.name.label("tenant_name"))
        .join(Tenant, Post.tenant_id == Tenant.id)
        .where(Post.status == PostStatus.REJECTED)
        .order_by(Post.created_at.desc())
        .limit(50)
    )
    result = await session.execute(stmt)
    return [
        {
            "id": str(row.Post.id),
            "content": (row.Post.content_text or "")[:200],
            "status": row.Post.status.value,
            "ai_confidence": row.Post.ai_confidence_score,
            "tenant_name": row.tenant_name,
            "tenant_id": str(row.Post.tenant_id),
            "created_at": row.Post.created_at.isoformat(),
        }
        for row in result
    ]


@router.get("/escalations")
async def active_escalations(
    user: User = Depends(require_superadmin),
    session: AsyncSession = Depends(get_session),
):
    stmt = (
        select(Escalation, Tenant.name.label("tenant_name"))
        .join(Tenant, Escalation.tenant_id == Tenant.id)
        .order_by(Escalation.created_at.desc())
        .limit(50)
    )
    result = await session.execute(stmt)
    return [
        {
            "id": str(row.Escalation.id),
            "conversation_id": str(row.Escalation.conversation_id),
            "reason": row.Escalation.reason,
            "priority": row.Escalation.priority,
            "status": row.Escalation.status,
            "tenant_name": row.tenant_name,
            "tenant_id": str(row.Escalation.tenant_id),
            "created_at": row.Escalation.created_at.isoformat(),
        }
        for row in result
    ]


@router.get("/stats")
async def moderation_stats(
    user: User = Depends(require_superadmin),
    session: AsyncSession = Depends(get_session),
):
    rejected = await session.scalar(
        select(func.count()).select_from(Post).where(Post.status == PostStatus.REJECTED)
    )
    escalated = await session.scalar(
        select(func.count()).select_from(Conversation).where(Conversation.status == "escalated")
    )
    pending_review = await session.scalar(
        select(func.count()).select_from(Post).where(Post.status == PostStatus.PENDING_REVIEW)
    )
    return {
        "rejected_posts": rejected,
        "escalated_conversations": escalated,
        "pending_review": pending_review,
    }
