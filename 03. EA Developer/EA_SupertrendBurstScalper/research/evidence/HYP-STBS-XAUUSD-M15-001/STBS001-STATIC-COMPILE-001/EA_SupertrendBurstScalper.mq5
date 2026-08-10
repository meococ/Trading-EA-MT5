#property strict
#property version   "1.00"
#property description "Closed-bar H1 Supertrend flip event clock with M15 ATR burst exits."

input string InpHypothesisId        = "HYP-STBS-XAUUSD-M15-001";
input string InpVariantTag          = "STBS_H1_FLIP_M15_BURST_ENGINEERING";
input bool   InpAuditOnly           = true;
input bool   InpEnableTelemetry     = false;
input long   InpMagic               = 5604101;
input double InpRiskPercent         = 0.25;
input double InpStopAtrMult         = 1.00;
input double InpTargetRR            = 1.50;
input int    InpMaxHoldBars         = 8;
input double InpMaxDailyLossPct     = 1.50;
input double InpMaxAccountDrawdownPct = 8.00;
input int    InpFridayEntryCutoffUtcMinutes = 18*60;
input int    InpFridayFlattenUtcMinutes     = 20*60;
input int    InpDeviationPoints     = 20;

const datetime SOURCE_START_TIME = D'2004.06.11 07:00:00';
const datetime DESIGN_START_TIME = D'2018.01.01 02:00:00';
const datetime DESIGN_END_TIME   = D'2023.01.01 02:00:00';
const int ST_ATR_PERIOD          = 10;
const double ST_FACTOR           = 3.0;
const int M15_ATR_PERIOD         = 14;
const int STATE_DOWN             = -1;
const int STATE_UP               = 1;

struct EntryPlan
{
   ENUM_ORDER_TYPE order_type;
   ENUM_ORDER_TYPE_FILLING filling;
   double entry;
   double stop;
   double target;
   double volume;
};

datetime g_current_h1_open=0;
datetime g_current_m15_open=0;
datetime g_last_h1_time=0;
datetime g_entry_m15_open=0;
double   g_st_atr=0.0;
double   g_final_upper=0.0;
double   g_final_lower=0.0;
double   g_supertrend=0.0;
double   g_prior_close=0.0;
double   g_peak_equity=0.0;
double   g_day_start_equity=0.0;
int      g_st_state=0;
int      g_day_key=0;
int      g_m15_atr_handle=INVALID_HANDLE;
bool     g_runtime_failed=false;
long     g_raw_events=0;
long     g_executable_events=0;
long     g_gap_events=0;
long     g_long_events=0;
long     g_short_events=0;
long     g_atr_ready_events=0;
long     g_geometry_ready_events=0;
long     g_entries_submitted=0;
long     g_entry_rejects=0;
long     g_closes_submitted=0;


string StateName(const int state)
{
   if(state==STATE_UP)
      return "UP";
   if(state==STATE_DOWN)
      return "DOWN";
   return "UNAVAILABLE";
}


datetime CurrentBarOpen(const ENUM_TIMEFRAMES timeframe)
{
   return (datetime)SeriesInfoInteger(_Symbol,timeframe,SERIES_LASTBAR_DATE);
}


bool ReadSeriesInteger(
   const ENUM_TIMEFRAMES timeframe,
   const ENUM_SERIES_INFO_INTEGER property_id,
   const string field_name,
   long &value
)
{
   ResetLastError();
   if(!SeriesInfoInteger(_Symbol,timeframe,property_id,value))
   {
      PrintFormat("DATA_EPOCH_D0_INIT_FAIL reason=series_info_invalid symbol=%s field=%s timeframe=%d error=%d",
                  _Symbol,field_name,(int)timeframe,GetLastError());
      return false;
   }
   return true;
}


