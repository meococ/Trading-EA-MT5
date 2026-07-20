#property copyright "AlphaFactory research"
#property version   "1.00"
#property strict
#property description "Owner-authorized LSS-OB EURUSD M15 MT5 diagnostic EA"
#property description "Closed-bar control/challenger; no optimization, promotion, or live authority"

#include <Trade/Trade.mqh>
#include "NewsCalendar2019_2022.mqh"

enum ENUM_SIGNAL_MODE
  {
   SIGNAL_CONTROL=0,
   SIGNAL_LSS_OB_CHALLENGER=1
  };

enum ENUM_SETUP_STAGE
  {
   SETUP_EMPTY=0,
   SETUP_SWEPT=1,
   SETUP_DISPLACED=2
  };

input bool             InpResearchAutoMode=false;
input bool             InpEnableTelemetry=true;
input ENUM_SIGNAL_MODE InpSignalMode=SIGNAL_LSS_OB_CHALLENGER;
input double           InpRiskPercent=0.25;
input long             InpMagic=5601502;

input int              InpPivotStrength=2;
input int              InpSweepLookback=20;
input int              InpDisplacementBars=3;
input double           InpDisplacementAtrMultiple=1.80;
input int              InpAtrPeriod=14;
input int              InpRetestBars=12;
input double           InpConfirmationBodyRatio=0.60;
input double           InpConfirmationOuterFraction=0.25;
input int              InpContextM15Bars=3000;
input int              InpAdxPeriod=14;
input double           InpMinAdx=25.0;

input double           InpStopBufferPips=1.50;
input double           InpMinStopPips=8.00;
input double           InpMaxStopPips=12.00;
input double           InpTargetRR=2.00;
input double           InpMaxSpreadPips=1.80;
input int              InpMaxTradesPerDay=2;
input double           InpDailyLossPct=1.50;
input double           InpMaxAccountDrawdownPct=8.00;
input int              InpMaxConsecutiveLosses=2;
input int              InpCooldownMinutes=120;
input int              InpFlattenUtcHour=21;
input int              InpFlattenUtcMinute=45;
input int              InpServerUtcOffsetWinterHours=2;
input bool             InpServerUsesEuropeDst=true;
input bool             InpRequireNewsGuard=true;
input int              InpNewsBlackoutMinutes=30;

const string EA_NAME="EA_LSSOBPropScalper";
const string HYPOTHESIS_ID="HYP-LSS-OB-REPL-MT5-EURUSD-M15-002";
const string TELEMETRY_PROFILE="lifecycle-v3";
const string REPORT_SHA256="8F3EE339C52B7271CC9382DE21379E8C35C0D1646CEF133D1050D083FEC19223";
const string SOURCE_DATA_SHA256="2959C555DB6690FD6EFD6CFB3B4C6323698E590C9B2D71E1E55F1902F724235A";
const string CLOCK_CONTRACT="fivepercent_eu_dst_server_to_utc_custom_h1_h4";
const int LONDON_START_UTC_MIN=7*60;
const int LONDON_END_UTC_MIN=10*60;
const int NEW_YORK_START_UTC_MIN=13*60;
const int NEW_YORK_END_UTC_MIN=16*60;

struct UtcBar
  {
   datetime time;
   double open;
   double high;
   double low;
   double close;
  };

struct SetupState
  {
   ENUM_SETUP_STAGE stage;
   int direction;
   int utc_date_key;
   int session_id;
   int bars_in_stage;
   datetime pivot_time;
   datetime sweep_time;
   double sweep_high;
   double sweep_low;
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
  };

CTrade trade;
SetupState g_setup;
int g_adx_handle=INVALID_HANDLE;
int g_atr_handle=INVALID_HANDLE;
datetime g_last_m15_bar=0;
datetime g_context_h1_bucket=0;
datetime g_context_h4_bucket=0;
int g_h1_bias=0;
double g_h4_low=0.0;
double g_h4_high=0.0;

