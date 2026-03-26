"""Worker: process incoming webhook events from social platforms."""

import asyncio
import uuid

import structlog
from sqlalchemy import select

logger = structlog.get_logger()


async def process_facebook_webhook(ctx: dict, payload: dict) -> dict:
    """ARQ task: process a Facebook/Messenger webhook payload."""
    from app.connectors.facebook import FacebookConnector
    return await _process_social_webhook(payload, "facebook")


async def process_whatsapp_webhook(ctx: dict, payload: dict) -> dict:
    """ARQ task: process a WhatsApp webhook payload."""
    from app.connectors.whatsapp import WhatsAppConnector
    return await _process_social_webhook(payload, "whatsapp")


async def _process_social_webhook(payload: dict, platform: str) -> dict:
    """Generic webhook processing: parse → normalize → route to handler."""
    from app.connectors.facebook import FacebookConnector
    from app.connectors.whatsapp import WhatsAppConnector
    from app.core.database import async_session_factory
    from app.models.social_account import SocialAccount, Channel

    # Parse events using the right connector
    if platform == "facebook":
        connector = FacebookConnector(page_id="", access_token="")
        events = connector.parse_webhook(payload)
    elif platform == "whatsapp":
        connector = WhatsAppConnector(phone_number_id="", access_token="")
        events = connector.parse_webhook(payload)
    else:
        return {"status": "error", "reason": f"unknown_platform:{platform}"}

    if not events:
        return {"status": "ok", "events_processed": 0}

    logger.info("webhook_events_parsed", platform=platform, count=len(events))

    processed = 0
    errors = []

    async with async_session_factory() as session:
        for event in events:
            try:
                # Find the social account by platform_account_id
                stmt = select(SocialAccount).where(
                    SocialAccount.platform_account_id == event.account_id,
                    SocialAccount.is_active.is_(True),
                )
                result = await session.execute(stmt)
                account = result.scalar_one_or_none()

                if not account:
                    logger.warning(
                        "webhook_account_not_found",
                        account_id=event.account_id,
                        platform=platform,
                    )
                    continue

                tenant_id = account.tenant_id
                brand_id = account.brand_id

                # Find or get the channel
                channel_type = "whatsapp" if platform == "whatsapp" else (
                    "messenger" if event.event_type == "message" else "feed"
                )
                ch_stmt = select(Channel).where(
                    Channel.social_account_id == account.id,
                    Channel.channel_type == channel_type,
                )
                ch_result = await session.execute(ch_stmt)
                channel = ch_result.scalar_one_or_none()

                if not channel:
                    # Auto-create channel
                    channel = Channel(
                        tenant_id=tenant_id,
                        social_account_id=account.id,
                        channel_type=channel_type,
                        is_active=True,
                    )
                    session.add(channel)
                    await session.flush()

                # Route based on event type
                if event.event_type == "message":
                    await _handle_message_event(
                        session, event, channel.id, brand_id, tenant_id
                    )
                elif event.event_type == "comment":
                    await _handle_comment_event(
                        session, event, tenant_id, brand_id, account
                    )
                elif event.event_type == "status_update":
                    await _handle_status_event(session, event)
                else:
                    logger.debug("webhook_event_ignored", event_type=event.event_type)

                processed += 1

            except Exception as e:
                logger.exception("webhook_event_error", event_id=event.external_id)
                errors.append(str(e))

        await session.commit()

    logger.info(
        "webhook_processing_done",
        platform=platform,
        processed=processed,
        errors=len(errors),
    )
    return {"status": "ok", "events_processed": processed, "errors": errors}


async def _handle_message_event(session, event, channel_id, brand_id, tenant_id):
    """Route an inbound message to the conversation service."""
    from app.services.conversation_service import ConversationService

    service = ConversationService(session, tenant_id=tenant_id)
    result = await service.handle_inbound_message(
        channel_id=channel_id,
        brand_id=brand_id,
        event=event,
    )

    # If the AI generated a reply, send it via the connector
    if result.get("action") == "auto_reply":
        await _deliver_outbound_message(
            session=session,
            message_id=result["message_id"],
            tenant_id=tenant_id,
            platform=event.platform,
            recipient_id=event.author_id,
            content=result["response"],
        )

    logger.info(
        "message_handled",
        action=result.get("action"),
        conversation_id=str(result.get("conversation_id")),
    )


async def _deliver_outbound_message(
    session, message_id, tenant_id, platform, recipient_id, content
):
    """Actually send a message via the platform connector."""
    from app.core.security import secret_manager
    from app.models.conversation import Message
    from app.models.social_account import SocialAccount
    from sqlalchemy import select

    # Find active account for this platform + tenant
    stmt = select(SocialAccount).where(
        SocialAccount.tenant_id == tenant_id,
        SocialAccount.platform == platform,
        SocialAccount.is_active.is_(True),
    )
    result = await session.execute(stmt)
    account = result.scalar_one_or_none()

    if not account:
        logger.error("no_account_for_delivery", platform=platform, tenant=str(tenant_id))
        return

    token = secret_manager.decrypt(account.access_token_encrypted)

    # Instantiate connector and send
    from app.workers.publishing import _get_connector
    connector = _get_connector(platform, account.platform_account_id, token)

    try:
        send_result = await connector.send_message(
            recipient_id=recipient_id,
            content=content,
        )

        # Update message status
        msg_stmt = select(Message).where(Message.id == message_id)
        msg_result = await session.execute(msg_stmt)
        msg = msg_result.scalar_one_or_none()
        if msg:
            if send_result.success:
                msg.status = "sent"
                msg.external_message_id = send_result.external_id
            else:
                msg.status = "failed"
                msg.error_message = send_result.error
            await session.flush()

        logger.info(
            "message_delivered",
            platform=platform,
            success=send_result.success,
            external_id=send_result.external_id,
        )

    except Exception as e:
        logger.exception("message_delivery_failed", platform=platform)


