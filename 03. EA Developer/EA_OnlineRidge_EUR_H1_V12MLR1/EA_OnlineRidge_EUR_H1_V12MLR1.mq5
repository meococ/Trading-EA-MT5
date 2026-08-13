//+------------------------------------------------------------------+
//| EA_OnlineRidge_EUR_H1_V12MLR1.mq5                                 |
//| HYP-ORLS-EURUSD-H1-002: causal delayed-label online ridge       |
//+------------------------------------------------------------------+
#property strict
#property version "1.00"
#property description "Leakage-controlled EURUSD H1 online RLS research EA"
#include <Trade/Trade.mqh>

#define FEATURE_COUNT 6
#define MODEL_DIM 7
#define LABEL_HORIZON 4
#define SPREAD_WINDOW 24

input group "--- Frozen authority ---"
input bool InpResearchAutoMode=false;
input bool InpEnableTelemetry=true;
input string InpHypothesisId="HYP-ORLS-EURUSD-H1-002";
input string InpVariantTag="ONLINE_RLS_PRIMARY";
input bool InpUseOnlineRidge=true;

input group "--- Frozen online model ---"
input double InpForgettingFactor=0.9975;
input double InpRidgeAlpha=1.0;
input double InpStandardizerBeta=0.9975;
input int InpWarmupBars=120;
input double InpVarianceFloor=0.00000001;
input double InpCostSafetyMultiplier=1.5;
input double InpCommissionReturn=0.00008;
input double InpSlippageReturn=0.00005;

input group "--- Frozen lifecycle and risk ---"
input int InpATRPeriod=14;
input double InpSLATRMult=3.0;
input double InpSLMinPips=25.0;
input double InpSLMaxPips=80.0;
input double InpRiskPercent=0.25;
input double InpMaxNotionalMult=3.0;
input double InpMaxMarginUsagePct=9.0;
input int InpMaxSpreadPoints=15;
input double InpDailyLossPct=1.0;
input double InpWeeklyLossPct=2.5;
input int InpDailyFlatHour=21;
input int InpDailyFlatMinute=50;
input int InpFridayFlatHour=18;
input int InpFridayFlatMinute=50;
input int InpDeviationPoints=5;
input long InpMagic=5605502;

const string EA_NAME="EA_OnlineRidge_EUR_H1_V12MLR1";
const string EXPECTED_HYPOTHESIS="HYP-ORLS-EURUSD-H1-002";
const string PRIMARY_VARIANT="ONLINE_RLS_PRIMARY";
const string CONTROL_VARIANT="FOUR_HOUR_MOMENTUM_CONTROL";

struct ModelSignal
  {
   bool fired;
   datetime decision_time;
   int direction;
   double score,hurdle,atr14,baseline_score,spread_points;
  };

CTrade g_trade;
datetime g_last_bar_open=0,g_entry_time=0,g_last_close_attempt_bar=0;
double g_entry_price=0.0,g_initial_sl=0.0,g_initial_risk_price=0.0,g_entry_risk_cash=0.0,g_entry_margin_pct=0.0;
double g_mfe_points=0.0,g_mae_points=0.0;
string g_pending_exit_reason="";
bool g_day_locked=false,g_week_locked=false,g_runtime_failed=false;
int g_day_key=0;long g_week_key=0;double g_day_start_equity=0.0,g_week_start_equity=0.0;

double g_w[MODEL_DIM],g_p[MODEL_DIM][MODEL_DIM];
double g_mean[FEATURE_COUNT],g_var[FEATURE_COUNT];
bool g_standardizer_ready=false;
double g_sample_z[LABEL_HORIZON][MODEL_DIM],g_sample_open[LABEL_HORIZON];
datetime g_sample_time[LABEL_HORIZON];bool g_sample_valid[LABEL_HORIZON];
double g_spread_history[SPREAD_WINDOW];int g_spread_count=0,g_spread_next=0;
long g_bar_sequence=0,g_valid_observations=0,g_predictions=0,g_rls_updates=0,g_p_resets=0;
long g_samples_stored=0,g_labels_gap=0,g_skip_missing=0,g_skip_nonfinite=0,g_warmup_bars=0;
long g_long_signals=0,g_short_signals=0,g_hurdle_rejects=0,g_schedule_rejects=0,g_spread_rejects=0;
long g_risk_lock_skips=0,g_exposure_skips=0,g_entries=0,g_entry_rejects=0,g_close_attempts=0,g_close_rejects=0,g_closes=0,g_catastrophe_stops=0;

