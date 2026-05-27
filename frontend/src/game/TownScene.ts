import * as Phaser from 'phaser'
import { useGameStore } from '../store/gameStore'

const MAP_W = 1536
const MAP_H = 1024
const SPRITE_SIZE = 64
const FRAME_W = 256
const FRAME_H = 256
const WALK_SPEED = 80

interface AgentConfig {
  id: string
  homeX: number
  homeY: number
  wanderRadius: number
}

const AGENT_CONFIGS: AgentConfig[] = [
  { id: 'opus', homeX: 768, homeY: 320, wanderRadius: 40 },
  { id: 'pixelcat', homeX: 300, homeY: 440, wanderRadius: 35 },
  { id: 'sonnet', homeX: 500, homeY: 240, wanderRadius: 35 },
  { id: 'codex', homeX: 900, homeY: 600, wanderRadius: 40 },
  { id: 'haiku', homeX: 650, homeY: 780, wanderRadius: 30 },
  { id: 'deepseek', homeX: 1150, homeY: 620, wanderRadius: 35 },
  { id: 'aris', homeX: 1100, homeY: 260, wanderRadius: 35 },
]

const WALKABLE_Y_MIN = 180
const WALKABLE_Y_MAX = 900
const WALKABLE_X_MIN = 100
const WALKABLE_X_MAX = 1440

function isWalkable(x: number, y: number): boolean {
  if (x < WALKABLE_X_MIN || x > WALKABLE_X_MAX) return false
  if (y < WALKABLE_Y_MIN || y > WALKABLE_Y_MAX) return false
  // Block building rooftops (approximate rectangles)
  const buildings = [
    { x: 680, y: 180, w: 180, h: 120 }, // Town Hall roof
    { x: 380, y: 130, w: 140, h: 90 },  // Memory Library roof
    { x: 1020, y: 130, w: 140, h: 100 }, // Knowledge Tower roof
    { x: 200, y: 320, w: 120, h: 80 },  // Skill Workshop roof
    { x: 1180, y: 320, w: 120, h: 80 }, // Resource Market roof
  ]
  for (const b of buildings) {
    if (x > b.x && x < b.x + b.w && y > b.y && y < b.y + b.h) return false
  }
  return true
}

export class TownScene extends Phaser.Scene {
  private agentSprites: Map<string, Phaser.GameObjects.Sprite> = new Map()
  private playerSprite!: Phaser.GameObjects.Sprite
  private playerTarget: { x: number; y: number } | null = null
  private bgReady = false

  constructor() {
    super({ key: 'TownScene' })
  }

  preload() {
    this.load.image('town-map', '/assets/town-map.png')

    const allIds = [...AGENT_CONFIGS.map(a => a.id), 'player']
    for (const id of allIds) {
      this.load.spritesheet(`sheet-${id}`, `/assets/characters/${id}-sheet.png`, {
        frameWidth: FRAME_W,
        frameHeight: FRAME_H,
      })
    }

    this.load.on('filecomplete-image-town-map', () => { this.bgReady = true })
  }

  create() {
    if (this.bgReady) {
      const bg = this.add.image(MAP_W / 2, MAP_H / 2, 'town-map')
      bg.setDisplaySize(MAP_W, MAP_H)
      bg.setDepth(0)
    } else {
      this.createFallbackBackground()
    }

    this.createBuildingHotspots()
    this.createAnimations()
    this.createAgents()
    this.createPlayer()
    this.setupCamera()
    this.setupClickToMove()
    this.startNPCIdleLoop()
  }

