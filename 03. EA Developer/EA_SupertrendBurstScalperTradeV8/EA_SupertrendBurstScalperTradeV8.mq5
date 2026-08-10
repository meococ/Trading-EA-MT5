#property strict
#property version   "8.00"
#property description "H1 Supertrend flip baseline with stable lifecycle replay and bounded margin evidence."

input string InpHypothesisId        = "HYP-STBS-XAUUSD-M15-021";
input string InpVariantTag          = "STBS_H1_FLIP_M15_BURST_TRADE_V8_STABLE_LIFECYCLE";
input bool   InpAuditOnly           = false;
input bool   InpEnableTelemetry     = true;
input long   InpMagic               = 5604121;
input double InpRiskPercent         = 0.25;
input double InpStopAtrMult         = 1.00;
input double InpTargetRR            = 1.50;
input int    InpMaxHoldBars         = 8;
input double InpMaxDailyLossPct     = 1.50;
input double InpMaxAccountDrawdownPct = 8.00;
input int    InpFridayEntryCutoffUtcMinutes = 18*60;
input int    InpFridayFlattenUtcMinutes     = 20*60;
input int    InpDeviationPoints     = 20;
input double InpMaxNewPositionMarginPct     = 5.00;
input double InpMinProjectedMarginLevelPct  = 2000.00;
input double InpPercentStopoutHeadroomFactor = 1.25;
input double InpMoneyHeadroomReserveFactor   = 0.20;
input double InpMoneyFreeEquityFloorPct      = 1.00;

const datetime SOURCE_START_TIME = D'2004.06.11 07:00:00';
const datetime DESIGN_START_TIME = D'2018.01.01 02:00:00';
const datetime DESIGN_END_TIME   = D'2023.01.01 02:00:00';
const int ST_ATR_PERIOD          = 10;
const double ST_FACTOR           = 3.0;
const int M15_ATR_PERIOD         = 14;
const int STATE_DOWN             = -1;
const int STATE_UP               = 1;
const int REQUEST_VISIBILITY_TIMEOUT_SECONDS = 60;
const string EA_NAME              = "EA_SupertrendBurstScalperTradeV8";
const string TELEMETRY_PROFILE    = "lifecycle-v3";

enum ExecutionState
{
   EXEC_FLAT=0,
   EXEC_ENTRY_PENDING=1,
   EXEC_OPEN=2,
   EXEC_EXIT_PENDING=3,
   EXEC_MANAGE_ONLY=4
};

enum ExitIntent
{
   EXIT_NONE=0,
   EXIT_OPPOSITE_FLIP=1,
   EXIT_TIME=2,
   EXIT_FRIDAY_WEEKEND=3,
   EXIT_PROTECTION_INVALID=4,
   EXIT_ENTRY_CLOCK_UNKNOWN=5,
   EXIT_RUNTIME_FAULT=6
};

enum MarginSafetyResult
{
   MARGIN_SAFETY_FATAL=-1,
   MARGIN_SAFETY_UNSAFE=0,
   MARGIN_SAFETY_PASS=1
};

struct EntryPlan
{
   ENUM_ORDER_TYPE order_type;
   ENUM_ORDER_TYPE_FILLING filling;
   double entry;
   double stop;
   double target;
   double volume;
   double required_margin;
   double required_free_margin;
   double projected_margin_free;
   double projected_margin_level;
};

datetime g_current_h1_open=0;
datetime g_current_m15_open=0;
datetime g_last_h1_time=0;
datetime g_entry_m15_open=0;
datetime g_entry_block_until=0;
double   g_st_atr=0.0;
double   g_final_upper=0.0;
double   g_final_lower=0.0;
double   g_supertrend=0.0;
double   g_prior_close=0.0;
double   g_peak_equity=0.0;
double   g_day_start_equity=0.0;
int      g_st_state=0;
int      g_day_key=0;
int      g_m15_atr_handle=INVALID_HANDLE;
bool     g_runtime_failed=false;
bool     g_risk_anchors_ready=false;
ExecutionState g_exec_state=EXEC_FLAT;
ExitIntent g_exit_intent=EXIT_NONE;
ulong    g_pending_order_id=0;
ulong    g_pending_deal_id=0;
uint     g_pending_request_id=0;
datetime g_request_started=0;
int      g_transient_flat_ticks=0;
long     g_expected_direction=0;
double   g_expected_volume=0.0;
double   g_expected_stop=0.0;
double   g_expected_target=0.0;
int      g_reverse_direction=0;
double   g_reverse_atr=0.0;
datetime g_reverse_decision=0;
ulong    g_counted_position_identifier=0;
bool     g_had_owned_position=false;
long     g_execution_generation=0;
string   g_execution_payload_cache="";
bool     g_execution_payload_ready=false;
bool     g_resumed_execution_state=false;
long     g_risk_generation=0;
long     g_raw_events=0;
long     g_executable_events=0;
long     g_gap_events=0;
long     g_long_events=0;
long     g_short_events=0;
long     g_atr_ready_events=0;
long     g_geometry_ready_events=0;
long     g_margin_ready_events=0;
long     g_margin_rejects=0;
long     g_margin_emergencies=0;
long     g_actual_margin_safe_positions=0;
long     g_forced_stopouts=0;
long     g_entries_submitted=0;
long     g_entry_rejects=0;
long     g_closes_submitted=0;
string   g_run_id="";
string   g_lifecycle_name="";
string   g_run_meta_name="";
int      g_lifecycle_handle=INVALID_HANDLE;
ulong    g_telemetry_position_id=0;
double   g_telemetry_entry_stop=0.0;
long     g_telemetry_entry_direction=0;
long     g_lifecycle_rows=0;
long     g_lifecycle_open_rows=0;
long     g_lifecycle_final_close_rows=0;
long     g_lifecycle_positions_opened=0;
long     g_lifecycle_positions_final_closed=0;
ulong    g_logged_deals[];
ulong    g_open_position_ids[];
ulong    g_closed_position_ids[];
ulong    g_forced_stopout_deals[];
ulong    g_pending_lifecycle_deals[];
datetime g_lifecycle_reconcile_started=0;
ulong    g_last_actual_margin_logged_position_id=0;


string StateName(const int state)
{
   if(state==STATE_UP)
      return "UP";
   if(state==STATE_DOWN)
      return "DOWN";
   return "UNAVAILABLE";
}


bool WriteRunMeta()
{
   if(!InpEnableTelemetry || g_run_meta_name=="")
      return true;
   const int handle=FileOpen(g_run_meta_name,FILE_WRITE|FILE_TXT|FILE_ANSI);
   if(handle==INVALID_HANDLE)
      return false;
   const string payload=StringFormat(
      "{\"schema_version\":\"alphafactory_run_meta.v1\",\"run_id\":\"%s\","
      "\"ea_name\":\"%s\",\"symbol\":\"%s\",\"telemetry_profile\":\"%s\","
      "\"hypothesis_id\":\"%s\",\"variant_tag\":\"%s\",\"magic\":%I64d,"
      "\"promotion_eligible\":false,\"audit_only\":%s,"
      "\"diagnostic\":{\"raw\":%I64d,\"executable\":%I64d,\"gaps\":%I64d,"
      "\"long\":%I64d,\"short\":%I64d,\"atr_ready\":%I64d,"
      "\"geometry_ready\":%I64d,\"margin_ready\":%I64d,\"margin_rejects\":%I64d,"
      "\"margin_emergencies\":%I64d,\"actual_margin_safe_positions\":%I64d,"
      "\"forced_stopouts\":%I64d,"
      "\"entries\":%I64d,\"entry_rejects\":%I64d,\"closes\":%I64d,"
      "\"lifecycle_rows\":%I64d,\"lifecycle_open_rows\":%I64d,"
      "\"lifecycle_final_close_rows\":%I64d,\"lifecycle_positions_opened\":%I64d,"
      "\"lifecycle_positions_final_closed\":%I64d,\"runtime_failed\":%s}}",
      g_run_id,EA_NAME,_Symbol,TELEMETRY_PROFILE,InpHypothesisId,InpVariantTag,
      InpMagic,InpAuditOnly ? "true" : "false",g_raw_events,g_executable_events,
      g_gap_events,g_long_events,g_short_events,g_atr_ready_events,
      g_geometry_ready_events,g_margin_ready_events,g_margin_rejects,
      g_margin_emergencies,g_actual_margin_safe_positions,g_forced_stopouts,
      g_entries_submitted,g_entry_rejects,
      g_closes_submitted,g_lifecycle_rows,g_lifecycle_open_rows,
      g_lifecycle_final_close_rows,g_lifecycle_positions_opened,
      g_lifecycle_positions_final_closed,g_runtime_failed ? "true" : "false");
   FileWriteString(handle,payload);
   FileClose(handle);
   return true;
}


bool LoadExistingLifecycleState()
{
   if(g_lifecycle_handle==INVALID_HANDLE ||
      !FileSeek(g_lifecycle_handle,0,SEEK_SET))
      return false;
   const string expected[17]={"event_time","action","order_type","volume","price",
                              "symbol","position_id","risk_pts","initial_risk_account",
                              "deal","deal_reason","deal_profit","deal_commission",
                              "deal_swap","deal_fee","deal_net","is_final_close"};
   for(int column=0;column<17;column++)
      if(FileReadString(g_lifecycle_handle)!=expected[column])
         return false;
   while(!FileIsEnding(g_lifecycle_handle))
   {
      string fields[17];
      for(int column=0;column<17;column++)
         fields[column]=FileReadString(g_lifecycle_handle);
      if(fields[0]=="" && fields[9]=="")
         break;
      const long deal_value=StringToInteger(fields[9]);
      const long position_value=StringToInteger(fields[6]);
      if(deal_value<=0 || position_value<=0 || fields[5]!=_Symbol ||
         !MarkDealLogged((ulong)deal_value))
         return false;
      g_lifecycle_rows++;
      if(fields[1]=="OPEN")
      {
         g_lifecycle_open_rows++;
         bool added=false;
         if(!MarkUniquePosition(g_open_position_ids,(ulong)position_value,added))
            return false;
         if(added)
            g_lifecycle_positions_opened++;
      }
      else if(fields[1]=="CLOSE" && fields[16]=="1")
      {
         g_lifecycle_final_close_rows++;
         bool added=false;
         if(!MarkUniquePosition(g_closed_position_ids,(ulong)position_value,added))
            return false;
         if(added)
            g_lifecycle_positions_final_closed++;
      }
      else if(fields[1]!="CLOSE_PARTIAL")
         return false;
      if(fields[10]=="DEAL_REASON_SO")
      {
         if(!RegisterForcedStopout((ulong)deal_value,(ulong)position_value))
            return false;
      }
   }
   return FileSeek(g_lifecycle_handle,0,SEEK_END);
}


bool OpenTelemetry()
{
   if(!InpEnableTelemetry)
      return false;
   g_run_id=StringFormat("%s_%I64d",InpHypothesisId,InpMagic);
   g_lifecycle_name=StringFormat("%s_LifecycleTrades_%s.csv",_Symbol,g_run_id);
   g_run_meta_name=StringFormat("%s_RunMeta_%s.json",_Symbol,g_run_id);
   const bool existing=FileIsExist(g_lifecycle_name);
   if(existing!=g_resumed_execution_state)
   {
      PrintFormat("STBS_FATAL|telemetry_restart_contract_mismatch|existing=%s|resumed=%s",
                  existing ? "true" : "false",
                  g_resumed_execution_state ? "true" : "false");
      return false;
   }
   g_lifecycle_handle=FileOpen(g_lifecycle_name,
                               FILE_READ|FILE_WRITE|FILE_CSV|FILE_ANSI,',');
   if(g_lifecycle_handle==INVALID_HANDLE)
      return false;
   if(existing)
   {
      if(!LoadExistingLifecycleState())
         return false;
   }
   else
   {
      FileWrite(g_lifecycle_handle,"event_time","action","order_type","volume","price",
                "symbol","position_id","risk_pts","initial_risk_account","deal",
                "deal_reason","deal_profit","deal_commission","deal_swap","deal_fee",
                "deal_net","is_final_close");
   }
   FileFlush(g_lifecycle_handle);
   return WriteRunMeta();
}


bool ResolvePositionOwnership(const ulong position_id,bool &opening_found,bool &owned)
{
   opening_found=false;
   owned=false;
   if(position_id==0 ||
      !HistorySelect(SOURCE_START_TIME,TimeCurrent()+PeriodSeconds(PERIOD_H1)))
      return false;
   const int total=HistoryDealsTotal();
   for(int index=0;index<total;index++)
   {
      const ulong deal=HistoryDealGetTicket(index);
      if(deal==0)
         return false;
      if((ulong)HistoryDealGetInteger(deal,DEAL_POSITION_ID)!=position_id ||
         HistoryDealGetString(deal,DEAL_SYMBOL)!=_Symbol ||
         (ENUM_DEAL_ENTRY)HistoryDealGetInteger(deal,DEAL_ENTRY)!=DEAL_ENTRY_IN)
         continue;
      opening_found=true;
      if((long)HistoryDealGetInteger(deal,DEAL_MAGIC)==InpMagic)
         owned=true;
   }
   return true;
}


bool DealAlreadyLogged(const ulong deal)
{
   const int total=ArraySize(g_logged_deals);
   for(int index=0;index<total;index++)
      if(g_logged_deals[index]==deal)
         return true;
   return false;
}


