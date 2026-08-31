//+------------------------------------------------------------------+
//| EA_CompBreak_XAU_M15_V2.mq5                                    |
//| HYP-CBC-XAUUSD-M15-001: stateful compression-break continuation |
//+------------------------------------------------------------------+
#property strict
#property version   "1.00"
#property description "Untuned closed-bar XAUUSD M15 compression-break continuation research EA"

#include <Trade/Trade.mqh>

input group "--- Frozen research authority ---"
input bool   InpResearchAutoMode=false;
input bool   InpEnableTelemetry=true;
input string InpHypothesisId="HYP-CBC-XAUUSD-M15-001";
input string InpVariantTag="COMP7_PRIMARY";
input bool   InpUseCompression=true;

input group "--- Frozen state and signal ---"
input int    InpCompressionBars=7;
input double InpCompressionATRMax=1.15;
input double InpCompressionBodyMax=0.55;
input double InpBreakBufferATR=0.10;
input double InpBreakBodyMin=0.50;
input int    InpExpiryBars=9;
input int    InpATRPeriod=14;

input group "--- Frozen exit and risk ---"
input double InpSLATRBuffer=0.20;
input double InpMinSLATR=1.30;
input double InpMaxSLATR=2.60;
input double InpBETriggerR=1.10;
input double InpBEOffsetR=0.15;
input double InpTrailStartR=1.80;
input double InpTrailATRMult=0.90;
input int    InpTimeStopBars=16;
input double InpRiskPercent=0.45;
input double InpMaxNotionalMult=4.50;
input double InpMaxMarginUsagePct=12.0;
input int    InpMaxSpreadPoints=48;
input double InpDailyLossPct=1.20;
input double InpWeeklyLossPct=3.00;
input int    InpLossStreakLimit=4;
input int    InpCooldownHours=8;
input int    InpDailyFlatHour=21;
input int    InpDailyFlatMinute=45;
input int    InpFridayFlatHour=19;
input int    InpFridayFlatMinute=30;
input int    InpDeviationPoints=12;
input long   InpMagic=5604801;

const string EA_NAME="EA_CompBreak_XAU_M15_V2";
const string EXPECTED_HYPOTHESIS="HYP-CBC-XAUUSD-M15-001";
const string PRIMARY_VARIANT="COMP7_PRIMARY";
const string CONTROL_VARIANT="BODY50_CONTROL";
const string LOG_PREFIX="CBC001";

enum ResearchState
  {
   STATE_IDLE=0,
   STATE_COMPRESSION=1,
   STATE_BREAK_CONFIRMED=2,
   STATE_IN_POSITION=3
  };

struct BreakSignal
  {
   bool fired;
   datetime decision_time;
   datetime availability_time;
   int direction;
   double signal_open;
   double signal_high;
   double signal_low;
   double signal_close;
   double signal_range;
   double body_ratio;
   double box_high;
   double box_low;
   double atr;
   int box_age;
  };

CTrade g_trade;
int g_atr_handle=INVALID_HANDLE;
ResearchState g_state=STATE_IDLE;
datetime g_last_bar_open=0;
datetime g_last_decision_time=0;
datetime g_box_detect_time=0;
double g_box_high=0.0;
double g_box_low=0.0;
double g_box_atr=0.0;
int g_box_age=0;
datetime g_entry_time=0;
datetime g_last_close_attempt_bar=0;
double g_entry_price=0.0;
double g_initial_sl=0.0;
double g_initial_risk=0.0;
double g_entry_spread_points=0.0;
double g_mfe_points=0.0;
double g_mae_points=0.0;
double g_entry_margin_usage_pct=0.0;
bool g_trail_armed=false;
string g_pending_exit_reason="";
int g_day_key=0;
long g_week_key=0;
double g_day_start_equity=0.0;
double g_week_start_equity=0.0;
bool g_day_locked=false;
bool g_week_locked=false;
int g_consecutive_losses=0;
datetime g_cooldown_until=0;
bool g_runtime_failed=false;

