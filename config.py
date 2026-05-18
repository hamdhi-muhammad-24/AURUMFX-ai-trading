"""
AURUMFx AI Trading System — Central Configuration
All runtime settings live here; override via .env or environment variables.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import List

from pydantic_settings import BaseSettings
from pydantic import Field

BASE_DIR = Path(__file__).parent


class Settings(BaseSettings):
    # ── Project meta ────────────────────────────────────────────────────────
    APP_NAME: str = "AURUMFx AI Trading System"
    VERSION: str = "1.0.0"
    ENV: str = "development"          # development | production

    # ── Supported symbols ───────────────────────────────────────────────────
    SYMBOLS: List[str] = ["EURUSD", "XAUUSD", "GBPUSD", "USDJPY",
                           "USDCHF", "AUDUSD", "USDCAD", "NZDUSD"]
    MVP_SYMBOLS: List[str] = ["EURUSD", "XAUUSD"]
    DEFAULT_SYMBOL: str = "EURUSD"
    DEFAULT_TIMEFRAME: str = "M15"    # M5 | M15 | H1 | H4
    SUPPORTED_TIMEFRAMES: List[str] = ["M5", "M15", "H1", "H4"]

    # ── Paths ────────────────────────────────────────────────────────────────
    DATA_DIR: Path = BASE_DIR / "data"
    RAW_DIR: Path = BASE_DIR / "data" / "raw"
    PROCESSED_DIR: Path = BASE_DIR / "data" / "processed"
    SIGNALS_DIR: Path = BASE_DIR / "data" / "signals"
    MODELS_DIR: Path = BASE_DIR / "data" / "models"
    SAMPLE_DIR: Path = BASE_DIR / "data" / "sample"
    PAPER_DIR: Path = BASE_DIR / "data" / "paper_trades"
    BACKTEST_DIR: Path = BASE_DIR / "data" / "backtest"
    NEWS_DIR: Path = BASE_DIR / "data" / "news"

    # ── Database ─────────────────────────────────────────────────────────────
    DATABASE_URL: str = f"sqlite:///{BASE_DIR / 'data' / 'aurumfx.db'}"
    # For PostgreSQL: DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/aurumfx

    # ── MT5 connection ────────────────────────────────────────────────────────
    MT5_ENABLED: bool = False         # set True when MT5 is installed
    MT5_LOGIN: int = 0
    MT5_PASSWORD: str = ""
    MT5_SERVER: str = ""
    MT5_PATH: str = ""                # path to terminal64.exe if needed

    # ── Data ingestion ────────────────────────────────────────────────────────
    CANDLES_LOOKBACK: int = 500       # bars to fetch for live analysis
    TRAIN_LOOKBACK: int = 5000        # bars for training
    MIN_CANDLES_REQUIRED: int = 250   # minimum bars before running ML

    # ── Feature engineering ───────────────────────────────────────────────────
    EMA_FAST: int = 20
    EMA_MID: int = 50
    EMA_SLOW: int = 200
    RSI_PERIOD: int = 14
    ATR_PERIOD: int = 14
    BB_PERIOD: int = 20
    BB_STD: float = 2.0
    MACD_FAST: int = 12
    MACD_SLOW: int = 26
    MACD_SIGNAL: int = 9
    VOLATILITY_WINDOW: int = 20
    FUTURE_BARS: int = 12             # bars ahead to compute label

    # ── ML settings ──────────────────────────────────────────────────────────
    LABEL_THRESHOLD_ATR_MULT: float = 0.5   # label = BUY if return > 0.5×ATR
    MIN_CONFIDENCE: float = 0.60            # below this → NO_TRADE
    TRAIN_TEST_RATIO: float = 0.80          # time-aware split
    MODEL_RETRAIN_EVERY: int = 500          # bars between auto-retrain
    RANDOM_STATE: int = 42

    # ── Rule engine ───────────────────────────────────────────────────────────
    MAX_SPREAD_PIPS: float = 3.0
    RSI_OVERBOUGHT: float = 70.0
    RSI_OVERSOLD: float = 30.0
    RSI_NEUTRAL_LOW: float = 40.0
    RSI_NEUTRAL_HIGH: float = 60.0
    MIN_ATR_PIPS: float = 3.0        # skip when volatility too low
    MAX_ATR_PIPS: float = 80.0       # skip when volatility too high (XAU)
    NEWS_BLOCK_MINUTES_BEFORE: int = 30
    NEWS_BLOCK_MINUTES_AFTER: int = 15

    # ── Risk management ───────────────────────────────────────────────────────
    DEFAULT_BALANCE: float = 10_000.0
    RISK_PER_TRADE_PCT: float = 1.0          # %
    MAX_DAILY_LOSS_PCT: float = 3.0          # % of balance
    MAX_OPEN_TRADES: int = 1
    MAX_TRADES_PER_DAY: int = 3
    MIN_RISK_REWARD: float = 1.5
    DEFAULT_LEVERAGE: float = 100.0
    SL_ATR_MULT: float = 1.5                 # SL = 1.5 × ATR
    TP_ATR_MULT: float = 2.25                # TP = 2.25 × ATR  (1:1.5 RR)

    # ── Pip values ────────────────────────────────────────────────────────────
    PIP_SIZE: dict = {
        "EURUSD": 0.0001, "GBPUSD": 0.0001, "AUDUSD": 0.0001,
        "NZDUSD": 0.0001, "USDCAD": 0.0001, "USDCHF": 0.0001,
        "USDJPY": 0.01,   "XAUUSD": 0.1,
    }
    LOT_USD_PER_PIP: dict = {
        "EURUSD": 10.0, "GBPUSD": 10.0, "AUDUSD": 10.0,
        "NZDUSD": 10.0, "USDCAD": 10.0, "USDCHF": 10.0,
        "USDJPY": 10.0, "XAUUSD": 10.0,
    }

    # ── Paper trading ─────────────────────────────────────────────────────────
    PAPER_ENABLED: bool = True
    PAPER_BALANCE: float = 10_000.0

    # ── Auto / demo trading (DISABLED BY DEFAULT) ─────────────────────────────
    DEMO_TRADING_ENABLED: bool = False   # must be manually set True
    KILL_SWITCH: bool = False            # True = halt all execution immediately
    REQUIRE_MANUAL_APPROVAL: bool = True

    # ── FastAPI ───────────────────────────────────────────────────────────────
    API_HOST: str = "127.0.0.1"
    API_PORT: int = 8000
    API_RELOAD: bool = True

    # ── Streamlit ─────────────────────────────────────────────────────────────
    DASHBOARD_PORT: int = 8501

    # ── External APIs (optional) ──────────────────────────────────────────────
    NEWS_API_KEY: str = ""            # newsapi.org
    CALENDAR_API_URL: str = ""        # e.g. investing.com scrape or FF calendar
    ANTHROPIC_API_KEY: str = ""       # for LLM explanation module

    # ── Logging ───────────────────────────────────────────────────────────────
    LOG_LEVEL: str = "INFO"
    LOG_FILE: Path = BASE_DIR / "data" / "aurumfx.log"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()


def get_pip_size(symbol: str) -> float:
    return settings.PIP_SIZE.get(symbol, 0.0001)


def get_lot_usd_per_pip(symbol: str) -> float:
    return settings.LOT_USD_PER_PIP.get(symbol, 10.0)
