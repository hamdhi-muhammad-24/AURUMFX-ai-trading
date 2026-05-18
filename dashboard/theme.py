"""
AURUMFx Dashboard Theme
Shared CSS, colors, and HTML helpers for all pages.
"""
import streamlit as st

# ── Brand palette ─────────────────────────────────────────────────────────────
GOLD   = "#F0B90B"
GOLD2  = "#FFD700"
GREEN  = "#00D4A0"
RED    = "#FF4560"
BLUE   = "#3B82F6"
PURPLE = "#8B5CF6"
BG     = "#0A0E1A"
CARD   = "#0D1421"
CARD2  = "#111827"
BORDER = "#1E2D4A"
TEXT   = "#E2E8F0"
MUTED  = "#64748B"

SIGNAL_COLOR = {
    "BUY":      GREEN,
    "SELL":     RED,
    "HOLD":     GOLD,
    "NO_TRADE": MUTED,
}

SIGNAL_BG = {
    "BUY":      "rgba(0,212,160,0.12)",
    "SELL":     "rgba(255,69,96,0.12)",
    "HOLD":     "rgba(240,185,11,0.12)",
    "NO_TRADE": "rgba(100,116,139,0.12)",
}

SIGNAL_EMOJI = {
    "BUY":      "BUY",
    "SELL":     "SELL",
    "HOLD":     "HOLD",
    "NO_TRADE": "NO TRADE",
}


# ── Global CSS injected into every page ────────────────────────────────────────
GLOBAL_CSS = """
<style>
/* ── Base & fonts ─────────────────────────────── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
}

/* Hide default Streamlit header */
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding-top: 1.2rem !important; padding-bottom: 2rem !important; }

/* ── Sidebar ───────────────────────────────────── */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #050911 0%, #0a1428 100%) !important;
    border-right: 1px solid #1E2D4A !important;
}
section[data-testid="stSidebar"] .stMarkdown p,
section[data-testid="stSidebar"] .stMarkdown span {
    color: #94a3b8 !important;
}

/* ── Metric cards ──────────────────────────────── */
[data-testid="metric-container"] {
    background: linear-gradient(135deg, #0D1421 0%, #111827 100%);
    border: 1px solid #1E2D4A;
    border-radius: 12px;
    padding: 1rem 1.2rem;
    transition: border-color 0.2s, transform 0.2s;
}
[data-testid="metric-container"]:hover {
    border-color: #F0B90B55;
    transform: translateY(-2px);
}
[data-testid="stMetricLabel"] {
    color: #64748B !important;
    font-size: 0.72rem !important;
    font-weight: 600 !important;
    text-transform: uppercase;
    letter-spacing: 0.08em;
}
[data-testid="stMetricValue"] {
    color: #E2E8F0 !important;
    font-size: 1.45rem !important;
    font-weight: 700 !important;
}
[data-testid="stMetricDelta"] svg { display: none; }

/* ── Buttons ───────────────────────────────────── */
.stButton > button {
    background: linear-gradient(135deg, #F0B90B 0%, #FFD700 100%) !important;
    color: #050911 !important;
    font-weight: 700 !important;
    font-size: 0.9rem !important;
    border: none !important;
    border-radius: 10px !important;
    padding: 0.55rem 1.4rem !important;
    letter-spacing: 0.03em;
    transition: opacity 0.2s, transform 0.15s !important;
    box-shadow: 0 4px 20px rgba(240,185,11,0.25) !important;
}
.stButton > button:hover {
    opacity: 0.88 !important;
    transform: translateY(-1px) !important;
}
.stButton > button[kind="secondary"] {
    background: linear-gradient(135deg, #1E2D4A 0%, #0D1421 100%) !important;
    color: #E2E8F0 !important;
    border: 1px solid #1E2D4A !important;
    box-shadow: none !important;
}

/* ── SelectBox & Input ─────────────────────────── */
[data-baseweb="select"] > div {
    background-color: #0D1421 !important;
    border: 1px solid #1E2D4A !important;
    border-radius: 10px !important;
    color: #E2E8F0 !important;
}
[data-baseweb="select"] > div:focus-within {
    border-color: #F0B90B !important;
    box-shadow: 0 0 0 2px rgba(240,185,11,0.15) !important;
}
.stNumberInput input, .stTextInput input {
    background: #0D1421 !important;
    border: 1px solid #1E2D4A !important;
    border-radius: 10px !important;
    color: #E2E8F0 !important;
}
.stNumberInput input:focus, .stTextInput input:focus {
    border-color: #F0B90B !important;
    box-shadow: 0 0 0 2px rgba(240,185,11,0.15) !important;
}
label[data-testid="stWidgetLabel"] p {
    color: #94a3b8 !important;
    font-size: 0.78rem !important;
    font-weight: 600 !important;
    text-transform: uppercase;
    letter-spacing: 0.06em;
}

/* ── Sliders ───────────────────────────────────── */
[data-testid="stSlider"] [data-baseweb="slider"] div[role="slider"] {
    background: #F0B90B !important;
    border-color: #F0B90B !important;
}

/* ── Checkboxes ─────────────────────────────────── */
[data-testid="stCheckbox"] label p { color: #94a3b8 !important; }

/* ── Dataframes / Tables ────────────────────────── */
[data-testid="stDataFrame"] {
    border: 1px solid #1E2D4A !important;
    border-radius: 12px !important;
    overflow: hidden !important;
}
.stDataFrame thead tr th {
    background: #111827 !important;
    color: #64748B !important;
    font-size: 0.72rem !important;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    border-bottom: 1px solid #1E2D4A !important;
}
.stDataFrame tbody tr:hover { background: #1E2D4A22 !important; }

/* ── Tabs ───────────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] {
    background: #0D1421 !important;
    border-radius: 12px !important;
    padding: 4px !important;
    gap: 4px !important;
    border: 1px solid #1E2D4A !important;
}
.stTabs [data-baseweb="tab"] {
    background: transparent !important;
    border-radius: 9px !important;
    color: #64748B !important;
    font-weight: 600 !important;
    font-size: 0.82rem !important;
    padding: 0.45rem 1rem !important;
}
.stTabs [aria-selected="true"] {
    background: linear-gradient(135deg, #F0B90B22, #F0B90B11) !important;
    color: #F0B90B !important;
    border: 1px solid #F0B90B33 !important;
}

/* ── Expanders ──────────────────────────────────── */
[data-testid="stExpander"] {
    background: #0D1421 !important;
    border: 1px solid #1E2D4A !important;
    border-radius: 12px !important;
}
[data-testid="stExpander"] summary {
    color: #94a3b8 !important;
    font-weight: 600 !important;
}

/* ── Alerts / Info boxes ────────────────────────── */
.stAlert {
    border-radius: 10px !important;
    border-left-width: 4px !important;
}

/* ── Divider ────────────────────────────────────── */
hr { border-color: #1E2D4A !important; margin: 1rem 0 !important; }

/* ── Spinner ────────────────────────────────────── */
.stSpinner > div { border-color: #F0B90B !important; }

/* ── Progress bar ───────────────────────────────── */
[data-testid="stProgressBar"] > div { background: #F0B90B !important; }

/* ── Plotly charts ──────────────────────────────── */
.js-plotly-plot .plotly { border-radius: 12px !important; }

/* ── Scrollbar ──────────────────────────────────── */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: #0A0E1A; }
::-webkit-scrollbar-thumb { background: #1E2D4A; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #F0B90B44; }
</style>
"""


