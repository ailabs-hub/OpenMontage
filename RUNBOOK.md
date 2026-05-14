# Marketing Creative Pipeline — Runbook

**For Claude sessions:** Read this file at the start of any marketing creative campaign. It tells you how to run the pipeline and what to do at each step.

---

## What This Is

The marketing-creative pipeline generates ad campaigns for any company configured in `../company_profiles/`. It runs in stages:

1. **Input Processing** (Python) — converts raw text / image / URL / idea-pool ref into a structured idea file
2. **Creative Concept** (Claude subagent) — generates 3-6 creative angles with hooks and visual direction
3. **Copy Variants** (Claude subagent) — writes headlines, body copy, CTAs for each angle
4. **Image Assets** (Claude subagent) — generates image prompts and produces ad images
5. **Review** (Claude subagent) — final QA, A/B test plan, budget summary

**Research is SKIPPED by default.** Only run it if the user explicitly asks for market research. Otherwise the pipeline uses the company profile (pain points, best practices, brand voice) as its source of truth.

---

## Quick Start — Most Common Flow

### Step 1: Run the pipeline with the user's idea

```bash
cd C:\Users\91829\Desktop\Vansun\Marketing_automations\OpenMontage
python -m pipelines.marketing_creative \
  --campaign-id <campaign-slug> \
  --company <company-slug> \
  --input-text "<the user's idea>" \
  --auto
```

**Flags explained:**
- `--campaign-id` — unique ID for this run (e.g., `clarity-vs-confusion`, `competitor-adapt-marathi`)
- `--company` — slug from `../company_profiles/` (e.g., `91astrology`)
- `--input-text` — raw idea text from the user
- `--auto` — auto-approves all human approval gates (use this unless the user wants to review each stage)
- `--research` — OPTIONAL. Adds a research stage before creative_concept. Only use if user asks for it.

**What the script prints:** A JSON action dict. Look for `"action": "spawn_subagent"`. This is your instruction to spawn a subagent.

### Step 2: Spawn the subagent

Read the JSON output from Step 1. It contains:
- `stage` — which stage to run (e.g., `creative_concept`)
- `subagent_type` — which agent type to spawn (e.g., `general-purpose`, `ad-creative-strategist`, `copy-variant-creator`, `content-generation-executor-kimi`)
- `prompt` — the FULL prompt to send to the subagent. This prompt already includes the locked brief, input file paths, output file paths, steering rules, and stage director skill path.

Spawn the subagent with:
```
Agent(
  subagent_type="<from JSON>",
  prompt="<the FULL prompt from the JSON>",
  description="Marketing pipeline: <stage> stage",
)
```

**The subagent will:**
1. Read its stage director skill from the path given in the prompt
2. Read input files from the paths given
3. Do its work
4. Write ALL output files to the paths given
5. Return a JSON summary

### Step 3: Resume the pipeline

After the subagent returns, run:
```bash
python -m pipelines.marketing_creative \
  --campaign-id <same-campaign-id> \
  --resume \
  --auto
```

**What happens:** The script reads the subagent's outputs from disk, marks the stage complete, and emits the next action dict (next subagent spawn request).

### Step 4: Repeat

Keep spawning subagents and running `--resume` until the action dict says `"action": "complete"`.

---

## Input Source Options

You have 4 ways to feed an idea into the pipeline. Pick ONE per run:

### Option A: Raw text (most common)
```bash
python -m pipelines.marketing_creative ... --input-text "A campaign about..."
```
Python structures the idea using company profile defaults. No LLM call.

### Option B: Screenshot of a real ad
```bash
python -m pipelines.marketing_creative ... --input-image "C:\path\to\screenshot.png"
```
Python calls OpenAI vision API to deconstruct the ad and reimagine it for the target company.

### Option C: URL to a landing page
```bash
python -m pipelines.marketing_creative ... --input-url https://example.com/landing
```
Python fetches the page, extracts ad elements, and reimagines.

### Option D: Existing idea from the pool
```bash
python -m pipelines.marketing_creative ... --idea-id idea-test-clarity
```
Python loads the idea from `{company}/ideas/idea-test-clarity.md`.

---

## Campaign Directory Structure

Each run creates:

