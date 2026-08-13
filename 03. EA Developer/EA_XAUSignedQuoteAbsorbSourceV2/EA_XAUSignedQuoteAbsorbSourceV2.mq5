//+------------------------------------------------------------------+
//| EA_XAUSignedQuoteAbsorbSourceV2.mq5                              |
//| HYP-XAU-SIGNED-QUOTE-ABSORB-002 - quiet runtime reissue           |
//+------------------------------------------------------------------+
#property copyright "AlphaFactory research"
#property version   "1.01"
#property strict
#property description "Collection-only signed XAU quote absorption source gate"

input bool InpCollectionOnly=true;

const string HYPOTHESIS_ID="HYP-XAU-SIGNED-QUOTE-ABSORB-002";
const string EXPECTED_SYMBOL="AFD_XAUUSD_DUKA_V3";
const int    WINDOW_MILLISECONDS=30000;
const int    MIN_NET_SIGNED_PRESSURE=8;
const double ABSORPTION_MID_ATR=0.12;
const int    ATR_PERIOD=14;
const int    WARMUP_M1_BARS=500;
const double MAX_SPREAD_USD=0.30;
const int    MIN_DESIGN_SIGNALS=350;
const int    MIN_YEAR_SIGNALS=40;
const int    MIN_SIGNAL_MEDIAN_ABS_PRESSURE=9;
const int    QUEUE_CAPACITY=262144;

long   g_queue_time_msc[];
double g_queue_mid[];
int    g_queue_net_delta[];
int    g_queue_event_count[];
int    g_queue_head=0;
int    g_queue_count=0;
int    g_window_net_pressure=0;
int    g_window_events=0;
double g_mid_at_or_before_window=0.0;
long   g_mid_at_or_before_window_time=0;

bool   g_have_previous=false;
long   g_previous_time_msc=0;
double g_previous_bid=0.0;
double g_previous_ask=0.0;
double g_previous_mid=0.0;
datetime g_current_minute_start=0;
bool   g_current_minute_has_valid_quote=false;
int    g_atr_handle=INVALID_HANDLE;

long g_total_ticks=0;
long g_valid_quote_ticks=0;
long g_invalid_quote_ticks=0;
long g_reverse_time_ticks=0;
long g_duplicate_time_ticks=0;
long g_exact_duplicate_quotes=0;
long g_completed_valid_m1=0;
long g_gap_minutes=0;
long g_signal_count=0;
long g_long_signals=0;
long g_short_signals=0;
long g_year_signals[4];
int  g_signal_abs_pressure[];
bool g_queue_overflow=false;

bool QuoteValid(const MqlTick &tick)
  {
   return tick.time_msc>0 && MathIsValidNumber(tick.bid) &&
          MathIsValidNumber(tick.ask) && tick.bid>0.0 &&
          tick.ask>tick.bid;
  }

int SignedStep(const double delta)
  {
   if(delta>0.0)
      return 1;
   if(delta<0.0)
      return -1;
   return 0;
  }

void ClearQuoteQueue()
  {
   g_queue_head=0;
   g_queue_count=0;
   g_window_net_pressure=0;
   g_window_events=0;
   g_mid_at_or_before_window=0.0;
   g_mid_at_or_before_window_time=0;
  }

bool AppendQuote(const long time_msc,
                 const double mid,
                 const int net_delta,
                 const int event_count)
  {
   if(g_queue_count>=QUEUE_CAPACITY)
     {
      g_queue_overflow=true;
      return false;
     }
   int index=(g_queue_head+g_queue_count)%QUEUE_CAPACITY;
   g_queue_time_msc[index]=time_msc;
   g_queue_mid[index]=mid;
   g_queue_net_delta[index]=net_delta;
   g_queue_event_count[index]=event_count;
   g_queue_count++;
   g_window_net_pressure+=net_delta;
   g_window_events+=event_count;
   return true;
  }

void PruneThrough(const long cutoff_msc)
  {
   while(g_queue_count>0)
     {
      int index=g_queue_head;
      if(g_queue_time_msc[index]>cutoff_msc)
         break;
      g_mid_at_or_before_window=g_queue_mid[index];
      g_mid_at_or_before_window_time=g_queue_time_msc[index];
      g_window_net_pressure-=g_queue_net_delta[index];
      g_window_events-=g_queue_event_count[index];
      g_queue_head=(g_queue_head+1)%QUEUE_CAPACITY;
      g_queue_count--;
     }
  }

bool IsEntrySession(const datetime decision_time)
  {
   MqlDateTime stamp;
   if(!TimeToStruct(decision_time,stamp))
      return false;
   if(stamp.day_of_week<1 || stamp.day_of_week>5)
      return false;
   if(stamp.hour<1 || stamp.hour>=21)
      return false;
   if(stamp.day_of_week==5 && stamp.hour>=18)
      return false;
   return true;
  }

int DesignYearIndex(const datetime decision_time)
  {
   MqlDateTime stamp;
   if(!TimeToStruct(decision_time,stamp))
      return -1;
   if(stamp.year<2018 || stamp.year>2021)
      return -1;
   return stamp.year-2018;
  }

