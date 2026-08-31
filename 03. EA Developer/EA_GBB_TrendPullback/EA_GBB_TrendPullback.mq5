//+------------------------------------------------------------------+
//| EA_GBB_TrendPullback.mq5                                         |
//| HYP-GBB-S2-XAUUSD-H1-002: closed-bar GBB S2 trend pullback       |
//+------------------------------------------------------------------+
#property strict
#property version   "1.00"
#property description "Untuned XAUUSD H1 GBB S2 closed-bar trend-pullback baseline"

#include <Trade/Trade.mqh>

input group "--- Frozen research authority ---"
input bool   InpResearchAutoMode=false;
input bool   InpEnableTelemetry=true;
input string InpHypothesisId="HYP-GBB-S2-XAUUSD-H1-002";
input string InpVariantTag="GBB_S2_TREND_PULLBACK";

input group "--- Frozen execution and risk ---"
input long   InpMagic=5604801;
input double InpRiskPercent=0.25;
input double InpMaxDailyLossPct=3.5;
input double InpMaxWeeklyLossPct=6.0;
input double InpMaxAccountDrawdownPct=8.0;
input int    InpMaxTradesPerDay=2;
input int    InpDeviationPoints=30;
input int    InpFridayFlattenHour=20;
input int    InpDailyFlatHour=21;
input int    InpDailyFlatMinute=50;
input double InpTargetR=1.50;
input int    InpTimeStopBars=24;
input int    InpATRPeriod=14;
input double InpSLATRBuffer=0.20;
input double InpMinSLATR=0.80;
input double InpMaxSLATR=2.50;
input int    InpMaxSpreadPoints=80;

const string EA_NAME="EA_GBB_TrendPullback";
const string EXPECTED_HYPOTHESIS="HYP-GBB-S2-XAUUSD-H1-002";
const string EXPECTED_VARIANT="GBB_S2_TREND_PULLBACK";
const int    GBB_REGIME_BUFFER=20;
const int    GBB_UPPER_BUFFER=3;
const int    GBB_LOWER_BUFFER=5;
const int    GBB_SIGNAL_BUFFER=31;
const int    GBB_WARMUP_BARS=400;

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
   double upper;
   double lower;
   double signal_code;
   double regime;
  };

CTrade g_trade;
int g_gbb_handle=INVALID_HANDLE;
int g_atr_handle=INVALID_HANDLE;
datetime g_last_bar_open=0;
datetime g_last_decision_time=0;
datetime g_entry_time=0;
datetime g_last_close_attempt_bar=0;
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
long g_risk_lock_skips=0;
long g_close_attempts=0;
long g_close_rejects=0;
long g_closes=0;
long g_invalid_inputs=0;
long g_volume_rejects=0;
long g_window_skips=0;

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
   const double bounded=MathMin(volume,vmax);
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

bool OwnedPosition(ulong &ticket)
  {
   ticket=0;
   int owned=0;
   for(int i=PositionsTotal()-1;i>=0;i--)
     {
      const ulong current=PositionGetTicket(i);
      if(current==0 || !PositionSelectByTicket(current))
         continue;
      if(PositionGetString(POSITION_SYMBOL)==_Symbol &&
         PositionGetInteger(POSITION_MAGIC)==InpMagic)
        {
         ticket=current;
         owned++;
        }
     }
   if(owned>1)
     {
      g_runtime_failed=true;
      return(false);
     }
   return(owned==1);
  }

