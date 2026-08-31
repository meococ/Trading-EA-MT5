//+------------------------------------------------------------------+
//| EA_Residual_EUR_M15_V8.mq5                                     |
//| HYP-XRV-EURUSD-M15-001: synchronized cross-pair residual fade   |
//+------------------------------------------------------------------+
#property strict
#property version "1.00"
#property description "Untuned closed-bar EURUSD M15 cross-pair residual EA"
#include <Trade/Trade.mqh>

input group "--- Frozen authority ---"
input bool InpResearchAutoMode=false;
input bool InpEnableTelemetry=true;
input string InpHypothesisId="HYP-XRV-EURUSD-M15-001";
input string InpVariantTag="RETRACE_PRIMARY";
input bool InpRequireRetracement=true;

input group "--- Frozen residual signal ---"
input string InpJPYSymbol="USDJPY";
input string InpGBPSymbol="GBPUSD";
input int InpSyncWarmupBars=50;
input double InpResidualThreshold=0.00028;
input double InpRetracementPct=0.40;
input int InpMaxBarsDislocToRev=5;
input int InpATRPeriod=14;

input group "--- Frozen exits and risk ---"
input double InpSLATRMult=1.80;
input double InpMinSLPips=12.0;
input double InpMaxSLPips=32.0;
input double InpBETriggerR=0.90;
input double InpBEOffsetPips=1.0;
input double InpTrailStartR=1.50;
input double InpTrailPips=8.0;
input int InpTimeStopBars=10;
input double InpRiskPercent=0.25;
input double InpMaxNotionalMult=3.50;
input double InpMaxMarginUsagePct=10.0;
input int InpMaxSpreadPoints=16;
input double InpDailyLossPct=1.00;
input double InpWeeklyLossPct=2.50;
input int InpDailyFlatHour=21;
input int InpDailyFlatMinute=40;
input int InpFridayFlatHour=18;
input int InpFridayFlatMinute=40;
input int InpDeviationPoints=7;
input long InpMagic=5605401;

const string EA_NAME="EA_Residual_EUR_M15_V8";
const string EXPECTED_HYPOTHESIS="HYP-XRV-EURUSD-M15-001";
const string PRIMARY_VARIANT="RETRACE_PRIMARY";
const string CONTROL_VARIANT="DIRECT_RESIDUAL_CONTROL";

enum ResidualState { NEUTRAL=0, DISLOCATION=1, IN_POSITION=2 };

struct EntrySignal
  {
   bool fired;
   datetime decision_time,availability_time,disloc_time;
   int direction,age;
   double ret_eur,ret_jpy,ret_gbp,basket,residual,original_residual,retrace_fraction,atr;
  };

CTrade g_trade;
ResidualState g_state=NEUTRAL;
datetime g_last_bar_open=0,g_disloc_time=0,g_entry_time=0,g_last_close_attempt_bar=0;
int g_resid_direction=0,g_disloc_age=0,g_sync_warmup=0;
double g_original_residual=0.0;
double g_entry_price=0.0,g_initial_sl=0.0,g_initial_risk=0.0,g_mfe_points=0.0,g_mae_points=0.0,g_entry_margin_usage_pct=0.0;
bool g_trail_armed=false,g_day_locked=false,g_week_locked=false,g_runtime_failed=false;
string g_pending_exit_reason="";
int g_day_key=0;long g_week_key=0;double g_day_start_equity=0.0,g_week_start_equity=0.0;

long g_potential_bars=0,g_synced_bars=0,g_sync_skips=0,g_zero_volume_skips=0,g_warmup_skips=0,g_dislocations=0,g_reversions=0,g_expiries=0;
long g_signals=0,g_long_signals=0,g_short_signals=0,g_spread_rejects=0,g_risk_lock_skips=0,g_exposure_skips=0,g_entries=0,g_entry_rejects=0;
long g_be_moves=0,g_trail_arms=0,g_trail_moves=0,g_close_attempts=0,g_close_rejects=0,g_closes=0,g_invalid_inputs=0;

