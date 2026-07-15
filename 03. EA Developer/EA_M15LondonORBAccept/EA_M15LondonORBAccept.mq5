//+------------------------------------------------------------------+
//| EA_M15LondonORBAccept.mq5 — London ORB acceptance rebuild (M15)  |
//| Symbol: USDJPY | Period: M15 | Magic: 880960                     |
//|                                                                   |
//| Hypothesis: HYP-LONDON-ORB-ACCEPT-001                              |
//| Structural child of parked LondonORB (PF~1.17) — NOT densify SB, |
//| NOT FailedORB fade. Require two consecutive closed closes outside |
//| ORB + no reclaim of ORB mid before entry.                         |
//| Closed-bar[1]/[2] only; Mon–Thu; weekend flat; risk 0.5%.       |
//+------------------------------------------------------------------+
#property copyright "SonicR / EA_M15LondonORBAccept"
#property version   "1.00"
#property strict

#include <Trade\Trade.mqh>

input group "=== General ==="
input ulong    InpMagic         = 880960;
input int      InpDeviation     = 30;
input bool     InpKillSwitch    = false;

input group "=== London ORB Acceptance ==="
input int      InpOrbStart      = 9;
input int      InpOrbEnd        = 10;
input double   InpRangeMinATR   = 0.25;
input double   InpRangeMaxATR   = 2.50;
input double   InpBrkBufferATR  = 0.10;
input double   InpBodyRatio     = 0.35;
input int      InpEMAPeriod     = 50;
input bool     InpUseTrendFilter= true;

input group "=== Session (server hours) ==="
input int      InpTradeStart    = 10;
input int      InpTradeEnd      = 16;
input int      InpFlatHour      = 21;
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
input int      InpMinSLPoints   = 50;
input int      InpMaxSLPoints   = 1200;
input int      InpMaxPerDay     = 1;
input double   InpDailyDD       = 4.0;
input int      InpMaxHoldBars   = 32;
input int      InpMaxSpreadPts  = 50;

CTrade   g_trade;
int      g_hATR  = INVALID_HANDLE;
int      g_hEMA  = INVALID_HANDLE;
datetime g_lastBar = 0;
int      g_tradesToday = 0;
int      g_lastTradeDay = -1;
double   g_dayStartBalance = 0;
int      g_holdBars = 0;

double   g_orbHi = 0.0;
double   g_orbLo = 0.0;
bool     g_orbBuilding = false;
bool     g_orbLocked = false;
bool     g_orbValid = false;
bool     g_brokeToday = false;

//+------------------------------------------------------------------+
int OnInit()
{
   g_trade.SetExpertMagicNumber((long)InpMagic);
   g_trade.SetDeviationInPoints(InpDeviation);
   g_hATR = iATR(_Symbol, PERIOD_CURRENT, 14);
   if(InpUseTrendFilter)
      g_hEMA = iMA(_Symbol, PERIOD_D1, InpEMAPeriod, 0, MODE_EMA, PRICE_CLOSE);
   if(g_hATR == INVALID_HANDLE)
      return INIT_FAILED;
   if(InpUseTrendFilter && g_hEMA == INVALID_HANDLE)
      return INIT_FAILED;
   g_dayStartBalance = AccountInfoDouble(ACCOUNT_BALANCE);
   PrintFormat("[LORBA] HYP-LONDON-ORB-ACCEPT-001 | dual-close accept ORB[%d,%d)",
               InpOrbStart, InpOrbEnd);
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   if(g_hATR != INVALID_HANDLE) IndicatorRelease(g_hATR);
   if(g_hEMA != INVALID_HANDLE) IndicatorRelease(g_hEMA);
}

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

bool IsSuccessfulRetcode(const uint retcode)
{
   return(retcode == TRADE_RETCODE_DONE ||
          retcode == TRADE_RETCODE_PLACED ||
          retcode == TRADE_RETCODE_DONE_PARTIAL);
}

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
                        "LORBA|" + reason, res);
   }
}

bool IsDDExceeded()
{
   if(g_dayStartBalance <= 0.0)
      return false;
   return ((g_dayStartBalance - AccountInfoDouble(ACCOUNT_EQUITY)) /
           g_dayStartBalance * 100.0) >= InpDailyDD;
}

bool IsTradeDay(const int dow)
{
   if(dow == 1) return InpTradeMon;
   if(dow == 2) return InpTradeTue;
   if(dow == 3) return InpTradeWed;
   if(dow == 4) return InpTradeThu;
   if(dow == 5) return InpTradeFri;
   return false;
}

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

void ResetOrbDay(const int dayKey)
{
   g_orbHi = 0.0;
   g_orbLo = 0.0;
   g_orbBuilding = false;
   g_orbLocked = false;
   g_orbValid = false;
   g_brokeToday = false;
}

