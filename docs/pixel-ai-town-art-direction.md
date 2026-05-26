# Pixel AI Town — Art Direction & Technical Spec

## Visual Style

Cozy top-down / 3/4 perspective pixel art town. All assets are original — no external assets, no copying existing games.

## Grid & Sizing

| Element | Size | Notes |
|---------|------|-------|
| Tile | 32x32 px | Base unit for all map composition |
| Character sprite | 32x32 px | Fits one tile, includes animation frames |
| Building sprite | 96x96 or 128x128 px | Multi-tile footprint, consistent per building type |

## Scaling

- Integer scaling only: 2x, 3x, or 4x
- No fractional scaling (no 1.5x, 2.5x)
- CSS: `image-rendering: pixelated` on all canvas/image elements
- No blur, no CSS smoothing, no anti-aliasing on pixel art
- No mixed resolution — every visible element at the same pixel density

## Color Palette

### Primary

| Name | Hex | Use |
|------|-----|-----|
| Pink | #FFB7B2 | Warm accents, UI highlights |
| Lavender | #DCD6F7 | Memory/knowledge areas, calm zones |
| Blue | #A8D8EA | Water, sky, cool accents |
| Cream | #FFEAA7 | Light surfaces, paths, warmth |
| Mint | #A8E6CF | Nature, growth, health |

### Supporting

| Name | Hex | Use |
|------|-----|-----|
| Dark background | #1A1A2E | Night sky, deep UI panels |
| Grass | #4A7C3F | Ground tiles, vegetation |
| Accent coral | #E94560 | Alerts, important markers, energy |
| Text warm white | #F8E8D4 | All readable text, labels |

## Map Structure

Tile-based composition using layered tilemaps. NOT a one-piece generated background image.

### Layer Order (bottom to top)

1. **Terrain** — grass, dirt, water, sand base tiles
2. **Path** — roads, walkways, bridges
3. **Decoration** — flowers, rocks, fences, small props
4. **Building** — structures, roofs, walls
5. **Character** — agent sprites, NPCs
6. **Effect** — particles, glow, weather
7. **Interaction** — clickable zones, hover indicators
8. **UI Overlay** — panels, tooltips, status bars
9. **Debug** — tile grid, zone boundaries, coordinates (default OFF)

## Sprite Rules

- **Outline**: 1px dark outline on all sprites, consistent across the sheet
- **Light direction**: top-left light source
- **Shadow**: bottom-right cast shadow, 1-2px offset
- **Animation**: frame-based, consistent timing per action type
- **Facing**: 4-directional minimum (down, up, left, right)

## UI Panels

- Pixel-style nine-slice panels for all UI containers
- Not SaaS cards, not rounded modern UI
- Panel borders match the pixel grid
- Text rendered at native pixel size or integer-scaled

## Asset Generation

- **gptimage2 ONLY** — no DALL-E 2, no Midjourney, no Stable Diffusion, no external providers
- No external asset packs or marketplace assets
- No copying sprites from existing games (Stardew Valley, Terraria, Undertale, etc.)
- Every asset entering the game must have an entry in the asset manifest

### Asset Manifest Requirements

Each asset entry must include:
- Filename and path
- Dimensions (px)
- Type (tile, sprite, building, UI, effect)
- Generation prompt used
- Date created
- Layer assignment

## Debug Overlay

- Default state: **OFF**
- When enabled, shows: tile grid lines, zone boundaries, coordinate labels
- Toggle via dev shortcut only
- Never visible in normal gameplay

## Prohibited

- No realistic rendering or photorealism
- No 3D perspective or isometric 3D
- No painterly or illustrated style
- No blurred or anti-aliased pixels
- No copyrighted game assets
- No direct copying of Stardew Valley, Terraria, or any existing game's visual style
- No AI-upscaled assets with fractional detail
- No mixed art styles within the same scene
