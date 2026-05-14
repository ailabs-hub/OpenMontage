"""Generate a filled pipeline prompt from the template.

Usage:
    python generate_prompt.py \
        --campaign-id marriage-signs-nadi \
        --input-source raw_input \
        --num-images 2

Output is printed to stdout. Pipe to file or copy manually.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


def slugify(text: str) -> str:
    """Convert text to kebab-case slug."""
    return re.sub(r"[^\w\s-]", "", text).strip().lower().replace(" ", "-")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fill the pipeline prompt template and print to stdout.",
    )
    parser.add_argument(
        "--campaign-id",
        required=True,
        help="Campaign identifier (e.g., marriage-signs-nadi). Auto-slugified if spaces.",
    )
    parser.add_argument(
        "--input-source",
        choices=["raw_input", "idea_pool"],
        default="raw_input",
        help="Input type: raw_input (text/image/URL) or idea_pool (default: raw_input)",
    )
    parser.add_argument(
        "--research",
        action="store_true",
        help="Enable research stage (default: False)",
    )
    parser.add_argument(
        "--input-data",
        default="",
        help="Raw input: text, image path, URL, or idea_id (default: empty)",
    )
    parser.add_argument(
        "--num-images",
        type=int,
        default=3,
        help="Total images across all creatives (default: 3)",
    )
    parser.add_argument(
        "--model",
        default="auto",
        help="Image model: auto, flux_image, openai_image, etc. (default: auto)",
    )
    parser.add_argument(
        "--preferred-provider",
        default="auto",
        dest="preferred_provider",
        help="Provider passed to image_selector: auto, openai, flux, etc. (default: auto). Use 'openai' for GPT Image 2.",
    )
    parser.add_argument(
        "--company",
        default="91astrology",
        help="Company slug (default: 91astrology)",
    )
    parser.add_argument(
        "--template",
        type=Path,
        default=None,
        help="Path to template file (default: ../PIPELINE_PROMPT_TEMPLATE.md)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Write output to file instead of stdout",
    )

    args = parser.parse_args()

    # Resolve template path.
    if args.template:
        template_path = args.template
    else:
        # Template lives one directory above OpenMontage root.
        template_path = Path(__file__).resolve().parent.parent / "PIPELINE_PROMPT_TEMPLATE.md"

    if not template_path.exists():
        print(f"error: template not found: {template_path}", file=sys.stderr)
        return 1

    # Slugify campaign id.
    campaign_id = slugify(args.campaign_id)

    # Build replacements.
    replacements = {
        "{{CAMPAIGN_ID}}": campaign_id,
        "{{INPUT_SOURCE}}": args.input_source,
        "{{INPUT_DATA}}": args.input_data,
        "{{RESEARCH}}": str(args.research),
        "{{NUM_IMAGES}}": str(args.num_images),
        "{{MODEL}}": args.model,
        "{{PREFERRED_PROVIDER}}": args.preferred_provider,
    }

    # Read template.
    template = template_path.read_text(encoding="utf-8")

    # Replace placeholders.
    for placeholder, value in replacements.items():
        template = template.replace(placeholder, value)

    # Also replace the company slug if it's not 91astrology.
    if args.company != "91astrology":
        template = template.replace("91astrology", args.company)
        # Update campaign dir path if company slug changed.
        template = template.replace(
            f"../91_astro/campaigns/{campaign_id}",
            f"../{args.company}/campaigns/{campaign_id}",
        )

    # Output.
    if args.output:
        args.output.write_text(template, encoding="utf-8")
        print(f"Prompt written to: {args.output}", file=sys.stderr)
    else:
        print(template)

    return 0


if __name__ == "__main__":
    sys.exit(main())
