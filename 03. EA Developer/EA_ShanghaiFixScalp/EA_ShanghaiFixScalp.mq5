//+------------------------------------------------------------------+
//| EA_ShanghaiFixScalp.mq5 — Shanghai Gold Fix Window Scalper       |
//| Symbol: XAUUSD+  |  Period: M15  |  Style: Fix-Window Scalp      |
//|                                                                   |
//| EDGE HYPOTHESIS:                                                  |
//| Shanghai Gold Exchange (SGE) runs 2 daily gold auctions that      |
//| create order flow from Chinese physical gold demand (world's #1   |
//| consumer market). Importers/jewelers buy gold ahead of fix to     |
//| lock pricing, creating pre-fix appreciation similar to LBMA.      |
//|                                                                   |
//| SGE Fix times (Beijing Time = UTC+8):                             |
//|   AM Fix: 10:15 AM BJT = 02:15 UTC                               |
//|   PM Fix: 14:15 PM BJT = 06:15 UTC                               |
//|                                                                   |
//| Strategy: Enter LONG before fix, exit after fix settles.          |
//| Also test SHORT (in case fix creates selling, not buying).        |
//| Also test BOTH fixes and each independently.                      |
//|                                                                   |
//| COUNTERPARTY: Chinese importers, jewelers, industrial buyers      |
//| STRUCTURAL REASON: Physical demand → pre-fix appreciation         |
//| DIFFERENT FROM COBRA: Cobra = LBMA PM Fix h16-17 (hedger sell).   |
//|   Shanghai = Asian session physical buy. Different time, different |
//|   counterparty, potentially different direction.                   |
//|                                                                   |
//| SIGNALS ON BAR[1] ONLY — no repaint, no lookahead.                |
//| Max | 2026-04-12 | v1.0                                          |
//+------------------------------------------------------------------+
#property copyright "Max — EA_ShanghaiFixScalp v1.0"
#property link      ""
#property version   "1.00"
#property strict

//+------------------------------------------------------------------+
//| Input Parameters                                                  |
//+------------------------------------------------------------------+
input group "=== General ==="
input ulong    InpMagic         = 206101;     // Magic Number
input int      InpDeviation     = 30;         // Max Slippage (pts)
input bool     InpKillSwitch    = false;      // Kill Switch

input group "=== Fix Windows (Server Time Hours) ==="
input bool     InpAMFix         = true;       // Trade AM Fix window
input bool     InpPMFix         = true;       // Trade PM Fix window
input int      InpAM_EntryH     = 4;          // AM Fix entry hour (server)
input int      InpAM_EntryM     = 0;          // AM Fix entry minute
input int      InpPM_EntryH     = 8;          // PM Fix entry hour (server)
input int      InpPM_EntryM     = 0;          // PM Fix entry minute
input int      InpHoldBars      = 2;          // Hold N bars after entry (M15 = 30min)

input group "=== Direction ==="
input int      InpDirection     = 0;          // 0=Buy, 1=Sell, 2=Both

input group "=== Risk Management ==="
input double   InpRiskPct       = 0.50;       // Risk per trade (% of balance)
input double   InpMaxLot        = 1.0;        // Max lot per trade
input int      InpMaxPerDay     = 2;          // Max trades per day (1 per fix)
input double   InpDailyDD       = 4.0;        // Daily DD Limit (%)
input double   InpATR_SL_Mult   = 1.5;        // SL = ATR * multiplier
input int      InpATR_Period    = 14;         // ATR period
input int      InpMinSLPoints   = 50;         // Min SL distance (points)
input int      InpMaxSLPoints   = 400;        // Max SL distance (points)

input group "=== TP Mode ==="
input int      InpTPMode        = 0;          // 0=Time-based exit, 1=RR target, 2=Both
input double   InpRR            = 1.5;        // R:R for TP (if mode 1 or 2)

input group "=== Filters ==="
input bool     InpSkipFriday    = true;       // Skip Friday (weekend risk)
input bool     InpSkipMonday    = false;      // Skip Monday
input bool     InpSkipTuesday   = false;      // Skip Tuesday
input bool     InpSkipWednesday = false;      // Skip Wednesday
input bool     InpSkipThursday  = false;      // Skip Thursday
input double   InpMinATR        = 0;          // Min ATR filter (0=disabled)

