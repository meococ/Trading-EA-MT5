#property copyright "AlphaFactory research"
#property version   "1.00"
#property strict

#include <Trade/Trade.mqh>

input bool   InpResearchAutoMode=false;
input bool   InpEnableTelemetry=true;
input double InpRiskPercent=0.30;
input long   InpMagic=5600716;
input int    InpAtrPeriod=14;
input int    InpSweepLookback=12;
input int    InpSweepStateBars=4;
input int    InpBreakerLookback=6;
input double InpMinDisplacementAtr=1.20;
input double InpStrongDisplacementAtr=1.80;
input double InpMinFvgAtr=0.05;
input double InpMinOverlapRatio=0.10;
input double InpStrongOverlapRatio=0.25;
input int    InpMinAutoScore=75;
input double InpTargetRR=2.50;
input double InpBreakEvenR=1.00;
input int    InpStopBufferPoints=40;
input int    InpMaxSpreadPoints=35;
input int    InpSessionStartUtcHour=7;
input int    InpSessionEndUtcHour=16;
input int    InpServerUtcOffsetHours=2;
input int    InpMaxHoldMinutes=90;
input int    InpMaxTradesPerDay=2;
input int    InpMaxConsecutiveLosses=2;
input double InpMaxDailyLossPct=1.00;
input double InpMaxWeeklyLossPct=2.00;
input double InpMaxAccountDrawdownPct=5.50;
input bool   InpRequireNewsGuard=false;

const string EA_NAME="EA_UnicornPrecisionScalper";
const string HYPOTHESIS_ID="HYP-UPS-XAU-M5-004";
const string TELEMETRY_PROFILE="lifecycle-v3";

struct SignalPlan
  {
   bool valid;
   int direction;
   int score;
   double sweep_extreme;
   double atr;
   double body_atr;
   double overlap_ratio;
  };

CTrade trade;
datetime g_last_bar=0;
bool g_new_bar_ready=false;
double g_peak_equity=0.0;
double g_planned_risk_points=0.0;
double g_planned_risk_account=0.0;
ulong g_position_identifier=0;
ENUM_ORDER_TYPE g_entry_order_type=ORDER_TYPE_BUY;
int g_telemetry_handle=INVALID_HANDLE;
string g_run_id="";
string g_lifecycle_name="";
string g_run_meta_name="";

string SafeRunToken()
  {
   return StringFormat("%s_%I64u",HYPOTHESIS_ID,GetTickCount64());
  }

bool WriteRunMeta()
  {
   g_run_meta_name=StringFormat("%s_RunMeta_%s.json",_Symbol,g_run_id);
   int handle=FileOpen(g_run_meta_name,FILE_WRITE|FILE_TXT|FILE_ANSI);
   if(handle==INVALID_HANDLE)
     {
      Print("UPS telemetry RunMeta open failed: ",GetLastError());
      return false;
     }
   string payload=StringFormat(
      "{\"schema_version\":\"alphafactory_run_meta.v1\",\"run_id\":\"%s\",\"ea_name\":\"%s\",\"symbol\":\"%s\",\"telemetry_profile\":\"%s\",\"hypothesis_id\":\"%s\"}",
      g_run_id,EA_NAME,_Symbol,TELEMETRY_PROFILE,HYPOTHESIS_ID);
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
   g_telemetry_handle=FileOpen(g_lifecycle_name,FILE_WRITE|FILE_CSV|FILE_ANSI,',');
   if(g_telemetry_handle==INVALID_HANDLE)
     {
      Print("UPS lifecycle telemetry open failed: ",GetLastError());
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
      Print("UPS requires M5 chart/test period.");
      return false;
     }
   if(InpRiskPercent<=0.0 || InpRiskPercent>1.0 || InpTargetRR<2.0 || InpBreakEvenR<=0.0)
      return false;
   if(InpAtrPeriod<5 || InpSweepLookback<3 || InpSweepStateBars<1 || InpSweepStateBars>12)
      return false;
   if(InpBreakerLookback<1 || InpMinDisplacementAtr<=0.0 || InpStrongDisplacementAtr<InpMinDisplacementAtr)
      return false;
   if(InpMinOverlapRatio<0.0 || InpStrongOverlapRatio<InpMinOverlapRatio || InpStrongOverlapRatio>1.0)
      return false;
   if(InpSessionStartUtcHour<0 || InpSessionStartUtcHour>23 || InpSessionEndUtcHour<1 || InpSessionEndUtcHour>24)
      return false;
   if(InpMaxSpreadPoints<=0 || InpStopBufferPoints<0 || InpMaxHoldMinutes<=0)
      return false;
   return true;
  }

