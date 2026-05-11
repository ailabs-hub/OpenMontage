---
name: marketing-creative-orchestrator
description: >
  Layer 3 orchestrator agent for the marketing-creative pipeline.
  Invoked in a fresh window to discuss/finalize campaign ideas, then spawns
  specialized subagents for each pipeline stage (research → creative_concept →
  copy → assets → review). Steers outputs using Visual Brief rules, language
  propagation, and v1 vs v2 quality lessons.
metadata:
  author: OpenMontage
  version: "1.0.0"
  tags: marketing, creative, orchestrator, pipeline, campaigns
---

# Marketing Creative Orchestrator

## When to Use

The user has arrived with a marketing campaign idea, topic, or request to "run an idea through the pipeline." This skill is the **entry point** for ALL marketing creative production in OpenMontage.

**Trigger phrases:**
- "Run idea-01 through the pipeline"
- "I want to create a marketing campaign for..."
- "Generate ad creatives for [company]"
- "Let's run the marketing pipeline"
- "Make me some ad images for..."

**What this skill does:**
1. **Idea Discussion** — Talk through the idea pool or raw topic with the user
2. **Finalization** — Lock the idea, platform, audience, and budget
3. **Subagent Spawning** — Spawn a specialized subagent for each pipeline stage
4. **Steering** — Validate subagent outputs against known failure patterns
5. **Recovery** — Rerun subagents if output quality is below bar

## Architecture

```
User invokes orchestrator
    ↓
Phase 1: Idea Discussion (orchestrator = you)
    ↓
Phase 2: Spawn subagents sequentially via Agent tool
    ├── research subagent  → produces research_brief
    ├── creative subagent  → produces creative_specs
    ├── copy subagent      → produces copy_manifest
    ├── assets subagent    → produces asset_manifest + generated images
    └── review subagent    → produces final_review
    ↓
Phase 3: Present deliverables, A/B plan, budget summary
```

**The orchestrator is NOT a background worker.** It is the Claude Code agent (you) reading this skill and executing the pipeline by spawning subagents for each stage. You stay in control. You steer. You approve subagent outputs before the next stage begins.

## Phase 1: Idea Discussion Protocol

### If user provides an idea ID (e.g., "idea-01")

1. Load the idea from the company idea pool directory (read `company_context.paths.idea_pool` from the company profile, resolve relative to the `openMontage/` repo root)
2. Read the README.md and any existing research
3. Present a one-paragraph summary to the user
4. Ask: **"Shall I proceed with this idea, or do you want to adjust the angle/audience/platform?"**
5. **Do NOT proceed until user confirms**

### If user says "pick the best one" or asks for idea pool

1. Scan the company idea pool directory (read `company_context.paths.idea_pool` from the company profile, resolve relative to the `openMontage/` repo root) for available ideas
2. Sort by score (highest first)
3. Present the top 3 ideas with:
   - Idea ID and title
   - Score (if available)
   - One-line hook
   - Platform recommendation
4. Ask user to pick one
5. **Do NOT proceed until user selects**

### If user provides a raw topic (no idea pool entry)

1. Treat this as a new idea
2. Ask clarifying questions (max 3):
   - What platform? (suggest from company_context.platform_focus)
   - What audience segment? (suggest from company_context.primary_audience)
   - Any budget constraints or known competitors?
3. Summarize back: "So we're making [platform] creatives for [audience] about [topic] — correct?"
4. **Do NOT proceed until user confirms**

### Lock the Brief

Once the idea is finalized, produce a `locked_brief` (inline markdown, no file needed):

```
LOCKED BRIEF
------------
Idea: [title]
Topic: [topic]
Platform: [platform]
Language: [single language from config — must be specified by user]
Audience: [description]
Budget Cap: $[amount]
Special Instructions: [any user notes]
```

**Language Configuration:**
The pipeline is language-independent. The user MUST specify the target language before locking the brief. Supported languages:
- English, Hinglish, Hindi, Odia, Bengali, Marathi, Malayalam, Gujarati, Telugu, Kannada, Tamil

Default from company_context: `primary_audience.languages`. If user overrides, use their choice.

