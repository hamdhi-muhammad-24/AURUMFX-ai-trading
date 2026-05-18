"""Page 2 — Signals"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import streamlit as st
import plotly.graph_objects as go
import pandas as pd

from config import settings
from dashboard.theme import (
    GLOBAL_CSS, GOLD, GREEN, RED, BLUE, PURPLE, MUTED, PLOTLY_THEME,
    SIGNAL_COLOR, SIGNAL_BG, SIGNAL_EMOJI,
    sidebar_logo, page_header, stat_card, signal_banner, trade_setup_card,
    filter_badge, section_title, disclaimer_box, render_sidebar_nav,
)

st.set_page_config(page_title="Signals — AURUMFx", page_icon="🎯", layout="wide")
st.markdown(GLOBAL_CSS, unsafe_allow_html=True)

with st.sidebar:
    render_sidebar_nav()
    symbol = st.selectbox("Symbol", settings.SYMBOLS, index=0)
    show_last = st.slider("Show last N", 10, 200, 50, 10)

st.markdown(page_header("AI Trading Signals", f"Signal history for {symbol}", "🎯"), unsafe_allow_html=True)


def load_signals(sym: str) -> pd.DataFrame:
    path = settings.SIGNALS_DIR / f"signals_{sym}.csv"
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path, parse_dates=["timestamp"])
    except Exception:
        return pd.DataFrame()


df_sig = load_signals(symbol)

if df_sig.empty:
    st.markdown(f"""
<div style="background:#F0B90B12;border:1px solid #F0B90B33;border-radius:14px;padding:2.5rem;text-align:center">
    <div style="font-size:2.5rem;margin-bottom:0.8rem">🎯</div>
    <div style="color:#F0B90B;font-weight:700;font-size:1rem">No signals yet for {symbol}</div>
    <div style="color:#64748B;font-size:0.82rem;margin-top:0.4rem">
        Go to <strong style="color:#E2E8F0">AI Assistant</strong> and click <strong style="color:#E2E8F0">Run Full Analysis</strong>
    </div>
