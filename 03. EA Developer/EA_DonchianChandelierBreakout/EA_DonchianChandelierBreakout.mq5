//+------------------------------------------------------------------+
//| EA_DonchianChandelierBreakout.mq5                               |
//| HYP-DCX-XAUUSD-M15-001: Donchian breakout + Chandelier exit     |
//+------------------------------------------------------------------+
#property strict
#property version   "1.00"
#property description "Untuned XAUUSD M15 Donchian-20 breakout with Chandelier-22x3 exit"

input group "--- Frozen research authority ---"
input bool   InpResearchAutoMode=false;
input bool   InpEnableTelemetry=false;
input string InpHypothesisId="HYP-DCX-XAUUSD-M15-001";
input string InpVariantTag="DONCHIAN20_CHANDELIER22X3_V1";

input group "--- Frozen execution and risk ---"
input long   InpMagic=5603801;
input double InpRiskPercent=0.25;
input double InpMaxDailyLossPct=3.5;
input double InpMaxAccountDrawdownPct=8.0;
input int    InpMaxTradesPerDay=1;
input int    InpDeviationPoints=20;
input int    InpFridayFlattenHour=20;

const string EA_NAME="EA_DonchianChandelierBreakout";
const string EXPECTED_HYPOTHESIS="HYP-DCX-XAUUSD-M15-001";
const string EXPECTED_VARIANT="DONCHIAN20_CHANDELIER22X3_V1";
const string EXPECTED_SYMBOL="XAUUSD";
const int    DONCHIAN_LENGTH=20;
const int    CHANDELIER_LENGTH=22;
const int    ATR_PERIOD=22;
const double CHANDELIER_ATR_MULTIPLIER=3.0;
const int    REQUIRED_RATES=22;
const datetime DESIGN_FROM=D'2010.01.04 00:00';
const datetime DESIGN_TO=D'2018.01.01 00:00';

struct SignalDecision
  {
   bool fired;
   datetime decision_time;
   datetime availability_time;
   int direction;
   double close;
   double prior_upper;
   double prior_lower;
   double previous_close;
   double atr;
   double chandelier_stop;
  };

datetime g_last_bar_open=0;
datetime g_last_decision_time=0;
int g_consumed_signal_date=0;
int g_atr_handle=INVALID_HANDLE;

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
long g_stop_updates=0;

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

bool LoadClosedRates(MqlRates &rates[])
  {
   ArrayResize(rates,REQUIRED_RATES);
   const int copied=CopyRates(_Symbol,PERIOD_M15,1,REQUIRED_RATES,rates);
   if(copied!=REQUIRED_RATES)
      return(false);
   for(int i=0;i<copied;i++)
      if(!ValidRate(rates[i]))
         return(false);
   return(true);
  }

bool ReadClosedAtr(double &atr)
  {
   atr=EMPTY_VALUE;
   if(g_atr_handle==INVALID_HANDLE || BarsCalculated(g_atr_handle)<ATR_PERIOD+2)
      return(false);
   double value[];
   if(CopyBuffer(g_atr_handle,0,1,1,value)!=1 || !IsUsable(value[0]) || value[0]<=0.0)
      return(false);
   atr=value[0];
   return(true);
  }

double HighestHigh(const MqlRates &rates[],const int first,const int last)
  {
   double value=-DBL_MAX;
   for(int i=first;i<=last;i++)
      value=MathMax(value,rates[i].high);
   return(value);
  }

double LowestLow(const MqlRates &rates[],const int first,const int last)
  {
   double value=DBL_MAX;
   for(int i=first;i<=last;i++)
      value=MathMin(value,rates[i].low);
   return(value);
  }

bool CurrentChandelier(const int direction,double &stop,double &atr)
  {
   MqlRates rates[];
   if(!LoadClosedRates(rates) || !ReadClosedAtr(atr))
      return(false);
   const int last=ArraySize(rates)-1;
   if(direction>0)
      stop=HighestHigh(rates,0,last)-CHANDELIER_ATR_MULTIPLIER*atr;
   else
      stop=LowestLow(rates,0,last)+CHANDELIER_ATR_MULTIPLIER*atr;
   return(IsUsable(stop));
  }