bool IsFinite(const double v){return(v!=EMPTY_VALUE&&MathIsValidNumber(v));}
int DayKey(const datetime t){MqlDateTime p;TimeToStruct(t,p);return(p.year*10000+p.mon*100+p.day);}
long WeekKey(const datetime t){MqlDateTime p;TimeToStruct(t,p);datetime s=t-p.hour*3600-p.min*60-p.sec;return((long)(s-((p.day_of_week+6)%7)*86400)/604800);}
double FloorToTick(const double p,const double t){return(MathFloor(p/t+1e-10)*t);}
double CeilToTick(const double p,const double t){return(MathCeil(p/t-1e-10)*t);}
double PipSize(){double p=SymbolInfoDouble(_Symbol,SYMBOL_POINT);int d=(int)SymbolInfoInteger(_Symbol,SYMBOL_DIGITS);return((d==3||d==5)?10.0*p:p);}

bool CurrentBarOpen(datetime &bar_open){long raw=0;bar_open=0;if(!SeriesInfoInteger(_Symbol,PERIOD_H1,SERIES_LASTBAR_DATE,raw)||raw<=0)return(false);bar_open=(datetime)raw;return(true);}

bool EmitSeriesProof()
  {
   long sync=0,m5first=0,m5terminal=0,m1server=0,m1terminal=0,bars=0;
   if(!SeriesInfoInteger(_Symbol,PERIOD_M5,SERIES_SYNCHRONIZED,sync)||!SeriesInfoInteger(_Symbol,PERIOD_M5,SERIES_FIRSTDATE,m5first)||!SeriesInfoInteger(_Symbol,PERIOD_M5,SERIES_TERMINAL_FIRSTDATE,m5terminal)||!SeriesInfoInteger(_Symbol,PERIOD_M1,SERIES_SERVER_FIRSTDATE,m1server)||!SeriesInfoInteger(_Symbol,PERIOD_M1,SERIES_TERMINAL_FIRSTDATE,m1terminal)||!SeriesInfoInteger(_Symbol,PERIOD_M5,SERIES_BARS_COUNT,bars))return(false);
   ResetLastError();const long maxbars=TerminalInfoInteger(TERMINAL_MAXBARS);const int terr=GetLastError();datetime a[];ArraySetAsSeries(a,false);ResetLastError();const int n=CopyTime(_Symbol,PERIOD_M5,(datetime)m5first,1,a);const int err=GetLastError();const long first=(n==1?(long)a[0]:0);
   PrintFormat("DATA_EPOCH_D0_SERIES_PROOF symbol=%s m5_synchronized=%I64d m5_first_epoch=%I64d m5_terminal_first_epoch=%I64d m1_server_first_epoch=%I64d m1_terminal_first_epoch=%I64d m5_bars=%I64d terminal_maxbars=%I64d copytime_from_epoch=%I64d copytime_count=1 copytime_result=%d copytime_first_epoch=%I64d copytime_last_error=%d",_Symbol,sync,m5first,m5terminal,m1server,m1terminal,bars,maxbars,m5first,n,first,err);
   return(sync==1&&m5first>0&&m5terminal>0&&m1server>0&&m1terminal>0&&bars>0&&maxbars>0&&terr==0&&n==1&&first==m5first&&err==0);
  }

void InitializeModel()
  {
   for(int i=0;i<MODEL_DIM;i++){g_w[i]=0.0;for(int j=0;j<MODEL_DIM;j++)g_p[i][j]=(i==j?1.0/InpRidgeAlpha:0.0);}
   for(int i=0;i<LABEL_HORIZON;i++){g_sample_valid[i]=false;g_sample_open[i]=0.0;g_sample_time[i]=0;for(int j=0;j<MODEL_DIM;j++)g_sample_z[i][j]=0.0;}
  }

