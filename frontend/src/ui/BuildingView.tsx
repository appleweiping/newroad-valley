import { useState, useEffect } from 'react'

interface BuildingData {
  name: string
  [key: string]: any
}

interface Props {
  buildingId: string
  onClose: () => void
}

const BUILDING_NAMES: Record<string, string> = {
  'memory-library': 'Memory Library',
  'skill-workshop': 'Skill Workshop',
  'knowledge-tower': 'Knowledge Tower',
  'town-hall': 'Town Hall',
  'devtools-lab': 'Devtools Lab',
  'dream-garden': 'Dream Garden',
}

export function BuildingView({ buildingId, onClose }: Props) {
  const [data, setData] = useState<BuildingData | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    fetch(`http://localhost:8000/api/buildings/${buildingId}`)
      .then(r => r.json())
      .then(d => { setData(d); setLoading(false) })
      .catch(() => { setData(null); setLoading(false) })
  }, [buildingId])

  return (
    <div className="building-overlay" onClick={onClose}>
      <div className="building-interior" onClick={e => e.stopPropagation()}>
        <button className="building-close" onClick={onClose}>×</button>
        <img className="building-bg" src={`/assets/interiors/${buildingId}.png`} alt="" />
        <div className="building-content">
          <h2 className="building-title">{BUILDING_NAMES[buildingId] || buildingId}</h2>
          {loading && <p className="building-loading">Loading real data...</p>}
          {data && renderBuildingContent(buildingId, data)}
        </div>
      </div>
    </div>
  )
}

function renderBuildingContent(id: string, data: any) {
  switch (id) {
    case 'memory-library':
      return (
        <div className="building-data">
          <div className="data-stats">
            <div className="stat"><span className="stat-num">{data.summary?.decisions || 0}</span><span className="stat-label">Decisions</span></div>
            <div className="stat"><span className="stat-num">{data.summary?.facts || 0}</span><span className="stat-label">Facts</span></div>
            <div className="stat"><span className="stat-num">{data.summary?.lessons || 0}</span><span className="stat-label">Lessons</span></div>
          </div>
          <h3>Recent Memories</h3>
          <ul className="data-list">
            {(data.recent || []).map((f: any, i: number) => (
              <li key={i}><span className="tag">{f.category}</span> {f.name}</li>
            ))}
          </ul>
        </div>
      )
    case 'skill-workshop':
      return (
        <div className="building-data">
          <div className="data-stats">
            <div className="stat"><span className="stat-num">{data.total_skills || 0}</span><span className="stat-label">Skills</span></div>
            <div className="stat"><span className="stat-num">{data.categories || 0}</span><span className="stat-label">Categories</span></div>
          </div>
          <h3>Skills</h3>
          <ul className="data-list">
            {(data.skills || []).slice(0, 15).map((s: any, i: number) => (
              <li key={i}><span className="tag">{s.category}</span> {s.name}</li>
            ))}
          </ul>
        </div>
      )
    case 'knowledge-tower':
      return (
        <div className="building-data">
          <div className="data-stats">
            <div className="stat"><span className="stat-num">{data.pages || 0}</span><span className="stat-label">Pages</span></div>
          </div>
          <h3>Topics</h3>
          <ul className="data-list">
            {(data.topics || []).map((t: string, i: number) => (
              <li key={i}>{t}</li>
            ))}
          </ul>
        </div>
      )
    case 'devtools-lab':
      return (
        <div className="building-data">
          <div className="data-stats">
            <div className="stat"><span className="stat-num">{data.count || 0}</span><span className="stat-label">Tools</span></div>
          </div>
          <h3>Available Tools</h3>
          <ul className="data-list">
            {(data.tools || []).map((t: any, i: number) => (
              <li key={i}>{t.name}</li>
            ))}
          </ul>
        </div>
      )
    case 'town-hall':
      return (
        <div className="building-data">
          <h3>Recent Decisions</h3>
          <ul className="data-list">
            {(data.recent_decisions || []).map((d: any, i: number) => (
              <li key={i}>{d.title || d.name}</li>
            ))}
          </ul>
        </div>
      )
    default:
      return <p>A peaceful place to rest and think...</p>
  }
}
