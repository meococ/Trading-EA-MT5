//+------------------------------------------------------------------+
//| EA_CCIExpansion.mq5                                             |
//| HYP-CCI-XAUUSD-M15-001: native CCI20 +/-100 expansion           |
//+------------------------------------------------------------------+
#property strict
#property version   "1.00"
#property description "Untuned XAUUSD M15 native CCI20 momentum expansion"

input group "--- Frozen research authority ---"
input bool   InpResearchAutoMode=false;
input bool   InpEnableTelemetry=false;
input string InpHypothesisId="HYP-CCI-XAUUSD-M15-001";
input string InpVariantTag="CCI20_TYPICAL_100_EXPANSION";

input group "--- Frozen execution and risk ---"
input long   InpMagic=5604201;
input double InpRiskPercent=0.25;
input double InpMaxDailyLossPct=3.5;
input double InpMaxAccountDrawdownPct=8.0;
input int    InpMaxTradesPerDay=1;
input int    InpDeviationPoints=20;
input int    InpFridayFlattenHour=20;

const string EA_NAME="EA_CCIExpansion";
const string EXPECTED_HYPOTHESIS="HYP-CCI-XAUUSD-M15-001";
const string EXPECTED_VARIANT="CCI20_TYPICAL_100_EXPANSION";
const string EXPECTED_SYMBOL="XAUUSD";
const int    ATR_PERIOD=14;
const int    CCI_PERIOD=20;
const int    KVO_FAST_PERIOD=34;
const int    KVO_SLOW_PERIOD=55;
const int    KVO_SIGNAL_PERIOD=13;
const int    TREND_EMA_PERIOD=100;
const double STOP_BUFFER_ATR=0.20;
const double TARGET_R=1.50;
const int    MAX_HOLD_BARS=12;
const int    REQUIRED_RATES=5;
const double MARGIN_HEADROOM_RESERVE_FACTOR=0.20;
const double MARGIN_FREE_EQUITY_FLOOR=0.01;
const double MARGIN_LEVEL_FLOOR_PCT=120.0;
const datetime DESIGN_FROM=D'2018.01.01 00:00';
const datetime DESIGN_TO=D'2023.01.01 00:00';

struct SignalDecision
  {
   bool fired;
   datetime decision_time;
   datetime availability_time;
   int direction;
   double close;
   double swing_high;
   double swing_low;
   double atr;
   double cci;
   double prior_cci;
   double kvo;
   double kvo_signal;
   double ema100;
   double structural_stop;
  };

enum KvoArmState
  {
   KVO_IDLE=0,
   KVO_LONG_ARMED=1,
   KVO_SHORT_ARMED=-1
  };

datetime g_last_bar_open=0;
datetime g_last_decision_time=0;
int g_atr_handle=INVALID_HANDLE;
int g_cci_handle=INVALID_HANDLE;
bool g_indicators_ready=false;

// Legacy KVO state remains compile-isolated from the CCI execution path.
bool g_have_previous_source=false;
double g_previous_sum=0.0;
double g_previous_dm=0.0;
int g_previous_trend=-1;
double g_cm=0.0;
bool g_cm_ready=false;
long g_vf_count=0;
double g_vf_sum34=0.0;
double g_vf_sum55=0.0;
double g_ema34=0.0;
double g_ema55=0.0;
bool g_ema34_ready=false;
bool g_ema55_ready=false;
long g_ko_count=0;
double g_ko_signal_sum=0.0;
double g_ko_signal_ema=0.0;
bool g_ko_signal_ready=false;
long g_close_count=0;
double g_close_sum100=0.0;
double g_close_ema100=0.0;
bool g_close_ema100_ready=false;
double g_previous_ko=0.0;
double g_previous_ko_signal=0.0;
bool g_previous_pair_ready=false;
KvoArmState g_kvo_arm=KVO_IDLE;
datetime g_kvo_last_time=0;

int g_daily_day_key=0;
double g_daily_start_equity=0.0;
double g_peak_equity=0.0;
bool g_daily_locked=false;
bool g_drawdown_locked=false;
int g_daily_entries=0;
bool g_runtime_failed=false;

long g_closed_bars=0;
long g_invalid_bars=0;
long g_clock_rejects=0;
long g_raw_signals=0;
long g_long_signals=0;
long g_short_signals=0;
long g_entries_accepted=0;
long g_entry_rejects=0;
long g_close_requests=0;
long g_stop_updates=0;

bool IsUsable(const double value)
  {
   return(value!=EMPTY_VALUE && MathIsValidNumber(value));
  }

bool CurrentM15Open(datetime &bar_open)
  {
   long raw=0;
   bar_open=0;
   if(!SeriesInfoInteger(_Symbol,PERIOD_M15,SERIES_LASTBAR_DATE,raw) || raw<=0)
      return(false);
   bar_open=(datetime)raw;
   return(true);
  }

bool ReadSeriesInteger(const ENUM_TIMEFRAMES timeframe,
                       const ENUM_SERIES_INFO_INTEGER property,
                       long &value)
  {
   value=0;
   ResetLastError();
   if(!SeriesInfoInteger(_Symbol,timeframe,property,value))
      return(false);
   return(GetLastError()==0);
  }

