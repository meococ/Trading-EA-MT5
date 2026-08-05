#property strict
#property version   "1.00"
#property description "Closed-bar fusion of AI Regime Detection, Modern Bollinger Bands and QQE MOD"
#property tester_indicator "AlphaFactory\\AI_Regime_Detection.ex5"
#property tester_indicator "AlphaFactory\\Modern_Bollinger_Bands_GBB.ex5"
#property tester_indicator "AlphaFactory\\QQE_MOD.ex5"

// Public indicator contracts consumed by this EA (closed bars only):
// AI Regime Detection: valid=11, held regime=12, confidence %=5.
// Modern Bollinger Bands: upper=3, lower=5, basis=7, S1..S3 flags=25..30.
// QQE MOD: primary RSI=3, secondary RSI=4, composite state=8.

enum FusionSignal
  {
   SIGNAL_NONE=0,
   SIGNAL_S1_RANGE_LONG=1,
   SIGNAL_S1_RANGE_SHORT=-1,
   SIGNAL_S2_TREND_LONG=2,
   SIGNAL_S2_TREND_SHORT=-2,
   SIGNAL_S3_BREAKOUT_LONG=3,
   SIGNAL_S3_BREAKOUT_SHORT=-3
  };

input group "--- Research authority (fail closed) ---"
input bool   InpResearchAutoMode=false;
input bool   InpEnableTelemetry=true;
input string InpHypothesisId="UNREGISTERED_BUILD_ONLY";
input string InpVariantTag="BASELINE_FROZEN";
input string InpExpectedSymbol="EURUSD";

input group "--- Execution and risk ---"
input long   InpMagic=5686101;
input double InpRiskPercent=0.25;
input double InpMaxDailyLossPct=3.5;
input double InpMaxAccountDrawdownPct=8.0;
input int    InpMaxTradesPerDay=3;
input double InpMaxSpreadToStop=0.15;
input int    InpDeviationPoints=20;
input int    InpMaxHoldBars=48;
input int    InpTradeStartMinutesUtc=420;
input int    InpDailyFlattenMinutesUtc=1200;
input int    InpFridayFlattenMinutesUtc=1200;

input group "--- Frozen ensemble setup ---"
input double InpMinAIConfidence=0.45;
input double InpStopHalfWidthMult=1.00;
input double InpRewardRisk=1.50;
input double InpRangeQQEExtreme=3.0;
input double InpTrendQQEMin=0.0;
input int    InpEntryCooldownBars=5;
input bool   InpAllowRangeS1=true;
input bool   InpAllowTrendS2=true;
input bool   InpAllowBreakoutS3=true;

const string EA_NAME="EA_AIRQMB_RegimeFusion";
const string TELEMETRY_PROFILE="lifecycle-v3";
const int    FIVEPERCENT_WINTER_OFFSET_HOURS=2;
const int    SECONDS_PER_M5_BAR=300;

int g_ai_handle=INVALID_HANDLE;
int g_mbb_handle=INVALID_HANDLE;
int g_qqe_handle=INVALID_HANDLE;
datetime g_last_bar_time=0;
datetime g_last_entry_bar_time=0;

int g_day_key=0;
double g_day_start_equity=0.0;
double g_peak_equity=0.0;
int g_trades_today=0;
bool g_daily_locked=false;
bool g_account_locked=false;

string g_run_id="";
string g_lifecycle_name="";
string g_run_meta_name="";
int g_lifecycle_handle=INVALID_HANDLE;

long g_ticks_seen=0;
long g_closed_bars_seen=0;
long g_indicator_ready=0;
long g_indicator_not_ready=0;
long g_regime_bull=0;
long g_regime_bear=0;
long g_regime_range=0;
long g_regime_highvol=0;
long g_s1_signals=0;
long g_s2_signals=0;
long g_s3_signals=0;
long g_no_signal=0;
long g_reject_session=0;
long g_reject_daily_lock=0;
long g_reject_account_lock=0;
long g_reject_trade_limit=0;
long g_reject_exposure=0;
long g_reject_spread=0;
long g_reject_geometry=0;
long g_reject_sizing=0;
long g_reject_margin=0;
long g_reject_order_check=0;
long g_reject_order_send=0;
long g_entries_opened=0;
long g_final_closes=0;
long g_max_hold_closes=0;
long g_daily_flatten_closes=0;
long g_friday_flatten_closes=0;
long g_invalid_deal_events=0;
string g_last_reason="NONE";

FusionSignal g_pending_signal=SIGNAL_NONE;
double g_pending_sl=0.0;
double g_pending_tp=0.0;
double g_pending_risk_account=0.0;
ulong g_active_position_id=0;
FusionSignal g_active_signal=SIGNAL_NONE;
double g_active_entry=0.0;
double g_active_sl=0.0;
double g_active_tp=0.0;
double g_active_risk_account=0.0;

struct EnsembleSnapshot
  {
   bool ready;
   int regime;
   double confidence;
   double upper;
   double lower;
   double basis;
   bool s1_long;
   bool s1_short;
   bool s2_long;
   bool s2_short;
   bool s3_long;
   bool s3_short;
   double qqe_primary;
   double qqe_primary_previous;
   double qqe_secondary;
   double qqe_secondary_previous;
   int qqe_state;
  };

struct TradeDecision
  {
   bool fired;
   int direction;
   FusionSignal signal;
   double stop;
   double target;
   string reason;
  };

