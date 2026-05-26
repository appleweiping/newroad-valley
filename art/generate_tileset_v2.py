"""
Generate a high-quality Stardew Valley-style terrain tileset via gptimage2.
This produces a single 512x512 PNG containing 16x16 tiles in a 32x32 grid.
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


# === TERRAIN TILESET ===
terrain_prompt = """Create a pixel art terrain tileset sprite sheet for a cozy top-down farming/town game.
The sheet should be exactly 512x512 pixels containing 16x16 pixel tiles arranged in a 32x32 grid.

Style requirements:
- Warm, saturated colors like Stardew Valley
- Each tile must be hand-crafted quality with rich pixel detail
- Consistent lighting from top-left
- 1px dark outline where tiles have distinct edges
- NO anti-aliasing, crisp pixel edges only

Tile layout (row by row, 32 tiles per row):
Row 1-2: Grass tiles (8 variants of lush green grass with individual blades, flowers, clover, different densities)
Row 3-4: Grass edge tiles (transitions to dirt - top, bottom, left, right, all 4 corners, inner corners)
Row 5-6: Dirt/path tiles (packed earth, with pebbles, worn paths, dry patches, muddy spots)
Row 7-8: Cobblestone path tiles (individual rounded stones with mortar gaps, highlight on top-left of each stone, shadow on bottom-right)
Row 9-10: Water tiles (deep blue center, lighter edges, ripple patterns, shore transitions)
Row 11-12: Wooden floor/deck tiles (planks with grain, nail heads, slight color variation between boards)

Color palette:
- Grass: rich warm greens (#5DAE3B, #4A9030, #72C04A, #3D7A25)
- Dirt: warm browns (#A08050, #8B6B3D, #C4A060, #6B4E2A)
- Stone: warm grey-beige (#B8A888, #9A8A6A, #D0C0A0, #7A6A4A)
- Water: clear blues (#3A7AB8, #5090D0, #2A5A88, #70B0E0)
- Wood: rich browns (#8B5E3C, #A06B42, #6B4530, #C08050)

This must look like a professional indie game tileset, not a placeholder.
Original art only - do not copy any existing game's tiles."""

# === BUILDING PARTS TILESET ===
building_prompt = """Create a pixel art building parts tileset sprite sheet for a cozy top-down town game.
The sheet should be exactly 512x512 pixels containing 16x16 pixel tiles arranged in a 32x32 grid.

Style: warm, cozy, Stardew Valley quality level. Hand-crafted pixel art, NOT generated-looking.

Tile layout:
Row 1-4: Wall tiles (wooden walls with planks, stone walls with mortar, plaster walls, brick walls - each with window and plain variants)
Row 5-8: Roof tiles (red clay roof, blue slate roof, green moss roof, brown thatch roof - each with left edge, middle, right edge, peak)
Row 9-10: Doors and windows (wooden door, fancy door, lit window warm glow, dark window, round window, shuttered window)
Row 11-12: Interior props (bookshelf full of colorful books, workbench with tools, crystal display shelf, glowing terminal screen, potion shelf, anvil)
Row 13-14: Exterior props (wooden sign, lamp post, flower pot, barrel, crate, well, mailbox, bench)
Row 15-16: Decorative (hanging banner, flag, chimney with smoke, weather vane, flower box, vine on wall)

Color palette:
- Walls: warm plaster (#D4B896), grey stone (#8A8A8A), red brick (#B85A4A), dark wood (#6B4530)
- Roofs: terracotta red (#C85A4A), slate blue (#4A7AB8), moss green (#6B8B5A), thatch brown (#A08050)
- Windows: warm glow (#FFE4A0), dark (#3A3A4A)
- Props: natural wood browns, iron grey, colorful book spines

Professional indie game quality. Original art only."""

if __name__ == "__main__":
    print("=== Generating Stardew-quality tilesets ===\n")
    generate(terrain_prompt, "tileset_terrain_v2")
    generate(building_prompt, "tileset_buildings_v2")
    print("\nDone!")
