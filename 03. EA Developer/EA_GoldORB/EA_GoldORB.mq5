//+------------------------------------------------------------------+
//| EA_GoldORB.mq5 — Gold Opening Range Breakout (M15)               |
//| Symbol: XAUUSD  |  Period: M15  |  Style: Session breakout       |
//|                                                                   |
//| EDGE HYPOTHESIS (v1.0):                                           |
//| Asian session builds a consolidation range (00:00-09:00 server).  |
//| London-NY overlap liquidity breaks this range with momentum.      |
//| Entry on confirmed breakout with body/ATR filter.                 |
//|                                                                   |
//| MECHANISM:                                                        |
//| Asian session = low liquidity, retail-dominated, range builds.    |
//| London open = European institutions enter, test Asian extremes.   |
//| NY overlap = peak volume, directional conviction, breaks stick.   |
//| 70% of daily highs/lows set in London-NY overlap.                 |
//|                                                                   |
//| COUNTERPARTY: Asian session liquidity providers who placed        |
//| orders at range edges; their stops fuel the breakout.             |
//|                                                                   |
//| SOURCE: Forex Factory, TraderViet, institutional microstructure   |
//|                                                                   |
//| Max | 2026-04-05 | v1.0                                         |
//+------------------------------------------------------------------+
#property copyright "Max — EA_GoldORB v1.0"
#property version   "1.00"
#property strict

#include <Trade\Trade.mqh>

//+------------------------------------------------------------------+
//| Input Parameters                                                  |
//+------------------------------------------------------------------+
input group "=== General ==="
input ulong    InpMagic         = 702601;    // Magic Number
input int      InpDeviation     = 50;        // Max Slippage (pts)
input bool     InpKillSwitch    = false;     // Kill Switch

input group "=== Asian Range (Server Time UTC+2) ==="
input int      InpRangeStart    = 0;         // Range start hour (server)
input int      InpRangeEnd      = 9;         // Range end hour (server)

input group "=== Breakout Window (Server Time) ==="
input int      InpEntryStart    = 10;        // Entry window start hour
input int      InpEntryEnd      = 18;        // Entry window end hour

input group "=== Breakout Filters ==="
input double   InpBodyRatio     = 0.55;      // Min body/range ratio (0.55 = 55%)
input double   InpATRBodyMult   = 0.8;       // Min body as multiple of ATR(14)
input int      InpATRPeriod     = 14;        // ATR period
input double   InpMinRangePips  = 50.0;      // Min Asian range (points, e.g. 50 = $5)
input double   InpMaxRangePips  = 500.0;     // Max Asian range (filter for news days)

input group "=== Day Filters ==="
input bool     InpMonday        = false;     // Trade Monday
input bool     InpTuesday       = true;      // Trade Tuesday
input bool     InpWednesday     = true;      // Trade Wednesday
input bool     InpThursday      = true;      // Trade Thursday
input bool     InpFriday        = false;     // Trade Friday

input group "=== Trend Filter ==="
input int      InpEMAPeriod     = 50;        // EMA trend filter (0=disabled)

input group "=== Risk Management ==="
input double   InpRiskPct       = 0.40;      // Risk per trade (%)
input double   InpMaxLot        = 0.50;      // Max lot
input int      InpSLMode        = 0;         // SL: 0=Opposite range side, 1=ATR-based
input double   InpATRMultSL     = 2.0;       // SL ATR multiplier (mode 1)
input double   InpMaxSLPips     = 400.0;     // Max SL distance (points)
input int      InpTPMode        = 0;         // TP: 0=RR ratio, 1=Time exit (bars)
input double   InpRR            = 2.0;       // TP RR ratio (mode 0)
input int      InpHoldBars      = 6;         // Hold bars (mode 1, 6 bars = 90 min)
input bool     InpUseBE         = true;      // Move SL to BE at 1R
input double   InpDailyDDPct    = 3.0;       // Daily DD kill (%)

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
double         g_rangeHigh;
double         g_rangeLow;
bool           g_rangeSet;
int            g_barsHeld;
int            g_logHandle;

