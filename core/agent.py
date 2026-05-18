"""
Module 10 — AI Analysis Agent
Orchestrates the full 16-step analysis cycle end-to-end.
One call to run_cycle() produces a complete SignalOutput.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Optional, Dict, Any

import pandas as pd

from config import settings
from core.data_loader import get_candles
from core.feature_engineering import build_features
from core.market_structure import analyse_structure
from core.ml_predictor import predict as ml_predict, train_models, models_exist
from core.rule_engine import evaluate as rule_evaluate
from core.risk_manager import approve_trade, RiskParams, get_tracker
from core.calendar_news import check_news_risk, _load_csv_calendar
from core.paper_trader import get_paper_trader
from core.explainer import generate_explanation
from utils.logger import get_logger
from utils.helpers import now_utc

log = get_logger("agent")

DISCLAIMER = (
    "\n⚠️  This is not financial advice. "
    "This is a probabilistic signal generated for educational "
    "and decision-support purposes only."
)


# ─────────────────────────────────────────────────────────────────────────────
# Output dataclass
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class SignalOutput:
    timestamp: str
    symbol: str
    timeframe: str

    # Final decision
    signal: str = "NO_TRADE"
    confidence: float = 0.0
    explanation: str = ""

    # ML layer
    ml_signal: str = ""
    ml_confidence: float = 0.0
    ml_probabilities: Dict[str, float] = field(default_factory=dict)
    ml_model_used: str = ""

    # Market data
    price: float = 0.0
    atr: float = 0.0
    atr_pips: float = 0.0
    rsi: float = 0.0
    macd_hist: float = 0.0
    ema_trend: str = ""
    spread: float = 0.0

    # Structure
    structure_label: str = ""
    bos: str = ""
    swing_high: Optional[float] = None
    swing_low: Optional[float] = None
    volatility_regime: str = ""

    # Rule engine
    blocks: list = field(default_factory=list)
    supports: list = field(default_factory=list)

    # Risk / trade params
    entry_price: float = 0.0
    sl_price: float = 0.0
    tp_price: float = 0.0
    lot_size: float = 0.0
    sl_pips: float = 0.0
    tp_pips: float = 0.0
    risk_amount: float = 0.0
    risk_reward: float = 0.0

    # News
    news_blocked: bool = False
    news_reason: str = ""
    news_sentiment: float = 0.0

    # Paper trade
    paper_trade_id: Optional[int] = None
    paper_trade_opened: bool = False

    # Risk state
    trades_today: int = 0
    daily_loss_pct: float = 0.0

    # Status
    error: str = ""
    source: str = "agent"

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), default=str, indent=2)


# ─────────────────────────────────────────────────────────────────────────────
# Cycle
# ─────────────────────────────────────────────────────────────────────────────

def run_cycle(
    symbol: str = None,
    timeframe: str = None,
    n_bars: int = None,
    risk_params: Optional[RiskParams] = None,
    force_retrain: bool = False,
    paper_mode: bool = None,
    demo_mode: bool = False,   # always disabled by default
) -> SignalOutput:
    """
    Full 16-step analysis cycle:
    1.  Fetch latest candles
    2.  Clean data
    3.  Generate features
    4.  Detect market structure
    5.  Run ML prediction
    6.  Check economic calendar
    7.  Check news sentiment
    8.  Apply rule engine
    9.  Run risk engine
    10. Calculate lot size, SL, TP
    11. Generate final signal
    12. Save signal
    13. Update dashboard (via shared state)
    14. Explain result in simple English
    15. If paper mode enabled, send to paper trading
    16. Demo mode is always OFF unless explicitly enabled + approved
    """
    symbol = symbol or settings.DEFAULT_SYMBOL
    timeframe = timeframe or settings.DEFAULT_TIMEFRAME
    n_bars = n_bars or settings.CANDLES_LOOKBACK
    paper_mode = paper_mode if paper_mode is not None else settings.PAPER_ENABLED

    output = SignalOutput(
        timestamp=now_utc().isoformat(),
        symbol=symbol,
        timeframe=timeframe,
    )

    # Safety: demo mode guard
    if demo_mode and (not settings.DEMO_TRADING_ENABLED or settings.REQUIRE_MANUAL_APPROVAL):
        log.warning("Demo auto-trading blocked — DEMO_TRADING_ENABLED=False or requires manual approval")
        demo_mode = False

    # ── Step 1 & 2: Fetch + clean ─────────────────────────────────────────
    log.info("=== Agent cycle: {} {} ===", symbol, timeframe)
    df_raw = get_candles(symbol, timeframe, n_bars)

    if df_raw.empty or len(df_raw) < settings.MIN_CANDLES_REQUIRED:
        output.error = f"Insufficient data: {len(df_raw)} bars"
        log.error(output.error)
        return output

    # ── Step 3: Feature engineering ───────────────────────────────────────
    df = build_features(df_raw, symbol)
    if df.empty:
        output.error = "Feature engineering returned empty DataFrame"
        return output

    last = df.iloc[-1]
    output.price = float(last.get("close", 0))
    output.atr = float(last.get("atr", 0))
    output.rsi = float(last.get("rsi", 50))
    output.macd_hist = float(last.get("macd_hist", 0))
    output.ema_trend = str(last.get("ema_trend", "neutral"))
    output.spread = float(last.get("spread", 0))

    from utils.helpers import price_to_pips
    output.atr_pips = round(price_to_pips(output.atr, symbol), 1)

    # ── Step 4: Market structure ──────────────────────────────────────────
    ms = analyse_structure(df, symbol)
    output.structure_label = ms.structure_label
    output.bos = ms.bos
    output.swing_high = ms.last_swing_high
    output.swing_low = ms.last_swing_low
    output.volatility_regime = ms.volatility_regime

    # ── Step 5: ML prediction ─────────────────────────────────────────────
    if force_retrain or not models_exist(symbol, timeframe):
        log.info("Training models for {} {}...", symbol, timeframe)
        train_models(df, symbol, timeframe)

    ml_result = ml_predict(df, symbol, timeframe)
    output.ml_signal = ml_result.signal
    output.ml_confidence = round(ml_result.confidence, 4)
    output.ml_probabilities = ml_result.probabilities or {}
    output.ml_model_used = ml_result.model_used

    # ── Steps 6 & 7: News ────────────────────────────────────────────────
    news_events = _load_csv_calendar()
    ts = pd.Timestamp(last["timestamp"])
    if ts.tzinfo is None:
        import pytz; ts = ts.replace(tzinfo=pytz.utc)
    news_check = check_news_risk(symbol, ts.to_pydatetime(), news_events)
    output.news_blocked = news_check.blocked
    output.news_reason = news_check.reason
    output.news_sentiment = news_check.sentiment_score

    # ── Steps 8 & 9: Rule engine ─────────────────────────────────────────
    tracker = get_tracker(symbol)
    tracker.reset_daily()
    risk_state = tracker.to_dict()
    output.trades_today = risk_state["trades_today"]
    output.daily_loss_pct = risk_state["daily_loss_pct"]

    rule_result = rule_evaluate(
        ml_signal=ml_result.signal,
        ml_confidence=ml_result.confidence,
        ml_probabilities=ml_result.probabilities or {},
        ema_trend=output.ema_trend,
        rsi=output.rsi,
        macd_hist=output.macd_hist,
        atr=output.atr,
        spread=output.spread,
        symbol=symbol,
        structure_label=ms.structure_label,
        bos=ms.bos,
        news_blocked=news_check.blocked,
        news_reason=news_check.reason,
        daily_loss_pct=output.daily_loss_pct,
        trades_today=output.trades_today,
        open_trades=len([]),   # will come from DB in full version
    )

    output.blocks = rule_result.blocks
    output.supports = rule_result.supports
    output.signal = rule_result.final_signal
    output.confidence = round(rule_result.final_confidence, 4)

    # ── Steps 10 & 11: Risk engine / trade params ─────────────────────────
    rp = risk_params or RiskParams()
    trade_params = None

    if rule_result.final_signal in ("BUY", "SELL"):
        trade_params = approve_trade(
            symbol=symbol,
            direction=rule_result.final_signal,
            entry_price=output.price,
            atr=output.atr,
            params=rp,
            tracker=tracker,
        )

        if not trade_params.approved:
            if output.signal not in ("HOLD", "NO_TRADE"):
                output.signal = "NO_TRADE"
                output.blocks.append(f"risk_rejected({trade_params.rejection_reason})")
        else:
            output.entry_price = trade_params.entry_price
            output.sl_price = trade_params.sl_price
            output.tp_price = trade_params.tp_price
            output.lot_size = trade_params.lot_size
            output.sl_pips = trade_params.sl_pips
            output.tp_pips = trade_params.tp_pips
            output.risk_amount = trade_params.risk_amount
            output.risk_reward = trade_params.risk_reward

    # ── Step 12: Save signal ──────────────────────────────────────────────
    _save_signal(output)

    # ── Step 14: LLM explanation ─────────────────────────────────────────
    output.explanation = generate_explanation(output.to_dict()) + DISCLAIMER

    # ── Step 15: Paper trading ────────────────────────────────────────────
    if paper_mode and output.signal in ("BUY", "SELL") and trade_params and trade_params.approved:
        paper = get_paper_trader(symbol, rp.balance)
        pos = paper.open_trade(
            direction=output.signal,
            entry_price=output.entry_price,
            sl_price=output.sl_price,
            tp_price=output.tp_price,
            lot_size=output.lot_size,
            sl_pips=output.sl_pips,
            tp_pips=output.tp_pips,
            risk_amount=output.risk_amount,
        )
        if pos:
            output.paper_trade_id = pos.id
            output.paper_trade_opened = True
            tracker.record_trade_opened()

    log.info("Cycle done: {} {} ({:.0%}) | Paper: {}",
             output.signal, symbol, output.confidence, output.paper_trade_opened)
    return output


# ─────────────────────────────────────────────────────────────────────────────
# Signal persistence
# ─────────────────────────────────────────────────────────────────────────────

def _save_signal(output: SignalOutput):
    import csv
    path = settings.SIGNALS_DIR / f"signals_{output.symbol}.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    row = {
        "timestamp": output.timestamp,
        "symbol": output.symbol,
        "timeframe": output.timeframe,
        "signal": output.signal,
        "confidence": output.confidence,
        "ml_signal": output.ml_signal,
        "ml_confidence": output.ml_confidence,
        "price": output.price,
        "sl_price": output.sl_price,
        "tp_price": output.tp_price,
        "sl_pips": output.sl_pips,
        "tp_pips": output.tp_pips,
        "lot_size": output.lot_size,
        "rr": output.risk_reward,
        "risk_amount": output.risk_amount,
        "atr_pips": output.atr_pips,
        "rsi": output.rsi,
        "ema_trend": output.ema_trend,
        "structure": output.structure_label,
        "news_blocked": output.news_blocked,
        "blocks": "|".join(output.blocks),
    }
    file_exists = path.exists()
    with open(path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=row.keys())
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)
