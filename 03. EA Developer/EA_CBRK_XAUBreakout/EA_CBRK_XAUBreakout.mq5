#property strict
#property version   "2.00"
#property description "CBRK XAUUSD M5 compression breakout clock-fixed EA"

enum EngineMode
  {
   ENGINE_SWEEP=0,
   ENGINE_BREAKOUT=1,
   ENGINE_BOTH=2
  };

enum EngineIdentity
  {
   IDENTITY_NONE=0,
   IDENTITY_SWEEP=1,
   IDENTITY_BREAKOUT=2
  };

input group "--- Build authority (fail closed) ---"
input bool   InpResearchAutoMode=false;
input bool   InpEnableTelemetry=true;
input string InpHypothesisId="UNREGISTERED_BUILD_ONLY";
input string InpVariantTag="BUILD_SCAFFOLD_BOTH";
input EngineMode InpEngineMode=ENGINE_BOTH;

input group "--- Symbol-scoped execution controls ---"
input long   InpMagic=5603100;
input double InpRiskPercent=0.25;
input double InpMaxDailyLossPct=3.5;
input double InpMaxAccountDrawdownPct=8.0;
input int    InpMaxTradesPerDay=3;
input double InpMaxSpreadToRisk=0.15;
input int    InpDeviationPoints=20;

input group "--- Frozen signal/session profile ---"
input int    InpATRPeriod=14;
input double InpSweepEpsilonMult=0.30;
input double InpSweepStopAtrMult=0.20;
input double InpSweepMinTp2R=1.50;
input int    InpVolumeLookback=20;
input double InpVolumeThreshold=1.50;
input int    InpAsianStartMinutesUtc=0;
input int    InpAsianEndMinutesUtc=360;
input int    InpTradeStartMinutesUtc=420;
input int    InpTradeEndMinutesUtc=960;
input int    InpDailyFlattenMinutesUtc=1200;
input int    InpFridayFlattenMinutesUtc=1200;
input double InpSweepScaleOutFraction=0.50;
input int    InpMaxHoldBars=96;

input group "--- Same-magic lot consistency ---"
input int    InpLotConsistencyMinFills=10;
input int    InpLotConsistencyLookbackFills=10;
input double InpLotConsistencyMinFactor=0.50;
input double InpLotConsistencyMaxFactor=1.50;

const string EA_NAME="EA_CBRK_XAUBreakout";
const string TELEMETRY_PROFILE="lifecycle-v3";
const int ATR_PERIOD=14;
const int CLOSED_BAR_COUNT=66;
const int ASIAN_START_MINUTE=0;
const int ASIAN_END_MINUTE=6*60;
const int TRADE_START_MINUTE=7*60;
const int TRADE_END_MINUTE=16*60;
const int ASIAN_BAR_COUNT=72;
const int ASIAN_LOOKBACK_BAR_COUNT=200;
const int FIVEPERCENT_WINTER_OFFSET_HOURS=2;
const double DAILY_LOSS_LOCK_PCT=3.5;
const double SWEEP_ATR_MULT=0.30;
const double SWEEP_VOLUME_Z=1.50;
const double SWEEP_STOP_ATR_MULT=0.20;
const double SWEEP_MIN_TP2_R=1.50;
const double BREAKOUT_CONTRACTION_RATIO=0.70;
const double BREAKOUT_BUFFER_ATR_MULT=0.20;
const double BREAKOUT_STOP_ATR_MULT=0.10;
const double BREAKOUT_TARGET_R=2.0;
const double MARGIN_HEADROOM_RESERVE_FACTOR=0.20;
const double MARGIN_FREE_EQUITY_FLOOR=0.01;
const double MARGIN_LEVEL_FLOOR_PCT=120.0;
const string SWEEP_PRIORITY="SWEEP_PRIORITY";

struct SignalDecision
  {
   bool fired;
   int direction;
   EngineIdentity engine;
   double stop;
   double tp1;
   double tp2;
   string reason;
  };

int g_atr_handle=INVALID_HANDLE;
datetime g_last_bar_clock=0;
int g_asian_day_key=0;
double g_asian_high=0.0;
double g_asian_low=0.0;

string g_daily_prefix="";
int g_daily_day_key=0;
double g_daily_start_equity=0.0;
bool g_daily_locked=false;
int g_daily_trades=0;
ulong g_daily_last_position=0;
double g_account_peak_equity=0.0;
bool g_account_dd_locked=false;

bool g_entry_request_pending=false;
EngineIdentity g_pending_engine=IDENTITY_NONE;
int g_pending_direction=0;
double g_pending_sl=0.0;
double g_pending_tp=0.0;
double g_pending_midpoint=0.0;
double g_pending_initial_risk=0.0;

ulong g_active_position_id=0;
EngineIdentity g_active_engine=IDENTITY_NONE;
int g_active_direction=0;
double g_active_entry=0.0;
double g_active_initial_sl=0.0;
double g_active_initial_tp=0.0;
double g_active_initial_risk=0.0;
double g_active_midpoint=0.0;
double g_active_initial_volume=0.0;
bool g_active_tp1_done=false;
bool g_active_be_done=false;
bool g_tp1_request_pending=false;

int g_lifecycle_handle=INVALID_HANDLE;
string g_run_id="";
string g_lifecycle_name="";
string g_run_meta_name="";

long g_ticks_seen=0;
long g_closed_bars_seen=0;
long g_asian_range_ready=0;
long g_asian_range_missing=0;
long g_sweep_evaluated=0;
long g_sweep_signals=0;
long g_breakout_evaluated=0;
long g_breakout_signals=0;
long g_both_collisions=0;
long g_sweep_selected=0;
long g_breakout_selected=0;
long g_no_signal=0;
long g_reject_daily_lock=0;
long g_reject_account_dd=0;
long g_reject_friday=0;
long g_reject_trade_limit=0;
long g_reject_exposure=0;
long g_reject_history=0;
long g_reject_spread=0;
long g_reject_geometry=0;
long g_reject_sizing=0;
long g_reject_margin_stopout=0;
long g_reject_order_check=0;
long g_reject_order_send=0;
long g_lot_consistency_clamps=0;
long g_margin_stopout_clamps=0;
long g_entries_opened=0;
long g_tp1_partial_closes=0;
long g_break_even_moves=0;
long g_final_closes=0;
long g_daily_flatten_closes=0;
long g_max_hold_closes=0;
long g_overnight_guard_closes=0;
long g_invalid_deal_events=0;
long g_duplicate_final_suppressed=0;
string g_last_reason="NONE";

//+------------------------------------------------------------------+
//| Clock and identity helpers                                       |
//+------------------------------------------------------------------+
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

datetime NthSunday(const int year,const int month,const int nth,const int hour)
  {
   datetime first=MakeDateTime(year,month,1,hour);
   MqlDateTime parts;
   TimeToStruct(first,parts);
   int first_sunday=1+((7-parts.day_of_week)%7);
   return MakeDateTime(year,month,first_sunday+(nth-1)*7,hour);
  }

bool IsEuropeDstUtc(const datetime utc_time)
  {
   MqlDateTime parts;
   TimeToStruct(utc_time,parts);
   datetime start=LastSunday(parts.year,3,1);
   datetime finish=LastSunday(parts.year,10,1);
   return utc_time>=start && utc_time<finish;
  }

bool IsUnitedStatesDstUtc(const datetime utc_time)
  {
   MqlDateTime parts;
   TimeToStruct(utc_time,parts);
   // US post-2024 broker era: 02:00 ET transitions are 07:00/06:00 UTC.
   datetime start=NthSunday(parts.year,3,2,7);
   datetime finish=NthSunday(parts.year,11,1,6);
   return utc_time>=start && utc_time<finish;
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
   datetime winter_candidate=server_time-FIVEPERCENT_WINTER_OFFSET_HOURS*3600;
   int offset=FIVEPERCENT_WINTER_OFFSET_HOURS;
   if(IsFivePercentDstUtc(winter_candidate))
      offset++;
   return server_time-offset*3600;
  }

datetime UtcToServer(const datetime utc_time)
  {
   int offset=FIVEPERCENT_WINTER_OFFSET_HOURS;
   if(IsFivePercentDstUtc(utc_time))
      offset++;
   return utc_time+offset*3600;
  }

int DateKey(const MqlDateTime &parts)
  {
   return parts.year*10000+parts.mon*100+parts.day;
  }

int UtcDateKey(const datetime utc_time)
  {
   MqlDateTime parts;
   TimeToStruct(utc_time,parts);
   return DateKey(parts);
  }

datetime UtcDayStart(const datetime utc_time)
  {
   MqlDateTime parts;
   TimeToStruct(utc_time,parts);
   parts.hour=0;
   parts.min=0;
   parts.sec=0;
   return StructToTime(parts);
  }

int MinuteOfDay(const MqlDateTime &parts)
  {
   return parts.hour*60+parts.min;
  }

uint HashText(const string value)
  {
   uint hash=2166136261;
   for(int i=0;i<StringLen(value);i++)
     {
      hash^=(uint)StringGetCharacter(value,i);
      hash*=16777619;
     }
   return hash;
  }

string JsonEscape(string value)
  {
   StringReplace(value,"\\","\\\\");
   StringReplace(value,"\"","\\\"");
   StringReplace(value,"\r"," ");
   StringReplace(value,"\n"," ");
   return value;
  }

string SafeToken(string value)
  {
   for(int i=0;i<StringLen(value);i++)
     {
      ushort c=StringGetCharacter(value,i);
      bool safe=(c>='A' && c<='Z') || (c>='a' && c<='z') ||
                (c>='0' && c<='9') || c=='_' || c=='-' || c=='.';
      if(!safe)
         StringSetCharacter(value,i,'_');
     }
   return value;
  }