bool MarkDealLogged(const ulong deal)
{
   if(DealAlreadyLogged(deal))
      return true;
   const int total=ArraySize(g_logged_deals);
   if(ArrayResize(g_logged_deals,total+1)!=total+1)
      return false;
   g_logged_deals[total]=deal;
   return true;
}


bool MarkUniquePosition(ulong &items[],const ulong position_id,bool &added)
{
   added=false;
   if(position_id==0)
      return false;
   const int total=ArraySize(items);
   for(int index=0;index<total;index++)
      if(items[index]==position_id)
         return true;
   if(ArrayResize(items,total+1)!=total+1)
      return false;
   items[total]=position_id;
   added=true;
   return true;
}


bool PositionWasLoggedOpen(const ulong position_id)
{
   const int total=ArraySize(g_open_position_ids);
   for(int index=0;index<total;index++)
      if(g_open_position_ids[index]==position_id)
         return true;
   return false;
}


bool RegisterForcedStopout(const ulong deal,const ulong position_id)
{
   bool added=false;
   if(deal==0 || position_id==0 ||
      !MarkUniquePosition(g_forced_stopout_deals,deal,added))
      return false;
   if(added)
   {
      g_forced_stopouts++;
      PrintFormat("STBS_FATAL|broker_stopout|deal=%I64u|position=%I64u",deal,position_id);
   }
   g_runtime_failed=true;
   return true;
}


bool RecoverTelemetryContextFromHistory(const ulong position_id)
{
   if(position_id==0 ||
      !HistorySelect(SOURCE_START_TIME,TimeCurrent()+PeriodSeconds(PERIOD_H1)))
      return false;
   const int total=HistoryDealsTotal();
   for(int index=0;index<total;index++)
   {
      const ulong deal=HistoryDealGetTicket(index);
      if(deal==0 ||
         (ulong)HistoryDealGetInteger(deal,DEAL_POSITION_ID)!=position_id ||
         HistoryDealGetString(deal,DEAL_SYMBOL)!=_Symbol ||
         (ENUM_DEAL_ENTRY)HistoryDealGetInteger(deal,DEAL_ENTRY)!=DEAL_ENTRY_IN ||
         (long)HistoryDealGetInteger(deal,DEAL_MAGIC)!=InpMagic)
         continue;
      const ENUM_DEAL_TYPE type=(ENUM_DEAL_TYPE)HistoryDealGetInteger(deal,DEAL_TYPE);
      const long direction=type==DEAL_TYPE_BUY ? 1 : type==DEAL_TYPE_SELL ? -1 : 0;
      const double entry=HistoryDealGetDouble(deal,DEAL_PRICE);
      const ulong order=(ulong)HistoryDealGetInteger(deal,DEAL_ORDER);
      double stop=0.0;
      if(order!=0 && HistoryOrderSelect(order))
         stop=HistoryOrderGetDouble(order,ORDER_SL);
      if(stop<=0.0 && g_expected_direction==direction)
         stop=g_expected_stop;
      if(direction==0 || !MathIsValidNumber(entry) || entry<=0.0 ||
         !MathIsValidNumber(stop) || stop<=0.0 ||
         (direction>0 && stop>=entry) || (direction<0 && stop<=entry))
         return false;
      g_telemetry_position_id=position_id;
      g_telemetry_entry_stop=stop;
      g_telemetry_entry_direction=direction;
      return true;
   }
   return false;
}


bool PositionDealVolumesThrough(const ulong position_id,const ulong through_deal,
                                 double &open_volume,double &close_volume)
{
   open_volume=0.0;
   close_volume=0.0;
   if(through_deal==0 || !HistoryDealSelect(through_deal))
      return false;
   const long target_time_msc=HistoryDealGetInteger(through_deal,DEAL_TIME_MSC);
   if(target_time_msc<=0 ||
      !HistorySelect(SOURCE_START_TIME,TimeCurrent()+PeriodSeconds(PERIOD_H1)))
      return false;
   const int total=HistoryDealsTotal();
   bool owned_open_found=false;
   for(int index=0;index<total;index++)
   {
      const ulong deal=HistoryDealGetTicket(index);
      if(deal==0)
         return false;
      const long candidate_time_msc=HistoryDealGetInteger(deal,DEAL_TIME_MSC);
      if(candidate_time_msc<=0 || candidate_time_msc>target_time_msc ||
         (candidate_time_msc==target_time_msc && deal>through_deal))
         continue;
      if((ulong)HistoryDealGetInteger(deal,DEAL_POSITION_ID)!=position_id ||
         HistoryDealGetString(deal,DEAL_SYMBOL)!=_Symbol)
         continue;
      const ENUM_DEAL_ENTRY entry=(ENUM_DEAL_ENTRY)HistoryDealGetInteger(deal,DEAL_ENTRY);
      if(entry==DEAL_ENTRY_IN &&
         (long)HistoryDealGetInteger(deal,DEAL_MAGIC)!=InpMagic)
         continue;
      const double volume=HistoryDealGetDouble(deal,DEAL_VOLUME);
      if(!MathIsValidNumber(volume) || volume<=0.0)
         return false;
      if(entry==DEAL_ENTRY_IN)
      {
         owned_open_found=true;
         open_volume+=volume;
      }
      else if(entry==DEAL_ENTRY_OUT || entry==DEAL_ENTRY_OUT_BY)
         close_volume+=volume;
      else
         return false;
   }
   return owned_open_found && open_volume>0.0 && close_volume<=open_volume+1e-8;
}


bool RecoverTelemetryPositionContext()
{
   int count=0;
   ulong ticket=0;
   if(!CountOwnedPositions(count,ticket))
      return false;
   if(count==0)
      return true;
   if(count!=1 || ticket==0 || !PositionSelectByTicket(ticket))
      return false;
   ResetLastError();
   g_telemetry_position_id=(ulong)PositionGetInteger(POSITION_IDENTIFIER);
   g_telemetry_entry_stop=PositionGetDouble(POSITION_SL);
   const ENUM_POSITION_TYPE type=(ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE);
   if(GetLastError()!=0 || g_telemetry_position_id==0 || g_telemetry_entry_stop<=0.0 ||
      (type!=POSITION_TYPE_BUY && type!=POSITION_TYPE_SELL))
      return false;
   g_telemetry_entry_direction=type==POSITION_TYPE_BUY ? 1 : -1;
   return true;
}


bool LifecycleReject(const string stage,const ulong deal)
{
   PrintFormat("STBS_LIFECYCLE_REJECT|stage=%s|deal=%I64u",stage,deal);
   return false;
}


bool LogLifecycleDeal(const ulong deal)
{
   if(!InpEnableTelemetry || g_lifecycle_handle==INVALID_HANDLE || deal==0 ||
       !HistoryDealSelect(deal))
      return LifecycleReject("select_or_handle",deal);
   if(DealAlreadyLogged(deal))
      return true;
   const ENUM_DEAL_ENTRY entry_kind=(ENUM_DEAL_ENTRY)HistoryDealGetInteger(deal,DEAL_ENTRY);
   const ENUM_DEAL_TYPE deal_type=(ENUM_DEAL_TYPE)HistoryDealGetInteger(deal,DEAL_TYPE);
   const ulong position_id=(ulong)HistoryDealGetInteger(deal,DEAL_POSITION_ID);
   const long deal_magic=(long)HistoryDealGetInteger(deal,DEAL_MAGIC);
   const string deal_symbol=HistoryDealGetString(deal,DEAL_SYMBOL);
   const double volume=HistoryDealGetDouble(deal,DEAL_VOLUME);
   const double price=HistoryDealGetDouble(deal,DEAL_PRICE);
   const double profit=HistoryDealGetDouble(deal,DEAL_PROFIT);
   const double commission=HistoryDealGetDouble(deal,DEAL_COMMISSION);
   const double swap=HistoryDealGetDouble(deal,DEAL_SWAP);
   const double fee=HistoryDealGetDouble(deal,DEAL_FEE);
   const datetime deal_time=(datetime)HistoryDealGetInteger(deal,DEAL_TIME);
   const ENUM_DEAL_REASON deal_reason=
      (ENUM_DEAL_REASON)HistoryDealGetInteger(deal,DEAL_REASON);
   if(deal_symbol!=_Symbol ||
      (entry_kind==DEAL_ENTRY_IN && deal_magic!=InpMagic))
      return true;
   if(entry_kind==DEAL_ENTRY_OUT || entry_kind==DEAL_ENTRY_OUT_BY)
   {
      bool opening_found=false;
      bool owned=false;
      if(!ResolvePositionOwnership(position_id,opening_found,owned))
         return LifecycleReject("ownership_history",deal);
      if(!opening_found)
         return LifecycleReject("ownership_missing",deal);
      if(!owned)
         return true;
   }
   if(position_id==0 || deal_time<=0 || volume<=0.0 || price<=0.0 ||
      !MathIsValidNumber(volume) ||
       !MathIsValidNumber(price) || !MathIsValidNumber(profit) ||
       !MathIsValidNumber(commission) || !MathIsValidNumber(swap) ||
       !MathIsValidNumber(fee))
      return LifecycleReject("snapshot_fields",deal);

   bool is_open=entry_kind==DEAL_ENTRY_IN;
   bool is_close=entry_kind==DEAL_ENTRY_OUT || entry_kind==DEAL_ENTRY_OUT_BY;
   if(!is_open && !is_close)
      return LifecycleReject("entry_kind",deal);
   long entry_direction=0;
   double risk_points=0.0;
   double initial_risk_account=0.0;
   if(is_open)
   {
      entry_direction=deal_type==DEAL_TYPE_BUY ? 1 : deal_type==DEAL_TYPE_SELL ? -1 : 0;
      const double stop=g_expected_stop>0.0 ? g_expected_stop : g_telemetry_entry_stop;
      if(entry_direction==0 || stop<=0.0 ||
         (entry_direction>0 && stop>=price) || (entry_direction<0 && stop<=price))
         return LifecycleReject("opening_geometry",deal);
      double loss=0.0;
      const ENUM_ORDER_TYPE order_type=entry_direction>0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
      if(!OrderCalcProfit(order_type,_Symbol,volume,price,stop,loss) ||
         !MathIsValidNumber(loss) || loss>=0.0)
         return LifecycleReject("opening_risk",deal);
      risk_points=MathAbs(price-stop)/_Point;
      initial_risk_account=MathAbs(loss);
      g_telemetry_position_id=position_id;
      g_telemetry_entry_stop=stop;
      g_telemetry_entry_direction=entry_direction;
   }
   else
   {
      if((g_telemetry_position_id!=position_id || g_telemetry_entry_direction==0) &&
         !RecoverTelemetryContextFromHistory(position_id))
         return LifecycleReject("closing_context",deal);
      entry_direction=g_telemetry_entry_direction;
   }
   double open_volume=0.0;
   double close_volume=0.0;
   if(!PositionDealVolumesThrough(position_id,deal,open_volume,close_volume))
      return LifecycleReject("cumulative_volume",deal);
   const bool final_close=is_close && close_volume+1e-8>=open_volume;
   const double net=profit+commission+swap+fee;
   const uint bytes_written=FileWrite(g_lifecycle_handle,
             TimeToString(deal_time,TIME_DATE|TIME_SECONDS),
             is_open ? "OPEN" : (final_close ? "CLOSE" : "CLOSE_PARTIAL"),
             entry_direction>0 ? "BUY" : "SELL",DoubleToString(volume,8),
             DoubleToString(price,_Digits),_Symbol,StringFormat("%I64u",position_id),
             DoubleToString(risk_points,8),DoubleToString(initial_risk_account,8),
             StringFormat("%I64u",deal),EnumToString(deal_reason),DoubleToString(profit,8),
             DoubleToString(commission,8),DoubleToString(swap,8),
             DoubleToString(fee,8),DoubleToString(net,8),final_close ? "1" : "0");
   if(bytes_written==0)
      return LifecycleReject("file_write",deal);
   FileFlush(g_lifecycle_handle);
   if(!MarkDealLogged(deal))
      return LifecycleReject("deal_index",deal);
   g_lifecycle_rows++;
   if(is_open)
   {
      g_lifecycle_open_rows++;
      bool added=false;
      if(!MarkUniquePosition(g_open_position_ids,position_id,added))
         return false;
      if(added)
         g_lifecycle_positions_opened++;
   }
   if(is_close && deal_reason==DEAL_REASON_SO)
   {
      if(!RegisterForcedStopout(deal,position_id))
         return false;
   }
   if(final_close)
   {
      g_lifecycle_final_close_rows++;
      bool added=false;
      if(!MarkUniquePosition(g_closed_position_ids,position_id,added))
         return false;
      if(added)
         g_lifecycle_positions_final_closed++;
      g_telemetry_position_id=0;
      g_telemetry_entry_stop=0.0;
      g_telemetry_entry_direction=0;
   }
   return true;
}


datetime CurrentBarOpen(const ENUM_TIMEFRAMES timeframe)
{
   return (datetime)SeriesInfoInteger(_Symbol,timeframe,SERIES_LASTBAR_DATE);
}


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


bool ValidBar(const MqlRates &bar)
{
   if(!MathIsValidNumber(bar.high) || !MathIsValidNumber(bar.low) ||
      !MathIsValidNumber(bar.close))
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
   return line==band;
}


