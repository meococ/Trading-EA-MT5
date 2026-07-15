//+------------------------------------------------------------------+
//| EA_GoldAMFix.mq5 — LBMA AM Gold Fix Window Scalper              |
//| Symbol: XAUUSD+  |  Period: M15  |  Style: Structural Fix        |
//|                                                                   |
//| EDGE HYPOTHESIS:                                                  |
//| LBMA AM Gold Price Fix at 10:30 London creates predictable       |
//| order flow from bullion banks and institutional hedgers.          |
//| Price tends to be pushed toward the fix price pre-auction,       |
//| then reverts after fix is published. This creates a mean-        |
//| reversion setup in the 30-60 min window around the fix.          |
//|                                                                   |
//| STRUCTURAL REASON:                                                |
//| ICE Benchmark Administration runs electronic auction with 15+    |
//| LBMA members. Hedgers/producers submit orders pre-fix,           |
//| creating anticipatory flow. Post-fix, pressure releases.         |
//| Same mechanism as Cobra PM Fix (h16) but different time.         |
//|                                                                   |
//| AM Fix = 10:30 London time                                       |
//| = 10:30 GMT (winter) / 09:30 GMT (summer BST)                   |
//| = ~12:30 server time (E8 GMT+2/+3 DST)                          |
//| Entry window: h11-h12 server (pre-fix buildup)                   |
//|                                                                   |
//| DIFFERENT FROM COBRA:                                             |
//| - Cobra = PM Fix h16 server (15:00 London)                       |
//| - This = AM Fix h12 server (10:30 London)                        |
//| - 4-5 hour gap = zero overlap                                    |
//|                                                                   |
//| SIGNALS ON BAR[1] ONLY — no repaint, no lookahead.               |
//| Max | 2026-04-12 | v1.0                                         |
//+------------------------------------------------------------------+
#property copyright "Max - EA_GoldAMFix v1.0"
#property version   "1.00"
#property strict

#include <Trade\Trade.mqh>

//+------------------------------------------------------------------+
input group "=== General ==="
input ulong    InpMagic         = 801501;
input int      InpDeviation     = 30;
input bool     InpKillSwitch    = false;

input group "=== AM Fix Window (Server Time) ==="
input int      InpEntryStartH   = 11;        // Entry window start hour
input int      InpEntryEndH     = 13;        // Entry window end hour (exclusive)
input int      InpExitH         = 14;        // Force close hour (post-fix)
input int      InpExitM         = 0;         // Force close minute

input group "=== Signal Logic ==="
input int      InpATRPeriod     = 14;        // ATR period
input double   InpEntryATRMult  = 0.3;       // Entry: price moved > ATR*this from day open
input int      InpEMA_Period    = 50;        // EMA for trend context
input bool     InpFadeMode      = true;      // true=fade pre-fix move, false=follow
input double   InpMinBodyRatio  = 0.4;       // Min body/range ratio on signal bar

input group "=== Asian Range ==="
input int      InpAsianStartH   = 0;         // Asian range start (server)
input int      InpAsianEndH     = 8;         // Asian range end (server)
input bool     InpUseAsianRange = true;      // Use Asian range levels

input group "=== Risk ==="
input double   InpRiskPct       = 0.50;
input double   InpMaxLot        = 0.50;
input int      InpMaxPerDay     = 2;
input double   InpDailyDDPct    = 4.0;
input double   InpSL_ATRMult    = 1.5;       // SL = ATR * this
input double   InpTP_ATRMult    = 2.0;       // TP = ATR * this
input double   InpMinSLPts      = 50;
input double   InpMaxSLPts      = 400;

input group "=== Day Filters ==="
input bool     InpMon = true;
input bool     InpTue = true;
input bool     InpWed = true;
input bool     InpThu = true;
input bool     InpFri = true;

//+------------------------------------------------------------------+
CTrade   g_trade;
int      g_hATR, g_hEMA;
datetime g_lastBar, g_todayDate;
double   g_dayStartBal, g_dayOpen;
double   g_asianHigh, g_asianLow;
int      g_tradesToday;
bool     g_asianBuilt;

