"""Content service — orchestrates post generation, moderation, and approval."""

import uuid
from datetime import datetime, timezone

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.agents.registry import get_orchestrator
from app.core.exceptions import InvalidInputError, NotFoundError
from app.models.post import Post, PostStatus, PostAsset
from app.models.approval import Approval
from app.repositories.base import BaseRepository
from app.services.brand_service import BrandService

logger = structlog.get_logger()


class PostRepository(BaseRepository[Post]):
    model = Post

    def _base_query(self):
        return (
            select(self.model)
            .where(self.model.tenant_id == self.tenant_id)
            .options(selectinload(Post.assets))
        )

    async def create(self, **kwargs) -> Post:
        """Override to eager-load assets after creation."""
        post = await super().create(**kwargs)
        # Re-fetch with selectinload so assets is an empty list, not lazy
        return await self.get_by_id(post.id) or post


class ApprovalRepository(BaseRepository[Approval]):
    model = Approval


class PostAssetRepository(BaseRepository[PostAsset]):
    model = PostAsset


class ContentService:
    """Manages the full lifecycle: generate → moderate → approve → publish."""

    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID):
        self.session = session
        self.tenant_id = tenant_id
        self.post_repo = PostRepository(session, tenant_id)
        self.approval_repo = ApprovalRepository(session, tenant_id)
        self.asset_repo = PostAssetRepository(session, tenant_id)
        self.brand_service = BrandService(session, tenant_id)

    # === Generation ===

    async def generate_post(
        self,
        *,
        brand_id: uuid.UUID,
        brief: str,
        channels: list[str],
        created_by: uuid.UUID,
        campaign_id: uuid.UUID | None = None,
        objective: str = "engagement",
        language: str = "fr",
        scheduled_at: datetime | None = None,
        generate_image: bool = False,
    ) -> Post:
        """Generate a post using the AI copywriter agent."""
        # Get brand context
        brand_context = await self.brand_service.get_brand_with_profile(brand_id)

        # For each channel, generate adapted content
        channel_variants = {}
        main_content = ""
        main_hashtags = []
        main_confidence = 0.0

        orchestrator = get_orchestrator()

        for channel in channels:
            channel_context = await self.brand_service.get_channel_context(brand_id, channel)
            result = await orchestrator.execute({
                "task_type": "generate_post",
                "brand_context": channel_context,
                "brief": brief,
                "channel": channel,
                "objective": objective,
            })

            if result.success:
                content = result.output.get("content", "")
                channel_variants[channel] = content
                if not main_content:
                    main_content = content
                    main_hashtags = result.output.get("hashtags", [])
                    main_confidence = result.confidence_score or 0.0
                    media_suggestion = result.output.get("media_suggestion", "")
            else:
                logger.warning(
                    "generation_failed_for_channel",
                    channel=channel,
                    error=result.output,
                )

        if not main_content:
            raise InvalidInputError("Failed to generate content for any channel")

        # Moderate the content
        moderation_result = await orchestrator.execute({
            "task_type": "moderate_content",
            "content": main_content,
            "content_type": "post",
            "brand_context": brand_context,
        })

        moderation_approved = moderation_result.output.get("approved", False)
        moderation_flags = moderation_result.output.get("flags", [])

        # Determine initial status
        if not moderation_approved:
            status = PostStatus.REJECTED if moderation_result.output.get("action") == "blocked" else PostStatus.DRAFT
        elif main_confidence >= 0.85:
            status = PostStatus.PENDING_REVIEW  # High confidence, ready for review
        else:
            status = PostStatus.DRAFT

        # Create the post
        target_channels = [{"channel": ch} for ch in channels]
        post = await self.post_repo.create(
            brand_id=brand_id,
            campaign_id=campaign_id,
            created_by=created_by,
            content_text=main_content,
            hashtags=main_hashtags,
            channel_variants=channel_variants,
            status=status,
            scheduled_at=scheduled_at,
            target_channels=target_channels,
            ai_generated=True,
            ai_confidence_score=main_confidence,
            generation_prompt=brief,
        )

        # Generate image if requested
        if generate_image and media_suggestion:
            image_result = await orchestrator.execute({
                "task_type": "generate_image",
                "brand_context": brand_context,
                "media_suggestion": media_suggestion,
                "aspect_ratio": "1:1",
            })
            if image_result.success:
                await self.asset_repo.create(
                    post_id=post.id,
                    asset_type="image",
                    file_url=image_result.output["image_url"],
                    ai_generated=True,
                    generation_prompt=image_result.output.get("prompt"),
                    metadata_={
                        "filename": image_result.output.get("filename"),
                        "s3_key": image_result.output.get("s3_key"),
                    }
                )
                logger.info("post_image_generated", post_id=str(post.id), url=image_result.output["image_url"])

        # If ready for review, create approval request
        if status == PostStatus.PENDING_REVIEW:
            await self.approval_repo.create(
                post_id=post.id,
                requested_by=created_by,
                status="pending",
            )

        logger.info(
            "post_generated",
            post_id=str(post.id),
            status=status.value,
            confidence=main_confidence,
            channels=channels,
            moderation_flags=moderation_flags,
        )
        return post

    # === Manual post creation ===

    async def create_manual_post(
        self,
        *,
        brand_id: uuid.UUID,
        content_text: str,
        created_by: uuid.UUID,
        hashtags: list[str] | None = None,
        target_channels: list[dict] | None = None,
        campaign_id: uuid.UUID | None = None,
        scheduled_at: datetime | None = None,
    ) -> Post:
        return await self.post_repo.create(
            brand_id=brand_id,
            campaign_id=campaign_id,
            created_by=created_by,
            content_text=content_text,
            hashtags=hashtags or [],
            target_channels=target_channels or [],
            status=PostStatus.DRAFT,
            scheduled_at=scheduled_at,
            ai_generated=False,
        )

    # === Approval Workflow ===

    async def submit_for_review(
        self, post_id: uuid.UUID, requested_by: uuid.UUID
    ) -> Approval:
        """Submit a post for human review."""
        post = await self.post_repo.get_by_id(post_id)
        if not post:
            raise NotFoundError("Post not found")

        await self.post_repo.update(post_id, status=PostStatus.PENDING_REVIEW)
        approval = await self.approval_repo.create(
            post_id=post_id,
            requested_by=requested_by,
            status="pending",
        )
        return approval

    async def approve_post(
        self,
        approval_id: uuid.UUID,
        reviewed_by: uuid.UUID,
        note: str | None = None,
    ) -> Post:
        """Approve a post for publication."""
        approval = await self.approval_repo.get_by_id(approval_id)
        if not approval:
            raise NotFoundError("Approval not found")

        now = datetime.now(timezone.utc)
        await self.approval_repo.update(
            approval_id,
            status="approved",
            reviewed_by=reviewed_by,
            reviewed_at=now,
            review_note=note,
        )

        post = await self.post_repo.get_by_id(approval.post_id)
        if not post:
            raise NotFoundError("Post not found")

        # If scheduled, mark as scheduled; otherwise mark approved
        new_status = PostStatus.SCHEDULED if post.scheduled_at else PostStatus.APPROVED
        await self.post_repo.update(approval.post_id, status=new_status)

        logger.info(
            "post_approved",
            post_id=str(approval.post_id),
            reviewed_by=str(reviewed_by),
            new_status=new_status.value,
        )
        return await self.post_repo.get_by_id(approval.post_id)

    async def reject_post(
        self,
        approval_id: uuid.UUID,
        reviewed_by: uuid.UUID,
        note: str,
    ) -> Post:
        """Reject a post with mandatory feedback."""
        if not note:
            raise InvalidInputError("Rejection note is required")

        approval = await self.approval_repo.get_by_id(approval_id)
        if not approval:
            raise NotFoundError("Approval not found")

        now = datetime.now(timezone.utc)
        await self.approval_repo.update(
            approval_id,
            status="rejected",
            reviewed_by=reviewed_by,
            reviewed_at=now,
            review_note=note,
        )
        await self.post_repo.update(approval.post_id, status=PostStatus.REJECTED)

        logger.info(
            "post_rejected",
            post_id=str(approval.post_id),
            reviewed_by=str(reviewed_by),
        )
        return await self.post_repo.get_by_id(approval.post_id)

    async def list_pending_approvals(self) -> list[Approval]:
        return await self.approval_repo.list(status="pending")
