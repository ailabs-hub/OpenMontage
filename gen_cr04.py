import sys
from pathlib import Path
OM_ROOT = Path(r"C:\Users\91829\Desktop\Vansun\Marketing_automations\OpenMontage")
sys.path.insert(0, str(OM_ROOT))
from lib.env_loader import load_env
load_env(OM_ROOT)
from tools.graphics.image_selector import ImageSelector

selector = ImageSelector()
prompt = (
    "Wide shot of an atmospheric split scene connected by a single warm light source, leading-lines framing, eye-level angle. "
    "Emotional contrast: career focus versus quiet longing. "
    "Visual anchor 1: organized desk bathed in soft amber glow of a reading lamp. "
    "Visual anchor 2: moonlit window with empty chair, silver light touching untouched tea cups. "
    "Text overlay: \"Success at work Silence at home\" in white serif lettering. "
    "Color palette: amber (#FFBF00), silver (#C0C0C0), deep blue (#00008B). "
    "Lighting: split lighting, warm amber reading lamp versus cool silver moonlight. "
    "Camera technical: Shot on Sony A7IV with 35mm lens at f/2.8, shallow depth of field, Kodak Portra 400 film emulation. "
    "Style: Cinematic, photorealistic, premium advertising aesthetic, 1:1 aspect ratio."
)
result = selector.execute({
    "prompt": prompt,
    "preferred_provider": "openai",
    "output_path": r"C:\Users\91829\Desktop\Vansun\Marketing_automations\91_astro\campaigns\marriage-signs-nadi\assets\cr04_pain_point_english.png",
    "size": "1024x1024",
    "quality": "high",
    "output_format": "png",
})
print("SUCCESS" if result.success else "FAILED")
if not result.success:
    print(result.error)
else:
    print(result.data.get("output"))