//+------------------------------------------------------------------+
int OnInit()
{
   if(InpKillSwitch) { Print("[GoldORB] Kill switch ON"); return INIT_SUCCEEDED; }

   g_trade.SetExpertMagicNumber(InpMagic);
   g_trade.SetDeviationInPoints(InpDeviation);
   g_trade.SetTypeFilling(ORDER_FILLING_FOK);

   g_hATR = iATR(_Symbol, PERIOD_CURRENT, InpATRPeriod);
   g_hEMA = (InpEMAPeriod > 0) ? iMA(_Symbol, PERIOD_CURRENT, InpEMAPeriod, 0, MODE_EMA, PRICE_CLOSE)
                                : INVALID_HANDLE;

   if(g_hATR == INVALID_HANDLE)
   { Print("[GoldORB] FATAL: ATR init failed"); return INIT_FAILED; }

   g_lastBar      = 0;
   g_todayDate    = 0;
   g_dayStartBal  = AccountInfoDouble(ACCOUNT_BALANCE);
   g_tradedToday  = false;
   g_rangeHigh    = 0;
   g_rangeLow     = 999999;
   g_rangeSet     = false;
   g_barsHeld     = 0;

   if(InpDatalog)
   {
      string fname = "GoldORB_datalog_" + _Symbol + ".csv";
      g_logHandle = FileOpen(fname, FILE_WRITE|FILE_CSV|FILE_COMMON, ',');
      if(g_logHandle != INVALID_HANDLE)
         FileWrite(g_logHandle,
            "Time","Signal","Price","RangeHigh","RangeLow","RangeSize",
            "ATR","EMA","Body","BodyRatio","SL","TP","Lot","DoW","SkipReason");
   }

   PrintFormat("[GoldORB] Init OK: %s %s Magic=%d Range=%d:00-%d:00 Entry=%d:00-%d:00",
               _Symbol, EnumToString(_Period), InpMagic,
               InpRangeStart, InpRangeEnd, InpEntryStart, InpEntryEnd);
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
void ManagePositions()
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0) continue;
      if(PositionGetInteger(POSITION_MAGIC) != InpMagic) continue;
      if(PositionGetString(POSITION_SYMBOL) != _Symbol) continue;

      double openPrice = PositionGetDouble(POSITION_PRICE_OPEN);
      double sl        = PositionGetDouble(POSITION_SL);
      double tp        = PositionGetDouble(POSITION_TP);
      long   posType   = PositionGetInteger(POSITION_TYPE);
      double bid       = SymbolInfoDouble(_Symbol, SYMBOL_BID);
      double ask       = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
      double pt        = SymbolInfoDouble(_Symbol, SYMBOL_POINT);

      // Time exit (mode 1)
      if(InpTPMode == 1)
      {
         g_barsHeld++;
         if(g_barsHeld >= InpHoldBars)
         {
            g_trade.PositionClose(ticket);
            PrintFormat("[GoldORB] Time exit after %d bars", g_barsHeld);
            g_barsHeld = 0;
            continue;
         }
      }

      // BE logic
      if(InpUseBE)
      {
         double slDist = MathAbs(openPrice - sl);
         if(posType == POSITION_TYPE_BUY)
         {
            if(bid >= openPrice + slDist && sl < openPrice)
               g_trade.PositionModify(ticket, openPrice + pt, tp);
         }
         else
         {
            if(ask <= openPrice - slDist && sl > openPrice)
               g_trade.PositionModify(ticket, openPrice - pt, tp);
         }
      }
   }
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
      g_rangeHigh   = 0;
      g_rangeLow    = 999999;
      g_rangeSet    = false;
   }

   // Manage existing positions
   if(CountMyPositions() > 0)
   {
      ManagePositions();
      return;
   }
   g_barsHeld = 0;

   // Phase 1: Build Asian range (using closed bars only — shift=1 minimum)
   if(dt.hour >= InpRangeStart && dt.hour < InpRangeEnd)
   {
      // Use bar[1] data for non-repaint
      double h1 = iHigh(_Symbol, PERIOD_CURRENT, 1);
      double l1 = iLow(_Symbol, PERIOD_CURRENT, 1);
      if(h1 > g_rangeHigh) g_rangeHigh = h1;
      if(l1 < g_rangeLow)  g_rangeLow  = l1;
      return;
   }

   // At range end, mark range as set
   if(!g_rangeSet && dt.hour >= InpRangeEnd)
   {
      g_rangeSet = true;
      double rangeSize = g_rangeHigh - g_rangeLow;
      double point = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
      double rangePts = (point > 0) ? rangeSize / point : 0;

      // Range size filters
      if(rangePts < InpMinRangePips || rangePts > InpMaxRangePips)
      {
         g_tradedToday = true; // Skip today — range out of bounds
         PrintFormat("[GoldORB] Range %.1f pts out of bounds [%.0f-%.0f], skip",
                     rangePts, InpMinRangePips, InpMaxRangePips);
         return;
      }
   }

   // Phase 2: Look for breakout
   if(!g_rangeSet || g_tradedToday) return;
   if(dt.hour < InpEntryStart || dt.hour >= InpEntryEnd) return;
   if(!IsTradingDay(dt.day_of_week)) return;

   // Daily DD kill
   double ddPct = (g_dayStartBal > 0)
                  ? (g_dayStartBal - AccountInfoDouble(ACCOUNT_EQUITY)) / g_dayStartBal * 100.0
                  : 0;
   if(ddPct >= InpDailyDDPct) return;

   // Read bar[1] for non-repaint signal
   double open1  = iOpen(_Symbol, PERIOD_CURRENT, 1);
   double close1 = iClose(_Symbol, PERIOD_CURRENT, 1);
   double high1  = iHigh(_Symbol, PERIOD_CURRENT, 1);
   double low1   = iLow(_Symbol, PERIOD_CURRENT, 1);
   int    digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
   double point  = SymbolInfoDouble(_Symbol, SYMBOL_POINT);

   // Body and range
   double body      = MathAbs(close1 - open1);
   double barRange  = high1 - low1;
   double bodyRatio = (barRange > 0) ? body / barRange : 0;

   // ATR
   double atr[];
   if(CopyBuffer(g_hATR, 0, 1, 1, atr) < 1) return;

   // EMA
   double emaVal = 0;
   if(InpEMAPeriod > 0 && g_hEMA != INVALID_HANDLE)
   {
      double ema[];
      if(CopyBuffer(g_hEMA, 0, 1, 1, ema) < 1) return;
      emaVal = ema[0];
   }

   // Breakout detection
   int signal = 0; // 0=none, 1=long, -1=short

   if(close1 > g_rangeHigh) signal = 1;
   else if(close1 < g_rangeLow) signal = -1;

   if(signal == 0) return;

   // Filter: body ratio
   if(bodyRatio < InpBodyRatio)
   {
      LogSignal(barTime, "SKIP", close1, atr[0], emaVal, body, bodyRatio, 0, 0, 0,
                dt.day_of_week, "BODY_RATIO_LOW");
      return;
   }

   // Filter: body vs ATR
   if(body < atr[0] * InpATRBodyMult)
   {
      LogSignal(barTime, "SKIP", close1, atr[0], emaVal, body, bodyRatio, 0, 0, 0,
                dt.day_of_week, "BODY_VS_ATR_LOW");
      return;
   }

   // Filter: EMA trend
   if(InpEMAPeriod > 0 && emaVal > 0)
   {
      if(signal == 1 && close1 < emaVal)
      {
         LogSignal(barTime, "SKIP_LONG", close1, atr[0], emaVal, body, bodyRatio, 0, 0, 0,
                   dt.day_of_week, "EMA_DOWNTREND");
         return;
      }
      if(signal == -1 && close1 > emaVal)
      {
         LogSignal(barTime, "SKIP_SHORT", close1, atr[0], emaVal, body, bodyRatio, 0, 0, 0,
                   dt.day_of_week, "EMA_UPTREND");
         return;
      }
   }

   // Calculate SL
   double price, sl, tp;
   double rangeSize = g_rangeHigh - g_rangeLow;

   if(signal == 1) // LONG breakout
   {
      price = SymbolInfoDouble(_Symbol, SYMBOL_ASK);

      if(InpSLMode == 0) // Opposite range side
         sl = NormalizeDouble(g_rangeLow - atr[0] * 0.2, digits); // Small buffer
      else
         sl = NormalizeDouble(price - atr[0] * InpATRMultSL, digits);

      // Cap SL distance
      double slDist = (price - sl) / point;
      if(slDist > InpMaxSLPips)
         sl = NormalizeDouble(price - InpMaxSLPips * point, digits);

      if(InpTPMode == 0)
         tp = NormalizeDouble(price + MathAbs(price - sl) * InpRR, digits);
      else
         tp = 0; // Time exit
   }
   else // SHORT breakout
   {
      price = SymbolInfoDouble(_Symbol, SYMBOL_BID);

      if(InpSLMode == 0)
         sl = NormalizeDouble(g_rangeHigh + atr[0] * 0.2, digits);
      else
         sl = NormalizeDouble(price + atr[0] * InpATRMultSL, digits);

      double slDist = (sl - price) / point;
      if(slDist > InpMaxSLPips)
         sl = NormalizeDouble(price + InpMaxSLPips * point, digits);

      if(InpTPMode == 0)
         tp = NormalizeDouble(price - MathAbs(sl - price) * InpRR, digits);
      else
         tp = 0;
   }

   // Lot size
   double slPoints = MathAbs(price - sl) / point;
   double lot = CalcLotSize(slPoints);
   if(lot <= 0)
   {
      LogSignal(barTime, "SKIP", close1, atr[0], emaVal, body, bodyRatio, sl, tp, 0,
                dt.day_of_week, "LOT_ZERO");
      return;
   }

   // Execute
   ENUM_ORDER_TYPE orderType = (signal == 1) ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
   string comment = StringFormat("ORB|RH=%.1f|RL=%.1f|DoW=%d",
                                 g_rangeHigh, g_rangeLow, dt.day_of_week);

   bool ok = g_trade.PositionOpen(_Symbol, orderType, lot, price, sl, tp, comment);
   if(ok)
   {
      g_tradedToday = true;
      g_barsHeld    = 0;
      PrintFormat("[GoldORB] %s %.2f @ %.2f SL=%.2f TP=%.2f Range=[%.2f-%.2f] DoW=%d",
                  signal == 1 ? "BUY" : "SELL", lot, price, sl, tp,
                  g_rangeLow, g_rangeHigh, dt.day_of_week);
      LogSignal(barTime, signal == 1 ? "BUY" : "SELL", price, atr[0], emaVal,
                body, bodyRatio, sl, tp, lot, dt.day_of_week, "EXECUTED");
   }
}

//+------------------------------------------------------------------+
void LogSignal(datetime time, string sig, double price, double atr,
               double ema, double body, double bodyRatio,
               double sl, double tp, double lot, int dow, string reason)
{
   if(!InpDatalog || g_logHandle == INVALID_HANDLE) return;
   double rangeSize = g_rangeHigh - g_rangeLow;
   FileWrite(g_logHandle,
      TimeToString(time, TIME_DATE|TIME_MINUTES),
      sig, DoubleToString(price, 2),
      DoubleToString(g_rangeHigh, 2), DoubleToString(g_rangeLow, 2),
      DoubleToString(rangeSize, 2),
      DoubleToString(atr, 2), DoubleToString(ema, 2),
      DoubleToString(body, 2), DoubleToString(bodyRatio, 3),
      DoubleToString(sl, 2), DoubleToString(tp, 2),
      DoubleToString(lot, 2), IntegerToString(dow), reason);
   FileFlush(g_logHandle);
}
//+------------------------------------------------------------------+
