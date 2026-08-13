//+------------------------------------------------------------------+
//| EA_NYOpeningDriveContinuation.mq5                               |
//| HYP-NYOD-XAUUSD-M15-001: New York opening-drive continuation   |
//+------------------------------------------------------------------+
#property strict
#property version   "1.00"
#property description "Untuned XAUUSD M15 New York opening-drive continuation"

#include <Trade/Trade.mqh>

input group "--- Frozen research authority ---"
input bool   InpResearchAutoMode=false;
input bool   InpEnableTelemetry=false;
input string InpHypothesisId="HYP-NYOD-XAUUSD-M15-001";
input string InpVariantTag="NY0815_DRIVE_PRIOR2H_BREAK_CONTINUATION";

input group "--- Frozen execution and risk ---"
input long   InpMagic=5604301;
input double InpRiskPercent=0.25;
input double InpMaxDailyLossPct=3.5;
input double InpMaxAccountDrawdownPct=8.0;
input int    InpDeviationPoints=20;
input int    InpFridayFlattenHourUtc=20;

const string EA_NAME="EA_NYOpeningDriveContinuation";
const string EXPECTED_HYPOTHESIS="HYP-NYOD-XAUUSD-M15-001";
const string EXPECTED_VARIANT="NY0815_DRIVE_PRIOR2H_BREAK_CONTINUATION";
const string EXPECTED_SYMBOL="XAUUSD";
const int ATR_PERIOD=14;
const int PRIOR_RANGE_BARS=8;
const int REQUIRED_RATES=10;
const double MIN_RANGE_ATR=1.00;
const double MIN_BODY_FRACTION=0.60;
const double MIN_CLOSE_LOCATION=0.75;
const double STOP_BUFFER_ATR=0.15;
const double TARGET_R=1.50;
const int MAX_HOLD_BARS=6;
const datetime DESIGN_FROM=D'2018.01.01 00:00';
const datetime DESIGN_TO=D'2023.01.01 00:00';

struct SignalDecision
  {
   bool fired;
   datetime decision_time;
   datetime availability_time;
   int direction;
   int ny_date_key;
   double close;
   double prior_high;
   double prior_low;
   double atr;
   double structural_stop;
  };

CTrade g_trade;
int g_atr_handle=INVALID_HANDLE;
datetime g_last_bar_open=0;
datetime g_last_decision_time=0;
datetime g_entry_time=0;
int g_consumed_ny_date=0;
int g_daily_utc_key=0;
double g_daily_start_equity=0.0;
double g_peak_equity=0.0;
bool g_daily_locked=false;
bool g_drawdown_locked=false;
bool g_runtime_failed=false;
long g_closed_bars=0;
long g_raw_signals=0;
long g_long_signals=0;
long g_short_signals=0;
long g_entries=0;
long g_entry_rejects=0;
long g_closes=0;
long g_clock_rejects=0;
long g_invalid_inputs=0;

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

int SundayOnOrAfter(const int year,const int month,const int day)
  {
   MqlDateTime p;
   TimeToStruct(MakeTime(year,month,day,0),p);
   return(day+((7-p.day_of_week)%7));
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
   const int hours=(IsBrokerDstServerTime(server_time) ? 3 : 2);
   return(server_time-hours*3600);
  }

bool IsNewYorkDstUtc(const datetime utc_time)
  {
   MqlDateTime p;
   TimeToStruct(utc_time,p);
   const int second_sunday=SundayOnOrAfter(p.year,3,1)+7;
   const int first_sunday=SundayOnOrAfter(p.year,11,1);
   const datetime start=MakeTime(p.year,3,second_sunday,7);
   const datetime finish=MakeTime(p.year,11,first_sunday,6);
   return(utc_time>=start && utc_time<finish);
  }

datetime UtcToNewYorkLocal(const datetime utc_time)
  {
   return(utc_time-(IsNewYorkDstUtc(utc_time) ? 4 : 5)*3600);
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
          bar.high>=MathMax(bar.open,bar.close) &&
          bar.low<=MathMin(bar.open,bar.close) && bar.high>=bar.low);
  }

