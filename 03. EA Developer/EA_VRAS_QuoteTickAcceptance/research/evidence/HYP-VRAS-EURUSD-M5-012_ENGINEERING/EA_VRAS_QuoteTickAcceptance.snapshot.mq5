//+------------------------------------------------------------------+
//| EA_VRAS_QuoteTickAcceptance.mq5                                  |
//| HYP-VRAS-EURUSD-M5-012 — collection-only quote-tick acceptance   |
//| Frozen closed-bar arm + causal OnTick observation FSM.           |
//| NO orders, NO SL/TP, NO sizing, NO deal-transaction hooks.       |
//+------------------------------------------------------------------+
#property copyright "AlphaFactory research"
#property version   "1.00"
#property strict
#property description "HYP-012 forward quote-tick acceptance collection only"
#property description "Closed-bar arm + causal OnTick FSM; never places trades"

input bool   InpCollectionOnly=true;
input string InpHypothesisId="HYP-VRAS-EURUSD-M5-012";
input int    InpH1EmaPeriod=200;
input int    InpRollingVwapBars=48;
input int    InpPrearmRingSize=60;
input int    InpPrearmMinQuotes=30;
input int    InpAcceptAgeMinMs=30000;
input int    InpAcceptAgeMaxMs=120000;
input int    InpMinQuoteUpdates=20;
input int    InpMinPriceChanges=12;
input double InpMinImbalance=0.60;
input double InpMaxSpreadRatio=1.50;
input int    InpMaxGapMs=15000;

const string EA_NAME="EA_VRAS_QuoteTickAcceptance";
const string SCHEMA_VERSION="vras_quote_acceptance.v1";
const string TELEMETRY_PROFILE="none";

#define DIR_NONE  0
#define DIR_LONG  1
#define DIR_SHORT -1

#define ST_IDLE     0
#define ST_PENDING  1
#define ST_ACTIVE   2
#define ST_TERMINAL 3

int      g_h1_ema_handle=INVALID_HANDLE;
datetime g_last_m5_bar=0;
string   g_run_id="";
string   g_csv_name="";
int      g_csv_handle=INVALID_HANDLE;
string   g_data_source="";

// Pre-arm ring of unique chronological spreads (price units).
double   g_prearm_spreads[];
int      g_prearm_count=0;
int      g_prearm_head=0; // next write index in ring
long     g_last_quote_time_msc=0;
double   g_last_valid_bid=0.0;
double   g_last_valid_ask=0.0;

// Arm / FSM state
int      g_state=ST_IDLE;
int      g_direction=DIR_NONE;
int      g_pending_direction=DIR_NONE;
double   g_pending_vwap=0.0;
datetime g_pending_arm_bar_time=0;
double   g_frozen_vwap=0.0;
datetime g_arm_bar_time=0;
long     g_arm_time_msc=0;
double   g_arm_bid=0.0;
double   g_arm_ask=0.0;
double   g_arm_mid=0.0;
double   g_arm_spread=0.0;
double   g_prearm_median=0.0;
double   g_prearm_median_points=0.0;
double   g_last_mid=0.0;
long     g_last_obs_time_msc=0;
int      g_quote_updates=0;
int      g_price_changes=0;
int      g_directional_moves=0;
int      g_opposite_moves=0;
long     g_max_gap_ms=0;
double   g_max_spread_since_arm=0.0;
string   g_terminal_event="";

//+------------------------------------------------------------------+
bool IdentityOk()
  {
   if(!InpCollectionOnly)
      return false;
   if(InpHypothesisId!="HYP-VRAS-EURUSD-M5-012")
      return false;
   if(_Symbol!="EURUSD")
      return false;
   if(_Period!=PERIOD_M5)
      return false;
   if(InpH1EmaPeriod!=200)
      return false;
   if(InpRollingVwapBars!=48)
      return false;
   if(InpPrearmRingSize!=60)
      return false;
   if(InpPrearmMinQuotes!=30)
      return false;
   if(InpAcceptAgeMinMs!=30000)
      return false;
   if(InpAcceptAgeMaxMs!=120000)
      return false;
   if(InpMinQuoteUpdates!=20)
      return false;
   if(InpMinPriceChanges!=12)
      return false;
   if(MathAbs(InpMinImbalance-0.60)>1e-12)
      return false;
   if(MathAbs(InpMaxSpreadRatio-1.50)>1e-12)
      return false;
   if(InpMaxGapMs!=15000)
      return false;
   return true;
  }

