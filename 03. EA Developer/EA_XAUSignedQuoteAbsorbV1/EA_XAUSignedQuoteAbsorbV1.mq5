//+------------------------------------------------------------------+
//| EA_XAUSignedQuoteAbsorbV1.mq5                              |
//| HYP-XAU-SIGNED-QUOTE-ABSORB-002 - frozen economic baseline           |
//+------------------------------------------------------------------+
#property copyright "AlphaFactory research"
#property version   "2.00"
#property strict
#property description "Frozen signed XAU quote absorption economic baseline"

input double InpRiskPercent=0.20;
input int    InpTimeStopMinutes=7;
input ulong  InpMagic=260812002;
input int    InpDeviationPoints=0;

const string HYPOTHESIS_ID="HYP-XAU-SIGNED-QUOTE-ABSORB-002";
const string EXPECTED_SYMBOL="AFD_XAUUSD_DUKA_V3";
const int    WINDOW_MILLISECONDS=30000;
const int    MIN_NET_SIGNED_PRESSURE=8;
const double ABSORPTION_MID_ATR=0.12;
const int    ATR_PERIOD=14;
const int    WARMUP_M1_BARS=500;
const double MAX_SPREAD_USD=0.30;
const int    MIN_DESIGN_SIGNALS=350;
const int    MIN_YEAR_SIGNALS=40;
const int    MIN_SIGNAL_MEDIAN_ABS_PRESSURE=9;
const int    QUEUE_CAPACITY=262144;
const double STOP_ATR_MULTIPLIER=1.70;
const double MIN_STOP_USD=0.35;
const double MAX_STOP_USD=1.60;
const double TARGET_R_MULTIPLIER=1.25;
const int    FRIDAY_FLAT_HOUR=21;

long   g_queue_time_msc[];
double g_queue_mid[];
int    g_queue_net_delta[];
int    g_queue_event_count[];
int    g_queue_head=0;
int    g_queue_count=0;
int    g_window_net_pressure=0;
int    g_window_events=0;
double g_mid_at_or_before_window=0.0;
long   g_mid_at_or_before_window_time=0;

bool   g_have_previous=false;
long   g_previous_time_msc=0;
double g_previous_bid=0.0;
double g_previous_ask=0.0;
double g_previous_mid=0.0;
datetime g_current_minute_start=0;
bool   g_current_minute_has_valid_quote=false;
int    g_atr_handle=INVALID_HANDLE;

long g_total_ticks=0;
long g_valid_quote_ticks=0;
long g_invalid_quote_ticks=0;
long g_reverse_time_ticks=0;
long g_duplicate_time_ticks=0;
long g_exact_duplicate_quotes=0;
long g_completed_valid_m1=0;
long g_gap_minutes=0;
long g_signal_count=0;
long g_long_signals=0;
long g_short_signals=0;
long g_year_signals[4];
int  g_signal_abs_pressure[];
bool g_queue_overflow=false;
long g_entries_accepted=0;
long g_position_skips=0;
long g_volume_rejects=0;
long g_geometry_rejects=0;
long g_order_check_rejects=0;
long g_order_send_rejects=0;
long g_close_requests=0;
long g_close_rejects=0;
long g_time_exit_requests=0;
long g_weekend_exit_requests=0;
long g_sl_exits=0;
long g_tp_exits=0;
long g_expert_exits=0;

bool QuoteValid(const MqlTick &tick)
  {
   return tick.time_msc>0 && MathIsValidNumber(tick.bid) &&
          MathIsValidNumber(tick.ask) && tick.bid>0.0 &&
          tick.ask>tick.bid;
  }

int SignedStep(const double delta)
  {
   if(delta>0.0)
      return 1;
   if(delta<0.0)
      return -1;
   return 0;
  }

void ClearQuoteQueue()
  {
   g_queue_head=0;
   g_queue_count=0;
   g_window_net_pressure=0;
   g_window_events=0;
   g_mid_at_or_before_window=0.0;
   g_mid_at_or_before_window_time=0;
  }

