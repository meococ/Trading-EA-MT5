//+------------------------------------------------------------------+
//| EA_KlingerPullback.mq5                                          |
//| HYP-KVO-EURUSD-M15-004: Klinger pullback continuation          |
//+------------------------------------------------------------------+
#property strict
#property version   "1.20"
#property description "Untuned EURUSD M15 Klinger 34/55/13 pullback re-entry continuation"

input group "--- Frozen research authority ---"
input bool   InpResearchAutoMode=false;
input bool   InpEnableTelemetry=false;
input string InpHypothesisId="HYP-KVO-EURUSD-M15-004";
input string InpVariantTag="KVO34_55_13_EMA100_PULLBACK_REENTRY_COMPACT";

input group "--- Frozen execution and risk ---"
input long   InpMagic=5604004;
input double InpRiskPercent=0.25;
input double InpMaxDailyLossPct=3.5;
input double InpMaxAccountDrawdownPct=8.0;
input int    InpMaxTradesPerDay=1;
input int    InpDeviationPoints=20;
input int    InpFridayFlattenHour=20;

const string EA_NAME="EA_KlingerPullback";
const string EXPECTED_HYPOTHESIS="HYP-KVO-EURUSD-M15-004";
const string EXPECTED_VARIANT="KVO34_55_13_EMA100_PULLBACK_REENTRY_COMPACT";
const string EXPECTED_SYMBOL="EURUSD";
const int    ATR_PERIOD=14;
const int    KVO_FAST_PERIOD=34;
const int    KVO_SLOW_PERIOD=55;
const int    KVO_SIGNAL_PERIOD=13;
const int    TREND_EMA_PERIOD=100;
const double STOP_BUFFER_ATR=0.15;
const double TARGET_R=1.50;
const int    MAX_HOLD_BARS=16;
const int    REQUIRED_RATES=4;
const datetime DESIGN_FROM=D'2010.01.04 00:00';
const datetime DESIGN_TO=D'2018.01.01 00:00';

struct SignalDecision
  {
   bool fired;
   datetime decision_time;
   datetime availability_time;
   int direction;
   double close;
   double swing_high;
   double swing_low;
   double atr;
   double kvo;
   double kvo_signal;
   double ema100;
   double structural_stop;
  };

enum KvoArmState
  {
   KVO_IDLE=0,
   KVO_LONG_ARMED=1,
   KVO_SHORT_ARMED=-1
  };

datetime g_last_bar_open=0;
datetime g_last_decision_time=0;
int g_atr_handle=INVALID_HANDLE;

bool g_have_previous_source=false;
double g_previous_sum=0.0;
double g_previous_dm=0.0;
int g_previous_trend=-1;
double g_cm=0.0;
bool g_cm_ready=false;
long g_vf_count=0;
double g_vf_sum34=0.0;
double g_vf_sum55=0.0;
double g_ema34=0.0;
double g_ema55=0.0;
bool g_ema34_ready=false;
bool g_ema55_ready=false;
long g_ko_count=0;
double g_ko_signal_sum=0.0;
double g_ko_signal_ema=0.0;
bool g_ko_signal_ready=false;
long g_close_count=0;
double g_close_sum100=0.0;
double g_close_ema100=0.0;
bool g_close_ema100_ready=false;
double g_previous_ko=0.0;
double g_previous_ko_signal=0.0;
bool g_previous_pair_ready=false;
KvoArmState g_kvo_arm=KVO_IDLE;
datetime g_kvo_last_time=0;

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

bool ReadClosedAtr(double &value)
  {
   value=EMPTY_VALUE;
   if(g_atr_handle==INVALID_HANDLE)
      return(false);
   double data[];
   const int copied=CopyBuffer(g_atr_handle,0,1,1,data);
   if(copied!=1 || !IsUsable(data[0]))
      return(false);
   value=data[0];
   return(true);
  }

