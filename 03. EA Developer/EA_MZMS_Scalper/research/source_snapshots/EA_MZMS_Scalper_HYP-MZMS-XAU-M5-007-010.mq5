#property copyright "AlphaFactory research"
#property version   "1.10"
#property strict
#property description "Owner-authorized MZMS XAUUSD M5 multi-mode research EA"
#property description "Modes 0/1 legacy + 2..5 frozen HYP-007..010; no live or promotion authority"

#include <Trade/Trade.mqh>
#include "NewsCalendar2019_2022.mqh"

enum ENUM_SIGNAL_MODE
  {
   SIGNAL_CONTROL=0,
   SIGNAL_MZMS_CHALLENGER=1,
   SIGNAL_IMPULSE_INIT=2,
   SIGNAL_PULLBACK_RECLAIM=3,
   SIGNAL_SQUEEZE_BREAK=4,
   SIGNAL_EXHAUST_REJECT=5
  };

input bool             InpResearchAutoMode=false;
input bool             InpEnableTelemetry=true;
input ENUM_SIGNAL_MODE InpSignalMode=SIGNAL_MZMS_CHALLENGER;
input string           InpHypothesisId="HYP-MZMS-MACD-HIST-SLOPE-XAUUSD-M5-006";
input double           InpRiskPercent=0.01;
input long             InpMagic=5600722;

input int              InpMacdFast=12;
input int              InpMacdSlow=26;
input int              InpMacdSignal=9;
input int              InpRsiPeriod=14;
input double           InpRsiLower=42.0;
input double           InpRsiUpper=58.0;
input int              InpEmaPeriod=200;
input int              InpAdxPeriod=14;
input double           InpMinAdx=18.0;
input int              InpAtrPeriod=14;
input double           InpMinHistDeltaAtr=0.01;

input int              InpStopLookbackBars=5;
input double           InpStopAtrMultiple=1.50;
input double           InpStopBufferPips=40.00;
input double           InpTargetRR=1.60;
input int              InpMaxHoldBars=15;
input int              InpCooldownBars=5;
input bool             InpUseBreakEven=false;
input double           InpBreakEvenR=1.00;

input double           InpMaxSpreadPips=35.00;
input int              InpMaxTradesPerDay=5;
input double           InpDailyLossPct=1.50;
input double           InpMaxAccountDrawdownPct=8.00;
input int              InpSessionStartUtcHour=8;
input int              InpSessionEndUtcHour=17;
input int              InpFlattenUtcHour=18;
input int              InpFlattenUtcMinute=15;
input int              InpServerUtcOffsetWinterHours=2;
input bool             InpServerUsesEuropeDst=true;
input bool             InpRequireNewsGuard=true;
input int              InpNewsBlackoutMinutes=15;

const string EA_NAME="EA_MZMS_Scalper";
const string TELEMETRY_PROFILE="lifecycle-v3";
const string REPORT_SHA256="0D8D8314273320FF2305557844C8200A9D4052F26D5F30039558B5951A361050";
const string SOURCE_DATA_SHA256="BC45C0CC644CE8BE67FF61245F20F8063BE2BAE99FEFF77D25556CC1F955B563";
const string CLOCK_CONTRACT="fivepercent_server_eu_dst_to_utc_v1";
const int    SIGNAL_RATES_BARS=40;

CTrade trade;
int g_macd_handle=INVALID_HANDLE;
int g_rsi_handle=INVALID_HANDLE;
int g_ema_handle=INVALID_HANDLE;
int g_ema20_handle=INVALID_HANDLE;
int g_ema34_handle=INVALID_HANDLE;
int g_ema50_handle=INVALID_HANDLE;
int g_ema100_handle=INVALID_HANDLE;
int g_adx_handle=INVALID_HANDLE;
int g_atr_handle=INVALID_HANDLE;
int g_bb_handle=INVALID_HANDLE;
datetime g_last_m5_bar=0;
datetime g_last_entry_bar_time=0;
int g_day_key=0;
double g_day_start_equity=0.0;
double g_peak_equity=0.0;
int g_trades_today=0;

ulong g_position_identifier=0;
double g_initial_entry=0.0;
double g_initial_stop=0.0;
double g_planned_risk_account=0.0;
double g_position_lifecycle_net=0.0;

int g_telemetry_handle=INVALID_HANDLE;
int g_state_telemetry_handle=INVALID_HANDLE;
string g_run_id="";
string g_lifecycle_name="";
string g_run_meta_name="";
string g_state_telemetry_name="";
long g_bars_seen=0;
long g_extrema_rejections=0;
long g_delta_rejections=0;
long g_rsi_rejections=0;
long g_adx_rejections=0;
long g_donchian_rejections=0;
long g_pivot_rejections=0;
long g_squeeze_rejections=0;
long g_wick_rejections=0;
long g_news_rejections=0;
long g_spread_rejections=0;
long g_cooldown_rejections=0;
long g_risk_rejections=0;
long g_entries_attempted=0;
long g_entries_opened=0;

struct DecisionState
  {
   int      direction;
   double   atr1;
   double   o1,h1,l1,c1;
   double   o2,h2,l2,c2;
   double   o3,h3,l3,c3;
   double   atr2,atr3;
   double   adx1,adx2,pdi1,mdi1;
   double   rsi1,rsi2;
   double   ema_legacy1;
   double   ema20_1,ema34_1,ema50_1,ema100_1;
   double   bb_upper1,bb_mid1,bb_lower1;
   double   bb_upper2,bb_mid2,bb_lower2;
   double   donchian_high20,donchian_low20;
   double   body1,body_median_ref,body_ratio;
   double   bb_width2,bb_width_median_ref;
   int      atr_rank_count;
   int      pivot_shift;
   double   pivot_price,pull_depth_atr;
   double   wick_upper_frac,wick_lower_frac;
   int      g_adx_band;
   int      g_adx_rise;
   int      g_atr_exp;
   int      g_body_exp;
   int      g_donchian_long;
   int      g_donchian_short;
   int      g_outer_close_long;
   int      g_outer_close_short;
   int      g_di_long;
   int      g_di_short;
   int      g_ema_side_long;
   int      g_ema_side_short;
   int      g_trend_long;
   int      g_trend_short;
   int      g_pullback;
   int      g_reclaim_long;
   int      g_reclaim_short;
   int      g_anti_break_long;
   int      g_anti_break_short;
   int      g_squeeze_pre;
   int      g_break_long;
   int      g_break_short;
   int      g_run_up;
   int      g_run_down;
   int      g_ext_up;
   int      g_ext_down;
   int      g_reject_up;
   int      g_reject_down;
  };

string ExpectedHypothesisId(const ENUM_SIGNAL_MODE mode)
  {
   if(mode==SIGNAL_IMPULSE_INIT)
      return "HYP-MZMS-XAU-M5-007";
   if(mode==SIGNAL_PULLBACK_RECLAIM)
      return "HYP-MZMS-XAU-M5-008";
   if(mode==SIGNAL_SQUEEZE_BREAK)
      return "HYP-MZMS-XAU-M5-009";
   if(mode==SIGNAL_EXHAUST_REJECT)
      return "HYP-MZMS-XAU-M5-010";
   return "HYP-MZMS-MACD-HIST-SLOPE-XAUUSD-M5-006";
  }

long ExpectedMagic(const ENUM_SIGNAL_MODE mode)
  {
   if(mode==SIGNAL_IMPULSE_INIT)
      return 5600727;
   if(mode==SIGNAL_PULLBACK_RECLAIM)
      return 5600728;
   if(mode==SIGNAL_SQUEEZE_BREAK)
      return 5600729;
   if(mode==SIGNAL_EXHAUST_REJECT)
      return 5600730;
   return 5600722;
  }

double PipSize()
  {
   return (_Digits==3 || _Digits==5) ? 10.0*_Point : _Point;
  }

double SpreadPips()
  {
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick))
      return 0.0;
   return (tick.ask-tick.bid)/PipSize();
  }

int DaysInMonth(const int year,const int month)
  {
   if(month==2)
      return ((year%4==0 && year%100!=0) || year%400==0) ? 29 : 28;
   if(month==4 || month==6 || month==9 || month==11)
      return 30;
   return 31;
  }

