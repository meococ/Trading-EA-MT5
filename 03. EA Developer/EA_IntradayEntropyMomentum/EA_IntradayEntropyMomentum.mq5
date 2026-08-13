//+------------------------------------------------------------------+
//| EA_IntradayEntropyMomentum.mq5                               |
//| HYP-IDEM-XAUUSD-M5-002: intraday entropy momentum  |
//+------------------------------------------------------------------+
#property strict
#property version   "1.00"
#property description "Untuned XAUUSD M5 intraday entropy momentum"

#include <Trade/Trade.mqh>

input group "--- Frozen research authority ---"
input bool   InpResearchAutoMode=false;
input bool   InpEnableTelemetry=false;
input string InpHypothesisId="HYP-IDEM-XAUUSD-M5-002";
input string InpVariantTag="INTRADAY_ENTROPY_MOMENTUM";

input group "--- Frozen execution and risk ---"
input long   InpMagic=5604406;
input double InpRiskPercent=0.10;
input double InpMaxDailyLossPct=3.5;
input double InpMaxAccountDrawdownPct=8.0;
input int    InpDeviationPoints=20;
input int    InpSessionFlattenHourUtc=20;

const string EA_NAME="EA_IntradayEntropyMomentum";
const string EXPECTED_HYPOTHESIS="HYP-IDEM-XAUUSD-M5-002";
const string EXPECTED_VARIANT="INTRADAY_ENTROPY_MOMENTUM";
const string EXPECTED_SYMBOL="XAUUSD";
const int SESSION_ROWS=192;
const int REFERENCE_DAYS=20;
const int HISTORY_BARS=15000;
const int ATR_PERIOD=14;
const int STOP_LOOKBACK_BARS=12;
const double STOP_BUFFER_ATR=0.20;
const double TARGET_R=1.50;
const datetime DESIGN_FROM=D'2018.01.01 00:00';
const datetime DESIGN_TO=D'2023.01.01 00:00';

struct SessionSummary
  {
   int date_key;
   datetime decision_server;
   double entropy;
   double session_return;
   int positive_returns;
   int negative_returns;
  };

struct SignalDecision
  {
   bool fired;
   datetime decision_time;
   datetime availability_time;
   int direction;
   int utc_date_key;
   double entropy;
   double prior20_entropy_median;
   double session_return;
   double atr;
   double structural_stop;
  };

CTrade g_trade;
int g_atr_handle=INVALID_HANDLE;
datetime g_last_bar_open=0;
datetime g_last_decision_time=0;
datetime g_entry_time=0;
datetime g_last_close_attempt_bar=0;
int g_consumed_utc_date=0;
int g_daily_utc_key=0;
double g_daily_start_equity=0.0;
double g_peak_equity=0.0;
bool g_daily_locked=false;
bool g_drawdown_locked=false;
bool g_runtime_failed=false;
long g_closed_bars=0;
long g_complete_sessions=0;
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
   return(copied>=SESSION_ROWS);
  }

void AppendCompleteSession(SessionSummary &sessions[],
                           const int date_key,
                           const datetime decision_server,
                           const int count,
                           const bool broken,
                           const datetime first_utc,
                           const datetime last_utc,
                           const double &closes[])
  {
   if(date_key<=0 || broken || count!=SESSION_ROWS || ArraySize(closes)!=SESSION_ROWS)
      return;
   MqlDateTime first_parts,last_parts;
   TimeToStruct(first_utc,first_parts);
   TimeToStruct(last_utc,last_parts);
   if(first_parts.hour!=0 || first_parts.min!=0 ||
      last_parts.hour!=15 || last_parts.min!=55 ||
      (long)(last_utc-first_utc)!=(SESSION_ROWS-1)*300)
      return;

   int positive=0;
   int negative=0;
   for(int i=0;i<SESSION_ROWS;i++)
     {
      if(!IsFinite(closes[i]) || closes[i]<=0.0)
         return;
      if(i>0)
        {
         const double value=MathLog(closes[i]/closes[i-1]);
         if(!IsFinite(value))
            return;
         if(value>0.0) positive++;
         else if(value<0.0) negative++;
        }
     }
   const int nonzero=positive+negative;
   if(nonzero<=0)
      return;
   const double p=(double)positive/(double)nonzero;
   double entropy=0.0;
   if(p>0.0 && p<1.0)
      entropy=-p*MathLog(p)-(1.0-p)*MathLog(1.0-p);
   const double session_return=MathLog(closes[SESSION_ROWS-1]/closes[0]);
   if(!IsFinite(entropy) || !IsFinite(session_return))
      return;

   const int size=ArraySize(sessions);
   ArrayResize(sessions,size+1);
   sessions[size].date_key=date_key;
   sessions[size].decision_server=decision_server;
   sessions[size].entropy=entropy;
   sessions[size].session_return=session_return;
   sessions[size].positive_returns=positive;
   sessions[size].negative_returns=negative;
  }

