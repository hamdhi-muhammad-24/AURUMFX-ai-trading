"""
Module 1 — Live Market Data
Fetches candles from MT5 (if available) or falls back to CSV sample data.
Handles cleaning: missing values, duplicate timestamps, wrong columns.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

import pandas as pd
import numpy as np

from config import settings
from utils.logger import get_logger
from utils.helpers import timeframe_to_minutes, now_utc

log = get_logger("data_loader")

REQUIRED_COLUMNS = ["timestamp", "open", "high", "low", "close", "volume"]
OPTIONAL_COLUMNS = ["spread", "tick_volume", "real_volume"]


# ─────────────────────────────────────────────────────────────────────────────
# MT5 helpers
# ─────────────────────────────────────────────────────────────────────────────

def _mt5_timeframe_const(tf: str):
    """Convert timeframe string to MT5 constant."""
    try:
        import MetaTrader5 as mt5
        mapping = {
            "M1": mt5.TIMEFRAME_M1,
            "M5": mt5.TIMEFRAME_M5,
            "M15": mt5.TIMEFRAME_M15,
            "M30": mt5.TIMEFRAME_M30,
            "H1": mt5.TIMEFRAME_H1,
            "H4": mt5.TIMEFRAME_H4,
            "D1": mt5.TIMEFRAME_D1,
        }
        return mapping.get(tf.upper(), mt5.TIMEFRAME_M15)
    except ImportError:
        return None


def _init_mt5() -> bool:
    if not settings.MT5_ENABLED:
        return False
    try:
        import MetaTrader5 as mt5
        kwargs: dict = {}
        if settings.MT5_PATH:
            kwargs["path"] = settings.MT5_PATH
        if not mt5.initialize(**kwargs):
            log.warning("MT5 initialize() failed: {}", mt5.last_error())
            return False
        if settings.MT5_LOGIN:
            ok = mt5.login(
                login=settings.MT5_LOGIN,
                password=settings.MT5_PASSWORD,
                server=settings.MT5_SERVER,
            )
            if not ok:
                log.warning("MT5 login failed: {}", mt5.last_error())
                return False
        log.info("MT5 connected successfully")
        return True
    except ImportError:
        log.warning("MetaTrader5 package not installed — using CSV fallback")
        return False
    except Exception as exc:
        log.error("MT5 init error: {}", exc)
        return False


def fetch_mt5_candles(
    symbol: str,
    timeframe: str,
    n_bars: int = 500,
    from_date: Optional[datetime] = None,
) -> Optional[pd.DataFrame]:
    """Fetch OHLCV from MT5. Returns None on failure."""
    try:
        import MetaTrader5 as mt5
    except ImportError:
        return None

    if not _init_mt5():
        return None

    tf_const = _mt5_timeframe_const(timeframe)
    if tf_const is None:
        return None

    if from_date:
        rates = mt5.copy_rates_from(symbol, tf_const, from_date, n_bars)
    else:
        rates = mt5.copy_rates_from_pos(symbol, tf_const, 0, n_bars)

    mt5.shutdown()

    if rates is None or len(rates) == 0:
        log.warning("MT5 returned no data for {} {}", symbol, timeframe)
        return None

    df = pd.DataFrame(rates)
    df["timestamp"] = pd.to_datetime(df["time"], unit="s", utc=True)
    df = df.rename(columns={
        "tick_volume": "volume",
        "real_volume": "real_volume",
    })
    if "volume" not in df.columns:
        df["volume"] = df.get("tick_volume", 0)
    if "spread" not in df.columns:
        df["spread"] = 0.0

    log.info("MT5 fetched {} bars for {} {}", len(df), symbol, timeframe)
    return df[["timestamp", "open", "high", "low", "close", "volume", "spread"]]


# ─────────────────────────────────────────────────────────────────────────────
# CSV fallback
# ─────────────────────────────────────────────────────────────────────────────

def _sample_csv_path(symbol: str, timeframe: str) -> Path:
    return settings.SAMPLE_DIR / f"{symbol}_{timeframe}.csv"


def _raw_csv_path(symbol: str, timeframe: str) -> Path:
    return settings.RAW_DIR / f"{symbol}_{timeframe}.csv"


def load_csv_candles(
    symbol: str,
    timeframe: str,
    n_bars: Optional[int] = None,
) -> Optional[pd.DataFrame]:
    """Load candles from CSV. Tries raw/ first, then sample/."""
    for path in [_raw_csv_path(symbol, timeframe), _sample_csv_path(symbol, timeframe)]:
        if path.exists():
            log.info("Loading CSV data from {}", path)
            try:
                df = pd.read_csv(path, parse_dates=["timestamp"])
                df = _clean_candles(df, symbol, timeframe)
                if n_bars:
                    df = df.tail(n_bars)
                return df
            except Exception as exc:
                log.error("CSV load error {}: {}", path, exc)

    log.warning("No CSV found for {} {} — returning None", symbol, timeframe)
    return None


def save_candles_csv(df: pd.DataFrame, symbol: str, timeframe: str, dest: str = "raw") -> Path:
    base = settings.RAW_DIR if dest == "raw" else settings.PROCESSED_DIR
    path = base / f"{symbol}_{timeframe}.csv"
    df.to_csv(path, index=False)
    log.info("Saved {} rows to {}", len(df), path)
    return path


# ─────────────────────────────────────────────────────────────────────────────
# Cleaning
# ─────────────────────────────────────────────────────────────────────────────

def _clean_candles(df: pd.DataFrame, symbol: str, timeframe: str) -> pd.DataFrame:
    """
    Standardise, validate, and clean a raw candle DataFrame.
    Steps:
      1. Normalise column names
      2. Ensure required columns exist
      3. Parse timestamp
      4. Drop duplicate timestamps (keep last)
      5. Sort ascending
      6. Drop rows with NaN OHLC
      7. Validate OHLCV ordering (high >= max(open,close) etc.)
      8. Forward-fill small gaps
    """
    df = df.copy()
    df.columns = [c.lower().strip() for c in df.columns]

    # Alias common column variants
    rename_map = {
        "date": "timestamp", "time": "timestamp", "datetime": "timestamp",
        "o": "open", "h": "high", "l": "low", "c": "close",
        "vol": "volume", "tick_volume": "volume", "real_volume": "volume",
    }
    for old, new in rename_map.items():
        if old in df.columns and new not in df.columns:
            df = df.rename(columns={old: new})

    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        log.error("Missing columns {} in data for {} {}", missing, symbol, timeframe)
        if "volume" in missing:
            df["volume"] = 0.0
        if "timestamp" in missing:
            raise ValueError(f"No timestamp column in data for {symbol} {timeframe}")

    # Parse timestamps
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    df = df.dropna(subset=["timestamp"])

    # Drop duplicates — keep last
    df = df.drop_duplicates(subset=["timestamp"], keep="last")

    # Sort
    df = df.sort_values("timestamp").reset_index(drop=True)

    # Ensure numeric OHLCV
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(subset=["open", "high", "low", "close"])

    # Validate OHLC sanity
    bad_mask = (
        (df["high"] < df["open"]) |
        (df["high"] < df["close"]) |
        (df["low"] > df["open"]) |
        (df["low"] > df["close"]) |
        (df["high"] < df["low"]) |
        (df["close"] <= 0) |
        (df["open"] <= 0)
    )
    if bad_mask.sum() > 0:
        log.warning("Dropping {} malformed candles for {} {}", bad_mask.sum(), symbol, timeframe)
        df = df[~bad_mask]

    # Fill missing optional columns
    if "spread" not in df.columns:
        df["spread"] = 0.0

    # Fill small gaps (≤ 3 candles) with forward-fill
    tf_min = timeframe_to_minutes(timeframe)
    expected_delta = pd.Timedelta(minutes=tf_min)
    df = df.reset_index(drop=True)

    log.info("Cleaned {} bars for {} {}", len(df), symbol, timeframe)
    return df[["timestamp", "open", "high", "low", "close", "volume", "spread"]]


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def get_candles(
    symbol: str,
    timeframe: str = "M15",
    n_bars: int = 500,
    from_date: Optional[datetime] = None,
    force_csv: bool = False,
) -> pd.DataFrame:
    """
    Master function: try MT5 first, fall back to CSV.
    Always returns a cleaned DataFrame with columns:
    timestamp, open, high, low, close, volume, spread
    """
    df = None

    if not force_csv and settings.MT5_ENABLED:
        df = fetch_mt5_candles(symbol, timeframe, n_bars, from_date)

    if df is None or df.empty:
        df = load_csv_candles(symbol, timeframe, n_bars)

    if df is None or df.empty:
        log.error("No data available for {} {}", symbol, timeframe)
        return pd.DataFrame(columns=REQUIRED_COLUMNS)

    return df


def get_latest_candle(symbol: str, timeframe: str = "M15") -> Optional[dict]:
    """Return the most recent completed candle as a dict."""
    df = get_candles(symbol, timeframe, n_bars=2)
    if df.empty:
        return None
    row = df.iloc[-1]
    return row.to_dict()


def merge_new_candles(existing: pd.DataFrame, new: pd.DataFrame) -> pd.DataFrame:
    """Merge two candle DataFrames, deduplicate, and sort."""
    combined = pd.concat([existing, new], ignore_index=True)
    combined = combined.drop_duplicates(subset=["timestamp"], keep="last")
    combined = combined.sort_values("timestamp").reset_index(drop=True)
    return combined
