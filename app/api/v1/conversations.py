"""Unified inbox API — conversations, messages, escalations."""

import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.database import get_session
from app.core.permissions import RequirePermission
from app.models.user import User
from app.services.conversation_service import ConversationService

router = APIRouter(prefix="/conversations", tags=["conversations"])


class SendMessageRequest(BaseModel):
    content: str = Field(min_length=1, max_length=4096)


def get_conversation_service(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> ConversationService:
    return ConversationService(session, tenant_id=user.tenant_id)


@router.get("")
async def list_conversations(
    status: str | None = None,
    user: User = Depends(RequirePermission("conversations.read")),
    service: ConversationService = Depends(get_conversation_service),
):
    convs = await service.list_conversations(status=status)
    return [
        {
            "id": c.id,
            "customer_name": c.customer_name,
            "platform": c.platform,
            "status": c.status.value,
            "message_count": c.message_count,
            "last_message_at": c.last_message_at,
            "sentiment": c.sentiment,
            "assigned_to": c.assigned_to,
            "tags": c.tags,
            "created_at": c.created_at,
        }
        for c in convs
    ]


@router.get("/{conv_id}")
async def get_conversation(
    conv_id: uuid.UUID,
    user: User = Depends(RequirePermission("conversations.read")),
    service: ConversationService = Depends(get_conversation_service),
):
    conv = await service.get_conversation(conv_id)
    return {
        "id": conv.id,
        "customer_name": conv.customer_name,
        "customer_phone": conv.customer_phone,
        "platform": conv.platform,
        "status": conv.status.value,
        "message_count": conv.message_count,
        "last_message_at": conv.last_message_at,
        "sentiment": conv.sentiment,
        "assigned_to": conv.assigned_to,
        "tags": conv.tags,
        "created_at": conv.created_at,
    }


@router.get("/{conv_id}/messages")
async def get_messages(
    conv_id: uuid.UUID,
    user: User = Depends(RequirePermission("conversations.read")),
    service: ConversationService = Depends(get_conversation_service),
):
    messages = await service.get_messages(conv_id)
    return [
        {
            "id": m.id,
            "direction": m.direction.value,
            "content": m.content,
            "content_type": m.content_type,
            "is_ai_generated": m.is_ai_generated,
            "ai_confidence_score": m.ai_confidence_score,
            "sent_by": m.sent_by,
            "status": m.status,
            "sources": m.sources,
            "created_at": m.created_at,
        }
        for m in messages
    ]


@router.post("/{conv_id}/messages")
async def send_message(
    conv_id: uuid.UUID,
    body: SendMessageRequest,
    user: User = Depends(RequirePermission("conversations.reply")),
    service: ConversationService = Depends(get_conversation_service),
):
    """Send a message as a human agent and deliver via connector."""
    msg = await service.send_human_message(
        conv_id=conv_id,
        content=body.content,
        sent_by=user.id,
    )

    # Deliver via the platform connector asynchronously
    conv = await service.get_conversation(conv_id)
    from app.core.queue import enqueue
    await enqueue(
        "deliver_human_message",
        str(msg.id),
        str(conv.id),
        str(user.tenant_id),
    )

    return {
        "id": msg.id,
        "content": msg.content,
        "status": "pending_delivery",
    }


@router.post("/{conv_id}/close")
async def close_conversation(
    conv_id: uuid.UUID,
    user: User = Depends(RequirePermission("conversations.reply")),
    service: ConversationService = Depends(get_conversation_service),
):
    conv = await service.close_conversation(conv_id)
    return {"id": conv.id, "status": conv.status.value}


@router.post("/{conv_id}/escalate")
async def manual_escalate(
    conv_id: uuid.UUID,
    user: User = Depends(RequirePermission("escalations.manage")),
    service: ConversationService = Depends(get_conversation_service),
):
    """Manually escalate a conversation."""
    conv = await service.get_conversation(conv_id)
    from app.agents.base import AgentResult
    dummy_result = AgentResult(
        success=False,
        output={},
        should_escalate=True,
        escalation_reason="manual_escalation",
        agent_name="human",
    )
    result = await service._handle_escalation(conv, dummy_result, {})
    return result