bool EmitD0SeriesProof()
  {
   long m5_synchronized=0;
   long m5_first_epoch=0;
   long m5_terminal_first_epoch=0;
   long m1_server_first_epoch=0;
   long m1_terminal_first_epoch=0;
   long m5_bars=0;
   if(!ReadSeriesInteger(PERIOD_M5,SERIES_SYNCHRONIZED,m5_synchronized) ||
      !ReadSeriesInteger(PERIOD_M5,SERIES_FIRSTDATE,m5_first_epoch) ||
      !ReadSeriesInteger(PERIOD_M5,SERIES_TERMINAL_FIRSTDATE,m5_terminal_first_epoch) ||
      !ReadSeriesInteger(PERIOD_M1,SERIES_SERVER_FIRSTDATE,m1_server_first_epoch) ||
      !ReadSeriesInteger(PERIOD_M1,SERIES_TERMINAL_FIRSTDATE,m1_terminal_first_epoch) ||
      !ReadSeriesInteger(PERIOD_M5,SERIES_BARS_COUNT,m5_bars))
      return(false);

   ResetLastError();
   const long terminal_maxbars=TerminalInfoInteger(TERMINAL_MAXBARS);
   const int terminal_error=GetLastError();
   datetime copytime_values[];
   ArraySetAsSeries(copytime_values,false);
   const datetime copytime_from=(datetime)m5_first_epoch;
   ResetLastError();
   const int copytime_result=CopyTime(_Symbol,PERIOD_M5,copytime_from,1,copytime_values);
   const int copytime_error=GetLastError();
   const long copytime_first_epoch=(copytime_result==1 ? (long)copytime_values[0] : 0);

   PrintFormat("DATA_EPOCH_D0_SERIES_PROOF symbol=%s m5_synchronized=%I64d m5_first_epoch=%I64d m5_terminal_first_epoch=%I64d m1_server_first_epoch=%I64d m1_terminal_first_epoch=%I64d m5_bars=%I64d terminal_maxbars=%I64d copytime_from_epoch=%I64d copytime_count=1 copytime_result=%d copytime_first_epoch=%I64d copytime_last_error=%d",
               _Symbol,m5_synchronized,m5_first_epoch,m5_terminal_first_epoch,
               m1_server_first_epoch,m1_terminal_first_epoch,m5_bars,terminal_maxbars,
               (long)copytime_from,copytime_result,copytime_first_epoch,copytime_error);
   if(m5_synchronized!=1 || m5_first_epoch<=0 || m5_terminal_first_epoch<=0 ||
      m1_server_first_epoch<=0 || m1_terminal_first_epoch<=0 || m5_bars<=0 ||
      terminal_maxbars<=0 || terminal_error!=0 || copytime_result!=1 ||
      copytime_first_epoch!=m5_first_epoch || copytime_error!=0)
      return(false);
   return(true);
  }

int DateKey(const datetime stamp)
  {
   MqlDateTime p;
   TimeToStruct(stamp,p);
   return(p.year*10000+p.mon*100+p.day);
  }

bool ValidRate(const MqlRates &bar)
  {
   return(bar.time>0 && IsUsable(bar.open) && IsUsable(bar.high) &&
          IsUsable(bar.low) && IsUsable(bar.close) &&
          bar.high>=MathMax(bar.open,bar.close) &&
          bar.low<=MathMin(bar.open,bar.close) && bar.high>=bar.low);
  }

bool LoadClosedRates(MqlRates &rates[])
  {
   ArrayResize(rates,REQUIRED_RATES);
   const int copied=CopyRates(_Symbol,PERIOD_M15,1,REQUIRED_RATES,rates);
   if(copied!=REQUIRED_RATES)
      return(false);
   for(int i=0;i<copied;i++)
      if(!ValidRate(rates[i]))
         return(false);
   return(true);
  }

bool ReadClosedAtr(double &value)
  {
   value=EMPTY_VALUE;
   if(g_atr_handle==INVALID_HANDLE)
      return(false);
   double data[];
   const int copied=CopyBuffer(g_atr_handle,0,1,1,data);
   if(copied!=1 || !IsUsable(data[0]))
      return(false);
   value=data[0];
   return(true);
  }

bool AdvanceKvoBar(const MqlRates &bar,int &direction,
                   double &ko_value,double &signal_value,double &ema100_value)
  {
   direction=0;
   ko_value=EMPTY_VALUE;
   signal_value=EMPTY_VALUE;
   ema100_value=EMPTY_VALUE;
   if(!ValidRate(bar) || bar.tick_volume<0)
      return(false);

   g_close_count++;
   if(g_close_count<=TREND_EMA_PERIOD)
     {
      g_close_sum100+=bar.close;
      if(g_close_count==TREND_EMA_PERIOD)
        {
         g_close_ema100=g_close_sum100/(double)TREND_EMA_PERIOD;
         g_close_ema100_ready=true;
        }
     }
   else
     {
      const double alpha100=2.0/(TREND_EMA_PERIOD+1.0);
      g_close_ema100=alpha100*bar.close+(1.0-alpha100)*g_close_ema100;
     }

   const double source_sum=bar.high+bar.low+bar.close;
   const double dm=bar.high-bar.low;
   if(!IsUsable(source_sum) || !IsUsable(dm) || dm<0.0)
      return(false);
   if(!g_have_previous_source)
     {
      g_have_previous_source=true;
      g_previous_sum=source_sum;
      g_previous_dm=dm;
      return(true);
     }

   const int trend=(source_sum>g_previous_sum ? 1 : -1);
   bool vf_defined=false;
   double vf=0.0;
   if(!g_cm_ready)
     {
      const double seed_cm=g_previous_dm+dm;
      if(seed_cm>0.0)
        {
         g_cm=seed_cm;
         g_cm_ready=true;
         vf=(double)bar.tick_volume*2.0*(dm/g_cm-1.0)*(double)trend*100.0;
         vf_defined=true;
        }
     }
   else
     {
      g_cm=(trend==g_previous_trend ? g_cm+dm : g_previous_dm+dm);
      if(!IsUsable(g_cm) || g_cm<0.0)
         return(false);
      vf=(g_cm==0.0 ? 0.0
                    : (double)bar.tick_volume*2.0*(dm/g_cm-1.0)*(double)trend*100.0);
      vf_defined=true;
     }

   g_previous_sum=source_sum;
   g_previous_dm=dm;
   g_previous_trend=trend;
   if(!vf_defined)
      return(true);
   if(!IsUsable(vf))
      return(false);

   g_vf_count++;
   if(g_vf_count<=KVO_FAST_PERIOD)
     {
      g_vf_sum34+=vf;
      if(g_vf_count==KVO_FAST_PERIOD)
        {
         g_ema34=g_vf_sum34/(double)KVO_FAST_PERIOD;
         g_ema34_ready=true;
        }
     }
   else
     {
      const double alpha34=2.0/(KVO_FAST_PERIOD+1.0);
      g_ema34=alpha34*vf+(1.0-alpha34)*g_ema34;
     }
   if(g_vf_count<=KVO_SLOW_PERIOD)
     {
      g_vf_sum55+=vf;
      if(g_vf_count==KVO_SLOW_PERIOD)
        {
         g_ema55=g_vf_sum55/(double)KVO_SLOW_PERIOD;
         g_ema55_ready=true;
        }
     }
   else
     {
      const double alpha55=2.0/(KVO_SLOW_PERIOD+1.0);
      g_ema55=alpha55*vf+(1.0-alpha55)*g_ema55;
     }
   if(!g_ema34_ready || !g_ema55_ready)
      return(true);

   const double ko=g_ema34-g_ema55;
   if(!IsUsable(ko))
      return(false);
   g_ko_count++;
   if(g_ko_count<=KVO_SIGNAL_PERIOD)
     {
      g_ko_signal_sum+=ko;
      if(g_ko_count==KVO_SIGNAL_PERIOD)
        {
         g_ko_signal_ema=g_ko_signal_sum/(double)KVO_SIGNAL_PERIOD;
         g_ko_signal_ready=true;
        }
     }
   else
     {
      const double alpha13=2.0/(KVO_SIGNAL_PERIOD+1.0);
      g_ko_signal_ema=alpha13*ko+(1.0-alpha13)*g_ko_signal_ema;
     }
   if(!g_ko_signal_ready || !g_close_ema100_ready)
      return(true);

   ko_value=ko;
   signal_value=g_ko_signal_ema;
   ema100_value=g_close_ema100;
   bool consumed_state=false;
   if(g_kvo_arm==KVO_LONG_ARMED)
     {
      const bool context=(ko<=0.0 && bar.close>g_close_ema100);
      if(g_previous_pair_ready && g_previous_ko<=g_previous_ko_signal &&
         ko>g_ko_signal_ema && context)
        {
         direction=1;
         g_kvo_arm=KVO_IDLE;
         consumed_state=true;
        }
      else if(!context)
        {
         g_kvo_arm=KVO_IDLE;
         consumed_state=true;
        }
     }
   else if(g_kvo_arm==KVO_SHORT_ARMED)
     {
      const bool context=(ko>=0.0 && bar.close<g_close_ema100);
      if(g_previous_pair_ready && g_previous_ko>=g_previous_ko_signal &&
         ko<g_ko_signal_ema && context)
        {
         direction=-1;
         g_kvo_arm=KVO_IDLE;
         consumed_state=true;
        }
      else if(!context)
        {
         g_kvo_arm=KVO_IDLE;
         consumed_state=true;
        }
     }
   if(direction==0 && !consumed_state && g_kvo_arm==KVO_IDLE)
     {
      if(ko<0.0 && bar.close>g_close_ema100)
         g_kvo_arm=KVO_LONG_ARMED;
      else if(ko>0.0 && bar.close<g_close_ema100)
         g_kvo_arm=KVO_SHORT_ARMED;
     }

   g_previous_ko=ko;
   g_previous_ko_signal=g_ko_signal_ema;
   g_previous_pair_ready=true;
   return(true);
  }

