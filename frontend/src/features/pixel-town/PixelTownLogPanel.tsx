import { useState, useCallback } from 'react';
import { usePixelTownStore } from './pixelTownStore';

export function PixelTownLogPanel() {
  const events = usePixelTownStore((s) => s.events);
  const eventsSource = usePixelTownStore((s) => s.eventsSource);
  const [minimized, setMinimized] = useState(false);

  const stop = useCallback((e: React.MouseEvent) => {
    e.stopPropagation();
  }, []);

  if (minimized) {
    return (
      <div className="pixel-log-panel" onClick={stop} onPointerDown={stop}>
        <button
          onClick={(e) => { e.stopPropagation(); setMinimized(false); }}
          className="pixel-panel"
          style={{ cursor: 'pointer', padding: '8px 14px', fontSize: 11, border: 'none', width: 'auto' }}
        >
          📜 日志 ({events.length}) ▲
        </button>
      </div>
    );
  }

  return (
    <div className="pixel-log-panel" onClick={stop} onPointerDown={stop}>
      <div className="pixel-panel">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 }}>
          <span className="pixel-panel-title" style={{ margin: 0, padding: 0, border: 'none' }}>
            📜 小镇日志
          </span>
          <button
            onClick={(e) => { e.stopPropagation(); setMinimized(true); }}
            style={{ background: 'rgba(233,69,96,0.15)', border: '1px solid rgba(233,69,96,0.3)', color: '#ffd6df', cursor: 'pointer', fontSize: 10, padding: '3px 8px', borderRadius: 3 }}
          >
            收起 ▼
          </button>
        </div>
        <div style={{ maxHeight: 140, overflowY: 'auto' }}>
          {events.slice(0, 12).map((event) => (
            <div key={event.id} className="pixel-log-entry">
              <span className="pixel-log-time">
                {new Date(event.timestamp * 1000).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })}
              </span>
              <span>{event.description}</span>
            </div>
          ))}
          {events.length === 0 && (
            <div style={{ padding: '12px 0', textAlign: 'center', fontSize: 11, color: 'rgba(248,232,212,0.4)', fontStyle: 'italic' }}>
              等待小镇活动...
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
