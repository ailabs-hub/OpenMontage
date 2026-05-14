# Plan: Permissions + Optional Checkpoints + Subagent Scoping + Directory Slimming

## Context

The marketing-creative pipeline works end-to-end but has four friction points:

1. **Permission prompts** — Claude Code stops at every bash command and subagent spawn. The user wants a config-file approach instead of `/auto` mode.
2. **Checkpoint/gate overhead** — Writing `checkpoint_*.json` + `gate-*.json` per stage is redundant when `.session.json` already tracks all state.
3. **Subagents read too many files** — Spawned subagents explore the OpenMontage directory and encounter 73+ video/animation skills, 246MB of `remotion-composer`, and other irrelevant files. They get distracted.
4. **Directory bloat** — OpenMontage is dominated by video pipeline infrastructure that's never used by marketing-creative. This wastes context window and confuses subagents.

## Discovery

### Permissions File Already Exists

`.claude/settings.local.json` contains `permissions.allow` with regex-like patterns:
```json
{
  "permissions": {
    "allow": [
      "Bash(python *)",
      "WebSearch",
      "Bash(git *)",
      ...
    ]
  }
}
```
Claude Code checks this file before asking for permission. Matching patterns auto-approve.

### Directory Sizes

| Directory | Size | Needed for Marketing-Creative? |
|---|---|---|
| `remotion-composer/` | 246.8 MB | NO — video composition engine |
| `assets/` | 20.4 MB | NO — generated media |
| `tools/` | 2.6 MB | PARTIAL — only image_selector, registry |
| `.agents/skills/` | 3.0 MB | PARTIAL — only flux, bfl (image gen) |
| `.claude/` | 2.6 MB | YES — settings + skills |
| `skills/pipelines/` | 1.0 MB | PARTIAL — only `marketing-creative/` subdirectory |
| `lib/` | 0.2 MB | YES — shared utilities |
| `pipelines/` | 0.1 MB | YES — pipeline code |
| `pipeline_defs/` | 0.1 MB | YES — manifest |
| `schemas/` | 0.1 MB | YES — artifact schemas |

**Total bloat:** ~270+ MB of video-specific files in a repo that only needs ~5 MB for marketing-creative.

### Subagent Scope Problem

When a subagent is spawned, its working directory is the OpenMontage root. It has access to:
- 14 pipeline skill directories (`skills/pipelines/animation`, `cinematic`, `talking-head`, etc.)
- 73 `.agents/skills/` directories (video gen, TTS, avatar, animation, etc.)
- `remotion-composer/` with hundreds of files
- `tools/` with video-specific tools

The subagent prompt currently says "Read the stage director skill at: [path]" but does NOT explicitly forbid reading other files. Subagents often explore and get distracted.

## Goal

1. **Permissions file** — Add marketing-creative patterns to `.claude/settings.local.json` so pipeline actions auto-approve without `/auto`
2. **Optional checkpoints** — Skip `checkpoint_*.json` and `gate-*.json` writes when `--auto` is used
3. **Subagent file scoping** — Add explicit "ONLY read these files" instructions to subagent prompts
4. **Directory slimming** — Create `.claudeignore` to hide video-specific directories from Claude Code context

## Changes

### 1. `.claude/settings.local.json` — UPDATE

Add patterns to `permissions.allow` for marketing-creative pipeline actions:

```json
"Agent(*Marketing pipeline:*)",
"Agent(*idea_refinement*)",
"Agent(*creative_concept*)",
"Agent(*copy*)",
"Agent(*assets*)",
"Agent(*review*)",
"Read(*.session.json)",
"Read(*campaigns*)",
"Read(*ideas*)",
"Read(*artifacts*)",
"Write(*campaigns*)",
"Write(*ideas*)",
"Write(*artifacts*)",
"Edit(*.session.json)"
```

### 2. `pipelines/marketing_creative/orchestrator.py` — UPDATE

Skip checkpoints/gates when `--auto` is used:

```python
# In __init__:
self.skip_checkpoints = self.session.state.get("auto_mode", False)

# In resume_with_subagent_result:
if not self.skip_checkpoints:
    self._write_checkpoint(stage, result)
    self._write_gate(stage, result, validation)
```

### 3. `lib/subagent_dispatcher.py` — UPDATE

Add explicit file-scoping instructions to the subagent prompt template in `_build_subagent_prompt()`:

Append after "CRITICAL RULES":
```
FILE SCOPE:
You are running in {openmontage_root} but you MUST NOT explore beyond these paths:
- The stage director skill at: {skill_path}
- The campaign directory at: {campaign_dir}
- The input files listed above
- The company profile at: ../company_profiles/{company}.json (if needed)
- The idea pool at: ../{company}/ideas/ (if needed)

DO NOT read files outside this scope. DO NOT explore other directories.
DO NOT read AGENT_GUIDE.md, CLAUDE.md, or any other guide files.
```

### 4. `.claudeignore` — NEW

Create at OpenMontage root to hide video-specific directories from Claude Code context:

```
# Video composition engine (246MB)
remotion-composer/

# Video pipeline skills (not needed for marketing-creative)
skills/pipelines/animation/
skills/pipelines/avatar-spokesperson/
skills/pipelines/character-animation/
skills/pipelines/cinematic/
skills/pipelines/clip-factory/
skills/pipelines/documentary-montage/
skills/pipelines/explainer/
skills/pipelines/hybrid/
skills/pipelines/localization-dub/
skills/pipelines/podcast-repurpose/
skills/pipelines/provider-benchmark/
skills/pipelines/screen-demo/
skills/pipelines/talking-head/

# Video/animation Layer 3 skills (most are irrelevant)
.agents/skills/acestep/
.agents/skills/ai-video-gen/
.agents/skills/avatar-video/
.agents/skills/canvas-procedural-animation/
.agents/skills/character-animation-qa/
.agents/skills/character-rigging/
.agents/skills/create-video/
.agents/skills/d3-viz/
.agents/skills/doubao-tts/
.agents/skills/elevenlabs/
.agents/skills/elevenlabs-agents/
.agents/skills/faceswap/
.agents/skills/ffmpeg/
.agents/skills/framer-motion/
.agents/skills/grok-media/
.agents/skills/gsap/
.agents/skills/gsap-core/
.agents/skills/gsap-frameworks/
.agents/skills/gsap-performance/
.agents/skills/gsap-plugins/
.agents/skills/gsap-react/
.agents/skills/gsap-scrolltrigger/
.agents/skills/gsap-timeline/
.agents/skills/gsap-utils/
.agents/skills/heygen/
.agents/skills/lottie-bodymovin/
.agents/skills/manim-composer/
.agents/skills/manimce-best-practices/
.agents/skills/manimgl-best-practices/
.agents/skills/music/
.agents/skills/playwright-recording/
.agents/skills/seedance-2-0/
.agents/skills/sound-effects/
.agents/skills/speech-to-text/
.agents/skills/synthetic-screen-recording/
.agents/skills/text-to-speech/
.agents/skills/video-edit/
.agents/skills/video-translate/
.agents/skills/video-understand/
.agents/skills/video_toolkit/
.agents/skills/visual-style/

# Generated media
assets/
projects/

# Styles are video-specific
styles/

# Tests (keep if needed, hide to reduce context)
tests/
```

### 5. `RUN_MARKETING_CAMPAIGN.md` — UPDATE

Replace the `/auto` prerequisite section with:

```markdown
## Prerequisites

### 1. Permissions are pre-configured

The `.claude/settings.local.json` file contains auto-approval patterns for all pipeline actions (bash commands, subagent spawns, file reads/writes). You should NOT see permission prompts.

If a permission prompt does appear, the specific tool pattern is missing from the permissions file. Add it to `.claude/settings.local.json` under `permissions.allow`.

### 2. Context is scoped

The `.claudeignore` file hides video-specific directories (remotion-composer, animation skills, TTS tools, etc.) from Claude's context. Only marketing-creative relevant files are visible.
```

## Verification

1. **Permissions test:** Run `python -m pipelines.marketing_creative ... --auto` and verify no permission prompts appear for bash, agent, read, or write operations.
2. **Checkpoints test:** Verify `.session.json` is updated but no `checkpoint_*.json` or `gate-*.json` files are created in the campaign directory.
3. **Subagent scoping test:** After spawning a subagent, verify it does NOT read files outside the campaign directory, skill path, and input files.
4. **Context slimming test:** Verify Claude Code does NOT index `remotion-composer/`, `skills/pipelines/animation/`, `.agents/skills/elevenlabs/`, etc. These should not appear in file searches or context.

## Implementation Order

1. Create `.claudeignore`
2. Update `.claude/settings.local.json` with marketing-creative permission patterns
3. Update `subagent_dispatcher.py` with file-scoping instructions
4. Update `orchestrator.py` to skip checkpoints when `auto_mode=True`
5. Update `RUN_MARKETING_CAMPAIGN.md` documentation
6. Test end-to-end with a text input campaign