//+------------------------------------------------------------------+
string DirectionLabel(const int direction)
  {
   if(direction==DIR_LONG)
      return "long";
   if(direction==DIR_SHORT)
      return "short";
   return "none";
  }

//+------------------------------------------------------------------+
string EventTimeUtc(const long time_msc)
  {
   datetime sec=(datetime)(time_msc/1000);
   MqlDateTime value;
   if(!TimeToStruct(sec,value))
      return "";
   int millis=(int)(time_msc%1000);
   if(millis<0)
      millis+=1000;
   return StringFormat("%04d-%02d-%02dT%02d:%02d:%02d.%03dZ",
                       value.year,value.mon,value.day,value.hour,value.min,
                       value.sec,millis);
  }

//+------------------------------------------------------------------+
bool QuoteValid(const long time_msc,const double bid,const double ask,const long last_time_msc)
  {
   if(last_time_msc>0 && time_msc<=last_time_msc)
      return false;
   if(!MathIsValidNumber(bid) || !MathIsValidNumber(ask))
      return false;
   if(bid<=0.0 || ask<=0.0)
      return false;
   if(ask<bid)
      return false;
   return true;
  }

//+------------------------------------------------------------------+
void PrearmPush(const double spread)
  {
   if(InpPrearmRingSize<=0)
      return;
   if(ArraySize(g_prearm_spreads)!=InpPrearmRingSize)
     {
      ArrayResize(g_prearm_spreads,InpPrearmRingSize);
      ArrayInitialize(g_prearm_spreads,0.0);
      g_prearm_count=0;
      g_prearm_head=0;
     }
   g_prearm_spreads[g_prearm_head]=spread;
   g_prearm_head=(g_prearm_head+1)%InpPrearmRingSize;
   if(g_prearm_count<InpPrearmRingSize)
      g_prearm_count++;
  }

//+------------------------------------------------------------------+
double PrearmMedian()
  {
   if(g_prearm_count<=0)
      return 0.0;
   double tmp[];
   ArrayResize(tmp,g_prearm_count);
   if(g_prearm_count<InpPrearmRingSize)
     {
      for(int i=0;i<g_prearm_count;i++)
         tmp[i]=g_prearm_spreads[i];
     }
   else
     {
      // Ring is full: logical order starts at head (oldest).
      for(int i=0;i<g_prearm_count;i++)
         tmp[i]=g_prearm_spreads[(g_prearm_head+i)%InpPrearmRingSize];
     }
   ArraySort(tmp);
   int n=g_prearm_count;
   if((n%2)==1)
      return tmp[n/2];
   return 0.5*(tmp[n/2-1]+tmp[n/2]);
  }

//+------------------------------------------------------------------+
double CalculateRollingVwap()
  {
   double sum_pv=0.0;
   double sum_v=0.0;
   MqlRates history[];
   ArraySetAsSeries(history,true);
   // Closed-bar only: shifts 1..InpRollingVwapBars
   if(CopyRates(_Symbol,PERIOD_M5,1,InpRollingVwapBars,history)!=InpRollingVwapBars)
      return 0.0;
   for(int index=0;index<InpRollingVwapBars;index++)
     {
      double typical=(history[index].high+history[index].low+history[index].close)/3.0;
      long volume=history[index].tick_volume;
      if(volume<=0)
         continue;
      sum_pv+=typical*(double)volume;
      sum_v+=(double)volume;
     }
   return sum_v>0.0 ? sum_pv/sum_v : 0.0;
  }

//+------------------------------------------------------------------+
bool ReadH1Closed(double &h1_close,double &h1_ema)
  {
   double ema_buffer[1];
   // Closed-bar only: H1 EMA200 and close at shift 1
   if(CopyBuffer(g_h1_ema_handle,0,1,1,ema_buffer)!=1)
      return false;
   h1_close=iClose(_Symbol,PERIOD_H1,1);
   h1_ema=ema_buffer[0];
   return h1_close>0.0 && h1_ema>0.0 && MathIsValidNumber(h1_close) && MathIsValidNumber(h1_ema);
  }