string EngineName(const EngineIdentity engine)
  {
   if(engine==IDENTITY_SWEEP) return "SWEEP";
   if(engine==IDENTITY_BREAKOUT) return "BREAKOUT";
   return "UNKNOWN";
  }

string EngineModeName()
  {
   if(InpEngineMode==ENGINE_SWEEP) return "SWEEP";
   if(InpEngineMode==ENGINE_BREAKOUT) return "BREAKOUT";
   return "BOTH";
  }

void RecordReason(const string reason)
  {
   g_last_reason=reason;
   PrintFormat("LOMX funnel reason=%s hyp=%s symbol=%s magic=%I64d",
               reason,InpHypothesisId,_Symbol,InpMagic);
  }

//+------------------------------------------------------------------+
//| Persistent daily state: account + hypothesis + symbol            |
//+------------------------------------------------------------------+
string DailyStatePrefix()
  {
   long login=AccountInfoInteger(ACCOUNT_LOGIN);
   return StringFormat("LOMXD.%I64d.%u.%u",login,HashText(InpHypothesisId),
                       HashText(_Symbol));
  }

string DailyKey(const string suffix)
  {
   return g_daily_prefix+"."+suffix;
  }

string AccountRiskKey(const string suffix)
  {
   long login=AccountInfoInteger(ACCOUNT_LOGIN);
   if(MQLInfoInteger(MQL_TESTER))
      return StringFormat("LOMXA.%I64d.%u.%s",login,
                          HashText(InpHypothesisId),suffix);
   return StringFormat("LOMXA.%I64d.%s",login,suffix);
  }

void PersistDailyState()
  {
   GlobalVariableSet(DailyKey("DAY"),(double)g_daily_day_key);
   GlobalVariableSet(DailyKey("EQ"),g_daily_start_equity);
   GlobalVariableSet(DailyKey("LOCK"),g_daily_locked ? 1.0 : 0.0);
   GlobalVariableSet(DailyKey("TRADES"),(double)g_daily_trades);
   GlobalVariableSet(DailyKey("LASTPOS"),(double)g_daily_last_position);
   GlobalVariableSet(AccountRiskKey("PEAK"),g_account_peak_equity);
   GlobalVariableSet(AccountRiskKey("DDLOCK"),g_account_dd_locked ? 1.0 : 0.0);
  }

void LoadDailyState(const datetime utc_now)
  {
   int today=UtcDateKey(utc_now);
   double current_equity=AccountInfoDouble(ACCOUNT_EQUITY);
   g_account_peak_equity=GlobalVariableCheck(AccountRiskKey("PEAK"))
                         ? GlobalVariableGet(AccountRiskKey("PEAK"))
                         : current_equity;
   g_account_dd_locked=GlobalVariableCheck(AccountRiskKey("DDLOCK")) &&
                       GlobalVariableGet(AccountRiskKey("DDLOCK"))>0.5;
   int stored=GlobalVariableCheck(DailyKey("DAY"))
              ? (int)GlobalVariableGet(DailyKey("DAY")) : 0;
   if(stored!=today)
     {
      g_daily_day_key=today;
      g_daily_start_equity=current_equity;
      g_daily_locked=false;
      g_daily_trades=0;
      g_daily_last_position=0;
      PersistDailyState();
      return;
     }
   g_daily_day_key=stored;
   g_daily_start_equity=GlobalVariableGet(DailyKey("EQ"));
   g_daily_locked=GlobalVariableGet(DailyKey("LOCK"))>0.5;
   g_daily_trades=(int)GlobalVariableGet(DailyKey("TRADES"));
   g_daily_last_position=(ulong)GlobalVariableGet(DailyKey("LASTPOS"));
  }

//+------------------------------------------------------------------+
//| Owned exposure and synchronous mutation helpers                  |
//+------------------------------------------------------------------+
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

bool HasOwnedPendingOrder()
  {
   for(int i=OrdersTotal()-1;i>=0;i--)
     {
      ulong ticket=OrderGetTicket(i);
      if(ticket==0 || !OrderSelect(ticket))
         continue;
      if(OrderGetString(ORDER_SYMBOL)==_Symbol &&
         (long)OrderGetInteger(ORDER_MAGIC)==InpMagic)
         return true;
     }
   return false;
  }

bool OwnedExposureExists()
  {
   return OwnedPositionTicket()!=0 || HasOwnedPendingOrder() ||
          g_entry_request_pending;
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

bool AcceptedRetcode(const uint retcode)
  {
   return retcode==TRADE_RETCODE_DONE ||
          retcode==TRADE_RETCODE_DONE_PARTIAL ||
          retcode==TRADE_RETCODE_PLACED;
  }

bool SubmitCloseByTicket(const ulong ticket,const string reason,
                         const double requested_volume=0.0)
  {
   if(ticket==0 || !PositionSelectByTicket(ticket))
      return false;
   if(PositionGetString(POSITION_SYMBOL)!=_Symbol ||
      (long)PositionGetInteger(POSITION_MAGIC)!=InpMagic)
      return false;
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick) || tick.ask<=0.0 || tick.bid<=0.0)
      return false;
   ENUM_POSITION_TYPE position_type=(ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE);
   double position_volume=PositionGetDouble(POSITION_VOLUME);
   double volume=requested_volume>0.0 ? MathMin(requested_volume,position_volume)
                                      : position_volume;
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
   request.volume=volume;
   request.type=position_type==POSITION_TYPE_BUY ? ORDER_TYPE_SELL
                                                 : ORDER_TYPE_BUY;
   request.price=position_type==POSITION_TYPE_BUY ? tick.bid : tick.ask;
   request.deviation=(ulong)InpDeviationPoints;
   request.type_filling=FillingMode();
   request.comment=reason;
   if(!OrderCheck(request,check))
     {
      g_reject_order_check++;
      RecordReason("CLOSE_ORDER_CHECK");
      return false;
     }
   bool sent=OrderSend(request,result); // synchronous by design; no shared async mutation
   if(!sent || !AcceptedRetcode(result.retcode))
     {
      g_reject_order_send++;
      RecordReason("CLOSE_ORDER_SEND");
      return false;
     }
   return true;
  }

void CloseOwnedPositions(const string reason)
  {
   for(int i=PositionsTotal()-1;i>=0;i--)
     {
      ulong ticket=PositionGetTicket(i);
      if(ticket==0 || !PositionSelectByTicket(ticket))
         continue;
      if(PositionGetString(POSITION_SYMBOL)==_Symbol &&
         (long)PositionGetInteger(POSITION_MAGIC)==InpMagic)
         SubmitCloseByTicket(ticket,reason);
     }
  }

void DeleteOwnedPendingOrders(const string reason)
  {
   for(int i=OrdersTotal()-1;i>=0;i--)
     {
      ulong ticket=OrderGetTicket(i);
      if(ticket==0 || !OrderSelect(ticket))
         continue;
      if(OrderGetString(ORDER_SYMBOL)!=_Symbol ||
         (long)OrderGetInteger(ORDER_MAGIC)!=InpMagic)
         continue;
      MqlTradeRequest request;
      MqlTradeResult result;
      ZeroMemory(request);
      ZeroMemory(result);
      request.action=TRADE_ACTION_REMOVE;
      request.order=ticket;
      request.comment=reason;
      if(!OrderSend(request,result) || !AcceptedRetcode(result.retcode))
        {
         g_reject_order_send++;
         RecordReason("PENDING_DELETE_FAILED");
        }
     }
  }

void EnforceDailyAndFridayRisk(const datetime utc_now)
  {
   LoadDailyState(utc_now);
   double equity=AccountInfoDouble(ACCOUNT_EQUITY);
   if(equity>g_account_peak_equity)
     {
      g_account_peak_equity=equity;
      PersistDailyState();
     }
   if(!g_daily_locked && g_daily_start_equity>0.0 &&
      equity<=g_daily_start_equity*(1.0-InpMaxDailyLossPct/100.0))
     {
      g_daily_locked=true;
      PersistDailyState();
     RecordReason("DAILY_3P5_LOCK");
     }
   if(!g_account_dd_locked && g_account_peak_equity>0.0 &&
      equity<=g_account_peak_equity*(1.0-InpMaxAccountDrawdownPct/100.0))
     {
      g_account_dd_locked=true;
      PersistDailyState();
      RecordReason("ACCOUNT_PEAK_DD_LOCK");
     }
   if(g_daily_locked)
     {
      CloseOwnedPositions("LOMX_DAILY_LOCK");
      DeleteOwnedPendingOrders("LOMX_DAILY_LOCK");
     }
   if(g_account_dd_locked)
     {
      CloseOwnedPositions("LOMX_ACCOUNT_DD_LOCK");
      DeleteOwnedPendingOrders("LOMX_ACCOUNT_DD_LOCK");
     }

   MqlDateTime parts;
   TimeToStruct(utc_now,parts);
   int minute_of_day=MinuteOfDay(parts);
   bool friday_flatten=(parts.day_of_week==5 &&
                        minute_of_day>=InpFridayFlattenMinutesUtc);
   bool daily_flatten=(minute_of_day>=InpDailyFlattenMinutesUtc);
   if(friday_flatten || daily_flatten)
     {
      if(OwnedPositionTicket()!=0 || HasOwnedPendingOrder())
        {
         g_daily_flatten_closes++;
         if(friday_flatten)
           {
            g_reject_friday++;
            RecordReason("FRIDAY_2000_UTC_FLATTEN");
           }
         else
            RecordReason("DAILY_2000_UTC_FLATTEN");
        }
      CloseOwnedPositions(friday_flatten ? "LOMX_FRIDAY_FLATTEN"
                                         : "LOMX_DAILY_FLATTEN");
      DeleteOwnedPendingOrders(friday_flatten ? "LOMX_FRIDAY_FLATTEN"
                                               : "LOMX_DAILY_FLATTEN");
     }
  }

