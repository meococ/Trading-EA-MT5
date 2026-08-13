//+------------------------------------------------------------------+
//| EA_VWAP_Disloc_EUR_M5_V4.mq5                                   |
//| HYP-VDR-EURUSD-M5-001: rolling-VWAP dislocation reversion       |
//+------------------------------------------------------------------+
#property strict
#property version "1.00"
#property description "Untuned closed-bar EURUSD M5 rolling-VWAP dislocation-reversion EA"

#include <Trade/Trade.mqh>

input group "--- Frozen research authority ---"
input bool InpResearchAutoMode=false;
input bool InpEnableTelemetry=true;
input string InpHypothesisId="HYP-VDR-EURUSD-M5-001";
input string InpVariantTag="VWAP_STATE_PRIMARY";
input bool InpUseVolumeReversionState=true;

input group "--- Frozen signal ---"
input int InpVWAPWindow=18;
input int InpVolumeSMAPeriod=18;
input int InpATRPeriod=14;
input double InpDislocATRMult=1.35;
input double InpVolumeExpandMult=1.45;
input int InpMaxBarsDislocToRev=6;
input double InpReversionBodyMin=0.35;

input group "--- Frozen exit and risk ---"
input double InpSLATRBuffer=0.30;
input double InpMinSLATR=1.00;
input double InpMaxSLATR=2.30;
input double InpBETriggerR=0.90;
input double InpBEOffsetR=0.12;
input double InpTrailStartR=1.50;
input double InpTrailATRMult=0.70;
input int InpTimeStopBars=24;
input double InpRiskPercent=0.25;
input double InpMaxNotionalMult=4.50;
input double InpMaxMarginUsagePct=12.0;
input int InpMaxSpreadPoints=15;
input double InpDailyLossPct=1.00;
input double InpWeeklyLossPct=2.50;
input int InpDailyFlatHour=21;
input int InpDailyFlatMinute=50;
input int InpFridayFlatHour=18;
input int InpFridayFlatMinute=50;
input int InpDeviationPoints=5;
input long InpMagic=5605001;

const string EA_NAME="EA_VWAP_Disloc_EUR_M5_V4";
const string EXPECTED_HYPOTHESIS="HYP-VDR-EURUSD-M5-001";
const string PRIMARY_VARIANT="VWAP_STATE_PRIMARY";
const string CONTROL_VARIANT="VWAP_DISTANCE_CONTROL";

enum StrategyState { STATE_NEUTRAL=0, STATE_DISLOCATION=1, STATE_IN_POSITION=2 };

struct EntrySignal
  {
   bool fired;
   datetime decision_time;
   datetime availability_time;
   int direction;
   int setup_age;
   double signal_open;
   double signal_high;
   double signal_low;
   double signal_close;
   double body_ratio;
   double atr;
   double vwap;
   double distance_atr;
   double volume_ratio;
   double disloc_extreme;
  };

CTrade g_trade;
int g_atr_handle=INVALID_HANDLE;
StrategyState g_state=STATE_NEUTRAL;
datetime g_last_bar_open=0;
datetime g_last_decision_time=0;
datetime g_disloc_time=0;
int g_disloc_direction=0;
int g_setup_age=0;
double g_disloc_extreme=0.0;
double g_disloc_vwap=0.0;
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
long g_dislocations=0;
long g_reversions=0;
long g_expiries=0;
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
long g_missing_volume=0;

bool IsFinite(const double value) { return(value!=EMPTY_VALUE && MathIsValidNumber(value)); }

int DayKey(const datetime stamp)
  {
   MqlDateTime p; TimeToStruct(stamp,p);
   return(p.year*10000+p.mon*100+p.day);
  }

long WeekKey(const datetime stamp)
  {
   MqlDateTime p; TimeToStruct(stamp,p);
   const datetime start=stamp-p.hour*3600-p.min*60-p.sec;
   return((long)(start-((p.day_of_week+6)%7)*86400)/604800);
  }

bool CurrentBarOpen(datetime &bar_open)
  {
   long raw=0; bar_open=0;
   if(!SeriesInfoInteger(_Symbol,PERIOD_M5,SERIES_LASTBAR_DATE,raw) || raw<=0) return(false);
   bar_open=(datetime)raw;
   return(true);
  }

