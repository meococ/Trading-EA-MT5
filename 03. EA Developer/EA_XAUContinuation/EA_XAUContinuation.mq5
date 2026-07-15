//+------------------------------------------------------------------+
//| EA_XAUContinuation.mq5                                            |
//| Prior NY impulse -> Asia shallow pullback -> London continuation  |
//| Symbol: XAUUSD+  |  Period: M15                                   |
//|                                                                  |
//| HYPOTHESIS: A genuine prior-day New York repricing in gold can    |
//| continue on the next day if Asia only retraces shallowly and      |
//| London re-accelerates through the Asia continuation level.        |
//|                                                                  |
//| BASELINE RULES (v1):                                              |
//| 1. Detect prior-day NY impulse with commitment                    |
//| 2. Measure next-day Asia retracement against NY impulse           |
//| 3. Accept only shallow retracement that does not invalidate bias  |
//| 4. Enter on London continuation break using closed bars only      |
//| 5. Flat by session close; no overnight holding                    |
//|                                                                  |
//| This is a structural hypothesis baseline, not a promoted edge.    |
//+------------------------------------------------------------------+
#property copyright "Max — EA_XAUContinuation v1.0"
#property version   "1.00"
#property strict

#include <Trade\Trade.mqh>
#include <Trade\PositionInfo.mqh>
#include <Trade\SymbolInfo.mqh>
#include <ExecQualityLog.mqh>
#include <HolidayCalendar.mqh>

input group "=== Core ==="
input bool   InpEnabled              = true;
input ulong  InpMagic                = 20260415;
input int    InpDeviation            = 50;
input double InpRiskPct              = 0.40;
input double InpMaxLot               = 0.50;
input string InpComment              = "XAUCont";

input group "=== Prior NY Impulse (broker time) ==="
input int    InpNYStartH             = 15;
input int    InpNYStartM             = 0;
input int    InpNYEndH               = 21;
input int    InpNYEndM               = 0;
input int    InpATRPeriodD1          = 14;
input double InpImpulseATRMult       = 0.60;
input double InpMinBodyRatio         = 0.55;
input double InpCloseLocationMin     = 0.70;

input group "=== Asia Pullback Filter (broker time) ==="
input int    InpAsiaStartH           = 0;
input int    InpAsiaStartM           = 0;
input int    InpAsiaEndH             = 8;
input int    InpAsiaEndM             = 0;
input double InpAsiaRetraceMin       = 0.15;
input double InpAsiaRetraceMax       = 0.55;
input bool   InpRequireAsiaMidHold   = true;

input group "=== London Continuation Entry (broker time) ==="
input int    InpLdnStartH            = 9;
input int    InpLdnStartM            = 0;
input int    InpLdnEndH              = 13;
input int    InpLdnEndM              = 0;
input int    InpATRPeriodM15         = 14;
input int    InpPullbackLookback     = 3;
input double InpBreakATRMult         = 0.08;
input double InpSLBufferATRMult      = 0.20;
input double InpRRRatio              = 2.00;
input bool   InpRequirePostOpenStab  = true;
input int    InpStabStartH           = 9;
input int    InpStabStartM           = 0;

input group "=== Safety / Exits ==="
input int    InpFlatHour             = 20;
input int    InpFlatMinute           = 0;
input double InpDailyDDPct           = 3.0;
input bool   InpTradeMon             = true;
input bool   InpTradeTue             = true;
input bool   InpTradeWed             = true;
input bool   InpTradeThu             = true;
input bool   InpTradeFri             = true;

input group "=== Audit Log ==="
input bool   InpDatalog              = true;

CTrade         g_trade;
CPositionInfo  g_pos;
CSymbolInfo    g_sym;

int            g_hATR_D1             = INVALID_HANDLE;
int            g_hATR_M15            = INVALID_HANDLE;
datetime       g_lastBar             = 0;
datetime       g_todayDate           = 0;
double         g_dayStartBalance     = 0.0;
bool           g_tradeEnteredToday   = false;

