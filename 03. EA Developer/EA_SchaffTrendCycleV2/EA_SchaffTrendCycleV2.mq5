//+------------------------------------------------------------------+
//| EA_SchaffTrendCycleV2.mq5                                         |
//| HYP-STC-EURUSD-M15-002: classic STC trend-cycle continuation    |
//+------------------------------------------------------------------+
#property strict
#property version   "2.00"
#property description "Untuned EURUSD M15 Schaff Trend Cycle continuation baseline; preload readiness revision"

input group "--- Frozen research authority ---"
input bool   InpResearchAutoMode=false;
input bool   InpEnableTelemetry=false;
input string InpHypothesisId="HYP-STC-EURUSD-M15-002";
input string InpVariantTag="STC_CLASSIC_TREND_CYCLE_V2_PRELOAD_READY";

input group "--- Frozen execution and risk ---"
input long   InpMagic=5603702;
input double InpRiskPercent=0.25;
input double InpMaxDailyLossPct=3.5;
input double InpMaxAccountDrawdownPct=8.0;
input int    InpMaxTradesPerDay=1;
input int    InpDeviationPoints=20;
input int    InpMaxHoldBars=16;
input int    InpFridayFlattenHour=20;

const string EA_NAME="EA_SchaffTrendCycleV2";
const string EXPECTED_HYPOTHESIS="HYP-STC-EURUSD-M15-002";
const string EXPECTED_VARIANT="STC_CLASSIC_TREND_CYCLE_V2_PRELOAD_READY";
const string EXPECTED_SYMBOL="EURUSD";

const int    STC_FAST_EMA=23;
const int    STC_SLOW_EMA=50;
const int    STC_CYCLE=10;
const int    STC_D1=3;
const int    STC_D2=3;
const double STC_LOWER=25.0;
const double STC_UPPER=75.0;
const int    STC_MIN_BARS=160;
const int    ATR_PERIOD=14;
const double STOP_ATR_MULTIPLIER=1.50;
const double TARGET_R=1.50;

const datetime STC_PRELOAD_FIRST=D'2015.01.02 09:00';
const datetime STC_PRELOAD_LAST=D'2015.12.31 20:00';
const int      STC_PRELOAD_BARS=24776;
const datetime DESIGN_FROM=D'2016.01.04 00:00';
const datetime DESIGN_TO=D'2021.01.01 00:00';

struct SignalDecision
  {
   bool fired;
   datetime decision_time;
   datetime availability_time;
   int direction;
   double previous_stc;
   double current_stc;
   double current_macd;
   double atr;
  };

datetime g_last_bar_open=0;
datetime g_last_decision_time=0;
int g_consumed_signal_date=0;

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

bool g_indicator_seeded=false;
datetime g_indicator_bar_time=0;
double g_previous_close=EMPTY_VALUE;
double g_ema_fast=EMPTY_VALUE;
double g_ema_slow=EMPTY_VALUE;
double g_macd_window[10];
int g_macd_count=0;
double g_d1_window[10];
int g_d1_count=0;
double g_last_k1=50.0;
double g_last_d1=EMPTY_VALUE;
double g_last_k2=50.0;
double g_previous_stc=EMPTY_VALUE;
double g_current_stc=EMPTY_VALUE;
double g_current_macd=EMPTY_VALUE;
double g_current_atr=EMPTY_VALUE;
double g_atr_seed_sum=0.0;
int g_atr_count=0;

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

double EmaStep(const double prior,const double value,const int length)
  {
   const double alpha=2.0/((double)length+1.0);
   return(prior+alpha*(value-prior));
  }

void ResetIndicatorState()
  {
   g_indicator_seeded=false;
   g_indicator_bar_time=0;
   g_previous_close=EMPTY_VALUE;
   g_ema_fast=EMPTY_VALUE;
   g_ema_slow=EMPTY_VALUE;
   ArrayInitialize(g_macd_window,0.0);
   g_macd_count=0;
   ArrayInitialize(g_d1_window,0.0);
   g_d1_count=0;
   g_last_k1=50.0;
   g_last_d1=EMPTY_VALUE;
   g_last_k2=50.0;
   g_previous_stc=EMPTY_VALUE;
   g_current_stc=EMPTY_VALUE;
   g_current_macd=EMPTY_VALUE;
   g_current_atr=EMPTY_VALUE;
   g_atr_seed_sum=0.0;
   g_atr_count=0;
  }

void PushWindow(double &values[],int &count,const double value)
  {
   if(count<STC_CYCLE)
     {
      values[count]=value;
      count++;
      return;
     }
   for(int i=1;i<STC_CYCLE;i++)
      values[i-1]=values[i];
   values[STC_CYCLE-1]=value;
  }

