import Phaser from "phaser";
import { TILE, MAP_W, MAP_H, BUILDINGS, AGENTS, PLAZA, FARM, type AgentDef } from "@/data/town";
import { generateTown, type TownLayout } from "@/game/world/mapgen";
import { findPath } from "@/game/world/astar";
import { INTERIOR_BY_BUILDING } from "@/data/interiors";
import { bus } from "@/shared/bus";
import { audio, AUDIO_FILES } from "@/game/audio";
import { currentMode, getData, postData } from "@/shared/api";
import { loadSave, writeSave, spendStamina, restoreStamina, currentStamina, type DemoCrop, type InvItem } from "@/shared/save";
import { touchState } from "@/shared/touch";

/** a multi-agent signal as the town sees it (bridge /api/town/signals) */
interface TownSignal {
  id: string;
  from: string;
  to: string;
  summary: string;
  type?: string;
  at?: string;
}

const WATER_FRAMES = 4;
const DAY_MINUTES = 24 * 60;
/** one in-game day = 12 real minutes */
const MINUTES_PER_SECOND = DAY_MINUTES / (12 * 60);

/** lpc crop columns that read nicely at town scale */
const CROP_VARIETIES = [0, 1, 2, 5, 6, 8, 9];
/** growth stage -> lpc frame row base (sheet is 32 columns wide; growth
 * stages live on visual rows 1/3/5/7 => frame rows 1,3,5,7 * 32) */
const STAGE_ROW = [0, 32, 96, 160, 224];
/** harvested product icons live on visual row 11 */
const PRODUCT_ROW = 352;

type Duty =
  | { kind: "anchor" }
  | { kind: "plaza" }
  | { kind: "building"; id: string }
  | { kind: "inn" };

/** where each resident works (buildings with interiors hide them inside) */
const WORKPLACE: Record<string, string> = {
  opus: "town-hall",
  codex: "town-hall",
  sonnet: "memory-library",
  aris: "research-hall",
  pixelcat: "skill-workshop",
  fable: "memory-library",
};

function dutyFor(agentId: string, hour: number): Duty {
  if (hour >= 21 || hour < 6) return { kind: "inn" };
  if (hour >= 12 && hour < 14) return { kind: "plaza" };
  if ((hour >= 9 && hour < 12) || (hour >= 14 && hour < 18)) {
    const work = WORKPLACE[agentId];
    return work ? { kind: "building", id: work } : { kind: "anchor" };
  }
  return { kind: "anchor" };
}

interface Npc {
  def: AgentDef;
  sprite: Phaser.Physics.Arcade.Sprite;
  label: Phaser.GameObjects.Text;
  emote: Phaser.GameObjects.Sprite;
  shadow: Phaser.GameObjects.Ellipse;
  state: "idle" | "walk" | "talk" | "path" | "inside";
  target: Phaser.Math.Vector2 | null;
  nextThink: number;
  path: { x: number; y: number }[] | null;
  pathIdx: number;
  insideBuilding: string | null;
  duty: Duty["kind"] | "";
  lastPX: number;
  lastPY: number;
  stuckMs: number;
}

interface Crop {
  cell: number;
  title: string;
  progress: number; // 1..4
  variety: number;
  taskId?: string;
  sprite?: Phaser.GameObjects.Image;
}

export class TownScene extends Phaser.Scene {
  private layout!: TownLayout;
  private collide!: boolean[][];
  private player!: Phaser.Physics.Arcade.Sprite;
  private cursors!: Phaser.Types.Input.Keyboard.CursorKeys;
  private wasd!: Record<"W" | "A" | "S" | "D" | "E" | "F", Phaser.Input.Keyboard.Key>;
  private npcs: Npc[] = [];
  private waterTiles: Phaser.Tilemaps.Tile[] = [];
  private waterFrame = 0;
  private nightOverlay!: Phaser.GameObjects.Rectangle;
  private lampGlows: Phaser.GameObjects.Arc[] = [];
  private clockMin = 8 * 60;
  private day = 1;
  private harvested = 0;
  private moveTarget: Phaser.Math.Vector2 | null = null;
  private playerPath: { x: number; y: number }[] | null = null;
  private playerPathIdx = 0;
  private following = true;
  private dragging = false;
  private dragStart = new Phaser.Math.Vector2();
  private camStart = new Phaser.Math.Vector2();
  private uiLock = false;
  private doorZones: { id: string; rect: Phaser.Geom.Rectangle }[] = [];
  private hintText!: Phaser.GameObjects.Text;
  private crops = new Map<number, Crop>();
  private demoCrops: DemoCrop[] = [];
  private actionCooldown = 0;
  private playerShadow!: Phaser.GameObjects.Ellipse;
  // ---- v5 state
  private ores: string[] = [];
  private fishCaught: string[] = [];
  private ach: Record<string, boolean> = {};
  private points = 0;
  private fishPool: { text: string; level: string; rarity: number }[] | null = null;
  private treeImgs: Phaser.GameObjects.Image[] = [];
  private grassLayer!: Phaser.Tilemaps.TilemapLayer;
  private pathLayer!: Phaser.Tilemaps.TilemapLayer;
  private currentSeason = "";
  private snow: Phaser.GameObjects.Particles.ParticleEmitter | null = null;
  private festivalToday = false;
  private festivalDecor: Phaser.GameObjects.GameObject[] = [];
  private lastFirework = 0;
  private mineZone!: Phaser.Geom.Rectangle;
  // ---- v6 state
  private touchInteract = false; // armed by the touch E button, consumed per frame
  private seenSignals = new Set<string>();
  private signalsPrimed = false; // first batch is history — observe, don't react
  private demoSignalTick = 0;
  // ---- v8 state
  private inventory: InvItem[] = [];
  private pendingShip: InvItem[] = [];
  private canLevel: 1 | 2 = 1;
  private museum: { ores: string[]; fish: string[] } = { ores: [], fish: [] };
  private decor: { id: string; tx: number; ty: number }[] = [];
  private decorSprites: Phaser.GameObjects.Image[] = [];
  private binTile: [number, number] = [4, 36];
  // ---- v7 state
  private weather: "sunny" | "rain" | "fog" = "sunny";
  private weatherDay = 0; // which day the current weather was rolled for
  private rain: Phaser.GameObjects.Particles.ParticleEmitter | null = null;
  private fogOverlay: Phaser.GameObjects.Rectangle | null = null;
  private lastMemoryCount = -1;
  private lastCommits = new Map<string, string>();
  private pulsePrimed = false;
  private chitchatAt = new Map<string, number>(); // pair key -> next allowed time
  private nextChitchatScan = 0;
  private bubbles: Phaser.GameObjects.Text[] = [];
  // ---- v9 state
  private tutorialStep = 1; // 1..5, 99 = done
  // ---- v10 state
  private hearts: Record<string, number> = {};
  private heartsDay: Record<string, number> = {};

  constructor() {
    super("town");
  }

  create(): void {
    this.layout = generateTown();
    this.collide = this.layout.collide.map((r) => [...r]);

    const save = loadSave();
    if (save) {
      this.day = save.day;
      this.clockMin = save.clockMin;
      this.harvested = save.harvested;
      this.demoCrops = save.demoCrops ?? [];
      this.ores = save.ores ?? [];
      this.fishCaught = save.fish ?? [];
      this.ach = save.ach ?? {};
      this.points = save.points ?? 0;
      this.inventory = save.inventory ?? [];
      this.pendingShip = save.pendingShip ?? [];
      this.canLevel = save.canLevel ?? 1;
      this.museum = save.museum ?? { ores: [], fish: [] };
      this.decor = save.decor ?? [];
      this.tutorialStep = save.tutorialStep ?? 1;
      this.hearts = save.hearts ?? {};
      this.heartsDay = save.heartsDay ?? {};
    }

    this.buildGround();
    this.buildDecor();
    this.buildPlaza();
    this.buildBuildings();
    this.buildMine();
    this.buildShippingBin();
    for (const d of this.decor) this.spawnDecor(d.id, d.tx, d.ty);
    this.buildPlayer(save?.px, save?.py);
    this.buildNpcs();
    this.buildAnimals();
    this.buildLighting();
    this.bindInput();
    this.bindBus();
    void this.initFarm();
    void this.initFestival();

    this.cameras.main.fadeIn(750, 26, 20, 35);
    this.cameras.main.setBounds(0, 0, MAP_W * TILE, MAP_H * TILE);
    this.cameras.main.setZoom(3);
    this.cameras.main.startFollow(this.player, true, 0.12, 0.12);

    this.time.addEvent({ delay: 260, loop: true, callback: () => this.cycleWater() });
    this.time.addEvent({ delay: 1000, loop: true, callback: () => this.tickClock() });
    this.time.addEvent({ delay: 60000, loop: true, callback: () => this.autosave() });
    // v6: multi-agent signals — live polls the bridge, demo replays samples
    this.time.addEvent({ delay: 30000, loop: true, callback: () => void this.pollSignals() });
    void this.pollSignals();
    // v7: the town heartbeat (memory count + git commits) and weather
    this.time.addEvent({ delay: 45000, loop: true, callback: () => void this.pollPulse() });
    void this.pollPulse();
    this.rollWeather();
    // v9: surface the onboarding quest once the UI has mounted
    this.time.delayedCall(1600, () => this.emitTutorial());

    // audio loads in the background AFTER the world is playable — a stalled
    // or missing sound file must never block entering the town
    for (const a of AUDIO_FILES) this.load.audio(a.key, a.url);
    this.load.once(Phaser.Loader.Events.COMPLETE, () => audio.startBgm());
    this.load.start();

    this.events.on(Phaser.Scenes.Events.WAKE, (_sys: unknown, data?: { returnTx: number; returnTy: number }) => {
      this.uiLock = false;
      if (data) {
        this.player.setPosition(data.returnTx * TILE + 8, (data.returnTy + 1) * TILE - 4);
        this.player.setDepth(this.player.y);
      }
      this.cameras.main.fadeIn(300, 26, 20, 35);
      this.autosave();
    });

    (window as unknown as Record<string, unknown>).__town = this;
  }

