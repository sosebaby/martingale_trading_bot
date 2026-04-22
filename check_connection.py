"""
check_connection.py
════════════════════════════════════════════════════════
Run this BEFORE starting the bot to verify everything works.

  python check_connection.py
════════════════════════════════════════════════════════
"""

import sys

print("\n" + "=" * 50)
print("  MARTINGALE BOT — CONNECTION CHECKER")
print("=" * 50 + "\n")


# ── 1. Check Python imports ──────────────────────────
print("1. Checking Python imports...")
try:
    from config import CONFIG
    from engine.fsm      import MartingaleFSM
    from engine.levels   import MartingaleLevels
    from engine.analysis import MarketAnalysis
    from engine.logger   import TradeLogger
    print("   ✅ All engine imports OK")
except ImportError as e:
    print(f"   ❌ Import error: {e}")
    print("   Run: pip install flask python-telegram-bot")
    sys.exit(1)

try:
    import flask
    print(f"   ✅ Flask {flask.__version__} installed")
except ImportError:
    print("   ❌ Flask missing — run: pip install flask")

try:
    import telegram
    print(f"   ✅ python-telegram-bot installed")
except ImportError:
    print("   ❌ python-telegram-bot missing — run: pip install python-telegram-bot")

# MT5 import — silently expected to fail on Mac
try:
    import MetaTrader5
    print("   ✅ MetaTrader5 package found (Windows mode)")
except ImportError:
    print("   ✅ MetaTrader5 not installed — normal on Mac, EA handles trades directly")


# ── 2. Check config values ───────────────────────────
print("\n2. Checking config.py...")
token    = CONFIG.get("TELEGRAM_BOT_TOKEN", "")
chat_ids = CONFIG.get("TELEGRAM_ALLOWED_CHAT_IDS", [])

if not token or "YOUR_BOT_TOKEN" in token:
    print("   ⚠️  TELEGRAM_BOT_TOKEN not set")
else:
    print(f"   ✅ Telegram token: {token[:10]}...{token[-5:]}")

if not chat_ids or chat_ids == [123456789]:
    print("   ⚠️  TELEGRAM_ALLOWED_CHAT_IDS not set")
else:
    print(f"   ✅ Allowed chat IDs: {chat_ids}")


# ── 3. Test Telegram connection ──────────────────────
print("\n3. Testing Telegram bot token...")
import urllib.request, json
try:
    url = f"https://api.telegram.org/bot{token}/getMe"
    with urllib.request.urlopen(url, timeout=5) as resp:
        data = json.loads(resp.read())
    if data.get("ok"):
        print(f"   ✅ Bot connected: @{data['result']['username']}")
    else:
        print(f"   ❌ Invalid token: {data}")
except Exception as e:
    print(f"   ❌ Telegram test failed: {e}")


# ── 4. Martingale level table ────────────────────────
print("\n4. Martingale level preview:")
lv = MartingaleLevels(
    base_lot      = CONFIG["BASE_LOT_SIZE"],
    sl_pips       = CONFIG["SL_PIPS"],
    tp_pips       = CONFIG["TP_PIPS"],
    tp_escalation = CONFIG["TP_ESCALATION_FACTOR"],
    max_levels    = CONFIG["MAX_MARTINGALE_LEVELS"],
)
lv.print_table()


print("=" * 50)
print("  All good? Run:  python main.py")
print("=" * 50 + "\n")