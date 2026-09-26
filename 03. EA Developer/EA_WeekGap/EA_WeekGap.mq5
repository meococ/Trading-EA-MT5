//+------------------------------------------------------------------+
//| EA_WeekGap.mq5                                                   |
//| WeekGap (WG) - weekend gap-down fade at the week reopen's second |
//| hour. Frozen spec: research/HYP-WGAP-JPY-M1-001_FROZEN_PREREG.md |
//|                                                                  |
//| Mechanism (honest label): when USDJPY gaps DOWN at the weekly    |
//| reopen (weekend risk-off = yen bid), USDJPY drifts UP during the |
//| 01:01-02:01 server window Monday. Probe: +2.16p/PF1.54 at        |
//| recorded cost, n=450, 2010-2026. CALIBRATION RUN ONLY - ~0.51    |
//| trades/week, permanently sub-GOAL-cadence; it exists to validate |
//| probe<->governed transfer on a real anomaly.                     |
//|                                                                  |
//| Substrate: clock/DST/news from LSW_Session.mqh, sizing/margin/   |
//| stops-level helpers from LSW_Risk.mqh, execution kernel and      |
//| lifecycle telemetry from _Shared. Do not change behaviour here   |
//| without a new hypothesis ID.                                     |
//+------------------------------------------------------------------+
#property strict
#property version   "1.00"
#property description "WeekGap - weekend gap-down fade, Monday reopen hour-2"

//--- The shared kernel is fail-closed by default; an adopting EA must opt in
//--- explicitly. This define MUST precede the include.
#define AF_EXEC_EXPERIMENTAL_MUTATION_ENABLED 1
#include "../_Shared/Execution/AF_ExecutionKernel.mqh"

#include <Trade/Trade.mqh>

#include "../EA_LiquiditySweep/Include/LSW_Types.mqh"
#include "../EA_LiquiditySweep/Include/LSW_Session.mqh"
#include "../EA_LiquiditySweep/Include/LSW_Risk.mqh"
#include "Include/WG_Telemetry.mqh"
#include "../_Shared/Telemetry/AF_LifecycleTelemetry.mqh"

#define WG_STRATEGY_ID              "WG"
#define WG_MAX_EXIT_ATTEMPTS_PER_BAR 5
#define WG_MAX_GAP_SCAN_BARS        300

//+------------------------------------------------------------------+
//| Inputs                                                           |
//+------------------------------------------------------------------+
input group "=== Identity and execution ==="
input ulong  InpMagic                   = 26451824;    // Magic number
input ulong  InpSlippagePoints          = 20;          // Max deviation (points)

input group "=== Clock ==="
input int    InpServerGmtOffsetHours    = 2;           // Server offset from GMT, winter
input bool   InpServerDstUsRule         = true;        // Server adds +1h on US DST
input int    InpFlattenHourServer       = 22;          // Hard flat at this server hour
input int    InpFridayFlattenHourServer = 20;          // Friday hard flat, server hour

input group "=== Signal (server clock) ==="
input int    InpSignalDowServer         = 1;           // Signal day-of-week (1=Mon, MQL5)
input int    InpSignalHourServer        = 1;           // Signal bar hour, server
input int    InpSignalMinuteServer      = 0;           // Signal bar minute, server
input double InpGapThreshPips           = 2.0;         // Weekend gap must be < -this

input group "=== Exit ==="
input double InpSlPips                  = 20.0;        // Fixed stop loss, pips
input int    InpMaxHoldBars             = 61;          // Time stop, M1 bars held
                                                     // (entry bar 01:01 + 61 -> exit
                                                     // at 02:02 event = close of the
                                                     // 02:01 bar = lab c[entry+60])

input group "=== Filters and risk ==="
input double InpMaxSpreadPips           = 8.0;         // Safety cap only, pips
input int    InpNewsBlackoutMin         = 20;          // News blackout +/- minutes, 0=off
input double InpRiskPercent             = 0.25;        // Risk per trade, % of equity
input int    InpMaxTradesPerDay         = 2;           // Max entries per server day
input int    InpMaxConsecutiveLosses    = 4;           // Streak lock, 0=off
input double InpMaxDailyLossPct         = 2.0;         // Daily loss lock, %
input double InpMaxAccountDdPct         = 10.0;        // Account drawdown lock, %