bool PreloadKvoState()
  {
   long synchronized=0;
   long series_count=0;
   long first_epoch=0;
   long current_epoch=0;
   if(!ReadSeriesInteger(PERIOD_M15,SERIES_SYNCHRONIZED,synchronized) ||
      !ReadSeriesInteger(PERIOD_M15,SERIES_BARS_COUNT,series_count) ||
      !ReadSeriesInteger(PERIOD_M15,SERIES_FIRSTDATE,first_epoch) ||
      !ReadSeriesInteger(PERIOD_M15,SERIES_LASTBAR_DATE,current_epoch) ||
      synchronized!=1 || series_count<300 || first_epoch<=0 || current_epoch<=first_epoch)
      return(false);
   const int available=Bars(_Symbol,PERIOD_M15);
   if(available<300 || (long)available!=series_count)
      return(false);
   const int requested=available-1;
   MqlRates history[];
   ArraySetAsSeries(history,false);
   const int copied=CopyRates(_Symbol,PERIOD_M15,1,requested,history);
   if(copied!=requested || copied<300 || history[0].time!=(datetime)first_epoch)
      return(false);
   const datetime expected_last=iTime(_Symbol,PERIOD_M15,1);
   if(expected_last<=0 || history[copied-1].time!=expected_last ||
      expected_last>=current_epoch)
      return(false);
   for(int i=1;i<copied;i++)
      if(history[i].time<=history[i-1].time)
         return(false);
   int ignored_direction=0;
   double ignored_ko=0.0,ignored_signal=0.0,ignored_ema=0.0;
   for(int i=0;i<copied;i++)
     {
      if(!AdvanceKvoBar(history[i],ignored_direction,ignored_ko,
                        ignored_signal,ignored_ema))
         return(false);
     }
   g_kvo_last_time=history[copied-1].time;
   const bool ready=(g_cm_ready && g_ema34_ready && g_ema55_ready &&
                     g_ko_signal_ready && g_close_ema100_ready && g_kvo_last_time>0);
   PrintFormat("CCI001_LEGACY_PRELOAD synchronized=%I64d requested=%d copied=%d first=%I64d last=%I64d current=%I64d ready=%s",
               synchronized,requested,copied,(long)history[0].time,
               (long)g_kvo_last_time,current_epoch,ready ? "true" : "false");
   return(ready);
  }

