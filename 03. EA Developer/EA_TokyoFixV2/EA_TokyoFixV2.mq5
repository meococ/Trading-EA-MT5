//+------------------------------------------------------------------+
//| EA_TokyoFixV2.mq5 — Post-Fix Reversal (Yen Strengthening)       |
//| Symbol: USDJPY  |  Period: M15  |  Style: Fix reversal           |
//|                                                                   |
//| EDGE HYPOTHESIS (v2.0):                                           |
//| After Tokyo Fix 9:55 JST (h2:55 GMT+2), USD systematically       |
//| DEPRECIATES as dealer inventory rebalances. This pattern exists   |
//| on ALL trading days, not just Gotobi.                             |
//|                                                                   |
//| v1.0 FAILED because: tried to BUY at fix (pre-fix direction).    |
//| v2.0 FIX: SELL USDJPY AFTER fix (post-fix reversal).             |
//|                                                                   |
//| ACADEMIC BASIS:                                                   |
//| Krohn et al. 2024, J. Finance — 21-year study shows:             |
//|   USD appreciates before Tokyo Fix                                |
//|   USD depreciates after Tokyo Fix (systematic reversal)           |
//| This W-shaped pattern is structural (dealer inventory mgmt).      |
//|                                                                   |
//| COUNTERPARTY: Banks that accumulated USD pre-fix now offload      |
//|                                                                   |
//| DESIGN:                                                           |
//| - SELL USDJPY post-fix (bar[1] at h3:00 GMT+2)                  |
//| - Skip Gotobi days (covered by EA_Gotobi which BUYS)             |
//| - Time exit after N bars or ATR target                            |
//| - No overlap with Gotobi, ITSM, LondonNY (all h15+ GMT+2)       |
//|                                                                   |
//| Max | 2026-04-12 | v2.0                                         |
//+------------------------------------------------------------------+
#property copyright "Max - EA_TokyoFixV2 v2.0"
#property version   "2.00"
#property strict

#include <Trade\Trade.mqh>

//+------------------------------------------------------------------+
//| Input Parameters                                                  |
//+------------------------------------------------------------------+
input group "=== General ==="
input ulong    InpMagic         = 601202;    // Magic Number
input int      InpDeviation     = 30;        // Max Slippage (pts)
input bool     InpKillSwitch    = false;     // Kill Switch

input group "=== Post-Fix Entry (Server Time GMT+2) ==="
input int      InpEntryHour     = 3;         // Entry hour (post-fix)
input int      InpEntryMinute   = 0;         // Entry minute (0 or 15 for M15)
input int      InpHoldBars      = 6;         // Hold for N bars (M15: 6=1.5hr)
input int      InpDeadlineHour  = 6;         // Force close hour
input int      InpDeadlineMin   = 0;         // Force close minute

input group "=== Direction ==="
input int      InpDirection     = -1;        // Trade direction: 1=Long, -1=Short(post-fix), 0=Both
input int      InpEMAPeriod     = 0;         // EMA trend filter (0=disabled)

input group "=== Gotobi Filter ==="
input bool     InpSkipGotobi    = true;      // Skip Gotobi days (already traded by EA_Gotobi)

input group "=== Day Filters ==="
input bool     InpMon           = false;     // Trade Monday (false = weekend gap risk)
input bool     InpTue           = true;      // Trade Tuesday
input bool     InpWed           = true;      // Trade Wednesday
input bool     InpThu           = true;      // Trade Thursday
input bool     InpFri           = true;      // Trade Friday

input group "=== Risk Management ==="
input double   InpRiskPct       = 0.40;      // Risk per trade (%)
input double   InpMaxLot        = 0.50;      // Max lot
input double   InpATRMultSL     = 1.5;       // SL = ATR x this
input int      InpATRPeriod     = 14;        // ATR Period
input double   InpRRRatio       = 1.0;       // TP = SL x this (0=time exit only)
input double   InpDailyDDPct    = 2.0;       // Daily DD kill (%)

input group "=== Pre-Fix Momentum Filter ==="
input bool     InpRequirePreFix = true;      // Require pre-fix USD appreciation
input double   InpMinPreFixATR  = 0.2;       // Min pre-fix move (ATR mult) for signal
input int      InpPreFixLookback= 8;         // Pre-fix lookback bars (M15: 8=2hr before fix)

input group "=== Datalog ==="
input bool     InpDatalog       = true;      // Enable CSV signal log