int g_day_key=0;
double g_day_start_equity=0.0;
double g_peak_equity=0.0;
int g_trades_today=0;
int g_consecutive_losses=0;
datetime g_cooldown_until=0;

ulong g_position_identifier=0;
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
   // Multiple distinct releases may share one scheduled epoch. The search
   // contract requires a nondecreasing array, not unique timestamps.
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
   return StringFormat("LSSOB.%s.%I64d.%s",_Symbol,InpMagic,suffix);
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
   GlobalVariableSet(PersistentKey("poslo"),(double)position_low);
   GlobalVariableSet(PersistentKey("poshi"),(double)position_high);
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

bool LifecycleNetFromHistory(const ulong position_id,double &lifecycle_net)
  {
   lifecycle_net=0.0;
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
      found=true;
     }
   return found;
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
      PrintFormat("LSSOB emergency close retry pending reason=%s retcode=%u %s",
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
   if(LifecycleNetFromHistory(position_id,history_net))
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
      return false;
   if(NewsBlocked(server_time))
     {
      g_news_rejections++;
      return false;
     }
   if(EligibleSession(server_time)==0 ||
      UtcMinute(server_time)>=InpFlattenUtcHour*60+InpFlattenUtcMinute)
      return false;
   if(g_trades_today>=InpMaxTradesPerDay || DailyLossHit() || AccountDrawdownHit() || CooldownActive())
      return false;
   if(OwnedPositionTicket()!=0 || OwnedPendingOrderExists() || ForeignSymbolExposure())
      return false;
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
   double risk_pips=risk_price/PipSize();
   if(risk_price<=0.0 || risk_pips<InpMinStopPips || risk_pips>InpMaxStopPips)
     {
      g_risk_rejections++;
      return false;
     }
   double target=NormalizeDouble(entry+(direction>0 ? 1.0 : -1.0)*InpTargetRR*risk_price,_Digits);
   if(!StopGeometryValid(direction,entry,stop,target))
     {
      g_risk_rejections++;
      return false;
     }

   double risk_account=0.0;
   double volume=RiskSizedVolume(direction,entry,stop,risk_account);
   if(volume<=0.0)
     {
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
   if(!OrderCheck(request,check) || (check.retcode!=TRADE_RETCODE_DONE && check.retcode!=TRADE_RETCODE_PLACED))
     {
      PrintFormat("LSSOB OrderCheck rejected retcode=%u comment=%s",check.retcode,check.comment);
      g_risk_rejections++;
      return false;
     }

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
      PrintFormat("LSSOB entry failed retcode=%u %s",retcode,trade.ResultRetcodeDescription());
      ClearPositionRiskState();
      return false;
     }
   // Opened-lifecycle and daily-trade counters advance only on the first
   // actual DEAL_ENTRY_IN transaction, never on a merely accepted request.
   SavePersistentRiskState();
   return true;
  }


bool IsM15PivotHigh(const MqlRates &bars[],const int count,const int index,const int strength)
  {
   if(index-strength<0 || index+strength>=count)
      return false;
   for(int offset=1;offset<=strength;offset++)
      if(bars[index].high<=bars[index-offset].high || bars[index].high<=bars[index+offset].high)
         return false;
   return true;
  }

bool IsM15PivotLow(const MqlRates &bars[],const int count,const int index,const int strength)
  {
   if(index-strength<0 || index+strength>=count)
      return false;
   for(int offset=1;offset<=strength;offset++)
      if(bars[index].low>=bars[index-offset].low || bars[index].low>=bars[index+offset].low)
         return false;
   return true;
  }

bool IsUtcPivotHigh(const UtcBar &bars[],const int count,const int index,const int strength)
  {
   if(index-strength<0 || index+strength>=count)
      return false;
   for(int offset=1;offset<=strength;offset++)
      if(bars[index].high<=bars[index-offset].high || bars[index].high<=bars[index+offset].high)
         return false;
   return true;
  }

