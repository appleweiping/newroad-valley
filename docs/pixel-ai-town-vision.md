# Pixel AI Town — Product Vision

## What It Is

Pixel AI Town is the living visualization layer for an existing multi-agent system. It renders the real state of AI agents, their memories, skills, resources, and relationships as an inhabited pixel world.

This is not a toy or demo. It is a persistent, game-like environment where AI agents live long-term — with identity, routine, mood, and history.

## Design Direction

- **Stardew Valley warmth**: cozy, inhabited, alive with small details and daily rhythms
- **Terraria asset pipeline**: modular tile-based construction, systematic sprite management
- **AI Agent long-term state**: agents persist across sessions, accumulate history, evolve relationships

## Town Geography — Real System Mapping

Each town area maps to a real backend system. All access is read-only.

| Town Area | Real System | What It Shows |
|-----------|-------------|---------------|
| Memory Library | agentmemory MCP | Memories, lessons, observations, recall activity |
| Skill Workshop | skills directories | Available skills, usage frequency, skill chains |
| Knowledge Tower | Vipin's Knowledgebase | Facts, decisions, workflows, indexes |
| Resource Market | agent-resources | Repos, skill packs, slash commands |
| Devtools Lab | devtools | CLI tools, agent configs, hub state |

### Data Access Rules

- All real system access is **read-only** — the town never writes back
- Graceful fallback when a system is unavailable (agents idle, buildings dim)
- No mock data pretending to be real — if data is unavailable, show absence honestly

## Agent Model

Each agent in the town has:

- **Identity**: name, role, visual appearance
- **State**: current activity, location, mood, energy
- **Memory summary**: recent memories, active recall topics
- **Skill summary**: equipped skills, recent skill usage
- **Resource summary**: tools and repos currently relevant
- **Relationships**: connections to other agents, interaction history
- **Events**: recent actions, completions, decisions

## Inhabited Feel

The town should feel lived-in:

- Agents have homes they return to
- Daily routines: work, rest, wander, interact
- Mood reflects real workload (busy agent = focused sprite, idle agent = relaxed)
- Activities visible: reading at the library, crafting at the workshop, trading at the market
- Time-of-day lighting and ambient changes

## Future Extensions

- **Dreams**: agents process memories during rest cycles
- **Schedules**: visible daily/weekly routines
- **Governance**: town council for multi-agent decisions
- **Economy**: resource trading, skill sharing costs
- **Relationship graphs**: visible social network in town
- **Action logs**: scrollable history per agent
- **Events**: town-wide happenings triggered by real system events

## Safety Boundaries

- No writes to real systems from the visualization layer
- No destructive migrations or state changes
- No mock data presented as real data
- No agent actions that affect production systems
- Visualization is always a reflection, never a controller
