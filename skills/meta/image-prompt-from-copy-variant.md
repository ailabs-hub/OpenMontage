# Image Prompt Generation from Copy Variants

Use this skill when generating image prompts from a selected copy variant in the OpenMontage pipeline. This prevents the common failure mode where the pipeline produces over-specified, creatively dead images.

## The Failure Pattern

**What goes wrong:** The agent reads the creative spec (which has detailed visual direction, UI elements, checkmarks, fonts) and dumps all of that into the image generation prompt. The result is a generic infographic that looks like every other template ad.

**Why it happens:** The creative spec is written for a *human designer* or *video editor* — someone who interprets mood and makes creative decisions. An image generation model is not a designer. It needs emotional direction and visual freedom, not design specifications.

**What the user sees:** A flat, sterile image with checklist UI elements instead of a compelling visual story.

---

## The Fix: Visual Brief Pattern

Instead of translating the creative spec directly into an image prompt, generate a **Visual Brief** that combines:

1. **Emotional core** from the creative spec (mood, contrast, story)
2. **Key phrases** from the selected copy variant (headlines → image text overlays)
3. **Language lock** from the selected copy variant (copy language → image text in same language)
4. **Visual anchor** — one or two defining visual elements, not a full UI spec

### What to INCLUDE in the image prompt

| Include | Example |
|---|---|
| Mood and atmosphere | "dark, anxious, unfair" vs "warm, calm, trustworthy" |
| Story contrast | "chaos versus order" / "betrayal versus relief" |
| 1-2 defining visual elements | "cracked phone" / "elegant document with gold seal" |
| Text overlays IN THE COPY VARIANT LANGUAGE | Copy language → matching image text language |
| Color palette direction with hex codes | "deep reds and blacks (#8B0000, #1A1A1A)" / "sage greens and creams (#9DC183, #F5F5DC)" |
| Lighting style (named pattern) | "harsh overhead shadows" / "soft warm ambient light" / "Rembrandt lighting" |
| Camera/Technical layer | "Shot on Sony A7IV with 35mm lens at f/2.8, shallow depth of field, Kodak Portra 400 film emulation" |

### What to EXCLUDE from the image prompt

| Exclude | Why |
|---|---|
| "Three green checkmarks" | The model will draw literal checkboxes. Boring. |
| "Clean sans-serif font" | The model cannot reliably render specific fonts. |
| "Soft gradient transition" | Over-prescribed. Let the model handle transitions. |
| Full UI specifications | This turns the image into a wireframe, not an ad. |
| Every element from the creative spec | The spec is for humans. The prompt is for the model. |

---

## Step-by-Step: From Copy Variant to Image Prompt

### Step 1: Select the copy variant

You have chosen:
- Creative: CR-01 [Creative Name]
- Angle: [Selected Angle]
- Language: [Selected Language] (primary)

### Step 2: Extract the emotional core

Read the creative spec for MOOD only. Ignore UI details.

From the CR-01 spec:
> "LEFT side: dark, chaotic visuals... anxious face in dim light... RIGHT side: warm amber light, clean desk... calm handwriting..."

Extract: **Chaos vs. Calm. Anxiety vs. Trust.**

### Step 3: Extract key phrases for image text

From the selected copy variant headlines:

> "[COMPETITOR_PRICE] confusion ke liye. [CORE_OFFER_PRICE] jawabon ke liye."

Select the SHORTEST, most visual phrase for the image. Do not put the full headline in the image — it will be in the ad caption.

For a comparison image, use:
- Left: "[COMPETITOR_PRICE]" + short pain phrase
- Right: "[CORE_OFFER_PRICE]" + short clarity phrase

### Step 4: Lock the language

**CRITICAL:** The image text overlays MUST be in the same language as the copy variant.

**Supported languages:** English, Hinglish, Hindi, Odia, Bengali, Marathi, Malayalam, Gujarati, Telugu, Kannada, Tamil.

**Regional language note:** If the locked language uses a non-Latin script (Odia, Bengali, Marathi, Malayalam, Gujarati, Telugu, Kannada, Tamil, Hindi-Devanagari), explicitly specify the script in the prompt: "text overlay in [Language] script" or "text in [Script] script". Example: "text overlay in Bengali script" or "text in Telugu script".

**Model guidance for regional languages:**
- GPT Image 2: Handles Devanagari (Hindi, Marathi) and major Indic scripts reasonably well
- Gemini Image: Explicitly supports high-fidelity text rendering in CJK, Devanagari, Arabic, and other scripts — use for best regional language results
- Seedream 4.5: Strong multilingual prompt understanding and accurate typography

If the copy is code-switched (e.g., Hinglish), do not write pure English in the image.
Example: Instead of "Bill: [COMPETITOR_PRICE]" (English), write "Bill: [COMPETITOR_PRICE] — jawab nahi" (matching the code-switched language).

Use short phrases in the locked language:
- Left side pain phrase
- Right side clarity phrase

### Step 5: Write the prompt using the Visual Brief formula (with Camera/Technical layer)

