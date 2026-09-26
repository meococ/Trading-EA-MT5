//+------------------------------------------------------------------+
//| EA_SessionMomentum.mq5                                           |
//| SessionMomentum (SM) - M5 session-open with-trend continuation   |
//| sleeve. Frozen spec: research/HYP-SMOM-JPY-M5-001                |
//| _FROZEN_PREREG.md. Do not change behaviour without a new         |
//| hypothesis ID.                                                   |
//|                                                                  |
//| Legs (per-symbol enable flags):                                  |
//|   LDN - first-2h wick pierce of the prior ASIA full-session      |
//|         extreme (00:00-07:00 GMT), entered WITH direction at the |
//|         next bar open, held to the 16:00 GMT London close.       |
//|   NY  - first-2h wick pierce of the prior LDN partial extreme    |
//|         (07:00-12:00 GMT), entered WITH direction at the next    |
//|         bar open, held to the 20:00 GMT NY close.                |
//| Catastrophe SL = sl_atr x ATR14 (sizing anchor, non-binding);    |
//| TP=10R never binds - the real exit is the leg time-stop.         |
//|                                                                  |
//| Shared substrate: clock/DST/news from LSW_Session.mqh, sizing    |
//| and broker geometry from LSW_Risk.mqh (synthetic-sweep adapter), |
//| execution kernel and lifecycle telemetry from _Shared.           |
//+------------------------------------------------------------------+
#property strict
#property version   "1.00"
#property description "SessionMomentum - M5 session-open with-trend continuation"

#define AF_EXEC_EXPERIMENTAL_MUTATION_ENABLED 1
#include "../_Shared/Execution/AF_ExecutionKernel.mqh"

#include <Trade/Trade.mqh>

#include "../EA_LiquiditySweep/Include/LSW_Types.mqh"
#include "../EA_LiquiditySweep/Include/LSW_Session.mqh"
#include "../EA_LiquiditySweep/Include/LSW_Signal.mqh"
#include "../EA_LiquiditySweep/Include/LSW_Risk.mqh"
#include "Include/SM_Types.mqh"
#include "Include/SM_Signal.mqh"
#include "Include/SM_Telemetry.mqh"
#include "../_Shared/Telemetry/AF_LifecycleTelemetry.mqh"

#define SM_STRATEGY_ID              "SM"
#define SM_MAX_EXIT_ATTEMPTS_PER_BAR 5

//+------------------------------------------------------------------+
//| Inputs                                                           |
//+------------------------------------------------------------------+
input group "=== Identity and execution ==="
input ulong  InpMagic                   = 26451826;    // Magic number
input ulong  InpSlippagePoints          = 20;          // Max deviation (points)

input group "=== Clock ==="
input int    InpServerGmtOffsetHours    = 2;           // Server offset from GMT, winter
input bool   InpServerDstUsRule         = true;        // Server adds +1h on US DST
input int    InpFlattenHourServer       = 22;          // Hard flat at this server hour
input int    InpFridayFlattenHourServer = 20;          // Friday hard flat, server hour

input group "=== SessionMomentum legs ==="
input bool   InpUseLdn                  = true;        // LEG_LDN: ASIA-extreme pierce, continue
input bool   InpUseNy                   = true;        // LEG_NY: LDN-extreme pierce, continue
input int    InpLdnTrigEndMin           = 540;         // LDN trigger window end, GMT min
input int    InpNyTrigEndMin            = 840;         // NY trigger window end, GMT min
input int    InpLdnExitMin              = 960;         // LDN time-exit, GMT min
input int    InpNyExitMin               = 1200;        // NY time-exit, GMT min
input double InpSlAtr                   = 25.0;        // Catastrophe SL, xATR14

input group "=== Exit engineering (HYP-002) ==="
input double InpBeTriggerPips           = 15.0;        // BE move trigger, pips floating
input double InpBeBufferPips            = 2.0;         // BE offset beyond entry, pips
input double InpTrailActPips            = 20.0;        // Trail activation, pips favorable
input double InpTrailDistPips           = 12.0;        // Chandelier distance, pips
input int    InpInvCutHours             = 2;           // Invalidation min age, hours (0=off)
input double InpInvCutMinMfePips        = 10.0;        // Invalidation MFE threshold, pips

input group "=== Filters and risk ==="
input double InpMaxSpreadAtr            = 0.0;         // Max spread as xATR (0=off)
input double InpMinAtrPoints            = 0.0;         // Volatility floor, points (0=off)
input int    InpNewsBlackoutMin         = 20;          // News blackout +/- minutes, 0=off
input double InpRiskPercent             = 0.35;        // Risk per trade, % of equity
input int    InpMaxTradesPerDay         = 6;           // Max entries per server day
input int    InpMaxConsecutiveLosses    = 4;           // Streak lock, 0=off
input double InpMaxDailyLossPct         = 2.0;         // Daily loss lock, %
input double InpMaxAccountDdPct         = 0.0;         // Account DD lock, % (0=off)

