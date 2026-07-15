//+------------------------------------------------------------------+
//| EA_H1SwingFailure.mq5 — H1 structural swing-failure fade           |
//| Symbol: USDJPY | Period: H1 | Magic: 880951                        |
//|                                                                    |
//| Hypothesis: HYP-H1-SWING-FAILURE-001                                |
//| Confirmed L=2 pivot swing (closed-bar only). Pierce beyond swing   |
//| then close back inside = failed structural break → fade.           |
//| Not Failed-ORB (no session OR), not PDH/LiqSweep, not FractalBreak |
//| (that was breakout), not EMA-stretch, not M15 fade shelf.          |
//|                                                                    |
//| Mon–Thu a priori; weekend flat; risk 0.5%. No day mining.          |
//+------------------------------------------------------------------+
#property copyright "SonicR / EA_H1SwingFailure"
#property version   "1.00"
#property strict

#include <Trade\Trade.mqh>

input group "=== General ==="
input ulong    InpMagic         = 880951;
input int      InpDeviation     = 30;
input bool     InpKillSwitch    = false;

input group "=== Swing Failure ==="
input int      InpPivotL        = 2;      // bars each side (frozen)
input int      InpMaxSwingAge   = 40;     // max H1 bars since swing
input double   InpPierceBufATR  = 0.05;
input double   InpBodyRatio     = 0.30;

input group "=== Session (server hours) ==="
input int      InpTradeStart    = 1;
input int      InpTradeEnd      = 21;
input int      InpFlatHour      = 22;
input bool     InpTradeMon      = true;
input bool     InpTradeTue      = true;
input bool     InpTradeWed      = true;
input bool     InpTradeThu      = true;
input bool     InpTradeFri      = false;

input group "=== Risk ==="
input double   InpRiskPct       = 0.50;
input double   InpMaxLot        = 1.0;
input double   InpSL_BufferATR  = 0.15;
input double   InpTP_Ratio      = 1.50;
input int      InpMinSLPoints   = 80;
input int      InpMaxSLPoints   = 2500;
input int      InpMaxPerDay     = 1;
input double   InpDailyDD       = 4.0;
input int      InpMaxHoldBars   = 24;
input int      InpMaxSpreadPts  = 50;

CTrade   g_trade;
int      g_hATR  = INVALID_HANDLE;
datetime g_lastBar = 0;
int      g_tradesToday = 0;
int      g_lastTradeDay = -1;
double   g_dayStartBalance = 0;
int      g_holdBars = 0;

double   g_swingHi = 0.0;
double   g_swingLo = 0.0;
int      g_swingHiAge = 9999;
int      g_swingLoAge = 9999;
bool     g_usedSwingHi = false;
bool     g_usedSwingLo = false;

//+------------------------------------------------------------------+
int OnInit()
{
   if(Period() != PERIOD_H1)
   {
      Print("[H1SF] FAIL — chart must be H1");
      return INIT_FAILED;
   }
   g_trade.SetExpertMagicNumber((long)InpMagic);
   g_trade.SetDeviationInPoints(InpDeviation);
   g_hATR = iATR(_Symbol, PERIOD_H1, 14);
   if(g_hATR == INVALID_HANDLE)
      return INIT_FAILED;
   g_dayStartBalance = AccountInfoDouble(ACCOUNT_BALANCE);
   PrintFormat("[H1SF] HYP-H1-SWING-FAILURE-001 | PivotL=%d TP=%.2fR risk=%.2f%%",
               InpPivotL, InpTP_Ratio, InpRiskPct);
   return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   if(g_hATR != INVALID_HANDLE) IndicatorRelease(g_hATR);
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
                        "H1SF|" + reason, res);
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
// Update last confirmed pivot using closed bars only.
// Pivot at shift = 1+InpPivotL is fully confirmed when bar[1] just closed.
void UpdateSwings()
{
   int sw = 1 + InpPivotL; // earliest fully confirmed pivot center
   bool isHi = true;
   bool isLo = true;
   double hSw = iHigh(_Symbol, PERIOD_H1, sw);
   double lSw = iLow(_Symbol, PERIOD_H1, sw);
   for(int i = 1; i <= InpPivotL; i++)
   {
      if(iHigh(_Symbol, PERIOD_H1, sw - i) >= hSw ||
         iHigh(_Symbol, PERIOD_H1, sw + i) >= hSw)
         isHi = false;
      if(iLow(_Symbol, PERIOD_H1, sw - i) <= lSw ||
         iLow(_Symbol, PERIOD_H1, sw + i) <= lSw)
         isLo = false;
   }

   g_swingHiAge++;
   g_swingLoAge++;

   if(isHi)
   {
      g_swingHi = hSw;
      g_swingHiAge = 0;
      g_usedSwingHi = false;
   }
   if(isLo)
   {
      g_swingLo = lSw;
      g_swingLoAge = 0;
      g_usedSwingLo = false;
   }
}

