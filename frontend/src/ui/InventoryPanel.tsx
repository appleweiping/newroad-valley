import { useState, useEffect } from 'react'

interface Project {
  name: string
  path: string
  items: string[]
  count: number
}

interface Props { onClose: () => void }

export function InventoryPanel({ onClose }: Props) {
  const [projects, setProjects] = useState<Project[]>([])
  const [loading, setLoading] = useState(true)
  const [expanded, setExpanded] = useState<string | null>(null)

  useEffect(() => {
    fetch('http://localhost:8000/api/inventory')
      .then(r => r.json())
      .then(d => { setProjects(d.projects || []); setLoading(false) })
      .catch(() => setLoading(false))
  }, [])

  return (
    <div className="book-overlay" onClick={onClose}>
      <div className="magic-book" onClick={e => e.stopPropagation()}>
        <button className="book-close" onClick={onClose}>×</button>
        <img className="book-bg" src="/assets/ui/magic-book-open.png" alt="" />
        <div className="book-content settings-content">
          <div className="settings-page" style={{overflow:'auto',maxHeight:'400px'}}>
            <h2 className="settings-title">Inventory — Your Projects</h2>
            {loading && <p style={{color:'#8b7b6b'}}>Scanning D: drive...</p>}
            {projects.map(p => (
              <div key={p.name} className="inventory-project">
                <div
                  className="inventory-header"
                  onClick={() => setExpanded(expanded === p.name ? null : p.name)}
                  style={{cursor:'pointer',display:'flex',justifyContent:'space-between',alignItems:'center',padding:'8px 0',borderBottom:'1px solid #e8e0d8'}}
                >
                  <span style={{fontWeight:'bold',color:'#4a3a2a',fontSize:'13px'}}>{p.name}</span>
                  <span style={{color:'#8b7b6b',fontSize:'11px'}}>{p.count} items</span>
                </div>
                {expanded === p.name && (
                  <ul className="data-list" style={{paddingLeft:'12px',marginTop:'4px'}}>
                    {p.items.map(item => <li key={item} style={{fontSize:'12px'}}>{item}</li>)}
                  </ul>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