bool WindowRange(const double &values[],const int count,
                 double &lowest,double &highest)
  {
   if(count!=STC_CYCLE)
      return(false);
   lowest=DBL_MAX;
   highest=-DBL_MAX;
   for(int i=0;i<STC_CYCLE;i++)
     {
      if(!IsUsable(values[i]))
         return(false);
      lowest=MathMin(lowest,values[i]);
      highest=MathMax(highest,values[i]);
     }
   return(IsUsable(lowest) && IsUsable(highest));
  }

bool AdvanceIndicatorState(const MqlRates &bar)
  {
   if(!ValidRate(bar) || bar.time<=g_indicator_bar_time)
      return(false);

   double tr=0.0;
   if(!g_indicator_seeded)
     {
      g_ema_fast=bar.close;
      g_ema_slow=bar.close;
      tr=bar.high-bar.low;
      g_indicator_seeded=true;
     }
   else
     {
      g_ema_fast=EmaStep(g_ema_fast,bar.close,STC_FAST_EMA);
      g_ema_slow=EmaStep(g_ema_slow,bar.close,STC_SLOW_EMA);
      tr=MathMax(bar.high-bar.low,
                 MathMax(MathAbs(bar.high-g_previous_close),
                         MathAbs(bar.low-g_previous_close)));
     }
   if(!IsUsable(tr) || tr<0.0)
      return(false);

   g_previous_close=bar.close;
   g_indicator_bar_time=bar.time;
   g_current_macd=g_ema_fast-g_ema_slow;

   if(g_atr_count<ATR_PERIOD)
     {
      g_atr_seed_sum+=tr;
      g_atr_count++;
      if(g_atr_count==ATR_PERIOD)
         g_current_atr=g_atr_seed_sum/(double)ATR_PERIOD;
     }
   else
      g_current_atr=((double)(ATR_PERIOD-1)*g_current_atr+tr)/(double)ATR_PERIOD;

   PushWindow(g_macd_window,g_macd_count,g_current_macd);
   double low=0.0;
   double high=0.0;
   if(WindowRange(g_macd_window,g_macd_count,low,high))
     {
      const double span=high-low;
      const double raw=(span>1e-14 ? 100.0*(g_current_macd-low)/span : g_last_k1);
      g_last_k1=MathMax(0.0,MathMin(100.0,raw));
      if(!IsUsable(g_last_d1))
         g_last_d1=g_last_k1;
      else
         g_last_d1=EmaStep(g_last_d1,g_last_k1,STC_D1);
      PushWindow(g_d1_window,g_d1_count,g_last_d1);
     }

   if(WindowRange(g_d1_window,g_d1_count,low,high))
     {
      const double span=high-low;
      const double raw=(span>1e-14 ? 100.0*(g_last_d1-low)/span : g_last_k2);
      g_last_k2=MathMax(0.0,MathMin(100.0,raw));
      const double next_stc=(!IsUsable(g_current_stc) ? g_last_k2
                              : EmaStep(g_current_stc,g_last_k2,STC_D2));
      g_previous_stc=g_current_stc;
      g_current_stc=next_stc;
     }
   return(true);
  }