bool LoadRawFeatures(const MqlTick &q,double &bar_open,double &atr14,double &spread_points,double &spread_return,double &baseline_score,double &raw[])
  {
   MqlRates r[];ArraySetAsSeries(r,true);const int need=26;if(CopyRates(_Symbol,PERIOD_H1,0,need,r)!=need){g_skip_missing++;return(false);}
   if(r[0].time<=0||r[0].open<=0||r[1].close<=0||r[2].close<=0||r[5].close<=0){g_skip_missing++;return(false);}bar_open=r[0].open;
   double atr8=0.0,atr24=0.0;
   for(int i=1;i<=24;i++)
     {
      double prev=r[i+1].close,tr=MathMax(r[i].high-r[i].low,MathMax(MathAbs(r[i].high-prev),MathAbs(r[i].low-prev)));
      if(prev<=0||tr<0||!IsFinite(tr)){g_skip_nonfinite++;return(false);}atr24+=tr;if(i<=8)atr8+=tr;
     }
   atr8/=8.0;atr24/=24.0;atr14=0.0;
   for(int i=1;i<=14;i++){double prev=r[i+1].close;atr14+=MathMax(r[i].high-r[i].low,MathMax(MathAbs(r[i].high-prev),MathAbs(r[i].low-prev)));}atr14/=14.0;
   double tvavg=0.0;for(int i=1;i<=8;i++)tvavg+=(double)r[i].tick_volume;tvavg/=8.0;
   double mid=(q.ask+q.bid)*0.5,point=SymbolInfoDouble(_Symbol,SYMBOL_POINT);if(q.ask<=q.bid||mid<=0||point<=0||atr8<=0||atr24<=0||atr14<=0){g_skip_nonfinite++;return(false);}
   spread_points=(q.ask-q.bid)/point;spread_return=(q.ask-q.bid)/mid;
   double sm=0.0,ss=0.0;if(g_spread_count>0){for(int i=0;i<g_spread_count;i++)sm+=g_spread_history[i];sm/=g_spread_count;for(int i=0;i<g_spread_count;i++){double d=g_spread_history[i]-sm;ss+=d*d;}ss=MathSqrt(ss/g_spread_count);}
   double spread_z=(g_spread_count>=SPREAD_WINDOW&&ss>1e-12?(spread_return-sm)/ss:0.0);
   raw[0]=(r[1].close-r[2].close)/r[2].close;
   raw[1]=(r[1].close-r[5].close)/r[5].close;
   raw[2]=atr8/r[1].close;
   raw[3]=atr8/atr24;
   raw[4]=((double)r[1].tick_volume-tvavg)/(tvavg+1.0);
   raw[5]=spread_z;
   double prior_open=r[4].open;baseline_score=(prior_open>0?MathLog(bar_open/prior_open):0.0);
   for(int i=0;i<FEATURE_COUNT;i++)if(!IsFinite(raw[i])){g_skip_nonfinite++;return(false);}return(true);
  }

void StandardizePastOnly(const double &raw[],double &z[])
  {
   for(int i=0;i<FEATURE_COUNT;i++){double v=MathMax(g_var[i],InpVarianceFloor);z[i]=(g_standardizer_ready?(raw[i]-g_mean[i])/MathSqrt(v):0.0);}z[FEATURE_COUNT]=1.0;
  }

void UpdateStandardizer(const double &raw[])
  {
   if(!g_standardizer_ready){for(int i=0;i<FEATURE_COUNT;i++){g_mean[i]=raw[i];g_var[i]=InpVarianceFloor;}g_standardizer_ready=true;return;}
   const double one=1.0-InpStandardizerBeta;for(int i=0;i<FEATURE_COUNT;i++){double delta=raw[i]-g_mean[i];g_mean[i]+=one*delta;g_var[i]=MathMax(InpVarianceFloor,InpStandardizerBeta*(g_var[i]+one*delta*delta));}
  }

