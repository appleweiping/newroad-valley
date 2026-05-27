interface Props {
  onOpenSettings: () => void
  onOpenQuests: () => void
  onOpenInventory: () => void
}

export function BottomBar({ onOpenSettings, onOpenQuests, onOpenInventory }: Props) {
  return (
    <div className="bottom-bar">
      <button className="action-btn" onClick={onOpenSettings} title="Settings">
        <img src="/assets/ui/settings.png" alt="Settings" />
      </button>
      <button className="action-btn" onClick={onOpenQuests} title="Quests">
        <img src="/assets/ui/quests.png" alt="Quests" />
      </button>
      <button className="action-btn" onClick={onOpenInventory} title="Inventory">
        <img src="/assets/ui/inventory.png" alt="Inventory" />
      </button>
    </div>
  )
}
