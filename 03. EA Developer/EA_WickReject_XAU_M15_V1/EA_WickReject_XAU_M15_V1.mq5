//+------------------------------------------------------------------+
//| EA_WickReject_XAU_M15_V1.mq5                                    |
//| HYP-CBWR-XAUUSD-M15-003: closed-bar swing wick rejection         |
//+------------------------------------------------------------------+
#property strict
#property version   "1.00"
#property description "Untuned closed-bar M15 swing wick-rejection research EA"

#include <Trade/Trade.mqh>

input group "--- Frozen research authority ---"
input bool   InpResearchAutoMode=false;
input bool   InpEnableTelemetry=true;
input string InpHypothesisId="HYP-CBWR-XAUUSD-M15-003";
input string InpVariantTag="SWING8_PRIMARY";
input bool   InpRequireSwing=true;

input group "--- Frozen signal ---"
input int    InpSwingBars=8;
input double InpWickRatio=0.60;
input double InpBodyRatio=0.35;
input double InpSwingAtrTolerance=0.15;
input int    InpATRPeriod=14;
input int    InpATRAverageBars=50;
input double InpATRMinMult=0.70;
input double InpATRMaxMult=2.20;

input group "--- Frozen exit and risk ---"
input double InpSLATRBuffer=0.25;
input double InpMinSLATR=1.20;
input double InpMaxSLATR=2.80;
input double InpTargetR=1.60;
input int    InpTimeStopBars=12;
input double InpBETriggerR=0.90;
input double InpRiskPercent=0.60;
input int    InpMaxSpreadPoints=55;
input double InpDailyLossPct=1.50;
input double InpWeeklyLossPct=3.50;
input int    InpDailyFlatHour=21;
input int    InpDailyFlatMinute=50;
input int    InpFridayFlatHour=20;
input int    InpDeviationPoints=10;
input long   InpMagic=5604703;

const string EA_NAME="EA_WickReject_XAU_M15_V1";
const string EXPECTED_HYPOTHESIS="HYP-CBWR-XAUUSD-M15-003";
const string PRIMARY_VARIANT="SWING8_PRIMARY";
const string CONTROL_VARIANT="NO_SWING_CONTROL";

struct SignalDecision
  {
   bool fired;
   datetime decision_time;
   datetime availability_time;
   int direction;
   double signal_open;
   double signal_high;
   double signal_low;
   double signal_close;
   double range;
   double body_ratio;
   double directional_wick_ratio;
   double close_location;
   double swing_level;
   double atr;
   double atr_average;
   double atr_ratio;
  };

CTrade g_trade;
int g_atr_handle=INVALID_HANDLE;
datetime g_last_bar_open=0;
datetime g_last_decision_time=0;
datetime g_entry_time=0;
datetime g_last_close_attempt_bar=0;
double g_entry_price=0.0;
double g_initial_sl=0.0;
double g_initial_risk=0.0;
double g_entry_spread_points=0.0;
double g_mfe_points=0.0;
double g_mae_points=0.0;
string g_pending_exit_reason="";
int g_day_key=0;
long g_week_key=0;
double g_day_start_equity=0.0;
double g_week_start_equity=0.0;
bool g_day_locked=false;
bool g_week_locked=false;
bool g_runtime_failed=false;
long g_closed_bars=0;
long g_wick_candidates=0;
long g_swing_rejects=0;
long g_atr_rejects=0;
long g_spread_rejects=0;
long g_risk_lock_skips=0;
long g_signals=0;
long g_long_signals=0;
long g_short_signals=0;
long g_entries=0;
long g_entry_rejects=0;
long g_be_moves=0;
long g_close_attempts=0;
long g_close_rejects=0;
long g_closes=0;
long g_invalid_inputs=0;

bool IsFinite(const double value)
  {
   return(value!=EMPTY_VALUE && MathIsValidNumber(value));
  }

int DayKey(const datetime stamp)
  {
   MqlDateTime p;
   TimeToStruct(stamp,p);
   return(p.year*10000+p.mon*100+p.day);
  }

