//+------------------------------------------------------------------+
//| EA_LondonAuction_GBP_M15_V5.mq5                                 |
//| HYP-LAR-GBPUSD-M15-001: overnight balance London auction retest  |
//+------------------------------------------------------------------+
#property strict
#property version "1.00"
#property description "Untuned closed-bar GBPUSD M15 London auction retest EA"
#include <Trade/Trade.mqh>

input group "--- Frozen authority ---"
input bool InpResearchAutoMode=false;
input bool InpEnableTelemetry=true;
input string InpHypothesisId="HYP-LAR-GBPUSD-M15-001";
input string InpVariantTag="RETEST_PRIMARY";
input bool InpRequireRetest=true;

input group "--- Frozen auction clock and signal ---"
input int InpBalanceStartHour=0;
input int InpBalanceEndHour=7;
input int InpBalanceEndMinute=45;
input int InpAuctionStartHour=8;
input int InpAuctionEndHour=11;
input int InpAuctionEndMinute=30;
input double InpMinBalancePips=18.0;
input double InpMaxBalancePips=55.0;
input double InpBreakBufferPips=3.0;
input double InpRetestZonePips=4.0;
input int InpMaxBarsBreakToRetest=6;
input double InpResumptionBodyMin=0.40;

input group "--- Frozen exits and risk ---"
input double InpSLExtraPips=4.0;
input double InpMinSLPips=12.0;
input double InpMaxSLPips=38.0;
input double InpBETriggerR=1.00;
input double InpBEOffsetPips=1.50;
input double InpTrailStartR=1.70;
input double InpTrailPips=9.0;
input int InpTimeStopBars=16;
input double InpRiskPercent=0.25;
input double InpMaxNotionalMult=3.00;
input double InpMaxMarginUsagePct=10.0;
input int InpMaxSpreadPoints=22;
input double InpDailyLossPct=1.00;
input double InpWeeklyLossPct=2.50;
input int InpDailyFlatHour=21;
input int InpDailyFlatMinute=40;
input int InpFridayFlatHour=18;
input int InpFridayFlatMinute=40;
input int InpDeviationPoints=8;
input long InpMagic=5605101;

const string EA_NAME="EA_LondonAuction_GBP_M15_V5";
const string EXPECTED_HYPOTHESIS="HYP-LAR-GBPUSD-M15-001";
const string PRIMARY_VARIANT="RETEST_PRIMARY";
const string CONTROL_VARIANT="DIRECT_BREAK_CONTROL";

enum AuctionState { WAITING_BALANCE=0, BALANCE_READY=1, BREAK_CONFIRMED=2, RETEST_TOUCHED=3, IN_POSITION=4, DAY_DONE=5 };

struct EntrySignal
  {
   bool fired; datetime decision_time; datetime availability_time; int direction; int break_age;
   double signal_open,signal_high,signal_low,signal_close,body_ratio;
   double balance_high,balance_low,balance_range_pips,break_level;
  };

CTrade g_trade;
AuctionState g_state=WAITING_BALANCE;
datetime g_last_bar_open=0,g_last_decision_time=0,g_break_time=0,g_retest_time=0,g_entry_time=0,g_last_close_attempt_bar=0;
int g_active_day=0,g_break_direction=0,g_break_age=0;
double g_balance_high=0.0,g_balance_low=0.0,g_break_level=0.0;
int g_balance_bars=0,g_entries_today=0;
double g_entry_price=0.0,g_initial_sl=0.0,g_initial_risk=0.0,g_mfe_points=0.0,g_mae_points=0.0,g_entry_margin_usage_pct=0.0;
bool g_trail_armed=false,g_day_locked=false,g_week_locked=false,g_runtime_failed=false;
string g_pending_exit_reason="";
int g_day_key=0; long g_week_key=0; double g_day_start_equity=0.0,g_week_start_equity=0.0;

