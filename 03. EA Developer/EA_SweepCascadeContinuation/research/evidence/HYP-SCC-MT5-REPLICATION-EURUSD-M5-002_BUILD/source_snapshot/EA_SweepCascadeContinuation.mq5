#property copyright "AlphaFactory research"
#property version   "1.00"
#property strict
#property description "Owner-directed SCC EURUSD M5 native MT5 diagnostic"
#property description "Closed-bar confirmed pivot break versus hold-retest continuation"

enum ENUM_SCC_STAGE
  {
   SCC_WAIT=0,
   SCC_AWAIT_HOLD=1,
   SCC_AWAIT_RETEST=2
  };

struct PivotState
  {
   bool valid;
   double level;
   datetime pivot_time;
   datetime confirmed_time;
  };

struct CandidateState
  {
   ENUM_SCC_STAGE stage;
   int direction;
   double level;
   datetime break_time;
   double break_open;
   double break_high;
   double break_low;
   double break_close;
   double break_atr;
   datetime hold_time;
   double hold_high;
   double hold_low;
   double hold_close;
   int passage_lag;
   datetime last_state_time;
  };

struct TradeDecision
  {
   int direction;
   datetime decision_time;
   double level;
   double atr;
   double planned_stop;
   int passage_lag;
   string event_code;
  };

input bool   InpResearchAutoMode=true;
input bool   InpEnableTelemetry=true;
input string InpHypothesisId="HYP-SCC-MT5-REPLICATION-EURUSD-M5-002";
input string InpVariantTag="CONTROL_FIRST_CLOSE_BREAK";
input bool   InpUseHoldRetest=false;
input long   InpMagic=5600752;

input int    InpPivotStrength=2;
input int    InpRetestBars=12;
input int    InpAtrPeriod=14;
input double InpStopAtrBuffer=0.25;
input double InpTargetR=2.00;
input int    InpMaxHoldBars=24;
input double InpRiskPercent=0.05;
input double InpMaxSpreadPips=2.00;
input double InpDeviationPips=0.50;
input int    InpBrokerGMTOffsetWinter=2;
input bool   InpBrokerFollowsEuropeDST=true;

const string EA_NAME="EA_SweepCascadeContinuation";
const string TELEMETRY_PROFILE="lifecycle-v3";
const string PREREG_SHA256="12B13C309B60BDA6AD4BC88A11F7389DB3E8EE18E9493CC2950DDB95AED53796";
const string PARENT_PLAN_SHA256="6541239D88FFF99D9C8D1E2B3C78645ECE0BE01A69FFCF32BA1620ED6557FA3B";
const string PARENT_RESULT_SHA256="B15465AF7B99BC1807550B03D0FA67B057159B0D0143CCA646803FCB2D5AB7CD";
const string SOURCE_DATA_SHA256="2959C555DB6690FD6EFD6CFB3B4C6323698E590C9B2D71E1E55F1902F724235A";

int g_atr_handle=INVALID_HANDLE;
datetime g_last_m5_bar=0;
PivotState g_pivot_high;
PivotState g_pivot_low;
CandidateState g_candidate;
int g_attempted_day_key=0;

long g_bars_seen=0;
long g_confirmed_highs=0;
long g_confirmed_lows=0;
long g_break_arms=0;
long g_long_break_arms=0;
long g_short_break_arms=0;
long g_ambiguous_breaks=0;
long g_reject_gap=0;
long g_reject_day_boundary=0;
long g_reject_hold=0;
long g_hold_pass=0;
long g_reject_close_inside=0;
long g_expire_retest=0;
long g_accept_retest=0;
long g_entries_attempted=0;
long g_entries_opened=0;
long g_spread_rejections=0;
long g_geometry_rejections=0;
long g_broker_rejections=0;
long g_exposure_rejections=0;
long g_timeout_closes=0;

ulong g_position_identifier=0;
double g_initial_entry=0.0;
double g_initial_stop=0.0;
double g_planned_risk_account=0.0;
double g_position_net=0.0;

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

int UtcDateKey(const datetime server_time)
  {
   MqlDateTime parts;
   TimeToStruct(ServerToUtc(server_time),parts);
   return parts.year*10000+parts.mon*100+parts.day;
  }

