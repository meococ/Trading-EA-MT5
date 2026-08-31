#property copyright "AlphaFactory research"
#property version   "1.19"
#property strict
#property description "Owner-authorized ordered ICT/FVG report-fidelity research EA"
#property description "EURUSD M5 + closed M15 MSS/ADX; no live or promotion authority"

#include <Trade/Trade.mqh>
#include "NewsCalendar2019_2022.mqh"

enum ENUM_SIGNAL_MODE
  {
   SIGNAL_HIGH_RECALL_CONTROL=0,
   SIGNAL_REPORT_FIDELITY=1,
   SIGNAL_CONTEXT_STATE=2
  };

enum ENUM_SETUP_STAGE
  {
   SETUP_EMPTY=0,
   SETUP_SWEPT=1,
   SETUP_DISPLACED=2,
   SETUP_MSS_CONFIRMED=3
  };

input bool             InpResearchAutoMode=false;
input bool             InpEnableTelemetry=true;
input ENUM_SIGNAL_MODE InpSignalMode=SIGNAL_REPORT_FIDELITY;
input double           InpRiskPercent=0.25;
input long             InpMagic=5600720;

input int              InpPivotStrength=2;
input int              InpSweepLookback=20;
input int              InpDisplacementBars=6;
input int              InpMeanBodyPeriod=20;
input double           InpDisplacementBodyMultiple=1.50;
input int              InpM15PivotStrength=2;
input int              InpM15Lookback=120;
input int              InpRetestBars=12;
input double           InpFvgDepthMin=0.50;
input double           InpFvgDepthMax=0.70;
input int              InpAdxPeriod=14;
input double           InpMinAdx=25.0;
input int              InpContextMaxBars=3;
input double           InpContextBodyMultiple=1.00;
input double           InpContextCloseFraction=0.25;

input double           InpStopBufferPips=1.50;
input double           InpTargetRR=2.00;
input double           InpMaxSpreadPips=1.50;
input int              InpMaxTradesPerDay=2;
input double           InpDailyLossPct=1.50;
input double           InpMaxAccountDrawdownPct=8.00;
input int              InpMaxConsecutiveLosses=2;
input int              InpCooldownMinutes=120;
input double           InpBreakEvenTriggerR=1.00;
input double           InpBreakEvenLockR=0.50;
input int              InpFlattenUtcHour=22;
input int              InpFridayFlattenUtcHour=20;
input int              InpFridayFlattenUtcMinute=55;
input int              InpServerUtcOffsetWinterHours=2;
input bool             InpServerUsesEuropeDst=true;
input bool             InpRequireNewsGuard=true;
input int              InpNewsBlackoutMinutes=30;
input bool             InpUseAtrTrail=false;
input double           InpAtrTrailStartR=1.50;
input double           InpAtrTrailMultiple=1.00;

const string EA_NAME="EA_ICTFVGReportFidelity";
const string HYPOTHESIS_ID="HYP-ICT-FVG-FRIDAY-SAFE-EURUSD-M5-013";
const string TELEMETRY_PROFILE="lifecycle-v3";
#define MAX_SETUPS 48
const int LONDON_START_UTC_MIN=7*60;
const int LONDON_END_UTC_MIN=11*60;
const int NEW_YORK_START_UTC_MIN=13*60;
const int NEW_YORK_END_UTC_MIN=17*60;

struct SetupState
  {
   ENUM_SETUP_STAGE stage;
   int direction;
   int utc_date_key;
   int session_id;
   int bars_in_stage;
   datetime sweep_time;
   double sweep_high;
   double sweep_low;
   double m15_break_level;
   datetime displacement_time;
   double fvg_low;
   double fvg_high;
   double ob_low;
   double ob_high;
   double ob_body_low;
   double ob_body_high;
   double overlap_low;
   double overlap_high;
   double stop;
   datetime mss_close_time;
  };

CTrade trade;
SetupState g_setups[MAX_SETUPS];
int g_adx_handle=INVALID_HANDLE;
int g_atr_handle=INVALID_HANDLE;
datetime g_last_m5_bar=0;

int g_day_key=0;
double g_day_start_equity=0.0;
double g_peak_equity=0.0;
int g_trades_today=0;
int g_consecutive_losses=0;
datetime g_cooldown_until=0;

ulong g_position_identifier=0;
ulong g_last_classified_position_identifier=0;
ENUM_ORDER_TYPE g_entry_order_type=ORDER_TYPE_BUY;
double g_initial_entry=0.0;
double g_initial_stop=0.0;
double g_initial_risk_price=0.0;
double g_planned_risk_account=0.0;
double g_position_lifecycle_net=0.0;
int g_position_entry_utc_key=0;
bool g_force_close=false;
datetime g_force_close_since=0;

int g_telemetry_handle=INVALID_HANDLE;
string g_run_id="";
string g_lifecycle_name="";
string g_run_meta_name="";

long g_days_seen=0;
long g_sweeps=0;
long g_displacements=0;
long g_fvgs=0;
long g_mss=0;
long g_pre_mss_mitigations=0;
long g_retests=0;
long g_adx_rejections=0;
long g_news_rejections=0;
long g_spread_rejections=0;
long g_risk_rejections=0;
long g_entries_attempted=0;
long g_entries_opened=0;
long g_fill_risk_closes=0;
long g_research_disabled_rejections=0;
long g_session_rejections=0;
long g_prop_rejections=0;
long g_exposure_rejections=0;
long g_stop_direction_rejections=0;
long g_stop_geometry_rejections=0;
long g_volume_rejections=0;
long g_ordercheck_rejections=0;
long g_ordercheck_zero_successes=0;
long g_send_rejections=0;
long g_displacement_day_expiries=0;
long g_displacement_timeouts=0;
long g_retest_day_expiries=0;
long g_retest_timeouts=0;
long g_retest_stop_breaches=0;
long g_retest_first_touches=0;
long g_retest_invalid_zones=0;
long g_retest_depth_rejections=0;
long g_retest_candle_rejections=0;
long g_adx_read_rejections=0;
long g_adx_threshold_rejections=0;
long g_adx_passes=0;
long g_context_duplicate_rejections=0;
long g_context_acceptance_invalidations=0;
long g_context_timeouts=0;
long g_context_confirmations=0;

double PipSize()
  {
   if(_Digits==3 || _Digits==5)
      return 10.0*_Point;
   return _Point;
  }

double PipsToPrice(const double pips)
  {
   return pips*PipSize();
  }

double SpreadPips()
  {
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick))
      return DBL_MAX;
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

bool FridayCutoffReached(const datetime server_time)
  {
   MqlDateTime parts;
   TimeToStruct(ServerToUtc(server_time),parts);
   if(parts.day_of_week!=5)
      return false;
   int cutoff=InpFridayFlattenUtcHour*60+InpFridayFlattenUtcMinute;
   return parts.hour*60+parts.min>=cutoff;
  }

int EligibleSession(const datetime server_time)
  {
   int minute=UtcMinute(server_time);
   if(minute>=LONDON_START_UTC_MIN && minute<LONDON_END_UTC_MIN)
      return 1;
   if(minute>=NEW_YORK_START_UTC_MIN && minute<NEW_YORK_END_UTC_MIN)
      return 2;
   return 0;
  }

bool NewsCalendarValid()
  {
   if(ArraySize(NEWS_CALENDAR_UTC)!=NEWS_CALENDAR_COUNT || NEWS_CALENDAR_COUNT<1 ||
      StringLen(NEWS_CALENDAR_SOURCE_SHA256)!=64)
      return false;
   for(int index=1;index<NEWS_CALENDAR_COUNT;index++)
      if(NEWS_CALENDAR_UTC[index]<=NEWS_CALENDAR_UTC[index-1])
         return false;
   return true;
  }

bool NewsBlocked(const datetime server_time)
  {
   if(!InpRequireNewsGuard)
      return false;

   datetime utc_time=ServerToUtc(server_time);
   if(utc_time<NEWS_CALENDAR_COVERAGE_START_UTC ||
      utc_time>NEWS_CALENDAR_COVERAGE_END_UTC)
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

   long window_seconds=(long)InpNewsBlackoutMinutes*60;
   if(left<NEWS_CALENDAR_COUNT)
     {
      long delta=(long)NEWS_CALENDAR_UTC[left]-(long)utc_time;
      if(delta<0)
         delta=-delta;
      if(delta<=window_seconds)
         return true;
     }
   if(left>0)
     {
      long delta=(long)utc_time-(long)NEWS_CALENDAR_UTC[left-1];
      if(delta<0)
         delta=-delta;
      if(delta<=window_seconds)
         return true;
     }
   return false;
  }

