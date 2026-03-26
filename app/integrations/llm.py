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


class GeminiProvider(BaseLLMProvider):
    """Google Gemini via the google-genai SDK."""
    name = "gemini"

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or settings.gemini_api_key
        self._client = None

    def _get_client(self):
        if self._client is None:
            from google import genai
            self._client = genai.Client(api_key=self.api_key)
        return self._client

    async def generate(self, request: LLMRequest) -> LLMResponse:
        import asyncio
        start = time.perf_counter()
        model = request.model or "gemini-2.5-flash"

        # Build contents from messages
        system_instruction = None
        contents = []
        for msg in request.messages:
            if msg["role"] == "system":
                system_instruction = msg["content"]
            else:
                role = "user" if msg["role"] == "user" else "model"
                contents.append({"role": role, "parts": [{"text": msg["content"]}]})

        if not contents:
            contents = [{"role": "user", "parts": [{"text": "Bonjour"}]}]

        from google.genai import types
        config = types.GenerateContentConfig(
            temperature=request.temperature,
            max_output_tokens=request.max_tokens,
            system_instruction=system_instruction,
        )

        def _call():
            client = self._get_client()
            return client.models.generate_content(
                model=model,
                contents=contents,
                config=config,
            )

        response = await asyncio.to_thread(_call)
        latency = int((time.perf_counter() - start) * 1000)

        content = response.text or ""
        tokens = getattr(response.usage_metadata, "total_token_count", 0) if response.usage_metadata else 0
        finish = "stop"
        if response.candidates and response.candidates[0].finish_reason:
            finish = str(response.candidates[0].finish_reason)

        return LLMResponse(
            content=content,
            model=model,
            provider="gemini",
            tokens_used=tokens,
            latency_ms=latency,
            finish_reason=finish,
        )

    async def health_check(self) -> bool:
        return bool(self.api_key)


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


# === Intelligent Model Cascade ===
# Each task has a prioritized list of (provider, model) pairs.
# The router tries each in order, auto-skipping rate-limited or unavailable providers.

TASK_MODEL_CASCADE = {
    "copywriting": {
        "cascade": [
            ("gemini", "gemini-3-flash-preview"),
            ("gemini", "gemini-3.1-flash-lite-preview"),
            ("ollama", "mistral:latest"),
            ("anthropic", "claude-haiku-4-5-20251001"),
        ],
        "temperature": 0.8,
        "max_tokens": 1500,
    },
    "support": {
        "cascade": [
            ("gemini", "gemini-3.1-flash-lite-preview"),
            ("gemini", "gemini-2.5-flash-lite"),
            ("ollama", "mistral:latest"),
        ],
        "temperature": 0.3,
        "max_tokens": 500,
    },
    "reply": {
        "cascade": [
            ("gemini", "gemini-3.1-flash-lite-preview"),
            ("gemini", "gemini-2.5-flash-lite"),
            ("ollama", "mistral:latest"),
        ],
        "temperature": 0.5,
        "max_tokens": 300,
    },
    "classification": {
        "cascade": [
            ("gemini", "gemini-3.1-flash-lite-preview"),
            ("gemini", "gemini-2.5-flash-lite"),
            ("ollama", "mistral:latest"),
        ],
        "temperature": 0.0,
        "max_tokens": 50,
    },
    "moderation": {
        "cascade": [
            ("gemini", "gemini-3.1-flash-lite-preview"),
            ("gemini", "gemini-2.5-flash-lite"),
            ("ollama", "mistral:latest"),
        ],
        "temperature": 0.0,
        "max_tokens": 200,
    },
    "summary": {
        "cascade": [
            ("gemini", "gemini-3-flash-preview"),
            ("gemini", "gemini-3.1-flash-lite-preview"),
            ("ollama", "mistral:latest"),
        ],
        "temperature": 0.3,
        "max_tokens": 500,
    },
    "sales": {
        "cascade": [
            ("gemini", "gemini-3-flash-preview"),
            ("gemini", "gemini-3.1-flash-lite-preview"),
            ("ollama", "mistral:latest"),
        ],
        "temperature": 0.5,
        "max_tokens": 600,
    },
    "followup": {
        "cascade": [
            ("gemini", "gemini-3.1-flash-lite-preview"),
            ("gemini", "gemini-2.5-flash-lite"),
            ("ollama", "mistral:latest"),
        ],
        "temperature": 0.5,
        "max_tokens": 400,
    },
    "strategy": {
        "cascade": [
            ("gemini", "gemini-3-flash-preview"),
            ("gemini", "gemini-3.1-flash-lite-preview"),
            ("ollama", "mistral:latest"),
        ],
        "temperature": 0.7,
        "max_tokens": 2000,
    },
    "timing": {
        "cascade": [
            ("gemini", "gemini-3.1-flash-lite-preview"),
            ("gemini", "gemini-2.5-flash-lite"),
            ("ollama", "mistral:latest"),
        ],
        "temperature": 0.3,
        "max_tokens": 300,
    },
    "story": {
        "cascade": [
            ("gemini", "gemini-3-flash-preview"),
            ("gemini", "gemini-3.1-flash-lite-preview"),
            ("ollama", "mistral:latest"),
        ],
        "temperature": 0.8,
        "max_tokens": 2000,
    },
    "analysis": {
        "cascade": [
            ("gemini", "gemini-3-flash-preview"),
            ("gemini", "gemini-3.1-flash-lite-preview"),
            ("ollama", "mistral:latest"),
        ],
        "temperature": 0.3,
        "max_tokens": 1500,
    },
    "commerce": {
        "cascade": [
            ("gemini", "gemini-3-flash-preview"),
            ("gemini", "gemini-3.1-flash-lite-preview"),
            ("ollama", "mistral:latest"),
        ],
        "temperature": 0.4,
        "max_tokens": 800,
    },
}


