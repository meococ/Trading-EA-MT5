//+------------------------------------------------------------------+
//| EA_TPR_EUR_M5_V3.mq5                                            |
//| HYP-TPR-EURUSD-M5-001: trend-pullback-resumption                 |
//+------------------------------------------------------------------+
#property strict
#property version   "1.00"
#property description "Untuned closed-bar EURUSD M5 trend-pullback-resumption research EA"

#include <Trade/Trade.mqh>

input group "--- Frozen research authority ---"
input bool   InpResearchAutoMode=false;
input bool   InpEnableTelemetry=true;
input string InpHypothesisId="HYP-TPR-EURUSD-M5-001";
input string InpVariantTag="TPR_PRIMARY";
input bool   InpUsePullbackState=true;

input group "--- Frozen signal ---"
input int    InpFastEMA=8;
input int    InpSlowEMA=21;
input int    InpATRPeriod=14;
input double InpTrendBodyMinATR=0.35;
input int    InpExpansionBars=5;
input double InpExpansionMinATR=1.60;
input double InpPullbackBufferATR=0.15;
input double InpResumptionBodyMin=0.40;
input int    InpMaxBarsToPullback=7;
input int    InpMaxBarsTrendToEntry=9;

input group "--- Frozen exit and risk ---"
input double InpSLATRBuffer=0.25;
input double InpMinSLATR=1.10;
input double InpMaxSLATR=2.40;
input double InpBETriggerR=1.00;
input double InpBEOffsetR=0.10;
input double InpTrailStartR=1.60;
input double InpTrailATRMult=0.75;
input int    InpTimeStopBars=24;
input double InpRiskPercent=0.35;
input double InpMaxNotionalMult=4.50;
input double InpMaxMarginUsagePct=12.0;
input int    InpMaxSpreadPoints=18;
input double InpDailyLossPct=1.10;
input double InpWeeklyLossPct=2.80;
input int    InpDailyFlatHour=21;
input int    InpDailyFlatMinute=50;
input int    InpFridayFlatHour=19;
input int    InpFridayFlatMinute=0;
input int    InpDeviationPoints=6;
input long   InpMagic=5604901;

const string EA_NAME="EA_TPR_EUR_M5_V3";
const string EXPECTED_HYPOTHESIS="HYP-TPR-EURUSD-M5-001";
const string PRIMARY_VARIANT="TPR_PRIMARY";
const string CONTROL_VARIANT="EMA_BODY_CONTROL";

enum StrategyState
  {
   STATE_NEUTRAL=0,
   STATE_TREND_DEFINED=1,
   STATE_PULLBACK=2,
   STATE_IN_POSITION=3
  };

struct EntrySignal
  {
   bool fired;
   datetime decision_time;
   datetime availability_time;
   int direction;
   int trend_age;
   double signal_open;
   double signal_high;
   double signal_low;
   double signal_close;
   double body_ratio;
   double atr;
   double fast_ema;
   double slow_ema;
   double pullback_low;
   double pullback_high;
  };

CTrade g_trade;
int g_atr_handle=INVALID_HANDLE;
int g_fast_handle=INVALID_HANDLE;
int g_slow_handle=INVALID_HANDLE;
StrategyState g_state=STATE_NEUTRAL;
datetime g_last_bar_open=0;
datetime g_last_decision_time=0;
datetime g_trend_time=0;
datetime g_pullback_time=0;
int g_trend_direction=0;
int g_trend_age=0;
double g_pullback_low=0.0;
double g_pullback_high=0.0;
datetime g_entry_time=0;
datetime g_last_close_attempt_bar=0;
double g_entry_price=0.0;
double g_initial_sl=0.0;
double g_initial_risk=0.0;
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
bool g_runtime_failed=false;

long g_closed_bars=0;
long g_trends=0;
long g_pullbacks=0;
long g_resumptions=0;
long g_trend_expiries=0;
long g_entry_expiries=0;
long g_long_signals=0;
long g_short_signals=0;
long g_spread_rejects=0;
long g_risk_lock_skips=0;
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
   if(!SeriesInfoInteger(_Symbol,PERIOD_M5,SERIES_LASTBAR_DATE,raw) || raw<=0)
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
   const int required=InpExpansionBars+2;
   ArraySetAsSeries(rates,true);
   if(CopyRates(_Symbol,PERIOD_M5,1,required,rates)!=required)
      return(false);
   for(int i=0;i<required;i++)
     {
      if(rates[i].time<=0 || rates[i].high<=rates[i].low || rates[i].open<=0.0 ||
         rates[i].close<=0.0 || rates[i].tick_volume<=0)
         return(false);
     }
   return(true);
  }

