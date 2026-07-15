//+------------------------------------------------------------------+
//| FVG_Detect.mqh — closed-bar 3-candle FVG detection                 |
//+------------------------------------------------------------------+
#ifndef FVG_DETECT_MQH
#define FVG_DETECT_MQH

#include "FVG_Types.mqh"

// Pip size: 3/5-digit FX → 10*Point; else Point (incl. many gold feeds).
double FVG_PipSize()
{
   int d = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
   double pt = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   if(d == 3 || d == 5)
      return pt * 10.0;
   return pt;
}

double FVG_PointsToPrice(const double points)
{
   return points * SymbolInfoDouble(_Symbol, SYMBOL_POINT);
}

double FVG_PipsToPrice(const double pips)
{
   return pips * FVG_PipSize();
}

double FVG_PriceToPips(const double price_dist)
{
   double pip = FVG_PipSize();
   if(pip <= 0.0)
      return 0.0;
   return price_dist / pip;
}

bool FVG_IsImpulseCandle(const int shift,
                         const double atr,
                         const double min_body_atr,
                         const double min_body_range)
{
   if(shift < 1)
      return false;
   double o = iOpen(_Symbol, PERIOD_CURRENT, shift);
   double h = iHigh(_Symbol, PERIOD_CURRENT, shift);
   double l = iLow(_Symbol, PERIOD_CURRENT, shift);
   double c = iClose(_Symbol, PERIOD_CURRENT, shift);
   double range = h - l;
   if(range <= 0.0)
      return false;
   double body = MathAbs(c - o);
   bool atr_ok = (atr > 0.0 && body >= atr * min_body_atr);
   bool ratio_ok = (body / range >= min_body_range);
   return (atr_ok || ratio_ok);
}

// 3-candle FVG at closed bars: newest of trio = shift (>=1).
// Bullish: High[shift+2] < Low[shift]  (no wick overlap)
// Bearish: Low[shift+2]  > High[shift]
bool FVG_DetectAtShift(const int shift,
                       const double atr,
                       const double min_gap_price,
                       const double min_body_atr,
                       const double min_body_range,
                       SFVGZone &out)
{
   out.valid = false;
   out.fully_mitigated = false;
   out.dir = FVG_DIR_NONE;
   if(shift < 1)
      return false;
   if(Bars(_Symbol, PERIOD_CURRENT) < shift + 3)
      return false;
   if(!FVG_IsImpulseCandle(shift + 1, atr, min_body_atr, min_body_range))
      return false;

   double h2 = iHigh(_Symbol, PERIOD_CURRENT, shift + 2);
   double l2 = iLow(_Symbol, PERIOD_CURRENT, shift + 2);
   double h0 = iHigh(_Symbol, PERIOD_CURRENT, shift);
   double l0 = iLow(_Symbol, PERIOD_CURRENT, shift);
   double ih = iHigh(_Symbol, PERIOD_CURRENT, shift + 1);
   double il = iLow(_Symbol, PERIOD_CURRENT, shift + 1);

   // Bullish FVG
   if(h2 < l0)
   {
      double gap = l0 - h2;
      if(gap < min_gap_price)
         return false;
      out.dir = FVG_DIR_BULL;
      out.bottom = h2;
      out.top = l0;
      out.mid = 0.5 * (out.top + out.bottom);
      out.impulse_high = ih;
      out.impulse_low = il;
      out.formed_time = iTime(_Symbol, PERIOD_CURRENT, shift);
      out.formed_shift = shift;
      out.valid = true;
      return true;
   }

   // Bearish FVG
   if(l2 > h0)
   {
      double gap = l2 - h0;
      if(gap < min_gap_price)
         return false;
      out.dir = FVG_DIR_BEAR;
      out.bottom = h0;
      out.top = l2;
      out.mid = 0.5 * (out.top + out.bottom);
      out.impulse_high = ih;
      out.impulse_low = il;
      out.formed_time = iTime(_Symbol, PERIOD_CURRENT, shift);
      out.formed_shift = shift;
      out.valid = true;
      return true;
   }
   return false;
}

