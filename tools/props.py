"""Hand-drawn interior props (matrix DSL, see creatures.py).

The free packs lack a bookshelf, a server/status screen, a forge and a
kanban board — the four signature fixtures of the working buildings.
"""
from __future__ import annotations

from PIL import Image

OUTLINE = (61, 43, 31, 255)


def _rgba(rgb):
    return (*rgb, 255)


WOOD = _rgba((138, 90, 59))
WOOD_D = _rgba((104, 66, 42))
WOOD_L = _rgba((176, 122, 82))

PROPS: dict[str, dict] = {}

# ---- bookshelf 16x32: warm wood frame, three rows of colourful spines ------
PROPS["bookshelf"] = {
    "pal": {
        "W": WOOD, "w": WOOD_D, "L": WOOD_L,
        "r": _rgba((196, 90, 90)), "g": _rgba((110, 162, 96)),
        "b": _rgba((96, 130, 186)), "y": _rgba((214, 174, 96)),
        "p": _rgba((150, 110, 170)), "t": _rgba((96, 168, 160)),
        "D": _rgba((52, 38, 30)),
    },
    "rows": [
        "#LLLLLLLLLLLLLL#",
        "#WWWWWWWWWWWWWW#",
        "#W#DDDDDDDDDD#W#",
        "#W#rrggbbyypp#W#",
        "#W#rrggbbyypp#W#",
        "#W#rrggbbyypp#W#",
        "#WwwwwwwwwwwwwW#",
        "#W#DDDDDDDDDD#W#",
        "#W#ttyyrrbbgg#W#",
        "#W#ttyyrrbbgg#W#",
        "#W#ttyyrrbbgg#W#",
        "#WwwwwwwwwwwwwW#",
        "#W#DDDDDDDDDD#W#",
        "#W#ggppttrryy#W#",
        "#W#ggppttrryy#W#",
        "#W#ggppttrryy#W#",
        "#WwwwwwwwwwwwwW#",
        "#WWWWWWWWWWWWWW#",
        "#LLLLLLLLLLLLLL#",
        "#WWWWWWWWWWWWWW#",
    ],
}

# ---- status screen 32x20: dark glass with green service bars ---------------
PROPS["status-screen"] = {
    "pal": {
        "F": _rgba((70, 76, 90)), "f": _rgba((96, 104, 122)),
        "D": _rgba((26, 30, 40)),
        "g": _rgba((110, 220, 130)), "G": _rgba((58, 150, 84)),
        "y": _rgba((230, 200, 100)), "r": _rgba((220, 110, 100)),
        "c": _rgba((120, 200, 220)),
    },
    "rows": [
        "#ffffffffffffffffffffffffffffff#",
        "#FDDDDDDDDDDDDDDDDDDDDDDDDDDDDF#",
        "#FDcccDDDDDDDDDDDDDDDDDDDDDDDDF#",
        "#FDDDDDDDDDDDDDDDDDDDDDDDDDDDDF#",
        "#FDggggggggggggggggggDDDDDDgDDF#",
        "#FDDDDDDDDDDDDDDDDDDDDDDDDDDDDF#",
        "#FDggggggggggggDDDDDDDDDDDDgDDF#",
        "#FDDDDDDDDDDDDDDDDDDDDDDDDDDDDF#",
        "#FDyyyyyyyyyyyyyyyyDDDDDDDDyDDF#",
        "#FDDDDDDDDDDDDDDDDDDDDDDDDDDDDF#",
        "#FDggggggggggggggggggggggDDgDDF#",
        "#FDDDDDDDDDDDDDDDDDDDDDDDDDDDDF#",
        "#FDrrrrrrDDDDDDDDDDDDDDDDDDrDDF#",
        "#FDDDDDDDDDDDDDDDDDDDDDDDDDDDDF#",
        "#FDggggggggggggggDDGGDDcccDDDDF#",
        "#FDDDDDDDDDDDDDDDDDDDDDDDDDDDDF#",
        "#ffffffffffffffffffffffffffffff#",
        "....#FF#................#FF#....",
        "....#FF#................#FF#....",
        "...#FFFF#..............#FFFF#...",
    ],
}

