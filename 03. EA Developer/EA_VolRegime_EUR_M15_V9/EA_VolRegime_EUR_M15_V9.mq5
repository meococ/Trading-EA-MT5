//+------------------------------------------------------------------+
//| EA_VolRegime_EUR_M15_V9.mq5                                    |
//| HYP-VRE-EURUSD-M15-001: volatility regime expansion impulse     |
//+------------------------------------------------------------------+
#property strict
#property version "1.00"
#property description "Untuned closed-bar EURUSD M15 volatility-regime expansion EA"
#include <Trade/Trade.mqh>

input group "--- Frozen authority ---"
input bool InpResearchAutoMode=false;
input bool InpEnableTelemetry=true;
input string InpHypothesisId="HYP-VRE-EURUSD-M15-001";
input string InpVariantTag="CONFIRM_PRIMARY";
input bool InpRequireConfirmation=true;

input group "--- Frozen volatility signal ---"
input int InpATRFastPeriod=8;
input int InpATRSlowPeriod=40;
input int InpWarmupBars=50;
input double InpVolRatioThreshold=1.55;
input double InpBodyMinRatio=0.55;
input double InpConfirmReverseMaxATR=0.30;

input group "--- Frozen exits and risk ---"
input double InpSLATRMult=1.60;
input double InpMinSLPips=11.0;
input double InpMaxSLPips=28.0;
input double InpBETriggerR=0.90;
input double InpBEOffsetPips=0.80;
input double InpTrailStartR=1.40;
input double InpTrailPips=7.0;
input int InpTimeStopBars=10;
input double InpRiskPercent=0.25;
input double InpMaxNotionalMult=3.50;
input double InpMaxMarginUsagePct=10.0;
input int InpMaxSpreadPoints=15;
input double InpDailyLossPct=1.00;
input double InpWeeklyLossPct=2.50;
input int InpDailyFlatHour=21;
input int InpDailyFlatMinute=40;
input int InpFridayFlatHour=18;
input int InpFridayFlatMinute=40;
input int InpDeviationPoints=7;
input long InpMagic=5605501;

const string EA_NAME="EA_VolRegime_EUR_M15_V9";
const string EXPECTED_HYPOTHESIS="HYP-VRE-EURUSD-M15-001";
const string PRIMARY_VARIANT="CONFIRM_PRIMARY";
const string CONTROL_VARIANT="DIRECT_EXPANSION_CONTROL";

enum ExpansionState { NEUTRAL=0, EXPANSION_DETECTED=1, IN_POSITION=2 };

struct EntrySignal
  {
   bool fired;datetime decision_time,availability_time,expansion_time;int direction;
   double atr_fast,atr_slow,vol_ratio,expansion_vol_ratio,body_ratio,expansion_close,reversal_atr;
  };

CTrade g_trade;
ExpansionState g_state=NEUTRAL;
datetime g_last_bar_open=0,g_expansion_time=0,g_entry_time=0,g_last_close_attempt_bar=0;
int g_exp_direction=0,g_warmup=0;
double g_exp_close=0.0,g_exp_atr_fast=0.0,g_exp_vol_ratio=0.0;
double g_entry_price=0.0,g_initial_sl=0.0,g_initial_risk=0.0,g_mfe_points=0.0,g_mae_points=0.0,g_entry_margin_usage_pct=0.0;
bool g_trail_armed=false,g_day_locked=false,g_week_locked=false,g_runtime_failed=false;string g_pending_exit_reason="";
int g_day_key=0;long g_week_key=0;double g_day_start_equity=0.0,g_week_start_equity=0.0;

long g_closed_bars=0,g_warmup_skips=0,g_expansions=0,g_confirmations=0,g_confirm_failures=0,g_signals=0,g_long_signals=0,g_short_signals=0;
long g_spread_rejects=0,g_risk_lock_skips=0,g_exposure_skips=0,g_entries=0,g_entry_rejects=0,g_be_moves=0,g_trail_arms=0,g_trail_moves=0;
long g_close_attempts=0,g_close_rejects=0,g_closes=0,g_invalid_inputs=0;