//+------------------------------------------------------------------+
int EvaluateClosedBarSignal(const MqlRates &bars[],const double h1_close,
                            const double h1_ema,const double vwap)
  {
   // bars[0]=shift1, bars[1]=shift2 (ArraySetAsSeries true)
   if(vwap<=0.0)
      return DIR_NONE;
   if(h1_close>h1_ema && bars[0].low<=vwap && bars[0].close>vwap &&
      bars[0].close>bars[1].high)
      return DIR_LONG;
   if(h1_close<h1_ema && bars[0].high>=vwap && bars[0].close<vwap &&
      bars[0].close<bars[1].low)
      return DIR_SHORT;
   return DIR_NONE;
  }

//+------------------------------------------------------------------+
double Imbalance()
  {
   int denom=g_directional_moves+g_opposite_moves;
   if(denom<=0)
      return 0.0;
   return (double)g_directional_moves/(double)denom;
  }

//+------------------------------------------------------------------+
bool OpenTelemetry()
  {
   // Terminal-local Files area only (common shared files flag is forbidden).
   g_run_id=StringFormat("%s_%I64d_%u",
                         InpHypothesisId,
                         (long)TimeGMT(),
                         (uint)GetTickCount());
   g_csv_name=StringFormat("vras_qta_%s.csv",g_run_id);
   g_csv_handle=FileOpen(g_csv_name,FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_REWRITE,',');
   if(g_csv_handle==INVALID_HANDLE)
     {
      PrintFormat("QTA file open failed name=%s err=%d",g_csv_name,GetLastError());
      return false;
     }
   FileWrite(g_csv_handle,
             "schema_version","hypothesis_id","run_id","event_time_msc","event_time_utc",
             "symbol","event","direction","arm_bar_time","arm_time_msc","age_ms",
             "bid","ask","mid","spread_points","prearm_median_spread_points",
             "quote_updates","price_changes","directional_moves","opposite_moves",
             "imbalance","directional_net_points","max_gap_ms","max_spread_ratio",
             "frozen_vwap","data_source","promotion_eligible");
   FileFlush(g_csv_handle);
   return true;
  }

//+------------------------------------------------------------------+
void WriteEvent(const string event_name,const long time_msc,
                const double bid,const double ask)
  {
   if(g_csv_handle==INVALID_HANDLE)
      return;
   double mid=(bid+ask)*0.5;
   double spr_pts=(_Point>0.0) ? (ask-bid)/_Point : 0.0;
   long age_ms=0;
   if(g_arm_time_msc>0)
      age_ms=time_msc-g_arm_time_msc;
   double net_pts=0.0;
   if(g_arm_time_msc>0 && _Point>0.0)
     {
      double sign=(g_direction==DIR_LONG) ? 1.0 : -1.0;
      net_pts=sign*(mid-g_arm_mid)/_Point;
     }
   double max_ratio=0.0;
   if(g_prearm_median>0.0)
      max_ratio=g_max_spread_since_arm/g_prearm_median;
   // promotion_eligible is always false
   FileWrite(g_csv_handle,
             SCHEMA_VERSION,
             InpHypothesisId,
             g_run_id,
             IntegerToString(time_msc),
             EventTimeUtc(time_msc),
             _Symbol,
             event_name,
             DirectionLabel(g_direction),
             TimeToString(g_arm_bar_time,TIME_DATE|TIME_SECONDS),
             IntegerToString(g_arm_time_msc),
             IntegerToString(age_ms),
             DoubleToString(bid,_Digits),
             DoubleToString(ask,_Digits),
             DoubleToString(mid,_Digits+1),
             DoubleToString(spr_pts,2),
             DoubleToString(g_prearm_median_points,2),
             IntegerToString(g_quote_updates),
             IntegerToString(g_price_changes),
             IntegerToString(g_directional_moves),
             IntegerToString(g_opposite_moves),
             DoubleToString(Imbalance(),6),
             DoubleToString(net_pts,4),
             IntegerToString(g_max_gap_ms),
             DoubleToString(max_ratio,6),
             DoubleToString(g_frozen_vwap,_Digits),
             g_data_source,
             "false");
   FileFlush(g_csv_handle);
  }

