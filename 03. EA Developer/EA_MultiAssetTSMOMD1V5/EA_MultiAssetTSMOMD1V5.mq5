//+------------------------------------------------------------------+
//| EA_MultiAssetTSMOMD1V5.mq5                                      |
//| HYP-MULTI-TSMOM-D1-005 - calendar-365 multi-asset TSMOM         |
//+------------------------------------------------------------------+
#property copyright "AlphaFactory research"
#property version   "1.00"
#property strict
#property description "Eight-to-nine asset calendar-365 time-series momentum"

input bool   InpResearchAutoMode=true;
input bool   InpLongOnlyComparator=false;
input ulong  InpMagic=260812007;
input int    InpDeviationPoints=20;

const string HYPOTHESIS_ID="HYP-MULTI-TSMOM-D1-005";
const string EXPECTED_SYMBOL="AFD_EURUSD_DUKA_TSMOM_V5";
#define ASSET_COUNT 9
#define VOL_RETURN_COUNT 60
#define HISTORY_BUFFER 460
const double SINGLE_WEIGHT_CAP=0.18;
const double FX_GROSS_CAP=0.70;
const double XAU_WEIGHT_CAP=0.25;
const double BTC_WEIGHT_CAP=0.20;
const double TOTAL_GROSS_CAP=1.00;
const double USD_FACTOR_CAP=0.25;
const double MAX_MARGIN_EQUITY_PCT=35.0;
const double MAX_FREE_MARGIN_USAGE_PCT=80.0;
const int    MAX_QUOTE_AGE_SECONDS=300;
const long   CALENDAR_LOOKBACK_SECONDS=365L*86400L;
const datetime BTC_ACTIVE_FROM=D'2018.05.14 00:00:00';

string g_symbols[ASSET_COUNT]={"AFD_EURUSD_DUKA_TSMOM_V5",
                               "AFD_GBPUSD_DUKA_TSMOM_V5",
                               "AFD_AUDUSD_DUKA_TSMOM_V5",
                               "AFD_NZDUSD_DUKA_TSMOM_V5",
                               "AFD_USDJPY_DUKA_TSMOM_V5",
                               "AFD_USDCAD_DUKA_TSMOM_V5",
                               "AFD_USDCHF_DUKA_TSMOM_V5",
                               "AFD_XAUUSD_DUKA_TSMOM_V5",
                               "AFD_BTCUSD_DUKA_TSMOM_V5"};
double g_signal[ASSET_COUNT];
double g_annual_vol[ASSET_COUNT];
double g_weight[ASSET_COUNT];
double g_target_signed_volume[ASSET_COUNT];
long   g_missing_weeks[ASSET_COUNT];
long   g_long_signals[ASSET_COUNT];
long   g_short_signals[ASSET_COUNT];

int      g_last_monday_key=0;
int      g_pending_monday_key=0;
datetime g_pending_decision_time=0;
datetime g_next_retry=0;
bool     g_snapshot_ready=false;
bool     g_volume_plan_ready=false;
int      g_last_finance_day=0;

long g_ticks_seen=0;
long g_monday_attempts=0;
long g_source_valid_mondays=0;
long g_weight_valid_mondays=0;
long g_completed_rebalances=0;
long g_failed_rebalances=0;
long g_rebalance_retries=0;
long g_stale_quote_waits=0;
long g_closed_session_waits=0;
long g_order_check_rejects=0;
long g_order_send_rejects=0;
long g_partial_retcode_events=0;
long g_below_min_volume=0;
long g_margin_scaled=0;
long g_source_years[4];
long g_execution_years[4];
long g_max_rebalance_latency_seconds=0;
double g_deal_profit=0.0;
double g_deal_swap=0.0;
double g_deal_commission=0.0;

bool IsFinitePositive(const double value)
  {
   return MathIsValidNumber(value) && value>0.0;
  }

bool IsFx(const int index)
  {
   return index>=0 && index<=6;
  }

bool IsDirectQuoteUsd(const int index)
  {
   return index<=3 || index==7 || index==8;
  }

bool IsActive(const int index,const datetime decision_time)
  {
   return index!=8 || decision_time>=BTC_ACTIVE_FROM;
  }

int SymbolIndex(const string symbol)
  {
   for(int i=0;i<ASSET_COUNT;i++)
      if(g_symbols[i]==symbol)
         return i;
   return -1;
  }

string AssetClass(const int index)
  {
   if(IsFx(index))
      return "FX";
   if(index==7)
      return "XAU";
   if(index==8)
      return "BTC";
   return "UNKNOWN";
  }