async def _handle_comment_event(session, event, tenant_id, brand_id=None, account=None):
    """Store incoming comment and auto-reply using SocialReplyAgent if enabled."""
    from app.models.comment import Comment
    from app.models.post import Post
    from app.services.feature_flag_service import is_enabled
    from sqlalchemy import select

    # Find the post by external_id
    if event.parent_id:
        stmt = select(Post).where(
            Post.tenant_id == tenant_id,
        )
        result = await session.execute(stmt)
        # Try to match by external_ids JSONB
        # For now, just store the comment
        pass

    comment = Comment(
        tenant_id=tenant_id,
        post_id=None,  # TODO: match to internal post
        platform=event.platform,
        external_comment_id=event.external_id,
        author_name=event.author_name,
        author_external_id=event.author_id,
        content=event.content or "",
        commented_at=event.timestamp,
    )
    session.add(comment)
    await session.flush()

    logger.info("comment_stored", external_id=event.external_id, platform=event.platform)

    # === Auto-reply logic ===

    # Skip if the comment is from the page itself (don't reply to ourselves)
    if account and event.author_id == account.platform_account_id:
        logger.debug("comment_from_own_page, skipping auto-reply", external_id=event.external_id)
        return

    # Check feature flag
    if not await is_enabled("auto_reply", str(tenant_id), session):
        logger.debug("auto_reply_disabled", tenant_id=str(tenant_id))
        return

    # Skip if no comment text
    if not event.content or not event.content.strip():
        return

    try:
        from app.agents.registry import get_orchestrator
        from app.services.brand_service import BrandService
        from app.services.audit_service import AuditService
        from app.core.security import secret_manager

        # Get brand context for the agent
        brand_ctx = {}
        if brand_id:
            try:
                brand_svc = BrandService(session, tenant_id)
                brand_ctx = await brand_svc.get_brand_with_profile(brand_id)
            except Exception:
                logger.warning("auto_reply_brand_context_failed", brand_id=str(brand_id))

        # Run the SocialReplyAgent
        orchestrator = get_orchestrator()
        reply_agent = orchestrator.agents.get("social_reply")
        if not reply_agent:
            logger.error("social_reply_agent_not_found")
            return

        result = await reply_agent.run({
            "comment_text": event.content,
            "post_content": "",
            "brand_context": brand_ctx,
            "platform": event.platform,
            "customer_name": event.author_name or "",
        })

        if not result.success:
            logger.warning("auto_reply_agent_failed", output=result.output)
            return

        reply_text = result.output.get("reply_text", "")
        action = result.output.get("action", "reply")

        # Don't post a reply if action is "hide" or no text
        if action == "hide" or not reply_text or not reply_text.strip():
            logger.info(
                "auto_reply_skipped",
                action=action,
                comment_type=result.output.get("comment_type"),
                external_id=event.external_id,
            )
            return

        # Add a 3-second delay before replying (to seem more natural)
        await asyncio.sleep(3)

        # Post the reply via the Facebook connector
        if account and event.platform == "facebook":
            token = secret_manager.decrypt(account.access_token_encrypted)
            from app.connectors.facebook import FacebookConnector
            fb_connector = FacebookConnector(
                page_id=account.platform_account_id,
                access_token=token,
            )
            publish_result = await fb_connector.reply_to_comment(
                comment_id=event.external_id,
                content=reply_text,
            )

            if publish_result.success:
                logger.info(
                    "auto_reply_posted",
                    comment_id=event.external_id,
                    reply_id=publish_result.external_id,
                    comment_type=result.output.get("comment_type"),
                )
            else:
                logger.error(
                    "auto_reply_post_failed",
                    comment_id=event.external_id,
                    error=publish_result.error,
                )
                return

            # Log the auto-reply in the audit
            audit = AuditService(session)
            await audit.log(
                tenant_id=tenant_id,
                action="comment.auto_reply",
                resource_type="comment",
                resource_id=comment.id if hasattr(comment, "id") else None,
                metadata={
                    "comment_external_id": event.external_id,
                    "reply_external_id": publish_result.external_id,
                    "comment_type": result.output.get("comment_type"),
                    "reply_text": reply_text[:500],
                    "confidence": result.confidence_score,
                    "model_used": result.model_used,
                    "platform": event.platform,
                },
            )

    except Exception as e:
        logger.exception(
            "auto_reply_error",
            comment_id=event.external_id,
            error=str(e),
        )


async def _handle_status_event(session, event):
    """Update message delivery status (sent/delivered/read)."""
    from app.models.conversation import Message
    from sqlalchemy import select

    if not event.external_id:
        return

    stmt = select(Message).where(Message.external_message_id == event.external_id)
    result = await session.execute(stmt)
    msg = result.scalar_one_or_none()

    if msg and event.content:
        status_map = {"sent": "sent", "delivered": "delivered", "read": "read", "failed": "failed"}
        new_status = status_map.get(event.content, msg.status)
        if new_status != msg.status:
            msg.status = new_status
            await session.flush()
            logger.debug("message_status_updated", msg_id=str(msg.id), status=new_status)