# ── Re-usable HTML components ─────────────────────────────────────────────────

def page_header(title: str, subtitle: str = "", icon: str = "") -> str:
    return f"""
<div style="
    background: linear-gradient(135deg, #0D1421 0%, #111827 100%);
    border: 1px solid #1E2D4A;
    border-left: 4px solid #F0B90B;
    border-radius: 14px;
    padding: 1.4rem 1.8rem;
    margin-bottom: 1.5rem;
">
    <div style="display:flex; align-items:center; gap:0.8rem;">
        <span style="font-size:2rem">{icon}</span>
        <div>
            <h1 style="margin:0; color:#E2E8F0; font-size:1.6rem; font-weight:800; letter-spacing:-0.02em">{title}</h1>
            {f'<p style="margin:0.2rem 0 0; color:#64748B; font-size:0.85rem">{subtitle}</p>' if subtitle else ''}
        </div>
    </div>
</div>
"""


def signal_banner(signal: str, confidence: float, price: float, symbol: str) -> str:
    color = SIGNAL_COLOR.get(signal, MUTED)
    bg    = SIGNAL_BG.get(signal, "rgba(100,116,139,0.12)")
    label = SIGNAL_EMOJI.get(signal, signal)
    arrow = {"BUY": "&#x25B2;", "SELL": "&#x25BC;", "HOLD": "&#x25A0;", "NO_TRADE": "&#x2715;"}.get(signal, "")
    return f"""
<div style="
    background: {bg};
    border: 2px solid {color}55;
    border-radius: 18px;
    padding: 2rem;
    text-align: center;
    margin: 1rem 0;
    position: relative;
    overflow: hidden;
">
    <div style="
        position:absolute; top:0; left:0; right:0; height:3px;
        background: linear-gradient(90deg, transparent, {color}, transparent);
    "></div>
    <div style="font-size:0.8rem; color:{color}; text-transform:uppercase; letter-spacing:0.15em; font-weight:700; margin-bottom:0.5rem">
        AI Signal &bull; {symbol}
    </div>
    <div style="font-size:3rem; font-weight:900; color:{color}; letter-spacing:-0.02em; line-height:1">
        {arrow} {label}
    </div>
    <div style="font-size:1rem; color:#94a3b8; margin-top:0.6rem">
        Confidence &nbsp;<span style="color:{color}; font-weight:700; font-size:1.2rem">{confidence:.0%}</span>
        &nbsp;&nbsp;&bull;&nbsp;&nbsp;
        Price &nbsp;<span style="color:#E2E8F0; font-weight:600">{price:.5f}</span>
    </div>
</div>
"""


