# 🤖 Martingale Futures Trading Bot

A production-grade autonomous trading system that integrates a Python FSM engine, Flask HTTP bridge, MetaTrader5 EA, and Telegram bot to execute and manage martingale-based futures trades in real time.

---

## 📌 Overview

This bot listens for trading signals via Telegram, opens positions on MetaTrader5, and autonomously manages a full martingale cycle — including loss recovery, position escalation, and early-close logic — with no manual intervention required.

It is designed to run on **Mac** (or Windows), with all trade execution handled by an MQL5 Expert Advisor (EA) inside MetaTrader5. Python communicates with the EA via HTTP endpoints served by a Flask bridge.

---

## 🏗️ Architecture

```
Telegram Bot
     │
     │  BUY / SELL signal
     ▼
 FSM Engine  ◄──────────────────────────────┐
     │                                       │
     │  State: PENDING / ESCALATING          │
     ▼                                       │
Flask Bridge  ◄──── /tick (live prices) ────┤
     │                                       │
     │  OPEN_BUY / OPEN_SELL / CLOSE / HOLD  │
     ▼                                       │
MetaTrader5 EA ──── /trade_opened ──────────┤
                 └── /trade_closed ──────────┘
```

### Components

| File | Role |
|------|------|
| `main.py` | Entry point — starts Flask + Telegram bot sharing one FSM |
| `engine/fsm.py` | Finite State Machine — tracks full martingale cycle state |
| `engine/levels.py` | Pure math — lot sizes, SL/TP prices per level |
| `engine/analysis.py` | Pip size mapping, spread validation, signal checking |
| `engine/logger.py` | CSV + console logging of every trade event |
| `execution/flask_bridge.py` | HTTP server — receives ticks and trade events from MT5 EA |
| `execution/mt5_bridge.py` | MT5 Python bridge (Windows only, gracefully skipped on Mac) |
| `config.py` | Single source of truth for all settings |
| `check_connection.py` | Pre-flight checker — run before starting the bot |

---

## ⚙️ How It Works

### Martingale Logic

The bot uses a classic martingale strategy with a fixed stop-loss and escalating take-profit:

| Level | Lot Size | SL (pips) | TP (pips) |
|-------|----------|-----------|-----------|
| 1 | 0.01 | 50 | 50 |
| 2 | 0.02 | 50 | 75 |
| 3 | 0.04 | 50 | 112.5 |
| 4 | 0.08 | 50 | 168.8 |
| 5 | 0.16 | 50 | 253.1 |
| 6 | 0.32 | 50 | 379.7 |

- **SL pips never change** — risk is fixed per trade
- **Lot size doubles** at each level
- **TP grows 50%** per level to ensure full loss recovery
- **Early close** — on Level 2+, the bot monitors live running profit tick-by-tick and closes as soon as `profit >= all previous losses + $5 net gain`
- **Max level cap** — automatically stops at Level 6 to protect the account

### FSM States

```
IDLE ──[signal]──► PENDING ──[trade opens]──► IN_TRADE
                                                  │
                                          ┌───────┴───────┐
                                       SL hit           TP hit
                                          │               │
                                     ESCALATING       COMPLETE
                                          │               │
                                     [reopens]         [reset]
                                          │               │
                                       IN_TRADE         IDLE
```

### Telegram Commands

| Command | Action |
|---------|--------|
| `/buy XAUUSD` | Open a BUY cycle on Gold |
| `/sell EURUSD` | Open a SELL cycle on EUR/USD |
| `/auto buy XAUUSD` | Auto-restart cycles after each TP hit |
| `/stop` | Stop after current trade closes |
| `/status` | Show current FSM state and cycle info |

---

## 🛠️ Setup & Installation

### Requirements

- Python 3.10+
- MetaTrader5 (with MQL5 EA installed and running)
- A Telegram Bot Token (from [@BotFather](https://t.me/BotFather))
- An Exness (or compatible) MT5 live/demo account

### Install Dependencies

```bash
pip install flask python-telegram-bot requests
```

> MetaTrader5 Python package is Windows-only and not required on Mac. The EA handles all execution directly.

### Configuration

Edit `config.py` with your credentials:

```python
CONFIG = {
    "TELEGRAM_BOT_TOKEN": "YOUR_BOT_TOKEN",
    "TELEGRAM_ALLOWED_CHAT_IDS": [YOUR_CHAT_ID],

    "MT5_LOGIN":    YOUR_ACCOUNT_NUMBER,
    "MT5_PASSWORD": "YOUR_PASSWORD",
    "MT5_SERVER":   "YOUR_BROKER_SERVER",

    "BASE_LOT_SIZE":         0.01,
    "SL_PIPS":               50,
    "TP_PIPS":               50,
    "TP_ESCALATION_FACTOR":  0.5,
    "MAX_MARTINGALE_LEVELS": 6,
    "MIN_NET_PROFIT_USD":    5.0,
}
```

### Pre-flight Check

```bash
python check_connection.py
```

This verifies imports, Telegram token, config values, and prints the martingale level table.

### Run the Bot

```bash
python main.py
```

---

## 📊 Trade Logging

Every trade event is logged to:

- **`bot.log`** — timestamped console log
- **`trade_log.csv`** — permanent CSV record with 13 fields per event

CSV fields: `timestamp, event, symbol, direction, level, lots, entry, sl, tp, profit_usd, total_loss_usd, net_usd, notes`

Events logged: `CYCLE_START`, `OPEN`, `SL_HIT`, `TP_HIT`, `MAX_LEVEL`, `STOP`

---

## 📈 Supported Instruments

```
EURUSD  GBPUSD  USDJPY  AUDUSD
GBPJPY  XAUUSD  BTCUSD  ETHUSD
US30    NAS100
```

---

## 🔐 Security Notes
- Only whitelisted Telegram chat IDs can send signals
- Max level cap prevents runaway loss escalation
- Spread validation blocks trades during high-volatility news events

---

## 📁 Project Structure

```
Martingale bot/
├── main.py                   # Entry point
├── config.py                 # Settings (excluded from git)
├── check_connection.py       # Pre-flight checker
├── trade_log.csv             # Auto-generated trade log
├── bot.log                   # Auto-generated console log
├── engine/
│   ├── fsm.py                # Finite State Machine
│   ├── levels.py             # Martingale math
│   ├── analysis.py           # Market analysis & pip sizes
│   └── logger.py             # Trade event logger
└── execution/
    ├── flask_bridge.py       # HTTP server for MT5 EA
    └── mt5_bridge.py         # MT5 Python bridge (Windows)
```

---

## 👩‍💻 Author

**Euodia Ebalu**
AI Student — Durham College | Honours Bachelor of Artificial Intelligence
[GitHub](https://github.com/sosebaby) · [LinkedIn](https://linkedin.com/in/euodia-eseose-ebalu)

---

## ⚠️ Disclaimer

This bot is for educational and research purposes. Martingale strategies carry significant financial risk. Past performance does not guarantee future results. Trade responsibly.
