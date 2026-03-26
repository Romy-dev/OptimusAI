"""Redis connection for caching and queue."""

import redis.asyncio as redis

from app.config import settings

redis_pool: redis.Redis | None = None


async def get_redis() -> redis.Redis:
    global redis_pool
    if redis_pool is None:
        redis_pool = redis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
            max_connections=20,
        )
    return redis_pool


async def close_redis() -> None:
    global redis_pool
    if redis_pool is not None:
        await redis_pool.aclose()
        redis_pool = None


class CacheService:
    """Simple cache abstraction over Redis."""

    def __init__(self, client: redis.Redis):
        self.client = client

    async def get(self, key: str) -> str | None:
        return await self.client.get(key)

    async def set(self, key: str, value: str, ttl_seconds: int = 300) -> None:
        await self.client.set(key, value, ex=ttl_seconds)

    async def delete(self, key: str) -> None:
        await self.client.delete(key)

    async def exists(self, key: str) -> bool:
        return bool(await self.client.exists(key))

    async def increment(self, key: str, ttl_seconds: int | None = None) -> int:
        val = await self.client.incr(key)
        if ttl_seconds and val == 1:
            await self.client.expire(key, ttl_seconds)
        return val
