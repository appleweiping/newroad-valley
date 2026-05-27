import { useEffect, useRef, useState } from 'react'
import * as Phaser from 'phaser'
import { TownScene } from './game/TownScene'
import { InteriorScene } from './game/InteriorScene'
import { DialoguePanel } from './ui/DialoguePanel'
import { Sidebar } from './ui/Sidebar'
import { BottomBar } from './ui/BottomBar'
import { CharacterBook } from './ui/CharacterBook'
import { SettingsPanel } from './ui/SettingsPanel'
import { BuildingView } from './ui/BuildingView'
import { QuestsPanel } from './ui/QuestsPanel'
import { InventoryPanel } from './ui/InventoryPanel'
import { useGameStore } from './store/gameStore'
import './App.css'

function App() {
  const gameRef = useRef<Phaser.Game | null>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const selectedAgent = useGameStore(s => s.selectedAgent)

  const [characterBookId, setCharacterBookId] = useState<string | null>(null)
  const [showSettings, setShowSettings] = useState(false)
  const [showQuests, setShowQuests] = useState(false)
  const [showInventory, setShowInventory] = useState(false)
  const [buildingId, setBuildingId] = useState<string | null>(null)

  useEffect(() => {
    if (!containerRef.current || gameRef.current) return

    gameRef.current = new Phaser.Game({
      type: Phaser.AUTO,
      parent: containerRef.current,
      width: window.innerWidth,
      height: window.innerHeight,
      pixelArt: false,
      backgroundColor: '#f5f0e8',
      scene: [TownScene, InteriorScene],
      scale: {
        mode: Phaser.Scale.RESIZE,
        autoCenter: Phaser.Scale.CENTER_BOTH,
      },
    })

    const handleBuildingClick = (e: Event) => {
      const detail = (e as CustomEvent).detail
      // Switch Phaser to interior scene
      if (gameRef.current) {
        const scene = gameRef.current.scene.getScene('TownScene')
        if (scene) {
          scene.scene.start('InteriorScene', { buildingId: detail })
        }
      }
      setBuildingId(detail)
    }
    window.addEventListener('building-click', handleBuildingClick)

    return () => {
      window.removeEventListener('building-click', handleBuildingClick)
      gameRef.current?.destroy(true)
      gameRef.current = null
    }
  }, [])

  return (
    <div className="game-container">
      <div ref={containerRef} className="phaser-canvas" />

      <Sidebar onOpenCharacter={setCharacterBookId} />
      <BottomBar
        onOpenSettings={() => setShowSettings(true)}
        onOpenQuests={() => setShowQuests(true)}
        onOpenInventory={() => setShowInventory(true)}
      />

      {selectedAgent && <DialoguePanel agentId={selectedAgent} />}
      {characterBookId && <CharacterBook characterId={characterBookId} onClose={() => setCharacterBookId(null)} />}
      {showSettings && <SettingsPanel onClose={() => setShowSettings(false)} />}
      {showQuests && <QuestsPanel onClose={() => setShowQuests(false)} />}
      {showInventory && <InventoryPanel onClose={() => setShowInventory(false)} />}
      {buildingId && <BuildingView buildingId={buildingId} onClose={() => setBuildingId(null)} />}

      <div className="hud">
        <span className="hud-title">Agent Town</span>
        <span className="hud-sep">|</span>
        <span className="hud-item">Click ground to move</span>
        <span className="hud-sep">|</span>
        <span className="hud-item">Click agent to chat</span>
        <span className="hud-sep">|</span>
        <span className="hud-item">Click building to enter</span>
      </div>
    </div>
  )
}

export default App
