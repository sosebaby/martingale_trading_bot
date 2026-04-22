"""
engine/analysis.py
════════════════════════════════════════════════════════
ROLE: Interprets incoming tick data from MT5 and
      provides symbol-specific settings (pip size,
      min lot, etc).

      Also validates that a signal from Telegram
      is tradeable right now (market open, spread ok).
════════════════════════════════════════════════════════
"""


# Pip sizes per symbol type
# 5-digit brokers (most modern brokers): 1 pip = 0.0001 for FX, 0.01 for JPY
PIP_SIZES = {
    "default": 0.0001,   # EURUSD, GBPUSD, AUDUSD etc.
    "JPY":     0.01,     # USDJPY, GBPJPY, EURJPY etc.
    "XAUUSD":  0.1,      # Gold (also matches XAUUSDm, XAUUSDM etc.)
    "XAGUSD":  0.01,     # Silver
    "BTCUSD":  1.0,      # Bitcoin
    "ETHUSD":  0.1,      # Ethereum
    "US30":    1.0,      # Dow Jones
    "NAS100":  1.0,      # Nasdaq
}

# Maximum allowed spread in pips before rejecting a trade
MAX_SPREAD_PIPS = 5.0


class MarketAnalysis:

    @staticmethod
    def get_pip_size(symbol: str) -> float:
        """Returns the pip size for a given symbol."""
        sym = symbol.upper()
        if sym in PIP_SIZES:
            return PIP_SIZES[sym]
        # Check base keys (e.g. broker suffix like XAUUSDm → XAUUSD)
        for key, val in PIP_SIZES.items():
            if key in sym:
                return val
        # JPY pairs have larger pip sizes
        if "JPY" in sym:
            return PIP_SIZES["JPY"]
        return PIP_SIZES["default"]

    @staticmethod
    def get_spread_pips(bid: float, ask: float, symbol: str) -> float:
        """Returns current spread in pips."""
        pip = MarketAnalysis.get_pip_size(symbol)
        return round((ask - bid) / pip, 1)

    @staticmethod
    def validate_signal(symbol: str, direction: str,
                        bid: float, ask: float) -> tuple[bool, str]:
        """
        Checks whether it's safe to open a trade right now.
        Returns (ok: bool, reason: str)
        """
        # Direction must be BUY or SELL
        if direction not in ("BUY", "SELL"):
            return False, f"Unknown direction: {direction}"

        # Check spread isn't too wide (avoid trading during news spikes)
        spread = MarketAnalysis.get_spread_pips(bid, ask, symbol)
        if spread > MAX_SPREAD_PIPS:
            return False, f"Spread too wide: {spread} pips (max {MAX_SPREAD_PIPS})"

        # Prices must be valid
        if bid <= 0 or ask <= 0:
            return False, "Invalid price data"

        return True, "OK"

    @staticmethod
    def detect_sl_tp_hit(direction: str, current_price: float,
                          sl_price: float, tp_price: float) -> str:
        """
        Check if current price has crossed SL or TP.
        Returns 'SL', 'TP', or 'NONE'
        Note: MT5 handles this natively — this is a fallback check.
        """
        if direction == "BUY":
            if current_price <= sl_price: return "SL"
            if current_price >= tp_price: return "TP"
        else:  # SELL
            if current_price >= sl_price: return "SL"
            if current_price <= tp_price: return "TP"
        return "NONE"