// Mitigation: how much of the gap has been touched by subsequent closed bars
// (bars newer than formed_shift, i.e. shift < formed_shift). Prefer unmitigated
// or partially mitigated (< ~50% fill from impulse side).
bool FVG_IsAcceptableMitigation(const SFVGZone &zone,
                                const int from_shift,
                                const double max_fill_pct)
{
   if(!zone.valid)
      return false;
   double fill = 0.0;
   double gap = zone.top - zone.bottom;
   if(gap <= 0.0)
      return false;

   for(int s = from_shift; s >= 1; s--)
   {
      double h = iHigh(_Symbol, PERIOD_CURRENT, s);
      double l = iLow(_Symbol, PERIOD_CURRENT, s);
      if(zone.dir == FVG_DIR_BULL)
      {
         // fill from top down into gap
         if(l < zone.top)
         {
            double pen = MathMin(zone.top, MathMax(l, zone.bottom));
            // deepest fill from top
            double depth = zone.top - pen;
            if(h < zone.bottom)
               depth = gap; // fully through
            if(depth > fill)
               fill = depth;
         }
      }
      else if(zone.dir == FVG_DIR_BEAR)
      {
         if(h > zone.bottom)
         {
            double pen = MathMax(zone.bottom, MathMin(h, zone.top));
            double depth = pen - zone.bottom;
            if(l > zone.top)
               depth = gap;
            if(depth > fill)
               fill = depth;
         }
      }
   }

   double pct = fill / gap;
   if(pct >= 0.999)
      return false; // fully mitigated
   return (pct <= max_fill_pct);
}

bool FVG_PriceInteractsZone(const SFVGZone &zone, const int shift)
{
   if(!zone.valid || shift < 1)
      return false;
   double h = iHigh(_Symbol, PERIOD_CURRENT, shift);
   double l = iLow(_Symbol, PERIOD_CURRENT, shift);
   return !(h < zone.bottom || l > zone.top);
}

// Depth into gap from impulse side: 0 = edge first touch, 1 = full fill.
// Bull: entering from above → depth = (top - close_or_low) / gap
double FVG_EntryDepthPct(const SFVGZone &zone, const int shift)
{
   if(!zone.valid || shift < 1)
      return -1.0;
   double gap = zone.top - zone.bottom;
   if(gap <= 0.0)
      return -1.0;
   double c = iClose(_Symbol, PERIOD_CURRENT, shift);
   if(zone.dir == FVG_DIR_BULL)
   {
      // depth from top
      double d = (zone.top - c) / gap;
      return d;
   }
   double d = (c - zone.bottom) / gap;
   return d;
}

bool FVG_IsRejectionCandle(const int shift, const ENUM_FVG_DIR dir)
{
   if(shift < 1)
      return false;
   double o = iOpen(_Symbol, PERIOD_CURRENT, shift);
   double h = iHigh(_Symbol, PERIOD_CURRENT, shift);
   double l = iLow(_Symbol, PERIOD_CURRENT, shift);
   double c = iClose(_Symbol, PERIOD_CURRENT, shift);
   double range = h - l;
   if(range <= 0.0)
      return false;
   double body = MathAbs(c - o);
   double upper = h - MathMax(o, c);
   double lower = MathMin(o, c) - l;

   // Pin bar
   bool pin_bull = (lower >= range * 0.55 && body <= range * 0.35 && c > o);
   bool pin_bear = (upper >= range * 0.55 && body <= range * 0.35 && c < o);

   // Engulf prior body
   double po = iOpen(_Symbol, PERIOD_CURRENT, shift + 1);
   double pc = iClose(_Symbol, PERIOD_CURRENT, shift + 1);
   bool engulf_bull = (c > o && c >= MathMax(po, pc) && o <= MathMin(po, pc));
   bool engulf_bear = (c < o && c <= MathMin(po, pc) && o >= MathMax(po, pc));

   // Strong close (≥60% body in direction)
   bool strong_bull = (c > o && body / range >= 0.60);
   bool strong_bear = (c < o && body / range >= 0.60);

   if(dir == FVG_DIR_BULL)
      return (pin_bull || engulf_bull || strong_bull);
   if(dir == FVG_DIR_BEAR)
      return (pin_bear || engulf_bear || strong_bear);
   return false;
}

// Scan recent closed bars for the newest acceptable FVG (formed_shift >= 2 so
// at least one bar after formation can interact).
bool FVG_FindLatestZone(const int lookback,
                        const double atr,
                        const double min_gap_price,
                        const double min_body_atr,
                        const double min_body_range,
                        const double max_fill_pct,
                        SFVGZone &out)
{
   out.valid = false;
   int max_s = MathMin(lookback, Bars(_Symbol, PERIOD_CURRENT) - 4);
   for(int s = 2; s <= max_s; s++)
   {
      SFVGZone z;
      if(!FVG_DetectAtShift(s, atr, min_gap_price, min_body_atr, min_body_range, z))
         continue;
      // Mitigation evaluated on bars newer than formation (1 .. s-1)
      if(!FVG_IsAcceptableMitigation(z, 1, max_fill_pct))
         continue;
      out = z;
      return true;
   }
   return false;
}

#endif
