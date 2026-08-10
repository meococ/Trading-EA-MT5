//+------------------------------------------------------------------+
//| EA_JCDR_PureReversal.mq5                                        |
//| HYP-JCDR-EURUSD-M5-006: pure jump-cluster decay reversal        |
//+------------------------------------------------------------------+
#property strict
#property version   "1.00"
#property description "Untuned EURUSD M5 jump-cluster decay reversal baseline"

input group "--- Frozen research authority ---"
input bool   InpResearchAutoMode=false;
input bool   InpEnableTelemetry=false;
input string InpHypothesisId="HYP-JCDR-EURUSD-M5-006";
input string InpVariantTag="JCDR_PURE_REVERSAL_V1";

input group "--- Frozen execution and risk ---"
input long   InpMagic=5603606;
input double InpRiskPercent=0.25;
input double InpMaxDailyLossPct=3.5;
input double InpMaxAccountDrawdownPct=8.0;
input int    InpMaxTradesPerDay=1;
input int    InpDeviationPoints=20;
input int    InpMaxHoldBars=12;
input int    InpFridayFlattenHour=20;

const string EA_NAME="EA_JCDR_PureReversal";
const string EXPECTED_HYPOTHESIS="HYP-JCDR-EURUSD-M5-006";
const string EXPECTED_VARIANT="JCDR_PURE_REVERSAL_V1";
const string EXPECTED_SYMBOL="EURUSD";

const int    JCDR_SCALE_RETURNS=48;
const int    JCDR_CLUSTER_BARS=15;
const int    JCDR_MIN_JUMPS=3;
const double JCDR_MIN_COHERENCE=0.80;
const double JCDR_MIN_DISPLACEMENT_PIP=4.0;
const double JCDR_JUMP_FLOOR_PIP=1.20;
const double JCDR_JUMP_MULTIPLIER=3.0;
const int    JCDR_DECAY_MAX_BARS=10;
const double JCDR_RETRACE_MIN=0.25;
const double JCDR_RETRACE_MAX=1.00;
const double JCDR_MIN_STOP_PIP=6.0;
const double JCDR_STOP_BUFFER_PIP=0.50;
const double JCDR_TARGET_R=1.50;
const int    JCDR_HISTORY_CAPACITY=128;

const datetime DESIGN_FROM=D'2016.01.04 00:00';
const datetime DESIGN_TO=D'2021.01.01 00:00';

struct JcdrBar
  {
   datetime time;
   double open;
   double high;
   double low;
   double close;
   double ret_pips;
   double scale_pips;
   double jump_threshold_pips;
   int jump_sign;
   bool jump_class_valid;
  };

struct PendingCluster
  {
   bool active;
   datetime peak_time;
   int dominant_sign;
   int jump_count;
   double coherence;
   double anchor;
   double extreme;
   double signed_displacement_pips;
   int bars_after_peak;
  };

struct SignalDecision
  {
   bool fired;
   datetime decision_time;
   datetime availability_time;
   int direction;
   double stop_pips;
   double retracement;
   int cluster_sign;
  };

JcdrBar g_bars[];
PendingCluster g_pending;
datetime g_last_bar_open=0;
datetime g_last_processed_time=0;
int g_consumed_signal_date=0;

int g_daily_day_key=0;
double g_daily_start_equity=0.0;
double g_peak_equity=0.0;
bool g_daily_locked=false;
bool g_drawdown_locked=false;
int g_daily_entries=0;
bool g_runtime_failed=false;

long g_closed_bars=0;
long g_gap_resets=0;
long g_invalid_resets=0;
long g_cluster_peaks=0;
long g_decay_expired=0;
long g_raw_signals=0;
long g_long_signals=0;
long g_short_signals=0;
long g_entries_accepted=0;
long g_entry_rejects=0;
long g_close_requests=0;

bool IsUsable(const double value)
  {
   return(value!=EMPTY_VALUE && MathIsValidNumber(value));
  }

