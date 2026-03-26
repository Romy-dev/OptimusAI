"""Admin Feature Flags — toggle features per-tenant or globally."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.database import get_session
from app.models.user import User
from app.models.feature_flag import FeatureFlag

router = APIRouter(prefix="/feature-flags", tags=["admin-feature-flags"])


def _require_superadmin(user: User = Depends(get_current_user)) -> User:
    if not user.is_superadmin:
        raise HTTPException(403, "Superadmin required")
    return user


class FlagCreate(BaseModel):
    name: str
    description: str = ""
    enabled_globally: bool = False


class FlagUpdate(BaseModel):
    enabled_globally: bool | None = None
    description: str | None = None
    enabled_tenants: list[str] | None = None
    disabled_tenants: list[str] | None = None


@router.get("")
async def list_flags(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(_require_superadmin),
):
    """List all feature flags."""
    result = await session.execute(select(FeatureFlag).order_by(FeatureFlag.name))
    flags = result.scalars().all()
    return [
        {
            "id": str(f.id),
            "name": f.name,
            "description": f.description,
            "enabled_globally": f.enabled_globally,
            "enabled_tenants": f.enabled_tenants or [],
            "disabled_tenants": f.disabled_tenants or [],
            "created_at": f.created_at.isoformat() if f.created_at else None,
        }
        for f in flags
    ]


@router.post("")
async def create_flag(
    payload: FlagCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(_require_superadmin),
):
    """Create a new feature flag."""
    existing = await session.scalar(
        select(FeatureFlag).where(FeatureFlag.name == payload.name)
    )
    if existing:
        raise HTTPException(409, f"Flag '{payload.name}' already exists")

    flag = FeatureFlag(
        id=uuid.uuid4(),
        name=payload.name,
        description=payload.description,
        enabled_globally=payload.enabled_globally,
        enabled_tenants=[],
        disabled_tenants=[],
    )
    session.add(flag)
    await session.flush()

    return {"id": str(flag.id), "name": flag.name, "created": True}


@router.put("/{flag_id}")
async def update_flag(
    flag_id: str,
    payload: FlagUpdate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(_require_superadmin),
):
    """Update a feature flag."""
    flag = await session.get(FeatureFlag, uuid.UUID(flag_id))
    if not flag:
        raise HTTPException(404, "Flag not found")

    if payload.enabled_globally is not None:
        flag.enabled_globally = payload.enabled_globally
    if payload.description is not None:
        flag.description = payload.description
    if payload.enabled_tenants is not None:
        flag.enabled_tenants = payload.enabled_tenants
    if payload.disabled_tenants is not None:
        flag.disabled_tenants = payload.disabled_tenants

    await session.flush()
    return {"id": str(flag.id), "updated": True}


@router.delete("/{flag_id}")
async def delete_flag(
    flag_id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(_require_superadmin),
):
    """Delete a feature flag."""
    flag = await session.get(FeatureFlag, uuid.UUID(flag_id))
    if not flag:
        raise HTTPException(404, "Flag not found")

    await session.delete(flag)
    await session.flush()
    return {"deleted": True}
