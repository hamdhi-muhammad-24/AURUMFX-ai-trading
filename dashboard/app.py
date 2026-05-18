"""AURUMFx AI Trading — Home Page"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from dashboard.theme import (
    GLOBAL_CSS, GOLD, GREEN, RED, BLUE, PURPLE, CARD, BORDER, TEXT, MUTED,
    sidebar_logo, disclaimer_box, stat_card, section_title, page_header,
    render_sidebar_nav,
)

st.set_page_config(
    page_title="AURUMFx AI Trading",
    page_icon="🟡",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(GLOBAL_CSS, unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    render_sidebar_nav()
    st.markdown("""
<div style="font-size:0.68rem; color:#475569; line-height:1.6; padding:0 0.2rem">
    <strong style="color:#F0B90B">AURUMFx</strong> combines ML prediction,
    technical analysis, market structure, and news filters to generate
    probabilistic trading signals.<br><br>
    Auto-trading is <strong style="color:#FF4560">DISABLED</strong> by default.
    This system operates in signal &amp; paper-trade mode only.
</div>
""", unsafe_allow_html=True)

# ── Hero section ──────────────────────────────────────────────────────────────
st.markdown("""
<div style="
    background: linear-gradient(135deg, #0D1421 0%, #0a1428 50%, #0D1421 100%);
    border: 1px solid #1E2D4A;
    border-radius: 20px;
    padding: 3rem 2.5rem;
    text-align: center;
    margin-bottom: 2rem;
    position: relative;
    overflow: hidden;
">
    <div style="
        position:absolute; top:-60px; left:50%; transform:translateX(-50%);
        width:300px; height:300px;
        background: radial-gradient(circle, rgba(240,185,11,0.08) 0%, transparent 70%);
        pointer-events:none;
    "></div>
    <div style="
        display:inline-block;
        background: linear-gradient(135deg, #F0B90B 0%, #FFD700 100%);
        border-radius: 16px;
        padding: 0.6rem 1.4rem;
        font-size: 0.75rem;
        font-weight: 800;
        color: #050911;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        margin-bottom: 1.2rem;
    ">
        AI-Powered Signal Prediction
    </div>
    <h1 style="
        font-size: 2.8rem;
        font-weight: 900;
        color: #E2E8F0;
        letter-spacing: -0.03em;
        margin: 0 0 0.8rem;
        line-height: 1.1;
    ">
        AURUM<span style="color:#F0B90B">Fx</span> Trading System
    </h1>
    <p style="
        font-size: 1rem;
        color: #64748B;
        max-width: 620px;
        margin: 0 auto 2rem;
        line-height: 1.6;
    ">
        Machine learning + technical analysis + market structure + economic calendar filters
        — combined into one intelligent signal engine for Forex & Gold.
    </p>
    <div style="display:flex; justify-content:center; gap:0.8rem; flex-wrap:wrap">
        <span style="background:#00D4A018;border:1px solid #00D4A044;color:#00D4A0;border-radius:999px;padding:0.35rem 1rem;font-size:0.78rem;font-weight:600">
            EUR/USD
        </span>
        <span style="background:#F0B90B18;border:1px solid #F0B90B44;color:#F0B90B;border-radius:999px;padding:0.35rem 1rem;font-size:0.78rem;font-weight:600">
            XAU/USD (Gold)
        </span>
        <span style="background:#3B82F618;border:1px solid #3B82F644;color:#3B82F6;border-radius:999px;padding:0.35rem 1rem;font-size:0.78rem;font-weight:600">
            GBP/USD
        </span>
        <span style="background:#8B5CF618;border:1px solid #8B5CF644;color:#8B5CF6;border-radius:999px;padding:0.35rem 1rem;font-size:0.78rem;font-weight:600">
            USD/JPY
        </span>
        <span style="background:#64748B18;border:1px solid #64748B44;color:#94a3b8;border-radius:999px;padding:0.35rem 1rem;font-size:0.78rem;font-weight:600">
            +4 more pairs
        </span>
    </div>
</div>
""", unsafe_allow_html=True)

# ── Stats row ─────────────────────────────────────────────────────────────────
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(stat_card("Supported Pairs", "8", "Forex + Gold", GOLD, "💱"), unsafe_allow_html=True)
with c2:
    st.markdown(stat_card("ML Models", "3", "LR + RF + XGBoost", BLUE, "🤖"), unsafe_allow_html=True)
with c3:
    st.markdown(stat_card("Risk Filters", "10+", "Rules + news + structure", PURPLE, "🛡️"), unsafe_allow_html=True)
with c4:
    st.markdown(stat_card("Auto-Trading", "DISABLED", "Signal mode only", RED, "🔒"), unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── Feature cards ─────────────────────────────────────────────────────────────
st.markdown(section_title("System Modules"), unsafe_allow_html=True)

features = [
    ("📈", "Live Market Data", "Real-time candle charts with EMA, RSI, MACD, ATR, Bollinger Bands. MT5 or CSV fallback.", "1_Live_Market"),
    ("🎯", "AI Signal Engine", "ML prediction (LR + RF + XGBoost) combined with 10+ rule-based filters.", "2_Signals"),
    ("📝", "Paper Trading", "Virtual trading with real prices. SL/TP tracking, equity curve, journal export.", "3_Paper_Trading"),
    ("📊", "Backtesting", "Walk-forward historical simulation. Win rate, profit factor, drawdown metrics.", "4_Backtesting"),
    ("📰", "News Risk", "Economic calendar blocking + keyword sentiment scoring for all major currencies.", "5_News_Risk"),
    ("🤖", "AI Assistant", "16-step full analysis cycle with plain-English explanation of every signal.", "6_AI_Assistant"),
]

cols = st.columns(3)
for i, (icon, title, desc, page) in enumerate(features):
    with cols[i % 3]:
        st.markdown(f"""
<div style="
    background: linear-gradient(135deg, #0D1421 0%, #111827 100%);
    border: 1px solid #1E2D4A;
    border-radius: 16px;
    padding: 1.4rem;
    margin-bottom: 1rem;
    height: 100%;
    transition: border-color 0.2s;
" onmouseover="this.style.borderColor='#F0B90B44'" onmouseout="this.style.borderColor='#1E2D4A'">
    <div style="font-size:1.8rem; margin-bottom:0.6rem">{icon}</div>
    <div style="font-size:0.9rem; font-weight:700; color:#E2E8F0; margin-bottom:0.4rem">{title}</div>
    <div style="font-size:0.78rem; color:#64748B; line-height:1.5">{desc}</div>
</div>
""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── Quick start ────────────────────────────────────────────────────────────────
st.markdown(section_title("Quick Start Guide"), unsafe_allow_html=True)

steps = [
    ("1", "Generate / Load Data", "Run `python run.py --generate-data` or add MT5 credentials in Settings.", GOLD),
    ("2", "Run AI Analysis", "Go to AI Assistant and click Run Full Analysis for a signal.", BLUE),
    ("3", "Review the Signal", "Check the signal confidence, trade setup (SL/TP), and explanation.", GREEN),
    ("4", "Paper Trade", "Monitor virtual trades in Paper Trading. No real money at risk.", PURPLE),
    ("5", "Backtest Strategy", "Validate the strategy on historical data in the Backtesting page.", RED),
]

for num, title, desc, color in steps:
    st.markdown(f"""
<div style="
    display:flex; align-items:center; gap:1rem;
    background: linear-gradient(135deg, #0D1421 0%, #111827 100%);
    border: 1px solid #1E2D4A;
    border-left: 3px solid {color};
    border-radius: 12px;
    padding: 1rem 1.2rem;
    margin-bottom: 0.5rem;
">
    <div style="
        min-width:2rem; height:2rem;
        background: {color}22; border: 1px solid {color}44;
        border-radius: 50%; display:flex; align-items:center; justify-content:center;
        font-size:0.8rem; font-weight:800; color:{color};
    ">{num}</div>
    <div>
        <div style="font-size:0.85rem; font-weight:700; color:#E2E8F0">{title}</div>
        <div style="font-size:0.75rem; color:#64748B; margin-top:0.1rem">{desc}</div>
    </div>
</div>
""", unsafe_allow_html=True)

st.markdown(disclaimer_box(), unsafe_allow_html=True)