  private createBuildingHotspots() {
    const buildings = [
      { id: 'town-hall', x: 768, y: 240, w: 160, h: 100 },
      { id: 'memory-library', x: 450, y: 170, w: 130, h: 80 },
      { id: 'knowledge-tower', x: 1100, y: 170, w: 130, h: 100 },
      { id: 'skill-workshop', x: 280, y: 370, w: 120, h: 80 },
      { id: 'devtools-lab', x: 280, y: 660, w: 120, h: 80 },
      { id: 'dream-garden', x: 1250, y: 710, w: 130, h: 90 },
    ]

    for (const b of buildings) {
      const zone = this.add.zone(b.x, b.y, b.w, b.h).setInteractive()
      zone.setDepth(5)
      zone.on('pointerdown', (p: Phaser.Input.Pointer) => {
        p.event.stopPropagation()
        window.dispatchEvent(new CustomEvent('building-click', { detail: b.id }))
      })
    }
  }

  private createFallbackBackground() {
    const g = this.add.graphics()
    g.fillStyle(0xf5f0e8)
    g.fillRect(0, 0, MAP_W, MAP_H)
    g.lineStyle(1, 0xd4c8b0, 0.3)
    for (let x = 0; x < MAP_W; x += 64) g.lineBetween(x, 0, x, MAP_H)
    for (let y = 0; y < MAP_H; y += 64) g.lineBetween(0, y, MAP_W, y)
    g.setDepth(0)
  }

  private createAnimations() {
    const allIds = [...AGENT_CONFIGS.map(a => a.id), 'player']
    for (const id of allIds) {
      const key = `sheet-${id}`
      if (!this.textures.exists(key)) continue

      // Row 0: walk-down (frames 0-3), Row 1: walk-left (4-7), Row 2: walk-right (8-11), Row 3: walk-up (12-15)
      this.anims.create({ key: `${id}-walk-down`, frames: this.anims.generateFrameNumbers(key, { start: 0, end: 3 }), frameRate: 6, repeat: -1 })
      this.anims.create({ key: `${id}-walk-left`, frames: this.anims.generateFrameNumbers(key, { start: 4, end: 7 }), frameRate: 6, repeat: -1 })
      this.anims.create({ key: `${id}-walk-right`, frames: this.anims.generateFrameNumbers(key, { start: 8, end: 11 }), frameRate: 6, repeat: -1 })
      this.anims.create({ key: `${id}-walk-up`, frames: this.anims.generateFrameNumbers(key, { start: 12, end: 15 }), frameRate: 6, repeat: -1 })
      this.anims.create({ key: `${id}-idle`, frames: this.anims.generateFrameNumbers(key, { frames: [0, 1] }), frameRate: 2, repeat: -1 })
    }
  }

  private createAgents() {
    for (const config of AGENT_CONFIGS) {
      let sprite: Phaser.GameObjects.Sprite
      if (this.textures.exists(`sheet-${config.id}`)) {
        sprite = this.add.sprite(config.homeX, config.homeY, `sheet-${config.id}`, 0)
        sprite.setDisplaySize(SPRITE_SIZE, SPRITE_SIZE)
        sprite.play(`${config.id}-idle`)
      } else {
        sprite = this.add.sprite(config.homeX, config.homeY, '__DEFAULT')
      }

      sprite.setDepth(10 + Math.floor(config.homeY))
      sprite.setInteractive()
      sprite.on('pointerdown', (p: Phaser.Input.Pointer) => {
        p.event.stopPropagation()
        useGameStore.getState().selectAgent(config.id)
      })

      this.agentSprites.set(config.id, sprite)
    }
  }

  private createPlayer() {
    const startX = 768
    const startY = 600
    if (this.textures.exists('sheet-player')) {
      this.playerSprite = this.add.sprite(startX, startY, 'sheet-player', 0)
      this.playerSprite.setDisplaySize(SPRITE_SIZE, SPRITE_SIZE)
      this.playerSprite.play('player-idle')
    } else {
      this.playerSprite = this.add.sprite(startX, startY, '__DEFAULT')
    }
    this.playerSprite.setDepth(100)
  }