bool AppendQuote(const long time_msc,
                 const double mid,
                 const int net_delta,
                 const int event_count)
  {
   if(g_queue_count>=QUEUE_CAPACITY)
     {
      g_queue_overflow=true;
      return false;
     }
   int index=(g_queue_head+g_queue_count)%QUEUE_CAPACITY;
   g_queue_time_msc[index]=time_msc;
   g_queue_mid[index]=mid;
   g_queue_net_delta[index]=net_delta;
   g_queue_event_count[index]=event_count;
   g_queue_count++;
   g_window_net_pressure+=net_delta;
   g_window_events+=event_count;
   return true;
  }

void PruneThrough(const long cutoff_msc)
  {
   while(g_queue_count>0)
     {
      int index=g_queue_head;
      if(g_queue_time_msc[index]>cutoff_msc)
         break;
      g_mid_at_or_before_window=g_queue_mid[index];
      g_mid_at_or_before_window_time=g_queue_time_msc[index];
      g_window_net_pressure-=g_queue_net_delta[index];
      g_window_events-=g_queue_event_count[index];
      g_queue_head=(g_queue_head+1)%QUEUE_CAPACITY;
      g_queue_count--;
     }
  }

bool IsEntrySession(const datetime decision_time)
  {
   MqlDateTime stamp;
   if(!TimeToStruct(decision_time,stamp))
      return false;
   if(stamp.day_of_week<1 || stamp.day_of_week>5)
      return false;
   if(stamp.hour<1 || stamp.hour>=21)
      return false;
   if(stamp.day_of_week==5 && stamp.hour>=18)
      return false;
   return true;
  }

int DesignYearIndex(const datetime decision_time)
  {
   MqlDateTime stamp;
   if(!TimeToStruct(decision_time,stamp))
      return -1;
   if(stamp.year<2018 || stamp.year>2021)
      return -1;
   return stamp.year-2018;
  }

bool ReadClosedAtr(double &atr)
  {
   double values[1];
   ResetLastError();
   if(CopyBuffer(g_atr_handle,0,1,1,values)!=1 ||
      !MathIsValidNumber(values[0]) || values[0]<=0.0)
      return false;
   atr=values[0];
   return true;
  }

bool IsUsable(const double value)
  {
   return MathIsValidNumber(value) && value>0.0;
  }

int VolumeDigits(const double step)
  {
   if(step>=1.0)
      return 0;
   int digits=0;
   double scaled=step;
   while(digits<8 && MathAbs(scaled-MathRound(scaled))>1e-9)
     {
      scaled*=10.0;
      digits++;
     }
   return digits;
  }

double FloorToTick(const double price)
  {
   double tick_size=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);
   if(!IsUsable(tick_size))
      tick_size=_Point;
   return NormalizeDouble(MathFloor(price/tick_size+1e-9)*tick_size,_Digits);
  }

double CeilToTick(const double price)
  {
   double tick_size=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);
   if(!IsUsable(tick_size))
      tick_size=_Point;
   return NormalizeDouble(MathCeil(price/tick_size-1e-9)*tick_size,_Digits);
  }

ENUM_ORDER_TYPE_FILLING ResolveFilling()
  {
   return ORDER_FILLING_FOK;
  }

bool AcceptedRetcode(const uint retcode)
  {
   return retcode==TRADE_RETCODE_DONE || retcode==TRADE_RETCODE_DONE_PARTIAL;
  }

bool OwnedPositionCount(int &count)
  {
   count=0;
   for(int i=PositionsTotal()-1;i>=0;i--)
     {
      const ulong ticket=PositionGetTicket(i);
      if(ticket==0 || !PositionSelectByTicket(ticket))
         return false;
      ResetLastError();
      const string symbol=PositionGetString(POSITION_SYMBOL);
      const long magic=PositionGetInteger(POSITION_MAGIC);
      if(GetLastError()!=0)
         return false;
      if(symbol==_Symbol && magic==(long)InpMagic)
         count++;
     }
   return true;
  }

