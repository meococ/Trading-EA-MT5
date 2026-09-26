//+------------------------------------------------------------------+
//|                                                   PA_Session.mqh |
//|  PA-PRO EA lane - session windows + entry vetoes + flat rules.   |
//|                                                                  |
//|  Exact port of the session/veto half of lib/pa_fill.py and the   |
//|  frozen session table of lib/pa_data.py:44-47.                   |
//|                                                                  |
//|  ENTRY VETO (pa_fill.py:196-215, on the SIGNAL bar OPEN time):   |
//|   - corrected mode (default):  dow >= 5  -> VETO_WEEKEND         |
//|                                dow == 4 && srv_h >= 20 -> VETO_FRIDAY |
//|   - legacy mode (tests only):  legacy_dow == 4 && srv_h >= 20    |
//|     -> VETO_FRIDAY  (the R00 bug: legacy_dow 4 is THURSDAY)      |
//|                                                                  |
//|  EXIT-SIDE FLATS (pa_fill.py:297-314, per M1 bar, checked AFTER  |
//|  SL/TP): msrv >= 22 -> DAILY; corrected dow==4 && msrv>=20 ->    |
//|  FRIDAY; weekend_veto && dow>=5 -> WEEKEND; day change ->        |
//|  MIDNIGHT at previous close; else DATA_END.                      |
//|                                                                  |
//|  SESSION WINDOWS (UTC minutes-of-day, pa_data.SESSIONS):         |
//|    eu = [300, 660)   us = [690, 1050)                            |
//|                                                                  |
//|  No order, position or trade call exists in this header.         |
//+------------------------------------------------------------------+
#ifndef PA_SESSION_MQH
#define PA_SESSION_MQH

#include "PA_Types.mqh"
#include "PA_Clock.mqh"

//--- veto / exit reason codes (CSV-friendly, match pa_fill statuses)
enum ENUM_PA_VETO
  {
   PA_VETO_NONE = 0,
   PA_VETO_FRIDAY,
   PA_VETO_WEEKEND,
   PA_VETO_SESSION,          // out of all enabled session windows
   PA_VETO_WARMUP            // signal bar < first live bar
  };

enum ENUM_PA_FLAT
  {
   PA_FLAT_NONE = 0,
   PA_FLAT_DAILY,            // "DAILY"
   PA_FLAT_FRIDAY,           // "FRIDAY"
   PA_FLAT_WEEKEND,          // "WEEKEND"
   PA_FLAT_MIDNIGHT          // "MIDNIGHT"
  };

string PaVetoName(const int v)
  {
   switch(v)
     {
      case PA_VETO_NONE:    return("NONE");
      case PA_VETO_FRIDAY:  return("VETO_FRIDAY");
      case PA_VETO_WEEKEND: return("VETO_WEEKEND");
      case PA_VETO_SESSION: return("VETO_SESSION");
      case PA_VETO_WARMUP:  return("VETO_WARMUP");
     }
   return("?");
  }

string PaFlatName(const int f)
  {
   switch(f)
     {
      case PA_FLAT_NONE:     return("NONE");
      case PA_FLAT_DAILY:    return("DAILY");
      case PA_FLAT_FRIDAY:   return("FRIDAY");
      case PA_FLAT_WEEKEND:  return("WEEKEND");
      case PA_FLAT_MIDNIGHT: return("MIDNIGHT");
     }
   return("?");
  }

//+------------------------------------------------------------------+
//| CPaSession - all session/veto policy knobs in one place.         |
//+------------------------------------------------------------------+
class CPaSession
  {
public:
   //--- session windows, UTC minutes-of-day [lo,hi); pa_data.SESSIONS
   int               eu_lo;
   int               eu_hi;
   int               us_lo;
   int               us_hi;
   bool              eu_on;
   bool              us_on;
   //--- flats (pa_fill DEFAULT_SPEC)
   bool              flats;
   bool              legacy_flats;   // NEVER true in production (R00 bug)
   int               daily_flat_hour;
   int               friday_flat_hour;
   bool              weekend_veto;

                     CPaSession(void)
     {
      eu_lo=300; eu_hi=660;          // 05:00-11:00 UTC
      us_lo=690; us_hi=1050;         // 11:30-17:30 UTC
      eu_on=true; us_on=true;
      flats=true;
      legacy_flats=false;
      daily_flat_hour=PA_DAILY_FLAT_HOUR;    // 22 server
      friday_flat_hour=PA_FRIDAY_FLAT_HOUR;  // 20 server
      weekend_veto=true;
     }

   //--- in-session check on a bar-close UTC minute (pa_data.session_mask)
   bool InSessionUtcMin(const int utc_min) const
     {
      if(eu_on && utc_min>=eu_lo && utc_min<eu_hi)
         return(true);
      if(us_on && utc_min>=us_lo && utc_min<us_hi)
         return(true);
      return(false);
     }

   //--- entry veto for a signal bar, pa_fill.py:196-215.
   //--- bar_open_t = M5 bar OPEN server epoch (the signal bar's t).
   int EntryVeto(const long bar_open_t) const
     {
      if(!flats)
         return(PA_VETO_NONE);
      int srv_h=(int)((bar_open_t%PA_DAY_SEC)/3600);
      if(legacy_flats)
        {
         if(PaLegacyServerDow(bar_open_t)==4 && srv_h>=friday_flat_hour)
            return(PA_VETO_FRIDAY);
         return(PA_VETO_NONE);
        }
      int dow=PaServerDow(bar_open_t);
      if(dow>=5 && weekend_veto)
         return(PA_VETO_WEEKEND);
      if(dow==4 && srv_h>=friday_flat_hour)
         return(PA_VETO_FRIDAY);
      return(PA_VETO_NONE);
     }

   //--- exit-side flat check for an M1 bar INSIDE a trade, pa_fill.py:297-311.
   //--- m1_t = M1 bar open epoch; fday = server day of the FILL bar.
   //--- Returns the flat reason or PA_FLAT_NONE (caller still checks
   //--- SL/TP first, then this, then midnight).
   int FlatHit(const long m1_t,const long fday) const
     {
      if(!flats)
         return(PA_FLAT_NONE);
      int msrv=(int)((m1_t%PA_DAY_SEC)/3600);
      if(msrv>=daily_flat_hour)
         return(PA_FLAT_DAILY);
      if(legacy_flats)
        {
         if(PaLegacyServerDow(m1_t)==4 && msrv>=friday_flat_hour)
            return(PA_FLAT_FRIDAY);
        }
      else
        {
         int dow=PaServerDow(m1_t);
         if(dow==4 && msrv>=friday_flat_hour)
            return(PA_FLAT_FRIDAY);
         if(weekend_veto && dow>=5)
            return(PA_FLAT_WEEKEND);
        }
      return(PA_FLAT_NONE);
     }

   //--- midnight fallback: the fill-day boundary changed (pa_fill.py:312)
   bool MidnightHit(const long m1_t,const long fday) const
     {
      return((m1_t/PA_DAY_SEC)!=fday);
     }
  };

#endif // PA_SESSION_MQH