bool AdvanceSupertrend(const MqlRates &bar,int &prior_state)
{
   if(!ValidBar(bar))
      return false;
   prior_state=g_st_state;
   const double tr=TrueRange(bar,true,g_prior_close);
   const double next_atr=(9.0*g_st_atr+tr)/10.0;
   const double hl2=(bar.high+bar.low)/2.0;
   const double basic_upper=hl2+ST_FACTOR*next_atr;
   const double basic_lower=hl2-ST_FACTOR*next_atr;
   const double next_upper=(basic_upper<g_final_upper || g_prior_close>g_final_upper)
                           ? basic_upper : g_final_upper;
   const double next_lower=(basic_lower>g_final_lower || g_prior_close<g_final_lower)
                           ? basic_lower : g_final_lower;

   int next_state=0;
   if(SameBandIdentity(g_supertrend,g_final_upper))
      next_state=(bar.close>next_upper) ? STATE_UP : STATE_DOWN;
   else if(SameBandIdentity(g_supertrend,g_final_lower))
      next_state=(bar.close<next_lower) ? STATE_DOWN : STATE_UP;
   else
      return false;

   g_st_atr=next_atr;
   g_final_upper=next_upper;
   g_final_lower=next_lower;
   g_st_state=next_state;
   g_supertrend=(g_st_state==STATE_UP) ? g_final_lower : g_final_upper;
   g_prior_close=bar.close;
   g_last_h1_time=bar.time;
   return MathIsValidNumber(g_st_atr) && MathIsValidNumber(g_final_upper) &&
          MathIsValidNumber(g_final_lower) && MathIsValidNumber(g_supertrend);
}


bool RebuildFrozenSupertrend(const datetime latest_closed_time)
{
   MqlRates history[];
   ArraySetAsSeries(history,false);
   const int total_bars=Bars(_Symbol,PERIOD_H1);
   if(total_bars<=ST_ATR_PERIOD)
      return false;
   const int copied=CopyRates(_Symbol,PERIOD_H1,1,total_bars-1,history);
   if(copied<ST_ATR_PERIOD || history[0].time!=SOURCE_START_TIME)
   {
      PrintFormat("STBS_FATAL|prehistory_unavailable|copied=%d|first=%s",copied,
                  copied>0 ? TimeToString(history[0].time,TIME_DATE|TIME_SECONDS) : "NONE");
      return false;
   }

   double seed_sum=0.0;
   double prior_close=0.0;
   for(int index=0;index<copied;index++)
   {
      if(!ValidBar(history[index]))
      {
         PrintFormat("STBS_FATAL|invalid_history_bar|index=%d|time=%s",index,
                     TimeToString(history[index].time,TIME_DATE|TIME_SECONDS));
         return false;
      }
      const double tr=TrueRange(history[index],index>0,prior_close);
      if(index<ST_ATR_PERIOD)
         seed_sum+=tr;
      if(index==ST_ATR_PERIOD-1)
      {
         g_st_atr=seed_sum/10.0;
         const double hl2=(history[index].high+history[index].low)/2.0;
         g_final_upper=hl2+ST_FACTOR*g_st_atr;
         g_final_lower=hl2-ST_FACTOR*g_st_atr;
         g_st_state=STATE_DOWN;
         g_supertrend=g_final_upper;
         g_prior_close=history[index].close;
         g_last_h1_time=history[index].time;
      }
      else if(index>=ST_ATR_PERIOD)
      {
         int ignored=0;
         if(!AdvanceSupertrend(history[index],ignored))
            return false;
      }
      prior_close=history[index].close;
   }
   return g_last_h1_time==latest_closed_time && g_st_state!=0;
}


datetime LastSundayUtc(const int year,const int month,const int hour)
{
   MqlDateTime parts;
   ZeroMemory(parts);
   parts.year=year;
   parts.mon=month;
   parts.day=31;
   parts.hour=hour;
   datetime candidate=StructToTime(parts);
   MqlDateTime check;
   TimeToStruct(candidate,check);
   while(check.mon!=month)
   {
      candidate-=86400;
      TimeToStruct(candidate,check);
   }
   return candidate-check.day_of_week*86400;
}


datetime NthSundayUtc(const int year,const int month,const int occurrence,const int hour)
{
   MqlDateTime parts;
   ZeroMemory(parts);
   parts.year=year;
   parts.mon=month;
   parts.day=1;
   parts.hour=hour;
   const datetime first=StructToTime(parts);
   MqlDateTime check;
   TimeToStruct(first,check);
   const int day=1+((7-check.day_of_week)%7)+(occurrence-1)*7;
   parts.day=day;
   return StructToTime(parts);
}


bool IsEuropeDstUtc(const datetime utc_time)
{
   MqlDateTime parts;
   TimeToStruct(utc_time,parts);
   const datetime begin=LastSundayUtc(parts.year,3,1);
   const datetime finish=LastSundayUtc(parts.year,10,1);
   return utc_time>=begin && utc_time<finish;
}


bool IsUnitedStatesDstUtc(const datetime utc_time)
{
   MqlDateTime parts;
   TimeToStruct(utc_time,parts);
   const datetime begin=NthSundayUtc(parts.year,3,2,7);
   const datetime finish=NthSundayUtc(parts.year,11,1,6);
   return utc_time>=begin && utc_time<finish;
}


bool IsFivePercentDstUtc(const datetime utc_time)
{
   MqlDateTime parts;
   TimeToStruct(utc_time,parts);
   return parts.year<=2023 ? IsEuropeDstUtc(utc_time)
                           : IsUnitedStatesDstUtc(utc_time);
}


datetime ServerToUtc(const datetime server_time)
{
   const datetime winter_candidate=server_time-2*3600;
   const int offset=2+(IsFivePercentDstUtc(winter_candidate) ? 1 : 0);
   return server_time-offset*3600;
}


int UtcDateKey(const datetime utc_time)
{
   MqlDateTime parts;
   TimeToStruct(utc_time,parts);
   return parts.year*10000+parts.mon*100+parts.day;
}


bool EntryClockAllowed(const datetime server_time)
{
   if(server_time<DESIGN_START_TIME || server_time>=DESIGN_END_TIME)
      return false;
   MqlDateTime parts;
   TimeToStruct(ServerToUtc(server_time),parts);
   const int minute=parts.hour*60+parts.min;
   if(parts.day_of_week==0 || parts.day_of_week==6)
      return false;
   if(parts.day_of_week==5 && minute>=InpFridayEntryCutoffUtcMinutes)
      return false;
   return true;
}


bool FlattenRequired(const datetime server_time)
{
   if(server_time<DESIGN_START_TIME || server_time>=DESIGN_END_TIME)
      return true;
   MqlDateTime parts;
   TimeToStruct(ServerToUtc(server_time),parts);
   if(parts.day_of_week==0 || parts.day_of_week==6)
      return true;
   return parts.day_of_week==5 &&
          parts.hour*60+parts.min>=InpFridayFlattenUtcMinutes;
}


string PersistentKey(const string suffix)
{
   return StringFormat("STBST_%I64d_%s_%s",InpMagic,_Symbol,suffix);
}


bool PersistValue(const string suffix,const double value)
{
   ResetLastError();
   return GlobalVariableSet(PersistentKey(suffix),value)>0 && GetLastError()==0;
}


bool LoadValue(const string suffix,double &value)
{
   const string key=PersistentKey(suffix);
   if(!GlobalVariableCheck(key))
      return false;
   ResetLastError();
   value=GlobalVariableGet(key);
   return GetLastError()==0 && MathIsValidNumber(value);
}


void DeleteValue(const string suffix)
{
   const string key=PersistentKey(suffix);
   if(GlobalVariableCheck(key))
      GlobalVariableDel(key);
}


string SnapshotKey(const string scope,const int slot,const string field)
{
   return StringFormat("%s_%d_%s",scope,slot,field);
}


bool WriteSnapshotValue(const string scope,const int slot,const string field,const double value)
{
   return PersistValue(SnapshotKey(scope,slot,field),value);
}


bool ReadSnapshotValue(const string scope,const int slot,const string field,double &value)
{
   return LoadValue(SnapshotKey(scope,slot,field),value);
}


bool NewerUncommittedSnapshotExists(const string scope,const long committed_generation)
{
   const int committed_slot=(int)(committed_generation%2);
   const int other_slot=1-committed_slot;
   const string other_key=PersistentKey(SnapshotKey(scope,other_slot,"GEN"));
   if(!GlobalVariableCheck(other_key))
      return false;
   double other_value=0.0;
   if(!ReadSnapshotValue(scope,other_slot,"GEN",other_value))
      return true;
   const long other_generation=(long)other_value;
   if(other_generation<=0 || (double)other_generation!=other_value)
      return true;
   return other_generation>committed_generation;
}


ulong SnapshotHash(const string payload)
{
   ulong hash=1469598103934665603;
   for(int index=0;index<StringLen(payload);index++)
   {
      hash^=(ulong)StringGetCharacter(payload,index);
      hash*=1099511628211;
   }
   return hash;
}


double UlongLow(const ulong value)
{
   return (double)(uint)(value & 0xFFFFFFFF);
}


double UlongHigh(const ulong value)
{
   return (double)(uint)(value>>32);
}


ulong JoinUlong(const double high_value,const double low_value)
{
   const ulong high=(ulong)(uint)high_value;
   const ulong low=(ulong)(uint)low_value;
   return (high<<32)|low;
}


bool ValidUlongPart(const double value)
{
   return value>=0.0 && value<=4294967295.0 && (double)(uint)value==value;
}


string RiskSnapshotPayload(const long generation,const double peak,
                           const double day_equity,const int day_key)
{
   return StringFormat("%I64d|%s|%s|%d",generation,
                       DoubleToString(peak,16),DoubleToString(day_equity,16),day_key);
}


bool PersistRiskSnapshot()
{
   const long generation=g_risk_generation+1;
   const int slot=(int)(generation%2);
   const ulong hash=SnapshotHash(RiskSnapshotPayload(generation,g_peak_equity,
                                                      g_day_start_equity,g_day_key));
   if(!WriteSnapshotValue("RISK",slot,"GEN",(double)generation) ||
      !WriteSnapshotValue("RISK",slot,"PEAK",g_peak_equity) ||
      !WriteSnapshotValue("RISK",slot,"DAYEQ",g_day_start_equity) ||
      !WriteSnapshotValue("RISK",slot,"DAYKEY",(double)g_day_key) ||
      !WriteSnapshotValue("RISK",slot,"HASHHI",UlongHigh(hash)) ||
      !WriteSnapshotValue("RISK",slot,"HASHLO",UlongLow(hash)))
      return false;
   GlobalVariablesFlush();
   if(!PersistValue("RISKGEN",(double)generation))
      return false;
   GlobalVariablesFlush();
   g_risk_generation=generation;
   return true;
}


bool LoadRiskSnapshot(bool &exists)
{
   exists=false;
   double committed=0.0;
   if(!LoadValue("RISKGEN",committed))
   {
      const bool residue=GlobalVariableCheck(PersistentKey(SnapshotKey("RISK",0,"GEN"))) ||
                         GlobalVariableCheck(PersistentKey(SnapshotKey("RISK",1,"GEN")));
      return !residue;
   }
   const long generation=(long)committed;
   if(generation<=0 || (double)generation!=committed)
      return false;
   if(NewerUncommittedSnapshotExists("RISK",generation))
      return false;
   const int slot=(int)(generation%2);
   double stored_generation=0.0;
   double peak=0.0;
   double day_equity=0.0;
   double day_key_value=0.0;
   double hash_high=0.0;
   double hash_low=0.0;
   if(!ReadSnapshotValue("RISK",slot,"GEN",stored_generation) ||
      !ReadSnapshotValue("RISK",slot,"PEAK",peak) ||
      !ReadSnapshotValue("RISK",slot,"DAYEQ",day_equity) ||
      !ReadSnapshotValue("RISK",slot,"DAYKEY",day_key_value) ||
      !ReadSnapshotValue("RISK",slot,"HASHHI",hash_high) ||
      !ReadSnapshotValue("RISK",slot,"HASHLO",hash_low) ||
      stored_generation!=committed || peak<=0.0 || day_equity<=0.0 ||
      day_key_value<=0.0 || (double)(int)day_key_value!=day_key_value ||
      !ValidUlongPart(hash_high) || !ValidUlongPart(hash_low))
      return false;
   const ulong expected=SnapshotHash(RiskSnapshotPayload(generation,peak,day_equity,
                                                          (int)day_key_value));
   if(JoinUlong(hash_high,hash_low)!=expected)
      return false;
   g_risk_generation=generation;
   g_peak_equity=peak;
   g_day_start_equity=day_equity;
   g_day_key=(int)day_key_value;
   g_risk_anchors_ready=true;
   exists=true;
   return true;
}


bool AnyOwnedHistoryExists()
{
   if(!HistorySelect(0,TimeCurrent()))
      return true;
   for(int index=HistoryDealsTotal()-1;index>=0;index--)
   {
      const ulong deal=HistoryDealGetTicket(index);
      if(deal==0)
         return true;
      ResetLastError();
      const string symbol=HistoryDealGetString(deal,DEAL_SYMBOL);
      const long magic=(long)HistoryDealGetInteger(deal,DEAL_MAGIC);
      if(GetLastError()!=0)
         return true;
      if(symbol==_Symbol && magic==InpMagic)
         return true;
   }
   return false;
}