bool IsFinite(const double v){return(v!=EMPTY_VALUE&&MathIsValidNumber(v));}
int DayKey(const datetime t){MqlDateTime p;TimeToStruct(t,p);return(p.year*10000+p.mon*100+p.day);}
long WeekKey(const datetime t){MqlDateTime p;TimeToStruct(t,p);datetime s=t-p.hour*3600-p.min*60-p.sec;return((long)(s-((p.day_of_week+6)%7)*86400)/604800);}
double PipSize(){const int d=(int)SymbolInfoInteger(_Symbol,SYMBOL_DIGITS);const double p=SymbolInfoDouble(_Symbol,SYMBOL_POINT);return((d==3||d==5)?10.0*p:p);}
double FloorToTick(const double p,const double t){return(MathFloor(p/t+1e-10)*t);}
double CeilToTick(const double p,const double t){return(MathCeil(p/t-1e-10)*t);}

bool CurrentBarOpen(datetime &bar_open){long raw=0;bar_open=0;if(!SeriesInfoInteger(_Symbol,PERIOD_M15,SERIES_LASTBAR_DATE,raw)||raw<=0)return(false);bar_open=(datetime)raw;return(true);}

bool EmitSeriesProof()
  {
   long sync=0,m5first=0,m5terminal=0,m1server=0,m1terminal=0,bars=0;if(!SeriesInfoInteger(_Symbol,PERIOD_M5,SERIES_SYNCHRONIZED,sync)||!SeriesInfoInteger(_Symbol,PERIOD_M5,SERIES_FIRSTDATE,m5first)||!SeriesInfoInteger(_Symbol,PERIOD_M5,SERIES_TERMINAL_FIRSTDATE,m5terminal)||!SeriesInfoInteger(_Symbol,PERIOD_M1,SERIES_SERVER_FIRSTDATE,m1server)||!SeriesInfoInteger(_Symbol,PERIOD_M1,SERIES_TERMINAL_FIRSTDATE,m1terminal)||!SeriesInfoInteger(_Symbol,PERIOD_M5,SERIES_BARS_COUNT,bars))return(false);
   ResetLastError();const long maxbars=TerminalInfoInteger(TERMINAL_MAXBARS);const int terr=GetLastError();datetime a[];ArraySetAsSeries(a,false);ResetLastError();const int n=CopyTime(_Symbol,PERIOD_M5,(datetime)m5first,1,a);const int err=GetLastError();const long first=(n==1?(long)a[0]:0);PrintFormat("DATA_EPOCH_D0_SERIES_PROOF symbol=%s m5_synchronized=%I64d m5_first_epoch=%I64d m5_terminal_first_epoch=%I64d m1_server_first_epoch=%I64d m1_terminal_first_epoch=%I64d m5_bars=%I64d terminal_maxbars=%I64d copytime_from_epoch=%I64d copytime_count=1 copytime_result=%d copytime_first_epoch=%I64d copytime_last_error=%d",_Symbol,sync,m5first,m5terminal,m1server,m1terminal,bars,maxbars,m5first,n,first,err);return(sync==1&&m5first>0&&m5terminal>0&&m1server>0&&m1terminal>0&&bars>0&&maxbars>0&&terr==0&&n==1&&first==m5first&&err==0);
  }