bool AdvanceKvoBar(const MqlRates &bar,int &direction,
                   double &ko_value,double &signal_value,double &ema100_value)
  {
   direction=0;
   ko_value=EMPTY_VALUE;
   signal_value=EMPTY_VALUE;
   ema100_value=EMPTY_VALUE;
   if(!ValidRate(bar) || bar.tick_volume<0)
      return(false);

   g_close_count++;
   if(g_close_count<=TREND_EMA_PERIOD)
     {
      g_close_sum100+=bar.close;
      if(g_close_count==TREND_EMA_PERIOD)
        {
         g_close_ema100=g_close_sum100/(double)TREND_EMA_PERIOD;
         g_close_ema100_ready=true;
        }
     }
   else
     {
      const double alpha100=2.0/(TREND_EMA_PERIOD+1.0);
      g_close_ema100=alpha100*bar.close+(1.0-alpha100)*g_close_ema100;
     }

   const double source_sum=bar.high+bar.low+bar.close;
   const double dm=bar.high-bar.low;
   if(!IsUsable(source_sum) || !IsUsable(dm) || dm<0.0)
      return(false);
   if(!g_have_previous_source)
     {
      g_have_previous_source=true;
      g_previous_sum=source_sum;
      g_previous_dm=dm;
      return(true);
     }

   const int trend=(source_sum>g_previous_sum ? 1 : -1);
   bool vf_defined=false;
   double vf=0.0;
   if(!g_cm_ready)
     {
      const double seed_cm=g_previous_dm+dm;
      if(seed_cm>0.0)
        {
         g_cm=seed_cm;
         g_cm_ready=true;
         vf=(double)bar.tick_volume*2.0*(dm/g_cm-1.0)*(double)trend*100.0;
         vf_defined=true;
        }
     }
   else
     {
      g_cm=(trend==g_previous_trend ? g_cm+dm : g_previous_dm+dm);
      if(!IsUsable(g_cm) || g_cm<0.0)
         return(false);
      vf=(g_cm==0.0 ? 0.0
                    : (double)bar.tick_volume*2.0*(dm/g_cm-1.0)*(double)trend*100.0);
      vf_defined=true;
     }

   g_previous_sum=source_sum;
   g_previous_dm=dm;
   g_previous_trend=trend;
   if(!vf_defined)
      return(true);
   if(!IsUsable(vf))
      return(false);

   g_vf_count++;
   if(g_vf_count<=KVO_FAST_PERIOD)
     {
      g_vf_sum34+=vf;
      if(g_vf_count==KVO_FAST_PERIOD)
        {
         g_ema34=g_vf_sum34/(double)KVO_FAST_PERIOD;
         g_ema34_ready=true;
        }
     }
   else
     {
      const double alpha34=2.0/(KVO_FAST_PERIOD+1.0);
      g_ema34=alpha34*vf+(1.0-alpha34)*g_ema34;
     }
   if(g_vf_count<=KVO_SLOW_PERIOD)
     {
      g_vf_sum55+=vf;
      if(g_vf_count==KVO_SLOW_PERIOD)
        {
         g_ema55=g_vf_sum55/(double)KVO_SLOW_PERIOD;
         g_ema55_ready=true;
        }
     }
   else
     {
      const double alpha55=2.0/(KVO_SLOW_PERIOD+1.0);
      g_ema55=alpha55*vf+(1.0-alpha55)*g_ema55;
     }
   if(!g_ema34_ready || !g_ema55_ready)
      return(true);

   const double ko=g_ema34-g_ema55;
   if(!IsUsable(ko))
      return(false);
   g_ko_count++;
   if(g_ko_count<=KVO_SIGNAL_PERIOD)
     {
      g_ko_signal_sum+=ko;
      if(g_ko_count==KVO_SIGNAL_PERIOD)
        {
         g_ko_signal_ema=g_ko_signal_sum/(double)KVO_SIGNAL_PERIOD;
         g_ko_signal_ready=true;
        }
     }
   else
     {
      const double alpha13=2.0/(KVO_SIGNAL_PERIOD+1.0);
      g_ko_signal_ema=alpha13*ko+(1.0-alpha13)*g_ko_signal_ema;
     }
   if(!g_ko_signal_ready || !g_close_ema100_ready)
      return(true);

   ko_value=ko;
   signal_value=g_ko_signal_ema;
   ema100_value=g_close_ema100;
   bool consumed_state=false;
   if(g_kvo_arm==KVO_LONG_ARMED)
     {
      const bool context=(ko<=0.0 && bar.close>g_close_ema100);
      if(g_previous_pair_ready && g_previous_ko<=g_previous_ko_signal &&
         ko>g_ko_signal_ema && context)
        {
         direction=1;
         g_kvo_arm=KVO_IDLE;
         consumed_state=true;
        }
      else if(!context)
        {
         g_kvo_arm=KVO_IDLE;
         consumed_state=true;
        }
     }
   else if(g_kvo_arm==KVO_SHORT_ARMED)
     {
      const bool context=(ko>=0.0 && bar.close<g_close_ema100);
      if(g_previous_pair_ready && g_previous_ko>=g_previous_ko_signal &&
         ko<g_ko_signal_ema && context)
        {
         direction=-1;
         g_kvo_arm=KVO_IDLE;
         consumed_state=true;
        }
      else if(!context)
        {
         g_kvo_arm=KVO_IDLE;
         consumed_state=true;
        }
     }
   if(direction==0 && !consumed_state && g_kvo_arm==KVO_IDLE)
     {
      if(ko<0.0 && bar.close>g_close_ema100)
         g_kvo_arm=KVO_LONG_ARMED;
      else if(ko>0.0 && bar.close<g_close_ema100)
         g_kvo_arm=KVO_SHORT_ARMED;
     }

   g_previous_ko=ko;
   g_previous_ko_signal=g_ko_signal_ema;
   g_previous_pair_ready=true;
   return(true);
  }

