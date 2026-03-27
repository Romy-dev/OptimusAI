
"""Story API — generate multi-slide stories with optional video assembly."""

import io
import uuid

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.database import get_session
from app.core.exceptions import NotFoundError
from app.core.storage import storage_service
from app.models.gallery import GeneratedImage
from app.models.story import Story
from app.models.user import User

router = APIRouter(prefix="/stories", tags=["stories"])

# ---------------------------------------------------------------------------
# Ensure tables exist (idempotent DDL)
# ---------------------------------------------------------------------------

_INIT_SQL = """
CREATE TABLE IF NOT EXISTS stories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    brand_id UUID REFERENCES brands(id),
    created_by UUID REFERENCES users(id),
    title VARCHAR(200),
    brief TEXT NOT NULL,
    platform VARCHAR(30) DEFAULT 'instagram',
    story_plan JSONB DEFAULT '{}',
    total_slides INTEGER DEFAULT 0,
    total_duration_s INTEGER DEFAULT 0,
    slide_images JSONB DEFAULT '[]',
    video_url VARCHAR(500),
    video_s3_key VARCHAR(500),
    video_duration_s INTEGER,
    music_mood VARCHAR(30),
    status VARCHAR(30) DEFAULT 'draft',
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE generated_images ADD COLUMN IF NOT EXISTS media_type VARCHAR(20) DEFAULT 'image';
"""

_tables_ensured = False


async def _ensure_tables(session: AsyncSession) -> None:
    """Run idempotent DDL the first time any story endpoint is hit."""
    global _tables_ensured
    if _tables_ensured:
        return
    for stmt in _INIT_SQL.strip().split(";"):
        stmt = stmt.strip()
        if stmt:
            await session.execute(text(stmt))
    await session.commit()
    _tables_ensured = True


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class StoryRequest(BaseModel):
    brief: str
    brand_id: str
    platform: str = "instagram"  # instagram, facebook, whatsapp
    generate_video: bool = False
    music_mood: str | None = None  # upbeat, chill, dramatic, inspiring, festive


class SlideImageRequest(BaseModel):
    story_id: str | None = None  # optional — link to persisted story
    story_plan: dict
    brand_id: str
    slide_index: int | None = None  # None = all slides


class StoryVideoRequest(BaseModel):
    story_id: str | None = None  # optional — link to persisted story
    story_plan: dict
    brand_id: str


class StoryConvertRequest(BaseModel):
    brief: str
    brand_id: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _story_to_dict(s: Story) -> dict:
    return {
        "id": str(s.id),
        "tenant_id": str(s.tenant_id),
        "brand_id": str(s.brand_id) if s.brand_id else None,
        "created_by": str(s.created_by) if s.created_by else None,
        "title": s.title,
        "brief": s.brief,
        "platform": s.platform,
        "story_plan": s.story_plan,
        "total_slides": s.total_slides,
        "total_duration_s": s.total_duration_s,
        "slide_images": s.slide_images,
        "video_url": s.video_url,
        "video_s3_key": s.video_s3_key,
        "video_duration_s": s.video_duration_s,
        "music_mood": s.music_mood,
        "status": s.status,
        "created_at": s.created_at.isoformat() if s.created_at else None,
        "updated_at": s.updated_at.isoformat() if s.updated_at else None,
    }


async def _get_story(session: AsyncSession, tenant_id, story_id: str) -> Story:
    stmt = (
        select(Story)
        .where(Story.tenant_id == tenant_id)
        .where(Story.id == uuid.UUID(story_id))
    )
    result = await session.execute(stmt)
    story = result.scalar_one_or_none()
    if not story:
        raise NotFoundError("Story not found")
    return story


# ---------------------------------------------------------------------------
# CRUD endpoints
# ---------------------------------------------------------------------------