bool ProcessClosedBar(const datetime availability_time,SignalDecision &signal)
  {
   ZeroMemory(signal);
   MqlRates rates[];
   if(!LoadClosedRates(rates))
     {
      g_invalid_bars++;
      g_runtime_failed=true;
       PrintFormat("CCI001_FATAL reason=LEGACY_CLOSED_RATE_LOAD availability=%I64d",
                  (long)availability_time);
      return(false);
     }
    const int release=ArraySize(rates)-1;
    const datetime decision_time=rates[release].time;
    if(decision_time<=0 || decision_time==g_last_decision_time)
       return(false);
    if(decision_time<g_kvo_last_time)
      {
       g_invalid_bars++;
       g_runtime_failed=true;
       PrintFormat("CCI001_FATAL reason=LEGACY_CLOCK_REGRESSION decision=%I64d last=%I64d",
                   (long)decision_time,(long)g_kvo_last_time);
       return(false);
      }
    g_last_decision_time=decision_time;
    g_closed_bars++;
    int direction=0;
    double ko=0.0,kvo_signal=0.0,ema100=0.0;
    if(decision_time>g_kvo_last_time)
      {
       if(!AdvanceKvoBar(rates[release],direction,ko,kvo_signal,ema100))
         {
          g_invalid_bars++;
          g_runtime_failed=true;
          PrintFormat("CCI001_FATAL reason=LEGACY_STATE decision=%I64d",(long)decision_time);
          return(false);
         }
       g_kvo_last_time=decision_time;
      }
    if(decision_time<DESIGN_FROM || decision_time>=DESIGN_TO || availability_time>=DESIGN_TO)
       return(false);
    if(direction==0)
       return(false);
    g_raw_signals++;
    if(direction>0)
       g_long_signals++;
    else
       g_short_signals++;
    if((long)(availability_time-decision_time)!=900)
      {
       g_clock_rejects++;
       return(false);
      }

    double atr_release=0.0;
    if(!ReadClosedAtr(atr_release) || atr_release<=0.0)
      {
       g_invalid_bars++;
       g_runtime_failed=true;
       PrintFormat("CCI001_FATAL reason=LEGACY_ATR_LOAD decision=%I64d",
                   (long)decision_time);
       return(false);
      }
    const double swing_low=MathMin(rates[release].low,
                                   MathMin(rates[release-1].low,rates[release-2].low));
    const double swing_high=MathMax(rates[release].high,
                                    MathMax(rates[release-1].high,rates[release-2].high));
    const double stop=(direction>0
                       ? swing_low-STOP_BUFFER_ATR*atr_release
                       : swing_high+STOP_BUFFER_ATR*atr_release);
    if(!IsUsable(stop))
     {
      g_invalid_bars++;
      return(false);
     }

   signal.fired=true;
   signal.decision_time=decision_time;
    signal.availability_time=availability_time;
    signal.direction=direction;
    signal.close=rates[release].close;
    signal.swing_high=swing_high;
    signal.swing_low=swing_low;
    signal.atr=atr_release;
    signal.kvo=ko;
    signal.kvo_signal=kvo_signal;
    signal.ema100=ema100;
    signal.structural_stop=stop;
    return(true);
  }

bool PreloadCciState()
  {
   if(g_cci_handle==INVALID_HANDLE || g_atr_handle==INVALID_HANDLE)
      return(false);
   const int cci_bars=BarsCalculated(g_cci_handle);
   const int atr_bars=BarsCalculated(g_atr_handle);
   if(cci_bars<CCI_PERIOD+2 || atr_bars<ATR_PERIOD+2)
      return(false);

   double cci_values[];
   double atr_values[];
   ArraySetAsSeries(cci_values,false);
   ArraySetAsSeries(atr_values,false);
   const int sample=16;
   if(CopyBuffer(g_cci_handle,0,1,sample,cci_values)!=sample ||
      CopyBuffer(g_atr_handle,0,1,sample,atr_values)!=sample)
      return(false);
   for(int i=0;i<sample;i++)
      if(!IsUsable(cci_values[i]) || !IsUsable(atr_values[i]) || atr_values[i]<=0.0)
         return(false);

   PrintFormat("CCI001_PRELOAD cci_bars=%d atr_bars=%d sample=%d latest_cci=%.8f latest_atr=%.8f",
               cci_bars,atr_bars,sample,cci_values[sample-1],atr_values[sample-1]);
   return(true);
  }

bool ReadClosedCciAndAtr(double &current_cci,double &prior_cci,double &current_atr)
  {
   current_cci=EMPTY_VALUE;
   prior_cci=EMPTY_VALUE;
   current_atr=EMPTY_VALUE;
   if(g_cci_handle==INVALID_HANDLE || g_atr_handle==INVALID_HANDLE)
      return(false);

   double cci_values[];
   double atr_values[];
   ArraySetAsSeries(cci_values,false);
   ArraySetAsSeries(atr_values,false);
   if(CopyBuffer(g_cci_handle,0,1,2,cci_values)!=2 ||
      CopyBuffer(g_atr_handle,0,1,1,atr_values)!=1)
      return(false);
   prior_cci=cci_values[0];
   current_cci=cci_values[1];
   current_atr=atr_values[0];
   return(IsUsable(prior_cci) && IsUsable(current_cci) &&
          IsUsable(current_atr) && current_atr>0.0);
  }

bool ProcessCciClosedBar(const datetime availability_time,SignalDecision &signal)
  {
   ZeroMemory(signal);
   MqlRates rates[];
   if(!LoadClosedRates(rates))
     {
      g_invalid_bars++;
      g_runtime_failed=true;
      PrintFormat("CCI001_FATAL reason=CLOSED_RATE_LOAD availability=%I64d",
                  (long)availability_time);
      return(false);
     }

   const int release=ArraySize(rates)-1;
   const int prior=release-1;
   const datetime decision_time=rates[release].time;
   if(decision_time<=0 || decision_time==g_last_decision_time)
      return(false);
   if(g_last_decision_time>0 && decision_time<g_last_decision_time)
     {
      g_invalid_bars++;
      g_runtime_failed=true;
      PrintFormat("CCI001_FATAL reason=DECISION_CLOCK_REGRESSION decision=%I64d last=%I64d",
                  (long)decision_time,(long)g_last_decision_time);
      return(false);
     }
   g_last_decision_time=decision_time;
   g_closed_bars++;

   if(decision_time<DESIGN_FROM || decision_time>=DESIGN_TO ||
      availability_time>=DESIGN_TO)
      return(false);

   double current_cci=0.0;
   double prior_cci=0.0;
   double current_atr=0.0;
   if(!ReadClosedCciAndAtr(current_cci,prior_cci,current_atr))
     {
      g_invalid_bars++;
      g_runtime_failed=true;
      PrintFormat("CCI001_FATAL reason=INDICATOR_LOAD decision=%I64d",
                  (long)decision_time);
      return(false);
     }

   int direction=0;
   if(prior_cci<=100.0 && current_cci>100.0)
      direction=1;
   else if(prior_cci>=-100.0 && current_cci<-100.0)
      direction=-1;
   if(direction==0)
      return(false);

   g_raw_signals++;
   if(direction>0)
      g_long_signals++;
   else
      g_short_signals++;
   if((long)(availability_time-decision_time)!=900)
     {
      g_clock_rejects++;
      return(false);
     }

   double swing_low=rates[0].low;
   double swing_high=rates[0].high;
   for(int i=1;i<ArraySize(rates);i++)
     {
      swing_low=MathMin(swing_low,rates[i].low);
      swing_high=MathMax(swing_high,rates[i].high);
     }
   const double stop=(direction>0
                      ? swing_low-STOP_BUFFER_ATR*current_atr
                      : swing_high+STOP_BUFFER_ATR*current_atr);
   if(!IsUsable(stop))
     {
      g_invalid_bars++;
      g_runtime_failed=true;
      return(false);
     }

   signal.fired=true;
   signal.decision_time=decision_time;
   signal.availability_time=availability_time;
   signal.direction=direction;
   signal.close=rates[release].close;
   signal.swing_high=swing_high;
   signal.swing_low=swing_low;
   signal.atr=current_atr;
   signal.cci=current_cci;
   signal.prior_cci=prior_cci;
   signal.structural_stop=stop;
   return(true);
  }