bool PreloadKvoState()
  {
   long synchronized=0;
   long series_count=0;
   long first_epoch=0;
   long current_epoch=0;
   if(!ReadSeriesInteger(PERIOD_M15,SERIES_SYNCHRONIZED,synchronized) ||
      !ReadSeriesInteger(PERIOD_M15,SERIES_BARS_COUNT,series_count) ||
      !ReadSeriesInteger(PERIOD_M15,SERIES_FIRSTDATE,first_epoch) ||
      !ReadSeriesInteger(PERIOD_M15,SERIES_LASTBAR_DATE,current_epoch) ||
      synchronized!=1 || series_count<300 || first_epoch<=0 || current_epoch<=first_epoch)
      return(false);
   const int available=Bars(_Symbol,PERIOD_M15);
   if(available<300 || (long)available!=series_count)
      return(false);
   const int requested=available-1;
   MqlRates history[];
   ArraySetAsSeries(history,false);
   const int copied=CopyRates(_Symbol,PERIOD_M15,1,requested,history);
   if(copied!=requested || copied<300 || history[0].time!=(datetime)first_epoch)
      return(false);
   const datetime expected_last=iTime(_Symbol,PERIOD_M15,1);
   if(expected_last<=0 || history[copied-1].time!=expected_last ||
      expected_last>=current_epoch)
      return(false);
   for(int i=1;i<copied;i++)
      if(history[i].time<=history[i-1].time)
         return(false);
   int ignored_direction=0;
   double ignored_ko=0.0,ignored_signal=0.0,ignored_ema=0.0;
   for(int i=0;i<copied;i++)
     {
      if(!AdvanceKvoBar(history[i],ignored_direction,ignored_ko,
                        ignored_signal,ignored_ema))
         return(false);
     }
   g_kvo_last_time=history[copied-1].time;
   const bool ready=(g_cm_ready && g_ema34_ready && g_ema55_ready &&
                     g_ko_signal_ready && g_close_ema100_ready && g_kvo_last_time>0);
   PrintFormat("KVO004_PRELOAD synchronized=%I64d requested=%d copied=%d first=%I64d last=%I64d current=%I64d ready=%s",
               synchronized,requested,copied,(long)history[0].time,
               (long)g_kvo_last_time,current_epoch,ready ? "true" : "false");
   return(ready);
  }

