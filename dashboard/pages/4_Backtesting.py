"""Page 4 — Backtesting"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import json
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd

from config import settings
from dashboard.theme import (
    GLOBAL_CSS, GOLD, GREEN, RED, BLUE, PURPLE, MUTED, PLOTLY_THEME,
    sidebar_logo, page_header, stat_card, section_title, disclaimer_box,
    render_sidebar_nav,
)

st.set_page_config(page_title="Backtesting — AURUMFx", page_icon="📊", layout="wide")
st.markdown(GLOBAL_CSS, unsafe_allow_html=True)

with st.sidebar:
    render_sidebar_nav()
    symbol    = st.selectbox("Symbol", settings.SYMBOLS, index=0)
    timeframe = st.selectbox("Timeframe", settings.SUPPORTED_TIMEFRAMES, index=1)
    init_bal  = st.number_input("Initial Balance ($)", value=10_000, step=1_000)

st.markdown(page_header("Backtesting", "Walk-forward historical strategy simulation", "📊"), unsafe_allow_html=True)

# ── Run button ─────────────────────────────────────────────────────────────────
if st.button("Run Backtest Now", use_container_width=True):
    with st.spinner("Running backtest — training models and simulating trades..."):
        try:
            from core.data_loader import get_candles
            from core.backtester import run_backtest, save_backtest_result
            from core.risk_manager import RiskParams

            df = get_candles(symbol, timeframe, n_bars=settings.TRAIN_LOOKBACK)
            if df.empty:
                st.error("No data available for backtesting.")
            else:
                result = run_backtest(df, symbol, timeframe, float(init_bal), RiskParams(balance=float(init_bal)))
                save_backtest_result(result)
                st.session_state["bt_result"] = result.to_dict()
                st.success(f"Backtest complete! {result.total_trades} trades simulated.")
                st.rerun()
        except Exception as exc:
            st.error(f"Backtest error: {exc}")


def load_result(sym, tf):
    if "bt_result" in st.session_state:
        return st.session_state["bt_result"]
    path = settings.BACKTEST_DIR / f"backtest_{sym}_{tf}.json"
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return None


result = load_result(symbol, timeframe)

if result is None:
    st.markdown(f"""
<div style="background:#3B82F612;border:1px solid #3B82F633;border-radius:14px;padding:3rem;text-align:center">
    <div style="font-size:2.5rem;margin-bottom:0.8rem">📊</div>
    <div style="color:#3B82F6;font-weight:700;font-size:1rem">No backtest results yet for {symbol} {timeframe}</div>
    <div style="color:#64748B;font-size:0.82rem;margin-top:0.4rem">Click <strong style="color:#E2E8F0">Run Backtest Now</strong> above</div>
