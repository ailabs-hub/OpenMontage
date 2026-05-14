# Marketing-Creative Pipeline — Agent-Native Prompt Template

Copy this entire block into your Claude Code / Kimi chat. Fill in the placeholders first.

---

## PASTE THIS INTO CLAUDE CODE / KIMI

```
Run the marketing-creative pipeline for 91astrology.

MANDATORY RULES — FOLLOW EXACTLY:
- DO NOT read AGENT_GUIDE.md.
- DO NOT spawn subagents.
- DO NOT use Claude built-in image tools (openai_image, google_imagen, etc.).
- DO NOT run preflight unless the assets stage requires it.
- DO NOT search for company profiles, schemas, or manifests.
- DO NOT restore files from git history.
- DO NOT explain what you are doing.
- DO NOT ask me for approval between stages.
- Execute every stage yourself in one continuous session.

STEP 1 — Read the pipeline driver skill:

Read: skills/pipelines/marketing-creative/agent-pipeline-driver.md

STEP 2 — Initialize the session. Run this exact command:

python -c "
from pipelines.marketing_creative.agent_utils import init_session
print(init_session('shocked-by-life-problems', '91astrology', 'raw_input', research=False, num_images=2, model='auto', input_data='C:\Users\91829\Downloads\Instagram post - 2463.png'))
"

This returns the campaign directory path.

STEP 3 — Load the company profile:

python -c "
from pipelines.marketing_creative.agent_utils import load_company_profile
import json
print(json.dumps(load_company_profile('91astrology'), indent=2))
"

STEP 4 — Execute all stages sequentially. For each stage in the sequence:

A. Check if already complete:
   python -c "from pipelines.marketing_creative.agent_utils import is_stage_complete; print(is_stage_complete('shocked-by-life-problems', '91astrology', 'STAGE_ID'))"

B. If False, get the skill path:
   python -c "from pipelines.marketing_creative.agent_utils import get_stage_skill_path; print(get_stage_skill_path('STAGE_ID'))"

C. Read the skill file and follow its instructions exactly.

D. Load inputs (resolve paths via agent_utils.resolve_stage_inputs()).

E. Execute creative work and write all outputs.

F. Mark stage complete:
   python -c "from pipelines.marketing_creative.agent_utils import mark_stage_complete; mark_stage_complete('shocked-by-life-problems', '91astrology', 'STAGE_ID')"

G. Immediately proceed to the next stage. Do NOT pause.

STEP 5 — For image generation (assets stage), run variant selection first, then generate:

A. Select top variants:
python -c "
from pipelines.marketing_creative.agent_utils import select_variants_for_generation
import json
selected = select_variants_for_generation('shocked-by-life-problems', '91astrology')
print(json.dumps(selected, indent=2))
"

B. Check session config to confirm image budget:
python -c "from pipelines.marketing_creative.agent_utils import get_session_status; import json; print(json.dumps(get_session_status('shocked-by-life-problems', '91astrology'), indent=2))"

C. For EACH selected variant, generate an image using the standalone script:

1. Write a JSON config file:
```json
{
  "prompt": "[your optimized Visual Brief prompt for this variant]",
  "width": 1024,
  "height": 1024,
  "output_path": "../91_astro/campaigns/shocked-by-life-problems/assets/VARIANT_ID.png",
  "provider": "image_selector",
  "preferred_provider": "openai"
}
```

2. Run the generation script:
```bash
python OpenMontage/tools/generate_image.py ../91_astro/campaigns/shocked-by-life-problems/assets/VARIANT_ID_config.json
```

**Alternative — direct OpenAI (GPT Image 2):**
Use `"provider": "openai_image"` and `"model": "gpt-image-2"` instead of `"provider": "image_selector"`.

STEP 6 — After all stages complete, list all files in ../91_astro/campaigns/shocked-by-life-problems/ and present the deliverables.

DO NOTHING ELSE.
```

---

## PLACEHOLDERS — FILL THESE IN BEFORE PASTING

| Placeholder | What to put | Example |
|---|---|---|
| `shocked-by-life-problems` | Kebab-case campaign name | `marriage-patterns-nadi` |
| `raw_input` | `"raw_input"` or `"idea_pool"` | `"raw_input"` |
| `C:\Users\91829\Downloads\Instagram post - 2463.png` | Raw text, image path, URL, or idea_id | `C:\Users\...\image.png` |
| `False` | `True` or `False` (default: False) | `False` |
| `2` | **Total** images across all creatives (default: 3) | `3` |
| `auto` | Image model (default: auto) | `auto` |
| `openai` | Provider for image_selector: `auto`, `openai` (GPT Image 2), `flux` | `auto` |