bool ProcessClosedBar(const datetime availability_time,SignalDecision &signal)
  {
   ZeroMemory(signal);
   MqlRates rates[];
   double atr=0.0;
   if(!LoadClosedRates(rates) || !ReadClosedAtr(atr))
     {
      g_invalid_bars++;
      return(false);
     }
   const int current=ArraySize(rates)-1;
   const int previous=current-1;
   const datetime decision_time=rates[current].time;
   if(decision_time<=0 || decision_time==g_last_decision_time)
      return(false);
   g_last_decision_time=decision_time;
   g_closed_bars++;
   if(decision_time<DESIGN_FROM || decision_time>=DESIGN_TO || availability_time>=DESIGN_TO)
      return(false);
   if((long)(availability_time-decision_time)!=900)
     {
      g_clock_rejects++;
      return(false);
     }

   const double upper=HighestHigh(rates,current-DONCHIAN_LENGTH,current-1);
   const double lower=LowestLow(rates,current-DONCHIAN_LENGTH,current-1);
   const double previous_upper=HighestHigh(rates,previous-DONCHIAN_LENGTH,previous-1);
   const double previous_lower=LowestLow(rates,previous-DONCHIAN_LENGTH,previous-1);
   int direction=0;
   if(rates[current].close>upper && rates[previous].close<=previous_upper)
      direction=1;
   else if(rates[current].close<lower && rates[previous].close>=previous_lower)
      direction=-1;
   if(direction==0)
      return(false);

   const int date_key=DateKey(decision_time);
   if(date_key==g_consumed_signal_date)
      return(false);
   g_consumed_signal_date=date_key;
   const double chandelier=(direction>0
                            ? HighestHigh(rates,0,current)-CHANDELIER_ATR_MULTIPLIER*atr
                            : LowestLow(rates,0,current)+CHANDELIER_ATR_MULTIPLIER*atr);
   if(!IsUsable(chandelier))
     {
      g_invalid_bars++;
      return(false);
     }

   signal.fired=true;
   signal.decision_time=decision_time;
   signal.availability_time=availability_time;
   signal.direction=direction;
   signal.close=rates[current].close;
   signal.prior_upper=upper;
   signal.prior_lower=lower;
   signal.previous_close=rates[previous].close;
   signal.atr=atr;
   signal.chandelier_stop=chandelier;
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
   return(ORDER_FILLING_FOK);
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
      PrintFormat("DCX001_FATAL reason=CLOSE_POSITION_SELECT ticket=%I64u",ticket);
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
      PrintFormat("DCX001_FATAL reason=CLOSE_POSITION_PROPERTIES ticket=%I64u error=%d type=%d volume=%.8f",
                  ticket,property_error,(int)position_type,volume);
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
      g_runtime_failed=true;
      PrintFormat("DCX001_CLOSE_REJECT ticket=%I64u retcode=%u error=%d reason=%s",
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

bool ModifyPositionStop(const ulong ticket,const long position_type,
                        const double candidate)
  {
   if(ticket==0 || !PositionSelectByTicket(ticket) || !IsUsable(candidate))
     {
      g_runtime_failed=true;
      return(false);
     }
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick))
     {
      g_runtime_failed=true;
      return(false);
     }
   ResetLastError();
   const double old_stop=PositionGetDouble(POSITION_SL);
   const double old_target=PositionGetDouble(POSITION_TP);
   const int property_error=GetLastError();
   long stops_level=0;
   long freeze_level=0;
   if(property_error!=0 || !IsUsable(old_stop) || old_stop<0.0 ||
      !IsUsable(old_target) || old_target<0.0 ||
      !SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL,stops_level) ||
      !SymbolInfoInteger(_Symbol,SYMBOL_TRADE_FREEZE_LEVEL,freeze_level) ||
      stops_level<0 || freeze_level<0 ||
      (position_type!=POSITION_TYPE_BUY && position_type!=POSITION_TYPE_SELL))
     {
      g_runtime_failed=true;
      PrintFormat("DCX001_FATAL reason=TRAIL_POSITION_PROPERTIES ticket=%I64u error=%d",
                  ticket,property_error);
      return(false);
     }
   const double minimum_distance=(double)MathMax(stops_level,freeze_level)*_Point;
   double next_stop=0.0;
   if(position_type==POSITION_TYPE_BUY)
     {
      next_stop=FloorToTick(candidate);
      if(next_stop<=0.0 || next_stop>=tick.bid-minimum_distance ||
         (old_stop>0.0 && next_stop<=old_stop+0.5*_Point))
         return(true);
     }
   else
     {
      next_stop=CeilToTick(candidate);
      if(next_stop<=tick.ask+minimum_distance ||
         (old_stop>0.0 && next_stop>=old_stop-0.5*_Point))
         return(true);
     }

   MqlTradeRequest request;
   MqlTradeResult result;
   ZeroMemory(request);
   ZeroMemory(result);
   request.action=TRADE_ACTION_SLTP;
   request.position=ticket;
   request.symbol=_Symbol;
   request.magic=InpMagic;
   request.sl=next_stop;
   request.tp=old_target;
   if(!OrderSend(request,result) || !AcceptedRetcode(result.retcode))
     {
      g_runtime_failed=true;
      PrintFormat("DCX001_TRAIL_REJECT ticket=%I64u retcode=%u error=%d stop=%.5f",
                  ticket,result.retcode,GetLastError(),next_stop);
      return(false);
     }
   g_stop_updates++;
   return(true);
  }