**Rule:** All copy, image text overlays, and CTAs MUST be in the locked language. No mixing unless the locked language itself is a mix (e.g., Hinglish).

**This locked brief is the steering document.** Every subagent receives it. If a subagent drifts from it, steer them back.

## Batch Multi-Campaign Protocol (MANDATORY)

If the user provides **more than one campaign** (e.g., "run all 4 ideas through the pipeline"):

### DO NOT process all campaigns in a single agent session.

**Why:** Each campaign requires research → creative_concept → copy → assets → review. Running 4 full pipelines in one invocation exhausts context, causes stages to be silently skipped, and produces fabricated checkpoint/review data (as observed in production failures).

### Correct batch pattern:

```
For each campaign:
  1. Process campaign N through all stages sequentially
  2. Write checkpoint files after every stage
  3. Write a batch_manifest.json at the project root tracking:
     - campaign_id
     - current_stage
     - status (completed / in_progress / failed)
     - last_checkpoint_timestamp
  4. ONLY after campaign N is fully complete, begin campaign N+1
```

### If a campaign fails mid-pipeline:

1. Halt the batch. Do not proceed to the next campaign.
2. Report the blocker to the user with campaign ID and failed stage.
3. On resume, read `batch_manifest.json`, find the first campaign with status != "completed", and resume from its last checkpoint.

### Context budget per campaign:

Each campaign consumes ~25-35K tokens across all stages. **Maximum 2 campaigns per agent invocation.** If the user asks for more than 2, process the first 2, write the batch manifest, and tell the user: "Campaigns 1-2 complete. Invoke me again to process campaigns 3-4."

---

## Gate System: Making Skipping Impossible

Each stage has a **non-bypassable gate** that MUST pass before the next stage begins. Gates are separate from checkpoints. A checkpoint says "the stage ran"; a gate says "the stage's output was validated."

### Gate Flow

```
locked_brief.md exists?
    ↓ YES
Gate 0: locked_brief validated → write gate-00-brief.json
    ↓
creative_specs.json exists?
    ↓ YES
Gate 1: creative concept validated → write gate-01-creative.json
    ↓
copy_manifest.json exists + file count matches?
    ↓ YES
Gate 2: copy validated → write gate-02-copy.json
    ↓
asset_manifest.json exists + skill_reading_log.json exists + prompt has camera/technical?
    ↓ YES
Gate 3: assets validated → write gate-03-assets.json
    ↓
final_review.json exists + file existence check passed?
    ↓ YES
Gate 4: review validated → write gate-04-review.json
    ↓
Pipeline complete
```

### Gate File Format

Use `lib/checkpoint.py:write_gate()` and `lib/checkpoint.py:validate_gate()`:

```python
write_gate(
    project_dir=Path(project_path),
    gate_id="gate-03-assets",
    stage="assets",
    validation={
        "asset_manifest_exists": True,
        "skill_reading_log_exists": True,
        "skills_read_count": 5,
        "prompt_has_camera_technical": True,
        "prompt_has_shot_type": True,
        "prompt_has_lighting_pattern": True,
        "prompt_under_400_tokens": True,
        "files_generated": 2,
    },
    artifact_paths=[Path(project_path) / "artifacts" / "asset_manifest.json", ...],
)
```

**If any validation field is `False`, the gate status is `failed` and the pipeline HALTS.**

### Critical Gate 3: Assets (The Skill Verification Gate)

Gate 3 is the most important gate. It verifies that the Content Generation Executor actually read all 5 mandatory skills and produced an optimized prompt.

**Gate 3 validation fields:**
- `asset_manifest_exists`: True
- `skill_reading_log_exists`: True
- `skills_read_count`: 5
- `skills_read`: List of all 5 skill paths
- `prompt_has_camera_technical`: True (contains "mm lens" or "f/" or "film stock")
- `prompt_has_shot_type`: True (contains "close-up", "medium shot", "wide shot", "establishing shot")
- `prompt_has_lighting_pattern`: True (contains "golden hour", "Rembrandt", "rim", "volumetric")
- `prompt_under_400_tokens`: True
- `files_generated`: N