double OneSpreadCostUsd(const int index,const string symbol,
                        const ENUM_DEAL_TYPE deal_type,const double volume,
                        const double deal_price,long &spread_points)
  {
   spread_points=SymbolInfoInteger(symbol,SYMBOL_SPREAD);
   const double point=SymbolInfoDouble(symbol,SYMBOL_POINT);
   if(index<0 || spread_points<1 || !IsFinitePositive(point) ||
      !IsFinitePositive(volume) || !IsFinitePositive(deal_price))
      return -1.0;
   ENUM_ORDER_TYPE order_type;
   double exit_price=deal_price;
   if(deal_type==DEAL_TYPE_BUY)
     {
      order_type=ORDER_TYPE_BUY;
      exit_price-=spread_points*point;
     }
   else if(deal_type==DEAL_TYPE_SELL)
     {
      order_type=ORDER_TYPE_SELL;
      exit_price+=spread_points*point;
     }
   else
      return -1.0;
   double profit=0.0;
   ResetLastError();
   if(!OrderCalcProfit(order_type,symbol,volume,deal_price,exit_price,profit) ||
      !MathIsValidNumber(profit))
      return -1.0;
   return MathAbs(profit);
  }

int DateKey(const datetime value)
  {
   MqlDateTime stamp;
   if(!TimeToStruct(value,stamp))
      return 0;
   return stamp.year*10000+stamp.mon*100+stamp.day;
  }

int DesignYearIndex(const datetime value)
  {
   MqlDateTime stamp;
   if(!TimeToStruct(value,stamp) || stamp.year<2018 || stamp.year>2021)
      return -1;
   return stamp.year-2018;
  }

int VolumeDigits(const double step)
  {
   if(step>=1.0)
      return 0;
   int digits=0;
   double scaled=step;
   while(digits<8 && MathAbs(scaled-MathRound(scaled))>1e-9)
     {
      scaled*=10.0;
      digits++;
     }
   return digits;
  }

double NormalizeVolumeDown(const string symbol,const double raw)
  {
   const double minimum=SymbolInfoDouble(symbol,SYMBOL_VOLUME_MIN);
   const double maximum=SymbolInfoDouble(symbol,SYMBOL_VOLUME_MAX);
   const double step=SymbolInfoDouble(symbol,SYMBOL_VOLUME_STEP);
   if(!IsFinitePositive(raw) || !IsFinitePositive(minimum) ||
      !IsFinitePositive(maximum) || !IsFinitePositive(step) || maximum<minimum)
      return 0.0;
   double volume=MathFloor(raw/step+1e-9)*step;
   volume=MathMin(volume,maximum);
   volume=NormalizeDouble(volume,VolumeDigits(step));
   return (volume>=minimum-1e-9 ? volume : 0.0);
  }

double NormalizeVolumeNearest(const string symbol,const double raw)
  {
   const double maximum=SymbolInfoDouble(symbol,SYMBOL_VOLUME_MAX);
   const double step=SymbolInfoDouble(symbol,SYMBOL_VOLUME_STEP);
   if(!MathIsValidNumber(raw) || raw==0.0 ||
      !IsFinitePositive(maximum) || !IsFinitePositive(step))
      return 0.0;
   const double sign=(raw>0.0 ? 1.0 : -1.0);
   const double absolute=MathMin(maximum,MathRound(MathAbs(raw)/step)*step);
   return sign*NormalizeDouble(absolute,VolumeDigits(step));
  }

bool ValidTick(const MqlTick &tick)
  {
   return tick.time_msc>0 && IsFinitePositive(tick.bid) &&
          IsFinitePositive(tick.ask) && tick.ask>tick.bid;
  }

ENUM_ORDER_TYPE_FILLING ResolveFilling(const string symbol)
  {
   long mode=0;
   if(!SymbolInfoInteger(symbol,SYMBOL_FILLING_MODE,mode))
      return ORDER_FILLING_FOK;
   if((mode&1)==1)
      return ORDER_FILLING_FOK;
   if((mode&2)==2)
      return ORDER_FILLING_IOC;
   return ORDER_FILLING_IOC;
  }

bool AcceptedRetcode(const uint retcode)
  {
   return retcode==TRADE_RETCODE_DONE;
  }

