from typing import Dict, Any, List, Optional
from config import AGENT_NAME, DEFAULT_EXPENSE_CATEGORIES, DEFAULT_INCOME_CATEGORIES, USD_TO_IDR_RATE

ROLE_BLOCK = f"""<role>
You are {AGENT_NAME}, an expert, witty AI Financial Assistant.
You combine rigorous financial accuracy with natural, friendly banter (using light humor on impulsive spending and hyping up savings). Bilingual in English and Indonesian.
</role>"""

AUTHORITY_BLOCK = """<authority>
Priority Hierarchy (Strict Precedence):
1. <rules> — Immutable financial rules & constraints.
2. <context> — Live SQLite ground truth. Authoritative for balances and transactions.
3. <user_profile> — User preferences & identity constraints.
4. <memories> — Long-term episodic/semantic notes (supplementary).
5. <conversation_summary> — Historical summary of earlier turns (supplementary).
RULE: When any conflict arises, higher-priority blocks ALWAYS override lower ones!
</authority>"""

RULES_BLOCK = f"""<rules>
1. Dual currency: USD ($) & IDR (Rp). 1 USD ≈ {USD_TO_IDR_RATE:,.0f} IDR.
2. Ground all numbers strictly in <context>. Never hallucinate balances.
3. For summaries/reports, format with clean markdown tables and bold numbers.
4. For destructive or irreversible actions (clear_database, delete_transaction, delete_account, transfer_funds), always state clearly what will be affected; Human-in-the-Loop confirmation will be requested.
</rules>"""

CATEGORIES_BLOCK = f"""<categories>
Expense: {', '.join(DEFAULT_EXPENSE_CATEGORIES)}
Income: {', '.join(DEFAULT_INCOME_CATEGORIES)}
</categories>"""

FORMAT_BLOCK = """<format>
If tool required:
<tool_call>
{"skill": "skill_name", "parameters": { ... }}
</tool_call>

<message>
Your response here.
</message>
</format>"""

DEFAULT_TOOLS = [
    "- data_management: action='get_accounts' (view account balances)",
    "- data_management: action='add_transaction': amount, currency, category, type ('expense'/'income'), merchant, date",
    "- financial_analytics: analysis_type='generate_full_report'|'monthly_summary'|'net_worth'"
]

def build_system_prompt(
    context_snapshot: Dict[str, Any],
    candidate_tools: Optional[List[str]] = None,
    conversation_summary: Optional[str] = None,
    retrieved_memories: Optional[List[Dict[str, Any]]] = None
) -> str:
    """
    Context Engineering - Layered System Prompt Assembly.
    Prevents Context Confusion by injecting only 3-5 relevant candidate tools.
    Prevents Context Clash via explicit <authority> ordering.
    """
    # 1. Candidate tools formatting (Dynamic Tool RAG)
    tools_to_inject = candidate_tools if candidate_tools else DEFAULT_TOOLS
    tools_section = "<tools>\n" + "\n".join(tools_to_inject) + "\n</tools>"

    # 2. Live Context snapshot formatting
    accounts = [f"{a['name']}: {a['balance']:,.2f} {a['currency']}" for a in context_snapshot.get("accounts", [])]
    accounts_str = " | ".join(accounts) if accounts else "None"
    
    recent_tx = [
        f"[{t['date']}] {t['type'].upper()} {t['amount']:,.2f} {t['currency']} ({t['category']}/{t.get('merchant','-')}) ID:{t['id']}"
        for t in context_snapshot.get("recent_transactions", [])[:6]
    ]
    recent_tx_str = "\n".join(recent_tx) if recent_tx else "Ledger at zero."
    
    m = context_snapshot.get("monthly_summary", {})
    summary_str = f"Income: {m.get('total_income',0):,.2f} {m.get('currency','USD')} | Expense: {m.get('total_expense',0):,.2f} | Savings: {m.get('net_savings',0):,.2f}"

    # 3. User profile formatting
    prefs = context_snapshot.get("user_preferences", {})
    profile_items = []
    if "user_name" in prefs:
        profile_items.append(f"User Name: {prefs['user_name']}")
    if "ai_name" in prefs:
        profile_items.append(f"Your AI Persona Name: {prefs['ai_name']}")
    for k, v in prefs.items():
        if k not in ("user_name", "ai_name"):
            profile_items.append(f"{k}: {v}")
    profile_str = f"\nProfile: {', '.join(profile_items)}" if profile_items else ""

    context_section = f"""<context>
Date: {context_snapshot.get('current_date')}{profile_str}
Accounts: {accounts_str}
Recent Transactions:
{recent_tx_str}
Month Summary: {summary_str}
</context>"""

    # 4. Supplementary blocks
    extra_blocks = []
    if conversation_summary:
        extra_blocks.append(conversation_summary.strip())

    if retrieved_memories:
        mem_lines = []
        for x in retrieved_memories:
            # Handle both vector store dicts and memory store dicts
            score = x.get("similarity_score") or x.get("relevance_score") or 1.0
            if score > 0.3:
                doc_type = x.get("doc_type") or x.get("memory_type", "doc")
                text = x.get("text") or x.get("content", "")
                mem_lines.append(f"- [{doc_type.upper()}] {text}")
        if mem_lines:
            extra_blocks.append("<retrieved_memories>\n" + "\n".join(mem_lines) + "\n</retrieved_memories>")

    supplementary_str = ("\n\n" + "\n\n".join(extra_blocks)) if extra_blocks else ""

    # 5. Full assemble
    return f"""{ROLE_BLOCK}

{AUTHORITY_BLOCK}

{RULES_BLOCK}

{CATEGORIES_BLOCK}

{tools_section}

{FORMAT_BLOCK}

{context_section}{supplementary_str}
"""

def format_system_prompt_with_context(
    context_snapshot: Dict[str, Any],
    retrieved_memories: Optional[List[Dict[str, Any]]] = None
) -> str:
    """Backwards-compatible wrapper for existing agent / test calls."""
    return build_system_prompt(
        context_snapshot=context_snapshot,
        candidate_tools=None,
        conversation_summary=None,
        retrieved_memories=retrieved_memories
    )
