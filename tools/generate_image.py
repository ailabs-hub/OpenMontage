"""Standalone image generation script for OpenMontage pipeline.

Usage:
    python tools/generate_image.py config.json
    python tools/generate_image.py '{"prompt":"...","width":1024,"height":1024,"output_path":"..."}'

The script auto-detects the OpenMontage root and adds it to sys.path,
so it can be run from any working directory.

Config keys:
    prompt (str, required): Image generation prompt
    width (int, default 1024): Output width
    height (int, default 1024): Output height
    output_path (str, required): Where to save the image
    provider (str, default "image_selector"): "image_selector", "openai_image", "flux_image", etc.
    model (str, optional): Model name for concrete providers (e.g., "gpt-image-2")
    preferred_provider (str, default "auto"): Passed to image_selector
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def _find_openmontage_root() -> Path:
    """Find OpenMontage root by looking for tools/tool_registry.py."""
    # If running from inside OpenMontage, use current file's parent.
    script_dir = Path(__file__).resolve().parent
    if (script_dir / "tool_registry.py").exists():
        return script_dir.parent

    # Walk upward from cwd.
    cwd = Path.cwd()
    for parent in [cwd] + list(cwd.parents):
        if (parent / "tools" / "tool_registry.py").exists():
            return parent

    raise RuntimeError(
        "Could not find OpenMontage root. "
        "Run this script from inside the OpenMontage repo."
    )


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python tools/generate_image.py <config.json> or '<inline-json>'", file=sys.stderr)
        return 1

    arg = sys.argv[1].strip()

    # Load config.
    if arg.endswith(".json") and Path(arg).exists():
        config = json.loads(Path(arg).read_text(encoding="utf-8"))
    else:
        config = json.loads(arg)

    # Ensure OpenMontage is importable.
    om_root = _find_openmontage_root()
    if str(om_root) not in sys.path:
        sys.path.insert(0, str(om_root))

    from tools.tool_registry import registry

    registry.discover()

    provider = config.get("provider", "image_selector")
    tool = registry.get(provider)

    if tool is None:
        available = list(registry._tools.keys())
        print(f"Error: provider '{provider}' not found. Available: {available}", file=sys.stderr)
        return 1

    # Build execute payload.
    payload = {
        "prompt": config["prompt"],
        "width": config.get("width", 1024),
        "height": config.get("height", 1024),
        "output_path": config["output_path"],
    }

    if provider == "image_selector":
        payload["preferred_provider"] = config.get("preferred_provider", "auto")
    elif "model" in config:
        payload["model"] = config["model"]

    result = tool.execute(payload)

    output = {
        "success": result.success,
        "output": result.data.get("output") if hasattr(result, "data") else None,
        "cost_usd": getattr(result, "cost_usd", 0.0),
    }
    if hasattr(result, "error") and result.error:
        output["error"] = str(result.error)

    print(json.dumps(output, indent=2))
    return 0 if result.success else 1


if __name__ == "__main__":
    sys.exit(main())
