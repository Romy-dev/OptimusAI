"""Admin audit — action history, login logs."""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.admin_auth import require_superadmin
from app.core.database import get_session
from app.models.user import User
from app.models.audit import AuditEvent
from app.models.tenant import Tenant

router = APIRouter(prefix="/audit")


@router.get("/events")
async def audit_events(
    limit: int = 100,
    action: str | None = None,
    tenant_id: str | None = None,
    user: User = Depends(require_superadmin),
    session: AsyncSession = Depends(get_session),
):
    stmt = (
        select(AuditEvent, Tenant.name.label("tenant_name"))
        .join(Tenant, AuditEvent.tenant_id == Tenant.id)
        .order_by(AuditEvent.created_at.desc())
        .limit(limit)
    )
    if action:
        stmt = stmt.where(AuditEvent.action == action)
    if tenant_id:
        import uuid
        stmt = stmt.where(AuditEvent.tenant_id == uuid.UUID(tenant_id))

    result = await session.execute(stmt)
    return [
        {
            "id": str(row.AuditEvent.id),
            "action": row.AuditEvent.action,
            "resource_type": row.AuditEvent.resource_type,
            "resource_id": str(row.AuditEvent.resource_id) if row.AuditEvent.resource_id else None,
            "user_id": str(row.AuditEvent.user_id) if row.AuditEvent.user_id else None,
            "details": row.AuditEvent.details,
            "tenant_name": row.tenant_name,
            "created_at": row.AuditEvent.created_at.isoformat(),
        }
        for row in result
    ]
