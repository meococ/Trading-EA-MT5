//+------------------------------------------------------------------+
//| EA_FixReversal_EUR_M5_V11.mq5                                  |
//| HYP-WMRR-EURUSD-M5-001: post-WMR fixing-window reversal         |
//+------------------------------------------------------------------+
#property strict
#property version "1.00"
#property description "Untuned EURUSD M5 post-WMR London-fix reversal EA"
#include <Trade/Trade.mqh>

input group "--- Frozen authority ---"
input bool   InpResearchAutoMode=false;
input bool   InpEnableTelemetry=true;
input string InpHypothesisId="HYP-WMRR-EURUSD-M5-001";
input string InpVariantTag="RETRACE_PRIMARY";
input bool   InpRequireRetracement=true;
input string InpClockConvention="US_DST_NY_CLOSE";

input group "--- Frozen WMR signal ---"
input int    InpNormalFixHour=18;
input int    InpMismatchFixHour=19;
input int    InpMeasurementBars=12;
input double InpMinFixMovePips=1.20;
input double InpRetracementFraction=0.35;
input int    InpMaxConfirmationBars=3;
input int    InpATRPeriod=14;

input group "--- Frozen exits and risk ---"
input double InpSLATRMult=1.90;
input double InpMinSLPips=12.0;
input double InpMaxSLPips=28.0;
input double InpTakeProfitR=1.40;
input int    InpTimeStopBars=18;
input double InpRiskPercent=0.20;
input double InpMaxNotionalMult=3.0;
input double InpMaxMarginUsagePct=9.0;
input int    InpMaxSpreadPoints=14;
input double InpDailyLossPct=0.90;
input double InpWeeklyLossPct=2.20;
input int    InpDailyFlatHour=21;
input int    InpDailyFlatMinute=50;
input int    InpFridayFlatHour=18;
input int    InpFridayFlatMinute=50;
input int    InpDeviationPoints=7;
input long   InpMagic=5605801;

const string EA_NAME="EA_FixReversal_EUR_M5_V11";
const string EXPECTED_HYPOTHESIS="HYP-WMRR-EURUSD-M5-001";
const string PRIMARY_VARIANT="RETRACE_PRIMARY";
const string CONTROL_VARIANT="IMMEDIATE_FADE_CONTROL";

enum FixState { NEUTRAL=0, FIX_OBSERVED=1, IN_POSITION=2 };

struct EntrySignal
  {
   bool fired;
   datetime decision_time,availability_time,fix_bar_open;
   int direction,confirmation_index,fix_hour;
   double atr,fix_close,fix_move,fix_move_pips,retrace_fraction;
  };

CTrade g_trade;
FixState g_state=NEUTRAL;
datetime g_last_bar_open=0,g_fix_bar_open=0,g_entry_time=0,g_last_close_attempt_bar=0;
int g_fix_dir=0,g_confirmation_index=0,g_day_key=0;long g_week_key=0;
double g_fix_close=0.0,g_fix_move=0.0,g_day_start_equity=0.0,g_week_start_equity=0.0;
double g_entry_price=0.0,g_initial_sl=0.0,g_initial_risk=0.0,g_entry_margin_usage_pct=0.0;
bool g_day_latched=false,g_day_locked=false,g_week_locked=false,g_runtime_failed=false;
string g_pending_exit_reason="";

long g_closed_bars=0,g_days_seen=0,g_fix18_days=0,g_fix19_days=0,g_contiguity_fails=0,g_small_move_days=0;
long g_fix_observed=0,g_confirmation_checks=0,g_confirmations=0,g_confirmation_expiries=0,g_signals=0;
long g_entries=0,g_entry_rejects=0,g_spread_cancels=0,g_stops_cancels=0,g_risk_cancels=0,g_exposure_cancels=0;
long g_close_attempts=0,g_close_rejects=0,g_closes=0,g_invalid_inputs=0;

