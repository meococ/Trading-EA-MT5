#property strict
#property version   "1.02"
#property description "Audit-only direct Supertrend 10/3 implementation plus read-only AlphaFactory data witness."

input bool   InpAuditOnly       = true;
input string InpAuditRunId      = "ST003-MT5-PARITY-001";
input string InpParityFileName  = "ST003_MQL5_PARITY_001.csv";
input bool   InpEnableTelemetry = false;

const string HYPOTHESIS_ID       = "HYP-ST-XAUUSD-H1-003";
const string PARITY_SCHEMA       = "st003_mql5_parity.v1";
const datetime SOURCE_START_TIME = D'2004.06.11 07:00:00';
const datetime DESIGN_START_TIME = D'2018.01.01 02:00:00';
const datetime DESIGN_END_TIME   = D'2023.01.01 02:00:00';
const datetime EXPECTED_FIRST_TIME = D'2018.01.02 09:00:00';
const datetime EXPECTED_LAST_TIME  = D'2022.12.30 22:00:00';
const datetime EXPECTED_LAST_NEXT  = D'2022.12.30 23:00:00';
const int ATR_PERIOD             = 10;
const double FACTOR              = 3.0;
const int STATE_DOWN             = -1;
const int STATE_UP               = 1;

int      g_file_handle       = INVALID_HANDLE;
datetime g_current_bar_open  = 0;
datetime g_last_bar_time     = 0;
double   g_atr               = 0.0;
double   g_final_upper       = 0.0;
double   g_final_lower       = 0.0;
double   g_supertrend        = 0.0;
double   g_prior_close       = 0.0;
int      g_state             = 0;
bool     g_runtime_failed    = false;
long     g_parity_rows       = 0;
long     g_raw_events        = 0;
long     g_executable_events = 0;
long     g_gap_events        = 0;
long     g_long_events       = 0;
long     g_short_events      = 0;
datetime g_first_parity_time = 0;
datetime g_last_parity_time  = 0;
datetime g_last_next_time    = 0;


bool ReadSeriesInteger(
   const ENUM_TIMEFRAMES timeframe,
   const ENUM_SERIES_INFO_INTEGER property_id,
   const string field_name,
   long &value
)
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


bool EmitDataQualitySeriesProof()
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


string StateName(const int state)
{
   if(state==STATE_UP)
      return "UP";
   if(state==STATE_DOWN)
      return "DOWN";
   return "UNAVAILABLE";
}


string PreciseDouble(const double value)
{
   return StringFormat("%.17g",value);
}


bool ValidBar(const MqlRates &bar)
{
   if(!MathIsValidNumber(bar.high) || !MathIsValidNumber(bar.low) || !MathIsValidNumber(bar.close))
      return false;
   return bar.high>=bar.low && bar.close>=bar.low && bar.close<=bar.high;
}


double TrueRange(const MqlRates &bar,const bool has_prior,const double prior_close)
{
   if(!has_prior)
      return bar.high-bar.low;
   const double range=bar.high-bar.low;
   const double high_gap=MathAbs(bar.high-prior_close);
   const double low_gap=MathAbs(bar.low-prior_close);
   return MathMax(range,MathMax(high_gap,low_gap));
}


bool SameBandIdentity(const double line,const double band)
{
   // The source dependency assigns these values directly. Exact identity is intentional.
   return line==band;
}


bool AdvanceState(const MqlRates &bar,int &prior_state)
{
   if(!ValidBar(bar))
      return false;

   prior_state=g_state;
   const double tr=TrueRange(bar,true,g_prior_close);
   const double next_atr=(9.0*g_atr+tr)/10.0;
   const double hl2=(bar.high+bar.low)/2.0;
   const double basic_upper=hl2+FACTOR*next_atr;
   const double basic_lower=hl2-FACTOR*next_atr;
   const double next_upper=(basic_upper<g_final_upper || g_prior_close>g_final_upper) ? basic_upper : g_final_upper;
   const double next_lower=(basic_lower>g_final_lower || g_prior_close<g_final_lower) ? basic_lower : g_final_lower;

   int next_state=0;
   if(SameBandIdentity(g_supertrend,g_final_upper))
      next_state=(bar.close>next_upper) ? STATE_UP : STATE_DOWN;
   else if(SameBandIdentity(g_supertrend,g_final_lower))
      next_state=(bar.close<next_lower) ? STATE_DOWN : STATE_UP;
   else
      return false;

   g_atr=next_atr;
   g_final_upper=next_upper;
   g_final_lower=next_lower;
   g_state=next_state;
   g_supertrend=(g_state==STATE_UP) ? g_final_lower : g_final_upper;
   g_prior_close=bar.close;
   g_last_bar_time=bar.time;
   return MathIsValidNumber(g_atr) && MathIsValidNumber(g_final_upper) &&
          MathIsValidNumber(g_final_lower) && MathIsValidNumber(g_supertrend);
}


