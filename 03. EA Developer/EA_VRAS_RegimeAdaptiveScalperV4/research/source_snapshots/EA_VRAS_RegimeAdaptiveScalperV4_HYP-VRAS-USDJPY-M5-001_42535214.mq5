#property strict
#property version   "4.00"
#property description "USDJPY M5 closed-bar Asian OU research EA; synchronous and tester-only"

enum ENUM_VRAS_SIGNAL
  {
   VRAS_SIGNAL_NONE=0,
   VRAS_SIGNAL_OU_LONG=1,
   VRAS_SIGNAL_OU_SHORT=-1
  };

input bool   InpResearchAutoMode=false;
input bool   InpEnableTelemetry=true;
input string InpHypothesisId="HYP-VRAS-USDJPY-M5-001";
input string InpVariantTag="PRIMARY_USDJPY_ASIAN_OU";
input long   InpMagic=5601601;
input int    InpDirectionMultiplier=1;

input int    InpOuWindow=72;
input int    InpVarianceRatioQ=5;
input double InpMaxVarianceRatio=1.00;
input double InpMinHalfLifeBars=1.0;
input double InpMaxHalfLifeBars=36.0;
input double InpEntryZ=2.0;
input double InpExitAbsZ=0.25;
input double InpTailStopZ=4.0;
input int    InpAtrPeriod=14;
input double InpMinStopAtr=1.5;
input double InpMinRewardRisk=1.5;

input double InpRiskPercent=0.25;
input double InpMaxSpreadPips=1.20;
input double InpCommissionPips=0.70;
input double InpSlippageOneWayPips=0.30;
input double InpCostDistanceMultiple=3.0;
input int    InpMaxTradesPerDay=3;
input double InpDailySoftStopPct=2.0;
input double InpDailyHardStopPct=3.5;
input double InpMaxAccountDrawdownPct=8.0;
input int    InpMaxHoldBars=18;
input int    InpBrokerGMTOffsetWinter=2;
input bool   InpBrokerFollowsEuropeDST=true;

const string EA_NAME="EA_VRAS_RegimeAdaptiveScalperV4";
const string TELEMETRY_PROFILE="lifecycle-v3";
const string SOURCE_DATA_SHA256="FECD42A01AFD14D4149121A122468DA5597939A20DD1533A36DA711E6FA2DAFD";
const string CLOCK_CONTRACT="FIVEPERCENT_SERVER_UTC_PLUS2_EU_DST_PLUS3";
const string STRATEGY_COMMENT="VRASU001";

struct OuState
  {
   bool valid;
   datetime decision_server;
   datetime decision_utc;
   double close1;
   double a;
   double b;
   double mu;
   double sigma_eq;
   double half_life;
   double variance_ratio;
   double z;
   double atr;
   int primary_direction;
   string event_code;
  };

datetime g_last_m5_bar=0;
int g_atr_handle=INVALID_HANDLE;

int g_day_key=0;
double g_day_start_equity=0.0;
double g_peak_equity=0.0;
int g_trades_today=0;
bool g_daily_hard_latch=false;
bool g_account_hard_latch=false;
bool g_persistence_fault=false;
bool g_confirmed_fill_breach=false;
bool g_run_persistence_fault_seen=false;
bool g_run_confirmed_fill_breach_seen=false;

ulong g_position_identifier=0;
double g_worst_entry_bound=0.0;
double g_initial_stop=0.0;
double g_planned_risk_account=0.0;
double g_planned_volume=0.0;
double g_planned_risk_per_lot=0.0;
double g_stop_risk_per_lot=0.0;
double g_position_net=0.0;
datetime g_entry_bar_open=0;
ulong g_pending_lifecycle_exit_deals[];
int g_pending_lifecycle_quiet_ticks=0;

int g_lifecycle_handle=INVALID_HANDLE;
int g_decision_handle=INVALID_HANDLE;
string g_run_id="";
string g_lifecycle_name="";
string g_decision_name="";
string g_run_meta_name="";

long g_bars_seen=0;
long g_estimator_rejections=0;
long g_session_rejections=0;
long g_spread_rejections=0;
long g_cost_rejections=0;
long g_geometry_rejections=0;
long g_risk_rejections=0;
long g_entries_attempted=0;
long g_entries_opened=0;
long g_mean_exits=0;
long g_time_exits=0;
long g_risk_exits=0;

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
   MqlDateTime value;
   ZeroMemory(value);
   value.year=year;
   value.mon=month;
   value.day=day;
   value.hour=hour;
   value.min=minute;
   return StructToTime(value);
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

int UtcMinutes(const datetime utc_time)
  {
   MqlDateTime parts;
   TimeToStruct(utc_time,parts);
   return parts.hour*60+parts.min;
  }

bool EntrySessionAllows(const datetime utc_time)
  {
   MqlDateTime parts;
   TimeToStruct(utc_time,parts);
   int minute=parts.hour*60+parts.min;
   if(minute<22*60+15 && minute>=5*60+30)
      return false;
   if(!WrappingSessionDayAllows(utc_time))
      return false;
   if(minute>=21*60+55 && minute<22*60+15)
      return false;
   return minute>=22*60+15 || minute<5*60+30;
  }

int WrappingSessionKey(const datetime utc_time)
  {
   MqlDateTime parts;
   TimeToStruct(utc_time+105*60,parts);
   return parts.year*10000+parts.mon*100+parts.day;
  }

bool WrappingSessionDayAllows(const datetime utc_time)
  {
   MqlDateTime parts;
   TimeToStruct(utc_time+105*60,parts);
   return parts.day_of_week>=1 && parts.day_of_week<=5;
  }

bool MustFlattenForClock(const datetime utc_time)
  {
   MqlDateTime parts;
   TimeToStruct(utc_time,parts);
   int minute=parts.hour*60+parts.min;
   if(!WrappingSessionDayAllows(utc_time))
      return true;
   return !(minute>=22*60+15 || minute<5*60+30);
  }

string RiskKey(const string suffix)
  {
   long login=AccountInfoInteger(ACCOUNT_LOGIN);
   return StringFormat("V4.%I64d.%I64d.%s",login,InpMagic,suffix);
  }

