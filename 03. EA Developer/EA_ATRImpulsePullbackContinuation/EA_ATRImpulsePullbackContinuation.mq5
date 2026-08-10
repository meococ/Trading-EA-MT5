//+------------------------------------------------------------------+
//| EA_ATRImpulsePullbackContinuation.mq5                           |
//| HYP-APC-XAUUSD-M15-002: ATR impulse-pullback continuation      |
//+------------------------------------------------------------------+
#property strict
#property version   "1.01"
#property description "Untuned XAUUSD M15 ATR impulse-pullback-release continuation; D0/flat-bar safe"

input group "--- Frozen research authority ---"
input bool   InpResearchAutoMode=false;
input bool   InpEnableTelemetry=false;
input string InpHypothesisId="HYP-APC-XAUUSD-M15-002";
input string InpVariantTag="ATR14_EMA50_ADX14_IMPULSE_PULLBACK_RELEASE_V2_D0_FLATSAFE";

input group "--- Frozen execution and risk ---"
input long   InpMagic=5603902;
input double InpRiskPercent=0.25;
input double InpMaxDailyLossPct=3.5;
input double InpMaxAccountDrawdownPct=8.0;
input int    InpMaxTradesPerDay=1;
input int    InpDeviationPoints=20;
input int    InpFridayFlattenHour=20;

const string EA_NAME="EA_ATRImpulsePullbackContinuation";
const string EXPECTED_HYPOTHESIS="HYP-APC-XAUUSD-M15-002";
const string EXPECTED_VARIANT="ATR14_EMA50_ADX14_IMPULSE_PULLBACK_RELEASE_V2_D0_FLATSAFE";
const string EXPECTED_SYMBOL="XAUUSD";
const int    ATR_PERIOD=14;
const int    EMA_PERIOD=50;
const int    ADX_PERIOD=14;
const double MIN_ADX=18.0;
const double IMPULSE_TR_ATR=1.35;
const double IMPULSE_BODY_FRAC=0.55;
const double IMPULSE_CLOSE_LOCATION=0.70;
const double PULLBACK_TR_ATR=0.85;
const double RELEASE_MAX_EXTENSION_ATR=0.35;
const double STOP_BUFFER_ATR=0.20;
const double TARGET_R=1.45;
const int    MAX_HOLD_BARS=10;
const int    REQUIRED_RATES=12;
const datetime DESIGN_FROM=D'2010.01.04 00:00';
const datetime DESIGN_TO=D'2018.01.01 00:00';

struct SignalDecision
  {
   bool fired;
   datetime decision_time;
   datetime availability_time;
   int direction;
   double close;
   double impulse_high;
   double impulse_low;
   double pullback_high;
   double pullback_low;
   double atr;
   double ema;
   double adx;
   double structural_stop;
  };

datetime g_last_bar_open=0;
datetime g_last_decision_time=0;
int g_consumed_signal_date=0;
int g_atr_handle=INVALID_HANDLE;
int g_ema_handle=INVALID_HANDLE;
int g_adx_handle=INVALID_HANDLE;

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

bool ReadSeriesInteger(const ENUM_TIMEFRAMES timeframe,
                       const ENUM_SERIES_INFO_INTEGER property,
                       long &value)
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

bool ReadIndicator(const int handle,const int buffer,const int shift,double &value)
  {
   value=EMPTY_VALUE;
   if(handle==INVALID_HANDLE || shift<1)
      return(false);
   double data[];
   int copied=0;
   if(shift==1)
      copied=CopyBuffer(handle,buffer,1,1,data);
   else if(shift==2)
      copied=CopyBuffer(handle,buffer,2,1,data);
   else if(shift==3)
      copied=CopyBuffer(handle,buffer,3,1,data);
   else if(shift==4)
      copied=CopyBuffer(handle,buffer,4,1,data);
   else if(shift==9)
      copied=CopyBuffer(handle,buffer,9,1,data);
   else
      return(false);
   if(copied!=1 || !IsUsable(data[0]))
      return(false);
   value=data[0];
   return(true);
  }

