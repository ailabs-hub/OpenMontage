---
name: veo-3-1
description: |
  Generate cinematic clips with Google Veo 3.1 — the OpenMontage native-Gemini video model. Use when (1) producing photoreal cinematic shots, hero clips, or trailer beats; (2) animating a still image as the literal first frame (image_to_video); (3) preserving a subject across multiple shots from up to 3 reference images (reference_to_video); (4) interpolating between a first and last frame (first_last_frame_to_video). Accessible via two providers in OpenMontage: Google Gemini API (DEFAULT — `provider="gemini"`, uses `GEMINI_API_KEY` / `GOOGLE_API_KEY`) and fal.ai (`provider="fal"`, uses `FAL_KEY`). Tool: `veo_video`.
allowed-tools: Bash, Read, Write
metadata:
  openclaw:
    requires:
      env_any:
        - GEMINI_API_KEY
        - GOOGLE_API_KEY
        - FAL_KEY
        - FAL_AI_API_KEY
---

# Veo 3.1 (Google)

Veo 3.1 is Google DeepMind's October 2025 cinematic video model, accessible through the Gemini API directly or relayed through fal.ai. Inside OpenMontage it is wrapped by `veo_video` with `provider="gemini"` as the default. Veo 3.1 Fast is also available via `model_variant="veo3.1/fast"`.

## When to pick Veo 3.1 vs Seedance 2.0

If `FAL_KEY` is set and the brief is cinematic / multi-shot / dialogue-heavy / camera-language-rich, **prefer Seedance 2.0 first** — it ranks #1 on Artificial Analysis Elo (1269) and beats Veo 3.1 on synced audio, multi-shot generation in one call, and director-level camera control. See the `seedance-2-0` Layer 3 skill for the authoritative cinematic prompting guide.

Pick Veo 3.1 specifically when:

- The user has only `GEMINI_API_KEY` (no fal.ai account) and wants to use their existing paid Gemini quota.
- The brief is a single calm photoreal shot where Veo's 1080p / 4K ceiling matters.
- You want first/last-frame interpolation (Seedance has reference-to-video but not first-last-frame as a distinct mode).
- Google brand alignment is a stated requirement.

## Prompting craft — read `seedance-2-0` first

The Seedance 2.0 prompting patterns transfer almost verbatim to Veo 3.1 because both are 2026-era reasoning-based video models with similar prompt syntax. Use `seedance-2-0/SKILL.md` as the authoritative source for:

- **Shot-structure declaration upfront** (the Higgsfield opener). Single biggest quality lever.
- **8-part legacy template** for single calm shots: framing → camera movement → subject → action beat(s) → setting → lighting/palette → style/grade → audio.
- **Beat-by-beat temporal markers** (`0–2s: …  2–4s: …  4–6s: …`).
- **Explicit camera negation** (`no cuts, no zoom, no stabilization`).
- **Realism enforcement phrase** (`no 3D, no cartoon, no VFX aesthetic — photorealistic textures, real skin pores, authentic fabric detail, grounded in reality`).
- **Audio direction** split into ambient + diegetic + music-textural. Music language stays textural, never trailer-swell.
- **Identity-anchor stacking** for reference-to-video shots.
- **Combat/action vocabulary** (specific verbs over `attacks`/`hits`/`fights`).

Veo 3.1 honors all of these. Don't re-derive the craft — apply the Seedance patterns and only overlay the deltas below.

## Veo 3.1 deltas vs Seedance 2.0 (the Veo-specific things)

These are the points where Veo 3.1 behaves differently from Seedance 2.0 and need explicit handling:

### 1. Native audio is always on, regardless of `generate_audio`
The Gemini API (as of May 2026) **rejects `generate_audio` as a `GenerateVideosConfig` kwarg** — passing `True` or `False` both fail. Veo always generates audio on the Gemini path. The `veo_video` tool therefore only forwards `generate_audio` to the underlying SDK when explicitly opted-in via the fal.ai provider.

Practical consequence: write an audio block in every Veo prompt. If you don't, Veo invents the soundscape from scratch. Direct it the way you would direct Seedance audio — ambient + diegetic + music-textural.

If you genuinely need a silent clip, route through `provider="fal"` (which does honor the toggle), or strip audio downstream in `audio_mixer` / FFmpeg.

### 2. No `revised_prompt` field
Unlike DALL-E 3, neither Veo nor gpt-image-2 returns a `revised_prompt`. The string you send is the string Veo renders from. The internal reasoning pass exists but is not surfaced. Don't expect to inspect a rewritten prompt in the sidecar.

### 3. Operations and their image inputs

| Operation | Image input | Behavior |
|---|---|---|
| `text_to_video` | none | Pure prompt-driven |
| `image_to_video` | one image (path or URL) | Image becomes literal first frame; Veo animates outward. Image MUST match the requested aspect ratio (16:9 or 9:16) and ≥720p, otherwise Veo silently crops/letterboxes. |
| `reference_to_video` | up to 3 subject images | Identity anchors across newly-framed shots. Image does NOT appear as a frame. Use for character/product consistency, not "animate this scene." |
| `first_last_frame_to_video` | first frame + last frame | Veo interpolates. First frame at `image_path`, last frame at `last_frame_path`. |

