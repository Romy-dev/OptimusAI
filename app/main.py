from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

import structlog
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.core.database import engine
from app.core.exceptions import OptimusError, optimus_exception_handler
from app.core.logging import setup_logging
from app.core.middleware import TenantMiddleware
from app.core.queue import close_queue_pool
from app.core.redis import close_redis, get_redis
from app.api.v1.router import api_v1_router
from app.api.admin.router import admin_router

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Startup
    setup_logging()
    logger.info("starting_app", version=settings.app_version, env=settings.environment)

    # Warm up Redis connection
    redis_client = await get_redis()
    await redis_client.ping()
    logger.info("redis_connected")

    yield

    # Shutdown
    logger.info("shutting_down")
    await close_queue_pool()
    await close_redis()
    await engine.dispose()


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        docs_url="/api/docs" if settings.debug else None,
        redoc_url="/api/redoc" if settings.debug else None,
        lifespan=lifespan,
    )

    # Exception handlers
    app.add_exception_handler(OptimusError, optimus_exception_handler)

    # Middleware (order matters: last added = first executed)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(TenantMiddleware)

    # API routes
    app.include_router(api_v1_router, prefix="/api/v1")
    app.include_router(admin_router, prefix="/api")

    # Health checks
    @app.get("/health")
    async def health_check():
        return {"status": "ok", "version": settings.app_version}

    @app.get("/health/ready")
    async def readiness_check():
        """Deep health check: verifies DB and Redis are reachable."""
        checks = {}
        try:
            from app.core.database import async_session_factory
            from sqlalchemy import text

            async with async_session_factory() as session:
                await session.execute(text("SELECT 1"))
            checks["database"] = "ok"
        except Exception as e:
            checks["database"] = f"error: {e}"

        try:
            redis_client = await get_redis()
            await redis_client.ping()
            checks["redis"] = "ok"
        except Exception as e:
            checks["redis"] = f"error: {e}"

        all_ok = all(v == "ok" for v in checks.values())
        return {
            "status": "ok" if all_ok else "degraded",
            "checks": checks,
            "version": settings.app_version,
        }

    # WebSocket endpoint
    @app.websocket("/ws")
    async def websocket_endpoint(ws: WebSocket):
        from app.core.websocket import ws_manager
        from app.core.auth import decode_token

        token = ws.query_params.get("token")
        if not token:
            await ws.close(code=4001, reason="Missing token")
            return
        try:
            payload = decode_token(token)
            tenant_id = payload.get("tenant_id", "")
            user_id = payload.get("sub", "")
        except Exception:
            await ws.close(code=4001, reason="Invalid token")
            return

        await ws_manager.connect(ws, tenant_id, user_id)
        try:
            while True:
                await ws.receive_text()  # keep alive
        except WebSocketDisconnect:
            ws_manager.disconnect(ws, tenant_id, user_id)

    return app


app = create_app()