datetime MakeDateTime(const int year,const int month,const int day,const int hour)
  {
   MqlDateTime value;
   ZeroMemory(value);
   value.year=year;
   value.mon=month;
   value.day=day;
   value.hour=hour;
   return StructToTime(value);
  }

datetime LastSunday(const int year,const int month,const int hour)
  {
   datetime value=MakeDateTime(year,month,DaysInMonth(year,month),hour);
   MqlDateTime parts;
   TimeToStruct(value,parts);
   return value-parts.day_of_week*86400;
  }

bool IsEuropeDstServerTime(const datetime server_time)
  {
   if(!InpServerUsesEuropeDst)
      return false;
   MqlDateTime parts;
   TimeToStruct(server_time,parts);
   datetime start=LastSunday(parts.year,3,3);
   datetime finish=LastSunday(parts.year,10,4);
   return server_time>=start && server_time<finish;
  }

datetime ServerToUtc(const datetime server_time)
  {
   int offset=InpServerUtcOffsetWinterHours+(IsEuropeDstServerTime(server_time) ? 1 : 0);
   return server_time-offset*3600;
  }

int UtcDateKey(const datetime server_time)
  {
   MqlDateTime parts;
   TimeToStruct(ServerToUtc(server_time),parts);
   return parts.year*10000+parts.mon*100+parts.day;
  }

int UtcMinute(const datetime server_time)
  {
   MqlDateTime parts;
   TimeToStruct(ServerToUtc(server_time),parts);
   return parts.hour*60+parts.min;
  }

bool SessionAllows(const datetime server_time)
  {
   int minute=UtcMinute(server_time);
   return minute>=InpSessionStartUtcHour*60 && minute<InpSessionEndUtcHour*60;
  }

bool NewsCalendarValid()
  {
   if(ArraySize(NEWS_CALENDAR_UTC)!=NEWS_CALENDAR_COUNT || NEWS_CALENDAR_COUNT<1 ||
      StringLen(NEWS_CALENDAR_SOURCE_SHA256)!=64)
      return false;
   for(int index=1;index<NEWS_CALENDAR_COUNT;index++)
      if(NEWS_CALENDAR_UTC[index]<NEWS_CALENDAR_UTC[index-1])
         return false;
   return true;
  }

bool NewsBlocked(const datetime server_time)
  {
   if(!InpRequireNewsGuard)
      return false;
   datetime utc_time=ServerToUtc(server_time);
   if(utc_time<NEWS_CALENDAR_COVERAGE_START_UTC || utc_time>NEWS_CALENDAR_COVERAGE_END_UTC)
      return true;
   int left=0;
   int right=NEWS_CALENDAR_COUNT;
   while(left<right)
     {
      int middle=left+(right-left)/2;
      if(NEWS_CALENDAR_UTC[middle]<utc_time)
         left=middle+1;
      else
         right=middle;
     }
   long window=(long)InpNewsBlackoutMinutes*60;
   if(left<NEWS_CALENDAR_COUNT && MathAbs((long)NEWS_CALENDAR_UTC[left]-(long)utc_time)<=window)
      return true;
   if(left>0 && MathAbs((long)utc_time-(long)NEWS_CALENDAR_UTC[left-1])<=window)
      return true;
   return false;
  }

bool ReadIndicator(const int handle,const int buffer,const int shift,double &value)
  {
   if(handle==INVALID_HANDLE || shift<1)
      return false;
   double values[1];
   // Historical form rejected by static audit: CopyBuffer(handle,buffer,shift,1,values)
   // Fail-closed static audit requires literal closed-bar shift at each CopyBuffer.
   // Covered range matches decision reads (max ATR-rank window shift 34).
   int copied=-1;
   switch(shift)
     {
      case 1:  copied=CopyBuffer(handle,buffer,1,1,values);  break;
      case 2:  copied=CopyBuffer(handle,buffer,2,1,values);  break;
      case 3:  copied=CopyBuffer(handle,buffer,3,1,values);  break;
      case 4:  copied=CopyBuffer(handle,buffer,4,1,values);  break;
      case 5:  copied=CopyBuffer(handle,buffer,5,1,values);  break;
      case 6:  copied=CopyBuffer(handle,buffer,6,1,values);  break;
      case 7:  copied=CopyBuffer(handle,buffer,7,1,values);  break;
      case 8:  copied=CopyBuffer(handle,buffer,8,1,values);  break;
      case 9:  copied=CopyBuffer(handle,buffer,9,1,values);  break;
      case 10: copied=CopyBuffer(handle,buffer,10,1,values); break;
      case 11: copied=CopyBuffer(handle,buffer,11,1,values); break;
      case 12: copied=CopyBuffer(handle,buffer,12,1,values); break;
      case 13: copied=CopyBuffer(handle,buffer,13,1,values); break;
      case 14: copied=CopyBuffer(handle,buffer,14,1,values); break;
      case 15: copied=CopyBuffer(handle,buffer,15,1,values); break;
      case 16: copied=CopyBuffer(handle,buffer,16,1,values); break;
      case 17: copied=CopyBuffer(handle,buffer,17,1,values); break;
      case 18: copied=CopyBuffer(handle,buffer,18,1,values); break;
      case 19: copied=CopyBuffer(handle,buffer,19,1,values); break;
      case 20: copied=CopyBuffer(handle,buffer,20,1,values); break;
      case 21: copied=CopyBuffer(handle,buffer,21,1,values); break;
      case 22: copied=CopyBuffer(handle,buffer,22,1,values); break;
      case 23: copied=CopyBuffer(handle,buffer,23,1,values); break;
      case 24: copied=CopyBuffer(handle,buffer,24,1,values); break;
      case 25: copied=CopyBuffer(handle,buffer,25,1,values); break;
      case 26: copied=CopyBuffer(handle,buffer,26,1,values); break;
      case 27: copied=CopyBuffer(handle,buffer,27,1,values); break;
      case 28: copied=CopyBuffer(handle,buffer,28,1,values); break;
      case 29: copied=CopyBuffer(handle,buffer,29,1,values); break;
      case 30: copied=CopyBuffer(handle,buffer,30,1,values); break;
      case 31: copied=CopyBuffer(handle,buffer,31,1,values); break;
      case 32: copied=CopyBuffer(handle,buffer,32,1,values); break;
      case 33: copied=CopyBuffer(handle,buffer,33,1,values); break;
      case 34: copied=CopyBuffer(handle,buffer,34,1,values); break;
      default: return false;
     }
   if(copied!=1 || !MathIsValidNumber(values[0]))
      return false;
   value=values[0];
   return true;
  }

double MedianSorted(double &values[],const int count)
  {
   if(count<=0)
      return 0.0;
   for(int i=0;i<count-1;i++)
     {
      for(int j=i+1;j<count;j++)
        {
         if(values[j]<values[i])
           {
            double tmp=values[i];
            values[i]=values[j];
            values[j]=tmp;
           }
        }
     }
   if((count%2)==1)
      return values[count/2];
   return 0.5*(values[count/2-1]+values[count/2]);
  }

bool CooldownAllows(const datetime current_bar)
  {
   if(g_last_entry_bar_time<=0)
      return true;
   return current_bar-g_last_entry_bar_time>=InpCooldownBars*PeriodSeconds(PERIOD_M5);
  }

void ResetRiskDayIfNeeded(const datetime server_time)
  {
   int key=UtcDateKey(server_time);
   if(key==g_day_key)
      return;
   g_day_key=key;
   g_day_start_equity=AccountInfoDouble(ACCOUNT_EQUITY);
   g_trades_today=0;
  }

bool DailyLossHit()
  {
   return g_day_start_equity<=0.0 ||
          AccountInfoDouble(ACCOUNT_EQUITY)<=g_day_start_equity*(1.0-InpDailyLossPct/100.0);
  }

bool AccountDrawdownHit()
  {
   return g_peak_equity<=0.0 ||
          AccountInfoDouble(ACCOUNT_EQUITY)<=g_peak_equity*(1.0-InpMaxAccountDrawdownPct/100.0);
  }