bool IsUtcPivotLow(const UtcBar &bars[],const int count,const int index,const int strength)
  {
   if(index-strength<0 || index+strength>=count)
      return false;
   for(int offset=1;offset<=strength;offset++)
      if(bars[index].low>=bars[index-offset].low || bars[index].low>=bars[index+offset].low)
         return false;
   return true;
  }

int BuildClosedUtcBars(const int timeframe_minutes,UtcBar &output[])
  {
   ArrayResize(output,0);
   MqlRates source[];
   ArraySetAsSeries(source,true);
   int copied=CopyRates(_Symbol,PERIOD_M15,1,InpContextM15Bars,source);
   if(copied<20)
      return 0;
   datetime cutoff=ServerToUtc(source[0].time+PeriodSeconds(PERIOD_M15));
   long span=(long)timeframe_minutes*60;
   for(int index=copied-1;index>=0;index--)
     {
      datetime utc_open=ServerToUtc(source[index].time);
      datetime bucket=(datetime)(((long)utc_open/span)*span);
      int size=ArraySize(output);
      if(size==0 || output[size-1].time!=bucket)
        {
         ArrayResize(output,size+1);
         output[size].time=bucket;
         output[size].open=source[index].open;
         output[size].high=source[index].high;
         output[size].low=source[index].low;
         output[size].close=source[index].close;
        }
      else
        {
         output[size-1].high=MathMax(output[size-1].high,source[index].high);
         output[size-1].low=MathMin(output[size-1].low,source[index].low);
         output[size-1].close=source[index].close;
        }
     }
   int size=ArraySize(output);
   while(size>0 && output[size-1].time+span>cutoff)
     {
      size--;
      ArrayResize(output,size);
     }
   return size;
  }

int LatestBosDirection(const UtcBar &bars[],const int count,const int strength)
  {
   if(count<2*strength+10)
      return 0;
   double latest_high=0.0;
   double latest_low=0.0;
   bool have_high=false;
   bool have_low=false;
   int bias=0;
   for(int confirmation=strength*2;confirmation<count;confirmation++)
     {
      int pivot=confirmation-strength;
      if(IsUtcPivotHigh(bars,count,pivot,strength))
        {
         latest_high=bars[pivot].high;
         have_high=true;
        }
      if(IsUtcPivotLow(bars,count,pivot,strength))
        {
         latest_low=bars[pivot].low;
         have_low=true;
        }
      if(have_high && bars[confirmation].close>latest_high)
         bias=1;
      else if(have_low && bars[confirmation].close<latest_low)
         bias=-1;
     }
   return bias;
  }

bool LatestConfirmedRange(const UtcBar &bars[],const int count,const int strength,
                          double &range_low,double &range_high)
  {
   bool have_high=false;
   bool have_low=false;
   for(int confirmation=strength*2;confirmation<count;confirmation++)
     {
      int pivot=confirmation-strength;
      if(IsUtcPivotHigh(bars,count,pivot,strength))
        {
         range_high=bars[pivot].high;
         have_high=true;
        }
      if(IsUtcPivotLow(bars,count,pivot,strength))
        {
         range_low=bars[pivot].low;
         have_low=true;
        }
     }
   return have_high && have_low && range_low<range_high;
  }

bool RefreshContext(const datetime server_bar_time)
  {
   datetime utc_open=ServerToUtc(server_bar_time);
   datetime h1_bucket=(datetime)(((long)utc_open/(60*60))*(60*60));
   datetime h4_bucket=(datetime)(((long)utc_open/(4*60*60))*(4*60*60));
   if(h1_bucket!=g_context_h1_bucket)
     {
      UtcBar h1[];
      int count=BuildClosedUtcBars(60,h1);
      g_h1_bias=LatestBosDirection(h1,count,InpPivotStrength);
      g_context_h1_bucket=h1_bucket;
     }
   if(h4_bucket!=g_context_h4_bucket)
     {
      UtcBar h4[];
      int count=BuildClosedUtcBars(240,h4);
      if(!LatestConfirmedRange(h4,count,InpPivotStrength,g_h4_low,g_h4_high))
        {
         g_h4_low=0.0;
         g_h4_high=0.0;
        }
      g_context_h4_bucket=h4_bucket;
     }
   return g_h1_bias!=0 && g_h4_low>0.0 && g_h4_high>g_h4_low;
  }

