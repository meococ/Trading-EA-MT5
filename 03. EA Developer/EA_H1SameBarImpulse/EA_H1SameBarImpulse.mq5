//+------------------------------------------------------------------+
//| EA_H1SameBarImpulse.mq5                                          |
//| HYP-SBI-XAUUSD-H1-001: closed-bar H1 impulse, flatten same H1    |
//+------------------------------------------------------------------+
#property strict
#property version   "1.00"
#property description "XAUUSD H1 same-bar impulse. Flatten before next H1. Not GBB."

#include <Trade/Trade.mqh>

input bool   InpResearchAutoMode=false;
input bool   InpEnableTelemetry=true;
input string InpHypothesisId="HYP-SBI-XAUUSD-H1-001";
input long   InpMagic=16081611;
input double InpRiskPercent=0.25;
input double InpMaxLot=0.03;
input double InpMaxDailyLossPct=3.5;
input double InpMaxWeeklyLossPct=6.0;
input double InpMaxAccountDrawdownPct=8.0;
input int    InpMaxTradesPerDay=8;
input int    InpDeviationPoints=30;
input int    InpFridayFlattenHour=20;
input int    InpLastEntryHour=21;
input int    InpFlattenMinute=50;
input int    InpATRPeriod=14;
input double InpBodyAtrMin=0.35;
input double InpMinRangeAtr=0.45;
input double InpCloseLocation=0.65;
input double InpSLATRBuffer=0.10;
input double InpMinSLATR=0.50;
input double InpMaxSLATR=1.20;
input double InpTargetR=0.80;
input double InpMinCostMultiple=6.0;
input int    InpMaxSpreadPoints=80;

const string EA_NAME="EA_H1SameBarImpulse";
const string EXPECTED_HYPOTHESIS="HYP-SBI-XAUUSD-H1-001";

struct SignalDecision
  {
   bool fired;
   datetime decision_time;
   datetime availability_time;
   int direction;
   double signal_high;
   double signal_low;
   double signal_close;
   double atr;
   double body_atr;
   double close_loc;
  };

CTrade g_trade;
int g_atr_handle=INVALID_HANDLE;
datetime g_last_bar_open=0;
datetime g_last_decision_time=0;
datetime g_entry_bar_open=0;
datetime g_entry_time=0;
double g_entry_price=0.0;
double g_initial_sl=0.0;
double g_initial_tp=0.0;
string g_pending_exit_reason="";
int g_day_key=0;
long g_week_key=0;
double g_day_start_equity=0.0;
double g_week_start_equity=0.0;
double g_peak_equity=0.0;
bool g_day_locked=false;
bool g_week_locked=false;
bool g_drawdown_locked=false;
int g_daily_entries=0;
bool g_runtime_failed=false;
long g_closed_bars=0;
long g_signals=0;
long g_long_signals=0;
long g_short_signals=0;
long g_entries=0;
long g_entry_rejects=0;
long g_spread_rejects=0;
long g_cost_rejects=0;
long g_window_skips=0;
long g_exposure_skips=0;
long g_geometry_rejects=0;
long g_volume_rejects=0;
long g_risk_lock_skips=0;
long g_close_attempts=0;
long g_close_rejects=0;
long g_closes=0;
long g_same_bar_closes=0;
long g_leak_closes=0;
long g_invalid_inputs=0;

bool IsFinite(const double value)
  {
   return(value!=EMPTY_VALUE && MathIsValidNumber(value));
  }

bool SymbolAllowed()
  {
   return(StringFind(_Symbol,"XAUUSD")==0);
  }

int DayKey(const datetime stamp)
  {
   MqlDateTime p;
   TimeToStruct(stamp,p);
   return(p.year*10000+p.mon*100+p.day);
  }

long WeekKey(const datetime stamp)
  {
   MqlDateTime p;
   TimeToStruct(stamp,p);
   const datetime day_start=stamp-p.hour*3600-p.min*60-p.sec;
   const int days_from_monday=(p.day_of_week+6)%7;
   return((long)(day_start-days_from_monday*86400)/604800);
  }