long WeekKey(const datetime stamp)
  {
   MqlDateTime p;
   TimeToStruct(stamp,p);
   const datetime day_start=stamp-p.hour*3600-p.min*60-p.sec;
   const int days_from_monday=(p.day_of_week+6)%7;
   return((long)(day_start-days_from_monday*86400)/604800);
  }

int MinuteOfDay(const datetime stamp)
  {
   MqlDateTime p;
   TimeToStruct(stamp,p);
   return(p.hour*60+p.min);
  }

bool CurrentBarOpen(datetime &bar_open)
  {
   long raw=0;
   bar_open=0;
   if(!SeriesInfoInteger(_Symbol,PERIOD_M15,SERIES_LASTBAR_DATE,raw) || raw<=0)
      return(false);
   bar_open=(datetime)raw;
   return(true);
  }

bool EmitSeriesProof()
  {
   long m5_synchronized=0;
   long m5_first_epoch=0;
   long m5_terminal_first_epoch=0;
   long m1_server_first_epoch=0;
   long m1_terminal_first_epoch=0;
   long m5_bars=0;
   if(!SeriesInfoInteger(_Symbol,PERIOD_M5,SERIES_SYNCHRONIZED,m5_synchronized) ||
      !SeriesInfoInteger(_Symbol,PERIOD_M5,SERIES_FIRSTDATE,m5_first_epoch) ||
      !SeriesInfoInteger(_Symbol,PERIOD_M5,SERIES_TERMINAL_FIRSTDATE,m5_terminal_first_epoch) ||
      !SeriesInfoInteger(_Symbol,PERIOD_M1,SERIES_SERVER_FIRSTDATE,m1_server_first_epoch) ||
      !SeriesInfoInteger(_Symbol,PERIOD_M1,SERIES_TERMINAL_FIRSTDATE,m1_terminal_first_epoch) ||
      !SeriesInfoInteger(_Symbol,PERIOD_M5,SERIES_BARS_COUNT,m5_bars))
      return(false);
   ResetLastError();
   const long terminal_maxbars=TerminalInfoInteger(TERMINAL_MAXBARS);
   const int terminal_error=GetLastError();
   datetime copied_time[];
   ArraySetAsSeries(copied_time,false);
   const datetime copytime_from=(datetime)m5_first_epoch;
   ResetLastError();
   const int copytime_result=CopyTime(_Symbol,PERIOD_M5,copytime_from,1,copied_time);
   const int copytime_error=GetLastError();
   const long copytime_first_epoch=(copytime_result==1 ? (long)copied_time[0] : 0);
   PrintFormat("DATA_EPOCH_D0_SERIES_PROOF symbol=%s m5_synchronized=%I64d m5_first_epoch=%I64d m5_terminal_first_epoch=%I64d m1_server_first_epoch=%I64d m1_terminal_first_epoch=%I64d m5_bars=%I64d terminal_maxbars=%I64d copytime_from_epoch=%I64d copytime_count=1 copytime_result=%d copytime_first_epoch=%I64d copytime_last_error=%d",
               _Symbol,m5_synchronized,m5_first_epoch,m5_terminal_first_epoch,
               m1_server_first_epoch,m1_terminal_first_epoch,m5_bars,terminal_maxbars,
               (long)copytime_from,copytime_result,copytime_first_epoch,copytime_error);
   return(m5_synchronized==1 && m5_first_epoch>0 && m5_terminal_first_epoch>0 &&
          m1_server_first_epoch>0 && m1_terminal_first_epoch>0 && m5_bars>0 &&
          terminal_maxbars>0 && terminal_error==0 && copytime_result==1 &&
          copytime_first_epoch==m5_first_epoch && copytime_error==0);
  }

bool LoadClosedRates(MqlRates &rates[])
  {
   const int required=MathMax(InpATRAverageBars+InpATRPeriod+3,InpSwingBars+3);
   ArraySetAsSeries(rates,true);
   const int copied=CopyRates(_Symbol,PERIOD_M15,1,required,rates);
   if(copied<required)
      return(false);
   for(int i=0;i<MathMin(copied,InpSwingBars+2);i++)
     {
      if(rates[i].time<=0 || rates[i].high<=rates[i].low || rates[i].open<=0.0 ||
         rates[i].close<=0.0 || rates[i].tick_volume<=0)
         return(false);
     }
   return(true);
  }

