"""Xinlu Valley asset pipeline.

Reads raw packs from art/packs/ (gitignored, see art/packs/LICENSES.md) and
produces game-ready assets under web/public/assets/:

  core/  - derived from licensed packs (Sprout Lands / Cute Fantasy /
           Mystic Woods free tiers). NOT committed to git; shipped only
           inside deployed builds. Regenerate with: python tools/build-assets.py
  open/  - CC0 (Kenney) and CC-BY-SA (LPC, attributed) assets. Committed.

Also emits web/public/assets/manifest.json describing every texture the
game loads (key, url, type, frame size) so the Phaser boot scene stays
data-driven.
"""
from __future__ import annotations

import colorsys
import json
import shutil
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
PACKS = ROOT / "art" / "packs"
OUT = ROOT / "web" / "public" / "assets"
CORE = OUT / "core"
OPEN = OUT / "open"

SPROUT = PACKS / "sprout-lands"
SPROUT_UI = PACKS / "sprout-lands-ui" / "Sprite sheets"
CUTE = PACKS / "cute-fantasy-rpg"
MYSTIC = PACKS / "mystic-woods"
KENNEY_FARM = PACKS / "kenney-pixel-platformer-farm-expansion"

manifest: list[dict] = []


def emit(key: str, rel: str, kind: str = "image", **extra) -> None:
    manifest.append({"key": key, "url": f"assets/{rel}", "type": kind, **extra})


def copy(src: Path, dst_rel: str, key: str, kind: str = "image", **extra) -> None:
    dst = OUT / dst_rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dst)
    emit(key, dst_rel, kind, **extra)


# --------------------------------------------------------------------------
# NPC recolors: shift the indigo/purple clothing cluster of the Sprout Lands
# base character to a per-agent hue while leaving skin/outline alone.
# --------------------------------------------------------------------------

AGENT_HUES = {
    # id: (target hue degrees, sat scale, val scale)
    "player": None,                 # original indigo
    "opus": (255, 1.10, 0.82),      # deep royal indigo — Chief Architect
    "codex": (175, 1.05, 0.95),     # teal — Coordinator
    "sonnet": (335, 0.95, 1.05),    # rose — Reviewer
    "haiku": (42, 1.10, 1.10),      # amber — Runner
    "deepseek": (210, 1.15, 0.90),  # whale blue — Bulk Worker
    "aris": (130, 0.90, 0.98),      # lab green — Research Frame
    "pixelcat": (20, 1.15, 1.05),   # ginger — Builder
}

# clothing cluster on the base sheet: blue/purple hues
CLOTH_HUE_RANGE = (200.0, 310.0)


def recolor_sheet(src: Path, target: tuple | None) -> Image.Image:
    img = Image.open(src).convert("RGBA")
    if target is None:
        return img
    hue_t, s_scale, v_scale = target
    px = img.load()
    w, h = img.size
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if a == 0:
                continue
            hh, ss, vv = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
            deg = hh * 360
            if ss > 0.18 and CLOTH_HUE_RANGE[0] <= deg <= CLOTH_HUE_RANGE[1]:
                nh = (hue_t % 360) / 360
                ns = min(1.0, ss * s_scale)
                nv = min(1.0, vv * v_scale)
                nr, ng, nb = colorsys.hsv_to_rgb(nh, ns, nv)
                px[x, y] = (round(nr * 255), round(ng * 255), round(nb * 255), a)
    return img


def build_characters() -> None:
    base = SPROUT / "Characters" / "Basic Charakter Spritesheet" / "Basic Charakter Spritesheet.png"
    actions = SPROUT / "Characters" / "Basic Charakter Actions" / "Basic Charakter Actions.png"
    outdir = CORE / "characters"
    outdir.mkdir(parents=True, exist_ok=True)
    for agent, target in AGENT_HUES.items():
        sheet = recolor_sheet(base, target)
        rel = f"core/characters/{agent}.png"
        sheet.save(OUT / rel)
        emit(f"char-{agent}", rel, "spritesheet", frameWidth=48, frameHeight=48)
    act = Image.open(actions).convert("RGBA")
    rel = "core/characters/player-actions.png"
    act.save(OUT / rel)
    emit("char-player-actions", rel, "spritesheet", frameWidth=48, frameHeight=48)


