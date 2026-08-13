//+------------------------------------------------------------------+
//| EA_MultiAssetTSMOMD1V1.mq5                                      |
//| HYP-MULTI-TSMOM-D1-001 - frozen nine-asset design baseline      |
//+------------------------------------------------------------------+
#property copyright "AlphaFactory research"
#property version   "1.00"
#property strict
#property description "Nine-asset 252D own time-series momentum portfolio"

input bool   InpResearchAutoMode=true;
input ulong  InpMagic=260812003;
input int    InpDeviationPoints=20;

const string HYPOTHESIS_ID="HYP-MULTI-TSMOM-D1-001";
const string EXPECTED_SYMBOL="EURUSD";
#define ASSET_COUNT 9
#define FORMATION_CLOSES 253
#define VOL_RETURN_COUNT 60
const double SINGLE_WEIGHT_CAP=0.18;
const double FX_GROSS_CAP=0.70;
const double XAU_WEIGHT_CAP=0.25;
const double BTC_WEIGHT_CAP=0.20;
const double TOTAL_GROSS_CAP=1.00;
const double USD_FACTOR_CAP=0.25;
const double MAX_MARGIN_EQUITY_PCT=35.0;
const double MAX_FREE_MARGIN_USAGE_PCT=80.0;
const double DAILY_LOSS_KILL_PCT=3.5;
const double WEEKLY_LOSS_KILL_PCT=7.0;
const double MIN_FULL_SOURCE_RATIO=0.95;
const double MAX_SYMBOL_MISSING_RATIO=0.08;

string g_symbols[ASSET_COUNT]={"EURUSD","GBPUSD","AUDUSD","NZDUSD",
                               "USDJPY","USDCAD","USDCHF","XAUUSD","BTCUSD"};
double g_signal[ASSET_COUNT];
double g_annual_vol[ASSET_COUNT];
double g_weight[ASSET_COUNT];
double g_target_volume[ASSET_COUNT];
long   g_missing_weeks[ASSET_COUNT];
long   g_long_signals[ASSET_COUNT];
long   g_short_signals[ASSET_COUNT];

datetime g_last_h1_open=0;
int      g_last_monday_key=0;
int      g_day_key=0;
double   g_day_start_equity=0.0;
double   g_week_start_equity=0.0;
bool     g_risk_locked=false;

long g_ticks_seen=0;
long g_monday_attempts=0;
long g_full_source_mondays=0;
long g_valid_baskets=0;
long g_skipped_baskets=0;
long g_rebalance_years[4];
long g_entries_requested=0;
long g_entries_accepted=0;
long g_closes_requested=0;
long g_closes_accepted=0;
long g_below_min_volume=0;
long g_margin_scaled=0;
long g_order_check_rejects=0;
long g_order_send_rejects=0;
long g_close_rejects=0;
long g_risk_kills=0;
double g_deal_profit=0.0;
double g_deal_swap=0.0;
double g_deal_commission=0.0;

bool IsFinitePositive(const double value)
  {
   return MathIsValidNumber(value) && value>0.0;
  }

bool IsDirectQuoteUsd(const int index)
  {
   return index<=3 || index==7 || index==8;
  }