bool CurrentBarOpen(datetime &bar_open)
  {
   long raw=0;
   bar_open=0;
   if(!SeriesInfoInteger(_Symbol,PERIOD_H1,SERIES_LASTBAR_DATE,raw) || raw<=0)
      return(false);
   bar_open=(datetime)raw;
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
   const double bounded=MathMin(volume,MathMin(vmax,InpMaxLot));
   if(bounded<vmin)
      return(0.0);
   const double units=MathFloor((bounded-vmin+1e-12)/step);
   return(NormalizeDouble(vmin+units*step,VolumeDigits(step)));
  }

double FloorToTick(const double price,const double tick_size)
  {
   return(MathFloor(price/tick_size+1e-10)*tick_size);
  }

double CeilToTick(const double price,const double tick_size)
  {
   return(MathCeil(price/tick_size-1e-10)*tick_size);
  }

void PrintAccountState(const string tag)
  {
   PrintFormat("%s balance=%.2f equity=%.2f margin=%.2f free=%.2f level=%.2f so_mode=%d so_so=%.2f so_call=%.2f",
               tag,
               AccountInfoDouble(ACCOUNT_BALANCE),
               AccountInfoDouble(ACCOUNT_EQUITY),
               AccountInfoDouble(ACCOUNT_MARGIN),
               AccountInfoDouble(ACCOUNT_MARGIN_FREE),
               AccountInfoDouble(ACCOUNT_MARGIN_LEVEL),
               (int)AccountInfoInteger(ACCOUNT_MARGIN_SO_MODE),
               AccountInfoDouble(ACCOUNT_MARGIN_SO_SO),
               AccountInfoDouble(ACCOUNT_MARGIN_SO_CALL));
  }

bool ScanOwnedPosition(ulong &ticket,bool &found)
  {
   found=false;
   ticket=0;
   const int total=PositionsTotal();
   if(total<0)
      return(false);
   for(int i=0;i<total;i++)
     {
      const ulong candidate=PositionGetTicket(i);
      if(candidate==0 || !PositionSelectByTicket(candidate))
         return(false);
      if(PositionGetString(POSITION_SYMBOL)!=_Symbol)
         continue;
      if(PositionGetInteger(POSITION_MAGIC)!=InpMagic)
         continue;
      if(found)
         return(false);
      found=true;
      ticket=candidate;
     }
   return(true);
  }

bool ForeignSymbolExposure(bool &scan_ok)
  {
   scan_ok=true;
   const int total=PositionsTotal();
   if(total<0)
     {
      scan_ok=false;
      return(true);
     }
   for(int i=0;i<total;i++)
     {
      const ulong ticket=PositionGetTicket(i);
      if(ticket==0 || !PositionSelectByTicket(ticket))
        {
         scan_ok=false;
         return(true);
        }
      if(PositionGetString(POSITION_SYMBOL)==_Symbol &&
         PositionGetInteger(POSITION_MAGIC)!=InpMagic)
         return(true);
     }
   return(false);
  }

void RefreshRiskLocks(const datetime server_now)
  {
   const double equity=AccountInfoDouble(ACCOUNT_EQUITY);
   const int day=DayKey(server_now);
   const long week=WeekKey(server_now);
   if(g_day_key!=day)
     {
      g_day_key=day;
      g_day_start_equity=equity;
      g_day_locked=false;
      g_daily_entries=0;
     }
   if(g_week_key!=week)
     {
      g_week_key=week;
      g_week_start_equity=equity;
      g_week_locked=false;
     }
   if(g_peak_equity<=0.0 || equity>g_peak_equity)
      g_peak_equity=equity;
   if(g_day_start_equity>0.0 &&
      equity<=g_day_start_equity*(1.0-InpMaxDailyLossPct/100.0))
      g_day_locked=true;
   if(g_week_start_equity>0.0 &&
      equity<=g_week_start_equity*(1.0-InpMaxWeeklyLossPct/100.0))
      g_week_locked=true;
   if(g_peak_equity>0.0 &&
      equity<=g_peak_equity*(1.0-InpMaxAccountDrawdownPct/100.0))
      g_drawdown_locked=true;
  }

bool EntryWindowOpen(const datetime server_now)
  {
   MqlDateTime p;
   TimeToStruct(server_now,p);
   if(p.day_of_week==0 || p.day_of_week==6)
      return(false);
   if(p.min>=InpFlattenMinute)
      return(false);
   if(p.hour>=InpLastEntryHour)
      return(false);
   if(p.day_of_week==5 && p.hour>=InpFridayFlattenHour)
      return(false);
   return(true);
  }

