# Assets Director - Provider Benchmark Pipeline

## When To Use

This stage executes the `benchmark_plan` cell-by-cell and produces the `asset_manifest` artifact with one entry per generated asset, plus a `metadata.failed_cells` block for any cell that did not produce an asset.

## Prerequisites

| Layer | Resource | Purpose |
|-------|----------|---------|
| Schema | `schemas/artifacts/asset_manifest.schema.json` | Artifact validation |
| Prior artifacts | `state.artifacts["plan"]["benchmark_plan"]` | The matrix of cells to execute |
| Tools (selectors) | `image_selector`, `video_selector` | Used only when the plan cell explicitly chose the selector route |
| Tools (direct providers) | `flux_image`, `google_imagen`, `openai_image`, `grok_image`, `recraft_image`, `pexels_image`, `pixabay_image`, `runway_video`, `veo_video`, `kling_video`, `seedance_video`, `grok_video`, `minimax_video`, `heygen_video`, `ltx_video_modal`, `pexels_video`, `pixabay_video` | Apples-to-apples calls — bypass the selector so the call hits exactly the provider/model the plan declared |

## MANDATORY: Read Layer 3 Skills BEFORE Any Generation Call

Before issuing any generation call in a given provider family, read the Layer 3 skill(s) for that family. Skip reading and you will write generic prompts that defeat the purpose of a benchmark.

| Provider family | Layer 3 skills to read first |
|-----------------|------------------------------|
| FLUX (`flux_image`) | `flux-best-practices`, `bfl-api` |
| Video (Runway, Kling, VEO, Seedance, MiniMax, HeyGen) | `ai-video-gen` |
| Grok image/video | `grok-media` |
| LTX video | `ltx2` |
| BFL FLUX async polling, webhooks, regional endpoints | `bfl-api` |

Read each relevant skill once at the start of the stage. Do not re-read between cells of the same provider family.

## Decision Communication Contract — MANDATORY

Per `AGENT_GUIDE.md`, before EACH paid generation call, announce in chat:

```
Calling <tool_name> | provider=<provider> | model=<model> | cell=<cell_id>
Reason: benchmark cell from approved plan; matches plan.cells[<i>]
Cost estimate: $<n>
```

This is non-optional. The user must never have to infer which provider was hit after the fact.

## Process

### 1. Load And Iterate The Plan

Load the `benchmark_plan` artifact. Iterate cells in order. For each cell:

1. Resolve the tool from `cell.tool` against the registry.
2. If the tool is UNAVAILABLE at runtime (e.g., key revoked since plan time), record the cell in `metadata.failed_cells` with `reason: "tool_unavailable"` and continue. Do not silently substitute a different provider — that violates the no-unilateral-substitutions rule.
3. Apply controls from `benchmark_plan.controls` merged with per-cell `cell.params`.
4. Announce the call (see Decision Communication Contract).
5. Execute via `tool.execute(params_dict)`.
6. On success, write the resulting asset to `projects/<project>/assets/<images|video>/<cell_id>.<ext>` and append to `asset_manifest.assets` with full provenance: `id`, `type`, `path`, `source_tool`, `prompt`, `seed`, `model`, `provider`, `cost_usd`, `resolution`, `format`, `generation_summary`. Use the `cell_id` as the asset `id` and as the `scene_id` (the asset_manifest schema requires `scene_id` — for a benchmark, the cell IS the scene).
7. On failure, record in `metadata.failed_cells` with `cell_id`, `provider`, `model`, `error`, and `attempted_at`.

### 2. VEO 3.1 Routing

When a cell targets VEO 3.1:
- Confirm `tool` is the registry-resolved VEO tool (likely `veo_video`). If only `video_selector` is registered, call it with `provider_preference: "veo"` and `model: "veo-3.1"`.
- Read `ai-video-gen` Layer 3 skill specifically for VEO prompt structure (camera grammar, motion phrasing, duration limits) before the first VEO call in the run.
- Announce the VEO call explicitly — VEO is high-cost; the user needs to see it before it fires.

### 3. Use Direct Provider Tools For Benchmark Cells

Even though `image_selector` and `video_selector` are in `tools_available`, prefer the direct provider tool for benchmark cells. The selector adds routing logic that obscures the apples-to-apples comparison. Use selectors only when the plan cell explicitly set `tool: "image_selector"` or `tool: "video_selector"` (e.g., a cell that intentionally measures the selector's routing behavior).

### 4. Cost Reconciliation

After all cells, compute `total_cost_usd` from the sum of `assets[].cost_usd`. Compare against `benchmark_plan.estimated_total_cost_usd` and record the delta in `metadata.cost_delta_usd`. If the delta exceeds 20 percent, surface it to the user.

### 5. Validate And Hand Off

Validate the manifest against `schemas/artifacts/asset_manifest.schema.json`. Confirm every referenced file exists on disk. Checkpoint and proceed.

## Quality Bar

- Every plan cell is accounted for (asset entry OR failed_cells entry).
- Provenance is complete: provider, model, seed (where supported), prompt, cost.
- Layer 3 skill was read before the first call in each provider family.
- Provider/model/reason was announced before every paid call.
- No silent provider substitutions on failure.
- Direct provider tools used for benchmark cells unless plan said otherwise.

## What This Stage Does NOT Do

- Does not edit, composite, or re-render assets — that's downstream pipeline work.
- Does not pick "the winner" — selection is the user's job after reviewing the manifest.
- Does not auto-retry failed cells with a different provider.