bool CalculateVolume(const ENUM_ORDER_TYPE order_type,
                     const double entry,
                     const double stop,
                     double &volume)
  {
   volume=0.0;
   double one_lot_profit=0.0;
   if(!OrderCalcProfit(order_type,_Symbol,1.0,entry,stop,one_lot_profit) ||
      !MathIsValidNumber(one_lot_profit) || one_lot_profit>=0.0)
      return false;
   const double balance=AccountInfoDouble(ACCOUNT_BALANCE);
   const double risk_budget=balance*InpRiskPercent/100.0;
   const double raw_volume=risk_budget/MathAbs(one_lot_profit);
   const double minimum=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN);
   const double maximum=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX);
   const double step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);
   if(!IsUsable(balance) || !IsUsable(risk_budget) || !IsUsable(raw_volume) ||
      !IsUsable(minimum) || !IsUsable(maximum) || !IsUsable(step) || maximum<minimum)
      return false;
   double sized=MathFloor(raw_volume/step+1e-9)*step;
   sized=MathMin(sized,maximum);
   sized=NormalizeDouble(sized,VolumeDigits(step));
   if(sized<minimum-1e-9)
      return false;
   double required_margin=0.0;
   if(!OrderCalcMargin(order_type,_Symbol,sized,entry,required_margin) ||
      !MathIsValidNumber(required_margin) || required_margin<0.0 ||
      required_margin>AccountInfoDouble(ACCOUNT_MARGIN_FREE))
      return false;
   volume=sized;
   return true;
  }

bool CloseOwnedPosition(const ulong ticket,const string reason)
  {
   if(ticket==0 || !PositionSelectByTicket(ticket))
      return false;
   const long position_type=PositionGetInteger(POSITION_TYPE);
   const double volume=PositionGetDouble(POSITION_VOLUME);
   MqlTick tick;
   if((position_type!=POSITION_TYPE_BUY && position_type!=POSITION_TYPE_SELL) ||
      !IsUsable(volume) || !SymbolInfoTick(_Symbol,tick) || !QuoteValid(tick))
      return false;
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
   ResetLastError();
   if(!OrderSend(request,result) || !AcceptedRetcode(result.retcode))
     {
      g_close_rejects++;
      return false;
     }
   g_close_requests++;
   return true;
  }

void ManageOwnedPositions(const datetime now)
  {
   MqlDateTime stamp;
   if(!TimeToStruct(now,stamp))
      return;
   const bool weekend_flat=(stamp.day_of_week==0 || stamp.day_of_week==6 ||
                            (stamp.day_of_week==5 && stamp.hour>=FRIDAY_FLAT_HOUR));
   for(int i=PositionsTotal()-1;i>=0;i--)
     {
      const ulong ticket=PositionGetTicket(i);
      if(ticket==0 || !PositionSelectByTicket(ticket))
         continue;
      if(PositionGetString(POSITION_SYMBOL)!=_Symbol ||
         PositionGetInteger(POSITION_MAGIC)!=(long)InpMagic)
         continue;
      const datetime opened=(datetime)PositionGetInteger(POSITION_TIME);
      const bool time_exit=(opened>0 && now>=opened+InpTimeStopMinutes*60);
      if(!weekend_flat && !time_exit)
         continue;
      if(CloseOwnedPosition(ticket,weekend_flat ? "SQA_WEEKEND" : "SQA_TIME"))
        {
         if(weekend_flat)
            g_weekend_exit_requests++;
         else
            g_time_exit_requests++;
        }
     }
  }

