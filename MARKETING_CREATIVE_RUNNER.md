# Marketing Creative Pipeline — Automated Runner

**When to use:** Any time the user mentions marketing campaigns, ad creatives, copy variants, running an idea through a pipeline, or wants to generate ad images/copy.

**What this does:** Runs the full marketing-creative pipeline end-to-end automatically. You handle the execution — the user just provides the idea and sees the final deliverables.

---

## Trigger Phrases

- "Run a campaign about..."
- "Generate ad creatives for [company]"
- "I want to create a marketing campaign"
- "Make me some ad images for..."
- "Run idea-01 through the pipeline"
- "Create a campaign from this screenshot"
- "Adapt this competitor ad for us"

---

## Execution Modes

There are two ways to run this pipeline. **Mode A (Agent-Native) is recommended.**

### Mode A: Agent-Native Deterministic (Recommended)

You read a single driver skill and execute all stages in one continuous session. **No CLI calls. No `--resume` loop.** This is the fastest and most reliable method.

**Flow:**
```
User provides idea → You read agent-pipeline-driver.md → Initialize session → Execute all stages → Present deliverables
```

**How it works:**
1. Read `skills/pipelines/marketing-creative/agent-pipeline-driver.md`
2. Initialize session via `agent_utils.init_session()`
3. For each stage in the deterministic sequence:
   - Check completion via `agent_utils.is_stage_complete()`
   - Read the stage director skill
   - Load inputs, execute creative work, write outputs
   - Mark complete via `agent_utils.mark_stage_complete()`
4. Generate images via OpenMontage Python tools
5. Present deliverables

**Key advantages:**
- Zero CLI calls
- Single continuous session (better context retention)
- Deterministic stage sequence
- Agent is the orchestrator

### Mode B: CLI Self-Execution (Legacy)

You call the Python orchestrator CLI to get stage instructions, then call `--resume` between stages.

**Flow:**
```
User provides idea → Call Python orchestrator → Read stage skill → Execute stage → Call Python resume → Repeat
```

**Use when:** You need the orchestrator to manage complex state or want to pause between stages for debugging.

---

## Mode A: Agent-Native Execution

### Step 1: Parse the user's input

Determine:
- **Company:** Did they mention a company? If not, ask. Look in `../company_profiles/*.json`.
- **Input source:** Is it raw text, an image, a URL, or an idea-pool reference?
- **Research needed?** Only enable if the user explicitly asks for market research. Default is skip.

### Step 2: Read the Agent Pipeline Driver

Read: `skills/pipelines/marketing-creative/agent-pipeline-driver.md`

This skill contains the exact step-by-step instructions for executing the pipeline. Follow it precisely.

### Step 3: Initialize Session

Run:

```python
python -c "
from pipelines.marketing_creative.agent_utils import init_session
print(init_session('CAMPAIGN_ID', 'COMPANY', 'INPUT_TYPE', research=RESEARCH))
"
```

This returns the campaign directory path and creates `.session.json`.

### Step 4: Execute All Stages

For each stage in the deterministic sequence:

1. **Check if already complete:**
   ```python
   python -c "from pipelines.marketing_creative.agent_utils import is_stage_complete; print(is_stage_complete('CAMPAIGN_ID', 'COMPANY', 'STAGE_ID'))"
   ```

2. **Get skill path:**
   ```python
   python -c "from pipelines.marketing_creative.agent_utils import get_stage_skill_path; print(get_stage_skill_path('STAGE_ID'))"
   ```

3. **Read the skill file** and follow its instructions exactly

4. **Load inputs** (resolve paths via `agent_utils.resolve_stage_inputs()`)

5. **Execute creative work** and write all outputs

6. **Mark stage complete:**
   ```python
   python -c "from pipelines.marketing_creative.agent_utils import mark_stage_complete; mark_stage_complete('CAMPAIGN_ID', 'COMPANY', 'STAGE_ID')"
   ```

7. **Immediately proceed to next stage**

### Step 5: Image Generation (Assets Stage)

Generate images using OpenMontage Python tools:

