//+------------------------------------------------------------------+
//| EA_GoldSnap.mq5 — Gold M5 BB Squeeze Mean Reversion             |
//| Symbol: XAUUSD+  |  Period: M5  |  Style: Mean Reversion Scalp  |
//|                                                                   |
//| EDGE HYPOTHESIS:                                                  |
//| When BB width contracts to multi-day low (squeeze), the first    |
//| touch of BB outer band + RSI extreme = mean reversion trade      |
//| targeting the BB midline. High frequency on M5 gold.             |
//|                                                                   |
//| FILTERS:                                                          |
//| - BB width must be in bottom 20% of recent range (squeeze)       |
//| - RSI extreme: >70 for sell, <30 for buy                         |
//| - London + NY sessions only                                       |
//| - Trend filter: only trade with H1 EMA direction                 |
//| - SL at BB outer + buffer, TP at BB midline                      |
//|                                                                   |
//| TARGET: 300+ trades/year                                          |
//| Max | 2026-04-12 | v1.0                                         |
//+------------------------------------------------------------------+
#property copyright "Max - EA_GoldSnap v1.0"
#property version   "1.00"
#property strict

#include <Trade\Trade.mqh>

//+------------------------------------------------------------------+
input group "=== General ==="
input ulong    InpMagic         = 801301;
input int      InpDeviation     = 30;
input bool     InpKillSwitch    = false;

input group "=== Bollinger Bands ==="
input int      InpBBPeriod      = 20;        // BB period
input double   InpBBDev         = 2.0;       // BB deviation
input int      InpSqueezeLook   = 100;       // Lookback for squeeze percentile
input double   InpSqueezePerc   = 25.0;      // Squeeze = width below this percentile

input group "=== RSI ==="
input int      InpRSIPeriod     = 14;        // RSI period
input double   InpRSIOB         = 70.0;      // RSI overbought (sell trigger)
input double   InpRSIOS         = 30.0;      // RSI oversold (buy trigger)

input group "=== Trend Filter ==="
input int      InpTrendEMA      = 50;        // H1 EMA for trend
input bool     InpUseTrend      = false;     // Use H1 trend filter

input group "=== Session (Server Time) ==="
input int      InpSessStart     = 8;         // Session start
input int      InpSessEnd       = 20;        // Session end

input group "=== Risk Management ==="
input double   InpRiskPct       = 0.50;      // Risk per trade %
input double   InpMaxLot        = 0.50;
input int      InpMaxPerDay     = 6;
input int      InpMaxOpen       = 1;
input double   InpDailyDDPct    = 4.0;
input double   InpMinSLPts      = 30;        // Min SL points
input double   InpMaxSLPts      = 300;       // Max SL points
input int      InpMaxBarsHold   = 24;        // Max bars holding