//+------------------------------------------------------------------+
//| Price, volume and broker geometry                                |
//+------------------------------------------------------------------+
double NormalizePriceToTick(const double price,const bool round_up)
  {
   double tick_size=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);
   if(tick_size<=0.0)
      tick_size=_Point;
   double steps=price/tick_size;
   double value=(round_up ? MathCeil(steps-1e-10)
                          : MathFloor(steps+1e-10))*tick_size;
   return NormalizeDouble(value,_Digits);
  }

double FloorVolume(const double requested)
  {
   double minimum=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN);
   double maximum=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX);
   double step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);
   if(minimum<=0.0 || maximum<=0.0 || step<=0.0 || requested<minimum)
      return 0.0;
   double capped=MathMin(requested,maximum);
   double floored=MathFloor((capped+1e-12)/step)*step;
   if(floored<minimum-1e-10)
      return 0.0;
   return NormalizeDouble(floored,8);
  }

bool LotConsistencyReference(double &reference,int &fills)
  {
   reference=0.0;
   fills=0;
   datetime now=TimeCurrent();
   if(!HistorySelect(now-180*86400,now+60))
      return false;
   double volumes[];
   ArrayResize(volumes,InpLotConsistencyLookbackFills);
   for(int i=HistoryDealsTotal()-1;i>=0 && fills<InpLotConsistencyLookbackFills;i--)
     {
      ulong ticket=HistoryDealGetTicket(i);
      if(ticket==0 || HistoryDealGetString(ticket,DEAL_SYMBOL)!=_Symbol ||
         (long)HistoryDealGetInteger(ticket,DEAL_MAGIC)!=InpMagic ||
         (ENUM_DEAL_ENTRY)HistoryDealGetInteger(ticket,DEAL_ENTRY)!=DEAL_ENTRY_IN)
         continue;
      double volume=HistoryDealGetDouble(ticket,DEAL_VOLUME);
      if(volume>0.0)
         volumes[fills++]=volume;
     }
   if(fills<InpLotConsistencyMinFills)
      return false;
   double sum=0.0;
   for(int i=0;i<fills;i++)
      sum+=volumes[i];
   reference=sum/fills; // exact AvgLot10 gate after ten same-magic entry fills
   return reference>0.0;
  }

double ApplyLotConsistencyClamp(const double proposed)
  {
   double reference=0.0;
   int fills=0;
   if(!LotConsistencyReference(reference,fills))
      return proposed;
   // Risk safety is one-sided: history can cap a new lot, never force it up.
   double minimum_consistent=reference*InpLotConsistencyMinFactor;
   if(proposed<minimum_consistent-1e-10)
     {
      RecordReason("LOT_BELOW_CONSISTENCY_FLOOR_REJECT");
      return 0.0; // never force volume upward to satisfy consistency
     }
   double capped=MathMin(proposed,reference*InpLotConsistencyMaxFactor);
   if(capped<proposed-1e-10)
      g_lot_consistency_clamps++;
   return capped;
  }

double FloorHalfSplittableVolume(const double requested)
  {
   double minimum=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN);
   double step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);
   if(minimum<=0.0 || step<=0.0)
      return 0.0;
   double volume=FloorVolume(requested);
   if(volume<=0.0)
      return 0.0;
   long units=(long)MathFloor((volume+1e-12)/step);
   if((units%2)!=0)
      units--;
   if(units<=0)
      return 0.0;
   return FloorVolume((double)units*step);
  }

bool MarginSafeVolume(const int direction,const double entry,
                      const double proposed,const bool require_half_split,
                      double &volume)
  {
   volume=0.0;
   if(proposed<=0.0 || entry<=0.0)
      return false;
   ENUM_ORDER_TYPE type=direction>0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
   double margin_one_lot=0.0;
   if(!OrderCalcMargin(type,_Symbol,1.0,entry,margin_one_lot) ||
      margin_one_lot<=0.0)
     {
      g_reject_margin_stopout++;
      RecordReason("MARGIN_CALC_FAILED");
      return false;
     }

   double equity=AccountInfoDouble(ACCOUNT_EQUITY);
   double used_margin=AccountInfoDouble(ACCOUNT_MARGIN);
   double margin_call_level=AccountInfoDouble(ACCOUNT_MARGIN_SO_CALL);
   double stopout_level=AccountInfoDouble(ACCOUNT_MARGIN_SO_SO);
   if(equity<=0.0 || used_margin<0.0 || margin_call_level<0.0 ||
      stopout_level<0.0)
     {
      g_reject_margin_stopout++;
      RecordReason("MARGIN_ACCOUNT_STATE_INVALID");
      return false;
     }

   ENUM_ACCOUNT_STOPOUT_MODE mode=
      (ENUM_ACCOUNT_STOPOUT_MODE)AccountInfoInteger(ACCOUNT_MARGIN_SO_MODE);
   double allowed_new_margin=0.0;
   if(mode==ACCOUNT_STOPOUT_MODE_MONEY)
     {
      // Absolute money thresholds do not scale with the tester deposit.
      // Keep free margin above the larger of margin-call and stop-out plus
      // a reserve taken from the remaining equity headroom.
      double protected_level=MathMax(margin_call_level,stopout_level);
      if(equity<=protected_level)
        {
         g_reject_margin_stopout++;
         RecordReason("MARGIN_DEPOSIT_BELOW_MONEY_THRESHOLD");
         return false;
        }
      double headroom=equity-protected_level;
      double reserve=MathMax(headroom*MARGIN_HEADROOM_RESERVE_FACTOR,
                             equity*MARGIN_FREE_EQUITY_FLOOR);
      double required_free=protected_level+reserve;
      allowed_new_margin=equity-used_margin-required_free;
     }
   else
     {
      // Percent-mode brokers compare equity / total margin. Maintain a
      // conservative floor above the declared broker stop-out percentage.
      double declared_level=MathMax(margin_call_level,stopout_level);
      double required_level=MathMax(MARGIN_LEVEL_FLOOR_PCT,
                                    declared_level*1.20);
      required_level=MathMax(required_level,declared_level+20.0);
      allowed_new_margin=equity*100.0/required_level-used_margin;
     }
   if(allowed_new_margin<=0.0)
     {
      g_reject_margin_stopout++;
      RecordReason("MARGIN_STOPOUT_NO_CAPACITY");
      return false;
     }

   double raw=MathMin(proposed,allowed_new_margin/margin_one_lot);
   volume=require_half_split ? FloorHalfSplittableVolume(raw)
                             : FloorVolume(raw);
   if(volume<=0.0)
     {
      g_reject_margin_stopout++;
      RecordReason("MARGIN_STOPOUT_VOLUME_ZERO");
      return false;
     }

   double exact_margin=0.0;
   if(!OrderCalcMargin(type,_Symbol,volume,entry,exact_margin) ||
      exact_margin<=0.0 || exact_margin>allowed_new_margin+0.01)
     {
      g_reject_margin_stopout++;
      RecordReason("MARGIN_STOPOUT_EXACT_CHECK");
      volume=0.0;
      return false;
     }
   if(volume<proposed-1e-10)
      g_margin_stopout_clamps++;
   return true;
  }

bool LossPerLot(const int direction,const double entry,const double stop,
                double &loss_per_lot)
  {
   loss_per_lot=0.0;
   double profit=0.0;
   ENUM_ORDER_TYPE type=direction>0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
   if(OrderCalcProfit(type,_Symbol,1.0,entry,stop,profit) && profit<0.0)
     {
      loss_per_lot=-profit;
      return true;
     }
   double tick_size=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);
   double tick_value=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_VALUE_LOSS);
   if(tick_value<=0.0)
      tick_value=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_VALUE);
   if(tick_size<=0.0 || tick_value<=0.0)
      return false;
   loss_per_lot=MathAbs(entry-stop)/tick_size*tick_value;
   return loss_per_lot>0.0;
  }

double RiskSizedVolume(const int direction,const double entry,const double stop,
                       const bool require_half_split,
                       double &initial_risk_account)
  {
   initial_risk_account=0.0;
   double loss_per_lot=0.0;
   if(!LossPerLot(direction,entry,stop,loss_per_lot) || loss_per_lot<=0.0)
      return 0.0;
   double risk_budget=AccountInfoDouble(ACCOUNT_EQUITY)*InpRiskPercent/100.0;
   if(risk_budget<=0.0)
      return 0.0;
   double raw=risk_budget/loss_per_lot;
   raw=ApplyLotConsistencyClamp(raw);
   double volume=0.0;
   if(!MarginSafeVolume(direction,entry,raw,require_half_split,volume))
      return 0.0;
   initial_risk_account=loss_per_lot*volume;
   return volume;
  }

bool CanSplitHalf(const double volume,double &half)
  {
   double minimum=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN);
   half=FloorVolume(volume*InpSweepScaleOutFraction);
   double remainder=NormalizeDouble(volume-half,8);
   return half>=minimum-1e-10 && remainder>=minimum-1e-10 &&
      MathAbs(half/volume-InpSweepScaleOutFraction)<=1e-8;
  }