double TrueRange(const MqlRates &bar,const double previous_close)
  {
   return(MathMax(bar.high-bar.low,
                  MathMax(MathAbs(bar.high-previous_close),
                          MathAbs(bar.low-previous_close))));
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

bool LoadClosedRates(MqlRates &rates[])
  {
   ArrayResize(rates,REQUIRED_RATES);
   if(CopyRates(_Symbol,PERIOD_M15,1,REQUIRED_RATES,rates)!=REQUIRED_RATES)
      return(false);
   for(int i=0;i<REQUIRED_RATES;i++)
      if(!ValidRate(rates[i]))
         return(false);
   return(true);
  }

bool ReadPriorAtr(double &atr)
  {
   atr=EMPTY_VALUE;
   if(g_atr_handle==INVALID_HANDLE)
      return(false);
   double values[];
   if(CopyBuffer(g_atr_handle,0,2,1,values)!=1 || !IsFinite(values[0]) || values[0]<=0.0)
      return(false);
   atr=values[0];
   return(true);
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
   const int drive=REQUIRED_RATES-1;
   const datetime decision_time=rates[drive].time;
   if(decision_time<=0 || decision_time==g_last_decision_time)
      return(false);
   g_last_decision_time=decision_time;
   g_closed_bars++;

   if(decision_time<DESIGN_FROM || decision_time>=DESIGN_TO || availability_time>=DESIGN_TO)
      return(false);
   if((long)(availability_time-decision_time)!=900)
     {
      g_clock_rejects++;
      return(false);
     }

   const datetime decision_utc=ServerToUtc(decision_time);
   const datetime availability_utc=ServerToUtc(availability_time);
   const datetime ny_decision=UtcToNewYorkLocal(decision_utc);
   const datetime ny_availability=UtcToNewYorkLocal(availability_utc);
   MqlDateTime d,a;
   TimeToStruct(ny_decision,d);
   TimeToStruct(ny_availability,a);
   if(d.hour!=8 || d.min!=15 || a.hour!=8 || a.min!=30 || DateKey(ny_decision)!=DateKey(ny_availability))
      return(false);
   if(d.day_of_week==0 || d.day_of_week==6)
      return(false);

   double atr=0.0;
   if(!ReadPriorAtr(atr))
     {
      g_invalid_inputs++;
      return(false);
     }
   const double drive_range=TrueRange(rates[drive],rates[drive-1].close);
   const double bar_range=rates[drive].high-rates[drive].low;
   if(!IsFinite(drive_range) || !IsFinite(bar_range) ||
      drive_range<=0.0 || bar_range<=0.0)
      return(false);
   const double body=MathAbs(rates[drive].close-rates[drive].open);
   const double long_location=(rates[drive].close-rates[drive].low)/bar_range;
   const double short_location=(rates[drive].high-rates[drive].close)/bar_range;

   double prior_high=rates[drive-PRIOR_RANGE_BARS].high;
   double prior_low=rates[drive-PRIOR_RANGE_BARS].low;
   for(int i=drive-PRIOR_RANGE_BARS+1;i<drive;i++)
     {
      prior_high=MathMax(prior_high,rates[i].high);
      prior_low=MathMin(prior_low,rates[i].low);
     }

   const bool common=(drive_range>=MIN_RANGE_ATR*atr &&
                      body>=MIN_BODY_FRACTION*bar_range);
   const bool long_signal=(common && rates[drive].close>rates[drive].open &&
                           long_location>=MIN_CLOSE_LOCATION &&
                           rates[drive].close>prior_high);
   const bool short_signal=(common && rates[drive].close<rates[drive].open &&
                            short_location>=MIN_CLOSE_LOCATION &&
                            rates[drive].close<prior_low);
   if(long_signal==short_signal)
      return(false);

   const int ny_key=DateKey(ny_decision);
   if(ny_key==g_consumed_ny_date)
      return(false);
   g_consumed_ny_date=ny_key;
   const int direction=(long_signal ? 1 : -1);
   signal.fired=true;
   signal.decision_time=decision_time;
   signal.availability_time=availability_time;
   signal.direction=direction;
   signal.ny_date_key=ny_key;
   signal.close=rates[drive].close;
   signal.prior_high=prior_high;
   signal.prior_low=prior_low;
   signal.atr=atr;
   signal.structural_stop=(direction>0
                           ? rates[drive].low-STOP_BUFFER_ATR*atr
                           : rates[drive].high+STOP_BUFFER_ATR*atr);
   g_raw_signals++;
   if(direction>0) g_long_signals++; else g_short_signals++;
   PrintFormat("NYOD001_SIGNAL decision=%I64d availability=%I64d ny_date=%d direction=%s close=%.5f prior_high=%.5f prior_low=%.5f atr=%.5f stop=%.5f",
               (long)decision_time,(long)availability_time,ny_key,
               (direction>0 ? "LONG" : "SHORT"),signal.close,
               prior_high,prior_low,atr,signal.structural_stop);
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
   if(!IsFinite(vmin) || !IsFinite(vmax) || !IsFinite(step) || step<=0.0 || volume<vmin)
      return(0.0);
   const double bounded=MathMin(volume,vmax);
   const double units=MathFloor((bounded-vmin+1e-12)/step);
   const double normalized=vmin+units*step;
   return(NormalizeDouble(normalized,VolumeDigits(step)));
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

bool FridayBlocked(const datetime server_now)
  {
   MqlDateTime p;
   TimeToStruct(ServerToUtc(server_now),p);
   return(p.day_of_week==5);
  }

bool FridayFlattenDue(const datetime server_now)
  {
   MqlDateTime p;
   TimeToStruct(ServerToUtc(server_now),p);
   return(p.day_of_week==5 && p.hour>=InpFridayFlattenHourUtc);
  }

bool CloseOwned(const string reason)
  {
   ulong ticket=0;
   if(!OwnedPosition(ticket))
      return(true);
   g_trade.SetDeviationInPoints(InpDeviationPoints);
   if(!g_trade.PositionClose(ticket,InpDeviationPoints))
     {
      PrintFormat("NYOD001_CLOSE_REJECT reason=%s ticket=%I64u retcode=%u",reason,ticket,g_trade.ResultRetcode());
      return(false);
     }
   const uint retcode=g_trade.ResultRetcode();
   if(retcode!=TRADE_RETCODE_DONE && retcode!=TRADE_RETCODE_DONE_PARTIAL)
      return(false);
   g_closes++;
   g_entry_time=0;
   PrintFormat("NYOD001_CLOSE reason=%s ticket=%I64u retcode=%u",reason,ticket,retcode);
   return(true);
  }

void ManagePosition(const datetime current_open)
  {
   ulong ticket=0;
   if(!OwnedPosition(ticket))
      return;
   if(FridayFlattenDue(current_open))
     {
      CloseOwned("FRIDAY_FLATTEN");
      return;
     }
   datetime entry_time=g_entry_time;
   if(entry_time<=0 && PositionSelectByTicket(ticket))
      entry_time=(datetime)PositionGetInteger(POSITION_TIME);
   if(entry_time>0)
     {
      const int shift=iBarShift(_Symbol,PERIOD_M15,entry_time,false);
      if(shift>=MAX_HOLD_BARS)
         CloseOwned("TIME_EXIT_6_BARS");
     }
  }

bool SubmitEntry(const SignalDecision &signal)
  {
   if(!signal.fired || g_daily_locked || g_drawdown_locked || FridayBlocked(signal.availability_time) || AnySymbolExposure())
      return(false);
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick) || !IsFinite(tick.ask) || !IsFinite(tick.bid) || tick.ask<=tick.bid)
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
   const double tp=(signal.direction>0
                    ? FloorToTick(raw_target,tick_size)
                    : CeilToTick(raw_target,tick_size));
   const long stops_level=SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL);
   const double minimum_distance=(double)MathMax(stops_level,0)*point;
   if(risk_distance<minimum_distance || MathAbs(tp-entry)<minimum_distance)
      return(false);

   double loss_one_lot=0.0;
   const ENUM_ORDER_TYPE type=(signal.direction>0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL);
   if(!OrderCalcProfit(type,_Symbol,1.0,entry,sl,loss_one_lot) || !IsFinite(loss_one_lot) || loss_one_lot>=0.0)
      return(false);
   const double equity=AccountInfoDouble(ACCOUNT_EQUITY);
   const double volume=NormalizeVolumeDown(equity*(InpRiskPercent/100.0)/MathAbs(loss_one_lot));
   if(volume<=0.0)
      return(false);
   double margin=0.0;
   if(!OrderCalcMargin(type,_Symbol,volume,entry,margin) || !IsFinite(margin) || margin>AccountInfoDouble(ACCOUNT_MARGIN_FREE))
      return(false);

   g_trade.SetExpertMagicNumber(InpMagic);
   g_trade.SetDeviationInPoints(InpDeviationPoints);
   g_trade.SetTypeFillingBySymbol(_Symbol);
   const bool sent=g_trade.PositionOpen(_Symbol,type,volume,entry,sl,tp,EXPECTED_VARIANT);
   const uint retcode=g_trade.ResultRetcode();
   if(!sent || (retcode!=TRADE_RETCODE_DONE && retcode!=TRADE_RETCODE_DONE_PARTIAL))
     {
      g_entry_rejects++;
      PrintFormat("NYOD001_ENTRY_REJECT direction=%s volume=%.2f entry=%.5f sl=%.5f tp=%.5f retcode=%u",
                  (signal.direction>0 ? "LONG" : "SHORT"),volume,entry,sl,tp,retcode);
      return(false);
     }
   g_entries++;
   g_entry_time=signal.availability_time;
   PrintFormat("NYOD001_ENTRY direction=%s volume=%.2f entry=%.5f sl=%.5f tp=%.5f risk_pct=%.3f retcode=%u",
               (signal.direction>0 ? "LONG" : "SHORT"),volume,entry,sl,tp,InpRiskPercent,retcode);
   return(true);
  }

