#ifndef SNR_NEWS_MQH
#define SNR_NEWS_MQH

#define SNR_NEWS_PAD_SEC 2700

bool SnrNewsCcyHighImpact(const datetime from_gmt,const datetime to_gmt,const string ccy)
  {
   if(from_gmt<=0 || to_gmt<=from_gmt || StringLen(ccy)<3)
      return(false);
   MqlCalendarValue values[];
   ResetLastError();
   const int n=CalendarValueHistory(values,from_gmt,to_gmt,NULL,ccy);
   if(n<=0)
      return(false);
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

bool SnrNewsUsdHighImpact(const datetime from_gmt,const datetime to_gmt)
  {
   return(SnrNewsCcyHighImpact(from_gmt,to_gmt,"USD"));
  }

bool SnrNewsUsdJpyHighImpact(const datetime from_gmt,const datetime to_gmt)
  {
   return(SnrNewsCcyHighImpact(from_gmt,to_gmt,"USD") ||
          SnrNewsCcyHighImpact(from_gmt,to_gmt,"JPY"));
  }

bool SnrNewsEurUsdHighImpact(const datetime from_gmt,const datetime to_gmt)
  {
   return(SnrNewsCcyHighImpact(from_gmt,to_gmt,"EUR") ||
          SnrNewsCcyHighImpact(from_gmt,to_gmt,"USD"));
  }

bool SnrNewsGbpUsdHighImpact(const datetime from_gmt,const datetime to_gmt)
  {
   return(SnrNewsCcyHighImpact(from_gmt,to_gmt,"GBP") ||
          SnrNewsCcyHighImpact(from_gmt,to_gmt,"USD"));
  }

bool SnrNewsAudUsdHighImpact(const datetime from_gmt,const datetime to_gmt)
  {
   return(SnrNewsCcyHighImpact(from_gmt,to_gmt,"AUD") ||
          SnrNewsCcyHighImpact(from_gmt,to_gmt,"USD"));
  }

bool SnrNewsNzdUsdHighImpact(const datetime from_gmt,const datetime to_gmt)
  {
   return(SnrNewsCcyHighImpact(from_gmt,to_gmt,"NZD") ||
          SnrNewsCcyHighImpact(from_gmt,to_gmt,"USD"));
  }

bool SnrNewsUsdChfHighImpact(const datetime from_gmt,const datetime to_gmt)
  {
   return(SnrNewsCcyHighImpact(from_gmt,to_gmt,"USD") ||
          SnrNewsCcyHighImpact(from_gmt,to_gmt,"CHF"));
  }

bool SnrNewsUsdCadHighImpact(const datetime from_gmt,const datetime to_gmt)
  {
   return(SnrNewsCcyHighImpact(from_gmt,to_gmt,"USD") ||
          SnrNewsCcyHighImpact(from_gmt,to_gmt,"CAD"));
  }

#endif
