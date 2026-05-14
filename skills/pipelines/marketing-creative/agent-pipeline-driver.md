# Agent Pipeline Driver — Marketing Creative (Deterministic Execution)

**Purpose:** Execute the entire marketing-creative pipeline in a single Claude/Kimi
session without calling the CLI orchestrator loop. The agent drives every stage
directly.

**Execution model:**
- The agent IS the orchestrator.
- Session state is managed via Python utility functions (`agent_utils.py`).
- Stage sequencing is deterministic and defined in this skill.
- Creative work (writing, prompting, reviewing) is done by the agent.
- Image generation is done via OpenMontage Python tools (NOT Claude built-in tools).

---

## Deterministic Stage Sequence

| Input Source | Research=False | Research=True |
|---|---|---|
| Raw (text/image/URL) | idea_refinement → creative_concept → copy → assets → review | research → idea_refinement → creative_concept → copy → assets → review |
| Idea pool | creative_concept → copy → assets → review | research → creative_concept → copy → assets → review |

---

## Pre-Execution: One-Time Setup

### Step 1: Parse User Request

Extract:
- `company`: Company slug (e.g., "91astrology")
- `input_type`: "raw_text", "raw_image", "raw_url", or "idea_pool"
- `input_data`: The actual text, image path, URL, or idea_id
- `campaign_id`: Derive from the idea using kebab-case
- `research`: True ONLY if user explicitly requests market research
- `num_images`: Number of image variants (default: 1)
- `model`: Image model preference (default: "auto")

### Step 2: Initialize Session

Run EXACTLY this command:

```python
python -c "
from pipelines.marketing_creative.agent_utils import init_session
print(init_session('CAMPAIGN_ID', 'COMPANY', 'INPUT_TYPE', research=RESEARCH, num_images=NUM_IMAGES, model='MODEL', input_data='INPUT_DATA'))
"
```

Replace:
- `CAMPAIGN_ID` with the actual campaign ID
- `COMPANY` with the company slug
- `INPUT_TYPE` with `"raw_input"` or `"idea_pool"`
- `RESEARCH` with `True` or `False`
- `NUM_IMAGES` with the TOTAL image budget across ALL creatives (default 3)
- `MODEL` with the model string (default `"auto"`)
- `INPUT_DATA` with the actual raw input: text string, image path, URL, or idea_id. Use empty string `""` for idea_pool.

This returns the campaign directory path and creates `.session.json`.

**IMPORTANT:** `num_images` is the TOTAL number of images to generate across the entire campaign, NOT per creative. The pipeline will intelligently select which copy variants get images.

### Step 3: Load Company Profile

Run EXACTLY this command:

```python
python -c "
from pipelines.marketing_creative.agent_utils import load_company_profile
import json
print(json.dumps(load_company_profile('COMPANY'), indent=2))
"
```

Store the profile. You will reference it across all stages.

### Step 4: Run Preflight (Assets Stage Only)

Before any creative work, run preflight to verify image generation tools:

```python
python -c "
from tools.tool_registry import registry
import json
registry.discover()
print(json.dumps(registry.provider_menu_summary(), indent=2))
"
```

If `image_selector` or `flux_image` is NOT available, STOP and report to the user.

---

## Stage Execution Loop

For each stage in the deterministic sequence:

### Loop Step A: Check Completion Status

Run EXACTLY:

```python
python -c "
from pipelines.marketing_creative.agent_utils import is_stage_complete
print(is_stage_complete('CAMPAIGN_ID', 'COMPANY', 'STAGE_ID'))
"
```

If output is `True`, skip to next stage.

### Loop Step B: Read Stage Skill

Get skill path via:

```python
python -c "
from pipelines.marketing_creative.agent_utils import get_stage_skill_path
print(get_stage_skill_path('STAGE_ID'))
"
```

Read the skill file at that path.

### Loop Step C: Load Stage Inputs

Resolve input paths:

