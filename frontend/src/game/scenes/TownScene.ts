import Phaser from 'phaser';
import { ZONES, TILE_SIZE, MAP_WIDTH, MAP_HEIGHT, AGENT_COLORS, type ZoneDef } from '../map/zones';
import { useTownStore } from '../../store/townStore';
import { usePixelTownStore } from '../../features/pixel-town/pixelTownStore';
import { TOWN_AREAS } from '../../features/pixel-town/pixelTownMapData';
import type { TownAgent } from '../../types';
import type { TownAgentState } from '../../features/pixel-town/pixelTownTypes';

export class TownScene extends Phaser.Scene {
  private agentSprites: Map<string, Phaser.GameObjects.Container> = new Map();
  private syncTimer: Phaser.Time.TimerEvent | null = null;

  constructor() {
    super({ key: 'TownScene' });
  }

  preload() {
    for (const key of Object.keys(AGENT_COLORS)) {
      this.load.image(`agent_${key}`, `/assets/town/agents/agent_${key}.png`);
    }
    for (const zone of ZONES) {
      this.load.image(`building_${zone.id}`, `/assets/town/buildings/building_${zone.id}.png`);
    }
  }

  create() {
    this.drawSky();
    this.drawTerrain();
    this.drawPaths();
    this.drawDecorations();
    this.drawBuildings();
    this.setupCamera();
    this.setupInput();

    this.syncTimer = this.time.addEvent({
      delay: 200,
      loop: true,
      callback: () => this.syncState(),
    });

    // Debug grid — only visible when debug mode is on
    this.drawDebugGrid();
  }

  private debugGraphics: Phaser.GameObjects.Graphics | null = null;

  private drawDebugGrid() {
    this.debugGraphics = this.add.graphics();
    this.debugGraphics.setDepth(9999);
    this.debugGraphics.setVisible(false);

    // Check debug state periodically
    this.time.addEvent({
      delay: 500,
      loop: true,
      callback: () => {
        const debug = usePixelTownStore.getState().config.debugMode;
        if (this.debugGraphics) {
          if (debug && !this.debugGraphics.visible) {
            this.debugGraphics.clear();
            // Grid lines
            this.debugGraphics.lineStyle(0.5, 0xffffff, 0.15);
            for (let x = 0; x <= MAP_WIDTH; x++) {
              this.debugGraphics.lineBetween(x * TILE_SIZE, 0, x * TILE_SIZE, MAP_HEIGHT * TILE_SIZE);
            }
            for (let y = 0; y <= MAP_HEIGHT; y++) {
              this.debugGraphics.lineBetween(0, y * TILE_SIZE, MAP_WIDTH * TILE_SIZE, y * TILE_SIZE);
            }
            // Zone boundaries
            this.debugGraphics.lineStyle(1.5, 0xffffff, 0.4);
            for (const zone of ZONES) {
              this.debugGraphics.strokeRect(
                zone.x * TILE_SIZE, zone.y * TILE_SIZE,
                zone.w * TILE_SIZE, zone.h * TILE_SIZE
              );
            }
            this.debugGraphics.setVisible(true);
          } else if (!debug && this.debugGraphics.visible) {
            this.debugGraphics.setVisible(false);
          }
        }
      },
    });
  }

  shutdown() {
    this.syncTimer?.destroy();
    this.agentSprites.clear();
  }

  private drawSky() {
    const g = this.add.graphics();
    const skyH = MAP_HEIGHT * TILE_SIZE;
    const skyW = MAP_WIDTH * TILE_SIZE;
    for (let i = 0; i < 20; i++) {
      const t = i / 20;
      const r = Math.floor(135 + t * 40);
      const gr = Math.floor(206 + t * 20);
      const b = Math.floor(235 - t * 30);
      const color = (r << 16) | (gr << 8) | b;
      g.fillStyle(color, 0.3);
      g.fillRect(0, i * (skyH / 20), skyW, skyH / 20);
    }
    g.setDepth(-10);
  }