int VolumeDigits(const double step)
  {
   int digits=0;
   double scaled=step;
   while(digits<8 && MathAbs(scaled-MathRound(scaled))>1e-9)
     {
      scaled*=10.0;
      digits++;
     }
   return(digits);
  }

double FloorToTick(const double price)
  {
   ResetLastError();
   const double tick_size=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);
   if(GetLastError()!=0 || !IsUsable(tick_size) || tick_size<=0.0)
     {
      g_runtime_failed=true;
      Print("CCI001_FATAL reason=TICK_SIZE_PROPERTY");
      return(EMPTY_VALUE);
     }
   return(NormalizeDouble(MathFloor(price/tick_size+1e-9)*tick_size,_Digits));
  }

double CeilToTick(const double price)
  {
   ResetLastError();
   const double tick_size=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);
   if(GetLastError()!=0 || !IsUsable(tick_size) || tick_size<=0.0)
     {
      g_runtime_failed=true;
      Print("CCI001_FATAL reason=TICK_SIZE_PROPERTY");
      return(EMPTY_VALUE);
     }
   return(NormalizeDouble(MathCeil(price/tick_size-1e-9)*tick_size,_Digits));
  }

ENUM_ORDER_TYPE_FILLING ResolveFilling()
  {
   return(ORDER_FILLING_FOK);
  }

bool AcceptedRetcode(const uint retcode)
  {
   return(retcode==TRADE_RETCODE_DONE);
  }

bool OwnedPositionCount(int &count)
  {
   count=0;
   for(int i=PositionsTotal()-1;i>=0;i--)
     {
      const ulong ticket=PositionGetTicket(i);
      if(ticket==0 || !PositionSelectByTicket(ticket))
         return(false);
      ResetLastError();
      const string symbol=PositionGetString(POSITION_SYMBOL);
      const long magic=PositionGetInteger(POSITION_MAGIC);
      if(GetLastError()!=0)
         return(false);
      if(symbol==_Symbol && magic==InpMagic)
         count++;
     }
   return(true);
  }

bool OwnedOrderCount(int &count)
  {
   count=0;
   for(int i=OrdersTotal()-1;i>=0;i--)
     {
      const ulong ticket=OrderGetTicket(i);
      if(ticket==0 || !OrderSelect(ticket))
         return(false);
      ResetLastError();
      const string symbol=OrderGetString(ORDER_SYMBOL);
      const long magic=OrderGetInteger(ORDER_MAGIC);
      if(GetLastError()!=0)
         return(false);
      if(symbol==_Symbol && magic==InpMagic)
         count++;
     }
   return(true);
  }

bool ClosePositionTicket(const ulong ticket,const string reason)
  {
   if(ticket==0 || !PositionSelectByTicket(ticket))
     {
      g_runtime_failed=true;
       PrintFormat("CCI001_FATAL reason=CLOSE_POSITION_SELECT ticket=%I64u",ticket);
      return(false);
     }
   ResetLastError();
   const long position_type=PositionGetInteger(POSITION_TYPE);
   const double volume=PositionGetDouble(POSITION_VOLUME);
   const int property_error=GetLastError();
   MqlTick tick;
   if(property_error!=0 ||
      (position_type!=POSITION_TYPE_BUY && position_type!=POSITION_TYPE_SELL) ||
      !IsUsable(volume) || volume<=0.0 || !SymbolInfoTick(_Symbol,tick))
     {
      g_runtime_failed=true;
       PrintFormat("CCI001_FATAL reason=CLOSE_POSITION_PROPERTIES ticket=%I64u error=%d type=%d volume=%.8f",
                  ticket,property_error,(int)position_type,volume);
      return(false);
     }

   MqlTradeRequest request;
   MqlTradeResult result;
   ZeroMemory(request);
   ZeroMemory(result);
   request.action=TRADE_ACTION_DEAL;
   request.position=ticket;
   request.symbol=_Symbol;
   request.magic=InpMagic;
   request.volume=volume;
   request.deviation=InpDeviationPoints;
   request.type_filling=ResolveFilling();
   request.comment=reason;
   if(position_type==POSITION_TYPE_BUY)
     {
      request.type=ORDER_TYPE_SELL;
      request.price=tick.bid;
     }
   else
     {
      request.type=ORDER_TYPE_BUY;
      request.price=tick.ask;
     }
   if(!OrderSend(request,result) || !AcceptedRetcode(result.retcode))
     {
      g_runtime_failed=true;
       PrintFormat("CCI001_CLOSE_REJECT ticket=%I64u retcode=%u error=%d reason=%s",
                  ticket,result.retcode,GetLastError(),reason);
      return(false);
     }
   g_close_requests++;
   return(true);
  }

void UpdateRiskLocks(const datetime now)
  {
   const double equity=AccountInfoDouble(ACCOUNT_EQUITY);
   if(!IsUsable(equity) || equity<=0.0)
     {
      g_runtime_failed=true;
      return;
     }
   const int day_key=DateKey(now);
   if(day_key!=g_daily_day_key)
     {
      g_daily_day_key=day_key;
      g_daily_start_equity=equity;
      g_daily_locked=false;
      g_daily_entries=0;
     }
   if(g_peak_equity<=0.0 || equity>g_peak_equity)
      g_peak_equity=equity;
   if(g_daily_start_equity>0.0 &&
      equity<=g_daily_start_equity*(1.0-InpMaxDailyLossPct/100.0))
      g_daily_locked=true;
   if(g_peak_equity>0.0 &&
      equity<=g_peak_equity*(1.0-InpMaxAccountDrawdownPct/100.0))
      g_drawdown_locked=true;
  }