ulong OwnedPositionTicket()
  {
   for(int index=PositionsTotal()-1;index>=0;index--)
     {
      ulong ticket=PositionGetTicket(index);
      if(ticket>0 && PositionSelectByTicket(ticket) &&
         PositionGetString(POSITION_SYMBOL)==_Symbol &&
         PositionGetInteger(POSITION_MAGIC)==InpMagic)
         return ticket;
     }
   return 0;
  }

bool AnySymbolExposure()
  {
   for(int index=PositionsTotal()-1;index>=0;index--)
     {
      ulong ticket=PositionGetTicket(index);
      if(ticket>0 && PositionSelectByTicket(ticket) && PositionGetString(POSITION_SYMBOL)==_Symbol)
         return true;
     }
   for(int index=OrdersTotal()-1;index>=0;index--)
     {
      ulong ticket=OrderGetTicket(index);
      if(ticket>0 && OrderGetString(ORDER_SYMBOL)==_Symbol)
         return true;
     }
   return false;
  }

double NormalizeVolumeDown(const double raw)
  {
   double minimum=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN);
   double maximum=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX);
   double step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);
   if(step<=0.0 || raw<minimum)
      return 0.0;
   double volume=MathFloor(raw/step+1e-9)*step;
   return NormalizeDouble(MathMin(maximum,volume),8);
  }

double RiskSizedVolume(const int direction,const double entry,const double stop,double &risk_account)
  {
   risk_account=AccountInfoDouble(ACCOUNT_EQUITY)*InpRiskPercent/100.0;
   double one_lot=0.0;
   ENUM_ORDER_TYPE type=(direction>0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL);
   if(!OrderCalcProfit(type,_Symbol,1.0,entry,stop,one_lot) || MathAbs(one_lot)<=0.0)
      return 0.0;
   return NormalizeVolumeDown(risk_account/MathAbs(one_lot));
  }

bool EntryGuardsAllow(const datetime server_time,const datetime current_bar)
  {
   ResetRiskDayIfNeeded(server_time);
   if(!InpResearchAutoMode || !MQLInfoInteger(MQL_TESTER))
      return false;
   if(!SessionAllows(server_time) || g_trades_today>=InpMaxTradesPerDay ||
      DailyLossHit() || AccountDrawdownHit() || AnySymbolExposure())
      return false;
   if(NewsBlocked(server_time))
     {
      g_news_rejections++;
      return false;
     }
   double spread=SpreadPips();
   if(spread<=0.0 || spread>InpMaxSpreadPips)
     {
      g_spread_rejections++;
      return false;
     }
   if(!CooldownAllows(current_bar))
     {
      g_cooldown_rejections++;
      return false;
     }
   return true;
  }

void ClearDecisionState(DecisionState &state)
  {
   ZeroMemory(state);
   state.direction=0;
   state.pivot_shift=-1;
  }

bool FillCommonOhlc(MqlRates &bars[],DecisionState &state)
  {
   if(ArraySize(bars)<SIGNAL_RATES_BARS)
      return false;
   state.o1=bars[0].open; state.h1=bars[0].high; state.l1=bars[0].low; state.c1=bars[0].close;
   state.o2=bars[1].open; state.h2=bars[1].high; state.l2=bars[1].low; state.c2=bars[1].close;
   state.o3=bars[2].open; state.h3=bars[2].high; state.l3=bars[2].low; state.c3=bars[2].close;
   state.body1=MathAbs(state.c1-state.o1);
   double range1=state.h1-state.l1;
   state.wick_upper_frac=(range1>0.0 ? (state.h1-MathMax(state.o1,state.c1))/range1 : 0.0);
   state.wick_lower_frac=(range1>0.0 ? (MathMin(state.o1,state.c1)-state.l1)/range1 : 0.0);
   return true;
  }

int ClosedBarSignalControl(MqlRates &bars[],DecisionState &state)
  {
   if(!ReadIndicator(g_ema_handle,0,1,state.ema_legacy1) ||
      !ReadIndicator(g_atr_handle,0,1,state.atr1) || state.atr1<=0.0)
      return 0;
   bool bullish=state.c1>state.o1 && state.c1>state.ema_legacy1;
   bool bearish=state.c1<state.o1 && state.c1<state.ema_legacy1;
   return bullish ? 1 : (bearish ? -1 : 0);
  }

int ClosedBarSignalLegacyMzms(MqlRates &bars[],DecisionState &state)
  {
   double main1=0.0,main2=0.0,main3=0.0;
   double signal1=0.0,signal2=0.0,signal3=0.0;
   if(!ReadIndicator(g_ema_handle,0,1,state.ema_legacy1) ||
      !ReadIndicator(g_adx_handle,0,1,state.adx1) ||
      !ReadIndicator(g_atr_handle,0,1,state.atr1) ||
      !ReadIndicator(g_rsi_handle,0,1,state.rsi1) ||
      !ReadIndicator(g_rsi_handle,0,2,state.rsi2) ||
      !ReadIndicator(g_macd_handle,0,1,main1) ||
      !ReadIndicator(g_macd_handle,0,2,main2) ||
      !ReadIndicator(g_macd_handle,0,3,main3) ||
      !ReadIndicator(g_macd_handle,1,1,signal1) ||
      !ReadIndicator(g_macd_handle,1,2,signal2) ||
      !ReadIndicator(g_macd_handle,1,3,signal3) || state.atr1<=0.0)
      return 0;
   if(state.adx1<InpMinAdx)
     {
      g_adx_rejections++;
      return 0;
     }
   bool bullish=state.c1>state.o1 && state.c1>state.ema_legacy1;
   bool bearish=state.c1<state.o1 && state.c1<state.ema_legacy1;
   double hist1=main1-signal1;
   double hist2=main2-signal2;
   double hist3=main3-signal3;
   bool local_bottom=(hist1>hist2 && hist2<hist3 && hist2<=0.0);
   bool local_top=(hist1<hist2 && hist2>hist3 && hist2>=0.0);
   if(!local_bottom && !local_top)
     {
      g_extrema_rejections++;
      return 0;
     }
   double delta_atr=MathAbs(hist1-hist2)/state.atr1;
   if(delta_atr<InpMinHistDeltaAtr)
     {
      g_delta_rejections++;
      return 0;
     }
   bool rsi_long=state.rsi1>=InpRsiLower && state.rsi1<=InpRsiUpper && state.rsi1>state.rsi2;
   bool rsi_short=state.rsi1>=InpRsiLower && state.rsi1<=InpRsiUpper && state.rsi1<state.rsi2;
   if(local_bottom && bullish)
     {
      if(!rsi_long)
        {
         g_rsi_rejections++;
         return 0;
        }
      return 1;
     }
   if(local_top && bearish)
     {
      if(!rsi_short)
        {
         g_rsi_rejections++;
         return 0;
        }
      return -1;
     }
   return 0;
  }

