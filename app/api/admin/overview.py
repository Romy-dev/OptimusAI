"""Admin overview — platform-wide metrics and health."""

from fastapi import APIRouter, Depends
from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.admin_auth import require_superadmin
from app.core.database import get_session
from app.core.redis import get_redis
from app.models.user import User
from app.models.tenant import Tenant
from app.models.post import Post
from app.models.conversation import Conversation
from app.models.knowledge import KnowledgeDoc
from app.models.gallery import GeneratedImage
from app.models.customer_profile import CustomerProfile

router = APIRouter()


@router.get("/overview")
async def platform_overview(
    user: User = Depends(require_superadmin),
    session: AsyncSession = Depends(get_session),
):
    """Global platform metrics."""
    # Count everything
    tenants = await session.scalar(select(func.count()).select_from(Tenant))
    users = await session.scalar(select(func.count()).select_from(User))
    posts = await session.scalar(select(func.count()).select_from(Post))
    conversations = await session.scalar(select(func.count()).select_from(Conversation))
    documents = await session.scalar(select(func.count()).select_from(KnowledgeDoc))
    images = await session.scalar(select(func.count()).select_from(GeneratedImage))
    customers = await session.scalar(select(func.count()).select_from(CustomerProfile))

    # Posts by status
    posts_by_status = {}
    rows = await session.execute(
        select(Post.status, func.count()).group_by(Post.status)
    )
    for status, count in rows:
        posts_by_status[status.value if hasattr(status, 'value') else str(status)] = count

    # Conversations by status
    convos_by_status = {}
    rows2 = await session.execute(
        select(Conversation.status, func.count()).group_by(Conversation.status)
    )
    for status, count in rows2:
        convos_by_status[status.value if hasattr(status, 'value') else str(status)] = count

    # Recent signups (last 7 days)
    recent_signups = await session.scalar(
        select(func.count()).select_from(Tenant).where(
            Tenant.created_at >= text("now() - interval '7 days'")
        )
    )

    return {
        "totals": {
            "tenants": tenants,
            "users": users,
            "posts": posts,
            "conversations": conversations,
            "documents": documents,
            "images": images,
            "customer_profiles": customers,
        },
        "posts_by_status": posts_by_status,
        "conversations_by_status": convos_by_status,
        "recent_signups_7d": recent_signups,
    }


@router.get("/health")
async def system_health(
    user: User = Depends(require_superadmin),
    session: AsyncSession = Depends(get_session),
):
    """Check health of all services."""
    import httpx
    from app.config import settings

    checks = {}

    # Database
    try:
        await session.execute(text("SELECT 1"))
        checks["database"] = {"status": "ok", "type": "PostgreSQL 16"}
    except Exception as e:
        checks["database"] = {"status": "error", "error": str(e)[:100]}

    # Redis
    try:
        redis = await get_redis()
        await redis.ping()
        info = await redis.info("memory")
        checks["redis"] = {
            "status": "ok",
            "used_memory_human": info.get("used_memory_human", "?"),
        }
    except Exception as e:
        checks["redis"] = {"status": "error", "error": str(e)[:100]}

    # Ollama
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"{settings.ollama_base_url}/api/tags")
            models = [m["name"] for m in resp.json().get("models", [])]
            checks["ollama"] = {"status": "ok", "models": models}
    except Exception:
        checks["ollama"] = {"status": "down"}

    # ComfyUI
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"{settings.comfyui_base_url}/system_stats")
            checks["comfyui"] = {"status": "ok" if resp.status_code == 200 else "error"}
    except Exception:
        checks["comfyui"] = {"status": "down"}

    # MinIO
    try:
        from app.core.storage import storage_service
        storage_service.client.head_bucket(Bucket=storage_service.bucket)
        checks["minio"] = {"status": "ok", "bucket": storage_service.bucket}
    except Exception:
        checks["minio"] = {"status": "down"}

    all_ok = all(c.get("status") == "ok" for c in checks.values())
    return {
        "status": "healthy" if all_ok else "degraded",
        "checks": checks,
    }
