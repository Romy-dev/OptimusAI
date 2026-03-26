"""Intelligence API — strategy, timing, sentiment, analytics, follow-ups."""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.database import get_session
from app.core.permissions import RequirePermission
from app.models.customer_profile import CustomerProfile
from app.models.user import User

router = APIRouter(prefix="/intelligence", tags=["intelligence"])


# ── Content Strategy ──
@router.post("/strategy")
async def generate_strategy(
    body: dict,
    user: User = Depends(RequirePermission("posts.create")),
    session: AsyncSession = Depends(get_session),
):
    """Generate a content calendar / strategy plan."""
    from app.agents.registry import get_orchestrator
    from app.services.brand_service import BrandService

    brand_id = body.get("brand_id")
    period = body.get("period", "week")

    brand_context = {}
    if brand_id:
        brand_service = BrandService(session, tenant_id=user.tenant_id)
        try:
            brand_context = await brand_service.get_brand_with_profile(uuid.UUID(brand_id))
        except Exception:
            pass

    orchestrator = get_orchestrator()
    result = await orchestrator.execute({
        "task_type": "content_strategy",
        "brand_context": brand_context,
        "recent_posts": body.get("recent_posts", []),
        "target_country": brand_context.get("target_country", "BF"),
        "period": period,
        "current_date": datetime.now(timezone.utc).isoformat(),
    })

    if result.success:
        return {"success": True, **result.output}
    return {"success": False, "error": result.output.get("error", "Strategy generation failed")}


# ── Timing Optimization ──
@router.post("/timing")
async def optimize_timing(
    body: dict,
    user: User = Depends(RequirePermission("posts.create")),
):
    """Get optimal posting time for a given platform and content type."""
    from app.agents.registry import get_orchestrator

    orchestrator = get_orchestrator()
    result = await orchestrator.execute({
        "task_type": "optimize_timing",
        "platform": body.get("platform", "facebook"),
        "target_country": body.get("target_country", "BF"),
        "content_type": body.get("content_type", "engagement"),
        "brand_context": body.get("brand_context", {}),
        "recent_posts": body.get("recent_posts", []),
    })

    if result.success:
        return {"success": True, **result.output}
    return {"success": False, "error": result.output.get("error", "Timing optimization failed")}


# ── Sentiment Analysis ──
@router.post("/sentiment")
async def analyze_sentiment(
    body: dict,
    user: User = Depends(RequirePermission("posts.read")),
):
    """Analyze sentiment of messages or generate a daily report."""
    from app.agents.registry import get_orchestrator

    orchestrator = get_orchestrator()
    result = await orchestrator.execute({
        "task_type": "analyze_sentiment",
        "messages": body.get("messages", []),
        "brand_context": body.get("brand_context", {}),
        "analysis_type": body.get("analysis_type", "single_message"),
    })

    if result.success:
        return {"success": True, **result.output}
    return {"success": False, "error": result.output.get("error", "Sentiment analysis failed")}


# ── Analytics Report ──
@router.post("/analytics")
async def generate_analytics(
    body: dict,
    user: User = Depends(RequirePermission("posts.read")),
):
    """Generate performance analytics report."""
    from app.agents.registry import get_orchestrator

    orchestrator = get_orchestrator()
    result = await orchestrator.execute({
        "task_type": "analyze_performance",
        "report_type": body.get("report_type", "weekly"),
        "posts": body.get("posts", []),
        "conversations": body.get("conversations", []),
        "brand_context": body.get("brand_context", {}),
        "period_start": body.get("period_start", ""),
        "period_end": body.get("period_end", ""),
    })

    if result.success:
        return {"success": True, **result.output}
    return {"success": False, "error": result.output.get("error", "Analytics failed")}


# ── Follow-up Generation ──
@router.post("/followup")
async def generate_followup(
    body: dict,
    user: User = Depends(RequirePermission("posts.create")),
):
    """Generate a follow-up message for a customer."""
    from app.agents.registry import get_orchestrator

    orchestrator = get_orchestrator()
    result = await orchestrator.execute({
        "task_type": "followup",
        "followup_type": body.get("followup_type", "re_engagement"),
        "customer_profile": body.get("customer_profile", {}),
        "brand_context": body.get("brand_context", {}),
        "channel": body.get("channel", "whatsapp"),
        "days_since_contact": body.get("days_since_contact", 30),
    })

    if result.success:
        return {"success": True, **result.output}
    return {"success": False, "error": result.output.get("error", "Follow-up generation failed")}


# ── Customer Profiles ──
@router.get("/customers")
async def list_customer_profiles(
    user: User = Depends(RequirePermission("posts.read")),
    session: AsyncSession = Depends(get_session),
):
    """List all customer profiles for the tenant."""
    stmt = (
        select(CustomerProfile)
        .where(CustomerProfile.tenant_id == user.tenant_id)
        .order_by(CustomerProfile.last_contact_at.desc().nullslast())
        .limit(100)
    )
    result = await session.execute(stmt)
    profiles = result.scalars().all()
    return [
        {
            "id": str(p.id),
            "display_name": p.display_name,
            "platform": p.platform,
            "segment": p.segment,
            "sentiment_trend": p.sentiment_trend,
            "total_conversations": p.total_conversations,
            "total_messages": p.total_messages,
            "interests": p.interests,
            "tags": p.tags,
            "last_contact_at": p.last_contact_at.isoformat() if p.last_contact_at else None,
            "next_followup_at": p.next_followup_at.isoformat() if p.next_followup_at else None,
            "followup_reason": p.followup_reason,
            "lifetime_value": p.lifetime_value,
        }
        for p in profiles
    ]
