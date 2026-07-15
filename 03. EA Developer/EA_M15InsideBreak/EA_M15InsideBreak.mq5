//+------------------------------------------------------------------+
//| EA_M15InsideBreak.mq5 — Inside-bar breakout + H4 bias (M15)      |
//| Symbol: USDJPY | Period: M15 | Magic: 880922                     |
//|                                                                   |
//| Near-miss seed: S226/S232 EA_InsideBar (PF~1.32–1.65).           |
//| Independent closed-bar[1] GOAL transfer after ChopTrend kill.    |
//| Hypothesis: HYP-INSIDEBAR-M15-001                                  |
//|                                                                   |
//| Detect compression at bar[2] (inside mother bar[3]); enter when  |
//| closed bar[1] breaks IB range with H4 EMA50 bias. Weekend flat.  |
//| Risk 0.5%. Prereg frozen 2026-07-14; Model 0 screen authorized.  |
//+------------------------------------------------------------------+
#property copyright "SonicR / EA_M15InsideBreak"
#property version   "1.00"
#property strict

#include <Trade\Trade.mqh>

input group "=== General ==="
input ulong    InpMagic         = 880922;
input int      InpDeviation     = 30;
input bool     InpKillSwitch    = false;

input group "=== Inside Bar ==="
input double   InpMinIBRangeATR = 0.20;
input double   InpMaxIBRangeATR = 0.80;
input double   InpBreakBufATR   = 0.05;
input double   InpMinBreakBody  = 0.50;
input int      InpH4_EMA        = 50;
input bool     InpUseH4Bias     = true;

input group "=== Session (server hours) ==="
input int      InpKZ1Start      = 9;
input int      InpKZ1End        = 12;
input int      InpKZ2Start      = 15;
input int      InpKZ2End        = 18;
input int      InpExitHour      = 21;
input bool     InpTradeMon      = true;
input bool     InpTradeTue      = true;
input bool     InpTradeWed      = true;
input bool     InpTradeThu      = true;
input bool     InpTradeFri      = false;  // weekend-flat: no Friday entries

input group "=== Risk ==="
input double   InpRiskPct       = 0.50;
input double   InpMaxLot        = 1.0;
input double   InpSL_BufferATR  = 0.20;
input double   InpTP_Ratio      = 1.5;
input int      InpMinSLPoints   = 50;
input int      InpMaxSLPoints   = 800;
input int      InpMaxPerDay     = 2;
input double   InpDailyDD       = 4.0;

CTrade   g_trade;
int      g_hATR  = INVALID_HANDLE;
int      g_hH4   = INVALID_HANDLE;
datetime g_lastBar = 0;
int      g_tradesToday = 0;
int      g_lastTradeDay = -1;
double   g_dayStartBalance = 0;

//+------------------------------------------------------------------+
int OnInit()
{
   g_trade.SetExpertMagicNumber((long)InpMagic);
   g_trade.SetDeviationInPoints(InpDeviation);

   g_hATR = iATR(_Symbol, PERIOD_CURRENT, 14);
   g_hH4  = iMA(_Symbol, PERIOD_H4, InpH4_EMA, 0, MODE_EMA, PRICE_CLOSE);
   if(g_hATR == INVALID_HANDLE || g_hH4 == INVALID_HANDLE)
      return INIT_FAILED;

   g_dayStartBalance = AccountInfoDouble(ACCOUNT_BALANCE);
   PrintFormat("[M15IB] HYP-INSIDEBAR-M15-001 | IB ATR[%.2f,%.2f] H4EMA=%d risk=%.2f%%",
               InpMinIBRangeATR, InpMaxIBRangeATR, InpH4_EMA, InpRiskPct);
   return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   if(g_hATR != INVALID_HANDLE) IndicatorRelease(g_hATR);
   if(g_hH4  != INVALID_HANDLE) IndicatorRelease(g_hH4);
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
      SendDealWithRetry(isBuy ? ORDER_TYPE_SELL : ORDER_TYPE_BUY,
                        PositionGetDouble(POSITION_VOLUME), 0.0, 0.0, t,
                        "M15IB|" + reason, res);
   }
}

