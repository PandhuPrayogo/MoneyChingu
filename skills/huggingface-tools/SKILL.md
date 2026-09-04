---
name: "huggingface-tools"
description: "Zero-shot transaction categorization and financial health sentiment analysis using HuggingFace NLP conventions."
license: "Apache-2.0"
compatibility: "Python 3.10+"
metadata:
  author: "MoneyChingu"
  version: "1.0.0"
allowed-tools: "Python(transformers:*) Python(huggingface_hub:*)"
---

# Hugging Face Tools Skill

## Overview
The **huggingface-tools** skill provides natural language understanding capabilities aligned with Hugging Face open-source models for expense categorization and financial sentiment scoring.

## Core Capabilities
- **Zero-Shot Categorization**: Classifies ambiguous transaction descriptions (e.g. "Starbucks caramel macchiato", "Uber trip", "Netflix sub") into canonical expense categories.
- **Financial Sentiment Analysis**: Analyzes financial sentiment from purchase patterns and notes.

## Directory Structure
```
huggingface-tools/
├── SKILL.md
├── scripts/
│   └── classify.py
└── references/
    └── api-reference.md
```

## Step-by-Step Usage

### 1. Categorizing Transaction Text
```python
from skills import hf_skill

result = hf_skill.execute(
    action="classify_expense",
    text="Hot latte at Starbucks"
)
```

### 2. Financial Sentiment
```python
sentiment = hf_skill.execute(
    task="financial_sentiment",
    text="Savings are growing, feeling financially secure!"
)
```

For complete parameter specifications, see [API Reference](references/api-reference.md).