bool ManageOwnedPositions(const datetime now,const bool update_trail)
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
         PrintFormat("DCX001_FATAL reason=POSITION_ENUMERATION index=%d",i);
         return(false);
        }
      ResetLastError();
      const string symbol=PositionGetString(POSITION_SYMBOL);
      const long magic=PositionGetInteger(POSITION_MAGIC);
      const long position_type=PositionGetInteger(POSITION_TYPE);
      if(GetLastError()!=0)
        {
         g_runtime_failed=true;
         PrintFormat("DCX001_FATAL reason=POSITION_PROPERTIES ticket=%I64u",ticket);
         return(false);
        }
      if(symbol!=_Symbol || magic!=InpMagic)
         continue;
      if(flatten_time)
        {
         if(!ClosePositionTicket(ticket,"DCX_WEEKEND_OR_END"))
            return(false);
         continue;
        }
      if(update_trail)
        {
         double stop=0.0;
         double atr=0.0;
         const int direction=(position_type==POSITION_TYPE_BUY ? 1 : -1);
         MqlTick tick;
         if(!CurrentChandelier(direction,stop,atr) || !SymbolInfoTick(_Symbol,tick))
           {
            g_runtime_failed=true;
            PrintFormat("DCX001_FATAL reason=TRAIL_UPDATE ticket=%I64u",ticket);
            return(false);
           }
         const bool crossed=(direction>0 ? tick.bid<=stop : tick.ask>=stop);
         if(crossed)
           {
            if(!ClosePositionTicket(ticket,"DCX_CHANDELIER_CROSS"))
               return(false);
           }
         else if(!ModifyPositionStop(ticket,position_type,stop))
           {
            g_runtime_failed=true;
            PrintFormat("DCX001_FATAL reason=TRAIL_MODIFY ticket=%I64u",ticket);
            return(false);
           }
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
   const double stop=(signal.direction>0 ? FloorToTick(signal.chandelier_stop)
                                         : CeilToTick(signal.chandelier_stop));
   const double risk=(signal.direction>0 ? entry-stop : stop-entry);
   if(!IsUsable(entry) || !IsUsable(stop) || risk<=0.0 ||
      (signal.direction>0 && !(stop<entry)) ||
      (signal.direction<0 && !(stop>entry)))
      return(false);
   const double minimum_distance=(double)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL)*_Point;
   if(risk+1e-12<minimum_distance)
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
   request.tp=0.0;
   request.deviation=InpDeviationPoints;
   request.type_filling=ResolveFilling();
   request.comment="DCX001";
   if(!OrderCheck(request,check) || check.retcode!=0)
     {
      PrintFormat("DCX001_ORDER_CHECK_REJECT decision=%I64d retcode=%u comment=%s",
                  (long)signal.decision_time,check.retcode,check.comment);
      return(false);
     }
   if(!OrderSend(request,result) || !AcceptedRetcode(result.retcode))
     {
      PrintFormat("DCX001_ORDER_SEND_REJECT decision=%I64d retcode=%u error=%d",
                  (long)signal.decision_time,result.retcode,GetLastError());
      return(false);
     }
   g_entries_accepted++;
   g_daily_entries++;
   PrintFormat("DCX001_ENTRY decision=%I64d availability=%I64d direction=%d volume=%.2f entry=%.5f sl=%.5f close=%.5f upper=%.5f lower=%.5f atr=%.5f",
               (long)signal.decision_time,(long)signal.availability_time,
               signal.direction,volume,entry,stop,signal.close,
               signal.prior_upper,signal.prior_lower,signal.atr);
   return(true);
  }