void UpdateSpreadHistory(const double v){g_spread_history[g_spread_next]=v;g_spread_next=(g_spread_next+1)%SPREAD_WINDOW;if(g_spread_count<SPREAD_WINDOW)g_spread_count++;}

void ResetCovariance()
  {
   for(int i=0;i<MODEL_DIM;i++)for(int j=0;j<MODEL_DIM;j++)g_p[i][j]=(i==j?1.0/InpRidgeAlpha:0.0);g_p_resets++;
  }

bool RLSUpdate(const double &x[],const double y)
  {
   double px[MODEL_DIM],row[MODEL_DIM],gain[MODEL_DIM];
   for(int i=0;i<MODEL_DIM;i++){px[i]=0.0;for(int j=0;j<MODEL_DIM;j++)px[i]+=g_p[i][j]*x[j];}
   double den=InpForgettingFactor;for(int i=0;i<MODEL_DIM;i++)den+=x[i]*px[i];if(!IsFinite(den)||den<=1e-12){ResetCovariance();return(false);}
   for(int i=0;i<MODEL_DIM;i++)gain[i]=px[i]/den;
   double pred=0.0;for(int i=0;i<MODEL_DIM;i++)pred+=g_w[i]*x[i];double err=y-pred;
   for(int i=0;i<MODEL_DIM;i++)g_w[i]+=gain[i]*err;
   for(int j=0;j<MODEL_DIM;j++){row[j]=0.0;for(int i=0;i<MODEL_DIM;i++)row[j]+=x[i]*g_p[i][j];}
   for(int i=0;i<MODEL_DIM;i++)for(int j=0;j<MODEL_DIM;j++)g_p[i][j]=(g_p[i][j]-gain[i]*row[j])/InpForgettingFactor;
   bool bad=false;for(int i=0;i<MODEL_DIM;i++){if(!IsFinite(g_w[i])||!IsFinite(g_p[i][i])||g_p[i][i]>1e6||g_p[i][i]<=0)bad=true;}
   if(bad){for(int i=0;i<MODEL_DIM;i++)if(!IsFinite(g_w[i]))g_w[i]=0.0;ResetCovariance();return(false);}g_rls_updates++;return(true);
  }

void MatureStoredSample(const int slot,const datetime now,const double current_open)
  {
   if(!g_sample_valid[slot])return;bool contiguous=(now-g_sample_time[slot]==LABEL_HORIZON*PeriodSeconds(PERIOD_H1));if(!contiguous||current_open<=0||g_sample_open[slot]<=0){g_labels_gap++;g_sample_valid[slot]=false;return;}
   if(g_valid_observations>=InpWarmupBars){double y=MathLog(current_open/g_sample_open[slot]),x[MODEL_DIM];for(int i=0;i<MODEL_DIM;i++)x[i]=g_sample_z[slot][i];if(IsFinite(y))RLSUpdate(x,y);else g_skip_nonfinite++;}g_sample_valid[slot]=false;
  }

double ModelScore(const double &z[]){double s=0.0;for(int i=0;i<MODEL_DIM;i++)s+=g_w[i]*z[i];return(s);}

bool ScheduledExitAllowed(const datetime entry_time)
  {
   MqlDateTime a,b;TimeToStruct(entry_time,a);datetime exit_time=entry_time+LABEL_HORIZON*PeriodSeconds(PERIOD_H1);TimeToStruct(exit_time,b);
   if(a.day_of_week==0||a.day_of_week==6||b.day_of_week==0||b.day_of_week==6||DayKey(entry_time)!=DayKey(exit_time))return(false);
   int limit=(a.day_of_week==5?InpFridayFlatHour*60+InpFridayFlatMinute:InpDailyFlatHour*60+InpDailyFlatMinute);return(b.hour*60+b.min<=limit);
  }