bool IsFinite(const double v){return(v!=EMPTY_VALUE&&MathIsValidNumber(v));}
int DayKey(const datetime t){MqlDateTime p;TimeToStruct(t,p);return(p.year*10000+p.mon*100+p.day);}
long WeekKey(const datetime t){MqlDateTime p;TimeToStruct(t,p);datetime s=t-p.hour*3600-p.min*60-p.sec;return((long)(s-((p.day_of_week+6)%7)*86400)/604800);}
double PipSize(){const int d=(int)SymbolInfoInteger(_Symbol,SYMBOL_DIGITS);const double p=SymbolInfoDouble(_Symbol,SYMBOL_POINT);return((d==3||d==5)?10.0*p:p);}
double FloorToTick(const double p,const double t){return(MathFloor(p/t+1e-10)*t);}
double CeilToTick(const double p,const double t){return(MathCeil(p/t-1e-10)*t);}
bool CurrentBarOpen(datetime &bar_open){long raw=0;bar_open=0;if(!SeriesInfoInteger(_Symbol,PERIOD_M15,SERIES_LASTBAR_DATE,raw)||raw<=0)return(false);bar_open=(datetime)raw;return(true);}

bool EmitSeriesProof()
  {
   long sync=0,m5first=0,m5terminal=0,m1server=0,m1terminal=0,bars=0;if(!SeriesInfoInteger(_Symbol,PERIOD_M5,SERIES_SYNCHRONIZED,sync)||!SeriesInfoInteger(_Symbol,PERIOD_M5,SERIES_FIRSTDATE,m5first)||!SeriesInfoInteger(_Symbol,PERIOD_M5,SERIES_TERMINAL_FIRSTDATE,m5terminal)||!SeriesInfoInteger(_Symbol,PERIOD_M1,SERIES_SERVER_FIRSTDATE,m1server)||!SeriesInfoInteger(_Symbol,PERIOD_M1,SERIES_TERMINAL_FIRSTDATE,m1terminal)||!SeriesInfoInteger(_Symbol,PERIOD_M5,SERIES_BARS_COUNT,bars))return(false);ResetLastError();const long maxbars=TerminalInfoInteger(TERMINAL_MAXBARS);const int terr=GetLastError();datetime a[];ArraySetAsSeries(a,false);ResetLastError();const int n=CopyTime(_Symbol,PERIOD_M5,(datetime)m5first,1,a);const int err=GetLastError();const long first=(n==1?(long)a[0]:0);PrintFormat("DATA_EPOCH_D0_SERIES_PROOF symbol=%s m5_synchronized=%I64d m5_first_epoch=%I64d m5_terminal_first_epoch=%I64d m1_server_first_epoch=%I64d m1_terminal_first_epoch=%I64d m5_bars=%I64d terminal_maxbars=%I64d copytime_from_epoch=%I64d copytime_count=1 copytime_result=%d copytime_first_epoch=%I64d copytime_last_error=%d",_Symbol,sync,m5first,m5terminal,m1server,m1terminal,bars,maxbars,m5first,n,first,err);return(sync==1&&m5first>0&&m5terminal>0&&m1server>0&&m1terminal>0&&bars>0&&maxbars>0&&terr==0&&n==1&&first==m5first&&err==0);
  }

bool LoadClosedFeatures(MqlRates &bar,double &atr_fast,double &atr_slow,double &vol_ratio,double &body_ratio)
  {
   bar.time=0;atr_fast=0;atr_slow=0;vol_ratio=0;body_ratio=0;if(Bars(_Symbol,PERIOD_M15)<InpWarmupBars){g_invalid_inputs++;return(false);}MqlRates r[];ArraySetAsSeries(r,true);const int need=InpATRSlowPeriod+1;if(CopyRates(_Symbol,PERIOD_M15,1,need,r)!=need){g_invalid_inputs++;return(false);}bar=r[0];double range=bar.high-bar.low;if(bar.time<=0||bar.open<=0||bar.close<=0||range<=0){g_invalid_inputs++;return(false);}
   double fast=0,slow=0;for(int i=0;i<InpATRSlowPeriod;i++){double prev=r[i+1].close;if(prev<=0||r[i].high<=r[i].low){g_invalid_inputs++;return(false);}double tr=MathMax(r[i].high-r[i].low,MathMax(MathAbs(r[i].high-prev),MathAbs(r[i].low-prev)));slow+=tr;if(i<InpATRFastPeriod)fast+=tr;}atr_fast=fast/InpATRFastPeriod;atr_slow=slow/InpATRSlowPeriod;if(!IsFinite(atr_fast)||!IsFinite(atr_slow)||atr_fast<=0||atr_slow<=0){g_invalid_inputs++;return(false);}vol_ratio=atr_fast/atr_slow;body_ratio=MathAbs(bar.close-bar.open)/range;return(IsFinite(vol_ratio)&&IsFinite(body_ratio));
  }