bool IsFinite(const double v){return(v!=EMPTY_VALUE&&MathIsValidNumber(v));}
int DayKey(const datetime t){MqlDateTime p;TimeToStruct(t,p);return(p.year*10000+p.mon*100+p.day);}
long WeekKey(const datetime t){MqlDateTime p;TimeToStruct(t,p);datetime s=t-p.hour*3600-p.min*60-p.sec;return((long)(s-((p.day_of_week+6)%7)*86400)/604800);}
double PipSize(){const int d=(int)SymbolInfoInteger(_Symbol,SYMBOL_DIGITS);const double p=SymbolInfoDouble(_Symbol,SYMBOL_POINT);return((d==3||d==5)?10.0*p:p);}
double FloorToTick(const double p,const double t){return(MathFloor(p/t+1e-10)*t);}
double CeilToTick(const double p,const double t){return(MathCeil(p/t-1e-10)*t);}

datetime MakeDate(const int year,const int month,const int day){MqlDateTime p;ZeroMemory(p);p.year=year;p.mon=month;p.day=day;return(StructToTime(p));}
int FirstSunday(const int year,const int month){MqlDateTime p;TimeToStruct(MakeDate(year,month,1),p);return(1+((7-p.day_of_week)%7));}
int LastSunday(const int year,const int month){int nm=(month==12?1:month+1),ny=(month==12?year+1:year);datetime last=MakeDate(ny,nm,1)-86400;MqlDateTime p;TimeToStruct(last,p);return(p.day-p.day_of_week);}

bool IsUkUsDstMismatchDate(const datetime t)
  {
   MqlDateTime p;TimeToStruct(t,p);datetime d=MakeDate(p.year,p.mon,p.day);
   datetime us_start=MakeDate(p.year,3,FirstSunday(p.year,3)+7);
   datetime uk_start=MakeDate(p.year,3,LastSunday(p.year,3));
   datetime uk_end=MakeDate(p.year,10,LastSunday(p.year,10));
   datetime us_end=MakeDate(p.year,11,FirstSunday(p.year,11));
   return((d>=us_start&&d<uk_start)||(d>=uk_end&&d<us_end));
  }

int FixHourForDate(const datetime t){return(IsUkUsDstMismatchDate(t)?InpMismatchFixHour:InpNormalFixHour);}

bool EmitSeriesProof()
  {
   long sync=0,m5first=0,m5terminal=0,m1server=0,m1terminal=0,bars=0;
   if(!SeriesInfoInteger(_Symbol,PERIOD_M5,SERIES_SYNCHRONIZED,sync)||!SeriesInfoInteger(_Symbol,PERIOD_M5,SERIES_FIRSTDATE,m5first)||!SeriesInfoInteger(_Symbol,PERIOD_M5,SERIES_TERMINAL_FIRSTDATE,m5terminal)||!SeriesInfoInteger(_Symbol,PERIOD_M1,SERIES_SERVER_FIRSTDATE,m1server)||!SeriesInfoInteger(_Symbol,PERIOD_M1,SERIES_TERMINAL_FIRSTDATE,m1terminal)||!SeriesInfoInteger(_Symbol,PERIOD_M5,SERIES_BARS_COUNT,bars))return(false);
   const long maxbars=TerminalInfoInteger(TERMINAL_MAXBARS);datetime a[];ArraySetAsSeries(a,false);ResetLastError();const int n=CopyTime(_Symbol,PERIOD_M5,(datetime)m5first,1,a);const int err=GetLastError();const long copied=(n==1?(long)a[0]:0);
   PrintFormat("DATA_EPOCH_D0_SERIES_PROOF symbol=%s m5_synchronized=%I64d m5_first_epoch=%I64d m5_terminal_first_epoch=%I64d m1_server_first_epoch=%I64d m1_terminal_first_epoch=%I64d m5_bars=%I64d terminal_maxbars=%I64d copytime_from_epoch=%I64d copytime_count=1 copytime_result=%d copytime_first_epoch=%I64d copytime_last_error=%d",_Symbol,sync,m5first,m5terminal,m1server,m1terminal,bars,maxbars,m5first,n,copied,err);
   return(sync==1&&m5first>0&&m5terminal>0&&m1server>0&&m1terminal>0&&bars>0&&maxbars>0&&n==1&&copied==m5first&&err==0);
  }