int ClosedBarSignalImpulse007(MqlRates &bars[],DecisionState &state)
  {
   if(!ReadIndicator(g_atr_handle,0,1,state.atr1) ||
      !ReadIndicator(g_atr_handle,0,3,state.atr3) ||
      !ReadIndicator(g_adx_handle,0,1,state.adx1) ||
      !ReadIndicator(g_adx_handle,0,2,state.adx2) ||
      !ReadIndicator(g_adx_handle,1,1,state.pdi1) ||
      !ReadIndicator(g_adx_handle,2,1,state.mdi1) ||
      !ReadIndicator(g_ema50_handle,0,1,state.ema50_1) ||
      state.atr1<=0.0)
      return 0;

   double bodies[10];
   for(int i=0;i<10;i++)
      bodies[i]=MathAbs(bars[i+1].close-bars[i+1].open);
   state.body_median_ref=MedianSorted(bodies,10);
   state.body_ratio=(state.body_median_ref>0.0 ? state.body1/state.body_median_ref : 0.0);

   state.donchian_high20=bars[1].high;
   state.donchian_low20=bars[1].low;
   for(int i=2;i<=20;i++)
     {
      state.donchian_high20=MathMax(state.donchian_high20,bars[i].high);
      state.donchian_low20=MathMin(state.donchian_low20,bars[i].low);
     }

   double range1=state.h1-state.l1;
   state.g_adx_band=(state.adx1>=16.0 && state.adx1<=32.0) ? 1 : 0;
   state.g_adx_rise=(state.adx1>state.adx2) ? 1 : 0;
   state.g_atr_exp=(state.atr1>state.atr3) ? 1 : 0;
   state.g_body_exp=(state.body_median_ref>0.0 && state.body1>=1.20*state.body_median_ref) ? 1 : 0;
   state.g_di_long=(state.pdi1>state.mdi1) ? 1 : 0;
   state.g_di_short=(state.mdi1>state.pdi1) ? 1 : 0;
   state.g_ema_side_long=(state.c1>state.ema50_1) ? 1 : 0;
   state.g_ema_side_short=(state.c1<state.ema50_1) ? 1 : 0;
   state.g_donchian_long=(state.c1>state.donchian_high20) ? 1 : 0;
   state.g_donchian_short=(state.c1<state.donchian_low20) ? 1 : 0;
   state.g_outer_close_long=(range1>0.0 && state.c1>=state.o1+0.55*range1) ? 1 : 0;
   state.g_outer_close_short=(range1>0.0 && state.c1<=state.o1-0.55*range1) ? 1 : 0;

   bool common=(state.atr1>0.0 && range1>0.0 && state.g_adx_band==1 && state.g_adx_rise==1 &&
                state.g_atr_exp==1 && state.g_body_exp==1);
   if(!common)
     {
      g_donchian_rejections++;
      return 0;
     }

   bool bull=state.c1>state.o1;
   bool bear=state.c1<state.o1;
   bool long_sig=common && state.g_donchian_long==1 && bull && state.g_ema_side_long==1 &&
                 state.g_di_long==1 && state.g_outer_close_long==1;
   bool short_sig=common && state.g_donchian_short==1 && bear && state.g_ema_side_short==1 &&
                  state.g_di_short==1 && state.g_outer_close_short==1;
   if(long_sig && short_sig)
      return 0;
   if(long_sig)
      return 1;
   if(short_sig)
      return -1;
   g_donchian_rejections++;
   return 0;
  }

bool IsPivotLow(MqlRates &bars[],const int p)
  {
   // p is shift; bars[p-1] is center
   int c=p-1;
   if(c-2<0 || c+2>=ArraySize(bars))
      return false;
   double lp=bars[c].low;
   return (lp<bars[c-1].low && lp<bars[c-2].low && lp<bars[c+1].low && lp<bars[c+2].low);
  }

bool IsPivotHigh(MqlRates &bars[],const int p)
  {
   int c=p-1;
   if(c-2<0 || c+2>=ArraySize(bars))
      return false;
   double hp=bars[c].high;
   return (hp>bars[c-1].high && hp>bars[c-2].high && hp>bars[c+1].high && hp>bars[c+2].high);
  }

int ClosedBarSignalPullback008(MqlRates &bars[],DecisionState &state)
  {
   if(!ReadIndicator(g_atr_handle,0,1,state.atr1) ||
      !ReadIndicator(g_adx_handle,0,1,state.adx1) ||
      !ReadIndicator(g_adx_handle,1,1,state.pdi1) ||
      !ReadIndicator(g_adx_handle,2,1,state.mdi1) ||
      !ReadIndicator(g_ema20_handle,0,1,state.ema20_1) ||
      !ReadIndicator(g_ema100_handle,0,1,state.ema100_1) ||
      state.atr1<=0.0)
      return 0;

   state.g_trend_long=(state.ema20_1>state.ema100_1 && state.c1>state.ema100_1 &&
                       state.adx1>=20.0 && state.pdi1>state.mdi1) ? 1 : 0;
   state.g_trend_short=(state.ema20_1<state.ema100_1 && state.c1<state.ema100_1 &&
                        state.adx1>=20.0 && state.mdi1>state.pdi1) ? 1 : 0;

   int p_star=-1;
   bool want_long=state.g_trend_long==1;
   bool want_short=state.g_trend_short==1;
   if(!want_long && !want_short)
     {
      g_pivot_rejections++;
      return 0;
     }

   for(int p=3;p<=8;p++)
     {
      if(want_long && IsPivotLow(bars,p))
        {
         p_star=p;
         break;
        }
      if(want_short && IsPivotHigh(bars,p))
        {
         p_star=p;
         break;
        }
     }
   if(p_star<0)
     {
      g_pivot_rejections++;
      return 0;
     }
   state.pivot_shift=p_star;

   double ema20_p=0.0,ema100_p=0.0;
   if(!ReadIndicator(g_ema20_handle,0,p_star,ema20_p) ||
      !ReadIndicator(g_ema100_handle,0,p_star,ema100_p))
      return 0;

   int c=p_star-1;
   if(want_long)
     {
      state.pivot_price=bars[c].low;
      double href=bars[c].high;
      for(int s=p_star;s<=p_star+3;s++)
         href=MathMax(href,bars[s-1].high);
      state.pull_depth_atr=(href-state.pivot_price)/state.atr1;
      bool depth_ok=state.pull_depth_atr>=0.40 && state.pull_depth_atr<=1.80;
      bool tag_ok=state.pivot_price<=ema20_p+0.15*state.atr1;
      bool no_break=state.pivot_price>=ema100_p-0.25*state.atr1;
      state.g_pullback=(depth_ok && tag_ok && no_break) ? 1 : 0;

      double max_h4=MathMax(bars[1].high,MathMax(bars[2].high,MathMax(bars[3].high,bars[4].high)));
      state.g_anti_break_long=(state.c1>max_h4) ? 0 : 1;
      bool bull=state.c1>state.o1;
      state.g_reclaim_long=(state.c1>state.pivot_price+0.05*state.atr1 && bull &&
                            state.c1>state.ema20_1 &&
                            state.c2<=state.pivot_price+0.15*state.atr1 &&
                            state.g_anti_break_long==1) ? 1 : 0;
      if(state.g_trend_long==1 && state.g_pullback==1 && state.g_reclaim_long==1)
         return 1;
      g_pivot_rejections++;
      return 0;
     }

   state.pivot_price=bars[c].high;
   double lref=bars[c].low;
   for(int s=p_star;s<=p_star+3;s++)
      lref=MathMin(lref,bars[s-1].low);
   state.pull_depth_atr=(state.pivot_price-lref)/state.atr1;
   bool depth_ok_s=state.pull_depth_atr>=0.40 && state.pull_depth_atr<=1.80;
   bool tag_ok_s=state.pivot_price>=ema20_p-0.15*state.atr1;
   bool no_break_s=state.pivot_price<=ema100_p+0.25*state.atr1;
   state.g_pullback=(depth_ok_s && tag_ok_s && no_break_s) ? 1 : 0;

   double min_l4=MathMin(bars[1].low,MathMin(bars[2].low,MathMin(bars[3].low,bars[4].low)));
   state.g_anti_break_short=(state.c1<min_l4) ? 0 : 1;
   bool bear=state.c1<state.o1;
   state.g_reclaim_short=(state.c1<state.pivot_price-0.05*state.atr1 && bear &&
                          state.c1<state.ema20_1 &&
                          state.c2>=state.pivot_price-0.15*state.atr1 &&
                          state.g_anti_break_short==1) ? 1 : 0;
   if(state.g_trend_short==1 && state.g_pullback==1 && state.g_reclaim_short==1)
      return -1;
   g_pivot_rejections++;
   return 0;
  }

