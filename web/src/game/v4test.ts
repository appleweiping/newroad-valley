/** In-page E2E smoke harness (?v4test=1).
 *
 * Drives a full v4 feature pass inside the running game and streams every
 * step (JSON + canvas screenshots) to the local bridge, which persists them
 * under workspace/v4-report.jsonl + workspace/v4-shots/. Verification thus
 * survives flaky browser tooling — evidence lands on disk step by step.
 * Dev/owner tool: it only ever talks to 127.0.0.1.
 */
import type Phaser from "phaser";
import { bus } from "@/shared/bus";

const BASE = "http://127.0.0.1:8000";

interface TownLike extends Phaser.Scene {
  clockMin: number;
  npcs: { def: { id: string }; state: string; insideBuilding: string | null }[];
  crops: Map<number, { cell: number; title: string; progress: number; taskId?: string }>;
  enterBuilding(id: string): void;
  plantCrop(cell: number, title: string): Promise<void>;
  waterCrop(c: unknown): Promise<void>;
  harvestCrop(c: unknown): Promise<void>;
  lookAt(tx: number, ty: number, zoom?: number): void;
}

function sleep(ms: number): Promise<void> {
  return new Promise((r) => setTimeout(r, ms));
}

async function report(step: string, data: unknown, withShot = false): Promise<void> {
  let image: string | undefined;
  if (withShot) {
    image = await shot();
  }
  try {
    await fetch(`${BASE}/api/town/test-report`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ step, data, image }),
    });
  } catch {
    /* bridge down — nothing to persist to */
  }
}

function shot(): Promise<string | undefined> {
  return new Promise((resolve) => {
    const game = (window as unknown as { __game?: Phaser.Game }).__game;
    if (!game) return resolve(undefined);
    try {
      game.renderer.snapshot((img) => {
        resolve((img as HTMLImageElement).src);
      });
    } catch {
      resolve(undefined);
    }
  });
}

function town(): TownLike | null {
  return ((window as unknown as { __town?: TownLike }).__town as TownLike) ?? null;
}