bool SubmitEntry(const bool is_long,
                 const MqlTick &entry_tick,
                 const double atr,
                 const datetime decision_time)
  {
   int positions=0;
   if(!OwnedPositionCount(positions))
     {
      g_order_check_rejects++;
      return false;
     }
   if(positions>0)
     {
      g_position_skips++;
      return false;
     }
   const double stop_distance=MathMax(MIN_STOP_USD,
                                      MathMin(MAX_STOP_USD,STOP_ATR_MULTIPLIER*atr));
   const ENUM_ORDER_TYPE order_type=(is_long ? ORDER_TYPE_BUY : ORDER_TYPE_SELL);
   const double entry=(is_long ? entry_tick.ask : entry_tick.bid);
   const double stop=(is_long ? FloorToTick(entry-stop_distance)
                              : CeilToTick(entry+stop_distance));
   const double actual_risk=(is_long ? entry-stop : stop-entry);
   const double target=(is_long ? CeilToTick(entry+TARGET_R_MULTIPLIER*actual_risk)
                                : FloorToTick(entry-TARGET_R_MULTIPLIER*actual_risk));
   long stops_level=0;
   if(!IsUsable(entry) || !IsUsable(stop) || !IsUsable(target) || actual_risk<=0.0 ||
      !SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL,stops_level) || stops_level<0 ||
      actual_risk+1e-12<(double)stops_level*_Point ||
      MathAbs(target-entry)+1e-12<(double)stops_level*_Point)
     {
      g_geometry_rejects++;
      return false;
     }
   double volume=0.0;
   if(!CalculateVolume(order_type,entry,stop,volume))
     {
      g_volume_rejects++;
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
   request.magic=InpMagic;
   request.volume=volume;
   request.type=order_type;
   request.price=entry;
   request.sl=stop;
   request.tp=target;
   request.deviation=InpDeviationPoints;
   request.type_filling=ResolveFilling();
   request.comment="SQA002";
   ResetLastError();
   const bool check_ok=OrderCheck(request,check);
   const int check_error=GetLastError();
   if(!check_ok || check_error!=0 || check.retcode!=0)
     {
      g_order_check_rejects++;
      if(g_order_check_rejects<=5)
         PrintFormat("SQA_ORDER_CHECK_REJECT decision=%I64d error=%d retcode=%u comment=%s",
                     (long)decision_time,check_error,check.retcode,check.comment);
      return false;
     }
   ResetLastError();
   const bool sent=OrderSend(request,result);
   const int send_error=GetLastError();
   if(!sent || send_error!=0 || !AcceptedRetcode(result.retcode))
     {
      g_order_send_rejects++;
      if(g_order_send_rejects<=5)
         PrintFormat("SQA_ORDER_SEND_REJECT decision=%I64d error=%d retcode=%u comment=%s",
                     (long)decision_time,send_error,result.retcode,result.comment);
      return false;
     }
   g_entries_accepted++;
   return true;
  }

void RegisterSignal(const bool is_long,
                    const datetime decision_time,
                    const int net_pressure,
                    const int events,
                    const double mid_move,
                    const double atr,
                    const double spread)
  {
   int size=ArraySize(g_signal_abs_pressure);
   if(ArrayResize(g_signal_abs_pressure,size+1)!=size+1)
     {
      g_queue_overflow=true;
      return;
     }
   g_signal_abs_pressure[size]=(int)MathAbs(net_pressure);
   g_signal_count++;
   if(is_long)
      g_long_signals++;
   else
      g_short_signals++;
   int year_index=DesignYearIndex(decision_time);
   if(year_index>=0)
      g_year_signals[year_index]++;
   // Per-signal journal emission is deliberately disabled in V2. The V1
   // source-gate filled the bounded journal before the final summary.
  }