bool IsTradeSessionOpen(const string symbol,const datetime now)
  {
   MqlDateTime stamp;
   if(!TimeToStruct(now,stamp))
      return false;
   const int second_of_day=stamp.hour*3600+stamp.min*60+stamp.sec;
   datetime from=0,to=0;
   for(uint session=0;session<32;session++)
     {
      if(!SymbolInfoSessionTrade(symbol,(ENUM_DAY_OF_WEEK)stamp.day_of_week,
                                 session,from,to))
         break;
      MqlDateTime from_stamp,to_stamp;
      if(!TimeToStruct(from,from_stamp) || !TimeToStruct(to,to_stamp))
         continue;
      const int start=from_stamp.hour*3600+from_stamp.min*60+from_stamp.sec;
      const int end=to_stamp.hour*3600+to_stamp.min*60+to_stamp.sec;
      if(start==end)
         return true;
      if(start<end && second_of_day>=start && second_of_day<end)
         return true;
      if(start>end && (second_of_day>=start || second_of_day<end))
         return true;
     }
   return false;
  }

bool CommonMarketReady(const datetime now)
  {
   bool ready=true;
   for(int i=0;i<ASSET_COUNT;i++)
     {
      if(!IsActive(i,g_pending_decision_time))
         continue;
      MqlTick tick;
      if(!SymbolInfoTick(g_symbols[i],tick) || !ValidTick(tick) ||
         tick.time>now || now-tick.time>MAX_QUOTE_AGE_SECONDS)
        {
         g_stale_quote_waits++;
         ready=false;
         continue;
        }
      if(!IsTradeSessionOpen(g_symbols[i],now))
        {
         g_closed_session_waits++;
         ready=false;
        }
     }
   return ready;
  }

bool LoadClosedAssetState(const int index,const datetime decision_time,
                          double &signal,double &annual_vol)
  {
   signal=0.0;
   annual_vol=0.0;
   MqlRates rates[];
   ArraySetAsSeries(rates,true);
   ResetLastError();
   const int copied=CopyRates(g_symbols[index],PERIOD_D1,1,HISTORY_BUFFER,rates);
   const int copy_error=GetLastError();
   ResetLastError();
   const datetime current_bar_open=iTime(g_symbols[index],PERIOD_D1,0);
   const int time_error=GetLastError();
   if(copied<VOL_RETURN_COUNT+2 || copy_error!=0 || time_error!=0 ||
      current_bar_open<=0 || current_bar_open>decision_time)
      return false;
   for(int i=0;i<copied;i++)
     {
      if(rates[i].time<=0 || !IsFinitePositive(rates[i].close))
         return false;
      if(i>0 && rates[i].time>=rates[i-1].time)
         return false;
     }

   const datetime cutoff=(datetime)((long)decision_time-CALENDAR_LOOKBACK_SECONDS);
   int lookback_index=-1;
   datetime lookback_close_time=0;
   for(int i=1;i<copied;i++)
     {
      const datetime close_time=rates[i-1].time;
      if(close_time<=cutoff)
        {
         lookback_index=i;
         lookback_close_time=close_time;
         break;
        }
     }
   if(lookback_index<1 || lookback_close_time<=0)
      return false;
   const double formation=rates[0].close/rates[lookback_index].close-1.0;
   if(!MathIsValidNumber(formation))
      return false;
   signal=(formation>0.0 ? 1.0 : (formation<0.0 ? -1.0 : 0.0));

   double returns[VOL_RETURN_COUNT];
   double mean=0.0;
   for(int i=0;i<VOL_RETURN_COUNT;i++)
     {
      returns[i]=MathLog(rates[i].close/rates[i+1].close);
      if(!MathIsValidNumber(returns[i]))
         return false;
      mean+=returns[i];
     }
   mean/=(double)VOL_RETURN_COUNT;
   double variance=0.0;
   for(int i=0;i<VOL_RETURN_COUNT;i++)
      variance+=(returns[i]-mean)*(returns[i]-mean);
   variance/=(double)(VOL_RETURN_COUNT-1);
   const datetime oldest_close_time=rates[VOL_RETURN_COUNT-1].time;
   const double elapsed_days=(double)(current_bar_open-oldest_close_time)/86400.0;
   if(!IsFinitePositive(elapsed_days))
      return false;
   annual_vol=MathSqrt(variance)*
              MathSqrt(365.2425*(double)VOL_RETURN_COUNT/elapsed_days);
   return IsFinitePositive(annual_vol);
  }

double UsdFactorExposure()
  {
   double exposure=0.0;
   for(int i=0;i<=6;i++)
     {
      const double orientation=(IsDirectQuoteUsd(i) ? -1.0 : 1.0);
      exposure+=orientation*g_signal[i]*g_weight[i];
     }
   return exposure;
  }

