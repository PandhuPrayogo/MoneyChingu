# RAG Context API Reference

## Operations & Parameters

| Operation | Parameters | Returns |
| :--- | :--- | :--- |
| `execute(query=..., top_k=3)` | `query` (str), `top_k` (int, default=3) | List of matching documents with `similarity_score`, `doc_type`, and `metadata` |
