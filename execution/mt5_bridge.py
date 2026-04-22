"""
execution/mt5_bridge.py
════════════════════════════════════════════════════════
ROLE: Placeholder file kept for project structure.

ON MAC: This file does nothing. The MetaTrader5 Python
package does not exist on Mac — and that's completely
fine. The MQL5 EA (Martingale_Bridge.mq5) handles ALL
trade execution and profit reading directly inside MT5.
It then sends the results to Python via HTTP.

ON WINDOWS (optional): If you ever move to a Windows
VPS, you can uncomment the MT5 code below to connect
Python directly to MT5 as well.

YOU DO NOT NEED TO CHANGE THIS FILE.
════════════════════════════════════════════════════════
"""

# MT5_AVAILABLE will always be False on Mac.
# The rest of the bot does not depend on this being True.
MT5_AVAILABLE = False

try:
    import MetaTrader5 as mt5  # Only works on Windows
    MT5_AVAILABLE = True
except ImportError:
    pass  # Silently ignored on Mac — this is expected and fine


class MT5Bridge:
    """
    On Mac: all methods return safe empty/None values.
    On Windows (optional): connect() can be used to link Python to MT5.
    """

    @staticmethod
    def is_available() -> bool:
        return MT5_AVAILABLE

    @staticmethod
    def connect(login: int, password: str, server: str) -> bool:
        if not MT5_AVAILABLE:
            # This is normal on Mac — no action needed
            return False

        # Windows only below this line
        if not mt5.initialize():
            print(f"MT5 init failed: {mt5.last_error()}")
            return False

        if not mt5.login(login=login, password=password, server=server):
            print(f"MT5 login failed: {mt5.last_error()}")
            mt5.shutdown()
            return False

        info = mt5.account_info()
        print(f"MT5 connected: Account {info.login}, "
              f"Balance {info.balance} {info.currency}")
        return True

    @staticmethod
    def disconnect():
        if MT5_AVAILABLE:
            mt5.shutdown()

    @staticmethod
    def get_deal_profit(position_ticket: int):
        """
        On Mac: always returns None.
        Profit is sent directly by the EA via /trade_closed?profit=X
        so this function is never needed on Mac.
        """
        if not MT5_AVAILABLE:
            return None

        from datetime import datetime, timedelta
        from_date = datetime.now() - timedelta(days=1)
        deals = mt5.history_deals_get(from_date, datetime.now())
        if deals is None:
            return None

        for deal in reversed(deals):
            if (deal.position_id == position_ticket and
                    deal.entry == mt5.DEAL_ENTRY_OUT):
                return deal.profit
        return None

    @staticmethod
    def get_account_info() -> dict:
        if not MT5_AVAILABLE:
            return {}
        info = mt5.account_info()
        if info is None:
            return {}
        return {
            "balance":  info.balance,
            "equity":   info.equity,
            "margin":   info.margin,
            "currency": info.currency,
        }