import asyncio
import sys
from pathlib import Path
from contextlib import asynccontextmanager

# Load .env before importing config
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).parent))

from config import HOST, PORT, TICK_INTERVAL_SECONDS
from db import init_db, save_event, get_recent_events
from town_engine import TownEngine
from websocket_manager import WebSocketManager
from adapters.agent_hub import AgentHubAdapter
from adapters.agentmemory import AgentMemoryAdapter
from adapters.shared_memory import SharedMemoryAdapter
from adapters.skills import SkillAdapter
from adapters.knowledge import KnowledgeAdapter

engine = TownEngine()
ws_manager = WebSocketManager()

hub_adapter = AgentHubAdapter()
memory_adapter = AgentMemoryAdapter()
shared_mem_adapter = SharedMemoryAdapter()
skill_adapter = SkillAdapter()
knowledge_adapter = KnowledgeAdapter()


async def tick_loop():
    while True:
        try:
            await hub_adapter.refresh()
            await memory_adapter.refresh()
            await shared_mem_adapter.refresh()
            await skill_adapter.refresh()
            await knowledge_adapter.refresh()

            engine.update_adapter_cache({
                "agent_status": hub_adapter.get_agent_status(),
                "recent_sessions": memory_adapter.get_recent_sessions(),
            })

            new_events = await engine.tick()

            for event in new_events:
                await save_event(
                    event.id, event.timestamp, event.agent_id,
                    event.event_type, event.description, event.zone
                )

            if ws_manager.client_count > 0:
                await ws_manager.broadcast({
                    "type": "tick",
                    "state": engine.get_state(),
                })
        except asyncio.CancelledError:
            raise
        except Exception as e:
            print(f"[tick] error: {e}")

        await asyncio.sleep(TICK_INTERVAL_SECONDS)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    task = asyncio.create_task(tick_loop())
    print(f"[AI Town] Engine started, tick every {TICK_INTERVAL_SECONDS}s")
    try:
        yield
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        print("[AI Town] Engine stopped")


app = FastAPI(
    title="Pixel AI Town",
    version="1.0.0",
    description="像素风 AI 小镇后端",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "tick_count": engine.tick_count,
        "clients": ws_manager.client_count,
        "adapters": {
            "agent_hub": hub_adapter.is_available,
            "agentmemory": memory_adapter.is_available,
            "shared_memory": shared_mem_adapter.is_available,
            "skills": skill_adapter.is_available,
            "knowledge": knowledge_adapter.is_available,
        },
    }


@app.get("/api/town/state")
async def get_town_state():
    return engine.get_state()


@app.get("/api/town/agents")
async def get_agents():
    return [a.model_dump() for a in engine.agents.values()]


@app.get("/api/town/agents/{agent_id}")
async def get_agent(agent_id: str):
    agent = engine.agents.get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="agent not found")
    return agent.model_dump()


@app.get("/api/town/buildings")
async def get_buildings():
    return [b.model_dump() for b in engine.buildings]


@app.get("/api/town/events")
async def get_events(limit: int = 30):
    safe_limit = max(1, min(limit, 100))
    if engine.events:
        return [e.model_dump() for e in engine.events[:safe_limit]]
    return await get_recent_events(safe_limit)


@app.get("/api/town/memory")
async def get_memory_data():
    await shared_mem_adapter.refresh()
    await memory_adapter.refresh()
    return {
        "source": "adapter" if shared_mem_adapter.is_available or memory_adapter.is_available else "unavailable",
        "shared_memory": {
            "available": shared_mem_adapter.is_available,
            "decisions": shared_mem_adapter.get_decisions(),
            "facts": shared_mem_adapter.get_facts(),
            "lessons": shared_mem_adapter.get_lessons(),
            "sessions": shared_mem_adapter.get_sessions(),
            "index_preview": shared_mem_adapter.get_index()[:800],
        },
        "agentmemory": {
            "available": memory_adapter.is_available,
            "total_count": memory_adapter.get_total_count(),
            "type_counts": memory_adapter.get_type_counts(),
            "top_concepts": memory_adapter.get_top_concepts(),
            "recent": memory_adapter.get_recent_memories(8),
        },
    }


@app.get("/api/town/skills")
async def get_skills_data():
    await skill_adapter.refresh()
    return {
        "source": "adapter" if skill_adapter.is_available else "unavailable",
        "available": skill_adapter.is_available,
        "total_count": skill_adapter.get_total_count(),
        "categories": skill_adapter.get_categories(),
    }


@app.get("/api/town/knowledge")
async def get_knowledge_data():
    await knowledge_adapter.refresh()
    overview = knowledge_adapter.get_overview()
    return {
        "source": "adapter" if knowledge_adapter.is_available else "unavailable",
        "available": knowledge_adapter.is_available,
        **overview,
    }


@app.get("/api/town/devtools")
async def get_devtools_data():
    """Read-only devtools status from D:\\devtools"""
    from pathlib import Path
    devtools_dir = Path(r"D:\devtools")
    result = {
        "source": "adapter" if devtools_dir.exists() else "unavailable",
        "available": devtools_dir.exists(),
        "tools": [],
        "agent_hub_status": hub_adapter.get_agent_status(),
    }
    if devtools_dir.exists():
        cmd_files = list(devtools_dir.glob("*.cmd"))
        result["tools"] = [f.stem for f in cmd_files[:20]]
        state_dir = devtools_dir / "agent-hub" / "state"
        if state_dir.exists():
            messages_file = state_dir / "messages-claude.json"
            if messages_file.exists():
                try:
                    import json
                    msgs = json.loads(messages_file.read_text(encoding="utf-8"))
                    result["pending_messages"] = len(msgs) if isinstance(msgs, list) else 0
                except Exception:
                    result["pending_messages"] = 0
    return result


class MoveRequest(BaseModel):
    x: int
    y: int


@app.post("/api/town/player/move")
async def move_player(req: MoveRequest):
    engine.move_player(req.x, req.y)
    if ws_manager.client_count > 0:
        await ws_manager.broadcast({
            "type": "tick",
            "state": engine.get_state(),
        })
    return {"ok": True, "state": engine.get_state()}


@app.post("/api/town/tick")
async def manual_tick():
    events = await engine.tick()
    return {"events": [e.model_dump() for e in events]}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        await websocket.send_json({"type": "init", "state": engine.get_state()})
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception:
        ws_manager.disconnect(websocket)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=HOST, port=PORT, reload=True)
