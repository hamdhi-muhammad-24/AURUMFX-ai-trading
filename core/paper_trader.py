"""
Module 9 — Paper Trading
Virtual balance, open/close trades by SL/TP or opposite signal.
Full P/L tracking, equity curve, journal export.
"""
from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Dict

from config import settings
from utils.logger import get_logger
from utils.helpers import price_to_pips, now_utc

log = get_logger("paper_trader")

USD_PER_PIP_PER_LOT = 10.0   # standard lot approximation


# ─────────────────────────────────────────────────────────────────────────────
# Data classes
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class PaperPosition:
    id: int
    symbol: str
    direction: str         # BUY | SELL
    entry_price: float
    sl_price: float
    tp_price: float
    lot_size: float
    sl_pips: float
    tp_pips: float
    risk_amount: float
    opened_at: str
    signal_id: Optional[int] = None
    exit_price: float = 0.0
    exit_reason: str = ""
    pnl: float = 0.0
    pips: float = 0.0
    closed_at: str = ""
    status: str = "open"

    def to_dict(self) -> dict:
        return asdict(self)

    def current_pnl(self, current_price: float) -> float:
        """Unrealised P/L at current_price."""
        diff = current_price - self.entry_price
        if self.direction == "SELL":
            diff = -diff
        pips = price_to_pips(abs(diff), self.symbol) * (1 if diff > 0 else -1)
        return round(pips * self.lot_size * USD_PER_PIP_PER_LOT, 2)


@dataclass
class PaperAccount:
    balance: float
    equity: float
    open_pnl: float = 0.0
    closed_pnl: float = 0.0
    trades_opened: int = 0
    trades_closed: int = 0
    win_count: int = 0
    loss_count: int = 0

    @property
    def win_rate(self) -> float:
        total = self.win_count + self.loss_count
        return self.win_count / total * 100 if total > 0 else 0.0

    def to_dict(self) -> dict:
        return {
            "balance": round(self.balance, 2),
            "equity": round(self.equity, 2),
            "open_pnl": round(self.open_pnl, 2),
            "closed_pnl": round(self.closed_pnl, 2),
            "trades_opened": self.trades_opened,
            "trades_closed": self.trades_closed,
            "win_rate": round(self.win_rate, 1),
        }


# ─────────────────────────────────────────────────────────────────────────────
# Paper trader engine
# ─────────────────────────────────────────────────────────────────────────────