**Common mistake:** people conflate `image_to_video` with `reference_to_video`. They are different. If the user says "use this image as a reference," ask whether they want the image to BE the first frame (image_to_video) or to BE a subject anchor for new framings (reference_to_video). Default to image_to_video for "animate this scene"; reference_to_video for "keep this character consistent across cuts."

### 4. Aspect / duration / resolution constraints

| Field | Allowed | Default in `veo_video` |
|---|---|---|
| `aspect_ratio` | `16:9`, `9:16` (no 21:9, no 1:1) | `16:9` |
| `duration` | `4s`, `6s`, `8s` | `8s` |
| `resolution` | `720p`, `1080p`, `4k` | `1080p` |
| `model_variant` | `veo3.1`, `veo3.1/fast`, `veo3`, `veo3/fast` | `veo3.1` |

Note: Veo does not support 5s, 7s, 10s, 12s, or 15s durations the way Seedance does. Round to the nearest valid duration.

### 5. Text rendering inside the video is unreliable
Same warning as Seedance — don't ask Veo to render readable text inside the clip. Decorative-only text (e.g., the Devanagari hallucinated on a kundli paper) will preserve for ~1 frame and then warp during animation. If text matters, burn it in via Remotion / HyperFrames in compose.

### 6. Pricing (Gemini provider, per second of output)

| Variant | Resolution | $/sec (audio always on) |
|---|---|---|
| `veo3.1` standard | 720p | ~$0.40 |
| `veo3.1` standard | 1080p | ~$0.40 |
| `veo3.1` standard | 4K | ~$0.60 |
| `veo3.1/fast` | 720p / 1080p | ~$0.20 |

A 6s 720p standard clip ≈ $2.40. A 6s 720p Fast clip ≈ $1.20. Cost-cap your iteration cycles accordingly — block out shape with Fast, lock the seed, then upgrade to standard for the keeper.

### 7. The Gemini SDK polling pattern

The Gemini API returns a long-running operation. `veo_video` already handles polling at 10s intervals up to 600s (10 min). If you call the SDK directly (not through `veo_video`), use:

```python
from google import genai
client = genai.Client()
op = client.models.generate_videos(model="veo-3.1-generate-preview", prompt=PROMPT, ...)
while not op.done:
    time.sleep(10)
    op = client.operations.get(op)
video = op.response.generated_videos[0]
client.files.download(file=video.video)
video.video.save("output.mp4")
```

## Calling Veo inside OpenMontage

Always go through `video_selector` when possible (it adapts the prompt and routes by availability). Direct call:

```python
from tools.tool_registry import registry
registry.ensure_discovered()
veo = registry.get("veo_video")
veo.execute({
    "prompt": PROMPT,
    "provider": "gemini",        # default; explicit for clarity
    "operation": "image_to_video",
    "model_variant": "veo3.1",
    "duration": "6s",
    "aspect_ratio": "16:9",
    "resolution": "720p",
    "image_path": "projects/<p>/assets/images/.../still.png",
    "output_path": "projects/<p>/assets/video/.../clip.mp4",
})
```

The tool writes a `<output>.prompt.json` sidecar capturing prompt provenance + settings + duration + estimated cost.

## Verification checklist for every Veo shot

- [ ] Motion reads coherently at the chosen duration
- [ ] Audio is present and matches the prompted mood (no surprise dialogue, no jarring music swell)
- [ ] If `image_to_video`: the first frame matches the input image cleanly (no aspect mismatch, no crop tax)
- [ ] If `reference_to_video`: subject identity holds across the clip
- [ ] No readable text the model tried to render (decorative-only text is acceptable)
- [ ] Output duration matches what you requested
- [ ] Sidecar JSON is present and complete

## What to avoid

| Don't | Why |
|---|---|
| Pass `generate_audio=False` on `provider="gemini"` and expect a silent clip | Gemini API rejects the kwarg; tool now no-ops it. Use `provider="fal"` if silent matters. |
| Use `image_to_video` with an image whose aspect doesn't match `aspect_ratio` | Veo silently crops/letterboxes — no warning. Match aspects up front. |
| Expect `revised_prompt` in the sidecar | Veo doesn't surface one. The user's prompt = the rendered prompt. |
| Use Veo 3.1 Fast for slow-mo, multi-shot, or hero shots on first try | Same warning Seedance gives — Fast trades motion fidelity for cost. Use for previews only. |
| Bypass `veo_video` and write a one-off SDK call | Loses sidecar logging + cost reconciliation + provider abstraction. Use the tool. |

## Sources

- Gemini API video docs: https://ai.google.dev/gemini-api/docs/video
- Veo 3.1 launch announcement: https://developers.googleblog.com/introducing-veo-3-1-and-new-creative-capabilities-in-the-gemini-api/
- Vertex AI Veo reference: https://docs.cloud.google.com/vertex-ai/generative-ai/docs/model-reference/veo-video-generation