long g_closed_bars=0,g_valid_balances=0,g_invalid_balances=0,g_breaks=0,g_retests=0,g_signals=0,g_long_signals=0,g_short_signals=0;
long g_day_latch_skips=0,g_spread_rejects=0,g_risk_lock_skips=0,g_entries=0,g_entry_rejects=0,g_be_moves=0,g_trail_arms=0,g_trail_moves=0;
long g_close_attempts=0,g_close_rejects=0,g_closes=0,g_invalid_inputs=0;

bool IsFinite(const double v) { return(v!=EMPTY_VALUE && MathIsValidNumber(v)); }
int DayKey(const datetime t) { MqlDateTime p; TimeToStruct(t,p); return(p.year*10000+p.mon*100+p.day); }
long WeekKey(const datetime t) { MqlDateTime p;TimeToStruct(t,p);datetime s=t-p.hour*3600-p.min*60-p.sec;return((long)(s-((p.day_of_week+6)%7)*86400)/604800); }
int MinuteOfDay(const datetime t) { MqlDateTime p;TimeToStruct(t,p);return(p.hour*60+p.min); }
double PipSize() { const int digits=(int)SymbolInfoInteger(_Symbol,SYMBOL_DIGITS);const double point=SymbolInfoDouble(_Symbol,SYMBOL_POINT);return((digits==3 || digits==5)?10.0*point:point); }

bool CurrentBarOpen(datetime &bar_open)
  {
   long raw=0;bar_open=0;if(!SeriesInfoInteger(_Symbol,PERIOD_M15,SERIES_LASTBAR_DATE,raw)||raw<=0)return(false);bar_open=(datetime)raw;return(true);
  }

bool EmitSeriesProof()
  {
   long sync=0,m5first=0,m5terminal=0,m1server=0,m1terminal=0,bars=0;
   if(!SeriesInfoInteger(_Symbol,PERIOD_M5,SERIES_SYNCHRONIZED,sync)||!SeriesInfoInteger(_Symbol,PERIOD_M5,SERIES_FIRSTDATE,m5first)||
      !SeriesInfoInteger(_Symbol,PERIOD_M5,SERIES_TERMINAL_FIRSTDATE,m5terminal)||!SeriesInfoInteger(_Symbol,PERIOD_M1,SERIES_SERVER_FIRSTDATE,m1server)||
      !SeriesInfoInteger(_Symbol,PERIOD_M1,SERIES_TERMINAL_FIRSTDATE,m1terminal)||!SeriesInfoInteger(_Symbol,PERIOD_M5,SERIES_BARS_COUNT,bars))return(false);
   ResetLastError();const long maxbars=TerminalInfoInteger(TERMINAL_MAXBARS);const int terr=GetLastError();datetime a[];ArraySetAsSeries(a,false);
   ResetLastError();const int n=CopyTime(_Symbol,PERIOD_M5,(datetime)m5first,1,a);const int err=GetLastError();const long first=(n==1?(long)a[0]:0);
   PrintFormat("DATA_EPOCH_D0_SERIES_PROOF symbol=%s m5_synchronized=%I64d m5_first_epoch=%I64d m5_terminal_first_epoch=%I64d m1_server_first_epoch=%I64d m1_terminal_first_epoch=%I64d m5_bars=%I64d terminal_maxbars=%I64d copytime_from_epoch=%I64d copytime_count=1 copytime_result=%d copytime_first_epoch=%I64d copytime_last_error=%d",_Symbol,sync,m5first,m5terminal,m1server,m1terminal,bars,maxbars,m5first,n,first,err);
   return(sync==1&&m5first>0&&m5terminal>0&&m1server>0&&m1terminal>0&&bars>0&&maxbars>0&&terr==0&&n==1&&first==m5first&&err==0);
  }

bool LoadClosedBar(MqlRates &bar)
  {
   MqlRates rates[];ArraySetAsSeries(rates,true);if(CopyRates(_Symbol,PERIOD_M15,1,1,rates)!=1)return(false);
   bar=rates[0];return(bar.time>0&&bar.high>bar.low&&bar.open>0.0&&bar.close>0.0&&bar.tick_volume>0);
  }