string PersistentKey(const string suffix)
  {
   return StringFormat("ICTFVG.%s.%I64d.%s",_Symbol,InpMagic,suffix);
  }

void SavePersistentRiskState()
  {
   if(MQLInfoInteger(MQL_TESTER))
      return;
   GlobalVariableSet(PersistentKey("day"),(double)g_day_key);
   GlobalVariableSet(PersistentKey("dayeq"),g_day_start_equity);
   GlobalVariableSet(PersistentKey("peak"),g_peak_equity);
   GlobalVariableSet(PersistentKey("trades"),(double)g_trades_today);
   GlobalVariableSet(PersistentKey("losses"),(double)g_consecutive_losses);
   GlobalVariableSet(PersistentKey("cool"),(double)g_cooldown_until);
   uint position_low=(uint)(g_position_identifier&0xFFFFFFFF);
   uint position_high=(uint)(g_position_identifier>>32);
   uint classified_low=(uint)(g_last_classified_position_identifier&0xFFFFFFFF);
   uint classified_high=(uint)(g_last_classified_position_identifier>>32);
   GlobalVariableSet(PersistentKey("poslo"),(double)position_low);
   GlobalVariableSet(PersistentKey("poshi"),(double)position_high);
   GlobalVariableSet(PersistentKey("classlo"),(double)classified_low);
   GlobalVariableSet(PersistentKey("classhi"),(double)classified_high);
   GlobalVariableSet(PersistentKey("otype"),(double)g_entry_order_type);
   GlobalVariableSet(PersistentKey("entry"),g_initial_entry);
   GlobalVariableSet(PersistentKey("stop"),g_initial_stop);
   GlobalVariableSet(PersistentKey("planrisk"),g_planned_risk_account);
   GlobalVariableSet(PersistentKey("lifenet"),g_position_lifecycle_net);
   GlobalVariableSet(PersistentKey("entryday"),(double)g_position_entry_utc_key);
   GlobalVariableSet(PersistentKey("force"),(g_force_close ? 1.0 : 0.0));
   GlobalVariableSet(PersistentKey("forcesince"),(double)g_force_close_since);
   GlobalVariablesFlush();
  }

void LoadPersistentRiskState()
  {
   g_peak_equity=AccountInfoDouble(ACCOUNT_EQUITY);
   if(MQLInfoInteger(MQL_TESTER))
      return;
   if(GlobalVariableCheck(PersistentKey("day")))
      g_day_key=(int)GlobalVariableGet(PersistentKey("day"));
   if(GlobalVariableCheck(PersistentKey("dayeq")))
      g_day_start_equity=GlobalVariableGet(PersistentKey("dayeq"));
   if(GlobalVariableCheck(PersistentKey("peak")))
      g_peak_equity=GlobalVariableGet(PersistentKey("peak"));
   if(GlobalVariableCheck(PersistentKey("trades")))
      g_trades_today=(int)GlobalVariableGet(PersistentKey("trades"));
   if(GlobalVariableCheck(PersistentKey("losses")))
      g_consecutive_losses=(int)GlobalVariableGet(PersistentKey("losses"));
   if(GlobalVariableCheck(PersistentKey("cool")))
      g_cooldown_until=(datetime)GlobalVariableGet(PersistentKey("cool"));
   if(GlobalVariableCheck(PersistentKey("poslo")) &&
      GlobalVariableCheck(PersistentKey("poshi")))
     {
      ulong position_low=(ulong)(uint)GlobalVariableGet(PersistentKey("poslo"));
      ulong position_high=(ulong)(uint)GlobalVariableGet(PersistentKey("poshi"));
      g_position_identifier=(position_high<<32)|position_low;
     }
   if(GlobalVariableCheck(PersistentKey("classlo")) &&
      GlobalVariableCheck(PersistentKey("classhi")))
     {
      ulong classified_low=(ulong)(uint)GlobalVariableGet(PersistentKey("classlo"));
      ulong classified_high=(ulong)(uint)GlobalVariableGet(PersistentKey("classhi"));
      g_last_classified_position_identifier=(classified_high<<32)|classified_low;
     }
   if(GlobalVariableCheck(PersistentKey("otype")))
      g_entry_order_type=(ENUM_ORDER_TYPE)(int)GlobalVariableGet(PersistentKey("otype"));
   if(GlobalVariableCheck(PersistentKey("entry")))
      g_initial_entry=GlobalVariableGet(PersistentKey("entry"));
   if(GlobalVariableCheck(PersistentKey("stop")))
      g_initial_stop=GlobalVariableGet(PersistentKey("stop"));
   if(GlobalVariableCheck(PersistentKey("planrisk")))
      g_planned_risk_account=GlobalVariableGet(PersistentKey("planrisk"));
   if(GlobalVariableCheck(PersistentKey("lifenet")))
      g_position_lifecycle_net=GlobalVariableGet(PersistentKey("lifenet"));
   if(GlobalVariableCheck(PersistentKey("entryday")))
      g_position_entry_utc_key=(int)GlobalVariableGet(PersistentKey("entryday"));
   if(GlobalVariableCheck(PersistentKey("force")))
      g_force_close=GlobalVariableGet(PersistentKey("force"))>0.5;
   if(GlobalVariableCheck(PersistentKey("forcesince")))
      g_force_close_since=(datetime)GlobalVariableGet(PersistentKey("forcesince"));
   g_initial_risk_price=MathAbs(g_initial_entry-g_initial_stop);
  }

void ResetRiskDayIfNeeded(const datetime server_time)
  {
   int key=UtcDateKey(server_time);
   if(key==g_day_key)
      return;
   g_day_key=key;
   g_day_start_equity=AccountInfoDouble(ACCOUNT_EQUITY);
   g_trades_today=0;
   g_days_seen++;
   SavePersistentRiskState();
  }

bool DailyLossHit()
  {
   if(g_day_start_equity<=0.0)
      return true;
   double floor_equity=g_day_start_equity*(1.0-InpDailyLossPct/100.0);
   return AccountInfoDouble(ACCOUNT_EQUITY)<=floor_equity;
  }

bool AccountDrawdownHit()
  {
   if(g_peak_equity<=0.0)
      return true;
   double floor_equity=g_peak_equity*(1.0-InpMaxAccountDrawdownPct/100.0);
   return AccountInfoDouble(ACCOUNT_EQUITY)<=floor_equity;
  }

bool CooldownActive()
  {
   return g_consecutive_losses>=InpMaxConsecutiveLosses && TimeCurrent()<g_cooldown_until;
  }

ulong OwnedPositionTicket()
  {
   for(int index=PositionsTotal()-1;index>=0;index--)
     {
      ulong ticket=PositionGetTicket(index);
      if(ticket==0 || !PositionSelectByTicket(ticket))
         continue;
      if(PositionGetString(POSITION_SYMBOL)==_Symbol &&
         PositionGetInteger(POSITION_MAGIC)==InpMagic)
         return ticket;
     }
   return 0;
  }

bool ForeignSymbolExposure()
  {
   for(int index=PositionsTotal()-1;index>=0;index--)
     {
      ulong ticket=PositionGetTicket(index);
      if(ticket==0 || !PositionSelectByTicket(ticket))
         continue;
      if(PositionGetString(POSITION_SYMBOL)==_Symbol &&
         PositionGetInteger(POSITION_MAGIC)!=InpMagic)
         return true;
     }
   return false;
  }

bool OwnedPendingOrderExists()
  {
   for(int index=OrdersTotal()-1;index>=0;index--)
     {
      ulong ticket=OrderGetTicket(index);
      if(ticket==0)
         continue;
      if(OrderGetString(ORDER_SYMBOL)==_Symbol &&
         OrderGetInteger(ORDER_MAGIC)==InpMagic)
         return true;
     }
   return false;
  }

void ClearPositionRiskState()
  {
   g_position_identifier=0;
   g_initial_entry=0.0;
   g_initial_stop=0.0;
   g_initial_risk_price=0.0;
   g_planned_risk_account=0.0;
   g_position_lifecycle_net=0.0;
   g_position_entry_utc_key=0;
   g_force_close=false;
   g_force_close_since=0;
  }