bool WeekendEntryBlocked(const datetime now)
  {
   MqlDateTime p;
   TimeToStruct(now,p);
   if(p.day_of_week==0 || p.day_of_week==6)
      return(true);
   return(p.day_of_week==5 && p.hour>=InpFridayFlattenHour);
  }

bool ManageOwnedPositions(const datetime now,const bool update_exit)
  {
   MqlDateTime p;
   TimeToStruct(now,p);
   const bool flatten_time=(now>=DESIGN_TO || p.day_of_week==0 ||
                            p.day_of_week==6 ||
                            (p.day_of_week==5 && p.hour>=InpFridayFlattenHour));
   for(int i=PositionsTotal()-1;i>=0;i--)
     {
      const ulong ticket=PositionGetTicket(i);
      if(ticket==0 || !PositionSelectByTicket(ticket))
        {
         g_runtime_failed=true;
         PrintFormat("CCI001_FATAL reason=POSITION_ENUMERATION index=%d",i);
         return(false);
        }
      ResetLastError();
      const string symbol=PositionGetString(POSITION_SYMBOL);
      const long magic=PositionGetInteger(POSITION_MAGIC);
      const long position_type=PositionGetInteger(POSITION_TYPE);
      const datetime position_time=(datetime)PositionGetInteger(POSITION_TIME);
      if(GetLastError()!=0 ||
         (position_type!=POSITION_TYPE_BUY && position_type!=POSITION_TYPE_SELL) ||
         position_time<=0)
        {
         g_runtime_failed=true;
         PrintFormat("CCI001_FATAL reason=POSITION_PROPERTIES ticket=%I64u",ticket);
         return(false);
        }
      if(symbol!=_Symbol || magic!=InpMagic)
         continue;
      if(flatten_time)
        {
          if(!ClosePositionTicket(ticket,"CCI_WEEKEND_OR_END"))
            return(false);
         continue;
        }
      if(update_exit)
        {
         ResetLastError();
         const int shift=iBarShift(_Symbol,PERIOD_M15,position_time,false);
         if(shift<0 || GetLastError()!=0)
           {
            g_runtime_failed=true;
             PrintFormat("CCI001_FATAL reason=ENTRY_BAR_RECOVERY ticket=%I64u",ticket);
            return(false);
           }
          if(shift>=MAX_HOLD_BARS && !ClosePositionTicket(ticket,"CCI_TIME_EXIT"))
            return(false);
        }
     }
   return(true);
  }

bool CalculateVolume(const ENUM_ORDER_TYPE order_type,const double entry,
                      const double stop,double &volume)
  {
   volume=0.0;
   double one_lot_profit=0.0;
   ResetLastError();
   if(!OrderCalcProfit(order_type,_Symbol,1.0,entry,stop,one_lot_profit) ||
      GetLastError()!=0 || !IsUsable(one_lot_profit) || one_lot_profit>=0.0)
     {
      g_runtime_failed=true;
      PrintFormat("CCI001_FATAL reason=ORDER_CALC_PROFIT error=%d value=%.8f",
                  GetLastError(),one_lot_profit);
      return(false);
     }
   ResetLastError();
   const double equity=AccountInfoDouble(ACCOUNT_EQUITY);
   const double used_margin=AccountInfoDouble(ACCOUNT_MARGIN);
   const double margin_call_level=AccountInfoDouble(ACCOUNT_MARGIN_SO_CALL);
   const double stopout_level=AccountInfoDouble(ACCOUNT_MARGIN_SO_SO);
   const ENUM_ACCOUNT_STOPOUT_MODE stopout_mode=
      (ENUM_ACCOUNT_STOPOUT_MODE)AccountInfoInteger(ACCOUNT_MARGIN_SO_MODE);
   const int account_error=GetLastError();
   if(account_error!=0 || !IsUsable(equity) || equity<=0.0 ||
      !IsUsable(used_margin) || used_margin<0.0 ||
      !IsUsable(margin_call_level) || margin_call_level<0.0 ||
      !IsUsable(stopout_level) || stopout_level<0.0 ||
      (stopout_mode!=ACCOUNT_STOPOUT_MODE_MONEY &&
       stopout_mode!=ACCOUNT_STOPOUT_MODE_PERCENT))
     {
      g_runtime_failed=true;
      PrintFormat("CCI001_FATAL reason=MARGIN_ACCOUNT_STATE error=%d mode=%d equity=%.2f margin=%.2f call=%.2f stopout=%.2f",
                  account_error,(int)stopout_mode,equity,used_margin,
                  margin_call_level,stopout_level);
      return(false);
     }
   const double risk_budget=equity*InpRiskPercent/100.0;
   const double raw_volume=risk_budget/MathAbs(one_lot_profit);
   ResetLastError();
   const double minimum=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN);
   const double maximum=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX);
   const double step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);
   const int volume_error=GetLastError();
   if(!IsUsable(raw_volume) || !IsUsable(minimum) || !IsUsable(maximum) ||
      !IsUsable(step) || minimum<=0.0 || maximum<minimum || step<=0.0 ||
      volume_error!=0)
     {
      g_runtime_failed=true;
      PrintFormat("CCI001_FATAL reason=VOLUME_PROPERTIES error=%d min=%.8f max=%.8f step=%.8f",
                  volume_error,minimum,maximum,step);
      return(false);
     }

   double allowed_new_margin=0.0;
   const double protected_level=MathMax(margin_call_level,stopout_level);
   if(stopout_mode==ACCOUNT_STOPOUT_MODE_MONEY)
     {
      if(equity<=protected_level)
         return(false);
      const double headroom=equity-protected_level;
      const double reserve=MathMax(headroom*MARGIN_HEADROOM_RESERVE_FACTOR,
                                   equity*MARGIN_FREE_EQUITY_FLOOR);
      const double required_free=protected_level+reserve;
      allowed_new_margin=equity-used_margin-required_free;
     }
   else
     {
      double required_level=MathMax(MARGIN_LEVEL_FLOOR_PCT,protected_level*1.20);
      required_level=MathMax(required_level,protected_level+20.0);
      allowed_new_margin=equity*100.0/required_level-used_margin;
     }
   if(!IsUsable(allowed_new_margin) || allowed_new_margin<=0.0)
      return(false);

   double margin_one_lot=0.0;
   ResetLastError();
   if(!OrderCalcMargin(order_type,_Symbol,1.0,entry,margin_one_lot) ||
      GetLastError()!=0 || !IsUsable(margin_one_lot) || margin_one_lot<=0.0)
     {
      g_runtime_failed=true;
      PrintFormat("CCI001_FATAL reason=MARGIN_ONE_LOT error=%d value=%.8f",
                  GetLastError(),margin_one_lot);
      return(false);
     }

   double sized=MathMin(raw_volume,allowed_new_margin/margin_one_lot);
   sized=MathMin(sized,maximum);
   sized=NormalizeDouble(MathFloor(sized/step+1e-9)*step,VolumeDigits(step));
   if(sized<minimum-1e-9)
      return(false);

   for(int guard=0;guard<1024 && sized>=minimum-1e-9;guard++)
     {
      double exact_margin=0.0;
      ResetLastError();
      if(!OrderCalcMargin(order_type,_Symbol,sized,entry,exact_margin) ||
         GetLastError()!=0 || !IsUsable(exact_margin) || exact_margin<0.0)
        {
         g_runtime_failed=true;
         PrintFormat("CCI001_FATAL reason=MARGIN_EXACT error=%d volume=%.8f value=%.8f",
                     GetLastError(),sized,exact_margin);
         return(false);
        }
      if(exact_margin<=allowed_new_margin+0.01)
        {
         volume=sized;
         return(true);
        }
      sized=NormalizeDouble(sized-step,VolumeDigits(step));
     }
   return(false);
  }