void ResetExpansion(){g_state=NEUTRAL;g_expansion_time=0;g_exp_direction=0;g_exp_close=0;g_exp_atr_fast=0;g_exp_vol_ratio=0;}

void FillSignal(EntrySignal &s,const MqlRates &bar,const datetime availability,const double af,const double as,const double vr,const double br,const bool control)
  {
   ZeroMemory(s);s.fired=true;s.decision_time=bar.time;s.availability_time=availability;s.expansion_time=g_expansion_time;s.direction=g_exp_direction;s.atr_fast=af;s.atr_slow=as;s.vol_ratio=vr;s.expansion_vol_ratio=g_exp_vol_ratio;s.body_ratio=br;s.expansion_close=g_exp_close;s.reversal_atr=(g_exp_direction>0?(g_exp_close-bar.close)/af:(bar.close-g_exp_close)/af);g_signals++;if(s.direction>0)g_long_signals++;else g_short_signals++;if(InpEnableTelemetry)PrintFormat("VRE001_SIGNAL decision=%I64d availability=%I64d direction=%s control=%s atr_fast=%.6f atr_slow=%.6f vol_ratio=%.6f expansion_ratio=%.6f body_ratio=%.6f reversal_atr=%.6f",(long)bar.time,(long)availability,(s.direction>0?"LONG":"SHORT"),(control?"true":"false"),af,as,vr,g_exp_vol_ratio,br,s.reversal_atr);
  }

bool BuildSignal(const datetime availability,EntrySignal &signal)
  {
   ZeroMemory(signal);MqlRates bar;double af,as,vr,br;if(!LoadClosedFeatures(bar,af,as,vr,br))return(false);g_closed_bars++;if((long)(availability-bar.time)!=PeriodSeconds(PERIOD_M15)){g_invalid_inputs++;return(false);}if(g_warmup<InpWarmupBars){g_warmup++;g_warmup_skips++;return(false);}if(g_state==IN_POSITION)return(false);
   if(g_state==EXPANSION_DETECTED)
     {
      if(bar.time<=g_expansion_time)return(false);bool same=(g_exp_direction>0?bar.close>bar.open:bar.close<bar.open);double reverse=(g_exp_direction>0?g_exp_close-bar.close:bar.close-g_exp_close);bool limited=(reverse<=InpConfirmReverseMaxATR*af);
      if(same&&limited){g_confirmations++;FillSignal(signal,bar,availability,af,as,vr,br,false);return(true);}g_confirm_failures++;ResetExpansion();return(false);
     }
   int direction=(bar.close>bar.open?1:(bar.close<bar.open?-1:0));if(direction==0||vr<InpVolRatioThreshold||br<InpBodyMinRatio)return(false);g_state=EXPANSION_DETECTED;g_expansion_time=bar.time;g_exp_direction=direction;g_exp_close=bar.close;g_exp_atr_fast=af;g_exp_vol_ratio=vr;g_expansions++;if(InpEnableTelemetry)PrintFormat("VRE001_EXPANSION time=%I64d direction=%s atr_fast=%.6f atr_slow=%.6f vol_ratio=%.6f body_ratio=%.6f close=%.5f",(long)bar.time,(direction>0?"LONG":"SHORT"),af,as,vr,br,bar.close);if(!InpRequireConfirmation){FillSignal(signal,bar,availability,af,as,vr,br,true);return(true);}return(false);
  }