bool LoadSynchronizedReturns(MqlRates &eur_bar,double &ret_eur,double &ret_jpy,double &ret_gbp)
  {
   g_potential_bars++;MqlRates e[],j[],g[];ArraySetAsSeries(e,true);ArraySetAsSeries(j,true);ArraySetAsSeries(g,true);
   if(CopyRates(_Symbol,PERIOD_M15,1,2,e)!=2||CopyRates(InpJPYSymbol,PERIOD_M15,1,2,j)!=2||CopyRates(InpGBPSymbol,PERIOD_M15,1,2,g)!=2){g_sync_skips++;return(false);}
   if(e[0].time<=0||e[0].time!=j[0].time||e[0].time!=g[0].time||e[1].time!=j[1].time||e[1].time!=g[1].time){g_sync_skips++;return(false);}
   if(e[0].tick_volume<=0||j[0].tick_volume<=0||g[0].tick_volume<=0||e[1].tick_volume<=0||j[1].tick_volume<=0||g[1].tick_volume<=0){g_zero_volume_skips++;return(false);}
   if(e[0].close<=0||e[1].close<=0||j[0].close<=0||j[1].close<=0||g[0].close<=0||g[1].close<=0){g_invalid_inputs++;return(false);}
   eur_bar=e[0];ret_eur=(e[0].close-e[1].close)/e[1].close;ret_jpy=(j[0].close-j[1].close)/j[1].close;ret_gbp=(g[0].close-g[1].close)/g[1].close;
   if(!IsFinite(ret_eur)||!IsFinite(ret_jpy)||!IsFinite(ret_gbp)){g_invalid_inputs++;return(false);}g_synced_bars++;return(true);
  }

bool ClosedEURATR(double &atr)
  {
   atr=0.0;MqlRates r[];ArraySetAsSeries(r,true);if(CopyRates(_Symbol,PERIOD_M15,1,InpATRPeriod+1,r)!=InpATRPeriod+1)return(false);double sum=0.0;
   for(int i=0;i<InpATRPeriod;i++){double prev=r[i+1].close;if(prev<=0||r[i].high<=r[i].low)return(false);sum+=MathMax(r[i].high-r[i].low,MathMax(MathAbs(r[i].high-prev),MathAbs(r[i].low-prev)));}atr=sum/InpATRPeriod;return(IsFinite(atr)&&atr>0.0);
  }

void ResetResidual(const string reason)
  {
   if(g_state==DISLOCATION&&InpEnableTelemetry)PrintFormat("XRV001_STATE from=1 to=0 reason=%s disloc_time=%I64d age=%d original=%.8f",reason,(long)g_disloc_time,g_disloc_age,g_original_residual);
   g_state=NEUTRAL;g_disloc_time=0;g_resid_direction=0;g_disloc_age=0;g_original_residual=0.0;
  }

void FillSignal(EntrySignal &s,const MqlRates &bar,const datetime availability,const double re,const double rj,const double rg,const double basket,const double residual,const double atr,const bool control)
  {
   ZeroMemory(s);s.fired=true;s.decision_time=bar.time;s.availability_time=availability;s.disloc_time=g_disloc_time;s.direction=-g_resid_direction;s.age=g_disloc_age;s.ret_eur=re;s.ret_jpy=rj;s.ret_gbp=rg;s.basket=basket;s.residual=residual;s.original_residual=g_original_residual;s.retrace_fraction=(MathAbs(g_original_residual)>0?1.0-MathAbs(residual)/MathAbs(g_original_residual):0.0);s.atr=atr;
   g_signals++;if(s.direction>0)g_long_signals++;else g_short_signals++;if(InpEnableTelemetry)PrintFormat("XRV001_SIGNAL decision=%I64d availability=%I64d direction=%s age=%d control=%s ret_eur=%.8f ret_jpy=%.8f ret_gbp=%.8f basket=%.8f residual=%.8f original=%.8f retrace=%.6f",(long)bar.time,(long)availability,(s.direction>0?"LONG":"SHORT"),s.age,(control?"true":"false"),re,rj,rg,basket,residual,g_original_residual,s.retrace_fraction);
  }