void ResetCandidate()
  {
   ZeroMemory(g_candidate);
   g_candidate.stage=SCC_WAIT;
  }

bool ReadAtrClosed(double &atr)
  {
   double values[];
   ArraySetAsSeries(values,true);
   if(CopyBuffer(g_atr_handle,0,1,1,values)!=1)
      return false;
   atr=values[0];
   return MathIsValidNumber(atr) && atr>0.0;
  }

void RefreshConfirmedPivots(MqlRates &bars[])
  {
   const int candidate_shift=4;
   const int p=candidate_shift-1;
   bool pivot_high=(bars[p].high>bars[p-2].high &&
                    bars[p].high>bars[p-1].high &&
                    bars[p].high>bars[p+1].high &&
                    bars[p].high>bars[p+2].high);
   bool pivot_low=(bars[p].low<bars[p-2].low &&
                   bars[p].low<bars[p-1].low &&
                   bars[p].low<bars[p+1].low &&
                   bars[p].low<bars[p+2].low);
   datetime confirmed_time=bars[0].time;
   if(pivot_high)
     {
      g_pivot_high.valid=true;
      g_pivot_high.level=bars[p].high;
      g_pivot_high.pivot_time=bars[p].time;
      g_pivot_high.confirmed_time=confirmed_time;
      g_confirmed_highs++;
     }
   if(pivot_low)
     {
      g_pivot_low.valid=true;
      g_pivot_low.level=bars[p].low;
      g_pivot_low.pivot_time=bars[p].time;
      g_pivot_low.confirmed_time=confirmed_time;
      g_confirmed_lows++;
     }
  }

void ConsumeArmedPivot(const int direction)
  {
   if(direction>0)
      g_pivot_high.valid=false;
   else
      g_pivot_low.valid=false;
  }

double CurrentSpreadPips()
  {
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick))
      return 0.0;
   return (tick.ask-tick.bid)/PipSize();
  }

void WriteDecisionEvent(const datetime event_time,const string event_code,
                        const string status,const int direction,
                        const double level,const MqlRates &bar,
                        const double atr,const double entry,
                        const double stop,const double target,
                        const int passage_lag)
  {
   if(!InpEnableTelemetry || g_decision_handle==INVALID_HANDLE)
      return;
   FileWrite(g_decision_handle,
             TimeToString(event_time,TIME_DATE|TIME_SECONDS),
             TimeToString(ServerToUtc(event_time),TIME_DATE|TIME_SECONDS),
             InpVariantTag,(int)g_candidate.stage,event_code,status,direction,
             DoubleToString(level,_Digits),
             DoubleToString(bar.open,_Digits),
             DoubleToString(bar.high,_Digits),
             DoubleToString(bar.low,_Digits),
             DoubleToString(bar.close,_Digits),
             DoubleToString(atr,_Digits),
             DoubleToString(entry,_Digits),
             DoubleToString(stop,_Digits),
             DoubleToString(target,_Digits),
             passage_lag,
             DoubleToString(CurrentSpreadPips(),4));
   FileFlush(g_decision_handle);
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

int VolumeDigits(const double step)
  {
   int digits=0;
   double scaled=step;
   while(digits<8 && MathAbs(scaled-MathRound(scaled))>1e-9)
     {
      scaled*=10.0;
      digits++;
     }
   return digits;
  }

double RiskSizedVolume(const int direction,const double entry,const double stop,
                       double &risk_account)
  {
   risk_account=AccountInfoDouble(ACCOUNT_EQUITY)*InpRiskPercent/100.0;
   if(risk_account<=0.0)
      return 0.0;
   double one_lot_profit=0.0;
   ENUM_ORDER_TYPE type=direction>0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
   if(!OrderCalcProfit(type,_Symbol,1.0,entry,stop,one_lot_profit))
      return 0.0;
   double one_lot_loss=MathAbs(one_lot_profit);
   if(one_lot_loss<=0.0)
      return 0.0;
   double min_volume=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN);
   double max_volume=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX);
   double step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);
   if(min_volume<=0.0 || max_volume<min_volume || step<=0.0)
      return 0.0;
   double raw=risk_account/one_lot_loss;
   double volume=MathFloor(raw/step+1e-9)*step;
   volume=MathMin(volume,max_volume);
   if(volume<min_volume)
      return 0.0;
   risk_account=one_lot_loss*volume;
   return NormalizeDouble(volume,VolumeDigits(step));
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