void ExecuteSignal(const SignalDecision &signal,const datetime now)
  {
   PrintFormat("DCX001_SIGNAL decision=%I64d availability=%I64d direction=%d close=%.5f upper=%.5f lower=%.5f previous_close=%.5f atr=%.5f chandelier=%.5f",
               (long)signal.decision_time,(long)signal.availability_time,
               signal.direction,signal.close,signal.prior_upper,
               signal.prior_lower,signal.previous_close,signal.atr,
               signal.chandelier_stop);
   int positions=0;
   int orders=0;
   if(!OwnedPositionCount(positions) || !OwnedOrderCount(orders))
     {
      g_runtime_failed=true;
      g_entry_rejects++;
      Print("DCX001_FATAL reason=OWNED_INVENTORY_UNCERTAIN");
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
          InpMagic==5603801 && MathAbs(InpRiskPercent-0.25)<1e-12 &&
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
      Print("DCX001_FATAL reason=FROZEN_INPUT_OR_SYMBOL_CONTRACT");
      return(INIT_PARAMETERS_INCORRECT);
     }
   if(!CurrentM15Open(g_last_bar_open))
     {
      g_runtime_failed=true;
      Print("DCX001_FATAL reason=INITIAL_M15_CLOCK");
      return(INIT_FAILED);
     }
   long filling_mode=0;
   if(!SymbolInfoInteger(_Symbol,SYMBOL_FILLING_MODE,filling_mode) ||
      (filling_mode&SYMBOL_FILLING_FOK)!=SYMBOL_FILLING_FOK)
     {
      g_runtime_failed=true;
      Print("DCX001_FATAL reason=FOK_NOT_SUPPORTED");
      return(INIT_FAILED);
     }
   g_atr_handle=iATR(_Symbol,PERIOD_M15,ATR_PERIOD);
   if(g_atr_handle==INVALID_HANDLE)
     {
      g_runtime_failed=true;
      Print("DCX001_FATAL reason=ATR_HANDLE");
      return(INIT_FAILED);
     }
   const double equity=AccountInfoDouble(ACCOUNT_EQUITY);
   if(!IsUsable(equity) || equity<=0.0)
     {
      g_runtime_failed=true;
      Print("DCX001_FATAL reason=INITIAL_EQUITY");
      return(INIT_FAILED);
     }
   g_daily_day_key=DateKey(TimeCurrent());
   g_daily_start_equity=equity;
   g_peak_equity=equity;
   PrintFormat("DCX001_INIT hypothesis=%s variant=%s symbol=%s period=%d",
               InpHypothesisId,InpVariantTag,_Symbol,(int)_Period);
   return(INIT_SUCCEEDED);
  }

void OnDeinit(const int reason)
  {
   if(g_atr_handle!=INVALID_HANDLE)
      IndicatorRelease(g_atr_handle);
   PrintFormat("DCX001_SUMMARY hypothesis=%s closed_bars=%I64d raw=%I64d long=%I64d short=%I64d entries=%I64d rejects=%I64d closes=%I64d trails=%I64d clock_rejects=%I64d invalid=%I64d runtime_failed=%s reason=%d",
               InpHypothesisId,g_closed_bars,g_raw_signals,g_long_signals,
               g_short_signals,g_entries_accepted,g_entry_rejects,
               g_close_requests,g_stop_updates,g_clock_rejects,g_invalid_bars,
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
      Print("DCX001_FATAL reason=BAR_CLOCK_REGRESSION");
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
