# Run Marketing Campaign — Single-File Guide

**Purpose:** This is the ONLY file you need to read to run a marketing creative campaign. It contains the complete automated execution loop with exact commands. Do not read any other guide files.

**Scope:** Static marketing creative production (ad images, copy variants) for companies configured in `../company_profiles/`.

---

## Prerequisites

### 1. Permissions are pre-configured
The `.claude/settings.local.json` file contains auto-approval patterns for all pipeline actions. You should NOT see permission prompts.

### 2. Context is scoped
The `.claudeignore` file hides video-specific directories from Claude's context. Only marketing-creative relevant files are visible.

### 3. Working Directory

All commands assume you're in:
```
C:\Users\91829\Desktop\Vansun\Marketing_automations\OpenMontage
```

---

## What This Pipeline Does

Converts a raw idea (text, image, or URL) into a complete ad campaign:

1. **idea_refinement** — Structures raw input into an idea file
2. **creative_concept** — Generates 3-6 creative angles with hooks
3. **copy** — Writes headlines, body copy, CTAs per angle (2-3 angles × N languages)
4. **assets** — Generates ad images using image generation tools (configurable count + model)
5. **review** — QA check, A/B test plan, budget summary

Research is SKIPPED by default. Only add `--research` if the user explicitly asks for market research.

### Optional Generation Flags

| Flag | Default | Description |
|---|---|---|
| `--num-images` | 1 | Image variants per creative |
| `--model` | `auto` | Image model: `openai_image`, `google_imagen`, `gemini_image`, `seedream_image`, `auto` |
| `--auto` | — | Auto-approve all gates, skip checkpoint writes (non-interactive) |

---

## Execution Loop (Follow Exactly)

### Step 1: Parse User Input

Determine from the user's message:
- **Company**: Extract company name. Default is `91astrology`. Look in `../company_profiles/*.json` to verify.
- **Input source**:
  - Raw text → `--input-text "..."`
  - Image path → `--input-image "C:\path\to\image.png"`
  - URL → `--input-url https://...`
  - Existing idea → `--idea-id idea-01`
- **Research?** Only add `--research` if user explicitly asks for it.

**Campaign ID rule:** Kebab-case from the idea. Examples:
- "clarity vs confusion" → `clarity-vs-confusion`
- "Instagram post adapt" → `instagram-post-adapt`
- "competitor ad analysis" → `competitor-ad-analysis`

### Step 2: Run the Python CLI

Execute this command with the appropriate input flag:

```bash
cd C:\Users\91829\Desktop\Vansun\Marketing_automations\OpenMontage
python -m pipelines.marketing_creative ^
  --campaign-id <kebab-case-id> ^
  --company <company-slug> ^
  --input-text "<user's idea>" ^
  --auto
```

Replace `--input-text` with the appropriate flag:
- `--input-text "A campaign about..."`
- `--input-image "C:\path\to\screenshot.png"`
- `--input-url https://example.com/landing`
- `--idea-id idea-01` (skip `--input-text` when using this)

### Step 3: Parse the JSON Output

The script prints a JSON action dict. Parse it.

**If `action: "spawn_subagent"`:**
- Extract `subagent_type`, `prompt`, `description`
- Spawn the subagent using the Agent tool exactly as shown below

**If `action: "complete"`:**
- Pipeline is done. Go to Step 7 (Present Deliverables).

**If `action: "error"`:**
- Stop. Report the error to the user.

### Step 4: Spawn the Subagent

Use the Agent tool with the exact values from the JSON:

```
Agent({
  subagent_type: "<from JSON subagent_type>",
  prompt: "<FULL prompt from JSON prompt field>",
  description: "<from JSON description>"
})
```

**CRITICAL:** Pass the FULL prompt from the JSON. Do not shorten or summarize it.

### Step 5: Auto-Resume

When the subagent finishes, **immediately** run the resume command. Do NOT ask the user if they want to continue.

```bash
cd C:\Users\91829\Desktop\Vansun\Marketing_automations\OpenMontage
python -m pipelines.marketing_creative ^
  --campaign-id <same-campaign-id> ^
  --company <same-company> ^
  --resume ^
  --auto
```

### Step 6: Loop

Repeat Steps 3-5 until the action dict says `"action": "complete"`.

**Expected stage sequences:**

| Input Type | Stage Order |
|---|---|
| Raw text/image/URL, no research | idea_refinement → creative_concept → copy → assets → review |
| Raw text/image/URL, with `--research` | idea_refinement → research → creative_concept → copy → assets → review |
| `--idea-id` from pool, no research | creative_concept → copy → assets → review |
| `--idea-id` from pool, with `--research` | research → creative_concept → copy → assets → review |

### Step 7: Present Deliverables

When `"action": "complete"` is received, read the campaign directory and present:

