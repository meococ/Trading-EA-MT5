//+------------------------------------------------------------------+
//| LSW_Session.mqh                                                  |
//| Decision clock, session windows, flatten windows, news blackout. |
//|                                                                  |
//| CLOCK DOCTRINE (CONTRACT.md §2):                                 |
//|  - Every input timestamp here is BROKER SERVER TIME (bar times). |
//|  - GMT is DERIVED: gmt = server - (offset + dst) * 3600.         |
//|  - TimeGMT() is never used for a decision; the EA prints the     |
//|    measured delta once as a diagnostic so the offset can be      |
//|    pinned from the journal.                                      |
//|  - Session windows use the derived GMT clock (liquidity is a GMT |
//|    phenomenon). Flatten and rollover use RAW SERVER time, because |
//|    unified_validation.py classifies overnight trades on server    |
//|    calendar dates.                                               |
//+------------------------------------------------------------------+
#ifndef LSW_SESSION_MQH
#define LSW_SESSION_MQH

#include "LSW_Types.mqh"

#define LSW_LONDON_OPEN_GMT   7
#define LSW_LONDON_CLOSE_GMT  16
#define LSW_NY_OPEN_GMT       12
#define LSW_NY_CLOSE_GMT      20
#define LSW_ASIA_START_GMT    0
#define LSW_ASIA_END_GMT      7

//--- Day-of-month of the n-th Sunday of a month (nth is 1-based).
int LswNthSundayDay(const int year,const int month,const int nth)
  {
   MqlDateTime t;
   ZeroMemory(t);
   t.year=year;
   t.mon=month;
   t.day=1;
   const datetime first=StructToTime(t);
   MqlDateTime probe;
   TimeToStruct(first,probe);
   // MqlDateTime.day_of_week: 0 = Sunday.
   const int first_sunday=1+((7-probe.day_of_week)%7);
   return(first_sunday+7*(nth-1));
  }

//--- US daylight saving: second Sunday of March 02:00 local -> first Sunday of
//--- November 02:00 local. Evaluated on the SERVER stamp, so the two switch days
//--- each year can be off by a few hours (declared in CONTRACT.md §12.3).
bool LswUsDstActive(const datetime stamp)
  {
   MqlDateTime t;
   TimeToStruct(stamp,t);
   if(t.mon<3 || t.mon>11)
      return(false);
   if(t.mon>3 && t.mon<11)
      return(true);
   if(t.mon==3)
     {
      const int start_day=LswNthSundayDay(t.year,3,2);
      if(t.day>start_day)
         return(true);
      if(t.day<start_day)
         return(false);
      return(t.hour>=7);      // 02:00 EST == 07:00 UTC
     }
   const int end_day=LswNthSundayDay(t.year,11,1);
   if(t.day<end_day)
      return(true);
   if(t.day>end_day)
      return(false);
   return(t.hour<6);          // 02:00 EDT == 06:00 UTC
  }

//--- Server -> GMT-equivalent. The only conversion in the package.
datetime LswServerToGmt(const datetime server_time,const LswConfig &cfg)
  {
   int offset=cfg.server_gmt_offset_hours;
   if(cfg.server_dst_us_rule && LswUsDstActive(server_time))
      offset++;
   return((datetime)((long)server_time-(long)offset*LSW_SEC_PER_HOUR));
  }

//--- Full clock snapshot for one closed-bar decision.
bool LswClockRead(const datetime server_time,const LswConfig &cfg,LswClock &out)
  {
   ZeroMemory(out);
   if(server_time<=0)
      return(false);

   out.server_time=server_time;
   out.gmt_time=LswServerToGmt(server_time,cfg);
   out.gmt_day_start=LswDayStart(out.gmt_time);

   MqlDateTime g,s;
   TimeToStruct(out.gmt_time,g);
   TimeToStruct(server_time,s);
   out.gmt_hour=g.hour;
   out.gmt_day_of_week=g.day_of_week;
   out.server_hour=s.hour;
   out.server_day_of_week=s.day_of_week;

   out.weekend=(s.day_of_week==0 || s.day_of_week==6);
   // Broker rollover: swap booking and the spread blowout around server midnight.
   out.rollover=(s.hour==23 || s.hour==0);
   out.friday_flatten=(s.day_of_week==5 && s.hour>=cfg.friday_flatten_hour_server);
   out.flatten=(out.weekend || out.friday_flatten ||
                s.hour>=cfg.flatten_hour_server);

   const bool london_enabled=(cfg.session_mode==LSW_SESS_LONDON_ONLY ||
                              cfg.session_mode==LSW_SESS_BOTH);
   const bool ny_enabled=(cfg.session_mode==LSW_SESS_NY_ONLY ||
                          cfg.session_mode==LSW_SESS_BOTH);
   out.in_london=(london_enabled && !out.weekend &&
                  g.hour>=LSW_LONDON_OPEN_GMT && g.hour<LSW_LONDON_CLOSE_GMT);
   out.in_newyork=(ny_enabled && !out.weekend &&
                   g.hour>=LSW_NY_OPEN_GMT && g.hour<LSW_NY_CLOSE_GMT);

   // Active session for the opening range: the most recently opened enabled
   // session that is currently live. Deterministic, documented in CONTRACT.md §4.
   out.session_open_gmt=0;
   if(out.in_london)
      out.session_open_gmt=out.gmt_day_start+LSW_LONDON_OPEN_GMT*LSW_SEC_PER_HOUR;
   if(out.in_newyork)
      out.session_open_gmt=out.gmt_day_start+LSW_NY_OPEN_GMT*LSW_SEC_PER_HOUR;

   out.entry_window=(!out.weekend && !out.rollover && !out.flatten &&
                     (out.in_london || out.in_newyork));
   out.valid=true;
   return(true);
  }

//--- True when a high-impact event for `ccy` falls inside [from,to].
//--- `queried` reports whether the calendar returned anything at all, so an
//--- empty calendar DB shows up as a counter instead of a silent pass.
bool LswCalendarHighImpact(const datetime from,const datetime to,const string ccy,
                           bool &queried)
  {
   if(from<=0 || to<=from || StringLen(ccy)<3)
      return(false);
   MqlCalendarValue values[];
   ResetLastError();
   const int n=CalendarValueHistory(values,from,to,NULL,ccy);
   if(n<=0)
      return(false);
   queried=true;
   for(int i=0;i<n;i++)
     {
      MqlCalendarEvent ev;
      if(!CalendarEventById(values[i].event_id,ev))
         continue;
      if(ev.importance==CALENDAR_IMPORTANCE_HIGH)
         return(true);
     }
   return(false);
  }

//--- Symmetric blackout around a high-impact release in either leg currency.
//--- FAILS OPEN by design (see CONTRACT.md §8): a tester with no calendar data
//--- must not block every trade. `query_empty` makes that visible.
bool LswNewsBlackout(const string symbol,const datetime server_now,
                     const int blackout_minutes,bool &query_empty)
  {
   query_empty=false;
   if(blackout_minutes<=0)
      return(false);
   const int pad=blackout_minutes*60;
   const datetime from=(datetime)((long)server_now-pad);
   const datetime to=(datetime)((long)server_now+pad);

   const string base=SymbolInfoString(symbol,SYMBOL_CURRENCY_BASE);
   const string profit=SymbolInfoString(symbol,SYMBOL_CURRENCY_PROFIT);

   bool queried=false;
   bool hit=LswCalendarHighImpact(from,to,base,queried);
   if(!hit && profit!=base)
      hit=LswCalendarHighImpact(from,to,profit,queried);
   query_empty=!queried;
   return(hit);
  }

#endif
