//+------------------------------------------------------------------+
//| EA_GoldMomo.mq5 — Gold Intraday Momentum Persistence            |
//| Symbol: XAUUSD+  |  Period: M5  |  Style: Momentum Scalp        |
//|                                                                   |
//| EDGE HYPOTHESIS:                                                  |
//| Intraday momentum persistence on gold: when price moves >1 ATR   |
//| in a direction over the past N bars, there is a statistical      |
//| tendency for continuation over the next few bars. This is NOT    |
//| breakout (no range to break) — it's pure momentum factor.        |
//|                                                                   |
//| STRUCTURAL REASON:                                                |
//| Gold has autocorrelated returns at 5-30 min horizon due to       |
//| institutional order flow clustering (LBMA members, central banks |
//| execute large orders over time → creates momentum waves).         |
//|                                                                   |
//| DIFFERENT FROM TESTED:                                            |
//| - NOT ORB (no opening range)                                      |
//| - NOT session breakout (no session boundary)                      |
//| - NOT EMA crossover (no lagging indicator)                        |
//| - Pure price action momentum with ATR normalization               |
//|                                                                   |
//| Max | 2026-04-12 | v1.0                                         |
//+------------------------------------------------------------------+
#property copyright "Max - EA_GoldMomo v1.0"
#property version   "1.00"
#property strict

#include <Trade\Trade.mqh>

//+------------------------------------------------------------------+
input group "=== General ==="
input ulong    InpMagic         = 801401;
input int      InpDeviation     = 30;
input bool     InpKillSwitch    = false;

input group "=== Momentum Detection ==="
input int      InpMomoLookback  = 24;        // Bars to measure momentum (24*5min = 2h)
input double   InpMomoATRMult   = 1.0;       // Min momentum = ATR * this
input int      InpATRPeriod     = 14;         // ATR period
input double   InpMinBarRatio   = 0.6;        // Min % of bars in same direction

input group "=== Momentum Strength ==="
input bool     InpUseVolFilter  = true;       // Volume above average filter
input double   InpVolMult       = 1.2;        // Volume must be > avg * this

input group "=== Session (Server Time) ==="
input int      InpSess1Start    = 8;          // London start
input int      InpSess1End      = 11;         // London end
input int      InpSess2Start    = 13;         // NY start
input int      InpSess2End      = 17;         // NY end

input group "=== Risk ==="
input double   InpRiskPct       = 0.50;
input double   InpMaxLot        = 0.50;
input int      InpMaxPerDay     = 4;
input int      InpMaxOpen       = 1;
input double   InpDailyDDPct    = 4.0;
input double   InpSLATRMult     = 1.5;       // SL = ATR * this
input double   InpTPATRMult     = 2.0;       // TP = ATR * this (1.33 RR)
input int      InpMaxBarsHold   = 36;        // Max holding (3 hours on M5)
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
int      g_hATR;
datetime g_lastBar, g_todayDate;
double   g_dayStartBal;
int      g_tradesToday, g_barsHeld;

//+------------------------------------------------------------------+
int OnInit()
{
   if(InpKillSwitch) return INIT_SUCCEEDED;
   g_trade.SetExpertMagicNumber(InpMagic);
   g_trade.SetDeviationInPoints(InpDeviation);
   g_trade.SetTypeFilling(ORDER_FILLING_FOK);

   g_hATR = iATR(_Symbol, PERIOD_CURRENT, InpATRPeriod);
   if(g_hATR == INVALID_HANDLE)
   { Print("[GM] FATAL: ATR init failed"); return INIT_FAILED; }

   g_lastBar = 0; g_todayDate = 0; g_tradesToday = 0; g_barsHeld = 0;
   g_dayStartBal = AccountInfoDouble(ACCOUNT_BALANCE);

   PrintFormat("[GM] GoldMomo v1.0 | %s %s | Magic=%d | Lookback=%d | ATRx=%.1f | BarRatio=%.0f%%",
               _Symbol, EnumToString(_Period), InpMagic,
               InpMomoLookback, InpMomoATRMult, InpMinBarRatio*100);
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   if(g_hATR != INVALID_HANDLE) IndicatorRelease(g_hATR);
}

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
   lot = MathMax(lot, minL); lot = MathMin(lot, MathMin(InpMaxLot, maxL));
   if(step > 0) lot = MathFloor(lot / step) * step;
   return NormalizeDouble(lot, 2);
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
   g_barsHeld = 0;
}