bool BuildModelSignal(const datetime now,const MqlTick &q,ModelSignal &signal)
  {
   ZeroMemory(signal);const int slot=(int)(g_bar_sequence%LABEL_HORIZON);double current_open=iOpen(_Symbol,PERIOD_H1,0);MatureStoredSample(slot,now,current_open);
   double raw[FEATURE_COUNT],z[MODEL_DIM],atr14=0,spread_points=0,spread_return=0,baseline=0,bar_open=0;
   bool valid=LoadRawFeatures(q,bar_open,atr14,spread_points,spread_return,baseline,raw);
   if(!valid){g_sample_valid[slot]=false;g_bar_sequence++;return(false);}StandardizePastOnly(raw,z);
   bool ready=(g_valid_observations>=InpWarmupBars);double model_score=(ready?ModelScore(z):0.0);double score=(InpUseOnlineRidge?model_score:baseline);double mid=(q.ask+q.bid)*0.5;double hurdle=InpCostSafetyMultiplier*(spread_return+InpCommissionReturn+InpSlippageReturn);
   if(!ready)g_warmup_bars++;else
     {
      g_predictions++;signal.score=score;signal.hurdle=hurdle;signal.atr14=atr14;signal.baseline_score=baseline;signal.spread_points=spread_points;signal.decision_time=now;
      if(spread_points>InpMaxSpreadPoints)g_spread_rejects++;
      else if(score>hurdle){signal.fired=true;signal.direction=1;g_long_signals++;}
      else if(score<-hurdle){signal.fired=true;signal.direction=-1;g_short_signals++;}
      else g_hurdle_rejects++;
     }
   UpdateStandardizer(raw);UpdateSpreadHistory(spread_return);g_valid_observations++;
   g_sample_valid[slot]=true;g_sample_open[slot]=bar_open;g_sample_time[slot]=now;for(int i=0;i<MODEL_DIM;i++)g_sample_z[slot][i]=z[i];g_samples_stored++;g_bar_sequence++;return(signal.fired);
  }

int VolumeDigits(const double s){int d=0;double v=s;while(d<8&&MathAbs(v-MathRound(v))>1e-9){v*=10.0;d++;}return(d);}
double NormalizeVolumeDown(const double v){double mn=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN),mx=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX),st=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);if(mn<=0||mx<mn||st<=0||v<mn)return(0);double u=MathFloor((MathMin(v,mx)-mn+1e-12)/st);return(NormalizeDouble(mn+u*st,VolumeDigits(st)));}
bool OwnedPosition(ulong &ticket){ticket=0;int n=0;for(int i=PositionsTotal()-1;i>=0;i--){ulong x=PositionGetTicket(i);if(x>0&&PositionSelectByTicket(x)&&PositionGetString(POSITION_SYMBOL)==_Symbol&&PositionGetInteger(POSITION_MAGIC)==InpMagic){ticket=x;n++;}}if(n>1)g_runtime_failed=true;return(n==1);}
bool AnySymbolExposure(){for(int i=PositionsTotal()-1;i>=0;i--){ulong x=PositionGetTicket(i);if(x>0&&PositionSelectByTicket(x)&&PositionGetString(POSITION_SYMBOL)==_Symbol)return(true);}return(false);}
void RefreshRiskLocks(const datetime now){double e=AccountInfoDouble(ACCOUNT_EQUITY);int d=DayKey(now);long w=WeekKey(now);if(d!=g_day_key){g_day_key=d;g_day_start_equity=e;g_day_locked=false;}if(w!=g_week_key){g_week_key=w;g_week_start_equity=e;g_week_locked=false;}if(g_day_start_equity>0&&e<=g_day_start_equity*(1-InpDailyLossPct/100.0))g_day_locked=true;if(g_week_start_equity>0&&e<=g_week_start_equity*(1-InpWeeklyLossPct/100.0))g_week_locked=true;}
bool CloseOwned(const string reason){ulong t=0;if(!OwnedPosition(t))return(true);g_close_attempts++;g_pending_exit_reason=reason;if(!g_trade.PositionClose(t,InpDeviationPoints)){g_close_rejects++;return(false);}uint c=g_trade.ResultRetcode();if(c!=TRADE_RETCODE_DONE&&c!=TRADE_RETCODE_DONE_PARTIAL){g_close_rejects++;return(false);}g_closes++;return(true);}