int DaysInMonth(const int year,const int month)
  {
   if(month==2)
      return(((year%4==0 && year%100!=0) || year%400==0) ? 29 : 28);
   if(month==4 || month==6 || month==9 || month==11)
      return(30);
   return(31);
  }

datetime MakeDateTime(const int year,const int month,const int day,const int hour,const int minute=0)
  {
   MqlDateTime p;
   ZeroMemory(p);
   p.year=year; p.mon=month; p.day=day; p.hour=hour; p.min=minute;
   return(StructToTime(p));
  }

datetime LastSunday(const int year,const int month,const int hour)
  {
   datetime value=MakeDateTime(year,month,DaysInMonth(year,month),hour);
   MqlDateTime p;
   TimeToStruct(value,p);
   return(value-p.day_of_week*86400);
  }

datetime NthSunday(const int year,const int month,const int nth,const int hour)
  {
   datetime first=MakeDateTime(year,month,1,hour);
   MqlDateTime p;
   TimeToStruct(first,p);
   int first_sunday=1+((7-p.day_of_week)%7);
   return(MakeDateTime(year,month,first_sunday+(nth-1)*7,hour));
  }

bool IsFivePercentDstUtc(const datetime utc_time)
  {
   MqlDateTime p;
   TimeToStruct(utc_time,p);
   if(p.year<=2023)
      return(utc_time>=LastSunday(p.year,3,1) && utc_time<LastSunday(p.year,10,1));
   return(utc_time>=NthSunday(p.year,3,2,7) && utc_time<NthSunday(p.year,11,1,6));
  }

datetime ServerToUtc(const datetime server_time)
  {
   datetime winter_candidate=server_time-FIVEPERCENT_WINTER_OFFSET_HOURS*3600;
   int offset=FIVEPERCENT_WINTER_OFFSET_HOURS+(IsFivePercentDstUtc(winter_candidate) ? 1 : 0);
   return(server_time-offset*3600);
  }

int DateKey(const MqlDateTime &p)
  {
   return(p.year*10000+p.mon*100+p.day);
  }

int MinuteOfDay(const MqlDateTime &p)
  {
   return(p.hour*60+p.min);
  }

string JsonEscape(string text)
  {
   StringReplace(text,"\\","\\\\");
   StringReplace(text,"\"","\\\"");
   StringReplace(text,"\r","\\r");
   StringReplace(text,"\n","\\n");
   return(text);
  }

string SafeToken(string text)
  {
   for(int i=0;i<StringLen(text);i++)
     {
      ushort c=StringGetCharacter(text,i);
      bool ok=(c>='A' && c<='Z') || (c>='a' && c<='z') ||
              (c>='0' && c<='9') || c=='_' || c=='-';
      if(!ok)
         StringSetCharacter(text,i,'_');
     }
   return(text);
  }

string SignalName(const FusionSignal signal)
  {
   switch(signal)
     {
      case SIGNAL_S1_RANGE_LONG:     return("S1_RANGE_LONG");
      case SIGNAL_S1_RANGE_SHORT:    return("S1_RANGE_SHORT");
      case SIGNAL_S2_TREND_LONG:     return("S2_TREND_LONG");
      case SIGNAL_S2_TREND_SHORT:    return("S2_TREND_SHORT");
      case SIGNAL_S3_BREAKOUT_LONG:  return("S3_BREAKOUT_LONG");
      case SIGNAL_S3_BREAKOUT_SHORT: return("S3_BREAKOUT_SHORT");
      default:                       return("NONE");
     }
  }

bool IsUsable(const double value)
  {
   return(value!=EMPTY_VALUE && MathIsValidNumber(value));
  }

bool ReadBufferValue(const int handle,const int buffer,const int shift,double &value)
  {
   double data[1];
   if(CopyBuffer(handle,buffer,shift,1,data)!=1 || !IsUsable(data[0]))
      return(false);
   value=data[0];
   return(true);
  }

bool ReadSnapshot(EnsembleSnapshot &s)
  {
   ZeroMemory(s);
   s.ready=false;
   if(BarsCalculated(g_ai_handle)<310 || BarsCalculated(g_mbb_handle)<310 || BarsCalculated(g_qqe_handle)<60)
      return(false);

   double ai_valid=0.0,regime=0.0,confidence_pct=0.0;
   double s1l=0.0,s1s=0.0,s2l=0.0,s2s=0.0,s3l=0.0,s3s=0.0,state=0.0;
   if(!ReadBufferValue(g_ai_handle,11,1,ai_valid) ||
      !ReadBufferValue(g_ai_handle,12,1,regime) ||
      !ReadBufferValue(g_ai_handle,5,1,confidence_pct) ||
      !ReadBufferValue(g_mbb_handle,3,1,s.upper) ||
      !ReadBufferValue(g_mbb_handle,5,1,s.lower) ||
      !ReadBufferValue(g_mbb_handle,7,1,s.basis) ||
      !ReadBufferValue(g_mbb_handle,25,1,s1l) ||
      !ReadBufferValue(g_mbb_handle,26,1,s1s) ||
      !ReadBufferValue(g_mbb_handle,27,1,s2l) ||
      !ReadBufferValue(g_mbb_handle,28,1,s2s) ||
      !ReadBufferValue(g_mbb_handle,29,1,s3l) ||
      !ReadBufferValue(g_mbb_handle,30,1,s3s) ||
      !ReadBufferValue(g_qqe_handle,3,1,s.qqe_primary) ||
      !ReadBufferValue(g_qqe_handle,3,2,s.qqe_primary_previous) ||
      !ReadBufferValue(g_qqe_handle,4,1,s.qqe_secondary) ||
      !ReadBufferValue(g_qqe_handle,4,2,s.qqe_secondary_previous) ||
      !ReadBufferValue(g_qqe_handle,8,1,state))
      return(false);

   if(ai_valid<0.5 || regime<0.0 || regime>3.0 || confidence_pct<0.0 ||
      s.upper<=s.lower || s.basis<=0.0)
      return(false);
   s.regime=(int)MathRound(regime);
   s.confidence=confidence_pct/100.0;
   s.s1_long=s1l>0.5; s.s1_short=s1s>0.5;
   s.s2_long=s2l>0.5; s.s2_short=s2s>0.5;
   s.s3_long=s3l>0.5; s.s3_short=s3s>0.5;
   s.qqe_state=(int)MathRound(state);
   s.ready=true;
   return(true);
  }

