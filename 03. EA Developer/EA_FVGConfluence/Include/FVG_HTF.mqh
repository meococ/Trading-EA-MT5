//+------------------------------------------------------------------+
//| FVG_HTF.mqh — HTF bias / BOS (closed-bar only)                     |
//+------------------------------------------------------------------+
#ifndef FVG_HTF_MQH
#define FVG_HTF_MQH

#include "FVG_Types.mqh"

int FVG_SwingPivotHigh(const ENUM_TIMEFRAMES tf, const int shift, const int left, const int right)
{
   // shift is the candidate pivot; requires right closed bars after it
   if(shift < right + 1)
      return 0;
   double h = iHigh(_Symbol, tf, shift);
   for(int i = 1; i <= left; i++)
   {
      if(iHigh(_Symbol, tf, shift + i) >= h)
         return 0;
   }
   for(int i = 1; i <= right; i++)
   {
      if(iHigh(_Symbol, tf, shift - i) > h)
         return 0;
   }
   return 1;
}

int FVG_SwingPivotLow(const ENUM_TIMEFRAMES tf, const int shift, const int left, const int right)
{
   if(shift < right + 1)
      return 0;
   double l = iLow(_Symbol, tf, shift);
   for(int i = 1; i <= left; i++)
   {
      if(iLow(_Symbol, tf, shift + i) <= l)
         return 0;
   }
   for(int i = 1; i <= right; i++)
   {
      if(iLow(_Symbol, tf, shift - i) < l)
         return 0;
   }
   return 1;
}

// Last confirmed swing high/low on HTF (closed bars only).
bool FVG_LastSwingHL(const ENUM_TIMEFRAMES tf,
                     const int lookback,
                     const int pivot_lr,
                     double &out_high,
                     datetime &out_high_t,
                     double &out_low,
                     datetime &out_low_t)
{
   out_high = 0.0;
   out_low = 0.0;
   out_high_t = 0;
   out_low_t = 0;
   int bars = Bars(_Symbol, tf);
   int max_s = MathMin(lookback, bars - pivot_lr - 2);
   bool got_h = false;
   bool got_l = false;
   for(int s = pivot_lr + 1; s <= max_s; s++)
   {
      if(!got_h && FVG_SwingPivotHigh(tf, s, pivot_lr, pivot_lr) == 1)
      {
         out_high = iHigh(_Symbol, tf, s);
         out_high_t = iTime(_Symbol, tf, s);
         got_h = true;
      }
      if(!got_l && FVG_SwingPivotLow(tf, s, pivot_lr, pivot_lr) == 1)
      {
         out_low = iLow(_Symbol, tf, s);
         out_low_t = iTime(_Symbol, tf, s);
         got_l = true;
      }
      if(got_h && got_l)
         break;
   }
   return (got_h && got_l);
}

// BOS: most recent closed HTF bar broke last swing in direction.
ENUM_FVG_DIR FVG_HTF_BOS(const ENUM_TIMEFRAMES tf,
                         const int lookback,
                         const int pivot_lr)
{
   double sh, sl;
   datetime th, tl;
   if(!FVG_LastSwingHL(tf, lookback, pivot_lr, sh, th, sl, tl))
      return FVG_DIR_NONE;

   // Scan newest closed bars for break
   int max_s = MathMin(lookback, Bars(_Symbol, tf) - 2);
   for(int s = 1; s <= max_s; s++)
   {
      double c = iClose(_Symbol, tf, s);
      datetime t = iTime(_Symbol, tf, s);
      if(t <= th && t <= tl)
         break;
      if(c > sh && t > th)
         return FVG_DIR_BULL;
      if(c < sl && t > tl)
         return FVG_DIR_BEAR;
   }
   return FVG_DIR_NONE;
}

// Soft bias: close vs mid of last swing range on HTF closed bar 1.
ENUM_FVG_DIR FVG_HTF_Bias(const ENUM_TIMEFRAMES tf,
                          const int lookback,
                          const int pivot_lr)
{
   ENUM_FVG_DIR bos = FVG_HTF_BOS(tf, lookback, pivot_lr);
   if(bos != FVG_DIR_NONE)
      return bos;

   double sh, sl;
   datetime th, tl;
   if(!FVG_LastSwingHL(tf, lookback, pivot_lr, sh, th, sl, tl))
      return FVG_DIR_NONE;
   double mid = 0.5 * (sh + sl);
   double c = iClose(_Symbol, tf, 1);
   if(c > mid)
      return FVG_DIR_BULL;
   if(c < mid)
      return FVG_DIR_BEAR;
   return FVG_DIR_NONE;
}

bool FVG_HTF_Aligned(const ENUM_FVG_DIR setup_dir,
                     const ENUM_TIMEFRAMES tf,
                     const int lookback,
                     const int pivot_lr)
{
   ENUM_FVG_DIR bias = FVG_HTF_Bias(tf, lookback, pivot_lr);
   if(bias == FVG_DIR_NONE || setup_dir == FVG_DIR_NONE)
      return false;
   return (bias == setup_dir);
}

#endif