```python
python -c "
from pipelines.marketing_creative.agent_utils import resolve_stage_inputs
import json
print(json.dumps(resolve_stage_inputs('STAGE_ID', 'CAMPAIGN_ID', 'COMPANY'), indent=2))
"
```

Read each input file. If a file does not exist, note it and proceed if the skill allows.

### Loop Step D: Execute Creative Work

Follow the stage director skill EXACTLY. Do not improvise.

Write ALL output files to the campaign directory.

### Loop Step E: Mark Stage Complete

Run EXACTLY:

```python
python -c "
from pipelines.marketing_creative.agent_utils import mark_stage_complete
mark_stage_complete('CAMPAIGN_ID', 'COMPANY', 'STAGE_ID')
"
```

### Loop Step F: Continue

Immediately proceed to the next stage. Do NOT pause, ask for approval, or call any CLI.

---

## Stage-Specific Reference

### idea_refinement

**Skill:** `skills/pipelines/marketing-creative/idea-refinement-director.md`
**Inputs:** None (uses user raw input + company profile)
**Outputs:** Structured idea file written to the company's idea pool directory.

The skill will tell you exactly where to write the idea file. After writing, capture the idea_id and store it for subsequent stages.

### research

**Skill:** `skills/pipelines/marketing-creative/research-director.md`
**Inputs:** Idea brief (from idea pool or locked brief)
**Outputs:** `artifacts/research_brief.json`

### creative_concept

**Skill:** `skills/pipelines/marketing-creative/creative-director.md`
**Inputs:** `idea.md` (from idea pool) or locked brief
**Outputs:** `artifacts/creative_specs.json`

### copy

**Skill:** `skills/pipelines/marketing-creative/copy-director.md`
**Inputs:** `artifacts/creative_specs.json`
**Outputs:** `artifacts/copy_manifest.json` + individual `.md` files in `copy_variants/`

### assets

**Skill:** `skills/pipelines/marketing-creative/asset-director.md`
**Inputs:** `artifacts/copy_manifest.json`, `artifacts/creative_specs.json`
**Outputs:** `artifacts/asset_manifest.json`, generated images in `assets/`, `logs/skill_reading_log.json`

**CRITICAL — Intelligent Variant Selection:**

You do NOT generate images for every copy variant. You generate images for only the BEST variants, up to the `num_images` budget.

**Step A: Run variant selection**

```python
python -c "
from pipelines.marketing_creative.agent_utils import select_variants_for_generation
import json
selected = select_variants_for_generation('CAMPAIGN_ID', 'COMPANY')
print(json.dumps(selected, indent=2))
"
```

This returns the ranked list of variants that should get images. Each entry includes:
- `rank`: 1 = highest priority
- `creative_id`: Which creative concept
- `variant_id`: Which copy variant
- `angle`: pain_point, direct_benefit, emotional, etc.
- `language`: english, hinglish, hindi, etc.
- `headline`: The exact headline to use in the image
- `score`: Selection score
- `selection_reason`: Why this variant was chosen

**Selection logic used (automatic):**
- Best-performing angles from company learnings get highest scores
- Primary language variants get a bonus
- Strong hooks (from creative spec) get a bonus
- Angle diversity is enforced — no more than 50% of budget to one angle

**Step B: Generate images for selected variants ONLY**

For EACH selected variant:
1. Read `skills/meta/image-prompt-from-copy-variant.md`
2. Read the asset-director skill
3. Read `.agents/skills/flux-best-practices/rules/t2i-prompting.md` (if available)
4. Read `.agents/skills/flux-best-practices/rules/typography-text.md` (if available)
5. Read `.agents/skills/flux-best-practices/rules/model-selection-guide.md` (if available)
6. Craft Visual Brief prompt using the selected variant's headline
7. Generate image

After reading EACH skill, append an entry to `logs/skill_reading_log.json`.

**To generate an image, use the standalone helper script (avoids Windows bash issues):**

1. **Write a JSON config file** for each selected variant:

