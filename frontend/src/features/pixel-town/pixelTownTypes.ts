export type DataSource = 'adapter' | 'mock' | 'unavailable';

export interface SourcedData<T> {
  data: T;
  source: DataSource;
  updatedAt: string;
  reason?: string;
}

export type ActivityState =
  | 'idle' | 'walking' | 'thinking' | 'reading_memory'
  | 'learning_skill' | 'chatting' | 'working' | 'resting'
  | 'exploring' | 'debugging' | 'reporting' | 'dreaming'
  | 'observing' | 'building' | 'reviewing';

export type AgentMood =
  | 'focused' | 'relaxed' | 'excited' | 'tired'
  | 'curious' | 'content' | 'creative' | 'determined';

export interface TownAgentState {
  id: string;
  name: string;
  role: string;
  personality: string;
  spriteId: string;
  homeAreaId: string;
  currentAreaId: string;
  position: [number, number];
  targetPosition: [number, number] | null;
  activity: ActivityState;
  status: 'online' | 'offline' | 'busy' | 'away';
  mood: AgentMood;
  memorySummary: string | null;
  skillSummary: string | null;
  resourceSummary: string | null;
  relationshipSummary: string | null;
  lastEventAt: string | null;
  source: DataSource;
  // Future extensions
  riskFlags?: string[];
  dailySchedule?: string;
  dreamState?: string;
}

export interface TownAreaEntity {
  id: string;
  name: string;
  nameCn: string;
  type: 'building' | 'zone' | 'landmark';
  position: { x: number; y: number };
  size: { w: number; h: number };
  visualAnchor: string;
  description: string;
  icon: string;
  adapterSource: string;
  fallbackState: string;
  systemLink: string | null;
  debugMetadata?: Record<string, unknown>;
}

export interface TownEvent {
  id: string;
  timestamp: number;
  agentId: string;
  eventType: string;
  description: string;
  zone: string;
}

export interface TownHealthStatus {
  overall: 'healthy' | 'degraded' | 'offline';
  memory: 'connected' | 'fallback' | 'unavailable';
  skills: 'connected' | 'fallback' | 'unavailable';
  resources: 'connected' | 'fallback' | 'unavailable';
  knowledge: 'connected' | 'fallback' | 'unavailable';
  agentHub: 'connected' | 'fallback' | 'unavailable';
}

export interface TownMemorySummary {
  totalMemories: number;
  recentCount: number;
  topConcepts: string[];
  lastUpdated: string | null;
  // Extended real data
  typeCounts?: Record<string, number>;
  recentMemories?: Array<{ id: string; type: string; title: string; concepts: string[]; createdAt: string }>;
  decisions?: Array<{ name: string; preview: string }>;
  facts?: Array<{ name: string; preview: string }>;
  indexPreview?: string;
}

export interface TownSkillSummary {
  totalSkills: number;
  recentlyUsed: string[];
  categories: string[];
  // Extended real data
  fullCategories?: Array<{ name: string; skills: string[] }>;
}

export interface TownResourceSummary {
  tokenBudget: number | null;
  tokensUsed: number | null;
  toolCount: number;
  activeTools: string[];
  // Extended real data
  agentHubStatus?: Record<string, string>;
  pendingMessages?: number;
}

export interface TownKnowledgeSummary {
  totalEntries: number;
  domains: string[];
  lastIndexed: string | null;
  // Extended real data
  pageCount?: number;
  memoryCount?: number;
  recentPages?: Array<{ name: string; path: string }>;
}

export interface PixelTownConfig {
  debugMode: boolean;
  showGrid: boolean;
  showZoneBounds: boolean;
  showCoordinates: boolean;
  showAdapterSource: boolean;
  animationsEnabled: boolean;
  renderScale: 1 | 2 | 3 | 4;
}

export const DEFAULT_CONFIG: PixelTownConfig = {
  debugMode: false,
  showGrid: false,
  showZoneBounds: false,
  showCoordinates: false,
  showAdapterSource: false,
  animationsEnabled: true,
  renderScale: 2,
};