// Prior NY state
bool           g_biasQualified       = false;
int            g_biasDirection       = 0;      // +1 bullish, -1 bearish
string         g_biasReason          = "";
double         g_prevNYOpen          = 0.0;
double         g_prevNYClose         = 0.0;
double         g_prevNYHigh          = 0.0;
double         g_prevNYLow           = 0.0;
double         g_prevNYRange         = 0.0;
double         g_prevImpulseSize     = 0.0;
double         g_prevATRD1           = 0.0;

// Current day Asia state
bool           g_asiaBuilt           = false;
bool           g_asiaFinalized       = false;
bool           g_asiaValid           = false;
string         g_asiaReason          = "";
double         g_asiaHigh            = 0.0;
double         g_asiaLow             = 0.0;
double         g_asiaClose           = 0.0;
double         g_asiaRetrace         = 0.0;
int            g_asiaBars            = 0;

bool           g_postOpenEvaluated   = false;
bool           g_postOpenStable      = false;
string         g_postOpenReason      = "";

int            g_logHandle           = INVALID_HANDLE;

//+------------------------------------------------------------------+
int MinutesOf(int h, int m)
{
   return h * 60 + m;
}

//+------------------------------------------------------------------+
datetime DateOnly(datetime t)
{
   MqlDateTime dt;
   TimeToStruct(t, dt);
   return StringToTime(StringFormat("%04d.%02d.%02d", dt.year, dt.mon, dt.day));
}

//+------------------------------------------------------------------+
bool IsTradingDay(datetime t)
{
   MqlDateTime dt;
   TimeToStruct(t, dt);
   switch(dt.day_of_week)
   {
      case 1: return InpTradeMon;
      case 2: return InpTradeTue;
      case 3: return InpTradeWed;
      case 4: return InpTradeThu;
      case 5: return InpTradeFri;
      default: return false;
   }
}

//+------------------------------------------------------------------+
int CountMyPositions()
{
   int count = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      if(!g_pos.SelectByIndex(i))
         continue;
      if(g_pos.Magic() == (long)InpMagic && g_pos.Symbol() == _Symbol)
         count++;
   }
   return count;
}

//+------------------------------------------------------------------+
void CloseAllPositions(string reason)
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      if(!g_pos.SelectByIndex(i))
         continue;
      if(g_pos.Magic() != (long)InpMagic || g_pos.Symbol() != _Symbol)
         continue;
      ulong ticket = g_pos.Ticket();
      if(g_trade.PositionClose(ticket))
         Print("[XAUCont] Close ", reason, " ticket=", ticket, " profit=", g_pos.Profit());
   }
}

//+------------------------------------------------------------------+
double ReadATR(int handle, int shift)
{
   double arr[];
   ArraySetAsSeries(arr, true);
   if(CopyBuffer(handle, 0, shift, 1, arr) < 1)
      return 0.0;
   return arr[0];
}

//+------------------------------------------------------------------+
double CalcLotSizeByPriceDistance(double priceDistance)
{
   if(priceDistance <= 0.0)
      return 0.0;

   double balance  = AccountInfoDouble(ACCOUNT_BALANCE);
   double riskAmt  = balance * InpRiskPct / 100.0;
   double tickSize = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   double tickVal  = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
   if(tickSize <= 0.0 || tickVal <= 0.0)
      return 0.0;

   double lots = riskAmt / (priceDistance / tickSize * tickVal);
   double minLot  = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double maxLot  = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   double lotStep = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);

   lots = MathMin(lots, InpMaxLot);
   lots = MathMin(lots, maxLot);
   lots = MathMax(lots, minLot);
   if(lotStep > 0.0)
      lots = MathFloor(lots / lotStep) * lotStep;
   return NormalizeDouble(lots, 2);
}