bool EmitSeriesProof()
  {
   long m5_sync=0,m5_first=0,m5_terminal_first=0,m1_server_first=0,m1_terminal_first=0,m5_bars=0;
   if(!SeriesInfoInteger(_Symbol,PERIOD_M5,SERIES_SYNCHRONIZED,m5_sync) ||
      !SeriesInfoInteger(_Symbol,PERIOD_M5,SERIES_FIRSTDATE,m5_first) ||
      !SeriesInfoInteger(_Symbol,PERIOD_M5,SERIES_TERMINAL_FIRSTDATE,m5_terminal_first) ||
      !SeriesInfoInteger(_Symbol,PERIOD_M1,SERIES_SERVER_FIRSTDATE,m1_server_first) ||
      !SeriesInfoInteger(_Symbol,PERIOD_M1,SERIES_TERMINAL_FIRSTDATE,m1_terminal_first) ||
      !SeriesInfoInteger(_Symbol,PERIOD_M5,SERIES_BARS_COUNT,m5_bars)) return(false);
   ResetLastError();
   const long maxbars=TerminalInfoInteger(TERMINAL_MAXBARS);
   const int terminal_error=GetLastError();
   datetime copied[]; ArraySetAsSeries(copied,false);
   ResetLastError();
   const int copied_n=CopyTime(_Symbol,PERIOD_M5,(datetime)m5_first,1,copied);
   const int copied_error=GetLastError();
   const long copied_first=(copied_n==1 ? (long)copied[0] : 0);
   PrintFormat("DATA_EPOCH_D0_SERIES_PROOF symbol=%s m5_synchronized=%I64d m5_first_epoch=%I64d m5_terminal_first_epoch=%I64d m1_server_first_epoch=%I64d m1_terminal_first_epoch=%I64d m5_bars=%I64d terminal_maxbars=%I64d copytime_from_epoch=%I64d copytime_count=1 copytime_result=%d copytime_first_epoch=%I64d copytime_last_error=%d",
               _Symbol,m5_sync,m5_first,m5_terminal_first,m1_server_first,m1_terminal_first,m5_bars,maxbars,
               m5_first,copied_n,copied_first,copied_error);
   return(m5_sync==1 && m5_first>0 && m5_terminal_first>0 && m1_server_first>0 &&
          m1_terminal_first>0 && m5_bars>0 && maxbars>0 && terminal_error==0 &&
          copied_n==1 && copied_first==m5_first && copied_error==0);
  }

bool LoadClosedRates(MqlRates &rates[])
  {
   const int required=MathMax(InpVWAPWindow,InpVolumeSMAPeriod)+2;
   ArraySetAsSeries(rates,true);
   if(CopyRates(_Symbol,PERIOD_M5,1,required,rates)!=required) return(false);
   for(int i=0;i<required;i++)
     {
      if(rates[i].time<=0 || rates[i].high<=rates[i].low || rates[i].open<=0.0 || rates[i].close<=0.0) return(false);
      if(rates[i].tick_volume<=0) { g_missing_volume++; return(false); }
     }
   return(true);
  }

bool LoadAtr(double &atr)
  {
   atr=0.0;
   if(g_atr_handle==INVALID_HANDLE || BarsCalculated(g_atr_handle)<InpATRPeriod+2) return(false);
   double values[]; ArraySetAsSeries(values,true);
   if(CopyBuffer(g_atr_handle,0,1,1,values)!=1) return(false);
   atr=values[0];
   return(IsFinite(atr) && atr>0.0);
  }

bool ComputeRollingStats(const MqlRates &rates[],double &vwap,double &volume_sma)
  {
   double sum_pv=0.0,sum_v=0.0,sum_volume=0.0;
   for(int i=0;i<InpVWAPWindow;i++)
     {
      if(rates[i].tick_volume<=0) { g_missing_volume++; return(false); }
      const double volume=(double)rates[i].tick_volume;
      const double typical=(rates[i].high+rates[i].low+rates[i].close)/3.0;
      sum_pv+=typical*volume;
      sum_v+=volume;
     }
   for(int i=0;i<InpVolumeSMAPeriod;i++)
     {
      if(rates[i].tick_volume<=0) { g_missing_volume++; return(false); }
      sum_volume+=(double)rates[i].tick_volume;
     }
   if(sum_v<=0.0 || sum_volume<=0.0) return(false);
   vwap=sum_pv/sum_v;
   volume_sma=sum_volume/InpVolumeSMAPeriod;
   return(IsFinite(vwap) && vwap>0.0 && IsFinite(volume_sma) && volume_sma>0.0);
  }

