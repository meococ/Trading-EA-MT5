#property strict
#property version   "1.00"
#property description "Audit-only London-open execution-fidelity successor"

input bool   InpAuditAutoMode=false;
input bool   InpEnableTelemetry=true;
input string InpHypothesisId="HYP-LOMX-EXEC-AUDIT-M1-003";
input string InpScenario="EURUSD_MIDDAY_CONT";
input long   InpMagic=5601303;
input double InpVolumeLots=0.01;
input double InpDeviationPips=2.00;
input int    InpBrokerGMTOffsetWinter=2;
input bool   InpBrokerFollowsEuropeDST=true;

const string EA_NAME="EA_LondonOpenExecutionAudit";
const string TELEMETRY_PROFILE="lifecycle-v3";
const string PREREG_SHA256="FA5745BAFFD8FBBE8238D82B143E5F6DFC4E9CD7DD1D9A5557F3B3E01310CABA";
const string BASE_PREREG_SHA256="039178106824BD8F2610B55F6AA54DED0CCAB3CE688A77B12142A9C897AC209B";
const string PARENT_PREREG_SHA256="87671236C8481111992FAA20476A118AB1A7ABFEFBC3FC11B51E7CBAA1BF8D91";
const string PARENT_TRADES_SHA256="32EE3D1A642D2F5F46A6309358CD35B1B7DC8D23FC215A179C97EE52D77EC4D6";
const string PARENT_METRICS_SHA256="6577299078F4ECB7009B2DD846C21118750D95DAABCEA2A66E5E702773C51261";

enum AuditSet
  {
   AUDIT_MIDDAY=0,
   AUDIT_LATE_FIX=1,
   AUDIT_FULL_SESSION=2
  };

AuditSet g_set=AUDIT_MIDDAY;
string g_set_name="MIDDAY";
int g_polarity=1;
int g_entry_minute=8*60+31;
int g_exit_minute=12*60;

int g_day_key=0;
bool g_signal_evaluated=false;
bool g_signal_ready=false;
bool g_entry_attempted=false;
bool g_exit_submitted=false;
int g_formation_sign=0;
int g_direction=0;
int g_source_0800_shift=-1;
int g_source_0830_shift=-1;
double g_open_0800=0.0;
double g_open_0830=0.0;
datetime g_source_0800_server=0;
datetime g_source_0830_server=0;
datetime g_signal_observed_server=0;
datetime g_entry_eligible_server=0;
ulong g_position_identifier=0;
int g_position_day_key=0;
int g_position_formation_sign=0;
int g_position_polarity=0;
int g_position_direction=0;

long g_ticks_seen=0;
long g_days_seen=0;
long g_weekend_days_skipped=0;
long g_signals_ready=0;
long g_zero_signals=0;
long g_missing_source_days=0;
long g_signal_window_misses=0;
long g_entries_attempted=0;
long g_entries_opened=0;
long g_entry_rejections=0;
long g_exposure_rejections=0;
long g_exit_requests=0;
long g_exit_rejections=0;
long g_entries_closed=0;
long g_overnight_violations=0;

int g_lifecycle_handle=INVALID_HANDLE;
int g_decision_handle=INVALID_HANDLE;
string g_run_id="";
string g_lifecycle_name="";
string g_run_meta_name="";
string g_decision_name="";

double PipSize()
  {
   return (_Digits==3 || _Digits==5) ? 10.0*_Point : _Point;
  }

int DaysInMonth(const int year,const int month)
  {
   if(month==2)
      return ((year%4==0 && year%100!=0) || year%400==0) ? 29 : 28;
   if(month==4 || month==6 || month==9 || month==11)
      return 30;
   return 31;
  }

datetime MakeDateTime(const int year,const int month,const int day,
                      const int hour,const int minute=0)
  {
   MqlDateTime parts;
   ZeroMemory(parts);
   parts.year=year;
   parts.mon=month;
   parts.day=day;
   parts.hour=hour;
   parts.min=minute;
   return StructToTime(parts);
  }

datetime LastSunday(const int year,const int month,const int hour)
  {
   datetime value=MakeDateTime(year,month,DaysInMonth(year,month),hour);
   MqlDateTime parts;
   TimeToStruct(value,parts);
   return value-parts.day_of_week*86400;
  }