**If `prompt_has_camera_technical` is False:**
- Halt pipeline
- Report: "Gate 3 FAILED: Prompt missing Camera/Technical layer. The Content Generation Executor did not read `flux-best-practices/t2i-prompting.md` or did not apply it. Rewrite the prompt with shot type, lens, aperture, and film stock, then regenerate."

### Gate Failure Actions

| Gate | Failure Mode | Action |
|---|---|---|
| Gate 0 | locked_brief missing | Halt. Report: "No locked brief found. Run idea discussion first." |
| Gate 1 | creative_specs missing or <3 creatives | Halt. Send creative subagent back for revision. |
| Gate 2 | copy_manifest missing or file count mismatch | Halt. Send copy subagent back to generate missing files. |
| Gate 3 | skill_reading_log missing or prompt lacks camera/technical | Halt. Send assets subagent back to re-read skills and regenerate. |
| Gate 4 | final_review missing or file existence check failed | Halt. Send review subagent back to complete verification. |

**Never skip a failing gate. Never proceed to the next stage with a failed gate.**

---

## Phase 2: Subagent Spawning Protocol

### CRITICAL: The Orchestrator Does NOT Execute Stages

**Your role is to SPAWN subagents, not to DO their work.**

The orchestrator must NEVER:
- Write `creative_specs.json` itself → creative concepting is the creative subagent's job
- Write copy variant files itself → copy writing is the copy subagent's job
- Generate image prompts or call image tools itself → asset generation is the assets subagent's job
- Write `final_review.json` itself → review is the review subagent's job

**Why this matters:**
- If you write creative specs inline, you will produce 1-2 shallow concepts instead of 3-5 distinct angles
- If you write copy variants inline, you will put descriptions in JSON but never write individual `.md` files to `copy_variants/` — the next stage will find an empty folder
- If you generate images inline, each image takes 3 minutes and you will exhaust context after 2 images, taking 25+ minutes total
- If you do review inline, you will fabricate file counts because you never verified actual files on disk

**The ONLY things the orchestrator does directly:**
1. Read the company profile and idea pool
2. Lock the brief with the user
3. Spawn subagents for each stage
4. Validate subagent outputs against review criteria
5. Write checkpoint and gate files
6. Present summaries to the user for approval

**If you are writing JSON files, calling image tools, or generating copy text yourself — YOU ARE DOING IT WRONG. Stop and spawn the appropriate subagent.**

---

### Subagent Spawning Protocol

For EACH stage:
1. Spawn a subagent using the `Agent` tool with `subagent_type: general-purpose`. Pass the full context the subagent needs. **Do NOT assume subagents remember anything from previous stages.**
2. **SELF-REVIEW (MANDATORY):** Read `skills/meta/reviewer.md`. Load the stage's `review_focus` items from `pipeline_defs/marketing-creative.yaml`. Check the subagent output against each review_focus item. Categorize findings: critical (must fix), suggestion (note and proceed), nitpick (ignore). If critical findings exist, send the subagent back for revision (max 3 send-backs).
3. Write a checkpoint file: `[project_path]/checkpoint_[stage].json` with status `"completed"` (or `"awaiting_human"` if `human_approval_default: true`).
4. Write a gate file using `lib/checkpoint.py:write_gate()` — this is MANDATORY and non-bypassable.
5. If `human_approval_default: true`, present the artifact summary to the user and **wait for explicit approval** before spawning the next stage.

### Subagent Context Contract

Every subagent MUST receive in its prompt:

1. **Locked Brief** (from Phase 1)
2. **Input Artifacts** (produced by previous stages — paste content inline)
3. **Stage Director Skill Path** (tell them which file to read)
4. **Steering Rules** (failure patterns to avoid — see below)
5. **Output Format** (what artifact to produce and where to save it)

### Stage-by-Stage Spawning

#### Stage: research

**Action:** Spawn `Agent` with `subagent_type: general-purpose`.