bool PersistRiskState()
  {
   bool ok=true;
   if(GlobalVariableSet(RiskKey("DAY"),(double)g_day_key)==0) ok=false;
   if(GlobalVariableSet(RiskKey("DEQ"),g_day_start_equity)==0) ok=false;
   if(GlobalVariableSet(RiskKey("PEQ"),g_peak_equity)==0) ok=false;
   if(GlobalVariableSet(RiskKey("TRD"),(double)g_trades_today)==0) ok=false;
   if(GlobalVariableSet(RiskKey("DHL"),g_daily_hard_latch ? 1.0 : 0.0)==0) ok=false;
   if(GlobalVariableSet(RiskKey("AHL"),g_account_hard_latch ? 1.0 : 0.0)==0) ok=false;
   GlobalVariablesFlush();
   if(ok)
     {
      ok=GlobalVariableCheck(RiskKey("DAY")) &&
         GlobalVariableCheck(RiskKey("DEQ")) &&
         GlobalVariableCheck(RiskKey("PEQ")) &&
         GlobalVariableCheck(RiskKey("TRD")) &&
         GlobalVariableCheck(RiskKey("DHL")) &&
         GlobalVariableCheck(RiskKey("AHL")) &&
         (int)GlobalVariableGet(RiskKey("DAY"))==g_day_key &&
         GlobalVariableGet(RiskKey("DEQ"))==g_day_start_equity &&
         GlobalVariableGet(RiskKey("PEQ"))==g_peak_equity &&
         (int)GlobalVariableGet(RiskKey("TRD"))==g_trades_today &&
         (GlobalVariableGet(RiskKey("DHL"))>0.5)==g_daily_hard_latch &&
         (GlobalVariableGet(RiskKey("AHL"))>0.5)==g_account_hard_latch;
     }
   if(!ok)
     {
       g_persistence_fault=true;
       g_run_persistence_fault_seen=true;
       g_account_hard_latch=true;
      GlobalVariableSet(RiskKey("AHL"),1.0);
      GlobalVariablesFlush();
     }
   return ok;
  }

bool LoadRiskState(const datetime server_time)
  {
   int current_key=UtcDateKey(server_time);
   double equity=AccountInfoDouble(ACCOUNT_EQUITY);
   bool has_day=GlobalVariableCheck(RiskKey("DAY"));
   int stored_key=has_day ? (int)GlobalVariableGet(RiskKey("DAY")) : 0;
   if(!has_day || stored_key>current_key)
     {
      g_day_key=current_key;
      g_day_start_equity=equity;
      g_peak_equity=equity;
      g_trades_today=0;
      g_daily_hard_latch=false;
      g_account_hard_latch=false;
      return PersistRiskState();
     }
   g_peak_equity=GlobalVariableCheck(RiskKey("PEQ")) ?
                 GlobalVariableGet(RiskKey("PEQ")) : equity;
   g_account_hard_latch=GlobalVariableCheck(RiskKey("AHL")) &&
                        GlobalVariableGet(RiskKey("AHL"))>0.5;
   if(stored_key!=current_key)
     {
      g_day_key=current_key;
      g_day_start_equity=equity;
      g_trades_today=0;
      g_daily_hard_latch=false;
     }
   else
     {
      g_day_key=stored_key;
      g_day_start_equity=GlobalVariableCheck(RiskKey("DEQ")) ?
                         GlobalVariableGet(RiskKey("DEQ")) : equity;
      g_trades_today=GlobalVariableCheck(RiskKey("TRD")) ?
                     (int)GlobalVariableGet(RiskKey("TRD")) : 0;
      g_daily_hard_latch=GlobalVariableCheck(RiskKey("DHL")) &&
                         GlobalVariableGet(RiskKey("DHL"))>0.5;
     }
   if(g_peak_equity<=0.0)
      g_peak_equity=equity;
   return PersistRiskState();
  }

void RefreshRiskState(const datetime server_time)
  {
   int key=UtcDateKey(server_time);
   if(key!=g_day_key)
     {
      g_day_key=key;
      g_day_start_equity=AccountInfoDouble(ACCOUNT_EQUITY);
      g_trades_today=0;
      g_daily_hard_latch=false;
     }
   double equity=AccountInfoDouble(ACCOUNT_EQUITY);
   if(equity>g_peak_equity)
      g_peak_equity=equity;
   if(g_day_start_equity>0.0 &&
      equity<=g_day_start_equity*(1.0-InpDailyHardStopPct/100.0))
      g_daily_hard_latch=true;
   if(g_peak_equity>0.0 &&
      equity<=g_peak_equity*(1.0-InpMaxAccountDrawdownPct/100.0))
      g_account_hard_latch=true;
   PersistRiskState();
  }

bool DailySoftStopHit()
  {
   double equity=AccountInfoDouble(ACCOUNT_EQUITY);
   return g_day_start_equity>0.0 &&
          equity<=g_day_start_equity*(1.0-InpDailySoftStopPct/100.0);
  }

