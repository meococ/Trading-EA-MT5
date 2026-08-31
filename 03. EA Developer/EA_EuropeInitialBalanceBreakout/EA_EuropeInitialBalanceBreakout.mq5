
//+------------------------------------------------------------------+
//| EA_EuropeInitialBalanceBreakout.mq5                         |
//| HYP-EIBB-XAUUSD-M15-001: M5-built initial-balance breakout |
//+------------------------------------------------------------------+
#property strict
#property version   "1.00"
#property description "Untuned XAUUSD M5-built M15 initial-balance breakout"

#include <Trade/Trade.mqh>

input group "--- Frozen research authority ---"
input bool   InpResearchAutoMode=false;
input bool   InpEnableTelemetry=false;
input string InpHypothesisId="HYP-EIBB-XAUUSD-M15-001";
input string InpVariantTag="UTC0700_4BAR_INITIAL_BALANCE_FIRST_CLOSE_BREAK";

input group "--- Frozen execution and risk ---"
input long   InpMagic=5604501;
input double InpRiskPercent=0.10;
input double InpMaxDailyLossPct=3.5;
input double InpMaxAccountDrawdownPct=8.0;
input int    InpDeviationPoints=20;
input int    InpSessionFlattenHourUtc=20;

const string EA_NAME="EA_EuropeInitialBalanceBreakout";
const string EXPECTED_HYPOTHESIS="HYP-EIBB-XAUUSD-M15-001";
const string EXPECTED_VARIANT="UTC0700_4BAR_INITIAL_BALANCE_FIRST_CLOSE_BREAK";
const string EXPECTED_SYMBOL="XAUUSD";
const int HISTORY_BARS=600;
const int MIN_HISTORY_BARS=120;
const int INITIAL_BALANCE_START_MINUTE_UTC=7*60;
const int INITIAL_BALANCE_BARS=4;
const int SCAN_START_MINUTE_UTC=8*60;
const int SCAN_END_MINUTE_UTC=16*60;
const double TARGET_R=1.50;
const int MAX_HOLD_M5_BARS=48;
const datetime DESIGN_FROM=D'2018.01.01 00:00';
const datetime DESIGN_TO=D'2023.01.01 00:00';

struct SyntheticM15
  {
   datetime time_server;
   datetime time_utc;
   double open;
   double high;
   double low;
   double close;
   long tick_volume;
  };

struct SignalDecision
  {
   bool fired;
   datetime decision_time;
   datetime availability_time;
   int direction;
   int utc_date_key;
   double initial_balance_high;
   double initial_balance_low;
   double source_close;
   double structural_stop;
  };

CTrade g_trade;
datetime g_last_bar_open=0;
datetime g_last_decision_time=0;
datetime g_entry_time=0;
datetime g_last_close_attempt_bar=0;
int g_consumed_utc_date=0;
int g_last_valid_ib_date=0;
int g_daily_utc_key=0;
double g_daily_start_equity=0.0;
double g_peak_equity=0.0;
bool g_daily_locked=false;
bool g_drawdown_locked=false;
bool g_runtime_failed=false;
long g_closed_bars=0;
long g_valid_initial_balance_dates=0;
long g_raw_signals=0;
long g_long_signals=0;
long g_short_signals=0;
long g_entries=0;
long g_entry_rejects=0;
long g_close_attempts=0;
long g_close_rejects=0;
long g_closes=0;
long g_clock_rejects=0;
long g_invalid_inputs=0;
long g_risk_lock_skips=0;

bool IsFinite(const double value)
  {
   return(value!=EMPTY_VALUE && MathIsValidNumber(value));
  }

datetime MakeTime(const int year,const int month,const int day,
                  const int hour,const int minute=0,const int second=0)
  {
   MqlDateTime p;
   ZeroMemory(p);
   p.year=year;
   p.mon=month;
   p.day=day;
   p.hour=hour;
   p.min=minute;
   p.sec=second;
   return(StructToTime(p));
  }

int DaysInMonth(const int year,const int month)
  {
   if(month==2)
      return(((year%4==0 && year%100!=0) || year%400==0) ? 29 : 28);
   if(month==4 || month==6 || month==9 || month==11)
      return(30);
   return(31);
  }

int LastSunday(const int year,const int month)
  {
   const int last=DaysInMonth(year,month);
   MqlDateTime p;
   TimeToStruct(MakeTime(year,month,last,0),p);
   return(last-p.day_of_week);
  }

