import Phaser from "phaser";
import { AGENTS } from "@/data/town";
import { INTERIORS, type InteriorDef } from "@/data/interiors";
import { bus } from "@/shared/bus";
import { audio } from "@/game/audio";
import { touchState } from "@/shared/touch";
import { loadSave } from "@/shared/save";

const T = 16;

/** Mystic Woods walls.png frame map (verified visually). */
const WALL = {
  capTL: 0, capT: 1, capTR: 3,
  faceTL: 32, faceT: 33, faceTR: 35,
  faceBL: 40, faceB: 41, faceBR: 43,
  sideL: 8, sideR: 11,
  botL: 24, botT: 25, botR: 27,
};

interface EnterData {
  interiorId: string;
  /** town tile to return to */
  returnTx: number;
  returnTy: number;
  /** residents currently stationed in this building */
  residents: string[];
}

export class InteriorScene extends Phaser.Scene {
  private def!: InteriorDef;
  private enterData!: EnterData;
  private player!: Phaser.GameObjects.Sprite;
  private cursors!: Phaser.Types.Input.Keyboard.CursorKeys;
  private wasd!: Record<"W" | "A" | "S" | "D" | "E", Phaser.Input.Keyboard.Key>;
  private collide: boolean[][] = [];
  private uiLock = false;
  private hint!: Phaser.GameObjects.Text;
  private interactables: { tx: number; ty: number; labelZh: string; panel?: string; action?: string }[] = [];
  private residents: { id: string; sprite: Phaser.GameObjects.Sprite }[] = [];
  private moveTarget: Phaser.Math.Vector2 | null = null;
  private playerShadow!: Phaser.GameObjects.Ellipse;

  constructor() {
    super("interior");
  }

  init(data: EnterData): void {
    this.enterData = data;
    this.def = INTERIORS.find((i) => i.id === data.interiorId)!;
    this.leaving = false;
  }

  create(): void {
    const { def } = this;
    this.uiLock = false;
    this.interactables = [];
    this.residents = [];
    this.moveTarget = null;
    this.collide = Array.from({ length: def.h }, () => Array<boolean>(def.w).fill(false));

    this.buildRoom();
    this.buildFixtures();
    if (def.id === "museum") this.buildMuseumExhibits();
    this.buildResidents();

    this.playerShadow = this.add
      .ellipse(def.exitX * T + 16, (def.h - 1) * T - 4, 16, 6, 0x1c140e, 0.3)
      .setDepth(2.5);
    this.player = this.add.sprite(def.exitX * T + 16, (def.h - 1) * T - 16, "char-player", 0);
    this.player.setDepth(this.player.y);

    this.cursors = this.input.keyboard!.createCursorKeys();
    this.wasd = this.input.keyboard!.addKeys("W,A,S,D,E") as InteriorScene["wasd"];
    // scene restarts per building — unhook on shutdown or listeners pile up
    const offTouch = bus.on("touch:interact", () => {
      if (this.scene.isActive()) this.touchInteract = true;
    });
    this.events.once(Phaser.Scenes.Events.SHUTDOWN, offTouch);

    this.hint = this.add
      .text(this.cameras.main.width / 2, this.cameras.main.height - 8, "", {
        fontFamily: "'Microsoft YaHei', sans-serif",
        fontSize: "12px", color: "#fff7e6", stroke: "#5a3b28", strokeThickness: 4, resolution: 3,
      })
      .setOrigin(0.5, 1).setScrollFactor(0).setDepth(20001);

    const roomName = this.add
      .text(this.cameras.main.width / 2, 10, this.def.nameZh, {
        fontFamily: "'Microsoft YaHei', sans-serif",
        fontSize: "13px", color: "#ffd97a", stroke: "#5a3b28", strokeThickness: 4, resolution: 3,
      })
      .setOrigin(0.5, 0).setScrollFactor(0).setDepth(20001);
    void roomName;

    const cam = this.cameras.main;
    cam.setBounds(0, 0, def.w * T, def.h * T);
    const zoom = Math.min(4, Math.floor(Math.min(cam.width / (def.w * T), cam.height / (def.h * T)) * 2) / 2);
    cam.setZoom(Math.max(3, zoom));
    cam.centerOn((def.w * T) / 2, (def.h * T) / 2);
    cam.fadeIn(350, 26, 20, 35);

    this.input.on("pointerup", (p: Phaser.Input.Pointer) => {
      if (this.uiLock) return;
      const world = cam.getWorldPoint(p.x, p.y);
      this.moveTarget = new Phaser.Math.Vector2(world.x, world.y);
    });

    const offs = [
      bus.on("dialogue:closed", () => { this.uiLock = false; }),
      bus.on("panel:closed", () => { this.uiLock = false; }),
      bus.on("sleep:done", () => {
        this.uiLock = false;
        this.cameras.main.flash(600, 26, 20, 35);
      }),
    ];
    this.events.once(Phaser.Scenes.Events.SHUTDOWN, () => offs.forEach((off) => off()));

    bus.emit("toast", { text: this.def.nameZh });
  }

