# Seedream Image Usage for OpenMontage

> How to use ByteDance Seedream 4.5 within OpenMontage pipelines.
> Supplements `skills/creative/image-gen-usage.md` (general image generation workflow)
> and `skills/creative/image-provider-usage.md` (provider selection).
>
> Layer 3 skill: `.agents/skills/seedream-4-5/SKILL.md` — read before authoring prompts.

## When to Choose Seedream 4.5

Seedream 4.5 is the **text-accuracy champion** in the OpenMontage image stack. Pick it when:

| Scenario | Why Seedream |
|---|---|
| Image contains readable text (labels, CTAs, headlines) | Best-in-class typography rendering across 725+ languages |
| Multi-reference composition | Fuse up to 10 refs — style, subject, environment, product |
| Precise image editing | Unified architecture: same model for generation + editing |
| Brand assets requiring exact colors/labels | Hex colors + exact text strings honored reliably |
| Multilingual brand content | Devanagari, CJK, Arabic render correctly alongside English |
| 4K hero assets | Native up to 4096×4096 with detail integrity |

## When NOT to Choose Seedream 4.5

| Scenario | Better Alternative | Reason |
|---|---|---|
| Budget bulk generation (100+ images) | `pexels_image` / `pixabay_image` | Stock is free; Seedream is $0.04/image flat |
| Photoreal human skin at lowest cost | `gemini_image` (Nano Banana Pro) | NBP at 2K is ~$0.018 vs Seedream's $0.04 |
| General photoreal without text | `flux_image` (FLUX.2) | FLUX pro is ~$0.03–$0.05 with broader ecosystem |
| Offline / air-gapped | `local_diffusion` | Seedream requires fal.ai API |

## Provider Comparison (Image Generation Stack)

| Tool | Provider | Cost | Text Accuracy | Photoreal Skin | Multi-Ref | Edit | Max Res |
|---|---|---|---|---|---|---|---|
| `seedream_image` | ByteDance | $0.04 flat | **Excellent** | Good | **Up to 10** | **Yes** | 4K |
| `flux_image` | BFL / fal.ai | $0.03–$0.05 | Poor | Excellent | Up to 4–8 | Limited | 4MP |
| `openai_image` | OpenAI | $0.011–$0.167 | Good | Slight CG-glow | No | No | 1024–1536 |
| `gemini_image` | Google | ~$0.018–$0.045 | Good | Good (Imagen-like) | No | No | 2K–4K |
| `recraft_image` | Recraft | $0.04–$0.25 | Good (SVG) | N/A | No | No | Varies |

## Resolution Strategy

Seedream's flat pricing means **resolution is free** — always generate at the highest resolution you need.

| Deliverable | Preset | Notes |
|---|---|---|
| Social post (square) | `square_hd` | ~1024×1024, crop as needed |
| Video frame 16:9 | `landscape_16_9` | ~1024×576, suitable for B-roll |
| Hero banner / website | `auto_2K` | Up to 2048px wide, crisp at retina |
| Print / 4K display | `auto_4K` | Up to 4096px, maximum detail integrity |

**Custom dimensions:** Pass `width` + `height` when the presets don't match your pipeline's exact needs (e.g., `1920×1088` for FLUX-compatible video frames).

## Prompting Workflow

### Step 1: Read the Layer 3 Skill

Before writing any prompt, read `.agents/skills/seedream-4-5/SKILL.md`. It contains:
- Exact-string text rendering patterns
- Multi-image composition syntax
- Lighting and camera keyword reference
- Common pitfalls specific to Seedream

### Step 2: Build the 3-Part Prompt

Adapt the standard OpenMontage 3-part approach for Seedream:

```
[ADAPTED STYLE ANCHOR from playbook — 5-10 words]
[SEEDREAM-SPECIFIC: exact text strings in quotes, multi-ref instructions]
[SCENE DESCRIPTION: specific subject, action, environment, lighting]
```

**Seedream-specific additions:**
- If text is required: `"must read exactly 'YOUR TEXT HERE'"`
- If editing: `"Apply the style from Image 1 to the subject in Image 2..."`
- If hex colors matter: `"walls in #0a1230 (midnight navy), accents in #c9a14d (antique gold)"`

### Step 3: Validate Text Requirements

