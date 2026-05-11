"""Google Veo 3.1 video generation.

Supports two providers:
- `gemini` (DEFAULT): native Google Gemini API via google-genai SDK. Uses
  GEMINI_API_KEY / GOOGLE_API_KEY. Cleanest path; no third-party account needed.
- `fal`: fal.ai relay. Uses FAL_KEY / FAL_AI_API_KEY. Kept for backwards compat.

Modes (both providers): text-to-video, image-to-video, reference-to-video,
first/last-frame interpolation.
"""

from __future__ import annotations

import base64
import json
import mimetypes
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

GEMINI_MODEL_MAP = {
    "veo3.1": "veo-3.1-generate-preview",
    "veo3.1/fast": "veo-3.1-fast-generate-preview",
    "veo3": "veo-3.0-generate-preview",
    "veo3/fast": "veo-3.0-fast-generate-preview",
}

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


class VeoVideo(BaseTool):
    name = "veo_video"
    version = "0.1.0"
    tier = ToolTier.GENERATE
    capability = "video_generation"
    provider = "veo"
    stability = ToolStability.EXPERIMENTAL
    execution_mode = ExecutionMode.SYNC
    determinism = Determinism.STOCHASTIC
    runtime = ToolRuntime.API

    dependencies = []
    install_instructions = (
        "Default provider is Google Gemini (recommended).\n"
        "  Set GEMINI_API_KEY (or GOOGLE_API_KEY) — get one at https://aistudio.google.com/apikey\n"
        "  pip install google-genai\n"
        "Alternative provider 'fal':\n"
        "  Set FAL_KEY (or FAL_AI_API_KEY) — get one at https://fal.ai/dashboard/keys"
    )
    agent_skills = ["ai-video-gen"]

    capabilities = ["text_to_video", "image_to_video", "reference_to_video", "first_last_frame_to_video"]
    supports = {
        "text_to_video": True,
        "image_to_video": True,
        "reference_to_video": True,
        "first_last_frame_to_video": True,
        "native_audio": True,
        "dialogue_generation": True,
        "ambient_sound": True,
    }
    best_for = [
        "videos with synchronized dialogue and audio",
        "cutting-edge quality from Google DeepMind",
        "ambient sound and music generation built in",
    ]
    not_good_for = ["budget projects", "offline generation", "quick iteration"]
    fallback_tools = ["kling_video", "minimax_video", "wan_video"]

    input_schema = {
        "type": "object",
        "required": ["prompt"],
        "properties": {
            "prompt": {"type": "string"},
            "provider": {
                "type": "string",
                "enum": ["gemini", "fal"],
                "default": "gemini",
                "description": "API route. 'gemini' (default) uses Google's native Gemini API; 'fal' relays through fal.ai.",
            },
            "operation": {
                "type": "string",
                "enum": ["text_to_video", "image_to_video", "reference_to_video", "first_last_frame_to_video"],
                "default": "text_to_video",
            },
            "model_variant": {
                "type": "string",
                "enum": ["veo3", "veo3/fast", "veo3.1", "veo3.1/fast"],
                "default": "veo3.1",
            },
            "duration": {
                "type": "string",
                "enum": ["4s", "6s", "8s"],
                "default": "8s",
                "description": "Duration in seconds",
            },
            "aspect_ratio": {
                "type": "string",
                "enum": ["16:9", "9:16"],
                "default": "16:9",
            },
            "generate_audio": {
                "type": "boolean",
                "default": True,
                "description": "Whether to generate synchronized audio",
            },
            "resolution": {
                "type": "string",
                "enum": ["720p", "1080p", "4k"],
                "default": "1080p",
            },
            "negative_prompt": {"type": "string"},
            "seed": {"type": "integer"},
            "auto_fix": {"type": "boolean", "default": True},
            "safety_tolerance": {
                "type": "string",
                "enum": ["1", "2", "3", "4", "5", "6"],
                "default": "4",
            },
            "image_url": {"type": "string", "description": "Reference image URL for image_to_video"},
            "image_path": {"type": "string", "description": "Local reference image path for image_to_video"},
            "reference_image_urls": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Reference image URLs for reference_to_video",
            },
            "reference_image_paths": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Local reference image paths for reference_to_video",
            },
            "first_frame_url": {"type": "string"},
            "first_frame_path": {"type": "string"},
            "last_frame_url": {"type": "string"},
            "last_frame_path": {"type": "string"},
            "output_path": {"type": "string"},
        },
    }

    resource_profile = ResourceProfile(
        cpu_cores=1, ram_mb=512, vram_mb=0, disk_mb=500, network_required=True
    )
    retry_policy = RetryPolicy(max_retries=2, retryable_errors=["rate_limit", "timeout"])
    idempotency_key_fields = ["prompt", "model_variant", "operation", "duration"]
    side_effects = ["writes video file to output_path", "calls fal.ai API"]
    user_visible_verification = [
        "Watch generated clip for visual quality and motion",
        "Listen for audio synchronization and quality",
    ]

    def _get_gemini_key(self) -> str | None:
        return os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")

    def _get_fal_key(self) -> str | None:
        return os.environ.get("FAL_KEY") or os.environ.get("FAL_AI_API_KEY")

    def _get_api_key(self, provider: str = "gemini") -> str | None:
        return self._get_gemini_key() if provider == "gemini" else self._get_fal_key()

    def get_status(self) -> ToolStatus:
        if self._get_gemini_key():
            try:
                import google.genai  # noqa: F401
                return ToolStatus.AVAILABLE
            except ImportError:
                pass
        if self._get_fal_key():
            return ToolStatus.AVAILABLE
        return ToolStatus.UNAVAILABLE

    def estimate_cost(self, inputs: dict[str, Any]) -> float:
        variant = inputs.get("model_variant", "veo3.1")
        duration_text = str(inputs.get("duration", "8s")).replace("s", "")
        duration = int(duration_text)
        resolution = inputs.get("resolution", "1080p")
        generate_audio = bool(inputs.get("generate_audio", True))

        if "fast" in variant:
            base_per_second = 0.10
            audio_per_second = 0.20
        else:
            if resolution == "4k":
                base_per_second = 0.40
                audio_per_second = 0.60
            else:
                base_per_second = 0.20
                audio_per_second = 0.40

        return (audio_per_second if generate_audio else base_per_second) * duration

    def estimate_runtime(self, inputs: dict[str, Any]) -> float:
        variant = inputs.get("model_variant", "veo3.1")
        if "fast" in variant:
            return 45.0
        return 120.0

    @staticmethod
    def _file_to_data_uri(path_str: str) -> str:
        path = Path(path_str)
        if not path.exists():
            raise FileNotFoundError(f"Input file not found: {path}")
        mime_type, _ = mimetypes.guess_type(path.name)
        if not mime_type:
            mime_type = "application/octet-stream"
        encoded = base64.b64encode(path.read_bytes()).decode("ascii")
        return f"data:{mime_type};base64,{encoded}"

    def _normalize_file_input(self, url_value: str | None, path_value: str | None) -> str | None:
        if url_value:
            return url_value
        if path_value:
            return self._file_to_data_uri(path_value)
        return None

    def execute(self, inputs: dict[str, Any]) -> ToolResult:
        provider = inputs.get("provider", "gemini")
        start = time.time()
        if provider == "gemini":
            result = self._execute_gemini(inputs, start)
        elif provider == "fal":
            result = self._execute_fal(inputs, start)
        else:
            return ToolResult(success=False, error=f"unknown provider '{provider}'")

        if result.success:
            self._write_sidecar(inputs, result, provider, start)
        return result

    def _write_sidecar(self, inputs: dict[str, Any], result: ToolResult, provider: str, start: float) -> None:
        try:
            output_path_str = (result.data or {}).get("output")
            if not output_path_str:
                return
            output_path = Path(output_path_str)
            sidecar = {
                "tool": self.name,
                "tool_version": self.version,
                "provider": provider,
                "model": (result.data or {}).get("model"),
                "operation": inputs.get("operation", "text_to_video"),
                "generated_at_utc": datetime.now(timezone.utc).isoformat(),
                "duration_seconds": round(time.time() - start, 2),
                "request": {
                    "user_prompt": inputs["prompt"],
                    "model_variant": inputs.get("model_variant", "veo3.1"),
                    "video_duration": inputs.get("duration", "8s"),
                    "aspect_ratio": inputs.get("aspect_ratio", "16:9"),
                    "resolution": inputs.get("resolution", "1080p"),
                    "generate_audio": inputs.get("generate_audio", True),
                    "negative_prompt": inputs.get("negative_prompt"),
                    "seed": inputs.get("seed"),
                    "image_path": inputs.get("image_path"),
                    "image_url": inputs.get("image_url"),
                    "reference_image_paths": inputs.get("reference_image_paths"),
                    "first_frame_path": inputs.get("first_frame_path"),
                    "last_frame_path": inputs.get("last_frame_path"),
                },
                "estimated_cost_usd": result.cost_usd,
                "video_path": str(output_path),
            }
            sidecar_path = output_path.with_suffix(output_path.suffix + ".prompt.json")
            sidecar_path.write_text(json.dumps(sidecar, indent=2, default=str), encoding="utf-8")
            if result.artifacts is not None:
                result.artifacts.append(str(sidecar_path))
            if isinstance(result.data, dict):
                result.data["prompt_log"] = str(sidecar_path)
        except Exception:
            pass

    def _execute_gemini(self, inputs: dict[str, Any], start: float) -> ToolResult:
        api_key = self._get_gemini_key()
        if not api_key:
            return ToolResult(
                success=False,
                error="GEMINI_API_KEY / GOOGLE_API_KEY not set. " + self.install_instructions,
            )

        try:
            from google import genai
            from google.genai import types
        except ImportError:
            return ToolResult(
                success=False,
                error="google-genai not installed. Run: pip install google-genai",
            )

        prompt = inputs["prompt"]
        op = inputs.get("operation", "text_to_video")
        variant = inputs.get("model_variant", "veo3.1")
        model = GEMINI_MODEL_MAP.get(variant, "veo-3.1-generate-preview")

        duration_str = str(inputs.get("duration", "8s"))
        duration_int = int(duration_str.replace("s", "")) if duration_str.endswith("s") else 8

        config_kwargs: dict[str, Any] = {}
        if inputs.get("aspect_ratio"):
            config_kwargs["aspect_ratio"] = inputs["aspect_ratio"]
        if inputs.get("negative_prompt"):
            config_kwargs["negative_prompt"] = inputs["negative_prompt"]
        if inputs.get("seed") is not None:
            config_kwargs["seed"] = inputs["seed"]
        if inputs.get("resolution"):
            config_kwargs["resolution"] = inputs["resolution"]
        config_kwargs["duration_seconds"] = duration_int
        # NOTE: The Gemini Veo backend rejects requests carrying the
        # `generate_audio` field on certain preview model/region combinations
        # ("generate_audio parameter is not supported in Gemini API"). The
        # google-genai SDK happily accepts it locally — failure only surfaces
        # when the API receives the request. Only forward the field when the
        # caller explicitly sets it; otherwise let the model's default apply.
        # Setting generate_audio=False when the API rejects the field is not
        # currently supported via this path (use the fal provider instead).
        if "generate_audio" in inputs and inputs["generate_audio"] is not None:
            config_kwargs["generate_audio"] = bool(inputs["generate_audio"])

        def _load_image(path_str: str | None, url_str: str | None):
            if path_str:
                p = Path(path_str)
                if not p.exists():
                    raise FileNotFoundError(f"Image not found: {p}")
                mime = mimetypes.guess_type(p.name)[0] or "image/png"
                return types.Image(image_bytes=p.read_bytes(), mime_type=mime)
            if url_str:
                import requests as _r
                resp = _r.get(url_str, timeout=60)
                resp.raise_for_status()
                mime = resp.headers.get("Content-Type", "image/png").split(";")[0]
                return types.Image(image_bytes=resp.content, mime_type=mime)
            return None

        kwargs: dict[str, Any] = {"model": model, "prompt": prompt}

        try:
            if op == "text_to_video":
                pass
            elif op == "image_to_video":
                img = _load_image(inputs.get("image_path"), inputs.get("image_url"))
                if not img:
                    return ToolResult(success=False, error="image_to_video requires image_path or image_url")
                kwargs["image"] = img
            elif op == "reference_to_video":
                paths = list(inputs.get("reference_image_paths") or [])
                urls = list(inputs.get("reference_image_urls") or [])
                refs = [_load_image(p, None) for p in paths] + [_load_image(None, u) for u in urls]
                refs = [r for r in refs if r is not None]
                if not refs:
                    return ToolResult(success=False, error="reference_to_video requires reference_image_paths or reference_image_urls")
                config_kwargs["reference_images"] = refs
            elif op == "first_last_frame_to_video":
                first_img = _load_image(inputs.get("first_frame_path"), inputs.get("first_frame_url"))
                last_img = _load_image(inputs.get("last_frame_path"), inputs.get("last_frame_url"))
                if not first_img or not last_img:
                    return ToolResult(success=False, error="first_last_frame_to_video requires first_frame and last_frame")
                kwargs["image"] = first_img
                config_kwargs["last_frame"] = last_img
            else:
                return ToolResult(success=False, error=f"unknown operation '{op}'")

            kwargs["config"] = types.GenerateVideosConfig(**config_kwargs)

            client = genai.Client(api_key=api_key)
            operation = client.models.generate_videos(**kwargs)

            poll_secs = 10
            max_wait = 600
            waited = 0
            while not operation.done and waited < max_wait:
                time.sleep(poll_secs)
                waited += poll_secs
                operation = client.operations.get(operation)

            if not operation.done:
                return ToolResult(success=False, error=f"Veo generation timed out after {max_wait}s")

            if not operation.response or not operation.response.generated_videos:
                err = getattr(operation, "error", None)
                return ToolResult(success=False, error=f"Veo returned no video. Error: {err}")

            video = operation.response.generated_videos[0]
            client.files.download(file=video.video)

            output_path = Path(inputs.get("output_path", "veo_output.mp4"))
            output_path.parent.mkdir(parents=True, exist_ok=True)
            video.video.save(str(output_path))

        except Exception as e:
            return ToolResult(success=False, error=f"Veo (gemini) failed: {e}")

        return ToolResult(
            success=True,
            data={
                "provider": "gemini",
                "model": model,
                "prompt": prompt,
                "output": str(output_path),
                "has_audio": bool(inputs.get("generate_audio", True)),
                "operation": op,
            },
            artifacts=[str(output_path)],
            cost_usd=self.estimate_cost(inputs),
            duration_seconds=round(time.time() - start, 2),
            model=model,
        )

    def _execute_fal(self, inputs: dict[str, Any], start: float) -> ToolResult:
        api_key = self._get_fal_key()
        if not api_key:
            return ToolResult(
                success=False,
                error="FAL_KEY / FAL_AI_API_KEY not set. " + self.install_instructions,
            )

        import requests

        operation = inputs.get("operation", "text_to_video")
        variant = inputs.get("model_variant", "veo3.1")
        duration = inputs.get("duration", "8s")

        # Current fal Veo 3.1 image-guided endpoints only accept 8-second clips.
        if variant == "veo3.1" and operation in {"reference_to_video", "first_last_frame_to_video"} and duration != "8s":
            return ToolResult(
                success=False,
                error=(
                    f"{operation} with {variant} currently requires duration='8s' on fal.ai; "
                    f"received duration='{duration}'"
                ),
            )

        # Build fal.ai model path
        operation_map = {
            "text_to_video": variant,
            "image_to_video": f"{variant}/image-to-video",
            "reference_to_video": f"{variant}/reference-to-video",
            "first_last_frame_to_video": f"{variant}/first-last-frame-to-video",
        }
        model_path = operation_map[operation]

        payload: dict[str, Any] = {"prompt": inputs["prompt"]}
        if inputs.get("duration"):
            payload["duration"] = inputs["duration"]
        if inputs.get("aspect_ratio"):
            payload["aspect_ratio"] = inputs["aspect_ratio"]
        if inputs.get("resolution"):
            payload["resolution"] = inputs["resolution"]
        if inputs.get("generate_audio") is not None:
            payload["generate_audio"] = inputs["generate_audio"]
        if inputs.get("negative_prompt"):
            payload["negative_prompt"] = inputs["negative_prompt"]
        if inputs.get("seed") is not None:
            payload["seed"] = inputs["seed"]
        if inputs.get("auto_fix") is not None:
            payload["auto_fix"] = inputs["auto_fix"]
        if inputs.get("safety_tolerance"):
            payload["safety_tolerance"] = inputs["safety_tolerance"]

        if operation == "image_to_video":
            image_value = self._normalize_file_input(inputs.get("image_url"), inputs.get("image_path"))
            if not image_value:
                return ToolResult(
                    success=False,
                    error="image_to_video requires image_url or image_path",
                )
            payload["image_url"] = image_value

        if operation == "reference_to_video":
            image_urls = list(inputs.get("reference_image_urls") or [])
            image_paths = list(inputs.get("reference_image_paths") or [])
            normalized = list(image_urls)
            normalized.extend(self._file_to_data_uri(path) for path in image_paths)
            if not normalized:
                return ToolResult(
                    success=False,
                    error="reference_to_video requires reference_image_urls or reference_image_paths",
                )
            payload["image_urls"] = normalized

        if operation == "first_last_frame_to_video":
            first_frame = self._normalize_file_input(
                inputs.get("first_frame_url"), inputs.get("first_frame_path")
            )
            last_frame = self._normalize_file_input(
                inputs.get("last_frame_url"), inputs.get("last_frame_path")
            )
            if not first_frame or not last_frame:
                return ToolResult(
                    success=False,
                    error="first_last_frame_to_video requires first_frame_url/path and last_frame_url/path",
                )
            payload["first_frame_url"] = first_frame
            payload["last_frame_url"] = last_frame

        headers = {
            "Authorization": f"Key {api_key}",
            "Content-Type": "application/json",
        }

        try:
            # Submit to queue API (async) — sync endpoint times out for video gen
            submit_resp = requests.post(
                f"https://queue.fal.run/fal-ai/{model_path}",
                headers=headers,
                json=payload,
                timeout=30,
            )
            submit_resp.raise_for_status()
            queue_data = submit_resp.json()
            status_url = queue_data["status_url"]
            response_url = queue_data["response_url"]

            # Poll until complete
            while True:
                time.sleep(5)
                status_resp = requests.get(status_url, headers=headers, timeout=15)
                status_resp.raise_for_status()
                status = status_resp.json().get("status", "UNKNOWN")
                if status == "COMPLETED":
                    break
                if status in ("FAILED", "CANCELLED"):
                    return ToolResult(
                        success=False,
                        error=f"Veo video generation {status.lower()}",
                    )

            # Fetch result
            result_resp = requests.get(response_url, headers=headers, timeout=30)
            if not result_resp.ok:
                detail = result_resp.text[:1000]
                return ToolResult(
                    success=False,
                    error=f"Veo video generation result fetch failed ({result_resp.status_code}): {detail}",
                )
            data = result_resp.json()

            video_url = data["video"]["url"]
            video_response = requests.get(video_url, timeout=120)
            video_response.raise_for_status()

            output_path = Path(inputs.get("output_path", "veo_output.mp4"))
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(video_response.content)

        except Exception as e:
            return ToolResult(success=False, error=f"Veo video generation failed: {e}")

        return ToolResult(
            success=True,
            data={
                "provider": "veo",
                "model": f"fal-ai/{model_path}",
                "prompt": inputs["prompt"],
                "output": str(output_path),
                "has_audio": inputs.get("generate_audio", True),
                "operation": operation,
            },
            artifacts=[str(output_path)],
            cost_usd=self.estimate_cost(inputs),
            duration_seconds=round(time.time() - start, 2),
            model=f"fal-ai/{model_path}",
        )