//+------------------------------------------------------------------+
//| Globals                                                           |
//+------------------------------------------------------------------+
int      g_hATR = INVALID_HANDLE;
datetime g_lastBar = 0;
int      g_tradesToday = 0;
int      g_lastTradeDay = -1;
double   g_dayStartBalance = 0;

int g_holdCountdown = 0;  // bars remaining before time-exit

//+------------------------------------------------------------------+
//| Expert initialization                                             |
//+------------------------------------------------------------------+
int OnInit()
{
   g_hATR = iATR(_Symbol, PERIOD_CURRENT, InpATR_Period);
   if(g_hATR == INVALID_HANDLE)
   {
      Print("[SGF] FATAL: ATR init failed");
      return INIT_FAILED;
   }

   g_dayStartBalance = AccountInfoDouble(ACCOUNT_BALANCE);
   g_holdCountdown = 0;

   PrintFormat("[SGF] EA_ShanghaiFixScalp v1.00 | %s %s | Magic=%d",
               _Symbol, EnumToString(_Period), InpMagic);
   PrintFormat("[SGF] AM Fix=%s (h%02d:%02d) | PM Fix=%s (h%02d:%02d) | Hold=%d bars",
               InpAMFix?"ON":"OFF", InpAM_EntryH, InpAM_EntryM,
               InpPMFix?"ON":"OFF", InpPM_EntryH, InpPM_EntryM,
               InpHoldBars);
   PrintFormat("[SGF] Direction=%s | ATR_SL=%.1fx | RR=%.1f",
               InpDirection==0?"BUY":InpDirection==1?"SELL":"BOTH",
               InpATR_SL_Mult, InpRR);

   return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
//| Expert deinitialization                                           |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   if(g_hATR != INVALID_HANDLE)
      IndicatorRelease(g_hATR);
}

//+------------------------------------------------------------------+
//| Count positions with our magic                                    |
//+------------------------------------------------------------------+
int CountPositions()
{
   int cnt = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket > 0 && PositionGetInteger(POSITION_MAGIC) == (long)InpMagic
         && PositionGetString(POSITION_SYMBOL) == _Symbol)
         cnt++;
   }
   return cnt;
}

//+------------------------------------------------------------------+
//| Check daily drawdown                                              |
//+------------------------------------------------------------------+
bool IsDailyDDExceeded()
{
   if(g_dayStartBalance <= 0) return false;
   double equity = AccountInfoDouble(ACCOUNT_EQUITY);
   double dd = (g_dayStartBalance - equity) / g_dayStartBalance * 100.0;
   return dd >= InpDailyDD;
}

//+------------------------------------------------------------------+
//| Calculate lot size                                                |
//+------------------------------------------------------------------+
double CalcLot(double slDist)
{
   if(slDist <= 0) return 0;
   double balance   = AccountInfoDouble(ACCOUNT_BALANCE);
   double riskMoney = balance * InpRiskPct / 100.0;
   double tickValue = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
   double tickSize  = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   if(tickValue <= 0 || tickSize <= 0) return 0;

   double lot = riskMoney / (slDist / tickSize * tickValue);

   double minLot  = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double maxLot  = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   double lotStep = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);

   lot = MathMin(lot, InpMaxLot);
   lot = MathMin(lot, maxLot);
   lot = MathMax(lot, minLot);
   lot = MathFloor(lot / lotStep) * lotStep;
   return lot;
}