bool PreloadIndicatorState()
  {
   const datetime last_closed=iTime(_Symbol,PERIOD_M15,1);
   if(last_closed!=STC_PRELOAD_LAST)
     {
      PrintFormat("STC002_PRELOAD_FAIL stage=last_closed actual=%I64d expected=%I64d error=%d",
                  (long)last_closed,(long)STC_PRELOAD_LAST,GetLastError());
      return(false);
     }
   ResetLastError();
   const int preload_count=Bars(_Symbol,PERIOD_M15,STC_PRELOAD_FIRST,last_closed);
   const int bars_error=GetLastError();
   if(preload_count!=STC_PRELOAD_BARS || preload_count<STC_MIN_BARS)
     {
      PrintFormat("STC002_PRELOAD_FAIL stage=bars actual=%d expected=%d error=%d",
                  preload_count,STC_PRELOAD_BARS,bars_error);
      return(false);
     }
   MqlRates rates[];
   ResetLastError();
   const int copied=CopyRates(_Symbol,PERIOD_M15,1,preload_count,rates);
   const int copy_error=GetLastError();
   if(copied!=preload_count)
     {
      PrintFormat("STC002_PRELOAD_FAIL stage=copy actual=%d expected=%d error=%d",
                  copied,preload_count,copy_error);
      return(false);
     }
   if(rates[0].time!=STC_PRELOAD_FIRST || rates[copied-1].time!=last_closed)
     {
      PrintFormat("STC002_PRELOAD_FAIL stage=endpoints first=%I64d expected_first=%I64d last=%I64d expected_last=%I64d",
                  (long)rates[0].time,(long)STC_PRELOAD_FIRST,
                  (long)rates[copied-1].time,(long)last_closed);
      return(false);
     }
   ResetIndicatorState();
   for(int i=0;i<copied;i++)
     {
      if(!AdvanceIndicatorState(rates[i]))
        {
         PrintFormat("STC002_PRELOAD_FAIL stage=advance index=%d time=%I64d prior=%I64d error=%d",
                     i,(long)rates[i].time,(long)g_indicator_bar_time,GetLastError());
         return(false);
        }
     }
   const bool ready=(g_indicator_bar_time==last_closed && IsUsable(g_previous_stc) &&
                     IsUsable(g_current_stc) && IsUsable(g_current_macd) &&
                     IsUsable(g_current_atr) && g_current_atr>0.0);
   if(!ready)
      PrintFormat("STC002_PRELOAD_FAIL stage=final_state bar=%I64d expected=%I64d prev_stc=%.8f stc=%.8f macd=%.8f atr=%.8f",
                  (long)g_indicator_bar_time,(long)last_closed,g_previous_stc,
                  g_current_stc,g_current_macd,g_current_atr);
   return(ready);
  }

bool ProcessClosedBar(const datetime availability_time,SignalDecision &signal)
  {
   ZeroMemory(signal);
   MqlRates rates[];
   if(CopyRates(_Symbol,PERIOD_M15,1,1,rates)!=1 ||
      !AdvanceIndicatorState(rates[0]))
     {
      g_invalid_bars++;
      return(false);
     }
   const datetime decision_time=g_indicator_bar_time;
   if(decision_time<=0 || decision_time==g_last_decision_time)
      return(false);
   g_last_decision_time=decision_time;
   g_closed_bars++;

   if(decision_time<DESIGN_FROM || decision_time>=DESIGN_TO ||
      availability_time>=DESIGN_TO)
      return(false);
   if((long)(availability_time-decision_time)!=900)
     {
      g_clock_rejects++;
      return(false);
     }

   int direction=0;
   if(g_previous_stc<=STC_LOWER && g_current_stc>STC_LOWER && g_current_macd>0.0)
      direction=1;
   else if(g_previous_stc>=STC_UPPER && g_current_stc<STC_UPPER && g_current_macd<0.0)
      direction=-1;
   if(direction==0)
      return(false);

   const int date_key=DateKey(decision_time);
   if(date_key==g_consumed_signal_date)
      return(false);
   g_consumed_signal_date=date_key;

   signal.fired=true;
   signal.decision_time=decision_time;
   signal.availability_time=availability_time;
   signal.direction=direction;
   signal.previous_stc=g_previous_stc;
   signal.current_stc=g_current_stc;
   signal.current_macd=g_current_macd;
   signal.atr=g_current_atr;
   g_raw_signals++;
   if(direction>0)
      g_long_signals++;
   else
      g_short_signals++;
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
   double tick_size=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);
   if(!IsUsable(tick_size) || tick_size<=0.0)
      tick_size=_Point;
   return(NormalizeDouble(MathFloor(price/tick_size+1e-9)*tick_size,_Digits));
  }

double CeilToTick(const double price)
  {
   double tick_size=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);
   if(!IsUsable(tick_size) || tick_size<=0.0)
      tick_size=_Point;
   return(NormalizeDouble(MathCeil(price/tick_size-1e-9)*tick_size,_Digits));
  }

ENUM_ORDER_TYPE_FILLING ResolveFilling()
  {
   long mode=0;
   if(SymbolInfoInteger(_Symbol,SYMBOL_FILLING_MODE,mode))
     {
      if((mode&SYMBOL_FILLING_FOK)==SYMBOL_FILLING_FOK)
         return(ORDER_FILLING_FOK);
      if((mode&SYMBOL_FILLING_IOC)==SYMBOL_FILLING_IOC)
         return(ORDER_FILLING_IOC);
     }
   return(ORDER_FILLING_FOK);
  }

bool AcceptedRetcode(const uint retcode)
  {
   return(retcode==TRADE_RETCODE_DONE);
  }

int OwnedPositionCount()
  {
   int count=0;
   for(int i=PositionsTotal()-1;i>=0;i--)
     {
      const ulong ticket=PositionGetTicket(i);
      if(ticket==0 || !PositionSelectByTicket(ticket))
         continue;
      if(PositionGetString(POSITION_SYMBOL)==_Symbol &&
         PositionGetInteger(POSITION_MAGIC)==InpMagic)
         count++;
     }
   return(count);
  }

