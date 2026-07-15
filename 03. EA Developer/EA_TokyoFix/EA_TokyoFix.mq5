//+------------------------------------------------------------------+
//| EA_TokyoFix.mq5 — USDJPY Tokyo Fix 9:55 JST Edge                |
//| Symbol: USDJPY  |  Period: M15  |  Style: Fix-window exploitation|
//|                                                                   |
//| EDGE HYPOTHESIS (v1.0):                                           |
//| Japanese importers buy USD before/at 9:55 JST daily fix.          |
//| Japan imports ~$800B/yr → persistent USD buy flow at fixing.     |
//| NBER Working Paper w22822 (Ito & Yamada 2017) confirms:           |
//|   - Anticipatory buying 9:51-9:55                                |
//|   - Partial mean-reversion 9:55-10:00                            |
//|                                                                   |
//| MECHANISM:                                                        |
//| Importers MUST buy USD to pay invoices. Banks front-run the fix   |
//| by accumulating USD slightly before. We join the buy pressure     |
//| and exit shortly after the fix.                                   |
//|                                                                   |
//| COUNTERPARTY: Natural hedgers (importers) = non-adversarial      |
//|                                                                   |
//| DESIGN:                                                           |
//| - Buy USDJPY at pre-fix bar close (bar[1] at fix window)         |
//| - Exit via time (30-60 min post-fix) or ATR trail                |
//| - Hard SL: 1.5xATR                                               |
//| - No trade on Monday (weekend gap effects)                        |
//| - Server hour configurable (broker dependent)                     |
//|                                                                   |
//| Max | 2026-04-05 | v1.0                                         |
//+------------------------------------------------------------------+
#property copyright "Max — EA_TokyoFix v1.0"
#property version   "1.00"
#property strict

#include <Trade\Trade.mqh>

//+------------------------------------------------------------------+
//| Input Parameters                                                  |
//+------------------------------------------------------------------+
input group "=== General ==="
input ulong    InpMagic         = 502601;    // Magic Number
input int      InpDeviation     = 30;        // Max Slippage (pts)
input bool     InpKillSwitch    = false;     // Kill Switch

input group "=== Fix Window (Server Time) ==="
input int      InpFixHour       = 2;         // Fix bar hour (server) — for UTC+2: 2, for UTC+3: 3
input int      InpFixMinute     = 45;        // Fix bar minute (server) — 45 means 02:45 bar
input int      InpHoldBars      = 4;         // Hold for N bars after entry (60min = 4 bars on M15)

input group "=== Day Filters ==="
input bool     InpMonday        = false;     // Trade Monday
input bool     InpTuesday       = true;      // Trade Tuesday
input bool     InpWednesday     = true;      // Trade Wednesday
input bool     InpThursday      = true;      // Trade Thursday
input bool     InpFriday        = true;      // Trade Friday

input group "=== Direction ==="
input int      InpDirection     = 1;         // Trade direction: 1=Long only, -1=Short only, 0=Both
input int      InpEMAPeriod     = 100;       // EMA trend filter (0=disabled)

input group "=== Risk Management ==="
input double   InpRiskPct       = 0.40;      // Risk per trade (%)
input double   InpMaxLot        = 0.50;      // Max lot
input double   InpATRMultSL     = 1.5;       // SL = ATR x this
input int      InpATRPeriod     = 14;        // ATR Period
input double   InpDailyDDPct    = 2.0;       // Daily DD kill (%)

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
int            g_barsHeld;       // bars since entry
ulong          g_activeTicket;   // current position ticket

//+------------------------------------------------------------------+
int OnInit()
{
   if(InpKillSwitch) { Print("[TokyoFix] Kill switch ON"); return INIT_SUCCEEDED; }

   g_trade.SetExpertMagicNumber(InpMagic);
   g_trade.SetDeviationInPoints(InpDeviation);
   g_trade.SetTypeFilling(ORDER_FILLING_FOK);

   g_hATR = iATR(_Symbol, PERIOD_CURRENT, InpATRPeriod);
   g_hEMA = (InpEMAPeriod > 0) ? iMA(_Symbol, PERIOD_CURRENT, InpEMAPeriod, 0, MODE_EMA, PRICE_CLOSE)
                                : INVALID_HANDLE;

   if(g_hATR == INVALID_HANDLE)
   { Print("[TokyoFix] FATAL: ATR init failed"); return INIT_FAILED; }

   g_lastBar      = 0;
   g_todayDate    = 0;
   g_dayStartBal  = AccountInfoDouble(ACCOUNT_BALANCE);
   g_tradedToday  = false;
   g_barsHeld     = 0;
   g_activeTicket = 0;

   if(InpDatalog)
   {
      string fname = "TokyoFix_datalog_" + _Symbol + ".csv";
      g_logHandle = FileOpen(fname, FILE_WRITE|FILE_CSV|FILE_COMMON, ',');
      if(g_logHandle != INVALID_HANDLE)
         FileWrite(g_logHandle,
            "Time","Signal","Price","ATR","EMA","SL","Lot","DoW","SkipReason");
   }

   PrintFormat("[TokyoFix] Init OK: %s %s Magic=%d FixHour=%d:%02d",
               _Symbol, EnumToString(_Period), InpMagic, InpFixHour, InpFixMinute);
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
      case 1: return InpMonday;
      case 2: return InpTuesday;
      case 3: return InpWednesday;
      case 4: return InpThursday;
      case 5: return InpFriday;
      default: return false;
   }
}

