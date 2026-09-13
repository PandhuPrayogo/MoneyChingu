import re
from typing import Dict, Any, List, Set

class IntentRouter:
    """
    Context Engineering - Just-in-Time Context Assembly (SELECT).
    Classifies user intent (bilingual English + Indonesian) and dynamically
    assembles only 3-5 candidate tool schemas instead of 20+ full schemas.
    Prevents Context Confusion (Combinatorial Schema Interference).
    """

    INTENT_KEYWORDS = {
        "query_balance": [
            r"\b(balance|balances|saldo|rekening|account|accounts|how much (money|do i have)|sisa uang|uangku)\b"
        ],
        "add_expense": [
            r"\b(spent|spend|bought|buy|paid|pay|beli|bayar|pengeluaran|belanja|keluar|habis)\b"
        ],
        "add_income": [
            r"\b(earned|earn|salary|gaji|income|pemasukan|dapet|dapat|terima uang|received)\b"
        ],
        "financial_report": [
            r"\b(report|laporan|summary|ringkasan|financial health|evaluasi|net worth|breakdown|rekap|insight)\b"
        ],
        "budget_management": [
            r"\b(budget|budgets|anggaran|limit|overspend|burn rate|kuota)\b"
        ],
        "ledger_management": [
            r"\b(edit|ubah|ganti|delete|hapus|remove|transfer|kirim saldo|pindah saldo|move funds)\b"
        ],
        "transaction_search": [
            r"\b(search|cari|find|list transactions|recent transactions|riwayat|histori|daftar transaksi)\b"
        ],
        "user_preference": [
            r"\b(my name|namaku|nama saya|call me|panggil aku|your name|namamu|nama kamu|remember|ingat)\b"
        ],
        "destructive_action": [
            r"\b(remove|clear|wipe|reset|delete all|hapus semua|bersihkan|kosongkan|nuke|hapus riwayat|remove all history|delete transactions|clear history|clear database|hapus database)\b"
        ]
    }

    # Tool Schema Registry (Compact definitions for dynamic injection)
    TOOL_SIGNATURES = {
        "get_accounts": "- data_management: action='get_accounts' (retrieve balances of all accounts)",
        "add_account": "- data_management: action='add_account': account_name, account_type ('cash'/'bank'/'e_wallet'), currency ('USD'/'IDR'), balance",
        "delete_account": "- data_management: action='delete_account': account_id",
        "add_transaction": "- data_management: action='add_transaction': amount, currency ('USD'/'IDR'), category, type ('expense'/'income'), date, merchant, description, account_id",
        "edit_transaction": "- data_management: action='edit_transaction': tx_id, amount, category, merchant, date, type",
        "delete_transaction": "- data_management: action='delete_transaction': tx_id",
        "list_transactions": "- data_management: action='list_transactions': limit, category, month",
        "search_transactions": "- data_management: action='search_transactions': query, category, min_amount, max_amount",
        "transfer_funds": "- data_management: action='transfer_funds': from_account_id, to_account_id, amount, currency, description",
        "set_budget": "- data_management: action='set_budget': category, monthly_limit, currency, date",
        "get_budgets": "- data_management: action='get_budgets': month",
        "clear_database": "- data_management: action='clear_database' (resets all ledger transactions, accounts, and history to zero)",
        "export_csv": "- data_management: action='export_csv' (export full transaction history as CSV before deleting)",
        "set_preference": "- data_management: action='set_preference': key, value (e.g. user_name, ai_name)",
        "get_preferences": "- data_management: action='get_preferences'",
        "generate_full_report": "- financial_analytics: analysis_type='generate_full_report' (complete net worth, savings rate, breakdown)",
        "monthly_summary": "- financial_analytics: analysis_type='monthly_summary' (inflow, outflow, savings)",
        "budget_status": "- financial_analytics: analysis_type='budget_status' (budget burn rates and remaining limits)",
        "net_worth": "- financial_analytics: analysis_type='net_worth' (aggregated net worth across all currencies)",
        "spending_insights": "- financial_analytics: analysis_type='spending_insights' (anomalies and high spending areas)",
        "classify_expense": "- huggingface_tools: action='classify_expense': text (predict category)"
    }

    # Mapping from classified intent to relevant tool keys
    INTENT_TOOL_MAPPING = {
        "query_balance": ["get_accounts", "net_worth", "list_transactions"],
        "add_expense": ["add_transaction", "classify_expense", "get_accounts", "set_budget"],
        "add_income": ["add_transaction", "get_accounts"],
        "financial_report": ["generate_full_report", "monthly_summary", "budget_status", "net_worth", "spending_insights"],
        "budget_management": ["get_budgets", "set_budget", "budget_status"],
        "ledger_management": ["edit_transaction", "delete_transaction", "transfer_funds", "delete_account"],
        "transaction_search": ["search_transactions", "list_transactions"],
        "user_preference": ["set_preference", "get_preferences"],
        "destructive_action": ["clear_database", "delete_transaction", "delete_account", "export_csv"],
        "general_chat": ["get_accounts", "generate_full_report"]
    }

    # Memory types needed per intent
    INTENT_MEMORY_MAPPING = {
        "query_balance": ["semantic", "episodic"],
        "add_expense": ["procedural", "semantic"],
        "add_income": ["procedural", "semantic"],
        "financial_report": ["episodic", "procedural"],
        "budget_management": ["procedural", "semantic"],
        "ledger_management": ["episodic", "semantic"],
        "transaction_search": ["episodic", "semantic"],
        "user_preference": ["semantic", "procedural"],
        "destructive_action": ["episodic", "procedural"],
        "general_chat": ["semantic", "procedural"]
    }

    def classify_intent(self, user_message: str) -> List[str]:
        """Classify message into matching intent categories."""
        msg_lower = user_message.lower()
        matched_intents = []

        for intent, patterns in self.INTENT_KEYWORDS.items():
            for pat in patterns:
                if re.search(pat, msg_lower, re.IGNORECASE):
                    matched_intents.append(intent)
                    break

        if not matched_intents:
            matched_intents.append("general_chat")

        return matched_intents

    def get_candidate_tools(self, intents: List[str]) -> List[str]:
        """Select 3-5 high-relevance tool schemas matching user intents."""
        selected_tool_keys: Set[str] = set()

        for intent in intents:
            tools = self.INTENT_TOOL_MAPPING.get(intent, [])
            for t in tools:
                selected_tool_keys.add(t)

        # Ensure we don't exceed 6 candidate tools to avoid schema confusion
        candidate_keys = list(selected_tool_keys)[:6]
        if not candidate_keys:
            candidate_keys = ["get_accounts", "add_transaction"]

        return [self.TOOL_SIGNATURES[k] for k in candidate_keys if k in self.TOOL_SIGNATURES]

    def get_required_memory_types(self, intents: List[str]) -> List[str]:
        """Identify which memory types are relevant for the turn."""
        mem_types: Set[str] = set()
        for intent in intents:
            types = self.INTENT_MEMORY_MAPPING.get(intent, ["semantic"])
            for t in types:
                mem_types.add(t)
        return list(mem_types)

# Global singleton
intent_router = IntentRouter()