void UpdateOrbFromClosedBar(const int hour, const double h, const double l, const double atr)
{
   if(hour >= InpOrbStart && hour < InpOrbEnd)
   {
      if(!g_orbBuilding)
      {
         g_orbHi = h;
         g_orbLo = l;
         g_orbBuilding = true;
         g_orbLocked = false;
         g_orbValid = false;
      }
      else
      {
         if(h > g_orbHi) g_orbHi = h;
         if(l < g_orbLo) g_orbLo = l;
      }
      return;
   }
   if(g_orbBuilding && !g_orbLocked && hour >= InpOrbEnd)
   {
      g_orbLocked = true;
      g_orbBuilding = false;
      double rng = g_orbHi - g_orbLo;
      g_orbValid = (atr > 0.0 &&
                    rng >= atr * InpRangeMinATR &&
                    rng <= atr * InpRangeMaxATR &&
                    g_orbHi > g_orbLo);
   }
}

// Dual closed-bar acceptance: bar[1] and bar[2] both close outside ORB;
// neither close reclaims ORB mid.
int GetSignal(const int hour, double &orbHi, double &orbLo)
{
   orbHi = 0.0;
   orbLo = 0.0;
   if(!g_orbLocked || !g_orbValid || g_brokeToday)
      return 0;
   if(hour < InpTradeStart || hour >= InpTradeEnd)
      return 0;

   double atr[];
   ArraySetAsSeries(atr, true);
   if(CopyBuffer(g_hATR, 0, 1, 1, atr) < 1 || atr[0] <= 0.0)
      return 0;

   double c1 = iClose(_Symbol, PERIOD_CURRENT, 1);
   double o1 = iOpen(_Symbol, PERIOD_CURRENT, 1);
   double h1 = iHigh(_Symbol, PERIOD_CURRENT, 1);
   double l1 = iLow(_Symbol, PERIOD_CURRENT, 1);
   double c2 = iClose(_Symbol, PERIOD_CURRENT, 2);
   double o2 = iOpen(_Symbol, PERIOD_CURRENT, 2);
   double range1 = h1 - l1;
   if(range1 <= 0.0)
      return 0;
   if(MathAbs(c1 - o1) / range1 < InpBodyRatio)
      return 0;

   double buf = atr[0] * InpBrkBufferATR;
   double mid = 0.5 * (g_orbHi + g_orbLo);
   int dir = 0;
   if(c1 > g_orbHi + buf && c2 > g_orbHi + buf && c1 > mid && c2 > mid)
      dir = +1;
   else if(c1 < g_orbLo - buf && c2 < g_orbLo - buf && c1 < mid && c2 < mid)
      dir = -1;
   else
      return 0;

   // Optional: bar[2] body also non-trivial
   double range2 = iHigh(_Symbol, PERIOD_CURRENT, 2) - iLow(_Symbol, PERIOD_CURRENT, 2);
   if(range2 <= 0.0 || MathAbs(c2 - o2) / range2 < 0.25)
      return 0;

   if(InpUseTrendFilter)
   {
      double ema[];
      ArraySetAsSeries(ema, true);
      if(CopyBuffer(g_hEMA, 0, 1, 1, ema) < 1)
         return 0;
      if(dir > 0 && c1 < ema[0])
         return 0;
      if(dir < 0 && c1 > ema[0])
         return 0;
   }

   orbHi = g_orbHi;
   orbLo = g_orbLo;
   return dir;
}

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
   int dayKey = dt.year * 1000 + dt.day_of_year;

   if(dayKey != g_lastTradeDay)
   {
      g_lastTradeDay = dayKey;
      g_tradesToday = 0;
      g_dayStartBalance = AccountInfoDouble(ACCOUNT_BALANCE);
      ResetOrbDay(dayKey);
   }

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

   double atr[];
   ArraySetAsSeries(atr, true);
   if(CopyBuffer(g_hATR, 0, 1, 1, atr) < 1 || atr[0] <= 0.0)
      return;

   UpdateOrbFromClosedBar(dt.hour, iHigh(_Symbol, PERIOD_CURRENT, 1),
                          iLow(_Symbol, PERIOD_CURRENT, 1), atr[0]);

   if(!IsTradeDay(dt.day_of_week))
      return;
   if(g_tradesToday >= InpMaxPerDay || IsDDExceeded())
      return;
   if(SymbolInfoInteger(_Symbol, SYMBOL_SPREAD) > InpMaxSpreadPts)
      return;

   double orbHi = 0.0, orbLo = 0.0;
   int signal = GetSignal(dt.hour, orbHi, orbLo);
   if(signal == 0)
      return;

   bool isBuy = (signal == +1);
   double entry = (isBuy ? SymbolInfoDouble(_Symbol, SYMBOL_ASK)
                         : SymbolInfoDouble(_Symbol, SYMBOL_BID));
   double slRaw = (isBuy ? orbLo - atr[0] * InpSL_BufferATR
                         : orbHi + atr[0] * InpSL_BufferATR);
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
                         "LORBA|acc", res))
      return;
   if(IsSuccessfulRetcode(res.retcode))
   {
      g_tradesToday++;
      g_brokeToday = true;
      g_holdBars = 0;
   }
}

double OnTester()
{
   double pf = TesterStatistics(STAT_PROFIT_FACTOR);
   double n  = TesterStatistics(STAT_TRADES);
   if(n < 20.0)
      return 0.0;
   return pf * MathSqrt(n);
}
//+------------------------------------------------------------------+