bool HasForeignSymbolPosition()
  {
   for(int i=PositionsTotal()-1;i>=0;i--)
     {
      ulong ticket=PositionGetTicket(i);
      if(ticket==0 || !PositionSelectByTicket(ticket) || PositionGetString(POSITION_SYMBOL)!=_Symbol)
         continue;
      if((long)PositionGetInteger(POSITION_MAGIC)!=InpMagic)
         return(true);
     }
   return(false);
  }

ulong OwnedPositionTicket()
  {
   for(int i=PositionsTotal()-1;i>=0;i--)
     {
      ulong ticket=PositionGetTicket(i);
      if(ticket>0 && PositionSelectByTicket(ticket) &&
         PositionGetString(POSITION_SYMBOL)==_Symbol &&
         (long)PositionGetInteger(POSITION_MAGIC)==InpMagic)
         return(ticket);
     }
   return(0);
  }

ENUM_ORDER_TYPE_FILLING ResolveFilling()
  {
   long flags=SymbolInfoInteger(_Symbol,SYMBOL_FILLING_MODE);
   if((flags&ORDER_FILLING_FOK)==ORDER_FILLING_FOK)
      return(ORDER_FILLING_FOK);
   if((flags&ORDER_FILLING_IOC)==ORDER_FILLING_IOC)
      return(ORDER_FILLING_IOC);
   return(ORDER_FILLING_RETURN);
  }

double NormalizeVolumeDown(const double raw)
  {
   double minimum=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN);
   double maximum=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX);
   double step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);
   if(step<=0.0 || maximum<=0.0)
      return(0.0);
   double volume=MathFloor(MathMin(raw,maximum)/step+1e-9)*step;
   if(volume<minimum-1e-9)
      return(0.0);
   int digits=0;
   double probe=step;
   while(digits<8 && MathAbs(probe-MathRound(probe))>1e-9)
     {
      probe*=10.0;
      digits++;
     }
   return(NormalizeDouble(volume,digits));
  }

double RiskSizedVolume(const int direction,const double entry,const double stop,double &risk_account)
  {
   risk_account=AccountInfoDouble(ACCOUNT_EQUITY)*InpRiskPercent/100.0;
   double profit=0.0;
   ENUM_ORDER_TYPE type=direction>0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
   if(risk_account<=0.0 || !OrderCalcProfit(type,_Symbol,1.0,entry,stop,profit) || profit>=0.0)
      return(0.0);
   double volume=NormalizeVolumeDown(risk_account/MathAbs(profit));
   if(volume<=0.0)
      return(0.0);

   double free_margin=AccountInfoDouble(ACCOUNT_MARGIN_FREE);
   double step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);
   double minimum=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN);
   double margin=0.0;
   while(volume>=minimum-1e-9)
     {
      if(OrderCalcMargin(type,_Symbol,volume,entry,margin) && margin<=free_margin*0.50)
         break;
      volume=NormalizeVolumeDown(volume-step);
     }
   if(volume<minimum-1e-9 || margin>free_margin*0.50)
      return(0.0);
   risk_account=MathAbs(profit)*volume;
   return(volume);
  }