bool SubmitEntry(const SignalDecision &signal)
  {
   MqlTick tick;
   ResetLastError();
   if(!SymbolInfoTick(_Symbol,tick) || GetLastError()!=0 ||
      !IsUsable(tick.ask) || !IsUsable(tick.bid) ||
      tick.ask<=0.0 || tick.bid<=0.0 || tick.ask<tick.bid)
     {
      g_runtime_failed=true;
      PrintFormat("CCI001_FATAL reason=SYMBOL_TICK error=%d bid=%.8f ask=%.8f",
                  GetLastError(),tick.bid,tick.ask);
      return(false);
     }
   const ENUM_ORDER_TYPE order_type=(signal.direction>0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL);
   const double entry=(signal.direction>0 ? tick.ask : tick.bid);
   const double stop=(signal.direction>0 ? FloorToTick(signal.structural_stop)
                                         : CeilToTick(signal.structural_stop));
   const double risk=(signal.direction>0 ? entry-stop : stop-entry);
   double target=(signal.direction>0 ? entry+TARGET_R*risk : entry-TARGET_R*risk);
   target=(signal.direction>0 ? FloorToTick(target) : CeilToTick(target));
   const double reward=(signal.direction>0 ? target-entry : entry-target);
   if(!IsUsable(entry) || !IsUsable(stop) || !IsUsable(target) ||
      risk<=0.0 || reward<=0.0 ||
      (signal.direction>0 && !(stop<entry && target>entry)) ||
      (signal.direction<0 && !(stop>entry && target<entry)))
      return(false);
   ResetLastError();
   const long stops_level=SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL);
   if(GetLastError()!=0 || stops_level<0)
     {
      g_runtime_failed=true;
      PrintFormat("CCI001_FATAL reason=STOPS_LEVEL_PROPERTY error=%d value=%I64d",
                  GetLastError(),stops_level);
      return(false);
     }
   const double minimum_distance=(double)stops_level*_Point;
   if(risk+1e-12<minimum_distance || reward+1e-12<minimum_distance)
      return(false);

   double volume=0.0;
   if(!CalculateVolume(order_type,entry,stop,volume))
      return(false);

   MqlTradeRequest request;
   MqlTradeCheckResult check;
   MqlTradeResult result;
   ZeroMemory(request);
   ZeroMemory(check);
   ZeroMemory(result);
   request.action=TRADE_ACTION_DEAL;
   request.symbol=_Symbol;
   request.magic=InpMagic;
   request.volume=volume;
   request.type=order_type;
   request.price=entry;
   request.sl=stop;
   request.tp=target;
   request.deviation=InpDeviationPoints;
   request.type_filling=ResolveFilling();
    request.comment="CCI001";
   ResetLastError();
   const bool check_ok=OrderCheck(request,check);
   const int check_error=GetLastError();
   if(!check_ok || check_error!=0 || check.retcode!=0)
     {
      g_runtime_failed=true;
      PrintFormat("CCI001_FATAL reason=ORDER_CHECK error=%d retcode=%u comment=%s",
                  check_error,check.retcode,check.comment);
      return(false);
     }
   ResetLastError();
   const bool send_ok=OrderSend(request,result);
   const int send_error=GetLastError();
   const bool definitive_no_fill=(result.retcode==TRADE_RETCODE_MARKET_CLOSED &&
                                  result.order==0 && result.deal==0);
   if(!send_ok && !definitive_no_fill)
     {
      g_runtime_failed=true;
      PrintFormat("CCI001_FATAL reason=ENTRY_SEND_TRANSPORT decision=%I64d retcode=%u error=%d order=%I64u deal=%I64u",
                  (long)signal.decision_time,result.retcode,send_error,
                  result.order,result.deal);
      return(false);
     }
   if(!AcceptedRetcode(result.retcode))
     {
      if(!definitive_no_fill)
        {
         g_runtime_failed=true;
         PrintFormat("CCI001_FATAL reason=ENTRY_REJECT_UNKNOWN decision=%I64d retcode=%u error=%d order=%I64u deal=%I64u",
                     (long)signal.decision_time,result.retcode,send_error,
                     result.order,result.deal);
         return(false);
        }
      int positions=0;
      int orders=0;
      if(!OwnedPositionCount(positions) || !OwnedOrderCount(orders) ||
         positions!=0 || orders!=0)
        {
         g_runtime_failed=true;
         PrintFormat("CCI001_FATAL reason=ENTRY_REJECT_AMBIGUOUS decision=%I64d retcode=%u error=%d positions=%d orders=%d",
                     (long)signal.decision_time,result.retcode,send_error,
                     positions,orders);
         return(false);
        }
      return(false);
     }
   g_entries_accepted++;
   g_daily_entries++;
   return(true);
  }