//+------------------------------------------------------------------+
// Signal from closed bar[1] vs last confirmed swing.
int GetSignal(double &pierceExtreme)
{
   pierceExtreme = 0.0;
   double atr[];
   ArraySetAsSeries(atr, true);
   if(CopyBuffer(g_hATR, 0, 1, 1, atr) < 1 || atr[0] <= 0.0)
      return 0;

   double bO = iOpen(_Symbol, PERIOD_H1, 1);
   double bH = iHigh(_Symbol, PERIOD_H1, 1);
   double bL = iLow(_Symbol, PERIOD_H1, 1);
   double bC = iClose(_Symbol, PERIOD_H1, 1);
   double range1 = bH - bL;
   if(range1 <= 0.0)
      return 0;
   if(MathAbs(bC - bO) / range1 < InpBodyRatio)
      return 0;

   double buf = atr[0] * InpPierceBufATR;

   // Failed break of swing high → fade short
   if(!g_usedSwingHi && g_swingHi > 0.0 && g_swingHiAge <= InpMaxSwingAge)
   {
      if(bH > g_swingHi + buf && bC < g_swingHi)
      {
         pierceExtreme = bH;
         return -1;
      }
   }
   // Failed break of swing low → fade long
   if(!g_usedSwingLo && g_swingLo > 0.0 && g_swingLoAge <= InpMaxSwingAge)
   {
      if(bL < g_swingLo - buf && bC > g_swingLo)
      {
         pierceExtreme = bL;
         return +1;
      }
   }
   return 0;
}

//+------------------------------------------------------------------+
void OnTick()
{
   if(InpKillSwitch)
      return;

   datetime barTime = iTime(_Symbol, PERIOD_H1, 0);
   if(barTime == 0 || barTime == g_lastBar)
      return;
   g_lastBar = barTime;

   datetime bar1Time = iTime(_Symbol, PERIOD_H1, 1);
   if(bar1Time == 0)
      return;

   MqlDateTime dt;
   TimeToStruct(bar1Time, dt);
   int dayKey = dt.year * 1000 + dt.day_of_year;

   if(dayKey != g_lastTradeDay)
   {
      g_lastTradeDay = dayKey;
      g_tradesToday = 0;
      g_dayStartBalance = AccountInfoDouble(ACCOUNT_BALANCE);
   }

   UpdateSwings();

   if(CountPositions() > 0)
   {
      g_holdBars++;
      if(g_holdBars >= InpMaxHoldBars || dt.hour >= InpFlatHour ||
         dt.day_of_week == 5 || dt.day_of_week == 0 || dt.day_of_week == 6)
         CloseAll("flat");
      return;
   }
   g_holdBars = 0;

   if(dt.hour >= InpFlatHour || dt.day_of_week == 5 ||
      dt.day_of_week == 0 || dt.day_of_week == 6)
      return;
   if(!IsTradeDay(dt.day_of_week))
      return;
   if(dt.hour < InpTradeStart || dt.hour >= InpTradeEnd)
      return;
   if(g_tradesToday >= InpMaxPerDay || IsDDExceeded())
      return;

   long spread = SymbolInfoInteger(_Symbol, SYMBOL_SPREAD);
   if(spread > InpMaxSpreadPts)
      return;

   double atr[];
   ArraySetAsSeries(atr, true);
   if(CopyBuffer(g_hATR, 0, 1, 1, atr) < 1 || atr[0] <= 0.0)
      return;

   double pierce = 0.0;
   int signal = GetSignal(pierce);
   if(signal == 0)
      return;

   bool isBuy = (signal == +1);
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double entry = (isBuy ? ask : bid);
   double slRaw = (isBuy ? pierce - atr[0] * InpSL_BufferATR
                         : pierce + atr[0] * InpSL_BufferATR);
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
                         "H1SF|sfp", res))
      return;

   if(IsSuccessfulRetcode(res.retcode))
   {
      g_tradesToday++;
      g_holdBars = 0;
      if(isBuy)
         g_usedSwingLo = true;
      else
         g_usedSwingHi = true;
      PrintFormat("[H1SF] %s lot=%.2f @ %.5f pierce=%.5f",
                  isBuy ? "BUY" : "SELL", lot, res.price, pierce);
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