  private drawTerrain() {
    const g = this.add.graphics();
    const hash = (x: number, y: number, seed: number) => Math.abs((x * 374761 + y * 668265 + seed * 12347) ^ ((x * 13) + (y * 7))) % 1000;

    for (let y = 0; y < MAP_HEIGHT; y++) {
      for (let x = 0; x < MAP_WIDTH; x++) {
        const h = hash(x, y, 0);
        const px = x * TILE_SIZE;
        const py = y * TILE_SIZE;

        if (this.isWater(x, y)) {
          this.drawWaterTile(g, px, py, h);
          continue;
        }

        // Smooth grass: use position-based color blending for natural look
        const baseG = 0x5ea03d;
        // Subtle variation based on large-scale noise (not per-tile)
        const regionHash = Math.abs(Math.floor(x / 3) * 17 + Math.floor(y / 3) * 31) % 100;
        const rShift = (regionHash % 3) - 1;
        const gShift = (regionHash % 5) - 2;
        const r = ((baseG >> 16) & 0xff) + rShift * 2;
        const green = ((baseG >> 8) & 0xff) + gShift * 3 + (h % 8) - 4;
        const b = (baseG & 0xff) + rShift;
        const tileColor = (Math.max(0, Math.min(255, r)) << 16) | (Math.max(0, Math.min(255, green)) << 8) | Math.max(0, Math.min(255, b));
        g.fillStyle(tileColor, 1);
        g.fillRect(px, py, TILE_SIZE, TILE_SIZE);

        // Subtle grass texture (very light, not per-tile-obvious)
        if (h % 4 === 0) {
          g.fillStyle(0x4e8a32, 0.2);
          g.fillRect(px + (h % 12) + 4, py + (h % 10) + 6, 4, 3);
        }

        // Sparse grass blades
        for (let i = 0; i < 3; i++) {
          const bh = hash(x * 7 + i, y * 11 + i, 2);
          const bx = px + (bh % 28) + 2;
          const by = py + (bh % 24) + 4;
          const bladeH = 2 + (bh % 2);
          g.fillStyle(0x4a7a2a, 0.35);
          g.fillRect(bx, by, 1, bladeH);
        }

        // Rare highlight specks
        if (h % 8 === 0) {
          g.fillStyle(0x8ecc5e, 0.3);
          g.fillRect(px + (hash(x, y, 3) % 24) + 4, py + (hash(x, y, 4) % 20) + 4, 1, 1);
        }

        // Scattered flowers (less frequent)
        if (h % 18 === 0) {
          const fx = px + (hash(x, y, 5) % 22) + 5;
          const fy = py + (hash(x, y, 6) % 18) + 6;
          const flowerPalette = [0xffdd44, 0xff8866, 0xcc88ff, 0x66ccff, 0xff6699];
          g.fillStyle(flowerPalette[h % flowerPalette.length], 0.7);
          g.fillRect(fx, fy, 2, 2);
          g.fillStyle(0x4a8832, 0.6);
          g.fillRect(fx, fy + 2, 1, 2);
        }
      }
    }
    g.setDepth(0);
  }

  private drawWaterTile(g: Phaser.GameObjects.Graphics, px: number, py: number, h: number) {
    // Deep water base
    g.fillStyle(0x3a7ab8, 1);
    g.fillRect(px, py, TILE_SIZE, TILE_SIZE);
    // Lighter ripple bands
    g.fillStyle(0x4a8fc8, 0.6);
    g.fillRect(px + 2, py + (h % 6) + 4, 12, 2);
    g.fillRect(px + 8, py + (h % 8) + 14, 10, 2);
    // Highlight sparkle
    g.fillStyle(0x8ac8e8, 0.4);
    g.fillRect(px + (h % 10) + 6, py + (h % 12) + 2, 2, 1);
    // Dark depth
    g.fillStyle(0x2a5a88, 0.3);
    g.fillRect(px + 4, py + 20, 8, 4);
  }

