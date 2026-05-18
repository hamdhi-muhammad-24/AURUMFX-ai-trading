"""
Module 2 — Feature Engineering
Calculates all technical indicators from OHLCV candle data.
Pure pandas/numpy — no TA-lib dependency required.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from typing import Optional

from config import settings
from utils.logger import get_logger
from utils.helpers import session_tag

log = get_logger("feature_engineering")


# ─────────────────────────────────────────────────────────────────────────────
# Low-level indicator functions
# ─────────────────────────────────────────────────────────────────────────────

def ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(com=period - 1, adjust=False).mean()
    avg_loss = loss.ewm(com=period - 1, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def macd(
    series: pd.Series,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    ema_fast = ema(series, fast)
    ema_slow = ema(series, slow)
    macd_line = ema_fast - ema_slow
    signal_line = ema(macd_line, signal)
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr.ewm(com=period - 1, adjust=False).mean()


def bollinger_bands(
    series: pd.Series,
    period: int = 20,
    std_mult: float = 2.0,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    mid = series.rolling(period).mean()
    std = series.rolling(period).std(ddof=0)
    upper = mid + std_mult * std
    lower = mid - std_mult * std
    return upper, mid, lower


def rolling_volatility(series: pd.Series, window: int = 20) -> pd.Series:
    log_ret = np.log(series / series.shift(1))
    return log_ret.rolling(window).std() * np.sqrt(window)


# ─────────────────────────────────────────────────────────────────────────────
# Candle structure features
# ─────────────────────────────────────────────────────────────────────────────

def candle_features(df: pd.DataFrame) -> pd.DataFrame:
    """Body size, upper/lower wick, candle range — all in price units."""
    df = df.copy()
    df["candle_range"] = df["high"] - df["low"]
    df["body"] = (df["close"] - df["open"]).abs()
    df["upper_wick"] = df["high"] - df[["open", "close"]].max(axis=1)
    df["lower_wick"] = df[["open", "close"]].min(axis=1) - df["low"]
    df["is_bullish"] = (df["close"] > df["open"]).astype(int)
    # Normalise body relative to range to avoid scale issues
    df["body_ratio"] = np.where(
        df["candle_range"] > 0, df["body"] / df["candle_range"], 0.0
    )
    return df


def return_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["return_1"] = df["close"].pct_change(1)
    df["return_3"] = df["close"].pct_change(3)
    df["return_6"] = df["close"].pct_change(6)
    return df


# ─────────────────────────────────────────────────────────────────────────────
# Session tag
# ─────────────────────────────────────────────────────────────────────────────

def add_session_tag(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["session"] = df["timestamp"].apply(
        lambda t: session_tag(t) if pd.notna(t) else "unknown"
    )
    SESSION_DUMMIES = ["sydney", "tokyo", "london", "new_york", "overlap"]
    for s in SESSION_DUMMIES:
        df[f"sess_{s}"] = (df["session"] == s).astype(int)
    return df


# ─────────────────────────────────────────────────────────────────────────────
# Master feature builder
# ─────────────────────────────────────────────────────────────────────────────

def build_features(df: pd.DataFrame, symbol: str = "EURUSD") -> pd.DataFrame:
    """
    Takes a cleaned candle DataFrame and returns it enriched with all features.
    Input must have columns: timestamp, open, high, low, close, volume, spread
    """
    if df.empty or len(df) < 50:
        log.warning("Not enough data to build features ({} rows)", len(df))
        return df

    df = df.copy().reset_index(drop=True)

    # ── Trend indicators ─────────────────────────────────────────────────────
    df["ema_20"] = ema(df["close"], settings.EMA_FAST)
    df["ema_50"] = ema(df["close"], settings.EMA_MID)
    df["ema_200"] = ema(df["close"], settings.EMA_SLOW)

    df["ema_trend"] = np.where(
        (df["close"] > df["ema_20"]) & (df["ema_20"] > df["ema_50"]) & (df["ema_50"] > df["ema_200"]),
        "up",
        np.where(
            (df["close"] < df["ema_20"]) & (df["ema_20"] < df["ema_50"]) & (df["ema_50"] < df["ema_200"]),
            "down",
            "neutral",
        ),
    )

    # Distance from EMAs (normalised by ATR for scale-invariance)
    _atr = atr(df["high"], df["low"], df["close"], settings.ATR_PERIOD)
    df["atr"] = _atr
    _safe_atr = _atr.replace(0, np.nan)
    df["dist_ema20"] = (df["close"] - df["ema_20"]) / _safe_atr
    df["dist_ema50"] = (df["close"] - df["ema_50"]) / _safe_atr
    df["dist_ema200"] = (df["close"] - df["ema_200"]) / _safe_atr

    # ── Momentum ─────────────────────────────────────────────────────────────
    df["rsi"] = rsi(df["close"], settings.RSI_PERIOD)
    macd_line, macd_sig, macd_hist = macd(
        df["close"], settings.MACD_FAST, settings.MACD_SLOW, settings.MACD_SIGNAL
    )
    df["macd"] = macd_line
    df["macd_signal"] = macd_sig
    df["macd_hist"] = macd_hist

    # ── Volatility ────────────────────────────────────────────────────────────
    bb_upper, bb_mid, bb_lower = bollinger_bands(
        df["close"], settings.BB_PERIOD, settings.BB_STD
    )
    df["bb_upper"] = bb_upper
    df["bb_mid"] = bb_mid
    df["bb_lower"] = bb_lower
    df["bb_width"] = (bb_upper - bb_lower) / bb_mid.replace(0, np.nan)
    df["bb_pct"] = (df["close"] - bb_lower) / (bb_upper - bb_lower).replace(0, np.nan)

    df["volatility"] = rolling_volatility(df["close"], settings.VOLATILITY_WINDOW)

    # ── Candle structure ──────────────────────────────────────────────────────
    df = candle_features(df)
    df = return_features(df)

    # ── Session ───────────────────────────────────────────────────────────────
    df = add_session_tag(df)

    # ── Volume features ───────────────────────────────────────────────────────
    df["volume_ma"] = df["volume"].rolling(20).mean()
    df["volume_ratio"] = df["volume"] / df["volume_ma"].replace(0, np.nan)

    # ── Lag features (prior bar) ──────────────────────────────────────────────
    for col in ["rsi", "macd_hist", "return_1"]:
        df[f"{col}_lag1"] = df[col].shift(1)
        df[f"{col}_lag2"] = df[col].shift(2)

    # ── ATR in pips (for display) ──────────────────────────────────────────────
    from utils.helpers import price_to_pips
    df["atr_pips"] = df["atr"].apply(lambda x: price_to_pips(x, symbol))

    log.info("Feature engineering complete — {} cols, {} rows", len(df.columns), len(df))
    return df


def get_feature_columns() -> list[str]:
    """Return the list of ML feature columns (no OHLCV, no target, no timestamp)."""
    return [
        "ema_20", "ema_50", "ema_200",
        "dist_ema20", "dist_ema50", "dist_ema200",
        "rsi", "macd", "macd_signal", "macd_hist",
        "atr", "bb_width", "bb_pct",
        "volatility",
        "candle_range", "body", "upper_wick", "lower_wick", "body_ratio", "is_bullish",
        "return_1", "return_3", "return_6",
        "volume_ratio",
        "rsi_lag1", "rsi_lag2",
        "macd_hist_lag1", "macd_hist_lag2",
        "return_1_lag1", "return_1_lag2",
        "sess_london", "sess_new_york", "sess_tokyo", "sess_sydney", "sess_overlap",
    ]
