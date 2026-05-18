"""Page 6 — AI Assistant"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import json
import streamlit as st
import plotly.graph_objects as go

from config import settings
from dashboard.theme import (
    GLOBAL_CSS, GOLD, GREEN, RED, BLUE, PURPLE, MUTED, PLOTLY_THEME,
    SIGNAL_COLOR, SIGNAL_BG, SIGNAL_EMOJI,
    sidebar_logo, page_header, stat_card, signal_banner, trade_setup_card,
    filter_badge, section_title, disclaimer_box, render_sidebar_nav,
)

st.set_page_config(page_title="AI Assistant — AURUMFx", page_icon="🤖", layout="wide")
st.markdown(GLOBAL_CSS, unsafe_allow_html=True)

with st.sidebar:
    render_sidebar_nav()
    st.markdown("""
<div style="font-size:0.68rem;color:#475569;line-height:1.6">
    The AI agent runs a complete 16-step analysis cycle and generates a full signal with explanation.
</div>
""", unsafe_allow_html=True)

st.markdown(page_header("AI Analysis Assistant", "16-step full market analysis — powered by ML + rules + news", "🤖"), unsafe_allow_html=True)

# ── Config panel ──────────────────────────────────────────────────────────────
st.markdown("""
<div style="background:#0D1421;border:1px solid #1E2D4A;border-radius:14px;padding:1.2rem 1.4rem;margin-bottom:1rem">
""", unsafe_allow_html=True)

cfg1, cfg2, cfg3 = st.columns([2, 2, 1])
with cfg1:
    symbol = st.selectbox("Symbol", settings.SYMBOLS, index=0)
with cfg2:
    timeframe = st.selectbox("Timeframe", settings.SUPPORTED_TIMEFRAMES, index=1)
with cfg3:
    n_bars = st.selectbox("Bars", [300, 500, 800, 1000], index=1)

opt1, opt2, opt3 = st.columns(3)
with opt1: paper_mode    = st.checkbox("Paper trade on signal", value=True)
with opt2: force_retrain = st.checkbox("Force retrain model",   value=False)
with opt3:
    st.checkbox("Demo auto-trade", value=False, disabled=True,
                help="Auto-trading is permanently disabled in this version")

st.markdown("</div>", unsafe_allow_html=True)

# ── Cycle steps display ────────────────────────────────────────────────────────
STEPS = [
    "Fetch candles", "Clean & validate", "Build features", "Detect structure",
    "ML prediction", "Check calendar", "Score sentiment", "Rule engine",
    "Risk approval", "Lot / SL / TP", "Generate signal", "Save signal",
    "Update dashboard", "Explain signal", "Paper trade", "Done",
]

run_clicked = st.button("Run Full Analysis", type="primary", use_container_width=True)

if run_clicked:
    prog_bar = st.progress(0, text="Initialising...")

    try:
        from core.agent import run_cycle

        for i, step in enumerate(STEPS[:-1]):
            prog_bar.progress((i + 1) / len(STEPS), text=f"Step {i+1}/{len(STEPS)} — {step}...")
            import time; time.sleep(0.04)

        with st.spinner("Running analysis..."):
            output = run_cycle(
                symbol=symbol,
                timeframe=timeframe,
                n_bars=int(n_bars),
                force_retrain=force_retrain,
                paper_mode=paper_mode,
            )

        prog_bar.progress(1.0, text="Analysis complete!")
        st.session_state["last_output"] = output.to_dict()

        if output.error:
            st.error(f"Analysis returned an error: {output.error}")
        else:
            st.success("Analysis complete! Results displayed below.")

    except Exception as exc:
        st.error(f"Analysis failed: {exc}")
        import traceback
        with st.expander("Error details"):
            st.code(traceback.format_exc())

# ── Display results ───────────────────────────────────────────────────────────
if "last_output" not in st.session_state:
    st.markdown(f"""
<div style="background:#0D1421;border:1px dashed #1E2D4A;border-radius:14px;padding:3rem;text-align:center;margin-top:1rem">
    <div style="font-size:2.5rem;margin-bottom:0.8rem">🤖</div>
    <div style="color:#E2E8F0;font-weight:700;font-size:1rem">Ready to analyse</div>
    <div style="color:#64748B;font-size:0.82rem;margin-top:0.4rem">Select a symbol and click <strong style="color:#F0B90B">Run Full Analysis</strong></div>
