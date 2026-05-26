import Phaser from 'phaser';
import { ZONES, TILE_SIZE, MAP_WIDTH, MAP_HEIGHT, AGENT_COLORS, type ZoneDef } from '../map/zones';
import { useTownStore } from '../../store/townStore';
import type { TownAgent, TownBuilding } from '../../types';

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

        // Stardew-style grass: warm yellow-green base with rich texture
        // Base fill with warm green (more saturated, more yellow than before)
        const baseColors = [0x6aad45, 0x5e9e3d, 0x72b84e, 0x68a843, 0x5c9638];
        g.fillStyle(baseColors[h % baseColors.length], 1);
        g.fillRect(px, py, TILE_SIZE, TILE_SIZE);

        // Layer 2: darker patches for depth (like soil showing through)
        const darkPatches = hash(x, y, 1);
        if (darkPatches % 3 === 0) {
          g.fillStyle(0x4e8a32, 0.4);
          g.fillRect(px + (darkPatches % 8), py + (darkPatches % 6) + 4, 6, 4);
        }

        // Layer 3: individual grass blades (1px wide, 2-4px tall)
        for (let i = 0; i < 6; i++) {
          const bh = hash(x * 7 + i, y * 11 + i, 2);
          const bx = px + (bh % 28) + 2;
          const by = py + (bh % 24) + 4;
          const bladeH = 2 + (bh % 3);
          // Dark blade (shadow side)
          g.fillStyle(0x3d7a28, 0.7);
          g.fillRect(bx, by, 1, bladeH);
          // Light blade (highlight)
          g.fillStyle(0x8acc5e, 0.6);
          g.fillRect(bx + 1, by + 1, 1, bladeH - 1);
        }

        // Layer 4: highlight specks (dew/light)
        if (h % 5 === 0) {
          const hx = px + (hash(x, y, 3) % 24) + 4;
          const hy = py + (hash(x, y, 4) % 20) + 4;
          g.fillStyle(0xb8e87a, 0.5);
          g.fillRect(hx, hy, 1, 1);
        }

        // Layer 5: tiny flowers scattered (Stardew has these)
        if (h % 12 === 0) {
          const fx = px + (hash(x, y, 5) % 22) + 5;
          const fy = py + (hash(x, y, 6) % 18) + 6;
          const flowerPalette = [0xffdd44, 0xff8866, 0xcc88ff, 0x66ccff, 0xff6699];
          g.fillStyle(flowerPalette[h % flowerPalette.length], 0.9);
          g.fillRect(fx, fy, 2, 2);
          g.fillStyle(0x4a8832, 0.8);
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

        // Stardew-style cobblestone: individual stones with mortar gaps
        // Base mortar/dirt color
        g.fillStyle(0x8a7a5a, 1);
        g.fillRect(px, py, TILE_SIZE, TILE_SIZE);

        // Draw individual cobblestones (irregular rectangles)
        const stones = [
          { sx: 1, sy: 1, sw: 7, sh: 6 },
          { sx: 9, sy: 1, sw: 8, sh: 5 },
          { sx: 18, sy: 1, sw: 7, sh: 6 },
          { sx: 26, sy: 1, sw: 5, sh: 5 },
          { sx: 1, sy: 8, sw: 6, sh: 7 },
          { sx: 8, sy: 7, sw: 9, sh: 6 },
          { sx: 18, sy: 8, sw: 7, sh: 7 },
          { sx: 26, sy: 7, sw: 5, sh: 6 },
          { sx: 1, sy: 16, sw: 8, sh: 6 },
          { sx: 10, sy: 14, sw: 7, sh: 7 },
          { sx: 18, sy: 16, sw: 8, sh: 6 },
          { sx: 27, sy: 14, sw: 4, sh: 7 },
          { sx: 1, sy: 23, sw: 6, sh: 6 },
          { sx: 8, sy: 22, sw: 9, sh: 7 },
          { sx: 18, sy: 24, sw: 7, sh: 5 },
          { sx: 26, sy: 22, sw: 5, sh: 7 },
        ];

        for (let i = 0; i < stones.length; i++) {
          const s = stones[i];
          const stoneH = hash(x * 16 + i, y * 16 + i, 1);
          // Stone base color (warm grey-beige variations)
          const stoneColors = [0xb8a888, 0xc4b498, 0xa89878, 0xbcac8c, 0xd0c0a0];
          g.fillStyle(stoneColors[stoneH % stoneColors.length], 1);
          g.fillRect(px + s.sx, py + s.sy, s.sw, s.sh);

          // Top-left highlight (light hits from top-left like Stardew)
          g.fillStyle(0xe0d4b8, 0.4);
          g.fillRect(px + s.sx, py + s.sy, s.sw, 1);
          g.fillRect(px + s.sx, py + s.sy, 1, s.sh);

          // Bottom-right shadow
          g.fillStyle(0x6a5a3a, 0.35);
          g.fillRect(px + s.sx, py + s.sy + s.sh - 1, s.sw, 1);
          g.fillRect(px + s.sx + s.sw - 1, py + s.sy, 1, s.sh);
        }

        // Edge transition: grass-to-path border softening
        if (!this.isPath(x, y - 1)) {
          g.fillStyle(0x5e9e3d, 0.5);
          g.fillRect(px, py, TILE_SIZE, 2);
        }
        if (!this.isPath(x, y + 1)) {
          g.fillStyle(0x5e9e3d, 0.5);
          g.fillRect(px, py + TILE_SIZE - 2, TILE_SIZE, 2);
        }
        if (!this.isPath(x - 1, y)) {
          g.fillStyle(0x5e9e3d, 0.5);
          g.fillRect(px, py, 2, TILE_SIZE);
        }
        if (!this.isPath(x + 1, y)) {
          g.fillStyle(0x5e9e3d, 0.5);
          g.fillRect(px + TILE_SIZE - 2, py, 2, TILE_SIZE);
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

        // Flowers near paths
        if (this.isAdjacentToPath(x, y) && h % 5 === 0) {
          const flowerColors = [0xff6b8a, 0xffb347, 0x87ceeb, 0xdda0dd, 0xffd700];
          g.fillStyle(flowerColors[h % flowerColors.length], 0.9);
          g.fillCircle(px + 8 + (h % 12), py + 8 + (h % 10), 3);
          g.fillStyle(0x3a6a2a, 0.8);
          g.fillRect(px + 8 + (h % 12), py + 11 + (h % 10), 1, 4);
        }

        // Trees at edges and scattered
        if ((x <= 1 || x >= MAP_WIDTH - 2 || y <= 1 || y >= MAP_HEIGHT - 2) && h % 3 === 0) {
          this.drawTree(g, px, py, h);
        } else if (h % 40 === 0 && !this.isAdjacentToPath(x, y)) {
          this.drawTree(g, px, py, h);
        }

        // Lamp posts along main paths
        if (this.isPath(x, y - 1) && h % 15 === 0 && y > 2) {
          this.drawLamp(g, px + 16, py);
        }

        // Benches near plaza
        if (this.isNearZone(x, y, 'plaza') && h % 25 === 0 && !this.isPath(x, y)) {
          this.drawBench(g, px, py);
        }

        // Fences around zone edges
        if (this.isZoneEdge(x, y) && h % 3 === 0) {
          g.fillStyle(0x8b5e3c, 0.8);
          g.fillRect(px + 2, py + 12, 28, 3);
          g.fillRect(px + 6, py + 6, 3, 12);
          g.fillRect(px + 22, py + 6, 3, 12);
        }
      }
    }
    g.setDepth(2);
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
    this.cameras.main.setZoom(1);

    this.input.on('wheel', (_p: any, _gos: any, _dx: number, dy: number) => {
      const cam = this.cameras.main;
      const newZoom = Phaser.Math.Clamp(cam.zoom - dy * 0.001, 0.5, 2.5);
      cam.setZoom(newZoom);
    });
  }

  private setupInput() {
    let dragging = false;
    let dragStart = { x: 0, y: 0 };
    let camStart = { x: 0, y: 0 };

    this.input.on('pointerdown', (pointer: Phaser.Input.Pointer) => {
      if (pointer.rightButtonDown()) {
        dragging = true;
        this.input.setDefaultCursor('grabbing');
        dragStart = { x: pointer.x, y: pointer.y };
        camStart = { x: this.cameras.main.scrollX, y: this.cameras.main.scrollY };
      }
    });

    this.input.on('pointermove', (pointer: Phaser.Input.Pointer) => {
      if (dragging) {
        const dx = (pointer.x - dragStart.x) / this.cameras.main.zoom;
        const dy = (pointer.y - dragStart.y) / this.cameras.main.zoom;
        this.cameras.main.scrollX = camStart.x - dx;
        this.cameras.main.scrollY = camStart.y - dy;
      }
    });

    this.input.on('pointerup', () => {
      dragging = false;
      this.input.setDefaultCursor('default');
    });

    this.input.on('pointerdown', (pointer: Phaser.Input.Pointer) => {
      if (pointer.leftButtonDown()) {
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
    const state = useTownStore.getState().state;
    if (!state) return;
    for (const agent of state.agents) {
      this.updateAgentSprite(agent);
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
    const spriteSize = agent.id === 'player' ? 52 : 48;
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
      y: y - 2,
      duration: 1500 + Math.random() * 500,
      yoyo: true,
      repeat: -1,
      ease: 'Sine.easeInOut',
    });

    return container;
  }

  private onZoneClick(zone: ZoneDef) {
    const state = useTownStore.getState().state;
    if (!state) return;
    const building = state.buildings.find((b) => b.zone === zone.id);
    if (building) {
      useTownStore.getState().selectBuilding(building);
    }
  }
}
