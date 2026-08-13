//+------------------------------------------------------------------+
//| EA_QuotePathFidelityProbe.mq5                                    |
//| HYP-QPF-EURUSD-M1-002 - collection-only quote-path reissue       |
//+------------------------------------------------------------------+
#property copyright "AlphaFactory research"
#property version   "1.00"
#property strict
#property description "Outcome-blind EURUSD real-tick quote-path fidelity probe"

input bool   InpCollectionOnly=true;
input string InpHypothesisId="HYP-QPF-EURUSD-M1-002";
input string InpExpectedSymbol="EURUSD";
input int    InpExpectedPeriodMinutes=1;
input int    InpBucketMinutes=5;

const string SCHEMA_VERSION="alphafactory.quote_path_fidelity.v1";
const string TELEMETRY_PROFILE="none";

string   g_run_id="";
string   g_csv_name="";
int      g_csv_handle=INVALID_HANDLE;
datetime g_bucket_start=0;
datetime g_previous_bucket=0;
long     g_emitted_buckets=0;
long     g_out_of_order_buckets=0;

long g_total_ticks=0;
long g_valid_quotes=0;
long g_invalid_quotes=0;
long g_invalid_time=0;
long g_repeated_time_msc=0;
long g_reverse_time_msc=0;
long g_exact_duplicate_quotes=0;
long g_quote_changes=0;
long g_bid_only_changes=0;
long g_ask_only_changes=0;
long g_both_changes=0;
long g_mid_up=0;
long g_mid_down=0;
long g_mid_flat=0;
long g_spread_changes=0;
long g_quote_flag_ticks=0;
long g_trade_flag_ticks=0;
long g_positive_volume_ticks=0;
long g_interarrival_count=0;
long g_gap_le_10=0;
long g_gap_le_50=0;
long g_gap_le_100=0;
long g_gap_le_250=0;
long g_gap_le_500=0;
long g_gap_le_1000=0;
long g_gap_le_5000=0;
long g_gap_le_15000=0;
long g_gap_gt_15000=0;
long g_max_gap_ms=0;
long g_duplicate_run=0;
long g_longest_duplicate_run=0;
long g_constant_spread_run=0;
long g_longest_constant_spread_run=0;
double g_spread_sum_points=0.0;
double g_spread_min_points=0.0;
double g_spread_max_points=0.0;

bool   g_have_previous=false;
long   g_previous_time_msc=0;
double g_previous_bid=0.0;
double g_previous_ask=0.0;
double g_previous_mid=0.0;
double g_previous_spread=0.0;

bool IdentityOk()
  {
   return InpCollectionOnly &&
          InpHypothesisId=="HYP-QPF-EURUSD-M1-002" &&
          InpExpectedSymbol=="EURUSD" &&
          _Symbol==InpExpectedSymbol &&
          InpExpectedPeriodMinutes==1 &&
          _Period==PERIOD_M1 &&
          InpBucketMinutes==5;
  }

bool QuoteValid(const MqlTick &tick)
  {
   return MathIsValidNumber(tick.bid) && MathIsValidNumber(tick.ask) &&
          tick.bid>0.0 && tick.ask>0.0 && tick.ask>=tick.bid;
  }

datetime BucketStart(const datetime tick_time)
  {
   long seconds=(long)InpBucketMinutes*60;
   return (datetime)(((long)tick_time/seconds)*seconds);
  }

void ResetBucket(const datetime bucket_start)
  {
   g_bucket_start=bucket_start;
   g_total_ticks=0;
   g_valid_quotes=0;
   g_invalid_quotes=0;
   g_invalid_time=0;
   g_repeated_time_msc=0;
   g_reverse_time_msc=0;
   g_exact_duplicate_quotes=0;
   g_quote_changes=0;
   g_bid_only_changes=0;
   g_ask_only_changes=0;
   g_both_changes=0;
   g_mid_up=0;
   g_mid_down=0;
   g_mid_flat=0;
   g_spread_changes=0;
   g_quote_flag_ticks=0;
   g_trade_flag_ticks=0;
   g_positive_volume_ticks=0;
   g_interarrival_count=0;
   g_gap_le_10=0;
   g_gap_le_50=0;
   g_gap_le_100=0;
   g_gap_le_250=0;
   g_gap_le_500=0;
   g_gap_le_1000=0;
   g_gap_le_5000=0;
   g_gap_le_15000=0;
   g_gap_gt_15000=0;
   g_max_gap_ms=0;
   g_duplicate_run=0;
   g_longest_duplicate_run=0;
   g_constant_spread_run=0;
   g_longest_constant_spread_run=0;
   g_spread_sum_points=0.0;
   g_spread_min_points=0.0;
   g_spread_max_points=0.0;
  }

