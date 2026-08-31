//+------------------------------------------------------------------+
//| EA_NativeSessionStatsProbe.mq5                                   |
//| Source-only native MT5 session-statistics capability probe.      |
//+------------------------------------------------------------------+
#property copyright "AlphaFactory research"
#property version   "1.00"
#property strict
#property description "No-order XAU/FX native session-statistics source probe"

input bool  InpResearchAutoMode=true;
input ulong InpMagic=260813101;

const string HYPOTHESIS_ID="HYP-NATIVE-SESSION-STATS-XAUFX-H1-004";
#define SYMBOL_COUNT 8
string g_symbols[SYMBOL_COUNT]={"XAUUSD","EURUSD","GBPUSD","USDJPY",
                                "AUDUSD","NZDUSD","USDCAD","USDCHF"};

long  g_observations[SYMBOL_COUNT];
long  g_directional_rows[SYMBOL_COUNT];
long  g_interest_rows[SYMBOL_COUNT];
long  g_nonzero_rows[SYMBOL_COUNT];
long  g_transitions[SYMBOL_COUNT];
ulong g_last_hash[SYMBOL_COUNT];
long  g_last_month_bucket=-1;
bool  g_all_selected=true;
bool  g_all_getters_ok=true;

string B01(const bool value)
  {
   return(value ? "true" : "false");
  }

bool ReadSeriesInteger(const ENUM_TIMEFRAMES timeframe,
                       const ENUM_SERIES_INFO_INTEGER property_id,
                       const string field_name,
                       long &value)
  {
   ResetLastError();
   if(!SeriesInfoInteger(_Symbol,timeframe,property_id,value))
     {
      PrintFormat("DATA_EPOCH_D0_INIT_FAIL reason=series_info_invalid symbol=%s field=%s timeframe=%d error=%d",
                  _Symbol,field_name,(int)timeframe,GetLastError());
      return false;
     }
   return true;
  }

bool EmitDataEpochProof()
  {
   long m5_synchronized=0;
   long m5_first_epoch=0;
   long m5_terminal_first_epoch=0;
   long m1_server_first_epoch=0;
   long m1_terminal_first_epoch=0;
   long m5_bars=0;
   long terminal_maxbars=0;

   if(!ReadSeriesInteger(PERIOD_M5,SERIES_SYNCHRONIZED,"m5_synchronized",m5_synchronized) ||
      !ReadSeriesInteger(PERIOD_M5,SERIES_FIRSTDATE,"m5_first_epoch",m5_first_epoch) ||
      !ReadSeriesInteger(PERIOD_M5,SERIES_TERMINAL_FIRSTDATE,"m5_terminal_first_epoch",m5_terminal_first_epoch) ||
      !ReadSeriesInteger(PERIOD_M1,SERIES_SERVER_FIRSTDATE,"m1_server_first_epoch",m1_server_first_epoch) ||
      !ReadSeriesInteger(PERIOD_M1,SERIES_TERMINAL_FIRSTDATE,"m1_terminal_first_epoch",m1_terminal_first_epoch) ||
      !ReadSeriesInteger(PERIOD_M5,SERIES_BARS_COUNT,"m5_bars",m5_bars))
      return false;

   ResetLastError();
   terminal_maxbars=TerminalInfoInteger(TERMINAL_MAXBARS);
   const int terminal_error=GetLastError();
   if(terminal_maxbars<=0 || terminal_error!=0)
     {
      PrintFormat("DATA_EPOCH_D0_INIT_FAIL reason=terminal_maxbars_invalid symbol=%s terminal_maxbars=%I64d error=%d",
                  _Symbol,terminal_maxbars,terminal_error);
      return false;
     }

   datetime copytime_values[];
   ArraySetAsSeries(copytime_values,false);
   const datetime copytime_from=(datetime)m5_first_epoch;
   ResetLastError();
   const int copytime_result=CopyTime(_Symbol,PERIOD_M5,copytime_from,1,copytime_values);
   const int copytime_error=GetLastError();
   long copytime_first_epoch=0;
   if(copytime_result==1)
      copytime_first_epoch=(long)copytime_values[0];

   PrintFormat("DATA_EPOCH_D0_SERIES_PROOF symbol=%s m5_synchronized=%I64d m5_first_epoch=%I64d m5_terminal_first_epoch=%I64d m1_server_first_epoch=%I64d m1_terminal_first_epoch=%I64d m5_bars=%I64d terminal_maxbars=%I64d copytime_from_epoch=%I64d copytime_count=1 copytime_result=%d copytime_first_epoch=%I64d copytime_last_error=%d",
               _Symbol,m5_synchronized,m5_first_epoch,m5_terminal_first_epoch,
               m1_server_first_epoch,m1_terminal_first_epoch,m5_bars,terminal_maxbars,
               (long)copytime_from,copytime_result,copytime_first_epoch,copytime_error);

   if(m5_synchronized!=1 || m5_first_epoch<=0 || m5_terminal_first_epoch<=0 ||
      m1_server_first_epoch<=0 || m1_terminal_first_epoch<=0 || m5_bars<=0 ||
      copytime_result!=1 || copytime_first_epoch!=m5_first_epoch || copytime_error!=0)
     {
      PrintFormat("DATA_EPOCH_D0_INIT_FAIL reason=series_proof_invalid symbol=%s m5_synchronized=%I64d copytime_result=%d copytime_last_error=%d",
                  _Symbol,m5_synchronized,copytime_result,copytime_error);
      return false;
     }
   return true;
  }