@router.get("")
async def list_stories(
    status: str | None = None,
    platform: str | None = None,
    limit: int = 50,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """List all stories for the tenant."""
    await _ensure_tables(session)

    stmt = select(Story).where(Story.tenant_id == user.tenant_id)
    if status:
        stmt = stmt.where(Story.status == status)
    if platform:
        stmt = stmt.where(Story.platform == platform)
    stmt = stmt.order_by(Story.created_at.desc()).limit(min(limit, 200))

    result = await session.execute(stmt)
    stories = result.scalars().all()
    return [_story_to_dict(s) for s in stories]


@router.get("/{story_id}")
async def get_story(
    story_id: str,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Get a single story with all its data."""
    await _ensure_tables(session)
    story = await _get_story(session, user.tenant_id, story_id)
    return _story_to_dict(story)


@router.delete("/{story_id}", status_code=204)
async def delete_story(
    story_id: str,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Delete a story and its S3 assets."""
    await _ensure_tables(session)
    story = await _get_story(session, user.tenant_id, story_id)

    # Best-effort S3 cleanup
    s3_keys_to_delete = []
    if story.video_s3_key:
        s3_keys_to_delete.append(story.video_s3_key)
    for slide in (story.slide_images or []):
        if isinstance(slide, dict) and slide.get("s3_key"):
            s3_keys_to_delete.append(slide["s3_key"])

    for key in s3_keys_to_delete:
        try:
            await storage_service.delete_file(key)
        except Exception:
            pass

    await session.delete(story)
    await session.commit()


# ---------------------------------------------------------------------------
# Plan endpoint (with persistence)
# ---------------------------------------------------------------------------

@router.post("/plan")
async def plan_story(
    body: StoryRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Generate a story plan (slides sequence) using AI and persist it."""
    await _ensure_tables(session)

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

    # Persist the story
    story_plan = result.output.get("story_plan", {})
    story = Story(
        tenant_id=user.tenant_id,
        brand_id=uuid.UUID(body.brand_id) if body.brand_id else None,
        created_by=user.id,
        title=result.output.get("story_title") or story_plan.get("story_title"),
        brief=body.brief,
        platform=body.platform,
        story_plan=story_plan,
        total_slides=result.output.get("total_slides", len(story_plan.get("slides", []))),
        total_duration_s=result.output.get("total_duration_s", 0),
        music_mood=body.music_mood or result.output.get("music_mood"),
        status="planned",
    )
    session.add(story)
    await session.commit()
    await session.refresh(story)

    output = result.output
    output["story_id"] = str(story.id)
    return output


# ---------------------------------------------------------------------------
# Render endpoint (with persistence)
# ---------------------------------------------------------------------------

@router.post("/render")
async def render_story(
    body: SlideImageRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Render story slides as images (1080x1920) using PosterAgent."""
    await _ensure_tables(session)

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
                    "rendered": True,
                })
            else:
                rendered.append({
                    "slide_index": idx,
                    "role": slide.get("role"),
                    "error": result.output.get("error", "Render failed"),
                    "rendered": False,
                })
        except Exception as e:
            rendered.append({
                "slide_index": idx,
                "role": slide.get("role"),
                "error": str(e)[:100],
                "rendered": False,
            })

    # Persist rendered slides to the story record
    if body.story_id:
        try:
            story = await _get_story(session, user.tenant_id, body.story_id)
            story.slide_images = rendered
            story.status = "rendered"
            await session.commit()
        except Exception:
            pass  # story persistence is best-effort; don't break the response

    return {
        "story_id": body.story_id,
        "rendered_slides": rendered,
        "total": len(rendered),
        "success": sum(1 for r in rendered if r.get("rendered")),
    }


# ---------------------------------------------------------------------------
# Video endpoint (with persistence + gallery entry)
# ---------------------------------------------------------------------------

@router.post("/video")
async def generate_video(
    body: StoryVideoRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Assemble rendered slides into a video with transitions and music."""
    await _ensure_tables(session)

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
        except Exception:
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

    # Persist to story record
    if body.story_id:
        try:
            story = await _get_story(session, user.tenant_id, body.story_id)
            story.video_url = video_url
            story.video_s3_key = s3_key
            story.video_duration_s = total_dur
            story.music_mood = music_mood
            story.status = "video_ready"
            await session.commit()
        except Exception:
            pass

    # Create a gallery entry so the video appears in the Media Center
    try:
        gallery_entry = GeneratedImage(
            tenant_id=user.tenant_id,
            created_by=user.id,
            prompt=plan.get("story_title", "Story video"),
            technical_prompt=f"Story video — {len(slide_images)} slides, {total_dur}s",
            image_url=video_url,
            s3_key=s3_key,
            aspect_ratio="9:16",
            media_type="video",
            metadata_={
                "type": "story_video",
                "story_id": body.story_id,
                "slides_count": len(slide_images),
                "duration_s": total_dur,
                "music_mood": music_mood,
            },
        )
        session.add(gallery_entry)
        await session.commit()
    except Exception:
        pass  # gallery entry is best-effort

    return {
        "story_id": body.story_id,
        "video_url": video_url,
        "s3_key": s3_key,
        "duration_s": total_dur,
        "slides_count": len(slide_images),
        "has_music": music_path is not None,
        "size_kb": len(video_bytes) // 1024,
    }


# ---------------------------------------------------------------------------
# Convert-formats endpoint (unchanged logic)
# ---------------------------------------------------------------------------

@router.post("/convert-formats")
async def convert_to_all_formats(
    body: StoryConvertRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Convert a story brief into 6 platform-optimized formats.

    Uses StoryAgent for story/reel slide plans, CopywriterAgent for
    platform-specific text, and PosterAgent for image layout plans at
    different aspect ratios.  No images are actually rendered — the user
    can choose which formats to render afterwards.
    """
    import asyncio
    from app.agents.registry import get_orchestrator
    from app.services.brand_service import BrandService

    # Get brand context
    brand_svc = BrandService(session, user.tenant_id)
    try:
        brand_ctx = await brand_svc.get_brand_with_profile(body.brand_id)
    except Exception:
        brand_ctx = {}

    orchestrator = get_orchestrator()
    story_agent = orchestrator.agents.get("story")
    copywriter_agent = orchestrator.agents.get("copywriter")
    poster_agent = orchestrator.agents.get("poster")

    # --- Run agents concurrently where possible ---

    # 1. StoryAgent: Instagram story plan (9:16 slides)
    story_task = story_agent.run({
        "brief": body.brief,
        "platform": "instagram",
        "brand_context": brand_ctx,
    })

    # 2. CopywriterAgent: Facebook post text
    fb_copy_task = copywriter_agent.run({
        "brief": body.brief,
        "channel": "facebook",
        "objective": "engagement",
        "brand_context": brand_ctx,
    })

    # 3. CopywriterAgent: TikTok post text
    tiktok_copy_task = copywriter_agent.run({
        "brief": body.brief,
        "channel": "tiktok",
        "objective": "engagement",
        "brand_context": brand_ctx,
    })

    # 4. PosterAgent: Facebook square image plan (1:1)
    fb_poster_task = poster_agent.run({
        "brief": body.brief,
        "brand_id": body.brand_id,
        "tenant_id": str(user.tenant_id),
        "aspect_ratio": "1:1",
        "brand_context": brand_ctx,
        "plan_only": True,
    })

    # 5. PosterAgent: Vertical image plan for WhatsApp/TikTok (9:16)
    vertical_poster_task = poster_agent.run({
        "brief": body.brief,
        "brand_id": body.brand_id,
        "tenant_id": str(user.tenant_id),
        "aspect_ratio": "9:16",
        "brand_context": brand_ctx,
        "plan_only": True,
    })

    # 6. PosterAgent: Website banner plan (16:9)
    banner_poster_task = poster_agent.run({
        "brief": body.brief,
        "brand_id": body.brand_id,
        "tenant_id": str(user.tenant_id),
        "aspect_ratio": "16:9",
        "brand_context": brand_ctx,
        "plan_only": True,
    })

    # Gather all results
    (
        story_result,
        fb_copy_result,
        tiktok_copy_result,
        fb_poster_result,
        vertical_poster_result,
        banner_poster_result,
    ) = await asyncio.gather(
        story_task,
        fb_copy_task,
        tiktok_copy_task,
        fb_poster_task,
        vertical_poster_task,
        banner_poster_task,
        return_exceptions=True,
    )

    # --- Assemble the 6 formats ---

    formats = {}

    # Instagram Story (slides from StoryAgent)
    if not isinstance(story_result, Exception) and story_result.success:
        story_plan = story_result.output.get("story_plan", {})
        formats["instagram_story"] = {
            "slides": story_plan.get("slides", []),
            "aspect_ratio": "9:16",
            "total_slides": story_result.output.get("total_slides", 0),
            "total_duration_s": story_result.output.get("total_duration_s", 0),
            "color_scheme": story_plan.get("color_scheme"),
            "mood": story_plan.get("mood"),
        }
    else:
        formats["instagram_story"] = {"error": "Story generation failed", "aspect_ratio": "9:16"}

    # Instagram Reel (reuse story slides as a video storyboard)
    if not isinstance(story_result, Exception) and story_result.success:
        story_plan = story_result.output.get("story_plan", {})
        formats["instagram_reel"] = {
            "slides": story_plan.get("slides", []),
            "aspect_ratio": "9:16",
            "duration": story_result.output.get("total_duration_s", 30),
            "music_mood": story_result.output.get("music_mood", "upbeat"),
            "note": "Use /stories/render + /stories/video to produce the final video",
        }
    else:
        formats["instagram_reel"] = {"error": "Reel generation failed", "aspect_ratio": "9:16"}

    # Facebook Post (copy + square image plan)
    fb_text = ""
    fb_hashtags = []
    fb_media_suggestion = ""
    if not isinstance(fb_copy_result, Exception) and fb_copy_result.success:
        fb_text = fb_copy_result.output.get("content", "")
        fb_hashtags = fb_copy_result.output.get("hashtags", [])
        fb_media_suggestion = fb_copy_result.output.get("media_suggestion", "")

    fb_image_plan = None
    if not isinstance(fb_poster_result, Exception) and fb_poster_result.success:
        fb_image_plan = fb_poster_result.output.get("layout_plan") or fb_poster_result.output

    formats["facebook_post"] = {
        "content_text": fb_text,
        "hashtags": fb_hashtags,
        "media_suggestion": fb_media_suggestion,
        "image_plan": fb_image_plan,
        "aspect_ratio": "1:1",
    }

    # WhatsApp Status (vertical image plan)
    vertical_image_plan = None
    if not isinstance(vertical_poster_result, Exception) and vertical_poster_result.success:
        vertical_image_plan = vertical_poster_result.output.get("layout_plan") or vertical_poster_result.output

    formats["whatsapp_status"] = {
        "image_plan": vertical_image_plan,
        "aspect_ratio": "9:16",
    }

    # TikTok Post (copy + vertical image plan)
    tiktok_text = ""
    tiktok_hashtags = []
    if not isinstance(tiktok_copy_result, Exception) and tiktok_copy_result.success:
        tiktok_text = tiktok_copy_result.output.get("content", "")
        tiktok_hashtags = tiktok_copy_result.output.get("hashtags", [])

    formats["tiktok_post"] = {
        "content_text": tiktok_text,
        "hashtags": tiktok_hashtags,
        "image_plan": vertical_image_plan,
        "aspect_ratio": "9:16",
    }

    # Website Banner (landscape image plan)
    banner_image_plan = None
    if not isinstance(banner_poster_result, Exception) and banner_poster_result.success:
        banner_image_plan = banner_poster_result.output.get("layout_plan") or banner_poster_result.output

    formats["website_banner"] = {
        "image_plan": banner_image_plan,
        "aspect_ratio": "16:9",
    }

    return {
        "brief": body.brief,
        "brand_id": body.brand_id,
        "formats": formats,
    }