void EvaluateClosedMinute(const datetime decision_time,
                          const MqlTick &entry_tick)
  {
   g_completed_valid_m1++;
   if(g_completed_valid_m1<WARMUP_M1_BARS || !IsEntrySession(decision_time))
      return;

   long boundary_msc=(long)decision_time*1000;
   long window_start_msc=boundary_msc-WINDOW_MILLISECONDS;
   // Frozen interval is (decision-30s, decision). Ticks exactly on the left
   // boundary establish the starting mid but do not add a signed event.
   PruneThrough(window_start_msc);
   if(g_mid_at_or_before_window_time<=0 || g_previous_time_msc>=boundary_msc ||
      g_previous_time_msc<=window_start_msc || g_window_events<MIN_NET_SIGNED_PRESSURE)
      return;

   double atr=0.0;
   if(!ReadClosedAtr(atr))
      return;
   double mid_move=g_previous_mid-g_mid_at_or_before_window;
   double spread=entry_tick.ask-entry_tick.bid;
   if(!MathIsValidNumber(spread) || spread<=0.0 || spread>MAX_SPREAD_USD)
      return;

   bool long_absorption=(g_window_net_pressure<=-MIN_NET_SIGNED_PRESSURE &&
                         mid_move>=-ABSORPTION_MID_ATR*atr);
   bool short_absorption=(g_window_net_pressure>=MIN_NET_SIGNED_PRESSURE &&
                          mid_move<=ABSORPTION_MID_ATR*atr);
   if(long_absorption==short_absorption)
      return;
   RegisterSignal(long_absorption,decision_time,g_window_net_pressure,
                  g_window_events,mid_move,atr,spread);
   SubmitEntry(long_absorption,entry_tick,atr,decision_time);
  }

void ProcessValidTick(const MqlTick &tick)
  {
   datetime minute_start=(datetime)(((long)tick.time/60)*60);
   if(g_current_minute_start==0)
     {
      g_current_minute_start=minute_start;
      g_current_minute_has_valid_quote=true;
     }
   else if(minute_start>g_current_minute_start)
     {
      long elapsed_minutes=((long)minute_start-(long)g_current_minute_start)/60;
      if(elapsed_minutes==1 && g_current_minute_has_valid_quote)
         EvaluateClosedMinute(minute_start,tick);
      else
        {
         if(elapsed_minutes>1)
            g_gap_minutes+=elapsed_minutes-1;
         ClearQuoteQueue();
         g_have_previous=false;
        }
      g_current_minute_start=minute_start;
      g_current_minute_has_valid_quote=true;
     }
   else if(minute_start<g_current_minute_start)
     {
      g_reverse_time_ticks++;
      return;
     }

   double mid=(tick.bid+tick.ask)*0.5;
   int net_delta=0;
   int event_count=0;
   if(g_have_previous)
     {
      if(tick.time_msc<g_previous_time_msc)
        {
         g_reverse_time_ticks++;
         return;
        }
      if(tick.time_msc==g_previous_time_msc)
         g_duplicate_time_ticks++;

      int bid_step=SignedStep(tick.bid-g_previous_bid);
      int ask_step=SignedStep(tick.ask-g_previous_ask);
      event_count=(bid_step!=0 ? 1 : 0)+(ask_step!=0 ? 1 : 0);
      if(event_count==0)
         g_exact_duplicate_quotes++;
      // BidPressure - AskPressure = sign(deltaBid) + sign(deltaAsk).
      net_delta=bid_step+ask_step;
     }
   if(!AppendQuote(tick.time_msc,mid,net_delta,event_count))
      return;
   g_previous_time_msc=tick.time_msc;
   g_previous_bid=tick.bid;
   g_previous_ask=tick.ask;
   g_previous_mid=mid;
   g_have_previous=true;
  }

int MedianAbsPressure()
  {
   int size=ArraySize(g_signal_abs_pressure);
   if(size<=0)
      return 0;
   ArraySort(g_signal_abs_pressure);
   if((size%2)==1)
      return g_signal_abs_pressure[size/2];
   return (g_signal_abs_pressure[size/2-1]+g_signal_abs_pressure[size/2])/2;
  }

