# Marketing-Creative Pipeline — Claude Code Prompt Template

## How to use this file

1. Fill in the placeholders below (CAMPAIGN_ID, COMPANY, INPUT, etc.)
2. Copy ONLY the gray block under "PASTE THIS INTO CLAUDE CODE"
3. Paste it into your Claude Code chat
4. Do NOT include this header text or the instructions — only the gray block

---

## FILL IN THESE VALUES FIRST

| Variable | Value | Example |
|---|---|---|
| CAMPAIGN_ID | Kebab-case name | `marriage-signs-nadi` |
| COMPANY_SLUG | Company profile slug | `91astrology` |
| COMPANY_DIR | Output directory name | `91_astro` |
| INPUT_FLAG | One of the four below | `--input-image "C:\path\to.png"` |
| NUM_IMAGES | Images per creative | `1` |
| MODEL | Image model | `auto`, `openai_image`, `gemini_image` |

### Pick ONE input option:

**Text:** `--input-text "A campaign about..."`

**Image:** `--input-image "C:\Users\...\image.png"`

**URL:** `--input-url https://example.com/landing`

**Idea pool:** `--idea-id idea-01`

---

## PASTE THIS INTO CLAUDE CODE

```
You are in the OpenMontage directory. Run the marketing-creative pipeline end-to-end.

RULES:
- Do NOT read AGENT_GUIDE.md.
- Do NOT run preflight or discover tools.
- Do NOT search for files or restore from git.
- Do NOT explain what you are doing.
- Do NOT ask for approval.

STEP 1: Run this PowerShell command:

python -m pipelines.marketing_creative `
  --campaign-id CAMPAIGN_ID `
  --company COMPANY_SLUG `
  INPUT_FLAG `
  --auto `
  --num-images NUM_IMAGES `
  --model MODEL

STEP 2: Parse the JSON. If action is "spawn_subagent", spawn the subagent with the exact prompt from the JSON.

STEP 3: When the subagent finishes, run this resume command:

python -m pipelines.marketing_creative `
  --campaign-id CAMPAIGN_ID `
  --company COMPANY_SLUG `
  --resume `
  --auto

STEP 4: Repeat Steps 2-3 until JSON says {"action": "complete"}.

STEP 5: List all files in ../COMPANY_DIR/campaigns/CAMPAIGN_ID/ and present them.

DO NOTHING ELSE.
```

---

## Example (filled in)

**Variables:**
- CAMPAIGN_ID = `marriage-signs-nadi`
- COMPANY_SLUG = `91astrology`
- COMPANY_DIR = `91_astro`
- INPUT_FLAG = `--input-image "C:\Users\91829\Downloads\Instagram post - 2485.png"`
- NUM_IMAGES = `2`
- MODEL = `openai_image`

**What to paste:**

```
You are in the OpenMontage directory. Run the marketing-creative pipeline end-to-end.

RULES:
- Do NOT read AGENT_GUIDE.md.
- Do NOT run preflight or discover tools.
- Do NOT search for files or restore from git.
- Do NOT explain what you are doing.
- Do NOT ask for approval.

STEP 1: Run this PowerShell command:

python -m pipelines.marketing_creative `
  --campaign-id marriage-signs-nadi `
  --company 91astrology `
  --input-image "C:\Users\91829\Downloads\Instagram post - 2485.png" `
  --auto `
  --num-images 2 `
  --model openai_image

STEP 2: Parse the JSON. If action is "spawn_subagent", spawn the subagent with the exact prompt from the JSON.

STEP 3: When the subagent finishes, run this resume command:

python -m pipelines.marketing_creative `
  --campaign-id marriage-signs-nadi `
  --company 91astrology `
  --resume `
  --auto

STEP 4: Repeat Steps 2-3 until JSON says {"action": "complete"}.

STEP 5: List all files in ../91_astro/campaigns/marriage-signs-nadi/ and present them.

DO NOTHING ELSE.
```