bool EmitDataQualitySeriesProof()
{
   long m5_synchronized=0;
   long m5_first_epoch=0;
   long m5_terminal_first_epoch=0;
   long m1_server_first_epoch=0;
   long m1_terminal_first_epoch=0;
   long m5_bars=0;
   long terminal_maxbars=0;

   if(!ReadSeriesInteger(PERIOD_M5,SERIES_SYNCHRONIZED,"m5_synchronized",m5_synchronized) ||
      !ReadSeriesInteger(PERIOD_M5,SERIES_FIRSTDATE,"m5_first_epoch",m5_first_epoch) ||
      !ReadSeriesInteger(PERIOD_M5,SERIES_TERMINAL_FIRSTDATE,"m5_terminal_first_epoch",m5_terminal_first_epoch) ||
      !ReadSeriesInteger(PERIOD_M1,SERIES_SERVER_FIRSTDATE,"m1_server_first_epoch",m1_server_first_epoch) ||
      !ReadSeriesInteger(PERIOD_M1,SERIES_TERMINAL_FIRSTDATE,"m1_terminal_first_epoch",m1_terminal_first_epoch) ||
      !ReadSeriesInteger(PERIOD_M5,SERIES_BARS_COUNT,"m5_bars",m5_bars))
      return false;

   ResetLastError();
   terminal_maxbars=TerminalInfoInteger(TERMINAL_MAXBARS);
   const int terminal_error=GetLastError();
   if(terminal_maxbars<=0 || terminal_error!=0)
   {
      PrintFormat("DATA_EPOCH_D0_INIT_FAIL reason=terminal_maxbars_invalid symbol=%s terminal_maxbars=%I64d error=%d",
                  _Symbol,terminal_maxbars,terminal_error);
      return false;
   }

   datetime copytime_values[];
   ArraySetAsSeries(copytime_values,false);
   const datetime copytime_from=(datetime)m5_first_epoch;
   ResetLastError();
   const int copytime_result=CopyTime(_Symbol,PERIOD_M5,copytime_from,1,copytime_values);
   const int copytime_error=GetLastError();
   long copytime_first_epoch=0;
   if(copytime_result==1)
      copytime_first_epoch=(long)copytime_values[0];

   PrintFormat("DATA_EPOCH_D0_SERIES_PROOF symbol=%s m5_synchronized=%I64d m5_first_epoch=%I64d m5_terminal_first_epoch=%I64d m1_server_first_epoch=%I64d m1_terminal_first_epoch=%I64d m5_bars=%I64d terminal_maxbars=%I64d copytime_from_epoch=%I64d copytime_count=1 copytime_result=%d copytime_first_epoch=%I64d copytime_last_error=%d",
               _Symbol,m5_synchronized,m5_first_epoch,m5_terminal_first_epoch,
               m1_server_first_epoch,m1_terminal_first_epoch,m5_bars,terminal_maxbars,
               (long)copytime_from,copytime_result,copytime_first_epoch,copytime_error);
   if(m5_synchronized!=1 || m5_first_epoch<=0 || m5_terminal_first_epoch<=0 ||
      m1_server_first_epoch<=0 || m1_terminal_first_epoch<=0 || m5_bars<=0 ||
      copytime_result!=1 || copytime_first_epoch!=m5_first_epoch || copytime_error!=0)
   {
      PrintFormat("DATA_EPOCH_D0_INIT_FAIL reason=series_proof_invalid symbol=%s m5_synchronized=%I64d copytime_result=%d copytime_last_error=%d",
                  _Symbol,m5_synchronized,copytime_result,copytime_error);
      return false;
   }
   return true;
}


bool ValidBar(const MqlRates &bar)
{
   if(!MathIsValidNumber(bar.high) || !MathIsValidNumber(bar.low) ||
      !MathIsValidNumber(bar.close))
      return false;
   return bar.high>=bar.low && bar.close>=bar.low && bar.close<=bar.high;
}


double TrueRange(const MqlRates &bar,const bool has_prior,const double prior_close)
{
   if(!has_prior)
      return bar.high-bar.low;
   const double range=bar.high-bar.low;
   const double high_gap=MathAbs(bar.high-prior_close);
   const double low_gap=MathAbs(bar.low-prior_close);
   return MathMax(range,MathMax(high_gap,low_gap));
}


bool SameBandIdentity(const double line,const double band)
{
   return line==band;
}


bool AdvanceSupertrend(const MqlRates &bar,int &prior_state)
{
   if(!ValidBar(bar))
      return false;
   prior_state=g_st_state;
   const double tr=TrueRange(bar,true,g_prior_close);
   const double next_atr=(9.0*g_st_atr+tr)/10.0;
   const double hl2=(bar.high+bar.low)/2.0;
   const double basic_upper=hl2+ST_FACTOR*next_atr;
   const double basic_lower=hl2-ST_FACTOR*next_atr;
   const double next_upper=(basic_upper<g_final_upper || g_prior_close>g_final_upper)
                           ? basic_upper : g_final_upper;
   const double next_lower=(basic_lower>g_final_lower || g_prior_close<g_final_lower)
                           ? basic_lower : g_final_lower;

   int next_state=0;
   if(SameBandIdentity(g_supertrend,g_final_upper))
      next_state=(bar.close>next_upper) ? STATE_UP : STATE_DOWN;
   else if(SameBandIdentity(g_supertrend,g_final_lower))
      next_state=(bar.close<next_lower) ? STATE_DOWN : STATE_UP;
   else
      return false;

   g_st_atr=next_atr;
   g_final_upper=next_upper;
   g_final_lower=next_lower;
   g_st_state=next_state;
   g_supertrend=(g_st_state==STATE_UP) ? g_final_lower : g_final_upper;
   g_prior_close=bar.close;
   g_last_h1_time=bar.time;
   return MathIsValidNumber(g_st_atr) && MathIsValidNumber(g_final_upper) &&
          MathIsValidNumber(g_final_lower) && MathIsValidNumber(g_supertrend);
}


