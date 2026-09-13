import os
import streamlit as st
import pandas as pd
from PIL import Image
from datetime import datetime

from config import (
    DEFAULT_CURRENCY, 
    SUPPORTED_CURRENCIES, 
    USD_TO_IDR_RATE, 
    DEFAULT_GEMINI_MODEL, 
    GEMINI_API_KEY, 
    AGENT_NAME,
    DEFAULT_EXPENSE_CATEGORIES
)
from database.db import db
from database.vector_store import vector_store
from database.seed_data import seed_initial_data
from core.agent import financial_agent
from core.gemini_client import gemini_client
from skills import data_processing_skill, data_management_skill, financial_analytics_skill, rag_context_skill
from ui.styles import CUSTOM_CSS
from ui.components import render_kpi_cards, render_hitl_card

# ================= 1. PAGE SETUP (NO SIDEBAR) ================= #

st.set_page_config(
    page_title=f"{AGENT_NAME} AI - Financial Assistant",
    page_icon="💰",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Apply sleek styling (hide sidebar toggle, white focus on search bar, polished glassmorphism)
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# Ensure baseline accounts exist (at zero balance)
seed_initial_data()

# Initialize session states from SQLite history if available
if "messages" not in st.session_state:
    saved_history = db.get_chat_history(limit=50)
    if saved_history:
        st.session_state.messages = saved_history
    else:
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": f"👋 Hi! I'm **{AGENT_NAME}**, your AI Financial Tracking Assistant. 💸\n\nI can help you **track spending**, **read receipts & statements (images, PDFs, CSVs)**, **manage budgets**, **check balances**, and **generate instant financial reports**.\n\n*How can I help you manage your money today?*"
            }
        ]

if "pending_hitl" not in st.session_state:
    st.session_state.pending_hitl = None

if "prompt_queue" not in st.session_state:
    st.session_state.prompt_queue = []

if "display_currency" not in st.session_state:
    st.session_state.display_currency = DEFAULT_CURRENCY

# ================= 2. TOP HEADER & QUICK STATS ================= #

curr_month = datetime.now().strftime("%Y-%m")
monthly_summary = db.get_monthly_summary(curr_month, display_currency=st.session_state.display_currency)
net_worth_summary = db.get_total_balance_summary(display_currency=st.session_state.display_currency)

curr_sym = "$" if st.session_state.display_currency == "USD" else "Rp "
total_nw = net_worth_summary.get("total_net_worth", 0.0)

col_title, col_stat = st.columns([2, 1])
with col_title:
    st.markdown(f"### 💰 {AGENT_NAME} AI")
    st.caption("All-in-One Conversational Financial Tracking Agent")

with col_stat:
    st.markdown(f"""
    <div style="text-align: right; margin-top: 5px;">
        <span class="header-pill">Net Worth: {curr_sym}{total_nw:,.2f}</span>
    </div>
    """, unsafe_allow_html=True)

# Minimal Settings Expander (Zero-clutter API Key & Currency setup)
with st.expander("⚙️ Settings & Currency", expanded=False):
    s1, s2, s3 = st.columns([2, 1, 1])
    with s1:
        api_key_input = st.text_input("Gemini API Key", value=gemini_client.api_key or "", type="password", help="Free key from aistudio.google.com")
        if api_key_input:
            gemini_client.set_api_key(api_key_input)
    with s2:
        selected_curr = st.selectbox("Currency", SUPPORTED_CURRENCIES, index=SUPPORTED_CURRENCIES.index(st.session_state.display_currency))
        if selected_curr != st.session_state.display_currency:
            st.session_state.display_currency = selected_curr
            st.rerun()
    with s3:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🗑️ Reset to Zero", help="Wipes all ledger transactions, chat history, and memory back to 0"):
            db.clear_all_data(create_default_empty_accounts=True)
            vector_store.clear_all()
            st.session_state.messages = [
                {
                    "role": "assistant",
                    "content": f"👋 Hi! I'm **{AGENT_NAME}**, your AI Financial Tracking Assistant. 💸\n\nI can help you **track spending**, **read receipts & statements (images, PDFs, CSVs)**, **manage budgets**, **check balances**, and **generate instant financial reports**.\n\n*How can I help you manage your money today?*"
                }
            ]
            st.session_state.pending_hitl = None
            st.session_state.prompt_queue = []
            st.toast("Database, chat history & vector memory reset to 0!", icon="🧹")
            st.rerun()

st.divider()

# ================= 3. CHAT SESSION STREAM ================= #

for msg in st.session_state.messages:
    with st.chat_message(msg["role"], avatar="🤖" if msg["role"] == "assistant" else "👤"):
        st.markdown(msg["content"])

# Inline Human-in-the-Loop (HITL) card rendered directly inside the chat flow
if st.session_state.pending_hitl:
    accounts = db.get_accounts()
    with st.chat_message("assistant", avatar="🛡️"):
        render_hitl_card("chat_hitl_inline", st.session_state.pending_hitl, accounts)

# ================= 4. INLINE CHAT TOOLBAR (TOOLS & ATTACH) ================= #

tool_c1, tool_c2, _ = st.columns([1, 1, 4])
quick_prompt = None

with tool_c1:
    with st.popover("🛠️ Tools", use_container_width=True):
        st.markdown("**Quick Actions**")
        if st.button("📒 Recent Transactions", use_container_width=True, key="tool_recent_tx"):
            quick_prompt = "List my recent transactions."
        if st.button("💳 Check Balances", use_container_width=True, key="tool_check_bal"):
            quick_prompt = "List all my account balances."

