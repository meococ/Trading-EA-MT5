#property copyright "AlphaFactory research"
#property version   "1.00"
#property strict

#include <Trade/Trade.mqh>
#include "research/generated/KLR_DTWEXBGS_Data.mqh"

input bool   InpResearchAutoMode=false;
input bool   InpEnableTelemetry=true;
input bool   InpRequireUsdGate=true;
input double InpRiskPercent=0.25;
input long   InpMagic=5600718;
input int    InpAtrPeriod=14;
input int    InpPivotStrength=2;
input double InpDisplacementAtr=1.00;
input int    InpDisplacementBars=4;
input int    InpRetestBars=6;
input double InpStopAtrBuffer=0.10;
input double InpTargetRR=2.00;
input int    InpMaxHoldBars=12;
input int    InpMaxTradesPerDay=1;
input int    InpLondonStartMinuteET=120;
input int    InpLondonEndMinuteET=300;
input int    InpNyStartMinuteET=510;
input int    InpNyEndMinuteET=660;
input int    InpMaxSpreadPoints=35;
input int    InpServerUtcOffsetWinterHours=2;
input bool   InpServerUsesEuropeDst=true;
input bool   InpUseFileCommon=false;

const string EA_NAME="EA_KLR_Scalper";
const string HYPOTHESIS_ID="HYP-KLR-MT5-REPLICATION-M5-XAU-001";
const string TELEMETRY_PROFILE="lifecycle-v3";
#define MAX_RAID_STATES 48
#define MAX_FVG_STATES 96

struct RaidState
  {
   bool active;
   int direction;
   int et_date_key;
   int window_id;
   int bars_after;
   datetime sweep_time;
   double sweep_high;
   double sweep_low;
   double stop;
  };

struct FvgState
  {
   bool active;
   int direction;
   int et_date_key;
   int window_id;
   int bars_after;
   datetime displacement_time;
   double zone_low;
   double zone_high;
   double stop;
  };

CTrade trade;
RaidState g_raids[MAX_RAID_STATES];
FvgState g_fvgs[MAX_FVG_STATES];
int g_atr_handle=INVALID_HANDLE;
datetime g_last_m5_bar=0;
int g_trade_day_key=0;
int g_position_day_key=0;
int g_position_window_id=0;
datetime g_position_entry_bar=0;
double g_peak_equity=0.0;
double g_planned_risk_points=0.0;
double g_planned_risk_account=0.0;
ulong g_position_identifier=0;
ENUM_ORDER_TYPE g_entry_order_type=ORDER_TYPE_BUY;
int g_telemetry_handle=INVALID_HANDLE;
string g_run_id="";
string g_lifecycle_name="";
string g_run_meta_name="";
long g_days_seen=0;
long g_sweeps=0;
long g_displacements=0;
long g_strict_fvgs=0;
long g_retests=0;
long g_usd_aligned_retests=0;
long g_entries_attempted=0;
long g_entries_opened=0;
long g_geometry_rejections=0;
long g_spread_rejections=0;

string SafeRunToken()
  {
   return StringFormat("%s_%I64u",HYPOTHESIS_ID,GetTickCount64());
  }

bool WriteRunMeta()
  {
   if(!InpEnableTelemetry || g_run_meta_name=="")
      return true;
   int handle=FileOpen(g_run_meta_name,FILE_WRITE|FILE_TXT|FILE_ANSI);
   if(handle==INVALID_HANDLE)
     {
      Print("KLR RunMeta open failed: ",GetLastError());
      return false;
     }
   string payload=StringFormat(
      "{\"schema_version\":\"alphafactory_run_meta.v1\",\"run_id\":\"%s\",\"ea_name\":\"%s\",\"symbol\":\"%s\",\"telemetry_profile\":\"%s\",\"hypothesis_id\":\"%s\",\"require_usd_gate\":%s,\"diagnostic\":{\"days_seen\":%I64d,\"sweeps\":%I64d,\"displacements\":%I64d,\"strict_fvgs\":%I64d,\"retests\":%I64d,\"usd_aligned_retests\":%I64d,\"entries_attempted\":%I64d,\"entries_opened\":%I64d,\"geometry_rejections\":%I64d,\"spread_rejections\":%I64d},\"usd_source_sha256\":\"%s\"}",
      g_run_id,EA_NAME,_Symbol,TELEMETRY_PROFILE,HYPOTHESIS_ID,
      InpRequireUsdGate ? "true" : "false",g_days_seen,g_sweeps,
      g_displacements,g_strict_fvgs,g_retests,g_usd_aligned_retests,
      g_entries_attempted,g_entries_opened,g_geometry_rejections,
      g_spread_rejections,KLR_DTWEXBGS_SOURCE_SHA256);
   FileWriteString(handle,payload);
   FileClose(handle);
   return true;
  }