bool FlattenNow(const datetime server_now,string &reason)
  {
   MqlDateTime p;
   TimeToStruct(server_now,p);
   if(p.day_of_week==0 || p.day_of_week==6)
     {
      reason="WEEKEND_FLAT";
      return(true);
     }
   if(p.day_of_week==5 && p.hour>=InpFridayFlattenHour)
     {
      reason="FRIDAY_FLAT";
      return(true);
     }
   if(p.min>=InpFlattenMinute)
     {
      reason="TIME_STOP";
      return(true);
     }
   return(false);
  }

void ClearPositionState()
  {
   g_entry_bar_open=0;
   g_entry_time=0;
   g_entry_price=0.0;
   g_initial_sl=0.0;
   g_initial_tp=0.0;
   g_pending_exit_reason="";
  }

bool CloseOwned(const string reason,const datetime current_bar_open)
  {
   ulong ticket=0;
   bool found=false;
   if(!ScanOwnedPosition(ticket,found))
     {
      g_runtime_failed=true;
      Print("SBI001_FATAL reason=POSITION_SCAN");
      return(false);
     }
   if(!found)
      return(true);
   g_close_attempts++;
   g_pending_exit_reason=reason;
   g_trade.SetExpertMagicNumber(InpMagic);
   g_trade.SetDeviationInPoints(InpDeviationPoints);
   g_trade.SetTypeFillingBySymbol(_Symbol);
   const bool sent=g_trade.PositionClose(ticket,InpDeviationPoints);
   const uint retcode=g_trade.ResultRetcode();
   if(!sent || (retcode!=TRADE_RETCODE_DONE && retcode!=TRADE_RETCODE_DONE_PARTIAL))
     {
      g_close_rejects++;
      PrintFormat("SBI001_CLOSE_REJECT reason=%s ticket=%I64u retcode=%u closed_same_bar=false",
                  reason,ticket,retcode);
      return(false);
     }
   const bool same_bar=(g_entry_bar_open>0 && current_bar_open==g_entry_bar_open &&
                        StringFind(reason,"LEAKED")<0);
   g_closes++;
   if(same_bar)
      g_same_bar_closes++;
   if(StringFind(reason,"LEAKED")==0)
      g_leak_closes++;
   PrintFormat("SBI001_CLOSE reason=%s ticket=%I64u retcode=%u closed_same_bar=%s entry_bar=%I64d current_bar=%I64d",
               reason,ticket,retcode,(same_bar ? "true" : "false"),
               (long)g_entry_bar_open,(long)current_bar_open);
   PrintAccountState("SBI001_CLOSE_ACCT");
   return(true);
  }

bool CopyClosedATR(double &value)
  {
   double raw[];
   ArraySetAsSeries(raw,true);
   if(g_atr_handle==INVALID_HANDLE || CopyBuffer(g_atr_handle,0,1,1,raw)!=1)
      return(false);
   value=raw[0];
   return(IsFinite(value) && value>0.0);
  }