If the image contains text, verify:
- [ ] Exact string is quoted in the prompt
- [ ] Text position is specified (centered, top-left, on label, etc.)
- [ ] Font style is described if it matters (serif, sans-serif, script)
- [ ] Language is specified for non-English text

### Step 4: Use Edit Mode for Iteration

Seedream's edit mode is powerful for refinement without regenerating from scratch:

```python
# Round 1: Generate base image
result = seedream_image.execute({
    "prompt": "A premium cosmetic bottle on marble surface, soft studio lighting...",
    "image_size": "auto_2K",
    "output_path": "assets/images/hero_base.png"
})

# Round 2: Edit — change label text, keep everything else
result = seedream_image.execute({
    "prompt": "Change the label text to read exactly 'LUMIÈRE NUIT' in elegant gold serif. Keep the bottle, lighting, and background exactly the same.",
    "generation_mode": "edit",
    "image_url": "file://assets/images/hero_base.png",  # or hosted URL
    "image_size": "auto_2K",
    "output_path": "assets/images/hero_v2.png"
})
```

## Multi-Reference Composition in OpenMontage

Seedream can accept up to 10 reference images. In a pipeline, this enables:

### Hero Reference Strategy (Enhanced)

```python
# Generate a style reference from the playbook
style_ref = seedream_image.execute({
    "prompt": "Abstract color palette swatch: midnight navy, antique gold, cream, deep saffron. Flat, no texture.",
    "image_size": "square",
    "output_path": "assets/ref/style_palette.png"
})

# Generate the hero using style + subject refs
hero = seedream_image.execute({
    "prompt": (
        "Apply the color palette and mood from Image 1. "
        "The Vedic astrologer from Image 2 sits in the traditional study from Image 3. "
        "Single warm amber light from camera-left. "
        "Midnight navy #0a1230 dominates shadows. "
        "Antique gold #c9a14d accents on brass artifacts."
    ),
    "generation_mode": "edit",
    "image_urls": [
        "file://assets/ref/style_palette.png",
        "file://assets/ref/astrologer_portrait.png",
        "file://assets/ref/study_background.png",
    ],
    "image_size": "auto_2K",
    "output_path": "assets/images/hero_final.png"
})
```

## Cost Planning

Seedream's flat $0.04/image pricing makes budgeting simple:

```
PRODUCTION PATH: Premium with Seedream
├── Hero images (4K): seedream_image × 3  = $0.12
├── Supporting visuals (2K): seedream_image × 5 = $0.20
├── Text-overlay base images: seedream_image × 2 = $0.08
├── Edits/iterations: seedream_image × 4 = $0.16
└── Total: ~$0.56

Compare to FLUX path:
├── Hero images (max): flux_image × 3 = $0.15
├── Supporting (pro): flux_image × 5 = $0.15
└── Total: ~$0.30  (but no text accuracy, no native editing)
```

**Decision rule:** If your pipeline needs **≥2 images with readable text** or **≥1 precise edit cycle**, Seedream's premium is justified by reduced iteration time and post-production work.

## Integration with Image Selector

The `image_selector` auto-discovers `seedream_image` via the registry. No selector code changes needed.

Routing hints for the selector:
- `preferred_provider="bytedance"` — forces Seedream
- `generation_mode="edit"` — routes to Seedream if available (FLUX supports limited editing; Seedream is strongest)

```python
# Force Seedream for text-heavy creative
result = image_selector.execute({
    "prompt": "A mobile app onboarding screen with exact text...",
    "preferred_provider": "bytedance",
    "image_size": "auto_2K",
    "output_path": "assets/images/onboarding.png"
})
```

## Quality Verification Checklist

After generation, verify:
- [ ] Text is spelled correctly and positioned as specified
- [ ] Colors match playbook hex codes (spot-check with eyedropper)
- [ ] No unintended artifacts in negative space (Seedream is generally clean)
- [ ] For edit mode: subject identity preserved, lighting consistent
- [ ] Resolution matches preset (check pixel dimensions)

## Related

- `skills/creative/image-gen-usage.md` — General image generation workflow
- `skills/creative/image-provider-usage.md` — Provider selection across all image tools
- `.agents/skills/seedream-4-5/SKILL.md` — Layer 3 prompting patterns and parameters
