"""Pipeline session management for persistent campaign state.

A PipelineSession tracks the progress of a single campaign through the pipeline,
storing completed stages, pending subagents, artifacts, and budget. It persists
to disk so the pipeline can resume across Claude Code invocations and subagent
spawns.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


class PipelineSession:
    """Persistent session for a pipeline campaign run.

    State is stored at ``{campaign_dir}/.session.json`` and updated atomically
    after every significant operation.
    """

    def __init__(
        self,
        campaign_id: str,
        campaign_dir: Path,
        company_slug: str,
        session_id: Optional[str] = None,
    ) -> None:
        self.campaign_id = campaign_id
        self.campaign_dir = Path(campaign_dir)
        self.company_slug = company_slug
        self.session_file = self.campaign_dir / ".session.json"
        self.session_id = session_id or str(uuid.uuid4())[:8]
        self.state = self._load_or_init()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load_or_init(self) -> dict[str, Any]:
        if self.session_file.exists():
            with open(self.session_file, encoding="utf-8") as f:
                loaded = json.load(f)
            # If a session_id was passed explicitly but file exists with a
            # different one, trust the file (resuming).
            self.session_id = loaded.get("session_id", self.session_id)
            return loaded

        return {
            "session_id": self.session_id,
            "campaign_id": self.campaign_id,
            "company_slug": self.company_slug,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "status": "initialized",
            "current_stage": None,
            "completed_stages": [],
            "pending_subagent": None,
            "artifacts": {},
            "budget": {"spent_usd": 0.0, "cap_usd": 5.00},
            "decisions": [],
            "execution_mode": "subagent",
            "auto_mode": False,
            "stop_after_stage": None,
        }

    def save(self) -> None:
        """Atomically write session state to disk."""
        self.state["updated_at"] = datetime.now(timezone.utc).isoformat()
        self.session_file.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.session_file.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.state, f, indent=2, ensure_ascii=False)
        tmp.replace(self.session_file)

    # ------------------------------------------------------------------
    # Stage lifecycle
    # ------------------------------------------------------------------

    def is_stage_completed(self, stage: str) -> bool:
        return stage in self.state["completed_stages"]

    def get_next_stage(self, stage_order: list[str]) -> Optional[str]:
        for stage in stage_order:
            if not self.is_stage_completed(stage):
                return stage
        return None

    def set_current_stage(self, stage: str) -> None:
        self.state["current_stage"] = stage
        self.state["status"] = "running"
        self.save()

    def mark_stage_completed(self, stage: str, artifacts: dict[str, Any]) -> None:
        if stage not in self.state["completed_stages"]:
            self.state["completed_stages"].append(stage)
        self.state["artifacts"][stage] = artifacts
        self.state["current_stage"] = None
        self.state["pending_subagent"] = None
        self.save()

    # ------------------------------------------------------------------
    # Subagent pause / resume
    # ------------------------------------------------------------------

    def pause_for_subagent(self, stage: str, spawn_request: dict[str, Any]) -> None:
        self.state["status"] = "paused"
        self.state["pending_subagent"] = {
            "stage": stage,
            "spawn_request": spawn_request,
            "requested_at": datetime.now(timezone.utc).isoformat(),
        }
        self.save()

    def resume_from_subagent(self) -> None:
        self.state["status"] = "running"
        self.state["pending_subagent"] = None
        self.save()

    def get_pending_subagent(self) -> Optional[dict[str, Any]]:
        return self.state.get("pending_subagent")

    # ------------------------------------------------------------------
    # Budget
    # ------------------------------------------------------------------

    def add_cost(self, cost_usd: float) -> bool:
        self.state["budget"]["spent_usd"] += cost_usd
        self.save()
        return self.state["budget"]["spent_usd"] <= self.state["budget"]["cap_usd"]

    def set_budget_cap(self, cap_usd: float) -> None:
        self.state["budget"]["cap_usd"] = cap_usd
        self.save()

    def is_over_budget(self) -> bool:
        return self.state["budget"]["spent_usd"] > self.state["budget"]["cap_usd"]

    # ------------------------------------------------------------------
    # Human approval
    # ------------------------------------------------------------------

    def record_human_approval(self, stage: str, approved: bool, notes: str = "") -> None:
        self.state.setdefault("human_approvals", []).append(
            {
                "stage": stage,
                "approved": approved,
                "notes": notes,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )
        self.save()

    def is_human_approved(self, stage: str) -> bool:
        approvals = self.state.get("human_approvals", [])
        for a in reversed(approvals):
            if a["stage"] == stage:
                return a["approved"]
        return False

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # Execution mode
    # ------------------------------------------------------------------

    def set_execution_mode(self, mode: str) -> None:
        self.state["execution_mode"] = mode
        self.save()

    def get_execution_mode(self) -> str:
        return self.state.get("execution_mode", "subagent")

    def set_auto_mode(self, enabled: bool) -> None:
        self.state["auto_mode"] = enabled
        self.save()

    def is_auto_mode(self) -> bool:
        return self.state.get("auto_mode", False)

    def set_stop_after(self, stage: str | None) -> None:
        self.state["stop_after_stage"] = stage
        self.save()

    def should_stop_after(self, stage: str) -> bool:
        return self.state.get("stop_after_stage") == stage

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        return self.state

    def __repr__(self) -> str:
        return (
            f"PipelineSession({self.campaign_id!r}, "
            f"status={self.state['status']!r}, "
            f"completed={self.state['completed_stages']!r})"
        )
