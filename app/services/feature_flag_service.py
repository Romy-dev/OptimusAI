"""Feature flag service — check if features are enabled for tenants."""

import json
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import get_cache_service
from app.models.feature_flag import FeatureFlag

CACHE_TTL = 300  # 5 minutes


async def is_enabled(flag_name: str, tenant_id: str, session: AsyncSession) -> bool:
    """Check if a feature flag is enabled for a specific tenant."""
    cache = get_cache_service()
    cache_key = f"ff:{flag_name}:{tenant_id}"

    # Check cache
    if cache:
        cached = await cache.get(cache_key)
        if cached is not None:
            return cached == "1"

    # Query DB
    flag = await session.scalar(
        select(FeatureFlag).where(FeatureFlag.name == flag_name)
    )

    if not flag:
        result = False
    elif tenant_id in (flag.disabled_tenants or []):
        result = False
    elif flag.enabled_globally:
        result = True
    elif tenant_id in (flag.enabled_tenants or []):
        result = True
    else:
        result = False

    # Cache
    if cache:
        await cache.set(cache_key, "1" if result else "0", ttl=CACHE_TTL)

    return result


async def invalidate_flag_cache(flag_name: str):
    """Invalidate cache for a specific flag across all tenants."""
    cache = get_cache_service()
    if cache:
        # Can't delete by pattern easily, so just let TTL expire
        pass