bool CopyOneClosed(const int handle,double &value)
  {
   value=0.0;
   if(handle==INVALID_HANDLE || BarsCalculated(handle)<InpSlowEMA+2)
      return(false);
   double values[];
   ArraySetAsSeries(values,true);
   if(CopyBuffer(handle,0,1,1,values)!=1)
      return(false);
   value=values[0];
   return(IsFinite(value) && value>0.0);
  }

bool LoadIndicators(double &atr,double &fast,double &slow)
  {
   return(CopyOneClosed(g_atr_handle,atr) && CopyOneClosed(g_fast_handle,fast) &&
          CopyOneClosed(g_slow_handle,slow));
  }

void ResetSetup(const string reason)
  {
   if(InpEnableTelemetry && g_state!=STATE_NEUTRAL)
      PrintFormat("TPR001_STATE from=%d to=0 reason=%s trend_time=%I64d pullback_time=%I64d age=%d direction=%d",
                  (int)g_state,reason,(long)g_trend_time,(long)g_pullback_time,g_trend_age,g_trend_direction);
   g_state=STATE_NEUTRAL;
   g_trend_time=0;
   g_pullback_time=0;
   g_trend_direction=0;
   g_trend_age=0;
   g_pullback_low=0.0;
   g_pullback_high=0.0;
  }

bool DetectTrend(const MqlRates &rates[],const double atr,const double fast,const double slow)
  {
   double highest=-DBL_MAX;
   double lowest=DBL_MAX;
   for(int i=0;i<InpExpansionBars;i++)
     {
      highest=MathMax(highest,rates[i].high);
      lowest=MathMin(lowest,rates[i].low);
     }
   const MqlRates bar=rates[0];
   const double body=bar.close-bar.open;
   int direction=0;
   if(fast>slow && bar.close>fast && body>=InpTrendBodyMinATR*atr &&
      highest-lowest>=InpExpansionMinATR*atr)
      direction=1;
   else if(fast<slow && bar.close<fast && -body>=InpTrendBodyMinATR*atr &&
           highest-lowest>=InpExpansionMinATR*atr)
      direction=-1;
   if(direction==0)
      return(false);
   g_state=STATE_TREND_DEFINED;
   g_trend_time=bar.time;
   g_trend_direction=direction;
   g_trend_age=0;
   g_trends++;
   if(InpEnableTelemetry)
      PrintFormat("TPR001_STATE from=0 to=1 reason=TREND time=%I64d direction=%s o=%.5f h=%.5f l=%.5f c=%.5f ema_fast=%.5f ema_slow=%.5f atr=%.5f body_atr=%.6f expansion=%.5f expansion_atr=%.6f",
                  (long)bar.time,(direction>0 ? "LONG" : "SHORT"),bar.open,bar.high,bar.low,bar.close,
                  fast,slow,atr,MathAbs(body)/atr,highest-lowest,(highest-lowest)/atr);
   return(true);
  }

bool IsPullback(const MqlRates &bar,const double atr,const double fast)
  {
   if(g_trend_direction>0)
      return(bar.low<=fast-InpPullbackBufferATR*atr && bar.close<bar.open);
   if(g_trend_direction<0)
      return(bar.high>=fast+InpPullbackBufferATR*atr && bar.close>bar.open);
   return(false);
  }

bool IsResumption(const MqlRates &bar,const double fast,double &body_ratio)
  {
   const double range=bar.high-bar.low;
   if(range<=0.0)
      return(false);
   body_ratio=MathAbs(bar.close-bar.open)/range;
   if(body_ratio<InpResumptionBodyMin)
      return(false);
   if(g_trend_direction>0)
      return(bar.close>fast && bar.close>bar.open);
   if(g_trend_direction<0)
      return(bar.close<fast && bar.close<bar.open);
   return(false);
  }

