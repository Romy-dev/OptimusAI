"""ComfyUI integration — generates images using self-hosted workflows."""

import json
import uuid
import time
from typing import Any

import httpx
import structlog
from pydantic import BaseModel

from app.config import settings
from app.core.exceptions import ExternalServiceError

logger = structlog.get_logger()


class ImageGenRequest(BaseModel):
    prompt: str
    negative_prompt: str | None = "text, watermark, blurry, low quality, distorted"
    aspect_ratio: str = "1:1"  # "1:1", "16:9", "9:16"
    seed: int | None = None
    steps: int = 30
    cfg: float = 7.0


class ImageGenResponse(BaseModel):
    image_url: str | None = None
    local_path: str | None = None
    filename: str
    workflow_id: str
    metadata: dict[str, Any] = {}
    latency_ms: int


class ComfyUIClient:
    """Client for ComfyUI API."""

    def __init__(self, base_url: str | None = None):
        self.base_url = base_url or settings.comfyui_base_url
        self.timeout = 1200  # 20 minutes — FLUX on M4 16GB is slow

    async def generate(self, request: ImageGenRequest) -> ImageGenResponse:
        """Submit a prompt to ComfyUI and wait for the result."""
        start = time.perf_counter()
        prompt_id = str(uuid.uuid4())

        # Simple SDXL Text-to-Image workflow (example structure)
        # In a real app, this would be loaded from a template JSON
        workflow = self._build_workflow(request)

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                # 1. Queue the prompt
                resp = await client.post(
                    f"{self.base_url}/prompt",
                    json={"prompt": workflow, "client_id": "optimusai"},
                )
                resp.raise_for_status()
                data = resp.json()
                prompt_id = data["prompt_id"]

                logger.info("comfyui_prompt_queued", prompt_id=prompt_id)

                # 2. Poll for completion
                # In production, we'd use WebSockets for efficiency
                filename = await self._wait_for_completion(client, prompt_id)

                latency = int((time.perf_counter() - start) * 1000)

                return ImageGenResponse(
                    filename=filename,
                    workflow_id=prompt_id,
                    latency_ms=latency,
                    metadata={
                        "prompt": request.prompt,
                        "steps": request.steps,
                        "cfg": request.cfg,
                    },
                )

            except httpx.HTTPError as e:
                logger.error("comfyui_error", error=str(e))
                raise ExternalServiceError(f"ComfyUI failed: {e}")

    async def _wait_for_completion(self, client: httpx.AsyncClient, prompt_id: str) -> str:
        """Poll the history API until the prompt is finished."""
        max_attempts = 1200  # 20 minutes total (FLUX Q4 on M4 is ~4 min/step)
        for _ in range(max_attempts):
            resp = await client.get(f"{self.base_url}/history/{prompt_id}")
            resp.raise_for_status()
            history = resp.json()

            if prompt_id in history:
                # Execution finished successfully
                outputs = history[prompt_id].get("outputs", {})
                # Find the first output image
                for node_id in outputs:
                    if "images" in outputs[node_id]:
                        return outputs[node_id]["images"][0]["filename"]

                raise ExternalServiceError("ComfyUI finished but no image output found")

            # Check if it's currently in the queue
            queue_resp = await client.get(f"{self.base_url}/queue")
            queue_resp.raise_for_status()
            queue_data = queue_resp.json()

            # If not in queue and not in history, something went wrong
            pending = [p[1] for p in queue_data.get("queue_running", [])] + \
                      [p[1] for p in queue_data.get("queue_pending", [])]

            if prompt_id not in pending:
                # Check for errors in history again as a fallback
                # but if still not there, it might have crashed
                pass

            import asyncio
            await asyncio.sleep(1.0)

        raise ExternalServiceError("ComfyUI timed out while generating image")

    def _build_workflow(self, request: ImageGenRequest) -> dict:
        """Build FLUX.1 schnell GGUF workflow for ComfyUI."""
        seed = request.seed or int(time.time())
        width, height = self._get_dimensions(request.aspect_ratio)

        return {
            # Load FLUX GGUF model
            "1": {
                "class_type": "UnetLoaderGGUF",
                "inputs": {
                    "unet_name": "flux1-schnell-Q4_K_S.gguf"
                }
            },
            # Load CLIP + T5 text encoders
            "2": {
                "class_type": "DualCLIPLoaderGGUF",
                "inputs": {
                    "clip_name1": "clip_l.safetensors",
                    "clip_name2": "t5xxl_fp8_e4m3fn.safetensors",
                    "type": "flux"
                }
            },
            # Load VAE
            "3": {
                "class_type": "VAELoader",
                "inputs": {
                    "vae_name": "ae.safetensors"
                }
            },
            # CLIP Text Encode (positive prompt)
            "4": {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "clip": ["2", 0],
                    "text": request.prompt
                }
            },
            # Empty latent
            "5": {
                "class_type": "EmptySD3LatentImage",
                "inputs": {
                    "batch_size": 1,
                    "height": height,
                    "width": width
                }
            },
            # KSampler for FLUX schnell (4 steps, cfg 1.0)
            "6": {
                "class_type": "KSampler",
                "inputs": {
                    "model": ["1", 0],
                    "positive": ["4", 0],
                    "negative": ["4", 0],
                    "latent_image": ["5", 0],
                    "seed": seed,
                    "steps": 4,
                    "cfg": 1.0,
                    "sampler_name": "euler",
                    "scheduler": "simple",
                    "denoise": 1.0
                }
            },
            # VAE Decode
            "7": {
                "class_type": "VAEDecode",
                "inputs": {
                    "samples": ["6", 0],
                    "vae": ["3", 0]
                }
            },
            # Save Image
            "8": {
                "class_type": "SaveImage",
                "inputs": {
                    "filename_prefix": "OptimusAI",
                    "images": ["7", 0]
                }
            }
        }

    def _get_dimensions(self, aspect_ratio: str) -> tuple[int, int]:
        # Reduced resolution for 16GB M4 Mac
        ratios = {
            "1:1": (512, 512),
            "16:9": (768, 432),
            "9:16": (432, 768),
        }
        return ratios.get(aspect_ratio, (512, 512))