//+------------------------------------------------------------------+
void ClearPending()
  {
   g_pending_direction=DIR_NONE;
   g_pending_vwap=0.0;
   g_pending_arm_bar_time=0;
  }

//+------------------------------------------------------------------+
void ResetArmCounters()
  {
   g_quote_updates=0;
   g_price_changes=0;
   g_directional_moves=0;
   g_opposite_moves=0;
   g_max_gap_ms=0;
   g_max_spread_since_arm=0.0;
   g_terminal_event="";
  }

//+------------------------------------------------------------------+
void TerminateArm(const string terminal,const long time_msc,
                  const double bid,const double ask)
  {
   g_terminal_event=terminal;
   g_state=ST_TERMINAL;
   WriteEvent(terminal,time_msc,bid,ask);
   // Immutable terminal for this arm; idle for a future arm.
   g_state=ST_IDLE;
   g_direction=DIR_NONE;
   ClearPending();
  }

//+------------------------------------------------------------------+
bool VwapViolated(const double bid,const double ask)
  {
   if(g_direction==DIR_LONG)
      return bid<=g_frozen_vwap;
   if(g_direction==DIR_SHORT)
      return ask>=g_frozen_vwap;
   return true;
  }

//+------------------------------------------------------------------+
bool AcceptanceGates(const double bid,const double ask,const long age_ms)
  {
   if(age_ms<InpAcceptAgeMinMs || age_ms>InpAcceptAgeMaxMs)
      return false;
   if(g_quote_updates<InpMinQuoteUpdates)
      return false;
   if(g_price_changes<InpMinPriceChanges)
      return false;
   if(Imbalance()<InpMinImbalance)
      return false;
   double sign=(g_direction==DIR_LONG) ? 1.0 : -1.0;
   double mid=(bid+ask)*0.5;
   double net_exp=sign*(mid-g_arm_mid);
   if(net_exp<g_arm_spread)
      return false;
   double cur_spread=ask-bid;
   if(cur_spread>g_prearm_median)
      return false;
   if(g_max_spread_since_arm>InpMaxSpreadRatio*g_prearm_median)
      return false;
   if(g_max_gap_ms>InpMaxGapMs)
      return false;
   if(VwapViolated(bid,ask))
      return false;
   return true;
  }

//+------------------------------------------------------------------+
void TryFreezeArm(const long time_msc,const double bid,const double ask)
  {
   if(g_state!=ST_PENDING)
      return;
   if(g_prearm_count<InpPrearmMinQuotes)
     {
      // Fail-closed: insufficient pre-arm history.
      ClearPending();
      g_state=ST_IDLE;
      if(QuoteValid(time_msc,bid,ask,g_last_quote_time_msc))
        {
         g_last_quote_time_msc=time_msc;
         g_last_valid_bid=bid;
         g_last_valid_ask=ask;
         PrearmPush(ask-bid);
        }
      return;
     }
   if(!QuoteValid(time_msc,bid,ask,g_last_quote_time_msc))
      return;

   g_prearm_median=PrearmMedian();
   if(g_prearm_median<=0.0 || !MathIsValidNumber(g_prearm_median))
     {
      ClearPending();
      g_state=ST_IDLE;
      g_last_quote_time_msc=time_msc;
      g_last_valid_bid=bid;
      g_last_valid_ask=ask;
      PrearmPush(ask-bid);
      return;
     }
   g_prearm_median_points=(_Point>0.0) ? g_prearm_median/_Point : 0.0;
   g_direction=g_pending_direction;
   g_frozen_vwap=g_pending_vwap;
   g_arm_bar_time=g_pending_arm_bar_time;
   g_arm_time_msc=time_msc;
   g_arm_bid=bid;
   g_arm_ask=ask;
   g_arm_mid=(bid+ask)*0.5;
   g_arm_spread=ask-bid;
   g_last_mid=g_arm_mid;
   g_last_obs_time_msc=time_msc;
   ResetArmCounters();
   g_max_spread_since_arm=g_arm_spread;
   g_state=ST_ACTIVE;
   ClearPending();
   g_last_quote_time_msc=time_msc;
   g_last_valid_bid=bid;
   g_last_valid_ask=ask;
   WriteEvent("ARMED",time_msc,bid,ask);
  }