bool RebuildFrozenSupertrend(const datetime latest_closed_time)
{
   MqlRates history[];
   ArraySetAsSeries(history,false);
   const int total_bars=Bars(_Symbol,PERIOD_H1);
   if(total_bars<=ST_ATR_PERIOD)
      return false;
   const int copied=CopyRates(_Symbol,PERIOD_H1,1,total_bars-1,history);
   if(copied<ST_ATR_PERIOD || history[0].time!=SOURCE_START_TIME)
   {
      PrintFormat("STBS_FATAL|prehistory_unavailable|copied=%d|first=%s",copied,
                  copied>0 ? TimeToString(history[0].time,TIME_DATE|TIME_SECONDS) : "NONE");
      return false;
   }

   double seed_sum=0.0;
   double prior_close=0.0;
   for(int index=0;index<copied;index++)
   {
      if(!ValidBar(history[index]))
      {
         PrintFormat("STBS_FATAL|invalid_history_bar|index=%d|time=%s",index,
                     TimeToString(history[index].time,TIME_DATE|TIME_SECONDS));
         return false;
      }
      const double tr=TrueRange(history[index],index>0,prior_close);
      if(index<ST_ATR_PERIOD)
         seed_sum+=tr;
      if(index==ST_ATR_PERIOD-1)
      {
         g_st_atr=seed_sum/10.0;
         const double hl2=(history[index].high+history[index].low)/2.0;
         g_final_upper=hl2+ST_FACTOR*g_st_atr;
         g_final_lower=hl2-ST_FACTOR*g_st_atr;
         g_st_state=STATE_DOWN;
         g_supertrend=g_final_upper;
         g_prior_close=history[index].close;
         g_last_h1_time=history[index].time;
      }
      else if(index>=ST_ATR_PERIOD)
      {
         int ignored=0;
         if(!AdvanceSupertrend(history[index],ignored))
            return false;
      }
      prior_close=history[index].close;
   }
   return g_last_h1_time==latest_closed_time && g_st_state!=0;
}


datetime LastSundayUtc(const int year,const int month,const int hour)
{
   MqlDateTime parts;
   ZeroMemory(parts);
   parts.year=year;
   parts.mon=month;
   parts.day=31;
   parts.hour=hour;
   datetime candidate=StructToTime(parts);
   MqlDateTime check;
   TimeToStruct(candidate,check);
   while(check.mon!=month)
   {
      candidate-=86400;
      TimeToStruct(candidate,check);
   }
   return candidate-check.day_of_week*86400;
}


datetime NthSundayUtc(const int year,const int month,const int occurrence,const int hour)
{
   MqlDateTime parts;
   ZeroMemory(parts);
   parts.year=year;
   parts.mon=month;
   parts.day=1;
   parts.hour=hour;
   const datetime first=StructToTime(parts);
   MqlDateTime check;
   TimeToStruct(first,check);
   const int day=1+((7-check.day_of_week)%7)+(occurrence-1)*7;
   parts.day=day;
   return StructToTime(parts);
}


bool IsEuropeDstUtc(const datetime utc_time)
{
   MqlDateTime parts;
   TimeToStruct(utc_time,parts);
   const datetime begin=LastSundayUtc(parts.year,3,1);
   const datetime finish=LastSundayUtc(parts.year,10,1);
   return utc_time>=begin && utc_time<finish;
}


bool IsUnitedStatesDstUtc(const datetime utc_time)
{
   MqlDateTime parts;
   TimeToStruct(utc_time,parts);
   const datetime begin=NthSundayUtc(parts.year,3,2,7);
   const datetime finish=NthSundayUtc(parts.year,11,1,6);
   return utc_time>=begin && utc_time<finish;
}


bool IsFivePercentDstUtc(const datetime utc_time)
{
   MqlDateTime parts;
   TimeToStruct(utc_time,parts);
   return parts.year<=2023 ? IsEuropeDstUtc(utc_time)
                           : IsUnitedStatesDstUtc(utc_time);
}