//+------------------------------------------------------------------+
int OnInit()
{
   if(InpKillSwitch) return INIT_SUCCEEDED;

   g_trade.SetExpertMagicNumber(InpMagic);
   g_trade.SetDeviationInPoints(InpDeviation);
   g_trade.SetTypeFilling(ORDER_FILLING_FOK);

   g_hATR = iATR(_Symbol, PERIOD_CURRENT, InpATRPeriod);
   g_hEMA = iMA(_Symbol, PERIOD_CURRENT, InpEMA_Period, 0, MODE_EMA, PRICE_CLOSE);

   if(g_hATR == INVALID_HANDLE || g_hEMA == INVALID_HANDLE)
   {
      Print("[AMF] FATAL: Indicator init failed");
      return INIT_FAILED;
   }

   g_lastBar = 0; g_todayDate = 0; g_tradesToday = 0;
   g_dayStartBal = AccountInfoDouble(ACCOUNT_BALANCE);
   g_dayOpen = 0; g_asianHigh = 0; g_asianLow = DBL_MAX; g_asianBuilt = false;

   PrintFormat("[AMF] GoldAMFix v1.0 | %s %s | Magic=%d",
               _Symbol, EnumToString(_Period), InpMagic);
   PrintFormat("[AMF] Window: h%d-h%d | Exit: h%d:%02d | Fade=%s",
               InpEntryStartH, InpEntryEndH, InpExitH, InpExitM,
               InpFadeMode ? "YES" : "NO");

   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   if(g_hATR != INVALID_HANDLE) IndicatorRelease(g_hATR);
   if(g_hEMA != INVALID_HANDLE) IndicatorRelease(g_hEMA);
}

//+------------------------------------------------------------------+
int CountPos()
{
   int n = 0;
   for(int i = PositionsTotal()-1; i >= 0; i--)
   {
      ulong t = PositionGetTicket(i);
      if(t > 0 && PositionGetInteger(POSITION_MAGIC) == (long)InpMagic &&
         PositionGetString(POSITION_SYMBOL) == _Symbol) n++;
   }
   return n;
}

void CloseAll()
{
   for(int i = PositionsTotal()-1; i >= 0; i--)
   {
      ulong t = PositionGetTicket(i);
      if(t > 0 && PositionGetInteger(POSITION_MAGIC) == (long)InpMagic &&
         PositionGetString(POSITION_SYMBOL) == _Symbol)
         g_trade.PositionClose(t);
   }
}

double CalcLot(double slPts)
{
   if(slPts <= 0) return 0;
   double bal     = AccountInfoDouble(ACCOUNT_BALANCE);
   double risk    = bal * InpRiskPct / 100.0;
   double tickSz  = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   double tickVal = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
   double pt      = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   if(tickSz == 0 || tickVal == 0 || pt == 0) return 0;
   double ptVal   = tickVal * pt / tickSz;
   double lot     = risk / (slPts * ptVal);
   double minL    = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double maxL    = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   double step    = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   lot = MathMax(lot, minL);
   lot = MathMin(lot, MathMin(InpMaxLot, maxL));
   if(step > 0) lot = MathFloor(lot / step) * step;
   return NormalizeDouble(lot, 2);
}

