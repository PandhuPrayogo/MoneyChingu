---
name: "financial-analytics"
description: "Calculates monthly summaries, cash flows, category spending velocity, budget limits, currency conversions, and financial health reports."
license: "Apache-2.0"
compatibility: "Python 3.10+"
metadata:
  author: "MoneyChingu"
  version: "1.0.0"
allowed-tools: "Python(database.db:*)"
---

# Financial Analytics Skill

## Overview
The **financial-analytics** skill performs quantitative financial calculations, budget tracking, currency conversions (USD and IDR), and generates comprehensive cash flow reports.

## Core Capabilities
- **Full Health Report**: Aggregates Net Worth, Inflow, Outflow, Net Savings, Savings Rate (%), and Budget Health in clean tabular format.
- **Monthly Summary**: Calculates monthly totals and category-by-category breakdown with automated currency unification.
- **Budget Burn Rate**: Tracks percentage consumed for each category and flags categories nearing or exceeding limits.
- **Dual-Currency Conversion**: Converts between USD ($) and IDR (Rp) using configured real-time rates.
- **Spending Velocity & Insights**: Identifies anomalies, large purchases, and spending momentum.

## Directory Structure
```
financial-analytics/
├── SKILL.md
├── scripts/
│   └── analytics.py
└── references/
    └── api-reference.md
```

## Step-by-Step Usage

### 1. Generating a Full Report
```python
from skills import financial_analytics_skill

report = financial_analytics_skill.execute(
    analysis_type="generate_full_report",
    month_year="2026-09",
    currency="USD"
)
```

### 2. Checking Budget Status
```python
budget_status = financial_analytics_skill.execute(
    analysis_type="budget_status",
    month_year="2026-09",
    currency="USD"
)
```

### 3. Converting Currency
```python
converted = financial_analytics_skill.execute(
    analysis_type="convert_currency",
    amount=50.0,
    from_currency="USD",
    to_currency="IDR"
)
```

For complete parameter specifications, see [API Reference](references/api-reference.md).
