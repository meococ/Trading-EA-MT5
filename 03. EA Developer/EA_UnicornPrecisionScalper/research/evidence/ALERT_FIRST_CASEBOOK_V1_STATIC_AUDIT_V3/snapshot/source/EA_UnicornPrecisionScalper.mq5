#property copyright "AlphaFactory research"
#property version   "1.21"
#property strict

#include <Trade/Trade.mqh>

input bool   InpResearchAutoMode=false;
input bool   InpAllowRetiredResearchExecution=false;
input bool   InpEnableTelemetry=false;
input bool   InpEnableAlertCasebook=false;
input int    InpAlertCasebookMaxRows=200;
input double InpRiskPercent=0.30;
input double InpEstimatedCommissionPerLotRoundTurn=0.0;
input int    InpEstimatedSlippagePoints=0;
input string InpExpectedSymbolPrefix="XAUUSD";
input long   InpMagic=5600717;
input int    InpAtrPeriod=14;
input int    InpSweepLookback=12;
input int    InpSweepStateBars=4;
input bool   InpUseEventAnchoredSweepState=true;
input int    InpBreakerLookback=6;
input double InpMinDisplacementAtr=1.20;
input double InpStrongDisplacementAtr=1.80;
input double InpMinFvgAtr=0.05;
input double InpMinOverlapRatio=0.10;
input double InpStrongOverlapRatio=0.25;
input int    InpMinAutoScore=75;
input double InpTargetRR=2.50;
input double InpBreakEvenR=1.00;
input int    InpStopBufferPoints=40;
input int    InpMaxSpreadPoints=35;
input int    InpSessionStartUtcHour=7;
input int    InpSessionEndUtcHour=16;
input int    InpServerUtcOffsetHours=2;
input int    InpMaxHoldMinutes=90;
input int    InpMaxTradesPerDay=2;
input int    InpMaxConsecutiveLosses=2;
input double InpMaxDailyLossPct=1.00;
input double InpMaxWeeklyLossPct=2.00;
input double InpMaxAccountDrawdownPct=5.50;
input bool   InpRequireNewsGuard=false;
input bool   InpPersistPeakEquityAcrossRestarts=true;
input bool   InpEmergencyBlockNewEntries=false;

const string EA_NAME="EA_UnicornPrecisionScalper";
const string HYPOTHESIS_ID="HYP-UPS-XAU-M5-006";
const string TELEMETRY_PROFILE="lifecycle-v3";
const string ENGINEERING_STATUS="POST_KILL_HARDENED_NO_RUN_AUTHORITY";
const string CASEBOOK_CONTRACT_ID="ALERT_FIRST_CASEBOOK_V1";
const string CASEBOOK_SOURCE_CONTRACT_ID="UPS_ALERT_FIRST_CASEBOOK_V1_1";

enum SignalRejectReason
  {
   REJECT_NONE=0,
   REJECT_HISTORY,
   REJECT_BIAS,
   REJECT_ATR,
   REJECT_DISPLACEMENT,
   REJECT_FVG,
   REJECT_SWEEP,
   REJECT_OVERLAP,
   REJECT_SCORE,
   REJECT_REASON_COUNT
  };

enum ExecutionState
  {
   EXEC_ALERT_ONLY=0,
   EXEC_IDLE,
   EXEC_PLACING_ORDER,
   EXEC_WAITING_FILL,
   EXEC_MANAGING_POSITION,
   EXEC_LOCKED_RISK,
   EXEC_RECOVERING_ERROR
  };

struct SignalPlan
  {
   bool valid;
   int reject_reason;
   int direction;
   int score;
   double sweep_extreme;
   double atr;
   double body_atr;
   double overlap_ratio;
   datetime decision_time_utc;
   int h4_bias;
   int d1_bias;
   int sweep_age_bars;
   double fvg_low;
   double fvg_high;
   bool pd_ok;
  };

CTrade trade;
datetime g_last_bar=0;
bool g_new_bar_ready=false;
double g_peak_equity=0.0;
double g_planned_risk_points=0.0;
double g_planned_risk_account=0.0;
ulong g_position_identifier=0;
ENUM_ORDER_TYPE g_entry_order_type=ORDER_TYPE_BUY;
double g_pending_risk_points=0.0;
double g_pending_risk_account=0.0;
double g_previous_risk_points=0.0;
double g_previous_risk_account=0.0;
ulong g_previous_position_identifier=0;
double g_initial_risk_distance=0.0;
ulong g_initial_risk_position_identifier=0;
long g_signal_decisions[REJECT_REASON_COUNT];
ExecutionState g_execution_state=EXEC_ALERT_ONLY;
int g_telemetry_handle=INVALID_HANDLE;
string g_run_id="";
string g_lifecycle_name="";
string g_run_meta_name="";
int g_casebook_handle=INVALID_HANDLE;
string g_casebook_name="";
string g_casebook_meta_name="";
int g_casebook_rows=0;
bool g_casebook_limit_reported=false;

string SafeRunToken()
  {
   return StringFormat("%s_%I64u",HYPOTHESIS_ID,GetTickCount64());
  }

bool WriteRunMeta()
  {
   g_run_meta_name=StringFormat("%s_RunMeta_%s.json",_Symbol,g_run_id);
   int handle=FileOpen(g_run_meta_name,FILE_WRITE|FILE_TXT|FILE_ANSI);
   if(handle==INVALID_HANDLE)
     {
      Print("UPS telemetry RunMeta open failed: ",GetLastError());
      return false;
     }
   string payload=StringFormat(
      "{\"schema_version\":\"alphafactory_run_meta.v1\",\"run_id\":\"%s\",\"ea_name\":\"%s\",\"symbol\":\"%s\",\"telemetry_profile\":\"%s\",\"hypothesis_id\":\"%s\",\"engineering_status\":\"%s\",\"trade_mutation_allowed\":%s}",
      g_run_id,EA_NAME,_Symbol,TELEMETRY_PROFILE,HYPOTHESIS_ID,ENGINEERING_STATUS,
      (InpResearchAutoMode && InpAllowRetiredResearchExecution) ? "true" : "false");
   FileWriteString(handle,payload);
   FileClose(handle);
   return true;
  }

bool OpenLifecycleTelemetry()
  {
   if(!InpEnableTelemetry)
      return true;
   g_run_id=SafeRunToken();
   g_lifecycle_name=StringFormat("%s_LifecycleTrades_%s.csv",_Symbol,g_run_id);
   g_telemetry_handle=FileOpen(g_lifecycle_name,FILE_WRITE|FILE_CSV|FILE_ANSI,',');
   if(g_telemetry_handle==INVALID_HANDLE)
     {
      Print("UPS lifecycle telemetry open failed: ",GetLastError());
      return false;
     }
   FileWrite(g_telemetry_handle,
             "event_time","action","order_type","volume","price","symbol",
             "position_id","risk_pts","initial_risk_account","deal",
             "deal_profit","deal_commission","deal_swap","deal_fee","deal_net",
             "is_final_close");
   FileFlush(g_telemetry_handle);
   return WriteRunMeta();
  }

bool AlertCasebookStorageAllowed()
  {
   if(!InpEnableAlertCasebook)
      return true;
   string data_path=TerminalInfoString(TERMINAL_DATA_PATH);
   StringReplace(data_path,"/","\\");
   return StringFind(data_path,"D:\\")==0 || StringFind(data_path,"d:\\")==0;
  }