  private buildRoom(): void {
    const { def } = this;
    const wallKey = def.warmWalls ? "ts-walls-warm" : "ts-walls";
    const put = (key: string, frame: number, tx: number, ty: number, depth = 0) =>
      this.add.image(tx * T + 8, ty * T + 8, key, frame).setDepth(depth);

    // floor
    for (let y = 2; y < def.h; y++) {
      for (let x = 0; x < def.w; x++) {
        put("ts-floor-wooden", 0, x, y, 0);
      }
    }
    // back wall: cap row + two brick-face rows
    for (let x = 0; x < def.w; x++) {
      const capF = x === 0 ? WALL.capTL : x === def.w - 1 ? WALL.capTR : WALL.capT;
      const topF = x === 0 ? WALL.faceTL : x === def.w - 1 ? WALL.faceTR : WALL.faceT;
      const botF = x === 0 ? WALL.faceBL : x === def.w - 1 ? WALL.faceBR : WALL.faceB;
      put(wallKey, capF, x, 0, 1);
      put(wallKey, topF, x, 1, 1);
      put(wallKey, botF, x, 2, 1);
      this.collide[0][x] = this.collide[1][x] = this.collide[2][x] = true;
    }
    // side walls
    for (let y = 3; y < def.h - 1; y++) {
      put(wallKey, WALL.sideL, 0, y, 1);
      put(wallKey, WALL.sideR, def.w - 1, y, 1);
      this.collide[y][0] = this.collide[y][def.w - 1] = true;
    }
    // bottom wall with a two-tile door gap (one tile was fiddly to thread)
    const gap = (x: number) => x === def.exitX || x === def.exitX + 1;
    for (let x = 0; x < def.w; x++) {
      if (gap(x)) continue;
      const f = x === 0 ? WALL.botL : x === def.w - 1 ? WALL.botR : WALL.botT;
      put(wallKey, f, x, def.h - 1, (def.h - 1) * T + 8);
      this.collide[def.h - 1][x] = true;
    }
    // door mats across the gap
    for (const x of [def.exitX, def.exitX + 1]) {
      this.add.image(x * T + 8, (def.h - 1) * T + 8, "decor-door", 0)
        .setDepth(2).setAlpha(0.95);
    }
  }

  private buildFixtures(): void {
    for (const f of this.def.fixtures) {
      const img = this.add.image(f.tx * T + 8, (f.ty + 1) * T, f.key, f.frame);
      img.setOrigin(0.5, 1);
      img.setDepth(f.flat ? 2 : (f.ty + 1) * T);
      const solid = f.solid !== false && !f.flat;
      if (solid) {
        const wTiles = Math.max(1, Math.round(img.width / T));
        const x0 = f.tx - Math.floor((wTiles - 1) / 2);
        for (let x = x0; x < x0 + wTiles; x++) {
          if (this.collide[f.ty]?.[x] !== undefined) this.collide[f.ty][x] = true;
        }
      }
      if (f.interact) {
        this.interactables.push({
          tx: f.tx, ty: f.ty,
          labelZh: f.interact.labelZh,
          panel: f.interact.panel,
          action: f.interact.action,
        });
      }
    }
  }

  private buildResidents(): void {
    for (const id of this.enterData.residents) {
      const station = this.def.stations[id];
      const def = AGENTS.find((a) => a.id === id);
      if (!station || !def) continue;
      this.add.ellipse(station.tx * T + 8, station.ty * T + 20, 16, 6, 0x1c140e, 0.3).setDepth(2.5);
      const s = this.add.sprite(station.tx * T + 8, station.ty * T + 8, def.texture, 0);
      s.setDepth(s.y);
      this.add
        .text(s.x, s.y - 20, def.nameZh, {
          fontFamily: "'Microsoft YaHei', sans-serif",
          fontSize: "7px", color: "#ffffff", stroke: "#3d2b1f", strokeThickness: 3, resolution: 4,
        })
        .setOrigin(0.5, 1).setDepth(10000);
      this.residents.push({ id, sprite: s });
    }
  }

  private isBlocked(px: number, py: number): boolean {
    const tx = Math.floor(px / T);
    const ty = Math.floor(py / T);
    if (tx < 0 || ty < 0 || tx >= this.def.w || ty >= this.def.h) return true;
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
      if (vx === 0 && vy === 0 && touchState.active) {
        vx = touchState.vx;
        vy = touchState.vy;
      }
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
      this.player.setDepth(this.player.y);
      const dir = Math.abs(vx) > Math.abs(vy) ? (vx > 0 ? "right" : "left") : vy > 0 ? "down" : "up";
      this.player.play(`player-walk-${dir}`, true);
      audio.step();
    } else {
      const cur = this.player.anims.currentAnim?.key ?? "player-walk-down";
      this.player.play(`player-idle-${cur.split("-").pop() ?? "down"}`, true);
    }
    this.playerShadow.setPosition(this.player.x, this.player.y + 12);