int OnInit()
  {
   if(!InpResearchAutoMode || InpEnableTelemetry || _Symbol!=EXPECTED_SYMBOL || _Period!=PERIOD_M15 ||
      InpHypothesisId!=EXPECTED_HYPOTHESIS || InpVariantTag!=EXPECTED_VARIANT ||
      InpMagic<=0 || InpRiskPercent<=0.0 || InpRiskPercent>1.0 ||
      InpMaxDailyLossPct<=0.0 || InpMaxAccountDrawdownPct<=0.0)
      return(INIT_PARAMETERS_INCORRECT);
   if(!EmitD0SeriesProof())
      return(INIT_FAILED);
   g_atr_handle=iATR(_Symbol,PERIOD_M15,ATR_PERIOD);
   if(g_atr_handle==INVALID_HANDLE)
      return(INIT_FAILED);
   g_trade.SetExpertMagicNumber(InpMagic);
   g_trade.SetDeviationInPoints(InpDeviationPoints);
   g_trade.SetTypeFillingBySymbol(_Symbol);
   const double equity=AccountInfoDouble(ACCOUNT_EQUITY);
   g_peak_equity=equity;
   g_daily_start_equity=equity;
   g_daily_utc_key=DateKey(ServerToUtc(TimeCurrent()));
   PrintFormat("NYOD001_INIT ea=%s hypothesis=%s variant=%s symbol=%s timeframe=M15",
               EA_NAME,InpHypothesisId,InpVariantTag,_Symbol);
   return(INIT_SUCCEEDED);
  }

void OnDeinit(const int reason)
  {
   if(g_atr_handle!=INVALID_HANDLE)
      IndicatorRelease(g_atr_handle);
   PrintFormat("NYOD001_SUMMARY reason=%d runtime_failed=%s closed=%I64d raw=%I64d long=%I64d short=%I64d entries=%I64d rejects=%I64d closes=%I64d clock_rejects=%I64d invalid=%I64d",
               reason,(g_runtime_failed ? "true" : "false"),g_closed_bars,
               g_raw_signals,g_long_signals,g_short_signals,g_entries,
               g_entry_rejects,g_closes,g_clock_rejects,g_invalid_inputs);
  }

void OnTick()
  {
   datetime current_open=0;
   if(!CurrentBarOpen(current_open) || current_open<=0)
      return;
   RefreshRiskLocks(current_open);
   if(FridayFlattenDue(current_open))
      CloseOwned("FRIDAY_FLATTEN_TICK");
   if(current_open==g_last_bar_open)
      return;
   g_last_bar_open=current_open;
   ManagePosition(current_open);
   if(AnySymbolExposure())
      return;
   SignalDecision signal;
   if(BuildSignal(current_open,signal) && signal.fired)
      SubmitEntry(signal);
  }
