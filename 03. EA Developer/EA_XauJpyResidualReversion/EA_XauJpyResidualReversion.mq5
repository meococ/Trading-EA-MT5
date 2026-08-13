//+------------------------------------------------------------------+
//| EA_XauJpyResidualReversion.mq5                                  |
//| HYP-XJRR-XAUUSD-M5-001: XAU/USDJPY residual mean reversion      |
//+------------------------------------------------------------------+
#property strict
#property version   "1.00"
#property description "Untuned XAUUSD M5 residual reversion versus USDJPY"

#include <Trade/Trade.mqh>

input group "--- Frozen research authority ---"
input bool   InpResearchAutoMode=false;
input bool   InpEnableTelemetry=false;
input string InpHypothesisId="HYP-XJRR-XAUUSD-M5-001";
input string InpVariantTag="XAU_USDJPY_RESIDUAL_REENTRY_V1";

input group "--- Frozen execution and risk ---"
input long   InpMagic=5604501;
input double InpRiskPercent=0.25;
input double InpMaxDailyLossPct=3.5;
input double InpMaxAccountDrawdownPct=8.0;
input int    InpDeviationPoints=20;
input int    InpFridayFlattenHourUtc=20;

const string EA_NAME="EA_XauJpyResidualReversion";
const string EXPECTED_HYPOTHESIS="HYP-XJRR-XAUUSD-M5-001";
const string EXPECTED_VARIANT="XAU_USDJPY_RESIDUAL_REENTRY_V1";
const string EXPECTED_SYMBOL="XAUUSD";
const string AUX_SYMBOL="USDJPY";
const int WINDOW=288;
const int INITIAL_HISTORY_BARS=768;
const int MAX_JOINED_BARS=768;
const int LOCKOUT_BARS=12;
const int MAX_HOLD_BARS=12;
const double ENTRY_Z=2.0;
const double STOP_ATR=1.25;
const datetime DESIGN_FROM=D'2018.01.01 00:00';
const datetime DESIGN_TO=D'2023.01.01 00:00';

struct JoinedBar
  {
   datetime time;
   double xau_close;
   double jpy_close;
  };

struct SignalDecision
  {
   bool fired;
   int direction;
   datetime decision_time;
   double beta;
   double sigma;
   double z_prior;
   double z;
  };

struct EntryPlan
  {
   bool valid;
   int direction;
   double entry;
   double stop;
   double volume;
  };

CTrade g_trade;
JoinedBar g_joined[];
int g_atr_handle=INVALID_HANDLE;
datetime g_current_bar_open=0;
datetime g_processed_joined_time=0;
int g_consumed_date=0;
int g_lockout_remaining=0;
int g_design_joined_count=0;
int g_daily_utc_key=0;
double g_daily_start_equity=0.0;
double g_peak_equity=0.0;
bool g_daily_locked=false;
bool g_drawdown_locked=false;
bool g_runtime_failed=false;
long g_closed_design_bars=0;
long g_raw_crosses=0;
long g_consumed_signals=0;
long g_long_signals=0;
long g_short_signals=0;
long g_entries=0;
long g_entry_rejects=0;
long g_closes=0;
long g_exact_next_rejects=0;
long g_overlap_rejects=0;
long g_friday_rejects=0;
long g_stale_rejects=0;
long g_geometry_rejects=0;
long g_risk_lock_rejects=0;
long g_runtime_rejects=0;
long g_reconstructed_consumed=0;
long g_invalid_inputs=0;

bool IsFinite(const double value)
  {
   return(value!=EMPTY_VALUE && MathIsValidNumber(value));
  }

datetime MakeTime(const int year,const int month,const int day,
                  const int hour,const int minute=0,const int second=0)
  {
   MqlDateTime p;
   ZeroMemory(p);
   p.year=year;
   p.mon=month;
   p.day=day;
   p.hour=hour;
   p.min=minute;
   p.sec=second;
   return(StructToTime(p));
  }

