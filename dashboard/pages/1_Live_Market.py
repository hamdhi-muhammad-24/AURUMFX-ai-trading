"""Page 1 — Live Market"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd

from config import settings
from core.data_loader import get_candles
from core.feature_engineering import build_features
from dashboard.theme import (
    GLOBAL_CSS, GOLD, GREEN, RED, BLUE, PURPLE, MUTED, PLOTLY_THEME,
    sidebar_logo, page_header, stat_card, section_title, disclaimer_box,
    render_sidebar_nav,
)

st.set_page_config(page_title="Live Market — AURUMFx", page_icon="📈", layout="wide")
st.markdown(GLOBAL_CSS, unsafe_allow_html=True)

with st.sidebar:
    render_sidebar_nav()
    st.markdown("""<div style="font-size:0.68rem;color:#475569">Auto-refresh every 60 seconds when data is live.</div>""", unsafe_allow_html=True)

st.markdown(page_header("Live Market", "Real-time price chart with technical indicators", "📈"), unsafe_allow_html=True)

# ── Controls bar ──────────────────────────────────────────────────────────────
st.markdown("""
<div style="background:#0D1421;border:1px solid #1E2D4A;border-radius:12px;padding:1rem 1.2rem;margin-bottom:1rem">
""", unsafe_allow_html=True)

ctrl1, ctrl2, ctrl3, ctrl4 = st.columns([2, 2, 1, 1])
with ctrl1:
    symbol = st.selectbox("Symbol", settings.SYMBOLS, index=0, label_visibility="visible")
with ctrl2:
    timeframe = st.selectbox("Timeframe", settings.SUPPORTED_TIMEFRAMES, index=1)
with ctrl3:
    n_bars = st.selectbox("Bars", [100, 200, 300, 500, 1000], index=1)
with ctrl4:
    show_bb = st.checkbox("Bollinger", value=True)

st.markdown("</div>", unsafe_allow_html=True)

col_refresh, col_info = st.columns([1, 4])
with col_refresh:
    if st.button("Refresh Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# ── Load data ─────────────────────────────────────────────────────────────────
@st.cache_data(ttl=60)
def load_data(sym, tf, bars):
    df = get_candles(sym, tf, bars)
    if not df.empty:
        df = build_features(df, sym)
    return df

with st.spinner("Loading market data..."):
    df = load_data(symbol, timeframe, n_bars)

if df.empty:
    st.markdown("""
<div style="background:#FF456018;border:1px solid #FF456044;border-radius:12px;padding:2rem;text-align:center">
    <div style="font-size:2rem;margin-bottom:0.5rem">⚠️</div>
    <div style="color:#FF4560;font-weight:700">No data available</div>
    <div style="color:#64748B;font-size:0.82rem;margin-top:0.3rem">Run <code>python run.py --generate-data</code> or check MT5 settings</div>
