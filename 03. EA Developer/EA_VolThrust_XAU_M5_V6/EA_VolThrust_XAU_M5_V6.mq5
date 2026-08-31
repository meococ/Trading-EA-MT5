//+------------------------------------------------------------------+
//| EA_VolThrust_XAU_M5_V6.mq5                                     |
//| HYP-VTC-XAUUSD-M5-001: volume thrust, pause, continuation       |
//+------------------------------------------------------------------+
#property strict
#property version "1.00"
#property description "Untuned closed-bar XAUUSD M5 volume-thrust continuation EA"
#include <Trade/Trade.mqh>

input group "--- Frozen authority ---"
input bool InpResearchAutoMode=false;
input bool InpEnableTelemetry=true;
input string InpHypothesisId="HYP-VTC-XAUUSD-M5-001";
input string InpVariantTag="PAUSE_PRIMARY";
input bool InpRequirePause=true;

input group "--- Frozen signal ---"
input int InpATRPeriod=14;
input int InpVolSMAPeriod=20;
input double InpThrustBodyMin=0.62;
input double InpThrustRangeATRMin=1.25;
input double InpThrustVolMult=1.70;
input int InpMaxBarsThrustToPause=4;
input double InpPauseBodyMax=0.45;
input double InpPauseBeyondATR=0.25;

input group "--- Frozen exits and risk ---"
input double InpSLBufferATR=0.35;
input double InpMinSLATR=1.15;
input double InpMaxSLATR=2.50;
input double InpBETriggerR=0.90;
input double InpBEOffsetR=0.15;
input double InpTrailStartR=1.60;
input double InpTrailATRMult=0.80;
input int InpTimeStopBars=24;
input double InpRiskPercent=0.25;
input double InpMaxNotionalMult=3.50;
input double InpMaxMarginUsagePct=10.0;
input int InpMaxSpreadPoints=45;
input double InpDailyLossPct=1.00;
input double InpWeeklyLossPct=2.50;
input int InpDailyFlatHour=21;
input int InpDailyFlatMinute=45;
input int InpFridayFlatHour=18;
input int InpFridayFlatMinute=45;
input int InpDeviationPoints=14;
input long InpMagic=5605201;

const string EA_NAME="EA_VolThrust_XAU_M5_V6";
const string EXPECTED_HYPOTHESIS="HYP-VTC-XAUUSD-M5-001";
const string PRIMARY_VARIANT="PAUSE_PRIMARY";
const string CONTROL_VARIANT="DIRECT_THRUST_CONTROL";

enum SignalState { NEUTRAL=0, THRUST_DETECTED=1, IN_POSITION=2 };

struct EntrySignal
  {
   bool fired;
   datetime decision_time,availability_time,thrust_time,pause_time;
   int direction,age;
   double thrust_high,thrust_low,thrust_atr,thrust_body_ratio,thrust_range_atr,thrust_vol_ratio;
   double pause_body_ratio,pause_open,pause_high,pause_low,pause_close;
  };

CTrade g_trade;
SignalState g_state=NEUTRAL;
datetime g_last_bar_open=0,g_last_decision_time=0,g_thrust_time=0,g_entry_time=0,g_last_close_attempt_bar=0;
int g_thrust_direction=0,g_thrust_age=0;
double g_thrust_high=0.0,g_thrust_low=0.0,g_thrust_atr=0.0,g_thrust_body_ratio=0.0,g_thrust_range_atr=0.0,g_thrust_vol_ratio=0.0;
double g_entry_price=0.0,g_initial_sl=0.0,g_initial_risk=0.0,g_mfe_points=0.0,g_mae_points=0.0,g_entry_margin_usage_pct=0.0;
bool g_trail_armed=false,g_day_locked=false,g_week_locked=false,g_runtime_failed=false;
string g_pending_exit_reason="";
int g_day_key=0;
long g_week_key=0;
double g_day_start_equity=0.0,g_week_start_equity=0.0;

long g_closed_bars=0,g_thrusts=0,g_pauses=0,g_expiries=0,g_signals=0,g_long_signals=0,g_short_signals=0;
long g_missing_volume=0,g_spread_rejects=0,g_risk_lock_skips=0,g_exposure_skips=0,g_entries=0,g_entry_rejects=0;
long g_be_moves=0,g_trail_arms=0,g_trail_moves=0,g_close_attempts=0,g_close_rejects=0,g_closes=0,g_invalid_inputs=0;