```
[Emotional contrast] +
[Visual anchor 1] + [Visual anchor 2] +
[Text overlays in locked language] +
[Mood words] +
[Lighting] +
[Camera/Technical: shot type, lens, aperture, film stock, depth of field]
```

**The Camera/Technical layer is MANDATORY.** Every prompt must include:
- **Shot type:** close-up, medium shot, wide shot, establishing shot
- **Framing:** rule-of-thirds, centered, leading-lines
- **Angle:** eye-level, low-angle, high-angle
- **Lens:** e.g., 35mm, 50mm, 85mm
- **Aperture:** e.g., f/1.4, f/2.8
- **Depth of field:** shallow, deep
- **Film stock emulation:** e.g., Kodak Portra 400

**Example (good — with full Camera/Technical layer):**

> A cinematic split-screen advertisement. LEFT SIDE feels dark and anxious: a damaged phone on a rough surface with a glaring billing alert, moody lighting, tense atmosphere. RIGHT SIDE feels warm and trustworthy: an elegant document with ornate gold details resting on a clean wooden surface beside a fountain pen, soft ambient light, serene mood. [Locked language] text overlays on the left: short pain phrase. [Locked language] text on the right: short clarity phrase. Deep reds and blacks on the left, sage greens and warm creams on the right. Shot on Sony A7IV with 35mm lens at f/2.8, shallow depth of field, cinematic color grading, Kodak Portra 400 film emulation. Photorealistic, premium advertising aesthetic.

**Example (bad — missing Camera/Technical layer — what NOT to do):**

> A cinematic split-screen advertisement. LEFT SIDE feels dark and anxious... RIGHT SIDE feels warm and trustworthy... Deep reds and blacks on the left, sage greens and warm creams on the right. Photorealistic, premium advertising aesthetic.

*Why bad:* No shot type, no lens, no aperture, no film stock. GPT Image 2 will produce a flat, generic image instead of a cinematic ad.

**Example (bad — what NOT to do):**

> A clean infographic with a left side showing a phone interface with timer "14:32", red "DISCONNECTED" stamp, "Bill: [COMPETITOR_PRICE]" in alarming red, three green checkmarks with text "[FEATURE_1]", "[FEATURE_2]", "[FEATURE_3]", soft gradient divider, modern flat vector design...

---

## Language Propagation Rule

| Copy Variant Language | Image Text Overlays | Script | Ad Caption Copy |
|---|---|---|---|
| English | English | Latin | English |
| Hinglish | Hinglish | Latin + Devanagari mix | Hinglish |
| Hindi | Hindi | Devanagari | Hindi |
| Odia | Odia | Odia script | Odia |
| Bengali | Bengali | Bengali script | Bengali |
| Marathi | Marathi | Devanagari | Marathi |
| Malayalam | Malayalam | Malayalam script | Malayalam |
| Gujarati | Gujarati | Gujarati script | Gujarati |
| Telugu | Telugu | Telugu script | Telugu |
| Kannada | Kannada | Kannada script | Kannada |
| Tamil | Tamil | Tamil script | Tamil |

**The pipeline must enforce this.** If the selected copy language and image text overlay language do not match, it is a pipeline bug.

**Important:** For regional languages, always specify the script name explicitly in the image prompt (e.g., "text overlay in Telugu script"). This helps the image model render the correct glyphs.

---

## Text Rendering Tips for Image Models

- **Short phrases work better** than long sentences. "[Short phrase]" renders more reliably than long sentences.
- **Mixed code-switched phrases** are acceptable if they match the locked language naturally.
- **Avoid complex grammar** in image text. Use punchy, telegram-style phrases.
- **Currency symbol** (₹, $, €) often renders better than abbreviated currency names in most models.
- **Test readability** — if the text is too long, the model may garble it.

---

## Verification Checklist

Before generating the image, verify:

- [ ] The prompt describes MOOD, not UI elements
- [ ] The prompt has at most 2 visual anchors per side
- [ ] Image text overlays match the copy variant language
- [ ] The prompt is concise and efficiently written (shorter prompts tend to preserve creativity, but there is no hard token limit)
- [ ] No checklist/checkmark UI elements are specified
- [ ] No specific fonts are requested
- [ ] Emotional contrast is explicit in the prompt
- [ ] **Camera/Technical layer is present** (shot type, lens, aperture, film stock)
- [ ] **Lighting pattern is named** (golden hour, Rembrandt, rim, volumetric)
- [ ] **Color palette includes hex codes or precise named colors**

---

## Example Pipeline Flow (Correct)

```
Ideation → Creative Concept → Copy Variants → Select Variant ([Angle], [Language])
    ↓
Extract emotional core + key phrases + lock language
    ↓
Generate Visual Brief (mood + anchors + locked language text)
    ↓
Craft image prompt (emotional, not prescriptive — concise is preferred but not enforced)
    ↓
Generate image (gpt-image-2, high quality)
    ↓
Verify image text matches locked language → if not, flag pipeline bug
```

---

---

## Camera/Technical Layer Reference

The Camera/Technical layer transforms a "descriptive" prompt into a **cinematic, premium advertising prompt**. GPT Image 2 and other advanced models use this information to render depth of field, bokeh, film grain, and color science. Without it, images look flat and generic.