long g_closed_bars=0;
long g_compressions=0;
long g_compression_rejects=0;
long g_expired_boxes=0;
long g_breaks=0;
long g_long_signals=0;
long g_short_signals=0;
long g_spread_rejects=0;
long g_risk_lock_skips=0;
long g_cooldown_skips=0;
long g_entries=0;
long g_entry_rejects=0;
long g_be_moves=0;
long g_trail_arms=0;
long g_trail_moves=0;
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
   const int required=InpCompressionBars+3;
   ArraySetAsSeries(rates,true);
   const int copied=CopyRates(_Symbol,PERIOD_M15,1,required,rates);
   if(copied<required)
      return(false);
   for(int i=0;i<required;i++)
     {
      if(rates[i].time<=0 || rates[i].high<=rates[i].low || rates[i].open<=0.0 ||
         rates[i].close<=0.0 || rates[i].tick_volume<=0)
         return(false);
     }
   return(true);
  }

bool LoadAtr(double &atr)
  {
   atr=0.0;
   if(g_atr_handle==INVALID_HANDLE || BarsCalculated(g_atr_handle)<InpATRPeriod+2)
      return(false);
   double values[];
   ArraySetAsSeries(values,true);
   if(CopyBuffer(g_atr_handle,0,1,1,values)!=1)
      return(false);
   atr=values[0];
   return(IsFinite(atr) && atr>0.0);
  }

void ResetBox(const string reason)
  {
   if(InpEnableTelemetry && g_state!=STATE_IDLE)
      PrintFormat("CBC001_STATE from=%d to=0 reason=%s detect=%I64d age=%d box_high=%.5f box_low=%.5f",
                  (int)g_state,reason,(long)g_box_detect_time,g_box_age,g_box_high,g_box_low);
   g_state=STATE_IDLE;
   g_box_detect_time=0;
   g_box_high=0.0;
   g_box_low=0.0;
   g_box_atr=0.0;
   g_box_age=0;
  }

bool DetectCompression(const MqlRates &rates[],const double atr)
  {
   double box_high=-DBL_MAX;
   double box_low=DBL_MAX;
   for(int i=1;i<=InpCompressionBars;i++)
     {
      const double range=rates[i].high-rates[i].low;
      if(range<=0.0 || MathAbs(rates[i].close-rates[i].open)/range>InpCompressionBodyMax)
        {
         g_compression_rejects++;
         return(false);
        }
      box_high=MathMax(box_high,rates[i].high);
      box_low=MathMin(box_low,rates[i].low);
     }
   const double box_range=box_high-box_low;
   if(!IsFinite(box_high) || !IsFinite(box_low) || box_range<=0.0 || box_range>InpCompressionATRMax*atr)
     {
      g_compression_rejects++;
      return(false);
     }
   g_state=STATE_COMPRESSION;
   g_box_detect_time=rates[0].time;
   g_box_high=box_high;
   g_box_low=box_low;
   g_box_atr=atr;
   g_box_age=1;
   g_compressions++;
   if(InpEnableTelemetry)
      PrintFormat("CBC001_STATE from=0 to=1 reason=COMPRESSION detect=%I64d age=1 box_first=%I64d box_last=%I64d box_high=%.5f box_low=%.5f box_range=%.5f atr=%.5f range_atr=%.6f",
                  (long)g_box_detect_time,(long)rates[InpCompressionBars].time,(long)rates[1].time,
                  g_box_high,g_box_low,box_range,atr,box_range/atr);
   return(true);
  }

