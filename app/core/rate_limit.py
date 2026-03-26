"""Rate limiting using Redis sliding window."""

import time

import redis.asyncio as redis
from fastapi import Depends, HTTPException, Request

from app.core.redis import get_redis


class RateLimiter:
    """Sliding window rate limiter backed by Redis."""

    def __init__(self, client: redis.Redis):
        self.client = client

    async def check(
        self,
        key: str,
        limit: int,
        window_seconds: int,
    ) -> tuple[bool, int]:
        """Check if request is within rate limit.

        Returns (allowed, remaining).
        """
        now = time.time()
        window_start = now - window_seconds
        pipe = self.client.pipeline()
        pipe.zremrangebyscore(key, 0, window_start)
        pipe.zadd(key, {str(now): now})
        pipe.zcard(key)
        pipe.expire(key, window_seconds)
        results = await pipe.execute()

        current_count = results[2]
        allowed = current_count <= limit
        remaining = max(0, limit - current_count)
        return allowed, remaining


class RateLimitDependency:
    """FastAPI dependency for rate limiting."""

    def __init__(self, limit: int, window_seconds: int, key_prefix: str = "rl"):
        self.limit = limit
        self.window_seconds = window_seconds
        self.key_prefix = key_prefix

    async def __call__(
        self,
        request: Request,
        redis_client: redis.Redis = Depends(get_redis),
    ) -> None:
        tenant_id = getattr(request.state, "tenant_id", "anon")
        key = f"{self.key_prefix}:{tenant_id}:{request.url.path}"

        limiter = RateLimiter(redis_client)
        allowed, remaining = await limiter.check(key, self.limit, self.window_seconds)

        if not allowed:
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded",
                headers={
                    "X-RateLimit-Limit": str(self.limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(self.window_seconds),
                },
            )
