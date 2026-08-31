//+------------------------------------------------------------------+
//| EA_PriorDayVolumeProfileReentry.mq5                              |
//| HYP-PVPR-EURUSD-M15-002: prior-day value-area reentry            |
//+------------------------------------------------------------------+
#property strict
#property version   "1.00"
#property description "Untuned EURUSD M15 prior-day volume-profile reentry"

#include <Trade/Trade.mqh>

input group "--- Frozen research authority ---"
input bool   InpResearchAutoMode=false;
input bool   InpEnableTelemetry=false;
input string InpHypothesisId="HYP-PVPR-EURUSD-M15-002";
input string InpVariantTag="PRIOR_UTC_DAY_VP70_FIRST_REENTRY_INT_POINTS";

input group "--- Frozen execution and risk ---"
input long   InpMagic=5604602;
input double InpRiskPercent=0.10;
input double InpMaxDailyLossPct=3.5;
input double InpMaxAccountDrawdownPct=8.0;
input int    InpDeviationPoints=20;
input int    InpSessionFlattenHourUtc=20;

const string EA_NAME="EA_PriorDayVolumeProfileReentry";
const string EXPECTED_HYPOTHESIS="HYP-PVPR-EURUSD-M15-002";
const string EXPECTED_VARIANT="PRIOR_UTC_DAY_VP70_FIRST_REENTRY_INT_POINTS";
const string EXPECTED_SYMBOL="EURUSD";
const double BROKER_POINT=0.00001;
const double PROFILE_PIP=0.0001;
const double VALUE_AREA_FRACTION=0.70;
const int MIN_PROFILE_ROWS=1000;
const int PROFILE_LOOKBACK_M1=3000;
const int SESSION_START_MINUTE_UTC=7*60;
const int SESSION_END_MINUTE_UTC=16*60;
const double TARGET_R=1.50;
const int MAX_HOLD_M15_BARS=16;
const datetime DESIGN_FROM=D'2016.01.04 00:00';
const datetime DESIGN_TO=D'2023.01.01 00:00';

struct PriorDayProfile
  {
   bool valid;
   int prior_date_key;
   int m1_rows;
   long poc_points;
   long val_points;
   long vah_points;
   double total_tick_volume;
  };

struct SignalDecision
  {
   bool fired;
   datetime source_time;
   datetime availability_time;
   int direction;
   int utc_date_key;
   long source_open_points;
   long source_close_points;
   long poc_points;
   long val_points;
   long vah_points;
   double source_high;
   double source_low;
   double structural_stop;
  };

CTrade g_trade;
datetime g_last_bar_open=0;
datetime g_entry_time=0;
datetime g_last_close_attempt_bar=0;
int g_consumed_utc_date=0;
int g_cached_source_date=0;
PriorDayProfile g_cached_profile;
int g_daily_utc_key=0;
double g_daily_start_equity=0.0;
double g_peak_equity=0.0;
bool g_daily_locked=false;
bool g_drawdown_locked=false;
bool g_runtime_failed=false;
long g_closed_m15=0;
long g_valid_profile_dates=0;
long g_invalid_profile_dates=0;
long g_raw_signals=0;
long g_long_signals=0;
long g_short_signals=0;
long g_entries=0;
long g_entry_rejects=0;
long g_geometry_rejects=0;
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
   MqlDateTime parts;
   ZeroMemory(parts);
   parts.year=year;
   parts.mon=month;
   parts.day=day;
   parts.hour=hour;
   parts.min=minute;
   parts.sec=second;
   return(StructToTime(parts));
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
   MqlDateTime parts;
   TimeToStruct(MakeTime(year,month,last,0),parts);
   return(last-parts.day_of_week);
  }

bool IsBrokerDstServerTime(const datetime server_time)
  {
   MqlDateTime parts;
   TimeToStruct(server_time,parts);
   const datetime start=MakeTime(parts.year,3,LastSunday(parts.year,3),3);
   const datetime finish=MakeTime(parts.year,10,LastSunday(parts.year,10),4);
   return(server_time>=start && server_time<finish);
  }

datetime ServerToUtc(const datetime server_time)
  {
   return(server_time-(IsBrokerDstServerTime(server_time) ? 3 : 2)*3600);
  }

int DateKey(const datetime stamp)
  {
   MqlDateTime parts;
   TimeToStruct(stamp,parts);
   return(parts.year*10000+parts.mon*100+parts.day);
  }

