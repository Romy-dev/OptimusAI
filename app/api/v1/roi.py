"""Revenue ROI Dashboard — translates every AI action into money saved/earned."""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.database import get_session
from app.models.user import User
from app.models.post import Post
from app.models.conversation import Conversation, Message
from app.models.chat import ChatMessage
from app.models.agent_run import AgentRun

router = APIRouter(prefix="/roi", tags=["roi"])

# Average costs in XOF (FCFA) for manual operations
MANUAL_COSTS = {
    "post_creation": 15000,       # Community manager creates 1 post: 15,000 FCFA
    "post_with_image": 25000,     # Post + image design: 25,000 FCFA
    "poster_design": 35000,       # Agency designs 1 poster: 35,000 FCFA
    "story_creation": 20000,      # 1 story (multi-slide): 20,000 FCFA
    "customer_reply": 500,        # 1 customer message reply: 500 FCFA (CM time)
    "comment_reply": 300,         # 1 comment reply: 300 FCFA
    "document_ingestion": 5000,   # Manual FAQ setup: 5,000 FCFA
    "cm_monthly_salary": 150000,  # Junior CM monthly salary: 150,000 FCFA
    "agency_monthly": 500000,     # Agency retainer: 500,000 FCFA/month
    "hours_saved_value": 3000,    # 1 hour of work value: 3,000 FCFA
}


@router.get("/dashboard")
async def roi_dashboard(
    period_days: int = 30,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Calculate the ROI of OptimusAI for the current tenant."""
    tenant_id = user.tenant_id
    since = datetime.now(timezone.utc) - timedelta(days=period_days)

    # Count AI-generated posts
    ai_posts = await session.scalar(
        select(func.count(Post.id)).where(
            Post.tenant_id == tenant_id,
            Post.ai_generated == True,
            Post.created_at >= since,
        )
    ) or 0

    # Count total posts
    total_posts = await session.scalar(
        select(func.count(Post.id)).where(
            Post.tenant_id == tenant_id,
            Post.created_at >= since,
        )
    ) or 0

    # Count AI messages (conversations handled by AI)
    ai_messages = await session.scalar(
        select(func.count(Message.id)).where(
            Message.tenant_id == tenant_id,
            Message.is_ai_generated == True,
            Message.created_at >= since,
        )
    ) or 0

    # Count conversations
    total_conversations = await session.scalar(
        select(func.count(Conversation.id)).where(
            Conversation.tenant_id == tenant_id,
            Conversation.created_at >= since,
        )
    ) or 0

    # Count chat interactions (concierge)
    chat_messages = await session.scalar(
        select(func.count(ChatMessage.id)).where(
            ChatMessage.tenant_id == tenant_id,
            ChatMessage.role == "assistant",
            ChatMessage.created_at >= since,
        )
    ) or 0

    # Calculate savings
    post_savings = ai_posts * MANUAL_COSTS["post_creation"]
    reply_savings = ai_messages * MANUAL_COSTS["customer_reply"]
    concierge_savings = chat_messages * MANUAL_COSTS["customer_reply"]

    # Estimate hours saved (avg 15 min per post, 3 min per reply, 2 min per chat)
    hours_saved = round(
        (ai_posts * 15 + ai_messages * 3 + chat_messages * 2) / 60, 1
    )
    hours_value = int(hours_saved * MANUAL_COSTS["hours_saved_value"])

    # Total
    total_savings = post_savings + reply_savings + concierge_savings + hours_value

    # What it would cost with alternatives
    cm_cost = MANUAL_COSTS["cm_monthly_salary"] * (period_days / 30)
    agency_cost = MANUAL_COSTS["agency_monthly"] * (period_days / 30)

    return {
        "period_days": period_days,
        "currency": "XOF",

        "activity": {
            "ai_posts_created": ai_posts,
            "total_posts": total_posts,
            "ai_messages_sent": ai_messages,
            "total_conversations": total_conversations,
            "concierge_interactions": chat_messages,
            "hours_saved": hours_saved,
        },

        "savings_breakdown": {
            "content_creation": {
                "count": ai_posts,
                "unit_cost": MANUAL_COSTS["post_creation"],
                "total": post_savings,
                "label": "Posts IA générés",
            },
            "customer_support": {
                "count": ai_messages,
                "unit_cost": MANUAL_COSTS["customer_reply"],
                "total": reply_savings,
                "label": "Réponses clients automatiques",
            },
            "concierge": {
                "count": chat_messages,
                "unit_cost": MANUAL_COSTS["customer_reply"],
                "total": concierge_savings,
                "label": "Interactions concierge IA",
            },
            "time_saved": {
                "hours": hours_saved,
                "hourly_rate": MANUAL_COSTS["hours_saved_value"],
                "total": hours_value,
                "label": "Heures de travail économisées",
            },
        },

        "totals": {
            "total_savings": total_savings,
            "vs_cm": {
                "cm_cost": int(cm_cost),
                "savings": total_savings,
                "roi_multiplier": round(total_savings / max(cm_cost, 1), 1),
                "label": "vs Community Manager",
            },
            "vs_agency": {
                "agency_cost": int(agency_cost),
                "savings": total_savings,
                "roi_multiplier": round(total_savings / max(agency_cost, 1), 1),
                "label": "vs Agence marketing",
            },
        },

        "insights": _generate_insights(ai_posts, ai_messages, chat_messages, hours_saved, total_savings),
    }


def _generate_insights(posts: int, messages: int, chats: int, hours: float, total: int) -> list[str]:
    """Generate human-readable ROI insights."""
    insights = []

    if posts > 0:
        insights.append(f"🎨 {posts} posts générés par IA — équivalent de {posts * 15} minutes de travail CM")

    if messages > 0:
        insights.append(f"💬 {messages} réponses clients automatiques — support 24h/7j sans pause")

    if hours > 10:
        insights.append(f"⏰ {hours}h économisées — c'est {hours / 8:.0f} journées de travail")

    if total > 100000:
        insights.append(f"💰 {total:,.0f} FCFA économisés — l'IA travaille pour vous même quand vous dormez")

    if posts == 0 and messages == 0:
        insights.append("🚀 Commencez à utiliser l'IA pour voir votre ROI augmenter !")

    return insights