bool TryOpenTrade(const TradeDecision &decision,const MqlRates &bar)
  {
   g_entries_attempted++;
   if(AnySymbolExposure())
     {
      g_exposure_rejections++;
      WriteDecisionEvent(decision.decision_time,decision.event_code,
                         "EXPOSURE_REJECT",decision.direction,decision.level,
                         bar,decision.atr,0.0,decision.planned_stop,0.0,
                         decision.passage_lag);
      return false;
     }
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick))
      return false;
   double spread=(tick.ask-tick.bid)/PipSize();
   if(spread<=0.0 || spread>InpMaxSpreadPips)
     {
      g_spread_rejections++;
      WriteDecisionEvent(decision.decision_time,decision.event_code,
                         "SPREAD_REJECT",decision.direction,decision.level,
                         bar,decision.atr,0.0,decision.planned_stop,0.0,
                         decision.passage_lag);
      return false;
     }
   double entry=decision.direction>0 ? tick.ask : tick.bid;
   double stop=NormalizeDouble(decision.planned_stop,_Digits);
   double risk_distance=MathAbs(entry-stop);
   double target=NormalizeDouble(entry+decision.direction*InpTargetR*risk_distance,
                                 _Digits);
   if(decision.direction*(entry-stop)<=0.0 ||
      decision.direction*(target-entry)<=0.0)
     {
      g_geometry_rejections++;
      WriteDecisionEvent(decision.decision_time,decision.event_code,
                         "GEOMETRY_REJECT",decision.direction,decision.level,
                         bar,decision.atr,entry,stop,target,
                         decision.passage_lag);
      return false;
     }
   long stops_level=0;
   long freeze_level=0;
   if(!SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL,stops_level) ||
      !SymbolInfoInteger(_Symbol,SYMBOL_TRADE_FREEZE_LEVEL,freeze_level))
      return false;
   double minimum_distance=MathMax((double)stops_level,(double)freeze_level)*_Point;
   if(risk_distance<minimum_distance || MathAbs(target-entry)<minimum_distance)
     {
      g_broker_rejections++;
      WriteDecisionEvent(decision.decision_time,decision.event_code,
                         "BROKER_DISTANCE_REJECT",decision.direction,
                         decision.level,bar,decision.atr,entry,stop,target,
                         decision.passage_lag);
      return false;
     }
   double risk_account=0.0;
   double volume=RiskSizedVolume(decision.direction,entry,stop,risk_account);
   if(volume<=0.0 || risk_account<=0.0)
     {
      g_geometry_rejections++;
      WriteDecisionEvent(decision.decision_time,decision.event_code,
                         "SIZING_REJECT",decision.direction,decision.level,
                         bar,decision.atr,entry,stop,target,
                         decision.passage_lag);
      return false;
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
   request.volume=volume;
   request.type=decision.direction>0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
   request.price=entry;
   request.sl=stop;
   request.tp=target;
   request.deviation=(ulong)MathMax(1,MathRound(InpDeviationPips*PipSize()/_Point));
   request.type_filling=FillingMode();
   request.type_time=ORDER_TIME_GTC;
   request.comment=StringSubstr(InpHypothesisId,0,30);

   if(!OrderCheck(request,check))
     {
      g_broker_rejections++;
      PrintFormat("SCC OrderCheck rejected retcode=%u comment=%s margin=%.2f free=%.2f",
                  check.retcode,check.comment,check.margin,check.margin_free);
      WriteDecisionEvent(decision.decision_time,decision.event_code,
                         "ORDER_CHECK_REJECT",decision.direction,decision.level,
                         bar,decision.atr,entry,stop,target,
                         decision.passage_lag);
      return false;
     }

   g_initial_entry=entry;
   g_initial_stop=stop;
   g_planned_risk_account=risk_account;
   if(!OrderSend(request,result) ||
      (result.retcode!=TRADE_RETCODE_DONE &&
       result.retcode!=TRADE_RETCODE_DONE_PARTIAL &&
       result.retcode!=TRADE_RETCODE_PLACED))
     {
      g_initial_entry=0.0;
      g_initial_stop=0.0;
      g_planned_risk_account=0.0;
      g_broker_rejections++;
      WriteDecisionEvent(decision.decision_time,decision.event_code,
                         "ORDER_SEND_REJECT",decision.direction,decision.level,
                         bar,decision.atr,entry,stop,target,
                         decision.passage_lag);
      return false;
     }
   WriteDecisionEvent(decision.decision_time,decision.event_code,
                      "ORDER_ACCEPTED",decision.direction,decision.level,bar,
                      decision.atr,entry,stop,target,decision.passage_lag);
   return true;
  }