bool CurrentM5Open(datetime &bar_open)
  {
   long raw=0;
   bar_open=0;
   if(!SeriesInfoInteger(_Symbol,PERIOD_M5,SERIES_LASTBAR_DATE,raw) || raw<=0)
      return(false);
   bar_open=(datetime)raw;
   return(true);
  }

double PipSize()
  {
   return((_Digits==3 || _Digits==5) ? 10.0*_Point : _Point);
  }

int DateKey(const datetime stamp)
  {
   MqlDateTime p;
   TimeToStruct(stamp,p);
   return(p.year*10000+p.mon*100+p.day);
  }

void ResetPending()
  {
   ZeroMemory(g_pending);
   g_pending.active=false;
  }

void ResetFormation()
  {
   ArrayResize(g_bars,0);
   ResetPending();
  }

bool ValidOhlc(const double open_price,const double high_price,
               const double low_price,const double close_price)
  {
   if(!IsUsable(open_price) || !IsUsable(high_price) ||
      !IsUsable(low_price) || !IsUsable(close_price))
      return(false);
   return(high_price>=MathMax(open_price,close_price) &&
          low_price<=MathMin(open_price,close_price) && high_price>=low_price);
  }

void AppendBar(const JcdrBar &bar)
  {
   int count=ArraySize(g_bars);
   if(count>=JCDR_HISTORY_CAPACITY)
     {
      for(int i=1;i<count;i++)
         g_bars[i-1]=g_bars[i];
      count--;
      ArrayResize(g_bars,count);
     }
   ArrayResize(g_bars,count+1);
   g_bars[count]=bar;
  }

bool PriorMedianAbs48(double &median_value)
  {
   double values[];
   ArrayResize(values,JCDR_SCALE_RETURNS);
   int found=0;
   for(int i=ArraySize(g_bars)-1;i>=0 && found<JCDR_SCALE_RETURNS;i--)
     {
      if(!IsUsable(g_bars[i].ret_pips))
         continue;
      values[found++]=MathAbs(g_bars[i].ret_pips);
     }
   if(found!=JCDR_SCALE_RETURNS)
      return(false);
   ArraySort(values);
   median_value=(values[23]+values[24])/2.0;
   return(IsUsable(median_value));
  }

bool TryFormCluster(PendingCluster &cluster)
  {
   const int count=ArraySize(g_bars);
   if(count<JCDR_CLUSTER_BARS || !g_bars[count-1].jump_class_valid ||
      g_bars[count-1].jump_sign==0)
      return(false);

   const int first=count-JCDR_CLUSTER_BARS;
   int jump_count=0;
   int up_count=0;
   int down_count=0;
   int first_jump=-1;
   for(int i=first;i<count;i++)
     {
      if(!g_bars[i].jump_class_valid)
         return(false);
      if(g_bars[i].jump_sign!=0)
        {
         if(first_jump<0)
            first_jump=i;
         jump_count++;
         if(g_bars[i].jump_sign>0)
            up_count++;
         else
            down_count++;
        }
     }
   if(jump_count<JCDR_MIN_JUMPS || first_jump<0)
      return(false);

   const int dominant=(up_count>=down_count ? 1 : -1);
   const int dominant_count=MathMax(up_count,down_count);
   const double coherence=(double)dominant_count/(double)jump_count;
   if(coherence<JCDR_MIN_COHERENCE)
      return(false);

   const double pip=PipSize();
   const double anchor=g_bars[first_jump].open;
   const double signed_displacement=dominant*(g_bars[count-1].close-anchor)/pip;
   if(signed_displacement<JCDR_MIN_DISPLACEMENT_PIP)
      return(false);

   double extreme=(dominant>0 ? g_bars[first].high : g_bars[first].low);
   for(int i=first+1;i<count;i++)
     {
      if(dominant>0)
         extreme=MathMax(extreme,g_bars[i].high);
      else
         extreme=MathMin(extreme,g_bars[i].low);
     }

   ZeroMemory(cluster);
   cluster.active=true;
   cluster.peak_time=g_bars[count-1].time;
   cluster.dominant_sign=dominant;
   cluster.jump_count=jump_count;
   cluster.coherence=coherence;
   cluster.anchor=anchor;
   cluster.extreme=extreme;
   cluster.signed_displacement_pips=signed_displacement;
   cluster.bars_after_peak=0;
   return(true);
  }