bool BuildFrozenWeights(const datetime decision_time)
  {
   double inverse_sum=0.0;
   for(int i=0;i<ASSET_COUNT;i++)
     {
      g_weight[i]=0.0;
      if(IsActive(i,decision_time) && g_signal[i]!=0.0 &&
         IsFinitePositive(g_annual_vol[i]))
         inverse_sum+=1.0/g_annual_vol[i];
     }
   if(!IsFinitePositive(inverse_sum))
      return false;
   for(int i=0;i<ASSET_COUNT;i++)
     {
      if(IsActive(i,decision_time) && g_signal[i]!=0.0)
         g_weight[i]=MathMin(SINGLE_WEIGHT_CAP,
                             (1.0/g_annual_vol[i])/inverse_sum);
     }

   double fx_gross=0.0;
   for(int i=0;i<=6;i++)
      fx_gross+=g_weight[i];
   if(fx_gross>FX_GROSS_CAP)
     {
      const double scale=FX_GROSS_CAP/fx_gross;
      for(int i=0;i<=6;i++)
         g_weight[i]*=scale;
     }
   g_weight[7]=MathMin(g_weight[7],XAU_WEIGHT_CAP);
   g_weight[8]=MathMin(g_weight[8],BTC_WEIGHT_CAP);

   const double usd=MathAbs(UsdFactorExposure());
   if(usd>USD_FACTOR_CAP)
     {
      const double scale=USD_FACTOR_CAP/usd;
      for(int i=0;i<=6;i++)
         g_weight[i]*=scale;
     }
   double gross=0.0;
   for(int i=0;i<ASSET_COUNT;i++)
      gross+=g_weight[i];
   if(gross>TOTAL_GROSS_CAP)
     {
      const double scale=TOTAL_GROSS_CAP/gross;
      for(int i=0;i<ASSET_COUNT;i++)
         g_weight[i]*=scale;
     }

   fx_gross=0.0;
   gross=0.0;
   for(int i=0;i<ASSET_COUNT;i++)
     {
      if(g_weight[i]<-1e-12 || g_weight[i]>SINGLE_WEIGHT_CAP+1e-9)
         return false;
      gross+=g_weight[i];
      if(IsFx(i))
         fx_gross+=g_weight[i];
     }
   return gross<=TOTAL_GROSS_CAP+1e-9 && fx_gross<=FX_GROSS_CAP+1e-9 &&
          g_weight[7]<=XAU_WEIGHT_CAP+1e-9 &&
          g_weight[8]<=BTC_WEIGHT_CAP+1e-9 &&
          MathAbs(UsdFactorExposure())<=USD_FACTOR_CAP+1e-9;
  }

double UsdNotionalPerLot(const int index,const MqlTick &tick)
  {
   const double contract=SymbolInfoDouble(g_symbols[index],SYMBOL_TRADE_CONTRACT_SIZE);
   if(!IsFinitePositive(contract) || !ValidTick(tick))
      return 0.0;
   return (IsDirectQuoteUsd(index) ? contract*(tick.bid+tick.ask)*0.5 : contract);
  }

bool PlanTargetVolumes()
  {
   const double equity=AccountInfoDouble(ACCOUNT_EQUITY);
   const double free_margin=AccountInfoDouble(ACCOUNT_MARGIN_FREE);
   if(!IsFinitePositive(equity) || !IsFinitePositive(free_margin))
      return false;
   double total_margin=0.0;
   int planned=0;
   for(int i=0;i<ASSET_COUNT;i++)
     {
      g_target_signed_volume[i]=0.0;
      if(g_weight[i]<=0.0 || g_signal[i]==0.0)
         continue;
      MqlTick tick;
      if(!SymbolInfoTick(g_symbols[i],tick) || !ValidTick(tick))
         return false;
      const double notional_per_lot=UsdNotionalPerLot(i,tick);
      const double volume=NormalizeVolumeDown(g_symbols[i],
                                               equity*g_weight[i]/notional_per_lot);
      if(volume<=0.0)
        {
         g_below_min_volume++;
         continue;
        }
      const ENUM_ORDER_TYPE type=(g_signal[i]>0.0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL);
      double margin=0.0;
      if(!OrderCalcMargin(type,g_symbols[i],volume,
                          type==ORDER_TYPE_BUY ? tick.ask : tick.bid,margin) ||
         !MathIsValidNumber(margin) || margin<0.0)
         return false;
      g_target_signed_volume[i]=g_signal[i]*volume;
      total_margin+=margin;
      planned++;
     }
   if(planned<=0)
      return false;
   const double cap=MathMin(equity*MAX_MARGIN_EQUITY_PCT/100.0,
                            free_margin*MAX_FREE_MARGIN_USAGE_PCT/100.0);
   if(total_margin>cap && IsFinitePositive(cap))
     {
      const double scale=cap/total_margin;
      g_margin_scaled++;
      planned=0;
      for(int i=0;i<ASSET_COUNT;i++)
        {
         if(g_target_signed_volume[i]==0.0)
            continue;
         const double sign=(g_target_signed_volume[i]>0.0 ? 1.0 : -1.0);
         const double volume=NormalizeVolumeDown(g_symbols[i],
                                                  MathAbs(g_target_signed_volume[i])*scale);
         g_target_signed_volume[i]=sign*volume;
         if(volume>0.0)
            planned++;
        }
     }
   return planned>0;
  }