  /** dev helper: jump camera to a tile (used by preview tooling) */
  lookAt(tx: number, ty: number, zoom = 3): void {
    this.following = false;
    this.cameras.main.stopFollow();
    this.cameras.main.setZoom(zoom);
    this.cameras.main.centerOn(tx * TILE, ty * TILE);
  }

  // ------------------------------------------------------------------ ground
  private buildGround(): void {
    const map = this.make.tilemap({ tileWidth: TILE, tileHeight: TILE, width: MAP_W, height: MAP_H });
    const tsWater = map.addTilesetImage("water", "ts-water", TILE, TILE, 0, 0)!;
    const tsGrass = map.addTilesetImage("grass", "ts-grass", TILE, TILE, 0, 0)!;
    const tsDirt = map.addTilesetImage("dirt", "ts-dirt", TILE, TILE, 0, 0)!;

    const water = map.createBlankLayer("water", tsWater)!;
    const grass = map.createBlankLayer("grass", tsGrass)!;
    const path = map.createBlankLayer("path", tsDirt)!;
    water.setDepth(0);
    grass.setDepth(1);
    path.setDepth(2);
    this.grassLayer = grass;
    this.pathLayer = path;

    for (let y = 0; y < MAP_H; y++) {
      for (let x = 0; x < MAP_W; x++) {
        const t = water.putTileAt(tsWater.firstgid, x, y);
        if (this.layout.isWater[y][x]) this.waterTiles.push(t);
        const g = this.layout.grass[y][x];
        if (g != null) grass.putTileAt(tsGrass.firstgid + g, x, y);
        const p = this.layout.path[y][x];
        if (p != null) path.putTileAt(tsDirt.firstgid + p, x, y);
      }
    }
    for (const c of this.layout.farmSoil) {
      path.putTileAt(tsDirt.firstgid + [0, 1, 2][(c.tx + c.ty) % 3], c.tx, c.ty);
    }
  }

  private cycleWater(): void {
    this.waterFrame = (this.waterFrame + 1) % WATER_FRAMES;
    for (const t of this.waterTiles) t.index = t.tileset!.firstgid + this.waterFrame;
  }

  // ------------------------------------------------------------------- decor
  private buildDecor(): void {
    for (const b of this.layout.bushes) {
      this.add.image(b.tx * TILE + 8, b.ty * TILE + 8, "decor-biom", b.frame).setDepth(b.ty * TILE + 8);
    }
    for (const f of this.layout.fences) {
      this.add.image(f.tx * TILE + 8, f.ty * TILE + 8, "ts-fences", f.frame).setDepth(f.ty * TILE + 4);
    }
    for (const t of this.layout.trees) {
      const img = t.small
        ? this.add.image(t.tx * TILE + 8, (t.ty + 1) * TILE, "decor-oak-small", 1)
        : this.add.image(t.tx * TILE + 8, (t.ty + 1) * TILE, "decor-oak");
      img.setOrigin(0.5, 1).setDepth((t.ty + 1) * TILE);
      this.treeImgs.push(img);
    }
  }

  // -------------------------------------------------------------------- mine
  /** entrance to the tech-debt mines, set into the western meadow */
  private buildMine(): void {
    const tx = 4;
    const ty = 27; // bottom row of the arch
    this.add.image(tx * TILE + 16, (ty + 1) * TILE, "prop-mine-entrance")
      .setOrigin(0.5, 1).setDepth((ty + 1) * TILE - 2);
    for (let y = ty - 1; y <= ty; y++) {
      for (let x = tx; x <= tx + 1; x++) this.collide[y][x] = true;
    }
    // doorway tile stays walkable just below the arch
    this.mineZone = new Phaser.Geom.Rectangle((tx - 1) * TILE, ty * TILE, TILE * 4, TILE * 2.4);
    this.add
      .text(tx * TILE + 16, (ty - 2) * TILE, "技术债矿洞", {
        fontFamily: "'Microsoft YaHei', sans-serif",
        fontSize: "8px", color: "#e6dcff", stroke: "#241a2e", strokeThickness: 3, resolution: 4,
      })
      .setOrigin(0.5, 1).setDepth(10000);
  }

  private enterMine(): void {
    if (this.uiLock) return;
    this.uiLock = true;
    audio.door();
    this.autosave();
    this.cameras.main.fadeOut(260, 8, 6, 12);
    this.cameras.main.once(Phaser.Cameras.Scene2D.Events.FADE_OUT_COMPLETE, () => {
      this.scene.run("mine", { level: 1, returnTx: 5, returnTy: 28 });
      this.scene.sleep();
    });
  }

  // ------------------------------------------------------------------- plaza
  private buildPlaza(): void {
    const img = (tx: number, ty: number, key: string, frame?: number, solid = true) => {
      const o = frame === undefined
        ? this.add.image(tx * TILE + 8, (ty + 1) * TILE, key)
        : this.add.image(tx * TILE + 8, (ty + 1) * TILE, key, frame);
      o.setOrigin(0.5, 1).setDepth((ty + 1) * TILE);
      if (solid) this.collide[ty][tx] = true;
      return o;
    };

    img(29, 18, "decor-sign");
    for (const [lx, ly] of [[27, 17], [37, 17], [27, 21], [37, 21]] as const) {
      img(lx, ly, "decor-lamp");
      const glow = this.add.circle(lx * TILE + 8, ly * TILE - 24, 14, 0xffc966, 0)
        .setDepth(15000).setBlendMode(Phaser.BlendModes.ADD);
      this.lampGlows.push(glow);
    }
    const tulips = [56, 57, 58, 59, 63, 64];
    const beds: [number, number][] = [
      [28, 17], [29, 17], [35, 17], [36, 17],
      [28, 21], [29, 21], [35, 21], [36, 21],
      [30, 16], [34, 16],
    ];
    beds.forEach(([fx, fy], i) => {
      this.add.image(fx * TILE + 8, fy * TILE + 12, "decor-outdoor", tulips[i % tulips.length])
        .setOrigin(0.5, 1).setDepth(fy * TILE + 12);
    });
    img(33, 21, "decor-outdoor", 49);
    img(34, 21, "decor-outdoor", 50);
    img(36, 19, "decor-oak-small", 1);
  }

  // --------------------------------------------------------------- buildings
  private buildBuildings(): void {
    for (const b of BUILDINGS) {
      const px = b.tx * TILE + TILE / 2;
      const py = (b.ty + 1) * TILE;
      const img = this.add.image(px, py, b.texture).setOrigin(0.5, 1).setDepth(py - 2);

      const wTiles = Math.ceil(img.width / TILE);
      const hTiles = Math.ceil(img.height / TILE);
      const x0 = b.tx - Math.floor(wTiles / 2);
      for (let dy = 1; dy < Math.min(hTiles, 5); dy++) {
        const y = b.ty - dy + 1;
        if (y < 0) continue;
        for (let x = x0; x < x0 + wTiles; x++) {
          if (x < 0 || x >= MAP_W) continue;
          if (dy === 1 && x === b.tx) continue; // doorway
          this.collide[y][x] = true;
        }
      }
      this.doorZones.push({
        id: b.id,
        rect: new Phaser.Geom.Rectangle((b.tx - 1) * TILE, (b.ty - 1) * TILE, TILE * 3, TILE * 2.2),
      });

      this.add
        .text(px, py - img.height - 4, b.nameZh, {
          fontFamily: "'Microsoft YaHei', sans-serif",
          fontSize: "8px", color: "#fff7e6", stroke: "#5a3b28", strokeThickness: 3, resolution: 4,
        })
        .setOrigin(0.5, 1).setDepth(10000);
    }
  }

  // ------------------------------------------------------------------ player
  private buildPlayer(px?: number, py?: number): void {
    let x = PLAZA.tx * TILE + 8;
    let y = PLAZA.ty * TILE + 8;
    if (px !== undefined && py !== undefined && !this.isBlocked(px, py + 12)) {
      x = px;
      y = py;
    }
    this.playerShadow = this.makeShadow(x, y);
    this.player = this.physics.add.sprite(x, y, "char-player", 0);
    this.player.body!.setSize(12, 10);
    (this.player.body as Phaser.Physics.Arcade.Body).setOffset(18, 30);
    this.player.setDepth(this.player.y);
  }

  /** soft contact shadow — grounds every character on the map */
  private makeShadow(x: number, y: number): Phaser.GameObjects.Ellipse {
    return this.add.ellipse(x, y + 12, 16, 6, 0x2a2018, 0.26).setDepth(3);
  }

  // -------------------------------------------------------------------- npcs
  private buildNpcs(): void {
    for (const def of AGENTS) {
      const sprite = this.physics.add.sprite(def.tx * TILE + 8, def.ty * TILE + 8, def.texture, 0);
      sprite.body!.setSize(12, 10);
      (sprite.body as Phaser.Physics.Arcade.Body).setOffset(18, 30);
      sprite.setInteractive({ useHandCursor: true });
      const label = this.add
        .text(sprite.x, sprite.y - 26, def.nameZh, {
          fontFamily: "'Microsoft YaHei', sans-serif",
          fontSize: "7px", color: "#ffffff", stroke: "#3d2b1f", strokeThickness: 3, resolution: 4,
        })
        .setOrigin(0.5, 1).setDepth(10000).setAlpha(0.92);
      const emote = this.add.sprite(sprite.x, sprite.y - 34, "ui-emotes", 0).setVisible(false).setDepth(10001);
      const shadow = this.makeShadow(sprite.x, sprite.y);
      this.npcs.push({
        def, sprite, label, emote, shadow,
        state: "idle", target: null, nextThink: 0,
        path: null, pathIdx: 0, insideBuilding: null, duty: "",
        lastPX: sprite.x, lastPY: sprite.y, stuckMs: 0,
      });
      sprite.on("pointerdown", (p: Phaser.Input.Pointer) => {
        if (p.getDistance() < 6) this.tryTalk(def.id);
      });
    }
  }

  /** residents currently working inside a given building */
  residentsInside(buildingId: string): string[] {
    return this.npcs.filter((n) => n.state === "inside" && n.insideBuilding === buildingId).map((n) => n.def.id);
  }