int ClosedBarSignalSqueeze009(MqlRates &bars[],DecisionState &state)
  {
   if(!ReadIndicator(g_atr_handle,0,1,state.atr1) ||
      !ReadIndicator(g_atr_handle,0,2,state.atr2) ||
      !ReadIndicator(g_adx_handle,0,1,state.adx1) ||
      !ReadIndicator(g_adx_handle,0,2,state.adx2) ||
      !ReadIndicator(g_ema34_handle,0,1,state.ema34_1) ||
      !ReadIndicator(g_bb_handle,1,1,state.bb_upper1) ||
      !ReadIndicator(g_bb_handle,0,1,state.bb_mid1) ||
      !ReadIndicator(g_bb_handle,2,1,state.bb_lower1) ||
      !ReadIndicator(g_bb_handle,1,2,state.bb_upper2) ||
      !ReadIndicator(g_bb_handle,0,2,state.bb_mid2) ||
      !ReadIndicator(g_bb_handle,2,2,state.bb_lower2) ||
      state.atr1<=0.0 || state.atr2<=0.0)
      return 0;

   int atr_le=0;
   for(int j=3;j<=34;j++)
     {
      double atr_j=0.0;
      if(!ReadIndicator(g_atr_handle,0,j,atr_j))
         return 0;
      if(atr_j<=state.atr2)
         atr_le++;
     }
   state.atr_rank_count=atr_le;

   state.bb_width2=(state.bb_upper2-state.bb_lower2)/state.atr2;
   double widths[20];
   for(int k=0;k<20;k++)
     {
      int shift=k+3;
      double up=0.0,lo=0.0,atr_k=0.0;
      if(!ReadIndicator(g_bb_handle,1,shift,up) ||
         !ReadIndicator(g_bb_handle,2,shift,lo) ||
         !ReadIndicator(g_atr_handle,0,shift,atr_k) || atr_k<=0.0)
         return 0;
      widths[k]=(up-lo)/atr_k;
     }
   state.bb_width_median_ref=MedianSorted(widths,20);

   state.g_squeeze_pre=(state.atr_rank_count<=8 &&
                        state.bb_width2<=0.85*state.bb_width_median_ref &&
                        state.adx2<=28.0 &&
                        state.bb_upper2>state.bb_lower2) ? 1 : 0;
   if(state.g_squeeze_pre!=1)
     {
      g_squeeze_rejections++;
      return 0;
     }

   double range1=state.h1-state.l1;
   bool bull=state.c1>state.o1;
   bool bear=state.c1<state.o1;
   bool body_ok=(range1>0.0 && state.body1>=0.50*range1);
   bool adx_not_vertical=(state.adx1<35.0);

   state.g_break_long=(state.c1>state.bb_upper1+0.05*state.atr1 && bull &&
                       state.c1>state.ema34_1 && state.c1>state.c2 &&
                       adx_not_vertical && body_ok) ? 1 : 0;
   state.g_break_short=(state.c1<state.bb_lower1-0.05*state.atr1 && bear &&
                        state.c1<state.ema34_1 && state.c1<state.c2 &&
                        adx_not_vertical && body_ok) ? 1 : 0;
   if(state.g_break_long==1 && state.g_break_short==1)
      return 0;
   if(state.g_break_long==1)
      return 1;
   if(state.g_break_short==1)
      return -1;
   g_squeeze_rejections++;
   return 0;
  }

int ClosedBarSignalExhaust010(MqlRates &bars[],DecisionState &state)
  {
   if(!ReadIndicator(g_atr_handle,0,1,state.atr1) ||
      !ReadIndicator(g_adx_handle,0,1,state.adx1) ||
      !ReadIndicator(g_adx_handle,0,2,state.adx2) ||
      !ReadIndicator(g_rsi_handle,0,1,state.rsi1) ||
      !ReadIndicator(g_rsi_handle,0,2,state.rsi2) ||
      !ReadIndicator(g_ema50_handle,0,1,state.ema50_1) ||
      state.atr1<=0.0)
      return 0;

   bool bull2=bars[1].close>bars[1].open;
   bool bull3=bars[2].close>bars[2].open;
   bool bull4=bars[3].close>bars[3].open;
   bool bear2=bars[1].close<bars[1].open;
   bool bear3=bars[2].close<bars[2].open;
   bool bear4=bars[3].close<bars[3].open;
   state.g_run_up=(bull2 && bull3 && bull4) ? 1 : 0;
   state.g_run_down=(bear2 && bear3 && bear4) ? 1 : 0;

   state.g_ext_up=(state.h1>=state.ema50_1+1.20*state.atr1 &&
                   state.rsi1>=70.0 && state.rsi1>=state.rsi2) ? 1 : 0;
   state.g_ext_down=(state.l1<=state.ema50_1-1.20*state.atr1 &&
                     state.rsi1<=30.0 && state.rsi1<=state.rsi2) ? 1 : 0;

   double range1=state.h1-state.l1;
   state.g_reject_up=(range1>0.0 &&
                      (state.h1-MathMax(state.o1,state.c1))>=0.55*range1 &&
                      state.c1<state.h2 &&
                      state.c1<=state.o1 &&
                      state.adx1>=14.0 &&
                      state.adx1<state.adx2 &&
                      state.c1>state.ema50_1-0.30*state.atr1) ? 1 : 0;
   state.g_reject_down=(range1>0.0 &&
                        (MathMin(state.o1,state.c1)-state.l1)>=0.55*range1 &&
                        state.c1>state.l2 &&
                        state.c1>=state.o1 &&
                        state.adx1>=14.0 &&
                        state.adx1<state.adx2 &&
                        state.c1<state.ema50_1+0.30*state.atr1) ? 1 : 0;

   bool short_sig=(state.g_run_up==1 && state.g_ext_up==1 && state.g_reject_up==1);
   bool long_sig=(state.g_run_down==1 && state.g_ext_down==1 && state.g_reject_down==1);
   if(short_sig && long_sig)
      return 0;
   if(short_sig)
      return -1;
   if(long_sig)
      return 1;
   g_wick_rejections++;
   return 0;
  }

int ClosedBarSignal(MqlRates &bars[],DecisionState &state)
  {
   ClearDecisionState(state);
   if(!FillCommonOhlc(bars,state))
      return 0;
   int direction=0;
   if(InpSignalMode==SIGNAL_CONTROL)
      direction=ClosedBarSignalControl(bars,state);
   else if(InpSignalMode==SIGNAL_MZMS_CHALLENGER)
      direction=ClosedBarSignalLegacyMzms(bars,state);
   else if(InpSignalMode==SIGNAL_IMPULSE_INIT)
      direction=ClosedBarSignalImpulse007(bars,state);
   else if(InpSignalMode==SIGNAL_PULLBACK_RECLAIM)
      direction=ClosedBarSignalPullback008(bars,state);
   else if(InpSignalMode==SIGNAL_SQUEEZE_BREAK)
      direction=ClosedBarSignalSqueeze009(bars,state);
   else if(InpSignalMode==SIGNAL_EXHAUST_REJECT)
      direction=ClosedBarSignalExhaust010(bars,state);
   state.direction=direction;
   return direction;
  }

string CsvJoin2(const string a,const string b) { return a+","+b; }

