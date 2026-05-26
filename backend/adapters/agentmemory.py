import json
import time
from pathlib import Path
from config import AGENTMEMORY_DB

STANDALONE_PATH = Path.home() / ".agentmemory" / "standalone.json"


class AgentMemoryAdapter:
    def __init__(self):
        self._cache: dict = {}
        self._cache_time: float = 0
        self._ttl: float = 30.0

    async def refresh(self):
        now = time.time()
        if now - self._cache_time < self._ttl:
            return
        self._cache_time = now

        if not STANDALONE_PATH.exists():
            return

        try:
            raw = STANDALONE_PATH.read_text(encoding="utf-8")
            data = json.loads(raw)

            memories = []
            if "mem:memories" in data:
                for mid, mem in data["mem:memories"].items():
                    memories.append({
                        "id": mem.get("id", mid),
                        "type": mem.get("type", "unknown"),
                        "title": mem.get("title", "")[:120],
                        "concepts": mem.get("concepts", []),
                        "createdAt": mem.get("createdAt", ""),
                        "strength": mem.get("strength", 0),
                    })

            memories.sort(key=lambda m: m.get("createdAt", ""), reverse=True)
            self._cache["memories"] = memories
            self._cache["total_count"] = len(memories)

            type_counts: dict[str, int] = {}
            all_concepts: dict[str, int] = {}
            for m in memories:
                t = m.get("type", "unknown")
                type_counts[t] = type_counts.get(t, 0) + 1
                for c in m.get("concepts", []):
                    all_concepts[c] = all_concepts.get(c, 0) + 1

            self._cache["type_counts"] = type_counts
            top_concepts = sorted(all_concepts.items(), key=lambda x: x[1], reverse=True)[:15]
            self._cache["top_concepts"] = [c[0] for c in top_concepts]

        except Exception as e:
            print(f"[agentmemory] refresh error: {e}")

    def get_recent_memories(self, limit: int = 10) -> list[dict]:
        return self._cache.get("memories", [])[:limit]

    def get_total_count(self) -> int:
        return self._cache.get("total_count", 0)

    def get_type_counts(self) -> dict[str, int]:
        return self._cache.get("type_counts", {})

    def get_top_concepts(self) -> list[str]:
        return self._cache.get("top_concepts", [])

    # Legacy compat
    def get_recent_sessions(self) -> list[dict]:
        return self.get_recent_memories(5)

    def get_recent_observations(self) -> list[dict]:
        return []

    def get_lessons(self) -> list[dict]:
        return []

    @property
    def is_available(self) -> bool:
        return STANDALONE_PATH.exists()