int MinuteOfDay(const datetime stamp)
  {
   MqlDateTime parts;
   TimeToStruct(stamp,parts);
   return(parts.hour*60+parts.min);
  }

bool ValidRate(const MqlRates &bar)
  {
   return(bar.time>0 && IsFinite(bar.open) && IsFinite(bar.high) &&
          IsFinite(bar.low) && IsFinite(bar.close) &&
          bar.open>0.0 && bar.high>0.0 && bar.low>0.0 && bar.close>0.0 &&
          bar.tick_volume>=0 && bar.high>=bar.low &&
          bar.high>=MathMax(bar.open,bar.close) &&
          bar.low<=MathMin(bar.open,bar.close));
  }

long PriceToPoints(const double price)
  {
   if(!IsFinite(price) || price<=0.0)
      return(-1);
   return((long)MathFloor(price/BROKER_POINT+0.5));
  }

int PriceToProfileBin(const double price)
  {
   if(!IsFinite(price) || price<=0.0)
      return(-1);
   return((int)MathFloor(price/PROFILE_PIP+0.5));
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

bool BuildPriorDayProfile(const datetime source_utc,PriorDayProfile &profile)
  {
   ZeroMemory(profile);
   const int source_date=DateKey(source_utc);
   const int prior_date=DateKey(source_utc-86400);
   profile.prior_date_key=prior_date;
   MqlRates rates[];
   ArraySetAsSeries(rates,false);
   const int copied=CopyRates(_Symbol,PERIOD_M1,1,PROFILE_LOOKBACK_M1,rates);
   if(copied<MIN_PROFILE_ROWS)
      return(false);

   int minimum_bin=2147483647;
   int maximum_bin=-2147483647;
   int row_count=0;
   int first_minute=1440;
   int last_minute=-1;
   double total_volume=0.0;
   double weighted_bin_sum=0.0;
   for(int i=0;i<copied;i++)
     {
      const datetime utc=ServerToUtc(rates[i].time);
      if(DateKey(utc)!=prior_date)
         continue;
      if(!ValidRate(rates[i]))
         return(false);
      const int bin=PriceToProfileBin((rates[i].high+rates[i].low+rates[i].close)/3.0);
      if(bin<=0)
         return(false);
      const double volume=(double)rates[i].tick_volume;
      minimum_bin=MathMin(minimum_bin,bin);
      maximum_bin=MathMax(maximum_bin,bin);
      total_volume+=volume;
      weighted_bin_sum+=(double)bin*volume;
      row_count++;
      const int minute=MinuteOfDay(utc);
      first_minute=MathMin(first_minute,minute);
      last_minute=MathMax(last_minute,minute);
     }
   if(source_date<=0 || row_count<MIN_PROFILE_ROWS || first_minute>15 ||
      last_minute<23*60+45 || !IsFinite(total_volume) || total_volume<=0.0 ||
      minimum_bin<=0 || maximum_bin<minimum_bin)
      return(false);

   const int bin_count=maximum_bin-minimum_bin+1;
   if(bin_count<=0 || bin_count>20000)
      return(false);
   double volumes[];
   ArrayResize(volumes,bin_count);
   ArrayInitialize(volumes,0.0);
   for(int i=0;i<copied;i++)
     {
      const datetime utc=ServerToUtc(rates[i].time);
      if(DateKey(utc)!=prior_date)
         continue;
      const int bin=PriceToProfileBin((rates[i].high+rates[i].low+rates[i].close)/3.0);
      if(bin<minimum_bin || bin>maximum_bin)
         return(false);
      volumes[bin-minimum_bin]+=(double)rates[i].tick_volume;
     }

   double maximum_volume=-1.0;
   for(int i=0;i<bin_count;i++)
      maximum_volume=MathMax(maximum_volume,volumes[i]);
   const double mean_bin=weighted_bin_sum/total_volume;
   int poc_index=-1;
   double best_distance=DBL_MAX;
   for(int i=0;i<bin_count;i++)
     {
      if(volumes[i]!=maximum_volume)
         continue;
      const int bin=minimum_bin+i;
      const double distance=MathAbs((double)bin-mean_bin);
      if(poc_index<0 || distance<best_distance ||
         (distance==best_distance && bin<minimum_bin+poc_index))
        {
         poc_index=i;
         best_distance=distance;
        }
     }
   if(poc_index<0)
      return(false);
   int left=poc_index;
   int right=poc_index;
   double included=volumes[poc_index];
   const double target=VALUE_AREA_FRACTION*total_volume;
   while(included<target && (left>0 || right+1<bin_count))
     {
      const double lower_volume=(left>0 ? volumes[left-1] : -1.0);
      const double upper_volume=(right+1<bin_count ? volumes[right+1] : -1.0);
      if(left>0 && lower_volume>=upper_volume)
        {
         left--;
         included+=volumes[left];
        }
      else
        {
         right++;
         included+=volumes[right];
        }
     }
   profile.valid=true;
   profile.m1_rows=row_count;
   profile.poc_points=(long)(minimum_bin+poc_index)*10;
   profile.val_points=(long)(minimum_bin+left)*10;
   profile.vah_points=(long)(minimum_bin+right)*10;
   profile.total_tick_volume=total_volume;
   return(profile.val_points<=profile.poc_points &&
          profile.poc_points<=profile.vah_points);
  }

bool LoadCachedProfile(const datetime source_utc,PriorDayProfile &profile)
  {
   const int source_date=DateKey(source_utc);
   if(source_date!=g_cached_source_date)
     {
      g_cached_source_date=source_date;
      ZeroMemory(g_cached_profile);
      if(BuildPriorDayProfile(source_utc,g_cached_profile))
         g_valid_profile_dates++;
      else
         g_invalid_profile_dates++;
     }
   profile=g_cached_profile;
   return(profile.valid);
  }

bool BuildSignal(const datetime availability_time,SignalDecision &signal)
  {
   ZeroMemory(signal);
   const datetime availability_utc=ServerToUtc(availability_time);
   if(MinuteOfDay(availability_utc)%15!=0)
      return(false);
   MqlRates source[];
   ArraySetAsSeries(source,false);
   if(CopyRates(_Symbol,PERIOD_M15,1,1,source)!=1 || !ValidRate(source[0]))
     {
      g_invalid_inputs++;
      return(false);
     }
   const datetime source_utc=ServerToUtc(source[0].time);
   g_closed_m15++;
   if((long)(availability_time-source[0].time)!=900 ||
      (long)(availability_utc-source_utc)!=900)
     {
      g_clock_rejects++;
      return(false);
     }
   if(source_utc<DESIGN_FROM || source_utc>=DESIGN_TO || availability_utc>=DESIGN_TO)
      return(false);
   MqlDateTime parts;
   TimeToStruct(source_utc,parts);
   if(parts.day_of_week<2 || parts.day_of_week>5)
      return(false);
   const int minute=MinuteOfDay(source_utc);
   if(minute<SESSION_START_MINUTE_UTC || minute>=SESSION_END_MINUTE_UTC)
      return(false);
   const int key=DateKey(source_utc);
   if(key==g_consumed_utc_date)
      return(false);
   PriorDayProfile profile;
   if(!LoadCachedProfile(source_utc,profile))
      return(false);
   const long open_points=PriceToPoints(source[0].open);
   const long close_points=PriceToPoints(source[0].close);
   if(open_points<=0 || close_points<=0)
     {
      g_invalid_inputs++;
      return(false);
     }
   const bool inside=(close_points>=profile.val_points && close_points<=profile.vah_points);
   const bool long_event=(open_points<profile.val_points && inside);
   const bool short_event=(open_points>profile.vah_points && inside);
   if(long_event==short_event)
      return(false);
   g_consumed_utc_date=key;
   signal.fired=true;
   signal.source_time=source[0].time;
   signal.availability_time=availability_time;
   signal.direction=(long_event ? 1 : -1);
   signal.utc_date_key=key;
   signal.source_open_points=open_points;
   signal.source_close_points=close_points;
   signal.poc_points=profile.poc_points;
   signal.val_points=profile.val_points;
   signal.vah_points=profile.vah_points;
   signal.source_high=source[0].high;
   signal.source_low=source[0].low;
   signal.structural_stop=(long_event ? source[0].low-PROFILE_PIP : source[0].high+PROFILE_PIP);
   g_raw_signals++;
   if(long_event) g_long_signals++; else g_short_signals++;
   PrintFormat("PVPR002_SIGNAL source=%I64d availability=%I64d utc_date=%d direction=%s open_points=%I64d close_points=%I64d poc_points=%I64d val_points=%I64d vah_points=%I64d profile_rows=%d profile_volume=%.0f",
               (long)source[0].time,(long)availability_time,key,
               (long_event ? "LONG" : "SHORT"),open_points,close_points,
               profile.poc_points,profile.val_points,profile.vah_points,
               profile.m1_rows,profile.total_tick_volume);
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
   const double minimum=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN);
   const double maximum=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX);
   const double step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);
   if(!IsFinite(minimum) || !IsFinite(maximum) || !IsFinite(step) ||
      minimum<=0.0 || maximum<minimum || step<=0.0 || volume<minimum)
      return(0.0);
   const double bounded=MathMin(volume,maximum);
   const double units=MathFloor((bounded-minimum+1e-12)/step);
   return(NormalizeDouble(minimum+units*step,VolumeDigits(step)));
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
      PrintFormat("PVPR002_CLOSE_REJECT reason=%s ticket=%I64u retcode=%u",reason,ticket,g_trade.ResultRetcode());
      return(false);
     }
   const uint retcode=g_trade.ResultRetcode();
   if(retcode!=TRADE_RETCODE_DONE && retcode!=TRADE_RETCODE_DONE_PARTIAL)
     {
      g_close_rejects++;
      PrintFormat("PVPR002_CLOSE_REJECT reason=%s ticket=%I64u retcode=%u",reason,ticket,retcode);
      return(false);
     }
   g_closes++;
   g_entry_time=0;
   PrintFormat("PVPR002_CLOSE reason=%s ticket=%I64u retcode=%u",reason,ticket,retcode);
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
   MqlDateTime entry_parts;
   TimeToStruct(entry_utc,entry_parts);
   bool must_close=(DateKey(current_utc)!=DateKey(entry_utc) ||
                    now_parts.hour>=InpSessionFlattenHourUtc ||
                    now_parts.day_of_week==0 || now_parts.day_of_week==6 ||
                    (entry_parts.day_of_week==5 && now_parts.hour>=InpSessionFlattenHourUtc));
   if(!must_close && entry_time>0)
     {
      const int shift=iBarShift(_Symbol,PERIOD_M15,entry_time,false);
      must_close=(shift>=MAX_HOLD_M15_BARS);
     }
   if(must_close && g_last_close_attempt_bar!=current_open)
     {
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
     {
      g_entry_rejects++;
      return(false);
     }
   const double tick_size=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);
   const double symbol_point=SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   if(!IsFinite(tick_size) || tick_size<=0.0 ||
      !IsFinite(symbol_point) || MathAbs(symbol_point-BROKER_POINT)>1e-12)
     {
      g_entry_rejects++;
      return(false);
     }
   const double entry=(signal.direction>0 ? tick.ask : tick.bid);
   const double stop=(signal.direction>0
                      ? FloorToTick(signal.structural_stop,tick_size)
                      : CeilToTick(signal.structural_stop,tick_size));
   if((signal.direction>0 && stop>=entry) || (signal.direction<0 && stop<=entry))
     {
      g_geometry_rejects++;
      return(false);
     }
   const double risk_distance=MathAbs(entry-stop);
   const double raw_target=entry+signal.direction*TARGET_R*risk_distance;
   const double target=(signal.direction>0 ? CeilToTick(raw_target,tick_size) : FloorToTick(raw_target,tick_size));
   const long stops_level=SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL);
   const long freeze_level=SymbolInfoInteger(_Symbol,SYMBOL_TRADE_FREEZE_LEVEL);
   const double minimum_distance=(double)MathMax(MathMax(stops_level,freeze_level),0)*symbol_point;
   if(risk_distance<minimum_distance || MathAbs(target-entry)<minimum_distance)
     {
      g_geometry_rejects++;
      return(false);
     }
   const ENUM_ORDER_TYPE type=(signal.direction>0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL);
   double loss_one_lot=0.0;
   if(!OrderCalcProfit(type,_Symbol,1.0,entry,stop,loss_one_lot) ||
      !IsFinite(loss_one_lot) || loss_one_lot>=0.0)
     {
      g_entry_rejects++;
      return(false);
     }
   const double equity=AccountInfoDouble(ACCOUNT_EQUITY);
   const double volume=NormalizeVolumeDown(equity*(InpRiskPercent/100.0)/MathAbs(loss_one_lot));
   if(volume<=0.0)
     {
      g_entry_rejects++;
      return(false);
     }
   double margin=0.0;
   if(!OrderCalcMargin(type,_Symbol,volume,entry,margin) || !IsFinite(margin) ||
      margin>AccountInfoDouble(ACCOUNT_MARGIN_FREE))
     {
      g_entry_rejects++;
      return(false);
     }
   g_trade.SetExpertMagicNumber(InpMagic);
   g_trade.SetDeviationInPoints(InpDeviationPoints);
   g_trade.SetTypeFillingBySymbol(_Symbol);
   const bool sent=g_trade.PositionOpen(_Symbol,type,volume,entry,stop,target,EXPECTED_VARIANT);
   const uint retcode=g_trade.ResultRetcode();
   if(!sent || (retcode!=TRADE_RETCODE_DONE && retcode!=TRADE_RETCODE_DONE_PARTIAL))
     {
      g_entry_rejects++;
      PrintFormat("PVPR002_ENTRY_REJECT direction=%s volume=%.2f entry=%.5f sl=%.5f tp=%.5f retcode=%u",
                  (signal.direction>0 ? "LONG" : "SHORT"),volume,entry,stop,target,retcode);
      return(false);
     }
   g_entries++;
   g_entry_time=signal.availability_time;
   PrintFormat("PVPR002_ENTRY direction=%s volume=%.2f entry=%.5f sl=%.5f tp=%.5f risk_pct=%.3f retcode=%u",
               (signal.direction>0 ? "LONG" : "SHORT"),volume,entry,stop,target,InpRiskPercent,retcode);
   return(true);
  }