bool BuildSessionHistory(const MqlRates &rates[],SessionSummary &sessions[])
  {
   ArrayResize(sessions,0);
   int current_key=0;
   int count=0;
   bool broken=false;
   datetime first_utc=0;
   datetime last_utc=0;
   datetime decision_server=0;
   double closes[];
   ArrayResize(closes,SESSION_ROWS);

   const int total=ArraySize(rates);
   for(int i=0;i<total;i++)
     {
      const datetime utc=ServerToUtc(rates[i].time);
      if(utc<DESIGN_FROM || utc>=DESIGN_TO)
         continue;
      MqlDateTime p;
      TimeToStruct(utc,p);
      if(p.day_of_week==0 || p.day_of_week==6 || p.hour>=16)
         continue;
      const int key=DateKey(utc);
      if(key!=current_key)
        {
         AppendCompleteSession(sessions,current_key,decision_server,count,broken,
                               first_utc,last_utc,closes);
         current_key=key;
         count=0;
         broken=false;
         first_utc=0;
         last_utc=0;
         decision_server=0;
         ArrayInitialize(closes,0.0);
        }
      if(!ValidRate(rates[i]))
         broken=true;
      if(count==0)
        {
         first_utc=utc;
         if(p.hour!=0 || p.min!=0)
            broken=true;
        }
      else if((long)(utc-last_utc)!=300)
         broken=true;
      if(count<SESSION_ROWS)
         closes[count]=rates[i].close;
      else
         broken=true;
      count++;
      last_utc=utc;
      decision_server=rates[i].time;
     }
   AppendCompleteSession(sessions,current_key,decision_server,count,broken,
                         first_utc,last_utc,closes);
   return(ArraySize(sessions)>0);
  }

bool Prior20EntropyMedian(const SessionSummary &sessions[],const int current,double &median)
  {
   median=EMPTY_VALUE;
   if(current<REFERENCE_DAYS)
      return(false);
   double values[];
   ArrayResize(values,REFERENCE_DAYS);
   for(int i=0;i<REFERENCE_DAYS;i++)
     {
      values[i]=sessions[current-REFERENCE_DAYS+i].entropy;
      if(!IsFinite(values[i]) || values[i]<0.0)
         return(false);
     }
   ArraySort(values);
   median=(values[REFERENCE_DAYS/2-1]+values[REFERENCE_DAYS/2])/2.0;
   return(IsFinite(median));
  }

bool ReadClosedAtr(double &atr)
  {
   atr=EMPTY_VALUE;
   if(g_atr_handle==INVALID_HANDLE)
      return(false);
   double value[];
   if(CopyBuffer(g_atr_handle,0,1,1,value)!=1 || !IsFinite(value[0]) || value[0]<=0.0)
      return(false);
   atr=value[0];
   return(true);
  }