bool ComputeOuState(const datetime decision_server,OuState &state)
  {
   ZeroMemory(state);
   state.decision_server=decision_server;
   state.decision_utc=ServerToUtc(decision_server);
   state.event_code="ESTIMATOR_REJECT";

   double closes[];
   datetime bar_times[];
   ArraySetAsSeries(closes,true);
   ArraySetAsSeries(bar_times,true);
   if(CopyClose(_Symbol,PERIOD_M5,1,InpOuWindow,closes)!=InpOuWindow)
      return false;
   if(CopyTime(_Symbol,PERIOD_M5,1,InpOuWindow,bar_times)!=InpOuWindow)
      return false;
   int decision_session_key=WrappingSessionKey(state.decision_utc);
   for(int i=0;i<InpOuWindow;i++)
     {
      datetime bar_utc=ServerToUtc(bar_times[i]);
      if(closes[i]<=0.0 || !MathIsValidNumber(closes[i]) ||
         !EntrySessionAllows(bar_utc) ||
         WrappingSessionKey(bar_utc)!=decision_session_key)
         return false;
      if(i+1<InpOuWindow &&
         bar_times[i]-bar_times[i+1]!=PeriodSeconds(PERIOD_M5))
         return false;
     }

   int n=InpOuWindow-1;
   double sx=0.0,sy=0.0,sxx=0.0,sxy=0.0;
   for(int i=InpOuWindow-1;i>=1;i--)
     {
      double x=closes[i];
      double y=closes[i-1];
      sx+=x;
      sy+=y;
      sxx+=x*x;
      sxy+=x*y;
     }
   double denominator=n*sxx-sx*sx;
   if(MathAbs(denominator)<=1e-18)
      return false;
   state.b=(n*sxy-sx*sy)/denominator;
   state.a=(sy-state.b*sx)/n;
   if(!MathIsValidNumber(state.a) || !MathIsValidNumber(state.b) ||
      state.b<=0.0 || state.b>=1.0-1e-12)
      return false;
   state.mu=state.a/(1.0-state.b);
   double residual_sum=0.0;
   for(int i=InpOuWindow-1;i>=1;i--)
     {
      double residual=closes[i-1]-(state.a+state.b*closes[i]);
      residual_sum+=residual*residual;
     }
   double residual_sd=MathSqrt(residual_sum/n);
   double eq_denominator=1.0-state.b*state.b;
   if(eq_denominator<=0.0 || residual_sd<=0.0)
      return false;
   state.sigma_eq=residual_sd/MathSqrt(eq_denominator);
   state.half_life=-MathLog(2.0)/MathLog(state.b);
   if(!MathIsValidNumber(state.mu) || !MathIsValidNumber(state.sigma_eq) ||
      !MathIsValidNumber(state.half_life) || state.sigma_eq<=0.0 ||
      state.half_life<InpMinHalfLifeBars || state.half_life>InpMaxHalfLifeBars)
      return false;

   double returns[];
   ArrayResize(returns,n);
   int index=0;
   for(int i=InpOuWindow-1;i>=1;i--)
      returns[index++]=MathLog(closes[i-1]/closes[i]);
   double mean=0.0;
   for(int i=0;i<n;i++)
      mean+=returns[i];
   mean/=n;
   double var1=0.0;
   for(int i=0;i<n;i++)
      var1+=(returns[i]-mean)*(returns[i]-mean);
   var1/=(n-1);
   int q_count=n-InpVarianceRatioQ+1;
   if(var1<=0.0 || q_count<2)
      return false;
   double q_returns[];
   ArrayResize(q_returns,q_count);
   double q_mean=0.0;
   for(int i=0;i<q_count;i++)
     {
      double value=0.0;
      for(int j=0;j<InpVarianceRatioQ;j++)
         value+=returns[i+j];
      q_returns[i]=value;
      q_mean+=value;
     }
   q_mean/=q_count;
   double q_var=0.0;
   for(int i=0;i<q_count;i++)
      q_var+=(q_returns[i]-q_mean)*(q_returns[i]-q_mean);
   q_var/=(q_count-1);
   state.variance_ratio=(q_var/InpVarianceRatioQ)/var1;
   if(!MathIsValidNumber(state.variance_ratio) ||
      state.variance_ratio>=InpMaxVarianceRatio)
      return false;

   double atr_buffer[1];
   if(CopyBuffer(g_atr_handle,0,1,1,atr_buffer)!=1 || atr_buffer[0]<=0.0)
      return false;
   state.atr=atr_buffer[0];
   state.close1=closes[0];
   state.z=(state.close1-state.mu)/state.sigma_eq;
   state.primary_direction=0;
   if(state.z<=-InpEntryZ)
      state.primary_direction=1;
   else if(state.z>=InpEntryZ)
      state.primary_direction=-1;
   state.event_code=state.primary_direction>0 ? "OU_LONG" :
                    (state.primary_direction<0 ? "OU_SHORT" : "NO_Z_ENTRY");
   state.valid=true;
   return true;
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
   for(int i=OrdersTotal()-1;i>=0;i--)
     {
      ulong ticket=OrderGetTicket(i);
      if(ticket==0)
         return true;
      if(OrderGetString(ORDER_SYMBOL)==_Symbol)
         return true;
     }
   return false;
  }

ENUM_ORDER_TYPE_FILLING FillingMode()
  {
   long filling=0;
   if(!SymbolInfoInteger(_Symbol,SYMBOL_FILLING_MODE,filling))
      return ORDER_FILLING_FOK;
   if((filling & SYMBOL_FILLING_IOC)==SYMBOL_FILLING_IOC)
      return ORDER_FILLING_IOC;
   return ORDER_FILLING_FOK;
  }

double NormalizeVolumeDown(const double raw)
  {
   double minimum=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN);
   double maximum=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX);
   double step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);
   if(minimum<=0.0 || maximum<minimum || step<=0.0)
      return 0.0;
   double volume=MathFloor((MathMin(raw,maximum)+1e-12)/step)*step;
   if(volume<minimum)
      return 0.0;
   return NormalizeDouble(volume,8);
  }

double AverageLastTenEntryLots()
  {
   if(!HistorySelect(0,TimeCurrent()))
      return 0.0;
   int total=HistoryDealsTotal();
   int count=0;
   double sum=0.0;
   for(int i=total-1;i>=0 && count<10;i--)
     {
      ulong deal=HistoryDealGetTicket(i);
      if(deal==0 || HistoryDealGetString(deal,DEAL_SYMBOL)!=_Symbol ||
         (long)HistoryDealGetInteger(deal,DEAL_MAGIC)!=InpMagic ||
         (ENUM_DEAL_ENTRY)HistoryDealGetInteger(deal,DEAL_ENTRY)!=DEAL_ENTRY_IN)
         continue;
      double volume=HistoryDealGetDouble(deal,DEAL_VOLUME);
      if(volume<=0.0)
         continue;
      sum+=volume;
      count++;
     }
   return count==10 ? sum/10.0 : 0.0;
  }

double ClampLotConsistency(const double requested)
  {
   double average=AverageLastTenEntryLots();
   if(average<=0.0)
      return requested;
   return MathMin(MathMax(requested,0.5*average),1.5*average);
  }

