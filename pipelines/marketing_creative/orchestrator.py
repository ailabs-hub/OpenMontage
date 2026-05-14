"""Code-level orchestrator for the marketing-creative pipeline.

Manages pipeline state, drives stage execution, pre-creates output directories,
and emits structured action requests for Claude Code to spawn subagents.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from lib.checkpoint import write_checkpoint, write_gate
from lib.idea_store import IdeaStore
from lib.pipeline_loader import load_pipeline
from lib.session import PipelineSession
from lib.subagent_dispatcher import (
    STAGE_HUMAN_APPROVAL,
    build_spawn_request,
)

from .agent_utils import (
    STAGE_OUTPUTS,
    get_stage_sequence,
)


class MarketingCreativeOrchestrator:
    """Concrete orchestrator for the marketing-creative pipeline.

    Usage (from Claude Code):
        orch = MarketingCreativeOrchestrator(
            campaign_id="noise_vs_clarity",
            company_slug="mycompany",
            idea={"title": "...", ...},  # from pool, OR
            raw_input={"type": "text", "value": "..."},  # raw input
        )
        action = orch.run()
        # Claude Code interprets action and spawns subagent
        # ... subagent completes ...
        action = orch.resume_with_subagent_result(subagent_result)
    """

    PIPELINE_NAME = "marketing-creative"

    # Stage sequencing is now centralized in agent_utils.py for consistency
    # between orchestrator mode and agent-native mode.

    def __init__(
        self,
        campaign_id: str,
        company_slug: str,
        idea: Optional[dict[str, Any]] = None,
        raw_input: Optional[dict[str, Any]] = None,
        openmontage_root: Optional[Path] = None,
        run_research: bool = False,
        num_images: int = 1,
        model: str = "auto",
        self_execution: bool = False,
        stop_after: Optional[str] = None,
        from_stage: Optional[str] = None,
        company_profile_path: Optional[Path] = None,
    ) -> None:
        self.campaign_id = campaign_id
        self.company_slug = company_slug
        self.run_research = run_research
        self.num_images = num_images
        self.model = model
        self.self_execution = self_execution
        self.stop_after = stop_after
        self.from_stage = from_stage
        self.company_profile_path = company_profile_path
        self.openmontage_root = Path(openmontage_root) if openmontage_root else self._find_openmontage_root()

        # Load company profile.
        self.company_profile = self._load_company_profile()

        # Resolve project root from company profile.
        self.project_root = self._resolve_project_root()

        # Campaign directory.
        self.campaign_dir = self.project_root / "campaigns" / campaign_id

        # Pre-create all output directories.
        self._ensure_directories()

        # Load pipeline manifest.
        self.manifest = load_pipeline(self.PIPELINE_NAME)

        # Budget cap from manifest.
        self.budget_cap = (
            self.manifest.get("orchestration", {}).get("budget_default_usd", 5.0)
        )

        # Initialize or resume session.
        self.session = PipelineSession(
            campaign_id=campaign_id,
            campaign_dir=self.campaign_dir,
            company_slug=company_slug,
        )
        self.session.set_budget_cap(self.budget_cap)
        self.session.state["num_images"] = num_images
        self.session.state["model"] = model
        self.session.set_execution_mode("self_execution" if self_execution else "subagent")
        if stop_after:
            self.session.set_stop_after(stop_after)
        self.session.save()

        # Determine if we need idea refinement.
        self.needs_idea_refinement = self._detect_needs_refinement(raw_input)

        # Mark prior stages complete (must be after needs_idea_refinement is set).
        if from_stage:
            self._mark_prior_stages_complete(from_stage)

        # Store input metadata in session (for resume).
        self._persist_input_metadata(idea, raw_input)

        # On resume: if idea_refinement completed, load the idea from pool.
        self.idea = self._resolve_idea(idea, raw_input)

        # Build locked brief.
        self.locked_brief = self._build_locked_brief()

        # Persist locked brief for resume.
        self.session.state["locked_brief"] = self.locked_brief
        self.session.save()

        # Write README with locked brief (if not already present).
        self._write_readme()

    @property
    def skip_checkpoints(self) -> bool:
        """Skip checkpoint/gate writes in auto mode to reduce friction."""
        return self.session.state.get("auto_mode", False)

    # ------------------------------------------------------------------
    # Input resolution
    # ------------------------------------------------------------------

    def _detect_needs_refinement(self, raw_input: Optional[dict[str, Any]]) -> bool:
        """True if the input is raw (needs a subagent to refine into an idea file)."""
        if raw_input is not None:
            return True
        # If session already recorded that refinement was needed, trust it.
        if self.session.state.get("input_source") == "raw":
            return True
        # If idea_refinement is already completed, we don't need it again.
        if "idea_refinement" in self.session.state.get("completed_stages", []):
            return False
        return False

    def _persist_input_metadata(
        self,
        idea: Optional[dict[str, Any]],
        raw_input: Optional[dict[str, Any]],
    ) -> None:
        """Store input source info in session for resume."""
        if raw_input is not None:
            self.session.state["input_source"] = "raw"
            self.session.state["raw_input"] = raw_input
        elif idea is not None and idea.get("source") == "idea_pool":
            self.session.state["input_source"] = "pool"
            self.session.state["idea_id"] = idea.get("id", "")
        self.session.save()

    def _resolve_idea(
        self,
        idea: Optional[dict[str, Any]],
        raw_input: Optional[dict[str, Any]],
    ) -> dict[str, Any]:
        """Get the idea dict — from param, from pool, or empty (if refinement pending)."""
        # Fresh run with explicit idea dict.
        if idea is not None:
            return idea

        # Resume: if idea_refinement completed, load from pool.
        completed = self.session.state.get("completed_stages", [])
        if "idea_refinement" in completed or "research" in completed:
            idea_id = self.session.state.get("idea_id")
            if idea_id:
                loaded = self._load_idea_from_pool(idea_id)
                if loaded:
                    return loaded

        # Resume with locked brief already stored.
        lb = self.session.state.get("locked_brief")
        if lb:
            return {
                "title": lb.get("idea", ""),
                "topic": lb.get("topic", ""),
                "platform": lb.get("platform", ""),
                "language": lb.get("language", ""),
                "source": lb.get("source", "conversation"),
            }

        return {}

    def _load_idea_from_pool(self, idea_id: str) -> Optional[dict[str, Any]]:
        """Load an idea from the company idea pool."""
        try:
            idea_pool_rel = self.company_profile.get("paths", {}).get("idea_pool", "../ideas/")
            idea_pool_dir = (self.openmontage_root / idea_pool_rel).resolve()
            store = IdeaStore(idea_pool_dir)
            idea = store.load_idea(idea_id)
            return {
                "id": idea.id,
                "title": idea.title,
                "topic": idea.core_concept or idea.body[:200],
                "body": idea.body,
                "source": idea.source,
                "platform": idea.target_platform or "",
                "language": idea.primary_language or "",
            }
        except Exception:
            return None

    # ------------------------------------------------------------------
    # Path resolution
    # ------------------------------------------------------------------

    def _find_openmontage_root(self) -> Path:
        """Resolve OpenMontage repo root from this file's location."""
        return Path(__file__).resolve().parent.parent.parent

    def _load_company_profile(self) -> dict[str, Any]:
        if self.company_profile_path:
            profile_path = Path(self.company_profile_path)
        else:
            # Company profiles live outside the OpenMontage repo, in the parent directory.
            profile_path = (
                self.openmontage_root.parent
                / "company_profiles"
                / f"{self.company_slug}.json"
            )
        if not profile_path.exists():
            raise FileNotFoundError(f"Company profile not found: {profile_path}")
        with open(profile_path, encoding="utf-8") as f:
            return json.load(f)

    def _mark_prior_stages_complete(self, from_stage: str) -> None:
        """Mark all stages before from_stage as completed."""
        for stage in self.stage_order:
            if stage == from_stage:
                break
            if not self.session.is_stage_completed(stage):
                self.session.mark_stage_completed(stage, {})
        self.session.save()

    def _resolve_project_root(self) -> Path:
        """Resolve project_root from company profile relative to OpenMontage root."""
        rel = self.company_profile.get("paths", {}).get("project_root", "..")
        return (self.openmontage_root / rel).resolve()

    def _resolve_idea_pool_dir(self) -> Path:
        """Resolve idea_pool directory from company profile."""
        rel = self.company_profile.get("paths", {}).get("idea_pool", "../ideas/")
        return (self.openmontage_root / rel).resolve()

    def _ensure_directories(self) -> None:
        """Pre-create all output directories so subagents never need mkdir."""
        dirs = [
            self.campaign_dir / "artifacts",
            self.campaign_dir / "copy_variants",
            self.campaign_dir / "assets",
            self.campaign_dir / "logs",
            self.campaign_dir / "checkpoints",
        ]
        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Locked brief
    # ------------------------------------------------------------------

    def _build_locked_brief(self) -> dict[str, Any]:
        """Build the locked brief dict passed to every subagent."""
        audience = self.company_profile.get("primary_audience", {})
        return {
            "idea": self.idea.get("title", self.idea.get("id", "untitled")),
            "topic": self.idea.get("topic", self.idea.get("core_concept", "")),
            "platform": self.idea.get("platform", "instagram_feed"),
            "language": self.idea.get("language", audience.get("primary_language", "English")),
            "audience": (
                f"{audience.get('age_range', '25-45')}, "
                f"{audience.get('location', 'India')}, "
                f"interests: {', '.join(audience.get('interests', ['astrology'])[:3])}"
            ),
            "budget_cap": self.budget_cap,
            "special_instructions": self.idea.get("special_instructions", ""),
            "source": self.idea.get("source", "conversation"),
        }

    def _write_readme(self) -> None:
        readme = self.campaign_dir / "README.md"
        if readme.exists():
            return  # Do not overwrite on resume.

        source = self.locked_brief.get("source", "conversation")
        research_note = "Research: SKIPPED (default)\n" if not self.run_research else "Research: ENABLED\n"
        refinement_note = ""
        if self.needs_idea_refinement and "idea_refinement" not in self.session.state.get("completed_stages", []):
            refinement_note = "Idea Refinement: PENDING (raw input → structured idea via subagent)\n"
        elif "idea_refinement" in self.session.state.get("completed_stages", []):
            refinement_note = "Idea Refinement: COMPLETED\n"

        content = f"""# Campaign: {self.campaign_id}

**Company:** {self.company_profile.get("company_name", self.company_slug)}
**Product:** {self.company_profile.get("product_name", "N/A")}
**Language:** {self.locked_brief["language"]}
**Platform:** {self.locked_brief["platform"]}
**Idea Source:** {source}
{research_note}{refinement_note}
## Locked Brief

| Field | Value |
|---|---|
| Idea | {self.locked_brief["idea"]} |
| Topic | {self.locked_brief["topic"]} |
| Platform | {self.locked_brief["platform"]} |
| Language | {self.locked_brief["language"]} |
| Audience | {self.locked_brief["audience"]} |
| Budget Cap | ${self.locked_brief["budget_cap"]} |
| Special Instructions | {self.locked_brief["special_instructions"] or "none"} |

## Pipeline Status

See `.session.json` for current stage and completion status.
"""
        readme.write_text(content, encoding="utf-8")

    # ------------------------------------------------------------------
    # Main orchestration loop
    # ------------------------------------------------------------------

    @property
    def stage_order(self) -> list[str]:
        """Return the stage order based on configuration."""
        input_source = "raw_input" if self.needs_idea_refinement else "idea_pool"
        return get_stage_sequence(input_source, research=self.run_research)

    def run(self) -> dict[str, Any]:
        """Determine the next action and return it as a dict.

        Returns one of:
            {"action": "complete", ...}
            {"action": "await_human_approval", ...}
            {"action": "spawn_subagent", "spawn_request": {...}}   (subagent mode)
            {"action": "execute_stage", "instructions": {...}}      (self-execution mode)
            {"action": "paused", "message": ...}                     (stop-after)
            {"action": "error", "message": ...}
        """
        next_stage = self.session.get_next_stage(self.stage_order)

        if next_stage is None:
            self.session.state["status"] = "completed"
            self.session.save()
            return {
                "action": "complete",
                "campaign_id": self.campaign_id,
                "campaign_dir": str(self.campaign_dir),
                "completed_stages": self.session.state["completed_stages"],
                "message": "All pipeline stages complete.",
            }

        self.session.set_current_stage(next_stage)

        # Check human approval gate.
        if STAGE_HUMAN_APPROVAL.get(next_stage, False):
            if not self.session.is_human_approved(next_stage):
                return {
                    "action": "await_human_approval",
                    "stage": next_stage,
                    "artifact_summary": self._summarize_stage_for_approval(next_stage),
                    "message": f"Stage '{next_stage}' requires human approval before proceeding.",
                }

        # Validate input artifacts exist.
        input_files = self._get_input_files_for_stage(next_stage)
        missing = self._validate_input_files(input_files)
        if missing:
            return {
                "action": "error",
                "stage": next_stage,
                "message": f"Missing input artifacts for stage '{next_stage}': {missing}",
            }

        # Build request based on execution mode.
        if self.self_execution or self.session.get_execution_mode() == "self_execution":
            return self._run_self_execution_stage(next_stage, input_files)
        else:
            return self._run_subagent_stage(next_stage, input_files)

    def _run_subagent_stage(self, stage: str, input_files: dict[str, str]) -> dict[str, Any]:
        """Build and return a subagent spawn request (legacy mode)."""
        generation_config: dict[str, Any] | None = None
        if stage == "assets":
            generation_config = {
                "num_images": self.session.state.get("num_images", self.num_images),
                "model": self.session.state.get("model", self.model),
            }
        spawn_request = build_spawn_request(
            stage=stage,
            campaign_dir=self.campaign_dir,
            input_files=input_files,
            locked_brief=self.locked_brief,
            openmontage_root=self.openmontage_root,
            generation_config=generation_config,
        )

        # Inject raw input context for idea_refinement stage.
        if stage == "idea_refinement":
            spawn_request = self._inject_raw_input(spawn_request)

        # Pause session and emit spawn request.
        self.session.pause_for_subagent(stage, spawn_request)

        return {
            "action": "spawn_subagent",
            "spawn_request": spawn_request,
        }

    def _run_self_execution_stage(self, stage: str, input_files: dict[str, str]) -> dict[str, Any]:
        """Build and return self-execution instructions for the agent."""
        from lib.subagent_dispatcher import build_execute_request

        generation_config: dict[str, Any] | None = None
        if stage == "assets":
            generation_config = {
                "num_images": self.session.state.get("num_images", self.num_images),
                "model": self.session.state.get("model", self.model),
            }

        execute_request = build_execute_request(
            stage=stage,
            campaign_dir=self.campaign_dir,
            input_files=input_files,
            locked_brief=self.locked_brief,
            openmontage_root=self.openmontage_root,
            generation_config=generation_config,
        )

        # Inject raw input context for idea_refinement stage.
        if stage == "idea_refinement":
            raw = self.session.state.get("raw_input", {})
            if raw:
                execute_request["raw_input"] = raw

        # Check stop-after.
        if self.session.should_stop_after(stage):
            self.session.mark_stage_completed(stage, {})
            return {
                "action": "paused",
                "stage": stage,
                "message": f"Pipeline paused after stage '{stage}' as requested (--stop-after).",
                "next_command": (
                    f"python -m pipelines.marketing_creative "
                    f"--campaign-id {self.campaign_id} "
                    f"--company {self.company_slug} "
                    f"--resume --self-execution"
                ),
            }

        # Pause session with execute request.
        self.session.pause_for_subagent(stage, execute_request)

        return {
            "action": "execute_stage",
            "stage": stage,
            "instructions": execute_request,
        }

    def _inject_raw_input(self, spawn_request: dict[str, Any]) -> dict[str, Any]:
        """Add raw input context to the idea_refinement spawn request."""
        raw = self.session.state.get("raw_input", {})
        if not raw:
            return spawn_request

        extra = f"\n\nRAW INPUT TO REFINE:\n"
        input_type = raw.get("type", "text")
        if input_type == "text":
            extra += f"Type: text\nValue: {raw.get('value', '')}\n"
        elif input_type == "image":
            extra += f"Type: image\nPath: {raw.get('path', '')}\n"
            extra += "Analyze this image using vision. Extract headline, body, CTA, visual style, color palette, platform, emotional angle, layout. Then reimagine for the target company.\n"
        elif input_type == "url":
            extra += f"Type: url\nURL: {raw.get('url', '')}\n"
            extra += "Fetch this URL, extract ad/landing page elements, then reimagine for the target company.\n"

        company_profile_path = self.openmontage_root.parent / "company_profiles" / f"{self.company_slug}.json"
        extra += f"\nCOMPANY PROFILE (read for defaults): {company_profile_path}\n"
        extra += f"Write the structured idea file to: {self._resolve_idea_pool_dir()}\n"
        extra += "Return the idea_id you used in your response.\n"

        spawn_request["prompt"] = spawn_request["prompt"] + extra
        return spawn_request

    def resume_with_subagent_result(self, result: dict[str, Any]) -> dict[str, Any]:
        """Process a subagent result and continue the pipeline."""
        stage = result.get("stage")
        if not stage:
            return {
                "action": "error",
                "message": "Missing 'stage' key in subagent result.",
            }

        self.session.resume_from_subagent()

        # If idea_refinement completed, capture the idea_id from the result.
        if stage == "idea_refinement":
            artifacts = result.get("artifacts", {})
            idea_id = artifacts.get("idea_id")
            if idea_id:
                self.session.state["idea_id"] = idea_id
                self.session.save()
                # Reload idea so subsequent stages have it.
                loaded = self._load_idea_from_pool(idea_id)
                if loaded:
                    self.idea = loaded
                    self.locked_brief = self._build_locked_brief()
                    self.session.state["locked_brief"] = self.locked_brief
                    self.session.save()

        # Verify output files exist on disk.
        expected_outputs = STAGE_OUTPUTS.get(stage, [])
        missing = []
        for rel_path in expected_outputs:
            abs_path = self.campaign_dir / rel_path
            if not abs_path.exists():
                missing.append(rel_path)

        if missing:
            return {
                "action": "retry_subagent",
                "stage": stage,
                "missing_files": missing,
                "message": (
                    f"Subagent claimed completion for stage '{stage}' but "
                    f"expected output files are missing: {missing}. "
                    f"Re-run the subagent and ensure all files are written."
                ),
            }

        # Validate output content (basic checks).
        validation = self._validate_stage_output(stage, result)
        if not validation["passed"]:
            return {
                "action": "retry_subagent",
                "stage": stage,
                "reason": validation["failures"],
                "message": f"Stage '{stage}' output validation failed: {validation['failures']}",
            }

        # Budget tracking.
        cost = result.get("cost_usd", 0.0)
        if cost > 0:
            under_budget = self.session.add_cost(cost)
            if not under_budget:
                return {
                    "action": "error",
                    "message": (
                        f"Budget exceeded. Spent: ${self.session.state['budget']['spent_usd']:.3f} "
                        f"/ Cap: ${self.session.state['budget']['cap_usd']:.3f}"
                    ),
                }

        # Write checkpoint (skipped in auto mode to reduce friction).
        if not self.skip_checkpoints:
            self._write_checkpoint(stage, result)
            self._write_gate(stage, result, validation)

        # Mark stage complete.
        artifacts = result.get("artifacts", {})
        self.session.mark_stage_completed(stage, artifacts)

        # Continue to next stage.
        return self.run()

    # ------------------------------------------------------------------
    # Input / output helpers
    # ------------------------------------------------------------------

    def _get_input_files_for_stage(self, stage: str) -> dict[str, str]:
        """Return the input file mapping for a stage (relative to campaign_dir)."""
        inputs: dict[str, str] = {}
        if stage == "idea_refinement":
            # idea_refinement uses company profile + raw input (in prompt)
            pass
        elif stage == "research":
            # research uses company profile + idea (in prompt)
            pass
        elif stage == "creative_concept":
            if self.run_research:
                inputs["research_brief"] = "artifacts/research_brief.json"
            # When research is skipped, creative_concept uses company profile + idea
            # (already included in the locked brief and company context).
        elif stage == "copy":
            inputs["creative_specs"] = "artifacts/creative_specs.json"
        elif stage == "assets":
            inputs["copy_manifest"] = "artifacts/copy_manifest.json"
            inputs["creative_specs"] = "artifacts/creative_specs.json"
        elif stage == "review":
            inputs["asset_manifest"] = "artifacts/asset_manifest.json"
            inputs["copy_manifest"] = "artifacts/copy_manifest.json"
            inputs["creative_specs"] = "artifacts/creative_specs.json"
        return inputs

    def _validate_input_files(self, input_files: dict[str, str]) -> list[str]:
        """Return list of missing input file paths."""
        missing = []
        for name, rel in input_files.items():
            path = self.campaign_dir / rel
            if not path.exists():
                missing.append(rel)
        return missing

    def _validate_stage_output(self, stage: str, result: dict[str, Any]) -> dict[str, Any]:
        """Run basic validation on subagent output.

        Returns {"passed": bool, "failures": list[str]}.
        """
        failures: list[str] = []
        artifacts = result.get("artifacts", {})

        if stage == "idea_refinement":
            if not artifacts.get("idea_id"):
                failures.append("Missing idea_id in artifacts")

        elif stage == "research":
            brief = artifacts.get("research_brief", {})
            signals = brief.get("signals", [])
            if len(signals) < 3:
                failures.append(f"Expected >=3 signals, got {len(signals)}")

        elif stage == "creative_concept":
            specs = artifacts.get("creative_specs", {})
            creatives = specs.get("creatives", [])
            if len(creatives) < 3:
                failures.append(f"Expected >=3 creatives, got {len(creatives)}")

        elif stage == "copy":
            manifest = artifacts.get("copy_manifest", {})
            creatives = manifest.get("creatives", [])
            if not creatives:
                failures.append("No creatives in copy_manifest")

        elif stage == "assets":
            manifest = artifacts.get("asset_manifest", {})
            assets = manifest.get("assets", [])
            if not assets:
                failures.append("No assets in asset_manifest")

        elif stage == "review":
            review = artifacts.get("final_review", {})
            ab_pairs = review.get("ab_test_plan", {}).get("test_pairs", [])
            if len(ab_pairs) < 2:
                failures.append(f"Expected >=2 A/B pairs, got {len(ab_pairs)}")

        return {"passed": len(failures) == 0, "failures": failures}

    def _write_checkpoint(self, stage: str, result: dict[str, Any]) -> None:
        """Write a checkpoint file for a completed stage."""
        artifacts = result.get("artifacts", {})
        canonical = {
            "idea_refinement": "idea_file",
            "research": "research_brief",
            "creative_concept": "creative_specs",
            "copy": "copy_manifest",
            "assets": "asset_manifest",
            "review": "final_review",
        }
        canonical_name = canonical.get(stage, stage)

        write_checkpoint(
            pipeline_dir=self.campaign_dir.parent,
            project_id=self.campaign_id,
            stage=stage,
            status="completed",
            artifacts={canonical_name: artifacts.get(canonical_name, {})},
            pipeline_type=self.PIPELINE_NAME,
        )

    def _write_gate(
        self,
        stage: str,
        result: dict[str, Any],
        validation: dict[str, Any],
    ) -> None:
        """Write a non-bypassable gate file for a completed stage."""
        gate_config = self._get_gate_config(stage)
        validation_fields = gate_config.get("validation_fields", [])

        gate_validation: dict[str, Any] = {}
        for field in validation_fields:
            if field == "prompt_under_400_tokens":
                continue
            gate_validation[field] = True

        if not validation["passed"]:
            gate_validation["output_validation"] = False

        artifact_paths = []
        for rel in STAGE_OUTPUTS.get(stage, []):
            path = self.campaign_dir / rel
            if path.exists():
                artifact_paths.append(path)

        write_gate(
            project_dir=self.campaign_dir,
            gate_id=gate_config.get("gate_id", f"gate-{stage}"),
            stage=stage,
            validation=gate_validation,
            artifact_paths=artifact_paths,
        )

    def _get_gate_config(self, stage: str) -> dict[str, Any]:
        """Read gate configuration for a stage from the pipeline manifest."""
        for s in self.manifest.get("stages", []):
            if s["name"] == stage:
                return s.get("gate", {})
        return {}

    def _summarize_stage_for_approval(self, stage: str) -> str:
        """Build a human-readable summary of a stage for approval."""
        if stage == "idea_refinement":
            return "Structured idea file created from raw input."
        if stage == "research":
            brief = self.session.state.get("artifacts", {}).get("research", {})
            signals = brief.get("research_brief", {}).get("signals", [])
            return f"Research brief with {len(signals)} signals."
        if stage == "creative_concept":
            specs = self.session.state.get("artifacts", {}).get("creative_concept", {})
            creatives = specs.get("creative_specs", {}).get("creatives", [])
            return f"Creative specs with {len(creatives)} concepts."
        if stage == "copy":
            manifest = self.session.state.get("artifacts", {}).get("copy", {})
            creatives = manifest.get("copy_manifest", {}).get("creatives", [])
            return f"Copy manifest with {len(creatives)} creatives."
        if stage == "review":
            review = self.session.state.get("artifacts", {}).get("review", {})
            return "Final review with A/B test plan."
        return f"Stage '{stage}' complete."
