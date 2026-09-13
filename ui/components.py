import streamlit as st
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime

from config import DEFAULT_EXPENSE_CATEGORIES, DEFAULT_INCOME_CATEGORIES, SUPPORTED_CURRENCIES
from database.db import db
from database.vector_store import vector_store

def render_kpi_cards(monthly_summary: Dict[str, Any], net_worth_summary: Dict[str, Any]):
    """Render top 4 summary metric KPI cards with dual-currency awareness."""
    currency = monthly_summary.get("currency", "USD")
    sym = "$" if currency == "USD" else "Rp "

    net_worth = net_worth_summary.get("total_net_worth", 0.0)
    income = monthly_summary.get("total_income", 0.0)
    expense = monthly_summary.get("total_expense", 0.0)
    savings = monthly_summary.get("net_savings", 0.0)
    savings_rate = monthly_summary.get("savings_rate_pct", 0.0)

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Total Net Worth</div>
            <div class="metric-value">{sym}{net_worth:,.2f}</div>
            <div class="metric-sub neutral-text">Across all accounts</div>
        </div>
        """, unsafe_allow_html=True)

    with c2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Monthly Income</div>
            <div class="metric-value positive-text">{sym}{income:,.2f}</div>
            <div class="metric-sub positive-text">Cash inflow</div>
        </div>
        """, unsafe_allow_html=True)

    with c3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Monthly Spending</div>
            <div class="metric-value negative-text">{sym}{expense:,.2f}</div>
            <div class="metric-sub negative-text">Total expenses</div>
        </div>
        """, unsafe_allow_html=True)

    with c4:
        savings_color = "positive-text" if savings >= 0 else "negative-text"
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Net Savings</div>
            <div class="metric-value {savings_color}">{sym}{savings:,.2f}</div>
            <div class="metric-sub {savings_color}">{savings_rate}% savings rate</div>
        </div>
        """, unsafe_allow_html=True)

def render_destructive_hitl_card(key_prefix: str, initial_data: Dict[str, Any]):
    """
    Render an action permission confirmation card for sensitive/destructive operations.
    """
    action = initial_data.get("action", "Dangerous Operation")
    description = initial_data.get("description", "This action will permanently modify or delete data.")

    st.markdown(f"""
    <div class="hitl-container" style="border-left: 4px solid #ef4444; background: rgba(239, 68, 68, 0.08); padding: 12px; border-radius: 8px; margin-bottom: 15px;">
        <div class="hitl-title" style="color: #ef4444; font-size: 1.05em;">
            <span>⚠️</span> <b>Action Permission Required: {action}</b>
        </div>
        <p style="margin-top: 6px; color: #e2e8f0; font-size: 0.95em;">
            {description}
        </p>
    </div>
    """, unsafe_allow_html=True)

    btn_c1, btn_c2, _ = st.columns([1, 1, 2])
    with btn_c1:
        if st.button("✅ Yes, Proceed", type="primary", key=f"{key_prefix}_dest_confirm_btn"):
            params = initial_data.get("parameters", {})
            from skills import data_management_skill
            result = data_management_skill.execute(**params)
            success_msg = f"✅ Executed **{action}**: {result.get('message', 'Operation completed.')}"
            if "messages" in st.session_state:
                st.session_state.messages.append({"role": "assistant", "content": success_msg})
            db.save_chat_message("assistant", success_msg)
            st.session_state["pending_hitl"] = None
            st.toast(f"Executed {action}!", icon="✅")
            st.rerun()

    with btn_c2:
        if st.button("❌ Cancel", key=f"{key_prefix}_dest_cancel_btn"):
            st.session_state["pending_hitl"] = None
            cancel_msg = f"🛑 Cancelled execution of **{action}**."
            if "messages" in st.session_state:
                st.session_state.messages.append({"role": "assistant", "content": cancel_msg})
            db.save_chat_message("assistant", cancel_msg)
            st.toast("Operation cancelled.", icon="🛑")
            st.rerun()

