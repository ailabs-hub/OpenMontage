# Plan Director - Provider Benchmark Pipeline

## When To Use

This stage produces the `benchmark_plan` artifact: the full matrix of (prompt x provider x variation) cells to execute, with controlled parameters and per-cell cost estimates. It is the contract that the assets stage will execute against, one cell at a time.

This pipeline is for **capability evaluation**, not production delivery. Be explicit with the user: outputs are reference assets for comparison, not shippable creative.

## Prerequisites

| Layer | Resource | Purpose |
|-------|----------|---------|
| Schema | `schemas/artifacts/benchmark_plan.schema.json` | Artifact validation |
| Registry | `tools.tool_registry.registry.provider_menu()` | Source of truth for which providers are AVAILABLE |
| Pipeline manifest | `pipeline_defs/provider-benchmark.yaml` | Stage contract and tools_available |

## Process

### 1. Confirm The Benchmark Objective

Ask the user (or read from prior turn) what is being measured. Examples:
- "Cinematic still quality across paid image providers at 1024x1024."
- "5-second sci-fi B-roll across VEO, Kling, Runway at 720p."
- "Cost-per-acceptable-output across stock vs generated for product shots."

Record this in `benchmark_plan.objective`.

### 2. Lock The Controls

Declare the variables held constant across cells. Typical controls:
- `seed` (where the provider supports it)
- `aspect_ratio` (e.g., "1:1", "16:9", "9:16")
- `resolution` (e.g., "1024x1024", "1920x1080")
- `negative_prompt` (image only)

Cells that cannot honor a control (e.g., a provider that ignores seed) must record that in their `params` block so the assets stage does not flag it as a deviation.

### 3. Define The Prompts

Write 1-N prompts in the `prompts[]` block. Each prompt is **the same text** sent to every provider in its row. Do NOT pre-rewrite the prompt for each provider in this stage — provider-specific prompt adaptation happens in the assets stage, guided by Layer 3 skills (`flux-best-practices`, `ai-video-gen`, etc.). The point of a benchmark is that the input is held constant.

Each prompt must declare its `modality` (`image` or `video`).

### 4. Pick The Provider Set

Read `registry.provider_menu()` (mandatory preflight per AGENT_GUIDE.md) and select providers that are AVAILABLE. Pick a meaningful spread — not all variants of the same model family, not only one tier. A good 4-cell image benchmark covers: one diffusion API (FLUX), one large-model API (Imagen or OpenAI), one stylized API (Recraft or Grok), one stock provider (Pexels) for the cost floor.

For each (prompt, provider) pair, emit one cell per variation_index. Most benchmarks want 1-2 variations per cell to keep cost bounded.

### 5. Estimate Cost

Populate `estimated_cost_usd` per cell from registry/Layer-3 cost data. Sum into `estimated_total_cost_usd`. If the total exceeds the user's stated budget, surface this immediately and propose a trimmed plan.

### 6. Address VEO Routing Explicitly

The user has stated VEO 3.1 is a future target. If the plan includes video generation:
- list the exact tool name from the registry that routes to VEO 3.1 (likely `veo_video` or via `video_selector` with provider preference),
- include at least one VEO cell unless the user has explicitly excluded it,
- record `model: "veo-3.1"` (or the registry-confirmed exact ID) in the cell's `params`.

### 7. Validate And Hand Off

Validate the plan against `schemas/artifacts/benchmark_plan.schema.json`. Save to the project workspace. Present to user with:
- objective,
- controls,
- prompt list,
- provider matrix,
- per-cell and total cost,
- which providers are unavailable and why those cells were dropped.

This stage requires human approval before the assets stage runs.

## Quality Bar

- Plan is reproducible: a second agent reading this artifact would issue identical calls.
- No provider was added or dropped without recording why.
- Cost is honest and itemized.
- Same prompt text per row across providers (no per-provider rewriting at plan time).
- VEO routing decision is explicit when video is in scope.
