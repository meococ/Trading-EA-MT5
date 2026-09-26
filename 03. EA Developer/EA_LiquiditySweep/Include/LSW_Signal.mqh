//+------------------------------------------------------------------+
//| LSW_Signal.mqh                                                   |
//| Sweep detection on closed M5 bars.                               |
//|                                                                  |
//| A sweep is: a bounded excursion beyond a reference level that     |
//| CLOSES BACK on the side it came from. Too shallow is noise; too   |
//| deep is a real breakout, not a stop cascade. Both are rejected.   |
//| Direction is always AGAINST the excursion.                        |
//+------------------------------------------------------------------+
#ifndef LSW_SIGNAL_MQH
#define LSW_SIGNAL_MQH

#include "LSW_Types.mqh"

//--- ATR at an explicit shift. count==1 makes the destination index direction
//--- irrelevant: buf[0] is the value at `shift` and nothing else is copied.
bool LswAtrAt(const int handle,const int shift,double &atr)
  {
   atr=0.0;
   if(handle==INVALID_HANDLE || shift<1)
      return(false);                     // shift 0 is the forming bar: never read
   double buf[1];
   ResetLastError();
   if(CopyBuffer(handle,0,shift,1,buf)!=1)
      return(false);
   if(!LswFinite(buf[0]) || buf[0]<=0.0)
      return(false);
   atr=buf[0];
   return(true);
  }

//--- One closed M5 bar at an explicit shift. count==1, so out is exactly that
//--- bar regardless of series flag; the flag is set anyway to state intent.
bool LswBarAt(const string symbol,const int shift,MqlRates &out)
  {
   if(shift<1)
      return(false);                     // shift 0 is the forming bar: never read
   MqlRates r[];
   ArraySetAsSeries(r,true);
   ResetLastError();
   if(CopyRates(symbol,PERIOD_M5,shift,1,r)!=1)
      return(false);
   if(!LswFinite(r[0].high) || !LswFinite(r[0].low) || !LswFinite(r[0].close) ||
      r[0].high<r[0].low || r[0].time<=0)
      return(false);
   out=r[0];
   return(true);
  }

//--- Detect the sweep on `bar`, given the bar before it and (optionally) the
//--- bar after it. All three are closed bars supplied by the caller.
//---   bar       : the sweep bar
//---   prev      : the bar immediately before it (proves approach direction)
//---   hold      : the bar immediately after it, only read when cfg says so
//--- Returns true when a tradable sweep was found. Reject attribution is
//--- written into counters exactly once per decision, not once per level.
bool LswDetectSweep(const LswLevelSet &levels,const MqlRates &bar,
                    const MqlRates &prev,const MqlRates &hold,
                    const double atr,const LswConfig &cfg,
                    LswSweep &out,LswCounters &cnt)
  {
   ZeroMemory(out);
   out.atr=atr;
   out.bar_time=bar.time;
   out.close_price=bar.close;

   if(levels.count<=0)
     {
      out.reject="NO_LEVEL";
      cnt.geom_no_level++;
      return(false);
     }
   if(!LswFinite(atr) || atr<=0.0)
     {
      out.reject="NO_ATR";
      cnt.data_fail++;
      return(false);
     }

   const double min_pen=cfg.sweep_min_atr*atr;
   const double max_pen=cfg.sweep_max_atr*atr;

   bool saw_pen_small=false,saw_pen_large=false;
   bool saw_no_close_back=false,saw_bad_approach=false,saw_hold_failed=false;

   int    best_short=-1;
   double best_short_pen=-1.0;
   int    best_long=-1;
   double best_long_pen=-1.0;

   for(int i=0;i<levels.count;i++)
     {
      const double L=levels.items[i].price;
      if(!LswFinite(L) || L<=0.0)
         continue;
      //--- The bar must actually straddle the level. Without this, every level
      //--- far above or below the bar would fire the opposite-side test and
      //--- bury the reject counters in noise that means nothing.
      if(L<bar.low || L>bar.high)
         continue;

      //--- HIGH sweep: excursion above L, close back below  => SHORT
      const double pen_h=bar.high-L;
      if(pen_h>0.0)
        {
         if(pen_h<min_pen)
            saw_pen_small=true;
         else if(pen_h>max_pen)
            saw_pen_large=true;
         else if(bar.close>=L)
            saw_no_close_back=true;
         else if(prev.close>L)
            saw_bad_approach=true;       // price was already above: not a sweep
         else if(cfg.require_next_bar_hold && hold.high>L)
            saw_hold_failed=true;
         else if(pen_h>best_short_pen)
           {
            best_short_pen=pen_h;
            best_short=i;
           }
        }

      //--- LOW sweep: excursion below L, close back above  => LONG
      const double pen_l=L-bar.low;
      if(pen_l>0.0)
        {
         if(pen_l<min_pen)
            saw_pen_small=true;
         else if(pen_l>max_pen)
            saw_pen_large=true;
         else if(bar.close<=L)
            saw_no_close_back=true;
         else if(prev.close<L)
            saw_bad_approach=true;
         else if(cfg.require_next_bar_hold && hold.low<L)
            saw_hold_failed=true;
         else if(pen_l>best_long_pen)
           {
            best_long_pen=pen_l;
            best_long=i;
           }
        }
     }

   //--- An outside bar that sweeps both sides is ambiguous. It is rejected,
   //--- not resolved by preference: the mechanism cannot say which side the
   //--- dealer inventory ended up on.
   if(best_short>=0 && best_long>=0)
     {
      out.reject="CONFLICT";
      cnt.geom_conflict++;
      return(false);
     }

   if(best_short<0 && best_long<0)
     {
      if(saw_pen_large)        { out.reject="PEN_LARGE";      cnt.geom_pen_large++; }
      else if(saw_no_close_back){ out.reject="NO_CLOSE_BACK"; cnt.geom_no_close_back++; }
      else if(saw_hold_failed) { out.reject="HOLD_FAILED";    cnt.geom_hold_failed++; }
      else if(saw_bad_approach){ out.reject="BAD_APPROACH";   cnt.geom_bad_approach++; }
      else if(saw_pen_small)   { out.reject="PEN_SMALL";      cnt.geom_pen_small++; }
      else                     { out.reject="NO_LEVEL";       cnt.geom_no_level++; }
      return(false);
     }

   const int    idx=(best_short>=0 ? best_short : best_long);
   const double pen=(best_short>=0 ? best_short_pen : best_long_pen);
   out.valid=true;
   out.direction=(best_short>=0 ? LSW_DIR_SHORT : LSW_DIR_LONG);
   out.level=levels.items[idx].price;
   out.family=levels.items[idx].family;
   out.extreme=(best_short>=0 ? bar.high : bar.low);
   out.penetration=pen;
   out.reject="";

   cnt.signals_seen++;
   if(out.direction==LSW_DIR_LONG)
      cnt.signals_long++;
   else
      cnt.signals_short++;
   // Explicit int for the array index: an enum is not an index type here.
   const int family_index=(int)out.family;
   if(family_index>0 && family_index<LSW_FAMILY_COUNT)
      cnt.signals_by_family[family_index]++;
   return(true);
  }

#endif