bool ValidateGeometry(const int direction,const MqlTick &tick,
                      const double entry,const double stop,const double target)
  {
   double risk=MathAbs(entry-stop);
   double reward=MathAbs(target-entry);
   double spread=tick.ask-tick.bid;
   long stops_level=SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL);
   long freeze_level=SymbolInfoInteger(_Symbol,SYMBOL_TRADE_FREEZE_LEVEL);
   double minimum_distance=(double)MathMax(stops_level,freeze_level)*_Point;
   if(risk<=0.0 || reward<=0.0 ||
      (direction>0 && !(stop<entry && target>entry)) ||
      (direction<0 && !(stop>entry && target<entry)) ||
      risk<minimum_distance || reward<minimum_distance)
     {
      g_reject_geometry++;
      RecordReason("STOP_FREEZE_GEOMETRY");
      return false;
     }
   if(spread<=0.0 || spread/risk>InpMaxSpreadToRisk)
     {
      g_reject_spread++;
      RecordReason("SPREAD_TO_RISK");
      return false;
     }
   return true;
  }

//+------------------------------------------------------------------+
//| Closed-bar data and two separable engines                        |
//+------------------------------------------------------------------+
datetime CurrentM5BarClock()
  {
   long value=0;
   if(!SeriesInfoInteger(_Symbol,PERIOD_M5,SERIES_LASTBAR_DATE,value) ||
      value<=0)
      return 0;
   return (datetime)value;
  }

bool IsNewM5Bar()
  {
   datetime clock=CurrentM5BarClock(); // clock only; never signal data
   if(clock<=0 || clock==g_last_bar_clock)
      return false;
   g_last_bar_clock=clock;
   return true;
  }

bool LoadClosedBars(MqlRates &rates[])
  {
   ArraySetAsSeries(rates,true);
   return CopyRates(_Symbol,PERIOD_M5,1,CLOSED_BAR_COUNT,rates)==CLOSED_BAR_COUNT;
  }

bool ClosedAtr(double &atr)
  {
   atr=0.0;
   double values[1];
   if(CopyBuffer(g_atr_handle,0,1,1,values)!=1 || values[0]<=0.0)
      return false;
   atr=values[0];
   return true;
  }

bool LoadExactAsianRange(const datetime utc_reference,double &asian_high,
                         double &asian_low)
  {
   datetime utc_day_start=UtcDayStart(utc_reference);
   int day_key=UtcDateKey(utc_reference);
   if(g_asian_day_key==day_key && g_asian_high>0.0 && g_asian_low>0.0)
     {
      asian_high=g_asian_high;
      asian_low=g_asian_low;
      return true;
     }
   double high_value=-DBL_MAX;
   double low_value=DBL_MAX;
   MqlRates closed[];
   ArraySetAsSeries(closed,true);
   if(CopyRates(_Symbol,PERIOD_M5,1,ASIAN_LOOKBACK_BAR_COUNT,closed)!=
      ASIAN_LOOKBACK_BAR_COUNT)
      return false;
   for(int i=0;i<ASIAN_BAR_COUNT;i++)
     {
      datetime expected_utc=utc_day_start+(InpAsianStartMinutesUtc+i*5)*60;
      datetime expected_server=UtcToServer(expected_utc);
      bool found=false;
      for(int j=0;j<ASIAN_LOOKBACK_BAR_COUNT;j++)
        {
         if(closed[j].time!=expected_server)
            continue;
         high_value=MathMax(high_value,closed[j].high);
         low_value=MathMin(low_value,closed[j].low);
         found=true;
         break;
        }
      if(!found)
         return false;
     }
   if(high_value<=low_value || low_value<=0.0)
      return false;
   g_asian_day_key=day_key;
   g_asian_high=high_value;
   g_asian_low=low_value;
   asian_high=high_value;
   asian_low=low_value;
   g_asian_range_ready++;
   return true;
  }

bool TickVolumeZScore(const MqlRates &rates[],const int candidate_index,
                      const int prior_count,double &zscore)
  {
   zscore=0.0;
   double mean=0.0;
   for(int i=candidate_index+1;i<=candidate_index+prior_count;i++)
      mean+=(double)rates[i].tick_volume;
   mean/=prior_count;
   double variance=0.0;
   for(int i=candidate_index+1;i<=candidate_index+prior_count;i++)
     {
      double diff=(double)rates[i].tick_volume-mean;
      variance+=diff*diff;
     }
   double deviation=MathSqrt(variance/prior_count);
   if(deviation<=0.0)
      return false;
   zscore=((double)rates[candidate_index].tick_volume-mean)/deviation;
   return true;
  }

void ResetSignal(SignalDecision &signal)
  {
   ZeroMemory(signal);
   signal.engine=IDENTITY_NONE;
   signal.reason="NO_SIGNAL";
  }

bool EvaluateSweep(const MqlRates &rates[],const double atr,
                   const double asian_high,const double asian_low,
                   SignalDecision &signal)
  {
   ResetSignal(signal);
   signal.engine=IDENTITY_SWEEP;
   g_sweep_evaluated++;
   double zscore=0.0;
   if(!TickVolumeZScore(rates,0,InpVolumeLookback,zscore) ||
      zscore<=InpVolumeThreshold)
     {
      signal.reason="SWEEP_VOLUME_Z_REJECT";
      return false;
     }
   if(rates[0].low<asian_low-InpSweepEpsilonMult*atr &&
      rates[0].close>asian_low)
     {
      signal.fired=true;
      signal.direction=1;
      signal.stop=rates[0].low-InpSweepStopAtrMult*atr;
      signal.tp1=(asian_high+asian_low)/2.0;
      signal.tp2=asian_high;
      signal.reason="ASIAN_LOW_SWEEP_RECLAIM";
      g_sweep_signals++;
      return true;
     }
   if(rates[0].high>asian_high+InpSweepEpsilonMult*atr &&
      rates[0].close<asian_high)
     {
      signal.fired=true;
      signal.direction=-1;
      signal.stop=rates[0].high+InpSweepStopAtrMult*atr;
      signal.tp1=(asian_high+asian_low)/2.0;
      signal.tp2=asian_low;
      signal.reason="ASIAN_HIGH_SWEEP_RECLAIM";
      g_sweep_signals++;
      return true;
     }
   signal.reason="SWEEP_GEOMETRY_REJECT";
   return false;
  }

bool EvaluateBreakout(const MqlRates &rates[],const double atr,
                      SignalDecision &signal)
  {
   ResetSignal(signal);
   signal.engine=IDENTITY_BREAKOUT;
   g_breakout_evaluated++;
   double prior_range_mean=0.0;
   for(int i=2;i<=51;i++)
      prior_range_mean+=rates[i].high-rates[i].low;
   prior_range_mean/=50.0;
   double bar2_range=rates[1].high-rates[1].low;
   if(prior_range_mean<=0.0 ||
      !(bar2_range<BREAKOUT_CONTRACTION_RATIO*prior_range_mean))
     {
      signal.reason="BREAKOUT_CONTRACTION_REJECT";
      return false;
     }
   double box_high=-DBL_MAX;
   double box_low=DBL_MAX;
   for(int i=1;i<=15;i++)
     {
      box_high=MathMax(box_high,rates[i].high);
      box_low=MathMin(box_low,rates[i].low);
     }
   double prior_volume_mean=0.0;
   for(int i=1;i<=InpVolumeLookback;i++)
      prior_volume_mean+=(double)rates[i].tick_volume;
   prior_volume_mean/=InpVolumeLookback;
   if((double)rates[0].tick_volume<=prior_volume_mean)
     {
      signal.reason="BREAKOUT_VOLUME_MEAN_REJECT";
      return false;
     }
   if(rates[0].close>box_high+BREAKOUT_BUFFER_ATR_MULT*atr)
     {
      signal.fired=true;
      signal.direction=1;
      signal.stop=box_low-BREAKOUT_STOP_ATR_MULT*atr;
      signal.reason="BOX_UP_BREAKOUT";
      g_breakout_signals++;
      return true;
     }
   if(rates[0].close<box_low-BREAKOUT_BUFFER_ATR_MULT*atr)
     {
      signal.fired=true;
      signal.direction=-1;
      signal.stop=box_high+BREAKOUT_STOP_ATR_MULT*atr;
      signal.reason="BOX_DOWN_BREAKOUT";
      g_breakout_signals++;
      return true;
     }
   signal.reason="BREAKOUT_BUFFER_REJECT";
   return false;
  }

bool SelectSignal(const SignalDecision &sweep,const SignalDecision &breakout,
                  SignalDecision &selected)
  {
   ResetSignal(selected);
   if(sweep.fired)
     {
      if(breakout.fired)
        {
         g_both_collisions++;
         RecordReason(SWEEP_PRIORITY);
        }
      selected=sweep;
      g_sweep_selected++;
      return true;
     }
   if(breakout.fired)
     {
      selected=breakout;
      g_breakout_selected++;
      return true;
     }
   g_no_signal++;
   return false;
  }

//+------------------------------------------------------------------+
//| Position context and lifecycle-v3 telemetry                      |
//+------------------------------------------------------------------+
string PositionStateKey(const ulong position_id,const string suffix)
  {
   return StringFormat("LOMXP.%I64d.%I64d.%I64u.%s",
                       AccountInfoInteger(ACCOUNT_LOGIN),InpMagic,
                       position_id,suffix);
  }

