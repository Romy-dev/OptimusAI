"""Admin users — global user management across all tenants."""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.admin_auth import require_superadmin
from app.core.database import get_session
from app.models.user import User
from app.models.tenant import Tenant

router = APIRouter(prefix="/users")


@router.get("")
async def list_all_users(
    search: str = "",
    limit: int = 100,
    user: User = Depends(require_superadmin),
    session: AsyncSession = Depends(get_session),
):
    stmt = select(User, Tenant.name.label("tenant_name")).join(Tenant, User.tenant_id == Tenant.id)
    if search:
        stmt = stmt.where(or_(User.email.ilike(f"%{search}%"), User.full_name.ilike(f"%{search}%")))
    stmt = stmt.order_by(User.created_at.desc()).limit(limit)
    result = await session.execute(stmt)
    return [
        {
            "id": str(row.User.id),
            "email": row.User.email,
            "full_name": row.User.full_name,
            "role": row.User.role.value if hasattr(row.User.role, 'value') else str(row.User.role),
            "is_active": row.User.is_active,
            "tenant_id": str(row.User.tenant_id),
            "tenant_name": row.tenant_name,
            "created_at": row.User.created_at.isoformat(),
        }
        for row in result
    ]


@router.post("/{user_id}/toggle")
async def toggle_user(
    user_id: uuid.UUID,
    admin: User = Depends(require_superadmin),
    session: AsyncSession = Depends(get_session),
):
    u = await session.get(User, user_id)
    if not u:
        from app.core.exceptions import NotFoundError
        raise NotFoundError("User not found")
    u.is_active = not u.is_active
    await session.commit()
    return {"id": str(u.id), "is_active": u.is_active}


@router.post("/{user_id}/reset-password")
async def reset_password(
    user_id: uuid.UUID,
    body: dict,
    admin: User = Depends(require_superadmin),
    session: AsyncSession = Depends(get_session),
):
    from app.core.auth import hash_password
    u = await session.get(User, user_id)
    if not u:
        from app.core.exceptions import NotFoundError
        raise NotFoundError("User not found")
    new_pw = body.get("password", "OptimusAI2026!")
    u.hashed_password = hash_password(new_pw)
    await session.commit()
    return {"id": str(u.id), "message": "Password reset"}
