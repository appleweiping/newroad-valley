import { usePixelTownStore } from './pixelTownStore';

function getTimeLabel(t: number): string {
  const hour = Math.floor(t * 24);
  const min = Math.floor((t * 24 - hour) * 60);
  return `${hour.toString().padStart(2, '0')}:${min.toString().padStart(2, '0')}`;
}

export function PixelTownHUD() {
  const connected = usePixelTownStore((s) => s.connected);
  const agents = usePixelTownStore((s) => s.agents);
  const timeOfDay = usePixelTownStore((s) => s.timeOfDay);
  const memorySummary = usePixelTownStore((s) => s.memorySummary);
  const skillSummary = usePixelTownStore((s) => s.skillSummary);
  const knowledgeSummary = usePixelTownStore((s) => s.knowledgeSummary);

  return (
    <header className="pixel-hud-header">
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
        <span style={{
          display: 'inline-flex', width: 24, height: 24,
          alignItems: 'center', justifyContent: 'center',
          borderRadius: 3, border: '1px solid rgba(233,69,96,0.4)',
          background: 'rgba(26,26,46,0.7)', fontSize: 12,
        }}>🏘️</span>
        <div>
          <div className="pixel-hud-title">PIXEL AI TOWN</div>
          <div style={{ fontSize: 9, color: 'rgba(248,232,212,0.45)' }}>multi-agent living layer</div>
        </div>
      </div>

      <div className="pixel-hud-stats">
        <span className="pixel-hud-stat">
          <span className="pixel-hud-stat-icon">🕐</span>
          {getTimeLabel(timeOfDay)}
        </span>
        <span className="pixel-hud-stat">
          <span className="pixel-hud-stat-icon">👥</span>
          {agents.length}
        </span>
        <span className="pixel-hud-stat" title="记忆">
          <span className="pixel-hud-stat-icon">📚</span>
          {memorySummary ? memorySummary.totalMemories : '—'}
        </span>
        <span className="pixel-hud-stat" title="技能">
          <span className="pixel-hud-stat-icon">🔧</span>
          {skillSummary ? skillSummary.totalSkills : '—'}
        </span>
        <span className="pixel-hud-stat" title="知识">
          <span className="pixel-hud-stat-icon">🗼</span>
          {knowledgeSummary ? knowledgeSummary.totalEntries : '—'}
        </span>
        <span className={connected ? 'pixel-hud-status pixel-hud-status--online' : 'pixel-hud-status pixel-hud-status--offline'}>
          {connected ? '● live' : '○ offline'}
        </span>
      </div>
    </header>
  );
}