void PersistPositionContext()
  {
   if(g_active_position_id==0)
      return;
   GlobalVariableSet(PositionStateKey(g_active_position_id,"E"),(double)g_active_engine);
   GlobalVariableSet(PositionStateKey(g_active_position_id,"D"),(double)g_active_direction);
   GlobalVariableSet(PositionStateKey(g_active_position_id,"P"),g_active_entry);
   GlobalVariableSet(PositionStateKey(g_active_position_id,"S"),g_active_initial_sl);
   GlobalVariableSet(PositionStateKey(g_active_position_id,"T"),g_active_initial_tp);
   GlobalVariableSet(PositionStateKey(g_active_position_id,"R"),g_active_initial_risk);
   GlobalVariableSet(PositionStateKey(g_active_position_id,"M"),g_active_midpoint);
   GlobalVariableSet(PositionStateKey(g_active_position_id,"V"),g_active_initial_volume);
   GlobalVariableSet(PositionStateKey(g_active_position_id,"X"),g_active_tp1_done ? 1.0 : 0.0);
   GlobalVariableSet(PositionStateKey(g_active_position_id,"B"),g_active_be_done ? 1.0 : 0.0);
  }

bool LoadPositionContext(const ulong position_id)
  {
   string engine_key=PositionStateKey(position_id,"E");
   if(!GlobalVariableCheck(engine_key))
      return false;
   g_active_position_id=position_id;
   g_active_engine=(EngineIdentity)(int)GlobalVariableGet(engine_key);
   g_active_direction=(int)GlobalVariableGet(PositionStateKey(position_id,"D"));
   g_active_entry=GlobalVariableGet(PositionStateKey(position_id,"P"));
   g_active_initial_sl=GlobalVariableGet(PositionStateKey(position_id,"S"));
   g_active_initial_tp=GlobalVariableGet(PositionStateKey(position_id,"T"));
   g_active_initial_risk=GlobalVariableGet(PositionStateKey(position_id,"R"));
   g_active_midpoint=GlobalVariableGet(PositionStateKey(position_id,"M"));
   g_active_initial_volume=GlobalVariableGet(PositionStateKey(position_id,"V"));
   g_active_tp1_done=GlobalVariableGet(PositionStateKey(position_id,"X"))>0.5;
   g_active_be_done=GlobalVariableGet(PositionStateKey(position_id,"B"))>0.5;
   return true;
  }

bool ReconstructPositionContext(const ulong position_id)
  {
   if(position_id==0 || !HistorySelect(0,TimeCurrent()+60))
      return false;
   double weighted_entry=0.0;
   double initial_volume=0.0;
   double initial_sl=0.0;
   double initial_tp=0.0;
   double initial_risk=0.0;
   int direction=0;
   EngineIdentity engine=IDENTITY_NONE;
   datetime first_entry_time=0;
   for(int i=0;i<HistoryDealsTotal();i++)
     {
      ulong deal=HistoryDealGetTicket(i);
      if(deal==0 ||
         (ulong)HistoryDealGetInteger(deal,DEAL_POSITION_ID)!=position_id ||
         HistoryDealGetString(deal,DEAL_SYMBOL)!=_Symbol ||
         (long)HistoryDealGetInteger(deal,DEAL_MAGIC)!=InpMagic ||
         (ENUM_DEAL_ENTRY)HistoryDealGetInteger(deal,DEAL_ENTRY)!=DEAL_ENTRY_IN)
         continue;
      double volume=HistoryDealGetDouble(deal,DEAL_VOLUME);
      double price=HistoryDealGetDouble(deal,DEAL_PRICE);
      if(volume<=0.0 || price<=0.0)
         continue;
      ulong order=(ulong)HistoryDealGetInteger(deal,DEAL_ORDER);
      if(initial_volume<=0.0)
        {
         ENUM_DEAL_TYPE deal_type=(ENUM_DEAL_TYPE)HistoryDealGetInteger(deal,DEAL_TYPE);
         direction=deal_type==DEAL_TYPE_BUY ? 1 : -1;
         engine=EngineFromOrder(order);
         first_entry_time=(datetime)HistoryDealGetInteger(deal,DEAL_TIME);
         if(order>0 && HistoryOrderSelect(order))
           {
            initial_sl=HistoryOrderGetDouble(order,ORDER_SL);
            initial_tp=HistoryOrderGetDouble(order,ORDER_TP);
           }
        }
      weighted_entry+=price*volume;
      initial_volume+=volume;
     }
   if(initial_volume<=0.0 || direction==0 || engine==IDENTITY_NONE)
      return false;
   double entry=weighted_entry/initial_volume;
   double loss_per_lot=0.0;
   if(initial_sl>0.0 && LossPerLot(direction,entry,initial_sl,loss_per_lot))
      initial_risk=loss_per_lot*initial_volume;
   double midpoint=0.0;
   if(engine==IDENTITY_SWEEP && first_entry_time>0)
     {
      double asian_high=0.0;
      double asian_low=0.0;
      if(LoadExactAsianRange(ServerToUtc(first_entry_time),asian_high,asian_low))
         midpoint=(asian_high+asian_low)/2.0;
     }
   g_active_position_id=position_id;
   g_active_engine=engine;
   g_active_direction=direction;
   g_active_entry=entry;
   g_active_initial_sl=initial_sl;
   g_active_initial_tp=initial_tp;
   g_active_initial_risk=initial_risk;
   g_active_midpoint=midpoint;
   g_active_initial_volume=initial_volume;
   g_active_tp1_done=false;
   g_active_be_done=false;
   ulong ticket=OwnedPositionTicket();
   if(ticket!=0 && PositionSelectByTicket(ticket) &&
      (ulong)PositionGetInteger(POSITION_IDENTIFIER)==position_id)
     {
      double current_volume=PositionGetDouble(POSITION_VOLUME);
      double current_sl=PositionGetDouble(POSITION_SL);
      double step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);
      g_active_tp1_done=current_volume<initial_volume-MathMax(1e-8,step/2.0);
      g_active_be_done=(direction>0 && current_sl>=entry-_Point/2.0) ||
                       (direction<0 && current_sl<=entry+_Point/2.0 &&
                        current_sl>0.0);
     }
   PersistPositionContext();
   return true;
  }

void ClearActiveContext()
  {
   g_active_position_id=0;
   g_active_engine=IDENTITY_NONE;
   g_active_direction=0;
   g_active_entry=0.0;
   g_active_initial_sl=0.0;
   g_active_initial_tp=0.0;
   g_active_initial_risk=0.0;
   g_active_midpoint=0.0;
   g_active_initial_volume=0.0;
   g_active_tp1_done=false;
   g_active_be_done=false;
   g_tp1_request_pending=false;
  }

void ClearPendingEntryContext()
  {
   g_entry_request_pending=false;
   g_pending_engine=IDENTITY_NONE;
   g_pending_direction=0;
   g_pending_sl=0.0;
   g_pending_tp=0.0;
   g_pending_midpoint=0.0;
   g_pending_initial_risk=0.0;
  }

EngineIdentity EngineFromOrder(const ulong order_id)
  {
   if(order_id==0 || !HistoryOrderSelect(order_id))
      return IDENTITY_NONE;
   string comment=HistoryOrderGetString(order_id,ORDER_COMMENT);
   if(StringFind(comment,"SWEEP")>=0) return IDENTITY_SWEEP;
   if(StringFind(comment,"BREAKOUT")>=0) return IDENTITY_BREAKOUT;
   return IDENTITY_NONE;
  }

bool RemainingVolumeThroughDeal(const ulong position_id,const ulong target_deal,
                                double &remaining)
  {
   remaining=0.0;
   if(!HistorySelect(0,TimeCurrent()+60))
      return false;
   bool found=false;
   for(int i=0;i<HistoryDealsTotal();i++)
     {
      ulong ticket=HistoryDealGetTicket(i);
      if(ticket==0 ||
         (ulong)HistoryDealGetInteger(ticket,DEAL_POSITION_ID)!=position_id ||
         HistoryDealGetString(ticket,DEAL_SYMBOL)!=_Symbol ||
         (long)HistoryDealGetInteger(ticket,DEAL_MAGIC)!=InpMagic)
         continue;
      ENUM_DEAL_ENTRY entry=(ENUM_DEAL_ENTRY)HistoryDealGetInteger(ticket,DEAL_ENTRY);
      double volume=HistoryDealGetDouble(ticket,DEAL_VOLUME);
      if(entry==DEAL_ENTRY_IN)
         remaining+=volume;
      else if(entry==DEAL_ENTRY_OUT || entry==DEAL_ENTRY_OUT_BY)
         remaining-=volume;
      if(ticket==target_deal)
        {
         found=true;
         break;
        }
     }
   if(remaining<0.0 && MathAbs(remaining)<1e-8)
      remaining=0.0;
   return found && remaining>=0.0;
  }

bool NetProfitThroughDeal(const ulong position_id,const ulong target_deal,
                          double &net_profit)
  {
   net_profit=0.0;
   if(!HistorySelect(0,TimeCurrent()+60))
      return false;
   bool found=false;
   for(int i=0;i<HistoryDealsTotal();i++)
     {
      ulong ticket=HistoryDealGetTicket(i);
      if(ticket==0 ||
         (ulong)HistoryDealGetInteger(ticket,DEAL_POSITION_ID)!=position_id ||
         HistoryDealGetString(ticket,DEAL_SYMBOL)!=_Symbol ||
         (long)HistoryDealGetInteger(ticket,DEAL_MAGIC)!=InpMagic)
         continue;
      net_profit+=HistoryDealGetDouble(ticket,DEAL_PROFIT)+
                  HistoryDealGetDouble(ticket,DEAL_COMMISSION)+
                  HistoryDealGetDouble(ticket,DEAL_SWAP)+
                  HistoryDealGetDouble(ticket,DEAL_FEE);
      if(ticket==target_deal)
        {
         found=true;
         break;
        }
     }
   return found;
  }