int OnInit()
  {
   if(!ValidateInputs())
      return INIT_PARAMETERS_INCORRECT;
   trade.SetExpertMagicNumber((ulong)InpMagic);
   trade.SetDeviationInPoints((ulong)MathMax(1,InpMaxSpreadPoints));
   trade.SetTypeFillingBySymbol(_Symbol);
   trade.SetAsyncMode(false);
   g_peak_equity=AccountInfoDouble(ACCOUNT_EQUITY);
   if(!OpenLifecycleTelemetry())
      return INIT_FAILED;
   PrintFormat("UPS init mode=%s hypothesis=%s telemetry=%s",
               InpResearchAutoMode ? "RESEARCH_AUTO" : "ALERT_ONLY",
               HYPOTHESIS_ID,InpEnableTelemetry ? "ON" : "OFF");
   return INIT_SUCCEEDED;
  }

void OnDeinit(const int reason)
  {
   if(g_telemetry_handle!=INVALID_HANDLE)
     {
      FileFlush(g_telemetry_handle);
      FileClose(g_telemetry_handle);
      g_telemetry_handle=INVALID_HANDLE;
     }
  }

void RefreshNewM5BarGate()
  {
   datetime current=iTime(_Symbol,PERIOD_M5,0);
   if(current==g_last_bar)
     {
      return;
     }
   g_last_bar=current;
   g_new_bar_ready=(current>0);
  }

double TrueRange(const MqlRates &bar,const MqlRates &older)
  {
   return MathMax(bar.high-bar.low,MathMax(MathAbs(bar.high-older.close),MathAbs(bar.low-older.close)));
  }

double ClosedAtr(const MqlRates &rates[],const int start_shift)
  {
   double total=0.0;
   for(int i=start_shift;i<start_shift+InpAtrPeriod;i++)
      total+=TrueRange(rates[i],rates[i+1]);
   return total/(double)InpAtrPeriod;
  }

int ClosedTrendState(const ENUM_TIMEFRAMES timeframe)
  {
   MqlRates bars[];
   ArraySetAsSeries(bars,true);
   int copied=CopyRates(_Symbol,timeframe,1,80,bars);
   if(copied<60)
      return 0;
   double fast=bars[copied-1].close;
   double slow=bars[copied-1].close;
   const double fast_alpha=2.0/21.0;
   const double slow_alpha=2.0/51.0;
   for(int i=copied-2;i>=0;i--)
     {
      fast=fast_alpha*bars[i].close+(1.0-fast_alpha)*fast;
      slow=slow_alpha*bars[i].close+(1.0-slow_alpha)*slow;
     }
   if(bars[0].close>fast && fast>slow)
      return 1;
   if(bars[0].close<fast && fast<slow)
      return -1;
   return 0;
  }

bool SessionOpen(const datetime server_time)
  {
   datetime utc_time=server_time-(InpServerUtcOffsetHours*3600);
   MqlDateTime parts;
   TimeToStruct(utc_time,parts);
   return parts.hour>=InpSessionStartUtcHour && parts.hour<InpSessionEndUtcHour;
  }

bool NewsGuardAllows()
  {
   if(!InpRequireNewsGuard)
      return true;
   // Historical calendar identity is not yet hash-bound. Required mode must
   // fail closed rather than silently pretending that no news exists.
   return false;
  }

double CandleOverlapRatio(const MqlRates &bar,const int direction,const double zone_low,const double zone_high)
  {
   bool opposite=(direction>0 ? bar.close<bar.open : bar.close>bar.open);
   if(!opposite)
      return 0.0;
   double width=zone_high-zone_low;
   if(width<=0.0)
      return 0.0;
   double candle_low=MathMin(bar.open,bar.close);
   double candle_high=MathMax(bar.open,bar.close);
   double overlap=MathMax(0.0,MathMin(zone_high,candle_high)-MathMax(zone_low,candle_low));
   return overlap/width;
  }