//+------------------------------------------------------------------+
//| Globals                                                           |
//+------------------------------------------------------------------+
CTrade         g_trade;
int            g_hATR;
int            g_hEMA;
datetime       g_lastBar;
datetime       g_todayDate;
double         g_dayStartBal;
bool           g_tradedToday;
int            g_logHandle;
int            g_barsHeld;
ulong          g_activeTicket;

//+------------------------------------------------------------------+
int OnInit()
{
   if(InpKillSwitch) { Print("[TFixV2] Kill switch ON"); return INIT_SUCCEEDED; }

   g_trade.SetExpertMagicNumber(InpMagic);
   g_trade.SetDeviationInPoints(InpDeviation);
   g_trade.SetTypeFilling(ORDER_FILLING_FOK);

   g_hATR = iATR(_Symbol, PERIOD_CURRENT, InpATRPeriod);
   g_hEMA = (InpEMAPeriod > 0) ? iMA(_Symbol, PERIOD_CURRENT, InpEMAPeriod, 0, MODE_EMA, PRICE_CLOSE)
                                : INVALID_HANDLE;

   if(g_hATR == INVALID_HANDLE)
   { Print("[TFixV2] FATAL: ATR init failed"); return INIT_FAILED; }

   g_lastBar      = 0;
   g_todayDate    = 0;
   g_dayStartBal  = AccountInfoDouble(ACCOUNT_BALANCE);
   g_tradedToday  = false;
   g_barsHeld     = 0;
   g_activeTicket = 0;

   if(InpDatalog)
   {
      string fname = "TFixV2_datalog_" + _Symbol + ".csv";
      g_logHandle = FileOpen(fname, FILE_WRITE|FILE_CSV|FILE_COMMON, ',');
      if(g_logHandle != INVALID_HANDLE)
         FileWrite(g_logHandle,
            "Time","Signal","Price","ATR","PreFixMove","SL","TP","Lot","DoW","DayOfMonth","Reason");
   }

   PrintFormat("[TFixV2] Init OK: %s %s Magic=%d Entry=%02d:%02d Hold=%d Dir=%d SkipGotobi=%d",
               _Symbol, EnumToString(_Period), InpMagic, InpEntryHour, InpEntryMinute,
               InpHoldBars, InpDirection, InpSkipGotobi);
   return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   if(g_hATR != INVALID_HANDLE) IndicatorRelease(g_hATR);
   if(g_hEMA != INVALID_HANDLE) IndicatorRelease(g_hEMA);
   if(g_logHandle != INVALID_HANDLE) FileClose(g_logHandle);
}

//+------------------------------------------------------------------+
bool IsTradingDay(int dow)
{
   switch(dow)
   {
      case 1: return InpMon;
      case 2: return InpTue;
      case 3: return InpWed;
      case 4: return InpThu;
      case 5: return InpFri;
      default: return false;
   }
}

//+------------------------------------------------------------------+
// Check if today is a Gotobi day (5th, 10th, 15th, 20th, 25th, last business day)
bool IsGotobiDay()
{
   MqlDateTime dt;
   TimeToStruct(TimeCurrent(), dt);
   int dom = dt.day;

   // Standard Gotobi: 5, 10, 15, 20, 25
   if(dom == 5 || dom == 10 || dom == 15 || dom == 20 || dom == 25)
      return true;

   // End of month: check if this is the last business day
   // Simple check: if day >= 28 and next business day is in next month
   if(dom >= 28)
   {
      // Check days remaining in month
      int daysInMonth;
      switch(dt.mon)
      {
         case 2:  daysInMonth = ((dt.year % 4 == 0 && (dt.year % 100 != 0 || dt.year % 400 == 0)) ? 29 : 28); break;
         case 4: case 6: case 9: case 11: daysInMonth = 30; break;
         default: daysInMonth = 31;
      }

      // If it's the last weekday of the month
      for(int d = dom; d <= daysInMonth; d++)
      {
         // Check if there's another weekday after today
         if(d > dom)
         {
            datetime futureDate = StringToTime(StringFormat("%04d.%02d.%02d", dt.year, dt.mon, d));
            MqlDateTime futDt;
            TimeToStruct(futureDate, futDt);
            if(futDt.day_of_week >= 1 && futDt.day_of_week <= 5)
               return false; // Another weekday exists after today in this month
         }
      }
      return true; // Today is the last weekday of the month
   }

   return false;
}

//+------------------------------------------------------------------+
int CountMyPositions()
{
   int count = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0) continue;
      if(PositionGetInteger(POSITION_MAGIC) == (long)InpMagic &&
         PositionGetString(POSITION_SYMBOL) == _Symbol)
         count++;
   }
   return count;
}