bool BuildSignal(const datetime availability,EntrySignal &signal)
  {
   ZeroMemory(signal);MqlRates bar;double re,rj,rg;if(!LoadSynchronizedReturns(bar,re,rj,rg))return(false);if((long)(availability-bar.time)!=PeriodSeconds(PERIOD_M15)){g_sync_skips++;return(false);}if(g_sync_warmup<InpSyncWarmupBars){g_sync_warmup++;g_warmup_skips++;return(false);}if(g_state==IN_POSITION)return(false);
   const double basket=(-rj+rg)/2.0,residual=re-basket;if(!IsFinite(basket)||!IsFinite(residual)){g_invalid_inputs++;return(false);}double atr=0.0;if(!ClosedEURATR(atr)){g_invalid_inputs++;return(false);}
   if(g_state==NEUTRAL)
     {
      if(MathAbs(residual)<InpResidualThreshold||residual==0.0)return(false);g_state=DISLOCATION;g_disloc_time=bar.time;g_resid_direction=(residual>0?1:-1);g_disloc_age=0;g_original_residual=residual;g_dislocations++;
      if(InpEnableTelemetry)PrintFormat("XRV001_DISLOCATION time=%I64d direction=%s ret_eur=%.8f ret_jpy=%.8f ret_gbp=%.8f basket=%.8f residual=%.8f",(long)bar.time,(g_resid_direction>0?"EUR_STRONG":"EUR_WEAK"),re,rj,rg,basket,residual);
      if(!InpRequireRetracement){FillSignal(signal,bar,availability,re,rj,rg,basket,residual,atr,true);return(true);}return(false);
     }
   if(g_state!=DISLOCATION||bar.time<=g_disloc_time)return(false);g_disloc_age++;double retrace=1.0-MathAbs(residual)/MathAbs(g_original_residual);bool close_reversion=(g_resid_direction>0?bar.close<bar.open:bar.close>bar.open);
   if(retrace>=InpRetracementPct&&close_reversion){g_reversions++;FillSignal(signal,bar,availability,re,rj,rg,basket,residual,atr,false);return(true);}if(g_disloc_age>=InpMaxBarsDislocToRev){g_expiries++;ResetResidual("REVERSION_EXPIRY");}return(false);
  }

int VolumeDigits(const double s){int d=0;double v=s;while(d<8&&MathAbs(v-MathRound(v))>1e-9){v*=10.0;d++;}return(d);}
double NormalizeVolumeDown(const double v){double mn=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN),mx=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX),st=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);if(mn<=0||mx<mn||st<=0||v<mn)return(0);double u=MathFloor((MathMin(v,mx)-mn+1e-12)/st);return(NormalizeDouble(mn+u*st,VolumeDigits(st)));}
bool OwnedPosition(ulong &ticket){ticket=0;int n=0;for(int i=PositionsTotal()-1;i>=0;i--){ulong x=PositionGetTicket(i);if(x>0&&PositionSelectByTicket(x)&&PositionGetString(POSITION_SYMBOL)==_Symbol&&PositionGetInteger(POSITION_MAGIC)==InpMagic){ticket=x;n++;}}if(n>1)g_runtime_failed=true;return(n==1);}
bool AnySymbolExposure(){for(int i=PositionsTotal()-1;i>=0;i--){ulong x=PositionGetTicket(i);if(x>0&&PositionSelectByTicket(x)&&PositionGetString(POSITION_SYMBOL)==_Symbol)return(true);}return(false);}
void RefreshRiskLocks(const datetime now){double e=AccountInfoDouble(ACCOUNT_EQUITY);int d=DayKey(now);long w=WeekKey(now);if(d!=g_day_key){g_day_key=d;g_day_start_equity=e;g_day_locked=false;}if(w!=g_week_key){g_week_key=w;g_week_start_equity=e;g_week_locked=false;}if(g_day_start_equity>0&&e<=g_day_start_equity*(1-InpDailyLossPct/100.0))g_day_locked=true;if(g_week_start_equity>0&&e<=g_week_start_equity*(1-InpWeeklyLossPct/100.0))g_week_locked=true;}
bool CloseOwned(const string reason){ulong t=0;if(!OwnedPosition(t))return(true);g_close_attempts++;g_pending_exit_reason=reason;if(!g_trade.PositionClose(t,InpDeviationPoints)){g_close_rejects++;return(false);}uint c=g_trade.ResultRetcode();if(c!=TRADE_RETCODE_DONE&&c!=TRADE_RETCODE_DONE_PARTIAL){g_close_rejects++;return(false);}g_closes++;PrintFormat("XRV001_CLOSE_REQUEST reason=%s ticket=%I64u",reason,t);return(true);}