void ResetSetup(const string reason)
  {
   if(InpEnableTelemetry && g_state!=STATE_NEUTRAL)
      PrintFormat("VDR001_STATE from=%d to=0 reason=%s disloc_time=%I64d direction=%d age=%d extreme=%.5f vwap=%.5f",
                  (int)g_state,reason,(long)g_disloc_time,g_disloc_direction,g_setup_age,g_disloc_extreme,g_disloc_vwap);
   g_state=STATE_NEUTRAL; g_disloc_time=0; g_disloc_direction=0; g_setup_age=0;
   g_disloc_extreme=0.0; g_disloc_vwap=0.0;
  }

bool DetectDislocation(const MqlRates &bar,const double atr,const double vwap,const double volume_sma)
  {
   const double distance=MathAbs(bar.close-vwap);
   const double volume_ratio=(double)bar.tick_volume/volume_sma;
   if(distance<InpDislocATRMult*atr || volume_ratio<InpVolumeExpandMult || bar.close==vwap) return(false);
   g_state=STATE_DISLOCATION;
   g_disloc_time=bar.time;
   g_disloc_direction=(bar.close>vwap ? 1 : -1);
   g_setup_age=0;
   g_disloc_extreme=bar.close;
   g_disloc_vwap=vwap;
   g_dislocations++;
   if(InpEnableTelemetry)
      PrintFormat("VDR001_STATE from=0 to=1 reason=DISLOCATION time=%I64d direction=%s close=%.5f vwap=%.5f distance=%.5f distance_atr=%.6f tick_volume=%I64d volume_sma=%.2f volume_ratio=%.6f atr=%.5f",
                  (long)bar.time,(g_disloc_direction>0 ? "ABOVE" : "BELOW"),bar.close,vwap,distance,
                  distance/atr,bar.tick_volume,volume_sma,volume_ratio,atr);
   return(true);
  }

bool BuildSignal(const datetime availability_time,EntrySignal &signal)
  {
   ZeroMemory(signal);
   MqlRates rates[];
   if(!LoadClosedRates(rates)) { g_invalid_inputs++; return(false); }
   const MqlRates bar=rates[0];
   if(bar.time<=0 || bar.time==g_last_decision_time) return(false);
   g_last_decision_time=bar.time; g_closed_bars++;
   if((long)(availability_time-bar.time)!=PeriodSeconds(PERIOD_M5)) { g_invalid_inputs++; return(false); }
   double atr=0.0,vwap=0.0,volume_sma=0.0;
   if(!LoadAtr(atr) || !ComputeRollingStats(rates,vwap,volume_sma)) { g_invalid_inputs++; return(false); }
   const double distance=MathAbs(bar.close-vwap);
   const double volume_ratio=(double)bar.tick_volume/volume_sma;

   if(!InpUseVolumeReversionState)
     {
      if(distance<InpDislocATRMult*atr || bar.close==vwap) return(false);
      signal.fired=true; signal.decision_time=bar.time; signal.availability_time=availability_time;
      signal.direction=(bar.close>vwap ? -1 : 1); signal.setup_age=0;
      signal.signal_open=bar.open; signal.signal_high=bar.high; signal.signal_low=bar.low; signal.signal_close=bar.close;
      signal.body_ratio=MathAbs(bar.close-bar.open)/(bar.high-bar.low); signal.atr=atr; signal.vwap=vwap;
      signal.distance_atr=distance/atr; signal.volume_ratio=volume_ratio; signal.disloc_extreme=bar.close;
      g_disloc_direction=-signal.direction; g_disloc_extreme=bar.close; g_state=STATE_DISLOCATION; g_reversions++;
      if(signal.direction>0) g_long_signals++; else g_short_signals++;
      return(true);
     }

   if(g_state==STATE_NEUTRAL)
     {
      DetectDislocation(bar,atr,vwap,volume_sma);
      return(false);
     }
   if(g_state==STATE_DISLOCATION && bar.time>g_disloc_time) g_setup_age++;
   if(g_state!=STATE_DISLOCATION) return(false);
   if(g_setup_age>InpMaxBarsDislocToRev)
     {
      g_expiries++; ResetSetup("REVERSAL_EXPIRY"); DetectDislocation(bar,atr,vwap,volume_sma); return(false);
     }
   const double range=bar.high-bar.low;
   if(range<=0.0) return(false);
   const double body_ratio=MathAbs(bar.close-bar.open)/range;
   const bool revert_from_above=(g_disloc_direction>0 && bar.close<bar.open && bar.close<g_disloc_extreme);
   const bool revert_from_below=(g_disloc_direction<0 && bar.close>bar.open && bar.close>g_disloc_extreme);
   if(body_ratio<InpReversionBodyMin || revert_from_above==revert_from_below) return(false);
   signal.fired=true; signal.decision_time=bar.time; signal.availability_time=availability_time;
   signal.direction=(revert_from_above ? -1 : 1); signal.setup_age=g_setup_age;
   signal.signal_open=bar.open; signal.signal_high=bar.high; signal.signal_low=bar.low; signal.signal_close=bar.close;
   signal.body_ratio=body_ratio; signal.atr=atr; signal.vwap=vwap; signal.distance_atr=distance/atr;
   signal.volume_ratio=volume_ratio; signal.disloc_extreme=g_disloc_extreme;
   g_reversions++;
   if(signal.direction>0) g_long_signals++; else g_short_signals++;
   if(InpEnableTelemetry)
      PrintFormat("VDR001_SIGNAL decision=%I64d availability=%I64d variant=%s direction=%s age=%d disloc_time=%I64d extreme=%.5f o=%.5f h=%.5f l=%.5f c=%.5f body_ratio=%.6f vwap=%.5f distance_atr=%.6f volume_ratio=%.6f atr=%.5f",
                  (long)bar.time,(long)availability_time,InpVariantTag,(signal.direction>0 ? "LONG" : "SHORT"),
                  g_setup_age,(long)g_disloc_time,g_disloc_extreme,bar.open,bar.high,bar.low,bar.close,
                  body_ratio,vwap,distance/atr,volume_ratio,atr);
   return(true);
  }

