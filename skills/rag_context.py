from typing import Dict, Any, List, Optional
from skills.base import BaseSkill
from database.vector_store import vector_store

class RAGContextSkill(BaseSkill):
    """
    RAG Context Skill: Performs semantic retrieval across past receipts, notes,
    and historical transaction details using vector similarity.
    """
    name = "rag_context"
    description = "Searches long-term financial memory and receipt notes using semantic vector search."
    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The natural language query or description to search for"
            },
            "top_k": {
                "type": "integer",
                "description": "Number of top relevant memory results to return (default 4)"
            }
        },
        "required": ["query"]
    }

    def execute(self, **kwargs) -> Dict[str, Any]:
        query = kwargs.get("query", "")
        top_k = int(kwargs.get("top_k", 4))
        
        if not query:
            return {"status": "error", "message": "Query parameter is required."}

        results = vector_store.search(query=query, top_k=top_k)
        return {
            "status": "success",
            "query": query,
            "results_count": len(results),
            "relevant_memories": results
        }

rag_context_skill = RAGContextSkill()