bool LoadOrInitializeRiskAnchors(const datetime server_time,const bool owned_exposure)
{
   bool snapshot_exists=false;
   if(!LoadRiskSnapshot(snapshot_exists))
      return false;
   if(snapshot_exists)
      return true;
   const double equity=AccountInfoDouble(ACCOUNT_EQUITY);
   if(equity<=0.0 || !MathIsValidNumber(equity))
      return false;
   if(owned_exposure || AnyOwnedHistoryExists())
      return false;
   g_peak_equity=equity;
   g_day_start_equity=equity;
   g_day_key=UtcDateKey(ServerToUtc(server_time));
   g_risk_anchors_ready=PersistRiskSnapshot();
   return g_risk_anchors_ready;
}


bool UpdateRiskAnchors(const datetime server_time)
{
   if(!g_risk_anchors_ready)
      return false;
   const double equity=AccountInfoDouble(ACCOUNT_EQUITY);
   if(equity<=0.0 || !MathIsValidNumber(equity))
      return false;
   bool changed=false;
   if(equity>g_peak_equity)
   {
      g_peak_equity=equity;
      changed=true;
   }
   const int today=UtcDateKey(ServerToUtc(server_time));
   if(g_day_key!=today)
   {
      g_day_key=today;
      g_day_start_equity=equity;
      changed=true;
   }
   if(!changed)
      return true;
   return PersistRiskSnapshot();
}


bool EntryRiskLocked()
{
   const double equity=AccountInfoDouble(ACCOUNT_EQUITY);
   if(!g_risk_anchors_ready || equity<=0.0 ||
      g_peak_equity<=0.0 || g_day_start_equity<=0.0)
      return true;
   const double account_dd=100.0*(g_peak_equity-equity)/g_peak_equity;
   const double day_dd=100.0*(g_day_start_equity-equity)/g_day_start_equity;
   return account_dd>=InpMaxAccountDrawdownPct || day_dd>=InpMaxDailyLossPct;
}


bool CountOwnedPositions(int &count,ulong &single_ticket)
{
   single_ticket=0;
   count=0;
   for(int index=PositionsTotal()-1;index>=0;index--)
   {
      const ulong ticket=PositionGetTicket(index);
      if(ticket==0 || !PositionSelectByTicket(ticket))
         return false;
      ResetLastError();
      const string symbol=PositionGetString(POSITION_SYMBOL);
      const long magic=(long)PositionGetInteger(POSITION_MAGIC);
      if(GetLastError()!=0)
         return false;
      if(symbol==_Symbol && magic==InpMagic)
      {
         count++;
         single_ticket=ticket;
      }
   }
   return true;
}


bool CountOwnedOrders(int &count,ulong &single_ticket)
{
   single_ticket=0;
   count=0;
   for(int index=OrdersTotal()-1;index>=0;index--)
   {
      const ulong ticket=OrderGetTicket(index);
      if(ticket==0 || !OrderSelect(ticket))
         return false;
      ResetLastError();
      const string symbol=OrderGetString(ORDER_SYMBOL);
      const long magic=(long)OrderGetInteger(ORDER_MAGIC);
      if(GetLastError()!=0)
         return false;
      if(symbol==_Symbol && magic==InpMagic)
      {
         count++;
         single_ticket=ticket;
      }
   }
   return true;
}


bool OwnedExposureExists(bool &exists)
{
   exists=false;
   ulong position_ticket=0;
   ulong order_ticket=0;
   int positions=0;
   int orders=0;
   if(!CountOwnedPositions(positions,position_ticket) ||
      !CountOwnedOrders(orders,order_ticket))
      return false;
   exists=positions>0 || orders>0;
   return true;
}


bool ForeignSymbolExposureExists(bool &exists)
{
   exists=false;
   for(int index=PositionsTotal()-1;index>=0;index--)
   {
      const ulong ticket=PositionGetTicket(index);
      if(ticket==0 || !PositionSelectByTicket(ticket))
         return false;
      ResetLastError();
      const string symbol=PositionGetString(POSITION_SYMBOL);
      const long magic=(long)PositionGetInteger(POSITION_MAGIC);
      if(GetLastError()!=0)
         return false;
      if(symbol==_Symbol && magic!=InpMagic)
      {
         exists=true;
         return true;
      }
   }
   for(int index=OrdersTotal()-1;index>=0;index--)
   {
      const ulong ticket=OrderGetTicket(index);
      if(ticket==0 || !OrderSelect(ticket))
         return false;
      ResetLastError();
      const string symbol=OrderGetString(ORDER_SYMBOL);
      const long magic=(long)OrderGetInteger(ORDER_MAGIC);
      if(GetLastError()!=0)
         return false;
      if(symbol==_Symbol && magic!=InpMagic)
      {
         exists=true;
         return true;
      }
   }
   return true;
}


string ExecutionSnapshotPayload(const long generation,const int exec_state,
                                const int exit_intent,const long direction,
                                const double volume,const double stop,const double target,
                                const int reverse_direction,const double reverse_atr,
                                const datetime reverse_time,const datetime entry_time,
                                const datetime entry_block_until,
                                const uint request_id,const ulong order_id,const ulong deal_id,
                                const datetime request_started,const ulong counted_identifier,
                                const bool had_position,const int transient_ticks)
{
   return StringFormat("%I64d|%d|%d|%I64d|%s|%s|%s|%d|%s|%I64d|%I64d|%I64d|%u|%I64u|%I64u|%I64d|%I64u|%d|%d",
                       generation,exec_state,exit_intent,direction,
                       DoubleToString(volume,16),DoubleToString(stop,16),
                       DoubleToString(target,16),reverse_direction,
                       DoubleToString(reverse_atr,16),(long)reverse_time,(long)entry_time,
                       (long)entry_block_until,
                       request_id,order_id,deal_id,(long)request_started,
                       counted_identifier,had_position ? 1 : 0,transient_ticks);
}


bool PersistExecutionIntent()
{
   const string payload=ExecutionSnapshotPayload(
      0,(int)g_exec_state,(int)g_exit_intent,g_expected_direction,
      g_expected_volume,g_expected_stop,g_expected_target,g_reverse_direction,
      g_reverse_atr,g_reverse_decision,g_entry_m15_open,g_entry_block_until,g_pending_request_id,
      g_pending_order_id,g_pending_deal_id,g_request_started,
      g_counted_position_identifier,g_had_owned_position,g_transient_flat_ticks);
   if(g_execution_payload_ready && payload==g_execution_payload_cache)
      return true;
   const long generation=g_execution_generation+1;
   const int slot=(int)(generation%2);
   const ulong hash=SnapshotHash(ExecutionSnapshotPayload(
      generation,(int)g_exec_state,(int)g_exit_intent,g_expected_direction,
      g_expected_volume,g_expected_stop,g_expected_target,g_reverse_direction,
      g_reverse_atr,g_reverse_decision,g_entry_m15_open,g_entry_block_until,g_pending_request_id,
      g_pending_order_id,g_pending_deal_id,g_request_started,
      g_counted_position_identifier,g_had_owned_position,g_transient_flat_ticks));
   if(!WriteSnapshotValue("EXEC",slot,"GEN",(double)generation) ||
      !WriteSnapshotValue("EXEC",slot,"STATE",(double)g_exec_state) ||
      !WriteSnapshotValue("EXEC",slot,"EXIT",(double)g_exit_intent) ||
      !WriteSnapshotValue("EXEC",slot,"DIR",(double)g_expected_direction) ||
      !WriteSnapshotValue("EXEC",slot,"VOL",g_expected_volume) ||
      !WriteSnapshotValue("EXEC",slot,"SL",g_expected_stop) ||
      !WriteSnapshotValue("EXEC",slot,"TP",g_expected_target) ||
      !WriteSnapshotValue("EXEC",slot,"RDIR",(double)g_reverse_direction) ||
      !WriteSnapshotValue("EXEC",slot,"RATR",g_reverse_atr) ||
      !WriteSnapshotValue("EXEC",slot,"RTIME",(double)g_reverse_decision) ||
      !WriteSnapshotValue("EXEC",slot,"ENTRY",(double)g_entry_m15_open) ||
      !WriteSnapshotValue("EXEC",slot,"BLOCK",(double)g_entry_block_until) ||
      !WriteSnapshotValue("EXEC",slot,"REQ",(double)g_pending_request_id) ||
      !WriteSnapshotValue("EXEC",slot,"ORDHI",UlongHigh(g_pending_order_id)) ||
      !WriteSnapshotValue("EXEC",slot,"ORDLO",UlongLow(g_pending_order_id)) ||
      !WriteSnapshotValue("EXEC",slot,"DEALHI",UlongHigh(g_pending_deal_id)) ||
      !WriteSnapshotValue("EXEC",slot,"DEALLO",UlongLow(g_pending_deal_id)) ||
      !WriteSnapshotValue("EXEC",slot,"REQTIME",(double)g_request_started) ||
      !WriteSnapshotValue("EXEC",slot,"CNTHI",UlongHigh(g_counted_position_identifier)) ||
      !WriteSnapshotValue("EXEC",slot,"CNTLO",UlongLow(g_counted_position_identifier)) ||
      !WriteSnapshotValue("EXEC",slot,"HADPOS",g_had_owned_position ? 1.0 : 0.0) ||
      !WriteSnapshotValue("EXEC",slot,"ZERO",(double)g_transient_flat_ticks) ||
      !WriteSnapshotValue("EXEC",slot,"HASHHI",UlongHigh(hash)) ||
      !WriteSnapshotValue("EXEC",slot,"HASHLO",UlongLow(hash)))
      return false;
   GlobalVariablesFlush();
   if(!PersistValue("EXECGEN",(double)generation))
      return false;
   GlobalVariablesFlush();
   g_execution_generation=generation;
   g_resumed_execution_state=true;
   g_execution_payload_cache=payload;
   g_execution_payload_ready=true;
   return true;
}


bool LoadExecutionIntent()
{
   double committed=0.0;
   if(!LoadValue("EXECGEN",committed))
   {
      const bool residue=GlobalVariableCheck(PersistentKey(SnapshotKey("EXEC",0,"GEN"))) ||
                         GlobalVariableCheck(PersistentKey(SnapshotKey("EXEC",1,"GEN")));
      return !residue;
   }
   const long generation=(long)committed;
   if(generation<=0 || (double)generation!=committed)
      return false;
   if(NewerUncommittedSnapshotExists("EXEC",generation))
      return false;
   const int slot=(int)(generation%2);
   double values[24];
   const string fields[24]={"GEN","STATE","EXIT","DIR","VOL","SL","TP","RDIR",
                            "RATR","RTIME","ENTRY","BLOCK","REQ","ORDHI","ORDLO",
                            "DEALHI","DEALLO","REQTIME","CNTHI","CNTLO","HADPOS",
                            "ZERO","HASHHI","HASHLO"};
   for(int index=0;index<24;index++)
      if(!ReadSnapshotValue("EXEC",slot,fields[index],values[index]))
         return false;
   const int exec_state=(int)values[1];
   const int exit_intent=(int)values[2];
   const long direction=(long)values[3];
   const int reverse_direction=(int)values[7];
   const uint request_id=(uint)values[12];
   const ulong order_id=JoinUlong(values[13],values[14]);
   const ulong deal_id=JoinUlong(values[15],values[16]);
   const ulong counted_identifier=JoinUlong(values[18],values[19]);
   const bool had_position=values[20]==1.0;
   const int transient_ticks=(int)values[21];
   if(values[0]!=committed || exec_state<EXEC_FLAT || exec_state>EXEC_MANAGE_ONLY ||
      exit_intent<EXIT_NONE || exit_intent>EXIT_RUNTIME_FAULT ||
      (direction!=-1 && direction!=0 && direction!=1) ||
      (reverse_direction!=-1 && reverse_direction!=0 && reverse_direction!=1) ||
      values[4]<0.0 || values[5]<0.0 || values[6]<0.0 || values[8]<0.0 ||
      values[9]<0.0 || values[10]<0.0 || values[11]<0.0 || values[17]<0.0 ||
      values[12]!=(double)request_id || values[20]!=(had_position ? 1.0 : 0.0) ||
      values[21]!=(double)transient_ticks || transient_ticks<0 ||
      !ValidUlongPart(values[13]) || !ValidUlongPart(values[14]) ||
      !ValidUlongPart(values[15]) || !ValidUlongPart(values[16]) ||
      !ValidUlongPart(values[18]) || !ValidUlongPart(values[19]) ||
      !ValidUlongPart(values[22]) || !ValidUlongPart(values[23]) ||
      (direction==0 && (values[4]!=0.0 || values[5]!=0.0 || values[6]!=0.0)) ||
      (direction!=0 && (values[4]<=0.0 || values[5]<=0.0 || values[6]<=0.0)) ||
      (reverse_direction==0 && (values[8]!=0.0 || values[9]!=0.0)) ||
      (reverse_direction!=0 && (values[8]<=0.0 || values[9]<=0.0)) ||
      (exec_state==EXEC_ENTRY_PENDING && (direction==0 || values[17]<=0.0)))
      return false;
   const ulong expected=SnapshotHash(ExecutionSnapshotPayload(
      generation,exec_state,exit_intent,direction,values[4],values[5],values[6],
      reverse_direction,values[8],(datetime)values[9],(datetime)values[10],
      (datetime)values[11],request_id,order_id,deal_id,(datetime)values[17],
      counted_identifier,had_position,transient_ticks));
   if(JoinUlong(values[22],values[23])!=expected)
      return false;
   g_execution_generation=generation;
   g_exec_state=(ExecutionState)exec_state;
   g_exit_intent=(ExitIntent)exit_intent;
   g_expected_direction=direction;
   g_expected_volume=values[4];
   g_expected_stop=values[5];
   g_expected_target=values[6];
   g_reverse_direction=reverse_direction;
   g_reverse_atr=values[8];
   g_reverse_decision=(datetime)values[9];
   g_entry_m15_open=(datetime)values[10];
   g_entry_block_until=(datetime)values[11];
   g_pending_request_id=request_id;
   g_pending_order_id=order_id;
   g_pending_deal_id=deal_id;
   g_request_started=(datetime)values[17];
   g_counted_position_identifier=counted_identifier;
   g_had_owned_position=had_position;
   g_transient_flat_ticks=transient_ticks;
   g_execution_payload_cache=ExecutionSnapshotPayload(
      0,(int)g_exec_state,(int)g_exit_intent,g_expected_direction,
      g_expected_volume,g_expected_stop,g_expected_target,g_reverse_direction,
      g_reverse_atr,g_reverse_decision,g_entry_m15_open,g_entry_block_until,g_pending_request_id,
      g_pending_order_id,g_pending_deal_id,g_request_started,
      g_counted_position_identifier,g_had_owned_position,g_transient_flat_ticks);
   g_execution_payload_ready=true;
   return true;
}


