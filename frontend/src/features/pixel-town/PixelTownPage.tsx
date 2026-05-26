import { useEffect, useRef } from 'react';
import { createGame } from '../../game/PhaserGame';
import { usePixelTownStore } from './pixelTownStore';
import { getTownHealth, getTownMemorySummary, getTownSkillSummary, getTownKnowledgeSummary } from './adapters/townDataAdapter';
import { PixelTownHUD } from './PixelTownHUD';
import { PixelTownLogPanel } from './PixelTownLogPanel';
import { PixelTownInspector } from './PixelTownInspector';
import { PixelTownDebugOverlay, PixelTownDebugToggle } from './PixelTownDebugOverlay';
import './styles/pixelTown.css';

function useAdapterPolling() {
  const setHealth = usePixelTownStore((s) => s.setHealth);
  const setMemorySummary = usePixelTownStore((s) => s.setMemorySummary);
  const setSkillSummary = usePixelTownStore((s) => s.setSkillSummary);
  const setKnowledgeSummary = usePixelTownStore((s) => s.setKnowledgeSummary);

  useEffect(() => {
    let cancelled = false;

    async function poll() {
      if (cancelled) return;
      try {
        const [health, memory, skills, knowledge] = await Promise.all([
          getTownHealth(),
          getTownMemorySummary(),
          getTownSkillSummary(),
          getTownKnowledgeSummary(),
        ]);
        if (cancelled) return;
        setHealth(health.data);
        setMemorySummary(memory.data);
        setSkillSummary(skills.data);
        setKnowledgeSummary(knowledge.data);
      } catch {
        // graceful - don't crash
      }
    }

    poll();
    const interval = setInterval(poll, 30000);
    return () => { cancelled = true; clearInterval(interval); };
  }, [setHealth, setMemorySummary, setSkillSummary, setKnowledgeSummary]);
}

export function PixelTownPage() {
  const gameRef = useRef<HTMLDivElement>(null);
  const gameInstance = useRef<Phaser.Game | null>(null);
  const connected = usePixelTownStore((s) => s.connected);

  useAdapterPolling();

  useEffect(() => {
    if (gameRef.current && !gameInstance.current) {
      gameInstance.current = createGame(gameRef.current);
    }
    return () => {
      gameInstance.current?.destroy(true);
      gameInstance.current = null;
    };
  }, []);

  return (
    <div className="pixel-town-root">
      <PixelTownHUD />

      {/* Game Canvas */}
      <div
        ref={gameRef}
        style={{ position: 'absolute', inset: 0, top: 40, zIndex: 1 }}
      />

      {/* UI Overlay Layer — sits above canvas, blocks pointer events on panels */}
      <div style={{ position: 'absolute', inset: 0, top: 40, zIndex: 10, pointerEvents: 'none' }}>
        {/* Connection notice */}
        {!connected && (
          <div style={{ position: 'absolute', left: 12, top: 12, pointerEvents: 'auto' }}>
            <div className="pixel-panel" style={{ maxWidth: 320 }}>
              <div className="pixel-panel-title">连接后端中</div>
              <p style={{ fontSize: 11, lineHeight: 1.5, color: 'rgba(248,232,212,0.7)', margin: 0 }}>
                小镇画面已就绪，正在连接 FastAPI 后端。请确认 backend 运行在 8000 端口。
              </p>
            </div>
          </div>
        )}

        {/* Inspector (right side) */}
        <div style={{ pointerEvents: 'auto' }}>
          <PixelTownInspector />
        </div>

        {/* Event Log (bottom-left) */}
        <div style={{ pointerEvents: 'auto' }}>
          <PixelTownLogPanel />
        </div>

        {/* Debug */}
        <div style={{ pointerEvents: 'auto' }}>
          <PixelTownDebugOverlay />
          <PixelTownDebugToggle />
        </div>
      </div>
    </div>
  );
}
