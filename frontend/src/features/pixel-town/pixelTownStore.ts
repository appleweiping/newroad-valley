import { create } from 'zustand';
import type {
  TownAgentState,
  TownAreaEntity,
  TownHealthStatus,
  TownMemorySummary,
  TownSkillSummary,
  TownResourceSummary,
  TownKnowledgeSummary,
  TownEvent,
  PixelTownConfig,
  DataSource,
} from './pixelTownTypes';
import { DEFAULT_CONFIG } from './pixelTownTypes';
import { MOCK_AGENTS, MOCK_HEALTH, MOCK_EVENTS } from './pixelTownMockData';

interface PixelTownStore {
  // Connection
  connected: boolean;
  setConnected: (v: boolean) => void;

  // Agents
  agents: TownAgentState[];
  agentsSource: DataSource;
  setAgents: (agents: TownAgentState[], source: DataSource) => void;

  // Selection
  selectedAgent: TownAgentState | null;
  selectedArea: TownAreaEntity | null;
  selectAgent: (agent: TownAgentState | null) => void;
  selectArea: (area: TownAreaEntity | null) => void;
  clearSelection: () => void;

  // Panel
  showPanel: 'agent' | 'building' | 'inspector' | null;

  // Events
  events: TownEvent[];
  eventsSource: DataSource;
  setEvents: (events: TownEvent[], source: DataSource) => void;

  // Summaries
  health: TownHealthStatus;
  memorySummary: TownMemorySummary | null;
  skillSummary: TownSkillSummary | null;
  resourceSummary: TownResourceSummary | null;
  knowledgeSummary: TownKnowledgeSummary | null;
  setHealth: (h: TownHealthStatus) => void;
  setMemorySummary: (s: TownMemorySummary | null) => void;
  setSkillSummary: (s: TownSkillSummary | null) => void;
  setResourceSummary: (s: TownResourceSummary | null) => void;
  setKnowledgeSummary: (s: TownKnowledgeSummary | null) => void;

  // Config
  config: PixelTownConfig;
  toggleDebug: () => void;
  setConfig: (partial: Partial<PixelTownConfig>) => void;

  // Time
  timeOfDay: number;
  tickCount: number;
  setTime: (time: number, tick: number) => void;

  // Legacy compat: accept raw backend state
  setState: (state: any) => void;
}

export const usePixelTownStore = create<PixelTownStore>((set, get) => ({
  connected: false,
  setConnected: (connected) => set({ connected }),

  agents: MOCK_AGENTS,
  agentsSource: 'mock',
  setAgents: (agents, source) => set({ agents, agentsSource: source }),

  selectedAgent: null,
  selectedArea: null,
  selectAgent: (agent) => set({ selectedAgent: agent, selectedArea: null, showPanel: agent ? 'agent' : null }),
  selectArea: (area) => set({ selectedArea: area, selectedAgent: null, showPanel: area ? 'building' : null }),
  clearSelection: () => set({ selectedAgent: null, selectedArea: null, showPanel: null }),

  showPanel: null,

  events: MOCK_EVENTS,
  eventsSource: 'mock',
  setEvents: (events, source) => set({ events, eventsSource: source }),

  health: MOCK_HEALTH,
  memorySummary: null,
  skillSummary: null,
  resourceSummary: null,
  knowledgeSummary: null,
  setHealth: (health) => set({ health }),
  setMemorySummary: (memorySummary) => set({ memorySummary }),
  setSkillSummary: (skillSummary) => set({ skillSummary }),
  setResourceSummary: (resourceSummary) => set({ resourceSummary }),
  setKnowledgeSummary: (knowledgeSummary) => set({ knowledgeSummary }),

  config: DEFAULT_CONFIG,
  toggleDebug: () => set((s) => ({
    config: {
      ...s.config,
      debugMode: !s.config.debugMode,
      showGrid: !s.config.debugMode,
      showZoneBounds: !s.config.debugMode,
    },
  })),
  setConfig: (partial) => set((s) => ({ config: { ...s.config, ...partial } })),

  timeOfDay: 0.5,
  tickCount: 0,
  setTime: (timeOfDay, tickCount) => set({ timeOfDay, tickCount }),

  setState: (state) => {
    if (!state) return;
    const agents: TownAgentState[] = (state.agents ?? []).map((a: any) => ({
      id: a.id,
      name: a.name,
      role: a.role,
      personality: a.personality ?? '',
      spriteId: a.sprite_key ?? `agent_${a.id}`,
      homeAreaId: a.home_zone ?? 'agent_homes',
      currentAreaId: a.zone ?? 'plaza',
      position: a.position ?? [0, 0],
      targetPosition: a.target_position ?? null,
      activity: a.current_activity ?? 'idle',
      status: 'online',
      mood: a.mood ?? 'content',
      memorySummary: null,
      skillSummary: null,
      resourceSummary: null,
      relationshipSummary: null,
      lastEventAt: null,
      source: 'adapter' as DataSource,
    }));
    const events: TownEvent[] = (state.events ?? []).map((e: any) => ({
      id: e.id,
      timestamp: e.timestamp,
      agentId: e.agent_id ?? e.agentId ?? '',
      eventType: e.event_type ?? 'activity',
      description: e.description ?? '',
      zone: e.zone ?? '',
    }));
    set({
      agents,
      agentsSource: 'adapter',
      events,
      eventsSource: 'adapter',
      timeOfDay: state.time_of_day ?? get().timeOfDay,
      tickCount: state.tick_count ?? get().tickCount,
      connected: true,
    });
  },
}));