bool LoadAtr(double &current_atr,double &average_atr)
  {
   current_atr=0.0;
   average_atr=0.0;
   if(g_atr_handle==INVALID_HANDLE || BarsCalculated(g_atr_handle)<InpATRAverageBars+2)
      return(false);
   double values[];
   ArraySetAsSeries(values,true);
   const int needed=InpATRAverageBars+1;
   if(CopyBuffer(g_atr_handle,0,1,needed,values)!=needed)
      return(false);
   current_atr=values[0];
   if(!IsFinite(current_atr) || current_atr<=0.0)
      return(false);
   double sum=0.0;
   for(int i=1;i<=InpATRAverageBars;i++)
     {
      if(!IsFinite(values[i]) || values[i]<=0.0)
         return(false);
      sum+=values[i];
     }
   average_atr=sum/InpATRAverageBars;
   return(IsFinite(average_atr) && average_atr>0.0);
  }

bool BuildSignal(const datetime availability_time,SignalDecision &signal)
  {
   ZeroMemory(signal);
   MqlRates rates[];
   if(!LoadClosedRates(rates))
     {
      g_invalid_inputs++;
      return(false);
     }
   const MqlRates bar=rates[0];
   if(bar.time<=0 || bar.time==g_last_decision_time)
      return(false);
   g_last_decision_time=bar.time;
   g_closed_bars++;
   if((long)(availability_time-bar.time)!=PeriodSeconds(PERIOD_M15))
     {
      g_invalid_inputs++;
      return(false);
     }

   double atr=0.0;
   double atr_average=0.0;
   if(!LoadAtr(atr,atr_average))
     {
      g_invalid_inputs++;
      return(false);
     }
   const double atr_ratio=atr/atr_average;
   if(atr_ratio<InpATRMinMult || atr_ratio>InpATRMaxMult)
     {
      g_atr_rejects++;
      return(false);
     }

   const double range=bar.high-bar.low;
   const double body=MathAbs(bar.close-bar.open);
   const double lower_wick=MathMin(bar.open,bar.close)-bar.low;
   const double upper_wick=bar.high-MathMax(bar.open,bar.close);
   if(range<=0.0 || body/range>InpBodyRatio)
      return(false);
   const double lower_ratio=lower_wick/range;
   const double upper_ratio=upper_wick/range;
   const double close_location=(bar.close-bar.low)/range;
   const bool long_wick=(lower_ratio>=InpWickRatio && close_location>=0.50);
   const bool short_wick=(upper_ratio>=InpWickRatio && close_location<=0.50);
   if(long_wick==short_wick)
      return(false);
   g_wick_candidates++;

   double swing_low=DBL_MAX;
   double swing_high=-DBL_MAX;
   for(int i=1;i<=InpSwingBars;i++)
     {
      swing_low=MathMin(swing_low,rates[i].low);
      swing_high=MathMax(swing_high,rates[i].high);
     }
   if(!IsFinite(swing_low) || !IsFinite(swing_high) || swing_high<=swing_low)
     {
      g_invalid_inputs++;
      return(false);
     }
   const int direction=(long_wick ? 1 : -1);
   const bool touches_swing=(direction>0
                             ? bar.low<=swing_low+InpSwingAtrTolerance*atr
                             : bar.high>=swing_high-InpSwingAtrTolerance*atr);
   if(InpRequireSwing && !touches_swing)
     {
      g_swing_rejects++;
      return(false);
     }

   signal.fired=true;
   signal.decision_time=bar.time;
   signal.availability_time=availability_time;
   signal.direction=direction;
   signal.signal_open=bar.open;
   signal.signal_high=bar.high;
   signal.signal_low=bar.low;
   signal.signal_close=bar.close;
   signal.range=range;
   signal.body_ratio=body/range;
   signal.directional_wick_ratio=(direction>0 ? lower_ratio : upper_ratio);
   signal.close_location=close_location;
   signal.swing_level=(direction>0 ? swing_low : swing_high);
   signal.atr=atr;
   signal.atr_average=atr_average;
   signal.atr_ratio=atr_ratio;
   g_signals++;
   if(direction>0) g_long_signals++; else g_short_signals++;
   if(InpEnableTelemetry)
      PrintFormat("CBWR003_SIGNAL decision=%I64d availability=%I64d variant=%s direction=%s o=%.5f h=%.5f l=%.5f c=%.5f range=%.5f wick_ratio=%.6f body_ratio=%.6f close_location=%.6f swing=%.5f atr=%.5f atr_avg=%.5f atr_ratio=%.6f",
                  (long)signal.decision_time,(long)availability_time,InpVariantTag,
                  (direction>0 ? "LONG" : "SHORT"),bar.open,bar.high,bar.low,bar.close,
                  range,signal.directional_wick_ratio,signal.body_ratio,close_location,
                  signal.swing_level,atr,atr_average,atr_ratio);
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

double NormalizeVolumeDown(const double volume)
  {
   const double vmin=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN);
   const double vmax=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX);
   const double step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);
   if(!IsFinite(vmin) || !IsFinite(vmax) || !IsFinite(step) ||
      vmin<=0.0 || vmax<vmin || step<=0.0 || volume<vmin)
      return(0.0);
   const double bounded=MathMin(volume,vmax);
   const double units=MathFloor((bounded-vmin+1e-12)/step);
   return(NormalizeDouble(vmin+units*step,VolumeDigits(step)));
  }

