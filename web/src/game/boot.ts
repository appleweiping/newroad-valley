import Phaser from "phaser";
import { createRoot } from "react-dom/client";
import { createElement } from "react";
import { BootScene } from "./scenes/BootScene";
import { TownScene } from "./scenes/TownScene";
import { InteriorScene } from "./scenes/InteriorScene";
import { MineScene } from "./scenes/MineScene";
import { audio } from "./audio";
import { maybeRunV4Test } from "./v4test";
import { GameUI } from "@/ui/GameUI";

window.addEventListener("error", (e) => {
  (window as unknown as Record<string, unknown>).__lastError = `${e.message} @ ${e.filename}:${e.lineno}`;
});
// async deaths (e.g. inside the e2e harness) are otherwise invisible
window.addEventListener("unhandledrejection", (e) => {
  (window as unknown as Record<string, unknown>).__lastRejection = String(e.reason);
});

const game = new Phaser.Game({
  type: Phaser.AUTO,
  parent: "game-root",
  backgroundColor: "#2a3f54",
  pixelArt: true,
  roundPixels: true,
  scale: {
    mode: Phaser.Scale.RESIZE,
    autoCenter: Phaser.Scale.CENTER_BOTH,
  },
  // one batch for the whole manifest: the default batch-of-32 scheduler has
  // stalled between batches in embedded/headless browsers (32/64 frozen,
  // zero inflight) — a single large batch sidesteps that path entirely
  loader: { maxParallelDownloads: 128 },
  physics: { default: "arcade" },
  scene: [BootScene, TownScene, InteriorScene, MineScene],
});

(window as unknown as Record<string, unknown>).__game = game;
audio.attach(game);
if (audio.muted) game.sound.mute = true;
audio.applySavedVolume();
void maybeRunV4Test();

// PWA: production only — a dev service worker would fight vite's HMR
if ("serviceWorker" in navigator && import.meta.env.PROD) {
  void navigator.serviceWorker.register("/sw.js");
}

createRoot(document.getElementById("ui-root")!).render(createElement(GameUI));
