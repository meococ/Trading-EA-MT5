//+------------------------------------------------------------------+
//| CBR_NewsFilter.mqh — News event guard for Cobra v3.0             |
//| Blocks new entries near high-impact USD economic events           |
//| Live: MQL5 CalendarValueHistory()                                |
//| Tester: loads MQL5/Files/news_events.csv                         |
//+------------------------------------------------------------------+
#ifndef CBR_NEWS_FILTER_MQH
#define CBR_NEWS_FILTER_MQH

//--- News event storage (for tester CSV mode)
struct CBR_NewsEvent
{
   datetime time;       // event time in server time
   string   eventType;
   string   currency;
   int      importance; // 2=medium, 3=high
};

static CBR_NewsEvent g_newsEvents[];
static int           g_newsCount      = 0;
static bool          g_newsLoaded     = false;
static bool          g_newsIsTester   = false;

//--- Live calendar cache
static datetime      g_newsLiveCacheTime = 0;
static datetime      g_newsLiveBlock     = 0;
static string        g_newsLiveBlockName = "";
static string        g_newsLastLog       = "";

#define CBR_NEWS_CACHE_SEC 300   // refresh live cache every 5 min

//+------------------------------------------------------------------+
//| Init — detect tester, load CSV if needed                         |
//+------------------------------------------------------------------+
void CBR_InitNews(string symbol)
{
   g_newsIsTester = (bool)MQLInfoInteger(MQL_TESTER);
   g_newsLoaded   = false;
   g_newsCount    = 0;
   g_newsLiveCacheTime = 0;

   if(g_newsIsTester)
   {
      CBR_LoadNewsCsv(symbol);
   }

   PrintFormat("[CBR] NewsFilter init | mode=%s | events=%d",
               g_newsIsTester ? "CSV" : "LIVE", g_newsCount);
}

//+------------------------------------------------------------------+
//| Load news_events.csv for Strategy Tester                         |
//| Format: date,time_utc,event_type,currency,importance             |
//| Times assumed server time (UTC+2 fixed)                          |
//+------------------------------------------------------------------+
void CBR_LoadNewsCsv(string symbol)
{
   string filename = "news_events.csv";
   int handle = FileOpen(filename, FILE_READ | FILE_CSV | FILE_ANSI, ',');
   if(handle == INVALID_HANDLE)
   {
      // Tester sandbox can't access MQL5/Files — try FILE_COMMON
      handle = FileOpen(filename, FILE_READ | FILE_CSV | FILE_ANSI | FILE_COMMON, ',');
   }
   if(handle == INVALID_HANDLE)
   {
      PrintFormat("[CBR] NewsFilter WARNING: cannot open %s (err=%d) — filter disabled in tester",
                  filename, GetLastError());
      return;
   }

   // Skip header line
   FileReadString(handle); // date
   FileReadString(handle); // time_utc
   FileReadString(handle); // event_type
   FileReadString(handle); // currency
   FileReadString(handle); // importance

   // Determine relevant currencies for this symbol
   string baseCur = "";
   if(StringFind(symbol, "XAU") >= 0 || StringFind(symbol, "GOLD") >= 0)
      baseCur = "USD";

   int count = 0;
   int capacity = 500;
   ArrayResize(g_newsEvents, capacity);

   while(!FileIsEnding(handle))
   {
      string dateStr = FileReadString(handle);
      if(StringLen(dateStr) == 0) break;

      string timeStr  = FileReadString(handle);
      string evType   = FileReadString(handle);
      string currency = FileReadString(handle);
      string impStr   = FileReadString(handle);

      int imp = (int)StringToInteger(impStr);

      // Only HIGH importance (3) and matching currency
      if(imp < 3) continue;
      if(baseCur != "" && currency != baseCur) continue;

      // Parse datetime: "2019.01.04" + "15:30"
      datetime dt = StringToTime(dateStr + " " + timeStr);
      if(dt <= 0) continue;

      if(count >= capacity)
      {
         capacity += 500;
         ArrayResize(g_newsEvents, capacity);
      }

      g_newsEvents[count].time       = dt;
      g_newsEvents[count].eventType  = evType;
      g_newsEvents[count].currency   = currency;
      g_newsEvents[count].importance = imp;
      count++;
   }

   FileClose(handle);
   ArrayResize(g_newsEvents, count);
   g_newsCount  = count;
   g_newsLoaded = true;

   PrintFormat("[CBR] NewsFilter loaded %d HIGH-impact %s events from CSV", count, baseCur);
}

