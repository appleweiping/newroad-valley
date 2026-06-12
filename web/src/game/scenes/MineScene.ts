import Phaser from "phaser";
import { bus } from "@/shared/bus";
import { getData } from "@/shared/api";
import { audio } from "@/game/audio";

const T = 16;
const W = 15;
const H = 11;

/** cold stone walls (mystic walls.png frame map, see InteriorScene) */
const WALL = {
  capTL: 0, capT: 1, capTR: 3,
  faceTL: 32, faceT: 33, faceTR: 35,
  faceBL: 40, faceB: 41, faceBR: 43,
  sideL: 8, sideR: 11,
  botL: 24, botT: 25, botR: 27,
};

interface Ore {
  id: string;
  kind: string;
  title: string;
  file: string;
  repo: string;
  depth: number;
}

const KIND_TINT: Record<string, number> = {
  todo: 0x9fd6ff,    // sky crystal
  hack: 0xffd27a,    // amber crystal
  fixme: 0xff9b9b,   // danger crystal
  hotspot: 0xc99bff, // violet crystal
};

interface OreNode {
  ore: Ore;
  sprite: Phaser.GameObjects.Image;
  hits: number;
  tx: number;
  ty: number;
  collected: boolean;
}

interface EnterData {
  level: number;
  returnTx: number;
  returnTy: number;
}

/** The tech-debt mines: each level holds ore mined from real TODO/FIXME
 * comments and git hotspots. Hit a node three times to extract the debt
 * card; deeper levels carry heavier debt. */
export class MineScene extends Phaser.Scene {
  private level = 1;
  private enterData!: EnterData;
  private player!: Phaser.GameObjects.Sprite;
  private playerShadow!: Phaser.GameObjects.Ellipse;
  private cursors!: Phaser.Types.Input.Keyboard.CursorKeys;
  private wasd!: Record<"W" | "A" | "S" | "D" | "E", Phaser.Input.Keyboard.Key>;
  private collide: boolean[][] = [];
  private nodes: OreNode[] = [];
  private ladder: { tx: number; ty: number } | null = null;
  private hint!: Phaser.GameObjects.Text;
  private moveTarget: { x: number; y: number } | null = null;
  private leaving = false;
  private oresPool: Ore[] = [];
  private uiLock = false;

  constructor() {
    super("mine");
  }

  init(data: EnterData): void {
    this.enterData = data;
    this.level = data.level || 1;
    this.leaving = false;
    this.uiLock = false;
    this.nodes = [];
    this.ladder = null;
    this.moveTarget = null;
  }

  create(): void {
    this.collide = Array.from({ length: H }, () => Array<boolean>(W).fill(false));
    this.buildCave();
    void this.populate();

    this.playerShadow = this.add.ellipse(7 * T + 16, (H - 1) * T - 4, 16, 6, 0x000000, 0.4).setDepth(2.5);
    this.player = this.add.sprite(7 * T + 16, (H - 1) * T - 18, "char-player", 0);
    this.player.setDepth(this.player.y);

    this.cursors = this.input.keyboard!.createCursorKeys();
    this.wasd = this.input.keyboard!.addKeys("W,A,S,D,E") as MineScene["wasd"];

    this.hint = this.add
      .text(this.cameras.main.width / 2, this.cameras.main.height - 8, "", {
        fontFamily: "'Microsoft YaHei', sans-serif",
        fontSize: "12px", color: "#ffe9c0", stroke: "#241a12", strokeThickness: 4, resolution: 3,
      })
      .setOrigin(0.5, 1).setScrollFactor(0).setDepth(20001);

    this.add
      .text(this.cameras.main.width / 2, 10, `技术债矿洞 · 第 ${this.level} 层`, {
        fontFamily: "'Microsoft YaHei', sans-serif",
        fontSize: "13px", color: "#c9b8ff", stroke: "#241a12", strokeThickness: 4, resolution: 3,
      })
      .setOrigin(0.5, 0).setScrollFactor(0).setDepth(20001);

    const cam = this.cameras.main;
    cam.setBounds(0, 0, W * T, H * T);
    cam.setZoom(Math.max(3, Math.floor(Math.min(cam.width / (W * T), cam.height / (H * T)) * 2) / 2));
    cam.centerOn((W * T) / 2, (H * T) / 2);
    cam.fadeIn(320, 8, 6, 12);

    // lantern glow ambience
    for (const [lx, ly] of [[2, 2], [12, 2]] as const) {
      const glow = this.add.circle(lx * T + 8, ly * T + 8, 26, 0xffb45e, 0.13)
        .setDepth(15000).setBlendMode(Phaser.BlendModes.ADD);
      this.tweens.add({ targets: glow, alpha: 0.22, duration: 1400, yoyo: true, repeat: -1 });
    }

    this.input.on("pointerup", (p: Phaser.Input.Pointer) => {
      if (this.uiLock) return;
      const world = cam.getWorldPoint(p.x, p.y);
      this.moveTarget = { x: world.x, y: world.y };
    });

    const offs = [
      bus.on("panel:closed", () => { this.uiLock = false; }),
      bus.on("dialogue:closed", () => { this.uiLock = false; }),
    ];
    this.events.once(Phaser.Scenes.Events.SHUTDOWN, () => offs.forEach((off) => off()));
  }