bool BuildDecision(const EnsembleSnapshot &s,TradeDecision &d)
  {
   ZeroMemory(d);
   d.fired=false;
   if(s.confidence+1e-12<InpMinAIConfidence || s.regime==3)
      return(false);

   if(s.regime==2 && InpAllowRangeS1)
     {
      bool rising=s.qqe_primary>s.qqe_primary_previous && s.qqe_secondary>s.qqe_secondary_previous;
      bool falling=s.qqe_primary<s.qqe_primary_previous && s.qqe_secondary<s.qqe_secondary_previous;
      if(s.s1_long && rising && MathMin(s.qqe_primary,s.qqe_secondary)<=-InpRangeQQEExtreme)
        {
         d.direction=1; d.signal=SIGNAL_S1_RANGE_LONG;
        }
      else if(s.s1_short && falling && MathMax(s.qqe_primary,s.qqe_secondary)>=InpRangeQQEExtreme)
        {
         d.direction=-1; d.signal=SIGNAL_S1_RANGE_SHORT;
        }
     }
   else if(s.regime==0)
     {
      bool qqe_long=s.qqe_primary>InpTrendQQEMin && s.qqe_secondary>InpTrendQQEMin && s.qqe_state>=0;
      if(InpAllowBreakoutS3 && s.s3_long && qqe_long)
        {
         d.direction=1; d.signal=SIGNAL_S3_BREAKOUT_LONG;
        }
      else if(InpAllowTrendS2 && s.s2_long && qqe_long)
        {
         d.direction=1; d.signal=SIGNAL_S2_TREND_LONG;
        }
     }
   else if(s.regime==1)
     {
      bool qqe_short=s.qqe_primary<-InpTrendQQEMin && s.qqe_secondary<-InpTrendQQEMin && s.qqe_state<=0;
      if(InpAllowBreakoutS3 && s.s3_short && qqe_short)
        {
         d.direction=-1; d.signal=SIGNAL_S3_BREAKOUT_SHORT;
        }
      else if(InpAllowTrendS2 && s.s2_short && qqe_short)
        {
         d.direction=-1; d.signal=SIGNAL_S2_TREND_SHORT;
        }
     }

   if(d.signal==SIGNAL_NONE)
      return(false);

   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick) || tick.ask<=0.0 || tick.bid<=0.0)
      return(false);
   double entry=d.direction>0 ? tick.ask : tick.bid;
   double half_width=(s.upper-s.lower)*0.5;
   double spread=tick.ask-tick.bid;
   long stops_level=SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL);
   double minimum_distance=MathMax((stops_level+2)*_Point,spread*3.0);
   double risk_distance=MathMax(half_width*InpStopHalfWidthMult,minimum_distance);
   if(risk_distance<=0.0 || spread/risk_distance>InpMaxSpreadToStop)
     {
      g_reject_spread++;
      return(false);
     }
   d.stop=NormalizeDouble(entry-d.direction*risk_distance,_Digits);
   d.target=NormalizeDouble(entry+d.direction*risk_distance*InpRewardRisk,_Digits);
   if((d.direction>0 && (d.stop>=tick.bid || d.target<=tick.ask)) ||
      (d.direction<0 && (d.stop<=tick.ask || d.target>=tick.bid)))
     {
      g_reject_geometry++;
      return(false);
     }
   d.reason=SignalName(d.signal);
   d.fired=true;
   return(true);
  }

bool SubmitEntry(const TradeDecision &d)
  {
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick))
      return(false);
   double entry=d.direction>0 ? tick.ask : tick.bid;
   double risk_account=0.0;
   double volume=RiskSizedVolume(d.direction,entry,d.stop,risk_account);
   if(volume<=0.0)
     {
      g_reject_sizing++;
      return(false);
     }

   MqlTradeRequest request;
   MqlTradeCheckResult check;
   MqlTradeResult result;
   ZeroMemory(request); ZeroMemory(check); ZeroMemory(result);
   request.action=TRADE_ACTION_DEAL;
   request.magic=(ulong)InpMagic;
   request.symbol=_Symbol;
   request.volume=volume;
   request.type=d.direction>0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
   request.price=entry;
   request.sl=d.stop;
   request.tp=d.target;
   request.deviation=(ulong)InpDeviationPoints;
   request.type_filling=ResolveFilling();
   request.comment=SignalName(d.signal);

   if(!OrderCheck(request,check) || (check.retcode!=TRADE_RETCODE_DONE && check.retcode!=TRADE_RETCODE_PLACED))
     {
      g_reject_order_check++;
      g_last_reason=StringFormat("ORDER_CHECK_%u",check.retcode);
      return(false);
     }
   g_pending_signal=d.signal;
   g_pending_sl=d.stop;
   g_pending_tp=d.target;
   g_pending_risk_account=risk_account;
   if(!OrderSend(request,result) || (result.retcode!=TRADE_RETCODE_DONE && result.retcode!=TRADE_RETCODE_PLACED && result.retcode!=TRADE_RETCODE_DONE_PARTIAL))
     {
      g_reject_order_send++;
      g_last_reason=StringFormat("ORDER_SEND_%u",result.retcode);
      g_pending_signal=SIGNAL_NONE;
      return(false);
     }
   g_last_entry_bar_time=g_last_bar_time;
   g_last_reason=d.reason;
   return(true);
  }

bool CloseOwnedPosition(const ulong ticket,const string reason)
  {
   if(ticket==0 || !PositionSelectByTicket(ticket))
      return(false);
   long type=PositionGetInteger(POSITION_TYPE);
   double volume=PositionGetDouble(POSITION_VOLUME);
   MqlTick tick;
   if(volume<=0.0 || !SymbolInfoTick(_Symbol,tick))
      return(false);
   MqlTradeRequest request;
   MqlTradeResult result;
   ZeroMemory(request); ZeroMemory(result);
   request.action=TRADE_ACTION_DEAL;
   request.magic=(ulong)InpMagic;
   request.position=ticket;
   request.symbol=_Symbol;
   request.volume=volume;
   request.type=type==POSITION_TYPE_BUY ? ORDER_TYPE_SELL : ORDER_TYPE_BUY;
   request.price=type==POSITION_TYPE_BUY ? tick.bid : tick.ask;
   request.deviation=(ulong)InpDeviationPoints;
   request.type_filling=ResolveFilling();
   request.comment=reason;
   if(!OrderSend(request,result) ||
      (result.retcode!=TRADE_RETCODE_DONE && result.retcode!=TRADE_RETCODE_DONE_PARTIAL && result.retcode!=TRADE_RETCODE_PLACED))
      return(false);
   g_last_reason=reason;
   return(true);
  }