bool IsEuropeDstUtc(const datetime utc_time)
  {
   MqlDateTime parts;
   TimeToStruct(utc_time,parts);
   datetime start=LastSunday(parts.year,3,1);
   datetime finish=LastSunday(parts.year,10,1);
   return utc_time>=start && utc_time<finish;
  }

datetime ServerToUtc(const datetime server_time)
  {
   datetime winter_candidate=server_time-InpBrokerGMTOffsetWinter*3600;
   int offset=InpBrokerGMTOffsetWinter;
   if(InpBrokerFollowsEuropeDST && IsEuropeDstUtc(winter_candidate))
      offset++;
   return server_time-offset*3600;
  }

datetime UtcToServer(const datetime utc_time)
  {
   int offset=InpBrokerGMTOffsetWinter;
   if(InpBrokerFollowsEuropeDST && IsEuropeDstUtc(utc_time))
      offset++;
   return utc_time+offset*3600;
  }

datetime UtcToLondon(const datetime utc_time)
  {
   return utc_time+(IsEuropeDstUtc(utc_time) ? 3600 : 0);
  }

datetime ServerToLondon(const datetime server_time)
  {
   return UtcToLondon(ServerToUtc(server_time));
  }

datetime LondonLocalToUtc(const int year,const int month,const int day,
                          const int hour,const int minute)
  {
   datetime local_clock=MakeDateTime(year,month,day,hour,minute);
   // All frozen audit boundaries are 08:00-16:30, outside DST ambiguity.
   return local_clock-(IsEuropeDstUtc(local_clock) ? 3600 : 0);
  }

datetime LondonTargetToServer(const MqlDateTime &london_date,
                              const int hour,const int minute)
  {
   return UtcToServer(LondonLocalToUtc(london_date.year,london_date.mon,
                                      london_date.day,hour,minute));
  }

int DateKey(const MqlDateTime &parts)
  {
   return parts.year*10000+parts.mon*100+parts.day;
  }

string DateKeyText(const int key)
  {
   return StringFormat("%04d.%02d.%02d",key/10000,(key/100)%100,key%100);
  }

string LondonTimeText(const datetime server_time)
  {
   return TimeToString(ServerToLondon(server_time),TIME_DATE|TIME_SECONDS);
  }

int MinuteOfDay(const MqlDateTime &parts)
  {
   return parts.hour*60+parts.min;
  }

ulong OwnedPositionTicket()
  {
   for(int i=PositionsTotal()-1;i>=0;i--)
     {
      ulong ticket=PositionGetTicket(i);
      if(ticket==0 || !PositionSelectByTicket(ticket))
         continue;
      if(PositionGetString(POSITION_SYMBOL)==_Symbol &&
         (long)PositionGetInteger(POSITION_MAGIC)==InpMagic)
         return ticket;
     }
   return 0;
  }