int DaysInMonth(const int year,const int month)
  {
   if(month==2)
      return(((year%4==0 && year%100!=0) || year%400==0) ? 29 : 28);
   if(month==4 || month==6 || month==9 || month==11)
      return(30);
   return(31);
  }

int LastSunday(const int year,const int month)
  {
   const int last=DaysInMonth(year,month);
   MqlDateTime p;
   TimeToStruct(MakeTime(year,month,last,0),p);
   return(last-p.day_of_week);
  }

bool IsBrokerDstServerTime(const datetime server_time)
  {
   MqlDateTime p;
   TimeToStruct(server_time,p);
   const datetime start=MakeTime(p.year,3,LastSunday(p.year,3),3);
   const datetime finish=MakeTime(p.year,10,LastSunday(p.year,10),4);
   return(server_time>=start && server_time<finish);
  }

datetime ServerToUtc(const datetime server_time)
  {
   return(server_time-(IsBrokerDstServerTime(server_time) ? 3 : 2)*3600);
  }

int DateKey(const datetime stamp)
  {
   MqlDateTime p;
   TimeToStruct(stamp,p);
   return(p.year*10000+p.mon*100+p.day);
  }

bool FridayBlocked(const datetime availability_server)
  {
   MqlDateTime p;
   TimeToStruct(ServerToUtc(availability_server),p);
   return(p.day_of_week==5 && p.hour>=InpFridayFlattenHourUtc);
  }

bool CurrentBarOpen(const string symbol,datetime &bar_open)
  {
   long raw=0;
   bar_open=0;
   ResetLastError();
   if(!SeriesInfoInteger(symbol,PERIOD_M5,SERIES_LASTBAR_DATE,raw) || raw<=0)
      return(false);
   bar_open=(datetime)raw;
   return(GetLastError()==0);
  }

bool ValidRate(const MqlRates &bar)
  {
   return(bar.time>0 && IsFinite(bar.open) && IsFinite(bar.high) &&
          IsFinite(bar.low) && IsFinite(bar.close) && bar.tick_volume>0 &&
          bar.high>=MathMax(bar.open,bar.close) &&
          bar.low<=MathMin(bar.open,bar.close) && bar.high>=bar.low);
  }

bool ReadSeriesInteger(const ENUM_TIMEFRAMES timeframe,
                       const ENUM_SERIES_INFO_INTEGER property,long &value)
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

bool CopyClosedRates(const string symbol,const int count,MqlRates &rates[])
  {
   ArraySetAsSeries(rates,false);
   const int copied=CopyRates(symbol,PERIOD_M5,1,count,rates);
   if(copied<WINDOW+3)
      return(false);
   for(int i=0;i<copied;i++)
      if(!ValidRate(rates[i]) || (i>0 && rates[i].time<=rates[i-1].time))
         return(false);
   return(true);
  }

bool MergeRates(const MqlRates &xau[],const MqlRates &jpy[],JoinedBar &joined[],
                const int minimum)
  {
   ArrayResize(joined,0);
   int i=0,j=0;
   while(i<ArraySize(xau) && j<ArraySize(jpy))
     {
      if(xau[i].time<jpy[j].time)
        {
         i++;
         continue;
        }
      if(jpy[j].time<xau[i].time)
        {
         j++;
         continue;
        }
      const int n=ArraySize(joined);
      ArrayResize(joined,n+1);
      joined[n].time=xau[i].time;
      joined[n].xau_close=xau[i].close;
      joined[n].jpy_close=jpy[j].close;
      i++;
      j++;
     }
   return(ArraySize(joined)>=minimum);
  }

void TrimJoined()
  {
   const int total=ArraySize(g_joined);
   if(total<=MAX_JOINED_BARS)
      return;
   const int remove=total-MAX_JOINED_BARS;
   for(int i=remove;i<total;i++)
      g_joined[i-remove]=g_joined[i];
   ArrayResize(g_joined,MAX_JOINED_BARS);
  }