  private drawPaths() {
    const g = this.add.graphics();
    const hash = (x: number, y: number, s: number) => Math.abs(x * 31 + y * 17 + s * 53) % 100;

    for (let y = 0; y < MAP_HEIGHT; y++) {
      for (let x = 0; x < MAP_WIDTH; x++) {
        if (!this.isPath(x, y)) continue;
        const px = x * TILE_SIZE;
        const py = y * TILE_SIZE;
        const h = hash(x, y, 0);

        // Warm dirt path base (not grey — earthy brown)
        g.fillStyle(0xa08860, 1);
        g.fillRect(px, py, TILE_SIZE, TILE_SIZE);

        // Subtle stone texture
        const stoneColors = [0xb89870, 0xc4a880, 0xa89068, 0xb8a078];
        for (let i = 0; i < 4; i++) {
          const sh = hash(x * 4 + i, y * 4 + i, 1);
          const sx = (sh % 6) * 5 + 1;
          const sy = (sh % 5) * 6 + 1;
          g.fillStyle(stoneColors[sh % stoneColors.length], 0.6);
          g.fillRect(px + sx, py + sy, 5 + (sh % 3), 4 + (sh % 3));
        }

        // Light highlight on top edge of stones
        if (h % 3 === 0) {
          g.fillStyle(0xd4c4a0, 0.3);
          g.fillRect(px + 4 + (h % 8), py + 2 + (h % 4), 8, 1);
        }

        // Grass-to-path soft edge (blend with surrounding grass)
        if (!this.isPath(x, y - 1)) {
          g.fillStyle(0x5ea03d, 0.45);
          g.fillRect(px, py, TILE_SIZE, 3);
          g.fillStyle(0x5ea03d, 0.2);
          g.fillRect(px, py + 3, TILE_SIZE, 2);
        }
        if (!this.isPath(x, y + 1)) {
          g.fillStyle(0x5ea03d, 0.45);
          g.fillRect(px, py + TILE_SIZE - 3, TILE_SIZE, 3);
          g.fillStyle(0x5ea03d, 0.2);
          g.fillRect(px, py + TILE_SIZE - 5, TILE_SIZE, 2);
        }
        if (!this.isPath(x - 1, y)) {
          g.fillStyle(0x5ea03d, 0.45);
          g.fillRect(px, py, 3, TILE_SIZE);
          g.fillStyle(0x5ea03d, 0.2);
          g.fillRect(px + 3, py, 2, TILE_SIZE);
        }
        if (!this.isPath(x + 1, y)) {
          g.fillStyle(0x5ea03d, 0.45);
          g.fillRect(px + TILE_SIZE - 3, py, 3, TILE_SIZE);
          g.fillStyle(0x5ea03d, 0.2);
          g.fillRect(px + TILE_SIZE - 5, py, 2, TILE_SIZE);
        }
      }
    }
    g.setDepth(1);
  }