</div>
""", unsafe_allow_html=True)
    st.markdown(disclaimer_box(), unsafe_allow_html=True)
    st.stop()

out  = st.session_state["last_output"]
sig  = out.get("signal", "NO_TRADE")
conf = float(out.get("confidence", 0))
price = float(out.get("price", 0))

# Signal banner
st.markdown("<br>", unsafe_allow_html=True)
st.markdown(signal_banner(sig, conf, price, out.get("symbol", symbol)), unsafe_allow_html=True)

# Trade setup
if sig in ("BUY", "SELL"):
    st.markdown(trade_setup_card(
        direction=sig,
        entry=float(out.get("entry_price", 0)),
        sl=float(out.get("sl_price", 0)),
        tp=float(out.get("tp_price", 0)),
        sl_pips=float(out.get("sl_pips", 0)),
        tp_pips=float(out.get("tp_pips", 0)),
        lot=float(out.get("lot_size", 0)),
        rr=float(out.get("risk_reward", 0)),
        risk_usd=float(out.get("risk_amount", 0)),
        symbol=out.get("symbol", symbol),
    ), unsafe_allow_html=True)

# Paper trade confirmation
if out.get("paper_trade_opened"):
    st.success(f"Paper trade #{out.get('paper_trade_id')} opened. Monitor it in Paper Trading.")

st.markdown("<br>", unsafe_allow_html=True)

# ── Indicator readings ────────────────────────────────────────────────────────
ind_left, ind_right = st.columns([3, 2])

with ind_left:
    st.markdown(section_title("Market Readings"), unsafe_allow_html=True)

    rsi_val  = float(out.get("rsi", 50))
    rsi_col  = RED if rsi_val > 70 else GREEN if rsi_val < 30 else GOLD
    ema_str  = str(out.get("ema_trend","—"))
    ema_col  = GREEN if ema_str=="up" else RED if ema_str=="down" else GOLD
    macd_val = float(out.get("macd_hist",0))
    macd_col = GREEN if macd_val > 0 else RED

    readings = [
        ("Price",      f"{float(out.get('price',0)):.5f}", "#E2E8F0"),
        ("RSI (14)",   f"{rsi_val:.1f}",                   rsi_col),
        ("ATR (pips)", f"{float(out.get('atr_pips',0)):.1f}", BLUE),
        ("EMA Trend",  ema_str.upper(),                     ema_col),
        ("MACD Hist",  f"{macd_val:.5f}",                  macd_col),
        ("Structure",  str(out.get("structure_label","—")).replace("_"," ").title(), PURPLE),
        ("BOS",        str(out.get("bos","none")).title(),  GOLD),
        ("Volatility", str(out.get("volatility_regime","—")).title(), MUTED),
    ]

    rows_html = "".join(f"""
<div style="display:flex;justify-content:space-between;align-items:center;
            padding:0.55rem 0;border-bottom:1px solid #1E2D4A11">
    <span style="font-size:0.78rem;color:#64748B">{label}</span>
    <span style="font-size:0.88rem;font-weight:700;color:{color}">{value}</span>
</div>
""" for label, value, color in readings)

    st.markdown(f"""
<div style="background:#0D1421;border:1px solid #1E2D4A;border-radius:12px;padding:1rem 1.2rem">
    {rows_html}
</div>
""", unsafe_allow_html=True)

with ind_right:
    st.markdown(section_title("ML Probabilities"), unsafe_allow_html=True)
    probs = out.get("ml_probabilities", {})
    if probs:
        prob_colors = {"BUY": GREEN, "SELL": RED, "HOLD": GOLD}
        for label, prob in probs.items():
            pct = float(prob) * 100
            bar_color = prob_colors.get(label, BLUE)
            st.markdown(f"""