```
Prompt template for subagent:
---
You are the Research Director for the marketing-creative pipeline.

LOCKED BRIEF:
[paste locked brief]

YOUR TASK:
Read the skill at skills/pipelines/marketing-creative/research-director.md
Execute the research stage. Produce a research_brief artifact.

STEERING RULES:
- The user has ALREADY selected a single idea. Your job is to RESEARCH that idea, not generate new ones.
- DO NOT produce an "ideas" section with multiple scored ideas. Only research the locked idea.
- Find REAL signals from REAL platforms (YouTube, Reddit, news, Twitter/X)
- At least 3 distinct signals with source URLs
- Competitor entries must have actual names and specific tactics
- Do NOT invent signals or sources

Save the research_brief to:
[project_path]/artifacts/research_brief.json

Return the full artifact content in your response.
---
```

#### Stage: creative_concept

**Action:** Spawn `Agent` with `subagent_type: ad-creative-strategist`.

```
Prompt template for subagent:
---
You are the Creative Director for the marketing-creative pipeline.

LOCKED BRIEF:
[paste locked brief]

INPUT ARTIFACT — Research Brief:
[paste research_brief content]

YOUR TASK:
Read the skill at skills/pipelines/marketing-creative/creative-director.md
Execute the creative_concept stage. Produce creative_specs.

STEERING RULES:
- Each creative must have a DISTINCT angle/hook (not 6 versions of the same idea)
- visual_direction describes MOOD, not UI wireframes
- Budget guidance must be specific (Rs./day, not vague)
- Format and placement must match target platform

Save creative_specs to:
[project_path]/artifacts/creative_specs.json

Return the full artifact content.
---
```

#### Stage: copy

**Action:** Spawn `Agent` with `subagent_type: copy-variant-creator`.

```
Prompt template for subagent:
---
You are the Copy Director for the marketing-creative pipeline.

LOCKED BRIEF:
[paste locked brief]

INPUT ARTIFACT — Creative Specs:
[paste creative_specs content]

YOUR TASK:
Read the skill at skills/pipelines/marketing-creative/copy-director.md
Execute the copy stage. Produce a copy_manifest.

STEERING RULES:
- 5 angles per creative: pain_point, direct_benefit, emotional, comparison, offer_led
- **LANGUAGE RULE:** Generate copy ONLY in the language specified in the locked brief. Do NOT generate multiple languages.
- If locked language is Hinglish: use natural code-switching, not forced translation
- If locked language is a regional Indian language (Odia, Bengali, Marathi, Malayalam, Gujarati, Telugu, Kannada, Tamil): ensure native script is used for image text overlays
- Headlines must be punchy and platform-appropriate
- Run the "read aloud" naturalness test on all copy variants
- **WRITE INDIVIDUAL FILES:** You MUST write one .md file per angle per language to [project_path]/copy_variants/. Do NOT put all variants in a single JSON file.
- **VERIFY FILE COUNT:** Before finishing, count the actual .md files in copy_variants/. The count must equal creatives × 5 angles × languages.

Save copy_manifest and individual copy variants to:
[project_path]/copy_variants/

Return the full copy_manifest content.
---
```

#### Stage: assets

This is the **critical quality stage**. The orchestrator must micromanage this subagent.

**Action:** Spawn `Agent` with `subagent_type: content-generation-executor-kimi`.