bool RemainingVolumeThroughDeal(const ulong position_id,const ulong target_deal,double &remaining)
  {
   remaining=0.0;
   if(!HistorySelect(0,TimeCurrent()+60))
      return(false);
   bool found=false;
   for(int i=0;i<HistoryDealsTotal();i++)
     {
      ulong deal=HistoryDealGetTicket(i);
      if(deal==0 || (ulong)HistoryDealGetInteger(deal,DEAL_POSITION_ID)!=position_id ||
         HistoryDealGetString(deal,DEAL_SYMBOL)!=_Symbol ||
         (long)HistoryDealGetInteger(deal,DEAL_MAGIC)!=InpMagic)
         continue;
      ENUM_DEAL_ENTRY entry=(ENUM_DEAL_ENTRY)HistoryDealGetInteger(deal,DEAL_ENTRY);
      double volume=HistoryDealGetDouble(deal,DEAL_VOLUME);
      if(entry==DEAL_ENTRY_IN) remaining+=volume;
      else if(entry==DEAL_ENTRY_OUT || entry==DEAL_ENTRY_OUT_BY) remaining-=volume;
      if(deal==target_deal) { found=true; break; }
     }
   return(found);
  }

double NetProfitThroughDeal(const ulong position_id,const ulong target_deal)
  {
   double net=0.0;
   if(!HistorySelect(0,TimeCurrent()+60))
      return(net);
   for(int i=0;i<HistoryDealsTotal();i++)
     {
      ulong deal=HistoryDealGetTicket(i);
      if(deal==0 || (ulong)HistoryDealGetInteger(deal,DEAL_POSITION_ID)!=position_id ||
         HistoryDealGetString(deal,DEAL_SYMBOL)!=_Symbol ||
         (long)HistoryDealGetInteger(deal,DEAL_MAGIC)!=InpMagic)
         continue;
      net+=HistoryDealGetDouble(deal,DEAL_PROFIT)+HistoryDealGetDouble(deal,DEAL_COMMISSION)+
           HistoryDealGetDouble(deal,DEAL_SWAP)+HistoryDealGetDouble(deal,DEAL_FEE);
      if(deal==target_deal)
         break;
     }
   return(net);
  }

bool WriteRunMeta()
  {
   if(!InpEnableTelemetry || g_run_meta_name=="")
      return(true);
   int handle=FileOpen(g_run_meta_name,FILE_WRITE|FILE_TXT|FILE_ANSI);
   if(handle==INVALID_HANDLE)
      return(false);
   string payload="{";
   payload+="\"schema_version\":\"alphafactory_run_meta.v1\",";
   payload+="\"run_id\":\""+JsonEscape(g_run_id)+"\",";
   payload+="\"ea_name\":\""+EA_NAME+"\",";
   payload+="\"symbol\":\""+JsonEscape(_Symbol)+"\",";
   payload+="\"telemetry_profile\":\""+TELEMETRY_PROFILE+"\",";
   payload+="\"hypothesis_id\":\""+JsonEscape(InpHypothesisId)+"\",";
   payload+="\"variant_tag\":\""+JsonEscape(InpVariantTag)+"\",";
   payload+=StringFormat("\"magic\":%I64d,",InpMagic);
   payload+="\"timeframe\":\"M5\",\"clock_profile\":\"FIVEPERCENT_EU_TO_2023_US_FROM_2024\",";
   payload+="\"research_auto_mode\":"+(InpResearchAutoMode ? "true" : "false")+",";
   payload+="\"economic_claims_authorized\":false,\"promotion_eligible\":false,\"closed_bar\":true,";
   payload+="\"funnel\":{";
   payload+=StringFormat("\"ticks_seen\":%I64d,\"closed_bars_seen\":%I64d,",g_ticks_seen,g_closed_bars_seen);
   payload+=StringFormat("\"indicator_ready\":%I64d,\"indicator_not_ready\":%I64d,",g_indicator_ready,g_indicator_not_ready);
   payload+=StringFormat("\"regime_bull\":%I64d,\"regime_bear\":%I64d,\"regime_range\":%I64d,\"regime_highvol\":%I64d,",g_regime_bull,g_regime_bear,g_regime_range,g_regime_highvol);
   payload+=StringFormat("\"s1_signals\":%I64d,\"s2_signals\":%I64d,\"s3_signals\":%I64d,\"no_signal\":%I64d,",g_s1_signals,g_s2_signals,g_s3_signals,g_no_signal);
   payload+=StringFormat("\"reject_session\":%I64d,\"reject_daily_lock\":%I64d,\"reject_account_lock\":%I64d,",g_reject_session,g_reject_daily_lock,g_reject_account_lock);
   payload+=StringFormat("\"reject_trade_limit\":%I64d,\"reject_exposure\":%I64d,\"reject_spread\":%I64d,",g_reject_trade_limit,g_reject_exposure,g_reject_spread);
   payload+=StringFormat("\"reject_geometry\":%I64d,\"reject_sizing\":%I64d,\"reject_margin\":%I64d,",g_reject_geometry,g_reject_sizing,g_reject_margin);
   payload+=StringFormat("\"reject_order_check\":%I64d,\"reject_order_send\":%I64d,",g_reject_order_check,g_reject_order_send);
   payload+=StringFormat("\"entries_opened\":%I64d,\"final_closes\":%I64d,",g_entries_opened,g_final_closes);
   payload+=StringFormat("\"max_hold_closes\":%I64d,\"daily_flatten_closes\":%I64d,\"friday_flatten_closes\":%I64d,",g_max_hold_closes,g_daily_flatten_closes,g_friday_flatten_closes);
   payload+=StringFormat("\"invalid_deal_events\":%I64d,",g_invalid_deal_events);
   payload+="\"last_reason\":\""+JsonEscape(g_last_reason)+"\"}}";
   FileWriteString(handle,payload);
   FileClose(handle);
   return(true);
  }