//+------------------------------------------------------------------+
double CalcLotSize(double slPoints)
{
   if(slPoints <= 0) return 0;
   double balance  = AccountInfoDouble(ACCOUNT_BALANCE);
   double riskAmt  = balance * InpRiskPct / 100.0;
   double tickSize = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   double tickVal  = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
   double point    = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   if(tickSize == 0 || tickVal == 0 || point == 0) return 0;
   double pointVal = tickVal * point / tickSize;
   double lot = riskAmt / (slPoints * pointVal);
   double minLot  = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double maxLot  = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   double lotStep = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   lot = MathMax(lot, minLot);
   lot = MathMin(lot, InpMaxLot);
   lot = MathMin(lot, maxLot);
   if(lotStep > 0) lot = MathFloor(lot / lotStep) * lotStep;
   return NormalizeDouble(lot, 2);
}

//+------------------------------------------------------------------+
// Measure pre-fix USD movement (USDJPY up = USD appreciation)
double GetPreFixMove()
{
   double close1 = iClose(_Symbol, PERIOD_CURRENT, 1);
   int lookback = InpPreFixLookback + 1; // +1 because we measure from bar[N] to bar[1]
   if(lookback > Bars(_Symbol, PERIOD_CURRENT)) return 0;
   double openAtStart = iOpen(_Symbol, PERIOD_CURRENT, lookback);
   return close1 - openAtStart;
}

//+------------------------------------------------------------------+
void CloseAllPositions()
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0) continue;
      if(PositionGetInteger(POSITION_MAGIC) == (long)InpMagic &&
         PositionGetString(POSITION_SYMBOL) == _Symbol)
      {
         g_trade.PositionClose(ticket);
      }
   }
   g_barsHeld     = 0;
   g_activeTicket = 0;
}

