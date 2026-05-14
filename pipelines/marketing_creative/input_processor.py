"""Raw-to-idea processor: converts text, image, URL, or idea-pool refs into structured idea files.

No external LLM calls for text input (uses company profile defaults).
OpenAI vision API used for image analysis (OPENAI_API_KEY already configured).
"""

from __future__ import annotations

import base64
import json
import re
import uuid
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from lib.idea_store import IdeaStore


def _sanitize_id(text: str) -> str:
    """Convert raw text into a URL-safe idea ID."""
    cleaned = re.sub(r"[^\w\s-]", "", text.lower())
    cleaned = re.sub(r"[\s_]+", "-", cleaned.strip())
    cleaned = cleaned[:60].strip("-")
    if not cleaned:
        cleaned = f"idea-{uuid.uuid4().hex[:8]}"
    return f"idea-{cleaned}"


class InputProcessor:
    """Converts raw inputs into structured idea files in the company idea pool."""

    def __init__(self, company_profile: dict[str, Any], om_root: Path) -> None:
        self.company_profile = company_profile
        self.om_root = om_root
        self.idea_pool_dir = self._resolve_idea_pool_dir()
        self.store = IdeaStore(self.idea_pool_dir)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def process_text(self, text: str) -> dict[str, Any]:
        """Create idea from raw text. No LLM call — uses company defaults."""
        idea_id = _sanitize_id(text)
        body = self._build_idea_body(
            core_concept=text,
            platform=self._default_platform(),
            audience=self._default_audience(),
            language=self._default_language(),
        )
        return {
            "id": idea_id,
            "title": text[:60].strip(),
            "body": body,
            "source": "conversation",
            "platform": self._default_platform(),
            "language": self._default_language(),
        }

    def process_image(self, image_path: Path, context_text: str = "") -> dict[str, Any]:
        """Analyze ad image with OpenAI vision, deconstruct, reimagine for company."""
        if not image_path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")

        vision_result = self._call_vision_api(image_path, context_text)
        idea_id = _sanitize_id(
            vision_result.get("reimagined_concept", context_text or "competitor-ad")
        )

        body = self._build_idea_body(
            core_concept=vision_result.get("reimagined_concept", "Competitor ad adaptation"),
            platform=self._default_platform(),
            audience=self._default_audience(),
            language=self._default_language(),
            reference_analysis=vision_result.get("reference_analysis", {}),
            special_instructions=context_text,
        )

        return {
            "id": idea_id,
            "title": vision_result.get("reimagined_title", "Competitor Ad Adaptation"),
            "body": body,
            "source": "image",
            "platform": self._default_platform(),
            "language": self._default_language(),
        }

    def process_url(self, url: str, context_text: str = "") -> dict[str, Any]:
        """Fetch URL, extract ad elements, reimagine for company."""
        content = self._fetch_url(url)
        extraction = self._call_text_api(
            system="You are a marketing analyst. Extract ad/landing page elements and reimagine for a new company.",
            prompt=self._build_url_prompt(content, url),
        )
        parsed = self._safe_json_parse(extraction)

        idea_id = _sanitize_id(
            parsed.get("reimagined_concept", context_text or urlparse(url).netloc)
        )

        body = self._build_idea_body(
            core_concept=parsed.get("reimagined_concept", f"Adaptation of {url}"),
            platform=self._default_platform(),
            audience=self._default_audience(),
            language=self._default_language(),
            reference_analysis=parsed.get("reference_analysis", {}),
            special_instructions=context_text,
        )

        return {
            "id": idea_id,
            "title": parsed.get("reimagined_title", f"URL Adaptation: {urlparse(url).netloc}"),
            "body": body,
            "source": "url",
            "platform": self._default_platform(),
            "language": self._default_language(),
        }

    def load_from_pool(self, idea_id: str) -> dict[str, Any]:
        """Load existing idea from company idea pool."""
        idea = self.store.load_idea(idea_id)
        return {
            "id": idea.id,
            "title": idea.title,
            "topic": idea.core_concept or idea.body[:200],
            "body": idea.body,
            "source": idea.source,
            "platform": idea.target_platform or self._default_platform(),
            "language": idea.primary_language or self._default_language(),
        }

    def write_idea_file(self, idea: dict[str, Any]) -> Path:
        """Write structured idea to idea_pool/{idea_id}.md."""
        return self.store.save_idea(
            idea_id=idea["id"],
            title=idea["title"],
            body=idea["body"],
            source=idea.get("source", "conversation"),
            author="user",
        )

    # ------------------------------------------------------------------
    # Defaults from company profile
    # ------------------------------------------------------------------

    def _default_platform(self) -> str:
        platforms = self.company_profile.get("platform_focus", [])
        return platforms[0] if platforms else "instagram_reels"

    def _default_audience(self) -> str:
        aud = self.company_profile.get("primary_audience", {})
        return f"{aud.get('age_range', '25-45')}, {aud.get('location', 'India')}"

    def _default_language(self) -> str:
        return self.company_profile.get("primary_audience", {}).get("primary_language", "English")

    def _default_visual_direction(self) -> str:
        vs = self.company_profile.get("visual_style", {})
        mood = vs.get("mood", "Premium, clean, modern")
        colors = vs.get("colors", "Neutral palette")
        lighting = vs.get("lighting", "Soft, natural")
        return f"{mood}. Colors: {colors}. Lighting: {lighting}"

    def _default_pain_points(self) -> list[str]:
        return self.company_profile.get("primary_audience", {}).get("pain_points", [])[:3]

    def _default_key_messages(self, core_concept: str) -> list[str]:
        pain_points = self._default_pain_points()
        if pain_points:
            return [
                f"Hook: {pain_points[0][:80]}...",
                f"Payoff: {self.company_profile.get('product_name', 'Our product')} gives you clarity and direction.",
            ]
        return [
            f"Hook: Are you struggling with {core_concept.lower()}?",
            f"Payoff: Discover the answer with {self.company_profile.get('product_name', 'our solution')}.",
        ]

    # ------------------------------------------------------------------
    # Path resolution
    # ------------------------------------------------------------------

    def _resolve_idea_pool_dir(self) -> Path:
        rel = self.company_profile.get("paths", {}).get("idea_pool", "../ideas/")
        return (self.om_root / rel).resolve()

    # ------------------------------------------------------------------
    # Idea body builder
    # ------------------------------------------------------------------

    def _build_idea_body(
        self,
        core_concept: str,
        platform: str,
        audience: str,
        language: str,
        reference_analysis: dict[str, Any] | None = None,
        special_instructions: str = "",
    ) -> str:
        lines: list[str] = []

        lines.append("## Core Concept")
        lines.append(core_concept)
        lines.append("")

        lines.append("## Target Platform")
        lines.append(platform)
        lines.append("")

        lines.append("## Target Audience")
        lines.append(audience)
        lines.append("")

        lines.append("## Primary Language")
        lines.append(language)
        lines.append("")

        lines.append("## Key Messages")
        for msg in self._default_key_messages(core_concept):
            lines.append(f"- {msg}")
        lines.append("")

        lines.append("## Visual Direction")
        lines.append(self._default_visual_direction())
        lines.append("")

        if reference_analysis:
            lines.append("## Reference Analysis")
            lines.append("| Field | Value |")
            lines.append("|---|---|")
            for key, value in reference_analysis.items():
                lines.append(f"| {key} | {value} |")
            lines.append("")

        if special_instructions:
            lines.append("## Special Instructions")
            lines.append(special_instructions)
            lines.append("")

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # LLM helpers (OpenAI — key already configured)
    # ------------------------------------------------------------------

    def _call_vision_api(self, image_path: Path, context_text: str) -> dict[str, Any]:
        """Call OpenAI vision API to analyze an ad image."""
        try:
            from openai import OpenAI
        except ImportError:
            raise RuntimeError("openai package not installed. Run: pip install openai")

        client = OpenAI()

        # Encode image to base64
        with open(image_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("utf-8")

        ext = image_path.suffix.lower().replace(".", "")
        if ext not in ("png", "jpg", "jpeg", "gif", "webp"):
            ext = "png"

        company_name = self.company_profile.get("company_name", "our company")
        product_name = self.company_profile.get("product_name", "our product")
        product_desc = self.company_profile.get("product_description", "")

        system_prompt = (
            "You are a senior marketing strategist. Analyze ad images and reimagine "
            "them for new companies while preserving the underlying strategy."
        )

        user_prompt = f"""Analyze this ad image and reimagine it for {company_name} ({product_name}).

Product description: {product_desc[:300]}

Context from user: {context_text or "None"}

Return ONLY a JSON object with this exact structure:
{{
  "reference_analysis": {{
    "Original Headline": "...",
    "Original Body Copy": "...",
    "Original CTA": "...",
    "Visual Style": "...",
    "Color Palette": "...",
    "Platform": "...",
    "Emotional Angle": "...",
    "Layout Structure": "...",
    "Why It Works": "..."
  }},
  "reimagined_title": "Short title for the new idea",
  "reimagined_concept": "One-paragraph description of the reimagined campaign for {company_name}"
}}
"""

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user_prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/{ext};base64,{b64}",
                                "detail": "high",
                            },
                        },
                    ],
                },
            ],
            max_tokens=2000,
            temperature=0.7,
        )

        content = response.choices[0].message.content or "{}"
        return self._safe_json_parse(content)

    def _call_text_api(self, system: str, prompt: str) -> str:
        """Call OpenAI text API."""
        try:
            from openai import OpenAI
        except ImportError:
            raise RuntimeError("openai package not installed. Run: pip install openai")

        client = OpenAI()
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            max_tokens=2000,
            temperature=0.7,
        )
        return response.choices[0].message.content or "{}"

    def _build_url_prompt(self, content: str, url: str) -> str:
        company_name = self.company_profile.get("company_name", "our company")
        product_name = self.company_profile.get("product_name", "our product")
        product_desc = self.company_profile.get("product_description", "")

        return f"""Analyze this landing page/ad content from {url} and reimagine it for {company_name} ({product_name}).

Product description: {product_desc[:300]}

Page content (first 4000 chars):
{content[:4000]}

Return ONLY a JSON object with this exact structure:
{{
  "reference_analysis": {{
    "Original Headline": "...",
    "Original Subheadline": "...",
    "Original CTA": "...",
    "Core Offer": "...",
    "Social Proof": "...",
    "Why It Works": "..."
  }},
  "reimagined_title": "Short title for the new idea",
  "reimagined_concept": "One-paragraph description of the reimagined campaign for {company_name}"
}}
"""

    def _fetch_url(self, url: str) -> str:
        """Fetch URL content as plain text."""
        try:
            import requests
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            resp = requests.get(url, headers=headers, timeout=15)
            resp.raise_for_status()
            return resp.text
        except Exception:
            # Fallback: try urllib
            try:
                from urllib.request import urlopen, Request
                req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
                with urlopen(req, timeout=15) as response:
                    return response.read().decode("utf-8", errors="ignore")
            except Exception as e:
                raise RuntimeError(f"Failed to fetch URL {url}: {e}")

    def _safe_json_parse(self, text: str) -> dict[str, Any]:
        """Extract JSON from text, handling markdown code blocks."""
        # Try to find JSON in markdown code block
        match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
        if match:
            text = match.group(1)
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Return a minimal fallback
            return {
                "reference_analysis": {},
                "reimagined_title": "Adapted Campaign Idea",
                "reimagined_concept": text[:300] if text else "Could not parse response",
            }
