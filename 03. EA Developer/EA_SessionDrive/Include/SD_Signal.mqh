//+------------------------------------------------------------------+
//| SD_Signal.mqh                                                    |
//| Session opening-drive continuation signal (closed-bar ORB).      |
//|                                                                  |
//| MECHANISM (frozen in research/CONTRACT.md):                      |
//|  - Three GMT sessions per day: Asia 00-07, London 07-16,         |
//|    New York 12-20. The first or_bars closed M5 bars of each      |
//|    session form its opening range.                               |
//|  - OR valid iff or_range in [or_min_atr, or_max_atr] x ATR14.    |
//|    OR bars must be exactly contiguous; a gap kills the session.  |
//|  - First closed M5 bar after the OR whose CLOSE is beyond an OR  |
//|    extreme fires one continuation entry (close>ORH: LONG,        |
//|    close<ORL: SHORT). Margin is zero: the canonical ORB trigger. |
//|  - Break window: [OR end, OR end + break_bars], always inside    |
//|    the session window. One entry per session, 3 sessions/day.    |
//|  - SL anchor: OR midpoint (drive failure), padded by ATR.        |
//|                                                                  |
//| Every decision reads only CLOSED bars (shift>=1). The forming    |
//| bar's prices are never consumed.                                 |
//+------------------------------------------------------------------+
#ifndef SD_SIGNAL_MQH
#define SD_SIGNAL_MQH

#include "SD_Types.mqh"
#include "../../EA_LiquiditySweep/Include/LSW_Types.mqh"

//--- Session open/close GMT hours for a session id.
void SdSessionHours(const int sess,int &open_gmt,int &close_gmt)
  {
   switch(sess)
     {
      case SD_SESS_ASIA: open_gmt=SD_ASIA_OPEN_GMT; close_gmt=SD_ASIA_CLOSE_GMT; return;
      case SD_SESS_LDN:  open_gmt=SD_LDN_OPEN_GMT;  close_gmt=SD_LDN_CLOSE_GMT;  return;
      case SD_SESS_NY:   open_gmt=SD_NY_OPEN_GMT;   close_gmt=SD_NY_CLOSE_GMT;   return;
      default: break;
     }
   open_gmt=-1; close_gmt=-1;
  }