bool OpenTelemetry()
  {
   g_run_id=StringFormat("%s_%I64d_%u",InpHypothesisId,(long)TimeGMT(),(uint)GetTickCount());
   g_csv_name=StringFormat("%s_QuotePathFidelity_%s.csv",_Symbol,g_run_id);
   g_csv_handle=FileOpen(g_csv_name,FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_REWRITE,',');
   if(g_csv_handle==INVALID_HANDLE)
     {
      PrintFormat("QPF_FILE_OPEN_FAIL name=%s error=%d",g_csv_name,GetLastError());
      return false;
     }
   FileWrite(g_csv_handle,
             "schema_version","hypothesis_id","run_id","symbol","timeframe",
             "bucket_start_server","bucket_end_server","gap_from_previous_buckets",
             "total_ticks","valid_quotes","invalid_quotes","invalid_time",
             "repeated_time_msc","reverse_time_msc","exact_duplicate_quotes",
             "quote_changes","bid_only_changes","ask_only_changes","both_changes",
             "mid_up","mid_down","mid_flat","spread_changes",
             "quote_flag_ticks","trade_flag_ticks","positive_volume_ticks",
             "interarrival_count","gap_le_10","gap_le_50","gap_le_100",
             "gap_le_250","gap_le_500","gap_le_1000","gap_le_5000",
             "gap_le_15000","gap_gt_15000","max_gap_ms",
             "longest_duplicate_run","longest_constant_spread_run",
             "spread_mean_points","spread_min_points","spread_max_points",
             "bar_complete","orders_sent","promotion_eligible");
   FileFlush(g_csv_handle);
   return true;
  }

void FinalizeBucket()
  {
   if(g_bucket_start<=0 || g_csv_handle==INVALID_HANDLE || g_total_ticks<=0)
      return;
   long gap_buckets=0;
   long bucket_seconds=(long)InpBucketMinutes*60;
   if(g_previous_bucket>0 && g_bucket_start>g_previous_bucket)
      gap_buckets=((long)g_bucket_start-(long)g_previous_bucket)/bucket_seconds-1;
   double spread_mean=(g_valid_quotes>0)
                      ? g_spread_sum_points/(double)g_valid_quotes : 0.0;
   FileWrite(g_csv_handle,
             SCHEMA_VERSION,InpHypothesisId,g_run_id,_Symbol,"M1",
             TimeToString(g_bucket_start,TIME_DATE|TIME_SECONDS),
             TimeToString(g_bucket_start+bucket_seconds,TIME_DATE|TIME_SECONDS),
             IntegerToString(gap_buckets),IntegerToString(g_total_ticks),
             IntegerToString(g_valid_quotes),IntegerToString(g_invalid_quotes),
             IntegerToString(g_invalid_time),IntegerToString(g_repeated_time_msc),
             IntegerToString(g_reverse_time_msc),IntegerToString(g_exact_duplicate_quotes),
             IntegerToString(g_quote_changes),IntegerToString(g_bid_only_changes),
             IntegerToString(g_ask_only_changes),IntegerToString(g_both_changes),
             IntegerToString(g_mid_up),IntegerToString(g_mid_down),IntegerToString(g_mid_flat),
             IntegerToString(g_spread_changes),IntegerToString(g_quote_flag_ticks),
             IntegerToString(g_trade_flag_ticks),IntegerToString(g_positive_volume_ticks),
             IntegerToString(g_interarrival_count),IntegerToString(g_gap_le_10),
             IntegerToString(g_gap_le_50),IntegerToString(g_gap_le_100),
             IntegerToString(g_gap_le_250),IntegerToString(g_gap_le_500),
             IntegerToString(g_gap_le_1000),IntegerToString(g_gap_le_5000),
             IntegerToString(g_gap_le_15000),IntegerToString(g_gap_gt_15000),
             IntegerToString(g_max_gap_ms),IntegerToString(g_longest_duplicate_run),
             IntegerToString(g_longest_constant_spread_run),DoubleToString(spread_mean,6),
             DoubleToString(g_spread_min_points,6),DoubleToString(g_spread_max_points,6),
             "true","0","false");
   g_previous_bucket=g_bucket_start;
   g_emitted_buckets++;
   if((g_emitted_buckets%1000)==0)
      FileFlush(g_csv_handle);
  }

void CountGap(const long gap_ms)
  {
   if(gap_ms<=0)
      return;
   g_interarrival_count++;
   if(gap_ms>g_max_gap_ms)
      g_max_gap_ms=gap_ms;
   if(gap_ms<=10) g_gap_le_10++;
   else if(gap_ms<=50) g_gap_le_50++;
   else if(gap_ms<=100) g_gap_le_100++;
   else if(gap_ms<=250) g_gap_le_250++;
   else if(gap_ms<=500) g_gap_le_500++;
   else if(gap_ms<=1000) g_gap_le_1000++;
   else if(gap_ms<=5000) g_gap_le_5000++;
   else if(gap_ms<=15000) g_gap_le_15000++;
   else g_gap_gt_15000++;
  }

