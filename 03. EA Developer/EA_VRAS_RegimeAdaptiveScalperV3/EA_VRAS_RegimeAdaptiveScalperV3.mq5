#property copyright "AlphaFactory research"
#property version   "1.02"
#property strict
#property description "VRAS EURUSD M5 seven-gap implementation; diagnostic research only"
#property description "Closed-bar Session VWAP/SD, ADX hysteresis, confirmed AVWAP, cost-aware execution"

#include "NewsCalendar2019_2022.mqh"

enum ENUM_VRAS_REGIME
  {
   REGIME_RANGE=0,
   REGIME_TREND=1
  };

enum ENUM_VRAS_VOLUME_MODE
  {
   VRAS_WEIGHT_TICK=0,
   VRAS_WEIGHT_EQUAL=1
  };

enum ENUM_VRAS_ANCHOR_MODE
  {
   ANCHOR_LONDON_OPEN=0,
   ANCHOR_UTC_MIDNIGHT=1,
   ANCHOR_BROKER_DAILY=2
  };

enum ENUM_VRAS_SIGNAL
  {
   SIGNAL_NONE=0,
   SIGNAL_RANGE_LONG=1,
   SIGNAL_RANGE_SHORT=2,
   SIGNAL_TREND_LONG=3,
   SIGNAL_TREND_SHORT=4
  };

input bool                  InpResearchAutoMode=false;
input bool                  InpEnableTelemetry=true;
input string                InpHypothesisId="HYP-VRAS-EURUSD-M5-003";
input string                InpVariantTag="PRIMARY_TICK_LONDON";
input long                  InpMagic=5600743;
input ENUM_VRAS_VOLUME_MODE InpVolumeMode=VRAS_WEIGHT_TICK;
input ENUM_VRAS_ANCHOR_MODE InpAnchorMode=ANCHOR_LONDON_OPEN;

input int                   InpAdxPeriod=14;
input double                InpAdxEnter=25.0;
input double                InpAdxExit=19.0;
input int                   InpMinRegimeDwellBars=6;
input int                   InpAtrPeriod=14;
input int                   InpRsiPeriod=14;
input double                InpRsiLongFloor=25.0;
input double                InpRsiShortCeiling=75.0;

input int                   InpWarmupBars=15;
input double                InpSdFloorAtr=0.30;
input double                InpBandMultiplier=2.0;
input double                InpRangeStopAtr=0.30;
input double                InpRangeStopSd=2.50;
input double                InpTrendStopAtr=0.40;
input double                InpTrendTargetR=1.80;
input int                   InpAnchorLookbackBars=60;
input bool                  InpUseM15Bias=true;

input double                InpRiskPercent=0.25;
input double                InpMaxSpreadPips=1.20;
input double                InpCommissionPips=0.70;
input double                InpSlippageOneWayPips=0.40;
input double                InpCostDistanceMultiple=8.0;
input int                   InpMaxTradesPerDay=3;
input double                InpDailyLossPct=1.50;
input double                InpMaxAccountDrawdownPct=6.00;
input int                   InpMaxHoldBars=20;
input bool                  InpRequireNewsGuard=true;
input int                   InpNewsBlackoutMinutes=45;
input int                   InpBrokerGMTOffsetWinter=2;
input bool                  InpBrokerFollowsUS_DST=true;

const string EA_NAME="EA_VRAS_RegimeAdaptiveScalperV3";
const string TELEMETRY_PROFILE="lifecycle-v3";
const string REPORT_SHA256="AB57D7D3F8993784C9B0016E4347BB7D093122A539C0A741C0389648AD014F0C";
const string GAP_REPORT_SHA256="DDBBCAD8F6DF1AD1DCD87855F3812B4DDC1F2DD775F9F74911B5686B3DFBD1B7";
const string SOURCE_DATA_SHA256="2959C555DB6690FD6EFD6CFB3B4C6323698E590C9B2D71E1E55F1902F724235A";
const string CLOCK_CONTRACT="broker_us_dst_to_utc_eu_us_local_session_v1";
const int REGIME_REPLAY_BARS=240;

struct WeightedStats
  {
   double weight;
   double mean;
   double m2;
   double variance;
   double sd;
   int samples;
   datetime anchor_utc;
  };

struct DecisionState
  {
   ENUM_VRAS_SIGNAL signal;
   int direction;
   datetime decision_server;
   datetime decision_utc;
   datetime anchor_utc;
   double open1;
   double high1;
   double low1;
   double close1;
   double open2;
   double close2;
   double adx;
   double atr;
   double rsi;
   double session_vwap;
   double session_sd;
   double shadow_vwap;
   double shadow_sd;
   double m15_close;
   double m15_vwap;
   double anchored_vwap;
   datetime avwap_anchor_time;
   datetime avwap_confirmed_time;
   double planned_stop;
   double planned_target;
   string event_code;
  };

int g_adx_handle=INVALID_HANDLE;
int g_atr_handle=INVALID_HANDLE;
int g_rsi_handle=INVALID_HANDLE;
datetime g_last_m5_bar=0;
ENUM_VRAS_REGIME g_regime=REGIME_RANGE;
int g_bars_since_regime_switch=999999;
bool g_regime_initialized=false;
long g_regime_switches=0;

int g_day_key=0;
double g_day_start_equity=0.0;
double g_peak_equity=0.0;
int g_trades_today=0;
int g_consecutive_losses=0;

ulong g_position_identifier=0;
double g_initial_entry=0.0;
double g_initial_stop=0.0;
double g_planned_risk_account=0.0;
double g_position_net=0.0;

int g_lifecycle_handle=INVALID_HANDLE;
int g_decision_handle=INVALID_HANDLE;
string g_run_id="";
string g_lifecycle_name="";
string g_run_meta_name="";
string g_decision_name="";

long g_bars_seen=0;
long g_range_bars=0;
long g_trend_bars=0;
long g_warmup_rejections=0;
long g_sd_floor_rejections=0;
long g_anchor_rejections=0;
long g_m15_rejections=0;
long g_news_rejections=0;
long g_spread_rejections=0;
long g_cost_rejections=0;
long g_risk_rejections=0;
long g_session_rejections=0;
long g_entries_attempted=0;
long g_entries_opened=0;
long g_range_long_entries=0;
long g_range_short_entries=0;
long g_trend_long_entries=0;
long g_trend_short_entries=0;

double PipSize()
  {
   return (_Digits==3 || _Digits==5) ? 10.0*_Point : _Point;
  }

int DaysInMonth(const int year,const int month)
  {
   if(month==2)
      return ((year%4==0 && year%100!=0) || year%400==0) ? 29 : 28;
   if(month==4 || month==6 || month==9 || month==11)
      return 30;
   return 31;
  }

datetime MakeDateTime(const int year,const int month,const int day,
                      const int hour,const int minute=0)
  {
   MqlDateTime value;
   ZeroMemory(value);
   value.year=year;
   value.mon=month;
   value.day=day;
   value.hour=hour;
   value.min=minute;
   return StructToTime(value);
  }