bool IsFinite(const double v){return(v!=EMPTY_VALUE&&MathIsValidNumber(v));}
int DayKey(const datetime t){MqlDateTime p;TimeToStruct(t,p);return(p.year*10000+p.mon*100+p.day);}
long WeekKey(const datetime t){MqlDateTime p;TimeToStruct(t,p);datetime s=t-p.hour*3600-p.min*60-p.sec;return((long)(s-((p.day_of_week+6)%7)*86400)/604800);}
double FloorToTick(const double p,const double t){return(MathFloor(p/t+1e-10)*t);}
double CeilToTick(const double p,const double t){return(MathCeil(p/t-1e-10)*t);}

bool CurrentBarOpen(datetime &bar_open)
  {
   long raw=0;bar_open=0;
   if(!SeriesInfoInteger(_Symbol,PERIOD_M5,SERIES_LASTBAR_DATE,raw)||raw<=0)return(false);
   bar_open=(datetime)raw;return(true);
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

bool LoadClosedFeatures(MqlRates &bar,double &atr,double &vol_sma,double &body_ratio,double &range_atr,double &vol_ratio)
  {
   bar.time=0;atr=0.0;vol_sma=0.0;body_ratio=0.0;range_atr=0.0;vol_ratio=0.0;
   if(Bars(_Symbol,PERIOD_M5)<30){g_invalid_inputs++;return(false);}
   const int need=MathMax(InpVolSMAPeriod,InpATRPeriod+1);
   MqlRates r[];ArraySetAsSeries(r,true);
   if(CopyRates(_Symbol,PERIOD_M5,1,need,r)!=need){g_invalid_inputs++;return(false);}
   bar=r[0];const double range=bar.high-bar.low;
   if(bar.time<=0||range<=0.0||bar.open<=0.0||bar.close<=0.0){g_invalid_inputs++;return(false);}
   double trsum=0.0;
   for(int i=0;i<InpATRPeriod;i++)
     {
      const double prev=r[i+1].close;
      if(prev<=0.0||r[i].high<=r[i].low){g_invalid_inputs++;return(false);}
      trsum+=MathMax(r[i].high-r[i].low,MathMax(MathAbs(r[i].high-prev),MathAbs(r[i].low-prev)));
     }
   double vsum=0.0;
   for(int i=0;i<InpVolSMAPeriod;i++)
     {
      if(r[i].tick_volume<=0){g_missing_volume++;return(false);}
      vsum+=(double)r[i].tick_volume;
     }
   atr=trsum/InpATRPeriod;vol_sma=vsum/InpVolSMAPeriod;
   if(!IsFinite(atr)||!IsFinite(vol_sma)||atr<=0.0||vol_sma<=0.0){g_invalid_inputs++;return(false);}
   body_ratio=MathAbs(bar.close-bar.open)/range;range_atr=range/atr;vol_ratio=(double)bar.tick_volume/vol_sma;
   return(IsFinite(body_ratio)&&IsFinite(range_atr)&&IsFinite(vol_ratio));
  }

bool ClosedATR(double &atr)
  {
   MqlRates b;double v,br,rr,vr;return(LoadClosedFeatures(b,atr,v,br,rr,vr));
  }

void ResetThrust(const string reason)
  {
   if(g_state==THRUST_DETECTED&&InpEnableTelemetry)PrintFormat("VTC001_STATE from=1 to=0 reason=%s thrust_time=%I64d age=%d",reason,(long)g_thrust_time,g_thrust_age);
   g_state=NEUTRAL;g_thrust_time=0;g_thrust_direction=0;g_thrust_age=0;g_thrust_high=0.0;g_thrust_low=0.0;g_thrust_atr=0.0;
   g_thrust_body_ratio=0.0;g_thrust_range_atr=0.0;g_thrust_vol_ratio=0.0;
  }

void FillSignal(EntrySignal &s,const MqlRates &bar,const datetime availability,const bool is_control,const double pause_body)
  {
   ZeroMemory(s);s.fired=true;s.decision_time=bar.time;s.availability_time=availability;s.thrust_time=g_thrust_time;
   s.pause_time=(is_control?0:bar.time);s.direction=g_thrust_direction;s.age=g_thrust_age;s.thrust_high=g_thrust_high;s.thrust_low=g_thrust_low;
   s.thrust_atr=g_thrust_atr;s.thrust_body_ratio=g_thrust_body_ratio;s.thrust_range_atr=g_thrust_range_atr;s.thrust_vol_ratio=g_thrust_vol_ratio;
   s.pause_body_ratio=pause_body;s.pause_open=bar.open;s.pause_high=bar.high;s.pause_low=bar.low;s.pause_close=bar.close;
   g_signals++;if(s.direction>0)g_long_signals++;else g_short_signals++;
   if(InpEnableTelemetry)PrintFormat("VTC001_SIGNAL decision=%I64d availability=%I64d direction=%s age=%d control=%s thrust_body=%.6f thrust_range_atr=%.6f thrust_vol_ratio=%.6f pause_body=%.6f",(long)s.decision_time,(long)s.availability_time,(s.direction>0?"LONG":"SHORT"),s.age,(is_control?"true":"false"),s.thrust_body_ratio,s.thrust_range_atr,s.thrust_vol_ratio,s.pause_body_ratio);
  }

bool BuildSignal(const datetime availability,EntrySignal &signal)
  {
   ZeroMemory(signal);MqlRates bar;double atr,vol_sma,body_ratio,range_atr,vol_ratio;
   if(!LoadClosedFeatures(bar,atr,vol_sma,body_ratio,range_atr,vol_ratio))return(false);
   if(bar.time==g_last_decision_time)return(false);g_last_decision_time=bar.time;g_closed_bars++;
   if((long)(availability-bar.time)!=PeriodSeconds(PERIOD_M5)){g_invalid_inputs++;return(false);}
   if(g_state==IN_POSITION)return(false);

   if(g_state==NEUTRAL)
     {
      const int direction=(bar.close>bar.open?1:(bar.close<bar.open?-1:0));
      if(direction==0||body_ratio<InpThrustBodyMin||range_atr<InpThrustRangeATRMin||vol_ratio<InpThrustVolMult)return(false);
      g_state=THRUST_DETECTED;g_thrust_time=bar.time;g_thrust_direction=direction;g_thrust_age=0;g_thrust_high=bar.high;g_thrust_low=bar.low;
      g_thrust_atr=atr;g_thrust_body_ratio=body_ratio;g_thrust_range_atr=range_atr;g_thrust_vol_ratio=vol_ratio;g_thrusts++;
      if(InpEnableTelemetry)PrintFormat("VTC001_THRUST time=%I64d direction=%s high=%.5f low=%.5f body_ratio=%.6f range_atr=%.6f tick_volume=%I64d vol_sma=%.2f vol_ratio=%.6f",(long)bar.time,(direction>0?"LONG":"SHORT"),bar.high,bar.low,body_ratio,range_atr,bar.tick_volume,vol_sma,vol_ratio);
      if(!InpRequirePause){FillSignal(signal,bar,availability,true,body_ratio);return(true);}
      return(false);
     }

   if(g_state!=THRUST_DETECTED||bar.time<=g_thrust_time)return(false);
   g_thrust_age++;
   if(g_thrust_age>InpMaxBarsThrustToPause){g_expiries++;ResetThrust("PAUSE_EXPIRY");return(false);}
   const bool no_new_extreme=(g_thrust_direction>0?bar.high<=g_thrust_high:bar.low>=g_thrust_low);
   const bool close_bounded=(bar.close>=g_thrust_low-InpPauseBeyondATR*g_thrust_atr&&bar.close<=g_thrust_high+InpPauseBeyondATR*g_thrust_atr);
   if(!no_new_extreme||!close_bounded||body_ratio>InpPauseBodyMax)return(false);
   g_pauses++;
   if(InpEnableTelemetry)PrintFormat("VTC001_PAUSE time=%I64d direction=%s age=%d high=%.5f low=%.5f close=%.5f body_ratio=%.6f",(long)bar.time,(g_thrust_direction>0?"LONG":"SHORT"),g_thrust_age,bar.high,bar.low,bar.close,body_ratio);
   FillSignal(signal,bar,availability,false,body_ratio);return(true);
  }

int VolumeDigits(const double s){int d=0;double v=s;while(d<8&&MathAbs(v-MathRound(v))>1e-9){v*=10.0;d++;}return(d);}
double NormalizeVolumeDown(const double v){double mn=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN),mx=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX),st=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);if(mn<=0||mx<mn||st<=0||v<mn)return(0);double u=MathFloor((MathMin(v,mx)-mn+1e-12)/st);return(NormalizeDouble(mn+u*st,VolumeDigits(st)));}

