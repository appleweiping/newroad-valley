import { useEffect, useState } from 'react';
import { usePixelTownStore } from './pixelTownStore';
import { ACTIVITY_LABELS, MOOD_LABELS, ZONE_LABELS, ACTIVITY_ICONS } from './pixelTownConstants';
import { getTownMemorySummary, getTownSkillSummary, getTownResourceSummary, getTownKnowledgeSummary } from './adapters/townDataAdapter';
import type { DataSource, TownAgentState, TownAreaEntity, TownMemorySummary, TownSkillSummary, TownResourceSummary, TownKnowledgeSummary } from './pixelTownTypes';

function SourceBadge({ source }: { source: DataSource }) {
  return (
    <span className={`pixel-source-badge pixel-source-badge--${source}`}>
      {source === 'adapter' ? '● live' : source === 'mock' ? '◐ mock' : '○ n/a'}
    </span>
  );
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="pixel-inspector-row">
      <span className="pixel-inspector-label">{label}</span>
      <span className="pixel-inspector-value">{value}</span>
    </div>
  );
}

function AgentInspector({ agent }: { agent: TownAgentState }) {
  return (
    <>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
        <span style={{ fontSize: 18 }}>{ACTIVITY_ICONS[agent.activity] || '💤'}</span>
        <div>
          <div style={{ fontSize: 12, fontWeight: 600, color: '#f8e8d4' }}>{agent.name}</div>
          <div style={{ fontSize: 10, color: 'rgba(248,232,212,0.5)' }}>{agent.role}</div>
        </div>
      </div>

      <div style={{ marginBottom: 8 }}>
        <SourceBadge source={agent.source} />
      </div>

      <div style={{ borderTop: '1px solid rgba(233,69,96,0.2)', paddingTop: 8 }}>
        <InfoRow label="状态" value={ACTIVITY_LABELS[agent.activity] || agent.activity} />
        <InfoRow label="心情" value={MOOD_LABELS[agent.mood] || agent.mood} />
        <InfoRow label="位置" value={`${ZONE_LABELS[agent.currentAreaId] || agent.currentAreaId}`} />
        <InfoRow label="坐标" value={`(${agent.position[0]}, ${agent.position[1]})`} />
      </div>

      {agent.memorySummary && (
        <div style={{ borderTop: '1px solid rgba(233,69,96,0.15)', paddingTop: 6, marginTop: 6 }}>
          <div style={{ fontSize: 9, color: 'rgba(248,232,212,0.4)', textTransform: 'uppercase', marginBottom: 4 }}>记忆</div>
          <div style={{ fontSize: 11, color: 'rgba(248,232,212,0.7)' }}>{agent.memorySummary}</div>
        </div>
      )}

      {agent.skillSummary && (
        <div style={{ borderTop: '1px solid rgba(233,69,96,0.15)', paddingTop: 6, marginTop: 6 }}>
          <div style={{ fontSize: 9, color: 'rgba(248,232,212,0.4)', textTransform: 'uppercase', marginBottom: 4 }}>技能</div>
          <div style={{ fontSize: 11, color: 'rgba(248,232,212,0.7)' }}>{agent.skillSummary}</div>
        </div>
      )}

      {agent.resourceSummary && (
        <div style={{ borderTop: '1px solid rgba(233,69,96,0.15)', paddingTop: 6, marginTop: 6 }}>
          <div style={{ fontSize: 9, color: 'rgba(248,232,212,0.4)', textTransform: 'uppercase', marginBottom: 4 }}>资源</div>
          <div style={{ fontSize: 11, color: 'rgba(248,232,212,0.7)' }}>{agent.resourceSummary}</div>
        </div>
      )}

      {agent.relationshipSummary && (
        <div style={{ borderTop: '1px solid rgba(233,69,96,0.15)', paddingTop: 6, marginTop: 6 }}>
          <div style={{ fontSize: 9, color: 'rgba(248,232,212,0.4)', textTransform: 'uppercase', marginBottom: 4 }}>关系</div>
          <div style={{ fontSize: 11, color: 'rgba(248,232,212,0.7)' }}>{agent.relationshipSummary}</div>
        </div>
      )}

      <div style={{ borderTop: '1px solid rgba(233,69,96,0.15)', paddingTop: 6, marginTop: 6 }}>
        <div style={{ fontSize: 9, color: 'rgba(248,232,212,0.4)', textTransform: 'uppercase', marginBottom: 4 }}>性格</div>
        <div style={{ fontSize: 11, color: 'rgba(248,232,212,0.6)', lineHeight: 1.4 }}>{agent.personality}</div>
      </div>
    </>
  );
}

