"""Admin tenants management — list, view, suspend, change plan."""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.admin_auth import require_superadmin
from app.core.database import get_session
from app.models.tenant import Tenant
from app.models.user import User
from app.models.post import Post
from app.models.conversation import Conversation

router = APIRouter(prefix="/tenants")


@router.get("")
async def list_all_tenants(
    user: User = Depends(require_superadmin),
    session: AsyncSession = Depends(get_session),
):
    """List all tenants with stats."""
    stmt = select(Tenant).order_by(Tenant.created_at.desc())
    result = await session.execute(stmt)
    tenants = result.scalars().all()

    output = []
    for t in tenants:
        # Count users
        user_count = await session.scalar(
            select(func.count()).select_from(User).where(User.tenant_id == t.id)
        )
        # Count posts
        post_count = await session.scalar(
            select(func.count()).select_from(Post).where(Post.tenant_id == t.id)
        )
        # Count conversations
        convo_count = await session.scalar(
            select(func.count()).select_from(Conversation).where(Conversation.tenant_id == t.id)
        )

        output.append({
            "id": str(t.id),
            "name": t.name,
            "slug": t.slug,
            "is_active": t.is_active,
            "settings": t.settings,
            "created_at": t.created_at.isoformat(),
            "stats": {
                "users": user_count,
                "posts": post_count,
                "conversations": convo_count,
            },
        })
    return output


@router.get("/{tenant_id}")
async def get_tenant_detail(
    tenant_id: uuid.UUID,
    user: User = Depends(require_superadmin),
    session: AsyncSession = Depends(get_session),
):
    """Get detailed info about a specific tenant."""
    tenant = await session.get(Tenant, tenant_id)
    if not tenant:
        from app.core.exceptions import NotFoundError
        raise NotFoundError("Tenant not found")

    # Users
    users_result = await session.execute(
        select(User).where(User.tenant_id == tenant_id).order_by(User.created_at)
    )
    users = users_result.scalars().all()

    return {
        "id": str(tenant.id),
        "name": tenant.name,
        "slug": tenant.slug,
        "is_active": tenant.is_active,
        "settings": tenant.settings,
        "created_at": tenant.created_at.isoformat(),
        "users": [
            {
                "id": str(u.id),
                "email": u.email,
                "full_name": u.full_name,
                "role": u.role.value if hasattr(u.role, 'value') else str(u.role),
                "is_active": u.is_active,
                "created_at": u.created_at.isoformat(),
            }
            for u in users
        ],
    }


@router.post("/{tenant_id}/suspend")
async def suspend_tenant(
    tenant_id: uuid.UUID,
    user: User = Depends(require_superadmin),
    session: AsyncSession = Depends(get_session),
):
    """Suspend a tenant."""
    tenant = await session.get(Tenant, tenant_id)
    if not tenant:
        from app.core.exceptions import NotFoundError
        raise NotFoundError("Tenant not found")
    tenant.is_active = False
    await session.commit()
    return {"id": str(tenant.id), "is_active": False}


@router.post("/{tenant_id}/activate")
async def activate_tenant(
    tenant_id: uuid.UUID,
    user: User = Depends(require_superadmin),
    session: AsyncSession = Depends(get_session),
):
    """Reactivate a suspended tenant."""
    tenant = await session.get(Tenant, tenant_id)
    if not tenant:
        from app.core.exceptions import NotFoundError
        raise NotFoundError("Tenant not found")
    tenant.is_active = True
    await session.commit()
    return {"id": str(tenant.id), "is_active": True}