bool CurrentBarOpen(datetime &bar_open){long raw=0;bar_open=0;if(!SeriesInfoInteger(_Symbol,PERIOD_M5,SERIES_LASTBAR_DATE,raw)||raw<=0)return(false);bar_open=(datetime)raw;return(true);}

bool LoadClosedRates(const int count,MqlRates &rates[])
  {
   ArraySetAsSeries(rates,true);const int n=CopyRates(_Symbol,PERIOD_M5,1,count,rates);
   if(n!=count){g_invalid_inputs++;return(false);}
   for(int i=0;i<count;i++)if(rates[i].time<=0||rates[i].open<=0||rates[i].close<=0||rates[i].high<rates[i].low){g_invalid_inputs++;return(false);}
   return(true);
  }

bool BarsContiguous(MqlRates &rates[])
  {
   for(int i=0;i<ArraySize(rates)-1;i++)if((long)(rates[i].time-rates[i+1].time)!=PeriodSeconds(PERIOD_M5))return(false);
   return(true);
  }

bool LoadATR(double &atr)
  {
   atr=0.0;MqlRates r[];if(!LoadClosedRates(InpATRPeriod+1,r))return(false);
   for(int i=0;i<InpATRPeriod;i++){double pc=r[i+1].close;double tr=MathMax(r[i].high-r[i].low,MathMax(MathAbs(r[i].high-pc),MathAbs(r[i].low-pc)));atr+=tr;}
   atr/=InpATRPeriod;return(IsFinite(atr)&&atr>0.0);
  }

int VolumeDigits(const double s){int d=0;double v=s;while(d<8&&MathAbs(v-MathRound(v))>1e-9){v*=10.0;d++;}return(d);}
double NormalizeVolumeDown(const double v){double mn=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN),mx=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX),st=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);if(mn<=0||mx<mn||st<=0||v<mn)return(0);double u=MathFloor((MathMin(v,mx)-mn+1e-12)/st);return(NormalizeDouble(mn+u*st,VolumeDigits(st)));}
bool OwnedPosition(ulong &ticket){ticket=0;int n=0;for(int i=PositionsTotal()-1;i>=0;i--){ulong x=PositionGetTicket(i);if(x>0&&PositionSelectByTicket(x)&&PositionGetString(POSITION_SYMBOL)==_Symbol&&PositionGetInteger(POSITION_MAGIC)==InpMagic){ticket=x;n++;}}if(n>1)g_runtime_failed=true;return(n==1);}
bool AnySymbolExposure(){for(int i=PositionsTotal()-1;i>=0;i--){ulong x=PositionGetTicket(i);if(x>0&&PositionSelectByTicket(x)&&PositionGetString(POSITION_SYMBOL)==_Symbol)return(true);}return(false);}

void ResetFixState(){g_state=NEUTRAL;g_fix_bar_open=0;g_fix_dir=0;g_fix_close=0;g_fix_move=0;g_confirmation_index=0;}

void RefreshDayAndRisk(const datetime now)
  {
   double e=AccountInfoDouble(ACCOUNT_EQUITY);int d=DayKey(now);long w=WeekKey(now);
   if(d!=g_day_key){g_day_key=d;g_days_seen++;g_day_start_equity=e;g_day_locked=false;g_day_latched=false;ulong t=0;if(!OwnedPosition(t))ResetFixState();}
   if(w!=g_week_key){g_week_key=w;g_week_start_equity=e;g_week_locked=false;}
   if(g_day_start_equity>0&&e<=g_day_start_equity*(1-InpDailyLossPct/100.0))g_day_locked=true;
   if(g_week_start_equity>0&&e<=g_week_start_equity*(1-InpWeeklyLossPct/100.0))g_week_locked=true;
  }

bool EntryTimeAllowed(const datetime t)
  {
   MqlDateTime p;TimeToStruct(t,p);if(p.day_of_week==0||p.day_of_week==6)return(false);int m=p.hour*60+p.min;if(m>=InpDailyFlatHour*60+InpDailyFlatMinute)return(false);if(p.day_of_week==5&&m>=InpFridayFlatHour*60+InpFridayFlatMinute)return(false);return(true);
  }

