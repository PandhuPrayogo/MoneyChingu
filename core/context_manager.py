from typing import Dict, Any, List
from datetime import datetime
from database.db import db
from config import DEFAULT_CURRENCY

class ContextManager:
    """
    Google-Standard Context Engineering:
    Manages live data grounding, conversation buffers, and token budgets.
    """
    def __init__(self, max_history_turns: int = 8):
        self.max_history_turns = max_history_turns

    def get_live_context_snapshot(self, display_currency: str = DEFAULT_CURRENCY) -> Dict[str, Any]:
        """
        Extract high-fidelity snapshot of user's financial state from SQLite.
        Provides ground truth for preventing hallucinations.
        """
        current_date = datetime.now().strftime("%Y-%m-%d %H:%M")
        current_month = datetime.now().strftime("%Y-%m")

        accounts = db.get_accounts()
        recent_txs = db.get_transactions(limit=6)
        monthly_summary = db.get_monthly_summary(current_month, display_currency=display_currency)
        budgets = db.get_budgets(current_month)

        return {
            "current_date": current_date,
            "current_month": current_month,
            "display_currency": display_currency,
            "accounts": accounts,
            "recent_transactions": recent_txs,
            "monthly_summary": monthly_summary,
            "budgets": budgets
        }

    def trim_history(self, history: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Keep recent conversation turns within token limits."""
        if len(history) > self.max_history_turns:
            return history[-self.max_history_turns:]
        return history

context_manager = ContextManager()