datetime CurrentH1Open()
{
   return (datetime)SeriesInfoInteger(_Symbol,PERIOD_H1,SERIES_LASTBAR_DATE);
}


bool RebuildFrozenState(const datetime latest_closed_time)
{
   MqlRates history[];
   ArraySetAsSeries(history,false);
   const int total_bars=Bars(_Symbol,PERIOD_H1);
   if(total_bars<=ATR_PERIOD)
      return false;
   const int copied=CopyRates(_Symbol,PERIOD_H1,1,total_bars-1,history);
   if(copied<ATR_PERIOD || history[0].time!=SOURCE_START_TIME)
   {
      PrintFormat("ST003_FATAL|prehistory_unavailable|copied=%d|first=%s",copied,
                  copied>0 ? TimeToString(history[0].time,TIME_DATE|TIME_SECONDS) : "NONE");
      return false;
   }

   double seed_sum=0.0;
   double prior_close=0.0;
   for(int index=0;index<copied;index++)
   {
      if(!ValidBar(history[index]))
      {
         PrintFormat("ST003_FATAL|invalid_history_bar|index=%d|time=%s",index,
                     TimeToString(history[index].time,TIME_DATE|TIME_SECONDS));
         return false;
      }
      const double tr=TrueRange(history[index],index>0,prior_close);
      if(index<ATR_PERIOD)
         seed_sum+=tr;

      if(index==ATR_PERIOD-1)
      {
         g_atr=seed_sum/10.0;
         const double hl2=(history[index].high+history[index].low)/2.0;
         g_final_upper=hl2+FACTOR*g_atr;
         g_final_lower=hl2-FACTOR*g_atr;
         g_state=STATE_DOWN;
         g_supertrend=g_final_upper;
         g_prior_close=history[index].close;
         g_last_bar_time=history[index].time;
      }
      else if(index>=ATR_PERIOD)
      {
         int ignored_prior_state=0;
         if(!AdvanceState(history[index],ignored_prior_state))
         {
            PrintFormat("ST003_FATAL|state_rebuild_failed|index=%d|time=%s",index,
                        TimeToString(history[index].time,TIME_DATE|TIME_SECONDS));
            return false;
         }
      }
      prior_close=history[index].close;
   }

   if(g_last_bar_time!=history[copied-1].time || g_last_bar_time!=latest_closed_time || g_state==0)
      return false;
   PrintFormat("ST003_INIT|bars=%d|first=%s|last=%s|state=%s",copied,
               TimeToString(history[0].time,TIME_DATE|TIME_SECONDS),
               TimeToString(g_last_bar_time,TIME_DATE|TIME_SECONDS),StateName(g_state));
   return true;
}


bool OpenParityFile()
{
   if(FileIsExist(InpParityFileName,FILE_COMMON))
   {
      PrintFormat("ST003_FATAL|parity_file_already_exists|name=%s",InpParityFileName);
      return false;
   }
   g_file_handle=FileOpen(InpParityFileName,FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',');
   if(g_file_handle==INVALID_HANDLE)
   {
      PrintFormat("ST003_FATAL|parity_file_open_failed|name=%s|error=%d",InpParityFileName,GetLastError());
      return false;
   }
   FileWrite(g_file_handle,
             "schema_version","hypothesis_id","audit_run_id","source_epoch","time_server",
             "atr10","final_upper","final_lower","supertrend","prior_state","state",
             "raw_event","next_source_epoch","exact_next","executable_event","direction");
   FileFlush(g_file_handle);
   return true;
}


void WriteParityRow(const MqlRates &bar,const int prior_state,const datetime next_time)
{
   const bool raw_event=(prior_state!=0 && prior_state!=g_state);
   const bool exact_next=(next_time==bar.time+PeriodSeconds(PERIOD_H1));
   const bool executable=(raw_event && exact_next);
   string direction="";
   if(raw_event)
      direction=(g_state==STATE_UP) ? "LONG" : "SHORT";

   FileWrite(g_file_handle,PARITY_SCHEMA,HYPOTHESIS_ID,InpAuditRunId,(long)bar.time,
             TimeToString(bar.time,TIME_DATE|TIME_SECONDS),PreciseDouble(g_atr),
             PreciseDouble(g_final_upper),PreciseDouble(g_final_lower),PreciseDouble(g_supertrend),
             StateName(prior_state),StateName(g_state),raw_event ? 1 : 0,(long)next_time,
              exact_next ? 1 : 0,executable ? 1 : 0,direction);
   if(g_parity_rows==0)
      g_first_parity_time=bar.time;
   g_last_parity_time=bar.time;
   g_last_next_time=next_time;
   g_parity_rows++;
   if(raw_event)
   {
      g_raw_events++;
      if(!exact_next)
         g_gap_events++;
   }
   if(executable)
   {
      g_executable_events++;
      if(direction=="LONG")
         g_long_events++;
      else
         g_short_events++;
   }
}


