CUSTOM_CSS = """
<style>
    /* Modern Glassmorphic Clean Theme */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    /* Main Container */
    .main .block-container {
        padding-top: 1.2rem;
        padding-bottom: 2.5rem;
        max-width: 900px;
    }

    /* Hide sidebar completely */
    [data-testid="collapsedControl"] { display: none; }
    section[data-testid="stSidebar"] { display: none; }

    /* ================= CHAT INPUT FOCUS OVERRIDE (WHITE / INDIGO INSTEAD OF RED) ================= */
    [data-testid="stChatInput"] {
        border-color: rgba(255, 255, 255, 0.2) !important;
        border-radius: 14px !important;
        background: rgba(30, 41, 59, 0.7) !important;
        backdrop-filter: blur(12px) !important;
    }
    
    [data-testid="stChatInput"]:focus-within {
        border-color: #ffffff !important;
        box-shadow: 0 0 12px rgba(255, 255, 255, 0.25) !important;
    }

    [data-testid="stChatInput"] textarea {
        color: #f8fafc !important;
        caret-color: #ffffff !important;
    }

    [data-testid="stChatInput"] textarea:focus {
        border-color: #ffffff !important;
        box-shadow: none !important;
    }

    [data-testid="stChatInput"] button {
        color: #ffffff !important;
    }

    [data-testid="stChatInput"] button:hover {
        background: rgba(255, 255, 255, 0.15) !important;
    }

    /* Override standard inputs focus from red to white */
    .stTextInput input:focus, .stNumberInput input:focus, .stSelectbox [data-baseweb="select"] > div:focus-within {
        border-color: #ffffff !important;
        box-shadow: 0 0 8px rgba(255, 255, 255, 0.2) !important;
    }

    /* Header & Quick Stat Bar */
    .chat-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding-bottom: 12px;
        margin-bottom: 10px;
        border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    }
    
    .header-pill {
        background: rgba(99, 102, 241, 0.15);
        border: 1px solid rgba(99, 102, 241, 0.35);
        color: #a5b4fc;
        padding: 5px 14px;
        border-radius: 20px;
        font-size: 0.88rem;
        font-weight: 600;
        letter-spacing: 0.3px;
    }

    /* Suggestion Chips */
    .suggestion-chip {
        display: inline-block;
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.12);
        color: #cbd5e1;
        padding: 6px 14px;
        border-radius: 20px;
        font-size: 0.82rem;
        cursor: pointer;
        transition: all 0.2s ease;
        margin: 4px 3px;
    }
    .suggestion-chip:hover {
        background: rgba(255, 255, 255, 0.12);
        border-color: #ffffff;
        color: #ffffff;
    }

    /* Metric Cards */
    .metric-card {
        background: linear-gradient(135deg, rgba(255, 255, 255, 0.05), rgba(255, 255, 255, 0.02));
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 14px;
        padding: 16px;
        backdrop-filter: blur(10px);
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.15);
        transition: transform 0.2s ease;
    }
    .metric-card:hover {
        transform: translateY(-2px);
        border-color: rgba(255, 255, 255, 0.3);
    }
    .metric-label {
        font-size: 0.82rem;
        font-weight: 500;
        color: #94a3b8;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .metric-value {
        font-size: 1.5rem;
        font-weight: 700;
        margin-top: 4px;
        color: #f8fafc;
    }
    .metric-sub {
        font-size: 0.78rem;
        margin-top: 4px;
    }
    .positive-text { color: #10b981; }
    .negative-text { color: #ffffff; }
    .neutral-text { color: #818cf8; }

    /* HITL Confirmation Box */
    .hitl-container {
        background: linear-gradient(135deg, rgba(99, 102, 241, 0.1), rgba(168, 85, 247, 0.06));
        border: 1.5px solid #818cf8;
        border-radius: 14px;
        padding: 18px;
        margin: 12px 0;
        box-shadow: 0 10px 25px -5px rgba(99, 102, 241, 0.2);
    }
    .hitl-title {
        font-size: 1rem;
        font-weight: 600;
        color: #c7d2fe;
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 12px;
    }

    /* Custom Scrollbars */
    ::-webkit-scrollbar {
        width: 6px;
        height: 6px;
    }
    ::-webkit-scrollbar-track {
        background: transparent;
    }
    ::-webkit-scrollbar-thumb {
        background: rgba(255, 255, 255, 0.2);
        border-radius: 3px;
    }
</style>
"""