string FinalCloseKey(const ulong position_id)
  {
   return StringFormat("LOMXF.%I64d.%I64d.%I64u",
                       AccountInfoInteger(ACCOUNT_LOGIN),InpMagic,position_id);
  }

bool FinalCloseAlreadyLogged(const ulong position_id)
  {
   string key=FinalCloseKey(position_id);
   return GlobalVariableCheck(key) && GlobalVariableGet(key)>0.5;
  }

void MarkFinalCloseLogged(const ulong position_id)
  {
   GlobalVariableSet(FinalCloseKey(position_id),1.0);
  }

bool WriteRunMeta()
  {
   if(!InpEnableTelemetry || g_run_meta_name=="")
      return true;
   int handle=FileOpen(g_run_meta_name,FILE_WRITE|FILE_TXT|FILE_ANSI);
   if(handle==INVALID_HANDLE)
      return false;
   string payload="{";
   payload+="\"schema_version\":\"alphafactory_run_meta.v1\",";
   payload+="\"run_id\":\""+JsonEscape(g_run_id)+"\",";
   payload+="\"ea_name\":\""+EA_NAME+"\",";
   payload+="\"symbol\":\""+JsonEscape(_Symbol)+"\",";
   payload+="\"telemetry_profile\":\""+TELEMETRY_PROFILE+"\",";
   payload+="\"hypothesis_id\":\""+JsonEscape(InpHypothesisId)+"\",";
   payload+="\"variant_tag\":\""+JsonEscape(InpVariantTag)+"\",";
   payload+="\"engine_mode\":\""+EngineModeName()+"\",";
   payload+=StringFormat("\"magic\":%I64d,",InpMagic);
   payload+="\"timeframe\":\"M5\",";
   payload+="\"clock_profile\":\"FIVEPERCENT_EU_TO_2023_US_FROM_2024\",";
   payload+="\"research_auto_mode\":"+
            (InpResearchAutoMode ? "true" : "false")+",";
   payload+="\"build_only_default\":"+
            (InpHypothesisId=="UNREGISTERED_BUILD_ONLY" ? "true" : "false")+",";
   payload+="\"economic_claims_authorized\":false,";
   payload+="\"promotion_eligible\":false,";
   payload+="\"closed_bar\":true,";
   payload+="\"funnel\":{";
   payload+=StringFormat("\"ticks_seen\":%I64d,\"closed_bars_seen\":%I64d,",g_ticks_seen,g_closed_bars_seen);
   payload+=StringFormat("\"asian_range_ready\":%I64d,\"asian_range_missing\":%I64d,",g_asian_range_ready,g_asian_range_missing);
   payload+=StringFormat("\"sweep_evaluated\":%I64d,\"sweep_signals\":%I64d,",g_sweep_evaluated,g_sweep_signals);
   payload+=StringFormat("\"breakout_evaluated\":%I64d,\"breakout_signals\":%I64d,",g_breakout_evaluated,g_breakout_signals);
   payload+=StringFormat("\"both_collisions\":%I64d,\"sweep_selected\":%I64d,",g_both_collisions,g_sweep_selected);
   payload+=StringFormat("\"breakout_selected\":%I64d,\"no_signal\":%I64d,",g_breakout_selected,g_no_signal);
   payload+=StringFormat("\"reject_daily_lock\":%I64d,\"reject_account_dd\":%I64d,",g_reject_daily_lock,g_reject_account_dd);
   payload+=StringFormat("\"reject_friday\":%I64d,\"daily_flatten_closes\":%I64d,",g_reject_friday,g_daily_flatten_closes);
   payload+=StringFormat("\"reject_trade_limit\":%I64d,\"reject_exposure\":%I64d,",g_reject_trade_limit,g_reject_exposure);
   payload+=StringFormat("\"reject_history\":%I64d,\"reject_spread\":%I64d,",g_reject_history,g_reject_spread);
   payload+=StringFormat("\"reject_geometry\":%I64d,\"reject_sizing\":%I64d,",g_reject_geometry,g_reject_sizing);
   payload+=StringFormat("\"reject_margin_stopout\":%I64d,\"margin_stopout_clamps\":%I64d,",g_reject_margin_stopout,g_margin_stopout_clamps);
   payload+=StringFormat("\"reject_order_check\":%I64d,\"reject_order_send\":%I64d,",g_reject_order_check,g_reject_order_send);
   payload+=StringFormat("\"lot_consistency_clamps\":%I64d,\"entries_opened\":%I64d,",g_lot_consistency_clamps,g_entries_opened);
   payload+=StringFormat("\"tp1_partial_closes\":%I64d,\"break_even_moves\":%I64d,",g_tp1_partial_closes,g_break_even_moves);
   payload+=StringFormat("\"final_closes\":%I64d,\"max_hold_closes\":%I64d,",g_final_closes,g_max_hold_closes);
   payload+=StringFormat("\"overnight_guard_closes\":%I64d,\"invalid_deal_events\":%I64d,",g_overnight_guard_closes,g_invalid_deal_events);
   payload+=StringFormat("\"duplicate_final_suppressed\":%I64d,",g_duplicate_final_suppressed);
   payload+="\"last_reason\":\""+JsonEscape(g_last_reason)+"\"}}";
   FileWriteString(handle,payload);
   FileClose(handle);
   return true;
  }

bool OpenTelemetry()
  {
   if(!InpEnableTelemetry)
      return false;
   g_run_id=StringFormat("%s_%I64u",SafeToken(InpHypothesisId),GetTickCount64());
   g_lifecycle_name=StringFormat("%s_LifecycleTrades_%s.csv",_Symbol,g_run_id);
   g_run_meta_name=StringFormat("%s_RunMeta_%s.json",_Symbol,g_run_id);
   g_lifecycle_handle=FileOpen(g_lifecycle_name,FILE_WRITE|FILE_CSV|FILE_ANSI,',');
   if(g_lifecycle_handle==INVALID_HANDLE)
      return false;
   FileWrite(g_lifecycle_handle,
             "event_time","utc_time","tag","action","order_type","volume",
             "price","sl","tp","reason","retcode","deal","order","symbol",
             "position_id","entry_price","initial_sl","initial_tp","risk_pts",
             "initial_risk_account","close_source","deal_reason","achievedr",
             "net_profit","swap","commission","fee","deal_profit",
             "deal_commission","deal_swap","deal_fee","deal_net","is_final_close",
             "engine_name","hypothesis_id");
   FileFlush(g_lifecycle_handle);
   return WriteRunMeta();
  }