  private buildAnimals(): void {
    const cow = this.physics.add.sprite((FARM.x + 2) * TILE, (FARM.y - 3) * TILE, "anim-cow", 0);
    cow.play("cow-idle").setDepth(cow.y);
    this.add.ellipse(cow.x, cow.y + 14, 24, 8, 0x2a2018, 0.24).setDepth(3);
    for (let i = 0; i < 3; i++) {
      const ch = this.physics.add.sprite((FARM.x + 5 + i * 2) * TILE, (FARM.y - 2.2) * TILE, "anim-chicken", 0);
      ch.play({ key: "chicken-peck", delay: i * 350 }).setDepth(ch.y);
      this.add.ellipse(ch.x, ch.y + 7, 11, 4, 0x2a2018, 0.24).setDepth(3);
    }
  }

  // ---------------------------------------------------------------- lighting
  private buildLighting(): void {
    const cam = this.cameras.main;
    this.nightOverlay = this.add
      .rectangle(0, 0, cam.width, cam.height, 0x0b1030, 0)
      .setOrigin(0).setScrollFactor(0).setDepth(20000);
    this.hintText = this.add
      .text(cam.width / 2, cam.height - 8, "", {
        fontFamily: "'Microsoft YaHei', sans-serif",
        fontSize: "12px", color: "#fff7e6", stroke: "#5a3b28", strokeThickness: 4, resolution: 3,
      })
      .setOrigin(0.5, 1).setScrollFactor(0).setDepth(20001);
  }

  private tickClock(): void {
    this.clockMin += MINUTES_PER_SECOND;
    if (this.clockMin >= DAY_MINUTES) {
      this.clockMin -= DAY_MINUTES;
      this.day += 1;
      this.settleShipping();
      restoreStamina(100);
    }
    if (this.day !== this.weatherDay) this.rollWeather(); // new morning, new sky
    const hour = Math.floor(this.clockMin / 60);
    const minute = Math.floor(this.clockMin % 60);
    const season = ["春", "夏", "秋", "冬"][Math.floor(((this.day - 1) % 28) / 7)];
    bus.emit("clock:tick", { day: this.day, hour, minute, season, weather: this.weather });
    if (season !== this.currentSeason) this.applySeason(season);
    this.fireworksTick();
    this.checkAchievements();

    const h = this.clockMin / 60;
    let a = 0;
    if (h >= 18 && h < 20) a = ((h - 18) / 2) * 0.55;
    else if (h >= 20 || h < 5) a = 0.55;
    else if (h >= 5 && h < 7) a = (1 - (h - 5) / 2) * 0.55;
    this.nightOverlay.fillAlpha = a;
    const lampOn = a > 0.18;
    for (const g of this.lampGlows) {
      g.setAlpha(lampOn ? 0.16 + (Math.sin(this.time.now / 600) + 1) * 0.07 : 0);
    }
  }

  // ------------------------------------------------------------------- input
  private bindInput(): void {
    this.cursors = this.input.keyboard!.createCursorKeys();
    this.wasd = this.input.keyboard!.addKeys("W,A,S,D,E,F") as TownScene["wasd"];

    this.input.on("wheel", (_p: unknown, _o: unknown, _dx: number, dy: number) => {
      const cam = this.cameras.main;
      const z = Phaser.Math.Clamp(cam.zoom - Math.sign(dy) * 0.25, 1.5, 5);
      cam.setZoom(z);
    });

    this.input.on("pointerdown", (p: Phaser.Input.Pointer) => {
      this.dragging = false;
      this.dragStart.set(p.x, p.y);
      this.camStart.set(this.cameras.main.scrollX, this.cameras.main.scrollY);
    });
    this.input.on("pointermove", (p: Phaser.Input.Pointer) => {
      if (!p.isDown) return;
      const dist = Phaser.Math.Distance.Between(p.x, p.y, this.dragStart.x, this.dragStart.y);
      if (dist > 8) {
        this.dragging = true;
        this.following = false;
        this.cameras.main.stopFollow();
        const cam = this.cameras.main;
        cam.setScroll(
          this.camStart.x - (p.x - this.dragStart.x) / cam.zoom,
          this.camStart.y - (p.y - this.dragStart.y) / cam.zoom,
        );
      }
    });
    this.input.on("pointerup", (p: Phaser.Input.Pointer) => {
      if (this.dragging || this.uiLock) return;
      const world = this.cameras.main.getWorldPoint(p.x, p.y);
      for (const z of this.doorZones) {
        if (z.rect.contains(world.x, world.y)) {
          this.enterBuilding(z.id);
          return;
        }
      }
      if (this.mineZone.contains(world.x, world.y) && this.mineZone.contains(this.player.x, this.player.y)) {
        this.enterMine();
        return;
      }
      this.setMoveTo(world.x, world.y);
    });
  }

  private bindBus(): void {
    bus.on("dialogue:closed", () => {
      this.uiLock = false;
      for (const n of this.npcs) if (n.state === "talk") n.state = "idle";
    });
    bus.on("panel:closed", () => {
      this.uiLock = false;
    });
    bus.on("sleep:request", () => {
      this.day += 1;
      this.clockMin = 8 * 60;
      this.settleShipping();
      restoreStamina(100);
      this.autosave();
      bus.emit("sleep:done", { day: this.day });
      bus.emit("toast", { text: `第 ${this.day} 天的清晨。体力满格，存档完成。` });
    });
    bus.on("farm:plant-confirm", ({ cell, title }) => {
      void this.plantCrop(cell, title);
    });
    bus.on("ore:collected", ({ title, kind, repo }) => {
      this.ores.push(`[${kind}] ${repo}: ${title}`);
      this.inventory.push({ kind: "ore", name: `[${kind}] ${title}`.slice(0, 60) });
      this.tutorialHook("ore");
      this.points += kind === "fixme" ? 3 : kind === "hotspot" ? 2 : 1;
      bus.emit("toast", { text: `⛏ 采得债务矿石：${title.slice(0, 36)}（建设点 +${kind === "fixme" ? 3 : kind === "hotspot" ? 2 : 1}）` });
      this.checkAchievements();
      this.autosave();
    });
    bus.on("fishing:result", ({ quality }) => {
      void this.resolveCatch(quality);
    });
    bus.on("touch:interact", () => {
      if (this.scene.isActive()) this.touchInteract = true;
    });
    bus.on("quest:take", ({ agentId }) => {
      void this.takeQuest(agentId);
    });
    bus.on("ship:add", ({ index }) => {
      const item = this.inventory[index];
      if (!item) return;
      this.inventory.splice(index, 1);
      this.pendingShip.push(item);
      this.autosave();
    });
    bus.on("ship:all", () => {
      if (this.inventory.length === 0) return;
      this.pendingShip.push(...this.inventory);
      this.inventory = [];
      this.autosave();
      bus.emit("toast", { text: "📦 全部投入出货箱——清晨结算成建设点" });
    });
    bus.on("shop:buy", ({ itemId }) => this.buyShopItem(itemId));
    bus.on("museum:donate", ({ kind, index }) => this.donate(kind, index));
    bus.on("settings:zoom", ({ zoom }) => {
      this.cameras.main.setZoom(Math.max(2, Math.min(4, zoom)));
    });
    bus.on("tutorial:skip", () => {
      if (this.tutorialStep >= 99) return;
      this.tutorialStep = 99;
      bus.emit("tutorial:step", { step: 99, total: 5, textZh: "", textEn: "" });
      this.autosave();
    });
  }

  // -------------------------------------------------------------- v10 hearts
  /** Friendship: first chat each day +1, quests +1, quest harvests +2.
   * Exposed for the harness. */
  bumpHearts(agentId: string, kind: "talk" | "quest" | "harvest"): void {
    if (!AGENTS.some((a) => a.id === agentId)) return;
    if (kind === "talk") {
      if (this.heartsDay[agentId] === this.day) return; // one credit per day
      this.heartsDay[agentId] = this.day;
    }
    const gain = kind === "harvest" ? 2 : 1;
    const before = this.hearts[agentId] ?? 0;
    const after = Math.min(10, before + gain);
    if (after === before) return;
    this.hearts[agentId] = after;
    const name = AGENTS.find((a) => a.id === agentId)?.nameZh ?? agentId;
    if (after >= 3 && before < 3) bus.emit("toast", { text: `♥ 你和${name}成了朋友（好感 ${after}/10）` });
    else if (after >= 7 && before < 7) bus.emit("toast", { text: `♥♥ ${name}已把你当作挚友（好感 ${after}/10）` });
    else if (after >= 10 && before < 10) bus.emit("toast", { text: `💖 你和${name}的友谊满格了！` });
    if (after >= 5) this.grantAch("heart5", "镇上有了好朋友（好感 ≥5）");
    this.autosave();
  }

  // ------------------------------------------------------------ v9 tutorial
  private static readonly TUTORIAL_STEPS: Record<number, [string, string]> = {
    1: ["去广场公告板旁找狐狸 Fable 聊聊", "Find Fable the fox by the notice board"],
    2: ["在农场种下一株任务（走近田垄按 E）", "Plant a task at the farm (press E)"],
    3: ["走进记忆图书馆逛逛", "Step inside the Memory Library"],
    4: ["去农场南侧的矿洞敲一块矿石", "Crack an ore node in the mines"],
    5: ["回去找 Fable 领开镇礼包", "Return to Fable for your welcome gift"],
  };

  private emitTutorial(): void {
    if (this.tutorialStep >= 99) return;
    const s = TownScene.TUTORIAL_STEPS[this.tutorialStep];
    if (s) bus.emit("tutorial:step", { step: this.tutorialStep, total: 5, textZh: s[0], textEn: s[1] });
  }

  /** Onboarding advances on real play events; exposed for the harness. */
  tutorialHook(evt: string): void {
    const need: Record<number, string> = { 1: "talk-fable", 2: "plant", 3: "library", 4: "ore", 5: "talk-fable" };
    if (this.tutorialStep >= 99 || need[this.tutorialStep] !== evt) return;
    if (this.tutorialStep >= 5) {
      this.tutorialStep = 99;
      this.points += 10;
      bus.emit("tutorial:step", { step: 99, total: 5, textZh: "", textEn: "" });
      bus.emit("toast", { text: "🎁 开镇礼包：建设点 +10！山谷由你掌舵了" });
      this.grantAch("tutorial1", "新镇长上任（完成引导）");
    } else {
      this.tutorialStep += 1;
      this.emitTutorial();
    }
    this.autosave();
  }