datetime LastSunday(const int year,const int month,const int hour)
  {
   datetime value=MakeDateTime(year,month,DaysInMonth(year,month),hour);
   MqlDateTime parts;
   TimeToStruct(value,parts);
   return value-parts.day_of_week*86400;
  }

datetime NthSunday(const int year,const int month,const int ordinal,const int hour)
  {
   datetime value=MakeDateTime(year,month,1,hour);
   MqlDateTime parts;
   TimeToStruct(value,parts);
   int first_sunday=1+((7-parts.day_of_week)%7);
   return MakeDateTime(year,month,first_sunday+7*(ordinal-1),hour);
  }

bool IsEuropeDstUtc(const datetime utc_time)
  {
   MqlDateTime parts;
   TimeToStruct(utc_time,parts);
   datetime start=LastSunday(parts.year,3,1);
   datetime finish=LastSunday(parts.year,10,1);
   return utc_time>=start && utc_time<finish;
  }

bool IsUsDstUtc(const datetime utc_time)
  {
   MqlDateTime parts;
   TimeToStruct(utc_time,parts);
   datetime start=NthSunday(parts.year,3,2,7);
   datetime finish=NthSunday(parts.year,11,1,6);
   return utc_time>=start && utc_time<finish;
  }

datetime ServerToUtc(const datetime server_time)
  {
   datetime winter_candidate=server_time-InpBrokerGMTOffsetWinter*3600;
   int offset=InpBrokerGMTOffsetWinter;
   if(InpBrokerFollowsUS_DST && IsUsDstUtc(winter_candidate))
      offset++;
   return server_time-offset*3600;
  }

datetime UtcToServer(const datetime utc_time)
  {
   int offset=InpBrokerGMTOffsetWinter;
   if(InpBrokerFollowsUS_DST && IsUsDstUtc(utc_time))
      offset++;
   return utc_time+offset*3600;
  }

datetime UtcMidnight(const datetime utc_time)
  {
   MqlDateTime parts;
   TimeToStruct(utc_time,parts);
   return MakeDateTime(parts.year,parts.mon,parts.day,0);
  }

datetime LondonOpenUtcForDate(const datetime utc_time)
  {
   MqlDateTime parts;
   TimeToStruct(utc_time,parts);
   datetime local_naive=MakeDateTime(parts.year,parts.mon,parts.day,8);
   datetime probe=local_naive;
   return local_naive-(IsEuropeDstUtc(probe) ? 3600 : 0);
  }

datetime NewYorkCloseUtcForDate(const datetime utc_time)
  {
   MqlDateTime parts;
   TimeToStruct(utc_time,parts);
   datetime local_naive=MakeDateTime(parts.year,parts.mon,parts.day,16);
   datetime winter_candidate=local_naive+5*3600;
   return local_naive+(IsUsDstUtc(winter_candidate) ? 4 : 5)*3600;
  }

datetime SessionAnchorUtc(const datetime decision_utc)
  {
   if(InpAnchorMode==ANCHOR_UTC_MIDNIGHT)
      return UtcMidnight(decision_utc);
   if(InpAnchorMode==ANCHOR_BROKER_DAILY)
     {
      datetime server_time=UtcToServer(decision_utc);
      MqlDateTime parts;
      TimeToStruct(server_time,parts);
      datetime server_midnight=MakeDateTime(parts.year,parts.mon,parts.day,0);
      return ServerToUtc(server_midnight);
     }
   datetime anchor=LondonOpenUtcForDate(decision_utc);
   if(decision_utc<anchor)
      anchor=LondonOpenUtcForDate(decision_utc-86400);
   return anchor;
  }

bool SessionAllows(const datetime decision_utc)
  {
   datetime start=LondonOpenUtcForDate(decision_utc);
   datetime finish=NewYorkCloseUtcForDate(decision_utc);
   return decision_utc>=start && decision_utc<finish;
  }

bool SessionMustFlatten(const datetime now_utc)
  {
   return now_utc>=NewYorkCloseUtcForDate(now_utc);
  }

int UtcDateKey(const datetime server_time)
  {
   MqlDateTime parts;
   TimeToStruct(ServerToUtc(server_time),parts);
   return parts.year*10000+parts.mon*100+parts.day;
  }

double CurrentSpreadPips()
  {
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick))
      return 0.0;
   return (tick.ask-tick.bid)/PipSize();
  }

void ResetWeightedStats(WeightedStats &state,const datetime anchor_utc)
  {
   ZeroMemory(state);
   state.anchor_utc=anchor_utc;
  }

void WeightedWelfordAdd(WeightedStats &state,const double value,const double weight)
  {
   if(weight<=0.0 || !MathIsValidNumber(value) || !MathIsValidNumber(weight))
      return;
   double next_weight=state.weight+weight;
   double delta=value-state.mean;
   state.mean+=(weight/next_weight)*delta;
   state.m2+=weight*delta*(value-state.mean);
   state.weight=next_weight;
   state.samples++;
  }

void FinishWeightedStats(WeightedStats &state)
  {
   if(state.weight<=0.0)
     {
      state.variance=0.0;
      state.sd=0.0;
      return;
     }
   state.variance=MathMax(0.0,state.m2/state.weight);
   state.sd=MathSqrt(state.variance);
  }

double BarWeight(const MqlRates &bar,const ENUM_VRAS_VOLUME_MODE mode)
  {
   if(mode==VRAS_WEIGHT_EQUAL)
      return 1.0;
   return (double)bar.tick_volume;
  }

bool ComputeSessionStats(const ENUM_TIMEFRAMES timeframe,
                         const datetime decision_server,
                         const datetime anchor_utc,
                         const ENUM_VRAS_VOLUME_MODE mode,
                         WeightedStats &state,
                         double &last_close)
  {
   ResetWeightedStats(state,anchor_utc);
   last_close=0.0;
   datetime anchor_server=UtcToServer(anchor_utc);
   MqlRates rates[];
   ArraySetAsSeries(rates,true);
   int lookback=(timeframe==PERIOD_M5 ? 400 : 150);
   int copied=CopyRates(_Symbol,timeframe,1,lookback,rates);
   if(copied<=0)
      return false;
   int seconds=PeriodSeconds(timeframe);
   for(int i=copied-1;i>=0;i--)
     {
      if(rates[i].time<anchor_server)
         continue;
      if(rates[i].time+seconds>decision_server)
         continue;
      double typical=(rates[i].high+rates[i].low+rates[i].close)/3.0;
      WeightedWelfordAdd(state,typical,BarWeight(rates[i],mode));
      last_close=rates[i].close;
     }
   FinishWeightedStats(state);
   return state.weight>0.0 && state.samples>0 && last_close>0.0;
  }