datetime ServerToUtc(const datetime server_time)
{
   const datetime winter_candidate=server_time-2*3600;
   const int offset=2+(IsFivePercentDstUtc(winter_candidate) ? 1 : 0);
   return server_time-offset*3600;
}


int UtcDateKey(const datetime utc_time)
{
   MqlDateTime parts;
   TimeToStruct(utc_time,parts);
   return parts.year*10000+parts.mon*100+parts.day;
}


bool EntryClockAllowed(const datetime server_time)
{
   MqlDateTime parts;
   TimeToStruct(ServerToUtc(server_time),parts);
   const int minute=parts.hour*60+parts.min;
   if(parts.day_of_week==0 || parts.day_of_week==6)
      return false;
   if(parts.day_of_week==5 && minute>=InpFridayEntryCutoffUtcMinutes)
      return false;
   return true;
}


bool FridayFlattenDue(const datetime server_time)
{
   MqlDateTime parts;
   TimeToStruct(ServerToUtc(server_time),parts);
   return parts.day_of_week==5 &&
          parts.hour*60+parts.min>=InpFridayFlattenUtcMinutes;
}


void UpdateRiskAnchors(const datetime server_time)
{
   const double equity=AccountInfoDouble(ACCOUNT_EQUITY);
   if(equity<=0.0 || !MathIsValidNumber(equity))
      return;
   if(g_peak_equity<=0.0 || equity>g_peak_equity)
      g_peak_equity=equity;
   const int today=UtcDateKey(ServerToUtc(server_time));
   if(g_day_key!=today || g_day_start_equity<=0.0)
   {
      g_day_key=today;
      g_day_start_equity=equity;
   }
}


bool EntryRiskLocked()
{
   const double equity=AccountInfoDouble(ACCOUNT_EQUITY);
   if(equity<=0.0 || g_peak_equity<=0.0 || g_day_start_equity<=0.0)
      return true;
   const double account_dd=100.0*(g_peak_equity-equity)/g_peak_equity;
   const double day_dd=100.0*(g_day_start_equity-equity)/g_day_start_equity;
   return account_dd>=InpMaxAccountDrawdownPct || day_dd>=InpMaxDailyLossPct;
}


ulong OwnedPositionTicket()
{
   for(int index=PositionsTotal()-1;index>=0;index--)
   {
      const ulong ticket=PositionGetTicket(index);
      if(ticket==0 || !PositionSelectByTicket(ticket))
         continue;
      if(PositionGetString(POSITION_SYMBOL)==_Symbol &&
         (long)PositionGetInteger(POSITION_MAGIC)==InpMagic)
         return ticket;
   }
   return 0;
}


bool ForeignSymbolExposureExists()
{
   for(int index=PositionsTotal()-1;index>=0;index--)
   {
      const ulong ticket=PositionGetTicket(index);
      if(ticket==0 || !PositionSelectByTicket(ticket))
         continue;
      if(PositionGetString(POSITION_SYMBOL)==_Symbol &&
         (long)PositionGetInteger(POSITION_MAGIC)!=InpMagic)
         return true;
   }
   return false;
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


bool AcceptedRetcode(const uint retcode)
{
   return retcode==TRADE_RETCODE_DONE ||
          retcode==TRADE_RETCODE_DONE_PARTIAL ||
          retcode==TRADE_RETCODE_PLACED;
}


bool SubmitClose(const ulong ticket,const string reason)
{
   if(ticket==0 || !PositionSelectByTicket(ticket))
      return false;
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick) || tick.bid<=0.0 || tick.ask<=0.0)
      return false;
   const ENUM_POSITION_TYPE position_type=
      (ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE);
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
   request.type=position_type==POSITION_TYPE_BUY ? ORDER_TYPE_SELL : ORDER_TYPE_BUY;
   request.price=position_type==POSITION_TYPE_BUY ? tick.bid : tick.ask;
   request.deviation=(ulong)InpDeviationPoints;
   request.type_filling=FillingMode();
   request.comment=reason;
   PrintFormat("STBS_CLOSE_REQUEST|ticket=%I64u|reason=%s|volume=%.8f|price=%.8f",
               ticket,reason,request.volume,request.price);
   if(!OrderCheck(request,check))
      return false;
   if(!OrderSend(request,result) || !AcceptedRetcode(result.retcode))
      return false;
   g_closes_submitted++;
   return true;
}


int VolumeDigits(const double step)
{
   int digits=0;
   double scaled=step;
   while(digits<8 && MathAbs(scaled-MathRound(scaled))>1e-10)
   {
      scaled*=10.0;
      digits++;
   }
   return digits;
}


