"""Tenant management: invitations, team, suspension, settings."""

import uuid
from datetime import datetime, timezone

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import hash_password
from app.core.exceptions import (
    AlreadyExistsError,
    NotFoundError,
    PermissionDeniedError,
)
from app.models.tenant import Tenant
from app.models.user import User, UserRole
from app.repositories.tenant import TenantRepository
from app.repositories.user import UserRepository
from app.services.audit_service import AuditService

logger = structlog.get_logger()


class TenantService:
    """Business logic for tenant management."""

    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID):
        self.session = session
        self.tenant_id = tenant_id
        self.tenant_repo = TenantRepository(session)
        self.user_repo = UserRepository(session, tenant_id=tenant_id)
        self.audit = AuditService(session)

    async def get_tenant(self) -> Tenant:
        tenant = await self.tenant_repo.get_by_id(self.tenant_id)
        if not tenant:
            raise NotFoundError("Tenant not found")
        return tenant

    async def update_settings(
        self,
        settings: dict,
        actor_id: uuid.UUID,
    ) -> Tenant:
        tenant = await self.get_tenant()
        old_settings = dict(tenant.settings)
        merged = {**tenant.settings, **settings}
        tenant = await self.tenant_repo.update(self.tenant_id, settings=merged)

        await self.audit.log(
            tenant_id=self.tenant_id,
            actor_id=actor_id,
            action="tenant.settings_update",
            resource_type="tenant",
            resource_id=self.tenant_id,
            changes={"before": old_settings, "after": merged},
        )
        return tenant

    async def invite_member(
        self,
        *,
        email: str,
        full_name: str,
        role: UserRole,
        invited_by: uuid.UUID,
        temp_password: str | None = None,
    ) -> User:
        """Invite a new member to the tenant."""
        # Check if email already exists
        existing = await self.user_repo.get_by_email(email)
        if existing:
            raise AlreadyExistsError("A user with this email already exists")

        # Generate temp password if not provided
        password = temp_password or uuid.uuid4().hex[:12]

        user = await self.user_repo.create(
            email=email,
            hashed_password=hash_password(password),
            full_name=full_name,
            role=role,
            is_active=True,
        )

        await self.audit.log(
            tenant_id=self.tenant_id,
            actor_id=invited_by,
            action="tenant.member_invite",
            resource_type="user",
            resource_id=user.id,
            metadata={"email": email, "role": role.value},
        )

        logger.info(
            "member_invited",
            tenant_id=str(self.tenant_id),
            email=email,
            role=role.value,
        )
        # TODO: send invitation email with temp password
        return user

    async def change_member_role(
        self,
        user_id: uuid.UUID,
        new_role: UserRole,
        actor_id: uuid.UUID,
    ) -> User:
        """Change a member's role."""
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise NotFoundError("User not found")

        # Cannot change own role
        if user_id == actor_id:
            raise PermissionDeniedError("Cannot change your own role")

        old_role = user.role.value
        user = await self.user_repo.update(user_id, role=new_role)

        await self.audit.log(
            tenant_id=self.tenant_id,
            actor_id=actor_id,
            action="tenant.member_role_change",
            resource_type="user",
            resource_id=user_id,
            changes={"role": {"before": old_role, "after": new_role.value}},
        )
        return user

    async def remove_member(
        self,
        user_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> None:
        """Remove a member from the tenant (soft deactivate)."""
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise NotFoundError("User not found")
        if user_id == actor_id:
            raise PermissionDeniedError("Cannot remove yourself")
        if user.role == UserRole.OWNER:
            raise PermissionDeniedError("Cannot remove the owner")

        await self.user_repo.update(user_id, is_active=False)

        await self.audit.log(
            tenant_id=self.tenant_id,
            actor_id=actor_id,
            action="tenant.member_remove",
            resource_type="user",
            resource_id=user_id,
        )

    async def list_members(self) -> list[User]:
        """List all active members of the tenant."""
        return await self.user_repo.list(is_active=True, limit=100)

    async def suspend_tenant(
        self,
        reason: str,
        actor_id: uuid.UUID,
    ) -> Tenant:
        """Suspend a tenant (admin action)."""
        tenant = await self.tenant_repo.update(self.tenant_id, is_active=False)

        await self.audit.log(
            tenant_id=self.tenant_id,
            actor_id=actor_id,
            action="tenant.suspend",
            resource_type="tenant",
            resource_id=self.tenant_id,
            metadata={"reason": reason},
        )
        logger.warning(
            "tenant_suspended",
            tenant_id=str(self.tenant_id),
            reason=reason,
        )
        return tenant

    async def reactivate_tenant(
        self,
        actor_id: uuid.UUID,
    ) -> Tenant:
        """Reactivate a suspended tenant."""
        tenant = await self.tenant_repo.update(self.tenant_id, is_active=True)

        await self.audit.log(
            tenant_id=self.tenant_id,
            actor_id=actor_id,
            action="tenant.reactivate",
            resource_type="tenant",
            resource_id=self.tenant_id,
        )
        return tenant