bool ReadIndicator(const int handle,const int buffer,double &value)
  {
   value=0.0;
   if(handle==INVALID_HANDLE)
      return false;
   double values[1];
   if(CopyBuffer(handle,buffer,1,1,values)!=1)
      return false;
   value=values[0];
   return MathIsValidNumber(value);
  }

void ApplyRegimeValue(const double adx_value,bool &switched)
  {
   switched=false;
   g_bars_since_regime_switch++;
   if(g_regime==REGIME_RANGE && adx_value>=InpAdxEnter &&
      g_bars_since_regime_switch>=InpMinRegimeDwellBars)
     {
      g_regime=REGIME_TREND;
      g_bars_since_regime_switch=0;
      g_regime_switches++;
      switched=true;
     }
   else if(g_regime==REGIME_TREND && adx_value<InpAdxExit &&
           g_bars_since_regime_switch>=InpMinRegimeDwellBars)
     {
      g_regime=REGIME_RANGE;
      g_bars_since_regime_switch=0;
      g_regime_switches++;
      switched=true;
     }
  }

bool InitializeRegimeReplay()
  {
   double values[];
   int copied=CopyBuffer(g_adx_handle,0,2,REGIME_REPLAY_BARS,values);
   if(copied<=0)
      return false;
   g_regime=REGIME_RANGE;
   g_bars_since_regime_switch=InpMinRegimeDwellBars;
   g_regime_switches=0;
   for(int i=0;i<copied;i++)
     {
      if(!MathIsValidNumber(values[i]))
         return false;
      bool ignored=false;
      ApplyRegimeValue(values[i],ignored);
     }
   g_regime_initialized=true;
   return true;
  }

bool UpdateRegime(const double adx_value,bool &switched)
  {
   if(!g_regime_initialized && !InitializeRegimeReplay())
      return false;
   ApplyRegimeValue(adx_value,switched);
   return true;
  }

bool BullishRejection(const MqlRates &bar1,const MqlRates &bar2)
  {
   double range=bar1.high-bar1.low;
   if(range<=0.0)
      return false;
   double body=MathAbs(bar1.close-bar1.open);
   double lower_wick=MathMin(bar1.open,bar1.close)-bar1.low;
   bool pin=(bar1.close>bar1.open && body/range<=0.40 && lower_wick/range>=0.50);
   bool engulf=(bar1.close>bar1.open && bar2.close<bar2.open &&
                bar1.open<=bar2.close && bar1.close>=bar2.open);
   return pin || engulf;
  }

bool BearishRejection(const MqlRates &bar1,const MqlRates &bar2)
  {
   double range=bar1.high-bar1.low;
   if(range<=0.0)
      return false;
   double body=MathAbs(bar1.close-bar1.open);
   double upper_wick=bar1.high-MathMax(bar1.open,bar1.close);
   bool pin=(bar1.close<bar1.open && body/range<=0.40 && upper_wick/range>=0.50);
   bool engulf=(bar1.close<bar1.open && bar2.close>bar2.open &&
                bar1.open>=bar2.close && bar1.close<=bar2.open);
   return pin || engulf;
  }

bool FindConfirmedAnchor(const int direction,datetime &anchor_time,
                         datetime &confirmed_time)
  {
   anchor_time=0;
   confirmed_time=0;
   MqlRates bars[];
   ArraySetAsSeries(bars,true);
   int need=MathMax(7,InpAnchorLookbackBars+5);
   int copied=CopyRates(_Symbol,PERIOD_M5,1,need,bars);
   if(copied<5)
      return false;
   int limit=MathMin(copied-3,InpAnchorLookbackBars);
   for(int center=2;center<=limit;center++)
     {
      bool low_fractal=(bars[center].low<bars[center-1].low &&
                        bars[center].low<bars[center-2].low &&
                        bars[center].low<bars[center+1].low &&
                        bars[center].low<bars[center+2].low);
      bool high_fractal=(bars[center].high>bars[center-1].high &&
                         bars[center].high>bars[center-2].high &&
                         bars[center].high>bars[center+1].high &&
                         bars[center].high>bars[center+2].high);
      if((direction>0 && low_fractal) || (direction<0 && high_fractal))
        {
         anchor_time=bars[center].time;
         confirmed_time=bars[center-2].time+PeriodSeconds(PERIOD_M5);
         return true;
        }
     }
   return false;
  }

bool ComputeAnchoredVwap(const datetime anchor_server,
                         const datetime decision_server,
                         const ENUM_VRAS_VOLUME_MODE mode,
                         double &value)
  {
   value=0.0;
   MqlRates rates[];
   ArraySetAsSeries(rates,true);
   int copied=CopyRates(_Symbol,PERIOD_M5,1,70,rates);
   if(copied<=0)
      return false;
   WeightedStats state;
   ResetWeightedStats(state,ServerToUtc(anchor_server));
   for(int i=copied-1;i>=0;i--)
     {
      if(rates[i].time<anchor_server)
         continue;
      if(rates[i].time+PeriodSeconds(PERIOD_M5)>decision_server)
         continue;
      double typical=(rates[i].high+rates[i].low+rates[i].close)/3.0;
      WeightedWelfordAdd(state,typical,BarWeight(rates[i],mode));
     }
   FinishWeightedStats(state);
   if(state.samples<3 || state.weight<=0.0)
      return false;
   value=state.mean;
   return MathIsValidNumber(value) && value>0.0;
  }

bool NewsCalendarValid()
  {
   if(NEWS_CALENDAR_COUNT<=0 || NEWS_CALENDAR_SOURCE_SHA256=="")
      return false;
   for(int i=1;i<NEWS_CALENDAR_COUNT;i++)
      if(NEWS_CALENDAR_UTC[i]<NEWS_CALENDAR_UTC[i-1])
         return false;
   return true;
  }

bool NewsBlocked(const datetime server_time)
  {
   if(!InpRequireNewsGuard)
      return false;
   datetime utc=ServerToUtc(server_time);
   if(utc<NEWS_CALENDAR_COVERAGE_START_UTC || utc>NEWS_CALENDAR_COVERAGE_END_UTC)
      return true;
   int left=0;
   int right=NEWS_CALENDAR_COUNT-1;
   while(left<=right)
     {
      int mid=(left+right)/2;
      datetime event_time=NEWS_CALENDAR_UTC[mid];
      long delta=(long)utc-(long)event_time;
      if(MathAbs((double)delta)<=InpNewsBlackoutMinutes*60)
         return true;
      if(event_time<utc)
         left=mid+1;
      else
         right=mid-1;
     }
   if(left<NEWS_CALENDAR_COUNT &&
      MathAbs((double)((long)utc-(long)NEWS_CALENDAR_UTC[left]))<=InpNewsBlackoutMinutes*60)
      return true;
   if(right>=0 &&
      MathAbs((double)((long)utc-(long)NEWS_CALENDAR_UTC[right]))<=InpNewsBlackoutMinutes*60)
      return true;
   return false;
  }