double OwnedSignedVolume(const string symbol)
  {
   double signed_volume=0.0;
   for(int i=PositionsTotal()-1;i>=0;i--)
     {
      const ulong ticket=PositionGetTicket(i);
      if(ticket==0 || !PositionSelectByTicket(ticket) ||
         PositionGetInteger(POSITION_MAGIC)!=(long)InpMagic ||
         PositionGetString(POSITION_SYMBOL)!=symbol)
         continue;
      const double volume=PositionGetDouble(POSITION_VOLUME);
      const long type=PositionGetInteger(POSITION_TYPE);
      signed_volume+=(type==POSITION_TYPE_BUY ? volume : -volume);
     }
   return signed_volume;
  }

bool SendOpen(const int index,const double signed_volume)
  {
   const double volume=NormalizeVolumeDown(g_symbols[index],MathAbs(signed_volume));
   if(volume<=0.0)
      return false;
   MqlTick tick;
   if(!SymbolInfoTick(g_symbols[index],tick) || !ValidTick(tick))
      return false;
   MqlTradeRequest request;
   MqlTradeCheckResult check;
   MqlTradeResult result;
   ZeroMemory(request);
   ZeroMemory(check);
   ZeroMemory(result);
   request.action=TRADE_ACTION_DEAL;
   request.symbol=g_symbols[index];
   request.magic=InpMagic;
   request.volume=volume;
   request.type=(signed_volume>0.0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL);
   request.price=(request.type==ORDER_TYPE_BUY ? tick.ask : tick.bid);
   request.deviation=InpDeviationPoints;
   request.type_filling=ResolveFilling(g_symbols[index]);
   request.comment="MTS005_DELTA";
   ResetLastError();
   const bool checked=OrderCheck(request,check);
   const int check_error=GetLastError();
   if(!checked || check_error!=0 || check.retcode!=0)
     {
      g_order_check_rejects++;
      return false;
     }
   ResetLastError();
   const bool sent=OrderSend(request,result);
   const int send_error=GetLastError();
   if(!sent || send_error!=0 || !AcceptedRetcode(result.retcode))
     {
      g_order_send_rejects++;
      if(result.retcode==TRADE_RETCODE_DONE_PARTIAL)
         g_partial_retcode_events++;
      return false;
     }
   return true;
  }

bool CloseTicketVolume(const ulong ticket,const double requested_volume)
  {
   if(ticket==0 || !PositionSelectByTicket(ticket) ||
      PositionGetInteger(POSITION_MAGIC)!=(long)InpMagic)
      return false;
   const string symbol=PositionGetString(POSITION_SYMBOL);
   const long position_type=PositionGetInteger(POSITION_TYPE);
   const double available=PositionGetDouble(POSITION_VOLUME);
   const double volume=NormalizeVolumeDown(symbol,MathMin(available,requested_volume));
   if(volume<=0.0)
      return false;
   MqlTick tick;
   if(!SymbolInfoTick(symbol,tick) || !ValidTick(tick))
      return false;
   MqlTradeRequest request;
   MqlTradeResult result;
   ZeroMemory(request);
   ZeroMemory(result);
   request.action=TRADE_ACTION_DEAL;
   request.position=ticket;
   request.symbol=symbol;
   request.magic=InpMagic;
   request.volume=volume;
   request.type=(position_type==POSITION_TYPE_BUY ? ORDER_TYPE_SELL : ORDER_TYPE_BUY);
   request.price=(request.type==ORDER_TYPE_BUY ? tick.ask : tick.bid);
   request.deviation=InpDeviationPoints;
   request.type_filling=ResolveFilling(symbol);
   request.comment="MTS005_DELTA";
   ResetLastError();
   const bool sent=OrderSend(request,result);
   const int send_error=GetLastError();
   if(!sent || send_error!=0 || !AcceptedRetcode(result.retcode))
     {
      g_order_send_rejects++;
      if(result.retcode==TRADE_RETCODE_DONE_PARTIAL)
         g_partial_retcode_events++;
      return false;
     }
   return true;
  }

