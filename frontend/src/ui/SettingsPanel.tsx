import { useState } from 'react'

interface Props {
  onClose: () => void
}

const LANGUAGES = [
  { code: 'zh', name: '中文' },
  { code: 'en', name: 'English' },
  { code: 'ja', name: '日本語' },
  { code: 'ko', name: '한국어' },
]

export function SettingsPanel({ onClose }: Props) {
  const [bgmVolume, setBgmVolume] = useState(70)
  const [sfxVolume, setSfxVolume] = useState(80)
  const [language, setLanguage] = useState('zh')

  const handleLanguageChange = (code: string) => {
    setLanguage(code)
    document.documentElement.setAttribute('data-lang', code)
  }

  return (
    <div className="book-overlay" onClick={onClose}>
      <div className="magic-book settings-book" onClick={e => e.stopPropagation()}>
        <button className="book-close" onClick={onClose}>×</button>
        <img className="book-bg" src="/assets/ui/magic-book-open.png" alt="" />
        <div className="book-content settings-content">
          <div className="settings-page">
            <h2 className="settings-title">Settings</h2>

            <div className="setting-group">
              <label>BGM Volume</label>
              <input type="range" min="0" max="100" value={bgmVolume} onChange={e => setBgmVolume(Number(e.target.value))} />
              <span className="vol-value">{bgmVolume}%</span>
            </div>

            <div className="setting-group">
              <label>SFX Volume</label>
              <input type="range" min="0" max="100" value={sfxVolume} onChange={e => setSfxVolume(Number(e.target.value))} />
              <span className="vol-value">{sfxVolume}%</span>
            </div>

            <div className="setting-group">
              <label>Language</label>
              <div className="lang-buttons">
                {LANGUAGES.map(l => (
                  <button
                    key={l.code}
                    className={`lang-btn ${language === l.code ? 'active' : ''}`}
                    onClick={() => handleLanguageChange(l.code)}
                  >
                    {l.name}
                  </button>
                ))}
              </div>
            </div>

            <div className="setting-group">
              <label>Camera Zoom</label>
              <input type="range" min="60" max="250" defaultValue={120} onChange={e => {
                const event = new CustomEvent('zoom-change', { detail: Number(e.target.value) / 100 })
                window.dispatchEvent(event)
              }} />
            </div>

            <div className="setting-group">
              <label>Tick Speed</label>
              <select defaultValue="10" onChange={e => {
                const event = new CustomEvent('tick-change', { detail: Number(e.target.value) })
                window.dispatchEvent(event)
              }}>
                <option value="5">Fast (5s)</option>
                <option value="10">Normal (10s)</option>
                <option value="20">Slow (20s)</option>
                <option value="30">Very Slow (30s)</option>
              </select>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
