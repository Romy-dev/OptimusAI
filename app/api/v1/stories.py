
"""Story API — generate multi-slide stories with optional video assembly."""

import io
import uuid

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.database import get_session
from app.core.storage import storage_service
from app.models.user import User

router = APIRouter(prefix="/stories", tags=["stories"])


class StoryRequest(BaseModel):
    brief: str
    brand_id: str
    platform: str = "instagram"  # instagram, facebook, whatsapp
    generate_video: bool = False
    music_mood: str | None = None  # upbeat, chill, dramatic, inspiring, festive


class SlideImageRequest(BaseModel):
    story_plan: dict
    brand_id: str
    slide_index: int | None = None  # None = all slides


@router.post("/plan")
async def plan_story(
    body: StoryRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Generate a story plan (slides sequence) using AI."""
    from app.agents.registry import get_orchestrator
    from app.services.brand_service import BrandService

    # Get brand context
    brand_svc = BrandService(session, user.tenant_id)
    try:
        brand_ctx = await brand_svc.get_brand_with_profile(body.brand_id)
    except Exception:
        brand_ctx = {}

    orchestrator = get_orchestrator()
    result = await orchestrator.execute({
        "task_type": "generate_story",
        "brief": body.brief,
        "platform": body.platform,
        "brand_context": brand_ctx,
        "brand_id": body.brand_id,
        "tenant_id": str(user.tenant_id),
        "user_id": str(user.id),
    })

    if not result.success:
        return {"error": result.output.get("error", "Story generation failed")}

    return result.output


@router.post("/render")
async def render_story(
    body: SlideImageRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Render story slides as images (1080x1920) using PosterAgent."""
    import asyncio
    from app.agents.registry import get_orchestrator

    plan = body.story_plan
    slides = plan.get("slides", [])
    color_scheme = plan.get("color_scheme", {})

    if not slides:
        return {"error": "No slides in story plan"}

    # Determine which slides to render
    if body.slide_index is not None:
        if body.slide_index >= len(slides):
            return {"error": f"Slide index {body.slide_index} out of range (0-{len(slides)-1})"}
        slides_to_render = [(body.slide_index, slides[body.slide_index])]
    else:
        slides_to_render = list(enumerate(slides))

    orchestrator = get_orchestrator()
    poster_agent = orchestrator.agents.get("poster")

    rendered = []
    for idx, slide in slides_to_render:
        # Build a poster brief from the slide
        brief = f"{slide.get('headline', '')}. {slide.get('subtext', '')}"

        try:
            result = await poster_agent.run({
                "brief": brief,
                "brand_id": body.brand_id,
                "tenant_id": str(user.tenant_id),
                "aspect_ratio": "9:16",
                "brand_context": {
                    "colors": {
                        "primary": color_scheme.get("primary", "#0D9488"),
                        "secondary": color_scheme.get("secondary", "#1a1a2e"),
                    },
                    "brand_name": plan.get("story_title", ""),
                    "industry": "",
                },
            })

            if result.success and result.output.get("image_url"):
                rendered.append({
                    "slide_index": idx,
                    "role": slide.get("role"),
                    "image_url": result.output["image_url"],
                    "s3_key": result.output.get("s3_key"),
                })
            else:
                rendered.append({
                    "slide_index": idx,
                    "role": slide.get("role"),
                    "error": result.output.get("error", "Render failed"),
                })
        except Exception as e:
            rendered.append({
                "slide_index": idx,
                "role": slide.get("role"),
                "error": str(e)[:100],
            })

    return {
        "rendered_slides": rendered,
        "total": len(rendered),
        "success": sum(1 for r in rendered if "image_url" in r),
    }


@router.post("/video")
async def generate_video(
    body: SlideImageRequest,
    user: User = Depends(get_current_user),
):
    """Assemble rendered slides into a video with transitions and music."""
    import asyncio
    from app.integrations.story_video import generate_story_video
    from app.integrations.music_library import get_music_for_mood

    plan = body.story_plan
    slides = plan.get("slides", [])
    rendered = plan.get("rendered_slides", [])

    # If no separate rendered_slides, extract from slides with image_url
    if not rendered:
        rendered = [
            {"slide_index": i, "role": s.get("role"), "image_url": s.get("image_url"), "s3_key": s.get("s3_key")}
            for i, s in enumerate(slides) if s.get("image_url")
        ]

    if not rendered:
        return {"error": "No rendered slides. Call /stories/render first."}

    # Download slide images from S3
    slide_images = []
    durations = []
    transitions = []

    for r in rendered:
        if "s3_key" not in r and "image_url" not in r:
            continue

        try:
            s3_key = r.get("s3_key", "")
            if s3_key:
                data = await asyncio.to_thread(
                    lambda k=s3_key: storage_service.client.get_object(
                        Bucket=storage_service.bucket, Key=k
                    )["Body"].read()
                )
            else:
                # Download from URL
                import httpx
                async with httpx.AsyncClient(timeout=15) as client:
                    resp = await client.get(r["image_url"])
                    data = resp.content

            slide_images.append(data)
            idx = r.get("slide_index", len(durations))
            dur = slides[idx].get("duration_s", 3) if idx < len(slides) else 3
            durations.append(dur)
            anim = slides[idx].get("animation", "fade") if idx < len(slides) else "fade"
            transitions.append(anim)
        except Exception as e:
            continue

    if not slide_images:
        return {"error": "Could not download any slide images"}

    # Get music
    music_mood = plan.get("music_mood", "upbeat")
    total_dur = sum(durations)
    music_path = await get_music_for_mood(music_mood, total_dur)

    # Generate video
    try:
        video_bytes = await generate_story_video(
            slide_images=slide_images,
            durations=durations,
            transitions=transitions,
            music_path=music_path,
        )
    except Exception as e:
        return {"error": f"Video generation failed: {str(e)[:100]}"}

    # Upload to S3
    s3_key = f"stories/{uuid.uuid4().hex}.mp4"
    await asyncio.to_thread(
        lambda: storage_service.client.put_object(
            Bucket=storage_service.bucket,
            Key=s3_key,
            Body=video_bytes,
            ContentType="video/mp4",
        )
    )

    video_url = storage_service.get_public_url(s3_key)

    return {
        "video_url": video_url,
        "s3_key": s3_key,
        "duration_s": total_dur,
        "slides_count": len(slide_images),
        "has_music": music_path is not None,
        "size_kb": len(video_bytes) // 1024,
    }
