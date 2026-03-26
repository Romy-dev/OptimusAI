"""Worker: deliver outbound messages via social platform connectors."""

import uuid

import structlog
from sqlalchemy import select

logger = structlog.get_logger()


async def deliver_human_message(
    ctx: dict, message_id: str, conversation_id: str, tenant_id: str
) -> dict:
    """ARQ task: send a human agent's message to the customer via the platform connector."""
    from app.core.database import async_session_factory
    from app.core.security import secret_manager
    from app.models.conversation import Conversation, Message
    from app.models.social_account import SocialAccount, Channel
    from app.workers.publishing import _get_connector

    msg_uuid = uuid.UUID(message_id)
    conv_uuid = uuid.UUID(conversation_id)
    tenant_uuid = uuid.UUID(tenant_id)

    async with async_session_factory() as session:
        try:
            # Load message and conversation
            msg = (await session.execute(
                select(Message).where(Message.id == msg_uuid)
            )).scalar_one_or_none()

            conv = (await session.execute(
                select(Conversation).where(
                    Conversation.id == conv_uuid,
                    Conversation.tenant_id == tenant_uuid,
                )
            )).scalar_one_or_none()

            if not msg or not conv:
                return {"status": "error", "reason": "message_or_conversation_not_found"}

            # Find the social account for this platform
            channel = (await session.execute(
                select(Channel).where(Channel.id == conv.channel_id)
            )).scalar_one_or_none()

            if not channel:
                return {"status": "error", "reason": "channel_not_found"}

            account = (await session.execute(
                select(SocialAccount).where(
                    SocialAccount.id == channel.social_account_id,
                    SocialAccount.is_active.is_(True),
                )
            )).scalar_one_or_none()

            if not account:
                msg.status = "failed"
                msg.error_message = "No active social account found"
                await session.commit()
                return {"status": "error", "reason": "no_active_account"}

            # Decrypt token and send
            token = secret_manager.decrypt(account.access_token_encrypted)
            connector = _get_connector(conv.platform, account.platform_account_id, token)

            result = await connector.send_message(
                recipient_id=conv.customer_external_id,
                content=msg.content,
                content_type=msg.content_type,
                media_url=msg.media_url,
            )

            if result.success:
                msg.status = "sent"
                msg.external_message_id = result.external_id
            else:
                msg.status = "failed"
                msg.error_message = result.error

            await session.commit()

            logger.info(
                "human_message_delivered",
                message_id=message_id,
                platform=conv.platform,
                success=result.success,
            )
            return {"status": msg.status, "external_id": result.external_id}

        except Exception as e:
            logger.exception("message_delivery_failed", message_id=message_id)
            try:
                if msg:
                    msg.status = "failed"
                    msg.error_message = str(e)
                    await session.commit()
            except Exception:
                pass
            return {"status": "error", "reason": str(e)}