bool BuildInitialJoined()
  {
   MqlRates xau[],jpy[];
   if(!CopyClosedRates(_Symbol,INITIAL_HISTORY_BARS,xau) ||
      !CopyClosedRates(AUX_SYMBOL,INITIAL_HISTORY_BARS,jpy))
      return(false);
   if(!MergeRates(xau,jpy,g_joined,WINDOW+3))
      return(false);
   TrimJoined();
   return(ArraySize(g_joined)>=WINDOW+3);
  }

bool AppendClosedRange(const datetime current_open)
  {
   const int existing=ArraySize(g_joined);
   if(existing<=0)
      return(false);
   MqlRates xau[],jpy[];
   ArraySetAsSeries(xau,false);
   ArraySetAsSeries(jpy,false);
   const int cx=CopyRates(_Symbol,PERIOD_M5,1,64,xau);
   const int cj=CopyRates(AUX_SYMBOL,PERIOD_M5,1,64,jpy);
   if(cx<=0 || cj<=0)
      return(false);
   for(int i=0;i<cx;i++)
      if(!ValidRate(xau[i]))
         return(false);
   for(int i=0;i<cj;i++)
      if(!ValidRate(jpy[i]))
         return(false);
   JoinedBar fresh[];
   if(MergeRates(xau,jpy,fresh,1))
     {
      for(int i=0;i<ArraySize(fresh);i++)
        {
         if(fresh[i].time>=current_open)
            continue;
         if(fresh[i].time<=g_joined[ArraySize(g_joined)-1].time)
            continue;
         const int n=ArraySize(g_joined);
         ArrayResize(g_joined,n+1);
         g_joined[n]=fresh[i];
        }
     }
   TrimJoined();
   return(true);
  }

bool ComputeZAt(const int index,double &beta,double &sigma,double &z)
  {
   beta=0.0;
   sigma=0.0;
   z=0.0;
   if(index<WINDOW+1 || index>=ArraySize(g_joined))
      return(false);
   double sx=0.0,sy=0.0,sxx=0.0,syy=0.0,sxy=0.0;
   for(int k=index-WINDOW;k<=index-1;k++)
     {
      if(g_joined[k-1].xau_close<=0.0 || g_joined[k].xau_close<=0.0 ||
         g_joined[k-1].jpy_close<=0.0 || g_joined[k].jpy_close<=0.0)
         return(false);
      const double rx=MathLog(g_joined[k].xau_close/g_joined[k-1].xau_close);
      const double rj=MathLog(g_joined[k].jpy_close/g_joined[k-1].jpy_close);
      if(!IsFinite(rx) || !IsFinite(rj))
         return(false);
      sx+=rx;
      sy+=rj;
      sxx+=rx*rx;
      syy+=rj*rj;
      sxy+=rx*rj;
     }
   if(!IsFinite(syy) || syy<=0.0)
      return(false);
   beta=sxy/syy;
   const double mean=(sx-beta*sy)/WINDOW;
   const double ss=sxx-2.0*beta*sxy+beta*beta*syy-WINDOW*mean*mean;
   const double variance=ss/(WINDOW-1);
   if(!IsFinite(beta) || !IsFinite(variance) || variance<=0.0)
      return(false);
   sigma=MathSqrt(variance);
   const double current_rx=MathLog(g_joined[index].xau_close/g_joined[index-1].xau_close);
   const double current_rj=MathLog(g_joined[index].jpy_close/g_joined[index-1].jpy_close);
   z=(current_rx-beta*current_rj)/sigma;
   return(IsFinite(sigma) && sigma>0.0 && IsFinite(z));
  }

bool RawSignalAt(const int index,SignalDecision &signal)
  {
   ZeroMemory(signal);
   if(index<WINDOW+2)
      return(false);
   double prior_beta=0.0,prior_sigma=0.0,prior_z=0.0;
   double beta=0.0,sigma=0.0,z=0.0;
   if(!ComputeZAt(index-1,prior_beta,prior_sigma,prior_z) ||
      !ComputeZAt(index,beta,sigma,z))
      return(false);
   const bool long_event=(prior_z<=-ENTRY_Z && z>-ENTRY_Z);
   const bool short_event=(prior_z>=ENTRY_Z && z<ENTRY_Z);
   if(long_event==short_event)
      return(false);
   signal.fired=true;
   signal.direction=(long_event ? 1 : -1);
   signal.decision_time=g_joined[index].time;
   signal.beta=beta;
   signal.sigma=sigma;
   signal.z_prior=prior_z;
   signal.z=z;
   return(true);
  }