bool IsBrokerDstServerTime(const datetime server_time)
  {
   MqlDateTime p;
   TimeToStruct(server_time,p);
   const datetime start=MakeTime(p.year,3,LastSunday(p.year,3),3);
   const datetime finish=MakeTime(p.year,10,LastSunday(p.year,10),4);
   return(server_time>=start && server_time<finish);
  }

datetime ServerToUtc(const datetime server_time)
  {
   return(server_time-(IsBrokerDstServerTime(server_time) ? 3 : 2)*3600);
  }

int DateKey(const datetime stamp)
  {
   MqlDateTime p;
   TimeToStruct(stamp,p);
   return(p.year*10000+p.mon*100+p.day);
  }

bool ValidRate(const MqlRates &bar)
  {
   return(bar.time>0 && IsFinite(bar.open) && IsFinite(bar.high) &&
          IsFinite(bar.low) && IsFinite(bar.close) &&
          bar.open>0.0 && bar.high>0.0 && bar.low>0.0 && bar.close>0.0 &&
          bar.tick_volume>0 &&
          bar.high>=MathMax(bar.open,bar.close) &&
          bar.low<=MathMin(bar.open,bar.close) && bar.high>=bar.low);
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

bool LoadClosedRates(MqlRates &rates[])
  {
   ArraySetAsSeries(rates,false);
   const int copied=CopyRates(_Symbol,PERIOD_M5,1,HISTORY_BARS,rates);
   if(copied<MIN_HISTORY_BARS)
      return(false);
   ArrayResize(rates,copied);
   return(true);
  }

int MinuteOfDay(const datetime utc_time)
  {
   MqlDateTime p;
   TimeToStruct(utc_time,p);
   return(p.hour*60+p.min);
  }

bool BuildSyntheticM15(const MqlRates &rates[],SyntheticM15 &bars[])
  {
   ArrayResize(bars,0);
   const int total=ArraySize(rates);
   for(int i=0;i+2<total;i++)
     {
      if(!ValidRate(rates[i]) || !ValidRate(rates[i+1]) || !ValidRate(rates[i+2]))
         continue;
      const datetime utc0=ServerToUtc(rates[i].time);
      const datetime utc1=ServerToUtc(rates[i+1].time);
      const datetime utc2=ServerToUtc(rates[i+2].time);
      if(MinuteOfDay(utc0)%15!=0 ||
         (long)(utc1-utc0)!=300 || (long)(utc2-utc1)!=300 ||
         (long)(rates[i+1].time-rates[i].time)!=300 ||
         (long)(rates[i+2].time-rates[i+1].time)!=300)
         continue;
      const int size=ArraySize(bars);
      ArrayResize(bars,size+1);
      bars[size].time_server=rates[i].time;
      bars[size].time_utc=utc0;
      bars[size].open=rates[i].open;
      bars[size].high=MathMax(rates[i].high,MathMax(rates[i+1].high,rates[i+2].high));
      bars[size].low=MathMin(rates[i].low,MathMin(rates[i+1].low,rates[i+2].low));
      bars[size].close=rates[i+2].close;
      bars[size].tick_volume=rates[i].tick_volume+rates[i+1].tick_volume+rates[i+2].tick_volume;
     }
   return(ArraySize(bars)>0);
  }

bool BuildSignal(const datetime availability_time,SignalDecision &signal)
  {
   ZeroMemory(signal);
   const datetime availability_utc=ServerToUtc(availability_time);
   if(MinuteOfDay(availability_utc)%15!=0)
      return(false);

   MqlRates rates[];
   if(!LoadClosedRates(rates))
     {
      g_invalid_inputs++;
      return(false);
     }
   SyntheticM15 bars[];
   if(!BuildSyntheticM15(rates,bars))
     {
      g_invalid_inputs++;
      return(false);
     }
   const int current=ArraySize(bars)-1;
   const datetime decision_time=bars[current].time_server;
   const datetime decision_utc=bars[current].time_utc;
   if(decision_time<=0 || decision_time==g_last_decision_time)
      return(false);
   g_last_decision_time=decision_time;
   g_closed_bars++;
   if((long)(availability_time-decision_time)!=900 ||
      (long)(availability_utc-decision_utc)!=900)
     {
      g_clock_rejects++;
      return(false);
     }
   if(decision_utc<DESIGN_FROM || decision_utc>=DESIGN_TO ||
      availability_utc>DESIGN_TO)
      return(false);

   MqlDateTime decision_parts;
   TimeToStruct(decision_utc,decision_parts);
   if(decision_parts.day_of_week==0 || decision_parts.day_of_week==6)
      return(false);
   const int decision_minute=MinuteOfDay(decision_utc);
   if(decision_minute<SCAN_START_MINUTE_UTC || decision_minute>=SCAN_END_MINUTE_UTC)
      return(false);
   const int key=DateKey(decision_utc);

   double ib_high=-DBL_MAX;
   double ib_low=DBL_MAX;
   datetime ib_server[4];
   ArrayInitialize(ib_server,0);
   int ib_count=0;
   for(int i=0;i<=current;i++)
     {
      if(DateKey(bars[i].time_utc)!=key)
         continue;
      const int offset=MinuteOfDay(bars[i].time_utc)-INITIAL_BALANCE_START_MINUTE_UTC;
      if(offset<0 || offset>=INITIAL_BALANCE_BARS*15 || offset%15!=0)
         continue;
      const int slot=offset/15;
      if(ib_server[slot]!=0)
        {
         g_invalid_inputs++;
         return(false);
        }
      ib_server[slot]=bars[i].time_server;
      ib_high=MathMax(ib_high,bars[i].high);
      ib_low=MathMin(ib_low,bars[i].low);
      ib_count++;
     }
   if(ib_count!=INITIAL_BALANCE_BARS || !IsFinite(ib_high) || !IsFinite(ib_low) || ib_high<=ib_low)
      return(false);
   for(int slot=1;slot<INITIAL_BALANCE_BARS;slot++)
      if((long)(ib_server[slot]-ib_server[slot-1])!=900)
        {
         g_clock_rejects++;
         return(false);
        }
   if(key!=g_last_valid_ib_date)
     {
      g_last_valid_ib_date=key;
      g_valid_initial_balance_dates++;
     }

   int first_direction=0;
   datetime first_break_time=0;
   double first_break_close=0.0;
   for(int i=0;i<=current;i++)
     {
      if(DateKey(bars[i].time_utc)!=key)
         continue;
      const int minute=MinuteOfDay(bars[i].time_utc);
      if(minute<SCAN_START_MINUTE_UTC || minute>=SCAN_END_MINUTE_UTC)
         continue;
      const bool long_break=(bars[i].close>ib_high);
      const bool short_break=(bars[i].close<ib_low);
      if(long_break==short_break)
         continue;
      first_direction=(long_break ? 1 : -1);
      first_break_time=bars[i].time_server;
      first_break_close=bars[i].close;
      break;
     }
   if(first_direction==0 || first_break_time!=decision_time)
      return(false);
   if(key==g_consumed_utc_date)
      return(false);
   g_consumed_utc_date=key;

   signal.fired=true;
   signal.decision_time=decision_time;
   signal.availability_time=availability_time;
   signal.direction=first_direction;
   signal.utc_date_key=key;
   signal.initial_balance_high=ib_high;
   signal.initial_balance_low=ib_low;
   signal.source_close=first_break_close;
   signal.structural_stop=(first_direction>0 ? ib_low : ib_high);
   g_raw_signals++;
   if(first_direction>0) g_long_signals++; else g_short_signals++;
   PrintFormat("EIBB001_SIGNAL decision=%I64d availability=%I64d utc_date=%d direction=%s close=%.5f ib_high=%.5f ib_low=%.5f stop=%.5f",
               (long)decision_time,(long)availability_time,key,
               (first_direction>0 ? "LONG" : "SHORT"),first_break_close,
               ib_high,ib_low,signal.structural_stop);
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

double FloorToTick(const double price,const double tick)
  {
   return(MathFloor(price/tick+1e-10)*tick);
  }

double CeilToTick(const double price,const double tick)
  {
   return(MathCeil(price/tick-1e-10)*tick);
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
   const int key=DateKey(ServerToUtc(server_now));
   if(g_daily_utc_key!=key)
     {
      g_daily_utc_key=key;
      g_daily_start_equity=equity;
      g_daily_locked=false;
     }
   if(equity>g_peak_equity)
      g_peak_equity=equity;
   if(g_daily_start_equity>0.0 && equity<=g_daily_start_equity*(1.0-InpMaxDailyLossPct/100.0))
      g_daily_locked=true;
   if(g_peak_equity>0.0 && equity<=g_peak_equity*(1.0-InpMaxAccountDrawdownPct/100.0))
      g_drawdown_locked=true;
  }

bool CloseOwned(const string reason)
  {
   ulong ticket=0;
   if(!OwnedPosition(ticket))
      return(true);
   g_close_attempts++;
   g_trade.SetDeviationInPoints(InpDeviationPoints);
   if(!g_trade.PositionClose(ticket,InpDeviationPoints))
     {
      g_close_rejects++;
      PrintFormat("EIBB001_CLOSE_REJECT reason=%s ticket=%I64u retcode=%u",reason,ticket,g_trade.ResultRetcode());
      return(false);
     }
   const uint retcode=g_trade.ResultRetcode();
   if(retcode!=TRADE_RETCODE_DONE && retcode!=TRADE_RETCODE_DONE_PARTIAL)
     {
      g_close_rejects++;
      PrintFormat("EIBB001_CLOSE_REJECT reason=%s ticket=%I64u retcode=%u",reason,ticket,retcode);
      return(false);
     }
   g_closes++;
   g_entry_time=0;
   PrintFormat("EIBB001_CLOSE reason=%s ticket=%I64u retcode=%u",reason,ticket,retcode);
   return(true);
  }

void ManagePosition(const datetime current_open)
  {
   ulong ticket=0;
   if(!OwnedPosition(ticket))
      return;
   const datetime current_utc=ServerToUtc(current_open);
   datetime entry_time=g_entry_time;
   if(entry_time<=0 && PositionSelectByTicket(ticket))
      entry_time=(datetime)PositionGetInteger(POSITION_TIME);
   const datetime entry_utc=ServerToUtc(entry_time);
   MqlDateTime now_parts;
   TimeToStruct(current_utc,now_parts);
   bool must_close=(DateKey(current_utc)!=DateKey(entry_utc) || now_parts.hour>=InpSessionFlattenHourUtc);
   if(!must_close && entry_time>0)
     {
      const int shift=iBarShift(_Symbol,PERIOD_M5,entry_time,false);
      must_close=(shift>=MAX_HOLD_M5_BARS);
     }
   if(must_close)
     {
      // Retry a required exit once per native M5 bar without journal flooding.
      if(g_last_close_attempt_bar==current_open)
         return;
      g_last_close_attempt_bar=current_open;
      CloseOwned("TIME_OR_SESSION_EXIT");
     }
  }

bool SubmitEntry(const SignalDecision &signal)
  {
   if(!signal.fired || AnySymbolExposure())
      return(false);
   if(g_daily_locked || g_drawdown_locked)
     {
      g_risk_lock_skips++;
      return(false);
     }
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick) || !IsFinite(tick.ask) || !IsFinite(tick.bid) ||
      tick.ask<=0.0 || tick.bid<=0.0 || tick.ask<=tick.bid)
      return(false);
   const double tick_size=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);
   const double point=SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   if(!IsFinite(tick_size) || tick_size<=0.0 || !IsFinite(point) || point<=0.0)
      return(false);
   const double entry=(signal.direction>0 ? tick.ask : tick.bid);
   const double sl=(signal.direction>0
                    ? FloorToTick(signal.structural_stop,tick_size)
                    : CeilToTick(signal.structural_stop,tick_size));
   if((signal.direction>0 && sl>=entry) || (signal.direction<0 && sl<=entry))
      return(false);
   const double risk_distance=MathAbs(entry-sl);
   const double raw_target=entry+signal.direction*TARGET_R*risk_distance;
   const double tp=(signal.direction>0 ? CeilToTick(raw_target,tick_size) : FloorToTick(raw_target,tick_size));
   const long stops_level=SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL);
   const long freeze_level=SymbolInfoInteger(_Symbol,SYMBOL_TRADE_FREEZE_LEVEL);
   const double minimum_distance=(double)MathMax(MathMax(stops_level,freeze_level),0)*point;
   if(risk_distance<minimum_distance || MathAbs(tp-entry)<minimum_distance)
      return(false);

   const ENUM_ORDER_TYPE type=(signal.direction>0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL);
   double loss_one_lot=0.0;
   if(!OrderCalcProfit(type,_Symbol,1.0,entry,sl,loss_one_lot) ||
      !IsFinite(loss_one_lot) || loss_one_lot>=0.0)
      return(false);
   const double equity=AccountInfoDouble(ACCOUNT_EQUITY);
   const double volume=NormalizeVolumeDown(equity*(InpRiskPercent/100.0)/MathAbs(loss_one_lot));
   if(volume<=0.0)
      return(false);
   double margin=0.0;
   if(!OrderCalcMargin(type,_Symbol,volume,entry,margin) || !IsFinite(margin) ||
      margin>AccountInfoDouble(ACCOUNT_MARGIN_FREE))
      return(false);

   g_trade.SetExpertMagicNumber(InpMagic);
   g_trade.SetDeviationInPoints(InpDeviationPoints);
   g_trade.SetTypeFillingBySymbol(_Symbol);
   const bool sent=g_trade.PositionOpen(_Symbol,type,volume,entry,sl,tp,EXPECTED_VARIANT);
   const uint retcode=g_trade.ResultRetcode();
   if(!sent || (retcode!=TRADE_RETCODE_DONE && retcode!=TRADE_RETCODE_DONE_PARTIAL))
     {
      g_entry_rejects++;
      PrintFormat("EIBB001_ENTRY_REJECT direction=%s volume=%.2f entry=%.5f sl=%.5f tp=%.5f retcode=%u",
                  (signal.direction>0 ? "LONG" : "SHORT"),volume,entry,sl,tp,retcode);
      return(false);
     }
   g_entries++;
   g_entry_time=signal.availability_time;
   PrintFormat("EIBB001_ENTRY direction=%s volume=%.2f entry=%.5f sl=%.5f tp=%.5f risk_pct=%.3f retcode=%u",
               (signal.direction>0 ? "LONG" : "SHORT"),volume,entry,sl,tp,InpRiskPercent,retcode);
   return(true);
  }