bool EvaluateBreak(const MqlRates &bar,const double atr,const datetime availability_time,BreakSignal &signal)
  {
   ZeroMemory(signal);
   const double range=bar.high-bar.low;
   if(range<=0.0)
      return(false);
   const double body_ratio=MathAbs(bar.close-bar.open)/range;
   if(body_ratio<InpBreakBodyMin)
      return(false);
   int direction=0;
   if(bar.close>g_box_high+InpBreakBufferATR*atr)
      direction=1;
   else if(bar.close<g_box_low-InpBreakBufferATR*atr)
      direction=-1;
   if(direction==0)
      return(false);
   signal.fired=true;
   signal.decision_time=bar.time;
   signal.availability_time=availability_time;
   signal.direction=direction;
   signal.signal_open=bar.open;
   signal.signal_high=bar.high;
   signal.signal_low=bar.low;
   signal.signal_close=bar.close;
   signal.signal_range=range;
   signal.body_ratio=body_ratio;
   signal.box_high=g_box_high;
   signal.box_low=g_box_low;
   signal.atr=atr;
   signal.box_age=g_box_age;
   g_state=STATE_BREAK_CONFIRMED;
   g_breaks++;
   if(direction>0) g_long_signals++; else g_short_signals++;
   if(InpEnableTelemetry)
      PrintFormat("CBC001_BREAK decision=%I64d availability=%I64d variant=%s direction=%s age=%d o=%.5f h=%.5f l=%.5f c=%.5f body_ratio=%.6f box_high=%.5f box_low=%.5f atr=%.5f buffer=%.5f",
                  (long)bar.time,(long)availability_time,InpVariantTag,(direction>0 ? "LONG" : "SHORT"),
                  g_box_age,bar.open,bar.high,bar.low,bar.close,body_ratio,g_box_high,g_box_low,atr,InpBreakBufferATR*atr);
   return(true);
  }

bool BuildSignal(const datetime availability_time,BreakSignal &signal)
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
   if(!LoadAtr(atr))
     {
      g_invalid_inputs++;
      return(false);
     }

   if(!InpUseCompression)
     {
      g_box_high=bar.high;
      g_box_low=bar.low;
      g_box_atr=atr;
      g_box_detect_time=bar.time;
      g_box_age=1;
      g_state=STATE_COMPRESSION;
      const double range=bar.high-bar.low;
      if(range<=0.0 || MathAbs(bar.close-bar.open)/range<InpBreakBodyMin || bar.close==bar.open)
        {
         ResetBox("CONTROL_NO_BODY_BREAK");
         return(false);
        }
      const int direction=(bar.close>bar.open ? 1 : -1);
      signal.fired=true;
      signal.decision_time=bar.time;
      signal.availability_time=availability_time;
      signal.direction=direction;
      signal.signal_open=bar.open;
      signal.signal_high=bar.high;
      signal.signal_low=bar.low;
      signal.signal_close=bar.close;
      signal.signal_range=range;
      signal.body_ratio=MathAbs(bar.close-bar.open)/range;
      signal.box_high=bar.high;
      signal.box_low=bar.low;
      signal.atr=atr;
      signal.box_age=1;
      g_state=STATE_BREAK_CONFIRMED;
      g_breaks++;
      if(direction>0) g_long_signals++; else g_short_signals++;
      return(true);
     }

   if(g_state==STATE_IDLE)
     {
      if(!DetectCompression(rates,atr))
         return(false);
     }
   else if(g_state==STATE_COMPRESSION && bar.time>g_box_detect_time)
      g_box_age++;

   if(g_state==STATE_COMPRESSION && EvaluateBreak(bar,atr,availability_time,signal))
      return(true);
   if(g_state==STATE_COMPRESSION && g_box_age>=InpExpiryBars)
     {
      g_expired_boxes++;
      ResetBox("EXPIRY");
     }
   return(false);
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
      PrintFormat("CBC001_CLOSE_REJECT reason=%s ticket=%I64u retcode=%u",reason,ticket,g_trade.ResultRetcode());
      return(false);
     }
   const uint retcode=g_trade.ResultRetcode();
   if(retcode!=TRADE_RETCODE_DONE && retcode!=TRADE_RETCODE_DONE_PARTIAL)
     {
      g_close_rejects++;
      PrintFormat("CBC001_CLOSE_REJECT reason=%s ticket=%I64u retcode=%u",reason,ticket,retcode);
      return(false);
     }
   g_closes++;
   PrintFormat("CBC001_CLOSE_REQUEST reason=%s ticket=%I64u retcode=%u",reason,ticket,retcode);
   return(true);
  }

