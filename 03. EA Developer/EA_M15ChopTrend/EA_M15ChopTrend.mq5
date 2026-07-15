//+------------------------------------------------------------------+
//| EA_M15ChopTrend.mq5 — Choppiness regime + EMA trend (M15)        |
//| Symbol: USDJPY | Period: M15 | Magic: 880912                     |
//|                                                                   |
//| Near-miss seed: S630 / EA_ChopRegime (PF~1.26, WFA 5/5).         |
//| Independent closed-bar[1] GOAL transfer: no Mon/Wed/Thu mining.  |
//| Hypothesis: HYP-CHOP-TREND-M15-001                                 |
//|                                                                   |
//| Trade only when CI(14) <= ChopHigh; direction from EMA8/21       |
//| fresh cross or strong-trend continuation (CI < ChopLow) with     |
//| EMA50 bias. Weekend flat. Risk 0.5%.                             |
//+------------------------------------------------------------------+
#property copyright "SonicR / EA_M15ChopTrend"
#property version   "1.00"
#property strict

#include <Trade\Trade.mqh>

input group "=== General ==="
input ulong    InpMagic         = 880912;
input int      InpDeviation     = 30;
input bool     InpKillSwitch    = false;

input group "=== Choppiness Index ==="
input int      InpChopPeriod    = 14;
input double   InpChopLow       = 38.2;   // strong-trend continuation threshold
input double   InpChopHigh      = 50.0;   // above = too choppy (no trade)

input group "=== Trend Detection ==="
input int      InpFastEMA       = 8;
input int      InpSlowEMA       = 21;
input int      InpTrendEMA      = 50;

input group "=== Session (server hours) ==="
input int      InpStartHour     = 8;
input int      InpEndHour       = 17;
input int      InpExitHour      = 21;
input bool     InpTradeMon      = true;
input bool     InpTradeTue      = true;
input bool     InpTradeWed      = true;
input bool     InpTradeThu      = true;
input bool     InpTradeFri      = false;  // weekend-flat: no Friday entries

input group "=== Risk ==="
input double   InpRiskPct       = 0.50;
input double   InpMaxLot        = 1.0;
input double   InpSL_ATR_Mult   = 1.5;
input double   InpTP_Ratio      = 1.5;
input int      InpMinSLPoints   = 100;
input int      InpMaxSLPoints   = 1000;
input int      InpMaxPerDay     = 2;
input double   InpDailyDD       = 4.0;

CTrade   g_trade;
int      g_hATR14 = INVALID_HANDLE;
int      g_hATR1  = INVALID_HANDLE;
int      g_hFast  = INVALID_HANDLE;
int      g_hSlow  = INVALID_HANDLE;
int      g_hTrend = INVALID_HANDLE;
datetime g_lastBar = 0;
int      g_tradesToday = 0;
int      g_lastTradeDay = -1;
double   g_dayStartBalance = 0;

//+------------------------------------------------------------------+
int OnInit()
{
   g_trade.SetExpertMagicNumber((long)InpMagic);
   g_trade.SetDeviationInPoints(InpDeviation);

   g_hATR14 = iATR(_Symbol, PERIOD_CURRENT, 14);
   g_hATR1  = iATR(_Symbol, PERIOD_CURRENT, 1);
   g_hFast  = iMA(_Symbol, PERIOD_CURRENT, InpFastEMA, 0, MODE_EMA, PRICE_CLOSE);
   g_hSlow  = iMA(_Symbol, PERIOD_CURRENT, InpSlowEMA, 0, MODE_EMA, PRICE_CLOSE);
   g_hTrend = iMA(_Symbol, PERIOD_CURRENT, InpTrendEMA, 0, MODE_EMA, PRICE_CLOSE);
   if(g_hATR14 == INVALID_HANDLE || g_hATR1 == INVALID_HANDLE ||
      g_hFast == INVALID_HANDLE || g_hSlow == INVALID_HANDLE ||
      g_hTrend == INVALID_HANDLE)
      return INIT_FAILED;

   g_dayStartBalance = AccountInfoDouble(ACCOUNT_BALANCE);
   PrintFormat("[CHOPTREND] HYP-CHOP-TREND-M15-001 | CI<%.1f EMA %d/%d/%d risk=%.2f%%",
               InpChopHigh, InpFastEMA, InpSlowEMA, InpTrendEMA, InpRiskPct);
   return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   if(g_hATR14 != INVALID_HANDLE) IndicatorRelease(g_hATR14);
   if(g_hATR1  != INVALID_HANDLE) IndicatorRelease(g_hATR1);
   if(g_hFast  != INVALID_HANDLE) IndicatorRelease(g_hFast);
   if(g_hSlow  != INVALID_HANDLE) IndicatorRelease(g_hSlow);
   if(g_hTrend != INVALID_HANDLE) IndicatorRelease(g_hTrend);
}