bool OwnedPosition(ulong &ticket){ticket=0;int n=0;for(int i=PositionsTotal()-1;i>=0;i--){ulong x=PositionGetTicket(i);if(x>0&&PositionSelectByTicket(x)&&PositionGetString(POSITION_SYMBOL)==_Symbol&&PositionGetInteger(POSITION_MAGIC)==InpMagic){ticket=x;n++;}}if(n>1)g_runtime_failed=true;return(n==1);}
bool AnySymbolExposure(){for(int i=PositionsTotal()-1;i>=0;i--){ulong x=PositionGetTicket(i);if(x>0&&PositionSelectByTicket(x)&&PositionGetString(POSITION_SYMBOL)==_Symbol)return(true);}return(false);}

void RefreshRiskLocks(const datetime now){double e=AccountInfoDouble(ACCOUNT_EQUITY);int d=DayKey(now);long w=WeekKey(now);if(d!=g_day_key){g_day_key=d;g_day_start_equity=e;g_day_locked=false;}if(w!=g_week_key){g_week_key=w;g_week_start_equity=e;g_week_locked=false;}if(g_day_start_equity>0&&e<=g_day_start_equity*(1-InpDailyLossPct/100.0))g_day_locked=true;if(g_week_start_equity>0&&e<=g_week_start_equity*(1-InpWeeklyLossPct/100.0))g_week_locked=true;}

