"""
main.py — Entry point. Starts Flask + Telegram sharing the same FSM.
"""

import threading
from engine.levels   import MartingaleLevels
from engine.logger   import TradeLogger
from config          import CONFIG

# ── Import the SINGLE shared FSM from flask_bridge ──────────────────
# Both flask_bridge and telegram_bot use this same object
from execution.flask_bridge import start_server, fsm, levels as flask_levels
from interface.telegram_bot import TelegramBot


def main():
    print("=" * 55)
    print("  MARTINGALE BOT — STARTING UP")
    print("=" * 55)

    logger = TradeLogger()

    # Print martingale table
    levels = MartingaleLevels(
        base_lot      = CONFIG["BASE_LOT_SIZE"],
        sl_pips       = CONFIG["SL_PIPS"],
        tp_pips       = CONFIG["TP_PIPS"],
        tp_escalation = CONFIG["TP_ESCALATION_FACTOR"],
        max_levels    = CONFIG["MAX_MARTINGALE_LEVELS"],
    )
    levels.print_table()

    # Start Flask in background thread
    flask_thread = threading.Thread(
        target=start_server,
        kwargs={"host": CONFIG["FLASK_HOST"], "port": CONFIG["FLASK_PORT"]},
        daemon=True
    )
    flask_thread.start()
    logger.info(f"Flask bridge running on {CONFIG['FLASK_HOST']}:{CONFIG['FLASK_PORT']}")

    # Pass the SAME fsm object to TelegramBot
    bot = TelegramBot(fsm=fsm, levels=flask_levels, logger=logger)
    logger.info("Telegram bot starting... Waiting for signals.")
    bot.run()


if __name__ == "__main__":
    main()