bool LifecycleStatsFromHistory(const ulong position_id,double &lifecycle_net,
                               datetime &last_deal_time)
  {
   lifecycle_net=0.0;
   last_deal_time=0;
   if(position_id==0 || !HistorySelect(0,TimeCurrent()))
      return false;
   bool found=false;
   for(int index=0;index<HistoryDealsTotal();index++)
     {
      ulong deal=HistoryDealGetTicket(index);
      if(deal==0 || (ulong)HistoryDealGetInteger(deal,DEAL_POSITION_ID)!=position_id ||
         HistoryDealGetString(deal,DEAL_SYMBOL)!=_Symbol ||
         HistoryDealGetInteger(deal,DEAL_MAGIC)!=InpMagic)
         continue;
      ENUM_DEAL_ENTRY entry=(ENUM_DEAL_ENTRY)HistoryDealGetInteger(deal,DEAL_ENTRY);
      if(entry!=DEAL_ENTRY_IN && entry!=DEAL_ENTRY_INOUT &&
         entry!=DEAL_ENTRY_OUT && entry!=DEAL_ENTRY_OUT_BY)
         continue;
      lifecycle_net+=HistoryDealGetDouble(deal,DEAL_PROFIT)+
                     HistoryDealGetDouble(deal,DEAL_COMMISSION)+
                     HistoryDealGetDouble(deal,DEAL_SWAP)+
                     HistoryDealGetDouble(deal,DEAL_FEE);
      datetime deal_time=(datetime)HistoryDealGetInteger(deal,DEAL_TIME);
      last_deal_time=MathMax(last_deal_time,deal_time);
      found=true;
     }
   return found;
  }

bool ApplyLifecycleClassification(const ulong position_id,const double lifecycle_net,
                                  const datetime final_deal_time)
  {
   if(position_id==0)
      return false;
   if(position_id==g_last_classified_position_identifier)
      return true;
   if(lifecycle_net<0.0)
     {
      g_consecutive_losses++;
      if(g_consecutive_losses>=InpMaxConsecutiveLosses)
        {
         datetime cooldown_anchor=(final_deal_time>0 ? final_deal_time : TimeCurrent());
         g_cooldown_until=MathMax(g_cooldown_until,
                                  cooldown_anchor+InpCooldownMinutes*60);
        }
     }
   else
      g_consecutive_losses=0;
   g_last_classified_position_identifier=position_id;
   return true;
  }

int CountActualEntryLifecyclesForUtcDay(const int date_key)
  {
   if(date_key<=0 || !HistorySelect(0,TimeCurrent()))
      return -1;
   ulong position_ids[];
   ArrayResize(position_ids,0);
   for(int index=0;index<HistoryDealsTotal();index++)
     {
      ulong deal=HistoryDealGetTicket(index);
      if(deal==0 || HistoryDealGetString(deal,DEAL_SYMBOL)!=_Symbol ||
         HistoryDealGetInteger(deal,DEAL_MAGIC)!=InpMagic)
         continue;
      ENUM_DEAL_ENTRY entry=(ENUM_DEAL_ENTRY)HistoryDealGetInteger(deal,DEAL_ENTRY);
      if(entry!=DEAL_ENTRY_IN && entry!=DEAL_ENTRY_INOUT)
         continue;
      datetime deal_time=(datetime)HistoryDealGetInteger(deal,DEAL_TIME);
      if(UtcDateKey(deal_time)!=date_key)
         continue;
      ulong position_id=(ulong)HistoryDealGetInteger(deal,DEAL_POSITION_ID);
      bool seen=false;
      for(int existing=0;existing<ArraySize(position_ids);existing++)
         if(position_ids[existing]==position_id)
           {
            seen=true;
            break;
           }
      if(!seen)
        {
         int size=ArraySize(position_ids);
         ArrayResize(position_ids,size+1);
         position_ids[size]=position_id;
        }
     }
   return ArraySize(position_ids);
  }

bool TradeRetcodeAccepted(const uint retcode)
  {
   return retcode==TRADE_RETCODE_DONE || retcode==TRADE_RETCODE_DONE_PARTIAL ||
          retcode==TRADE_RETCODE_PLACED;
  }

bool ForceCloseOwnedPosition(const string reason)
  {
   ulong ticket=OwnedPositionTicket();
   if(ticket==0 || !PositionSelectByTicket(ticket))
     {
      // A DEAL_ADD transaction can arrive just before the position becomes
      // selectable. Keep the fail-close latch for one minute so the next tick
      // retries instead of silently clearing the guard in that race window.
      if(g_force_close && g_force_close_since>0 &&
         TimeCurrent()<g_force_close_since+60)
         return false;
      g_force_close=false;
      g_force_close_since=0;
      SavePersistentRiskState();
      return true;
     }
   g_force_close=true;
   if(g_force_close_since<=0)
      g_force_close_since=TimeCurrent();
   SavePersistentRiskState();
   bool sent=trade.PositionClose(ticket);
   uint retcode=trade.ResultRetcode();
   if(!sent || !TradeRetcodeAccepted(retcode))
     {
      PrintFormat("ICTFVG emergency close retry pending reason=%s retcode=%u %s",
                  reason,retcode,trade.ResultRetcodeDescription());
      return false;
     }
   return true;
  }

bool RestoreOwnedPositionState()
  {
   ulong ticket=OwnedPositionTicket();
   if(ticket==0 || !PositionSelectByTicket(ticket))
     {
      if(!OwnedPendingOrderExists())
        {
         ulong closed_position_id=g_position_identifier;
         if(closed_position_id!=0 &&
            closed_position_id!=g_last_classified_position_identifier)
           {
            double closed_net=0.0;
            datetime final_deal_time=0;
            if(LifecycleStatsFromHistory(closed_position_id,closed_net,final_deal_time))
               ApplyLifecycleClassification(closed_position_id,closed_net,final_deal_time);
            else
              {
               // History should contain the persisted lifecycle. If it does
               // not, do not assume a winner or silently loosen the guard.
               g_consecutive_losses=MathMax(g_consecutive_losses,
                                             InpMaxConsecutiveLosses);
               g_cooldown_until=MathMax(g_cooldown_until,
                                        TimeCurrent()+InpCooldownMinutes*60);
               g_last_classified_position_identifier=closed_position_id;
              }
           }
         ClearPositionRiskState();
         SavePersistentRiskState();
        }
      return true;
     }

   ulong position_id=(ulong)PositionGetInteger(POSITION_IDENTIFIER);
   bool same_position=(g_position_identifier==position_id && position_id!=0);
   ENUM_POSITION_TYPE position_type=(ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE);
   int direction=(position_type==POSITION_TYPE_BUY ? 1 : -1);
   double entry=PositionGetDouble(POSITION_PRICE_OPEN);

   g_position_identifier=position_id;
   g_entry_order_type=(direction>0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL);
   g_position_entry_utc_key=UtcDateKey((datetime)PositionGetInteger(POSITION_TIME));

   bool stored_stop_valid=same_position &&
      ((direction>0 && g_initial_stop>0.0 && g_initial_stop<entry) ||
       (direction<0 && g_initial_stop>entry));
   g_initial_entry=entry;
   if(!same_position || !stored_stop_valid || g_planned_risk_account<=0.0)
     {
      g_initial_stop=0.0;
      g_initial_risk_price=0.0;
      g_force_close=true;
      g_force_close_since=TimeCurrent();
      SavePersistentRiskState();
      return true;
     }
   g_initial_risk_price=MathAbs(g_initial_entry-g_initial_stop);

   double history_net=0.0;
   datetime history_last_deal_time=0;
   if(LifecycleStatsFromHistory(position_id,history_net,history_last_deal_time))
      g_position_lifecycle_net=history_net;
   else if(!same_position)
      g_position_lifecycle_net=0.0;

   SavePersistentRiskState();
   return true;
  }

double NormalizeVolumeDown(const double raw)
  {
   double minimum=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN);
   double maximum=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX);
   double step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);
   if(step<=0.0 || raw<minimum)
      return 0.0;
   double volume=MathFloor(raw/step+1e-9)*step;
   volume=MathMin(maximum,volume);
   return NormalizeDouble(volume,8);
  }

double RiskSizedVolume(const int direction,const double entry,const double stop,
                       double &risk_account)
  {
   risk_account=AccountInfoDouble(ACCOUNT_EQUITY)*InpRiskPercent/100.0;
   double one_lot_profit=0.0;
   ENUM_ORDER_TYPE type=(direction>0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL);
   if(!OrderCalcProfit(type,_Symbol,1.0,entry,stop,one_lot_profit))
      return 0.0;
   double one_lot_risk=MathAbs(one_lot_profit);
   if(one_lot_risk<=0.0)
      return 0.0;
   return NormalizeVolumeDown(risk_account/one_lot_risk);
  }

