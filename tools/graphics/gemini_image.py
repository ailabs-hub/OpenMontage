"""Google Nano Banana / Gemini Image generation via google-genai SDK.

Distinct from `google_imagen.py` which calls the older Imagen `:predict` endpoint.
Nano Banana models are reasoning-based image generators built on Gemini and
called through `client.models.generate_content` with image response modality.
"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
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


class GeminiImage(BaseTool):
    name = "gemini_image"
    version = "0.1.0"
    tier = ToolTier.GENERATE
    capability = "image_generation"
    provider = "google_gemini"
    stability = ToolStability.BETA
    execution_mode = ExecutionMode.SYNC
    determinism = Determinism.STOCHASTIC
    runtime = ToolRuntime.API

    dependencies = []
    install_instructions = (
        "Set GOOGLE_API_KEY (or GEMINI_API_KEY) and install the SDK:\n"
        "  pip install google-genai\n"
        "Get a key at https://aistudio.google.com/apikey"
    )
    agent_skills = []

    capabilities = ["generate_image", "generate_illustration", "text_to_image"]
    supports = {
        "complex_instructions": True,
        "text_in_image": True,
        "reasoning": True,
        "aspect_ratio": True,
    }
    best_for = [
        "reasoning-driven compositions with real-world knowledge",
        "high-fidelity text rendering (incl. CJK, Devanagari, Arabic)",
        "marketing assets and brand-aware imagery at up to 4K",
    ]
    not_good_for = ["offline generation", "deterministic re-runs"]

    input_schema = {
        "type": "object",
        "required": ["prompt"],
        "properties": {
            "prompt": {"type": "string"},
            "model": {
                "type": "string",
                "enum": [
                    "gemini-3-pro-image-preview",
                    "gemini-3-flash-image",
                    "gemini-2.5-flash-image-preview",
                ],
                "default": "gemini-3-pro-image-preview",
            },
            "aspect_ratio": {
                "type": "string",
                "enum": [
                    "1:1", "2:3", "3:2", "3:4", "4:3", "4:5", "5:4",
                    "9:16", "16:9", "21:9",
                ],
                "default": "1:1",
            },
            "image_size": {
                "type": "string",
                "enum": ["1K", "2K", "4K"],
                "default": "2K",
            },
            "output_path": {"type": "string"},
        },
    }

    resource_profile = ResourceProfile(
        cpu_cores=1, ram_mb=512, vram_mb=0, disk_mb=100, network_required=True
    )
    retry_policy = RetryPolicy(max_retries=2, retryable_errors=["rate_limit", "timeout"])
    idempotency_key_fields = ["prompt", "aspect_ratio", "image_size", "model"]
    side_effects = ["writes image file to output_path", "calls Google Gemini API"]
    user_visible_verification = ["Inspect generated image for relevance and quality"]

    def _get_api_key(self) -> str | None:
        return os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")

    def get_status(self) -> ToolStatus:
        if not self._get_api_key():
            return ToolStatus.UNAVAILABLE
        try:
            import google.genai  # noqa: F401
        except ImportError:
            return ToolStatus.UNAVAILABLE
        return ToolStatus.AVAILABLE

    def estimate_cost(self, inputs: dict[str, Any]) -> float:
        # Token-based pricing: input $2/M, output $12/M.
        # Output token counts scale with resolution (1K~1500, 2K~3500, 4K~5500 for 16:9).
        size = inputs.get("image_size", "2K")
        size_tokens = {"1K": 1500, "2K": 3500, "4K": 5500}.get(size, 3500)
        input_tokens = 200  # prompt budget approximation
        return (input_tokens * 2 + size_tokens * 12) / 1_000_000

    def execute(self, inputs: dict[str, Any]) -> ToolResult:
        api_key = self._get_api_key()
        if not api_key:
            return ToolResult(
                success=False,
                error="No Google API key found. " + self.install_instructions,
            )

        try:
            from google import genai
            from google.genai import types
        except ImportError:
            return ToolResult(
                success=False,
                error="google-genai not installed. " + self.install_instructions,
            )

        start = time.time()
        model = inputs.get("model", "gemini-3-pro-image-preview")
        prompt = inputs["prompt"]
        aspect_ratio = inputs.get("aspect_ratio", "1:1")
        image_size = inputs.get("image_size", "2K")

        try:
            client = genai.Client(api_key=api_key)
            response = client.models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_modalities=["TEXT", "IMAGE"],
                    image_config=types.ImageConfig(
                        aspect_ratio=aspect_ratio,
                        image_size=image_size,
                    ),
                ),
            )

            output_path = Path(inputs.get("output_path", "generated_image.png"))
            output_path.parent.mkdir(parents=True, exist_ok=True)

            saved = False
            text_parts: list[str] = []
            for part in response.candidates[0].content.parts:
                if getattr(part, "inline_data", None):
                    output_path.write_bytes(part.inline_data.data)
                    saved = True
                elif getattr(part, "text", None):
                    text_parts.append(part.text)

            if not saved:
                return ToolResult(
                    success=False,
                    error=f"Gemini returned no image. Text only: {' | '.join(text_parts)[:500]}",
                )

            usage = getattr(response, "usage_metadata", None)
            usage_dict: dict[str, Any] | None = None
            if usage is not None:
                try:
                    usage_dict = usage.model_dump()
                except Exception:
                    usage_dict = {
                        "prompt_token_count": getattr(usage, "prompt_token_count", None),
                        "candidates_token_count": getattr(usage, "candidates_token_count", None),
                        "total_token_count": getattr(usage, "total_token_count", None),
                    }

            sidecar = {
                "tool": self.name,
                "tool_version": self.version,
                "provider": "google_gemini",
                "model": model,
                "generated_at_utc": datetime.now(timezone.utc).isoformat(),
                "duration_seconds": round(time.time() - start, 2),
                "request": {
                    "user_prompt": prompt,
                    "aspect_ratio": aspect_ratio,
                    "image_size": image_size,
                    "response_modalities": ["TEXT", "IMAGE"],
                },
                "model_text_output": "\n".join(text_parts) if text_parts else None,
                "google_revised_prompt": None,
                "usage_metadata": usage_dict,
                "image_path": str(output_path),
            }
            sidecar_path = output_path.with_suffix(output_path.suffix + ".prompt.json")
            sidecar_path.write_text(
                json.dumps(sidecar, indent=2, default=str), encoding="utf-8"
            )

        except Exception as e:
            return ToolResult(success=False, error=f"Gemini image generation failed: {e}")

        return ToolResult(
            success=True,
            data={
                "provider": "google_gemini",
                "model": model,
                "prompt": prompt,
                "model_text_output": "\n".join(text_parts) if text_parts else None,
                "aspect_ratio": aspect_ratio,
                "image_size": image_size,
                "output": str(output_path),
                "prompt_log": str(sidecar_path),
            },
            artifacts=[str(output_path), str(sidecar_path)],
            cost_usd=self.estimate_cost(inputs),
            duration_seconds=round(time.time() - start, 2),
            model=model,
        )
