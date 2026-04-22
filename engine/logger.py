"""
engine/logger.py
════════════════════════════════════════════════════════
ROLE: Records every trade event to:
  1. Console (with timestamps)
  2. trade_log.csv (permanent record you can open in Excel)

Every SL hit, TP hit, cycle start/end is logged here.
════════════════════════════════════════════════════════
"""

import csv
import logging
import os
from datetime import datetime

LOG_FILE  = "trade_log.csv"
CSV_FIELDS = [
    "timestamp", "event", "symbol", "direction",
    "level", "lots", "entry", "sl", "tp",
    "profit_usd", "total_loss_usd", "net_usd", "notes"
]

# Console logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("bot.log"),
    ]
)
log = logging.getLogger("MartingaleBot")


class TradeLogger:
    def __init__(self, log_file: str = LOG_FILE):
        self.log_file = log_file
        self._init_csv()

    def _init_csv(self):
        """Create CSV with headers if it doesn't exist."""
        if not os.path.exists(self.log_file):
            with open(self.log_file, "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
                writer.writeheader()

    def _write_row(self, **kwargs):
        kwargs["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # Fill missing fields with empty string
        row = {field: kwargs.get(field, "") for field in CSV_FIELDS}
        with open(self.log_file, "a", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
            writer.writerow(row)

    # ─── PUBLIC LOGGING METHODS ─────────────────────────────────────

    def log_cycle_start(self, symbol: str, direction: str):
        msg = f"🚀 NEW CYCLE: {direction} {symbol}"
        log.info(msg)
        self._write_row(event="CYCLE_START", symbol=symbol,
                        direction=direction, notes=msg)

    def log_trade_opened(self, symbol: str, direction: str,
                         level: int, lots: float,
                         entry: float, sl: float, tp: float):
        msg = (f"📈 TRADE OPEN | {direction} {symbol} | Level {level} | "
               f"Lots {lots} | Entry {entry:.5f} | SL {sl:.5f} | TP {tp:.5f}")
        log.info(msg)
        self._write_row(event="OPEN", symbol=symbol, direction=direction,
                        level=level, lots=lots, entry=entry, sl=sl, tp=tp)

    def log_sl_hit(self, symbol: str, direction: str,
                   level: int, loss: float, total_loss: float):
        msg = (f"🔴 SL HIT | {direction} {symbol} | Level {level} | "
               f"Loss ${loss:.2f} | Total loss ${total_loss:.2f}")
        log.warning(msg)
        self._write_row(event="SL_HIT", symbol=symbol, direction=direction,
                        level=level, profit_usd=loss, total_loss_usd=total_loss)

    def log_tp_hit(self, symbol: str, direction: str, level: int,
                   profit: float, total_loss: float, net: float):
        msg = (f"🟢 TP HIT | {direction} {symbol} | Level {level} | "
               f"Profit ${profit:.2f} | Net ${net:.2f}")
        log.info(msg)
        self._write_row(event="TP_HIT", symbol=symbol, direction=direction,
                        level=level, profit_usd=profit,
                        total_loss_usd=total_loss, net_usd=net)

    def log_max_level(self, symbol: str, level: int, total_loss: float):
        msg = (f"🚨 MAX LEVEL REACHED | {symbol} | Level {level} | "
               f"Total loss ${total_loss:.2f} | CYCLE STOPPED")
        log.error(msg)
        self._write_row(event="MAX_LEVEL", symbol=symbol, level=level,
                        total_loss_usd=total_loss, notes=msg)

    def log_stop(self, reason: str = "Manual STOP"):
        log.info(f"⛔ STOPPED: {reason}")
        self._write_row(event="STOP", notes=reason)

    def info(self, msg: str):
        log.info(msg)

    def error(self, msg: str):
        log.error(msg)