bool AnySymbolExposure()
  {
   for(int i=PositionsTotal()-1;i>=0;i--)
     {
      const ulong ticket=PositionGetTicket(i);
      if(ticket>0 && PositionSelectByTicket(ticket) &&
         PositionGetString(POSITION_SYMBOL)==_Symbol)
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
   const int minute=p.hour*60+p.min;
   if(p.day_of_week==5 && minute>=InpFridayFlattenHour*60)
      return(false);
   return(minute<InpDailyFlatHour*60+InpDailyFlatMinute);
  }

bool CloseOwned(const string reason)
  {
   ulong ticket=0;
   if(!OwnedPosition(ticket))
      return(true);
   g_close_attempts++;
   g_pending_exit_reason=reason;
   g_trade.SetDeviationInPoints(InpDeviationPoints);
   if(!g_trade.PositionClose(ticket,InpDeviationPoints))
     {
      g_close_rejects++;
      PrintFormat("GBB001_CLOSE_REJECT reason=%s ticket=%I64u retcode=%u",
                  reason,ticket,g_trade.ResultRetcode());
      return(false);
     }
   const uint retcode=g_trade.ResultRetcode();
   if(retcode!=TRADE_RETCODE_DONE && retcode!=TRADE_RETCODE_DONE_PARTIAL)
     {
      g_close_rejects++;
      PrintFormat("GBB001_CLOSE_REJECT reason=%s ticket=%I64u retcode=%u",
                  reason,ticket,retcode);
      return(false);
     }
   g_closes++;
   PrintFormat("GBB001_CLOSE_REQUEST reason=%s ticket=%I64u retcode=%u",
               reason,ticket,retcode);
   return(true);
  }

void ManagePosition(const datetime server_now,const datetime current_bar_open)
  {
   ulong ticket=0;
   if(!OwnedPosition(ticket))
      return;
   MqlDateTime now_parts;
   TimeToStruct(server_now,now_parts);
   const int minute=now_parts.hour*60+now_parts.min;
   string exit_reason="";
   if(now_parts.day_of_week==5 && minute>=InpFridayFlattenHour*60)
      exit_reason="FRIDAY_FLAT";
   else if(minute>=InpDailyFlatHour*60+InpDailyFlatMinute)
      exit_reason="DAILY_FLAT";
   else
     {
      datetime entry_time=g_entry_time;
      if(entry_time<=0 && PositionSelectByTicket(ticket))
         entry_time=(datetime)PositionGetInteger(POSITION_TIME);
      if(entry_time>0)
        {
         const int held_bars=iBarShift(_Symbol,PERIOD_H1,entry_time,false);
         if(held_bars>=InpTimeStopBars)
            exit_reason="TIME_STOP";
        }
     }
   if(exit_reason=="" || g_last_close_attempt_bar==current_bar_open)
      return;
   g_last_close_attempt_bar=current_bar_open;
   CloseOwned(exit_reason);
  }

void ManageProtectiveExits()
  {
   ulong ticket=0;
   if(!OwnedPosition(ticket) || !PositionSelectByTicket(ticket))
      return;
   if(g_initial_sl<=0.0 && g_initial_tp<=0.0)
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
      CloseOwned(exit_reason);
  }

bool CopyClosed(const int handle,const int buffer,double &value)
  {
   double raw[];
   ArraySetAsSeries(raw,true);
   if(CopyBuffer(handle,buffer,1,1,raw)!=1)
      return(false);
   value=raw[0];
   return(IsFinite(value));
  }

bool BuildSignal(const datetime availability_time,SignalDecision &signal)
  {
   ZeroMemory(signal);
   if(g_gbb_handle==INVALID_HANDLE || g_atr_handle==INVALID_HANDLE)
      return(false);
   if(BarsCalculated(g_gbb_handle)<GBB_WARMUP_BARS ||
      BarsCalculated(g_atr_handle)<InpATRPeriod+2)
     {
      g_invalid_inputs++;
      return(false);
     }

   MqlRates rates[];
   ArraySetAsSeries(rates,true);
   if(CopyRates(_Symbol,PERIOD_H1,1,2,rates)!=2)
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

   double code=0.0,regime=0.0,upper=0.0,lower=0.0,atr=0.0;
   if(!CopyClosed(g_gbb_handle,GBB_SIGNAL_BUFFER,code) ||
      !CopyClosed(g_gbb_handle,GBB_REGIME_BUFFER,regime) ||
      !CopyClosed(g_gbb_handle,GBB_UPPER_BUFFER,upper) ||
      !CopyClosed(g_gbb_handle,GBB_LOWER_BUFFER,lower) ||
      !CopyClosed(g_atr_handle,0,atr) || atr<=0.0)
     {
      g_invalid_inputs++;
      return(false);
     }

   int direction=0;
   if(MathAbs(code-2.0)<1e-9 && MathAbs(regime-1.0)<1e-9)
      direction=1;
   else if(MathAbs(code+2.0)<1e-9 && MathAbs(regime-1.0)<1e-9)
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
   signal.upper=upper;
   signal.lower=lower;
   signal.signal_code=code;
   signal.regime=regime;
   g_signals++;
   if(direction>0) g_long_signals++; else g_short_signals++;
   if(InpEnableTelemetry)
      PrintFormat("GBB001_SIGNAL decision=%I64d dir=%s code=%.1f regime=%.1f c=%.5f atr=%.5f upper=%.5f lower=%.5f",
                  (long)bar.time,(direction>0 ? "LONG" : "SHORT"),code,regime,
                  bar.close,atr,upper,lower);
   return(true);
  }

bool SubmitEntry(const SignalDecision &signal)
  {
   if(!signal.fired || AnySymbolExposure())
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
      return(false);
   const double point=SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   const double tick_size=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);
   if(point<=0.0 || tick_size<=0.0)
      return(false);
   const double spread_points=(tick.ask-tick.bid)/point;
   if(!IsFinite(spread_points) || spread_points>InpMaxSpreadPoints)
     {
      g_spread_rejects++;
      return(false);
     }

   const double entry=(signal.direction>0 ? tick.ask : tick.bid);
   const double raw_stop=(signal.direction>0
                          ? MathMin(signal.signal_low,signal.lower)-InpSLATRBuffer*signal.atr
                          : MathMax(signal.signal_high,signal.upper)+InpSLATRBuffer*signal.atr);
   double risk_distance=(signal.direction>0 ? entry-raw_stop : raw_stop-entry);
   risk_distance=MathMax(InpMinSLATR*signal.atr,MathMin(risk_distance,InpMaxSLATR*signal.atr));
   if(!IsFinite(risk_distance) || risk_distance<=0.0)
      return(false);
   const double raw_sl=entry-signal.direction*risk_distance;
   const double raw_tp=entry+signal.direction*InpTargetR*risk_distance;
   const double sl=(signal.direction>0 ? FloorToTick(raw_sl,tick_size) : CeilToTick(raw_sl,tick_size));
   const double tp=(signal.direction>0 ? CeilToTick(raw_tp,tick_size) : FloorToTick(raw_tp,tick_size));
   const double minimum_distance=(double)MathMax(MathMax(SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL),
                                                         SymbolInfoInteger(_Symbol,SYMBOL_TRADE_FREEZE_LEVEL)),0)*point;
   if(MathAbs(entry-sl)<minimum_distance || MathAbs(tp-entry)<minimum_distance)
      return(false);

   const ENUM_ORDER_TYPE order_type=(signal.direction>0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL);
   double one_lot_loss=0.0;
   if(!OrderCalcProfit(order_type,_Symbol,1.0,entry,sl,one_lot_loss) ||
      !IsFinite(one_lot_loss) || one_lot_loss>=0.0)
      return(false);
   const double equity=AccountInfoDouble(ACCOUNT_EQUITY);
   double volume=NormalizeVolumeDown(equity*(InpRiskPercent/100.0)/MathAbs(one_lot_loss));
   if(volume<=0.0)
     {
      g_volume_rejects++;
      PrintFormat("GBB001_VOLUME_REJECT reason=RISK_LOT_ZERO equity=%.2f one_lot_loss=%.2f",
                  equity,one_lot_loss);
      return(false);
     }
   // MQ Demo margins at historical bid/ask (leverage 1:100). Do not floor
   // notional to a live-quote proxy: equity*0.50/(contract*5000) is exactly
   // volume_min at $10k, so one losing fill zeros every later signal.
   const double contract=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_CONTRACT_SIZE);
   const double hist_px=MathMax(entry,MathMax(SymbolInfoDouble(_Symbol,SYMBOL_BID),
                                              SymbolInfoDouble(_Symbol,SYMBOL_ASK)));
   if(!IsFinite(contract) || !IsFinite(hist_px) || contract<=0.0 || hist_px<=0.0)
      return(false);
   const double max_volume=NormalizeVolumeDown(equity*0.50/(contract*hist_px));
   if(max_volume<=0.0)
     {
      g_volume_rejects++;
      PrintFormat("GBB001_VOLUME_REJECT reason=NOTIONAL_CAP_ZERO equity=%.2f hist=%.5f contract=%.2f",
                  equity,hist_px,contract);
      return(false);
     }
   if(volume>max_volume)
     {
      PrintFormat("GBB001_VOLUME_CAP reason=HIST_NOTIONAL from=%.2f to=%.2f hist=%.5f contract=%.2f",
                  volume,max_volume,hist_px,contract);
      volume=max_volume;
     }
   double margin=0.0;
   if(!OrderCalcMargin(order_type,_Symbol,volume,entry,margin) || !IsFinite(margin) ||
      margin>AccountInfoDouble(ACCOUNT_MARGIN_FREE))
      return(false);

   g_trade.SetExpertMagicNumber(InpMagic);
   g_trade.SetDeviationInPoints(InpDeviationPoints);
   g_trade.SetTypeFillingBySymbol(_Symbol);
   // Broker SL/TP on FivePercent XAU Model-0 stop-outs the whole pass one
   // bar later (0.03 and 0.01 lots; comment so <margin_level>$). Same 1.5R
   // exits are enforced tick-by-tick in ManageProtectiveExits.
   const bool sent=g_trade.PositionOpen(_Symbol,order_type,volume,entry,0.0,0.0,InpVariantTag);
   const uint retcode=g_trade.ResultRetcode();
   if(!sent || (retcode!=TRADE_RETCODE_DONE && retcode!=TRADE_RETCODE_DONE_PARTIAL))
     {
      g_entry_rejects++;
      PrintFormat("GBB001_ENTRY_REJECT dir=%s vol=%.2f entry=%.5f sl=%.5f tp=%.5f retcode=%u",
                  (signal.direction>0 ? "LONG" : "SHORT"),volume,entry,sl,tp,retcode);
      return(false);
     }
   g_entries++;
   g_daily_entries++;
   g_entry_time=signal.availability_time;
   g_entry_price=(g_trade.ResultPrice()>0.0 ? g_trade.ResultPrice() : entry);
   g_initial_sl=sl;
   g_initial_tp=tp;
   PrintFormat("GBB001_ENTRY decision=%I64d dir=%s vol=%.2f entry=%.5f sl=%.5f tp=%.5f retcode=%u margin=%.2f level=%.2f",
               (long)signal.decision_time,(signal.direction>0 ? "LONG" : "SHORT"),
               volume,g_entry_price,sl,tp,retcode,
               AccountInfoDouble(ACCOUNT_MARGIN),AccountInfoDouble(ACCOUNT_MARGIN_LEVEL));
   return(true);
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
   PrintFormat("GBB001_EXIT deal=%I64u reason=%s profit=%.2f commission=%.2f swap=%.2f",
               trans.deal,ExitReasonName(HistoryDealGetInteger(trans.deal,DEAL_REASON)),
               HistoryDealGetDouble(trans.deal,DEAL_PROFIT),
               HistoryDealGetDouble(trans.deal,DEAL_COMMISSION),
               HistoryDealGetDouble(trans.deal,DEAL_SWAP));
   ulong owned=0;
   if(!OwnedPosition(owned))
     {
      g_entry_time=0;
      g_entry_price=0.0;
      g_initial_sl=0.0;
      g_initial_tp=0.0;
      g_pending_exit_reason="";
     }
  }