void ResetRiskDayIfNeeded(const datetime server_time)
  {
   int key=UtcDateKey(server_time);
   if(key==g_day_key)
      return;
   g_day_key=key;
   g_day_start_equity=AccountInfoDouble(ACCOUNT_EQUITY);
   g_trades_today=0;
   g_consecutive_losses=0;
  }

bool DailyLossHit()
  {
   double equity=AccountInfoDouble(ACCOUNT_EQUITY);
   return g_day_start_equity>0.0 &&
          equity<=g_day_start_equity*(1.0-InpDailyLossPct/100.0);
  }

bool AccountDrawdownHit()
  {
   double equity=AccountInfoDouble(ACCOUNT_EQUITY);
   return g_peak_equity>0.0 &&
          equity<=g_peak_equity*(1.0-InpMaxAccountDrawdownPct/100.0);
  }

ulong OwnedPositionTicket()
  {
   for(int i=PositionsTotal()-1;i>=0;i--)
     {
      ulong ticket=PositionGetTicket(i);
      if(ticket==0 || !PositionSelectByTicket(ticket))
         continue;
      if(PositionGetString(POSITION_SYMBOL)==_Symbol &&
         (long)PositionGetInteger(POSITION_MAGIC)==InpMagic)
         return ticket;
     }
   return 0;
  }

bool AnySymbolExposure()
  {
   for(int i=PositionsTotal()-1;i>=0;i--)
     {
      ulong ticket=PositionGetTicket(i);
      if(ticket==0 || !PositionSelectByTicket(ticket))
         return true;
      if(PositionGetString(POSITION_SYMBOL)==_Symbol)
         return true;
     }
   for(int i=OrdersTotal()-1;i>=0;i--)
     {
      ulong ticket=OrderGetTicket(i);
      if(ticket==0)
         return true;
      if(OrderGetString(ORDER_SYMBOL)==_Symbol)
         return true;
     }
   return false;
  }

double NormalizeVolumeDown(const double raw)
  {
   double minimum=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN);
   double maximum=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX);
   double step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);
   if(minimum<=0.0 || maximum<minimum || step<=0.0)
      return 0.0;
   double volume=MathFloor((MathMin(raw,maximum)+1e-12)/step)*step;
   if(volume<minimum)
      return 0.0;
   return NormalizeDouble(volume,8);
  }

double RiskSizedVolume(const int direction,const double entry,const double stop,
                       double &planned_risk_account)
  {
   planned_risk_account=0.0;
   double equity=AccountInfoDouble(ACCOUNT_EQUITY);
   double budget=equity*InpRiskPercent/100.0;
   if(budget<=0.0)
      return 0.0;
   ENUM_ORDER_TYPE type=direction>0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
   double stop_loss=0.0;
   if(!OrderCalcProfit(type,_Symbol,1.0,entry,stop,stop_loss))
      return 0.0;
   double cost_close=entry-direction*(InpCommissionPips+
                                      2.0*InpSlippageOneWayPips)*PipSize();
   double cost_loss=0.0;
   if(!OrderCalcProfit(type,_Symbol,1.0,entry,cost_close,cost_loss))
      return 0.0;
   double loss_per_lot=MathAbs(stop_loss)+MathAbs(cost_loss);
   if(loss_per_lot<=0.0 || !MathIsValidNumber(loss_per_lot))
      return 0.0;
   double volume=NormalizeVolumeDown(budget/loss_per_lot);
   if(volume<=0.0)
      return 0.0;
   planned_risk_account=loss_per_lot*volume;
   if(planned_risk_account>budget*(1.0+1e-8))
      return 0.0;
   return volume;
  }

bool CostDistanceAllows(const int direction,const double entry,const double target,
                        const double spread_pips,double &estimated_cost_pips)
  {
   estimated_cost_pips=spread_pips+InpCommissionPips+2.0*InpSlippageOneWayPips;
   if(estimated_cost_pips<=0.0 || !MathIsValidNumber(estimated_cost_pips))
      return false;
   double target_pips=direction*(target-entry)/PipSize();
   return target_pips>0.0 &&
          target_pips>=InpCostDistanceMultiple*estimated_cost_pips;
  }

bool EntryGuardsAllow(const datetime decision_server)
  {
   ResetRiskDayIfNeeded(decision_server);
   if(!InpResearchAutoMode || !MQLInfoInteger(MQL_TESTER))
      return false;
   datetime decision_utc=ServerToUtc(decision_server);
   if(!SessionAllows(decision_utc))
     {
      g_session_rejections++;
      return false;
     }
   if(g_trades_today>=InpMaxTradesPerDay || g_consecutive_losses>=3 ||
      DailyLossHit() || AccountDrawdownHit() || AnySymbolExposure())
      return false;
   if(NewsBlocked(decision_server))
     {
      g_news_rejections++;
      return false;
     }
   double spread=CurrentSpreadPips();
   if(spread<=0.0 || spread>InpMaxSpreadPips)
     {
      g_spread_rejections++;
      return false;
     }
   return true;
  }