void ResetAuctionDay(const datetime current_bar_open)
  {
   g_active_day=DayKey(current_bar_open);g_state=WAITING_BALANCE;g_balance_high=-DBL_MAX;g_balance_low=DBL_MAX;g_balance_bars=0;
   g_break_direction=0;g_break_time=0;g_retest_time=0;g_break_age=0;g_break_level=0.0;g_entries_today=0;
   if(InpEnableTelemetry)PrintFormat("LAR001_DAY_RESET day=%d time=%I64d",g_active_day,(long)current_bar_open);
  }

void LatchDay(const string reason)
  {
   if(g_state!=DAY_DONE&&InpEnableTelemetry)PrintFormat("LAR001_STATE from=%d to=5 reason=%s day=%d entries_today=%d",(int)g_state,reason,g_active_day,g_entries_today);
   g_state=DAY_DONE;
  }

void AccumulateOrFinalizeBalance(const MqlRates &bar,const datetime availability)
  {
   if(g_state!=WAITING_BALANCE)return;
   const int open_minute=MinuteOfDay(bar.time);const int end_minute=InpBalanceEndHour*60+InpBalanceEndMinute;
   if(open_minute>=InpBalanceStartHour*60&&open_minute<end_minute)
     {g_balance_high=MathMax(g_balance_high,bar.high);g_balance_low=MathMin(g_balance_low,bar.low);g_balance_bars++;}
   if(MinuteOfDay(availability)<end_minute)return;
   const double pip=PipSize();const double range=(g_balance_bars>0&&pip>0.0?(g_balance_high-g_balance_low)/pip:0.0);
   if(g_balance_bars<1||range<InpMinBalancePips||range>InpMaxBalancePips)
     {g_invalid_balances++;if(InpEnableTelemetry)PrintFormat("LAR001_BALANCE day=%d valid=false bars=%d high=%.5f low=%.5f range_pips=%.2f",g_active_day,g_balance_bars,g_balance_high,g_balance_low,range);LatchDay("INVALID_BALANCE");return;}
   g_state=BALANCE_READY;g_valid_balances++;
   if(InpEnableTelemetry)PrintFormat("LAR001_BALANCE day=%d valid=true bars=%d high=%.5f low=%.5f range_pips=%.2f",g_active_day,g_balance_bars,g_balance_high,g_balance_low,range);
  }