double TrueRange(const MqlRates &bar,const double previous_close)
  {
   return(MathMax(bar.high-bar.low,
                  MathMax(MathAbs(bar.high-previous_close),
                          MathAbs(bar.low-previous_close))));
  }

bool ProcessClosedBar(const datetime availability_time,SignalDecision &signal)
  {
   ZeroMemory(signal);
   MqlRates rates[];
   if(!LoadClosedRates(rates))
     {
      g_invalid_bars++;
      g_runtime_failed=true;
      PrintFormat("APC002_FATAL reason=CLOSED_RATE_LOAD availability=%I64d",
                  (long)availability_time);
      return(false);
     }
   const int release=ArraySize(rates)-1;
   const int pullback=release-1;
   const int impulse=release-2;
   const datetime decision_time=rates[release].time;
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

   double atr_release=0.0,atr_pullback=0.0,atr_impulse=0.0;
   double ema_release=0.0,ema_slope_ref=0.0;
   double adx_release=0.0,adx_rise_ref=0.0,plus_di=0.0,minus_di=0.0;
   if(!ReadIndicator(g_atr_handle,0,1,atr_release) ||
      !ReadIndicator(g_atr_handle,0,2,atr_pullback) ||
      !ReadIndicator(g_atr_handle,0,3,atr_impulse) ||
      !ReadIndicator(g_ema_handle,0,1,ema_release) ||
      !ReadIndicator(g_ema_handle,0,9,ema_slope_ref) ||
      !ReadIndicator(g_adx_handle,0,1,adx_release) ||
      !ReadIndicator(g_adx_handle,0,4,adx_rise_ref) ||
      !ReadIndicator(g_adx_handle,1,1,plus_di) ||
      !ReadIndicator(g_adx_handle,2,1,minus_di) ||
      atr_release<=0.0 || atr_pullback<=0.0 || atr_impulse<=0.0)
     {
      g_invalid_bars++;
      g_runtime_failed=true;
      PrintFormat("APC002_FATAL reason=CLOSED_INDICATOR_LOAD decision=%I64d",
                  (long)decision_time);
      return(false);
     }

   const double impulse_tr=TrueRange(rates[impulse],rates[impulse-1].close);
   const double pullback_tr=TrueRange(rates[pullback],rates[pullback-1].close);
   const double impulse_body=MathAbs(rates[impulse].close-rates[impulse].open);
   if(!IsUsable(impulse_tr) || !IsUsable(pullback_tr) ||
      impulse_tr<0.0 || pullback_tr<0.0)
     {
      g_invalid_bars++;
      g_runtime_failed=true;
      PrintFormat("APC002_FATAL reason=TRUE_RANGE_INVALID decision=%I64d",
                  (long)decision_time);
      return(false);
     }
   // A broker-native H=L=C impulse bar is valid data but cannot be an impulse.
   // Consume it as a non-signal before any close-location division.
   if(impulse_tr==0.0)
      return(false);
   const double impulse_mid=0.5*(rates[impulse].open+rates[impulse].close);
   const double long_close_location=(rates[impulse].close-rates[impulse].low)/impulse_tr;
   const double short_close_location=(rates[impulse].high-rates[impulse].close)/impulse_tr;

   const bool common_impulse=(impulse_tr>=IMPULSE_TR_ATR*atr_impulse &&
                              impulse_body>=IMPULSE_BODY_FRAC*impulse_tr);
   const bool common_pullback=(pullback_tr<=PULLBACK_TR_ATR*atr_pullback);
   const bool long_trend=(rates[release].close>ema_release &&
                          ema_release>ema_slope_ref &&
                          adx_release>=MIN_ADX && adx_release>adx_rise_ref &&
                          plus_di>minus_di);
   const bool short_trend=(rates[release].close<ema_release &&
                           ema_release<ema_slope_ref &&
                           adx_release>=MIN_ADX && adx_release>adx_rise_ref &&
                           minus_di>plus_di);
   const bool long_impulse=(common_impulse &&
                            rates[impulse].close>rates[impulse].open &&
                            long_close_location>=IMPULSE_CLOSE_LOCATION);
   const bool short_impulse=(common_impulse &&
                             rates[impulse].close<rates[impulse].open &&
                             short_close_location>=IMPULSE_CLOSE_LOCATION);
   const bool long_pullback=(common_pullback &&
                             rates[pullback].low>=impulse_mid &&
                             rates[pullback].close>=rates[impulse].open);
   const bool short_pullback=(common_pullback &&
                              rates[pullback].high<=impulse_mid &&
                              rates[pullback].close<=rates[impulse].open);
   const bool long_release=(rates[release].close>rates[pullback].high &&
                            rates[release].close<=rates[impulse].high+RELEASE_MAX_EXTENSION_ATR*atr_release);
   const bool short_release=(rates[release].close<rates[pullback].low &&
                             rates[release].close>=rates[impulse].low-RELEASE_MAX_EXTENSION_ATR*atr_release);

   const bool long_signal=(long_trend && long_impulse && long_pullback && long_release);
   const bool short_signal=(short_trend && short_impulse && short_pullback && short_release);
   if(long_signal==short_signal)
      return(false);
   const int direction=(long_signal ? 1 : -1);

   const int date_key=DateKey(decision_time);
   if(date_key==g_consumed_signal_date)
      return(false);
   g_consumed_signal_date=date_key;
   const double stop=(direction>0
                      ? MathMin(rates[impulse].low,rates[pullback].low)-STOP_BUFFER_ATR*atr_release
                      : MathMax(rates[impulse].high,rates[pullback].high)+STOP_BUFFER_ATR*atr_release);
   if(!IsUsable(stop))
     {
      g_invalid_bars++;
      return(false);
     }

   signal.fired=true;
   signal.decision_time=decision_time;
   signal.availability_time=availability_time;
   signal.direction=direction;
   signal.close=rates[release].close;
   signal.impulse_high=rates[impulse].high;
   signal.impulse_low=rates[impulse].low;
   signal.pullback_high=rates[pullback].high;
   signal.pullback_low=rates[pullback].low;
   signal.atr=atr_release;
   signal.ema=ema_release;
   signal.adx=adx_release;
   signal.structural_stop=stop;
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
      PrintFormat("APC002_FATAL reason=CLOSE_POSITION_SELECT ticket=%I64u",ticket);
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
      PrintFormat("APC002_FATAL reason=CLOSE_POSITION_PROPERTIES ticket=%I64u error=%d type=%d volume=%.8f",
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
      PrintFormat("APC002_CLOSE_REJECT ticket=%I64u retcode=%u error=%d reason=%s",
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

bool ManageOwnedPositions(const datetime now,const bool update_exit)
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
         PrintFormat("APC002_FATAL reason=POSITION_ENUMERATION index=%d",i);
         return(false);
        }
      ResetLastError();
      const string symbol=PositionGetString(POSITION_SYMBOL);
      const long magic=PositionGetInteger(POSITION_MAGIC);
      const long position_type=PositionGetInteger(POSITION_TYPE);
      const datetime position_time=(datetime)PositionGetInteger(POSITION_TIME);
      if(GetLastError()!=0 ||
         (position_type!=POSITION_TYPE_BUY && position_type!=POSITION_TYPE_SELL) ||
         position_time<=0)
        {
         g_runtime_failed=true;
         PrintFormat("APC002_FATAL reason=POSITION_PROPERTIES ticket=%I64u",ticket);
         return(false);
        }
      if(symbol!=_Symbol || magic!=InpMagic)
         continue;
      if(flatten_time)
        {
         if(!ClosePositionTicket(ticket,"APC_WEEKEND_OR_END"))
            return(false);
         continue;
        }
      if(update_exit)
        {
         ResetLastError();
         const int shift=iBarShift(_Symbol,PERIOD_M15,position_time,false);
         if(shift<0 || GetLastError()!=0)
           {
            g_runtime_failed=true;
            PrintFormat("APC002_FATAL reason=ENTRY_BAR_RECOVERY ticket=%I64u",ticket);
            return(false);
           }
         if(shift>=MAX_HOLD_BARS && !ClosePositionTicket(ticket,"APC_TIME_EXIT"))
            return(false);
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
   const double stop=(signal.direction>0 ? FloorToTick(signal.structural_stop)
                                         : CeilToTick(signal.structural_stop));
   const double risk=(signal.direction>0 ? entry-stop : stop-entry);
   double target=(signal.direction>0 ? entry+TARGET_R*risk : entry-TARGET_R*risk);
   target=(signal.direction>0 ? FloorToTick(target) : CeilToTick(target));
   const double reward=(signal.direction>0 ? target-entry : entry-target);
   if(!IsUsable(entry) || !IsUsable(stop) || !IsUsable(target) ||
      risk<=0.0 || reward<=0.0 ||
      (signal.direction>0 && !(stop<entry && target>entry)) ||
      (signal.direction<0 && !(stop>entry && target<entry)))
      return(false);
   ResetLastError();
   const long stops_level=SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL);
   if(GetLastError()!=0 || stops_level<0)
      return(false);
   const double minimum_distance=(double)stops_level*_Point;
   if(risk+1e-12<minimum_distance || reward+1e-12<minimum_distance)
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
   request.comment="APC002";
   if(!OrderCheck(request,check) || check.retcode!=0)
     {
      PrintFormat("APC002_ORDER_CHECK_REJECT decision=%I64d retcode=%u comment=%s",
                  (long)signal.decision_time,check.retcode,check.comment);
      return(false);
     }
   if(!OrderSend(request,result) || !AcceptedRetcode(result.retcode))
     {
      g_runtime_failed=true;
      PrintFormat("APC002_ORDER_SEND_REJECT decision=%I64d retcode=%u error=%d",
                  (long)signal.decision_time,result.retcode,GetLastError());
      return(false);
     }
   g_entries_accepted++;
   g_daily_entries++;
   PrintFormat("APC002_ENTRY decision=%I64d availability=%I64d direction=%d volume=%.2f entry=%.5f sl=%.5f tp=%.5f close=%.5f atr=%.5f ema=%.5f adx=%.5f",
               (long)signal.decision_time,(long)signal.availability_time,
               signal.direction,volume,entry,stop,target,signal.close,
               signal.atr,signal.ema,signal.adx);
   return(true);
  }

void ExecuteSignal(const SignalDecision &signal,const datetime now)
  {
   PrintFormat("APC002_SIGNAL decision=%I64d availability=%I64d direction=%d close=%.5f impulse_high=%.5f impulse_low=%.5f pullback_high=%.5f pullback_low=%.5f atr=%.5f ema=%.5f adx=%.5f stop=%.5f",
               (long)signal.decision_time,(long)signal.availability_time,
               signal.direction,signal.close,signal.impulse_high,
               signal.impulse_low,signal.pullback_high,signal.pullback_low,
               signal.atr,signal.ema,signal.adx,signal.structural_stop);
   int positions=0;
   int orders=0;
   if(!OwnedPositionCount(positions) || !OwnedOrderCount(orders))
     {
      g_runtime_failed=true;
      g_entry_rejects++;
      Print("APC002_FATAL reason=OWNED_INVENTORY_UNCERTAIN");
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
          InpMagic==5603902 && MathAbs(InpRiskPercent-0.25)<1e-12 &&
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
      Print("APC002_FATAL reason=FROZEN_INPUT_OR_SYMBOL_CONTRACT");
      return(INIT_PARAMETERS_INCORRECT);
     }
   if(!CurrentM15Open(g_last_bar_open))
     {
      g_runtime_failed=true;
      Print("APC002_FATAL reason=INITIAL_M15_CLOCK");
      return(INIT_FAILED);
     }
   if(!EmitD0SeriesProof())
     {
      g_runtime_failed=true;
      Print("APC002_FATAL reason=D0_SERIES_PROOF");
      return(INIT_FAILED);
     }
   long filling_mode=0;
   if(!SymbolInfoInteger(_Symbol,SYMBOL_FILLING_MODE,filling_mode) ||
      (filling_mode&SYMBOL_FILLING_FOK)!=SYMBOL_FILLING_FOK)
     {
      g_runtime_failed=true;
      Print("APC002_FATAL reason=FOK_NOT_SUPPORTED");
      return(INIT_FAILED);
     }
   g_atr_handle=iATR(_Symbol,PERIOD_M15,ATR_PERIOD);
   g_ema_handle=iMA(_Symbol,PERIOD_M15,EMA_PERIOD,0,MODE_EMA,PRICE_CLOSE);
   g_adx_handle=iADX(_Symbol,PERIOD_M15,ADX_PERIOD);
   if(g_atr_handle==INVALID_HANDLE || g_ema_handle==INVALID_HANDLE ||
      g_adx_handle==INVALID_HANDLE)
     {
      g_runtime_failed=true;
      Print("APC002_FATAL reason=INDICATOR_HANDLE");
      return(INIT_FAILED);
     }
   const double equity=AccountInfoDouble(ACCOUNT_EQUITY);
   if(!IsUsable(equity) || equity<=0.0)
     {
      g_runtime_failed=true;
      Print("APC002_FATAL reason=INITIAL_EQUITY");
      return(INIT_FAILED);
     }
   g_daily_day_key=DateKey(TimeCurrent());
   g_daily_start_equity=equity;
   g_peak_equity=equity;
   PrintFormat("APC002_INIT hypothesis=%s variant=%s symbol=%s period=%d",
               InpHypothesisId,InpVariantTag,_Symbol,(int)_Period);
   return(INIT_SUCCEEDED);
  }

void OnDeinit(const int reason)
  {
   if(g_atr_handle!=INVALID_HANDLE)
      IndicatorRelease(g_atr_handle);
   if(g_ema_handle!=INVALID_HANDLE)
      IndicatorRelease(g_ema_handle);
   if(g_adx_handle!=INVALID_HANDLE)
      IndicatorRelease(g_adx_handle);
   PrintFormat("APC002_SUMMARY hypothesis=%s closed_bars=%I64d raw=%I64d long=%I64d short=%I64d entries=%I64d rejects=%I64d closes=%I64d clock_rejects=%I64d invalid=%I64d runtime_failed=%s reason=%d",
               InpHypothesisId,g_closed_bars,g_raw_signals,g_long_signals,
               g_short_signals,g_entries_accepted,g_entry_rejects,
               g_close_requests,g_clock_rejects,g_invalid_bars,
               g_runtime_failed ? "true" : "false",reason);
  }

void OnTick()
  {
   const datetime now=TimeCurrent();
   UpdateRiskLocks(now);
   if(!ManageOwnedPositions(now,false))
      return;

   datetime current_open=0;
   if(!CurrentM15Open(current_open))
     {
      g_runtime_failed=true;
      Print("APC002_FATAL reason=M15_SCHEDULING_CLOCK");
      return;
     }
   if(current_open==g_last_bar_open)
      return;
   if(current_open<g_last_bar_open)
     {
      g_runtime_failed=true;
      Print("APC002_FATAL reason=BAR_CLOCK_REGRESSION");
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
