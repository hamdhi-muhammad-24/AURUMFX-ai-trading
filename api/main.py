"""
AURUMFx FastAPI Backend
Provides REST endpoints for signals, backtesting, paper trading, and settings.
"""
from __future__ import annotations

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from contextlib import asynccontextmanager
from typing import Optional, List

from fastapi import FastAPI, HTTPException, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from config import settings
from database.db import init_db
from utils.logger import get_logger

log = get_logger("api")


# ─────────────────────────────────────────────────────────────────────────────
# Startup
# ─────────────────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("Starting AURUMFx API...")
    init_db()
    # Ensure sample calendar exists
    from core.calendar_news import create_sample_calendar
    create_sample_calendar()
    yield
    log.info("AURUMFx API shutting down")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="AI-powered Forex & Gold signal prediction system",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────────────────────────────────────
# Pydantic schemas
# ─────────────────────────────────────────────────────────────────────────────

class SignalRequest(BaseModel):
    symbol: str = "EURUSD"
    timeframe: str = "M15"
    n_bars: int = 500
    force_retrain: bool = False
    paper_mode: bool = True


class BacktestRequest(BaseModel):
    symbol: str = "EURUSD"
    timeframe: str = "M15"
    initial_balance: float = 10_000.0


class PaperCloseRequest(BaseModel):
    symbol: str = "EURUSD"
    close_price: float


# ─────────────────────────────────────────────────────────────────────────────
# Health
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "version": settings.VERSION, "app": settings.APP_NAME}