double RiskSizedVolume(const int direction,const double entry,const double stop,
                       double &planned_risk_account,double &stop_risk_per_lot)
  {
   planned_risk_account=0.0;
   stop_risk_per_lot=0.0;
   double budget=AccountInfoDouble(ACCOUNT_EQUITY)*InpRiskPercent/100.0;
   if(budget<=0.0)
      return 0.0;
   ENUM_ORDER_TYPE type=direction>0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
   double stop_loss=0.0;
   if(!OrderCalcProfit(type,_Symbol,1.0,entry,stop,stop_loss))
      return 0.0;
   // The supplied entry is already shifted to the adverse entry-slippage
   // bound. Only round-trip commission plus the remaining exit-slippage leg
   // belongs in the post-fill risk allowance.
   double remaining_cost_pips=InpCommissionPips+InpSlippageOneWayPips;
   double cost_close=entry-direction*remaining_cost_pips*PipSize();
   double cost_loss=0.0;
   if(!OrderCalcProfit(type,_Symbol,1.0,entry,cost_close,cost_loss))
      return 0.0;
   double loss_per_lot=MathAbs(stop_loss)+MathAbs(cost_loss);
   if(loss_per_lot<=0.0 || !MathIsValidNumber(loss_per_lot))
      return 0.0;
   double volume=NormalizeVolumeDown(ClampLotConsistency(budget/loss_per_lot));
   if(volume<=0.0)
      return 0.0;
   planned_risk_account=loss_per_lot*volume;
   stop_risk_per_lot=MathAbs(stop_loss);
   if(planned_risk_account>budget*(1.0+1e-8))
      return 0.0;
   return volume;
  }

double NormalizePrice(const double price)
  {
   double tick_size=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);
   if(tick_size<=0.0)
      tick_size=_Point;
   return NormalizeDouble(MathRound(price/tick_size)*tick_size,_Digits);
  }

bool BuildGeometry(const OuState &state,const int final_direction,
                   const double entry,double &stop,double &target)
  {
   int primary=state.primary_direction;
   if(primary==0 || final_direction!=primary*InpDirectionMultiplier)
      return false;
   double primary_stop=0.0;
   double primary_target=state.mu;
   if(primary>0)
      primary_stop=MathMin(state.mu-InpTailStopZ*state.sigma_eq,
                           entry-InpMinStopAtr*state.atr);
   else
      primary_stop=MathMax(state.mu+InpTailStopZ*state.sigma_eq,
                           entry+InpMinStopAtr*state.atr);
   double risk=MathAbs(entry-primary_stop);
   double reward=MathAbs(primary_target-entry);
   if(risk<=0.0 || reward<=0.0 || primary*(primary_target-entry)<=0.0)
      return false;
   if(InpDirectionMultiplier==1)
     {
      stop=primary_stop;
      target=primary_target;
     }
   else
     {
      stop=entry-final_direction*risk;
      target=entry+final_direction*reward;
     }
   stop=NormalizePrice(stop);
   target=NormalizePrice(target);
   risk=MathAbs(entry-stop);
   reward=MathAbs(target-entry);
   return final_direction*(entry-stop)>0.0 &&
          final_direction*(target-entry)>0.0 &&
          reward/risk>=InpMinRewardRisk;
  }

void WriteDecision(const OuState &state,const string status,const double entry=0.0,
                   const double stop=0.0,const double target=0.0,
                   const double estimated_cost=0.0)
  {
   if(!InpEnableTelemetry || g_decision_handle==INVALID_HANDLE)
      return;
   FileWrite(g_decision_handle,
             TimeToString(state.decision_server,TIME_DATE|TIME_SECONDS),
             TimeToString(state.decision_utc,TIME_DATE|TIME_SECONDS),
             InpVariantTag,state.event_code,status,
             DoubleToString(state.close1,_Digits),DoubleToString(state.a,10),
             DoubleToString(state.b,10),DoubleToString(state.mu,_Digits),
             DoubleToString(state.sigma_eq,10),DoubleToString(state.half_life,6),
             DoubleToString(state.variance_ratio,8),DoubleToString(state.z,8),
             DoubleToString(state.atr,_Digits),IntegerToString(state.primary_direction),
             IntegerToString(state.primary_direction*InpDirectionMultiplier),
             DoubleToString(entry,_Digits),DoubleToString(stop,_Digits),
             DoubleToString(target,_Digits),DoubleToString(estimated_cost,6),
             DoubleToString((SymbolInfoDouble(_Symbol,SYMBOL_ASK)-
                             SymbolInfoDouble(_Symbol,SYMBOL_BID))/PipSize(),6));
   FileFlush(g_decision_handle);
  }

