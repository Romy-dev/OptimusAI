"""Tests for the ImageGen agent."""

import pytest
from unittest.mock import AsyncMock, patch

from app.agents.image_gen import ImageGenAgent
from app.agents.base import AgentResult


@pytest.fixture
def agent():
    return ImageGenAgent()


@pytest.fixture
def brand_context():
    return {
        "id": "123e4567-e89b-12d3-a456-426614174000",
        "brand_name": "Wax Élégance",
        "industry": "textile",
    }


class TestImageGenAgent:
    @pytest.mark.asyncio
    @patch("app.integrations.llm.LLMRouter.generate")
    @patch("app.integrations.image_gen.ComfyUIClient.generate")
    @patch("app.integrations.image_gen.download_image")
    @patch("app.core.storage.get_storage_client")
    async def test_execute_success(
        self,
        mock_storage,
        mock_download,
        mock_comfy,
        mock_llm,
        agent,
        brand_context,
    ):
        # Mock LLM response (technical prompt expansion)
        mock_llm.return_value = AsyncMock(
            content="Professional photo of wax fabric, vibrant colors, 8k",
            tokens_used=10,
            model="test-model"
        )

        # Mock ComfyUI response
        mock_comfy.return_value = AsyncMock(
            filename="optimus_test_123.png",
            prompt_id="prompt-123",
            latency_ms=5000,
            metadata={"prompt": "test prompt"}
        )

        # Mock download
        mock_download.return_value = b"fake-image-bytes"

        # Mock storage
        mock_s3 = AsyncMock()
        mock_s3.upload_file_object.return_value = "https://s3.optimusai.com/test.png"
        mock_storage.return_value = mock_s3

        context = {
            "media_suggestion": "Une belle photo de tissu wax sur un marché",
            "brand_context": brand_context,
            "aspect_ratio": "1:1"
        }

        result = await agent.execute(context)

        assert result.success is True
        assert result.output["image_url"] == "https://s3.optimusai.com/test.png"
        assert result.output["prompt"] == "Professional photo of wax fabric, vibrant colors, 8k"
        assert result.agent_name == "image_gen"
        
        # Verify calls
        mock_llm.assert_called_once()
        mock_comfy.assert_called_once()
        mock_s3.upload_file_object.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_no_suggestion(self, agent, brand_context):
        result = await agent.execute({"brand_context": brand_context})
        assert result.success is False
        assert "error" in result.output
