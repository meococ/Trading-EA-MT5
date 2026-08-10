//+------------------------------------------------------------------+
//| EA_FisherTrendPullback.mq5                                      |
//| HYP-FTP-XAUUSD-M15-001: Fisher pullback turn in EMA200 trend    |
//+------------------------------------------------------------------+
#property strict
#property version   "1.00"
#property description "Untuned XAUUSD M15 Fisher-10 extreme turn inside EMA200 trend"

input group "--- Frozen research authority ---"
input bool   InpResearchAutoMode=false;
input bool   InpEnableTelemetry=false;
input string InpHypothesisId="HYP-FTP-XAUUSD-M15-001";
input string InpVariantTag="FISHER10_EMA200_PULLBACK_V1";

input group "--- Frozen execution and risk ---"
input long   InpMagic=5603802;
input double InpRiskPercent=0.25;
input double InpMaxDailyLossPct=3.5;
input double InpMaxAccountDrawdownPct=8.0;
input int    InpMaxTradesPerDay=1;
input int    InpDeviationPoints=20;
input int    InpFridayFlattenHour=20;

const string EXPECTED_HYPOTHESIS="HYP-FTP-XAUUSD-M15-001";
const string EXPECTED_VARIANT="FISHER10_EMA200_PULLBACK_V1";
const string EXPECTED_SYMBOL="XAUUSD";
const int FISHER_LENGTH=10;
const int FISHER_WARMUP=500;
const int EMA_PERIOD=200;
const int EMA_SLOPE_BARS=8;
const int ATR_PERIOD=14;
const double FISHER_EXTREME=1.50;
const double STOP_ATR_FLOOR=1.25;
const double STOP_ATR_BUFFER=0.25;
const double TARGET_R=1.50;
const int MAX_HOLD_BARS=12;
const datetime DESIGN_FROM=D'2010.01.04 00:00';
const datetime DESIGN_TO=D'2018.01.01 00:00';

struct SignalDecision
  {
   bool fired;
   datetime decision_time;
   datetime availability_time;
   int direction;
   double close;
   double signal_high;
   double signal_low;
   double atr;
   double fish;
   double prior_fish;
   double ema;
   double prior_ema;
  };

datetime g_last_bar_open=0;
datetime g_last_decision_time=0;
int g_atr_handle=INVALID_HANDLE;
int g_ema_handle=INVALID_HANDLE;
double g_fisher_value=0.0;
double g_fisher=0.0;

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
long g_time_exits=0;

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

double ClampFisherInput(const double value)
  {
   return(MathMax(-0.999,MathMin(0.999,value)));
  }

bool AdvanceFisher(const MqlRates &rates[],const int current,
                   double &value_state,double &fish_state)
  {
   if(current<FISHER_LENGTH-1 || current>=ArraySize(rates))
      return(false);
   double highest=-DBL_MAX;
   double lowest=DBL_MAX;
   for(int i=current-FISHER_LENGTH+1;i<=current;i++)
     {
      if(!ValidRate(rates[i]))
         return(false);
      highest=MathMax(highest,rates[i].high);
      lowest=MathMin(lowest,rates[i].low);
     }
   const double price=0.5*(rates[current].high+rates[current].low);
   double raw=0.0;
   if(highest>lowest)
      raw=2.0*((price-lowest)/(highest-lowest)-0.5);
   value_state=ClampFisherInput(0.33*raw+0.67*value_state);
   const double next_fish=0.5*MathLog((1.0+value_state)/(1.0-value_state))+0.5*fish_state;
   if(!IsUsable(next_fish))
      return(false);
   fish_state=next_fish;
   return(true);
  }

bool InitializeFisherState()
  {
   MqlRates rates[];
   ArrayResize(rates,FISHER_WARMUP);
   const int copied=CopyRates(_Symbol,PERIOD_M15,1,FISHER_WARMUP,rates);
   if(copied!=FISHER_WARMUP)
      return(false);
   double value_state=0.0;
   double fish_state=0.0;
   for(int i=FISHER_LENGTH-1;i<copied;i++)
      if(!AdvanceFisher(rates,i,value_state,fish_state))
         return(false);
   g_fisher_value=value_state;
   g_fisher=fish_state;
   g_last_decision_time=rates[copied-1].time;
   return(true);
  }