void LogLifecycleDeal(const ulong deal)
  {
   if(!HistoryDealSelect(deal))
      return;
   if(HistoryDealGetString(deal,DEAL_SYMBOL)!=_Symbol ||
      (long)HistoryDealGetInteger(deal,DEAL_MAGIC)!=InpMagic)
      return;
   ENUM_DEAL_ENTRY entry=(ENUM_DEAL_ENTRY)HistoryDealGetInteger(deal,DEAL_ENTRY);
   if(entry!=DEAL_ENTRY_IN && entry!=DEAL_ENTRY_OUT && entry!=DEAL_ENTRY_OUT_BY)
      return;
   long deal_time_msc=HistoryDealGetInteger(deal,DEAL_TIME_MSC);
   datetime deal_time=(datetime)HistoryDealGetInteger(deal,DEAL_TIME);
   double deal_volume=HistoryDealGetDouble(deal,DEAL_VOLUME);
   double deal_price=HistoryDealGetDouble(deal,DEAL_PRICE);
   if(deal_time_msc<=0 || deal_volume<=0.0 || deal_price<=0.0)
     {
      g_invalid_deal_events++;
      return;
     }
   ulong position_id=(ulong)HistoryDealGetInteger(deal,DEAL_POSITION_ID);
   ulong order_id=(ulong)HistoryDealGetInteger(deal,DEAL_ORDER);
   ENUM_DEAL_TYPE deal_type=(ENUM_DEAL_TYPE)HistoryDealGetInteger(deal,DEAL_TYPE);
   ENUM_DEAL_REASON deal_reason=(ENUM_DEAL_REASON)HistoryDealGetInteger(deal,DEAL_REASON);
   double profit=HistoryDealGetDouble(deal,DEAL_PROFIT);
   double commission=HistoryDealGetDouble(deal,DEAL_COMMISSION);
   double swap=HistoryDealGetDouble(deal,DEAL_SWAP);
   double fee=HistoryDealGetDouble(deal,DEAL_FEE);
   bool is_open=(entry==DEAL_ENTRY_IN);
   string action="OPEN";
   bool is_final_close=false;
   EngineIdentity engine=IDENTITY_NONE;
   int direction=0;
   double row_initial_risk_account=0.0;

   if(is_open)
     {
      engine=g_pending_engine;
      if(engine==IDENTITY_NONE)
         engine=EngineFromOrder(order_id);
      direction=deal_type==DEAL_TYPE_BUY ? 1 : -1;
      if(g_active_position_id!=position_id)
        {
         ClearActiveContext();
         g_active_position_id=position_id;
         g_active_engine=engine;
         g_active_direction=direction;
         g_active_entry=deal_price;
         g_active_initial_sl=g_pending_sl;
         g_active_initial_tp=g_pending_tp;
         g_active_initial_risk=0.0;
         g_active_midpoint=g_pending_midpoint;
        }
      else if(g_active_initial_volume>0.0)
         g_active_entry=(g_active_entry*g_active_initial_volume+
                         deal_price*deal_volume)/
                        (g_active_initial_volume+deal_volume);
      double fill_loss_per_lot=0.0;
      if(LossPerLot(direction,deal_price,g_active_initial_sl,fill_loss_per_lot))
        {
         row_initial_risk_account=fill_loss_per_lot*deal_volume;
         g_active_initial_risk+=row_initial_risk_account;
        }
      g_active_initial_volume+=deal_volume;
      PersistPositionContext();
      ClearPendingEntryContext();
      if(g_daily_last_position!=position_id)
        {
         g_daily_last_position=position_id;
         g_daily_trades++;
         g_entries_opened++;
         PersistDailyState();
        }
     }
   else
     {
      if(g_active_position_id!=position_id &&
         !LoadPositionContext(position_id))
         ReconstructPositionContext(position_id);
      engine=g_active_engine;
      direction=g_active_direction;
      double remaining=0.0;
      bool remaining_known=RemainingVolumeThroughDeal(position_id,deal,remaining);
      double step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);
      bool final_candidate=remaining_known && remaining<=MathMax(1e-8,step/2.0);
      if(final_candidate && !FinalCloseAlreadyLogged(position_id))
        {
         action="CLOSE";
         is_final_close=true;
        }
      else
        {
         action="CLOSE_PARTIAL";
         if(final_candidate)
            g_duplicate_final_suppressed++;
        }
      if(!is_final_close && engine==IDENTITY_SWEEP)
        {
         g_active_tp1_done=true;
         g_tp1_request_pending=false;
         g_tp1_partial_closes++;
         PersistPositionContext();
        }
     }

   double net_profit=profit+commission+swap+fee;
   double aggregate_net=0.0;
   if(NetProfitThroughDeal(position_id,deal,aggregate_net))
      net_profit=aggregate_net;
   double achieved_r=(g_active_initial_risk>0.0)
                     ? net_profit/g_active_initial_risk : 0.0;
   double risk_points=(is_open && g_active_initial_sl>0.0)
                      ? MathAbs(deal_price-g_active_initial_sl)/_Point
                      : ((g_active_entry>0.0 && g_active_initial_sl>0.0)
                         ? MathAbs(g_active_entry-g_active_initial_sl)/_Point
                         : 0.0);
   if(!is_open)
      row_initial_risk_account=g_active_initial_risk;
   double deal_net=profit+commission+swap+fee;
   string reason_text=EnumToString(deal_reason);
   uint written=0;
   if(g_lifecycle_handle!=INVALID_HANDLE)
     {
      written=FileWrite(g_lifecycle_handle,
                TimeToString(deal_time,TIME_DATE|TIME_SECONDS),
                TimeToString(ServerToUtc(deal_time),TIME_DATE|TIME_SECONDS),
                InpVariantTag,action,direction<0 ? "SELL" : "BUY",
                DoubleToString(deal_volume,8),DoubleToString(deal_price,_Digits),
                DoubleToString(g_active_initial_sl,_Digits),
                DoubleToString(g_active_initial_tp,_Digits),reason_text,"0",
                StringFormat("%I64u",deal),StringFormat("%I64u",order_id),
                _Symbol,StringFormat("%I64u",position_id),
                DoubleToString(g_active_entry,_Digits),
                DoubleToString(g_active_initial_sl,_Digits),
                DoubleToString(g_active_initial_tp,_Digits),
                DoubleToString(risk_points,4),
                DoubleToString(row_initial_risk_account,8),reason_text,reason_text,
                DoubleToString(achieved_r,8),DoubleToString(net_profit,8),
                DoubleToString(swap,8),DoubleToString(commission,8),
                DoubleToString(fee,8),DoubleToString(profit,8),
                DoubleToString(commission,8),DoubleToString(swap,8),
                DoubleToString(fee,8),DoubleToString(deal_net,8),
                is_final_close ? "1" : "0",
                EngineName(engine),InpHypothesisId);
      FileFlush(g_lifecycle_handle);
     }
   if(is_final_close && written>0)
     {
      MarkFinalCloseLogged(position_id);
      g_final_closes++;
      ClearActiveContext();
     }
   WriteRunMeta();
  }

//+------------------------------------------------------------------+
//| Entry and active Sweep management                                |
//+------------------------------------------------------------------+
bool SubmitEntry(const SignalDecision &signal,const double volume,
                 const double entry,const double stop,const double target,
                 const double initial_risk_account)
  {
   MqlTradeRequest request;
   MqlTradeCheckResult check;
   MqlTradeResult result;
   ZeroMemory(request);
   ZeroMemory(check);
   ZeroMemory(result);
   request.action=TRADE_ACTION_DEAL;
   request.magic=(ulong)InpMagic;
   request.symbol=_Symbol;
   request.volume=volume;
   request.type=signal.direction>0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
   request.price=entry;
   request.sl=stop;
   request.tp=target;
   request.deviation=(ulong)InpDeviationPoints;
   request.type_filling=FillingMode();
   request.comment=signal.engine==IDENTITY_SWEEP
                   ? (signal.direction>0 ? "LOMX_SWEEP_BUY" : "LOMX_SWEEP_SELL")
                   : (signal.direction>0 ? "LOMX_BREAKOUT_BUY" : "LOMX_BREAKOUT_SELL");
   g_pending_engine=signal.engine;
   g_pending_direction=signal.direction;
   g_pending_sl=stop;
   g_pending_tp=target;
   g_pending_midpoint=signal.tp1;
   g_pending_initial_risk=initial_risk_account;
   g_entry_request_pending=true;
   if(!OrderCheck(request,check))
     {
      ClearPendingEntryContext();
      g_reject_order_check++;
      RecordReason("ENTRY_ORDER_CHECK");
      return false;
     }
   bool sent=OrderSend(request,result); // synchronous OrderSend; async is disabled
   if(!sent || !AcceptedRetcode(result.retcode))
     {
      ClearPendingEntryContext();
      g_reject_order_send++;
      RecordReason("ENTRY_ORDER_SEND");
      return false;
     }
   RecordReason(signal.reason+"_SUBMITTED_"+EngineName(signal.engine));
   return true;
  }

bool PrepareAndSubmit(const SignalDecision &signal,const MqlTick &tick)
  {
   double entry=signal.direction>0 ? tick.ask : tick.bid;
   double stop=signal.direction>0 ? NormalizePriceToTick(signal.stop,false)
                                  : NormalizePriceToTick(signal.stop,true);
   double risk=MathAbs(entry-stop);
   if(risk<=0.0)
     {
      g_reject_geometry++;
      RecordReason("NONPOSITIVE_RISK");
      return false;
     }
   double target=0.0;
   if(signal.engine==IDENTITY_SWEEP)
     {
      target=signal.direction>0 ? NormalizePriceToTick(signal.tp2,false)
                                : NormalizePriceToTick(signal.tp2,true);
      double midpoint=signal.tp1;
      double reward=MathAbs(target-entry);
      bool midpoint_valid=signal.direction>0 ? midpoint>entry && midpoint<target
                                             : midpoint<entry && midpoint>target;
      if(!midpoint_valid || reward/risk<InpSweepMinTp2R)
        {
         g_reject_geometry++;
         RecordReason("SWEEP_TP2_LT_1P5R_OR_TP1_INVALID");
         return false;
        }
     }
   else
     {
      double raw_target=signal.direction>0 ? entry+BREAKOUT_TARGET_R*risk
                                           : entry-BREAKOUT_TARGET_R*risk;
      target=signal.direction>0 ? NormalizePriceToTick(raw_target,false)
                                : NormalizePriceToTick(raw_target,true);
     }
   if(!ValidateGeometry(signal.direction,tick,entry,stop,target))
      return false;
   double initial_risk_account=0.0;
   double volume=RiskSizedVolume(signal.direction,entry,stop,
                                 signal.engine==IDENTITY_SWEEP,
                                 initial_risk_account);
   if(volume<=0.0)
     {
      g_reject_sizing++;
      RecordReason("RISK_SIZING_ZERO");
      return false;
     }
   if(signal.engine==IDENTITY_SWEEP)
     {
      double half=0.0;
      if(!CanSplitHalf(volume,half))
        {
         g_reject_sizing++;
         RecordReason("SWEEP_VOLUME_NOT_50PCT_SPLITTABLE");
         return false;
        }
     }
   return SubmitEntry(signal,volume,entry,stop,target,initial_risk_account);
  }

bool SubmitPartialClose(const ulong ticket)
  {
   if(g_tp1_request_pending || !PositionSelectByTicket(ticket))
      return false;
   double current_volume=PositionGetDouble(POSITION_VOLUME);
   double half=0.0;
   if(!CanSplitHalf(current_volume,half))
     {
      RecordReason("TP1_PARTIAL_VOLUME_INVALID");
      return false;
     }
   g_tp1_request_pending=true;
   if(!SubmitCloseByTicket(ticket,"LOMX_SWEEP_TP1",half))
     {
      g_tp1_request_pending=false;
      return false;
     }
   return true;
  }