bool CloseOwned(const string reason){ulong t=0;if(!OwnedPosition(t))return(true);g_close_attempts++;g_pending_exit_reason=reason;if(!g_trade.PositionClose(t,InpDeviationPoints)){g_close_rejects++;return(false);}uint c=g_trade.ResultRetcode();if(c!=TRADE_RETCODE_DONE&&c!=TRADE_RETCODE_DONE_PARTIAL){g_close_rejects++;return(false);}g_closes++;PrintFormat("VTC001_CLOSE_REQUEST reason=%s ticket=%I64u",reason,t);return(true);}

bool ModifyStop(const ulong ticket,const double proposed,const string reason)
  {
   if(!PositionSelectByTicket(ticket))return(false);bool is_long=((ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_BUY);double current=PositionGetDouble(POSITION_SL);MqlTick q;if(!SymbolInfoTick(_Symbol,q))return(false);
   double point=SymbolInfoDouble(_Symbol,SYMBOL_POINT),tick=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);if(point<=0||tick<=0)return(false);double next=(is_long?FloorToTick(proposed,tick):CeilToTick(proposed,tick));
   if((is_long&&current>=next-point*.1)||(!is_long&&current>0&&current<=next+point*.1))return(false);double md=(double)MathMax(MathMax(SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL),SymbolInfoInteger(_Symbol,SYMBOL_TRADE_FREEZE_LEVEL)),0)*point;
   if((is_long&&q.bid-next<md)||(!is_long&&next-q.ask<md))return(false);if(!g_trade.PositionModify(ticket,next,0.0))return(false);uint c=g_trade.ResultRetcode();if(c!=TRADE_RETCODE_DONE&&c!=TRADE_RETCODE_NO_CHANGES)return(false);
   PrintFormat("VTC001_STOP_MOVE reason=%s ticket=%I64u sl=%.5f mfe_points=%.1f mae_points=%.1f",reason,ticket,next,g_mfe_points,g_mae_points);return(true);
  }

