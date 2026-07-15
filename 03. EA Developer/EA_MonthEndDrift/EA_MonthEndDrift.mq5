//+------------------------------------------------------------------+
//| EA_MonthEndDrift.mq5 — GPIF Month-End Rebalancing Drift          |
//| Symbol: USDJPY+  |  Period: M15  |  Style: Swing (2-3 days)      |
//|                                                                   |
//| EDGE HYPOTHESIS:                                                  |
//| GPIF (>200 trl JPY) rebalances to target 24.37% foreign equity.  |
//| When foreign equities outperform JGB in a month, GPIF sells      |
//| foreign assets -> buys JPY -> USDJPY drops. Flow 450-540B JPY    |
//| concentrated in last 3 business days, peak at Tokyo fix 3pm JST. |
//|                                                                   |
//| IMPLEMENTATION:                                                   |
//| - Detect last 3 business days of month                           |
//| - Measure monthly equity performance proxy (USDJPY trend as      |
//|   proxy for risk-on/equity-up months)                             |
//| - Short USDJPY during Tokyo afternoon session (05:00-08:00 UTC)  |
//| - Hold until session end or SL/TP                                 |
//|                                                                   |
//| COUNTERPARTY: GPIF mechanically rebalances regardless of price.   |
//| Harvey et al. (2023): pension fund rebalancing costs $16B/yr.     |
//| Banti et al.: calendar anomalies in FX month-end.                 |
//|                                                                   |
//| SIGNALS ON BAR[1] ONLY — no repaint, no lookahead.               |
//| Max | 2026-04-12 | v1.0                                          |
//+------------------------------------------------------------------+
#property copyright "Max — EA_MonthEndDrift v1.0"
#property link      ""
#property version   "1.00"
#property strict

//+------------------------------------------------------------------+
//| Input Parameters                                                  |
//+------------------------------------------------------------------+
input group "=== General ==="
input ulong    InpMagic         = 208001;     // Magic Number
input int      InpDeviation     = 30;         // Max Slippage (pts)
input bool     InpKillSwitch    = false;      // Kill Switch

input group "=== Month-End Window ==="
input int      InpLastDays      = 3;          // Last N business days of month
input int      InpEntryHourStart= 5;          // Entry window start (UTC/server)
input int      InpEntryHourEnd  = 8;          // Entry window end (UTC/server)
input int      InpExitHour      = 8;          // Force exit hour (UTC/server)

input group "=== Monthly Trend Filter ==="
input bool     InpUseTrendFilter= true;       // Require month-positive trend
input int      InpTrendLookback = 20;         // Bars to measure monthly trend (D1)
input double   InpMinTrendPips  = 50.0;       // Min monthly move (pips) for signal

input group "=== Trade Management ==="
input double   InpSLPips        = 20.0;       // Stop loss (pips)
input double   InpTPPips        = 30.0;       // Take profit (pips)
input int      InpMaxPerWindow  = 1;          // Max trades per month-end window

input group "=== Risk ==="
input double   InpRiskPct       = 0.50;       // Risk per trade (% balance)
input double   InpMaxLot        = 1.0;        // Max lot
input double   InpDailyDD       = 4.0;        // Daily DD kill (%)

//+------------------------------------------------------------------+
//| Globals                                                           |
//+------------------------------------------------------------------+
datetime g_lastBar       = 0;
int      g_tradesWindow  = 0;     // Trades in current month-end window
int      g_lastMonth     = -1;    // Track month changes
double   g_dayStartBal   = 0;
int      g_lastTradeDay  = -1;