input group "=== Telemetry ==="
input bool   InpVerboseLog              = true;        // Per-decision signal/reject lines
input bool   InpEnableTelemetry         = true;        // AlphaFactory lifecycle telemetry
input string InpHypothesisId            = "HYP-SMOM-JPY-M5-001";

//+------------------------------------------------------------------+
//| Globals                                                          |
//+------------------------------------------------------------------+
LswConfig           g_cfg;
SmParams            g_p;
LswCounters         g_cnt;
LswRiskState        g_risk;
SmDayState          g_day;
CAFExecutionKernel *g_exec=NULL;
CTrade              g_trade;

int                 g_atr_handle=INVALID_HANDLE;
datetime            g_last_bar_time=0;
datetime            g_submit_bar_time=0;
long                g_signal_id=0;
long                g_active_sid=0;
bool                g_runtime_failed=false;

//--- Live position mirror. Rebuilt from the terminal every tick.
ulong               g_pos_ticket=0;
int                 g_pos_direction=LSW_DIR_NONE;
double              g_pos_open_price=0.0;
double              g_pos_risk_distance=0.0;
int                 g_pos_leg=SM_LEG_NONE;

//--- Exit-engineering state (HYP-002): favorable peak + MFE tracking.
double              g_pos_peak=0.0;
double              g_pos_mfe_pips=0.0;
datetime            g_pos_open_time=0;
bool                g_pos_be_done=false;

//--- Per-leg attribution (SM_LEG_* indexed).
long                g_leg_signals[SM_LEG_COUNT];
long                g_leg_trades[SM_LEG_COUNT];

//--- Carried from the submitted plan to the fill.
int                 g_pending_leg=SM_LEG_NONE;
double              g_pending_risk_distance=0.0;

//--- Exit-attempt throttle so a permanently failing close cannot spam.
datetime            g_exit_bar=0;
int                 g_exit_attempts=0;

//+------------------------------------------------------------------+
//| Ownership scans. All fail-closed.                                |
//+------------------------------------------------------------------+
int SmFindOwnedPosition(ulong &ticket)
  {
   ticket=0;
   int owned=0;
   for(int i=PositionsTotal()-1;i>=0;i--)
     {
      const ulong current=PositionGetTicket(i);
      if(current==0)
         return(-1);
      if(PositionGetString(POSITION_SYMBOL)!=_Symbol)
         continue;
      if((ulong)PositionGetInteger(POSITION_MAGIC)!=g_cfg.magic)
         continue;
      ticket=current;
      owned++;
     }
   return(owned);
  }

int SmCountSymbolPositions()
  {
   int count=0;
   for(int i=PositionsTotal()-1;i>=0;i--)
     {
      const ulong current=PositionGetTicket(i);
      if(current==0)
         return(-1);
      if(PositionGetString(POSITION_SYMBOL)==_Symbol)
         count++;
     }
   return(count);
  }

int SmCountOwnedOrders()
  {
   int count=0;
   for(int i=OrdersTotal()-1;i>=0;i--)
     {
      const ulong current=OrderGetTicket(i);
      if(current==0)
         return(-1);
      if(OrderGetString(ORDER_SYMBOL)!=_Symbol)
         continue;
      if((ulong)OrderGetInteger(ORDER_MAGIC)!=g_cfg.magic)
         continue;
      count++;
     }
   return(count);
  }

//+------------------------------------------------------------------+
//| Execution kernel lifecycle                                       |
//+------------------------------------------------------------------+
bool SmResetKernel()
  {
   if(CheckPointer(g_exec)!=POINTER_INVALID)
     {
      delete g_exec;
      g_exec=NULL;
     }
   g_exec=new CAFExecutionKernel();
   if(CheckPointer(g_exec)==POINTER_INVALID)
      return(false);
   if(!g_exec.Configure(_Symbol,g_cfg.magic,SM_STRATEGY_ID))
      return(false);
   g_exec.Reconcile();
   return(true);
  }

void SmMaybeRecycleKernel(const datetime bar_time)
  {
   if(CheckPointer(g_exec)==POINTER_INVALID)
      return;
   const AF_EXEC_STATE state=g_exec.State();
   if(state==AF_EXEC_IDLE)
      return;
   if(g_submit_bar_time!=0 && bar_time==g_submit_bar_time)
      return;                                   // never recycle on the submit bar
   ulong owned_ticket=0;
   if(SmFindOwnedPosition(owned_ticket)!=0)
      return;
   if(SmCountOwnedOrders()!=0)
      return;

   if(state==AF_EXEC_PENDING_NEW || state==AF_EXEC_ORDER_PLACED ||
      state==AF_EXEC_PARTIALLY_FILLED)
      g_cnt.entry_timeouts++;
   if(state==AF_EXEC_RECOVERING_AMBIGUOUS)
      g_cnt.kernel_ambiguous++;
   if(SmResetKernel())
      g_cnt.kernel_recycles++;
   else
      g_runtime_failed=true;
  }

