# Copy Director — Marketing Creative Pipeline

## When to Use

You are the Copywriter for a marketing creative campaign. You have `creative_specs` with hooks, angles, and formats. Your job is to generate copy variants for every creative, organized by strategic angle and language.

Each creative needs 5 angles × N languages = 5×N copy variants. The locked brief specifies the target language(s). Most campaigns have a PRIMARY language; some also specify SECONDARY languages (e.g., Marathi primary + Hinglish + Hindi). Generate copy for EVERY language listed in the locked brief. Do not guess — read the brief.

## Prerequisites

| Layer | Resource | Purpose |
|-------|----------|---------|
| Prior artifacts | `state.artifacts["creative_concept"]["creative_specs"]` | What to write for |
| Research | `state.artifacts["research"]["research_brief"]` | Insights to ground copy in |

## Copy Variant Structure

For each creative, generate these 5 angles:

| Angle | Purpose | Example Hook |
|---|---|---|
| **pain_point** | Agitate the problem | "Charged per minute. Disconnected mid-call. Still no answers." |
| **direct_benefit** | Lead with the outcome | "Complete [PRODUCT_NAME] for [CORE_OFFER_PRICE] flat. No per-minute traps." |
| **emotional** | Connect to feeling | "The anxiety of not knowing — finally, clarity." |
| **comparison** | Contrast with alternative | "[COMPETITOR_PRICE] confusion vs [CORE_OFFER_PRICE] clarity." |
| **offer_led** | Lead with price/deal | "Flat [CORE_OFFER_PRICE]. Limited slots this week." |

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

## Headlines (pick 3-5)
1. "[COMPETITOR_PRICE] confusion ke liye. [CORE_OFFER_PRICE] jawabon ke liye."
2. "Har minute charge? Nahi. Ek flat price? Haan."
3. "Pehle bill darta tha. Ab clarity milti hai."

## Body Copy
[2-3 sentences matching the angle]

## CTA
"[PRODUCT_NAME] abhi lein ->"

## Notes
- Platform: [from company_context.platform_focus]
- Character limit: Headline 60 chars, body 125 chars, CTA 30 chars
```

## Process

### Step 1: Read Creative Specs

For each creative:
- Note the primary hook
- Note the format (image 1:1, video 9:16, etc.)
- Note the platform (Instagram, Facebook, etc.)
- Note character limits for that platform

### Step 2: Generate Angles

For each creative, write all 5 angles. Each angle should feel strategically distinct:
- Pain-point: agitate, make the user feel the problem
- Direct benefit: lead with what they get
- Emotional: connect to the feeling behind the need
- Comparison: contrast explicitly with the alternative
- Offer-led: urgency or scarcity

### Step 3: Translate to Languages

For each angle, write in **ALL languages specified in the locked brief**:
1. Write each language directly (no need for English draft unless that language IS English)
2. If a language is code-switched (e.g., Hinglish), ensure natural rhythm — read aloud test is mandatory
3. If a language uses a non-Latin script (Odia, Bengali, Marathi, Malayalam, Gujarati, Telugu, Kannada, Tamil, Hindi-Devanagari), write in native script for maximum authenticity
4. Count the actual files you write. The total must equal: (number of creatives) × 5 angles × (number of languages in locked brief).

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
  "total_variants": "5 angles × 3 languages = 15 variants per creative",
  "languages": ["marathi", "hinglish", "hindi"],
  "locked_language": "[primary language from locked brief]"
}
```

**CRITICAL:** The `total_variants` field MUST be computed from actual files written, not hardcoded. Before finishing, count the `.md` files in `copy_variants/`. That count must match `creatives × 5 angles × languages`.

## Folder Structure

One folder per creative. One subfolder per angle. One `.md` file per language from the locked brief.

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
    ├── emotional/
    │   ├── marathi.md
    │   ├── hinglish.md
    │   └── hindi.md
    ├── comparison/
    │   ├── marathi.md
    │   ├── hinglish.md
    │   └── hindi.md
    └── offer_led/
        ├── marathi.md
        ├── hinglish.md
        └── hindi.md
```

**If the locked brief specifies only 1 language**, the structure has 1 file per angle instead of 3.

## Step 6: Completion Verification (MANDATORY)

Before claiming the copy stage is complete:

1. **Count actual files:** `find copy_variants/ -name "*.md" | wc -l`
2. **Verify count matches expected:** creatives × 5 angles × languages_in_locked_brief
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