<div style="margin-bottom:0.8rem">
    <div style="display:flex;justify-content:space-between;margin-bottom:0.3rem">
        <span style="font-size:0.78rem;color:#E2E8F0;font-weight:600">{label}</span>
        <span style="font-size:0.78rem;color:{bar_color};font-weight:700">{pct:.1f}%</span>
    </div>
    <div style="background:#1E2D4A;border-radius:999px;height:8px;overflow:hidden">
        <div style="width:{pct}%;height:100%;background:linear-gradient(90deg,{bar_color}99,{bar_color});border-radius:999px;transition:width 0.5s"></div>
    </div>
</div>
""", unsafe_allow_html=True)
        st.markdown(f"""
<div style="font-size:0.72rem;color:#64748B;margin-top:0.5rem">
    Model: <strong style="color:#E2E8F0">{out.get('ml_model_used','—').upper()}</strong>
    &nbsp;&bull;&nbsp;
    ML signal: <strong style="color:{SIGNAL_COLOR.get(out.get('ml_signal',''), MUTED)}">{out.get('ml_signal','—')}</strong>
    @ <strong style="color:#E2E8F0">{float(out.get('ml_confidence',0)):.0%}</strong>
</div>
""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── Filters ────────────────────────────────────────────────────────────────────
f_left, f_right = st.columns(2)

with f_left:
    st.markdown(section_title("Blocking Filters"), unsafe_allow_html=True)
    blocks = out.get("blocks", [])
    if blocks:
        for b in blocks:
            st.markdown(filter_badge(b, "block"), unsafe_allow_html=True)
    else:
        st.markdown(f"""
<div style="background:{GREEN}0F;border:1px solid {GREEN}33;border-radius:8px;padding:0.6rem 0.8rem;font-size:0.78rem;color:{GREEN}">
    No filters blocked this signal
</div>
""", unsafe_allow_html=True)

with f_right:
    st.markdown(section_title("Supporting Factors"), unsafe_allow_html=True)
    supports = out.get("supports", [])
    if supports:
        for s in supports:
            st.markdown(filter_badge(s, "support"), unsafe_allow_html=True)
    else:
        st.markdown(f"""
<div style="background:#64748B0F;border:1px solid #64748B33;border-radius:8px;padding:0.6rem 0.8rem;font-size:0.78rem;color:#64748B">
    No supporting factors recorded
</div>
""", unsafe_allow_html=True)

# ── News status ────────────────────────────────────────────────────────────────
news_col, _ = st.columns([1, 2])
with news_col:
    news_blocked = out.get("news_blocked", False)
    news_color = RED if news_blocked else GREEN
    st.markdown(f"""
<div style="background:{news_color}0F;border:1px solid {news_color}33;border-radius:10px;padding:0.8rem 1rem;margin-top:0.5rem">
    <div style="font-size:0.72rem;color:#64748B;text-transform:uppercase;letter-spacing:0.06em">News Status</div>
    <div style="font-size:0.9rem;font-weight:700;color:{news_color};margin-top:0.2rem">
        {'BLOCKED' if news_blocked else 'CLEAR'}
    </div>
    <div style="font-size:0.72rem;color:#64748B;margin-top:0.2rem">
        Sentiment: {float(out.get('news_sentiment',0)):+.2f} &nbsp;|&nbsp; {out.get('news_reason','') or 'No block reason'}
    </div>
</div>
""", unsafe_allow_html=True)

# ── Explanation ────────────────────────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
st.markdown(section_title("Analysis Explanation"), unsafe_allow_html=True)

explanation = out.get("explanation", "No explanation available.")
# Strip non-ASCII for safe rendering
explanation_clean = explanation.encode("ascii", errors="replace").decode("ascii").replace("?", "")

st.markdown(f"""
<div style="
    background: linear-gradient(135deg, #0D1421 0%, #111827 100%);
    border: 1px solid #1E2D4A;
    border-radius: 14px;
    padding: 1.5rem;
    line-height: 1.7;
    font-size: 0.88rem;
    color: #94a3b8;
">
    {explanation_clean.replace(chr(10), '<br>')}
</div>
""", unsafe_allow_html=True)

# ── Raw JSON ──────────────────────────────────────────────────────────────────
with st.expander("Raw Signal JSON"):
    st.code(json.dumps(out, indent=2, default=str), language="json")

st.markdown(disclaimer_box(), unsafe_allow_html=True)
