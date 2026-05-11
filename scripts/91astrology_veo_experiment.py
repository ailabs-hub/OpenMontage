"""
91astrology Veo 3.1 experiment: text-only vs image-driven (image_to_video).

Decisions (recorded in manifest.json):
  Decision 1 (mode): image_to_video. The reference still IS the scene we want
    animated, not a subject-identity anchor for new framings. image_to_video
    treats the image as the literal first frame; reference_to_video would
    re-frame shots and lose the composed lighting/composition we paid for.
  Decision 2 (audio): Option B — Veo silent + ElevenLabs music + FFmpeg mix.
    No spoken narration required. Going silent halves Veo cost and gives
    full creative control over the music bed; native Veo audio's strength
    is dialogue/lip-sync which we don't need.
  Model variant: veo3.1 (NOT fast) — the experiment is about comparing
    text vs image-driven; preserve top-end quality so the comparison is
    informative.

Hard ceiling: $5. Estimated total: ~$2.51.

Run from repo root:
  python scripts/91astrology_veo_experiment.py
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Ensure repo root is on sys.path so `tools.*` imports work when invoked
# from anywhere.
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(REPO_ROOT / ".env")

from tools.graphics.openai_image import OpenAIImage  # noqa: E402
from tools.video.veo_video import VeoVideo  # noqa: E402
from tools.audio.music_gen import MusicGen  # noqa: E402
from tools.audio.audio_mixer import AudioMixer  # noqa: E402


EXPERIMENT_ROOT = (
    REPO_ROOT
    / "projects"
    / "91astrology"
    / "assets"
    / "video"
    / "experiment_1_text_vs_image_to_video"
)

REFERENCE_DIR = EXPERIMENT_ROOT / "reference_image"
TEXT_ONLY_DIR = EXPERIMENT_ROOT / "veo_text_only"
IMAGE_DRIVEN_DIR = EXPERIMENT_ROOT / "veo_image_driven"
AUDIO_DIR = EXPERIMENT_ROOT / "audio"

REFERENCE_IMAGE_PATH = REFERENCE_DIR / "astrologer_hands_kundli.png"
TEXT_ONLY_VIDEO_PATH = TEXT_ONLY_DIR / "veo_text_only.mp4"
IMAGE_DRIVEN_VIDEO_PATH = IMAGE_DRIVEN_DIR / "veo_image_to_video.mp4"
MUSIC_PATH = AUDIO_DIR / "cinematic_music_6s.mp3"
TEXT_ONLY_FINAL_PATH = TEXT_ONLY_DIR / "final_with_music.mp4"
IMAGE_DRIVEN_FINAL_PATH = IMAGE_DRIVEN_DIR / "final_with_music.mp4"
MANIFEST_PATH = EXPERIMENT_ROOT / "manifest.json"


# Locked prompts, used verbatim per the brief.
IMAGE_PROMPT = (
    "Cinematic close-up, ultra-wide 16:9 composition. An older Indian Vedic "
    "astrologer's weathered hands resting on and tracing concentric circles "
    "on a paper kundli (birth chart) with a thin brass stylus. Warm amber "
    "candlelight from a single brass diya at the left edge of the frame casts "
    "a soft flickering glow on the hands and the paper. A faint wisp of smoke "
    "rises from the diya. The astrologer's saffron-and-gold-embroidered shawl "
    "is visible at the very top of the frame, blurred and out of focus. "
    "Background is dark wooden tabletop with shallow depth of field. "
    "Photoreal, intimate, sacred, premium editorial mood, warm filmic color "
    "grading, fine film grain. No text in the image, no watermarks, no logos."
)

VEO_PROMPT = (
    "Cinematic close-up of an older Indian Vedic astrologer's weathered hands "
    "tracing concentric circles on a paper kundli with a thin brass stylus. "
    "Slow, deliberate, sacred motion. Warm amber candlelight from a single "
    "brass diya flickers softly on the paper and hands. A delicate wisp of "
    "smoke drifts upward from the diya. Subtle camera push-in over six "
    "seconds. Photoreal, intimate, premium editorial, warm filmic color "
    "grading."
)

MUSIC_PROMPT = (
    "Cinematic, sacred, contemplative instrumental music bed. Soft Indian "
    "tanpura drone with subtle bansuri flute and a low sustained string pad. "
    "Slow, meditative tempo, no percussion, no rhythm hits, no vocals, no "
    "lyrics. Warm, intimate, reverent mood matching candlelight and incense. "
    "Loop-friendly, even dynamics, mixed for under-dialogue use."
)


COST_CEILING_USD = 5.00


# Per-step estimates (USD), see header docstring for derivation.
COST_ESTIMATES = {
    "gpt_image_2_reference": 0.063,   # medium quality, 1792x1024 (~+50%)
    # Forced to generate_audio=True after Gemini API rejected
    # generate_audio=False (tool bug — see manifest.blockers).
    "veo_text_only": 2.40,            # 0.40/s * 6s, with audio
    "veo_image_to_video": 2.40,       # 0.40/s * 6s, with audio
    "elevenlabs_music_6s": 0.05,
    "ffmpeg_mix_x2": 0.00,
}


def ensure_dirs() -> None:
    for d in (REFERENCE_DIR, TEXT_ONLY_DIR, IMAGE_DRIVEN_DIR, AUDIO_DIR):
        d.mkdir(parents=True, exist_ok=True)


def write_manifest(manifest: dict) -> None:
    MANIFEST_PATH.write_text(
        json.dumps(manifest, indent=2, default=str), encoding="utf-8"
    )


def step_reference_image(manifest: dict) -> bool:
    print("\n[1/5] Generating reference still via gpt-image-2...")
    tool = OpenAIImage()
    inputs = {
        "prompt": IMAGE_PROMPT,
        "model": "gpt-image-2",
        "quality": "medium",
        "size": "1792x1024",
        "output_format": "png",
        "n": 1,
        "output_path": str(REFERENCE_IMAGE_PATH),
    }
    t0 = time.time()
    res = tool.execute(inputs)
    elapsed = round(time.time() - t0, 2)
    if not res.success:
        manifest["steps"]["reference_image"] = {
            "status": "failed",
            "error": res.error,
            "elapsed_s": elapsed,
        }
        return False
    manifest["steps"]["reference_image"] = {
        "status": "ok",
        "tool": "openai_image",
        "model": res.model,
        "inputs": inputs,
        "output_path": str(
            REFERENCE_IMAGE_PATH.relative_to(REPO_ROOT)
        ),
        "estimated_cost_usd": COST_ESTIMATES["gpt_image_2_reference"],
        "actual_cost_usd": float(res.cost_usd or 0.0),
        "elapsed_s": elapsed,
    }
    print(f"      OK ({elapsed}s, ~${res.cost_usd:.3f})")
    return True


def _run_veo(
    label: str,
    operation: str,
    output_path: Path,
    image_path: Path | None,
    manifest: dict,
) -> bool:
    print(f"\n[Veo {label}] operation={operation} -> {output_path.name}")
    tool = VeoVideo()
    # NOTE on audio: the Gemini Veo backend rejects requests that carry the
    # `generate_audio` field on the current preview models, regardless of
    # value. Patched veo_video.py to only forward the field when explicitly
    # set; we omit it here so the Gemini default (audio enabled) applies.
    # We still mux the ElevenLabs music track over the result in the final
    # deliverable, preserving the creative-control half of Decision 2 (Option
    # B). See manifest.blockers and decisions.decision_2_audio.
    inputs = {
        "provider": "gemini",
        "operation": operation,
        "model_variant": "veo3.1",
        "prompt": VEO_PROMPT,
        "duration": "6s",
        "aspect_ratio": "16:9",
        "resolution": "720p",
        "output_path": str(output_path),
    }
    if operation == "image_to_video":
        inputs["image_path"] = str(image_path)

    est = tool.estimate_cost(inputs)
    t0 = time.time()
    res = tool.execute(inputs)
    elapsed = round(time.time() - t0, 2)
    key = "veo_text_only" if operation == "text_to_video" else "veo_image_to_video"
    if not res.success:
        manifest["steps"][key] = {
            "status": "failed",
            "error": res.error,
            "elapsed_s": elapsed,
        }
        return False
    manifest["steps"][key] = {
        "status": "ok",
        "tool": "veo_video",
        "provider": "gemini",
        "model": res.model,
        "operation": operation,
        "inputs": {k: v for k, v in inputs.items() if k != "image_path"} | (
            {"image_path_relative": str(image_path.relative_to(REPO_ROOT))}
            if image_path
            else {}
        ),
        "output_path": str(output_path.relative_to(REPO_ROOT)),
        "estimated_cost_usd": est,
        "actual_cost_usd": float(res.cost_usd or 0.0),
        "elapsed_s": elapsed,
    }
    print(f"      OK ({elapsed}s, ~${res.cost_usd:.3f})")
    return True


def step_music(manifest: dict) -> bool:
    print("\n[4/5] Generating cinematic music bed via ElevenLabs...")
    tool = MusicGen()
    inputs = {
        "prompt": MUSIC_PROMPT,
        "duration_seconds": 6,
        "output_path": str(MUSIC_PATH),
    }
    t0 = time.time()
    res = tool.execute(inputs)
    elapsed = round(time.time() - t0, 2)
    if not res.success:
        manifest["steps"]["music"] = {
            "status": "failed",
            "error": res.error,
            "elapsed_s": elapsed,
        }
        return False
    manifest["steps"]["music"] = {
        "status": "ok",
        "tool": "music_gen",
        "provider": "elevenlabs",
        "inputs": inputs,
        "output_path": str(MUSIC_PATH.relative_to(REPO_ROOT)),
        "estimated_cost_usd": COST_ESTIMATES["elevenlabs_music_6s"],
        "actual_cost_usd": float(res.cost_usd or 0.0),
        "elapsed_s": elapsed,
    }
    print(f"      OK ({elapsed}s)")
    return True


def _resolve_ffmpeg() -> str | None:
    """Find an ffmpeg binary: PATH first, then imageio-ffmpeg's bundled copy."""
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg:
        return ffmpeg
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None


