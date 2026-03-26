"""Worker: publish posts to social platforms."""

import uuid
from datetime import datetime, timezone

import structlog

logger = structlog.get_logger()


async def publish_post(ctx: dict, post_id: str, tenant_id: str) -> dict:
    """ARQ task: publish an approved post to its target social channels."""
    from app.core.database import async_session_factory
    from app.core.security import secret_manager
    from app.models.post import Post, PostStatus
    from app.models.social_account import SocialAccount
    from sqlalchemy import select

    post_uuid = uuid.UUID(post_id)
    tenant_uuid = uuid.UUID(tenant_id)

    logger.info("publish_started", post_id=post_id)

    async with async_session_factory() as session:
        try:
            # Load post
            stmt = select(Post).where(
                Post.id == post_uuid,
                Post.tenant_id == tenant_uuid,
            )
            result = await session.execute(stmt)
            post = result.scalar_one_or_none()

            if not post:
                return {"status": "error", "reason": "post_not_found"}

            if post.status not in (PostStatus.APPROVED, PostStatus.SCHEDULED):
                return {"status": "error", "reason": f"invalid_status:{post.status.value}"}

            post.status = PostStatus.PUBLISHING
            await session.commit()

            external_ids = {}
            errors = []

            # Publish to each target channel
            for target in post.target_channels:
                channel_name = target.get("channel", "")
                social_account_id = target.get("social_account_id")

                if not social_account_id:
                    # Find first active account for this platform
                    sa_stmt = select(SocialAccount).where(
                        SocialAccount.tenant_id == tenant_uuid,
                        SocialAccount.brand_id == post.brand_id,
                        SocialAccount.platform == channel_name,
                        SocialAccount.is_active.is_(True),
                    )
                    sa_result = await session.execute(sa_stmt)
                    account = sa_result.scalar_one_or_none()
                else:
                    sa_stmt = select(SocialAccount).where(
                        SocialAccount.id == uuid.UUID(social_account_id),
                        SocialAccount.tenant_id == tenant_uuid,
                    )
                    sa_result = await session.execute(sa_stmt)
                    account = sa_result.scalar_one_or_none()

                if not account:
                    errors.append(f"No active {channel_name} account found")
                    continue

                # Get content for this channel
                content = post.channel_variants.get(channel_name, post.content_text or "")
                token = secret_manager.decrypt(account.access_token_encrypted)

                # Select connector
                try:
                    connector = _get_connector(channel_name, account.platform_account_id, token)
                    pub_result = await connector.publish_post(content=content)

                    if pub_result.success:
                        external_ids[f"{channel_name}:{account.platform_account_id}"] = pub_result.external_id
                        logger.info("channel_published", channel=channel_name, ext_id=pub_result.external_id)
                    else:
                        errors.append(f"{channel_name}: {pub_result.error}")
                        logger.warning("channel_publish_failed", channel=channel_name, error=pub_result.error)

                except Exception as e:
                    errors.append(f"{channel_name}: {str(e)}")
                    logger.exception("connector_error", channel=channel_name)

            # Update post status
            if external_ids:
                post.status = PostStatus.PUBLISHED
                post.published_at = datetime.now(timezone.utc)
                post.external_ids = external_ids
            elif errors:
                post.status = PostStatus.FAILED
            else:
                post.status = PostStatus.FAILED

            await session.commit()

            logger.info(
                "publish_completed",
                post_id=post_id,
                status=post.status.value,
                published_to=list(external_ids.keys()),
                errors=errors,
            )

            # Notify frontend via WebSocket
            try:
                from app.core.websocket import notify
                await notify(
                    tenant_id=tenant_id,
                    event_type="post_published",
                    data={
                        "post_id": post_id,
                        "status": post.status.value,
                        "published_to": list(external_ids.keys()),
                        "errors": errors,
                        "message": f"Post {'publié' if external_ids else 'échoué'}",
                    },
                )
            except Exception:
                pass  # WS is best-effort

            return {
                "status": post.status.value,
                "external_ids": external_ids,
                "errors": errors,
            }

        except Exception as e:
            logger.exception("publish_failed", post_id=post_id)
            try:
                post.status = PostStatus.FAILED
                await session.commit()
            except Exception:
                pass
            return {"status": "error", "reason": str(e)}


def _get_connector(platform: str, account_id: str, token: str):
    """Instantiate the right connector for the platform."""
    if platform == "facebook":
        from app.connectors.facebook import FacebookConnector
        return FacebookConnector(page_id=account_id, access_token=token)
    elif platform == "whatsapp":
        from app.connectors.whatsapp import WhatsAppConnector
        return WhatsAppConnector(phone_number_id=account_id, access_token=token)
    else:
        raise ValueError(f"Unsupported platform: {platform}")