bool WriteAlertCasebookMeta()
  {
   g_casebook_meta_name=StringFormat("%s_AlertCasebookMeta_%s.csv",_Symbol,g_run_id);
   int handle=FileOpen(g_casebook_meta_name,FILE_WRITE|FILE_CSV|FILE_ANSI,',');
   if(handle==INVALID_HANDLE)
     {
      Print("UPS alert casebook metadata open failed: ",GetLastError());
      return false;
     }
   FileWrite(handle,
             "schema_version","contract_id","source_contract_id","run_id",
             "ea_name","hypothesis_id","engineering_status","symbol",
             "account_server","terminal_company","terminal_build","terminal_data_path",
             "period","server_utc_offset_hours","session_start_utc_hour","session_end_utc_hour",
             "atr_period","sweep_lookback","sweep_state_bars","event_anchored_sweep",
             "breaker_lookback","min_displacement_atr","strong_displacement_atr",
             "min_fvg_atr","min_overlap_ratio","strong_overlap_ratio","min_auto_score",
             "target_rr","break_even_r","stop_buffer_points","max_spread_points",
             "max_hold_minutes","casebook_max_rows");
   FileWrite(handle,
             "alert_first_casebook_meta.v1",CASEBOOK_CONTRACT_ID,CASEBOOK_SOURCE_CONTRACT_ID,g_run_id,
             EA_NAME,HYPOTHESIS_ID,ENGINEERING_STATUS,_Symbol,
             AccountInfoString(ACCOUNT_SERVER),TerminalInfoString(TERMINAL_COMPANY),
             TerminalInfoInteger(TERMINAL_BUILD),TerminalInfoString(TERMINAL_DATA_PATH),
             EnumToString((ENUM_TIMEFRAMES)_Period),InpServerUtcOffsetHours,
             InpSessionStartUtcHour,InpSessionEndUtcHour,InpAtrPeriod,InpSweepLookback,
             InpSweepStateBars,InpUseEventAnchoredSweepState ? "1" : "0",InpBreakerLookback,
             DoubleToString(InpMinDisplacementAtr,6),DoubleToString(InpStrongDisplacementAtr,6),
             DoubleToString(InpMinFvgAtr,6),DoubleToString(InpMinOverlapRatio,6),
             DoubleToString(InpStrongOverlapRatio,6),InpMinAutoScore,
             DoubleToString(InpTargetRR,6),DoubleToString(InpBreakEvenR,6),
             InpStopBufferPoints,InpMaxSpreadPoints,InpMaxHoldMinutes,InpAlertCasebookMaxRows);
   FileFlush(handle);
   FileClose(handle);
   return true;
  }

bool OpenAlertCasebook()
  {
   if(!InpEnableAlertCasebook)
      return true;
   if(g_run_id=="")
      g_run_id=SafeRunToken();
   g_casebook_name=StringFormat("%s_AlertCasebook_%s.csv",_Symbol,g_run_id);
   g_casebook_handle=FileOpen(g_casebook_name,FILE_WRITE|FILE_CSV|FILE_ANSI,',');
   if(g_casebook_handle==INVALID_HANDLE)
     {
      Print("UPS alert casebook open failed: ",GetLastError());
      return false;
     }
   FileWrite(g_casebook_handle,
             "schema_version","contract_id","source_contract_id","run_id","event_id",
             "decision_time_utc","decision_time_server","server_utc_offset_hours",
             "symbol","direction","detector_score","sweep_extreme",
             "sweep_age_bars","displacement_atr","fvg_low","fvg_mid",
             "fvg_high","overlap_ratio","h4_bias","d1_bias","pd_ok",
             "spread_points","label_true_sweep_liquidity",
             "label_true_displacement","label_true_mss_bos_close",
             "label_fvg_fresh_unfilled","label_micro_confirm_present",
             "label_trade_quality_accept","reject_reason","reviewer_id",
             "label_time_utc");
   FileFlush(g_casebook_handle);
   if(WriteAlertCasebookMeta())
      return true;
   FileClose(g_casebook_handle);
   g_casebook_handle=INVALID_HANDLE;
   return false;
  }

bool WriteAlertCasebook(const SignalPlan &signal,const double spread_points)
  {
   if(!InpEnableAlertCasebook)
      return true;
   if(g_casebook_handle==INVALID_HANDLE)
      return false;
   if(g_casebook_rows>=InpAlertCasebookMaxRows)
     {
      if(!g_casebook_limit_reported)
        {
         PrintFormat("UPS alert casebook row limit reached: %d",InpAlertCasebookMaxRows);
         g_casebook_limit_reported=true;
        }
      return true;
     }
   string event_id=StringFormat("%s_%I64d_%d",_Symbol,(long)signal.decision_time_utc,signal.direction);
   datetime decision_time_server=signal.decision_time_utc+InpServerUtcOffsetHours*3600;
   double fvg_mid=(signal.fvg_low+signal.fvg_high)/2.0;
   FileWrite(g_casebook_handle,
             "alert_first_casebook.v1",CASEBOOK_CONTRACT_ID,CASEBOOK_SOURCE_CONTRACT_ID,g_run_id,event_id,
             TimeToString(signal.decision_time_utc,TIME_DATE|TIME_SECONDS),
             TimeToString(decision_time_server,TIME_DATE|TIME_SECONDS),InpServerUtcOffsetHours,
             _Symbol,signal.direction,signal.score,
             DoubleToString(signal.sweep_extreme,_Digits),signal.sweep_age_bars,
             DoubleToString(signal.body_atr,6),DoubleToString(signal.fvg_low,_Digits),
             DoubleToString(fvg_mid,_Digits),DoubleToString(signal.fvg_high,_Digits),
             DoubleToString(signal.overlap_ratio,6),signal.h4_bias,signal.d1_bias,
             signal.pd_ok ? "1" : "0",DoubleToString(spread_points,1),
             "","","","","","","","","");
   FileFlush(g_casebook_handle);
   g_casebook_rows++;
   return true;
  }

bool InputError(const string message)
  {
   Print("UPS invalid input: ",message);
   return false;
  }

bool TradingMutationAllowed()
  {
   return InpResearchAutoMode && InpAllowRetiredResearchExecution;
  }

string PeakEquityStateKey()
  {
   return StringFormat("UPS_PEAK_%I64d_%s_%I64d",
                       AccountInfoInteger(ACCOUNT_LOGIN),_Symbol,InpMagic);
  }

void PersistPeakEquityState()
  {
   if(!InpPersistPeakEquityAcrossRestarts || !TradingMutationAllowed() ||
      MQLInfoInteger(MQL_TESTER) || g_peak_equity<=0.0)
      return;
   if(!GlobalVariableSet(PeakEquityStateKey(),g_peak_equity))
      Print("UPS peak-equity persistence failed: ",GetLastError());
  }

void LoadPeakEquityState()
  {
   if(!InpPersistPeakEquityAcrossRestarts || !TradingMutationAllowed() ||
      MQLInfoInteger(MQL_TESTER))
      return;
   string key=PeakEquityStateKey();
   if(GlobalVariableCheck(key))
      g_peak_equity=MathMax(g_peak_equity,GlobalVariableGet(key));
  }

string SignalRejectReasonName(const int reason)
  {
   switch(reason)
     {
      case REJECT_NONE:         return "VALID";
      case REJECT_HISTORY:      return "HISTORY";
      case REJECT_BIAS:         return "BIAS";
      case REJECT_ATR:          return "ATR";
      case REJECT_DISPLACEMENT: return "DISPLACEMENT";
      case REJECT_FVG:          return "FVG";
      case REJECT_SWEEP:        return "SWEEP";
      case REJECT_OVERLAP:      return "OVERLAP";
      case REJECT_SCORE:        return "SCORE";
     }
   return "UNKNOWN";
  }

void CountSignalDecision(const int reason)
  {
   if(reason>=0 && reason<REJECT_REASON_COUNT)
      g_signal_decisions[reason]++;
  }

