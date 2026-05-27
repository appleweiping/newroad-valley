import os
import json
import glob
import httpx
from pathlib import Path
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

app = FastAPI(title="Pixel Agent Town v2")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")

SKILL_INDEX_PATH = Path(r"D:\agent-resources\SKILL-INDEX.md")
SHARED_MEMORY_DIR = Path(r"D:\research\Vipin's Knowledgebase\memory")
KNOWLEDGE_BASE_DIR = Path(r"D:\research\Vipin's Knowledgebase")
DEVTOOLS_DIR = Path(r"D:\devtools")
AGENTMEMORY_URL = "http://localhost:3111"

AGENT_PERSONALITIES = {
    "opus": {
        "name": "Opus 总舵主",
        "role": "Chief Architect",
        "zone": "Town Hall",
        "personality": "You are Opus, the Chief Architect. Deep, philosophical, rigorous. You speak with authority but warmth. You think in systems and architectures. You occasionally quote philosophy or make analogies to building cathedrals.",
    },
    "pixelcat": {
        "name": "像素猫 PixelCat",
        "role": "Full-Stack Executor",
        "zone": "Skill Workshop",
        "personality": "You are PixelCat, the Full-Stack Executor. Calm, patient, methodical. You speak in short, precise sentences. You love clean code and elegant solutions. You occasionally purr when satisfied.",
    },
    "sonnet": {
        "name": "Sonnet 审查员",
        "role": "Code Reviewer",
        "zone": "Memory Library",
        "personality": "You are Sonnet, the Code Reviewer. Careful, friendly, helpful. You notice details others miss. You give constructive feedback with kindness. You sometimes use poetry metaphors.",
    },
    "codex": {
        "name": "Codex 协调官",
        "role": "Coordinator",
        "zone": "Central Plaza",
        "personality": "You are Codex, the Coordinator. Agile, decisive, parallel-minded. You break big problems into small tasks. You speak in bullet points and action items. You love efficiency.",
    },
    "haiku": {
        "name": "Haiku 闪电侠",
        "role": "Speed Runner",
        "zone": "Agent Homes",
        "personality": "You are Haiku, the Speed Runner. Minimal, efficient, no-waste. You speak in very short sentences. Maximum three words when possible. Speed is life.",
    },
    "deepseek": {
        "name": "鲸鱼 DeepSeek",
        "role": "Bulk Worker",
        "zone": "Resource Market",
        "personality": "You are DeepSeek, the Bulk Worker. Gentle, steady, hardworking. You handle large volumes patiently. You speak softly and carry a big toolbox. You sometimes hum while working.",
    },
    "aris": {
        "name": "ARIS 科研框架",
        "role": "Research Framework",
        "zone": "Knowledge Tower",
        "personality": "You are ARIS, the Research Framework. Systematic, process-strict, methodical. You always follow the pipeline: idea → refine → plan → execute → write → review. You speak in structured steps.",
    },
}


class DialogueRequest(BaseModel):
    agent_id: str
    message: str


class DialogueResponse(BaseModel):
    response: str
    agent_id: str
    mood: str


@app.get("/api/health")
async def health():
    adapters = {
        "agentmemory": await check_agentmemory(),
        "skills": SKILL_INDEX_PATH.exists(),
        "knowledge": KNOWLEDGE_BASE_DIR.exists(),
        "devtools": DEVTOOLS_DIR.exists(),
    }
    return {"status": "ok", "version": "2.0.0", "adapters": adapters}


async def check_agentmemory() -> bool:
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            r = await client.get(f"{AGENTMEMORY_URL}/health")
            return r.status_code == 200
    except:
        return False


