#property copyright "AlphaFactory research"
#property version   "1.00"
#property strict
#property description "Owner-authorized MZMS EURUSD M5 research EA"
#property description "Strict closed-bar control/challenger; no live or promotion authority"

#include <Trade/Trade.mqh>
#include "NewsCalendar2019_2022.mqh"

enum ENUM_SIGNAL_MODE
  {
   SIGNAL_CONTROL=0,
   SIGNAL_MZMS_CHALLENGER=1
  };

input bool             InpResearchAutoMode=false;
input bool             InpEnableTelemetry=true;
input ENUM_SIGNAL_MODE InpSignalMode=SIGNAL_MZMS_CHALLENGER;
input double           InpRiskPercent=0.01;
input long             InpMagic=5600721;

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
input double           InpStopBufferPips=0.50;
input double           InpTargetRR=1.60;
input int              InpMaxHoldBars=15;
input int              InpCooldownBars=5;
input bool             InpUseBreakEven=false;
input double           InpBreakEvenR=1.00;

input double           InpMaxSpreadPips=0.80;
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
const string HYPOTHESIS_ID="HYP-MZMS-MACD-HIST-SLOPE-EURUSD-M5-003";
const string TELEMETRY_PROFILE="lifecycle-v3";
const string REPORT_SHA256="0D8D8314273320FF2305557844C8200A9D4052F26D5F30039558B5951A361050";
const string SOURCE_DATA_SHA256="2959C555DB6690FD6EFD6CFB3B4C6323698E590C9B2D71E1E55F1902F724235A";
const string CLOCK_CONTRACT="fivepercent_server_eu_dst_to_utc_v1";

CTrade trade;
int g_macd_handle=INVALID_HANDLE;
int g_rsi_handle=INVALID_HANDLE;
int g_ema_handle=INVALID_HANDLE;
int g_adx_handle=INVALID_HANDLE;
int g_atr_handle=INVALID_HANDLE;
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
string g_run_id="";
string g_lifecycle_name="";
string g_run_meta_name="";
long g_bars_seen=0;
long g_extrema_rejections=0;
long g_delta_rejections=0;
long g_rsi_rejections=0;
long g_adx_rejections=0;
long g_news_rejections=0;
long g_spread_rejections=0;
long g_cooldown_rejections=0;
long g_risk_rejections=0;
long g_entries_attempted=0;
long g_entries_opened=0;

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
   double values[1];
   int copied=0;
   if(shift==1)
      copied=CopyBuffer(handle,buffer,1,1,values);
   else if(shift==2)
      copied=CopyBuffer(handle,buffer,2,1,values);
   else if(shift==3)
      copied=CopyBuffer(handle,buffer,3,1,values);
   else
      return false;
   if(copied!=1 || !MathIsValidNumber(values[0]))
      return false;
   value=values[0];
   return true;
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

int ClosedBarSignal(MqlRates &bars[],double &atr1)
  {
   double ema1=0.0,adx1=0.0,rsi1=0.0,rsi2=0.0;
   double main1=0.0,main2=0.0,main3=0.0;
   double signal1=0.0,signal2=0.0,signal3=0.0;
   if(!ReadIndicator(g_ema_handle,0,1,ema1) ||
      !ReadIndicator(g_adx_handle,0,1,adx1) ||
      !ReadIndicator(g_atr_handle,0,1,atr1) ||
      !ReadIndicator(g_rsi_handle,0,1,rsi1) ||
      !ReadIndicator(g_rsi_handle,0,2,rsi2) ||
      !ReadIndicator(g_macd_handle,0,1,main1) ||
      !ReadIndicator(g_macd_handle,0,2,main2) ||
      !ReadIndicator(g_macd_handle,0,3,main3) ||
      !ReadIndicator(g_macd_handle,1,1,signal1) ||
      !ReadIndicator(g_macd_handle,1,2,signal2) ||
      !ReadIndicator(g_macd_handle,1,3,signal3) || atr1<=0.0)
      return 0;
   if(adx1<InpMinAdx)
     {
      g_adx_rejections++;
      return 0;
     }
   bool bullish=bars[0].close>bars[0].open && bars[0].close>ema1;
   bool bearish=bars[0].close<bars[0].open && bars[0].close<ema1;
   if(InpSignalMode==SIGNAL_CONTROL)
      return bullish ? 1 : (bearish ? -1 : 0);

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
   double delta_atr=MathAbs(hist1-hist2)/atr1;
   if(delta_atr<InpMinHistDeltaAtr)
     {
      g_delta_rejections++;
      return 0;
     }
   bool rsi_long=rsi1>=InpRsiLower && rsi1<=InpRsiUpper && rsi1>rsi2;
   bool rsi_short=rsi1>=InpRsiLower && rsi1<=InpRsiUpper && rsi1<rsi2;
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

bool TryOpenTrade(const int direction,MqlRates &bars[],const double atr1,
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
   for(int index=1;index<InpStopLookbackBars;index++)
      structural=(direction>0 ? MathMin(structural,bars[index].low)
                              : MathMax(structural,bars[index].high));
   structural+=(direction>0 ? -1.0 : 1.0)*InpStopBufferPips*PipSize();
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
   bool sent=(direction>0 ? trade.Buy(volume,_Symbol,0.0,stop,target,HYPOTHESIS_ID)
                          : trade.Sell(volume,_Symbol,0.0,stop,target,HYPOTHESIS_ID));
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
      "{\"schema_version\":\"alphafactory_run_meta.v1\",\"run_id\":\"%s\",\"ea_name\":\"%s\",\"symbol\":\"%s\",\"telemetry_profile\":\"%s\",\"hypothesis_id\":\"%s\",\"signal_mode\":%d,\"promotion_eligible\":false,\"report_sha256\":\"%s\",\"source_data_sha256\":\"%s\",\"clock_contract\":\"%s\",\"cost_status\":\"UNVERIFIED_DIAGNOSTIC\",\"news_status\":\"%s\",\"news_source_sha256\":\"%s\",\"diagnostic\":{\"bars_seen\":%I64d,\"extrema_rejections\":%I64d,\"delta_rejections\":%I64d,\"rsi_rejections\":%I64d,\"adx_rejections\":%I64d,\"news_rejections\":%I64d,\"spread_rejections\":%I64d,\"cooldown_rejections\":%I64d,\"risk_rejections\":%I64d,\"entries_attempted\":%I64d,\"entries_opened\":%I64d}}",
      g_run_id,EA_NAME,_Symbol,TELEMETRY_PROFILE,HYPOTHESIS_ID,(int)InpSignalMode,
      REPORT_SHA256,SOURCE_DATA_SHA256,CLOCK_CONTRACT,
      InpRequireNewsGuard ? NEWS_CALENDAR_SOURCE_CLASS : "DISABLED",NEWS_CALENDAR_SOURCE_SHA256,
      g_bars_seen,g_extrema_rejections,g_delta_rejections,g_rsi_rejections,
      g_adx_rejections,g_news_rejections,g_spread_rejections,g_cooldown_rejections,
      g_risk_rejections,g_entries_attempted,g_entries_opened);
   FileWriteString(handle,payload);
   FileClose(handle);
   return true;
  }