ENUM_ORDER_TYPE_FILLING FillingMode()
  {
   long modes=SymbolInfoInteger(_Symbol,SYMBOL_FILLING_MODE);
   if((modes&SYMBOL_FILLING_FOK)==SYMBOL_FILLING_FOK)
      return ORDER_FILLING_FOK;
   if((modes&SYMBOL_FILLING_IOC)==SYMBOL_FILLING_IOC)
      return ORDER_FILLING_IOC;
   return ORDER_FILLING_RETURN;
  }

bool StopGeometryValid(const int direction,const double entry,const double stop,
                       const double target)
  {
   double minimum=MathMax(_Point,(double)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL)*_Point);
   if(direction>0)
      return stop<entry && target>entry && entry-stop>minimum && target-entry>minimum;
   return stop>entry && target<entry && stop-entry>minimum && entry-target>minimum;
  }

bool CanOpenNow(const datetime server_time)
  {
   ResetRiskDayIfNeeded(server_time);
   if(!InpResearchAutoMode)
     {
      g_research_disabled_rejections++;
      return false;
     }
   if(NewsBlocked(server_time))
     {
      g_news_rejections++;
      return false;
     }
   if(FridayCutoffReached(server_time) || EligibleSession(server_time)==0 ||
      UtcMinute(server_time)>=InpFlattenUtcHour*60)
     {
      g_session_rejections++;
      return false;
     }
   if(g_trades_today>=InpMaxTradesPerDay || DailyLossHit() || AccountDrawdownHit() || CooldownActive())
     {
      g_prop_rejections++;
      return false;
     }
   if(OwnedPositionTicket()!=0 || OwnedPendingOrderExists() || ForeignSymbolExposure())
     {
      g_exposure_rejections++;
      return false;
     }
   double spread=SpreadPips();
   if(spread>InpMaxSpreadPips)
     {
      g_spread_rejections++;
      return false;
     }
   return true;
  }

bool TryOpenTrade(const int direction,const double raw_stop,const string reason)
  {
   datetime server_time=TimeCurrent();
   if(!CanOpenNow(server_time))
      return false;

   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick))
      return false;
   double entry=(direction>0 ? tick.ask : tick.bid);
   double stop=NormalizeDouble(raw_stop,_Digits);
   double risk_price=(direction>0 ? entry-stop : stop-entry);
   if(risk_price<=0.0)
     {
      g_stop_direction_rejections++;
      g_risk_rejections++;
      return false;
     }
   double target=NormalizeDouble(entry+(direction>0 ? 1.0 : -1.0)*InpTargetRR*risk_price,_Digits);
   if(!StopGeometryValid(direction,entry,stop,target))
     {
      g_stop_geometry_rejections++;
      g_risk_rejections++;
      return false;
     }

   double risk_account=0.0;
   double volume=RiskSizedVolume(direction,entry,stop,risk_account);
   if(volume<=0.0)
     {
      g_volume_rejections++;
      g_risk_rejections++;
      return false;
     }

   MqlTradeRequest request;
   MqlTradeCheckResult check;
   ZeroMemory(request);
   ZeroMemory(check);
   request.action=TRADE_ACTION_DEAL;
   request.magic=(ulong)InpMagic;
   request.symbol=_Symbol;
   request.volume=volume;
   request.type=(direction>0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL);
   request.price=entry;
   request.sl=stop;
   request.tp=target;
   request.deviation=(ulong)MathMax(1,MathRound(InpMaxSpreadPips*PipSize()/_Point));
   request.type_filling=FillingMode();
   request.type_time=ORDER_TIME_GTC;
   request.comment=HYPOTHESIS_ID;
   ResetLastError();
   bool check_ok=OrderCheck(request,check);
   int check_error=GetLastError();
   bool check_result_accepted=(check.retcode==0 ||
                               check.retcode==TRADE_RETCODE_DONE ||
                               check.retcode==TRADE_RETCODE_PLACED);
   if(!check_ok)
     {
      PrintFormat("ICTFVG OrderCheck rejected ok=%s error=%d retcode=%u comment=%s",
                  check_ok ? "true" : "false",check_error,check.retcode,check.comment);
      g_ordercheck_rejections++;
      g_risk_rejections++;
      return false;
     }
   if(!check_result_accepted)
     {
      PrintFormat("ICTFVG OrderCheck unexpected result error=%d retcode=%u comment=%s",
                  check_error,check.retcode,check.comment);
      g_ordercheck_rejections++;
      g_risk_rejections++;
      return false;
     }
   if(check.retcode==0)
      g_ordercheck_zero_successes++;

   g_entries_attempted++;
   g_initial_entry=entry;
   g_initial_stop=stop;
   g_initial_risk_price=risk_price;
   g_planned_risk_account=risk_account;
   g_entry_order_type=(direction>0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL);
   g_position_entry_utc_key=UtcDateKey(server_time);
   g_position_lifecycle_net=0.0;

   bool sent=(direction>0 ? trade.Buy(volume,_Symbol,0.0,stop,target,reason)
                          : trade.Sell(volume,_Symbol,0.0,stop,target,reason));
   uint retcode=trade.ResultRetcode();
   if(!sent || !TradeRetcodeAccepted(retcode))
     {
      PrintFormat("ICTFVG entry failed retcode=%u %s",retcode,trade.ResultRetcodeDescription());
      g_send_rejections++;
      ClearPositionRiskState();
      return false;
     }
   // Opened-lifecycle and daily-trade counters advance only on the first
   // actual DEAL_ENTRY_IN transaction, never on a merely accepted request.
   SavePersistentRiskState();
   return true;
  }

bool IsPivotHigh(const MqlRates &bars[],const int count,const int index,const int strength)
  {
   if(index-strength<0 || index+strength>=count)
      return false;
   for(int offset=1;offset<=strength;offset++)
      if(bars[index].high<=bars[index-offset].high || bars[index].high<=bars[index+offset].high)
         return false;
   return true;
  }

bool IsPivotLow(const MqlRates &bars[],const int count,const int index,const int strength)
  {
   if(index-strength<0 || index+strength>=count)
      return false;
   for(int offset=1;offset<=strength;offset++)
      if(bars[index].low>=bars[index-offset].low || bars[index].low>=bars[index+offset].low)
         return false;
   return true;
  }

bool FindLatestM5Pivots(const MqlRates &bars[],const int count,double &pivot_high,double &pivot_low)
  {
   bool high_found=false;
   bool low_found=false;
   int limit=MathMin(count-InpPivotStrength-1,InpSweepLookback+InpPivotStrength);
   for(int index=InpPivotStrength;index<=limit;index++)
     {
      if(!high_found && IsPivotHigh(bars,count,index,InpPivotStrength))
        {
         pivot_high=bars[index].high;
         high_found=true;
        }
      if(!low_found && IsPivotLow(bars,count,index,InpPivotStrength))
        {
         pivot_low=bars[index].low;
         low_found=true;
        }
      if(high_found && low_found)
         return true;
     }
   return false;
  }

bool FindLatestM15BreakLevel(const int direction,double &level)
  {
   MqlRates bars[];
   ArraySetAsSeries(bars,true);
   int requested=MathMax(40,InpM15Lookback);
   int copied=CopyRates(_Symbol,PERIOD_M15,1,requested,bars);
   if(copied<2*InpM15PivotStrength+10)
      return false;
   for(int index=InpM15PivotStrength;index<copied-InpM15PivotStrength;index++)
     {
      if(direction>0 && IsPivotHigh(bars,copied,index,InpM15PivotStrength))
        {
         level=bars[index].high;
         return true;
        }
      if(direction<0 && IsPivotLow(bars,copied,index,InpM15PivotStrength))
        {
         level=bars[index].low;
         return true;
        }
     }
   return false;
  }

bool ClosedM15Adx(double &value)
  {
   double values[];
   ArraySetAsSeries(values,true);
   if(CopyBuffer(g_adx_handle,0,1,1,values)!=1)
      return false;
   value=values[0];
   return MathIsValidNumber(value) && value>=0.0;
  }

double ClosedM5Atr()
  {
   double values[];
   ArraySetAsSeries(values,true);
   if(CopyBuffer(g_atr_handle,0,1,1,values)!=1)
      return 0.0;
   return values[0];
  }

double MeanPriorBody(const MqlRates &bars[],const int count)
  {
   if(count<=InpMeanBodyPeriod)
      return 0.0;
   double total=0.0;
   for(int index=1;index<=InpMeanBodyPeriod;index++)
      total+=MathAbs(bars[index].close-bars[index].open);
   return total/InpMeanBodyPeriod;
  }

