#ifndef SNR_TIME_COMPLIANCE_MQH
#define SNR_TIME_COMPLIANCE_MQH

SnrNewsEvent    g_snrNewsEvents[];
int             g_snrNewsCount = 0;
SnrCalendarMeta g_snrCalendarMeta;

string SNR_Trim(string value)
{
   StringTrimLeft(value);
   StringTrimRight(value);
   return value;
}

string SNR_ToUpper(string value)
{
   StringToUpper(value);
   return value;
}

string SNR_CleanTesterString(string value)
{
   value = SNR_Trim(value);
   int pos = StringFind(value, "||");
   if(pos >= 0)
      value = StringSubstr(value, 0, pos);
   return SNR_Trim(value);
}

datetime SNR_LastSundayServer(const int year, const int month, const int hour_local)
{
   MqlDateTime dt;
   dt.year = year;
   dt.mon  = month;
   dt.day  = 31;
   dt.hour = hour_local;
   dt.min  = 0;
   dt.sec  = 0;
   datetime t = StructToTime(dt);
   if(t <= 0)
      return 0;

   MqlDateTime cur;
   TimeToStruct(t, cur);
   while(cur.mon == month && cur.day_of_week != 0)
   {
      t -= 86400;
      TimeToStruct(t, cur);
   }
   return t;
}

int SNR_ServerUtcOffsetHours(const datetime server_time)
{
   if(g_timeProfileMode == 0)
      return g_fixedUtcOffsetHours;

   MqlDateTime dt;
   TimeToStruct(server_time, dt);
   datetime dst_start = SNR_LastSundayServer(dt.year, 3, 3);
   datetime dst_end   = SNR_LastSundayServer(dt.year, 10, 4);
   if(dst_start > 0 && dst_end > 0 && server_time >= dst_start && server_time < dst_end)
      return 3;
   return 2;
}

datetime SNR_ServerToUTC(const datetime server_time)
{
   return server_time - (datetime)(SNR_ServerUtcOffsetHours(server_time) * 3600);
}

datetime SNR_UTCToServer(const datetime utc_time)
{
   if(g_timeProfileMode == 0)
      return utc_time + (datetime)(g_fixedUtcOffsetHours * 3600);

   datetime probe = utc_time + 2 * 3600;
   int offset = SNR_ServerUtcOffsetHours(probe);
   return utc_time + (datetime)(offset * 3600);
}

int SNR_MinutesOfDay(const int hour, const int minute)
{
   return hour * 60 + minute;
}

int SNR_ServerMinutesOfDay(const datetime server_time)
{
   MqlDateTime dt;
   TimeToStruct(server_time, dt);
   return SNR_MinutesOfDay(dt.hour, dt.min);
}

bool SNR_TimeInWindow(const datetime server_time,
                      const int start_hour,
                      const int start_minute,
                      const int end_hour,
                      const int end_minute)
{
   int cur = SNR_ServerMinutesOfDay(server_time);
   int from_val = SNR_MinutesOfDay(start_hour, start_minute);
   int to_val   = SNR_MinutesOfDay(end_hour, end_minute);
   if(from_val == to_val)
      return false;
   if(from_val < to_val)
      return (cur >= from_val && cur < to_val);
   return (cur >= from_val || cur < to_val);
}

int SNR_MinutesUntilClock(const datetime server_time, const int hour, const int minute)
{
   int cur = SNR_ServerMinutesOfDay(server_time);
   int dst = SNR_MinutesOfDay(hour, minute);
   int diff = dst - cur;
   if(diff < 0)
      diff += 1440;
   return diff;
}

string SNR_FormatDateTime(const datetime t)
{
   if(t <= 0)
      return "";
   return TimeToString(t, TIME_DATE | TIME_MINUTES | TIME_SECONDS);
}