# --------------------------------------------------------------------------
# Building assembler: compose varied buildings from the Wooden House kit.
# Kit grid (16px cells, 7 cols): walls col0-2, door col3-4, roof col5-6.
# --------------------------------------------------------------------------

KIT_GRID = 16


def kit_tile(kit: Image.Image, col: int, row: int) -> Image.Image:
    return kit.crop((col * KIT_GRID, row * KIT_GRID, (col + 1) * KIT_GRID, (row + 1) * KIT_GRID))


def shift_hue(img: Image.Image, dh: float, ds: float = 1.0, dv: float = 1.0,
              hue_range: tuple = (0.0, 360.0), min_sat: float = 0.15) -> Image.Image:
    out = img.copy()
    px = out.load()
    w, h = out.size
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if a == 0:
                continue
            hh, ss, vv = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
            deg = hh * 360
            lo, hi = hue_range
            in_range = (lo <= deg <= hi) if lo <= hi else (deg >= lo or deg <= hi)
            if ss >= min_sat and in_range:
                nh = ((deg + dh) % 360) / 360
                ns = max(0.0, min(1.0, ss * ds))
                nv = max(0.0, min(1.0, vv * dv))
                nr, ng, nb = colorsys.hsv_to_rgb(nh, ns, nv)
                px[x, y] = (round(nr * 255), round(ng * 255), round(nb * 255), a)
    return out


def roof_recolor(img: Image.Image, dh: float) -> Image.Image:
    """Hue-rotate the red shingle band of the Cute Fantasy house. The brown
    timber sits around hue 20-40 with lower saturation, so restricting to a
    saturated red band keeps wood mostly intact; the small spill onto gable
    trim reads as a deliberate painted-gable two-tone, consistent across the
    whole town."""
    if not dh:
        return img.copy()
    out = img.copy()
    px = out.load()
    w, h = out.size
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if a == 0:
                continue
            hh, ss, vv = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
            deg = hh * 360
            if ss > 0.30 and (deg >= 325 or deg <= 18) and y < 82:
                nh = ((deg + dh) % 360) / 360
                nr, ng, nb = colorsys.hsv_to_rgb(nh, ss, vv)
                px[x, y] = (round(nr * 255), round(ng * 255), round(nb * 255), a)
    return out


def make_twin(img: Image.Image, overlap_x: int = 56) -> Image.Image:
    """Double-gable rowhouse: two copies half-overlapped (left in front)."""
    w, h = img.size
    canvas = Image.new("RGBA", (w + overlap_x, h), (0, 0, 0, 0))
    canvas.alpha_composite(img, (overlap_x, 0))
    canvas.alpha_composite(img, (0, 0))
    return canvas


def make_tall(img: Image.Image, repeats: int) -> Image.Image:
    """Insert extra plain-plank wall bands (y 76..84 is doors/windows-free)."""
    if repeats <= 0:
        return img
    w, h = img.size
    band_top, band_bot = 76, 84
    bh = band_bot - band_top
    canvas = Image.new("RGBA", (w, h + bh * repeats), (0, 0, 0, 0))
    canvas.alpha_composite(img.crop((0, 0, w, band_bot)), (0, 0))
    for i in range(repeats):
        canvas.alpha_composite(img.crop((0, band_top, w, band_bot)), (0, band_bot + i * bh))
    canvas.alpha_composite(img.crop((0, band_bot, w, h)), (0, band_bot + repeats * bh))
    return canvas