### Input source options

**Raw input** (text, image, or URL — the agent handles all three):
```
INPUT_SOURCE = "raw_input"
INPUT_DATA = "your text here"               # for text
INPUT_DATA = "C:\path\to\image.png"        # for image
INPUT_DATA = "https://example.com/page"    # for URL
```

**Idea pool** (provide the idea_id):
```
INPUT_SOURCE = "idea_pool"
INPUT_DATA = "idea-01"
```

**num_images is the TOTAL image budget**, not per-creative. The pipeline intelligently selects which copy variants get images based on company learnings.

---

## EXAMPLE — FILLED IN

```
Run the marketing-creative pipeline for 91astrology.

MANDATORY RULES — FOLLOW EXACTLY:
- DO NOT read AGENT_GUIDE.md.
- DO NOT spawn subagents.
- DO NOT use Claude built-in image tools (openai_image, google_imagen, etc.).
- DO NOT run preflight unless the assets stage requires it.
- DO NOT search for company profiles, schemas, or manifests.
- DO NOT restore files from git history.
- DO NOT explain what you are doing.
- DO NOT ask me for approval between stages.
- Execute every stage yourself in one continuous session.

STEP 1 — Read the pipeline driver skill:

Read: skills/pipelines/marketing-creative/agent-pipeline-driver.md

STEP 2 — Initialize the session. Run this exact command:

python -c "
from pipelines.marketing_creative.agent_utils import init_session
print(init_session('marriage-patterns-nadi', '91astrology', 'raw_input', research=False, num_images=3, model='auto', input_data=''))
"

This returns the campaign directory path.

STEP 3 — Load the company profile:

python -c "
from pipelines.marketing_creative.agent_utils import load_company_profile
import json
print(json.dumps(load_company_profile('91astrology'), indent=2))
"

STEP 4 — Execute all stages sequentially. For each stage in the sequence:

A. Check if already complete:
   python -c "from pipelines.marketing_creative.agent_utils import is_stage_complete; print(is_stage_complete('marriage-patterns-nadi', '91astrology', 'STAGE_ID'))"

B. If False, get the skill path:
   python -c "from pipelines.marketing_creative.agent_utils import get_stage_skill_path; print(get_stage_skill_path('STAGE_ID'))"

C. Read the skill file and follow its instructions exactly.

D. Load inputs (resolve paths via agent_utils.resolve_stage_inputs()).

E. Execute creative work and write all outputs.

F. Mark stage complete:
   python -c "from pipelines.marketing_creative.agent_utils import mark_stage_complete; mark_stage_complete('marriage-patterns-nadi', '91astrology', 'STAGE_ID')"

G. Immediately proceed to the next stage. Do NOT pause.

STEP 5 — For image generation (assets stage), run variant selection first, then generate:

A. Select top variants:
python -c "
from pipelines.marketing_creative.agent_utils import select_variants_for_generation
import json
selected = select_variants_for_generation('marriage-patterns-nadi', '91astrology')
print(json.dumps(selected, indent=2))
"

B. Check session config to confirm image budget:
python -c "from pipelines.marketing_creative.agent_utils import get_session_status; import json; print(json.dumps(get_session_status('marriage-patterns-nadi', '91astrology'), indent=2))"

C. For EACH selected variant, generate an image using the standalone script:

1. Write a JSON config file:
```json
{
  "prompt": "[your optimized Visual Brief prompt for this variant]",
  "width": 1024,
  "height": 1024,
  "output_path": "../91_astro/campaigns/marriage-patterns-nadi/assets/VARIANT_ID.png",
  "provider": "image_selector",
  "preferred_provider": "openai"
}
```

2. Run the generation script:
```bash
python OpenMontage/tools/generate_image.py ../91_astro/campaigns/marriage-patterns-nadi/assets/VARIANT_ID_config.json
```

STEP 6 — After all stages complete, list all files in ../91_astro/campaigns/marriage-patterns-nadi/ and present the deliverables.

DO NOTHING ELSE.
```