//+------------------------------------------------------------------+
//| Expert initialization                                             |
//+------------------------------------------------------------------+
int OnInit()
{
   if(StringFind(_Symbol, "JPY") < 0)
      PrintFormat("[MED] WARNING: Designed for USDJPY, running on %s", _Symbol);

   g_dayStartBal = AccountInfoDouble(ACCOUNT_BALANCE);

   PrintFormat("[MED] EA_MonthEndDrift v1.00 | Symbol=%s | TF=%s | Magic=%d",
               _Symbol, EnumToString(_Period), InpMagic);
   PrintFormat("[MED] Window: last %d biz days | Entry h%d-h%d | Exit h%d",
               InpLastDays, InpEntryHourStart, InpEntryHourEnd, InpExitHour);
   return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
void OnDeinit(const int reason) { }

//+------------------------------------------------------------------+
double PipSize()
{
   return (_Digits == 3 || _Digits == 5) ? _Point * 10 : _Point;
}

//+------------------------------------------------------------------+
//| Check if today is in the last N business days of the month        |
//+------------------------------------------------------------------+
bool IsMonthEndWindow(MqlDateTime &dt)
{
   // Get last day of current month
   int year  = dt.year;
   int month = dt.mon;
   int lastDay;

   if(month == 2)
      lastDay = ((year % 4 == 0 && year % 100 != 0) || year % 400 == 0) ? 29 : 28;
   else if(month == 4 || month == 6 || month == 9 || month == 11)
      lastDay = 30;
   else
      lastDay = 31;

   // Count business days from today to end of month
   int bizDaysLeft = 0;
   for(int d = dt.day + 1; d <= lastDay; d++)
   {
      MqlDateTime tmp;
      tmp.year = year;
      tmp.mon  = month;
      tmp.day  = d;
      tmp.hour = 12;
      tmp.min  = 0;
      tmp.sec  = 0;
      datetime t = StructToTime(tmp);
      MqlDateTime check;
      TimeToStruct(t, check);

      // 0=Sunday, 6=Saturday
      if(check.day_of_week >= 1 && check.day_of_week <= 5)
         bizDaysLeft++;
   }

   // We're in window if bizDaysLeft < InpLastDays
   // AND today is a business day
   return (bizDaysLeft < InpLastDays &&
           dt.day_of_week >= 1 && dt.day_of_week <= 5);
}

//+------------------------------------------------------------------+
//| Check monthly trend: has USDJPY risen this month?                 |
//| If it has, foreign equity likely outperformed -> GPIF sells       |
//| foreign -> buys JPY -> SHORT bias                                  |
//+------------------------------------------------------------------+
bool CheckMonthlyTrend(double &trendPips)
{
   trendPips = 0;
   if(!InpUseTrendFilter) return true;  // No filter = always trade

   // Get price at start of month vs now
   MqlDateTime dt;
   datetime now = iTime(_Symbol, PERIOD_CURRENT, 1);
   TimeToStruct(now, dt);

   // Find first business day of month
   dt.day = 1;
   dt.hour = 0;
   dt.min = 0;
   dt.sec = 0;
   datetime monthStart = StructToTime(dt);

   int barStart = iBarShift(_Symbol, PERIOD_CURRENT, monthStart, false);
   if(barStart <= 1) return false;

   double startPrice = iClose(_Symbol, PERIOD_CURRENT, barStart);
   double curPrice   = iClose(_Symbol, PERIOD_CURRENT, 1);

   if(startPrice <= 0) return false;

   trendPips = (curPrice - startPrice) / PipSize();

   // USDJPY up this month = risk-on = foreign equity up = GPIF will sell foreign
   // So we want to SHORT when USDJPY has risen (positive trend)
   return (trendPips >= InpMinTrendPips);
}

//+------------------------------------------------------------------+
//| Count positions                                                   |
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
//| Manage: force exit at exit hour                                   |
//+------------------------------------------------------------------+
void ManagePosition(MqlDateTime &dt)
{
   if(dt.hour < InpExitHour) return;

   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0) continue;
      if(PositionGetInteger(POSITION_MAGIC) != (long)InpMagic) continue;
      if(PositionGetString(POSITION_SYMBOL) != _Symbol) continue;

      long posType = PositionGetInteger(POSITION_TYPE);

      MqlTradeRequest req = {};
      MqlTradeResult  res = {};
      req.action   = TRADE_ACTION_DEAL;
      req.symbol   = _Symbol;
      req.volume   = PositionGetDouble(POSITION_VOLUME);
      req.type     = (posType == POSITION_TYPE_BUY) ? ORDER_TYPE_SELL : ORDER_TYPE_BUY;
      req.price    = (posType == POSITION_TYPE_BUY) ?
                     SymbolInfoDouble(_Symbol, SYMBOL_BID) :
                     SymbolInfoDouble(_Symbol, SYMBOL_ASK);
      req.deviation = (ulong)InpDeviation;
      req.magic     = InpMagic;
      req.position  = ticket;
      req.comment   = "MED|SessionExit";
      req.type_filling = ORDER_FILLING_FOK;

      if(!OrderSend(req, res))
      {
         req.type_filling = ORDER_FILLING_IOC;
         OrderSend(req, res);
      }

      if(res.retcode == TRADE_RETCODE_DONE || res.retcode == TRADE_RETCODE_PLACED)
         PrintFormat("[MED] SESSION EXIT | profit=%.2f",
                     PositionGetDouble(POSITION_PROFIT));
   }
}

