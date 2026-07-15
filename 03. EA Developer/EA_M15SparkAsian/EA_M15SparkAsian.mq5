//+------------------------------------------------------------------+
//| EA_M15SparkAsian.mq5 — Asian range → LDN/NY breakout (M15)       |
//| Symbol: USDJPY | Period: M15 | Magic: 880930                     |
//|                                                                   |
//| Near-miss seed: S111 / EA_Spark v1.4 USDJPY+ (PF~1.26, ~71/yr).  |
//| Independent closed-bar[1] GOAL transfer; NOT Carry/HourOpen/     |
//| VolExp/ChopTrend/GoldJPYLead rescue.                             |
//| Hypothesis: HYP-SPARK-ASIAN-M15-001                                |
//|                                                                   |
//| Build Asian high/low on closed bars [00,08); lock; enter when     |
//| closed bar[1] breaks range with body + D1 EMA50 bias.             |
//| Seed-faithful Tue–Wed only (skip Mon/Thu/Fri). Weekend flat.     |
//| Risk 0.5%.                                                       |
//+------------------------------------------------------------------+
#property copyright "SonicR / EA_M15SparkAsian"
#property version   "1.00"
#property strict

#include <Trade\Trade.mqh>

input group "=== General ==="
input ulong    InpMagic         = 880930;
input int      InpDeviation     = 30;
input bool     InpKillSwitch    = false;

input group "=== Asian Range ==="
input int      InpAsianStart    = 0;
input int      InpAsianEnd      = 8;
input double   InpBrkBufferATR  = 0.15;
input double   InpBodyRatio     = 0.35;
input double   InpRangeMinATR   = 0.80;
input double   InpRangeMaxATR   = 8.00;
input int      InpATRPeriod     = 14;
input int      InpEMAPeriod     = 50;
input bool     InpUseTrendFilter= true;

input group "=== Session (server hours) ==="
input int      InpLdnStart      = 9;
input int      InpLdnEnd        = 13;
input bool     InpNYEnabled     = true;
input int      InpNYStart       = 15;
input int      InpNYEnd         = 18;
input int      InpFlatHour      = 21;
input bool     InpTradeMon      = false;  // S111 seed: skip Mon
input bool     InpTradeTue      = true;
input bool     InpTradeWed      = true;
input bool     InpTradeThu      = false;  // S111 seed: skip Thu
input bool     InpTradeFri      = false;  // weekend flat

input group "=== Risk ==="
input double   InpRiskPct       = 0.50;
input double   InpMaxLot        = 1.0;
input double   InpTPRatio       = 1.50;  // Model 0 screen defaults (run 20260714_002614)
input double   InpSLBufferATR   = 0.20;
input bool     InpBEEnabled     = true;
input double   InpBERatio       = 1.0;
input int      InpMaxHoldBars   = 24;
input int      InpMaxSpread     = 50;
input int      InpMaxPerDay     = 2;
input double   InpDailyDD       = 4.0;

CTrade   g_trade;
int      g_hATR    = INVALID_HANDLE;
int      g_hEMA_D1 = INVALID_HANDLE;
datetime g_lastBar = 0;
int      g_tradesToday = 0;
int      g_lastTradeDay = -1;
double   g_dayStartBalance = 0;
int      g_holdBars = 0;
bool     g_beMoved = false;

double   g_asianHi = 0;
double   g_asianLo = 99999.0;
bool     g_rangeLocked = false;
bool     g_rangeValid  = false;

//+------------------------------------------------------------------+
int OnInit()
{
   g_trade.SetExpertMagicNumber((long)InpMagic);
   g_trade.SetDeviationInPoints(InpDeviation);

   g_hATR = iATR(_Symbol, PERIOD_CURRENT, InpATRPeriod);
   if(InpUseTrendFilter)
      g_hEMA_D1 = iMA(_Symbol, PERIOD_D1, InpEMAPeriod, 0, MODE_EMA, PRICE_CLOSE);

   if(g_hATR == INVALID_HANDLE)
      return INIT_FAILED;
   if(InpUseTrendFilter && g_hEMA_D1 == INVALID_HANDLE)
      return INIT_FAILED;

   g_dayStartBalance = AccountInfoDouble(ACCOUNT_BALANCE);
   PrintFormat("[SPKA] HYP-SPARK-ASIAN-M15-001 | Asian[%d,%d) TP=%.2fR risk=%.2f%%",
               InpAsianStart, InpAsianEnd, InpTPRatio, InpRiskPct);
   return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   if(g_hATR != INVALID_HANDLE) IndicatorRelease(g_hATR);
   if(g_hEMA_D1 != INVALID_HANDLE) IndicatorRelease(g_hEMA_D1);
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
                            "SPKA|" + reason, res))
         PrintFormat("[SPKA] Close failed ticket=%I64u retcode=%u", t, res.retcode);
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
double GetATR1()
{
   double buf[];
   ArraySetAsSeries(buf, true);
   if(CopyBuffer(g_hATR, 0, 1, 1, buf) < 1)
      return 0;
   return buf[0];
}