def render_hitl_card(key_prefix: str, initial_data: Dict[str, Any], accounts: List[Dict[str, Any]]):
    """
    Render an interactive Human-in-the-Loop (HITL) Editable Confirmation Card.
    Allows user to verify, modify, and confirm AI-extracted transactions before saving to SQLite.
    """
    if initial_data.get("type") == "destructive_confirmation":
        render_destructive_hitl_card(key_prefix, initial_data)
        return

    st.markdown("""
    <div class="hitl-container">
        <div class="hitl-title">
            <span>🛡️</span> <b>Human-in-the-Loop: Review & Confirm Transaction</b>
        </div>
    </div>
    """, unsafe_allow_html=True)

    with st.container():
        # Display LLM Image Analysis Summary if present
        analysis_summary = initial_data.get("analysis_summary")
        if analysis_summary:
            st.markdown(f"""
            <div style="background: rgba(59, 130, 246, 0.1); border-left: 3px solid #3b82f6; padding: 10px 14px; border-radius: 6px; margin: 6px 0 14px 0;">
                <div style="font-size: 0.85em; font-weight: 600; color: #60a5fa; margin-bottom: 2px;">
                    🔍 LLM Image Analysis Summary
                </div>
                <div style="font-size: 0.95em; color: #f1f5f9; line-height: 1.4;">
                    {analysis_summary}
                </div>
            </div>
            """, unsafe_allow_html=True)

        col1, col2, col3 = st.columns(3)
        with col1:
            tx_date = st.date_input("Date", value=datetime.strptime(initial_data.get("date", datetime.now().strftime("%Y-%m-%d")), "%Y-%m-%d"), key=f"{key_prefix}_date")
        with col2:
            tx_amount = st.number_input("Amount", min_value=0.0, value=float(initial_data.get("amount", 0.0)), step=1.0, format="%.2f", key=f"{key_prefix}_amount")
        with col3:
            curr_idx = 0 if initial_data.get("currency", "USD").upper() == "USD" else 1
            tx_currency = st.selectbox("Currency", SUPPORTED_CURRENCIES, index=curr_idx, key=f"{key_prefix}_curr")

        col4, col5, col6 = st.columns(3)
        with col4:
            tx_type = st.selectbox("Type", ["expense", "income", "transfer"], index=0 if initial_data.get("type") == "expense" else 1, key=f"{key_prefix}_type")
        with col5:
            cat_list = DEFAULT_EXPENSE_CATEGORIES if tx_type == "expense" else DEFAULT_INCOME_CATEGORIES
            default_cat = initial_data.get("category", cat_list[0])
            cat_idx = cat_list.index(default_cat) if default_cat in cat_list else 0
            tx_cat = st.selectbox("Category", cat_list, index=cat_idx, key=f"{key_prefix}_cat")
        with col6:
            acc_names = [a["name"] for a in accounts]
            tx_acc_name = st.selectbox("Account", acc_names, index=0 if acc_names else 0, key=f"{key_prefix}_acc")

        tx_merchant = st.text_input("Merchant / Payee", value=initial_data.get("merchant", "General Store"), key=f"{key_prefix}_merch")

        default_note = initial_data.get("description") or initial_data.get("notes") or initial_data.get("items_summary", "")
        tx_desc = st.text_area(
            "📝 Note / Information (Manually edit or add details below):",
            value=default_note,
            height=75,
            key=f"{key_prefix}_desc",
            help="You can manually edit or refine any extracted details or items here before confirming."
        )

        btn_c1, btn_c2, _ = st.columns([1, 1, 2])
        with btn_c1:
            if st.button("✅ Confirm & Save", type="primary", key=f"{key_prefix}_confirm_btn"):
                # Find matching account ID
                selected_acc = next((a for a in accounts if a["name"] == tx_acc_name), None)
                acc_id = selected_acc["id"] if selected_acc else None

                tx_id = db.add_transaction(
                    date=tx_date.strftime("%Y-%m-%d"),
                    amount=tx_amount,
                    currency=tx_currency,
                    category=tx_cat,
                    tx_type=tx_type,
                    account_id=acc_id,
                    merchant=tx_merchant,
                    description=tx_desc,
                    raw_source=initial_data.get("raw_source", "manual"),
                    status="confirmed"
                )

                # Add to Vector Store
                vector_store.add_document(
                    text=f"{tx_merchant} {tx_cat} {tx_type} of {tx_amount} {tx_currency} on {tx_date}. {tx_desc}",
                    metadata={"tx_id": tx_id, "amount": tx_amount, "currency": tx_currency, "category": tx_cat, "merchant": tx_merchant},
                    doc_type="receipt" if initial_data.get("raw_source") == "receipt_image" else "transaction",
                    ref_id=tx_id
                )

                confirm_msg = f"✅ Confirmed and saved **{tx_type.upper()}**: **{tx_currency} {tx_amount:,.2f}** for **{tx_merchant}** ({tx_cat}) into **{tx_acc_name}**."
                if "messages" in st.session_state:
                    st.session_state.messages.append({"role": "assistant", "content": confirm_msg})
                db.save_chat_message("assistant", confirm_msg)

                st.toast("🎉 Transaction recorded successfully into SQLite ledger!", icon="✅")
                st.session_state["pending_hitl"] = None
                st.rerun()

        with btn_c2:
            if st.button("❌ Discard", key=f"{key_prefix}_discard_btn"):
                st.session_state["pending_hitl"] = None
                discard_msg = "❌ Discarded transaction draft."
                if "messages" in st.session_state:
                    st.session_state.messages.append({"role": "assistant", "content": discard_msg})
                db.save_chat_message("assistant", discard_msg)
                st.toast("Discarded transaction.", icon="🗑️")
                st.rerun()