```
Prompt template for subagent:
---
You are the Asset Director for the marketing-creative pipeline.

LOCKED BRIEF:
[paste locked brief]

INPUT ARTIFACTS:
- Creative Specs: [paste]
- Copy Manifest: [paste]

SELECTION (made by orchestrator):
- Creative: [CR-XX]
- Angle: [pain_point / direct_benefit / emotional / comparison / offer_led]
- Language: [locked brief language — one of: English, Hinglish, Hindi, Odia, Bengali, Marathi, Malayalam, Gujarati, Telugu, Kannada, Tamil]

YOUR TASK:
1. Read skills/pipelines/marketing-creative/asset-director.md (MANDATORY)
2. Read skills/meta/image-prompt-from-copy-variant.md (MANDATORY)
3. Read .agents/skills/flux-best-practices/rules/t2i-prompting.md (MANDATORY)
4. Read .agents/skills/flux-best-practices/rules/typography-text.md (MANDATORY)
5. Read .agents/skills/flux-best-practices/rules/model-selection-guide.md (MANDATORY)
6. Write skill_reading_log.json to logs/skill_reading_log.json with all 5 skills documented
7. Produce the image prompt using the Visual Brief pattern WITH Camera/Technical layer
8. Generate the image using the appropriate tool

**You MUST read all 5 skills before writing the prompt. The skill_reading_log.json is a MANDATORY output. If it is missing, the pipeline halts at Gate 3.**

STEERING RULES — CRITICAL:
- MANDATORY SKILL STACK: You MUST read all 5 skills listed above. The prompt must reflect what you learned from them.
- VISUAL BRIEF PATTERN + CAMERA/TECHNICAL: Every prompt MUST include:
  - Emotional contrast + 1-2 visual anchors per side + text overlays in LOCKED language
  - Color palette with hex codes or precise named colors
  - Named lighting pattern (golden hour, Rembrandt, rim, volumetric)
  - **Camera/Technical layer: shot type, framing, angle, lens, aperture, depth of field, film stock**
  - EXCLUDE: checkmarks, specific fonts, gradient transitions, full UI specs
- LANGUAGE PROPAGATION: copy variant language → image text MUST be same language
  - Copy language and image text language must match exactly.
  - **Regional language note:** If locked language uses a non-Latin script (Odia, Bengali, Marathi, Malayalam, Gujarati, Telugu, Kannada, Tamil, Hindi-Devanagari), the prompt must specify the script name explicitly (e.g., "text overlay in Bengali script", "text in Telugu script").
  - GPT Image 2 handles Devanagari and major Indic scripts. For best results with rare scripts, consider Gemini which explicitly supports CJK, Devanagari, Arabic, and other scripts.
  - This is a pipeline bug if violated. Stop and fix.
- TOKEN LIMIT: Keep prompt under 400 tokens. The Camera/Technical layer adds ~40-80 tokens. Total must still be under 400.
- NO CHECKLISTS in generated images
- NO SPECIFIC FONTS requested

MANDATORY PRE-GENERATION CHECKLIST (Gate-Blocking):
- [ ] Prompt describes MOOD, not UI
- [ ] At most 2 visual anchors per side
- [ ] Image text matches copy variant language
- [ ] Prompt under 400 tokens
- [ ] No checklist/checkmark UI elements
- [ ] No specific fonts
- [ ] Emotional contrast explicit
- [ ] **Camera/Technical layer present** (shot type, lens, aperture, film stock)
- [ ] **Lighting pattern named** (golden hour, Rembrandt, rim, volumetric)
- [ ] **Color palette includes hex codes or precise named colors**
- [ ] **All 5 mandatory skills were read** (evidenced by skill_reading_log.json)
- [ ] **skill_reading_log.json exists** in logs/ with all 5 skills listed
- [ ] **FACTUAL VERIFICATION: All dates, prices, product names in prompt match locked brief**
- [ ] **TEXT OVERLAY VERIFICATION: Any text in image is factually accurate (years, dates, prices)**

**If ANY check fails, DO NOT generate the image. Rewrite the prompt and re-verify. This checklist is gate-blocking.**

Save outputs:
- Asset manifest: [project_path]/artifacts/asset_manifest.json
- Image: [project_path]/assets/[filename].png
- Prompt log: [project_path]/assets/[filename].prompt.json
- Prompt markdown: [project_path]/assets/[filename]_prompt.md
- Skill reading log: [project_path]/logs/skill_reading_log.json (MANDATORY)

Return: asset manifest, generation parameters, file paths, and confirmation that skill_reading_log.json was written.
---
```

**Content-Generation-Executor Reconciliation:**
If images are generated via the `content-generation-executor` agent instead of the assets subagent directly:
1. After executor returns, read all generated `.prompt.json` files
2. Update the asset manifest to include ALL generated assets (not just what the assets subagent prepared)
3. Verify file paths resolve to actual files on disk
4. Reconcile cost: sum all `.prompt.json` costs into the manifest total_cost_usd

