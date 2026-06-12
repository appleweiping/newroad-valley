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
import { touchState } from "@/shared/touch";

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

  // --- v6: virtual joystick drives the player ---------------------------------
  const px0 = (t as unknown as { player: { x: number } }).player.x;
  touchState.active = true;
  touchState.vx = 1;
  touchState.vy = 0;
  await sleep(700);
  touchState.active = false;
  touchState.vx = 0;
  await sleep(200);
  const px1 = (t as unknown as { player: { x: number } }).player.x;
  await report("touch-sim", { moved: Math.round(px1 - px0), ok: px1 - px0 > 8 });

  // --- v6: a multi-agent signal sends an NPC to the notice board ---------------
  const tAny = t as unknown as {
    onSignals(s: { id: string; from: string; to: string; summary: string }[]): void;
    npcs: { def: { id: string }; state: string }[];
  };
  tAny.onSignals([{ id: "v6-test-sig", from: "cc", to: "haiku", summary: "哨兵测试信号：请到公告板集合" }]);
  await sleep(900);
  const haiku = tAny.npcs.find((n) => n.def.id === "haiku");
  await report("signal-npc", { haikuState: haiku?.state ?? "?", reacted: haiku?.state === "path" }, true);

  // --- v6: pwa artifacts served ------------------------------------------------
  let manifestOk = false;
  let swOk = false;
  try { manifestOk = (await fetch("/manifest.webmanifest")).ok; } catch { /* absent */ }
  try { swOk = (await fetch("/sw.js")).ok; } catch { /* absent */ }
  await report("pwa", { manifestOk, swOk });

  // --- v6: spectate flag isolates a read-only view ------------------------------
  const frame = document.createElement("iframe");
  frame.style.cssText = "position:absolute;left:-9999px;width:480px;height:320px;";
  frame.src = "/play.html?spectate=1";
  document.body.appendChild(frame);
  let spectateFlag = false;
  for (let i = 0; i < 28; i++) {
    await sleep(500);
    try {
      const flags = (frame.contentWindow as unknown as { __flags?: { spectate?: boolean } })?.__flags;
      if (flags?.spectate === true) { spectateFlag = true; break; }
    } catch { /* cross-origin can't happen, same origin */ }
  }
  frame.remove();
  await report("spectate", { flag: spectateFlag });

  // --- v7: heartbeat reactions (memory growth + new commit) --------------------
  const tPulse = t as unknown as {
    onPulse(d: { memoryCount: number; commits: { repo: string; hash: string; msg: string }[] }): void;
    pulsePrimed: boolean;
    lastMemoryCount: number;
  };
  tPulse.onPulse({ memoryCount: 100, commits: [{ repo: "test-repo", hash: "aaa1111", msg: "baseline" }] });
  await sleep(300);
  tPulse.onPulse({ memoryCount: 101, commits: [{ repo: "test-repo", hash: "bbb2222", msg: "feat: 哨兵提交" }] });
  await sleep(800);
  await report("pulse-react", {
    primed: tPulse.pulsePrimed,
    memoryCount: tPulse.lastMemoryCount,
    ok: tPulse.lastMemoryCount === 101,
  }, true);

  // --- v7: weather drives visuals + auto-watering ------------------------------
  const tw = t as unknown as { setWeather(w: string): void; weather: string; rain: unknown };
  tw.setWeather("rain");
  await sleep(700);
  await report("weather", { weather: tw.weather, rainEmitter: !!tw.rain, ok: tw.weather === "rain" && !!tw.rain }, true);
  tw.setWeather("sunny");

  // --- v7: two residents stop for a chat ---------------------------------------
  const tc = t as unknown as {
    chitchat(a: unknown, b: unknown): void;
    npcs: { def: { id: string }; state: string; sprite: { visible: boolean } }[];
    bubbles: unknown[];
  };
  const pair = tc.npcs.filter((n) => n.sprite.visible).slice(0, 2);
  let chatOk = false;
  if (pair.length === 2) {
    tc.chitchat(pair[0], pair[1]);
    await sleep(900);
    chatOk = pair[0].state === "talk" && tc.bubbles.length > 0;
    await sleep(4200); // let them finish so later steps see idle npcs
  }
  await report("chitchat", { ok: chatOk, pair: pair.map((p) => p.def.id) }, true);

  // --- v7: take a quest via the dialogue ---------------------------------------
  const cropsBefore = t.crops.size;
  bus.emit("quest:take", { agentId: "sonnet" });
  await sleep(1500);
  await report("quest-take", {
    before: cropsBefore,
    after: t.crops.size,
    ok: t.crops.size > cropsBefore,
  }, true);

  // --- v8: the day's work filled the bag and drained stamina -------------------
  const save8 = JSON.parse(localStorage.getItem("nrv-save-v1") ?? "{}") as {
    inventory?: unknown[]; stamina?: number;
  };
  await report("inventory", {
    count: save8.inventory?.length ?? 0,
    stamina: save8.stamina ?? -1,
    ok: (save8.inventory?.length ?? 0) >= 1 && (save8.stamina ?? 100) < 100,
  });

  // --- v8: ship everything, settle, points grow ---------------------------------
  const t8 = t as unknown as {
    points: number;
    settleShipping(): void;
    donate(k: "ore" | "fish", i: number): void;
  };
  const pointsBefore = t8.points;
  bus.emit("ship:all", undefined);
  await sleep(400);
  t8.settleShipping();
  await sleep(400);
  await report("shipping", { before: pointsBefore, after: t8.points, ok: t8.points > pointsBefore }, true);

  // --- v8: shop — watering can II + a plaza lamp ---------------------------------
  t8.points += 50; // test budget
  bus.emit("shop:buy", { itemId: "can2" });
  await sleep(300);
  bus.emit("shop:buy", { itemId: "lamp" });
  await sleep(500);
  const save8b = JSON.parse(localStorage.getItem("nrv-save-v1") ?? "{}") as { canLevel?: number; decor?: unknown[] };
  await report("shop", {
    canLevel: save8b.canLevel ?? 1,
    decor: save8b.decor?.length ?? 0,
    ok: (save8b.canLevel ?? 1) === 2 && (save8b.decor?.length ?? 0) >= 1,
  }, true);

  // --- v8: museum donation --------------------------------------------------------
  t8.donate("ore", 0);
  await sleep(400);
  const save8c = JSON.parse(localStorage.getItem("nrv-save-v1") ?? "{}") as { museum?: { ores?: string[] } };
  await report("museum", { ores: save8c.museum?.ores?.length ?? 0, ok: (save8c.museum?.ores?.length ?? 0) >= 1 });

  // --- v9: onboarding chain completes with the welcome gift ---------------------
  const t9 = t as unknown as { tutorialHook(e: string): void; tutorialStep: number; points: number };
  const p9 = t9.points;
  for (const evt of ["talk-fable", "plant", "library", "ore", "talk-fable"]) t9.tutorialHook(evt);
  await sleep(600);
  await report("tutorial", {
    step: t9.tutorialStep,
    gift: t9.points - p9,
    ok: t9.tutorialStep === 99 && t9.points - p9 === 10,
  }, true);

  // --- v9: settings drive audio volume + camera zoom -----------------------------
  const { audio: audioMod } = await import("@/game/audio");
  audioMod.setVolume(0.5);
  bus.emit("settings:zoom", { zoom: 2 });
  await sleep(400);
  const zoom9 = (t as unknown as { cameras: { main: { zoom: number } } }).cameras.main.zoom;
  await report("settings", {
    volume: audioMod.volume,
    persisted: localStorage.getItem("nrv-volume"),
    zoom: zoom9,
    ok: Math.abs(audioMod.volume - 0.5) < 0.01 && zoom9 === 2,
  }, true);
  bus.emit("settings:zoom", { zoom: 3 });
  audioMod.setVolume(1);

  // --- v10: the museum renders donations on its pedestals -----------------------
  (t as unknown as { enterBuilding(id: string): void }).enterBuilding("museum");
  await sleep(2600);
  const museumScene = game5.scene.getScene("interior") as
    | (Phaser.Scene & { leave?: () => void; def?: { id: string } })
    | null;
  await report("museum-interior", {
    active: !!museumScene?.scene.isActive(),
    room: museumScene?.def?.id ?? "?",
    ok: !!museumScene?.scene.isActive() && museumScene?.def?.id === "museum",
  }, true);
  museumScene?.leave?.();
  await sleep(2400);

  // --- v10: the chronicle aggregates real history --------------------------------
  let chron: { entries?: unknown[] } = {};
  try { chron = await (await fetch(`${BASE}/api/town/chronicle`)).json(); } catch { /* bridge down */ }
  if (!chron.entries) {
    try { chron = await (await fetch("/demo/chronicle.json")).json(); } catch { /* no demo either */ }
  }
  await report("chronicle", { entries: chron.entries?.length ?? 0, ok: (chron.entries?.length ?? 0) >= 5 });

  // --- v10: hearts grow with talks and quests -------------------------------------
  const tH = t as unknown as { bumpHearts(id: string, k: string): void };
  tH.bumpHearts("sonnet", "talk");
  tH.bumpHearts("sonnet", "harvest");
  await sleep(400);
  const save10 = JSON.parse(localStorage.getItem("nrv-save-v1") ?? "{}") as { hearts?: Record<string, number> };
  await report("hearts", { sonnet: save10.hearts?.sonnet ?? 0, ok: (save10.hearts?.sonnet ?? 0) >= 3 });

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
