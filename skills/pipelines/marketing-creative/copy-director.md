# Copy Director — Marketing Creative Pipeline

## When to Use

You are the Copywriter for a marketing creative campaign. You have `creative_specs` with hooks, angles, and formats. Your job is to generate copy variants for every creative, organized by strategic angle and language.

Each creative needs 2-3 angles × N languages = 2-3×N copy variants. The locked brief specifies the target language(s). Most campaigns have a PRIMARY language; some also specify SECONDARY languages (e.g., Marathi primary + Hinglish + Hindi). Generate copy for EVERY language listed in the locked brief. Do not guess — read the brief.

Generate ONLY the angles that best serve each creative's hook. Do not default to all 5.

## Prerequisites

| Layer | Resource | Purpose |
|-------|----------|---------|
| Prior artifacts | `state.artifacts["creative_concept"]["creative_specs"]` | What to write for |
| Research | `state.artifacts["research"]["research_brief"]` | Insights to ground copy in |

## Copy Variant Structure

For each creative, SELECT the 2-3 best angles based on the hook. Do not default to all 5.

| Angle | When to Use | Purpose | Example Hook |
|---|---|---|---|
| **pain_point** | Almost always — strongest angle | Agitate the problem | "Charged per minute. Disconnected mid-call. Still no answers." |
| **direct_benefit** | Almost always — second strongest | Lead with the outcome | "Complete [PRODUCT_NAME] for [CORE_OFFER_PRICE] flat. No per-minute traps." |
| **emotional** | When hook is feeling-driven | Connect to feeling | "The anxiety of not knowing — finally, clarity." |
| **comparison** | When there's a clear alternative | Contrast with alternative | "[COMPETITOR_PRICE] confusion vs [CORE_OFFER_PRICE] clarity." |
| **offer_led** | When price/deal is the differentiator | Lead with price/deal | "Flat [CORE_OFFER_PRICE]. Limited slots this week." |

**Selection Rule:** For each creative, read its hook and visual_direction. Pick ONLY the angles that amplify that specific hook:
- If the hook is about solving a frustration → pain_point + direct_benefit (+ emotional if it resonates)
- If the hook is about feeling/transformative → pain_point + emotional (+ direct_benefit)
- If the hook is about price advantage → pain_point + comparison + offer_led
- If the hook is about trust/reliability → pain_point + direct_benefit + comparison

**Minimum 2 angles. Maximum 3 angles. Never all 5.**

For each angle, generate copy in **every language** specified in the locked brief. The locked brief overrides the company profile language list. If the brief lists only one language, generate only that language. If the brief lists multiple languages (e.g., Marathi primary + Hinglish secondary + Hindi tertiary), generate ALL of them. Do not omit secondary languages to save time.

## Code-Switching / Bilingual Guidelines

If the company profile includes a code-switched language (e.g., Hinglish for Indian audiences), it is the PRIMARY language. It is NOT literal translation. It is natural code-switching as spoken in the target region.

**Good code-switched copy (example: Hinglish):**
- "Apna report abhi lein ->"
- "Call cut gayi. Jawab nahi."
- "Ek poori report. Poori clarity."
- "Har minute charge — yehi toh problem hai."

**Bad code-switched copy (literal translation):**
- "Please take your report now" (too formal)
- "Call was disconnected. There is no answer." (grammatical but unnatural)
- "One complete report. Complete clarity." (stiff)

**Rules:**
- Use common local words that match the target region's spoken rhythm
- Keep English for numbers, brand names, and concepts: "[CORE_OFFER_PRICE]", "report", "clarity"
- Match spoken rhythm, not written grammar
- When in doubt, read the copy aloud — does it sound like a natural conversation in the target region?

## Copy Variant File Format

Each `.md` file contains:

```markdown
# Copy Variant: CR-01 | Angle: comparison | Language: [primary_language]

## Headline (1 best option)
"[COMPETITOR_PRICE] confusion ke liye. [CORE_OFFER_PRICE] jawabon ke liye."

## Body Copy
1-2 short punchy sentences, max 100 characters. This is social media ad caption text, not a blog post.

## CTA
"[PRODUCT_NAME] abhi lein ->"

## Notes
- Platform: [from company_context.platform_focus]
- Character limit: Headline 60 chars, body 100 chars, CTA 30 chars
```

## Process

### Step 1: Read Creative Specs

For each creative:
- Note the primary hook
- Note the format (image 1:1, video 9:16, etc.)
- Note the platform (Instagram, Facebook, etc.)
- Note character limits for that platform

