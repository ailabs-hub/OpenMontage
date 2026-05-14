# Asset Director — Marketing Creative Pipeline

## When to Use

You are the Asset Producer for a marketing creative campaign. You have:
- A `creative_spec` with visual direction, mood, format, and hook
- A set of `copy_variants` organized by angle (pain_point, direct_benefit, emotional, comparison, offer_led) and language (english, hinglish, hindi)
- A selected copy variant (one angle + one language) to convert into a static image or video asset

Your job is to generate the visual asset. Every file must exist on disk before you finish.

This is where copy becomes visual. A bad prompt here produces generic infographic ads. A good prompt produces cinematic, emotionally compelling creative that converts.

## Prerequisites

| Layer | Resource | Purpose |
|-------|----------|---------|
| Meta skill | `skills/meta/image-prompt-from-copy-variant.md` | **MANDATORY** — Visual Brief pattern + Camera/Technical layer. |
| Stage skill | `skills/pipelines/marketing-creative/asset-director.md` | **MANDATORY** — This file. Stage process + checklists. |
| T2I skill | `.agents/skills/flux-best-practices/rules/t2i-prompting.md` | **MANDATORY** — Camera/lens/film stock reference. |
| Typography skill | `.agents/skills/flux-best-practices/rules/typography-text.md` | **MANDATORY** — Text rendering optimization. |
| Model selection | `.agents/skills/flux-best-practices/rules/model-selection-guide.md` | **MANDATORY** — Provider selection (GPT Image 2 vs Gemini vs FLUX). |
| Prior artifacts | `state.artifacts["copy"]["copy_manifest"]` (selected variant), `state.artifacts["creative_concept"]["creative_specs"]` | What to produce |
| Tools | **Python-based OpenMontage tools** — `image_selector`, `flux_image`, etc. Run via Python scripts, not agent built-in tools | Generation capabilities |
| Cost tracker | `tools/cost_tracker.py` | Budget governance |

## MANDATORY: Skill Reading Protocol

Before generating ANY prompt, you MUST read all 5 skills in order and produce a `skill_reading_log.json`. This log is a MANDATORY output. If it is missing, the pipeline halts at Gate 3.

### Step 0: Read All 5 Skills (in order)

1. `skills/meta/image-prompt-from-copy-variant.md` — Visual Brief pattern + Camera/Technical layer
2. `skills/pipelines/marketing-creative/asset-director.md` — Stage process + pre/post generation checklists
3. `.agents/skills/flux-best-practices/rules/t2i-prompting.md` — Provider-specific prompting (camera, lens, film)
4. `.agents/skills/flux-best-practices/rules/typography-text.md` — Text rendering optimization
5. `.agents/skills/flux-best-practices/rules/model-selection-guide.md` — Model selection (GPT Image 2 vs Gemini vs FLUX)

### Step 0.5: Write Skill Reading Log

After reading each skill, append to `logs/skill_reading_log.json`:

```json
{
  "stage": "assets",
  "step": "skill_reading",
  "skills_read": [
    {
      "skill": "image-prompt-from-copy-variant.md",
      "timestamp": "2026-05-11T10:00:00Z",
      "key_takeaways": ["Visual Brief formula includes Camera/Technical now", "Hex codes for color palette"]
    },
    {
      "skill": "asset-director.md",
      "timestamp": "2026-05-11T10:01:00Z",
      "key_takeaways": ["Pre-generation checklist is gate-blocking", "Must write skill_reading_log"]
    },
    {
      "skill": "flux-best-practices/t2i-prompting.md",
      "timestamp": "2026-05-11T10:02:00Z",
      "key_takeaways": ["35mm f/2.8 is the default advertising lens", "Kodak Portra 400 for warm skin tones"]
    },
    {
      "skill": "flux-best-practices/typography-text.md",
      "timestamp": "2026-05-11T10:03:00Z",
      "key_takeaways": ["Short phrases render better", "Specify script name for Indic languages"]
    },
    {
      "skill": "flux-best-practices/model-selection-guide.md",
      "timestamp": "2026-05-11T10:04:00Z",
      "key_takeaways": ["GPT Image 2 for Devanagari + photorealistic ads"]
    }
  ],
  "visual_brief_formula_used": true,
  "camera_technical_layer_added": true,
  "provider_selected": "gpt-image-2",
  "provider_rationale": "Best text rendering for Devanagari script + photorealistic advertising aesthetic"
}
```

**If any skill is unread or the log is missing:** STOP. Do not proceed. The gate will fail.