bool ContextAligned(const double price,const int direction)
  {
   if(g_h1_bias!=direction || g_h4_low<=0.0 || g_h4_high<=g_h4_low)
      return false;
   if(price<g_h4_low || price>g_h4_high)
      return false;
   double midpoint=0.5*(g_h4_low+g_h4_high);
   return direction>0 ? price<=midpoint : price>=midpoint;
  }

bool FindLatestM15Pivots(const MqlRates &bars[],const int count,
                         double &pivot_high,double &pivot_low,
                         datetime &pivot_high_time,datetime &pivot_low_time)
  {
   bool high_found=false;
   bool low_found=false;
   int limit=MathMin(count-InpPivotStrength-1,InpSweepLookback);
   for(int index=InpPivotStrength;index<=limit;index++)
     {
      if(!high_found && IsM15PivotHigh(bars,count,index,InpPivotStrength))
        {
         pivot_high=bars[index].high;
         pivot_high_time=bars[index].time;
         high_found=true;
        }
      if(!low_found && IsM15PivotLow(bars,count,index,InpPivotStrength))
        {
         pivot_low=bars[index].low;
         pivot_low_time=bars[index].time;
         low_found=true;
        }
      if(high_found && low_found)
         return true;
     }
   return false;
  }

bool ClosedAdx(double &value)
  {
   double values[];
   ArraySetAsSeries(values,true);
   if(CopyBuffer(g_adx_handle,0,1,1,values)!=1)
      return false;
   value=values[0];
   return MathIsValidNumber(value) && value>=0.0;
  }

