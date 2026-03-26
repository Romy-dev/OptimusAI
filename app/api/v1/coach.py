"""Coach Marketing API — proactive suggestions for tenant activity."""

import json

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.database import get_session
from app.core.redis import get_redis, CacheService
from app.models.user import User
from app.models.post import Post
from app.models.conversation import Conversation
from app.models.social_account import SocialAccount
from app.models.knowledge import KnowledgeDoc
from app.models.brand import Brand
from app.models.brand_profile import BrandProfile
from app.models.gallery import GeneratedImage
from app.models.design_template import DesignTemplate
from app.agents.registry import get_orchestrator

router = APIRouter(prefix="/coach", tags=["coach"])

CACHE_TTL = 3600  # 1 hour


@router.get("/suggestions")
async def get_suggestions(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Get AI-powered marketing suggestions for the current tenant."""
    tenant_id = user.tenant_id
    cache_key = f"coach:suggestions:{tenant_id}"

    # Check cache first
    try:
        redis_client = await get_redis()
        cache = CacheService(redis_client)
        cached = await cache.get(cache_key)
        if cached:
            return json.loads(cached)
    except Exception:
        cache = None

    # Gather activity metrics
    context = await _build_activity_context(session, tenant_id)

    # Run the coach agent
    orchestrator = get_orchestrator()
    coach = orchestrator.agents.get("coach")

    if coach:
        try:
            result = await coach.run(context)
            output = result.output
            # If agent failed or returned error, use rule-based fallback
            if not result.success or "error" in output or "suggestions" not in output:
                raise ValueError("Fallback needed")
        except Exception:
            output = {
                "suggestions": coach._fallback_suggestions(context),
                "health_score": coach._compute_health(context),
                "summary": "Suggestions basées sur votre activité.",
            }
    else:
        output = {"suggestions": [], "health_score": 0, "summary": "Coach agent non disponible"}

    # Cache for 1 hour
    if cache:
        try:
            await cache.set(cache_key, json.dumps(output, ensure_ascii=False, default=str), ttl_seconds=CACHE_TTL)
        except Exception:
            pass

    return output


async def _build_activity_context(session: AsyncSession, tenant_id) -> dict:
    """Build the full activity context for the coach agent."""
    from datetime import datetime, timedelta, timezone

    now = datetime.now(timezone.utc)
    seven_days_ago = now - timedelta(days=7)

    # Posts
    posts_total = await session.scalar(
        select(func.count(Post.id)).where(Post.tenant_id == tenant_id)
    )
    posts_7d = await session.scalar(
        select(func.count(Post.id)).where(
            Post.tenant_id == tenant_id,
            Post.created_at >= seven_days_ago,
        )
    )
    last_post = await session.scalar(
        select(Post.created_at)
        .where(Post.tenant_id == tenant_id)
        .order_by(Post.created_at.desc())
        .limit(1)
    )

    # Conversations
    convs_total = await session.scalar(
        select(func.count(Conversation.id)).where(Conversation.tenant_id == tenant_id)
    )
    convs_open = await session.scalar(
        select(func.count(Conversation.id)).where(
            Conversation.tenant_id == tenant_id,
            Conversation.status.in_(["open", "ai_handling", "human_handling"]),
        )
    )

    # Connected platforms
    platforms_result = await session.execute(
        select(SocialAccount.platform).where(
            SocialAccount.tenant_id == tenant_id,
            SocialAccount.is_active == True,
        ).distinct()
    )
    platforms = [row[0] for row in platforms_result.all()]

    # Knowledge docs
    kb_count = await session.scalar(
        select(func.count(KnowledgeDoc.id)).where(KnowledgeDoc.tenant_id == tenant_id)
    )

    # Brand info
    brand = await session.scalar(
        select(Brand).where(Brand.tenant_id == tenant_id).limit(1)
    )
    brand_name = brand.name if brand else "Non défini"
    industry = brand.industry if brand else "Non défini"
    country = brand.target_country if brand else "Non défini"
    language = brand.language if brand else "français"

    # Brand completeness
    completeness = 20  # base
    if brand:
        if brand.name:
            completeness += 10
        if brand.description:
            completeness += 10
        if brand.industry:
            completeness += 10
        if brand.tone:
            completeness += 10
        if brand.logo_url:
            completeness += 10
        if brand.colors:
            completeness += 10
        profile = await session.scalar(
            select(BrandProfile).where(BrandProfile.brand_id == brand.id)
        )
        if profile:
            completeness += 20

    # Products count
    products_count = 0
    if brand:
        profile = await session.scalar(
            select(BrandProfile).where(BrandProfile.brand_id == brand.id)
        )
        if profile and profile.products:
            products_count = len(profile.products)

    # Images
    images_count = await session.scalar(
        select(func.count(GeneratedImage.id)).where(GeneratedImage.tenant_id == tenant_id)
    )

    # Templates
    templates_count = await session.scalar(
        select(func.count(DesignTemplate.id)).where(DesignTemplate.tenant_id == tenant_id)
    )

    return {
        "tenant_id": str(tenant_id),
        "brand_name": brand_name,
        "industry": industry,
        "country": country,
        "language": language,
        "posts_count": posts_total or 0,
        "posts_last_7d": posts_7d or 0,
        "last_post_date": last_post.strftime("%d/%m/%Y") if last_post else "jamais",
        "conversations_count": convs_total or 0,
        "conversations_open": convs_open or 0,
        "connected_platforms": platforms,
        "knowledge_docs": kb_count or 0,
        "brand_completeness": min(100, completeness),
        "products_count": products_count,
        "images_count": images_count or 0,
        "templates_count": templates_count or 0,
    }
