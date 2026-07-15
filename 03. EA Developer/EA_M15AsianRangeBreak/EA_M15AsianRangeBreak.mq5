//+------------------------------------------------------------------+
//| EA_M15AsianRangeBreak.mq5 — Asian range -> LDN/NY breakout        |
//| Symbol: USDJPY | Period: M15 | Magic: 880931                     |
//|                                                                   |
//| Near-miss seed: S111 / EA_Spark USDJPY M15 baked (PF~1.26,       |
//| ~71/yr ≈ 1.37/week). Independent GOAL transfer after InsideBar   |
//| / Chop / VolExp / GoldJPY kills.                                 |
//| Hypothesis: HYP-SPARK-ASIAN-M15-001                                |
//|                                                                   |
//| Build Asian Hi/Lo on closed bars during Asian window; lock at    |
//| AsianEnd; enter on closed bar[1] breakout in LDN or NY window    |
//| with D1 EMA50 bias. Seed day filter Tue+Wed only (S111/S223).    |
//| Weekend flat. Risk 0.5%. No post-hoc day/hour mining.            |
//+------------------------------------------------------------------+
#property copyright "SonicR / EA_M15AsianRangeBreak"
#property version   "1.00"
#property strict

#include <Trade\Trade.mqh>

input group "=== General ==="
input ulong    InpMagic         = 880931;
input int      InpDeviation     = 30;
input bool     InpKillSwitch    = false;

input group "=== Asian Range ==="
input int      InpAsianStart    = 0;
input int      InpAsianEnd      = 8;
input double   InpRangeMinATR   = 0.80;
input double   InpRangeMaxATR   = 8.00;
input double   InpBrkBufferATR  = 0.15;
input double   InpBodyRatio     = 0.35;
input int      InpEMAPeriod     = 50;
input bool     InpUseTrendFilter= true;

input group "=== Session (server hours) ==="
input int      InpLdnStart      = 9;
input int      InpLdnEnd        = 13;
input bool     InpNYEnabled     = true;
input int      InpNYStart       = 15;
input int      InpNYEnd         = 18;
input int      InpExitHour      = 21;
// Seed baked days: Tue+Wed only (S111 / S223 structural — not mined tonight)
input bool     InpTradeMon      = false;
input bool     InpTradeTue      = true;
input bool     InpTradeWed      = true;
input bool     InpTradeThu      = false;
input bool     InpTradeFri      = false;

input group "=== Risk ==="
input double   InpRiskPct       = 0.50;
input double   InpMaxLot        = 1.0;
input double   InpSL_BufferATR  = 0.20;
input double   InpTP_Ratio      = 2.00;
input int      InpMinSLPoints   = 50;
input int      InpMaxSLPoints   = 1200;
input int      InpMaxPerDay     = 3;
input double   InpDailyDD       = 4.0;
input int      InpMaxHoldBars   = 24;
input int      InpMaxSpreadPts  = 50;

CTrade   g_trade;
int      g_hATR  = INVALID_HANDLE;
int      g_hEMA  = INVALID_HANDLE;
datetime g_lastBar = 0;
int      g_tradesToday = 0;
int      g_lastTradeDay = -1;
double   g_dayStartBalance = 0;

double   g_asianHi = 0.0;
double   g_asianLo = 0.0;
bool     g_rangeLocked = false;
bool     g_rangeValid  = false;
int      g_holdBars = 0;
datetime g_posOpenBar = 0;