def stat_card(title: str, value: str, sub: str = "", color: str = GOLD, icon: str = "") -> str:
    return f"""
<div style="
    background: linear-gradient(135deg, #0D1421 0%, #111827 100%);
    border: 1px solid #1E2D4A;
    border-top: 3px solid {color};
    border-radius: 14px;
    padding: 1.2rem 1.4rem;
    height: 100%;
    transition: transform 0.2s;
">
    <div style="display:flex; justify-content:space-between; align-items:flex-start">
        <div>
            <div style="font-size:0.7rem; color:#64748B; font-weight:700; text-transform:uppercase; letter-spacing:0.08em; margin-bottom:0.4rem">
                {title}
            </div>
            <div style="font-size:1.6rem; color:#E2E8F0; font-weight:800; line-height:1.1">
                {value}
            </div>
            {f'<div style="font-size:0.78rem; color:#64748B; margin-top:0.3rem">{sub}</div>' if sub else ''}
        </div>
        {f'<div style="font-size:1.8rem; opacity:0.6">{icon}</div>' if icon else ''}
    </div>
</div>
"""


def trade_setup_card(direction: str, entry: float, sl: float, tp: float,
                     sl_pips: float, tp_pips: float, lot: float, rr: float, risk_usd: float, symbol: str) -> str:
    color = GREEN if direction == "BUY" else RED
    arrow = "&#x25B2;" if direction == "BUY" else "&#x25BC;"
    return f"""
<div style="
    background: linear-gradient(135deg, #0D1421 0%, #111827 100%);
    border: 1px solid {color}44;
    border-radius: 16px;
    padding: 1.5rem;
    margin: 0.8rem 0;
">
    <div style="font-size:0.75rem; color:{color}; font-weight:700; text-transform:uppercase; letter-spacing:0.1em; margin-bottom:1rem">
        {arrow} {direction} Setup &bull; {symbol}
    </div>
    <div style="display:grid; grid-template-columns:repeat(5,1fr); gap:0.8rem; text-align:center">
        <div>
            <div style="font-size:0.65rem; color:#64748B; text-transform:uppercase; letter-spacing:0.06em">Entry</div>
            <div style="font-size:1rem; color:#E2E8F0; font-weight:700; margin-top:0.2rem">{entry:.5f}</div>
        </div>
        <div>
            <div style="font-size:0.65rem; color:#64748B; text-transform:uppercase; letter-spacing:0.06em">Stop Loss</div>
            <div style="font-size:1rem; color:{RED}; font-weight:700; margin-top:0.2rem">{sl:.5f}</div>
            <div style="font-size:0.7rem; color:#475569">{sl_pips:.1f} pips</div>
        </div>
        <div>
            <div style="font-size:0.65rem; color:#64748B; text-transform:uppercase; letter-spacing:0.06em">Take Profit</div>
            <div style="font-size:1rem; color:{GREEN}; font-weight:700; margin-top:0.2rem">{tp:.5f}</div>
            <div style="font-size:0.7rem; color:#475569">{tp_pips:.1f} pips</div>
        </div>
        <div>
            <div style="font-size:0.65rem; color:#64748B; text-transform:uppercase; letter-spacing:0.06em">Risk/Reward</div>
            <div style="font-size:1rem; color:{GOLD}; font-weight:700; margin-top:0.2rem">1:{rr:.2f}</div>
        </div>
        <div>
            <div style="font-size:0.65rem; color:#64748B; text-transform:uppercase; letter-spacing:0.06em">Lot / Risk</div>
            <div style="font-size:1rem; color:#E2E8F0; font-weight:700; margin-top:0.2rem">{lot}</div>
            <div style="font-size:0.7rem; color:#475569">${risk_usd:.2f}</div>
        </div>
    </div>
</div>
"""