bool TryOpenTrade(const OuState &state)
  {
   g_entries_attempted++;
   RefreshRiskState(state.decision_server);
   if(!InpResearchAutoMode || !MQLInfoInteger(MQL_TESTER) ||
      !EntrySessionAllows(state.decision_utc))
     {
      g_session_rejections++;
      WriteDecision(state,"ENTRY_SESSION_OR_MODE_REJECT");
      return false;
     }
   if(g_trades_today>=InpMaxTradesPerDay || DailySoftStopHit() ||
       g_daily_hard_latch || g_account_hard_latch || g_persistence_fault ||
       ArraySize(g_pending_lifecycle_exit_deals)>0 || AnySymbolExposure())
     {
      g_risk_rejections++;
      WriteDecision(state,"ENTRY_RISK_REJECT");
      return false;
     }
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick))
      return false;
   double spread=(tick.ask-tick.bid)/PipSize();
   if(spread<=0.0 || spread>InpMaxSpreadPips || AnySymbolExposure())
     {
      g_spread_rejections++;
      WriteDecision(state,"ENTRY_SPREAD_REJECT");
      return false;
     }
   int direction=state.primary_direction*InpDirectionMultiplier;
   double entry=direction>0 ? tick.ask : tick.bid;
   double geometry_entry=entry+direction*InpSlippageOneWayPips*PipSize();
   double stop=0.0,target=0.0;
   if(!BuildGeometry(state,direction,geometry_entry,stop,target))
     {
      g_geometry_rejections++;
      WriteDecision(state,"ENTRY_GEOMETRY_REJECT",entry,stop,target);
      return false;
     }
   long stops_level=0,freeze_level=0;
   if(!SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL,stops_level) ||
      !SymbolInfoInteger(_Symbol,SYMBOL_TRADE_FREEZE_LEVEL,freeze_level))
      return false;
   double minimum_distance=MathMax((double)stops_level,(double)freeze_level)*_Point;
   if(MathAbs(geometry_entry-stop)<minimum_distance ||
      MathAbs(target-geometry_entry)<minimum_distance)
     {
      g_geometry_rejections++;
      WriteDecision(state,"ENTRY_BROKER_DISTANCE_REJECT",entry,stop,target);
      return false;
     }
   double estimated_cost=spread+InpCommissionPips+2.0*InpSlippageOneWayPips;
   double target_pips=direction*(target-geometry_entry)/PipSize();
   if(estimated_cost<=0.0 || target_pips<InpCostDistanceMultiple*estimated_cost)
     {
      g_cost_rejections++;
      WriteDecision(state,"ENTRY_COST_DISTANCE_REJECT",entry,stop,target,estimated_cost);
      return false;
     }
   double risk_account=0.0;
   double stop_risk_per_lot=0.0;
   double volume=RiskSizedVolume(direction,geometry_entry,stop,risk_account,stop_risk_per_lot);
   if(volume<=0.0 || risk_account<=0.0)
     {
      g_risk_rejections++;
      WriteDecision(state,"ENTRY_SIZING_REJECT",entry,stop,target,estimated_cost);
      return false;
     }

   MqlTradeRequest request;
   MqlTradeCheckResult check;
   MqlTradeResult result;
   ZeroMemory(request);
   ZeroMemory(check);
   ZeroMemory(result);
   request.action=TRADE_ACTION_DEAL;
   request.symbol=_Symbol;
   request.magic=(ulong)InpMagic;
   request.volume=volume;
   request.type=direction>0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
   request.price=entry;
   request.sl=stop;
   request.tp=target;
   request.deviation=(ulong)MathMax(1,MathRound(InpSlippageOneWayPips*PipSize()/_Point));
   request.type_filling=FillingMode();
   request.type_time=ORDER_TIME_GTC;
   request.comment=STRATEGY_COMMENT;
   if(!OrderCheck(request,check) || check.retcode!=0)
     {
      g_risk_rejections++;
      WriteDecision(state,"ENTRY_ORDER_CHECK_REJECT",entry,stop,target,estimated_cost);
      return false;
     }
   // OrderSend is synchronous, but its deal callback may be delivered before this
   // function returns. Bind the frozen entry risk first so lifecycle telemetry
   // cannot observe zero or stale geometry.
   g_worst_entry_bound=geometry_entry;
   g_initial_stop=stop;
   g_planned_risk_account=risk_account;
   g_planned_volume=volume;
   g_planned_risk_per_lot=risk_account/volume;
   g_stop_risk_per_lot=stop_risk_per_lot;
   g_entry_bar_open=state.decision_server;
   g_confirmed_fill_breach=false;
   if(!OrderSend(request,result) ||
      (result.retcode!=TRADE_RETCODE_DONE &&
       result.retcode!=TRADE_RETCODE_DONE_PARTIAL &&
       result.retcode!=TRADE_RETCODE_PLACED))
     {
      g_worst_entry_bound=0.0;
      g_initial_stop=0.0;
      g_planned_risk_account=0.0;
      g_planned_volume=0.0;
      g_planned_risk_per_lot=0.0;
      g_stop_risk_per_lot=0.0;
      g_entry_bar_open=0;
      WriteDecision(state,"ENTRY_ORDER_SEND_REJECT",entry,stop,target,estimated_cost);
      return false;
     }
   WriteDecision(state,"ENTRY_ACCEPTED",entry,stop,target,estimated_cost);
   return true;
  }

bool PositionIdentifierExists(const ulong identifier)
  {
   for(int i=0;i<PositionsTotal();i++)
     {
      ulong ticket=PositionGetTicket(i);
      if(ticket>0 && (ulong)PositionGetInteger(POSITION_IDENTIFIER)==identifier)
         return true;
     }
   return false;
  }

ENUM_ORDER_TYPE EntryTypeForPosition(const ulong identifier)
  {
   if(HistorySelectByPosition(identifier))
     {
      int total=HistoryDealsTotal();
      for(int i=0;i<total;i++)
        {
         ulong deal=HistoryDealGetTicket(i);
         if(deal==0)
            continue;
         ENUM_DEAL_ENTRY entry=(ENUM_DEAL_ENTRY)HistoryDealGetInteger(deal,DEAL_ENTRY);
         if(entry==DEAL_ENTRY_IN || entry==DEAL_ENTRY_INOUT)
            return HistoryDealGetInteger(deal,DEAL_TYPE)==DEAL_TYPE_SELL ?
                   ORDER_TYPE_SELL : ORDER_TYPE_BUY;
        }
     }
   return ORDER_TYPE_BUY;
  }

void QueueLifecycleExitDeal(const ulong deal)
  {
   if(deal==0)
      return;
   int count=ArraySize(g_pending_lifecycle_exit_deals);
   for(int i=0;i<count;i++)
      if(g_pending_lifecycle_exit_deals[i]==deal)
         return;
   ArrayResize(g_pending_lifecycle_exit_deals,count+1);
   g_pending_lifecycle_exit_deals[count]=deal;
   g_pending_lifecycle_quiet_ticks=0;
  }

int ExitFinalDisposition(const ulong deal,const ulong position_id)
  {
   if(PositionIdentifierExists(position_id))
      return 0;
   if(!HistorySelectByPosition(position_id))
      return -1;
   int total=HistoryDealsTotal();
   double entry_volume=0.0;
   double exit_volume=0.0;
   ulong latest_exit_deal=0;
   long latest_exit_msc=-1;
   for(int i=0;i<total;i++)
     {
      ulong candidate=HistoryDealGetTicket(i);
      if(candidate==0 || HistoryDealGetString(candidate,DEAL_SYMBOL)!=_Symbol ||
         (long)HistoryDealGetInteger(candidate,DEAL_MAGIC)!=InpMagic)
         continue;
      ENUM_DEAL_ENTRY candidate_entry=(ENUM_DEAL_ENTRY)HistoryDealGetInteger(candidate,DEAL_ENTRY);
      double volume=HistoryDealGetDouble(candidate,DEAL_VOLUME);
      if(candidate_entry==DEAL_ENTRY_IN || candidate_entry==DEAL_ENTRY_INOUT)
         entry_volume+=volume;
      else if(candidate_entry==DEAL_ENTRY_OUT || candidate_entry==DEAL_ENTRY_OUT_BY)
        {
         exit_volume+=volume;
         long time_msc=(long)HistoryDealGetInteger(candidate,DEAL_TIME_MSC);
         if(time_msc>latest_exit_msc ||
            (time_msc==latest_exit_msc && candidate>latest_exit_deal))
           {
            latest_exit_msc=time_msc;
            latest_exit_deal=candidate;
           }
        }
     }
   double volume_step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);
   if(volume_step<=0.0)
      volume_step=1e-8;
   if(entry_volume<=0.0 || latest_exit_deal==0 ||
      exit_volume+0.5*volume_step<entry_volume)
      return -1;
   return deal==latest_exit_deal ? 1 : 0;
  }

