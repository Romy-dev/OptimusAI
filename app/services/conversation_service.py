"""Conversation service — manages the unified inbox and message flow."""

import uuid
from datetime import datetime, timezone

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors.base import NormalizedEvent
from app.core.exceptions import NotFoundError
from app.models.conversation import (
    Conversation,
    ConversationStatus,
    Message,
    MessageDirection,
)
from app.models.escalation import Escalation
from app.repositories.base import BaseRepository

logger = structlog.get_logger()


class ConversationRepository(BaseRepository[Conversation]):
    model = Conversation

    async def find_or_create(
        self,
        channel_id: uuid.UUID,
        brand_id: uuid.UUID,
        customer_external_id: str,
        platform: str,
        customer_name: str | None = None,
    ) -> tuple[Conversation, bool]:
        """Find existing open conversation or create a new one."""
        stmt = self._base_query().where(
            Conversation.channel_id == channel_id,
            Conversation.customer_external_id == customer_external_id,
            Conversation.status.notin_([
                ConversationStatus.CLOSED,
            ]),
        )
        result = await self.session.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            return existing, False

        conv = await self.create(
            channel_id=channel_id,
            brand_id=brand_id,
            customer_external_id=customer_external_id,
            customer_name=customer_name,
            platform=platform,
            status=ConversationStatus.OPEN,
        )
        return conv, True