  // ------------------------------------------------------------- v6 signals
  /** Poll multi-agent signals. LIVE reads the bridge (agentmemory relay);
   * DEMO replays one sample per tick so visitors still see the town react. */
  private async pollSignals(): Promise<void> {
    try {
      const d = await getData<{ signals: TownSignal[] }>("/api/town/signals", "signals.json");
      let sigs = d.signals ?? [];
      if (currentMode() !== "live") {
        if (!this.signalsPrimed) {
          this.signalsPrimed = true; // demo has no history to swallow
          return;
        }
        if (sigs.length === 0) return;
        const pick = sigs[this.demoSignalTick % sigs.length];
        this.demoSignalTick += 1;
        sigs = [{ ...pick, id: `${pick.id}-replay-${this.demoSignalTick}` }];
      }
      this.onSignals(sigs);
    } catch {
      /* bridge offline — town just stays quiet */
    }
  }

  /** Ingest a batch of signals; exposed for the e2e harness. */
  onSignals(sigs: TownSignal[]): void {
    for (const s of sigs) {
      if (!s.id || this.seenSignals.has(s.id)) continue;
      this.seenSignals.add(s.id);
      if (this.signalsPrimed) this.reactToSignal(s);
    }
    this.signalsPrimed = true;
  }

  /** The receiver dashes to the plaza notice board and waves. */
  private reactToSignal(s: TownSignal): void {
    const n =
      this.npcs.find((x) => x.def.id === s.to) ??
      this.npcs.find((x) => x.def.id === "fable") ??
      this.npcs[0];
    bus.emit("signal:received", { from: s.from, to: s.to, summary: s.summary });
    bus.emit("toast", { text: `📨 信号 ${s.from} → ${s.to === "all" ? "全镇" : s.to}：${s.summary.slice(0, 48)}` });
    if (!n || n.state === "inside" || n.state === "talk") return;
    const np = findPath(
      this.collide,
      Math.floor(n.sprite.x / TILE), Math.floor(n.sprite.y / TILE),
      29, 20, // just below the plaza notice board
    );
    if (np && np.length > 0) {
      n.path = np;
      n.pathIdx = 0;
      n.state = "path";
      (n as Npc & { after?: unknown }).after = undefined;
      n.emote.setVisible(true);
      n.emote.play("emote-alert");
    }
  }

  // -------------------------------------------------------------- v7 pulse
  private ensureDotTexture(): void {
    if (this.textures.exists("snowdot")) return;
    const g = this.make.graphics({ x: 0, y: 0 }, false);
    g.fillStyle(0xffffff, 1);
    g.fillRect(0, 0, 2, 2);
    g.generateTexture("snowdot", 2, 2);
    g.destroy();
  }

  private async pollPulse(): Promise<void> {
    try {
      const d = await getData<{ memoryCount: number; commits: { repo: string; hash: string; msg: string }[] }>(
        "/api/town/pulse", "pulse.json",
      );
      this.onPulse(d);
    } catch {
      /* bridge offline — no heartbeat this round */
    }
  }

  /** Ingest a heartbeat; first call only records the baseline. */
  onPulse(d: { memoryCount: number; commits: { repo: string; hash: string; msg: string }[] }): void {
    const primed = this.pulsePrimed;
    this.pulsePrimed = true;
    if (typeof d.memoryCount === "number" && d.memoryCount >= 0) {
      if (primed && this.lastMemoryCount >= 0 && d.memoryCount > this.lastMemoryCount) {
        this.reactMemoryGrowth(d.memoryCount - this.lastMemoryCount);
      }
      this.lastMemoryCount = d.memoryCount;
    }
    for (const c of d.commits ?? []) {
      const prev = this.lastCommits.get(c.repo);
      if (primed && prev && prev !== c.hash) this.reactCommit(c.repo, c.msg);
      this.lastCommits.set(c.repo, c.hash);
    }
  }

  /** new memories shelved -> the library chimney puffs and Sonnet beams */
  private reactMemoryGrowth(n: number): void {
    const lib = BUILDINGS.find((b) => b.id === "memory-library");
    if (lib) this.puffSmoke((lib.tx + 1.3) * TILE, (lib.ty + 0.5) * TILE);
    const sonnet = this.npcs.find((x) => x.def.id === "sonnet");
    if (sonnet && sonnet.sprite.visible) {
      sonnet.emote.setVisible(true);
      sonnet.emote.play("emote-alert");
    }
    bus.emit("toast", { text: `📚 图书馆上架了 ${n} 本新记忆，烟囱冒烟啦` });
  }

  /** a fresh commit -> confetti over the code workshop */
  private reactCommit(repo: string, msg: string): void {
    const shop = BUILDINGS.find((b) => b.id === "code-workshop");
    if (shop) this.burstConfetti((shop.tx + 2) * TILE, (shop.ty + 0.6) * TILE);
    bus.emit("toast", { text: `🔨 ${repo} 收成新提交：${msg.slice(0, 40)}` });
  }

  private puffSmoke(x: number, y: number): void {
    this.ensureDotTexture();
    const e = this.add.particles(x, y, "snowdot", {
      speedY: { min: -18, max: -9 }, speedX: { min: -4, max: 4 },
      scale: { start: 1.6, end: 3.4 }, alpha: { start: 0.5, end: 0 },
      tint: 0xbdb6ae, lifespan: 2600, frequency: 140, quantity: 1,
    }).setDepth(19000);
    this.time.delayedCall(9000, () => e.destroy());
  }

  private burstConfetti(x: number, y: number): void {
    this.ensureDotTexture();
    const e = this.add.particles(x, y, "snowdot", {
      speed: { min: 26, max: 80 }, angle: { min: 200, max: 340 },
      gravityY: 70, scale: { start: 1.5, end: 0.4 },
      tint: [0xff8a8a, 0xffd27a, 0x9be564, 0x9fd6ff, 0xc99bff],
      lifespan: 1500, emitting: false,
    }).setDepth(19000);
    e.explode(30, 0, 0);
    this.time.delayedCall(1800, () => e.destroy());
  }

  // ------------------------------------------------------------ v7 weather
  /** roll the day's weather — deterministic per day so reloads agree */
  private rollWeather(): void {
    this.weatherDay = this.day;
    const season = ["春", "夏", "秋", "冬"][Math.floor(((this.day - 1) % 28) / 7)];
    const r = (Math.sin(this.day * 127.1) * 43758.5453) % 1;
    const roll = Math.abs(r);
    const rainChance = season === "夏" ? 0.32 : season === "春" ? 0.25 : 0.16;
    const fogChance = season === "秋" ? 0.22 : season === "冬" ? 0.18 : 0.07;
    this.setWeather(roll < rainChance ? "rain" : roll < rainChance + fogChance ? "fog" : "sunny");
  }

  /** apply weather visuals; rainy mornings water every crop once */
  setWeather(w: "sunny" | "rain" | "fog"): void {
    this.weather = w;
    this.rain?.destroy();
    this.rain = null;
    this.fogOverlay?.destroy();
    this.fogOverlay = null;
    const cam = this.cameras.main;
    if (w === "rain") {
      this.ensureDotTexture();
      this.rain = this.add.particles(0, 0, "snowdot", {
        x: { min: 0, max: cam.width }, y: -8,
        speedY: { min: 210, max: 280 }, speedX: { min: -32, max: -16 },
        scale: { start: 1.1, end: 0.7 }, alpha: { start: 0.5, end: 0.12 },
        tint: 0x9fc8ef, lifespan: 2400, frequency: 9, quantity: 2,
      }).setScrollFactor(0).setDepth(19500);
      void this.rainWaterCrops();
    } else if (w === "fog") {
      this.fogOverlay = this.add.rectangle(0, 0, cam.width, cam.height, 0xcfd8dd, 0.16)
        .setOrigin(0).setScrollFactor(0).setDepth(19400);
    }
  }

  private async rainWaterCrops(): Promise<void> {
    let watered = 0;
    for (const c of [...this.crops.values()]) {
      if (c.progress >= 1 && c.progress < 4) {
        await this.waterCrop(c, true);
        watered += 1;
      }
    }
    if (watered > 0) bus.emit("toast", { text: `🌧 雨水替你浇了 ${watered} 株作物` });
  }

  // ----------------------------------------------------------- v7 chitchat
  private static readonly CHITCHAT: Record<string, string[]> = {
    opus: ["市政厅的报表又厚了三页。", "今晚的月色适合写规划。"],
    codex: ["刚合了一个 PR，神清气爽。", "测试全绿的感觉真好。"],
    sonnet: ["新书今天就上架。", "记忆要常整理才不积灰。"],
    haiku: ["风从河面来。", "今天的云走得很快。"],
    deepseek: ["我在想一个很深的问题。", "推理到第七层了。"],
    aris: ["实验数据有了新眉目。", "看板上又多了一张卡。"],
    pixelcat: ["像素要一颗一颗地点。", "喵——配色灵感来了！"],
    fable: ["这故事值得写进镇志。", "听说矿洞里有新矿石？"],
  };

  /** every few seconds, let one nearby pair stop for a two-line exchange */
  private maybeChitchat(time: number): void {
    if (time < this.nextChitchatScan) return;
    this.nextChitchatScan = time + 5000;
    const out = this.npcs.filter((n) => (n.state === "idle" || n.state === "walk") && n.sprite.visible);
    for (let i = 0; i < out.length; i++) {
      for (let j = i + 1; j < out.length; j++) {
        const a = out[i];
        const b = out[j];
        if (Phaser.Math.Distance.Between(a.sprite.x, a.sprite.y, b.sprite.x, b.sprite.y) > TILE * 2.2) continue;
        const key = [a.def.id, b.def.id].sort().join("|");
        if (time < (this.chitchatAt.get(key) ?? 0)) continue;
        this.chitchatAt.set(key, time + 90000);
        this.chitchat(a, b);
        return; // one pair per scan keeps the plaza cozy
      }
    }
  }

