---
name: seedream-4-5
description: ByteDance Seedream 4.5 image generation — prompting best practices, parameter tuning, text rendering, multi-image composition, and editing workflows via fal.ai.
metadata:
  author: ByteDance / fal.ai
  version: "1.0.0"
  tags: seedream, bytedance, image-generation, text-rendering, image-editing, multi-reference
---

# Seedream 4.5 — Prompting & Usage Guide

Use this skill when generating prompts for ByteDance Seedream 4.5 via `tools/graphics/seedream_image.py`.

## When to Use

- Creating images with **accurate text/typography** (logos, labels, ad copy, UI mockups)
- **Multi-image composition** — fusing style, subject, and environment from multiple references
- **Precise image editing** — object replacement, inpainting, style transfer while preserving composition
- **High-resolution** hero assets (up to 4K)
- **Multilingual prompts** — strong comprehension across 725+ languages
- **Brand assets** where exact color and label fidelity matters

## Quick Reference

### Model Selection

| Use Case | Recommended Mode | Notes |
|---|---|---|
| Text-to-image generation | `text-to-image` | Standard generation from prompt |
| Image editing / inpainting | `edit` | Provide source image(s) + edit prompt |
| Multi-reference composition | `edit` or `text-to-image` | Pass up to 10 reference images |
| Bulk variations | `text-to-image` with `n=4-6` | $0.04 per image regardless of size |

### Resolution Presets

| Preset | Dimensions | Best For |
|---|---|---|
| `square_hd` | ~1024×1024 | Social posts, profile images |
| `square` | ~512×512 | Thumbnails, icons |
| `portrait_4_3` | ~768×1024 | Mobile portraits |
| `portrait_16_9` | ~576×1024 | Stories, vertical video frames |
| `landscape_4_3` | ~1024×768 | Standard photography |
| `landscape_16_9` | ~1024×576 | Video frames, banners |
| `auto_2K` | Up to 2048px | High-quality production |
| `auto_4K` | Up to 4096px | Maximum detail, hero assets |

**Custom dimensions:** Pass `width` + `height` (1920–4096px per axis, total pixels 2560×1440 to 4096×4096).

### Cost & Speed

- **$0.04 per image** — flat rate regardless of resolution
- **~15–25 seconds** typical generation time (fal.ai)
- **Batch:** `n=1-6` separate generations per call

---

## Prompt Structure

Seedream 4.5 responds best to **30–100 word prompts** with clear subject-action-context-lighting ordering.

### Basic Formula

```
[Subject] + [Action/Pose] + [Style/Medium] + [Context/Setting] + [Lighting] + [Technical/Camera]
```

### Expanded Framework

```
[Main Subject] — who/what is the focus, with specific attributes
[Action/Pose] — what they're doing, dynamic or static
[Environment] — where, setting, background details
[Style/Medium] — artistic approach, rendering style
[Lighting] — light source, quality, mood, color temperature
[Composition] — framing, camera angle, negative space
[Technical] — camera body, lens, film stock, resolution cues
[Text/Label Instructions] — exact text to render (if applicable)
```

---

## Text Rendering — Seedream's Superpower

Seedream 4.5 has **exceptional text accuracy** compared to most image models. Use these patterns:

### Exact String Rendering

```
The label reads exactly: "91 Astrology"
```

```
A premium wine bottle with a cream label. The text on the label must read 
exactly: "Château Margaux 2015" in elegant serif typography.
```

### Multi-Line Text

```
A smartphone screen showing an onboarding screen. Top text reads exactly: 
"Welcome Back" in bold sans-serif. Below, smaller text reads exactly: 
"Continue your cosmic journey" in light weight.
```

### Multilingual Text

```
A traditional Indian wedding invitation card. The headline reads exactly in 
Hindi: "शुभ विवाह" and below in English: "Wedding Invitation". Both must be 
legible and correctly spelled.
```

### Text Positioning

```
Text centered at top of frame: "EXPLORER'S GUIDE"
Text bottom-left corner: "Volume III"
Text on product packaging, front-facing: "ORGANIC MATCHA"
```

---

## Multi-Image Composition (Edit Mode)

Seedream can fuse up to **10 reference images** into a single output.

### Use Cases

- **Style transfer:** "Apply the artistic style from Image 1 to the subject in Image 2"
- **Product placement:** "Place the product from Image 1 into the lifestyle scene from Image 2"
- **Character consistency:** "The character from Image 1 in the environment from Image 2 wearing the outfit from Image 3"
- **Background replacement:** "Keep the person from Image 1, replace the background with the scene from Image 2"

### Prompt Patterns for Edit Mode

```
Replace the background of the person in Image 1 with the tropical beach 
scene from Image 2. Maintain the person's pose, lighting, and clothing 
exactly. Match the lighting direction to the new background.
```

```
Apply the painting style from Image 1 (oil painting, visible brushstrokes, 
warm palette) to the photograph in Image 2. Preserve the subject's identity 
and pose.
```

```
The product from Image 1 placed on the kitchen counter from Image 2. 
Maintain the product's proportions, colors, and label text exactly. 
Match the lighting to the kitchen scene.
```

---

## Lighting & Style Keywords

### Lighting

```
Golden hour warm light — soft, directional, warm tones
Rembrandt lighting — 45° key light, dramatic shadows
Butterfly lighting — overhead key, glamour portrait
Practical lighting — visible light sources in frame (lamps, candles, neon)
Volumetric light — visible light rays through atmosphere
Rim lighting — backlight creating edge glow
Softbox lighting — even, diffused, studio quality
```

### Style / Medium

```
Photorealistic editorial — magazine-quality, sharp detail
Cinematic — anamorphic lens feel, film grain, color graded
Oil painting — visible brushstrokes, rich impasto
Watercolor — transparent washes, soft edges
Digital illustration — clean lines, concept art style
3D render — photoreal CGI, studio lighting
Vintage photograph — faded colors, film grain, 1970s aesthetic
```

### Camera / Technical

```
Shot on Hasselblad X2D — medium format, exceptional detail
Shot on Leica M10 — rangefinder character, smooth tonality
85mm f/1.4 — creamy bokeh, portrait compression
24mm f/2.8 — wide environmental perspective
50mm f/1.2 — natural perspective, shallow DOF
Kodak Portra 400 — warm film grain, organic skin tones
Fujifilm Velvia 50 — saturated colors, high contrast
```

---

## Negative Prompting

Seedream does **not** use negative prompts in the traditional sense. Instead, describe what you want and use exclusion phrases in the main prompt:

```
A clean white background with no textures, no shadows, no gradients, 
no additional objects. Pure #FFFFFF white only.
```

```
A portrait with natural skin texture. No smoothing, no filters, no 
beauty retouching, no plastic skin effect.
```

---

## Common Pitfalls

1. **Too short prompts** — Under 20 words often produce generic results. Aim for 30–100 words.
2. **Conflicting instructions** — "Red car" and "blue car" in the same prompt will confuse the model.
3. **Over-specifying** — More than 150 words can dilute the signal. Prioritize subject, action, lighting.
4. **Impossible physics** — The model will attempt them and produce artifacts. Be realistic about lighting and geometry.
5. **Vague text requests** — "Some text on the label" produces gibberish. Always specify exact strings in quotes.
6. **Too many reference images** — While Seedream supports 10 refs, quality degrades beyond 4–5 meaningful references.

---

## Related

- For OpenMontage pipeline integration, see `skills/creative/seedream-image-usage.md`
- For API integration details (endpoints, auth, rate limits), see the fal.ai docs at https://fal.ai/docs/model-api-reference/image-generation-api/bytedance-seedream-v4.5
