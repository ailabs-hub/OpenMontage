# OpenMontage — Marketing Creative Pipeline

This repository houses the marketing-creative pipeline for producing static marketing assets (ad images, copy variants, campaign concepts).

## Auto-Routing Rules

When the user mentions any of the following, **automatically execute the marketing-creative pipeline**:

- "Run a campaign about..."
- "Generate ad creatives for [company]"
- "Create a marketing campaign"
- "Make ad images for..."
- "Run idea-01 through the pipeline"
- "Create a campaign from this screenshot"
- "Adapt this competitor ad"
- Any request involving ad copy, creative concepts, or campaign assets

**Action:** Read `skills/pipelines/marketing-creative/agent-pipeline-driver.md` and execute the pipeline per its instructions. Do NOT ask the user for confirmation before starting.

## How the Pipeline Runs

The agent-native execution mode runs the entire pipeline in one continuous session:

1. Read `agent-pipeline-driver.md`
2. Initialize session via `agent_utils.init_session()`
3. Execute stages sequentially: idea → concept → copy → assets → review
4. Generate images via OpenMontage Python tools (`image_selector`, `flux_image`)
5. Present deliverables

**No subagents. No `--resume` loop. The agent drives everything.**

## Key Files

| File | Purpose |
|------|---------|
| `skills/pipelines/marketing-creative/agent-pipeline-driver.md` | **Primary execution skill** — read this first |
| `pipelines/marketing_creative/agent_utils.py` | Session management utilities |
| `pipeline_defs/marketing-creative.yaml` | Pipeline manifest (stages, gates, tools) |
| `skills/pipelines/marketing-creative/executive-producer.md` | High-level pipeline overview |
| `../company_profiles/{slug}.json` | Company configuration |

## What NOT to Do

- Do NOT read `AGENT_GUIDE.md` — it covers video pipelines, not marketing creative.
- Do NOT spawn subagents.
- Do NOT use Claude Code built-in image tools. Use OpenMontage Python tools only.
- Do NOT fall back to video pipelines for marketing creative requests.
