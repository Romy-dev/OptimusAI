"""Shared FastAPI dependencies for dependency injection."""

import uuid

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.database import get_session
from app.models.user import User
from app.repositories.base import BaseRepository
from app.repositories.tenant import TenantRepository
from app.repositories.user import UserRepository


def get_tenant_id(request: Request) -> uuid.UUID | None:
    return getattr(request.state, "tenant_id", None)


async def get_user_repo(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> UserRepository:
    return UserRepository(session, tenant_id=user.tenant_id)


async def get_tenant_repo(
    session: AsyncSession = Depends(get_session),
) -> TenantRepository:
    return TenantRepository(session)