ulong Fnv1a(const string value)
  {
   ulong hash=1469598103934665603;
   ushort chars[];
   int count=StringToShortArray(value,chars);
   if(count>0)
      count--;
   for(int i=0;i<count;i++)
     {
      hash^=(ulong)chars[i];
      hash*=1099511628211;
     }
   return hash;
  }

void SampleSymbol(const int index,const string stage,const datetime tester_time)
  {
   const string symbol=g_symbols[index];
   ResetLastError();
   const bool selected=SymbolSelect(symbol,true);
   const int select_error=GetLastError();

   long deals=0,buy_orders=0,sell_orders=0,calc_mode=0;
   double session_volume=0.0,session_interest=0.0;
   double buy_orders_volume=0.0,sell_orders_volume=0.0;

   ResetLastError();
   const bool deals_ok=SymbolInfoInteger(symbol,SYMBOL_SESSION_DEALS,deals);
   const bool buy_orders_ok=SymbolInfoInteger(symbol,SYMBOL_SESSION_BUY_ORDERS,buy_orders);
   const bool sell_orders_ok=SymbolInfoInteger(symbol,SYMBOL_SESSION_SELL_ORDERS,sell_orders);
   const bool calc_mode_ok=SymbolInfoInteger(symbol,SYMBOL_TRADE_CALC_MODE,calc_mode);
   const bool session_volume_ok=SymbolInfoDouble(symbol,SYMBOL_SESSION_VOLUME,session_volume);
   const bool session_interest_ok=SymbolInfoDouble(symbol,SYMBOL_SESSION_INTEREST,session_interest);
   const bool buy_volume_ok=SymbolInfoDouble(symbol,SYMBOL_SESSION_BUY_ORDERS_VOLUME,buy_orders_volume);
   const bool sell_volume_ok=SymbolInfoDouble(symbol,SYMBOL_SESSION_SELL_ORDERS_VOLUME,sell_orders_volume);
   const int getter_error=GetLastError();

   const bool getters_ok=(deals_ok && buy_orders_ok && sell_orders_ok &&
                          calc_mode_ok && session_volume_ok &&
                          session_interest_ok && buy_volume_ok &&
                          sell_volume_ok);
   const bool directional=((buy_orders>0 && sell_orders>0) ||
                           (buy_orders_volume>0.0 && sell_orders_volume>0.0));
   const bool interest_nonzero=(session_interest>0.0);
   const bool any_nonzero=(deals>0 || buy_orders>0 || sell_orders>0 ||
                           session_volume>0.0 || session_interest>0.0 ||
                           buy_orders_volume>0.0 || sell_orders_volume>0.0);

   const string state=StringFormat("%I64d|%I64d|%I64d|%.8f|%.8f|%.8f|%.8f",
                                   deals,buy_orders,sell_orders,session_volume,
                                   session_interest,buy_orders_volume,
                                   sell_orders_volume);
   const ulong state_hash=Fnv1a(state);
   if(g_observations[index]>0 && state_hash!=g_last_hash[index])
      g_transitions[index]++;
   g_last_hash[index]=state_hash;
   g_observations[index]++;
   if(directional)
      g_directional_rows[index]++;
   if(interest_nonzero)
      g_interest_rows[index]++;
   if(any_nonzero)
      g_nonzero_rows[index]++;
   if(!selected)
      g_all_selected=false;
   if(!getters_ok)
      g_all_getters_ok=false;

   PrintFormat("NSSP_SAMPLE hypothesis_id=%s stage=%s tester_time_epoch=%I64d symbol=%s selected=%s select_error=%d getters_ok=%s getter_error=%d calc_mode=%I64d deals=%I64d buy_orders=%I64d sell_orders=%I64d session_volume=%.8f session_interest=%.8f buy_orders_volume=%.8f sell_orders_volume=%.8f directional=%s any_nonzero=%s state_hash=%I64u prices_read=false orders=0 economics_authorized=false",
               HYPOTHESIS_ID,stage,(long)tester_time,symbol,B01(selected),
               select_error,B01(getters_ok),getter_error,calc_mode,deals,
               buy_orders,sell_orders,session_volume,session_interest,
               buy_orders_volume,sell_orders_volume,B01(directional),
               B01(any_nonzero),state_hash);
  }