bool BuildSignal(const datetime availability_time,SignalDecision &signal)
  {
   ZeroMemory(signal);
   if(g_atr_handle==INVALID_HANDLE || BarsCalculated(g_atr_handle)<InpATRPeriod+2)
     {
      g_invalid_inputs++;
      return(false);
     }
   MqlRates rates[];
   ArraySetAsSeries(rates,true);
   if(CopyRates(_Symbol,PERIOD_H1,1,1,rates)!=1)
     {
      g_invalid_inputs++;
      return(false);
     }
   const MqlRates bar=rates[0];
   if(bar.time<=0 || bar.time==g_last_decision_time)
      return(false);
   if((long)(availability_time-bar.time)!=PeriodSeconds(PERIOD_H1))
     {
      g_invalid_inputs++;
      return(false);
     }
   g_last_decision_time=bar.time;
   g_closed_bars++;

   double atr=0.0;
   if(!CopyClosedATR(atr))
     {
      g_invalid_inputs++;
      return(false);
     }
   const double range=bar.high-bar.low;
   const double body=MathAbs(bar.close-bar.open);
   if(!IsFinite(range) || !IsFinite(body) || range<=0.0 || body<=0.0)
      return(false);
   const double body_atr=body/atr;
   const double range_atr=range/atr;
   const double close_loc=(bar.close-bar.low)/range;
   if(body_atr<InpBodyAtrMin || range_atr<InpMinRangeAtr)
      return(false);

   int direction=0;
   if(bar.close>bar.open && close_loc>=InpCloseLocation)
      direction=1;
   else if(bar.close<bar.open && (1.0-close_loc)>=InpCloseLocation)
      direction=-1;
   if(direction==0)
      return(false);

   signal.fired=true;
   signal.decision_time=bar.time;
   signal.availability_time=availability_time;
   signal.direction=direction;
   signal.signal_high=bar.high;
   signal.signal_low=bar.low;
   signal.signal_close=bar.close;
   signal.atr=atr;
   signal.body_atr=body_atr;
   signal.close_loc=close_loc;
   g_signals++;
   if(direction>0) g_long_signals++; else g_short_signals++;
   if(InpEnableTelemetry)
      PrintFormat("SBI001_SIGNAL decision=%I64d dir=%s body_atr=%.3f close_loc=%.3f c=%.5f atr=%.5f",
                  (long)bar.time,(direction>0 ? "LONG" : "SHORT"),
                  body_atr,close_loc,bar.close,atr);
   return(true);
  }