double RiskSizedVolume(const ENUM_ORDER_TYPE order_type,const double entry,const double stop)
{
   const double equity=AccountInfoDouble(ACCOUNT_EQUITY);
   const double risk_cash=equity*InpRiskPercent/100.0;
   double one_lot_profit=0.0;
   if(risk_cash<=0.0 ||
      !OrderCalcProfit(order_type,_Symbol,1.0,entry,stop,one_lot_profit) ||
      !MathIsValidNumber(one_lot_profit) || one_lot_profit>=0.0)
      return 0.0;
   const double step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);
   const double minimum=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN);
   const double maximum=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX);
   if(step<=0.0 || minimum<=0.0 || maximum<minimum)
      return 0.0;
   double volume=MathFloor((risk_cash/MathAbs(one_lot_profit))/step)*step;
   volume=MathMin(volume,maximum);
   volume=NormalizeDouble(volume,VolumeDigits(step));
   if(volume<minimum)
      return 0.0;
   return volume;
}


double NormalizePriceDown(const double price,const double tick_size)
{
   return NormalizeDouble(MathFloor(price/tick_size)*tick_size,_Digits);
}


double NormalizePriceUp(const double price,const double tick_size)
{
   return NormalizeDouble(MathCeil(price/tick_size)*tick_size,_Digits);
}


bool ClosedM15AtrAtDecision(const datetime decision_time,
                            const int decision_shift,
                            double &atr)
{
   atr=0.0;
   if(decision_shift<0)
      return false;
   const datetime prior_time=decision_time-PeriodSeconds(PERIOD_M15);
   const int prior_shift=iBarShift(_Symbol,PERIOD_M15,prior_time,true);
   if(prior_shift!=decision_shift+1)
      return false;
   double values[];
   ArraySetAsSeries(values,false);
   const int requested=prior_shift;
   if(g_m15_atr_handle==INVALID_HANDLE ||
      CopyBuffer(g_m15_atr_handle,0,1,requested,values)!=requested)
      return false;
   atr=values[0];
   return MathIsValidNumber(atr) && atr>0.0;
}


bool BuildEntryPlan(const int direction,const double atr,EntryPlan &plan)
{
   ZeroMemory(plan);
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick) || tick.bid<=0.0 || tick.ask<=0.0 ||
      tick.ask<tick.bid)
      return false;
   const double tick_size=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);
   const double point=SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   if(tick_size<=0.0 || point<=0.0)
      return false;
   const ENUM_ORDER_TYPE order_type=direction>0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
   const double entry=direction>0 ? tick.ask : tick.bid;
   const double raw_stop=direction>0 ? entry-InpStopAtrMult*atr
                                     : entry+InpStopAtrMult*atr;
   const double stop=direction>0 ? NormalizePriceDown(raw_stop,tick_size)
                                 : NormalizePriceUp(raw_stop,tick_size);
   const double risk_distance=direction>0 ? entry-stop : stop-entry;
   if(risk_distance<=0.0 || !MathIsValidNumber(risk_distance))
      return false;
   const double raw_target=direction>0 ? entry+InpTargetRR*risk_distance
                                       : entry-InpTargetRR*risk_distance;
   const double target=direction>0 ? NormalizePriceUp(raw_target,tick_size)
                                   : NormalizePriceDown(raw_target,tick_size);
   const long stops_level=SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL);
   const long freeze_level=SymbolInfoInteger(_Symbol,SYMBOL_TRADE_FREEZE_LEVEL);
   const double minimum_distance=(double)MathMax(stops_level,freeze_level)*point;
   if((direction>0 &&
       (stop>=tick.bid || target<=tick.ask || tick.bid-stop<minimum_distance ||
        target-tick.ask<minimum_distance)) ||
      (direction<0 &&
       (stop<=tick.ask || target>=tick.bid || stop-tick.ask<minimum_distance ||
        tick.bid-target<minimum_distance)))
      return false;
   const double volume=RiskSizedVolume(order_type,entry,stop);
   if(volume<=0.0)
      return false;

   double required_margin=0.0;
   const double free_margin=AccountInfoDouble(ACCOUNT_MARGIN_FREE);
   if(free_margin<=0.0 ||
      !OrderCalcMargin(order_type,_Symbol,volume,entry,required_margin) ||
      !MathIsValidNumber(required_margin) || required_margin<0.0 ||
      required_margin>free_margin)
      return false;

   plan.order_type=order_type;
   plan.filling=FillingMode();
   plan.entry=entry;
   plan.stop=stop;
   plan.target=target;
   plan.volume=volume;
   return true;
}


