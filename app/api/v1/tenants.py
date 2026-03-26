import uuid

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.database import get_session
from app.core.permissions import RequirePermission
from app.models.user import User, UserRole
from app.schemas.tenant import (
    MemberInviteRequest,
    MemberResponse,
    MemberRoleUpdate,
    TenantResponse,
    TenantSettingsUpdate,
    UsageSummaryResponse,
)
from app.services.quota_service import QuotaService
from app.services.tenant_service import TenantService

router = APIRouter(prefix="/tenants", tags=["tenants"])


def get_tenant_service(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> TenantService:
    return TenantService(session, tenant_id=user.tenant_id)


@router.get("/current", response_model=TenantResponse)
async def get_current_tenant(
    user: User = Depends(get_current_user),
    service: TenantService = Depends(get_tenant_service),
):
    return await service.get_tenant()


@router.put("/current/settings", response_model=TenantResponse)
async def update_tenant_settings(
    body: TenantSettingsUpdate,
    user: User = Depends(RequirePermission("members.manage")),
    service: TenantService = Depends(get_tenant_service),
):
    return await service.update_settings(body.settings, actor_id=user.id)


@router.get("/current/members", response_model=list[MemberResponse])
async def list_members(
    user: User = Depends(RequirePermission("members.read")),
    service: TenantService = Depends(get_tenant_service),
):
    members = await service.list_members()
    return members


@router.post("/current/members", response_model=MemberResponse, status_code=201)
async def invite_member(
    body: MemberInviteRequest,
    user: User = Depends(RequirePermission("members.manage")),
    service: TenantService = Depends(get_tenant_service),
    session: AsyncSession = Depends(get_session),
):
    # Check quota
    quota = QuotaService(session)
    await quota.enforce_quota(user.tenant_id, "users")

    new_user = await service.invite_member(
        email=body.email,
        full_name=body.full_name,
        role=body.role,
        invited_by=user.id,
    )
    await quota.record_usage(user.tenant_id, "users")
    return new_user


@router.put("/current/members/{user_id}/role", response_model=MemberResponse)
async def change_member_role(
    user_id: uuid.UUID,
    body: MemberRoleUpdate,
    user: User = Depends(RequirePermission("members.manage")),
    service: TenantService = Depends(get_tenant_service),
):
    return await service.change_member_role(user_id, body.role, actor_id=user.id)


@router.delete("/current/members/{user_id}", status_code=204)
async def remove_member(
    user_id: uuid.UUID,
    user: User = Depends(RequirePermission("members.manage")),
    service: TenantService = Depends(get_tenant_service),
):
    await service.remove_member(user_id, actor_id=user.id)


@router.get("/current/usage", response_model=UsageSummaryResponse)
async def get_usage(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    quota = QuotaService(session)
    summary = await quota.get_usage_summary(user.tenant_id)
    return UsageSummaryResponse(usage=summary)