bool AnySymbolExposure()
  {
   for(int i=PositionsTotal()-1;i>=0;i--)
     {
      ulong ticket=PositionGetTicket(i);
      if(ticket==0 || !PositionSelectByTicket(ticket))
         return true;
      if(PositionGetString(POSITION_SYMBOL)==_Symbol)
         return true;
     }
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

void WriteDecision(const datetime event_time,const string event_code,
                   const string status,const double requested_price,
                   const double actual_price,const double volume,
                   const ulong order_id,const ulong deal_id,
                   const ulong position_id,const uint retcode,
                   const string reason,const int context_day_key=0,
                   const int context_formation_sign=0,
                   const int context_polarity=0,
                   const int context_direction=0)
  {
   if(!InpEnableTelemetry || g_decision_handle==INVALID_HANDLE)
      return;
   MqlTick tick;
   ZeroMemory(tick);
   SymbolInfoTick(_Symbol,tick);
   int row_day_key=context_day_key>0 ? context_day_key : g_day_key;
   int row_formation=context_day_key>0 ? context_formation_sign : g_formation_sign;
   int row_polarity=context_day_key>0 ? context_polarity : g_polarity;
   int row_direction=context_day_key>0 ? context_direction : g_direction;
   FileWrite(g_decision_handle,
             TimeToString(event_time,TIME_DATE|TIME_SECONDS),
             TimeToString(ServerToUtc(event_time),TIME_DATE|TIME_SECONDS),
             LondonTimeText(event_time),DateKeyText(row_day_key),
             event_code,status,InpScenario,g_set_name,InpHypothesisId,
             row_formation,row_polarity,row_direction,
             TimeToString(g_source_0800_server,TIME_DATE|TIME_SECONDS),
             TimeToString(g_source_0830_server,TIME_DATE|TIME_SECONDS),
             DoubleToString(g_open_0800,_Digits),
             DoubleToString(g_open_0830,_Digits),
             g_source_0800_shift,g_source_0830_shift,
             TimeToString(g_signal_observed_server,TIME_DATE|TIME_SECONDS),
             TimeToString(g_entry_eligible_server,TIME_DATE|TIME_SECONDS),
             DoubleToString(tick.bid,_Digits),DoubleToString(tick.ask,_Digits),
             DoubleToString((tick.ask-tick.bid)/_Point,2),
             DoubleToString(requested_price,_Digits),
             DoubleToString(actual_price,_Digits),DoubleToString(volume,8),
             StringFormat("%I64u",order_id),StringFormat("%I64u",deal_id),
             StringFormat("%I64u",position_id),(long)retcode,reason);
   FileFlush(g_decision_handle);
  }

bool RemainingPositionVolumeFromHistory(const ulong position_id,
                                        const datetime through_time,
                                        double &remaining)
  {
   remaining=0.0;
   if(!HistorySelect(0,through_time+1))
      return false;
   int total=HistoryDealsTotal();
   for(int i=0;i<total;i++)
     {
      ulong ticket=HistoryDealGetTicket(i);
      if(ticket==0 ||
         (ulong)HistoryDealGetInteger(ticket,DEAL_POSITION_ID)!=position_id)
         continue;
      ENUM_DEAL_ENTRY item_entry=(ENUM_DEAL_ENTRY)HistoryDealGetInteger(ticket,DEAL_ENTRY);
      double item_volume=HistoryDealGetDouble(ticket,DEAL_VOLUME);
      if(item_entry==DEAL_ENTRY_IN)
         remaining+=item_volume;
      else if(item_entry==DEAL_ENTRY_OUT || item_entry==DEAL_ENTRY_OUT_BY)
         remaining-=item_volume;
      else if(item_entry==DEAL_ENTRY_INOUT)
         return false;
     }
   if(remaining<0.0 && MathAbs(remaining)<1e-8)
      remaining=0.0;
   return remaining>=0.0;
  }

void LogLifecycleDeal(const ulong deal)
  {
   if(!HistoryDealSelect(deal))
      return;
   if(HistoryDealGetString(deal,DEAL_SYMBOL)!=_Symbol ||
      (long)HistoryDealGetInteger(deal,DEAL_MAGIC)!=InpMagic)
      return;
   ENUM_DEAL_ENTRY entry=(ENUM_DEAL_ENTRY)HistoryDealGetInteger(deal,DEAL_ENTRY);
   if(entry!=DEAL_ENTRY_IN && entry!=DEAL_ENTRY_INOUT &&
      entry!=DEAL_ENTRY_OUT && entry!=DEAL_ENTRY_OUT_BY)
      return;
   bool is_open=(entry==DEAL_ENTRY_IN);
   ulong position_id=(ulong)HistoryDealGetInteger(deal,DEAL_POSITION_ID);
   double profit=HistoryDealGetDouble(deal,DEAL_PROFIT);
   double commission=HistoryDealGetDouble(deal,DEAL_COMMISSION);
   double swap=HistoryDealGetDouble(deal,DEAL_SWAP);
   double fee=HistoryDealGetDouble(deal,DEAL_FEE);
   double net=profit+commission+swap+fee;
   datetime deal_time=(datetime)HistoryDealGetInteger(deal,DEAL_TIME);
   double deal_price=HistoryDealGetDouble(deal,DEAL_PRICE);
   double deal_volume=HistoryDealGetDouble(deal,DEAL_VOLUME);
   ulong order_id=(ulong)HistoryDealGetInteger(deal,DEAL_ORDER);
   ENUM_DEAL_TYPE deal_type=(ENUM_DEAL_TYPE)HistoryDealGetInteger(deal,DEAL_TYPE);
   int deal_direction=(deal_type==DEAL_TYPE_BUY ? 1 : -1);
   int entry_direction=is_open ? deal_direction : -deal_direction;
   MqlDateTime deal_london_parts;
   TimeToStruct(ServerToLondon(deal_time),deal_london_parts);
   int deal_day_key=DateKey(deal_london_parts);
   double remaining_volume=0.0;
   bool remaining_known=RemainingPositionVolumeFromHistory(position_id,deal_time,
                                                            remaining_volume);
   double volume_step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);
   bool final_close=(!is_open && remaining_known &&
                     remaining_volume<=MathMax(1e-8,volume_step/2.0));
   if(is_open)
     {
      g_entries_opened++;
      g_position_identifier=position_id;
      g_position_day_key=deal_day_key;
      g_position_formation_sign=g_formation_sign;
      g_position_polarity=g_polarity;
      g_position_direction=entry_direction;
     }
   int context_day_key=is_open ? deal_day_key : g_position_day_key;
   int context_formation=is_open ? g_formation_sign : g_position_formation_sign;
   int context_polarity=is_open ? g_polarity : g_position_polarity;
   int context_direction=is_open ? entry_direction : g_position_direction;
   if(context_day_key<=0)
     {
      context_day_key=deal_day_key;
      context_direction=entry_direction;
     }
   if(InpEnableTelemetry && g_lifecycle_handle!=INVALID_HANDLE)
     {
      FileWrite(g_lifecycle_handle,
                TimeToString(deal_time,TIME_DATE|TIME_SECONDS),
                is_open ? "OPEN" : (final_close ? "CLOSE" : "CLOSE_PARTIAL"),
                context_direction<0 ? "SELL" : "BUY",
                DoubleToString(deal_volume,8),DoubleToString(deal_price,_Digits),
                _Symbol,StringFormat("%I64u",position_id),"0","0",
                StringFormat("%I64u",deal),DoubleToString(profit,8),
                DoubleToString(commission,8),DoubleToString(swap,8),
                DoubleToString(fee,8),DoubleToString(net,8),
                final_close ? "1" : "0");
      FileFlush(g_lifecycle_handle);
     }
   WriteDecision(deal_time,is_open ? "ENTRY_DEAL" : "EXIT_DEAL","EXECUTED",
                 0.0,deal_price,deal_volume,order_id,deal,position_id,0,
                 is_open ? "broker_entry_fill" : "broker_exit_fill",
                 context_day_key,context_formation,context_polarity,
                 context_direction);
   if(final_close)
     {
      g_entries_closed++;
      g_position_identifier=0;
      g_position_day_key=0;
      g_position_formation_sign=0;
      g_position_polarity=0;
      g_position_direction=0;
     }
  }

