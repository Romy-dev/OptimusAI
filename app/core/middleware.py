import uuid
import time

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.auth import decode_token

logger = structlog.get_logger()


class TenantMiddleware(BaseHTTPMiddleware):
    """Extracts tenant_id from JWT and attaches it to request state."""

    SKIP_PATHS = {"/health", "/api/docs", "/api/redoc", "/api/openapi.json"}

    async def dispatch(self, request: Request, call_next) -> Response:
        request.state.tenant_id = None
        request.state.user_id = None
        request.state.request_id = str(uuid.uuid4())

        # Skip auth for public paths
        if request.url.path in self.SKIP_PATHS:
            return await call_next(request)

        # Extract tenant from JWT if present
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            try:
                payload = decode_token(token)
                request.state.tenant_id = uuid.UUID(payload["tenant_id"])
                request.state.user_id = uuid.UUID(payload["sub"])
            except Exception:
                pass  # Auth errors handled by route dependencies

        # Log request
        start_time = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start_time) * 1000

        logger.info(
            "request_completed",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=round(duration_ms, 2),
            tenant_id=str(request.state.tenant_id) if request.state.tenant_id else None,
            request_id=request.state.request_id,
        )

        response.headers["X-Request-ID"] = request.state.request_id
        return response