bool DetectBreak(MqlRates &bars[],int &direction,double &level)
  {
   direction=0;
   level=0.0;
   if(bars[0].time-bars[1].time!=PeriodSeconds(PERIOD_M5))
      return false;
   int day_key=UtcDateKey(bars[0].time);
   if(day_key==g_attempted_day_key)
      return false;
   bool long_break=(g_pivot_high.valid &&
                    bars[1].close<=g_pivot_high.level &&
                    bars[0].close>g_pivot_high.level);
   bool short_break=(g_pivot_low.valid &&
                     bars[1].close>=g_pivot_low.level &&
                     bars[0].close<g_pivot_low.level);
   if(long_break && short_break)
     {
      g_ambiguous_breaks++;
      return false;
     }
   if(!long_break && !short_break)
      return false;
   direction=long_break ? 1 : -1;
   level=long_break ? g_pivot_high.level : g_pivot_low.level;
   return true;
  }

TradeDecision BuildTradeDecision(const int direction,const datetime decision_time,
                                 const double level,const double atr,
                                 const double stop,const int passage_lag,
                                 const string event_code)
  {
   TradeDecision decision;
   ZeroMemory(decision);
   decision.direction=direction;
   decision.decision_time=decision_time;
   decision.level=level;
   decision.atr=atr;
   decision.planned_stop=stop;
   decision.passage_lag=passage_lag;
   decision.event_code=event_code;
   return decision;
  }

void ResolveControlBreak(const MqlRates &bar,const double atr)
  {
   double stop=(g_candidate.direction>0 ?
                g_candidate.break_low-InpStopAtrBuffer*atr :
                g_candidate.break_high+InpStopAtrBuffer*atr);
   TradeDecision decision=BuildTradeDecision(g_candidate.direction,
                                             g_candidate.break_time,
                                             g_candidate.level,atr,stop,0,
                                             "CONTROL_BREAK_ENTRY");
   WriteDecisionEvent(g_candidate.break_time,"BREAK_ARMED","CONTROL_ACCEPT",
                      g_candidate.direction,g_candidate.level,bar,atr,0.0,
                      stop,0.0,0);
   TryOpenTrade(decision,bar);
   ResetCandidate();
  }

void ArmBreak(const MqlRates &bar,const int direction,const double level,
              const double atr)
  {
   ResetCandidate();
   g_candidate.stage=InpUseHoldRetest ? SCC_AWAIT_HOLD : SCC_WAIT;
   g_candidate.direction=direction;
   g_candidate.level=level;
   g_candidate.break_time=bar.time;
   g_candidate.break_open=bar.open;
   g_candidate.break_high=bar.high;
   g_candidate.break_low=bar.low;
   g_candidate.break_close=bar.close;
   g_candidate.break_atr=atr;
   g_candidate.last_state_time=bar.time;
   g_attempted_day_key=UtcDateKey(bar.time);
   g_break_arms++;
   if(direction>0) g_long_break_arms++; else g_short_break_arms++;
   ConsumeArmedPivot(direction);
   if(InpUseHoldRetest)
      WriteDecisionEvent(bar.time,"BREAK_ARMED","AWAIT_HOLD",direction,level,
                         bar,atr,0.0,0.0,0.0,0);
   else
      ResolveControlBreak(bar,atr);
  }

