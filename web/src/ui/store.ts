import { create } from "zustand";

export type Lang = "zh" | "en";

interface UIState {
  lang: Lang;
  live: boolean;
  dialogueAgent: string | null;
  dialogueActivity: { zh: string; en: string } | null;
  dialogueHearts: number;
  openPanel: string | null; // building id
  plantCell: number | null; // farm cell awaiting a task title
  toast: string | null;
  fishing: boolean;
  almanac: boolean;
  almanacTab: string;
  stamina: number;
  settings: boolean;
  clock: { day: number; hour: number; minute: number; season: string; weather?: string };
  setLang(l: Lang): void;
  setLive(v: boolean): void;
  openDialogue(agentId: string, activity?: { zh: string; en: string } | null, hearts?: number): void;
  closeDialogue(): void;
  openBuilding(buildingId: string): void;
  closePanel(): void;
  setClock(c: UIState["clock"]): void;
  setPlantCell(c: number | null): void;
  setToast(t: string | null): void;
  setFishing(v: boolean): void;
  setAlmanac(v: boolean): void;
  setAlmanacTab(t: string): void;
  setStamina(v: number): void;
  setSettings(v: boolean): void;
}

export const useUI = create<UIState>((set) => ({
  lang: "zh",
  live: false,
  dialogueAgent: null,
  dialogueActivity: null,
  dialogueHearts: 0,
  openPanel: null,
  plantCell: null,
  toast: null,
  fishing: false,
  almanac: false,
  almanacTab: "bag",
  stamina: 100,
  settings: false,
  clock: { day: 1, hour: 8, minute: 0, season: "春" },
  setLang: (lang) => set({ lang }),
  setLive: (live) => set({ live }),
  openDialogue: (dialogueAgent, dialogueActivity = null, dialogueHearts = 0) => set({ dialogueAgent, dialogueActivity, dialogueHearts }),
  closeDialogue: () => set({ dialogueAgent: null, dialogueActivity: null }),
  openBuilding: (openPanel) => set({ openPanel }),
  closePanel: () => set({ openPanel: null }),
  setClock: (clock) => set({ clock }),
  setPlantCell: (plantCell) => set({ plantCell }),
  setToast: (toast) => set({ toast }),
  setFishing: (fishing) => set({ fishing }),
  setAlmanac: (almanac) => set({ almanac }),
  setAlmanacTab: (almanacTab) => set({ almanacTab }),
  setStamina: (stamina) => set({ stamina }),
  setSettings: (settings) => set({ settings }),
}));