## CRITICAL: Read the Meta Skill First

Before doing ANYTHING in this stage, read **`skills/meta/image-prompt-from-copy-variant.md`**. It contains the Visual Brief pattern that prevents the two most common pipeline failures:

1. **Over-specification killing creativity** — dumping UI specs into image prompts
2. **Language propagation bugs** — copy variant language not matching image text overlays
3. **Missing Camera/Technical layer** — producing flat, generic images instead of cinematic ads

If you skip this meta skill, you WILL produce flat infographic ads with wrong-language text and no camera layer. This is not optional.

## Process

### Step 0: Intelligent Variant Selection

You do NOT generate images for every copy variant. The pipeline uses an intelligent selection system that scores all variants and picks the top N (where N = `num_images` from session config).

**How selection works:**
1. All copy variants are scored using company profile learnings
2. Best-performing angles (from `pipeline_learnings.best_performing_angles`) get highest priority
3. Primary language variants get a bonus
4. Creative hook strength (from creative spec) adds points
5. Angle diversity is enforced — max 50% of budget to one angle

**To get the selected variants, run:**
```python
python -c "
from pipelines.marketing_creative.agent_utils import select_variants_for_generation
import json
selected = select_variants_for_generation('CAMPAIGN_ID', 'COMPANY')
print(json.dumps(selected, indent=2))
"
```

This returns a ranked list. Generate images ONLY for these selected variants.

### Step 1: Load Selected Copy Variants

For EACH selected variant:
- **Creative:** e.g., CR-01 Trust Contrast
- **Angle:** e.g., comparison
- **Language:** e.g., hinglish
- **Headline:** The exact headline text (use this in the image)

Load the copy variant data from the copy manifest.

### Step 1.5: Read Generation Config

The session specifies:
- **num_images**: TOTAL image budget across ALL creatives (default: 3)
- **model**: Which provider to use (`flux_image`, `image_selector` auto-routing, or `auto`)

If model is `auto`, use `image_selector` to pick the best provider.
If model is specified, use that provider directly.

### Step 2: Read the Creative Spec for MOOD Only

Load the creative spec. Extract ONLY the emotional and atmospheric direction:
- Mood words (dark/anxious vs warm/calm)
- Story contrast (chaos vs order, betrayal vs relief)
- Lighting direction
- Color palette

**IGNORE** UI specifications like:
- "three green checkmarks"
- "clean sans-serif font"
- "soft gradient transition"
- Specific layout instructions

These are for human designers, not image generation models.

### Step 3: Lock the Language

| Copy Variant Language | Image Text Overlays Must Be |
|---|---|
| english | English |
| [primary_language] | **[primary_language]** (from company_context) |
| [other languages] | [Matching language] |

**This is a hard rule.** If the copy variant language and image text overlay language do not match, it is a pipeline bug. Stop and fix it.

### Step 4: Craft the Visual Brief Prompt (with Camera/Technical Layer)

Follow the Visual Brief formula from the meta skill:

```
[Emotional contrast] +
[Visual anchor 1] + [Visual anchor 2] +
[Text overlays: use the HEADLINE from the selected copy variant — exact text, locked language] +
[Mood words] +
[Lighting] +
[Camera/Technical: shot type, lens, aperture, film stock, depth of field]
```

**Text Overlay Rule:** The image MUST include the copy variant's headline text. Not generic text in the same language — the EXACT headline from the copy variant file. The copy variant contains a single best headline (not multiple options). Use short, punchy phrases (telegram-style) — image models garble long sentences.

**What to INCLUDE:**
- Mood and atmosphere
- Story contrast
- 1-2 defining visual elements per side (not a full UI spec)
- Text overlays using the EXACT HEADLINE from the selected copy variant, in the LOCKED LANGUAGE (short phrases, telegram-style)
- Color palette direction with **hex codes or precise named colors**
- Lighting style using **named lighting patterns** (golden hour, Rembrandt, rim, volumetric)
- **Camera/Technical layer** (MANDATORY):
  - Shot type: close-up, medium shot, wide shot, establishing shot
  - Framing: rule-of-thirds, centered, leading-lines
  - Angle: eye-level, low-angle, high-angle
  - Lens: e.g., 35mm, 50mm, 85mm
  - Aperture: e.g., f/1.4, f/2.8
  - Depth of field: shallow, deep
  - Film stock emulation: e.g., Kodak Portra 400

**What to EXCLUDE:**
- Checkmarks, checkboxes, tick lists
- Specific font names
- Gradient specifications
- Full UI layouts
- Every element from the creative spec

