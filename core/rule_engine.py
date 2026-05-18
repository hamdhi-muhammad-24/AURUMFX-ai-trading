"""
Module 5 — Rule-Based Decision Engine
Combines ML signal with filter layers: trend, RSI, MACD, ATR, spread,
news, structure, and risk gates.  ML never decides alone.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import List, Optional

from config import settings
from utils.logger import get_logger
from utils.helpers import price_to_pips

log = get_logger("rule_engine")

FINAL_SIGNALS = {"BUY", "SELL", "HOLD", "NO_TRADE"}


# ─────────────────────────────────────────────────────────────────────────────
# Result dataclass
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class RuleResult:
    final_signal: str = "NO_TRADE"
    final_confidence: float = 0.0
    ml_signal: str = ""
    ml_confidence: float = 0.0
    blocks: List[str] = field(default_factory=list)
    supports: List[str] = field(default_factory=list)
    ema_trend: str = ""
    rsi_value: float = 0.0
    macd_value: float = 0.0
    atr_pips: float = 0.0
    spread_pips: float = 0.0
    structure_label: str = ""
    news_blocked: bool = False
    risk_blocked: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


# ─────────────────────────────────────────────────────────────────────────────
# Individual filter functions
# ─────────────────────────────────────────────────────────────────────────────

def _check_confidence(signal: str, confidence: float) -> tuple[bool, str]:
    if confidence < settings.MIN_CONFIDENCE:
        return False, f"confidence_too_low({confidence:.0%})"
    return True, ""


def _check_spread(spread_pips: float) -> tuple[bool, str]:
    if spread_pips > settings.MAX_SPREAD_PIPS:
        return False, f"spread_too_high({spread_pips:.1f}pips)"
    return True, ""


def _check_ema_trend(signal: str, ema_trend: str) -> tuple[bool, str, str]:
    """Returns (pass, block_reason, support_reason)."""
    if signal == "BUY" and ema_trend == "down":
        return False, "ema_trend_conflict(down_vs_buy)", ""
    if signal == "SELL" and ema_trend == "up":
        return False, "ema_trend_conflict(up_vs_sell)", ""
    if (signal == "BUY" and ema_trend == "up") or (signal == "SELL" and ema_trend == "down"):
        return True, "", f"ema_trend_aligned({ema_trend})"
    return True, "", ""


def _check_rsi(signal: str, rsi: float) -> tuple[bool, str, str]:
    if signal == "BUY" and rsi > settings.RSI_OVERBOUGHT:
        return False, f"rsi_overbought({rsi:.1f})", ""
    if signal == "SELL" and rsi < settings.RSI_OVERSOLD:
        return False, f"rsi_oversold({rsi:.1f})", ""
    if signal == "BUY" and rsi < settings.RSI_NEUTRAL_HIGH:
        return True, "", f"rsi_not_overbought({rsi:.1f})"
    if signal == "SELL" and rsi > settings.RSI_NEUTRAL_LOW:
        return True, "", f"rsi_not_oversold({rsi:.1f})"
    return True, "", ""


def _check_macd(signal: str, macd_hist: float) -> tuple[bool, str, str]:
    if signal == "BUY" and macd_hist > 0:
        return True, "", "macd_bullish"
    if signal == "SELL" and macd_hist < 0:
        return True, "", "macd_bearish"
    if signal == "BUY" and macd_hist < 0:
        return False, "macd_conflict(bearish_hist_vs_buy)", ""
    if signal == "SELL" and macd_hist > 0:
        return False, "macd_conflict(bullish_hist_vs_sell)", ""
    return True, "", ""


def _check_volatility(atr_pips: float, symbol: str) -> tuple[bool, str]:
    min_atr = settings.MIN_ATR_PIPS
    # Gold has much larger pip values — use a generous max
    max_atr = settings.MAX_ATR_PIPS if "XAU" not in symbol else 300.0
    if atr_pips < min_atr:
        return False, f"volatility_too_low({atr_pips:.1f}pips)"
    if atr_pips > max_atr:
        return False, f"volatility_too_high({atr_pips:.1f}pips)"
    return True, ""


def _check_structure(signal: str, structure_label: str, bos: str) -> tuple[bool, str, str]:
    if signal == "BUY" and structure_label == "bullish_trending":
        return True, "", "structure_bullish_trending"
    if signal == "SELL" and structure_label == "bearish_trending":
        return True, "", "structure_bearish_trending"
    if signal == "BUY" and structure_label == "bearish_trending":
        return False, "structure_conflict(bearish_structure_vs_buy)", ""
    if signal == "SELL" and structure_label == "bullish_trending":
        return False, "structure_conflict(bullish_structure_vs_sell)", ""
    if bos == "bullish" and signal == "BUY":
        return True, "", "bos_bullish_confirms_buy"
    if bos == "bearish" and signal == "SELL":
        return True, "", "bos_bearish_confirms_sell"
    return True, "", ""


def _check_risk_gate(
    daily_loss_pct: float,
    trades_today: int,
    open_trades: int,
) -> tuple[bool, str]:
    if daily_loss_pct >= settings.MAX_DAILY_LOSS_PCT:
        return False, f"daily_loss_limit_reached({daily_loss_pct:.1f}%)"
    if trades_today >= settings.MAX_TRADES_PER_DAY:
        return False, f"max_trades_per_day_reached({trades_today})"
    if open_trades >= settings.MAX_OPEN_TRADES:
        return False, f"max_open_trades_reached({open_trades})"
    return True, ""


# ─────────────────────────────────────────────────────────────────────────────
# Master rule engine
# ─────────────────────────────────────────────────────────────────────────────

def evaluate(
    ml_signal: str,
    ml_confidence: float,
    ml_probabilities: dict,
    # Market data
    ema_trend: str,
    rsi: float,
    macd_hist: float,
    atr: float,
    spread: float,
    symbol: str = "EURUSD",
    # Market structure
    structure_label: str = "neutral",
    bos: str = "none",
    # Calendar / news
    news_blocked: bool = False,
    news_reason: str = "",
    # Risk state
    daily_loss_pct: float = 0.0,
    trades_today: int = 0,
    open_trades: int = 0,
    # Kill switch
    kill_switch: bool = False,
) -> RuleResult:
    """
    Apply all rule filters.  Returns a RuleResult with final_signal
    and full audit trail of blocks/supports.
    """
    result = RuleResult(
        ml_signal=ml_signal,
        ml_confidence=ml_confidence,
        ema_trend=ema_trend,
        rsi_value=rsi,
        macd_value=macd_hist,
        atr_pips=price_to_pips(atr, symbol),
        spread_pips=spread,
        structure_label=structure_label,
    )

    # Hard abort
    if kill_switch or settings.KILL_SWITCH:
        result.blocks.append("kill_switch_active")
        result.final_signal = "NO_TRADE"
        return result

    if ml_signal not in ("BUY", "SELL", "HOLD"):
        result.blocks.append("invalid_ml_signal")
        result.final_signal = "NO_TRADE"
        return result

    if ml_signal == "HOLD":
        result.final_signal = "HOLD"
        result.final_confidence = ml_confidence
        return result

    # Confidence gate
    ok, reason = _check_confidence(ml_signal, ml_confidence)
    if not ok:
        result.blocks.append(reason)
        result.final_signal = "NO_TRADE"
        return result

    # News gate
    if news_blocked:
        result.blocks.append(f"news_blocked({news_reason})")
        result.news_blocked = True
        result.final_signal = "NO_TRADE"
        return result

    # Spread gate
    spread_pips = price_to_pips(spread, symbol) if spread < 1 else spread
    ok, reason = _check_spread(spread_pips)
    result.spread_pips = spread_pips
    if not ok:
        result.blocks.append(reason)
        result.final_signal = "NO_TRADE"
        return result

    # Risk gate
    ok, reason = _check_risk_gate(daily_loss_pct, trades_today, open_trades)
    if not ok:
        result.blocks.append(reason)
        result.risk_blocked = True
        result.final_signal = "NO_TRADE"
        return result

    # Volatility gate
    atr_pips = price_to_pips(atr, symbol)
    ok, reason = _check_volatility(atr_pips, symbol)
    if not ok:
        result.blocks.append(reason)
        result.final_signal = "NO_TRADE"
        return result

    # EMA trend filter
    ok, block, support = _check_ema_trend(ml_signal, ema_trend)
    if not ok:
        result.blocks.append(block)
    elif support:
        result.supports.append(support)

    # RSI filter
    ok, block, support = _check_rsi(ml_signal, rsi)
    if not ok:
        result.blocks.append(block)
    elif support:
        result.supports.append(support)

    # MACD filter
    ok, block, support = _check_macd(ml_signal, macd_hist)
    if not ok:
        result.blocks.append(block)
    elif support:
        result.supports.append(support)

    # Structure filter
    ok, block, support = _check_structure(ml_signal, structure_label, bos)
    if not ok:
        result.blocks.append(block)
    elif support:
        result.supports.append(support)

    # ── Determine final signal ────────────────────────────────────────────────
    # Confidence adjustment: reduce by 10% per blocking filter (soft blocks)
    adjusted_confidence = ml_confidence
    # Hard blocks already returned NO_TRADE; remaining blocks are soft
    adjusted_confidence -= len(result.blocks) * 0.08
    adjusted_confidence = max(0.0, min(1.0, adjusted_confidence))

    if result.blocks:
        # Multiple soft blocks → NO_TRADE
        if len(result.blocks) >= 2:
            result.blocks.append(f"multiple_soft_blocks({len(result.blocks)})")
            result.final_signal = "NO_TRADE"
            result.final_confidence = adjusted_confidence
        else:
            # Single soft block → reduce confidence, still pass if > threshold
            if adjusted_confidence >= settings.MIN_CONFIDENCE:
                result.final_signal = ml_signal
                result.final_confidence = adjusted_confidence
            else:
                result.final_signal = "NO_TRADE"
                result.final_confidence = adjusted_confidence
    else:
        result.final_signal = ml_signal
        result.final_confidence = adjusted_confidence

    log.info(
        "Rule engine: {} ({:.0%}) | blocks={} | supports={}",
        result.final_signal, result.final_confidence,
        result.blocks, result.supports,
    )
    return result