bool OpenLifecycleTelemetry()
  {
   if(!InpEnableTelemetry)
      return true;
   g_run_id=SafeRunToken();
   g_lifecycle_name=StringFormat("%s_LifecycleTrades_%s.csv",_Symbol,g_run_id);
   g_run_meta_name=StringFormat("%s_RunMeta_%s.json",_Symbol,g_run_id);
   g_telemetry_handle=FileOpen(g_lifecycle_name,FILE_WRITE|FILE_CSV|FILE_ANSI,',');
   if(g_telemetry_handle==INVALID_HANDLE)
     {
      Print("KLR lifecycle telemetry open failed: ",GetLastError());
      return false;
     }
   FileWrite(g_telemetry_handle,
             "event_time","action","order_type","volume","price","symbol",
             "position_id","risk_pts","initial_risk_account","deal",
             "deal_profit","deal_commission","deal_swap","deal_fee","deal_net",
             "is_final_close");
   FileFlush(g_telemetry_handle);
   return WriteRunMeta();
  }

bool ValidateInputs()
  {
   if(_Period!=PERIOD_M5)
     {
      Print("KLR replication requires M5 tester period.");
      return false;
     }
   if(!InpResearchAutoMode)
      Print("KLR is in alert-only mode; tester replication requires explicit research auto mode.");
   if(InpUseFileCommon)
     {
      Print("KLR forbids the common-file sandbox.");
      return false;
     }
   if(InpRiskPercent<=0.0 || InpRiskPercent>1.0 || InpAtrPeriod<5 ||
      InpPivotStrength<1 || InpPivotStrength>5 || InpDisplacementAtr<=0.0 ||
      InpDisplacementBars<1 || InpDisplacementBars>12 || InpRetestBars<1 ||
      InpRetestBars>24 || InpStopAtrBuffer<0.0 || InpTargetRR<=0.0 ||
      InpMaxHoldBars<1 || InpMaxTradesPerDay!=1 || InpMaxSpreadPoints<=0)
      return false;
   if(InpLondonStartMinuteET<0 || InpLondonEndMinuteET<=InpLondonStartMinuteET ||
      InpNyStartMinuteET<0 || InpNyEndMinuteET<=InpNyStartMinuteET ||
      InpNyEndMinuteET>1440)
      return false;
   if(KLR_USD_OBSERVATION_COUNT!=ArraySize(KLR_USD_DATES) ||
      KLR_USD_OBSERVATION_COUNT!=ArraySize(KLR_USD_CHANGES))
      return false;
   return true;
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

datetime NthSunday(const int year,const int month,const int nth,const int hour)
  {
   datetime first=MakeDateTime(year,month,1,hour);
   MqlDateTime parts;
   TimeToStruct(first,parts);
   int first_sunday=1+((7-parts.day_of_week)%7);
   return MakeDateTime(year,month,first_sunday+(nth-1)*7,hour);
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

bool IsUsDstUtc(const datetime utc_time)
  {
   MqlDateTime parts;
   TimeToStruct(utc_time,parts);
   datetime start=NthSunday(parts.year,3,2,7);
   datetime finish=NthSunday(parts.year,11,1,6);
   return utc_time>=start && utc_time<finish;
  }

datetime ServerToEt(const datetime server_time)
  {
   datetime utc_time=ServerToUtc(server_time);
   return utc_time-(IsUsDstUtc(utc_time) ? 4 : 5)*3600;
  }

int EtDateKey(const datetime server_time)
  {
   MqlDateTime parts;
   TimeToStruct(ServerToEt(server_time),parts);
   return parts.year*10000+parts.mon*100+parts.day;
  }

int EtMinute(const datetime server_time)
  {
   MqlDateTime parts;
   TimeToStruct(ServerToEt(server_time),parts);
   return parts.hour*60+parts.min;
  }

datetime DateFromKey(const int key)
  {
   return MakeDateTime(key/10000,(key/100)%100,key%100,0);
  }

datetime SubtractBusinessDays(datetime value,int count)
  {
   while(count>0)
     {
      value-=86400;
      MqlDateTime parts;
      TimeToStruct(value,parts);
      if(parts.day_of_week!=0 && parts.day_of_week!=6)
         count--;
     }
   return value;
  }

bool UsdChangeForEtDate(const int et_date_key,double &change)
  {
   datetime cutoff=SubtractBusinessDays(DateFromKey(et_date_key),2);
   int left=0;
   int right=KLR_USD_OBSERVATION_COUNT-1;
   int found=-1;
   while(left<=right)
     {
      int middle=(left+right)/2;
      if(KLR_USD_DATES[middle]<=cutoff)
        {
         found=middle;
         left=middle+1;
        }
      else
         right=middle-1;
     }
   if(found<0)
      return false;
   change=KLR_USD_CHANGES[found];
   return MathIsValidNumber(change) && change!=0.0;
  }

int EligibleWindow(const int et_minute)
  {
   if(et_minute>=InpLondonStartMinuteET && et_minute<InpLondonEndMinuteET)
      return 1;
   if(et_minute>=InpNyStartMinuteET && et_minute<InpNyEndMinuteET)
      return 2;
   return 0;
  }

int WindowEndMinute(const int window_id)
  {
   return window_id==1 ? InpLondonEndMinuteET : InpNyEndMinuteET;
  }

bool CurrentClosedAtr(double &atr)
  {
   double values[];
   ArraySetAsSeries(values,true);
   if(CopyBuffer(g_atr_handle,0,1,1,values)!=1)
      return false;
   atr=values[0];
   return MathIsValidNumber(atr) && atr>0.0;
  }

bool IsPivotHigh(const MqlRates &bars[],const int index)
  {
   for(int offset=1;offset<=InpPivotStrength;offset++)
      if(bars[index].high<=bars[index-offset].high || bars[index].high<=bars[index+offset].high)
         return false;
   return true;
  }

bool IsPivotLow(const MqlRates &bars[],const int index)
  {
   for(int offset=1;offset<=InpPivotStrength;offset++)
      if(bars[index].low>=bars[index-offset].low || bars[index].low>=bars[index+offset].low)
         return false;
   return true;
  }

int ClosedM15Bias()
  {
   MqlRates bars[];
   ArraySetAsSeries(bars,true);
   int copied=CopyRates(_Symbol,PERIOD_M15,1,240,bars);
   if(copied<40)
      return 0;
   double newer_high=0.0,older_high=0.0,newer_low=0.0,older_low=0.0;
   int highs_found=0;
   int lows_found=0;
   for(int index=InpPivotStrength;index<copied-InpPivotStrength;index++)
     {
      if(highs_found<2 && IsPivotHigh(bars,index))
        {
         if(highs_found==0)
            newer_high=bars[index].high;
         else
            older_high=bars[index].high;
         highs_found++;
        }
      if(lows_found<2 && IsPivotLow(bars,index))
        {
         if(lows_found==0)
            newer_low=bars[index].low;
         else
            older_low=bars[index].low;
         lows_found++;
        }
      if(highs_found>=2 && lows_found>=2)
         break;
     }
   if(highs_found<2 || lows_found<2)
      return 0;
   if(newer_high>older_high && newer_low>older_low)
      return 1;
   if(newer_high<older_high && newer_low<older_low)
      return -1;
   return 0;
  }

bool PreviousEtDayLevels(const int current_key,double &previous_high,double &previous_low)
  {
   MqlRates history[];
   ArraySetAsSeries(history,true);
   int copied=CopyRates(_Symbol,PERIOD_M5,1,2200,history);
   if(copied<300)
      return false;
   int previous_key=0;
   previous_high=-DBL_MAX;
   previous_low=DBL_MAX;
   for(int index=0;index<copied;index++)
     {
      int key=EtDateKey(history[index].time);
      if(key==current_key)
         continue;
      if(previous_key==0)
         previous_key=key;
      if(key!=previous_key)
         break;
      previous_high=MathMax(previous_high,history[index].high);
      previous_low=MathMin(previous_low,history[index].low);
     }
   return previous_key>0 && previous_high>previous_low;
  }

void ResetDayStates(const int date_key)
  {
   static int last_date_key=0;
   if(date_key==last_date_key)
      return;
   last_date_key=date_key;
   g_days_seen++;
   for(int i=0;i<MAX_RAID_STATES;i++)
      g_raids[i].active=false;
   for(int i=0;i<MAX_FVG_STATES;i++)
      g_fvgs[i].active=false;
  }

void AddRaid(const int direction,const int date_key,const int window_id,
             const MqlRates &bar,const double atr)
  {
   for(int i=0;i<MAX_RAID_STATES;i++)
     {
      if(g_raids[i].active)
         continue;
      g_raids[i].active=true;
      g_raids[i].direction=direction;
      g_raids[i].et_date_key=date_key;
      g_raids[i].window_id=window_id;
      g_raids[i].bars_after=0;
      g_raids[i].sweep_time=bar.time;
      g_raids[i].sweep_high=bar.high;
      g_raids[i].sweep_low=bar.low;
      g_raids[i].stop=(direction>0 ? bar.low-InpStopAtrBuffer*atr : bar.high+InpStopAtrBuffer*atr);
      g_sweeps++;
      return;
     }
   Print("KLR raid state capacity exhausted.");
  }

void AddFvg(const RaidState &raid,const MqlRates &bar,const MqlRates &two_older)
  {
   double zone_low=0.0;
   double zone_high=0.0;
   if(raid.direction>0 && bar.low>two_older.high)
     {
      zone_low=two_older.high;
      zone_high=bar.low;
     }
   else if(raid.direction<0 && bar.high<two_older.low)
     {
      zone_low=bar.high;
      zone_high=two_older.low;
     }
   else
      return;
   g_strict_fvgs++;
   for(int i=0;i<MAX_FVG_STATES;i++)
     {
      if(g_fvgs[i].active)
         continue;
      g_fvgs[i].active=true;
      g_fvgs[i].direction=raid.direction;
      g_fvgs[i].et_date_key=raid.et_date_key;
      g_fvgs[i].window_id=raid.window_id;
      g_fvgs[i].bars_after=0;
      g_fvgs[i].displacement_time=bar.time;
      g_fvgs[i].zone_low=zone_low;
      g_fvgs[i].zone_high=zone_high;
      g_fvgs[i].stop=raid.stop;
      return;
     }
   Print("KLR FVG state capacity exhausted.");
  }

ulong OwnedPositionTicket()
  {
   for(int index=PositionsTotal()-1;index>=0;index--)
     {
      ulong ticket=PositionGetTicket(index);
      if(ticket==0 || !PositionSelectByTicket(ticket))
         continue;
      if(PositionGetString(POSITION_SYMBOL)==_Symbol && PositionGetInteger(POSITION_MAGIC)==InpMagic)
         return ticket;
     }
   return 0;
  }

double NormalizeVolume(const double raw)
  {
   double minimum=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN);
   double maximum=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX);
   double step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);
   if(step<=0.0)
      return 0.0;
   double volume=MathFloor(raw/step+1e-9)*step;
   volume=MathMax(minimum,MathMin(maximum,volume));
   return NormalizeDouble(volume,8);
  }

