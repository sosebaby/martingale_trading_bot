"""
execution/flask_bridge.py
═══════════════════════════════════════════════════════
TP LOGIC:
  - SL and TP are ALWAYS 1:1 (50 pips each, every level)
  - BUT on Level 2+, every tick checks running profit
  - If running profit >= all previous losses + $5 → close early
  - This way ratio stays 1:1 but recovery is still guaranteed
═══════════════════════════════════════════════════════
"""

from flask import Flask, request, jsonify
from engine.fsm      import MartingaleFSM, State
from engine.levels   import MartingaleLevels
from engine.analysis import MarketAnalysis
from engine.logger   import TradeLogger
from config          import CONFIG
import requests

app    = Flask(__name__)
logger = TradeLogger()
levels = MartingaleLevels(
    base_lot      = CONFIG["BASE_LOT_SIZE"],
    sl_pips       = CONFIG["SL_PIPS"],
    tp_pips       = CONFIG["TP_PIPS"],
    tp_escalation = CONFIG["TP_ESCALATION_FACTOR"],
    max_levels    = CONFIG["MAX_MARTINGALE_LEVELS"],
)
fsm = MartingaleFSM()

_auto_direction = ""
_auto_symbol    = ""
_auto_active    = False
_cycle_count    = 0

MIN_NET_PROFIT = CONFIG.get("MIN_NET_PROFIT_USD", 5.0)


def send_telegram(message: str):
    try:
        token   = CONFIG["TELEGRAM_BOT_TOKEN"]
        chat_id = CONFIG["TELEGRAM_ALLOWED_CHAT_IDS"][0]
        url     = f"https://api.telegram.org/bot{token}/sendMessage"
        requests.post(url, json={"chat_id": chat_id, "text": message}, timeout=5)
    except Exception as e:
        logger.error(f"Telegram notify failed: {e}")


def auto_restart():
    global _cycle_count
    if not _auto_active or not _auto_direction or not _auto_symbol:
        return
    _cycle_count += 1
    fsm.on_signal_received(_auto_direction, _auto_symbol)
    logger.log_cycle_start(_auto_symbol, _auto_direction)
    send_telegram(
        f"🔄 Auto-restarting — Cycle #{_cycle_count}\n"
        f"{_auto_direction} {_auto_symbol}\n"
        f"Send /stop anytime to stop."
    )


def set_auto_trade(direction: str, symbol: str, active: bool):
    global _auto_direction, _auto_symbol, _auto_active, _cycle_count
    _auto_direction = direction
    _auto_symbol    = symbol
    _auto_active    = active
    if not active:
        _cycle_count = 0


# ─── ENDPOINTS ──────────────────────────────────────────────────────

@app.route("/ping")
def ping():
    return "pong", 200


@app.route("/ea_offline")
def ea_offline():
    logger.info("MT5 EA went offline.")
    send_telegram("⚠️ MT5 EA went offline! Check MetaTrader.")
    return "ok", 200


@app.route("/status")
def status():
    return jsonify({
        "state":       fsm.state.value,
        "cycle":       fsm.status_str(),
        "auto_active": _auto_active,
        "direction":   _auto_direction,
        "symbol":      _auto_symbol,
        "cycles_done": _cycle_count,
    })


@app.route("/tick", methods=["POST"])
def tick():
    data       = request.get_json(silent=True) or {}
    symbol     = data.get("symbol", "")
    bid        = float(data.get("bid", 0))
    ask        = float(data.get("ask", 0))
    pos_profit = float(data.get("pos_profit", 0))  # live running profit from EA
    pip_size   = MarketAnalysis.get_pip_size(symbol)

    if not hasattr(tick, '_count'):
        tick._count = 0
    tick._count += 1
    if tick._count % 30 == 0:
        logger.info(f"FSM: {fsm.state.value} | Auto: {_auto_active} | "
                    f"Cycles: {_cycle_count}")

    # ── Open new trade ───────────────────────────────────────────────
    if fsm.state in (State.PENDING, State.ESCALATING):
        # Only open if EA chart symbol matches intended symbol
        if symbol.upper() != _auto_symbol.upper():
            return "HOLD", 200

        level     = fsm.get_level()
        lots      = levels.get_lot_size(level)
        direction = fsm.get_direction()
        entry     = ask if direction == "BUY" else bid

        # ALWAYS 1:1 — SL and TP same pips
        sl_price = levels.get_sl_price(entry, direction, pip_size)
        tp_price = levels.get_tp_price(entry, direction, pip_size, level=1)  # always level 1 pips = 1:1

        cmd = f"OPEN_{direction}|{lots}|{sl_price:.5f}|{tp_price:.5f}"
        logger.info(f"→ EA command: {cmd}")
        return cmd, 200

    # ── Monitor open trade for early close ──────────────────────────
    if fsm.state == State.IN_TRADE:
        total_loss = fsm.get_total_loss()

        # Only check early close on Level 2+ (there are losses to recover)
        if total_loss > 0 and pos_profit > 0:
            target = total_loss + MIN_NET_PROFIT
            if pos_profit >= target:
                logger.info(
                    f"🎯 Profit target hit! Running profit ${pos_profit:.2f} "
                    f">= losses ${total_loss:.2f} + ${MIN_NET_PROFIT} target"
                )
                return "CLOSE", 200

    return "HOLD", 200


