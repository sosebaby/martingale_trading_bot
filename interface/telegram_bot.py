"""
interface/telegram_bot.py
═══════════════════════════════════════════════════════
TEAM SUPPORT:
  - Multiple users can control the bot from a group
  - Each command shows WHO sent it
  - /stop requires confirmation to prevent accidents
  - All team members see all notifications
═══════════════════════════════════════════════════════
"""

import logging
import re
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler,
    MessageHandler, filters, ContextTypes
)
from engine.fsm      import MartingaleFSM, State
from engine.levels   import MartingaleLevels
from engine.logger   import TradeLogger
from config          import CONFIG

log = logging.getLogger("TelegramBot")


class TelegramBot:
    def __init__(self, fsm: MartingaleFSM, levels: MartingaleLevels,
                 logger: TradeLogger):
        self.fsm    = fsm
        self.levels = levels
        self.logger = logger
        self.app    = ApplicationBuilder().token(CONFIG["TELEGRAM_BOT_TOKEN"]).build()
        self._register_handlers()

    def _register_handlers(self):
        self.app.add_handler(CommandHandler("start",   self._cmd_start))
        self.app.add_handler(CommandHandler("status",  self._cmd_status))
        self.app.add_handler(CommandHandler("stop",    self._cmd_stop))
        self.app.add_handler(CommandHandler("table",   self._cmd_table))
        self.app.add_handler(CommandHandler("help",    self._cmd_start))
        self.app.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self._on_message)
        )

    def _get_name(self, update: Update) -> str:
        """Get display name of whoever sent the command."""
        user = update.effective_user
        return user.first_name or user.username or "Unknown"

    # ─── COMMANDS ───────────────────────────────────────────────────

    async def _cmd_start(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        if not self._is_allowed(update): return
        name = self._get_name(update)
        await update.message.reply_text(
            f"👋 Hey {name}! MartingaleBot is online.\n\n"
            "📋 *How to use:*\n"
            "  `BUY XAUUSD` — start auto-buying\n"
            "  `SELL XAUUSD` — start auto-selling\n"
            "  `/stop` — stop after current trade\n"
            "  `/status` — check current state\n"
            "  `/table` — show martingale levels\n\n"
            "🔄 After every TP hit the bot auto-restarts.\n"
            "📈 After SL hit martingale escalates automatically.\n"
            "✅ Any team member can send signals from this group.",
            parse_mode="Markdown"
        )

    async def _cmd_status(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        if not self._is_allowed(update): return
        from execution.flask_bridge import (_auto_active, _auto_direction,
                                            _auto_symbol, _cycle_count)
        status = self.fsm.status_str()
        auto   = (f"🔄 Auto-trading ON: {_auto_direction} {_auto_symbol}"
                  if _auto_active else "✋ Auto-trading: OFF")
        await update.message.reply_text(
            f"📊 *Bot Status*\n"
            f"{status}\n"
            f"{auto}\n"
            f"Cycles completed: {_cycle_count}",
            parse_mode="Markdown"
        )

    async def _cmd_stop(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        if not self._is_allowed(update): return
        from execution.flask_bridge import (set_auto_trade, _auto_symbol,
                                            _auto_direction, _cycle_count)
        name = self._get_name(update)
        set_auto_trade(_auto_direction, _auto_symbol, active=False)
        self.logger.log_stop(f"Telegram /stop by {name}")

        if self.fsm.is_idle():
            await update.message.reply_text(
                f"✋ *Stopped by {name}*\n"
                f"No active trade.\n"
                f"Cycles completed this session: {_cycle_count}\n"
                f"Send BUY or SELL to start again.",
                parse_mode="Markdown"
            )
        else:
            self.fsm.on_stop_command()
            await update.message.reply_text(
                f"⛔ *Stopped by {name}*\n"
                f"Auto-trading is OFF.\n"
                f"Current trade closed.\n"
                f"Cycles completed this session: {_cycle_count}\n"
                f"Send BUY or SELL whenever ready.",
                parse_mode="Markdown"
            )

    async def _cmd_table(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        if not self._is_allowed(update): return
        lines = ["📊 *Martingale Level Table*\n"]
        lines.append("`Level  Lots    SL pip  TP pip`")
        for lvl in range(1, CONFIG["MAX_MARTINGALE_LEVELS"] + 1):
            lines.append(
                f"`{lvl:<7}"
                f"{self.levels.get_lot_size(lvl):<8.2f}"
                f"{self.levels.get_sl_pips():<8}"
                f"{self.levels.get_tp_pips(lvl):.1f}`"
            )
        await update.message.reply_text(
            "\n".join(lines), parse_mode="Markdown"
        )

    # ─── SIGNAL HANDLER ─────────────────────────────────────────────

    async def _on_message(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        if not self._is_allowed(update): return

        text  = update.message.text.strip().upper()
        match = re.match(r"^(BUY|SELL)\s+([A-Z0-9]+)$", text)

        if not match:
            # Silently ignore non-signal messages in group chats
            chat_type = update.effective_chat.type
            if chat_type in ("group", "supergroup"):
                return
            await update.message.reply_text(
                "❓ Unknown command.\n"
                "Try: `BUY XAUUSD` or `SELL XAUUSD`\n"
                "Or use /help to see all commands.",
                parse_mode="Markdown"
            )
            return

        direction = match.group(1)
        symbol    = match.group(2)
        name      = self._get_name(update)

        if symbol not in CONFIG["ALLOWED_SYMBOLS"]:
            await update.message.reply_text(
                f"❌ Symbol `{symbol}` not allowed.\n"
                f"Allowed: {', '.join(CONFIG['ALLOWED_SYMBOLS'])}",
                parse_mode="Markdown"
            )
            return

        if not self.fsm.is_idle():
            from execution.flask_bridge import _auto_direction, _auto_symbol
            await update.message.reply_text(
                f"⚠️ Already trading!\n"
                f"{self.fsm.status_str()}\n"
                f"Current direction: {_auto_direction} {_auto_symbol}\n"
                f"Send /stop first to change direction.",
                parse_mode="Markdown"
            )
            return

        # ── Start auto-trading ───────────────────────────────────
        from execution.flask_bridge import set_auto_trade
        set_auto_trade(direction, symbol, active=True)
        self.fsm.on_signal_received(direction, symbol)
        self.logger.log_cycle_start(symbol, direction)

        lot_1 = self.levels.get_lot_size(1)
        tp_1  = self.levels.get_tp_pips(1)
        sl_1  = self.levels.get_sl_pips()

        await update.message.reply_text(
            f"✅ *{name} started auto-trading!*\n"
            f"Direction: {direction} {symbol}\n"
            f"Lots: {lot_1} | SL: {sl_1} pips | TP: {tp_1:.0f} pips\n\n"
            f"🔄 Auto-restarts after every TP hit.\n"
            f"Send /stop to stop anytime.",
            parse_mode="Markdown"
        )
        log.info(f"Auto-trade started by {name}: {direction} {symbol}")

    # ─── SECURITY ───────────────────────────────────────────────────

    def _is_allowed(self, update: Update) -> bool:
        uid     = update.effective_user.id
        chat_id = update.effective_chat.id
        allowed = CONFIG["TELEGRAM_ALLOWED_CHAT_IDS"]

        if uid in allowed or chat_id in allowed:
            return True

        log.warning(f"Blocked — user: {uid}, chat: {chat_id}")
        return False

    def run(self):
        log.info("Telegram bot polling started.")
        self.app.run_polling(drop_pending_updates=True)