int FindJoinedTime(const datetime value)
  {
   for(int i=ArraySize(g_joined)-1;i>=0;i--)
      if(g_joined[i].time==value)
         return(i);
   return(-1);
  }

int DesignBarsThrough(const int index)
  {
   int count=0;
   for(int i=0;i<=index;i++)
      if(g_joined[i].time>=DESIGN_FROM && g_joined[i].time<DESIGN_TO)
         count++;
   return(count);
  }

void ReconstructConsumptionState()
  {
   g_consumed_date=0;
   g_lockout_remaining=0;
   const int last=ArraySize(g_joined)-1;
   g_design_joined_count=DesignBarsThrough(last);
   const bool mature_before_window=(last>=0 && g_joined[last].time>=DESIGN_FROM+7*86400);
   int local_design=0;
   for(int i=0;i<=last;i++)
     {
      if(g_joined[i].time<DESIGN_FROM || g_joined[i].time>=DESIGN_TO)
         continue;
      local_design++;
      const bool locked=(g_lockout_remaining>0);
      if(g_lockout_remaining>0)
         g_lockout_remaining--;
      if((local_design<WINDOW+3 && !mature_before_window) || i<WINDOW+2)
         continue;
      SignalDecision signal;
      if(!RawSignalAt(i,signal))
         continue;
      const int date_key=DateKey(signal.decision_time);
      if(locked || g_consumed_date==date_key)
         continue;
      g_consumed_date=date_key;
      g_lockout_remaining=LOCKOUT_BARS;
      g_reconstructed_consumed++;
     }
   if(last>=0)
      g_processed_joined_time=g_joined[last].time;
  }

ulong OwnedPositionTicket()
  {
   ulong found=0;
   for(int i=PositionsTotal()-1;i>=0;i--)
     {
      const ulong ticket=PositionGetTicket(i);
      if(ticket==0 || !PositionSelectByTicket(ticket))
         continue;
      if(PositionGetString(POSITION_SYMBOL)!=_Symbol ||
         PositionGetInteger(POSITION_MAGIC)!=InpMagic)
         continue;
      if(found!=0)
        {
         g_runtime_failed=true;
         return(found);
        }
      found=ticket;
     }
   return(found);
  }

bool AcceptedRetcode()
  {
   const uint code=g_trade.ResultRetcode();
   return(code==TRADE_RETCODE_DONE || code==TRADE_RETCODE_DONE_PARTIAL);
  }

bool CloseOwned(const string reason)
  {
   const ulong ticket=OwnedPositionTicket();
   if(ticket==0)
      return(true);
   if(!g_trade.PositionClose(ticket) || !AcceptedRetcode())
     {
      PrintFormat("XJRR_CLOSE_REJECT reason=%s retcode=%u",reason,g_trade.ResultRetcode());
      return(false);
     }
   g_closes++;
   return(true);
  }

void UpdateRiskAnchors(const datetime server_now)
  {
   const double equity=AccountInfoDouble(ACCOUNT_EQUITY);
   if(!IsFinite(equity) || equity<=0.0)
     {
      g_runtime_failed=true;
      return;
     }
   const int utc_key=DateKey(ServerToUtc(server_now));
   if(g_daily_utc_key!=utc_key)
     {
      g_daily_utc_key=utc_key;
      g_daily_start_equity=equity;
      g_daily_locked=false;
     }
   if(g_peak_equity<=0.0 || equity>g_peak_equity)
      g_peak_equity=equity;
   if(g_daily_start_equity>0.0 && equity<=g_daily_start_equity*(1.0-InpMaxDailyLossPct/100.0))
      g_daily_locked=true;
   if(g_peak_equity>0.0 && equity<=g_peak_equity*(1.0-InpMaxAccountDrawdownPct/100.0))
      g_drawdown_locked=true;
  }

