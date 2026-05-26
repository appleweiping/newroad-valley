import type {
  SourcedData,
  TownAgentState,
  TownMemorySummary,
  TownSkillSummary,
  TownResourceSummary,
  TownKnowledgeSummary,
  TownHealthStatus,
  TownEvent,
} from '../pixelTownTypes';
import {
  MOCK_AGENTS,
  MOCK_MEMORY_SUMMARY,
  MOCK_SKILL_SUMMARY,
  MOCK_RESOURCE_SUMMARY,
  MOCK_KNOWLEDGE_SUMMARY,
  MOCK_HEALTH,
  MOCK_EVENTS,
} from '../pixelTownMockData';

const API_BASE = '/api/town';

async function fetchSafe<T>(url: string): Promise<T | null> {
  try {
    const res = await fetch(url);
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

function mapAgentFromApi(raw: any): TownAgentState {
  return {
    id: raw.id,
    name: raw.name,
    role: raw.role,
    personality: raw.personality ?? '',
    spriteId: raw.sprite_key ?? `agent_${raw.id}`,
    homeAreaId: raw.home_zone ?? 'agent_homes',
    currentAreaId: raw.zone ?? 'plaza',
    position: raw.position ?? [0, 0],
    targetPosition: raw.target_position ?? null,
    activity: raw.current_activity ?? 'idle',
    status: raw.real_status ? 'online' : 'online',
    mood: raw.mood ?? 'content',
    memorySummary: null,
    skillSummary: null,
    resourceSummary: null,
    relationshipSummary: null,
    lastEventAt: null,
    source: 'adapter',
  };
}

export async function getTownAgents(): Promise<SourcedData<TownAgentState[]>> {
  const data = await fetchSafe<any[]>(`${API_BASE}/agents`);
  if (data && Array.isArray(data)) {
    return {
      data: data.map(mapAgentFromApi),
      source: 'adapter',
      updatedAt: new Date().toISOString(),
    };
  }
  return {
    data: MOCK_AGENTS,
    source: 'mock',
    updatedAt: new Date().toISOString(),
    reason: 'Backend unavailable, using mock data',
  };
}

export async function getTownAgentById(id: string): Promise<SourcedData<TownAgentState | null>> {
  const data = await fetchSafe<any>(`${API_BASE}/agents/${id}`);
  if (data) {
    return {
      data: mapAgentFromApi(data),
      source: 'adapter',
      updatedAt: new Date().toISOString(),
    };
  }
  const mock = MOCK_AGENTS.find(a => a.id === id) ?? null;
  return {
    data: mock,
    source: mock ? 'mock' : 'unavailable',
    updatedAt: new Date().toISOString(),
    reason: mock ? 'Using mock fallback' : 'Agent not found',
  };
}

export async function getTownMemorySummary(): Promise<SourcedData<TownMemorySummary>> {
  const data = await fetchSafe<any>(`${API_BASE}/memory`);
  if (data && data.source === 'adapter') {
    const am = data.agentmemory || {};
    const sm = data.shared_memory || {};
    return {
      data: {
        totalMemories: (am.total_count || 0) + (sm.decisions?.length || 0) + (sm.facts?.length || 0),
        recentCount: am.recent?.length || 0,
        topConcepts: am.top_concepts || [],
        lastUpdated: am.recent?.[0]?.createdAt || null,
        // Extended real data
        typeCounts: am.type_counts || {},
        recentMemories: am.recent || [],
        decisions: sm.decisions || [],
        facts: sm.facts || [],
        indexPreview: sm.index_preview || '',
      },
      source: 'adapter',
      updatedAt: new Date().toISOString(),
    };
  }
  return {
    data: MOCK_MEMORY_SUMMARY,
    source: 'mock',
    updatedAt: new Date().toISOString(),
    reason: 'Memory service unavailable',
  };
}

export async function getTownSkillSummary(): Promise<SourcedData<TownSkillSummary>> {
  const data = await fetchSafe<any>(`${API_BASE}/skills`);
  if (data && data.source === 'adapter') {
    return {
      data: {
        totalSkills: data.total_count || 0,
        recentlyUsed: [],
        categories: (data.categories || []).map((c: any) => c.name || c),
        // Extended real data
        fullCategories: data.categories || [],
      },
      source: 'adapter',
      updatedAt: new Date().toISOString(),
    };
  }
  return {
    data: MOCK_SKILL_SUMMARY,
    source: 'mock',
    updatedAt: new Date().toISOString(),
    reason: 'Skill service unavailable',
  };
}

export async function getTownResourceSummary(): Promise<SourcedData<TownResourceSummary>> {
  const data = await fetchSafe<any>(`${API_BASE}/devtools`);
  if (data && data.source === 'adapter') {
    return {
      data: {
        tokenBudget: null,
        tokensUsed: null,
        toolCount: data.tools?.length || 0,
        activeTools: data.tools || [],
        // Extended real data
        agentHubStatus: data.agent_hub_status || {},
        pendingMessages: data.pending_messages || 0,
      },
      source: 'adapter',
      updatedAt: new Date().toISOString(),
    };
  }
  return {
    data: MOCK_RESOURCE_SUMMARY,
    source: 'mock',
    updatedAt: new Date().toISOString(),
    reason: 'Resource service unavailable',
  };
}

export async function getTownKnowledgeSummary(): Promise<SourcedData<TownKnowledgeSummary>> {
  const data = await fetchSafe<any>(`${API_BASE}/knowledge`);
  if (data && data.source === 'adapter') {
    return {
      data: {
        totalEntries: (data.page_count || 0) + (data.memory_count || 0),
        domains: (data.recent_pages || []).map((p: any) => p.name || ''),
        lastIndexed: null,
        // Extended real data
        pageCount: data.page_count || 0,
        memoryCount: data.memory_count || 0,
        recentPages: data.recent_pages || [],
      },
      source: 'adapter',
      updatedAt: new Date().toISOString(),
    };
  }
  return {
    data: MOCK_KNOWLEDGE_SUMMARY,
    source: 'mock',
    updatedAt: new Date().toISOString(),
    reason: 'Knowledge service unavailable',
  };
}

export async function getTownEvents(): Promise<SourcedData<TownEvent[]>> {
  const data = await fetchSafe<any[]>(`${API_BASE}/events`);
  if (data && Array.isArray(data)) {
    return {
      data: data.map(e => ({
        id: e.id,
        timestamp: e.timestamp,
        agentId: e.agent_id ?? e.agentId,
        eventType: e.event_type ?? e.eventType ?? 'activity',
        description: e.description,
        zone: e.zone,
      })),
      source: 'adapter',
      updatedAt: new Date().toISOString(),
    };
  }
  return {
    data: MOCK_EVENTS,
    source: 'mock',
    updatedAt: new Date().toISOString(),
    reason: 'Event service unavailable',
  };
}

export async function getTownHealth(): Promise<SourcedData<TownHealthStatus>> {
  const data = await fetchSafe<any>(`${API_BASE}/health`);
  if (data && data.status === 'ok') {
    return {
      data: {
        overall: 'healthy',
        memory: 'connected',
        skills: 'connected',
        resources: 'connected',
        knowledge: 'connected',
        agentHub: 'connected',
      },
      source: 'adapter',
      updatedAt: new Date().toISOString(),
    };
  }
  return {
    data: MOCK_HEALTH,
    source: 'mock',
    updatedAt: new Date().toISOString(),
    reason: 'Health check unavailable',
  };
}

export async function getTownAreaStatus(areaId: string): Promise<SourcedData<Record<string, unknown>>> {
  const data = await fetchSafe<any>(`${API_BASE}/state`);
  if (data) {
    const building = data.buildings?.find((b: any) => b.id === areaId || b.zone === areaId);
    if (building) {
      return {
        data: building,
        source: 'adapter',
        updatedAt: new Date().toISOString(),
      };
    }
  }
  return {
    data: { id: areaId, status: 'mock_fallback' },
    source: 'mock',
    updatedAt: new Date().toISOString(),
    reason: 'Area data unavailable',
  };
}
