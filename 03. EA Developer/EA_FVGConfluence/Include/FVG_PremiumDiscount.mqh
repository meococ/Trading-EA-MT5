//+------------------------------------------------------------------+
//| FVG_PremiumDiscount.mqh — swing PD + liquidity sweep               |
//+------------------------------------------------------------------+
#ifndef FVG_PREMIUMDISCOUNT_MQH
#define FVG_PREMIUMDISCOUNT_MQH

#include "FVG_Types.mqh"
#include "FVG_HTF.mqh"

// Equilibrium from recent chart-TF swing high/low (closed bars).
bool FVG_PD_Levels(const int lookback,
                   const int pivot_lr,
                   double &premium_top,
                   double &eq,
                   double &discount_bot)
{
   double sh, sl;
   datetime th, tl;
   if(!FVG_LastSwingHL(PERIOD_CURRENT, lookback, pivot_lr, sh, th, sl, tl))
      return false;
   premium_top = sh;
   discount_bot = sl;
   eq = 0.5 * (sh + sl);
   return true;
}

// Longs prefer discount (price below EQ); shorts prefer premium (above EQ).
bool FVG_PD_Aligned(const ENUM_FVG_DIR dir,
                    const int lookback,
                    const int pivot_lr)
{
   double top, eq, bot;
   if(!FVG_PD_Levels(lookback, pivot_lr, top, eq, bot))
      return false;
   double c = iClose(_Symbol, PERIOD_CURRENT, 1);
   if(dir == FVG_DIR_BULL)
      return (c <= eq);
   if(dir == FVG_DIR_BEAR)
      return (c >= eq);
   return false;
}

// Liquidity sweep: closed bar wicked beyond prior swing then closed back.
bool FVG_LiquiditySweepPrior(const ENUM_FVG_DIR dir,
                             const int lookback,
                             const int pivot_lr,
                             const int sweep_lookback)
{
   double sh, sl;
   datetime th, tl;
   if(!FVG_LastSwingHL(PERIOD_CURRENT, lookback, pivot_lr, sh, th, sl, tl))
      return false;

   int max_s = MathMin(sweep_lookback, Bars(_Symbol, PERIOD_CURRENT) - 2);
   for(int s = 1; s <= max_s; s++)
   {
      double h = iHigh(_Symbol, PERIOD_CURRENT, s);
      double l = iLow(_Symbol, PERIOD_CURRENT, s);
      double c = iClose(_Symbol, PERIOD_CURRENT, s);
      if(dir == FVG_DIR_BULL)
      {
         // sweep lows then reclaim
         if(l < sl && c > sl)
            return true;
      }
      else if(dir == FVG_DIR_BEAR)
      {
         if(h > sh && c < sh)
            return true;
      }
   }
   return false;
}

#endif