bool StrictFvg(const int direction,const MqlRates &current,const MqlRates &two_older,
               double &low,double &high)
  {
   if(direction>0 && current.low>two_older.high)
     {
      low=two_older.high;
      high=current.low;
      return true;
     }
   if(direction<0 && current.high<two_older.low)
     {
      low=current.high;
      high=two_older.low;
      return true;
     }
   return false;
  }

bool FindFreshOrderBlock(const int direction,const MqlRates &bars[],const int count,
                         MqlRates &ob)
  {
   int limit=MathMin(count-1,10);
   for(int index=1;index<=limit;index++)
     {
      bool opposite=(direction>0 ? bars[index].close<bars[index].open
                                 : bars[index].close>bars[index].open);
      if(opposite)
        {
         ob=bars[index];
         return true;
        }
     }
   return false;
  }

bool OverlapZone(const double fvg_low,const double fvg_high,
                 const double ob_body_low,const double ob_body_high,
                 double &overlap_low,double &overlap_high)
  {
   overlap_low=MathMax(fvg_low,ob_body_low);
   overlap_high=MathMin(fvg_high,ob_body_high);
   return overlap_high-overlap_low>=_Point;
  }

void ClearSetup(SetupState &setup)
  {
   ZeroMemory(setup);
   setup.stage=SETUP_EMPTY;
  }

bool AddSweepSetup(const int direction,const int date_key,const int session_id,
                   const MqlRates &bar,const double m15_break_level,
                   const bool count_sweep)
  {
   for(int index=0;index<MAX_SETUPS;index++)
     {
      if(g_setups[index].stage!=SETUP_EMPTY)
         continue;
      ClearSetup(g_setups[index]);
      g_setups[index].stage=SETUP_SWEPT;
      g_setups[index].direction=direction;
      g_setups[index].utc_date_key=date_key;
      g_setups[index].session_id=session_id;
      g_setups[index].sweep_time=bar.time;
      g_setups[index].sweep_high=bar.high;
      g_setups[index].sweep_low=bar.low;
      g_setups[index].m15_break_level=m15_break_level;
      if(count_sweep)
         g_sweeps++;
      return true;
     }
   Print("ICTFVG setup capacity exhausted");
   return false;
  }

bool ContextSetupExists(const int direction,const int date_key,const int session_id)
  {
   for(int index=0;index<MAX_SETUPS;index++)
      if(g_setups[index].stage==SETUP_SWEPT &&
         g_setups[index].direction==direction &&
         g_setups[index].utc_date_key==date_key &&
         g_setups[index].session_id==session_id)
         return true;
   return false;
  }

void DetectSweep(const MqlRates &bars[],const int count,const int date_key,const int session_id)
  {
   if(session_id==0)
      return;
   double pivot_high=0.0;
   double pivot_low=0.0;
   if(!FindLatestM5Pivots(bars,count,pivot_high,pivot_low))
      return;
   int direction=0;
   if(bars[0].low<pivot_low && bars[0].close>pivot_low)
      direction=1;
   else if(bars[0].high>pivot_high && bars[0].close<pivot_high)
      direction=-1;
   if(direction==0)
      return;

   if(InpSignalMode==SIGNAL_HIGH_RECALL_CONTROL)
     {
      g_sweeps++;
      double stop=(direction>0 ? bars[0].low-PipsToPrice(InpStopBufferPips)
                               : bars[0].high+PipsToPrice(InpStopBufferPips));
      TryOpenTrade(direction,stop,"ICTFVG_CONTROL_SWEEP");
      return;
     }

   if(InpSignalMode==SIGNAL_CONTEXT_STATE)
     {
      g_sweeps++;
      if(ContextSetupExists(direction,date_key,session_id))
        {
         g_context_duplicate_rejections++;
         return;
        }
      AddSweepSetup(direction,date_key,session_id,bars[0],0.0,false);
      return;
     }

   double break_level=0.0;
   if(!FindLatestM15BreakLevel(direction,break_level))
      return;
   AddSweepSetup(direction,date_key,session_id,bars[0],break_level,true);
  }

void AdvanceContextState(SetupState &setup,const MqlRates &bars[],const int count,
                         const int date_key)
  {
   if(setup.stage!=SETUP_SWEPT || bars[0].time<=setup.sweep_time)
      return;
   if(setup.utc_date_key!=date_key)
     {
      g_context_timeouts++;
      ClearSetup(setup);
      return;
     }
   setup.bars_in_stage++;
   if(setup.bars_in_stage>InpContextMaxBars)
     {
      g_context_timeouts++;
      ClearSetup(setup);
      return;
     }

   bool accepted_beyond=(setup.direction>0 ? bars[0].close<=setup.sweep_low
                                            : bars[0].close>=setup.sweep_high);
   if(accepted_beyond)
     {
      g_context_acceptance_invalidations++;
      ClearSetup(setup);
      return;
     }

   bool directional=(setup.direction>0 ? bars[0].close>bars[0].open
                                       : bars[0].close<bars[0].open);
   double mean_body=MeanPriorBody(bars,count);
   double body=MathAbs(bars[0].close-bars[0].open);
   bool strong_body=(mean_body>0.0 && body>=InpContextBodyMultiple*mean_body);
   bool opposite_break=(setup.direction>0 ? bars[0].close>setup.sweep_high
                                          : bars[0].close<setup.sweep_low);
   double range=bars[0].high-bars[0].low;
   if(range<=0.0)
      return;
   double close_location=(bars[0].close-bars[0].low)/range;
   bool decisive_close=(setup.direction>0 ? close_location>=1.0-InpContextCloseFraction
                                          : close_location<=InpContextCloseFraction);
   if(!directional || !strong_body || !opposite_break || !decisive_close)
      return;

   double stop=(setup.direction>0 ? setup.sweep_low-PipsToPrice(InpStopBufferPips)
                                  : setup.sweep_high+PipsToPrice(InpStopBufferPips));
   g_context_confirmations++;
   TryOpenTrade(setup.direction,stop,"ICTFVG_CONTEXT_STATE");
   ClearSetup(setup);
  }

void AdvanceContextSetups(const MqlRates &bars[],const int count,const int date_key)
  {
   for(int index=0;index<MAX_SETUPS;index++)
      if(g_setups[index].stage!=SETUP_EMPTY)
         AdvanceContextState(g_setups[index],bars,count,date_key);
  }

void AdvanceDisplacement(SetupState &setup,const MqlRates &bars[],const int count,
                         const int date_key)
  {
   if(setup.stage!=SETUP_SWEPT || bars[0].time<=setup.sweep_time)
      return;
   if(setup.utc_date_key!=date_key)
     {
      g_displacement_day_expiries++;
      ClearSetup(setup);
      return;
     }
   setup.bars_in_stage++;
   if(setup.bars_in_stage>InpDisplacementBars)
     {
      g_displacement_timeouts++;
      ClearSetup(setup);
      return;
     }

   bool directional=(setup.direction>0 ? bars[0].close>bars[0].open
                                       : bars[0].close<bars[0].open);
   double mean_body=MeanPriorBody(bars,count);
   double body=MathAbs(bars[0].close-bars[0].open);
   if(!directional || mean_body<=0.0 || body<=InpDisplacementBodyMultiple*mean_body)
      return;

   double fvg_low=0.0;
   double fvg_high=0.0;
   if(!StrictFvg(setup.direction,bars[0],bars[2],fvg_low,fvg_high))
      return;

   MqlRates ob;
   if(!FindFreshOrderBlock(setup.direction,bars,count,ob))
      return;
   double ob_body_low=MathMin(ob.open,ob.close);
   double ob_body_high=MathMax(ob.open,ob.close);
   double overlap_low=0.0;
   double overlap_high=0.0;
   if(!OverlapZone(fvg_low,fvg_high,ob_body_low,ob_body_high,overlap_low,overlap_high))
      return;

   setup.stage=SETUP_DISPLACED;
   setup.bars_in_stage=0;
   setup.displacement_time=bars[0].time;
   setup.fvg_low=fvg_low;
   setup.fvg_high=fvg_high;
   setup.ob_low=ob.low;
   setup.ob_high=ob.high;
   setup.ob_body_low=ob_body_low;
   setup.ob_body_high=ob_body_high;
   setup.overlap_low=overlap_low;
   setup.overlap_high=overlap_high;
   setup.stop=(setup.direction>0 ? ob.low-PipsToPrice(InpStopBufferPips)
                                 : ob.high+PipsToPrice(InpStopBufferPips));
   g_displacements++;
   g_fvgs++;
  }

bool BarIntersects(const MqlRates &bar,const double low,const double high)
  {
   return bar.low<=high && bar.high>=low;
  }

