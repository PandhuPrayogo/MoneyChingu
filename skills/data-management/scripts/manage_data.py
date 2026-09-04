"""
Data Management Helper Script:
Direct programmatic access to MoneyChingu SQLite operations.
"""
from database.db import db

def get_ledger_summary():
    """Return quick stats of accounts and transactions count."""
    accounts = db.get_accounts()
    txs = db.get_transactions(limit=10)
    return {
        "accounts_count": len(accounts),
        "recent_tx_count": len(txs),
        "accounts": accounts
    }

if __name__ == "__main__":
    print(get_ledger_summary())