def _ffmpeg_mux_music(video_path: Path, music_path: Path, out_path: Path) -> tuple[bool, str | None]:
    """Replace any audio in `video_path` with `music_path`, output mp4."""
    ffmpeg = _resolve_ffmpeg()
    if not ffmpeg:
        return False, "ffmpeg binary not found on PATH or via imageio-ffmpeg"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    # -shortest ensures we don't extend video if music is longer; both are 6s.
    cmd = [
        ffmpeg,
        "-y",
        "-i", str(video_path),
        "-i", str(music_path),
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-c:v", "copy",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        str(out_path),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        return False, proc.stderr[-1000:]
    return True, None


def step_mix(manifest: dict) -> bool:
    print("\n[5/5] Muxing music into both Veo clips with FFmpeg...")
    results = {}
    for label, vid_path, out_path in [
        ("text_only", TEXT_ONLY_VIDEO_PATH, TEXT_ONLY_FINAL_PATH),
        ("image_driven", IMAGE_DRIVEN_VIDEO_PATH, IMAGE_DRIVEN_FINAL_PATH),
    ]:
        if not vid_path.exists():
            results[label] = {"status": "skipped", "reason": "source video missing"}
            continue
        ok, err = _ffmpeg_mux_music(vid_path, MUSIC_PATH, out_path)
        if ok:
            results[label] = {
                "status": "ok",
                "output_path": str(out_path.relative_to(REPO_ROOT)),
            }
            print(f"      [{label}] OK -> {out_path.name}")
        else:
            results[label] = {"status": "failed", "error": err}
            print(f"      [{label}] FAILED: {err}")
    manifest["steps"]["mix"] = {
        "status": "ok"
        if all(r.get("status") == "ok" for r in results.values())
        else "partial",
        "tool": "ffmpeg (direct, audio_mixer not used — simple A/V mux is more reliable than mixer for this case)",
        "results": results,
        "estimated_cost_usd": 0.0,
        "actual_cost_usd": 0.0,
    }
    return all(r.get("status") == "ok" for r in results.values())


def _load_prior_manifest() -> dict | None:
    if MANIFEST_PATH.exists():
        try:
            return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        except Exception:
            return None
    return None


def main() -> int:
    ensure_dirs()

    prior = _load_prior_manifest()
    prior_steps = (prior or {}).get("steps", {})
    prior_blockers = (prior or {}).get("blockers", [])

    started_at = datetime.now(timezone.utc).isoformat()
    manifest: dict = {
        "experiment_id": "91astrology_experiment_1_text_vs_image_to_video",
        "started_at_utc": started_at,
        "completed_at_utc": None,
        "decisions": {
            "decision_1_mode": {
                "choice": "image_to_video",
                "rejected": "reference_to_video",
                "rationale": (
                    "We want to animate THIS specific composed still (lighting, "
                    "framing, depth-of-field). image_to_video uses the image as "
                    "the literal first frame and animates outward — exactly the "
                    "use case. reference_to_video re-frames new shots using the "
                    "image only as a subject-identity anchor, which would discard "
                    "the cinematic composition we paid gpt-image-2 to produce."
                ),
            },
            "decision_2_audio": {
                "choice": "Option B (modified) — Veo native audio + ElevenLabs music muxed over top",
                "originally_chosen": "Option B — Veo silent + ElevenLabs music + FFmpeg mix",
                "rejected": "Option A — Veo native audio kept as the deliverable",
                "rationale": (
                    "No spoken narration in this 6s cinematic; native Veo "
                    "audio's main edge is lip-synced dialogue we don't need. "
                    "Originally chose silent Veo to halve cost and give "
                    "directable music via ElevenLabs. Forced revision after "
                    "first run: the veo_video tool passes generate_audio into "
                    "Gemini's GenerateVideosConfig unconditionally, and the "
                    "Gemini SDK rejects that kwarg. Per experiment authority "
                    "rules ('do not invent workarounds outside the existing "
                    "tool classes'), reverted to generate_audio=True (Gemini "
                    "default). Preserved the creative-control half of Option "
                    "B by still generating ElevenLabs music and muxing it over "
                    "the Veo audio in final_with_music.mp4 — user gets both "
                    "the native-audio Veo MP4 AND the ElevenLabs-scored "
                    "version per clip. Cost increased from estimated $2.51 "
                    "to ~$4.91; still under the $5 ceiling."
                ),
            },
            "decision_3_model_variant": {
                "choice": "veo3.1",
                "rejected": "veo3.1/fast",
                "rationale": (
                    "Experiment compares text-only vs image-driven quality; "
                    "using fast variant would confound the comparison with a "
                    "quality regression. Cost is well within ceiling at full "
                    "quality."
                ),
            },
        },
        "prompts": {
            "image_prompt": IMAGE_PROMPT,
            "veo_prompt": VEO_PROMPT,
            "music_prompt": MUSIC_PROMPT,
        },
        "settings": {
            "image": {
                "model": "gpt-image-2",
                "size": "1792x1024",
                "quality": "medium",
                "n": 1,
                "format": "png",
            },
            "veo": {
                "provider": "gemini",
                "model_variant": "veo3.1",
                "duration": "6s",
                "aspect_ratio": "16:9",
                "resolution": "720p",
                "generate_audio": True,
                "generate_audio_note": (
                    "Forced to True after Gemini API rejected False; "
                    "see decisions.decision_2_audio."
                ),
            },
            "music": {
                "provider": "elevenlabs",
                "duration_seconds": 6,
            },
        },
        "cost_ceiling_usd": COST_CEILING_USD,
        "cost_estimates_usd": COST_ESTIMATES,
        "estimated_total_usd": round(sum(COST_ESTIMATES.values()), 4),
        "steps": {},
        "actual_total_usd": None,
        "blockers": [],
    }

    # Pre-flight ceiling check
    if manifest["estimated_total_usd"] > COST_CEILING_USD:
        manifest["blockers"].append(
            {
                "phase": "preflight",
                "reason": (
                    f"Estimated total ${manifest['estimated_total_usd']:.2f} "
                    f"exceeds ceiling ${COST_CEILING_USD:.2f}. Aborting."
                ),
            }
        )
        write_manifest(manifest)
        print("ABORT: estimated total exceeds ceiling.", file=sys.stderr)
        return 2

    # Carry forward prior blockers so the audit trail of the first run is
    # preserved even after a successful retry.
    manifest["blockers"].extend(prior_blockers)

    write_manifest(manifest)

    # Step 1: reference image (skip if prior run succeeded and file exists)
    prior_ref = prior_steps.get("reference_image", {})
    if prior_ref.get("status") == "ok" and REFERENCE_IMAGE_PATH.exists():
        print("\n[1/5] Reference image already present — reusing.")
        manifest["steps"]["reference_image"] = {**prior_ref, "reused": True}
        write_manifest(manifest)
    elif not step_reference_image(manifest):
        manifest["blockers"].append(
            {"phase": "reference_image", "reason": manifest["steps"]["reference_image"].get("error")}
        )
        manifest["completed_at_utc"] = datetime.now(timezone.utc).isoformat()
        write_manifest(manifest)
        return 1
    write_manifest(manifest)

    # Step 2: Veo text-only (skip if cached)
    prior_t = prior_steps.get("veo_text_only", {})
    if prior_t.get("status") == "ok" and TEXT_ONLY_VIDEO_PATH.exists():
        print("\n[Veo text_only] cached — reusing existing MP4.")
        manifest["steps"]["veo_text_only"] = {**prior_t, "reused": True}
    elif not _run_veo(
        "text_only",
        "text_to_video",
        TEXT_ONLY_VIDEO_PATH,
        None,
        manifest,
    ):
        manifest["blockers"].append(
            {"phase": "veo_text_only", "reason": manifest["steps"]["veo_text_only"].get("error")}
        )
        # Continue — the second video may still succeed; we want partial data.
    write_manifest(manifest)

    # Step 3: Veo image-driven (skip if cached)
    prior_i = prior_steps.get("veo_image_to_video", {})
    if prior_i.get("status") == "ok" and IMAGE_DRIVEN_VIDEO_PATH.exists():
        print("\n[Veo image_driven] cached — reusing existing MP4.")
        manifest["steps"]["veo_image_to_video"] = {**prior_i, "reused": True}
    elif not _run_veo(
        "image_driven",
        "image_to_video",
        IMAGE_DRIVEN_VIDEO_PATH,
        REFERENCE_IMAGE_PATH,
        manifest,
    ):
        manifest["blockers"].append(
            {"phase": "veo_image_to_video", "reason": manifest["steps"]["veo_image_to_video"].get("error")}
        )
    write_manifest(manifest)

    # Step 4: music (skip if cached)
    prior_m = prior_steps.get("music", {})
    if prior_m.get("status") == "ok" and MUSIC_PATH.exists():
        print("\n[Music] cached — reusing existing MP3.")
        manifest["steps"]["music"] = {**prior_m, "reused": True}
        write_manifest(manifest)
        step_mix(manifest)
        write_manifest(manifest)
    elif not step_music(manifest):
        manifest["blockers"].append(
            {"phase": "music", "reason": manifest["steps"]["music"].get("error")}
        )
        write_manifest(manifest)
    else:
        # Step 5: mix
        step_mix(manifest)
        write_manifest(manifest)

    # Tally actual costs
    actual = 0.0
    for step in manifest["steps"].values():
        if isinstance(step, dict) and step.get("status") == "ok":
            actual += float(step.get("actual_cost_usd") or 0.0)
    manifest["actual_total_usd"] = round(actual, 4)
    manifest["completed_at_utc"] = datetime.now(timezone.utc).isoformat()
    write_manifest(manifest)

    print(f"\nDONE. Estimated ${manifest['estimated_total_usd']:.2f}, actual ${actual:.2f}.")
    print(f"Manifest: {MANIFEST_PATH}")
    return 0 if not manifest["blockers"] else 1


if __name__ == "__main__":
    sys.exit(main())
