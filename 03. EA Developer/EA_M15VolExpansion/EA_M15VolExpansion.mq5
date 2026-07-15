//+------------------------------------------------------------------+
//| EA_M15VolExpansion.mq5 — RV-ratio vol-expansion breakout (M15)   |
//| Symbol: USDJPY | Period: M15 | Magic: 880902                     |
//|                                                                   |
//| Near-miss seed: S639 / EA_VolCluster (PF~1.21, Type #86).        |
//| Independent closed-bar[1] cadence-book transfer for GOAL.         |
//| Hypothesis: HYP-VOLEXP-M15-001                                    |
//|                                                                   |
//| When short RV / long RV exceeds expansion threshold, trade the   |
//| recent closed-bar body direction only if aligned with EMA50.     |
//| Weekend flat. Risk 0.5%. No day-of-week mining.                  |
//+------------------------------------------------------------------+
#property copyright "SonicR / EA_M15VolExpansion"
#property version   "1.00"
#property strict

#include <Trade\Trade.mqh>

input group "=== General ==="
input ulong    InpMagic         = 880902;
input int      InpDeviation     = 30;
input bool     InpKillSwitch    = false;

input group "=== Volatility Expansion ==="
input int      InpRVShort       = 5;
input int      InpRVLong        = 20;
input double   InpExpansionMult = 1.50;
input int      InpBreakoutBars  = 3;
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
input int      InpMinSLPoints   = 50;
input int      InpMaxSLPoints   = 800;
input int      InpMaxPerDay     = 2;
input double   InpDailyDD       = 4.0;

CTrade   g_trade;
int      g_hATR   = INVALID_HANDLE;
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

   g_hATR   = iATR(_Symbol, PERIOD_CURRENT, 14);
   g_hTrend = iMA(_Symbol, PERIOD_CURRENT, InpTrendEMA, 0, MODE_EMA, PRICE_CLOSE);
   if(g_hATR == INVALID_HANDLE || g_hTrend == INVALID_HANDLE)
      return INIT_FAILED;

   g_dayStartBalance = AccountInfoDouble(ACCOUNT_BALANCE);
   PrintFormat("[M15VOLEXP] HYP-VOLEXP-M15-001 | RV %d/%d exp>=%.2f risk=%.2f%%",
               InpRVShort, InpRVLong, InpExpansionMult, InpRiskPct);
   return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   if(g_hATR != INVALID_HANDLE) IndicatorRelease(g_hATR);
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
         if(!OrderSend(req, tmp))
         {
            if(IsRetryableRetcode(tmp.retcode) || GetLastError() != 0)
            {
               Sleep(50);
               continue;
            }
            return false;
         }
         res = tmp;
         if(IsSuccessfulRetcode(tmp.retcode))
            return true;
         if(IsRetryableRetcode(tmp.retcode))
         {
            Sleep(50);
            continue;
         }
         return false;
      }
   }
   return false;
}

//+------------------------------------------------------------------+
void CloseAll()
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong t = PositionGetTicket(i);
      if(t <= 0 ||
         PositionGetInteger(POSITION_MAGIC) != (long)InpMagic ||
         PositionGetString(POSITION_SYMBOL) != _Symbol)
         continue;

      long ptype = PositionGetInteger(POSITION_TYPE);
      double vol = PositionGetDouble(POSITION_VOLUME);
      ENUM_ORDER_TYPE closeType = (ptype == POSITION_TYPE_BUY ? ORDER_TYPE_SELL : ORDER_TYPE_BUY);
      MqlTradeResult res = {};
      SendDealWithRetry(closeType, vol, 0.0, 0.0, t, "M15VOLEXP|flat", res);
   }
}

//+------------------------------------------------------------------+
bool IsDDExceeded()
{
   if(g_dayStartBalance <= 0.0)
      return false;
   double eq = AccountInfoDouble(ACCOUNT_EQUITY);
   return ((g_dayStartBalance - eq) / g_dayStartBalance * 100.0) >= InpDailyDD;
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
double CalcLot(const double slDist)
{
   if(slDist <= 0.0)
      return 0.0;
   double balance = AccountInfoDouble(ACCOUNT_BALANCE);
   double riskCash = balance * InpRiskPct / 100.0;
   double tickValue = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
   double tickSize  = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   if(tickValue <= 0.0 || tickSize <= 0.0)
      return 0.0;

   double lot = riskCash / (slDist / tickSize * tickValue);
   lot = MathMin(lot, InpMaxLot);
   lot = MathMin(lot, SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX));
   lot = MathMax(lot, SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN));
   double step = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   if(step > 0.0)
      lot = MathFloor(lot / step) * step;
   return lot;
}

