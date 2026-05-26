"""
Pixel AI Town — Regenerate sprites with proper transparent backgrounds
and generate additional props for a richer map.
"""

import httpx
import base64
import os
import sys
import time
from pathlib import Path
from PIL import Image
import numpy as np

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

OUTPUT_DIR = Path(__file__).parent / "generated"
OUTPUT_DIR.mkdir(exist_ok=True)
PROCESSED_DIR = Path(__file__).parent / "processed"
PROCESSED_DIR.mkdir(exist_ok=True)

DEPLOY_AGENTS = Path(__file__).parent.parent / "frontend" / "public" / "assets" / "town" / "agents"
DEPLOY_BUILDINGS = Path(__file__).parent.parent / "frontend" / "public" / "assets" / "town" / "buildings"

GENERATE_URL = "http://127.0.0.1:9800/generate-image"
FALLBACK_URL = os.environ.get("GPTIMAGE_URL", "https://cclaude.ai/v1/images/generations")
FALLBACK_KEY = os.environ.get("GPTIMAGE_KEY", "")

STYLE_PREFIX = (
    "pixel art, 32x32 game sprite, top-down RPG style, warm pastel color palette, "
    "cozy cute aesthetic, clean pixel edges, gentle shading, game asset, "
    "solid white background, no anti-aliasing, crisp pixels, single character centered"
)

AGENTS = {
    "agent_opus": "wise owl character wearing purple robe with golden trim, small crown, calm expression, facing forward",
    "agent_pixelcat": "playful orange pixel cat with tiny blue scarf, alert ears, curious eyes, facing forward",
    "agent_codex": "round robot with blue-purple gradient body, glowing screen face, facing forward",
    "agent_sonnet": "gentle deer character with cream and soft brown colors, holding notebook, facing forward",
    "agent_haiku": "tiny hummingbird character, iridescent teal-green feathers, energetic pose, facing forward",
    "agent_deepseek": "small friendly blue whale character with tiny backpack, gentle smile, facing forward",
    "agent_openhands": "raccoon character with tool belt, brown and grey fur, determined expression, facing forward",
    "agent_aris": "crystal golem character, translucent purple geometric body, glowing core, facing forward",
    "agent_player": "cute anime girl with long flowing hair, pastel pink and lavender colors, fantasy flower crown, gentle expression, facing forward",
}


def generate_image(prompt: str, name: str, size: str = "1024x1024") -> bool:
    full_prompt = f"{STYLE_PREFIX}, {prompt}"
    print(f"  Generating: {name}...")

    # Try fallback (more reliable)
    try:
        headers = {"Content-Type": "application/json"}
        if FALLBACK_KEY:
            headers["Authorization"] = f"Bearer {FALLBACK_KEY}"
        resp = httpx.post(
            FALLBACK_URL,
            json={"model": "gpt-image-2", "prompt": full_prompt, "size": size, "quality": "high", "n": 1},
            headers=headers,
            timeout=120.0,
        )
        if resp.status_code == 200:
            data = resp.json()
            if "data" in data and data["data"]:
                img_data = data["data"][0]
                if "b64_json" in img_data:
                    img_bytes = base64.b64decode(img_data["b64_json"])
                elif "url" in img_data:
                    img_resp = httpx.get(img_data["url"], timeout=30.0)
                    img_bytes = img_resp.content
                else:
                    print(f"  [FAIL] No image data")
                    return False
                out_path = OUTPUT_DIR / f"{name}.png"
                out_path.write_bytes(img_bytes)
                print(f"  [OK] Saved: {out_path} ({len(img_bytes)} bytes)")
                return True
        else:
            print(f"  [FAIL] HTTP {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        print(f"  [FAIL] {e}")

    return False


def remove_background(input_path: Path, output_path: Path, threshold: int = 240):
    """Remove white/near-white background and make it transparent."""
    img = Image.open(input_path).convert("RGBA")
    data = np.array(img)

    # Find white-ish pixels (R>threshold, G>threshold, B>threshold)
    white_mask = (data[:, :, 0] > threshold) & (data[:, :, 1] > threshold) & (data[:, :, 2] > threshold)

    # Also find green-ish background pixels (common in gptimage2 output)
    green_mask = (data[:, :, 1] > data[:, :, 0] + 30) & (data[:, :, 1] > data[:, :, 2] + 30) & (data[:, :, 1] > 100)

    # Combine masks
    bg_mask = white_mask | green_mask

    # Set alpha to 0 for background pixels
    data[bg_mask, 3] = 0

    result = Image.fromarray(data)
    result.save(output_path)
    print(f"  [BG-REMOVE] {output_path.name}")


def process_and_deploy_agents():
    """Process generated agents: remove background, resize, deploy."""
    for name in AGENTS:
        src = OUTPUT_DIR / f"{name}.png"
        if not src.exists():
            print(f"  [SKIP] {name} not generated yet")
            continue

        # Remove background
        processed = PROCESSED_DIR / f"{name}.png"
        remove_background(src, processed)

        # Deploy to frontend
        deploy_path = DEPLOY_AGENTS / f"{name}.png"
        # Resize to reasonable game size (128x128 for display at 40-48px)
        img = Image.open(processed)
        img = img.resize((128, 128), Image.NEAREST)
        img.save(deploy_path)
        print(f"  [DEPLOY] {deploy_path}")


def generate_all_agents():
    print("\n=== Generating Agent Sprites (white bg for removal) ===")
    for name, desc in AGENTS.items():
        generate_image(desc, name)
        time.sleep(3)
    print("\n=== Processing: removing backgrounds ===")
    process_and_deploy_agents()


if __name__ == "__main__":
    args = sys.argv[1:] if len(sys.argv) > 1 else ["--agents"]

    if "--agents" in args or "--all" in args:
        generate_all_agents()

    print("\nDone!")