void LogLifecycleDeal(const ulong deal,const bool final_close)
  {
   if(!HistoryDealSelect(deal) || HistoryDealGetString(deal,DEAL_SYMBOL)!=_Symbol ||
      (long)HistoryDealGetInteger(deal,DEAL_MAGIC)!=InpMagic)
      return;
   ENUM_DEAL_ENTRY entry=(ENUM_DEAL_ENTRY)HistoryDealGetInteger(deal,DEAL_ENTRY);
   if(entry!=DEAL_ENTRY_IN && entry!=DEAL_ENTRY_INOUT &&
      entry!=DEAL_ENTRY_OUT && entry!=DEAL_ENTRY_OUT_BY)
      return;
   ulong position_id=(ulong)HistoryDealGetInteger(deal,DEAL_POSITION_ID);
   bool is_open=(entry==DEAL_ENTRY_IN || entry==DEAL_ENTRY_INOUT);
   ENUM_ORDER_TYPE order_type=EntryTypeForPosition(position_id);
   double profit=HistoryDealGetDouble(deal,DEAL_PROFIT);
   double commission=HistoryDealGetDouble(deal,DEAL_COMMISSION);
   double swap=HistoryDealGetDouble(deal,DEAL_SWAP);
   double fee=HistoryDealGetDouble(deal,DEAL_FEE);
   double net=profit+commission+swap+fee;
   double deal_volume=HistoryDealGetDouble(deal,DEAL_VOLUME);
   double deal_initial_risk=0.0;
   if(is_open)
      deal_initial_risk=g_stop_risk_per_lot*deal_volume;
   if(is_open && position_id!=g_position_identifier)
     {
      g_position_identifier=position_id;
      g_position_net=0.0;
      g_entries_opened++;
      g_trades_today++;
      PersistRiskState();
     }
   g_position_net+=net;
   if(InpEnableTelemetry && g_lifecycle_handle!=INVALID_HANDLE)
     {
      FileWrite(g_lifecycle_handle,
                TimeToString((datetime)HistoryDealGetInteger(deal,DEAL_TIME),TIME_DATE|TIME_SECONDS),
                is_open ? "OPEN" : (final_close ? "CLOSE" : "CLOSE_PARTIAL"),
                order_type==ORDER_TYPE_SELL ? "SELL" : "BUY",
                 DoubleToString(deal_volume,8),
                 DoubleToString(HistoryDealGetDouble(deal,DEAL_PRICE),_Digits),
                 _Symbol,StringFormat("%I64u",position_id),
                 DoubleToString(MathAbs(g_worst_entry_bound-g_initial_stop)/_Point,8),
                 DoubleToString(deal_initial_risk,8),StringFormat("%I64u",deal),
                DoubleToString(profit,8),DoubleToString(commission,8),
                DoubleToString(swap,8),DoubleToString(fee,8),DoubleToString(net,8),
                final_close ? "1" : "0");
      FileFlush(g_lifecycle_handle);
     }
   if(final_close && position_id==g_position_identifier)
     {
      g_position_identifier=0;
      g_worst_entry_bound=0.0;
      g_initial_stop=0.0;
      g_planned_risk_account=0.0;
      g_planned_volume=0.0;
      g_planned_risk_per_lot=0.0;
      g_stop_risk_per_lot=0.0;
      g_position_net=0.0;
      g_entry_bar_open=0;
      g_confirmed_fill_breach=false;
     }
  }

void ReconcileLifecycleEntryDeal(const ulong deal)
  {
   if(!HistoryDealSelect(deal))
     {
      QueueLifecycleExitDeal(deal);
      return;
     }
   if(HistoryDealGetString(deal,DEAL_SYMBOL)!=_Symbol ||
      (long)HistoryDealGetInteger(deal,DEAL_MAGIC)!=InpMagic)
      return;
   ENUM_DEAL_ENTRY entry=(ENUM_DEAL_ENTRY)HistoryDealGetInteger(deal,DEAL_ENTRY);
   if(entry!=DEAL_ENTRY_IN && entry!=DEAL_ENTRY_INOUT)
      return;
   double confirmed_price=HistoryDealGetDouble(deal,DEAL_PRICE);
   ENUM_DEAL_TYPE deal_type=(ENUM_DEAL_TYPE)HistoryDealGetInteger(deal,DEAL_TYPE);
   int direction=deal_type==DEAL_TYPE_SELL ? -1 : 1;
   if(g_worst_entry_bound>0.0 && confirmed_price>0.0 &&
      direction*(confirmed_price-g_worst_entry_bound)>0.5*_Point)
     {
      g_confirmed_fill_breach=true;
      g_run_confirmed_fill_breach_seen=true;
     }
   if(g_entry_bar_open<=0)
     {
      datetime deal_time=(datetime)HistoryDealGetInteger(deal,DEAL_TIME);
      g_entry_bar_open=deal_time-(deal_time%PeriodSeconds(PERIOD_M5));
     }
   LogLifecycleDeal(deal,false);
  }