bool ReadClosedAtr(double &atr)
  {
   double values[1];
   ResetLastError();
   if(CopyBuffer(g_atr_handle,0,1,1,values)!=1 ||
      !MathIsValidNumber(values[0]) || values[0]<=0.0)
      return false;
   atr=values[0];
   return true;
  }

void RegisterSignal(const bool is_long,
                    const datetime decision_time,
                    const int net_pressure,
                    const int events,
                    const double mid_move,
                    const double atr,
                    const double spread)
  {
   int size=ArraySize(g_signal_abs_pressure);
   if(ArrayResize(g_signal_abs_pressure,size+1)!=size+1)
     {
      g_queue_overflow=true;
      return;
     }
   g_signal_abs_pressure[size]=(int)MathAbs(net_pressure);
   g_signal_count++;
   if(is_long)
      g_long_signals++;
   else
      g_short_signals++;
   int year_index=DesignYearIndex(decision_time);
   if(year_index>=0)
      g_year_signals[year_index]++;
   // Per-signal journal emission is deliberately disabled in V2. The V1
   // source-gate filled the bounded journal before the final summary.
  }

void EvaluateClosedMinute(const datetime decision_time,
                          const MqlTick &entry_tick)
  {
   g_completed_valid_m1++;
   if(g_completed_valid_m1<WARMUP_M1_BARS || !IsEntrySession(decision_time))
      return;

   long boundary_msc=(long)decision_time*1000;
   long window_start_msc=boundary_msc-WINDOW_MILLISECONDS;
   // Frozen interval is (decision-30s, decision). Ticks exactly on the left
   // boundary establish the starting mid but do not add a signed event.
   PruneThrough(window_start_msc);
   if(g_mid_at_or_before_window_time<=0 || g_previous_time_msc>=boundary_msc ||
      g_previous_time_msc<=window_start_msc || g_window_events<MIN_NET_SIGNED_PRESSURE)
      return;

   double atr=0.0;
   if(!ReadClosedAtr(atr))
      return;
   double mid_move=g_previous_mid-g_mid_at_or_before_window;
   double spread=entry_tick.ask-entry_tick.bid;
   if(!MathIsValidNumber(spread) || spread<=0.0 || spread>MAX_SPREAD_USD)
      return;

   bool long_absorption=(g_window_net_pressure<=-MIN_NET_SIGNED_PRESSURE &&
                         mid_move>=-ABSORPTION_MID_ATR*atr);
   bool short_absorption=(g_window_net_pressure>=MIN_NET_SIGNED_PRESSURE &&
                          mid_move<=ABSORPTION_MID_ATR*atr);
   if(long_absorption==short_absorption)
      return;
   RegisterSignal(long_absorption,decision_time,g_window_net_pressure,
                  g_window_events,mid_move,atr,spread);
  }

void ProcessValidTick(const MqlTick &tick)
  {
   datetime minute_start=(datetime)(((long)tick.time/60)*60);
   if(g_current_minute_start==0)
     {
      g_current_minute_start=minute_start;
      g_current_minute_has_valid_quote=true;
     }
   else if(minute_start>g_current_minute_start)
     {
      long elapsed_minutes=((long)minute_start-(long)g_current_minute_start)/60;
      if(elapsed_minutes==1 && g_current_minute_has_valid_quote)
         EvaluateClosedMinute(minute_start,tick);
      else
        {
         if(elapsed_minutes>1)
            g_gap_minutes+=elapsed_minutes-1;
         ClearQuoteQueue();
         g_have_previous=false;
        }
      g_current_minute_start=minute_start;
      g_current_minute_has_valid_quote=true;
     }
   else if(minute_start<g_current_minute_start)
     {
      g_reverse_time_ticks++;
      return;
     }

   double mid=(tick.bid+tick.ask)*0.5;
   int net_delta=0;
   int event_count=0;
   if(g_have_previous)
     {
      if(tick.time_msc<g_previous_time_msc)
        {
         g_reverse_time_ticks++;
         return;
        }
      if(tick.time_msc==g_previous_time_msc)
         g_duplicate_time_ticks++;

      int bid_step=SignedStep(tick.bid-g_previous_bid);
      int ask_step=SignedStep(tick.ask-g_previous_ask);
      event_count=(bid_step!=0 ? 1 : 0)+(ask_step!=0 ? 1 : 0);
      if(event_count==0)
         g_exact_duplicate_quotes++;
      // BidPressure - AskPressure = sign(deltaBid) + sign(deltaAsk).
      net_delta=bid_step+ask_step;
     }
   if(!AppendQuote(tick.time_msc,mid,net_delta,event_count))
      return;
   g_previous_time_msc=tick.time_msc;
   g_previous_bid=tick.bid;
   g_previous_ask=tick.ask;
   g_previous_mid=mid;
   g_have_previous=true;
  }

