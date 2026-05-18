"""Page 3 — Paper Trading"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import streamlit as st
import plotly.graph_objects as go
import pandas as pd

from config import settings
from core.paper_trader import get_paper_trader
from dashboard.theme import (
    GLOBAL_CSS, GOLD, GREEN, RED, BLUE, PURPLE, MUTED, PLOTLY_THEME,
    sidebar_logo, page_header, stat_card, section_title, disclaimer_box,
    render_sidebar_nav,
)

st.set_page_config(page_title="Paper Trading — AURUMFx", page_icon="📝", layout="wide")
st.markdown(GLOBAL_CSS, unsafe_allow_html=True)

with st.sidebar:
    render_sidebar_nav()
    symbol = st.selectbox("Symbol", settings.SYMBOLS, index=0)

st.markdown(page_header("Paper Trading", "Virtual trading — no real money at risk", "📝"), unsafe_allow_html=True)

if not settings.PAPER_ENABLED:
    st.warning("Paper trading is disabled. Enable it in Settings.")
    st.stop()

trader = get_paper_trader(symbol)
last_price = trader.equity_curve[-1] if trader.equity_curve else settings.PAPER_BALANCE
account = trader.get_account(last_price)

# ── Account summary cards ─────────────────────────────────────────────────────
net_pnl = account.closed_pnl
net_color = GREEN if net_pnl >= 0 else RED
pnl_icon = "📈" if net_pnl >= 0 else "📉"

c1, c2, c3, c4, c5, c6 = st.columns(6)
with c1: st.markdown(stat_card("Balance", f"${account.balance:,.2f}", "virtual", GOLD, "💰"), unsafe_allow_html=True)
with c2: st.markdown(stat_card("Equity",  f"${account.equity:,.2f}",  "incl. open", BLUE, "📊"), unsafe_allow_html=True)
with c3: st.markdown(stat_card("Open P/L",f"${account.open_pnl:+,.2f}", "unrealised", GREEN if account.open_pnl>=0 else RED, "⏳"), unsafe_allow_html=True)
with c4: st.markdown(stat_card("Net P/L",  f"${net_pnl:+,.2f}", "realised", net_color, pnl_icon), unsafe_allow_html=True)
with c5: st.markdown(stat_card("Win Rate", f"{account.win_rate:.1f}%", f"{account.win_count}W / {account.loss_count}L", GREEN if account.win_rate>=50 else RED, "🏆"), unsafe_allow_html=True)
with c6: st.markdown(stat_card("Trades",   str(account.trades_closed), "closed", PURPLE, "📋"), unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── Equity curve ──────────────────────────────────────────────────────────────
left, right = st.columns([2, 1])

with left:
    st.markdown(section_title("Equity Curve"), unsafe_allow_html=True)
    eq = trader.equity_curve
    if len(eq) > 1:
        fig_eq = go.Figure()
        # Fill area
        fig_eq.add_trace(go.Scatter(
            y=eq, mode="lines", name="Equity",
            line=dict(color=GREEN, width=2.5),
            fill="tozeroy",
            fillcolor="rgba(0,212,160,0.06)",
            hovertemplate="Equity: $%{y:,.2f}<extra></extra>",
        ))
        fig_eq.add_hline(
            y=trader.initial_balance, line_dash="dash",
            line_color="rgba(240,185,11,0.5)", line_width=1.5,
            annotation_text="Initial balance",
            annotation_font_color=GOLD, annotation_font_size=10,
        )
        fig_eq.update_layout(
            height=300, **PLOTLY_THEME,
            yaxis_title="Balance ($)",
            xaxis_title="Trade #",
        )
        st.plotly_chart(fig_eq, use_container_width=True)
    else:
        st.markdown("""
<div style="background:#0D1421;border:1px solid #1E2D4A;border-radius:12px;padding:2rem;text-align:center;height:220px;display:flex;align-items:center;justify-content:center">
    <div>
        <div style="font-size:2rem;margin-bottom:0.5rem">📈</div>
        <div style="color:#64748B;font-size:0.85rem">Equity curve appears here after your first trade closes</div>
    </div>
</div>
""", unsafe_allow_html=True)

# ── Open positions ─────────────────────────────────────────────────────────────
with right:
    st.markdown(section_title(f"Open Positions ({len(trader.open_positions)})"), unsafe_allow_html=True)

    if trader.open_positions:
        for pos in trader.open_positions.values():
            color = GREEN if pos.direction == "BUY" else RED
            arrow = "▲" if pos.direction == "BUY" else "▼"
            st.markdown(f"""
