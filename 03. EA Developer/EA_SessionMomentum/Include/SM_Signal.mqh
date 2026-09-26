//+------------------------------------------------------------------+
//| SM_Signal.mqh                                                    |
//| SessionMomentum signal detection. Strictly past-only: levels are |
//| built exclusively from same-GMT-day bars closed BEFORE the       |
//| session open; triggers read only closed bars.                    |
//+------------------------------------------------------------------+
#ifndef SM_SIGNAL_MQH
#define SM_SIGNAL_MQH

#include "SM_Types.mqh"
#include "../../EA_LiquiditySweep/Include/LSW_Types.mqh"

//--- Guarded closed-bar rate copy: the shift is a bare parameter proven
//--- >=1 by the dominating guard below (non-repaint audit contract).
bool SmCopyClosedM5(const string symbol,const int shift,const int count,
                    MqlRates &r[])
  {
   if(shift<1)
      return(false);
   ArraySetAsSeries(r,true);
   return(CopyRates(symbol,PERIOD_M5,shift,count,r)==count);
  }

//--- Reconstruct the prior-session level for the GMT day containing `bar`.
//--- `bar` is the just-closed bar (shift 1) whose open GMT minute is
//--- gmt_min. The level is the high/low envelope of the same-day M5 bars
//--- in [prior_start, prior_end): the last level bar opens at prior_end-5,
//--- which sits (gmt_min-(prior_end-5))/5 positions before `bar`.
//--- All level bars must be contiguous 300s steps inside the same GMT day
//--- and at least 12 bars deep — else fail closed.
bool SmSessionLevel(const string symbol,const MqlRates &bar,const int gmt_min,
                    const SmLegGeom &g,double &level_high,double &level_low)
  {
   level_high=0.0; level_low=0.0;
   const int nbars=(g.prior_end-g.prior_start)/5;
   if(gmt_min<g.open_min || nbars<12)
      return(false);
   // absolute shift of the (prior_end-5) bar relative to `bar` at shift 1
   const int level_start=1+(gmt_min-g.prior_end)/5+1;
   MqlRates r[];
   if(!SmCopyClosedM5(symbol,level_start,nbars,r))
      return(false);
   for(int k=0;k<nbars;k++)
     {
      const MqlRates x=r[k];
      // bar k opens at (prior_end-5-5k): expected offset from `bar`
      if(x.time!=bar.time-(gmt_min-g.prior_end+5+5*k)*60)
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

//--- Continuation detect for one leg on the just-closed bar. Fires once
//--- per GMT day per leg, only inside [open_min, trig_end). Direction is
//--- WITH the wick pierce: high above level -> LONG, low below -> SHORT.
bool SmDetectCont(const string symbol,const MqlRates &bar,const int gmt_min,
                  const int day_key,const int leg,const SmLegGeom &g,
                  SmDayState &st,SmSignal &out)
  {
   ZeroMemory(out);
   if(gmt_min<g.open_min || gmt_min>=g.trig_end)
      return(false);
   int slot=0;
   if(leg==SM_LEG_LDN)
      slot=1;
   else if(leg==SM_LEG_NY)
      slot=2;
   else
      return(false);
   if((slot==1 && st.ldn_day_key==day_key) ||
      (slot==2 && st.ny_day_key==day_key))
      return(false);                            // one entry per leg per GMT day
   double lh=0.0,ll=0.0;
   if(!SmSessionLevel(symbol,bar,gmt_min,g,lh,ll))
      return(false);
   if(bar.high>lh)
      { out.direction=LSW_DIR_LONG; }
   else if(bar.low<ll)
      { out.direction=LSW_DIR_SHORT; }
   else
      return(false);
   out.valid=true;
   out.leg=leg;
   out.level_high=lh;
   out.level_low=ll;
   out.ref_bar_time=bar.time;
   if(slot==1)
      st.ldn_day_key=day_key;
   else
      st.ny_day_key=day_key;
   return(true);
  }

//--- Time-exit minute for a leg, in GMT minutes past midnight.
int SmLegExitMin(const int leg,const SmParams &p)
  {
   if(leg==SM_LEG_LDN)
      return(p.ldn.exit_min);
   if(leg==SM_LEG_NY)
      return(p.ny.exit_min);
   return(-1);
  }

#endif