void PrintSignalDecisionSummary()
  {
   for(int i=0;i<REJECT_REASON_COUNT;i++)
      if(g_signal_decisions[i]>0)
         PrintFormat("UPS reject summary reason=%s count=%I64d",
                     SignalRejectReasonName(i),g_signal_decisions[i]);
  }

string ExecutionStateName(const ExecutionState state)
  {
   switch(state)
     {
      case EXEC_ALERT_ONLY:        return "ALERT_ONLY";
      case EXEC_IDLE:              return "IDLE";
      case EXEC_PLACING_ORDER:     return "PLACING_ORDER";
      case EXEC_WAITING_FILL:      return "WAITING_FILL";
      case EXEC_MANAGING_POSITION: return "MANAGING_POSITION";
      case EXEC_LOCKED_RISK:       return "LOCKED_RISK";
      case EXEC_RECOVERING_ERROR:  return "RECOVERING_ERROR";
     }
   return "UNKNOWN";
  }

void SetExecutionState(const ExecutionState next,const string reason)
  {
   if(g_execution_state==next)
      return;
   PrintFormat("UPS FSM from=%s to=%s reason=%s",
               ExecutionStateName(g_execution_state),ExecutionStateName(next),reason);
   g_execution_state=next;
  }

bool ValidateInputs()
  {
   if(_Period!=PERIOD_M5)
      return InputError("M5 chart/test period required");
   if(StringLen(InpExpectedSymbolPrefix)<3 || StringFind(_Symbol,InpExpectedSymbolPrefix)!=0)
      return InputError("symbol does not match InpExpectedSymbolPrefix");
   if(InpResearchAutoMode && !InpAllowRetiredResearchExecution)
      return InputError("retired HYP-006 execution is blocked; alert-only remains available");
   if(InpResearchAutoMode &&
      (InpEstimatedCommissionPerLotRoundTurn<=0.0 || InpEstimatedSlippagePoints<=0))
      return InputError("research-auto requires positive commission and slippage assumptions");
   if(InpEnableAlertCasebook && TradingMutationAllowed())
      return InputError("alert casebook requires non-mutating alert-only mode");
   if(InpAlertCasebookMaxRows<1 || InpAlertCasebookMaxRows>200)
      return InputError("alert casebook rows must be within 1..200");
   if(InpEnableAlertCasebook && !AlertCasebookStorageAllowed())
      return InputError("alert casebook requires terminal data path on D drive");
   if(InpRiskPercent<=0.0 || InpRiskPercent>1.0 || InpTargetRR<2.0 || InpBreakEvenR<=0.0)
      return InputError("risk/target/break-even parameters out of range");
   if(InpAtrPeriod<5 || InpSweepLookback<3 || InpSweepStateBars<1 || InpSweepStateBars>12)
      return InputError("ATR/sweep parameters out of range");
   if(InpBreakerLookback<1 || InpMinDisplacementAtr<=0.0 || InpStrongDisplacementAtr<InpMinDisplacementAtr)
      return InputError("breaker/displacement parameters out of range");
   if(InpMinFvgAtr<=0.0 || InpMinOverlapRatio<0.0 ||
      InpStrongOverlapRatio<InpMinOverlapRatio || InpStrongOverlapRatio>1.0 ||
      InpMinAutoScore<0 || InpMinAutoScore>100)
      return InputError("FVG/overlap/score parameters out of range");
   if(InpSessionStartUtcHour<0 || InpSessionStartUtcHour>23 ||
      InpSessionEndUtcHour<1 || InpSessionEndUtcHour>24 ||
      InpSessionStartUtcHour>=InpSessionEndUtcHour)
      return InputError("same-day UTC session must have start < end");
   if(InpMaxSpreadPoints<=0 || InpStopBufferPoints<0 || InpMaxHoldMinutes<=0 ||
      InpMaxTradesPerDay<=0 || InpMaxConsecutiveLosses<=0)
      return InputError("execution limits must be positive");
   if(InpMaxDailyLossPct<=0.0 || InpMaxWeeklyLossPct<=0.0 ||
      InpMaxAccountDrawdownPct<=0.0 || InpMaxAccountDrawdownPct>100.0)
      return InputError("loss limits out of range");
   if(InpEstimatedCommissionPerLotRoundTurn<0.0 || InpEstimatedSlippagePoints<0)
      return InputError("execution cost assumptions cannot be negative");
   return true;
  }

datetime CurrentM5BucketOpen()
  {
   datetime now=TimeCurrent();
   int seconds=PeriodSeconds(PERIOD_M5);
   if(now<=0 || seconds<=0)
      return 0;
   return now-(now%seconds);
  }

int OnInit()
  {
   if(!ValidateInputs())
      return INIT_PARAMETERS_INCORRECT;
   trade.SetExpertMagicNumber((ulong)InpMagic);
   trade.SetDeviationInPoints((ulong)MathMax(1,InpMaxSpreadPoints));
   trade.SetTypeFillingBySymbol(_Symbol);
   trade.SetAsyncMode(false);
   g_peak_equity=AccountInfoDouble(ACCOUNT_EQUITY);
   LoadPeakEquityState();
   // Seed the gate so attaching or restarting mid-bar cannot execute a stale
   // signal from the previously completed candle.
   g_last_bar=CurrentM5BucketOpen();
   g_new_bar_ready=false;
   if(g_last_bar<=0)
      return INIT_FAILED;
   if(!OpenLifecycleTelemetry())
      return INIT_FAILED;
   if(!OpenAlertCasebook())
      return INIT_FAILED;
   PrintFormat("UPS init mode=%s hypothesis=%s engineering=%s telemetry=%s casebook=%s",
               TradingMutationAllowed() ? "RETIRED_RESEARCH_OVERRIDE" : "ALERT_ONLY",
               HYPOTHESIS_ID,ENGINEERING_STATUS,InpEnableTelemetry ? "ON" : "OFF",
               InpEnableAlertCasebook ? "ON" : "OFF");
   ulong owned=OwnedPositionTicket();
   if(!TradingMutationAllowed())
     {
      SetExecutionState(EXEC_ALERT_ONLY,"trade mutation disabled");
      if(owned!=0)
         Print("UPS alert-only: owned position detected and intentionally left untouched.");
     }
   else if(owned!=0)
     {
      ulong position_id=(ulong)PositionGetInteger(POSITION_IDENTIFIER);
      CaptureInitialRiskFromPosition(position_id);
      SetExecutionState(EXEC_MANAGING_POSITION,"owned position recovered on init");
     }
   else
      SetExecutionState(EXEC_IDLE,"initialized without owned position");
   return INIT_SUCCEEDED;
  }

void OnDeinit(const int reason)
  {
   PersistPeakEquityState();
   PrintSignalDecisionSummary();
   if(g_telemetry_handle!=INVALID_HANDLE)
     {
      FileFlush(g_telemetry_handle);
      FileClose(g_telemetry_handle);
      g_telemetry_handle=INVALID_HANDLE;
     }
   if(g_casebook_handle!=INVALID_HANDLE)
     {
      FileFlush(g_casebook_handle);
      FileClose(g_casebook_handle);
      g_casebook_handle=INVALID_HANDLE;
     }
  }

void RefreshNewM5BarGate()
  {
   datetime current=iTime(_Symbol,PERIOD_M5,0);
   if(current<=0 || current<=g_last_bar)
      return;
   g_last_bar=current;
   g_new_bar_ready=true;
  }

double TrueRange(const MqlRates &bar,const MqlRates &older)
  {
   return MathMax(bar.high-bar.low,MathMax(MathAbs(bar.high-older.close),MathAbs(bar.low-older.close)));
  }