bool ReadClosedIndicators(double &atr,double &ema,double &prior_ema)
  {
   atr=EMPTY_VALUE;
   ema=EMPTY_VALUE;
   prior_ema=EMPTY_VALUE;
   if(g_atr_handle==INVALID_HANDLE || g_ema_handle==INVALID_HANDLE ||
      BarsCalculated(g_atr_handle)<ATR_PERIOD+2 ||
      BarsCalculated(g_ema_handle)<EMA_PERIOD+EMA_SLOPE_BARS+2)
      return(false);
   double atr_value[];
   double ema_value[];
   double ema_prior[];
   if(CopyBuffer(g_atr_handle,0,1,1,atr_value)!=1 ||
      CopyBuffer(g_ema_handle,0,1,1,ema_value)!=1 ||
      CopyBuffer(g_ema_handle,0,9,1,ema_prior)!=1)
      return(false);
   atr=atr_value[0];
   ema=ema_value[0];
   prior_ema=ema_prior[0];
   return(IsUsable(atr) && atr>0.0 && IsUsable(ema) && IsUsable(prior_ema));
  }

bool ProcessClosedBar(const datetime availability_time,SignalDecision &signal)
  {
   ZeroMemory(signal);
   MqlRates rates[];
   ArrayResize(rates,FISHER_LENGTH);
   if(CopyRates(_Symbol,PERIOD_M15,1,FISHER_LENGTH,rates)!=FISHER_LENGTH)
     {
      g_invalid_bars++;
      return(false);
     }
   for(int i=0;i<ArraySize(rates);i++)
      if(!ValidRate(rates[i]))
        {
         g_invalid_bars++;
         return(false);
        }
   const int current=ArraySize(rates)-1;
   const datetime decision_time=rates[current].time;
   if(decision_time<=0 || decision_time==g_last_decision_time)
      return(false);
   if((long)(availability_time-decision_time)!=900)
     {
      g_clock_rejects++;
      return(false);
     }
   const double prior_fish=g_fisher;
   double next_value=g_fisher_value;
   double next_fish=g_fisher;
   if(!AdvanceFisher(rates,current,next_value,next_fish))
     {
      g_invalid_bars++;
      return(false);
     }
   g_fisher_value=next_value;
   g_fisher=next_fish;
   g_last_decision_time=decision_time;
   g_closed_bars++;

   if(decision_time<DESIGN_FROM || decision_time>=DESIGN_TO || availability_time>=DESIGN_TO)
      return(false);
   double atr=0.0;
   double ema=0.0;
   double prior_ema=0.0;
   if(!ReadClosedIndicators(atr,ema,prior_ema))
     {
      g_invalid_bars++;
      return(false);
     }
   int direction=0;
   if(prior_fish<=-FISHER_EXTREME && next_fish>prior_fish &&
      rates[current].close>ema && ema>prior_ema)
      direction=1;
   else if(prior_fish>=FISHER_EXTREME && next_fish<prior_fish &&
           rates[current].close<ema && ema<prior_ema)
      direction=-1;
   if(direction==0)
      return(false);

   signal.fired=true;
   signal.decision_time=decision_time;
   signal.availability_time=availability_time;
   signal.direction=direction;
   signal.close=rates[current].close;
   signal.signal_high=rates[current].high;
   signal.signal_low=rates[current].low;
   signal.atr=atr;
   signal.fish=next_fish;
   signal.prior_fish=prior_fish;
   signal.ema=ema;
   signal.prior_ema=prior_ema;
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
   request.type_filling=ORDER_FILLING_FOK;
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
      PrintFormat("FTP001_CLOSE_REJECT ticket=%I64u retcode=%u error=%d reason=%s",
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

bool ManageOwnedPositions(const datetime now,const bool new_bar)
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
         return(false);
        }
      ResetLastError();
      const string symbol=PositionGetString(POSITION_SYMBOL);
      const long magic=PositionGetInteger(POSITION_MAGIC);
      const datetime entry_time=(datetime)PositionGetInteger(POSITION_TIME);
      if(GetLastError()!=0)
        {
         g_runtime_failed=true;
         return(false);
        }
      if(symbol!=_Symbol || magic!=InpMagic)
         continue;
      bool time_exit=false;
      if(new_bar)
        {
         const int shift=iBarShift(_Symbol,PERIOD_M15,entry_time,false);
         if(shift<0)
           {
            g_runtime_failed=true;
            return(false);
           }
         time_exit=(shift>=MAX_HOLD_BARS);
        }
      if(flatten_time || time_exit)
        {
         if(!ClosePositionTicket(ticket,flatten_time ? "FTP_WEEKEND_OR_END" : "FTP_TIME_EXIT"))
            return(false);
         if(time_exit)
            g_time_exits++;
        }
     }
   return(true);
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
   if(!IsUsable(equity) || equity<=0.0 || !IsUsable(raw_volume) ||
      !IsUsable(minimum) || !IsUsable(maximum) || !IsUsable(step) ||
      minimum<=0.0 || maximum<minimum || step<=0.0)
      return(false);
   double sized=MathFloor(raw_volume/step+1e-9)*step;
   sized=MathMin(sized,maximum);
   sized=NormalizeDouble(sized,VolumeDigits(step));
   if(sized<minimum-1e-9)
      return(false);
   double required_margin=0.0;
   const double free_margin=AccountInfoDouble(ACCOUNT_MARGIN_FREE);
   if(!OrderCalcMargin(order_type,_Symbol,sized,entry,required_margin) ||
      !IsUsable(required_margin) || required_margin<0.0 ||
      !IsUsable(free_margin) || required_margin>free_margin)
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
   double raw_stop=0.0;
   if(signal.direction>0)
      raw_stop=MathMin(signal.signal_low-STOP_ATR_BUFFER*signal.atr,
                       entry-STOP_ATR_FLOOR*signal.atr);
   else
      raw_stop=MathMax(signal.signal_high+STOP_ATR_BUFFER*signal.atr,
                       entry+STOP_ATR_FLOOR*signal.atr);
   const double stop=(signal.direction>0 ? FloorToTick(raw_stop) : CeilToTick(raw_stop));
   const double risk=(signal.direction>0 ? entry-stop : stop-entry);
   double target=(signal.direction>0 ? entry+TARGET_R*risk : entry-TARGET_R*risk);
   target=(signal.direction>0 ? CeilToTick(target) : FloorToTick(target));
   long stops_level=0;
   long freeze_level=0;
   if(!SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL,stops_level) ||
      !SymbolInfoInteger(_Symbol,SYMBOL_TRADE_FREEZE_LEVEL,freeze_level) ||
      stops_level<0 || freeze_level<0)
      return(false);
   const double minimum_distance=(double)MathMax(stops_level,freeze_level)*_Point;
   const double reward=(signal.direction>0 ? target-entry : entry-target);
   if(!IsUsable(entry) || !IsUsable(stop) || !IsUsable(target) ||
      risk<=0.0 || reward<=0.0 || risk+1e-12<minimum_distance ||
      reward+1e-12<minimum_distance)
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
   request.type_filling=ORDER_FILLING_FOK;
   request.comment="FTP001";
   if(!OrderCheck(request,check) || check.retcode!=0)
     {
      PrintFormat("FTP001_ORDER_CHECK_REJECT decision=%I64d retcode=%u comment=%s",
                  (long)signal.decision_time,check.retcode,check.comment);
      return(false);
     }
   if(!OrderSend(request,result) || !AcceptedRetcode(result.retcode))
     {
      PrintFormat("FTP001_ORDER_SEND_REJECT decision=%I64d retcode=%u error=%d",
                  (long)signal.decision_time,result.retcode,GetLastError());
      return(false);
     }
   g_entries_accepted++;
   g_daily_entries++;
   PrintFormat("FTP001_ENTRY decision=%I64d availability=%I64d direction=%d volume=%.2f entry=%.5f sl=%.5f tp=%.5f fish=%.6f prior=%.6f ema=%.5f atr=%.5f",
               (long)signal.decision_time,(long)signal.availability_time,
               signal.direction,volume,entry,stop,target,signal.fish,
               signal.prior_fish,signal.ema,signal.atr);
   return(true);
  }