bool FindRecentSweep(const MqlRates &rates[],const int left,const int direction,double &extreme)
  {
   for(int j=left;j<left+InpSweepStateBars;j++)
     {
      double prior_low=DBL_MAX;
      double prior_high=-DBL_MAX;
      for(int k=j+1;k<=j+InpSweepLookback;k++)
        {
         prior_low=MathMin(prior_low,rates[k].low);
         prior_high=MathMax(prior_high,rates[k].high);
        }
      if(direction>0 && rates[j].low<prior_low && rates[j].close>prior_low)
        {
         extreme=rates[j].low;
         return true;
        }
      if(direction<0 && rates[j].high>prior_high && rates[j].close<prior_high)
        {
         extreme=rates[j].high;
         return true;
        }
     }
   return false;
  }

SignalPlan EvaluateClosedSignal()
  {
   SignalPlan result;
   result.valid=false;
   result.direction=0;
   result.score=0;
   result.sweep_extreme=0.0;
   result.atr=0.0;
   result.body_atr=0.0;
   result.overlap_ratio=0.0;

   int required=MathMax(80,InpSweepLookback+InpSweepStateBars+InpBreakerLookback+20);
   MqlRates rates[];
   ArraySetAsSeries(rates,true);
   int copied=CopyRates(_Symbol,PERIOD_M5,1,required,rates);
   if(copied<required)
      return result;

   int h4_bias=ClosedTrendState(PERIOD_H4);
   int d1_bias=ClosedTrendState(PERIOD_D1);
   if(h4_bias==0 || d1_bias==-h4_bias)
      return result;

   const int right=0;
   const int middle=1;
   const int left=2;
   double current_atr=ClosedAtr(rates,middle);
   if(current_atr<=0.0)
      return result;
   double body=MathAbs(rates[middle].close-rates[middle].open);
   double body_atr=body/current_atr;
   if(body_atr<InpMinDisplacementAtr)
      return result;

   int direction=0;
   double fvg_low=0.0;
   double fvg_high=0.0;
   if(h4_bias>0 && rates[middle].close>rates[middle].open && rates[right].low>rates[left].high)
     {
      direction=1;
      fvg_low=rates[left].high;
      fvg_high=rates[right].low;
     }
   else if(h4_bias<0 && rates[middle].close<rates[middle].open && rates[right].high<rates[left].low)
     {
      direction=-1;
      fvg_low=rates[right].high;
      fvg_high=rates[left].low;
     }
   if(direction==0 || (fvg_high-fvg_low)/current_atr<InpMinFvgAtr)
      return result;

   double sweep_extreme=0.0;
   if(!FindRecentSweep(rates,left,direction,sweep_extreme))
      return result;
   double best_overlap=0.0;
   for(int i=left;i<=left+InpBreakerLookback;i++)
      best_overlap=MathMax(best_overlap,CandleOverlapRatio(rates[i],direction,fvg_low,fvg_high));
   if(best_overlap<InpMinOverlapRatio)
      return result;

   double range_low=DBL_MAX;
   double range_high=-DBL_MAX;
   for(int i=0;i<25;i++)
     {
      range_low=MathMin(range_low,rates[i].low);
      range_high=MathMax(range_high,rates[i].high);
     }
   double midpoint=(range_low+range_high)/2.0;
   bool pd_ok=(direction>0 ? rates[right].close<=midpoint : rates[right].close>=midpoint);
   int score=15+(d1_bias==h4_bias ? 10 : 0)+15;
   score+=(body_atr>=InpStrongDisplacementAtr ? 20 : 15);
   score+=10;
   score+=(best_overlap>=InpStrongOverlapRatio ? 20 : 15);
   score+=(pd_ok ? 10 : 0);
   if(score<InpMinAutoScore)
      return result;

   result.valid=true;
   result.direction=direction;
   result.score=score;
   result.sweep_extreme=sweep_extreme;
   result.atr=current_atr;
   result.body_atr=body_atr;
   result.overlap_ratio=best_overlap;
   return result;
  }

