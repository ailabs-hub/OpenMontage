# Executive Producer — Marketing Creative Pipeline

## When to Use

You are the Executive Producer (EP) for a marketing creative campaign. The user has either:
1. Selected an idea from the idea pool (e.g., "Run idea-01 [idea name from pool]")
2. Given you a topic and asked you to run the full pipeline

Your job is to orchestrate the entire `marketing-creative` pipeline from start to finish: research → creative_concept → copy → assets → review.

## Architecture: How This Works

The OpenMontage framework supports two execution modes. This skill covers **both**.

### Mode A: Self-Execution (Default)
You (the AI agent) read the pipeline manifest and stage director skills, then execute each stage yourself using tools. No subagents are spawned. You are the orchestrator and the executor.

```
User picks idea → You read EP skill → You read stage skill → You execute stage → Checkpoint → Next stage
```

**Use self-execution when:**
- Processing a single campaign
- Context window is healthy (< 50% used)
- Stages are straightforward (copy + image generation)

### Mode B: Subagent Spawning
You (the AI agent) act as the orchestrator. For each stage, you spawn a dedicated subagent via the `Agent` tool with `subagent_type: general-purpose`. The subagent reads the stage skill, executes it, and returns results. You validate output, write checkpoints, and decide whether to proceed.

```
User picks idea → You lock brief → Spawn research subagent → Review → Checkpoint
                                    Spawn creative subagent → Review → Checkpoint
                                    Spawn copy subagent → Review → Checkpoint
                                    Spawn assets subagent → Review → Checkpoint
                                    Spawn review subagent → Final checkpoint
```

**Use subagent mode when:**
- Processing multiple campaigns (see Batch Multi-Campaign Protocol in orchestrator skill)
- A stage requires deep isolated context (e.g., research with web search)
- You want parallel execution of independent stages (rare — most stages are sequential)

**IMPORTANT:** Do not mix modes within a single campaign. Pick one mode at the start and stick with it for the entire pipeline. Switching modes mid-pipeline causes checkpoint inconsistency.

## Pipeline Flow

### Step 1: Idea Selection

**If user provides an idea ID:** Load the idea from the idea pool. Verify it exists and has a score.

**If user says "pick the best one":**
1. Read the idea pool file
2. Sort by score (descending)
3. Present the top 3 ideas to the user with scores and one-line summaries
4. Ask user to confirm or pick a different one
5. **Do NOT proceed without user confirmation on idea selection**

**If user provides a raw topic (no idea pool entry):**
1. Run the `research` stage first to build the idea
2. Score it
3. Present to user for approval
4. Then proceed to creative_concept

### Step 2: Run Preflight

Before any creative work, run the OpenMontage preflight:

```bash
python -c "
from tools.tool_registry import registry
import json
registry.discover()
print(json.dumps(registry.provider_menu_summary(), indent=2))
"
```

Check specifically for:
- `image_selector` or concrete image tools (`openai_image`, `google_imagen`, etc.)
- Budget tracker availability

Report capability summary to user.

### Step 3: Run Pipeline Stage by Stage

For EACH stage, follow this exact pattern:

```
1. Read the stage director skill: skills/pipelines/marketing-creative/<stage>-director.md
2. Load required input artifacts
3. Execute the stage per the skill's instructions
4. Self-review using skills/meta/reviewer.md
5. Checkpoint via checkpoint protocol
6. If human_approval_default=true: present artifact to user and WAIT for approval
7. If approved: proceed to next stage
```

**Stage order and dependencies:**

| Stage | Skill | Input Artifacts | Output Artifacts | Human Approval |
|---|---|---|---|---|
| research | research-director | (user idea or topic) | research_brief | ✅ Required |
| creative_concept | creative-director | research_brief | creative_specs | ✅ Required |
| copy | copy-director | creative_specs | copy_manifest | ✅ Required |
| assets | asset-director | copy_manifest + creative_specs | asset_manifest | ❌ Auto-proceed |
| review | review-director | asset_manifest + copy_manifest + creative_specs | final_review | ✅ Required |

### Step 4: Copy Variant Selection (Within the assets stage)

**This is the critical decision point.** The asset-director skill says to select ONE copy variant to convert into an image.

**Default selection logic:**
1. Pick the highest-performing angle from company_context.pipeline_learnings (if available)
2. Pick the primary language from company_context.primary_audience.primary_language
3. Present the selection to the user: "I'll generate for CR-01 / [angle] / [primary_language] — OK?"