bool SubmitEntry(const SignalDecision &signal,const datetime current_bar_open)
  {
   ulong owned=0;
   bool found=false;
   if(!ScanOwnedPosition(owned,found))
     {
      g_runtime_failed=true;
      Print("SBI001_FATAL reason=POSITION_SCAN");
      return(false);
     }
   if(found)
     {
      g_exposure_skips++;
      return(false);
     }
   bool scan_ok=true;
   if(ForeignSymbolExposure(scan_ok))
     {
      if(!scan_ok)
        {
         g_runtime_failed=true;
         Print("SBI001_FATAL reason=FOREIGN_SCAN");
         return(false);
        }
      g_exposure_skips++;
      return(false);
     }
   if(!signal.fired)
      return(false);
   if(!EntryWindowOpen(signal.availability_time))
     {
      g_window_skips++;
      return(false);
     }
   if(g_day_locked || g_week_locked || g_drawdown_locked ||
      g_daily_entries>=InpMaxTradesPerDay)
     {
      g_risk_lock_skips++;
      return(false);
     }
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick) || !IsFinite(tick.ask) || !IsFinite(tick.bid) ||
      tick.ask<=tick.bid || tick.bid<=0.0)
     {
      g_geometry_rejects++;
      return(false);
     }
   const double point=SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   const double tick_size=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);
   if(point<=0.0 || tick_size<=0.0)
     {
      g_geometry_rejects++;
      return(false);
     }
   const double spread_price=tick.ask-tick.bid;
   const double spread_points=spread_price/point;
   if(!IsFinite(spread_points) || spread_points>InpMaxSpreadPoints)
     {
      g_spread_rejects++;
      return(false);
     }

   const double entry=(signal.direction>0 ? tick.ask : tick.bid);
   const double raw_stop=(signal.direction>0
                          ? signal.signal_low-InpSLATRBuffer*signal.atr
                          : signal.signal_high+InpSLATRBuffer*signal.atr);
   double risk_distance=(signal.direction>0 ? entry-raw_stop : raw_stop-entry);
   risk_distance=MathMax(InpMinSLATR*signal.atr,MathMin(risk_distance,InpMaxSLATR*signal.atr));
   if(!IsFinite(risk_distance) || risk_distance<=0.0)
     {
      g_geometry_rejects++;
      return(false);
     }
   if(risk_distance<InpMinCostMultiple*spread_price)
     {
      g_cost_rejects++;
      PrintFormat("SBI001_ENTRY_REJECT reason=COST_WINDOW risk=%.5f spread=%.5f",
                  risk_distance,spread_price);
      return(false);
     }
   const double raw_sl=entry-signal.direction*risk_distance;
   const double raw_tp=entry+signal.direction*InpTargetR*risk_distance;
   const double sl=(signal.direction>0 ? FloorToTick(raw_sl,tick_size) : CeilToTick(raw_sl,tick_size));
   const double tp=(signal.direction>0 ? CeilToTick(raw_tp,tick_size) : FloorToTick(raw_tp,tick_size));
   if(MathAbs(entry-sl)<=0.0 || MathAbs(tp-entry)<=0.0)
     {
      g_geometry_rejects++;
      return(false);
     }

   const ENUM_ORDER_TYPE order_type=(signal.direction>0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL);
   double one_lot_loss=0.0;
   if(!OrderCalcProfit(order_type,_Symbol,1.0,entry,sl,one_lot_loss) ||
      !IsFinite(one_lot_loss) || one_lot_loss>=0.0)
     {
      g_geometry_rejects++;
      PrintFormat("SBI001_ENTRY_REJECT reason=CALC_PROFIT entry=%.5f sl=%.5f",entry,sl);
      return(false);
     }
   const double equity=AccountInfoDouble(ACCOUNT_EQUITY);
   double volume=NormalizeVolumeDown(equity*(InpRiskPercent/100.0)/MathAbs(one_lot_loss));
   if(volume<=0.0)
     {
      g_volume_rejects++;
      PrintFormat("SBI001_ENTRY_REJECT reason=VOLUME_ZERO loss=%.2f",one_lot_loss);
      return(false);
     }
   const double contract=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_CONTRACT_SIZE);
   const double hist_px=MathMax(entry,MathMax(SymbolInfoDouble(_Symbol,SYMBOL_BID),
                                              SymbolInfoDouble(_Symbol,SYMBOL_ASK)));
   if(!IsFinite(contract) || !IsFinite(hist_px) || contract<=0.0 || hist_px<=0.0)
     {
      g_geometry_rejects++;
      return(false);
     }
   double margin_px=hist_px;
   if(contract>=10.0 && hist_px>=100.0)
      margin_px=MathMax(hist_px,5000.0);
   const double raw_max=equity*0.50/(contract*margin_px);
   double max_volume=NormalizeVolumeDown(raw_max);
   if(max_volume<=0.0 && raw_max>0.0)
     {
      const double vmin=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN);
      if(IsFinite(vmin) && vmin>0.0 && raw_max>=vmin*0.50)
         max_volume=NormalizeVolumeDown(vmin);
     }
   if(max_volume<=0.0)
     {
      g_volume_rejects++;
      PrintFormat("SBI001_ENTRY_REJECT reason=MAX_VOLUME_ZERO raw=%.5f margin_px=%.5f",
                  raw_max,margin_px);
      return(false);
     }
   if(volume>max_volume)
     {
      PrintFormat("SBI001_VOLUME_CAP from=%.2f to=%.2f hist=%.5f margin_px=%.5f",
                  volume,max_volume,hist_px,margin_px);
      volume=max_volume;
     }
   double margin=0.0;
   if(!OrderCalcMargin(order_type,_Symbol,volume,entry,margin) || !IsFinite(margin) ||
      margin>AccountInfoDouble(ACCOUNT_MARGIN_FREE))
     {
      g_entry_rejects++;
      PrintFormat("SBI001_ENTRY_REJECT reason=MARGIN vol=%.2f entry=%.5f margin=%.2f",
                  volume,entry,margin);
      return(false);
     }

   g_trade.SetExpertMagicNumber(InpMagic);
   g_trade.SetDeviationInPoints(InpDeviationPoints);
   g_trade.SetTypeFillingBySymbol(_Symbol);
   const bool sent=g_trade.PositionOpen(_Symbol,order_type,volume,entry,0.0,0.0,"SBI_SAMEBAR");
   const uint retcode=g_trade.ResultRetcode();
   if(!sent || (retcode!=TRADE_RETCODE_DONE && retcode!=TRADE_RETCODE_DONE_PARTIAL))
     {
      g_entry_rejects++;
      PrintFormat("SBI001_ENTRY_REJECT dir=%s vol=%.2f entry=%.5f sl=%.5f tp=%.5f retcode=%u",
                  (signal.direction>0 ? "LONG" : "SHORT"),volume,entry,sl,tp,retcode);
      return(false);
     }
   g_entries++;
   g_daily_entries++;
   g_entry_bar_open=current_bar_open;
   g_entry_time=signal.availability_time;
   g_entry_price=(g_trade.ResultPrice()>0.0 ? g_trade.ResultPrice() : entry);
   g_initial_sl=sl;
   g_initial_tp=tp;
   PrintFormat("SBI001_ENTRY decision=%I64d dir=%s vol=%.2f entry=%.5f sl=%.5f tp=%.5f same_bar=true retcode=%u",
               (long)signal.decision_time,(signal.direction>0 ? "LONG" : "SHORT"),
               volume,g_entry_price,sl,tp,retcode);
   PrintAccountState("SBI001_ENTRY_ACCT");
   return(true);
  }