string SNR_BuildEventClass(const string title)
{
   string upper = SNR_ToUpper(title);
   if(StringFind(upper, "NONFARM") >= 0 || StringFind(upper, "PAYROLL") >= 0)
      return "NFP";
   if(StringFind(upper, "CPI") >= 0)
      return "CPI";
   if(StringFind(upper, "FOMC") >= 0)
      return "FOMC";
   if(StringFind(upper, "RATE") >= 0)
      return "RATE";
   if(StringFind(upper, "GDP") >= 0)
      return "GDP";
   if(StringFind(upper, "PCE") >= 0)
      return "PCE";
   if(StringFind(upper, "PMI") >= 0)
      return "PMI";
   return "NEWS";
}

string SNR_MakeEventId(const datetime utc_time, const string currency, const string title)
{
   string slug = SNR_ToUpper(title);
   StringReplace(slug, " ", "_");
   StringReplace(slug, ".", "");
   StringReplace(slug, ",", "");
   StringReplace(slug, "/", "_");
   StringReplace(slug, "-", "_");
   MqlDateTime dt;
   TimeToStruct(utc_time, dt);
   return StringFormat("%s_%04d%02d%02d_%02d%02d_%s",
                       SNR_ToUpper(currency),
                       dt.year, dt.mon, dt.day,
                       dt.hour, dt.min,
                       slug);
}

string SNR_ComputeCalendarHash()
{
   ulong hash = 2166136261;
   for(int i = 0; i < g_snrNewsCount; i++)
   {
      string row = g_snrNewsEvents[i].event_id + "|" +
                   IntegerToString((int)g_snrNewsEvents[i].utc_time) + "|" +
                   g_snrNewsEvents[i].event_class + "|" +
                   g_snrNewsEvents[i].currency + "|" +
                   g_snrNewsEvents[i].title;
      for(int j = 0; j < StringLen(row); j++)
      {
         hash ^= (ulong)StringGetCharacter(row, j);
         hash *= 16777619;
      }
   }
   return StringFormat("%I64u", hash);
}

string SNR_CleanSymbolCore(const string symbol)
{
   string cleaned = "";
   for(int i = 0; i < StringLen(symbol); i++)
   {
      int ch = StringGetCharacter(symbol, i);
      if((ch >= 'A' && ch <= 'Z') || (ch >= 'a' && ch <= 'z'))
         cleaned += CharToString((uchar)ch);
      if(StringLen(cleaned) >= 6)
         break;
   }
   return SNR_ToUpper(cleaned);
}

void SNR_DetectSymbolCurrencies(string &base_currency, string &quote_currency)
{
   string core = SNR_CleanSymbolCore(_Symbol);
   if(StringLen(core) >= 6)
   {
      base_currency  = StringSubstr(core, 0, 3);
      quote_currency = StringSubstr(core, 3, 3);
      return;
   }

   base_currency  = "";
   quote_currency = "USD";
}

bool SNR_IsCurrencyRelevant(const string base_currency,
                            const string quote_currency,
                            const string event_currency)
{
   string evt = SNR_ToUpper(event_currency);
   return (evt == base_currency || evt == quote_currency);
}

void SNR_ResetCalendarMeta()
{
   g_snrCalendarMeta.loaded = false;
   g_snrCalendarMeta.used_legacy_fallback = false;
   g_snrCalendarMeta.snapshot_id = "";
   g_snrCalendarMeta.snapshot_hash = "";
   g_snrCalendarMeta.snapshot_coverage_from = "";
   g_snrCalendarMeta.snapshot_coverage_to = "";
   g_snrCalendarMeta.included_event_classes = "";
   g_snrCalendarMeta.source_provenance = "";
   g_snrCalendarMeta.source_file = "";
   g_snrCalendarMeta.total_events = 0;
}