```json
{
  "prompt": "YOUR_OPTIMIZED_PROMPT_WITH_CAMERA_TECHNICAL_LAYER",
  "width": 1024,
  "height": 1024,
  "output_path": "CAMPAIGN_DIR/assets/VARIANT_ID.png",
  "provider": "image_selector",
  "preferred_provider": "auto"
}
```

Replace `CAMPAIGN_DIR` with the actual campaign directory path and `VARIANT_ID` with the selected variant's ID.

2. **Run the generation script:**

```bash
python OpenMontage/tools/generate_image.py CAMPAIGN_DIR/assets/VARIANT_ID_config.json
```

**Alternative — direct OpenAI (GPT Image 2):**

```json
{
  "prompt": "YOUR_OPTIMIZED_PROMPT",
  "width": 1024,
  "height": 1024,
  "output_path": "CAMPAIGN_DIR/assets/VARIANT_ID.png",
  "provider": "openai_image",
  "model": "gpt-image-2"
}
```

Then run:
```bash
python OpenMontage/tools/generate_image.py CAMPAIGN_DIR/assets/VARIANT_ID_config.json
```

**Alternative — direct FLUX provider:**

```json
{
  "prompt": "YOUR_OPTIMIZED_PROMPT",
  "width": 1024,
  "height": 1024,
  "output_path": "CAMPAIGN_DIR/assets/VARIANT_ID.png",
  "provider": "flux_image",
  "model": "flux-pro/v1.1"
}
```

Then run:
```bash
python OpenMontage/tools/generate_image.py CAMPAIGN_DIR/assets/VARIANT_ID_config.json
```

### review

**Skill:** `skills/pipelines/marketing-creative/review-director.md`
**Inputs:** `artifacts/creative_specs.json`, `artifacts/copy_manifest.json`, `artifacts/asset_manifest.json`
**Outputs:** `artifacts/final_review.json`

---

## Post-Execution: Present Deliverables

After all stages are complete:

1. List all files in the campaign directory
2. Summarize:
   - Campaign ID and company
   - Stages completed
   - Artifacts produced (with file paths)
   - A/B test plan from `final_review.json`
   - Budget summary from `.session.json`

---

## Absolute Rules

1. **Do NOT spawn subagents.** Execute every stage yourself.
2. **Do NOT call `python -m pipelines.marketing_creative --resume`.** Use `agent_utils.py` for state management.
3. **Do NOT use Claude Code built-in image tools** (`openai_image`, `google_imagen`, etc.). Use OpenMontage Python tools only.
4. **Do NOT pause between stages for approval.** Execute all stages in one continuous session.
5. **Read the skill file for EVERY stage** before executing it.
6. **Write `.session.json` after each stage** via `mark_stage_complete()`.
7. **If a stage fails, retry once.** If it fails again, stop and report to the user.
8. **Respect the batch limit:** maximum 2 campaigns per agent invocation.
9. **All file paths are absolute.** Do NOT assume relative paths from current directory.
10. **API keys load automatically from `.env`.** Do NOT ask the user for API keys.

---

## Quick Reference: Python One-Liners

**Get stage sequence:**
```python
python -c "from pipelines.marketing_creative.agent_utils import get_stage_sequence; import json; print(json.dumps(get_stage_sequence('raw_input', research=False)))"
```

**Get next pending stage:**
```python
python -c "from pipelines.marketing_creative.agent_utils import get_next_stage; print(get_next_stage('CAMPAIGN_ID', 'COMPANY'))"
```

**Get session status:**
```python
python -c "from pipelines.marketing_creative.agent_utils import get_session_status; import json; print(json.dumps(get_session_status('CAMPAIGN_ID', 'COMPANY'), indent=2))"
```

**Resolve output paths for a stage:**
```python
python -c "from pipelines.marketing_creative.agent_utils import resolve_stage_outputs; import json; print(json.dumps(resolve_stage_outputs('STAGE_ID', 'CAMPAIGN_ID', 'COMPANY'), indent=2))"
```