void FlushPendingLifecycleDeals(const bool force)
  {
   int count=ArraySize(g_pending_lifecycle_exit_deals);
   if(count==0)
      return;
   if(!force && g_pending_lifecycle_quiet_ticks<1)
     {
      g_pending_lifecycle_quiet_ticks++;
      return;
     }
   ulong batch[];
   ArrayCopy(batch,g_pending_lifecycle_exit_deals);
   ArrayResize(g_pending_lifecycle_exit_deals,0);
   g_pending_lifecycle_quiet_ticks=0;
   for(int i=0;i<count-1;i++)
      for(int j=i+1;j<count;j++)
        {
         long left_time=(long)HistoryDealGetInteger(batch[i],DEAL_TIME_MSC);
         long right_time=(long)HistoryDealGetInteger(batch[j],DEAL_TIME_MSC);
         if(right_time<left_time ||
            (right_time==left_time && batch[j]<batch[i]))
           {
            ulong swap=batch[i];
            batch[i]=batch[j];
            batch[j]=swap;
           }
        }
   for(int i=0;i<count;i++)
     {
      ulong deal=batch[i];
      if(!HistoryDealSelect(deal))
        {
         QueueLifecycleExitDeal(deal);
         continue;
        }
      if(HistoryDealGetString(deal,DEAL_SYMBOL)!=_Symbol ||
         (long)HistoryDealGetInteger(deal,DEAL_MAGIC)!=InpMagic)
         continue;
       ENUM_DEAL_ENTRY entry=(ENUM_DEAL_ENTRY)HistoryDealGetInteger(deal,DEAL_ENTRY);
       if(entry==DEAL_ENTRY_IN || entry==DEAL_ENTRY_INOUT)
         {
          ReconcileLifecycleEntryDeal(deal);
          continue;
         }
      if(entry!=DEAL_ENTRY_OUT && entry!=DEAL_ENTRY_OUT_BY)
         continue;
      ulong position_id=(ulong)HistoryDealGetInteger(deal,DEAL_POSITION_ID);
      int disposition=ExitFinalDisposition(deal,position_id);
      if(disposition<0)
        {
         QueueLifecycleExitDeal(deal);
         continue;
        }
      LogLifecycleDeal(deal,disposition==1);
     }
  }

bool CloseOwnedPosition(const ulong ticket,const string reason)
  {
   if(ticket==0 || !PositionSelectByTicket(ticket))
      return false;
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick))
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
   request.symbol=_Symbol;
   request.magic=(ulong)InpMagic;
   request.volume=PositionGetDouble(POSITION_VOLUME);
   request.type=position_type==POSITION_TYPE_BUY ? ORDER_TYPE_SELL : ORDER_TYPE_BUY;
   request.price=position_type==POSITION_TYPE_BUY ? tick.bid : tick.ask;
   request.deviation=(ulong)MathMax(1,MathRound(InpSlippageOneWayPips*PipSize()/_Point));
   request.type_filling=FillingMode();
   request.comment=StringSubstr(reason,0,16);
   if(!OrderCheck(request,check) || check.retcode!=0)
      return false;
   if(!OrderSend(request,result))
      return false;
   return result.retcode==TRADE_RETCODE_DONE ||
          result.retcode==TRADE_RETCODE_DONE_PARTIAL ||
          result.retcode==TRADE_RETCODE_PLACED;
  }

void EnforceTickRisk()
  {
   RefreshRiskState(TimeCurrent());
   if(!g_daily_hard_latch && !g_account_hard_latch &&
      !g_persistence_fault && !g_confirmed_fill_breach)
      return;
   ulong ticket=OwnedPositionTicket();
   if(ticket>0 && CloseOwnedPosition(ticket,"VRAS risk cut"))
      g_risk_exits++;
  }

bool ManageMandatoryClosedBar(const datetime current_bar)
  {
   ulong ticket=OwnedPositionTicket();
   if(ticket==0 || !PositionSelectByTicket(ticket))
      return false;
   datetime opened=(datetime)PositionGetInteger(POSITION_TIME);
   datetime entry_bar_open=g_entry_bar_open;
   if(entry_bar_open<=0)
      entry_bar_open=opened-(opened%PeriodSeconds(PERIOD_M5));
   bool time_exit=MustFlattenForClock(ServerToUtc(current_bar)) ||
                  current_bar-entry_bar_open>=InpMaxHoldBars*PeriodSeconds(PERIOD_M5);
   if(!time_exit)
      return false;
   if(CloseOwnedPosition(ticket,"VRAS time exit"))
      g_time_exits++;
   // Suppress estimator/entry work on this bar even when the close request was
   // rejected; the next tick risk loop can retry without opening new exposure.
   return true;
  }

