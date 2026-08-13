//+------------------------------------------------------------------+
//| EA_TickSpread_XAU_V10R1.mq5                                     |
//| HYP-TSDR-XAUUSD-TICK-002: D0-compatible tick fidelity repair    |
//| Phase P0: native-tick fidelity preflight, no trading             |
//+------------------------------------------------------------------+
#property strict
#property version "1.00"
#property description "XAUUSD native-tick fidelity preflight for tick spread dislocation research"

input group "--- Frozen authority ---"
input bool   InpResearchAutoMode=false;
input bool   InpEnableTelemetry=true;
input string InpHypothesisId="HYP-TSDR-XAUUSD-TICK-002";
input string InpVariantTag="PREFLIGHT_ONLY";
input bool   InpPreflightOnly=true;

input group "--- Frozen fidelity contract ---"
input int    InpRequiredBrokerDays=5;
input double InpInvalidQuoteMaxPct=0.30;
input double InpNonMonotonicMaxPct=0.10;
input double InpDuplicateMaxPct=15.00;
input double InpMinMedianSpreadRaw=0.05;
input double InpMaxMedianSpreadRaw=3.00;
input int    InpLongZeroRunMinTicks=40;
input double InpLongZeroRunMaxPct=40.00;
input int    InpHistogramMaxPoints=100000;
input long   InpMagic=5605602;

const string EA_NAME="EA_TickSpread_XAU_V10R1";
const string EXPECTED_HYPOTHESIS="HYP-TSDR-XAUUSD-TICK-002";
const string PREFLIGHT_VARIANT="PREFLIGHT_ONLY";
#define HIST_CAP 100000

long g_spread_hist[HIST_CAP+1];
long g_total_ticks=0,g_valid_quotes=0,g_invalid_quotes=0,g_non_monotonic=0,g_same_time=0;
long g_distribution_ticks=0,g_spread_changes=0,g_long_run_ticks=0,g_hist_overflow=0;
long g_last_present=0,g_volume_present=0,g_max_gap_ms=0;
long g_last_time_msc=0;
double g_last_bid=0.0,g_last_ask=0.0;
int g_last_spread_points=-1,g_run_length=0,g_current_day=0,g_distinct_days=0;
bool g_finalized=false,g_passed=false,g_runtime_failed=false;

double SafePct(const long n,const long d){return(d>0?100.0*(double)n/(double)d:0.0);}

int DayKeyMs(const long time_msc)
  {
   if(time_msc<=0)return(0);
   MqlDateTime p;
   if(!TimeToStruct((datetime)(time_msc/1000),p))return(0);
   return(p.year*10000+p.mon*100+p.day);
  }

bool EmitSeriesProof()
  {
   long sync=0,m5first=0,m5terminal=0,m1server=0,m1terminal=0,bars=0;
   if(!SeriesInfoInteger(_Symbol,PERIOD_M5,SERIES_SYNCHRONIZED,sync)||
      !SeriesInfoInteger(_Symbol,PERIOD_M5,SERIES_FIRSTDATE,m5first)||
      !SeriesInfoInteger(_Symbol,PERIOD_M5,SERIES_TERMINAL_FIRSTDATE,m5terminal)||
      !SeriesInfoInteger(_Symbol,PERIOD_M1,SERIES_SERVER_FIRSTDATE,m1server)||
      !SeriesInfoInteger(_Symbol,PERIOD_M1,SERIES_TERMINAL_FIRSTDATE,m1terminal)||
      !SeriesInfoInteger(_Symbol,PERIOD_M5,SERIES_BARS_COUNT,bars))return(false);
   const long maxbars=TerminalInfoInteger(TERMINAL_MAXBARS);
   datetime a[];ArraySetAsSeries(a,false);ResetLastError();
   const int n=CopyTime(_Symbol,PERIOD_M5,(datetime)m5first,1,a);
   const int err=GetLastError();
   const long copied=(n==1?(long)a[0]:0);
   PrintFormat("DATA_EPOCH_D0_SERIES_PROOF symbol=%s m5_synchronized=%I64d m5_first_epoch=%I64d m5_terminal_first_epoch=%I64d m1_server_first_epoch=%I64d m1_terminal_first_epoch=%I64d m5_bars=%I64d terminal_maxbars=%I64d copytime_from_epoch=%I64d copytime_count=1 copytime_result=%d copytime_first_epoch=%I64d copytime_last_error=%d",_Symbol,sync,m5first,m5terminal,m1server,m1terminal,bars,maxbars,m5first,n,copied,err);
   return(sync==1&&m5first>0&&m5terminal>0&&m1server>0&&m1terminal>0&&bars>0&&maxbars>0&&n==1&&copied==m5first&&err==0);
  }