input group "=== Telemetry ==="
input bool   InpVerboseLog              = true;        // Per-decision signal/reject lines
input bool   InpEnableTelemetry         = true;        // AlphaFactory lifecycle telemetry
input string InpHypothesisId            = "HYP-WGAP-JPY-M1-001";

//+------------------------------------------------------------------+
//| Globals                                                          |
//+------------------------------------------------------------------+
LswConfig           g_cfg;
LswCounters         g_cnt;
LswRiskState        g_risk;
CAFExecutionKernel *g_exec=NULL;
CTrade              g_trade;

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
int                 g_pos_bars_held=0;

double              g_pending_risk_distance=0.0;

datetime            g_exit_bar=0;
int                 g_exit_attempts=0;

//+------------------------------------------------------------------+
//| One closed M1 bar at an explicit shift. The guard is required by |
//| the non-repaint audit: shift 0 (the forming bar) is never read.  |
//+------------------------------------------------------------------+
bool WgBarAtM1(const string symbol,const int shift,MqlRates &out)
  {
   if(shift<1)
      return(false);                     // shift 0 is the forming bar: never read
   MqlRates r[];
   ArraySetAsSeries(r,true);
   ResetLastError();
   if(CopyRates(symbol,PERIOD_M1,shift,1,r)!=1)
      return(false);
   if(!LswFinite(r[0].open) || !LswFinite(r[0].high) || !LswFinite(r[0].low) ||
      !LswFinite(r[0].close) || r[0].high<r[0].low || r[0].time<=0)
      return(false);
   out=r[0];
   return(true);
  }

//+------------------------------------------------------------------+
//| Weekend gap in pips at the decision bar. Scans closed M1 bars    |
//| back from the signal bar to the first bar of its server-day (the |
//| week reopen, stamped ~00:00-00:05); gap = that bar's open minus  |
//| the close of the bar before it (Friday's last). Only OPEN/CLOSE  |
//| are read - the reopen bar's fabricated h/l are never touched.    |
//| Returns false when no day boundary is found (data hole: skip).   |
//+------------------------------------------------------------------+
bool WgWeekGapPips(const string symbol,const MqlRates &signal_bar,
                   double &gap_pips)
  {
   gap_pips=0.0;
   const int sig_day=LswDayKey(signal_bar.time);
   const double point=SymbolInfoDouble(symbol,SYMBOL_POINT);
   const int digits=(int)SymbolInfoInteger(symbol,SYMBOL_DIGITS);
   const double pip=((digits==3 || digits==5) ? point*10.0 : point);
   if(!LswFinite(pip) || pip<=0.0)
      return(false);

   MqlRates first_today;
   ZeroMemory(first_today);
   MqlRates prev_bar;
   ZeroMemory(prev_bar);
   bool found=false;
   for(int s=2;s<WG_MAX_GAP_SCAN_BARS;s++)
     {
      MqlRates b;
      if(!WgBarAtM1(symbol,s,b))
         break;                            // history exhausted: fail closed
      if(LswDayKey(b.time)!=sig_day)
        {
         //--- b is the last bar before this server-day (Friday's last).
         prev_bar=b;
         found=true;
         break;
        }
      first_today=b;
     }
   if(!found || prev_bar.time<=0)
      return(false);
   //--- Week opened at/after the signal bar: the signal bar itself is
   //--- the week's first bar. Same semantics as the lab's
   //--- first-bar-of-day convention.
   if(first_today.time<=0)
      first_today=signal_bar;
   if(!LswFinite(first_today.open) || !LswFinite(prev_bar.close))
      return(false);
   gap_pips=(first_today.open-prev_bar.close)/pip;
   return(LswFinite(gap_pips));
  }