# ---- forge 16x24: stone hearth with glowing fire ---------------------------
PROPS["forge"] = {
    "pal": {
        "S": _rgba((122, 116, 126)), "s": _rgba((92, 86, 98)),
        "D": _rgba((54, 48, 58)),
        "F": _rgba((240, 150, 60)), "f": _rgba((250, 208, 96)),
        "R": _rgba((200, 90, 50)),
        "C": _rgba((40, 34, 32)),
    },
    "rows": [
        "...#SSSSSSSSS#..",
        "..#SssssssssSS#.",
        "..#SsDDDDDDsSS#.",
        "..#SsDDDDDDsSS#.",
        "..#SsDfffDDsSS#.",
        "..#SsDfFfFDsSS#.",
        "..#SsFFRFFDsSS#.",
        "..#SsFRRRFDsSS#.",
        "..#SsRRRRRDsSS#.",
        "..#SsCCCCCCsSS#.",
        "..#SssssssssSS#.",
        "..#SSSSSSSSSSS#.",
        "..#sDDDDDDDDDs#.",
        "..#SSSSSSSSSSS#.",
    ],
}

# ---- kanban board 32x20: cork board with three card columns ----------------
PROPS["kanban"] = {
    "pal": {
        "W": WOOD, "w": WOOD_D, "L": WOOD_L,
        "K": _rgba((205, 170, 124)),
        "r": _rgba((222, 130, 120)), "y": _rgba((228, 200, 120)),
        "g": _rgba((150, 200, 130)), "b": _rgba((140, 170, 215)),
        "P": _rgba((245, 240, 228)),
    },
    "rows": [
        "#LLLLLLLLLLLLLLLLLLLLLLLLLLLLLL#",
        "#WKKKKKKKKKKKKKKKKKKKKKKKKKKKKW#",
        "#WKPPPPPPKKPPPPPPKKKPPPPPPKKKKW#",
        "#WKKKKKKKKKKKKKKKKKKKKKKKKKKKKW#",
        "#WKrrrrKKKKyyyyKKKKKggggKKKKKKW#",
        "#WKrrrrKKKKyyyyKKKKKggggKKKKKKW#",
        "#WKKKKKKKKKKKKKKKKKKKKKKKKKKKKW#",
        "#WKrrrrKKKKbbbbKKKKKggggKKKKKKW#",
        "#WKrrrrKKKKbbbbKKKKKggggKKKKKKW#",
        "#WKKKKKKKKKKKKKKKKKKKKKKKKKKKKW#",
        "#WKyyyyKKKKKKKKKKKKKbbbbKKKKKKW#",
        "#WKyyyyKKKKKKKKKKKKKbbbbKKKKKKW#",
        "#WKKKKKKKKKKKKKKKKKKKKKKKKKKKKW#",
        "#WWWWWWWWWWWWWWWWWWWWWWWWWWWWWW#",
        "#LLLLLLLLLLLLLLLLLLLLLLLLLLLLLL#",
        "......#WW#............#WW#......",
        "......#WW#............#WW#......",
        "......#WW#............#WW#......",
        ".....#WWWW#..........#WWWW#.....",
        "................................",
    ],
}


# ---- ore node 16x14: rock with glowing crystal veins (tinted per kind) -----
PROPS["ore-node"] = {
    "pal": {
        "S": _rgba((116, 110, 122)), "s": _rgba((88, 82, 96)),
        "d": _rgba((62, 56, 70)),
        "C": _rgba((150, 220, 255)), "c": _rgba((96, 170, 230)),
    },
    "rows": [
        "....##SSS##.....",
        "..##SSSSSSS#....",
        ".#SSSCcSSSSS#...",
        ".#SSCCcSSssS#...",
        "#SSSCcSSSssS#...",
        "#SsSScSSCCsS#...",
        "#SsSSSSCCcss#...",
        "#SssSSSCcsss#...",
        ".#SsssSSssd#....",
        ".#Sssddsdd#.....",
        "..##ddddd##.....",
        "....#####.......",
    ],
}

# ---- cracked ore node (stage 2) --------------------------------------------
PROPS["ore-node-cracked"] = {
    "pal": {
        "S": _rgba((116, 110, 122)), "s": _rgba((88, 82, 96)),
        "d": _rgba((62, 56, 70)), "K": _rgba((30, 26, 36)),
        "C": _rgba((150, 220, 255)), "c": _rgba((96, 170, 230)),
    },
    "rows": [
        "....##SSS##.....",
        "..##SSKSSSS#....",
        ".#SSSCKSSSSS#...",
        ".#SSCCcKSssS#...",
        "#SSSCcSKSssS#...",
        "#SsSScKSCCsS#...",
        "#SsSSKSCCcss#...",
        "#SssKSSCcsss#...",
        ".#SsssKSssd#....",
        ".#SssddKdd#.....",
        "..##ddddd##.....",
        "....#####.......",
    ],
}

