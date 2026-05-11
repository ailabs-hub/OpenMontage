"""ByteDance Seedream 4.5 image generation via fal.ai API.

Seedream 4.5 is a unified text-to-image and image-editing model with
exceptional text rendering, multi-image composition, and 4K output support.
"""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any

from tools.base_tool import (
    BaseTool,
    Determinism,
    ExecutionMode,
    ResourceProfile,
    RetryPolicy,
    ToolResult,
    ToolRuntime,
    ToolStability,
    ToolStatus,
    ToolTier,
)


class SeedreamImage(BaseTool):
    name = "seedream_image"
    version = "0.1.0"
    tier = ToolTier.GENERATE
    capability = "image_generation"
    provider = "bytedance"
    stability = ToolStability.BETA
    execution_mode = ExecutionMode.SYNC
    determinism = Determinism.SEEDED
    runtime = ToolRuntime.API

    dependencies = []
    install_instructions = (
        "Set FAL_KEY to your fal.ai API key.\n"
        "  Get one at https://fal.ai/dashboard/keys\n"
        "  Seedream 4.5 is available at https://fal.ai/models/fal-ai/bytedance/seedream/v4.5"
    )
    agent_skills = ["seedream-4-5"]

    capabilities = [
        "generate_image",
        "generate_illustration",
        "text_to_image",
        "image_edit",
        "image_composite",
    ]
    supports = {
        "seed": True,
        "custom_size": True,
        "multiple_outputs": True,
        "image_edit": True,
        "text_in_image": True,
        "multi_reference": True,
    }
    best_for = [
        "images with accurate text/typography",
        "multi-image composition and style transfer",
        "precise image editing (inpainting, object replacement)",
        "high-resolution output up to 4K",
        "multilingual prompt understanding",
        "brand assets with exact color and label fidelity",
    ]
    not_good_for = [
        "offline generation",
        "budget-constrained bulk generation (flat $0.04/image)",
    ]

    input_schema = {
        "type": "object",
        "required": ["prompt"],
        "properties": {
            "prompt": {"type": "string", "description": "Text prompt describing the desired image"},
            "image_size": {
                "type": "string",
                "enum": [
                    "square_hd",
                    "square",
                    "portrait_4_3",
                    "portrait_16_9",
                    "landscape_4_3",
                    "landscape_16_9",
                    "auto_2K",
                    "auto_4K",
                ],
                "default": "landscape_16_9",
                "description": "Aspect ratio / resolution preset. Use auto_2K or auto_4K for max quality.",
            },
            "width": {
                "type": "integer",
                "description": "Custom width (1920-4096). Only used if image_size is not provided.",
            },
            "height": {
                "type": "integer",
                "description": "Custom height (1920-4096). Only used if image_size is not provided.",
            },
            "seed": {"type": "integer", "description": "Random seed for reproducibility"},
            "n": {
                "type": "integer",
                "default": 1,
                "minimum": 1,
                "maximum": 6,
                "description": "Number of separate model generations (1-6)",
            },
            "max_images": {
                "type": "integer",
                "default": 1,
                "minimum": 1,
                "maximum": 6,
                "description": "Enable multi-image generation when >1",
            },
            "generation_mode": {
                "type": "string",
                "enum": ["generate", "edit"],
                "default": "generate",
                "description": "Use 'edit' when providing source image(s) for editing",
            },
            "image_url": {
                "type": "string",
                "description": "Source image URL for edit mode",
            },
            "image_path": {
                "type": "string",
                "description": "Local source image path for edit mode",
            },
            "image_urls": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Multiple source image URLs for compositing (edit mode, up to 10)",
            },
            "image_paths": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Multiple local source image paths for compositing (edit mode, up to 10)",
            },
            "enable_safety_checker": {
                "type": "boolean",
                "default": True,
                "description": "Enable content safety filtering",
            },
            "output_path": {"type": "string"},
        },
    }

    resource_profile = ResourceProfile(
        cpu_cores=1, ram_mb=512, vram_mb=0, disk_mb=100, network_required=True
    )
    retry_policy = RetryPolicy(max_retries=2, retryable_errors=["rate_limit", "timeout"])
    idempotency_key_fields = ["prompt", "image_size", "seed", "generation_mode"]
    side_effects = ["writes image file(s) to output_path", "calls fal.ai API"]
    user_visible_verification = ["Inspect generated image for relevance, quality, and text accuracy"]

    def _get_api_key(self) -> str | None:
        return os.environ.get("FAL_KEY") or os.environ.get("FAL_AI_API_KEY")

    def get_status(self) -> ToolStatus:
        if self._get_api_key():
            return ToolStatus.AVAILABLE
        return ToolStatus.UNAVAILABLE

    def estimate_cost(self, inputs: dict[str, Any]) -> float:
        n = inputs.get("n", 1)
        return 0.04 * n

    def execute(self, inputs: dict[str, Any]) -> ToolResult:
        api_key = self._get_api_key()
        if not api_key:
            return ToolResult(
                success=False,
                error="No fal.ai API key found. " + self.install_instructions,
            )

        import requests

        start = time.time()
        prompt = inputs["prompt"]
        mode = inputs.get("generation_mode", "generate")
        n = inputs.get("n", 1)

        # Build payload
        payload: dict[str, Any] = {"prompt": prompt}

        if n > 1:
            payload["num_images"] = n

        max_images = inputs.get("max_images")
        if max_images and max_images > 1:
            payload["max_images"] = max_images

        # Size: prefer enum preset, fallback to custom dimensions
        image_size = inputs.get("image_size")
        width = inputs.get("width")
        height = inputs.get("height")
        if image_size:
            payload["image_size"] = image_size
        elif width and height:
            payload["image_size"] = {"width": width, "height": height}
        else:
            payload["image_size"] = "landscape_16_9"

        if inputs.get("seed") is not None:
            payload["seed"] = inputs["seed"]

        safety = inputs.get("enable_safety_checker")
        if safety is not None:
            payload["enable_safety_checker"] = safety

        # Determine endpoint
        if mode == "edit":
            endpoint = "fal-ai/bytedance/seedream/v4.5/edit"
            image_urls = self._resolve_image_urls(inputs)
            if image_urls:
                payload["image_urls"] = image_urls
            else:
                return ToolResult(
                    success=False,
                    error="Edit mode requires at least one source image via image_url, image_path, image_urls, or image_paths.",
                )
        else:
            endpoint = "fal-ai/bytedance/seedream/v4.5/text-to-image"

        try:
            response = requests.post(
                f"https://fal.run/{endpoint}",
                headers={
                    "Authorization": f"Key {api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=120,
            )
            response.raise_for_status()
            data = response.json()

            images = data.get("images", [])
            if not images:
                return ToolResult(
                    success=False,
                    error=f"No images returned from Seedream API. Response: {data}",
                )

            output_path = Path(inputs.get("output_path", "generated_image.png"))
            output_path.parent.mkdir(parents=True, exist_ok=True)

            saved_paths = []
            for idx, img_data in enumerate(images):
                image_url = img_data.get("url")
                if not image_url:
                    continue

                image_response = requests.get(image_url, timeout=60)
                image_response.raise_for_status()

                if len(images) == 1:
                    save_path = output_path
                else:
                    suffix = output_path.suffix
                    stem = output_path.stem
                    save_path = output_path.with_name(f"{stem}_{idx + 1}{suffix}")

                save_path.write_bytes(image_response.content)
                saved_paths.append(str(save_path))

            if not saved_paths:
                return ToolResult(
                    success=False,
                    error="Failed to download any images from Seedream response.",
                )

        except Exception as e:
            return ToolResult(success=False, error=f"Seedream generation failed: {e}")

        return ToolResult(
            success=True,
            data={
                "provider": "bytedance",
                "model": "seedream-4.5",
                "prompt": prompt,
                "mode": mode,
                "output": saved_paths[0] if len(saved_paths) == 1 else saved_paths,
                "seed": data.get("seed"),
            },
            artifacts=saved_paths,
            cost_usd=self.estimate_cost(inputs),
            duration_seconds=round(time.time() - start, 2),
            seed=data.get("seed"),
            model="seedream-4.5",
        )

    def _resolve_image_urls(self, inputs: dict[str, Any]) -> list[str]:
        """Resolve image inputs to URLs/paths for edit mode."""
        urls = []
        if inputs.get("image_urls"):
            urls.extend(inputs["image_urls"])
        if inputs.get("image_url"):
            urls.append(inputs["image_url"])
        # Local paths cannot be passed as URLs directly; fal.ai expects URLs.
        # If local paths are provided, they would need to be uploaded first.
        # For now, we accept URLs only for edit mode.
        return urls[:10]  # fal.ai limit