```
../{company}/campaigns/{campaign_id}/
```

Present:
- Campaign ID and directory path
- What stages ran
- Final artifacts:
  - `artifacts/creative_specs.json` — creative angles and hooks
  - `artifacts/copy_manifest.json` — copy variants
  - `copy_variants/*.md` — individual copy files per angle
  - `assets/*.png` — generated images
  - `artifacts/final_review.json` — A/B test plan and QA
- Budget summary from `.session.json`

---

## Error Handling

| Scenario | Action |
|---|---|
| Subagent fails | Retry the same subagent once. If it fails again, stop and report. |
| `--resume` returns error | Check if the previous stage's output files exist. If missing, the subagent didn't write them. Report to user. |
| Budget exceeded | Stop. Read `.session.json` for spent vs cap and report. |
| `--auto` hits approval gate | Run with `--approve` flag before `--resume`. |

---

## Example: Text Input

**User:** "Run a campaign about clarity vs confusion for 91astrology."

**You do:**
1. Run initial command (add `--num-images` and `--model` if user specifies):
   ```bash
   python -m pipelines.marketing_creative ^
     --campaign-id clarity-vs-confusion ^
     --company 91astrology ^
     --input-text "A campaign about clarity vs confusion for the Nadi Report" ^
     --auto ^
     --num-images 1 ^
     --model auto
   ```
2. Parse JSON → `{"action": "spawn_subagent", "stage": "idea_refinement", ...}`
3. Spawn idea_refinement subagent
4. Subagent returns
5. Run resume:
   ```bash
   python -m pipelines.marketing_creative ^
     --campaign-id clarity-vs-confusion ^
     --company 91astrology ^
     --resume ^
     --auto
   ```
6. Parse JSON → `{"action": "spawn_subagent", "stage": "creative_concept", ...}`
7. Spawn creative_concept subagent
8. Subagent returns
9. Run resume (same command as step 5)
10. Parse JSON → `{"action": "spawn_subagent", "stage": "copy", ...}`
11. Spawn copy subagent
12. Subagent returns
13. Run resume
14. Parse JSON → `{"action": "spawn_subagent", "stage": "assets", ...}`
15. Spawn assets subagent
16. Subagent returns
17. Run resume
18. Parse JSON → `{"action": "spawn_subagent", "stage": "review", ...}`
19. Spawn review subagent
20. Subagent returns
21. Run resume
22. Parse JSON → `{"action": "complete", ...}`
23. Read deliverables and present to user

## Example: Image Input

**User:** "Adapt this Instagram post for 91astrology." (with image)

**You do:**
1. Run initial command:
   ```bash
   python -m pipelines.marketing_creative ^
     --campaign-id instagram-post-adapt ^
     --company 91astrology ^
     --input-image "C:\Users\91829\Downloads\Instagram post - 2449.png" ^
     --auto
   ```
2. Parse JSON → `{"action": "spawn_subagent", "stage": "idea_refinement", ...}`
3. Spawn idea_refinement subagent (it will analyze the image with vision)
4. Subagent returns
5. Run resume (same pattern as text example)
6. Continue through creative_concept → copy → assets → review → complete

## Example: Idea Pool Reference

**User:** "Run idea-01 through the pipeline for 91astrology."

**You do:**
1. Run initial command:
   ```bash
   python -m pipelines.marketing_creative ^
     --campaign-id idea-01-run ^
     --company 91astrology ^
     --idea-id idea-01 ^
     --auto
   ```
2. Parse JSON → `{"action": "spawn_subagent", "stage": "creative_concept", ...}`
   (Note: idea_refinement is SKIPPED because the idea already exists in the pool)
3. Continue through remaining stages

---

## Critical Rules

1. **Do NOT ask the user to confirm between stages.** The loop is automated.
2. **Do NOT fall back to video pipelines.** This is a static marketing creative pipeline.
3. **Do NOT modify the action-dict pattern.** Execute what the Python script emits exactly.
4. **Always use `--auto`** on both initial run and resume commands.
5. **Always pass the FULL subagent prompt** from the JSON. Never summarize or shorten.

---

## Key Paths

| Path | Purpose |
|---|---|
| `../company_profiles/{slug}.json` | Company configuration (brand voice, audience, pricing) |
| `../{company}/ideas/` | Idea pool directory — structured idea files |
| `../{company}/campaigns/{id}/` | Campaign output directory — all artifacts |
| `../{company}/campaigns/{id}/.session.json` | Pipeline state and budget tracking |
| `../{company}/campaigns/{id}/artifacts/` | JSON artifacts from each stage |
| `../{company}/campaigns/{id}/copy_variants/` | Individual .md copy files |
| `../{company}/campaigns/{id}/assets/` | Generated images and prompts |