bool SubmitEntry(const int direction,const double atr,const datetime decision_time)
{
   EntryPlan plan;
   if(!BuildEntryPlan(direction,atr,plan))
      return false;

   MqlTradeRequest request;
   MqlTradeCheckResult check;
   MqlTradeResult result;
   ZeroMemory(request);
   ZeroMemory(check);
   ZeroMemory(result);
   request.action=TRADE_ACTION_DEAL;
   request.magic=(ulong)InpMagic;
   request.symbol=_Symbol;
   request.volume=plan.volume;
   request.type=plan.order_type;
   request.price=plan.entry;
   request.sl=plan.stop;
   request.tp=plan.target;
   request.deviation=(ulong)InpDeviationPoints;
   request.type_filling=plan.filling;
   request.comment=direction>0 ? "STBS_FLIP_BUY" : "STBS_FLIP_SELL";
   PrintFormat("STBS_ENTRY_REQUEST|decision=%s|direction=%s|atr=%.8f|entry=%.8f|sl=%.8f|tp=%.8f|volume=%.8f",
               TimeToString(decision_time,TIME_DATE|TIME_SECONDS),
               direction>0 ? "LONG" : "SHORT",atr,plan.entry,plan.stop,
               plan.target,plan.volume);
   if(!OrderCheck(request,check))
      return false;
   if(!OrderSend(request,result) || !AcceptedRetcode(result.retcode))
      return false;
   g_entry_m15_open=CurrentBarOpen(PERIOD_M15);
   g_entries_submitted++;
   return true;
}


void ConsumeFlipEvent(const MqlRates &bar,const int prior_state,const datetime next_time)
{
   const bool raw_event=prior_state!=0 && prior_state!=g_st_state;
   if(!raw_event)
      return;
   g_raw_events++;
   const int decision_m15_shift=iBarShift(_Symbol,PERIOD_M15,next_time,true);
   const bool exact_next=next_time==bar.time+PeriodSeconds(PERIOD_H1) &&
                         decision_m15_shift>=0;
   if(!exact_next)
   {
      g_gap_events++;
      PrintFormat("STBS_SIGNAL|source=%s|decision=%s|source_epoch=%I64d|decision_epoch=%I64d|direction=%s|exact_next=false|consumed=true",
                  TimeToString(bar.time,TIME_DATE|TIME_SECONDS),
                  TimeToString(next_time,TIME_DATE|TIME_SECONDS),
                  (long)ServerToUtc(bar.time),(long)ServerToUtc(next_time),
                  g_st_state==STATE_UP ? "LONG" : "SHORT");
      return;
   }
   g_executable_events++;
   const int direction=g_st_state==STATE_UP ? 1 : -1;
   if(direction>0)
      g_long_events++;
   else
      g_short_events++;
   double atr=0.0;
   const bool atr_ready=ClosedM15AtrAtDecision(next_time,decision_m15_shift,atr);
   if(atr_ready)
      g_atr_ready_events++;
   EntryPlan probe;
   const bool geometry_ready=atr_ready && CurrentBarOpen(PERIOD_M15)==next_time &&
                             BuildEntryPlan(direction,atr,probe);
   if(geometry_ready)
      g_geometry_ready_events++;
   PrintFormat("STBS_SIGNAL|source=%s|decision=%s|source_epoch=%I64d|decision_epoch=%I64d|direction=%s|exact_next=true|atr_ready=%s|geometry_ready=%s|atr=%.8f|entry=%.8f|sl=%.8f|tp=%.8f|volume=%.8f|audit=%s",
               TimeToString(bar.time,TIME_DATE|TIME_SECONDS),
               TimeToString(next_time,TIME_DATE|TIME_SECONDS),
               (long)ServerToUtc(bar.time),(long)ServerToUtc(next_time),
               direction>0 ? "LONG" : "SHORT",atr_ready ? "true" : "false",
               geometry_ready ? "true" : "false",atr,
               geometry_ready ? probe.entry : 0.0,
               geometry_ready ? probe.stop : 0.0,
               geometry_ready ? probe.target : 0.0,
               geometry_ready ? probe.volume : 0.0,
               InpAuditOnly ? "true" : "false");
   if(InpAuditOnly)
      return;
   if(!atr_ready || CurrentBarOpen(PERIOD_M15)!=next_time ||
      !EntryClockAllowed(next_time) || EntryRiskLocked() ||
      ForeignSymbolExposureExists())
   {
      g_entry_rejects++;
      return;
   }
   const ulong owned=OwnedPositionTicket();
   if(owned!=0)
   {
      if(!SubmitClose(owned,"STBS_OPPOSITE_FLIP") || OwnedPositionTicket()!=0)
      {
         g_entry_rejects++;
         return;
      }
   }
   if(!SubmitEntry(direction,atr,next_time))
      g_entry_rejects++;
}