**Prompt structure tags (for verification):**
When crafting the prompt, mentally verify that these sections are present:
```
[SHOT_TYPE: ...] +
[FRAMING: ...] +
[ANGLE: ...] +
[EMOTIONAL_CONTRAST: ...] +
[VISUAL_ANCHOR_1: ...] + [VISUAL_ANCHOR_2: ...] +
[TEXT_OVERLAY: ...] +
[COLOR_PALETTE: ...] +
[LIGHTING: ...] +
[CAMERA_TECHNICAL: ...] +
[STYLE: ...]
```

### Step 5: Pre-Generation Verification Checklist (Gate-Blocking)

**This checklist is gate-blocking. If ANY check fails, the gate fails and the pipeline HALTS.**

Before calling any image generation tool, verify:

- [ ] The prompt describes MOOD, not UI elements
- [ ] The prompt has at most 2 visual anchors per side
- [ ] Image text overlays use the EXACT headline text from the selected copy variant
- [ ] Image text overlays are in the correct language
- [ ] No checklist/checkmark UI elements are specified
- [ ] No specific fonts are requested
- [ ] Emotional contrast is explicit in the prompt
- [ ] **Camera/Technical layer is present** (shot type, lens, aperture, film stock)
- [ ] **Lighting pattern is named** (golden hour, Rembrandt, rim, volumetric)
- [ ] **Color palette includes hex codes or precise named colors**
- [ ] **All 5 mandatory skills were read** (evidenced by skill_reading_log.json)
- [ ] **skill_reading_log.json exists** in `logs/` with all 5 skills listed

**If any check fails:**
1. DO NOT call the image generation tool
2. Rewrite the prompt to fix the failing check
3. Re-run the checklist
4. Only proceed when ALL checks pass

**This is not optional. A failing prompt that proceeds anyway will be caught by Gate 3 and the pipeline will halt.**

### Step 6: Generate the Image via Python Tools

**IMPORTANT:** You do NOT use Claude Code built-in tools (`openai_image`, `google_imagen`, etc.). You run **Python scripts** that invoke OpenMontage tools.

1. **Run preflight** to discover available providers:
   ```bash
   cd [OpenMontage root]
   python -c "from tools.tool_registry import registry; registry.discover(); import json; print(json.dumps(registry.provider_menu_summary(), indent=2))"
   ```

2. **Generate using `image_selector`** (auto-routes to best provider):
   ```python
   from tools.tool_registry import registry
   registry.discover()

   selector = registry.get("image_selector")
   result = selector.execute({
       "prompt": "[your optimized Visual Brief prompt]",
       "width": 1024,      # 1024 for 1:1, 1280 for 4:5, 1024 for 9:16 (height=1792)
       "height": 1024,
       "output_path": "assets/cr01_pain_point_english.png",
       "preferred_provider": "auto",  # or "flux", "openai", etc.
   })
   print(f"Success: {result.success}")
   print(f"Output: {result.data.get('output')}")
   print(f"Cost: ${result.cost_usd}")
   ```

3. **Or use a concrete provider directly** (e.g., FLUX):
   ```python
   from tools.tool_registry import registry
   registry.discover()

   flux = registry.get("flux_image")
   result = flux.execute({
       "prompt": "[your optimized prompt]",
       "width": 1024,
       "height": 1024,
       "output_path": "assets/cr01_pain_point_english.png",
       "model": "flux-pro/v1.1",
   })
   print(result)
   ```

4. **Parameters:**
   - Size: match the creative spec format (1:1 = 1024x1024, 9:16 = 1024x1792, 4:5 = 1024x1280)
   - Quality: `high` for production assets
   - Format: `png`
   - API keys are loaded automatically from `.env`

5. **Log the generation:**
   - Save prompt to `<asset_name>_prompt.md`
   - Save generation metadata to `<asset_name>.prompt.json` (tool, model, parameters, timestamp)

### Step 7: Post-Generation Verification

**Language and text content check:**
- [ ] Image text overlays use the EXACT headline text from the selected copy variant
- [ ] Image text overlays are in the correct language
- [ ] Copy variant language → matching image text language
- [ ] All configured languages properly reflected in image text

**Quality check:**
- [ ] Image matches the emotional direction (not flat/infographic)
- [ ] No garbled or misspelled text
- [ ] Visual contrast is clear and compelling
- [ ] File exists on disk and is readable