function AreaInspector({ area }: { area: TownAreaEntity }) {
  const [areaData, setAreaData] = useState<any>(null);
  const [dataSource, setDataSource] = useState<DataSource>('mock');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    const fetchData = async () => {
      try {
        let result: any = null;
        if (area.id === 'memory_library') {
          result = await getTownMemorySummary();
        } else if (area.id === 'skill_workshop') {
          result = await getTownSkillSummary();
        } else if (area.id === 'resource_market' || area.id === 'devtools_lab') {
          result = await getTownResourceSummary();
        } else if (area.id === 'knowledge_tower') {
          result = await getTownKnowledgeSummary();
        }
        if (result) {
          setAreaData(result.data);
          setDataSource(result.source);
        }
      } catch {
        setDataSource('unavailable');
      }
      setLoading(false);
    };
    fetchData();
  }, [area.id]);

  return (
    <>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
        <span style={{ fontSize: 18 }}>{area.icon}</span>
        <div>
          <div style={{ fontSize: 12, fontWeight: 600, color: '#f8e8d4' }}>{area.nameCn}</div>
          <div style={{ fontSize: 10, color: 'rgba(248,232,212,0.5)' }}>{area.name}</div>
        </div>
      </div>

      <div style={{ marginBottom: 8 }}>
        <SourceBadge source={dataSource} />
        {area.systemLink && (
          <span style={{ marginLeft: 6, fontSize: 9, color: 'rgba(248,232,212,0.4)' }}>
            → {area.systemLink}
          </span>
        )}
      </div>

      <div style={{ fontSize: 11, color: 'rgba(248,232,212,0.75)', lineHeight: 1.5, marginBottom: 8 }}>
        {area.description}
      </div>

      {loading && (
        <div style={{ fontSize: 10, color: 'rgba(248,232,212,0.4)', fontStyle: 'italic' }}>加载中...</div>
      )}

      {!loading && areaData && area.id === 'memory_library' && (
        <MemoryDetail data={areaData} />
      )}
      {!loading && areaData && area.id === 'skill_workshop' && (
        <SkillDetail data={areaData} />
      )}
      {!loading && areaData && (area.id === 'resource_market' || area.id === 'devtools_lab') && (
        <DevtoolsDetail data={areaData} />
      )}
      {!loading && areaData && area.id === 'knowledge_tower' && (
        <KnowledgeDetail data={areaData} />
      )}

      <div style={{ borderTop: '1px solid rgba(233,69,96,0.2)', paddingTop: 8, marginTop: 8 }}>
        <InfoRow label="类型" value={area.type} />
        <InfoRow label="位置" value={`(${area.position.x}, ${area.position.y})`} />
        <InfoRow label="大小" value={`${area.size.w}×${area.size.h} tiles`} />
      </div>
    </>
  );
}

function MemoryDetail({ data }: { data: any }) {
  return (
    <div style={{ borderTop: '1px solid rgba(233,69,96,0.15)', paddingTop: 6 }}>
      <div style={{ fontSize: 9, color: 'rgba(248,232,212,0.4)', textTransform: 'uppercase', marginBottom: 4 }}>记忆系统</div>
      <InfoRow label="总记忆数" value={String(data.totalMemories || 0)} />
      {data.typeCounts && Object.keys(data.typeCounts).length > 0 && (
        <div style={{ marginTop: 4 }}>
          <div style={{ fontSize: 9, color: 'rgba(248,232,212,0.4)', marginBottom: 2 }}>类型分布</div>
          {Object.entries(data.typeCounts).map(([type, count]) => (
            <InfoRow key={type} label={type} value={String(count)} />
          ))}
        </div>
      )}
      {data.topConcepts && data.topConcepts.length > 0 && (
        <div style={{ marginTop: 6 }}>
          <div style={{ fontSize: 9, color: 'rgba(248,232,212,0.4)', marginBottom: 3 }}>热门概念</div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 3 }}>
            {data.topConcepts.slice(0, 10).map((c: string) => (
              <span key={c} style={{ fontSize: 9, padding: '1px 5px', background: 'rgba(233,69,96,0.15)', borderRadius: 3, color: 'rgba(248,232,212,0.8)' }}>{c}</span>
            ))}
          </div>
        </div>
      )}
      {data.recentMemories && data.recentMemories.length > 0 && (
        <div style={{ marginTop: 6 }}>
          <div style={{ fontSize: 9, color: 'rgba(248,232,212,0.4)', marginBottom: 3 }}>最近记忆</div>
          {data.recentMemories.slice(0, 4).map((m: any) => (
            <div key={m.id} style={{ fontSize: 10, color: 'rgba(248,232,212,0.65)', marginBottom: 3, lineHeight: 1.3, borderLeft: '2px solid rgba(233,69,96,0.3)', paddingLeft: 6 }}>
              <span style={{ color: 'rgba(248,232,212,0.4)', fontSize: 9 }}>[{m.type}]</span> {m.title?.slice(0, 60)}
            </div>
          ))}
        </div>
      )}
      {data.decisions && data.decisions.length > 0 && (
        <div style={{ marginTop: 6 }}>
          <div style={{ fontSize: 9, color: 'rgba(248,232,212,0.4)', marginBottom: 3 }}>决策 ({data.decisions.length})</div>
          {data.decisions.slice(0, 3).map((d: any) => (
            <div key={d.name} style={{ fontSize: 10, color: 'rgba(248,232,212,0.6)', marginBottom: 2 }}>• {d.name}</div>
          ))}
        </div>
      )}
    </div>
  );
}

