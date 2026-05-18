"""
Module 8 — Backtesting Engine
Simulates the full strategy (ML + rules + risk) on historical data.
Walk-forward: trains on first 70%, tests on remaining 30%.
Outputs: equity curve, trade log, performance metrics.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any

import numpy as np
import pandas as pd

from config import settings
from core.feature_engineering import build_features, get_feature_columns
from core.market_structure import analyse_structure
from core.ml_predictor import create_labels, train_models, predict
from core.rule_engine import evaluate as rule_evaluate
from core.risk_manager import approve_trade, RiskParams
from core.calendar_news import check_news_risk, _load_csv_calendar
from utils.logger import get_logger
from utils.helpers import price_to_pips

log = get_logger("backtester")


# ─────────────────────────────────────────────────────────────────────────────
# Trade record
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class BacktestTrade:
    bar_index: int
    timestamp: str
    direction: str
    entry_price: float
    sl_price: float
    tp_price: float
    lot_size: float
    sl_pips: float
    tp_pips: float
    risk_amount: float
    exit_price: float = 0.0
    exit_reason: str = ""
    pnl: float = 0.0
    pips: float = 0.0
    duration_bars: int = 0

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class BacktestResult:
    symbol: str
    timeframe: str
    start_date: str
    end_date: str
    initial_balance: float
    final_balance: float
    peak_balance: float
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    max_drawdown_pct: float = 0.0
    sharpe_ratio: float = 0.0
    total_pips: float = 0.0
    blocked_count: int = 0
    no_trade_count: int = 0
    trade_log: List[dict] = field(default_factory=list)
    equity_curve: List[float] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


# ─────────────────────────────────────────────────────────────────────────────
# Metrics
# ─────────────────────────────────────────────────────────────────────────────

def _compute_metrics(result: BacktestResult) -> BacktestResult:
    trades = result.trade_log
    if not trades:
        return result

    winners = [t for t in trades if t["pnl"] > 0]
    losers = [t for t in trades if t["pnl"] < 0]

    result.total_trades = len(trades)
    result.winning_trades = len(winners)
    result.losing_trades = len(losers)
    result.win_rate = round(len(winners) / len(trades) * 100, 2) if trades else 0.0

    gross_profit = sum(t["pnl"] for t in winners)
    gross_loss = abs(sum(t["pnl"] for t in losers))
    result.profit_factor = round(gross_profit / gross_loss, 3) if gross_loss > 0 else float("inf")
    result.total_pips = round(sum(t["pips"] for t in trades), 1)

    # Drawdown
    eq = result.equity_curve
    if eq:
        peak = eq[0]
        max_dd = 0.0
        for v in eq:
            if v > peak:
                peak = v
            dd = (peak - v) / peak * 100
            if dd > max_dd:
                max_dd = dd
        result.max_drawdown_pct = round(max_dd, 2)
        result.peak_balance = round(max(eq), 2)
    else:
        result.peak_balance = result.initial_balance

    # Sharpe (simplified daily returns)
    if len(eq) > 1:
        returns = np.diff(eq) / np.array(eq[:-1])
        if returns.std() > 0:
            result.sharpe_ratio = round(returns.mean() / returns.std() * np.sqrt(252), 3)

    return result


# ─────────────────────────────────────────────────────────────────────────────
# Bar simulator
# ─────────────────────────────────────────────────────────────────────────────

def _simulate_trade_exit(
    trade: BacktestTrade,
    future_df: pd.DataFrame,
    start_idx: int,
    symbol: str,
) -> BacktestTrade:
    """Walk forward through bars until SL, TP, or end of data."""
    from utils.helpers import get_lot_usd_per_pip
    pip_value = price_to_pips(1.0, symbol)  # pips per 1 price unit
    usd_per_pip = 10.0  # standard lot approximation

    for i in range(start_idx, min(start_idx + 200, len(future_df))):
        bar = future_df.iloc[i]
        direction = trade.direction

        if direction == "BUY":
            if bar["low"] <= trade.sl_price:
                trade.exit_price = trade.sl_price
                trade.exit_reason = "SL"
                trade.pips = -(trade.sl_pips)
                break
            if bar["high"] >= trade.tp_price:
                trade.exit_price = trade.tp_price
                trade.exit_reason = "TP"
                trade.pips = trade.tp_pips
                break
        else:  # SELL
            if bar["high"] >= trade.sl_price:
                trade.exit_price = trade.sl_price
                trade.exit_reason = "SL"
                trade.pips = -(trade.sl_pips)
                break
            if bar["low"] <= trade.tp_price:
                trade.exit_price = trade.tp_price
                trade.exit_reason = "TP"
                trade.pips = trade.tp_pips
                break

        trade.duration_bars = i - start_idx + 1

    if not trade.exit_reason:
        # Hit end of data — close at last bar
        last = future_df.iloc[min(start_idx + 199, len(future_df) - 1)]
        trade.exit_price = last["close"]
        trade.exit_reason = "END"
        diff = trade.exit_price - trade.entry_price
        if trade.direction == "SELL":
            diff = -diff
        trade.pips = price_to_pips(diff, symbol) * (1 if diff > 0 else -1)

    trade.pnl = round(trade.pips * trade.lot_size * usd_per_pip, 2)
    return trade


# ─────────────────────────────────────────────────────────────────────────────
# Main backtest runner
# ─────────────────────────────────────────────────────────────────────────────

def run_backtest(
    df_raw: pd.DataFrame,
    symbol: str = "EURUSD",
    timeframe: str = "M15",
    initial_balance: float = None,
    risk_params: Optional[RiskParams] = None,
    warmup_bars: int = 250,
) -> BacktestResult:
    """
    Full backtest:
    1. Build features on complete dataset (no leakage — labels use future bars)
    2. Train models on first 70% bars
    3. Walk forward through remaining 30% bar by bar
    4. Apply full rule + risk engine per bar
    5. Simulate SL/TP exits
    """
    initial_balance = initial_balance or settings.DEFAULT_BALANCE
    risk_params = risk_params or RiskParams(balance=initial_balance)

    log.info("Starting backtest: {} {} | {} bars", symbol, timeframe, len(df_raw))

    # Build features
    df = build_features(df_raw.copy(), symbol)
    df = df.dropna(subset=get_feature_columns()).reset_index(drop=True)

    if len(df) < settings.MIN_CANDLES_REQUIRED + warmup_bars:
        log.error("Not enough data for backtest: {} rows", len(df))
        return BacktestResult(
            symbol=symbol, timeframe=timeframe,
            start_date="", end_date="",
            initial_balance=initial_balance,
            final_balance=initial_balance,
            peak_balance=initial_balance,
        )

    # Train on first 70%
    train_split = int(len(df) * 0.70)
    df_train = df.iloc[:train_split]
    df_test = df.iloc[train_split:].reset_index(drop=True)

    log.info("Training on {} bars, testing on {} bars", len(df_train), len(df_test))
    train_models(df_train, symbol, timeframe)

    # Load news events once
    news_events = _load_csv_calendar()

    # Result container
    result = BacktestResult(
        symbol=symbol, timeframe=timeframe,
        start_date=str(df_test.iloc[0]["timestamp"]),
        end_date=str(df_test.iloc[-1]["timestamp"]),
        initial_balance=initial_balance,
        final_balance=initial_balance,
        peak_balance=initial_balance,
    )

    balance = initial_balance
    equity_curve = [balance]
    trade_log: List[dict] = []
    open_trade: Optional[BacktestTrade] = None
    trades_today = 0
    daily_pnl = 0.0
    last_date = None

    for i, row in df_test.iterrows():
        bar_date = pd.Timestamp(row["timestamp"]).date()

        # Daily reset
        if last_date != bar_date:
            last_date = bar_date
            trades_today = 0
            daily_pnl = 0.0

        # Check if open trade hit SL/TP on this bar
        if open_trade:
            direction = open_trade.direction
            if direction == "BUY":
                if row["low"] <= open_trade.sl_price:
                    open_trade.exit_price = open_trade.sl_price
                    open_trade.exit_reason = "SL"
                    open_trade.pips = -(open_trade.sl_pips)
                elif row["high"] >= open_trade.tp_price:
                    open_trade.exit_price = open_trade.tp_price
                    open_trade.exit_reason = "TP"
                    open_trade.pips = open_trade.tp_pips
            else:
                if row["high"] >= open_trade.sl_price:
                    open_trade.exit_price = open_trade.sl_price
                    open_trade.exit_reason = "SL"
                    open_trade.pips = -(open_trade.sl_pips)
                elif row["low"] <= open_trade.tp_price:
                    open_trade.exit_price = open_trade.tp_price
                    open_trade.exit_reason = "TP"
                    open_trade.pips = open_trade.tp_pips

            if open_trade.exit_reason:
                pnl = round(open_trade.pips * open_trade.lot_size * 10.0, 2)
                open_trade.pnl = pnl
                balance += pnl
                daily_pnl += pnl
                equity_curve.append(balance)
                trade_log.append(open_trade.to_dict())
                log.debug("Trade closed: {} {} pips | balance ${:.2f}", open_trade.exit_reason, open_trade.pips, balance)
                open_trade = None

        if open_trade is not None:
            continue  # one trade at a time

        # Get ML signal on this bar (using rolling window up to this bar)
        window = df_test.iloc[max(0, i - warmup_bars): i + 1]
        if len(window) < 50:
            result.no_trade_count += 1
            continue

        from core.ml_predictor import predict as ml_predict, PredictionResult
        ml_result = ml_predict(window, symbol, timeframe)

        if ml_result.signal == "HOLD" or ml_result.confidence < 0.40:
            result.no_trade_count += 1
            continue

        # News check
        ts = pd.Timestamp(row["timestamp"])
        if ts.tzinfo is None:
            import pytz
            ts = ts.replace(tzinfo=pytz.utc)
        news_check = check_news_risk(symbol, ts.to_pydatetime(), news_events)

        # Rule engine
        rule_result = rule_evaluate(
            ml_signal=ml_result.signal,
            ml_confidence=ml_result.confidence,
            ml_probabilities=ml_result.probabilities or {},
            ema_trend=str(row.get("ema_trend", "neutral")),
            rsi=float(row.get("rsi", 50)),
            macd_hist=float(row.get("macd_hist", 0)),
            atr=float(row.get("atr", 0.001)),
            spread=float(row.get("spread", 0)),
            symbol=symbol,
            structure_label="neutral",
            bos="none",
            news_blocked=news_check.blocked,
            news_reason=news_check.reason,
            daily_loss_pct=abs(daily_pnl) / balance * 100 if daily_pnl < 0 else 0,
            trades_today=trades_today,
            open_trades=0,
        )

        if rule_result.final_signal not in ("BUY", "SELL"):
            if rule_result.blocks:
                result.blocked_count += 1
            else:
                result.no_trade_count += 1
            continue

        # Risk approval
        trade_params = approve_trade(
            symbol=symbol,
            direction=rule_result.final_signal,
            entry_price=float(row["close"]),
            atr=float(row.get("atr", 0.001)),
            params=risk_params,
        )

        if not trade_params.approved:
            result.blocked_count += 1
            continue

        # Open trade
        open_trade = BacktestTrade(
            bar_index=i,
            timestamp=str(row["timestamp"]),
            direction=rule_result.final_signal,
            entry_price=trade_params.entry_price,
            sl_price=trade_params.sl_price,
            tp_price=trade_params.tp_price,
            lot_size=trade_params.lot_size,
            sl_pips=trade_params.sl_pips,
            tp_pips=trade_params.tp_pips,
            risk_amount=trade_params.risk_amount,
        )
        trades_today += 1
        log.debug("Trade opened: {} @ {:.5f}", rule_result.final_signal, trade_params.entry_price)

    # Close any open trade at end of data
    if open_trade and not open_trade.exit_reason:
        last_close = df_test.iloc[-1]["close"]
        open_trade.exit_price = last_close
        open_trade.exit_reason = "END"
        diff = last_close - open_trade.entry_price
        if open_trade.direction == "SELL":
            diff = -diff
        open_trade.pips = price_to_pips(abs(diff), symbol) * (1 if diff > 0 else -1)
        open_trade.pnl = round(open_trade.pips * open_trade.lot_size * 10.0, 2)
        balance += open_trade.pnl
        equity_curve.append(balance)
        trade_log.append(open_trade.to_dict())

    result.final_balance = round(balance, 2)
    result.equity_curve = [round(v, 2) for v in equity_curve]
    result.trade_log = trade_log

    result = _compute_metrics(result)

    log.info(
        "Backtest complete: {} trades | {:.0f}% win | PF {:.2f} | DD {:.1f}% | Balance ${:.2f}",
        result.total_trades, result.win_rate, result.profit_factor,
        result.max_drawdown_pct, result.final_balance,
    )
    return result


def save_backtest_result(result: BacktestResult, path: Optional[Path] = None) -> Path:
    path = path or (settings.BACKTEST_DIR / f"backtest_{result.symbol}_{result.timeframe}.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(result.to_dict(), f, indent=2, default=str)
    log.info("Backtest result saved to {}", path)
    return path
