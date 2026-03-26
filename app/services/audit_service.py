"""Audit trail service — logs every sensitive action."""

import uuid
from datetime import datetime

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditEvent

logger = structlog.get_logger()


class AuditService:
    """Records audit events for compliance and debugging."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def log(
        self,
        *,
        tenant_id: uuid.UUID,
        action: str,
        resource_type: str,
        resource_id: uuid.UUID | None = None,
        actor_id: uuid.UUID | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        changes: dict | None = None,
        metadata: dict | None = None,
    ) -> AuditEvent:
        event = AuditEvent(
            tenant_id=tenant_id,
            actor_id=actor_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=ip_address,
            user_agent=user_agent,
            changes=changes or {},
            metadata_=metadata or {},
        )
        self.session.add(event)
        await self.session.flush()

        logger.info(
            "audit_event",
            action=action,
            resource_type=resource_type,
            resource_id=str(resource_id) if resource_id else None,
            actor_id=str(actor_id) if actor_id else None,
            tenant_id=str(tenant_id),
        )
        return event

    async def log_from_request(
        self,
        *,
        request,
        tenant_id: uuid.UUID,
        actor_id: uuid.UUID | None,
        action: str,
        resource_type: str,
        resource_id: uuid.UUID | None = None,
        changes: dict | None = None,
    ) -> AuditEvent:
        """Convenience method that extracts IP and user-agent from a FastAPI Request."""
        ip = request.client.host if request.client else None
        ua = request.headers.get("user-agent")
        return await self.log(
            tenant_id=tenant_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            actor_id=actor_id,
            ip_address=ip,
            user_agent=ua,
            changes=changes,
        )
