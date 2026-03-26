import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.database import get_session
from app.core.permissions import RequirePermission
from app.models.user import User
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
async def list_pending_approvals(
    user: User = Depends(RequirePermission("approvals.read")),
    service: ContentService = Depends(get_content_service),
):
    approvals = await service.list_pending_approvals()
    return [
        {
            "id": a.id,
            "post_id": a.post_id,
            "requested_by": a.requested_by,
            "status": a.status,
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