int VolumeDigits(const double s){int d=0;double v=s;while(d<8&&MathAbs(v-MathRound(v))>1e-9){v*=10.0;d++;}return(d);}
double NormalizeVolumeDown(const double v){double mn=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN),mx=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX),st=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);if(mn<=0||mx<mn||st<=0||v<mn)return(0);double u=MathFloor((MathMin(v,mx)-mn+1e-12)/st);return(NormalizeDouble(mn+u*st,VolumeDigits(st)));}
bool OwnedPosition(ulong &ticket){ticket=0;int n=0;for(int i=PositionsTotal()-1;i>=0;i--){ulong x=PositionGetTicket(i);if(x>0&&PositionSelectByTicket(x)&&PositionGetString(POSITION_SYMBOL)==_Symbol&&PositionGetInteger(POSITION_MAGIC)==InpMagic){ticket=x;n++;}}if(n>1)g_runtime_failed=true;return(n==1);}
bool AnySymbolExposure(){for(int i=PositionsTotal()-1;i>=0;i--){ulong x=PositionGetTicket(i);if(x>0&&PositionSelectByTicket(x)&&PositionGetString(POSITION_SYMBOL)==_Symbol)return(true);}return(false);}
void RefreshRiskLocks(const datetime now){double e=AccountInfoDouble(ACCOUNT_EQUITY);int d=DayKey(now);long w=WeekKey(now);if(d!=g_day_key){g_day_key=d;g_day_start_equity=e;g_day_locked=false;}if(w!=g_week_key){g_week_key=w;g_week_start_equity=e;g_week_locked=false;}if(g_day_start_equity>0&&e<=g_day_start_equity*(1-InpDailyLossPct/100.0))g_day_locked=true;if(g_week_start_equity>0&&e<=g_week_start_equity*(1-InpWeeklyLossPct/100.0))g_week_locked=true;}
bool CloseOwned(const string reason){ulong t=0;if(!OwnedPosition(t))return(true);g_close_attempts++;g_pending_exit_reason=reason;if(!g_trade.PositionClose(t,InpDeviationPoints)){g_close_rejects++;return(false);}uint c=g_trade.ResultRetcode();if(c!=TRADE_RETCODE_DONE&&c!=TRADE_RETCODE_DONE_PARTIAL){g_close_rejects++;return(false);}g_closes++;return(true);}

bool ModifyStop(const ulong ticket,const double proposed)
  {
   if(!PositionSelectByTicket(ticket))return(false);bool is_long=((ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_BUY);double current=PositionGetDouble(POSITION_SL);MqlTick q;if(!SymbolInfoTick(_Symbol,q))return(false);double point=SymbolInfoDouble(_Symbol,SYMBOL_POINT),tick=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);if(point<=0||tick<=0)return(false);double next=(is_long?FloorToTick(proposed,tick):CeilToTick(proposed,tick));if((is_long&&current>=next-point*.1)||(!is_long&&current>0&&current<=next+point*.1))return(false);double md=(double)MathMax(MathMax(SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL),SymbolInfoInteger(_Symbol,SYMBOL_TRADE_FREEZE_LEVEL)),0)*point;if((is_long&&q.bid-next<md)||(!is_long&&next-q.ask<md))return(false);if(!g_trade.PositionModify(ticket,next,0.0))return(false);uint c=g_trade.ResultRetcode();return(c==TRADE_RETCODE_DONE||c==TRADE_RETCODE_NO_CHANGES);
  }

