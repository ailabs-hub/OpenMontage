"""Three-way image comparison for 91astrology project.

Generates 3 use cases (A: horoscope card stress-test, B: astrologer hero,
C: app onboarding splash) across 3 models (gpt-image-2, Imagen 4 Ultra,
Nano Banana Pro), 9 images total, in parallel.

Output structure:
    images/openai/<usecase>/gpt_image_2.png + sidecar
    images/google/<usecase>/imagen_4_ultra.png + sidecar
    images/google/<usecase>/nano_banana_pro.png + sidecar
    images/comparison/comparison_<n>_<usecase>/<model>.png + manifest.json
"""

from __future__ import annotations

import json
import shutil
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from tools.graphics.gemini_image import GeminiImage
from tools.graphics.google_imagen import GoogleImagen
from tools.graphics.openai_image import OpenAIImage


PROMPT_A_HOROSCOPE_STRESS = (
    "Premium mobile app horoscope card design, square 1:1 composition, app-card aesthetic for a "
    "Vedic astrology brand named '91 Astrology'. Vertically split layout: TOP 55% is a deep "
    "midnight-navy field (#0a1230) with a subtle starfield, holding a single hero illustration — "
    "an ornate antique-gold Aries (ram) glyph centered, stylized ram head with curved horns and a "
    "faint glowing amber eye, encircled by a thin gold zodiac wheel ring with twelve glyphs. "
    "BOTTOM 45% is a clean ivory-cream panel (#f5ecd9) separated from the top by a thin antique-gold "
    "horizontal divider line. The cream panel contains FIVE typographic elements stacked from top to "
    "bottom with generous spacing: "
    "(1) a large Devanagari Sanskrit headline that must read exactly 'मेष राशि' in serif gold (#c9a14d); "
    "(2) an English subhead that must read exactly 'ARIES — Today’s Reading' in clean small-caps navy; "
    "(3) a date line that must read exactly 'May 1, 2026' in light navy italics; "
    "(4) a four-line English horoscope paragraph in dark navy serif beginning with the exact words "
    "'Today brings a surge of creative momentum.' and continuing for three more grammatically correct "
    "sentences; "
    "(5) a small footer line in muted gold reading exactly 'Lucky Number: 7  •  Lucky Color: Crimson'. "
    "All English text must be perfectly legible, correctly spelled, and grammatically correct. The "
    "Devanagari headline must read clearly as 'मेष राशि'. Premium editorial typography, hierarchy is "
    "obvious, no clutter, no decorative flourishes around the text. Brand colors strictly: midnight "
    "navy #0a1230, antique gold #c9a14d, ivory cream #f5ecd9, dark navy text #1a2150. No watermarks, "
    "no app UI chrome, no logos other than the implied brand."
)

PROMPT_B_ASTROLOGER_HERO = (
    "Photoreal cinematic portrait, ultra-wide 16:9 landscape composition. An older Indian Vedic "
    "astrologer in his late 60s — silver-gray beard, weathered serene face, kind eyes, wearing a "
    "saffron and cream traditional kurta with a gold-embroidered shawl draped over one shoulder. "
    "He sits cross-legged at a low dark wooden table, peering down at a hand-drawn paper kundli "
    "(traditional Indian birth chart) marked with stylized Devanagari notations and concentric "
    "geometric divisions, holding a thin brass stylus. Three small brass diyas (oil lamps) glow on "
    "the table around the chart, casting warm amber rim light from camera-left across his face, "
    "hands, and the kundli paper. Deep shadow falls on the right side of the frame. Background is "
    "an out-of-focus traditional study with brass artifacts and a faintly visible bookshelf, all "
    "dimmed into soft bokeh. The right ~40 percent of the frame is intentionally darker and emptier — "
    "clean negative space for headline typography overlay. Shot on a 50mm prime lens, shallow depth "
    "of field, warm filmic color grading, fine film grain. Photoreal, sacred, intimate, premium "
    "editorial mood. No text in the image, no watermarks."
)

PROMPT_C_ONBOARDING_SPLASH = (
    "Mobile app onboarding screen, 9:16 vertical portrait composition. TOP 60 percent is a dramatic "
    "cosmic illustration: deep midnight-navy void with eight stylized planetary spheres aligned along "
    "a soft glowing ecliptic curve that arcs from upper-left down to lower-right of this top section. "
    "Each planet is a small luminous sphere in a different tonal gold (amber, brass, champagne, "
    "antique gold, rose gold). Fine starfield and drifting gold particle dust around them. A thin "
    "gold zodiac wheel arc is suggested faintly behind the planets. BOTTOM 40 percent is a clean "
    "ivory-cream rounded UI panel with a soft drop shadow, separated from the cosmic art above by a "
    "smooth horizontal blend. The cream panel contains, vertically stacked with generous spacing: "
    "(1) a bold dark-navy headline that must read exactly 'Discover Your Cosmic Story' in modern "
    "sans-serif; (2) a subhead in Devanagari that must read exactly 'अपनी ज्योतिषीय यात्रा शुरू करें' in elegant "
    "serif gold; (3) a single primary CTA pill button at the bottom in deep antique gold with white "
    "sans-serif label that must read exactly 'Begin Your Reading'. All text must be perfectly legible "
    "and correctly spelled. Generous whitespace, premium app aesthetic. No other UI chrome, no status "
    "bar, no watermarks."
)

