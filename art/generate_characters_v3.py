"""
Generate single-frame character portraits (48x48 each) for Pixel AI Town.
One clean standing pose per character, NOT a sprite sheet.
"""
import httpx
import base64
import os
import sys
import time
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")
sys.stdout.reconfigure(encoding="utf-8")

OUTPUT_DIR = Path(__file__).parent / "generated"
OUTPUT_DIR.mkdir(exist_ok=True)

URL = os.environ.get("GPTIMAGE_URL", "https://cclaude.ai/v1/images/generations")
KEY = os.environ.get("GPTIMAGE_KEY", "")

def generate(prompt: str, name: str):
    print(f"  Generating: {name}...")
    try:
        with httpx.Client(timeout=httpx.Timeout(180.0, connect=15.0)) as client:
            resp = client.post(
                URL,
                json={"model": "gpt-image-2", "prompt": prompt, "size": "1024x1024", "quality": "high", "n": 1},
                headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"},
            )
        if resp.status_code == 200:
            data = resp.json()
            if "data" in data and data["data"]:
                img = data["data"][0]
                if "b64_json" in img:
                    (OUTPUT_DIR / f"{name}.png").write_bytes(base64.b64decode(img["b64_json"]))
                    print(f"  [OK] {name}.png")
                    return True
                elif "url" in img:
                    img_resp = httpx.get(img["url"], timeout=30.0)
                    (OUTPUT_DIR / f"{name}.png").write_bytes(img_resp.content)
                    print(f"  [OK] {name}.png")
                    return True
        else:
            print(f"  [FAIL] {resp.status_code}: {resp.text[:100]}")
    except Exception as e:
        print(f"  [FAIL] {type(e).__name__}: {str(e)[:80]}")
    return False

STYLE = """single pixel art character, one character only, standing idle pose facing forward,
48x48 pixels displayed on a 1024x1024 canvas (centered, scaled up cleanly),
top-down 3/4 view like Stardew Valley NPCs,
warm saturated colors, crisp pixels, 1px dark outline,
solid colored background (light green #90EE90) for easy removal,
professional indie game quality, original design NOT copied from any game,
ONE character only, no duplicates, no sprite sheet, just one single standing pose"""

CHARS = {
    "agent_opus": f"""{STYLE},
character: a wise orange cubic pixel creature, the Claude/Anthropic mascot style,
blocky rounded-square orange body (#F39C12), simple black dot eyes,
tiny stubby legs, wearing a small golden crown and tiny purple cape,
dignified calm posture, warm orange with darker shading on bottom""",

    "agent_codex": f"""{STYLE},
character: a cute cloud-shaped blue-purple AI robot,
body is a soft puffy cloud shape in blue-purple gradient (#6C5CE7 to #74B9FF),
small glowing rectangular screen for face showing a blinking cursor,
tiny round feet, compact fluffy body, white cloud highlights on top""",

    "agent_pixelcat": f"""{STYLE},
character: a playful orange pixel cat standing upright on two legs,
cat with pointed triangle ears, long curved tail, orange fur (#F39C12),
wearing a small blue scarf (#3498DB) around neck,
cream-colored belly, alert curious green eyes, whiskers""",

    "agent_sonnet": f"""{STYLE},
character: a friendly medium orange cubic pixel creature from the Claude family,
similar to Opus but slightly smaller and rounder, no crown,
blocky orange body (#E67E22), happy curved-line smile, dot eyes,
holding a tiny green notebook in one stubby arm""",

    "agent_haiku": f"""{STYLE},
character: the tiniest orange cubic pixel creature from the Claude family,
very small blocky body (#F1C40F bright yellow-orange), energetic pose,
simple excited dot eyes, tiny fast legs mid-step,
small speed lines or sparkle near it to show quickness""",

    "agent_deepseek": f"""{STYLE},
character: a friendly small blue whale standing upright on tail fin,
cute cartoon whale body in deep ocean blue (#2980B9),
lighter blue belly (#5DADE2), small flippers as arms,
gentle closed-eye smile, tiny backpack on back,
small water droplet floating above head""",

    "agent_openhands": f"""{STYLE},
character: a practical raccoon standing upright,
grey-brown fur (#7F8C8D) with dark raccoon mask markings around eyes,
wearing a brown leather tool belt with tiny wrench and hammer,
sturdy determined posture, bushy striped tail""",

    "agent_aris": f"""{STYLE},
character: a geometric crystal golem made of purple crystal,
angular body of translucent purple segments (#9B59B6),
bright glowing red-orange core visible in chest (#E74C3C),
geometric limbs, two small crystal fragments floating near head,
precise upright posture""",

    "agent_player": f"""{STYLE},
character: a cute anime-inspired girl,
long flowing pastel pink-lavender hair (#FFB7B2) reaching below shoulders,
wearing a delicate flower crown with tiny white and pink flowers,
simple cream-colored dress (#FFF8DC) with soft pink trim,
large expressive dark eyes, gentle warm smile,
small and cute proportions""",
}

if __name__ == "__main__":
    print("=== Generating Single-Frame Character Portraits ===\n")
    for name, prompt in CHARS.items():
        generate(prompt, name)
        time.sleep(2)
    print("\nDone!")