bool ModifyStop(const ulong ticket,const double proposed,const string reason)
  {
   if(!PositionSelectByTicket(ticket))return(false);bool is_long=((ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_BUY);double current=PositionGetDouble(POSITION_SL);MqlTick q;if(!SymbolInfoTick(_Symbol,q))return(false);double point=SymbolInfoDouble(_Symbol,SYMBOL_POINT),tick=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);if(point<=0||tick<=0)return(false);double next=(is_long?FloorToTick(proposed,tick):CeilToTick(proposed,tick));if((is_long&&current>=next-point*.1)||(!is_long&&current>0&&current<=next+point*.1))return(false);double md=(double)MathMax(MathMax(SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL),SymbolInfoInteger(_Symbol,SYMBOL_TRADE_FREEZE_LEVEL)),0)*point;if((is_long&&q.bid-next<md)||(!is_long&&next-q.ask<md))return(false);if(!g_trade.PositionModify(ticket,next,0.0))return(false);uint c=g_trade.ResultRetcode();if(c!=TRADE_RETCODE_DONE&&c!=TRADE_RETCODE_NO_CHANGES)return(false);PrintFormat("XRV001_STOP_MOVE reason=%s ticket=%I64u sl=%.5f mfe_points=%.1f mae_points=%.1f",reason,ticket,next,g_mfe_points,g_mae_points);return(true);
  }