bool WriteRunMeta()
  {
   if(!InpEnableTelemetry || g_run_meta_name=="")
      return true;
   int handle=FileOpen(g_run_meta_name,FILE_WRITE|FILE_TXT|FILE_ANSI);
   if(handle==INVALID_HANDLE)
      return false;
   string payload=StringFormat(
      "{\"schema_version\":\"alphafactory_run_meta.v1\"," 
      "\"run_id\":\"%s\",\"ea_name\":\"%s\",\"symbol\":\"%s\"," 
      "\"telemetry_profile\":\"%s\",\"hypothesis_id\":\"%s\"," 
      "\"variant_tag\":\"%s\",\"set_name\":\"%s\",\"magic\":%I64d," 
      "\"audit_only\":true,\"performance_metrics_authorized\":false," 
      "\"promotion_eligible\":false,\"closed_bar\":true," 
      "\"entry_latency_minutes\":%d,\"cost_status\":\"UNVERIFIED_DIAGNOSTIC_ONLY\"," 
      "\"prereg_sha256\":\"%s\",\"base_prereg_sha256\":\"%s\"," 
      "\"parent_prereg_sha256\":\"%s\"," 
      "\"parent_trades_sha256\":\"%s\",\"parent_metrics_sha256\":\"%s\"," 
      "\"diagnostic\":{\"ticks_seen\":%I64d,\"days_seen\":%I64d," 
      "\"weekend_days_skipped\":%I64d,\"signals_ready\":%I64d," 
      "\"zero_signals\":%I64d,\"missing_source_days\":%I64d," 
      "\"signal_window_misses\":%I64d,\"entries_attempted\":%I64d," 
      "\"entries_opened\":%I64d,\"entry_rejections\":%I64d," 
      "\"exposure_rejections\":%I64d,\"exit_requests\":%I64d," 
      "\"exit_rejections\":%I64d,\"entries_closed\":%I64d," 
      "\"overnight_violations\":%I64d}}",
      g_run_id,EA_NAME,_Symbol,TELEMETRY_PROFILE,InpHypothesisId,InpScenario,
      g_set_name,InpMagic,(g_set==AUDIT_LATE_FIX ? 0 : 1),PREREG_SHA256,
      BASE_PREREG_SHA256,PARENT_PREREG_SHA256,PARENT_TRADES_SHA256,
      PARENT_METRICS_SHA256,
      g_ticks_seen,g_days_seen,g_weekend_days_skipped,g_signals_ready,
      g_zero_signals,g_missing_source_days,g_signal_window_misses,
      g_entries_attempted,g_entries_opened,g_entry_rejections,
      g_exposure_rejections,g_exit_requests,g_exit_rejections,
      g_entries_closed,g_overnight_violations);
   FileWriteString(handle,payload);
   FileClose(handle);
   return true;
  }

