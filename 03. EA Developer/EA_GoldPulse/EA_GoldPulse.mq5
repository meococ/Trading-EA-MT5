//+------------------------------------------------------------------+
//| EA_GoldPulse.mq5 — Gold M5 Volatility Pulse Scalper             |
//| Symbol: XAUUSD+  |  Period: M5  |  Style: Volatility Breakout   |
//|                                                                   |
//| EDGE HYPOTHESIS:                                                  |
//| Gold M5 shows mean-reverting volatility: periods of compression  |
//| (low ATR) followed by expansion (high ATR). Enter on the FIRST   |
//| expansion bar after compression, in the direction of the bar.    |
//| This captures the initial momentum of a new move.                |
//|                                                                   |
//| Additional filters:                                               |
//| - Session filter (London+NY only — Asia is noise on gold)        |
//| - Trend context from H1 EMA (trade with trend only)              |
//| - Minimum compression period (3+ bars of low ATR)                |
//| - SL at compression range opposite end, TP at 1.5R              |
//|                                                                   |
//| TARGET: 300-500 trades/year for prop firm frequency              |
//|                                                                   |
//| Max | 2026-04-12 | v1.0                                         |
//+------------------------------------------------------------------+
#property copyright "Max - EA_GoldPulse v1.0"
#property version   "1.00"
#property strict

#include <Trade\Trade.mqh>

//+------------------------------------------------------------------+
//| Inputs                                                            |
//+------------------------------------------------------------------+
input group "=== General ==="
input ulong    InpMagic         = 801201;
input int      InpDeviation     = 30;
input bool     InpKillSwitch    = false;

input group "=== Volatility Detection ==="
input int      InpATRPeriod     = 14;        // ATR period
input int      InpATRFastPeriod = 3;         // Fast ATR (current vol)
input double   InpCompressMult  = 0.85;      // Compression = fast ATR < slow ATR * this
input int      InpMinCompBars   = 2;         // Min bars in compression before signal
input double   InpExpandMult    = 1.05;      // Expansion = fast ATR > slow ATR * this

input group "=== Trend Filter (H1) ==="
input int      InpTrendEMA      = 50;        // H1 EMA period for trend
input bool     InpUseTrend      = true;      // Only trade with H1 trend

input group "=== Session Filter (Server Time) ==="
input int      InpLdnStart      = 8;         // London session start
input int      InpLdnEnd        = 11;        // London session end
input int      InpNYStart       = 13;        // NY session start
input int      InpNYEnd         = 17;        // NY session end
input bool     InpTradeAsia     = false;     // Trade Asian session?

input group "=== Entry / Exit ==="
input double   InpRR            = 1.5;       // Risk:Reward ratio
input double   InpMinSLPts      = 50;        // Min SL in points
input double   InpMaxSLPts      = 400;       // Max SL in points
input int      InpMaxBarsHold   = 30;        // Max bars in trade

input group "=== Risk Management ==="
input double   InpRiskPct       = 0.50;      // Risk per trade %
input double   InpMaxLot        = 0.50;      // Max lot
input int      InpMaxPerDay     = 5;         // Max trades per day
input int      InpMaxOpen       = 1;         // Max simultaneous
input double   InpDailyDDPct    = 4.0;       // Daily DD kill %

input group "=== Day Filters ==="
input bool     InpMon = true;
input bool     InpTue = true;
input bool     InpWed = true;
input bool     InpThu = true;
input bool     InpFri = true;

//+------------------------------------------------------------------+
//| Globals                                                           |
//+------------------------------------------------------------------+
CTrade         g_trade;
int            g_hATR;
int            g_hATRFast;
int            g_hEmaH1;
datetime       g_lastBar;
datetime       g_todayDate;
double         g_dayStartBal;
int            g_tradesToday;
int            g_barsHeld;
int            g_compressBars;   // consecutive compression bars