bool CloseOwned(const string reason)
  {
   ulong t=0;if(!OwnedPosition(t))return(true);g_close_attempts++;g_pending_exit_reason=reason;
   if(!g_trade.PositionClose(t,InpDeviationPoints)){g_close_rejects++;return(false);}uint c=g_trade.ResultRetcode();if(c!=TRADE_RETCODE_DONE&&c!=TRADE_RETCODE_DONE_PARTIAL){g_close_rejects++;return(false);}g_closes++;return(true);
  }

void ManagePosition(const datetime now,const datetime bar_open,const bool new_bar)
  {
   ulong t=0;if(!OwnedPosition(t))return;g_state=IN_POSITION;MqlDateTime p;TimeToStruct(now,p);int m=p.hour*60+p.min;string reason="";
   if(p.day_of_week==5&&m>=InpFridayFlatHour*60+InpFridayFlatMinute)reason="FRIDAY_FLAT";else if(m>=InpDailyFlatHour*60+InpDailyFlatMinute)reason="DAILY_FLAT";else if(new_bar){datetime s=g_entry_time;if(s<=0&&PositionSelectByTicket(t))s=(datetime)PositionGetInteger(POSITION_TIME);if(s>0&&iBarShift(_Symbol,PERIOD_M5,s,false)>=InpTimeStopBars)reason="TIME_STOP";}
   if(reason==""||g_last_close_attempt_bar==bar_open)return;g_last_close_attempt_bar=bar_open;CloseOwned(reason);
  }

void FillSignal(EntrySignal &s,const datetime availability,const int confirmation_index,const double atr)
  {
   ZeroMemory(s);s.fired=true;s.decision_time=availability-PeriodSeconds(PERIOD_M5);s.availability_time=availability;s.fix_bar_open=g_fix_bar_open;s.direction=-g_fix_dir;s.confirmation_index=confirmation_index;s.fix_hour=FixHourForDate(availability);s.atr=atr;s.fix_close=g_fix_close;s.fix_move=g_fix_move;s.fix_move_pips=MathAbs(g_fix_move)/PipSize();s.retrace_fraction=(confirmation_index>0?MathAbs((iClose(_Symbol,PERIOD_M5,1)-g_fix_close)/g_fix_move):0.0);g_signals++;
  }