//+------------------------------------------------------------------+
void ProcessActiveQuote(const long time_msc,const double bid,const double ask)
  {
   if(g_state!=ST_ACTIVE)
      return;
   if(!QuoteValid(time_msc,bid,ask,g_last_quote_time_msc))
     {
      long receipt_time=MathMax(time_msc,g_last_quote_time_msc+1);
      TerminateArm("REJECT_INVALID_QUOTE",receipt_time,
                   g_last_valid_bid,g_last_valid_ask);
      return;
     }

   long gap=time_msc-g_last_obs_time_msc;
   if(gap>g_max_gap_ms)
      g_max_gap_ms=gap;
   double cur_spread=ask-bid;
   if(cur_spread>g_max_spread_since_arm)
      g_max_spread_since_arm=cur_spread;

   double mid=(bid+ask)*0.5;
   g_quote_updates++;
   if(mid!=g_last_mid)
     {
      g_price_changes++;
      if(g_direction==DIR_LONG)
        {
         if(mid>g_last_mid)
            g_directional_moves++;
         else if(mid<g_last_mid)
            g_opposite_moves++;
        }
      else if(g_direction==DIR_SHORT)
        {
         if(mid<g_last_mid)
            g_directional_moves++;
         else if(mid>g_last_mid)
            g_opposite_moves++;
        }
     }
   g_last_mid=mid;
   g_last_obs_time_msc=time_msc;
   g_last_quote_time_msc=time_msc;
   g_last_valid_bid=bid;
   g_last_valid_ask=ask;
   long age_ms=time_msc-g_arm_time_msc;

   if(VwapViolated(bid,ask))
     {
      TerminateArm("REJECT_VWAP_RECROSS",time_msc,bid,ask);
      return;
     }
   if(g_prearm_median>0.0 &&
      g_max_spread_since_arm>InpMaxSpreadRatio*g_prearm_median)
     {
      TerminateArm("REJECT_SPREAD_SPIKE",time_msc,bid,ask);
      return;
     }
   if(g_max_gap_ms>InpMaxGapMs)
     {
      TerminateArm("REJECT_STALE_GAP",time_msc,bid,ask);
      return;
     }
   if(age_ms>InpAcceptAgeMaxMs)
     {
      TerminateArm("EXPIRE_NO_ACCEPTANCE",time_msc,bid,ask);
      return;
     }
   if(AcceptanceGates(bid,ask,age_ms))
     {
      TerminateArm("ACCEPTED_OBSERVATION",time_msc,bid,ask);
      return;
     }
   WriteEvent("OBSERVE",time_msc,bid,ask);
  }

//+------------------------------------------------------------------+
void ProcessIdleOrPrearm(const long time_msc,const double bid,const double ask)
  {
   if(!QuoteValid(time_msc,bid,ask,g_last_quote_time_msc))
      return;
   g_last_quote_time_msc=time_msc;
   g_last_valid_bid=bid;
   g_last_valid_ask=ask;
   PrearmPush(ask-bid);
  }

//+------------------------------------------------------------------+
void MaybeArmFromClosedBar()
  {
   // At most one active/pending arm.
   if(g_state==ST_ACTIVE || g_state==ST_PENDING)
      return;
   datetime current_bar=iTime(_Symbol,PERIOD_M5,0);
   if(current_bar<=0)
      return;
   if(current_bar==g_last_m5_bar)
      return;
   g_last_m5_bar=current_bar;

   MqlRates bars[];
   ArraySetAsSeries(bars,true);
   // Closed-bar only: M5 shifts 1 and 2 (plus shift3 not required)
   if(CopyRates(_Symbol,PERIOD_M5,1,3,bars)!=3)
      return;
   double h1_close=0.0;
   double h1_ema=0.0;
   if(!ReadH1Closed(h1_close,h1_ema))
      return;
   double vwap=CalculateRollingVwap();
   int signal=EvaluateClosedBarSignal(bars,h1_close,h1_ema,vwap);
   if(signal==DIR_NONE)
      return;
   g_pending_direction=signal;
   g_pending_vwap=vwap;
   g_pending_arm_bar_time=bars[0].time;
   g_state=ST_PENDING;
  }