void AdvanceM15Mss(SetupState &setup,const MqlRates &closed_bar)
  {
   if(setup.stage!=SETUP_DISPLACED || closed_bar.time<=setup.displacement_time)
      return;
   if(BarIntersects(closed_bar,setup.overlap_low,setup.overlap_high))
     {
      g_pre_mss_mitigations++;
      ClearSetup(setup);
      return;
     }
   MqlRates m15[];
   ArraySetAsSeries(m15,true);
   if(CopyRates(_Symbol,PERIOD_M15,1,1,m15)!=1)
      return;
   datetime close_time=m15[0].time+PeriodSeconds(PERIOD_M15);
   if(close_time<=setup.displacement_time || close_time<=setup.mss_close_time)
      return;
   bool broken=(setup.direction>0 ? m15[0].close>setup.m15_break_level
                                  : m15[0].close<setup.m15_break_level);
   if(!broken)
      return;
   setup.stage=SETUP_MSS_CONFIRMED;
   setup.bars_in_stage=0;
   setup.mss_close_time=close_time;
   g_mss++;
  }

void AdvanceRetest(SetupState &setup,const MqlRates &closed_bar,const int date_key)
  {
   if(setup.stage!=SETUP_MSS_CONFIRMED || closed_bar.time<setup.mss_close_time)
      return;
   if(setup.utc_date_key!=date_key)
     {
      g_retest_day_expiries++;
      ClearSetup(setup);
      return;
     }
   setup.bars_in_stage++;
   if(setup.bars_in_stage>InpRetestBars)
     {
      g_retest_timeouts++;
      ClearSetup(setup);
      return;
     }
   if((setup.direction>0 && closed_bar.low<=setup.stop) ||
      (setup.direction<0 && closed_bar.high>=setup.stop))
     {
      g_retest_stop_breaches++;
      ClearSetup(setup);
      return;
     }
   if(!BarIntersects(closed_bar,setup.overlap_low,setup.overlap_high))
      return;
   g_retest_first_touches++;

   double size=setup.fvg_high-setup.fvg_low;
   if(size<=0.0)
     {
      g_retest_invalid_zones++;
      ClearSetup(setup);
      return;
     }
   double depth=(setup.direction>0 ? (setup.fvg_high-closed_bar.low)/size
                                   : (closed_bar.high-setup.fvg_low)/size);
   bool depth_ok=(depth>=InpFvgDepthMin && depth<=InpFvgDepthMax);
   double overlap_mid=0.5*(setup.overlap_low+setup.overlap_high);
   bool rejection=(setup.direction>0 ? closed_bar.close>closed_bar.open && closed_bar.close>overlap_mid
                                     : closed_bar.close<closed_bar.open && closed_bar.close<overlap_mid);
   if(!depth_ok)
     {
      g_retest_depth_rejections++;
      ClearSetup(setup); // the contract allows only the first mitigation
      return;
     }
   if(!rejection)
     {
      g_retest_candle_rejections++;
      ClearSetup(setup);
      return;
     }
   g_retests++;
   double adx=0.0;
   if(!ClosedM15Adx(adx))
     {
      g_adx_read_rejections++;
      g_adx_rejections++;
      ClearSetup(setup);
      return;
     }
   if(adx<=InpMinAdx)
     {
      g_adx_threshold_rejections++;
      g_adx_rejections++;
      ClearSetup(setup);
      return;
     }
   g_adx_passes++;
   TryOpenTrade(setup.direction,setup.stop,"ICTFVG_FULL_FIDELITY");
   ClearSetup(setup);
  }

void AdvanceSetups(const MqlRates &bars[],const int count,const int date_key)
  {
   for(int index=0;index<MAX_SETUPS;index++)
     {
      if(g_setups[index].stage==SETUP_EMPTY)
         continue;
      ENUM_SETUP_STAGE stage_before=g_setups[index].stage;
      if(stage_before==SETUP_SWEPT)
         AdvanceDisplacement(g_setups[index],bars,count,date_key);
      else if(stage_before==SETUP_DISPLACED)
         AdvanceM15Mss(g_setups[index],bars[0]);
      else if(stage_before==SETUP_MSS_CONFIRMED)
         AdvanceRetest(g_setups[index],bars[0],date_key);
     }
  }

void ProcessClosedM5Bar()
  {
   int requested=MathMax(80,InpSweepLookback+InpMeanBodyPeriod+2*InpPivotStrength+12);
   MqlRates bars[];
   ArraySetAsSeries(bars,true);
   int copied=CopyRates(_Symbol,PERIOD_M5,1,requested,bars);
   if(copied<MathMax(40,InpMeanBodyPeriod+3))
      return;
   ResetRiskDayIfNeeded(bars[0].time);
   int date_key=UtcDateKey(bars[0].time);
   int session_id=EligibleSession(bars[0].time);
   if(InpSignalMode==SIGNAL_REPORT_FIDELITY)
      AdvanceSetups(bars,copied,date_key);
   else if(InpSignalMode==SIGNAL_CONTEXT_STATE)
      AdvanceContextSetups(bars,copied,date_key);
   DetectSweep(bars,copied,date_key,session_id);
  }

bool PositionIdentifierExists(const ulong position_id)
  {
   for(int index=PositionsTotal()-1;index>=0;index--)
     {
      ulong ticket=PositionGetTicket(index);
      if(ticket>0 && PositionSelectByTicket(ticket) &&
         (ulong)PositionGetInteger(POSITION_IDENTIFIER)==position_id)
         return true;
     }
   return false;
  }

ENUM_ORDER_TYPE EntryTypeForPosition(const ulong position_id)
  {
   if(position_id==g_position_identifier)
      return g_entry_order_type;
   if(!HistorySelect(0,TimeCurrent()))
      return ORDER_TYPE_BUY;
   for(int index=0;index<HistoryDealsTotal();index++)
     {
      ulong deal=HistoryDealGetTicket(index);
      if(deal==0 || (ulong)HistoryDealGetInteger(deal,DEAL_POSITION_ID)!=position_id)
         continue;
      ENUM_DEAL_ENTRY entry=(ENUM_DEAL_ENTRY)HistoryDealGetInteger(deal,DEAL_ENTRY);
      if(entry==DEAL_ENTRY_IN || entry==DEAL_ENTRY_INOUT)
        {
         ENUM_DEAL_TYPE type=(ENUM_DEAL_TYPE)HistoryDealGetInteger(deal,DEAL_TYPE);
         return type==DEAL_TYPE_SELL ? ORDER_TYPE_SELL : ORDER_TYPE_BUY;
        }
     }
   return ORDER_TYPE_BUY;
  }

bool WriteRunMeta()
  {
   if(!InpEnableTelemetry || g_run_meta_name=="")
      return true;
   int handle=FileOpen(g_run_meta_name,FILE_WRITE|FILE_TXT|FILE_ANSI);
   if(handle==INVALID_HANDLE)
      return false;
   string news_status=(InpRequireNewsGuard ? NEWS_CALENDAR_SOURCE_CLASS : "DISABLED");
   string payload=StringFormat(
      "{\"schema_version\":\"alphafactory_run_meta.v1\",\"run_id\":\"%s\",\"ea_name\":\"%s\",\"symbol\":\"%s\",\"telemetry_profile\":\"%s\",\"hypothesis_id\":\"%s\",\"signal_mode\":%d,\"promotion_eligible\":false,\"news_status\":\"%s\",\"news_source_sha256\":\"%s\",\"news_blackout_minutes\":%d,\"diagnostic\":{\"days_seen\":%I64d,\"sweeps\":%I64d,\"displacements\":%I64d,\"fvgs\":%I64d,\"mss\":%I64d,\"pre_mss_mitigations\":%I64d,\"retests\":%I64d,\"adx_rejections\":%I64d,\"news_rejections\":%I64d,\"spread_rejections\":%I64d,\"risk_rejections\":%I64d,\"entries_attempted\":%I64d,\"entries_opened\":%I64d,\"fill_risk_closes\":%I64d,\"research_disabled_rejections\":%I64d,\"session_rejections\":%I64d,\"prop_rejections\":%I64d,\"exposure_rejections\":%I64d,\"stop_direction_rejections\":%I64d,\"stop_geometry_rejections\":%I64d,\"volume_rejections\":%I64d,\"ordercheck_rejections\":%I64d,\"ordercheck_zero_successes\":%I64d,\"send_rejections\":%I64d,\"displacement_day_expiries\":%I64d,\"displacement_timeouts\":%I64d,\"retest_day_expiries\":%I64d,\"retest_timeouts\":%I64d,\"retest_stop_breaches\":%I64d,\"retest_first_touches\":%I64d,\"retest_invalid_zones\":%I64d,\"retest_depth_rejections\":%I64d,\"retest_candle_rejections\":%I64d,\"adx_read_rejections\":%I64d,\"adx_threshold_rejections\":%I64d,\"adx_passes\":%I64d,\"context_duplicate_rejections\":%I64d,\"context_acceptance_invalidations\":%I64d,\"context_timeouts\":%I64d,\"context_confirmations\":%I64d}}",
      g_run_id,EA_NAME,_Symbol,TELEMETRY_PROFILE,HYPOTHESIS_ID,(int)InpSignalMode,
      news_status,NEWS_CALENDAR_SOURCE_SHA256,InpNewsBlackoutMinutes,
      g_days_seen,g_sweeps,g_displacements,g_fvgs,g_mss,g_pre_mss_mitigations,
      g_retests,g_adx_rejections,g_news_rejections,g_spread_rejections,g_risk_rejections,
      g_entries_attempted,g_entries_opened,g_fill_risk_closes,
      g_research_disabled_rejections,g_session_rejections,g_prop_rejections,
      g_exposure_rejections,g_stop_direction_rejections,g_stop_geometry_rejections,
      g_volume_rejections,g_ordercheck_rejections,g_ordercheck_zero_successes,
      g_send_rejections,g_displacement_day_expiries,g_displacement_timeouts,
      g_retest_day_expiries,g_retest_timeouts,g_retest_stop_breaches,
      g_retest_first_touches,g_retest_invalid_zones,g_retest_depth_rejections,
      g_retest_candle_rejections,g_adx_read_rejections,g_adx_threshold_rejections,
      g_adx_passes,g_context_duplicate_rejections,g_context_acceptance_invalidations,
      g_context_timeouts,g_context_confirmations);
   FileWriteString(handle,payload);
   FileClose(handle);
   return true;
  }