bool SubmitEntry(const EntrySignal &s)
  {
   if(!s.fired||AnySymbolExposure()||!EntryTimeAllowed(s.availability_time)){g_exposure_cancels++;return(false);}if(g_day_locked||g_week_locked){g_risk_cancels++;return(false);}
   MqlTick q;if(!SymbolInfoTick(_Symbol,q)||q.ask<=q.bid)return(false);double point=SymbolInfoDouble(_Symbol,SYMBOL_POINT),pip=PipSize(),tick=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE),contract=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_CONTRACT_SIZE);if(point<=0||pip<=0||tick<=0||contract<=0)return(false);
   double spread=(q.ask-q.bid)/point;if(spread>InpMaxSpreadPoints){g_spread_cancels++;return(false);}double dist=MathMax(InpMinSLPips*pip,MathMin(InpSLATRMult*s.atr,InpMaxSLPips*pip)),tpdist=InpTakeProfitR*dist;
   double min_dist=(double)MathMax(MathMax(SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL),SymbolInfoInteger(_Symbol,SYMBOL_TRADE_FREEZE_LEVEL)),0)*point;if(dist<min_dist||tpdist<min_dist){g_stops_cancels++;return(false);}
   ENUM_ORDER_TYPE type=(s.direction>0?ORDER_TYPE_BUY:ORDER_TYPE_SELL);double entry=(s.direction>0?q.ask:q.bid);double sl=(s.direction>0?FloorToTick(entry-dist,tick):CeilToTick(entry+dist,tick));double tp=(s.direction>0?CeilToTick(entry+tpdist,tick):FloorToTick(entry-tpdist,tick));
   if((s.direction>0&&(entry-sl<min_dist||tp-entry<min_dist))||(s.direction<0&&(sl-entry<min_dist||entry-tp<min_dist))){g_stops_cancels++;return(false);}
   double loss=0,margin1=0;if(!OrderCalcProfit(type,_Symbol,1,entry,sl,loss)||loss>=0)return(false);if(!OrderCalcMargin(type,_Symbol,1,entry,margin1)||margin1<=0)return(false);
   double eq=AccountInfoDouble(ACCOUNT_EQUITY),free=AccountInfoDouble(ACCOUNT_MARGIN_FREE);double vr=eq*(InpRiskPercent/100.0)/MathAbs(loss),vn=(eq*InpMaxNotionalMult)/(entry*contract),vm=(free*(InpMaxMarginUsagePct/100.0))/margin1;double volume=NormalizeVolumeDown(MathMin(vr,MathMin(vn,vm)));if(volume<=0){g_risk_cancels++;return(false);}
   double margin=0;if(!OrderCalcMargin(type,_Symbol,volume,entry,margin))return(false);double notional=volume*entry*contract;if(margin>free*InpMaxMarginUsagePct/100.0+.01||notional>eq*InpMaxNotionalMult+.01){g_risk_cancels++;return(false);}
   g_trade.SetExpertMagicNumber(InpMagic);g_trade.LogLevel(LOG_LEVEL_NO);g_trade.SetDeviationInPoints(InpDeviationPoints);g_trade.SetTypeFillingBySymbol(_Symbol);
   bool sent=g_trade.PositionOpen(_Symbol,type,volume,entry,sl,tp,InpVariantTag);uint c=g_trade.ResultRetcode();if(!sent||(c!=TRADE_RETCODE_DONE&&c!=TRADE_RETCODE_DONE_PARTIAL)){g_entry_rejects++;return(false);}
   g_entries++;g_state=IN_POSITION;g_entry_time=s.availability_time;g_entry_price=(g_trade.ResultPrice()>0?g_trade.ResultPrice():entry);g_initial_sl=sl;g_initial_risk=MathAbs(g_entry_price-sl);g_entry_margin_usage_pct=100.0*margin/free;g_pending_exit_reason="";
   PrintFormat("WMRR001_ENTRY availability=%I64d fix_open=%I64d fix_hour=%d confirmation_index=%d direction=%s fix_move_pips=%.3f retrace_fraction=%.4f atr=%.6f volume=%.2f entry=%.5f sl=%.5f tp=%.5f spread_points=%.1f notional_mult=%.4f margin_usage_pct=%.4f",(long)s.availability_time,(long)s.fix_bar_open,s.fix_hour,s.confirmation_index,(s.direction>0?"LONG":"SHORT"),s.fix_move_pips,s.retrace_fraction,s.atr,volume,g_entry_price,sl,tp,spread,notional/eq,g_entry_margin_usage_pct);
   return(true);
  }

void DetectFixWindow(const datetime availability)
  {
   if(g_state!=NEUTRAL||g_day_latched)return;MqlRates r[];if(!LoadClosedRates(InpMeasurementBars+1,r))return;MqlDateTime p;TimeToStruct(r[0].time,p);int fix_hour=FixHourForDate(r[0].time);if(p.hour!=fix_hour||p.min!=0||availability-r[0].time!=PeriodSeconds(PERIOD_M5))return;
   if(fix_hour==InpNormalFixHour)g_fix18_days++;else g_fix19_days++;
   if(!BarsContiguous(r)){g_contiguity_fails++;g_day_latched=true;return;}
   g_fix_close=r[0].close;g_fix_move=g_fix_close-r[InpMeasurementBars].close;double move_pips=MathAbs(g_fix_move)/PipSize();if(move_pips<InpMinFixMovePips){g_small_move_days++;g_day_latched=true;ResetFixState();return;}
   g_fix_dir=(g_fix_move>0?1:-1);g_fix_bar_open=r[0].time;g_confirmation_index=0;g_fix_observed++;g_state=FIX_OBSERVED;
   PrintFormat("WMRR001_PREFIX availability=%I64d fix_open=%I64d fix_hour=%d direction=%s fix_close=%.5f displacement_pips=%.3f",(long)availability,(long)g_fix_bar_open,fix_hour,(g_fix_dir>0?"UP":"DOWN"),g_fix_close,move_pips);
   if(!InpRequireRetracement){double atr=0;EntrySignal s;if(LoadATR(atr)){FillSignal(s,availability,0,atr);SubmitEntry(s);}g_day_latched=true;if(g_state!=IN_POSITION)ResetFixState();}
  }