//+------------------------------------------------------------------+
//| Position mirror and exits                                        |
//+------------------------------------------------------------------+
void SmSyncPosition()
  {
   ulong ticket=0;
   const int owned=SmFindOwnedPosition(ticket);
   if(owned<0)
      return;                                   // transient scan race: retry next tick
   if(owned==0)
     {
      if(g_pos_ticket!=0)
        {
         g_pos_ticket=0;
         g_pos_direction=LSW_DIR_NONE;
         g_pos_open_price=0.0;
         g_pos_risk_distance=0.0;
         g_pos_leg=SM_LEG_NONE;
         g_pos_peak=0.0;
         g_pos_mfe_pips=0.0;
         g_pos_open_time=0;
         g_pos_be_done=false;
        }
      return;
     }
   if(owned>1)
      g_runtime_failed=true;                    // must be impossible: one per symbol
   if(ticket==g_pos_ticket)
      return;
   if(!PositionSelectByTicket(ticket))
      return;

   g_pos_ticket=ticket;
   g_pos_open_price=PositionGetDouble(POSITION_PRICE_OPEN);
   g_pos_direction=(((ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_BUY)
                    ? LSW_DIR_LONG : LSW_DIR_SHORT);
   const double position_sl=PositionGetDouble(POSITION_SL);
   const double position_tp=PositionGetDouble(POSITION_TP);
   const double volume=PositionGetDouble(POSITION_VOLUME);
   g_pos_risk_distance=(position_sl>0.0 ? MathAbs(g_pos_open_price-position_sl)
                        : g_pending_risk_distance);
   g_pos_leg=g_pending_leg;
   g_pos_peak=g_pos_open_price;
   g_pos_mfe_pips=0.0;
   g_pos_open_time=(datetime)PositionGetInteger(POSITION_TIME);
   g_pos_be_done=false;

   double money_per_lot=0.0;
   double realized_risk=0.0;
   if(g_pos_risk_distance>0.0 && position_sl>0.0 &&
      LswMoneyRiskPerLot(_Symbol,g_pos_direction,g_pos_open_price,position_sl,
                         g_pos_risk_distance,money_per_lot))
      realized_risk=money_per_lot*volume;
   SmLogPosition(g_active_sid,g_pos_ticket,volume,g_pos_open_price,
                 position_sl,position_tp,realized_risk);
  }

bool SmClosePosition(const string reason)
  {
   if(g_pos_ticket==0)
      return(true);
   const datetime bar_time=iTime(_Symbol,PERIOD_M5,0);
   if(bar_time!=g_exit_bar)
     {
      g_exit_bar=bar_time;
      g_exit_attempts=0;
     }
   if(g_exit_attempts>=SM_MAX_EXIT_ATTEMPTS_PER_BAR)
      return(false);
   g_exit_attempts++;

   g_trade.SetExpertMagicNumber(g_cfg.magic);
   g_trade.SetDeviationInPoints(g_cfg.slippage_points);
   const ulong ticket=g_pos_ticket;
   const bool sent=g_trade.PositionClose(ticket,g_cfg.slippage_points);
   const uint retcode=g_trade.ResultRetcode();
   const bool ok=(sent && (retcode==TRADE_RETCODE_DONE ||
                           retcode==TRADE_RETCODE_DONE_PARTIAL));
   SmLogExit(g_active_sid,reason,ticket,ok,retcode);
   if(!ok)
      g_cnt.exit_reject++;
   return(ok);
  }

double SmPipSize()
  {
   const int digits=(int)SymbolInfoInteger(_Symbol,SYMBOL_DIGITS);
   const double point=SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   return((digits==3 || digits==5) ? point*10.0 : point);
  }

//--- Ratchet SL toward profit only, min 1-pip step between modifies
//--- (broker-realistic granularity; keeps tester journal under cap).
bool SmModifySl(const double new_sl,const string reason)
  {
   if(g_pos_ticket==0 || !PositionSelectByTicket(g_pos_ticket))
      return(false);
   const double cur_sl=PositionGetDouble(POSITION_SL);
   const double cur_tp=PositionGetDouble(POSITION_TP);
   const double step=SmPipSize();
   if(g_pos_direction>0 && new_sl<cur_sl+step)
      return(false);                             // never loosen a long SL
   if(g_pos_direction<0 && cur_sl>0.0 && new_sl>cur_sl-step)
      return(false);                             // never loosen a short SL
   g_trade.SetExpertMagicNumber(g_cfg.magic);
   const bool ok=g_trade.PositionModify(g_pos_ticket,new_sl,cur_tp);
   PrintFormat("SM001_SLMOD reason=%s ticket=%I64u sl=%.5f->%.5f ok=%s ret=%u",
               reason,g_pos_ticket,cur_sl,new_sl,(ok ? "true" : "false"),
               g_trade.ResultRetcode());
   return(ok);
  }

void SmManageOpenPosition(const LswClock &clk_now,const int gmt_min_now)
  {
   if(g_pos_ticket==0)
      return;
   //--- Hard flats first: structural, not a preference.
   if(clk_now.friday_flatten)
     {
      if(SmClosePosition("FRIDAY_FLAT"))
         g_cnt.exit_friday_flat++;
      return;
     }
   if(clk_now.flatten)
     {
      if(SmClosePosition("DAILY_FLAT"))
         g_cnt.exit_daily_flat++;
      return;
     }
   //--- Exit engineering (HYP-002): favorable-peak tracking, premise-
   //--- invalidation cut, BE move, chandelier trail. Prices are tick-level;
   //--- no bar data is consumed here, so the audit surface is unchanged.
   const double pip=SmPipSize();
   MqlTick mtick;
   if(!SymbolInfoTick(_Symbol,mtick) || mtick.bid<=0.0 || mtick.ask<=0.0)
      return;
   const double fav_px=(g_pos_direction>0 ? mtick.bid : mtick.ask);
   const double fav_pips=(fav_px-g_pos_open_price)*g_pos_direction/pip;
   if((g_pos_direction>0 && fav_px>g_pos_peak) ||
      (g_pos_direction<0 && fav_px<g_pos_peak))
      g_pos_peak=fav_px;
   if(fav_pips>g_pos_mfe_pips)
      g_pos_mfe_pips=fav_pips;

   const int age_sec=(int)(TimeCurrent()-g_pos_open_time);
   if(InpInvCutHours>0 && age_sec>=InpInvCutHours*3600 &&
      fav_pips<0.0 && g_pos_mfe_pips<InpInvCutMinMfePips)
     {
      if(SmClosePosition("INV_CUT"))
         g_cnt.exit_time_stop++;
      return;
     }
   if(!g_pos_be_done && g_pos_mfe_pips>=InpBeTriggerPips)
     {
      const double be_sl=g_pos_open_price+g_pos_direction*InpBeBufferPips*pip;
      if(SmModifySl(be_sl,"BE_MOVE"))
         g_pos_be_done=true;
     }
   if(g_pos_mfe_pips>=InpTrailActPips)
     {
      const double trail_sl=g_pos_peak-g_pos_direction*InpTrailDistPips*pip;
      SmModifySl(trail_sl,"TRAIL");
     }
   //--- Leg time-stop: the real exit. LDN -> 16:00 GMT, NY -> 20:00 GMT.
   const int exit_min=SmLegExitMin(g_pos_leg,g_p);
   if(exit_min>=0 && gmt_min_now>=exit_min)
     {
      if(SmClosePosition("LEG_TIME_STOP"))
         g_cnt.exit_time_stop++;
      return;
     }
  }

//+------------------------------------------------------------------+
//| Signal -> filters -> plan -> submit. One path for both legs.     |
//+------------------------------------------------------------------+
void SmTryEnter(SmSignal &sig,const LswClock &clk_now,const datetime bar0_time,
                const double atr)
  {
   const long sid=++g_signal_id;
   g_cnt.signals_seen++;
   if(sig.direction>0)
      g_cnt.signals_long++;
   else
      g_cnt.signals_short++;
   if(sig.leg>SM_LEG_NONE && sig.leg<SM_LEG_COUNT)
      g_leg_signals[sig.leg]++;
   sig.atr=atr;
   SmLogSignal(sid,sig,clk_now,g_cfg.verbose);

   //--- Entry filters, one counter per reject.
   if(clk_now.weekend || clk_now.rollover || clk_now.flatten)
     {
      if(clk_now.rollover)
         g_cnt.filt_rollover++;
      else if(clk_now.flatten)
         g_cnt.filt_flatten++;
      else
         g_cnt.filt_session++;
      SmLogReject(sid,"FILTER","SESSION",g_cfg.verbose);
      return;
     }
   const int symbol_positions=SmCountSymbolPositions();
   const int owned_orders=SmCountOwnedOrders();
   if(symbol_positions<0 || owned_orders<0)
     {
      g_cnt.data_fail++;
      SmLogReject(sid,"FILTER","SCAN_FAIL",g_cfg.verbose);
      return;
     }
   if(symbol_positions!=0)
     {
      g_cnt.filt_position_open++;
      SmLogReject(sid,"FILTER","POSITION_OPEN",g_cfg.verbose);
      return;
     }
   if(CheckPointer(g_exec)==POINTER_INVALID || g_exec.State()!=AF_EXEC_IDLE ||
      owned_orders!=0)
     {
      g_cnt.filt_exec_busy++;
      SmLogReject(sid,"FILTER","EXEC_BUSY",g_cfg.verbose);
      return;
     }
   if(LswRiskBlocked(g_risk,g_cfg,g_cnt))
     {
      SmLogReject(sid,"FILTER","RISK_LOCK",g_cfg.verbose);
      return;
     }

   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick) || tick.ask<=0.0 || tick.bid<=0.0 ||
      tick.ask<=tick.bid)
     {
      g_cnt.data_fail++;
      return;
     }
   const double point=SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   if(!LswFinite(point) || point<=0.0)
     {
      g_cnt.data_fail++;
      return;
     }
   if(atr<g_cfg.min_atr_points*point)
     {
      g_cnt.filt_atr_floor++;
      SmLogReject(sid,"FILTER","ATR_FLOOR",g_cfg.verbose);
      return;
     }
   if(g_cfg.max_spread_atr>0.0 && tick.ask-tick.bid>g_cfg.max_spread_atr*atr)
     {
      g_cnt.filt_spread++;
      SmLogReject(sid,"FILTER","SPREAD",g_cfg.verbose);
      return;
     }
   bool news_empty=false;
   const bool news_block=LswNewsBlackout(_Symbol,bar0_time,g_cfg.news_blackout_min,
                                         news_empty);
   if(news_empty)
      g_cnt.news_query_empty++;
   if(news_block)
     {
      g_cnt.filt_news++;
      SmLogReject(sid,"FILTER","NEWS",g_cfg.verbose);
      return;
     }

   //--- Synthetic sweep adapter: catastrophe SL = sl_atr x ATR beyond entry,
   //--- TP = tp_r x risk (10R: never binds; the leg time-stop is the exit).
   LswSweep sweep;
   ZeroMemory(sweep);
   sweep.valid=true;
   sweep.direction=sig.direction;
   sweep.atr=atr;
   const double entry_ref=(sig.direction>0 ? tick.ask : tick.bid);
   sweep.extreme=entry_ref-sig.direction*g_p.sl_atr*atr;
   LswPlan plan;
   if(!LswBuildPlan(_Symbol,sweep,g_cfg,tick.ask,tick.bid,plan))
     {
      if(plan.reject=="SIZING" || plan.reject=="VOLUME" || plan.reject=="MARGIN")
         g_cnt.entry_reject_sizing++;
      else if(plan.reject=="STOPS_LEVEL" || plan.reject=="BAD_GEOMETRY")
         g_cnt.entry_reject_geometry++;
      else
         g_cnt.entry_reject_plan++;
      SmLogReject(sid,"PLAN",plan.reject,g_cfg.verbose);
      return;
     }
   SmLogRequest(sid,plan,sig,g_cfg.risk_percent);

   const ENUM_ORDER_TYPE order_type=(plan.direction>0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL);
   const bool submitted=g_exec.SubmitMarket(order_type,plan.volume,plan.sl,plan.tp,
                                            g_cfg.slippage_points);
   SmLogOrder(sid,submitted,(int)g_exec.State(),g_exec.RequestId(),
              g_exec.OrderTicket(),g_exec.LastRetcode());
   if(!submitted)
     {
      g_cnt.entry_reject_submit++;
      return;
     }
   g_cnt.entries_submitted++;
   g_risk.daily_entries++;
   g_active_sid=sid;
   g_submit_bar_time=bar0_time;
   g_pending_leg=sig.leg;
   g_pending_risk_distance=plan.risk_distance;
   AfTele_SetPlannedRisk(plan.risk_distance/point,
                         AccountInfoDouble(ACCOUNT_EQUITY)*g_cfg.risk_percent/100.0);
  }

