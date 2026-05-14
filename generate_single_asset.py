#!/usr/bin/env python3
"""Generate a single campaign asset."""
import sys
from pathlib import Path

OM_ROOT = Path(r"C:\Users\91829\Desktop\Vansun\Marketing_automations\OpenMontage")
sys.path.insert(0, str(OM_ROOT))

from lib.env_loader import load_env
load_env(OM_ROOT)

from tools.graphics.image_selector import ImageSelector

selector = ImageSelector()
result = selector.execute({
    "prompt": sys.argv[1],
    "preferred_provider": "openai",
    "output_path": sys.argv[2],
    "size": sys.argv[3],
    "quality": "high",
    "output_format": "png",
})

print("SUCCESS" if result.success else "FAILED")
if not result.success:
    print(result.error)
else:
    print(result.data.get("provider"), result.data.get("model"))
    print(result.data.get("output"))