void ClearEntryExpectation()
{
   g_expected_direction=0;
   g_expected_volume=0.0;
   g_expected_stop=0.0;
   g_expected_target=0.0;
   g_pending_order_id=0;
   g_pending_deal_id=0;
   g_pending_request_id=0;
   g_request_started=0;
   g_transient_flat_ticks=0;
}


void ClearRequestTracking()
{
   g_pending_order_id=0;
   g_pending_deal_id=0;
   g_pending_request_id=0;
   g_request_started=0;
   g_transient_flat_ticks=0;
}


void ClearReverseIntent()
{
   g_reverse_direction=0;
   g_reverse_atr=0.0;
   g_reverse_decision=0;
}


bool SetExitIntent(const ExitIntent intent)
{
   if(g_exit_intent==EXIT_NONE || intent==EXIT_RUNTIME_FAULT ||
      intent==EXIT_PROTECTION_INVALID || intent==EXIT_FRIDAY_WEEKEND)
      g_exit_intent=intent;
   if(intent!=EXIT_OPPOSITE_FLIP)
   {
      const datetime current_m15=CurrentBarOpen(PERIOD_M15);
      const datetime block_until=current_m15>0 ?
                                 current_m15+PeriodSeconds(PERIOD_M15) :
                                 TimeCurrent()+PeriodSeconds(PERIOD_M15);
      if(block_until>g_entry_block_until)
         g_entry_block_until=block_until;
   }
   if(PersistExecutionIntent())
      return true;
   g_runtime_failed=true;
   g_exec_state=EXEC_MANAGE_ONLY;
   Print("STBS_FATAL|runtime|exit_intent_persistence_failed");
   return false;
}


ENUM_ORDER_TYPE_FILLING FillingMode()
{
   long flags=0;
   if(!SymbolInfoInteger(_Symbol,SYMBOL_FILLING_MODE,flags))
      return ORDER_FILLING_FOK;
   if((flags & SYMBOL_FILLING_FOK)==SYMBOL_FILLING_FOK)
      return ORDER_FILLING_FOK;
   if((flags & SYMBOL_FILLING_IOC)==SYMBOL_FILLING_IOC)
      return ORDER_FILLING_IOC;
   return ORDER_FILLING_RETURN;
}


bool RequestAcceptedForTracking(const uint retcode)
{
   return retcode==TRADE_RETCODE_DONE ||
          retcode==TRADE_RETCODE_DONE_PARTIAL ||
          retcode==TRADE_RETCODE_PLACED;
}


bool CheckApproved(const MqlTradeCheckResult &check)
{
   return check.retcode==0;
}


bool SubmitCancelOrder(const ulong ticket)
{
   if(InpAuditOnly)
   {
      FailRuntime("audit_cancel_gateway_forbidden");
      return false;
   }
   if(ticket==0 || !OrderSelect(ticket))
      return false;
   MqlTradeRequest request;
   MqlTradeResult result;
   ZeroMemory(request);
   ZeroMemory(result);
   request.action=TRADE_ACTION_REMOVE;
   request.order=ticket;
   request.magic=(ulong)InpMagic;
   request.symbol=_Symbol;
   if(!OrderSend(request,result) || !RequestAcceptedForTracking(result.retcode))
      return false;
   g_pending_request_id=result.request_id;
   g_pending_order_id=result.order;
   g_pending_deal_id=result.deal;
   g_request_started=TimeCurrent();
   if(!PersistExecutionIntent())
      FailRuntime("cancel_request_persistence_failed");
   return true;
}


bool SubmitClose(const ulong ticket,const string reason)
{
   if(InpAuditOnly)
   {
      FailRuntime("audit_close_gateway_forbidden");
      return false;
   }
   ulong pending_ticket=0;
   int pending_orders=0;
   if(!CountOwnedOrders(pending_orders,pending_ticket))
   {
      FailRuntime("owned_order_enumeration_failed_before_close");
      return false;
   }
   if(pending_orders>0)
   {
      g_exec_state=EXEC_EXIT_PENDING;
      return true;
   }
   if(ticket==0 || !PositionSelectByTicket(ticket))
      return false;
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick) || tick.bid<=0.0 || tick.ask<=0.0)
      return false;
   ResetLastError();
   const ENUM_POSITION_TYPE position_type=
      (ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE);
   const double position_volume=PositionGetDouble(POSITION_VOLUME);
   if(GetLastError()!=0 || position_volume<=0.0)
      return false;
   MqlTradeRequest request;
   MqlTradeCheckResult check;
   MqlTradeResult result;
   ZeroMemory(request);
   ZeroMemory(check);
   ZeroMemory(result);
   request.action=TRADE_ACTION_DEAL;
   request.position=ticket;
   request.magic=(ulong)InpMagic;
   request.symbol=_Symbol;
   request.volume=position_volume;
   request.type=position_type==POSITION_TYPE_BUY ? ORDER_TYPE_SELL : ORDER_TYPE_BUY;
   request.price=position_type==POSITION_TYPE_BUY ? tick.bid : tick.ask;
   request.deviation=(ulong)InpDeviationPoints;
   request.type_filling=FillingMode();
   request.comment=reason;
   if(!OrderCheck(request,check) || !CheckApproved(check))
      return false;
   if(!OrderSend(request,result) || !RequestAcceptedForTracking(result.retcode))
      return false;
   g_pending_order_id=result.order;
   g_pending_deal_id=result.deal;
   g_pending_request_id=result.request_id;
   g_request_started=TimeCurrent();
   g_transient_flat_ticks=0;
   g_exec_state=EXEC_EXIT_PENDING;
   if(!PersistExecutionIntent())
      FailRuntime("close_request_persistence_failed");
   return true;
}


int VolumeDigits(const double step)
{
   int digits=0;
   double scaled=step;
   while(digits<8 && MathAbs(scaled-MathRound(scaled))>1e-10)
   {
      scaled*=10.0;
      digits++;
   }
   return digits;
}


double RiskSizedVolume(const ENUM_ORDER_TYPE order_type,const double entry,const double stop)
{
   const double equity=AccountInfoDouble(ACCOUNT_EQUITY);
   const double risk_cash=equity*InpRiskPercent/100.0;
   double one_lot_profit=0.0;
   if(risk_cash<=0.0 ||
      !OrderCalcProfit(order_type,_Symbol,1.0,entry,stop,one_lot_profit) ||
      !MathIsValidNumber(one_lot_profit) || one_lot_profit>=0.0)
      return 0.0;
   const double step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);
   const double minimum=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN);
   const double maximum=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX);
   if(step<=0.0 || minimum<=0.0 || maximum<minimum)
      return 0.0;
   double volume=MathFloor((risk_cash/MathAbs(one_lot_profit))/step)*step;
   volume=MathMin(volume,maximum);
   volume=NormalizeDouble(volume,VolumeDigits(step));
   if(volume<minimum)
      return 0.0;
   return volume;
}


double NormalizePriceDown(const double price,const double tick_size)
{
   return NormalizeDouble(MathFloor(price/tick_size)*tick_size,_Digits);
}


double NormalizePriceUp(const double price,const double tick_size)
{
   return NormalizeDouble(MathCeil(price/tick_size)*tick_size,_Digits);
}


bool ClosedM15AtrAtDecision(const datetime decision_time,
                            const int decision_shift,
                            double &atr)
{
   atr=0.0;
   if(decision_shift<0)
      return false;
   const datetime prior_time=decision_time-PeriodSeconds(PERIOD_M15);
   const int prior_shift=iBarShift(_Symbol,PERIOD_M15,prior_time,true);
   if(prior_shift!=decision_shift+1)
      return false;
   double values[];
   ArraySetAsSeries(values,false);
   const int requested=prior_shift;
   if(g_m15_atr_handle==INVALID_HANDLE ||
      CopyBuffer(g_m15_atr_handle,0,1,requested,values)!=requested)
      return false;
   atr=values[0];
   return MathIsValidNumber(atr) && atr>0.0;
}


bool BuildEntryGeometry(const int direction,const double atr,EntryPlan &plan)
{
   ZeroMemory(plan);
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick) || tick.bid<=0.0 || tick.ask<=0.0 ||
      tick.ask<tick.bid)
      return false;
   const double tick_size=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);
   const double point=SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   if(tick_size<=0.0 || point<=0.0)
      return false;
   const ENUM_ORDER_TYPE order_type=direction>0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
   const double entry=direction>0 ? tick.ask : tick.bid;
   const double raw_stop=direction>0 ? entry-InpStopAtrMult*atr
                                     : entry+InpStopAtrMult*atr;
   const double stop=direction>0 ? NormalizePriceDown(raw_stop,tick_size)
                                 : NormalizePriceUp(raw_stop,tick_size);
   const double risk_distance=direction>0 ? entry-stop : stop-entry;
   if(risk_distance<=0.0 || !MathIsValidNumber(risk_distance))
      return false;
   const double raw_target=direction>0 ? entry+InpTargetRR*risk_distance
                                       : entry-InpTargetRR*risk_distance;
   const double target=direction>0 ? NormalizePriceUp(raw_target,tick_size)
                                   : NormalizePriceDown(raw_target,tick_size);
   const long stops_level=SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL);
   const long freeze_level=SymbolInfoInteger(_Symbol,SYMBOL_TRADE_FREEZE_LEVEL);
   const double minimum_distance=(double)MathMax(stops_level,freeze_level)*point;
   if((direction>0 &&
       (stop>=tick.bid || target<=tick.ask || tick.bid-stop<minimum_distance ||
        target-tick.ask<minimum_distance)) ||
      (direction<0 &&
       (stop<=tick.ask || target>=tick.bid || stop-tick.ask<minimum_distance ||
        tick.bid-target<minimum_distance)))
      return false;
   const double volume=RiskSizedVolume(order_type,entry,stop);
   if(volume<=0.0)
      return false;

   plan.order_type=order_type;
   plan.filling=FillingMode();
   plan.entry=entry;
   plan.stop=stop;
   plan.target=target;
   plan.volume=volume;
   return true;
}


