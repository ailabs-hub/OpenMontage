"""Subagent dispatcher: maps pipeline stages to subagent types and builds prompts.

Centralises the subagent prompt templates that previously lived scattered across
SKILL.md. Each stage gets a precisely typed subagent with resolved absolute file
paths, steering rules, and expected output files.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


# Stage → subagent_type mapping.
# These are the Claude Code subagent types defined in the orchestrator skill.
STAGE_TO_SUBAGENT: dict[str, str] = {
    "idea_refinement": "general-purpose",
    "research": "general-purpose",
    "creative_concept": "ad-creative-strategist",
    "copy": "copy-variant-creator",
    "assets": "content-generation-executor-kimi",
    "review": "general-purpose",
}

# Stage director skill paths (relative to OpenMontage root).
STAGE_SKILL_PATHS: dict[str, str] = {
    "idea_refinement": "skills/pipelines/marketing-creative/idea-refinement-director.md",
    "research": "skills/pipelines/marketing-creative/research-director.md",
    "creative_concept": "skills/pipelines/marketing-creative/creative-director.md",
    "copy": "skills/pipelines/marketing-creative/copy-director.md",
    "assets": "skills/pipelines/marketing-creative/asset-director.md",
    "review": "skills/pipelines/marketing-creative/review-director.md",
}

# Expected output files per stage (relative to campaign_dir).
STAGE_OUTPUTS: dict[str, list[str]] = {
    "idea_refinement": [],  # Writes to idea pool, not campaign dir.
    "research": ["artifacts/research_brief.json"],
    "creative_concept": ["artifacts/creative_specs.json"],
    "copy": [
        "artifacts/copy_manifest.json",
        "copy_variants/",
    ],
    "assets": [
        "artifacts/asset_manifest.json",
        "logs/skill_reading_log.json",
    ],
    "review": ["artifacts/final_review.json"],
}

# Human approval required per stage (from pipeline manifest).
STAGE_HUMAN_APPROVAL: dict[str, bool] = {
    "idea_refinement": False,
    "research": True,
    "creative_concept": True,
    "copy": True,
    "assets": False,
    "review": True,
}


def get_subagent_type(stage: str) -> str:
    return STAGE_TO_SUBAGENT[stage]


def build_execute_request(
    stage: str,
    campaign_dir: Path,
    input_files: dict[str, str],
    locked_brief: dict[str, Any],
    openmontage_root: Path,
    generation_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a structured execute request for agent-native self-execution mode.

    The agent reads the skill file and executes the stage itself (no subagents).
    """
    skill_path = openmontage_root / STAGE_SKILL_PATHS[stage]
    output_files = STAGE_OUTPUTS[stage]

    # Resolve input files to absolute paths.
    abs_inputs = {
        name: str(campaign_dir / rel) for name, rel in input_files.items()
    }

    # Resolve output files to absolute paths.
    abs_outputs = [str(campaign_dir / rel) for rel in output_files]

    # Build generation config block for assets stage.
    gen_config_block = ""
    if stage == "assets" and generation_config:
        gen_config_block = _format_generation_config(generation_config)

    # Build tool invocation block for assets stage.
    tool_commands = ""
    if stage == "assets":
        tool_commands = _build_image_tool_commands(
            generation_config or {}, campaign_dir, openmontage_root
        )

    # Build the full execute instructions.
    instructions = _build_execute_instructions(
        stage=stage,
        locked_brief=locked_brief,
        skill_path=str(skill_path),
        input_files=abs_inputs,
        output_files=abs_outputs,
        campaign_dir=str(campaign_dir),
        generation_config_block=gen_config_block,
        tool_commands=tool_commands,
        openmontage_root=str(openmontage_root),
    )

    return {
        "action": "execute_stage",
        "stage": stage,
        "description": f"Marketing pipeline: {stage} stage (self-execution)",
        "instructions": instructions,
        "skill_path": str(skill_path),
        "expected_outputs": output_files,
        "human_approval_required": STAGE_HUMAN_APPROVAL[stage],
    }