bool SubmitBreakEven(const ulong ticket)
  {
   if(!PositionSelectByTicket(ticket))
      return false;
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick))
      return false;
   ENUM_POSITION_TYPE type=(ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE);
   double entry=PositionGetDouble(POSITION_PRICE_OPEN);
   double current_sl=PositionGetDouble(POSITION_SL);
   double current_tp=PositionGetDouble(POSITION_TP);
   long stops_level=SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL);
   long freeze_level=SymbolInfoInteger(_Symbol,SYMBOL_TRADE_FREEZE_LEVEL);
   double minimum_distance=(double)MathMax(stops_level,freeze_level)*_Point;
   if((type==POSITION_TYPE_BUY && current_sl>=entry-_Point/2.0) ||
      (type==POSITION_TYPE_SELL && current_sl<=entry+_Point/2.0 && current_sl>0.0))
     {
      g_active_be_done=true;
      PersistPositionContext();
      return true;
     }
   if((type==POSITION_TYPE_BUY && tick.bid-entry<minimum_distance) ||
      (type==POSITION_TYPE_SELL && entry-tick.ask<minimum_distance))
      return false;
   MqlTradeRequest request;
   MqlTradeCheckResult check;
   MqlTradeResult result;
   ZeroMemory(request);
   ZeroMemory(check);
   ZeroMemory(result);
   request.action=TRADE_ACTION_SLTP;
   request.position=ticket;
   request.magic=(ulong)InpMagic;
   request.symbol=_Symbol;
   request.sl=NormalizePriceToTick(entry,type==POSITION_TYPE_SELL);
   request.tp=current_tp;
   if(!OrderCheck(request,check) || !OrderSend(request,result) ||
      !AcceptedRetcode(result.retcode))
     {
      RecordReason("BREAK_EVEN_MODIFY_REJECT");
      return false;
     }
   g_active_be_done=true;
   g_break_even_moves++;
   PersistPositionContext();
   return true;
  }

void ManageOwnedPosition(const datetime utc_now)
  {
   ulong ticket=OwnedPositionTicket();
   if(ticket==0 || !PositionSelectByTicket(ticket))
      return;
   ulong position_id=(ulong)PositionGetInteger(POSITION_IDENTIFIER);
   datetime position_server_time=(datetime)PositionGetInteger(POSITION_TIME);
   datetime position_utc_time=ServerToUtc(position_server_time);
   if(UtcDateKey(position_utc_time)!=UtcDateKey(utc_now))
     {
      if(SubmitCloseByTicket(ticket,"LOMX_OVERNIGHT_GUARD"))
         g_overnight_guard_closes++;
      return;
     }
   if(g_active_position_id!=position_id &&
      !LoadPositionContext(position_id) &&
      !ReconstructPositionContext(position_id))
      return;
   int held_bars=iBarShift(_Symbol,PERIOD_M5,position_server_time,false);
   if(held_bars>=InpMaxHoldBars)
     {
      if(SubmitCloseByTicket(ticket,"LOMX_MAX_HOLD"))
         g_max_hold_closes++;
      return;
     }
   if(g_active_engine!=IDENTITY_SWEEP)
      return;
   if(g_active_tp1_done)
     {
      if(!g_active_be_done)
         SubmitBreakEven(ticket);
      return;
     }
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick))
      return;
   bool reached=g_active_direction>0 ? tick.bid>=g_active_midpoint
                                     : tick.ask<=g_active_midpoint;
   if(reached)
      SubmitPartialClose(ticket);
  }

//+------------------------------------------------------------------+
//| Validation and event handlers                                    |
//+------------------------------------------------------------------+
bool SafeIdentifier(const string value)
  {
   if(StringLen(value)<1 || StringLen(value)>80)
      return false;
   return SafeToken(value)==value;
  }

bool ValidateInputs()
  {
   if(!InpResearchAutoMode)
      return false;
   if(!InpEnableTelemetry || InpHypothesisId=="UNREGISTERED_BUILD_ONLY" ||
      !SafeIdentifier(InpHypothesisId) || _Period!=PERIOD_M5)
      return false;
   if(InpMagic<=0 || InpRiskPercent<=0.0 || InpRiskPercent>2.0 ||
      MathAbs(InpMaxDailyLossPct-DAILY_LOSS_LOCK_PCT)>1e-10 ||
      MathAbs(InpMaxAccountDrawdownPct-8.0)>1e-10 ||
      InpMaxTradesPerDay!=3 ||
      InpMaxSpreadToRisk<=0.0 || InpMaxSpreadToRisk>1.0 ||
      InpDeviationPoints<0 || InpMaxHoldBars<1 ||
      InpATRPeriod!=ATR_PERIOD ||
      MathAbs(InpSweepEpsilonMult-SWEEP_ATR_MULT)>1e-10 ||
      MathAbs(InpSweepStopAtrMult-SWEEP_STOP_ATR_MULT)>1e-10 ||
      MathAbs(InpSweepMinTp2R-SWEEP_MIN_TP2_R)>1e-10 ||
      InpVolumeLookback!=20 ||
      MathAbs(InpVolumeThreshold-SWEEP_VOLUME_Z)>1e-10 ||
      InpAsianStartMinutesUtc!=ASIAN_START_MINUTE ||
      InpAsianEndMinutesUtc!=ASIAN_END_MINUTE ||
      InpTradeStartMinutesUtc!=TRADE_START_MINUTE ||
      InpTradeEndMinutesUtc!=TRADE_END_MINUTE ||
      InpDailyFlattenMinutesUtc!=20*60 ||
      InpFridayFlattenMinutesUtc!=20*60 ||
      MathAbs(InpSweepScaleOutFraction-0.50)>1e-10 ||
      InpLotConsistencyMinFills!=10 ||
      InpLotConsistencyLookbackFills!=10 ||
      MathAbs(InpLotConsistencyMinFactor-0.50)>1e-10 ||
      MathAbs(InpLotConsistencyMaxFactor-1.50)>1e-10)
      return false;
   return true;
  }

int OnInit()
  {
   if(!ValidateInputs())
     {
      Print("LOMX default-off/build-only guard: set registered authority, telemetry and M5 explicitly.");
      return INIT_PARAMETERS_INCORRECT;
     }
   g_atr_handle=iATR(_Symbol,PERIOD_M5,InpATRPeriod);
   if(g_atr_handle==INVALID_HANDLE)
      return INIT_FAILED;
   g_daily_prefix=DailyStatePrefix();
   LoadDailyState(ServerToUtc(TimeCurrent()));
   g_last_bar_clock=CurrentM5BarClock();
   if(!OpenTelemetry())
      return INIT_FAILED;
   ulong ticket=OwnedPositionTicket();
   if(ticket!=0 && PositionSelectByTicket(ticket))
     {
      ulong position_id=(ulong)PositionGetInteger(POSITION_IDENTIFIER);
      if(!LoadPositionContext(position_id))
         ReconstructPositionContext(position_id);
     }
   PrintFormat("LOMX engineering scaffold init hyp=%s engine=%s symbol=%s timeframe=M5 economic_claim=false",
               InpHypothesisId,EngineModeName(),_Symbol);
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
   if(g_atr_handle!=INVALID_HANDLE)
      IndicatorRelease(g_atr_handle);
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
   datetime server_now=TimeCurrent();
   datetime utc_now=ServerToUtc(server_now);
   EnforceDailyAndFridayRisk(utc_now);
   ManageOwnedPosition(utc_now);
   if(!IsNewM5Bar())
      return;
   g_closed_bars_seen++;

   MqlRates rates[];
   if(!LoadClosedBars(rates))
     {
      g_reject_history++;
      RecordReason("CLOSED_BAR_HISTORY_MISSING");
      return;
     }
   datetime signal_utc=ServerToUtc(rates[0].time);
   MqlDateTime signal_parts;
   TimeToStruct(signal_utc,signal_parts);
   int signal_minute_of_day=MinuteOfDay(signal_parts);
   if(signal_parts.day_of_week==0 || signal_parts.day_of_week==6 ||
      signal_minute_of_day<InpTradeStartMinutesUtc ||
      signal_minute_of_day>=InpTradeEndMinutesUtc)
      return;
   if(g_daily_locked || g_account_dd_locked)
     {
      if(g_daily_locked)
        {
         g_reject_daily_lock++;
         RecordReason("DAILY_LOCK_ENTRY_REJECT");
        }
      else
        {
         g_reject_account_dd++;
         RecordReason("ACCOUNT_DD_ENTRY_REJECT");
        }
      return;
     }
   if(g_daily_trades>=InpMaxTradesPerDay)
     {
      g_reject_trade_limit++;
      RecordReason("MAX_TRADES_PER_DAY");
      return;
     }
   if(OwnedExposureExists())
     {
      g_reject_exposure++;
      RecordReason("OWNED_SYMBOL_MAGIC_EXPOSURE");
      return;
     }

   double atr=0.0;
   if(!ClosedAtr(atr))
     {
      g_reject_history++;
      RecordReason("CLOSED_BAR_HISTORY_MISSING");
      return;
     }
   double asian_high=0.0;
   double asian_low=0.0;
   if(!LoadExactAsianRange(signal_utc,asian_high,asian_low))
     {
      g_asian_range_missing++;
      g_reject_history++;
      RecordReason("EXACT_ASIAN_RANGE_MISSING");
      return;
     }

   SignalDecision sweep;
   SignalDecision breakout;
   SignalDecision selected;
   ResetSignal(sweep);
   ResetSignal(breakout);
   if(InpEngineMode==ENGINE_SWEEP || InpEngineMode==ENGINE_BOTH)
      EvaluateSweep(rates,atr,asian_high,asian_low,sweep);
   if(InpEngineMode==ENGINE_BREAKOUT || InpEngineMode==ENGINE_BOTH)
      EvaluateBreakout(rates,atr,breakout);
   if(!SelectSignal(sweep,breakout,selected))
      return;
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick) || tick.ask<=0.0 || tick.bid<=0.0)
     {
      g_reject_geometry++;
      RecordReason("NO_EXECUTABLE_QUOTE");
      return;
     }
   PrepareAndSubmit(selected,tick);
  }