BUILDINGS = [
    # id, roof hue shift, twin gable, extra wall bands
    ("town-hall", 215.0, True, 1),
    ("memory-library", 265.0, False, 1),
    ("knowledge-tower", 195.0, False, 3),
    ("research-hall", 150.0, True, 0),
    ("skill-workshop", 35.0, False, 0),
    ("code-workshop", 180.0, False, 1),
    ("agent-inn", 318.0, True, 1),
    ("market", 48.0, False, 0),
    ("player-house", 0.0, False, 0),
    ("greenhouse", 110.0, False, 0),
]


def build_buildings() -> None:
    base = Image.open(CUTE / "Outdoor decoration" / "House.png").convert("RGBA")
    outdir = CORE / "buildings"
    outdir.mkdir(parents=True, exist_ok=True)
    for bid, hue, twin, bands in BUILDINGS:
        img = roof_recolor(base, hue)
        img = make_tall(img, bands)
        if twin:
            img = make_twin(img)
        rel = f"core/buildings/{bid}.png"
        img.save(OUT / rel)
        emit(f"bld-{bid}", rel, "image")


# --------------------------------------------------------------------------
# Straight copies
# --------------------------------------------------------------------------

def build_tiles_and_decor() -> None:
    t = "core/tiles"
    copy(SPROUT / "Tilesets/Grass/Grass.png", f"{t}/grass.png", "ts-grass")
    copy(SPROUT / "Tilesets/Tilled Dirt/Tilled Dirt.png", f"{t}/dirt.png", "ts-dirt")
    copy(SPROUT / "Tilesets/Hills/Hills.png", f"{t}/hills.png", "ts-hills")
    copy(SPROUT / "Tilesets/Water.png", f"{t}/water.png", "ts-water",
         "spritesheet", frameWidth=16, frameHeight=16)
    copy(SPROUT / "Objects/Paths/Paths.png", f"{t}/paths.png", "ts-paths")
    copy(SPROUT / "Tilesets/Fences/Fences.png", f"{t}/fences.png", "ts-fences",
         "spritesheet", frameWidth=16, frameHeight=16)

    d = "core/decor"
    copy(SPROUT / "Objects/Basic Plants/Basic Plants.png", f"{d}/plants.png", "decor-plants",
         "spritesheet", frameWidth=16, frameHeight=16)
    copy(SPROUT / "Objects/Basic Grass Biom things/Basic Grass Biom things 1.png",
         f"{d}/biom.png", "decor-biom", "spritesheet", frameWidth=16, frameHeight=16)
    copy(SPROUT / "Objects/Basic Furniture/Basic Furniture.png", f"{d}/furniture.png",
         "decor-furniture", "spritesheet", frameWidth=16, frameHeight=16)
    copy(SPROUT / "Objects/Wood Bridge/Wood Bridge.png", f"{d}/bridge.png", "decor-bridge")
    copy(SPROUT / "Objects/Chest/Chest.png", f"{d}/chest.png", "decor-chest",
         "spritesheet", frameWidth=48, frameHeight=48)
    copy(SPROUT / "Objects/Free_Chicken_House.png", f"{d}/chicken-house.png", "decor-chicken-house")

    copy(CUTE / "Outdoor decoration/Oak_Tree.png", f"{d}/oak-tree.png", "decor-oak")
    copy(CUTE / "Outdoor decoration/Oak_Tree_Small.png", f"{d}/oak-tree-small.png", "decor-oak-small",
         "spritesheet", frameWidth=32, frameHeight=48)
    copy(CUTE / "Outdoor decoration/Outdoor_Decor_Free.png", f"{d}/outdoor-decor.png",
         "decor-outdoor", "spritesheet", frameWidth=16, frameHeight=16)
    copy(CUTE / "Outdoor decoration/House.png", f"{d}/cute-house.png", "bld-cute-house")

    a = "core/animals"
    copy(SPROUT / "Characters/Free Chicken Sprites/Free Chicken Sprites.png",
         f"{a}/chicken.png", "anim-chicken", "spritesheet", frameWidth=16, frameHeight=16)
    copy(SPROUT / "Characters/Free Cow Sprites/Free Cow Sprites.png",
         f"{a}/cow.png", "anim-cow", "spritesheet", frameWidth=32, frameHeight=32)
    copy(CUTE / "Animals/Pig/Pig.png", f"{a}/pig.png", "anim-pig",
         "spritesheet", frameWidth=32, frameHeight=32)
    copy(CUTE / "Animals/Sheep/Sheep.png", f"{a}/sheep.png", "anim-sheep",
         "spritesheet", frameWidth=32, frameHeight=32)