void UpdatePositionPathAndStops(const ulong ticket,const bool new_bar)
  {
   if(!PositionSelectByTicket(ticket)||g_initial_risk<=0||g_entry_price<=0)return;bool is_long=((ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_BUY);MqlTick q;if(!SymbolInfoTick(_Symbol,q))return;
   double point=SymbolInfoDouble(_Symbol,SYMBOL_POINT);if(point<=0)return;double quote=(is_long?q.bid:q.ask),fav=(is_long?quote-g_entry_price:g_entry_price-quote);
   g_mfe_points=MathMax(g_mfe_points,MathMax(0.0,fav)/point);g_mae_points=MathMax(g_mae_points,MathMax(0.0,-fav)/point);
   if(fav>=InpBETriggerR*g_initial_risk){double be=(is_long?g_entry_price+InpBEOffsetR*g_initial_risk:g_entry_price-InpBEOffsetR*g_initial_risk);if(ModifyStop(ticket,be,"BREAKEVEN_PLUS"))g_be_moves++;}
   if(!g_trail_armed&&fav>=InpTrailStartR*g_initial_risk){g_trail_armed=true;g_trail_arms++;}
   if(g_trail_armed&&new_bar){double atr=0.0;if(ClosedATR(atr)&&atr>0.0){double trail=(is_long?q.bid-InpTrailATRMult*atr:q.ask+InpTrailATRMult*atr);if(ModifyStop(ticket,trail,"CLOSED_BAR_ATR_TRAIL"))g_trail_moves++;}}
  }

void ManagePosition(const datetime now,const datetime bar_open,const bool new_bar)
  {
   ulong t=0;if(!OwnedPosition(t))return;g_state=IN_POSITION;UpdatePositionPathAndStops(t,new_bar);MqlDateTime p;TimeToStruct(now,p);int m=p.hour*60+p.min;string r="";
   if(p.day_of_week==5&&m>=InpFridayFlatHour*60+InpFridayFlatMinute)r="FRIDAY_FLAT";else if(m>=InpDailyFlatHour*60+InpDailyFlatMinute)r="DAILY_FLAT";else if(new_bar){datetime s=g_entry_time;if(s<=0&&PositionSelectByTicket(t))s=(datetime)PositionGetInteger(POSITION_TIME);if(s>0&&iBarShift(_Symbol,PERIOD_M5,s,false)>=InpTimeStopBars)r="TIME_STOP";}
   if(r==""||g_last_close_attempt_bar==bar_open)return;g_last_close_attempt_bar=bar_open;CloseOwned(r);
  }

bool EntryTimeAllowed(const datetime t){MqlDateTime p;TimeToStruct(t,p);if(p.day_of_week==0||p.day_of_week==6)return(false);int m=p.hour*60+p.min;if(m>=InpDailyFlatHour*60+InpDailyFlatMinute)return(false);if(p.day_of_week==5&&m>=InpFridayFlatHour*60+InpFridayFlatMinute)return(false);return(true);}

bool SubmitEntry(const EntrySignal &s)
  {
   if(!s.fired||AnySymbolExposure()||!EntryTimeAllowed(s.availability_time)){g_exposure_skips++;return(false);}if(g_day_locked||g_week_locked){g_risk_lock_skips++;return(false);}MqlTick q;if(!SymbolInfoTick(_Symbol,q)||q.ask<=q.bid)return(false);
   double point=SymbolInfoDouble(_Symbol,SYMBOL_POINT),tick=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE),contract=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_CONTRACT_SIZE);if(point<=0||tick<=0||contract<=0)return(false);
   double spread=(q.ask-q.bid)/point;if(spread>InpMaxSpreadPoints){g_spread_rejects++;return(false);}double entry=(s.direction>0?q.ask:q.bid),structural=(s.direction>0?s.thrust_low-InpSLBufferATR*s.thrust_atr:s.thrust_high+InpSLBufferATR*s.thrust_atr);
   double dist=(s.direction>0?entry-structural:structural-entry);dist=MathMax(InpMinSLATR*s.thrust_atr,MathMin(dist,InpMaxSLATR*s.thrust_atr));if(dist<=0)return(false);double sl=(s.direction>0?FloorToTick(entry-dist,tick):CeilToTick(entry+dist,tick));
   ENUM_ORDER_TYPE type=(s.direction>0?ORDER_TYPE_BUY:ORDER_TYPE_SELL);double loss=0,margin1=0;if(!OrderCalcProfit(type,_Symbol,1,entry,sl,loss)||loss>=0)return(false);if(!OrderCalcMargin(type,_Symbol,1,entry,margin1)||margin1<=0)return(false);
   double eq=AccountInfoDouble(ACCOUNT_EQUITY),free=AccountInfoDouble(ACCOUNT_MARGIN_FREE);double vr=eq*(InpRiskPercent/100.0)/MathAbs(loss),vn=(eq*InpMaxNotionalMult)/(entry*contract),vm=(free*(InpMaxMarginUsagePct/100.0))/margin1;
   double volume=NormalizeVolumeDown(MathMin(vr,MathMin(vn,vm)));if(volume<=0)return(false);double margin=0;if(!OrderCalcMargin(type,_Symbol,volume,entry,margin))return(false);double notional=volume*entry*contract;if(margin>free*InpMaxMarginUsagePct/100.0+.01||notional>eq*InpMaxNotionalMult+.01)return(false);
   g_trade.SetExpertMagicNumber(InpMagic);g_trade.SetDeviationInPoints(InpDeviationPoints);g_trade.SetTypeFillingBySymbol(_Symbol);bool sent=g_trade.PositionOpen(_Symbol,type,volume,entry,sl,0.0,InpVariantTag);uint c=g_trade.ResultRetcode();
   if(!sent||(c!=TRADE_RETCODE_DONE&&c!=TRADE_RETCODE_DONE_PARTIAL)){g_entry_rejects++;ResetThrust("ENTRY_REJECTED");return(false);}g_entries++;g_state=IN_POSITION;g_entry_time=s.availability_time;g_entry_price=(g_trade.ResultPrice()>0?g_trade.ResultPrice():entry);g_initial_sl=sl;g_initial_risk=MathAbs(g_entry_price-sl);g_entry_margin_usage_pct=100*margin/free;g_mfe_points=0;g_mae_points=0;g_trail_armed=false;g_pending_exit_reason="";
   PrintFormat("VTC001_ENTRY decision=%I64d direction=%s volume=%.2f entry=%.5f sl=%.5f risk=%.5f thrust_age=%d thrust_range_atr=%.6f thrust_vol_ratio=%.6f spread_points=%.1f volume_risk=%.4f volume_notional=%.4f volume_margin=%.4f notional_mult=%.4f margin_usage_pct=%.4f",(long)s.decision_time,(s.direction>0?"LONG":"SHORT"),volume,g_entry_price,sl,g_initial_risk,s.age,s.thrust_range_atr,s.thrust_vol_ratio,spread,vr,vn,vm,notional/eq,g_entry_margin_usage_pct);return(true);
  }

