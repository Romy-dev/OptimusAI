"""Image generation agent — creates visuals from text descriptions."""

import io
import uuid

import structlog
from PIL import Image

from app.agents.base import AgentResult, BaseAgent
from app.core.exceptions import ExternalServiceError
from app.integrations.image_gen import get_image_gen_client, download_image
from app.core.storage import storage_service

logger = structlog.get_logger()

def _get_system_prompt(brand_name: str, industry: str, country: str = "international") -> str:
    """Load the image_gen system prompt from the Jinja2 template."""
    from app.prompts.loader import get_prompt_manager
    return get_prompt_manager().get_prompt(
        "image_gen", "system",
        brand_name=brand_name,
        industry=industry,
        country=country,
    )


class ImageGenAgent(BaseAgent):
    name = "image_gen"
    description = "Generates visuals from text descriptions using ComfyUI"
    max_retries = 1
    confidence_threshold = 0.5

    async def execute(self, context: dict) -> AgentResult:
        from app.integrations.llm import get_llm_router

        media_suggestion = context.get("media_suggestion", "")
        brand = context.get("brand_context", {})
        aspect_ratio = context.get("aspect_ratio", "1:1")

        if not media_suggestion:
            return AgentResult(
                success=False,
                output={"error": "No media suggestion provided"},
                agent_name=self.name,
            )

        # 1. Expand media suggestion to technical prompt using LLM
        brand_name = brand.get("brand_name", "")
        industry = brand.get("industry", "")
        country = brand.get("country", "international")
        system = _get_system_prompt(brand_name, industry, country)

        llm = get_llm_router()
        llm_response = await llm.generate(
            task_type="support",
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": media_suggestion},
            ],
            temperature=0.7,
        )
        technical_prompt = llm_response.content.strip()
        logger.info("technical_prompt_generated", prompt=technical_prompt)

        # 2. Call ComfyUI for generation
        try:
            client = get_image_gen_client()
            from app.integrations.image_gen import ImageGenRequest
            
            gen_request = ImageGenRequest(
                prompt=technical_prompt,
                aspect_ratio=aspect_ratio,
            )
            gen_response = await client.generate(gen_request)

            # 3. Download the result
            if gen_response.local_path:
                # Fallback client saves locally
                with open(gen_response.local_path, "rb") as f:
                    image_bytes = f.read()
            else:
                # ComfyUI — download from its API
                image_bytes = await download_image(gen_response.filename)
            
            # 4. Upload to S3
            s3_key = f"brands/{brand.get('id')}/assets/{uuid.uuid4()}.png"
            
            file_url = await storage_service.upload_file(
                file_data=image_bytes,
                filename=f"{uuid.uuid4()}.png",
                content_type="image/png",
                folder=f"brands/{brand.get('id')}/assets",
            )
            
            # The upload_file method returns the key, but we need the full URL
            full_url = storage_service.get_public_url(file_url)

            return AgentResult(
                success=True,
                output={
                    "image_url": full_url,
                    "s3_key": file_url,
                    "prompt": technical_prompt,
                    "filename": gen_response.filename,
                    "metadata": gen_response.metadata,
                },
                confidence_score=0.9,  # Image generation is deterministic if it completes
                agent_name=self.name,
                execution_time_ms=gen_response.latency_ms,
            )

        except ExternalServiceError as e:
            logger.error("image_gen_failed", error=str(e))
            return AgentResult(
                success=False,
                output={"error": str(e)},
                agent_name=self.name,
            )

    async def validate_output(self, result: AgentResult) -> bool:
        return result.success and bool(result.output.get("image_url"))