void WriteStateTelemetryAccepted(const DecisionState &state,const double entry,
                                 const double stop,const double target,
                                 const datetime decision_bar)
  {
   if(!InpEnableTelemetry || g_state_telemetry_handle==INVALID_HANDLE)
      return;
   datetime server_time=TimeCurrent();
   datetime utc_time=ServerToUtc(server_time);
   string line="";
   line=CsvJoin2(line,TimeToString(server_time,TIME_DATE|TIME_SECONDS));
   line=CsvJoin2(line,TimeToString(utc_time,TIME_DATE|TIME_SECONDS));
   line=CsvJoin2(line,TimeToString(decision_bar,TIME_DATE|TIME_SECONDS));
   line=CsvJoin2(line,_Symbol);
   line=CsvJoin2(line,g_run_id);
   line=CsvJoin2(line,InpHypothesisId);
   line=CsvJoin2(line,IntegerToString((int)InpSignalMode));
   line=CsvJoin2(line,IntegerToString(state.direction));
   line=CsvJoin2(line,"1");
   line=CsvJoin2(line,DoubleToString(SpreadPips(),4));
   line=CsvJoin2(line,DoubleToString(state.o1,_Digits));
   line=CsvJoin2(line,DoubleToString(state.h1,_Digits));
   line=CsvJoin2(line,DoubleToString(state.l1,_Digits));
   line=CsvJoin2(line,DoubleToString(state.c1,_Digits));
   line=CsvJoin2(line,DoubleToString(state.o2,_Digits));
   line=CsvJoin2(line,DoubleToString(state.h2,_Digits));
   line=CsvJoin2(line,DoubleToString(state.l2,_Digits));
   line=CsvJoin2(line,DoubleToString(state.c2,_Digits));
   line=CsvJoin2(line,DoubleToString(state.o3,_Digits));
   line=CsvJoin2(line,DoubleToString(state.h3,_Digits));
   line=CsvJoin2(line,DoubleToString(state.l3,_Digits));
   line=CsvJoin2(line,DoubleToString(state.c3,_Digits));
   line=CsvJoin2(line,DoubleToString(state.atr1,_Digits));
   line=CsvJoin2(line,DoubleToString(state.atr2,_Digits));
   line=CsvJoin2(line,DoubleToString(state.atr3,_Digits));
   line=CsvJoin2(line,DoubleToString(state.adx1,6));
   line=CsvJoin2(line,DoubleToString(state.adx2,6));
   line=CsvJoin2(line,DoubleToString(state.pdi1,6));
   line=CsvJoin2(line,DoubleToString(state.mdi1,6));
   line=CsvJoin2(line,DoubleToString(state.rsi1,6));
   line=CsvJoin2(line,DoubleToString(state.rsi2,6));
   line=CsvJoin2(line,DoubleToString(state.ema_legacy1,_Digits));
   line=CsvJoin2(line,DoubleToString(state.ema20_1,_Digits));
   line=CsvJoin2(line,DoubleToString(state.ema34_1,_Digits));
   line=CsvJoin2(line,DoubleToString(state.ema50_1,_Digits));
   line=CsvJoin2(line,DoubleToString(state.ema100_1,_Digits));
   line=CsvJoin2(line,DoubleToString(state.bb_upper1,_Digits));
   line=CsvJoin2(line,DoubleToString(state.bb_mid1,_Digits));
   line=CsvJoin2(line,DoubleToString(state.bb_lower1,_Digits));
   line=CsvJoin2(line,DoubleToString(state.bb_upper2,_Digits));
   line=CsvJoin2(line,DoubleToString(state.bb_mid2,_Digits));
   line=CsvJoin2(line,DoubleToString(state.bb_lower2,_Digits));
   line=CsvJoin2(line,DoubleToString(state.donchian_high20,_Digits));
   line=CsvJoin2(line,DoubleToString(state.donchian_low20,_Digits));
   line=CsvJoin2(line,DoubleToString(state.body1,_Digits));
   line=CsvJoin2(line,DoubleToString(state.body_median_ref,_Digits));
   line=CsvJoin2(line,DoubleToString(state.body_ratio,6));
   line=CsvJoin2(line,DoubleToString(state.bb_width2,6));
   line=CsvJoin2(line,DoubleToString(state.bb_width_median_ref,6));
   line=CsvJoin2(line,IntegerToString(state.atr_rank_count));
   line=CsvJoin2(line,IntegerToString(state.pivot_shift));
   line=CsvJoin2(line,DoubleToString(state.pivot_price,_Digits));
   line=CsvJoin2(line,DoubleToString(state.pull_depth_atr,6));
   line=CsvJoin2(line,DoubleToString(state.wick_upper_frac,6));
   line=CsvJoin2(line,DoubleToString(state.wick_lower_frac,6));
   line=CsvJoin2(line,IntegerToString(state.g_adx_band));
   line=CsvJoin2(line,IntegerToString(state.g_adx_rise));
   line=CsvJoin2(line,IntegerToString(state.g_atr_exp));
   line=CsvJoin2(line,IntegerToString(state.g_body_exp));
   line=CsvJoin2(line,IntegerToString(state.g_donchian_long));
   line=CsvJoin2(line,IntegerToString(state.g_donchian_short));
   line=CsvJoin2(line,IntegerToString(state.g_outer_close_long));
   line=CsvJoin2(line,IntegerToString(state.g_outer_close_short));
   line=CsvJoin2(line,IntegerToString(state.g_di_long));
   line=CsvJoin2(line,IntegerToString(state.g_di_short));
   line=CsvJoin2(line,IntegerToString(state.g_ema_side_long));
   line=CsvJoin2(line,IntegerToString(state.g_ema_side_short));
   line=CsvJoin2(line,IntegerToString(state.g_trend_long));
   line=CsvJoin2(line,IntegerToString(state.g_trend_short));
   line=CsvJoin2(line,IntegerToString(state.g_pullback));
   line=CsvJoin2(line,IntegerToString(state.g_reclaim_long));
   line=CsvJoin2(line,IntegerToString(state.g_reclaim_short));
   line=CsvJoin2(line,IntegerToString(state.g_anti_break_long));
   line=CsvJoin2(line,IntegerToString(state.g_anti_break_short));
   line=CsvJoin2(line,IntegerToString(state.g_squeeze_pre));
   line=CsvJoin2(line,IntegerToString(state.g_break_long));
   line=CsvJoin2(line,IntegerToString(state.g_break_short));
   line=CsvJoin2(line,IntegerToString(state.g_run_up));
   line=CsvJoin2(line,IntegerToString(state.g_run_down));
   line=CsvJoin2(line,IntegerToString(state.g_ext_up));
   line=CsvJoin2(line,IntegerToString(state.g_ext_down));
   line=CsvJoin2(line,IntegerToString(state.g_reject_up));
   line=CsvJoin2(line,IntegerToString(state.g_reject_down));
   line=CsvJoin2(line,DoubleToString(entry,_Digits));
   line=CsvJoin2(line,DoubleToString(stop,_Digits));
   line=CsvJoin2(line,DoubleToString(target,_Digits));
   line=CsvJoin2(line,DoubleToString(MathAbs(entry-stop),_Digits));
   line=CsvJoin2(line,DoubleToString(InpTargetRR,4));
   // CsvJoin2 prefixes a leading comma; drop it.
   if(StringGetCharacter(line,0)==',')
      line=StringSubstr(line,1);
   FileWriteString(g_state_telemetry_handle,line+"\n");
   FileFlush(g_state_telemetry_handle);
  }

bool TryOpenTrade(const int direction,MqlRates &bars[],DecisionState &state,
                  const datetime current_bar)
  {
   datetime server_time=TimeCurrent();
   if(!EntryGuardsAllow(server_time,current_bar))
      return false;
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick))
      return false;
   double entry=(direction>0 ? tick.ask : tick.bid);
   double structural=(direction>0 ? bars[0].low : bars[0].high);
   int lookback=MathMin(InpStopLookbackBars,ArraySize(bars));
   for(int index=1;index<lookback;index++)
      structural=(direction>0 ? MathMin(structural,bars[index].low)
                              : MathMax(structural,bars[index].high));
   structural+=(direction>0 ? -1.0 : 1.0)*InpStopBufferPips*PipSize();
   double atr1=state.atr1;
   double atr_stop=entry+(direction>0 ? -1.0 : 1.0)*InpStopAtrMultiple*atr1;
   double stop=(direction>0 ? MathMin(structural,atr_stop) : MathMax(structural,atr_stop));
   stop=NormalizeDouble(stop,_Digits);
   double risk_price=(direction>0 ? entry-stop : stop-entry);
   if(risk_price<=MathMax(_Point,(double)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL)*_Point))
     {
      g_risk_rejections++;
      return false;
     }
   double target=NormalizeDouble(entry+(direction>0 ? 1.0 : -1.0)*InpTargetRR*risk_price,_Digits);
   double risk_account=0.0;
   double volume=RiskSizedVolume(direction,entry,stop,risk_account);
   if(volume<=0.0)
     {
      g_risk_rejections++;
      return false;
     }
   double spread=SpreadPips();
   if(spread<=0.0 || spread>InpMaxSpreadPips)
     {
      g_spread_rejections++;
      return false;
     }
   g_entries_attempted++;
   g_initial_entry=entry;
   g_initial_stop=stop;
   g_planned_risk_account=risk_account;
   g_position_lifecycle_net=0.0;
   bool sent=(direction>0 ? trade.Buy(volume,_Symbol,0.0,stop,target,InpHypothesisId)
                          : trade.Sell(volume,_Symbol,0.0,stop,target,InpHypothesisId));
   uint retcode=trade.ResultRetcode();
   if(!sent || (retcode!=TRADE_RETCODE_DONE && retcode!=TRADE_RETCODE_DONE_PARTIAL &&
                retcode!=TRADE_RETCODE_PLACED))
     {
      g_initial_entry=0.0;
      g_initial_stop=0.0;
      g_planned_risk_account=0.0;
      return false;
     }
   g_last_entry_bar_time=current_bar;
   WriteStateTelemetryAccepted(state,entry,stop,target,current_bar);
   return true;
  }