double NormalizeStop(const int direction,const double raw_stop,const double tick_size)
  {
   if(direction>0)
      return(MathFloor(raw_stop/tick_size)*tick_size);
   return(MathCeil(raw_stop/tick_size)*tick_size);
  }

bool ReadClosedAtr(double &atr)
  {
   atr=0.0;
   double values[];
   ArraySetAsSeries(values,false);
   if(g_atr_handle==INVALID_HANDLE || CopyBuffer(g_atr_handle,0,1,1,values)!=1)
      return(false);
   atr=values[0];
   return(IsFinite(atr) && atr>0.0);
  }

bool BuildEntryPlan(const int direction,EntryPlan &plan)
  {
   ZeroMemory(plan);
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick) || tick.ask<=0.0 || tick.bid<=0.0)
      return(false);
   double atr=0.0;
   if(!ReadClosedAtr(atr))
      return(false);
   const double tick_size=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);
   const double point=SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   const double volume_min=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN);
   const double volume_max=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX);
   const double volume_step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);
   if(tick_size<=0.0 || point<=0.0 || volume_min<=0.0 || volume_max<volume_min || volume_step<=0.0)
      return(false);
   const double entry=(direction>0 ? tick.ask : tick.bid);
   const double raw_stop=entry-direction*STOP_ATR*atr;
   const double stop=NormalizeStop(direction,raw_stop,tick_size);
   const int stops_level=(int)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL);
   if((direction>0 && stop>=tick.bid-stops_level*point) ||
      (direction<0 && stop<=tick.ask+stops_level*point))
      return(false);
   double loss_one_lot=0.0;
   const ENUM_ORDER_TYPE type=(direction>0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL);
   if(!OrderCalcProfit(type,_Symbol,1.0,entry,stop,loss_one_lot) ||
      !IsFinite(loss_one_lot) || loss_one_lot>=0.0)
      return(false);
   const double risk_cash=AccountInfoDouble(ACCOUNT_EQUITY)*InpRiskPercent/100.0;
   double volume=MathFloor((risk_cash/MathAbs(loss_one_lot))/volume_step+1e-12)*volume_step;
   volume=MathMin(volume,volume_max);
   if(volume<volume_min)
      return(false);
   double margin=0.0;
   if(!OrderCalcMargin(type,_Symbol,volume,entry,margin) || !IsFinite(margin) ||
      margin>AccountInfoDouble(ACCOUNT_MARGIN_FREE))
      return(false);
   plan.valid=true;
   plan.direction=direction;
   plan.entry=entry;
   plan.stop=stop;
   plan.volume=volume;
   return(true);
  }

bool SubmitEntry(const EntryPlan &plan)
  {
   if(!plan.valid || OwnedPositionTicket()!=0)
      return(false);
   bool sent=false;
   if(plan.direction>0)
      sent=g_trade.Buy(plan.volume,_Symbol,0.0,plan.stop,0.0,"XJRR_LONG");
   else
      sent=g_trade.Sell(plan.volume,_Symbol,0.0,plan.stop,0.0,"XJRR_SHORT");
   if(!sent || !AcceptedRetcode())
     {
      PrintFormat("XJRR_ENTRY_REJECT direction=%d volume=%.2f stop=%.5f retcode=%u",
                  plan.direction,plan.volume,plan.stop,g_trade.ResultRetcode());
      return(false);
     }
   if(OwnedPositionTicket()==0)
     {
      g_runtime_failed=true;
      return(false);
     }
   g_entries++;
   return(true);
  }