//+------------------------------------------------------------------+
//| Closed-bar decision                                              |
//+------------------------------------------------------------------+
void SmDecide(const datetime bar0_time,const LswClock &clk_now)
  {
   g_cnt.decisions++;

   double atr=0.0;
   if(!LswAtrAt(g_atr_handle,1,atr))
     {
      g_cnt.data_fail++;
      return;
     }

   //--- Both legs evaluate the just-closed bar (shift 1). Closed-bar only.
   MqlRates bar;
   ZeroMemory(bar);
   if(!LswBarAt(_Symbol,1,bar))
     {
      g_cnt.data_fail++;
      return;
     }
   if((long)bar0_time-(long)bar.time!=SM_SEC_PER_M5)
     {
      g_cnt.filt_bar_gap++;
      return;
     }
   LswClock clk_bar;
   if(!LswClockRead(bar.time,g_cfg,clk_bar))
     {
      g_cnt.data_fail++;
      return;
     }
   MqlDateTime gb;
   TimeToStruct(clk_bar.gmt_time,gb);
   const int gmt_min=gb.hour*60+gb.min;
   const int day_key=(int)(clk_bar.gmt_time/86400);

   SmSignal sig;
   if(g_p.use_ldn &&
      SmDetectCont(_Symbol,bar,gmt_min,day_key,SM_LEG_LDN,g_p.ldn,g_day,sig))
     {
      SmTryEnter(sig,clk_now,bar0_time,atr);
      return;                                   // at most one entry per bar
     }
   if(g_p.use_ny &&
      SmDetectCont(_Symbol,bar,gmt_min,day_key,SM_LEG_NY,g_p.ny,g_day,sig))
      SmTryEnter(sig,clk_now,bar0_time,atr);
  }