def build_spawn_request(
    stage: str,
    campaign_dir: Path,
    input_files: dict[str, str],
    locked_brief: dict[str, Any],
    openmontage_root: Path,
    generation_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a structured spawn request for the outer Claude Code to execute.

    Args:
        stage: Pipeline stage name.
        campaign_dir: Absolute path to the campaign directory.
        input_files: Mapping of artifact name → relative file path (from campaign_dir).
        locked_brief: The locked brief dict (idea, platform, language, etc.).
        openmontage_root: Absolute path to the OpenMontage repo root.
        generation_config: Optional dict with num_images and model for assets stage.

    Returns:
        A dict with ``action: "spawn_subagent"`` plus all context needed for
        Claude Code to spawn the correct subagent.
    """
    subagent_type = get_subagent_type(stage)
    skill_path = openmontage_root / STAGE_SKILL_PATHS[stage]
    output_files = STAGE_OUTPUTS[stage]

    # Resolve input files to absolute paths.
    abs_inputs = {
        name: str(campaign_dir / rel) for name, rel in input_files.items()
    }

    # Resolve output files to absolute paths.
    abs_outputs = [str(campaign_dir / rel) for rel in output_files]

    # Build generation config block for assets stage.
    gen_config_block = ""
    if stage == "assets" and generation_config:
        gen_config_block = _format_generation_config(generation_config)

    # Build the full subagent prompt.
    prompt = _build_subagent_prompt(
        stage=stage,
        locked_brief=locked_brief,
        skill_path=str(skill_path),
        input_files=abs_inputs,
        output_files=abs_outputs,
        campaign_dir=str(campaign_dir),
        generation_config_block=gen_config_block,
    )

    return {
        "action": "spawn_subagent",
        "stage": stage,
        "subagent_type": subagent_type,
        "description": f"Marketing pipeline: {stage} stage",
        "prompt": prompt,
        "expected_outputs": output_files,
        "human_approval_required": STAGE_HUMAN_APPROVAL[stage],
    }


def _build_subagent_prompt(
    stage: str,
    locked_brief: dict[str, Any],
    skill_path: str,
    input_files: dict[str, str],
    output_files: list[str],
    campaign_dir: str,
    generation_config_block: str = "",
) -> str:
    """Construct the full prompt sent to a subagent."""

    role_titles = {
        "idea_refinement": "Idea Refinement Director",
        "research": "Research Director",
        "creative_concept": "Creative Director",
        "copy": "Copy Director",
        "assets": "Asset Director",
        "review": "Review Director",
    }

    # Build input files block.
    input_block = "\n".join(
        f"- {name}: {path}" for name, path in input_files.items()
    ) or "- (none — this is the first stage)"

    # Build output files block.
    output_block = "\n".join(f"- {path}" for path in output_files)

    # Stage-specific steering rules.
    steering = _get_steering_rules(stage)

    # File scope for all stages (prevents subagents from exploring irrelevant dirs).
    file_scope = _get_file_scope(stage, skill_path, campaign_dir)

    # Mandatory skill reading protocol for assets stage.
    skill_reading_protocol = ""
    if stage == "assets":
        skill_reading_protocol = _get_skill_reading_protocol()

    prompt = f"""You are the {role_titles[stage]} for the marketing-creative pipeline.

LOCKED BRIEF:
-------------
Idea: {locked_brief.get("idea", "N/A")}
Topic: {locked_brief.get("topic", "N/A")}
Platform: {locked_brief.get("platform", "N/A")}
Language: {locked_brief.get("language", "N/A")}
Audience: {locked_brief.get("audience", "N/A")}
Budget Cap: ${locked_brief.get("budget_cap", 5.0)}
Special Instructions: {locked_brief.get("special_instructions", "none")}

INPUT ARTIFACTS (read from these absolute paths):
{input_block}

YOUR TASK:
1. Read the stage director skill at: {skill_path}
2. Execute the "{stage}" stage per the skill's instructions.
3. Produce ALL required output artifacts.

OUTPUT ARTIFACTS (write to these absolute paths):
{output_block}
{generation_config_block}

CRITICAL RULES:
- Read input files from the paths listed above. Do NOT assume they are in the current directory.
- Write output files to the paths listed above. Do NOT write files anywhere else.
- Every output file must exist on disk before you finish.
- If a file is missing, the stage is NOT complete.
{skill_reading_protocol}
{file_scope}

STEERING RULES:
{steering}

CAMPAIGN DIRECTORY:
{campaign_dir}

Return a JSON summary of what you produced, including file paths and any issues encountered.
"""
    return prompt


def _get_steering_rules(stage: str) -> str:
    """Stage-specific steering rules extracted from the orchestrator skill."""

    rules: dict[str, str] = {
        "idea_refinement": (
            "- Convert the user's RAW INPUT into a structured idea file in the company's idea pool.\n"
            "- Use the company profile's defaults (platform, audience, language) when not specified.\n"
            "- For IMAGE input: use vision to extract headline, body, CTA, visual style, color palette, platform, emotional angle. Then reimagine for the target company.\n"
            "- For URL input: fetch the page, extract ad/landing elements, then reimagine for the target company.\n"
            "- Output MUST be a properly formatted idea file written to the idea pool directory.\n"
            "- Return the idea_id you used in your JSON summary."
        ),
        "research": (
            "- The user has ALREADY selected a single idea. Your job is to RESEARCH that idea, not generate new ones.\n"
            "- Find REAL signals from REAL platforms (YouTube, Reddit, news, Twitter/X).\n"
            "- At least 3 distinct signals with source URLs.\n"
            "- Competitor entries must have actual names and specific tactics.\n"
            "- Do NOT invent signals or sources."
        ),
        "creative_concept": (
            "- Each creative must have a DISTINCT angle/hook (not 6 versions of the same idea).\n"
            "- visual_direction describes MOOD, not UI wireframes.\n"
            "- Budget guidance must be specific (Rs./day, not vague).\n"
            "- Format and placement must match the target platform.\n"
            "- If no research_brief is available (research was skipped), use company_profile.primary_audience.pain_points "
            "and company_profile.pipeline_learnings.best_practices as your signal source. "
            "Do NOT invent signals or competitors."
        ),
        "copy": (
            "- Select 2-3 BEST angles per creative based on the hook.\n"
            "- pain_point and direct_benefit are usually the strongest.\n"
            "- Add emotional if the hook is feeling-driven, comparison if there's a clear alternative, offer_led if price is the differentiator.\n"
            "- Generate ONLY the angles that best serve THIS creative's hook. Do NOT generate all 5 by default.\n"
            "- Generate copy ONLY in the language specified in the locked brief.\n"
            "- If locked language is Hinglish: use natural code-switching, not forced translation.\n"
            "- ONE headline per variant. Do NOT provide multiple options.\n"
            "- Body copy: 1-2 short punchy sentences MAX (ad caption text, not a paragraph).\n"
            "- NO visual direction in copy variants. Visual decisions are the asset stage's job.\n"
            "- WRITE INDIVIDUAL FILES: one .md file per angle per language to copy_variants/ (campaign root, NOT artifacts/).\n"
            "- VERIFY FILE COUNT: count actual .md files in copy_variants/ before finishing."
        ),
        "assets": (
            "- MANDATORY SKILL STACK: read skills/meta/image-prompt-from-copy-variant.md BEFORE writing any prompt.\n"
            "- VISUAL BRIEF PATTERN + CAMERA/TECHNICAL: every prompt must include emotional contrast, visual anchors, text overlays in locked language, color palette with hex codes, named lighting pattern, and Camera/Technical layer (shot type, lens, aperture, film stock).\n"
            "- LANGUAGE PROPAGATION: copy variant language → image text MUST be same language.\n"
            "- TEXT CONTENT: image text overlays MUST use the EXACT headline from the selected copy variant. Not generic text in the same language.\n"
            "- NO CHECKLISTS in generated images.\n"
            "- NO SPECIFIC FONTS requested.\n"
            "- Write skill_reading_log.json to logs/ with all skills documented.\n"
            "- Save asset manifest, image, prompt log, and prompt markdown to their designated paths."
        ),
        "review": (
            "- Verify language propagation: image text language MUST match copy variant language.\n"
            "- Verify assets match creative spec emotional direction.\n"
            "- Verify no flat infographic/checklist images snuck through.\n"
            "- Define A/B test plan with at least 2 variant pairs.\n"
            "- Budget summary must be accurate."
        ),
    }

    return rules.get(stage, "- Follow the stage director skill exactly.")


def _get_file_scope(stage: str, skill_path: str, campaign_dir: str) -> str:
    """Restrict subagent file exploration to relevant paths only."""
    return f"""FILE SCOPE:
You are running inside the OpenMontage repo but you MUST NOT explore beyond these paths:
- The stage director skill at: {skill_path}
- The campaign directory at: {campaign_dir}
- The input files listed above
- The company profile (if referenced by the skill)
- The idea pool directory (if referenced by the skill)

DO NOT read files outside this scope. DO NOT explore other directories.
DO NOT read AGENT_GUIDE.md, CLAUDE.md, or any other guide files.
"""


def _get_skill_reading_protocol() -> str:
    """Mandatory skill reading protocol for the assets stage."""
    return """MANDATORY SKILL READING PROTOCOL:
Before generating ANY image prompt, you MUST complete these steps IN ORDER:
1. Read skills/meta/image-prompt-from-copy-variant.md
2. Read skills/pipelines/marketing-creative/asset-director.md
3. Read .agents/skills/flux-best-practices/rules/t2i-prompting.md
4. Read .agents/skills/flux-best-practices/rules/typography-text.md
5. Read .agents/skills/flux-best-practices/rules/model-selection-guide.md

After reading EACH skill, append an entry to logs/skill_reading_log.json.
The skill_reading_log.json file is a MANDATORY output. If missing, the stage has FAILED.
Do NOT skip any skill. Do NOT claim you read them without actually doing so.
"""


def _build_execute_instructions(
    stage: str,
    locked_brief: dict[str, Any],
    skill_path: str,
    input_files: dict[str, str],
    output_files: list[str],
    campaign_dir: str,
    generation_config_block: str = "",
    tool_commands: str = "",
    openmontage_root: str = "",
) -> str:
    """Construct the full instructions sent to the agent in self-execution mode."""

    role_titles = {
        "idea_refinement": "Idea Refinement Director",
        "research": "Research Director",
        "creative_concept": "Creative Director",
        "copy": "Copy Director",
        "assets": "Asset Director",
        "review": "Review Director",
    }

    # Build input files block.
    input_block = "\n".join(
        f"- {name}: {path}" for name, path in input_files.items()
    ) or "- (none -- this is the first stage)"

    # Build output files block.
    output_block = "\n".join(f"- {path}" for path in output_files)

    # Stage-specific steering rules.
    steering = _get_steering_rules(stage)

    # File scope for all stages.
    file_scope = _get_file_scope(stage, skill_path, campaign_dir)

    # Mandatory skill reading protocol for assets stage.
    skill_reading_protocol = ""
    if stage == "assets":
        skill_reading_protocol = _get_skill_reading_protocol()

    # Validate skill paths exist.
    skill_validation = _validate_skill_paths(skill_path, openmontage_root)

    instructions = f"""You are the {role_titles[stage]} for the marketing-creative pipeline.

LOCKED BRIEF:
-------------
Idea: {locked_brief.get("idea", "N/A")}
Topic: {locked_brief.get("topic", "N/A")}
Platform: {locked_brief.get("platform", "N/A")}
Language: {locked_brief.get("language", "N/A")}
Audience: {locked_brief.get("audience", "N/A")}
Budget Cap: ${locked_brief.get("budget_cap", 5.0)}
Special Instructions: {locked_brief.get("special_instructions", "none")}

INPUT ARTIFACTS (read from these absolute paths):
{input_block}

YOUR TASK:
1. Read the stage director skill at: {skill_path}
2. Execute the "{stage}" stage per the skill's instructions.
3. Produce ALL required output artifacts.

OUTPUT ARTIFACTS (write to these absolute paths):
{output_block}
{generation_config_block}

CRITICAL RULES:
- Read input files from the paths listed above. Do NOT assume they are in the current directory.
- Write output files to the paths listed above. Do NOT write files anywhere else.
- Every output file must exist on disk before you finish.
- If a file is missing, the stage is NOT complete.
{skill_reading_protocol}
{skill_validation}
{file_scope}

STEERING RULES:
{steering}

{tool_commands}

CAMPAIGN DIRECTORY:
{campaign_dir}

Return a JSON summary of what you produced, including file paths and any issues encountered.
"""
    return instructions


def _build_image_tool_commands(
    generation_config: dict[str, Any],
    campaign_dir: Path,
    openmontage_root: Path,
) -> str:
    """Build Python tool invocation examples for the assets stage."""
    num_images = generation_config.get("num_images", 1)
    model = generation_config.get("model", "auto")

    model_note = "auto-routes to best provider" if model == "auto" else f"uses '{model}' directly"

    return f"""IMAGE GENERATION TOOLS (Python-based, runs in this environment):

You do NOT need Claude Code built-in tools. OpenMontage has Python tools that call image generation APIs.

Step 1: Run preflight to discover available providers:
```bash
cd {openmontage_root}
python -c "from tools.tool_registry import registry; registry.discover(); import json; print(json.dumps(registry.provider_menu_summary(), indent=2))"
```

Step 2: Generate image using image_selector (auto-routes to best available provider):
```python
from tools.tool_registry import registry
registry.discover()

selector = registry.get("image_selector")
result = selector.execute({{
    "prompt": "[your optimized prompt here -- MUST include Camera/Technical layer]",
    "width": 1024,
    "height": 1024,  # 1280 for 4:5, 1792 for 9:16
    "output_path": "{campaign_dir}/assets/cr01_pain_point_english.png",
    "preferred_provider": "{model}",  # {model_note}
}})
print(f"Success: {{result.success}}")
print(f"Output: {{result.data.get('output')}}")
print(f"Cost: ${{result.cost_usd}}")
```

Step 3: Alternative -- use a concrete provider directly (e.g., FLUX):
```python
from tools.tool_registry import registry
registry.discover()

flux = registry.get("flux_image")
result = flux.execute({{
    "prompt": "[your optimized prompt]",
    "width": 1024,
    "height": 1024,
    "output_path": "{campaign_dir}/assets/cr01_pain_point_english.png",
    "model": "flux-pro/v1.1",
}})
print(f"Success: {{result.success}}, Output: {{result.data.get('output')}}")
```

IMPORTANT: API keys are loaded automatically from the .env file in the OpenMontage root.
"""


def _validate_skill_paths(skill_path: str, openmontage_root: str) -> str:
    """Check that referenced skill paths exist. Warn if missing."""
    from pathlib import Path

    warnings = []
    om_root = Path(openmontage_root)

    # Check the main skill path.
    if not Path(skill_path).exists():
        warnings.append(f"WARNING: Skill file not found: {skill_path}")

    # Check flux best practices skills.
    flux_skills_dir = om_root / ".agents" / "skills" / "flux-best-practices" / "rules"
    if not flux_skills_dir.exists():
        warnings.append(
            f"WARNING: FLUX best practices skills not found at {flux_skills_dir}. "
            "Image generation guidance will be limited."
        )

    if warnings:
        return "\n".join("- " + w for w in warnings) + "\n"
    return ""


def _format_generation_config(generation_config: dict[str, Any]) -> str:
    """Format generation config block for assets stage prompt."""
    num_images = generation_config.get("num_images", 1)
    model = generation_config.get("model", "auto")
    model_note = "use image_selector to pick the best provider" if model == "auto" else f"use the '{model}' provider directly"
    return f"""GENERATION CONFIG:
- Images per creative: {num_images}
- Model: {model} ({model_note})
"""