void ManageOpenPosition(const datetime server_now,const datetime current_bar_open)
  {
   ulong ticket=0;
   bool found=false;
   if(!ScanOwnedPosition(ticket,found))
     {
      g_runtime_failed=true;
      Print("SBI001_FATAL reason=POSITION_SCAN");
      return;
     }
   if(!found)
     {
      if(g_entry_bar_open>0)
         ClearPositionState();
      return;
     }
   if(g_entry_bar_open<=0)
     {
      g_runtime_failed=true;
      CloseOwned("RESTART_FLAT",current_bar_open);
      return;
     }
   if(current_bar_open!=g_entry_bar_open)
     {
      g_runtime_failed=true;
      CloseOwned("LEAKED_NEW_BAR",current_bar_open);
      return;
     }
   string flatten_reason="";
   if(FlattenNow(server_now,flatten_reason))
     {
      CloseOwned(flatten_reason,current_bar_open);
      return;
     }
   if(!PositionSelectByTicket(ticket) || (g_initial_sl<=0.0 && g_initial_tp<=0.0))
      return;
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick) || !IsFinite(tick.bid) || !IsFinite(tick.ask))
      return;
   const bool is_long=(PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_BUY);
   string exit_reason="";
   if(is_long)
     {
      if(g_initial_sl>0.0 && tick.bid<=g_initial_sl)
         exit_reason="SL";
      else if(g_initial_tp>0.0 && tick.bid>=g_initial_tp)
         exit_reason="TP";
     }
   else
     {
      if(g_initial_sl>0.0 && tick.ask>=g_initial_sl)
         exit_reason="SL";
      else if(g_initial_tp>0.0 && tick.ask<=g_initial_tp)
         exit_reason="TP";
     }
   if(exit_reason!="")
      CloseOwned(exit_reason,current_bar_open);
  }

string ExitReasonName(const long reason)
  {
   if(reason==DEAL_REASON_SL) return("SL");
   if(reason==DEAL_REASON_TP) return("TP");
   if(reason==DEAL_REASON_EXPERT && g_pending_exit_reason!="") return(g_pending_exit_reason);
   return(StringFormat("DEAL_REASON_%d",(int)reason));
  }

void OnTradeTransaction(const MqlTradeTransaction &trans,
                        const MqlTradeRequest &request,
                        const MqlTradeResult &result)
  {
   if(trans.type!=TRADE_TRANSACTION_DEAL_ADD || trans.deal==0 || !HistoryDealSelect(trans.deal))
      return;
   if(HistoryDealGetString(trans.deal,DEAL_SYMBOL)!=_Symbol ||
      HistoryDealGetInteger(trans.deal,DEAL_MAGIC)!=InpMagic)
      return;
   const long entry_kind=HistoryDealGetInteger(trans.deal,DEAL_ENTRY);
   if(entry_kind!=DEAL_ENTRY_OUT && entry_kind!=DEAL_ENTRY_OUT_BY)
      return;
   datetime current_bar_open=0;
   CurrentBarOpen(current_bar_open);
   const bool same_bar=(g_entry_bar_open>0 && current_bar_open==g_entry_bar_open &&
                        StringFind(g_pending_exit_reason,"LEAKED")<0);
   PrintFormat("SBI001_EXIT deal=%I64u reason=%s profit=%.2f commission=%.2f swap=%.2f closed_same_bar=%s",
               trans.deal,ExitReasonName(HistoryDealGetInteger(trans.deal,DEAL_REASON)),
               HistoryDealGetDouble(trans.deal,DEAL_PROFIT),
               HistoryDealGetDouble(trans.deal,DEAL_COMMISSION),
               HistoryDealGetDouble(trans.deal,DEAL_SWAP),
               (same_bar ? "true" : "false"));
   ulong ticket=0;
   bool found=false;
   if(!ScanOwnedPosition(ticket,found) || !found)
      ClearPositionState();
  }

