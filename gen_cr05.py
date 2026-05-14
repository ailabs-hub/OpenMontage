import sys
from pathlib import Path
OM_ROOT = Path(r"C:\Users\91829\Desktop\Vansun\Marketing_automations\OpenMontage")
sys.path.insert(0, str(OM_ROOT))
from lib.env_loader import load_env
load_env(OM_ROOT)
from tools.graphics.image_selector import ImageSelector

selector = ImageSelector()
prompt = (
    "Medium shot of a serene temple interior at dawn, rule-of-thirds framing, low-angle. "
    "Emotional contrast: stuck pattern versus healing transformation. "
    "Visual anchor 1: gentle incense smoke rising in soft spirals against warm morning light. "
    "Visual anchor 2: single diya flame burning steadily, reflected softly on polished stone floor. "
    "Text overlay: \"Free mantras Expert guidance\" in warm gold serif lettering. "
    "Color palette: maroon (#800000), sandalwood (#F4A460), gold (#D4AF37). "
    "Lighting: warm dawn morning light, volumetric rays filtering through incense smoke. "
    "Camera technical: Shot on Sony A7IV with 50mm lens at f/2.0, shallow depth of field, Kodak Portra 400 film emulation. "
    "Style: Devotional, photorealistic, premium advertising aesthetic, 4:5 aspect ratio."
)
result = selector.execute({
    "prompt": prompt,
    "preferred_provider": "openai",
    "output_path": r"C:\Users\91829\Desktop\Vansun\Marketing_automations\91_astro\campaigns\marriage-signs-nadi\assets\cr05_offer_led_english.png",
    "size": "auto",
    "quality": "high",
    "output_format": "png",
})
print("SUCCESS" if result.success else "FAILED")
if not result.success:
    print(result.error)
else:
    print(result.data.get("output"))