bool IsOwnedPosition(const ulong ticket)
  {
   if(ticket==0 || !PositionSelectByTicket(ticket))
      return false;
   return PositionGetString(POSITION_SYMBOL)==_Symbol && PositionGetInteger(POSITION_MAGIC)==InpMagic;
  }

ulong OwnedPositionTicket()
  {
   for(int i=PositionsTotal()-1;i>=0;i--)
     {
      ulong ticket=PositionGetTicket(i);
      if(IsOwnedPosition(ticket))
         return ticket;
     }
   return 0;
  }

datetime StartOfDay(const datetime now)
  {
   MqlDateTime p;
   TimeToStruct(now,p);
   p.hour=0; p.min=0; p.sec=0;
   return StructToTime(p);
  }

datetime StartOfWeek(const datetime now)
  {
   MqlDateTime p;
   TimeToStruct(now,p);
   int days_from_monday=(p.day_of_week+6)%7;
   return StartOfDay(now)-days_from_monday*86400;
  }

double RealizedNetSince(const datetime from_time,int &closing_trades,int &consecutive_losses)
  {
   closing_trades=0;
   consecutive_losses=0;
   double net=0.0;
   if(!HistorySelect(from_time,TimeCurrent()))
      return 0.0;
   int total=HistoryDealsTotal();
   bool counting_streak=true;
   for(int i=0;i<total;i++)
     {
      ulong deal=HistoryDealGetTicket(i);
      if(deal==0 || HistoryDealGetString(deal,DEAL_SYMBOL)!=_Symbol || HistoryDealGetInteger(deal,DEAL_MAGIC)!=InpMagic)
         continue;
      ENUM_DEAL_ENTRY entry=(ENUM_DEAL_ENTRY)HistoryDealGetInteger(deal,DEAL_ENTRY);
      if(entry!=DEAL_ENTRY_OUT && entry!=DEAL_ENTRY_OUT_BY)
         continue;
      double row=HistoryDealGetDouble(deal,DEAL_PROFIT)+HistoryDealGetDouble(deal,DEAL_COMMISSION)+
                 HistoryDealGetDouble(deal,DEAL_SWAP)+HistoryDealGetDouble(deal,DEAL_FEE);
      net+=row;
      closing_trades++;
     }
   for(int i=total-1;i>=0 && counting_streak;i--)
     {
      ulong deal=HistoryDealGetTicket(i);
      if(deal==0 || HistoryDealGetString(deal,DEAL_SYMBOL)!=_Symbol || HistoryDealGetInteger(deal,DEAL_MAGIC)!=InpMagic)
         continue;
      ENUM_DEAL_ENTRY entry=(ENUM_DEAL_ENTRY)HistoryDealGetInteger(deal,DEAL_ENTRY);
      if(entry!=DEAL_ENTRY_OUT && entry!=DEAL_ENTRY_OUT_BY)
         continue;
      double row=HistoryDealGetDouble(deal,DEAL_PROFIT)+HistoryDealGetDouble(deal,DEAL_COMMISSION)+
                 HistoryDealGetDouble(deal,DEAL_SWAP)+HistoryDealGetDouble(deal,DEAL_FEE);
      if(row<0.0)
         consecutive_losses++;
      else
         counting_streak=false;
     }
   return net;
  }

bool RiskGuardsAllow()
  {
   double equity=AccountInfoDouble(ACCOUNT_EQUITY);
   if(equity<=0.0)
      return false;
   g_peak_equity=MathMax(g_peak_equity,equity);
   double account_dd=(g_peak_equity-equity)/g_peak_equity*100.0;
   if(account_dd>=InpMaxAccountDrawdownPct)
      return false;
   int day_trades=0,streak=0;
   double day_net=RealizedNetSince(StartOfDay(TimeCurrent()),day_trades,streak);
   double day_start=MathMax(1.0,AccountInfoDouble(ACCOUNT_BALANCE)-day_net);
   if(day_trades>=InpMaxTradesPerDay || streak>=InpMaxConsecutiveLosses || (-day_net/day_start*100.0)>=InpMaxDailyLossPct)
      return false;
   int week_trades=0,week_streak=0;
   double week_net=RealizedNetSince(StartOfWeek(TimeCurrent()),week_trades,week_streak);
   double week_start=MathMax(1.0,AccountInfoDouble(ACCOUNT_BALANCE)-week_net);
   if((-week_net/week_start*100.0)>=InpMaxWeeklyLossPct)
      return false;
   return true;
  }