bool BuildSignal(const datetime availability_time,EntrySignal &signal)
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
   if((long)(availability_time-bar.time)!=PeriodSeconds(PERIOD_M5))
     {
      g_invalid_inputs++;
      return(false);
     }
   double atr=0.0,fast=0.0,slow=0.0;
   if(!LoadIndicators(atr,fast,slow))
     {
      g_invalid_inputs++;
      return(false);
     }

   if(!InpUsePullbackState)
     {
      const double range=bar.high-bar.low;
      if(range<=0.0 || MathAbs(bar.close-bar.open)/range<InpResumptionBodyMin)
         return(false);
      const int direction=(fast>slow && bar.close>bar.open ? 1 :
                           (fast<slow && bar.close<bar.open ? -1 : 0));
      if(direction==0)
         return(false);
      signal.fired=true;
      signal.decision_time=bar.time;
      signal.availability_time=availability_time;
      signal.direction=direction;
      signal.trend_age=0;
      signal.signal_open=bar.open;
      signal.signal_high=bar.high;
      signal.signal_low=bar.low;
      signal.signal_close=bar.close;
      signal.body_ratio=MathAbs(bar.close-bar.open)/range;
      signal.atr=atr;
      signal.fast_ema=fast;
      signal.slow_ema=slow;
      signal.pullback_low=bar.low;
      signal.pullback_high=bar.high;
      g_state=STATE_PULLBACK;
      g_trend_direction=direction;
      g_resumptions++;
      if(direction>0) g_long_signals++; else g_short_signals++;
      return(true);
     }

   if(g_state==STATE_NEUTRAL)
     {
      DetectTrend(rates,atr,fast,slow);
      return(false);
     }
   if(bar.time>g_trend_time)
      g_trend_age++;

   if(g_state==STATE_TREND_DEFINED)
     {
      if(g_trend_age>InpMaxBarsToPullback)
        {
         g_trend_expiries++;
         ResetSetup("PULLBACK_EXPIRY");
         DetectTrend(rates,atr,fast,slow);
         return(false);
        }
      if(IsPullback(bar,atr,fast))
        {
         g_state=STATE_PULLBACK;
         g_pullback_time=bar.time;
         g_pullback_low=bar.low;
         g_pullback_high=bar.high;
         g_pullbacks++;
         if(InpEnableTelemetry)
            PrintFormat("TPR001_STATE from=1 to=2 reason=PULLBACK time=%I64d direction=%s age=%d o=%.5f h=%.5f l=%.5f c=%.5f ema_fast=%.5f ema_slow=%.5f atr=%.5f",
                        (long)bar.time,(g_trend_direction>0 ? "LONG" : "SHORT"),g_trend_age,
                        bar.open,bar.high,bar.low,bar.close,fast,slow,atr);
        }
      return(false);
     }

   if(g_state==STATE_PULLBACK)
     {
      if(g_trend_age>InpMaxBarsTrendToEntry)
        {
         g_entry_expiries++;
         ResetSetup("ENTRY_EXPIRY");
         DetectTrend(rates,atr,fast,slow);
         return(false);
        }
      double body_ratio=0.0;
      if(!IsResumption(bar,fast,body_ratio))
         return(false);
      signal.fired=true;
      signal.decision_time=bar.time;
      signal.availability_time=availability_time;
      signal.direction=g_trend_direction;
      signal.trend_age=g_trend_age;
      signal.signal_open=bar.open;
      signal.signal_high=bar.high;
      signal.signal_low=bar.low;
      signal.signal_close=bar.close;
      signal.body_ratio=body_ratio;
      signal.atr=atr;
      signal.fast_ema=fast;
      signal.slow_ema=slow;
      signal.pullback_low=g_pullback_low;
      signal.pullback_high=g_pullback_high;
      g_resumptions++;
      if(signal.direction>0) g_long_signals++; else g_short_signals++;
      if(InpEnableTelemetry)
         PrintFormat("TPR001_SIGNAL decision=%I64d availability=%I64d variant=%s direction=%s age=%d pullback_time=%I64d o=%.5f h=%.5f l=%.5f c=%.5f body_ratio=%.6f ema_fast=%.5f ema_slow=%.5f atr=%.5f pullback_low=%.5f pullback_high=%.5f",
                     (long)bar.time,(long)availability_time,InpVariantTag,
                     (signal.direction>0 ? "LONG" : "SHORT"),g_trend_age,(long)g_pullback_time,
                     bar.open,bar.high,bar.low,bar.close,body_ratio,fast,slow,atr,g_pullback_low,g_pullback_high);
      return(true);
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
   if(vmin<=0.0 || vmax<vmin || step<=0.0 || volume<vmin)
      return(0.0);
   const double units=MathFloor((MathMin(volume,vmax)-vmin+1e-12)/step);
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
      if(current==0 || !PositionSelectByTicket(current)) continue;
      if(PositionGetString(POSITION_SYMBOL)==_Symbol && PositionGetInteger(POSITION_MAGIC)==InpMagic)
        {
         ticket=current;
         owned++;
        }
     }
   if(owned>1) g_runtime_failed=true;
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
   if(g_day_start_equity>0.0 && equity<=g_day_start_equity*(1.0-InpDailyLossPct/100.0)) g_day_locked=true;
   if(g_week_start_equity>0.0 && equity<=g_week_start_equity*(1.0-InpWeeklyLossPct/100.0)) g_week_locked=true;
  }