void UpdatePositionPathAndStops(const ulong ticket)
  {
   if(!PositionSelectByTicket(ticket)||g_initial_risk<=0||g_entry_price<=0)return;bool is_long=((ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_BUY);MqlTick q;if(!SymbolInfoTick(_Symbol,q))return;double point=SymbolInfoDouble(_Symbol,SYMBOL_POINT),pip=PipSize();if(point<=0||pip<=0)return;double quote=(is_long?q.bid:q.ask),fav=(is_long?quote-g_entry_price:g_entry_price-quote);g_mfe_points=MathMax(g_mfe_points,MathMax(0.0,fav)/point);g_mae_points=MathMax(g_mae_points,MathMax(0.0,-fav)/point);if(fav>=InpBETriggerR*g_initial_risk){double be=(is_long?g_entry_price+InpBEOffsetPips*pip:g_entry_price-InpBEOffsetPips*pip);if(ModifyStop(ticket,be))g_be_moves++;}if(!g_trail_armed&&fav>=InpTrailStartR*g_initial_risk){g_trail_armed=true;g_trail_arms++;}if(g_trail_armed){double trail=(is_long?q.bid-InpTrailPips*pip:q.ask+InpTrailPips*pip);if(ModifyStop(ticket,trail))g_trail_moves++;}
  }

void ManagePosition(const datetime now,const datetime bar_open,const bool new_bar)
  {
   ulong t=0;if(!OwnedPosition(t))return;g_state=IN_POSITION;UpdatePositionPathAndStops(t);MqlDateTime p;TimeToStruct(now,p);int m=p.hour*60+p.min;string r="";if(p.day_of_week==5&&m>=InpFridayFlatHour*60+InpFridayFlatMinute)r="FRIDAY_FLAT";else if(m>=InpDailyFlatHour*60+InpDailyFlatMinute)r="DAILY_FLAT";else if(new_bar){datetime s=g_entry_time;if(s<=0&&PositionSelectByTicket(t))s=(datetime)PositionGetInteger(POSITION_TIME);if(s>0&&iBarShift(_Symbol,PERIOD_M15,s,false)>=InpTimeStopBars)r="TIME_STOP";}if(r==""||g_last_close_attempt_bar==bar_open)return;g_last_close_attempt_bar=bar_open;CloseOwned(r);
  }

bool EntryTimeAllowed(const datetime t){MqlDateTime p;TimeToStruct(t,p);if(p.day_of_week==0||p.day_of_week==6)return(false);int m=p.hour*60+p.min;if(m>=InpDailyFlatHour*60+InpDailyFlatMinute)return(false);if(p.day_of_week==5&&m>=InpFridayFlatHour*60+InpFridayFlatMinute)return(false);return(true);}

bool SubmitEntry(const EntrySignal &s)
  {
   if(!s.fired||AnySymbolExposure()||!EntryTimeAllowed(s.availability_time)){g_exposure_skips++;ResetExpansion();return(false);}if(g_day_locked||g_week_locked){g_risk_lock_skips++;ResetExpansion();return(false);}MqlTick q;if(!SymbolInfoTick(_Symbol,q)||q.ask<=q.bid)return(false);double point=SymbolInfoDouble(_Symbol,SYMBOL_POINT),pip=PipSize(),tick=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE),contract=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_CONTRACT_SIZE);if(point<=0||pip<=0||tick<=0||contract<=0)return(false);double spread=(q.ask-q.bid)/point;if(spread>InpMaxSpreadPoints){g_spread_rejects++;ResetExpansion();return(false);}double entry=(s.direction>0?q.ask:q.bid),dist=MathMax(InpMinSLPips*pip,MathMin(InpSLATRMult*s.atr_fast,InpMaxSLPips*pip));double sl=(s.direction>0?FloorToTick(entry-dist,tick):CeilToTick(entry+dist,tick));ENUM_ORDER_TYPE type=(s.direction>0?ORDER_TYPE_BUY:ORDER_TYPE_SELL);double loss=0,margin1=0;if(!OrderCalcProfit(type,_Symbol,1,entry,sl,loss)||loss>=0)return(false);if(!OrderCalcMargin(type,_Symbol,1,entry,margin1)||margin1<=0)return(false);
   double eq=AccountInfoDouble(ACCOUNT_EQUITY),free=AccountInfoDouble(ACCOUNT_MARGIN_FREE);double vr=eq*(InpRiskPercent/100.0)/MathAbs(loss),vn=(eq*InpMaxNotionalMult)/(entry*contract),vm=(free*(InpMaxMarginUsagePct/100.0))/margin1;double volume=NormalizeVolumeDown(MathMin(vr,MathMin(vn,vm)));if(volume<=0)return(false);double margin=0;if(!OrderCalcMargin(type,_Symbol,volume,entry,margin))return(false);double notional=volume*entry*contract;if(margin>free*InpMaxMarginUsagePct/100.0+.01||notional>eq*InpMaxNotionalMult+.01)return(false);
   g_trade.SetExpertMagicNumber(InpMagic);g_trade.LogLevel(LOG_LEVEL_NO);g_trade.SetDeviationInPoints(InpDeviationPoints);g_trade.SetTypeFillingBySymbol(_Symbol);bool sent=g_trade.PositionOpen(_Symbol,type,volume,entry,sl,0.0,InpVariantTag);uint c=g_trade.ResultRetcode();if(!sent||(c!=TRADE_RETCODE_DONE&&c!=TRADE_RETCODE_DONE_PARTIAL)){g_entry_rejects++;ResetExpansion();return(false);}g_entries++;g_state=IN_POSITION;g_entry_time=s.availability_time;g_entry_price=(g_trade.ResultPrice()>0?g_trade.ResultPrice():entry);g_initial_sl=sl;g_initial_risk=MathAbs(g_entry_price-sl);g_entry_margin_usage_pct=100*margin/free;g_mfe_points=0;g_mae_points=0;g_trail_armed=false;g_pending_exit_reason="";PrintFormat("VRE001_ENTRY decision=%I64d direction=%s volume=%.2f entry=%.5f sl=%.5f risk=%.5f vol_ratio=%.6f expansion_ratio=%.6f reversal_atr=%.6f spread_points=%.1f volume_risk=%.4f volume_notional=%.4f volume_margin=%.4f notional_mult=%.4f margin_usage_pct=%.4f",(long)s.decision_time,(s.direction>0?"LONG":"SHORT"),volume,g_entry_price,sl,g_initial_risk,s.vol_ratio,s.expansion_vol_ratio,s.reversal_atr,spread,vr,vn,vm,notional/eq,g_entry_margin_usage_pct);return(true);
  }

