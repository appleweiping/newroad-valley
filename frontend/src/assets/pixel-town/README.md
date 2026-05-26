# Pixel AI Town — Dedicated Asset Directory

This directory manages all visual assets for the Pixel AI Town project.

## Asset Source Policy

- **All new art must come through gptimage2 or user-provided original assets**
- No external/network assets allowed
- No other image providers (DALL-E, Midjourney, Stable Diffusion, etc.)
- No whole-map background images — maps are composed from tilesets
- No copying existing game assets from other projects or games
- Every asset is original, generated specifically for this project

## Asset Consistency Rules

All assets must follow unified standards:

| Property | Standard |
|----------|----------|
| Tile size | 32x32 px |
| Palette | Warm, limited (max ~16 colors per asset set) |
| Outline | 1px dark outline, consistent across all assets |
| Lighting | Top-left light source, soft shadows |
| Scale | 1x pixel scale, no sub-pixel rendering |
| Anti-aliasing | None — crisp pixels only |
| Style | Cozy pixel art, top-down / 3/4 view |

## Registration & Usage

- All assets **must** be registered in `manifest.json`
- Frontend code can **only** use assets through the manifest or explicit import
- Each asset entry tracks its gptimage2 prompt file for reproducibility

## Directory Structure

```
pixel-town/
├── README.md              ← this file
├── manifest.json          ← asset registry
└── prompts/               ← gptimage2 generation prompts
    ├── gptimage2-terrain.md
    ├── gptimage2-paths.md
    ├── gptimage2-buildings.md
    ├── gptimage2-props.md
    ├── gptimage2-player.md
    ├── gptimage2-agents.md
    └── gptimage2-ui.md
```

## Production Assets

Existing production assets live at `/public/assets/town/` and were all generated via gptimage2. They are the current active set used by the game frontend.