bool CloseOwned(const string reason)
  {
   ulong ticket=0;
   if(!OwnedPosition(ticket)) return(true);
   g_close_attempts++;
   g_pending_exit_reason=reason;
   if(!g_trade.PositionClose(ticket,InpDeviationPoints))
     {
      g_close_rejects++;
      PrintFormat("TPR001_CLOSE_REJECT reason=%s ticket=%I64u retcode=%u",reason,ticket,g_trade.ResultRetcode());
      return(false);
     }
   const uint retcode=g_trade.ResultRetcode();
   if(retcode!=TRADE_RETCODE_DONE && retcode!=TRADE_RETCODE_DONE_PARTIAL)
     {
      g_close_rejects++;
      return(false);
     }
   g_closes++;
   PrintFormat("TPR001_CLOSE_REQUEST reason=%s ticket=%I64u retcode=%u",reason,ticket,retcode);
   return(true);
  }

bool ModifyOwnedStop(const ulong ticket,const double proposed_sl,const string reason)
  {
   if(!PositionSelectByTicket(ticket)) return(false);
   const bool is_long=((ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_BUY);
   const double current_sl=PositionGetDouble(POSITION_SL);
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick)) return(false);
   const double point=SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   const double tick_size=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);
   if(point<=0.0 || tick_size<=0.0) return(false);
   const double new_sl=(is_long ? FloorToTick(proposed_sl,tick_size) : CeilToTick(proposed_sl,tick_size));
   if((is_long && current_sl>=new_sl-point*0.1) || (!is_long && current_sl>0.0 && current_sl<=new_sl+point*0.1))
      return(false);
   const double min_distance=(double)MathMax(MathMax(SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL),
                                                     SymbolInfoInteger(_Symbol,SYMBOL_TRADE_FREEZE_LEVEL)),0)*point;
   if((is_long && tick.bid-new_sl<min_distance) || (!is_long && new_sl-tick.ask<min_distance)) return(false);
   if(!g_trade.PositionModify(ticket,new_sl,0.0)) return(false);
   const uint retcode=g_trade.ResultRetcode();
   if(retcode!=TRADE_RETCODE_DONE && retcode!=TRADE_RETCODE_NO_CHANGES) return(false);
   PrintFormat("TPR001_STOP_MOVE reason=%s ticket=%I64u sl=%.5f mfe_points=%.1f mae_points=%.1f",
               reason,ticket,new_sl,g_mfe_points,g_mae_points);
   return(true);
  }

