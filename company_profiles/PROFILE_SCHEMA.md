# Company Profile Schema

This document defines the schema for `company_profiles/{company_slug}.json` files. Each file is loaded at pipeline initiation and injected as `company_context` into all subagent prompts.

## Top-Level Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `company_slug` | string | yes | URL-safe identifier, e.g., `91astrology` |
| `company_name` | string | yes | Display name, e.g., `91Astrology` |
| `product_name` | string | yes | Primary product, e.g., `Nadi Report` |
| `product_description` | string | yes | One-line description of what the product does |
| `brand_voice` | string | yes | Tone and personality guidelines |
| `industry` | string | yes | Industry/category for research targeting |
| `primary_audience` | object | yes | Audience definition (see below) |
| `competitors` | array | yes | Competitor landscape (see below) |
| `pricing` | object | yes | Pricing and budget info (see below) |
| `key_differentiators` | array | yes | What makes this company unique |
| `visual_style` | object | yes | Visual direction for assets (see below) |
| `platform_focus` | array | yes | Target ad platforms |
| `formats` | array | yes | Creative formats to produce |
| `paths` | object | yes | Project directory paths relative to the `openMontage/` repo root (see below) |
| `pipeline_learnings` | object | no | Past pipeline failures and best practices |
| `copy_guidelines` | object | no | Language-specific copy rules |
| `research_sources` | object | no | Where to look for signals |

## `primary_audience`

| Field | Type | Description |
|-------|------|-------------|
| `age_range` | string | e.g., `25-45` |
| `location` | string | Geo target, e.g., `India + NRI diaspora` |
| `languages` | array | Supported languages for this company. Full list: English, Hinglish, Hindi, Odia, Bengali, Marathi, Malayalam, Gujarati, Telugu, Kannada, Tamil |
| `primary_language` | string | The dominant language. The pipeline uses the locked brief language at runtime, not the full company profile list |
| `pain_points` | array | Specific, quotable audience pain points |
| `geo_targeting` | string | Specific cities/regions for ad targeting |

## `competitors` (array of objects)

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Competitor name |
| `offering` | string | What they sell |
| `pricing_model` | string | How they charge |
| `complaints` | array | Specific audience complaints (quotable) |
| `vulnerability` | string | Where this company can win |
| `creative_strategy` | string | What ads they run (optional) |

## `pricing`

| Field | Type | Description |
|-------|------|-------------|
| `currency` | string | ISO currency code, e.g., `INR` |
| `currency_symbol` | string | Display symbol, e.g., `Rs.` |
| `core_offer` | string | Main offer with price, e.g., `Rs.1,799 FLAT` |
| `competitor_price` | string | Competitor price for contrast |
| `daily_ad_budget_range` | string | Daily spend guidance |

## `visual_style`

| Field | Type | Description |
|-------|------|-------------|
| `mood` | string | Overall emotional tone |
| `colors` | string | Color palette direction |
| `lighting` | string | Lighting style |
| `constraints` | array | Hard rules, e.g., `No human faces in generated images` |

## `paths`

| Field | Type | Description |
|-------|------|-------------|
| `idea_pool` | string | Relative path to idea pool directory (e.g., `../91_astro/ideas/`) |
| `project_root` | string | Root directory for campaign outputs (e.g., `../91_astro/`) |

## `pipeline_learnings`

| Field | Type | Description |
|-------|------|-------------|
| `v1_failures` | array | Past failures with fix descriptions |
| `best_practices` | array | What has worked well |

## Example

See `company_profiles/91astrology.json` for a fully populated example.