void ResolveHold(const MqlRates &bar)
  {
   if(bar.time!=g_candidate.break_time+PeriodSeconds(PERIOD_M5))
     {
      g_reject_gap++;
      WriteDecisionEvent(bar.time,"REJECT_GAP","TERMINAL",
                         g_candidate.direction,g_candidate.level,bar,0.0,
                         0.0,0.0,0.0,0);
      ResetCandidate();
      return;
     }
   if(UtcDateKey(bar.time)!=UtcDateKey(g_candidate.break_time))
     {
      g_reject_day_boundary++;
      WriteDecisionEvent(bar.time,"REJECT_DAY_BOUNDARY","TERMINAL",
                         g_candidate.direction,g_candidate.level,bar,0.0,
                         0.0,0.0,0.0,0);
      ResetCandidate();
      return;
     }
   bool outside=(g_candidate.direction>0 ?
                 bar.close>g_candidate.level :
                 bar.close<g_candidate.level);
   if(!outside)
     {
      g_reject_hold++;
      WriteDecisionEvent(bar.time,"REJECT_HOLD","TERMINAL",
                         g_candidate.direction,g_candidate.level,bar,0.0,
                         0.0,0.0,0.0,0);
      ResetCandidate();
      return;
     }
   g_candidate.stage=SCC_AWAIT_RETEST;
   g_candidate.hold_time=bar.time;
   g_candidate.hold_high=bar.high;
   g_candidate.hold_low=bar.low;
   g_candidate.hold_close=bar.close;
   g_candidate.passage_lag=0;
   g_candidate.last_state_time=bar.time;
   g_hold_pass++;
   WriteDecisionEvent(bar.time,"HOLD_PASS","AWAIT_RETEST",
                      g_candidate.direction,g_candidate.level,bar,0.0,
                      0.0,0.0,0.0,0);
  }

void ResolveRetest(const MqlRates &bar)
  {
   int next_lag=g_candidate.passage_lag+1;
   if(bar.time!=g_candidate.last_state_time+PeriodSeconds(PERIOD_M5))
     {
      g_reject_gap++;
      WriteDecisionEvent(bar.time,"REJECT_GAP","TERMINAL",
                         g_candidate.direction,g_candidate.level,bar,0.0,
                         0.0,0.0,0.0,next_lag);
      ResetCandidate();
      return;
     }
   if(UtcDateKey(bar.time)!=UtcDateKey(g_candidate.break_time))
     {
      g_reject_day_boundary++;
      WriteDecisionEvent(bar.time,"REJECT_DAY_BOUNDARY","TERMINAL",
                         g_candidate.direction,g_candidate.level,bar,0.0,
                         0.0,0.0,0.0,next_lag);
      ResetCandidate();
      return;
     }
   g_candidate.passage_lag=next_lag;
   g_candidate.last_state_time=bar.time;
   bool close_inside=(g_candidate.direction>0 ?
                      bar.close<=g_candidate.level :
                      bar.close>=g_candidate.level);
   if(close_inside)
     {
      g_reject_close_inside++;
      WriteDecisionEvent(bar.time,"REJECT_CLOSE_INSIDE","TERMINAL",
                         g_candidate.direction,g_candidate.level,bar,0.0,
                         0.0,0.0,0.0,next_lag);
      ResetCandidate();
      return;
     }
   bool touched=(g_candidate.direction>0 ?
                 bar.low<=g_candidate.level :
                 bar.high>=g_candidate.level);
   if(touched)
     {
      double atr=0.0;
      if(!ReadAtrClosed(atr))
        {
         g_geometry_rejections++;
         WriteDecisionEvent(bar.time,"ATR_INVALID","TERMINAL",
                            g_candidate.direction,g_candidate.level,bar,0.0,
                            0.0,0.0,0.0,next_lag);
         ResetCandidate();
         return;
        }
      double complex_extreme=(g_candidate.direction>0 ?
         MathMin(g_candidate.break_low,MathMin(g_candidate.hold_low,bar.low)) :
         MathMax(g_candidate.break_high,MathMax(g_candidate.hold_high,bar.high)));
      double stop=complex_extreme-g_candidate.direction*InpStopAtrBuffer*atr;
      TradeDecision decision=BuildTradeDecision(g_candidate.direction,bar.time,
                                                g_candidate.level,atr,stop,
                                                next_lag,"ACCEPT_RETEST");
      int direction=g_candidate.direction;
      double level=g_candidate.level;
      g_accept_retest++;
      ResetCandidate();
      WriteDecisionEvent(bar.time,"ACCEPT_RETEST","ENTRY_ATTEMPT",direction,
                         level,bar,atr,0.0,stop,0.0,next_lag);
      TryOpenTrade(decision,bar);
      return;
     }
   if(next_lag>=InpRetestBars)
     {
      g_expire_retest++;
      WriteDecisionEvent(bar.time,"EXPIRE_12","TERMINAL",
                         g_candidate.direction,g_candidate.level,bar,0.0,
                         0.0,0.0,0.0,next_lag);
      ResetCandidate();
      return;
     }
   WriteDecisionEvent(bar.time,"RETEST_WAIT","CONTINUE",
                      g_candidate.direction,g_candidate.level,bar,0.0,
                      0.0,0.0,0.0,next_lag);
  }