  private drawDecorations() {
    const g = this.add.graphics();
    const hash = (x: number, y: number) => Math.abs(x * 997 + y * 613) % 1000;

    for (let y = 0; y < MAP_HEIGHT; y++) {
      for (let x = 0; x < MAP_WIDTH; x++) {
        const h = hash(x, y);
        const px = x * TILE_SIZE;
        const py = y * TILE_SIZE;

        if (this.isPath(x, y) || this.isWater(x, y)) continue;
        if (this.isInsideBuilding(x, y)) continue;

        // Dense flower patches near paths
        if (this.isAdjacentToPath(x, y) && h % 3 === 0) {
          const flowerColors = [0xff6b8a, 0xffb347, 0x87ceeb, 0xdda0dd, 0xffd700, 0xff9eaa, 0xffcc66];
          for (let i = 0; i < 3; i++) {
            const fh = hash(x * 3 + i, y * 5 + i);
            const fx = px + (fh % 24) + 4;
            const fy = py + (fh % 20) + 6;
            g.fillStyle(flowerColors[fh % flowerColors.length], 0.85);
            g.fillCircle(fx, fy, 2);
            g.fillStyle(0x3a6a2a, 0.7);
            g.fillRect(fx, fy + 2, 1, 3);
          }
        }

        // Bushes (small round green clusters)
        if (h % 12 === 0 && !this.isAdjacentToPath(x, y)) {
          this.drawBush(g, px, py, h);
        }

        // Trees — dense at edges, scattered in open areas
        if ((x <= 1 || x >= MAP_WIDTH - 2 || y <= 1 || y >= MAP_HEIGHT - 2) && h % 2 === 0) {
          this.drawTree(g, px, py, h);
        } else if (h % 20 === 0 && !this.isAdjacentToPath(x, y)) {
          this.drawTree(g, px, py, h);
        }

        // Small pine trees (variety)
        if ((x <= 2 || x >= MAP_WIDTH - 3) && h % 4 === 1) {
          this.drawPineTree(g, px, py, h);
        }

        // Lamp posts along paths
        if (this.isPath(x, y - 1) && h % 10 === 0 && y > 2) {
          this.drawLamp(g, px + 16, py);
        }

        // Benches near plaza and buildings
        if ((this.isNearZone(x, y, 'plaza') || this.isNearZone(x, y, 'dream_garden')) && h % 18 === 0 && !this.isPath(x, y)) {
          this.drawBench(g, px, py);
        }

        // Rocks scattered
        if (h % 25 === 0 && !this.isAdjacentToPath(x, y)) {
          this.drawRock(g, px, py, h);
        }

        // Mushrooms in shady areas (near trees/edges)
        if ((x <= 3 || x >= MAP_WIDTH - 4) && h % 14 === 0) {
          this.drawMushroom(g, px, py, h);
        }

        // Flower beds around zone edges
        if (this.isZoneEdge(x, y) && h % 3 === 0) {
          const flowerColors = [0xff9eaa, 0xffcc66, 0xaa88ff, 0x88ddff, 0xff6b8a];
          for (let i = 0; i < 2; i++) {
            const fh = hash(x + i * 7, y + i * 3);
            g.fillStyle(flowerColors[fh % flowerColors.length], 0.75);
            g.fillCircle(px + 6 + (fh % 20), py + 8 + (fh % 16), 2);
          }
          // Small leaf/grass tuft
          g.fillStyle(0x4a8832, 0.6);
          g.fillRect(px + 14 + (h % 8), py + 20, 3, 4);
          g.fillRect(px + 12 + (h % 8), py + 22, 7, 2);
        }

        // Wooden signs near buildings
        if (this.isZoneEdge(x, y) && this.isAdjacentToPath(x, y) && h % 20 === 0) {
          this.drawSign(g, px, py);
        }

        // Fence posts along zone boundaries (sparse, natural)
        if (this.isZoneEdge(x, y) && h % 8 === 0 && !this.isAdjacentToPath(x, y)) {
          this.drawFencePost(g, px, py);
        }
      }
    }
    g.setDepth(2);
  }

  private drawBush(g: Phaser.GameObjects.Graphics, px: number, py: number, h: number) {
    const greens = [0x3a7a28, 0x4a8a38, 0x2d6b1a];
    g.fillStyle(greens[h % 3], 0.9);
    g.fillCircle(px + 16, py + 20, 7);
    g.fillCircle(px + 10, py + 22, 5);
    g.fillCircle(px + 22, py + 21, 5);
    // Highlight
    g.fillStyle(0x6aaa4a, 0.4);
    g.fillCircle(px + 14, py + 18, 3);
  }

  private drawPineTree(g: Phaser.GameObjects.Graphics, px: number, py: number, h: number) {
    // Trunk
    g.fillStyle(0x5a3a20, 1);
    g.fillRect(px + 14, py + 22, 4, 10);
    // Triangular canopy layers
    const green = h % 2 === 0 ? 0x2a5a18 : 0x1a4a10;
    g.fillStyle(green, 1);
    g.fillTriangle(px + 16, py + 2, px + 6, py + 16, px + 26, py + 16);
    g.fillTriangle(px + 16, py + 8, px + 8, py + 22, px + 24, py + 22);
    // Snow/highlight on tips
    g.fillStyle(0x5a9a48, 0.5);
    g.fillTriangle(px + 16, py + 2, px + 12, py + 8, px + 20, py + 8);
  }

  private drawRock(g: Phaser.GameObjects.Graphics, px: number, py: number, h: number) {
    const greys = [0x8a8a7a, 0x9a9a8a, 0x7a7a6a];
    g.fillStyle(greys[h % 3], 0.9);
    g.fillEllipse(px + 16 + (h % 6), py + 22, 8 + (h % 4), 5 + (h % 3));
    // Highlight
    g.fillStyle(0xb0b0a0, 0.4);
    g.fillEllipse(px + 14 + (h % 6), py + 20, 4, 2);
  }

