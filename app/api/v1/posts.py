import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.database import get_session
from app.core.exceptions import NotFoundError
from app.core.permissions import RequirePermission
from app.models.user import User
from app.schemas.post import (
    AttachImageRequest,
    PostCreate,
    PostGenerateRequest,
    PostResponse,
    PostUpdate,
)
from app.core.queue import enqueue
from app.services.content_service import ContentService
from app.services.quota_service import QuotaService

router = APIRouter(prefix="/posts", tags=["posts"])


def get_content_service(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> ContentService:
    return ContentService(session, tenant_id=user.tenant_id)


@router.get("", response_model=list[PostResponse])
async def list_posts(
    brand_id: uuid.UUID | None = None,
    status: str | None = None,
    user: User = Depends(RequirePermission("posts.read")),
    service: ContentService = Depends(get_content_service),
):
    filters = {}
    if brand_id:
        filters["brand_id"] = brand_id
    if status:
        filters["status"] = status
    return await service.post_repo.list(**filters)


@router.post("", response_model=PostResponse, status_code=201)
async def create_post(
    body: PostCreate,
    user: User = Depends(RequirePermission("posts.create")),
    service: ContentService = Depends(get_content_service),
):
    return await service.create_manual_post(
        brand_id=body.brand_id,
        content_text=body.content_text,
        created_by=user.id,
        hashtags=body.hashtags,
        target_channels=body.target_channels,
        scheduled_at=body.scheduled_at,
    )


@router.post("/generate", response_model=PostResponse, status_code=201)
async def generate_post(
    body: PostGenerateRequest,
    user: User = Depends(RequirePermission("posts.create")),
    service: ContentService = Depends(get_content_service),
    session: AsyncSession = Depends(get_session),
):
    """Generate a post using AI copywriter."""
    quota = QuotaService(session)
    await quota.enforce_quota(user.tenant_id, "ai_generations")

    post = await service.generate_post(
        brand_id=body.brand_id,
        brief=body.brief,
        channels=body.channels,
        created_by=user.id,
        campaign_id=body.campaign_id,
        language=body.language,
        scheduled_at=body.scheduled_at,
    )

    await quota.record_usage(user.tenant_id, "ai_generations")
    return post


@router.get("/{post_id}", response_model=PostResponse)
async def get_post(
    post_id: uuid.UUID,
    user: User = Depends(RequirePermission("posts.read")),
    service: ContentService = Depends(get_content_service),
):
    post = await service.post_repo.get_by_id(post_id)
    if not post:
        raise NotFoundError("Post not found")
    return post


@router.put("/{post_id}", response_model=PostResponse)
async def update_post(
    post_id: uuid.UUID,
    body: PostUpdate,
    user: User = Depends(RequirePermission("posts.update")),
    service: ContentService = Depends(get_content_service),
):
    data = body.model_dump(exclude_unset=True)
    post = await service.post_repo.update(post_id, **data)
    if not post:
        raise NotFoundError("Post not found")
    return post


@router.delete("/{post_id}", status_code=204)
async def delete_post(
    post_id: uuid.UUID,
    user: User = Depends(RequirePermission("posts.delete")),
    service: ContentService = Depends(get_content_service),
):
    if not await service.post_repo.delete(post_id):
        raise NotFoundError("Post not found")


@router.post("/{post_id}/submit-review")
async def submit_for_review(
    post_id: uuid.UUID,
    user: User = Depends(RequirePermission("posts.create")),
    service: ContentService = Depends(get_content_service),
):
    approval = await service.submit_for_review(post_id, requested_by=user.id)
    return {"approval_id": approval.id, "status": "pending_review"}


@router.post("/{post_id}/publish")
async def publish_post(
    post_id: uuid.UUID,
    user: User = Depends(RequirePermission("posts.publish")),
    service: ContentService = Depends(get_content_service),
):
    """Publish an approved post immediately."""
    post = await service.post_repo.get_by_id(post_id)
    if not post:
        raise NotFoundError("Post not found")
    if post.status.value not in ("approved", "scheduled"):
        from app.core.exceptions import InvalidInputError
        raise InvalidInputError(
            f"Post must be approved before publishing. Current status: {post.status.value}"
        )
    await enqueue("publish_post", str(post.id), str(user.tenant_id))
    return {"status": "publishing_queued", "post_id": post.id}


@router.post("/poster")
async def generate_poster_endpoint(
    body: dict,
    user: User = Depends(RequirePermission("posts.create")),
    session: AsyncSession = Depends(get_session),
):
    """Generate a marketing poster with text overlay, CTA, brand colors.

    Body: {"brief": "...", "brand_id": "...", "aspect_ratio": "1:1"}
    """
    from app.agents.registry import get_orchestrator
    from app.services.brand_service import BrandService

    brief = body.get("brief", "")
    brand_id = body.get("brand_id")
    aspect_ratio = body.get("aspect_ratio", "1:1")

    if not brief:
        from app.core.exceptions import InvalidInputError
        raise InvalidInputError("brief is required")

    brand_context = {}
    if brand_id:
        brand_service = BrandService(session, tenant_id=user.tenant_id)
        try:
            brand_context = await brand_service.get_brand_with_profile(uuid.UUID(brand_id))
        except Exception:
            pass

    orchestrator = get_orchestrator()
    result = await orchestrator.execute({
        "task_type": "generate_poster",
        "brief": brief,
        "brand_context": brand_context,
        "aspect_ratio": aspect_ratio,
    })

    if result.success:
        # Persist to gallery
        from app.models.gallery import GeneratedImage
        image = GeneratedImage(
            tenant_id=user.tenant_id,
            created_by=user.id,
            prompt=brief,
            technical_prompt=str(result.output.get("poster_plan", {})),
            image_url=result.output.get("image_url", ""),
            s3_key=result.output.get("s3_key", ""),
            aspect_ratio=aspect_ratio,
            metadata_={"type": "poster", "poster_plan": result.output.get("poster_plan", {})},
        )
        session.add(image)
        await session.commit()

        return {
            "success": True,
            "image_url": result.output.get("image_url"),
            "poster_plan": result.output.get("poster_plan"),
        }
    else:
        return {
            "success": False,
            "error": result.output.get("error", "Poster generation failed"),
        }


@router.post("/{post_id}/attach-image")
async def attach_image_to_post(
    post_id: uuid.UUID,
    body: AttachImageRequest,
    user: User = Depends(RequirePermission("posts.create")),
    service: ContentService = Depends(get_content_service),
    session: AsyncSession = Depends(get_session),
):
    """Attach an existing image URL to a post as a PostAsset."""
    from app.models.post import PostAsset

    post = await service.post_repo.get_by_id(post_id)
    if not post:
        raise NotFoundError("Post not found")

    asset = PostAsset(
        tenant_id=user.tenant_id,
        post_id=post_id,
        asset_type="image",
        file_url=body.image_url,
        mime_type="image/png",
        ai_generated=True,
        generation_prompt=body.prompt or "",
        metadata_=body.metadata,
    )
    session.add(asset)
    await session.commit()
    await session.refresh(asset)
    return {"id": str(asset.id), "file_url": asset.file_url, "post_id": str(post_id)}


@router.post("/image")
async def generate_image_endpoint(
    body: dict,
    user: User = Depends(RequirePermission("posts.create")),
    session: AsyncSession = Depends(get_session),
):
    """Generate an image via the ImageGen agent.

    Body: {"media_suggestion": "...", "brand_id": "...", "aspect_ratio": "1:1", "post_id": "..."}
    """
    from app.agents.registry import get_orchestrator
    from app.services.brand_service import BrandService

    media_suggestion = body.get("media_suggestion", "")
    brand_id = body.get("brand_id")
    aspect_ratio = body.get("aspect_ratio", "1:1")
    post_id = body.get("post_id")  # optional — attach to post if provided

    if not media_suggestion:
        from app.core.exceptions import InvalidInputError
        raise InvalidInputError("media_suggestion is required")

    brand_context = {}
    if brand_id:
        brand_service = BrandService(session, tenant_id=user.tenant_id)
        try:
            brand_context = await brand_service.get_brand_with_profile(uuid.UUID(brand_id))
        except Exception:
            pass

    orchestrator = get_orchestrator()
    result = await orchestrator.execute({
        "task_type": "generate_image",
        "media_suggestion": media_suggestion,
        "brand_context": brand_context,
        "aspect_ratio": aspect_ratio,
    })

    if result.success:
        # Persist to gallery
        from app.models.gallery import GeneratedImage
        image_url = result.output.get("image_url", "")
        s3_key = result.output.get("s3_key", "")

        gallery_image = GeneratedImage(
            tenant_id=user.tenant_id,
            created_by=user.id,
            prompt=media_suggestion,
            technical_prompt=result.output.get("prompt"),
            image_url=image_url,
            s3_key=s3_key,
            aspect_ratio=aspect_ratio,
            metadata_=result.output.get("metadata", {}),
        )
        session.add(gallery_image)

        # Auto-attach to post if post_id provided
        asset_id = None
        if post_id:
            from app.models.post import PostAsset
            asset = PostAsset(
                tenant_id=user.tenant_id,
                post_id=uuid.UUID(post_id),
                asset_type="image",
                file_url=image_url,
                mime_type="image/png",
                ai_generated=True,
                generation_prompt=result.output.get("prompt", ""),
                metadata_=result.output.get("metadata", {}),
            )
            session.add(asset)

        await session.commit()

        return {
            "success": True,
            "image_url": image_url,
            "prompt": result.output.get("prompt"),
            "metadata": result.output.get("metadata", {}),
            "attached_to_post": post_id,
        }
    else:
        return {
            "success": False,
            "error": result.output.get("error", "Image generation failed"),
        }
