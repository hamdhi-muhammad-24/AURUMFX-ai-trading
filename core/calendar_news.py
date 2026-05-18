"""
Module 7 — Economic Calendar & News Sentiment
Loads/fetches news events. Blocks trades near high-impact events.
Scores news sentiment: -1 (negative) / 0 (neutral) / +1 (positive).
News cannot create trades alone — it can only block or reduce confidence.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Optional, Dict

import pandas as pd

from config import settings
from utils.logger import get_logger
from utils.helpers import now_utc

log = get_logger("calendar_news")

IMPACT_WEIGHTS = {"high": 1.0, "medium": 0.5, "low": 0.1}
CURRENCY_TO_SYMBOL: Dict[str, List[str]] = {
    "USD": ["EURUSD", "GBPUSD", "USDJPY", "XAUUSD", "USDCHF", "AUDUSD", "USDCAD", "NZDUSD"],
    "EUR": ["EURUSD"],
    "GBP": ["GBPUSD"],
    "JPY": ["USDJPY"],
    "AUD": ["AUDUSD"],
    "CAD": ["USDCAD"],
    "CHF": ["USDCHF"],
    "NZD": ["NZDUSD"],
    "XAU": ["XAUUSD"],
}


# ─────────────────────────────────────────────────────────────────────────────
# Data class
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class NewsEvent:
    event_time: datetime
    currency: str
    country: str
    title: str
    impact: str           # low | medium | high
    actual: str = ""
    forecast: str = ""
    previous: str = ""
    sentiment: float = 0.0  # -1 negative, 0 neutral, +1 positive

    def to_dict(self) -> dict:
        d = asdict(self)
        d["event_time"] = self.event_time.isoformat()
        return d


@dataclass
class NewsCheckResult:
    blocked: bool = False
    reason: str = ""
    nearby_events: List[dict] = None
    sentiment_score: float = 0.0
    confidence_modifier: float = 0.0   # negative = reduce confidence

    def to_dict(self) -> dict:
        return asdict(self)


# ─────────────────────────────────────────────────────────────────────────────
# Sample / CSV calendar loader
# ─────────────────────────────────────────────────────────────────────────────

def _sample_calendar_path() -> Path:
    return settings.NEWS_DIR / "economic_calendar.csv"


def _load_csv_calendar() -> List[NewsEvent]:
    path = _sample_calendar_path()
    if not path.exists():
        log.info("No calendar CSV found at {} — using empty calendar", path)
        return []
    try:
        df = pd.read_csv(path, parse_dates=["event_time"])
        events: List[NewsEvent] = []
        for _, row in df.iterrows():
            try:
                et = row["event_time"]
                if et.tzinfo is None:
                    et = et.replace(tzinfo=timezone.utc)
                events.append(NewsEvent(
                    event_time=et,
                    currency=str(row.get("currency", "")).upper(),
                    country=str(row.get("country", "")),
                    title=str(row.get("title", "")),
                    impact=str(row.get("impact", "low")).lower(),
                    actual=str(row.get("actual", "")),
                    forecast=str(row.get("forecast", "")),
                    previous=str(row.get("previous", "")),
                    sentiment=float(row.get("sentiment", 0.0)),
                ))
            except Exception as exc:
                log.debug("Skipping bad calendar row: {}", exc)
        log.info("Loaded {} calendar events", len(events))
        return events
    except Exception as exc:
        log.error("Calendar CSV load error: {}", exc)
        return []


# ─────────────────────────────────────────────────────────────────────────────
# Sentiment scorer (basic keyword-based; replace with NLP API if available)
# ─────────────────────────────────────────────────────────────────────────────

POSITIVE_WORDS = {
    "beat", "better", "stronger", "surge", "rise", "gain", "growth",
    "expansion", "positive", "above", "exceeded", "hawkish", "hike",
}
NEGATIVE_WORDS = {
    "miss", "weak", "worse", "fall", "decline", "drop", "contraction",
    "below", "negative", "dovish", "cut", "recession", "disappoint",
}


def score_sentiment(text: str) -> float:
    if not text:
        return 0.0
    words = set(text.lower().split())
    pos = len(words & POSITIVE_WORDS)
    neg = len(words & NEGATIVE_WORDS)
    if pos > neg:
        return min(1.0, pos * 0.3)
    if neg > pos:
        return max(-1.0, -neg * 0.3)
    return 0.0


# ─────────────────────────────────────────────────────────────────────────────
# Core check
# ─────────────────────────────────────────────────────────────────────────────

def check_news_risk(
    symbol: str,
    check_time: Optional[datetime] = None,
    events: Optional[List[NewsEvent]] = None,
    block_before_minutes: int = None,
    block_after_minutes: int = None,
) -> NewsCheckResult:
    """
    Returns NewsCheckResult.
    Blocks trade if a high-impact event for this symbol's currencies
    is within the blackout window.
    """
    check_time = check_time or now_utc()
    if check_time.tzinfo is None:
        check_time = check_time.replace(tzinfo=timezone.utc)

    block_before = timedelta(minutes=block_before_minutes or settings.NEWS_BLOCK_MINUTES_BEFORE)
    block_after = timedelta(minutes=block_after_minutes or settings.NEWS_BLOCK_MINUTES_AFTER)

    if events is None:
        events = _load_csv_calendar()

    # Which currencies affect this symbol?
    affected = {c for c, syms in CURRENCY_TO_SYMBOL.items() if symbol in syms}

    nearby = []
    sentiment_scores = []
    blocked = False
    block_reason = ""

    for ev in events:
        if ev.currency not in affected:
            continue
        window_start = ev.event_time - block_before
        window_end = ev.event_time + block_after
        is_nearby = window_start <= check_time <= window_end
        is_high_impact = ev.impact == "high"

        if is_nearby:
            nearby.append(ev.to_dict())
            sentiment_scores.append(ev.sentiment)
            if is_high_impact and not blocked:
                blocked = True
                block_reason = f"high_impact_{ev.currency}_{ev.title[:30]}"

    overall_sentiment = sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0.0
    conf_mod = 0.0
    if nearby:
        # Reduce confidence by up to 20% for nearby medium/high events
        high_count = sum(1 for e in nearby if e["impact"] == "high")
        med_count = sum(1 for e in nearby if e["impact"] == "medium")
        conf_mod = -(high_count * 0.15 + med_count * 0.05)

    return NewsCheckResult(
        blocked=blocked,
        reason=block_reason,
        nearby_events=nearby,
        sentiment_score=round(overall_sentiment, 3),
        confidence_modifier=round(conf_mod, 3),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Generate sample calendar CSV
# ─────────────────────────────────────────────────────────────────────────────

def create_sample_calendar(days_ahead: int = 7):
    """Write a sample economic_calendar.csv to data/news/."""
    from datetime import date
    import random

    path = _sample_calendar_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    if path.exists():
        return

    base = datetime.now(timezone.utc).replace(hour=14, minute=0, second=0, microsecond=0)
    rows = []
    events_template = [
        ("USD", "United States", "Non-Farm Payrolls", "high"),
        ("USD", "United States", "CPI m/m", "high"),
        ("USD", "United States", "Fed Interest Rate Decision", "high"),
        ("EUR", "European Union", "ECB Rate Decision", "high"),
        ("GBP", "United Kingdom", "Bank of England Rate Decision", "high"),
        ("USD", "United States", "ISM Manufacturing PMI", "medium"),
        ("EUR", "European Union", "German CPI", "medium"),
        ("USD", "United States", "Initial Jobless Claims", "medium"),
        ("GBP", "United Kingdom", "CPI y/y", "medium"),
        ("AUD", "Australia", "RBA Rate Decision", "high"),
    ]

    for d in range(days_ahead):
        dt = base + timedelta(days=d)
        for currency, country, title, impact in random.sample(events_template, k=3):
            sentiment = round(random.uniform(-0.5, 0.5), 2)
            rows.append({
                "event_time": (dt + timedelta(hours=random.randint(-2, 2))).strftime("%Y-%m-%d %H:%M:%S"),
                "currency": currency,
                "country": country,
                "title": title,
                "impact": impact,
                "actual": "",
                "forecast": "",
                "previous": "",
                "sentiment": sentiment,
            })

    pd.DataFrame(rows).to_csv(path, index=False)
    log.info("Sample calendar created at {}", path)