bool OpenTelemetry()
  {
   if(!InpEnableTelemetry)
      return true;
   g_run_id=StringFormat("%s_%I64u",HYPOTHESIS_ID,GetTickCount64());
   g_lifecycle_name=StringFormat("%s_LifecycleTrades_%s.csv",_Symbol,g_run_id);
   g_run_meta_name=StringFormat("%s_RunMeta_%s.json",_Symbol,g_run_id);
   g_telemetry_handle=FileOpen(g_lifecycle_name,FILE_WRITE|FILE_CSV|FILE_ANSI,',');
   if(g_telemetry_handle==INVALID_HANDLE)
      return false;
   FileWrite(g_telemetry_handle,"event_time","action","order_type","volume","price","symbol",
             "position_id","risk_pts","initial_risk_account","deal","deal_profit",
             "deal_commission","deal_swap","deal_fee","deal_net","is_final_close");
   FileFlush(g_telemetry_handle);
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
   g_adx_handle=iADX(_Symbol,PERIOD_M5,InpAdxPeriod);
   g_atr_handle=iATR(_Symbol,PERIOD_M5,InpAtrPeriod);
   if(g_macd_handle==INVALID_HANDLE || g_rsi_handle==INVALID_HANDLE ||
      g_ema_handle==INVALID_HANDLE || g_adx_handle==INVALID_HANDLE || g_atr_handle==INVALID_HANDLE)
      return INIT_FAILED;
   trade.SetExpertMagicNumber((ulong)InpMagic);
   trade.SetDeviationInPoints((ulong)MathMax(1,MathRound(InpMaxSpreadPips*PipSize()/_Point)));
   trade.SetTypeFillingBySymbol(_Symbol);
   trade.SetAsyncMode(false);
   g_peak_equity=AccountInfoDouble(ACCOUNT_EQUITY);
   ResetRiskDayIfNeeded(TimeCurrent());
   if(!OpenTelemetry())
      return INIT_FAILED;
   PrintFormat("MZMS init hypothesis=%s mode=%d auto=%s closed_bar=true BE=%s promotion=false",
               HYPOTHESIS_ID,(int)InpSignalMode,InpResearchAutoMode ? "true" : "false",
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
   if(g_macd_handle!=INVALID_HANDLE) IndicatorRelease(g_macd_handle);
   if(g_rsi_handle!=INVALID_HANDLE) IndicatorRelease(g_rsi_handle);
   if(g_ema_handle!=INVALID_HANDLE) IndicatorRelease(g_ema_handle);
   if(g_adx_handle!=INVALID_HANDLE) IndicatorRelease(g_adx_handle);
   if(g_atr_handle!=INVALID_HANDLE) IndicatorRelease(g_atr_handle);
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
   if(CopyRates(_Symbol,PERIOD_M5,1,InpStopLookbackBars,bars)!=InpStopLookbackBars)
      return;
   double atr1=0.0;
   int direction=ClosedBarSignal(bars,atr1);
   if(direction!=0)
      TryOpenTrade(direction,bars,atr1,current_bar);
  }
