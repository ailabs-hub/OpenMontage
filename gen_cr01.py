import sys
from pathlib import Path
OM_ROOT = Path(r"C:\Users\91829\Desktop\Vansun\Marketing_automations\OpenMontage")
sys.path.insert(0, str(OM_ROOT))
from lib.env_loader import load_env
load_env(OM_ROOT)
from tools.graphics.image_selector import ImageSelector

selector = ImageSelector()
prompt = (
    "Medium shot of two silhouetted figures standing at a thoughtful distance in a warm candlelit interior, "
    "rule-of-thirds framing, eye-level angle. Emotional contrast: quiet uncertainty versus intimate warmth. "
    "Visual anchor 1: sheer fabric filtering soft golden light. "
    "Visual anchor 2: long gentle shadows stretching across polished floor. "
    "Text overlay: \"The right person is greater than the right date\" in elegant serif lettering. "
    "Color palette: deep amber (#B87333), warm cream (#FFF8E7), subtle maroon (#800000). "
    "Lighting: golden hour through sheer curtains, soft volumetric light rays. "
    "Camera technical: Shot on Sony A7IV with 50mm lens at f/2.0, shallow depth of field, Kodak Portra 400 film emulation. "
    "Style: Cinematic, photorealistic, premium advertising aesthetic, 4:5 aspect ratio."
)
result = selector.execute({
    "prompt": prompt,
    "preferred_provider": "openai",
    "output_path": r"C:\Users\91829\Desktop\Vansun\Marketing_automations\91_astro\campaigns\marriage-signs-nadi\assets\cr01_pain_point_english.png",
    "size": "auto",
    "quality": "high",
    "output_format": "png",
})
print("SUCCESS" if result.success else "FAILED")
if not result.success:
    print(result.error)
else:
    print(result.data.get("output"))
