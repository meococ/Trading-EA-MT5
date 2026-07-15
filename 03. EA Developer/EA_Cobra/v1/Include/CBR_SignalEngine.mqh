//+------------------------------------------------------------------+
//| CBR_SignalEngine.mqh — Kill Zone Momentum Signal Generator       |
//| Core edge: Strong momentum bars in high-liquidity kill zones     |
//+------------------------------------------------------------------+
#ifndef CBR_SIGNALENGINE_MQH
#define CBR_SIGNALENGINE_MQH

#include "CBR_Config.mqh"
#include "CBR_Types.mqh"
#include "CBR_Indicators.mqh"

//+------------------------------------------------------------------+
//| Initialize signal struct                                          |
//+------------------------------------------------------------------+
void CBR_InitSignal(CBR_Signal &sig)
{
   sig.valid        = false;
   sig.type         = ORDER_TYPE_BUY;
   sig.killZone     = CBR_KZ_NONE;
   sig.atr          = 0.0;
   sig.bodyRatio    = 0.0;
   sig.closeLoc     = 0.0;
   sig.barRangeAtr  = 0.0;
   sig.bbwPctile    = 0.0;
   sig.bias         = 0;
   sig.emaFast      = 0.0;
   sig.emaSlow      = 0.0;
   sig.slPrice      = 0.0;
   sig.tpPrice      = 0.0;
   sig.slPts        = 0.0;
   sig.rrRatio      = 0.0;
   sig.rejectReason = "";
}

//+------------------------------------------------------------------+
//| Calculate close location value                                    |
//| For bullish: how close to HIGH (1.0 = closed at high)            |
//| For bearish: how close to LOW (1.0 = closed at low)              |
//+------------------------------------------------------------------+
double CBR_CalcCloseLoc(double open, double high, double low, double close)
{
   double range = high - low;
   if(range <= 0.0) return 0.0;

   if(close > open) // Bullish
      return (close - low) / range;     // 1.0 = closed at high
   else             // Bearish
      return (high - close) / range;    // 1.0 = closed at low
}

//+------------------------------------------------------------------+
//| MAIN SIGNAL: Check for momentum bar in kill zone                 |
//| Logic: Strong directional bar + trend aligned + vol context      |
//+------------------------------------------------------------------+
void CBR_CheckMomentumSignal(string symbol, ENUM_CBR_KILLZONE kz,
                              double maxSpread, CBR_Signal &sig)
{
   CBR_InitSignal(sig);
   sig.killZone = kz;

   //=== Gate 1: Must be in a kill zone ===
   if(kz == CBR_KZ_NONE)
   { sig.rejectReason = "no_killzone"; return; }

   //=== Gate 2: Spread check ===
   double spreadPts = (double)SymbolInfoInteger(symbol, SYMBOL_SPREAD);
   if(spreadPts > maxSpread)
   { sig.rejectReason = "spread_" + DoubleToString(spreadPts, 0); return; }

   //=== Gate 3: ATR available ===
   sig.atr = CBR_GetATR(1);
   if(sig.atr <= 0.0)
   { sig.rejectReason = "atr_na"; return; }

   //=== Gate 4: OHLC bar[1] (closed bar — NO lookahead) ===
   double o1 = iOpen(symbol, PERIOD_CURRENT, 1);
   double h1 = iHigh(symbol, PERIOD_CURRENT, 1);
   double l1 = iLow(symbol, PERIOD_CURRENT, 1);
   double c1 = iClose(symbol, PERIOD_CURRENT, 1);

   double body  = MathAbs(c1 - o1);
   double range = h1 - l1;

   if(range <= 0.0)
   { sig.rejectReason = "doji"; return; }

   //=== Gate 5: Body Ratio — strong candle (not doji/hammer) ===
   sig.bodyRatio = body / range;
   if(sig.bodyRatio < CBR_BODY_RATIO_MIN)
   { sig.rejectReason = "body_weak_" + DoubleToString(sig.bodyRatio, 2); return; }

   //=== Gate 6: Close Location — closed near extreme ===
   sig.closeLoc = CBR_CalcCloseLoc(o1, h1, l1, c1);
   if(sig.closeLoc < CBR_CLOSE_LOC_MIN)
   { sig.rejectReason = "close_loc_" + DoubleToString(sig.closeLoc, 2); return; }

   //=== Gate 7: Range vs ATR — meaningful move, not spike ===
   double atrPts = sig.atr / g_cbrPt;
   double rangePts = range / g_cbrPt;
   sig.barRangeAtr = rangePts / atrPts;

   if(sig.barRangeAtr < CBR_ATR_RANGE_MIN)
   { sig.rejectReason = "range_small_" + DoubleToString(sig.barRangeAtr, 2); return; }

   if(sig.barRangeAtr > CBR_ATR_RANGE_MAX)
   { sig.rejectReason = "range_spike_" + DoubleToString(sig.barRangeAtr, 2); return; }

   //=== Gate 8: Trend bias (H1 EMA alignment) ===
   sig.bias = CBR_GetBias(symbol);
   bool isBullBar = (c1 > o1);
   bool isBearBar = (c1 < o1);

   // Direction must align with bias
   // Exception: bias=0 (no clear trend) — allow both directions but with
   // stricter body ratio (0.65 instead of 0.55)
   if(sig.bias == 0)
   {
      if(sig.bodyRatio < 0.65)
      { sig.rejectReason = "no_bias_weak_body"; return; }
   }
   else if(sig.bias == 1 && !isBullBar)
   { sig.rejectReason = "bias_bull_bar_bear"; return; }
   else if(sig.bias == -1 && !isBearBar)
   { sig.rejectReason = "bias_bear_bar_bull"; return; }

   //=== Gate 9: BB Width context (optional squeeze bonus) ===
   sig.bbwPctile = CBR_CalcBBWPercentile(symbol);
   // We don't REQUIRE squeeze, but squeeze gives confidence
   // (stored for logging/analysis)

   //=== Gate 10: EMA values for logging ===
   CBR_GetEMA(sig.emaFast, sig.emaSlow);

   //=== All gates passed — Build execution levels ===

   // SL calculation
   double slAtrPts = atrPts * CBR_SL_ATR_MULT;
   if(slAtrPts < CBR_SL_MIN_PTS) slAtrPts = CBR_SL_MIN_PTS;
   if(slAtrPts > CBR_SL_MAX_PTS) slAtrPts = CBR_SL_MAX_PTS;

   sig.slPts  = slAtrPts;
   sig.rrRatio = CBR_GetRR(kz);

   if(isBullBar)
   {
      sig.valid   = true;
      sig.type    = ORDER_TYPE_BUY;
      sig.slPrice = c1 - slAtrPts * g_cbrPt;
      sig.tpPrice = c1 + slAtrPts * sig.rrRatio * g_cbrPt;
   }
   else if(isBearBar)
   {
      sig.valid   = true;
      sig.type    = ORDER_TYPE_SELL;
      sig.slPrice = c1 + slAtrPts * g_cbrPt;
      sig.tpPrice = c1 - slAtrPts * sig.rrRatio * g_cbrPt;
   }
   else
   {
      sig.rejectReason = "indeterminate";
   }
}

#endif // CBR_SIGNALENGINE_MQH
