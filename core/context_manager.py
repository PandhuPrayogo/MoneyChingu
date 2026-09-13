import re
from typing import Dict, Any, List, Optional
from datetime import datetime
from database.db import db
from config import DEFAULT_CURRENCY

class ContextManager:
    """
    Context Engineering - Token Pruning & Lifecycle Eviction (COMPRESS).
    Implements a 3-phase compression architecture:
    1. Pre-Injection: Strips scratchpads, trims bloated outputs
    2. In-Flight: Hybrid sliding window (recent verbatim + rolling extractive summary)
    3. Post-Action: Evicts raw table/data dumps to 1-line status records
    """
    def __init__(self, verbatim_turns: int = 4, max_msg_chars: int = 1500):
        self.verbatim_turns = verbatim_turns
        self.max_msg_chars = max_msg_chars

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
        user_preferences = db.get_all_preferences()

        return {
            "current_date": current_date,
            "current_month": current_month,
            "display_currency": display_currency,
            "accounts": accounts,
            "recent_transactions": recent_txs,
            "monthly_summary": monthly_summary,
            "budgets": budgets,
            "user_preferences": user_preferences
        }

    def estimate_tokens(self, text: str) -> int:
        """Heuristic token estimation (~4 characters per token)."""
        return max(1, len(text) // 4)

    def prepare_history_for_injection(self, history: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """
        Pre-injection pruning:
        - Strip scratchpad tags from assistant messages
        - Enforce character caps on single verbose turns
        - Keep recent sliding window turns intact
        """
        if not history:
            return []

        # Keep last verbatim messages (e.g. last 4 conversational turns = 8 messages)
        verbatim_count = self.verbatim_turns * 2
        recent_msgs = history[-verbatim_count:]

        pruned_history = []
        for msg in recent_msgs:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            # 1. Strip <scratchpad> reasoning blocks from assistant messages
            if role == "assistant" and "<scratchpad>" in content:
                content = re.sub(r"<scratchpad>.*?</scratchpad>", "", content, flags=re.DOTALL).strip()

            # 2. Compress verbose historical markdown tables in older assistant turns
            if len(content) > self.max_msg_chars:
                content = content[:self.max_msg_chars] + "... [truncated for context efficiency]"

            pruned_history.append({"role": role, "content": content})

        return pruned_history

    def get_conversation_summary(self, history: List[Dict[str, str]]) -> str:
        """
        Extract rolling semantic summary of conversation turns that have fallen
        outside the verbatim sliding window buffer.
        """
        verbatim_count = self.verbatim_turns * 2
        if len(history) <= verbatim_count:
            return ""

        older_msgs = history[:-verbatim_count]
        extracted_facts = []

        for msg in older_msgs:
            role = msg.get("role", "user")
            content = msg.get("content", "").strip()

            if role == "user":
                # Extract key user intent or directive
                clean = content.replace("\n", " ")[:100]
                if clean:
                    extracted_facts.append(f"User requested: '{clean}'")
            elif role == "assistant":
                # Check for recorded actions
                if "Confirmed and saved" in content or "recorded successfully" in content:
                    m = re.search(r"(saved|recorded)\s+([A-Z]+:\s+[^\.]+)", content)
                    if m:
                        extracted_facts.append(f"System logged: {m.group(2)}")
                elif "Your Account Balances" in content:
                    extracted_facts.append("System displayed account balances.")
                elif "Financial Health Report" in content:
                    extracted_facts.append("System delivered full financial report.")

        if not extracted_facts:
            return ""

        # Deduplicate while preserving order, cap at 5 key points
        unique_facts = list(dict.fromkeys(extracted_facts))[-5:]
        lines = [f"- {fact}" for fact in unique_facts]
        return "<conversation_summary>\n" + "\n".join(lines) + "\n</conversation_summary>"

    def evict_tool_output(self, raw_content: str) -> str:
        """
        Post-action eviction:
        Condense massive data tables into concise 1-line confirmations
        for safe long-term storage in session memory.
        """
        if "### 💳 Your Account Balances" in raw_content:
            return "💳 [Displayed live account balances]"
        if "### 📊 Full Financial Health Report" in raw_content:
            return "📊 [Delivered full financial health and net worth report]"
        if "### 📈 Monthly Financial Summary" in raw_content:
            return "📈 [Generated monthly income, expense & savings summary]"
        if "### 🎯 Monthly Budget" in raw_content:
            return "🎯 [Displayed monthly category budget limits and burn rates]"
        if "### 📒 Recent Transactions" in raw_content:
            return "📒 [Listed recent ledger transactions]"

        # Default: if text is over 500 chars, truncate
        if len(raw_content) > 500:
            return raw_content[:300] + "... [data summary]"

        return raw_content

context_manager = ContextManager()