bool SNR_ParseContractCalendar(const string file_name)
{
   int handle = FileOpen(file_name, FILE_COMMON | FILE_READ | FILE_TXT | FILE_ANSI);
   if(handle == INVALID_HANDLE)
      return false;

   ArrayResize(g_snrNewsEvents, 0);
   g_snrNewsCount = 0;
   SNR_ResetCalendarMeta();
   g_snrCalendarMeta.source_file = file_name;

   while(!FileIsEnding(handle))
   {
      string line = SNR_Trim(FileReadString(handle));
      if(line == "")
         continue;

      if(StringSubstr(line, 0, 1) == "#")
      {
         int pos = StringFind(line, "=");
         if(pos > 1)
         {
            string key = SNR_Trim(StringSubstr(line, 1, pos - 1));
            string val = SNR_Trim(StringSubstr(line, pos + 1));
            if(key == "snapshot_id")             g_snrCalendarMeta.snapshot_id = val;
            if(key == "snapshot_hash")           g_snrCalendarMeta.snapshot_hash = val;
            if(key == "snapshot_coverage_from")  g_snrCalendarMeta.snapshot_coverage_from = val;
            if(key == "snapshot_coverage_to")    g_snrCalendarMeta.snapshot_coverage_to = val;
            if(key == "included_event_classes")  g_snrCalendarMeta.included_event_classes = val;
            if(key == "source_provenance")       g_snrCalendarMeta.source_provenance = val;
         }
         continue;
      }

      if(StringFind(line, "event_id,utc_time,event_class,currency,title") == 0)
         continue;

      string parts[];
      int count = StringSplit(line, ',', parts);
      if(count < 5)
         continue;

      int idx = g_snrNewsCount;
      g_snrNewsCount++;
      ArrayResize(g_snrNewsEvents, g_snrNewsCount);
      g_snrNewsEvents[idx].event_id    = SNR_Trim(parts[0]);
      g_snrNewsEvents[idx].utc_time    = StringToTime(SNR_Trim(parts[1]));
      g_snrNewsEvents[idx].event_class = SNR_ToUpper(SNR_Trim(parts[2]));
      g_snrNewsEvents[idx].currency    = SNR_ToUpper(SNR_Trim(parts[3]));
      g_snrNewsEvents[idx].title       = SNR_Trim(parts[4]);
   }
   FileClose(handle);

   g_snrCalendarMeta.loaded = (g_snrNewsCount > 0);
   g_snrCalendarMeta.total_events = g_snrNewsCount;
   if(g_snrCalendarMeta.snapshot_hash == "")
      g_snrCalendarMeta.snapshot_hash = SNR_ComputeCalendarHash();
   if(g_snrCalendarMeta.snapshot_id == "")
      g_snrCalendarMeta.snapshot_id = "SNR_CONTRACT_AUTO";
   if(g_snrCalendarMeta.source_provenance == "")
      g_snrCalendarMeta.source_provenance = "contract_snapshot";
   return g_snrCalendarMeta.loaded;
}

bool SNR_ParseLegacyCalendar(const string file_name)
{
   int handle = FileOpen(file_name, FILE_COMMON | FILE_READ | FILE_TXT | FILE_ANSI);
   if(handle == INVALID_HANDLE)
      return false;

   ArrayResize(g_snrNewsEvents, 0);
   g_snrNewsCount = 0;
   SNR_ResetCalendarMeta();
   g_snrCalendarMeta.source_file = file_name;
   g_snrCalendarMeta.used_legacy_fallback = true;
   g_snrCalendarMeta.source_provenance = "legacy_news_events_csv";
   g_snrCalendarMeta.snapshot_id = "LEGACY_NEWS_EVENTS_AUTO";

   datetime coverage_from = 0;
   datetime coverage_to   = 0;

   while(!FileIsEnding(handle))
   {
      string line = SNR_Trim(FileReadString(handle));
      if(line == "" || StringFind(line, "date,time_utc,event_type,currency,importance") == 0)
         continue;

      string parts[];
      int count = StringSplit(line, ',', parts);
      if(count < 5)
         continue;

      int importance = (int)StringToInteger(SNR_Trim(parts[4]));
      if(importance < g_legacyCalendarMinImportance)
         continue;

      string time_text = SNR_Trim(parts[1]);
      string title     = SNR_Trim(parts[2]);
      string currency  = SNR_ToUpper(SNR_Trim(parts[3]));
      datetime utc_time = StringToTime(SNR_Trim(parts[0]) + " " + time_text + ":00");
      if(utc_time <= 0)
         utc_time = StringToTime(SNR_Trim(parts[0]) + " " + time_text);
      if(utc_time <= 0)
         continue;

      int idx = g_snrNewsCount;
      g_snrNewsCount++;
      ArrayResize(g_snrNewsEvents, g_snrNewsCount);
      g_snrNewsEvents[idx].event_id    = SNR_MakeEventId(utc_time, currency, title);
      g_snrNewsEvents[idx].utc_time    = utc_time;
      g_snrNewsEvents[idx].event_class = SNR_BuildEventClass(title);
      g_snrNewsEvents[idx].currency    = currency;
      g_snrNewsEvents[idx].title       = title;

      if(coverage_from == 0 || utc_time < coverage_from)
         coverage_from = utc_time;
      if(coverage_to == 0 || utc_time > coverage_to)
         coverage_to = utc_time;
   }
   FileClose(handle);

   g_snrCalendarMeta.loaded = (g_snrNewsCount > 0);
   g_snrCalendarMeta.total_events = g_snrNewsCount;
   g_snrCalendarMeta.snapshot_hash = SNR_ComputeCalendarHash();
   g_snrCalendarMeta.snapshot_coverage_from = SNR_FormatDateTime(coverage_from);
   g_snrCalendarMeta.snapshot_coverage_to   = SNR_FormatDateTime(coverage_to);
   g_snrCalendarMeta.included_event_classes = StringFormat("legacy_importance_%d_plus", g_legacyCalendarMinImportance);
   return g_snrCalendarMeta.loaded;
}