bool ProcessNewClosedH1Bars(const datetime current_open)
{
   MqlRates bars[];
   ArraySetAsSeries(bars,false);
   const int prior_shift=iBarShift(_Symbol,PERIOD_H1,g_last_h1_time,true);
   if(prior_shift<=1)
      return false;
   const int copied=CopyRates(_Symbol,PERIOD_H1,1,prior_shift-1,bars);
   if(copied<=0)
      return false;
   for(int index=0;index<copied;index++)
   {
      if(bars[index].time<=g_last_h1_time)
         return false;
      int prior_state=0;
      if(!AdvanceSupertrend(bars[index],prior_state))
         return false;
      const datetime next_time=(index+1<copied) ? bars[index+1].time : current_open;
      if(bars[index].time>=DESIGN_START_TIME && bars[index].time<DESIGN_END_TIME)
         ConsumeFlipEvent(bars[index],prior_state,next_time);
      else if(!InpAuditOnly)
         ConsumeFlipEvent(bars[index],prior_state,next_time);
   }
   return true;
}


void RecoverEntryClock()
{
   const ulong ticket=OwnedPositionTicket();
   if(ticket==0 || !PositionSelectByTicket(ticket))
   {
      g_entry_m15_open=0;
      return;
   }
   const datetime position_time=(datetime)PositionGetInteger(POSITION_TIME);
   const long seconds=(long)position_time;
   const long period_seconds=(long)PeriodSeconds(PERIOD_M15);
   const datetime candidate=(datetime)(seconds-seconds%period_seconds);
   g_entry_m15_open=iBarShift(_Symbol,PERIOD_M15,candidate,true)>=0 ? candidate : 0;
}


void ManageOpenPosition(const datetime server_time,const bool new_m15_bar)
{
   const ulong ticket=OwnedPositionTicket();
   if(ticket==0)
   {
      g_entry_m15_open=0;
      return;
   }
   if(FridayFlattenDue(server_time))
   {
      SubmitClose(ticket,"STBS_FRIDAY_FLAT");
      return;
   }
   if(!new_m15_bar)
      return;
   if(g_entry_m15_open<=0)
      RecoverEntryClock();
   if(g_entry_m15_open<=0)
      return;
   const int shift=iBarShift(_Symbol,PERIOD_M15,g_entry_m15_open,true);
   if(shift>=InpMaxHoldBars)
      SubmitClose(ticket,"STBS_TIME_EXIT");
}


void FailRuntime(const string reason)
{
   if(g_runtime_failed)
      return;
   g_runtime_failed=true;
   PrintFormat("STBS_FATAL|runtime|%s",reason);
   ExpertRemove();
}


int OnInit()
{
   if(_Symbol!="XAUUSD" || _Period!=PERIOD_M15 ||
      InpHypothesisId!="HYP-STBS-XAUUSD-M15-001" ||
      InpVariantTag!="STBS_H1_FLIP_M15_BURST_ENGINEERING" ||
      !InpAuditOnly || InpEnableTelemetry || InpMagic!=5604101 ||
      InpRiskPercent!=0.25 || InpStopAtrMult!=1.00 || InpTargetRR!=1.50 ||
      InpMaxHoldBars!=8 || InpMaxDailyLossPct!=1.50 ||
      InpMaxAccountDrawdownPct!=8.00 ||
      InpFridayEntryCutoffUtcMinutes!=18*60 ||
      InpFridayFlattenUtcMinutes!=20*60 || InpDeviationPoints!=20)
   {
      g_runtime_failed=true;
      Print("STBS_FATAL|frozen_input_or_chart_contract_failed");
      return INIT_PARAMETERS_INCORRECT;
   }
   if(!EmitDataQualitySeriesProof())
   {
      g_runtime_failed=true;
      Print("STBS_FATAL|data_quality_series_proof_failed");
      return INIT_FAILED;
   }
   g_m15_atr_handle=iATR(_Symbol,PERIOD_M15,M15_ATR_PERIOD);
   if(g_m15_atr_handle==INVALID_HANDLE)
   {
      g_runtime_failed=true;
      Print("STBS_FATAL|m15_atr_handle_failed");
      return INIT_FAILED;
   }
   g_current_h1_open=CurrentBarOpen(PERIOD_H1);
   g_current_m15_open=CurrentBarOpen(PERIOD_M15);
   const datetime latest_closed=iTime(_Symbol,PERIOD_H1,1);
   if(g_current_h1_open<=0 || g_current_m15_open<=0 || latest_closed<=0 ||
      latest_closed>=g_current_h1_open || !RebuildFrozenSupertrend(latest_closed))
   {
      g_runtime_failed=true;
      Print("STBS_FATAL|prehistory_or_state_rebuild_failed");
      return INIT_FAILED;
   }
   UpdateRiskAnchors(TimeCurrent());
   RecoverEntryClock();
   PrintFormat("STBS_INIT|hypothesis=%s|audit=%s|h1_last=%s|state=%s",
               InpHypothesisId,InpAuditOnly ? "true" : "false",
               TimeToString(g_last_h1_time,TIME_DATE|TIME_SECONDS),StateName(g_st_state));
   return INIT_SUCCEEDED;
}