**After the assets subagent returns:**
1. Read the generated image prompt
2. Verify `logs/skill_reading_log.json` exists with all 5 skills listed
3. Verify the language propagation rule
4. Verify the Visual Brief pattern was followed
5. **Verify Camera/Technical layer is present** (search prompt for "mm lens" or "f/" or "film stock" or "depth of field")
6. **Verify shot type is present** (search for "close-up", "medium shot", "wide shot", "establishing shot")
7. **Verify named lighting pattern is present** (search for "golden hour", "Rembrandt", "rim", "volumetric")
8. **Verify factual accuracy: dates, prices, product names in prompt and text overlays**
9. **Write Gate 3 using Python:**
   ```python
   from lib.checkpoint import write_gate
   write_gate(
       project_dir=Path("[project_path]"),
       gate_id="gate-03-assets",
       stage="assets",
       validation={
           "asset_manifest_exists": True,
           "skill_reading_log_exists": True,
           "skills_read_count": 5,
           "prompt_has_camera_technical": True,
           "prompt_has_shot_type": True,
           "prompt_has_lighting_pattern": True,
           "prompt_under_400_tokens": True,
           "files_generated": N,
       },
       artifact_paths=[Path("[project_path]/artifacts/asset_manifest.json"), ...],
   )
   ```
10. If ANY check fails → flag it, instruct the subagent to rerun with correction
11. If image generation failed → try fallback provider, or escalate to user

#### Stage: review

**Action:** Spawn `Agent` with `subagent_type: general-purpose`.

```
Prompt template for subagent:
---
You are the Review Director for the marketing-creative pipeline.

LOCKED BRIEF:
[paste locked brief]

INPUT ARTIFACTS:
- Asset Manifest: [paste]
- Copy Manifest: [paste]
- Creative Specs: [paste]

YOUR TASK:
Read skills/pipelines/marketing-creative/review-director.md
Execute the review stage. Produce final_review.

STEERING RULES:
- Verify language propagation: image text language MUST match copy variant language
- Verify assets match creative spec emotional direction
- Verify no flat infographic/checklist images snuck through
- Define A/B test plan with at least 2 variant pairs
- Budget summary must be accurate

Save final_review to:
[project_path]/artifacts/final_review.json

Return the full artifact.
---
```

### Post-Stage Gate Writing (MANDATORY for ALL stages)

After EVERY subagent returns and passes self-review, you MUST write both a checkpoint AND a gate:

```python
from lib.checkpoint import write_checkpoint, write_gate
from pathlib import Path

# 1. Write checkpoint
write_checkpoint(
    pipeline_dir=Path("[project_path]").parent,
    project_id="[campaign_id]",
    stage="[stage_name]",
    status="completed",
    artifacts={"[canonical_artifact_name]": {...}},
)

# 2. Write gate (NON-BYPASSABLE)
write_gate(
    project_dir=Path("[project_path]"),
    gate_id=f"gate-[NN]-[stage_name]",
    stage="[stage_name]",
    validation={
        "[artifact]_exists": True,
        "[other_validation]": True,
    },
    artifact_paths=[Path("[project_path]/artifacts/[file].json")],
)
```

**Stage-to-gate mapping:**
| Stage | Gate ID | Key Validations |
|---|---|---|
| research | gate-00-research | research_brief exists, ≥3 signals, ≥2 competitors |
| creative_concept | gate-01-creative | creative_specs exists, ≥3 creatives, distinct angles |
| copy | gate-02-copy | copy_manifest exists, file count matches, all languages present |
| assets | gate-03-assets | asset_manifest exists, skill_reading_log exists, camera/technical present |
| review | gate-04-review | final_review exists, file existence check passed, A/B plan has 2 pairs |

**If you do not write the gate file, the next stage CANNOT proceed.** The gate is what makes skipping impossible.

## Steering Rules — Lessons from v1 Failure

These rules exist because the pipeline previously produced bad output. Enforce them ruthlessly.

### Steering Rule 1: Visual Brief Pattern (Creativity Preservation)

**What went wrong in v1:** The pipeline dumped full creative spec UI details into image prompts. Result: generic infographic with checkmarks.

**What v2 does:** Visual Brief = emotional direction + visual anchors + locked language text + color palette + lighting.