//+------------------------------------------------------------------+
int GetTrendBias()
{
   if(!InpUseTrendFilter || g_hEMA_D1 == INVALID_HANDLE)
      return 0;
   double ema[];
   ArraySetAsSeries(ema, true);
   if(CopyBuffer(g_hEMA_D1, 0, 1, 1, ema) < 1)
      return 0;
   double d1c[];
   ArraySetAsSeries(d1c, true);
   if(CopyClose(_Symbol, PERIOD_D1, 1, 1, d1c) < 1)
      return 0;
   if(d1c[0] > ema[0]) return 1;
   if(d1c[0] < ema[0]) return -1;
   return 0;
}

//+------------------------------------------------------------------+
void ResetDay()
{
   g_asianHi = 0;
   g_asianLo = 99999.0;
   g_rangeLocked = false;
   g_rangeValid = false;
   g_tradesToday = 0;
   g_holdBars = 0;
   g_beMoved = false;
   g_dayStartBalance = AccountInfoDouble(ACCOUNT_BALANCE);
}

//+------------------------------------------------------------------+
void LockRange(const double atr)
{
   g_rangeLocked = true;
   if(g_asianHi <= 0 || g_asianLo >= 99999.0 || g_asianHi <= g_asianLo)
   {
      g_rangeValid = false;
      return;
   }
   double rangeSize = g_asianHi - g_asianLo;
   double ratio = (atr > 0) ? rangeSize / atr : 0;
   g_rangeValid = (ratio >= InpRangeMinATR && ratio <= InpRangeMaxATR);
}

//+------------------------------------------------------------------+
void ManageOpen(const int hour)
{
   if(CountPositions() <= 0)
      return;

   g_holdBars++;

   if(hour >= InpFlatHour)
   {
      CloseAll("FLAT");
      return;
   }
   if(g_holdBars >= InpMaxHoldBars)
   {
      CloseAll("MAX_HOLD");
      return;
   }

   if(!InpBEEnabled || g_beMoved)
      return;

   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong t = PositionGetTicket(i);
      if(t <= 0 ||
         PositionGetInteger(POSITION_MAGIC) != (long)InpMagic ||
         PositionGetString(POSITION_SYMBOL) != _Symbol)
         continue;

      bool isBuy = (PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY);
      double openPx = PositionGetDouble(POSITION_PRICE_OPEN);
      double currSL = PositionGetDouble(POSITION_SL);
      double currTP = PositionGetDouble(POSITION_TP);
      if(currSL <= 0)
         break;

      double slDist = MathAbs(openPx - currSL);
      double beTarget = slDist * InpBERatio;
      double curPrice = isBuy ? SymbolInfoDouble(_Symbol, SYMBOL_BID)
                              : SymbolInfoDouble(_Symbol, SYMBOL_ASK);
      double profit = isBuy ? (curPrice - openPx) : (openPx - curPrice);
      if(profit < beTarget || beTarget <= 0)
         break;

      double newSL = NormalizeDouble(isBuy ? openPx + _Point : openPx - _Point, _Digits);
      long stopLvl = 0;
      SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL, stopLvl);
      if(MathAbs(curPrice - newSL) < stopLvl * _Point)
         break;

      if(g_trade.PositionModify(t, newSL, currTP))
         g_beMoved = true;
      break;
   }
}

