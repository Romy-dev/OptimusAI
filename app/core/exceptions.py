from fastapi import Request
from fastapi.responses import JSONResponse


class OptimusError(Exception):
    """Base exception for all OptimusAI errors."""

    status_code: int = 500
    error_code: str = "internal_error"
    message: str = "An internal error occurred"

    def __init__(self, message: str | None = None, details: dict | None = None):
        self.message = message or self.__class__.message
        self.details = details or {}
        super().__init__(self.message)


class NotFoundError(OptimusError):
    status_code = 404
    error_code = "not_found"
    message = "Resource not found"


class AlreadyExistsError(OptimusError):
    status_code = 409
    error_code = "already_exists"
    message = "Resource already exists"


class PermissionDeniedError(OptimusError):
    status_code = 403
    error_code = "permission_denied"
    message = "Permission denied"


class QuotaExceededError(OptimusError):
    status_code = 429
    error_code = "quota_exceeded"
    message = "Quota exceeded for this resource"


class InvalidInputError(OptimusError):
    status_code = 422
    error_code = "invalid_input"
    message = "Invalid input provided"


class ExternalServiceError(OptimusError):
    status_code = 502
    error_code = "external_service_error"
    message = "External service is unavailable"


class TokenExpiredError(OptimusError):
    status_code = 401
    error_code = "token_expired"
    message = "Social account token has expired"


class LLMUnavailableError(OptimusError):
    status_code = 503
    error_code = "llm_unavailable"
    message = "AI model is currently unavailable"


class PromptInjectionDetected(OptimusError):
    status_code = 400
    error_code = "prompt_injection"
    message = "Suspicious input detected"


async def optimus_exception_handler(request: Request, exc: OptimusError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.error_code,
                "message": exc.message,
                "details": exc.details,
            }
        },
    )