double FloorToTick(const double price,const double tick_size)
  {
   return(MathFloor(price/tick_size+1e-10)*tick_size);
  }

double CeilToTick(const double price,const double tick_size)
  {
   return(MathCeil(price/tick_size-1e-10)*tick_size);
  }

bool OwnedPosition(ulong &ticket)
  {
   ticket=0;
   int owned=0;
   for(int i=PositionsTotal()-1;i>=0;i--)
     {
      const ulong current=PositionGetTicket(i);
      if(current==0 || !PositionSelectByTicket(current))
         continue;
      if(PositionGetString(POSITION_SYMBOL)==_Symbol && PositionGetInteger(POSITION_MAGIC)==InpMagic)
        {
         ticket=current;
         owned++;
        }
     }
   if(owned>1)
     {
      g_runtime_failed=true;
      return(false);
     }
   return(owned==1);
  }

bool AnySymbolExposure()
  {
   for(int i=PositionsTotal()-1;i>=0;i--)
     {
      const ulong ticket=PositionGetTicket(i);
      if(ticket>0 && PositionSelectByTicket(ticket) && PositionGetString(POSITION_SYMBOL)==_Symbol)
         return(true);
     }
   return(false);
  }

void RefreshRiskLocks(const datetime server_now)
  {
   const double equity=AccountInfoDouble(ACCOUNT_EQUITY);
   const int day=DayKey(server_now);
   const long week=WeekKey(server_now);
   if(g_day_key!=day)
     {
      g_day_key=day;
      g_day_start_equity=equity;
      g_day_locked=false;
     }
   if(g_week_key!=week)
     {
      g_week_key=week;
      g_week_start_equity=equity;
      g_week_locked=false;
     }
   if(g_day_start_equity>0.0 && equity<=g_day_start_equity*(1.0-InpDailyLossPct/100.0))
      g_day_locked=true;
   if(g_week_start_equity>0.0 && equity<=g_week_start_equity*(1.0-InpWeeklyLossPct/100.0))
      g_week_locked=true;
  }

