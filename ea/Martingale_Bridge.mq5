//+------------------------------------------------------------------+
//|                    Martingale_Bridge.mq5                         |
//|                                                                  |
//| ROLE: The only file that lives inside MetaTrader 5.              |
//|       Acts as a BRIDGE between MT5 and the Python engine.        |
//|                                                                  |
//| WHAT IT DOES:                                                     |
//|   1. Every tick → asks Python "should I open/close a trade?"     |
//|   2. Python replies with a command (OPEN_BUY, OPEN_SELL, CLOSE)  |
//|   3. This EA executes that command directly in MT5               |
//|   4. Reports back the result (ticket, price, profit) to Python   |
//|                                                                  |
//| COMMUNICATION: HTTP requests to Flask server on localhost:5000   |
//|                                                                  |
//| HOW TO INSTALL:                                                  |
//|   MT5 → File → Open Data Folder → MQL5 → Experts                |
//|   Copy this file there → F7 to compile → Drag onto chart        |
//+------------------------------------------------------------------+
#property copyright "MartingaleBot"
#property version   "1.0"

#include <Trade\Trade.mqh>

//--- Input Parameters (set in MT5 EA settings panel)
input string FlaskServerURL  = "http://localhost:5000";  // Python server address
input int    MagicNumber     = 20240001;                 // Unique trade ID
input int    Slippage        = 20;                       // Max slippage (points)
input int    PollIntervalSec = 1;                        // How often to poll Python

//--- Globals
CTrade     g_Trade;
datetime   g_LastPoll = 0;
ulong      g_CurrentTicket = 0;

//+------------------------------------------------------------------+
//| OnInit                                                            |
//+------------------------------------------------------------------+
int OnInit()
{
   g_Trade.SetExpertMagicNumber(MagicNumber);
   g_Trade.SetDeviationInPoints(Slippage);

   Print("=== Martingale Bridge EA started ===");
   Print("Connecting to Python engine at: ", FlaskServerURL);

   // Tell Python the EA is alive
   string response = HttpGET(FlaskServerURL + "/ping");
   if(StringFind(response, "pong") < 0)
   {
      Alert("Cannot reach Python engine! Make sure main.py is running.");
      return INIT_FAILED;
   }

   Print("Python engine connected successfully.");
   return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
//| OnDeinit                                                          |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   HttpGET(FlaskServerURL + "/ea_offline");
   Print("Bridge EA stopped.");
}

//+------------------------------------------------------------------+
//| OnTick — main loop                                                |
//+------------------------------------------------------------------+
void OnTick()
{
   if(TimeCurrent() - g_LastPoll < PollIntervalSec) return;
   g_LastPoll = TimeCurrent();

   // --- Step 1: Send current account/position state to Python ---
   string symbol  = _Symbol;
   double bid     = SymbolInfoDouble(symbol, SYMBOL_BID);
   double ask     = SymbolInfoDouble(symbol, SYMBOL_ASK);
   double balance = AccountInfoDouble(ACCOUNT_BALANCE);
   double equity  = AccountInfoDouble(ACCOUNT_EQUITY);

   // Check if our position is still open
   bool posOpen = PositionSelectByTicket(g_CurrentTicket);
   double posProfit = posOpen ? PositionGetDouble(POSITION_PROFIT) : 0.0;

   string stateJSON = StringFormat(
      "{\"symbol\":\"%s\",\"bid\":%.5f,\"ask\":%.5f,"
      "\"balance\":%.2f,\"equity\":%.2f,"
      "\"ticket\":%d,\"pos_open\":%s,\"pos_profit\":%.2f}",
      symbol, bid, ask, balance, equity,
      g_CurrentTicket, posOpen ? "true" : "false", posProfit
   );

   // --- Step 2: POST state to Python, get back a command ---
   string command = HttpPOST(FlaskServerURL + "/tick", stateJSON);

   // --- Step 3: Execute whatever Python told us to do ---
   ExecuteCommand(command, symbol, ask, bid);
}

//+------------------------------------------------------------------+
//| ExecuteCommand — acts on Python's instruction                     |
//+------------------------------------------------------------------+
void ExecuteCommand(string cmd, string symbol, double ask, double bid)
{
   if(cmd == "" || cmd == "HOLD") return;

   // OPEN_BUY|lots|sl|tp
   if(StringFind(cmd, "OPEN_BUY") == 0)
   {
      string parts[];
      StringSplit(cmd, '|', parts);
      double lots = StringToDouble(parts[1]);
      double sl   = StringToDouble(parts[2]);
      double tp   = StringToDouble(parts[3]);

      if(g_Trade.Buy(lots, symbol, ask, sl, tp, "Martingale"))
      {
         g_CurrentTicket = g_Trade.ResultOrder();
         PrintFormat("BUY opened. Ticket=%d Lots=%.2f SL=%.5f TP=%.5f",
                     g_CurrentTicket, lots, sl, tp);
         // Report back to Python
         HttpGET(StringFormat("%s/trade_opened?ticket=%d&price=%.5f",
                 FlaskServerURL, g_CurrentTicket, ask));
      }
      else
         PrintFormat("BUY failed: %s", g_Trade.ResultRetcodeDescription());
   }

   // OPEN_SELL|lots|sl|tp
   else if(StringFind(cmd, "OPEN_SELL") == 0)
   {
      string parts[];
      StringSplit(cmd, '|', parts);
      double lots = StringToDouble(parts[1]);
      double sl   = StringToDouble(parts[2]);
      double tp   = StringToDouble(parts[3]);

      if(g_Trade.Sell(lots, symbol, bid, sl, tp, "Martingale"))
      {
         g_CurrentTicket = g_Trade.ResultOrder();
         PrintFormat("SELL opened. Ticket=%d Lots=%.2f SL=%.5f TP=%.5f",
                     g_CurrentTicket, lots, sl, tp);
         HttpGET(StringFormat("%s/trade_opened?ticket=%d&price=%.5f",
                 FlaskServerURL, g_CurrentTicket, bid));
      }
      else
         PrintFormat("SELL failed: %s", g_Trade.ResultRetcodeDescription());
   }

   // CLOSE
   else if(cmd == "CLOSE")
   {
      if(g_Trade.PositionClose(g_CurrentTicket))
      {
         PrintFormat("Position %d closed.", g_CurrentTicket);
         HttpGET(StringFormat("%s/trade_closed?ticket=%d",
                 FlaskServerURL, g_CurrentTicket));
         g_CurrentTicket = 0;
      }
   }
}

//+------------------------------------------------------------------+
//| HttpGET — sends a GET request, returns response body             |
//+------------------------------------------------------------------+
string HttpGET(string url)
{
   char   post[], result[];
   string headers;
   int res = WebRequest("GET", url, "", 3000, post, result, headers);
   if(res < 0) return "";
   return CharArrayToString(result);
}

//+------------------------------------------------------------------+
//| HttpPOST — sends JSON body, returns response body                |
//+------------------------------------------------------------------+
string HttpPOST(string url, string jsonBody)
{
   char post[], result[];
   StringToCharArray(jsonBody, post, 0, StringLen(jsonBody));
   string headers  = "Content-Type: application/json\r\n";
   string respHeaders;
   int res = WebRequest("POST", url, headers, 3000, post, result, respHeaders);
   if(res < 0) return "";
   return CharArrayToString(result);
}