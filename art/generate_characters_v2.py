"""
Generate high-quality character sprite sheets for Pixel AI Town.
Each character gets a 288x48 sprite sheet (6 frames x 48x48 each):
  Frame 1-2: idle animation
  Frame 3-4: walk right
  Frame 5-6: walk left

Characters based on their real appearances:
- Opus: orange cubic creature (CC family - orange pixel block beings)
- PixelCat/OpenCode: orange pixel cat with blue scarf
- Codex: cloud-shaped blue-purple robot
- Sonnet: orange cubic creature, smaller than Opus (CC family)
- Haiku: orange cubic creature, smallest (CC family)
- DeepSeek: blue whale character
- OpenHands: raccoon with tools
- ARIS: purple crystal golem
- Player: cute anime girl, long pink hair, flower crown
"""
import httpx
import base64
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")
sys.stdout.reconfigure(encoding="utf-8")

OUTPUT_DIR = Path(__file__).parent / "generated"
OUTPUT_DIR.mkdir(exist_ok=True)

URL = os.environ.get("GPTIMAGE_URL", "https://cclaude.ai/v1/images/generations")
KEY = os.environ.get("GPTIMAGE_KEY", "")

def generate(prompt: str, name: str, size: str = "1024x1024"):
    print(f"  Generating: {name}...")
    try:
        with httpx.Client(timeout=httpx.Timeout(180.0, connect=15.0)) as client:
            resp = client.post(
                URL,
                json={"model": "gpt-image-2", "prompt": prompt, "size": size, "quality": "high", "n": 1},
                headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"},
            )
        if resp.status_code == 200:
            data = resp.json()
            if "data" in data and data["data"]:
                img = data["data"][0]
                if "b64_json" in img:
                    (OUTPUT_DIR / f"{name}.png").write_bytes(base64.b64decode(img["b64_json"]))
                    print(f"  [OK] Saved: {name}.png")
                    return True
                elif "url" in img:
                    img_resp = httpx.get(img["url"], timeout=30.0)
                    (OUTPUT_DIR / f"{name}.png").write_bytes(img_resp.content)
                    print(f"  [OK] Saved: {name}.png")
                    return True
        else:
            print(f"  [FAIL] {resp.status_code}: {resp.text[:150]}")
    except Exception as e:
        print(f"  [FAIL] {type(e).__name__}: {str(e)[:100]}")
    return False

import time

STYLE_BASE = """pixel art character sprite sheet, 6 frames arranged horizontally in a single row,
each frame is 48x48 pixels (total image: 288x48 pixels),
top-down 3/4 view RPG style, warm saturated colors,
professional indie game quality like Stardew Valley characters,
crisp pixels, no anti-aliasing, 1px dark outline on character,
transparent background,
frames: idle-1, idle-2, walk-right-1, walk-right-2, walk-left-1, walk-left-2,
original character design, NOT copied from any game"""

CHARACTERS = {
    "sprite_opus": f"""{STYLE_BASE},
character: a wise orange cubic pixel creature with a small golden crown,
the CC/Claude family mascot style - blocky orange body like a rounded square,
simple dot eyes, tiny legs, dignified posture,
wearing a tiny purple cape to show authority,
the body is warm orange (#F39C12) with darker orange shading""",

    "sprite_codex": f"""{STYLE_BASE},
character: a cute cloud-shaped blue-purple robot,
body looks like a soft puffy cloud or cotton ball in blue-purple gradient,
has a small glowing screen/visor for a face showing a cursor blinking,
compact round body, tiny stubby legs,
colors: blue-purple (#6C5CE7 to #3498DB) with white cloud highlights""",

    "sprite_pixelcat": f"""{STYLE_BASE},
character: a playful orange pixel cat standing upright,
cat body with pointed ears, long tail, wearing a tiny blue scarf,
the OpenCode mascot - a pixel art cat in 8-bit retro style,
alert curious expression, orange fur (#F39C12) with cream belly,
blue scarf (#3498DB), dark outline""",

    "sprite_sonnet": f"""{STYLE_BASE},
character: a medium-sized orange cubic pixel creature from the CC/Claude family,
similar to Opus but slightly smaller and more friendly looking,
blocky orange body, simple happy dot eyes, tiny legs,
holding a small notebook or clipboard,
warm orange (#E67E22) with lighter orange highlights""",

    "sprite_haiku": f"""{STYLE_BASE},
character: the smallest orange cubic pixel creature from the CC/Claude family,
tiny blocky orange body, very small and fast-looking,
simple dot eyes with energetic expression, tiny quick legs,
has a small lightning bolt or speed lines around it,
bright orange (#F1C40F to #F39C12), smallest of the family""",

    "sprite_deepseek": f"""{STYLE_BASE},
character: a friendly small blue whale character walking upright,
cute cartoon whale body in deep blue, small flippers used as arms,
gentle smile, tiny backpack on back,
the DeepSeek mascot - a pixel whale that walks on its tail,
colors: deep ocean blue (#2980B9) with lighter blue belly (#5DADE2),
small water droplet above head""",

    "sprite_openhands": f"""{STYLE_BASE},
character: a practical raccoon character standing upright,
grey-brown fur with distinctive raccoon mask markings,
wearing a tool belt with tiny wrench and hammer,
sturdy build, determined helpful expression,
colors: grey (#7F8C8D), brown (#8B5E3C), dark mask (#2C3E50)""",

    "sprite_aris": f"""{STYLE_BASE},
character: a geometric crystal golem character,
body made of translucent purple crystal segments,
glowing bright core in chest, angular geometric limbs,
systematic precise posture, floating crystal fragments around head,
colors: purple crystal (#9B59B6), bright core (#E74C3C), dark outline""",

    "sprite_player": f"""{STYLE_BASE},
character: a cute anime-inspired girl character,
long flowing pastel pink-lavender hair reaching below shoulders,
wearing a soft fantasy flower crown with small white and pink flowers,
simple cream-colored dress with pink trim,
gentle warm expression, large expressive pixel eyes,
colors: pink hair (#FFB7B2), lavender highlights (#DCD6F7), cream dress (#FFF8DC)""",
}

if __name__ == "__main__":
    print("=== Generating Character Sprite Sheets (48x48, 6 frames) ===\n")
    for name, prompt in CHARACTERS.items():
        generate(prompt, name)
        time.sleep(2)
    print("\nDone!")