class MessageRepository(BaseRepository[Message]):
    model = Message

    async def get_conversation_history(
        self, conversation_id: uuid.UUID, limit: int = 20
    ) -> list[Message]:
        stmt = (
            self._base_query()
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        messages = list(result.scalars().all())
        messages.reverse()  # Chronological order
        return messages


class EscalationRepository(BaseRepository[Escalation]):
    model = Escalation


class ConversationService:
    """Manages conversations, messages, and the support pipeline."""

    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID):
        self.session = session
        self.tenant_id = tenant_id
        self.conv_repo = ConversationRepository(session, tenant_id)
        self.msg_repo = MessageRepository(session, tenant_id)
        self.esc_repo = EscalationRepository(session, tenant_id)

    async def handle_inbound_message(
        self,
        *,
        channel_id: uuid.UUID,
        brand_id: uuid.UUID,
        event: NormalizedEvent,
    ) -> dict:
        """Process an incoming message through the full support pipeline.

        Returns dict with the action taken and any response sent.
        """
        # 1. Find or create conversation
        conv, is_new = await self.conv_repo.find_or_create(
            channel_id=channel_id,
            brand_id=brand_id,
            customer_external_id=event.author_id or "",
            platform=event.platform,
            customer_name=event.author_name,
        )

        # 2. Store the inbound message
        inbound_msg = await self.msg_repo.create(
            conversation_id=conv.id,
            direction=MessageDirection.INBOUND,
            content=event.content or "",
            content_type=event.content_type,
            media_url=event.media_url,
            external_message_id=event.external_id,
            platform=event.platform,
            status="received",
        )

        # Update conversation metadata
        conv.message_count = (conv.message_count or 0) + 1
        conv.last_message_at = datetime.now(timezone.utc)
        await self.session.flush()

        # 3. Check conversation status
        if conv.status == ConversationStatus.HUMAN_HANDLING:
            # Don't interfere — notify the assigned human agent
            logger.info(
                "message_for_human_agent",
                conversation_id=str(conv.id),
                assigned_to=str(conv.assigned_to),
            )
            return {
                "action": "forwarded_to_human",
                "conversation_id": conv.id,
                "message_id": inbound_msg.id,
            }

        if conv.status in (ConversationStatus.CLOSED, ConversationStatus.RESOLVED):
            # Reopen the conversation
            conv.status = ConversationStatus.OPEN
            await self.session.flush()

        # 4. Run AI support pipeline
        return await self._run_ai_support(conv, inbound_msg, brand_id)

    async def _run_ai_support(
        self,
        conversation: Conversation,
        inbound_msg: Message,
        brand_id: uuid.UUID,
    ) -> dict:
        """Run the AI support agent on the conversation."""
        from app.agents.registry import get_orchestrator
        from app.services.brand_service import BrandService
        from app.services.knowledge_service import KnowledgeService

        # Get brand context
        brand_service = BrandService(self.session, self.tenant_id)
        brand_context = await brand_service.get_channel_context(
            brand_id, conversation.platform
        )

        # Get conversation history
        history = await self.msg_repo.get_conversation_history(
            conversation.id, limit=10
        )
        history_dicts = [
            {
                "direction": m.direction.value,
                "content": m.content,
                "is_ai": m.is_ai_generated,
            }
            for m in history
        ]

        # Search knowledge base
        knowledge_service = KnowledgeService(self.session, self.tenant_id)
        knowledge_results = await knowledge_service.search(
            query=inbound_msg.content,
            brand_id=brand_id,
            top_k=3,
        )

        # Run orchestrator → support agent
        orchestrator = get_orchestrator()
        result = await orchestrator.execute({
            "task_type": "support_query",
            "brand_context": brand_context,
            "customer_message": inbound_msg.content,
            "conversation_history": history_dicts,
            "knowledge_results": knowledge_results,
            "channel": conversation.platform,
            "customer_name": conversation.customer_name,
            "conversation_id": str(conversation.id),
        })

        # 5. Handle result
        if result.should_escalate:
            return await self._handle_escalation(
                conversation, result, brand_context
            )

        confidence = result.confidence_score or 0.0
        response_text = result.output.get("response", "")

        # Get auto-reply threshold from tenant settings
        # TODO: Load from tenant settings
        auto_reply_threshold = 0.6

        if confidence >= auto_reply_threshold and response_text:
            # Auto-reply
            outbound_msg = await self.msg_repo.create(
                conversation_id=conversation.id,
                direction=MessageDirection.OUTBOUND,
                content=response_text,
                content_type="text",
                is_ai_generated=True,
                ai_confidence_score=confidence,
                platform=conversation.platform,
                status="pending",
                sources=result.output.get("sources", []),
            )

            conversation.status = ConversationStatus.AI_HANDLING
            await self.session.flush()

            return {
                "action": "auto_reply",
                "conversation_id": conversation.id,
                "message_id": outbound_msg.id,
                "response": response_text,
                "confidence": confidence,
                "sources": result.output.get("sources", []),
            }
        else:
            # Low confidence — save as draft, escalate
            return await self._handle_escalation(
                conversation, result, brand_context
            )

    async def _handle_escalation(
        self, conversation: Conversation, agent_result, brand_context: dict,
    ) -> dict:
        """Escalate to human support."""
        from app.agents.registry import get_orchestrator

        orchestrator = get_orchestrator()
        escalation_result = await orchestrator.execute({
            "task_type": "escalate_to_human",
            "brand_context": brand_context,
            "conversation_id": str(conversation.id),
            "escalation_reason": agent_result.escalation_reason or "low_confidence",
            "customer_name": conversation.customer_name,
            "channel": conversation.platform,
        })

        # Create escalation record
        escalation = await self.esc_repo.create(
            conversation_id=conversation.id,
            reason=agent_result.escalation_reason or "low_confidence",
            priority=escalation_result.output.get("priority", "medium"),
            ai_summary=escalation_result.output.get("escalation_summary", ""),
            ai_context={
                "last_confidence": agent_result.confidence_score,
                "last_output": agent_result.output,
            },
        )

        # Send customer message
        customer_msg = escalation_result.output.get(
            "customer_message",
            "Un de nos conseillers va prendre le relais. Merci de votre patience !"
        )
        outbound_msg = await self.msg_repo.create(
            conversation_id=conversation.id,
            direction=MessageDirection.OUTBOUND,
            content=customer_msg,
            content_type="text",
            is_ai_generated=True,
            platform=conversation.platform,
            status="pending",
        )

        conversation.status = ConversationStatus.ESCALATED
        await self.session.flush()

        # TODO: Notify human agents

        logger.info(
            "conversation_escalated",
            conversation_id=str(conversation.id),
            reason=agent_result.escalation_reason,
            priority=escalation_result.output.get("priority"),
        )

        return {
            "action": "escalated",
            "conversation_id": conversation.id,
            "escalation_id": escalation.id,
            "customer_message": customer_msg,
            "priority": escalation_result.output.get("priority", "medium"),
        }

    # === Inbox API methods ===

    async def list_conversations(
        self, status: str | None = None, limit: int = 20
    ) -> list[Conversation]:
        filters = {}
        if status:
            filters["status"] = status
        return await self.conv_repo.list(limit=limit, **filters)

    async def get_conversation(self, conv_id: uuid.UUID) -> Conversation:
        conv = await self.conv_repo.get_by_id(conv_id)
        if not conv:
            raise NotFoundError("Conversation not found")
        return conv

    async def get_messages(
        self, conv_id: uuid.UUID, limit: int = 50
    ) -> list[Message]:
        return await self.msg_repo.get_conversation_history(conv_id, limit=limit)

    async def send_human_message(
        self,
        conv_id: uuid.UUID,
        content: str,
        sent_by: uuid.UUID,
    ) -> Message:
        """Send a message as a human agent."""
        conv = await self.get_conversation(conv_id)
        msg = await self.msg_repo.create(
            conversation_id=conv_id,
            direction=MessageDirection.OUTBOUND,
            content=content,
            content_type="text",
            is_ai_generated=False,
            sent_by=sent_by,
            platform=conv.platform,
            status="pending",
        )

        if conv.status != ConversationStatus.HUMAN_HANDLING:
            conv.status = ConversationStatus.HUMAN_HANDLING
            conv.assigned_to = sent_by
            await self.session.flush()

        return msg

    async def close_conversation(self, conv_id: uuid.UUID) -> Conversation:
        conv = await self.get_conversation(conv_id)
        conv.status = ConversationStatus.CLOSED
        conv.resolved_at = datetime.now(timezone.utc)
        await self.session.flush()
        return conv
