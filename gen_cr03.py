import sys
from pathlib import Path
OM_ROOT = Path(r"C:\Users\91829\Desktop\Vansun\Marketing_automations\OpenMontage")
sys.path.insert(0, str(OM_ROOT))
from lib.env_loader import load_env
load_env(OM_ROOT)
from tools.graphics.image_selector import ImageSelector

selector = ImageSelector()
prompt = (
    "Overhead shot of premium parchment surface softly illuminated by celestial glow, centered framing, top-down angle. "
    "Emotional contrast: generic horoscope versus deeply personal blueprint. "
    "Visual anchor 1: faint constellation patterns emerging like whispered star maps. "
    "Visual anchor 2: soft celestial glow revealing handwritten planetary details. "
    "Text overlay: \"Horoscope vs your blueprint\" in elegant gold serif lettering. "
    "Color palette: warm cream (#F5E6C8), soft gold (#D4AF37), midnight blue (#191970). "
    "Lighting: soft celestial glow from above, volumetric light. "
    "Camera technical: Shot on Hasselblad X2D with 90mm lens at f/4, deep depth of field, Fujifilm Velvia film emulation. "
    "Style: Sacred, premium, photorealistic advertising aesthetic, 4:5 aspect ratio."
)
result = selector.execute({
    "prompt": prompt,
    "preferred_provider": "openai",
    "output_path": r"C:\Users\91829\Desktop\Vansun\Marketing_automations\91_astro\campaigns\marriage-signs-nadi\assets\cr03_comparison_english.png",
    "size": "auto",
    "quality": "high",
    "output_format": "png",
})
print("SUCCESS" if result.success else "FAILED")
if not result.success:
    print(result.error)
else:
    print(result.data.get("output"))