bool SNR_LoadCalendar(const string requested_file)
{
   string clean_file = SNR_CleanTesterString(requested_file);
   ArrayResize(g_snrNewsEvents, 0);
   g_snrNewsCount = 0;
   SNR_ResetCalendarMeta();

   if(!g_useNewsFilter)
      return false;

   if(SNR_ParseContractCalendar(clean_file))
      return true;

   if(StringCompare(SNR_ToUpper(clean_file), "NEWS_EVENTS.CSV") != 0)
      return SNR_ParseLegacyCalendar("news_events.csv");

   return false;
}

int SNR_FindNearestRelevantNewsMinutes(const datetime now_utc,
                                       const string base_currency,
                                       const string quote_currency,
                                       bool &block_entry,
                                       bool &force_flat,
                                       string &event_class_tag)
{
   int best_abs = 1000000;
   int best_signed = 1000000;
   block_entry = false;
   force_flat = false;
   event_class_tag = "";

   for(int i = 0; i < g_snrNewsCount; i++)
   {
      if(!SNR_IsCurrencyRelevant(base_currency, quote_currency, g_snrNewsEvents[i].currency))
         continue;

      int diff_min = (int)((g_snrNewsEvents[i].utc_time - now_utc) / 60);
      int abs_diff = MathAbs(diff_min);
      if(abs_diff < best_abs)
      {
         best_abs = abs_diff;
         best_signed = diff_min;
         event_class_tag = g_snrNewsEvents[i].event_class;
      }

      if(diff_min >= 0 && diff_min <= g_forceFlatBeforeNewsMin)
         force_flat = true;

      if((diff_min >= 0 && diff_min <= g_newsBlockBeforeMin) ||
         (diff_min < 0 && MathAbs(diff_min) <= g_newsBlockAfterMin))
      {
         block_entry = true;
      }
   }

   return best_signed;
}

string SNR_SessionBucket(const datetime server_time)
{
   bool in_london = (g_useLondon &&
                     SNR_TimeInWindow(server_time,
                                      g_londonStartHour,
                                      g_londonStartMinute,
                                      g_londonEndHour,
                                      g_londonEndMinute));
   bool in_ny = (g_useNewYork &&
                 SNR_TimeInWindow(server_time,
                                  g_newYorkStartHour,
                                  g_newYorkStartMinute,
                                  g_newYorkEndHour,
                                  g_newYorkEndMinute));

   if(in_london && in_ny)
      return "LONDON_NY";
   if(in_london)
      return "LONDON";
   if(in_ny)
      return "NEWYORK";
   return "OFF";
}