//+------------------------------------------------------------------+
void OnTick()
{
   if(InpKillSwitch) return;

   datetime barTime = iTime(_Symbol, PERIOD_CURRENT, 0);
   if(barTime == g_lastBar) return;
   g_lastBar = barTime;

   MqlDateTime dt;
   TimeToStruct(barTime, dt);
   datetime today = StringToTime(StringFormat("%04d.%02d.%02d", dt.year, dt.mon, dt.day));

   // Day reset
   if(today != g_todayDate)
   {
      g_todayDate   = today;
      g_tradedToday = false;
      g_dayStartBal = AccountInfoDouble(ACCOUNT_BALANCE);
   }

   //=== Manage existing positions ===
   if(CountMyPositions() > 0)
   {
      g_barsHeld++;

      // Deadline force close
      int nowMin = dt.hour * 60 + dt.min;
      int deadMin = InpDeadlineHour * 60 + InpDeadlineMin;
      if(nowMin >= deadMin)
      {
         PrintFormat("[TFixV2] Deadline close at %02d:%02d after %d bars", dt.hour, dt.min, g_barsHeld);
         CloseAllPositions();
         return;
      }

      // Time-based exit (if no TP set)
      if(InpRRRatio <= 0 && g_barsHeld >= InpHoldBars)
      {
         PrintFormat("[TFixV2] Time exit after %d bars", g_barsHeld);
         CloseAllPositions();
         return;
      }
      return;
   }

   //=== Entry logic ===
   if(g_tradedToday) return;

   // Daily DD kill
   double ddPct = (g_dayStartBal > 0)
                  ? (g_dayStartBal - AccountInfoDouble(ACCOUNT_EQUITY)) / g_dayStartBal * 100.0
                  : 0;
   if(ddPct >= InpDailyDDPct) return;

   // Day filter
   if(!IsTradingDay(dt.day_of_week)) return;

   // Gotobi filter
   if(InpSkipGotobi && IsGotobiDay())
   {
      LogSignal(barTime, "SKIP", 0, 0, 0, 0, 0, 0, dt.day_of_week, dt.day, "GOTOBI_DAY");
      return;
   }

   // Fix window check
   if(dt.hour != InpEntryHour || dt.min != InpEntryMinute)
      return;

   // Read ATR
   double atr[];
   if(CopyBuffer(g_hATR, 0, 1, 1, atr) < 1) return;
   if(atr[0] <= 0) return;

   double point = SymbolInfoDouble(_Symbol, SYMBOL_POINT);

   // Pre-fix momentum filter
   double preFixMove = GetPreFixMove();
   double moveATR = preFixMove / atr[0]; // Positive = USD appreciated = USDJPY went up

   if(InpRequirePreFix)
   {
      // For post-fix SHORT: we want pre-fix USD appreciation (USDJPY up)
      // This confirms the W-pattern: up before fix, down after fix
      if(InpDirection <= 0 && moveATR < InpMinPreFixATR)
      {
         LogSignal(barTime, "SKIP", 0, atr[0], preFixMove, 0, 0, 0,
                   dt.day_of_week, dt.day, "NO_PREFIX_UP");
         return;
      }
      // For post-fix LONG: we want pre-fix USD depreciation (USDJPY down)
      if(InpDirection > 0 && moveATR > -InpMinPreFixATR)
      {
         LogSignal(barTime, "SKIP", 0, atr[0], preFixMove, 0, 0, 0,
                   dt.day_of_week, dt.day, "NO_PREFIX_DOWN");
         return;
      }
   }

   // EMA trend filter
   if(InpEMAPeriod > 0 && g_hEMA != INVALID_HANDLE)
   {
      double ema[];
      if(CopyBuffer(g_hEMA, 0, 1, 1, ema) < 1) return;
      double close1 = iClose(_Symbol, PERIOD_CURRENT, 1);

      // For shorts: don't short in strong uptrend (optional safety)
      // For longs: don't buy in strong downtrend
   }

   // Determine direction
   int signal = InpDirection;
   if(signal == 0)
   {
      // Both directions: use pre-fix move to decide
      signal = (preFixMove > 0) ? -1 : 1; // Fade the pre-fix move
   }

   // Calculate SL/TP
   int    digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
   double slDist = atr[0] * InpATRMultSL;
   double price, sl, tp;

   if(signal > 0) // BUY
   {
      price = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
      sl    = NormalizeDouble(price - slDist, digits);
      tp    = (InpRRRatio > 0) ? NormalizeDouble(price + slDist * InpRRRatio, digits) : 0;
   }
   else // SELL
   {
      price = SymbolInfoDouble(_Symbol, SYMBOL_BID);
      sl    = NormalizeDouble(price + slDist, digits);
      tp    = (InpRRRatio > 0) ? NormalizeDouble(price - slDist * InpRRRatio, digits) : 0;
   }

   // Check stop level
   double stopLevel = SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL) * point;
   if(MathAbs(price - sl) < stopLevel)
   {
      sl = (signal > 0) ? NormalizeDouble(price - stopLevel - point, digits)
                        : NormalizeDouble(price + stopLevel + point, digits);
   }

   // Lot size
   double slPoints = MathAbs(price - sl) / point;
   double lot = CalcLotSize(slPoints);
   if(lot <= 0)
   {
      LogSignal(barTime, "SKIP", price, atr[0], preFixMove, sl, 0, 0,
                dt.day_of_week, dt.day, "LOT_ZERO");
      return;
   }

   // Execute
   ENUM_ORDER_TYPE orderType = (signal > 0) ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
   string comment = StringFormat("TFV2|PFM=%.1f|ATR=%.1f|D=%d",
                                 preFixMove / point, atr[0] / point, dt.day);

   bool ok = g_trade.PositionOpen(_Symbol, orderType, lot, price, sl, tp, comment);
   if(ok)
   {
      g_tradedToday = true;
      g_barsHeld    = 0;
      PrintFormat("[TFixV2] %s %.2f @ %.5f SL=%.5f TP=%.5f PreFix=%.1f ATR=%.1f DoW=%d Dom=%d",
                  signal > 0 ? "BUY" : "SELL", lot, price, sl, tp,
                  preFixMove / point, atr[0] / point, dt.day_of_week, dt.day);
      LogSignal(barTime, signal > 0 ? "BUY" : "SELL", price, atr[0], preFixMove,
                sl, tp, lot, dt.day_of_week, dt.day, "EXECUTED");
   }
}

//+------------------------------------------------------------------+
void LogSignal(datetime time, string sig, double price, double atr,
               double move, double sl, double tp, double lot, int dow, int dom, string reason)
{
   if(!InpDatalog || g_logHandle == INVALID_HANDLE) return;
   int digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
   FileWrite(g_logHandle,
      TimeToString(time, TIME_DATE|TIME_MINUTES),
      sig, DoubleToString(price, digits),
      DoubleToString(atr, digits), DoubleToString(move, digits),
      DoubleToString(sl, digits), DoubleToString(tp, digits),
      DoubleToString(lot, 2),
      IntegerToString(dow), IntegerToString(dom), reason);
   FileFlush(g_logHandle);
}
//+------------------------------------------------------------------+
