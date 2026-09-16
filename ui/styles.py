"""Custom CSS injected into the Streamlit app for a premium engineering-dashboard look."""

CUSTOM_CSS = """
<style>
    :root {
        --navy-900: #0b1e3d;
        --navy-800: #12284f;
        --navy-700: #1a3563;
        --navy-600: #24447a;
        --accent-blue: #2f6fed;
        --accent-cyan: #14b8c8;
        --bg-light: #f4f6fa;
        --card-bg: #ffffff;
        --text-dark: #10213e;
        --text-muted: #5c6b85;
        --border-light: #e3e8f0;
        --success: #1a9e6f;
        --warning: #d98c1f;
        --danger: #d64545;
    }

    /* Overall app background */
    .stApp {
        background-color: var(--bg-light);
    }

    /* Hide default Streamlit chrome that looks unpolished */
    #MainMenu, footer {visibility: hidden;}

    /* Main header banner */
    .bess-header {
        background: linear-gradient(120deg, var(--navy-900) 0%, var(--navy-700) 100%);
        padding: 1.6rem 2rem;
        border-radius: 14px;
        margin-bottom: 1.4rem;
        box-shadow: 0 6px 20px rgba(11, 30, 61, 0.25);
    }
    .bess-header h1 {
        color: #ffffff;
        font-size: 1.65rem;
        font-weight: 700;
        margin: 0;
        letter-spacing: 0.02em;
    }
    .bess-header p {
        color: #b9c7e6;
        margin: 0.25rem 0 0 0;
        font-size: 0.92rem;
    }

    /* Section header bar */
    .section-header {
        background: var(--navy-800);
        color: #ffffff;
        padding: 0.6rem 1rem;
        border-radius: 8px;
        font-weight: 600;
        font-size: 1.02rem;
        margin: 1.1rem 0 0.8rem 0;
        letter-spacing: 0.01em;
    }
    .subsection-header {
        color: var(--navy-800);
        font-weight: 700;
        font-size: 0.95rem;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        border-bottom: 2px solid var(--accent-blue);
        padding-bottom: 0.3rem;
        margin: 1rem 0 0.7rem 0;
    }

    /* Result / KPI cards */
    .kpi-card {
        background: var(--card-bg);
        border: 1px solid var(--border-light);
        border-left: 4px solid var(--accent-blue);
        border-radius: 10px;
        padding: 0.9rem 1.1rem;
        box-shadow: 0 2px 8px rgba(16, 33, 62, 0.06);
        height: 100%;
    }
    .kpi-card .kpi-label {
        color: var(--text-muted);
        font-size: 0.76rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        font-weight: 600;
        margin-bottom: 0.25rem;
    }
    .kpi-card .kpi-value {
        color: var(--text-dark);
        font-size: 1.45rem;
        font-weight: 700;
        line-height: 1.2;
    }
    .kpi-card .kpi-unit {
        color: var(--text-muted);
        font-size: 0.85rem;
        font-weight: 500;
    }
    .kpi-card.accent-cyan { border-left-color: var(--accent-cyan); }
    .kpi-card.accent-success { border-left-color: var(--success); }
    .kpi-card.accent-warning { border-left-color: var(--warning); }

    /* Calculated (read-only) field badge */
    .calc-badge {
        display: inline-block;
        background: #eaf1ff;
        color: var(--accent-blue);
        font-size: 0.68rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        padding: 0.12rem 0.5rem;
        border-radius: 999px;
        margin-left: 0.4rem;
        vertical-align: middle;
    }
    .input-badge {
        display: inline-block;
        background: #eaf9f2;
        color: var(--success);
        font-size: 0.68rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        padding: 0.12rem 0.5rem;
        border-radius: 999px;
        margin-left: 0.4rem;
        vertical-align: middle;
    }

    /* Formula trace box */
    .formula-box {
        background: #f8fafc;
        border: 1px dashed var(--border-light);
        border-radius: 8px;
        padding: 0.7rem 0.9rem;
        font-family: 'Courier New', monospace;
        font-size: 0.85rem;
        color: var(--navy-800);
        margin: 0.4rem 0;
        white-space: pre-wrap;
    }

    /* Sidebar */
    section[data-testid="stSidebar"] {
        background: var(--navy-900);
    }
    section[data-testid="stSidebar"] * {
        color: #dce4f5 !important;
    }
    section[data-testid="stSidebar"] .stRadio label {
        color: #dce4f5 !important;
    }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 4px;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #ffffff;
        border-radius: 8px 8px 0 0;
        padding: 0.5rem 1rem;
        border: 1px solid var(--border-light);
        border-bottom: none;
    }
    .stTabs [aria-selected="true"] {
        background-color: var(--navy-800) !important;
        color: white !important;
    }

    /* DataFrames */
    div[data-testid="stDataFrame"] {
        border: 1px solid var(--border-light);
        border-radius: 8px;
    }

    /* Metric divider line */
    hr {
        border-top: 1px solid var(--border-light);
    }

    .footer-note {
        color: var(--text-muted);
        font-size: 0.78rem;
        text-align: center;
        margin-top: 2rem;
        padding-top: 1rem;
        border-top: 1px solid var(--border-light);
    }
</style>
"""


def kpi_card_html(label: str, value_str: str, unit: str = "", accent: str = "") -> str:
    accent_cls = f" {accent}" if accent else ""
    return f"""
    <div class="kpi-card{accent_cls}">
        <div class="kpi-label">{label}</div>
        <div class="kpi-value">{value_str} <span class="kpi-unit">{unit}</span></div>
    </div>
    """


def section_header_html(title: str) -> str:
    return f'<div class="section-header">{title}</div>'


def subsection_header_html(title: str) -> str:
    return f'<div class="subsection-header">{title}</div>'


def formula_box_html(text: str) -> str:
    return f'<div class="formula-box">{text}</div>'


def calc_badge_html() -> str:
    return '<span class="calc-badge">Calculated</span>'


def input_badge_html() -> str:
    return '<span class="input-badge">Input</span>'