string ExitReasonName(const long r){if(r==DEAL_REASON_SL)return("SL");if(r==DEAL_REASON_TP)return("TP_UNEXPECTED");if(r==DEAL_REASON_EXPERT&&g_pending_exit_reason!="")return(g_pending_exit_reason);return(StringFormat("DEAL_REASON_%d",(int)r));}
void OnTradeTransaction(const MqlTradeTransaction &tr,const MqlTradeRequest &rq,const MqlTradeResult &rs)
  {
   if(tr.type!=TRADE_TRANSACTION_DEAL_ADD||tr.deal==0||!HistoryDealSelect(tr.deal))return;if(HistoryDealGetString(tr.deal,DEAL_SYMBOL)!=_Symbol||HistoryDealGetInteger(tr.deal,DEAL_MAGIC)!=InpMagic)return;long k=HistoryDealGetInteger(tr.deal,DEAL_ENTRY);if(k!=DEAL_ENTRY_OUT&&k!=DEAL_ENTRY_OUT_BY)return;long reason=HistoryDealGetInteger(tr.deal,DEAL_REASON);double price=HistoryDealGetDouble(tr.deal,DEAL_PRICE),profit=HistoryDealGetDouble(tr.deal,DEAL_PROFIT),com=HistoryDealGetDouble(tr.deal,DEAL_COMMISSION),swap=HistoryDealGetDouble(tr.deal,DEAL_SWAP);datetime t=(datetime)HistoryDealGetInteger(tr.deal,DEAL_TIME);PrintFormat("VRE001_EXIT time=%I64d reason=%s price=%.5f profit=%.2f commission=%.2f swap=%.2f net=%.2f mfe_points=%.1f mae_points=%.1f margin_usage_pct=%.4f bars_held=%d",(long)t,ExitReasonName(reason),price,profit,com,swap,profit+com+swap,g_mfe_points,g_mae_points,g_entry_margin_usage_pct,(g_entry_time>0?iBarShift(_Symbol,PERIOD_M15,g_entry_time,false):-1));ulong ticket=0;if(!OwnedPosition(ticket)){g_entry_time=0;g_entry_price=0;g_initial_sl=0;g_initial_risk=0;g_entry_margin_usage_pct=0;g_trail_armed=false;g_pending_exit_reason="";ResetExpansion();}
  }

