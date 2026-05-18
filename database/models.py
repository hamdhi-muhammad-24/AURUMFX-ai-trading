"""SQLAlchemy ORM models for the AURUMFx trading system."""
from __future__ import annotations

import json
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Column, Integer, Float, String, Boolean, DateTime,
    Text, JSON, ForeignKey, Index, UniqueConstraint,
)
from sqlalchemy.orm import relationship

from database.db import Base


class Candle(Base):
    __tablename__ = "candles"
    __table_args__ = (
        UniqueConstraint("symbol", "timeframe", "timestamp", name="uq_candle"),
        Index("ix_candle_symbol_tf_ts", "symbol", "timeframe", "timestamp"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(16), nullable=False, index=True)
    timeframe = Column(String(8), nullable=False)
    timestamp = Column(DateTime, nullable=False)
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Float, default=0.0)
    spread = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)


class Signal(Base):
    __tablename__ = "signals"
    __table_args__ = (
        Index("ix_signal_symbol_ts", "symbol", "timestamp"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(16), nullable=False)
    timeframe = Column(String(8), nullable=False)
    timestamp = Column(DateTime, nullable=False)

    # Final output
    signal = Column(String(16), nullable=False)   # BUY | SELL | HOLD | NO_TRADE
    confidence = Column(Float, default=0.0)        # 0.0 – 1.0
    explanation = Column(Text, default="")

    # ML layer
    ml_prediction = Column(String(16), default="")
    ml_confidence = Column(Float, default=0.0)
    ml_probabilities = Column(JSON, default=dict)

    # Market data at signal time
    price_at_signal = Column(Float, default=0.0)
    sl_price = Column(Float, default=0.0)
    tp_price = Column(Float, default=0.0)
    lot_size = Column(Float, default=0.0)
    risk_amount = Column(Float, default=0.0)
    atr = Column(Float, default=0.0)
    spread = Column(Float, default=0.0)

    # Filters applied
    ema_trend = Column(String(8), default="")
    rsi_value = Column(Float, default=0.0)
    macd_value = Column(Float, default=0.0)
    structure_label = Column(String(32), default="")
    blocked_by = Column(Text, default="")          # comma-separated block reasons

    # Source
    source = Column(String(16), default="agent")   # agent | backtest | paper
    created_at = Column(DateTime, default=datetime.utcnow)


class PaperTrade(Base):
    __tablename__ = "paper_trades"
    __table_args__ = (
        Index("ix_paper_symbol_status", "symbol", "status"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    signal_id = Column(Integer, ForeignKey("signals.id"), nullable=True)

    symbol = Column(String(16), nullable=False)
    timeframe = Column(String(8), nullable=False)
    direction = Column(String(8), nullable=False)   # BUY | SELL
    status = Column(String(16), default="open")     # open | closed | cancelled

    entry_price = Column(Float, nullable=False)
    sl_price = Column(Float, nullable=False)
    tp_price = Column(Float, nullable=False)
    lot_size = Column(Float, default=0.01)
    risk_amount = Column(Float, default=0.0)

    exit_price = Column(Float, nullable=True)
    exit_reason = Column(String(16), default="")    # SL | TP | SIGNAL | MANUAL
    pnl = Column(Float, default=0.0)
    pips = Column(Float, default=0.0)

    opened_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    closed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class BacktestRun(Base):
    __tablename__ = "backtest_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(16), nullable=False)
    timeframe = Column(String(8), nullable=False)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)

    initial_balance = Column(Float, default=10_000.0)
    final_balance = Column(Float, default=0.0)
    total_trades = Column(Integer, default=0)
    winning_trades = Column(Integer, default=0)
    losing_trades = Column(Integer, default=0)
    win_rate = Column(Float, default=0.0)
    profit_factor = Column(Float, default=0.0)
    max_drawdown_pct = Column(Float, default=0.0)
    sharpe_ratio = Column(Float, default=0.0)
    blocked_count = Column(Integer, default=0)
    no_trade_count = Column(Integer, default=0)

    trade_log = Column(JSON, default=list)
    equity_curve = Column(JSON, default=list)
    settings_snapshot = Column(JSON, default=dict)

    created_at = Column(DateTime, default=datetime.utcnow)


class NewsEvent(Base):
    __tablename__ = "news_events"
    __table_args__ = (
        Index("ix_news_currency_ts", "currency", "event_time"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_time = Column(DateTime, nullable=False)
    currency = Column(String(8), nullable=False)
    country = Column(String(64), default="")
    title = Column(String(256), nullable=False)
    impact = Column(String(16), default="low")       # low | medium | high
    actual = Column(String(32), default="")
    forecast = Column(String(32), default="")
    previous = Column(String(32), default="")
    sentiment = Column(Float, default=0.0)            # -1 negative, 0 neutral, +1 positive
    created_at = Column(DateTime, default=datetime.utcnow)


class RiskState(Base):
    """Tracks intraday risk counters — one row per symbol per day."""
    __tablename__ = "risk_state"
    __table_args__ = (
        UniqueConstraint("symbol", "date", name="uq_risk_state"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(16), nullable=False)
    date = Column(String(10), nullable=False)          # YYYY-MM-DD
    trades_opened = Column(Integer, default=0)
    daily_pnl = Column(Float, default=0.0)
    kill_switch_active = Column(Boolean, default=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