void SampleAll(const string stage)
  {
   const datetime tester_time=TimeCurrent();
   for(int i=0;i<SYMBOL_COUNT;i++)
      SampleSymbol(i,stage,tester_time);
  }

long MonthBucket(const datetime value)
  {
   MqlDateTime parts;
   if(!TimeToStruct(value,parts))
      return -1;
   return((long)parts.year*12+(long)parts.mon);
  }

int OnInit()
  {
   if(_Symbol!="EURUSD" || _Period!=PERIOD_H1 || !InpResearchAutoMode ||
      InpMagic!=260813101)
      return INIT_FAILED;
   if(!EmitDataEpochProof())
      return INIT_FAILED;
   g_last_month_bucket=MonthBucket(TimeCurrent());
   if(g_last_month_bucket<0)
      return INIT_FAILED;
   SampleAll("INIT");
   PrintFormat("NSSP_READY hypothesis_id=%s symbols=%d source_only=true prices_read=false orders=0 historical_pit_authorized=false performance_metrics_authorized=false economics_authorized=false",
               HYPOTHESIS_ID,SYMBOL_COUNT);
   return INIT_SUCCEEDED;
  }

void OnTick()
  {
   if(g_observations[0]>=24)
      return;
   const long month_bucket=MonthBucket(TimeCurrent());
   if(month_bucket<0 || month_bucket==g_last_month_bucket)
      return;
   g_last_month_bucket=month_bucket;
   SampleAll("MONTH_BUCKET");
  }

void OnDeinit(const int reason)
  {
   bool any_directional=false;
   bool any_interest=false;
   bool any_mutable=false;
   for(int i=0;i<SYMBOL_COUNT;i++)
     {
      if(g_directional_rows[i]>0)
         any_directional=true;
      if(g_interest_rows[i]>0)
         any_interest=true;
      if(g_transitions[i]>0)
         any_mutable=true;
      PrintFormat("NSSP_SYMBOL_SUMMARY hypothesis_id=%s symbol=%s observations=%I64d nonzero_rows=%I64d directional_rows=%I64d interest_rows=%I64d transitions=%I64d orders=0 prices_read=false",
                  HYPOTHESIS_ID,g_symbols[i],g_observations[i],
                  g_nonzero_rows[i],g_directional_rows[i],
                  g_interest_rows[i],g_transitions[i]);
     }
   PrintFormat("NSSP_FINAL hypothesis_id=%s reason=%d all_selected=%s all_getters_ok=%s any_directional=%s any_interest=%s any_mutable=%s source_only=true historical_pit_authorized=false performance_metrics_authorized=false economics_authorized=false orders=0 prices_read=false",
               HYPOTHESIS_ID,reason,B01(g_all_selected),
               B01(g_all_getters_ok),B01(any_directional),
               B01(any_interest),B01(any_mutable));
  }
//+------------------------------------------------------------------+
