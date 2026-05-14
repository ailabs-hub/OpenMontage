"""Deterministic utilities for agent-native pipeline execution.

These functions are designed to be called by the agent via one-liner
``python -c "..."`` commands. They are pure, stateless, and idempotent
where possible. All path resolution and session management lives here
so the agent skill can focus on creative execution.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Optional

# Add OpenMontage root to path so imports work from any cwd.
_OM_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_OM_ROOT) not in sys.path:
    sys.path.insert(0, str(_OM_ROOT))

from lib.session import PipelineSession  # noqa: E402

# ---------------------------------------------------------------------------
# Stage sequencing — single source of truth for the marketing-creative pipeline
# ---------------------------------------------------------------------------

STAGE_SEQUENCES: dict[str, list[str]] = {
    "raw_input": ["idea_refinement", "creative_concept", "copy", "assets", "review"],
    "idea_pool": ["creative_concept", "copy", "assets", "review"],
}

OPTIONAL_STAGES: dict[str, dict[str, Any]] = {
    "research": {
        "insert_before": "creative_concept",
        "skill": "skills/pipelines/marketing-creative/research-director.md",
    }
}

# Stage → expected output files (relative to campaign_dir).
# idea_refinement writes to the idea pool, not campaign_dir.
STAGE_OUTPUTS: dict[str, list[str]] = {
    "idea_refinement": [],
    "research": ["artifacts/research_brief.json"],
    "creative_concept": ["artifacts/creative_specs.json"],
    "copy": ["artifacts/copy_manifest.json", "copy_variants/"],
    "assets": ["artifacts/asset_manifest.json", "logs/skill_reading_log.json"],
    "review": ["artifacts/final_review.json"],
}

# Stage → input artifact names → relative paths (from campaign_dir).
STAGE_INPUTS: dict[str, dict[str, str]] = {
    "idea_refinement": {},
    "research": {},
    "creative_concept": {},
    "copy": {"creative_specs": "artifacts/creative_specs.json"},
    "assets": {
        "copy_manifest": "artifacts/copy_manifest.json",
        "creative_specs": "artifacts/creative_specs.json",
    },
    "review": {
        "asset_manifest": "artifacts/asset_manifest.json",
        "copy_manifest": "artifacts/copy_manifest.json",
        "creative_specs": "artifacts/creative_specs.json",
    },
}

# Skill paths relative to OpenMontage root.
STAGE_SKILLS: dict[str, str] = {
    "idea_refinement": "skills/pipelines/marketing-creative/idea-refinement-director.md",
    "research": "skills/pipelines/marketing-creative/research-director.md",
    "creative_concept": "skills/pipelines/marketing-creative/creative-director.md",
    "copy": "skills/pipelines/marketing-creative/copy-director.md",
    "assets": "skills/pipelines/marketing-creative/asset-director.md",
    "review": "skills/pipelines/marketing-creative/review-director.md",
}


# ---------------------------------------------------------------------------
# Path resolution
# ---------------------------------------------------------------------------

def get_openmontage_root() -> Path:
    """Return absolute path to OpenMontage repo root."""
    return _OM_ROOT


def load_company_profile(company_slug: str, profile_path: Optional[Path] = None) -> dict[str, Any]:
    """Load company profile JSON."""
    if profile_path is None:
        profile_path = _OM_ROOT.parent / "company_profiles" / f"{company_slug}.json"
    if not profile_path.exists():
        raise FileNotFoundError(f"Company profile not found: {profile_path}")
    with open(profile_path, encoding="utf-8") as f:
        return json.load(f)


def get_project_root(company_slug: str) -> Path:
    """Resolve project root from company profile."""
    profile = load_company_profile(company_slug)
    rel = profile.get("paths", {}).get("project_root", "..")
    return (_OM_ROOT / rel).resolve()


def get_campaign_dir(campaign_id: str, company_slug: str) -> Path:
    """Return absolute path to campaign directory."""
    return get_project_root(company_slug) / "campaigns" / campaign_id


def get_idea_pool_dir(company_slug: str) -> Path:
    """Return absolute path to idea pool directory."""
    profile = load_company_profile(company_slug)
    rel = profile.get("paths", {}).get("idea_pool", "../ideas/")
    return (_OM_ROOT / rel).resolve()


def get_stage_skill_path(stage_id: str) -> Path:
    """Return absolute path to stage director skill."""
    rel = STAGE_SKILLS.get(stage_id, "")
    if not rel:
        raise ValueError(f"Unknown stage: {stage_id}")
    return _OM_ROOT / rel


def resolve_stage_inputs(stage_id: str, campaign_id: str, company_slug: str) -> dict[str, str]:
    """Return resolved absolute input paths for a stage."""
    campaign_dir = get_campaign_dir(campaign_id, company_slug)
    inputs = {}
    for name, rel in STAGE_INPUTS.get(stage_id, {}).items():
        inputs[name] = str(campaign_dir / rel)
    return inputs


def resolve_stage_outputs(stage_id: str, campaign_id: str, company_slug: str) -> list[str]:
    """Return resolved absolute output paths for a stage."""
    campaign_dir = get_campaign_dir(campaign_id, company_slug)
    return [str(campaign_dir / rel) for rel in STAGE_OUTPUTS.get(stage_id, [])]


# ---------------------------------------------------------------------------
# Stage sequencing
# ---------------------------------------------------------------------------

def get_stage_sequence(input_source: str, research: bool = False) -> list[str]:
    """Return ordered stage list based on input source and research flag.

    Args:
        input_source: "raw_input" or "idea_pool".
        research: Whether to include the research stage.

    Returns:
        Ordered list of stage IDs.
    """
    base = list(STAGE_SEQUENCES.get(input_source, STAGE_SEQUENCES["raw_input"]))
    if research:
        insert_point = OPTIONAL_STAGES["research"]["insert_before"]
        if insert_point in base:
            idx = base.index(insert_point)
            base.insert(idx, "research")
    return base


# ---------------------------------------------------------------------------
# Session management
# ---------------------------------------------------------------------------

def init_session(
    campaign_id: str,
    company_slug: str,
    input_source: str,
    research: bool = False,
    num_images: int = 1,
    model: str = "auto",
    input_data: Optional[str] = None,
) -> str:
    """Initialize or resume a pipeline session.

    Args:
        input_data: For raw_input, the actual text, image path, or URL.

    Returns the absolute campaign directory path.
    """
    campaign_dir = get_campaign_dir(campaign_id, company_slug)
    campaign_dir.mkdir(parents=True, exist_ok=True)

    # Pre-create output directories.
    for sub in ["artifacts", "copy_variants", "assets", "logs", "checkpoints"]:
        (campaign_dir / sub).mkdir(parents=True, exist_ok=True)

    session = PipelineSession(campaign_id, campaign_dir, company_slug)
    session.state["input_source"] = input_source
    session.state["research"] = research
    session.state["num_images"] = num_images
    session.state["model"] = model
    if input_data:
        session.state["input_data"] = input_data
    session.set_execution_mode("agent_native")
    session.save()
    return str(campaign_dir)


def get_next_stage(campaign_id: str, company_slug: str) -> Optional[str]:
    """Return the next pending stage, or None if all complete."""
    campaign_dir = get_campaign_dir(campaign_id, company_slug)
    session = PipelineSession(campaign_id, campaign_dir, company_slug)

    input_source = session.state.get("input_source", "raw_input")
    research = session.state.get("research", False)
    sequence = get_stage_sequence(input_source, research)

    for stage in sequence:
        if not session.is_stage_completed(stage):
            return stage
    return None


def mark_stage_complete(
    campaign_id: str,
    company_slug: str,
    stage_id: str,
    artifacts: Optional[dict[str, Any]] = None,
) -> bool:
    """Mark a stage as completed in the session."""
    campaign_dir = get_campaign_dir(campaign_id, company_slug)
    session = PipelineSession(campaign_id, campaign_dir, company_slug)
    session.mark_stage_completed(stage_id, artifacts or {})
    return True


def is_stage_complete(campaign_id: str, company_slug: str, stage_id: str) -> bool:
    """Check if a stage is already completed."""
    campaign_dir = get_campaign_dir(campaign_id, company_slug)
    session = PipelineSession(campaign_id, campaign_dir, company_slug)
    return session.is_stage_completed(stage_id)


def get_session_status(campaign_id: str, company_slug: str) -> dict[str, Any]:
    """Return full session state as a dict."""
    campaign_dir = get_campaign_dir(campaign_id, company_slug)
    session = PipelineSession(campaign_id, campaign_dir, company_slug)
    return session.to_dict()


# ---------------------------------------------------------------------------
# Copy variant parsing helpers
# ---------------------------------------------------------------------------

def _parse_copy_variant_md(md_path: Path) -> dict[str, str]:
    """Parse headline, body, cta from a copy variant markdown file.

    Expected format:
        ## Headline
        "The headline text"

        ## Body Copy
        The body text...

        ## CTA
        "The CTA text"
    """
    if not md_path.exists():
        return {"headline": "", "body": "", "cta": ""}

    text = md_path.read_text(encoding="utf-8")
    result: dict[str, str] = {"headline": "", "body": "", "cta": ""}

    # Simple section parser: find ## Section Name and capture until next ## or EOF.
    import re
    for key, label in [("headline", "Headline"), ("body", "Body Copy"), ("cta", "CTA")]:
        pattern = rf"##\s*{label}\s*\n+(.*?)(?=\n##\s|\Z)"
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            result[key] = match.group(1).strip().strip('"').strip("'")

    return result


def _extract_variants_from_manifest(
    manifest_creative: dict[str, Any],
    campaign_dir: Path,
    spec: dict[str, Any],
) -> list[dict[str, Any]]:
    """Extract flat variant list from a manifest creative.

    Handles BOTH formats:
      - Format A (path-based): creatives[].angles.{angle}.{lang} = "path.md"
      - Format B (inline):     creatives[].variants[] = {id, angle, lang, headline, body, cta}
    """
    variants: list[dict[str, Any]] = []

    # Format B: inline variants array.
    if "variants" in manifest_creative:
        for v in manifest_creative["variants"]:
            variants.append({
                "id": v.get("id", ""),
                "angle": v.get("angle", ""),
                "language": v.get("language", ""),
                "headline": v.get("headline", ""),
                "body": v.get("body", ""),
                "cta": v.get("cta", ""),
            })
        return variants

    # Format A: path-based angles dict.
    angles = manifest_creative.get("angles", {})
    for angle, langs in angles.items():
        if not isinstance(langs, dict):
            continue
        for lang, rel_path in langs.items():
            md_path = campaign_dir / rel_path if isinstance(rel_path, str) else campaign_dir
            parsed = _parse_copy_variant_md(md_path)
            variants.append({
                "id": f"{manifest_creative.get('creative_id', 'unknown')}-{angle}-{lang}",
                "angle": angle,
                "language": lang,
                "headline": parsed["headline"],
                "body": parsed["body"],
                "cta": parsed["cta"],
            })

    return variants


# ---------------------------------------------------------------------------
# Variant selection for intelligent image generation
# ---------------------------------------------------------------------------

def select_variants_for_generation(
    campaign_id: str,
    company_slug: str,
    num_images: Optional[int] = None,
) -> list[dict[str, Any]]:
    """Score and rank all copy variants, return top N for image generation.

    Uses company profile learnings, primary language, and creative hook strength
    to intelligently select which variants get images. Ensures angle diversity
    across the selected set.

    Handles both inline 'variants' arrays and path-based 'angles' dicts in the
    copy manifest.

    Args:
        num_images: Total image budget. Defaults to session's num_images.

    Returns:
        List of selected variant dicts with rank, score, and selection_reason.
    """
    campaign_dir = get_campaign_dir(campaign_id, company_slug)
    session = PipelineSession(campaign_id, campaign_dir, company_slug)

    if num_images is None:
        num_images = session.state.get("num_images", 1)

    profile = load_company_profile(company_slug)
    learnings = profile.get("pipeline_learnings", {})
    best_angles = learnings.get("best_performing_angles", ["pain_point", "direct_benefit", "emotional"])
    primary_lang = profile.get("primary_audience", {}).get("primary_language", "English")

    # Load creative specs and copy manifest.
    creative_specs_path = campaign_dir / "artifacts" / "creative_specs.json"
    copy_manifest_path = campaign_dir / "artifacts" / "copy_manifest.json"

    if not creative_specs_path.exists() or not copy_manifest_path.exists():
        return []

    with open(creative_specs_path, encoding="utf-8-sig") as f:
        creative_specs = json.load(f)
    with open(copy_manifest_path, encoding="utf-8-sig") as f:
        copy_manifest = json.load(f)

    creatives = creative_specs.get("creatives", [])
    manifest_creatives = copy_manifest.get("creatives", [])

    # Build lookup tables.
    spec_by_id = {c["id"]: c for c in creatives if "id" in c}

    # Score every variant.
    scored: list[dict[str, Any]] = []
    for mc in manifest_creatives:
        creative_id = mc.get("id", mc.get("creative_id", ""))
        spec = spec_by_id.get(creative_id, {})
        hook_strength = spec.get("hook_strength", 3)

        variants = _extract_variants_from_manifest(mc, campaign_dir, spec)
        for variant in variants:
            score = 0
            reasons: list[str] = []

            angle = variant.get("angle", "")
            lang = variant.get("language", "")

            # Angle performance (up to 15 points).
            if angle in best_angles:
                rank = best_angles.index(angle)
                angle_score = 15 - (rank * 5)
                score += max(angle_score, 0)
                reasons.append(f"{angle} is #{rank+1} best-performing angle")

            # Language priority (up to 10 points).
            if lang.lower() == primary_lang.lower():
                score += 10
                reasons.append("primary language")
            elif lang.lower() in [primary_lang.lower(), "hinglish"]:
                score += 5
                reasons.append("secondary language match")

            # Hook strength (up to 5 points).
            score += hook_strength
            if hook_strength >= 4:
                reasons.append("strong hook")

            scored.append({
                "creative_id": creative_id,
                "variant_id": variant.get("id", ""),
                "angle": angle,
                "language": lang,
                "headline": variant.get("headline", ""),
                "body": variant.get("body", ""),
                "cta": variant.get("cta", ""),
                "score": score,
                "selection_reason": "; ".join(reasons) if reasons else "baseline",
                "creative_spec": spec,
            })

    # Sort by score descending.
    scored.sort(key=lambda x: x["score"], reverse=True)

    # Ensure angle diversity: cap same-angle selections.
    angle_counts: dict[str, int] = {}
    diversified: list[dict[str, Any]] = []
    max_per_angle = max(2, num_images // 2)

    for v in scored:
        angle = v["angle"]
        if angle_counts.get(angle, 0) < max_per_angle:
            diversified.append(v)
            angle_counts[angle] = angle_counts.get(angle, 0) + 1
        if len(diversified) >= num_images:
            break

    # If diversity culling left us short, fill from remaining high scorers.
    if len(diversified) < num_images:
        for v in scored:
            if v not in diversified:
                diversified.append(v)
            if len(diversified) >= num_images:
                break

    # Add rank.
    for i, v in enumerate(diversified, 1):
        v["rank"] = i

    return diversified[:num_images]


# ---------------------------------------------------------------------------
# Locked brief builder
# ---------------------------------------------------------------------------

def build_locked_brief(campaign_id: str, company_slug: str, idea: dict[str, Any]) -> dict[str, Any]:
    """Build the locked brief dict passed to every stage."""
    profile = load_company_profile(company_slug)
    audience = profile.get("primary_audience", {})
    return {
        "idea": idea.get("title", idea.get("id", "untitled")),
        "topic": idea.get("topic", idea.get("core_concept", "")),
        "platform": idea.get("platform", "instagram_feed"),
        "language": idea.get("language", audience.get("primary_language", "English")),
        "audience": (
            f"{audience.get('age_range', '25-45')}, "
            f"{audience.get('location', 'India')}, "
            f"interests: {', '.join(audience.get('interests', ['astrology'])[:3])}"
        ),
        "budget_cap": 5.0,
        "special_instructions": idea.get("special_instructions", ""),
        "source": idea.get("source", "conversation"),
    }


# ---------------------------------------------------------------------------
# CLI helpers (for ``python -c "..."`` one-liners)
# ---------------------------------------------------------------------------

def _cli_print(data: Any) -> None:
    """Print JSON to stdout for CLI consumption."""
    text = json.dumps(data, indent=2, ensure_ascii=False)
    try:
        print(text)
    except UnicodeEncodeError:
        # Windows console fallback.
        import sys
        sys.stdout.buffer.write(text.encode("utf-8", "replace"))
        sys.stdout.buffer.write(b"\n")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Agent-native pipeline utilities")
    sub = parser.add_subparsers(dest="command")

    # init
    p_init = sub.add_parser("init", help="Initialize session")
    p_init.add_argument("--campaign-id", required=True)
    p_init.add_argument("--company", required=True)
    p_init.add_argument("--input-source", default="raw_input")
    p_init.add_argument("--input-data", default=None, help="Raw input: text, image path, or URL")
    p_init.add_argument("--research", action="store_true")
    p_init.add_argument("--num-images", type=int, default=1)
    p_init.add_argument("--model", default="auto")

    # next
    p_next = sub.add_parser("next", help="Get next pending stage")
    p_next.add_argument("--campaign-id", required=True)
    p_next.add_argument("--company", required=True)

    # complete
    p_complete = sub.add_parser("complete", help="Mark stage complete")
    p_complete.add_argument("--campaign-id", required=True)
    p_complete.add_argument("--company", required=True)
    p_complete.add_argument("--stage", required=True)

    # status
    p_status = sub.add_parser("status", help="Get session status")
    p_status.add_argument("--campaign-id", required=True)
    p_status.add_argument("--company", required=True)

    # sequence
    p_seq = sub.add_parser("sequence", help="Get stage sequence")
    p_seq.add_argument("--input-source", default="raw_input")
    p_seq.add_argument("--research", action="store_true")

    # config (session config inspection)
    p_config = sub.add_parser("config", help="Get session config (num_images, model, etc.)")
    p_config.add_argument("--campaign-id", required=True)
    p_config.add_argument("--company", required=True)

    # select (variant selection for assets stage)
    p_select = sub.add_parser("select", help="Select top copy variants for image generation")
    p_select.add_argument("--campaign-id", required=True)
    p_select.add_argument("--company", required=True)
    p_select.add_argument("--num-images", type=int, default=None, help="Override session num_images")

    args = parser.parse_args()

    if args.command == "init":
        result = init_session(
            args.campaign_id,
            args.company,
            args.input_source,
            args.research,
            args.num_images,
            args.model,
            args.input_data,
        )
        _cli_print({"campaign_dir": result, "status": "initialized"})

    elif args.command == "next":
        stage = get_next_stage(args.campaign_id, args.company)
        _cli_print({"next_stage": stage, "complete": stage is None})

    elif args.command == "complete":
        mark_stage_complete(args.campaign_id, args.company, args.stage)
        _cli_print({"stage": args.stage, "status": "completed"})

    elif args.command == "status":
        _cli_print(get_session_status(args.campaign_id, args.company))

    elif args.command == "config":
        status = get_session_status(args.campaign_id, args.company)
        _cli_print({
            "num_images": status.get("num_images", 1),
            "model": status.get("model", "auto"),
            "input_source": status.get("input_source", "raw_input"),
            "research": status.get("research", False),
            "input_data": status.get("input_data", ""),
        })

    elif args.command == "sequence":
        _cli_print({"sequence": get_stage_sequence(args.input_source, args.research)})

    elif args.command == "select":
        selected = select_variants_for_generation(
            args.campaign_id, args.company, args.num_images
        )
        _cli_print({
            "selected_count": len(selected),
            "total_budget": args.num_images,
            "variants": selected,
        })

    else:
        parser.print_help()