  /** a small two-line exchange; exposed for the harness */
  chitchat(a: Npc, b: Npc): void {
    a.state = "talk";
    b.state = "talk";
    a.target = null;
    b.target = null;
    const lineOf = (id: string, alt: number) => {
      const pool = TownScene.CHITCHAT[id] ?? ["今天也辛苦啦。"];
      return pool[(this.day + alt) % pool.length];
    };
    this.bubble(a, lineOf(a.def.id, 0), 0);
    this.bubble(b, lineOf(b.def.id, 1), 2300);
    this.time.delayedCall(4800, () => {
      if (a.state === "talk") a.state = "idle";
      if (b.state === "talk") b.state = "idle";
    });
  }

  private bubble(n: Npc, text: string, delay: number): void {
    this.time.delayedCall(delay, () => {
      if (!n.sprite.visible) return;
      const t = this.add.text(n.sprite.x, n.sprite.y - 30, text, {
        fontFamily: "'Microsoft YaHei', sans-serif", fontSize: "9px",
        color: "#3b2a18", backgroundColor: "#f7eeddee",
        padding: { x: 4, y: 2 }, resolution: 3,
      }).setOrigin(0.5, 1).setDepth(19600);
      this.bubbles.push(t);
      this.tweens.add({ targets: t, y: t.y - 6, duration: 2100 });
      this.time.delayedCall(2250, () => t.destroy());
    });
  }

  // ------------------------------------------------------------ v8 economy
  private buildShippingBin(): void {
    const [tx, ty] = this.binTile;
    this.add.image(tx * TILE + 8, (ty + 1) * TILE, "prop-shipping-bin")
      .setOrigin(0.5, 1).setDepth((ty + 1) * TILE);
    this.collide[ty][tx] = true;
  }

  /** morning payout: bin contents become build points */
  settleShipping(): void {
    if (this.pendingShip.length === 0) return;
    const value = (i: InvItem) => (i.kind === "ore" ? 3 : 2);
    const sum = this.pendingShip.reduce((a, i) => a + value(i), 0);
    this.points += sum;
    bus.emit("toast", { text: `📦 清晨结算：${this.pendingShip.length} 件货品 → 建设点 +${sum}（现有 ${this.points}）` });
    audio.harvest();
    this.pendingShip = [];
    this.autosave();
  }

  private static readonly SHOP: Record<string, { name: string; cost: number }> = {
    can2: { name: "浇水壶 II（一次浇 3 格）", cost: 20 },
    lamp: { name: "广场灯串（南广场一盏）", cost: 8 },
    flower: { name: "南广场花坛（一座）", cost: 6 },
  };

  // open ground flanking the plaza — clear of the market's collision box
  private static readonly DECOR_SPOTS: Record<string, [number, number][]> = {
    lamp: [[25, 22], [39, 22], [25, 19], [39, 19]],
    flower: [[26, 22], [38, 22], [26, 19], [38, 19]],
  };

  buyShopItem(itemId: string): void {
    const item = TownScene.SHOP[itemId];
    if (!item) return;
    if (itemId === "can2" && this.canLevel >= 2) {
      bus.emit("toast", { text: "🛒 浇水壶 II 已经在你手里啦" });
      return;
    }
    const spots = TownScene.DECOR_SPOTS[itemId];
    const used = spots ? this.decor.filter((d) => d.id === itemId).length : 0;
    if (spots && used >= spots.length) {
      bus.emit("toast", { text: "🛒 这种摆件的位置都摆满了" });
      return;
    }
    if (this.points < item.cost) {
      bus.emit("toast", { text: `🛒 建设点不够（需要 ${item.cost}，现有 ${this.points}）` });
      return;
    }
    this.points -= item.cost;
    if (itemId === "can2") this.canLevel = 2;
    if (spots) {
      const [tx, ty] = spots[used];
      this.decor.push({ id: itemId, tx, ty });
      this.spawnDecor(itemId, tx, ty);
    }
    audio.harvest();
    bus.emit("toast", { text: `🛒 已购买：${item.name}（建设点 -${item.cost}）` });
    this.autosave();
  }

  private spawnDecor(id: string, tx: number, ty: number): void {
    if (id === "lamp") {
      const o = this.add.image(tx * TILE + 8, (ty + 1) * TILE, "decor-lamp")
        .setOrigin(0.5, 1).setDepth((ty + 1) * TILE);
      this.collide[ty][tx] = true;
      const glow = this.add.circle(tx * TILE + 8, ty * TILE - 8, 14, 0xffc966, 0)
        .setDepth(15000).setBlendMode(Phaser.BlendModes.ADD);
      this.lampGlows.push(glow);
      this.decorSprites.push(o);
    } else {
      const o = this.add.image(tx * TILE + 8, ty * TILE + 12, "decor-outdoor", 57)
        .setOrigin(0.5, 1).setDepth(ty * TILE + 12);
      this.decorSprites.push(o);
    }
  }

  /** hang a collected piece on the museum wall (+2 points, once each) */
  donate(kind: "ore" | "fish", index: number): void {
    const src = kind === "ore" ? this.ores : this.fishCaught;
    const item = src[index];
    if (!item) return;
    const wall = kind === "ore" ? this.museum.ores : this.museum.fish;
    if (wall.includes(item)) {
      bus.emit("toast", { text: "🏛 这件展品已经挂在墙上了" });
      return;
    }
    wall.push(item);
    this.points += 2;
    audio.harvest();
    bus.emit("toast", { text: `🏛 捐赠成功：${item.slice(0, 32)}（建设点 +2）` });
    if (this.museum.ores.length + this.museum.fish.length >= 8) {
      this.grantAch("museum8", "镇立博物馆开馆（馆藏×8）");
    }
    this.autosave();
  }

  /** watering can II splashes the next two cells too */
  private async waterWithCan(crop: Crop): Promise<void> {
    await this.waterCrop(crop);
    if (this.canLevel >= 2) {
      let extra = 0;
      for (const c of [this.crops.get(crop.cell + 1), this.crops.get(crop.cell + 2)]) {
        if (c && c.progress < 4) {
          await this.waterCrop(c, true);
          extra += 1;
        }
      }
      if (extra > 0) bus.emit("toast", { text: `💧 浇水壶 II 顺手浇了旁边 ${extra} 株` });
    }
  }

  // -------------------------------------------------------------- v7 quest
  private static readonly QUESTS: Record<string, string[]> = {
    opus: ["梳理本周运营报表", "把镇志目录补全"],
    codex: ["清理一张积压 PR", "给工具链补一个冒烟测试"],
    sonnet: ["整理 3 条旧记忆的标签", "归档上月的会话书"],
    haiku: ["写一段今晨速报", "巡河一圈记录水位"],
    deepseek: ["推演难题的第三种解法", "复盘昨天的推理链"],
    aris: ["更新研究看板一张卡", "记录一次实验眉目"],
    pixelcat: ["画一枚 16px 新图标", "给工坊出一版配色"],
    fable: ["采写一位居民的小传", "把矿洞传说写成两段"],
  };

  /** dialogue "接单" -> a quest crop lands in the first free farm cell */
  async takeQuest(agentId: string): Promise<void> {
    const pool = TownScene.QUESTS[agentId] ?? ["帮小镇做一件小事"];
    const title = `${agentId} 委托：${pool[(this.day + this.crops.size) % pool.length]}`;
    let cell = -1;
    const cells = FARM.w * FARM.h / 4; // plots are sparse — probe a sane range
    for (let i = 0; i < cells; i++) {
      if (!this.crops.has(i)) {
        cell = i;
        break;
      }
    }
    if (cell < 0) {
      bus.emit("toast", { text: "🌾 田里满了，先收一茬再来接单吧" });
      return;
    }
    await this.plantCrop(cell, title);
    this.bumpHearts(agentId, "quest");
    bus.emit("toast", { text: `🌱 已接下委托：${title.slice(0, 42)}` });
  }

  /** click-to-walk: straight line when clear, A* around obstacles otherwise */
  private setMoveTo(px: number, py: number): void {
    this.playerPath = null;
    this.moveTarget = null;
    if (this.lineWalkable(this.player.x, this.player.y, px, py)) {
      this.moveTarget = new Phaser.Math.Vector2(px, py);
      return;
    }
    const path = findPath(
      this.collide,
      Math.floor(this.player.x / TILE), Math.floor(this.player.y / TILE),
      Math.floor(px / TILE), Math.floor(py / TILE),
    );
    if (path && path.length > 0) {
      this.playerPath = path;
      this.playerPathIdx = 0;
    } else {
      bus.emit("toast", { text: "那里走不过去" });
    }
  }

  private tryTalk(agentId: string): void {
    if (this.uiLock) return;
    const npc = this.npcs.find((n) => n.def.id === agentId);
    if (!npc || npc.state === "inside") return;
    const d = Phaser.Math.Distance.Between(this.player.x, this.player.y, npc.sprite.x, npc.sprite.y);
    if (d > TILE * 3.2) {
      this.setMoveTo(npc.sprite.x, npc.sprite.y + 8);
      return;
    }
    npc.state = "talk";
    npc.path = null;
    npc.sprite.setVelocity(0, 0);
    const dir = npc.sprite.x > this.player.x ? "left" : "right";
    npc.sprite.play(`${npc.def.id}-idle-${dir}`, true);
    this.uiLock = true;
    const duty = dutyFor(npc.def.id, Math.floor(this.clockMin / 60));
    const activityZh =
      duty.kind === "plaza" ? "正在广场歇脚" :
      duty.kind === "inn" ? "正准备回旅店休息" :
      duty.kind === "building" ? `今天在${BUILDINGS.find((b) => b.id === duty.id)?.nameZh ?? "镇里"}当班` :
      "正在镇上转悠";
    const activityEn =
      duty.kind === "plaza" ? "taking a break at the plaza" :
      duty.kind === "inn" ? "about to head back to the inn" :
      duty.kind === "building" ? `on duty at the ${BUILDINGS.find((b) => b.id === duty.id)?.nameEn ?? "town"}` :
      "out and about";
    bus.emit("npc:talk", { agentId, activityZh, activityEn, hearts: this.hearts[agentId] ?? 0 });
    this.bumpHearts(agentId, "talk");
    if (agentId === "fable") this.tutorialHook("talk-fable");
  }