//+------------------------------------------------------------------+
int CountPositions()
{
   int c = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong t = PositionGetTicket(i);
      if(t > 0 &&
         PositionGetInteger(POSITION_MAGIC) == (long)InpMagic &&
         PositionGetString(POSITION_SYMBOL) == _Symbol)
         c++;
   }
   return c;
}

//+------------------------------------------------------------------+
bool IsSuccessfulRetcode(const uint retcode)
{
   return(retcode == TRADE_RETCODE_DONE ||
          retcode == TRADE_RETCODE_PLACED ||
          retcode == TRADE_RETCODE_DONE_PARTIAL);
}

//+------------------------------------------------------------------+
bool IsRetryableRetcode(const uint retcode)
{
   return(retcode == TRADE_RETCODE_REQUOTE ||
          retcode == TRADE_RETCODE_PRICE_CHANGED ||
          retcode == TRADE_RETCODE_PRICE_OFF ||
          retcode == TRADE_RETCODE_CONNECTION ||
          retcode == TRADE_RETCODE_TIMEOUT ||
          retcode == TRADE_RETCODE_TOO_MANY_REQUESTS ||
          retcode == TRADE_RETCODE_LOCKED);
}

//+------------------------------------------------------------------+
int ResolveFillModes(ENUM_ORDER_TYPE_FILLING &primary, ENUM_ORDER_TYPE_FILLING &secondary)
{
   long fillMask = 0;
   primary = ORDER_FILLING_FOK;
   secondary = ORDER_FILLING_IOC;
   if(!SymbolInfoInteger(_Symbol, SYMBOL_FILLING_MODE, fillMask))
      return 2;

   int count = 0;
   if((fillMask & SYMBOL_FILLING_FOK) == SYMBOL_FILLING_FOK)
   {
      primary = ORDER_FILLING_FOK;
      count++;
   }
   if((fillMask & SYMBOL_FILLING_IOC) == SYMBOL_FILLING_IOC)
   {
      if(count == 0) primary = ORDER_FILLING_IOC;
      else secondary = ORDER_FILLING_IOC;
      count++;
   }
   if(count == 0)
      return 1;
   return count;
}

//+------------------------------------------------------------------+
bool ValidateStops(const bool isBuy, const double entryPrice, const double sl, const double tp)
{
   long stopsLevel = 0;
   long freezeLevel = 0;
   SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL, stopsLevel);
   SymbolInfoInteger(_Symbol, SYMBOL_TRADE_FREEZE_LEVEL, freezeLevel);
   double minDistance = (double)MathMax(stopsLevel, freezeLevel) * _Point;
   if(minDistance <= 0.0)
      return true;
   if(isBuy)
      return ((entryPrice - sl) >= minDistance && (tp - entryPrice) >= minDistance);
   return ((sl - entryPrice) >= minDistance && (entryPrice - tp) >= minDistance);
}