bool CloseOwned(const string reason)
  {
   ulong ticket=0;
   if(!OwnedPosition(ticket))
      return(true);
   g_close_attempts++;
   g_pending_exit_reason=reason;
   g_trade.SetDeviationInPoints(InpDeviationPoints);
   if(!g_trade.PositionClose(ticket,InpDeviationPoints))
     {
      g_close_rejects++;
      PrintFormat("CBWR003_CLOSE_REJECT reason=%s ticket=%I64u retcode=%u",reason,ticket,g_trade.ResultRetcode());
      return(false);
     }
   const uint retcode=g_trade.ResultRetcode();
   if(retcode!=TRADE_RETCODE_DONE && retcode!=TRADE_RETCODE_DONE_PARTIAL)
     {
      g_close_rejects++;
      PrintFormat("CBWR003_CLOSE_REJECT reason=%s ticket=%I64u retcode=%u",reason,ticket,retcode);
      return(false);
     }
   g_closes++;
   PrintFormat("CBWR003_CLOSE_REQUEST reason=%s ticket=%I64u retcode=%u",reason,ticket,retcode);
   return(true);
  }

bool MoveBreakEven(const ulong ticket)
  {
   if(!PositionSelectByTicket(ticket) || g_initial_risk<=0.0 || g_entry_price<=0.0)
      return(false);
   const ENUM_POSITION_TYPE position_type=(ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE);
   const double current_sl=PositionGetDouble(POSITION_SL);
   const double current_tp=PositionGetDouble(POSITION_TP);
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick))
      return(false);
   const double point=SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   const double tick_size=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);
   if(point<=0.0 || tick_size<=0.0)
      return(false);
   const bool is_long=(position_type==POSITION_TYPE_BUY);
   const double exit_quote=(is_long ? tick.bid : tick.ask);
   const double favorable=(is_long ? exit_quote-g_entry_price : g_entry_price-exit_quote);
   const double adverse=MathMax(0.0,-favorable);
   g_mfe_points=MathMax(g_mfe_points,MathMax(0.0,favorable)/point);
   g_mae_points=MathMax(g_mae_points,adverse/point);
   if(favorable<InpBETriggerR*g_initial_risk)
      return(false);
   const double raw_be=(is_long
                        ? g_entry_price+g_entry_spread_points*point
                        : g_entry_price-g_entry_spread_points*point);
   const double new_sl=(is_long ? CeilToTick(raw_be,tick_size) : FloorToTick(raw_be,tick_size));
   if((is_long && current_sl>=new_sl-point*0.1) || (!is_long && current_sl>0.0 && current_sl<=new_sl+point*0.1))
      return(false);
   const double min_distance=(double)MathMax(SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL),0)*point;
   if((is_long && tick.bid-new_sl<min_distance) || (!is_long && new_sl-tick.ask<min_distance))
      return(false);
   if(!g_trade.PositionModify(ticket,new_sl,current_tp))
      return(false);
   const uint retcode=g_trade.ResultRetcode();
   if(retcode!=TRADE_RETCODE_DONE && retcode!=TRADE_RETCODE_NO_CHANGES)
      return(false);
   g_be_moves++;
   PrintFormat("CBWR003_BE ticket=%I64u sl=%.5f trigger_r=%.3f mfe_points=%.1f",
               ticket,new_sl,InpBETriggerR,g_mfe_points);
   return(true);
  }

void ManagePosition(const datetime server_now,const datetime current_bar_open)
  {
   ulong ticket=0;
   if(!OwnedPosition(ticket))
      return;
   MoveBreakEven(ticket);
   MqlDateTime now_parts;
   TimeToStruct(server_now,now_parts);
   const int minute=now_parts.hour*60+now_parts.min;
   string exit_reason="";
   if(now_parts.day_of_week==5 && minute>=InpFridayFlatHour*60)
      exit_reason="FRIDAY_FLAT";
   else if(minute>=InpDailyFlatHour*60+InpDailyFlatMinute)
      exit_reason="DAILY_FLAT";
   else
     {
      datetime entry_time=g_entry_time;
      if(entry_time<=0 && PositionSelectByTicket(ticket))
         entry_time=(datetime)PositionGetInteger(POSITION_TIME);
      if(entry_time>0)
        {
         const int held_bars=iBarShift(_Symbol,PERIOD_M15,entry_time,false);
         if(held_bars>=InpTimeStopBars)
            exit_reason="TIME_STOP";
        }
     }
   if(exit_reason=="" || g_last_close_attempt_bar==current_bar_open)
      return;
   g_last_close_attempt_bar=current_bar_open;
   CloseOwned(exit_reason);
  }