bool EvaluateSignal(MqlRates &bars[],const datetime decision_server,
                    DecisionState &state)
  {
   ZeroMemory(state);
   state.signal=SIGNAL_NONE;
   state.direction=0;
   state.decision_server=decision_server;
   state.decision_utc=ServerToUtc(decision_server);
   state.anchor_utc=SessionAnchorUtc(state.decision_utc);
   state.open1=bars[0].open;
   state.high1=bars[0].high;
   state.low1=bars[0].low;
   state.close1=bars[0].close;
   state.open2=bars[1].open;
   state.close2=bars[1].close;
   state.event_code="NO_SIGNAL";

   if(!ReadIndicator(g_adx_handle,0,state.adx) ||
      !ReadIndicator(g_atr_handle,0,state.atr) ||
      !ReadIndicator(g_rsi_handle,0,state.rsi) ||
      state.atr<=0.0)
     {
      state.event_code="INDICATOR_INVALID";
      return false;
     }

   bool switched=false;
   if(!UpdateRegime(state.adx,switched))
     {
      state.event_code="REGIME_INVALID";
      return false;
     }

   WeightedStats tick_stats,equal_stats;
   double tick_close=0.0,equal_close=0.0;
   if(!ComputeSessionStats(PERIOD_M5,decision_server,state.anchor_utc,
                           VRAS_WEIGHT_TICK,tick_stats,tick_close) ||
      !ComputeSessionStats(PERIOD_M5,decision_server,state.anchor_utc,
                           VRAS_WEIGHT_EQUAL,equal_stats,equal_close))
     {
      state.event_code="SESSION_DATA_INVALID";
      return false;
     }
   WeightedStats primary=(InpVolumeMode==VRAS_WEIGHT_TICK ? tick_stats : equal_stats);
   WeightedStats shadow=(InpVolumeMode==VRAS_WEIGHT_TICK ? equal_stats : tick_stats);
   state.session_vwap=primary.mean;
   state.session_sd=primary.sd;
   state.shadow_vwap=shadow.mean;
   state.shadow_sd=shadow.sd;

   if(primary.samples<InpWarmupBars)
     {
      g_warmup_rejections++;
      state.event_code="WARMUP";
      return false;
     }
   if(state.session_sd<InpSdFloorAtr*state.atr)
     {
      g_sd_floor_rejections++;
      state.event_code="SD_FLOOR";
      return false;
     }

   bool bull=BullishRejection(bars[0],bars[1]);
   bool bear=BearishRejection(bars[0],bars[1]);
   double upper2=state.session_vwap+InpBandMultiplier*state.session_sd;
   double lower2=state.session_vwap-InpBandMultiplier*state.session_sd;
   double upper1=state.session_vwap+state.session_sd;
   double lower1=state.session_vwap-state.session_sd;

   if(g_regime==REGIME_RANGE)
     {
      g_range_bars++;
      if(state.close1<=lower2 && bull && state.rsi>InpRsiLongFloor)
        {
         state.signal=SIGNAL_RANGE_LONG;
         state.direction=1;
         state.planned_stop=MathMin(state.low1-InpRangeStopAtr*state.atr,
                                    state.session_vwap-InpRangeStopSd*state.session_sd);
         state.planned_target=state.session_vwap;
         state.event_code="RANGE_LONG";
         return true;
        }
      if(state.close1>=upper2 && bear && state.rsi<InpRsiShortCeiling)
        {
         state.signal=SIGNAL_RANGE_SHORT;
         state.direction=-1;
         state.planned_stop=MathMax(state.high1+InpRangeStopAtr*state.atr,
                                    state.session_vwap+InpRangeStopSd*state.session_sd);
         state.planned_target=state.session_vwap;
         state.event_code="RANGE_SHORT";
         return true;
        }
      if(switched)
         state.event_code="REGIME_SWITCH_RANGE";
      return false;
     }

   if(g_regime==REGIME_TREND)
     {
      g_trend_bars++;
      WeightedStats m15_stats;
      double m15_close=0.0;
      if(InpUseM15Bias &&
         !ComputeSessionStats(PERIOD_M15,decision_server,state.anchor_utc,
                              InpVolumeMode,m15_stats,m15_close))
        {
         g_m15_rejections++;
         state.event_code="M15_DATA_INVALID";
         return false;
        }
      state.m15_close=m15_close;
      state.m15_vwap=InpUseM15Bias ? m15_stats.mean : 0.0;

      bool long_pullback=(state.low1<=state.session_vwap &&
                          state.close1>=lower1);
      bool short_pullback=(state.high1>=state.session_vwap &&
                           state.close1<=upper1);

      if(state.close1>state.session_vwap && long_pullback && bull)
        {
         datetime anchor_time=0,confirmed_time=0;
         if(!FindConfirmedAnchor(1,anchor_time,confirmed_time) ||
            !ComputeAnchoredVwap(anchor_time,decision_server,InpVolumeMode,
                                 state.anchored_vwap))
           {
            g_anchor_rejections++;
            state.event_code="LONG_ANCHOR_INVALID";
            return false;
           }
         state.avwap_anchor_time=anchor_time;
         state.avwap_confirmed_time=confirmed_time;
         if(state.close1<=state.anchored_vwap)
           {
            g_anchor_rejections++;
            state.event_code="LONG_AVWAP_REJECT";
            return false;
           }
         if(InpUseM15Bias && state.m15_close<=state.m15_vwap)
           {
            g_m15_rejections++;
            state.event_code="LONG_M15_REJECT";
            return false;
           }
         state.signal=SIGNAL_TREND_LONG;
         state.direction=1;
         state.planned_stop=state.low1-InpTrendStopAtr*state.atr;
         state.event_code="TREND_LONG";
         return true;
        }

      if(state.close1<state.session_vwap && short_pullback && bear)
        {
         datetime anchor_time=0,confirmed_time=0;
         if(!FindConfirmedAnchor(-1,anchor_time,confirmed_time) ||
            !ComputeAnchoredVwap(anchor_time,decision_server,InpVolumeMode,
                                 state.anchored_vwap))
           {
            g_anchor_rejections++;
            state.event_code="SHORT_ANCHOR_INVALID";
            return false;
           }
         state.avwap_anchor_time=anchor_time;
         state.avwap_confirmed_time=confirmed_time;
         if(state.close1>=state.anchored_vwap)
           {
            g_anchor_rejections++;
            state.event_code="SHORT_AVWAP_REJECT";
            return false;
           }
         if(InpUseM15Bias && state.m15_close>=state.m15_vwap)
           {
            g_m15_rejections++;
            state.event_code="SHORT_M15_REJECT";
            return false;
           }
         state.signal=SIGNAL_TREND_SHORT;
         state.direction=-1;
         state.planned_stop=state.high1+InpTrendStopAtr*state.atr;
         state.event_code="TREND_SHORT";
         return true;
        }
      if(switched)
         state.event_code="REGIME_SWITCH_TREND";
     }
   return false;
  }