//+------------------------------------------------------------------+
bool SendDealWithRetry(const ENUM_ORDER_TYPE type, const double volume,
                       const double sl, const double tp, const ulong position,
                       const string comment, MqlTradeResult &res)
{
   ENUM_ORDER_TYPE_FILLING primaryMode, secondaryMode;
   int modeCount = ResolveFillModes(primaryMode, secondaryMode);

   for(int modeIdx = 0; modeIdx < modeCount; modeIdx++)
   {
      ENUM_ORDER_TYPE_FILLING activeMode = (modeIdx == 0 ? primaryMode : secondaryMode);
      for(int attempt = 0; attempt < 3; attempt++)
      {
         double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
         double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
         MqlTradeRequest req = {};
         MqlTradeResult tmp = {};
         req.action   = TRADE_ACTION_DEAL;
         req.symbol   = _Symbol;
         req.volume   = volume;
         req.type     = type;
         req.price    = (type == ORDER_TYPE_BUY ? ask : bid);
         req.sl       = sl;
         req.tp       = tp;
         req.deviation = (ulong)InpDeviation;
         req.magic    = InpMagic;
         req.position = position;
         req.comment  = comment;
         req.type_filling = activeMode;

         if(position == 0 && sl > 0.0 && tp > 0.0 &&
            !ValidateStops(type == ORDER_TYPE_BUY, req.price, sl, tp))
            return false;

         ResetLastError();
         bool sent = OrderSend(req, tmp);
         res = tmp;

         if(sent && IsSuccessfulRetcode(res.retcode))
            return true;
         if(sent && !IsRetryableRetcode(res.retcode))
            return false;
         if(!sent && attempt == 2)
            return false;

         Sleep(100 * (1 << attempt));
      }
   }
   return false;
}

//+------------------------------------------------------------------+
void CloseAll(const string reason)
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong t = PositionGetTicket(i);
      if(t <= 0 ||
         PositionGetInteger(POSITION_MAGIC) != (long)InpMagic ||
         PositionGetString(POSITION_SYMBOL) != _Symbol)
         continue;
      bool isBuy = (PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY);
      MqlTradeResult res = {};
      if(!SendDealWithRetry(isBuy ? ORDER_TYPE_SELL : ORDER_TYPE_BUY,
                            PositionGetDouble(POSITION_VOLUME), 0.0, 0.0, t,
                            "CHOPT|" + reason, res))
         PrintFormat("[CHOPTREND] Close failed ticket=%I64u retcode=%u", t, res.retcode);
   }
}

//+------------------------------------------------------------------+
bool IsDDExceeded()
{
   if(g_dayStartBalance <= 0) return false;
   return (g_dayStartBalance - AccountInfoDouble(ACCOUNT_EQUITY)) / g_dayStartBalance * 100.0 >= InpDailyDD;
}

//+------------------------------------------------------------------+
double CalcLot(const double slDist)
{
   if(slDist <= 0) return 0;
   double bal = AccountInfoDouble(ACCOUNT_BALANCE);
   double riskCash = bal * InpRiskPct / 100.0;
   double tv = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
   double ts = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   if(tv <= 0 || ts <= 0) return 0;
   double lot = riskCash / (slDist / ts * tv);
   lot = MathMin(lot, InpMaxLot);
   lot = MathMin(lot, SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX));
   lot = MathMax(lot, SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN));
   double step = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   if(step > 0)
      lot = MathFloor(lot / step) * step;
   return lot;
}

//+------------------------------------------------------------------+
double ComputeChoppiness(const int shift)
{
   double atr1[];
   ArraySetAsSeries(atr1, true);
   if(CopyBuffer(g_hATR1, 0, shift, InpChopPeriod, atr1) < InpChopPeriod)
      return 50.0;

   double atrSum = 0;
   for(int i = 0; i < InpChopPeriod; i++)
      atrSum += atr1[i];

   double hh = -DBL_MAX;
   double ll = DBL_MAX;
   for(int i = shift; i < shift + InpChopPeriod; i++)
   {
      double h = iHigh(_Symbol, PERIOD_CURRENT, i);
      double l = iLow(_Symbol, PERIOD_CURRENT, i);
      if(h > hh) hh = h;
      if(l < ll) ll = l;
   }
   double range = hh - ll;
   if(range <= 0 || atrSum <= 0) return 50.0;
   return 100.0 * MathLog10(atrSum / range) / MathLog10((double)InpChopPeriod);
}

//+------------------------------------------------------------------+
bool IsTradeDay(const int dow)
{
   if(dow == 1) return InpTradeMon;
   if(dow == 2) return InpTradeTue;
   if(dow == 3) return InpTradeWed;
   if(dow == 4) return InpTradeThu;
   if(dow == 5) return InpTradeFri;
   return false;
}