bool InputsAreFrozen()
  {
   bool variant=((InpVariantTag==PRIMARY_VARIANT&&InpRequireConfirmation)||(InpVariantTag==CONTROL_VARIANT&&!InpRequireConfirmation));return(InpResearchAutoMode&&InpEnableTelemetry&&InpHypothesisId==EXPECTED_HYPOTHESIS&&variant&&InpATRFastPeriod==8&&InpATRSlowPeriod==40&&InpWarmupBars==50&&MathAbs(InpVolRatioThreshold-1.55)<1e-12&&MathAbs(InpBodyMinRatio-.55)<1e-12&&MathAbs(InpConfirmReverseMaxATR-.30)<1e-12&&MathAbs(InpSLATRMult-1.6)<1e-12&&MathAbs(InpMinSLPips-11)<1e-12&&MathAbs(InpMaxSLPips-28)<1e-12&&MathAbs(InpBETriggerR-.9)<1e-12&&MathAbs(InpBEOffsetPips-.8)<1e-12&&MathAbs(InpTrailStartR-1.4)<1e-12&&MathAbs(InpTrailPips-7)<1e-12&&InpTimeStopBars==10&&MathAbs(InpRiskPercent-.25)<1e-12&&MathAbs(InpMaxNotionalMult-3.5)<1e-12&&MathAbs(InpMaxMarginUsagePct-10)<1e-12&&InpMaxSpreadPoints==15&&MathAbs(InpDailyLossPct-1)<1e-12&&MathAbs(InpWeeklyLossPct-2.5)<1e-12&&InpDailyFlatHour==21&&InpDailyFlatMinute==40&&InpFridayFlatHour==18&&InpFridayFlatMinute==40&&InpDeviationPoints==7&&InpMagic==5605501);
  }

int OnInit(){if(_Symbol!="EURUSD"||_Period!=PERIOD_M15||!InputsAreFrozen())return(INIT_PARAMETERS_INCORRECT);if(!EmitSeriesProof())return(INIT_FAILED);g_trade.SetExpertMagicNumber(InpMagic);g_trade.LogLevel(LOG_LEVEL_NO);g_trade.SetDeviationInPoints(InpDeviationPoints);g_trade.SetTypeFillingBySymbol(_Symbol);datetime now=TimeCurrent();double e=AccountInfoDouble(ACCOUNT_EQUITY);g_day_key=DayKey(now);g_week_key=WeekKey(now);g_day_start_equity=e;g_week_start_equity=e;if(!CurrentBarOpen(g_last_bar_open))return(INIT_FAILED);PrintFormat("VRE001_INIT ea=%s hypothesis=%s variant=%s symbol=%s timeframe=M15 require_confirmation=%s",EA_NAME,InpHypothesisId,InpVariantTag,_Symbol,(InpRequireConfirmation?"true":"false"));return(INIT_SUCCEEDED);}
void OnDeinit(const int reason){PrintFormat("VRE001_SUMMARY reason=%d runtime_failed=%s closed_bars=%I64d warmup_skips=%I64d expansions=%I64d confirmations=%I64d confirm_failures=%I64d signals=%I64d long=%I64d short=%I64d spread_rejects=%I64d risk_lock_skips=%I64d exposure_skips=%I64d entries=%I64d entry_rejects=%I64d be_moves=%I64d trail_arms=%I64d trail_moves=%I64d close_attempts=%I64d close_rejects=%I64d closes=%I64d invalid=%I64d",reason,(g_runtime_failed?"true":"false"),g_closed_bars,g_warmup_skips,g_expansions,g_confirmations,g_confirm_failures,g_signals,g_long_signals,g_short_signals,g_spread_rejects,g_risk_lock_skips,g_exposure_skips,g_entries,g_entry_rejects,g_be_moves,g_trail_arms,g_trail_moves,g_close_attempts,g_close_rejects,g_closes,g_invalid_inputs);}
void OnTick(){datetime bar=0;if(!CurrentBarOpen(bar))return;datetime now=TimeCurrent();RefreshRiskLocks(now);const bool new_bar=(bar!=g_last_bar_open);ManagePosition(now,bar,new_bar);if(!new_bar)return;g_last_bar_open=bar;if(AnySymbolExposure())return;EntrySignal s;if(BuildSignal(bar,s)&&s.fired)SubmitEntry(s);}