void UpdateExcursionAndStops(const ulong ticket,const bool new_bar)
  {
   if(!PositionSelectByTicket(ticket) || g_initial_risk<=0.0 || g_entry_price<=0.0) return;
   const bool is_long=((ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_BUY);
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick)) return;
   const double point=SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   if(point<=0.0) return;
   const double quote=(is_long ? tick.bid : tick.ask);
   const double favorable=(is_long ? quote-g_entry_price : g_entry_price-quote);
   g_mfe_points=MathMax(g_mfe_points,MathMax(0.0,favorable)/point);
   g_mae_points=MathMax(g_mae_points,MathMax(0.0,-favorable)/point);
   if(favorable>=InpBETriggerR*g_initial_risk)
     {
      const double be=(is_long ? g_entry_price+InpBEOffsetR*g_initial_risk
                               : g_entry_price-InpBEOffsetR*g_initial_risk);
      if(ModifyOwnedStop(ticket,be,"BREAKEVEN_PLUS")) g_be_moves++;
     }
   if(!g_trail_armed && favorable>=InpTrailStartR*g_initial_risk)
     {
      g_trail_armed=true;
      g_trail_arms++;
      PrintFormat("TPR001_TRAIL_ARM ticket=%I64u trigger_r=%.3f mfe_points=%.1f",ticket,InpTrailStartR,g_mfe_points);
     }
   if(!new_bar || !g_trail_armed) return;
   MqlRates closed[];
   ArraySetAsSeries(closed,true);
   if(CopyRates(_Symbol,PERIOD_M5,1,1,closed)!=1) return;
   double atr=0.0,fast=0.0,slow=0.0;
   if(!LoadIndicators(atr,fast,slow)) return;
   const double trail=(is_long ? closed[0].close-InpTrailATRMult*atr : closed[0].close+InpTrailATRMult*atr);
   if(ModifyOwnedStop(ticket,trail,"ATR_TRAIL")) g_trail_moves++;
  }

void ManagePosition(const datetime server_now,const datetime current_bar_open,const bool new_bar)
  {
   ulong ticket=0;
   if(!OwnedPosition(ticket)) return;
   g_state=STATE_IN_POSITION;
   UpdateExcursionAndStops(ticket,new_bar);
   MqlDateTime p;
   TimeToStruct(server_now,p);
   const int minute=p.hour*60+p.min;
   string reason="";
   if(p.day_of_week==5 && minute>=InpFridayFlatHour*60+InpFridayFlatMinute) reason="FRIDAY_FLAT";
   else if(minute>=InpDailyFlatHour*60+InpDailyFlatMinute) reason="DAILY_FLAT";
   else
     {
      datetime started=g_entry_time;
      if(started<=0 && PositionSelectByTicket(ticket)) started=(datetime)PositionGetInteger(POSITION_TIME);
      if(started>0 && iBarShift(_Symbol,PERIOD_M5,started,false)>=InpTimeStopBars) reason="TIME_STOP";
     }
   if(reason=="" || g_last_close_attempt_bar==current_bar_open) return;
   g_last_close_attempt_bar=current_bar_open;
   CloseOwned(reason);
  }

bool EntryWindowOpen(const datetime stamp)
  {
   MqlDateTime p;
   TimeToStruct(stamp,p);
   if(p.day_of_week==0 || p.day_of_week==6) return(false);
   const int minute=p.hour*60+p.min;
   if(p.day_of_week==5 && minute>=InpFridayFlatHour*60+InpFridayFlatMinute) return(false);
   return(minute<InpDailyFlatHour*60+InpDailyFlatMinute);
  }