//+------------------------------------------------------------------+
double ComputeRV(const int shift, const int window)
{
   if(window <= 1)
      return 0.0;

   double mean = 0.0;
   double returns[];
   ArrayResize(returns, window);
   for(int i = 0; i < window; i++)
   {
      double c1 = iClose(_Symbol, PERIOD_CURRENT, shift + i);
      double c2 = iClose(_Symbol, PERIOD_CURRENT, shift + i + 1);
      if(c1 <= 0.0 || c2 <= 0.0)
         return 0.0;
      returns[i] = MathLog(c1 / c2);
      mean += returns[i];
   }
   mean /= (double)window;

   double var = 0.0;
   for(int i = 0; i < window; i++)
   {
      double d = returns[i] - mean;
      var += d * d;
   }
   return MathSqrt(var / (double)window);
}

//+------------------------------------------------------------------+
int GetSignal(double &outRatio)
{
   outRatio = 0.0;
   double rvShort = ComputeRV(1, InpRVShort);
   double rvLong  = ComputeRV(1, InpRVLong);
   if(rvLong <= 0.0)
      return 0;

   outRatio = rvShort / rvLong;
   if(outRatio < InpExpansionMult)
      return 0;

   double moveSum = 0.0;
   for(int i = 1; i <= InpBreakoutBars; i++)
      moveSum += iClose(_Symbol, PERIOD_CURRENT, i) - iOpen(_Symbol, PERIOD_CURRENT, i);

   double trend[];
   ArraySetAsSeries(trend, true);
   if(CopyBuffer(g_hTrend, 0, 1, 1, trend) < 1)
      return 0;

   double close1 = iClose(_Symbol, PERIOD_CURRENT, 1);
   bool upTrend = (close1 > trend[0]);
   bool downTrend = (close1 < trend[0]);

   if(moveSum > 0.0 && upTrend)
      return +1;
   if(moveSum < 0.0 && downTrend)
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

   MqlDateTime dt;
   TimeToStruct(barTime, dt);
   if(dt.day_of_year != g_lastTradeDay)
   {
      g_lastTradeDay = dt.day_of_year;
      g_tradesToday = 0;
      g_dayStartBalance = AccountInfoDouble(ACCOUNT_BALANCE);
   }

   if(dt.hour >= InpExitHour && CountPositions() > 0)
   {
      CloseAll();
      return;
   }

   if(dt.hour < InpStartHour || dt.hour >= InpEndHour)
      return;
   if(!IsTradeDay(dt.day_of_week))
      return;
   if(g_tradesToday >= InpMaxPerDay || CountPositions() > 0 || IsDDExceeded())
      return;

   double ratio = 0.0;
   int signal = GetSignal(ratio);
   if(signal == 0)
      return;

   double atr[];
   ArraySetAsSeries(atr, true);
   if(CopyBuffer(g_hATR, 0, 1, 1, atr) < 1 || atr[0] <= 0.0)
      return;

   double slDist = atr[0] * InpSL_ATR_Mult;
   if(slDist < InpMinSLPoints * _Point)
      slDist = InpMinSLPoints * _Point;
   if(slDist > InpMaxSLPoints * _Point)
      return;

   bool isBuy = (signal == +1);
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double entry = (isBuy ? ask : bid);
   double sl = (isBuy ? entry - slDist : entry + slDist);
   double tp = (isBuy ? entry + slDist * InpTP_Ratio : entry - slDist * InpTP_Ratio);

   int digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
   sl = NormalizeDouble(sl, digits);
   tp = NormalizeDouble(tp, digits);

   double lot = CalcLot(slDist);
   if(lot <= 0.0)
      return;

   MqlTradeResult res = {};
   ENUM_ORDER_TYPE orderType = (isBuy ? ORDER_TYPE_BUY : ORDER_TYPE_SELL);
   string comment = StringFormat("M15VOLEXP|r=%.2f", ratio);
   if(!SendDealWithRetry(orderType, lot, sl, tp, 0, comment, res))
      return;

   g_tradesToday++;
   PrintFormat("[M15VOLEXP] %s lot=%.2f @ %.5f ratio=%.2f",
               (isBuy ? "BUY" : "SELL"), lot, res.price, ratio);
}

//+------------------------------------------------------------------+
double OnTester()
{
   double pf = TesterStatistics(STAT_PROFIT_FACTOR);
   double n  = TesterStatistics(STAT_TRADES);
   if(n < 20.0)
      return 0.0;
   return pf * MathSqrt(n);
}
//+------------------------------------------------------------------+