  private buildCave(): void {
    // dark dirt floor: reuse wooden floor heavily darkened reads as packed earth
    for (let y = 2; y < H; y++) {
      for (let x = 0; x < W; x++) {
        this.add.image(x * T + 8, y * T + 8, "ts-floor-wooden", 0).setDepth(0).setTint(0x4a4038);
      }
    }
    const put = (frame: number, tx: number, ty: number, depth = 1) =>
      this.add.image(tx * T + 8, ty * T + 8, "ts-walls", frame).setDepth(depth).setTint(0x9a92a8);
    for (let x = 0; x < W; x++) {
      put(x === 0 ? WALL.capTL : x === W - 1 ? WALL.capTR : WALL.capT, x, 0);
      put(x === 0 ? WALL.faceTL : x === W - 1 ? WALL.faceTR : WALL.faceT, x, 1);
      put(x === 0 ? WALL.faceBL : x === W - 1 ? WALL.faceBR : WALL.faceB, x, 2);
      this.collide[0][x] = this.collide[1][x] = this.collide[2][x] = true;
    }
    for (let y = 3; y < H - 1; y++) {
      put(WALL.sideL, 0, y);
      put(WALL.sideR, W - 1, y);
      this.collide[y][0] = this.collide[y][W - 1] = true;
    }
    const gap = (x: number) => x === 7 || x === 8;
    for (let x = 0; x < W; x++) {
      if (gap(x)) continue;
      put(x === 0 ? WALL.botL : x === W - 1 ? WALL.botR : WALL.botT, x, H - 1, (H - 1) * T + 8);
      this.collide[H - 1][x] = true;
    }
  }

  private async populate(): Promise<void> {
    if (this.oresPool.length === 0) {
      try {
        const d = await getData<{ ores: Ore[] }>("/api/town/debt", "debt.json");
        this.oresPool = d.ores;
      } catch {
        this.oresPool = [];
      }
    }
    // this level's ore: depth match (deeper level = heavier debt), pad with any
    const want = this.oresPool.filter((o) => o.depth === Math.min(3, this.level));
    const pool = [...want, ...this.oresPool.filter((o) => o.depth !== Math.min(3, this.level))];
    const spots: [number, number][] = [[3, 4], [6, 5], [10, 4], [12, 6], [4, 7], [9, 7]];
    const count = Math.min(spots.length, Math.max(3, 3 + this.level));
    for (let i = 0; i < count && i < pool.length; i++) {
      const [tx, ty] = spots[i];
      const ore = pool[(this.level * 7 + i * 3) % pool.length];
      const sprite = this.add.image(tx * T + 8, (ty + 1) * T, "prop-ore-node")
        .setOrigin(0.5, 1).setDepth((ty + 1) * T)
        .setTint(KIND_TINT[ore.kind] ?? 0x9fd6ff);
      this.collide[ty][tx] = true;
      this.nodes.push({ ore, sprite, hits: 0, tx, ty, collected: false });
    }
    // ladder down (until level 3)
    if (this.level < 3) {
      this.ladder = { tx: 12, ty: 8 };
      this.add.image(12 * T + 8, 8 * T + 8, "prop-ladder-down").setDepth(2);
    }
  }

  private isBlocked(px: number, py: number): boolean {
    const tx = Math.floor(px / T);
    const ty = Math.floor(py / T);
    if (tx < 0 || ty < 0 || tx >= W || ty >= H) return true;
    return this.collide[ty][tx];
  }