class FallbackImageClient:
    """Fallback: generate images via HuggingFace Inference API (free tier).
    Used when ComfyUI is unavailable or OOM on small machines.
    """

    async def generate(self, request: ImageGenRequest) -> ImageGenResponse:
        start = time.perf_counter()
        api_url = "https://router.huggingface.co/hf-inference/models/stabilityai/stable-diffusion-xl-base-1.0"

        async with httpx.AsyncClient(timeout=120) as client:
            try:
                resp = await client.post(
                    api_url,
                    json={"inputs": request.prompt},
                    headers={"Content-Type": "application/json"},
                )

                if resp.status_code == 200 and resp.headers.get("content-type", "").startswith("image"):
                    # Save to a temp file and return
                    filename = f"OptimusAI_{int(time.time())}.png"
                    output_path = f"/tmp/{filename}"
                    with open(output_path, "wb") as f:
                        f.write(resp.content)

                    latency = int((time.perf_counter() - start) * 1000)
                    return ImageGenResponse(
                        filename=filename,
                        local_path=output_path,
                        workflow_id="hf-inference",
                        latency_ms=latency,
                        metadata={"prompt": request.prompt, "source": "huggingface"},
                    )
                else:
                    error_msg = resp.text[:200]
                    raise ExternalServiceError(f"HuggingFace API error: {error_msg}")

            except httpx.HTTPError as e:
                raise ExternalServiceError(f"HuggingFace API failed: {e}")


async def download_image(filename: str) -> bytes:
    """Download the generated image from ComfyUI."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{settings.comfyui_base_url}/view", params={"filename": filename})
        resp.raise_for_status()
        return resp.read()


_image_gen_client = None


def get_image_gen_client():
    """Get image gen client — tries ComfyUI first, falls back to HuggingFace API."""
    global _image_gen_client
    if _image_gen_client is not None:
        return _image_gen_client

    # Check if ComfyUI is reachable
    import httpx
    try:
        resp = httpx.get(f"{settings.comfyui_base_url}/system_stats", timeout=3)
        if resp.status_code == 200:
            _image_gen_client = ComfyUIClient()
            logger.info("image_gen_client", provider="comfyui")
            return _image_gen_client
    except Exception:
        pass

    # Fallback to HuggingFace
    logger.info("image_gen_client", provider="huggingface_fallback")
    _image_gen_client = FallbackImageClient()
    return _image_gen_client
