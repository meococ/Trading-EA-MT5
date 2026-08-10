//+------------------------------------------------------------------+
//| EA_TickFlowCVDProbe.mq5                                          |
//| HYP-TFCVD-XAUUSD-M5-001 — collection only                       |
//| Broker quote-tick delta / absorption source feasibility.         |
//+------------------------------------------------------------------+
#property copyright "AlphaFactory research"
#property version   "1.00"
#property strict
#property description "Collection-only XAUUSD M5 quote-tick delta probe"

input bool   InpCollectionOnly=true;
input string InpHypothesisId="HYP-TFCVD-XAUUSD-M5-001";
input string InpExpectedSymbol="XAUUSD";
input int    InpExpectedPeriodMinutes=5;

const string EA_NAME="EA_TickFlowCVDProbe";
const string SCHEMA_VERSION="alphafactory.tick_flow_cvd_source.v1";
const string TELEMETRY_PROFILE="none";

string   g_run_id="";
string   g_csv_name="";
int      g_csv_handle=INVALID_HANDLE;
datetime g_bar_start=0;
datetime g_previous_emitted_bar=0;

long   g_total_ticks=0;
long   g_valid_quote_ticks=0;
long   g_invalid_ticks=0;
long   g_exact_duplicate_ticks=0;
long   g_unique_quote_updates=0;
long   g_classified_updates=0;
long   g_up_updates=0;
long   g_down_updates=0;
long   g_zero_mid_updates=0;
long   g_unclassified_updates=0;
long   g_quote_tick_delta=0;
long   g_delta_high=0;
long   g_delta_low=0;
long   g_trade_flag_ticks=0;
long   g_buy_flag_ticks=0;
long   g_sell_flag_ticks=0;
long   g_positive_volume_ticks=0;
double g_spread_sum_points=0.0;
double g_spread_max_points=0.0;
double g_mid_open=0.0;
double g_mid_high=0.0;
double g_mid_low=0.0;
double g_mid_close=0.0;

bool   g_have_previous_quote=false;
double g_previous_bid=0.0;
double g_previous_ask=0.0;
double g_previous_mid=0.0;
int    g_last_nonzero_sign=0;
long   g_emitted_bars=0;
long   g_out_of_order_ticks=0;

bool IdentityOk()
  {
   return InpCollectionOnly &&
          InpHypothesisId=="HYP-TFCVD-XAUUSD-M5-001" &&
          InpExpectedSymbol=="XAUUSD" &&
          _Symbol==InpExpectedSymbol &&
          InpExpectedPeriodMinutes==5 &&
          _Period==PERIOD_M5;
  }

bool QuoteValid(const MqlTick &tick)
  {
   if(!MathIsValidNumber(tick.bid) || !MathIsValidNumber(tick.ask))
      return false;
   if(tick.bid<=0.0 || tick.ask<=0.0 || tick.ask<tick.bid)
      return false;
   return true;
  }

datetime M5Start(const datetime tick_time)
  {
   return (datetime)(((long)tick_time/300)*300);
  }

void ResetBarCounters(const datetime bar_start)
  {
   g_bar_start=bar_start;
   g_total_ticks=0;
   g_valid_quote_ticks=0;
   g_invalid_ticks=0;
   g_exact_duplicate_ticks=0;
   g_unique_quote_updates=0;
   g_classified_updates=0;
   g_up_updates=0;
   g_down_updates=0;
   g_zero_mid_updates=0;
   g_unclassified_updates=0;
   g_quote_tick_delta=0;
   g_delta_high=0;
   g_delta_low=0;
   g_trade_flag_ticks=0;
   g_buy_flag_ticks=0;
   g_sell_flag_ticks=0;
   g_positive_volume_ticks=0;
   g_spread_sum_points=0.0;
   g_spread_max_points=0.0;
   g_mid_open=0.0;
   g_mid_high=0.0;
   g_mid_low=0.0;
   g_mid_close=0.0;
  }