</div>
""", unsafe_allow_html=True)
    st.stop()

df_sig = df_sig.tail(show_last).reset_index(drop=True)
latest = df_sig.iloc[-1]
sig    = str(latest.get("signal", "NO_TRADE"))
conf   = float(latest.get("confidence", 0))
price  = float(latest.get("price", 0))

# ── Latest signal banner ───────────────────────────────────────────────────────
st.markdown(signal_banner(sig, conf, price, symbol), unsafe_allow_html=True)

# ── Trade setup (if actionable) ──────────────────────────────────────────────
if sig in ("BUY", "SELL"):
    st.markdown(trade_setup_card(
        direction=sig,
        entry=float(latest.get("price", 0)),
        sl=float(latest.get("sl_price", 0)),
        tp=float(latest.get("tp_price", 0)),
        sl_pips=float(latest.get("sl_pips", 0) if "sl_pips" in latest else 0),
        tp_pips=float(latest.get("tp_pips", 0) if "tp_pips" in latest else 0),
        lot=float(latest.get("lot_size", 0)),
        rr=float(latest.get("rr", 0)),
        risk_usd=0.0,
        symbol=symbol,
    ), unsafe_allow_html=True)

# ── Stats row ─────────────────────────────────────────────────────────────────
total   = len(df_sig)
buys    = len(df_sig[df_sig["signal"] == "BUY"])
sells   = len(df_sig[df_sig["signal"] == "SELL"])
blocked = len(df_sig[df_sig["signal"] == "NO_TRADE"])

s1, s2, s3, s4, s5 = st.columns(5)
with s1: st.markdown(stat_card("Total Signals", str(total), "in history", GOLD, "📋"), unsafe_allow_html=True)
with s2: st.markdown(stat_card("BUY Signals", str(buys), f"{buys/total*100:.0f}%" if total else "0%", GREEN, "📈"), unsafe_allow_html=True)
with s3: st.markdown(stat_card("SELL Signals", str(sells), f"{sells/total*100:.0f}%" if total else "0%", RED, "📉"), unsafe_allow_html=True)
with s4: st.markdown(stat_card("Blocked", str(blocked), "filtered out", MUTED, "🚫"), unsafe_allow_html=True)
with s5: st.markdown(stat_card("Avg Confidence", f"{df_sig['confidence'].astype(float).mean():.0%}", "across all", BLUE, "🎯"), unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)
st.markdown(section_title("Signal Confidence History"), unsafe_allow_html=True)

# ── Confidence chart ──────────────────────────────────────────────────────────
fig = go.Figure()

df_sig["confidence_f"] = df_sig["confidence"].astype(float)

for sig_type, color, symbol_marker in [
    ("BUY", GREEN, "triangle-up"),
    ("SELL", RED, "triangle-down"),
    ("HOLD", GOLD, "diamond"),
    ("NO_TRADE", MUTED, "circle-open"),
]:
    mask = df_sig["signal"] == sig_type
    if mask.any():
        fig.add_trace(go.Scatter(
            x=df_sig.loc[mask, "timestamp"],
            y=df_sig.loc[mask, "confidence_f"],
            mode="markers",
            name=sig_type,
            marker=dict(
                color=color, size=12 if sig_type in ("BUY","SELL") else 8,
                symbol=symbol_marker,
                line=dict(color=color, width=1.5),
            ),
            hovertemplate=f"<b>{sig_type}</b><br>Confidence: %{{y:.0%}}<br>%{{x}}<extra></extra>",
        ))

fig.add_hline(
    y=settings.MIN_CONFIDENCE,
    line_dash="dash", line_color=GOLD, line_width=1.5,
    annotation_text=f"Min Confidence ({settings.MIN_CONFIDENCE:.0%})",
    annotation_font_color=GOLD, annotation_font_size=10,
)
fig.add_hrect(y0=0, y1=settings.MIN_CONFIDENCE,
              fillcolor="rgba(255,69,96,0.04)", line_width=0)

fig.update_layout(
    height=300, **PLOTLY_THEME,
    yaxis=dict(tickformat=".0%", range=[0, 1.05], gridcolor="#1E2D4A"),
    xaxis=dict(gridcolor="#1E2D4A"),
    legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="left", x=0,
                bgcolor="#111827", bordercolor="#1E2D4A", borderwidth=1),
)
st.plotly_chart(fig, use_container_width=True)

# ── Distribution pie ──────────────────────────────────────────────────────────
col_pie, col_table = st.columns([1, 2])

with col_pie:
    st.markdown(section_title("Signal Distribution"), unsafe_allow_html=True)
    counts = df_sig["signal"].value_counts()
    pie = go.Figure(go.Pie(
        labels=counts.index.tolist(),
        values=counts.values.tolist(),
        hole=0.55,
        marker_colors=[SIGNAL_COLOR.get(s, MUTED) for s in counts.index],
        textfont=dict(size=11, color="#E2E8F0"),
    ))
    pie.update_layout(
        height=260, **PLOTLY_THEME,
        annotations=[dict(text=f"<b>{total}</b><br>signals", x=0.5, y=0.5,
                          font=dict(size=13, color="#E2E8F0"), showarrow=False)],
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5,
                    bgcolor="rgba(0,0,0,0)", font=dict(size=10)),
        margin=dict(l=0, r=0, t=10, b=10),
    )
    st.plotly_chart(pie, use_container_width=True)

with col_table:
    st.markdown(section_title("Signal Log"), unsafe_allow_html=True)
    display = df_sig[["timestamp","signal","confidence","price","rsi","atr_pips","ema_trend","structure","news_blocked"]
                    ].copy().sort_values("timestamp", ascending=False).reset_index(drop=True)
    display["confidence"] = display["confidence"].astype(float).map(lambda x: f"{x:.0%}")
    st.dataframe(display, use_container_width=True, height=230)

st.markdown(disclaimer_box(), unsafe_allow_html=True)