double RiskSizedVolume(const int direction,const double entry,const double stop,
                       double &risk_account)
  {
   risk_account=AccountInfoDouble(ACCOUNT_EQUITY)*InpRiskPercent/100.0;
   double one_lot_profit=0.0;
   ENUM_ORDER_TYPE order_type=(direction>0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL);
   if(!OrderCalcProfit(order_type,_Symbol,1.0,entry,stop,one_lot_profit))
      return 0.0;
   double one_lot_risk=MathAbs(one_lot_profit);
   if(one_lot_risk<=0.0)
      return 0.0;
   return NormalizeVolume(risk_account/one_lot_risk);
  }

bool TryOpenFromRetest(const FvgState &setup)
  {
   if(g_trade_day_key==setup.et_date_key || OwnedPositionTicket()!=0)
      return false;
   double usd_change=0.0;
   bool usd_available=UsdChangeForEtDate(setup.et_date_key,usd_change);
   bool usd_aligned=usd_available && ((setup.direction>0 && usd_change<0.0) ||
                                      (setup.direction<0 && usd_change>0.0));
   if(usd_aligned)
      g_usd_aligned_retests++;
   if(InpRequireUsdGate && !usd_aligned)
      return false;
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick))
      return false;
   double spread_points=(tick.ask-tick.bid)/_Point;
   if(spread_points>InpMaxSpreadPoints)
     {
      g_spread_rejections++;
      return false;
     }
   if(!InpResearchAutoMode)
      return false;
   double entry=(setup.direction>0 ? tick.ask : tick.bid);
   double stop=NormalizeDouble(setup.stop,_Digits);
   double risk=(setup.direction>0 ? entry-stop : stop-entry);
   long stops_level=SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL);
   if(risk<=MathMax(_Point,(double)stops_level*_Point))
     {
      g_geometry_rejections++;
      return false;
     }
   double target=NormalizeDouble(entry+(setup.direction>0 ? 1.0 : -1.0)*InpTargetRR*risk,_Digits);
   double risk_account=0.0;
   double volume=RiskSizedVolume(setup.direction,entry,stop,risk_account);
   if(volume<=0.0)
     {
      g_geometry_rejections++;
      return false;
     }
   g_entries_attempted++;
   g_planned_risk_points=risk/_Point;
   g_planned_risk_account=risk_account;
   g_entry_order_type=(setup.direction>0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL);
   bool sent=(setup.direction>0 ? trade.Buy(volume,_Symbol,0.0,stop,target,HYPOTHESIS_ID)
                                : trade.Sell(volume,_Symbol,0.0,stop,target,HYPOTHESIS_ID));
   if(!sent)
     {
      PrintFormat("KLR entry failed retcode=%u %s",trade.ResultRetcode(),trade.ResultRetcodeDescription());
      g_planned_risk_points=0.0;
      g_planned_risk_account=0.0;
      return false;
     }
   g_entries_opened++;
   g_trade_day_key=setup.et_date_key;
   g_position_day_key=setup.et_date_key;
   g_position_window_id=setup.window_id;
   g_position_entry_bar=TimeCurrent();
   return true;
  }

