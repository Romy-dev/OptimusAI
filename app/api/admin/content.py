"""Admin content — view all posts, images, documents across tenants."""

from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.admin_auth import require_superadmin
from app.core.database import get_session
from app.models.user import User
from app.models.post import Post
from app.models.gallery import GeneratedImage
from app.models.knowledge import KnowledgeDoc
from app.models.tenant import Tenant
from app.models.social_account import SocialAccount

router = APIRouter(prefix="/content")


@router.get("/posts")
async def all_posts(
    limit: int = 50,
    status: str | None = None,
    user: User = Depends(require_superadmin),
    session: AsyncSession = Depends(get_session),
):
    stmt = (
        select(Post, Tenant.name.label("tenant_name"))
        .join(Tenant, Post.tenant_id == Tenant.id)
        .order_by(Post.created_at.desc())
        .limit(limit)
    )
    if status:
        stmt = stmt.where(Post.status == status)
    result = await session.execute(stmt)
    return [
        {
            "id": str(row.Post.id),
            "content": (row.Post.content_text or "")[:150],
            "status": row.Post.status.value if hasattr(row.Post.status, 'value') else str(row.Post.status),
            "ai_generated": row.Post.ai_generated,
            "ai_confidence": row.Post.ai_confidence_score,
            "tenant_name": row.tenant_name,
            "created_at": row.Post.created_at.isoformat(),
        }
        for row in result
    ]


@router.get("/images")
async def all_images(
    limit: int = 50,
    user: User = Depends(require_superadmin),
    session: AsyncSession = Depends(get_session),
):
    stmt = (
        select(GeneratedImage, Tenant.name.label("tenant_name"))
        .join(Tenant, GeneratedImage.tenant_id == Tenant.id)
        .order_by(GeneratedImage.created_at.desc())
        .limit(limit)
    )
    result = await session.execute(stmt)
    return [
        {
            "id": str(row.GeneratedImage.id),
            "prompt": row.GeneratedImage.prompt[:100],
            "image_url": row.GeneratedImage.image_url,
            "tenant_name": row.tenant_name,
            "created_at": row.GeneratedImage.created_at.isoformat(),
        }
        for row in result
    ]


@router.get("/documents")
async def all_documents(
    user: User = Depends(require_superadmin),
    session: AsyncSession = Depends(get_session),
):
    stmt = (
        select(KnowledgeDoc, Tenant.name.label("tenant_name"))
        .join(Tenant, KnowledgeDoc.tenant_id == Tenant.id)
        .order_by(KnowledgeDoc.created_at.desc())
        .limit(50)
    )
    result = await session.execute(stmt)
    return [
        {
            "id": str(row.KnowledgeDoc.id),
            "title": row.KnowledgeDoc.title,
            "doc_type": row.KnowledgeDoc.doc_type,
            "status": row.KnowledgeDoc.status,
            "chunk_count": row.KnowledgeDoc.chunk_count,
            "tenant_name": row.tenant_name,
            "created_at": row.KnowledgeDoc.created_at.isoformat(),
        }
        for row in result
    ]


@router.get("/connections")
async def all_connections(
    user: User = Depends(require_superadmin),
    session: AsyncSession = Depends(get_session),
):
    stmt = (
        select(SocialAccount, Tenant.name.label("tenant_name"))
        .join(Tenant, SocialAccount.tenant_id == Tenant.id)
        .order_by(SocialAccount.created_at.desc())
    )
    result = await session.execute(stmt)
    return [
        {
            "id": str(row.SocialAccount.id),
            "platform": row.SocialAccount.platform.value,
            "account_name": row.SocialAccount.account_name,
            "is_active": row.SocialAccount.is_active,
            "token_expires_at": row.SocialAccount.token_expires_at.isoformat() if row.SocialAccount.token_expires_at else None,
            "tenant_name": row.tenant_name,
            "created_at": row.SocialAccount.created_at.isoformat(),
        }
        for row in result
    ]