void ManageOpenPosition(const datetime current_open,const double current_z)
  {
   const ulong ticket=OwnedPositionTicket();
   if(ticket==0 || !PositionSelectByTicket(ticket))
      return;
   const long type=PositionGetInteger(POSITION_TYPE);
   const datetime entry_time=(datetime)PositionGetInteger(POSITION_TIME);
   const int shift=iBarShift(_Symbol,PERIOD_M5,entry_time,false);
   const bool residual_exit=(type==POSITION_TYPE_BUY ? current_z>=0.0 : current_z<=0.0);
   const bool time_exit=(shift>=MAX_HOLD_BARS);
   if(current_open>=DESIGN_TO)
      CloseOwned("DESIGN_END");
   else if(FridayBlocked(current_open))
      CloseOwned("FRIDAY_FLATTEN");
   else if(residual_exit)
      CloseOwned("RESIDUAL_ZERO");
   else if(time_exit)
      CloseOwned("MAX_HOLD");
  }

bool ProcessDecisionIndex(const int index,const bool latest,const datetime current_open,
                          const bool position_at_tick_start,SignalDecision &candidate)
  {
   ZeroMemory(candidate);
   const datetime decision_time=g_joined[index].time;
   if(decision_time<DESIGN_FROM || decision_time>=DESIGN_TO)
      return(true);
   g_design_joined_count++;
   g_closed_design_bars++;
   const bool locked=(g_lockout_remaining>0);
   if(g_lockout_remaining>0)
      g_lockout_remaining--;
   if(g_design_joined_count<WINDOW+3 || index<WINDOW+2)
      return(true);
   SignalDecision signal;
   if(!RawSignalAt(index,signal))
      return(true);
   g_raw_crosses++;
   const int date_key=DateKey(signal.decision_time);
   if(locked || g_consumed_date==date_key)
      return(true);
   g_consumed_date=date_key;
   g_lockout_remaining=LOCKOUT_BARS;
   g_consumed_signals++;
   if(signal.direction>0)
      g_long_signals++;
   else
      g_short_signals++;
   if(!latest)
     {
      g_stale_rejects++;
      return(true);
     }
   datetime aux_current=0;
   const bool exact_next=(current_open==signal.decision_time+300 &&
                          CurrentBarOpen(AUX_SYMBOL,aux_current) && aux_current==current_open);
   if(!exact_next)
     {
      g_exact_next_rejects++;
      return(true);
     }
   if(FridayBlocked(current_open))
     {
      g_friday_rejects++;
      return(true);
     }
   if(position_at_tick_start || OwnedPositionTicket()!=0)
     {
      g_overlap_rejects++;
      return(true);
     }
   candidate=signal;
   return(true);
  }

bool ProcessNewClosedBars(const datetime current_open)
  {
   if(!AppendClosedRange(current_open))
      return(false);
   const int total=ArraySize(g_joined);
   if(total<WINDOW+3)
      return(false);
   int first=0;
   if(g_processed_joined_time>0)
     {
      const int previous=FindJoinedTime(g_processed_joined_time);
      if(previous<0)
         return(false);
      first=previous+1;
     }
   if(first>=total)
      return(true);
   const bool position_at_tick_start=(OwnedPositionTicket()!=0);
   SignalDecision latest_candidate;
   ZeroMemory(latest_candidate);
   for(int i=first;i<total;i++)
     {
      SignalDecision candidate;
      if(!ProcessDecisionIndex(i,i==total-1,current_open,position_at_tick_start,candidate))
         return(false);
      if(candidate.fired)
         latest_candidate=candidate;
     }
   g_processed_joined_time=g_joined[total-1].time;
   double beta=0.0,sigma=0.0,current_z=0.0;
   if(!ComputeZAt(total-1,beta,sigma,current_z))
      return(false);
   if(position_at_tick_start)
      ManageOpenPosition(current_open,current_z);
   if(latest_candidate.fired && !position_at_tick_start)
     {
      if(g_runtime_failed)
         g_runtime_rejects++;
      else if(g_daily_locked || g_drawdown_locked)
         g_risk_lock_rejects++;
      else
        {
         EntryPlan plan;
         if(!BuildEntryPlan(latest_candidate.direction,plan))
           {
            g_geometry_rejects++;
            g_entry_rejects++;
           }
         else if(!SubmitEntry(plan))
            g_entry_rejects++;
        }
     }
   return(true);
  }