void WriteDecisionTelemetry(const DecisionState &state,const double entry,
                            const double stop,const double target,
                            const double estimated_cost,const string status)
  {
   if(!InpEnableTelemetry || g_decision_handle==INVALID_HANDLE)
      return;
   FileWrite(g_decision_handle,
             TimeToString(state.decision_server,TIME_DATE|TIME_SECONDS),
             TimeToString(state.decision_utc,TIME_DATE|TIME_SECONDS),
             InpVariantTag,(int)g_regime,state.event_code,status,
             DoubleToString(state.adx,6),DoubleToString(state.atr,_Digits),
             DoubleToString(state.rsi,6),
             DoubleToString(state.session_vwap,_Digits),
             DoubleToString(state.session_sd,_Digits),
             DoubleToString(state.shadow_vwap,_Digits),
             DoubleToString(state.shadow_sd,_Digits),
             TimeToString(state.anchor_utc,TIME_DATE|TIME_SECONDS),
             TimeToString(state.avwap_anchor_time,TIME_DATE|TIME_SECONDS),
             TimeToString(state.avwap_confirmed_time,TIME_DATE|TIME_SECONDS),
             DoubleToString(state.anchored_vwap,_Digits),
             DoubleToString(state.m15_close,_Digits),
             DoubleToString(state.m15_vwap,_Digits),
             DoubleToString(entry,_Digits),DoubleToString(stop,_Digits),
             DoubleToString(target,_Digits),DoubleToString(estimated_cost,6),
             DoubleToString(CurrentSpreadPips(),6));
   FileFlush(g_decision_handle);
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

bool TryOpenTrade(const DecisionState &state)
  {
   g_entries_attempted++;
   if(!EntryGuardsAllow(state.decision_server))
     {
      WriteDecisionTelemetry(state,0.0,state.planned_stop,state.planned_target,0.0,
                             "ENTRY_GUARD_REJECT");
      return false;
     }
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick))
      return false;
   double spread=(tick.ask-tick.bid)/PipSize();
   if(spread<=0.0 || spread>InpMaxSpreadPips || AnySymbolExposure())
     {
      g_spread_rejections++;
      WriteDecisionTelemetry(state,0.0,state.planned_stop,state.planned_target,0.0,
                             "PRESEND_SPREAD_OR_EXPOSURE");
      return false;
     }
   int direction=state.direction;
   double entry=direction>0 ? tick.ask : tick.bid;
   double stop=NormalizeDouble(state.planned_stop,_Digits);
   double target=state.planned_target;
   if(state.signal==SIGNAL_TREND_LONG || state.signal==SIGNAL_TREND_SHORT)
      target=entry+direction*InpTrendTargetR*MathAbs(entry-stop);
   target=NormalizeDouble(target,_Digits);
   if(direction*(entry-stop)<=0.0 || direction*(target-entry)<=0.0)
     {
      g_risk_rejections++;
      WriteDecisionTelemetry(state,entry,stop,target,0.0,"GEOMETRY_REJECT");
      return false;
     }

   long stops_level=0;
   long freeze_level=0;
   if(!SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL,stops_level) ||
      !SymbolInfoInteger(_Symbol,SYMBOL_TRADE_FREEZE_LEVEL,freeze_level))
      return false;
   double minimum_distance=MathMax((double)stops_level,(double)freeze_level)*_Point;
   if(MathAbs(entry-stop)<minimum_distance || MathAbs(target-entry)<minimum_distance)
     {
      g_risk_rejections++;
      WriteDecisionTelemetry(state,entry,stop,target,0.0,"BROKER_DISTANCE_REJECT");
      return false;
     }

   double estimated_cost=0.0;
   if(!CostDistanceAllows(direction,entry,target,spread,estimated_cost))
     {
      g_cost_rejections++;
      WriteDecisionTelemetry(state,entry,stop,target,estimated_cost,"COST_DISTANCE_REJECT");
      return false;
     }

   double risk_account=0.0;
   double volume=RiskSizedVolume(direction,entry,stop,risk_account);
   if(volume<=0.0 || risk_account<=0.0)
     {
      g_risk_rejections++;
      WriteDecisionTelemetry(state,entry,stop,target,estimated_cost,"SIZING_REJECT");
      return false;
     }

   MqlTradeRequest request;
   MqlTradeCheckResult check;
   MqlTradeResult result;
   ZeroMemory(request);
   ZeroMemory(check);
   ZeroMemory(result);
   request.action=TRADE_ACTION_DEAL;
   request.magic=(ulong)InpMagic;
   request.symbol=_Symbol;
   request.volume=volume;
   request.type=direction>0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
   request.price=entry;
   request.sl=stop;
   request.tp=target;
   request.deviation=(ulong)MathMax(1,MathRound(InpSlippageOneWayPips*PipSize()/_Point));
   request.type_filling=FillingMode();
   request.type_time=ORDER_TIME_GTC;
   request.comment=StringSubstr(InpHypothesisId,0,30);

   // OrderCheck success is expressed by its boolean return. On a successful
   // preflight MqlTradeCheckResult.retcode is 0, not an OrderSend retcode.
   if(!OrderCheck(request,check))
     {
      g_risk_rejections++;
      PrintFormat("VRAS OrderCheck rejected retcode=%u comment=%s margin=%.2f free=%.2f",
                  check.retcode,check.comment,check.margin,check.margin_free);
      WriteDecisionTelemetry(state,entry,stop,target,estimated_cost,"ORDER_CHECK_REJECT");
      return false;
     }
   if(!OrderSend(request,result) ||
      (result.retcode!=TRADE_RETCODE_DONE &&
       result.retcode!=TRADE_RETCODE_DONE_PARTIAL &&
       result.retcode!=TRADE_RETCODE_PLACED))
     {
      g_risk_rejections++;
      WriteDecisionTelemetry(state,entry,stop,target,estimated_cost,"ORDER_SEND_REJECT");
      return false;
     }
   g_initial_entry=entry;
   g_initial_stop=stop;
   g_planned_risk_account=risk_account;
   if(state.signal==SIGNAL_RANGE_LONG) g_range_long_entries++;
   if(state.signal==SIGNAL_RANGE_SHORT) g_range_short_entries++;
   if(state.signal==SIGNAL_TREND_LONG) g_trend_long_entries++;
   if(state.signal==SIGNAL_TREND_SHORT) g_trend_short_entries++;
   WriteDecisionTelemetry(state,entry,stop,target,estimated_cost,"ORDER_ACCEPTED");
   return true;
  }

bool PositionIdentifierExists(const ulong identifier)
  {
   if(identifier==0)
      return false;
   for(int i=PositionsTotal()-1;i>=0;i--)
     {
      ulong ticket=PositionGetTicket(i);
      if(ticket==0 || !PositionSelectByTicket(ticket))
         continue;
      if((ulong)PositionGetInteger(POSITION_IDENTIFIER)==identifier)
         return true;
     }
   return false;
  }

ENUM_ORDER_TYPE EntryTypeForPosition(const ulong identifier)
  {
   if(!HistorySelect(0,TimeCurrent()))
      return ORDER_TYPE_BUY;
   int total=HistoryDealsTotal();
   for(int i=0;i<total;i++)
     {
      ulong deal=HistoryDealGetTicket(i);
      if(deal==0 ||
         (ulong)HistoryDealGetInteger(deal,DEAL_POSITION_ID)!=identifier)
         continue;
      ENUM_DEAL_ENTRY entry=(ENUM_DEAL_ENTRY)HistoryDealGetInteger(deal,DEAL_ENTRY);
      if(entry==DEAL_ENTRY_IN || entry==DEAL_ENTRY_INOUT)
         return HistoryDealGetInteger(deal,DEAL_TYPE)==DEAL_TYPE_SELL ?
                ORDER_TYPE_SELL : ORDER_TYPE_BUY;
     }
   return ORDER_TYPE_BUY;
  }