bool SNR_IsBlockedEntryHour(const datetime server_time)
{
   string value = SNR_CleanTesterString(g_blockedEntryHours);
   if(value == "")
      return false;

   MqlDateTime dt;
   TimeToStruct(server_time, dt);

   string parts[];
   int count = StringSplit(value, ',', parts);
   for(int i = 0; i < count; i++)
   {
      string item = SNR_Trim(parts[i]);
      if(item == "")
         continue;
      int hour = (int)StringToInteger(item);
      if(hour == dt.hour)
         return true;
   }
   return false;
}

int SNR_WeekdayNumberFromName(string value)
{
   string upper = SNR_ToUpper(SNR_Trim(value));
   if(upper == "SUN" || upper == "SUNDAY")
      return 0;
   if(upper == "MON" || upper == "MONDAY")
      return 1;
   if(upper == "TUE" || upper == "TUESDAY")
      return 2;
   if(upper == "WED" || upper == "WEDNESDAY")
      return 3;
   if(upper == "THU" || upper == "THURSDAY")
      return 4;
   if(upper == "FRI" || upper == "FRIDAY")
      return 5;
   if(upper == "SAT" || upper == "SATURDAY")
      return 6;
   return (int)StringToInteger(upper);
}

bool SNR_IsBlockedEntryWeekday(const datetime server_time)
{
   string value = SNR_CleanTesterString(g_blockedEntryWeekdays);
   if(value == "")
      return false;

   MqlDateTime dt;
   TimeToStruct(server_time, dt);

   string parts[];
   int count = StringSplit(value, ',', parts);
   for(int i = 0; i < count; i++)
   {
      string item = SNR_Trim(parts[i]);
      if(item == "")
         continue;
      if(SNR_WeekdayNumberFromName(item) == dt.day_of_week)
         return true;
   }
   return false;
}

bool SNR_ListContainsToken(const string csv_value, const string token)
{
   string value = SNR_CleanTesterString(csv_value);
   if(value == "")
      return false;

   string target = SNR_ToUpper(SNR_Trim(token));
   string parts[];
   int count = StringSplit(value, ',', parts);
   for(int i = 0; i < count; i++)
   {
      string item = SNR_ToUpper(SNR_Trim(parts[i]));
      if(item == target)
         return true;
   }
   return false;
}

void SNR_SelectHtfBiasTimeframes(ENUM_TIMEFRAMES &fast_tf, ENUM_TIMEFRAMES &slow_tf)
{
   fast_tf = PERIOD_H1;
   slow_tf = PERIOD_H4;

   if(g_htfProfileMode != 1)
      return;

   int current_seconds = PeriodSeconds(_Period);
   int m5_seconds = PeriodSeconds(PERIOD_M5);
   if(current_seconds > 0 && m5_seconds > 0 && current_seconds <= m5_seconds)
   {
      fast_tf = PERIOD_M15;
      slow_tf = PERIOD_H1;
   }
}

string SNR_HtfTimeframeName(const ENUM_TIMEFRAMES timeframe)
{
   return EnumToString(timeframe);
}

int SNR_MinutesToForcedFlat(const datetime server_time)
{
   int best = 1440;

   if(g_useLondon &&
      SNR_TimeInWindow(server_time,
                       g_londonStartHour,
                       g_londonStartMinute,
                       g_londonEndHour,
                       g_londonEndMinute))
   {
      best = MathMin(best, SNR_MinutesUntilClock(server_time, g_londonEndHour, g_londonEndMinute));
   }

   if(g_useNewYork &&
      SNR_TimeInWindow(server_time,
                       g_newYorkStartHour,
                       g_newYorkStartMinute,
                       g_newYorkEndHour,
                       g_newYorkEndMinute))
   {
      best = MathMin(best, SNR_MinutesUntilClock(server_time, g_newYorkEndHour, g_newYorkEndMinute));
   }

   best = MathMin(best, SNR_MinutesUntilClock(server_time, g_hardFlatHour, g_hardFlatMinute));

   MqlDateTime dt;
   TimeToStruct(server_time, dt);
   if(dt.day_of_week == 5)
      best = MathMin(best, SNR_MinutesUntilClock(server_time, g_fridayFlatHour, g_fridayFlatMinute));

   return best;
}

#endif