**If user says "you choose":**
- Default to: `pain_point` angle (if supported by company learnings) + `primary_language`
- Rationale: Pain-point hooks generally have the best CTR. Primary language is the audience's dominant language.

**If user wants a specific variant:**
- Ask: "Which creative, angle, and language?" (e.g., "CR-03 / emotional / hindi")
- Then proceed with their selection

**After selection:**
1. Read the selected copy variant file
2. Read the creative spec for MOOD only
3. Read `skills/meta/image-prompt-from-copy-variant.md` (MANDATORY)
4. Lock the language
5. Craft the Visual Brief prompt
6. Run pre-generation checklist
7. Generate the image
8. Post-generation verification
9. Build asset manifest

### Step 5: Budget Governance

Track spend at every generation step:

| Tool | Cost per call |
|---|---|
| `openai_image` (gpt-image-2, high, 1024x1024) | ~$0.167 |
| `google_imagen` | Varies by model |
| `gemini_image` | Varies by model |

Before generating:
1. Estimate total cost for the selected variant
2. Check against pipeline budget (`orchestration.budget_default_usd`)
3. If over budget: switch to cheaper provider via `image_selector`
4. Announce cost before generating

### Step 6: Human Approval Gates

**Mandatory pauses (user must approve before proceeding):**
- After `research` — user validates signals and idea score
- After `creative_concept` — user approves creative directions
- After `copy` — user approves copy variants
- After `review` — user approves final assets for launch

**Auto-proceed stages:**
- `assets` — once copy variant is selected, generate without further approval
- But: announce before each paid generation call per Decision Communication Contract

### Step 7: Error Handling

| Scenario | Action |
|---|---|
| Image generation fails | Log error, try fallback provider via `image_selector`, report to user |
| Language propagation fails | CRITICAL. Stop. Flag pipeline bug. Do not proceed. |
| Budget exceeded | Stop. Present options: reduce scope, switch provider, or increase budget. Wait for user. |
| User rejects a stage artifact | Revise per reviewer feedback. Max 3 revisions per stage. |

### Step 8: Pipeline Completion

When `review` stage is approved:
1. Present final asset inventory
2. Present A/B test plan
3. Present budget summary
4. Hand off to user for campaign launch

## Quick Start: "Run Idea X"

When user says: **"Run idea-01 through the pipeline"**

```
1. Load idea-01 from idea pool
2. Run preflight
3. research → creative_concept → copy → assets → review
4. At each approval gate: present summary, wait for OK
5. In assets stage: select pain_point + primary_language by default (from company_context)
6. Generate image using Visual Brief + openai_image (gpt-image-2)
7. Review and present final output
```

## Batch Execution Limits

**Maximum 2 campaigns per agent invocation.** Each campaign consumes ~25-35K tokens across all stages. Attempting to process 3+ campaigns in one session causes context exhaustion, silent stage skipping, and fabricated checkpoint/review data.

If the user asks for N > 2 campaigns:
1. Process campaigns 1-2 fully (all stages, all checkpoints)
2. Write `batch_manifest.json` tracking completion status
3. Tell the user: "Campaigns 1-2 complete. Invoke me again to process campaigns 3-N."
4. **Do not attempt to process all campaigns in one go.**

## What Is NOT Automated

**The OpenMontage framework is instruction-driven, not autonomous.** These steps require the AI agent to read skills and make decisions:

- Reading and interpreting the idea pool
- Executing each stage per its director skill (self-execution mode) or spawning subagents (subagent mode)
- Making creative judgments (which angle, which language)
- Getting user approvals at checkpoints
- Handling errors and fallbacks
- **Enforcing batch limits and verifying file existence between stages**

**There is no "click and walk away" mode.** The agent must be present to orchestrate. However, with this EP skill, the agent knows exactly what to do at each step — no improvisation needed.

## Required Files Checklist

Before claiming the pipeline is ready, verify these exist:

- [ ] `pipeline_defs/marketing-creative.yaml`
- [ ] `skills/pipelines/marketing-creative/executive-producer.md` (this file)
- [ ] `skills/pipelines/marketing-creative/research-director.md`
- [ ] `skills/pipelines/marketing-creative/creative-director.md`
- [ ] `skills/pipelines/marketing-creative/copy-director.md`
- [ ] `skills/pipelines/marketing-creative/asset-director.md`
- [ ] `skills/pipelines/marketing-creative/review-director.md`
- [ ] `skills/meta/image-prompt-from-copy-variant.md`