```python
python -c "
from tools.tool_registry import registry
registry.discover()

selector = registry.get('image_selector')
result = selector.execute({
    'prompt': '[your optimized Visual Brief prompt]',
    'width': 1024,
    'height': 1024,
    'output_path': 'CAMPAIGN_DIR/assets/cr01_pain_point_english.png',
    'preferred_provider': 'auto',
})
print(f'Success: {result.success}')
print(f'Output: {result.data.get(\"output\")}')
"
```

### Step 6: Present Deliverables

When all stages are complete:
- Campaign ID and directory path
- Stages completed
- Final artifacts: creative specs, copy variants, generated images, review report
- A/B test plan from `final_review.json`
- Budget summary from `.session.json`

---

## Mode B: CLI Self-Execution Loop

Use this mode only if you need the orchestrator to manage state or pause between stages.

### Step 1: Parse input and run CLI

```bash
cd C:\Users\91829\Desktop\Vansun\Marketing_automations\OpenMontage
python -m pipelines.marketing_creative \
  --campaign-id <kebab-case-slug> \
  --company <company-slug> \
  --input-text "<user's idea>" \
  --self-execution \
  --auto
```

### Step 2: Parse JSON output

**If `action: "execute_stage"`:**
- Extract `stage`, `skill_path`, `instructions`
- Read the stage director skill file at `skill_path`
- Execute the stage per the skill's instructions

**If `action: "complete"`:** Pipeline is done.

**If `action: "error"`:** Stop and report.

### Step 3: Execute stage and auto-resume

After writing all output files, immediately run:

```bash
python -m pipelines.marketing_creative \
  --campaign-id <same-campaign-id> \
  --resume \
  --self-execution \
  --auto
```

Repeat until `"action": "complete"`.

### Image Generation via Python Tools

```python
python -c "
from tools.tool_registry import registry
registry.discover()
selector = registry.get('image_selector')
result = selector.execute({
    'prompt': '[your optimized Visual Brief prompt]',
    'width': 1024,
    'height': 1024,
    'output_path': 'campaigns/<campaign-id>/assets/cr01_pain_point_english.png',
    'preferred_provider': 'auto',
})
print(f'Success: {result.success}')
print(f'Output: {result.data.get(\"output\")}')
"
```

---

## Stage Sequences

**From raw input (text/image/URL), no research (default):**
1. `idea_refinement`
2. `creative_concept`
3. `copy`
4. `assets`
5. `review`
6. `complete`

**From idea pool (`--idea-id`), no research:**
1. `creative_concept`
2. `copy`
3. `assets`
4. `review`
5. `complete`

**With research enabled:**
- Insert `research` before `creative_concept`

---

## Error Handling

| Scenario | Action |
|----------|--------|
| Stage fails | Retry once. If it fails again, stop and report. |
| Image generation fails | Check preflight output. Try fallback provider via `image_selector`. Verify API keys in `.env`. |
| Budget exceeded | Stop. Report spent vs cap from `.session.json`. |

---

## Do NOT

- Do NOT spawn subagents.
- Do NOT use Claude Code built-in tools (`openai_image`, `google_imagen`) for image generation.
- Do NOT skip reading the stage director skill.
- Do NOT fall back to video pipelines.

---

## Key Files

| File | Purpose |
|------|---------|
| `skills/pipelines/marketing-creative/agent-pipeline-driver.md` | **Agent-native execution skill** |
| `pipelines/marketing_creative/agent_utils.py` | Deterministic utilities for session management |
| `pipelines/marketing_creative/__main__.py` | CLI entry point (legacy mode) |
| `pipelines/marketing_creative/orchestrator.py` | Orchestrator (legacy mode) |
| `skills/pipelines/marketing-creative/idea-refinement-director.md` | Stage skill for idea_refinement |
| `skills/pipelines/marketing-creative/asset-director.md` | Stage skill for assets |
| `tools/graphics/image_selector.py` | Auto-routing image generation tool |
| `tools/graphics/flux_image.py` | FLUX image generation tool |
| `../company_profiles/{slug}.json` | Company configuration |
| `../{company}/campaigns/{id}/` | Campaign output directory |