bool ThreeClosedBarsNoJump()
  {
   const int count=ArraySize(g_bars);
   if(count<3)
      return(false);
   for(int i=count-3;i<count;i++)
     {
      if(!g_bars[i].jump_class_valid || g_bars[i].jump_sign!=0)
         return(false);
     }
   return(true);
  }

double RetracementFraction(const double decision_close)
  {
   const double distance=MathAbs(g_pending.extreme-g_pending.anchor);
   if(!IsUsable(distance) || distance<=0.0)
      return(EMPTY_VALUE);
   if(g_pending.dominant_sign>0)
      return((g_pending.extreme-decision_close)/distance);
   return((decision_close-g_pending.extreme)/distance);
  }

bool ProcessClosedBar(const datetime availability_time,SignalDecision &signal)
  {
   ZeroMemory(signal);
   const datetime bar_time=iTime(_Symbol,PERIOD_M5,1);
   if(bar_time<=0)
     {
      g_invalid_resets++;
      ResetFormation();
      g_last_processed_time=0;
      return(false);
     }
   if(bar_time<DESIGN_FROM || bar_time>=DESIGN_TO || availability_time>=DESIGN_TO)
     {
      ResetFormation();
      g_last_processed_time=0;
      return(false);
     }

   JcdrBar bar;
   ZeroMemory(bar);
   bar.time=bar_time;
   bar.open=iOpen(_Symbol,PERIOD_M5,1);
   bar.high=iHigh(_Symbol,PERIOD_M5,1);
   bar.low=iLow(_Symbol,PERIOD_M5,1);
   bar.close=iClose(_Symbol,PERIOD_M5,1);
   bar.ret_pips=EMPTY_VALUE;
   bar.scale_pips=EMPTY_VALUE;
   bar.jump_threshold_pips=EMPTY_VALUE;
   bar.jump_sign=0;
   bar.jump_class_valid=false;

   if(!ValidOhlc(bar.open,bar.high,bar.low,bar.close))
     {
      g_invalid_resets++;
      ResetFormation();
      g_last_processed_time=bar.time;
      return(false);
     }

   if(g_last_processed_time>0 && (long)(bar.time-g_last_processed_time)!=300)
     {
      g_gap_resets++;
      ResetFormation();
     }

   const int prior_count=ArraySize(g_bars);
   if(prior_count>0)
     {
      bar.ret_pips=(bar.close-g_bars[prior_count-1].close)/PipSize();
      double scale=EMPTY_VALUE;
      if(PriorMedianAbs48(scale))
        {
         bar.scale_pips=scale;
         bar.jump_threshold_pips=MathMax(JCDR_JUMP_FLOOR_PIP,
                                         JCDR_JUMP_MULTIPLIER*scale);
         bar.jump_class_valid=true;
         if(MathAbs(bar.ret_pips)>=bar.jump_threshold_pips)
            bar.jump_sign=(bar.ret_pips>0.0 ? 1 : -1);
        }
     }
   AppendBar(bar);
   g_last_processed_time=bar.time;
   g_closed_bars++;

   PendingCluster new_cluster;
   if(TryFormCluster(new_cluster))
     {
      g_pending=new_cluster;
      g_cluster_peaks++;
      return(false);
     }
   if(!g_pending.active)
      return(false);

   g_pending.bars_after_peak++;
   if(g_pending.bars_after_peak>JCDR_DECAY_MAX_BARS)
     {
      g_decay_expired++;
      ResetPending();
      return(false);
     }
   if(!ThreeClosedBarsNoJump())
      return(false);

   const double retracement=RetracementFraction(bar.close);
   if(!IsUsable(retracement) || retracement<JCDR_RETRACE_MIN ||
      retracement>JCDR_RETRACE_MAX)
      return(false);

   const int date_key=DateKey(bar.time);
   if(date_key==g_consumed_signal_date)
     {
      ResetPending();
      return(false);
     }

   signal.fired=true;
   signal.decision_time=bar.time;
   signal.availability_time=availability_time;
   signal.direction=-g_pending.dominant_sign;
   signal.stop_pips=MathMax(JCDR_MIN_STOP_PIP,
                            MathAbs(g_pending.extreme-g_pending.anchor)/PipSize()+
                            JCDR_STOP_BUFFER_PIP);
   signal.retracement=retracement;
   signal.cluster_sign=g_pending.dominant_sign;
   g_consumed_signal_date=date_key;
   g_raw_signals++;
   if(signal.direction>0)
      g_long_signals++;
   else
      g_short_signals++;
   ResetPending();
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
   return(retcode==TRADE_RETCODE_DONE || retcode==TRADE_RETCODE_DONE_PARTIAL);
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
      if(OrderGetString(ORDER_SYMBOL)==_Symbol && OrderGetInteger(ORDER_MAGIC)==InpMagic)
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
      PrintFormat("JCDR006_CLOSE_REJECT ticket=%I64u retcode=%u error=%d reason=%s",
                  ticket,result.retcode,GetLastError(),reason);
      return(false);
     }
   g_close_requests++;
   return(true);
  }

