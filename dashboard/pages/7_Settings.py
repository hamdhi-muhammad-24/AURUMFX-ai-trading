"""Page 7 — Settings"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import streamlit as st
from config import settings
from core.risk_manager import get_tracker
from dashboard.theme import (
    GLOBAL_CSS, GOLD, GREEN, RED, BLUE, PURPLE, MUTED,
    sidebar_logo, page_header, stat_card, section_title, disclaimer_box,
    render_sidebar_nav,
)

st.set_page_config(page_title="Settings — AURUMFx", page_icon="⚙️", layout="wide")
st.markdown(GLOBAL_CSS, unsafe_allow_html=True)

with st.sidebar:
    render_sidebar_nav()

st.markdown(page_header("Settings", "Configure risk, ML, data source, and safety controls", "⚙️"), unsafe_allow_html=True)

st.markdown(f"""
<div style="
    background: rgba(240,185,11,0.08);
    border: 1px solid rgba(240,185,11,0.25);
    border-left: 4px solid {GOLD};
    border-radius: 10px;
    padding: 0.8rem 1.1rem;
    margin-bottom: 1rem;
    font-size: 0.78rem;
    color: #94a3b8;
">
    Changes here affect the current session only. To persist settings, edit <code>.env</code> or <code>config.py</code>.
</div>
""", unsafe_allow_html=True)

tabs = st.tabs(["Risk Management", "ML & Signals", "Data Source", "Safety Controls", "System Info"])

# ─────────────────────────────────────────────────────────────────────────────
# Tab 1 — Risk Management
# ─────────────────────────────────────────────────────────────────────────────
with tabs[0]:
    st.markdown(section_title("Risk Parameters"), unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        risk_pct     = st.slider("Risk per trade (%)",    0.1,  5.0,  float(settings.RISK_PER_TRADE_PCT), 0.1,
                                  help="Percentage of balance risked per trade")
        max_dl       = st.slider("Max daily loss (%)",    1.0,  15.0, float(settings.MAX_DAILY_LOSS_PCT),  0.5,
                                  help="Stops all trading once daily loss hits this level")
        max_open     = st.number_input("Max open trades",     1, 10, int(settings.MAX_OPEN_TRADES))
        max_per_day  = st.number_input("Max trades per day",  1, 20, int(settings.MAX_TRADES_PER_DAY))
    with col2:
        min_rr       = st.slider("Minimum RR ratio",      1.0, 5.0,  float(settings.MIN_RISK_REWARD), 0.1,
                                  help="Minimum Risk:Reward required to open a trade")
        sl_mult      = st.slider("SL = N x ATR",          0.5, 5.0,  float(settings.SL_ATR_MULT),    0.1)
        tp_mult      = st.slider("TP = N x ATR",          0.5, 8.0,  float(settings.TP_ATR_MULT),    0.1)
        balance      = st.number_input("Account balance ($)", 100.0, 1_000_000.0, float(settings.DEFAULT_BALANCE), 500.0)

    if st.button("Save Risk Settings", use_container_width=True):
        settings.RISK_PER_TRADE_PCT  = risk_pct
        settings.MAX_DAILY_LOSS_PCT  = max_dl
        settings.MAX_OPEN_TRADES     = max_open
        settings.MAX_TRADES_PER_DAY  = max_per_day
        settings.MIN_RISK_REWARD     = min_rr
        settings.SL_ATR_MULT         = sl_mult
        settings.TP_ATR_MULT         = tp_mult
        settings.DEFAULT_BALANCE     = balance
        st.success("Risk settings updated for this session.")

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(section_title("Live Risk State"), unsafe_allow_html=True)

    state_cols = st.columns(len(settings.MVP_SYMBOLS))
    for i, sym in enumerate(settings.MVP_SYMBOLS):
        tracker = get_tracker(sym, settings.DEFAULT_BALANCE)
        tracker.reset_daily()
        state = tracker.to_dict()
        daily_loss_pct = state["daily_loss_pct"]
        loss_color = RED if daily_loss_pct >= settings.MAX_DAILY_LOSS_PCT * 0.8 else GOLD if daily_loss_pct >= settings.MAX_DAILY_LOSS_PCT * 0.5 else GREEN
        with state_cols[i]:
            st.markdown(f"""