void ManagePosition(const datetime now,const datetime bar_open,const bool new_bar)
  {
   ulong t=0;if(!OwnedPosition(t))return;if(PositionSelectByTicket(t)){MqlTick q;if(SymbolInfoTick(_Symbol,q)){bool is_long=((ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_BUY);double point=SymbolInfoDouble(_Symbol,SYMBOL_POINT),quote=(is_long?q.bid:q.ask),fav=(is_long?quote-g_entry_price:g_entry_price-quote);if(point>0){g_mfe_points=MathMax(g_mfe_points,MathMax(0.0,fav)/point);g_mae_points=MathMax(g_mae_points,MathMax(0.0,-fav)/point);}}}
   MqlDateTime p;TimeToStruct(now,p);int m=p.hour*60+p.min;string reason="";
   if(p.day_of_week==5&&m>=InpFridayFlatHour*60+InpFridayFlatMinute)reason="FRIDAY_FLAT";else if(m>=InpDailyFlatHour*60+InpDailyFlatMinute)reason="DAILY_FLAT";else if(new_bar&&g_entry_time>0&&bar_open-g_entry_time>=LABEL_HORIZON*PeriodSeconds(PERIOD_H1))reason="FIXED_HORIZON";
   if(reason==""||g_last_close_attempt_bar==bar_open)return;g_last_close_attempt_bar=bar_open;CloseOwned(reason);
  }

bool SubmitEntry(const ModelSignal &s)
  {
   if(!s.fired)return(false);if(AnySymbolExposure()){g_exposure_skips++;return(false);}if(!ScheduledExitAllowed(s.decision_time)){g_schedule_rejects++;return(false);}if(g_day_locked||g_week_locked){g_risk_lock_skips++;return(false);}
   MqlTick q;if(!SymbolInfoTick(_Symbol,q)||q.ask<=q.bid)return(false);double point=SymbolInfoDouble(_Symbol,SYMBOL_POINT),tick=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE),contract=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_CONTRACT_SIZE),pip=PipSize();if(point<=0||tick<=0||contract<=0||pip<=0)return(false);
   double spread=(q.ask-q.bid)/point;if(spread>InpMaxSpreadPoints){g_spread_rejects++;return(false);}double entry=(s.direction>0?q.ask:q.bid);double dist=MathMax(InpSLMinPips*pip,MathMin(InpSLATRMult*s.atr14,InpSLMaxPips*pip));double sl=(s.direction>0?FloorToTick(entry-dist,tick):CeilToTick(entry+dist,tick));ENUM_ORDER_TYPE type=(s.direction>0?ORDER_TYPE_BUY:ORDER_TYPE_SELL);
   double loss1=0,margin1=0;if(!OrderCalcProfit(type,_Symbol,1,entry,sl,loss1)||loss1>=0||!OrderCalcMargin(type,_Symbol,1,entry,margin1)||margin1<=0)return(false);double eq=AccountInfoDouble(ACCOUNT_EQUITY),free=AccountInfoDouble(ACCOUNT_MARGIN_FREE);double vr=eq*(InpRiskPercent/100.0)/MathAbs(loss1),vn=(eq*InpMaxNotionalMult)/(entry*contract),vm=(free*(InpMaxMarginUsagePct/100.0))/margin1;double volume=NormalizeVolumeDown(MathMin(vr,MathMin(vn,vm)));if(volume<=0)return(false);
   double margin=0;if(!OrderCalcMargin(type,_Symbol,volume,entry,margin))return(false);double notional=volume*entry*contract;if(margin>free*InpMaxMarginUsagePct/100.0+.01||notional>eq*InpMaxNotionalMult+.01)return(false);
   g_trade.SetExpertMagicNumber(InpMagic);g_trade.LogLevel(LOG_LEVEL_NO);g_trade.SetDeviationInPoints(InpDeviationPoints);g_trade.SetTypeFillingBySymbol(_Symbol);bool sent=g_trade.PositionOpen(_Symbol,type,volume,entry,sl,0.0,InpVariantTag);uint c=g_trade.ResultRetcode();if(!sent||(c!=TRADE_RETCODE_DONE&&c!=TRADE_RETCODE_DONE_PARTIAL)){g_entry_rejects++;return(false);}
   g_entries++;g_entry_time=s.decision_time;g_entry_price=(g_trade.ResultPrice()>0?g_trade.ResultPrice():entry);g_initial_sl=sl;g_initial_risk_price=MathAbs(g_entry_price-sl);g_entry_risk_cash=MathAbs(loss1)*volume;g_entry_margin_pct=100.0*margin/free;g_mfe_points=0;g_mae_points=0;g_pending_exit_reason="";
   PrintFormat("ORLS002_ENTRY decision=%I64d direction=%s volume=%.2f entry=%.5f sl=%.5f score=%.9f hurdle=%.9f baseline=%.9f atr14=%.6f spread_points=%.1f risk_cash=%.2f margin_usage_pct=%.4f",(long)s.decision_time,(s.direction>0?"LONG":"SHORT"),volume,g_entry_price,sl,s.score,s.hurdle,s.baseline_score,s.atr14,spread,g_entry_risk_cash,g_entry_margin_pct);return(true);
  }