  private drawMushroom(g: Phaser.GameObjects.Graphics, px: number, py: number, h: number) {
    const capColors = [0xe84040, 0xd4a040, 0xc080c0];
    // Stem
    g.fillStyle(0xf0e8d0, 0.9);
    g.fillRect(px + 14 + (h % 6), py + 22, 3, 5);
    // Cap
    g.fillStyle(capColors[h % 3], 0.9);
    g.fillCircle(px + 15 + (h % 6), py + 21, 4);
    // Spots
    g.fillStyle(0xffffff, 0.6);
    g.fillCircle(px + 14 + (h % 6), py + 20, 1);
  }

  private drawSign(g: Phaser.GameObjects.Graphics, px: number, py: number) {
    // Post
    g.fillStyle(0x6b4530, 1);
    g.fillRect(px + 14, py + 14, 3, 14);
    // Board
    g.fillStyle(0x8b6540, 1);
    g.fillRect(px + 8, py + 10, 16, 8);
    g.fillStyle(0xa07850, 0.6);
    g.fillRect(px + 9, py + 11, 14, 6);
  }

  private drawFencePost(g: Phaser.GameObjects.Graphics, px: number, py: number) {
    g.fillStyle(0x7a5030, 0.85);
    g.fillRect(px + 14, py + 12, 3, 14);
    g.fillRect(px + 12, py + 10, 7, 3);
  }

  private drawTree(g: Phaser.GameObjects.Graphics, px: number, py: number, h: number) {
    // Trunk
    g.fillStyle(0x6b4530, 1);
    g.fillRect(px + 12, py + 16, 8, 16);
    // Canopy
    const greens = [0x2d6b1a, 0x3a7a28, 0x4a8a38];
    g.fillStyle(greens[h % 3], 1);
    g.fillCircle(px + 16, py + 10, 12);
    g.fillStyle(0x5a9a48, 0.6);
    g.fillCircle(px + 12, py + 8, 6);
    g.fillCircle(px + 20, py + 12, 5);
  }

  private drawLamp(g: Phaser.GameObjects.Graphics, px: number, py: number) {
    // Post
    g.fillStyle(0x4a4a4a, 1);
    g.fillRect(px - 1, py - 20, 3, 22);
    // Light
    g.fillStyle(0xffe4a0, 0.9);
    g.fillCircle(px, py - 22, 4);
    // Glow
    g.fillStyle(0xffe4a0, 0.15);
    g.fillCircle(px, py - 22, 12);
  }

  private drawBench(g: Phaser.GameObjects.Graphics, px: number, py: number) {
    g.fillStyle(0x8b5e3c, 1);
    g.fillRect(px + 4, py + 18, 24, 4);
    g.fillRect(px + 4, py + 14, 24, 3);
    g.fillStyle(0x5a3a20, 1);
    g.fillRect(px + 6, py + 22, 3, 6);
    g.fillRect(px + 23, py + 22, 3, 6);
  }

  private drawBuildings() {
    for (const zone of ZONES) {
      const x = zone.x * TILE_SIZE;
      const y = zone.y * TILE_SIZE;
      const w = zone.w * TILE_SIZE;
      const h = zone.h * TILE_SIZE;

      // Building image
      const building = this.add.image(x + w / 2, y + h / 2 + 4, `building_${zone.id}`);
      const maxDisplay = Math.min(w, h) * 0.85;
      building.setDisplaySize(maxDisplay, maxDisplay);
      building.setDepth(y + h);
      building.setInteractive({ useHandCursor: true });
      building.on('pointerdown', (_pointer: Phaser.Input.Pointer, _localX: number, _localY: number, event: Phaser.Types.Input.EventData) => {
        event.stopPropagation();
        this.onZoneClick(zone);
      });

      // Zone label as a sign post
      const labelY = y + h + 8;
      const signBg = this.add.graphics();
      const textWidth = zone.nameCn.length * 13 + 16;
      signBg.fillStyle(0x6b4530, 0.9);
      signBg.fillRoundedRect(x + w / 2 - textWidth / 2, labelY - 2, textWidth, 18, 3);
      signBg.lineStyle(1, 0x4a3020, 0.8);
      signBg.strokeRoundedRect(x + w / 2 - textWidth / 2, labelY - 2, textWidth, 18, 3);
      signBg.setDepth(y + h + 10);

      const label = this.add.text(x + w / 2, labelY + 7, zone.nameCn, {
        fontSize: '11px',
        color: '#fff8dc',
        fontFamily: '"Microsoft YaHei", sans-serif',
        align: 'center',
      });
      label.setOrigin(0.5);
      label.setDepth(y + h + 11);
    }
  }

