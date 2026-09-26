//+------------------------------------------------------------------+
//| BE_Signal.mqh                                                    |
//| BoundaryEdge signal detection. Strictly past-only: the fade      |
//| level is built exclusively from the 12 M5 bars BEFORE 00:00 GMT; |
//| triggers read only closed bars; the chain leg is a timed entry   |
//| at a fixed week-open bar.                                        |
//+------------------------------------------------------------------+
#ifndef BE_SIGNAL_MQH
#define BE_SIGNAL_MQH

#include "BE_Types.mqh"
#include "../../EA_LiquiditySweep/Include/LSW_Types.mqh"

//--- Guarded closed-bar rate copy: the shift is a bare parameter proven
//--- >=1 by the dominating guard below (non-repaint audit contract).
bool BeCopyClosedM5(const string symbol,const int shift,const int count,
                    MqlRates &r[])
  {
   if(shift<1)
      return(false);
   ArraySetAsSeries(r,true);
   return(CopyRates(symbol,PERIOD_M5,shift,count,r)==count);
  }

//--- Reconstruct the prior-hour level for the GMT day containing `bar_time`.
//--- The level is the high/low envelope of the `level_bars` M5 bars ending
//--- at 23:55 GMT the previous day. `bar` must be the day's bar at GMT
//--- minute gmt_min (0 <= gmt_min < fade_trig_end). The bar at GMT 00:00
//--- sits `gmt_min/5` positions before it, so the level bars are the next
//--- `level_bars` positions further back. All must be contiguous 300s
//--- steps and the anchor bar must be at GMT minute 0 — else fail closed.
bool BeAsiaLevel(const string symbol,const MqlRates &bar,const int gmt_min,
                 const int level_bars,double &level_high,double &level_low)
  {
   level_high=0.0; level_low=0.0;
   if(gmt_min<0 || level_bars<1)
      return(false);
   // `bar` is the just-closed bar (shift 1). The day's 00:00 GMT bar sits
   // gmt_min/5 positions before it; the level bars are the `level_bars`
   // bars immediately older than that 00:00 bar (23:00-23:55 GMT).
   const int level_start=1+gmt_min/5+1;         // absolute shift of the 23:55 bar
   MqlRates r[];
   if(!BeCopyClosedM5(symbol,level_start,level_bars,r))
      return(false);
   for(int k=0;k<level_bars;k++)
     {
      const MqlRates x=r[k];
      if(x.time!=bar.time-(gmt_min/5+1+k)*BE_SEC_PER_M5)
         return(false);                         // gap inside the level: untrusted
      if(!LswFinite(x.high) || !LswFinite(x.low) || x.high<x.low)
         return(false);
      if(k==0 || x.high>level_high)
         level_high=x.high;
      if(k==0 || x.low<level_low)
         level_low=x.low;
     }
   return(level_high>level_low);
  }

//--- LEG_FADE: evaluate the just-closed bar (shift 1). Fires once per GMT
//--- day, only inside the trigger window [0, fade_trig_end).
bool BeDetectFade(const string symbol,const MqlRates &bar,const int gmt_min,
                  const int day_key,const BeParams &p,BeDayState &st,
                  BeSignal &out)
  {
   ZeroMemory(out);
   if(!p.use_fade || gmt_min<BE_ASIA_OPEN_MIN || gmt_min>=p.fade_trig_end)
      return(false);
   if(st.fade_day_key==day_key)
      return(false);                            // one fade entry per GMT day
   double lh=0.0,ll=0.0;
   if(!BeAsiaLevel(symbol,bar,gmt_min,p.fade_level_bars,lh,ll))
      return(false);
   if(bar.close>lh)
      { out.direction=LSW_DIR_SHORT; }
   else if(bar.close<ll)
      { out.direction=LSW_DIR_LONG; }
   else
      return(false);
   out.valid=true;
   out.leg=BE_LEG_FADE;
   out.level_high=lh;
   out.level_low=ll;
   out.ref_bar_time=bar.time;
   st.fade_day_key=day_key;
   return(true);
  }

//--- LEG_MONCH: timed week-open entry. Fires when the FORMING bar is the
//--- Monday 00:00 GMT bar (i.e., the first tick of that bar): decision uses
//--- wall-clock only, no price data — inherently past-only.
bool BeDetectMonChain(const int gmt_min,const int gmt_dow,const int day_key,
                      const BeParams &p,BeDayState &st,BeSignal &out)
  {
   ZeroMemory(out);
   if(!p.use_monch || gmt_dow!=1 || gmt_min!=BE_ASIA_OPEN_MIN)
      return(false);
   if(st.monch_day_key==day_key)
      return(false);
   out.valid=true;
   out.direction=LSW_DIR_LONG;
   out.leg=BE_LEG_MONCH;
   st.monch_day_key=day_key;
   return(true);
  }

//--- Time-exit minute for a leg, in GMT minutes past midnight.
int BeLegExitMin(const int leg,const BeParams &p)
  {
   if(leg==BE_LEG_FADE)
      return(p.asia_close_min);
   if(leg==BE_LEG_MONCH)
      return(p.monch_exit_min);
   return(-1);
  }

#endif