bool BuildSignal(const datetime availability,EntrySignal &signal)
  {
   ZeroMemory(signal);MqlRates bar;if(!LoadClosedBar(bar)){g_invalid_inputs++;return(false);}
   if(bar.time<=0||bar.time==g_last_decision_time)return(false);g_last_decision_time=bar.time;g_closed_bars++;
   if((long)(availability-bar.time)!=PeriodSeconds(PERIOD_M15)){g_invalid_inputs++;return(false);}
   if(DayKey(availability)!=g_active_day)ResetAuctionDay(availability);
   AccumulateOrFinalizeBalance(bar,availability);
   const int minute=MinuteOfDay(availability),start=InpAuctionStartHour*60,end=InpAuctionEndHour*60+InpAuctionEndMinute;
   if(minute<start)return(false);
   if(minute>end){if(g_state!=IN_POSITION)LatchDay("AUCTION_END");return(false);}
   if(g_state==DAY_DONE||g_state==WAITING_BALANCE||g_state==IN_POSITION)return(false);
   const double pip=PipSize();if(pip<=0.0){g_invalid_inputs++;return(false);}

   if(g_state==BALANCE_READY)
     {
      int direction=0;if(bar.close>g_balance_high+InpBreakBufferPips*pip)direction=1;else if(bar.close<g_balance_low-InpBreakBufferPips*pip)direction=-1;
      if(direction==0)return(false);g_break_direction=direction;g_break_level=(direction>0?g_balance_high:g_balance_low);g_break_time=bar.time;g_break_age=0;g_breaks++;
      if(!InpRequireRetest)
        {g_state=RETEST_TOUCHED;g_retest_time=bar.time-PeriodSeconds(PERIOD_M15);}
      else g_state=BREAK_CONFIRMED;
      if(InpEnableTelemetry)PrintFormat("LAR001_BREAK day=%d time=%I64d direction=%s level=%.5f close=%.5f balance_high=%.5f balance_low=%.5f",g_active_day,(long)bar.time,(direction>0?"LONG":"SHORT"),g_break_level,bar.close,g_balance_high,g_balance_low);
      if(InpRequireRetest)return(false);
     }
   else if((g_state==BREAK_CONFIRMED||g_state==RETEST_TOUCHED)&&bar.time>g_break_time)g_break_age++;

   if((g_state==BREAK_CONFIRMED||g_state==RETEST_TOUCHED)&&g_break_age>InpMaxBarsBreakToRetest){LatchDay("RETEST_EXPIRY");return(false);}
   if(g_state==BREAK_CONFIRMED)
     {
      const bool touched=(g_break_direction>0?bar.low<=g_break_level+InpRetestZonePips*pip:bar.high>=g_break_level-InpRetestZonePips*pip);
      if(!touched)return(false);g_state=RETEST_TOUCHED;g_retest_time=bar.time;g_retests++;
      if(InpEnableTelemetry)PrintFormat("LAR001_RETEST day=%d time=%I64d direction=%s age=%d level=%.5f h=%.5f l=%.5f",g_active_day,(long)bar.time,(g_break_direction>0?"LONG":"SHORT"),g_break_age,g_break_level,bar.high,bar.low);
      return(false);
     }
   if(g_state!=RETEST_TOUCHED||bar.time<=g_retest_time)return(false);
   const double range=bar.high-bar.low;if(range<=0.0)return(false);const double body_ratio=MathAbs(bar.close-bar.open)/range;
   const bool resumes=(g_break_direction>0?bar.close>bar.open:bar.close<bar.open);
   if(!resumes||body_ratio<InpResumptionBodyMin)return(false);
   signal.fired=true;signal.decision_time=bar.time;signal.availability_time=availability;signal.direction=g_break_direction;signal.break_age=g_break_age;
   signal.signal_open=bar.open;signal.signal_high=bar.high;signal.signal_low=bar.low;signal.signal_close=bar.close;signal.body_ratio=body_ratio;
   signal.balance_high=g_balance_high;signal.balance_low=g_balance_low;signal.balance_range_pips=(g_balance_high-g_balance_low)/pip;signal.break_level=g_break_level;
   g_signals++;if(signal.direction>0)g_long_signals++;else g_short_signals++;
   if(InpEnableTelemetry)PrintFormat("LAR001_SIGNAL decision=%I64d availability=%I64d direction=%s age=%d body_ratio=%.6f balance_high=%.5f balance_low=%.5f break_level=%.5f",(long)bar.time,(long)availability,(signal.direction>0?"LONG":"SHORT"),g_break_age,body_ratio,g_balance_high,g_balance_low,g_break_level);
   return(true);
  }

int VolumeDigits(const double s){int d=0;double v=s;while(d<8&&MathAbs(v-MathRound(v))>1e-9){v*=10.0;d++;}return(d);}
double NormalizeVolumeDown(const double v){double mn=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN),mx=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX),st=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);if(mn<=0||mx<mn||st<=0||v<mn)return(0);double u=MathFloor((MathMin(v,mx)-mn+1e-12)/st);return(NormalizeDouble(mn+u*st,VolumeDigits(st)));}
double FloorToTick(const double p,const double t){return(MathFloor(p/t+1e-10)*t);} double CeilToTick(const double p,const double t){return(MathCeil(p/t-1e-10)*t);}

bool OwnedPosition(ulong &ticket){ticket=0;int n=0;for(int i=PositionsTotal()-1;i>=0;i--){ulong x=PositionGetTicket(i);if(x>0&&PositionSelectByTicket(x)&&PositionGetString(POSITION_SYMBOL)==_Symbol&&PositionGetInteger(POSITION_MAGIC)==InpMagic){ticket=x;n++;}}if(n>1)g_runtime_failed=true;return(n==1);}
bool AnySymbolExposure(){for(int i=PositionsTotal()-1;i>=0;i--){ulong x=PositionGetTicket(i);if(x>0&&PositionSelectByTicket(x)&&PositionGetString(POSITION_SYMBOL)==_Symbol)return(true);}return(false);}

