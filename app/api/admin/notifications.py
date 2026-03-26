"""Admin Notifications — broadcast messages to tenants via WebSocket."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.database import get_session
from app.models.user import User

router = APIRouter(prefix="/notifications", tags=["admin-notifications"])


def _require_superadmin(user: User = Depends(get_current_user)) -> User:
    if not user.is_superadmin:
        from fastapi import HTTPException
        raise HTTPException(403, "Superadmin required")
    return user


class BroadcastRequest(BaseModel):
    message: str
    title: str = "Notification"
    target_tenant_id: str | None = None  # None = broadcast to all
    level: str = "info"  # info, warning, success, error


@router.post("/broadcast")
async def broadcast_notification(
    payload: BroadcastRequest,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(_require_superadmin),
):
    """Send a notification to all connected users or a specific tenant."""
    from app.core.websocket import ws_manager

    notification = {
        "type": "admin_broadcast",
        "title": payload.title,
        "message": payload.message,
        "level": payload.level,
        "from": "admin",
    }

    sent_count = 0

    if payload.target_tenant_id:
        sent_count = await ws_manager.send_to_tenant(
            payload.target_tenant_id, notification
        )
    else:
        sent_count = await ws_manager.broadcast(notification)

    return {
        "success": True,
        "sent_to": sent_count,
        "target": payload.target_tenant_id or "all",
    }


@router.get("/history")
async def notification_history(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(_require_superadmin),
):
    """Get recent broadcast notification history from audit log."""
    from sqlalchemy import select
    from app.models.audit import AuditEvent

    result = await session.execute(
        select(AuditEvent)
        .where(AuditEvent.action == "admin_broadcast")
        .order_by(AuditEvent.created_at.desc())
        .limit(50)
    )
    events = result.scalars().all()
    return [
        {
            "id": str(e.id),
            "message": e.metadata_.get("message", "") if e.metadata_ else "",
            "target": e.metadata_.get("target", "all") if e.metadata_ else "all",
            "sent_to": e.metadata_.get("sent_to", 0) if e.metadata_ else 0,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        }
        for e in events
    ]