void ProcessTick(const MqlTick &tick)
  {
   g_total_ticks++;
   if((tick.flags&(TICK_FLAG_BID|TICK_FLAG_ASK))!=0) g_quote_flag_ticks++;
   if((tick.flags&(TICK_FLAG_LAST|TICK_FLAG_VOLUME|TICK_FLAG_BUY|TICK_FLAG_SELL))!=0)
      g_trade_flag_ticks++;
   if(tick.volume>0 || tick.volume_real>0.0) g_positive_volume_ticks++;
   if(tick.time_msc<=0) g_invalid_time++;
   if(!QuoteValid(tick))
     {
      g_invalid_quotes++;
      return;
     }
   g_valid_quotes++;
   double spread=tick.ask-tick.bid;
   double spread_points=(_Point>0.0) ? spread/_Point : 0.0;
   g_spread_sum_points+=spread_points;
   if(g_spread_min_points<=0.0 || spread_points<g_spread_min_points)
      g_spread_min_points=spread_points;
   if(spread_points>g_spread_max_points) g_spread_max_points=spread_points;

   if(g_have_previous)
     {
      long gap=tick.time_msc-g_previous_time_msc;
      if(gap==0) g_repeated_time_msc++;
      else if(gap<0) g_reverse_time_msc++;
      else CountGap(gap);

      bool bid_changed=(tick.bid!=g_previous_bid);
      bool ask_changed=(tick.ask!=g_previous_ask);
      bool exact_duplicate=(!bid_changed && !ask_changed);
      if(exact_duplicate)
        {
         g_exact_duplicate_quotes++;
         g_duplicate_run++;
         if(g_duplicate_run>g_longest_duplicate_run)
            g_longest_duplicate_run=g_duplicate_run;
        }
      else
        {
         g_duplicate_run=0;
         g_quote_changes++;
         if(bid_changed && ask_changed) g_both_changes++;
         else if(bid_changed) g_bid_only_changes++;
         else if(ask_changed) g_ask_only_changes++;
        }

      double mid=(tick.bid+tick.ask)*0.5;
      if(mid>g_previous_mid) g_mid_up++;
      else if(mid<g_previous_mid) g_mid_down++;
      else g_mid_flat++;

      if(spread!=g_previous_spread)
        {
         g_spread_changes++;
         g_constant_spread_run=0;
        }
      else
        {
         g_constant_spread_run++;
         if(g_constant_spread_run>g_longest_constant_spread_run)
            g_longest_constant_spread_run=g_constant_spread_run;
        }
     }

   g_previous_time_msc=tick.time_msc;
   g_previous_bid=tick.bid;
   g_previous_ask=tick.ask;
   g_previous_mid=(tick.bid+tick.ask)*0.5;
   g_previous_spread=spread;
   g_have_previous=true;
  }

int OnInit()
  {
   if(!IdentityOk())
     {
      Print("QPF_IDENTITY_FAIL require exact HYP-QPF-EURUSD-M1-002 EURUSD M1 collection-only defaults");
      return INIT_FAILED;
     }
   if(!OpenTelemetry())
      return INIT_FAILED;
   PrintFormat("QPF_READY hypothesis_id=%s symbol=%s timeframe=M1 bucket_minutes=%d model_requires_real_ticks=true collection_only=true telemetry_profile=%s",
               InpHypothesisId,_Symbol,InpBucketMinutes,TELEMETRY_PROFILE);
   return INIT_SUCCEEDED;
  }

void OnTick()
  {
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick))
      return;
   datetime bucket_start=BucketStart(tick.time);
   if(bucket_start<=0)
      return;
   if(g_bucket_start==0)
      ResetBucket(bucket_start);
   else if(bucket_start<g_bucket_start)
     {
      g_out_of_order_buckets++;
      return;
     }
   else if(bucket_start>g_bucket_start)
     {
      FinalizeBucket();
      ResetBucket(bucket_start);
     }
   ProcessTick(tick);
  }

void OnDeinit(const int reason)
  {
   // The final open bucket is omitted because no later tick proved completion.
   if(g_csv_handle!=INVALID_HANDLE)
     {
      FileFlush(g_csv_handle);
      FileClose(g_csv_handle);
      g_csv_handle=INVALID_HANDLE;
     }
   PrintFormat("QPF_SUMMARY hypothesis_id=%s emitted_buckets=%I64d out_of_order_buckets=%I64d final_open_bucket_omitted=true orders_sent=0 reason=%d",
               InpHypothesisId,g_emitted_buckets,g_out_of_order_buckets,reason);
  }

// Collection only by construction: no trade request, position or deal API.