double NormalizeVolume(const double raw)
  {
   double minimum=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN);
   double maximum=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX);
   double step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);
   if(minimum<=0.0 || maximum<minimum || step<=0.0 || raw<minimum)
      return 0.0;
   double volume=MathFloor((MathMin(raw,maximum)-minimum)/step+1e-9)*step+minimum;
   int digits=0;
   double probe=step;
   while(digits<8 && MathAbs(probe-MathRound(probe))>1e-9)
     {
      probe*=10.0;
      digits++;
     }
   return NormalizeDouble(volume,digits);
  }

double RiskSizedVolume(const int direction,const double entry,const double stop,double &risk_account)
  {
   double loss_one_lot=0.0;
   ENUM_ORDER_TYPE type=(direction>0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL);
   if(!OrderCalcProfit(type,_Symbol,1.0,entry,stop,loss_one_lot) || loss_one_lot>=0.0)
      return 0.0;
   risk_account=AccountInfoDouble(ACCOUNT_EQUITY)*InpRiskPercent/100.0;
   double volume=NormalizeVolume(risk_account/MathAbs(loss_one_lot));
   if(volume<=0.0)
      return 0.0;
   double normalized_loss=0.0;
   if(!OrderCalcProfit(type,_Symbol,volume,entry,stop,normalized_loss))
      return 0.0;
   if(MathAbs(normalized_loss)>risk_account*1.05)
      return 0.0;
   risk_account=MathAbs(normalized_loss);
   return volume;
  }

bool StopGeometryValid(const int direction,const double entry,const double stop,const double target)
  {
   long stops_level=SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL);
   double minimum=(double)stops_level*_Point;
   if(direction>0)
      return stop<entry && target>entry && entry-stop>=minimum && target-entry>=minimum;
   return stop>entry && target<entry && stop-entry>=minimum && entry-target>=minimum;
  }

bool OpenFromSignal(const SignalPlan &signal)
  {
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick) || tick.ask<=0.0 || tick.bid<=0.0)
      return false;
   double entry=(signal.direction>0 ? tick.ask : tick.bid);
   double buffer=(double)InpStopBufferPoints*_Point;
   double stop=(signal.direction>0 ? signal.sweep_extreme-buffer : signal.sweep_extreme+buffer);
   double risk_distance=MathAbs(entry-stop);
   double target=(signal.direction>0 ? entry+InpTargetRR*risk_distance : entry-InpTargetRR*risk_distance);
   stop=NormalizeDouble(stop,_Digits);
   target=NormalizeDouble(target,_Digits);
   if(!StopGeometryValid(signal.direction,entry,stop,target))
      return false;
   double risk_account=0.0;
   double volume=RiskSizedVolume(signal.direction,entry,stop,risk_account);
   if(volume<=0.0)
      return false;
   g_planned_risk_points=risk_distance/_Point;
   g_planned_risk_account=risk_account;
   g_entry_order_type=(signal.direction>0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL);
   bool sent=(signal.direction>0 ? trade.Buy(volume,_Symbol,0.0,stop,target,HYPOTHESIS_ID)
                                 : trade.Sell(volume,_Symbol,0.0,stop,target,HYPOTHESIS_ID));
   if(!sent || (trade.ResultRetcode()!=TRADE_RETCODE_DONE && trade.ResultRetcode()!=TRADE_RETCODE_DONE_PARTIAL))
     {
      PrintFormat("UPS order rejected sent=%s retcode=%u %s",sent ? "true" : "false",trade.ResultRetcode(),trade.ResultRetcodeDescription());
      g_planned_risk_points=0.0;
      g_planned_risk_account=0.0;
      return false;
     }
   return true;
  }

