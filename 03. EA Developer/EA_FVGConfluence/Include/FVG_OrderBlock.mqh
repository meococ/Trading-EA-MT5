//+------------------------------------------------------------------+
//| FVG_OrderBlock.mqh — nearby opposite OB before impulse             |
//+------------------------------------------------------------------+
#ifndef FVG_ORDERBLOCK_MQH
#define FVG_ORDERBLOCK_MQH

#include "FVG_Types.mqh"

// Bullish OB: last bearish candle before bullish impulse near FVG bottom.
// Bearish OB: last bullish candle before bearish impulse near FVG top.
bool FVG_FindNearbyOB(const SFVGZone &zone,
                      const int search_bars,
                      const double max_dist_price,
                      double &ob_high,
                      double &ob_low)
{
   ob_high = 0.0;
   ob_low = 0.0;
   if(!zone.valid)
      return false;

   int start = zone.formed_shift + 2; // before the 3-candle pattern
   int end = start + search_bars;
   int bars = Bars(_Symbol, PERIOD_CURRENT);
   if(start >= bars - 1)
      return false;
   if(end >= bars - 1)
      end = bars - 2;

   for(int s = start; s <= end; s++)
   {
      double o = iOpen(_Symbol, PERIOD_CURRENT, s);
      double c = iClose(_Symbol, PERIOD_CURRENT, s);
      double h = iHigh(_Symbol, PERIOD_CURRENT, s);
      double l = iLow(_Symbol, PERIOD_CURRENT, s);

      if(zone.dir == FVG_DIR_BULL)
      {
         if(c >= o)
            continue; // need bearish candle
         double dist = MathAbs(h - zone.bottom);
         if(dist <= max_dist_price)
         {
            ob_high = h;
            ob_low = l;
            return true;
         }
      }
      else if(zone.dir == FVG_DIR_BEAR)
      {
         if(c <= o)
            continue;
         double dist = MathAbs(l - zone.top);
         if(dist <= max_dist_price)
         {
            ob_high = h;
            ob_low = l;
            return true;
         }
      }
   }
   return false;
}

bool FVG_HasNearbyOB(const SFVGZone &zone,
                     const int search_bars,
                     const double max_dist_price)
{
   double h, l;
   return FVG_FindNearbyOB(zone, search_bars, max_dist_price, h, l);
}

#endif