//+------------------------------------------------------------------+
CTrade   g_trade;
int      g_hBB, g_hRSI, g_hEmaH1;
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

   g_hBB    = iBands(_Symbol, PERIOD_CURRENT, InpBBPeriod, 0, InpBBDev, PRICE_CLOSE);
   g_hRSI   = iRSI(_Symbol, PERIOD_CURRENT, InpRSIPeriod, PRICE_CLOSE);
   g_hEmaH1 = iMA(_Symbol, PERIOD_H1, InpTrendEMA, 0, MODE_EMA, PRICE_CLOSE);

   if(g_hBB == INVALID_HANDLE || g_hRSI == INVALID_HANDLE || g_hEmaH1 == INVALID_HANDLE)
   { Print("[GS] FATAL: Indicator init failed"); return INIT_FAILED; }

   g_lastBar = 0; g_todayDate = 0; g_tradesToday = 0; g_barsHeld = 0;
   g_dayStartBal = AccountInfoDouble(ACCOUNT_BALANCE);

   PrintFormat("[GS] GoldSnap v1.0 | %s %s | Magic=%d | BB=%d/%.1f | RSI=%d | Squeeze=%.0f%%",
               _Symbol, EnumToString(_Period), InpMagic,
               InpBBPeriod, InpBBDev, InpRSIPeriod, InpSqueezePerc);
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   if(g_hBB    != INVALID_HANDLE) IndicatorRelease(g_hBB);
   if(g_hRSI   != INVALID_HANDLE) IndicatorRelease(g_hRSI);
   if(g_hEmaH1 != INVALID_HANDLE) IndicatorRelease(g_hEmaH1);
}

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

   if(today != g_todayDate)
   { g_todayDate = today; g_tradesToday = 0; g_dayStartBal = AccountInfoDouble(ACCOUNT_BALANCE); }

   // Manage open positions
   if(CountPos() > 0)
   {
      g_barsHeld++;
      if(g_barsHeld >= InpMaxBarsHold) { CloseAll(); }
      return;
   }

   // Filters
   if(dt.hour < InpSessStart || dt.hour >= InpSessEnd) return;
   if(dt.day_of_week < 1 || dt.day_of_week > 5) return;
   if(g_tradesToday >= InpMaxPerDay) return;
   if(CountPos() >= InpMaxOpen) return;

   double ddPct = (g_dayStartBal > 0) ?
                  (g_dayStartBal - AccountInfoDouble(ACCOUNT_EQUITY)) / g_dayStartBal * 100.0 : 0;
   if(ddPct >= InpDailyDDPct) return;

   //=== Read indicators at bar[1] ===
   double bbUp[], bbMid[], bbLow[], rsi[], emaH1[];
   ArraySetAsSeries(bbUp, true);  ArraySetAsSeries(bbMid, true);
   ArraySetAsSeries(bbLow, true); ArraySetAsSeries(rsi, true);

   int need = InpSqueezeLook + 5;
   if(CopyBuffer(g_hBB, 1, 1, need, bbUp)  < need) return;  // Upper
   if(CopyBuffer(g_hBB, 0, 1, need, bbMid) < need) return;  // Middle
   if(CopyBuffer(g_hBB, 2, 1, need, bbLow) < need) return;  // Lower
   if(CopyBuffer(g_hRSI, 0, 1, 3, rsi) < 3) return;
   if(CopyBuffer(g_hEmaH1, 0, 0, 1, emaH1) < 1) return;

   double point  = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   int    digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);

   //=== BB Squeeze detection ===
   // Current BB width
   double bbWidth0 = bbUp[0] - bbLow[0];
   if(bbWidth0 <= 0) return;

   // Calculate percentile of current width in lookback
   int narrowerCount = 0;
   for(int i = 1; i < need; i++)
   {
      double w = bbUp[i] - bbLow[i];
      if(w < bbWidth0) narrowerCount++;
   }
   double percentile = (double)narrowerCount / (double)(need - 1) * 100.0;

   // Squeeze: current width is in bottom X percentile
   bool isSqueeze = (percentile <= InpSqueezePerc);
   if(!isSqueeze) return;

   //=== Signal: price at BB extreme + RSI extreme ===
   double close1 = iClose(_Symbol, PERIOD_CURRENT, 1);
   double high1  = iHigh(_Symbol, PERIOD_CURRENT, 1);
   double low1   = iLow(_Symbol, PERIOD_CURRENT, 1);

   bool sellSignal = (high1 >= bbUp[0] && rsi[0] >= InpRSIOB);
   bool buySignal  = (low1  <= bbLow[0] && rsi[0] <= InpRSIOS);

   if(!sellSignal && !buySignal) return;

   // Trend filter
   if(InpUseTrend)
   {
      if(buySignal  && close1 < emaH1[0]) return;
      if(sellSignal && close1 > emaH1[0]) return;
   }

   //=== Calculate SL/TP ===
   double price, slPrice, tpPrice, slDist;
   double slBuffer = 5 * point;

   if(buySignal)
   {
      price   = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
      slPrice = bbLow[0] - slBuffer;
      tpPrice = bbMid[0];
      slDist  = price - slPrice;
   }
   else
   {
      price   = SymbolInfoDouble(_Symbol, SYMBOL_BID);
      slPrice = bbUp[0] + slBuffer;
      tpPrice = bbMid[0];
      slDist  = slPrice - price;
   }

   double slPts = slDist / point;
   if(slPts < InpMinSLPts || slPts > InpMaxSLPts) return;

   // TP distance check (must be positive)
   double tpDist = buySignal ? (tpPrice - price) : (price - tpPrice);
   if(tpDist <= 0) return;

   // Stop level
   double stopLevel = SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL) * point;
   if(slDist < stopLevel || tpDist < stopLevel) return;

   // Normalize
   slPrice = NormalizeDouble(slPrice, digits);
   tpPrice = NormalizeDouble(tpPrice, digits);

   double lot = CalcLot(slPts);
   if(lot <= 0) return;

   string comment = StringFormat("GS|sq=%.0f%%|rsi=%.0f|bw=%.1f",
                                 percentile, rsi[0], bbWidth0/point);
   bool ok = false;
   if(buySignal)
      ok = g_trade.PositionOpen(_Symbol, ORDER_TYPE_BUY, lot, price, slPrice, tpPrice, comment);
   else
      ok = g_trade.PositionOpen(_Symbol, ORDER_TYPE_SELL, lot, price, slPrice, tpPrice, comment);

   if(ok)
   {
      g_tradesToday++;
      g_barsHeld = 0;
      PrintFormat("[GS] %s %.2f @ %.2f SL=%.2f TP=%.2f sq=%.0f%% rsi=%.0f",
                  buySignal ? "BUY" : "SELL", lot, price, slPrice, tpPrice, percentile, rsi[0]);
   }
}
//+------------------------------------------------------------------+