  update(): void {
    if (!this.player || this.leaving) return;
    const speed = 80;
    const dt = this.game.loop.delta / 1000;
    let vx = 0;
    let vy = 0;
    if (!this.uiLock) {
      if (this.cursors.left.isDown || this.wasd.A.isDown) vx = -1;
      else if (this.cursors.right.isDown || this.wasd.D.isDown) vx = 1;
      if (this.cursors.up.isDown || this.wasd.W.isDown) vy = -1;
      else if (this.cursors.down.isDown || this.wasd.S.isDown) vy = 1;
    }
    if (vx !== 0 || vy !== 0) this.moveTarget = null;
    else if (this.moveTarget && !this.uiLock) {
      const d = Phaser.Math.Distance.Between(this.player.x, this.player.y, this.moveTarget.x, this.moveTarget.y);
      if (d < 3) this.moveTarget = null;
      else {
        vx = (this.moveTarget.x - this.player.x) / d;
        vy = (this.moveTarget.y - this.player.y) / d;
      }
    }
    const len = Math.hypot(vx, vy);
    if (len > 0) {
      vx = (vx / len) * speed * dt;
      vy = (vy / len) * speed * dt;
      const footY = this.player.y + 10;
      if (vx !== 0 && !this.isBlocked(this.player.x + vx + Math.sign(vx) * 4, footY)) this.player.x += vx;
      if (vy !== 0 && !this.isBlocked(this.player.x, footY + vy + (vy > 0 ? 2 : -2))) this.player.y += vy;
      if (this.isBlocked(this.player.x, this.player.y + 10)) {
        this.player.x -= vx;
        this.player.y -= vy;
      }
      this.player.setDepth(this.player.y);
      const dir = Math.abs(vx) > Math.abs(vy) ? (vx > 0 ? "right" : "left") : vy > 0 ? "down" : "up";
      this.player.play(`player-walk-${dir}`, true);
      audio.step();
    } else {
      const cur = this.player.anims.currentAnim?.key ?? "player-walk-down";
      this.player.play(`player-idle-${cur.split("-").pop() ?? "down"}`, true);
    }
    this.playerShadow.setPosition(this.player.x, this.player.y + 12);

    // exit through the bottom gap
    const ptx = Math.floor(this.player.x / T);
    if ((ptx === 7 || ptx === 8) && this.player.y >= (H - 1) * T - 2) {
      this.leave();
      return;
    }

    // nearest interactable
    let hint = "走到下方门口离开";
    let target: OreNode | null = null;
    for (const n of this.nodes) {
      if (n.collected) continue;
      const d = Phaser.Math.Distance.Between(this.player.x, this.player.y, n.tx * T + 8, n.ty * T + 8);
      if (d < T * 1.9) {
        target = n;
        hint = `按 E 开采 [${n.ore.kind.toUpperCase()}] ${n.ore.title.slice(0, 18)}…（${n.hits}/3）`;
        break;
      }
    }
    let onLadder = false;
    if (!target && this.ladder) {
      const d = Phaser.Math.Distance.Between(this.player.x, this.player.y, this.ladder.tx * T + 8, this.ladder.ty * T + 8);
      if (d < T * 1.6) {
        onLadder = true;
        hint = `按 E 下到第 ${this.level + 1} 层`;
      }
    }
    this.hint.setText(this.uiLock ? "" : hint);

    if (Phaser.Input.Keyboard.JustDown(this.wasd.E) && !this.uiLock) {
      if (target) {
        this.hitNode(target);
      } else if (onLadder) {
        this.cameras.main.fadeOut(240, 8, 6, 12);
        this.time.delayedCall(280, () => {
          this.scene.restart({ level: this.level + 1, returnTx: this.enterData.returnTx, returnTy: this.enterData.returnTy });
        });
      }
    }
  }

  private hitNode(n: OreNode): void {
    n.hits += 1;
    audio.plant();
    this.cameras.main.shake(70, 0.004);
    this.tweens.add({ targets: n.sprite, x: n.sprite.x + 2, duration: 45, yoyo: true, repeat: 1 });
    if (n.hits === 2) {
      n.sprite.setTexture("prop-ore-node-cracked");
      n.sprite.setTint(KIND_TINT[n.ore.kind] ?? 0x9fd6ff);
    }
    if (n.hits >= 3 && !n.collected) {
      n.collected = true;
      this.collide[n.ty][n.tx] = false;
      audio.harvest();
      const pop = this.add.image(n.sprite.x, n.sprite.y - 10, "prop-ore-node")
        .setOrigin(0.5, 1).setScale(0.7).setDepth(99999)
        .setTint(KIND_TINT[n.ore.kind] ?? 0x9fd6ff);
      this.tweens.add({
        targets: pop, y: pop.y - 16, alpha: 0, duration: 800, ease: "Cubic.easeOut",
        onComplete: () => pop.destroy(),
      });
      n.sprite.destroy();
      bus.emit("ore:collected", { title: n.ore.title, kind: n.ore.kind, repo: n.ore.repo, file: n.ore.file });
    }
  }

  private leave(): void {
    if (this.leaving) return;
    this.leaving = true;
    audio.door();
    this.cameras.main.fadeOut(260, 8, 6, 12);
    this.time.delayedCall(300, () => {
      this.scene.stop();
      this.scene.wake("town", { returnTx: this.enterData.returnTx, returnTy: this.enterData.returnTy });
    });
  }
}
