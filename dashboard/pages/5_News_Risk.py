"""Page 5 — News Risk"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import streamlit as st
import plotly.graph_objects as go
import pandas as pd

from config import settings
from core.calendar_news import _load_csv_calendar, check_news_risk, create_sample_calendar
from utils.helpers import now_utc
from dashboard.theme import (
    GLOBAL_CSS, GOLD, GREEN, RED, BLUE, PURPLE, MUTED, PLOTLY_THEME,
    sidebar_logo, page_header, stat_card, section_title, disclaimer_box,
    render_sidebar_nav,
)

st.set_page_config(page_title="News Risk — AURUMFx", page_icon="📰", layout="wide")
st.markdown(GLOBAL_CSS, unsafe_allow_html=True)

with st.sidebar:
    render_sidebar_nav()
    symbol = st.selectbox("Symbol", settings.SYMBOLS, index=0)
    impact_filter = st.multiselect("Impact filter", ["high", "medium", "low"], default=["high", "medium"])

st.markdown(page_header("News & Economic Calendar", "High-impact event detection and sentiment analysis", "📰"), unsafe_allow_html=True)

create_sample_calendar(days_ahead=14)

@st.cache_data(ttl=300)
def load_events():
    return _load_csv_calendar()

col_reload, _ = st.columns([1, 4])
with col_reload:
    if st.button("Reload Calendar"):
        st.cache_data.clear()
        st.rerun()

events = load_events()
filtered = [e for e in events if e.impact in impact_filter] if events else []

now = now_utc()
check = check_news_risk(symbol, now, events)

# ── Status banner ──────────────────────────────────────────────────────────────
if check.blocked:
    st.markdown(f"""
<div style="
    background: rgba(255,69,96,0.1);
    border: 1px solid rgba(255,69,96,0.4);
    border-left: 4px solid {RED};
    border-radius: 12px;
    padding: 1rem 1.4rem;
    margin-bottom: 1rem;
    display: flex;
    align-items: center;
    gap: 1rem;
">
    <div style="font-size:1.8rem">🚨</div>
    <div>
        <div style="color:{RED};font-weight:700;font-size:0.95rem">Trading Blocked — High-Impact Event Active</div>
        <div style="color:#94a3b8;font-size:0.78rem;margin-top:0.2rem">{check.reason}</div>
    </div>
</div>
""", unsafe_allow_html=True)
elif check.nearby_events:
    count = len(check.nearby_events)
    st.markdown(f"""
<div style="
    background: rgba(240,185,11,0.08);
    border: 1px solid rgba(240,185,11,0.3);
    border-left: 4px solid {GOLD};
    border-radius: 12px;
    padding: 1rem 1.4rem;
    margin-bottom: 1rem;
    display: flex;
    align-items: center;
    gap: 1rem;
">
    <div style="font-size:1.8rem">⚠️</div>
    <div>
        <div style="color:{GOLD};font-weight:700;font-size:0.95rem">{count} Nearby Event(s) — Confidence Reduced</div>
        <div style="color:#94a3b8;font-size:0.78rem;margin-top:0.2rem">Signal confidence will be reduced by up to 20% during this window.</div>
    </div>
</div>
""", unsafe_allow_html=True)
else:
    st.markdown(f"""
<div style="
    background: rgba(0,212,160,0.08);
    border: 1px solid rgba(0,212,160,0.3);
    border-left: 4px solid {GREEN};
    border-radius: 12px;
    padding: 1rem 1.4rem;
    margin-bottom: 1rem;
    display: flex;
    align-items: center;
    gap: 1rem;
">
    <div style="font-size:1.8rem">✅</div>
    <div>
        <div style="color:{GREEN};font-weight:700;font-size:0.95rem">Clear — No High-Impact Events Near This Symbol</div>
        <div style="color:#94a3b8;font-size:0.78rem;margin-top:0.2rem">Signals are not being blocked by news at this time.</div>
    </div>
</div>
""", unsafe_allow_html=True)

# ── Stats ──────────────────────────────────────────────────────────────────────
high_count = sum(1 for e in filtered if e.impact == "high")
med_count  = sum(1 for e in filtered if e.impact == "medium")
avg_sent   = sum(e.sentiment for e in filtered) / len(filtered) if filtered else 0
sent_color = GREEN if avg_sent > 0.1 else RED if avg_sent < -0.1 else GOLD

c1, c2, c3, c4 = st.columns(4)
with c1: st.markdown(stat_card("Total Events", str(len(filtered)), "in calendar", BLUE, "📅"), unsafe_allow_html=True)
with c2: st.markdown(stat_card("High Impact",  str(high_count), "events", RED, "🔴"), unsafe_allow_html=True)
with c3: st.markdown(stat_card("Medium Impact", str(med_count), "events", GOLD, "🟡"), unsafe_allow_html=True)
with c4: st.markdown(stat_card("Avg Sentiment", f"{avg_sent:+.2f}", "-1 to +1 scale", sent_color, "📊"), unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── Calendar table ─────────────────────────────────────────────────────────────
st.markdown(section_title("Economic Calendar"), unsafe_allow_html=True)

IMPACT_COLOR = {"HIGH": RED, "MEDIUM": GOLD, "LOW": MUTED}
IMPACT_BG    = {"HIGH": "rgba(255,69,96,0.12)", "MEDIUM": "rgba(240,185,11,0.12)", "LOW": "rgba(100,116,139,0.08)"}

if filtered:
    sorted_events = sorted(filtered, key=lambda e: e.event_time)
    for ev in sorted_events[:40]:
        impact = ev.impact.upper()
        color  = IMPACT_COLOR.get(impact, MUTED)
        bg     = IMPACT_BG.get(impact, "")
        sent_c = GREEN if ev.sentiment > 0.1 else RED if ev.sentiment < -0.1 else MUTED
        st.markdown(f"""