//+------------------------------------------------------------------+
//| Input validation. Fail closed at init.                           |
//+------------------------------------------------------------------+
bool SmValidateInputs()
  {
   string bad="";
   if(InpMagic==0)
      bad="InpMagic";
   else if(InpLdnTrigEndMin<=420 || InpLdnTrigEndMin>960)
      bad="InpLdnTrigEndMin";
   else if(InpNyTrigEndMin<=720 || InpNyTrigEndMin>1200)
      bad="InpNyTrigEndMin";
   else if(InpLdnExitMin<=InpLdnTrigEndMin || InpLdnExitMin>1439)
      bad="InpLdnExitMin";
   else if(InpNyExitMin<=InpNyTrigEndMin || InpNyExitMin>1439)
      bad="InpNyExitMin";
   else if(InpSlAtr<1.0 || InpSlAtr>60.0)
      bad="InpSlAtr";
   else if(InpBeTriggerPips<0.0 || InpBeTriggerPips>200.0)
      bad="InpBeTriggerPips";
   else if(InpBeBufferPips<0.0 || InpBeBufferPips>50.0)
      bad="InpBeBufferPips";
   else if(InpTrailActPips<0.0 || InpTrailActPips>300.0)
      bad="InpTrailActPips";
   else if(InpTrailDistPips<0.5 || InpTrailDistPips>100.0)
      bad="InpTrailDistPips";
   else if(InpInvCutHours<0 || InpInvCutHours>48)
      bad="InpInvCutHours";
   else if(InpInvCutMinMfePips<0.0 || InpInvCutMinMfePips>100.0)
      bad="InpInvCutMinMfePips";
   else if(InpMaxSpreadAtr<0.0 || InpMaxSpreadAtr>1.0)
      bad="InpMaxSpreadAtr";
   else if(InpMinAtrPoints<0.0)
      bad="InpMinAtrPoints";
   else if(InpRiskPercent<=0.0 || InpRiskPercent>5.0)
      bad="InpRiskPercent";
   else if(!InpUseLdn && !InpUseNy)
      bad="InpUseLdn|InpUseNy";
   if(bad!="")
     {
      PrintFormat("SM001_INIT_FAIL bad_input=%s",bad);
      return(false);
     }
   return(true);
  }

