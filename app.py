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

# Initialize session states
if "messages" not in st.session_state:
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
        if st.button("🗑️ Reset to Zero", help="Wipes all ledger transactions and memory back to 0"):
            db.clear_all_data(create_default_empty_accounts=True)
            vector_store.clear_all()
            st.toast("Database & vector memory reset to 0!", icon="🧹")
            st.rerun()

st.divider()

# ================= 3. INLINE HUMAN-IN-THE-LOOP (HITL) CARD ================= #

accounts = db.get_accounts()

if st.session_state.pending_hitl:
    render_hitl_card("chat_hitl_inline", st.session_state.pending_hitl, accounts)

# ================= 4. CHAT SESSION STREAM (ABOVE INPUT) ================= #

for msg in st.session_state.messages:
    with st.chat_message(msg["role"], avatar="🤖" if msg["role"] == "assistant" else "👤"):
        st.markdown(msg["content"])

# Quick action shortcut buttons
qc1, qc2, qc3, qc4 = st.columns(4)
quick_prompt = None
with qc1:
    if st.button("📊 Monthly Report", use_container_width=True):
        quick_prompt = "Generate my full monthly financial summary and net worth breakdown."
with qc2:
    if st.button("💳 Check Balances", use_container_width=True):
        quick_prompt = "List all my account balances."
with qc3:
    if st.button("🎯 Budget Status", use_container_width=True):
        quick_prompt = "Show my budget status for this month."
with qc4:
    if st.button("📒 Recent Transactions", use_container_width=True):
        quick_prompt = "List my recent transactions."

# ================= 5. MULTIMODAL ATTACHMENT ACCORDION ================= #

with st.expander("📎 Attach Receipt Image, PDF Statement, or CSV File", expanded=False):
    uploaded_file = st.file_uploader(
        "Upload receipt / invoice / statement for instant AI extraction",
        type=["png", "jpg", "jpeg", "webp", "pdf", "csv"],
        key="inline_multimodal_uploader"
    )
    if uploaded_file is not None:
        uc1, uc2 = st.columns([1, 2])
        with uc1:
            if uploaded_file.type.startswith("image/"):
                st.image(uploaded_file, caption="Receipt Attached", width=180)
        with uc2:
            if st.button("⚡ Extract & Review in Chat", type="primary", key="btn_extract_doc"):
                with st.spinner("Extracting document..."):
                    if uploaded_file.type.startswith("image/"):
                        res = data_processing_skill.process_receipt_image(uploaded_file)
                        if res.get("status") == "success":
                            st.session_state.pending_hitl = res["data"]
                            st.toast("Receipt parsed! Review the confirmation card above.", icon="✨")
                            st.rerun()
                        else:
                            st.error(res.get("message", "Error extracting image."))
                    elif uploaded_file.type == "application/pdf":
                        res = data_processing_skill.process_bank_pdf(uploaded_file)
                        if res.get("status") == "success":
                            tx_list = res.get("data", [])
                            if tx_list and isinstance(tx_list, list):
                                st.session_state.pending_hitl = tx_list[0]
                                st.toast("PDF statement parsed! Review transaction above.", icon="📄")
                                st.rerun()
                            else:
                                st.write("Extracted PDF Transactions:", pd.DataFrame(tx_list))
                        else:
                            st.error(res.get("message", "Error extracting PDF."))
                    elif uploaded_file.type in ["text/csv", "application/vnd.ms-excel"]:
                        res = data_processing_skill.process_csv_statement(uploaded_file)
                        if res.get("status") == "success":
                            tx_list = res.get("data", [])
                            if tx_list and isinstance(tx_list, list):
                                st.session_state.pending_hitl = tx_list[0]
                                st.toast("CSV statement parsed! Review transaction above.", icon="📊")
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

            # Check if HITL confirmation needed
            if agent_res.get("hitl_pending"):
                st.session_state.pending_hitl = agent_res["hitl_pending"]
                st.rerun()

    # If there are remaining queued prompts, trigger rerun to process sequentially
    if st.session_state.prompt_queue:
        st.rerun()