bool OpenLifecycleTelemetry()
  {
   if(!InpEnableTelemetry)
      return true;
   g_run_id=StringFormat("%s_%I64u",HYPOTHESIS_ID,GetTickCount64());
   g_lifecycle_name=StringFormat("%s_LifecycleTrades_%s.csv",_Symbol,g_run_id);
   g_run_meta_name=StringFormat("%s_RunMeta_%s.json",_Symbol,g_run_id);
   g_telemetry_handle=FileOpen(g_lifecycle_name,FILE_WRITE|FILE_CSV|FILE_ANSI,',');
   if(g_telemetry_handle==INVALID_HANDLE)
      return false;
   FileWrite(g_telemetry_handle,
             "event_time","action","order_type","volume","price","symbol",
             "position_id","risk_pts","initial_risk_account","deal",
             "deal_profit","deal_commission","deal_swap","deal_fee","deal_net",
             "is_final_close");
   FileFlush(g_telemetry_handle);
   return WriteRunMeta();
  }

bool ReconcileActualFillRisk(const ulong deal)
  {
   if(!HistoryDealSelect(deal))
      return false;
   ENUM_DEAL_ENTRY entry=(ENUM_DEAL_ENTRY)HistoryDealGetInteger(deal,DEAL_ENTRY);
   if(entry!=DEAL_ENTRY_IN && entry!=DEAL_ENTRY_INOUT)
      return true;
   ulong ticket=OwnedPositionTicket();
   if(ticket==0 || !PositionSelectByTicket(ticket))
     {
      g_force_close=true;
      if(g_force_close_since<=0)
         g_force_close_since=TimeCurrent();
      SavePersistentRiskState();
      return false;
     }
   double fill=PositionGetDouble(POSITION_PRICE_OPEN);
   double stop=PositionGetDouble(POSITION_SL);
   double volume=PositionGetDouble(POSITION_VOLUME);
   int direction=(PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_BUY ? 1 : -1);
   double actual_one_lot=0.0;
   if(!OrderCalcProfit(direction>0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL,
                        _Symbol,1.0,fill,stop,actual_one_lot))
     {
      g_fill_risk_closes++;
      ForceCloseOwnedPosition("actual fill risk could not be calculated");
      return false;
     }
   double actual_risk=MathAbs(actual_one_lot)*volume;
   g_initial_entry=fill;
   g_initial_stop=stop;
   g_initial_risk_price=MathAbs(fill-stop);
   g_position_identifier=(ulong)PositionGetInteger(POSITION_IDENTIFIER);
   SavePersistentRiskState();
   if(g_planned_risk_account>0.0 && actual_risk>g_planned_risk_account*1.10)
     {
      g_fill_risk_closes++;
      PrintFormat("ICTFVG actual fill risk %.2f exceeds plan %.2f; closing",actual_risk,g_planned_risk_account);
      ForceCloseOwnedPosition("actual fill risk exceeds plan by more than 10 percent");
      return false;
     }
   return true;
  }

void LogLifecycleDeal(const ulong deal)
  {
   if(!HistoryDealSelect(deal))
      return;
   if(HistoryDealGetString(deal,DEAL_SYMBOL)!=_Symbol ||
      HistoryDealGetInteger(deal,DEAL_MAGIC)!=InpMagic)
      return;
   ENUM_DEAL_ENTRY entry=(ENUM_DEAL_ENTRY)HistoryDealGetInteger(deal,DEAL_ENTRY);
   if(entry!=DEAL_ENTRY_IN && entry!=DEAL_ENTRY_INOUT &&
      entry!=DEAL_ENTRY_OUT && entry!=DEAL_ENTRY_OUT_BY)
      return;
   ulong position_id=(ulong)HistoryDealGetInteger(deal,DEAL_POSITION_ID);
   ENUM_DEAL_TYPE deal_type=(ENUM_DEAL_TYPE)HistoryDealGetInteger(deal,DEAL_TYPE);
   ENUM_ORDER_TYPE entry_type=EntryTypeForPosition(position_id);
   bool is_open=(entry==DEAL_ENTRY_IN || entry==DEAL_ENTRY_INOUT);
   bool first_open=(is_open && position_id!=g_position_identifier);
   if(is_open)
     {
      entry_type=(deal_type==DEAL_TYPE_SELL ? ORDER_TYPE_SELL : ORDER_TYPE_BUY);
      if(first_open)
        {
         g_entries_opened++;
         g_trades_today++;
         g_position_lifecycle_net=0.0;
        }
      g_entry_order_type=entry_type;
      g_position_identifier=position_id;
      ReconcileActualFillRisk(deal);
     }
   bool final_close=(!is_open && !PositionIdentifierExists(position_id));
   string action=(is_open ? "OPEN" : (final_close ? "CLOSE" : "CLOSE_PARTIAL"));
   double profit=HistoryDealGetDouble(deal,DEAL_PROFIT);
   double commission=HistoryDealGetDouble(deal,DEAL_COMMISSION);
   double swap=HistoryDealGetDouble(deal,DEAL_SWAP);
   double fee=HistoryDealGetDouble(deal,DEAL_FEE);
   double net=profit+commission+swap+fee;
   double authoritative_net=0.0;
   datetime authoritative_last_time=(datetime)HistoryDealGetInteger(deal,DEAL_TIME);
   if(LifecycleStatsFromHistory(position_id,authoritative_net,
                                authoritative_last_time))
      g_position_lifecycle_net=authoritative_net;
   else
      g_position_lifecycle_net+=net;
   if(InpEnableTelemetry && g_telemetry_handle!=INVALID_HANDLE)
     {
      FileWrite(g_telemetry_handle,
                TimeToString((datetime)HistoryDealGetInteger(deal,DEAL_TIME),
                             TIME_DATE|TIME_SECONDS),action,
                entry_type==ORDER_TYPE_SELL ? "SELL" : "BUY",
                DoubleToString(HistoryDealGetDouble(deal,DEAL_VOLUME),8),
                DoubleToString(HistoryDealGetDouble(deal,DEAL_PRICE),_Digits),_Symbol,
                StringFormat("%I64u",position_id),
                DoubleToString(g_initial_risk_price/_Point,8),
                DoubleToString(g_planned_risk_account,8),StringFormat("%I64u",deal),
                DoubleToString(profit,8),DoubleToString(commission,8),
                DoubleToString(swap,8),DoubleToString(fee,8),DoubleToString(net,8),
                final_close ? "1" : "0");
      FileFlush(g_telemetry_handle);
     }
   if(final_close)
     {
      ApplyLifecycleClassification(position_id,g_position_lifecycle_net,
                                   authoritative_last_time);
      ClearPositionRiskState();
      SavePersistentRiskState();
     }
   else
      SavePersistentRiskState();
  }