//+------------------------------------------------------------------+
int OnInit()
  {
   if(!IdentityOk())
     {
      Print("QTA identity fail-closed: require EURUSD M5 HYP-VRAS-EURUSD-M5-012 exact defaults collection-only");
      return INIT_FAILED;
     }
   g_h1_ema_handle=iMA(_Symbol,PERIOD_H1,InpH1EmaPeriod,0,MODE_EMA,PRICE_CLOSE);
   if(g_h1_ema_handle==INVALID_HANDLE)
     {
      Print("QTA H1 EMA handle invalid");
      return INIT_FAILED;
     }
   ArrayResize(g_prearm_spreads,InpPrearmRingSize);
   ArrayInitialize(g_prearm_spreads,0.0);
   g_prearm_count=0;
   g_prearm_head=0;
   g_last_quote_time_msc=0;
   g_last_valid_bid=0.0;
   g_last_valid_ask=0.0;
   g_last_m5_bar=0;
   g_state=ST_IDLE;
   ClearPending();
   ResetArmCounters();
   g_data_source=MQLInfoInteger(MQL_TESTER) ? "SYNTHETIC_TESTER_TICKS" : "LIVE_QUOTES";
   if(!OpenTelemetry())
      return INIT_FAILED;
   PrintFormat("QTA init hypothesis=%s collection_only=true closed_bar_arm=true causal_ontick=true data_source=%s promotion_eligible=false telemetry_profile=%s",
               InpHypothesisId,g_data_source,TELEMETRY_PROFILE);
   return INIT_SUCCEEDED;
  }

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
  {
   if(g_state==ST_ACTIVE)
     {
      MqlTick tick;
      long t_msc=0;
      double bid=g_arm_bid;
      double ask=g_arm_ask;
      if(SymbolInfoTick(_Symbol,tick))
        {
         t_msc=tick.time_msc;
         bid=tick.bid;
         ask=tick.ask;
        }
      if(t_msc<=0)
         t_msc=(long)TimeCurrent()*1000;
      if(t_msc<=g_last_quote_time_msc || !QuoteValid(t_msc,bid,ask,0))
        {
         t_msc=g_last_quote_time_msc+1;
         if(g_last_valid_bid>0.0 && g_last_valid_ask>=g_last_valid_bid)
           {
            bid=g_last_valid_bid;
            ask=g_last_valid_ask;
           }
        }
      TerminateArm("DEINIT_ACTIVE_ARM",t_msc,bid,ask);
     }
   if(g_csv_handle!=INVALID_HANDLE)
     {
      FileFlush(g_csv_handle);
      FileClose(g_csv_handle);
      g_csv_handle=INVALID_HANDLE;
     }
   if(g_h1_ema_handle!=INVALID_HANDLE)
     {
      IndicatorRelease(g_h1_ema_handle);
      g_h1_ema_handle=INVALID_HANDLE;
     }
  }

//+------------------------------------------------------------------+
// Causal OnTick: quote evidence AFTER a closed-bar arm is intentional.
// Signal/arm creation uses only shift>=1 closed bars (see MaybeArmFromClosedBar).
//+------------------------------------------------------------------+
void OnTick()
  {
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick))
      return;
   long time_msc=tick.time_msc;
   double bid=tick.bid;
   double ask=tick.ask;

   // New M5 bar may create a pending closed-bar arm (no overwrite of active).
   MaybeArmFromClosedBar();

   if(g_state==ST_PENDING)
      TryFreezeArm(time_msc,bid,ask);
   else if(g_state==ST_ACTIVE)
      ProcessActiveQuote(time_msc,bid,ask);
   else
      ProcessIdleOrPrearm(time_msc,bid,ask);
  }

//+------------------------------------------------------------------+
// Collection-only: no trade requests, no position mutation, no deal hooks.
//+------------------------------------------------------------------+