double ClosedAtr(const MqlRates &rates[],const int start_shift)
  {
   double total=0.0;
   for(int i=start_shift;i<start_shift+InpAtrPeriod;i++)
      total+=TrueRange(rates[i],rates[i+1]);
   return total/(double)InpAtrPeriod;
  }

int ClosedTrendState(const ENUM_TIMEFRAMES timeframe)
  {
   MqlRates bars[];
   ArraySetAsSeries(bars,true);
   int copied=CopyRates(_Symbol,timeframe,1,80,bars);
   if(copied<60)
      return 0;
   double fast=bars[copied-1].close;
   double slow=bars[copied-1].close;
   const double fast_alpha=2.0/21.0;
   const double slow_alpha=2.0/51.0;
   for(int i=copied-2;i>=0;i--)
     {
      fast=fast_alpha*bars[i].close+(1.0-fast_alpha)*fast;
      slow=slow_alpha*bars[i].close+(1.0-slow_alpha)*slow;
     }
   if(bars[0].close>fast && fast>slow)
      return 1;
   if(bars[0].close<fast && fast<slow)
      return -1;
   return 0;
  }

bool SessionOpen(const datetime server_time)
  {
   datetime utc_time=server_time-(InpServerUtcOffsetHours*3600);
   MqlDateTime parts;
   TimeToStruct(utc_time,parts);
   return parts.hour>=InpSessionStartUtcHour && parts.hour<InpSessionEndUtcHour;
  }

bool NewsGuardAllows()
  {
   if(!InpRequireNewsGuard)
      return true;
   // Historical calendar identity is not yet hash-bound. Required mode must
   // fail closed rather than silently pretending that no news exists.
   return false;
  }

double CandleOverlapRatio(const MqlRates &bar,const int direction,const double zone_low,const double zone_high)
  {
   bool opposite=(direction>0 ? bar.close<bar.open : bar.close>bar.open);
   if(!opposite)
      return 0.0;
   double width=zone_high-zone_low;
   if(width<=0.0)
      return 0.0;
   double candle_low=MathMin(bar.open,bar.close);
   double candle_high=MathMax(bar.open,bar.close);
   double overlap=MathMax(0.0,MathMin(zone_high,candle_high)-MathMax(zone_low,candle_low));
   return overlap/width;
  }

bool FindRecentSweep(const MqlRates &rates[],const int left,const int direction,
                     double &extreme,int &sweep_age_bars)
  {
   int last_index=left+InpSweepStateBars-1;
   if(InpUseEventAnchoredSweepState)
      last_index=ArraySize(rates)-InpSweepLookback-1;
   datetime decision_utc=rates[0].time+PeriodSeconds(PERIOD_M5)-(InpServerUtcOffsetHours*3600);
   MqlDateTime decision_parts;
   TimeToStruct(decision_utc,decision_parts);
   for(int j=left;j<=last_index;j++)
     {
      if(InpUseEventAnchoredSweepState)
        {
         datetime sweep_close_utc=rates[j].time+PeriodSeconds(PERIOD_M5)-(InpServerUtcOffsetHours*3600);
         MqlDateTime sweep_parts;
         TimeToStruct(sweep_close_utc,sweep_parts);
         if(sweep_parts.year!=decision_parts.year || sweep_parts.day_of_year!=decision_parts.day_of_year ||
            sweep_parts.hour<InpSessionStartUtcHour || sweep_parts.hour>=InpSessionEndUtcHour)
            break;
        }
      double prior_low=DBL_MAX;
      double prior_high=-DBL_MAX;
      for(int k=j+1;k<=j+InpSweepLookback;k++)
        {
         prior_low=MathMin(prior_low,rates[k].low);
         prior_high=MathMax(prior_high,rates[k].high);
        }
      if(direction>0 && rates[j].low<prior_low && rates[j].close>prior_low)
        {
         bool invalidated=false;
         if(InpUseEventAnchoredSweepState)
            for(int k=left;k<j;k++)
               if(rates[k].close<=rates[j].low)
                 {
                  invalidated=true;
                  break;
                 }
         if(!invalidated)
           {
            extreme=rates[j].low;
            sweep_age_bars=j-left;
            return true;
           }
        }
      if(direction<0 && rates[j].high>prior_high && rates[j].close<prior_high)
        {
         bool invalidated=false;
         if(InpUseEventAnchoredSweepState)
            for(int k=left;k<j;k++)
               if(rates[k].close>=rates[j].high)
                 {
                  invalidated=true;
                  break;
                 }
         if(!invalidated)
           {
            extreme=rates[j].high;
            sweep_age_bars=j-left;
            return true;
           }
        }
     }
   return false;
  }

SignalPlan EvaluateClosedSignal()
  {
   SignalPlan result;
   result.valid=false;
   result.reject_reason=REJECT_HISTORY;
   result.direction=0;
   result.score=0;
   result.sweep_extreme=0.0;
   result.atr=0.0;
   result.body_atr=0.0;
   result.overlap_ratio=0.0;
   result.decision_time_utc=0;
   result.h4_bias=0;
   result.d1_bias=0;
   result.sweep_age_bars=0;
   result.fvg_low=0.0;
   result.fvg_high=0.0;
   result.pd_ok=false;

   int state_capacity=(InpUseEventAnchoredSweepState ? 160 : InpSweepStateBars);
   int required=MathMax(80,InpSweepLookback+state_capacity+InpBreakerLookback+20);
   MqlRates rates[];
   ArraySetAsSeries(rates,true);
   int copied=CopyRates(_Symbol,PERIOD_M5,1,required,rates);
   if(copied<required)
      return result;
   result.decision_time_utc=rates[0].time+PeriodSeconds(PERIOD_M5)-(InpServerUtcOffsetHours*3600);

   int h4_bias=ClosedTrendState(PERIOD_H4);
   int d1_bias=ClosedTrendState(PERIOD_D1);
   result.h4_bias=h4_bias;
   result.d1_bias=d1_bias;
   result.reject_reason=REJECT_BIAS;
   if(h4_bias==0 || d1_bias==-h4_bias)
      return result;

   const int right=0;
   const int middle=1;
   const int left=2;
   double current_atr=ClosedAtr(rates,middle);
   result.reject_reason=REJECT_ATR;
   if(current_atr<=0.0)
      return result;
   double body=MathAbs(rates[middle].close-rates[middle].open);
   double body_atr=body/current_atr;
   result.reject_reason=REJECT_DISPLACEMENT;
   if(body_atr<InpMinDisplacementAtr)
      return result;

   int direction=0;
   double fvg_low=0.0;
   double fvg_high=0.0;
   if(h4_bias>0 && rates[middle].close>rates[middle].open && rates[right].low>rates[left].high)
     {
      direction=1;
      fvg_low=rates[left].high;
      fvg_high=rates[right].low;
     }
   else if(h4_bias<0 && rates[middle].close<rates[middle].open && rates[right].high<rates[left].low)
     {
      direction=-1;
      fvg_low=rates[right].high;
      fvg_high=rates[left].low;
     }
   result.reject_reason=REJECT_FVG;
   if(direction==0 || (fvg_high-fvg_low)/current_atr<InpMinFvgAtr)
      return result;
   result.fvg_low=fvg_low;
   result.fvg_high=fvg_high;

   double sweep_extreme=0.0;
   int sweep_age_bars=0;
   result.reject_reason=REJECT_SWEEP;
   if(!FindRecentSweep(rates,left,direction,sweep_extreme,sweep_age_bars))
      return result;
   double best_overlap=0.0;
   for(int i=left;i<=left+InpBreakerLookback;i++)
      best_overlap=MathMax(best_overlap,CandleOverlapRatio(rates[i],direction,fvg_low,fvg_high));
   result.reject_reason=REJECT_OVERLAP;
   if(best_overlap<InpMinOverlapRatio)
      return result;

   double range_low=DBL_MAX;
   double range_high=-DBL_MAX;
   for(int i=0;i<25;i++)
     {
      range_low=MathMin(range_low,rates[i].low);
      range_high=MathMax(range_high,rates[i].high);
     }
   double midpoint=(range_low+range_high)/2.0;
   bool pd_ok=(direction>0 ? rates[right].close<=midpoint : rates[right].close>=midpoint);
   result.pd_ok=pd_ok;
   int score=15+(d1_bias==h4_bias ? 10 : 0)+15;
   score+=(body_atr>=InpStrongDisplacementAtr ? 20 : 15);
   score+=10;
   score+=(best_overlap>=InpStrongOverlapRatio ? 20 : 15);
   score+=(pd_ok ? 10 : 0);
   result.reject_reason=REJECT_SCORE;
   if(score<InpMinAutoScore)
      return result;

   result.valid=true;
   result.reject_reason=REJECT_NONE;
   result.direction=direction;
   result.score=score;
   result.sweep_extreme=sweep_extreme;
   result.sweep_age_bars=sweep_age_bars;
   result.atr=current_atr;
   result.body_atr=body_atr;
   result.overlap_ratio=best_overlap;
   return result;
  }