</div>
""", unsafe_allow_html=True)
    st.stop()

last = df.iloc[-1]
prev = df.iloc[-2] if len(df) > 1 else last
price_change = last["close"] - prev["close"]
pct_change = price_change / prev["close"] * 100
change_color = GREEN if price_change >= 0 else RED
change_arrow = "▲" if price_change >= 0 else "▼"

# ── Price ticker ──────────────────────────────────────────────────────────────
st.markdown(f"""
<div style="
    background: linear-gradient(135deg, #0D1421 0%, #111827 100%);
    border: 1px solid #1E2D4A;
    border-radius: 14px;
    padding: 1.2rem 1.6rem;
    margin-bottom: 1rem;
    display: flex;
    align-items: center;
    gap: 2rem;
    flex-wrap: wrap;
">
    <div>
        <div style="font-size:0.65rem;color:#64748B;text-transform:uppercase;letter-spacing:0.1em;font-weight:700">{symbol} / {timeframe}</div>
        <div style="font-size:2.2rem;font-weight:900;color:#E2E8F0;letter-spacing:-0.02em;line-height:1">{last['close']:.5f}</div>
        <div style="font-size:0.9rem;color:{change_color};font-weight:700;margin-top:0.1rem">
            {change_arrow} {abs(price_change):.5f} &nbsp; ({pct_change:+.2f}%)
        </div>
    </div>
    <div style="display:flex;gap:2rem;flex-wrap:wrap">
        <div>
            <div style="font-size:0.62rem;color:#64748B;text-transform:uppercase;letter-spacing:0.08em">RSI (14)</div>
            <div style="font-size:1.1rem;font-weight:700;color:{'#FF4560' if last.get('rsi',50)>70 else '#00D4A0' if last.get('rsi',50)<30 else '#E2E8F0'}">{last.get('rsi',0):.1f}</div>
        </div>
        <div>
            <div style="font-size:0.62rem;color:#64748B;text-transform:uppercase;letter-spacing:0.08em">ATR (pips)</div>
            <div style="font-size:1.1rem;font-weight:700;color:#E2E8F0">{last.get('atr_pips',0):.1f}</div>
        </div>
        <div>
            <div style="font-size:0.62rem;color:#64748B;text-transform:uppercase;letter-spacing:0.08em">EMA Trend</div>
            <div style="font-size:1.1rem;font-weight:700;color:{'#00D4A0' if str(last.get('ema_trend','')).lower()=='up' else '#FF4560' if str(last.get('ema_trend','')).lower()=='down' else '#F0B90B'}">{str(last.get('ema_trend','—')).upper()}</div>
        </div>
        <div>
            <div style="font-size:0.62rem;color:#64748B;text-transform:uppercase;letter-spacing:0.08em">Session</div>
            <div style="font-size:1.1rem;font-weight:700;color:#3B82F6">{str(last.get('session','—')).title()}</div>
        </div>
        <div>
            <div style="font-size:0.62rem;color:#64748B;text-transform:uppercase;letter-spacing:0.08em">MACD Hist</div>
            <div style="font-size:1.1rem;font-weight:700;color:{'#00D4A0' if last.get('macd_hist',0)>0 else '#FF4560'}">{last.get('macd_hist',0):.5f}</div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# ── Chart ─────────────────────────────────────────────────────────────────────
fig = make_subplots(
    rows=4, cols=1, shared_xaxes=True,
    row_heights=[0.55, 0.15, 0.15, 0.15],
    vertical_spacing=0.015,
    subplot_titles=("", "Volume", "RSI (14)", "MACD"),
)

# Candlesticks
fig.add_trace(go.Candlestick(
    x=df["timestamp"], open=df["open"], high=df["high"],
    low=df["low"], close=df["close"],
    name="OHLC",
    increasing=dict(line=dict(color=GREEN, width=1), fillcolor=GREEN),
    decreasing=dict(line=dict(color=RED, width=1), fillcolor=RED),
), row=1, col=1)

# EMAs
ema_styles = [(20, BLUE, 1.5), (50, GOLD, 1.5), (200, PURPLE, 2)]
for period, color, width in ema_styles:
    col_name = f"ema_{period}"
    if col_name in df.columns:
        fig.add_trace(go.Scatter(
            x=df["timestamp"], y=df[col_name],
            name=f"EMA {period}", line=dict(color=color, width=width),
            opacity=0.85, hovertemplate=f"EMA{period}: %{{y:.5f}}<extra></extra>",
        ), row=1, col=1)

# Bollinger Bands
if show_bb and "bb_upper" in df.columns:
    fig.add_trace(go.Scatter(
        x=df["timestamp"], y=df["bb_upper"], name="BB Upper",
        line=dict(color="rgba(148,163,184,0.4)", dash="dot", width=1), showlegend=False,
    ), row=1, col=1)
    fig.add_trace(go.Scatter(
        x=df["timestamp"], y=df["bb_lower"], name="BB Lower",
        line=dict(color="rgba(148,163,184,0.4)", dash="dot", width=1),
        fill="tonexty", fillcolor="rgba(148,163,184,0.04)", showlegend=False,
    ), row=1, col=1)

# Volume
vol_colors = [GREEN if c >= o else RED for c, o in zip(df["close"], df["open"])]
fig.add_trace(go.Bar(
    x=df["timestamp"], y=df["volume"], name="Volume",
    marker=dict(color=vol_colors, opacity=0.6),
    showlegend=False,
), row=2, col=1)

# RSI
if "rsi" in df.columns:
    fig.add_trace(go.Scatter(
        x=df["timestamp"], y=df["rsi"], name="RSI",
        line=dict(color=GOLD, width=1.8),
        hovertemplate="RSI: %{y:.1f}<extra></extra>",
    ), row=3, col=1)
    # Overbought/oversold fill
    fig.add_hrect(y0=70, y1=100, fillcolor="rgba(255,69,96,0.06)", line_width=0, row=3, col=1)
    fig.add_hrect(y0=0,  y1=30,  fillcolor="rgba(0,212,160,0.06)", line_width=0, row=3, col=1)
    fig.add_hline(y=70, line_dash="dot", line_color="rgba(255,69,96,0.5)", line_width=1, row=3, col=1)
    fig.add_hline(y=30, line_dash="dot", line_color="rgba(0,212,160,0.5)", line_width=1, row=3, col=1)
    fig.add_hline(y=50, line_dash="dot", line_color="rgba(100,116,139,0.3)", line_width=1, row=3, col=1)

# MACD
if "macd_hist" in df.columns:
    hist_colors = [GREEN if v >= 0 else RED for v in df["macd_hist"]]
    fig.add_trace(go.Bar(
        x=df["timestamp"], y=df["macd_hist"], name="Histogram",
        marker=dict(color=hist_colors, opacity=0.7),
        showlegend=False,
    ), row=4, col=1)
    if "macd" in df.columns:
        fig.add_trace(go.Scatter(
            x=df["timestamp"], y=df["macd"], name="MACD",
            line=dict(color=BLUE, width=1.5),
        ), row=4, col=1)
    if "macd_signal" in df.columns:
        fig.add_trace(go.Scatter(
            x=df["timestamp"], y=df["macd_signal"], name="Signal",
            line=dict(color=RED, width=1.5),
        ), row=4, col=1)

fig.update_layout(
    height=820,
    xaxis_rangeslider_visible=False,
    showlegend=True,
    **PLOTLY_THEME,
    legend=dict(
        orientation="h", yanchor="bottom", y=1.01, xanchor="left", x=0,
        bgcolor="#111827", bordercolor="#1E2D4A", borderwidth=1, font=dict(size=11),
    ),
)
fig.update_yaxes(title_text=symbol, row=1, col=1, title_font=dict(size=10))
fig.update_yaxes(title_text="Vol", row=2, col=1, title_font=dict(size=10))
fig.update_yaxes(title_text="RSI", row=3, col=1, range=[0, 100], title_font=dict(size=10))
fig.update_yaxes(title_text="MACD", row=4, col=1, title_font=dict(size=10))
for i in range(1, 5):
    fig.update_xaxes(gridcolor="#1E2D4A", zerolinecolor="#1E2D4A", row=i, col=1)
    fig.update_yaxes(gridcolor="#1E2D4A", zerolinecolor="#1E2D4A", row=i, col=1)

st.plotly_chart(fig, use_container_width=True)

# ── OHLC summary bar ─────────────────────────────────────────────────────────
st.markdown(section_title("Latest Bar OHLC"), unsafe_allow_html=True)
oc1, oc2, oc3, oc4, oc5 = st.columns(5)
oc1.metric("Open",   f"{last['open']:.5f}")
oc2.metric("High",   f"{last['high']:.5f}")
oc3.metric("Low",    f"{last['low']:.5f}")
oc4.metric("Close",  f"{last['close']:.5f}", f"{price_change:+.5f}")
oc5.metric("Volume", f"{int(last['volume']):,}")

# ── Raw data table ────────────────────────────────────────────────────────────
with st.expander("Raw Data Table (last 30 bars)"):
    cols_show = ["timestamp", "open", "high", "low", "close", "volume",
                 "ema_20", "ema_50", "rsi", "macd_hist", "atr_pips", "ema_trend"]
    avail = [c for c in cols_show if c in df.columns]
    st.dataframe(df[avail].tail(30).sort_index(ascending=False), use_container_width=True)

st.markdown(disclaimer_box(), unsafe_allow_html=True)