//+------------------------------------------------------------------+
int OnInit()
{
   if(InpKillSwitch) { Print("[GP] Kill switch ON"); return INIT_SUCCEEDED; }

   g_trade.SetExpertMagicNumber(InpMagic);
   g_trade.SetDeviationInPoints(InpDeviation);
   g_trade.SetTypeFilling(ORDER_FILLING_FOK);

   g_hATR     = iATR(_Symbol, PERIOD_CURRENT, InpATRPeriod);
   g_hATRFast = iATR(_Symbol, PERIOD_CURRENT, InpATRFastPeriod);
   g_hEmaH1   = iMA(_Symbol, PERIOD_H1, InpTrendEMA, 0, MODE_EMA, PRICE_CLOSE);

   if(g_hATR == INVALID_HANDLE || g_hATRFast == INVALID_HANDLE || g_hEmaH1 == INVALID_HANDLE)
   { Print("[GP] FATAL: Indicator init failed"); return INIT_FAILED; }

   g_lastBar       = 0;
   g_todayDate     = 0;
   g_dayStartBal   = AccountInfoDouble(ACCOUNT_BALANCE);
   g_tradesToday   = 0;
   g_barsHeld      = 0;
   g_compressBars  = 0;

   PrintFormat("[GP] GoldPulse v1.0 | %s %s | Magic=%d | ATR=%d/%d | Comp=%.1f Exp=%.1f",
               _Symbol, EnumToString(_Period), InpMagic,
               InpATRPeriod, InpATRFastPeriod, InpCompressMult, InpExpandMult);
   return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   if(g_hATR     != INVALID_HANDLE) IndicatorRelease(g_hATR);
   if(g_hATRFast != INVALID_HANDLE) IndicatorRelease(g_hATRFast);
   if(g_hEmaH1   != INVALID_HANDLE) IndicatorRelease(g_hEmaH1);
}

//+------------------------------------------------------------------+
bool InSession(int hour)
{
   if(hour >= InpLdnStart && hour < InpLdnEnd) return true;
   if(hour >= InpNYStart  && hour < InpNYEnd)  return true;
   if(InpTradeAsia && hour >= 0 && hour < 7)   return true;
   return false;
}

//+------------------------------------------------------------------+
bool IsTradingDay(int dow)
{
   switch(dow)
   {
      case 1: return InpMon;  case 2: return InpTue;  case 3: return InpWed;
      case 4: return InpThu;  case 5: return InpFri;  default: return false;
   }
}

//+------------------------------------------------------------------+
int CountPos()
{
   int n = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong t = PositionGetTicket(i);
      if(t > 0 && PositionGetInteger(POSITION_MAGIC) == (long)InpMagic &&
         PositionGetString(POSITION_SYMBOL) == _Symbol) n++;
   }
   return n;
}

//+------------------------------------------------------------------+
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