//+------------------------------------------------------------------+
int OnInit()
{
   g_trade.SetExpertMagicNumber((long)InpMagic);
   g_trade.SetDeviationInPoints(InpDeviation);

   g_hATR = iATR(_Symbol, PERIOD_CURRENT, 14);
   if(g_hATR == INVALID_HANDLE)
      return INIT_FAILED;

   if(InpUseTrendFilter)
   {
      g_hEMA = iMA(_Symbol, PERIOD_D1, InpEMAPeriod, 0, MODE_EMA, PRICE_CLOSE);
      if(g_hEMA == INVALID_HANDLE)
         return INIT_FAILED;
   }

   g_dayStartBalance = AccountInfoDouble(ACCOUNT_BALANCE);
   PrintFormat("[M15ARB] HYP-SPARK-ASIAN-M15-001 | Asian[%d,%d) Brk=%.2f Body=%.2f risk=%.2f%%",
               InpAsianStart, InpAsianEnd, InpBrkBufferATR, InpBodyRatio, InpRiskPct);
   return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   if(g_hATR != INVALID_HANDLE) IndicatorRelease(g_hATR);
   if(g_hEMA != INVALID_HANDLE) IndicatorRelease(g_hEMA);
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
                        "M15ARB|" + reason, res);
   }
   g_holdBars = 0;
   g_posOpenBar = 0;
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
bool InEntryWindow(const int hour)
{
   bool inLdn = (hour >= InpLdnStart && hour < InpLdnEnd);
   bool inNY  = InpNYEnabled && (hour >= InpNYStart && hour < InpNYEnd);
   return (inLdn || inNY);
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
void ResetRange()
{
   g_asianHi = 0.0;
   g_asianLo = 0.0;
   g_rangeLocked = false;
   g_rangeValid = false;
}

//+------------------------------------------------------------------+
void UpdateAsianRange()
{
   double hi1 = iHigh(_Symbol, PERIOD_CURRENT, 1);
   double lo1 = iLow(_Symbol, PERIOD_CURRENT, 1);
   if(hi1 <= 0.0 || lo1 <= 0.0)
      return;
   if(g_asianHi <= 0.0 || hi1 > g_asianHi)
      g_asianHi = hi1;
   if(g_asianLo <= 0.0 || lo1 < g_asianLo)
      g_asianLo = lo1;
}

//+------------------------------------------------------------------+
void LockRange(const double atr)
{
   g_rangeLocked = true;
   if(g_asianHi <= 0.0 || g_asianLo <= 0.0 || g_asianHi <= g_asianLo || atr <= 0.0)
   {
      g_rangeValid = false;
      return;
   }
   double ratio = (g_asianHi - g_asianLo) / atr;
   g_rangeValid = (ratio >= InpRangeMinATR && ratio <= InpRangeMaxATR);
}

//+------------------------------------------------------------------+
int GetTrendBias()
{
   if(!InpUseTrendFilter || g_hEMA == INVALID_HANDLE)
      return 0;
   double ema[];
   ArraySetAsSeries(ema, true);
   if(CopyBuffer(g_hEMA, 0, 1, 1, ema) < 1)
      return 0;
   double c = iClose(_Symbol, PERIOD_D1, 1);
   if(c > ema[0]) return +1;
   if(c < ema[0]) return -1;
   return 0;
}

//+------------------------------------------------------------------+
// Closed-bar[1] only: breakout of locked Asian range.
int GetSignal(const double atr)
{
   if(!g_rangeLocked || !g_rangeValid || atr <= 0.0)
      return 0;

   double o1 = iOpen(_Symbol, PERIOD_CURRENT, 1);
   double c1 = iClose(_Symbol, PERIOD_CURRENT, 1);
   double h1 = iHigh(_Symbol, PERIOD_CURRENT, 1);
   double l1 = iLow(_Symbol, PERIOD_CURRENT, 1);
   if(h1 <= l1)
      return 0;

   double bodyRatio = MathAbs(c1 - o1) / (h1 - l1);
   if(bodyRatio < InpBodyRatio)
      return 0;

   double buf = atr * InpBrkBufferATR;
   int dir = 0;
   if(c1 > g_asianHi + buf && c1 > o1)
      dir = +1;
   else if(c1 < g_asianLo - buf && c1 < o1)
      dir = -1;
   else
      return 0;

   int bias = GetTrendBias();
   if(bias != 0 && bias != dir)
      return 0;
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
   int hour = dt.hour;
   int dayHash = dt.year * 400 + dt.day_of_year;

   if(dayHash != g_lastTradeDay)
   {
      g_lastTradeDay = dayHash;
      g_tradesToday = 0;
      g_dayStartBalance = AccountInfoDouble(ACCOUNT_BALANCE);
      ResetRange();
   }

   // Weekend / EOD flat (manage first)
   if(hour >= InpExitHour || dt.day_of_week == 5 || dt.day_of_week == 0 || dt.day_of_week == 6)
   {
      if(CountPositions() > 0)
         CloseAll("flat");
      return;
   }

   // Max-hold on existing position
   if(CountPositions() > 0)
   {
      g_holdBars++;
      if(g_holdBars >= InpMaxHoldBars)
         CloseAll("maxhold");
      return;
   }
   g_holdBars = 0;

   double atr[];
   ArraySetAsSeries(atr, true);
   if(CopyBuffer(g_hATR, 0, 1, 1, atr) < 1 || atr[0] <= 0.0)
      return;

   // Build / lock Asian range from closed bars only
   if(hour >= InpAsianStart && hour < InpAsianEnd)
      UpdateAsianRange();
   if(hour >= InpAsianEnd && !g_rangeLocked)
      LockRange(atr[0]);

   if(!IsTradeDay(dt.day_of_week))
      return;
   if(!InEntryWindow(hour))
      return;
   if(g_tradesToday >= InpMaxPerDay || IsDDExceeded())
      return;

   int spread = (int)SymbolInfoInteger(_Symbol, SYMBOL_SPREAD);
   if(spread > InpMaxSpreadPts)
      return;

   int signal = GetSignal(atr[0]);
   if(signal == 0)
      return;

   bool isBuy = (signal == +1);
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double entry = (isBuy ? ask : bid);
   double slRaw = (isBuy ? g_asianLo - atr[0] * InpSL_BufferATR
                         : g_asianHi + atr[0] * InpSL_BufferATR);
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
                         "M15ARB|brk", res))
      return;

   if(IsSuccessfulRetcode(res.retcode))
   {
      g_tradesToday++;
      g_holdBars = 0;
      g_posOpenBar = bar1Time;
      PrintFormat("[M15ARB] %s lot=%.2f @ %.5f range=[%.5f,%.5f]",
                  isBuy ? "BUY" : "SELL", lot, res.price, g_asianLo, g_asianHi);
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
