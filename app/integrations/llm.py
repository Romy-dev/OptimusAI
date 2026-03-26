"""LLM provider abstraction — routes requests to the right model."""

import time
from abc import ABC, abstractmethod
from enum import Enum

import httpx
import structlog
from pydantic import BaseModel

from app.config import settings

logger = structlog.get_logger()


class LLMRequest(BaseModel):
    messages: list[dict]  # [{"role": "system", "content": "..."}, ...]
    model: str | None = None
    temperature: float = 0.7
    max_tokens: int = 1024
    stop: list[str] | None = None


class LLMResponse(BaseModel):
    content: str
    model: str
    provider: str
    tokens_used: int
    latency_ms: int
    finish_reason: str


class BaseLLMProvider(ABC):
    name: str

    @abstractmethod
    async def generate(self, request: LLMRequest) -> LLMResponse:
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        ...


class OllamaProvider(BaseLLMProvider):
    name = "ollama"

    def __init__(self, base_url: str | None = None):
        self.base_url = base_url or settings.ollama_base_url

    async def generate(self, request: LLMRequest) -> LLMResponse:
        start = time.perf_counter()
        model = request.model or "qwen2:7b"

        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": model,
                    "messages": request.messages,
                    "options": {
                        "temperature": request.temperature,
                        "num_predict": request.max_tokens,
                    },
                    "stream": False,
                },
            )
            resp.raise_for_status()
            data = resp.json()

        latency = int((time.perf_counter() - start) * 1000)
        return LLMResponse(
            content=data["message"]["content"],
            model=model,
            provider="ollama",
            tokens_used=data.get("eval_count", 0),
            latency_ms=latency,
            finish_reason=data.get("done_reason", "stop"),
        )

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(f"{self.base_url}/api/tags")
                return resp.status_code == 200
        except Exception:
            return False


class AnthropicProvider(BaseLLMProvider):
    name = "anthropic"

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or settings.anthropic_api_key

    async def generate(self, request: LLMRequest) -> LLMResponse:
        start = time.perf_counter()
        model = request.model or "claude-haiku-4-5-20251001"

        # Separate system message from user messages
        system_content = ""
        messages = []
        for msg in request.messages:
            if msg["role"] == "system":
                system_content = msg["content"]
            else:
                messages.append(msg)

        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": model,
                    "max_tokens": request.max_tokens,
                    "system": system_content,
                    "messages": messages,
                    "temperature": request.temperature,
                },
            )
            resp.raise_for_status()
            data = resp.json()

        latency = int((time.perf_counter() - start) * 1000)
        content = data["content"][0]["text"] if data["content"] else ""
        tokens = data.get("usage", {})
        total_tokens = tokens.get("input_tokens", 0) + tokens.get("output_tokens", 0)

        return LLMResponse(
            content=content,
            model=model,
            provider="anthropic",
            tokens_used=total_tokens,
            latency_ms=latency,
            finish_reason=data.get("stop_reason", "end_turn"),
        )

    async def health_check(self) -> bool:
        return bool(self.api_key)


# === Model routing configuration ===

TASK_MODEL_CONFIG = {
    "copywriting": {
        "primary": "ollama",
        "model": "mistral:latest",
        "fallback": "anthropic",
        "fallback_model": "claude-haiku-4-5-20251001",
        "temperature": 0.8,
        "max_tokens": 1500,
    },
    "support": {
        "primary": "ollama",
        "model": "mistral:latest",
        "fallback": "anthropic",
        "fallback_model": "claude-haiku-4-5-20251001",
        "temperature": 0.3,
        "max_tokens": 500,
    },
    "reply": {
        "primary": "ollama",
        "model": "mistral:latest",
        "fallback": "anthropic",
        "fallback_model": "claude-haiku-4-5-20251001",
        "temperature": 0.5,
        "max_tokens": 300,
    },
    "classification": {
        "primary": "ollama",
        "model": "mistral:latest",
        "temperature": 0.0,
        "max_tokens": 50,
    },
    "moderation": {
        "primary": "ollama",
        "model": "mistral:latest",
        "fallback": "anthropic",
        "fallback_model": "claude-haiku-4-5-20251001",
        "temperature": 0.0,
        "max_tokens": 200,
    },
    "summary": {
        "primary": "ollama",
        "model": "mistral:latest",
        "fallback": "anthropic",
        "fallback_model": "claude-haiku-4-5-20251001",
        "temperature": 0.3,
        "max_tokens": 500,
    },
}


class LLMRouter:
    """Routes LLM requests to the correct provider based on task type."""

    def __init__(self):
        self.providers: dict[str, BaseLLMProvider] = {}
        self._init_providers()

    def _init_providers(self):
        self.providers["ollama"] = OllamaProvider()
        if settings.anthropic_api_key:
            self.providers["anthropic"] = AnthropicProvider()

    async def generate(
        self,
        task_type: str,
        messages: list[dict],
        **overrides,
    ) -> LLMResponse:
        """Generate a response for a specific task type."""
        config = TASK_MODEL_CONFIG.get(task_type, TASK_MODEL_CONFIG["support"])

        request = LLMRequest(
            messages=messages,
            model=overrides.get("model", config.get("model")),
            temperature=overrides.get("temperature", config.get("temperature", 0.7)),
            max_tokens=overrides.get("max_tokens", config.get("max_tokens", 1024)),
        )

        # Try primary provider
        primary_name = config["primary"]
        primary = self.providers.get(primary_name)
        if primary:
            try:
                if await primary.health_check():
                    response = await primary.generate(request)
                    logger.info(
                        "llm_response",
                        task=task_type,
                        provider=primary_name,
                        model=response.model,
                        tokens=response.tokens_used,
                        latency_ms=response.latency_ms,
                    )
                    return response
            except Exception as e:
                logger.warning(
                    "llm_primary_failed",
                    task=task_type,
                    provider=primary_name,
                    error=str(e),
                )

        # Try fallback
        fallback_name = config.get("fallback")
        if fallback_name:
            fallback = self.providers.get(fallback_name)
            if fallback:
                request.model = config.get("fallback_model")
                response = await fallback.generate(request)
                logger.info(
                    "llm_response_fallback",
                    task=task_type,
                    provider=fallback_name,
                    model=response.model,
                    tokens=response.tokens_used,
                    latency_ms=response.latency_ms,
                )
                return response

        from app.core.exceptions import LLMUnavailableError
        raise LLMUnavailableError(f"No LLM provider available for task: {task_type}")


# Singleton
_llm_router: LLMRouter | None = None


def get_llm_router() -> LLMRouter:
    global _llm_router
    if _llm_router is None:
        _llm_router = LLMRouter()
    return _llm_router