### Step 2: Generate Angles

For each creative, write ONLY the 2-3 strongest angles. Use the selection table above to decide which angles best serve THIS creative's hook. Each selected angle should feel strategically distinct from the others.

### Step 3: Translate to Languages

For each angle, write in **ALL languages specified in the locked brief**:
1. Write each language directly (no need for English draft unless that language IS English)
2. If a language is code-switched (e.g., Hinglish), ensure natural rhythm — read aloud test is mandatory
3. If a language uses a non-Latin script (Odia, Bengali, Marathi, Malayalam, Gujarati, Telugu, Kannada, Tamil, Hindi-Devanagari), write in native script for maximum authenticity
4. Count the actual files you write. The total must equal: (number of creatives) × (2-3 angles per creative) × (number of languages in locked brief).
5. **ONE headline per variant.** Do not provide multiple headline options.
6. **Body copy: 1-2 short punchy sentences MAX.** This is social media ad text, not a blog post. Max 100 characters.
7. **NO visual direction in copy variants.** Visual decisions are the asset stage's job.

**Every language in the locked brief is mandatory.** If the brief specifies Marathi + Hinglish + Hindi, you must generate all three. Do not skip secondary languages to save time or tokens.

### Step 4: Verify Naturalness

Read every copy variant aloud in the locked language. Ask:
- Does this sound like how the target audience would actually say it?
- Is the code-switching natural or forced? (for Hinglish)
- Is the native script correct and natural? (for regional languages)
- Would this work in a social media caption or messaging app?

If unnatural, rewrite. Do not ship stiff copy.

### Step 5: Build Copy Manifest

```json
{
  "version": "1.0",
  "creatives": [
    {
      "creative_id": "CR-01",
      "creative_name": "Trust Contrast",
      "angles": {
        "pain_point": {
          "marathi": "copy_variants/cr01_trust_contrast/pain_point/marathi.md",
          "hinglish": "copy_variants/cr01_trust_contrast/pain_point/hinglish.md",
          "hindi": "copy_variants/cr01_trust_contrast/pain_point/hindi.md"
        },
        "direct_benefit": { ... },
        "emotional": { ... },
        "comparison": { ... },
        "offer_led": { ... }
      }
    }
  ],
  "total_variants": "2-3 angles × 3 languages = 6-9 variants per creative",
  "languages": ["marathi", "hinglish", "hindi"],
  "locked_language": "[primary language from locked brief]"
}
```

**CRITICAL:** The `total_variants` field MUST be computed from actual files written, not hardcoded. Before finishing, count the `.md` files in `copy_variants/`. That count must match `creatives × (actual angles generated) × languages`.

## Folder Structure

One folder per creative. One subfolder per SELECTED angle (2-3 angles, not all 5). One `.md` file per language from the locked brief.

```
copy_variants/
└── cr01_trust_contrast/
    ├── pain_point/
    │   ├── marathi.md
    │   ├── hinglish.md
    │   └── hindi.md
    ├── direct_benefit/
    │   ├── marathi.md
    │   ├── hinglish.md
    │   └── hindi.md
    └── emotional/
        ├── marathi.md
        ├── hinglish.md
        └── hindi.md
```

**PATH RULE:** Write `copy_variants/` directly inside the campaign directory, NOT inside `artifacts/`.

**If the locked brief specifies only 1 language**, the structure has 1 file per angle instead of 3.

## Step 6: Completion Verification (MANDATORY)

Before claiming the copy stage is complete:

1. **Count actual files:** `find copy_variants/ -name "*.md" | wc -l`
2. **Verify count matches expected:** creatives × (actual angles generated) × languages_in_locked_brief
3. **Verify manifest paths resolve:** Every path in `copy_manifest.json` must point to an existing file
4. **If any check fails:** The stage is NOT complete. Generate missing files before proceeding.

**Do not write `copy_manifest.json` with phantom paths.** Only include paths to files that actually exist on disk.

## Common Pitfalls

- **Literal translation for code-switched languages:** Direct translation from English is not natural code-switching. Match spoken rhythm.
- **Same headline across angles:** Each angle should have a distinct strategic voice.
- **Ignoring platform limits:** Different platforms have different caption constraints.
- **Forgetting the CTA:** Every variant needs a clear call-to-action.
- **Uneven quality:** Primary language gets 80% of the polish. Other languages are secondary but still must be good.
- **Phantom manifest entries:** Claiming 75 variants but only writing 3 files. Always verify file existence.