@app.route("/trade_opened")
def trade_opened():
    ticket = request.args.get("ticket", "0")
    price  = float(request.args.get("price", 0))

    fsm.on_trade_opened(int(ticket), price)

    level      = fsm.get_level()
    direction  = fsm.get_direction()
    symbol     = fsm.get_symbol()
    pip_size   = MarketAnalysis.get_pip_size(symbol)
    lots       = levels.get_lot_size(level)
    total_loss = fsm.get_total_loss()
    sl         = levels.get_sl_price(price, direction, pip_size)
    tp         = levels.get_tp_price(price, direction, pip_size, level=1)

    logger.log_trade_opened(symbol, direction, level, lots, price, sl, tp)

    if total_loss > 0:
        target_note = (f"🎯 Will close early when profit >= "
                       f"${total_loss:.2f} losses + ${MIN_NET_PROFIT:.0f} = "
                       f"${total_loss + MIN_NET_PROFIT:.2f}")
    else:
        target_note = f"TP: {tp:.2f} | SL: {sl:.2f} (1:1)"

    send_telegram(
        f"📈 Trade Opened!\n"
        f"{direction} {symbol} | Level {level} | Lots: {lots}\n"
        f"Entry: {price:.2f} | SL: {sl:.2f} | TP: {tp:.2f}\n"
        f"{target_note}"
    )
    return "ok", 200


@app.route("/trade_closed")
def trade_closed():
    global _auto_active, _cycle_count

    ticket = request.args.get("ticket", "0")
    profit = float(request.args.get("profit", 0))

    if not fsm.is_in_trade():
        return "ok", 200

    level      = fsm.get_level()
    direction  = fsm.get_direction()
    symbol     = fsm.get_symbol()
    total_loss = fsm.get_total_loss()

    if profit < 0:
        # ── SL HIT ───────────────────────────────────────────────
        new_total = total_loss + abs(profit)
        logger.log_sl_hit(symbol, direction, level, profit, new_total)

        if levels.is_max_level(level + 1):
            logger.log_max_level(symbol, level + 1, new_total)
            fsm.reset()
            _auto_active = False
            send_telegram(
                f"🚨 MAX LEVEL REACHED!\n"
                f"Stopping to protect account.\n"
                f"Total loss: ${new_total:.2f}\n"
                f"Send a new signal to restart."
            )
        else:
            fsm.on_sl_hit(profit)
            next_level = fsm.get_level()
            next_lots  = levels.get_lot_size(next_level)
            send_telegram(
                f"🔴 SL Hit — Loss: ${abs(profit):.2f}\n"
                f"Total to recover: ${new_total:.2f}\n"
                f"⬆️ Escalating to Level {next_level}\n"
                f"Next lots: {next_lots} (1:1 ratio maintained)\n"
                f"Will close when profit >= ${new_total + MIN_NET_PROFIT:.2f}"
            )

    else:
        # ── TP HIT or EARLY CLOSE ────────────────────────────────
        result = fsm.on_tp_hit(profit)
        _cycle_count += 1
        logger.log_tp_hit(symbol, direction, level, profit,
                          total_loss, result["net_gain"])

        close_type = "🎯 Target Reached!" if total_loss > 0 else "🟢 TP Hit!"
        send_telegram(
            f"{close_type} Cycle Complete!\n"
            f"Gross profit: ${profit:.2f}\n"
            f"Losses recovered: ${total_loss:.2f}\n"
            f"✅ NET GAIN: ${result['net_gain']:.2f}\n"
            f"Total cycles: {_cycle_count}\n"
            f"{'🔄 Opening next trade...' if _auto_active else '✋ Stopped.'}"
        )

        if _auto_active:
            auto_restart()

    return "ok", 200


def start_server(host="127.0.0.1", port=5000):
    logger.info(f"Flask bridge on http://{host}:{port}")
    app.run(host=host, port=port, debug=False, use_reloader=False)