void EvaluateConfirmation(const datetime availability)
  {
   if(g_state!=FIX_OBSERVED||!InpRequireRetracement)return;const int next_index=g_confirmation_index+1;const datetime expected=g_fix_bar_open+(next_index+1)*PeriodSeconds(PERIOD_M5);
   if(availability<expected)return;if(availability!=expected){g_contiguity_fails++;g_day_latched=true;ResetFixState();return;}
   MqlRates r[];if(!LoadClosedRates(1,r)||r[0].time!=g_fix_bar_open+next_index*PeriodSeconds(PERIOD_M5)){g_contiguity_fails++;g_day_latched=true;ResetFixState();return;}
   g_confirmation_index=next_index;g_confirmation_checks++;double threshold=InpRetracementFraction*MathAbs(g_fix_move);bool reversed=(g_fix_dir>0?r[0].close<=g_fix_close-threshold:r[0].close>=g_fix_close+threshold);
   if(reversed){double atr=0;EntrySignal s;if(LoadATR(atr)){g_confirmations++;FillSignal(s,availability,next_index,atr);PrintFormat("WMRR001_CONFIRM availability=%I64d confirmation_index=%d close=%.5f fix_close=%.5f retrace_fraction=%.4f",(long)availability,next_index,r[0].close,g_fix_close,MathAbs((r[0].close-g_fix_close)/g_fix_move));SubmitEntry(s);}g_day_latched=true;if(g_state!=IN_POSITION)ResetFixState();return;}
   if(next_index>=InpMaxConfirmationBars){g_confirmation_expiries++;g_day_latched=true;ResetFixState();}
  }

string ExitReasonName(const long r){if(r==DEAL_REASON_SL)return("SL");if(r==DEAL_REASON_TP)return("TP");if(r==DEAL_REASON_EXPERT&&g_pending_exit_reason!="")return(g_pending_exit_reason);return(StringFormat("DEAL_REASON_%d",(int)r));}
void OnTradeTransaction(const MqlTradeTransaction &tr,const MqlTradeRequest &rq,const MqlTradeResult &rs)
  {
   if(tr.type!=TRADE_TRANSACTION_DEAL_ADD||tr.deal==0||!HistoryDealSelect(tr.deal))return;if(HistoryDealGetString(tr.deal,DEAL_SYMBOL)!=_Symbol||HistoryDealGetInteger(tr.deal,DEAL_MAGIC)!=InpMagic)return;long k=HistoryDealGetInteger(tr.deal,DEAL_ENTRY);if(k!=DEAL_ENTRY_OUT&&k!=DEAL_ENTRY_OUT_BY)return;
   long reason=HistoryDealGetInteger(tr.deal,DEAL_REASON);double price=HistoryDealGetDouble(tr.deal,DEAL_PRICE),profit=HistoryDealGetDouble(tr.deal,DEAL_PROFIT),com=HistoryDealGetDouble(tr.deal,DEAL_COMMISSION),swap=HistoryDealGetDouble(tr.deal,DEAL_SWAP);datetime t=(datetime)HistoryDealGetInteger(tr.deal,DEAL_TIME);int held=(g_entry_time>0?iBarShift(_Symbol,PERIOD_M5,g_entry_time,false):-1);
   PrintFormat("WMRR001_EXIT time=%I64d reason=%s price=%.5f profit=%.2f commission=%.2f swap=%.2f net=%.2f bars_held=%d margin_usage_pct=%.4f",(long)t,ExitReasonName(reason),price,profit,com,swap,profit+com+swap,held,g_entry_margin_usage_pct);ulong ticket=0;if(!OwnedPosition(ticket)){g_entry_time=0;g_entry_price=0;g_initial_sl=0;g_initial_risk=0;g_entry_margin_usage_pct=0;g_pending_exit_reason="";ResetFixState();}
  }