bool IsOwnedPosition(const ulong ticket)
  {
   if(ticket==0 || !PositionSelectByTicket(ticket))
      return false;
   return PositionGetString(POSITION_SYMBOL)==_Symbol &&
          PositionGetInteger(POSITION_MAGIC)==InpMagic &&
          PositionGetString(POSITION_COMMENT)==HYPOTHESIS_ID;
  }

ulong OwnedPositionTicket()
  {
   for(int i=PositionsTotal()-1;i>=0;i--)
     {
      ulong ticket=PositionGetTicket(i);
      if(IsOwnedPosition(ticket))
         return ticket;
     }
   return 0;
  }

bool ForeignSymbolPositionExists()
  {
   for(int i=PositionsTotal()-1;i>=0;i--)
     {
      ulong ticket=PositionGetTicket(i);
      if(ticket==0 || !PositionSelectByTicket(ticket))
         continue;
      if(PositionGetString(POSITION_SYMBOL)==_Symbol && !IsOwnedPosition(ticket))
         return true;
     }
   return false;
  }

bool ForeignSymbolOrderExists()
  {
   for(int i=OrdersTotal()-1;i>=0;i--)
     {
      ulong ticket=OrderGetTicket(i);
      if(ticket==0)
         continue;
      if(OrderGetString(ORDER_SYMBOL)==_Symbol)
         return true;
     }
   return false;
  }

datetime StartOfDay(const datetime now)
  {
   MqlDateTime p;
   TimeToStruct(now,p);
   p.hour=0; p.min=0; p.sec=0;
   return StructToTime(p);
  }

datetime StartOfWeek(const datetime now)
  {
   MqlDateTime p;
   TimeToStruct(now,p);
   int days_from_monday=(p.day_of_week+6)%7;
   return StartOfDay(now)-days_from_monday*86400;
  }

int FindPositionId(const ulong &position_ids[],const ulong position_id)
  {
   for(int i=0;i<ArraySize(position_ids);i++)
      if(position_ids[i]==position_id)
         return i;
   return -1;
  }

int EntryPositionCountSince(const datetime from_time,bool &history_ok)
  {
   history_ok=false;
   if(!HistorySelect(from_time,TimeCurrent()))
      return 0;
   history_ok=true;
   ulong position_ids[];
   int total=HistoryDealsTotal();
   for(int i=0;i<total;i++)
     {
      ulong deal=HistoryDealGetTicket(i);
      if(deal==0 || HistoryDealGetString(deal,DEAL_SYMBOL)!=_Symbol ||
         HistoryDealGetInteger(deal,DEAL_MAGIC)!=InpMagic)
         continue;
      ENUM_DEAL_ENTRY entry=(ENUM_DEAL_ENTRY)HistoryDealGetInteger(deal,DEAL_ENTRY);
      if(entry!=DEAL_ENTRY_IN && entry!=DEAL_ENTRY_INOUT)
         continue;
      ulong position_id=(ulong)HistoryDealGetInteger(deal,DEAL_POSITION_ID);
      if(position_id==0 || FindPositionId(position_ids,position_id)>=0)
         continue;
      int next=ArraySize(position_ids);
      ArrayResize(position_ids,next+1);
      position_ids[next]=position_id;
     }
   return ArraySize(position_ids);
  }

double RealizedNetSince(const datetime from_time,bool &history_ok)
  {
   history_ok=false;
   double net=0.0;
   if(!HistorySelect(from_time,TimeCurrent()))
      return 0.0;
   history_ok=true;
   int total=HistoryDealsTotal();
   for(int i=0;i<total;i++)
     {
      ulong deal=HistoryDealGetTicket(i);
      if(deal==0 || HistoryDealGetString(deal,DEAL_SYMBOL)!=_Symbol ||
         HistoryDealGetInteger(deal,DEAL_MAGIC)!=InpMagic)
         continue;
      double row=HistoryDealGetDouble(deal,DEAL_PROFIT)+HistoryDealGetDouble(deal,DEAL_COMMISSION)+
                 HistoryDealGetDouble(deal,DEAL_SWAP)+HistoryDealGetDouble(deal,DEAL_FEE);
      net+=row;
     }
   return net;
  }

int ConsecutiveLosingPositionsSince(const datetime from_time,bool &history_ok)
  {
   history_ok=false;
   if(!HistorySelect(from_time,TimeCurrent()))
      return 0;
   history_ok=true;
   ulong position_ids[];
   double position_net[];
   bool has_exit[];
   int total=HistoryDealsTotal();
   for(int i=0;i<total;i++)
     {
      ulong deal=HistoryDealGetTicket(i);
      if(deal==0 || HistoryDealGetString(deal,DEAL_SYMBOL)!=_Symbol ||
         HistoryDealGetInteger(deal,DEAL_MAGIC)!=InpMagic)
         continue;
      ulong position_id=(ulong)HistoryDealGetInteger(deal,DEAL_POSITION_ID);
      if(position_id==0)
         continue;
      int index=FindPositionId(position_ids,position_id);
      if(index<0)
        {
         index=ArraySize(position_ids);
         ArrayResize(position_ids,index+1);
         ArrayResize(position_net,index+1);
         ArrayResize(has_exit,index+1);
         position_ids[index]=position_id;
         position_net[index]=0.0;
         has_exit[index]=false;
        }
      position_net[index]+=HistoryDealGetDouble(deal,DEAL_PROFIT)+
                           HistoryDealGetDouble(deal,DEAL_COMMISSION)+
                           HistoryDealGetDouble(deal,DEAL_SWAP)+
                           HistoryDealGetDouble(deal,DEAL_FEE);
      ENUM_DEAL_ENTRY entry=(ENUM_DEAL_ENTRY)HistoryDealGetInteger(deal,DEAL_ENTRY);
      if(entry==DEAL_ENTRY_OUT || entry==DEAL_ENTRY_OUT_BY)
         has_exit[index]=true;
     }
   int losses=0;
   for(int i=ArraySize(position_ids)-1;i>=0;i--)
     {
      if(!has_exit[i])
         continue;
      if(position_net[i]<0.0)
         losses++;
      else
         break;
     }
   return losses;
  }