bool ModifyOwnedStop(const ulong ticket,const double proposed_sl,const string reason)
  {
   if(!PositionSelectByTicket(ticket))
      return(false);
   const ENUM_POSITION_TYPE position_type=(ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE);
   const bool is_long=(position_type==POSITION_TYPE_BUY);
   const double current_sl=PositionGetDouble(POSITION_SL);
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick))
      return(false);
   const double point=SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   const double tick_size=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);
   if(point<=0.0 || tick_size<=0.0)
      return(false);
   const double new_sl=(is_long ? FloorToTick(proposed_sl,tick_size) : CeilToTick(proposed_sl,tick_size));
   if((is_long && current_sl>=new_sl-point*0.1) || (!is_long && current_sl>0.0 && current_sl<=new_sl+point*0.1))
      return(false);
   const double min_distance=(double)MathMax(MathMax(SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL),
                                                     SymbolInfoInteger(_Symbol,SYMBOL_TRADE_FREEZE_LEVEL)),0)*point;
   if((is_long && tick.bid-new_sl<min_distance) || (!is_long && new_sl-tick.ask<min_distance))
      return(false);
   if(!g_trade.PositionModify(ticket,new_sl,0.0))
      return(false);
   const uint retcode=g_trade.ResultRetcode();
   if(retcode!=TRADE_RETCODE_DONE && retcode!=TRADE_RETCODE_NO_CHANGES)
      return(false);
   PrintFormat("CBC001_STOP_MOVE reason=%s ticket=%I64u sl=%.5f mfe_points=%.1f mae_points=%.1f",
               reason,ticket,new_sl,g_mfe_points,g_mae_points);
   return(true);
  }

void UpdateExcursionAndStops(const ulong ticket,const bool new_bar)
  {
   if(!PositionSelectByTicket(ticket) || g_initial_risk<=0.0 || g_entry_price<=0.0)
      return;
   const ENUM_POSITION_TYPE position_type=(ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE);
   const bool is_long=(position_type==POSITION_TYPE_BUY);
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick))
      return;
   const double point=SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   if(point<=0.0)
      return;
   const double exit_quote=(is_long ? tick.bid : tick.ask);
   const double favorable=(is_long ? exit_quote-g_entry_price : g_entry_price-exit_quote);
   g_mfe_points=MathMax(g_mfe_points,MathMax(0.0,favorable)/point);
   g_mae_points=MathMax(g_mae_points,MathMax(0.0,-favorable)/point);

   if(favorable>=InpBETriggerR*g_initial_risk)
     {
      const double be=(is_long ? g_entry_price+InpBEOffsetR*g_initial_risk
                               : g_entry_price-InpBEOffsetR*g_initial_risk);
      if(ModifyOwnedStop(ticket,be,"BREAKEVEN_PLUS"))
         g_be_moves++;
     }
   if(!g_trail_armed && favorable>=InpTrailStartR*g_initial_risk)
     {
      g_trail_armed=true;
      g_trail_arms++;
      PrintFormat("CBC001_TRAIL_ARM ticket=%I64u trigger_r=%.3f mfe_points=%.1f",ticket,InpTrailStartR,g_mfe_points);
     }
   if(!new_bar || !g_trail_armed)
      return;
   MqlRates closed[];
   ArraySetAsSeries(closed,true);
   if(CopyRates(_Symbol,PERIOD_M15,1,1,closed)!=1)
      return;
   double atr=0.0;
   if(!LoadAtr(atr))
      return;
   const double trail=(is_long ? closed[0].close-InpTrailATRMult*atr
                               : closed[0].close+InpTrailATRMult*atr);
   if(ModifyOwnedStop(ticket,trail,"ATR_TRAIL"))
      g_trail_moves++;
  }

void ManagePosition(const datetime server_now,const datetime current_bar_open,const bool new_bar)
  {
   ulong ticket=0;
   if(!OwnedPosition(ticket))
      return;
   g_state=STATE_IN_POSITION;
   UpdateExcursionAndStops(ticket,new_bar);
   MqlDateTime now_parts;
   TimeToStruct(server_now,now_parts);
   const int minute=now_parts.hour*60+now_parts.min;
   string exit_reason="";
   if(now_parts.day_of_week==5 && minute>=InpFridayFlatHour*60+InpFridayFlatMinute)
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
   if(p.day_of_week==5 && minute>=InpFridayFlatHour*60+InpFridayFlatMinute)
      return(false);
   return(minute<InpDailyFlatHour*60+InpDailyFlatMinute);
  }