# ---- ladder down 16x16 ------------------------------------------------------
PROPS["ladder-down"] = {
    "pal": {
        "K": _rgba((24, 20, 30)), "W": WOOD, "L": WOOD_L,
    },
    "rows": [
        "#KKKKKKKKKKKKKK#",
        "#KKKKKKKKKKKKKK#",
        "#KK#LWWWWWWL#KK#",
        "#KK#W######W#KK#",
        "#KK#WWWWWWWW#KK#",
        "#KK#W######W#KK#",
        "#KK#WWWWWWWW#KK#",
        "#KK#W######W#KK#",
        "#KK#WWWWWWWW#KK#",
        "#KK#W######W#KK#",
        "#KK#WWWWWWWW#KK#",
        "#KKKKKKKKKKKKKK#",
    ],
}

# ---- mine entrance 32x28: dark arch set into rock ---------------------------
PROPS["mine-entrance"] = {
    "pal": {
        "S": _rgba((124, 118, 130)), "s": _rgba((94, 88, 102)),
        "d": _rgba((66, 60, 74)), "K": _rgba((22, 18, 28)),
        "W": WOOD, "L": WOOD_L,
    },
    "rows": [
        "......####################......",
        "....##SSSSSSSSSSSSSSSSSSSS##....",
        "..##SSSSSSSSSSSSSSSSSSSSSSSS##..",
        ".#SSSSssSSSSSSSSSSSSSSssSSSSSS#.",
        ".#SSsSSSSSSSSSSSSSSSSSSSSsSSSS#.",
        "#SSSSSS##############SSSSSSSSSS#",
        "#SSSSS#KKKKKKKKKKKKKK#SSsSSSSSS#",
        "#SsSS#KKKKKKKKKKKKKKKK#SSSSSdSS#",
        "#SSSS#KKKKKKKKKKKKKKKK#SSSSSSSS#",
        "#SSS#KKKKKKKKKKKKKKKKKK#SSsSSSS#",
        "#SsS#KKKKKKKKKKKKKKKKKK#SSSSSsS#",
        "#SSS#KKKKLKKKKKKKKLKKKK#SdSSSSS#",
        "#SSS#KKKKWKKKKKKKKWKKKK#SSSSSSS#",
        "#SsS#KKKKWKKKKKKKKWKKKK#SSsSSsS#",
        "#SSS#KKKKWKKKKKKKKWKKKK#SSSSSSS#",
        "#SSS#KKKKWKKKKKKKKWKKKK#SSSdSSS#",
        "#SdS#KKKKWKKKKKKKKWKKKK#SSSSSsS#",
        "#SSS#KKKKWKKKKKKKKWKKKK#SsSSSSS#",
        "#SSS#KKKKWKKKKKKKKWKKKK#SSSSSSS#",
        "#SsS#KKKKWKKKKKKKKWKKKK#SSSdSSS#",
        "#SSS#KKKKKKKKKKKKKKKKKK#SSSSSsS#",
        "#SSS#KKKKKKKKKKKKKKKKKK#SsSSSSS#",
        "#SsS#KKKKKKKKKKKKKKKKKK#SSSSSSS#",
        "#SSS#KKKKKKKKKKKKKKKKKK#SSSdSSS#",
        "#dSS#KKKKKKKKKKKKKKKKKK#SSSSSdS#",
        "#SSS#KKKKKKKKKKKKKKKKKK#SsSSSSS#",
        "#ddd#KKKKKKKKKKKKKKKKKK#ddddddd#",
        "################################",
    ],
}


def draw_prop(prop_id: str, scale: int = 1) -> Image.Image:
    spec = PROPS[prop_id]
    pal = spec["pal"]
    rows = spec["rows"]
    h = len(rows)
    w = max(len(r) for r in rows)
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    px = img.load()
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            if ch == ".":
                continue
            px[x, y] = OUTLINE if ch == "#" else pal[ch]
    if scale > 1:
        img = img.resize((w * scale, h * scale), Image.NEAREST)
    return img