int VolumeDigits(const double step)
  {
   int digits=0; double value=step;
   while(digits<8 && MathAbs(value-MathRound(value))>1e-9) { value*=10.0; digits++; }
   return(digits);
  }

double NormalizeVolumeDown(const double volume)
  {
   const double vmin=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN),vmax=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX),step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);
   if(vmin<=0.0 || vmax<vmin || step<=0.0 || volume<vmin) return(0.0);
   const double units=MathFloor((MathMin(volume,vmax)-vmin+1e-12)/step);
   return(NormalizeDouble(vmin+units*step,VolumeDigits(step)));
  }

double FloorToTick(const double p,const double tick) { return(MathFloor(p/tick+1e-10)*tick); }
double CeilToTick(const double p,const double tick) { return(MathCeil(p/tick-1e-10)*tick); }

bool OwnedPosition(ulong &ticket)
  {
   ticket=0; int owned=0;
   for(int i=PositionsTotal()-1;i>=0;i--)
     {
      const ulong current=PositionGetTicket(i);
      if(current>0 && PositionSelectByTicket(current) && PositionGetString(POSITION_SYMBOL)==_Symbol && PositionGetInteger(POSITION_MAGIC)==InpMagic)
        { ticket=current; owned++; }
     }
   if(owned>1) g_runtime_failed=true;
   return(owned==1);
  }

bool AnySymbolExposure()
  {
   for(int i=PositionsTotal()-1;i>=0;i--)
     {
      const ulong ticket=PositionGetTicket(i);
      if(ticket>0 && PositionSelectByTicket(ticket) && PositionGetString(POSITION_SYMBOL)==_Symbol) return(true);
     }
   return(false);
  }

void RefreshRiskLocks(const datetime now)
  {
   const double equity=AccountInfoDouble(ACCOUNT_EQUITY);
   const int day=DayKey(now); const long week=WeekKey(now);
   if(day!=g_day_key) { g_day_key=day; g_day_start_equity=equity; g_day_locked=false; }
   if(week!=g_week_key) { g_week_key=week; g_week_start_equity=equity; g_week_locked=false; }
   if(g_day_start_equity>0.0 && equity<=g_day_start_equity*(1.0-InpDailyLossPct/100.0)) g_day_locked=true;
   if(g_week_start_equity>0.0 && equity<=g_week_start_equity*(1.0-InpWeeklyLossPct/100.0)) g_week_locked=true;
  }