**Your job as orchestrator:** After the assets subagent produces a prompt, verify:
- Does it describe MOOD or UI? (Must be mood)
- Are there ≤2 visual anchors per side? (More = over-specified)
- Is the prompt under 400 tokens? (Longer = less creative)

**If any check fails:** Send the subagent back with: "Rewrite prompt using Visual Brief pattern. Remove UI specs. Focus on mood and emotional contrast."

### Steering Rule 2: Language Propagation (Hinglish Enforcement)

**What went wrong in v1:** Hinglish copy variant was selected, but image prompt had 100% English text overlays.

**Your job as orchestrator:** After the assets subagent produces a prompt, grep for text overlays. Verify:
- Hinglish copy → Hinglish image text overlays
- English copy → English image text overlays
- Hindi copy → Hindi (Devanagari) image text overlays

**If wrong language:** This is a pipeline bug. Instruct subagent: "Language propagation failed. Copy variant is [language] but image text is [wrong language]. Rewrite all image text overlays in [language]."

### Steering Rule 3: Factual Verification (Pre-Generation)

**What went wrong:** CR-01 image showed "May 2025" instead of "May 2026" because the prompt did not explicitly state the year.

**What we do now:** Before ANY image generation call, verify:
- [ ] All dates in the prompt match the locked brief
- [ ] All prices/currencies match the locked brief
- [ ] All product names match the locked brief
- [ ] Any text overlay contains factual claims? If yes, verify against company_context

**If any check fails:** Stop generation. Fix the prompt. Re-verify.

### Steering Rule 4: Subagent Output Validation

After every subagent completes, validate its output against the stage's `success_criteria` from the pipeline manifest (`pipeline_defs/marketing-creative.yaml`).

| Stage | Validation Check | If Failed |
|---|---|---|
| research | ≥3 signals with URLs? ≥2 competitors? | Send back for more research |
| creative_concept | ≥3 distinct angles? visual_direction is mood? | Send back for revision |
| copy | All 5 angles × all locked-brief languages present? **Count actual files on disk.** | Send back for completion |
| assets | Visual Brief followed? Language correct? File exists at claimed path? | Send back for rewrite |
| review | A/B plan has ≥2 pairs? Budget accurate? **File existence pre-check passed?** | Send back for completion |

**File existence is non-negotiable.** If a subagent claims to have written 75 copy variants but fewer files exist on disk, that stage is NOT complete. Do not proceed. Send the subagent back with: "File count mismatch. Manifest claims X files but only Y exist. Generate the missing files."

**Max 3 send-backs per stage.** After 3, proceed with warnings noted.

**Batch execution limit:** If running multiple campaigns in one session, enforce a hard limit of 2 campaigns maximum per invocation. Write batch_manifest.json and halt.

### Steering Rule 4: Budget Governance

Track spend at every generation step. The pipeline default is $5.00.

| Tool | Cost per call |
|---|---|
| `openai_image` (gpt-image-2, high, 1024x1024) | ~$0.167 |
| `google_imagen` | Varies by model |
| `gemini_image` | Varies by model |

Before any paid generation:
1. Announce cost to user
2. Verify total estimated cost ≤ budget cap
3. If over budget: switch provider, reduce scope, or ask user to increase budget

## Phase 3: Checkpoint & Approval Protocol

Between stages, follow the checkpoint protocol from `skills/meta/checkpoint-protocol.md`.

### Mandatory Human Approval Gates

Pause and present to user for approval BEFORE spawning the next subagent:

| After Stage | What to Present | Wait for User? |
|---|---|---|
| research | Research brief summary (3 signals, top competitor, idea score) | YES |
| creative_concept | Creative spec summaries (3+ angles, hooks, visual directions) | YES |
| copy | Copy variant summary (angles × languages, headline samples) | YES |
| assets | Generated image + prompt + cost | NO (auto-proceed after variant selection) |
| review | Final review + A/B plan + budget summary | YES |

**Approval prompt template:**
```
[Stage] complete. Here's the summary:

[3-5 bullet points of key findings/decisions]

[If applicable] Sample output: [paste a representative excerpt]

Approve and proceed to [next stage]? Or request revisions?
```

### Decision Communication Contract