class LLMRouter:
    """Intelligent LLM router with automatic cascade on rate limits.

    Tries providers in priority order. When a provider returns 429 (rate limit),
    it's temporarily disabled for that model and the next option is tried.
    """

    def __init__(self):
        self.providers: dict[str, BaseLLMProvider] = {}
        self._rate_limited: dict[str, float] = {}  # "provider:model" -> timestamp when usable again
        self._init_providers()

    def _init_providers(self):
        self.providers["ollama"] = OllamaProvider()
        if settings.gemini_api_key:
            self.providers["gemini"] = GeminiProvider()
        if settings.anthropic_api_key:
            self.providers["anthropic"] = AnthropicProvider()

    def _is_rate_limited(self, provider: str, model: str) -> bool:
        key = f"{provider}:{model}"
        if key not in self._rate_limited:
            return False
        if time.time() > self._rate_limited[key]:
            del self._rate_limited[key]
            return False
        return True

    def _mark_rate_limited(self, provider: str, model: str, retry_after: int = 60):
        key = f"{provider}:{model}"
        self._rate_limited[key] = time.time() + retry_after
        logger.warning("llm_rate_limited", provider=provider, model=model, retry_after=retry_after)

    async def generate(
        self,
        task_type: str,
        messages: list[dict],
        **overrides,
    ) -> LLMResponse:
        """Generate a response, cascading through providers on failure."""
        config = TASK_MODEL_CASCADE.get(task_type, TASK_MODEL_CASCADE["support"])
        cascade = config["cascade"]

        temperature = overrides.get("temperature", config.get("temperature", 0.7))
        max_tokens = overrides.get("max_tokens", config.get("max_tokens", 1024))

        last_error = None
        for provider_name, model in cascade:
            # Skip if provider not available
            provider = self.providers.get(provider_name)
            if not provider:
                continue

            # Skip if rate limited
            if self._is_rate_limited(provider_name, model):
                continue

            request = LLMRequest(
                messages=messages,
                model=overrides.get("model", model),
                temperature=temperature,
                max_tokens=max_tokens,
            )

            try:
                if not await provider.health_check():
                    continue

                response = await provider.generate(request)
                logger.info(
                    "llm_response",
                    task=task_type,
                    provider=provider_name,
                    model=response.model,
                    tokens=response.tokens_used,
                    latency_ms=response.latency_ms,
                )
                return response

            except Exception as e:
                last_error = e
                error_str = str(e)

                # Detect rate limiting (429)
                if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str or "rate" in error_str.lower():
                    # Extract retry delay if available
                    retry_after = 60
                    import re
                    match = re.search(r'retry in (\d+)', error_str.lower())
                    if match:
                        retry_after = int(match.group(1)) + 5
                    self._mark_rate_limited(provider_name, model, retry_after)
                else:
                    logger.warning(
                        "llm_cascade_failed",
                        task=task_type,
                        provider=provider_name,
                        model=model,
                        error=error_str[:100],
                    )

        from app.core.exceptions import LLMUnavailableError
        raise LLMUnavailableError(
            f"All providers exhausted for task '{task_type}'. Last error: {last_error}"
        )


# Singleton
_llm_router: LLMRouter | None = None


def get_llm_router() -> LLMRouter:
    global _llm_router
    if _llm_router is None:
        _llm_router = LLMRouter()
    return _llm_router
