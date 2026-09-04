---
name: "data-processing"
description: "Multimodal OCR receipt extraction, bank PDF statement parser, and CSV statement ingestion using Gemini Vision and PyPDF2."
license: "Apache-2.0"
compatibility: "Python 3.10+"
metadata:
  author: "MoneyChingu"
  version: "1.0.0"
allowed-tools: "Python(PIL:*) Python(pypdf2:*) Python(pandas:*)"
---

# Data Processing Skill

## Overview
The **data-processing** skill handles ingestion of raw, unstructured financial documents—including paper receipts, digital invoice photos, multi-page PDF bank statements, and CSV exports. It extracts structured records and passes them to Human-in-the-Loop review.

## Core Capabilities
- **Receipt Vision OCR**: Parses merchant name, transaction date, line items, taxes, currency, and total amount using Google Gemini Vision with automatic model fallback.
- **PDF Bank Statement Parser**: Extracts text chunks from PDF bank statements using `PyPDF2` and structures them into tabular rows.
- **CSV Bank Ingestion**: Automatically detects headers, date columns, and amounts from standard bank and credit card CSV exports using `pandas`.

## Directory Structure
```
data-processing/
├── SKILL.md
├── scripts/
│   └── process_docs.py
└── references/
    └── api-reference.md
```

## Step-by-Step Usage

### 1. Extracting Receipt Images
```python
from PIL import Image
from skills import data_processing_skill

with open("receipt.jpg", "rb") as f:
    result = data_processing_skill.process_receipt_image(f)
```

### 2. Parsing Bank Statement PDFs
```python
with open("statement.pdf", "rb") as f:
    result = data_processing_skill.process_bank_pdf(f)
```

For complete parameter specifications, see [API Reference](references/api-reference.md).
