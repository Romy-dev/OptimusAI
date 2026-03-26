"""ARQ worker configuration — registers all background tasks."""

from arq.connections import RedisSettings

from app.config import settings
from app.workers.document_ingestion import ingest_document
from app.workers.publishing import publish_post
from app.workers.message_delivery import deliver_human_message
from app.workers.webhook_processing import (
    process_facebook_webhook,
    process_whatsapp_webhook,
)
from app.workers.scheduler import check_scheduled_posts
from app.workers.design_analysis import analyze_design_template


async def startup(ctx):
    """Worker startup: initialize logging."""
    from app.core.logging import setup_logging
    setup_logging()


async def shutdown(ctx):
    """Worker shutdown."""
    pass


class WorkerSettings:
    """ARQ worker settings."""

    functions = [
        ingest_document,
        publish_post,
        process_facebook_webhook,
        process_whatsapp_webhook,
        deliver_human_message,
        check_scheduled_posts,
        analyze_design_template,
    ]
    cron_jobs = [
        # Check for scheduled posts every minute (at second 0)
        {"coroutine": "app.workers.scheduler.check_scheduled_posts", "minute": None, "second": 0},
    ]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    max_jobs = 10
    job_timeout = 300
    keep_result = 3600