bool EntryWindowOpen(const datetime server_now)
  {
   MqlDateTime p;
   TimeToStruct(server_now,p);
   if(p.day_of_week==0 || p.day_of_week==6)
      return(false);
   const int minute=p.hour*60+p.min;
   if(p.day_of_week==5 && minute>=InpFridayFlatHour*60)
      return(false);
   return(minute<InpDailyFlatHour*60+InpDailyFlatMinute);
  }

bool SubmitEntry(const SignalDecision &signal)
  {
   if(!signal.fired || AnySymbolExposure() || !EntryWindowOpen(signal.availability_time))
      return(false);
   if(g_day_locked || g_week_locked)
     {
      g_risk_lock_skips++;
      return(false);
     }
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick) || !IsFinite(tick.ask) || !IsFinite(tick.bid) ||
      tick.ask<=tick.bid || tick.bid<=0.0)
      return(false);
   const double point=SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   const double tick_size=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);
   if(point<=0.0 || tick_size<=0.0)
      return(false);
   const double spread_points=(tick.ask-tick.bid)/point;
   if(!IsFinite(spread_points) || spread_points>InpMaxSpreadPoints)
     {
      g_spread_rejects++;
      return(false);
     }
   const double entry=(signal.direction>0 ? tick.ask : tick.bid);
   const double raw_stop=(signal.direction>0
                          ? signal.signal_low-InpSLATRBuffer*signal.atr
                          : signal.signal_high+InpSLATRBuffer*signal.atr);
   double risk_distance=(signal.direction>0 ? entry-raw_stop : raw_stop-entry);
   risk_distance=MathMax(InpMinSLATR*signal.atr,MathMin(risk_distance,InpMaxSLATR*signal.atr));
   if(!IsFinite(risk_distance) || risk_distance<=0.0)
      return(false);
   const double raw_sl=entry-signal.direction*risk_distance;
   const double raw_tp=entry+signal.direction*InpTargetR*risk_distance;
   const double sl=(signal.direction>0 ? FloorToTick(raw_sl,tick_size) : CeilToTick(raw_sl,tick_size));
   const double tp=(signal.direction>0 ? CeilToTick(raw_tp,tick_size) : FloorToTick(raw_tp,tick_size));
   const double minimum_distance=(double)MathMax(MathMax(SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL),
                                                         SymbolInfoInteger(_Symbol,SYMBOL_TRADE_FREEZE_LEVEL)),0)*point;
   if(MathAbs(entry-sl)<minimum_distance || MathAbs(tp-entry)<minimum_distance)
      return(false);

   const ENUM_ORDER_TYPE order_type=(signal.direction>0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL);
   double one_lot_loss=0.0;
   if(!OrderCalcProfit(order_type,_Symbol,1.0,entry,sl,one_lot_loss) ||
      !IsFinite(one_lot_loss) || one_lot_loss>=0.0)
      return(false);
   const double equity=AccountInfoDouble(ACCOUNT_EQUITY);
   const double volume=NormalizeVolumeDown(equity*(InpRiskPercent/100.0)/MathAbs(one_lot_loss));
   if(volume<=0.0)
      return(false);
   double margin=0.0;
   if(!OrderCalcMargin(order_type,_Symbol,volume,entry,margin) || !IsFinite(margin) ||
      margin>AccountInfoDouble(ACCOUNT_MARGIN_FREE))
      return(false);

   g_trade.SetExpertMagicNumber(InpMagic);
   g_trade.SetDeviationInPoints(InpDeviationPoints);
   g_trade.SetTypeFillingBySymbol(_Symbol);
   const bool sent=g_trade.PositionOpen(_Symbol,order_type,volume,entry,sl,tp,InpVariantTag);
   const uint retcode=g_trade.ResultRetcode();
   if(!sent || (retcode!=TRADE_RETCODE_DONE && retcode!=TRADE_RETCODE_DONE_PARTIAL))
     {
      g_entry_rejects++;
      PrintFormat("CBWR003_ENTRY_REJECT direction=%s volume=%.2f entry=%.5f sl=%.5f tp=%.5f spread_points=%.1f retcode=%u",
                  (signal.direction>0 ? "LONG" : "SHORT"),volume,entry,sl,tp,spread_points,retcode);
      return(false);
     }
   g_entries++;
   g_entry_time=signal.availability_time;
   g_entry_price=(g_trade.ResultPrice()>0.0 ? g_trade.ResultPrice() : entry);
   g_initial_sl=sl;
   g_initial_risk=MathAbs(g_entry_price-sl);
   g_entry_spread_points=spread_points;
   g_mfe_points=0.0;
   g_mae_points=0.0;
   g_pending_exit_reason="";
   PrintFormat("CBWR003_ENTRY decision=%I64d direction=%s volume=%.2f entry=%.5f sl=%.5f tp=%.5f initial_risk=%.5f risk_pct=%.3f spread_points=%.1f retcode=%u",
               (long)signal.decision_time,(signal.direction>0 ? "LONG" : "SHORT"),volume,
               g_entry_price,sl,tp,g_initial_risk,InpRiskPercent,spread_points,retcode);
   return(true);
  }

