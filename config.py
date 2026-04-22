"""
config.py — Single source of truth for all bot settings.
"""

CONFIG = {

    # ── TELEGRAM ─────────────────────────────────────────────────────
    "TELEGRAM_BOT_TOKEN": "YOUR-TOKEN",
    "TELEGRAM_ALLOWED_CHAT_IDS": [
        6290115847,
        -1003567290589
    ],

    # ── MT5 ACCOUNT ───────────────────────────────────────────────────
    "MT5_LOGIN":    YOUR-LOGIN,
    "MT5_PASSWORD": "PASSWORD",
    "MT5_SERVER":   "Exness-**

    # ── MARTINGALE SETTINGS ───────────────────────────────────────────
    "BASE_LOT_SIZE":          0.01,   # Lot size at Level 1
    "SL_PIPS":                50,     # Stop Loss pips (never changes)
    "TP_PIPS":                50,     # Take Profit pips at Level 1
    "TP_ESCALATION_FACTOR":   0.5,    # 50% TP increase per level
    "MAX_MARTINGALE_LEVELS":  6,      # Safety cap

    # ── PROFIT TARGET ─────────────────────────────────────────────────
    # After SL hits, the recovery trade only closes when:
    # current trade profit >= all previous losses + MIN_NET_PROFIT_USD
    "MIN_NET_PROFIT_USD": 5.0,        # Minimum $5 net gain per cycle

    # ── ALLOWED SYMBOLS ───────────────────────────────────────────────
    "ALLOWED_SYMBOLS": [
        "EURUSD", "GBPUSD", "USDJPY", "AUDUSD",
        "GBPJPY", "XAUUSD", "XAUUSDM", "XAUUSDC", "BTCUSD", "ETHUSD",
        "US30",   "NAS100",
    ],

    # ── FLASK SERVER ──────────────────────────────────────────────────
    "FLASK_HOST": "127.0.0.1",
    "FLASK_PORT": 5000,
}