//+------------------------------------------------------------------+
bool IsDDExceeded()
{
   if(g_dayStartBalance <= 0.0)
      return false;
   return ((g_dayStartBalance - AccountInfoDouble(ACCOUNT_EQUITY)) /
           g_dayStartBalance * 100.0) >= InpDailyDD;
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
bool InKillZone(const int hour)
{
   return ((hour >= InpKZ1Start && hour < InpKZ1End) ||
           (hour >= InpKZ2Start && hour < InpKZ2End));
}

//+------------------------------------------------------------------+
double CalcLot(const double slDist)
{
   if(slDist <= 0.0)
      return 0.0;
   double bal = AccountInfoDouble(ACCOUNT_BALANCE);
   double riskCash = bal * InpRiskPct / 100.0;
   double tv = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
   double ts = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   if(tv <= 0.0 || ts <= 0.0)
      return 0.0;
   double lot = riskCash / (slDist / ts * tv);
   lot = MathMin(lot, InpMaxLot);
   lot = MathMin(lot, SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX));
   lot = MathMax(lot, SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN));
   double step = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   if(step > 0.0)
      lot = MathFloor(lot / step) * step;
   return lot;
}

//+------------------------------------------------------------------+
// Closed-bar only: mother=3, inside=2, break=1.
int GetSignal(double &ibHigh, double &ibLow)
{
   ibHigh = 0.0;
   ibLow  = 0.0;

   double atr[];
   ArraySetAsSeries(atr, true);
   if(CopyBuffer(g_hATR, 0, 1, 1, atr) < 1 || atr[0] <= 0.0)
      return 0;

   double mH = iHigh(_Symbol, PERIOD_CURRENT, 3);
   double mL = iLow(_Symbol, PERIOD_CURRENT, 3);
   double iH = iHigh(_Symbol, PERIOD_CURRENT, 2);
   double iL = iLow(_Symbol, PERIOD_CURRENT, 2);
   double bH = iHigh(_Symbol, PERIOD_CURRENT, 1);
   double bL = iLow(_Symbol, PERIOD_CURRENT, 1);
   double bO = iOpen(_Symbol, PERIOD_CURRENT, 1);
   double bC = iClose(_Symbol, PERIOD_CURRENT, 1);

   // Inside bar at shift 2 relative to mother at shift 3.
   if(!(iH < mH && iL > mL))
      return 0;

   double ibRange = iH - iL;
   if(ibRange < atr[0] * InpMinIBRangeATR || ibRange > atr[0] * InpMaxIBRangeATR)
      return 0;

   double buf = atr[0] * InpBreakBufATR;
   double body = MathAbs(bC - bO);
   double range1 = bH - bL;
   if(range1 <= 0.0 || body / range1 < InpMinBreakBody)
      return 0;

   int dir = 0;
   if(bC > iH + buf)
      dir = +1;
   else if(bC < iL - buf)
      dir = -1;
   else
      return 0;

   if(InpUseH4Bias)
   {
      double h4[];
      ArraySetAsSeries(h4, true);
      if(CopyBuffer(g_hH4, 0, 1, 1, h4) < 1)
         return 0;
      if(dir > 0 && bC < h4[0])
         return 0;
      if(dir < 0 && bC > h4[0])
         return 0;
   }

   ibHigh = iH;
   ibLow  = iL;
   return dir;
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

   if(!InKillZone(dt.hour))
      return;
   if(!IsTradeDay(dt.day_of_week))
      return;
   if(g_tradesToday >= InpMaxPerDay || CountPositions() > 0 || IsDDExceeded())
      return;

   double ibHigh = 0.0, ibLow = 0.0;
   int signal = GetSignal(ibHigh, ibLow);
   if(signal == 0)
      return;

   double atr[];
   ArraySetAsSeries(atr, true);
   if(CopyBuffer(g_hATR, 0, 1, 1, atr) < 1 || atr[0] <= 0.0)
      return;

   bool isBuy = (signal == +1);
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double entry = (isBuy ? ask : bid);
   double slRaw = (isBuy ? ibLow - atr[0] * InpSL_BufferATR
                         : ibHigh + atr[0] * InpSL_BufferATR);
   double slDist = MathAbs(entry - slRaw);
   if(slDist < InpMinSLPoints * _Point)
      slDist = InpMinSLPoints * _Point;
   if(slDist > InpMaxSLPoints * _Point)
      return;

   double sl = (isBuy ? entry - slDist : entry + slDist);
   double tp = (isBuy ? entry + slDist * InpTP_Ratio : entry - slDist * InpTP_Ratio);

   int digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
   sl = NormalizeDouble(sl, digits);
   tp = NormalizeDouble(tp, digits);

   double lot = CalcLot(slDist);
   if(lot <= 0.0)
      return;

   MqlTradeResult res = {};
   if(!SendDealWithRetry(isBuy ? ORDER_TYPE_BUY : ORDER_TYPE_SELL, lot, sl, tp, 0,
                         "M15IB|brk", res))
      return;

   if(IsSuccessfulRetcode(res.retcode))
   {
      g_tradesToday++;
      PrintFormat("[M15IB] %s lot=%.2f @ %.5f",
                  isBuy ? "BUY" : "SELL", lot, res.price);
   }
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
