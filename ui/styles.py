CUSTOM_CSS = """
<style>
    /* Modern Glassmorphic Clean Theme */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    /* Main Container Padding */
    .main .block-container {
        padding-top: 1.5rem;
        padding-bottom: 3rem;
        max-width: 1200px;
    }

    /* Metric Cards */
    .metric-card {
        background: linear-gradient(135deg, rgba(255, 255, 255, 0.05), rgba(255, 255, 255, 0.02));
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 14px;
        padding: 18px;
        backdrop-filter: blur(10px);
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.15);
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    .metric-card:hover {
        transform: translateY(-2px);
        border-color: rgba(99, 102, 241, 0.4);
    }
    .metric-label {
        font-size: 0.85rem;
        font-weight: 500;
        color: #94a3b8;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .metric-value {
        font-size: 1.6rem;
        font-weight: 700;
        margin-top: 4px;
        color: #f8fafc;
    }
    .metric-sub {
        font-size: 0.8rem;
        margin-top: 4px;
    }
    .positive-text { color: #10b981; }
    .negative-text { color: #ef4444; }
    .neutral-text { color: #6366f1; }

    /* HITL Confirmation Box */
    .hitl-container {
        background: linear-gradient(135deg, rgba(99, 102, 241, 0.08), rgba(168, 85, 247, 0.05));
        border: 1.5px solid #6366f1;
        border-radius: 14px;
        padding: 20px;
        margin: 15px 0;
        box-shadow: 0 10px 25px -5px rgba(99, 102, 241, 0.2);
    }
    .hitl-title {
        font-size: 1.05rem;
        font-weight: 600;
        color: #818cf8;
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 12px;
    }

    /* CoT Scratchpad Collapsible */
    .scratchpad-box {
        background: rgba(15, 23, 42, 0.6);
        border-left: 3px solid #8b5cf6;
        padding: 10px 14px;
        border-radius: 0 8px 8px 0;
        font-family: monospace;
        font-size: 0.85rem;
        color: #cbd5e1;
        margin-bottom: 10px;
    }

    /* Badges */
    .badge-pill {
        display: inline-block;
        padding: 3px 10px;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
    }
    .badge-usd { background: rgba(16, 185, 129, 0.15); color: #10b981; border: 1px solid rgba(16, 185, 129, 0.3); }
    .badge-idr { background: rgba(245, 158, 11, 0.15); color: #f59e0b; border: 1px solid rgba(245, 158, 11, 0.3); }

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