bool ReduceOwnedVolume(const string symbol,const bool reduce_buys,double amount)
  {
   const double step=SymbolInfoDouble(symbol,SYMBOL_VOLUME_STEP);
   for(int i=PositionsTotal()-1;i>=0 && amount>=step*0.5;i--)
     {
      const ulong ticket=PositionGetTicket(i);
      if(ticket==0 || !PositionSelectByTicket(ticket) ||
         PositionGetInteger(POSITION_MAGIC)!=(long)InpMagic ||
         PositionGetString(POSITION_SYMBOL)!=symbol)
         continue;
      const long type=PositionGetInteger(POSITION_TYPE);
      if((reduce_buys && type!=POSITION_TYPE_BUY) ||
         (!reduce_buys && type!=POSITION_TYPE_SELL))
         continue;
      const double before=PositionGetDouble(POSITION_VOLUME);
      const double request=MathMin(before,amount);
      if(!CloseTicketVolume(ticket,request))
         return false;
      amount-=request;
     }
   return amount<step*0.5;
  }

bool RebalanceSymbol(const int index)
  {
   const string symbol=g_symbols[index];
   const double target=g_target_signed_volume[index];
   const double step=SymbolInfoDouble(symbol,SYMBOL_VOLUME_STEP);
   if(!IsFinitePositive(step))
      return false;

   // Remove positions opposing the frozen target before changing same-side size.
   for(int i=PositionsTotal()-1;i>=0;i--)
     {
      const ulong ticket=PositionGetTicket(i);
      if(ticket==0 || !PositionSelectByTicket(ticket) ||
         PositionGetInteger(POSITION_MAGIC)!=(long)InpMagic ||
         PositionGetString(POSITION_SYMBOL)!=symbol)
         continue;
      const long type=PositionGetInteger(POSITION_TYPE);
      const bool opposing=(target==0.0 ||
                           (target>0.0 && type==POSITION_TYPE_SELL) ||
                           (target<0.0 && type==POSITION_TYPE_BUY));
      if(opposing && !CloseTicketVolume(ticket,PositionGetDouble(POSITION_VOLUME)))
         return false;
     }

   const double current=OwnedSignedVolume(symbol);
   const double delta=NormalizeVolumeNearest(symbol,target-current);
   if(MathAbs(delta)<step*0.5)
      return true;
   if((current>=0.0 && delta>0.0) || (current<=0.0 && delta<0.0) || current==0.0)
      return SendOpen(index,delta);
   return ReduceOwnedVolume(symbol,current>0.0,MathAbs(delta));
  }

bool TargetsReached()
  {
   for(int i=0;i<ASSET_COUNT;i++)
     {
      const double step=SymbolInfoDouble(g_symbols[i],SYMBOL_VOLUME_STEP);
      if(!IsFinitePositive(step) ||
         MathAbs(OwnedSignedVolume(g_symbols[i])-g_target_signed_volume[i])>=step*0.5)
         return false;
     }
   return true;
  }

bool PrepareSnapshot(const datetime decision_time)
  {
   bool full_source=true;
   for(int i=0;i<ASSET_COUNT;i++)
     {
      g_signal[i]=0.0;
      g_annual_vol[i]=0.0;
      if(!IsActive(i,decision_time))
         continue;
      if(!LoadClosedAssetState(i,decision_time,g_signal[i],g_annual_vol[i]))
        {
         g_missing_weeks[i]++;
         full_source=false;
         continue;
        }
      if(InpLongOnlyComparator)
         g_signal[i]=1.0;
      if(g_signal[i]>0.0)
         g_long_signals[i]++;
      else if(g_signal[i]<0.0)
         g_short_signals[i]++;
     }
   if(!full_source)
      return false;
   g_source_valid_mondays++;
   const int year_index=DesignYearIndex(decision_time);
   if(year_index>=0)
      g_source_years[year_index]++;
   if(!BuildFrozenWeights(decision_time))
      return false;
   g_weight_valid_mondays++;
   return true;
  }

void BeginMonday(const datetime now,const int monday_key)
  {
   g_pending_monday_key=monday_key;
   g_pending_decision_time=now;
   g_snapshot_ready=false;
   g_volume_plan_ready=false;
   g_next_retry=0;
   g_monday_attempts++;
  }