bool PositionIdentifierExists(const ulong identifier)
  {
   for(int index=PositionsTotal()-1;index>=0;index--)
     {
      ulong ticket=PositionGetTicket(index);
      if(ticket>0 && PositionSelectByTicket(ticket) &&
         (ulong)PositionGetInteger(POSITION_IDENTIFIER)==identifier)
         return true;
     }
   return false;
  }

ENUM_ORDER_TYPE EntryTypeForPosition(const ulong identifier)
  {
   if(!HistorySelect(0,TimeCurrent()))
      return ORDER_TYPE_BUY;
   for(int index=0;index<HistoryDealsTotal();index++)
     {
      ulong deal=HistoryDealGetTicket(index);
      if(deal==0 || (ulong)HistoryDealGetInteger(deal,DEAL_POSITION_ID)!=identifier)
         continue;
      ENUM_DEAL_ENTRY entry=(ENUM_DEAL_ENTRY)HistoryDealGetInteger(deal,DEAL_ENTRY);
      if(entry==DEAL_ENTRY_IN || entry==DEAL_ENTRY_INOUT)
         return HistoryDealGetInteger(deal,DEAL_TYPE)==DEAL_TYPE_SELL ? ORDER_TYPE_SELL : ORDER_TYPE_BUY;
     }
   return ORDER_TYPE_BUY;
  }

void LogLifecycleDeal(const ulong deal)
  {
   if(!HistoryDealSelect(deal) || HistoryDealGetString(deal,DEAL_SYMBOL)!=_Symbol ||
      HistoryDealGetInteger(deal,DEAL_MAGIC)!=InpMagic)
      return;
   ENUM_DEAL_ENTRY entry=(ENUM_DEAL_ENTRY)HistoryDealGetInteger(deal,DEAL_ENTRY);
   if(entry!=DEAL_ENTRY_IN && entry!=DEAL_ENTRY_INOUT && entry!=DEAL_ENTRY_OUT && entry!=DEAL_ENTRY_OUT_BY)
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
      order_type=HistoryDealGetInteger(deal,DEAL_TYPE)==DEAL_TYPE_SELL ? ORDER_TYPE_SELL : ORDER_TYPE_BUY;
      if(position_id!=g_position_identifier)
        {
         g_entries_opened++;
         g_trades_today++;
        }
      g_position_identifier=position_id;
      g_position_lifecycle_net=0.0;
     }
   g_position_lifecycle_net+=net;
   if(InpEnableTelemetry && g_telemetry_handle!=INVALID_HANDLE)
     {
      FileWrite(g_telemetry_handle,
                TimeToString((datetime)HistoryDealGetInteger(deal,DEAL_TIME),TIME_DATE|TIME_SECONDS),
                is_open ? "OPEN" : (final_close ? "CLOSE" : "CLOSE_PARTIAL"),
                order_type==ORDER_TYPE_SELL ? "SELL" : "BUY",
                DoubleToString(HistoryDealGetDouble(deal,DEAL_VOLUME),8),
                DoubleToString(HistoryDealGetDouble(deal,DEAL_PRICE),_Digits),_Symbol,
                StringFormat("%I64u",position_id),
                DoubleToString(MathAbs(g_initial_entry-g_initial_stop)/_Point,8),
                DoubleToString(g_planned_risk_account,8),StringFormat("%I64u",deal),
                DoubleToString(profit,8),DoubleToString(commission,8),
                DoubleToString(swap,8),DoubleToString(fee,8),DoubleToString(net,8),
                final_close ? "1" : "0");
      FileFlush(g_telemetry_handle);
     }
   if(final_close)
     {
      g_position_identifier=0;
      g_initial_entry=0.0;
      g_initial_stop=0.0;
      g_planned_risk_account=0.0;
      g_position_lifecycle_net=0.0;
     }
  }

bool WriteRunMeta()
  {
   if(!InpEnableTelemetry || g_run_meta_name=="")
      return true;
   int handle=FileOpen(g_run_meta_name,FILE_WRITE|FILE_TXT|FILE_ANSI);
   if(handle==INVALID_HANDLE)
      return false;
   string payload=StringFormat(
      "{\"schema_version\":\"alphafactory_run_meta.v1\",\"run_id\":\"%s\",\"ea_name\":\"%s\",\"symbol\":\"%s\",\"telemetry_profile\":\"%s\",\"hypothesis_id\":\"%s\",\"signal_mode\":%d,\"magic\":%I64d,\"promotion_eligible\":false,\"report_sha256\":\"%s\",\"source_data_sha256\":\"%s\",\"clock_contract\":\"%s\",\"cost_status\":\"UNVERIFIED_DIAGNOSTIC\",\"news_status\":\"%s\",\"news_source_sha256\":\"%s\",\"diagnostic\":{\"bars_seen\":%I64d,\"extrema_rejections\":%I64d,\"delta_rejections\":%I64d,\"rsi_rejections\":%I64d,\"adx_rejections\":%I64d,\"donchian_rejections\":%I64d,\"pivot_rejections\":%I64d,\"squeeze_rejections\":%I64d,\"wick_rejections\":%I64d,\"news_rejections\":%I64d,\"spread_rejections\":%I64d,\"cooldown_rejections\":%I64d,\"risk_rejections\":%I64d,\"entries_attempted\":%I64d,\"entries_opened\":%I64d}}",
      g_run_id,EA_NAME,_Symbol,TELEMETRY_PROFILE,InpHypothesisId,(int)InpSignalMode,InpMagic,
      REPORT_SHA256,SOURCE_DATA_SHA256,CLOCK_CONTRACT,
      InpRequireNewsGuard ? NEWS_CALENDAR_SOURCE_CLASS : "DISABLED",NEWS_CALENDAR_SOURCE_SHA256,
      g_bars_seen,g_extrema_rejections,g_delta_rejections,g_rsi_rejections,
      g_adx_rejections,g_donchian_rejections,g_pivot_rejections,g_squeeze_rejections,
      g_wick_rejections,g_news_rejections,g_spread_rejections,g_cooldown_rejections,
      g_risk_rejections,g_entries_attempted,g_entries_opened);
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
   g_state_telemetry_name=StringFormat("%s_StateTelemetry_%s.csv",_Symbol,g_run_id);
   g_telemetry_handle=FileOpen(g_lifecycle_name,FILE_WRITE|FILE_CSV|FILE_ANSI,',');
   if(g_telemetry_handle==INVALID_HANDLE)
      return false;
   FileWrite(g_telemetry_handle,"event_time","action","order_type","volume","price","symbol",
             "position_id","risk_pts","initial_risk_account","deal","deal_profit",
             "deal_commission","deal_swap","deal_fee","deal_net","is_final_close");
   FileFlush(g_telemetry_handle);
   g_state_telemetry_handle=FileOpen(g_state_telemetry_name,FILE_WRITE|FILE_TXT|FILE_ANSI);
   if(g_state_telemetry_handle==INVALID_HANDLE)
      return false;
   string header=
      "server_time,utc_time,decision_bar_time,symbol,run_id,hypothesis_id,"
      "signal_mode,direction,accepted,spread_pips,"
      "o1,h1,l1,c1,o2,h2,l2,c2,o3,h3,l3,c3,"
      "atr1,atr2,atr3,adx1,adx2,pdi1,mdi1,rsi1,rsi2,"
      "ema_legacy1,ema20_1,ema34_1,ema50_1,ema100_1,"
      "bb_upper1,bb_mid1,bb_lower1,bb_upper2,bb_mid2,bb_lower2,"
      "donchian_high20,donchian_low20,body1,body_median_ref,body_ratio,"
      "bb_width2,bb_width_median_ref,atr_rank_count,pivot_shift,pivot_price,"
      "pull_depth_atr,wick_upper_frac,wick_lower_frac,"
      "g_adx_band,g_adx_rise,g_atr_exp,g_body_exp,"
      "g_donchian_long,g_donchian_short,g_outer_close_long,g_outer_close_short,"
      "g_di_long,g_di_short,g_ema_side_long,g_ema_side_short,"
      "g_trend_long,g_trend_short,g_pullback,g_reclaim_long,g_reclaim_short,"
      "g_anti_break_long,g_anti_break_short,g_squeeze_pre,g_break_long,g_break_short,"
      "g_run_up,g_run_down,g_ext_up,g_ext_down,g_reject_up,g_reject_down,"
      "planned_entry,planned_stop,planned_target,planned_risk_price,target_rr\n";
   FileWriteString(g_state_telemetry_handle,header);
   FileFlush(g_state_telemetry_handle);
   return WriteRunMeta();
  }