bool SubmitEntry(const BreakSignal &signal)
  {
   if(!signal.fired || AnySymbolExposure() || !EntryWindowOpen(signal.availability_time))
      return(false);
   if(g_day_locked || g_week_locked)
     {
      g_risk_lock_skips++;
      return(false);
     }
   if(signal.availability_time<g_cooldown_until)
     {
      g_cooldown_skips++;
      return(false);
     }
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick) || !IsFinite(tick.ask) || !IsFinite(tick.bid) ||
      tick.ask<=tick.bid || tick.bid<=0.0)
      return(false);
   const double point=SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   const double tick_size=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);
   const double contract_size=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_CONTRACT_SIZE);
   if(point<=0.0 || tick_size<=0.0 || contract_size<=0.0)
      return(false);
   const double spread_points=(tick.ask-tick.bid)/point;
   if(!IsFinite(spread_points) || spread_points>InpMaxSpreadPoints)
     {
      g_spread_rejects++;
      return(false);
     }
   const double entry=(signal.direction>0 ? tick.ask : tick.bid);
   const double structural_stop=(signal.direction>0
                                 ? signal.box_low-InpSLATRBuffer*signal.atr
                                 : signal.box_high+InpSLATRBuffer*signal.atr);
   double risk_distance=(signal.direction>0 ? entry-structural_stop : structural_stop-entry);
   if(!InpUseCompression)
      risk_distance=1.80*signal.atr;
   risk_distance=MathMax(InpMinSLATR*signal.atr,MathMin(risk_distance,InpMaxSLATR*signal.atr));
   if(!IsFinite(risk_distance) || risk_distance<=0.0)
      return(false);
   const double raw_sl=entry-signal.direction*risk_distance;
   const double sl=(signal.direction>0 ? FloorToTick(raw_sl,tick_size) : CeilToTick(raw_sl,tick_size));
   const double minimum_distance=(double)MathMax(MathMax(SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL),
                                                         SymbolInfoInteger(_Symbol,SYMBOL_TRADE_FREEZE_LEVEL)),0)*point;
   if(MathAbs(entry-sl)<minimum_distance)
      return(false);

   const ENUM_ORDER_TYPE order_type=(signal.direction>0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL);
   double one_lot_loss=0.0;
   if(!OrderCalcProfit(order_type,_Symbol,1.0,entry,sl,one_lot_loss) ||
      !IsFinite(one_lot_loss) || one_lot_loss>=0.0)
      return(false);
   double margin_per_lot=0.0;
   if(!OrderCalcMargin(order_type,_Symbol,1.0,entry,margin_per_lot) ||
      !IsFinite(margin_per_lot) || margin_per_lot<=0.0)
      return(false);
   const double equity=AccountInfoDouble(ACCOUNT_EQUITY);
   const double free_margin=AccountInfoDouble(ACCOUNT_MARGIN_FREE);
   if(equity<=0.0 || free_margin<=0.0)
      return(false);
   const double volume_risk=equity*(InpRiskPercent/100.0)/MathAbs(one_lot_loss);
   const double volume_notional=(equity*InpMaxNotionalMult)/(entry*contract_size);
   const double volume_margin=(free_margin*(InpMaxMarginUsagePct/100.0))/margin_per_lot;
   const double raw_volume=MathMin(volume_risk,MathMin(volume_notional,volume_margin));
   const double volume=NormalizeVolumeDown(raw_volume);
   if(volume<=0.0)
      return(false);
   double margin=0.0;
   if(!OrderCalcMargin(order_type,_Symbol,volume,entry,margin) || !IsFinite(margin) ||
      margin>free_margin*(InpMaxMarginUsagePct/100.0)+0.01)
      return(false);
   const double notional=volume*entry*contract_size;
   if(notional>equity*InpMaxNotionalMult+0.01)
      return(false);

   g_trade.SetExpertMagicNumber(InpMagic);
   g_trade.SetDeviationInPoints(InpDeviationPoints);
   g_trade.SetTypeFillingBySymbol(_Symbol);
   const bool sent=g_trade.PositionOpen(_Symbol,order_type,volume,entry,sl,0.0,InpVariantTag);
   const uint retcode=g_trade.ResultRetcode();
   if(!sent || (retcode!=TRADE_RETCODE_DONE && retcode!=TRADE_RETCODE_DONE_PARTIAL))
     {
      g_entry_rejects++;
      PrintFormat("CBC001_ENTRY_REJECT direction=%s volume=%.2f entry=%.5f sl=%.5f spread_points=%.1f margin=%.2f retcode=%u",
                  (signal.direction>0 ? "LONG" : "SHORT"),volume,entry,sl,spread_points,margin,retcode);
      return(false);
     }
   g_entries++;
   g_state=STATE_IN_POSITION;
   g_entry_time=signal.availability_time;
   g_entry_price=(g_trade.ResultPrice()>0.0 ? g_trade.ResultPrice() : entry);
   g_initial_sl=sl;
   g_initial_risk=MathAbs(g_entry_price-sl);
   g_entry_spread_points=spread_points;
   g_entry_margin_usage_pct=100.0*margin/free_margin;
   g_mfe_points=0.0;
   g_mae_points=0.0;
   g_trail_armed=false;
   g_pending_exit_reason="";
   PrintFormat("CBC001_ENTRY decision=%I64d direction=%s age=%d volume=%.2f entry=%.5f sl=%.5f tp=0 initial_risk=%.5f risk_pct=%.3f spread_points=%.1f volume_risk=%.4f volume_notional=%.4f volume_margin=%.4f notional=%.2f notional_equity_mult=%.4f margin=%.2f margin_usage_pct=%.4f equity=%.2f retcode=%u",
               (long)signal.decision_time,(signal.direction>0 ? "LONG" : "SHORT"),signal.box_age,
               volume,g_entry_price,sl,g_initial_risk,InpRiskPercent,spread_points,volume_risk,
               volume_notional,volume_margin,notional,notional/equity,margin,g_entry_margin_usage_pct,equity,retcode);
   return(true);
  }