int OnInit()
  {
   if(!InpResearchAutoMode || InpEnableTelemetry || _Symbol!=EXPECTED_SYMBOL || _Period!=PERIOD_M5 ||
      InpHypothesisId!=EXPECTED_HYPOTHESIS || InpVariantTag!=EXPECTED_VARIANT ||
      InpMagic!=5604501 || MathAbs(InpRiskPercent-0.10)>1e-12 ||
      MathAbs(InpMaxDailyLossPct-3.5)>1e-12 || MathAbs(InpMaxAccountDrawdownPct-8.0)>1e-12 ||
      InpDeviationPoints!=20 || InpSessionFlattenHourUtc!=20)
      return(INIT_PARAMETERS_INCORRECT);
   if(!EmitD0SeriesProof())
      return(INIT_FAILED);
   g_trade.SetExpertMagicNumber(InpMagic);
   g_trade.SetDeviationInPoints(InpDeviationPoints);
   g_trade.SetTypeFillingBySymbol(_Symbol);
   const double equity=AccountInfoDouble(ACCOUNT_EQUITY);
   g_peak_equity=equity;
   g_daily_start_equity=equity;
   g_daily_utc_key=DateKey(ServerToUtc(TimeCurrent()));
   if(!CurrentBarOpen(g_last_bar_open) || g_last_bar_open<=0)
      return(INIT_FAILED);
   PrintFormat("EIBB001_INIT ea=%s hypothesis=%s variant=%s symbol=%s timeframe=M5 synthetic=M15",
               EA_NAME,InpHypothesisId,InpVariantTag,_Symbol);
   return(INIT_SUCCEEDED);
  }

void OnDeinit(const int reason)
  {
   PrintFormat("EIBB001_SUMMARY reason=%d runtime_failed=%s closed_m15=%I64d ib_dates=%I64d raw=%I64d long=%I64d short=%I64d entries=%I64d rejects=%I64d close_attempts=%I64d close_rejects=%I64d closes=%I64d clock_rejects=%I64d invalid=%I64d risk_lock_skips=%I64d",
               reason,(g_runtime_failed ? "true" : "false"),g_closed_bars,
               g_valid_initial_balance_dates,g_raw_signals,g_long_signals,g_short_signals,
               g_entries,g_entry_rejects,g_close_attempts,g_close_rejects,g_closes,
               g_clock_rejects,g_invalid_inputs,g_risk_lock_skips);
  }

void OnTick()
  {
   datetime current_open=0;
   if(!CurrentBarOpen(current_open) || current_open<=0)
      return;
   RefreshRiskLocks(current_open);
   ManagePosition(current_open);
   if(current_open==g_last_bar_open)
      return;
   g_last_bar_open=current_open;
   if(AnySymbolExposure())
      return;
   SignalDecision signal;
   if(BuildSignal(current_open,signal) && signal.fired)
      SubmitEntry(signal);
  }