//+------------------------------------------------------------------+
void LogDailyState(string eventName, string reason, double triggerPrice = 0.0, double sl = 0.0, double tp = 0.0, double lots = 0.0)
{
   if(!InpDatalog || g_logHandle == INVALID_HANDLE)
      return;

   FileWrite(
      g_logHandle,
      TimeToString(TimeCurrent(), TIME_DATE|TIME_MINUTES),
      eventName,
      reason,
      IntegerToString(g_biasDirection),
      DoubleToString(g_prevNYOpen, 2),
      DoubleToString(g_prevNYClose, 2),
      DoubleToString(g_prevNYHigh, 2),
      DoubleToString(g_prevNYLow, 2),
      DoubleToString(g_prevImpulseSize, 2),
      DoubleToString(g_prevATRD1, 2),
      DoubleToString(g_asiaHigh, 2),
      DoubleToString(g_asiaLow, 2),
      DoubleToString(g_asiaClose, 2),
      DoubleToString(g_asiaRetrace, 3),
      DoubleToString(triggerPrice, 2),
      DoubleToString(sl, 2),
      DoubleToString(tp, 2),
      DoubleToString(lots, 2)
   );
   FileFlush(g_logHandle);
}

//+------------------------------------------------------------------+
void ResetDayState(datetime today)
{
   g_todayDate           = today;
   g_dayStartBalance     = AccountInfoDouble(ACCOUNT_BALANCE);
   g_tradeEnteredToday   = false;

   g_biasQualified       = false;
   g_biasDirection       = 0;
   g_biasReason          = "";
   g_prevNYOpen          = 0.0;
   g_prevNYClose         = 0.0;
   g_prevNYHigh          = 0.0;
   g_prevNYLow           = 0.0;
   g_prevNYRange         = 0.0;
   g_prevImpulseSize     = 0.0;
   g_prevATRD1           = 0.0;

   g_asiaBuilt           = false;
   g_asiaFinalized       = false;
   g_asiaValid           = false;
   g_asiaReason          = "";
   g_asiaHigh            = 0.0;
   g_asiaLow             = 999999.0;
   g_asiaClose           = 0.0;
   g_asiaRetrace         = 0.0;
   g_asiaBars            = 0;

   g_postOpenEvaluated   = false;
   g_postOpenStable      = false;
   g_postOpenReason      = "";
}

//+------------------------------------------------------------------+
bool LoadPreviousNYImpulse(datetime today)
{
   datetime prevDay      = today - 86400;
   datetime sessionStart = prevDay + MinutesOf(InpNYStartH, InpNYStartM) * 60;
   datetime sessionEnd   = prevDay + MinutesOf(InpNYEndH, InpNYEndM) * 60;
   if(sessionEnd <= sessionStart)
   {
      g_biasReason = "NY_WINDOW_INVALID";
      return false;
   }

   int startShift = iBarShift(_Symbol, PERIOD_CURRENT, sessionStart, false);
   int endShift   = iBarShift(_Symbol, PERIOD_CURRENT, sessionEnd - 1, false);
   if(startShift < 0 || endShift < 0 || startShift < endShift)
   {
      g_biasReason = "NY_BARS_MISSING";
      return false;
   }

   double highVal = -DBL_MAX;
   double lowVal  = DBL_MAX;
   for(int s = startShift; s >= endShift; s--)
   {
      double hi = iHigh(_Symbol, PERIOD_CURRENT, s);
      double lo = iLow(_Symbol, PERIOD_CURRENT, s);
      if(hi > highVal) highVal = hi;
      if(lo < lowVal)  lowVal  = lo;
   }

   g_prevNYOpen      = iOpen(_Symbol, PERIOD_CURRENT, startShift);
   g_prevNYClose     = iClose(_Symbol, PERIOD_CURRENT, endShift);
   g_prevNYHigh      = highVal;
   g_prevNYLow       = lowVal;
   g_prevNYRange     = g_prevNYHigh - g_prevNYLow;
   g_prevImpulseSize = MathAbs(g_prevNYClose - g_prevNYOpen);
   g_prevATRD1       = ReadATR(g_hATR_D1, 1);

   if(g_prevNYRange <= 0.0 || g_prevATRD1 <= 0.0)
   {
      g_biasReason = "NY_RANGE_OR_ATR_ZERO";
      return false;
   }

   double bodyRatio = g_prevImpulseSize / g_prevNYRange;
   if(g_prevImpulseSize < g_prevATRD1 * InpImpulseATRMult)
   {
      g_biasReason = "NY_IMPULSE_TOO_SMALL";
      return false;
   }
   if(bodyRatio < InpMinBodyRatio)
   {
      g_biasReason = "NY_BODY_RATIO_LOW";
      return false;
   }

   if(g_prevNYClose > g_prevNYOpen)
   {
      double closeLoc = (g_prevNYClose - g_prevNYLow) / g_prevNYRange;
      if(closeLoc < InpCloseLocationMin)
      {
         g_biasReason = "NY_BULL_CLOSE_LOC_LOW";
         return false;
      }
      g_biasDirection = 1;
      g_biasQualified = true;
      g_biasReason    = "NY_BULL_IMPULSE";
      return true;
   }

   if(g_prevNYClose < g_prevNYOpen)
   {
      double closeLoc = (g_prevNYHigh - g_prevNYClose) / g_prevNYRange;
      if(closeLoc < InpCloseLocationMin)
      {
         g_biasReason = "NY_BEAR_CLOSE_LOC_LOW";
         return false;
      }
      g_biasDirection = -1;
      g_biasQualified = true;
      g_biasReason    = "NY_BEAR_IMPULSE";
      return true;
   }

   g_biasReason = "NY_DOJI_CLOSE";
   return false;
}

