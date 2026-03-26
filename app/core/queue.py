"""Queue helper — enqueues jobs to ARQ workers."""

import structlog
from arq import create_pool
from arq.connections import ArqRedis, RedisSettings

from app.config import settings

logger = structlog.get_logger()

_pool: ArqRedis | None = None


async def get_queue_pool() -> ArqRedis:
    """Get or create the ARQ Redis connection pool."""
    global _pool
    if _pool is None:
        _pool = await create_pool(RedisSettings.from_dsn(settings.redis_url))
    return _pool


async def close_queue_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.aclose()
        _pool = None


async def enqueue(job_name: str, *args, **kwargs) -> str | None:
    """Enqueue a job for async processing by ARQ workers.

    Returns the job ID or None if enqueueing failed.
    """
    try:
        pool = await get_queue_pool()
        job = await pool.enqueue_job(job_name, *args, **kwargs)
        if job:
            logger.info("job_enqueued", job_name=job_name, job_id=job.job_id)
            return job.job_id
        return None
    except Exception as e:
        logger.error("job_enqueue_failed", job_name=job_name, error=str(e))
        return None