bool CloseOwned(const string reason)
  {
   ulong ticket=0; if(!OwnedPosition(ticket)) return(true);
   g_close_attempts++; g_pending_exit_reason=reason;
   if(!g_trade.PositionClose(ticket,InpDeviationPoints)) { g_close_rejects++; return(false); }
   const uint code=g_trade.ResultRetcode();
   if(code!=TRADE_RETCODE_DONE && code!=TRADE_RETCODE_DONE_PARTIAL) { g_close_rejects++; return(false); }
   g_closes++; PrintFormat("VDR001_CLOSE_REQUEST reason=%s ticket=%I64u retcode=%u",reason,ticket,code); return(true);
  }

bool ModifyStop(const ulong ticket,const double proposed,const string reason)
  {
   if(!PositionSelectByTicket(ticket)) return(false);
   const bool is_long=((ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_BUY);
   const double current=PositionGetDouble(POSITION_SL);
   MqlTick tick; if(!SymbolInfoTick(_Symbol,tick)) return(false);
   const double point=SymbolInfoDouble(_Symbol,SYMBOL_POINT),tick_size=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);
   if(point<=0.0 || tick_size<=0.0) return(false);
   const double next=(is_long ? FloorToTick(proposed,tick_size) : CeilToTick(proposed,tick_size));
   if((is_long && current>=next-point*0.1) || (!is_long && current>0.0 && current<=next+point*0.1)) return(false);
   const double min_dist=(double)MathMax(MathMax(SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL),SymbolInfoInteger(_Symbol,SYMBOL_TRADE_FREEZE_LEVEL)),0)*point;
   if((is_long && tick.bid-next<min_dist) || (!is_long && next-tick.ask<min_dist)) return(false);
   if(!g_trade.PositionModify(ticket,next,0.0)) return(false);
   const uint code=g_trade.ResultRetcode();
   if(code!=TRADE_RETCODE_DONE && code!=TRADE_RETCODE_NO_CHANGES) return(false);
   PrintFormat("VDR001_STOP_MOVE reason=%s ticket=%I64u sl=%.5f mfe_points=%.1f mae_points=%.1f",reason,ticket,next,g_mfe_points,g_mae_points);
   return(true);
  }