bool StructuralStop(const MqlRates &rates[],const int direction,const double atr,double &stop)
  {
   stop=EMPTY_VALUE;
   const int total=ArraySize(rates);
   if(total<STOP_LOOKBACK_BARS || !IsFinite(atr) || atr<=0.0)
      return(false);
   const int first=total-STOP_LOOKBACK_BARS;
   double extreme=(direction>0 ? rates[first].low : rates[first].high);
   datetime previous_utc=ServerToUtc(rates[first].time);
   if(!ValidRate(rates[first]))
      return(false);
   for(int i=first+1;i<total;i++)
     {
      const datetime current_utc=ServerToUtc(rates[i].time);
      if(!ValidRate(rates[i]) || (long)(current_utc-previous_utc)!=300)
         return(false);
      extreme=(direction>0 ? MathMin(extreme,rates[i].low) : MathMax(extreme,rates[i].high));
      previous_utc=current_utc;
     }
   stop=(direction>0 ? extreme-STOP_BUFFER_ATR*atr : extreme+STOP_BUFFER_ATR*atr);
   return(IsFinite(stop) && stop>0.0);
  }

bool BuildSignal(const datetime availability_time,SignalDecision &signal)
  {
   ZeroMemory(signal);
   const datetime availability_utc=ServerToUtc(availability_time);
   MqlDateTime available;
   TimeToStruct(availability_utc,available);
   if(available.hour!=16 || available.min!=0 || available.day_of_week==0 || available.day_of_week==6)
      return(false);
   if(availability_utc<DESIGN_FROM || availability_utc>=DESIGN_TO)
      return(false);

   MqlRates rates[];
   if(!LoadClosedRates(rates))
     {
      g_invalid_inputs++;
      return(false);
     }
   const int last=ArraySize(rates)-1;
   const datetime decision_time=rates[last].time;
   const datetime decision_utc=ServerToUtc(decision_time);
   if(decision_time<=0 || decision_time==g_last_decision_time)
      return(false);
   g_last_decision_time=decision_time;
   g_closed_bars++;
   MqlDateTime decision;
   TimeToStruct(decision_utc,decision);
   if((long)(availability_time-decision_time)!=300 ||
      (long)(availability_utc-decision_utc)!=300 ||
      decision.hour!=15 || decision.min!=55 ||
      DateKey(decision_utc)!=DateKey(availability_utc))
     {
      g_clock_rejects++;
      return(false);
     }

   SessionSummary sessions[];
   if(!BuildSessionHistory(rates,sessions))
     {
      g_invalid_inputs++;
      return(false);
     }
   const int current=ArraySize(sessions)-1;
   const SessionSummary today=sessions[current];
   if(today.date_key!=DateKey(availability_utc) || today.decision_server!=decision_time)
     {
      g_invalid_inputs++;
      return(false);
     }
   g_complete_sessions++;
   double reference_entropy=0.0;
   if(!Prior20EntropyMedian(sessions,current,reference_entropy) ||
      today.entropy>=reference_entropy || today.session_return==0.0)
      return(false);
   const int direction=(today.session_return>0.0 ? 1 : -1);
   const int key=today.date_key;
   if(key==g_consumed_utc_date)
      return(false);
   g_consumed_utc_date=key;
   double atr=0.0;
   double stop=0.0;
   if(!ReadClosedAtr(atr) || !StructuralStop(rates,direction,atr,stop))
     {
      g_invalid_inputs++;
      return(false);
     }

   signal.fired=true;
   signal.decision_time=decision_time;
   signal.availability_time=availability_time;
   signal.direction=direction;
   signal.utc_date_key=key;
   signal.entropy=today.entropy;
   signal.prior20_entropy_median=reference_entropy;
   signal.session_return=today.session_return;
   signal.atr=atr;
   signal.structural_stop=stop;
   g_raw_signals++;
   if(direction>0) g_long_signals++; else g_short_signals++;
   PrintFormat("IDEM002_SIGNAL decision=%I64d availability=%I64d utc_date=%d direction=%s entropy=%.10f prior20_median=%.10f session_return=%.10f positive=%d negative=%d atr=%.5f stop=%.5f",
               (long)decision_time,(long)availability_time,key,
               (direction>0 ? "LONG" : "SHORT"),today.entropy,reference_entropy,
               today.session_return,today.positive_returns,today.negative_returns,atr,stop);
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
      PrintFormat("IDEM002_CLOSE_REJECT reason=%s ticket=%I64u retcode=%u",reason,ticket,g_trade.ResultRetcode());
      return(false);
     }
   const uint retcode=g_trade.ResultRetcode();
   if(retcode!=TRADE_RETCODE_DONE && retcode!=TRADE_RETCODE_DONE_PARTIAL)
     {
      g_close_rejects++;
      PrintFormat("IDEM002_CLOSE_REJECT reason=%s ticket=%I64u retcode=%u",reason,ticket,retcode);
      return(false);
     }
   g_closes++;
   g_entry_time=0;
   PrintFormat("IDEM002_CLOSE reason=%s ticket=%I64u retcode=%u",reason,ticket,retcode);
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
   if(DateKey(current_utc)!=DateKey(entry_utc) || now_parts.hour>=InpSessionFlattenHourUtc)
     {
      // Retry a required flatten once per native M5 bar. This preserves the
      // exit intent while preventing a closed market from flooding the tester
      // journal on every synthetic tick.
      if(g_last_close_attempt_bar==current_open)
         return;
      g_last_close_attempt_bar=current_open;
      CloseOwned("UTC_2000_OR_DAY_ROLL");
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
      PrintFormat("IDEM002_ENTRY_REJECT direction=%s volume=%.2f entry=%.5f sl=%.5f tp=%.5f retcode=%u",
                  (signal.direction>0 ? "LONG" : "SHORT"),volume,entry,sl,tp,retcode);
      return(false);
     }
   g_entries++;
   g_entry_time=signal.availability_time;
   PrintFormat("IDEM002_ENTRY direction=%s volume=%.2f entry=%.5f sl=%.5f tp=%.5f risk_pct=%.3f retcode=%u",
               (signal.direction>0 ? "LONG" : "SHORT"),volume,entry,sl,tp,InpRiskPercent,retcode);
   return(true);
  }

