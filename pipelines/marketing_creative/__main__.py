"""CLI entry point for the marketing-creative pipeline orchestrator.

Usage:
    # From raw text
    python -m pipelines.marketing_creative \
        --campaign-id noise_vs_clarity \
        --company 91astrology \
        --input-text "A campaign about clarity vs noise"

    # From image
    python -m pipelines.marketing_creative \
        --campaign-id competitor_adapt \
        --company 91astrology \
        --input-image /path/to/screenshot.png

    # From URL
    python -m pipelines.marketing_creative \
        --campaign-id landing_adapt \
        --company 91astrology \
        --input-url https://example.com/landing

    # From idea pool
    python -m pipelines.marketing_creative \
        --campaign-id noise_vs_clarity \
        --company 91astrology \
        --idea-id idea-03

    # With research enabled
    python -m pipelines.marketing_creative ... --research

    # Resume after subagent completed
    python -m pipelines.marketing_creative \
        --campaign-id noise_vs_clarity \
        --resume \
        --subagent-result-file /tmp/subagent_result.json

Output is a JSON action dict printed to stdout for Claude Code to interpret.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from lib.idea_store import IdeaStore

from .orchestrator import MarketingCreativeOrchestrator


def _auto_detect_root() -> Path:
    """Auto-detect OpenMontage root from this file's location."""
    return Path(__file__).resolve().parent.parent.parent


def _load_company_profile(company_slug: str, om_root: Path) -> dict:
    """Load company profile from the parent directory."""
    profile_path = om_root.parent / "company_profiles" / f"{company_slug}.json"
    if not profile_path.exists():
        raise FileNotFoundError(f"Company profile not found: {profile_path}")
    with open(profile_path, encoding="utf-8") as f:
        return json.load(f)