export async function maybeRunV4Test(): Promise<void> {
  if (!new URLSearchParams(window.location.search).has("v4test")) return;

  // wait for the town
  for (let i = 0; i < 60 && !town(); i++) await sleep(500);
  const t = town();
  if (!t) {
    void report("boot", { ok: false, error: "town never became ready" });
    return;
  }
  await report("boot", { ok: true, live: document.body.innerText.includes("联机") }, true);

  // --- schedules: jump to work hours, watch residents head inside ----------
  t.clockMin = 9 * 60 + 58;
  await sleep(9000);
  await report(
    "schedules",
    t.npcs.map((n) => `${n.def.id}:${n.state}${n.insideBuilding ? "@" + n.insideBuilding : ""}`),
    true,
  );

  // --- interior: enter the library, look around, leave ---------------------
  t.enterBuilding("memory-library");
  await sleep(4000);
  const interior = (window as unknown as { __game: Phaser.Game }).__game.scene.getScene("interior") as
    | (Phaser.Scene & { residents?: { id: string }[]; leave?: () => void })
    | null;
  await report(
    "interior-library",
    {
      active: !!interior?.scene.isActive(),
      residents: interior?.residents?.map((r) => r.id) ?? [],
    },
    true,
  );
  // walk out through the door using the game's own click-to-walk channel —
  // this exercises the doorway geometry + exit threshold end to end
  if (interior) {
    const idef = (interior as unknown as { def: { exitX: number; h: number } }).def;
    // a plain {x,y} satisfies the distance math the walker uses
    (interior as unknown as { moveTarget: { x: number; y: number } | null }).moveTarget = {
      x: idef.exitX * 16 + 16,
      y: idef.h * 16,
    };
  }
  await sleep(3500);
  const idbg = interior as unknown as {
    def?: { exitX: number; h: number };
    player?: { x: number; y: number };
    collide?: boolean[][];
    uiLock?: boolean;
    moveTarget?: unknown;
    leave?: () => void;
  } | null;
  await report("interior-exit-via-door", {
    townActive: t.scene.isActive(),
    interiorActive: !!interior?.scene.isActive(),
    debug: idbg?.def && idbg.player ? {
      py: Math.round(idbg.player.y),
      px: Math.round(idbg.player.x),
      ptx: Math.floor(idbg.player.x / 16),
      exitX: idbg.def.exitX,
      threshold: (idbg.def.h - 1) * 16 - 2,
      uiLock: idbg.uiLock,
      moveTargetLeft: idbg.moveTarget != null,
      bottomRow: idbg.collide?.[idbg.def.h - 1]?.map((b) => (b ? 1 : 0)).join(""),
    } : null,
  }, true);
  // fallback so the rest of the suite still runs if the walk missed
  if (interior?.scene.isActive()) {
    idbg?.leave?.();
    await sleep(2200);
    await report("interior-exit-fallback", { townActive: t.scene.isActive() });
  }

  // --- farm: plant -> water x3 -> harvest (live mode writes the ledger) ----
  t.lookAt(12, 37, 3);
  const cell = 0;
  await (t as unknown as { plantCrop(c: number, s: string): Promise<void> }).plantCrop(cell, "v4 验收作物");
  await sleep(1200);
  await report("farm-plant", { crop: snap(t, cell) }, true);
  for (let i = 0; i < 3; i++) {
    const c = t.crops.get(cell);
    if (c) await (t as unknown as { waterCrop(c: unknown): Promise<void> }).waterCrop(c);
    await sleep(700);
  }
  await report("farm-watered", { crop: snap(t, cell) }, true);
  const mature = t.crops.get(cell);
  if (mature) await (t as unknown as { harvestCrop(c: unknown): Promise<void> }).harvestCrop(mature);
  await sleep(1200);
  await report("farm-harvest", { remaining: snap(t, cell) }, true);

  // --- v5: the tech-debt mines ----------------------------------------------
  (t as unknown as { enterMine(): void }).enterMine();
  await sleep(4200);
  const game5 = (window as unknown as { __game: Phaser.Game }).__game;
  const mine = game5.scene.getScene("mine") as
    | (Phaser.Scene & {
        nodes?: { collected: boolean; ore: { title: string } }[];
        hitNode?: (n: unknown) => void;
        leave?: () => void;
      })
    | null;
  // ore arrives async (bridge /debt may be mid-scan) — wait for the real outcome
  for (let i = 0; i < 24 && (mine?.nodes?.length ?? 0) === 0; i++) await sleep(500);
  await report("mine-enter", {
    active: !!mine?.scene.isActive(),
    nodes: mine?.nodes?.length ?? 0,
  }, true);
  const node = mine?.nodes?.[0];
  if (mine?.hitNode && node) {
    mine.hitNode(node);
    mine.hitNode(node);
    mine.hitNode(node);
  }
  await sleep(1200);
  const saveAfterDig = JSON.parse(localStorage.getItem("nrv-save-v1") ?? "{}") as { ores?: string[] };
  await report("mine-dig", {
    collected: node?.collected ?? false,
    oreTitle: node?.ore.title ?? null,
    oresInSave: saveAfterDig.ores?.length ?? 0,
  }, true);
  mine?.leave?.();
  await sleep(2600);
  await report("mine-exit", { townActive: t.scene.isActive() });

  // --- v5: fishing (resolve through the result channel) ----------------------
  bus.emit("fishing:result", { quality: 2 });
  await sleep(1600);
  const saveAfterFish = JSON.parse(localStorage.getItem("nrv-save-v1") ?? "{}") as { fish?: string[]; ach?: Record<string, boolean> };
  await report("fish-catch", {
    fishInSave: saveAfterFish.fish?.length ?? 0,
    lastFish: saveAfterFish.fish?.slice(-1)[0] ?? null,
    achievements: Object.keys(saveAfterFish.ach ?? {}),
  });

  // --- v5: season change ------------------------------------------------------
  (t as unknown as { day: number }).day = 8; // week 2 = summer
  await sleep(1500);
  await report("season", {
    season: (t as unknown as { currentSeason: string }).currentSeason,
  }, true);

  // --- dialogue bridge ------------------------------------------------------
  let reply = "";
  try {
    const r = await fetch(`${BASE}/api/town/dialogue`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ agentId: "sonnet", message: "记忆图书馆最近有什么新书？" }),
    });
    reply = String((await r.json()).reply ?? "");
  } catch (e) {
    reply = `ERR ${String(e)}`;
  }
  await report("dialogue", { reply });

  // --- audio + save ----------------------------------------------------------
  const game = (window as unknown as { __game: Phaser.Game }).__game;
  await report("audio-save", {
    bgmCached: game.cache.audio.exists("audio-bgm"),
    sfxCached: game.cache.audio.exists("audio-harvest"),
    saveExists: !!localStorage.getItem("nrv-save-v1"),
  });

  await report("done", { ok: true });
  document.title = "V4TEST-DONE";
}

function snap(t: TownLike, cell: number): unknown {
  const c = t.crops.get(cell);
  return c ? { title: c.title, progress: c.progress, taskId: c.taskId ?? null } : null;
}