//+------------------------------------------------------------------+
//| Lot calc                                                          |
//+------------------------------------------------------------------+
double CalcLot(double slPips)
{
   if(slPips <= 0) return 0;
   double slDist    = slPips * PipSize();
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
//| Daily DD check                                                    |
//+------------------------------------------------------------------+
bool IsDailyDDExceeded()
{
   if(g_dayStartBal <= 0) return false;
   double eq = AccountInfoDouble(ACCOUNT_EQUITY);
   return ((g_dayStartBal - eq) / g_dayStartBal * 100.0) >= InpDailyDD;
}

//+------------------------------------------------------------------+
//| Expert tick function                                              |
//+------------------------------------------------------------------+
void OnTick()
{
   if(InpKillSwitch) return;

   datetime barTime = iTime(_Symbol, PERIOD_CURRENT, 0);
   if(barTime == g_lastBar) return;
   g_lastBar = barTime;

   MqlDateTime dt;
   TimeToStruct(barTime, dt);

   // Day reset
   if(dt.day_of_year != g_lastTradeDay)
   {
      g_lastTradeDay = dt.day_of_year;
      g_dayStartBal = AccountInfoDouble(ACCOUNT_BALANCE);
   }

   // Month reset
   if(dt.mon != g_lastMonth)
   {
      g_lastMonth = dt.mon;
      g_tradesWindow = 0;
   }

   // Manage existing positions
   if(CountPositions() > 0)
   {
      ManagePosition(dt);
      return;
   }

   // Pre-flight
   if(g_tradesWindow >= InpMaxPerWindow) return;
   if(IsDailyDDExceeded()) return;

   // Check month-end window
   if(!IsMonthEndWindow(dt)) return;

   // Check entry hour
   if(dt.hour < InpEntryHourStart || dt.hour >= InpEntryHourEnd) return;

   // Check monthly trend filter
   double trendPips = 0;
   if(!CheckMonthlyTrend(trendPips)) return;

   //--- ENTRY: SHORT USDJPY (GPIF selling foreign -> buying JPY)
   double pip = PipSize();
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double sl  = bid + InpSLPips * pip;
   double tp  = bid - InpTPPips * pip;

   // Stop level check
   int stopLevel = (int)SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL);
   double minDist = stopLevel * _Point;
   if(InpSLPips * pip < minDist || InpTPPips * pip < minDist) return;

   double lot = CalcLot(InpSLPips);
   if(lot <= 0) return;

   int digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
   sl = NormalizeDouble(sl, digits);
   tp = NormalizeDouble(tp, digits);

   MqlTradeRequest req = {};
   MqlTradeResult  res = {};

   req.action    = TRADE_ACTION_DEAL;
   req.symbol    = _Symbol;
   req.volume    = lot;
   req.type      = ORDER_TYPE_SELL;
   req.price     = bid;
   req.sl        = sl;
   req.tp        = tp;
   req.deviation = (ulong)InpDeviation;
   req.magic     = InpMagic;
   req.comment   = StringFormat("MED|S|Trend=%.0f", trendPips);
   req.type_filling = ORDER_FILLING_FOK;

   if(!OrderSend(req, res))
   {
      req.type_filling = ORDER_FILLING_IOC;
      if(!OrderSend(req, res))
      {
         PrintFormat("[MED] OrderSend FAIL: err=%d retcode=%d",
                     GetLastError(), res.retcode);
         return;
      }
   }

   if(res.retcode == TRADE_RETCODE_DONE || res.retcode == TRADE_RETCODE_PLACED)
   {
      g_tradesWindow++;
      PrintFormat("[MED] SELL %.2f @ %.5f | SL=%.5f TP=%.5f | MonthTrend=%.0f pips",
                  lot, res.price, sl, tp, trendPips);
   }
}

//+------------------------------------------------------------------+
double OnTester()
{
   double pf = TesterStatistics(STAT_PROFIT_FACTOR);
   double trades = TesterStatistics(STAT_TRADES);
   if(trades < 15) return 0;
   return pf * MathSqrt(trades);
}
//+------------------------------------------------------------------+