void ProcessMonday(const datetime now)
  {
   MqlDateTime stamp;
   if(!TimeToStruct(now,stamp))
      return;
   if(stamp.day_of_week!=1)
     {
      if(g_pending_monday_key>0 && g_pending_monday_key!=g_last_monday_key &&
         DateKey(now)>g_pending_monday_key)
        {
         g_failed_rebalances++;
         g_last_monday_key=g_pending_monday_key;
        }
      return;
     }
   const int monday_key=DateKey(now);
   if(monday_key<=0 || monday_key==g_last_monday_key)
      return;
   if(monday_key!=g_pending_monday_key)
      BeginMonday(now,monday_key);
   else if(g_next_retry>0 && now<g_next_retry)
      return;

   if(!g_snapshot_ready)
     {
      if(!PrepareSnapshot(g_pending_decision_time))
        {
         g_rebalance_retries++;
         g_next_retry=now+60;
         return;
        }
      g_snapshot_ready=true;
     }
   if(!CommonMarketReady(now))
     {
      g_rebalance_retries++;
      g_next_retry=now+30;
      return;
     }
   if(!g_volume_plan_ready)
     {
      if(!PlanTargetVolumes())
        {
         g_rebalance_retries++;
         g_next_retry=now+30;
         return;
        }
      g_volume_plan_ready=true;
     }

   bool transition_ok=true;
   for(int i=0;i<ASSET_COUNT;i++)
     {
      if(!RebalanceSymbol(i))
         transition_ok=false;
     }
   if(transition_ok && TargetsReached())
     {
      g_completed_rebalances++;
      g_last_monday_key=monday_key;
      const long latency=(long)(now-g_pending_decision_time);
      if(latency>g_max_rebalance_latency_seconds)
         g_max_rebalance_latency_seconds=latency;
      const int year_index=DesignYearIndex(g_pending_decision_time);
      if(year_index>=0)
         g_execution_years[year_index]++;
      PrintFormat("MTS005_REBALANCE_COMPLETE decision=%I64d execution=%I64d latency_sec=%I64d usd_factor=%.8f",
                  (long)g_pending_decision_time,(long)now,latency,UsdFactorExposure());
      EmitFinancingExposure(now,true,"rebalance");
      return;
     }
   g_rebalance_retries++;
   g_next_retry=now+30;
  }

void EmitFinancingExposure(const datetime now,const bool force,const string reason)
  {
   const int day=DateKey(now);
   if(day<=0 || (!force && day==g_last_finance_day))
      return;
   g_last_finance_day=day;
   double fx=0.0,xau=0.0,btc=0.0;
   for(int i=0;i<ASSET_COUNT;i++)
     {
      const double lots=MathAbs(OwnedSignedVolume(g_symbols[i]));
      if(lots<=0.0)
         continue;
      MqlTick tick;
      if(!SymbolInfoTick(g_symbols[i],tick) || !ValidTick(tick))
         continue;
      const double notional=lots*UsdNotionalPerLot(i,tick);
      if(IsFx(i))
         fx+=notional;
      else if(i==7)
         xau+=notional;
      else
         btc+=notional;
     }
   PrintFormat("MTS005_FINANCE_EXPOSURE epoch=%I64d day=%d reason=%s fx_usd=%.2f xau_usd=%.2f btc_usd=%.2f",
               (long)now,day,reason,fx,xau,btc);
  }

int OnInit()
  {
   const ulong expected_magic=(InpLongOnlyComparator ? 260812008 : 260812007);
   if(_Symbol!=EXPECTED_SYMBOL || _Period!=PERIOD_H1 || !InpResearchAutoMode ||
      InpMagic!=expected_magic || InpDeviationPoints!=20 ||
      AccountInfoString(ACCOUNT_CURRENCY)!="USD")
     {
      PrintFormat("MTS005_IDENTITY_FAIL symbol=%s period=%d currency=%s",
                  _Symbol,(int)_Period,AccountInfoString(ACCOUNT_CURRENCY));
      return INIT_FAILED;
     }
   for(int i=0;i<ASSET_COUNT;i++)
     {
      ResetLastError();
      if(!SymbolSelect(g_symbols[i],true) || GetLastError()!=0)
        {
         PrintFormat("MTS005_SYMBOL_SELECT_FAIL symbol=%s error=%d",
                     g_symbols[i],GetLastError());
         return INIT_FAILED;
        }
     }
   ArrayInitialize(g_missing_weeks,0);
   ArrayInitialize(g_long_signals,0);
   ArrayInitialize(g_short_signals,0);
   ArrayInitialize(g_source_years,0);
   ArrayInitialize(g_execution_years,0);
   PrintFormat("MTS005_READY hypothesis_id=%s variant=%s primary=%s lookback_calendar_days=365 vol_returns=60 btc_active=%I64d",
               HYPOTHESIS_ID,(InpLongOnlyComparator ? "LONG_ONLY_COMPARATOR" : "TSMOM"),
               _Symbol,(long)BTC_ACTIVE_FROM);
   return INIT_SUCCEEDED;
  }