void UpdatePositionPathAndStops(const ulong ticket)
  {
   if(!PositionSelectByTicket(ticket)||g_initial_risk<=0||g_entry_price<=0)return;bool is_long=((ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_BUY);MqlTick q;if(!SymbolInfoTick(_Symbol,q))return;double point=SymbolInfoDouble(_Symbol,SYMBOL_POINT),pip=PipSize();if(point<=0||pip<=0)return;double quote=(is_long?q.bid:q.ask),fav=(is_long?quote-g_entry_price:g_entry_price-quote);g_mfe_points=MathMax(g_mfe_points,MathMax(0.0,fav)/point);g_mae_points=MathMax(g_mae_points,MathMax(0.0,-fav)/point);
   if(fav>=InpBETriggerR*g_initial_risk){double be=(is_long?g_entry_price+InpBEOffsetPips*pip:g_entry_price-InpBEOffsetPips*pip);if(ModifyStop(ticket,be,"BREAKEVEN_PLUS"))g_be_moves++;}if(!g_trail_armed&&fav>=InpTrailStartR*g_initial_risk){g_trail_armed=true;g_trail_arms++;}if(g_trail_armed){double trail=(is_long?q.bid-InpTrailPips*pip:q.ask+InpTrailPips*pip);if(ModifyStop(ticket,trail,"FIXED_TRAIL"))g_trail_moves++;}
  }

void ManagePosition(const datetime now,const datetime bar_open,const bool new_bar)
  {
   ulong t=0;if(!OwnedPosition(t))return;g_state=IN_POSITION;UpdatePositionPathAndStops(t);MqlDateTime p;TimeToStruct(now,p);int m=p.hour*60+p.min;string r="";if(p.day_of_week==5&&m>=InpFridayFlatHour*60+InpFridayFlatMinute)r="FRIDAY_FLAT";else if(m>=InpDailyFlatHour*60+InpDailyFlatMinute)r="DAILY_FLAT";else if(new_bar){datetime s=g_entry_time;if(s<=0&&PositionSelectByTicket(t))s=(datetime)PositionGetInteger(POSITION_TIME);if(s>0&&iBarShift(_Symbol,PERIOD_M15,s,false)>=InpTimeStopBars)r="TIME_STOP";}if(r==""||g_last_close_attempt_bar==bar_open)return;g_last_close_attempt_bar=bar_open;CloseOwned(r);
  }

bool EntryTimeAllowed(const datetime t){MqlDateTime p;TimeToStruct(t,p);if(p.day_of_week==0||p.day_of_week==6)return(false);int m=p.hour*60+p.min;if(m>=InpDailyFlatHour*60+InpDailyFlatMinute)return(false);if(p.day_of_week==5&&m>=InpFridayFlatHour*60+InpFridayFlatMinute)return(false);return(true);}

bool SubmitEntry(const EntrySignal &s)
  {
   if(!s.fired||AnySymbolExposure()||!EntryTimeAllowed(s.availability_time)){g_exposure_skips++;ResetResidual("ENTRY_CANCELLED");return(false);}if(g_day_locked||g_week_locked){g_risk_lock_skips++;ResetResidual("RISK_LOCK");return(false);}MqlTick q;if(!SymbolInfoTick(_Symbol,q)||q.ask<=q.bid)return(false);double point=SymbolInfoDouble(_Symbol,SYMBOL_POINT),pip=PipSize(),tick=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE),contract=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_CONTRACT_SIZE);if(point<=0||pip<=0||tick<=0||contract<=0)return(false);double spread=(q.ask-q.bid)/point;if(spread>InpMaxSpreadPoints){g_spread_rejects++;ResetResidual("SPREAD_CANCEL");return(false);}
   double entry=(s.direction>0?q.ask:q.bid),dist=MathMax(InpMinSLPips*pip,MathMin(InpSLATRMult*s.atr,InpMaxSLPips*pip));if(dist<=0)return(false);double sl=(s.direction>0?FloorToTick(entry-dist,tick):CeilToTick(entry+dist,tick));ENUM_ORDER_TYPE type=(s.direction>0?ORDER_TYPE_BUY:ORDER_TYPE_SELL);double loss=0,margin1=0;if(!OrderCalcProfit(type,_Symbol,1,entry,sl,loss)||loss>=0)return(false);if(!OrderCalcMargin(type,_Symbol,1,entry,margin1)||margin1<=0)return(false);
   double eq=AccountInfoDouble(ACCOUNT_EQUITY),free=AccountInfoDouble(ACCOUNT_MARGIN_FREE);double vr=eq*(InpRiskPercent/100.0)/MathAbs(loss),vn=(eq*InpMaxNotionalMult)/(entry*contract),vm=(free*(InpMaxMarginUsagePct/100.0))/margin1;double volume=NormalizeVolumeDown(MathMin(vr,MathMin(vn,vm)));if(volume<=0)return(false);double margin=0;if(!OrderCalcMargin(type,_Symbol,volume,entry,margin))return(false);double notional=volume*entry*contract;if(margin>free*InpMaxMarginUsagePct/100.0+.01||notional>eq*InpMaxNotionalMult+.01)return(false);
   g_trade.SetExpertMagicNumber(InpMagic);g_trade.SetDeviationInPoints(InpDeviationPoints);g_trade.SetTypeFillingBySymbol(_Symbol);bool sent=g_trade.PositionOpen(_Symbol,type,volume,entry,sl,0.0,InpVariantTag);uint c=g_trade.ResultRetcode();if(!sent||(c!=TRADE_RETCODE_DONE&&c!=TRADE_RETCODE_DONE_PARTIAL)){g_entry_rejects++;ResetResidual("ENTRY_REJECTED");return(false);}g_entries++;g_state=IN_POSITION;g_entry_time=s.availability_time;g_entry_price=(g_trade.ResultPrice()>0?g_trade.ResultPrice():entry);g_initial_sl=sl;g_initial_risk=MathAbs(g_entry_price-sl);g_entry_margin_usage_pct=100*margin/free;g_mfe_points=0;g_mae_points=0;g_trail_armed=false;g_pending_exit_reason="";
   PrintFormat("XRV001_ENTRY decision=%I64d direction=%s volume=%.2f entry=%.5f sl=%.5f risk=%.5f age=%d residual=%.8f original=%.8f retrace=%.6f spread_points=%.1f volume_risk=%.4f volume_notional=%.4f volume_margin=%.4f notional_mult=%.4f margin_usage_pct=%.4f",(long)s.decision_time,(s.direction>0?"LONG":"SHORT"),volume,g_entry_price,sl,g_initial_risk,s.age,s.residual,s.original_residual,s.retrace_fraction,spread,vr,vn,vm,notional/eq,g_entry_margin_usage_pct);return(true);
  }

