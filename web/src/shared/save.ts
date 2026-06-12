/** Save file in localStorage. Bed = manual save; door transitions autosave. */

import { bus } from "./bus";

export interface DemoCrop {
  cell: number;          // index into farm soil cells
  title: string;
  progress: number;      // 1..4 growth, 5 = harvested/done
  variety: number;       // lpc crop column
  createdDay: number;
}

/** one thing in the bag — produce of the three trades */
export interface InvItem {
  kind: "crop" | "ore" | "fish";
  name: string;
  variety?: number;      // lpc product column for crops
}

export interface SaveData {
  version: 3;
  day: number;
  clockMin: number;
  px: number;
  py: number;
  harvested: number;
  demoCrops: DemoCrop[];
  lang: "zh" | "en";
  /** v5 almanac: collected tech-debt ore titles */
  ores: string[];
  /** v5 almanac: caught log-fish texts */
  fish: string[];
  /** v5 achievements unlocked (id -> true) */
  ach: Record<string, boolean>;
  /** build points earned (the town's currency) */
  points: number;
  /** v8: the bag */
  inventory: InvItem[];
  /** v8: items waiting in the shipping bin (paid out next morning) */
  pendingShip: InvItem[];
  /** v8: stamina 0..100 */
  stamina: number;
  /** v8: watering can level (II waters 3 cells) */
  canLevel: 1 | 2;
  /** v8: museum donations */
  museum: { ores: string[]; fish: string[] };
  /** v8: purchased decorations placed in town */
  decor: { id: string; tx: number; ty: number }[];
  /** v9: onboarding progress (1..5, 99 = done) */
  tutorialStep: number;
  /** v10: friendship hearts per resident (0..10) */
  hearts: Record<string, number>;
  /** v10: last game-day a talk credited hearts, per resident */
  heartsDay: Record<string, number>;
}

const KEY = "nrv-save-v1";

const DEFAULTS = {
  ores: [] as string[],
  fish: [] as string[],
  ach: {} as Record<string, boolean>,
  points: 0,
  inventory: [] as InvItem[],
  pendingShip: [] as InvItem[],
  stamina: 100,
  canLevel: 1 as const,
  museum: { ores: [] as string[], fish: [] as string[] },
  decor: [] as { id: string; tx: number; ty: number }[],
  tutorialStep: 1,
  hearts: {} as Record<string, number>,
  heartsDay: {} as Record<string, number>,
};

export function loadSave(): SaveData | null {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return null;
    const d = JSON.parse(raw) as Partial<SaveData> & { version?: number };
    const v: number = d.version ?? 0;
    if (v < 1 || v > 3) return null;
    return { ...DEFAULTS, ...d, version: 3 } as SaveData;
  } catch {
    return null;
  }
}

export function writeSave(d: SaveData): void {
  try {
    localStorage.setItem(KEY, JSON.stringify(d));
  } catch {
    /* storage full/denied — ignore */
  }
}

// ---------------------------------------------------------------- stamina
/** Stamina lives on the save so every scene shares one pool.
 * Returns false (and toasts) when too tired to act. */
export function spendStamina(n: number): boolean {
  const s = loadSave();
  const cur = s?.stamina ?? 100;
  if (cur <= 0) {
    bus.emit("toast", { text: "😴 太累了……回床上睡一觉吧" });
    return false;
  }
  const next = Math.max(0, cur - n);
  if (s) {
    s.stamina = next;
    writeSave(s);
  }
  bus.emit("stamina:changed", { value: next });
  return true;
}

export function restoreStamina(value = 100): void {
  const s = loadSave();
  if (s) {
    s.stamina = value;
    writeSave(s);
  }
  bus.emit("stamina:changed", { value });
}

export function currentStamina(): number {
  return loadSave()?.stamina ?? 100;
}