//+------------------------------------------------------------------+
//| Check if news blocks entry — CSV mode (tester)                   |
//+------------------------------------------------------------------+
bool CBR_IsNewsBlockedCsv(int beforeMin, int afterMin)
{
   if(!g_newsLoaded || g_newsCount == 0)
      return false;

   datetime now = TimeCurrent();
   int beforeSec = beforeMin * 60;
   int afterSec  = afterMin  * 60;

   // Linear scan — g_newsCount is small (~150 for 6yr USD HIGH only)
   for(int i = 0; i < g_newsCount; i++)
   {
      datetime evTime = g_newsEvents[i].time;

      // Skip events far in the past
      if(evTime < now - afterSec)
         continue;

      // Stop scanning if event is far in the future
      if(evTime > now + beforeSec)
         break;

      // Within window
      if(now >= evTime - beforeSec && now <= evTime + afterSec)
      {
         string logKey = IntegerToString((int)evTime);
         if(logKey != g_newsLastLog)
         {
            PrintFormat("[CBR] NEWS BLOCK: %s at %s (now=%s)",
                        g_newsEvents[i].eventType,
                        TimeToString(evTime, TIME_DATE | TIME_MINUTES),
                        TimeToString(now, TIME_DATE | TIME_MINUTES));
            g_newsLastLog = logKey;
         }
         return true;
      }
   }

   return false;
}

//+------------------------------------------------------------------+
//| Check if news blocks entry — Live calendar mode                  |
//+------------------------------------------------------------------+
bool CBR_IsNewsBlockedLive(string symbol, int beforeMin, int afterMin)
{
   datetime now = TimeTradeServer();
   if(now <= 0) now = TimeCurrent();
   if(now <= 0) return false;

   // Refresh cache periodically
   if(now - g_newsLiveCacheTime < CBR_NEWS_CACHE_SEC && g_newsLiveCacheTime > 0)
   {
      // Use cached result
      if(g_newsLiveBlock <= 0) return false;
      return (now >= g_newsLiveBlock - beforeMin * 60 &&
              now <= g_newsLiveBlock + afterMin * 60);
   }

   g_newsLiveCacheTime = now;
   g_newsLiveBlock     = 0;
   g_newsLiveBlockName = "";

   int beforeSec = beforeMin * 60;
   int afterSec  = afterMin  * 60;
   datetime fromTs = now - afterSec;
   datetime toTs   = now + beforeSec;

   // Determine currency from symbol
   string cur = "USD";
   if(StringFind(symbol, "XAU") >= 0 || StringFind(symbol, "GOLD") >= 0)
      cur = "USD";
   else
   {
      string base = SymbolInfoString(symbol, SYMBOL_CURRENCY_BASE);
      string prof = SymbolInfoString(symbol, SYMBOL_CURRENCY_PROFIT);
      cur = (StringLen(base) > 0) ? base : prof;
   }

   MqlCalendarValue values[];
   ResetLastError();
   int n = CalendarValueHistory(values, fromTs, toTs, NULL, cur);
   if(n <= 0) return false;

   for(int i = 0; i < n; i++)
   {
      if(values[i].time <= 0) continue;

      MqlCalendarEvent ev;
      ResetLastError();
      if(!CalendarEventById(values[i].event_id, ev)) continue;

      if((ENUM_CALENDAR_EVENT_IMPORTANCE)ev.importance != CALENDAR_IMPORTANCE_HIGH)
         continue;

      if(values[i].time >= fromTs && values[i].time <= toTs)
      {
         if(g_newsLiveBlock == 0 ||
            MathAbs((int)(values[i].time - now)) < MathAbs((int)(g_newsLiveBlock - now)))
         {
            g_newsLiveBlock     = values[i].time;
            g_newsLiveBlockName = ev.name;
         }
      }
   }

   if(g_newsLiveBlock > 0)
   {
      string logKey = IntegerToString((int)g_newsLiveBlock);
      if(logKey != g_newsLastLog)
      {
         PrintFormat("[CBR] NEWS BLOCK: %s at %s",
                     g_newsLiveBlockName,
                     TimeToString(g_newsLiveBlock, TIME_DATE | TIME_MINUTES));
         g_newsLastLog = logKey;
      }
      return true;
   }

   return false;
}

//+------------------------------------------------------------------+
//| Main public function — auto-selects CSV or Live mode             |
//+------------------------------------------------------------------+
bool CBR_IsNewsBlocked(string symbol, int beforeMin, int afterMin)
{
   if(g_newsIsTester)
      return CBR_IsNewsBlockedCsv(beforeMin, afterMin);
   else
      return CBR_IsNewsBlockedLive(symbol, beforeMin, afterMin);
}

//+------------------------------------------------------------------+
//| Deinit — cleanup                                                 |
//+------------------------------------------------------------------+
void CBR_DeinitNews()
{
   ArrayFree(g_newsEvents);
   g_newsCount         = 0;
   g_newsLoaded        = false;
   g_newsLiveCacheTime = 0;
   g_newsLiveBlock     = 0;
   g_newsLastLog       = "";
}

#endif // CBR_NEWS_FILTER_MQH