# ─────────────────────────────────────────────────────────────────────────────
# Signals
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/api/signal")
def generate_signal(req: SignalRequest):
    """Run a full AI analysis cycle and return a trading signal."""
    try:
        from core.agent import run_cycle
        result = run_cycle(
            symbol=req.symbol,
            timeframe=req.timeframe,
            n_bars=req.n_bars,
            force_retrain=req.force_retrain,
            paper_mode=req.paper_mode,
        )
        return result.to_dict()
    except Exception as exc:
        log.error("Signal generation failed: {}", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/signals/{symbol}")
def get_signals(symbol: str, limit: int = Query(50, le=500)):
    """Retrieve recent saved signals for a symbol."""
    import csv
    path = settings.SIGNALS_DIR / f"signals_{symbol}.csv"
    if not path.exists():
        return {"signals": [], "count": 0}
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    rows = rows[-limit:]
    return {"signals": rows, "count": len(rows)}


@app.get("/api/symbols")
def list_symbols():
    return {"symbols": settings.SYMBOLS, "mvp": settings.MVP_SYMBOLS}


@app.get("/api/timeframes")
def list_timeframes():
    return {"timeframes": settings.SUPPORTED_TIMEFRAMES}


# ─────────────────────────────────────────────────────────────────────────────
# Candles
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/api/candles/{symbol}")
def get_candles(
    symbol: str,
    timeframe: str = Query("M15"),
    n_bars: int = Query(200, le=2000),
):
    """Return cleaned candle data as JSON."""
    try:
        from core.data_loader import get_candles as _gc
        df = _gc(symbol, timeframe, n_bars)
        if df.empty:
            return {"candles": [], "count": 0}
        records = df.tail(n_bars).to_dict(orient="records")
        for r in records:
            if hasattr(r.get("timestamp"), "isoformat"):
                r["timestamp"] = r["timestamp"].isoformat()
        return {"candles": records, "count": len(records)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ─────────────────────────────────────────────────────────────────────────────
# Backtesting
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/api/backtest")
def run_backtest_endpoint(req: BacktestRequest, background_tasks: BackgroundTasks):
    """Trigger a backtest run (runs synchronously for MVP; async in prod)."""
    try:
        from core.data_loader import get_candles as _gc
        from core.backtester import run_backtest, save_backtest_result

        df = _gc(req.symbol, req.timeframe, n_bars=settings.TRAIN_LOOKBACK)
        if df.empty:
            raise HTTPException(status_code=400, detail="No data available for backtest")

        result = run_backtest(df, req.symbol, req.timeframe, req.initial_balance)
        save_backtest_result(result)
        return result.to_dict()
    except Exception as exc:
        log.error("Backtest failed: {}", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/backtest/latest/{symbol}")
def get_latest_backtest(symbol: str, timeframe: str = Query("M15")):
    import json
    path = settings.BACKTEST_DIR / f"backtest_{symbol}_{timeframe}.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="No backtest result found")
    with open(path) as f:
        return json.load(f)


# ─────────────────────────────────────────────────────────────────────────────
# Paper trading
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/api/paper/{symbol}")
def get_paper_account(symbol: str):
    from core.paper_trader import get_paper_trader
    trader = get_paper_trader(symbol)
    account = trader.get_account()
    open_pos = [p.to_dict() for p in trader.open_positions.values()]
    closed_pos = [p.to_dict() for p in trader.closed_positions[-20:]]
    return {
        "account": account.to_dict(),
        "open_positions": open_pos,
        "recent_closed": closed_pos,
        "equity_curve": trader.equity_curve[-100:],
    }


@app.post("/api/paper/close-all")
def close_all_paper(req: PaperCloseRequest):
    from core.paper_trader import get_paper_trader
    trader = get_paper_trader(req.symbol)
    trader.close_all(req.close_price)
    return {"status": "closed", "balance": trader.balance}


@app.get("/api/paper/{symbol}/export")
def export_paper_journal(symbol: str):
    from core.paper_trader import get_paper_trader
    trader = get_paper_trader(symbol)
    path = trader.export_journal()
    return {"path": str(path), "status": "exported"}


# ─────────────────────────────────────────────────────────────────────────────
# News / calendar
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/api/news")
def get_news(symbol: str = Query("EURUSD"), hours_ahead: int = Query(24)):
    from core.calendar_news import _load_csv_calendar, check_news_risk
    from datetime import timedelta
    events = _load_csv_calendar()
    check = check_news_risk(symbol, events=events)
    event_dicts = [e.to_dict() for e in events[:50]]
    return {
        "symbol": symbol,
        "news_blocked": check.blocked,
        "block_reason": check.reason,
        "sentiment_score": check.sentiment_score,
        "nearby_events": check.nearby_events or [],
        "all_events": event_dicts,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Risk state
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/api/risk/{symbol}")
def get_risk_state(symbol: str):
    from core.risk_manager import get_tracker
    tracker = get_tracker(symbol)
    tracker.reset_daily()
    return tracker.to_dict()


@app.post("/api/risk/{symbol}/kill-switch")
def toggle_kill_switch(symbol: str, activate: bool = True):
    from core.risk_manager import get_tracker
    tracker = get_tracker(symbol)
    tracker._kill_switch = activate
    return {"symbol": symbol, "kill_switch": activate}


# ─────────────────────────────────────────────────────────────────────────────
# Settings
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/api/settings")
def get_settings():
    return {
        "risk_per_trade_pct": settings.RISK_PER_TRADE_PCT,
        "max_daily_loss_pct": settings.MAX_DAILY_LOSS_PCT,
        "max_open_trades": settings.MAX_OPEN_TRADES,
        "max_trades_per_day": settings.MAX_TRADES_PER_DAY,
        "min_risk_reward": settings.MIN_RISK_REWARD,
        "min_confidence": settings.MIN_CONFIDENCE,
        "paper_enabled": settings.PAPER_ENABLED,
        "demo_trading_enabled": settings.DEMO_TRADING_ENABLED,
        "kill_switch": settings.KILL_SWITCH,
        "mt5_enabled": settings.MT5_ENABLED,
        "news_block_before_min": settings.NEWS_BLOCK_MINUTES_BEFORE,
        "news_block_after_min": settings.NEWS_BLOCK_MINUTES_AFTER,
    }