bool InputsAreFrozen()
  {
   return(InpResearchAutoMode&&InpEnableTelemetry&&InpHypothesisId==EXPECTED_HYPOTHESIS&&
          InpVariantTag==PREFLIGHT_VARIANT&&InpPreflightOnly&&InpRequiredBrokerDays==5&&
          MathAbs(InpInvalidQuoteMaxPct-.30)<1e-12&&MathAbs(InpNonMonotonicMaxPct-.10)<1e-12&&
          MathAbs(InpDuplicateMaxPct-15.0)<1e-12&&MathAbs(InpMinMedianSpreadRaw-.05)<1e-12&&
          MathAbs(InpMaxMedianSpreadRaw-3.0)<1e-12&&InpLongZeroRunMinTicks==40&&
          MathAbs(InpLongZeroRunMaxPct-40.0)<1e-12&&InpHistogramMaxPoints==HIST_CAP&&InpMagic==5605602);
  }

double HistogramQuantile(const double q)
  {
   if(g_distribution_ticks<=0)return(0.0);
   const long target=(long)MathCeil(q*(double)g_distribution_ticks);
   long cumulative=0;
   for(int i=0;i<=HIST_CAP;i++)
     {
      cumulative+=g_spread_hist[i];
      if(cumulative>=target)return((double)i*_Point);
     }
   return((double)HIST_CAP*_Point);
  }

void CloseSpreadRun()
  {
   if(g_run_length>=InpLongZeroRunMinTicks)g_long_run_ticks+=g_run_length;
   g_run_length=0;
  }

void FinalizePreflight()
  {
   if(g_finalized)return;
   CloseSpreadRun();
   const double median=HistogramQuantile(.50);
   const double p95=HistogramQuantile(.95);
   const double p99=HistogramQuantile(.99);
   const double invalid_pct=SafePct(g_invalid_quotes,g_total_ticks);
   const double nonmono_pct=SafePct(g_non_monotonic,g_total_ticks);
   const double duplicate_pct=SafePct(g_same_time,g_total_ticks);
   const double spread_change_pct=SafePct(g_spread_changes,MathMax(g_distribution_ticks-1,0));
   const double long_run_pct=SafePct(g_long_run_ticks,g_total_ticks);
   const double last_pct=SafePct(g_last_present,g_valid_quotes);
   const double volume_pct=SafePct(g_volume_present,g_valid_quotes);
   g_passed=(g_distinct_days>=InpRequiredBrokerDays&&g_distribution_ticks>0&&
             invalid_pct<=InpInvalidQuoteMaxPct&&nonmono_pct<=InpNonMonotonicMaxPct&&
             duplicate_pct<=InpDuplicateMaxPct&&median>=InpMinMedianSpreadRaw&&
             median<=InpMaxMedianSpreadRaw&&long_run_pct<=InpLongZeroRunMaxPct);
   g_finalized=true;
   PrintFormat("TSDR002_PREFLIGHT_RESULT result=%s broker_days=%d total_ticks=%I64d valid_bid_ask=%I64d invalid_quotes=%I64d invalid_pct=%.6f non_monotonic=%I64d non_monotonic_pct=%.6f same_time_ticks=%I64d duplicate_pct=%.6f distribution_ticks=%I64d median_spread_raw=%.6f p95_spread_raw=%.6f p99_spread_raw=%.6f spread_change_pct=%.6f max_gap_ms=%I64d long_zero_run_ticks=%I64d long_zero_run_pct=%.6f last_populated_pct=%.6f volume_populated_pct=%.6f hist_overflow=%I64d trading_enabled=false",(g_passed?"PASS":"DATA_FRONTIER_BLOCKED"),g_distinct_days,g_total_ticks,g_valid_quotes,g_invalid_quotes,invalid_pct,g_non_monotonic,nonmono_pct,g_same_time,duplicate_pct,g_distribution_ticks,median,p95,p99,spread_change_pct,g_max_gap_ms,g_long_run_ticks,long_run_pct,last_pct,volume_pct,g_hist_overflow);
  }