bool ReadSeriesInteger(const ENUM_TIMEFRAMES timeframe,
                       const ENUM_SERIES_INFO_INTEGER property,
                       long &value)
  {
   value=0;
   ResetLastError();
   if(!SeriesInfoInteger(_Symbol,timeframe,property,value))
      return false;
   return GetLastError()==0;
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
      return false;

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
      return false;
   return true;
  }

int OnInit()
  {
   if(_Symbol!=EXPECTED_SYMBOL || _Period!=PERIOD_M1 ||
      MathAbs(InpRiskPercent-0.20)>1e-12 || InpTimeStopMinutes!=7 ||
      InpMagic!=260812002 || InpDeviationPoints!=0)
     {
      PrintFormat("SQA_ECON_IDENTITY_FAIL expected=%s/M1 risk=0.20 time_stop=7 actual=%s/%d",
                  EXPECTED_SYMBOL,_Symbol,(int)_Period);
      return INIT_FAILED;
     }
   if(ArrayResize(g_queue_time_msc,QUEUE_CAPACITY)!=QUEUE_CAPACITY ||
      ArrayResize(g_queue_mid,QUEUE_CAPACITY)!=QUEUE_CAPACITY ||
      ArrayResize(g_queue_net_delta,QUEUE_CAPACITY)!=QUEUE_CAPACITY ||
      ArrayResize(g_queue_event_count,QUEUE_CAPACITY)!=QUEUE_CAPACITY)
     {
      Print("SQA_SOURCE_QUEUE_ALLOCATION_FAIL");
      return INIT_FAILED;
     }
   g_atr_handle=iATR(_Symbol,PERIOD_M1,ATR_PERIOD);
   if(g_atr_handle==INVALID_HANDLE)
     {
      PrintFormat("SQA_SOURCE_ATR_INIT_FAIL error=%d",GetLastError());
      return INIT_FAILED;
     }
   if(!EmitD0SeriesProof())
     {
      PrintFormat("SQA_SOURCE_D0_SERIES_PROOF_FAIL error=%d",GetLastError());
      return INIT_FAILED;
     }
   ArrayInitialize(g_year_signals,0);
   PrintFormat("SQA_ECON_READY hypothesis_id=%s symbol=%s timeframe=M1 window_ms=%d net_threshold=%d mid_atr=%.2f warmup=%d risk_pct=%.2f stop_atr=%.2f stop_min=%.2f stop_max=%.2f target_r=%.2f time_stop_min=%d",
               HYPOTHESIS_ID,_Symbol,WINDOW_MILLISECONDS,MIN_NET_SIGNED_PRESSURE,
               ABSORPTION_MID_ATR,WARMUP_M1_BARS,InpRiskPercent,STOP_ATR_MULTIPLIER,
               MIN_STOP_USD,MAX_STOP_USD,TARGET_R_MULTIPLIER,InpTimeStopMinutes);
   return INIT_SUCCEEDED;
  }

void OnTick()
  {
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick))
      return;
   g_total_ticks++;
   if(!QuoteValid(tick))
     {
      g_invalid_quote_ticks++;
      return;
     }
   g_valid_quote_ticks++;
   ManageOwnedPositions((datetime)tick.time);
   ProcessValidTick(tick);
  }