USECASES: dict[str, dict] = {
    "horoscope_card_aries": {
        "comparison_num": 1,
        "prompt": PROMPT_A_HOROSCOPE_STRESS,
        "stress_test": True,
        "openai_size": "1024x1024",
        "google_aspect": "1:1",
        "stress_notes": (
            "Stress-tested: 5 distinct typographic elements, mixed Sanskrit + English, "
            "exact text strings demanded, exact brand hex colors, vertical split layout."
        ),
    },
    "astrologer_hero": {
        "comparison_num": 2,
        "prompt": PROMPT_B_ASTROLOGER_HERO,
        "stress_test": False,
        "openai_size": "1536x1024",
        "google_aspect": "16:9",
    },
    "onboarding_splash": {
        "comparison_num": 3,
        "prompt": PROMPT_C_ONBOARDING_SPLASH,
        "stress_test": False,
        "openai_size": "1024x1536",
        "google_aspect": "9:16",
    },
}

IMAGES_BASE = ROOT / "projects" / "91astrology" / "assets" / "images"
OPENAI_BASE = IMAGES_BASE / "openai"
GOOGLE_BASE = IMAGES_BASE / "google"
COMPARISON_BASE = IMAGES_BASE / "comparison"


def run_openai(usecase: str, cfg: dict):
    out = OPENAI_BASE / usecase / "gpt_image_2.png"
    return ("gpt_image_2", usecase, OpenAIImage().execute({
        "prompt": cfg["prompt"],
        "model": "gpt-image-2",
        "size": cfg["openai_size"],
        "quality": "medium",
        "output_format": "png",
        "n": 1,
        "output_path": str(out),
    }))


def run_imagen(usecase: str, cfg: dict):
    out = GOOGLE_BASE / usecase / "imagen_4_ultra.png"
    return ("imagen_4_ultra", usecase, GoogleImagen().execute({
        "prompt": cfg["prompt"],
        "model": "imagen-4.0-ultra-generate-001",
        "aspect_ratio": cfg["google_aspect"],
        "number_of_images": 1,
        "output_path": str(out),
    }))


def run_gemini(usecase: str, cfg: dict):
    out = GOOGLE_BASE / usecase / "nano_banana_pro.png"
    return ("nano_banana_pro", usecase, GeminiImage().execute({
        "prompt": cfg["prompt"],
        "model": "gemini-3-pro-image-preview",
        "aspect_ratio": cfg["google_aspect"],
        "image_size": "2K",
        "output_path": str(out),
    }))


def main():
    start = time.time()
    futures = []
    with ThreadPoolExecutor(max_workers=9) as ex:
        for usecase, cfg in USECASES.items():
            futures.append(ex.submit(run_openai, usecase, cfg))
            futures.append(ex.submit(run_imagen, usecase, cfg))
            futures.append(ex.submit(run_gemini, usecase, cfg))

        results: dict[tuple[str, str], object] = {}
        for f in as_completed(futures):
            try:
                model_name, usecase, r = f.result()
                results[(usecase, model_name)] = r
                tag = "OK" if r.success else f"ERR: {r.error[:200]}"
                cost = getattr(r, "cost_usd", None)
                dur = getattr(r, "duration_seconds", None)
                print(f"[{usecase} / {model_name}] {tag}  cost=${cost}  dur={dur}s")
            except Exception as e:  # noqa: BLE001
                print(f"FATAL: {e}")

    # Build comparison subfolders + manifests
    for usecase, cfg in USECASES.items():
        n = cfg["comparison_num"]
        cmp_dir = COMPARISON_BASE / f"comparison_{n}_{usecase}"
        cmp_dir.mkdir(parents=True, exist_ok=True)

        manifest = {
            "comparison_number": n,
            "usecase": usecase,
            "stress_test": cfg.get("stress_test", False),
            "stress_notes": cfg.get("stress_notes"),
            "prompt": cfg["prompt"],
            "models": {},
        }

        for model_name, src_dir in [
            ("gpt_image_2", OPENAI_BASE / usecase),
            ("imagen_4_ultra", GOOGLE_BASE / usecase),
            ("nano_banana_pro", GOOGLE_BASE / usecase),
        ]:
            src = src_dir / f"{model_name}.png"
            sidecar = src_dir / f"{model_name}.png.prompt.json"
            entry: dict = {"primary": str(src.relative_to(ROOT)) if src.exists() else None}
            if src.exists():
                dst = cmp_dir / f"{model_name}.png"
                shutil.copy2(src, dst)
                entry["comparison_copy"] = str(dst.relative_to(ROOT))
            if sidecar.exists():
                entry["sidecar"] = str(sidecar.relative_to(ROOT))
                try:
                    sc = json.loads(sidecar.read_text(encoding="utf-8"))
                    entry["duration_seconds"] = sc.get("duration_seconds")
                    entry["model"] = sc.get("model")
                    if "raw_response_metadata" in sc and isinstance(sc["raw_response_metadata"], dict):
                        usage = sc["raw_response_metadata"].get("usage")
                        if usage:
                            entry["usage_metadata"] = usage
                    if "usage_metadata" in sc:
                        entry["usage_metadata"] = sc["usage_metadata"]
                except Exception:
                    pass
            r = results.get((usecase, model_name))
            if r is not None:
                entry["success"] = bool(r.success)
                entry["cost_usd_estimate"] = getattr(r, "cost_usd", None)
                if not r.success:
                    entry["error"] = r.error
            manifest["models"][model_name] = entry

        (cmp_dir / "manifest.json").write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    elapsed = round(time.time() - start, 1)
    total_cost = 0.0
    for r in results.values():
        c = getattr(r, "cost_usd", 0) or 0
        total_cost += c
    print(f"\nALL DONE in {elapsed}s. Estimated total cost: ${total_cost:.4f}")


if __name__ == "__main__":
    main()