int OnInit()
  {
   if(_Period!=PERIOD_H1 || !SymbolAllowed() ||
      InpHypothesisId!=EXPECTED_HYPOTHESIS ||
      InpRiskPercent<=0.0 || InpMaxLot<=0.0 ||
      InpLastEntryHour<12 || InpLastEntryHour>22 ||
      InpFlattenMinute<45 || InpFlattenMinute>59 ||
      InpBodyAtrMin<=0.0 || InpMinRangeAtr<=0.0 ||
      InpCloseLocation<=0.5 || InpCloseLocation>=1.0 ||
      InpTargetR<=0.0 || InpMinCostMultiple<=0.0)
      return(INIT_PARAMETERS_INCORRECT);

   g_atr_handle=iATR(_Symbol,PERIOD_H1,InpATRPeriod);
   if(g_atr_handle==INVALID_HANDLE)
     {
      Print("SBI001_FATAL reason=ATR_HANDLE");
      return(INIT_FAILED);
     }
   g_trade.SetExpertMagicNumber(InpMagic);
   g_trade.SetDeviationInPoints(InpDeviationPoints);
   g_trade.SetTypeFillingBySymbol(_Symbol);
   const datetime now=TimeCurrent();
   const double equity=AccountInfoDouble(ACCOUNT_EQUITY);
   g_day_key=DayKey(now);
   g_week_key=WeekKey(now);
   g_day_start_equity=equity;
   g_week_start_equity=equity;
   g_peak_equity=equity;
   if(!CurrentBarOpen(g_last_bar_open) || g_last_bar_open<=0)
      return(INIT_FAILED);
   PrintFormat("SBI001_INIT ea=%s hyp=%s symbol=%s tf=H1 risk=%.2f max_lot=%.2f flatten_min=%d",
               EA_NAME,InpHypothesisId,_Symbol,InpRiskPercent,InpMaxLot,InpFlattenMinute);
   PrintAccountState("SBI001_INIT_ACCT");
   return(INIT_SUCCEEDED);
  }

void OnDeinit(const int reason)
  {
   if(g_atr_handle!=INVALID_HANDLE)
      IndicatorRelease(g_atr_handle);
   PrintFormat("SBI001_SUMMARY reason=%d failed=%s closed_bars=%I64d signals=%I64d long=%I64d short=%I64d entries=%I64d entry_rej=%I64d spread_rej=%I64d cost_rej=%I64d window_skip=%I64d expo_skip=%I64d geom_rej=%I64d vol_rej=%I64d risk_skip=%I64d closes=%I64d same_bar_closes=%I64d leak_closes=%I64d close_rej=%I64d invalid=%I64d",
               reason,(g_runtime_failed ? "true" : "false"),g_closed_bars,g_signals,
               g_long_signals,g_short_signals,g_entries,g_entry_rejects,g_spread_rejects,
               g_cost_rejects,g_window_skips,g_exposure_skips,g_geometry_rejects,g_volume_rejects,
               g_risk_lock_skips,g_closes,g_same_bar_closes,g_leak_closes,
               g_close_rejects,g_invalid_inputs);
   PrintAccountState("SBI001_DEINIT_ACCT");
  }

void OnTick()
  {
   datetime current_bar_open=0;
   if(!CurrentBarOpen(current_bar_open) || current_bar_open<=0)
      return;
   const datetime server_now=TimeCurrent();
   RefreshRiskLocks(server_now);
   ManageOpenPosition(server_now,current_bar_open);
   if(g_runtime_failed)
      return;
   if(current_bar_open==g_last_bar_open)
      return;
   g_last_bar_open=current_bar_open;
   ulong ticket=0;
   bool found=false;
   if(!ScanOwnedPosition(ticket,found))
     {
      g_runtime_failed=true;
      return;
     }
   if(found)
      return;
   SignalDecision signal;
   if(BuildSignal(current_bar_open,signal) && signal.fired)
      SubmitEntry(signal,current_bar_open);
  }
//+------------------------------------------------------------------+