//+------------------------------------------------------------------+
//| Config                                                           |
//+------------------------------------------------------------------+
void SmConfigure()
  {
   ZeroMemory(g_cfg);
   g_cfg.server_gmt_offset_hours=InpServerGmtOffsetHours;
   g_cfg.server_dst_us_rule=InpServerDstUsRule;
   g_cfg.session_mode=LSW_SESS_BOTH;            // SM gates on GMT stamps itself
   g_cfg.flatten_hour_server=InpFlattenHourServer;
   g_cfg.friday_flatten_hour_server=InpFridayFlattenHourServer;
   g_cfg.sl_buffer_atr=0.10;                    // pad beyond synthetic extreme
   g_cfg.min_sl_spread_mult=4.0;
   g_cfg.tp_r=10.0;                             // never binds: time-stop exits
   g_cfg.max_hold_bars=0;                       // leg time-stop owns the exit
   g_cfg.be_at_r=0.0;                           // off: faithful to probe
   g_cfg.max_spread_atr=InpMaxSpreadAtr;
   g_cfg.min_atr_points=InpMinAtrPoints;
   g_cfg.news_blackout_min=InpNewsBlackoutMin;
   g_cfg.risk_percent=InpRiskPercent;
   g_cfg.max_trades_per_day=InpMaxTradesPerDay;
   g_cfg.max_consecutive_losses=InpMaxConsecutiveLosses;
   g_cfg.max_daily_loss_pct=InpMaxDailyLossPct;
   g_cfg.max_account_dd_pct=InpMaxAccountDdPct;
   g_cfg.magic=InpMagic;
   g_cfg.slippage_points=InpSlippagePoints;
   g_cfg.verbose=InpVerboseLog;

   ZeroMemory(g_p);
   g_p.use_ldn=InpUseLdn;
   g_p.use_ny=InpUseNy;
   g_p.ldn.open_min=420;                        // frozen spec: ASIA 00-07 -> LDN
   g_p.ldn.trig_end=InpLdnTrigEndMin;
   g_p.ldn.prior_start=0;
   g_p.ldn.prior_end=420;
   g_p.ldn.exit_min=InpLdnExitMin;
   g_p.ny.open_min=720;                         // frozen spec: LDN 07-12 -> NY
   g_p.ny.trig_end=InpNyTrigEndMin;
   g_p.ny.prior_start=420;
   g_p.ny.prior_end=720;
   g_p.ny.exit_min=InpNyExitMin;
   g_p.sl_atr=InpSlAtr;
  }