def _load_idea_from_pool(idea_id: str, company_slug: str, om_root: Path) -> dict:
    """Load an idea from the company idea pool using IdeaStore."""
    profile = _load_company_profile(company_slug, om_root)
    idea_pool_rel = profile.get("paths", {}).get("idea_pool", "../ideas/")
    idea_pool_dir = (om_root / idea_pool_rel).resolve()

    store = IdeaStore(idea_pool_dir)
    idea = store.load_idea(idea_id)

    return {
        "id": idea.id,
        "title": idea.title,
        "topic": idea.core_concept or idea.body[:200],
        "body": idea.body,
        "source": "idea_pool",
        "platform": idea.target_platform or "",
        "language": idea.primary_language or "",
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Marketing-creative pipeline orchestrator",
    )
    parser.add_argument(
        "--campaign-id",
        required=True,
        help="Unique campaign identifier (e.g., noise_vs_clarity)",
    )
    parser.add_argument(
        "--company",
        default="91astrology",
        help="Company slug (default: 91astrology)",
    )

    # Input sources (mutually exclusive)
    input_group = parser.add_mutually_exclusive_group()
    input_group.add_argument(
        "--input-text",
        help="Raw text idea/topic",
    )
    input_group.add_argument(
        "--input-image",
        help="Path to ad screenshot (analyzed with vision)",
    )
    input_group.add_argument(
        "--input-url",
        help="URL to ad/landing page",
    )
    input_group.add_argument(
        "--idea-id",
        help="Idea ID from the company idea pool",
    )

    # Flags
    parser.add_argument(
        "--research",
        action="store_true",
        help="Run research stage (default: skip)",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from a pending subagent",
    )
    parser.add_argument(
        "--subagent-result-file",
        help="Path to JSON file containing subagent result (used with --resume)",
    )
    parser.add_argument(
        "--approve",
        action="store_true",
        help="Approve the current stage (used with --resume)",
    )
    parser.add_argument(
        "--auto",
        action="store_true",
        help="Auto-approve all human approval gates (non-interactive mode)",
    )
    parser.add_argument(
        "--num-images",
        type=int,
        default=1,
        help="Number of image variants to generate per creative (default: 1)",
    )
    parser.add_argument(
        "--model",
        choices=["openai_image", "google_imagen", "gemini_image", "seedream_image", "auto"],
        default="auto",
        help="Image generation model (default: auto = image_selector decides)",
    )
    parser.add_argument(
        "--openmontage-root",
        help="Path to OpenMontage repo root (auto-detected if omitted)",
    )
    parser.add_argument(
        "--self-execution",
        action="store_true",
        help="Enable agent-native self-execution mode (no subagents)",
    )
    parser.add_argument(
        "--stop-after",
        help="Pause after a specific stage (for debugging)",
    )
    parser.add_argument(
        "--from-stage",
        help="Resume from a specific stage (mark prior stages complete)",
    )
    parser.add_argument(
        "--company-profile",
        help="Override path to company profile JSON",
    )

    args = parser.parse_args()
    om_root = Path(args.openmontage_root) if args.openmontage_root else _auto_detect_root()

    # ------------------------------------------------------------------
    # Resume mode: no input processing needed
    # ------------------------------------------------------------------
    if args.resume:
        # Create orchestrator with empty idea (ignored on resume)
        orchestrator = MarketingCreativeOrchestrator(
            campaign_id=args.campaign_id,
            company_slug=args.company,
            idea={},
            openmontage_root=om_root,
            run_research=args.research,
            num_images=args.num_images,
            model=args.model,
            self_execution=args.self_execution,
            stop_after=args.stop_after,
            from_stage=args.from_stage,
            company_profile_path=Path(args.company_profile) if args.company_profile else None,
        )

        if args.auto:
            # Pre-approve all stages so resume never hits an approval gate.
            for stage in orchestrator.stage_order:
                orchestrator.session.record_human_approval(stage, True)
            orchestrator.session.set_auto_mode(True)
            orchestrator.session.save()

        if args.approve:
            current = orchestrator.session.state.get("current_stage")
            if current:
                orchestrator.session.record_human_approval(current, True)
            else:
                next_stage = orchestrator.session.get_next_stage(orchestrator.stage_order)
                if next_stage:
                    orchestrator.session.record_human_approval(next_stage, True)

        if args.subagent_result_file:
            result_path = Path(args.subagent_result_file)
            if not result_path.exists():
                print(
                    f"error: subagent result file not found: {result_path}",
                    file=sys.stderr,
                )
                return 1
            with open(result_path, encoding="utf-8") as f:
                result = json.load(f)
            action = orchestrator.resume_with_subagent_result(result)
        else:
            # Session state is the single source of truth.
            # If a stage was marked running but not completed, trust session state.
            # Do NOT auto-detect from file existence (causes infinite loops).
            current = orchestrator.session.state.get("current_stage")
            if current and not orchestrator.session.is_stage_completed(current):
                # Clear the running state so the stage can be re-evaluated
                orchestrator.session.state["current_stage"] = None
                orchestrator.session.state["pending_subagent"] = None
                orchestrator.session.save()
                print(
                    f"resuming: stage '{current}' was in progress, will be re-evaluated",
                    file=sys.stderr,
                )
            action = orchestrator.run()

        print(json.dumps(action, indent=2, ensure_ascii=False))
        return 0

    # ------------------------------------------------------------------
    # Fresh run: process input source into an idea
    # ------------------------------------------------------------------
    if not any([args.input_text, args.input_image, args.input_url, args.idea_id]):
        print(
            "error: one of --input-text, --input-image, --input-url, or --idea-id is required",
            file=sys.stderr,
        )
        return 1

    idea: dict | None = None
    raw_input: dict | None = None

    if args.idea_id:
        # Load existing idea from pool.
        idea = _load_idea_from_pool(args.idea_id, args.company, om_root)
        print(f"Idea loaded from pool: {idea['id']}", file=sys.stderr)
    elif args.input_text:
        raw_input = {"type": "text", "value": args.input_text}
    elif args.input_image:
        raw_input = {"type": "image", "path": str(Path(args.input_image).resolve())}
    elif args.input_url:
        raw_input = {"type": "url", "url": args.input_url}

    # ------------------------------------------------------------------
    # Create orchestrator and run
    # ------------------------------------------------------------------
    orchestrator = MarketingCreativeOrchestrator(
        campaign_id=args.campaign_id,
        company_slug=args.company,
        idea=idea or {},
        raw_input=raw_input,
        openmontage_root=om_root,
        run_research=args.research,
        num_images=args.num_images,
        model=args.model,
        self_execution=args.self_execution,
        stop_after=args.stop_after,
        from_stage=args.from_stage,
        company_profile_path=Path(args.company_profile) if args.company_profile else None,
    )

    if args.auto:
        # Auto-approve all stages for non-interactive execution.
        for stage in orchestrator.stage_order:
            orchestrator.session.record_human_approval(stage, True)
        orchestrator.session.set_auto_mode(True)
        orchestrator.session.save()

    if args.approve:
        # Approve the current/next stage on fresh run.
        current = orchestrator.session.state.get("current_stage")
        if current:
            orchestrator.session.record_human_approval(current, True)
        else:
            next_stage = orchestrator.session.get_next_stage(orchestrator.stage_order)
            if next_stage:
                orchestrator.session.record_human_approval(next_stage, True)

    action = orchestrator.run()
    print(json.dumps(action, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
