"""Scheduled post publisher — checks for posts due and publishes them."""

import asyncio
from datetime import datetime, timezone

import structlog
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_factory
from app.core.queue import enqueue
from app.models.post import Post, PostStatus

logger = structlog.get_logger()


async def check_scheduled_posts(_ctx: dict) -> None:
    """Periodically check for posts scheduled to publish now.

    Runs every 60 seconds via ARQ cron.
    """
    async with async_session_factory() as session:
        now = datetime.now(timezone.utc)

        # Find posts that are scheduled and past their publish time
        stmt = (
            select(Post)
            .where(
                Post.status == PostStatus.SCHEDULED,
                Post.scheduled_at <= now,
            )
            .limit(50)
        )
        result = await session.execute(stmt)
        posts = result.scalars().all()

        if not posts:
            return

        logger.info("scheduler_found_posts", count=len(posts))

        for post in posts:
            try:
                # Mark as publishing
                post.status = PostStatus.PUBLISHING
                await session.flush()

                # Enqueue the actual publishing job
                await enqueue("publish_post", str(post.id), str(post.tenant_id))

                logger.info(
                    "scheduler_queued_post",
                    post_id=str(post.id),
                    scheduled_at=str(post.scheduled_at),
                )
            except Exception as e:
                logger.error("scheduler_post_failed", post_id=str(post.id), error=str(e))
                post.status = PostStatus.FAILED

        await session.commit()