void ManageClosedBar(const OuState &state)
  {
   ulong ticket=OwnedPositionTicket();
   if(ticket==0 || !PositionSelectByTicket(ticket))
      return;
   int position_direction=(ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_BUY ? 1 : -1;
   int primary_direction=position_direction*InpDirectionMultiplier;
   bool mean_exit=state.valid &&
                  (MathAbs(state.z)<=InpExitAbsZ ||
                   (primary_direction>0 && state.z>=0.0) ||
                   (primary_direction<0 && state.z<=0.0));
   if(mean_exit && CloseOwnedPosition(ticket,"VRAS mean exit"))
      g_mean_exits++;
  }

bool WriteRunMeta()
  {
   if(!InpEnableTelemetry || g_run_meta_name=="")
      return true;
   int handle=FileOpen(g_run_meta_name,FILE_WRITE|FILE_TXT|FILE_ANSI);
   if(handle==INVALID_HANDLE)
      return false;
   string payload=StringFormat(
      "{\"schema_version\":\"alphafactory_run_meta.v1\",\"run_id\":\"%s\","+
      "\"ea_name\":\"%s\",\"symbol\":\"%s\",\"telemetry_profile\":\"%s\","+
      "\"hypothesis_id\":\"%s\",\"variant_tag\":\"%s\",\"magic\":%I64d,"+
      "\"direction_multiplier\":%d,\"promotion_eligible\":false,"+
      "\"source_data_sha256\":\"%s\",\"clock_contract\":\"%s\","+
      "\"cost_status\":\"UNVERIFIED_DIAGNOSTIC\",\"news_status\":\"UNMET_OFF\","+
      "\"diagnostic\":{\"bars_seen\":%I64d,\"estimator_rejections\":%I64d,"+
      "\"session_rejections\":%I64d,\"spread_rejections\":%I64d,"+
      "\"cost_rejections\":%I64d,\"geometry_rejections\":%I64d,"+
      "\"risk_rejections\":%I64d,\"entries_attempted\":%I64d,"+
       "\"entries_opened\":%I64d,\"mean_exits\":%I64d,"+
       "\"time_exits\":%I64d,\"risk_exits\":%I64d,"+
       "\"persistence_fault\":%s,\"confirmed_fill_breach\":%s,"+
       "\"pending_lifecycle_exit_deals\":%d,"+
       "\"pending_lifecycle_reconciliation_complete\":%s}}",
      g_run_id,EA_NAME,_Symbol,TELEMETRY_PROFILE,InpHypothesisId,InpVariantTag,
      InpMagic,InpDirectionMultiplier,SOURCE_DATA_SHA256,CLOCK_CONTRACT,
      g_bars_seen,g_estimator_rejections,g_session_rejections,g_spread_rejections,
      g_cost_rejections,g_geometry_rejections,g_risk_rejections,
       g_entries_attempted,g_entries_opened,g_mean_exits,g_time_exits,g_risk_exits,
       g_run_persistence_fault_seen ? "true" : "false",
       g_run_confirmed_fill_breach_seen ? "true" : "false",
       ArraySize(g_pending_lifecycle_exit_deals),
       ArraySize(g_pending_lifecycle_exit_deals)==0 ? "true" : "false");
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
   g_decision_name=StringFormat("%s_DecisionTelemetry_%s.csv",_Symbol,g_run_id);
   g_run_meta_name=StringFormat("%s_RunMeta_%s.json",_Symbol,g_run_id);
   g_lifecycle_handle=FileOpen(g_lifecycle_name,FILE_WRITE|FILE_CSV|FILE_ANSI,',');
   if(g_lifecycle_handle==INVALID_HANDLE)
      return false;
   FileWrite(g_lifecycle_handle,"event_time","action","order_type","volume","price",
             "symbol","position_id","risk_pts","initial_risk_account","deal",
             "deal_profit","deal_commission","deal_swap","deal_fee","deal_net",
             "is_final_close");
   FileFlush(g_lifecycle_handle);
   g_decision_handle=FileOpen(g_decision_name,FILE_WRITE|FILE_CSV|FILE_ANSI,',');
   if(g_decision_handle==INVALID_HANDLE)
      return false;
   FileWrite(g_decision_handle,"server_time","utc_time","variant","event","status",
             "close1","a","b","mu","sigma_eq","half_life","variance_ratio_q5",
             "z","atr","primary_direction","final_direction","entry","stop",
             "target","estimated_cost_pips","spread_pips");
   FileFlush(g_decision_handle);
   return WriteRunMeta();
  }

bool ValidateInputs()
  {
   if(_Symbol!="USDJPY" || _Period!=PERIOD_M5)
      return false;
   if(InpHypothesisId!="HYP-VRAS-USDJPY-M5-001" || InpMagic!=5601601 ||
      (InpDirectionMultiplier!=1 && InpDirectionMultiplier!=-1))
      return false;
   if(InpVariantTag=="" || InpOuWindow!=72 || InpVarianceRatioQ!=5 ||
      InpMaxVarianceRatio!=1.0 || InpMinHalfLifeBars!=1.0 ||
      InpMaxHalfLifeBars!=36.0 || InpEntryZ!=2.0 || InpExitAbsZ!=0.25 ||
      InpTailStopZ!=4.0 || InpAtrPeriod!=14 || InpMinStopAtr!=1.5 ||
      InpMinRewardRisk!=1.5 || InpRiskPercent!=0.25 ||
      InpMaxSpreadPips!=1.20 || InpCommissionPips!=0.70 ||
      InpSlippageOneWayPips!=0.30 || InpCostDistanceMultiple!=3.0 ||
      InpMaxTradesPerDay!=3 || InpDailySoftStopPct!=2.0 ||
      InpDailyHardStopPct!=3.5 || InpMaxAccountDrawdownPct!=8.0 ||
      InpMaxHoldBars!=18 || InpBrokerGMTOffsetWinter!=2 ||
      !InpBrokerFollowsEuropeDST)
      return false;
   return true;
  }

int OnInit()
  {
   if(!ValidateInputs())
      return INIT_PARAMETERS_INCORRECT;
   g_atr_handle=iATR(_Symbol,PERIOD_M5,InpAtrPeriod);
   if(g_atr_handle==INVALID_HANDLE)
      return INIT_FAILED;
   // The first tick only arms the new-bar gate; no mid-bar decision is allowed.
   g_last_m5_bar=0;
   if(!LoadRiskState(TimeCurrent()))
      return INIT_FAILED;
   if(!OpenTelemetry())
      return INIT_FAILED;
   PrintFormat("VRAS V4 init hyp=%s variant=%s direction=%d auto=%s closed_bar=true async=false promotion=false",
               InpHypothesisId,InpVariantTag,InpDirectionMultiplier,
               InpResearchAutoMode ? "true" : "false");
   return INIT_SUCCEEDED;
  }

void OnDeinit(const int reason)
  {
   FlushPendingLifecycleDeals(true);
   WriteRunMeta();
   PersistRiskState();
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
   if(trans.type!=TRADE_TRANSACTION_DEAL_ADD || trans.deal==0)
      return;
   if(!HistoryDealSelect(trans.deal))
     {
      QueueLifecycleExitDeal(trans.deal);
      return;
     }
   ENUM_DEAL_ENTRY entry=(ENUM_DEAL_ENTRY)HistoryDealGetInteger(trans.deal,DEAL_ENTRY);
   if(entry==DEAL_ENTRY_IN || entry==DEAL_ENTRY_INOUT)
      ReconcileLifecycleEntryDeal(trans.deal);
   else if(entry==DEAL_ENTRY_OUT || entry==DEAL_ENTRY_OUT_BY)
      QueueLifecycleExitDeal(trans.deal);
  }

void OnTick()
  {
   FlushPendingLifecycleDeals(false);
   EnforceTickRisk();
   datetime current_bar=iTime(_Symbol,PERIOD_M5,0);
   if(current_bar<=0)
      return;
   if(g_last_m5_bar==0)
     {
      g_last_m5_bar=current_bar;
      return;
     }
   if(current_bar==g_last_m5_bar)
      return;
   g_last_m5_bar=current_bar;
   g_bars_seen++;
   if(ManageMandatoryClosedBar(current_bar))
      return;
   OuState state;
   bool estimator_ok=ComputeOuState(current_bar,state);
   if(!estimator_ok)
     {
      g_estimator_rejections++;
      return;
     }
   ManageClosedBar(state);
   if(OwnedPositionTicket()>0 || state.primary_direction==0)
      return;
   TryOpenTrade(state);
  }
