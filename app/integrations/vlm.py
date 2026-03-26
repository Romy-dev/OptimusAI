"""Vision Language Model integration — analyzes images using Claude Vision or LLaVA.

Supports multiple providers:
1. Anthropic Claude (claude-3.5-sonnet) — best quality, API cost
2. Ollama LLaVA — free, self-hosted, good enough for design analysis
"""

import base64
import io
from typing import Any

import httpx
import structlog

from app.config import settings

logger = structlog.get_logger()


class VLMResponse:
    """Normalized VLM response."""
    def __init__(self, content: str, model: str, tokens_used: int = 0):
        self.content = content
        self.model = model
        self.tokens_used = tokens_used


class ClaudeVisionProvider:
    """Anthropic Claude Vision API."""

    async def analyze(self, image_data: bytes, prompt: str, system: str = "") -> VLMResponse:
        b64 = base64.standard_b64encode(image_data).decode("utf-8")
        media_type = "image/png"
        if image_data[:3] == b'\xff\xd8\xff':
            media_type = "image/jpeg"

        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {"type": "base64", "media_type": media_type, "data": b64},
                    },
                    {"type": "text", "text": prompt},
                ],
            }
        ]

        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": settings.anthropic_api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": "claude-sonnet-4-20250514",
                    "max_tokens": 4096,
                    "system": system or "You are an expert visual design analyst.",
                    "messages": messages,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            content = data["content"][0]["text"]
            tokens = data.get("usage", {}).get("input_tokens", 0) + data.get("usage", {}).get("output_tokens", 0)
            return VLMResponse(content=content, model="claude-sonnet-4-20250514", tokens_used=tokens)


class GeminiVisionProvider:
    """Google Gemini Vision — best quality VLM, native JSON output."""

    def __init__(self):
        self._client = None

    def _get_client(self):
        if self._client is None:
            from google import genai
            self._client = genai.Client(api_key=settings.gemini_api_key)
        return self._client

    async def analyze(self, image_data: bytes, prompt: str, system: str = "") -> VLMResponse:
        import asyncio
        from google.genai import types

        # Detect media type
        media_type = "image/png"
        if image_data[:3] == b'\xff\xd8\xff':
            media_type = "image/jpeg"

        image_part = types.Part.from_bytes(data=image_data, mime_type=media_type)

        full_prompt = prompt
        if system:
            full_prompt = f"{system}\n\n{prompt}"

        config = types.GenerateContentConfig(
            temperature=0.3,
            max_output_tokens=4096,
            response_mime_type="application/json",
        )

        def _call():
            client = self._get_client()
            return client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[full_prompt, image_part],
                config=config,
            )

        response = await asyncio.to_thread(_call)
        content = response.text or ""
        tokens = getattr(response.usage_metadata, "total_token_count", 0) if response.usage_metadata else 0

        return VLMResponse(content=content, model="gemini-2.5-flash", tokens_used=tokens)


class OllamaVisionProvider:
    """Ollama LLaVA / llava-llama3 / bakllava for local vision."""

    def __init__(self):
        self.base_url = settings.ollama_base_url
        self.model = "qwen2.5vl:7b"  # Best available VLM on Ollama — OCR 29 langs, design analysis

    async def analyze(self, image_data: bytes, prompt: str, system: str = "") -> VLMResponse:
        b64 = base64.standard_b64encode(image_data).decode("utf-8")

        full_prompt = prompt
        if system:
            full_prompt = f"{system}\n\n{prompt}"

        async with httpx.AsyncClient(timeout=300) as client:
            resp = await client.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": full_prompt,
                    "images": [b64],
                    "stream": False,
                    "options": {"temperature": 0.3, "num_predict": 4096},
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return VLMResponse(
                content=data.get("response", ""),
                model=self.model,
                tokens_used=data.get("eval_count", 0),
            )


class VLMRouter:
    """Routes VLM requests to the best available provider."""

    def __init__(self):
        self._provider = None

    def _get_provider(self):
        if self._provider:
            return self._provider

        # Prefer Gemini Vision (best quality + native JSON)
        if settings.gemini_api_key:
            self._provider = GeminiVisionProvider()
            logger.info("vlm_provider", provider="gemini_vision")
            return self._provider

        # Then Claude Vision
        if settings.anthropic_api_key:
            self._provider = ClaudeVisionProvider()
            logger.info("vlm_provider", provider="claude_vision")
            return self._provider

        # Fallback to Ollama
        self._provider = OllamaVisionProvider()
        logger.info("vlm_provider", provider="ollama_vision")
        return self._provider

    async def analyze_image(
        self,
        image_data: bytes,
        prompt: str,
        system: str = "",
    ) -> VLMResponse:
        """Analyze an image with the best available VLM."""
        provider = self._get_provider()
        try:
            return await provider.analyze(image_data, prompt, system)
        except Exception as e:
            logger.error("vlm_primary_failed", provider=type(provider).__name__, error=str(e))
            # Try fallbacks in order
            fallbacks = []
            if not isinstance(provider, GeminiVisionProvider) and settings.gemini_api_key:
                fallbacks.append(GeminiVisionProvider())
            if not isinstance(provider, OllamaVisionProvider):
                fallbacks.append(OllamaVisionProvider())
            for fb in fallbacks:
                try:
                    return await fb.analyze(image_data, prompt, system)
                except Exception as e2:
                    logger.error("vlm_fallback_failed", provider=type(fb).__name__, error=str(e2))
            raise


_vlm_router: VLMRouter | None = None


def get_vlm_router() -> VLMRouter:
    global _vlm_router
    if _vlm_router is None:
        _vlm_router = VLMRouter()
    return _vlm_router