void FailRuntime(const string reason)
{
   if(g_runtime_failed)
      return;
   g_runtime_failed=true;
   PrintFormat("ST003_FATAL|runtime|%s",reason);
   if(g_file_handle!=INVALID_HANDLE)
      FileFlush(g_file_handle);
   ExpertRemove();
}


bool ProcessNewClosedBars(const datetime current_open)
{
   MqlRates bars[];
   ArraySetAsSeries(bars,false);
   const int prior_shift=iBarShift(_Symbol,PERIOD_H1,g_last_bar_time,true);
   if(prior_shift<=1)
      return false;
   const int copied=CopyRates(_Symbol,PERIOD_H1,1,prior_shift-1,bars);
   if(copied<=0)
      return false;

   for(int index=0;index<copied;index++)
   {
      if(bars[index].time<=g_last_bar_time)
         return false;
      int prior_state=0;
      if(!AdvanceState(bars[index],prior_state))
         return false;
      const datetime next_time=(index+1<copied) ? bars[index+1].time : current_open;
      if(bars[index].time>=DESIGN_START_TIME && bars[index].time<DESIGN_END_TIME)
         WriteParityRow(bars[index],prior_state,next_time);
   }
   FileFlush(g_file_handle);
   return true;
}


int OnInit()
{
   if(!InpAuditOnly || InpEnableTelemetry || _Symbol!="XAUUSD" || _Period!=PERIOD_H1 ||
      InpAuditRunId!="ST003-MT5-PARITY-001" || InpParityFileName!="ST003_MQL5_PARITY_001.csv")
   {
      g_runtime_failed=true;
      Print("ST003_FATAL|frozen_input_or_chart_contract_failed");
      return INIT_PARAMETERS_INCORRECT;
   }

   if(!EmitDataQualitySeriesProof())
   {
      g_runtime_failed=true;
      Print("ST003_FATAL|data_quality_series_proof_failed");
      return INIT_FAILED;
   }

   g_current_bar_open=CurrentH1Open();
   const datetime latest_closed=iTime(_Symbol,PERIOD_H1,1);
   if(g_current_bar_open<=0 || latest_closed<=0 || latest_closed>=g_current_bar_open)
   {
      g_runtime_failed=true;
      return INIT_FAILED;
   }
   if(!RebuildFrozenState(latest_closed))
   {
      g_runtime_failed=true;
      return INIT_FAILED;
   }
   if(!OpenParityFile())
   {
      g_runtime_failed=true;
      return INIT_FAILED;
   }
   return INIT_SUCCEEDED;
}


void OnDeinit(const int reason)
{
   if(g_parity_rows>0 &&
      (g_parity_rows!=29460 || g_first_parity_time!=EXPECTED_FIRST_TIME ||
       g_last_parity_time!=EXPECTED_LAST_TIME || g_last_next_time!=EXPECTED_LAST_NEXT))
   {
      g_runtime_failed=true;
      PrintFormat("ST003_FATAL|design_window_mismatch|rows=%I64d|first=%s|last=%s|last_next=%s",
                  g_parity_rows,TimeToString(g_first_parity_time,TIME_DATE|TIME_SECONDS),
                  TimeToString(g_last_parity_time,TIME_DATE|TIME_SECONDS),
                  TimeToString(g_last_next_time,TIME_DATE|TIME_SECONDS));
   }
   if(g_file_handle!=INVALID_HANDLE)
   {
      FileFlush(g_file_handle);
      FileClose(g_file_handle);
      g_file_handle=INVALID_HANDLE;
   }
   PrintFormat("ST003_SUMMARY|run=%s|reason=%d|rows=%I64d|raw=%I64d|executable=%I64d|gaps=%I64d|long=%I64d|short=%I64d|failed=%s",
               InpAuditRunId,reason,g_parity_rows,g_raw_events,g_executable_events,g_gap_events,
               g_long_events,g_short_events,g_runtime_failed ? "true" : "false");
}


void OnTick()
{
   if(g_runtime_failed)
      return;
   const datetime current_open=CurrentH1Open();
   if(current_open<=0 || current_open==g_current_bar_open)
      return;
   if(current_open<g_current_bar_open)
   {
      FailRuntime("current_bar_time_regressed");
      return;
   }
   if(!ProcessNewClosedBars(current_open))
   {
      FailRuntime("closed_bar_backlog_processing_failed");
      return;
   }
   g_current_bar_open=current_open;
}


double OnTester()
{
   return 0.0;
}