//+------------------------------------------------------------------+
int GetSignal()
{
   // Closed-bar[1] only.
   double ci = ComputeChoppiness(1);
   if(ci > InpChopHigh)
      return 0;

   double fast[], slow[], trend[];
   ArraySetAsSeries(fast, true);
   ArraySetAsSeries(slow, true);
   ArraySetAsSeries(trend, true);
   if(CopyBuffer(g_hFast, 0, 1, 2, fast) < 2) return 0;
   if(CopyBuffer(g_hSlow, 0, 1, 2, slow) < 2) return 0;
   if(CopyBuffer(g_hTrend, 0, 1, 1, trend) < 1) return 0;

   double close1 = iClose(_Symbol, PERIOD_CURRENT, 1);

   bool bullish = (fast[0] > slow[0] && close1 > trend[0]);
   bool bearish = (fast[0] < slow[0] && close1 < trend[0]);

   bool freshBull = bullish && (fast[1] <= slow[1]);
   bool freshBear = bearish && (fast[1] >= slow[1]);
   bool contBull  = bullish && (ci < InpChopLow);
   bool contBear  = bearish && (ci < InpChopLow);

   if(freshBull || contBull)
      return +1;
   if(freshBear || contBear)
      return -1;
   return 0;
}

//+------------------------------------------------------------------+
void OnTick()
{
   if(InpKillSwitch)
      return;

   datetime barTime = iTime(_Symbol, PERIOD_CURRENT, 0);
   if(barTime == 0 || barTime == g_lastBar)
      return;
   g_lastBar = barTime;

   datetime bar1Time = iTime(_Symbol, PERIOD_CURRENT, 1);
   if(bar1Time == 0)
      return;

   MqlDateTime dt;
   TimeToStruct(bar1Time, dt);

   if(dt.day_of_year != g_lastTradeDay)
   {
      g_lastTradeDay = dt.day_of_year;
      g_tradesToday = 0;
      g_dayStartBalance = AccountInfoDouble(ACCOUNT_BALANCE);
   }

   if(dt.hour >= InpExitHour || dt.day_of_week == 5 || dt.day_of_week == 0 || dt.day_of_week == 6)
   {
      if(CountPositions() > 0)
         CloseAll("flat");
      return;
   }

   if(dt.hour < InpStartHour || dt.hour >= InpEndHour)
      return;
   if(!IsTradeDay(dt.day_of_week))
      return;
   if(g_tradesToday >= InpMaxPerDay || CountPositions() > 0 || IsDDExceeded())
      return;

   int signal = GetSignal();
   if(signal == 0)
      return;

   double atr[];
   ArraySetAsSeries(atr, true);
   if(CopyBuffer(g_hATR14, 0, 1, 1, atr) < 1)
      return;

   double slDist = atr[0] * InpSL_ATR_Mult;
   if(slDist < InpMinSLPoints * _Point) slDist = InpMinSLPoints * _Point;
   if(slDist > InpMaxSLPoints * _Point) return;

   bool isBuy = (signal == +1);
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double sl = isBuy ? ask - slDist : bid + slDist;
   double tp = isBuy ? ask + slDist * InpTP_Ratio : bid - slDist * InpTP_Ratio;

   long stopsLevel = 0;
   SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL, stopsLevel);
   if(slDist < stopsLevel * _Point)
      return;

   double lot = CalcLot(slDist);
   if(lot <= 0)
      return;

   int digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
   sl = NormalizeDouble(sl, digits);
   tp = NormalizeDouble(tp, digits);

   MqlTradeResult res = {};
   if(!SendDealWithRetry(isBuy ? ORDER_TYPE_BUY : ORDER_TYPE_SELL, lot, sl, tp, 0,
                         StringFormat("CHOPT|CI=%.1f", ComputeChoppiness(1)), res))
      return;

   if(IsSuccessfulRetcode(res.retcode))
   {
      g_tradesToday++;
      PrintFormat("[CHOPTREND] %s lot=%.2f @ %.5f CI=%.1f",
                  isBuy ? "BUY" : "SELL", lot, res.price, ComputeChoppiness(1));
   }
}

//+------------------------------------------------------------------+
double OnTester()
{
   double pf = TesterStatistics(STAT_PROFIT_FACTOR);
   double n  = TesterStatistics(STAT_TRADES);
   if(n < 20) return 0;
   return pf * MathSqrt(n);
}
