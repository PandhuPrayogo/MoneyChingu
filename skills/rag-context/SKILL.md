---
name: "rag-context"
description: "Retrieves relevant financial memories, receipts, and past transactions via vector embeddings and cosine similarity search."
license: "Apache-2.0"
compatibility: "Python 3.10+"
metadata:
  author: "MoneyChingu"
  version: "1.0.0"
allowed-tools: "Python(database.vector_store:*)"
---

# RAG Context Skill

## Overview
The **rag-context** skill manages long-term semantic memory for MoneyChingu. It embeds past receipt OCR outputs, notes, and transactions using Google `text-embedding-004` (with offline fallback), and performs cosine similarity search.

## Core Capabilities
- **Semantic Retrieval**: Searches memory documents by natural language query (e.g. "where did I buy that jacket").
- **Silent Context Injection**: Integrates automatically with the ReAct agent prompt to provide memory context on every turn.
- **Dynamic Scoring**: Filters memories using a cosine similarity threshold ($> 0.35$).

## Directory Structure
```
rag-context/
├── SKILL.md
├── scripts/
│   └── search_memory.py
└── references/
    └── api-reference.md
```

## Step-by-Step Usage

### 1. Searching Semantic Memory
```python
from skills import rag_context_skill

results = rag_context_skill.execute(
    query="sushi dinner",
    top_k=3
)
```

For complete parameter specifications, see [API Reference](references/api-reference.md).