void ManageOwnedPosition()
  {
   if(g_force_close)
     {
      ForceCloseOwnedPosition("restart-safe fill-risk guard");
      return;
     }
   ulong ticket=OwnedPositionTicket();
   if(ticket==0 || !PositionSelectByTicket(ticket))
      return;
   datetime now=TimeCurrent();
   ResetRiskDayIfNeeded(now);
   int now_key=UtcDateKey(now);
   int minute=UtcMinute(now);
   if(g_position_entry_utc_key==0)
      g_position_entry_utc_key=UtcDateKey((datetime)PositionGetInteger(POSITION_TIME));
   if(now_key!=g_position_entry_utc_key || FridayCutoffReached(now) ||
      minute>=InpFlattenUtcHour*60 || AccountDrawdownHit())
     {
      if(!trade.PositionClose(ticket))
         PrintFormat("ICTFVG flatten failed retcode=%u %s",trade.ResultRetcode(),trade.ResultRetcodeDescription());
      return;
     }

   ENUM_POSITION_TYPE type=(ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE);
   int direction=(type==POSITION_TYPE_BUY ? 1 : -1);
   double entry=PositionGetDouble(POSITION_PRICE_OPEN);
   double current_sl=PositionGetDouble(POSITION_SL);
   double current_tp=PositionGetDouble(POSITION_TP);
   if(g_initial_risk_price<=0.0)
     {
      g_initial_entry=entry;
      g_initial_stop=current_sl;
      g_initial_risk_price=MathAbs(entry-current_sl);
     }
   if(g_initial_risk_price<=0.0)
      return;
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick))
      return;
   double favorable=(direction>0 ? tick.bid-entry : entry-tick.ask);
   double achieved_r=favorable/g_initial_risk_price;
   double candidate_sl=current_sl;
   if(achieved_r>=InpBreakEvenTriggerR)
     {
      double locked=entry+(direction>0 ? 1.0 : -1.0)*InpBreakEvenLockR*g_initial_risk_price;
      if((direction>0 && locked>candidate_sl) || (direction<0 && locked<candidate_sl))
         candidate_sl=locked;
     }
   if(InpUseAtrTrail && achieved_r>=InpAtrTrailStartR)
     {
      double atr=ClosedM5Atr();
      if(atr>0.0)
        {
         double trailed=(direction>0 ? tick.bid-InpAtrTrailMultiple*atr
                                     : tick.ask+InpAtrTrailMultiple*atr);
         if((direction>0 && trailed>candidate_sl) || (direction<0 && trailed<candidate_sl))
            candidate_sl=trailed;
        }
     }
   candidate_sl=NormalizeDouble(candidate_sl,_Digits);
   double minimum=MathMax(_Point,(double)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL)*_Point);
   bool valid=(direction>0 ? candidate_sl>current_sl && candidate_sl<tick.bid-minimum
                           : candidate_sl<current_sl && candidate_sl>tick.ask+minimum);
   if(valid && !trade.PositionModify(ticket,candidate_sl,current_tp))
      PrintFormat("ICTFVG stop tighten failed retcode=%u %s",trade.ResultRetcode(),trade.ResultRetcodeDescription());
  }

bool ValidateInputs()
  {
   if(_Period!=PERIOD_M5)
     {
      Print("EA_ICTFVGReportFidelity requires M5.");
      return false;
     }
   if(InpRequireNewsGuard && !NewsCalendarValid())
     {
      Print("Historical news guard calendar failed validation; fail closed.");
      return false;
     }
   if(InpRiskPercent<=0.0 || InpRiskPercent>1.0 || InpPivotStrength<1 ||
      InpSweepLookback<5 || InpDisplacementBars<1 || InpMeanBodyPeriod<5 ||
      InpDisplacementBodyMultiple<=1.0 || InpM15PivotStrength<1 ||
      InpM15Lookback<30 || InpRetestBars<1 || InpFvgDepthMin<0.0 ||
      InpFvgDepthMax>1.0 || InpFvgDepthMin>=InpFvgDepthMax ||
      InpAdxPeriod<5 || InpMinAdx<=0.0 || InpContextMaxBars<1 ||
      InpContextBodyMultiple<=0.0 || InpContextCloseFraction<=0.0 ||
      InpContextCloseFraction>=0.5 || InpStopBufferPips<=0.0 ||
      InpTargetRR<1.0 || InpMaxSpreadPips<=0.0 || InpMaxTradesPerDay<1 ||
      InpDailyLossPct<=0.0 || InpMaxAccountDrawdownPct<=0.0 ||
      InpMaxConsecutiveLosses<1 || InpCooldownMinutes<1 ||
      InpNewsBlackoutMinutes<1 || InpNewsBlackoutMinutes>180 ||
      InpBreakEvenTriggerR<=0.0 || InpBreakEvenLockR<0.0 ||
      InpBreakEvenLockR>=InpBreakEvenTriggerR || InpFlattenUtcHour<18 ||
      InpFlattenUtcHour>23 || InpFridayFlattenUtcHour<18 ||
      InpFridayFlattenUtcHour>21 || InpFridayFlattenUtcMinute<0 ||
      InpFridayFlattenUtcMinute>59 ||
      InpFridayFlattenUtcHour*60+InpFridayFlattenUtcMinute>=InpFlattenUtcHour*60)
      return false;
   return true;
  }

string SignalModeName()
  {
   if(InpSignalMode==SIGNAL_REPORT_FIDELITY)
      return "FULL_FIDELITY";
   if(InpSignalMode==SIGNAL_CONTEXT_STATE)
      return "CONTEXT_STATE";
   return "CONTROL_SWEEP";
  }

int OnInit()
  {
   if(!ValidateInputs())
      return INIT_PARAMETERS_INCORRECT;
   for(int index=0;index<MAX_SETUPS;index++)
      ClearSetup(g_setups[index]);
   g_adx_handle=iADX(_Symbol,PERIOD_M15,InpAdxPeriod);
   g_atr_handle=iATR(_Symbol,PERIOD_M5,14);
   if(g_adx_handle==INVALID_HANDLE || g_atr_handle==INVALID_HANDLE)
      return INIT_FAILED;
   trade.SetExpertMagicNumber((ulong)InpMagic);
   trade.SetDeviationInPoints((ulong)MathMax(1,MathRound(InpMaxSpreadPips*PipSize()/_Point)));
   trade.SetTypeFillingBySymbol(_Symbol);
   trade.SetAsyncMode(false);
   LoadPersistentRiskState();
   ResetRiskDayIfNeeded(TimeCurrent());
   g_peak_equity=MathMax(g_peak_equity,AccountInfoDouble(ACCOUNT_EQUITY));
   if(!RestoreOwnedPositionState())
      return INIT_FAILED;
   int actual_entries_today=CountActualEntryLifecyclesForUtcDay(g_day_key);
   if(actual_entries_today>=0)
     {
      g_trades_today=actual_entries_today;
      SavePersistentRiskState();
     }
   if(!OpenLifecycleTelemetry())
      return INIT_FAILED;
   PrintFormat("ICTFVG init hypothesis=%s mode=%s auto=%s news=%s count=%d sha256=%s promotion=false",
               HYPOTHESIS_ID,
               SignalModeName(),
               InpResearchAutoMode ? "true" : "false",
               InpRequireNewsGuard ? NEWS_CALENDAR_SOURCE_CLASS : "DISABLED",
               NEWS_CALENDAR_COUNT,NEWS_CALENDAR_SOURCE_SHA256);
   return INIT_SUCCEEDED;
  }

void OnDeinit(const int reason)
  {
   WriteRunMeta();
   SavePersistentRiskState();
   if(g_telemetry_handle!=INVALID_HANDLE)
     {
      FileFlush(g_telemetry_handle);
      FileClose(g_telemetry_handle);
      g_telemetry_handle=INVALID_HANDLE;
     }
   if(g_adx_handle!=INVALID_HANDLE)
      IndicatorRelease(g_adx_handle);
   if(g_atr_handle!=INVALID_HANDLE)
      IndicatorRelease(g_atr_handle);
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
     {
      g_peak_equity=equity;
      if(!MQLInfoInteger(MQL_TESTER))
         GlobalVariableSet(PersistentKey("peak"),g_peak_equity);
     }
   ManageOwnedPosition();
   datetime current_bar=iTime(_Symbol,PERIOD_M5,0);
   if(current_bar<=0)
      return;
   if(current_bar==g_last_m5_bar)
      return;
   g_last_m5_bar=current_bar;
   ProcessClosedM5Bar();
  }