void UpdateStops(const ulong ticket,const bool new_bar)
  {
   if(!PositionSelectByTicket(ticket) || g_initial_risk<=0.0 || g_entry_price<=0.0) return;
   const bool is_long=((ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_BUY);
   MqlTick tick; if(!SymbolInfoTick(_Symbol,tick)) return;
   const double point=SymbolInfoDouble(_Symbol,SYMBOL_POINT); if(point<=0.0) return;
   const double quote=(is_long ? tick.bid : tick.ask);
   const double favorable=(is_long ? quote-g_entry_price : g_entry_price-quote);
   g_mfe_points=MathMax(g_mfe_points,MathMax(0.0,favorable)/point);
   g_mae_points=MathMax(g_mae_points,MathMax(0.0,-favorable)/point);
   if(favorable>=InpBETriggerR*g_initial_risk)
     {
      const double be=(is_long ? g_entry_price+InpBEOffsetR*g_initial_risk : g_entry_price-InpBEOffsetR*g_initial_risk);
      if(ModifyStop(ticket,be,"BREAKEVEN_PLUS")) g_be_moves++;
     }
   if(!g_trail_armed && favorable>=InpTrailStartR*g_initial_risk)
     { g_trail_armed=true; g_trail_arms++; PrintFormat("VDR001_TRAIL_ARM ticket=%I64u",ticket); }
   if(!new_bar || !g_trail_armed) return;
   MqlRates closed[]; ArraySetAsSeries(closed,true);
   if(CopyRates(_Symbol,PERIOD_M5,1,1,closed)!=1) return;
   double atr=0.0; if(!LoadAtr(atr)) return;
   const double trail=(is_long ? closed[0].close-InpTrailATRMult*atr : closed[0].close+InpTrailATRMult*atr);
   if(ModifyStop(ticket,trail,"ATR_TRAIL")) g_trail_moves++;
  }

void ManagePosition(const datetime now,const datetime bar_open,const bool new_bar)
  {
   ulong ticket=0; if(!OwnedPosition(ticket)) return;
   g_state=STATE_IN_POSITION; UpdateStops(ticket,new_bar);
   MqlDateTime p; TimeToStruct(now,p); const int minute=p.hour*60+p.min;
   string reason="";
   if(p.day_of_week==5 && minute>=InpFridayFlatHour*60+InpFridayFlatMinute) reason="FRIDAY_FLAT";
   else if(minute>=InpDailyFlatHour*60+InpDailyFlatMinute) reason="DAILY_FLAT";
   else
     {
      datetime started=g_entry_time;
      if(started<=0 && PositionSelectByTicket(ticket)) started=(datetime)PositionGetInteger(POSITION_TIME);
      if(started>0 && iBarShift(_Symbol,PERIOD_M5,started,false)>=InpTimeStopBars) reason="TIME_STOP";
     }
   if(reason=="" || g_last_close_attempt_bar==bar_open) return;
   g_last_close_attempt_bar=bar_open; CloseOwned(reason);
  }

bool EntryWindowOpen(const datetime stamp)
  {
   MqlDateTime p; TimeToStruct(stamp,p);
   if(p.day_of_week==0 || p.day_of_week==6) return(false);
   const int minute=p.hour*60+p.min;
   if(p.day_of_week==5 && minute>=InpFridayFlatHour*60+InpFridayFlatMinute) return(false);
   return(minute<InpDailyFlatHour*60+InpDailyFlatMinute);
  }

bool SubmitEntry(const EntrySignal &signal)
  {
   if(!signal.fired || AnySymbolExposure() || !EntryWindowOpen(signal.availability_time)) return(false);
   if(g_day_locked || g_week_locked) { g_risk_lock_skips++; return(false); }
   MqlTick tick; if(!SymbolInfoTick(_Symbol,tick) || tick.ask<=tick.bid || tick.bid<=0.0) return(false);
   const double point=SymbolInfoDouble(_Symbol,SYMBOL_POINT),tick_size=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE),contract=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_CONTRACT_SIZE);
   if(point<=0.0 || tick_size<=0.0 || contract<=0.0) return(false);
   const double spread=(tick.ask-tick.bid)/point;
   if(!IsFinite(spread) || spread>InpMaxSpreadPoints) { g_spread_rejects++; return(false); }
   const double entry=(signal.direction>0 ? tick.ask : tick.bid);
   const double structural=(signal.direction>0 ? signal.disloc_extreme-InpSLATRBuffer*signal.atr : signal.disloc_extreme+InpSLATRBuffer*signal.atr);
   double distance=(signal.direction>0 ? entry-structural : structural-entry);
   distance=MathMax(InpMinSLATR*signal.atr,MathMin(distance,InpMaxSLATR*signal.atr));
   if(!IsFinite(distance) || distance<=0.0) return(false);
   const double sl=(signal.direction>0 ? FloorToTick(entry-distance,tick_size) : CeilToTick(entry+distance,tick_size));
   const double min_dist=(double)MathMax(MathMax(SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL),SymbolInfoInteger(_Symbol,SYMBOL_TRADE_FREEZE_LEVEL)),0)*point;
   if(MathAbs(entry-sl)<min_dist) return(false);
   const ENUM_ORDER_TYPE type=(signal.direction>0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL);
   double one_lot_loss=0.0,margin_per_lot=0.0;
   if(!OrderCalcProfit(type,_Symbol,1.0,entry,sl,one_lot_loss) || one_lot_loss>=0.0) return(false);
   if(!OrderCalcMargin(type,_Symbol,1.0,entry,margin_per_lot) || margin_per_lot<=0.0) return(false);
   const double equity=AccountInfoDouble(ACCOUNT_EQUITY),free_margin=AccountInfoDouble(ACCOUNT_MARGIN_FREE);
   if(equity<=0.0 || free_margin<=0.0) return(false);
   const double volume_risk=equity*(InpRiskPercent/100.0)/MathAbs(one_lot_loss);
   const double volume_notional=(equity*InpMaxNotionalMult)/(entry*contract);
   const double volume_margin=(free_margin*(InpMaxMarginUsagePct/100.0))/margin_per_lot;
   const double volume=NormalizeVolumeDown(MathMin(volume_risk,MathMin(volume_notional,volume_margin)));
   if(volume<=0.0) return(false);
   double margin=0.0; if(!OrderCalcMargin(type,_Symbol,volume,entry,margin)) return(false);
   const double notional=volume*entry*contract;
   if(margin>free_margin*(InpMaxMarginUsagePct/100.0)+0.01 || notional>equity*InpMaxNotionalMult+0.01) return(false);
   g_trade.SetExpertMagicNumber(InpMagic); g_trade.SetDeviationInPoints(InpDeviationPoints); g_trade.SetTypeFillingBySymbol(_Symbol);
   const bool sent=g_trade.PositionOpen(_Symbol,type,volume,entry,sl,0.0,InpVariantTag);
   const uint code=g_trade.ResultRetcode();
   if(!sent || (code!=TRADE_RETCODE_DONE && code!=TRADE_RETCODE_DONE_PARTIAL)) { g_entry_rejects++; return(false); }
   g_entries++; g_state=STATE_IN_POSITION; g_entry_time=signal.availability_time;
   g_entry_price=(g_trade.ResultPrice()>0.0 ? g_trade.ResultPrice() : entry); g_initial_sl=sl; g_initial_risk=MathAbs(g_entry_price-sl);
   g_entry_margin_usage_pct=100.0*margin/free_margin; g_mfe_points=0.0; g_mae_points=0.0; g_trail_armed=false; g_pending_exit_reason="";
   PrintFormat("VDR001_ENTRY decision=%I64d direction=%s age=%d volume=%.2f entry=%.5f sl=%.5f tp=0 initial_risk=%.5f risk_pct=%.3f spread_points=%.1f distance_atr=%.6f volume_ratio=%.6f volume_risk=%.4f volume_notional=%.4f volume_margin=%.4f notional_equity_mult=%.4f margin_usage_pct=%.4f equity=%.2f retcode=%u",
               (long)signal.decision_time,(signal.direction>0 ? "LONG" : "SHORT"),signal.setup_age,volume,g_entry_price,sl,g_initial_risk,
               InpRiskPercent,spread,signal.distance_atr,signal.volume_ratio,volume_risk,volume_notional,volume_margin,notional/equity,g_entry_margin_usage_pct,equity,code);
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
   const long kind=HistoryDealGetInteger(trans.deal,DEAL_ENTRY); if(kind!=DEAL_ENTRY_OUT && kind!=DEAL_ENTRY_OUT_BY) return;
   const long reason=HistoryDealGetInteger(trans.deal,DEAL_REASON);
   const double price=HistoryDealGetDouble(trans.deal,DEAL_PRICE),profit=HistoryDealGetDouble(trans.deal,DEAL_PROFIT),commission=HistoryDealGetDouble(trans.deal,DEAL_COMMISSION),swap=HistoryDealGetDouble(trans.deal,DEAL_SWAP);
   const datetime stamp=(datetime)HistoryDealGetInteger(trans.deal,DEAL_TIME);
   PrintFormat("VDR001_EXIT time=%I64d deal=%I64u reason=%s price=%.5f profit=%.2f commission=%.2f swap=%.2f net=%.2f mfe_points=%.1f mae_points=%.1f margin_usage_pct=%.4f bars_held=%d equity=%.2f",
               (long)stamp,trans.deal,ExitReasonName(reason),price,profit,commission,swap,profit+commission+swap,g_mfe_points,g_mae_points,
               g_entry_margin_usage_pct,(g_entry_time>0 ? iBarShift(_Symbol,PERIOD_M5,g_entry_time,false) : -1),AccountInfoDouble(ACCOUNT_EQUITY));
   ulong ticket=0;
   if(!OwnedPosition(ticket))
     { g_entry_time=0; g_entry_price=0.0; g_initial_sl=0.0; g_initial_risk=0.0; g_entry_margin_usage_pct=0.0; g_trail_armed=false; g_pending_exit_reason=""; ResetSetup("POSITION_CLOSED"); }
  }

