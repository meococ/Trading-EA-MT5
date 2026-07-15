//+------------------------------------------------------------------+
//| CBR_SignalEngine.mqh — Level-Based Kill Zone Signal Generator     |
//| v2 CORE CHANGE: Requires price interaction with reference level   |
//|                                                                   |
//| EDGE THESIS: Kill zone timing + structural level + momentum bar  |
//|  = Time × Price_Level × Momentum = Statistical edge              |
//|                                                                   |
//| Levels used:                                                      |
//|  1. Asian Range Hi/Lo (built 00:00-06:59, used in LDN/NY KZ)    |
//|  2. Previous Day Hi/Lo (D1 bar[1], used in all KZ)               |
//|                                                                   |
//| Entry modes:                                                      |
//|  BREAKOUT: Price closed beyond level + momentum bar               |
//|  BOUNCE:   Price touched level zone + rejected (wicked) + close   |
//|            back inside → fade the touch (mean revert from level)  |
//+------------------------------------------------------------------+
#ifndef CBR_SIGNALENGINE_MQH
#define CBR_SIGNALENGINE_MQH

#include "CBR_Config.mqh"
#include "CBR_Types.mqh"
#include "CBR_Indicators.mqh"
#include "CBR_SessionTime.mqh"

//+------------------------------------------------------------------+
//| Initialize signal struct                                          |
//+------------------------------------------------------------------+
void CBR_InitSignal(CBR_Signal &sig)
{
   sig.valid        = false;
   sig.type         = ORDER_TYPE_BUY;
   sig.killZone     = CBR_KZ_NONE;
   sig.entryMode    = CBR_ENTRY_NONE;
   sig.levelType    = CBR_LVL_NONE;
   sig.levelPrice   = 0.0;
   sig.levelDist    = 0.0;
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
//+------------------------------------------------------------------+
double CBR_CalcCloseLoc(double open, double high, double low, double close)
{
   double range = high - low;
   if(range <= 0.0) return 0.0;
   if(close > open) return (close - low) / range;
   else             return (high - close) / range;
}

//+------------------------------------------------------------------+
//| Check BREAKOUT interaction with a single level                    |
//| Returns true if bar[1] broke through the level with momentum      |
//+------------------------------------------------------------------+
bool CBR_CheckBreakout(double c1, double o1, double h1, double l1,
                        double levelPrice, double pt,
                        bool isUpperLevel,  // true = Asian Hi / PrevDay Hi
                        ENUM_ORDER_TYPE &direction)
{
   double breakPts = CBR_LEVEL_BREAK_PTS * pt;

   if(isUpperLevel)
   {
      // BUY breakout: close ABOVE level + break distance, bullish bar
      if(c1 > levelPrice + breakPts && c1 > o1)
      {
         direction = ORDER_TYPE_BUY;
         return true;
      }
   }
   else
   {
      // SELL breakout: close BELOW level - break distance, bearish bar
      if(c1 < levelPrice - breakPts && c1 < o1)
      {
         direction = ORDER_TYPE_SELL;
         return true;
      }
   }

   return false;
}

//+------------------------------------------------------------------+
//| Check BOUNCE interaction with a single level                      |
//| Returns true if bar[1] wicked into level zone but closed back     |
//+------------------------------------------------------------------+
bool CBR_CheckBounce(double c1, double o1, double h1, double l1,
                      double levelPrice, double pt,
                      bool isUpperLevel,
                      ENUM_ORDER_TYPE &direction)
{
   double zonePts = CBR_LEVEL_ZONE_PTS * pt;

   if(isUpperLevel)
   {
      // SELL bounce: wick touched level zone (high >= level - zone)
      //              but closed below level (rejection)
      //              bearish bar (close < open)
      if(h1 >= levelPrice - zonePts && c1 < levelPrice && c1 < o1)
      {
         direction = ORDER_TYPE_SELL;
         return true;
      }
   }
   else
   {
      // BUY bounce: wick touched level zone (low <= level + zone)
      //             but closed above level (rejection)
      //             bullish bar (close > open)
      if(l1 <= levelPrice + zonePts && c1 > levelPrice && c1 > o1)
      {
         direction = ORDER_TYPE_BUY;
         return true;
      }
   }

   return false;
}

//+------------------------------------------------------------------+
//| Scan all levels for best interaction                              |
//| Priority: Asian levels first (stronger), then PrevDay             |
//| Within type: Breakout > Bounce (breakout has more follow-through) |
//+------------------------------------------------------------------+
bool CBR_FindLevelSignal(double c1, double o1, double h1, double l1,
                          double pt, int bias,
                          ENUM_ORDER_TYPE &direction,
                          ENUM_CBR_ENTRY_MODE &entryMode,
                          ENUM_CBR_LEVEL_TYPE &levelType,
                          double &levelPrice)
{
   //=== 1. Asian Range levels (strongest — daily structure) ===
   if(g_cbrLevels.asianValid)
   {
      // Asian Hi — breakout BUY or bounce SELL
      if(CBR_CheckBreakout(c1, o1, h1, l1, g_cbrLevels.asianHi, pt, true, direction))
      {
         // v2.1: Breakout BUY needs STRICT bull bias
         if(bias == 1)
         {
            entryMode  = CBR_ENTRY_BREAKOUT;
            levelType  = CBR_LVL_ASIAN_HI;
            levelPrice = g_cbrLevels.asianHi;
            return true;
         }
      }
      if(CBR_CheckBounce(c1, o1, h1, l1, g_cbrLevels.asianHi, pt, true, direction))
      {
         // v2.1: Bounce SELL from Asian Hi needs STRICT bear bias
         if(bias == -1)
         {
            entryMode  = CBR_ENTRY_BOUNCE;
            levelType  = CBR_LVL_ASIAN_HI;
            levelPrice = g_cbrLevels.asianHi;
            return true;
         }
      }

      // Asian Lo — breakout SELL or bounce BUY
      if(CBR_CheckBreakout(c1, o1, h1, l1, g_cbrLevels.asianLo, pt, false, direction))
      {
         // v2.1: STRICT bear bias for SELL breakout
         if(bias == -1)
         {
            entryMode  = CBR_ENTRY_BREAKOUT;
            levelType  = CBR_LVL_ASIAN_LO;
            levelPrice = g_cbrLevels.asianLo;
            return true;
         }
      }
      if(CBR_CheckBounce(c1, o1, h1, l1, g_cbrLevels.asianLo, pt, false, direction))
      {
         // v2.1: STRICT bull bias for BUY bounce
         if(bias == 1)
         {
            entryMode  = CBR_ENTRY_BOUNCE;
            levelType  = CBR_LVL_ASIAN_LO;
            levelPrice = g_cbrLevels.asianLo;
            return true;
         }
      }
   }

   //=== 2. Previous Day levels (weaker — broader context) ===
   if(g_cbrLevels.prevDayValid)
   {
      // PrevDay Hi — breakout BUY or bounce SELL
      if(CBR_CheckBreakout(c1, o1, h1, l1, g_cbrLevels.prevDayHi, pt, true, direction))
      {
         // v2.1: STRICT bull bias
         if(bias == 1)
         {
            entryMode  = CBR_ENTRY_BREAKOUT;
            levelType  = CBR_LVL_PREV_HI;
            levelPrice = g_cbrLevels.prevDayHi;
            return true;
         }
      }
      if(CBR_CheckBounce(c1, o1, h1, l1, g_cbrLevels.prevDayHi, pt, true, direction))
      {
         // v2.1: STRICT bear bias
         if(bias == -1)
         {
            entryMode  = CBR_ENTRY_BOUNCE;
            levelType  = CBR_LVL_PREV_HI;
            levelPrice = g_cbrLevels.prevDayHi;
            return true;
         }
      }

      // PrevDay Lo — breakout SELL or bounce BUY
      if(CBR_CheckBreakout(c1, o1, h1, l1, g_cbrLevels.prevDayLo, pt, false, direction))
      {
         // v2.1: STRICT bear bias
         if(bias == -1)
         {
            entryMode  = CBR_ENTRY_BREAKOUT;
            levelType  = CBR_LVL_PREV_LO;
            levelPrice = g_cbrLevels.prevDayLo;
            return true;
         }
      }
      if(CBR_CheckBounce(c1, o1, h1, l1, g_cbrLevels.prevDayLo, pt, false, direction))
      {
         // v2.1: STRICT bull bias
         if(bias == 1)
         {
            entryMode  = CBR_ENTRY_BOUNCE;
            levelType  = CBR_LVL_PREV_LO;
            levelPrice = g_cbrLevels.prevDayLo;
            return true;
         }
      }
   }

   return false;
}

//+------------------------------------------------------------------+
//| MAIN SIGNAL: Level-based kill zone signal                        |
//| Gate sequence:                                                    |
//|  1. Kill zone active                                              |
//|  2. Spread OK                                                     |
//|  3. ATR available                                                 |
//|  4. At least one level set valid                                  |
//|  5. Bar quality (body ratio, close location, range)               |
//|  6. Level interaction found (breakout or bounce)                  |
//|  7. Build execution levels (SL anchored to level)                 |
//+------------------------------------------------------------------+
void CBR_CheckLevelSignal(string symbol, ENUM_CBR_KILLZONE kz,
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

   //=== Gate 4: At least one level set must be valid ===
   if(!g_cbrLevels.asianValid && !g_cbrLevels.prevDayValid)
   { sig.rejectReason = "no_levels"; return; }

   //=== Gate 5: OHLC bar[1] (closed bar — NO lookahead) ===
   double o1 = iOpen(symbol, PERIOD_CURRENT, 1);
   double h1 = iHigh(symbol, PERIOD_CURRENT, 1);
   double l1 = iLow(symbol, PERIOD_CURRENT, 1);
   double c1 = iClose(symbol, PERIOD_CURRENT, 1);

   double body  = MathAbs(c1 - o1);
   double range = h1 - l1;

   if(range <= 0.0)
   { sig.rejectReason = "doji"; return; }

   //=== Gate 6: Body Ratio ===
   sig.bodyRatio = body / range;
   if(sig.bodyRatio < CBR_BODY_RATIO_MIN)
   { sig.rejectReason = "body_" + DoubleToString(sig.bodyRatio, 2); return; }

   //=== Gate 7: Close Location ===
   sig.closeLoc = CBR_CalcCloseLoc(o1, h1, l1, c1);
   if(sig.closeLoc < CBR_CLOSE_LOC_MIN)
   { sig.rejectReason = "cloc_" + DoubleToString(sig.closeLoc, 2); return; }

   //=== Gate 8: Range vs ATR ===
   double atrPts = sig.atr / g_cbrPt;
   double rangePts = range / g_cbrPt;
   sig.barRangeAtr = rangePts / atrPts;

   if(sig.barRangeAtr < CBR_ATR_RANGE_MIN)
   { sig.rejectReason = "range_small"; return; }
   if(sig.barRangeAtr > CBR_ATR_RANGE_MAX)
   { sig.rejectReason = "range_spike"; return; }

   //=== Gate 9: Trend bias ===
   sig.bias = CBR_GetBias(symbol);
   CBR_GetEMA(sig.emaFast, sig.emaSlow);

   //=== Gate 10: BBW context (logged, not required) ===
   sig.bbwPctile = CBR_CalcBBWPercentile(symbol);

   //=== Gate 10b (v2.1): STRICT BIAS — must have directional bias ===
   if(sig.bias == 0)
   { sig.rejectReason = "no_bias"; return; }

   //=== Gate 11: LEVEL INTERACTION — the KEY gate ===
   ENUM_ORDER_TYPE direction;
   ENUM_CBR_ENTRY_MODE entryMode;
   ENUM_CBR_LEVEL_TYPE levelType;
   double levelPrice;

   if(!CBR_FindLevelSignal(c1, o1, h1, l1, g_cbrPt, sig.bias,
                            direction, entryMode, levelType, levelPrice))
   {
      sig.rejectReason = "no_level_interaction";
      return;
   }

   sig.entryMode  = entryMode;
   sig.levelType  = levelType;
   sig.levelPrice = levelPrice;
   sig.levelDist  = MathAbs(c1 - levelPrice) / g_cbrPt;

   //=== Gate 11b (v2.1): Level distance filter — reject if too far from level ===
   double levelDistAtr = sig.levelDist / atrPts;
   if(levelDistAtr > CBR_MAX_LEVEL_DIST_ATR)
   { sig.rejectReason = "level_too_far_" + DoubleToString(levelDistAtr, 1); return; }

   //=== All gates passed — Build execution levels ===

   // SL: Anchored to LEVEL (structural), not just ATR
   double slAtrPts = atrPts * CBR_SL_ATR_MULT;

   // For BREAKOUT: SL beyond the level (structural invalid point)
   // For BOUNCE: SL beyond the bar extreme + buffer
   double structuralSL = 0.0;

   if(entryMode == CBR_ENTRY_BREAKOUT)
   {
      // Breakout BUY from level: SL = level - ATR*0.3 (below the broken level)
      // Breakout SELL from level: SL = level + ATR*0.3
      if(direction == ORDER_TYPE_BUY)
         structuralSL = levelPrice - atrPts * 0.3 * g_cbrPt;
      else
         structuralSL = levelPrice + atrPts * 0.3 * g_cbrPt;
   }
   else // BOUNCE
   {
      // Bounce: SL beyond the wick (the extreme that touched the level)
      if(direction == ORDER_TYPE_BUY)
         structuralSL = l1 - atrPts * 0.2 * g_cbrPt;  // Below the low
      else
         structuralSL = h1 + atrPts * 0.2 * g_cbrPt;  // Above the high
   }

   // Use the BETTER (closer to valid) of structural SL and ATR SL
   double atrSL = 0.0;
   if(direction == ORDER_TYPE_BUY)
      atrSL = c1 - slAtrPts * g_cbrPt;
   else
      atrSL = c1 + slAtrPts * g_cbrPt;

   // Pick the WIDER (more protective) SL
   double finalSL = 0.0;
   if(direction == ORDER_TYPE_BUY)
      finalSL = MathMin(structuralSL, atrSL);  // Lower = more protective for BUY
   else
      finalSL = MathMax(structuralSL, atrSL);  // Higher = more protective for SELL

   // Validate SL distance
   double slDist = MathAbs(c1 - finalSL) / g_cbrPt;
   if(slDist < CBR_SL_MIN_PTS)
   {
      if(direction == ORDER_TYPE_BUY)
         finalSL = c1 - CBR_SL_MIN_PTS * g_cbrPt;
      else
         finalSL = c1 + CBR_SL_MIN_PTS * g_cbrPt;
      slDist = CBR_SL_MIN_PTS;
   }
   if(slDist > CBR_SL_MAX_PTS)
   {
      sig.rejectReason = "sl_too_wide_" + DoubleToString(slDist, 0);
      return;
   }

   // TP based on R:R
   sig.slPts   = slDist;
   sig.rrRatio = CBR_GetRR(kz);
   sig.type    = direction;
   sig.valid   = true;

   if(direction == ORDER_TYPE_BUY)
   {
      sig.slPrice = finalSL;
      sig.tpPrice = c1 + slDist * sig.rrRatio * g_cbrPt;
   }
   else
   {
      sig.slPrice = finalSL;
      sig.tpPrice = c1 - slDist * sig.rrRatio * g_cbrPt;
   }
}

#endif // CBR_SIGNALENGINE_MQH
