# 💰 MoneyChingu AI: Multimodal Financial Tracking Agent

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/frontend-Streamlit-FF4B4B.svg)](https://streamlit.io/)
[![Google Gemini](https://img.shields.io/badge/AI_Model-Gemini_Free_Tier-4285F4.svg)](https://aistudio.google.com/)
[![SQLite](https://img.shields.io/badge/Database-SQLite-003B57.svg)](https://www.sqlite.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> An intelligent, conversational AI Financial Tracking Assistant that turns messy receipts, bank statements (PDF/CSV), and casual text prompts into clean, categorized, audited financial records. Features dual-currency support (**USD \$** & **IDR Rp**), **Human-in-the-Loop (HITL)** confirmation, and **RAG Semantic Memory**.

---

## 🌟 Key Highlights & Features

- 💬 **Single-Pane Conversational UI**: Focused, distraction-free chat interface with chat session displayed cleanly above the input box (no complex sidebars).
- 🛠️ **Inline Chat Toolbar**: Sleek popovers directly above chat input: `🛠️ Tools` (Recent Transactions, Check Balances) and `➕ Attach` (receipt images, PDF/CSV statements) with instant preview.
- 🛡️ **Action Permission Gate (HITL)**: Destructive and irreversible actions (`clear_database`, `delete_transaction`, `delete_account`, `transfer_funds`) are intercepted and require explicit confirmation (`✅ Yes, Proceed` / `❌ Cancel`).
- 🧠 **4-Pillar Context Engineering**: Google-standard architecture implementing WRITE (episodic/semantic memory in SQLite), SELECT (JIT tool & intent routing), COMPRESS (token pruning & rolling summaries), and ISOLATE (layered prompts with strict authority hierarchy).
- 📸 **Multimodal Vision OCR & Summary**: Gemini Vision analyzes receipt images, provides a concise visual analysis summary banner, and lets users manually refine notes and fields before confirming.
- 🌐 **Dual International Currency**: Native support for **USD (\$ )** and **IDR (Rp)** with automated conversion.
- 🔒 **Privacy-First & Local Storage**: 100% local SQLite database with cross-session chat and memory persistence.

---

## 🏗️ System Architecture

```mermaid
flowchart TD
    User([User]) <--> ChatUI[Streamlit Single-Pane Chat & Inline Toolbar]
    ChatUI <--> AgentCore[AI Financial Agent Core]
    
    subgraph AgentCore [Context Engineering ReAct Loop]
        IntentRouter[🎯 Intent Router & Dynamic Tool RAG]
        ContextMgr[🗜️ Context Manager: Pruning & Compression]
        LayeredPrompt[📐 Layered System Prompt & Authority Hierarchy]
        MemoryStore[💾 Memory Store: Episodic, Semantic, Procedural]
        GeminiClient[🤖 Google Gemini 3.6 / 2.0 Flash]
    end

    AgentCore <--> SkillsLayer [Modular Agent Skills]

    subgraph SkillsLayer [Modular Agent Skills]
        SkillOCR[📸 Data Processing: Receipt OCR / PDF / CSV]
        SkillCRUD[💾 Data Management: SQLite CRUD & Reports]
        SkillStats[📈 Financial Analytics & Budgets]
        SkillHF[🤗 HuggingFace Integration]
    end

    AgentCore --> PermissionGate{🛡️ Action Permission Gate}
    PermissionGate -- Safe / User Confirmed --> SkillsLayer
    PermissionGate -- Destructive / Needs Review --> HITLCard[🛡️ Inline HITL Confirmation Card]
    HITLCard -- Confirmed --> SkillsLayer
    SkillsLayer <--> SQLiteDB[(SQLite: money_tracker.db)]
    SkillsLayer <--> VectorDB[(Vector Memory: vectors.json)]
```

---

## 📁 Project Structure

```
Tracking_Money/
├── app.py                          # Streamlit Main Dashboard & Chat Controller
├── config.py                       # App Configuration, Model Settings, & Currency Rates
├── requirements.txt                # Python Dependencies
├── PRD.md                          # Product Requirement Document & Progress Log
├── README.md                       # Repository Documentation
├── .env.example                    # Environment Variable Template
├── core/
│   ├── agent.py                    # Central AI ReAct Agent with 7-Phase Context Engineering
│   ├── intent_router.py            # Bilingual Intent Router & JIT Dynamic Tool Injection
│   ├── memory_store.py             # Typed Memory Persistence (Episodic, Semantic, Procedural)
│   ├── context_manager.py          # In-Flight Token Pruning & Rolling Extractive Summarizer
│   ├── prompts.py                  # Layered XML Prompts with Strict Authority Precedence
│   └── gemini_client.py            # Gemini API Client (Multimodal & Free Tier Fallbacks)
├── database/
│   ├── db.py                       # SQLite Database Manager (Accounts, Transactions, Budgets, Memory)
│   ├── vector_store.py             # Vector Store with Google Embeddings for RAG
│   └── seed_data.py                # Initial Seed Data for Instant Setup
├── skills/
│   ├── base.py                     # Abstract Base Skill
│   ├── data_processing.py          # Multimodal OCR, PDF & CSV Parser
│   ├── data_management.py          # SQLite CRUD, Balance Reconciliation, CSV Export
│   ├── financial_analytics.py      # Budget Burn Rates, Cash Flows, Currency Math
│   ├── rag_context.py              # Semantic Retrieval over Financial Memory
│   └── hf_skills.py                # HuggingFace Zero-Shot Categorization & Sentiment
├── ui/
│   ├── components.py               # Inline HITL Cards, Destructive Permission Cards, KPI Widgets
│   ├── charts.py                   # Plotly Interactive Visualizations
│   └── styles.py                   # Sleek Modern Dark/Glassmorphic CSS Theme
└── tests/
    ├── test_money_tracker.py       # Unit Tests for Database, Skills, and Vector RAG
    ├── test_agent.py               # Unit Tests for Agent Core, Permissions, and Formatting
    └── test_context_engineering.py # Unit Tests for 4 Context Engineering Pillars
```

---

## 🚀 Quick Start Guide

### 1. Clone the Repository
```bash
git clone https://github.com/PandhuPrayogo/MoneyChingu.git
cd MoneyChingu
```

### 2. Set Up Virtual Environment
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Gemini API Key (Free Tier)
Create a `.env` file or copy from `.env.example`:
```bash
cp .env.example .env
```
Add your free Google Gemini API key (obtainable at [Google AI Studio](https://aistudio.google.com/)):
```env
GEMINI_API_KEY=AIzaSy...
GEMINI_MODEL=gemini-3.6-flash
USD_TO_IDR_RATE=16000.0
```
*(Note: You can also enter or switch your Gemini API key directly inside the Streamlit sidebar UI at runtime).*

### 5. Launch the Application
```bash
streamlit run app.py
```
The app will open automatically in your browser at `http://localhost:8501`.

---

## 🧪 Running Unit Tests

Run the complete test suite to verify database operations, skills, currency conversions, and agent reasoning:

```bash
python -m unittest discover -s tests -v
```

---

## 💡 Usage Examples

### 1. Conversational Logging
* *"Spent \$24 on sushi lunch at Tokyo Dine with credit card"*
* *"Beli kopi kenangan 45000 IDR pake GoPay"*
* *"Received \$2,500 salary from employer"*

### 2. Receipt Vision Scanning & Attachments
1. Click **`➕ Attach`** directly above the chat box.
2. Upload a receipt image, PDF bank statement, or CSV export.
3. Preview the image or file and click **`⚡ Extract & Review in Chat`**.
4. Read the **LLM Image Analysis Summary** and review the inline confirmation card.
5. Manually adjust any notes or fields, then click **`✅ Confirm & Save`**.

### 3. Financial Analytics & RAG
* *"How much did I spend on Food this month in USD?"*
* *"Show my current budget burn rate."*
* *"Where did I buy that pasta dinner last week?"* (Searches semantic vector memory).

---

## 🆕 Progress Log / What's New

### v1.2.0
- **Clean Inline Toolbar**: Simplified to 2 essential shortcuts (`Recent Transactions`, `Check Balances`) and inline `➕ Attach` popover with instant preview.
- **In-Chat HITL Placement**: Confirmation cards now render directly inside the active chat message stream instead of at the top of the UI.
- **Action Permission Gate**: Destructive actions (`clear_database`, `delete_transaction`, `delete_account`, `transfer_funds`) are intercepted and require explicit confirmation.
- **Visual Image Analysis Summary & Editable Notes**: Gemini Flash Vision analyzes attached receipts, generates a visual overview banner, and provides an editable notes area for manual refinement.
- **Context Engineering Architecture**: Defeats context poisoning, distraction, confusion, and clash via 4 pillars: WRITE (typed memory), SELECT (JIT dynamic tools), COMPRESS (token pruning & summaries), and ISOLATE (layered prompts with authority hierarchy).
- **Cross-Session Continuity**: SQLite-persisted chat history and user preferences loaded on startup.

---

## 📜 License
Distributed under the MIT License. See `LICENSE` for more information.
