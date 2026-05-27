import * as Phaser from 'phaser'
import { useGameStore } from '../store/gameStore'

const INTERIOR_W = 1536
const INTERIOR_H = 1024
const SPRITE_SIZE = 64
const WALK_SPEED = 70

const BUILDING_RESIDENTS: Record<string, string> = {
  'town-hall': 'opus',
  'memory-library': 'sonnet',
  'knowledge-tower': 'aris',
  'skill-workshop': 'pixelcat',
  'devtools-lab': 'codex',
  'dream-garden': 'haiku',
  'resource-market': 'deepseek',
  'agent-homes': 'haiku',
}

export class InteriorScene extends Phaser.Scene {
  private buildingId: string = ''
  private playerSprite!: Phaser.GameObjects.Sprite
  private residentSprite!: Phaser.GameObjects.Sprite
  private playerTarget: { x: number; y: number } | null = null
  private residentId: string = ''

  constructor() {
    super({ key: 'InteriorScene' })
  }

  init(data: { buildingId: string }) {
    this.buildingId = data.buildingId
    this.residentId = BUILDING_RESIDENTS[data.buildingId] || 'opus'
  }

  preload() {
    const bgKey = `interior-${this.buildingId}`
    if (!this.textures.exists(bgKey)) {
      this.load.image(bgKey, `/assets/interiors/${this.buildingId}.png`)
    }
  }

  create() {
    const bgKey = `interior-${this.buildingId}`
    if (this.textures.exists(bgKey)) {
      const bg = this.add.image(INTERIOR_W / 2, INTERIOR_H / 2, bgKey)
      bg.setDisplaySize(INTERIOR_W, INTERIOR_H)
      bg.setDepth(0)
    }

    this.createResident()
    this.createPlayer()
    this.setupCamera()
    this.setupInput()
    this.addExitButton()
    this.startResidentIdle()
  }

  private createResident() {
    const key = `sheet-${this.residentId}`
    const x = INTERIOR_W / 2 + 100
    const y = INTERIOR_H / 2 + 50

    if (this.textures.exists(key)) {
      this.residentSprite = this.add.sprite(x, y, key, 0)
      this.residentSprite.setDisplaySize(SPRITE_SIZE, SPRITE_SIZE)
      const idleKey = `${this.residentId}-idle`
      if (this.anims.exists(idleKey)) this.residentSprite.play(idleKey)
    } else {
      this.residentSprite = this.add.sprite(x, y, '__DEFAULT')
    }

    this.residentSprite.setDepth(10)
    this.residentSprite.setInteractive()
    this.residentSprite.on('pointerdown', (p: Phaser.Input.Pointer) => {
      p.event.stopPropagation()
      useGameStore.getState().selectAgent(this.residentId)
    })
  }

  private createPlayer() {
    const x = INTERIOR_W / 2 - 100
    const y = INTERIOR_H / 2 + 100

    if (this.textures.exists('sheet-player')) {
      this.playerSprite = this.add.sprite(x, y, 'sheet-player', 0)
      this.playerSprite.setDisplaySize(SPRITE_SIZE, SPRITE_SIZE)
      const idleKey = 'player-idle'
      if (this.anims.exists(idleKey)) this.playerSprite.play(idleKey)
    } else {
      this.playerSprite = this.add.sprite(x, y, '__DEFAULT')
    }
    this.playerSprite.setDepth(20)
  }

  private setupCamera() {
    this.cameras.main.setBounds(0, 0, INTERIOR_W, INTERIOR_H)
    this.cameras.main.centerOn(INTERIOR_W / 2, INTERIOR_H / 2)
  }

  private setupInput() {
    this.input.on('pointerdown', (pointer: Phaser.Input.Pointer) => {
      const x = pointer.worldX
      const y = pointer.worldY
      if (y > 200 && y < 900 && x > 100 && x < 1400) {
        this.playerTarget = { x, y }
      }
    })
  }

  private addExitButton() {
    const btn = this.add.text(50, 30, '← Exit', {
      fontSize: '16px', color: '#4a3a2a', fontFamily: 'Georgia, serif',
      backgroundColor: '#f5f0e8dd', padding: { x: 12, y: 6 },
    }).setInteractive().setDepth(100).setScrollFactor(0)

    btn.on('pointerdown', () => {
      this.scene.start('TownScene')
    })
    btn.on('pointerover', () => btn.setStyle({ color: '#6c5b7b' }))
    btn.on('pointerout', () => btn.setStyle({ color: '#4a3a2a' }))
  }

  private startResidentIdle() {
    this.time.addEvent({
      delay: 5000,
      loop: true,
      callback: () => {
        const ox = Phaser.Math.Between(-30, 30)
        const oy = Phaser.Math.Between(-15, 15)
        const tx = Phaser.Math.Clamp(INTERIOR_W / 2 + 100 + ox, 200, 1300)
        const ty = Phaser.Math.Clamp(INTERIOR_H / 2 + 50 + oy, 300, 800)

        const dx = tx - this.residentSprite.x
        const dir = Math.abs(dx) > Math.abs(ty - this.residentSprite.y)
          ? (dx > 0 ? 'right' : 'left')
          : (ty > this.residentSprite.y ? 'down' : 'up')

        const walkKey = `${this.residentId}-walk-${dir}`
        if (this.anims.exists(walkKey)) this.residentSprite.play(walkKey, true)

        this.tweens.add({
          targets: this.residentSprite,
          x: tx, y: ty,
          duration: 1500,
          ease: 'Sine.easeInOut',
          onComplete: () => {
            const idleKey = `${this.residentId}-idle`
            if (this.anims.exists(idleKey)) this.residentSprite.play(idleKey, true)
          }
        })
      }
    })
  }

  update(_time: number, delta: number) {
    if (!this.playerTarget || !this.playerSprite) return

    const dx = this.playerTarget.x - this.playerSprite.x
    const dy = this.playerTarget.y - this.playerSprite.y
    const dist = Math.sqrt(dx * dx + dy * dy)

    if (dist < 5) {
      this.playerTarget = null
      if (this.anims.exists('player-idle')) this.playerSprite.play('player-idle', true)
      return
    }

    const speed = WALK_SPEED * (delta / 1000)
    const moveX = (dx / dist) * Math.min(speed, dist)
    const moveY = (dy / dist) * Math.min(speed, dist)
    this.playerSprite.x += moveX
    this.playerSprite.y += moveY

    const dir = Math.abs(dx) > Math.abs(dy)
      ? (dx > 0 ? 'right' : 'left')
      : (dy > 0 ? 'down' : 'up')
    const animKey = `player-walk-${dir}`
    if (this.anims.exists(animKey) && this.playerSprite.anims.currentAnim?.key !== animKey) {
      this.playerSprite.play(animKey, true)
    }
  }
}