<div style="background:#0D1421;border:1px solid #1E2D4A;border-radius:12px;padding:1rem;text-align:center">
    <div style="font-size:0.7rem;color:#64748B;font-weight:700;text-transform:uppercase;letter-spacing:0.08em;margin-bottom:0.5rem">{sym}</div>
    <div style="font-size:0.78rem;color:#94a3b8;margin:0.2rem 0">Trades today: <strong style="color:#E2E8F0">{state['trades_today']}</strong></div>
    <div style="font-size:0.78rem;color:#94a3b8;margin:0.2rem 0">Daily P/L: <strong style="color:{GREEN if state['daily_pnl']>=0 else RED}">${state['daily_pnl']:+.2f}</strong></div>
    <div style="font-size:0.78rem;color:#94a3b8;margin:0.2rem 0">Loss: <strong style="color:{loss_color}">{daily_loss_pct:.1f}%</strong></div>
</div>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# Tab 2 — ML & Signals
# ─────────────────────────────────────────────────────────────────────────────
with tabs[1]:
    st.markdown(section_title("Signal Filter Settings"), unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        min_conf    = st.slider("Min confidence for signal", 0.50, 0.95, float(settings.MIN_CONFIDENCE),    0.01,
                                 help="Signals below this confidence become NO_TRADE")
        future_bars = st.number_input("Future bars for labeling", 3, 50, int(settings.FUTURE_BARS),
                                      help="How many bars ahead to compute the label return")
        atr_mult    = st.slider("ATR mult for label threshold", 0.1, 2.0, float(settings.LABEL_THRESHOLD_ATR_MULT), 0.05)
    with col2:
        max_spread  = st.slider("Max spread (pips)",     0.5, 20.0, float(settings.MAX_SPREAD_PIPS), 0.5)
        min_atr     = st.slider("Min ATR (pips)",        0.5, 20.0, float(settings.MIN_ATR_PIPS),    0.5)
        train_ratio = st.slider("Train split ratio",     0.5, 0.9,  float(settings.TRAIN_TEST_RATIO),  0.05)

    if st.button("Save ML Settings", use_container_width=True):
        settings.MIN_CONFIDENCE            = min_conf
        settings.FUTURE_BARS               = future_bars
        settings.LABEL_THRESHOLD_ATR_MULT  = atr_mult
        settings.MAX_SPREAD_PIPS           = max_spread
        settings.MIN_ATR_PIPS              = min_atr
        settings.TRAIN_TEST_RATIO          = train_ratio
        st.success("ML settings updated.")

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(section_title("Retrain Models"), unsafe_allow_html=True)

    r1, r2, _ = st.columns([2, 2, 3])
    with r1: retrain_sym = st.selectbox("Symbol", settings.MVP_SYMBOLS, key="rsym")
    with r2: retrain_tf  = st.selectbox("Timeframe", settings.SUPPORTED_TIMEFRAMES, key="rtf")

    if st.button("Retrain Now", use_container_width=True):
        with st.spinner(f"Retraining {retrain_sym} {retrain_tf}..."):
            try:
                from core.data_loader import get_candles
                from core.feature_engineering import build_features
                from core.ml_predictor import train_models
                df = get_candles(retrain_sym, retrain_tf, n_bars=settings.TRAIN_LOOKBACK)
                df = build_features(df, retrain_sym)
                res = train_models(df, retrain_sym, retrain_tf)
                models_trained = ", ".join(res.get("models_saved", []))
                st.success(f"Models retrained: {models_trained}")
            except Exception as exc:
                st.error(f"Retrain error: {exc}")


# ─────────────────────────────────────────────────────────────────────────────
# Tab 3 — Data Source
# ─────────────────────────────────────────────────────────────────────────────
with tabs[2]:
    st.markdown(section_title("Data Source"), unsafe_allow_html=True)

    mt5_col, csv_col = st.columns(2)
    with mt5_col:
        st.markdown(f"""
<div style="background:#0D1421;border:1px solid #1E2D4A;border-radius:12px;padding:1.2rem;margin-bottom:0.8rem">
    <div style="font-size:0.85rem;font-weight:700;color:#E2E8F0;margin-bottom:0.8rem">MetaTrader 5</div>
""", unsafe_allow_html=True)
        mt5_enabled = st.checkbox("Enable MT5 connection", value=bool(settings.MT5_ENABLED))
        if mt5_enabled:
            mt5_login  = st.number_input("Login",    value=int(settings.MT5_LOGIN))
            mt5_server = st.text_input( "Server",    value=settings.MT5_SERVER)
            mt5_pass   = st.text_input( "Password",  type="password")
            mt5_path   = st.text_input( "Terminal path (optional)", value=settings.MT5_PATH)
            if st.button("Apply MT5 Settings"):
                settings.MT5_ENABLED  = True
                settings.MT5_LOGIN    = mt5_login
                settings.MT5_PASSWORD = mt5_pass
                settings.MT5_SERVER   = mt5_server
                settings.MT5_PATH     = mt5_path
                st.success("MT5 settings saved.")
        st.markdown("</div>", unsafe_allow_html=True)

    with csv_col:
        st.markdown(f"""
<div style="background:#0D1421;border:1px solid {GREEN}33;border-radius:12px;padding:1.2rem">
    <div style="font-size:0.85rem;font-weight:700;color:{GREEN};margin-bottom:0.5rem">CSV Fallback Mode (Active)</div>
    <div style="font-size:0.78rem;color:#64748B;line-height:1.6">
        Sample CSV files are in <code>data/sample/</code>.<br>
        Available: EURUSD, XAUUSD, GBPUSD, USDJPY<br>
        Timeframes: M5, M15, H1, H4<br><br>
        Run <code>python run.py --generate-data</code> to regenerate.
    </div>
</div>
""", unsafe_allow_html=True)

        if st.button("Regenerate Sample Data"):
            with st.spinner("Generating..."):
                try:
                    from scripts.generate_sample_data import main as gen
                    gen()
                    st.success("Sample data regenerated.")
                except Exception as exc:
                    st.error(f"Error: {exc}")

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(section_title("Indicator Parameters (read-only)"), unsafe_allow_html=True)
    st.markdown(f"""
<div style="background:#0D1421;border:1px solid #1E2D4A;border-radius:12px;padding:1.2rem">
    <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:1rem">
        <div><span style="color:#64748B;font-size:0.72rem">EMA Fast</span><div style="color:#E2E8F0;font-weight:700">{settings.EMA_FAST}</div></div>
        <div><span style="color:#64748B;font-size:0.72rem">EMA Mid</span><div style="color:#E2E8F0;font-weight:700">{settings.EMA_MID}</div></div>
        <div><span style="color:#64748B;font-size:0.72rem">EMA Slow</span><div style="color:#E2E8F0;font-weight:700">{settings.EMA_SLOW}</div></div>
        <div><span style="color:#64748B;font-size:0.72rem">RSI Period</span><div style="color:#E2E8F0;font-weight:700">{settings.RSI_PERIOD}</div></div>
        <div><span style="color:#64748B;font-size:0.72rem">ATR Period</span><div style="color:#E2E8F0;font-weight:700">{settings.ATR_PERIOD}</div></div>
        <div><span style="color:#64748B;font-size:0.72rem">BB Period</span><div style="color:#E2E8F0;font-weight:700">{settings.BB_PERIOD}</div></div>
        <div><span style="color:#64748B;font-size:0.72rem">MACD Fast</span><div style="color:#E2E8F0;font-weight:700">{settings.MACD_FAST}</div></div>
        <div><span style="color:#64748B;font-size:0.72rem">MACD Slow</span><div style="color:#E2E8F0;font-weight:700">{settings.MACD_SLOW}</div></div>
        <div><span style="color:#64748B;font-size:0.72rem">MACD Signal</span><div style="color:#E2E8F0;font-weight:700">{settings.MACD_SIGNAL}</div></div>
    </div>
    <div style="font-size:0.7rem;color:#475569;margin-top:0.8rem">Edit <code>config.py</code> to change indicator periods.</div>
</div>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# Tab 4 — Safety Controls
# ─────────────────────────────────────────────────────────────────────────────
with tabs[3]:
    # Kill switch
    st.markdown(section_title("Kill Switch"), unsafe_allow_html=True)
    kill_col, _ = st.columns([2, 3])
    with kill_col:
        kill_active = st.checkbox(
            "KILL SWITCH — Halt all signal generation",
            value=bool(settings.KILL_SWITCH),
            help="When active, every signal cycle returns NO_TRADE immediately"
        )
        if kill_active != settings.KILL_SWITCH:
            settings.KILL_SWITCH = kill_active

    kill_color = RED if kill_active else GREEN
    st.markdown(f"""
<div style="background:{kill_color}0F;border:1px solid {kill_color}33;border-radius:10px;padding:0.8rem 1rem;margin-bottom:1rem">
    <strong style="color:{kill_color}">Kill Switch: {'ACTIVE — Trading Halted' if kill_active else 'OFF — System Running'}</strong>
</div>
""", unsafe_allow_html=True)

    st.markdown(f"""
<div style="background:{RED}0A;border:1px solid {RED}33;border-radius:12px;padding:1.2rem;margin-bottom:1rem">
    <div style="color:{RED};font-weight:800;font-size:0.95rem;margin-bottom:0.4rem">AUTO-TRADING IS PERMANENTLY DISABLED</div>
    <div style="color:#64748B;font-size:0.78rem">This system operates in signal prediction + paper trading mode only. Demo auto-trading requires explicit activation in config.py and is disabled by design.</div>
</div>
""", unsafe_allow_html=True)

    # News blocking
    st.markdown(section_title("News Blocking Window"), unsafe_allow_html=True)
    nb1, nb2 = st.columns(2)
    with nb1: block_before = st.number_input("Block minutes BEFORE event", 0, 120, settings.NEWS_BLOCK_MINUTES_BEFORE)
    with nb2: block_after  = st.number_input("Block minutes AFTER event",  0,  60, settings.NEWS_BLOCK_MINUTES_AFTER)

    if st.button("Save News Settings"):
        settings.NEWS_BLOCK_MINUTES_BEFORE = block_before
        settings.NEWS_BLOCK_MINUTES_AFTER  = block_after
        st.success("News blocking settings updated.")


# ─────────────────────────────────────────────────────────────────────────────
# Tab 5 — System Info
# ─────────────────────────────────────────────────────────────────────────────
with tabs[4]:
    st.markdown(section_title("System Information"), unsafe_allow_html=True)

    info_left, info_right = st.columns(2)
    with info_left:
        st.markdown(f"""
<div style="background:#0D1421;border:1px solid #1E2D4A;border-radius:12px;padding:1.2rem">
    <div style="font-size:0.82rem;font-weight:700;color:#E2E8F0;margin-bottom:0.8rem">Application</div>
    <table style="width:100%;font-size:0.78rem;border-collapse:collapse">
        <tr><td style="color:#64748B;padding:0.3rem 0">Name</td><td style="color:#E2E8F0;font-weight:600">{settings.APP_NAME}</td></tr>
        <tr><td style="color:#64748B;padding:0.3rem 0">Version</td><td style="color:#E2E8F0;font-weight:600">{settings.VERSION}</td></tr>
        <tr><td style="color:#64748B;padding:0.3rem 0">Environment</td><td style="color:{GOLD};font-weight:600">{settings.ENV.upper()}</td></tr>
        <tr><td style="color:#64748B;padding:0.3rem 0">Database</td><td style="color:#E2E8F0;font-weight:600">{settings.DATABASE_URL[:40]}...</td></tr>
        <tr><td style="color:#64748B;padding:0.3rem 0">MT5 Enabled</td><td style="color:{GREEN if settings.MT5_ENABLED else RED};font-weight:600">{'YES' if settings.MT5_ENABLED else 'NO (CSV mode)'}</td></tr>
        <tr><td style="color:#64748B;padding:0.3rem 0">Paper Trading</td><td style="color:{GREEN if settings.PAPER_ENABLED else RED};font-weight:600">{'ENABLED' if settings.PAPER_ENABLED else 'DISABLED'}</td></tr>
        <tr><td style="color:#64748B;padding:0.3rem 0">Demo Trading</td><td style="color:{RED};font-weight:700">DISABLED</td></tr>
        <tr><td style="color:#64748B;padding:0.3rem 0">Kill Switch</td><td style="color:{RED if settings.KILL_SWITCH else GREEN};font-weight:700">{'ACTIVE' if settings.KILL_SWITCH else 'OFF'}</td></tr>
    </table>
</div>
""", unsafe_allow_html=True)

    with info_right:
        import sys as _sys, platform
        st.markdown(f"""
<div style="background:#0D1421;border:1px solid #1E2D4A;border-radius:12px;padding:1.2rem">
    <div style="font-size:0.82rem;font-weight:700;color:#E2E8F0;margin-bottom:0.8rem">Environment</div>
    <table style="width:100%;font-size:0.78rem;border-collapse:collapse">
        <tr><td style="color:#64748B;padding:0.3rem 0">Python</td><td style="color:#E2E8F0;font-weight:600">{_sys.version.split()[0]}</td></tr>
        <tr><td style="color:#64748B;padding:0.3rem 0">Platform</td><td style="color:#E2E8F0;font-weight:600">{platform.system()} {platform.release()}</td></tr>
        <tr><td style="color:#64748B;padding:0.3rem 0">Data Dir</td><td style="color:#E2E8F0;font-weight:600">{str(settings.DATA_DIR)[-35:]}</td></tr>
        <tr><td style="color:#64748B;padding:0.3rem 0">Models Dir</td><td style="color:#E2E8F0;font-weight:600">{str(settings.MODELS_DIR)[-35:]}</td></tr>
        <tr><td style="color:#64748B;padding:0.3rem 0">MVP Symbols</td><td style="color:{GOLD};font-weight:600">{', '.join(settings.MVP_SYMBOLS)}</td></tr>
    </table>
</div>
""", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Initialize Database"):
            try:
                from database.db import init_db
                init_db()
                st.success("Database tables initialised.")
            except Exception as exc:
                st.error(f"Database init failed: {exc}")

st.markdown(disclaimer_box(), unsafe_allow_html=True)