string ExitReasonName(const long reason)
  {
   if(reason==DEAL_REASON_SL) return("SL");
   if(reason==DEAL_REASON_TP) return("TP");
   if(reason==DEAL_REASON_EXPERT && g_pending_exit_reason!="") return(g_pending_exit_reason);
   return(StringFormat("DEAL_REASON_%d",(int)reason));
  }

void OnTradeTransaction(const MqlTradeTransaction &trans,
                        const MqlTradeRequest &request,
                        const MqlTradeResult &result)
  {
   if(trans.type!=TRADE_TRANSACTION_DEAL_ADD || trans.deal==0 || !HistoryDealSelect(trans.deal))
      return;
   if(HistoryDealGetString(trans.deal,DEAL_SYMBOL)!=_Symbol ||
      HistoryDealGetInteger(trans.deal,DEAL_MAGIC)!=InpMagic)
      return;
   const long entry_kind=HistoryDealGetInteger(trans.deal,DEAL_ENTRY);
   if(entry_kind!=DEAL_ENTRY_OUT && entry_kind!=DEAL_ENTRY_OUT_BY)
      return;
   const long reason=HistoryDealGetInteger(trans.deal,DEAL_REASON);
   const double price=HistoryDealGetDouble(trans.deal,DEAL_PRICE);
   const double profit=HistoryDealGetDouble(trans.deal,DEAL_PROFIT);
   const double commission=HistoryDealGetDouble(trans.deal,DEAL_COMMISSION);
   const double swap=HistoryDealGetDouble(trans.deal,DEAL_SWAP);
   const datetime stamp=(datetime)HistoryDealGetInteger(trans.deal,DEAL_TIME);
   PrintFormat("CBWR003_EXIT time=%I64d deal=%I64u reason=%s price=%.5f profit=%.2f commission=%.2f swap=%.2f mfe_points=%.1f mae_points=%.1f equity=%.2f",
               (long)stamp,trans.deal,ExitReasonName(reason),price,profit,commission,swap,
               g_mfe_points,g_mae_points,AccountInfoDouble(ACCOUNT_EQUITY));
   ulong owned_ticket=0;
   if(!OwnedPosition(owned_ticket))
     {
      g_entry_time=0;
      g_entry_price=0.0;
      g_initial_sl=0.0;
      g_initial_risk=0.0;
      g_entry_spread_points=0.0;
      g_pending_exit_reason="";
     }
  }

