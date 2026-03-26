import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.database import get_session
from app.core.exceptions import NotFoundError
from app.core.permissions import RequirePermission
from app.core.storage import storage_service
from app.models.gallery import GeneratedImage
from app.models.user import User

router = APIRouter(prefix="/gallery", tags=["gallery"])


@router.get("/images")
async def list_images(
    user: User = Depends(RequirePermission("posts.read")),
    session: AsyncSession = Depends(get_session),
):
    """List all generated images for the tenant."""
    stmt = (
        select(GeneratedImage)
        .where(GeneratedImage.tenant_id == user.tenant_id)
        .order_by(GeneratedImage.created_at.desc())
        .limit(100)
    )
    result = await session.execute(stmt)
    images = result.scalars().all()
    return [
        {
            "id": str(img.id),
            "prompt": img.prompt,
            "technical_prompt": img.technical_prompt,
            "image_url": img.image_url,
            "aspect_ratio": img.aspect_ratio,
            "metadata": img.metadata_,
            "created_at": img.created_at.isoformat(),
        }
        for img in images
    ]


@router.delete("/images/{image_id}", status_code=204)
async def delete_image(
    image_id: uuid.UUID,
    user: User = Depends(RequirePermission("posts.delete")),
    session: AsyncSession = Depends(get_session),
):
    """Delete a generated image."""
    stmt = (
        select(GeneratedImage)
        .where(GeneratedImage.tenant_id == user.tenant_id)
        .where(GeneratedImage.id == image_id)
    )
    result = await session.execute(stmt)
    image = result.scalar_one_or_none()
    if not image:
        raise NotFoundError("Image not found")

    # Delete from S3
    try:
        await storage_service.delete_file(image.s3_key)
    except Exception:
        pass  # S3 cleanup is best-effort

    await session.delete(image)
    await session.commit()