//+------------------------------------------------------------------+
void CloseAll()
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong t = PositionGetTicket(i);
      if(t > 0 && PositionGetInteger(POSITION_MAGIC) == (long)InpMagic &&
         PositionGetString(POSITION_SYMBOL) == _Symbol)
         g_trade.PositionClose(t);
   }
   g_barsHeld = 0;
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
      g_todayDate     = today;
      g_tradesToday   = 0;
      g_dayStartBal   = AccountInfoDouble(ACCOUNT_BALANCE);
      g_compressBars  = 0;
   }

   //=== Manage positions ===
   if(CountPos() > 0)
   {
      g_barsHeld++;
      if(g_barsHeld >= InpMaxBarsHold)
      {
         PrintFormat("[GP] Time exit %d bars", g_barsHeld);
         CloseAll();
      }
      return;
   }

   //=== Filters ===
   if(!IsTradingDay(dt.day_of_week)) return;
   if(!InSession(dt.hour)) return;
   if(g_tradesToday >= InpMaxPerDay) return;
   if(CountPos() >= InpMaxOpen) return;

   // Daily DD kill
   double ddPct = (g_dayStartBal > 0)
                  ? (g_dayStartBal - AccountInfoDouble(ACCOUNT_EQUITY)) / g_dayStartBal * 100.0 : 0;
   if(ddPct >= InpDailyDDPct) return;

   //=== Read indicators (bar[1]) ===
   double atrSlow[], atrFast[], emaH1[];
   if(CopyBuffer(g_hATR, 0, 1, 3, atrSlow) < 3) return;
   if(CopyBuffer(g_hATRFast, 0, 1, 3, atrFast) < 3) return;
   if(CopyBuffer(g_hEmaH1, 0, 0, 1, emaH1) < 1) return; // H1 EMA current

   double point  = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   int    digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);

   //=== Volatility state machine ===
   // atrFast[0] = bar[1], atrFast[1] = bar[2], atrFast[2] = bar[3]
   // atrSlow[0] = bar[1], atrSlow[1] = bar[2]

   // Check if bar[2] was in compression
   bool bar2Compressed = (atrFast[1] < atrSlow[1] * InpCompressMult);
   bool bar1Expanded   = (atrFast[0] > atrSlow[0] * InpExpandMult);

   if(bar2Compressed)
      g_compressBars++;
   else if(!bar1Expanded)
      g_compressBars = 0; // Reset if not compressed and not expanding

   //=== Entry: compression → expansion ===
   if(!bar1Expanded || g_compressBars < InpMinCompBars) return;

   // Direction from bar[1] body
   double open1  = iOpen(_Symbol, PERIOD_CURRENT, 1);
   double close1 = iClose(_Symbol, PERIOD_CURRENT, 1);
   double high1  = iHigh(_Symbol, PERIOD_CURRENT, 1);
   double low1   = iLow(_Symbol, PERIOD_CURRENT, 1);

   bool bullish = (close1 > open1);
   bool bearish = (close1 < open1);
   if(!bullish && !bearish) return; // doji, skip

   // H1 trend filter
   if(InpUseTrend)
   {
      double priceNow = SymbolInfoDouble(_Symbol, SYMBOL_BID);
      if(bullish && priceNow < emaH1[0]) return;  // Buy only above H1 EMA
      if(bearish && priceNow > emaH1[0]) return;   // Sell only below H1 EMA
   }

   //=== Calculate SL from compression range ===
   // Find the compression range (low to high of compressed bars)
   double compHigh = high1;
   double compLow  = low1;
   for(int i = 2; i <= g_compressBars + 1 && i < 30; i++)
   {
      double h = iHigh(_Symbol, PERIOD_CURRENT, i);
      double l = iLow(_Symbol, PERIOD_CURRENT, i);
      if(h > compHigh) compHigh = h;
      if(l < compLow)  compLow  = l;
   }

   double price, slPrice, tpPrice, slDist;

   if(bullish)
   {
      price   = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
      slPrice = compLow - point; // SL below compression low
      slDist  = price - slPrice;
      tpPrice = price + slDist * InpRR;
   }
   else
   {
      price   = SymbolInfoDouble(_Symbol, SYMBOL_BID);
      slPrice = compHigh + point; // SL above compression high
      slDist  = slPrice - price;
      tpPrice = price - slDist * InpRR;
   }

   // SL distance checks
   double slPts = slDist / point;
   if(slPts < InpMinSLPts || slPts > InpMaxSLPts) return;

   // Stop level check
   double stopLevel = SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL) * point;
   if(slDist < stopLevel) return;

   // Normalize
   slPrice = NormalizeDouble(slPrice, digits);
   tpPrice = NormalizeDouble(tpPrice, digits);

   // Lot
   double lot = CalcLot(slPts);
   if(lot <= 0) return;

   // Execute
   string comment = StringFormat("GP|comp=%d|atrF=%.1f|atrS=%.1f",
                                 g_compressBars, atrFast[0]/point, atrSlow[0]/point);
   bool ok = false;
   if(bullish)
      ok = g_trade.PositionOpen(_Symbol, ORDER_TYPE_BUY, lot, price, slPrice, tpPrice, comment);
   else
      ok = g_trade.PositionOpen(_Symbol, ORDER_TYPE_SELL, lot, price, slPrice, tpPrice, comment);

   if(ok)
   {
      g_tradesToday++;
      g_barsHeld      = 0;
      g_compressBars  = 0;
      PrintFormat("[GP] %s %.2f @ %.2f SL=%.2f TP=%.2f comp=%d",
                  bullish ? "BUY" : "SELL", lot, price, slPrice, tpPrice, g_compressBars);
   }
}
//+------------------------------------------------------------------+