  private isPath(x: number, y: number): boolean {
    // Main horizontal road
    if (y >= 14 && y <= 15 && x >= 3 && x <= 36) return true;
    // Main vertical road
    if (x >= 19 && x <= 20 && y >= 2 && y <= 27) return true;
    // Branch to each zone
    for (const z of ZONES) {
      const zx = z.x + Math.floor(z.w / 2);
      const zy = z.y + Math.floor(z.h / 2);
      if ((x === zx || x === zx + 1) && y >= Math.min(zy, 14) && y <= Math.max(zy, 15)) return true;
      if ((y === zy || y === zy + 1) && x >= Math.min(zx, 19) && x <= Math.max(zx, 20)) return true;
    }
    return false;
  }

  private isWater(x: number, y: number): boolean {
    const cx = 19, cy = 15;
    const dx = x - cx, dy = y - cy;
    return dx * dx + dy * dy <= 3;
  }

  private isInsideBuilding(x: number, y: number): boolean {
    for (const z of ZONES) {
      if (x >= z.x + 1 && x < z.x + z.w - 1 && y >= z.y + 1 && y < z.y + z.h - 1) return true;
    }
    return false;
  }

  private isAdjacentToPath(x: number, y: number): boolean {
    return this.isPath(x - 1, y) || this.isPath(x + 1, y) || this.isPath(x, y - 1) || this.isPath(x, y + 1);
  }

  private isNearZone(x: number, y: number, zoneId: string): boolean {
    const z = ZONES.find(z => z.id === zoneId);
    if (!z) return false;
    return x >= z.x - 2 && x <= z.x + z.w + 1 && y >= z.y - 2 && y <= z.y + z.h + 1;
  }

  private isZoneEdge(x: number, y: number): boolean {
    for (const z of ZONES) {
      if ((x === z.x || x === z.x + z.w - 1) && y >= z.y && y < z.y + z.h) return true;
      if ((y === z.y || y === z.y + z.h - 1) && x >= z.x && x < z.x + z.w) return true;
    }
    return false;
  }

  private setupCamera() {
    this.cameras.main.setBounds(0, 0, MAP_WIDTH * TILE_SIZE, MAP_HEIGHT * TILE_SIZE);
    this.cameras.main.centerOn((MAP_WIDTH * TILE_SIZE) / 2, (MAP_HEIGHT * TILE_SIZE) / 2);
    this.cameras.main.setZoom(1.5);

    this.input.on('wheel', (_p: any, _gos: any, _dx: number, dy: number) => {
      const cam = this.cameras.main;
      const zoomDelta = dy > 0 ? -0.15 : 0.15;
      const newZoom = Phaser.Math.Clamp(cam.zoom + zoomDelta, 0.6, 3.5);
      this.tweens.add({
        targets: cam,
        zoom: newZoom,
        duration: 150,
        ease: 'Sine.easeOut',
      });
    });
  }