bool InSession(int hour)
{
   if(hour >= InpSess1Start && hour < InpSess1End) return true;
   if(hour >= InpSess2Start && hour < InpSess2End) return true;
   return false;
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

   if(today != g_todayDate)
   { g_todayDate = today; g_tradesToday = 0; g_dayStartBal = AccountInfoDouble(ACCOUNT_BALANCE); }

   // Manage
   if(CountPos() > 0)
   {
      g_barsHeld++;
      if(g_barsHeld >= InpMaxBarsHold) CloseAll();
      return;
   }

   // Filters
   if(!IsTradingDay(dt.day_of_week)) return;
   if(!InSession(dt.hour)) return;
   if(g_tradesToday >= InpMaxPerDay) return;
   if(CountPos() >= InpMaxOpen) return;

   double ddPct = (g_dayStartBal > 0) ?
                  (g_dayStartBal - AccountInfoDouble(ACCOUNT_EQUITY)) / g_dayStartBal * 100.0 : 0;
   if(ddPct >= InpDailyDDPct) return;

   // Need enough bars
   int barsAvail = Bars(_Symbol, PERIOD_CURRENT);
   if(barsAvail < InpMomoLookback + InpATRPeriod + 10) return;

   //=== Read ATR ===
   double atr[];
   if(CopyBuffer(g_hATR, 0, 1, 1, atr) < 1) return;
   double atrVal = atr[0];
   if(atrVal <= 0) return;

   double pt = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   int digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);

   //=== Measure momentum over lookback ===
   double close_start = iClose(_Symbol, PERIOD_CURRENT, InpMomoLookback + 1);
   double close_end   = iClose(_Symbol, PERIOD_CURRENT, 1);
   double moveSize    = close_end - close_start;
   double movePts     = MathAbs(moveSize) / pt;

   // Check if momentum exceeds threshold
   double atrPts = atrVal / pt;
   if(movePts < atrPts * InpMomoATRMult) return;

   // Count bars in the momentum direction
   int upBars = 0, downBars = 0;
   for(int i = 1; i <= InpMomoLookback; i++)
   {
      double o = iOpen(_Symbol, PERIOD_CURRENT, i);
      double c = iClose(_Symbol, PERIOD_CURRENT, i);
      if(c > o) upBars++;
      else if(c < o) downBars++;
   }

   bool bullMomo = (moveSize > 0 && (double)upBars / InpMomoLookback >= InpMinBarRatio);
   bool bearMomo = (moveSize < 0 && (double)downBars / InpMomoLookback >= InpMinBarRatio);

   if(!bullMomo && !bearMomo) return;

   //=== Volume filter ===
   if(InpUseVolFilter)
   {
      long vol0 = iVolume(_Symbol, PERIOD_CURRENT, 1);
      // Average volume over lookback
      long volSum = 0;
      for(int i = 1; i <= InpMomoLookback; i++)
         volSum += iVolume(_Symbol, PERIOD_CURRENT, i);
      double avgVol = (double)volSum / InpMomoLookback;
      if(vol0 < avgVol * InpVolMult) return;
   }

   //=== Entry ===
   double slDist = atrVal * InpSLATRMult;
   double tpDist = atrVal * InpTPATRMult;
   double slPts  = slDist / pt;

   if(slPts < InpMinSLPts || slPts > InpMaxSLPts) return;

   double stopLevel = SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL) * pt;
   if(slDist < stopLevel || tpDist < stopLevel) return;

   double price, sl, tp;
   bool isBuy = bullMomo;

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

   string comment = StringFormat("GM|mv=%.0f|atr=%.0f|u=%d/d=%d",
                                 movePts, atrPts, upBars, downBars);

   bool ok = g_trade.PositionOpen(_Symbol,
               isBuy ? ORDER_TYPE_BUY : ORDER_TYPE_SELL,
               lot, price, sl, tp, comment);

   if(ok)
   {
      g_tradesToday++;
      g_barsHeld = 0;
      PrintFormat("[GM] %s %.2f @ %.2f SL=%.2f TP=%.2f mv=%.0fpt",
                  isBuy ? "BUY" : "SELL", lot, price, sl, tp, movePts);
   }
}
//+------------------------------------------------------------------+