void UpdateFvgs(const MqlRates &closed_bar,const int date_key,const int window_id)
  {
   for(int i=0;i<MAX_FVG_STATES;i++)
     {
      if(!g_fvgs[i].active)
         continue;
      if(g_fvgs[i].et_date_key!=date_key || g_fvgs[i].window_id!=window_id ||
         closed_bar.time<=g_fvgs[i].displacement_time)
        {
         if(g_fvgs[i].et_date_key!=date_key || g_fvgs[i].window_id!=window_id)
            g_fvgs[i].active=false;
         continue;
        }
      g_fvgs[i].bars_after++;
      if(g_fvgs[i].bars_after>InpRetestBars)
        {
         g_fvgs[i].active=false;
         continue;
        }
      bool overlap=closed_bar.low<=g_fvgs[i].zone_high && closed_bar.high>=g_fvgs[i].zone_low;
      bool directional_close=(g_fvgs[i].direction>0 ? closed_bar.close>closed_bar.open
                                                    : closed_bar.close<closed_bar.open);
      if(overlap && directional_close)
        {
         g_retests++;
         TryOpenFromRetest(g_fvgs[i]);
         g_fvgs[i].active=false;
        }
      else if(g_fvgs[i].bars_after>=InpRetestBars)
         g_fvgs[i].active=false;
     }
  }