double InitialRiskDistance(const ulong ticket)
  {
   if(!PositionSelectByTicket(ticket))
      return 0.0;
   double entry=PositionGetDouble(POSITION_PRICE_OPEN);
   double target=PositionGetDouble(POSITION_TP);
   if(InpTargetRR>0.0 && target>0.0)
      return MathAbs(target-entry)/InpTargetRR;
   double stop=PositionGetDouble(POSITION_SL);
   return MathAbs(entry-stop);
  }

void ManageOwnedPosition()
  {
   ulong ticket=OwnedPositionTicket();
   if(ticket==0 || !PositionSelectByTicket(ticket))
      return;
   double entry=PositionGetDouble(POSITION_PRICE_OPEN);
   double stop=PositionGetDouble(POSITION_SL);
   double target=PositionGetDouble(POSITION_TP);
   ENUM_POSITION_TYPE type=(ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE);
   datetime opened=(datetime)PositionGetInteger(POSITION_TIME);
   if(TimeCurrent()-opened>=InpMaxHoldMinutes*60)
     {
      if(!trade.PositionClose(ticket))
         Print("UPS max-hold close failed: ",trade.ResultRetcodeDescription());
      return;
     }
   double risk_distance=InitialRiskDistance(ticket);
   if(risk_distance<=0.0)
      return;
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick))
      return;
   double current=(type==POSITION_TYPE_BUY ? tick.bid : tick.ask);
   double favorable=(type==POSITION_TYPE_BUY ? current-entry : entry-current);
   if(favorable<InpBreakEvenR*risk_distance)
      return;
   double break_even=NormalizeDouble(entry,_Digits);
   bool needs_move=(type==POSITION_TYPE_BUY ? stop<break_even : stop>break_even || stop==0.0);
   if(needs_move && !trade.PositionModify(ticket,break_even,target))
      Print("UPS break-even modify failed: ",trade.ResultRetcodeDescription());
  }

ENUM_ORDER_TYPE EntryTypeForPosition(const ulong position_id)
  {
   if(position_id==g_position_identifier)
      return g_entry_order_type;
   if(HistorySelect(0,TimeCurrent()))
     {
      int total=HistoryDealsTotal();
      for(int i=0;i<total;i++)
        {
         ulong deal=HistoryDealGetTicket(i);
         if(deal==0 || (ulong)HistoryDealGetInteger(deal,DEAL_POSITION_ID)!=position_id)
            continue;
         ENUM_DEAL_ENTRY entry=(ENUM_DEAL_ENTRY)HistoryDealGetInteger(deal,DEAL_ENTRY);
         if(entry!=DEAL_ENTRY_IN && entry!=DEAL_ENTRY_INOUT)
            continue;
         ENUM_DEAL_TYPE type=(ENUM_DEAL_TYPE)HistoryDealGetInteger(deal,DEAL_TYPE);
         return type==DEAL_TYPE_SELL ? ORDER_TYPE_SELL : ORDER_TYPE_BUY;
        }
     }
   return ORDER_TYPE_BUY;
  }

bool PositionIdentifierExists(const ulong position_id)
  {
   for(int i=PositionsTotal()-1;i>=0;i--)
     {
      ulong ticket=PositionGetTicket(i);
      if(ticket>0 && PositionSelectByTicket(ticket) && (ulong)PositionGetInteger(POSITION_IDENTIFIER)==position_id)
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
     }
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
   g_new_bar_ready=false;
   RefreshNewM5BarGate();
   if(!g_new_bar_ready)
      return;
   if(OwnedPositionTicket()!=0 || !SessionOpen(g_last_bar) || !NewsGuardAllows())
      return;
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick) || (tick.ask-tick.bid)/_Point>InpMaxSpreadPoints)
      return;
   SignalPlan signal=EvaluateClosedSignal();
   if(!signal.valid)
      return;
   PrintFormat("UPS signal dir=%d score=%d bodyATR=%.3f overlap=%.3f mode=%s",
               signal.direction,signal.score,signal.body_atr,signal.overlap_ratio,
               InpResearchAutoMode ? "RESEARCH_AUTO" : "ALERT_ONLY");
   if(!InpResearchAutoMode || !RiskGuardsAllow())
      return;
   OpenFromSignal(signal);
  }