string ExitReasonName(const long r){if(r==DEAL_REASON_SL)return("SL");if(r==DEAL_REASON_TP)return("TP_UNEXPECTED");if(r==DEAL_REASON_EXPERT&&g_pending_exit_reason!="")return(g_pending_exit_reason);return(StringFormat("DEAL_REASON_%d",(int)r));}
void OnTradeTransaction(const MqlTradeTransaction &tr,const MqlTradeRequest &rq,const MqlTradeResult &rs)
  {
   if(tr.type!=TRADE_TRANSACTION_DEAL_ADD||tr.deal==0||!HistoryDealSelect(tr.deal))return;if(HistoryDealGetString(tr.deal,DEAL_SYMBOL)!=_Symbol||HistoryDealGetInteger(tr.deal,DEAL_MAGIC)!=InpMagic)return;long k=HistoryDealGetInteger(tr.deal,DEAL_ENTRY);if(k!=DEAL_ENTRY_OUT&&k!=DEAL_ENTRY_OUT_BY)return;long reason=HistoryDealGetInteger(tr.deal,DEAL_REASON);double price=HistoryDealGetDouble(tr.deal,DEAL_PRICE),profit=HistoryDealGetDouble(tr.deal,DEAL_PROFIT),com=HistoryDealGetDouble(tr.deal,DEAL_COMMISSION),swap=HistoryDealGetDouble(tr.deal,DEAL_SWAP);datetime t=(datetime)HistoryDealGetInteger(tr.deal,DEAL_TIME);PrintFormat("XRV001_EXIT time=%I64d reason=%s price=%.5f profit=%.2f commission=%.2f swap=%.2f net=%.2f mfe_points=%.1f mae_points=%.1f margin_usage_pct=%.4f bars_held=%d",(long)t,ExitReasonName(reason),price,profit,com,swap,profit+com+swap,g_mfe_points,g_mae_points,g_entry_margin_usage_pct,(g_entry_time>0?iBarShift(_Symbol,PERIOD_M15,g_entry_time,false):-1));ulong ticket=0;if(!OwnedPosition(ticket)){g_entry_time=0;g_entry_price=0;g_initial_sl=0;g_initial_risk=0;g_entry_margin_usage_pct=0;g_trail_armed=false;g_pending_exit_reason="";ResetResidual("POSITION_CLOSED");}
  }

