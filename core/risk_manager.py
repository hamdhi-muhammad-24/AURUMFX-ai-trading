"""
Module 6 — Risk Management
Lot size calculation, SL/TP, margin check, daily limits, kill switch.
No martingale, no over-leverage, no revenge trading.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import date
from typing import Optional

from config import settings, get_pip_size, get_lot_usd_per_pip
from utils.logger import get_logger
from utils.helpers import clamp, price_to_pips, pips_to_price, round_price

log = get_logger("risk_manager")


# ─────────────────────────────────────────────────────────────────────────────
# Data classes
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class RiskParams:
    balance: float = settings.DEFAULT_BALANCE
    risk_pct: float = settings.RISK_PER_TRADE_PCT
    max_daily_loss_pct: float = settings.MAX_DAILY_LOSS_PCT
    max_open_trades: int = settings.MAX_OPEN_TRADES
    max_trades_per_day: int = settings.MAX_TRADES_PER_DAY
    min_risk_reward: float = settings.MIN_RISK_REWARD
    leverage: float = settings.DEFAULT_LEVERAGE
    sl_atr_mult: float = settings.SL_ATR_MULT
    tp_atr_mult: float = settings.TP_ATR_MULT
    kill_switch: bool = False


@dataclass
class TradeParameters:
    symbol: str
    direction: str        # BUY | SELL
    entry_price: float
    sl_price: float
    tp_price: float
    lot_size: float
    sl_pips: float
    tp_pips: float
    risk_amount: float
    risk_reward: float
    margin_required: float
    approved: bool = True
    rejection_reason: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


# ─────────────────────────────────────────────────────────────────────────────
# Core calculations
# ─────────────────────────────────────────────────────────────────────────────

def calculate_lot_size(
    symbol: str,
    balance: float,
    risk_pct: float,
    sl_pips: float,
) -> float:
    """
    lot_size = (balance × risk_pct/100) / (sl_pips × pip_value_per_lot)
    For standard lots: 1 lot = $10 per pip for most majors.
    """
    risk_amount = balance * (risk_pct / 100.0)
    pip_value = get_lot_usd_per_pip(symbol)
    if sl_pips <= 0 or pip_value <= 0:
        return 0.01
    lot = risk_amount / (sl_pips * pip_value)
    # Clamp to sensible retail range
    lot = clamp(round(lot, 2), 0.01, 100.0)
    return lot


def calculate_sl_tp(
    symbol: str,
    direction: str,
    entry_price: float,
    atr: float,
    sl_atr_mult: float = None,
    tp_atr_mult: float = None,
) -> tuple[float, float]:
    """Returns (sl_price, tp_price)."""
    sl_atr_mult = sl_atr_mult or settings.SL_ATR_MULT
    tp_atr_mult = tp_atr_mult or settings.TP_ATR_MULT

    sl_dist = atr * sl_atr_mult
    tp_dist = atr * tp_atr_mult

    if direction == "BUY":
        sl_price = entry_price - sl_dist
        tp_price = entry_price + tp_dist
    else:  # SELL
        sl_price = entry_price + sl_dist
        tp_price = entry_price - tp_dist

    return round_price(sl_price, symbol), round_price(tp_price, symbol)


def calculate_margin(lot_size: float, price: float, leverage: float) -> float:
    """margin = (lot_size × 100_000 × price) / leverage"""
    return (lot_size * 100_000 * price) / leverage


# ─────────────────────────────────────────────────────────────────────────────
# State tracker (in-memory, synced with DB by agent)
# ─────────────────────────────────────────────────────────────────────────────

class RiskStateTracker:
    """Lightweight in-memory risk state — not thread-safe; use per-symbol."""

    def __init__(self, symbol: str, balance: float = None):
        self.symbol = symbol
        self.balance = balance or settings.DEFAULT_BALANCE
        self._date = str(date.today())
        self._trades_today = 0
        self._daily_pnl = 0.0
        self._open_trades = 0
        self._kill_switch = settings.KILL_SWITCH

    def reset_daily(self):
        today = str(date.today())
        if today != self._date:
            self._date = today
            self._trades_today = 0
            self._daily_pnl = 0.0

    def record_trade_opened(self):
        self.reset_daily()
        self._trades_today += 1
        self._open_trades += 1

    def record_trade_closed(self, pnl: float):
        self.reset_daily()
        self._daily_pnl += pnl
        self._open_trades = max(0, self._open_trades - 1)

    def daily_loss_pct(self) -> float:
        if self._daily_pnl >= 0:
            return 0.0
        return abs(self._daily_pnl) / self.balance * 100.0

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "date": self._date,
            "trades_today": self._trades_today,
            "daily_pnl": self._daily_pnl,
            "open_trades": self._open_trades,
            "daily_loss_pct": self.daily_loss_pct(),
            "kill_switch": self._kill_switch,
        }


# Global trackers keyed by symbol
_trackers: dict[str, RiskStateTracker] = {}


def get_tracker(symbol: str, balance: float = None) -> RiskStateTracker:
    if symbol not in _trackers:
        _trackers[symbol] = RiskStateTracker(symbol, balance)
    return _trackers[symbol]


# ─────────────────────────────────────────────────────────────────────────────
# Master approval function
# ─────────────────────────────────────────────────────────────────────────────

def approve_trade(
    symbol: str,
    direction: str,
    entry_price: float,
    atr: float,
    params: Optional[RiskParams] = None,
    tracker: Optional[RiskStateTracker] = None,
) -> TradeParameters:
    """
    Full risk approval:
    1. Calculate SL/TP
    2. Calculate lot size
    3. Check margin
    4. Check daily limits
    5. Return TradeParameters with approved flag
    """
    params = params or RiskParams()
    tracker = tracker or get_tracker(symbol, params.balance)
    tracker.reset_daily()

    # Kill switch
    if params.kill_switch or settings.KILL_SWITCH or tracker._kill_switch:
        return TradeParameters(
            symbol=symbol, direction=direction,
            entry_price=entry_price, sl_price=0, tp_price=0,
            lot_size=0, sl_pips=0, tp_pips=0,
            risk_amount=0, risk_reward=0, margin_required=0,
            approved=False, rejection_reason="kill_switch_active",
        )

    # SL / TP
    sl_price, tp_price = calculate_sl_tp(
        symbol, direction, entry_price, atr,
        params.sl_atr_mult, params.tp_atr_mult,
    )
    sl_pips = price_to_pips(abs(entry_price - sl_price), symbol)
    tp_pips = price_to_pips(abs(entry_price - tp_price), symbol)

    if sl_pips <= 0:
        return TradeParameters(
            symbol=symbol, direction=direction,
            entry_price=entry_price, sl_price=sl_price, tp_price=tp_price,
            lot_size=0, sl_pips=0, tp_pips=0,
            risk_amount=0, risk_reward=0, margin_required=0,
            approved=False, rejection_reason="sl_pips_zero",
        )

    # RR check
    rr = tp_pips / sl_pips if sl_pips > 0 else 0
    if rr < params.min_risk_reward:
        return TradeParameters(
            symbol=symbol, direction=direction,
            entry_price=entry_price, sl_price=sl_price, tp_price=tp_price,
            lot_size=0, sl_pips=sl_pips, tp_pips=tp_pips,
            risk_amount=0, risk_reward=round(rr, 2), margin_required=0,
            approved=False, rejection_reason=f"rr_too_low({rr:.2f}<{params.min_risk_reward})",
        )

    # Lot size
    lot = calculate_lot_size(symbol, params.balance, params.risk_pct, sl_pips)
    risk_amount = lot * sl_pips * get_lot_usd_per_pip(symbol)

    # Daily loss check
    if tracker.daily_loss_pct() >= params.max_daily_loss_pct:
        return TradeParameters(
            symbol=symbol, direction=direction,
            entry_price=entry_price, sl_price=sl_price, tp_price=tp_price,
            lot_size=lot, sl_pips=sl_pips, tp_pips=tp_pips,
            risk_amount=risk_amount, risk_reward=round(rr, 2), margin_required=0,
            approved=False, rejection_reason="daily_loss_limit_reached",
        )

    # Trade count
    if tracker._trades_today >= params.max_trades_per_day:
        return TradeParameters(
            symbol=symbol, direction=direction,
            entry_price=entry_price, sl_price=sl_price, tp_price=tp_price,
            lot_size=lot, sl_pips=sl_pips, tp_pips=tp_pips,
            risk_amount=risk_amount, risk_reward=round(rr, 2), margin_required=0,
            approved=False, rejection_reason="max_trades_per_day_reached",
        )

    if tracker._open_trades >= params.max_open_trades:
        return TradeParameters(
            symbol=symbol, direction=direction,
            entry_price=entry_price, sl_price=sl_price, tp_price=tp_price,
            lot_size=lot, sl_pips=sl_pips, tp_pips=tp_pips,
            risk_amount=risk_amount, risk_reward=round(rr, 2), margin_required=0,
            approved=False, rejection_reason="max_open_trades_reached",
        )

    # Margin
    margin = calculate_margin(lot, entry_price, params.leverage)
    if margin > params.balance * 0.5:
        return TradeParameters(
            symbol=symbol, direction=direction,
            entry_price=entry_price, sl_price=sl_price, tp_price=tp_price,
            lot_size=lot, sl_pips=sl_pips, tp_pips=tp_pips,
            risk_amount=risk_amount, risk_reward=round(rr, 2), margin_required=margin,
            approved=False, rejection_reason="insufficient_margin",
        )

    log.info(
        "Trade approved: {} {} @ {:.5f} | SL {:.5f} | TP {:.5f} | Lot {:.2f} | Risk ${:.2f} | RR {:.2f}",
        direction, symbol, entry_price, sl_price, tp_price, lot, risk_amount, rr,
    )

    return TradeParameters(
        symbol=symbol, direction=direction,
        entry_price=entry_price, sl_price=sl_price, tp_price=tp_price,
        lot_size=lot, sl_pips=sl_pips, tp_pips=tp_pips,
        risk_amount=round(risk_amount, 2), risk_reward=round(rr, 2),
        margin_required=round(margin, 2),
        approved=True,
    )