void ExecuteSignal(const SignalDecision &signal,const datetime now)
  {
   int positions=0;
   int orders=0;
   if(!OwnedPositionCount(positions) || !OwnedOrderCount(orders))
     {
      g_runtime_failed=true;
      g_entry_rejects++;
       Print("CCI001_FATAL reason=OWNED_INVENTORY_UNCERTAIN");
      return;
     }
   if(g_runtime_failed || g_daily_locked || g_drawdown_locked ||
      g_daily_entries>=InpMaxTradesPerDay || WeekendEntryBlocked(now) ||
      positions!=0 || orders!=0)
     {
      g_entry_rejects++;
      return;
     }
   if(!SubmitEntry(signal))
      g_entry_rejects++;
  }

bool ValidateFrozenInputs()
  {
   return(_Symbol==EXPECTED_SYMBOL && _Period==PERIOD_M15 &&
          InpResearchAutoMode && !InpEnableTelemetry &&
          InpHypothesisId==EXPECTED_HYPOTHESIS && InpVariantTag==EXPECTED_VARIANT &&
           InpMagic==5604201 && MathAbs(InpRiskPercent-0.25)<1e-12 &&
          MathAbs(InpMaxDailyLossPct-3.5)<1e-12 &&
          MathAbs(InpMaxAccountDrawdownPct-8.0)<1e-12 &&
          InpMaxTradesPerDay==1 && InpDeviationPoints==20 &&
          InpFridayFlattenHour==20);
  }

int OnInit()
  {
   if(!ValidateFrozenInputs())
     {
      g_runtime_failed=true;
       Print("CCI001_FATAL reason=FROZEN_INPUT_OR_SYMBOL_CONTRACT");
      return(INIT_PARAMETERS_INCORRECT);
     }
   if(!CurrentM15Open(g_last_bar_open))
     {
      g_runtime_failed=true;
       Print("CCI001_FATAL reason=INITIAL_M15_CLOCK");
      return(INIT_FAILED);
     }
   if(!EmitD0SeriesProof())
     {
      g_runtime_failed=true;
       Print("CCI001_FATAL reason=D0_SERIES_PROOF");
      return(INIT_FAILED);
     }
   long filling_mode=0;
   if(!SymbolInfoInteger(_Symbol,SYMBOL_FILLING_MODE,filling_mode) ||
      (filling_mode&SYMBOL_FILLING_FOK)!=SYMBOL_FILLING_FOK)
     {
      g_runtime_failed=true;
       Print("CCI001_FATAL reason=FOK_NOT_SUPPORTED");
      return(INIT_FAILED);
     }
    g_atr_handle=iATR(_Symbol,PERIOD_M15,ATR_PERIOD);
    g_cci_handle=iCCI(_Symbol,PERIOD_M15,CCI_PERIOD,PRICE_TYPICAL);
    if(g_atr_handle==INVALID_HANDLE || g_cci_handle==INVALID_HANDLE)
      {
       g_runtime_failed=true;
       Print("CCI001_FATAL reason=INDICATOR_HANDLE");
       return(INIT_FAILED);
      }
    g_indicators_ready=PreloadCciState();
   const double equity=AccountInfoDouble(ACCOUNT_EQUITY);
   if(!IsUsable(equity) || equity<=0.0)
     {
      g_runtime_failed=true;
       Print("CCI001_FATAL reason=INITIAL_EQUITY");
      return(INIT_FAILED);
     }
   g_daily_day_key=DateKey(TimeCurrent());
   g_daily_start_equity=equity;
   g_peak_equity=equity;
    PrintFormat("CCI001_INIT hypothesis=%s variant=%s symbol=%s period=%d cci_period=%d atr_period=%d",
                InpHypothesisId,InpVariantTag,_Symbol,(int)_Period,CCI_PERIOD,ATR_PERIOD);
   return(INIT_SUCCEEDED);
  }

void OnDeinit(const int reason)
  {
   if(!g_indicators_ready)
      g_runtime_failed=true;
   if(g_atr_handle!=INVALID_HANDLE)
      IndicatorRelease(g_atr_handle);
   if(g_cci_handle!=INVALID_HANDLE)
      IndicatorRelease(g_cci_handle);
   PrintFormat("CCI001_SUMMARY hypothesis=%s closed_bars=%I64d raw=%I64d long=%I64d short=%I64d entries=%I64d rejects=%I64d closes=%I64d clock_rejects=%I64d invalid=%I64d runtime_failed=%s reason=%d",
               InpHypothesisId,g_closed_bars,g_raw_signals,g_long_signals,
               g_short_signals,g_entries_accepted,g_entry_rejects,
               g_close_requests,g_clock_rejects,g_invalid_bars,
               g_runtime_failed ? "true" : "false",reason);
  }

void OnTick()
  {
   const datetime now=TimeCurrent();
   UpdateRiskLocks(now);
   if(!ManageOwnedPositions(now,false))
      return;
   if(!g_indicators_ready)
     {
      g_indicators_ready=PreloadCciState();
      if(!g_indicators_ready)
         return;
      datetime warmup_open=0;
      if(!CurrentM15Open(warmup_open))
        {
         g_runtime_failed=true;
         Print("CCI001_FATAL reason=WARMUP_M15_CLOCK");
         return;
        }
      g_last_bar_open=warmup_open;
      return;
     }

   datetime current_open=0;
   if(!CurrentM15Open(current_open))
     {
      g_runtime_failed=true;
       Print("CCI001_FATAL reason=M15_SCHEDULING_CLOCK");
      return;
     }
   if(current_open==g_last_bar_open)
      return;
   if(current_open<g_last_bar_open)
     {
      g_runtime_failed=true;
       Print("CCI001_FATAL reason=BAR_CLOCK_REGRESSION");
      return;
     }
   g_last_bar_open=current_open;
   if(!ManageOwnedPositions(now,true))
      return;

   SignalDecision signal;
   if(ProcessCciClosedBar(current_open,signal) && signal.fired)
      ExecuteSignal(signal,current_open);
  }
//+------------------------------------------------------------------+