void RefreshRiskLocks(const datetime now){double e=AccountInfoDouble(ACCOUNT_EQUITY);int d=DayKey(now);long w=WeekKey(now);if(d!=g_day_key){g_day_key=d;g_day_start_equity=e;g_day_locked=false;}if(w!=g_week_key){g_week_key=w;g_week_start_equity=e;g_week_locked=false;}if(g_day_start_equity>0&&e<=g_day_start_equity*(1-InpDailyLossPct/100.0))g_day_locked=true;if(g_week_start_equity>0&&e<=g_week_start_equity*(1-InpWeeklyLossPct/100.0))g_week_locked=true;}

bool CloseOwned(const string reason){ulong t=0;if(!OwnedPosition(t))return(true);g_close_attempts++;g_pending_exit_reason=reason;if(!g_trade.PositionClose(t,InpDeviationPoints)){g_close_rejects++;return(false);}uint c=g_trade.ResultRetcode();if(c!=TRADE_RETCODE_DONE&&c!=TRADE_RETCODE_DONE_PARTIAL){g_close_rejects++;return(false);}g_closes++;PrintFormat("LAR001_CLOSE_REQUEST reason=%s ticket=%I64u",reason,t);return(true);}

bool ModifyStop(const ulong ticket,const double proposed,const string reason)
  {
   if(!PositionSelectByTicket(ticket))return(false);bool is_long=((ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_BUY);double current=PositionGetDouble(POSITION_SL);MqlTick q;if(!SymbolInfoTick(_Symbol,q))return(false);
   double point=SymbolInfoDouble(_Symbol,SYMBOL_POINT),tick=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);if(point<=0||tick<=0)return(false);double next=(is_long?FloorToTick(proposed,tick):CeilToTick(proposed,tick));
   if((is_long&&current>=next-point*.1)||(!is_long&&current>0&&current<=next+point*.1))return(false);double md=(double)MathMax(MathMax(SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL),SymbolInfoInteger(_Symbol,SYMBOL_TRADE_FREEZE_LEVEL)),0)*point;
   if((is_long&&q.bid-next<md)||(!is_long&&next-q.ask<md))return(false);if(!g_trade.PositionModify(ticket,next,0.0))return(false);uint c=g_trade.ResultRetcode();if(c!=TRADE_RETCODE_DONE&&c!=TRADE_RETCODE_NO_CHANGES)return(false);
   PrintFormat("LAR001_STOP_MOVE reason=%s ticket=%I64u sl=%.5f mfe_points=%.1f mae_points=%.1f",reason,ticket,next,g_mfe_points,g_mae_points);return(true);
  }