//+------------------------------------------------------------------+
//| Event handlers                                                   |
//+------------------------------------------------------------------+
bool ReadSeriesInteger(const ENUM_TIMEFRAMES timeframe,
                       const ENUM_SERIES_INFO_INTEGER property,
                       long &value)
  {
   value=0;
   ResetLastError();
   if(!SeriesInfoInteger(_Symbol,timeframe,property,value))
      return(false);
   return(GetLastError()==0);
  }

bool EmitD0SeriesProof()
  {
   long m5_synchronized=0;
   long m5_first_epoch=0;
   long m5_terminal_first_epoch=0;
   long m1_server_first_epoch=0;
   long m1_terminal_first_epoch=0;
   long m5_bars=0;
   if(!ReadSeriesInteger(PERIOD_M5,SERIES_SYNCHRONIZED,m5_synchronized) ||
      !ReadSeriesInteger(PERIOD_M5,SERIES_FIRSTDATE,m5_first_epoch) ||
      !ReadSeriesInteger(PERIOD_M5,SERIES_TERMINAL_FIRSTDATE,m5_terminal_first_epoch) ||
      !ReadSeriesInteger(PERIOD_M1,SERIES_SERVER_FIRSTDATE,m1_server_first_epoch) ||
      !ReadSeriesInteger(PERIOD_M1,SERIES_TERMINAL_FIRSTDATE,m1_terminal_first_epoch) ||
      !ReadSeriesInteger(PERIOD_M5,SERIES_BARS_COUNT,m5_bars))
      return(false);

   ResetLastError();
   const long terminal_maxbars=TerminalInfoInteger(TERMINAL_MAXBARS);
   const int terminal_error=GetLastError();
   datetime copytime_values[];
   ArraySetAsSeries(copytime_values,false);
   const datetime copytime_from=(datetime)m5_first_epoch;
   ResetLastError();
   const int copytime_result=CopyTime(_Symbol,PERIOD_M5,copytime_from,1,copytime_values);
   const int copytime_error=GetLastError();
   const long copytime_first_epoch=(copytime_result==1 ? (long)copytime_values[0] : 0);

   PrintFormat("DATA_EPOCH_D0_SERIES_PROOF symbol=%s m5_synchronized=%I64d m5_first_epoch=%I64d m5_terminal_first_epoch=%I64d m1_server_first_epoch=%I64d m1_terminal_first_epoch=%I64d m5_bars=%I64d terminal_maxbars=%I64d copytime_from_epoch=%I64d copytime_count=1 copytime_result=%d copytime_first_epoch=%I64d copytime_last_error=%d",
               _Symbol,m5_synchronized,m5_first_epoch,m5_terminal_first_epoch,
               m1_server_first_epoch,m1_terminal_first_epoch,m5_bars,terminal_maxbars,
               (long)copytime_from,copytime_result,copytime_first_epoch,copytime_error);
   if(m5_synchronized!=1 || m5_first_epoch<=0 || m5_terminal_first_epoch<=0 ||
      m1_server_first_epoch<=0 || m1_terminal_first_epoch<=0 || m5_bars<=0 ||
      terminal_maxbars<=0 || terminal_error!=0 || copytime_result!=1 ||
      copytime_first_epoch!=m5_first_epoch || copytime_error!=0)
      return(false);
   return(true);
  }

int OnInit()
  {
   if(!EmitD0SeriesProof())
     {
      Print("SM_FATAL reason=D0_SERIES_PROOF");
      return(INIT_FAILED);
     }
   if(!SmValidateInputs())
      return(INIT_PARAMETERS_INCORRECT);

   SmConfigure();
   ZeroMemory(g_cnt);
   ZeroMemory(g_risk);
   ZeroMemory(g_day);
   ArrayInitialize(g_leg_signals,0);
   ArrayInitialize(g_leg_trades,0);
   g_runtime_failed=false;
   g_pos_ticket=0;
   g_pos_direction=LSW_DIR_NONE;
   g_pos_open_price=0.0;
   g_pos_risk_distance=0.0;
   g_pos_leg=SM_LEG_NONE;
   g_pending_leg=SM_LEG_NONE;
   g_pending_risk_distance=0.0;
   g_submit_bar_time=0;
   g_exit_bar=0;
   g_exit_attempts=0;

   g_atr_handle=iATR(_Symbol,PERIOD_M5,14);
   if(g_atr_handle==INVALID_HANDLE)
     {
      PrintFormat("SM001_INIT_REJECT reason=atr_handle error=%d",GetLastError());
      return(INIT_FAILED);
     }

   g_trade.SetExpertMagicNumber(g_cfg.magic);
   g_trade.SetDeviationInPoints(g_cfg.slippage_points);
   g_trade.SetMarginMode();
   g_trade.SetTypeFillingBySymbol(_Symbol);

   if(!SmResetKernel())
     {
      Print("SM001_INIT_REJECT reason=kernel_configure");
      if(g_atr_handle!=INVALID_HANDLE)IndicatorRelease(g_atr_handle);
      return(INIT_FAILED);
     }

   SmLogClockDiag(g_cfg.server_gmt_offset_hours,g_cfg.server_dst_us_rule);

   //--- Warm-up: never decide on the bar that was already forming at attach.
   g_last_bar_time=iTime(_Symbol,PERIOD_M5,0);
   SmSyncPosition();
   if(!AfTele_OnInit("EA_SessionMomentum",InpHypothesisId,InpEnableTelemetry))
      { if(g_atr_handle!=INVALID_HANDLE)IndicatorRelease(g_atr_handle); return(INIT_FAILED); }
   return(INIT_SUCCEEDED);
  }

