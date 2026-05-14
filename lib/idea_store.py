"""Idea pool storage: read and write structured idea files with YAML front matter.

Ideas are stored as markdown files in the company idea pool directory.
Each file has a YAML front matter block with metadata and a markdown body
with structured sections.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


@dataclass
class Idea:
    """Structured representation of an idea from the idea pool."""

    id: str
    title: str
    created_at: str
    status: str
    source: str
    author: str
    body: str
    front_matter: dict[str, Any]

    @property
    def core_concept(self) -> str:
        """Extract Core Concept section from body."""
        return self._extract_section("Core Concept")

    @property
    def target_platform(self) -> str:
        return self._extract_section("Target Platform")

    @property
    def primary_language(self) -> str:
        return self._extract_section("Primary Language")

    def _extract_section(self, heading: str) -> str:
        pattern = rf"## {re.escape(heading)}\n+(.*?)(?=\n## |\Z)"
        match = re.search(pattern, self.body, re.DOTALL)
        return match.group(1).strip() if match else ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "created_at": self.created_at,
            "status": self.status,
            "source": self.source,
            "author": self.author,
            "body": self.body,
            **self.front_matter,
        }


class IdeaStore:
    """Read and write ideas to the company idea pool."""

    def __init__(self, idea_pool_dir: Path) -> None:
        self.idea_pool_dir = Path(idea_pool_dir)
        self.idea_pool_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def list_ideas(self) -> list[dict[str, Any]]:
        """List all ideas in the pool with basic metadata."""
        ideas = []
        for f in sorted(self.idea_pool_dir.glob("*.md")):
            try:
                idea = self.load_idea(f.stem)
                ideas.append(
                    {
                        "id": idea.id,
                        "title": idea.title,
                        "created_at": idea.created_at,
                        "status": idea.status,
                        "source": idea.source,
                    }
                )
            except Exception:
                continue
        return ideas

    def load_idea(self, idea_id: str) -> Idea:
        """Load an idea by ID, parsing front matter and body."""
        idea_file = self._find_idea_file(idea_id)
        content = idea_file.read_text(encoding="utf-8")
        front_matter, body = self._parse_front_matter(content)

        return Idea(
            id=front_matter.get("id", idea_id),
            title=front_matter.get("title", idea_id),
            created_at=front_matter.get("created_at", ""),
            status=front_matter.get("status", "draft"),
            source=front_matter.get("source", "unknown"),
            author=front_matter.get("author", ""),
            body=body.strip(),
            front_matter=front_matter,
        )

    def _find_idea_file(self, idea_id: str) -> Path:
        """Find idea file by exact match or prefix."""
        exact = self.idea_pool_dir / f"{idea_id}.md"
        if exact.exists():
            return exact
        for f in self.idea_pool_dir.glob("*.md"):
            if f.stem.startswith(idea_id):
                return f
        raise FileNotFoundError(f"Idea {idea_id!r} not found in {self.idea_pool_dir}")

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def save_idea(
        self,
        idea_id: str,
        title: str,
        body: str,
        source: str = "conversation",
        author: str = "user",
        extra_front_matter: dict[str, Any] | None = None,
    ) -> Path:
        """Write a structured idea to the idea pool.

        Args:
            idea_id: Unique identifier for the idea (used as filename).
            title: Human-readable title.
            body: Markdown body with structured sections.
            source: Where the idea came from (conversation, image, url, idea_pool).
            author: Who created the idea.
            extra_front_matter: Additional metadata to include in front matter.

        Returns:
            Path to the written file.
        """
        front_matter: dict[str, Any] = {
            "id": idea_id,
            "title": title,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "status": "finalized",
            "source": source,
            "author": author,
        }
        if extra_front_matter:
            front_matter.update(extra_front_matter)

        content = self._render_idea_file(front_matter, body)
        idea_file = self.idea_pool_dir / f"{idea_id}.md"
        idea_file.write_text(content, encoding="utf-8")
        return idea_file

    def update_idea(self, idea_id: str, **kwargs: Any) -> Path:
        """Load an existing idea, update fields, and write back."""
        idea = self.load_idea(idea_id)

        if "title" in kwargs:
            idea.title = kwargs.pop("title")
        if "body" in kwargs:
            idea.body = kwargs.pop("body")
        if "status" in kwargs:
            idea.status = kwargs.pop("status")

        idea.front_matter.update(kwargs)
        idea.front_matter["updated_at"] = datetime.now(timezone.utc).isoformat()

        content = self._render_idea_file(idea.front_matter, idea.body)
        idea_file = self.idea_pool_dir / f"{idea.id}.md"
        idea_file.write_text(content, encoding="utf-8")
        return idea_file

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_front_matter(content: str) -> tuple[dict[str, Any], str]:
        """Parse YAML front matter from markdown content.

        Returns (front_matter_dict, body_without_front_matter).
        """
        if not content.startswith("---"):
            return {}, content

        parts = content.split("---", 2)
        if len(parts) < 3:
            return {}, content

        try:
            front_matter = yaml.safe_load(parts[1]) or {}
        except yaml.YAMLError:
            front_matter = {}

        body = parts[2]
        return front_matter, body

    @staticmethod
    def _render_idea_file(front_matter: dict[str, Any], body: str) -> str:
        """Render front matter + body into a markdown file."""
        yaml_block = yaml.safe_dump(
            front_matter,
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True,
        )
        return f"---\n{yaml_block}---\n\n{body}\n"