bool PositionIdentifierExists(const ulong identifier)
  {
   if(identifier==0)
      return false;
   for(int i=PositionsTotal()-1;i>=0;i--)
     {
      ulong ticket=PositionGetTicket(i);
      if(ticket==0 || !PositionSelectByTicket(ticket))
         continue;
      if((ulong)PositionGetInteger(POSITION_IDENTIFIER)==identifier)
         return true;
     }
   return false;
  }

ENUM_ORDER_TYPE EntryTypeForPosition(const ulong identifier)
  {
   if(!HistorySelect(0,TimeCurrent()))
      return ORDER_TYPE_BUY;
   int total=HistoryDealsTotal();
   for(int i=0;i<total;i++)
     {
      ulong deal=HistoryDealGetTicket(i);
      if(deal==0 ||
         (ulong)HistoryDealGetInteger(deal,DEAL_POSITION_ID)!=identifier)
         continue;
      ENUM_DEAL_ENTRY entry=(ENUM_DEAL_ENTRY)HistoryDealGetInteger(deal,DEAL_ENTRY);
      if(entry==DEAL_ENTRY_IN || entry==DEAL_ENTRY_INOUT)
         return HistoryDealGetInteger(deal,DEAL_TYPE)==DEAL_TYPE_SELL ?
                ORDER_TYPE_SELL : ORDER_TYPE_BUY;
     }
   return ORDER_TYPE_BUY;
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
   ulong position_id=(ulong)HistoryDealGetInteger(deal,DEAL_POSITION_ID);
   bool is_open=(entry==DEAL_ENTRY_IN || entry==DEAL_ENTRY_INOUT);
   bool final_close=(!is_open && !PositionIdentifierExists(position_id));
   ENUM_ORDER_TYPE order_type=EntryTypeForPosition(position_id);
   double profit=HistoryDealGetDouble(deal,DEAL_PROFIT);
   double commission=HistoryDealGetDouble(deal,DEAL_COMMISSION);
   double swap=HistoryDealGetDouble(deal,DEAL_SWAP);
   double fee=HistoryDealGetDouble(deal,DEAL_FEE);
   double net=profit+commission+swap+fee;
   if(is_open)
     {
      order_type=HistoryDealGetInteger(deal,DEAL_TYPE)==DEAL_TYPE_SELL ?
                 ORDER_TYPE_SELL : ORDER_TYPE_BUY;
      if(position_id!=g_position_identifier)
         g_entries_opened++;
      g_position_identifier=position_id;
      g_position_net=0.0;
     }
   g_position_net+=net;
   if(InpEnableTelemetry && g_lifecycle_handle!=INVALID_HANDLE)
     {
      FileWrite(g_lifecycle_handle,
                TimeToString((datetime)HistoryDealGetInteger(deal,DEAL_TIME),
                             TIME_DATE|TIME_SECONDS),
                is_open ? "OPEN" : (final_close ? "CLOSE" : "CLOSE_PARTIAL"),
                order_type==ORDER_TYPE_SELL ? "SELL" : "BUY",
                DoubleToString(HistoryDealGetDouble(deal,DEAL_VOLUME),8),
                DoubleToString(HistoryDealGetDouble(deal,DEAL_PRICE),_Digits),
                _Symbol,StringFormat("%I64u",position_id),
                DoubleToString(MathAbs(g_initial_entry-g_initial_stop)/_Point,8),
                DoubleToString(g_planned_risk_account,8),
                StringFormat("%I64u",deal),DoubleToString(profit,8),
                DoubleToString(commission,8),DoubleToString(swap,8),
                DoubleToString(fee,8),DoubleToString(net,8),
                final_close ? "1" : "0");
      FileFlush(g_lifecycle_handle);
     }
   if(final_close)
     {
      g_position_identifier=0;
      g_initial_entry=0.0;
      g_initial_stop=0.0;
      g_planned_risk_account=0.0;
      g_position_net=0.0;
     }
  }