bool IsTradingDay(int dow)
{
   switch(dow)
   {
      case 1: return InpMon; case 2: return InpTue; case 3: return InpWed;
      case 4: return InpThu; case 5: return InpFri; default: return false;
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

   //--- Day reset
   if(today != g_todayDate)
   {
      g_todayDate = today;
      g_tradesToday = 0;
      g_dayStartBal = AccountInfoDouble(ACCOUNT_BALANCE);
      g_dayOpen = iOpen(_Symbol, PERIOD_CURRENT, 0);
      g_asianHigh = 0;
      g_asianLow = DBL_MAX;
      g_asianBuilt = false;
   }

   //--- Build Asian range
   if(dt.hour >= InpAsianStartH && dt.hour < InpAsianEndH)
   {
      double h1 = iHigh(_Symbol, PERIOD_CURRENT, 1);
      double l1 = iLow(_Symbol, PERIOD_CURRENT, 1);
      if(h1 > g_asianHigh) g_asianHigh = h1;
      if(l1 < g_asianLow)  g_asianLow  = l1;
   }
   else if(dt.hour >= InpAsianEndH && !g_asianBuilt)
   {
      g_asianBuilt = true;
   }

   //--- Force close after fix window
   if(CountPos() > 0)
   {
      if(dt.hour > InpExitH || (dt.hour == InpExitH && dt.min >= InpExitM))
      {
         CloseAll();
         return;
      }
   }

   //--- Pre-flight
   if(!IsTradingDay(dt.day_of_week)) return;
   if(dt.hour < InpEntryStartH || dt.hour >= InpEntryEndH) return;
   if(g_tradesToday >= InpMaxPerDay) return;
   if(CountPos() > 0) return;

   double ddPct = (g_dayStartBal > 0) ?
                  (g_dayStartBal - AccountInfoDouble(ACCOUNT_EQUITY)) / g_dayStartBal * 100.0 : 0;
   if(ddPct >= InpDailyDDPct) return;

   //--- Read indicators on bar[1]
   double atr[], ema[];
   if(CopyBuffer(g_hATR, 0, 1, 1, atr) < 1) return;
   if(CopyBuffer(g_hEMA, 0, 1, 1, ema) < 1) return;

   double atrVal = atr[0];
   double emaVal = ema[0];
   if(atrVal <= 0) return;

   double pt     = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   int    digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);

   double close1 = iClose(_Symbol, PERIOD_CURRENT, 1);
   double open1  = iOpen(_Symbol, PERIOD_CURRENT, 1);
   double high1  = iHigh(_Symbol, PERIOD_CURRENT, 1);
   double low1   = iLow(_Symbol, PERIOD_CURRENT, 1);

   //--- Signal bar quality: body ratio check
   double range1 = high1 - low1;
   if(range1 <= 0) return;
   double body1 = MathAbs(close1 - open1);
   if(body1 / range1 < InpMinBodyRatio) return;

   //--- Measure pre-fix move from day open
   if(g_dayOpen <= 0) return;
   double moveFromOpen = close1 - g_dayOpen;
   double moveAbs = MathAbs(moveFromOpen);

   // Need minimum displacement
   if(moveAbs < atrVal * InpEntryATRMult) return;

   //--- Direction decision
   bool isBuy;
   if(InpFadeMode)
   {
      // Fade the pre-fix move: if price ran up → short, if down → long
      isBuy = (moveFromOpen < 0);  // price dropped → buy (expect reversion toward fix)
   }
   else
   {
      // Follow: continuation
      isBuy = (moveFromOpen > 0);
   }

   //--- Asian range confluence (optional)
   if(InpUseAsianRange && g_asianBuilt)
   {
      double asianMid = (g_asianHigh + g_asianLow) / 2.0;
      if(isBuy && close1 > g_asianHigh)
         return;  // Price already above Asian high, no room for long
      if(!isBuy && close1 < g_asianLow)
         return;  // Price already below Asian low, no room for short
   }

   //--- SL/TP
   double slDist = atrVal * InpSL_ATRMult;
   double tpDist = atrVal * InpTP_ATRMult;
   double slPts  = slDist / pt;

   if(slPts < InpMinSLPts || slPts > InpMaxSLPts) return;

   double stopLevel = (double)SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL) * pt;
   if(slDist < stopLevel || tpDist < stopLevel) return;

   double price, sl, tp;
   if(isBuy)
   {
      price = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
      sl = NormalizeDouble(price - slDist, digits);
      tp = NormalizeDouble(price + tpDist, digits);
   }
   else
   {
      price = SymbolInfoDouble(_Symbol, SYMBOL_BID);
      sl = NormalizeDouble(price + slDist, digits);
      tp = NormalizeDouble(price - tpDist, digits);
   }

   double lot = CalcLot(slPts);
   if(lot <= 0) return;

   string comment = StringFormat("AMF|%s|mv=%.0f|atr=%.0f",
                                 isBuy ? "BUY" : "SELL",
                                 moveAbs/pt, atrVal/pt);

   bool ok = g_trade.PositionOpen(_Symbol,
               isBuy ? ORDER_TYPE_BUY : ORDER_TYPE_SELL,
               lot, price, sl, tp, comment);

   if(ok)
   {
      g_tradesToday++;
      PrintFormat("[AMF] %s %.2f @ %.2f SL=%.2f TP=%.2f mv=%.1f",
                  isBuy ? "BUY" : "SELL", lot, price, sl, tp, moveFromOpen);
   }
}

//+------------------------------------------------------------------+
double OnTester()
{
   double pf = TesterStatistics(STAT_PROFIT_FACTOR);
   double trades = TesterStatistics(STAT_TRADES);
   if(trades < 30) return 0;
   return pf * MathSqrt(trades);
}
//+------------------------------------------------------------------+