string ExitReasonName(const long r){if(r==DEAL_REASON_SL)return("CATASTROPHE_SL");if(r==DEAL_REASON_TP)return("TP_UNEXPECTED");if(r==DEAL_REASON_EXPERT&&g_pending_exit_reason!="")return(g_pending_exit_reason);return(StringFormat("DEAL_REASON_%d",(int)r));}
void OnTradeTransaction(const MqlTradeTransaction &tr,const MqlTradeRequest &rq,const MqlTradeResult &rs)
  {
   if(tr.type!=TRADE_TRANSACTION_DEAL_ADD||tr.deal==0||!HistoryDealSelect(tr.deal))return;if(HistoryDealGetString(tr.deal,DEAL_SYMBOL)!=_Symbol||HistoryDealGetInteger(tr.deal,DEAL_MAGIC)!=InpMagic)return;long k=HistoryDealGetInteger(tr.deal,DEAL_ENTRY);if(k!=DEAL_ENTRY_OUT&&k!=DEAL_ENTRY_OUT_BY)return;
   long reason=HistoryDealGetInteger(tr.deal,DEAL_REASON);if(reason==DEAL_REASON_SL)g_catastrophe_stops++;double profit=HistoryDealGetDouble(tr.deal,DEAL_PROFIT),com=HistoryDealGetDouble(tr.deal,DEAL_COMMISSION),swap=HistoryDealGetDouble(tr.deal,DEAL_SWAP),net=profit+com+swap;datetime t=(datetime)HistoryDealGetInteger(tr.deal,DEAL_TIME);double realized_r=(g_entry_risk_cash>0?net/g_entry_risk_cash:0.0);
   PrintFormat("ORLS002_EXIT time=%I64d reason=%s profit=%.2f commission=%.2f swap=%.2f net=%.2f realized_r=%.6f mfe_points=%.1f mae_points=%.1f bars_held=%d",(long)t,ExitReasonName(reason),profit,com,swap,net,realized_r,g_mfe_points,g_mae_points,(g_entry_time>0?iBarShift(_Symbol,PERIOD_H1,g_entry_time,false):-1));ulong ticket=0;if(!OwnedPosition(ticket)){g_entry_time=0;g_entry_price=0;g_initial_sl=0;g_initial_risk_price=0;g_entry_risk_cash=0;g_entry_margin_pct=0;g_pending_exit_reason="";}
  }

