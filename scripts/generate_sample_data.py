"""
Generates realistic synthetic OHLCV candle data for EURUSD and XAUUSD.
Uses Geometric Brownian Motion with session-aware volatility.
Run: python scripts/generate_sample_data.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pathlib import Path
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd

from config import settings

np.random.seed(42)


def generate_gbm_candles(
    symbol: str,
    timeframe: str,
    n_bars: int,
    start_price: float,
    annual_vol: float = 0.10,
    drift: float = 0.00,
    start_dt: datetime = None,
) -> pd.DataFrame:
    """
    Simulate candles using Geometric Brownian Motion.
    Each candle: open = prev close, then generate realistic H/L/C within bar.
    """
    tf_min = {"M5": 5, "M15": 15, "H1": 60, "H4": 240}[timeframe]
    dt_step = timedelta(minutes=tf_min)

    bars_per_year = 252 * 24 * 60 / tf_min
    bar_vol = annual_vol / np.sqrt(bars_per_year)
    bar_drift = drift / bars_per_year

    if start_dt is None:
        start_dt = datetime.now(timezone.utc) - dt_step * n_bars

    prices = [start_price]
    for _ in range(n_bars):
        ret = bar_drift + bar_vol * np.random.randn()
        prices.append(prices[-1] * np.exp(ret))

    rows = []
    ts = start_dt
    for i in range(n_bars):
        o = prices[i]
        c = prices[i + 1]

        # Realistic intra-bar H/L
        intra_vol = bar_vol * start_price
        h = max(o, c) + abs(np.random.exponential(intra_vol * 0.7))
        l = min(o, c) - abs(np.random.exponential(intra_vol * 0.7))
        h = round(h, 5 if "XAU" not in symbol else 2)
        l = round(l, 5 if "XAU" not in symbol else 2)
        o = round(o, 5 if "XAU" not in symbol else 2)
        c = round(c, 5 if "XAU" not in symbol else 2)

        vol = int(abs(np.random.normal(1000, 400)))
        spread = round(abs(np.random.normal(0.5 if "XAU" not in symbol else 2.0, 0.2)), 1)

        # Skip weekends
        if ts.weekday() < 5:
            rows.append({
                "timestamp": ts.strftime("%Y-%m-%d %H:%M:%S+00:00"),
                "open": o, "high": h, "low": l, "close": c,
                "volume": max(100, vol),
                "spread": spread,
            })
        ts += dt_step

    return pd.DataFrame(rows)


def main():
    out_dir = settings.SAMPLE_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    configs = [
        # symbol, TF, n_bars, start_price, ann_vol
        ("EURUSD", "M15", 6000, 1.08500, 0.07),
        ("EURUSD", "M5",  6000, 1.08500, 0.07),
        ("EURUSD", "H1",  3000, 1.08500, 0.07),
        ("EURUSD", "H4",  1500, 1.08500, 0.07),
        ("XAUUSD", "M15", 6000, 2350.00, 0.15),
        ("XAUUSD", "M5",  6000, 2350.00, 0.15),
        ("XAUUSD", "H1",  3000, 2350.00, 0.15),
        ("XAUUSD", "H4",  1500, 2350.00, 0.15),
        ("GBPUSD", "M15", 3000, 1.26500, 0.09),
        ("USDJPY", "M15", 3000, 151.500, 0.09),
    ]

    for symbol, tf, n_bars, start_price, ann_vol in configs:
        df = generate_gbm_candles(symbol, tf, n_bars, start_price, ann_vol)
        path = out_dir / f"{symbol}_{tf}.csv"
        df.to_csv(path, index=False)
        print(f"Generated {len(df)} bars -> {path}")

    print(f"\nSample data created in: {out_dir}")
    print("The system will automatically use these files when MT5 is not available.")


if __name__ == "__main__":
    main()
