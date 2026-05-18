"""Shared helper functions used across modules."""
from __future__ import annotations

import math
from datetime import datetime, timezone, time as dtime
from typing import Optional


def safe_float(value, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def round_price(price: float, symbol: str) -> float:
    decimals = {"USDJPY": 3, "XAUUSD": 2}.get(symbol, 5)
    return round(price, decimals)


def pips_to_price(pips: float, symbol: str) -> float:
    from config import get_pip_size
    return pips * get_pip_size(symbol)


def price_to_pips(price_diff: float, symbol: str) -> float:
    from config import get_pip_size
    pip = get_pip_size(symbol)
    return abs(price_diff) / pip if pip else 0.0


def session_tag(dt: datetime) -> str:
    """Return trading session name based on UTC hour."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    h = dt.hour
    if 22 <= h or h < 8:
        return "sydney"
    if 0 <= h < 9:
        return "tokyo"
    if 7 <= h < 16:
        return "london"
    if 13 <= h < 22:
        return "new_york"
    return "overlap"


def timeframe_to_minutes(tf: str) -> int:
    mapping = {"M1": 1, "M5": 5, "M15": 15, "M30": 30, "H1": 60, "H4": 240, "D1": 1440}
    return mapping.get(tf.upper(), 15)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def bars_needed_for_training(lookback: int, future_bars: int) -> int:
    return lookback + future_bars + 250   # +250 for indicator warm-up
