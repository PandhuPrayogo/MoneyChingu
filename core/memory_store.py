from typing import List, Dict, Any, Optional
from datetime import datetime
from database.db import db

class MemoryStore:
    """
    Context Engineering - External State Persistence Layer.
    Manages three classes of long-term agent memory:
    1. Episodic: Summaries of past tool actions and outcomes
    2. Semantic: Stated user facts, profile attributes, and domain knowledge
    3. Procedural: Operational directives and learned behavioral rules
    """
    def __init__(self):
        pass

    def store_episodic(self, action_name: str, summary: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Store condensed tool action outcome."""
        meta = metadata or {}
        meta["action"] = action_name
        meta["date"] = datetime.now().strftime("%Y-%m-%d %H:%M")
        return db.store_memory(
            memory_type="episodic",
            content=f"[{action_name}] {summary}",
            metadata=meta
        )

    def store_semantic(self, fact: str, category: str = "user_preference", metadata: Optional[Dict[str, Any]] = None) -> str:
        """Store user or domain fact (e.g. preferred currency, user name)."""
        meta = metadata or {}
        meta["category"] = category
        return db.store_memory(
            memory_type="semantic",
            content=fact,
            metadata=meta
        )

    def store_procedural(self, rule: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Store standing behavioral directive (e.g. format preference, tone rules)."""
        return db.store_memory(
            memory_type="procedural",
            content=rule,
            metadata=metadata or {}
        )

    def retrieve_memories(self, query: str, memory_types: Optional[List[str]] = None, top_k: int = 3) -> List[Dict[str, Any]]:
        """Retrieve relevant memories matching query or latest active memories."""
        if query:
            results = db.search_memories(query=query, memory_types=memory_types, limit=top_k)
            if results:
                return results
        # Fallback to most recently accessed memories of matching types
        all_recent = []
        types = memory_types or ["semantic", "procedural", "episodic"]
        for m_type in types:
            all_recent.extend(db.get_memories_by_type(m_type, limit=2))
        all_recent.sort(key=lambda x: x.get("accessed_at", ""), reverse=True)
        return all_recent[:top_k]

    def format_memories_for_prompt(self, memories: List[Dict[str, Any]]) -> str:
        """Render memories cleanly into compact XML block."""
        if not memories:
            return ""
        lines = []
        for m in memories:
            m_type = m.get("memory_type", "fact").upper()
            content = m.get("content", "").strip()
            lines.append(f"- [{m_type}] {content}")
        return "<memories>\n" + "\n".join(lines) + "\n</memories>"

    def evict_stale(self, max_age_days: int = 30) -> int:
        """Cleanup old episodic records."""
        return db.evict_stale_memories(max_age_days=max_age_days)

# Global singleton
memory_store = MemoryStore()
