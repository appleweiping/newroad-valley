import { useState, useEffect } from 'react'

interface Props { onClose: () => void }

export function QuestsPanel({ onClose }: Props) {
  const [tasks, setTasks] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch('http://localhost:8000/api/tasks')
      .then(r => r.json())
      .then(d => { setTasks(d.tasks || d.actions || []); setLoading(false) })
      .catch(() => setLoading(false))
  }, [])

  return (
    <div className="book-overlay" onClick={onClose}>
      <div className="magic-book" onClick={e => e.stopPropagation()}>
        <button className="book-close" onClick={onClose}>×</button>
        <img className="book-bg" src="/assets/ui/magic-book-open.png" alt="" />
        <div className="book-content settings-content">
          <div className="settings-page">
            <h2 className="settings-title">Quests & Tasks</h2>
            {loading && <p style={{color:'#8b7b6b'}}>Loading from agentmemory...</p>}
            {!loading && tasks.length === 0 && (
              <p style={{color:'#4a3a2a',fontSize:'13px'}}>No active quests. Talk to agents to assign work — they will create real tasks in the system.</p>
            )}
            {tasks.length > 0 && (
              <ul className="data-list">
                {tasks.map((t: any, i: number) => (
                  <li key={i}>
                    <span className="tag">{t.status || 'pending'}</span>
                    {t.title || t.description || JSON.stringify(t).slice(0, 60)}
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