bool InputsAreFrozen()
  {
   bool variant=((InpVariantTag==PRIMARY_VARIANT&&InpRequireRetracement)||(InpVariantTag==CONTROL_VARIANT&&!InpRequireRetracement));return(InpResearchAutoMode&&InpEnableTelemetry&&InpHypothesisId==EXPECTED_HYPOTHESIS&&variant&&InpClockConvention=="US_DST_NY_CLOSE"&&InpNormalFixHour==18&&InpMismatchFixHour==19&&InpMeasurementBars==12&&MathAbs(InpMinFixMovePips-1.2)<1e-12&&MathAbs(InpRetracementFraction-.35)<1e-12&&InpMaxConfirmationBars==3&&InpATRPeriod==14&&MathAbs(InpSLATRMult-1.9)<1e-12&&MathAbs(InpMinSLPips-12)<1e-12&&MathAbs(InpMaxSLPips-28)<1e-12&&MathAbs(InpTakeProfitR-1.4)<1e-12&&InpTimeStopBars==18&&MathAbs(InpRiskPercent-.2)<1e-12&&MathAbs(InpMaxNotionalMult-3)<1e-12&&MathAbs(InpMaxMarginUsagePct-9)<1e-12&&InpMaxSpreadPoints==14&&MathAbs(InpDailyLossPct-.9)<1e-12&&MathAbs(InpWeeklyLossPct-2.2)<1e-12&&InpDailyFlatHour==21&&InpDailyFlatMinute==50&&InpFridayFlatHour==18&&InpFridayFlatMinute==50&&InpDeviationPoints==7&&InpMagic==5605801);
  }

int OnInit()
  {
   if(_Symbol!="EURUSD"||_Period!=PERIOD_M5||!InputsAreFrozen())return(INIT_PARAMETERS_INCORRECT);if(!EmitSeriesProof())return(INIT_FAILED);g_trade.SetExpertMagicNumber(InpMagic);g_trade.LogLevel(LOG_LEVEL_NO);g_trade.SetDeviationInPoints(InpDeviationPoints);g_trade.SetTypeFillingBySymbol(_Symbol);datetime now=TimeCurrent();double e=AccountInfoDouble(ACCOUNT_EQUITY);g_day_key=DayKey(now);g_week_key=WeekKey(now);g_day_start_equity=e;g_week_start_equity=e;g_days_seen=1;if(!CurrentBarOpen(g_last_bar_open))return(INIT_FAILED);PrintFormat("WMRR001_INIT ea=%s hypothesis=%s variant=%s symbol=%s timeframe=M5 clock=%s confirmation=%s",EA_NAME,InpHypothesisId,InpVariantTag,_Symbol,InpClockConvention,(InpRequireRetracement?"true":"false"));return(INIT_SUCCEEDED);
  }

void OnDeinit(const int reason)
  {
   PrintFormat("WMRR001_SUMMARY reason=%d runtime_failed=%s closed_bars=%I64d days_seen=%I64d fix18_days=%I64d fix19_days=%I64d contiguity_fails=%I64d small_move_days=%I64d fix_observed=%I64d confirmation_checks=%I64d confirmations=%I64d confirmation_expiries=%I64d signals=%I64d entries=%I64d entry_rejects=%I64d spread_cancels=%I64d stops_cancels=%I64d risk_cancels=%I64d exposure_cancels=%I64d close_attempts=%I64d close_rejects=%I64d closes=%I64d invalid_inputs=%I64d",reason,(g_runtime_failed?"true":"false"),g_closed_bars,g_days_seen,g_fix18_days,g_fix19_days,g_contiguity_fails,g_small_move_days,g_fix_observed,g_confirmation_checks,g_confirmations,g_confirmation_expiries,g_signals,g_entries,g_entry_rejects,g_spread_cancels,g_stops_cancels,g_risk_cancels,g_exposure_cancels,g_close_attempts,g_close_rejects,g_closes,g_invalid_inputs);
  }

void OnTick()
  {
   datetime bar=0;if(!CurrentBarOpen(bar))return;datetime now=TimeCurrent();RefreshDayAndRisk(now);const bool new_bar=(bar!=g_last_bar_open);ManagePosition(now,bar,new_bar);if(!new_bar)return;g_last_bar_open=bar;g_closed_bars++;if(AnySymbolExposure())return;if(g_state==FIX_OBSERVED){EvaluateConfirmation(bar);return;}DetectFixWindow(bar);
  }