bool RiskGuardsAllow()
  {
   if(InpEmergencyBlockNewEntries)
      return false;
   double equity=AccountInfoDouble(ACCOUNT_EQUITY);
   if(equity<=0.0)
      return false;
   g_peak_equity=MathMax(g_peak_equity,equity);
   double account_dd=(g_peak_equity-equity)/g_peak_equity*100.0;
   if(account_dd>=InpMaxAccountDrawdownPct)
      return false;
   bool day_count_ok=false;
   bool streak_ok=false;
   bool day_net_ok=false;
   bool week_net_ok=false;
   int day_trades=EntryPositionCountSince(StartOfDay(TimeCurrent()),day_count_ok);
   int streak=ConsecutiveLosingPositionsSince(StartOfWeek(TimeCurrent()),streak_ok);
   double day_net=RealizedNetSince(StartOfDay(TimeCurrent()),day_net_ok);
   double week_net=RealizedNetSince(StartOfWeek(TimeCurrent()),week_net_ok);
   if(!day_count_ok || !streak_ok || !day_net_ok || !week_net_ok)
      return false;
   double day_start=MathMax(1.0,AccountInfoDouble(ACCOUNT_BALANCE)-day_net);
   if(day_trades>=InpMaxTradesPerDay || streak>=InpMaxConsecutiveLosses || (-day_net/day_start*100.0)>=InpMaxDailyLossPct)
      return false;
   double week_start=MathMax(1.0,AccountInfoDouble(ACCOUNT_BALANCE)-week_net);
   if((-week_net/week_start*100.0)>=InpMaxWeeklyLossPct)
      return false;
   return true;
  }

double NormalizeVolume(const double raw)
  {
   double minimum=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN);
   double maximum=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX);
   double step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);
   if(minimum<=0.0 || maximum<minimum || step<=0.0 || raw<minimum)
      return 0.0;
   double volume=MathFloor((MathMin(raw,maximum)-minimum)/step+1e-9)*step+minimum;
   int digits=0;
   double probe=step;
   while(digits<8 && MathAbs(probe-MathRound(probe))>1e-9)
     {
      probe*=10.0;
      digits++;
     }
   return NormalizeDouble(volume,digits);
  }

double EstimatedExecutionCostOneLot(const ENUM_ORDER_TYPE type,const double entry)
  {
   double total=InpEstimatedCommissionPerLotRoundTurn;
   if(InpEstimatedSlippagePoints<=0)
      return total;
   double adverse=(type==ORDER_TYPE_BUY
                   ? entry-(double)InpEstimatedSlippagePoints*_Point
                   : entry+(double)InpEstimatedSlippagePoints*_Point);
   double slippage_pnl=0.0;
   if(!OrderCalcProfit(type,_Symbol,1.0,entry,adverse,slippage_pnl))
      return DBL_MAX;
   return total+MathAbs(slippage_pnl);
  }

double RiskSizedVolume(const int direction,const double entry,const double stop,double &risk_account)
  {
   double loss_one_lot=0.0;
   ENUM_ORDER_TYPE type=(direction>0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL);
   if(!OrderCalcProfit(type,_Symbol,1.0,entry,stop,loss_one_lot) || loss_one_lot>=0.0)
      return 0.0;
   double execution_cost_one_lot=EstimatedExecutionCostOneLot(type,entry);
   if(!MathIsValidNumber(execution_cost_one_lot) || execution_cost_one_lot<0.0 || execution_cost_one_lot==DBL_MAX)
      return 0.0;
   double total_loss_one_lot=MathAbs(loss_one_lot)+execution_cost_one_lot;
   if(total_loss_one_lot<=0.0)
      return 0.0;
   risk_account=AccountInfoDouble(ACCOUNT_EQUITY)*InpRiskPercent/100.0;
   double volume=NormalizeVolume(risk_account/total_loss_one_lot);
   if(volume<=0.0)
      return 0.0;
   double normalized_loss=0.0;
   if(!OrderCalcProfit(type,_Symbol,volume,entry,stop,normalized_loss))
      return 0.0;
   double normalized_total_loss=MathAbs(normalized_loss)+volume*execution_cost_one_lot;
   if(normalized_total_loss>risk_account*1.05)
      return 0.0;
   risk_account=normalized_total_loss;
   return volume;
  }

bool StopGeometryValid(const int direction,const double entry,const double stop,const double target)
  {
   long stops_level=SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL);
   double minimum=(double)stops_level*_Point;
   if(direction>0)
      return stop<entry && target>entry && entry-stop>=minimum && target-entry>=minimum;
   return stop>entry && target<entry && stop-entry>=minimum && entry-target>=minimum;
  }

bool BrokerTradingAllows(const int direction)
  {
   if(!TerminalInfoInteger(TERMINAL_TRADE_ALLOWED) ||
      !MQLInfoInteger(MQL_TRADE_ALLOWED) ||
      !AccountInfoInteger(ACCOUNT_TRADE_ALLOWED))
      return false;
   ENUM_SYMBOL_TRADE_MODE mode=(ENUM_SYMBOL_TRADE_MODE)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_MODE);
   if(mode==SYMBOL_TRADE_MODE_DISABLED || mode==SYMBOL_TRADE_MODE_CLOSEONLY)
      return false;
   if(direction>0 && mode==SYMBOL_TRADE_MODE_SHORTONLY)
      return false;
   if(direction<0 && mode==SYMBOL_TRADE_MODE_LONGONLY)
      return false;
   return true;
  }

bool ModificationGeometryValid(const ENUM_POSITION_TYPE type,const double new_stop)
  {
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick) || tick.ask<=0.0 || tick.bid<=0.0)
      return false;
   long stops_level=SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL);
   long freeze_level=SymbolInfoInteger(_Symbol,SYMBOL_TRADE_FREEZE_LEVEL);
   double minimum=(double)MathMax(stops_level,freeze_level)*_Point;
   if(type==POSITION_TYPE_BUY)
      return new_stop<tick.bid && tick.bid-new_stop>=minimum;
   return new_stop>tick.ask && new_stop-tick.ask>=minimum;
  }

ENUM_ORDER_TYPE_FILLING FillingModeForSymbol()
  {
   int flags=(int)SymbolInfoInteger(_Symbol,SYMBOL_FILLING_MODE);
   if((flags&SYMBOL_FILLING_FOK)==SYMBOL_FILLING_FOK)
      return ORDER_FILLING_FOK;
   if((flags&SYMBOL_FILLING_IOC)==SYMBOL_FILLING_IOC)
      return ORDER_FILLING_IOC;
   return ORDER_FILLING_RETURN;
  }

bool PreflightMarketOrder(const int direction,const double volume,const double entry,
                          const double stop,const double target)
  {
   if(!BrokerTradingAllows(direction) || ForeignSymbolPositionExists() || ForeignSymbolOrderExists())
      return false;
   MqlTradeRequest request={};
   MqlTradeCheckResult check={};
   request.action=TRADE_ACTION_DEAL;
   request.magic=(ulong)InpMagic;
   request.symbol=_Symbol;
   request.volume=volume;
   request.type=(direction>0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL);
   request.price=entry;
   request.sl=stop;
   request.tp=target;
   request.deviation=(ulong)MathMax(1,InpMaxSpreadPoints);
   request.type_filling=FillingModeForSymbol();
   request.type_time=ORDER_TIME_GTC;
   request.comment=HYPOTHESIS_ID;
   if(!OrderCheck(request,check))
     {
      PrintFormat("UPS OrderCheck failed retcode=%u comment=%s margin=%.2f free=%.2f",
                  check.retcode,check.comment,check.margin,check.margin_free);
      return false;
     }
   return true;
  }