void UpdateStops(const ulong ticket)
  {
   if(!PositionSelectByTicket(ticket)||g_initial_risk<=0||g_entry_price<=0)return;bool is_long=((ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_BUY);MqlTick q;if(!SymbolInfoTick(_Symbol,q))return;
   double point=SymbolInfoDouble(_Symbol,SYMBOL_POINT),pip=PipSize();if(point<=0||pip<=0)return;double quote=(is_long?q.bid:q.ask),fav=(is_long?quote-g_entry_price:g_entry_price-quote);
   g_mfe_points=MathMax(g_mfe_points,MathMax(0.0,fav)/point);g_mae_points=MathMax(g_mae_points,MathMax(0.0,-fav)/point);
   if(fav>=InpBETriggerR*g_initial_risk){double be=(is_long?g_entry_price+InpBEOffsetPips*pip:g_entry_price-InpBEOffsetPips*pip);if(ModifyStop(ticket,be,"BREAKEVEN_PLUS"))g_be_moves++;}
   if(!g_trail_armed&&fav>=InpTrailStartR*g_initial_risk){g_trail_armed=true;g_trail_arms++;}
   if(g_trail_armed){double trail=(is_long?q.bid-InpTrailPips*pip:q.ask+InpTrailPips*pip);if(ModifyStop(ticket,trail,"FIXED_TRAIL"))g_trail_moves++;}
  }

void ManagePosition(const datetime now,const datetime bar_open)
  {
   ulong t=0;if(!OwnedPosition(t))return;g_state=IN_POSITION;UpdateStops(t);MqlDateTime p;TimeToStruct(now,p);int m=p.hour*60+p.min;string r="";
   if(p.day_of_week==5&&m>=InpFridayFlatHour*60+InpFridayFlatMinute)r="FRIDAY_FLAT";else if(m>=InpDailyFlatHour*60+InpDailyFlatMinute)r="DAILY_FLAT";else{datetime s=g_entry_time;if(s<=0&&PositionSelectByTicket(t))s=(datetime)PositionGetInteger(POSITION_TIME);if(s>0&&iBarShift(_Symbol,PERIOD_M15,s,false)>=InpTimeStopBars)r="TIME_STOP";}
   if(r==""||g_last_close_attempt_bar==bar_open)return;g_last_close_attempt_bar=bar_open;CloseOwned(r);
  }

bool EntryWindowOpen(const datetime t){MqlDateTime p;TimeToStruct(t,p);if(p.day_of_week==0||p.day_of_week==6)return(false);int m=p.hour*60+p.min;return(m>=InpAuctionStartHour*60&&m<=InpAuctionEndHour*60+InpAuctionEndMinute&&!(p.day_of_week==5&&m>=InpFridayFlatHour*60+InpFridayFlatMinute));}

bool SubmitEntry(const EntrySignal &s)
  {
   if(!s.fired||AnySymbolExposure()||!EntryWindowOpen(s.availability_time)||g_entries_today>0){g_day_latch_skips++;return(false);}if(g_day_locked||g_week_locked){g_risk_lock_skips++;return(false);}MqlTick q;if(!SymbolInfoTick(_Symbol,q)||q.ask<=q.bid)return(false);
   double point=SymbolInfoDouble(_Symbol,SYMBOL_POINT),pip=PipSize(),tick=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE),contract=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_CONTRACT_SIZE);if(point<=0||pip<=0||tick<=0||contract<=0)return(false);
   double spread=(q.ask-q.bid)/point;if(spread>InpMaxSpreadPoints){g_spread_rejects++;return(false);}double entry=(s.direction>0?q.ask:q.bid),structural=(s.direction>0?s.balance_low-InpSLExtraPips*pip:s.balance_high+InpSLExtraPips*pip);
   double dist=(s.direction>0?entry-structural:structural-entry);dist=MathMax(InpMinSLPips*pip,MathMin(dist,InpMaxSLPips*pip));if(dist<=0)return(false);double sl=(s.direction>0?FloorToTick(entry-dist,tick):CeilToTick(entry+dist,tick));
   ENUM_ORDER_TYPE type=(s.direction>0?ORDER_TYPE_BUY:ORDER_TYPE_SELL);double loss=0,margin1=0;if(!OrderCalcProfit(type,_Symbol,1,entry,sl,loss)||loss>=0)return(false);if(!OrderCalcMargin(type,_Symbol,1,entry,margin1)||margin1<=0)return(false);
   double eq=AccountInfoDouble(ACCOUNT_EQUITY),free=AccountInfoDouble(ACCOUNT_MARGIN_FREE);double vr=eq*(InpRiskPercent/100.0)/MathAbs(loss),vn=(eq*InpMaxNotionalMult)/(entry*contract),vm=(free*(InpMaxMarginUsagePct/100.0))/margin1;
   double volume=NormalizeVolumeDown(MathMin(vr,MathMin(vn,vm)));if(volume<=0)return(false);double margin=0;if(!OrderCalcMargin(type,_Symbol,volume,entry,margin))return(false);double notional=volume*entry*contract;if(margin>free*InpMaxMarginUsagePct/100.0+.01||notional>eq*InpMaxNotionalMult+.01)return(false);
   g_trade.SetExpertMagicNumber(InpMagic);g_trade.SetDeviationInPoints(InpDeviationPoints);g_trade.SetTypeFillingBySymbol(_Symbol);bool sent=g_trade.PositionOpen(_Symbol,type,volume,entry,sl,0.0,InpVariantTag);uint c=g_trade.ResultRetcode();
   if(!sent||(c!=TRADE_RETCODE_DONE&&c!=TRADE_RETCODE_DONE_PARTIAL)){g_entry_rejects++;return(false);}g_entries++;g_entries_today++;g_state=IN_POSITION;g_entry_time=s.availability_time;g_entry_price=(g_trade.ResultPrice()>0?g_trade.ResultPrice():entry);g_initial_sl=sl;g_initial_risk=MathAbs(g_entry_price-sl);g_entry_margin_usage_pct=100*margin/free;g_mfe_points=0;g_mae_points=0;g_trail_armed=false;g_pending_exit_reason="";
   PrintFormat("LAR001_ENTRY decision=%I64d day=%d direction=%s volume=%.2f entry=%.5f sl=%.5f tp=0 risk=%.5f balance_range_pips=%.2f spread_points=%.1f volume_risk=%.4f volume_notional=%.4f volume_margin=%.4f notional_mult=%.4f margin_usage_pct=%.4f",(long)s.decision_time,g_active_day,(s.direction>0?"LONG":"SHORT"),volume,g_entry_price,sl,g_initial_risk,s.balance_range_pips,spread,vr,vn,vm,notional/eq,g_entry_margin_usage_pct);return(true);
  }