bool OpenTelemetry()
  {
   g_run_id=StringFormat("%s_%I64u",SafeToken(InpHypothesisId),GetTickCount64());
   g_lifecycle_name=StringFormat("%s_LifecycleTrades_%s.csv",_Symbol,g_run_id);
   g_run_meta_name=StringFormat("%s_RunMeta_%s.json",_Symbol,g_run_id);
   g_lifecycle_handle=FileOpen(g_lifecycle_name,FILE_WRITE|FILE_CSV|FILE_ANSI,',');
   if(g_lifecycle_handle==INVALID_HANDLE)
      return(false);
   FileWrite(g_lifecycle_handle,
             "event_time","utc_time","tag","action","order_type","volume","price","sl","tp",
             "reason","retcode","deal","order","symbol","position_id","entry_price","initial_sl",
             "initial_tp","risk_pts","initial_risk_account","close_source","deal_reason","achievedr",
             "net_profit","swap","commission","fee","deal_profit","deal_commission","deal_swap",
             "deal_fee","deal_net","is_final_close","engine_name","hypothesis_id");
   FileFlush(g_lifecycle_handle);
   return(WriteRunMeta());
  }

void LogLifecycleDeal(const ulong deal)
  {
   if(!HistoryDealSelect(deal) || HistoryDealGetString(deal,DEAL_SYMBOL)!=_Symbol ||
      (long)HistoryDealGetInteger(deal,DEAL_MAGIC)!=InpMagic)
      return;
   ENUM_DEAL_ENTRY entry=(ENUM_DEAL_ENTRY)HistoryDealGetInteger(deal,DEAL_ENTRY);
   if(entry!=DEAL_ENTRY_IN && entry!=DEAL_ENTRY_OUT && entry!=DEAL_ENTRY_OUT_BY)
      return;
   datetime event_time=(datetime)HistoryDealGetInteger(deal,DEAL_TIME);
   double volume=HistoryDealGetDouble(deal,DEAL_VOLUME);
   double price=HistoryDealGetDouble(deal,DEAL_PRICE);
   if(event_time<=0 || volume<=0.0 || price<=0.0)
     {
      g_invalid_deal_events++;
      return;
     }
   ulong position_id=(ulong)HistoryDealGetInteger(deal,DEAL_POSITION_ID);
   ulong order_id=(ulong)HistoryDealGetInteger(deal,DEAL_ORDER);
   ENUM_DEAL_TYPE deal_type=(ENUM_DEAL_TYPE)HistoryDealGetInteger(deal,DEAL_TYPE);
   ENUM_DEAL_REASON deal_reason=(ENUM_DEAL_REASON)HistoryDealGetInteger(deal,DEAL_REASON);
   double profit=HistoryDealGetDouble(deal,DEAL_PROFIT);
   double commission=HistoryDealGetDouble(deal,DEAL_COMMISSION);
   double swap=HistoryDealGetDouble(deal,DEAL_SWAP);
   double fee=HistoryDealGetDouble(deal,DEAL_FEE);
   bool is_open=entry==DEAL_ENTRY_IN;
   bool is_final=false;

   if(is_open)
     {
      g_active_position_id=position_id;
      g_active_signal=g_pending_signal;
      g_active_entry=price;
      g_active_sl=g_pending_sl;
      g_active_tp=g_pending_tp;
      g_active_risk_account=g_pending_risk_account;
      g_entries_opened++;
      g_trades_today++;
     }
   else
     {
      double remaining=0.0;
      if(RemainingVolumeThroughDeal(position_id,deal,remaining))
        {
         double step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);
         is_final=remaining<=MathMax(1e-8,step*0.5);
        }
     }

   double aggregate_net=is_open ? profit+commission+swap+fee : NetProfitThroughDeal(position_id,deal);
   double achieved_r=g_active_risk_account>0.0 ? aggregate_net/g_active_risk_account : 0.0;
   double risk_points=(g_active_entry>0.0 && g_active_sl>0.0) ? MathAbs(g_active_entry-g_active_sl)/_Point : 0.0;
   string reason=EnumToString(deal_reason);
   if(g_lifecycle_handle!=INVALID_HANDLE)
     {
      FileWrite(g_lifecycle_handle,
                TimeToString(event_time,TIME_DATE|TIME_SECONDS),
                TimeToString(ServerToUtc(event_time),TIME_DATE|TIME_SECONDS),
                InpVariantTag,is_open ? "OPEN" : (is_final ? "CLOSE" : "CLOSE_PARTIAL"),
                deal_type==DEAL_TYPE_BUY ? "BUY" : "SELL",DoubleToString(volume,8),
                DoubleToString(price,_Digits),DoubleToString(g_active_sl,_Digits),DoubleToString(g_active_tp,_Digits),
                reason,"0",StringFormat("%I64u",deal),StringFormat("%I64u",order_id),_Symbol,
                StringFormat("%I64u",position_id),DoubleToString(g_active_entry,_Digits),
                DoubleToString(g_active_sl,_Digits),DoubleToString(g_active_tp,_Digits),
                DoubleToString(risk_points,4),DoubleToString(g_active_risk_account,8),reason,reason,
                DoubleToString(achieved_r,8),DoubleToString(aggregate_net,8),DoubleToString(swap,8),
                DoubleToString(commission,8),DoubleToString(fee,8),DoubleToString(profit,8),
                DoubleToString(commission,8),DoubleToString(swap,8),DoubleToString(fee,8),
                DoubleToString(profit+commission+swap+fee,8),is_final ? "1" : "0",
                SignalName(g_active_signal),InpHypothesisId);
      FileFlush(g_lifecycle_handle);
     }
   if(is_final)
     {
      g_final_closes++;
      g_active_position_id=0;
      g_active_signal=SIGNAL_NONE;
      g_active_entry=0.0; g_active_sl=0.0; g_active_tp=0.0; g_active_risk_account=0.0;
     }
   if(is_open)
      g_pending_signal=SIGNAL_NONE;
   WriteRunMeta();
  }