//+------------------------------------------------------------------+
void UpdateAsiaState(datetime barTime)
{
   if(g_asiaFinalized)
      return;

   MqlDateTime dt;
   TimeToStruct(barTime, dt);
   int nowMins  = dt.hour * 60 + dt.min;
   int asiaFrom = MinutesOf(InpAsiaStartH, InpAsiaStartM);
   int asiaTo   = MinutesOf(InpAsiaEndH, InpAsiaEndM);

   if(nowMins < asiaFrom || nowMins >= asiaTo)
      return;

   datetime bar1Time = iTime(_Symbol, PERIOD_CURRENT, 1);
   if(bar1Time <= 0 || DateOnly(bar1Time) != g_todayDate)
      return;

   MqlDateTime b1;
   TimeToStruct(bar1Time, b1);
   int bar1Mins = b1.hour * 60 + b1.min;
   if(bar1Mins < asiaFrom || bar1Mins >= asiaTo)
      return;

   double hi = iHigh(_Symbol, PERIOD_CURRENT, 1);
   double lo = iLow(_Symbol, PERIOD_CURRENT, 1);
   double cl = iClose(_Symbol, PERIOD_CURRENT, 1);

   if(!g_asiaBuilt)
   {
      g_asiaHigh  = hi;
      g_asiaLow   = lo;
      g_asiaClose = cl;
      g_asiaBuilt = true;
      g_asiaBars  = 1;
      return;
   }

   if(hi > g_asiaHigh) g_asiaHigh = hi;
   if(lo < g_asiaLow)  g_asiaLow  = lo;
   g_asiaClose = cl;
   g_asiaBars++;
}

