//+------------------------------------------------------------------+
//| EA_M15FailedORBFade.mq5 — London OR failed-auction fade          |
//| Symbol: USDJPY | Period: M15 | Magic: 880943                     |
//|                                                                   |
//| Hypothesis: HYP-FAILED-ORB-FADE-M15-001                            |
//| Opposite of parked LondonORB *break continuation*: after OR lock, |
//| a pierce of OR high/low that closes back inside is a failed       |
//| auction → fade toward OR mid. Same a-priori OR window [9,10) as   |
//| LondonORB (not mined). Independent of PDH/NY/Spark/ITSM/SB.       |
//|                                                                   |
//| Closed-bar[1] only. Mon–Thu; weekend flat; risk 0.5%.             |
//+------------------------------------------------------------------+
#property copyright "SonicR / EA_M15FailedORBFade"
#property version   "1.00"
#property strict

#include <Trade\Trade.mqh>

input group "=== General ==="
input ulong    InpMagic         = 880943;
input int      InpDeviation     = 30;
input bool     InpKillSwitch    = false;

input group "=== London OR (a priori same as LondonORB) ==="
input int      InpOrbStart      = 9;
input int      InpOrbEnd        = 10;
input double   InpRangeMinATR   = 0.25;
input double   InpRangeMaxATR   = 2.50;
input double   InpPierceBufATR  = 0.05;

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
bool     g_tradedToday = false;
int      g_orbDay = -1;

//+------------------------------------------------------------------+
int OnInit()
{
   g_trade.SetExpertMagicNumber((long)InpMagic);
   g_trade.SetDeviationInPoints(InpDeviation);
   g_hATR = iATR(_Symbol, PERIOD_CURRENT, 14);
   if(g_hATR == INVALID_HANDLE)
      return INIT_FAILED;
   g_dayStartBalance = AccountInfoDouble(ACCOUNT_BALANCE);
   PrintFormat("[FORB] HYP-FAILED-ORB-FADE-M15-001 | ORB[%d,%d) trade[%d,%d) TP=%.2fR",
               InpOrbStart, InpOrbEnd, InpTradeStart, InpTradeEnd, InpTP_Ratio);
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
                        "FORB|" + reason, res);
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
void ResetOrbDay(const int dayKey)
{
   g_orbDay = dayKey;
   g_orbHi = 0.0;
   g_orbLo = 0.0;
   g_orbBuilding = false;
   g_orbLocked = false;
   g_orbValid = false;
   g_tradedToday = false;
}

//+------------------------------------------------------------------+
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

//+------------------------------------------------------------------+
// Failed auction: pierce OR extreme then close back inside on bar[1].
int GetSignal(const int hour, double &pierceExt)
{
   pierceExt = 0.0;
   if(!g_orbLocked || !g_orbValid || g_tradedToday)
      return 0;
   if(hour < InpTradeStart || hour >= InpTradeEnd)
      return 0;

   double atr[];
   ArraySetAsSeries(atr, true);
   if(CopyBuffer(g_hATR, 0, 1, 1, atr) < 1 || atr[0] <= 0.0)
      return 0;

   double bH = iHigh(_Symbol, PERIOD_CURRENT, 1);
   double bL = iLow(_Symbol, PERIOD_CURRENT, 1);
   double bC = iClose(_Symbol, PERIOD_CURRENT, 1);
   double buf = atr[0] * InpPierceBufATR;

   // Inside OR close required for failed auction.
   if(bC >= g_orbHi || bC <= g_orbLo)
      return 0;

   if(bH > g_orbHi + buf)
   {
      pierceExt = bH;
      return -1; // fade short
   }
   if(bL < g_orbLo - buf)
   {
      pierceExt = bL;
      return +1; // fade long
   }
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
   int dayKey = dt.year * 1000 + dt.day_of_year;
   if(dayKey != g_orbDay)
      ResetOrbDay(dayKey);
   if(dayKey != g_lastTradeDay)
   {
      g_lastTradeDay = dayKey;
      g_tradesToday = 0;
      g_dayStartBalance = AccountInfoDouble(ACCOUNT_BALANCE);
   }

   double atr[];
   ArraySetAsSeries(atr, true);
   if(CopyBuffer(g_hATR, 0, 1, 1, atr) < 1 || atr[0] <= 0.0)
      return;

   double bH = iHigh(_Symbol, PERIOD_CURRENT, 1);
   double bL = iLow(_Symbol, PERIOD_CURRENT, 1);
   UpdateOrbFromClosedBar(dt.hour, bH, bL, atr[0]);

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
   if(g_tradesToday >= InpMaxPerDay || IsDDExceeded())
      return;

   long spread = SymbolInfoInteger(_Symbol, SYMBOL_SPREAD);
   if(spread > InpMaxSpreadPts)
      return;

   double pierceExt = 0.0;
   int signal = GetSignal(dt.hour, pierceExt);
   if(signal == 0)
      return;

   bool isBuy = (signal == +1);
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double entry = (isBuy ? ask : bid);

   // SL beyond pierce extreme.
   double slRaw = (isBuy ? pierceExt - atr[0] * InpSL_BufferATR
                         : pierceExt + atr[0] * InpSL_BufferATR);
   double slDist = MathAbs(entry - slRaw);
   if(slDist < InpMinSLPoints * _Point)
      slDist = InpMinSLPoints * _Point;
   if(slDist > InpMaxSLPoints * _Point)
      return;

   double sl = (isBuy ? entry - slDist : entry + slDist);
   // Prefer OR mid as structural TP if it is at least 0.8R away; else 1.5R.
   double mid = 0.5 * (g_orbHi + g_orbLo);
   double tpDist = slDist * InpTP_Ratio;
   double midDist = MathAbs(mid - entry);
   if(midDist >= slDist * 0.80 && midDist <= slDist * 2.50)
      tpDist = midDist;
   double tp = (isBuy ? entry + tpDist : entry - tpDist);

   int digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
   sl = NormalizeDouble(sl, digits);
   tp = NormalizeDouble(tp, digits);

   double lot = CalcLot(slDist);
   if(lot <= 0.0)
      return;

   MqlTradeResult res = {};
   if(!SendDealWithRetry(isBuy ? ORDER_TYPE_BUY : ORDER_TYPE_SELL, lot, sl, tp, 0,
                         "FORB|fail", res))
      return;

   if(IsSuccessfulRetcode(res.retcode))
   {
      g_tradesToday++;
      g_tradedToday = true;
      g_holdBars = 0;
      PrintFormat("[FORB] %s lot=%.2f @ %.5f OR=[%.5f,%.5f] pierce=%.5f",
                  isBuy ? "BUY" : "SELL", lot, res.price, g_orbLo, g_orbHi, pierceExt);
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