MarginSafetyResult EvaluateMarginCandidate(EntryPlan &plan,const double volume)
{
   ResetLastError();
   const double equity=AccountInfoDouble(ACCOUNT_EQUITY);
   const double free_margin=AccountInfoDouble(ACCOUNT_MARGIN_FREE);
   const double current_margin=AccountInfoDouble(ACCOUNT_MARGIN);
   const double so_call=AccountInfoDouble(ACCOUNT_MARGIN_SO_CALL);
   const double so_stop=AccountInfoDouble(ACCOUNT_MARGIN_SO_SO);
   const ENUM_ACCOUNT_STOPOUT_MODE so_mode=
      (ENUM_ACCOUNT_STOPOUT_MODE)AccountInfoInteger(ACCOUNT_MARGIN_SO_MODE);
   if(GetLastError()!=0 || !MathIsValidNumber(equity) || equity<=0.0 ||
      !MathIsValidNumber(free_margin) || free_margin<0.0 ||
      !MathIsValidNumber(current_margin) || current_margin<0.0 ||
      !MathIsValidNumber(so_call) || so_call<0.0 ||
      !MathIsValidNumber(so_stop) || so_stop<0.0 ||
      (so_mode!=ACCOUNT_STOPOUT_MODE_PERCENT && so_mode!=ACCOUNT_STOPOUT_MODE_MONEY))
      return MARGIN_SAFETY_FATAL;

   double required_margin=0.0;
   if(!OrderCalcMargin(plan.order_type,_Symbol,volume,plan.entry,required_margin) ||
      !MathIsValidNumber(required_margin) || required_margin<=0.0)
      return MARGIN_SAFETY_FATAL;
   if(required_margin>equity*InpMaxNewPositionMarginPct/100.0 ||
      required_margin>free_margin)
      return MARGIN_SAFETY_UNSAFE;

   MqlTradeRequest request;
   MqlTradeCheckResult check;
   ZeroMemory(request);
   ZeroMemory(check);
   request.action=TRADE_ACTION_DEAL;
   request.magic=(ulong)InpMagic;
   request.symbol=_Symbol;
   request.volume=volume;
   request.type=plan.order_type;
   request.price=plan.entry;
   request.sl=plan.stop;
   request.tp=plan.target;
   request.deviation=(ulong)InpDeviationPoints;
   request.type_filling=plan.filling;
   request.comment=plan.order_type==ORDER_TYPE_BUY ? "STBS_FLIP_BUY" : "STBS_FLIP_SELL";
   if(!OrderCheck(request,check))
      return MARGIN_SAFETY_FATAL;
   if(!CheckApproved(check))
      return MARGIN_SAFETY_UNSAFE;
   if(!MathIsValidNumber(check.equity) || check.equity<=0.0 ||
      !MathIsValidNumber(check.margin) || check.margin<=0.0 ||
      !MathIsValidNumber(check.margin_free) || check.margin_free<0.0 ||
      !MathIsValidNumber(check.margin_level) || check.margin_level<=0.0)
      return MARGIN_SAFETY_FATAL;

   bool safe=false;
   double threshold=0.0;
   if(so_mode==ACCOUNT_STOPOUT_MODE_PERCENT)
   {
      threshold=MathMax(InpMinProjectedMarginLevelPct,
                        MathMax(so_call,so_stop)*InpPercentStopoutHeadroomFactor);
      safe=check.margin_level>=threshold;
   }
   else
   {
      const double protected_level=MathMax(so_call,so_stop);
      if(check.equity>protected_level)
      {
         const double remaining_headroom=check.equity-protected_level;
         const double reserve=MathMax(remaining_headroom*InpMoneyHeadroomReserveFactor,
                                      check.equity*InpMoneyFreeEquityFloorPct/100.0);
         threshold=protected_level+reserve;
         safe=check.margin_free>=threshold && check.equity-check.margin>=threshold;
      }
   }
   if(!InpAuditOnly && !safe)
      PrintFormat("STBS_MARGIN_UNSAFE|volume=%.8f|free=%.8f|level=%.8f|threshold=%.8f",
                  volume,check.margin_free,check.margin_level,threshold);
   if(!safe)
      return MARGIN_SAFETY_UNSAFE;
   plan.volume=volume;
   plan.required_margin=required_margin;
   plan.required_free_margin=threshold;
   plan.projected_margin_free=check.margin_free;
   plan.projected_margin_level=check.margin_level;
   return MARGIN_SAFETY_PASS;
}


bool SelectMarginSafeVolume(EntryPlan &plan,const bool count_reject)
{
   const double step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);
   const double minimum=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN);
   if(step<=0.0 || minimum<=0.0 || plan.volume<minimum)
   {
      FailRuntime("margin_volume_contract_invalid");
      return false;
   }
   const int digits=VolumeDigits(step);
   double candidate=NormalizeDouble(MathFloor(plan.volume/step)*step,digits);
   while(candidate+step*0.5>=minimum)
   {
      const MarginSafetyResult result=EvaluateMarginCandidate(plan,candidate);
      if(result==MARGIN_SAFETY_PASS)
         return true;
      if(result==MARGIN_SAFETY_FATAL)
      {
         FailRuntime("margin_candidate_evaluation_failed");
         return false;
      }
      candidate=NormalizeDouble(candidate-step,digits);
   }
   if(count_reject)
      g_margin_rejects++;
   if(!InpAuditOnly)
      Print("STBS_MARGIN_REJECT|min_volume_unsafe=true");
   return false;
}


MarginSafetyResult EvaluateActualMargin(const ulong position_identifier)
{
   ResetLastError();
   const double equity=AccountInfoDouble(ACCOUNT_EQUITY);
   const double margin=AccountInfoDouble(ACCOUNT_MARGIN);
   const double free_margin=AccountInfoDouble(ACCOUNT_MARGIN_FREE);
   const double margin_level=AccountInfoDouble(ACCOUNT_MARGIN_LEVEL);
   const double so_call=AccountInfoDouble(ACCOUNT_MARGIN_SO_CALL);
   const double so_stop=AccountInfoDouble(ACCOUNT_MARGIN_SO_SO);
   const ENUM_ACCOUNT_STOPOUT_MODE so_mode=
      (ENUM_ACCOUNT_STOPOUT_MODE)AccountInfoInteger(ACCOUNT_MARGIN_SO_MODE);
   if(GetLastError()!=0 || !MathIsValidNumber(equity) || equity<=0.0 ||
      !MathIsValidNumber(margin) || margin<=0.0 ||
      !MathIsValidNumber(free_margin) || free_margin<0.0 ||
      !MathIsValidNumber(margin_level) || margin_level<=0.0 ||
      !MathIsValidNumber(so_call) || so_call<0.0 ||
      !MathIsValidNumber(so_stop) || so_stop<0.0 ||
      (so_mode!=ACCOUNT_STOPOUT_MODE_PERCENT && so_mode!=ACCOUNT_STOPOUT_MODE_MONEY))
      return MARGIN_SAFETY_FATAL;
   bool safe=false;
   double threshold=0.0;
   if(so_mode==ACCOUNT_STOPOUT_MODE_PERCENT)
   {
      threshold=MathMax(InpMinProjectedMarginLevelPct,
                        MathMax(so_call,so_stop)*InpPercentStopoutHeadroomFactor);
      safe=margin_level>=threshold;
   }
   else
   {
      const double protected_level=MathMax(so_call,so_stop);
      if(equity>protected_level)
      {
         const double remaining_headroom=equity-protected_level;
         const double reserve=MathMax(remaining_headroom*InpMoneyHeadroomReserveFactor,
                                      equity*InpMoneyFreeEquityFloorPct/100.0);
         threshold=protected_level+reserve;
         safe=free_margin>=threshold && equity-margin>=threshold;
      }
   }
   if(!safe || position_identifier==0)
   {
      PrintFormat("STBS_MARGIN_ACTUAL_UNSAFE|position=%I64u|level=%.8f|threshold=%.8f",
                  position_identifier,margin_level,threshold);
   }
   else if(g_last_actual_margin_logged_position_id!=position_identifier)
   {
      g_last_actual_margin_logged_position_id=position_identifier;
      g_actual_margin_safe_positions++;
   }
   return safe ? MARGIN_SAFETY_PASS : MARGIN_SAFETY_UNSAFE;
}


bool BuildEntryPlan(const int direction,const double atr,EntryPlan &plan,
                    const bool count_margin_reject)
{
   if(!BuildEntryGeometry(direction,atr,plan))
      return false;
   return SelectMarginSafeVolume(plan,count_margin_reject);
}


bool SubmitEntry(const int direction,const double atr,const datetime decision_time)
{
   if(InpAuditOnly)
   {
      FailRuntime("audit_entry_gateway_forbidden");
      return false;
   }
   EntryPlan plan;
   if(!BuildEntryPlan(direction,atr,plan,true))
      return false;

   MqlTradeRequest request;
   MqlTradeCheckResult check;
   MqlTradeResult result;
   ZeroMemory(request);
   ZeroMemory(check);
   ZeroMemory(result);
   request.action=TRADE_ACTION_DEAL;
   request.magic=(ulong)InpMagic;
   request.symbol=_Symbol;
   request.volume=plan.volume;
   request.type=plan.order_type;
   request.price=plan.entry;
   request.sl=plan.stop;
   request.tp=plan.target;
   request.deviation=(ulong)InpDeviationPoints;
   request.type_filling=plan.filling;
   request.comment=direction>0 ? "STBS_FLIP_BUY" : "STBS_FLIP_SELL";
   g_expected_direction=direction;
   g_expected_volume=plan.volume;
   g_expected_stop=plan.stop;
   g_expected_target=plan.target;
   g_pending_request_id=0;
   g_pending_order_id=0;
   g_pending_deal_id=0;
   g_request_started=TimeCurrent();
   g_transient_flat_ticks=0;
   g_exec_state=EXEC_ENTRY_PENDING;
   if(!PersistExecutionIntent())
   {
      ClearEntryExpectation();
      g_exec_state=EXEC_MANAGE_ONLY;
      FailRuntime("pre_entry_persistence_failed");
      return false;
   }
   if(!OrderCheck(request,check) || !CheckApproved(check))
   {
      ClearEntryExpectation();
      g_exec_state=EXEC_FLAT;
      PersistExecutionIntent();
      return false;
   }
   if(!OrderSend(request,result) || !RequestAcceptedForTracking(result.retcode))
   {
      ClearEntryExpectation();
      g_exec_state=EXEC_FLAT;
      PersistExecutionIntent();
      return false;
   }
   g_pending_order_id=result.order;
   g_pending_deal_id=result.deal;
   g_pending_request_id=result.request_id;
   if(!PersistExecutionIntent())
      FailRuntime("entry_request_persistence_failed");
   ReconcileExecutionState(false);
   return true;
}


void ConsumeFlipEvent(const MqlRates &bar,const int prior_state,const datetime next_time)
{
   const bool raw_event=prior_state!=0 && prior_state!=g_st_state;
   if(!raw_event)
      return;
   g_raw_events++;
   const int decision_m15_shift=iBarShift(_Symbol,PERIOD_M15,next_time,true);
   const bool exact_next=next_time==bar.time+PeriodSeconds(PERIOD_H1) &&
                         decision_m15_shift>=0;
   if(!exact_next)
   {
      g_gap_events++;
      if(InpAuditOnly)
         PrintFormat("STBS_SIGNAL|source_epoch=%I64d|decision_epoch=%I64d|direction=%s|exact_next=false|consumed=true|audit=true",
                     (long)ServerToUtc(bar.time),(long)ServerToUtc(next_time),
                     g_st_state==STATE_UP ? "LONG" : "SHORT");
      return;
   }
   g_executable_events++;
   const int direction=g_st_state==STATE_UP ? 1 : -1;
   if(direction>0)
      g_long_events++;
   else
      g_short_events++;
   double atr=0.0;
   const bool atr_ready=ClosedM15AtrAtDecision(next_time,decision_m15_shift,atr);
   if(atr_ready)
      g_atr_ready_events++;
   EntryPlan probe;
   const bool geometry_ready=atr_ready && CurrentBarOpen(PERIOD_M15)==next_time &&
                             BuildEntryGeometry(direction,atr,probe);
   if(geometry_ready)
      g_geometry_ready_events++;
   const bool margin_ready=geometry_ready && SelectMarginSafeVolume(probe,false);
   if(margin_ready)
      g_margin_ready_events++;
   if(InpAuditOnly)
      PrintFormat("STBS_SIGNAL|source_epoch=%I64d|decision_epoch=%I64d|direction=%s|exact_next=true|atr_ready=%s|geometry_ready=%s|margin_ready=%s|volume=%.8f|projected_free=%.8f|required_free=%.8f|audit=true",
                  (long)ServerToUtc(bar.time),(long)ServerToUtc(next_time),
                  direction>0 ? "LONG" : "SHORT",atr_ready ? "true" : "false",
                  geometry_ready ? "true" : "false",margin_ready ? "true" : "false",
                  margin_ready ? probe.volume : 0.0,
                  margin_ready ? probe.projected_margin_free : 0.0,
                  margin_ready ? probe.required_free_margin : 0.0);
   if(InpAuditOnly)
      return;
   if(g_runtime_failed)
      return;
   bool foreign_exposure=false;
   if(!ForeignSymbolExposureExists(foreign_exposure))
   {
      g_entry_rejects++;
      FailRuntime("foreign_exposure_enumeration_failed");
      return;
   }
   if(!atr_ready || !margin_ready || CurrentBarOpen(PERIOD_M15)!=next_time ||
      next_time<g_entry_block_until || !EntryClockAllowed(next_time) || EntryRiskLocked() ||
      FlattenRequired(next_time) || foreign_exposure)
   {
      g_entry_rejects++;
      return;
   }
   ReconcileExecutionState();
   if(g_exec_state==EXEC_FLAT)
   {
      if(!SubmitEntry(direction,atr,next_time))
         g_entry_rejects++;
      return;
   }
   if(g_exec_state!=EXEC_OPEN)
   {
      g_entry_rejects++;
      return;
   }
   ulong owned=0;
   int owned_positions=0;
   if(!CountOwnedPositions(owned_positions,owned) ||
      owned_positions!=1 || !PositionSelectByTicket(owned))
   {
      g_entry_rejects++;
      SetExitIntent(EXIT_RUNTIME_FAULT);
      return;
   }
   const ENUM_POSITION_TYPE position_type=(ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE);
   const int current_direction=position_type==POSITION_TYPE_BUY ? 1 : -1;
   if(current_direction==direction)
   {
      g_entry_rejects++;
      return;
   }
   g_reverse_direction=direction;
   g_reverse_atr=atr;
   g_reverse_decision=next_time;
   SetExitIntent(EXIT_OPPOSITE_FLIP);
   if(!SubmitClose(owned,"STBS_OPPOSITE_FLIP"))
      g_entry_rejects++;
}


bool ProcessNewClosedH1Bars(const datetime current_open)
{
   MqlRates bars[];
   ArraySetAsSeries(bars,false);
   const int prior_shift=iBarShift(_Symbol,PERIOD_H1,g_last_h1_time,true);
   if(prior_shift<=1)
      return false;
   const int copied=CopyRates(_Symbol,PERIOD_H1,1,prior_shift-1,bars);
   if(copied<=0)
      return false;
   for(int index=0;index<copied;index++)
   {
      if(bars[index].time<=g_last_h1_time)
         return false;
      int prior_state=0;
      if(!AdvanceSupertrend(bars[index],prior_state))
         return false;
      const datetime next_time=(index+1<copied) ? bars[index+1].time : current_open;
      if(bars[index].time>=DESIGN_START_TIME && bars[index].time<DESIGN_END_TIME)
         ConsumeFlipEvent(bars[index],prior_state,next_time);
   }
   return true;
}