</div>
""", unsafe_allow_html=True)
    st.stop()

# ── Performance metrics ───────────────────────────────────────────────────────
pnl = result["final_balance"] - result["initial_balance"]
pnl_color = GREEN if pnl >= 0 else RED
win_color  = GREEN if result["win_rate"] >= 50 else RED
pf_color   = GREEN if result["profit_factor"] >= 1 else RED
dd_color   = RED if result["max_drawdown_pct"] > 15 else GOLD if result["max_drawdown_pct"] > 8 else GREEN

st.markdown(section_title("Performance Summary"), unsafe_allow_html=True)
c1, c2, c3, c4 = st.columns(4)
with c1: st.markdown(stat_card("Final Balance", f"${result['final_balance']:,.2f}", f"P/L: ${pnl:+,.2f}", pnl_color, "💰"), unsafe_allow_html=True)
with c2: st.markdown(stat_card("Win Rate",      f"{result['win_rate']:.1f}%",       f"{result['winning_trades']}W / {result['losing_trades']}L", win_color, "🏆"), unsafe_allow_html=True)
with c3: st.markdown(stat_card("Profit Factor", f"{result['profit_factor']:.3f}",   "> 1.0 is profitable", pf_color, "📈"), unsafe_allow_html=True)
with c4: st.markdown(stat_card("Max Drawdown",  f"{result['max_drawdown_pct']:.1f}%", "peak-to-trough", dd_color, "📉"), unsafe_allow_html=True)

c5, c6, c7, c8 = st.columns(4)
with c5: st.markdown(stat_card("Total Trades",  str(result["total_trades"]),         "", BLUE,   "📋"), unsafe_allow_html=True)
with c6: st.markdown(stat_card("Total Pips",    f"{result.get('total_pips',0):+.0f}", "", GOLD,  "📏"), unsafe_allow_html=True)
with c7: st.markdown(stat_card("Sharpe Ratio",  f"{result.get('sharpe_ratio',0):.3f}", "> 1 is good", PURPLE, "⚡"), unsafe_allow_html=True)
with c8: st.markdown(stat_card("Blocked",       f"{result['blocked_count']}", "filtered signals", MUTED, "🚫"), unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── Equity curve + P/L per trade ──────────────────────────────────────────────
eq = result.get("equity_curve", [])
trade_log = result.get("trade_log", [])

chart_left, chart_right = st.columns([2, 1])

with chart_left:
    st.markdown(section_title("Equity Curve"), unsafe_allow_html=True)
    if eq:
        fig_eq = go.Figure()
        fig_eq.add_trace(go.Scatter(
            y=eq, mode="lines", name="Portfolio",
            line=dict(color=GREEN if eq[-1] >= result["initial_balance"] else RED, width=2.5),
            fill="tozeroy",
            fillcolor=f"rgba({'0,212,160' if eq[-1]>=result['initial_balance'] else '255,69,96'},0.06)",
        ))
        fig_eq.add_hline(y=result["initial_balance"], line_dash="dash",
                         line_color="rgba(240,185,11,0.5)", line_width=1.5,
                         annotation_text="Initial balance",
                         annotation_font_color=GOLD, annotation_font_size=10)
        fig_eq.update_layout(height=300, **PLOTLY_THEME,
                             yaxis_title="Balance ($)", xaxis_title="Trade #")
        st.plotly_chart(fig_eq, use_container_width=True)

with chart_right:
    st.markdown(section_title("Win / Loss Breakdown"), unsafe_allow_html=True)
    if trade_log:
        pie = go.Figure(go.Pie(
            labels=["Wins", "Losses"],
            values=[result["winning_trades"], result["losing_trades"]],
            hole=0.55,
            marker_colors=[GREEN, RED],
            textfont=dict(size=11),
        ))
        pie.update_layout(
            height=300, **PLOTLY_THEME,
            annotations=[dict(text=f"<b>{result['win_rate']:.0f}%</b><br>win rate",
                              x=0.5, y=0.5, font=dict(size=13, color="#E2E8F0"), showarrow=False)],
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=-0.15, xanchor="center", x=0.5,
                        bgcolor="rgba(0,0,0,0)"),
            margin=dict(l=0, r=0, t=10, b=30),
        )
        st.plotly_chart(pie, use_container_width=True)

# ── P/L bar chart ──────────────────────────────────────────────────────────────
if trade_log:
    pnls  = [float(t.get("pnl", 0)) for t in trade_log]
    dirs  = [t.get("direction","") for t in trade_log]
    colors = [GREEN if p >= 0 else RED for p in pnls]

    st.markdown(section_title("P/L Per Trade"), unsafe_allow_html=True)
    fig_bar = go.Figure(go.Bar(
        y=pnls, marker_color=colors,
        hovertemplate="Trade %{x}<br>P/L: $%{y:,.2f}<extra></extra>",
    ))
    fig_bar.add_hline(y=0, line_color="rgba(100,116,139,0.5)", line_width=1)
    fig_bar.update_layout(height=220, **PLOTLY_THEME,
                          yaxis_title="P/L ($)", xaxis_title="Trade #")
    st.plotly_chart(fig_bar, use_container_width=True)

    # Trade log table
    st.markdown(section_title("Trade Log"), unsafe_allow_html=True)
    df_trades = pd.DataFrame(trade_log)
    cols_show = ["timestamp","direction","entry_price","exit_price","exit_reason","pips","pnl","lot_size"]
    avail = [c for c in cols_show if c in df_trades.columns]
    df_show = df_trades[avail].copy()
    if "pnl" in df_show.columns:
        df_show["pnl"] = df_show["pnl"].apply(lambda x: f"${float(x):+,.2f}")
    if "pips" in df_show.columns:
        df_show["pips"] = df_show["pips"].apply(lambda x: f"{float(x):+.1f}")
    st.dataframe(df_show, use_container_width=True, height=320)

st.markdown(disclaimer_box(), unsafe_allow_html=True)
