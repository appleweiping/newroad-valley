/** Interior room definitions — one data-driven scene renders them all.
 *
 * Coordinates are room-local TILES. Rooms have a 3-row back wall (cap +
 * two brick-face rows); the floor starts at y=3. The exit door sits on the
 * bottom wall. Furniture frames reference the Sprout furniture sheet
 * (decor-furniture, 9 cols) unless a `key` overrides it.
 */

export interface Fixture {
  key: string;
  frame?: number;
  tx: number;
  ty: number;
  /** blocks movement (default true) */
  solid?: boolean;
  /** opens a data panel or triggers an action when interacted */
  interact?: { panel?: string; action?: "save" | "sleep"; labelZh: string; labelEn: string };
  /** draw flat on the floor under everything (rugs) */
  flat?: boolean;
}

export interface InteriorDef {
  id: string;
  buildingId: string;
  nameZh: string;
  nameEn: string;
  w: number;
  h: number;
  /** warm (homes) or cold (civic stone) walls */
  warmWalls: boolean;
  exitX: number;
  fixtures: Fixture[];
  /** where a resident stands when their schedule puts them here */
  stations: Record<string, { tx: number; ty: number }>;
}

const F = "decor-furniture"; // sprout furniture sheet (9 cols)

export const INTERIORS: InteriorDef[] = [
  {
    id: "memory-library",
    buildingId: "memory-library",
    nameZh: "记忆图书馆 · 书架长廊",
    nameEn: "Memory Library · Stacks",
    w: 15, h: 11, warmWalls: true, exitX: 7,
    fixtures: [
      // long wall of bookshelves — the memory stacks
      ...[1, 3, 5, 9, 11, 13].map((tx) => ({
        key: "prop-bookshelf", tx, ty: 3,
        interact: { panel: "memory", labelZh: "翻阅记忆书架", labelEn: "Browse the memory stacks" },
      })),
      { key: F, frame: 51, tx: 7, ty: 6, flat: true, solid: false },
      { key: F, frame: 24, tx: 6, ty: 6 },   // reading table
      { key: F, frame: 22, tx: 5, ty: 6, solid: false },  // chair
      { key: F, frame: 12, tx: 1, ty: 6 },   // green lamp
      { key: F, frame: 13, tx: 13, ty: 6 },  // blue lamp
      { key: F, frame: 32, tx: 9, ty: 3, solid: false },  // wall clock
      { key: F, frame: 3, tx: 2, ty: 8, solid: false },   // potted plant
      { key: F, frame: 5, tx: 12, ty: 8, solid: false },
    ],
    stations: { sonnet: { tx: 5, ty: 5 }, fable: { tx: 9, ty: 6 } },
  },
  {
    id: "skill-workshop",
    buildingId: "skill-workshop",
    nameZh: "技能工坊 · 锻造间",
    nameEn: "Skill Workshop · Forge",
    w: 13, h: 10, warmWalls: false, exitX: 6,
    fixtures: [
      { key: "prop-forge", tx: 2, ty: 3, interact: { panel: "skills", labelZh: "查看锻造配方", labelEn: "Browse forge recipes" } },
      { key: "prop-forge", tx: 10, ty: 3 },
      { key: "prop-kanban", tx: 6, ty: 3, interact: { panel: "skills", labelZh: "查看技能清单", labelEn: "View the skill index" } },
      { key: F, frame: 21, tx: 4, ty: 5 },   // dresser top (tool cabinet)
      { key: F, frame: 30, tx: 4, ty: 6, solid: false },
      { key: F, frame: 25, tx: 8, ty: 6 },   // crate table
      { key: F, frame: 14, tx: 1, ty: 7 },   // pink lamp
      { key: F, frame: 31, tx: 11, ty: 7 },  // stool
    ],
    stations: { pixelcat: { tx: 3, ty: 5 } },
  },
  {
    id: "town-hall",
    buildingId: "town-hall",
    nameZh: "市政厅 · 状态大厅",
    nameEn: "Town Hall · Status Hall",
    w: 17, h: 11, warmWalls: false, exitX: 8,
    fixtures: [
      { key: "prop-status-screen", tx: 8, ty: 3, interact: { panel: "town-hall", labelZh: "查看镇内服务状态", labelEn: "Check town services" } },
      { key: "prop-status-screen", tx: 3, ty: 3, interact: { panel: "code", labelZh: "查看代码工场报告", labelEn: "View repo reports" } },
      { key: "prop-kanban", tx: 13, ty: 3, interact: { panel: "agents", labelZh: "居民登记册", labelEn: "Resident register" } },
      { key: F, frame: 48, tx: 8, ty: 6, flat: true, solid: false }, // wide rug
      { key: F, frame: 24, tx: 5, ty: 7 },
      { key: F, frame: 22, tx: 4, ty: 7, solid: false },
      { key: F, frame: 23, tx: 6, ty: 7, solid: false },
      { key: F, frame: 33, tx: 11, ty: 3, solid: false }, // clock
      { key: F, frame: 4, tx: 1, ty: 8, solid: false },
      { key: F, frame: 4, tx: 15, ty: 8, solid: false },
    ],
    stations: { opus: { tx: 8, ty: 5 }, codex: { tx: 4, ty: 6 } },
  },
  {
    id: "player-house",
    buildingId: "player-house",
    nameZh: "农舍 · 卧室",
    nameEn: "Farmhouse · Bedroom",
    w: 11, h: 9, warmWalls: true, exitX: 5,
    fixtures: [
      { key: F, frame: 19, tx: 2, ty: 3 },
      { key: F, frame: 28, tx: 2, ty: 4, interact: { action: "sleep", labelZh: "睡觉（存档，醒来已是明早）", labelEn: "Sleep (save; wake tomorrow)" } },
      { key: F, frame: 21, tx: 8, ty: 3 },
      { key: F, frame: 30, tx: 8, ty: 4, solid: false },
      { key: F, frame: 46, tx: 5, ty: 5, flat: true, solid: false }, // pink rug
      { key: F, frame: 1, tx: 5, ty: 3, solid: false },   // wall picture
      { key: F, frame: 34, tx: 7, ty: 3, solid: false },  // small clock
      { key: F, frame: 12, tx: 9, ty: 6 },                // lamp
      { key: F, frame: 5, tx: 1, ty: 6, solid: false },   // plant
    ],
    stations: {},
  },
  {
    id: "greenhouse",
    buildingId: "greenhouse",
    nameZh: "温室 · 育苗间",
    nameEn: "Greenhouse · Nursery",
    w: 12, h: 9, warmWalls: true, exitX: 6,
    fixtures: [
      { key: "ts-lpc-crops", frame: 224, tx: 2, ty: 4, solid: false },
      { key: "ts-lpc-crops", frame: 229, tx: 4, ty: 4, solid: false },
      { key: "ts-lpc-crops", frame: 232, tx: 8, ty: 4, solid: false },
      { key: "ts-lpc-crops", frame: 226, tx: 10, ty: 4, solid: false },
      { key: "prop-kanban", tx: 6, ty: 3, interact: { panel: "farm", labelZh: "查看任务苗谱", labelEn: "View the task seedling chart" } },
      { key: F, frame: 4, tx: 1, ty: 6, solid: false },
      { key: F, frame: 5, tx: 10, ty: 6, solid: false },
      { key: F, frame: 3, tx: 6, ty: 6, solid: false },
    ],
    stations: {},
  },
  {
    id: "research-hall",
    buildingId: "research-hall",
    nameZh: "研究大厅 · 看板墙",
    nameEn: "Research Hall · Board Wall",
    w: 15, h: 10, warmWalls: false, exitX: 7,
    fixtures: [
      { key: "prop-kanban", tx: 3, ty: 3, interact: { panel: "research", labelZh: "查看研究看板", labelEn: "Review research boards" } },
      { key: "prop-kanban", tx: 8, ty: 3, interact: { panel: "research", labelZh: "查看研究看板", labelEn: "Review research boards" } },
      { key: "prop-bookshelf", tx: 12, ty: 3, interact: { panel: "wiki", labelZh: "翻阅文献架", labelEn: "Browse the literature shelf" } },
      { key: F, frame: 24, tx: 5, ty: 6 },
      { key: F, frame: 22, tx: 4, ty: 6, solid: false },
      { key: F, frame: 23, tx: 6, ty: 6, solid: false },
      { key: F, frame: 53, tx: 10, ty: 6, flat: true, solid: false },
      { key: F, frame: 13, tx: 1, ty: 7 },
      { key: F, frame: 3, tx: 13, ty: 7, solid: false },
    ],
    stations: { aris: { tx: 4, ty: 5 } },
  },
  {
    id: "museum",
    buildingId: "museum",
    nameZh: "镇立博物馆 · 展厅",
    nameEn: "Town Museum · Exhibit Hall",
    w: 15, h: 11, warmWalls: false, exitX: 7,
    fixtures: [
      // reception desk — donations happen here
      { key: F, frame: 24, tx: 7, ty: 6, interact: { panel: "museum", labelZh: "捐赠与馆藏目录", labelEn: "Donate & browse the catalog" } },
      { key: F, frame: 22, tx: 6, ty: 6, solid: false },
      // pedestal rows along the walls — exhibits render on top (dynamic)
      { key: F, frame: 25, tx: 2, ty: 3 },
      { key: F, frame: 25, tx: 5, ty: 3 },
      { key: F, frame: 25, tx: 9, ty: 3 },
      { key: F, frame: 25, tx: 12, ty: 3 },
      { key: F, frame: 25, tx: 2, ty: 8 },
      { key: F, frame: 25, tx: 12, ty: 8 },
      { key: F, frame: 48, tx: 7, ty: 5, flat: true, solid: false }, // wide rug
      { key: F, frame: 12, tx: 1, ty: 6 },
      { key: F, frame: 13, tx: 13, ty: 6 },
      { key: F, frame: 33, tx: 7, ty: 3, solid: false }, // clock
    ],
    stations: {},
  },
];

export const INTERIOR_BY_BUILDING = new Map(INTERIORS.map((i) => [i.buildingId, i]));
