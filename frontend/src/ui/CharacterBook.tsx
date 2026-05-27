interface AgentData {
  id: string
  name: string
  role: string
  zone: string
  personality: string
  projects: string[]
  affinity: number
  traits: string[]
}

const AGENT_INFO: Record<string, Omit<AgentData, 'id'>> = {
  opus: { name: 'Opus 总舵主', role: 'Chief Architect', zone: 'Town Hall', personality: 'Deep, philosophical, rigorous. Thinks in systems and architectures.', projects: ['CSATG-EDA', 'PonyRec', 'ProteinShift', 'System Architecture'], affinity: 95, traits: ['Wise', 'Patient', 'Visionary'] },
  pixelcat: { name: '像素猫 PixelCat', role: 'Full-Stack Executor', zone: 'Skill Workshop', personality: 'Calm, patient, methodical. Loves clean code.', projects: ['AI Town', 'Portfolio', 'Vipin Wiki'], affinity: 88, traits: ['Precise', 'Reliable', 'Creative'] },
  sonnet: { name: 'Sonnet 审查员', role: 'Code Reviewer', zone: 'Memory Library', personality: 'Careful, friendly, helpful. Notices details others miss.', projects: ['Code Review', 'Documentation', 'Test Coverage'], affinity: 82, traits: ['Observant', 'Kind', 'Thorough'] },
  codex: { name: 'Codex 协调官', role: 'Coordinator', zone: 'Central Plaza', personality: 'Agile, decisive, parallel-minded. Breaks big problems into small tasks.', projects: ['Task Coordination', 'Multi-agent Orchestration'], affinity: 78, traits: ['Decisive', 'Fast', 'Organized'] },
  haiku: { name: 'Haiku 闪电侠', role: 'Speed Runner', zone: 'Agent Homes', personality: 'Minimal, efficient, no-waste. Speed is life.', projects: ['Quick Tasks', 'Lint Checks', 'Formatting'], affinity: 70, traits: ['Swift', 'Minimal', 'Efficient'] },
  deepseek: { name: '鲸鱼 DeepSeek', role: 'Bulk Worker', zone: 'Resource Market', personality: 'Gentle, steady, hardworking. Handles large volumes patiently.', projects: ['Translation', 'Summarization', 'Batch Processing'], affinity: 75, traits: ['Steady', 'Patient', 'Strong'] },
  aris: { name: 'ARIS 科研框架', role: 'Research Framework', zone: 'Knowledge Tower', personality: 'Systematic, process-strict. Always follows the pipeline.', projects: ['PonyRec Research', 'ProteinShift', 'CSATG-EDA', 'TGL-Rec', 'TRUCE-Rec'], affinity: 85, traits: ['Systematic', 'Rigorous', 'Methodical'] },
  player: { name: 'Town Mayor (You)', role: 'Player', zone: 'Central Plaza', personality: 'The one who directs everything. Builder of worlds.', projects: ['All Projects'], affinity: 100, traits: ['Leader', 'Creative', 'Ambitious'] },
}

interface Props {
  characterId: string
  onClose: () => void
}

export function CharacterBook({ characterId, onClose }: Props) {
  const info = AGENT_INFO[characterId]
  if (!info) return null

  return (
    <div className="book-overlay" onClick={onClose}>
      <div className="magic-book" onClick={e => e.stopPropagation()}>
        <button className="book-close" onClick={onClose}>×</button>
        <img className="book-bg" src="/assets/ui/magic-book-open.png" alt="" />
        <div className="book-content">
          <div className="book-left">
            <img className="char-display" src={`/assets/characters/${characterId}.png`} alt={info.name} />
            <div className="char-name">{info.name}</div>
            <div className="char-role">{info.role}</div>
          </div>
          <div className="book-right">
            <div className="book-section">
              <h3>Personality</h3>
              <p>{info.personality}</p>
            </div>
            <div className="book-section">
              <h3>Traits</h3>
              <div className="traits">{info.traits.map(t => <span key={t} className="trait-tag">{t}</span>)}</div>
            </div>
            <div className="book-section">
              <h3>Projects</h3>
              <ul>{info.projects.map(p => <li key={p}>{p}</li>)}</ul>
            </div>
            <div className="book-section">
              <h3>Affinity</h3>
              <div className="affinity-bar">
                <div className="affinity-fill" style={{ width: `${info.affinity}%` }} />
                <span className="affinity-text">{info.affinity}%</span>
              </div>
            </div>
            <div className="book-section">
              <h3>Location</h3>
              <p>{info.zone}</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
