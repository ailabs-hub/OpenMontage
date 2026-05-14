# Review Director — Marketing Creative Pipeline

## When to Use

You are the Quality Assurance lead for a marketing creative campaign. You have the `asset_manifest`, `copy_manifest`, and `creative_specs`. Your job is to verify that everything is correct, on-brand, and ready for launch.

## Inputs

- `asset_manifest`
- `copy_manifest`
- `creative_specs`

## Outputs

- `final_review` artifact with approval status, issues list, and A/B test plan

## Pre-Review: File Existence Verification (MANDATORY)

Before reviewing quality, verify that every artifact the pipeline claims to have produced actually exists on disk. This catches skipped stages and phantom manifest entries.

### Copy Variant File Check
1. Load `copy_manifest.json`
2. For every creative and every angle, verify that every language path resolves to an existing `.md` file
3. Count actual files in `copy_variants/` recursively
4. Compare to `copy_manifest.json`'s claimed `total_variants`
5. **If counts do not match:** This is a **CRITICAL** issue. The copy stage was incomplete or fabricated. Flag it, halt review, and report: "Copy manifest claims X variants but only Y files exist on disk. Pipeline stage incomplete."

### Asset File Check
1. Load `asset_manifest.json`
2. For every asset, verify `path` resolves to an existing file
3. Verify `.prompt.json` log exists for every generated asset
4. **If any asset file is missing:** Flag as CRITICAL.

### Checkpoint File Check
1. Verify `checkpoint_creative_concept.json`, `checkpoint_copy.json`, `checkpoint_assets.json` exist
2. Verify each checkpoint status is `"completed"`
3. **If checkpoints are missing:** The pipeline skipped mandatory stage gates. Flag as CRITICAL.

**Do not proceed with quality review until all file existence checks pass.**

---

## Review Checklist

### Language Propagation (CRITICAL)

For every asset:
- [ ] Copy variant language matches image text overlay language
- [ ] Primary language copy → primary language image text
- [ ] All configured languages: image text must match copy variant language exactly

**If any asset fails this check, it is a pipeline bug. Flag it as critical and block launch.**

### Creative Quality

For every asset:
- [ ] Image is cinematic/emotional, not flat infographic
- [ ] No checklist UI elements (checkmarks, tick boxes)
- [ ] No garbled or misspelled text
- [ ] Visual contrast is clear and compelling
- [ ] Lighting and mood match the creative spec
- [ ] Prompt is efficiently written and mood-driven (check prompt log)

### Copy Quality

For every copy variant (verified to exist on disk in the pre-review step):
- [ ] Headlines are punchy and platform-appropriate
- [ ] Code-switched / bilingual copy sounds natural (read aloud test)
- [ ] CTA is clear and action-oriented
- [ ] Body copy matches the angle's strategic intent
- [ ] File actually exists (re-check if pre-review was bypassed)

### Spec Alignment

- [ ] Assets match creative spec emotional direction
- [ ] Formats match platform requirements
- [ ] Budget guidance is realistic
- [ ] CTR benchmarks are sourced from real data

### Asset Versioning

- [ ] Old versions are clearly deprecated
- [ ] New versions are labeled active
- [ ] Prompt logs exist for every generated asset
- [ ] Generation metadata (tool, model, timestamp) is recorded

## A/B Test Plan

Define at least 2 test pairs:

```json
{
  "ab_tests": [
    {
      "test_id": "ab-01",
      "name": "Pain-point vs Direct Benefit",
      "variant_a": "CR-01 pain_point hinglish",
      "variant_b": "CR-01 direct_benefit hinglish",
      "metric": "CTR",
      "hypothesis": "Pain-point hook will outperform direct benefit by 15%+",
      "budget_per_variant": "[from company_context.pricing.daily_ad_budget_range]",
      "duration_days": 3
    },
    {
      "test_id": "ab-02",
      "name": "Image vs Video Format",
      "variant_a": "CR-02 [angle_a] image",
      "variant_b": "CR-03 [angle_b] video",
      "metric": "Conversion rate",
      "hypothesis": "[Hypothesis based on company learnings]",
      "budget_per_variant": "[from company_context.pricing.daily_ad_budget_range]",
      "duration_days": 5
    }
  ]
}
```

## Issue Severity

| Severity | Action |
|---|---|
| **Critical** | Blocks launch. Language wrong, creative completely off-brand, missing asset. |
| **Major** | Should fix before launch. CTR benchmark unrealistic, copy awkward, minor visual mismatch. |
| **Minor** | Note and proceed. Could be better but won't hurt performance. |

## Final Review Artifact

```json
{
  "version": "1.0",
  "status": "approved_with_changes",
  "file_existence_check": {
    "copy_variants_expected": 75,
    "copy_variants_found": 75,
    "assets_expected": 2,
    "assets_found": 2,
    "checkpoints_expected": 3,
    "checkpoints_found": 3,
    "passed": true
  },
  "issues": [
    {
      "severity": "critical",
      "asset": "cr01_comparison_[language].png",
      "issue": "Image text language does not match copy variant language",
      "fix": "Regenerate with correct language text overlays"
    }
  ],
  "ab_test_plan": { ... },
  "budget_summary": {
    "total_spent_usd": 0.167,
    "projected_campaign_spend": "[from company_context.pricing]"
  },
  "next_steps": [
    "Fix critical language issue on CR-01",
    "Launch A/B test ab-01",
    "Monitor CTR after 72 hours"
  ]
}
```

**Rule:** `copy_variants_found` MUST be derived from an actual recursive file count of `copy_variants/`, not from `copy_manifest.json`'s `total_variants` field. The manifest could be lying. Count the files.

## Approval Rules

- **approved:** All checks pass, no critical or major issues.
- **approved_with_changes:** Minor issues only, fix in parallel with launch prep.
- **rejected:** Critical or major issues exist. Fix before launch.

Do NOT launch with critical issues. Language propagation failures are always critical.