bool OpenTelemetry()
  {
   if(!InpEnableTelemetry)
      return true;
   g_run_id=StringFormat("%s_%I64u",InpHypothesisId,GetTickCount64());
   g_lifecycle_name=StringFormat("%s_LifecycleTrades_%s.csv",_Symbol,g_run_id);
   g_run_meta_name=StringFormat("%s_RunMeta_%s.json",_Symbol,g_run_id);
   g_decision_name=StringFormat("%s_DecisionTelemetry_%s.csv",_Symbol,g_run_id);
   g_lifecycle_handle=FileOpen(g_lifecycle_name,FILE_WRITE|FILE_CSV|FILE_ANSI,',');
   if(g_lifecycle_handle==INVALID_HANDLE)
      return false;
   FileWrite(g_lifecycle_handle,"event_time","action","order_type","volume",
             "price","symbol","position_id","risk_pts","initial_risk_account",
             "deal","deal_profit","deal_commission","deal_swap","deal_fee",
             "deal_net","is_final_close");
   FileFlush(g_lifecycle_handle);
   g_decision_handle=FileOpen(g_decision_name,FILE_WRITE|FILE_CSV|FILE_ANSI,',');
   if(g_decision_handle==INVALID_HANDLE)
      return false;
   FileWrite(g_decision_handle,"server_time","utc_time","london_time",
             "london_date","event","status","scenario","set_name",
             "hypothesis_id","formation_sign","polarity","direction",
             "source_0800_server","source_0830_server","source_0800_open_bid",
             "source_0830_open_bid","source_0800_shift","source_0830_shift",
             "signal_observed_server","entry_eligible_server","bid","ask",
             "spread_points","request_price","actual_deal_price","volume",
             "order_id","deal_id","position_id","retcode","reason");
   FileFlush(g_decision_handle);
   return WriteRunMeta();
  }

bool ParseScenario()
  {
   if(InpScenario=="EURUSD_MIDDAY_CONT")
     {
      if(_Symbol!="EURUSD") return false;
      g_set=AUDIT_MIDDAY; g_set_name="MIDDAY"; g_polarity=1;
      g_entry_minute=8*60+31; g_exit_minute=12*60;
      return true;
     }
   if(InpScenario=="GBPUSD_MIDDAY_REV")
     {
      if(_Symbol!="GBPUSD") return false;
      g_set=AUDIT_MIDDAY; g_set_name="MIDDAY"; g_polarity=-1;
      g_entry_minute=8*60+31; g_exit_minute=12*60;
      return true;
     }
   if(InpScenario=="GBPUSD_LATE_FIX_REV")
     {
      if(_Symbol!="GBPUSD") return false;
      g_set=AUDIT_LATE_FIX; g_set_name="LATE_FIX"; g_polarity=-1;
      g_entry_minute=15*60+30; g_exit_minute=16*60;
      return true;
     }
   if(InpScenario=="GBPUSD_FULL_SESSION_REV")
     {
      if(_Symbol!="GBPUSD") return false;
      g_set=AUDIT_FULL_SESSION; g_set_name="FULL_SESSION"; g_polarity=-1;
      g_entry_minute=8*60+31; g_exit_minute=16*60+30;
      return true;
     }
   return false;
  }