bool RecoverEntryClock(const ulong ticket)
{
   if(g_entry_m15_open>0)
   {
      if(g_entry_m15_open<=CurrentBarOpen(PERIOD_M15) &&
         iBarShift(_Symbol,PERIOD_M15,g_entry_m15_open,true)>=0)
         return true;
      return false;
   }
   if(ticket==0 || !PositionSelectByTicket(ticket))
      return false;
   ResetLastError();
   const datetime position_time=(datetime)PositionGetInteger(POSITION_TIME);
   if(GetLastError()!=0)
      return false;
   const long seconds=(long)position_time;
   const long period_seconds=(long)PeriodSeconds(PERIOD_M15);
   const datetime candidate=(datetime)(seconds-seconds%period_seconds);
   if(candidate<=0 || iBarShift(_Symbol,PERIOD_M15,candidate,true)<0)
      return false;
   g_entry_m15_open=candidate;
   return PersistExecutionIntent();
}


bool PositionMatchesExpectation(const ulong ticket)
{
   if(ticket==0 || !PositionSelectByTicket(ticket) ||
      g_expected_direction==0 || g_expected_volume<=0.0 ||
      g_expected_stop<=0.0 || g_expected_target<=0.0)
      return false;
   ResetLastError();
   const ENUM_POSITION_TYPE type=(ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE);
   const int actual_direction=type==POSITION_TYPE_BUY ? 1 : -1;
   const double volume=PositionGetDouble(POSITION_VOLUME);
   const double open_price=PositionGetDouble(POSITION_PRICE_OPEN);
   const double stop=PositionGetDouble(POSITION_SL);
   const double target=PositionGetDouble(POSITION_TP);
   if(GetLastError()!=0)
      return false;
   const double volume_step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);
   const double tick_size=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);
   if(actual_direction!=g_expected_direction || volume_step<=0.0 || tick_size<=0.0 ||
      MathAbs(volume-g_expected_volume)>volume_step*0.5+1e-12 ||
      MathAbs(stop-g_expected_stop)>tick_size*0.5+1e-12 ||
      MathAbs(target-g_expected_target)>tick_size*0.5+1e-12)
      return false;
   return (actual_direction>0 && stop<open_price && target>open_price) ||
          (actual_direction<0 && target<open_price && stop>open_price);
}


bool ReconcileExecutionState(const bool advance_visibility_timeout=false)
{
   ulong position_ticket=0;
   ulong order_ticket=0;
   int positions=0;
   int orders=0;
   if(!CountOwnedPositions(positions,position_ticket) ||
      !CountOwnedOrders(orders,order_ticket))
   {
      g_exec_state=EXEC_MANAGE_ONLY;
      FailRuntime("owned_exposure_enumeration_failed");
      return false;
   }
   if(positions>1 || orders>1)
   {
      g_exec_state=EXEC_MANAGE_ONLY;
      SetExitIntent(EXIT_RUNTIME_FAULT);
      return false;
   }
   if(positions==0)
   {
      if(g_had_owned_position)
      {
         g_closes_submitted++;
         g_had_owned_position=false;
      }
      if(orders>0)
      {
         if(g_expected_direction==0 && g_exit_intent==EXIT_NONE)
            SetExitIntent(EXIT_RUNTIME_FAULT);
         g_exec_state=g_exit_intent==EXIT_NONE ? EXEC_ENTRY_PENDING : EXEC_EXIT_PENDING;
         return PersistExecutionIntent();
      }
      if(g_exec_state==EXEC_ENTRY_PENDING && g_expected_direction!=0 &&
         g_request_started>0)
      {
         if(!advance_visibility_timeout ||
            TimeCurrent()-g_request_started<=REQUEST_VISIBILITY_TIMEOUT_SECONDS)
         {
            if(advance_visibility_timeout)
               g_transient_flat_ticks++;
            return PersistExecutionIntent();
         }
         g_exec_state=EXEC_MANAGE_ONLY;
         SetExitIntent(EXIT_RUNTIME_FAULT);
         return false;
      }
      g_entry_m15_open=0;
      if(g_exit_intent!=EXIT_NONE)
         g_exit_intent=EXIT_NONE;
      ClearEntryExpectation();
      if(g_runtime_failed)
      {
         g_exec_state=EXEC_MANAGE_ONLY;
         return PersistExecutionIntent();
      }
      g_exec_state=EXEC_FLAT;
      return PersistExecutionIntent();
   }

   g_had_owned_position=true;
   if(orders>0)
   {
      g_exec_state=g_exit_intent==EXIT_NONE ? EXEC_MANAGE_ONLY : EXEC_EXIT_PENDING;
      if(g_exit_intent==EXIT_NONE)
         SetExitIntent(EXIT_PROTECTION_INVALID);
      PersistExecutionIntent();
      return false;
   }
   if(g_exit_intent!=EXIT_NONE)
   {
      g_exec_state=EXEC_EXIT_PENDING;
      return PersistExecutionIntent();
   }
   if(!PositionMatchesExpectation(position_ticket))
   {
      g_exec_state=EXEC_MANAGE_ONLY;
      SetExitIntent(EXIT_PROTECTION_INVALID);
      return false;
   }
   if(!RecoverEntryClock(position_ticket))
   {
      g_exec_state=EXEC_MANAGE_ONLY;
      SetExitIntent(EXIT_ENTRY_CLOCK_UNKNOWN);
      return false;
   }
   ResetLastError();
   const ulong identifier=(ulong)PositionGetInteger(POSITION_IDENTIFIER);
   if(GetLastError()!=0 || identifier==0)
   {
      g_exec_state=EXEC_MANAGE_ONLY;
      SetExitIntent(EXIT_PROTECTION_INVALID);
      return false;
   }
   const MarginSafetyResult actual_margin=EvaluateActualMargin(identifier);
   if(actual_margin!=MARGIN_SAFETY_PASS)
   {
      if(g_exit_intent!=EXIT_RUNTIME_FAULT)
         g_margin_emergencies++;
      g_runtime_failed=true;
      g_exec_state=EXEC_MANAGE_ONLY;
      PrintFormat("STBS_FATAL|actual_margin_contract_failed|result=%d",(int)actual_margin);
      SetExitIntent(EXIT_RUNTIME_FAULT);
      return false;
   }
   if(g_counted_position_identifier!=identifier)
   {
      g_counted_position_identifier=identifier;
      g_entries_submitted++;
   }
   ClearRequestTracking();
   g_exec_state=EXEC_OPEN;
   return PersistExecutionIntent();
}


void TryPendingReverse(const datetime server_time)
{
   if(g_exec_state!=EXEC_FLAT || g_reverse_direction==0)
      return;
   bool foreign_exposure=false;
   if(!ForeignSymbolExposureExists(foreign_exposure))
   {
      FailRuntime("foreign_exposure_enumeration_failed_on_reverse");
      return;
   }
   if(g_runtime_failed || CurrentBarOpen(PERIOD_M15)!=g_reverse_decision ||
      g_reverse_decision<g_entry_block_until ||
      !EntryClockAllowed(server_time) || EntryRiskLocked() ||
      FlattenRequired(server_time) || foreign_exposure)
   {
      ClearReverseIntent();
      PersistExecutionIntent();
      g_entry_rejects++;
      return;
   }
   const int direction=g_reverse_direction;
   const double atr=g_reverse_atr;
   const datetime decision=g_reverse_decision;
   ClearReverseIntent();
   PersistExecutionIntent();
   if(!SubmitEntry(direction,atr,decision))
      g_entry_rejects++;
}


void ManageLifecycle(const datetime server_time)
{
   if(!ReconcileExecutionState(true) && !g_runtime_failed)
      FailRuntime("execution_reconciliation_failed");
   ulong ticket=0;
   int positions=0;
   ulong order_ticket=0;
   int orders=0;
   if(!CountOwnedPositions(positions,ticket) ||
      !CountOwnedOrders(orders,order_ticket))
   {
      FailRuntime("owned_exposure_enumeration_failed_in_management");
      return;
   }
   if(FlattenRequired(server_time) && (positions>0 || orders>0))
   {
      ClearReverseIntent();
      SetExitIntent(EXIT_FRIDAY_WEEKEND);
   }
   else if(g_runtime_failed && (positions>0 || orders>0))
      SetExitIntent(EXIT_RUNTIME_FAULT);
   if(orders>0 && (positions>0 || g_exit_intent!=EXIT_NONE))
      SubmitCancelOrder(order_ticket);
   if(positions>0)
   {
      if(!FlattenRequired(server_time) && !g_runtime_failed)
      {
         const int entry_shift=g_entry_m15_open>0 ?
                               iBarShift(_Symbol,PERIOD_M15,g_entry_m15_open,true) : -1;
         if(entry_shift<0)
            SetExitIntent(EXIT_ENTRY_CLOCK_UNKNOWN);
         else if(entry_shift>=InpMaxHoldBars)
            SetExitIntent(EXIT_TIME);
      }
      if(g_exit_intent!=EXIT_NONE)
         SubmitClose(ticket,StringFormat("STBS_EXIT_%d",(int)g_exit_intent));
   }
   if(!ReconcileExecutionState() && !g_runtime_failed)
      FailRuntime("post_management_reconciliation_failed");
   TryPendingReverse(server_time);
}


void FailRuntime(const string reason)
{
   if(g_runtime_failed)
      return;
   g_runtime_failed=true;
   PrintFormat("STBS_FATAL|runtime|%s",reason);
   g_exec_state=EXEC_MANAGE_ONLY;
   ClearReverseIntent();
   SetExitIntent(EXIT_RUNTIME_FAULT);
}


bool LifecycleRequiresTick(const bool new_m15_bar)
{
   return new_m15_bar || g_exec_state!=EXEC_FLAT || g_exit_intent!=EXIT_NONE ||
          g_expected_direction!=0 || g_reverse_direction!=0 ||
          g_pending_request_id!=0 || g_pending_order_id!=0 || g_pending_deal_id!=0 ||
          g_request_started!=0 || g_runtime_failed;
}


int OnInit()
{
   if(!MQLInfoInteger(MQL_TESTER) || MQLInfoInteger(MQL_OPTIMIZATION) ||
      _Symbol!="XAUUSD" || _Period!=PERIOD_M15 ||
       InpHypothesisId!="HYP-STBS-XAUUSD-M15-021" ||
       InpVariantTag!="STBS_H1_FLIP_M15_BURST_TRADE_V8_STABLE_LIFECYCLE" ||
       InpAuditOnly || !InpEnableTelemetry || InpMagic!=5604121 ||
      InpRiskPercent!=0.25 || InpStopAtrMult!=1.00 || InpTargetRR!=1.50 ||
      InpMaxHoldBars!=8 || InpMaxDailyLossPct!=1.50 ||
      InpMaxAccountDrawdownPct!=8.00 ||
      InpFridayEntryCutoffUtcMinutes!=18*60 ||
      InpFridayFlattenUtcMinutes!=20*60 || InpDeviationPoints!=20 ||
      InpMaxNewPositionMarginPct!=5.00 ||
      InpMinProjectedMarginLevelPct!=2000.00 ||
      InpPercentStopoutHeadroomFactor!=1.25 ||
      InpMoneyHeadroomReserveFactor!=0.20 ||
      InpMoneyFreeEquityFloorPct!=1.00)
   {
      g_runtime_failed=true;
      Print("STBS_FATAL|frozen_input_or_chart_contract_failed");
      return INIT_PARAMETERS_INCORRECT;
   }
   bool owned_exposure=false;
   if(!OwnedExposureExists(owned_exposure))
   {
      g_runtime_failed=true;
      g_exec_state=EXEC_MANAGE_ONLY;
      Print("STBS_FATAL|owned_exposure_enumeration_failed_on_init");
      SetExitIntent(EXIT_RUNTIME_FAULT);
      return INIT_SUCCEEDED;
   }
   if(!LoadExecutionIntent())
   {
      g_runtime_failed=true;
      Print("STBS_FATAL|execution_intent_missing_or_corrupt");
      if(owned_exposure)
      {
         g_exec_state=EXEC_MANAGE_ONLY;
         SetExitIntent(EXIT_RUNTIME_FAULT);
         return INIT_SUCCEEDED;
      }
      return INIT_FAILED;
   }
   if(!LoadOrInitializeRiskAnchors(TimeCurrent(),owned_exposure))
   {
      g_runtime_failed=true;
      Print("STBS_FATAL|risk_anchor_missing_or_corrupt");
      if(owned_exposure)
      {
         g_exec_state=EXEC_MANAGE_ONLY;
         SetExitIntent(EXIT_RUNTIME_FAULT);
         return INIT_SUCCEEDED;
      }
      return INIT_FAILED;
   }
   if(!EmitDataQualitySeriesProof())
   {
      g_runtime_failed=true;
      Print("STBS_FATAL|data_quality_series_proof_failed");
      if(owned_exposure)
      {
         g_exec_state=EXEC_MANAGE_ONLY;
         SetExitIntent(EXIT_RUNTIME_FAULT);
         return INIT_SUCCEEDED;
      }
      return INIT_FAILED;
   }
   g_m15_atr_handle=iATR(_Symbol,PERIOD_M15,M15_ATR_PERIOD);
   if(g_m15_atr_handle==INVALID_HANDLE)
   {
      g_runtime_failed=true;
      Print("STBS_FATAL|m15_atr_handle_failed");
      if(owned_exposure)
      {
         g_exec_state=EXEC_MANAGE_ONLY;
         SetExitIntent(EXIT_RUNTIME_FAULT);
         return INIT_SUCCEEDED;
      }
      return INIT_FAILED;
   }
   g_current_h1_open=CurrentBarOpen(PERIOD_H1);
   g_current_m15_open=CurrentBarOpen(PERIOD_M15);
   const datetime latest_closed=iTime(_Symbol,PERIOD_H1,1);
   if(g_current_h1_open<=0 || g_current_m15_open<=0 || latest_closed<=0 ||
      latest_closed>=g_current_h1_open || !RebuildFrozenSupertrend(latest_closed))
   {
      g_runtime_failed=true;
      Print("STBS_FATAL|prehistory_or_state_rebuild_failed");
      if(owned_exposure)
      {
         g_exec_state=EXEC_MANAGE_ONLY;
         SetExitIntent(EXIT_RUNTIME_FAULT);
         return INIT_SUCCEEDED;
      }
      return INIT_FAILED;
   }
   if(InpEnableTelemetry &&
      (!OpenTelemetry() || !RecoverTelemetryPositionContext() ||
       !ReconcileLifecycleHistory()))
   {
      g_runtime_failed=true;
      Print("STBS_FATAL|lifecycle_telemetry_init_failed");
      if(owned_exposure)
      {
         g_exec_state=EXEC_MANAGE_ONLY;
         SetExitIntent(EXIT_RUNTIME_FAULT);
         return INIT_SUCCEEDED;
      }
      return INIT_FAILED;
   }
   ReconcileExecutionState();
   PrintFormat("STBS_INIT|hypothesis=%s|audit=%s|h1_last=%s|state=%s|exec_state=%d",
               InpHypothesisId,InpAuditOnly ? "true" : "false",
               TimeToString(g_last_h1_time,TIME_DATE|TIME_SECONDS),StateName(g_st_state),
               (int)g_exec_state);
   return INIT_SUCCEEDED;
}