void UpdateRaids(const MqlRates &closed_bar,const MqlRates &two_older,
                 const double atr,const int date_key,const int window_id)
  {
   for(int i=0;i<MAX_RAID_STATES;i++)
     {
      if(!g_raids[i].active)
         continue;
      if(g_raids[i].et_date_key!=date_key || g_raids[i].window_id!=window_id ||
         closed_bar.time<=g_raids[i].sweep_time)
        {
         if(g_raids[i].et_date_key!=date_key || g_raids[i].window_id!=window_id)
            g_raids[i].active=false;
         continue;
        }
      g_raids[i].bars_after++;
      if(g_raids[i].bars_after>InpDisplacementBars)
        {
         g_raids[i].active=false;
         continue;
        }
      double body=MathAbs(closed_bar.close-closed_bar.open);
      bool mss=(g_raids[i].direction>0 ? closed_bar.close>g_raids[i].sweep_high
                                      : closed_bar.close<g_raids[i].sweep_low);
      if(body>=InpDisplacementAtr*atr && mss)
        {
         g_displacements++;
         AddFvg(g_raids[i],closed_bar,two_older);
        }
      if(g_raids[i].bars_after>=InpDisplacementBars)
         g_raids[i].active=false;
     }
  }

void DetectRaid(const MqlRates &closed_bar,const double atr,const int date_key,const int window_id)
  {
   if(window_id==0)
      return;
   double prior_high=0.0;
   double prior_low=0.0;
   if(!PreviousEtDayLevels(date_key,prior_high,prior_low))
      return;
   int bias=ClosedM15Bias();
   if(bias>0 && closed_bar.low<prior_low && closed_bar.close>prior_low)
      AddRaid(1,date_key,window_id,closed_bar,atr);
   else if(bias<0 && closed_bar.high>prior_high && closed_bar.close<prior_high)
      AddRaid(-1,date_key,window_id,closed_bar,atr);
  }

