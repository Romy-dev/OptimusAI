"""Admin config — feature flags, plan limits, LLM settings."""

from fastapi import APIRouter, Depends

from app.core.admin_auth import require_superadmin
from app.config import settings
from app.models.user import User

router = APIRouter(prefix="/config")


@router.get("/current")
async def current_config(
    user: User = Depends(require_superadmin),
):
    """Show current platform configuration (non-sensitive)."""
    return {
        "app": {
            "name": settings.app_name,
            "version": settings.app_version,
            "environment": settings.environment,
            "debug": settings.debug,
        },
        "llm": {
            "provider": settings.default_llm_provider,
            "ollama_url": settings.ollama_base_url,
            "has_anthropic_key": bool(settings.anthropic_api_key),
            "has_openai_key": bool(settings.openai_api_key),
            "embedding_model": settings.embedding_model,
        },
        "image_gen": {
            "comfyui_url": settings.comfyui_base_url,
        },
        "storage": {
            "endpoint": settings.s3_endpoint_url,
            "bucket": settings.s3_bucket_name,
            "public_url": settings.s3_public_url,
        },
        "auth": {
            "token_expire_minutes": settings.access_token_expire_minutes,
            "refresh_expire_days": settings.refresh_token_expire_days,
        },
        "social": {
            "has_facebook_app": bool(settings.facebook_app_id),
            "facebook_webhook_token": settings.facebook_webhook_verify_token,
            "whatsapp_webhook_token": settings.whatsapp_webhook_verify_token,
        },
        "plans": {
            "starter": {"brands": 1, "social_accounts": 3, "posts_per_month": 20, "ai_generations": 50, "documents": 5, "price_fcfa": 9900},
            "pro": {"brands": 3, "social_accounts": 10, "posts_per_month": 100, "ai_generations": 500, "documents": 50, "price_fcfa": 29900},
            "business": {"brands": -1, "social_accounts": -1, "posts_per_month": -1, "ai_generations": -1, "documents": -1, "price_fcfa": 79900},
        },
    }


@router.get("/agents")
async def agents_config(
    user: User = Depends(require_superadmin),
):
    """Show all agents and their configuration."""
    from app.agents.registry import create_agent_registry
    from app.agents.orchestrator import ROUTING_TABLE

    registry = create_agent_registry()
    return {
        "agents": [
            {
                "name": a.name,
                "description": a.description,
                "max_retries": a.max_retries,
                "confidence_threshold": a.confidence_threshold,
            }
            for a in registry.values()
        ],
        "routing_table": {k.value: v for k, v in ROUTING_TABLE.items()},
        "total_agents": len(registry),
    }