//+------------------------------------------------------------------+
int GetBreakoutSignal(const double atr)
{
   if(atr <= 0 || !g_rangeLocked || !g_rangeValid)
      return 0;

   int spread = (int)SymbolInfoInteger(_Symbol, SYMBOL_SPREAD);
   if(spread > InpMaxSpread)
      return 0;

   double open1  = iOpen(_Symbol, PERIOD_CURRENT, 1);
   double close1 = iClose(_Symbol, PERIOD_CURRENT, 1);
   double high1  = iHigh(_Symbol, PERIOD_CURRENT, 1);
   double low1   = iLow(_Symbol, PERIOD_CURRENT, 1);
   if(high1 <= low1)
      return 0;

   double barRange = high1 - low1;
   double bodyRatio = MathAbs(close1 - open1) / barRange;
   if(bodyRatio < InpBodyRatio)
      return 0;

   double buffer = atr * InpBrkBufferATR;
   int direction = 0;
   if(close1 > g_asianHi + buffer && close1 > open1)
      direction = 1;
   else if(close1 < g_asianLo - buffer && close1 < open1)
      direction = -1;
   if(direction == 0)
      return 0;

   if(InpUseTrendFilter)
   {
      int bias = GetTrendBias();
      if((direction == 1 && bias == -1) || (direction == -1 && bias == 1))
         return 0;
   }
   return direction;
}

//+------------------------------------------------------------------+
void TryEntry(const double atr, const string session)
{
   int direction = GetBreakoutSignal(atr);
   if(direction == 0)
      return;

   double slBuffer = atr * InpSLBufferATR;
   double entry = 0, sl = 0, tp = 0, slDist = 0;
   if(direction == 1)
   {
      entry = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
      sl = g_asianLo - slBuffer;
      slDist = entry - sl;
      tp = entry + slDist * InpTPRatio;
   }
   else
   {
      entry = SymbolInfoDouble(_Symbol, SYMBOL_BID);
      sl = g_asianHi + slBuffer;
      slDist = sl - entry;
      tp = entry - slDist * InpTPRatio;
   }
   if(slDist <= 0)
      return;

   sl = NormalizeDouble(sl, _Digits);
   tp = NormalizeDouble(tp, _Digits);
   double lots = CalcLot(slDist);
   if(lots <= 0)
      return;

   MqlTradeResult res = {};
   string comment = "SPKA|" + session;
   bool ok = SendDealWithRetry(direction == 1 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL,
                               lots, sl, tp, 0, comment, res);
   if(ok)
   {
      g_tradesToday++;
      g_holdBars = 0;
      g_beMoved = false;
      PrintFormat("[SPKA] ENTRY %s %s lots=%.2f SL=%.5f TP=%.5f",
                  (direction == 1 ? "BUY" : "SELL"), session, lots, sl, tp);
   }
   else
      PrintFormat("[SPKA] ENTRY FAIL retcode=%u", res.retcode);
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
   int hour = dt.hour;
   int dow = dt.day_of_week;
   int dayKey = dt.year * 400 + dt.day_of_year;
   if(dayKey != g_lastTradeDay)
   {
      g_lastTradeDay = dayKey;
      ResetDay();
   }

   double atr = GetATR1();
   if(atr <= 0)
      return;

   // Range tracking uses closed bar[1] only (even on skip days so lock is ready).
   if(hour >= InpAsianStart && hour < InpAsianEnd)
   {
      double hi1 = iHigh(_Symbol, PERIOD_CURRENT, 1);
      double lo1 = iLow(_Symbol, PERIOD_CURRENT, 1);
      if(hi1 > g_asianHi) g_asianHi = hi1;
      if(lo1 < g_asianLo && lo1 > 0) g_asianLo = lo1;
   }
   if(hour >= InpAsianEnd && !g_rangeLocked)
      LockRange(atr);

   if(CountPositions() > 0)
   {
      ManageOpen(hour);
      return;
   }

   if(!IsTradeDay(dow) || IsDDExceeded())
      return;
   if(g_tradesToday >= InpMaxPerDay)
      return;
   if(hour >= InpFlatHour)
      return;

   bool inLdn = (hour >= InpLdnStart && hour < InpLdnEnd);
   bool inNY  = InpNYEnabled && (hour >= InpNYStart && hour < InpNYEnd);
   if(!inLdn && !inNY)
      return;

   TryEntry(atr, inLdn ? "LDN" : "NY");
}

//+------------------------------------------------------------------+