string ExitReasonName(const long reason)
  {
   if(reason==DEAL_REASON_SL) return("SL");
   if(reason==DEAL_REASON_TP) return("TP_UNEXPECTED");
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
   const double net=profit+commission+swap;
   const datetime stamp=(datetime)HistoryDealGetInteger(trans.deal,DEAL_TIME);
   if(net<0.0)
      g_consecutive_losses++;
   else
      g_consecutive_losses=0;
   if(g_consecutive_losses>=InpLossStreakLimit)
     {
      g_cooldown_until=stamp+InpCooldownHours*3600;
      PrintFormat("CBC001_COOLDOWN start=%I64d until=%I64d loss_streak=%d",(long)stamp,(long)g_cooldown_until,g_consecutive_losses);
     }
   PrintFormat("CBC001_EXIT time=%I64d deal=%I64u reason=%s price=%.5f profit=%.2f commission=%.2f swap=%.2f net=%.2f mfe_points=%.1f mae_points=%.1f margin_usage_pct=%.4f bars_held=%d loss_streak=%d equity=%.2f",
               (long)stamp,trans.deal,ExitReasonName(reason),price,profit,commission,swap,net,
               g_mfe_points,g_mae_points,g_entry_margin_usage_pct,
               (g_entry_time>0 ? iBarShift(_Symbol,PERIOD_M15,g_entry_time,false) : -1),
               g_consecutive_losses,AccountInfoDouble(ACCOUNT_EQUITY));
   ulong owned_ticket=0;
   if(!OwnedPosition(owned_ticket))
     {
      g_entry_time=0;
      g_entry_price=0.0;
      g_initial_sl=0.0;
      g_initial_risk=0.0;
      g_entry_spread_points=0.0;
      g_entry_margin_usage_pct=0.0;
      g_trail_armed=false;
      g_pending_exit_reason="";
      ResetBox("POSITION_CLOSED");
     }
  }