  private setupInput() {
    let dragging = false;
    let dragStart = { x: 0, y: 0 };
    let camStart = { x: 0, y: 0 };
    let dragMoved = false;

    this.input.on('pointerdown', (pointer: Phaser.Input.Pointer) => {
      if (pointer.leftButtonDown() || pointer.rightButtonDown() || pointer.middleButtonDown()) {
        dragging = true;
        dragMoved = false;
        this.input.setDefaultCursor('grabbing');
        dragStart = { x: pointer.x, y: pointer.y };
        camStart = { x: this.cameras.main.scrollX, y: this.cameras.main.scrollY };
      }
    });

    this.input.on('pointermove', (pointer: Phaser.Input.Pointer) => {
      if (dragging) {
        const dx = (pointer.x - dragStart.x) / this.cameras.main.zoom;
        const dy = (pointer.y - dragStart.y) / this.cameras.main.zoom;
        if (Math.abs(dx) > 3 || Math.abs(dy) > 3) {
          dragMoved = true;
        }
        this.cameras.main.scrollX = camStart.x - dx;
        this.cameras.main.scrollY = camStart.y - dy;
      }
    });

    this.input.on('pointerup', (pointer: Phaser.Input.Pointer) => {
      const wasDragging = dragging;
      dragging = false;
      this.input.setDefaultCursor('default');

      // Only trigger click actions if we didn't drag
      if (wasDragging && !dragMoved) {
        const worldX = Math.floor(pointer.worldX / TILE_SIZE);
        const worldY = Math.floor(pointer.worldY / TILE_SIZE);
        if (worldX >= 0 && worldX < MAP_WIDTH && worldY >= 0 && worldY < MAP_HEIGHT) {
          fetch('/api/town/player/move', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ x: worldX, y: worldY }),
          })
            .then((response) => response.ok ? response.json() : null)
            .then((data) => {
              if (data?.state) {
                useTownStore.getState().setState(data.state);
              }
            })
            .catch((error) => console.warn('[town] move failed:', error));
        }
      }
    });
  }

  private syncState() {
    const pixelStore = usePixelTownStore.getState();
    const agents = pixelStore.agents;
    if (!agents || agents.length === 0) {
      const legacyState = useTownStore.getState().state;
      if (!legacyState) return;
      for (const agent of legacyState.agents) {
        this.updateAgentSprite(agent);
      }
      return;
    }
    for (const agent of agents) {
      this.updateAgentSpriteV2(agent);
    }
  }

  private updateAgentSprite(agent: TownAgent) {
    let container = this.agentSprites.get(agent.id);
    if (!container) {
      container = this.createAgentSprite(agent);
      this.agentSprites.set(agent.id, container);
    }

    const targetX = agent.position[0] * TILE_SIZE + TILE_SIZE / 2;
    const targetY = agent.position[1] * TILE_SIZE + TILE_SIZE / 2;

    const speed = 0.15;
    container.x += (targetX - container.x) * speed;
    container.y += (targetY - container.y) * speed;
    container.setDepth(container.y + 1000);

    const bubble = container.getByName('bubble') as Phaser.GameObjects.Text;
    if (bubble) {
      const icons: Record<string, string> = {
        idle: '💤', walking: '🚶', thinking: '💭',
        reading_memory: '📖', learning_skill: '🔧', chatting: '💬',
        working: '⚡', resting: '😴', exploring: '🔍',
      };
      bubble.setText(icons[agent.current_activity] || '');
    }
  }

  private createAgentSprite(agent: TownAgent): Phaser.GameObjects.Container {
    const x = agent.position[0] * TILE_SIZE + TILE_SIZE / 2;
    const y = agent.position[1] * TILE_SIZE + TILE_SIZE / 2;

    const shadow = this.add.ellipse(0, 18, 30, 10, 0x132414, 0.32);
    const body = this.add.image(0, 0, agent.sprite_key || `agent_${agent.id}`);
    const spriteSize = agent.id === 'player' ? 60 : 56;
    body.setDisplaySize(spriteSize, spriteSize);
    body.setName('body');

    const nameLabel = this.add.text(0, -32, agent.name.split(' ')[0], {
      fontSize: '10px',
      color: '#fff8dc',
      fontFamily: '"Microsoft YaHei", sans-serif',
      stroke: '#000000',
      strokeThickness: 2,
    });
    nameLabel.setOrigin(0.5);

    const bubble = this.add.text(16, -28, '', {
      fontSize: '12px',
      stroke: '#000000',
      strokeThickness: 2,
    });
    bubble.setOrigin(0.5);
    bubble.setName('bubble');

    const container = this.add.container(x, y, [shadow, body, nameLabel, bubble]);
    container.setSize(34, 40);
    container.setDepth(y + 1000);
    container.setInteractive(new Phaser.Geom.Circle(0, 0, 18), Phaser.Geom.Circle.Contains);

    container.on('pointerdown', (_pointer: Phaser.Input.Pointer, _localX: number, _localY: number, event: Phaser.Types.Input.EventData) => {
      event.stopPropagation();
      useTownStore.getState().selectAgent(agent);
    });

    container.on('pointerover', () => {
      body.setDisplaySize(spriteSize * 1.12, spriteSize * 1.12);
      this.input.setDefaultCursor('pointer');
    });
    container.on('pointerout', () => {
      body.setDisplaySize(spriteSize, spriteSize);
      this.input.setDefaultCursor('default');
    });

    this.tweens.add({
      targets: container,
      y: y - 3,
      duration: 2000 + Math.random() * 800,
      yoyo: true,
      repeat: -1,
      ease: 'Sine.easeInOut',
    });

    return container;
  }

  private onZoneClick(zone: ZoneDef) {
    const area = TOWN_AREAS.find(a => a.id === zone.id);
    if (area) {
      usePixelTownStore.getState().selectArea(area);
    }
    const state = useTownStore.getState().state;
    if (!state) return;
    const building = state.buildings.find((b) => b.zone === zone.id);
    if (building) {
      useTownStore.getState().selectBuilding(building);
    }
  }

  private updateAgentSpriteV2(agent: TownAgentState) {
    let container = this.agentSprites.get(agent.id);
    if (!container) {
      container = this.createAgentSpriteV2(agent);
      this.agentSprites.set(agent.id, container);
    }

    const targetX = agent.position[0] * TILE_SIZE + TILE_SIZE / 2;
    const targetY = agent.position[1] * TILE_SIZE + TILE_SIZE / 2;

    const speed = 0.15;
    container.x += (targetX - container.x) * speed;
    container.y += (targetY - container.y) * speed;
    container.setDepth(container.y + 1000);

    const bubble = container.getByName('bubble') as Phaser.GameObjects.Text;
    if (bubble) {
      const icons: Record<string, string> = {
        idle: '💤', walking: '🚶', thinking: '💭',
        reading_memory: '📖', learning_skill: '🔧', chatting: '💬',
        working: '⚡', resting: '😴', exploring: '🔍',
        debugging: '🐛', reporting: '📋', dreaming: '🌙',
        observing: '👁️', building: '🏗️', reviewing: '📝',
      };
      bubble.setText(icons[agent.activity] || '');
    }
  }

  private createAgentSpriteV2(agent: TownAgentState): Phaser.GameObjects.Container {
    const x = agent.position[0] * TILE_SIZE + TILE_SIZE / 2;
    const y = agent.position[1] * TILE_SIZE + TILE_SIZE / 2;

    const shadow = this.add.ellipse(0, 18, 30, 10, 0x132414, 0.32);
    const body = this.add.image(0, 0, agent.spriteId || `agent_${agent.id}`);
    const spriteSize = agent.id === 'player' ? 48 : 44;
    body.setDisplaySize(spriteSize, spriteSize);
    body.setName('body');

    const nameLabel = this.add.text(0, -26, agent.name.split(' ')[0], {
      fontSize: '9px',
      color: '#fff8dc',
      fontFamily: '"Microsoft YaHei", sans-serif',
      stroke: '#000000',
      strokeThickness: 2,
    });
    nameLabel.setOrigin(0.5);

    const bubble = this.add.text(16, -28, '', {
      fontSize: '12px',
      stroke: '#000000',
      strokeThickness: 2,
    });
    bubble.setOrigin(0.5);
    bubble.setName('bubble');

    const container = this.add.container(x, y, [shadow, body, nameLabel, bubble]);
    container.setSize(34, 40);
    container.setDepth(y + 1000);
    container.setInteractive(new Phaser.Geom.Circle(0, 0, 18), Phaser.Geom.Circle.Contains);

    container.on('pointerdown', (_pointer: Phaser.Input.Pointer, _localX: number, _localY: number, event: Phaser.Types.Input.EventData) => {
      event.stopPropagation();
      usePixelTownStore.getState().selectAgent(agent);
    });

    container.on('pointerover', () => {
      body.setDisplaySize(spriteSize * 1.12, spriteSize * 1.12);
      this.input.setDefaultCursor('pointer');
    });
    container.on('pointerout', () => {
      body.setDisplaySize(spriteSize, spriteSize);
      this.input.setDefaultCursor('default');
    });

    this.tweens.add({
      targets: container,
      y: y - 3,
      duration: 2000 + Math.random() * 800,
      yoyo: true,
      repeat: -1,
      ease: 'Sine.easeInOut',
    });

    return container;
  }
}