//+------------------------------------------------------------------+
void FinalizeAsiaIfReady(datetime barTime)
{
   if(g_asiaFinalized)
      return;

   MqlDateTime dt;
   TimeToStruct(barTime, dt);
   int nowMins = dt.hour * 60 + dt.min;
   int asiaTo  = MinutesOf(InpAsiaEndH, InpAsiaEndM);
   if(nowMins < asiaTo)
      return;

   g_asiaFinalized = true;

   if(!g_biasQualified)
   {
      g_asiaReason = g_biasReason;
      LogDailyState("DAY_SKIP", g_asiaReason);
      return;
   }

   if(!g_asiaBuilt || g_asiaBars < 2 || g_prevImpulseSize <= 0.0)
   {
      g_asiaReason = "ASIA_BARS_MISSING";
      LogDailyState("DAY_SKIP", g_asiaReason);
      return;
   }

   double midpoint = (g_prevNYOpen + g_prevNYClose) * 0.5;

   if(g_biasDirection > 0)
   {
      g_asiaRetrace = (g_prevNYClose - g_asiaLow) / g_prevImpulseSize;
      if(g_asiaLow <= g_prevNYOpen)
      {
         g_asiaReason = "ASIA_BULL_INVALIDATES_OPEN";
         LogDailyState("ASIA_FAIL", g_asiaReason);
         return;
      }
      if(InpRequireAsiaMidHold && g_asiaClose < midpoint)
      {
         g_asiaReason = "ASIA_BULL_CLOSE_BELOW_MID";
         LogDailyState("ASIA_FAIL", g_asiaReason);
         return;
      }
   }
   else if(g_biasDirection < 0)
   {
      g_asiaRetrace = (g_asiaHigh - g_prevNYClose) / g_prevImpulseSize;
      if(g_asiaHigh >= g_prevNYOpen)
      {
         g_asiaReason = "ASIA_BEAR_INVALIDATES_OPEN";
         LogDailyState("ASIA_FAIL", g_asiaReason);
         return;
      }
      if(InpRequireAsiaMidHold && g_asiaClose > midpoint)
      {
         g_asiaReason = "ASIA_BEAR_CLOSE_ABOVE_MID";
         LogDailyState("ASIA_FAIL", g_asiaReason);
         return;
      }
   }
   else
   {
      g_asiaReason = "BIAS_DIRECTION_ZERO";
      LogDailyState("ASIA_FAIL", g_asiaReason);
      return;
   }

   if(g_asiaRetrace < InpAsiaRetraceMin)
   {
      g_asiaReason = "ASIA_RETRACE_TOO_SHALLOW";
      LogDailyState("ASIA_FAIL", g_asiaReason);
      return;
   }
   if(g_asiaRetrace > InpAsiaRetraceMax)
   {
      g_asiaReason = "ASIA_RETRACE_TOO_DEEP";
      LogDailyState("ASIA_FAIL", g_asiaReason);
      return;
   }

   g_asiaValid  = true;
   g_asiaReason = "ASIA_SHALLOW_PULLBACK_PASS";
   LogDailyState("ASIA_PASS", g_asiaReason);
}

//+------------------------------------------------------------------+
bool DailyDDExceeded()
{
   if(g_dayStartBalance <= 0.0)
      return false;
   double ddPct = (g_dayStartBalance - AccountInfoDouble(ACCOUNT_EQUITY)) / g_dayStartBalance * 100.0;
   return ddPct >= InpDailyDDPct;
}