void CloseAllOwned(const string reason)
  {
   for(int i=PositionsTotal()-1;i>=0;i--)
     {
      const ulong ticket=PositionGetTicket(i);
      if(ticket==0 || !PositionSelectByTicket(ticket))
         continue;
      if(PositionGetString(POSITION_SYMBOL)==_Symbol &&
         PositionGetInteger(POSITION_MAGIC)==InpMagic)
         ClosePositionTicket(ticket,reason);
     }
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
   const bool flatten_time=(now>=DESIGN_TO || p.day_of_week==0 || p.day_of_week==6 ||
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
         ClosePositionTicket(ticket,"JCDR_WEEKEND_OR_END");
         continue;
        }
      const datetime opened=(datetime)PositionGetInteger(POSITION_TIME);
      const int held_bars=iBarShift(_Symbol,PERIOD_M5,opened,false);
      if(held_bars>=InpMaxHoldBars)
         ClosePositionTicket(ticket,"JCDR_TIME_EXIT");
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
   const double raw_distance=signal.stop_pips*PipSize();
   const double stop=(signal.direction>0 ? FloorToTick(entry-raw_distance)
                                         : CeilToTick(entry+raw_distance));
   const double risk=(signal.direction>0 ? entry-stop : stop-entry);
   const double target=(signal.direction>0 ? CeilToTick(entry+JCDR_TARGET_R*risk)
                                           : FloorToTick(entry-JCDR_TARGET_R*risk));
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
   request.comment="JCDR006";
   if(!OrderCheck(request,check) || check.retcode!=0)
     {
      PrintFormat("JCDR006_ORDER_CHECK_REJECT decision=%I64d retcode=%u comment=%s",
                  (long)signal.decision_time,check.retcode,check.comment);
      return(false);
     }
   if(!OrderSend(request,result) || !AcceptedRetcode(result.retcode))
     {
      PrintFormat("JCDR006_ORDER_SEND_REJECT decision=%I64d retcode=%u error=%d",
                  (long)signal.decision_time,result.retcode,GetLastError());
      return(false);
     }
   g_entries_accepted++;
   g_daily_entries++;
   PrintFormat("JCDR006_ENTRY decision=%I64d availability=%I64d direction=%d volume=%.2f entry=%.5f sl=%.5f tp=%.5f stop_pips=%.5f retracement=%.8f",
               (long)signal.decision_time,(long)signal.availability_time,signal.direction,
               volume,entry,stop,target,signal.stop_pips,signal.retracement);
   return(true);
  }

