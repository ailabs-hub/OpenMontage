import sys
from pathlib import Path
OM_ROOT = Path(r"C:\Users\91829\Desktop\Vansun\Marketing_automations\OpenMontage")
sys.path.insert(0, str(OM_ROOT))
from lib.env_loader import load_env
load_env(OM_ROOT)
from tools.graphics.image_selector import ImageSelector

selector = ImageSelector()
prompt = (
    "Close-up of weathered hands slowly opening an ancient manuscript, centered framing, eye-level angle. "
    "Emotional contrast: mystery versus sacred revelation. "
    "Visual anchor 1: warm amber light spilling from between aged parchment pages. "
    "Visual anchor 2: golden dust particles floating in volumetric light shafts. "
    "Text overlay: \"Your love window is opening\" in elegant gold serif lettering. "
    "Color palette: rich cream (#FFFDD0), aged gold (#D4AF37), deep brown (#3E2723). "
    "Lighting: volumetric golden light, Rembrandt lighting on hands. "
    "Camera technical: Shot on Sony A7IV with 85mm lens at f/2.8, shallow depth of field, Kodak Portra 400 film emulation. "
    "Style: Photorealistic, cinematic, premium advertising aesthetic, 1:1 aspect ratio."
)
result = selector.execute({
    "prompt": prompt,
    "preferred_provider": "openai",
    "output_path": r"C:\Users\91829\Desktop\Vansun\Marketing_automations\91_astro\campaigns\marriage-signs-nadi\assets\cr02_direct_benefit_english.png",
    "size": "1024x1024",
    "quality": "high",
    "output_format": "png",
})
print("SUCCESS" if result.success else "FAILED")
if not result.success:
    print(result.error)
else:
    print(result.data.get("output"))