bool OpenTelemetry()
  {
   g_run_id=StringFormat("%s_%I64d_%u",InpHypothesisId,(long)TimeGMT(),(uint)GetTickCount());
   g_csv_name=StringFormat("%s_TickFlow_StateTelemetry_%s.csv",_Symbol,g_run_id);
   g_csv_handle=FileOpen(g_csv_name,FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_REWRITE,',');
   if(g_csv_handle==INVALID_HANDLE)
     {
      PrintFormat("TFCVD_FILE_OPEN_FAIL name=%s error=%d",g_csv_name,GetLastError());
      return false;
     }
   FileWrite(g_csv_handle,
             "schema_version","hypothesis_id","run_id","symbol","timeframe",
             "bar_start_server","bar_end_server","gap_from_prev_bars",
             "total_ticks","valid_quote_ticks","invalid_ticks","exact_duplicate_ticks",
             "unique_quote_updates","classified_updates","up_updates","down_updates",
             "zero_mid_updates","unclassified_updates","quote_tick_delta","delta_high","delta_low",
             "mid_open","mid_high","mid_low","mid_close","mid_range_points",
             "spread_mean_points","spread_max_points","trade_flag_ticks","buy_flag_ticks",
             "sell_flag_ticks","positive_volume_ticks","bar_complete","promotion_eligible");
   FileFlush(g_csv_handle);
   return true;
  }

void FinalizeBar()
  {
   if(g_bar_start<=0 || g_csv_handle==INVALID_HANDLE || g_valid_quote_ticks<=0)
      return;
   double spread_mean=(g_valid_quote_ticks>0)
                      ? g_spread_sum_points/(double)g_valid_quote_ticks : 0.0;
   double mid_range_points=(_Point>0.0) ? (g_mid_high-g_mid_low)/_Point : 0.0;
   long gap_bars=0;
   if(g_previous_emitted_bar>0 && g_bar_start>g_previous_emitted_bar)
      gap_bars=((long)g_bar_start-(long)g_previous_emitted_bar)/300-1;
   FileWrite(g_csv_handle,
             SCHEMA_VERSION,InpHypothesisId,g_run_id,_Symbol,"M5",
             TimeToString(g_bar_start,TIME_DATE|TIME_SECONDS),
             TimeToString(g_bar_start+300,TIME_DATE|TIME_SECONDS),
             IntegerToString(gap_bars),IntegerToString(g_total_ticks),
             IntegerToString(g_valid_quote_ticks),IntegerToString(g_invalid_ticks),
             IntegerToString(g_exact_duplicate_ticks),IntegerToString(g_unique_quote_updates),
             IntegerToString(g_classified_updates),IntegerToString(g_up_updates),
             IntegerToString(g_down_updates),IntegerToString(g_zero_mid_updates),
             IntegerToString(g_unclassified_updates),IntegerToString(g_quote_tick_delta),
             IntegerToString(g_delta_high),IntegerToString(g_delta_low),
             DoubleToString(g_mid_open,_Digits+1),DoubleToString(g_mid_high,_Digits+1),
             DoubleToString(g_mid_low,_Digits+1),DoubleToString(g_mid_close,_Digits+1),
             DoubleToString(mid_range_points,4),DoubleToString(spread_mean,4),
             DoubleToString(g_spread_max_points,4),IntegerToString(g_trade_flag_ticks),
             IntegerToString(g_buy_flag_ticks),IntegerToString(g_sell_flag_ticks),
             IntegerToString(g_positive_volume_ticks),"true","false");
   FileFlush(g_csv_handle);
   g_previous_emitted_bar=g_bar_start;
   g_emitted_bars++;
  }