string ExitReasonName(const long r){if(r==DEAL_REASON_SL)return("SL");if(r==DEAL_REASON_TP)return("TP_UNEXPECTED");if(r==DEAL_REASON_EXPERT&&g_pending_exit_reason!="")return(g_pending_exit_reason);return(StringFormat("DEAL_REASON_%d",(int)r));}
void OnTradeTransaction(const MqlTradeTransaction &tr,const MqlTradeRequest &rq,const MqlTradeResult &rs)
  {
   if(tr.type!=TRADE_TRANSACTION_DEAL_ADD||tr.deal==0||!HistoryDealSelect(tr.deal))return;if(HistoryDealGetString(tr.deal,DEAL_SYMBOL)!=_Symbol||HistoryDealGetInteger(tr.deal,DEAL_MAGIC)!=InpMagic)return;long k=HistoryDealGetInteger(tr.deal,DEAL_ENTRY);if(k!=DEAL_ENTRY_OUT&&k!=DEAL_ENTRY_OUT_BY)return;
   long reason=HistoryDealGetInteger(tr.deal,DEAL_REASON);double price=HistoryDealGetDouble(tr.deal,DEAL_PRICE),profit=HistoryDealGetDouble(tr.deal,DEAL_PROFIT),com=HistoryDealGetDouble(tr.deal,DEAL_COMMISSION),swap=HistoryDealGetDouble(tr.deal,DEAL_SWAP);datetime t=(datetime)HistoryDealGetInteger(tr.deal,DEAL_TIME);
   PrintFormat("LAR001_EXIT time=%I64d reason=%s price=%.5f profit=%.2f commission=%.2f swap=%.2f net=%.2f mfe_points=%.1f mae_points=%.1f margin_usage_pct=%.4f bars_held=%d",(long)t,ExitReasonName(reason),price,profit,com,swap,profit+com+swap,g_mfe_points,g_mae_points,g_entry_margin_usage_pct,(g_entry_time>0?iBarShift(_Symbol,PERIOD_M15,g_entry_time,false):-1));
   ulong ticket=0;if(!OwnedPosition(ticket)){g_entry_time=0;g_entry_price=0;g_initial_sl=0;g_initial_risk=0;g_entry_margin_usage_pct=0;g_trail_armed=false;g_pending_exit_reason="";LatchDay("POSITION_CLOSED");}
  }