Before any paid generation call, state:
- Exact tool name
- Provider and model
- Reason for choice
- Whether sample or batch
- Estimated cost

## Error Recovery Protocol

| Scenario | Action |
|---|---|
| Subagent produces bad output | Send back with specific steering instruction (max 3 retries) |
| Image generation fails | Try fallback provider via `image_selector`. Announce switch. |
| Language propagation fails | CRITICAL. Stop pipeline. Flag bug. Do not proceed. |
| Budget exceeded | Stop. Present options: reduce scope, switch provider, increase budget. Wait. |
| User rejects stage artifact | Collect feedback, send subagent back with revision notes (max 3 revisions) |
| Subagent times out or crashes | Retry once. If fails again, escalate to user with blocker format. |

### Blocker Escalation Format

When a hard blocker occurs, present to user:

```
BLOCKER: [short description]

What was attempted: [action]
What failed: [error or bad output]
Issue type: [auth / provider access / tool bug / prompt quality / budget]
Options:
  1. [option with estimated outcome]
  2. [option with estimated outcome]
  3. [option with estimated outcome]

Recommendation: [option N] because [reason]
```

## Project Directory Convention

Each orchestrated run creates a project workspace. The root path is determined by `company_context.paths.project_root` from the company profile (e.g., `company_profiles/91astrology.json`).

**Path Resolution Rule:**
- Read `company_context.paths.project_root` from the company profile
- Resolve it relative to the `openMontage/` repo root
- Example: if `project_root` = `"../91_astro/"`, resolved path = `C:/.../Marketing_automations/91_astro/`
- **Never hardcode internal paths** like `openmontage/91astrology/nadi-report/`. Always use the company profile value.

**Campaign workspace structure:**
```
[resolved_project_root]/campaigns/[campaign_id]/
├── README.md                    # Campaign brief and locked brief
├── artifacts/
│   ├── research_brief.json
│   ├── creative_specs.json
│   ├── copy_manifest.json
│   ├── asset_manifest.json
│   └── final_review.json
├── copy_variants/
│   └── [cr_id]_[angle]_[language].md
└── assets/
    ├── [filename].png
    ├── [filename].prompt.json
    └── [filename]_prompt.md
```

## Invocation from Fresh Window

When invoked in a fresh Claude Code window, the orchestrator:

1. **Assumes the user is in the OpenMontage repo** (the skill only exists here)
2. **Reads this skill** (you are reading it now)
3. **Reads the pipeline manifest** (`pipeline_defs/marketing-creative.yaml`)
4. **Runs preflight** (registry discovery for image tools)
5. **Validates output path:** Read `company_context.paths.project_root`. Verify it resolves to the correct external folder (e.g., `../91_astro/`, NOT an internal OpenMontage path). If wrong, report to user before proceeding.
6. **Begins Phase 1** (idea discussion)

**The user does NOT need prior context.** All instructions are in this skill + the pipeline manifest + stage director skills.

## Quick Reference: Subagent Spawning Commands

```python
# Research subagent
Agent({
  description: "Marketing pipeline: research stage",
  prompt: "You are the Research Director... [full context]..."
})

# Creative concept subagent
Agent({
  description: "Marketing pipeline: creative concept stage",
  prompt: "You are the Creative Director... [full context]..."
})

# Copy subagent
Agent({
  description: "Marketing pipeline: copy stage",
  prompt: "You are the Copy Director... [full context]..."
})

# Assets subagent
Agent({
  description: "Marketing pipeline: assets stage",
  prompt: "You are the Asset Director... [full context with Visual Brief rules]..."
})

# Review subagent
Agent({
  description: "Marketing pipeline: review stage",
  prompt: "You are the Review Director... [full context]..."
})
```

## Related Files

- Pipeline manifest: `pipeline_defs/marketing-creative.yaml`
- Stage directors: `skills/pipelines/marketing-creative/*-director.md`
- Visual Brief meta skill: `skills/meta/image-prompt-from-copy-variant.md`
- Reviewer meta skill: `skills/meta/reviewer.md`
- Checkpoint protocol: `skills/meta/checkpoint-protocol.md`