void RefreshRiskLocks(const datetime utc_now)
  {
   MqlDateTime p;
   TimeToStruct(utc_now,p);
   int key=DateKey(p);
   double equity=AccountInfoDouble(ACCOUNT_EQUITY);
   if(g_day_key!=key)
     {
      g_day_key=key;
      g_day_start_equity=equity;
      g_trades_today=0;
      g_daily_locked=false;
     }
   if(g_peak_equity<=0.0 || equity>g_peak_equity)
      g_peak_equity=equity;
   if(g_day_start_equity>0.0 && 100.0*(g_day_start_equity-equity)/g_day_start_equity>=InpMaxDailyLossPct)
      g_daily_locked=true;
   if(g_peak_equity>0.0 && 100.0*(g_peak_equity-equity)/g_peak_equity>=InpMaxAccountDrawdownPct)
      g_account_locked=true;
  }

void ManagePosition(const datetime utc_now)
  {
   ulong ticket=OwnedPositionTicket();
   if(ticket==0 || !PositionSelectByTicket(ticket))
      return;
   MqlDateTime p;
   TimeToStruct(utc_now,p);
   int minute=MinuteOfDay(p);
   if(p.day_of_week==5 && minute>=InpFridayFlattenMinutesUtc)
     {
      if(CloseOwnedPosition(ticket,"FRIDAY_FLAT")) g_friday_flatten_closes++;
      return;
     }
   if(minute>=InpDailyFlattenMinutesUtc)
     {
      if(CloseOwnedPosition(ticket,"DAILY_FLAT")) g_daily_flatten_closes++;
      return;
     }
   datetime opened=(datetime)PositionGetInteger(POSITION_TIME);
   if(opened>0 && TimeCurrent()-opened>=InpMaxHoldBars*SECONDS_PER_M5_BAR)
     {
      if(CloseOwnedPosition(ticket,"MAX_HOLD")) g_max_hold_closes++;
     }
  }

bool IsNewM5Bar()
  {
   datetime value=iTime(_Symbol,PERIOD_M5,0);
   if(value<=0 || value==g_last_bar_time)
      return(false);
   g_last_bar_time=value;
   return(true);
  }

bool ValidateInputs()
  {
   if(!InpResearchAutoMode || !InpEnableTelemetry || _Period!=PERIOD_M5)
      return(false);
   if(InpExpectedSymbol!=_Symbol || StringFind(InpHypothesisId,"HYP-AIRQMB-")!=0 ||
      InpHypothesisId=="UNREGISTERED_BUILD_ONLY")
      return(false);
   if(InpMagic<=0 || InpRiskPercent<=0.0 || InpRiskPercent>1.0 ||
      InpMaxDailyLossPct<=0.0 || InpMaxDailyLossPct>3.5 ||
      InpMaxAccountDrawdownPct<=0.0 || InpMaxAccountDrawdownPct>8.0 ||
      InpMaxTradesPerDay<1 || InpMaxTradesPerDay>5 ||
      InpMaxSpreadToStop<=0.0 || InpMaxSpreadToStop>0.50 ||
      InpDeviationPoints<0 || InpMaxHoldBars<1 || InpMaxHoldBars>288 ||
      InpTradeStartMinutesUtc<0 || InpTradeStartMinutesUtc>=InpDailyFlattenMinutesUtc ||
      InpDailyFlattenMinutesUtc>1440 || InpFridayFlattenMinutesUtc>1440 ||
      InpMinAIConfidence<0.25 || InpMinAIConfidence>0.90 ||
      InpStopHalfWidthMult<0.25 || InpStopHalfWidthMult>3.0 ||
      InpRewardRisk<0.50 || InpRewardRisk>4.0 ||
      InpRangeQQEExtreme<0.0 || InpTrendQQEMin<0.0 || InpEntryCooldownBars<0)
      return(false);
   return(true);
  }