int MedianAbsPressure()
  {
   int size=ArraySize(g_signal_abs_pressure);
   if(size<=0)
      return 0;
   ArraySort(g_signal_abs_pressure);
   if((size%2)==1)
      return g_signal_abs_pressure[size/2];
   return (g_signal_abs_pressure[size/2-1]+g_signal_abs_pressure[size/2])/2;
  }

int OnInit()
  {
   if(!InpCollectionOnly || _Symbol!=EXPECTED_SYMBOL || _Period!=PERIOD_M1)
     {
      PrintFormat("SQA_SOURCE_IDENTITY_FAIL expected=%s/M1 collection_only=true actual=%s/%d",
                  EXPECTED_SYMBOL,_Symbol,(int)_Period);
      return INIT_FAILED;
     }
   if(ArrayResize(g_queue_time_msc,QUEUE_CAPACITY)!=QUEUE_CAPACITY ||
      ArrayResize(g_queue_mid,QUEUE_CAPACITY)!=QUEUE_CAPACITY ||
      ArrayResize(g_queue_net_delta,QUEUE_CAPACITY)!=QUEUE_CAPACITY ||
      ArrayResize(g_queue_event_count,QUEUE_CAPACITY)!=QUEUE_CAPACITY)
     {
      Print("SQA_SOURCE_QUEUE_ALLOCATION_FAIL");
      return INIT_FAILED;
     }
   g_atr_handle=iATR(_Symbol,PERIOD_M1,ATR_PERIOD);
   if(g_atr_handle==INVALID_HANDLE)
     {
      PrintFormat("SQA_SOURCE_ATR_INIT_FAIL error=%d",GetLastError());
      return INIT_FAILED;
     }
   ArrayInitialize(g_year_signals,0);
   PrintFormat("SQA_SOURCE_READY hypothesis_id=%s symbol=%s timeframe=M1 window_ms=%d net_threshold=%d mid_atr=%.2f warmup=%d collection_only=true orders_sent=0",
               HYPOTHESIS_ID,_Symbol,WINDOW_MILLISECONDS,MIN_NET_SIGNED_PRESSURE,
               ABSORPTION_MID_ATR,WARMUP_M1_BARS);
   return INIT_SUCCEEDED;
  }

void OnTick()
  {
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick))
      return;
   g_total_ticks++;
   if(!QuoteValid(tick))
     {
      g_invalid_quote_ticks++;
      return;
     }
   g_valid_quote_ticks++;
   ProcessValidTick(tick);
  }

void OnDeinit(const int reason)
  {
   int median_abs_pressure=MedianAbsPressure();
   long expected_m1=Bars(_Symbol,PERIOD_M1,D'2018.01.01 00:00',D'2022.01.01 00:00');
   double minute_coverage=(expected_m1>0)
                          ? (double)g_completed_valid_m1/(double)expected_m1 : 0.0;
   double valid_quote_ratio=(g_total_ticks>0)
                            ? (double)g_valid_quote_ticks/(double)g_total_ticks : 0.0;
   bool years_pass=true;
   for(int i=0;i<4;i++)
      if(g_year_signals[i]<MIN_YEAR_SIGNALS)
         years_pass=false;
   bool source_gate_pass=(minute_coverage>=0.98 && valid_quote_ratio>=0.98 &&
                          g_signal_count>=MIN_DESIGN_SIGNALS &&
                          median_abs_pressure>=MIN_SIGNAL_MEDIAN_ABS_PRESSURE &&
                          years_pass && !g_queue_overflow &&
                          g_reverse_time_ticks==0);
   PrintFormat("SQA_SOURCE_SUMMARY hypothesis_id=%s signals=%I64d long=%I64d short=%I64d y2018=%I64d y2019=%I64d y2020=%I64d y2021=%I64d median_abs_pressure=%d completed_valid_m1=%I64d expected_m1=%I64d minute_coverage=%.8f total_ticks=%I64d valid_quote_ticks=%I64d invalid_quote_ticks=%I64d valid_quote_ratio=%.8f duplicate_time_ticks=%I64d exact_duplicate_quotes=%I64d reverse_time_ticks=%I64d gap_minutes=%I64d queue_overflow=%s source_gate_pass=%s orders_sent=0 reason=%d",
               HYPOTHESIS_ID,g_signal_count,g_long_signals,g_short_signals,
               g_year_signals[0],g_year_signals[1],g_year_signals[2],g_year_signals[3],
               median_abs_pressure,g_completed_valid_m1,expected_m1,minute_coverage,
               g_total_ticks,g_valid_quote_ticks,g_invalid_quote_ticks,valid_quote_ratio,
               g_duplicate_time_ticks,g_exact_duplicate_quotes,g_reverse_time_ticks,
               g_gap_minutes,(string)g_queue_overflow,(string)source_gate_pass,reason);
   if(g_atr_handle!=INVALID_HANDLE)
      IndicatorRelease(g_atr_handle);
  }

// Collection-only by construction: no OrderSend, position or deal APIs.
//+------------------------------------------------------------------+