//+------------------------------------------------------------------+
void EvaluatePostOpenStabilization(datetime barTime)
{
   if(g_postOpenEvaluated || !g_asiaValid)
      return;

   if(!InpRequirePostOpenStab)
   {
      g_postOpenEvaluated = true;
      g_postOpenStable    = true;
      g_postOpenReason    = "POST_OPEN_STAB_DISABLED";
      return;
   }

   MqlDateTime dt;
   TimeToStruct(barTime, dt);
   int nowMins   = dt.hour * 60 + dt.min;
   int stabFrom  = MinutesOf(InpStabStartH, InpStabStartM);
   int entryFrom = MinutesOf(InpLdnStartH, InpLdnStartM);
   if(entryFrom <= stabFrom)
   {
      g_postOpenEvaluated = true;
      g_postOpenStable    = true;
      g_postOpenReason    = "POST_OPEN_STAB_WINDOW_EMPTY";
      return;
   }
   if(nowMins < entryFrom)
      return;

   double atrM15 = ReadATR(g_hATR_M15, 1);
   if(atrM15 <= 0.0)
      return;

   bool unstable = false;
   string reason = "POST_OPEN_STABLE";
   double bullBreak = g_asiaHigh + atrM15 * InpBreakATRMult;
   double bearBreak = g_asiaLow  - atrM15 * InpBreakATRMult;

   int totalBars = Bars(_Symbol, PERIOD_CURRENT);
   for(int shift = 1; shift < totalBars; shift++)
   {
      datetime sampleTime = iTime(_Symbol, PERIOD_CURRENT, shift);
      if(sampleTime <= 0)
         continue;
      if(DateOnly(sampleTime) != g_todayDate)
         break;

      MqlDateTime sampleDt;
      TimeToStruct(sampleTime, sampleDt);
      int sampleMins = sampleDt.hour * 60 + sampleDt.min;
      if(sampleMins >= entryFrom)
         continue;
      if(sampleMins < stabFrom)
         break;

      double hi = iHigh(_Symbol, PERIOD_CURRENT, shift);
      double lo = iLow(_Symbol, PERIOD_CURRENT, shift);
      double op = iOpen(_Symbol, PERIOD_CURRENT, shift);
      double cl = iClose(_Symbol, PERIOD_CURRENT, shift);

      if(g_biasDirection > 0)
      {
         if(hi >= bullBreak)
         {
            unstable = true;
            reason   = "POST_OPEN_BULL_BREAKOUT";
            break;
         }
      }
      else if(g_biasDirection < 0)
      {
         if(lo <= bearBreak)
         {
            unstable = true;
            reason   = "POST_OPEN_BEAR_BREAKOUT";
            break;
         }
      }
   }

   g_postOpenEvaluated = true;
   g_postOpenStable    = !unstable;
   g_postOpenReason    = reason;
   LogDailyState(g_postOpenStable ? "STAB_PASS" : "STAB_FAIL", g_postOpenReason);
}