bool ReconcileLifecycleHistory()
{
   if(!InpEnableTelemetry || g_lifecycle_handle==INVALID_HANDLE)
      return false;
   if(!HistorySelect(SOURCE_START_TIME,TimeCurrent()+PeriodSeconds(PERIOD_H1)))
      return false;
   const int total=HistoryDealsTotal();
   ulong deals[];
   long deal_times[];
   if(ArrayResize(deals,total)!=total)
      return false;
   if(ArrayResize(deal_times,total)!=total)
      return false;
   for(int index=0;index<total;index++)
   {
      deals[index]=HistoryDealGetTicket(index);
      if(deals[index]==0)
         return false;
      deal_times[index]=HistoryDealGetInteger(deals[index],DEAL_TIME_MSC);
      if(deal_times[index]<=0)
         return false;
   }
   for(int index=1;index<total;index++)
   {
      const ulong ticket=deals[index];
      const long time_msc=deal_times[index];
      int prior=index-1;
      while(prior>=0 &&
            (deal_times[prior]>time_msc ||
             (deal_times[prior]==time_msc && deals[prior]>ticket)))
      {
         deals[prior+1]=deals[prior];
         deal_times[prior+1]=deal_times[prior];
         prior--;
      }
      deals[prior+1]=ticket;
      deal_times[prior+1]=time_msc;
   }
   for(int pass=0;pass<2;pass++)
   {
      for(int index=0;index<total;index++)
      {
         if(!HistoryDealSelect(deals[index]))
            return false;
         const ENUM_DEAL_ENTRY entry=
            (ENUM_DEAL_ENTRY)HistoryDealGetInteger(deals[index],DEAL_ENTRY);
         const bool opening=entry==DEAL_ENTRY_IN;
         const bool closing=entry==DEAL_ENTRY_OUT || entry==DEAL_ENTRY_OUT_BY;
         if((pass==0 && !opening) || (pass==1 && !closing))
            continue;
         if(!LogLifecycleDeal(deals[index]))
            return false;
      }
   }
   return true;
}


bool PendingLifecycleDealQueued(const ulong deal)
{
   const int total=ArraySize(g_pending_lifecycle_deals);
   for(int index=0;index<total;index++)
      if(g_pending_lifecycle_deals[index]==deal)
         return true;
   return false;
}


bool ScheduleLifecycleReconcile(const ulong deal)
{
   if(deal==0 || DealAlreadyLogged(deal) || PendingLifecycleDealQueued(deal))
      return deal!=0;
   const int total=ArraySize(g_pending_lifecycle_deals);
   if(ArrayResize(g_pending_lifecycle_deals,total+1)!=total+1)
      return false;
   g_pending_lifecycle_deals[total]=deal;
   if(g_lifecycle_reconcile_started==0)
      g_lifecycle_reconcile_started=TimeCurrent();
   return true;
}


bool LifecycleDealResolved(const ulong deal,bool &resolved)
{
   resolved=false;
   if(deal==0)
      return false;
   if(DealAlreadyLogged(deal))
   {
      resolved=true;
      return true;
   }
   if(!HistoryDealSelect(deal))
      return true;
   const string symbol=HistoryDealGetString(deal,DEAL_SYMBOL);
   const ENUM_DEAL_ENTRY entry=
      (ENUM_DEAL_ENTRY)HistoryDealGetInteger(deal,DEAL_ENTRY);
   const ulong position_id=(ulong)HistoryDealGetInteger(deal,DEAL_POSITION_ID);
   const long magic=(long)HistoryDealGetInteger(deal,DEAL_MAGIC);
   if(symbol!=_Symbol)
   {
      resolved=true;
      return true;
   }
   if(entry==DEAL_ENTRY_IN)
   {
      resolved=magic!=InpMagic;
      return true;
   }
   if(entry==DEAL_ENTRY_OUT || entry==DEAL_ENTRY_OUT_BY)
   {
      bool opening_found=false;
      bool owned=false;
      if(!ResolvePositionOwnership(position_id,opening_found,owned))
         return false;
      resolved=opening_found && !owned;
      return true;
   }
   resolved=true;
   return true;
}


bool CompactResolvedLifecycleDeals()
{
   const int total=ArraySize(g_pending_lifecycle_deals);
   int write_index=0;
   for(int read_index=0;read_index<total;read_index++)
   {
      bool resolved=false;
      if(!LifecycleDealResolved(g_pending_lifecycle_deals[read_index],resolved) || !resolved)
      {
         g_pending_lifecycle_deals[write_index]=g_pending_lifecycle_deals[read_index];
         write_index++;
      }
   }
   if(ArrayResize(g_pending_lifecycle_deals,write_index)!=write_index)
      return false;
   if(write_index==0)
      g_lifecycle_reconcile_started=0;
   return true;
}


bool TryLifecycleReconcile()
{
   if(!InpEnableTelemetry || ArraySize(g_pending_lifecycle_deals)==0)
      return true;
   ReconcileLifecycleHistory();
   if(!CompactResolvedLifecycleDeals())
   {
      FailRuntime("lifecycle_queue_compaction_failed");
      return false;
   }
   if(ArraySize(g_pending_lifecycle_deals)==0)
      return true;
   if(g_lifecycle_reconcile_started>0 &&
      TimeCurrent()-g_lifecycle_reconcile_started>=REQUEST_VISIBILITY_TIMEOUT_SECONDS)
   {
      FailRuntime("lifecycle_history_reconcile_timeout");
      return false;
   }
   return true;
}


void OnDeinit(const int reason)
{
   if(InpEnableTelemetry && !ReconcileLifecycleHistory())
      g_runtime_failed=true;
   if(InpEnableTelemetry && !CompactResolvedLifecycleDeals())
      g_runtime_failed=true;
   if(InpEnableTelemetry && ArraySize(g_pending_lifecycle_deals)>0)
   {
      g_runtime_failed=true;
      PrintFormat("STBS_FATAL|lifecycle_unresolved_tickets|count=%d",
                  ArraySize(g_pending_lifecycle_deals));
   }
   if(!ReconcileExecutionState(true))
   {
      bool owned_exposure=false;
      if(!OwnedExposureExists(owned_exposure) || owned_exposure)
         g_runtime_failed=true;
   }
   if(InpEnableTelemetry &&
      g_lifecycle_positions_opened!=g_lifecycle_positions_final_closed)
   {
      g_runtime_failed=true;
      PrintFormat("STBS_FATAL|lifecycle_unbalanced|positions_opened=%I64d|positions_final_closed=%I64d|open_rows=%I64d|final_close_rows=%I64d",
                  g_lifecycle_positions_opened,g_lifecycle_positions_final_closed,
                  g_lifecycle_open_rows,g_lifecycle_final_close_rows);
   }
   if(!WriteRunMeta())
      g_runtime_failed=true;
   if(g_lifecycle_handle!=INVALID_HANDLE)
   {
      FileFlush(g_lifecycle_handle);
      FileClose(g_lifecycle_handle);
      g_lifecycle_handle=INVALID_HANDLE;
   }
   if(g_m15_atr_handle!=INVALID_HANDLE)
   {
      IndicatorRelease(g_m15_atr_handle);
      g_m15_atr_handle=INVALID_HANDLE;
   }
   PrintFormat("STBS_SUMMARY|hypothesis=%s|reason=%d|raw=%I64d|executable=%I64d|gaps=%I64d|long=%I64d|short=%I64d|atr_ready=%I64d|geometry_ready=%I64d|margin_ready=%I64d|margin_rejects=%I64d|margin_emergencies=%I64d|forced_stopouts=%I64d|entries=%I64d|entry_rejects=%I64d|closes=%I64d|lifecycle_open_rows=%I64d|lifecycle_final_close_rows=%I64d|lifecycle_positions_opened=%I64d|lifecycle_positions_final_closed=%I64d|exec_state=%d|exit_intent=%d|failed=%s",
               InpHypothesisId,reason,g_raw_events,g_executable_events,g_gap_events,
               g_long_events,g_short_events,g_atr_ready_events,g_geometry_ready_events,
               g_margin_ready_events,g_margin_rejects,g_margin_emergencies,
               g_forced_stopouts,g_entries_submitted,g_entry_rejects,g_closes_submitted,
               g_lifecycle_open_rows,g_lifecycle_final_close_rows,
               g_lifecycle_positions_opened,g_lifecycle_positions_final_closed,
               (int)g_exec_state,(int)g_exit_intent,g_runtime_failed ? "true" : "false");
}


void OnTick()
{
   const datetime server_time=TimeCurrent();
   if(!TryLifecycleReconcile())
   {
      ManageLifecycle(server_time);
      return;
   }
   if(!UpdateRiskAnchors(server_time))
      FailRuntime("risk_anchor_update_failed");
   const datetime m15_open=CurrentBarOpen(PERIOD_M15);
   const bool new_m15_bar=m15_open>0 && m15_open!=g_current_m15_open;
   if(new_m15_bar)
   {
      if(m15_open<g_current_m15_open)
      {
         FailRuntime("m15_time_regressed");
         ManageLifecycle(server_time);
         return;
      }
      g_current_m15_open=m15_open;
   }
   bool full_lifecycle=LifecycleRequiresTick(new_m15_bar);
   if(!full_lifecycle)
   {
      bool owned_exposure=false;
      if(!OwnedExposureExists(owned_exposure))
      {
         FailRuntime("idle_inventory_enumeration_failed");
         full_lifecycle=true;
      }
      else if(owned_exposure)
         full_lifecycle=true;
   }
   if(full_lifecycle)
      ManageLifecycle(server_time);
   if(g_runtime_failed)
      return;
   const datetime h1_open=CurrentBarOpen(PERIOD_H1);
   if(h1_open<=0 || h1_open==g_current_h1_open)
      return;
   if(h1_open<g_current_h1_open)
   {
      FailRuntime("h1_time_regressed");
      return;
   }
   if(!ProcessNewClosedH1Bars(h1_open))
   {
      FailRuntime("h1_backlog_processing_failed");
      return;
   }
   g_current_h1_open=h1_open;
}


void OnTradeTransaction(const MqlTradeTransaction &transaction,
                         const MqlTradeRequest &request,
                         const MqlTradeResult &result)
{
   if(transaction.type==TRADE_TRANSACTION_REQUEST && result.retcode!=TRADE_RETCODE_DONE)
      PrintFormat("STBS_REQUEST_RESULT|request_id=%u|retcode=%u|order=%I64u|deal=%I64u|comment=%s",
                  result.request_id,result.retcode,result.order,result.deal,result.comment);
   if(transaction.type==TRADE_TRANSACTION_DEAL_ADD && transaction.deal!=0 &&
      (transaction.symbol==_Symbol || transaction.symbol==""))
   {
      if(!ScheduleLifecycleReconcile(transaction.deal))
         FailRuntime("lifecycle_queue_allocation_failed");
   }
   ReconcileExecutionState();
   if(g_runtime_failed)
      ManageLifecycle(TimeCurrent());
}


double OnTester()
{
   return 0.0;
}