bool InputsAreFrozen()
  {
   bool variant=((InpVariantTag==PRIMARY_VARIANT&&InpUseOnlineRidge)||(InpVariantTag==CONTROL_VARIANT&&!InpUseOnlineRidge));return(InpResearchAutoMode&&InpEnableTelemetry&&InpHypothesisId==EXPECTED_HYPOTHESIS&&variant&&MathAbs(InpForgettingFactor-.9975)<1e-12&&MathAbs(InpRidgeAlpha-1.0)<1e-12&&MathAbs(InpStandardizerBeta-.9975)<1e-12&&InpWarmupBars==120&&MathAbs(InpVarianceFloor-.00000001)<1e-15&&MathAbs(InpCostSafetyMultiplier-1.5)<1e-12&&MathAbs(InpCommissionReturn-.00008)<1e-12&&MathAbs(InpSlippageReturn-.00005)<1e-12&&InpATRPeriod==14&&MathAbs(InpSLATRMult-3.0)<1e-12&&MathAbs(InpSLMinPips-25.0)<1e-12&&MathAbs(InpSLMaxPips-80.0)<1e-12&&MathAbs(InpRiskPercent-.25)<1e-12&&MathAbs(InpMaxNotionalMult-3.0)<1e-12&&MathAbs(InpMaxMarginUsagePct-9.0)<1e-12&&InpMaxSpreadPoints==15&&MathAbs(InpDailyLossPct-1.0)<1e-12&&MathAbs(InpWeeklyLossPct-2.5)<1e-12&&InpDailyFlatHour==21&&InpDailyFlatMinute==50&&InpFridayFlatHour==18&&InpFridayFlatMinute==50&&InpDeviationPoints==5&&InpMagic==5605502);
  }

int OnInit()
  {
   if(_Symbol!="EURUSD"||_Period!=PERIOD_H1||!InputsAreFrozen())return(INIT_PARAMETERS_INCORRECT);if(!EmitSeriesProof())return(INIT_FAILED);InitializeModel();g_trade.SetExpertMagicNumber(InpMagic);g_trade.LogLevel(LOG_LEVEL_NO);g_trade.SetDeviationInPoints(InpDeviationPoints);g_trade.SetTypeFillingBySymbol(_Symbol);datetime now=TimeCurrent();double e=AccountInfoDouble(ACCOUNT_EQUITY);g_day_key=DayKey(now);g_week_key=WeekKey(now);g_day_start_equity=e;g_week_start_equity=e;if(!CurrentBarOpen(g_last_bar_open))return(INIT_FAILED);PrintFormat("ORLS002_INIT ea=%s hypothesis=%s variant=%s symbol=%s timeframe=H1 online=%s",EA_NAME,InpHypothesisId,InpVariantTag,_Symbol,(InpUseOnlineRidge?"true":"false"));return(INIT_SUCCEEDED);
  }
void OnDeinit(const int reason)
  {
   PrintFormat("ORLS002_SUMMARY reason=%d runtime_failed=%s bars=%I64d valid=%I64d warmup=%I64d predictions=%I64d rls_updates=%I64d p_resets=%I64d samples=%I64d label_gaps=%I64d skip_missing=%I64d skip_nonfinite=%I64d long=%I64d short=%I64d hurdle_rejects=%I64d schedule_rejects=%I64d spread_rejects=%I64d risk_lock_skips=%I64d exposure_skips=%I64d entries=%I64d entry_rejects=%I64d closes=%I64d close_rejects=%I64d catastrophe_stops=%I64d",reason,(g_runtime_failed?"true":"false"),g_bar_sequence,g_valid_observations,g_warmup_bars,g_predictions,g_rls_updates,g_p_resets,g_samples_stored,g_labels_gap,g_skip_missing,g_skip_nonfinite,g_long_signals,g_short_signals,g_hurdle_rejects,g_schedule_rejects,g_spread_rejects,g_risk_lock_skips,g_exposure_skips,g_entries,g_entry_rejects,g_closes,g_close_rejects,g_catastrophe_stops);
  }
void OnTick()
  {
   datetime bar=0;if(!CurrentBarOpen(bar))return;datetime now=TimeCurrent();RefreshRiskLocks(now);const bool new_bar=(bar!=g_last_bar_open);ManagePosition(now,bar,new_bar);if(!new_bar)return;g_last_bar_open=bar;MqlTick q;if(!SymbolInfoTick(_Symbol,q))return;ModelSignal s;if(BuildModelSignal(bar,q,s)&&s.fired)SubmitEntry(s);
  }