int OnInit()
  {
   if(_Period!=PERIOD_H1 || !SymbolAllowed() ||
      InpHypothesisId!=EXPECTED_HYPOTHESIS || InpVariantTag!=EXPECTED_VARIANT)
      return(INIT_PARAMETERS_INCORRECT);

   // Defaults are the frozen S2 math. An explicit iCustom list shifts under
   // input group/color on build 6090 and yields INIT_PARAMETERS_INCORRECT
   // (tester log flood → OOM → "some error after pass finished").
   g_gbb_handle=iCustom(_Symbol,PERIOD_H1,"Modern_Bollinger_Bands_GBB");
   g_atr_handle=iATR(_Symbol,PERIOD_H1,InpATRPeriod);
   if(g_gbb_handle==INVALID_HANDLE || g_atr_handle==INVALID_HANDLE)
     {
      Print("GBB001_FATAL reason=INDICATOR_HANDLE");
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
   PrintFormat("GBB001_INIT ea=%s hyp=%s symbol=%s tf=H1",EA_NAME,InpHypothesisId,_Symbol);
   return(INIT_SUCCEEDED);
  }

void OnDeinit(const int reason)
  {
   if(g_gbb_handle!=INVALID_HANDLE)
      IndicatorRelease(g_gbb_handle);
   if(g_atr_handle!=INVALID_HANDLE)
      IndicatorRelease(g_atr_handle);
   PrintFormat("GBB001_SUMMARY reason=%d failed=%s closed_bars=%I64d signals=%I64d long=%I64d short=%I64d entries=%I64d entry_rej=%I64d spread_rej=%I64d risk_skip=%I64d vol_rej=%I64d window_skip=%I64d closes=%I64d close_rej=%I64d invalid=%I64d",
               reason,(g_runtime_failed ? "true" : "false"),g_closed_bars,g_signals,
               g_long_signals,g_short_signals,g_entries,g_entry_rejects,g_spread_rejects,
               g_risk_lock_skips,g_volume_rejects,g_window_skips,g_closes,g_close_rejects,
               g_invalid_inputs);
  }

void OnTick()
  {
   datetime current_bar_open=0;
   if(!CurrentBarOpen(current_bar_open) || current_bar_open<=0)
      return;
   const datetime server_now=TimeCurrent();
   RefreshRiskLocks(server_now);
   ManageProtectiveExits();
   ManagePosition(server_now,current_bar_open);
   if(current_bar_open==g_last_bar_open)
      return;
   g_last_bar_open=current_bar_open;
   if(AnySymbolExposure() || g_runtime_failed)
      return;
   SignalDecision signal;
   if(BuildSignal(current_bar_open,signal) && signal.fired)
      SubmitEntry(signal);
  }
//+------------------------------------------------------------------+