bool InputsAreFrozen()
  {
   const bool variant_ok=((InpVariantTag==PRIMARY_VARIANT && InpRequireSwing) ||
                          (InpVariantTag==CONTROL_VARIANT && !InpRequireSwing));
   return(InpResearchAutoMode && InpEnableTelemetry &&
          InpHypothesisId==EXPECTED_HYPOTHESIS && variant_ok &&
          InpSwingBars==8 && MathAbs(InpWickRatio-0.60)<1e-12 &&
          MathAbs(InpBodyRatio-0.35)<1e-12 && MathAbs(InpSwingAtrTolerance-0.15)<1e-12 &&
          InpATRPeriod==14 && InpATRAverageBars==50 &&
          MathAbs(InpATRMinMult-0.70)<1e-12 && MathAbs(InpATRMaxMult-2.20)<1e-12 &&
          MathAbs(InpSLATRBuffer-0.25)<1e-12 && MathAbs(InpMinSLATR-1.20)<1e-12 &&
          MathAbs(InpMaxSLATR-2.80)<1e-12 && MathAbs(InpTargetR-1.60)<1e-12 &&
          InpTimeStopBars==12 && MathAbs(InpBETriggerR-0.90)<1e-12 &&
          MathAbs(InpRiskPercent-0.60)<1e-12 && InpMaxSpreadPoints==55 &&
          MathAbs(InpDailyLossPct-1.50)<1e-12 && MathAbs(InpWeeklyLossPct-3.50)<1e-12 &&
          InpDailyFlatHour==21 && InpDailyFlatMinute==50 && InpFridayFlatHour==20 &&
          InpDeviationPoints==10 && InpMagic==5604703);
  }

int OnInit()
  {
   if(_Period!=PERIOD_M15 || !InputsAreFrozen())
      return(INIT_PARAMETERS_INCORRECT);
   g_atr_handle=iATR(_Symbol,PERIOD_M15,InpATRPeriod);
   if(g_atr_handle==INVALID_HANDLE)
      return(INIT_FAILED);
   if(!EmitSeriesProof())
      return(INIT_FAILED);
   g_trade.SetExpertMagicNumber(InpMagic);
   g_trade.SetDeviationInPoints(InpDeviationPoints);
   g_trade.SetTypeFillingBySymbol(_Symbol);
   const datetime now=TimeCurrent();
   const double equity=AccountInfoDouble(ACCOUNT_EQUITY);
   g_day_key=DayKey(now);
   g_week_key=WeekKey(now);
   g_day_start_equity=equity;
   g_week_start_equity=equity;
   if(!CurrentBarOpen(g_last_bar_open) || g_last_bar_open<=0)
      return(INIT_FAILED);
   PrintFormat("CBWR003_INIT ea=%s hypothesis=%s variant=%s symbol=%s timeframe=M15 require_swing=%s",
               EA_NAME,InpHypothesisId,InpVariantTag,_Symbol,(InpRequireSwing ? "true" : "false"));
   return(INIT_SUCCEEDED);
  }

void OnDeinit(const int reason)
  {
   if(g_atr_handle!=INVALID_HANDLE)
      IndicatorRelease(g_atr_handle);
   PrintFormat("CBWR003_SUMMARY reason=%d runtime_failed=%s closed_bars=%I64d wick_candidates=%I64d swing_rejects=%I64d atr_rejects=%I64d spread_rejects=%I64d risk_lock_skips=%I64d signals=%I64d long=%I64d short=%I64d entries=%I64d entry_rejects=%I64d be_moves=%I64d close_attempts=%I64d close_rejects=%I64d closes=%I64d invalid=%I64d",
               reason,(g_runtime_failed ? "true" : "false"),g_closed_bars,g_wick_candidates,
               g_swing_rejects,g_atr_rejects,g_spread_rejects,g_risk_lock_skips,g_signals,
               g_long_signals,g_short_signals,g_entries,g_entry_rejects,g_be_moves,
               g_close_attempts,g_close_rejects,g_closes,g_invalid_inputs);
  }

void OnTick()
  {
   datetime current_bar_open=0;
   if(!CurrentBarOpen(current_bar_open) || current_bar_open<=0)
      return;
   const datetime server_now=TimeCurrent();
   RefreshRiskLocks(server_now);
   ManagePosition(server_now,current_bar_open);
   if(current_bar_open==g_last_bar_open)
      return;
   g_last_bar_open=current_bar_open;
   if(AnySymbolExposure())
      return;
   SignalDecision signal;
   if(BuildSignal(current_bar_open,signal) && signal.fired)
      SubmitEntry(signal);
  }