bool SubmitEntry(const EntrySignal &signal)
  {
   if(!signal.fired || AnySymbolExposure() || !EntryWindowOpen(signal.availability_time)) return(false);
   if(g_day_locked || g_week_locked)
     {
      g_risk_lock_skips++;
      return(false);
     }
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick) || tick.ask<=tick.bid || tick.bid<=0.0) return(false);
   const double point=SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   const double tick_size=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);
   const double contract_size=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_CONTRACT_SIZE);
   if(point<=0.0 || tick_size<=0.0 || contract_size<=0.0) return(false);
   const double spread_points=(tick.ask-tick.bid)/point;
   if(!IsFinite(spread_points) || spread_points>InpMaxSpreadPoints)
     {
      g_spread_rejects++;
      return(false);
     }
   const double entry=(signal.direction>0 ? tick.ask : tick.bid);
   const double structural=(signal.direction>0
                            ? MathMin(signal.pullback_low,signal.slow_ema)-InpSLATRBuffer*signal.atr
                            : MathMax(signal.pullback_high,signal.slow_ema)+InpSLATRBuffer*signal.atr);
   double risk_distance=(signal.direction>0 ? entry-structural : structural-entry);
   risk_distance=MathMax(InpMinSLATR*signal.atr,MathMin(risk_distance,InpMaxSLATR*signal.atr));
   if(!IsFinite(risk_distance) || risk_distance<=0.0) return(false);
   const double raw_sl=entry-signal.direction*risk_distance;
   const double sl=(signal.direction>0 ? FloorToTick(raw_sl,tick_size) : CeilToTick(raw_sl,tick_size));
   const double minimum_distance=(double)MathMax(MathMax(SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL),
                                                         SymbolInfoInteger(_Symbol,SYMBOL_TRADE_FREEZE_LEVEL)),0)*point;
   if(MathAbs(entry-sl)<minimum_distance) return(false);
   const ENUM_ORDER_TYPE order_type=(signal.direction>0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL);
   double one_lot_loss=0.0,margin_per_lot=0.0;
   if(!OrderCalcProfit(order_type,_Symbol,1.0,entry,sl,one_lot_loss) || one_lot_loss>=0.0) return(false);
   if(!OrderCalcMargin(order_type,_Symbol,1.0,entry,margin_per_lot) || margin_per_lot<=0.0) return(false);
   const double equity=AccountInfoDouble(ACCOUNT_EQUITY);
   const double free_margin=AccountInfoDouble(ACCOUNT_MARGIN_FREE);
   if(equity<=0.0 || free_margin<=0.0) return(false);
   const double volume_risk=equity*(InpRiskPercent/100.0)/MathAbs(one_lot_loss);
   const double volume_notional=(equity*InpMaxNotionalMult)/(entry*contract_size);
   const double volume_margin=(free_margin*(InpMaxMarginUsagePct/100.0))/margin_per_lot;
   const double volume=NormalizeVolumeDown(MathMin(volume_risk,MathMin(volume_notional,volume_margin)));
   if(volume<=0.0) return(false);
   double margin=0.0;
   if(!OrderCalcMargin(order_type,_Symbol,volume,entry,margin) ||
      margin>free_margin*(InpMaxMarginUsagePct/100.0)+0.01) return(false);
   const double notional=volume*entry*contract_size;
   if(notional>equity*InpMaxNotionalMult+0.01) return(false);
   g_trade.SetExpertMagicNumber(InpMagic);
   g_trade.SetDeviationInPoints(InpDeviationPoints);
   g_trade.SetTypeFillingBySymbol(_Symbol);
   const bool sent=g_trade.PositionOpen(_Symbol,order_type,volume,entry,sl,0.0,InpVariantTag);
   const uint retcode=g_trade.ResultRetcode();
   if(!sent || (retcode!=TRADE_RETCODE_DONE && retcode!=TRADE_RETCODE_DONE_PARTIAL))
     {
      g_entry_rejects++;
      PrintFormat("TPR001_ENTRY_REJECT direction=%s volume=%.2f entry=%.5f sl=%.5f spread_points=%.1f retcode=%u",
                  (signal.direction>0 ? "LONG" : "SHORT"),volume,entry,sl,spread_points,retcode);
      return(false);
     }
   g_entries++;
   g_state=STATE_IN_POSITION;
   g_entry_time=signal.availability_time;
   g_entry_price=(g_trade.ResultPrice()>0.0 ? g_trade.ResultPrice() : entry);
   g_initial_sl=sl;
   g_initial_risk=MathAbs(g_entry_price-sl);
   g_entry_margin_usage_pct=100.0*margin/free_margin;
   g_mfe_points=0.0;
   g_mae_points=0.0;
   g_trail_armed=false;
   g_pending_exit_reason="";
   PrintFormat("TPR001_ENTRY decision=%I64d direction=%s age=%d volume=%.2f entry=%.5f sl=%.5f tp=0 initial_risk=%.5f risk_pct=%.3f spread_points=%.1f volume_risk=%.4f volume_notional=%.4f volume_margin=%.4f notional_equity_mult=%.4f margin_usage_pct=%.4f equity=%.2f retcode=%u",
               (long)signal.decision_time,(signal.direction>0 ? "LONG" : "SHORT"),signal.trend_age,
               volume,g_entry_price,sl,g_initial_risk,InpRiskPercent,spread_points,volume_risk,
               volume_notional,volume_margin,notional/equity,g_entry_margin_usage_pct,equity,retcode);
   return(true);
  }