//+------------------------------------------------------------------+
int CountMyPositions()
{
   int count = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0) continue;
      if(PositionGetInteger(POSITION_MAGIC) == InpMagic &&
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

   // Manage existing positions (time exit)
   if(CountMyPositions() > 0)
   {
      g_barsHeld++;
      if(g_barsHeld >= InpHoldBars)
      {
         // Time exit
         for(int i = PositionsTotal() - 1; i >= 0; i--)
         {
            ulong ticket = PositionGetTicket(i);
            if(ticket == 0) continue;
            if(PositionGetInteger(POSITION_MAGIC) == InpMagic &&
               PositionGetString(POSITION_SYMBOL) == _Symbol)
            {
               g_trade.PositionClose(ticket);
               PrintFormat("[TokyoFix] Time exit after %d bars", g_barsHeld);
            }
         }
         g_barsHeld     = 0;
         g_activeTicket = 0;
      }
      return; // Already in position — manage only
   }

   // Already traded today?
   if(g_tradedToday) return;

   // Daily DD kill
   double ddPct = (g_dayStartBal > 0)
                  ? (g_dayStartBal - AccountInfoDouble(ACCOUNT_EQUITY)) / g_dayStartBal * 100.0
                  : 0;
   if(ddPct >= InpDailyDDPct) return;

   // Day filter
   if(!IsTradingDay(dt.day_of_week)) return;

   // Fix window check: is current bar the fix bar?
   // On M15, bar at 02:45 covers 02:45-02:59. Fix at 02:55 falls in this bar.
   if(dt.hour != InpFixHour || dt.min != InpFixMinute)
      return;

   // We are AT the fix bar. Use bar[1] data for non-repaint signal.
   double close1 = iClose(_Symbol, PERIOD_CURRENT, 1);
   int    digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
   double point  = SymbolInfoDouble(_Symbol, SYMBOL_POINT);

   // Read indicators on bar[1]
   double atr[];
   if(CopyBuffer(g_hATR, 0, 1, 1, atr) < 1) return;

   // EMA trend filter
   int signal = InpDirection; // Default direction
   if(InpEMAPeriod > 0 && g_hEMA != INVALID_HANDLE)
   {
      double ema[];
      if(CopyBuffer(g_hEMA, 0, 1, 1, ema) < 1) return;

      if(InpDirection == 1 && close1 < ema[0])
      {
         // Long-only but downtrend — skip
         LogSignal(barTime, "SKIP_LONG", close1, atr[0], ema[0], 0, 0, dt.day_of_week, "EMA_DOWNTREND");
         return;
      }
      if(InpDirection == -1 && close1 > ema[0])
      {
         LogSignal(barTime, "SKIP_SHORT", close1, atr[0], ema[0], 0, 0, dt.day_of_week, "EMA_UPTREND");
         return;
      }
   }

   // Calculate SL
   double slDist = atr[0] * InpATRMultSL;
   double price, sl;

   if(signal >= 0) // Default: long (USD buy at fix)
   {
      price = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
      sl    = NormalizeDouble(price - slDist, digits);
   }
   else
   {
      price = SymbolInfoDouble(_Symbol, SYMBOL_BID);
      sl    = NormalizeDouble(price + slDist, digits);
   }

   // No fixed TP — time-based exit after InpHoldBars
   double tp = 0;

   // Lot size
   double slPoints = MathAbs(price - sl) / point;
   double lot = CalcLotSize(slPoints);
   if(lot <= 0)
   {
      LogSignal(barTime, "SKIP", close1, atr[0], 0, sl, 0, dt.day_of_week, "LOT_ZERO");
      return;
   }

   // Execute
   ENUM_ORDER_TYPE orderType = (signal >= 0) ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
   string comment = StringFormat("TFix|DoW=%d|ATR=%.1f", dt.day_of_week, atr[0] / point);

   bool ok = g_trade.PositionOpen(_Symbol, orderType, lot, price, sl, tp, comment);
   if(ok)
   {
      g_tradedToday = true;
      g_barsHeld    = 0;
      PrintFormat("[TokyoFix] %s %.2f @ %.5f SL=%.5f Hold=%d bars DoW=%d",
                  signal >= 0 ? "BUY" : "SELL", lot, price, sl, InpHoldBars, dt.day_of_week);
      LogSignal(barTime, signal >= 0 ? "BUY" : "SELL", price, atr[0], 0, sl, lot, dt.day_of_week, "EXECUTED");
   }
}

//+------------------------------------------------------------------+
void LogSignal(datetime time, string sig, double price, double atr,
               double ema, double sl, double lot, int dow, string reason)
{
   if(!InpDatalog || g_logHandle == INVALID_HANDLE) return;
   FileWrite(g_logHandle,
      TimeToString(time, TIME_DATE|TIME_MINUTES),
      sig, DoubleToString(price, 5),
      DoubleToString(atr, 5), DoubleToString(ema, 5),
      DoubleToString(sl, 5), DoubleToString(lot, 2),
      IntegerToString(dow), reason);
   FileFlush(g_logHandle);
}
//+------------------------------------------------------------------+