bool ValidateInputs()
  {
   if(!InpAuditAutoMode || !InpEnableTelemetry || _Period!=PERIOD_M1)
      return false;
   if(InpHypothesisId!="HYP-LOMX-EXEC-AUDIT-M1-003" ||
      InpMagic!=5601303 || MathAbs(InpVolumeLots-0.01)>1e-12 ||
      InpDeviationPips<=0.0 || InpBrokerGMTOffsetWinter!=2 ||
      !InpBrokerFollowsEuropeDST)
      return false;
   if(!ParseScenario())
      return false;
   double minimum=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN);
   double maximum=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX);
   double step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);
   if(InpVolumeLots<minimum || InpVolumeLots>maximum || step<=0.0)
      return false;
   double steps=MathRound((InpVolumeLots-minimum)/step);
   if(MathAbs(minimum+steps*step-InpVolumeLots)>1e-8)
      return false;
   return true;
  }

void ResetDay(const int key)
  {
   g_day_key=key;
   g_signal_evaluated=false;
   g_signal_ready=false;
   g_entry_attempted=false;
   g_exit_submitted=false;
   g_formation_sign=0;
   g_direction=0;
   g_source_0800_shift=-1;
   g_source_0830_shift=-1;
   g_open_0800=0.0;
   g_open_0830=0.0;
   g_source_0800_server=0;
   g_source_0830_server=0;
   g_signal_observed_server=0;
   g_entry_eligible_server=0;
   g_position_identifier=0;
   g_position_day_key=0;
   g_position_formation_sign=0;
   g_position_polarity=0;
   g_position_direction=0;
   g_days_seen++;
  }

bool ReadExactClosedOpen(const MqlDateTime &london_date,
                         const int hour,const int minute,
                         double &value,datetime &server_time,int &shift)
  {
   server_time=LondonTargetToServer(london_date,hour,minute);
   shift=iBarShift(_Symbol,PERIOD_M1,server_time,true);
   if(shift<1)
      return false;
   MqlRates bars[];
   ArraySetAsSeries(bars,true);
   if(CopyRates(_Symbol,PERIOD_M1,shift,1,bars)!=1)
      return false;
   if(bars[0].time!=server_time || bars[0].open<=0.0)
      return false;
   value=bars[0].open;
   return true;
  }

void ObserveSignal(const datetime now,const MqlDateTime &london_parts)
  {
   g_signal_evaluated=true;
   g_signal_observed_server=now;
   if(!ReadExactClosedOpen(london_parts,8,0,g_open_0800,
                           g_source_0800_server,g_source_0800_shift) ||
      !ReadExactClosedOpen(london_parts,8,30,g_open_0830,
                           g_source_0830_server,g_source_0830_shift))
     {
      g_missing_source_days++;
      WriteDecision(now,"SIGNAL_REJECT","MISSING_EXACT_CLOSED_BAR",0.0,0.0,
                    0.0,0,0,0,0,"required_0800_or_0830_bar_absent");
      return;
     }
   double formation=MathLog(g_open_0830/g_open_0800);
   if(formation==0.0)
     {
      g_zero_signals++;
      WriteDecision(now,"SIGNAL_REJECT","ZERO_FORMATION",0.0,0.0,0.0,
                    0,0,0,0,"exact_zero_log_return");
      return;
     }
   g_formation_sign=formation>0.0 ? 1 : -1;
   g_direction=g_polarity*g_formation_sign;
   g_signal_ready=true;
   g_signals_ready++;
   MqlDateTime date_copy=london_parts;
   g_entry_eligible_server=LondonTargetToServer(date_copy,
                                                g_entry_minute/60,
                                                g_entry_minute%60);
   WriteDecision(now,"SIGNAL_READY","PASS",0.0,0.0,0.0,0,0,0,0,
                 "closed_0830_bar_observed");
  }

