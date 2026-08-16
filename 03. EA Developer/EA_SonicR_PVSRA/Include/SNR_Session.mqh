#ifndef SNR_SESSION_MQH
#define SNR_SESSION_MQH

#include "SNR_Types.mqh"

int SnrLastSundayOfMonth(const int year,const int month)
  {
   MqlDateTime next;
   ZeroMemory(next);
   next.year=year;
   next.mon=month+1;
   next.day=1;
   if(next.mon>12)
     {
      next.mon=1;
      next.year++;
     }
   datetime last_dt=StructToTime(next)-86400;
   MqlDateTime last;
   TimeToStruct(last_dt,last);
   return(last.day-last.day_of_week);
  }

bool SnrUkDstActive(const datetime gmt)
  {
   MqlDateTime t;
   TimeToStruct(gmt,t);
   if(t.mon<3 || t.mon>10)
      return(false);
   if(t.mon>3 && t.mon<10)
      return(true);
   const int last_sun=SnrLastSundayOfMonth(t.year,t.mon);
   if(t.mon==3)
     {
      if(t.day>last_sun)
         return(true);
      if(t.day<last_sun)
         return(false);
      return(t.hour>=1);
     }
   if(t.day<last_sun)
      return(true);
   if(t.day>last_sun)
      return(false);
   return(t.hour<1);
  }

void SnrGmtToLondon(const datetime gmt,MqlDateTime &london)
  {
   const datetime shifted=gmt+(SnrUkDstActive(gmt) ? 3600 : 0);
   TimeToStruct(shifted,london);
  }

bool SnrSessionRead(const datetime gmt,const SnrClassicCfg &cfg,SnrSessionSnap &out)
  {
   ZeroMemory(out);
   if(gmt<=0)
      return(false);
   MqlDateTime london;
   SnrGmtToLondon(gmt,london);
   out.valid=true;
   out.uk_dst=SnrUkDstActive(gmt);
   out.london_hour=london.hour;
   out.london_dow=london.day_of_week;
   const bool weekend=(london.day_of_week==0 || london.day_of_week==6);
   const bool friday_late=(london.day_of_week==5 && london.hour>=cfg.friday_flatten_hour);
   out.flatten=(weekend || friday_late);
   const bool in_london=(!weekend && SnrHourInRange(london.hour,cfg.london_start_hour,cfg.london_end_hour)==1);
   const bool in_ny=(cfg.use_ny_session && !weekend &&
                     SnrHourInRange(london.hour,cfg.ny_start_hour,cfg.ny_end_hour)==1);
   if(in_london)
      out.zone=SNR_SESS_LONDON;
   else if(in_ny)
      out.zone=SNR_SESS_NY;
   else
      out.zone=SNR_SESS_NONE;
   out.entry_allowed=(!out.flatten && !friday_late && out.zone!=SNR_SESS_NONE);
   return(true);
  }

#endif