int OnInit()
  {
   if(!ValidateInputs())
     {
      Print("AIRQMB fail-closed: registered hypothesis, matching symbol, telemetry and M5 are mandatory.");
      return(INIT_PARAMETERS_INCORRECT);
     }
   // Headless integration: preserve every mathematical/model default while
   // disabling chart objects, visible plots and alerts that have no role in an
   // EA/tester consumer.  AIRD otherwise rebuilds a 24-row dashboard plus
   // regime objects every bar, which dominates multi-year research runtime.
   g_ai_handle=iCustom(_Symbol,PERIOD_M5,"AlphaFactory\\AI_Regime_Detection",
                       0.92,0.010,0.010,true,0,0.05,1,2.0,
                       50,14,20,300,14,
                       false,false,false,false,false,0,1,
                       C'0,230,118',C'255,23,68',C'68,138,255',C'255,179,0',
                       false,false,false);
   g_mbb_handle=iCustom(_Symbol,PERIOD_M5,"AlphaFactory\\Modern_Bollinger_Bands_GBB",
                        0,20,0,0,2.0,97.5,2.5,4,80,2,30,
                        20,252,70.0,55.0,20.0,5,0.25,
                        true,false,false,false,5,
                        C'61,165,232',C'232,163,61',C'125,220,130',C'220,125,125',
                        false,false,false,false,D'2023.01.01 00:00');
   g_qqe_handle=iCustom(_Symbol,PERIOD_M5,"AlphaFactory\\QQE_MOD",
                        6,5,3.0,3.0,PRICE_CLOSE,
                        6,5,1.61,3.0,PRICE_CLOSE,
                        50,0.35,true,clrBlack,C'112,112,112',C'0,195,255',
                        C'255,0,98',C'130,130,130',2,2,
                        false,false,false,false);
   if(g_ai_handle==INVALID_HANDLE || g_mbb_handle==INVALID_HANDLE || g_qqe_handle==INVALID_HANDLE)
     {
      PrintFormat("AIRQMB indicator handle failure ai=%d mbb=%d qqe=%d error=%d",g_ai_handle,g_mbb_handle,g_qqe_handle,GetLastError());
      return(INIT_FAILED);
     }
   g_last_bar_time=iTime(_Symbol,PERIOD_M5,0);
   datetime utc=ServerToUtc(TimeCurrent());
   RefreshRiskLocks(utc);
   if(!OpenTelemetry())
      return(INIT_FAILED);
   PrintFormat("AIRQMB init hyp=%s symbol=%s confidence=%.2f rr=%.2f stop_hw=%.2f",
               InpHypothesisId,_Symbol,InpMinAIConfidence,InpRewardRisk,InpStopHalfWidthMult);
   return(INIT_SUCCEEDED);
  }

void OnDeinit(const int reason)
  {
   WriteRunMeta();
   if(g_lifecycle_handle!=INVALID_HANDLE)
     {
      FileFlush(g_lifecycle_handle);
      FileClose(g_lifecycle_handle);
     }
   if(g_ai_handle!=INVALID_HANDLE) IndicatorRelease(g_ai_handle);
   if(g_mbb_handle!=INVALID_HANDLE) IndicatorRelease(g_mbb_handle);
   if(g_qqe_handle!=INVALID_HANDLE) IndicatorRelease(g_qqe_handle);
  }

void OnTradeTransaction(const MqlTradeTransaction &trans,
                        const MqlTradeRequest &request,
                        const MqlTradeResult &result)
  {
   if(trans.type==TRADE_TRANSACTION_DEAL_ADD && trans.deal>0)
      LogLifecycleDeal(trans.deal);
  }

void OnTick()
  {
   g_ticks_seen++;
   if(!IsNewM5Bar())
      return;
   g_closed_bars_seen++;

   // Every decision made by this EA is bar-close based.  Server-side SL/TP
   // remains tick-accurate, while clock conversion, account scans and custom
   // indicator reads run once per M5 bar instead of once per market tick.
   datetime utc_now=ServerToUtc(TimeCurrent());
   RefreshRiskLocks(utc_now);
   ManagePosition(utc_now);
   if(OwnedPositionTicket()!=0)
      return;

   MqlDateTime p;
   TimeToStruct(utc_now,p);
   int minute=MinuteOfDay(p);
   if(p.day_of_week==0 || p.day_of_week==6 ||
      (p.day_of_week==5 && minute>=InpFridayFlattenMinutesUtc) ||
      minute<InpTradeStartMinutesUtc || minute>=InpDailyFlattenMinutesUtc)
     {
      g_reject_session++;
      return;
     }
   if(g_daily_locked) { g_reject_daily_lock++; return; }
   if(g_account_locked) { g_reject_account_lock++; return; }
   if(g_trades_today>=InpMaxTradesPerDay) { g_reject_trade_limit++; return; }
   if(OwnedPositionTicket()!=0 || HasForeignSymbolPosition()) { g_reject_exposure++; return; }
   if(InpEntryCooldownBars>0 && g_last_entry_bar_time>0 &&
      g_last_bar_time-g_last_entry_bar_time<InpEntryCooldownBars*SECONDS_PER_M5_BAR)
      return;

   EnsembleSnapshot s;
   if(!ReadSnapshot(s))
     {
      g_indicator_not_ready++;
      return;
     }
   g_indicator_ready++;
   if(s.regime==0) g_regime_bull++;
   else if(s.regime==1) g_regime_bear++;
   else if(s.regime==2) g_regime_range++;
   else g_regime_highvol++;

   TradeDecision d;
   if(!BuildDecision(s,d))
     {
      g_no_signal++;
      return;
     }
   int magnitude=(int)MathAbs((double)d.signal);
   if(magnitude==1) g_s1_signals++;
   else if(magnitude==2) g_s2_signals++;
   else if(magnitude==3) g_s3_signals++;
   SubmitEntry(d);
  }