//+------------------------------------------------------------------+
//| Fixed-pip order plan. The sweep-anchored LswBuildPlan derives SL |
//| from a swept extreme; this mechanism has no level - the stop is  |
//| a fixed pip distance. Reuses the same sizing/margin/stops-level  |
//| helpers so geometry handling stays identical to the siblings.    |
//+------------------------------------------------------------------+
bool WgBuildPlan(const string symbol,const int direction,const double sl_pips,
                 const LswConfig &cfg,const double ask,const double bid,
                 LswPlan &plan)
  {
   ZeroMemory(plan);
   plan.reject="NONE";

   const double point=SymbolInfoDouble(symbol,SYMBOL_POINT);
   const double tick_size=SymbolInfoDouble(symbol,SYMBOL_TRADE_TICK_SIZE);
   const int digits=(int)SymbolInfoInteger(symbol,SYMBOL_DIGITS);
   const double pip=((digits==3 || digits==5) ? point*10.0 : point);
   if(direction==LSW_DIR_NONE || !LswFinite(ask) || !LswFinite(bid) ||
      ask<=bid || !LswFinite(point) || point<=0.0 || !LswFinite(pip) ||
      pip<=0.0 || !LswFinite(tick_size) || tick_size<=0.0 ||
      !LswFinite(sl_pips) || sl_pips<=0.0)
     {
      plan.reject="BAD_INPUT";
      return(false);
     }

   const double entry=(direction>0 ? ask : bid);
   double risk_distance=sl_pips*pip;
   const double sl_adj=entry-direction*risk_distance;
   const double sl=(direction>0 ? LswFloorToTick(sl_adj,tick_size)
                    : LswCeilToTick(sl_adj,tick_size));
   risk_distance=MathAbs(entry-sl);
   if(!LswFinite(risk_distance) || risk_distance<=0.0)
     {
      plan.reject="BAD_DISTANCE";
      return(false);
     }

   const long stops_level=SymbolInfoInteger(symbol,SYMBOL_TRADE_STOPS_LEVEL);
   const long freeze_level=SymbolInfoInteger(symbol,SYMBOL_TRADE_FREEZE_LEVEL);
   long broker_level=(stops_level>freeze_level ? stops_level : freeze_level);
   if(broker_level<0)
      broker_level=0;
   const double min_dist=(double)broker_level*point;
   if(MathAbs(entry-sl)<min_dist)
     {
      plan.reject="STOPS_LEVEL";
      return(false);
     }
   if((direction>0 && sl>=entry) || (direction<0 && sl<=entry))
     {
      plan.reject="BAD_GEOMETRY";
      return(false);
     }

   double money_per_lot=0.0;
   if(!LswMoneyRiskPerLot(symbol,direction,entry,sl,risk_distance,money_per_lot))
     {
      plan.reject="SIZING";
      return(false);
     }
   const double equity=AccountInfoDouble(ACCOUNT_EQUITY);
   if(!LswFinite(equity) || equity<=0.0 || cfg.risk_percent<=0.0)
     {
      plan.reject="SIZING";
      return(false);
     }
   const double volume=LswNormalizeVolumeDown(symbol,
                       equity*(cfg.risk_percent/100.0)/money_per_lot);
   if(volume<=0.0)
     {
      plan.reject="VOLUME";
      return(false);
     }

   double margin=0.0;
   const ENUM_ORDER_TYPE order_type=(direction>0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL);
   const double free_margin=AccountInfoDouble(ACCOUNT_MARGIN_FREE);
   if(!OrderCalcMargin(order_type,symbol,volume,entry,margin) || !LswFinite(margin) ||
      !LswFinite(free_margin) || margin>free_margin*0.5)
     {
      plan.reject="MARGIN";
      return(false);
     }

   plan.valid=true;
   plan.direction=direction;
   plan.entry=entry;
   plan.sl=sl;
   plan.tp=0.0;                          // no take profit in this mechanism
   plan.volume=volume;
   plan.risk_distance=risk_distance;
   plan.money_per_lot=money_per_lot;
   plan.reject="";
   return(true);
  }

//+------------------------------------------------------------------+
//| Ownership scans. All fail-closed.                                |
//+------------------------------------------------------------------+
int WgFindOwnedPosition(ulong &ticket)
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

int WgCountSymbolPositions()
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

int WgCountOwnedOrders()
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
//| Execution kernel lifecycle (same recycle doctrine as SD)         |
//+------------------------------------------------------------------+
bool WgResetKernel()
  {
   if(CheckPointer(g_exec)!=POINTER_INVALID)
     {
      delete g_exec;
      g_exec=NULL;
     }
   g_exec=new CAFExecutionKernel();
   if(CheckPointer(g_exec)==POINTER_INVALID)
      return(false);
   if(!g_exec.Configure(_Symbol,g_cfg.magic,WG_STRATEGY_ID))
      return(false);
   g_exec.Reconcile();
   return(true);
  }