void OnTick()
  {
   MqlTick primary;
   if(!SymbolInfoTick(_Symbol,primary) || !ValidTick(primary))
      return;
   g_ticks_seen++;
   const datetime now=(datetime)primary.time;
   EmitFinancingExposure(now,false,"daily_open");
   ProcessMonday(now);
  }

void OnTradeTransaction(const MqlTradeTransaction &transaction,
                        const MqlTradeRequest &request,
                        const MqlTradeResult &result)
  {
   if(transaction.type!=TRADE_TRANSACTION_DEAL_ADD || transaction.deal==0 ||
      !HistoryDealSelect(transaction.deal) ||
      HistoryDealGetInteger(transaction.deal,DEAL_MAGIC)!=(long)InpMagic)
      return;
   const string symbol=HistoryDealGetString(transaction.deal,DEAL_SYMBOL);
   const int index=SymbolIndex(symbol);
   const ENUM_DEAL_TYPE deal_type=(ENUM_DEAL_TYPE)HistoryDealGetInteger(transaction.deal,DEAL_TYPE);
   const long entry=HistoryDealGetInteger(transaction.deal,DEAL_ENTRY);
   const datetime stamp=(datetime)HistoryDealGetInteger(transaction.deal,DEAL_TIME);
   const double volume=HistoryDealGetDouble(transaction.deal,DEAL_VOLUME);
   const double price=HistoryDealGetDouble(transaction.deal,DEAL_PRICE);
   const double profit=HistoryDealGetDouble(transaction.deal,DEAL_PROFIT);
   const double swap=HistoryDealGetDouble(transaction.deal,DEAL_SWAP);
   const double commission=HistoryDealGetDouble(transaction.deal,DEAL_COMMISSION);
   long spread_points=0;
   const double one_spread_cost=OneSpreadCostUsd(index,symbol,deal_type,volume,
                                                 price,spread_points);
   PrintFormat("MTS005_DEAL_COST epoch=%I64d deal=%I64u symbol=%s class=%s entry=%I64d type=%I64d volume=%.8f price=%.8f spread_points=%I64d one_spread_cost_usd=%.8f native_profit=%.8f native_swap=%.8f native_commission=%.8f",
               (long)stamp,transaction.deal,symbol,AssetClass(index),entry,
               (long)deal_type,volume,price,spread_points,one_spread_cost,
               profit,swap,commission);
   g_deal_profit+=profit;
   g_deal_swap+=swap;
   g_deal_commission+=commission;
  }

void OnDeinit(const int reason)
  {
   EmitFinancingExposure(TimeCurrent(),true,"deinit");
   for(int i=0;i<ASSET_COUNT;i++)
      PrintFormat("MTS005_SYMBOL_SOURCE symbol=%s missing_weeks=%I64d long=%I64d short=%I64d",
                  g_symbols[i],g_missing_weeks[i],g_long_signals[i],g_short_signals[i]);
   PrintFormat("MTS005_SOURCE_SUMMARY hypothesis_id=%s attempts=%I64d source_valid=%I64d weight_valid=%I64d y2018=%I64d y2019=%I64d y2020=%I64d y2021=%I64d reason=%d",
               HYPOTHESIS_ID,g_monday_attempts,g_source_valid_mondays,
               g_weight_valid_mondays,g_source_years[0],g_source_years[1],
               g_source_years[2],g_source_years[3],reason);
   PrintFormat("MTS005_EXEC_SUMMARY completed=%I64d failed=%I64d retries=%I64d stale_quote_waits=%I64d closed_session_waits=%I64d check_rejects=%I64d send_rejects=%I64d partial_retcode=%I64d below_min_volume=%I64d margin_scaled=%I64d max_latency_sec=%I64d execution_y2018=%I64d execution_y2019=%I64d execution_y2020=%I64d execution_y2021=%I64d",
               g_completed_rebalances,g_failed_rebalances,g_rebalance_retries,
               g_stale_quote_waits,g_closed_session_waits,g_order_check_rejects,
               g_order_send_rejects,g_partial_retcode_events,g_below_min_volume,
               g_margin_scaled,g_max_rebalance_latency_seconds,
               g_execution_years[0],g_execution_years[1],
               g_execution_years[2],g_execution_years[3]);
   PrintFormat("MTS005_ECON_TELEMETRY ticks=%I64d deal_profit=%.2f deal_swap=%.2f deal_commission=%.2f native_net=%.2f",
               g_ticks_seen,g_deal_profit,g_deal_swap,g_deal_commission,
               g_deal_profit+g_deal_swap+g_deal_commission);
  }
//+------------------------------------------------------------------+
