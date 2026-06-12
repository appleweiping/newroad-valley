/** Tiny typed event bus bridging Phaser (game world) and React (UI layer). */

export type BusEvents = {
  "npc:talk": { agentId: string; activityZh?: string; activityEn?: string };
  "building:enter": { buildingId: string };
  "building:enter-panel": { panel: string };
  "building:hover": { buildingId: string | null };
  "dialogue:closed": undefined;
  "panel:closed": undefined;
  "clock:tick": { day: number; hour: number; minute: number; season: string };
  "mode:detected": { live: boolean };
  "player:moved": { tx: number; ty: number };
  "toast": { text: string };
  "sleep:request": undefined;
  "sleep:done": { day: number };
  "farm:plant-request": { cell: number };
  "farm:plant-confirm": { cell: number; title: string };
  "ore:collected": { title: string; kind: string; repo: string; file: string };
  "fishing:start": undefined;
  "fishing:result": { quality: number };
  "fish:caught": { text: string; level: string };
  "almanac:open": undefined;
  "ach:unlocked": { name: string };
};

type Handler<T> = (payload: T) => void;

class Bus {
  private handlers = new Map<string, Set<Handler<unknown>>>();

  on<K extends keyof BusEvents>(event: K, fn: Handler<BusEvents[K]>): () => void {
    if (!this.handlers.has(event)) this.handlers.set(event, new Set());
    this.handlers.get(event)!.add(fn as Handler<unknown>);
    return () => this.off(event, fn);
  }

  off<K extends keyof BusEvents>(event: K, fn: Handler<BusEvents[K]>): void {
    this.handlers.get(event)?.delete(fn as Handler<unknown>);
  }

  emit<K extends keyof BusEvents>(event: K, payload: BusEvents[K]): void {
    this.handlers.get(event)?.forEach((fn) => fn(payload));
  }
}

export const bus = new Bus();