void WgMaybeRecycleKernel(const datetime bar_time)
  {
   if(CheckPointer(g_exec)==POINTER_INVALID)
      return;
   const AF_EXEC_STATE state=g_exec.State();
   if(state==AF_EXEC_IDLE)
      return;
   if(g_submit_bar_time!=0 && bar_time==g_submit_bar_time)
      return;
   ulong owned_ticket=0;
   if(WgFindOwnedPosition(owned_ticket)!=0)
      return;
   if(WgCountOwnedOrders()!=0)
      return;

   if(state==AF_EXEC_PENDING_NEW || state==AF_EXEC_ORDER_PLACED ||
      state==AF_EXEC_PARTIALLY_FILLED)
      g_cnt.entry_timeouts++;
   if(state==AF_EXEC_RECOVERING_AMBIGUOUS)
      g_cnt.kernel_ambiguous++;
   if(WgResetKernel())
      g_cnt.kernel_recycles++;
   else
      g_runtime_failed=true;
  }

//+------------------------------------------------------------------+
//| Position mirror and exits                                        |
//+------------------------------------------------------------------+
void WgSyncPosition()
  {
   ulong ticket=0;
   const int owned=WgFindOwnedPosition(ticket);
   if(owned<0)
      return;
   if(owned==0)
     {
      if(g_pos_ticket!=0)
        {
         g_pos_ticket=0;
         g_pos_direction=LSW_DIR_NONE;
         g_pos_open_price=0.0;
         g_pos_risk_distance=0.0;
         g_pos_bars_held=0;
        }
      return;
     }
   if(owned>1)
      g_runtime_failed=true;
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
   g_pos_bars_held=0;

   double money_per_lot=0.0;
   double realized_risk=0.0;
   if(g_pos_risk_distance>0.0 && position_sl>0.0 &&
      LswMoneyRiskPerLot(_Symbol,g_pos_direction,g_pos_open_price,position_sl,
                         g_pos_risk_distance,money_per_lot))
      realized_risk=money_per_lot*volume;
   WgLogPosition(g_active_sid,g_pos_ticket,volume,g_pos_open_price,
                 position_sl,position_tp,realized_risk);
  }

bool WgClosePosition(const string reason)
  {
   if(g_pos_ticket==0)
      return(true);
   const datetime bar_time=iTime(_Symbol,PERIOD_M1,0);
   if(bar_time!=g_exit_bar)
     {
      g_exit_bar=bar_time;
      g_exit_attempts=0;
     }
   if(g_exit_attempts>=WG_MAX_EXIT_ATTEMPTS_PER_BAR)
      return(false);
   g_exit_attempts++;

   g_trade.SetExpertMagicNumber(g_cfg.magic);
   g_trade.SetDeviationInPoints(g_cfg.slippage_points);
   const ulong ticket=g_pos_ticket;
   const bool sent=g_trade.PositionClose(ticket,g_cfg.slippage_points);
   const uint retcode=g_trade.ResultRetcode();
   const bool ok=(sent && (retcode==TRADE_RETCODE_DONE ||
                           retcode==TRADE_RETCODE_DONE_PARTIAL));
   WgLogExit(g_active_sid,reason,ticket,ok,retcode);
   if(!ok)
      g_cnt.exit_reject++;
   return(ok);
  }

void WgManageOpenPosition(const LswClock &clk)
  {
   if(g_pos_ticket==0)
      return;
   //--- Hard flats first: structural, not a preference.
   if(clk.friday_flatten)
     {
      if(WgClosePosition("FRIDAY_FLAT"))
         g_cnt.exit_friday_flat++;
      return;
     }
   if(clk.flatten)
     {
      if(WgClosePosition("DAILY_FLAT"))
         g_cnt.exit_daily_flat++;
      return;
     }
   if(g_cfg.max_hold_bars>0 && g_pos_bars_held>=g_cfg.max_hold_bars)
     {
      if(WgClosePosition("TIME_STOP"))
         g_cnt.exit_time_stop++;
      return;
     }
  }

