/** Save file in localStorage. Bed = manual save; door transitions autosave. */

export interface DemoCrop {
  cell: number;          // index into farm soil cells
  title: string;
  progress: number;      // 1..4 growth, 5 = harvested/done
  variety: number;       // lpc crop column
  createdDay: number;
}

export interface SaveData {
  version: 2;
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
  /** build points earned (spent in later versions) */
  points: number;
}

const KEY = "nrv-save-v1";

const DEFAULTS = { ores: [] as string[], fish: [] as string[], ach: {} as Record<string, boolean>, points: 0 };

export function loadSave(): SaveData | null {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return null;
    const d = JSON.parse(raw) as Partial<SaveData> & { version?: number };
    const v: number = d.version ?? 0;
    if (v !== 1 && v !== 2) return null;
    return { ...DEFAULTS, ...d, version: 2 } as SaveData;
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