### Prompt Structure Template (Tagged Sections)

Every prompt MUST include these tagged sections. The tags are used by the pipeline to verify OpenMontage optimization was applied.

```
[SHOT_TYPE: [close-up/medium/wide/establishing] of [subject]] +
[FRAMING: [rule-of-thirds/centered/leading-lines]] +
[ANGLE: [eye-level/low-angle/high-angle]] +
[EMOTIONAL_CONTRAST: [mood A] vs [mood B]] +
[VISUAL_ANCHOR_1: [element 1]] + [VISUAL_ANCHOR_2: [element 2]] +
[TEXT_OVERLAY: "[phrase]" in [Language] script] +
[COLOR_PALETTE: [hex codes or named colors]] +
[LIGHTING: [named pattern — golden hour/Rembrandt/rim/volumetric]] +
[CAMERA_TECHNICAL: Shot on [camera body] with [lens] at [aperture], [depth-of-field], [film stock]] +
[STYLE: [photorealistic/cinematic/advertising aesthetic]]
```

**Example (C01 CR-01 pain_point, Marathi):**
```
[SHOT_TYPE: medium shot] of a young Indian man in his late 20s, [FRAMING: rule-of-thirds], [ANGLE: eye-level]. [EMOTIONAL_CONTRAST: exhaustion vs curiosity]. Split-screen: LEFT — slouched in a modern cafe corner, phone glowing with blurred dating app profiles, exhausted expression, harsh overhead fluorescent creating deep shadows, cool blue-grey tones (#6B7B8C, #A0B0C0). RIGHT — same man upright and curious, glowing astrological chart on a tablet, soft golden-amber window light, warm cream and gold palette (#F5E6C8, #D4AF37). [TEXT_OVERLAY: "असंख्य ख्वाहिशा" in Marathi script] on left. [TEXT_OVERLAY: "असली नातं" in Marathi script] on right. [LIGHTING: harsh overhead fluorescent vs soft golden-amber window light]. [CAMERA_TECHNICAL: Shot on Sony A7IV with 35mm lens at f/2.8, shallow depth of field, cinematic color grading, Kodak Portra 400 film emulation]. [STYLE: Premium advertising aesthetic, photorealistic, 4:5 aspect ratio].
```

When writing the actual prompt sent to the image model, you may remove the bracket tags and write a flowing paragraph. The tags are primarily for **verification** — to prove OpenMontage optimization was applied.

### Camera/Technical Cheat Sheet

| Element | Options | When to Use |
|---|---|---|
| Shot type | close-up, medium shot, wide shot, establishing shot | Medium shot for portraits, wide for environments |
| Framing | rule-of-thirds, centered, leading-lines | Rule-of-thirds for dynamic ads, centered for symmetry |
| Angle | eye-level, low-angle, high-angle | Eye-level for relatability, low-angle for power |
| Lens | 35mm (environmental), 50mm (natural), 85mm (portrait) | 35mm for context, 85mm for tight emotional shots |
| Aperture | f/1.4 (extreme blur), f/2.8 (moderate), f/8 (sharp) | f/2.8 for most ads — subject pops, background softens |
| Depth of field | shallow, deep | Shallow for portraits, deep for landscapes |
| Film stock | Kodak Portra 400 (warm), Fujifilm Velvia (vivid), Ilford HP5 (B&W) | Portra 400 for warm skin tones in Indian advertising |

### Provider-Specific Optimization: GPT Image 2

When using `gpt-image-2` (the default for 91Astrology campaigns):

1. **Camera/Technical layer is HIGHLY effective.** GPT Image 2 interprets lens/aperture/film stock and renders corresponding depth of field, bokeh, and color science.
2. **Named lighting patterns work.** "Rembrandt lighting", "golden hour", "volumetric light" all produce visible effects.
3. **Hex color codes are respected.** Include `#RRGGBB` values for palette precision.
4. **Text rendering:** Handles Devanagari (Hindi, Marathi) and major Indic scripts well. Always specify the script explicitly: "text overlay in Marathi script".
5. ### Verification Checklist (Updated)

Before generating the image, verify:

- [ ] The prompt describes MOOD, not UI elements
- [ ] The prompt has at most 2 visual anchors per side
- [ ] Image text overlays match the copy variant language
- [ ] The prompt is concise and efficiently written (shorter prompts tend to preserve creativity, but there is no hard token limit)
- [ ] No checklist/checkmark UI elements are specified
- [ ] No specific fonts are requested
- [ ] Emotional contrast is explicit in the prompt
- [ ] **Camera/Technical layer is present** (shot type, lens, aperture, film stock)
- [ ] **Lighting pattern is named** (golden hour, Rembrandt, rim, volumetric)
- [ ] **Color palette includes hex codes or precise named colors**

## Related Skills

- `flux-best-practices/rules/t2i-prompting.md` — comprehensive camera/lens/film reference
- `flux-best-practices/rules/typography-text.md` — text rendering optimization
- `flux-best-practices/rules/model-selection-guide.md` — when to use GPT Image 2 vs Gemini vs FLUX
- `skills/creative/image-gen-usage.md` — OpenMontage image generation patterns

