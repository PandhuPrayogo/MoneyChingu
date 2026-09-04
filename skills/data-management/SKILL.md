---
name: "data-management"
description: "Executes transactions creation, balance reconciliation, deletions, account management, and ledger exports in SQLite."
license: "Apache-2.0"
compatibility: "Python 3.10+"
metadata:
  author: "MoneyChingu"
  version: "1.0.0"
allowed-tools: "Python(database.db:*)"
---

# Data Management Skill

## Overview
The **data-management** skill provides transactional ACID operations on the MoneyChingu SQLite financial ledger. It manages accounts, transactions, category budgets, balance reconciliations, and CSV exports.

## Core Capabilities
- **Transaction CRUD**: Add, edit, delete, and list transactions with real-time account balance updates.
- **Fund Transfers**: Transfer money between two distinct accounts (e.g. Bank to Cash or E-Wallet) with atomic double-entry updates.
- **Multi-Field Search**: Filter transactions by merchant, category, date range, and min/max amount.
- **Account Management**: Create, view, and delete accounts (Cash, Bank, E-Wallet, Credit Card).
- **Budget Control**: Set and query monthly spending limits per category.
- **Ledger Export & Reset**: Export entire ledger history to CSV or reset to a clean zero state.

## Directory Structure
```
data-management/
├── SKILL.md
├── scripts/
│   └── manage_data.py
└── references/
    └── api-reference.md
```

## Step-by-Step Usage

### 1. Adding a Transaction
To add an expense or income, provide the amount, currency, category, and target account.
```python
from skills import data_management_skill

result = data_management_skill.execute(
    action="add_transaction",
    date="2026-09-04",
    amount=25.50,
    currency="USD",
    category="Food & Dining",
    type="expense",
    merchant="Chipotle",
    description="Lunch burrito"
)
```

### 2. Transferring Funds Between Accounts
```python
result = data_management_skill.execute(
    action="transfer_funds",
    from_account_id="acc_bank",
    to_account_id="acc_cash",
    amount=100.0,
    currency="USD",
    description="ATM withdrawal"
)
```

### 3. Setting Category Budgets
```python
result = data_management_skill.execute(
    action="set_budget",
    category="Groceries",
    monthly_limit=400.0,
    currency="USD",
    date="2026-09"
)
```

For complete parameter specifications, see [API Reference](references/api-reference.md).