//+------------------------------------------------------------------+
void TryLondonEntry(datetime barTime)
{
   if(!g_biasQualified || !g_asiaValid || g_tradeEnteredToday)
      return;
   if(CountMyPositions() > 0 || DailyDDExceeded())
      return;

   MqlDateTime dt;
   TimeToStruct(barTime, dt);
   int nowMins = dt.hour * 60 + dt.min;
   int ldnFrom = MinutesOf(InpLdnStartH, InpLdnStartM);
   int ldnTo   = MinutesOf(InpLdnEndH, InpLdnEndM);
   if(nowMins < ldnFrom || nowMins >= ldnTo)
      return;

   EvaluatePostOpenStabilization(barTime);
   if(InpRequirePostOpenStab && (!g_postOpenEvaluated || !g_postOpenStable))
      return;

   double atrM15 = ReadATR(g_hATR_M15, 1);
   if(atrM15 <= 0.0)
      return;

   double open1  = iOpen(_Symbol, PERIOD_CURRENT, 1);
   double close1 = iClose(_Symbol, PERIOD_CURRENT, 1);
   double high1  = iHigh(_Symbol, PERIOD_CURRENT, 1);
   double low1   = iLow(_Symbol, PERIOD_CURRENT, 1);
   double point  = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   int    digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);

   double recentLow = DBL_MAX;
   double recentHigh = -DBL_MAX;
   for(int i = 1; i <= InpPullbackLookback; i++)
   {
      double lo = iLow(_Symbol, PERIOD_CURRENT, i);
      double hi = iHigh(_Symbol, PERIOD_CURRENT, i);
      if(lo < recentLow)  recentLow  = lo;
      if(hi > recentHigh) recentHigh = hi;
   }

   bool trigger = false;
   bool isBuy   = false;
   double entry = 0.0;
   double sl    = 0.0;
   double tp    = 0.0;

   if(g_biasDirection > 0)
   {
      bool higherLow = recentLow > g_asiaLow;
      bool breakout  = close1 > (g_asiaHigh + atrM15 * InpBreakATRMult);
      bool bullBar   = close1 > open1 && high1 >= g_asiaHigh;
      if(higherLow && breakout && bullBar)
      {
         isBuy = true;
         entry = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
         sl    = recentLow - atrM15 * InpSLBufferATRMult;
         tp    = entry + (entry - sl) * InpRRRatio;
         trigger = true;
      }
   }
   else if(g_biasDirection < 0)
   {
      bool lowerHigh = recentHigh < g_asiaHigh;
      bool breakout  = close1 < (g_asiaLow - atrM15 * InpBreakATRMult);
      bool bearBar   = close1 < open1 && low1 <= g_asiaLow;
      if(lowerHigh && breakout && bearBar)
      {
         isBuy = false;
         entry = SymbolInfoDouble(_Symbol, SYMBOL_BID);
         sl    = recentHigh + atrM15 * InpSLBufferATRMult;
         tp    = entry - (sl - entry) * InpRRRatio;
         trigger = true;
      }
   }

   if(!trigger)
      return;

   int stopLevel = (int)SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL);
   double minDist = stopLevel * point;
   if(isBuy)
   {
      if((entry - sl) < minDist) sl = entry - minDist - point;
      if((tp - entry) < minDist) tp = entry + minDist + point;
   }
   else
   {
      if((sl - entry) < minDist) sl = entry + minDist + point;
      if((entry - tp) < minDist) tp = entry - minDist - point;
   }

   entry = NormalizeDouble(entry, digits);
   sl    = NormalizeDouble(sl, digits);
   tp    = NormalizeDouble(tp, digits);

   double lots = CalcLotSizeByPriceDistance(MathAbs(entry - sl));
   if(lots <= 0.0)
   {
      LogDailyState("ENTRY_SKIP", "LOT_ZERO", entry, sl, tp, 0.0);
      return;
   }

   double pipSize = g_sym.Point() * 10.0;
   if(StringFind(_Symbol, "JPY") >= 0)
      pipSize = g_sym.Point() * 100.0;
   double spreadPips = (double)SymbolInfoInteger(_Symbol, SYMBOL_SPREAD) * g_sym.Point() / pipSize;
   EQL_SetContext(entry, spreadPips, "LDN");

   bool ok = false;
   g_trade.SetTypeFilling(ORDER_FILLING_FOK);
   if(isBuy)
      ok = g_trade.Buy(lots, _Symbol, entry, sl, tp, InpComment + "_BUY");
   else
      ok = g_trade.Sell(lots, _Symbol, entry, sl, tp, InpComment + "_SELL");

   if(!ok)
   {
      uint rc = g_trade.ResultRetcode();
      EQL_RecordRetry(rc);
      g_trade.SetTypeFilling(ORDER_FILLING_IOC);
      if(isBuy)
         ok = g_trade.Buy(lots, _Symbol, entry, sl, tp, InpComment + "_BUY");
      else
         ok = g_trade.Sell(lots, _Symbol, entry, sl, tp, InpComment + "_SELL");
   }

   if(!ok)
   {
      LogDailyState("ENTRY_FAIL", IntegerToString((int)g_trade.ResultRetcode()), entry, sl, tp, lots);
      return;
   }

   EQL_RecordFill(g_trade.ResultRetcode());
   g_tradeEnteredToday = true;
   LogDailyState(isBuy ? "ENTRY_BUY" : "ENTRY_SELL", "EXECUTED", entry, sl, tp, lots);
   PrintFormat("[XAUCont] %s %.2f @ %.2f SL=%.2f TP=%.2f | NY=%s AsiaRetrace=%.2f",
               isBuy ? "BUY" : "SELL", lots, entry, sl, tp, g_biasReason, g_asiaRetrace);
}