int OnInit()
  {
   if(!InpResearchAutoMode || InpEnableTelemetry || _Symbol!=EXPECTED_SYMBOL || _Period!=PERIOD_M15 ||
      InpHypothesisId!=EXPECTED_HYPOTHESIS || InpVariantTag!=EXPECTED_VARIANT ||
      InpMagic!=5604602 || MathAbs(InpRiskPercent-0.10)>1e-12 ||
      MathAbs(InpMaxDailyLossPct-3.5)>1e-12 || MathAbs(InpMaxAccountDrawdownPct-8.0)>1e-12 ||
      InpDeviationPoints!=20 || InpSessionFlattenHourUtc!=20 ||
      MathAbs(SymbolInfoDouble(_Symbol,SYMBOL_POINT)-BROKER_POINT)>1e-12)
      return(INIT_PARAMETERS_INCORRECT);
   if(!EmitD0SeriesProof())
     {
      g_runtime_failed=true;
      return(INIT_FAILED);
     }
   g_trade.SetExpertMagicNumber(InpMagic);
   g_trade.SetDeviationInPoints(InpDeviationPoints);
   g_trade.SetTypeFillingBySymbol(_Symbol);
   const double equity=AccountInfoDouble(ACCOUNT_EQUITY);
   g_peak_equity=equity;
   g_daily_start_equity=equity;
   g_daily_utc_key=DateKey(ServerToUtc(TimeCurrent()));
   if(!CurrentBarOpen(g_last_bar_open) || g_last_bar_open<=0)
     {
      g_runtime_failed=true;
      return(INIT_FAILED);
     }
   PrintFormat("PVPR002_INIT ea=%s hypothesis=%s variant=%s symbol=%s timeframe=M15",
               EA_NAME,InpHypothesisId,InpVariantTag,_Symbol);
   return(INIT_SUCCEEDED);
  }

void OnDeinit(const int reason)
  {
   ulong ticket=0;
   const bool open_position=OwnedPosition(ticket);
   PrintFormat("PVPR002_SUMMARY reason=%d runtime_failed=%s closed_m15=%I64d valid_profiles=%I64d invalid_profiles=%I64d raw=%I64d long=%I64d short=%I64d entries=%I64d entry_rejects=%I64d geometry_rejects=%I64d close_attempts=%I64d close_rejects=%I64d closes=%I64d clock_rejects=%I64d invalid_inputs=%I64d risk_lock_skips=%I64d open_position=%s",
               reason,(g_runtime_failed ? "true" : "false"),g_closed_m15,
               g_valid_profile_dates,g_invalid_profile_dates,g_raw_signals,
               g_long_signals,g_short_signals,g_entries,g_entry_rejects,
               g_geometry_rejects,g_close_attempts,g_close_rejects,g_closes,
               g_clock_rejects,g_invalid_inputs,g_risk_lock_skips,
               (open_position ? "true" : "false"));
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
