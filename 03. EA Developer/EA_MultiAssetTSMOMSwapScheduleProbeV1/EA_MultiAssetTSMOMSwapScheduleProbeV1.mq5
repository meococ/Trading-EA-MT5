//+------------------------------------------------------------------+
//| EA_MultiAssetTSMOMSwapScheduleProbeV1.mq5                        |
//| Source-only weekday swap schedule probe; sends no orders.        |
//+------------------------------------------------------------------+
#property copyright "AlphaFactory research"
#property version   "1.00"
#property strict
#property description "No-order weekday swap schedule probe for MTS004"

input bool  InpResearchAutoMode=true;
input ulong InpMagic=260812009;

const string HYPOTHESIS_ID="HYP-MULTI-TSMOM-D1-004-SWAP-SCHEDULE-PROBE-001";
#define SYMBOL_COUNT 9
string g_symbols[SYMBOL_COUNT]={"EURUSD","GBPUSD","AUDUSD","NZDUSD",
                                "USDJPY","USDCAD","USDCHF","XAUUSD","BTCUSD"};
long g_ticks=0;

bool EmitSeriesProof()
  {
   long sync=0,m5first=0,m5terminal=0,m1server=0,m1terminal=0,bars=0;
   if(!SeriesInfoInteger(_Symbol,PERIOD_M5,SERIES_SYNCHRONIZED,sync) ||
      !SeriesInfoInteger(_Symbol,PERIOD_M5,SERIES_FIRSTDATE,m5first) ||
      !SeriesInfoInteger(_Symbol,PERIOD_M5,SERIES_TERMINAL_FIRSTDATE,m5terminal) ||
      !SeriesInfoInteger(_Symbol,PERIOD_M1,SERIES_SERVER_FIRSTDATE,m1server) ||
      !SeriesInfoInteger(_Symbol,PERIOD_M1,SERIES_TERMINAL_FIRSTDATE,m1terminal) ||
      !SeriesInfoInteger(_Symbol,PERIOD_M5,SERIES_BARS_COUNT,bars))
      return false;
   ResetLastError();
   const long maxbars=TerminalInfoInteger(TERMINAL_MAXBARS);
   const int terminal_error=GetLastError();
   datetime copied_time[];
   ArraySetAsSeries(copied_time,false);
   ResetLastError();
   const int copied=CopyTime(_Symbol,PERIOD_M5,(datetime)m5first,1,copied_time);
   const int copy_error=GetLastError();
   const long copied_first=(copied==1 ? (long)copied_time[0] : 0);
   PrintFormat("DATA_EPOCH_D0_SERIES_PROOF symbol=%s m5_synchronized=%I64d m5_first_epoch=%I64d m5_terminal_first_epoch=%I64d m1_server_first_epoch=%I64d m1_terminal_first_epoch=%I64d m5_bars=%I64d terminal_maxbars=%I64d copytime_from_epoch=%I64d copytime_count=1 copytime_result=%d copytime_first_epoch=%I64d copytime_last_error=%d",
               _Symbol,sync,m5first,m5terminal,m1server,m1terminal,bars,maxbars,
               m5first,copied,copied_first,copy_error);
   return sync==1 && m5first>0 && m5terminal>0 && m1server>0 &&
          m1terminal>0 && bars>0 && maxbars>0 && terminal_error==0 &&
          copied==1 && copied_first==m5first && copy_error==0;
  }

void EmitSwapSchedule(const string symbol)
  {
   ResetLastError();
   const bool selected=SymbolSelect(symbol,true);
   const int select_error=GetLastError();
   long mode=0,rollover3=0;
   double swap_long=0.0,swap_short=0.0;
   double sunday=0.0,monday=0.0,tuesday=0.0,wednesday=0.0;
   double thursday=0.0,friday=0.0,saturday=0.0;
   const bool integer_ok=
      SymbolInfoInteger(symbol,SYMBOL_SWAP_MODE,mode) &&
      SymbolInfoInteger(symbol,SYMBOL_SWAP_ROLLOVER3DAYS,rollover3);
   const bool double_ok=
      SymbolInfoDouble(symbol,SYMBOL_SWAP_LONG,swap_long) &&
      SymbolInfoDouble(symbol,SYMBOL_SWAP_SHORT,swap_short) &&
      SymbolInfoDouble(symbol,SYMBOL_SWAP_SUNDAY,sunday) &&
      SymbolInfoDouble(symbol,SYMBOL_SWAP_MONDAY,monday) &&
      SymbolInfoDouble(symbol,SYMBOL_SWAP_TUESDAY,tuesday) &&
      SymbolInfoDouble(symbol,SYMBOL_SWAP_WEDNESDAY,wednesday) &&
      SymbolInfoDouble(symbol,SYMBOL_SWAP_THURSDAY,thursday) &&
      SymbolInfoDouble(symbol,SYMBOL_SWAP_FRIDAY,friday) &&
      SymbolInfoDouble(symbol,SYMBOL_SWAP_SATURDAY,saturday);
   PrintFormat("MTS004_SWAP_SCHEDULE symbol=%s selected=%s select_error=%d integer_ok=%s double_ok=%s mode=%I64d swap_long=%.12f swap_short=%.12f rollover3=%I64d sunday=%.6f monday=%.6f tuesday=%.6f wednesday=%.6f thursday=%.6f friday=%.6f saturday=%.6f weekly_sum=%.6f",
               symbol,(string)selected,select_error,(string)integer_ok,(string)double_ok,
               mode,swap_long,swap_short,rollover3,sunday,monday,tuesday,wednesday,
               thursday,friday,saturday,
               sunday+monday+tuesday+wednesday+thursday+friday+saturday);
  }

int OnInit()
  {
   if(_Symbol!="EURUSD" || _Period!=PERIOD_H1 || !InpResearchAutoMode ||
      InpMagic!=260812009)
      return INIT_FAILED;
   if(!EmitSeriesProof())
      return INIT_FAILED;
   for(int i=0;i<SYMBOL_COUNT;i++)
      EmitSwapSchedule(g_symbols[i]);
   PrintFormat("MTS004_SWAP_SCHEDULE_READY hypothesis_id=%s economics_authorized=false",
               HYPOTHESIS_ID);
   return INIT_SUCCEEDED;
  }

void OnTick()
  {
   g_ticks++;
  }

void OnDeinit(const int reason)
  {
   PrintFormat("MTS004_SWAP_SCHEDULE_SUMMARY hypothesis_id=%s ticks=%I64d reason=%d orders=0 performance_metrics_authorized=false economics_authorized=false",
               HYPOTHESIS_ID,g_ticks,reason);
  }
//+------------------------------------------------------------------+
