# 📄 Product Requirement Document (PRD): MoneyChingu AI

## 1. Executive Summary
**MoneyChingu AI** is an intelligent, multimodal personal finance and money tracking application powered by **Google Gemini AI**, **Streamlit**, and **SQLite**. It replaces tedious manual spreadsheet logging with a natural language conversational agent that can parse receipts via Vision AI, extract transactions from bank statements (PDF/CSV), enforce budgets, perform semantic memory search (RAG), and provide Human-in-the-Loop (HITL) review.

---

## 2. Target Users & Problem Statement

### 2.1 Target Persona
- **Single User / Power User**: Individuals, freelancers, and professionals looking for a frictionless, private, and automated financial tracking system with dual currency support (**USD \$** and **IDR Rp**).

### 2.2 Core Problems Solved
1. **Manual Entry Fatigue**: Logging transactions into spreadsheets daily is tedious and prone to abandonment.
2. **Data Inaccuracies**: Mistyped numbers, missed paper receipts, or lost bank records.
3. **No Proactive Advice**: Static spreadsheets don't warn about overspending or answer conversational questions about historical spending habits.
4. **Data Privacy**: Users want their financial ledger stored locally rather than exposed to third-party cloud servers.

---

## 3. Product Features & Functional Requirements

```mermaid
flowchart LR
    A[Multimodal Inputs: Prompts / Images / PDFs / CSV] --> B[AI Processing & OCR]
    B --> C[Inline HITL Confirmation]
    C --> D[SQLite Ledger & Silent Vector RAG]
    D --> E[Conversational Reporting & Action Delivery]
```

### 3.1 Feature Matrix

| Feature | Description | Priority |
| :--- | :--- | :--- |
| **Single-Pane Chat Interface** | Conversational chat stream positioned right above the text input with zero sidebar distraction. | **P0 (Critical)** |
| **All-in-One Conversational CRUD** | Agent creates, reads, updates, and deletes transactions, accounts, budgets, and produces instant reports directly in chat. | **P0 (Critical)** |
| **Multimodal Vision OCR** | Upload receipt images and invoices inline; Gemini Vision automatically extracts merchant, date, amount, currency, and items. | **P0 (Critical)** |
| **Inline Human-in-the-Loop (HITL)** | Editable confirmation card displayed right in the chat stream before saving extracted transactions. | **P0 (Critical)** |
| **Dual Currency Engine** | Full support for **USD (\$ )** and **IDR (Rp)** with live conversion rate calculations and multi-currency accounts. | **P0 (Critical)** |
| **Silent RAG Pipeline** | Background vector retrieval automatically enriches prompt context with relevant memories on every user query. | **P0 (Critical)** |
| **Local SQLite Persistence** | Zero-latency, privacy-first local database storing accounts, transactions, budgets, and audit logs. | **P0 (Critical)** |

---

## 4. System Architecture & Tech Stack

- **Frontend**: Streamlit 1.35+ with responsive custom CSS, interactive Plotly charts, and chat interfaces.
- **AI Core**: Google Gemini Free Tier (`gemini-3.6-flash`) + Google `text-embedding-004`.
- **Engineering Standards**:
  - **Anthropic Prompt Engineering**: XML-based system prompt structure (`<system_role>`, `<financial_context>`, `<scratchpad>`, `<output_format>`) with explicit Chain-of-Thought (CoT) reasoning.
  - **Google Context Engineering**: Context grounding strictly in SQLite facts to eliminate hallucinations, token budget optimization.
- **Database**: SQLite3 (Local ledger with relational constraints) + Vector Store (JSON/SQLite cosine similarity).
- **Languages & Frameworks**: Python 3.10+, Pandas, Pillow, PyPDF2, Plotly, NumPy, Scikit-learn.

---

## 5. Security & Privacy
- **Local-First Storage**: All transaction data, accounts, and budgets reside exclusively on the user's local machine in `data/money_tracker.db`.
- **API Key Safety**: API keys are loaded via `.env` or input via secure password fields and never committed to version control.
- **Audit Logs**: Every mutation (add, delete, balance change) is recorded in the `audit_logs` table for full traceability.