//+------------------------------------------------------------------+
//| Closed-bar decision                                              |
//+------------------------------------------------------------------+
void WgDecide(const datetime bar0_time,const LswClock &clk_now)
  {
   g_signal_id++;
   g_cnt.decisions++;
   const long sid=g_signal_id;

   //--- Signal bar: shift 1, never the forming bar.
   MqlRates sig;
   ZeroMemory(sig);
   if(!WgBarAtM1(_Symbol,1,sig))
     {
      g_cnt.data_fail++;
      return;
     }
   if((long)bar0_time-(long)sig.time!=60)
     {
      g_cnt.filt_bar_gap++;
      return;
     }

   //--- The slot: the signal bar must be the Monday 01:00 bar
   //--- (server clock; MQL5 day_of_week 1=Monday).
   MqlDateTime st;
   TimeToStruct(sig.time,st);
   if(st.day_of_week!=InpSignalDowServer || st.hour!=InpSignalHourServer ||
      st.min!=InpSignalMinuteServer)
     {
      g_cnt.geom_bad_approach++;          // non-slot decision
      return;
     }

   //--- Weekend gap condition, computed on closed bars only.
   double gap_pips=0.0;
   if(!WgWeekGapPips(_Symbol,sig,gap_pips))
     {
      g_cnt.geom_no_level++;
      WgLogReject(sid,"SIGNAL","GAP_UNREADABLE",g_cfg.verbose);
      return;
     }
   if(gap_pips>=0.0)
     {
      g_cnt.geom_pen_large++;             // gap wrong direction
      return;
     }
   if(gap_pips>=-InpGapThreshPips)
     {
      g_cnt.geom_pen_small++;             // gap too shallow
      return;
     }

   g_cnt.signals_seen++;
   g_cnt.signals_long++;
   WgLogSignal(sid,sig.time,gap_pips,g_cfg.verbose);

   //--- Entry filters, one counter per reject.
   if(clk_now.weekend || clk_now.rollover || clk_now.flatten)
     {
      if(clk_now.rollover)
         g_cnt.filt_rollover++;
      else if(clk_now.flatten)
         g_cnt.filt_flatten++;
      else
         g_cnt.filt_session++;
      WgLogReject(sid,"FILTER","SESSION",g_cfg.verbose);
      return;
     }
   const int symbol_positions=WgCountSymbolPositions();
   const int owned_orders=WgCountOwnedOrders();
   if(symbol_positions<0 || owned_orders<0)
     {
      g_cnt.data_fail++;
      WgLogReject(sid,"FILTER","SCAN_FAIL",g_cfg.verbose);
      return;
     }
   if(symbol_positions!=0)
     {
      g_cnt.filt_position_open++;
      WgLogReject(sid,"FILTER","POSITION_OPEN",g_cfg.verbose);
      return;
     }
   if(CheckPointer(g_exec)==POINTER_INVALID || g_exec.State()!=AF_EXEC_IDLE ||
      owned_orders!=0)
     {
      g_cnt.filt_exec_busy++;
      WgLogReject(sid,"FILTER","EXEC_BUSY",g_cfg.verbose);
      return;
     }
   if(LswRiskBlocked(g_risk,g_cfg,g_cnt))
     {
      WgLogReject(sid,"FILTER","RISK_LOCK",g_cfg.verbose);
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
   const int digits=(int)SymbolInfoInteger(_Symbol,SYMBOL_DIGITS);
   const double pip=((digits==3 || digits==5) ? point*10.0 : point);
   if(!LswFinite(point) || point<=0.0 || !LswFinite(pip) || pip<=0.0)
     {
      g_cnt.data_fail++;
      return;
     }
   if((tick.ask-tick.bid)>InpMaxSpreadPips*pip)
     {
      g_cnt.filt_spread++;
      WgLogReject(sid,"FILTER","SPREAD",g_cfg.verbose);
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
      WgLogReject(sid,"FILTER","NEWS",g_cfg.verbose);
      return;
     }

   //--- Fixed-SL plan (no level anchor in this mechanism).
   LswPlan plan;
   if(!WgBuildPlan(_Symbol,LSW_DIR_LONG,InpSlPips,g_cfg,tick.ask,tick.bid,plan))
     {
      if(plan.reject=="SIZING" || plan.reject=="VOLUME" || plan.reject=="MARGIN")
         g_cnt.entry_reject_sizing++;
      else if(plan.reject=="STOPS_LEVEL" || plan.reject=="BAD_GEOMETRY")
         g_cnt.entry_reject_geometry++;
      else
         g_cnt.entry_reject_plan++;
      WgLogReject(sid,"PLAN",plan.reject,g_cfg.verbose);
      return;
     }
   WgLogRequest(sid,plan,gap_pips,g_cfg.risk_percent);

   const bool submitted=g_exec.SubmitMarket(ORDER_TYPE_BUY,plan.volume,plan.sl,
                                            0.0,g_cfg.slippage_points);
   WgLogOrder(sid,submitted,(int)g_exec.State(),g_exec.RequestId(),
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
   g_pending_risk_distance=plan.risk_distance;
   AfTele_SetPlannedRisk(plan.risk_distance/point,
                         AccountInfoDouble(ACCOUNT_EQUITY)*g_cfg.risk_percent/100.0);
  }

//+------------------------------------------------------------------+
//| Input validation. Fail closed at init.                           |
//+------------------------------------------------------------------+
bool WgValidateInputs()
  {
   string bad="";
   if(InpMagic==0)                                        bad="InpMagic";
   else if(InpSlippagePoints>(ulong)1000)                 bad="InpSlippagePoints";
   else if(InpServerGmtOffsetHours<-12 || InpServerGmtOffsetHours>14)
      bad="InpServerGmtOffsetHours";
   else if(InpFlattenHourServer<12 || InpFlattenHourServer>23)
      bad="InpFlattenHourServer";
   else if(InpFridayFlattenHourServer<1 || InpFridayFlattenHourServer>23)
      bad="InpFridayFlattenHourServer";
   else if(InpSignalDowServer<0 || InpSignalDowServer>6)  bad="InpSignalDowServer";
   else if(InpSignalHourServer<0 || InpSignalHourServer>23)
      bad="InpSignalHourServer";
   else if(InpSignalMinuteServer<0 || InpSignalMinuteServer>59)
      bad="InpSignalMinuteServer";
   else if(InpGapThreshPips<=0.0 || InpGapThreshPips>200.0)
      bad="InpGapThreshPips";
   else if(InpSlPips<=0.0 || InpSlPips>500.0)             bad="InpSlPips";
   else if(InpMaxHoldBars<1 || InpMaxHoldBars>5000)       bad="InpMaxHoldBars";
   else if(InpMaxSpreadPips<=0.0 || InpMaxSpreadPips>100.0)
      bad="InpMaxSpreadPips";
   else if(InpNewsBlackoutMin<0 || InpNewsBlackoutMin>240)
      bad="InpNewsBlackoutMin";
   else if(InpRiskPercent<=0.0 || InpRiskPercent>5.0)     bad="InpRiskPercent";
   else if(InpMaxTradesPerDay<0 || InpMaxTradesPerDay>500)
      bad="InpMaxTradesPerDay";
   else if(InpMaxConsecutiveLosses<0 || InpMaxConsecutiveLosses>100)
      bad="InpMaxConsecutiveLosses";
   else if(InpMaxDailyLossPct<0.0 || InpMaxDailyLossPct>100.0)
      bad="InpMaxDailyLossPct";
   else if(InpMaxAccountDdPct<0.0 || InpMaxAccountDdPct>100.0)
      bad="InpMaxAccountDdPct";
   if(StringLen(bad)==0)
      return(true);
   PrintFormat("WG002_INIT_REJECT input=%s",bad);
   return(false);
  }

void WgLoadConfig()
  {
   ZeroMemory(g_cfg);
   g_cfg.server_gmt_offset_hours=InpServerGmtOffsetHours;
   g_cfg.server_dst_us_rule=InpServerDstUsRule;
   g_cfg.session_mode=LSW_SESS_BOTH;                 // inert: WG has own slot
   g_cfg.flatten_hour_server=InpFlattenHourServer;
   g_cfg.friday_flatten_hour_server=InpFridayFlattenHourServer;
   g_cfg.max_hold_bars=InpMaxHoldBars;
   g_cfg.news_blackout_min=InpNewsBlackoutMin;
   g_cfg.risk_percent=InpRiskPercent;
   g_cfg.max_trades_per_day=InpMaxTradesPerDay;
   g_cfg.max_consecutive_losses=InpMaxConsecutiveLosses;
   g_cfg.max_daily_loss_pct=InpMaxDailyLossPct;
   g_cfg.max_account_dd_pct=InpMaxAccountDdPct;
   g_cfg.magic=InpMagic;
   g_cfg.slippage_points=InpSlippagePoints;
   g_cfg.verbose=InpVerboseLog;
  }

//+------------------------------------------------------------------+
//| Series proof: identical doctrine to the siblings - the tester    |
//| must prove synchronized M1 history exists before trading.        |
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
   //--- Wire contract: the governed post-run validator and the non-repaint
   //--- auditor whitelist this exact shape — m5_* denotes the M5 series
   //--- provenance probe, m1_* denotes the terminal's M1 history bounds.
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

//+------------------------------------------------------------------+
//| Event handlers                                                   |
//+------------------------------------------------------------------+
int OnInit()
  {
   if(!EmitD0SeriesProof())
     {
      Print("WG002_FATAL reason=D0_SERIES_PROOF");
      return(INIT_FAILED);
     }
   if(!WgValidateInputs())
      return(INIT_PARAMETERS_INCORRECT);

   WgLoadConfig();
   ZeroMemory(g_cnt);
   ZeroMemory(g_risk);
   g_runtime_failed=false;
   g_pos_ticket=0;
   g_pos_direction=LSW_DIR_NONE;
   g_pos_open_price=0.0;
   g_pos_risk_distance=0.0;
   g_pos_bars_held=0;
   g_pending_risk_distance=0.0;
   g_submit_bar_time=0;
   g_exit_bar=0;
   g_exit_attempts=0;

   g_trade.SetExpertMagicNumber(g_cfg.magic);
   g_trade.SetDeviationInPoints(g_cfg.slippage_points);
   g_trade.SetMarginMode();
   g_trade.SetTypeFillingBySymbol(_Symbol);

   if(!WgResetKernel())
     {
      Print("WG002_INIT_REJECT reason=kernel_configure");
      return(INIT_FAILED);
     }

   WgLogClockDiag(g_cfg.server_gmt_offset_hours,g_cfg.server_dst_us_rule);

   //--- Warm-up: never decide on the bar already forming at attach.
   g_last_bar_time=iTime(_Symbol,PERIOD_M1,0);
   WgSyncPosition();
   if(!AfTele_OnInit("EA_WeekGap",InpHypothesisId,InpEnableTelemetry))
      return(INIT_FAILED);
   return(INIT_SUCCEEDED);
  }

void OnDeinit(const int reason)
  {
   AfTele_OnDeinit();
   WgSummary(g_cnt,reason,g_runtime_failed);
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
   WgSyncPosition();

   LswClock clk;
   if(!LswClockRead(server_now,g_cfg,clk))
     {
      g_cnt.data_fail++;
      return;
     }

   //--- Closed-bar edge. iTime(...,0) is only a TIMESTAMP read: no price
   //--- from the forming bar ever reaches a decision.
   const datetime bar0=iTime(_Symbol,PERIOD_M1,0);
   const bool new_bar=(bar0>0 && bar0!=g_last_bar_time);
   if(new_bar)
     {
      g_last_bar_time=bar0;
      g_cnt.closed_bars++;
      if(g_pos_ticket!=0)
         g_pos_bars_held++;
     }

   //--- Exits run on every tick: time stop and the hard flats.
   WgManageOpenPosition(clk);

   if(!new_bar)
      return;
   if(g_runtime_failed)
      return;

   WgMaybeRecycleKernel(bar0);

   //--- Decision clock = the confirmation bar's close = forming bar's open.
   LswClock clk_decision;
   if(!LswClockRead(bar0,g_cfg,clk_decision))
     {
      g_cnt.data_fail++;
      return;
     }
   WgDecide(bar0,clk_decision);
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
   WgLogDeal(g_active_sid,trans.deal,(int)entry,volume,price,net);

   if(entry==DEAL_ENTRY_IN)
     {
      g_cnt.entries_filled++;
      g_pos_risk_distance=g_pending_risk_distance;
      g_pos_bars_held=0;
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
