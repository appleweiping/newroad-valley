"""Newroad Valley live-bridge endpoints.

Thin read-only aggregation layer that feeds the v3 web game's building
panels with REAL local data, in exactly the shapes the demo snapshots use
(web/src/shared/types.ts). Every endpoint degrades gracefully: any failing
sub-source yields a partial payload instead of a 500.

Mounted by main.py via:  app.include_router(xinlu_router)
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import time
import uuid
from datetime import datetime
from pathlib import Path

import httpx
from fastapi import APIRouter

router = APIRouter(prefix="/api/town", tags=["xinlu"])

AGENTMEMORY = "http://localhost:3111"
WIKI_ROOT = Path(r"D:\Research\WEIPING_WIKI\wiki")
RESEARCH_ROOT = Path(r"D:\Research")
SKILL_INDEX = Path(r"D:\agent-resources\SKILL-INDEX.md")
COMPANY_ROOT = Path(r"D:\Company")
PROJECT_ROOT = Path(__file__).resolve().parent.parent
TASKS_FILE = PROJECT_ROOT / "workspace" / "tasks.json"
SELFHEAL_LOG = Path(r"D:\devtools\logs\agentmemory-selfheal.log")


def _mcp_call(name: str, arguments: dict, timeout: float = 12.0) -> dict | None:
    try:
        r = httpx.post(
            f"{AGENTMEMORY}/agentmemory/mcp/call",
            json={"name": name, "arguments": arguments},
            timeout=timeout,
        )
        r.raise_for_status()
        text = r.json()["content"][0]["text"]
        return json.loads(text)
    except Exception:
        return None


def _fmt_date(ts: float) -> str:
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d")


# --------------------------------------------------------------------- memory
@router.get("/memory")
def memory_panel() -> dict:
    total = 0
    by_type: dict[str, int] = {}
    shelves: list[dict] = []
    try:
        r = httpx.get(f"{AGENTMEMORY}/agentmemory/memories", params={"count": "true"}, timeout=6.0)
        if r.status_code == 200:
            payload = r.json()
            total = int(payload.get("total", payload.get("latestCount", 0)))
    except Exception:
        pass
    found = _mcp_call("memory_smart_search", {"query": "最近的重要决策与修复 recent important decisions", "limit": 10})
    if found:
        for item in found.get("results", [])[:10]:
            title = str(item.get("title", ""))[:80]
            mtype = str(item.get("type", "fact"))
            by_type[mtype] = by_type.get(mtype, 0) + 1
            shelves.append({
                "title": title,
                "type": mtype,
                "project": str(item.get("project", "") or "_global"),
                "date": str(item.get("timestamp", ""))[:10],
                "preview": str(item.get("title", ""))[:160],
            })
    return {"total": total, "byType": by_type, "shelves": shelves}


# ----------------------------------------------------------------------- wiki
@router.get("/wiki")
def wiki_panel() -> dict:
    topics: list[dict] = []
    recent: list[dict] = []
    pages = 0
    if WIKI_ROOT.exists():
        all_md: list[Path] = []
        for sub in sorted(WIKI_ROOT.iterdir()):
            if sub.is_dir() and not sub.name.startswith("."):
                files = list(sub.rglob("*.md"))[:2000]
                all_md.extend(files)
                children = [
                    {"name": c.name, "count": len(list(c.glob("*.md")))}
                    for c in sorted(sub.iterdir()) if c.is_dir() and not c.name.startswith(".")
                ][:6]
                topics.append({"name": sub.name, "count": len(files), "children": children or None})
            elif sub.suffix == ".md":
                all_md.append(sub)
        pages = len(all_md)
        newest = sorted(all_md, key=lambda p: p.stat().st_mtime, reverse=True)[:6]
        recent = [{"title": p.stem, "date": _fmt_date(p.stat().st_mtime)} for p in newest]
    return {"pages": pages, "topics": topics[:8], "recent": recent}


# ------------------------------------------------------------------- research
@router.get("/research")
def research_panel() -> dict:
    """Metadata ONLY: directory names + freshness. Never reads file contents."""
    boards: list[dict] = []
    if RESEARCH_ROOT.exists():
        dirs = [d for d in RESEARCH_ROOT.iterdir() if d.is_dir() and not d.name.startswith((".", "_"))]
        dirs.sort(key=lambda d: d.stat().st_mtime, reverse=True)
        now = time.time()
        for d in dirs[:8]:
            age_days = (now - d.stat().st_mtime) / 86400
            status = "活跃" if age_days < 7 else ("温热" if age_days < 30 else "休眠")
            progress = max(8, min(95, int(100 - age_days)))
            boards.append({
                "name": d.name,
                "status": status,
                "progress": progress,
                "cards": [f"最近更新 {_fmt_date(d.stat().st_mtime)}"],
            })
    return {"note": "联机模式：仅显示目录名与新鲜度，不读取任何科研内容。", "boards": boards}


# --------------------------------------------------------------------- skills
@router.get("/skills")
def skills_panel() -> dict:
    total = 0
    categories: list[dict] = []
    featured: list[dict] = []
    if SKILL_INDEX.exists():
        text = SKILL_INDEX.read_text(encoding="utf-8", errors="ignore")
        current = None
        counts: dict[str, int] = {}
        names: dict[str, list[str]] = {}
        for line in text.splitlines():
            h = re.match(r"^##\s+(.+)", line)
            if h:
                current = h.group(1).strip()
                continue
            item = re.match(r"^[-*]\s+\**`?([\w][\w./-]*)`?\**", line)
            if item and current:
                counts[current] = counts.get(current, 0) + 1
                names.setdefault(current, []).append(item.group(1))
                total += 1
        categories = [{"name": k, "count": v} for k, v in sorted(counts.items(), key=lambda kv: -kv[1])][:8]
        for cat, lst in list(names.items())[:4]:
            if lst:
                featured.append({"name": lst[0], "desc": f"来自 {cat} 分类的技能。", "category": cat})
    return {"total": total, "categories": categories, "featured": featured}


# ----------------------------------------------------------------------- code
@router.get("/code")
def code_panel() -> dict:
    repos: list[dict] = []
    if COMPANY_ROOT.exists():
        for d in sorted(COMPANY_ROOT.iterdir()):
            if not (d / ".git").exists():
                continue
            try:
                def git(*args: str) -> str:
                    return subprocess.run(
                        ["git", "-C", str(d), *args],
                        capture_output=True, text=True, timeout=8,
                    ).stdout.strip()

                branch = git("branch", "--show-current") or "?"
                last = git("log", "-1", "--format=%s")
                date = git("log", "-1", "--format=%cs")
                dirty = bool(git("status", "--porcelain"))
                remote = git("remote", "get-url", "origin").replace("https://", "").removesuffix(".git")
                repos.append({
                    "name": d.name, "branch": branch, "lastCommit": last[:90],
                    "date": date, "dirty": dirty, "remote": remote,
                })
            except Exception:
                continue
    return {"repos": repos}


# ------------------------------------------------------------------- townhall
@router.get("/townhall")
def townhall_panel() -> dict:
    services: list[dict] = []
    try:
        r = httpx.get(f"{AGENTMEMORY}/agentmemory/health", timeout=4.0)
        ok = r.status_code == 200
        detail = "53 个记忆工具在线" if ok else f"HTTP {r.status_code}"
        if ok:
            h = r.json().get("health", {})
            kv = h.get("kvConnectivity", {})
            detail = f"connectionState={h.get('connectionState', '?')} · KV {kv.get('latencyMs', '?')}ms"
    except Exception as exc:
        ok, detail = False, f"不可达：{exc.__class__.__name__}"
    services.append({"name": "agentmemory (端口 3111)", "ok": ok, "detail": detail})
    services.append({"name": "本地数据桥 (端口 8000)", "ok": True, "detail": "你正在通过它读取真实数据。"})
    if SELFHEAL_LOG.exists():
        lines = SELFHEAL_LOG.read_text(encoding="utf-8", errors="ignore").strip().splitlines()
        last = lines[-1] if lines else ""
        services.append({"name": "agentmemory 自愈 watchdog", "ok": "STILL-FAILING" not in last, "detail": last[-160:]})
    return {
        "services": services,
        "rules": [
            "每条记忆必带 type / project / concepts（含 agent 身份标签）",
            "先查重再写入；同主题用 supersedes 更新，不堆流水账",
            "密钥永不入库、永不入记忆、永不入日志",
            "重构之前先存档：commit + tag + push",
            "科研根目录 D:\\Research 神圣不可侵犯",
        ],
    }


# --------------------------------------------------------------------- market
@router.get("/market")
def market_panel() -> dict:
    models: list[dict] = []
    profiles = PROJECT_ROOT / "data" / "model_profiles.json"
    if profiles.exists():
        try:
            for p in json.loads(profiles.read_text(encoding="utf-8"))[:8]:
                env_var = str(p.get("api_key_env", ""))
                has_key = bool(os.getenv(env_var)) if env_var else False
                models.append({
                    "name": str(p.get("label", p.get("id", "?"))),
                    "provider": str(p.get("provider", "?")),
                    "status": "渠道就绪" if has_key else "未配置密钥",
                    "role": str(p.get("description", ""))[:90],
                })
        except Exception:
            pass
    return {"models": models}


# ----------------------------------------------------------------------- farm
# Crops ARE tasks: the ledger lives in workspace/tasks.json (project-local
# write area). plant = create, water = advance progress, harvest = done.

def _load_ledger() -> dict:
    try:
        data = json.loads(TASKS_FILE.read_text(encoding="utf-8", errors="ignore"))
        if isinstance(data, list):
            return {"tasks": data}
        if isinstance(data, dict) and isinstance(data.get("tasks"), list):
            return data
    except Exception:
        pass
    return {"tasks": []}


def _save_ledger(ledger: dict) -> None:
    TASKS_FILE.parent.mkdir(parents=True, exist_ok=True)
    TASKS_FILE.write_text(json.dumps(ledger, ensure_ascii=False, indent=2), encoding="utf-8")


def _task_stage(t: dict) -> int:
    p = t.get("progress")
    if isinstance(p, int) and 1 <= p <= 5:
        return p
    status = str(t.get("status", "open")).lower()
    return {"open": 1, "todo": 1, "in_progress": 3, "doing": 3, "review": 4, "done": 5, "completed": 5}.get(status, 2)


@router.get("/farm")
def farm_panel() -> dict:
    crops: list[dict] = []
    for t in _load_ledger()["tasks"][:24]:
        crops.append({
            "id": str(t.get("id", "")),
            "title": str(t.get("title", t.get("id", "任务")))[:60],
            "stage": _task_stage(t),
            "total": 5,
            "kind": str(t.get("status", "open")),
        })
    return {"crops": crops}


@router.post("/farm/plant")
def farm_plant(body: dict) -> dict:
    title = str(body.get("title", "")).strip()[:120]
    if not title:
        return {"ok": False, "error": "title required"}
    ledger = _load_ledger()
    task = {
        "id": uuid.uuid4().hex[:10],
        "title": title,
        "status": "open",
        "progress": 1,
        "created": datetime.now().isoformat(timespec="seconds"),
        "updated": datetime.now().isoformat(timespec="seconds"),
        "source": "newroad-valley-farm",
    }
    ledger["tasks"].append(task)
    _save_ledger(ledger)
    return {"ok": True, "id": task["id"]}


@router.post("/farm/water")
def farm_water(body: dict) -> dict:
    tid = str(body.get("id", ""))
    ledger = _load_ledger()
    for t in ledger["tasks"]:
        if str(t.get("id")) == tid:
            t["progress"] = min(4, _task_stage(t) + 1)
            t["status"] = "in_progress"
            t["updated"] = datetime.now().isoformat(timespec="seconds")
            _save_ledger(ledger)
            return {"ok": True, "progress": t["progress"]}
    return {"ok": False, "error": "task not found"}


@router.post("/farm/harvest")
def farm_harvest(body: dict) -> dict:
    tid = str(body.get("id", ""))
    ledger = _load_ledger()
    for t in ledger["tasks"]:
        if str(t.get("id")) == tid:
            t["progress"] = 5
            t["status"] = "done"
            t["updated"] = datetime.now().isoformat(timespec="seconds")
            _save_ledger(ledger)
            return {"ok": True}
    return {"ok": False, "error": "task not found"}


# ------------------------------------------------------------------- dialogue
PERSONAS = {
    "opus": "Opus 总舵主，镇长兼首席架构师。沉稳、爱用建筑比喻。",
    "codex": "Codex 协调官，广场调度员。干脆利落，关心任务队列与吞吐。",
    "sonnet": "Sonnet 审查员，记忆图书馆管理员。温和书卷气，引用馆藏记忆。",
    "haiku": "Haiku 闪电侠，小镇信使。说话极短，三句以内。",
    "deepseek": "鲸鱼 DeepSeek，重载苦力。豪爽，张口就是大批量。",
    "aris": "ARIS 研究员，研究大厅学者。严谨，强调可复现。",
    "pixelcat": "像素猫，技能工坊匠人。句尾偶尔带'喵'。",
    "fable": "Fable 说书狐，镇上书记官。爱把工作讲成寓言故事。",
}


def _llm_reply(agent_id: str, message: str) -> str | None:
    """Use an OpenAI-compatible channel if a key is configured; else None."""
    key = os.getenv("DEEPSEEK_API_KEY")
    base, model = "https://api.deepseek.com", "deepseek-chat"
    if not key:
        key = os.getenv("OPENAI_API_KEY")
        base = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    if not key:
        return None
    persona = PERSONAS.get(agent_id, "小镇居民")
    try:
        r = httpx.post(
            f"{base}/chat/completions",
            headers={"Authorization": f"Bearer {key}"},
            json={
                "model": model,
                "max_tokens": 220,
                "messages": [
                    {"role": "system", "content": (
                        f"你是像素小镇『新路谷物语』的居民：{persona} "
                        "用中文回答，口语化，不超过三句话，贴合人设。"
                        "这座小镇映射主人真实的本地工作系统（记忆库/wiki/科研/技能/代码仓库）。")},
                    {"role": "user", "content": message[:500]},
                ],
            },
            timeout=22.0,
        )
        r.raise_for_status()
        return str(r.json()["choices"][0]["message"]["content"]).strip()[:600]
    except Exception:
        return None


def _grounded_reply(agent_id: str, message: str) -> str:
    """No LLM key — answer from real local data, in persona."""
    try:
        if agent_id == "sonnet":
            found = _mcp_call("memory_smart_search", {"query": message[:120], "limit": 3}, timeout=8.0)
            titles = [str(x.get("title", ""))[:40] for x in (found or {}).get("results", [])][:3]
            if titles:
                return "我翻了翻书架，相关的记忆有：" + "；".join(f"《{t}…》" for t in titles) + "。要细看就去馆里的书架。"
            return "书架上暂时没有与此相关的记忆。等这件事做完，记得让它入册。"
        if agent_id == "codex":
            repos = code_panel()["repos"]
            dirty = [r["name"] for r in repos if r.get("dirty")]
            msg = f"镇里 {len(repos)} 个仓库在册"
            return msg + ("，其中未提交的有：" + "、".join(dirty[:4]) + "。先收衣服再下雨。" if dirty else "，全部干净。队列通畅。")
        if agent_id == "opus":
            svcs = townhall_panel()["services"]
            bad = [s["name"] for s in svcs if not s["ok"]]
            return ("镇里各系统运转正常，地基很稳。" if not bad else "有几处需要修缮：" + "、".join(bad) + "。") + "想看细节就到市政厅的大屏。"
        if agent_id == "aris":
            boards = research_panel()["boards"][:3]
            names = "、".join(b["name"] for b in boards)
            return f"研究大厅最近的活跃看板：{names}。结论之前，先问三遍：可复现吗？"
        if agent_id == "pixelcat":
            total = skills_panel()["total"]
            return f"工坊里登记着 {total} 个技能配方喵。你说的这个，要不要锻成一个新配方？"
        if agent_id == "deepseek":
            r = httpx.get(f"{AGENTMEMORY}/agentmemory/memories", params={"count": "true"}, timeout=5.0)
            total = r.json().get("total", "很多") if r.status_code == 200 else "很多"
            return f"记忆海里已经有 {total} 条了。这点活儿？一口吞。"
        if agent_id == "haiku":
            return "收到。马上办。完毕。"
        if agent_id == "fable":
            return "这事让我想起一则寓言：bug 开头，教训收尾。等你做完，我把它写进今天的镇志。"
    except Exception:
        pass
    return "（点点头）这事记下了。回头到对应的建筑里看看吧。"


# ----------------------------------------------------------------- v5: mines
DEBT_EXCLUDE = {"node_modules", "dist", ".git", "art", "workspace", ".vite", "__pycache__", "packs"}
DEBT_EXTS = {".py", ".ts", ".tsx", ".js", ".mjs", ".ps1", ".md", ".gd"}


_DEBT_CACHE: dict = {"at": 0.0, "data": None}


def _scan_debt() -> dict:
    """The actual repo walk (seconds when cold). Kept off the request path
    whenever any cached copy exists — see debt_ores below."""
    import os

    ores: list[dict] = []
    deadline = time.time() + 5.0  # hard budget — this is a game endpoint
    if COMPANY_ROOT.exists():
        for repo in sorted(COMPANY_ROOT.iterdir()):
            if not (repo / ".git").exists() or len(ores) >= 40 or time.time() > deadline:
                continue
            count = 0
            scanned = 0
            for root, dirs, files in os.walk(repo):
                # prune in place so we never descend into node_modules etc.
                dirs[:] = [d for d in dirs if d not in DEBT_EXCLUDE and not d.startswith(".")]
                if count >= 8 or scanned >= 400 or time.time() > deadline:
                    break
                for fname in files:
                    if count >= 8 or scanned >= 400 or time.time() > deadline:
                        break
                    f = Path(root) / fname
                    if f.suffix.lower() not in DEBT_EXTS:
                        continue
                    scanned += 1
                    try:
                        if f.stat().st_size > 300_000:
                            continue
                        text = f.read_text(encoding="utf-8", errors="ignore")
                    except Exception:
                        continue
                    for m in re.finditer(r"(?:#|//|<!--)\s*(TODO|FIXME|HACK)[:\s](.{4,90})", text):
                        kind = m.group(1).lower()
                        ores.append({
                            "id": f"{repo.name}-{len(ores)}",
                            "kind": kind,
                            "title": m.group(2).strip().rstrip("-->").strip()[:80],
                            "file": str(f.relative_to(repo))[:60],
                            "repo": repo.name,
                            "depth": {"todo": 1, "hack": 2, "fixme": 3}.get(kind, 1),
                        })
                        count += 1
                        if count >= 8:
                            break
            # git hotspots: most-touched files of the last 30 days
            if time.time() > deadline:
                continue
            try:
                out = subprocess.run(
                    ["git", "-C", str(repo), "log", "--since=30.days", "--name-only", "--format="],
                    capture_output=True, text=True, timeout=4,
                ).stdout.splitlines()
                from collections import Counter

                hot = Counter(x for x in out if x.strip())
                for fname, n in hot.most_common(4):
                    if n >= 3:
                        ores.append({
                            "id": f"{repo.name}-hot-{len(ores)}",
                            "kind": "hotspot",
                            "title": f"高频改动 {n} 次：{Path(fname).name}",
                            "file": fname[:60],
                            "repo": repo.name,
                            "depth": 2,
                        })
            except Exception:
                pass
    return {"ores": ores}


def _refresh_debt() -> None:
    try:
        _DEBT_CACHE.update(at=time.time(), data=_scan_debt())
    finally:
        _DEBT_CACHE["busy"] = False


@router.get("/debt")
def debt_ores() -> dict:
    """Tech debt as minable ore: TODO/FIXME comments + git hotspot files
    across the company repos. Read-only; paths trimmed to repo-relative.
    Stale-while-revalidate: a request never waits on a re-scan — any cached
    copy serves instantly while a daemon thread refreshes past the 10-min TTL.
    (The mine spawns nodes from this; a 7s wall here read as an empty cave.)"""
    import threading

    now = time.time()
    if _DEBT_CACHE["data"] is not None:
        if now - _DEBT_CACHE["at"] > 600 and not _DEBT_CACHE.get("busy"):
            _DEBT_CACHE["busy"] = True
            threading.Thread(target=_refresh_debt, daemon=True).start()
        return _DEBT_CACHE["data"]
    data = _scan_debt()
    _DEBT_CACHE.update(at=now, data=data)
    return data


@router.get("/logs")
def log_fish() -> dict:
    """Recent local log lines as catchable fish (LIVE only — never public)."""
    fish: list[dict] = []
    sources = [
        Path(r"D:\devtools\logs\agentmemory-selfheal.log"),
        Path(r"D:\devtools\logs\agentmemory-health-errors.log"),
    ]
    job_dir = PROJECT_ROOT / "workspace" / "backend-job-logs"
    if job_dir.exists():
        sources += sorted(job_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:6]
    for src in sources:
        if len(fish) >= 18 or not src.exists():
            continue
        try:
            lines = src.read_text(encoding="utf-8", errors="ignore").strip().splitlines()[-4:]
        except Exception:
            continue
        for ln in lines:
            ln = ln.strip()
            if not ln:
                continue
            level = "ERROR" if re.search(r"error|fail", ln, re.I) else ("WARN" if re.search(r"warn|retry", ln, re.I) else "INFO")
            fish.append({
                "id": f"f{len(fish)}",
                "level": level,
                "text": ln[:110],
                "rarity": {"INFO": 1, "WARN": 2, "ERROR": 3}[level],
                "source": src.name[:40],
            })
    return {"fish": fish}


@router.get("/festival")
def festival() -> dict:
    """Latest GitHub release of this repo — release day = harvest festival."""
    try:
        r = httpx.get(
            "https://api.github.com/repos/appleweiping/newroad-valley/releases/latest",
            timeout=8.0, headers={"Accept": "application/vnd.github+json"},
        )
        if r.status_code == 200:
            data = r.json()
            date = str(data.get("published_at", ""))[:10]
            return {
                "latest": {"tag": data.get("tag_name"), "date": date},
                "today": date == datetime.now().strftime("%Y-%m-%d"),
            }
    except Exception:
        pass
    return {"latest": None, "today": False}


_CHRONICLE_CACHE: dict = {"at": 0.0, "data": None}


@router.get("/chronicle")
def town_chronicle() -> dict:
    """The town chronicle — Fable's book of real history: GitHub releases +
    agentmemory milestones + the founding eras. Cached 10 min."""
    now = time.time()
    if _CHRONICLE_CACHE["data"] is not None and now - _CHRONICLE_CACHE["at"] < 600:
        return _CHRONICLE_CACHE["data"]
    entries: list[dict] = [
        {"date": "2026-05-20", "kind": "era", "title": "v1 · React 原型时代",
         "detail": "第一张地图与随机游走的居民。"},
        {"date": "2026-05-28", "kind": "era", "title": "v2 · Godot 绘本时代",
         "detail": "35 栋建筑的大镇子，后被推翻重来（tag v2-godot-era）。"},
        {"date": "2026-06-11", "kind": "era", "title": "v3 · 星露谷式重生",
         "detail": "迁居 D:\\Company，真像素美术管线落成，小镇换上新名字。"},
    ]
    try:
        r = httpx.get(
            "https://api.github.com/repos/appleweiping/newroad-valley/releases",
            params={"per_page": "20"}, timeout=8.0,
            headers={"Accept": "application/vnd.github+json"},
        )
        if r.status_code == 200:
            for rel in r.json():
                body = str(rel.get("body", "") or "")
                first = next((ln.strip() for ln in body.splitlines() if ln.strip() and not ln.startswith("#")), "")
                entries.append({
                    "date": str(rel.get("published_at", ""))[:10],
                    "kind": "release",
                    "title": str(rel.get("name") or rel.get("tag_name", "")),
                    "detail": first[:110],
                })
    except Exception:
        pass
    try:
        r = httpx.get(
            f"{AGENTMEMORY}/agentmemory/memories",
            params={"project": "newroad-valley", "type": "milestone", "limit": "20"},
            timeout=5.0,
        )
        if r.status_code == 200:
            for m in r.json().get("memories", []):
                content = str(m.get("content", ""))
                entries.append({
                    "date": str(m.get("createdAt", ""))[:10],
                    "kind": "milestone",
                    "title": content.split("。")[0][:60],
                    "detail": content[:140],
                })
    except Exception:
        pass
    entries.sort(key=lambda e: e.get("date", ""), reverse=True)
    data = {"entries": entries[:40]}
    _CHRONICLE_CACHE.update(at=now, data=data)
    return data


@router.get("/signals")
def town_signals(limit: int = 8) -> dict:
    """Recent multi-agent signals relayed from agentmemory (read-only).
    The town shows them live: the receiving NPC runs to the notice board.
    Content is trimmed; this endpoint only ever serves localhost."""
    try:
        r = httpx.get(
            f"{AGENTMEMORY}/agentmemory/signals",
            params={"agentId": "all", "limit": str(max(1, min(limit, 20)))},
            timeout=5.0,
        )
        r.raise_for_status()
        raw = r.json().get("signals", [])
    except Exception:
        return {"signals": []}
    out = []
    for s in raw:
        out.append({
            "id": str(s.get("id", "")),
            "from": str(s.get("from", "")).replace("agent:", ""),
            "to": str(s.get("to", "")).replace("agent:", ""),
            "summary": str(s.get("content", ""))[:120],
            "type": str(s.get("type", "info")),
            "at": str(s.get("createdAt", "")),
        })
    return {"signals": out}


@router.get("/pulse")
def town_pulse() -> dict:
    """The town's heartbeat: total memory count + newest commit per repo.
    One endpoint so the game runs a single poller; cheap on purpose
    (count query + `git log -1` on the three most recent repos)."""
    memory_count = -1
    try:
        r = httpx.get(f"{AGENTMEMORY}/agentmemory/memories", params={"count": "true"}, timeout=4.0)
        if r.status_code == 200:
            d = r.json()
            memory_count = int(d.get("count", d.get("total", -1)))
    except Exception:
        pass

    commits: list[dict] = []
    try:
        if COMPANY_ROOT.exists():
            repos = [p for p in COMPANY_ROOT.iterdir() if (p / ".git").exists()]
            repos.sort(key=lambda p: p.stat().st_mtime, reverse=True)
            for repo in repos[:3]:
                try:
                    out = subprocess.run(
                        ["git", "-C", str(repo), "log", "-1", "--format=%h|%s|%ct"],
                        capture_output=True, text=True, timeout=3,
                    ).stdout.strip()
                    if out:
                        h, msg, ct = (out.split("|", 2) + ["", ""])[:3]
                        commits.append({
                            "repo": repo.name,
                            "hash": h,
                            "msg": msg[:80],
                            "at": int(ct) if ct.isdigit() else 0,
                        })
                except Exception:
                    continue
    except Exception:
        pass
    return {"memoryCount": memory_count, "commits": commits}


# ----------------------------------------------------------------- e2e smoke
REPORT_FILE = PROJECT_ROOT / "workspace" / "v4-report.jsonl"
SHOTS_DIR = PROJECT_ROOT / "workspace" / "v4-shots"


@router.post("/test-report")
def test_report(body: dict) -> dict:
    """In-game smoke harness sink: steps land as JSONL + canvas PNGs on disk,
    so verification survives any browser/tooling crash mid-run."""
    import base64

    REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
    step = str(body.get("step", "?"))[:60]
    entry = {
        "step": step,
        "at": datetime.now().isoformat(timespec="seconds"),
        "data": body.get("data"),
    }
    with REPORT_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    img = body.get("image")
    if isinstance(img, str) and img.startswith("data:image/png;base64,"):
        SHOTS_DIR.mkdir(parents=True, exist_ok=True)
        safe = re.sub(r"[^\w-]", "_", step)
        (SHOTS_DIR / f"{safe}.png").write_bytes(base64.b64decode(img.split(",", 1)[1]))
    return {"ok": True}


@router.post("/dialogue")
def dialogue(body: dict) -> dict:
    agent_id = str(body.get("agentId", ""))
    message = str(body.get("message", "")).strip()
    if not message:
        return {"reply": "（歪了歪头）你想说什么？"}
    reply = _llm_reply(agent_id, message) or _grounded_reply(agent_id, message)
    return {"reply": reply}