bool ProcessClosedBar(const datetime availability_time,SignalDecision &signal)
  {
   ZeroMemory(signal);
   MqlRates rates[];
   if(!LoadClosedRates(rates))
     {
      g_invalid_bars++;
      g_runtime_failed=true;
       PrintFormat("KVO004_FATAL reason=CLOSED_RATE_LOAD availability=%I64d",
                  (long)availability_time);
      return(false);
     }
    const int release=ArraySize(rates)-1;
    const datetime decision_time=rates[release].time;
    if(decision_time<=0 || decision_time==g_last_decision_time)
       return(false);
    if(decision_time<g_kvo_last_time)
      {
       g_invalid_bars++;
       g_runtime_failed=true;
       PrintFormat("KVO004_FATAL reason=KVO_CLOCK_REGRESSION decision=%I64d last=%I64d",
                   (long)decision_time,(long)g_kvo_last_time);
       return(false);
      }
    g_last_decision_time=decision_time;
    g_closed_bars++;
    int direction=0;
    double ko=0.0,kvo_signal=0.0,ema100=0.0;
    if(decision_time>g_kvo_last_time)
      {
       if(!AdvanceKvoBar(rates[release],direction,ko,kvo_signal,ema100))
         {
          g_invalid_bars++;
          g_runtime_failed=true;
          PrintFormat("KVO004_FATAL reason=KVO_STATE decision=%I64d",(long)decision_time);
          return(false);
         }
       g_kvo_last_time=decision_time;
      }
    if(decision_time<DESIGN_FROM || decision_time>=DESIGN_TO || availability_time>=DESIGN_TO)
       return(false);
    if(direction==0)
       return(false);
    g_raw_signals++;
    if(direction>0)
       g_long_signals++;
    else
       g_short_signals++;
    if((long)(availability_time-decision_time)!=900)
      {
       g_clock_rejects++;
       return(false);
      }

    double atr_release=0.0;
    if(!ReadClosedAtr(atr_release) || atr_release<=0.0)
      {
       g_invalid_bars++;
       g_runtime_failed=true;
       PrintFormat("KVO004_FATAL reason=ATR_LOAD decision=%I64d",
                   (long)decision_time);
       return(false);
      }
    const double swing_low=MathMin(rates[release].low,
                                   MathMin(rates[release-1].low,rates[release-2].low));
    const double swing_high=MathMax(rates[release].high,
                                    MathMax(rates[release-1].high,rates[release-2].high));
    const double stop=(direction>0
                       ? swing_low-STOP_BUFFER_ATR*atr_release
                       : swing_high+STOP_BUFFER_ATR*atr_release);
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
    signal.swing_high=swing_high;
    signal.swing_low=swing_low;
    signal.atr=atr_release;
    signal.kvo=ko;
    signal.kvo_signal=kvo_signal;
    signal.ema100=ema100;
    signal.structural_stop=stop;
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
       PrintFormat("KVO004_FATAL reason=CLOSE_POSITION_SELECT ticket=%I64u",ticket);
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
       PrintFormat("KVO004_FATAL reason=CLOSE_POSITION_PROPERTIES ticket=%I64u error=%d type=%d volume=%.8f",
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
       PrintFormat("KVO004_CLOSE_REJECT ticket=%I64u retcode=%u error=%d reason=%s",
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
         PrintFormat("KVO004_FATAL reason=POSITION_ENUMERATION index=%d",i);
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
         PrintFormat("KVO004_FATAL reason=POSITION_PROPERTIES ticket=%I64u",ticket);
         return(false);
        }
      if(symbol!=_Symbol || magic!=InpMagic)
         continue;
      if(flatten_time)
        {
          if(!ClosePositionTicket(ticket,"KVO_WEEKEND_OR_END"))
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
             PrintFormat("KVO004_FATAL reason=ENTRY_BAR_RECOVERY ticket=%I64u",ticket);
            return(false);
           }
          if(shift>=MAX_HOLD_BARS && !ClosePositionTicket(ticket,"KVO_TIME_EXIT"))
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
    request.comment="KVO004";
   if(!OrderCheck(request,check) || check.retcode!=0)
     {
      return(false);
     }
   ResetLastError();
   const bool send_ok=OrderSend(request,result);
   const int send_error=GetLastError();
   const bool definitive_no_fill=(result.retcode==TRADE_RETCODE_MARKET_CLOSED &&
                                  result.order==0 && result.deal==0);
   if(!send_ok && !definitive_no_fill)
     {
      g_runtime_failed=true;
      PrintFormat("KVO004_FATAL reason=ENTRY_SEND_TRANSPORT decision=%I64d retcode=%u error=%d order=%I64u deal=%I64u",
                  (long)signal.decision_time,result.retcode,send_error,
                  result.order,result.deal);
      return(false);
     }
   if(!AcceptedRetcode(result.retcode))
     {
      if(!definitive_no_fill)
        {
         g_runtime_failed=true;
         PrintFormat("KVO004_FATAL reason=ENTRY_REJECT_UNKNOWN decision=%I64d retcode=%u error=%d order=%I64u deal=%I64u",
                     (long)signal.decision_time,result.retcode,send_error,
                     result.order,result.deal);
         return(false);
        }
      int positions=0;
      int orders=0;
      if(!OwnedPositionCount(positions) || !OwnedOrderCount(orders) ||
         positions!=0 || orders!=0)
        {
         g_runtime_failed=true;
         PrintFormat("KVO004_FATAL reason=ENTRY_REJECT_AMBIGUOUS decision=%I64d retcode=%u error=%d positions=%d orders=%d",
                     (long)signal.decision_time,result.retcode,send_error,
                     positions,orders);
         return(false);
        }
      return(false);
     }
   g_entries_accepted++;
   g_daily_entries++;
   return(true);
  }

void ExecuteSignal(const SignalDecision &signal,const datetime now)
  {
   int positions=0;
   int orders=0;
   if(!OwnedPositionCount(positions) || !OwnedOrderCount(orders))
     {
      g_runtime_failed=true;
      g_entry_rejects++;
       Print("KVO004_FATAL reason=OWNED_INVENTORY_UNCERTAIN");
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
           InpMagic==5604004 && MathAbs(InpRiskPercent-0.25)<1e-12 &&
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
       Print("KVO004_FATAL reason=FROZEN_INPUT_OR_SYMBOL_CONTRACT");
      return(INIT_PARAMETERS_INCORRECT);
     }
   if(!CurrentM15Open(g_last_bar_open))
     {
      g_runtime_failed=true;
       Print("KVO004_FATAL reason=INITIAL_M15_CLOCK");
      return(INIT_FAILED);
     }
   if(!EmitD0SeriesProof())
     {
      g_runtime_failed=true;
       Print("KVO004_FATAL reason=D0_SERIES_PROOF");
      return(INIT_FAILED);
     }
   long filling_mode=0;
   if(!SymbolInfoInteger(_Symbol,SYMBOL_FILLING_MODE,filling_mode) ||
      (filling_mode&SYMBOL_FILLING_FOK)!=SYMBOL_FILLING_FOK)
     {
      g_runtime_failed=true;
       Print("KVO004_FATAL reason=FOK_NOT_SUPPORTED");
      return(INIT_FAILED);
     }
    g_atr_handle=iATR(_Symbol,PERIOD_M15,ATR_PERIOD);
    if(g_atr_handle==INVALID_HANDLE)
      {
       g_runtime_failed=true;
       Print("KVO004_FATAL reason=INDICATOR_HANDLE");
       return(INIT_FAILED);
      }
    if(!PreloadKvoState())
      {
       g_runtime_failed=true;
       Print("KVO004_FATAL reason=KVO_PRELOAD");
       return(INIT_FAILED);
      }
   const double equity=AccountInfoDouble(ACCOUNT_EQUITY);
   if(!IsUsable(equity) || equity<=0.0)
     {
      g_runtime_failed=true;
       Print("KVO004_FATAL reason=INITIAL_EQUITY");
      return(INIT_FAILED);
     }
   g_daily_day_key=DateKey(TimeCurrent());
   g_daily_start_equity=equity;
   g_peak_equity=equity;
    PrintFormat("KVO004_INIT hypothesis=%s variant=%s symbol=%s period=%d preloaded_through=%I64d",
                InpHypothesisId,InpVariantTag,_Symbol,(int)_Period,(long)g_kvo_last_time);
   return(INIT_SUCCEEDED);
  }

void OnDeinit(const int reason)
  {
   if(g_atr_handle!=INVALID_HANDLE)
      IndicatorRelease(g_atr_handle);
    PrintFormat("KVO004_SUMMARY hypothesis=%s closed_bars=%I64d raw=%I64d long=%I64d short=%I64d entries=%I64d rejects=%I64d closes=%I64d clock_rejects=%I64d invalid=%I64d runtime_failed=%s reason=%d",
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
       Print("KVO004_FATAL reason=M15_SCHEDULING_CLOCK");
      return;
     }
   if(current_open==g_last_bar_open)
      return;
   if(current_open<g_last_bar_open)
     {
      g_runtime_failed=true;
       Print("KVO004_FATAL reason=BAR_CLOCK_REGRESSION");
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