void ProcessClosedM5Bar()
  {
   MqlRates bars[];
   ArraySetAsSeries(bars,true);
   if(CopyRates(_Symbol,PERIOD_M5,1,3,bars)!=3)
      return;
   double atr=0.0;
   if(!CurrentClosedAtr(atr))
      return;
   int date_key=EtDateKey(bars[0].time);
   int window_id=EligibleWindow(EtMinute(bars[0].time));
   ResetDayStates(date_key);
   UpdateFvgs(bars[0],date_key,window_id);
   UpdateRaids(bars[0],bars[2],atr,date_key,window_id);
   DetectRaid(bars[0],atr,date_key,window_id);
  }

void ManageOwnedPosition()
  {
   ulong ticket=OwnedPositionTicket();
   if(ticket==0 || !PositionSelectByTicket(ticket))
      return;
   datetime now=TimeCurrent();
   int date_key=EtDateKey(now);
   int window_id=EligibleWindow(EtMinute(now));
   datetime entry_bar=g_position_entry_bar;
   if(entry_bar==0)
      entry_bar=(datetime)PositionGetInteger(POSITION_TIME);
   int held_bars=(int)MathMax(0,(now-entry_bar)/PeriodSeconds(PERIOD_M5));
   bool must_flat=(date_key!=g_position_day_key || window_id!=g_position_window_id ||
                   held_bars>=InpMaxHoldBars || EtMinute(now)>=WindowEndMinute(g_position_window_id));
   if(must_flat && !trade.PositionClose(ticket))
      PrintFormat("KLR position close failed retcode=%u %s",trade.ResultRetcode(),trade.ResultRetcodeDescription());
  }