bool InputsAreFrozen()
  {
   const bool variant_ok=((InpVariantTag==PRIMARY_VARIANT && InpUseVolumeReversionState) || (InpVariantTag==CONTROL_VARIANT && !InpUseVolumeReversionState));
   return(InpResearchAutoMode && InpEnableTelemetry && InpHypothesisId==EXPECTED_HYPOTHESIS && variant_ok &&
          InpVWAPWindow==18 && InpVolumeSMAPeriod==18 && InpATRPeriod==14 && MathAbs(InpDislocATRMult-1.35)<1e-12 &&
          MathAbs(InpVolumeExpandMult-1.45)<1e-12 && InpMaxBarsDislocToRev==6 && MathAbs(InpReversionBodyMin-0.35)<1e-12 &&
          MathAbs(InpSLATRBuffer-0.30)<1e-12 && MathAbs(InpMinSLATR-1.00)<1e-12 && MathAbs(InpMaxSLATR-2.30)<1e-12 &&
          MathAbs(InpBETriggerR-0.90)<1e-12 && MathAbs(InpBEOffsetR-0.12)<1e-12 && MathAbs(InpTrailStartR-1.50)<1e-12 &&
          MathAbs(InpTrailATRMult-0.70)<1e-12 && InpTimeStopBars==24 && MathAbs(InpRiskPercent-0.25)<1e-12 &&
          MathAbs(InpMaxNotionalMult-4.50)<1e-12 && MathAbs(InpMaxMarginUsagePct-12.0)<1e-12 && InpMaxSpreadPoints==15 &&
          MathAbs(InpDailyLossPct-1.00)<1e-12 && MathAbs(InpWeeklyLossPct-2.50)<1e-12 && InpDailyFlatHour==21 &&
          InpDailyFlatMinute==50 && InpFridayFlatHour==18 && InpFridayFlatMinute==50 && InpDeviationPoints==5 && InpMagic==5605001);
  }