bool OpenFromSignal(const SignalPlan &signal)
  {
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick) || tick.ask<=0.0 || tick.bid<=0.0)
      return false;
   if((tick.ask-tick.bid)/_Point>InpMaxSpreadPoints)
      return false;
   double entry=(signal.direction>0 ? tick.ask : tick.bid);
   double buffer=(double)InpStopBufferPoints*_Point;
   double stop=(signal.direction>0 ? signal.sweep_extreme-buffer : signal.sweep_extreme+buffer);
   double risk_distance=MathAbs(entry-stop);
   double target=(signal.direction>0 ? entry+InpTargetRR*risk_distance : entry-InpTargetRR*risk_distance);
   stop=NormalizeDouble(stop,_Digits);
   target=NormalizeDouble(target,_Digits);
   if(!StopGeometryValid(signal.direction,entry,stop,target))
      return false;
   double risk_account=0.0;
   double volume=RiskSizedVolume(signal.direction,entry,stop,risk_account);
   if(volume<=0.0)
      return false;
   if(!PreflightMarketOrder(signal.direction,volume,entry,stop,target))
     {
      SetExecutionState(EXEC_RECOVERING_ERROR,"market-order preflight rejected");
      return false;
     }
   g_pending_risk_points=risk_distance/_Point;
   g_pending_risk_account=risk_account;
   SetExecutionState(EXEC_PLACING_ORDER,"sending synchronous market request");
   bool sent=(signal.direction>0 ? trade.Buy(volume,_Symbol,0.0,stop,target,HYPOTHESIS_ID)
                                 : trade.Sell(volume,_Symbol,0.0,stop,target,HYPOTHESIS_ID));
   if(!sent || (trade.ResultRetcode()!=TRADE_RETCODE_DONE && trade.ResultRetcode()!=TRADE_RETCODE_DONE_PARTIAL))
     {
      PrintFormat("UPS order rejected sent=%s retcode=%u %s",sent ? "true" : "false",trade.ResultRetcode(),trade.ResultRetcodeDescription());
      g_pending_risk_points=0.0;
      g_pending_risk_account=0.0;
      SetExecutionState(EXEC_RECOVERING_ERROR,"broker rejected market request");
      return false;
     }
   if(OwnedPositionTicket()!=0)
      SetExecutionState(EXEC_MANAGING_POSITION,"position visible after market request");
   else
      SetExecutionState(EXEC_WAITING_FILL,"accepted request awaiting position event");
   return true;
  }

double InitialRiskDistance(const ulong ticket)
  {
   if(!PositionSelectByTicket(ticket))
      return 0.0;
   ulong position_id=(ulong)PositionGetInteger(POSITION_IDENTIFIER);
   if(position_id==g_initial_risk_position_identifier && g_initial_risk_distance>0.0)
      return g_initial_risk_distance;
   double entry=PositionGetDouble(POSITION_PRICE_OPEN);
   double stop=PositionGetDouble(POSITION_SL);
   if(stop>0.0 && MathAbs(entry-stop)>_Point*0.5)
      return MathAbs(entry-stop);
   double target=PositionGetDouble(POSITION_TP);
   if(InpTargetRR>0.0 && target>0.0)
      return MathAbs(target-entry)/InpTargetRR;
   return 0.0;
  }

bool TradeResultCompleted(const bool sent)
  {
   if(!sent)
      return false;
   uint retcode=trade.ResultRetcode();
   return retcode==TRADE_RETCODE_DONE || retcode==TRADE_RETCODE_DONE_PARTIAL;
  }

void ManageOwnedPosition()
  {
   ulong ticket=OwnedPositionTicket();
   if(ticket==0 || !PositionSelectByTicket(ticket))
      return;
   double entry=PositionGetDouble(POSITION_PRICE_OPEN);
   double stop=PositionGetDouble(POSITION_SL);
   double target=PositionGetDouble(POSITION_TP);
   ENUM_POSITION_TYPE type=(ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE);
   datetime opened=(datetime)PositionGetInteger(POSITION_TIME);
   if(TimeCurrent()-opened>=InpMaxHoldMinutes*60)
     {
      if(!TradeResultCompleted(trade.PositionClose(ticket)))
         Print("UPS max-hold close failed: ",trade.ResultRetcodeDescription());
      return;
     }
   double risk_distance=InitialRiskDistance(ticket);
   if(risk_distance<=0.0)
      return;
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick))
      return;
   double current=(type==POSITION_TYPE_BUY ? tick.bid : tick.ask);
   double favorable=(type==POSITION_TYPE_BUY ? current-entry : entry-current);
   if(favorable<InpBreakEvenR*risk_distance)
      return;
   double break_even=NormalizeDouble(entry,_Digits);
   bool needs_move=(type==POSITION_TYPE_BUY ? stop<break_even : stop>break_even || stop==0.0);
   if(needs_move && !ModificationGeometryValid(type,break_even))
      return;
   if(needs_move && !TradeResultCompleted(trade.PositionModify(ticket,break_even,target)))
      Print("UPS break-even modify failed: ",trade.ResultRetcodeDescription());
  }

ENUM_ORDER_TYPE EntryTypeForPosition(const ulong position_id)
  {
   if(position_id==g_position_identifier)
      return g_entry_order_type;
   if(HistorySelect(0,TimeCurrent()))
     {
      int total=HistoryDealsTotal();
      for(int i=0;i<total;i++)
        {
         ulong deal=HistoryDealGetTicket(i);
         if(deal==0 || (ulong)HistoryDealGetInteger(deal,DEAL_POSITION_ID)!=position_id)
            continue;
         ENUM_DEAL_ENTRY entry=(ENUM_DEAL_ENTRY)HistoryDealGetInteger(deal,DEAL_ENTRY);
         if(entry!=DEAL_ENTRY_IN && entry!=DEAL_ENTRY_INOUT)
            continue;
         ENUM_DEAL_TYPE type=(ENUM_DEAL_TYPE)HistoryDealGetInteger(deal,DEAL_TYPE);
         return type==DEAL_TYPE_SELL ? ORDER_TYPE_SELL : ORDER_TYPE_BUY;
        }
     }
   return ORDER_TYPE_BUY;
  }

ulong PositionTicketByIdentifier(const ulong position_id)
  {
   for(int i=PositionsTotal()-1;i>=0;i--)
     {
      ulong ticket=PositionGetTicket(i);
      if(ticket>0 && PositionSelectByTicket(ticket) && (ulong)PositionGetInteger(POSITION_IDENTIFIER)==position_id)
         return ticket;
     }
   return 0;
  }

bool PositionIdentifierExists(const ulong position_id)
  {
   return PositionTicketByIdentifier(position_id)>0;
  }

void CaptureInitialRiskFromPosition(const ulong position_id)
  {
   ulong ticket=PositionTicketByIdentifier(position_id);
   if(ticket==0 || !PositionSelectByTicket(ticket))
      return;
   double entry=PositionGetDouble(POSITION_PRICE_OPEN);
   double stop=PositionGetDouble(POSITION_SL);
   double distance=MathAbs(entry-stop);
   if(entry<=0.0 || stop<=0.0 || distance<=_Point*0.5)
      return;
   g_initial_risk_position_identifier=position_id;
   g_initial_risk_distance=distance;
  }