//--- Feed one closed bar into one session FSM. On a break, `drive` is filled
//--- and true is returned; the caller then runs the shared filter/plan path.
//--- bar_gmt is the CLOSED bar's open time on the GMT clock; gmt_min is its
//--- minute-of-day. atr is the M5 ATR14 at this bar.
bool SdSessionFeed(const int sess,SdSession &s,const MqlRates &bar,
                   const datetime bar_gmt,const int gmt_min,
                   const double atr,const SdParams &p,
                   LswCounters &cnt,SdDrive &drive)
  {
   ZeroMemory(drive);
   drive.session=sess;
   drive.bar_time=bar.time;

   int open_gmt,close_gmt;
   SdSessionHours(sess,open_gmt,close_gmt);
   const int open_min=open_gmt*60;
   const int close_min=close_gmt*60;
   const int or_span=p.or_bars*5;                      // minutes
   const int break_end=open_min+or_span+p.break_bars*5;

   const int day_key=(int)((long)bar_gmt/LSW_SEC_PER_DAY);
   if(s.day_key!=day_key)
     {
      ZeroMemory(s);
      s.day_key=day_key;
     }
   if(gmt_min<open_min || gmt_min>=close_min)
      return(false);                                  // outside this session entirely
   s.seen=true;
   if(s.dead || s.traded)
      return(false);

   //--- Phase 1: opening-range formation. Bars must be exactly contiguous.
   if(gmt_min>=open_min && gmt_min<open_min+or_span)
     {
      if(s.or_count>0 &&
         (long)bar.time-(long)s.last_bar!=LSW_SEC_PER_M5)
        {
         s.dead=true;
         cnt.geom_bad_approach++;                     // OR window bar gap
         return(false);
        }
      s.last_bar=bar.time;
      if(s.or_count==0)
        {
         s.orh=bar.high;
         s.orl=bar.low;
        }
      else
        {
         s.orh=MathMax(s.orh,bar.high);
         s.orl=MathMin(s.orl,bar.low);
        }
      s.or_count++;
      if(s.or_count==p.or_bars)
        {
         const double rng=s.orh-s.orl;
         if(!LswFinite(atr) || atr<=0.0)
           {
            s.dead=true;
            cnt.geom_no_level++;                      // ATR unreadable at OR end
            return(false);
           }
         if(rng<p.or_min_atr*atr)
           {
            s.dead=true;
            cnt.geom_pen_small++;                     // OR below floor: no drive
            return(false);
           }
         if(rng>p.or_max_atr*atr)
           {
            s.dead=true;
            cnt.geom_pen_large++;                     // OR too wide: drive spent
            return(false);
           }
         s.armed=true;
        }
      return(false);
     }

   //--- Phase 2: break window. Only armed sessions can fire.
   if(gmt_min>=open_min+or_span && gmt_min<break_end)
     {
      if(!s.armed)
         return(false);                               // forming incomplete or dead
      if(!LswFinite(atr) || atr<=0.0)
        {
         cnt.data_fail++;
         return(false);
        }
      if(bar.close>s.orh)
        {
         s.traded=true;
         s.armed=false;
         drive.valid=true;
         drive.direction=LSW_DIR_LONG;
         drive.orh=s.orh;
         drive.orl=s.orl;
         drive.or_mid=(s.orh+s.orl)*0.5;
         drive.atr=atr;
         drive.close_price=bar.close;
         return(true);
        }
      if(bar.close<s.orl)
        {
         s.traded=true;
         s.armed=false;
         drive.valid=true;
         drive.direction=LSW_DIR_SHORT;
         drive.orh=s.orh;
         drive.orl=s.orl;
         drive.or_mid=(s.orh+s.orl)*0.5;
         drive.atr=atr;
         drive.close_price=bar.close;
         return(true);
        }
      return(false);                                  // armed, still inside range
     }

   //--- Break window exhausted without a fill.
   if(s.armed && gmt_min>=break_end)
     {
      s.armed=false;
      cnt.geom_no_close_back++;                       // armed but never broke
     }
   return(false);
  }

//--- Feed one closed bar through the enabled session FSMs. Returns the first
//--- drive found; at most one session can break on a single bar in practice
//--- (LDN and NY both armed during overlap is possible, so sessions are
//--- checked in open order: ASIA, LDN, NY).
bool SdDetectDrive(SdSession &sessions[],const MqlRates &bar,
                   const datetime bar_gmt,const int gmt_min,
                   const double atr,const SdParams &p,
                   LswCounters &cnt,SdDrive &drive)
  {
   if(p.use_asia &&
      SdSessionFeed(SD_SESS_ASIA,sessions[SD_SESS_ASIA],bar,bar_gmt,gmt_min,
                    atr,p,cnt,drive))
      return(true);
   if(p.use_london &&
      SdSessionFeed(SD_SESS_LDN,sessions[SD_SESS_LDN],bar,bar_gmt,gmt_min,
                    atr,p,cnt,drive))
      return(true);
   if(p.use_newyork &&
      SdSessionFeed(SD_SESS_NY,sessions[SD_SESS_NY],bar,bar_gmt,gmt_min,
                    atr,p,cnt,drive))
      return(true);
   return(false);
  }

//--- Adapt the drive signal into the shared LswSweep wire type so the proven
//--- LswBuildPlan sizing/geometry path is reused unchanged. The plan builder
//--- treats `extreme` as the structural stop anchor: here that is the OR
//--- midpoint (a break retracing through mid-OR means the drive failed).
void SdDriveToSweep(const SdDrive &drive,LswSweep &sweep)
  {
   ZeroMemory(sweep);
   sweep.valid=drive.valid;
   sweep.direction=drive.direction;
   sweep.family=LSW_FAM_OPEN_RANGE;
   sweep.level=drive.or_mid;
   sweep.extreme=drive.or_mid;
   sweep.close_price=drive.close_price;
   sweep.penetration=0.0;
   sweep.atr=drive.atr;
   sweep.bar_time=drive.bar_time;
  }

#endif