<div style="
    background: linear-gradient(135deg, #0D1421 0%, #111827 100%);
    border: 1px solid {color}33;
    border-left: 3px solid {color};
    border-radius: 12px;
    padding: 1rem;
    margin-bottom: 0.6rem;
">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.5rem">
        <span style="color:{color};font-weight:700;font-size:0.85rem">{arrow} #{pos.id} {pos.direction}</span>
        <span style="color:#64748B;font-size:0.72rem">{pos.lot_size} lot</span>
    </div>
    <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:0.4rem">
        <div>
            <div style="font-size:0.62rem;color:#64748B">Entry</div>
            <div style="font-size:0.82rem;color:#E2E8F0;font-weight:600">{pos.entry_price:.5f}</div>
        </div>
        <div>
            <div style="font-size:0.62rem;color:#64748B">SL</div>
            <div style="font-size:0.82rem;color:{RED};font-weight:600">{pos.sl_price:.5f}</div>
        </div>
        <div>
            <div style="font-size:0.62rem;color:#64748B">TP</div>
            <div style="font-size:0.82rem;color:{GREEN};font-weight:600">{pos.tp_price:.5f}</div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)
    else:
        st.markdown("""
<div style="background:#0D1421;border:1px solid #1E2D4A;border-radius:12px;padding:1.5rem;text-align:center">
    <div style="color:#64748B;font-size:0.82rem">No open positions</div>
</div>
""", unsafe_allow_html=True)

    with st.expander("Close All Positions"):
        close_px = st.number_input("Close price", value=0.0, format="%.5f", key="close_px")
        if st.button("Close All Now", type="primary"):
            if close_px > 0:
                trader.close_all(close_px)
                st.success("All positions closed")
                st.rerun()

# ── Closed trades table ───────────────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
st.markdown(section_title("Closed Trades"), unsafe_allow_html=True)

if trader.closed_positions:
    rows = [p.to_dict() for p in reversed(trader.closed_positions)]
    df_closed = pd.DataFrame(rows)
    display_cols = ["id","direction","entry_price","exit_price","exit_reason","pips","pnl","lot_size","opened_at","closed_at"]
    avail = [c for c in display_cols if c in df_closed.columns]
    df_show = df_closed[avail].copy()
    if "pnl" in df_show.columns:
        df_show["pnl"] = df_show["pnl"].apply(lambda x: f"${float(x):+,.2f}")
    if "pips" in df_show.columns:
        df_show["pips"] = df_show["pips"].apply(lambda x: f"{float(x):+.1f}")
    st.dataframe(df_show, use_container_width=True, height=350)

    # P/L per trade bar chart
    if len(trader.closed_positions) > 1:
        pnls = [p.pnl for p in trader.closed_positions]
        bar_colors = [GREEN if v >= 0 else RED for v in pnls]
        fig_pnl = go.Figure(go.Bar(
            y=pnls,
            marker_color=bar_colors,
            hovertemplate="Trade: %{x}<br>P/L: $%{y:,.2f}<extra></extra>",
        ))
        fig_pnl.update_layout(
            height=200, **PLOTLY_THEME,
            yaxis_title="P/L ($)",
            xaxis_title="Trade #",
            title=dict(text="P/L Per Trade", font=dict(size=12, color="#94a3b8")),
        )
        fig_pnl.add_hline(y=0, line_color="rgba(100,116,139,0.5)", line_width=1)
        st.plotly_chart(fig_pnl, use_container_width=True)

    exp_col, _ = st.columns([1, 3])
    with exp_col:
        if st.button("Export Journal CSV", use_container_width=True):
            path = trader.export_journal()
            st.success(f"Exported: {path.name}")
else:
    st.markdown("""
<div style="background:#0D1421;border:1px solid #1E2D4A;border-radius:12px;padding:2rem;text-align:center">
    <div style="font-size:1.8rem;margin-bottom:0.5rem">📝</div>
    <div style="color:#E2E8F0;font-weight:600;margin-bottom:0.3rem">No closed trades yet</div>
    <div style="color:#64748B;font-size:0.78rem">Run AI Assistant to generate signals and open paper trades</div>
</div>
""", unsafe_allow_html=True)

st.markdown(disclaimer_box(), unsafe_allow_html=True)