string ExitReasonName(const long r){if(r==DEAL_REASON_SL)return("SL");if(r==DEAL_REASON_TP)return("TP_UNEXPECTED");if(r==DEAL_REASON_EXPERT&&g_pending_exit_reason!="")return(g_pending_exit_reason);return(StringFormat("DEAL_REASON_%d",(int)r));}

void OnTradeTransaction(const MqlTradeTransaction &tr,const MqlTradeRequest &rq,const MqlTradeResult &rs)
  {
   if(tr.type!=TRADE_TRANSACTION_DEAL_ADD||tr.deal==0||!HistoryDealSelect(tr.deal))return;if(HistoryDealGetString(tr.deal,DEAL_SYMBOL)!=_Symbol||HistoryDealGetInteger(tr.deal,DEAL_MAGIC)!=InpMagic)return;long k=HistoryDealGetInteger(tr.deal,DEAL_ENTRY);if(k!=DEAL_ENTRY_OUT&&k!=DEAL_ENTRY_OUT_BY)return;
   long reason=HistoryDealGetInteger(tr.deal,DEAL_REASON);double price=HistoryDealGetDouble(tr.deal,DEAL_PRICE),profit=HistoryDealGetDouble(tr.deal,DEAL_PROFIT),com=HistoryDealGetDouble(tr.deal,DEAL_COMMISSION),swap=HistoryDealGetDouble(tr.deal,DEAL_SWAP);datetime t=(datetime)HistoryDealGetInteger(tr.deal,DEAL_TIME);
   PrintFormat("VTC001_EXIT time=%I64d reason=%s price=%.5f profit=%.2f commission=%.2f swap=%.2f net=%.2f mfe_points=%.1f mae_points=%.1f margin_usage_pct=%.4f bars_held=%d",(long)t,ExitReasonName(reason),price,profit,com,swap,profit+com+swap,g_mfe_points,g_mae_points,g_entry_margin_usage_pct,(g_entry_time>0?iBarShift(_Symbol,PERIOD_M5,g_entry_time,false):-1));
   ulong ticket=0;if(!OwnedPosition(ticket)){g_entry_time=0;g_entry_price=0;g_initial_sl=0;g_initial_risk=0;g_entry_margin_usage_pct=0;g_trail_armed=false;g_pending_exit_reason="";ResetThrust("POSITION_CLOSED");}
  }