//+------------------------------------------------------------------+
//| Close position by ticket                                          |
//+------------------------------------------------------------------+
bool ClosePosition(ulong ticket)
{
   if(!PositionSelectByTicket(ticket)) return false;

   double vol = PositionGetDouble(POSITION_VOLUME);
   long   typ = PositionGetInteger(POSITION_TYPE);

   MqlTradeRequest req = {};
   MqlTradeResult  res = {};

   req.action    = TRADE_ACTION_DEAL;
   req.symbol    = _Symbol;
   req.volume    = vol;
   req.type      = (typ == POSITION_TYPE_BUY) ? ORDER_TYPE_SELL : ORDER_TYPE_BUY;
   req.price     = (typ == POSITION_TYPE_BUY) ?
                   SymbolInfoDouble(_Symbol, SYMBOL_BID) :
                   SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   req.deviation = (ulong)InpDeviation;
   req.magic     = InpMagic;
   req.position  = ticket;
   req.type_filling = ORDER_FILLING_FOK;

   if(!OrderSend(req, res))
   {
      req.type_filling = ORDER_FILLING_IOC;
      if(!OrderSend(req, res))
      {
         PrintFormat("[SGF] Close FAIL ticket=%d err=%d", ticket, GetLastError());
         return false;
      }
   }

   if(res.retcode == TRADE_RETCODE_DONE || res.retcode == TRADE_RETCODE_PLACED)
   {
      PrintFormat("[SGF] CLOSED ticket=%d @ %.5f", ticket, res.price);
      return true;
   }
   return false;
}

//+------------------------------------------------------------------+
//| Process time-based exits — close all positions by magic           |
//+------------------------------------------------------------------+
void ProcessExits()
{
   if(g_holdCountdown <= 0) return;

   g_holdCountdown--;

   if(g_holdCountdown <= 0)
   {
      // Close all positions with our magic
      for(int i = PositionsTotal() - 1; i >= 0; i--)
      {
         ulong ticket = PositionGetTicket(i);
         if(ticket > 0 && PositionGetInteger(POSITION_MAGIC) == (long)InpMagic
            && PositionGetString(POSITION_SYMBOL) == _Symbol)
            ClosePosition(ticket);
      }
   }
}

//+------------------------------------------------------------------+
//| Open a trade                                                      |
//+------------------------------------------------------------------+
bool OpenTrade(int direction, double slDist, string comment)
{
   double lot = CalcLot(slDist);
   if(lot <= 0) return false;

   int digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);

   double sl, tp, price;

   if(direction == 0) // BUY
   {
      price = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
      sl = NormalizeDouble(price - slDist, digits);
      if(InpTPMode == 0)
         tp = 0;  // Time-based exit, no TP
      else
         tp = NormalizeDouble(price + slDist * InpRR, digits);
   }
   else // SELL
   {
      price = SymbolInfoDouble(_Symbol, SYMBOL_BID);
      sl = NormalizeDouble(price + slDist, digits);
      if(InpTPMode == 0)
         tp = 0;
      else
         tp = NormalizeDouble(price - slDist * InpRR, digits);
   }

   // Stop level check
   int stopLevel = (int)SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL);
   double minDist = stopLevel * _Point;
   if(slDist < minDist) return false;
   if(tp > 0 && MathAbs(price - tp) < minDist) return false;

   MqlTradeRequest req = {};
   MqlTradeResult  res = {};

   req.action    = TRADE_ACTION_DEAL;
   req.symbol    = _Symbol;
   req.volume    = lot;
   req.type      = (direction == 0) ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
   req.price     = price;
   req.sl        = sl;
   req.tp        = tp;
   req.deviation = (ulong)InpDeviation;
   req.magic     = InpMagic;
   req.comment   = comment;
   req.type_filling = ORDER_FILLING_FOK;

   if(!OrderSend(req, res))
   {
      req.type_filling = ORDER_FILLING_IOC;
      if(!OrderSend(req, res))
      {
         PrintFormat("[SGF] OrderSend FAIL: err=%d retcode=%d", GetLastError(), res.retcode);
         return false;
      }
   }

   if(res.retcode == TRADE_RETCODE_DONE || res.retcode == TRADE_RETCODE_PLACED)
   {
      g_tradesToday++;

      // Register time-based exit
      if(InpTPMode == 0 || InpTPMode == 2)
      {
         g_holdCountdown = InpHoldBars;
      }

      PrintFormat("[SGF] %s %.2f @ %.5f | SL=%.5f TP=%.5f | %s",
                  direction==0?"BUY":"SELL", lot, res.price, sl, tp, comment);
      return true;
   }

   PrintFormat("[SGF] Order retcode=%d", res.retcode);
   return false;
}