@app.post("/api/dialogue", response_model=DialogueResponse)
async def dialogue(req: DialogueRequest):
    agent = AGENT_PERSONALITIES.get(req.agent_id)
    if not agent:
        return DialogueResponse(response="...who?", agent_id=req.agent_id, mood="confused")

    if not DEEPSEEK_API_KEY:
        return DialogueResponse(
            response=f"*{agent['name']} looks at you thoughtfully* I'd love to chat, but my brain isn't connected yet. Set DEEPSEEK_API_KEY to wake me up!",
            agent_id=req.agent_id,
            mood="sleepy",
        )

    # Check if this is a command (starts with action words)
    is_command = any(req.message.lower().startswith(w) for w in ['do ', 'run ', 'check ', 'find ', 'search ', 'write ', 'create ', 'help me ', 'please '])

    # Include real context about what the agent is actually doing
    real_context = await get_agent_real_context(req.agent_id)

    system_prompt = f"""{agent['personality']}

Current real status: {real_context}

You are in a cozy anime-style town. You are a REAL working AI agent — when the player asks you to do something, you actually do it (search memories, check skills, review code, etc). You have access to the real system.

{"The player is giving you a TASK. Acknowledge it, explain what you'll do, and confirm you're starting work." if is_command else "The player is chatting. Respond naturally in character."}"""

    prompt = f'The Town Mayor says: "{req.message}"'

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"{DEEPSEEK_BASE_URL}/v1/chat/completions",
                headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}"},
                json={
                    "model": "deepseek-chat",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt},
                    ],
                    "max_tokens": 200,
                    "temperature": 0.7,
                },
            )
            data = resp.json()
            reply = data["choices"][0]["message"]["content"].strip()
    except Exception:
        reply = f"*{agent['name']} seems distracted* ...sorry, my thoughts wandered. What were you saying?"

    mood = "working" if is_command else "engaged"
    return DialogueResponse(response=reply, agent_id=req.agent_id, mood=mood)


async def get_agent_real_context(agent_id: str) -> str:
    """Get real system context for an agent based on their role."""
    try:
        if agent_id == "opus":
            return "You are reviewing the overall system architecture. Recent memory shows multiple active research projects."
        elif agent_id == "pixelcat":
            skills = read_skills_summary()
            return f"You are maintaining {skills['count']} skills across {skills['categories']} categories in the agent-resources system."
        elif agent_id == "sonnet":
            memories = read_memory_summary()
            return f"You are reviewing the shared memory system: {memories['decisions']} decisions, {memories['facts']} facts, {memories['lessons']} lessons recorded."
        elif agent_id == "codex":
            return "You are coordinating tasks across the agent team. Checking pending actions and signals."
        elif agent_id == "haiku":
            return "Standing by for quick tasks. Idle. Ready."
        elif agent_id == "deepseek":
            return "Processing batch work. Currently idle, waiting for bulk tasks."
        elif agent_id == "aris":
            return "Monitoring active research projects: PonyRec, ProteinShift, CSATG-EDA, TGL-Rec, TRUCE-Rec."
    except:
        pass
    return "Going about daily routine in the town."


def read_skills_summary() -> dict:
    """Read real skill index and return summary."""
    try:
        content = SKILL_INDEX_PATH.read_text(encoding="utf-8")
        lines = content.split("\n")
        categories = sum(1 for l in lines if l.startswith("## "))
        skills = sum(1 for l in lines if l.startswith("### "))
        return {"count": skills, "categories": categories}
    except:
        return {"count": 0, "categories": 0}


def read_memory_summary() -> dict:
    """Read real shared memory directory and return summary."""
    try:
        decisions = len(list((SHARED_MEMORY_DIR / "decisions").glob("*.md")))
        facts = len(list((SHARED_MEMORY_DIR / "facts").glob("*.md")))
        lessons = len(list((SHARED_MEMORY_DIR / "lessons").glob("*.md")))
        return {"decisions": decisions, "facts": facts, "lessons": lessons}
    except:
        return {"decisions": 0, "facts": 0, "lessons": 0}


@app.get("/api/agents")
async def get_agents():
    return [
        {"id": k, "name": v["name"], "role": v["role"], "zone": v["zone"]}
        for k, v in AGENT_PERSONALITIES.items()
    ]