//+------------------------------------------------------------------+
int OnInit()
{
   if(!InpEnabled)
      return INIT_SUCCEEDED;

   g_trade.SetExpertMagicNumber(InpMagic);
   g_trade.SetDeviationInPoints(InpDeviation);
   g_sym.Name(_Symbol);

   g_hATR_D1  = iATR(_Symbol, PERIOD_D1, InpATRPeriodD1);
   g_hATR_M15 = iATR(_Symbol, PERIOD_CURRENT, InpATRPeriodM15);
   if(g_hATR_D1 == INVALID_HANDLE || g_hATR_M15 == INVALID_HANDLE)
   {
      Print("[XAUCont] FATAL: indicator handle init failed");
      return INIT_FAILED;
   }

   ResetDayState(DateOnly(TimeCurrent()));
   LoadPreviousNYImpulse(g_todayDate);

   if(InpDatalog)
   {
      string fname = "XAUContinuation_datalog_" + _Symbol + ".csv";
      g_logHandle = FileOpen(fname, FILE_WRITE|FILE_CSV|FILE_COMMON, ',');
      if(g_logHandle != INVALID_HANDLE)
      {
         FileWrite(g_logHandle,
            "Time","Event","Reason","BiasDir","PrevNYOpen","PrevNYClose","PrevNYHigh","PrevNYLow",
            "PrevImpulse","PrevATRD1","AsiaHigh","AsiaLow","AsiaClose","AsiaRetrace","Entry","SL","TP","Lots");
      }
   }

   double pipSize = g_sym.Point() * 10.0;
   if(StringFind(_Symbol, "JPY") >= 0)
      pipSize = g_sym.Point() * 100.0;
   EQL_Init("EA_XAUContinuation", InpMagic, "XAUC", pipSize, true);

   PrintFormat("[XAUCont] Init OK %s %s Magic=%d", _Symbol, EnumToString(_Period), InpMagic);
   return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   if(g_hATR_D1 != INVALID_HANDLE)  IndicatorRelease(g_hATR_D1);
   if(g_hATR_M15 != INVALID_HANDLE) IndicatorRelease(g_hATR_M15);
   if(g_logHandle != INVALID_HANDLE) FileClose(g_logHandle);
}

//+------------------------------------------------------------------+
void OnTick()
{
   if(!InpEnabled)
      return;
   if(IsMarketHoliday())
      return;

   datetime curBar = iTime(_Symbol, PERIOD_CURRENT, 0);
   if(curBar == g_lastBar)
      return;
   g_lastBar = curBar;

   datetime today = DateOnly(curBar);
   if(today != g_todayDate)
   {
      ResetDayState(today);
      LoadPreviousNYImpulse(today);
      LogDailyState("DAY_START", g_biasQualified ? g_biasReason : g_biasReason);
   }

   if(!IsTradingDay(curBar))
      return;

   MqlDateTime dt;
   TimeToStruct(curBar, dt);
   int nowMins = dt.hour * 60 + dt.min;
   int flatMins = MinutesOf(InpFlatHour, InpFlatMinute);

   if(CountMyPositions() > 0 && nowMins >= flatMins)
   {
      CloseAllPositions("FlatTime");
      return;
   }

   UpdateAsiaState(curBar);
   FinalizeAsiaIfReady(curBar);
   EvaluatePostOpenStabilization(curBar);
   TryLondonEntry(curBar);
}

//+------------------------------------------------------------------+
void OnTradeTransaction(const MqlTradeTransaction& trans,
                        const MqlTradeRequest& request,
                        const MqlTradeResult& result)
{
   if(trans.type != TRADE_TRANSACTION_DEAL_ADD) return;
   if(trans.deal == 0) return;
   if(!HistoryDealSelect(trans.deal)) return;
   if((long)HistoryDealGetInteger(trans.deal, DEAL_MAGIC) != (long)InpMagic) return;
   EQL_OnDeal(trans.deal);
}

//+------------------------------------------------------------------+
double OnTester()
{
   double pf = TesterStatistics(STAT_PROFIT_FACTOR);
   double n  = TesterStatistics(STAT_TRADES);
   if(n < 20) return 0.0;
   return pf * MathSqrt(n);
}
//+------------------------------------------------------------------+