int OnInit()
  {
   if(_Period!=PERIOD_M5 || !InputsAreFrozen()) return(INIT_PARAMETERS_INCORRECT);
   g_atr_handle=iATR(_Symbol,PERIOD_M5,InpATRPeriod); if(g_atr_handle==INVALID_HANDLE) return(INIT_FAILED);
   if(!EmitSeriesProof()) return(INIT_FAILED);
   g_trade.SetExpertMagicNumber(InpMagic); g_trade.SetDeviationInPoints(InpDeviationPoints); g_trade.SetTypeFillingBySymbol(_Symbol);
   const datetime now=TimeCurrent(); const double equity=AccountInfoDouble(ACCOUNT_EQUITY);
   g_day_key=DayKey(now); g_week_key=WeekKey(now); g_day_start_equity=equity; g_week_start_equity=equity;
   if(!CurrentBarOpen(g_last_bar_open) || g_last_bar_open<=0) return(INIT_FAILED);
   PrintFormat("VDR001_INIT ea=%s hypothesis=%s variant=%s symbol=%s timeframe=M5 volume_state=%s missing_volume=FAIL_CLOSED no_fixed_tp=true",
               EA_NAME,InpHypothesisId,InpVariantTag,_Symbol,(InpUseVolumeReversionState ? "true" : "false"));
   return(INIT_SUCCEEDED);
  }

void OnDeinit(const int reason)
  {
   if(g_atr_handle!=INVALID_HANDLE) IndicatorRelease(g_atr_handle);
   PrintFormat("VDR001_SUMMARY reason=%d runtime_failed=%s closed_bars=%I64d dislocations=%I64d reversions=%I64d expiries=%I64d long=%I64d short=%I64d spread_rejects=%I64d risk_lock_skips=%I64d entries=%I64d entry_rejects=%I64d be_moves=%I64d trail_arms=%I64d trail_moves=%I64d close_attempts=%I64d close_rejects=%I64d closes=%I64d invalid=%I64d missing_volume=%I64d",
               reason,(g_runtime_failed ? "true" : "false"),g_closed_bars,g_dislocations,g_reversions,g_expiries,g_long_signals,g_short_signals,
               g_spread_rejects,g_risk_lock_skips,g_entries,g_entry_rejects,g_be_moves,g_trail_arms,g_trail_moves,g_close_attempts,g_close_rejects,g_closes,g_invalid_inputs,g_missing_volume);
  }

void OnTick()
  {
   datetime bar_open=0; if(!CurrentBarOpen(bar_open) || bar_open<=0) return;
   const bool new_bar=(bar_open!=g_last_bar_open); const datetime now=TimeCurrent();
   RefreshRiskLocks(now); ManagePosition(now,bar_open,new_bar); if(!new_bar) return;
   g_last_bar_open=bar_open; if(AnySymbolExposure()) return;
   if(g_state==STATE_IN_POSITION) ResetSetup("NO_POSITION_ON_NEW_BAR");
   EntrySignal signal;
   if(BuildSignal(bar_open,signal) && signal.fired) { if(!SubmitEntry(signal)) ResetSetup("SIGNAL_CANCELLED_OR_REJECTED"); }
  }
