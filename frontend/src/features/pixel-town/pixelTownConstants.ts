export const TILE_SIZE = 32;
export const MAP_WIDTH = 40;
export const MAP_HEIGHT = 30;
export const RENDER_SCALE = 2;

export const PALETTE = {
  grass: [0x6aad45, 0x5e9e3d, 0x72b84e, 0x68a843, 0x5c9638],
  grassDark: 0x4e8a32,
  grassBlade: 0x3d7a28,
  grassHighlight: 0x8acc5e,
  grassDew: 0xb8e87a,
  water: { base: 0x3a7ab8, ripple: 0x4a8fc8, sparkle: 0x8ac8e8, deep: 0x2a5a88 },
  path: {
    mortar: 0x8a7a5a,
    stones: [0xb8a888, 0xc4b498, 0xa89878, 0xbcac8c, 0xd0c0a0],
    highlight: 0xe0d4b8,
    shadow: 0x6a5a3a,
  },
  flowers: [0xffdd44, 0xff8866, 0xcc88ff, 0x66ccff, 0xff6699],
  flowersLarge: [0xff6b8a, 0xffb347, 0x87ceeb, 0xdda0dd, 0xffd700],
  tree: { trunk: 0x6b4530, canopy: [0x2d6b1a, 0x3a7a28, 0x4a8a38], highlight: 0x5a9a48 },
  fence: 0x8b5e3c,
  lamp: { post: 0x4a4a4a, light: 0xffe4a0 },
  bench: { seat: 0x8b5e3c, leg: 0x5a3a20 },
  ui: {
    bgDark: 0x1a1a2e,
    bgPanel: 0x16213e,
    accent: 0xe94560,
    textWarm: 0xf8e8d4,
    textPink: 0xffd6df,
    borderAccent: 'rgba(233, 69, 96, 0.3)',
  },
} as const;

export const ZONE_LABELS: Record<string, string> = {
  town_hall: '镇政厅',
  memory_library: '记忆图书馆',
  skill_workshop: '技能工坊',
  dream_garden: '梦境花园',
  devtools_lab: '开发实验室',
  resource_market: '资源市场',
  knowledge_tower: '知识塔',
  agent_homes: '居民住宅',
  plaza: '中央广场',
};

export const ACTIVITY_LABELS: Record<string, string> = {
  idle: '发呆中',
  walking: '散步中',
  thinking: '深度思考',
  reading_memory: '阅读记忆',
  learning_skill: '学习技能',
  chatting: '聊天中',
  working: '工作中',
  resting: '休息中',
  exploring: '探索中',
  debugging: '调试中',
  reporting: '汇报中',
  dreaming: '做梦中',
  observing: '观察中',
  building: '建造中',
  reviewing: '审查中',
};

export const ACTIVITY_ICONS: Record<string, string> = {
  idle: '💤',
  walking: '🚶',
  thinking: '💭',
  reading_memory: '📖',
  learning_skill: '🔧',
  chatting: '💬',
  working: '⚡',
  resting: '😴',
  exploring: '🔍',
  debugging: '🐛',
  reporting: '📋',
  dreaming: '🌙',
  observing: '👁️',
  building: '🏗️',
  reviewing: '📝',
};

export const MOOD_LABELS: Record<string, string> = {
  focused: '🎯 专注',
  relaxed: '😌 放松',
  excited: '✨ 兴奋',
  tired: '😪 疲惫',
  curious: '🤔 好奇',
  content: '😊 满足',
  creative: '🎨 创造',
  determined: '💪 坚定',
};

export const AGENT_COLORS: Record<string, number> = {
  opus: 0x9b59b6,
  pixelcat: 0xf39c12,
  codex: 0x3498db,
  sonnet: 0x2ecc71,
  haiku: 0x1abc9c,
  deepseek: 0x2980b9,
  openhands: 0x8e44ad,
  aris: 0xe74c3c,
  player: 0xff69b4,
};
