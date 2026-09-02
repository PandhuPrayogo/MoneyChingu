from typing import Dict, Any, List, Optional
from config import AGENT_NAME, DEFAULT_EXPENSE_CATEGORIES, DEFAULT_INCOME_CATEGORIES, USD_TO_IDR_RATE

SYSTEM_PROMPT_TEMPLATE = f"""<role>
You are {AGENT_NAME}, an expert, witty AI Financial Assistant.
You combine rigorous financial accuracy with natural, friendly banter (using light humor on impulsive spending and hyping up savings). Bilingual in English and Indonesian.
</role>

<rules>
1. Dual currency: USD ($) & IDR (Rp). 1 USD ≈ {USD_TO_IDR_RATE:,.0f} IDR.
2. Ground all numbers strictly in the provided financial context. Never hallucinate balances.
3. For summaries/reports, format with clean markdown tables and bold numbers.
</rules>

<categories>
Expense: {', '.join(DEFAULT_EXPENSE_CATEGORIES)}
Income: {', '.join(DEFAULT_INCOME_CATEGORIES)}
</categories>

<tools>
- data_management:
  * action='add_transaction': date, amount, currency, category, type ('expense'/'income'), merchant, description, account_id
  * action='edit_transaction': tx_id, amount, category, merchant, date, type
  * action='delete_transaction': tx_id
  * action='list_transactions': limit, category, month
  * action='search_transactions': query, category, min_amount, max_amount
  * action='get_accounts'
  * action='add_account': account_name, account_type ('cash'/'bank'/'e_wallet'/'credit_card'), currency, balance
  * action='delete_account': account_id
  * action='transfer_funds': from_account_id, to_account_id, amount, currency, description
  * action='set_budget': category, monthly_limit, currency, date
  * action='get_budgets': month
  * action='clear_database'
  * action='export_csv'
- financial_analytics:
  * analysis_type='monthly_summary'|'budget_status'|'net_worth'|'convert_currency'|'spending_insights'|'generate_full_report'
- data_processing: multimodal OCR, PDF statement parsing, CSV ETL
- rag_context: query
- huggingface_tools: zero-shot classification & financial sentiment
</tools>

<format>
If tool required:
<tool_call>
{{"skill": "skill_name", "parameters": {{ ... }}}}
</tool_call>

<message>
Your response here.
</message>
</format>
"""

def format_system_prompt_with_context(context_snapshot: Dict[str, Any], retrieved_memories: Optional[List[Dict[str, Any]]] = None) -> str:
    """Inject real-time SQLite financial context and silent RAG memories into the prompt."""
    accounts = [f"{a['name']}: {a['balance']:,.2f} {a['currency']}" for a in context_snapshot.get("accounts", [])]
    accounts_str = " | ".join(accounts) if accounts else "None"
    
    recent_tx = [
        f"[{t['date']}] {t['type'].upper()} {t['amount']:,.2f} {t['currency']} ({t['category']}/{t.get('merchant','-')}) ID:{t['id']}"
        for t in context_snapshot.get("recent_transactions", [])[:6]
    ]
    recent_tx_str = "\n".join(recent_tx) if recent_tx else "Ledger at zero."
    
    m = context_snapshot.get("monthly_summary", {})
    summary_str = f"Income: {m.get('total_income',0):,.2f} {m.get('currency','USD')} | Expense: {m.get('total_expense',0):,.2f} | Savings: {m.get('net_savings',0):,.2f}"

    memories_str = ""
    if retrieved_memories:
        mem_lines = [
            f"- [{x.get('doc_type','doc').upper()}] {x.get('text','')} ({x.get('similarity_score',0):.2f})"
            for x in retrieved_memories if x.get('similarity_score', 0) > 0.35
        ]
        if mem_lines:
            joined = "\n".join(mem_lines)
            memories_str = f"\n<retrieved_memories>\n{joined}\n</retrieved_memories>"

    return f"""{SYSTEM_PROMPT_TEMPLATE}

<context>
Date: {context_snapshot.get('current_date')}
Accounts: {accounts_str}
Recent Transactions:
{recent_tx_str}
Month Summary: {summary_str}{memories_str}
</context>
"""