void OnDeinit(const int reason)
{
   if(g_m15_atr_handle!=INVALID_HANDLE)
   {
      IndicatorRelease(g_m15_atr_handle);
      g_m15_atr_handle=INVALID_HANDLE;
   }
   PrintFormat("STBS_SUMMARY|hypothesis=%s|reason=%d|raw=%I64d|executable=%I64d|gaps=%I64d|long=%I64d|short=%I64d|atr_ready=%I64d|geometry_ready=%I64d|entries=%I64d|entry_rejects=%I64d|closes=%I64d|failed=%s",
               InpHypothesisId,reason,g_raw_events,g_executable_events,g_gap_events,
               g_long_events,g_short_events,g_atr_ready_events,g_geometry_ready_events,
               g_entries_submitted,g_entry_rejects,g_closes_submitted,
               g_runtime_failed ? "true" : "false");
}


void OnTick()
{
   if(g_runtime_failed)
      return;
   const datetime server_time=TimeCurrent();
   UpdateRiskAnchors(server_time);
   const datetime m15_open=CurrentBarOpen(PERIOD_M15);
   const bool new_m15_bar=m15_open>0 && m15_open!=g_current_m15_open;
   if(new_m15_bar)
   {
      if(m15_open<g_current_m15_open)
      {
         FailRuntime("m15_time_regressed");
         return;
      }
      g_current_m15_open=m15_open;
   }
   if(!InpAuditOnly)
      ManageOpenPosition(server_time,new_m15_bar);

   const datetime h1_open=CurrentBarOpen(PERIOD_H1);
   if(h1_open<=0 || h1_open==g_current_h1_open)
      return;
   if(h1_open<g_current_h1_open)
   {
      FailRuntime("h1_time_regressed");
      return;
   }
   if(!ProcessNewClosedH1Bars(h1_open))
   {
      FailRuntime("h1_backlog_processing_failed");
      return;
   }
   g_current_h1_open=h1_open;
}


void OnTradeTransaction(const MqlTradeTransaction &transaction,
                        const MqlTradeRequest &request,
                        const MqlTradeResult &result)
{
   if(transaction.type!=TRADE_TRANSACTION_DEAL_ADD || transaction.deal==0 ||
      !HistoryDealSelect(transaction.deal))
      return;
   if(HistoryDealGetString(transaction.deal,DEAL_SYMBOL)!=_Symbol ||
      (long)HistoryDealGetInteger(transaction.deal,DEAL_MAGIC)!=InpMagic)
      return;
   PrintFormat("STBS_DEAL|deal=%I64u|order=%I64u|position=%I64u|entry=%d|type=%d|volume=%.8f|price=%.8f|profit=%.8f|commission=%.8f|swap=%.8f|request_retcode=%u",
               transaction.deal,transaction.order,
               (ulong)HistoryDealGetInteger(transaction.deal,DEAL_POSITION_ID),
               (int)HistoryDealGetInteger(transaction.deal,DEAL_ENTRY),
               (int)HistoryDealGetInteger(transaction.deal,DEAL_TYPE),
               HistoryDealGetDouble(transaction.deal,DEAL_VOLUME),
               HistoryDealGetDouble(transaction.deal,DEAL_PRICE),
               HistoryDealGetDouble(transaction.deal,DEAL_PROFIT),
               HistoryDealGetDouble(transaction.deal,DEAL_COMMISSION),
               HistoryDealGetDouble(transaction.deal,DEAL_SWAP),result.retcode);
}


double OnTester()
{
   return 0.0;
}