void LogLifecycleDeal(const ulong deal)
  {
   if(!HistoryDealSelect(deal))
      return;
   if(HistoryDealGetString(deal,DEAL_SYMBOL)!=_Symbol ||
      (long)HistoryDealGetInteger(deal,DEAL_MAGIC)!=InpMagic)
      return;
   ENUM_DEAL_ENTRY entry=(ENUM_DEAL_ENTRY)HistoryDealGetInteger(deal,DEAL_ENTRY);
   if(entry!=DEAL_ENTRY_IN && entry!=DEAL_ENTRY_INOUT &&
      entry!=DEAL_ENTRY_OUT && entry!=DEAL_ENTRY_OUT_BY)
      return;
   ulong position_id=(ulong)HistoryDealGetInteger(deal,DEAL_POSITION_ID);
   bool is_open=(entry==DEAL_ENTRY_IN || entry==DEAL_ENTRY_INOUT);
   bool final_close=(!is_open && !PositionIdentifierExists(position_id));
   ENUM_ORDER_TYPE order_type=EntryTypeForPosition(position_id);
   double profit=HistoryDealGetDouble(deal,DEAL_PROFIT);
   double commission=HistoryDealGetDouble(deal,DEAL_COMMISSION);
   double swap=HistoryDealGetDouble(deal,DEAL_SWAP);
   double fee=HistoryDealGetDouble(deal,DEAL_FEE);
   double net=profit+commission+swap+fee;
   if(is_open)
     {
      order_type=HistoryDealGetInteger(deal,DEAL_TYPE)==DEAL_TYPE_SELL ?
                 ORDER_TYPE_SELL : ORDER_TYPE_BUY;
      if(position_id!=g_position_identifier)
        {
         g_entries_opened++;
         g_trades_today++;
        }
      g_position_identifier=position_id;
      g_position_net=0.0;
     }
   g_position_net+=net;
   if(InpEnableTelemetry && g_lifecycle_handle!=INVALID_HANDLE)
     {
      FileWrite(g_lifecycle_handle,
                TimeToString((datetime)HistoryDealGetInteger(deal,DEAL_TIME),
                             TIME_DATE|TIME_SECONDS),
                is_open ? "OPEN" : (final_close ? "CLOSE" : "CLOSE_PARTIAL"),
                order_type==ORDER_TYPE_SELL ? "SELL" : "BUY",
                DoubleToString(HistoryDealGetDouble(deal,DEAL_VOLUME),8),
                DoubleToString(HistoryDealGetDouble(deal,DEAL_PRICE),_Digits),
                _Symbol,StringFormat("%I64u",position_id),
                DoubleToString(MathAbs(g_initial_entry-g_initial_stop)/_Point,8),
                DoubleToString(g_planned_risk_account,8),
                StringFormat("%I64u",deal),DoubleToString(profit,8),
                DoubleToString(commission,8),DoubleToString(swap,8),
                DoubleToString(fee,8),DoubleToString(net,8),
                final_close ? "1" : "0");
      FileFlush(g_lifecycle_handle);
     }
   if(final_close)
     {
      if(g_position_net<0.0)
         g_consecutive_losses++;
      else
         g_consecutive_losses=0;
      g_position_identifier=0;
      g_initial_entry=0.0;
      g_initial_stop=0.0;
      g_planned_risk_account=0.0;
      g_position_net=0.0;
     }
  }

bool CloseOwnedPosition(const ulong ticket)
  {
   if(ticket==0 || !PositionSelectByTicket(ticket))
      return false;
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick))
      return false;
   ENUM_POSITION_TYPE pos_type=(ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE);
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
   request.type=pos_type==POSITION_TYPE_BUY ? ORDER_TYPE_SELL : ORDER_TYPE_BUY;
   request.price=pos_type==POSITION_TYPE_BUY ? tick.bid : tick.ask;
   request.deviation=(ulong)MathMax(1,MathRound(InpSlippageOneWayPips*PipSize()/_Point));
   request.type_filling=FillingMode();
   request.comment="VRAS safety exit";
   if(!OrderCheck(request,check))
     {
      PrintFormat("VRAS close OrderCheck rejected retcode=%u comment=%s",
                  check.retcode,check.comment);
      return false;
     }
   if(!OrderSend(request,result))
      return false;
   return result.retcode==TRADE_RETCODE_DONE ||
          result.retcode==TRADE_RETCODE_DONE_PARTIAL ||
          result.retcode==TRADE_RETCODE_PLACED;
  }

void ManageOwnedPosition()
  {
   ulong ticket=OwnedPositionTicket();
   if(ticket==0 || !PositionSelectByTicket(ticket))
      return;
   datetime now_server=TimeCurrent();
   datetime now_utc=ServerToUtc(now_server);
   datetime opened=(datetime)PositionGetInteger(POSITION_TIME);
   if(SessionMustFlatten(now_utc) ||
      now_server-opened>=InpMaxHoldBars*PeriodSeconds(PERIOD_M5) ||
      DailyLossHit() || AccountDrawdownHit())
      CloseOwnedPosition(ticket);
  }

bool WriteRunMeta()
  {
   if(!InpEnableTelemetry || g_run_meta_name=="")
      return true;
   int handle=FileOpen(g_run_meta_name,FILE_WRITE|FILE_TXT|FILE_ANSI);
   if(handle==INVALID_HANDLE)
      return false;
   string payload=StringFormat(
      "{\"schema_version\":\"alphafactory_run_meta.v1\",\"run_id\":\"%s\","
      "\"ea_name\":\"%s\",\"symbol\":\"%s\",\"telemetry_profile\":\"%s\","
      "\"hypothesis_id\":\"%s\",\"variant_tag\":\"%s\",\"volume_mode\":%d,"
      "\"anchor_mode\":%d,\"magic\":%I64d,\"promotion_eligible\":false,"
      "\"report_sha256\":\"%s\",\"gap_report_sha256\":\"%s\","
      "\"source_data_sha256\":\"%s\",\"clock_contract\":\"%s\","
      "\"cost_status\":\"UNVERIFIED_DIAGNOSTIC\",\"news_status\":\"%s\","
      "\"news_source_sha256\":\"%s\",\"diagnostic\":{\"bars_seen\":%I64d,"
      "\"range_bars\":%I64d,\"trend_bars\":%I64d,\"regime_switches\":%I64d,"
      "\"warmup_rejections\":%I64d,\"sd_floor_rejections\":%I64d,"
      "\"anchor_rejections\":%I64d,\"m15_rejections\":%I64d,"
      "\"news_rejections\":%I64d,\"spread_rejections\":%I64d,"
      "\"cost_rejections\":%I64d,\"risk_rejections\":%I64d,"
      "\"session_rejections\":%I64d,\"entries_attempted\":%I64d,"
      "\"entries_opened\":%I64d,\"range_long_entries\":%I64d,"
      "\"range_short_entries\":%I64d,\"trend_long_entries\":%I64d,"
      "\"trend_short_entries\":%I64d}}",
      g_run_id,EA_NAME,_Symbol,TELEMETRY_PROFILE,InpHypothesisId,InpVariantTag,
      (int)InpVolumeMode,(int)InpAnchorMode,InpMagic,REPORT_SHA256,GAP_REPORT_SHA256,
      SOURCE_DATA_SHA256,CLOCK_CONTRACT,
      InpRequireNewsGuard ? NEWS_CALENDAR_SOURCE_CLASS : "DISABLED",
      NEWS_CALENDAR_SOURCE_SHA256,g_bars_seen,g_range_bars,g_trend_bars,
      g_regime_switches,g_warmup_rejections,g_sd_floor_rejections,
      g_anchor_rejections,g_m15_rejections,g_news_rejections,
      g_spread_rejections,g_cost_rejections,g_risk_rejections,
      g_session_rejections,g_entries_attempted,g_entries_opened,
      g_range_long_entries,g_range_short_entries,g_trend_long_entries,
      g_trend_short_entries);
   FileWriteString(handle,payload);
   FileClose(handle);
   return true;
  }