int OnInit()
  {
   if(_Symbol!=EXPECTED_SYMBOL || _Period!=PERIOD_M5 ||
      InpHypothesisId!=EXPECTED_HYPOTHESIS || InpVariantTag!=EXPECTED_VARIANT ||
      InpMagic!=5604501 || MathAbs(InpRiskPercent-0.25)>1e-12 ||
      MathAbs(InpMaxDailyLossPct-3.5)>1e-12 ||
      MathAbs(InpMaxAccountDrawdownPct-8.0)>1e-12 ||
      InpDeviationPoints!=20 || InpFridayFlattenHourUtc!=20 || InpEnableTelemetry)
     {
      g_runtime_failed=true;
      return(INIT_PARAMETERS_INCORRECT);
     }
   if(!SymbolSelect(AUX_SYMBOL,true))
     {
      g_runtime_failed=true;
      return(INIT_FAILED);
     }
   g_trade.SetExpertMagicNumber(InpMagic);
   g_trade.SetDeviationInPoints(InpDeviationPoints);
   g_trade.SetAsyncMode(false);
   g_trade.SetTypeFillingBySymbol(_Symbol);
   g_atr_handle=iATR(_Symbol,PERIOD_M5,14);
   if(g_atr_handle==INVALID_HANDLE || !EmitD0SeriesProof() || !BuildInitialJoined())
     {
      g_runtime_failed=true;
      return(INIT_FAILED);
     }
   datetime aux_open=0;
   if(!CurrentBarOpen(_Symbol,g_current_bar_open) ||
      !CurrentBarOpen(AUX_SYMBOL,aux_open))
     {
      g_runtime_failed=true;
      return(INIT_FAILED);
     }
   ReconstructConsumptionState();
   UpdateRiskAnchors(g_current_bar_open);
   PrintFormat("XJRR_INIT hyp=%s variant=%s aux=%s joined=%d current=%I64d aux_current=%I64d audit_only=false",
               InpHypothesisId,InpVariantTag,AUX_SYMBOL,ArraySize(g_joined),
               (long)g_current_bar_open,(long)aux_open);
   return(INIT_SUCCEEDED);
  }

void OnTick()
  {
   datetime current_open=0;
   if(!CurrentBarOpen(_Symbol,current_open))
     {
      g_runtime_failed=true;
      return;
     }
   UpdateRiskAnchors(current_open);
   if(OwnedPositionTicket()!=0 && (FridayBlocked(current_open) || current_open>=DESIGN_TO))
      CloseOwned(current_open>=DESIGN_TO ? "DESIGN_END_TICK" : "FRIDAY_TICK");
   if(current_open==g_current_bar_open)
      return;
   g_current_bar_open=current_open;
   if(!ProcessNewClosedBars(current_open))
     {
      g_invalid_inputs++;
      g_runtime_failed=true;
     }
  }

void OnDeinit(const int reason)
  {
   if(g_atr_handle!=INVALID_HANDLE)
      IndicatorRelease(g_atr_handle);
   PrintFormat("XJRR_SUMMARY hyp=%s variant=%s reason=%d closed=%I64d raw_crosses=%I64d consumed=%I64d long=%I64d short=%I64d entries=%I64d entry_rejects=%I64d closes=%I64d exact_next_rejects=%I64d overlap_rejects=%I64d friday_rejects=%I64d stale_rejects=%I64d geometry_rejects=%I64d risk_lock_rejects=%I64d runtime_rejects=%I64d reconstructed_consumed=%I64d invalid=%I64d runtime_failed=%s",
               InpHypothesisId,InpVariantTag,reason,g_closed_design_bars,
               g_raw_crosses,g_consumed_signals,g_long_signals,g_short_signals,
               g_entries,g_entry_rejects,g_closes,g_exact_next_rejects,
               g_overlap_rejects,g_friday_rejects,g_stale_rejects,
               g_geometry_rejects,g_risk_lock_rejects,g_runtime_rejects,
               g_reconstructed_consumed,g_invalid_inputs,
               (g_runtime_failed ? "true" : "false"));
  }
//+------------------------------------------------------------------+