//+------------------------------------------------------------------+
//| Check if current bar[1] is in a fix entry window                  |
//+------------------------------------------------------------------+
int CheckFixWindow(MqlDateTime &dt)
{
   // Returns: 0=no fix, 1=AM fix, 2=PM fix

   if(InpAMFix)
   {
      if(dt.hour == InpAM_EntryH && dt.min == InpAM_EntryM)
         return 1;
   }

   if(InpPMFix)
   {
      if(dt.hour == InpPM_EntryH && dt.min == InpPM_EntryM)
         return 2;
   }

   return 0;
}

//+------------------------------------------------------------------+
//| Expert tick function                                              |
//+------------------------------------------------------------------+
void OnTick()
{
   if(InpKillSwitch) return;

   // New bar check
   datetime barTime = iTime(_Symbol, PERIOD_CURRENT, 0);
   if(barTime == g_lastBar) return;
   g_lastBar = barTime;

   // Day reset
   MqlDateTime dt;
   TimeToStruct(barTime, dt);
   if(dt.day_of_year != g_lastTradeDay)
   {
      g_lastTradeDay = dt.day_of_year;
      g_tradesToday = 0;
      g_dayStartBalance = AccountInfoDouble(ACCOUNT_BALANCE);
   }

   // Process pending time-based exits first
   ProcessExits();

   // Pre-flight checks
   if(g_tradesToday >= InpMaxPerDay) return;
   if(CountPositions() > 0) return;
   if(IsDailyDDExceeded()) return;

   // Day filters
   if(InpSkipFriday && dt.day_of_week == 5) return;
   if(InpSkipMonday && dt.day_of_week == 1) return;
   if(InpSkipTuesday && dt.day_of_week == 2) return;
   if(InpSkipWednesday && dt.day_of_week == 3) return;
   if(InpSkipThursday && dt.day_of_week == 4) return;

   // Check if we're in a fix window
   // Use bar[1] time for signal (closed bar)
   datetime bar1Time = iTime(_Symbol, PERIOD_CURRENT, 1);
   MqlDateTime dt1;
   TimeToStruct(bar1Time, dt1);

   int fixSignal = CheckFixWindow(dt1);
   if(fixSignal == 0) return;

   // ATR for SL
   double atr[];
   ArraySetAsSeries(atr, true);
   if(CopyBuffer(g_hATR, 0, 1, 1, atr) < 1) return;

   if(InpMinATR > 0 && atr[0] < InpMinATR * _Point) return;

   double slDist = atr[0] * InpATR_SL_Mult;

   // SL bounds
   if(slDist < InpMinSLPoints * _Point)
      slDist = InpMinSLPoints * _Point;
   if(slDist > InpMaxSLPoints * _Point)
      return;

   // Direction logic
   string fixName = (fixSignal == 1) ? "AM_Fix" : "PM_Fix";

   if(InpDirection == 0) // Buy only
   {
      OpenTrade(0, slDist, StringFormat("SGF|%s|ATR=%.1f", fixName, atr[0]/_Point));
   }
   else if(InpDirection == 1) // Sell only
   {
      OpenTrade(1, slDist, StringFormat("SGF|%s|ATR=%.1f", fixName, atr[0]/_Point));
   }
   else // Both — buy AM, sell PM (hypothesis: buy into fix demand, sell after)
   {
      if(fixSignal == 1)
         OpenTrade(0, slDist, StringFormat("SGF|AM_Fix_BUY|ATR=%.1f", atr[0]/_Point));
      else
         OpenTrade(1, slDist, StringFormat("SGF|PM_Fix_SELL|ATR=%.1f", atr[0]/_Point));
   }
}

//+------------------------------------------------------------------+
//| Tester - time-based exit needs OnTimer or bar tracking            |
//| Since we use new-bar logic, ProcessExits handles bar countdown    |
//+------------------------------------------------------------------+
double OnTester()
{
   double pf = TesterStatistics(STAT_PROFIT_FACTOR);
   double trades = TesterStatistics(STAT_TRADES);
   if(trades < 30) return 0;
   return pf * MathSqrt(trades);
}
//+------------------------------------------------------------------+