void ExecuteSignal(const SignalDecision &signal,const datetime now)
  {
   PrintFormat("FTP001_SIGNAL decision=%I64d availability=%I64d direction=%d close=%.5f fish=%.6f prior=%.6f ema=%.5f ema8=%.5f atr=%.5f",
               (long)signal.decision_time,(long)signal.availability_time,
               signal.direction,signal.close,signal.fish,signal.prior_fish,
               signal.ema,signal.prior_ema,signal.atr);
   int positions=0;
   int orders=0;
   if(!OwnedPositionCount(positions) || !OwnedOrderCount(orders))
     {
      g_runtime_failed=true;
      g_entry_rejects++;
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
          InpMagic==5603802 && MathAbs(InpRiskPercent-0.25)<1e-12 &&
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
      Print("FTP001_FATAL reason=FROZEN_INPUT_OR_SYMBOL_CONTRACT");
      return(INIT_PARAMETERS_INCORRECT);
     }
   if(!CurrentM15Open(g_last_bar_open))
     {
      g_runtime_failed=true;
      return(INIT_FAILED);
     }
   long filling_mode=0;
   if(!SymbolInfoInteger(_Symbol,SYMBOL_FILLING_MODE,filling_mode) ||
      (filling_mode&SYMBOL_FILLING_FOK)!=SYMBOL_FILLING_FOK)
     {
      g_runtime_failed=true;
      Print("FTP001_FATAL reason=FOK_NOT_SUPPORTED");
      return(INIT_FAILED);
     }
   g_atr_handle=iATR(_Symbol,PERIOD_M15,ATR_PERIOD);
   g_ema_handle=iMA(_Symbol,PERIOD_M15,EMA_PERIOD,0,MODE_EMA,PRICE_CLOSE);
   if(g_atr_handle==INVALID_HANDLE || g_ema_handle==INVALID_HANDLE ||
      !InitializeFisherState())
     {
      g_runtime_failed=true;
      Print("FTP001_FATAL reason=INDICATOR_INITIALIZATION");
      return(INIT_FAILED);
     }
   const double equity=AccountInfoDouble(ACCOUNT_EQUITY);
   if(!IsUsable(equity) || equity<=0.0)
     {
      g_runtime_failed=true;
      return(INIT_FAILED);
     }
   g_daily_day_key=DateKey(TimeCurrent());
   g_daily_start_equity=equity;
   g_peak_equity=equity;
   PrintFormat("FTP001_INIT hypothesis=%s variant=%s symbol=%s period=%d fish=%.6f",
               InpHypothesisId,InpVariantTag,_Symbol,(int)_Period,g_fisher);
   return(INIT_SUCCEEDED);
  }