void TryEntry(const datetime now)
  {
   if(!g_signal_ready || g_entry_attempted)
      return;
   g_entry_attempted=true;
   g_entries_attempted++;
   if(AnySymbolExposure())
     {
      g_exposure_rejections++;
      g_entry_rejections++;
      WriteDecision(now,"ENTRY_REJECT","EXPOSURE",0.0,0.0,0.0,
                    0,0,0,0,"symbol_position_already_exists");
      return;
     }
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick) || tick.ask<=0.0 || tick.bid<=0.0)
     {
      g_entry_rejections++;
      WriteDecision(now,"ENTRY_REJECT","NO_EXECUTABLE_QUOTE",0.0,0.0,0.0,
                    0,0,0,0,"bid_or_ask_unavailable");
      return;
     }
   MqlTradeRequest request;
   MqlTradeCheckResult check;
   MqlTradeResult result;
   ZeroMemory(request);
   ZeroMemory(check);
   ZeroMemory(result);
   request.action=TRADE_ACTION_DEAL;
   request.magic=(ulong)InpMagic;
   request.symbol=_Symbol;
   request.volume=InpVolumeLots;
   request.type=g_direction>0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
   request.price=g_direction>0 ? tick.ask : tick.bid;
   request.deviation=(ulong)MathMax(1,MathRound(InpDeviationPips*PipSize()/_Point));
   request.type_filling=FillingMode();
   request.comment="LOMX audit entry";
   WriteDecision(now,"ENTRY_REQUEST","REQUESTED",request.price,0.0,
                 request.volume,0,0,0,0,"first_eligible_tick");
   if(!OrderCheck(request,check))
     {
      g_entry_rejections++;
      WriteDecision(now,"ENTRY_REJECT","ORDER_CHECK_FALSE",request.price,0.0,
                    request.volume,0,0,0,check.retcode,check.comment);
      return;
     }
   bool sent=OrderSend(request,result);
   bool accepted=sent && (result.retcode==TRADE_RETCODE_DONE ||
                          result.retcode==TRADE_RETCODE_DONE_PARTIAL ||
                          result.retcode==TRADE_RETCODE_PLACED);
   if(!accepted)
      g_entry_rejections++;
   WriteDecision(now,"ENTRY_SUBMIT",accepted ? "ACCEPTED" : "REJECTED",
                 request.price,result.price,request.volume,result.order,
                 result.deal,0,result.retcode,result.comment);
  }

bool SubmitExit(const ulong ticket,const datetime now,const string reason)
  {
   if(ticket==0 || !PositionSelectByTicket(ticket))
      return false;
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick) || tick.ask<=0.0 || tick.bid<=0.0)
      return false;
   ENUM_POSITION_TYPE position_type=(ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE);
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
   request.volume=PositionGetDouble(POSITION_VOLUME);
   request.type=position_type==POSITION_TYPE_BUY ? ORDER_TYPE_SELL : ORDER_TYPE_BUY;
   request.price=position_type==POSITION_TYPE_BUY ? tick.bid : tick.ask;
   request.deviation=(ulong)MathMax(1,MathRound(InpDeviationPips*PipSize()/_Point));
   request.type_filling=FillingMode();
   request.comment="LOMX audit exit";
   g_exit_requests++;
   WriteDecision(now,"EXIT_REQUEST","REQUESTED",request.price,0.0,
                 request.volume,0,0,
                 (ulong)PositionGetInteger(POSITION_IDENTIFIER),0,reason);
   if(!OrderCheck(request,check))
     {
      g_exit_rejections++;
      WriteDecision(now,"EXIT_REJECT","ORDER_CHECK_FALSE",request.price,0.0,
                    request.volume,0,0,
                    (ulong)PositionGetInteger(POSITION_IDENTIFIER),
                    check.retcode,check.comment);
      return false;
     }
   bool sent=OrderSend(request,result);
   bool accepted=sent && (result.retcode==TRADE_RETCODE_DONE ||
                          result.retcode==TRADE_RETCODE_DONE_PARTIAL ||
                          result.retcode==TRADE_RETCODE_PLACED);
   if(!accepted)
      g_exit_rejections++;
   WriteDecision(now,"EXIT_SUBMIT",accepted ? "ACCEPTED" : "REJECTED",
                 request.price,result.price,request.volume,result.order,
                 result.deal,(ulong)PositionGetInteger(POSITION_IDENTIFIER),
                 result.retcode,result.comment);
   return accepted;
  }