ENUM_ORDER_TYPE EntryTypeForPosition(const ulong position_id)
  {
   if(position_id==g_position_identifier)
      return g_entry_order_type;
   if(HistorySelect(0,TimeCurrent()))
     {
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
     }
   return ORDER_TYPE_BUY;
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

void LogLifecycleDeal(const ulong deal)
  {
   if(!InpEnableTelemetry || g_telemetry_handle==INVALID_HANDLE || !HistoryDealSelect(deal))
      return;
   if(HistoryDealGetString(deal,DEAL_SYMBOL)!=_Symbol || HistoryDealGetInteger(deal,DEAL_MAGIC)!=InpMagic)
      return;
   ENUM_DEAL_ENTRY entry=(ENUM_DEAL_ENTRY)HistoryDealGetInteger(deal,DEAL_ENTRY);
   if(entry!=DEAL_ENTRY_IN && entry!=DEAL_ENTRY_INOUT && entry!=DEAL_ENTRY_OUT && entry!=DEAL_ENTRY_OUT_BY)
      return;
   ulong position_id=(ulong)HistoryDealGetInteger(deal,DEAL_POSITION_ID);
   ENUM_DEAL_TYPE deal_type=(ENUM_DEAL_TYPE)HistoryDealGetInteger(deal,DEAL_TYPE);
   ENUM_ORDER_TYPE entry_type=EntryTypeForPosition(position_id);
   bool is_open=(entry==DEAL_ENTRY_IN || entry==DEAL_ENTRY_INOUT);
   if(is_open)
     {
      entry_type=(deal_type==DEAL_TYPE_SELL ? ORDER_TYPE_SELL : ORDER_TYPE_BUY);
      g_position_identifier=position_id;
      g_entry_order_type=entry_type;
     }
   bool final_close=(!is_open && !PositionIdentifierExists(position_id));
   string action=(is_open ? "OPEN" : (final_close ? "CLOSE" : "CLOSE_PARTIAL"));
   string order_type=(entry_type==ORDER_TYPE_SELL ? "SELL" : "BUY");
   double profit=HistoryDealGetDouble(deal,DEAL_PROFIT);
   double commission=HistoryDealGetDouble(deal,DEAL_COMMISSION);
   double swap=HistoryDealGetDouble(deal,DEAL_SWAP);
   double fee=HistoryDealGetDouble(deal,DEAL_FEE);
   double net=profit+commission+swap+fee;
   datetime event_time=(datetime)HistoryDealGetInteger(deal,DEAL_TIME);
   FileWrite(g_telemetry_handle,
             TimeToString(event_time,TIME_DATE|TIME_SECONDS),action,order_type,
             DoubleToString(HistoryDealGetDouble(deal,DEAL_VOLUME),8),
             DoubleToString(HistoryDealGetDouble(deal,DEAL_PRICE),_Digits),_Symbol,
             StringFormat("%I64u",position_id),DoubleToString(g_planned_risk_points,8),
             DoubleToString(g_planned_risk_account,8),StringFormat("%I64u",deal),
             DoubleToString(profit,8),DoubleToString(commission,8),
             DoubleToString(swap,8),DoubleToString(fee,8),DoubleToString(net,8),
             final_close ? "1" : "0");
   FileFlush(g_telemetry_handle);
   if(final_close)
     {
      g_position_identifier=0;
      g_planned_risk_points=0.0;
      g_planned_risk_account=0.0;
      g_position_day_key=0;
      g_position_window_id=0;
      g_position_entry_bar=0;
     }
  }

int OnInit()
  {
   if(!ValidateInputs())
      return INIT_PARAMETERS_INCORRECT;
   g_atr_handle=iATR(_Symbol,PERIOD_M5,InpAtrPeriod);
   if(g_atr_handle==INVALID_HANDLE)
      return INIT_FAILED;
   trade.SetExpertMagicNumber((ulong)InpMagic);
   trade.SetDeviationInPoints((ulong)MathMax(1,InpMaxSpreadPoints));
   trade.SetTypeFillingBySymbol(_Symbol);
   trade.SetAsyncMode(false);
   g_peak_equity=AccountInfoDouble(ACCOUNT_EQUITY);
   if(!OpenLifecycleTelemetry())
      return INIT_FAILED;
   PrintFormat("KLR init hypothesis=%s role=%s mode=%s telemetry=%s",
               HYPOTHESIS_ID,InpRequireUsdGate ? "CHALLENGER_USD" : "CONTROL_CORE",
               InpResearchAutoMode ? "RESEARCH_AUTO" : "ALERT_ONLY",
               InpEnableTelemetry ? "ON" : "OFF");
   return INIT_SUCCEEDED;
  }

void OnDeinit(const int reason)
  {
   WriteRunMeta();
   if(g_telemetry_handle!=INVALID_HANDLE)
     {
      FileFlush(g_telemetry_handle);
      FileClose(g_telemetry_handle);
      g_telemetry_handle=INVALID_HANDLE;
     }
   if(g_atr_handle!=INVALID_HANDLE)
     {
      IndicatorRelease(g_atr_handle);
      g_atr_handle=INVALID_HANDLE;
     }
   PrintFormat("KLR diagnostic days=%I64d sweeps=%I64d displacement=%I64d fvg=%I64d retest=%I64d usd=%I64d entries=%I64d",
               g_days_seen,g_sweeps,g_displacements,g_strict_fvgs,g_retests,
               g_usd_aligned_retests,g_entries_opened);
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
   g_peak_equity=MathMax(g_peak_equity,AccountInfoDouble(ACCOUNT_EQUITY));
   ManageOwnedPosition();
   datetime current_bar=iTime(_Symbol,PERIOD_M5,0);
   if(current_bar<=0)
      return;
   if(current_bar==g_last_m5_bar)
      return;
   g_last_m5_bar=current_bar;
   ProcessClosedM5Bar();
  }