bool CloseOwnedPosition(const ulong ticket)
  {
   if(ticket==0 || !PositionSelectByTicket(ticket))
      return false;
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick))
      return false;
   ENUM_POSITION_TYPE pos_type=(ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE);
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
   request.type=pos_type==POSITION_TYPE_BUY ? ORDER_TYPE_SELL : ORDER_TYPE_BUY;
   request.price=pos_type==POSITION_TYPE_BUY ? tick.bid : tick.ask;
   request.deviation=(ulong)MathMax(1,MathRound(InpDeviationPips*PipSize()/_Point));
   request.type_filling=FillingMode();
   request.comment="SCC timeout";
   if(!OrderCheck(request,check))
      return false;
   if(!OrderSend(request,result))
      return false;
   return result.retcode==TRADE_RETCODE_DONE ||
          result.retcode==TRADE_RETCODE_DONE_PARTIAL ||
          result.retcode==TRADE_RETCODE_PLACED;
  }

void ManageOwnedPosition()
  {
   ulong ticket=OwnedPositionTicket();
   if(ticket==0 || !PositionSelectByTicket(ticket))
      return;
   datetime opened=(datetime)PositionGetInteger(POSITION_TIME);
   if(TimeCurrent()-opened>=InpMaxHoldBars*PeriodSeconds(PERIOD_M5))
     {
      if(CloseOwnedPosition(ticket))
         g_timeout_closes++;
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
      "\"variant_tag\":\"%s\",\"magic\":%I64d,"
      "\"hold_retest_enabled\":%s,\"promotion_eligible\":false,"
      "\"cost_status\":\"UNVERIFIED_DIAGNOSTIC_ONLY\","
      "\"news_status\":\"DISABLED_MATCHED\","
      "\"source_identity_basis\":\"RUN_MANIFEST_HASH_BOUND\","
      "\"prereg_sha256\":\"%s\",\"parent_plan_sha256\":\"%s\","
      "\"parent_result_sha256\":\"%s\",\"source_data_sha256\":\"%s\","
      "\"diagnostic\":{\"bars_seen\":%I64d,\"confirmed_highs\":%I64d,"
      "\"confirmed_lows\":%I64d,\"break_arms\":%I64d,"
      "\"long_break_arms\":%I64d,\"short_break_arms\":%I64d,"
      "\"ambiguous_breaks\":%I64d,\"hold_pass\":%I64d,"
      "\"reject_hold\":%I64d,\"reject_gap\":%I64d,"
      "\"reject_day_boundary\":%I64d,\"reject_close_inside\":%I64d,"
      "\"accept_retest\":%I64d,\"expire_retest\":%I64d,"
      "\"entries_attempted\":%I64d,\"entries_opened\":%I64d,"
      "\"spread_rejections\":%I64d,\"geometry_rejections\":%I64d,"
      "\"broker_rejections\":%I64d,\"exposure_rejections\":%I64d,"
      "\"timeout_closes\":%I64d}}",
      g_run_id,EA_NAME,_Symbol,TELEMETRY_PROFILE,InpHypothesisId,InpVariantTag,
      InpMagic,InpUseHoldRetest ? "true" : "false",PREREG_SHA256,
      PARENT_PLAN_SHA256,PARENT_RESULT_SHA256,SOURCE_DATA_SHA256,
      g_bars_seen,g_confirmed_highs,g_confirmed_lows,g_break_arms,
      g_long_break_arms,g_short_break_arms,g_ambiguous_breaks,g_hold_pass,
      g_reject_hold,g_reject_gap,g_reject_day_boundary,g_reject_close_inside,
      g_accept_retest,g_expire_retest,g_entries_attempted,g_entries_opened,
      g_spread_rejections,g_geometry_rejections,g_broker_rejections,
      g_exposure_rejections,g_timeout_closes);
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
   FileWrite(g_decision_handle,"server_time","utc_time","variant","stage",
             "event","status","direction","level","open","high","low","close",
             "atr","entry","stop","target","passage_lag","spread_pips");
   FileFlush(g_decision_handle);
   return WriteRunMeta();
  }