bool InputsAreFrozen()
  {
   bool variant=((InpVariantTag==PRIMARY_VARIANT&&InpRequirePause)||(InpVariantTag==CONTROL_VARIANT&&!InpRequirePause));
   return(InpResearchAutoMode&&InpEnableTelemetry&&InpHypothesisId==EXPECTED_HYPOTHESIS&&variant&&InpATRPeriod==14&&InpVolSMAPeriod==20&&MathAbs(InpThrustBodyMin-.62)<1e-12&&MathAbs(InpThrustRangeATRMin-1.25)<1e-12&&MathAbs(InpThrustVolMult-1.70)<1e-12&&InpMaxBarsThrustToPause==4&&MathAbs(InpPauseBodyMax-.45)<1e-12&&MathAbs(InpPauseBeyondATR-.25)<1e-12&&MathAbs(InpSLBufferATR-.35)<1e-12&&MathAbs(InpMinSLATR-1.15)<1e-12&&MathAbs(InpMaxSLATR-2.50)<1e-12&&MathAbs(InpBETriggerR-.90)<1e-12&&MathAbs(InpBEOffsetR-.15)<1e-12&&MathAbs(InpTrailStartR-1.60)<1e-12&&MathAbs(InpTrailATRMult-.80)<1e-12&&InpTimeStopBars==24&&MathAbs(InpRiskPercent-.25)<1e-12&&MathAbs(InpMaxNotionalMult-3.50)<1e-12&&MathAbs(InpMaxMarginUsagePct-10)<1e-12&&InpMaxSpreadPoints==45&&MathAbs(InpDailyLossPct-1)<1e-12&&MathAbs(InpWeeklyLossPct-2.5)<1e-12&&InpDailyFlatHour==21&&InpDailyFlatMinute==45&&InpFridayFlatHour==18&&InpFridayFlatMinute==45&&InpDeviationPoints==14&&InpMagic==5605201);
  }

int OnInit()
  {
   if(_Symbol!="XAUUSD"||_Period!=PERIOD_M5||!InputsAreFrozen())return(INIT_PARAMETERS_INCORRECT);if(!EmitSeriesProof())return(INIT_FAILED);
   g_trade.SetExpertMagicNumber(InpMagic);g_trade.SetDeviationInPoints(InpDeviationPoints);g_trade.SetTypeFillingBySymbol(_Symbol);datetime now=TimeCurrent();double e=AccountInfoDouble(ACCOUNT_EQUITY);g_day_key=DayKey(now);g_week_key=WeekKey(now);g_day_start_equity=e;g_week_start_equity=e;if(!CurrentBarOpen(g_last_bar_open))return(INIT_FAILED);
   PrintFormat("VTC001_INIT ea=%s hypothesis=%s variant=%s symbol=%s timeframe=M5 require_pause=%s",EA_NAME,InpHypothesisId,InpVariantTag,_Symbol,(InpRequirePause?"true":"false"));return(INIT_SUCCEEDED);
  }

void OnDeinit(const int reason)
  {
   PrintFormat("VTC001_SUMMARY reason=%d runtime_failed=%s closed_bars=%I64d thrusts=%I64d pauses=%I64d expiries=%I64d signals=%I64d long=%I64d short=%I64d missing_volume=%I64d spread_rejects=%I64d risk_lock_skips=%I64d exposure_skips=%I64d entries=%I64d entry_rejects=%I64d be_moves=%I64d trail_arms=%I64d trail_moves=%I64d close_attempts=%I64d close_rejects=%I64d closes=%I64d invalid=%I64d",reason,(g_runtime_failed?"true":"false"),g_closed_bars,g_thrusts,g_pauses,g_expiries,g_signals,g_long_signals,g_short_signals,g_missing_volume,g_spread_rejects,g_risk_lock_skips,g_exposure_skips,g_entries,g_entry_rejects,g_be_moves,g_trail_arms,g_trail_moves,g_close_attempts,g_close_rejects,g_closes,g_invalid_inputs);
  }

void OnTick()
  {
   datetime bar=0;if(!CurrentBarOpen(bar))return;datetime now=TimeCurrent();RefreshRiskLocks(now);const bool new_bar=(bar!=g_last_bar_open);ManagePosition(now,bar,new_bar);if(!new_bar)return;g_last_bar_open=bar;if(AnySymbolExposure())return;
   EntrySignal s;if(BuildSignal(bar,s)&&s.fired)SubmitEntry(s);
  }