function SkillDetail({ data }: { data: any }) {
  return (
    <div style={{ borderTop: '1px solid rgba(233,69,96,0.15)', paddingTop: 6 }}>
      <div style={{ fontSize: 9, color: 'rgba(248,232,212,0.4)', textTransform: 'uppercase', marginBottom: 4 }}>技能系统</div>
      <InfoRow label="总技能数" value={String(data.totalSkills || 0)} />
      {data.fullCategories && data.fullCategories.length > 0 && (
        <div style={{ marginTop: 6 }}>
          <div style={{ fontSize: 9, color: 'rgba(248,232,212,0.4)', marginBottom: 3 }}>分类</div>
          {data.fullCategories.slice(0, 6).map((cat: any) => (
            <div key={cat.name} style={{ marginBottom: 4 }}>
              <div style={{ fontSize: 10, color: 'rgba(248,232,212,0.8)', fontWeight: 500 }}>{cat.name} ({cat.skills?.length || 0})</div>
              <div style={{ fontSize: 9, color: 'rgba(248,232,212,0.5)', marginLeft: 8 }}>
                {cat.skills?.slice(0, 3).join(', ')}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function DevtoolsDetail({ data }: { data: any }) {
  return (
    <div style={{ borderTop: '1px solid rgba(233,69,96,0.15)', paddingTop: 6 }}>
      <div style={{ fontSize: 9, color: 'rgba(248,232,212,0.4)', textTransform: 'uppercase', marginBottom: 4 }}>开发工具</div>
      <InfoRow label="工具数" value={String(data.toolCount || 0)} />
      {data.pendingMessages !== undefined && (
        <InfoRow label="待处理消息" value={String(data.pendingMessages)} />
      )}
      {data.activeTools && data.activeTools.length > 0 && (
        <div style={{ marginTop: 6 }}>
          <div style={{ fontSize: 9, color: 'rgba(248,232,212,0.4)', marginBottom: 3 }}>可用工具</div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 3 }}>
            {data.activeTools.slice(0, 12).map((t: string) => (
              <span key={t} style={{ fontSize: 9, padding: '1px 5px', background: 'rgba(74,222,128,0.12)', borderRadius: 3, color: 'rgba(134,239,172,0.9)' }}>{t}</span>
            ))}
          </div>
        </div>
      )}
      {data.agentHubStatus && Object.keys(data.agentHubStatus).length > 0 && (
        <div style={{ marginTop: 6 }}>
          <div style={{ fontSize: 9, color: 'rgba(248,232,212,0.4)', marginBottom: 3 }}>Agent Hub</div>
          {Object.entries(data.agentHubStatus).map(([agent, status]) => (
            <InfoRow key={agent} label={agent} value={String(status)} />
          ))}
        </div>
      )}
    </div>
  );
}

function KnowledgeDetail({ data }: { data: any }) {
  return (
    <div style={{ borderTop: '1px solid rgba(233,69,96,0.15)', paddingTop: 6 }}>
      <div style={{ fontSize: 9, color: 'rgba(248,232,212,0.4)', textTransform: 'uppercase', marginBottom: 4 }}>知识库</div>
      <InfoRow label="Wiki 页面" value={String(data.pageCount || 0)} />
      <InfoRow label="Memory 文件" value={String(data.memoryCount || 0)} />
      <InfoRow label="总条目" value={String(data.totalEntries || 0)} />
      {data.recentPages && data.recentPages.length > 0 && (
        <div style={{ marginTop: 6 }}>
          <div style={{ fontSize: 9, color: 'rgba(248,232,212,0.4)', marginBottom: 3 }}>最近页面</div>
          {data.recentPages.slice(0, 5).map((p: any) => (
            <div key={p.name} style={{ fontSize: 10, color: 'rgba(248,232,212,0.65)', marginBottom: 2 }}>📄 {p.name}</div>
          ))}
        </div>
      )}
    </div>
  );
}

export function PixelTownInspector() {
  const selectedAgent = usePixelTownStore((s) => s.selectedAgent);
  const selectedArea = usePixelTownStore((s) => s.selectedArea);
  const showPanel = usePixelTownStore((s) => s.showPanel);
  const clearSelection = usePixelTownStore((s) => s.clearSelection);

  if (!showPanel || (!selectedAgent && !selectedArea)) return null;

  return (
    <div className="pixel-inspector">
      <div className="pixel-panel">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
          <span className="pixel-panel-title" style={{ margin: 0, padding: 0, border: 'none' }}>
            {selectedAgent ? '🔍 居民信息' : '🏠 建筑信息'}
          </span>
          <button
            onClick={clearSelection}
            style={{
              background: 'none', border: 'none', color: 'rgba(248,232,212,0.5)',
              cursor: 'pointer', fontSize: 16, padding: '0 4px',
            }}
            aria-label="关闭面板"
          >
            ×
          </button>
        </div>

        {selectedAgent && <AgentInspector agent={selectedAgent} />}
        {selectedArea && <AreaInspector area={selectedArea} />}
      </div>
    </div>
  );
}
