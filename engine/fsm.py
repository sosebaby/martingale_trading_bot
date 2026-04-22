"""
engine/fsm.py
════════════════════════════════════════════════════════
ROLE: Finite State Machine — the "memory" and "brain"
      of the entire bot. Tracks exactly what state the
      cycle is in at every moment.

STATES:
  IDLE       → No active trade. Waiting for Telegram signal.
  PENDING    → Signal received. Waiting for MT5 to confirm open.
  IN_TRADE   → Position is open. Monitoring tick by tick.
  ESCALATING → SL was just hit. About to open next level.
  COMPLETE   → TP was hit. Logging profit. Returning to IDLE.

TRANSITIONS:
  IDLE ──[signal received]──▶ PENDING
  PENDING ──[MT5 confirms open]──▶ IN_TRADE
  IN_TRADE ──[SL hit]──▶ ESCALATING ──[reopened]──▶ IN_TRADE
  IN_TRADE ──[TP hit]──▶ COMPLETE ──[reset]──▶ IDLE
════════════════════════════════════════════════════════
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Optional


class State(Enum):
    IDLE       = "IDLE"
    PENDING    = "PENDING"
    IN_TRADE   = "IN_TRADE"
    ESCALATING = "ESCALATING"
    COMPLETE   = "COMPLETE"


@dataclass
class CycleData:
    """Everything we know about the current martingale cycle."""
    direction:     str   = ""
    symbol:        str   = ""
    level:         int   = 1
    ticket:        int   = 0
    entry_price:   float = 0.0
    total_loss:    float = 0.0   # Accumulated USD loss across all SL hits
    trades_count:  int   = 0     # How many trades opened this cycle


class MartingaleFSM:
    def __init__(self):
        self.state = State.IDLE
        self.cycle = CycleData()

    # ─── STATE TRANSITIONS ──────────────────────────────────────────

    def on_signal_received(self, direction: str, symbol: str):
        """Telegram sent a BUY or SELL signal."""
        assert self.state == State.IDLE, "Signal received while not IDLE!"
        self.cycle = CycleData(direction=direction, symbol=symbol, level=1)
        self.state = State.PENDING

    def on_trade_opened(self, ticket: int, entry_price: float):
        """MT5 confirmed the position is open."""
        assert self.state in (State.PENDING, State.ESCALATING)
        self.cycle.ticket      = ticket
        self.cycle.entry_price = entry_price
        self.cycle.trades_count += 1
        self.state = State.IN_TRADE

    def on_sl_hit(self, loss_usd: float):
        """Position closed at SL — escalate to next level."""
        assert self.state == State.IN_TRADE
        self.cycle.total_loss += abs(loss_usd)
        self.cycle.level      += 1
        self.cycle.ticket      = 0
        self.state = State.ESCALATING

    def on_tp_hit(self, profit_usd: float) -> dict:
        """Position closed at TP — cycle is done."""
        assert self.state == State.IN_TRADE
        self.state = State.COMPLETE
        result = {
            "direction":   self.cycle.direction,
            "symbol":      self.cycle.symbol,
            "levels_used": self.cycle.level,
            "trades":      self.cycle.trades_count,
            "total_loss":  self.cycle.total_loss,
            "final_profit":profit_usd,
            "net_gain":    profit_usd - self.cycle.total_loss,
        }
        self.reset()
        return result

    def on_stop_command(self):
        """Manual STOP from Telegram."""
        self.reset()

    def reset(self):
        self.state = State.IDLE
        self.cycle = CycleData()

    # ─── GETTERS ────────────────────────────────────────────────────

    def is_idle(self)      -> bool: return self.state == State.IDLE
    def is_in_trade(self)  -> bool: return self.state == State.IN_TRADE
    def is_escalating(self)-> bool: return self.state == State.ESCALATING

    def get_level(self)    -> int:  return self.cycle.level
    def get_ticket(self)   -> int:  return self.cycle.ticket
    def get_direction(self)-> str:  return self.cycle.direction
    def get_symbol(self)   -> str:  return self.cycle.symbol
    def get_total_loss(self)->float:return self.cycle.total_loss

    def status_str(self) -> str:
        if self.state == State.IDLE:
            return "IDLE — no active cycle."
        return (
            f"State: {self.state.value} | "
            f"{self.cycle.direction} {self.cycle.symbol} | "
            f"Level: {self.cycle.level} | "
            f"Ticket: {self.cycle.ticket} | "
            f"Total loss: ${self.cycle.total_loss:.2f}"
        )