bool ValidateInputs()
  {
   if(_Symbol!="EURUSD" || _Period!=PERIOD_M5)
      return false;
   if(!InpResearchAutoMode || !InpEnableTelemetry ||
      InpHypothesisId!="HYP-SCC-MT5-REPLICATION-EURUSD-M5-002" ||
      InpMagic!=5600752)
      return false;
   if(InpUseHoldRetest)
     {
      if(InpVariantTag!="CHALLENGER_HOLD_RETEST")
         return false;
     }
   else
     {
      if(InpVariantTag!="CONTROL_FIRST_CLOSE_BREAK")
         return false;
     }
   if(InpPivotStrength!=2 || InpRetestBars!=12 || InpAtrPeriod!=14 ||
      MathAbs(InpStopAtrBuffer-0.25)>1e-9 ||
      MathAbs(InpTargetR-2.00)>1e-9 || InpMaxHoldBars!=24 ||
      MathAbs(InpRiskPercent-0.05)>1e-9 ||
      MathAbs(InpMaxSpreadPips-2.00)>1e-9 ||
      InpDeviationPips<=0.0 || InpBrokerGMTOffsetWinter!=2 ||
      !InpBrokerFollowsEuropeDST)
      return false;
   return true;
  }

int OnInit()
  {
   if(!ValidateInputs())
      return INIT_PARAMETERS_INCORRECT;
   ZeroMemory(g_pivot_high);
   ZeroMemory(g_pivot_low);
   ResetCandidate();
   g_atr_handle=iATR(_Symbol,PERIOD_M5,InpAtrPeriod);
   if(g_atr_handle==INVALID_HANDLE)
      return INIT_FAILED;
   g_last_m5_bar=iTime(_Symbol,PERIOD_M5,0);
   if(!OpenTelemetry())
      return INIT_FAILED;
   PrintFormat("SCC init hyp=%s variant=%s hold_retest=%s magic=%I64d closed_bar=true promotion=false",
               InpHypothesisId,InpVariantTag,
               InpUseHoldRetest ? "true" : "false",InpMagic);
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
   ManageOwnedPosition();
   datetime current_bar=iTime(_Symbol,PERIOD_M5,0);
   if(current_bar<=0)
      return;
   if(current_bar==g_last_m5_bar)
      return;
   g_last_m5_bar=current_bar;
   g_bars_seen++;

   MqlRates bars[];
   ArraySetAsSeries(bars,true);
   if(CopyRates(_Symbol,PERIOD_M5,1,6,bars)!=6)
      return;
   RefreshConfirmedPivots(bars);

   if(g_candidate.stage==SCC_AWAIT_HOLD)
     {
      ResolveHold(bars[0]);
      return;
     }
   if(g_candidate.stage==SCC_AWAIT_RETEST)
     {
      ResolveRetest(bars[0]);
      return;
     }

   int direction=0;
   double level=0.0;
   if(!DetectBreak(bars,direction,level))
      return;
   double atr=0.0;
   if(!ReadAtrClosed(atr))
      return;
   ArmBreak(bars[0],direction,level,atr);
  }