void ObserveTick(const MqlTick &tick)
  {
   if(g_finalized)return;
   const long t=tick.time_msc;
   if(t<=0){g_total_ticks++;g_invalid_quotes++;return;}
   if(g_last_time_msc>0&&t<g_last_time_msc){g_total_ticks++;g_non_monotonic++;return;}

   const int day=DayKeyMs(t);
   if(g_last_time_msc>0&&t>g_last_time_msc&&day>0&&g_current_day>0&&day!=g_current_day&&g_distinct_days>=InpRequiredBrokerDays)
     {
      FinalizePreflight();
      return;
     }

   g_total_ticks++;
   const bool quote_valid=(tick.bid>0.0&&tick.ask>tick.bid);
   if(quote_valid)g_valid_quotes++;else g_invalid_quotes++;

   if(g_last_time_msc>0&&t==g_last_time_msc)
     {
      g_same_time++;
      g_last_bid=tick.bid;g_last_ask=tick.ask;
      return;
     }

   if(day>0&&day!=g_current_day)
     {
      g_current_day=day;
      g_distinct_days++;
     }
   if(g_last_time_msc>0)g_max_gap_ms=MathMax(g_max_gap_ms,t-g_last_time_msc);
   g_last_time_msc=t;g_last_bid=tick.bid;g_last_ask=tick.ask;
   if(!quote_valid)return;

   if(tick.last>0.0)g_last_present++;
   if(tick.volume>0||tick.volume_real>0.0)g_volume_present++;
   const double spread=tick.ask-tick.bid;
   int points=(int)MathRound(spread/_Point);
   if(points<0){g_invalid_quotes++;return;}
   if(points>HIST_CAP){points=HIST_CAP;g_hist_overflow++;}
   g_spread_hist[points]++;
   g_distribution_ticks++;

   if(g_last_spread_points<0)g_run_length=1;
   else if(points==g_last_spread_points)g_run_length++;
   else
     {
      g_spread_changes++;
      CloseSpreadRun();
      g_run_length=1;
     }
   g_last_spread_points=points;
  }

int OnInit()
  {
   if(_Symbol!="XAUUSD"||_Period!=PERIOD_M1||!InputsAreFrozen())return(INIT_PARAMETERS_INCORRECT);
   if(!EmitSeriesProof())return(INIT_FAILED);
   ArrayInitialize(g_spread_hist,0);
   PrintFormat("TSDR002_INIT ea=%s hypothesis=%s variant=%s symbol=%s timeframe=M1 required_broker_days=%d preflight_only=true",EA_NAME,InpHypothesisId,InpVariantTag,_Symbol,InpRequiredBrokerDays);
   return(INIT_SUCCEEDED);
  }

void OnTick()
  {
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick)){g_total_ticks++;g_invalid_quotes++;return;}
   ObserveTick(tick);
  }

void OnDeinit(const int reason)
  {
   if(!g_finalized)
      PrintFormat("TSDR002_PREFLIGHT_INCOMPLETE reason=%d broker_days=%d required_days=%d total_ticks=%I64d distribution_ticks=%I64d",reason,g_distinct_days,InpRequiredBrokerDays,g_total_ticks,g_distribution_ticks);
   PrintFormat("TSDR002_SUMMARY reason=%d finalized=%s result=%s runtime_failed=%s broker_days=%d total_ticks=%I64d valid_bid_ask=%I64d invalid_quotes=%I64d non_monotonic=%I64d same_time_ticks=%I64d distribution_ticks=%I64d hist_overflow=%I64d",reason,(g_finalized?"true":"false"),(g_finalized?(g_passed?"PASS":"DATA_FRONTIER_BLOCKED"):"INCOMPLETE"),(g_runtime_failed?"true":"false"),g_distinct_days,g_total_ticks,g_valid_quotes,g_invalid_quotes,g_non_monotonic,g_same_time,g_distribution_ticks,g_hist_overflow);
  }