def build_ui() -> None:
    u = "core/ui"
    copy(SPROUT_UI / "Dialouge UI/Premade dialog box  big.png", f"{u}/dialog-big.png", "ui-dialog-big")
    copy(SPROUT_UI / "Dialouge UI/Premade dialog box medium.png", f"{u}/dialog-medium.png", "ui-dialog-medium")
    copy(SPROUT_UI / "Dialouge UI/Premade dialog box small.png", f"{u}/dialog-small.png", "ui-dialog-small")
    copy(SPROUT_UI / "Dialouge UI/dialog box.png", f"{u}/dialog-9slice.png", "ui-dialog-9slice")
    copy(SPROUT_UI / "Dialouge UI/dialog box character finished talking click to continue indicator - spritesheet .png",
         f"{u}/dialog-next.png", "ui-dialog-next", "spritesheet", frameWidth=16, frameHeight=16)
    copy(SPROUT_UI / "Icons/All Icons.png", f"{u}/icons.png", "ui-icons",
         "spritesheet", frameWidth=16, frameHeight=16)
    copy(SPROUT_UI / "Dialouge UI/Emotes/Teemo Basic emote animations sprite sheet.png",
         f"{u}/emotes.png", "ui-emotes", "spritesheet", frameWidth=16, frameHeight=16)
    copy(SPROUT_UI / "buttons/Square Buttons 26x26.png", f"{u}/buttons-26.png", "ui-buttons-26")
    copy(SPROUT_UI / "Mouse sprites/Triangle Mouse icon 1.png", f"{u}/cursor.png", "ui-cursor")
    copy(SPROUT_UI / "Mouse sprites/Catpaw Mouse icon.png", f"{u}/cursor-paw.png", "ui-cursor-paw")


def build_interiors() -> None:
    floors = MYSTIC / "sprites/tilesets/floors"
    walls = MYSTIC / "sprites/tilesets/walls"
    i = "core/interior"
    if (walls / "walls.png").exists():
        copy(walls / "walls.png", f"{i}/walls.png", "ts-walls")
    if floors.exists():
        for f in sorted(floors.glob("*.png")):
            copy(f, f"{i}/floor-{f.stem}.png", f"ts-floor-{f.stem}")
    decor = MYSTIC / "sprites/objects/decor_16x16.png"
    if decor.exists():
        copy(decor, f"{i}/decor.png", "decor-interior", "spritesheet",
             frameWidth=16, frameHeight=16)


def build_open() -> None:
    """CC0 / attribution-safe assets that DO get committed."""
    src = KENNEY_FARM / "Tilemap" / "tilemap_packed.png"
    if src.exists():
        copy(src, "open/kenney-farm.png", "ts-kenney-farm", "spritesheet",
             frameWidth=18, frameHeight=18)
    lpc = PACKS / "lpc-crops" / "crops-v2" / "crops.png"
    if lpc.exists():
        copy(lpc, "open/lpc-crops.png", "ts-lpc-crops", "spritesheet",
             frameWidth=32, frameHeight=32)


def main() -> None:
    if CORE.exists():
        shutil.rmtree(CORE)
    CORE.mkdir(parents=True, exist_ok=True)
    OPEN.mkdir(parents=True, exist_ok=True)
    build_tiles_and_decor()
    build_characters()
    build_buildings()
    build_ui()
    build_interiors()
    build_open()
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"manifest entries: {len(manifest)}")
    print(f"core files: {sum(1 for _ in CORE.rglob('*.png'))}")
    print(f"open files: {sum(1 for _ in OPEN.rglob('*.png'))}")


if __name__ == "__main__":
    main()