string ExitReasonName(const long reason)
  {
   if(reason==DEAL_REASON_SL) return("SL");
   if(reason==DEAL_REASON_TP) return("TP_UNEXPECTED");
   if(reason==DEAL_REASON_EXPERT && g_pending_exit_reason!="") return(g_pending_exit_reason);
   return(StringFormat("DEAL_REASON_%d",(int)reason));
  }

void OnTradeTransaction(const MqlTradeTransaction &trans,const MqlTradeRequest &request,const MqlTradeResult &result)
  {
   if(trans.type!=TRADE_TRANSACTION_DEAL_ADD || trans.deal==0 || !HistoryDealSelect(trans.deal)) return;
   if(HistoryDealGetString(trans.deal,DEAL_SYMBOL)!=_Symbol || HistoryDealGetInteger(trans.deal,DEAL_MAGIC)!=InpMagic) return;
   const long kind=HistoryDealGetInteger(trans.deal,DEAL_ENTRY);
   if(kind!=DEAL_ENTRY_OUT && kind!=DEAL_ENTRY_OUT_BY) return;
   const long reason=HistoryDealGetInteger(trans.deal,DEAL_REASON);
   const double price=HistoryDealGetDouble(trans.deal,DEAL_PRICE);
   const double profit=HistoryDealGetDouble(trans.deal,DEAL_PROFIT);
   const double commission=HistoryDealGetDouble(trans.deal,DEAL_COMMISSION);
   const double swap=HistoryDealGetDouble(trans.deal,DEAL_SWAP);
   const datetime stamp=(datetime)HistoryDealGetInteger(trans.deal,DEAL_TIME);
   PrintFormat("TPR001_EXIT time=%I64d deal=%I64u reason=%s price=%.5f profit=%.2f commission=%.2f swap=%.2f net=%.2f mfe_points=%.1f mae_points=%.1f margin_usage_pct=%.4f bars_held=%d equity=%.2f",
               (long)stamp,trans.deal,ExitReasonName(reason),price,profit,commission,swap,profit+commission+swap,
               g_mfe_points,g_mae_points,g_entry_margin_usage_pct,
               (g_entry_time>0 ? iBarShift(_Symbol,PERIOD_M5,g_entry_time,false) : -1),AccountInfoDouble(ACCOUNT_EQUITY));
   ulong ticket=0;
   if(!OwnedPosition(ticket))
     {
      g_entry_time=0;
      g_entry_price=0.0;
      g_initial_sl=0.0;
      g_initial_risk=0.0;
      g_entry_margin_usage_pct=0.0;
      g_trail_armed=false;
      g_pending_exit_reason="";
      ResetSetup("POSITION_CLOSED");
     }
  }

bool InputsAreFrozen()
  {
   const bool variant_ok=((InpVariantTag==PRIMARY_VARIANT && InpUsePullbackState) ||
                          (InpVariantTag==CONTROL_VARIANT && !InpUsePullbackState));
   return(InpResearchAutoMode && InpEnableTelemetry && InpHypothesisId==EXPECTED_HYPOTHESIS && variant_ok &&
          InpFastEMA==8 && InpSlowEMA==21 && InpATRPeriod==14 &&
          MathAbs(InpTrendBodyMinATR-0.35)<1e-12 && InpExpansionBars==5 &&
          MathAbs(InpExpansionMinATR-1.60)<1e-12 && MathAbs(InpPullbackBufferATR-0.15)<1e-12 &&
          MathAbs(InpResumptionBodyMin-0.40)<1e-12 && InpMaxBarsToPullback==7 &&
          InpMaxBarsTrendToEntry==9 && MathAbs(InpSLATRBuffer-0.25)<1e-12 &&
          MathAbs(InpMinSLATR-1.10)<1e-12 && MathAbs(InpMaxSLATR-2.40)<1e-12 &&
          MathAbs(InpBETriggerR-1.00)<1e-12 && MathAbs(InpBEOffsetR-0.10)<1e-12 &&
          MathAbs(InpTrailStartR-1.60)<1e-12 && MathAbs(InpTrailATRMult-0.75)<1e-12 &&
          InpTimeStopBars==24 && MathAbs(InpRiskPercent-0.35)<1e-12 &&
          MathAbs(InpMaxNotionalMult-4.50)<1e-12 && MathAbs(InpMaxMarginUsagePct-12.0)<1e-12 &&
          InpMaxSpreadPoints==18 && MathAbs(InpDailyLossPct-1.10)<1e-12 &&
          MathAbs(InpWeeklyLossPct-2.80)<1e-12 && InpDailyFlatHour==21 &&
          InpDailyFlatMinute==50 && InpFridayFlatHour==19 && InpFridayFlatMinute==0 &&
          InpDeviationPoints==6 && InpMagic==5604901);
  }