with tool_c2:
    with st.popover("➕ Attach", use_container_width=True):
        st.markdown("**Attach Receipt or File**")
        uploaded_file = st.file_uploader(
            "Upload receipt / invoice / statement",
            type=["png", "jpg", "jpeg", "webp", "pdf", "csv"],
            key="inline_attach_uploader",
            label_visibility="collapsed"
        )
        if uploaded_file is not None:
            if uploaded_file.type.startswith("image/"):
                st.image(uploaded_file, caption=f"Preview: {uploaded_file.name}", use_container_width=True)
            else:
                st.info(f"📄 **{uploaded_file.name}** ({uploaded_file.size / 1024:.1f} KB)")

            if st.button("⚡ Extract & Review in Chat", type="primary", use_container_width=True, key="btn_extract_doc"):
                with st.spinner("Extracting document..."):
                    if uploaded_file.type.startswith("image/"):
                        res = data_processing_skill.process_receipt_image(uploaded_file)
                        if res.get("status") == "success":
                            data = res["data"]
                            st.session_state.pending_hitl = data
                            analysis_summary = data.get("analysis_summary") or f"Receipt from **{data.get('merchant', 'Merchant')}** for **{data.get('currency', 'USD')} {data.get('amount', 0.0):,.2f}** ({data.get('category', 'Expense')})."
                            user_msg = f"📎 *Attached Receipt: {uploaded_file.name}*"
                            asst_msg = f"🔍 **LLM Image Analysis Summary:**\n{analysis_summary}\n\n*Review the extracted draft below. You can manually adjust the note and details before confirming.*"
                            st.session_state.messages.append({"role": "user", "content": user_msg})
                            st.session_state.messages.append({"role": "assistant", "content": asst_msg})
                            db.save_chat_message("user", user_msg)
                            db.save_chat_message("assistant", asst_msg)
                            st.toast("Receipt analyzed! Review details in the card below.", icon="🔍")
                            st.rerun()
                        else:
                            st.error(res.get("message", "Error extracting image."))
                    elif uploaded_file.type == "application/pdf":
                        res = data_processing_skill.process_bank_pdf(uploaded_file)
                        if res.get("status") == "success":
                            tx_list = res.get("data", [])
                            user_msg = f"📎 *Attached PDF Statement: {uploaded_file.name}*"
                            if tx_list and isinstance(tx_list, list):
                                st.session_state.pending_hitl = tx_list[0]
                                asst_msg = f"📄 Extracted PDF statement (**{len(tx_list)} transactions** detected). Review the first transaction draft in the card below."
                            else:
                                asst_msg = "📄 Extracted PDF text, but no distinct transaction rows were recognized."
                            st.session_state.messages.append({"role": "user", "content": user_msg})
                            st.session_state.messages.append({"role": "assistant", "content": asst_msg})
                            db.save_chat_message("user", user_msg)
                            db.save_chat_message("assistant", asst_msg)
                            st.toast("PDF statement parsed! Review transaction below.", icon="📄")
                            st.rerun()
                        else:
                            st.error(res.get("message", "Error extracting PDF."))
                    elif uploaded_file.type in ["text/csv", "application/vnd.ms-excel"]:
                        res = data_processing_skill.process_csv_statement(uploaded_file)
                        if res.get("status") == "success":
                            tx_list = res.get("data", [])
                            user_msg = f"📎 *Attached CSV Statement: {uploaded_file.name}*"
                            if tx_list and isinstance(tx_list, list):
                                st.session_state.pending_hitl = tx_list[0]
                                asst_msg = f"📊 Extracted CSV statement (**{len(tx_list)} rows**). Review the first transaction draft in the card below."
                            else:
                                asst_msg = "📊 Processed CSV, but no transaction records were recognized."
                            st.session_state.messages.append({"role": "user", "content": user_msg})
                            st.session_state.messages.append({"role": "assistant", "content": asst_msg})
                            db.save_chat_message("user", user_msg)
                            db.save_chat_message("assistant", asst_msg)
                            st.toast("CSV statement parsed! Review transaction below.", icon="📊")
                            st.rerun()

# ================= 6. CHAT INPUT & PROMPT QUEUE HANDLING ================= #

user_prompt = st.chat_input("Ask MoneyChingu, log spending, or request a financial report...") or quick_prompt

# If a new prompt is submitted, push into the prompt queue
if user_prompt:
    st.session_state.prompt_queue.append(user_prompt)

# Display queue status banner if multiple prompts are waiting
if len(st.session_state.prompt_queue) > 1:
    st.caption(f"⏳ **Prompt Queue Active**: {len(st.session_state.prompt_queue)} message(s) queued for processing.")

# Process the next queued prompt FIFO
if st.session_state.prompt_queue:
    current_prompt = st.session_state.prompt_queue.pop(0)

    # Append User Message
    st.session_state.messages.append({"role": "user", "content": current_prompt})
    db.save_chat_message("user", current_prompt)
    with st.chat_message("user", avatar="👤"):
        st.markdown(current_prompt)

    # Generate Assistant Response
    with st.chat_message("assistant", avatar="🤖"):
        with st.spinner("MoneyChingu thinking..."):
            agent_res = financial_agent.process_user_turn(
                user_message=current_prompt,
                conversation_history=st.session_state.messages,
                display_currency=st.session_state.display_currency
            )

            st.markdown(agent_res["message"])

            # Save assistant turn
            st.session_state.messages.append({
                "role": "assistant",
                "content": agent_res["message"]
            })
            db.save_chat_message("assistant", agent_res["message"])

            # Check if HITL confirmation needed
            if agent_res.get("hitl_pending"):
                st.session_state.pending_hitl = agent_res["hitl_pending"]
                st.rerun()

    # If there are remaining queued prompts, trigger rerun to process sequentially
    if st.session_state.prompt_queue:
        st.rerun()
