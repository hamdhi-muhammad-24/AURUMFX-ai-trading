"""
Module 3 — Market Structure Analysis
Detects swing highs/lows, HH/HL/LH/LL patterns, BOS, support/resistance zones,
trend regime, and volatility regime.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import List, Optional

import numpy as np
import pandas as pd

from utils.logger import get_logger

log = get_logger("market_structure")

SWING_LOOKBACK = 5   # bars each side for swing detection


# ─────────────────────────────────────────────────────────────────────────────
# Data classes
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class SwingPoint:
    index: int
    timestamp: pd.Timestamp
    price: float
    kind: str          # "high" | "low"


@dataclass
class Zone:
    top: float
    bottom: float
    kind: str          # "support" | "resistance"
    touches: int = 1
    broken: bool = False


@dataclass
class MarketStructure:
    trend: str = "neutral"           # up | down | neutral | ranging
    volatility_regime: str = "normal"  # low | normal | high
    last_swing_high: Optional[float] = None
    last_swing_low: Optional[float] = None
    hh: bool = False                 # higher high formed
    hl: bool = False                 # higher low formed
    lh: bool = False                 # lower high formed
    ll: bool = False                 # lower low formed
    bos: str = "none"                # none | bullish | bearish
    support_zones: List[Zone] = field(default_factory=list)
    resistance_zones: List[Zone] = field(default_factory=list)
    ranging: bool = False
    trending: bool = False
    structure_label: str = "neutral"

    def to_dict(self) -> dict:
        d = asdict(self)
        d["support_zones"] = [asdict(z) for z in self.support_zones]
        d["resistance_zones"] = [asdict(z) for z in self.resistance_zones]
        return d


# ─────────────────────────────────────────────────────────────────────────────
# Swing detection
# ─────────────────────────────────────────────────────────────────────────────

def detect_swings(df: pd.DataFrame, lookback: int = SWING_LOOKBACK) -> List[SwingPoint]:
    """Identify swing highs and lows using a n-bar window either side."""
    swings: List[SwingPoint] = []
    highs = df["high"].values
    lows = df["low"].values
    timestamps = df["timestamp"].values

    for i in range(lookback, len(df) - lookback):
        window_hi = highs[i - lookback: i + lookback + 1]
        window_lo = lows[i - lookback: i + lookback + 1]

        if highs[i] == window_hi.max():
            swings.append(SwingPoint(i, timestamps[i], highs[i], "high"))
        elif lows[i] == window_lo.min():
            swings.append(SwingPoint(i, timestamps[i], lows[i], "low"))

    return swings


# ─────────────────────────────────────────────────────────────────────────────
# HH / HL / LH / LL classification
# ─────────────────────────────────────────────────────────────────────────────

def classify_swings(swings: List[SwingPoint]) -> dict:
    """Return HH, HL, LH, LL flags and BOS based on last 4 swings."""
    result = {"hh": False, "hl": False, "lh": False, "ll": False,
               "bos": "none", "last_swing_high": None, "last_swing_low": None}

    highs = [s for s in swings if s.kind == "high"]
    lows = [s for s in swings if s.kind == "low"]

    if len(highs) >= 2:
        result["last_swing_high"] = highs[-1].price
        if highs[-1].price > highs[-2].price:
            result["hh"] = True
        else:
            result["lh"] = True

    if len(lows) >= 2:
        result["last_swing_low"] = lows[-1].price
        if lows[-1].price > lows[-2].price:
            result["hl"] = True
        else:
            result["ll"] = True

    # Break of structure
    if len(highs) >= 1 and len(lows) >= 1:
        last_high = highs[-1].price
        last_low = lows[-1].price
        current_close = None  # Will be supplied externally
        # BOS is flagged externally when price breaks the last swing
    return result


def detect_bos(df: pd.DataFrame, swings: List[SwingPoint]) -> str:
    """
    Detect Break of Structure based on whether the latest close
    has broken above the last swing high or below the last swing low.
    """
    if df.empty or not swings:
        return "none"
    current_close = df["close"].iloc[-1]
    highs = [s for s in swings if s.kind == "high"]
    lows = [s for s in swings if s.kind == "low"]

    if highs and current_close > highs[-1].price:
        return "bullish"
    if lows and current_close < lows[-1].price:
        return "bearish"
    return "none"


# ─────────────────────────────────────────────────────────────────────────────
# Support / resistance zones
# ─────────────────────────────────────────────────────────────────────────────

def build_zones(swings: List[SwingPoint], tolerance_pct: float = 0.0015) -> List[Zone]:
    """
    Cluster swing points into support/resistance zones.
    tolerance_pct: price within X% counts as same zone.
    """
    zones: List[Zone] = []

    for sp in swings:
        kind = "resistance" if sp.kind == "high" else "support"
        tol = sp.price * tolerance_pct

        matched = False
        for z in zones:
            if z.kind == kind and z.bottom <= sp.price <= z.top + tol:
                z.touches += 1
                z.top = max(z.top, sp.price + tol / 2)
                z.bottom = min(z.bottom, sp.price - tol / 2)
                matched = True
                break

        if not matched:
            zones.append(Zone(
                top=sp.price + tol / 2,
                bottom=sp.price - tol / 2,
                kind=kind,
                touches=1,
            ))

    return [z for z in zones if z.touches >= 2]


# ─────────────────────────────────────────────────────────────────────────────
# Trend and volatility regime
# ─────────────────────────────────────────────────────────────────────────────

def classify_trend(df: pd.DataFrame) -> str:
    """Use EMA ordering and recent swing sequence to classify trend."""
    if "ema_20" not in df.columns or "ema_50" not in df.columns:
        return "neutral"
    last = df.iloc[-1]
    if last["ema_20"] > last["ema_50"] and last["ema_50"] > last.get("ema_200", last["ema_50"]):
        return "up"
    if last["ema_20"] < last["ema_50"] and last["ema_50"] < last.get("ema_200", last["ema_50"]):
        return "down"
    return "neutral"


def classify_volatility(df: pd.DataFrame) -> str:
    """
    Classify volatility regime using ATR percentile over last 100 bars.
    Returns 'low' | 'normal' | 'high'
    """
    if "atr" not in df.columns or len(df) < 50:
        return "normal"
    recent_atr = df["atr"].dropna().tail(100)
    if recent_atr.empty:
        return "normal"
    pct = recent_atr.iloc[-1]
    p25 = recent_atr.quantile(0.25)
    p75 = recent_atr.quantile(0.75)
    if pct < p25:
        return "low"
    if pct > p75:
        return "high"
    return "normal"


def classify_market_type(swings: List[SwingPoint]) -> tuple[bool, bool]:
    """Returns (trending: bool, ranging: bool)."""
    if len(swings) < 4:
        return False, False

    highs = sorted([s for s in swings if s.kind == "high"], key=lambda s: s.index)
    lows = sorted([s for s in swings if s.kind == "low"], key=lambda s: s.index)

    if len(highs) < 2 or len(lows) < 2:
        return False, True

    hi_diffs = [highs[i + 1].price - highs[i].price for i in range(len(highs) - 1)]
    lo_diffs = [lows[i + 1].price - lows[i].price for i in range(len(lows) - 1)]

    trending_up = all(d > 0 for d in hi_diffs) and all(d > 0 for d in lo_diffs)
    trending_dn = all(d < 0 for d in hi_diffs) and all(d < 0 for d in lo_diffs)
    trending = trending_up or trending_dn

    # Ranging: highs and lows oscillate around a mean without consistent direction
    hi_range = max(s.price for s in highs) - min(s.price for s in highs)
    lo_range = max(s.price for s in lows) - min(s.price for s in lows)
    mid_price = (highs[0].price + lows[0].price) / 2
    ranging = (hi_range / mid_price < 0.01) and (lo_range / mid_price < 0.01)

    return trending, ranging


# ─────────────────────────────────────────────────────────────────────────────
# Master function
# ─────────────────────────────────────────────────────────────────────────────

def analyse_structure(df: pd.DataFrame, symbol: str = "EURUSD") -> MarketStructure:
    """
    Full market structure analysis.
    Returns a MarketStructure dataclass instance.
    """
    ms = MarketStructure()

    if df.empty or len(df) < 20:
        log.warning("Insufficient data for structure analysis")
        return ms

    swings = detect_swings(df)
    if not swings:
        return ms

    swing_info = classify_swings(swings)
    ms.hh = swing_info["hh"]
    ms.hl = swing_info["hl"]
    ms.lh = swing_info["lh"]
    ms.ll = swing_info["ll"]
    ms.last_swing_high = swing_info["last_swing_high"]
    ms.last_swing_low = swing_info["last_swing_low"]

    ms.bos = detect_bos(df, swings)
    ms.trend = classify_trend(df)
    ms.volatility_regime = classify_volatility(df)

    trending, ranging = classify_market_type(swings)
    ms.trending = trending
    ms.ranging = ranging

    all_zones = build_zones(swings)
    ms.support_zones = [z for z in all_zones if z.kind == "support"]
    ms.resistance_zones = [z for z in all_zones if z.kind == "resistance"]

    # Human-readable structure label
    if ms.hh and ms.hl:
        ms.structure_label = "bullish_trending"
    elif ms.ll and ms.lh:
        ms.structure_label = "bearish_trending"
    elif ms.ranging:
        ms.structure_label = "ranging"
    else:
        ms.structure_label = "mixed"

    log.info(
        "Structure: {} | BOS: {} | Vol: {} | Zones: {}S {}R",
        ms.structure_label, ms.bos, ms.volatility_regime,
        len(ms.support_zones), len(ms.resistance_zones),
    )
    return ms


def price_near_zone(price: float, zones: List[Zone], atr: float) -> bool:
    """True if price is within 0.5 × ATR of any zone boundary."""
    for z in zones:
        if z.bottom - atr * 0.5 <= price <= z.top + atr * 0.5:
            return True
    return False
