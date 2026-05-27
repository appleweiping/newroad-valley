const AGENTS = [
  { id: 'opus', name: 'Opus' },
  { id: 'pixelcat', name: 'PixelCat' },
  { id: 'sonnet', name: 'Sonnet' },
  { id: 'codex', name: 'Codex' },
  { id: 'haiku', name: 'Haiku' },
  { id: 'deepseek', name: 'DeepSeek' },
  { id: 'aris', name: 'ARIS' },
  { id: 'player', name: 'Mayor' },
]

interface Props {
  onOpenCharacter: (id: string) => void
}

export function Sidebar({ onOpenCharacter }: Props) {
  return (
    <div className="sidebar-left">
      {AGENTS.map(a => (
        <button
          key={a.id}
          className="portrait-btn"
          onClick={() => onOpenCharacter(a.id)}
          title={a.name}
        >
          <img src={`/assets/portraits/${a.id}.png`} alt={a.name} />
        </button>
      ))}
    </div>
  )
}