    // exit through the door: standing on the gap tiles near the threshold
    // is enough — no need to squeeze past the wall row
    const ptx = Math.floor(this.player.x / T);
    if (
      (ptx === this.def.exitX || ptx === this.def.exitX + 1) &&
      this.player.y >= (this.def.h - 1) * T - 2
    ) {
      this.leave();
      return;
    }

    // interaction hint + E
    let hintText = "";
    let target: InteriorScene["interactables"][number] | null = null;
    for (const it of this.interactables) {
      const d = Phaser.Math.Distance.Between(this.player.x, this.player.y, it.tx * T + 8, it.ty * T + 8);
      if (d < T * 1.8) {
        hintText = `按 E ${it.labelZh}`;
        target = it;
        break;
      }
    }
    let npc: { id: string } | null = null;
    if (!target) {
      for (const r of this.residents) {
        const d = Phaser.Math.Distance.Between(this.player.x, this.player.y, r.sprite.x, r.sprite.y);
        if (d < T * 2.2) {
          const a = AGENTS.find((x) => x.id === r.id)!;
          hintText = `按 E 与 ${a.nameZh} 对话`;
          npc = r;
          break;
        }
      }
    }
    if (!hintText) hintText = "走到门口离开";
    if (!this.uiLock) this.hint.setText(hintText);
    else this.hint.setText("");

    const touchE = this.touchInteract;
    this.touchInteract = false;
    if ((Phaser.Input.Keyboard.JustDown(this.wasd.E) || touchE) && !this.uiLock) {
      if (target) {
        if (target.action === "sleep") {
          this.uiLock = true;
          bus.emit("sleep:request", undefined);
        } else if (target.panel) {
          this.uiLock = true;
          audio.page();
          bus.emit("building:enter-panel", { panel: target.panel });
        }
      } else if (npc) {
        this.uiLock = true;
        bus.emit("npc:talk", { agentId: npc.id });
      }
    }
  }

  private leaving = false;
  private touchInteract = false;

  /** the museum renders the player's donations live on its pedestals */
  private buildMuseumExhibits(): void {
    const save = loadSave();
    const ores = save?.museum?.ores ?? [];
    const fish = save?.museum?.fish ?? [];
    const pedestals: [number, number][] = [[2, 3], [5, 3], [9, 3], [12, 3], [2, 8], [12, 8]];
    const KIND_TINT: Record<string, number> = {
      todo: 0x9fd6ff, hack: 0xffd27a, fixme: 0xff9b9b, hotspot: 0xc99bff,
    };
    const exhibits = [
      ...ores.map((o) => ({ kind: "ore" as const, label: o })),
      ...fish.map((f) => ({ kind: "fish" as const, label: f })),
    ].slice(0, pedestals.length);
    exhibits.forEach((ex, i) => {
      const [tx, ty] = pedestals[i];
      const px = tx * T + 8;
      const py = ty * T + 10;
      if (ex.kind === "ore") {
        const m = /^\[(\w+)\]/.exec(ex.label);
        this.add.image(px, py, "prop-ore-node")
          .setOrigin(0.5, 1).setScale(0.55)
          .setTint(KIND_TINT[m?.[1] ?? ""] ?? 0x9fd6ff)
          .setDepth(py + 1);
      } else {
        this.add.text(px, py - 8, "🐟", { fontSize: "10px", resolution: 3 })
          .setOrigin(0.5, 1).setDepth(py + 1);
      }
    });
    const total = ores.length + fish.length;
    this.add.text(11 * T, 3 * T - 6, total > 0 ? `馆藏 ${total} 件` : "虚位以待", {
      fontFamily: "'Microsoft YaHei', sans-serif", fontSize: "8px",
      color: "#e8ddc8", stroke: "#3a3148", strokeThickness: 3, resolution: 3,
    }).setOrigin(0.5, 1).setDepth(20000);
  }

  private leave(): void {
    // update() hits the threshold every frame — without this guard the
    // fade restarts forever and the completion callback never fires
    if (this.leaving) return;
    this.leaving = true;
    audio.door();
    this.cameras.main.fadeOut(260, 26, 20, 35);
    this.time.delayedCall(300, () => {
      this.scene.stop();
      this.scene.wake("town", { returnTx: this.enterData.returnTx, returnTy: this.enterData.returnTy });
    });
  }

}