int OwnedOrderCount()
  {
   int count=0;
   for(int i=OrdersTotal()-1;i>=0;i--)
     {
      const ulong ticket=OrderGetTicket(i);
      if(ticket==0)
         continue;
      if(OrderGetString(ORDER_SYMBOL)==_Symbol &&
         OrderGetInteger(ORDER_MAGIC)==InpMagic)
         count++;
     }
   return(count);
  }

bool ClosePositionTicket(const ulong ticket,const string reason)
  {
   if(ticket==0 || !PositionSelectByTicket(ticket))
      return(false);
   const long position_type=PositionGetInteger(POSITION_TYPE);
   const double volume=PositionGetDouble(POSITION_VOLUME);
   MqlTick tick;
   if(volume<=0.0 || !SymbolInfoTick(_Symbol,tick))
      return(false);

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
      PrintFormat("STC002_CLOSE_REJECT ticket=%I64u retcode=%u error=%d reason=%s",
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

void ManageOwnedPositions(const datetime now)
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
         continue;
      if(PositionGetString(POSITION_SYMBOL)!=_Symbol ||
         PositionGetInteger(POSITION_MAGIC)!=InpMagic)
         continue;
      if(flatten_time)
        {
         ClosePositionTicket(ticket,"STC_WEEKEND_OR_END");
         continue;
        }
      const datetime opened=(datetime)PositionGetInteger(POSITION_TIME);
      const int held_bars=iBarShift(_Symbol,PERIOD_M15,opened,false);
      if(held_bars>=InpMaxHoldBars)
         ClosePositionTicket(ticket,"STC_TIME_EXIT");
     }
  }

bool CalculateVolume(const ENUM_ORDER_TYPE order_type,const double entry,
                     const double stop,double &volume)
  {
   volume=0.0;
   double one_lot_profit=0.0;
   if(!OrderCalcProfit(order_type,_Symbol,1.0,entry,stop,one_lot_profit) ||
      !IsUsable(one_lot_profit) || one_lot_profit>=0.0)
      return(false);
   const double equity=AccountInfoDouble(ACCOUNT_EQUITY);
   const double risk_budget=equity*InpRiskPercent/100.0;
   const double raw_volume=risk_budget/MathAbs(one_lot_profit);
   const double minimum=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN);
   const double maximum=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX);
   const double step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);
   if(!IsUsable(raw_volume) || !IsUsable(minimum) || !IsUsable(maximum) ||
      !IsUsable(step) || minimum<=0.0 || maximum<minimum || step<=0.0)
      return(false);
   double sized=MathFloor(raw_volume/step+1e-9)*step;
   sized=MathMin(sized,maximum);
   sized=NormalizeDouble(sized,VolumeDigits(step));
   if(sized<minimum-1e-9)
      return(false);
   double required_margin=0.0;
   if(!OrderCalcMargin(order_type,_Symbol,sized,entry,required_margin) ||
      !IsUsable(required_margin) || required_margin<0.0 ||
      required_margin>AccountInfoDouble(ACCOUNT_MARGIN_FREE))
      return(false);
   volume=sized;
   return(true);
  }

bool SubmitEntry(const SignalDecision &signal)
  {
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick))
      return(false);
   const ENUM_ORDER_TYPE order_type=(signal.direction>0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL);
   const double entry=(signal.direction>0 ? tick.ask : tick.bid);
   const double raw_distance=STOP_ATR_MULTIPLIER*signal.atr;
   const double stop=(signal.direction>0 ? FloorToTick(entry-raw_distance)
                                         : CeilToTick(entry+raw_distance));
   const double risk=(signal.direction>0 ? entry-stop : stop-entry);
   const double target=(signal.direction>0 ? CeilToTick(entry+TARGET_R*risk)
                                           : FloorToTick(entry-TARGET_R*risk));
   if(!IsUsable(entry) || !IsUsable(stop) || !IsUsable(target) || risk<=0.0 ||
      (signal.direction>0 && !(stop<entry && target>entry)) ||
      (signal.direction<0 && !(target<entry && stop>entry)))
      return(false);
   const double minimum_distance=(double)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL)*_Point;
   if(risk+1e-12<minimum_distance || MathAbs(target-entry)+1e-12<minimum_distance)
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
   request.comment="STC002";
   if(!OrderCheck(request,check) || check.retcode!=0)
     {
      PrintFormat("STC002_ORDER_CHECK_REJECT decision=%I64d retcode=%u comment=%s",
                  (long)signal.decision_time,check.retcode,check.comment);
      return(false);
     }
   if(!OrderSend(request,result) || !AcceptedRetcode(result.retcode))
     {
      PrintFormat("STC002_ORDER_SEND_REJECT decision=%I64d retcode=%u error=%d",
                  (long)signal.decision_time,result.retcode,GetLastError());
      return(false);
     }
   g_entries_accepted++;
   g_daily_entries++;
   PrintFormat("STC002_ENTRY decision=%I64d availability=%I64d direction=%d volume=%.2f entry=%.5f sl=%.5f tp=%.5f prev_stc=%.8f stc=%.8f macd=%.8f atr=%.8f",
               (long)signal.decision_time,(long)signal.availability_time,
               signal.direction,volume,entry,stop,target,signal.previous_stc,
               signal.current_stc,signal.current_macd,signal.atr);
   return(true);
  }