def filter_badge(text: str, kind: str = "block") -> str:
    color = RED if kind == "block" else GREEN
    icon  = "&#x2715;" if kind == "block" else "&#x2713;"
    return f"""<span style="
        display:inline-flex; align-items:center; gap:0.3rem;
        background:{color}18; border:1px solid {color}44;
        color:{color}; border-radius:999px;
        padding:0.2rem 0.7rem; font-size:0.72rem; font-weight:600;
        margin: 0.15rem;
    ">{icon} {text}</span>"""


def section_title(text: str, color: str = GOLD) -> str:
    return f"""
<div style="
    display:flex; align-items:center; gap:0.6rem;
    margin: 1.2rem 0 0.7rem;
">
    <div style="width:3px; height:1.1rem; background:{color}; border-radius:2px"></div>
    <span style="color:#E2E8F0; font-size:0.9rem; font-weight:700; letter-spacing:0.01em">{text}</span>
</div>
"""


PLOTLY_THEME = dict(
    template="plotly_dark",
    paper_bgcolor="#0D1421",
    plot_bgcolor="#0D1421",
    font=dict(family="Inter", color="#94a3b8", size=11),
    margin=dict(l=10, r=10, t=30, b=10),
    legend=dict(
        bgcolor="#111827",
        bordercolor="#1E2D4A",
        borderwidth=1,
        font=dict(size=11),
    ),
    xaxis=dict(gridcolor="#1E2D4A", zerolinecolor="#1E2D4A"),
    yaxis=dict(gridcolor="#1E2D4A", zerolinecolor="#1E2D4A"),
)


def sidebar_logo():
    return """
<div style="padding: 0.5rem 0 1rem;">
    <div style="
        background: linear-gradient(135deg, #F0B90B 0%, #FFD700 100%);
        border-radius: 12px;
        padding: 0.7rem 1rem;
        text-align: center;
        margin-bottom: 0.5rem;
    ">
        <div style="font-size:1.3rem; font-weight:900; color:#050911; letter-spacing:0.05em">
            AURUM<span style="opacity:0.7">Fx</span>
        </div>
        <div style="font-size:0.6rem; color:#050911; opacity:0.7; letter-spacing:0.15em; font-weight:700">
            AI TRADING SYSTEM
        </div>
    </div>
    <div style="font-size:0.65rem; color:#475569; text-align:center; letter-spacing:0.08em">
        v1.0.0 &bull; SIGNAL PREDICTION
    </div>
</div>
"""


def disclaimer_box() -> str:
    return """
<div style="
    background: rgba(240,185,11,0.06);
    border: 1px solid rgba(240,185,11,0.2);
    border-radius: 10px;
    padding: 0.7rem 1rem;
    margin-top: 1rem;
    font-size: 0.72rem;
    color: #64748B;
    line-height: 1.5;
">
    <strong style="color:#F0B90B">Disclaimer:</strong>
    This is not financial advice. All signals are probabilistic estimates for
    educational and decision-support purposes only. Never risk more than you can afford to lose.
</div>
"""


def render_sidebar_nav() -> None:
    """Render the shared logo + navigation links inside st.sidebar context."""
    st.markdown(sidebar_logo(), unsafe_allow_html=True)
    st.page_link("app.py",                        label="Home",          icon="🏠")
    st.page_link("pages/1_Live_Market.py",         label="Live Market",   icon="📈")
    st.page_link("pages/2_Signals.py",             label="Signals",       icon="🎯")
    st.page_link("pages/3_Paper_Trading.py",       label="Paper Trading", icon="📝")
    st.page_link("pages/4_Backtesting.py",         label="Backtesting",   icon="📊")
    st.page_link("pages/5_News_Risk.py",           label="News Risk",     icon="📰")
    st.page_link("pages/6_AI_Assistant.py",        label="AI Assistant",  icon="🤖")
    st.page_link("pages/7_Settings.py",            label="Settings",      icon="⚙️")
    st.markdown("<hr>", unsafe_allow_html=True)