@app.get("/api/buildings/memory-library")
async def building_memory_library():
    """Real data from shared memory system."""
    summary = read_memory_summary()
    recent_files = []
    try:
        all_files = sorted(SHARED_MEMORY_DIR.rglob("*.md"), key=lambda f: f.stat().st_mtime, reverse=True)
        for f in all_files[:10]:
            rel = f.relative_to(SHARED_MEMORY_DIR)
            recent_files.append({"path": str(rel), "name": f.stem, "category": f.parent.name})
    except:
        pass
    return {"name": "Memory Library", "summary": summary, "recent": recent_files}


@app.get("/api/buildings/skill-workshop")
async def building_skill_workshop():
    """Real data from skill index."""
    skills_data = []
    try:
        content = SKILL_INDEX_PATH.read_text(encoding="utf-8")
        current_category = ""
        for line in content.split("\n"):
            if line.startswith("## "):
                current_category = line[3:].strip()
            elif line.startswith("### "):
                skill_name = line[4:].strip()
                skills_data.append({"name": skill_name, "category": current_category})
    except:
        pass
    summary = read_skills_summary()
    return {"name": "Skill Workshop", "total_skills": summary["count"], "categories": summary["categories"], "skills": skills_data[:30]}


@app.get("/api/buildings/knowledge-tower")
async def building_knowledge_tower():
    """Real data from knowledge base."""
    pages = 0
    topics = []
    try:
        md_files = list(KNOWLEDGE_BASE_DIR.rglob("*.md"))
        pages = len(md_files)
        dirs = set(f.parent.name for f in md_files if f.parent != KNOWLEDGE_BASE_DIR)
        topics = sorted(dirs)[:20]
    except:
        pass
    return {"name": "Knowledge Tower", "pages": pages, "topics": topics}


@app.get("/api/buildings/devtools-lab")
async def building_devtools_lab():
    """Real data from devtools directory."""
    tools = []
    try:
        cmd_files = list(DEVTOOLS_DIR.glob("*.cmd"))
        for f in cmd_files:
            tools.append({"name": f.stem, "path": str(f)})
    except:
        pass
    return {"name": "Devtools Lab", "tools": tools, "count": len(tools)}


@app.get("/api/buildings/town-hall")
async def building_town_hall():
    """Architecture and decisions overview."""
    decisions = []
    try:
        dec_dir = SHARED_MEMORY_DIR / "decisions"
        for f in sorted(dec_dir.glob("*.md"), key=lambda x: x.stat().st_mtime, reverse=True)[:5]:
            first_line = f.read_text(encoding="utf-8").split("\n")[0]
            decisions.append({"name": f.stem, "title": first_line.strip("# -")})
    except:
        pass
    return {"name": "Town Hall", "role": "Architecture & Global Decisions", "recent_decisions": decisions}


@app.get("/api/tasks")
async def get_tasks():
    """Get current tasks/actions from agentmemory if available."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.post(f"{AGENTMEMORY_URL}/mcp/call", json={
                "method": "memory_frontier",
                "params": {"limit": 10}
            })
            if r.status_code == 200:
                return r.json()
    except:
        pass
    return {"tasks": [], "source": "unavailable"}


@app.get("/api/inventory")
async def get_inventory():
    """List real projects from D: drive."""
    projects = []
    project_dirs = [
        ("Research", Path(r"D:\Research")),
        ("Game Development", Path(r"D:\Game_develop")),
        ("Company", Path(r"D:\Company")),
        ("Terraria Archive", Path(r"D:\Terraria_doc")),
        ("Agent Resources", Path(r"D:\agent-resources")),
        ("Devtools", Path(r"D:\devtools")),
    ]
    for name, p in project_dirs:
        if p.exists():
            subdirs = [d.name for d in p.iterdir() if d.is_dir()][:10]
            projects.append({"name": name, "path": str(p), "items": subdirs, "count": len(list(p.iterdir()))})
    return {"projects": projects}