bool OpenTelemetry()
  {
   if(!InpEnableTelemetry)
      return true;
   g_run_id=StringFormat("%s_%I64u",InpHypothesisId,GetTickCount64());
   g_lifecycle_name=StringFormat("%s_LifecycleTrades_%s.csv",_Symbol,g_run_id);
   g_run_meta_name=StringFormat("%s_RunMeta_%s.json",_Symbol,g_run_id);
   g_decision_name=StringFormat("%s_DecisionTelemetry_%s.csv",_Symbol,g_run_id);
   g_lifecycle_handle=FileOpen(g_lifecycle_name,FILE_WRITE|FILE_CSV|FILE_ANSI,',');
   if(g_lifecycle_handle==INVALID_HANDLE)
      return false;
   FileWrite(g_lifecycle_handle,"event_time","action","order_type","volume","price",
             "symbol","position_id","risk_pts","initial_risk_account","deal",
             "deal_profit","deal_commission","deal_swap","deal_fee","deal_net",
             "is_final_close");
   FileFlush(g_lifecycle_handle);
   g_decision_handle=FileOpen(g_decision_name,FILE_WRITE|FILE_CSV|FILE_ANSI,',');
   if(g_decision_handle==INVALID_HANDLE)
      return false;
   FileWrite(g_decision_handle,"server_time","utc_time","variant","regime","event",
             "status","adx","atr","rsi","session_vwap","session_sd",
             "shadow_vwap","shadow_sd","session_anchor_utc","avwap_anchor_server",
             "avwap_confirmed_server","anchored_vwap","m15_close","m15_vwap",
             "entry","stop","target","estimated_cost_pips","spread_pips");
   FileFlush(g_decision_handle);
   return WriteRunMeta();
  }

bool ValidateInputs()
  {
   if(_Symbol!="EURUSD" || _Period!=PERIOD_M5)
      return false;
   if(InpHypothesisId!="HYP-VRAS-EURUSD-M5-003" || InpMagic!=5600743)
      return false;
   if(InpVariantTag=="" || InpAdxPeriod<2 || InpAtrPeriod<2 || InpRsiPeriod<2 ||
      InpAdxEnter<InpAdxExit+4.0 || InpAdxExit<=0.0 ||
      InpMinRegimeDwellBars<1 || InpWarmupBars<3 || InpSdFloorAtr<=0.0 ||
      InpBandMultiplier<=0.0 || InpRangeStopAtr<=0.0 ||
      InpRangeStopSd<=InpBandMultiplier || InpTrendStopAtr<=0.0 ||
      InpTrendTargetR<=0.0 || InpAnchorLookbackBars<5 ||
      InpRsiLongFloor<=0.0 || InpRsiShortCeiling>=100.0 ||
      InpRsiShortCeiling<=InpRsiLongFloor || InpRiskPercent<=0.0 ||
      InpRiskPercent>0.50 || InpMaxSpreadPips<=0.0 ||
      InpCommissionPips<=0.0 || InpSlippageOneWayPips<=0.0 ||
      InpCostDistanceMultiple<1.0 || InpMaxTradesPerDay<1 ||
      InpDailyLossPct<=0.0 || InpMaxAccountDrawdownPct<=0.0 ||
      InpMaxHoldBars<1 || InpNewsBlackoutMinutes<1 ||
      InpBrokerGMTOffsetWinter<-12 || InpBrokerGMTOffsetWinter>14)
      return false;
   if(InpRequireNewsGuard && !NewsCalendarValid())
      return false;
   return true;
  }

int OnInit()
  {
   if(!ValidateInputs())
      return INIT_PARAMETERS_INCORRECT;
   g_adx_handle=iADX(_Symbol,PERIOD_M5,InpAdxPeriod);
   g_atr_handle=iATR(_Symbol,PERIOD_M5,InpAtrPeriod);
   g_rsi_handle=iRSI(_Symbol,PERIOD_M5,InpRsiPeriod,PRICE_CLOSE);
   if(g_adx_handle==INVALID_HANDLE || g_atr_handle==INVALID_HANDLE ||
      g_rsi_handle==INVALID_HANDLE)
      return INIT_FAILED;
   datetime now_server=TimeCurrent();
   g_last_m5_bar=now_server-(now_server%PeriodSeconds(PERIOD_M5));
   g_peak_equity=AccountInfoDouble(ACCOUNT_EQUITY);
   ResetRiskDayIfNeeded(TimeCurrent());
   if(!OpenTelemetry())
      return INIT_FAILED;
   PrintFormat("VRAS init hyp=%s variant=%s volume=%d anchor=%d auto=%s closed_bar=true promotion=false",
               InpHypothesisId,InpVariantTag,(int)InpVolumeMode,(int)InpAnchorMode,
               InpResearchAutoMode ? "true" : "false");
   return INIT_SUCCEEDED;
  }

void OnDeinit(const int reason)
  {
   WriteRunMeta();
   if(g_lifecycle_handle!=INVALID_HANDLE)
     {
      FileFlush(g_lifecycle_handle);
      FileClose(g_lifecycle_handle);
     }
   if(g_decision_handle!=INVALID_HANDLE)
     {
      FileFlush(g_decision_handle);
      FileClose(g_decision_handle);
     }
   if(g_adx_handle!=INVALID_HANDLE) IndicatorRelease(g_adx_handle);
   if(g_atr_handle!=INVALID_HANDLE) IndicatorRelease(g_atr_handle);
   if(g_rsi_handle!=INVALID_HANDLE) IndicatorRelease(g_rsi_handle);
  }

void OnTradeTransaction(const MqlTradeTransaction &trans,
                        const MqlTradeRequest &request,
                        const MqlTradeResult &result)
  {
   if(trans.type==TRADE_TRANSACTION_DEAL_ADD && trans.deal>0)
      LogLifecycleDeal(trans.deal);
  }

void OnTick()
  {
   double equity=AccountInfoDouble(ACCOUNT_EQUITY);
   if(equity>g_peak_equity)
      g_peak_equity=equity;
   ManageOwnedPosition();
   datetime current_bar=iTime(_Symbol,PERIOD_M5,0);
   if(current_bar<=0)
      return;
   if(current_bar==g_last_m5_bar)
      return;
   g_last_m5_bar=current_bar;
   g_bars_seen++;
   MqlRates bars[];
   ArraySetAsSeries(bars,true);
   if(CopyRates(_Symbol,PERIOD_M5,1,3,bars)!=3)
      return;
   DecisionState state;
   bool has_signal=EvaluateSignal(bars,current_bar,state);
   if(has_signal)
      TryOpenTrade(state);
   else if(StringFind(state.event_code,"REGIME_SWITCH")==0)
      WriteDecisionTelemetry(state,0.0,0.0,0.0,0.0,"STATE_EVENT");
  }