bool InputsAreFrozen()
  {
   bool variant=((InpVariantTag==PRIMARY_VARIANT&&InpRequireRetracement)||(InpVariantTag==CONTROL_VARIANT&&!InpRequireRetracement));return(InpResearchAutoMode&&InpEnableTelemetry&&InpHypothesisId==EXPECTED_HYPOTHESIS&&variant&&InpJPYSymbol=="USDJPY"&&InpGBPSymbol=="GBPUSD"&&InpSyncWarmupBars==50&&MathAbs(InpResidualThreshold-.00028)<1e-12&&MathAbs(InpRetracementPct-.40)<1e-12&&InpMaxBarsDislocToRev==5&&InpATRPeriod==14&&MathAbs(InpSLATRMult-1.8)<1e-12&&MathAbs(InpMinSLPips-12)<1e-12&&MathAbs(InpMaxSLPips-32)<1e-12&&MathAbs(InpBETriggerR-.9)<1e-12&&MathAbs(InpBEOffsetPips-1)<1e-12&&MathAbs(InpTrailStartR-1.5)<1e-12&&MathAbs(InpTrailPips-8)<1e-12&&InpTimeStopBars==10&&MathAbs(InpRiskPercent-.25)<1e-12&&MathAbs(InpMaxNotionalMult-3.5)<1e-12&&MathAbs(InpMaxMarginUsagePct-10)<1e-12&&InpMaxSpreadPoints==16&&MathAbs(InpDailyLossPct-1)<1e-12&&MathAbs(InpWeeklyLossPct-2.5)<1e-12&&InpDailyFlatHour==21&&InpDailyFlatMinute==40&&InpFridayFlatHour==18&&InpFridayFlatMinute==40&&InpDeviationPoints==7&&InpMagic==5605401);
  }

int OnInit(){if(_Symbol!="EURUSD"||_Period!=PERIOD_M15||!InputsAreFrozen())return(INIT_PARAMETERS_INCORRECT);if(!SymbolSelect(InpJPYSymbol,true)||!SymbolSelect(InpGBPSymbol,true)||!EmitSeriesProof())return(INIT_FAILED);g_trade.SetExpertMagicNumber(InpMagic);g_trade.SetDeviationInPoints(InpDeviationPoints);g_trade.SetTypeFillingBySymbol(_Symbol);datetime now=TimeCurrent();double e=AccountInfoDouble(ACCOUNT_EQUITY);g_day_key=DayKey(now);g_week_key=WeekKey(now);g_day_start_equity=e;g_week_start_equity=e;if(!CurrentBarOpen(g_last_bar_open))return(INIT_FAILED);PrintFormat("XRV001_INIT ea=%s hypothesis=%s variant=%s execution=%s refs=%s,%s timeframe=M15 require_retrace=%s",EA_NAME,InpHypothesisId,InpVariantTag,_Symbol,InpJPYSymbol,InpGBPSymbol,(InpRequireRetracement?"true":"false"));return(INIT_SUCCEEDED);}
void OnDeinit(const int reason){double skip_pct=(g_potential_bars>0?100.0*(g_sync_skips+g_zero_volume_skips)/g_potential_bars:0.0);PrintFormat("XRV001_SUMMARY reason=%d runtime_failed=%s potential_bars=%I64d synced_bars=%I64d sync_skips=%I64d zero_volume_skips=%I64d skip_pct=%.6f warmup_skips=%I64d dislocations=%I64d reversions=%I64d expiries=%I64d signals=%I64d long=%I64d short=%I64d spread_rejects=%I64d risk_lock_skips=%I64d exposure_skips=%I64d entries=%I64d entry_rejects=%I64d be_moves=%I64d trail_arms=%I64d trail_moves=%I64d close_attempts=%I64d close_rejects=%I64d closes=%I64d invalid=%I64d",reason,(g_runtime_failed?"true":"false"),g_potential_bars,g_synced_bars,g_sync_skips,g_zero_volume_skips,skip_pct,g_warmup_skips,g_dislocations,g_reversions,g_expiries,g_signals,g_long_signals,g_short_signals,g_spread_rejects,g_risk_lock_skips,g_exposure_skips,g_entries,g_entry_rejects,g_be_moves,g_trail_arms,g_trail_moves,g_close_attempts,g_close_rejects,g_closes,g_invalid_inputs);}
void OnTick(){datetime bar=0;if(!CurrentBarOpen(bar))return;datetime now=TimeCurrent();RefreshRiskLocks(now);const bool new_bar=(bar!=g_last_bar_open);ManagePosition(now,bar,new_bar);if(!new_bar)return;g_last_bar_open=bar;if(AnySymbolExposure())return;EntrySignal s;if(BuildSignal(bar,s)&&s.fired)SubmitEntry(s);}