void OnDeinit(const int reason)
  {
   if(g_atr_handle!=INVALID_HANDLE)
      IndicatorRelease(g_atr_handle);
   if(g_ema_handle!=INVALID_HANDLE)
      IndicatorRelease(g_ema_handle);
   PrintFormat("FTP001_SUMMARY hypothesis=%s closed_bars=%I64d raw=%I64d long=%I64d short=%I64d entries=%I64d rejects=%I64d closes=%I64d time_exits=%I64d clock_rejects=%I64d invalid=%I64d runtime_failed=%s reason=%d",
               InpHypothesisId,g_closed_bars,g_raw_signals,g_long_signals,
               g_short_signals,g_entries_accepted,g_entry_rejects,
               g_close_requests,g_time_exits,g_clock_rejects,g_invalid_bars,
               g_runtime_failed ? "true" : "false",reason);
  }

void OnTick()
  {
   const datetime now=TimeCurrent();
   UpdateRiskLocks(now);
   if(!ManageOwnedPositions(now,false))
      return;
   datetime current_open=0;
   if(!CurrentM15Open(current_open) || current_open==g_last_bar_open)
      return;
   if(current_open<g_last_bar_open)
     {
      g_runtime_failed=true;
      return;
     }
   g_last_bar_open=current_open;
   if(!ManageOwnedPositions(now,true))
      return;
   SignalDecision signal;
   if(ProcessClosedBar(current_open,signal) && signal.fired)
      ExecuteSignal(signal,current_open);
  }
//+------------------------------------------------------------------+