bool InputsAreFrozen()
  {
   const bool variant_ok=((InpVariantTag==PRIMARY_VARIANT && InpUseCompression) ||
                          (InpVariantTag==CONTROL_VARIANT && !InpUseCompression));
   return(InpResearchAutoMode && InpEnableTelemetry &&
          InpHypothesisId==EXPECTED_HYPOTHESIS && variant_ok &&
          InpCompressionBars==7 && MathAbs(InpCompressionATRMax-1.15)<1e-12 &&
          MathAbs(InpCompressionBodyMax-0.55)<1e-12 && MathAbs(InpBreakBufferATR-0.10)<1e-12 &&
          MathAbs(InpBreakBodyMin-0.50)<1e-12 && InpExpiryBars==9 && InpATRPeriod==14 &&
          MathAbs(InpSLATRBuffer-0.20)<1e-12 && MathAbs(InpMinSLATR-1.30)<1e-12 &&
          MathAbs(InpMaxSLATR-2.60)<1e-12 && MathAbs(InpBETriggerR-1.10)<1e-12 &&
          MathAbs(InpBEOffsetR-0.15)<1e-12 && MathAbs(InpTrailStartR-1.80)<1e-12 &&
          MathAbs(InpTrailATRMult-0.90)<1e-12 && InpTimeStopBars==16 &&
          MathAbs(InpRiskPercent-0.45)<1e-12 && MathAbs(InpMaxNotionalMult-4.50)<1e-12 &&
          MathAbs(InpMaxMarginUsagePct-12.0)<1e-12 && InpMaxSpreadPoints==48 &&
          MathAbs(InpDailyLossPct-1.20)<1e-12 && MathAbs(InpWeeklyLossPct-3.00)<1e-12 &&
          InpLossStreakLimit==4 && InpCooldownHours==8 && InpDailyFlatHour==21 &&
          InpDailyFlatMinute==45 && InpFridayFlatHour==19 && InpFridayFlatMinute==30 &&
          InpDeviationPoints==12 && InpMagic==5604801);
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
   PrintFormat("CBC001_INIT ea=%s hypothesis=%s variant=%s symbol=%s timeframe=M15 compression=%s no_fixed_tp=true",
               EA_NAME,InpHypothesisId,InpVariantTag,_Symbol,(InpUseCompression ? "true" : "false"));
   return(INIT_SUCCEEDED);
  }

void OnDeinit(const int reason)
  {
   if(g_atr_handle!=INVALID_HANDLE)
      IndicatorRelease(g_atr_handle);
   PrintFormat("CBC001_SUMMARY reason=%d runtime_failed=%s closed_bars=%I64d compressions=%I64d compression_rejects=%I64d expired=%I64d breaks=%I64d long=%I64d short=%I64d spread_rejects=%I64d risk_lock_skips=%I64d cooldown_skips=%I64d entries=%I64d entry_rejects=%I64d be_moves=%I64d trail_arms=%I64d trail_moves=%I64d close_attempts=%I64d close_rejects=%I64d closes=%I64d invalid=%I64d max_loss_streak=%d cooldown_until=%I64d",
               reason,(g_runtime_failed ? "true" : "false"),g_closed_bars,g_compressions,
               g_compression_rejects,g_expired_boxes,g_breaks,g_long_signals,g_short_signals,
               g_spread_rejects,g_risk_lock_skips,g_cooldown_skips,g_entries,g_entry_rejects,
               g_be_moves,g_trail_arms,g_trail_moves,g_close_attempts,g_close_rejects,g_closes,
               g_invalid_inputs,g_consecutive_losses,(long)g_cooldown_until);
  }

void OnTick()
  {
   datetime current_bar_open=0;
   if(!CurrentBarOpen(current_bar_open) || current_bar_open<=0)
      return;
   const bool new_bar=(current_bar_open!=g_last_bar_open);
   const datetime server_now=TimeCurrent();
   RefreshRiskLocks(server_now);
   ManagePosition(server_now,current_bar_open,new_bar);
   if(!new_bar)
      return;
   g_last_bar_open=current_bar_open;
   if(AnySymbolExposure())
      return;
   if(g_state==STATE_IN_POSITION)
      ResetBox("NO_POSITION_ON_NEW_BAR");
   BreakSignal signal;
   if(BuildSignal(current_bar_open,signal) && signal.fired)
     {
      const bool entered=SubmitEntry(signal);
      if(!entered)
         ResetBox("BREAK_CANCELLED_OR_REJECTED");
     }
  }