bool IsFx(const int index)
  {
   return index<=6;
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
   if(volume<minimum-1e-9)
      return 0.0;
   return volume;
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

bool AcceptedRetcode(const uint code)
  {
   return code==TRADE_RETCODE_DONE || code==TRADE_RETCODE_DONE_PARTIAL;
  }

bool ValidTick(const MqlTick &tick)
  {
   return tick.time_msc>0 && IsFinitePositive(tick.bid) &&
          IsFinitePositive(tick.ask) && tick.ask>tick.bid;
  }

bool LoadClosedAssetState(const int index,double &signal,double &annual_vol)
  {
   signal=0.0;
   annual_vol=0.0;
   double closes[];
   datetime times[];
   ArraySetAsSeries(closes,true);
   ArraySetAsSeries(times,true);
   ResetLastError();
   const int copied_close=CopyClose(g_symbols[index],PERIOD_D1,1,FORMATION_CLOSES,closes);
   const int close_error=GetLastError();
   ResetLastError();
   const int copied_time=CopyTime(g_symbols[index],PERIOD_D1,1,FORMATION_CLOSES,times);
   const int time_error=GetLastError();
   if(copied_close!=FORMATION_CLOSES || copied_time!=FORMATION_CLOSES ||
      close_error!=0 || time_error!=0)
      return false;
   for(int i=0;i<FORMATION_CLOSES;i++)
     {
      if(!IsFinitePositive(closes[i]) || times[i]<=0)
         return false;
      if(i>0 && times[i]>=times[i-1])
         return false;
     }
   const double formation=closes[0]/closes[FORMATION_CLOSES-1]-1.0;
   if(!MathIsValidNumber(formation))
      return false;
   if(formation>0.0)
      signal=1.0;
   else if(formation<0.0)
      signal=-1.0;
   else
      signal=0.0;

   double returns[VOL_RETURN_COUNT];
   double mean=0.0;
   for(int i=0;i<VOL_RETURN_COUNT;i++)
     {
      returns[i]=MathLog(closes[i]/closes[i+1]);
      if(!MathIsValidNumber(returns[i]))
         return false;
      mean+=returns[i];
     }
   mean/=(double)VOL_RETURN_COUNT;
   double variance=0.0;
   for(int i=0;i<VOL_RETURN_COUNT;i++)
      variance+=(returns[i]-mean)*(returns[i]-mean);
   variance/=(double)(VOL_RETURN_COUNT-1);
   annual_vol=MathSqrt(variance)*MathSqrt(252.0);
   return IsFinitePositive(annual_vol);
  }

double UsdFactorExposure(const double &weights[])
  {
   double exposure=0.0;
   for(int i=0;i<ASSET_COUNT;i++)
     {
      if(g_signal[i]==0.0 || weights[i]<=0.0)
         continue;
      // Direct pairs: BUY is short USD. Inverse pairs: BUY is long USD.
      const double orientation=(IsDirectQuoteUsd(i) ? -1.0 : 1.0);
      exposure+=orientation*g_signal[i]*weights[i];
     }
   return exposure;
  }

bool BuildFrozenWeights()
  {
   double inverse_sum=0.0;
   int active=0;
   for(int i=0;i<ASSET_COUNT;i++)
     {
      g_weight[i]=0.0;
      if(g_signal[i]==0.0 || !IsFinitePositive(g_annual_vol[i]))
         continue;
      inverse_sum+=1.0/g_annual_vol[i];
      active++;
     }
   if(active<=0 || !IsFinitePositive(inverse_sum))
      return false;
   double fx_gross=0.0;
   double max_single=0.0;
   for(int i=0;i<ASSET_COUNT;i++)
     {
      if(g_signal[i]==0.0)
         continue;
      g_weight[i]=(1.0/g_annual_vol[i])/inverse_sum;
      max_single=MathMax(max_single,g_weight[i]);
      if(IsFx(i))
         fx_gross+=g_weight[i];
     }

   double scale=1.0;
   if(max_single>SINGLE_WEIGHT_CAP)
      scale=MathMin(scale,SINGLE_WEIGHT_CAP/max_single);
   if(fx_gross>FX_GROSS_CAP)
      scale=MathMin(scale,FX_GROSS_CAP/fx_gross);
   if(g_weight[7]>XAU_WEIGHT_CAP)
      scale=MathMin(scale,XAU_WEIGHT_CAP/g_weight[7]);
   if(g_weight[8]>BTC_WEIGHT_CAP)
      scale=MathMin(scale,BTC_WEIGHT_CAP/g_weight[8]);
   double gross=0.0;
   for(int i=0;i<ASSET_COUNT;i++)
      gross+=g_weight[i];
   if(gross>TOTAL_GROSS_CAP)
      scale=MathMin(scale,TOTAL_GROSS_CAP/gross);
   double usd=MathAbs(UsdFactorExposure(g_weight));
   if(usd>USD_FACTOR_CAP)
      scale=MathMin(scale,USD_FACTOR_CAP/usd);
   if(!IsFinitePositive(scale))
      return false;
   for(int i=0;i<ASSET_COUNT;i++)
      g_weight[i]*=scale;
   return true;
  }

double UsdNotionalPerLot(const int index,const MqlTick &tick)
  {
   const double contract=SymbolInfoDouble(g_symbols[index],SYMBOL_TRADE_CONTRACT_SIZE);
   if(!IsFinitePositive(contract) || !ValidTick(tick))
      return 0.0;
   if(IsDirectQuoteUsd(index))
      return contract*(tick.bid+tick.ask)*0.5;
   return contract;
  }

bool PlanVolumes()
  {
   const double equity=AccountInfoDouble(ACCOUNT_EQUITY);
   const double free_margin=AccountInfoDouble(ACCOUNT_MARGIN_FREE);
   if(!IsFinitePositive(equity) || !IsFinitePositive(free_margin))
      return false;
   double total_margin=0.0;
   int tradable=0;
   for(int i=0;i<ASSET_COUNT;i++)
     {
      g_target_volume[i]=0.0;
      if(g_weight[i]<=0.0 || g_signal[i]==0.0)
         continue;
      MqlTick tick;
      if(!SymbolInfoTick(g_symbols[i],tick) || !ValidTick(tick))
         continue;
      const double notional_per_lot=UsdNotionalPerLot(i,tick);
      const double raw=(equity*g_weight[i])/notional_per_lot;
      const double volume=NormalizeVolumeDown(g_symbols[i],raw);
      if(volume<=0.0)
        {
         g_below_min_volume++;
         continue;
        }
      const ENUM_ORDER_TYPE type=(g_signal[i]>0.0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL);
      const double entry=(type==ORDER_TYPE_BUY ? tick.ask : tick.bid);
      double margin=0.0;
      if(!OrderCalcMargin(type,g_symbols[i],volume,entry,margin) ||
         !MathIsValidNumber(margin) || margin<0.0)
         continue;
      g_target_volume[i]=volume;
      total_margin+=margin;
      tradable++;
     }
   if(tradable<=0)
      return false;

   const double margin_cap=MathMin(equity*MAX_MARGIN_EQUITY_PCT/100.0,
                                   free_margin*MAX_FREE_MARGIN_USAGE_PCT/100.0);
   if(total_margin>margin_cap && IsFinitePositive(margin_cap))
     {
      const double scale=margin_cap/total_margin;
      g_margin_scaled++;
      tradable=0;
      for(int i=0;i<ASSET_COUNT;i++)
        {
         if(g_target_volume[i]<=0.0)
            continue;
         g_target_volume[i]=NormalizeVolumeDown(g_symbols[i],g_target_volume[i]*scale);
         if(g_target_volume[i]>0.0)
            tradable++;
        }
     }
   return tradable>0;
  }

bool CloseOwnedPosition(const ulong ticket,const string comment)
  {
   if(ticket==0 || !PositionSelectByTicket(ticket))
      return false;
   if(PositionGetInteger(POSITION_MAGIC)!=(long)InpMagic)
      return false;
   const string symbol=PositionGetString(POSITION_SYMBOL);
   const long position_type=PositionGetInteger(POSITION_TYPE);
   const double volume=PositionGetDouble(POSITION_VOLUME);
   MqlTick tick;
   if(!IsFinitePositive(volume) || !SymbolInfoTick(symbol,tick) || !ValidTick(tick))
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
   request.deviation=InpDeviationPoints;
   request.type_filling=ResolveFilling(symbol);
   request.comment=comment;
   if(position_type==POSITION_TYPE_BUY)
     {
      request.type=ORDER_TYPE_SELL;
      request.price=tick.bid;
     }
   else if(position_type==POSITION_TYPE_SELL)
     {
      request.type=ORDER_TYPE_BUY;
      request.price=tick.ask;
     }
   else
      return false;
   g_closes_requested++;
   ResetLastError();
   if(!OrderSend(request,result) || !AcceptedRetcode(result.retcode))
     {
      g_close_rejects++;
      return false;
     }
   g_closes_accepted++;
   return true;
  }

void CloseAllOwned(const string comment)
  {
   for(int i=PositionsTotal()-1;i>=0;i--)
     {
      const ulong ticket=PositionGetTicket(i);
      if(ticket==0 || !PositionSelectByTicket(ticket))
         continue;
      if(PositionGetInteger(POSITION_MAGIC)!=(long)InpMagic)
         continue;
      CloseOwnedPosition(ticket,comment);
     }
  }

bool SubmitPlannedEntry(const int index)
  {
   const double volume=g_target_volume[index];
   if(volume<=0.0 || g_signal[index]==0.0)
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
   request.type=(g_signal[index]>0.0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL);
   request.price=(request.type==ORDER_TYPE_BUY ? tick.ask : tick.bid);
   request.deviation=InpDeviationPoints;
   request.type_filling=ResolveFilling(g_symbols[index]);
   request.comment="MTS001";
   g_entries_requested++;
   ResetLastError();
   const bool check_ok=OrderCheck(request,check);
   const int check_error=GetLastError();
   if(!check_ok || check_error!=0 || check.retcode!=0)
     {
      g_order_check_rejects++;
      if(g_order_check_rejects<=10)
         PrintFormat("MTS_ORDER_CHECK_REJECT symbol=%s error=%d retcode=%u comment=%s",
                     g_symbols[index],check_error,check.retcode,check.comment);
      return false;
     }
   ResetLastError();
   const bool sent=OrderSend(request,result);
   const int send_error=GetLastError();
   if(!sent || send_error!=0 || !AcceptedRetcode(result.retcode))
     {
      g_order_send_rejects++;
      if(g_order_send_rejects<=10)
         PrintFormat("MTS_ORDER_SEND_REJECT symbol=%s error=%d retcode=%u comment=%s",
                     g_symbols[index],send_error,result.retcode,result.comment);
      return false;
     }
   g_entries_accepted++;
   return true;
  }

bool PrepareMondayBasket(const datetime decision_time)
  {
   g_monday_attempts++;
   bool full_source=true;
   for(int i=0;i<ASSET_COUNT;i++)
     {
      if(!LoadClosedAssetState(i,g_signal[i],g_annual_vol[i]))
        {
         full_source=false;
         g_missing_weeks[i]++;
         g_signal[i]=0.0;
         g_annual_vol[i]=0.0;
        }
      else if(g_signal[i]>0.0)
         g_long_signals[i]++;
      else if(g_signal[i]<0.0)
         g_short_signals[i]++;
     }
   // Fixed-universe economics are all-nine fail-closed. No partial basket.
   if(!full_source)
     {
      g_skipped_baskets++;
      return false;
     }
   g_full_source_mondays++;
   if(!BuildFrozenWeights() || !PlanVolumes())
     {
      g_skipped_baskets++;
      return false;
     }
   g_valid_baskets++;
   const int year_index=DesignYearIndex(decision_time);
   if(year_index>=0)
      g_rebalance_years[year_index]++;
   return true;
  }

void ProcessMonday(const datetime now)
  {
   MqlDateTime stamp;
   if(!TimeToStruct(now,stamp) || stamp.day_of_week!=1)
      return;
   const int monday_key=DateKey(now);
   if(monday_key<=0 || monday_key==g_last_monday_key)
      return;
   g_last_monday_key=monday_key;
   g_risk_locked=false;
   g_week_start_equity=AccountInfoDouble(ACCOUNT_EQUITY);
   CloseAllOwned("MTS_WEEKLY");
   if(!PrepareMondayBasket(now))
      return;
   for(int i=0;i<ASSET_COUNT;i++)
      SubmitPlannedEntry(i);
   PrintFormat("MTS_REBALANCE decision=%I64d equity=%.2f entries=%I64d usd_factor=%.8f",
               (long)now,AccountInfoDouble(ACCOUNT_EQUITY),g_entries_accepted,
               UsdFactorExposure(g_weight));
  }

void RefreshDayBaseline(const datetime now)
  {
   const int key=DateKey(now);
   if(key>0 && key!=g_day_key)
     {
      g_day_key=key;
      g_day_start_equity=AccountInfoDouble(ACCOUNT_EQUITY);
     }
  }

void ManagePortfolioRisk(const datetime now)
  {
   RefreshDayBaseline(now);
   if(g_risk_locked)
      return;
   const double equity=AccountInfoDouble(ACCOUNT_EQUITY);
   if(!IsFinitePositive(equity))
      return;
   const bool daily_hit=(IsFinitePositive(g_day_start_equity) &&
                         equity<=g_day_start_equity*(1.0-DAILY_LOSS_KILL_PCT/100.0));
   const bool weekly_hit=(IsFinitePositive(g_week_start_equity) &&
                          equity<=g_week_start_equity*(1.0-WEEKLY_LOSS_KILL_PCT/100.0));
   if(!daily_hit && !weekly_hit)
      return;
   g_risk_locked=true;
   g_risk_kills++;
   CloseAllOwned(daily_hit ? "MTS_DAILY_KILL" : "MTS_WEEK_KILL");
  }

bool ReadSeriesInteger(const ENUM_TIMEFRAMES timeframe,
                       const ENUM_SERIES_INFO_INTEGER property,
                       long &value)
  {
   value=0;
   ResetLastError();
   if(!SeriesInfoInteger(_Symbol,timeframe,property,value))
      return false;
   return GetLastError()==0;
  }

bool EmitD0SeriesProof()
  {
   long m5_synchronized=0,m5_first_epoch=0,m5_terminal_first_epoch=0;
   long m1_server_first_epoch=0,m1_terminal_first_epoch=0,m5_bars=0;
   if(!ReadSeriesInteger(PERIOD_M5,SERIES_SYNCHRONIZED,m5_synchronized) ||
      !ReadSeriesInteger(PERIOD_M5,SERIES_FIRSTDATE,m5_first_epoch) ||
      !ReadSeriesInteger(PERIOD_M5,SERIES_TERMINAL_FIRSTDATE,m5_terminal_first_epoch) ||
      !ReadSeriesInteger(PERIOD_M1,SERIES_SERVER_FIRSTDATE,m1_server_first_epoch) ||
      !ReadSeriesInteger(PERIOD_M1,SERIES_TERMINAL_FIRSTDATE,m1_terminal_first_epoch) ||
      !ReadSeriesInteger(PERIOD_M5,SERIES_BARS_COUNT,m5_bars))
      return false;
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
      return false;
   return true;
  }

int OnInit()
  {
   if(_Symbol!=EXPECTED_SYMBOL || _Period!=PERIOD_H1 || !InpResearchAutoMode ||
      InpMagic!=260812003 || InpDeviationPoints!=20 ||
      AccountInfoString(ACCOUNT_CURRENCY)!="USD")
     {
      PrintFormat("MTS_IDENTITY_FAIL symbol=%s period=%d currency=%s",
                  _Symbol,(int)_Period,AccountInfoString(ACCOUNT_CURRENCY));
      return INIT_FAILED;
     }
   for(int i=0;i<ASSET_COUNT;i++)
     {
      ResetLastError();
      if(!SymbolSelect(g_symbols[i],true) || GetLastError()!=0)
        {
         PrintFormat("MTS_SYMBOL_SELECT_FAIL symbol=%s error=%d",g_symbols[i],GetLastError());
         return INIT_FAILED;
        }
     }
   if(!EmitD0SeriesProof())
     {
      PrintFormat("MTS_D0_SERIES_PROOF_FAIL error=%d",GetLastError());
      return INIT_FAILED;
     }
   ArrayInitialize(g_missing_weeks,0);
   ArrayInitialize(g_long_signals,0);
   ArrayInitialize(g_short_signals,0);
   ArrayInitialize(g_rebalance_years,0);
   g_day_start_equity=AccountInfoDouble(ACCOUNT_EQUITY);
   g_week_start_equity=g_day_start_equity;
   PrintFormat("MTS_READY hypothesis_id=%s universe=EURUSD,GBPUSD,AUDUSD,NZDUSD,USDJPY,USDCAD,USDCHF,XAUUSD,BTCUSD formation=252D vol=60D gross_cap=%.2f fx_cap=%.2f usd_cap=%.2f",
               HYPOTHESIS_ID,TOTAL_GROSS_CAP,FX_GROSS_CAP,USD_FACTOR_CAP);
   return INIT_SUCCEEDED;
  }

void OnTick()
  {
   MqlTick primary;
   if(!SymbolInfoTick(_Symbol,primary) || !ValidTick(primary))
      return;
   g_ticks_seen++;
   const datetime now=(datetime)primary.time;
   ManagePortfolioRisk(now);
   const datetime current_h1=iTime(_Symbol,PERIOD_H1,0);
   if(current_h1==g_last_h1_open)
      return;
   if(current_h1<=0)
      return;
   g_last_h1_open=current_h1;
   ProcessMonday(now);
  }

void OnTradeTransaction(const MqlTradeTransaction &transaction,
                        const MqlTradeRequest &request,
                        const MqlTradeResult &result)
  {
   if(transaction.type!=TRADE_TRANSACTION_DEAL_ADD || transaction.deal==0 ||
      !HistoryDealSelect(transaction.deal))
      return;
   if(HistoryDealGetInteger(transaction.deal,DEAL_MAGIC)!=(long)InpMagic)
      return;
   g_deal_profit+=HistoryDealGetDouble(transaction.deal,DEAL_PROFIT);
   g_deal_swap+=HistoryDealGetDouble(transaction.deal,DEAL_SWAP);
   g_deal_commission+=HistoryDealGetDouble(transaction.deal,DEAL_COMMISSION);
  }

void OnDeinit(const int reason)
  {
   const double full_ratio=(g_monday_attempts>0 ?
                            (double)g_full_source_mondays/(double)g_monday_attempts : 0.0);
   bool symbol_coverage_pass=true;
   for(int i=0;i<ASSET_COUNT;i++)
     {
      const double miss=(g_monday_attempts>0 ?
                         (double)g_missing_weeks[i]/(double)g_monday_attempts : 1.0);
      if(miss>MAX_SYMBOL_MISSING_RATIO)
         symbol_coverage_pass=false;
      PrintFormat("MTS_SYMBOL_SOURCE symbol=%s missing_weeks=%I64d attempts=%I64d missing_ratio=%.8f long=%I64d short=%I64d",
                  g_symbols[i],g_missing_weeks[i],g_monday_attempts,miss,
                  g_long_signals[i],g_short_signals[i]);
     }
   const bool source_pass=(g_monday_attempts>0 && full_ratio>=MIN_FULL_SOURCE_RATIO &&
                           symbol_coverage_pass);
   PrintFormat("MTS_SOURCE_SUMMARY hypothesis_id=%s attempts=%I64d full_source=%I64d full_ratio=%.8f valid_baskets=%I64d skipped=%I64d y2018=%I64d y2019=%I64d y2020=%I64d y2021=%I64d source_gate_pass=%s reason=%d",
               HYPOTHESIS_ID,g_monday_attempts,g_full_source_mondays,full_ratio,
               g_valid_baskets,g_skipped_baskets,g_rebalance_years[0],g_rebalance_years[1],
               g_rebalance_years[2],g_rebalance_years[3],(string)source_pass,reason);
   PrintFormat("MTS_ECON_SUMMARY hypothesis_id=%s ticks=%I64d entries_requested=%I64d entries_accepted=%I64d closes_requested=%I64d closes_accepted=%I64d below_min_volume=%I64d margin_scaled=%I64d order_check_rejects=%I64d order_send_rejects=%I64d close_rejects=%I64d risk_kills=%I64d deal_profit=%.2f deal_swap=%.2f deal_commission=%.2f deal_net=%.2f",
               HYPOTHESIS_ID,g_ticks_seen,g_entries_requested,g_entries_accepted,
               g_closes_requested,g_closes_accepted,g_below_min_volume,g_margin_scaled,
               g_order_check_rejects,g_order_send_rejects,g_close_rejects,g_risk_kills,
               g_deal_profit,g_deal_swap,g_deal_commission,
               g_deal_profit+g_deal_swap+g_deal_commission);
  }

// Frozen baseline: own 252D sign, 60D inverse-vol, weekly all-nine basket.
//+------------------------------------------------------------------+