<div style="
    background: {bg};
    border: 1px solid {color}33;
    border-radius: 10px;
    padding: 0.75rem 1rem;
    margin-bottom: 0.4rem;
    display: flex;
    align-items: center;
    gap: 1rem;
    flex-wrap: wrap;
">
    <div style="min-width:130px">
        <div style="font-size:0.65rem;color:#64748B;text-transform:uppercase;letter-spacing:0.06em">Time (UTC)</div>
        <div style="font-size:0.82rem;color:#E2E8F0;font-weight:600">{ev.event_time.strftime('%d %b %H:%M')}</div>
    </div>
    <div style="
        background:{color}22;border:1px solid {color}44;color:{color};
        border-radius:999px;padding:0.2rem 0.7rem;font-size:0.68rem;font-weight:700;
        min-width:70px;text-align:center;
    ">{impact}</div>
    <div style="
        background:#3B82F622;border:1px solid #3B82F644;color:#3B82F6;
        border-radius:999px;padding:0.2rem 0.7rem;font-size:0.68rem;font-weight:700;
    ">{ev.currency}</div>
    <div style="flex:1;min-width:200px">
        <div style="font-size:0.85rem;color:#E2E8F0;font-weight:600">{ev.title}</div>
        <div style="font-size:0.72rem;color:#64748B">{ev.country}</div>
    </div>
    <div style="display:flex;gap:1.5rem">
        <div>
            <div style="font-size:0.6rem;color:#64748B">Actual</div>
            <div style="font-size:0.8rem;color:#E2E8F0;font-weight:600">{ev.actual or '—'}</div>
        </div>
        <div>
            <div style="font-size:0.6rem;color:#64748B">Forecast</div>
            <div style="font-size:0.8rem;color:#E2E8F0">{ev.forecast or '—'}</div>
        </div>
        <div>
            <div style="font-size:0.6rem;color:#64748B">Sentiment</div>
            <div style="font-size:0.8rem;color:{sent_c};font-weight:600">{ev.sentiment:+.2f}</div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)
else:
    st.info("No events match the selected filters.")

# ── Sentiment timeline ─────────────────────────────────────────────────────────
if filtered:
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(section_title("Sentiment Timeline"), unsafe_allow_html=True)
    times = [ev.event_time for ev in filtered]
    sents = [ev.sentiment for ev in filtered]
    labels = [f"{ev.currency}: {ev.title[:25]}" for ev in filtered]
    colors = [GREEN if s >= 0 else RED for s in sents]

    fig_sent = go.Figure()
    fig_sent.add_trace(go.Bar(
        x=times, y=sents,
        marker_color=colors,
        text=[ev.currency for ev in filtered],
        textposition="outside",
        hovertext=labels,
        hovertemplate="%{hovertext}<br>Sentiment: %{y:+.2f}<extra></extra>",
    ))
    fig_sent.add_hline(y=0, line_color="rgba(100,116,139,0.5)", line_width=1)
    fig_sent.update_layout(
        height=280, **PLOTLY_THEME,
        yaxis_title="Sentiment Score",
        xaxis_title="Event Time",
    )
    st.plotly_chart(fig_sent, use_container_width=True)

# ── Upload custom calendar ─────────────────────────────────────────────────────
with st.expander("Import Custom Calendar CSV"):
    st.markdown("""
<div style="font-size:0.78rem;color:#64748B;margin-bottom:0.8rem">
    Required columns: <code>event_time, currency, country, title, impact, actual, forecast, previous, sentiment</code>
</div>
""", unsafe_allow_html=True)
    uploaded = st.file_uploader("Upload CSV", type=["csv"])
    if uploaded:
        try:
            df_up = pd.read_csv(uploaded)
            out_path = settings.NEWS_DIR / "economic_calendar.csv"
            df_up.to_csv(out_path, index=False)
            st.success(f"Saved {len(df_up)} events.")
            st.cache_data.clear()
        except Exception as exc:
            st.error(f"Import failed: {exc}")

st.markdown(disclaimer_box(), unsafe_allow_html=True)