```
{project_root}/campaigns/{campaign_id}/
├── README.md                    # Locked brief + status
├── .session.json               # Pipeline state (stages completed, budget)
├── artifacts/
│   ├── research_brief.json     # Only if --research
│   ├── creative_specs.json     # After creative_concept
│   ├── copy_manifest.json      # After copy
│   ├── asset_manifest.json     # After assets
│   └── final_review.json       # After review
├── copy_variants/
│   └── {cr_id}_{angle}_{lang}.md
├── assets/
│   ├── {filename}.png
│   ├── {filename}.prompt.json
│   └── {filename}_prompt.md
└── logs/
    └── skill_reading_log.json  # After assets
```

The `../ideas/` directory (sibling to campaign dir) stores structured idea files.

---

## Stage Reference

| Stage | Subagent Type | Input | Output | Approval Gate |
|-------|--------------|-------|--------|---------------|
| research | general-purpose | company profile + idea | `research_brief.json` | Yes |
| creative_concept | ad-creative-strategist | research_brief (if exists) OR company profile + idea | `creative_specs.json` | Yes |
| copy | copy-variant-creator | `creative_specs.json` | `copy_manifest.json` + `.md` files | Yes |
| assets | content-generation-executor-kimi | `copy_manifest.json` + `creative_specs.json` | Images + `asset_manifest.json` | No |
| review | general-purpose | All artifacts | `final_review.json` | Yes |

**Approval gates:** If you use `--auto`, all gates are pre-approved. If not, the action dict will say `"action": "await_human_approval"` — you must confirm before the subagent spawns.

---

## Resume Patterns

### Resume after subagent returns without a result file
```bash
python -m pipelines.marketing_creative --campaign-id <id> --resume --auto
```
The script detects what the subagent wrote to disk and continues.

### Resume with a subagent result file
If the subagent wrote a JSON result file:
```bash
python -m pipelines.marketing_creative \
  --campaign-id <id> \
  --resume \
  --subagent-result-file /path/to/result.json \
  --auto
```

### Resume from a specific stage (if a stage failed)
There's no `--resume-from` flag. Instead:
1. Delete or fix the broken output files in the campaign directory
2. Edit `.session.json` to remove the failed stage from `completed_stages`
3. Run `--resume --auto`

---

## Common Issues

| Problem | Fix |
|---------|-----|
| "Company profile not found" | Check `../company_profiles/{slug}.json` exists |
| "Idea not found in pool" | Check `../{company}/ideas/{idea_id}.md` exists |
| Subagent says input file missing | The previous stage didn't write its output. Run `--resume` to retry, or check the artifact file exists |
| Budget exceeded | The session tracks spend in `.session.json`. Increase cap or skip expensive stages |
| First stage is research but user didn't ask for it | You forgot `--research`. Without it, research is skipped and the pipeline starts at `creative_concept` |

---

## Example: Full Walkthrough

**User says:** "Run a campaign about clarity vs confusion for 91astrology."

**You do:**
```bash
python -m pipelines.marketing_creative \
  --campaign-id clarity-vs-confusion \
  --company 91astrology \
  --input-text "A campaign about clarity vs confusion for the Nadi Report" \
  --auto
```

**Script prints:** `{"action": "spawn_subagent", "stage": "creative_concept", ...}`

**You do:** Spawn the subagent with the full prompt from the JSON.

**Subagent returns.**

**You do:**
```bash
python -m pipelines.marketing_creative \
  --campaign-id clarity-vs-confusion \
  --resume \
  --auto
```

**Script prints:** `{"action": "spawn_subagent", "stage": "copy", ...}`

**You do:** Spawn the copy subagent.

**Subagent returns.**

**You do:** `--resume --auto` again.

**Script prints:** `{"action": "spawn_subagent", "stage": "assets", ...}`

**You do:** Spawn the assets subagent.

**Subagent returns.**

**You do:** `--resume --auto` again.

**Script prints:** `{"action": "spawn_subagent", "stage": "review", ...}`

**You do:** Spawn the review subagent.

**Subagent returns.**

**You do:** `--resume --auto` again.

**Script prints:** `{"action": "complete", ...}` — done.

---

## Company Profiles

Profiles live outside this repo at:
```
C:\Users\91829\Desktop\Vansun\Marketing_automations\company_profiles\{slug}.json
```

Each profile contains: company name, product name, brand voice, primary audience (age, location, languages, pain points), pricing, key differentiators, visual style (mood, colors, lighting), platform focus, copy guidelines, and pipeline learnings.

To add a new company: create a JSON file following the same schema as `91astrology.json`.

---

*Last updated: 2026-05-12*
