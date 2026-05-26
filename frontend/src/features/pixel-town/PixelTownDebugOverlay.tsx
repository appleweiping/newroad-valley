import { usePixelTownStore } from './pixelTownStore';

export function PixelTownDebugOverlay() {
  const config = usePixelTownStore((s) => s.config);
  const agents = usePixelTownStore((s) => s.agents);
  const agentsSource = usePixelTownStore((s) => s.agentsSource);
  const eventsSource = usePixelTownStore((s) => s.eventsSource);
  const health = usePixelTownStore((s) => s.health);

  if (!config.debugMode) return null;

  return (
    <div className="pixel-debug-overlay">
      <div className="pixel-panel" style={{ fontSize: 10, opacity: 0.9, maxWidth: 220 }}>
        <div className="pixel-panel-title" style={{ marginBottom: 4 }}>🐛 DEBUG</div>
        <div style={{ color: 'rgba(248,232,212,0.7)', lineHeight: 1.6 }}>
          <div>Agents: {agents.length} ({agentsSource})</div>
          <div>Events source: {eventsSource}</div>
          <div>Memory: {health.memory}</div>
          <div>Skills: {health.skills}</div>
          <div>Resources: {health.resources}</div>
          <div>Knowledge: {health.knowledge}</div>
          <div>Agent Hub: {health.agentHub}</div>
          <div>Grid: {config.showGrid ? 'ON' : 'OFF'}</div>
          <div>Zone bounds: {config.showZoneBounds ? 'ON' : 'OFF'}</div>
        </div>
      </div>
    </div>
  );
}

export function PixelTownDebugToggle() {
  const toggleDebug = usePixelTownStore((s) => s.toggleDebug);
  const debugMode = usePixelTownStore((s) => s.config.debugMode);

  return (
    <button
      className="pixel-debug-toggle"
      onClick={toggleDebug}
      title={debugMode ? 'Hide debug info' : 'Show debug info'}
    >
      {debugMode ? '🐛 DEBUG ON' : '🐛'}
    </button>
  );
}