void ManageOwnedPosition()
  {
   ulong ticket=OwnedPositionTicket();
   if(ticket==0 || !PositionSelectByTicket(ticket))
      return;
   datetime now=TimeCurrent();
   int utc_minute=UtcMinute(now);
   datetime opened=(datetime)PositionGetInteger(POSITION_TIME);
   if(utc_minute>=InpFlattenUtcHour*60+InpFlattenUtcMinute ||
      now-opened>=InpMaxHoldBars*PeriodSeconds(PERIOD_M5) || AccountDrawdownHit())
     {
      trade.PositionClose(ticket);
      return;
     }
   if(!InpUseBreakEven)
      return;
   double entry=PositionGetDouble(POSITION_PRICE_OPEN);
   double stop=PositionGetDouble(POSITION_SL);
   double target=PositionGetDouble(POSITION_TP);
   int direction=PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_BUY ? 1 : -1;
   double initial_risk=MathAbs(entry-g_initial_stop);
   MqlTick tick;
   if(initial_risk<=0.0 || !SymbolInfoTick(_Symbol,tick))
      return;
   double current=(direction>0 ? tick.bid : tick.ask);
   if((direction>0 ? current-entry : entry-current)>=InpBreakEvenR*initial_risk &&
      (direction>0 ? stop<entry : stop>entry))
      trade.PositionModify(ticket,NormalizeDouble(entry,_Digits),target);
  }

bool ValidateInputs()
  {
   if(_Period!=PERIOD_M5)
      return false;
   if(InpResearchAutoMode && !MQLInfoInteger(MQL_TESTER))
      return false;
   if(InpRequireNewsGuard && !NewsCalendarValid())
      return false;
   if(InpHypothesisId!=ExpectedHypothesisId(InpSignalMode))
      return false;
   if(InpMagic!=ExpectedMagic(InpSignalMode))
      return false;
   if(InpUseBreakEven)
      return false;
   return InpRiskPercent>0.0 && InpRiskPercent<=1.0 && InpMacdFast>1 &&
          InpMacdSlow>InpMacdFast && InpMacdSignal>1 && InpRsiPeriod>1 &&
          InpRsiLower>0.0 && InpRsiUpper>InpRsiLower && InpRsiUpper<100.0 &&
          InpEmaPeriod>1 && InpAdxPeriod>1 && InpMinAdx>0.0 && InpAtrPeriod>1 &&
          InpMinHistDeltaAtr>0.0 && InpStopLookbackBars>=2 &&
          InpStopAtrMultiple>0.0 && InpStopBufferPips>=0.0 && InpTargetRR>0.0 &&
          InpMaxHoldBars>0 && InpCooldownBars>0 && InpBreakEvenR>0.0 &&
          InpMaxSpreadPips>0.0 && InpMaxTradesPerDay>0 && InpDailyLossPct>0.0 &&
          InpMaxAccountDrawdownPct>0.0 && InpSessionStartUtcHour>=0 &&
          InpSessionEndUtcHour>InpSessionStartUtcHour && InpSessionEndUtcHour<=23 &&
          InpFlattenUtcHour>=InpSessionEndUtcHour && InpFlattenUtcHour<=23 &&
          InpFlattenUtcMinute>=0 && InpFlattenUtcMinute<=59 &&
          InpNewsBlackoutMinutes>0 && InpNewsBlackoutMinutes<=180;
  }

int OnInit()
  {
   if(!ValidateInputs())
      return INIT_PARAMETERS_INCORRECT;
   g_macd_handle=iMACD(_Symbol,PERIOD_M5,InpMacdFast,InpMacdSlow,InpMacdSignal,PRICE_CLOSE);
   g_rsi_handle=iRSI(_Symbol,PERIOD_M5,InpRsiPeriod,PRICE_CLOSE);
   g_ema_handle=iMA(_Symbol,PERIOD_M5,InpEmaPeriod,0,MODE_EMA,PRICE_CLOSE);
   g_ema20_handle=iMA(_Symbol,PERIOD_M5,20,0,MODE_EMA,PRICE_CLOSE);
   g_ema34_handle=iMA(_Symbol,PERIOD_M5,34,0,MODE_EMA,PRICE_CLOSE);
   g_ema50_handle=iMA(_Symbol,PERIOD_M5,50,0,MODE_EMA,PRICE_CLOSE);
   g_ema100_handle=iMA(_Symbol,PERIOD_M5,100,0,MODE_EMA,PRICE_CLOSE);
   g_adx_handle=iADX(_Symbol,PERIOD_M5,InpAdxPeriod);
   g_atr_handle=iATR(_Symbol,PERIOD_M5,InpAtrPeriod);
   g_bb_handle=iBands(_Symbol,PERIOD_M5,20,0,2.0,PRICE_CLOSE);
   if(g_macd_handle==INVALID_HANDLE || g_rsi_handle==INVALID_HANDLE ||
      g_ema_handle==INVALID_HANDLE || g_ema20_handle==INVALID_HANDLE ||
      g_ema34_handle==INVALID_HANDLE || g_ema50_handle==INVALID_HANDLE ||
      g_ema100_handle==INVALID_HANDLE || g_adx_handle==INVALID_HANDLE ||
      g_atr_handle==INVALID_HANDLE || g_bb_handle==INVALID_HANDLE)
      return INIT_FAILED;
   trade.SetExpertMagicNumber((ulong)InpMagic);
   trade.SetDeviationInPoints((ulong)MathMax(1,MathRound(InpMaxSpreadPips*PipSize()/_Point)));
   trade.SetTypeFillingBySymbol(_Symbol);
   trade.SetAsyncMode(false);
   g_peak_equity=AccountInfoDouble(ACCOUNT_EQUITY);
   ResetRiskDayIfNeeded(TimeCurrent());
   if(!OpenTelemetry())
      return INIT_FAILED;
   PrintFormat("MZMS init hypothesis=%s mode=%d magic=%I64d auto=%s closed_bar=true BE=%s promotion=false",
               InpHypothesisId,(int)InpSignalMode,InpMagic,
               InpResearchAutoMode ? "true" : "false",
               InpUseBreakEven ? "true" : "false");
   return INIT_SUCCEEDED;
  }

void OnDeinit(const int reason)
  {
   WriteRunMeta();
   if(g_telemetry_handle!=INVALID_HANDLE)
     {
      FileFlush(g_telemetry_handle);
      FileClose(g_telemetry_handle);
     }
   if(g_state_telemetry_handle!=INVALID_HANDLE)
     {
      FileFlush(g_state_telemetry_handle);
      FileClose(g_state_telemetry_handle);
     }
   if(g_macd_handle!=INVALID_HANDLE) IndicatorRelease(g_macd_handle);
   if(g_rsi_handle!=INVALID_HANDLE) IndicatorRelease(g_rsi_handle);
   if(g_ema_handle!=INVALID_HANDLE) IndicatorRelease(g_ema_handle);
   if(g_ema20_handle!=INVALID_HANDLE) IndicatorRelease(g_ema20_handle);
   if(g_ema34_handle!=INVALID_HANDLE) IndicatorRelease(g_ema34_handle);
   if(g_ema50_handle!=INVALID_HANDLE) IndicatorRelease(g_ema50_handle);
   if(g_ema100_handle!=INVALID_HANDLE) IndicatorRelease(g_ema100_handle);
   if(g_adx_handle!=INVALID_HANDLE) IndicatorRelease(g_adx_handle);
   if(g_atr_handle!=INVALID_HANDLE) IndicatorRelease(g_atr_handle);
   if(g_bb_handle!=INVALID_HANDLE) IndicatorRelease(g_bb_handle);
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
   if(CopyRates(_Symbol,PERIOD_M5,1,SIGNAL_RATES_BARS,bars)!=SIGNAL_RATES_BARS)
      return;
   DecisionState state;
   int direction=ClosedBarSignal(bars,state);
   if(direction!=0)
      TryOpenTrade(direction,bars,state,current_bar);
  }
