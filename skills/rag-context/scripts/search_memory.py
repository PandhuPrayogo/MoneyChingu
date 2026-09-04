"""
RAG Context Helper Script:
Searches vector store for semantic matches.
"""
from skills.rag_context import rag_context_skill

def search(query: str, top_k: int = 3):
    return rag_context_skill.execute(query=query, top_k=top_k)

if __name__ == "__main__":
    import sys
    q = sys.argv[1] if len(sys.argv) > 1 else "lunch"
    print(search(q))