  private enterBuilding(id: string): void {
    if (this.uiLock) return;
    const b = BUILDINGS.find((bb) => bb.id === id);
    if (!b) return;
    if (id === "memory-library") this.tutorialHook("library");
    const interior = INTERIOR_BY_BUILDING.get(id);
    if (!interior) {
      this.uiLock = true;
      audio.page();
      bus.emit("building:enter", { buildingId: id });
      return;
    }
    this.uiLock = true;
    audio.door();
    this.autosave();
    this.cameras.main.fadeOut(260, 26, 20, 35);
    this.cameras.main.once(Phaser.Cameras.Scene2D.Events.FADE_OUT_COMPLETE, () => {
      this.scene.run("interior", {
        interiorId: interior.id,
        returnTx: b.tx,
        returnTy: b.ty,
        residents: this.residentsInside(id),
      });
      this.scene.sleep();
    });
  }

  // -------------------------------------------------------------------- farm
  private cellTile(cell: number): { tx: number; ty: number } {
    return this.layout.farmSoil[cell];
  }

  private async initFarm(): Promise<void> {
    if (currentMode() === "live") {
      try {
        const d = await getData<{ crops: { id?: string; title: string; stage: number; total: number }[] }>(
          "/api/town/farm", "farm.json",
        );
        d.crops.slice(0, this.layout.farmSoil.length).forEach((c, i) => {
          if (c.stage >= 5) return; // already harvested/done
          this.setCrop({
            cell: i,
            title: c.title,
            progress: Math.max(1, Math.min(4, c.stage)),
            variety: CROP_VARIETIES[this.hashTitle(c.title) % CROP_VARIETIES.length],
            taskId: c.id,
          });
        });
        return;
      } catch {
        /* fall through to demo */
      }
    }
    for (const c of this.demoCrops) {
      if (c.progress >= 5) continue;
      this.setCrop({ cell: c.cell, title: c.title, progress: c.progress, variety: c.variety });
    }
  }