void LogLifecycleDeal(const ulong deal)
  {
   if(!InpEnableTelemetry || g_telemetry_handle==INVALID_HANDLE || !HistoryDealSelect(deal))
      return;
   if(HistoryDealGetString(deal,DEAL_SYMBOL)!=_Symbol || HistoryDealGetInteger(deal,DEAL_MAGIC)!=InpMagic)
      return;
   ENUM_DEAL_ENTRY entry=(ENUM_DEAL_ENTRY)HistoryDealGetInteger(deal,DEAL_ENTRY);
   if(entry!=DEAL_ENTRY_IN && entry!=DEAL_ENTRY_INOUT && entry!=DEAL_ENTRY_OUT && entry!=DEAL_ENTRY_OUT_BY)
      return;
   ulong position_id=(ulong)HistoryDealGetInteger(deal,DEAL_POSITION_ID);
   ENUM_DEAL_TYPE deal_type=(ENUM_DEAL_TYPE)HistoryDealGetInteger(deal,DEAL_TYPE);
   ENUM_ORDER_TYPE entry_type=EntryTypeForPosition(position_id);
   bool is_open=(entry==DEAL_ENTRY_IN || entry==DEAL_ENTRY_INOUT);
   if(is_open)
     {
      entry_type=(deal_type==DEAL_TYPE_SELL ? ORDER_TYPE_SELL : ORDER_TYPE_BUY);
      bool new_position=(g_position_identifier!=position_id);
      if(g_position_identifier!=0 && new_position)
        {
         g_previous_position_identifier=g_position_identifier;
         g_previous_risk_points=g_planned_risk_points;
         g_previous_risk_account=g_planned_risk_account;
        }
      g_position_identifier=position_id;
      g_entry_order_type=entry_type;
      // A broker may split a market fill into multiple entry deals. Only the
      // first callback owns the pending plan; later partial fills must not
      // overwrite lifecycle risk with zero.
      if(g_pending_risk_points>0.0 && g_pending_risk_account>0.0)
        {
         g_planned_risk_points=g_pending_risk_points;
         g_planned_risk_account=g_pending_risk_account;
         g_pending_risk_points=0.0;
         g_pending_risk_account=0.0;
        }
      CaptureInitialRiskFromPosition(position_id);
      if(g_initial_risk_position_identifier==position_id && g_initial_risk_distance>0.0)
         g_planned_risk_points=g_initial_risk_distance/_Point;
     }
   bool final_close=(!is_open && !PositionIdentifierExists(position_id));
   string action=(is_open ? "OPEN" : (final_close ? "CLOSE" : "CLOSE_PARTIAL"));
   string order_type=(entry_type==ORDER_TYPE_SELL ? "SELL" : "BUY");
   double profit=HistoryDealGetDouble(deal,DEAL_PROFIT);
   double commission=HistoryDealGetDouble(deal,DEAL_COMMISSION);
   double swap=HistoryDealGetDouble(deal,DEAL_SWAP);
   double fee=HistoryDealGetDouble(deal,DEAL_FEE);
   double net=profit+commission+swap+fee;
   datetime event_time=(datetime)HistoryDealGetInteger(deal,DEAL_TIME);
   double lifecycle_risk_points=0.0;
   double lifecycle_risk_account=0.0;
   if(position_id==g_position_identifier)
     {
      lifecycle_risk_points=g_planned_risk_points;
      lifecycle_risk_account=g_planned_risk_account;
     }
   else if(position_id==g_previous_position_identifier)
     {
      lifecycle_risk_points=g_previous_risk_points;
      lifecycle_risk_account=g_previous_risk_account;
     }
   FileWrite(g_telemetry_handle,
             TimeToString(event_time,TIME_DATE|TIME_SECONDS),action,order_type,
             DoubleToString(HistoryDealGetDouble(deal,DEAL_VOLUME),8),
             DoubleToString(HistoryDealGetDouble(deal,DEAL_PRICE),_Digits),_Symbol,
             StringFormat("%I64u",position_id),DoubleToString(lifecycle_risk_points,8),
             DoubleToString(lifecycle_risk_account,8),StringFormat("%I64u",deal),
             DoubleToString(profit,8),DoubleToString(commission,8),
             DoubleToString(swap,8),DoubleToString(fee,8),DoubleToString(net,8),
             final_close ? "1" : "0");
   FileFlush(g_telemetry_handle);
   if(final_close)
     {
      if(position_id==g_position_identifier)
        {
         g_position_identifier=0;
         g_planned_risk_points=0.0;
         g_planned_risk_account=0.0;
        }
      if(position_id==g_initial_risk_position_identifier)
        {
         g_initial_risk_position_identifier=0;
         g_initial_risk_distance=0.0;
        }
      if(position_id==g_previous_position_identifier)
        {
         g_previous_position_identifier=0;
         g_previous_risk_points=0.0;
         g_previous_risk_account=0.0;
        }
     }
  }

void OnTradeTransaction(const MqlTradeTransaction &trans,
                        const MqlTradeRequest &request,
                        const MqlTradeResult &result)
  {
   if(trans.type==TRADE_TRANSACTION_DEAL_ADD && trans.deal>0)
     {
      LogLifecycleDeal(trans.deal);
      if(!TradingMutationAllowed() || !HistoryDealSelect(trans.deal) ||
         HistoryDealGetString(trans.deal,DEAL_SYMBOL)!=_Symbol ||
         HistoryDealGetInteger(trans.deal,DEAL_MAGIC)!=InpMagic)
         return;
      ENUM_DEAL_ENTRY entry=(ENUM_DEAL_ENTRY)HistoryDealGetInteger(trans.deal,DEAL_ENTRY);
      ulong position_id=(ulong)HistoryDealGetInteger(trans.deal,DEAL_POSITION_ID);
      if(entry==DEAL_ENTRY_IN || entry==DEAL_ENTRY_INOUT)
         SetExecutionState(EXEC_MANAGING_POSITION,"entry deal confirmed");
      else if((entry==DEAL_ENTRY_OUT || entry==DEAL_ENTRY_OUT_BY) &&
              !PositionIdentifierExists(position_id))
         SetExecutionState(EXEC_IDLE,"final close deal confirmed");
      else if(entry==DEAL_ENTRY_OUT || entry==DEAL_ENTRY_OUT_BY)
         SetExecutionState(EXEC_MANAGING_POSITION,"partial close deal confirmed");
     }
  }

void OnTick()
  {
   double equity=AccountInfoDouble(ACCOUNT_EQUITY);
   if(equity>g_peak_equity)
     {
      g_peak_equity=equity;
      PersistPeakEquityState();
     }
   ulong owned=OwnedPositionTicket();
   if(TradingMutationAllowed() && owned!=0)
     {
      SetExecutionState(EXEC_MANAGING_POSITION,"owned position present on tick");
      ManageOwnedPosition();
     }
   else if(!TradingMutationAllowed())
      SetExecutionState(EXEC_ALERT_ONLY,"trade mutation disabled");
   else if(g_execution_state==EXEC_MANAGING_POSITION || g_execution_state==EXEC_WAITING_FILL)
      SetExecutionState(EXEC_IDLE,"no owned position present");
   g_new_bar_ready=false;
   RefreshNewM5BarGate();
   if(!g_new_bar_ready)
      return;
   if(OwnedPositionTicket()!=0 || !SessionOpen(g_last_bar) || !NewsGuardAllows())
      return;
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick))
      return;
   double spread_points=(tick.ask-tick.bid)/_Point;
   if(spread_points>InpMaxSpreadPoints)
      return;
   SignalPlan signal=EvaluateClosedSignal();
   CountSignalDecision(signal.reject_reason);
   if(!signal.valid)
      return;
   PrintFormat("UPS signal dir=%d score=%d bodyATR=%.3f overlap=%.3f mode=%s",
               signal.direction,signal.score,signal.body_atr,signal.overlap_ratio,
               InpResearchAutoMode ? "RESEARCH_AUTO" : "ALERT_ONLY");
   if(!WriteAlertCasebook(signal,spread_points))
     {
      Print("UPS alert casebook write failed; signal handling stopped.");
      return;
     }
   if(!TradingMutationAllowed())
      return;
   if(!RiskGuardsAllow())
     {
      SetExecutionState(EXEC_LOCKED_RISK,"risk guard blocked new entry");
      return;
     }
   if(g_execution_state==EXEC_LOCKED_RISK || g_execution_state==EXEC_RECOVERING_ERROR)
      SetExecutionState(EXEC_IDLE,"risk and execution preconditions restored");
   OpenFromSignal(signal);
  }