void ExecuteSignal(const SignalDecision &signal,const datetime now)
  {
   PrintFormat("STC002_SIGNAL decision=%I64d availability=%I64d direction=%d prev_stc=%.8f stc=%.8f macd=%.8f atr=%.8f",
               (long)signal.decision_time,(long)signal.availability_time,
               signal.direction,signal.previous_stc,signal.current_stc,
               signal.current_macd,signal.atr);
   if(g_runtime_failed || g_daily_locked || g_drawdown_locked ||
      g_daily_entries>=InpMaxTradesPerDay || WeekendEntryBlocked(now) ||
      OwnedPositionCount()!=0 || OwnedOrderCount()!=0)
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
          InpMagic==5603702 && MathAbs(InpRiskPercent-0.25)<1e-12 &&
          MathAbs(InpMaxDailyLossPct-3.5)<1e-12 &&
          MathAbs(InpMaxAccountDrawdownPct-8.0)<1e-12 &&
          InpMaxTradesPerDay==1 && InpDeviationPoints==20 &&
          InpMaxHoldBars==16 && InpFridayFlattenHour==20);
  }

int OnInit()
  {
   if(!ValidateFrozenInputs())
     {
      Print("STC002_FATAL reason=FROZEN_INPUT_OR_SYMBOL_CONTRACT");
      return(INIT_PARAMETERS_INCORRECT);
     }
   if(!CurrentM15Open(g_last_bar_open))
     {
      Print("STC002_FATAL reason=INITIAL_M15_CLOCK");
      return(INIT_FAILED);
     }
   if(!PreloadIndicatorState())
     {
      Print("STC002_FATAL reason=INDICATOR_PRELOAD");
      return(INIT_FAILED);
     }
   const double equity=AccountInfoDouble(ACCOUNT_EQUITY);
   if(!IsUsable(equity) || equity<=0.0)
     {
      Print("STC002_FATAL reason=INITIAL_EQUITY");
      return(INIT_FAILED);
     }
   g_daily_day_key=DateKey(TimeCurrent());
   g_daily_start_equity=equity;
   g_peak_equity=equity;
   PrintFormat("STC002_INIT hypothesis=%s variant=%s symbol=%s period=%d",
               InpHypothesisId,InpVariantTag,_Symbol,(int)_Period);
   return(INIT_SUCCEEDED);
  }

void OnDeinit(const int reason)
  {
   PrintFormat("STC002_SUMMARY hypothesis=%s closed_bars=%I64d raw=%I64d long=%I64d short=%I64d entries=%I64d rejects=%I64d closes=%I64d clock_rejects=%I64d invalid=%I64d runtime_failed=%s reason=%d",
               InpHypothesisId,g_closed_bars,g_raw_signals,g_long_signals,
               g_short_signals,g_entries_accepted,g_entry_rejects,
               g_close_requests,g_clock_rejects,g_invalid_bars,
               g_runtime_failed ? "true" : "false",reason);
  }

void OnTick()
  {
   const datetime now=TimeCurrent();
   UpdateRiskLocks(now);
   ManageOwnedPositions(now);

   datetime current_open=0;
   if(!CurrentM15Open(current_open) || current_open==g_last_bar_open)
      return;
   if(current_open<g_last_bar_open)
     {
      g_runtime_failed=true;
      Print("STC002_FATAL reason=BAR_CLOCK_REGRESSION");
      return;
     }
   g_last_bar_open=current_open;

   SignalDecision signal;
   if(ProcessClosedBar(current_open,signal) && signal.fired)
      ExecuteSignal(signal,current_open);
  }
//+------------------------------------------------------------------+
