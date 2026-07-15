//+------------------------------------------------------------------+
//| EA_TimeFade.mq5 — Time-Displacement Fade Scanner                 |
//| Symbol: Any  |  Period: M15  |  Style: Mean Reversion Scalp      |
//|                                                                   |
//| EDGE HYPOTHESIS:                                                  |
//| At specific hours, intraday displacement from session open        |
//| exceeding N*ATR creates a mean-reversion opportunity.             |
//| The structural reason varies by hour:                             |
//| - Pre-fix hours: auction-driven flow then reverts                 |
//| - Late session: profit-taking, position squaring                  |
//| - Cross-session: liquidity transition creates overshoot           |
//|                                                                   |
//| This EA is a SCANNER: run on full data, analyze by hour in       |
//| the report to find which hours have genuine fade edge.            |
//|                                                                   |
//| SIGNALS ON BAR[1] ONLY — no repaint.                             |
//| Max | 2026-04-12 | v1.0                                         |
//+------------------------------------------------------------------+
#property copyright "Max - EA_TimeFade v1.0"
#property version   "1.00"
#property strict

#include <Trade\Trade.mqh>

//+------------------------------------------------------------------+
input group "=== General ==="
input ulong    InpMagic         = 802001;
input int      InpDeviation     = 30;
input bool     InpKillSwitch    = false;

input group "=== Time Window ==="
input int      InpTradeStartH   = 2;         // Earliest entry hour (server)
input int      InpTradeEndH     = 20;        // Latest entry hour (server)
input int      InpHoldBars      = 4;         // Max bars to hold (4 x M15 = 1h)
input int      InpDayOpenH      = 0;         // Day open hour for displacement calc

input group "=== Displacement ==="
input int      InpATRPeriod     = 14;
input double   InpMinDisplace   = 0.8;       // Min displacement: ATR * this
input double   InpMaxDisplace   = 3.0;       // Max displacement: ATR * this (avoid extremes)

input group "=== Risk ==="
input double   InpRiskPct       = 0.50;
input double   InpMaxLot        = 0.50;
input int      InpMaxPerDay     = 3;
input double   InpDailyDDPct    = 4.0;
input double   InpSL_ATRMult    = 1.2;       // SL = ATR * this
input double   InpTP_ATRMult    = 1.0;       // TP = ATR * this (fade = smaller target)

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
double   g_dayOpen, g_dayStartBal;
int      g_tradesToday;
datetime g_posOpenTime;

//+------------------------------------------------------------------+
int OnInit()
{
   if(InpKillSwitch) return INIT_SUCCEEDED;
   g_trade.SetExpertMagicNumber(InpMagic);
   g_trade.SetDeviationInPoints(InpDeviation);
   g_trade.SetTypeFilling(ORDER_FILLING_FOK);

   g_hATR = iATR(_Symbol, PERIOD_CURRENT, InpATRPeriod);
   if(g_hATR == INVALID_HANDLE) { Print("[TF] ATR init fail"); return INIT_FAILED; }

   g_lastBar = 0; g_todayDate = 0; g_tradesToday = 0;
   g_dayOpen = 0; g_dayStartBal = AccountInfoDouble(ACCOUNT_BALANCE);
   g_posOpenTime = 0;

   PrintFormat("[TF] TimeFade v1.0 | %s %s | h%d-h%d | Displace %.1f-%.1f ATR",
               _Symbol, EnumToString(_Period),
               InpTradeStartH, InpTradeEndH,
               InpMinDisplace, InpMaxDisplace);
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   if(g_hATR != INVALID_HANDLE) IndicatorRelease(g_hATR);
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
   double bal  = AccountInfoDouble(ACCOUNT_BALANCE);
   double risk = bal * InpRiskPct / 100.0;
   double tSz  = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   double tVal = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
   double pt   = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   if(tSz == 0 || tVal == 0 || pt == 0) return 0;
   double ptVal = tVal * pt / tSz;
   double lot   = risk / (slPts * ptVal);
   double minL  = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double maxL  = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   double step  = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
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

   // Day reset
   if(today != g_todayDate)
   {
      g_todayDate = today;
      g_tradesToday = 0;
      g_dayStartBal = AccountInfoDouble(ACCOUNT_BALANCE);

      // Find day open price
      datetime dayOpenTime = today + InpDayOpenH * 3600;
      int barIdx = iBarShift(_Symbol, PERIOD_CURRENT, dayOpenTime, false);
      if(barIdx >= 0)
         g_dayOpen = iOpen(_Symbol, PERIOD_CURRENT, barIdx);
      else
         g_dayOpen = iOpen(_Symbol, PERIOD_CURRENT, 0);
   }

   // Time-based exit for open positions
   if(CountPos() > 0)
   {
      int barsHeld = 0;
      if(g_posOpenTime > 0)
         barsHeld = iBarShift(_Symbol, PERIOD_CURRENT, g_posOpenTime, false);
      if(barsHeld >= InpHoldBars)
      {
         CloseAll();
         g_posOpenTime = 0;
      }
      return;  // Don't open new positions while holding
   }

   // Pre-flight
   if(!IsTradingDay(dt.day_of_week)) return;
   if(dt.hour < InpTradeStartH || dt.hour >= InpTradeEndH) return;
   if(g_tradesToday >= InpMaxPerDay) return;
   if(g_dayOpen <= 0) return;

   double ddPct = (g_dayStartBal > 0) ?
      (g_dayStartBal - AccountInfoDouble(ACCOUNT_EQUITY)) / g_dayStartBal * 100.0 : 0;
   if(ddPct >= InpDailyDDPct) return;

   // Read ATR
   double atr[];
   if(CopyBuffer(g_hATR, 0, 1, 1, atr) < 1) return;
   double atrVal = atr[0];
   if(atrVal <= 0) return;

   // Measure displacement from day open
   double close1 = iClose(_Symbol, PERIOD_CURRENT, 1);
   double displacement = close1 - g_dayOpen;
   double dispAbs = MathAbs(displacement);
   double dispATR = dispAbs / atrVal;

   // Check displacement thresholds
   if(dispATR < InpMinDisplace || dispATR > InpMaxDisplace) return;

   // FADE the displacement
   bool isBuy = (displacement < 0);  // Price dropped → buy
   // (displacement > 0) → price rallied → sell

   double pt     = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   int    digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
   double slDist = atrVal * InpSL_ATRMult;
   double tpDist = atrVal * InpTP_ATRMult;
   double slPts  = slDist / pt;

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

   string comment = StringFormat("TF|h%d|d=%.1fATR|%s",
                                 dt.hour, dispATR, isBuy ? "BUY" : "SELL");

   bool ok = g_trade.PositionOpen(_Symbol,
               isBuy ? ORDER_TYPE_BUY : ORDER_TYPE_SELL,
               lot, price, sl, tp, comment);

   if(ok)
   {
      g_tradesToday++;
      g_posOpenTime = barTime;
      PrintFormat("[TF] %s %.2f @ %.5f | h%d | disp=%.1fATR",
                  isBuy ? "BUY" : "SELL", lot, price, dt.hour, dispATR);
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