bool InputsAreFrozen()
  {
   bool variant=((InpVariantTag==PRIMARY_VARIANT&&InpRequireRetest)||(InpVariantTag==CONTROL_VARIANT&&!InpRequireRetest));
   return(InpResearchAutoMode&&InpEnableTelemetry&&InpHypothesisId==EXPECTED_HYPOTHESIS&&variant&&InpBalanceStartHour==0&&InpBalanceEndHour==7&&InpBalanceEndMinute==45&&InpAuctionStartHour==8&&InpAuctionEndHour==11&&InpAuctionEndMinute==30&&MathAbs(InpMinBalancePips-18)<1e-12&&MathAbs(InpMaxBalancePips-55)<1e-12&&MathAbs(InpBreakBufferPips-3)<1e-12&&MathAbs(InpRetestZonePips-4)<1e-12&&InpMaxBarsBreakToRetest==6&&MathAbs(InpResumptionBodyMin-.40)<1e-12&&MathAbs(InpSLExtraPips-4)<1e-12&&MathAbs(InpMinSLPips-12)<1e-12&&MathAbs(InpMaxSLPips-38)<1e-12&&MathAbs(InpBETriggerR-1)<1e-12&&MathAbs(InpBEOffsetPips-1.5)<1e-12&&MathAbs(InpTrailStartR-1.7)<1e-12&&MathAbs(InpTrailPips-9)<1e-12&&InpTimeStopBars==16&&MathAbs(InpRiskPercent-.25)<1e-12&&MathAbs(InpMaxNotionalMult-3)<1e-12&&MathAbs(InpMaxMarginUsagePct-10)<1e-12&&InpMaxSpreadPoints==22&&MathAbs(InpDailyLossPct-1)<1e-12&&MathAbs(InpWeeklyLossPct-2.5)<1e-12&&InpDailyFlatHour==21&&InpDailyFlatMinute==40&&InpFridayFlatHour==18&&InpFridayFlatMinute==40&&InpDeviationPoints==8&&InpMagic==5605101);
  }

int OnInit(){if(_Period!=PERIOD_M15||!InputsAreFrozen())return(INIT_PARAMETERS_INCORRECT);if(!EmitSeriesProof())return(INIT_FAILED);g_trade.SetExpertMagicNumber(InpMagic);g_trade.SetDeviationInPoints(InpDeviationPoints);g_trade.SetTypeFillingBySymbol(_Symbol);datetime now=TimeCurrent();double e=AccountInfoDouble(ACCOUNT_EQUITY);g_day_key=DayKey(now);g_week_key=WeekKey(now);g_day_start_equity=e;g_week_start_equity=e;if(!CurrentBarOpen(g_last_bar_open))return(INIT_FAILED);ResetAuctionDay(g_last_bar_open);PrintFormat("LAR001_INIT ea=%s hypothesis=%s variant=%s symbol=%s timeframe=M15 retest=%s",EA_NAME,InpHypothesisId,InpVariantTag,_Symbol,(InpRequireRetest?"true":"false"));return(INIT_SUCCEEDED);}
void OnDeinit(const int reason){PrintFormat("LAR001_SUMMARY reason=%d runtime_failed=%s closed_bars=%I64d valid_balances=%I64d invalid_balances=%I64d breaks=%I64d retests=%I64d signals=%I64d long=%I64d short=%I64d day_latch_skips=%I64d spread_rejects=%I64d risk_lock_skips=%I64d entries=%I64d entry_rejects=%I64d be_moves=%I64d trail_arms=%I64d trail_moves=%I64d close_attempts=%I64d close_rejects=%I64d closes=%I64d invalid=%I64d",reason,(g_runtime_failed?"true":"false"),g_closed_bars,g_valid_balances,g_invalid_balances,g_breaks,g_retests,g_signals,g_long_signals,g_short_signals,g_day_latch_skips,g_spread_rejects,g_risk_lock_skips,g_entries,g_entry_rejects,g_be_moves,g_trail_arms,g_trail_moves,g_close_attempts,g_close_rejects,g_closes,g_invalid_inputs);}
void OnTick(){datetime bar=0;if(!CurrentBarOpen(bar))return;datetime now=TimeCurrent();RefreshRiskLocks(now);ManagePosition(now,bar);if(bar==g_last_bar_open)return;g_last_bar_open=bar;if(AnySymbolExposure())return;EntrySignal s;if(BuildSignal(bar,s)&&s.fired){bool entered=SubmitEntry(s);if(!entered)LatchDay("SIGNAL_CANCELLED_OR_REJECTED");}}