  private setupCamera() {
    this.cameras.main.setBounds(0, 0, MAP_W, MAP_H)
    this.cameras.main.startFollow(this.playerSprite, true, 0.05, 0.05)
    this.cameras.main.setZoom(1.2)

    this.input.on('wheel', (_p: any, _gos: any, _dx: number, dy: number) => {
      const cam = this.cameras.main
      const newZoom = Phaser.Math.Clamp(cam.zoom - dy * 0.001, 0.6, 2.5)
      cam.setZoom(newZoom)
    })
  }

  private setupClickToMove() {
    this.input.on('pointerdown', (pointer: Phaser.Input.Pointer) => {
      const worldX = pointer.worldX
      const worldY = pointer.worldY
      if (isWalkable(worldX, worldY)) {
        this.playerTarget = { x: worldX, y: worldY }
      }
    })
  }

  private startNPCIdleLoop() {
    this.time.addEvent({
      delay: 4000,
      loop: true,
      callback: () => this.npcIdleTick(),
    })
  }

  private npcIdleTick() {
    for (const config of AGENT_CONFIGS) {
      const sprite = this.agentSprites.get(config.id)
      if (!sprite) continue

      // Small wander near home (not across the map)
      const offsetX = Phaser.Math.Between(-config.wanderRadius, config.wanderRadius)
      const offsetY = Phaser.Math.Between(-config.wanderRadius / 2, config.wanderRadius / 2)
      const targetX = Phaser.Math.Clamp(config.homeX + offsetX, WALKABLE_X_MIN, WALKABLE_X_MAX)
      const targetY = Phaser.Math.Clamp(config.homeY + offsetY, WALKABLE_Y_MIN, WALKABLE_Y_MAX)

      if (!isWalkable(targetX, targetY)) return

      const dx = targetX - sprite.x
      const dy = targetY - sprite.y
      const dir = Math.abs(dx) > Math.abs(dy)
        ? (dx > 0 ? 'right' : 'left')
        : (dy > 0 ? 'down' : 'up')

      const animKey = `${config.id}-walk-${dir}`
      if (this.anims.exists(animKey)) sprite.play(animKey, true)

      const dist = Math.sqrt(dx * dx + dy * dy)
      const duration = (dist / 40) * 1000

      this.tweens.add({
        targets: sprite,
        x: targetX,
        y: targetY,
        duration: Math.max(duration, 800),
        ease: 'Sine.easeInOut',
        onUpdate: () => { sprite.setDepth(10 + Math.floor(sprite.y)) },
        onComplete: () => {
          const idleKey = `${config.id}-idle`
          if (this.anims.exists(idleKey)) sprite.play(idleKey, true)
        },
      })
    }
  }

  update(_time: number, delta: number) {
    if (!this.playerTarget || !this.playerSprite) return

    const dx = this.playerTarget.x - this.playerSprite.x
    const dy = this.playerTarget.y - this.playerSprite.y
    const dist = Math.sqrt(dx * dx + dy * dy)

    if (dist < 5) {
      this.playerTarget = null
      const idleKey = 'player-idle'
      if (this.anims.exists(idleKey)) this.playerSprite.play(idleKey, true)
      return
    }

    const speed = WALK_SPEED * (delta / 1000)
    const moveX = (dx / dist) * Math.min(speed, dist)
    const moveY = (dy / dist) * Math.min(speed, dist)

    const newX = this.playerSprite.x + moveX
    const newY = this.playerSprite.y + moveY

    if (isWalkable(newX, newY)) {
      this.playerSprite.x = newX
      this.playerSprite.y = newY
      this.playerSprite.setDepth(100 + Math.floor(newY))

      const dir = Math.abs(dx) > Math.abs(dy)
        ? (dx > 0 ? 'right' : 'left')
        : (dy > 0 ? 'down' : 'up')
      const animKey = `player-walk-${dir}`
      if (this.anims.exists(animKey) && this.playerSprite.anims.currentAnim?.key !== animKey) {
        this.playerSprite.play(animKey, true)
      }
    } else {
      this.playerTarget = null
      const idleKey = 'player-idle'
      if (this.anims.exists(idleKey)) this.playerSprite.play(idleKey, true)
    }
  }
}