void ProcessTick(const MqlTick &tick)
  {
   g_total_ticks++;
   if((tick.flags&TICK_FLAG_LAST)!=0 || (tick.flags&TICK_FLAG_VOLUME)!=0)
      g_trade_flag_ticks++;
   if((tick.flags&TICK_FLAG_BUY)!=0)
      g_buy_flag_ticks++;
   if((tick.flags&TICK_FLAG_SELL)!=0)
      g_sell_flag_ticks++;
   if(tick.volume>0 || tick.volume_real>0.0)
      g_positive_volume_ticks++;
   if(!QuoteValid(tick))
     {
      g_invalid_ticks++;
      return;
     }
   g_valid_quote_ticks++;
   double spread_points=(_Point>0.0) ? (tick.ask-tick.bid)/_Point : 0.0;
   g_spread_sum_points+=spread_points;
   if(spread_points>g_spread_max_points)
      g_spread_max_points=spread_points;
   double mid=(tick.bid+tick.ask)*0.5;
   if(g_mid_open<=0.0)
     {
      g_mid_open=mid;
      g_mid_high=mid;
      g_mid_low=mid;
     }
   if(mid>g_mid_high)
      g_mid_high=mid;
   if(mid<g_mid_low)
      g_mid_low=mid;
   g_mid_close=mid;

   if(g_have_previous_quote && tick.bid==g_previous_bid && tick.ask==g_previous_ask)
     {
      g_exact_duplicate_ticks++;
      return;
     }
   g_unique_quote_updates++;
   int sign=0;
   if(g_have_previous_quote)
     {
      if(mid>g_previous_mid)
        {
         sign=1;
         g_last_nonzero_sign=1;
         g_up_updates++;
        }
      else if(mid<g_previous_mid)
        {
         sign=-1;
         g_last_nonzero_sign=-1;
         g_down_updates++;
        }
      else
        {
         g_zero_mid_updates++;
         sign=g_last_nonzero_sign;
         if(sign==0)
            g_unclassified_updates++;
        }
     }
   else
     {
      g_unclassified_updates++;
     }
   if(sign!=0)
      g_classified_updates++;
   g_quote_tick_delta+=sign;
   if(g_quote_tick_delta>g_delta_high)
      g_delta_high=g_quote_tick_delta;
   if(g_quote_tick_delta<g_delta_low)
      g_delta_low=g_quote_tick_delta;
   g_previous_bid=tick.bid;
   g_previous_ask=tick.ask;
   g_previous_mid=mid;
   g_have_previous_quote=true;
  }

int OnInit()
  {
   if(!IdentityOk())
     {
      Print("TFCVD_IDENTITY_FAIL require exact HYP-TFCVD-XAUUSD-M5-001 XAUUSD M5 collection-only");
      return INIT_FAILED;
     }
   if(!OpenTelemetry())
      return INIT_FAILED;
   PrintFormat("TFCVD_READY hypothesis_id=%s symbol=%s timeframe=M5 model_requires_real_ticks=true collection_only=true telemetry_profile=%s",
               InpHypothesisId,_Symbol,TELEMETRY_PROFILE);
   return INIT_SUCCEEDED;
  }

void OnTick()
  {
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick))
      return;
   datetime bar_start=M5Start(tick.time);
   if(bar_start<=0)
      return;
   if(g_bar_start==0)
      ResetBarCounters(bar_start);
   else if(bar_start<g_bar_start)
     {
      g_out_of_order_ticks++;
      return;
     }
   else if(bar_start>g_bar_start)
     {
      FinalizeBar();
      ResetBarCounters(bar_start);
     }
   ProcessTick(tick);
  }

void OnDeinit(const int reason)
  {
   // The last open bar is intentionally not emitted: no later M5 bar proved it complete.
   if(g_csv_handle!=INVALID_HANDLE)
     {
      FileFlush(g_csv_handle);
      FileClose(g_csv_handle);
      g_csv_handle=INVALID_HANDLE;
     }
   PrintFormat("TFCVD_SUMMARY hypothesis_id=%s emitted_bars=%I64d out_of_order_ticks=%I64d final_open_bar_omitted=true reason=%d",
               InpHypothesisId,g_emitted_bars,g_out_of_order_ticks,reason);
  }

// Collection only by construction: no trade request, order, position or deal hooks.
