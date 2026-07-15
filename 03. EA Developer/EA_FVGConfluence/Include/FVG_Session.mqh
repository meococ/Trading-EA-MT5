//+------------------------------------------------------------------+
//| FVG_Session.mqh — London / NY session + news stub                  |
//+------------------------------------------------------------------+
#ifndef FVG_SESSION_MQH
#define FVG_SESSION_MQH

// Broker-server time with optional hour/minute offsets.
datetime FVG_BrokerNow()
{
   return TimeTradeServer();
}

int FVG_HourOf(const datetime t)
{
   MqlDateTime dt;
   TimeToStruct(t, dt);
   return dt.hour;
}

int FVG_MinuteOf(const datetime t)
{
   MqlDateTime dt;
   TimeToStruct(t, dt);
   return dt.min;
}

int FVG_DayOfYear(const datetime t)
{
   MqlDateTime dt;
   TimeToStruct(t, dt);
   return dt.day_of_year + dt.year * 1000;
}

int FVG_MinutesOfDay(const datetime t, const int hour_offset, const int minute_offset)
{
   int total = FVG_HourOf(t) * 60 + FVG_MinuteOf(t) + hour_offset * 60 + minute_offset;
   // wrap into [0, 1440)
   while(total < 0)
      total += 1440;
   while(total >= 1440)
      total -= 1440;
   return total;
}

bool FVG_InWindow(const int now_min,
                  const int start_h, const int start_m,
                  const int end_h, const int end_m)
{
   int a = start_h * 60 + start_m;
   int b = end_h * 60 + end_m;
   if(a == b)
      return false;
   if(a < b)
      return (now_min >= a && now_min < b);
   // wraps midnight
   return (now_min >= a || now_min < b);
}

bool FVG_InLondonOrNY(const int hour_offset,
                      const int minute_offset,
                      const bool use_london,
                      const int lon_sh, const int lon_sm,
                      const int lon_eh, const int lon_em,
                      const bool use_ny,
                      const int ny_sh, const int ny_sm,
                      const int ny_eh, const int ny_em)
{
   datetime now = FVG_BrokerNow();
   int m = FVG_MinutesOfDay(now, hour_offset, minute_offset);
   bool ok = false;
   if(use_london && FVG_InWindow(m, lon_sh, lon_sm, lon_eh, lon_em))
      ok = true;
   if(use_ny && FVG_InWindow(m, ny_sh, ny_sm, ny_eh, ny_em))
      ok = true;
   return ok;
}

// News filter STUB: disabled by default. Optional fixed block windows
// as "HH:MM-HH:MM;HH:MM-HH:MM" in broker-offset minutes-of-day.
bool FVG_ParseHM(const string token, int &h, int &m)
{
   h = 0;
   m = 0;
   string parts[];
   int n = StringSplit(token, ':', parts);
   if(n < 2)
      return false;
   h = (int)StringToInteger(parts[0]);
   m = (int)StringToInteger(parts[1]);
   return true;
}

bool FVG_InNewsBlockWindow(const string windows,
                           const int hour_offset,
                           const int minute_offset)
{
   if(StringLen(windows) == 0)
      return false;
   datetime now = FVG_BrokerNow();
   int cur = FVG_MinutesOfDay(now, hour_offset, minute_offset);

   string segs[];
   int n = StringSplit(windows, ';', segs);
   for(int i = 0; i < n; i++)
   {
      string seg = segs[i];
      StringTrimLeft(seg);
      StringTrimRight(seg);
      if(StringLen(seg) == 0)
         continue;
      string hm[];
      if(StringSplit(seg, '-', hm) < 2)
         continue;
      int sh, sm, eh, em;
      if(!FVG_ParseHM(hm[0], sh, sm))
         continue;
      if(!FVG_ParseHM(hm[1], eh, em))
         continue;
      if(FVG_InWindow(cur, sh, sm, eh, em))
         return true;
   }
   return false;
}

// InpUseNewsFilter=false by default — no calendar feed wired.
// When true, only optional manual block windows apply (stub).
bool FVG_NewsBlocksEntry(const bool use_news_filter,
                         const string block_windows,
                         const int hour_offset,
                         const int minute_offset)
{
   if(!use_news_filter)
      return false;
   // STUB: no economic calendar integration. Manual windows only.
   return FVG_InNewsBlockWindow(block_windows, hour_offset, minute_offset);
}

#endif