class PaperTrader:
    """
    Manages virtual open/closed positions.
    Thread-safe only for single-symbol usage; for multi-symbol run separate instances.
    """

    def __init__(self, initial_balance: float = None, symbol: str = "EURUSD"):
        self.symbol = symbol
        self.initial_balance = initial_balance or settings.PAPER_BALANCE
        self.balance = self.initial_balance
        self.open_positions: Dict[int, PaperPosition] = {}
        self.closed_positions: List[PaperPosition] = []
        self.equity_curve: List[float] = [self.balance]
        self._next_id = 1

    # ── Open ─────────────────────────────────────────────────────────────────

    def open_trade(
        self,
        direction: str,
        entry_price: float,
        sl_price: float,
        tp_price: float,
        lot_size: float,
        sl_pips: float,
        tp_pips: float,
        risk_amount: float,
        signal_id: Optional[int] = None,
    ) -> Optional[PaperPosition]:
        if direction not in ("BUY", "SELL"):
            log.error("Invalid direction: {}", direction)
            return None
        if not settings.PAPER_ENABLED:
            log.warning("Paper trading is disabled")
            return None

        pos = PaperPosition(
            id=self._next_id,
            symbol=self.symbol,
            direction=direction,
            entry_price=entry_price,
            sl_price=sl_price,
            tp_price=tp_price,
            lot_size=lot_size,
            sl_pips=sl_pips,
            tp_pips=tp_pips,
            risk_amount=risk_amount,
            opened_at=now_utc().isoformat(),
            signal_id=signal_id,
        )
        self.open_positions[self._next_id] = pos
        self._next_id += 1

        log.info("Paper OPEN #{} {} {} @ {:.5f} | SL {:.5f} | TP {:.5f} | Lot {}",
                 pos.id, direction, self.symbol, entry_price, sl_price, tp_price, lot_size)
        return pos

    # ── Check prices on each bar ──────────────────────────────────────────────

    def update(self, high: float, low: float, close: float):
        """Call once per new bar to check for SL/TP hits and update equity."""
        newly_closed = []
        for pos_id, pos in list(self.open_positions.items()):
            if pos.direction == "BUY":
                if low <= pos.sl_price:
                    self._close(pos, pos.sl_price, "SL")
                    newly_closed.append(pos_id)
                elif high >= pos.tp_price:
                    self._close(pos, pos.tp_price, "TP")
                    newly_closed.append(pos_id)
            else:
                if high >= pos.sl_price:
                    self._close(pos, pos.sl_price, "SL")
                    newly_closed.append(pos_id)
                elif low <= pos.tp_price:
                    self._close(pos, pos.tp_price, "TP")
                    newly_closed.append(pos_id)

        for pid in newly_closed:
            del self.open_positions[pid]

        # Update equity
        open_pnl = sum(p.current_pnl(close) for p in self.open_positions.values())
        self.equity_curve.append(round(self.balance + open_pnl, 2))

    def _close(self, pos: PaperPosition, exit_price: float, reason: str):
        diff = exit_price - pos.entry_price
        if pos.direction == "SELL":
            diff = -diff
        pips = price_to_pips(abs(diff), pos.symbol) * (1 if diff > 0 else -1)
        pnl = round(pips * pos.lot_size * USD_PER_PIP_PER_LOT, 2)

        pos.exit_price = exit_price
        pos.exit_reason = reason
        pos.pnl = pnl
        pos.pips = round(pips, 1)
        pos.closed_at = now_utc().isoformat()
        pos.status = "closed"

        self.balance += pnl
        self.closed_positions.append(pos)

        log.info("Paper CLOSE #{} {} pips | PnL ${:.2f} | Balance ${:.2f}",
                 pos.id, round(pips, 1), pnl, self.balance)

    def close_by_signal(self, opposite_signal: str, close_price: float):
        """Close all open positions on opposite signal."""
        for pos_id, pos in list(self.open_positions.items()):
            if (opposite_signal == "SELL" and pos.direction == "BUY") or \
               (opposite_signal == "BUY" and pos.direction == "SELL"):
                self._close(pos, close_price, "SIGNAL")
                del self.open_positions[pos_id]

    def close_all(self, close_price: float):
        for pos_id, pos in list(self.open_positions.items()):
            self._close(pos, close_price, "MANUAL")
        self.open_positions.clear()

    # ── Account summary ───────────────────────────────────────────────────────

    def get_account(self, current_price: float = 0.0) -> PaperAccount:
        open_pnl = sum(p.current_pnl(current_price) for p in self.open_positions.values())
        closed_pnl = sum(p.pnl for p in self.closed_positions)
        wins = sum(1 for p in self.closed_positions if p.pnl > 0)
        losses = sum(1 for p in self.closed_positions if p.pnl <= 0)
        return PaperAccount(
            balance=self.balance,
            equity=self.balance + open_pnl,
            open_pnl=open_pnl,
            closed_pnl=closed_pnl,
            trades_opened=len(self.closed_positions) + len(self.open_positions),
            trades_closed=len(self.closed_positions),
            win_count=wins,
            loss_count=losses,
        )

    # ── Persistence ───────────────────────────────────────────────────────────

    def export_journal(self) -> Path:
        path = settings.PAPER_DIR / f"paper_journal_{self.symbol}.csv"
        path.parent.mkdir(parents=True, exist_ok=True)
        all_trades = [p.to_dict() for p in self.closed_positions]
        if not all_trades:
            log.info("No closed trades to export")
            return path
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=all_trades[0].keys())
            writer.writeheader()
            writer.writerows(all_trades)
        log.info("Journal exported: {} trades → {}", len(all_trades), path)
        return path

    def save_state(self) -> Path:
        path = settings.PAPER_DIR / f"paper_state_{self.symbol}.json"
        state = {
            "symbol": self.symbol,
            "balance": self.balance,
            "initial_balance": self.initial_balance,
            "open_positions": [p.to_dict() for p in self.open_positions.values()],
            "closed_count": len(self.closed_positions),
            "equity_curve": self.equity_curve[-100:],  # last 100 points
        }
        with open(path, "w") as f:
            json.dump(state, f, indent=2, default=str)
        return path


# Singleton per symbol
_paper_traders: Dict[str, PaperTrader] = {}


def get_paper_trader(symbol: str, balance: float = None) -> PaperTrader:
    if symbol not in _paper_traders:
        _paper_traders[symbol] = PaperTrader(balance, symbol)
    return _paper_traders[symbol]