void ExecuteSignal(const SignalDecision &signal,const datetime now)
  {
   PrintFormat("JCDR006_SIGNAL decision=%I64d availability=%I64d direction=%d stop_pips=%.5f retracement=%.8f",
               (long)signal.decision_time,(long)signal.availability_time,
               signal.direction,signal.stop_pips,signal.retracement);
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
   return(_Symbol==EXPECTED_SYMBOL && _Period==PERIOD_M5 &&
          InpResearchAutoMode && !InpEnableTelemetry &&
          InpHypothesisId==EXPECTED_HYPOTHESIS && InpVariantTag==EXPECTED_VARIANT &&
          InpMagic==5603606 && MathAbs(InpRiskPercent-0.25)<1e-12 &&
          MathAbs(InpMaxDailyLossPct-3.5)<1e-12 &&
          MathAbs(InpMaxAccountDrawdownPct-8.0)<1e-12 &&
          InpMaxTradesPerDay==1 && InpDeviationPoints==20 &&
          InpMaxHoldBars==12 && InpFridayFlattenHour==20);
  }

int OnInit()
  {
   if(!ValidateFrozenInputs())
     {
      Print("JCDR006_FATAL reason=FROZEN_INPUT_OR_SYMBOL_CONTRACT");
      return(INIT_PARAMETERS_INCORRECT);
     }
   ResetFormation();
   if(!CurrentM5Open(g_last_bar_open))
     {
      Print("JCDR006_FATAL reason=INITIAL_M5_CLOCK");
      return(INIT_FAILED);
     }
   const double equity=AccountInfoDouble(ACCOUNT_EQUITY);
   if(g_last_bar_open<=0 || !IsUsable(equity) || equity<=0.0)
     {
      Print("JCDR006_FATAL reason=INITIAL_HISTORY_OR_EQUITY");
      return(INIT_FAILED);
     }
   g_daily_day_key=DateKey(TimeCurrent());
   g_daily_start_equity=equity;
   g_peak_equity=equity;
   PrintFormat("JCDR006_INIT hypothesis=%s variant=%s symbol=%s period=%d",
               InpHypothesisId,InpVariantTag,_Symbol,(int)_Period);
   return(INIT_SUCCEEDED);
  }

void OnDeinit(const int reason)
  {
   PrintFormat("JCDR006_SUMMARY hypothesis=%s closed_bars=%I64d clusters=%I64d raw=%I64d long=%I64d short=%I64d entries=%I64d rejects=%I64d closes=%I64d gaps=%I64d invalid=%I64d runtime_failed=%s reason=%d",
               InpHypothesisId,g_closed_bars,g_cluster_peaks,g_raw_signals,
               g_long_signals,g_short_signals,g_entries_accepted,g_entry_rejects,
               g_close_requests,g_gap_resets,g_invalid_resets,
               g_runtime_failed ? "true" : "false",reason);
  }

void OnTick()
  {
   const datetime now=TimeCurrent();
   UpdateRiskLocks(now);
   ManageOwnedPositions(now);

   datetime current_open=0;
   if(!CurrentM5Open(current_open) || current_open==g_last_bar_open)
      return;
   if(current_open<g_last_bar_open)
     {
      g_runtime_failed=true;
      Print("JCDR006_FATAL reason=BAR_CLOCK_REGRESSION");
      return;
     }
   g_last_bar_open=current_open;

   SignalDecision signal;
   if(ProcessClosedBar(current_open,signal) && signal.fired)
      ExecuteSignal(signal,current_open);
  }
//+------------------------------------------------------------------+