**OpenMontage optimization check:**
- [ ] Prompt contains Camera/Technical layer (search for "mm lens" or "f/" or "film stock")
- [ ] Prompt contains shot type (search for "close-up", "medium shot", "wide shot", "establishing shot")
- [ ] Prompt contains named lighting pattern (search for "golden hour", "Rembrandt", "rim", "volumetric")
- [ ] Prompt contains color palette with hex codes or precise named colors
- [ ] skill_reading_log.json exists in `logs/` with all 5 skills listed

**If language is wrong:** Flag as pipeline bug. The language propagation rule was violated. Log it and regenerate with corrected prompt.

**If image is flat/infographic:** The prompt was over-specified. Rewrite using the Visual Brief pattern and regenerate.

**If Camera/Technical layer is missing:** This is a gate failure. The prompt must be rewritten to include shot type, lens, aperture, and film stock. Do not proceed to the next stage until fixed.

### Step 8: Version and Deprecate

When regenerating an existing asset:
1. Label old asset as deprecated in filename or folder
2. Label new asset as current/active
3. Keep both prompt logs for comparison
4. Update the creative spec to reference the new active asset

Example:
- `cr01_comparison_hinglish.png` (v1, deprecated)
- `cr01_comparison_hinglish_v2.png` (v2, active)
- `cr01_comparison_hinglish_v2_prompt.md` (v2 prompt)

### Step 9: Build Asset Manifest

```json
{
  "version": "1.0",
  "assets": [
    {
      "id": "cr01-comparison-hinglish-v2",
      "type": "image",
      "path": "assets/cr01_comparison_hinglish_v2.png",
      "source_tool": "image_selector",
      "source_model": "flux-pro/v1.1",
      "creative_id": "CR-01",
      "angle": "comparison",
      "language": "hinglish",
      "prompt_path": "assets/cr01_comparison_hinglish_v2_prompt.md",
      "prompt_tokens": 186,
      "cost_usd": 0.167,
      "status": "active",
      "deprecated_version": "assets/cr01_comparison_hinglish.png",
      "skill_reading_log_ref": "logs/skill_reading_log.json",
      "prompt_structure_tags": {
        "shot_type": true,
        "framing": true,
        "angle": true,
        "emotional_contrast": true,
        "visual_anchor_1": true,
        "visual_anchor_2": true,
        "text_overlay": true,
        "color_palette": true,
        "lighting": true,
        "camera_technical": true,
        "style": true
      }
    }
  ],
  "total_cost_usd": 0.167,
  "generation_summary": {
    "images_generated": 1,
    "language_propagation_checks_passed": 1,
    "visual_brief_checks_passed": 1,
    "camera_technical_checks_passed": 1,
    "skill_reading_log_exists": true
  }
}
```

### Step 10: Self-Evaluate

Score (1-5):

| Criterion | Question |
|-----------|----------|
| **Language accuracy** | Does image text match the copy variant language? |
| **Creative quality** | Is the image cinematic/emotional, not flat/infographic? |
| **Prompt efficiency** | Is the prompt mood-driven and efficiently written? |
| **Spec alignment** | Does the image match the creative spec's emotional direction? |
| **Budget adherence** | Is cost within the approved budget? |

If any dimension scores below 3, fix before proceeding.

## Common Pitfalls

- **Skipping the meta skill:** The `image-prompt-from-copy-variant` skill is mandatory. Without it, you will over-specify prompts and produce flat ads.
- **Wrong text in image:** This is the #1 pipeline bug. The image MUST show the EXACT headline from the copy variant, not generic text in the same language. Always verify.
- **Wrong language in image text:** Copy variant language must match image text language exactly. Always verify.
- **Using wrong language for code-switched variants:** If the copy is in a code-switched language (e.g., Hinglish), the image text must also be in that same code-switched language. Do not fall back to pure English.
- **Long text in images:** Image models garble long sentences. Use short, punchy phrases from the headline.
- **Not versioning assets:** Always label v1, v2, etc. and deprecate old versions clearly.
- **Generating without sample approval:** Always generate one sample first, verify it, then batch-generate remaining variants.

## When You Do Not Know How

If you encounter uncertainty about image generation techniques, provider behavior, or prompting patterns:

1. **Read `.agents/skills/flux-best-practices/`** for provider-specific image generation guidance
2. **Read `.agents/skills/bfl-api/`** for Black Forest Labs (FLUX) specific patterns
3. **Search the web** for current best practices — image models evolve rapidly
4. **Log it** in the decision log: `category: "capability_extension"`, `subject: "learned technique: <name>"`

Do not rely on stale knowledge. When in doubt, search first.