  private hashTitle(s: string): number {
    let h = 0;
    for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) >>> 0;
    return h;
  }

  private setCrop(c: Crop): void {
    const old = this.crops.get(c.cell);
    old?.sprite?.destroy();
    const { tx, ty } = this.cellTile(c.cell);
    const frame = STAGE_ROW[c.progress] + c.variety;
    const spr = this.add.image(tx * TILE + 8, (ty + 1) * TILE, "ts-lpc-crops", frame)
      .setOrigin(0.5, 1).setDepth((ty + 1) * TILE - 1);
    this.crops.set(c.cell, { ...c, sprite: spr });
  }

  private removeCrop(cell: number): void {
    this.crops.get(cell)?.sprite?.destroy();
    this.crops.delete(cell);
  }

  private nearestFarmCell(): number | null {
    let best: number | null = null;
    let bestD = TILE * 1.6;
    for (let i = 0; i < this.layout.farmSoil.length; i++) {
      const { tx, ty } = this.layout.farmSoil[i];
      const d = Phaser.Math.Distance.Between(this.player.x, this.player.y, tx * TILE + 8, ty * TILE + 8);
      if (d < bestD) {
        bestD = d;
        best = i;
      }
    }
    return best;
  }

  private async plantCrop(cell: number, title: string): Promise<void> {
    this.uiLock = false;
    if (!title.trim()) return;
    if (!spendStamina(2)) return;
    const variety = CROP_VARIETIES[this.hashTitle(title) % CROP_VARIETIES.length];
    if (currentMode() === "live") {
      const r = await postData<{ id?: string }>("/api/town/farm/plant", { title });
      this.setCrop({ cell, title, progress: 1, variety, taskId: r?.id });
    } else {
      this.demoCrops = this.demoCrops.filter((c) => c.cell !== cell);
      this.demoCrops.push({ cell, title, progress: 1, variety, createdDay: this.day });
      this.setCrop({ cell, title, progress: 1, variety });
    }
    audio.plant();
    bus.emit("toast", { text: `种下任务：${title}` });
    this.tutorialHook("plant");
    this.autosave();
  }

  private async waterCrop(crop: Crop, silent = false): Promise<void> {
    if (crop.progress >= 4) return;
    if (!silent && !spendStamina(2)) return; // rain waters for free
    crop.progress += 1;
    if (currentMode() === "live" && crop.taskId) {
      void postData("/api/town/farm/water", { id: crop.taskId });
    } else {
      const d = this.demoCrops.find((c) => c.cell === crop.cell);
      if (d) d.progress = crop.progress;
    }
    this.setCrop(crop);
    if (!silent) {
      audio.water();
      bus.emit("toast", { text: `浇水：${crop.title}（${crop.progress}/4）` });
    }
    this.autosave();
  }

  private async harvestCrop(crop: Crop): Promise<void> {
    if (!spendStamina(1)) return;
    if (currentMode() === "live" && crop.taskId) {
      void postData("/api/town/farm/harvest", { id: crop.taskId });
    } else {
      const d = this.demoCrops.find((c) => c.cell === crop.cell);
      if (d) d.progress = 5;
    }
    const { tx, ty } = this.cellTile(crop.cell);
    const pop = this.add.image(tx * TILE + 8, ty * TILE, "ts-lpc-crops", PRODUCT_ROW + crop.variety)
      .setOrigin(0.5, 1).setDepth(99999);
    this.tweens.add({
      targets: pop, y: pop.y - 18, alpha: 0, duration: 900, ease: "Cubic.easeOut",
      onComplete: () => pop.destroy(),
    });
    this.removeCrop(crop.cell);
    this.harvested += 1;
    this.inventory.push({ kind: "crop", name: crop.title, variety: crop.variety });
    const questOwner = /^([a-z]+) 委托：/.exec(crop.title)?.[1];
    if (questOwner) this.bumpHearts(questOwner, "harvest");
    audio.harvest();
    bus.emit("toast", { text: `收获入包：${crop.title} ✅（累计 ${this.harvested}）` });
    this.autosave();
  }

  // -------------------------------------------------------------------- save
  private autosave(): void {
    writeSave({
      version: 3,
      day: this.day,
      clockMin: this.clockMin,
      px: this.player.x,
      py: this.player.y,
      harvested: this.harvested,
      demoCrops: this.demoCrops,
      lang: "zh",
      ores: this.ores,
      fish: this.fishCaught,
      ach: this.ach,
      points: this.points,
      inventory: this.inventory,
      pendingShip: this.pendingShip,
      stamina: currentStamina(), // save.ts owns the pool between writes
      canLevel: this.canLevel,
      museum: this.museum,
      decor: this.decor,
      tutorialStep: this.tutorialStep,
      hearts: this.hearts,
      heartsDay: this.heartsDay,
    });
  }

  // ----------------------------------------------------------- achievements
  private grantAch(id: string, name: string): void {
    if (this.ach[id]) return;
    this.ach[id] = true;
    audio.harvest();
    bus.emit("toast", { text: `🏆 成就解锁：${name}` });
    bus.emit("ach:unlocked", { name });
    this.autosave();
  }

  private checkAchievements(): void {
    if (this.harvested >= 1) this.grantAch("harvest1", "第一捧收成");
    if (this.harvested >= 5) this.grantAch("harvest5", "勤恳农夫（收获×5）");
    if (this.harvested >= 20) this.grantAch("harvest20", "谷物大亨（收获×20）");
    if (this.ores.length >= 1) this.grantAch("ore1", "第一块技术债矿石");
    if (this.ores.length >= 10) this.grantAch("ore10", "债务清道夫（矿石×10）");
    if (this.fishCaught.length >= 1) this.grantAch("fish1", "第一条日志鱼");
    if (this.fishCaught.length >= 10) this.grantAch("fish10", "日志垂钓宗师（鱼×10）");
    if (this.day >= 7) this.grantAch("week1", "在山谷住满一周");
    if (this.day >= 28) this.grantAch("season1", "四季轮转之证");
  }

  // ---------------------------------------------------------------- fishing
  private nearWater(): boolean {
    const tx = Math.floor(this.player.x / TILE);
    const ty = Math.floor((this.player.y + 12) / TILE);
    for (const [dx, dy] of [[0, 1], [0, -1], [1, 0], [-1, 0], [1, 1], [-1, 1]] as const) {
      const x = tx + dx;
      const y = ty + dy;
      if (x >= 0 && y >= 0 && x < MAP_W && y < MAP_H && this.layout.isWater[y][x]) return true;
    }
    return false;
  }

  private async resolveCatch(quality: number): Promise<void> {
    this.uiLock = false;
    if (quality <= 0) {
      bus.emit("toast", { text: "💨 鱼跑了……再试一次" });
      return;
    }
    if (!this.fishPool) {
      try {
        const d = await getData<{ fish: { text: string; level: string; rarity: number }[] }>(
          "/api/town/logs", "fish.json",
        );
        this.fishPool = d.fish;
      } catch {
        this.fishPool = [];
      }
    }
    if (!this.fishPool || this.fishPool.length === 0) {
      bus.emit("toast", { text: "🌊 今天水里很安静" });
      return;
    }
    if (!spendStamina(4)) return;
    // perfect catches bias toward rare (ERROR-grade) fish
    const pool = this.fishPool.filter((f) => (quality >= 2 ? f.rarity >= 2 : f.rarity <= 2));
    const pick = (pool.length ? pool : this.fishPool)[Math.floor(Math.random() * (pool.length || this.fishPool.length))];
    this.fishCaught.push(`[${pick.level}] ${pick.text}`);
    this.inventory.push({ kind: "fish", name: `[${pick.level}] ${pick.text}`.slice(0, 60) });
    audio.water();
    const stars = pick.rarity >= 3 ? "★★★" : pick.rarity === 2 ? "★★" : "★";
    bus.emit("toast", { text: `🎣 钓到日志鱼 ${stars}：${pick.text.slice(0, 40)}` });
    bus.emit("fish:caught", { text: pick.text, level: pick.level });
    this.checkAchievements();
    this.autosave();
  }

  // ---------------------------------------------------------------- seasons
  private applySeason(season: string): void {
    this.currentSeason = season;
    const tints: Record<string, { grass: number; path: number; tree: number }> = {
      "春": { grass: 0xffffff, path: 0xffffff, tree: 0xffffff },
      "夏": { grass: 0xeaffdc, path: 0xfff3da, tree: 0xe4ffd8 },
      "秋": { grass: 0xffd9a0, path: 0xffe9c8, tree: 0xffa860 },
      "冬": { grass: 0xd8e6f6, path: 0xe8eef8, tree: 0xcfe0f0 },
    };
    const t = tints[season] ?? tints["春"];
    this.grassLayer.setTint(t.grass);
    this.pathLayer.setTint(t.path);
    for (const img of this.treeImgs) img.setTint(t.tree);
    if (season === "冬") {
      if (!this.snow) {
        if (!this.textures.exists("snowdot")) {
          const g = this.make.graphics({ x: 0, y: 0 }, false);
          g.fillStyle(0xffffff, 1);
          g.fillRect(0, 0, 2, 2);
          g.generateTexture("snowdot", 2, 2);
          g.destroy();
        }
        const cam = this.cameras.main;
        this.snow = this.add.particles(0, 0, "snowdot", {
          x: { min: 0, max: cam.width },
          y: -6,
          lifespan: 9000,
          speedY: { min: 18, max: 42 },
          speedX: { min: -12, max: 12 },
          alpha: { start: 0.9, end: 0.4 },
          quantity: 2,
          frequency: 110,
        }).setScrollFactor(0).setDepth(19999);
      }
      this.snow.start();
    } else {
      this.snow?.stop();
    }
    if (season !== "春") bus.emit("toast", { text: `🍂 季节更替：${season}天来了` });
  }

  // --------------------------------------------------------------- festival
  private async initFestival(): Promise<void> {
    interface Fest { today: boolean; latest: { tag: string; date: string } | null }
    let fest: Fest | null = null;
    try {
      if (currentMode() === "live") {
        fest = await getData<Fest>("/api/town/festival", "__none__.json");
      } else {
        const r = await fetch("https://api.github.com/repos/appleweiping/newroad-valley/releases/latest");
        if (r.ok) {
          const data = await r.json();
          const date = String(data.published_at ?? "").slice(0, 10);
          const today = new Date().toISOString().slice(0, 10);
          fest = { today: date === today, latest: { tag: data.tag_name, date } };
        }
      }
    } catch {
      fest = null;
    }
    if (fest?.today) {
      this.festivalToday = true;
      this.decorateFestival(fest.latest?.tag ?? "");
    }
  }

  private decorateFestival(tag: string): void {
    // bunting strung across the plaza between the lamp posts
    const colors = [0xff8a8a, 0xffd27a, 0x9be564, 0x8ad2ff, 0xd0a4ff];
    for (let x = 27; x <= 37; x++) {
      const flag = this.add.triangle(
        x * TILE + 8, 16.4 * TILE + ((x % 2) ? 3 : 0),
        0, 0, 8, 0, 4, 7,
        colors[x % colors.length],
      ).setDepth(15001);
      this.festivalDecor.push(flag);
    }
    bus.emit("toast", { text: `🎉 今天是丰收节（${tag} 发布日）！夜里广场有烟花` });
    this.grantAch("festival1", "赶上了丰收节");
  }

  private fireworksTick(): void {
    if (!this.festivalToday || this.nightOverlay.fillAlpha < 0.3) return;
    if (this.time.now - this.lastFirework < 3600) return;
    this.lastFirework = this.time.now;
    if (!this.textures.exists("snowdot")) {
      const g = this.make.graphics({ x: 0, y: 0 }, false);
      g.fillStyle(0xffffff, 1);
      g.fillRect(0, 0, 2, 2);
      g.generateTexture("snowdot", 2, 2);
      g.destroy();
    }
    const x = (28 + Math.random() * 9) * TILE;
    const y = (13 + Math.random() * 3) * TILE;
    const tint = [0xff8a8a, 0xffd27a, 0x9be564, 0x8ad2ff, 0xd0a4ff][Math.floor(Math.random() * 5)];
    const burst = this.add.particles(x, y, "snowdot", {
      speed: { min: 30, max: 85 },
      lifespan: 750,
      quantity: 26,
      tint,
      alpha: { start: 1, end: 0 },
      emitting: false,
    }).setDepth(19998);
    burst.explode(26, x, y);
    this.time.delayedCall(1000, () => burst.destroy());
  }

  // ------------------------------------------------------------------ update
  update(time: number): void {
    this.updatePlayer();
    this.updateNpcs(time);
    this.maybeChitchat(time);
    this.updateHint();
  }

  private isBlocked(px: number, py: number): boolean {
    const tx = Math.floor(px / TILE);
    const ty = Math.floor(py / TILE);
    if (tx < 0 || ty < 0 || tx >= MAP_W || ty >= MAP_H) return true;
    return this.collide[ty][tx];
  }

  private moveWithCollision(sprite: Phaser.Physics.Arcade.Sprite, vx: number, vy: number, dt: number): void {
    const ox = sprite.x;
    const oy = sprite.y;
    const nx = sprite.x + vx * dt;
    const ny = sprite.y + vy * dt;
    const footY = sprite.y + 12;
    if (vx !== 0 && !this.isBlocked(nx + Math.sign(vx) * 5, footY)) sprite.x = nx;
    const footNY = ny + 12;
    if (vy !== 0 && !this.isBlocked(sprite.x, footNY + (vy > 0 ? 2 : -2))) sprite.y = ny;
    // corner-clip guard: the two axis moves can pass individually yet land
    // the foot inside a blocked tile — that's how sprites used to tunnel
    // through building corners. Revert outright if it happens.
    if (this.isBlocked(sprite.x, sprite.y + 12)) {
      sprite.x = ox;
      sprite.y = oy;
    }
    sprite.setDepth(sprite.y);
  }

  /** straight segment walkability (sampled every ~6px at foot height) */
  private lineWalkable(x1: number, y1: number, x2: number, y2: number): boolean {
    const d = Math.hypot(x2 - x1, y2 - y1);
    const steps = Math.max(2, Math.ceil(d / 6));
    for (let i = 1; i <= steps; i++) {
      const t = i / steps;
      if (this.isBlocked(x1 + (x2 - x1) * t, y1 + (y2 - y1) * t + 12)) return false;
    }
    return true;
  }

  private updatePlayer(): void {
    const speed = 85;
    const dt = this.game.loop.delta / 1000;
    let vx = 0;
    let vy = 0;
    if (!this.uiLock) {
      if (this.cursors.left.isDown || this.wasd.A.isDown) vx = -1;
      else if (this.cursors.right.isDown || this.wasd.D.isDown) vx = 1;
      if (this.cursors.up.isDown || this.wasd.W.isDown) vy = -1;
      else if (this.cursors.down.isDown || this.wasd.S.isDown) vy = 1;
      if (vx === 0 && vy === 0 && touchState.active) {
        vx = touchState.vx; // analog joystick merges in like a key-pair
        vy = touchState.vy;
      }
    }
    if (vx !== 0 || vy !== 0) {
      this.moveTarget = null;
      this.playerPath = null;
      this.following = true;
      this.cameras.main.startFollow(this.player, true, 0.12, 0.12);
    } else if (this.playerPath && !this.uiLock) {
      const wp = this.playerPath[this.playerPathIdx];
      if (!wp) {
        this.playerPath = null;
      } else {
        const wx = wp.x * TILE + 8;
        const wy = wp.y * TILE + 8;
        const d = Phaser.Math.Distance.Between(this.player.x, this.player.y, wx, wy);
        if (d < 3) this.playerPathIdx += 1;
        else {
          vx = (wx - this.player.x) / d;
          vy = (wy - this.player.y) / d;
        }
      }
    } else if (this.moveTarget && !this.uiLock) {
      const d = Phaser.Math.Distance.Between(this.player.x, this.player.y, this.moveTarget.x, this.moveTarget.y);
      if (d < 4) this.moveTarget = null;
      else {
        vx = (this.moveTarget.x - this.player.x) / d;
        vy = (this.moveTarget.y - this.player.y) / d;
      }
    }
    const len = Math.hypot(vx, vy);
    if (len > 0) {
      vx = (vx / len) * speed;
      vy = (vy / len) * speed;
      this.moveWithCollision(this.player, vx, vy, dt);
      const dir = Math.abs(vx) > Math.abs(vy) ? (vx > 0 ? "right" : "left") : vy > 0 ? "down" : "up";
      this.player.play(`player-walk-${dir}`, true);
      audio.step();
      bus.emit("player:moved", { tx: Math.floor(this.player.x / TILE), ty: Math.floor(this.player.y / TILE) });
    } else {
      const cur = this.player.anims.currentAnim?.key ?? "player-walk-down";
      const dir = cur.split("-").pop() ?? "down";
      this.player.play(`player-idle-${dir}`, true);
    }
    this.playerShadow.setPosition(this.player.x, this.player.y + 12);
    if (this.wasd.F.isDown && !this.following) {
      this.following = true;
      this.cameras.main.startFollow(this.player, true, 0.12, 0.12);
    }
    const touchE = this.touchInteract;
    this.touchInteract = false;
    if ((Phaser.Input.Keyboard.JustDown(this.wasd.E) || touchE) && !this.uiLock && this.time.now > this.actionCooldown) {
      this.actionCooldown = this.time.now + 350;
      // 1) farm action
      const cell = this.nearestFarmCell();
      if (cell !== null) {
        const crop = this.crops.get(cell);
        if (!crop) {
          this.uiLock = true;
          bus.emit("farm:plant-request", { cell });
          return;
        }
        if (crop.progress >= 4) {
          void this.harvestCrop(crop);
        } else {
          void this.waterWithCan(crop);
        }
        return;
      }
      // 2) mine entrance
      if (this.mineZone.contains(this.player.x, this.player.y)) {
        this.enterMine();
        return;
      }
      // 2.5) shipping bin
      const [btx, bty] = this.binTile;
      if (Phaser.Math.Distance.Between(this.player.x, this.player.y, btx * TILE + 8, bty * TILE + 8) < TILE * 1.8) {
        this.uiLock = true;
        audio.click();
        bus.emit("almanac:tab", { tab: "ship" });
        return;
      }
      // 2.6) plaza notice board -> the town chronicle
      if (Phaser.Math.Distance.Between(this.player.x, this.player.y, 29 * TILE + 8, 18 * TILE + 8) < TILE * 1.8) {
        this.uiLock = true;
        audio.page();
        bus.emit("almanac:tab", { tab: "chronicle" });
        return;
      }
      // 3) fishing at the water's edge
      if (this.nearWater()) {
        this.uiLock = true;
        audio.click();
        bus.emit("fishing:start", undefined);
        return;
      }
      // 4) npc
      let best: Npc | null = null;
      let bestD = TILE * 2.6;
      for (const n of this.npcs) {
        if (n.state === "inside") continue;
        const d = Phaser.Math.Distance.Between(this.player.x, this.player.y, n.sprite.x, n.sprite.y);
        if (d < bestD) {
          bestD = d;
          best = n;
        }
      }
      if (best) {
        this.tryTalk(best.def.id);
        return;
      }
      // 3) door
      for (const z of this.doorZones) {
        if (z.rect.contains(this.player.x, this.player.y)) {
          this.enterBuilding(z.id);
          return;
        }
      }
    }
  }

  // ---------------------------------------------------------------- schedule
  private applyDuty(n: Npc, duty: Duty): void {
    n.duty = duty.kind;
    const exitInside = () => {
      if (n.state === "inside" && n.insideBuilding) {
        const b = BUILDINGS.find((bb) => bb.id === n.insideBuilding)!;
        n.sprite.setPosition(b.tx * TILE + 8, (b.ty + 1) * TILE - 2);
        n.sprite.setVisible(true).setAlpha(0);
        n.label.setVisible(true);
        n.shadow.setVisible(true);
        this.tweens.add({ targets: n.sprite, alpha: 1, duration: 400 });
        n.insideBuilding = null;
      }
    };

    const goTo = (tx: number, ty: number, then: "inside" | "idle", buildingId?: string) => {
      exitInside();
      const sx = Math.floor(n.sprite.x / TILE);
      const sy = Math.floor(n.sprite.y / TILE);
      const path = findPath(this.collide, sx, sy, tx, ty);
      if (!path || path.length === 0) {
        if (then === "inside" && buildingId) this.hideInside(n, buildingId);
        else n.state = "idle";
        return;
      }
      n.path = path;
      n.pathIdx = 0;
      n.state = "path";
      (n as Npc & { after?: { kind: string; buildingId?: string } }).after = undefined;
      if (then === "inside" && buildingId) {
        (n as Npc & { after?: { kind: string; buildingId?: string } }).after = { kind: "inside", buildingId };
      }
    };

    switch (duty.kind) {
      case "building": {
        const b = BUILDINGS.find((bb) => bb.id === duty.id);
        if (!b) return;
        if (n.insideBuilding === duty.id) return;
        goTo(b.tx, b.ty, "inside", duty.id);
        break;
      }
      case "inn": {
        const inn = BUILDINGS.find((bb) => bb.id === "agent-inn")!;
        if (n.insideBuilding === "agent-inn") return;
        goTo(inn.tx, inn.ty, "inside", "agent-inn");
        break;
      }
      case "plaza": {
        goTo(PLAZA.tx + Math.floor(Math.random() * 5) - 2, PLAZA.ty + Math.floor(Math.random() * 3) - 1, "idle");
        break;
      }
      default: {
        exitInside();
        goTo(n.def.tx, n.def.ty, "idle");
      }
    }
  }

  private hideInside(n: Npc, buildingId: string): void {
    n.state = "inside";
    n.insideBuilding = buildingId;
    n.path = null;
    this.tweens.add({
      targets: n.sprite, alpha: 0, duration: 350,
      onComplete: () => {
        n.sprite.setVisible(false);
        n.label.setVisible(false);
        n.emote.setVisible(false);
        n.shadow.setVisible(false);
      },
    });
  }

  private updateNpcs(time: number): void {
    const dt = this.game.loop.delta / 1000;
    const hour = Math.floor(this.clockMin / 60);
    for (const n of this.npcs) {
      const duty = dutyFor(n.def.id, hour);
      if (duty.kind !== n.duty && n.state !== "talk") {
        this.applyDuty(n, duty);
      }
      if (n.state === "inside") continue;

      n.label.setPosition(n.sprite.x, n.sprite.y - 24);
      n.emote.setPosition(n.sprite.x, n.sprite.y - 34);
      n.shadow.setPosition(n.sprite.x, n.sprite.y + 12);
      n.shadow.setVisible(n.sprite.visible);
      const near = Phaser.Math.Distance.Between(this.player.x, this.player.y, n.sprite.x, n.sprite.y) < TILE * 3.2;
      if (near && n.state !== "talk") {
        if (!n.emote.visible) {
          n.emote.setVisible(true);
          n.emote.play("emote-alert");
        }
      } else if (n.emote.visible) {
        n.emote.setVisible(false);
        n.emote.stop();
      }
      if (n.state === "talk") continue;

      // stuck watchdog: grinding against a wall for >1.2s means the straight
      // line failed — re-route via A* (path) or give up (wander)
      if (n.state === "walk" || n.state === "path") {
        const moved = Math.hypot(n.sprite.x - n.lastPX, n.sprite.y - n.lastPY);
        n.stuckMs = moved < 0.15 ? n.stuckMs + this.game.loop.delta : 0;
        n.lastPX = n.sprite.x;
        n.lastPY = n.sprite.y;
        if (n.stuckMs > 1200) {
          n.stuckMs = 0;
          if (n.state === "path" && n.path && n.path.length > 0) {
            const dest = n.path[n.path.length - 1];
            const np = findPath(
              this.collide,
              Math.floor(n.sprite.x / TILE), Math.floor(n.sprite.y / TILE),
              dest.x, dest.y,
            );
            if (np && np.length > 0) {
              n.path = np;
              n.pathIdx = 0;
            } else {
              n.path = null;
              n.state = "idle";
              (n as Npc & { after?: unknown }).after = undefined;
            }
          } else {
            n.state = "idle";
            n.target = null;
          }
        }
      }

      if (n.state === "path" && n.path) {
        const wp = n.path[n.pathIdx];
        if (!wp) {
          n.path = null;
          const after = (n as Npc & { after?: { kind: string; buildingId?: string } }).after;
          if (after?.kind === "inside" && after.buildingId) this.hideInside(n, after.buildingId);
          else n.state = "idle";
          continue;
        }
        const wx = wp.x * TILE + 8;
        const wy = wp.y * TILE + 8;
        const d = Phaser.Math.Distance.Between(n.sprite.x, n.sprite.y, wx, wy);
        if (d < 3) {
          n.pathIdx += 1;
        } else {
          const sp = 44;
          const vx = ((wx - n.sprite.x) / d) * sp;
          const vy = ((wy - n.sprite.y) / d) * sp;
          this.moveWithCollision(n.sprite, vx, vy, dt);
          const dir = Math.abs(vx) > Math.abs(vy) ? (vx > 0 ? "right" : "left") : vy > 0 ? "down" : "up";
          n.sprite.play(`${n.def.id}-walk-${dir}`, true);
        }
        continue;
      }

      // free wander
      if (time > n.nextThink) {
        n.nextThink = time + 2200 + Math.random() * 3800;
        if (n.state === "idle" && Math.random() < 0.65) {
          const ax = n.sprite.x;
          const ay = n.sprite.y;
          for (let tries = 0; tries < 6; tries++) {
            const tx = ax + (Math.random() * 8 - 4) * TILE;
            const ty = ay + (Math.random() * 6 - 3) * TILE;
            // destination must be free AND reachable in a straight line —
            // otherwise the dumb walk just grinds against a house wall
            if (!this.isBlocked(tx, ty + 12) && this.lineWalkable(n.sprite.x, n.sprite.y, tx, ty)) {
              n.target = new Phaser.Math.Vector2(tx, ty);
              n.state = "walk";
              break;
            }
          }
        } else {
          n.state = "idle";
          n.target = null;
        }
      }
      if (n.state === "walk" && n.target) {
        const d = Phaser.Math.Distance.Between(n.sprite.x, n.sprite.y, n.target.x, n.target.y);
        if (d < 3) {
          n.state = "idle";
          n.target = null;
          const cur = n.sprite.anims.currentAnim?.key ?? `${n.def.id}-walk-down`;
          n.sprite.play(`${n.def.id}-idle-${cur.split("-").pop() ?? "down"}`, true);
        } else {
          const sp = 38;
          const vx = ((n.target.x - n.sprite.x) / d) * sp;
          const vy = ((n.target.y - n.sprite.y) / d) * sp;
          this.moveWithCollision(n.sprite, vx, vy, dt);
          const dir = Math.abs(vx) > Math.abs(vy) ? (vx > 0 ? "right" : "left") : vy > 0 ? "down" : "up";
          n.sprite.play(`${n.def.id}-walk-${dir}`, true);
        }
      } else if (n.state === "idle") {
        const cur = n.sprite.anims.currentAnim?.key ?? `${n.def.id}-walk-down`;
        const dir = cur.split("-").pop() ?? "down";
        n.sprite.play(`${n.def.id}-idle-${dir}`, true);
      }
    }
  }

  private updateHint(): void {
    let hint = "";
    if (!this.uiLock) {
      const cell = this.nearestFarmCell();
      if (cell !== null) {
        const crop = this.crops.get(cell);
        if (!crop) hint = "按 E 在这块田里种下一个任务";
        else if (crop.progress >= 4) hint = `按 E 收获「${crop.title}」`;
        else hint = `按 E 给「${crop.title}」浇水（${crop.progress}/4）`;
      }
      if (!hint) {
        for (const n of this.npcs) {
          if (n.state === "inside") continue;
          if (Phaser.Math.Distance.Between(this.player.x, this.player.y, n.sprite.x, n.sprite.y) < TILE * 3.2) {
            hint = `按 E 与 ${n.def.nameZh} 对话`;
            break;
          }
        }
      }
      if (!hint && this.mineZone.contains(this.player.x, this.player.y)) {
        hint = "按 E 进入技术债矿洞";
      }
      if (!hint && this.nearWater()) {
        hint = "按 E 在水边垂钓日志鱼";
      }
      if (!hint) {
        for (const z of this.doorZones) {
          if (z.rect.contains(this.player.x, this.player.y)) {
            const b = BUILDINGS.find((bb) => bb.id === z.id)!;
            hint = INTERIOR_BY_BUILDING.has(b.id) ? `按 E 走进 ${b.nameZh}` : `按 E 查看 ${b.nameZh}`;
            break;
          }
        }
      }
    }
    this.hintText.setText(hint);
  }
}
