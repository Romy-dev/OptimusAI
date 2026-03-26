import uuid

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.database import get_session
from app.core.permissions import RequirePermission
from app.models.user import User
from app.models.approval import Approval
from app.services.content_service import ContentService

router = APIRouter(prefix="/approvals", tags=["approvals"])


class ApproveRequest(BaseModel):
    note: str | None = None


class RejectRequest(BaseModel):
    note: str = Field(min_length=5, description="Rejection reason is required")


def get_content_service(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> ContentService:
    return ContentService(session, tenant_id=user.tenant_id)


@router.get("")
async def list_approvals(
    status: str | None = Query(None, description="Filter by status: pending, approved, rejected"),
    user: User = Depends(RequirePermission("approvals.read")),
    service: ContentService = Depends(get_content_service),
    session: AsyncSession = Depends(get_session),
):
    """List approvals. Without status filter, returns pending. With status=all, returns all."""
    if status and status != "all":
        stmt = (
            select(Approval)
            .where(Approval.tenant_id == user.tenant_id, Approval.status == status)
            .order_by(Approval.created_at.desc())
            .limit(100)
        )
        result = await session.execute(stmt)
        approvals = result.scalars().all()
    elif status == "all":
        stmt = (
            select(Approval)
            .where(Approval.tenant_id == user.tenant_id)
            .order_by(Approval.created_at.desc())
            .limit(100)
        )
        result = await session.execute(stmt)
        approvals = result.scalars().all()
    else:
        approvals = await service.list_pending_approvals()

    return [
        {
            "id": a.id,
            "post_id": a.post_id,
            "requested_by": a.requested_by,
            "reviewed_by": getattr(a, "reviewed_by", None),
            "status": a.status,
            "review_note": getattr(a, "review_note", None),
            "reviewed_at": getattr(a, "reviewed_at", None),
            "created_at": a.created_at,
        }
        for a in approvals
    ]


@router.post("/{approval_id}/approve")
async def approve(
    approval_id: uuid.UUID,
    body: ApproveRequest | None = None,
    user: User = Depends(RequirePermission("approvals.review")),
    service: ContentService = Depends(get_content_service),
):
    post = await service.approve_post(
        approval_id=approval_id,
        reviewed_by=user.id,
        note=body.note if body else None,
    )
    return {"status": "approved", "post_id": post.id, "post_status": post.status.value}


@router.post("/{approval_id}/reject")
async def reject(
    approval_id: uuid.UUID,
    body: RejectRequest,
    user: User = Depends(RequirePermission("approvals.review")),
    service: ContentService = Depends(get_content_service),
):
    post = await service.reject_post(
        approval_id=approval_id,
        reviewed_by=user.id,
        note=body.note,
    )
    return {"status": "rejected", "post_id": post.id, "rejection_note": body.note}