double ClosedAtr()
  {
   double values[];
   ArraySetAsSeries(values,true);
   if(CopyBuffer(g_atr_handle,0,1,1,values)!=1)
      return 0.0;
   return values[0];
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

bool FindOrderBlock(const int direction,const MqlRates &bars[],const int count,
                    const datetime sweep_time,MqlRates &ob)
  {
   int limit=MathMin(count-1,InpDisplacementBars);
   for(int index=1;index<=limit;index++)
     {
      if(bars[index].time<sweep_time)
         break;
      bool opposite=(direction>0 ? bars[index].close<bars[index].open
                                 : bars[index].close>bars[index].open);
      if(!opposite)
         continue;
      bool invalid=false;
      for(int intermediate=1;intermediate<index;intermediate++)
        {
         if((direction>0 && bars[intermediate].close<bars[index].low) ||
            (direction<0 && bars[intermediate].close>bars[index].high))
           {
            invalid=true;
            break;
           }
        }
      if(!invalid)
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
   return overlap_high>overlap_low;
  }

bool BarIntersects(const MqlRates &bar,const double low,const double high)
  {
   return bar.low<=high && bar.high>=low;
  }

bool IsConfirmation(const MqlRates &current,const MqlRates &previous,const int direction)
  {
   double range=current.high-current.low;
   if(range<=0.0)
      return false;
   bool directional=(direction>0 ? current.close>current.open : current.close<current.open);
   bool engulf=(direction>0 ? current.close>current.open && current.open<=previous.close && current.close>=previous.open
                            : current.close<current.open && current.open>=previous.close && current.close<=previous.open);
   double ratio=MathAbs(current.close-current.open)/range;
   bool outer=(direction>0 ? current.close>=current.low+(1.0-InpConfirmationOuterFraction)*range
                           : current.close<=current.low+InpConfirmationOuterFraction*range);
   return engulf || (directional && ratio>=InpConfirmationBodyRatio && outer);
  }

void ClearSetup(SetupState &setup)
  {
   ZeroMemory(setup);
   setup.stage=SETUP_EMPTY;
  }

void DetectSweep(const MqlRates &bars[],const int count,const int date_key,const int session_id)
  {
   if(g_setup.stage!=SETUP_EMPTY || session_id==0 || !RefreshContext(bars[0].time))
      return;
   double pivot_high=0.0;
   double pivot_low=0.0;
   datetime high_time=0;
   datetime low_time=0;
   if(!FindLatestM15Pivots(bars,count,pivot_high,pivot_low,high_time,low_time))
      return;
   int direction=0;
   datetime pivot_time=0;
   if(bars[0].low<pivot_low && bars[0].close>pivot_low && ContextAligned(bars[0].close,1))
     {
      direction=1;
      pivot_time=low_time;
     }
   else if(bars[0].high>pivot_high && bars[0].close<pivot_high && ContextAligned(bars[0].close,-1))
     {
      direction=-1;
      pivot_time=high_time;
     }
   if(direction==0)
      return;
   ClearSetup(g_setup);
   g_setup.stage=SETUP_SWEPT;
   g_setup.direction=direction;
   g_setup.utc_date_key=date_key;
   g_setup.session_id=session_id;
   g_setup.pivot_time=pivot_time;
   g_setup.sweep_time=bars[0].time;
   g_setup.sweep_high=bars[0].high;
   g_setup.sweep_low=bars[0].low;
   g_sweeps++;
  }

bool CommonSignalGates()
  {
   double adx=0.0;
   if(!ClosedAdx(adx) || adx<=InpMinAdx)
     {
      g_adx_rejections++;
      return false;
     }
   return true;
  }

void AdvanceDisplacement(const MqlRates &bars[],const int count,const int date_key,const int session_id)
  {
   if(g_setup.stage!=SETUP_SWEPT || bars[0].time<=g_setup.sweep_time)
      return;
   if(g_setup.utc_date_key!=date_key || session_id!=g_setup.session_id ||
      !RefreshContext(bars[0].time) || !ContextAligned(bars[0].close,g_setup.direction) ||
      (g_setup.direction>0 && bars[0].close<g_setup.sweep_low) ||
      (g_setup.direction<0 && bars[0].close>g_setup.sweep_high))
     {
      ClearSetup(g_setup);
      return;
     }
   g_setup.bars_in_stage++;
   if(g_setup.bars_in_stage>InpDisplacementBars)
     {
      ClearSetup(g_setup);
      return;
     }
   double atr=ClosedAtr();
   double body=MathAbs(bars[0].close-bars[0].open);
   bool directional=(g_setup.direction>0 ? bars[0].close>bars[0].open
                                         : bars[0].close<bars[0].open);
   if(!directional || atr<=0.0 || body<InpDisplacementAtrMultiple*atr)
      return;
   double fvg_low=0.0;
   double fvg_high=0.0;
   if(!StrictFvg(g_setup.direction,bars[0],bars[2],fvg_low,fvg_high))
      return;
   MqlRates ob;
   if(!FindOrderBlock(g_setup.direction,bars,count,g_setup.sweep_time,ob))
      return;
   double ob_body_low=MathMin(ob.open,ob.close);
   double ob_body_high=MathMax(ob.open,ob.close);
   double overlap_low=0.0;
   double overlap_high=0.0;
   if(!OverlapZone(fvg_low,fvg_high,ob_body_low,ob_body_high,overlap_low,overlap_high))
      return;
   g_setup.stage=SETUP_DISPLACED;
   g_setup.bars_in_stage=0;
   g_setup.displacement_time=bars[0].time;
   g_setup.fvg_low=fvg_low;
   g_setup.fvg_high=fvg_high;
   g_setup.ob_low=ob.low;
   g_setup.ob_high=ob.high;
   g_setup.ob_body_low=ob_body_low;
   g_setup.ob_body_high=ob_body_high;
   g_setup.overlap_low=overlap_low;
   g_setup.overlap_high=overlap_high;
   g_setup.stop=(g_setup.direction>0 ? MathMin(g_setup.sweep_low,ob.low)-PipsToPrice(InpStopBufferPips)
                                     : MathMax(g_setup.sweep_high,ob.high)+PipsToPrice(InpStopBufferPips));
   g_displacements++;
   g_fvgs++;
   if(InpSignalMode==SIGNAL_CONTROL)
     {
      if(CommonSignalGates())
         TryOpenTrade(g_setup.direction,g_setup.stop,"LSSOB_CONTROL");
      ClearSetup(g_setup);
     }
  }

void AdvanceRetest(const MqlRates &bars[],const int date_key,const int session_id)
  {
   if(g_setup.stage!=SETUP_DISPLACED || bars[0].time<=g_setup.displacement_time)
      return;
   g_setup.bars_in_stage++;
   if(g_setup.bars_in_stage>InpRetestBars || g_setup.utc_date_key!=date_key ||
      session_id!=g_setup.session_id || !RefreshContext(bars[0].time) ||
      !ContextAligned(bars[0].close,g_setup.direction) ||
      (g_setup.direction>0 && bars[0].close<g_setup.sweep_low) ||
      (g_setup.direction<0 && bars[0].close>g_setup.sweep_high))
     {
      ClearSetup(g_setup);
      return;
     }
   if(!BarIntersects(bars[0],g_setup.overlap_low,g_setup.overlap_high))
      return;
   if(IsConfirmation(bars[0],bars[1],g_setup.direction))
     {
      g_retests++;
      if(CommonSignalGates())
         TryOpenTrade(g_setup.direction,g_setup.stop,"LSSOB_CHALLENGER");
     }
   ClearSetup(g_setup); // first overlap touch only
  }

void ProcessClosedM15Bar()
  {
   int requested=MathMax(100,InpSweepLookback+2*InpPivotStrength+20);
   MqlRates bars[];
   ArraySetAsSeries(bars,true);
   int copied=CopyRates(_Symbol,PERIOD_M15,1,requested,bars);
   if(copied<50)
      return;
   ResetRiskDayIfNeeded(bars[0].time);
   int date_key=UtcDateKey(bars[0].time);
   int session_id=EligibleSession(bars[0].time);
   if(g_setup.stage==SETUP_SWEPT)
      AdvanceDisplacement(bars,copied,date_key,session_id);
   else if(g_setup.stage==SETUP_DISPLACED)
      AdvanceRetest(bars,date_key,session_id);
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
      "{\"schema_version\":\"alphafactory_run_meta.v1\",\"run_id\":\"%s\",\"ea_name\":\"%s\",\"symbol\":\"%s\",\"telemetry_profile\":\"%s\",\"hypothesis_id\":\"%s\",\"signal_mode\":%d,\"promotion_eligible\":false,\"report_sha256\":\"%s\",\"source_data_sha256\":\"%s\",\"clock_contract\":\"%s\",\"cost_status\":\"UNVERIFIED_DIAGNOSTIC\",\"news_status\":\"%s\",\"news_source_sha256\":\"%s\",\"news_blackout_minutes\":%d,\"diagnostic\":{\"days_seen\":%I64d,\"sweeps\":%I64d,\"displacements\":%I64d,\"fvgs\":%I64d,\"confirmed_retests\":%I64d,\"adx_rejections\":%I64d,\"news_rejections\":%I64d,\"spread_rejections\":%I64d,\"risk_rejections\":%I64d,\"entries_attempted\":%I64d,\"entries_opened\":%I64d,\"fill_risk_closes\":%I64d}}",
      g_run_id,EA_NAME,_Symbol,TELEMETRY_PROFILE,HYPOTHESIS_ID,(int)InpSignalMode,
      REPORT_SHA256,SOURCE_DATA_SHA256,CLOCK_CONTRACT,
      news_status,NEWS_CALENDAR_SOURCE_SHA256,InpNewsBlackoutMinutes,
      g_days_seen,g_sweeps,g_displacements,g_fvgs,g_retests,g_adx_rejections,
      g_news_rejections,g_spread_rejections,g_risk_rejections,
      g_entries_attempted,g_entries_opened,g_fill_risk_closes);
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
      PrintFormat("LSSOB actual fill risk %.2f exceeds plan %.2f; closing",actual_risk,g_planned_risk_account);
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
   if(LifecycleNetFromHistory(position_id,authoritative_net))
      g_position_lifecycle_net=authoritative_net;
   else
      g_position_lifecycle_net+=net;
   if(InpEnableTelemetry && g_telemetry_handle!=INVALID_HANDLE)
     {
      datetime event_time=(datetime)HistoryDealGetInteger(deal,DEAL_TIME);
      FileWrite(g_telemetry_handle,
                TimeToString(event_time,TIME_DATE|TIME_SECONDS),action,
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
      if(g_position_lifecycle_net<0.0)
        {
         g_consecutive_losses++;
         if(g_consecutive_losses>=InpMaxConsecutiveLosses)
            g_cooldown_until=TimeCurrent()+InpCooldownMinutes*60;
        }
      else
         g_consecutive_losses=0;
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
   if(now_key!=g_position_entry_utc_key ||
      minute>=InpFlattenUtcHour*60+InpFlattenUtcMinute || AccountDrawdownHit())
     {
      if(!trade.PositionClose(ticket))
         PrintFormat("LSSOB flatten failed retcode=%u %s",trade.ResultRetcode(),trade.ResultRetcodeDescription());
      return;
     }
   // V1 is fixed SL/2R only: no break-even, partial, or trailing logic.
  }

bool ValidateInputs()
  {
   if(_Period!=PERIOD_M15)
     {
      Print("EA_LSSOBPropScalper requires M15.");
      return false;
     }
   if(InpRequireNewsGuard && !NewsCalendarValid())
     {
      Print("Historical news guard calendar failed validation; fail closed.");
      return false;
     }
   if(InpRiskPercent<=0.0 || InpRiskPercent>1.0 || InpPivotStrength<1 ||
      InpSweepLookback<5 || InpDisplacementBars<1 ||
      InpDisplacementAtrMultiple<=1.0 || InpAtrPeriod<5 ||
      InpRetestBars<1 || InpConfirmationBodyRatio<=0.0 ||
      InpConfirmationBodyRatio>1.0 || InpConfirmationOuterFraction<=0.0 ||
      InpConfirmationOuterFraction>=0.5 || InpContextM15Bars<500 ||
      InpAdxPeriod<5 || InpMinAdx<=0.0 || InpStopBufferPips<=0.0 ||
      InpMinStopPips<=0.0 || InpMaxStopPips<=InpMinStopPips ||
      InpTargetRR<1.0 || InpMaxSpreadPips<=0.0 || InpMaxTradesPerDay<1 ||
      InpDailyLossPct<=0.0 || InpMaxAccountDrawdownPct<=0.0 ||
      InpMaxConsecutiveLosses<1 || InpCooldownMinutes<1 ||
      InpNewsBlackoutMinutes<1 || InpNewsBlackoutMinutes>180 ||
      InpFlattenUtcHour<18 || InpFlattenUtcHour>23 ||
      InpFlattenUtcMinute<0 || InpFlattenUtcMinute>59)
      return false;
   return true;
  }

int OnInit()
  {
   if(!ValidateInputs())
      return INIT_PARAMETERS_INCORRECT;
   ClearSetup(g_setup);
   g_adx_handle=iADX(_Symbol,PERIOD_M15,InpAdxPeriod);
   g_atr_handle=iATR(_Symbol,PERIOD_M15,InpAtrPeriod);
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
   if(!OpenLifecycleTelemetry())
      return INIT_FAILED;
   PrintFormat("LSSOB init hypothesis=%s mode=%s auto=%s news=%s count=%d sha256=%s promotion=false",
               HYPOTHESIS_ID,
               InpSignalMode==SIGNAL_LSS_OB_CHALLENGER ? "LSS_OB_CHALLENGER" : "CONTROL",
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
   datetime current_bar=iTime(_Symbol,PERIOD_M15,0);
   if(current_bar<=0)
      return;
   if(current_bar==g_last_m15_bar)
      return;
   g_last_m15_bar=current_bar;
   ProcessClosedM15Bar();
  }