void OnDeinit(const int reason)
  {
   int median_abs_pressure=MedianAbsPressure();
   long expected_m1=Bars(_Symbol,PERIOD_M1,D'2018.01.01 00:00',D'2022.01.01 00:00');
   double minute_coverage=(expected_m1>0)
                          ? (double)g_completed_valid_m1/(double)expected_m1 : 0.0;
   double valid_quote_ratio=(g_total_ticks>0)
                            ? (double)g_valid_quote_ticks/(double)g_total_ticks : 0.0;
   bool years_pass=true;
   for(int i=0;i<4;i++)
      if(g_year_signals[i]<MIN_YEAR_SIGNALS)
         years_pass=false;
   bool source_gate_pass=(minute_coverage>=0.98 && valid_quote_ratio>=0.98 &&
                          g_signal_count>=MIN_DESIGN_SIGNALS &&
                          median_abs_pressure>=MIN_SIGNAL_MEDIAN_ABS_PRESSURE &&
                          years_pass && !g_queue_overflow &&
                          g_reverse_time_ticks==0);
   PrintFormat("SQA_SOURCE_SUMMARY hypothesis_id=%s signals=%I64d long=%I64d short=%I64d y2018=%I64d y2019=%I64d y2020=%I64d y2021=%I64d median_abs_pressure=%d completed_valid_m1=%I64d expected_m1=%I64d minute_coverage=%.8f total_ticks=%I64d valid_quote_ticks=%I64d invalid_quote_ticks=%I64d valid_quote_ratio=%.8f duplicate_time_ticks=%I64d exact_duplicate_quotes=%I64d reverse_time_ticks=%I64d gap_minutes=%I64d queue_overflow=%s source_gate_pass=%s orders_sent=%I64d reason=%d",
               HYPOTHESIS_ID,g_signal_count,g_long_signals,g_short_signals,
               g_year_signals[0],g_year_signals[1],g_year_signals[2],g_year_signals[3],
               median_abs_pressure,g_completed_valid_m1,expected_m1,minute_coverage,
               g_total_ticks,g_valid_quote_ticks,g_invalid_quote_ticks,valid_quote_ratio,
               g_duplicate_time_ticks,g_exact_duplicate_quotes,g_reverse_time_ticks,
               g_gap_minutes,(string)g_queue_overflow,(string)source_gate_pass,
               g_entries_accepted,reason);
   PrintFormat("SQA_ECON_SUMMARY hypothesis_id=%s entries=%I64d position_skips=%I64d volume_rejects=%I64d geometry_rejects=%I64d order_check_rejects=%I64d order_send_rejects=%I64d close_requests=%I64d close_rejects=%I64d time_exits=%I64d weekend_exits=%I64d sl_exits=%I64d tp_exits=%I64d expert_exits=%I64d",
               HYPOTHESIS_ID,g_entries_accepted,g_position_skips,g_volume_rejects,
               g_geometry_rejects,g_order_check_rejects,g_order_send_rejects,
               g_close_requests,g_close_rejects,g_time_exit_requests,
               g_weekend_exit_requests,g_sl_exits,g_tp_exits,g_expert_exits);
   if(g_atr_handle!=INVALID_HANDLE)
      IndicatorRelease(g_atr_handle);
  }

void OnTradeTransaction(const MqlTradeTransaction &transaction,
                        const MqlTradeRequest &request,
                        const MqlTradeResult &result)
  {
   if(transaction.type!=TRADE_TRANSACTION_DEAL_ADD || transaction.deal==0 ||
      !HistoryDealSelect(transaction.deal))
      return;
   if(HistoryDealGetString(transaction.deal,DEAL_SYMBOL)!=_Symbol ||
      HistoryDealGetInteger(transaction.deal,DEAL_MAGIC)!=(long)InpMagic)
      return;
   const long entry_kind=HistoryDealGetInteger(transaction.deal,DEAL_ENTRY);
   if(entry_kind!=DEAL_ENTRY_OUT && entry_kind!=DEAL_ENTRY_OUT_BY)
      return;
   const long reason=HistoryDealGetInteger(transaction.deal,DEAL_REASON);
   if(reason==DEAL_REASON_SL)
      g_sl_exits++;
   else if(reason==DEAL_REASON_TP)
      g_tp_exits++;
   else if(reason==DEAL_REASON_EXPERT)
      g_expert_exits++;
  }

// Frozen economic baseline: native Bid/Ask spread, one position, no lookahead.
//+------------------------------------------------------------------+