int OnInit()
  {
   if(!InpResearchAutoMode || InpEnableTelemetry || _Symbol!=EXPECTED_SYMBOL || _Period!=PERIOD_M5 ||
      InpHypothesisId!=EXPECTED_HYPOTHESIS || InpVariantTag!=EXPECTED_VARIANT ||
      InpMagic!=5604406 || MathAbs(InpRiskPercent-0.10)>1e-12 ||
      MathAbs(InpMaxDailyLossPct-3.5)>1e-12 || MathAbs(InpMaxAccountDrawdownPct-8.0)>1e-12 ||
      InpDeviationPoints!=20 || InpSessionFlattenHourUtc!=20)
      return(INIT_PARAMETERS_INCORRECT);
   if(!EmitD0SeriesProof())
      return(INIT_FAILED);
   g_atr_handle=iATR(_Symbol,PERIOD_M5,ATR_PERIOD);
   if(g_atr_handle==INVALID_HANDLE)
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
   PrintFormat("IDEM002_INIT ea=%s hypothesis=%s variant=%s symbol=%s timeframe=M5",
               EA_NAME,InpHypothesisId,InpVariantTag,_Symbol);
   return(INIT_SUCCEEDED);
  }

void OnDeinit(const int reason)
  {
   if(g_atr_handle!=INVALID_HANDLE)
      IndicatorRelease(g_atr_handle);
   PrintFormat("IDEM002_SUMMARY reason=%d runtime_failed=%s closed=%I64d sessions=%I64d raw=%I64d long=%I64d short=%I64d entries=%I64d rejects=%I64d close_attempts=%I64d close_rejects=%I64d closes=%I64d clock_rejects=%I64d invalid=%I64d risk_lock_skips=%I64d",
               reason,(g_runtime_failed ? "true" : "false"),g_closed_bars,
               g_complete_sessions,g_raw_signals,g_long_signals,g_short_signals,
               g_entries,g_entry_rejects,g_close_attempts,g_close_rejects,g_closes,g_clock_rejects,g_invalid_inputs,
               g_risk_lock_skips);
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