int OnInit()
  {
   if(_Period!=PERIOD_M5 || !InputsAreFrozen()) return(INIT_PARAMETERS_INCORRECT);
   g_atr_handle=iATR(_Symbol,PERIOD_M5,InpATRPeriod);
   g_fast_handle=iMA(_Symbol,PERIOD_M5,InpFastEMA,0,MODE_EMA,PRICE_CLOSE);
   g_slow_handle=iMA(_Symbol,PERIOD_M5,InpSlowEMA,0,MODE_EMA,PRICE_CLOSE);
   if(g_atr_handle==INVALID_HANDLE || g_fast_handle==INVALID_HANDLE || g_slow_handle==INVALID_HANDLE) return(INIT_FAILED);
   if(!EmitSeriesProof()) return(INIT_FAILED);
   g_trade.SetExpertMagicNumber(InpMagic);
   g_trade.SetDeviationInPoints(InpDeviationPoints);
   g_trade.SetTypeFillingBySymbol(_Symbol);
   const datetime now=TimeCurrent();
   const double equity=AccountInfoDouble(ACCOUNT_EQUITY);
   g_day_key=DayKey(now);
   g_week_key=WeekKey(now);
   g_day_start_equity=equity;
   g_week_start_equity=equity;
   if(!CurrentBarOpen(g_last_bar_open) || g_last_bar_open<=0) return(INIT_FAILED);
   PrintFormat("TPR001_INIT ea=%s hypothesis=%s variant=%s symbol=%s timeframe=M5 pullback_state=%s no_fixed_tp=true",
               EA_NAME,InpHypothesisId,InpVariantTag,_Symbol,(InpUsePullbackState ? "true" : "false"));
   return(INIT_SUCCEEDED);
  }

void OnDeinit(const int reason)
  {
   if(g_atr_handle!=INVALID_HANDLE) IndicatorRelease(g_atr_handle);
   if(g_fast_handle!=INVALID_HANDLE) IndicatorRelease(g_fast_handle);
   if(g_slow_handle!=INVALID_HANDLE) IndicatorRelease(g_slow_handle);
   PrintFormat("TPR001_SUMMARY reason=%d runtime_failed=%s closed_bars=%I64d trends=%I64d pullbacks=%I64d resumptions=%I64d trend_expiries=%I64d entry_expiries=%I64d long=%I64d short=%I64d spread_rejects=%I64d risk_lock_skips=%I64d entries=%I64d entry_rejects=%I64d be_moves=%I64d trail_arms=%I64d trail_moves=%I64d close_attempts=%I64d close_rejects=%I64d closes=%I64d invalid=%I64d",
               reason,(g_runtime_failed ? "true" : "false"),g_closed_bars,g_trends,g_pullbacks,
               g_resumptions,g_trend_expiries,g_entry_expiries,g_long_signals,g_short_signals,
               g_spread_rejects,g_risk_lock_skips,g_entries,g_entry_rejects,g_be_moves,g_trail_arms,
               g_trail_moves,g_close_attempts,g_close_rejects,g_closes,g_invalid_inputs);
  }

void OnTick()
  {
   datetime current_bar_open=0;
   if(!CurrentBarOpen(current_bar_open) || current_bar_open<=0) return;
   const bool new_bar=(current_bar_open!=g_last_bar_open);
   const datetime now=TimeCurrent();
   RefreshRiskLocks(now);
   ManagePosition(now,current_bar_open,new_bar);
   if(!new_bar) return;
   g_last_bar_open=current_bar_open;
   if(AnySymbolExposure()) return;
   if(g_state==STATE_IN_POSITION) ResetSetup("NO_POSITION_ON_NEW_BAR");
   EntrySignal signal;
   if(BuildSignal(current_bar_open,signal) && signal.fired)
     {
      if(!SubmitEntry(signal)) ResetSetup("SIGNAL_CANCELLED_OR_REJECTED");
     }
  }