void OnDeinit(const int reason)
  {
   AfTele_OnDeinit();
   SmSummary(g_cnt,g_leg_signals,g_leg_trades,reason,g_runtime_failed);
   if(g_atr_handle!=INVALID_HANDLE)
     {
      IndicatorRelease(g_atr_handle);
      g_atr_handle=INVALID_HANDLE;
     }
   if(CheckPointer(g_exec)!=POINTER_INVALID)
     {
      delete g_exec;
      g_exec=NULL;
     }
  }

void OnTick()
  {
   const datetime server_now=TimeCurrent();
   LswRiskRefresh(g_risk,server_now,g_cfg);
   SmSyncPosition();

   LswClock clk;
   if(!LswClockRead(server_now,g_cfg,clk))
     {
      g_cnt.data_fail++;
      return;
     }

   //--- Closed-bar edge. iTime(...,0) is only a TIMESTAMP read: no price from
   //--- the forming bar ever reaches a decision.
   const datetime bar0=iTime(_Symbol,PERIOD_M5,0);
   const bool new_bar=(bar0>0 && bar0!=g_last_bar_time);
   if(new_bar)
     {
      g_last_bar_time=bar0;
      g_cnt.closed_bars++;
     }

   //--- Exits run on every tick: leg time-stops and the hard flats.
   MqlDateTime gb0;
   TimeToStruct(clk.gmt_time,gb0);
   SmManageOpenPosition(clk,gb0.hour*60+gb0.min);

   if(!new_bar)
      return;
   //--- A latched runtime failure stops NEW risk but never stops the exits.
   if(g_runtime_failed)
      return;

   SmMaybeRecycleKernel(bar0);

   //--- The clock used for the entry filters is the confirmation bar's CLOSE,
   //--- which is exactly the forming bar's open time.
   LswClock clk_decision;
   if(!LswClockRead(bar0,g_cfg,clk_decision))
     {
      g_cnt.data_fail++;
      return;
     }
   SmDecide(bar0,clk_decision);
  }

void OnTradeTransaction(const MqlTradeTransaction &trans,
                        const MqlTradeRequest &request,
                        const MqlTradeResult &result)
  {
   AfTele_OnTransaction(trans,(long)g_cfg.magic);
   if(CheckPointer(g_exec)!=POINTER_INVALID)
      g_exec.OnTradeTransaction(trans,request,result);

   if(trans.type!=TRADE_TRANSACTION_DEAL_ADD || trans.deal==0)
      return;
   if(!HistoryDealSelect(trans.deal))
      return;
   if(HistoryDealGetString(trans.deal,DEAL_SYMBOL)!=_Symbol)
      return;
   if((ulong)HistoryDealGetInteger(trans.deal,DEAL_MAGIC)!=g_cfg.magic)
      return;

   const ENUM_DEAL_ENTRY entry=
      (ENUM_DEAL_ENTRY)HistoryDealGetInteger(trans.deal,DEAL_ENTRY);
   const double volume=HistoryDealGetDouble(trans.deal,DEAL_VOLUME);
   const double price=HistoryDealGetDouble(trans.deal,DEAL_PRICE);
   const double net=HistoryDealGetDouble(trans.deal,DEAL_PROFIT)+
                    HistoryDealGetDouble(trans.deal,DEAL_SWAP)+
                    HistoryDealGetDouble(trans.deal,DEAL_COMMISSION);
   SmLogDeal(g_active_sid,trans.deal,(int)entry,volume,price,net);

   if(entry==DEAL_ENTRY_IN)
     {
      g_cnt.entries_filled++;
      if(g_pending_leg>SM_LEG_NONE && g_pending_leg<SM_LEG_COUNT)
         g_leg_trades[g_pending_leg]++;
      g_pos_risk_distance=g_pending_risk_distance;
      return;
     }
   if(entry==DEAL_ENTRY_OUT || entry==DEAL_ENTRY_OUT_BY)
     {
      g_cnt.deals_out++;
      if(net<0.0)
         g_cnt.deals_out_loss++;
      LswRegisterClosedDeal(g_risk,g_cfg,net);
     }
  }
//+------------------------------------------------------------------+