void ManageExit(const datetime now,const int current_date_key,
                const int minute_of_day)
  {
   ulong ticket=OwnedPositionTicket();
   if(ticket==0 || g_exit_submitted)
      return;
   bool overdue_day=(current_date_key>g_day_key);
   if(!overdue_day && minute_of_day<g_exit_minute)
      return;
   if(overdue_day)
      g_overnight_violations++;
   if(SubmitExit(ticket,now,overdue_day ? "OVERNIGHT_EMERGENCY" : "FROZEN_TIME_EXIT"))
      g_exit_submitted=true;
  }

int OnInit()
  {
   if(!ValidateInputs())
      return INIT_PARAMETERS_INCORRECT;
   if(!OpenTelemetry())
      return INIT_FAILED;
   PrintFormat("LOMX execution audit init hyp=%s scenario=%s symbol=%s closed_bar=true audit_only=true promotion=false",
               InpHypothesisId,InpScenario,_Symbol);
   return INIT_SUCCEEDED;
  }

void OnDeinit(const int reason)
  {
   WriteRunMeta();
   if(g_lifecycle_handle!=INVALID_HANDLE)
     {
      FileFlush(g_lifecycle_handle);
      FileClose(g_lifecycle_handle);
     }
   if(g_decision_handle!=INVALID_HANDLE)
     {
      FileFlush(g_decision_handle);
      FileClose(g_decision_handle);
     }
  }

void OnTradeTransaction(const MqlTradeTransaction &trans,
                        const MqlTradeRequest &request,
                        const MqlTradeResult &result)
  {
   if(trans.type==TRADE_TRANSACTION_DEAL_ADD && trans.deal>0)
      LogLifecycleDeal(trans.deal);
  }

void OnTick()
  {
   g_ticks_seen++;
   datetime now=TimeCurrent();
   datetime london=ServerToLondon(now);
   MqlDateTime london_parts;
   TimeToStruct(london,london_parts);
   int current_date_key=DateKey(london_parts);
   int minute_of_day=MinuteOfDay(london_parts);

   ManageExit(now,current_date_key,minute_of_day);
   if(current_date_key!=g_day_key)
     {
      if(OwnedPositionTicket()!=0)
         return;
      ResetDay(current_date_key);
      if(london_parts.day_of_week==0 || london_parts.day_of_week==6)
        {
         g_weekend_days_skipped++;
         g_signal_evaluated=true;
        }
     }
   if(g_signal_evaluated && !g_signal_ready)
      return;
   if(!g_signal_evaluated)
     {
      const int signal_minute=8*60+31;
      if(minute_of_day==signal_minute)
         ObserveSignal(now,london_parts);
      else if(minute_of_day>signal_minute)
        {
         g_signal_evaluated=true;
         g_signal_window_misses++;
         WriteDecision(now,"SIGNAL_REJECT","OBSERVATION_WINDOW_MISSED",
                       0.0,0.0,0.0,0,0,0,0,"no_tick_in_london_0831_minute");
        }
     }
   if(!g_signal_ready || g_entry_attempted)
      return;
   if(minute_of_day>=g_exit_minute)
     {
      g_entry_attempted=true;
      g_entry_rejections++;
      WriteDecision(now,"ENTRY_REJECT","ENTRY_WINDOW_MISSED",0.0,0.0,0.0,
                    0,0,0,0,"first_eligible_tick_after_frozen_exit");
      return;
     }
   if(g_set==AUDIT_LATE_FIX)
     {
      if(minute_of_day>=g_entry_minute)
         TryEntry(now);
     }
   else if(minute_of_day==8*60+31)
      TryEntry(now);
  }
