//+------------------------------------------------------------------+
//| EA_LiquiditySweep.mq5                                            |
//| Liquidity Sweep Reversion (LSW) - M5, closed bar.                |
//|                                                                  |
//| Resting stop-loss orders cluster just beyond salient intraday    |
//| reference levels (Osler 2003, J.Finance 58(5)). A bounded        |
//| excursion beyond such a level that CLOSES BACK inside was a stop  |
//| cascade absorbed by dealers, not information. Dealers unwind the  |
//| unwanted inventory; that unwind is the payoff. Traded only inside |
//| the London / New York liquidity windows (Andersen & Bollerslev,   |
//| 1997/1998).                                                       |
//|                                                                  |
//| Frozen spec: research/CONTRACT.md. Do not change behaviour here   |
//| without a new hypothesis ID.                                      |
//+------------------------------------------------------------------+
#property strict
#property version   "1.00"
#property description "Liquidity Sweep Reversion - M5 closed-bar stop-run fade"

//--- The shared kernel is fail-closed by default; an adopting EA must opt in
//--- explicitly. This define MUST precede the include.
#define AF_EXEC_EXPERIMENTAL_MUTATION_ENABLED 1
#include "../_Shared/Execution/AF_ExecutionKernel.mqh"

#include <Trade/Trade.mqh>

#include "Include/LSW_Types.mqh"
#include "Include/LSW_Session.mqh"
#include "Include/LSW_Levels.mqh"
#include "Include/LSW_Signal.mqh"
#include "Include/LSW_Risk.mqh"
#include "Include/LSW_Telemetry.mqh"
#include "../_Shared/Telemetry/AF_LifecycleTelemetry.mqh"

#define LSW_STRATEGY_ID              "LSW"
#define LSW_MAX_EXIT_ATTEMPTS_PER_BAR 5

//+------------------------------------------------------------------+
//| Inputs - 29 total. The host EA has 54 and is unmaintainable.      |
//+------------------------------------------------------------------+
input group "=== Identity and execution ==="
input ulong  InpMagic                   = 26451822;    // Magic number
input ulong  InpSlippagePoints          = 20;          // Max deviation (points)

input group "=== Clock and sessions ==="
input int    InpServerGmtOffsetHours    = 2;           // Server offset from GMT, winter
input bool   InpServerDstUsRule         = true;        // Server adds +1h on US DST
input LSW_SESSION_MODE InpSessionMode   = LSW_SESS_BOTH; // Tradable liquidity windows
input int    InpFlattenHourServer       = 22;          // Hard flat at this server hour
input int    InpFridayFlattenHourServer = 20;          // Friday hard flat, server hour

input group "=== Reference levels ==="
input bool   InpUsePrevDayLevels        = true;        // Prior completed D1 high/low
input bool   InpUseAsiaRange            = true;        // Asia 00:00-07:00 GMT range
input bool   InpUseOpeningRange         = true;        // Session opening range
input int    InpOrBars                  = 6;           // Opening-range length, M5 bars
input double InpRoundStep               = 5.0;         // Round step, 0=off. XAU 5.0 EUR 0.0050

input group "=== Sweep geometry ==="
input double InpSweepMinAtr             = 0.15;        // Min penetration beyond level, xATR
input double InpSweepMaxAtr             = 1.00;        // Max penetration, deeper = breakout
input bool   InpRequireNextBarHold      = false;       // Next bar must not re-penetrate

input group "=== Exit ==="
input double InpSlBufferAtr             = 0.45;        // SL beyond sweep extreme, xATR
input double InpMinSlSpreadMult         = 4.0;         // SL floor as a multiple of spread
input double InpTpR                     = 1.30;        // Take profit in R
input int    InpMaxHoldBars             = 24;          // Time stop, M5 bars
input double InpBeAtR                   = 0.70;        // Break-even trigger in R, 0=off

input group "=== Filters and risk ==="
input double InpMaxSpreadAtr            = 0.20;        // Max spread as xATR
input double InpMinAtrPoints            = 60.0;        // Volatility floor, points
input int    InpNewsBlackoutMin         = 20;          // News blackout +/- minutes, 0=off
input double InpRiskPercent             = 0.35;        // Risk per trade, % of equity
input int    InpMaxTradesPerDay         = 6;           // Max entries per server day
input int    InpMaxConsecutiveLosses    = 4;           // Streak lock, 0=off
input double InpMaxDailyLossPct         = 2.0;         // Daily loss lock, %
input double InpMaxAccountDdPct         = 10.0;        // Account drawdown lock, %

input group "=== Telemetry ==="
input bool   InpVerboseLog              = true;        // Per-decision signal/reject lines
input bool   InpEnableTelemetry         = true;        // AlphaFactory lifecycle telemetry
input string InpHypothesisId            = "HYP-LSWEEP-EUR-M5-001";

//+------------------------------------------------------------------+
//| Globals                                                          |
//+------------------------------------------------------------------+
LswConfig           g_cfg;
LswCounters         g_cnt;
LswRiskState        g_risk;
LswLevelCache       g_cache;
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
int                 g_pos_bars_held=0;
bool                g_be_done=false;

//--- Carried from the submitted plan to the fill.
LSW_FAMILY          g_pending_family=LSW_FAM_NONE;
double              g_pending_risk_distance=0.0;

//--- Exit-attempt throttle so a permanently failing close cannot spam.
datetime            g_exit_bar=0;
int                 g_exit_attempts=0;

//+------------------------------------------------------------------+
//| Ownership scans. All fail-closed: a scan that cannot be trusted   |
//| returns -1 and callers must refuse to trade.                      |
//+------------------------------------------------------------------+
int LswFindOwnedPosition(ulong &ticket)
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

int LswCountSymbolPositions()
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

int LswCountOwnedOrders()
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
//|                                                                  |
//| CAFExecutionKernel tracks exactly ONE request per instance: after |
//| a cycle ends it can never return to AF_EXEC_IDLE (Reconcile keeps  |
//| a non-zero requested volume ambiguous forever). A fresh instance   |
//| is therefore the documented way to arm the next trade. Recycling   |
//| happens only on a new bar and only while genuinely flat, so it     |
//| cannot race an in-flight async request.                            |
//+------------------------------------------------------------------+
bool LswResetKernel()
  {
   if(CheckPointer(g_exec)!=POINTER_INVALID)
     {
      delete g_exec;
      g_exec=NULL;
     }
   g_exec=new CAFExecutionKernel();
   if(CheckPointer(g_exec)==POINTER_INVALID)
      return(false);
   if(!g_exec.Configure(_Symbol,g_cfg.magic,LSW_STRATEGY_ID))
      return(false);
   g_exec.Reconcile();
   return(true);
  }

void LswMaybeRecycleKernel(const datetime bar_time)
  {
   if(CheckPointer(g_exec)==POINTER_INVALID)
      return;
   const AF_EXEC_STATE state=g_exec.State();
   if(state==AF_EXEC_IDLE)
      return;
   if(g_submit_bar_time!=0 && bar_time==g_submit_bar_time)
      return;                                   // never recycle on the submit bar
   ulong owned_ticket=0;
   if(LswFindOwnedPosition(owned_ticket)!=0)
      return;
   if(LswCountOwnedOrders()!=0)
      return;

   if(state==AF_EXEC_PENDING_NEW || state==AF_EXEC_ORDER_PLACED ||
      state==AF_EXEC_PARTIALLY_FILLED)
      g_cnt.entry_timeouts++;                   // sent, then vanished without a fill
   if(state==AF_EXEC_RECOVERING_AMBIGUOUS)
      g_cnt.kernel_ambiguous++;
   if(LswResetKernel())
      g_cnt.kernel_recycles++;
   else
      g_runtime_failed=true;
  }

//+------------------------------------------------------------------+
//| Position mirror and exits                                        |
//+------------------------------------------------------------------+
void LswSyncPosition()
  {
   ulong ticket=0;
   const int owned=LswFindOwnedPosition(ticket);
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
         g_pos_bars_held=0;
         g_be_done=false;
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
   // Realised risk distance beats the planned one: it is what the broker holds.
   g_pos_risk_distance=(position_sl>0.0 ? MathAbs(g_pos_open_price-position_sl)
                        : g_pending_risk_distance);
   g_pos_bars_held=0;
   g_be_done=false;

   double money_per_lot=0.0;
   double realized_risk=0.0;
   if(g_pos_risk_distance>0.0 && position_sl>0.0 &&
      LswMoneyRiskPerLot(_Symbol,g_pos_direction,g_pos_open_price,position_sl,
                         g_pos_risk_distance,money_per_lot))
      realized_risk=money_per_lot*volume;
   LswLogPosition(g_active_sid,g_pos_ticket,volume,g_pos_open_price,
                  position_sl,position_tp,realized_risk);
  }

bool LswClosePosition(const string reason)
  {
   if(g_pos_ticket==0)
      return(true);
   const datetime bar_time=iTime(_Symbol,PERIOD_M5,0);
   if(bar_time!=g_exit_bar)
     {
      g_exit_bar=bar_time;
      g_exit_attempts=0;
     }
   if(g_exit_attempts>=LSW_MAX_EXIT_ATTEMPTS_PER_BAR)
      return(false);
   g_exit_attempts++;

   g_trade.SetExpertMagicNumber(g_cfg.magic);
   g_trade.SetDeviationInPoints(g_cfg.slippage_points);
   const ulong ticket=g_pos_ticket;
   const bool sent=g_trade.PositionClose(ticket,g_cfg.slippage_points);
   const uint retcode=g_trade.ResultRetcode();
   const bool ok=(sent && (retcode==TRADE_RETCODE_DONE ||
                           retcode==TRADE_RETCODE_DONE_PARTIAL));
   LswLogExit(g_active_sid,reason,ticket,ok,retcode);
   if(!ok)
      g_cnt.exit_reject++;
   return(ok);
  }

void LswTryBreakEven()
  {
   if(g_cfg.be_at_r<=0.0 || g_be_done || g_pos_ticket==0 ||
      g_pos_risk_distance<=0.0 || g_pos_direction==LSW_DIR_NONE)
      return;
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick) || tick.bid<=0.0 || tick.ask<=0.0)
      return;
   const double favourable=(g_pos_direction>0 ? tick.bid-g_pos_open_price
                            : g_pos_open_price-tick.ask);
   if(favourable<g_cfg.be_at_r*g_pos_risk_distance)
      return;
   if(!PositionSelectByTicket(g_pos_ticket))
      return;
   const double current_tp=PositionGetDouble(POSITION_TP);
   const double current_sl=PositionGetDouble(POSITION_SL);
   const double point=SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   const long stops_level=SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL);
   const long freeze_level=SymbolInfoInteger(_Symbol,SYMBOL_TRADE_FREEZE_LEVEL);
   long broker_level=(stops_level>freeze_level ? stops_level : freeze_level);
   if(broker_level<0)
      broker_level=0;
   const double min_dist=(double)broker_level*point;
   const double new_sl=g_pos_open_price;

   // Refuse a modify the broker would reject, and never loosen an existing stop.
   if(g_pos_direction>0)
     {
      if(new_sl>tick.bid-min_dist || (current_sl>0.0 && new_sl<=current_sl))
         return;
     }
   else
     {
      if(new_sl<tick.ask+min_dist || (current_sl>0.0 && new_sl>=current_sl))
         return;
     }

   const bool sent=g_trade.PositionModify(g_pos_ticket,new_sl,current_tp);
   const uint retcode=g_trade.ResultRetcode();
   const bool ok=(sent && (retcode==TRADE_RETCODE_DONE ||
                           retcode==TRADE_RETCODE_PLACED));
   LswLogBreakEven(g_active_sid,g_pos_ticket,new_sl,ok,retcode);
   if(ok)
     {
      g_be_done=true;
      g_cnt.be_moves++;
     }
   else
      g_cnt.be_rejects++;
  }

void LswManageOpenPosition(const LswClock &clk)
  {
   if(g_pos_ticket==0)
      return;
   //--- Hard flats first. These exist so the scalp holding contract
   //--- (overnight_trades == 0, weekend_crossing_trades == 0) is structural.
   if(clk.friday_flatten)
     {
      if(LswClosePosition("FRIDAY_FLAT"))
         g_cnt.exit_friday_flat++;
      return;
     }
   if(clk.flatten)
     {
      if(LswClosePosition("DAILY_FLAT"))
         g_cnt.exit_daily_flat++;
      return;
     }
   if(g_cfg.max_hold_bars>0 && g_pos_bars_held>=g_cfg.max_hold_bars)
     {
      if(LswClosePosition("TIME_STOP"))
         g_cnt.exit_time_stop++;
      return;
     }
   LswTryBreakEven();
  }

//+------------------------------------------------------------------+
//| Closed-bar decision                                              |
//+------------------------------------------------------------------+
void LswDecide(const datetime bar0_time,const LswClock &clk_now)
  {
   g_signal_id++;
   g_cnt.decisions++;
   const long sid=g_signal_id;

   //--- Bar selection. shift 0 is the forming bar and is NEVER read for prices.
   const int sweep_shift=(g_cfg.require_next_bar_hold ? 2 : 1);
   const int prev_shift=sweep_shift+1;

   MqlRates sweep_bar,prev_bar,hold_bar;
   ZeroMemory(sweep_bar);
   ZeroMemory(prev_bar);
   ZeroMemory(hold_bar);
   if(!LswBarAt(_Symbol,sweep_shift,sweep_bar) ||
      !LswBarAt(_Symbol,prev_shift,prev_bar))
     {
      g_cnt.data_fail++;
      return;
     }
   if(g_cfg.require_next_bar_hold && !LswBarAt(_Symbol,1,hold_bar))
     {
      g_cnt.data_fail++;
      return;
     }

   //--- Contiguity. Across a weekend or holiday seam the "previous" bar is days
   //--- old and the setup is meaningless, so the decision is skipped.
   if((long)bar0_time-(long)sweep_bar.time!=(long)sweep_shift*LSW_SEC_PER_M5 ||
      (long)sweep_bar.time-(long)prev_bar.time!=LSW_SEC_PER_M5)
     {
      g_cnt.filt_bar_gap++;
      return;
     }

   double atr=0.0;
   if(!LswAtrAt(g_atr_handle,sweep_shift,atr))
     {
      g_cnt.data_fail++;
      return;
     }

   //--- Level availability is judged at the SWEEP bar, not at "now": a level
   //--- must have existed before the bar that swept it.
   LswClock clk_signal;
   if(!LswClockRead(sweep_bar.time,g_cfg,clk_signal))
     {
      g_cnt.data_fail++;
      return;
     }

   LswLevelSet levels;
   if(!LswBuildLevels(_Symbol,sweep_bar.time,sweep_bar.high,sweep_bar.low,
                      g_cfg,clk_signal,g_cache,levels))
     {
      g_cnt.data_fail++;
      return;
     }

   LswSweep sweep;
   if(!LswDetectSweep(levels,sweep_bar,prev_bar,hold_bar,atr,g_cfg,sweep,g_cnt))
     {
      LswLogReject(sid,"GEOMETRY",sweep.reject,g_cfg.verbose);
      return;
     }
   LswLogSignal(sid,sweep,clk_now,g_cfg.verbose);

   //--- Filters. Each path increments exactly one counter and returns.
   if(!clk_now.entry_window)
     {
      if(clk_now.rollover)
         g_cnt.filt_rollover++;
      else if(clk_now.flatten)
         g_cnt.filt_flatten++;
      else
         g_cnt.filt_session++;
      LswLogReject(sid,"FILTER","SESSION",g_cfg.verbose);
      return;
     }
   const int symbol_positions=LswCountSymbolPositions();
   const int owned_orders=LswCountOwnedOrders();
   if(symbol_positions<0 || owned_orders<0)
     {
      g_cnt.data_fail++;                        // a scan we cannot trust: fail closed
      LswLogReject(sid,"FILTER","SCAN_FAIL",g_cfg.verbose);
      return;
     }
   if(symbol_positions!=0)
     {
      g_cnt.filt_position_open++;
      LswLogReject(sid,"FILTER","POSITION_OPEN",g_cfg.verbose);
      return;
     }
   if(CheckPointer(g_exec)==POINTER_INVALID || g_exec.State()!=AF_EXEC_IDLE ||
      owned_orders!=0)
     {
      g_cnt.filt_exec_busy++;
      LswLogReject(sid,"FILTER","EXEC_BUSY",g_cfg.verbose);
      return;
     }
   if(LswRiskBlocked(g_risk,g_cfg,g_cnt))
     {
      LswLogReject(sid,"FILTER","RISK_LOCK",g_cfg.verbose);
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
      LswLogReject(sid,"FILTER","ATR_FLOOR",g_cfg.verbose);
      return;
     }
   if(tick.ask-tick.bid>g_cfg.max_spread_atr*atr)
     {
      g_cnt.filt_spread++;
      LswLogReject(sid,"FILTER","SPREAD",g_cfg.verbose);
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
      LswLogReject(sid,"FILTER","NEWS",g_cfg.verbose);
      return;
     }

   //--- Plan and submit.
   LswPlan plan;
   if(!LswBuildPlan(_Symbol,sweep,g_cfg,tick.ask,tick.bid,plan))
     {
      if(plan.reject=="SIZING" || plan.reject=="VOLUME" || plan.reject=="MARGIN")
         g_cnt.entry_reject_sizing++;
      else if(plan.reject=="STOPS_LEVEL" || plan.reject=="BAD_GEOMETRY")
         g_cnt.entry_reject_geometry++;
      else
         g_cnt.entry_reject_plan++;
      LswLogReject(sid,"PLAN",plan.reject,g_cfg.verbose);
      return;
     }
   LswLogRequest(sid,plan,sweep,g_cfg.risk_percent);

   const ENUM_ORDER_TYPE order_type=(plan.direction>0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL);
   const bool submitted=g_exec.SubmitMarket(order_type,plan.volume,plan.sl,plan.tp,
                                            g_cfg.slippage_points);
   LswLogOrder(sid,submitted,(int)g_exec.State(),g_exec.RequestId(),
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
   g_pending_family=sweep.family;
   g_pending_risk_distance=plan.risk_distance;
   AfTele_SetPlannedRisk(plan.risk_distance/point,
                         AccountInfoDouble(ACCOUNT_EQUITY)*g_cfg.risk_percent/100.0);
  }

//+------------------------------------------------------------------+
//| Input validation. Fail closed at init rather than at runtime.    |
//+------------------------------------------------------------------+
bool LswValidateInputs()
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
   else if(InpOrBars<1 || InpOrBars>60)                   bad="InpOrBars";
   else if(InpRoundStep<0.0)                              bad="InpRoundStep";
   else if(InpSweepMinAtr<=0.0 || InpSweepMinAtr>5.0)     bad="InpSweepMinAtr";
   else if(InpSweepMaxAtr<=InpSweepMinAtr || InpSweepMaxAtr>10.0)
      bad="InpSweepMaxAtr";
   else if(InpSlBufferAtr<0.0 || InpSlBufferAtr>5.0)      bad="InpSlBufferAtr";
   else if(InpMinSlSpreadMult<0.0 || InpMinSlSpreadMult>50.0)
      bad="InpMinSlSpreadMult";
   else if(InpTpR<=0.0 || InpTpR>20.0)                    bad="InpTpR";
   else if(InpMaxHoldBars<1 || InpMaxHoldBars>5000)       bad="InpMaxHoldBars";
   else if(InpBeAtR<0.0 || InpBeAtR>20.0)                 bad="InpBeAtR";
   else if(InpMaxSpreadAtr<=0.0 || InpMaxSpreadAtr>10.0)  bad="InpMaxSpreadAtr";
   else if(InpMinAtrPoints<0.0)                           bad="InpMinAtrPoints";
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
   else if(!InpUsePrevDayLevels && !InpUseAsiaRange && !InpUseOpeningRange &&
           InpRoundStep<=0.0)
      bad="no level family enabled";
   if(StringLen(bad)==0)
      return(true);
   PrintFormat("LSW001_INIT_REJECT input=%s",bad);
   return(false);
  }

void LswLoadConfig()
  {
   ZeroMemory(g_cfg);
   g_cfg.server_gmt_offset_hours=InpServerGmtOffsetHours;
   g_cfg.server_dst_us_rule=InpServerDstUsRule;
   g_cfg.session_mode=InpSessionMode;
   g_cfg.flatten_hour_server=InpFlattenHourServer;
   g_cfg.friday_flatten_hour_server=InpFridayFlattenHourServer;
   g_cfg.use_prev_day=InpUsePrevDayLevels;
   g_cfg.use_asia=InpUseAsiaRange;
   g_cfg.use_open_range=InpUseOpeningRange;
   g_cfg.round_step=InpRoundStep;
   g_cfg.or_bars=InpOrBars;
   g_cfg.sweep_min_atr=InpSweepMinAtr;
   g_cfg.sweep_max_atr=InpSweepMaxAtr;
   g_cfg.require_next_bar_hold=InpRequireNextBarHold;
   g_cfg.sl_buffer_atr=InpSlBufferAtr;
   g_cfg.min_sl_spread_mult=InpMinSlSpreadMult;
   g_cfg.tp_r=InpTpR;
   g_cfg.max_hold_bars=InpMaxHoldBars;
   g_cfg.be_at_r=InpBeAtR;
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
      Print("LSW_FATAL reason=D0_SERIES_PROOF");
      return(INIT_FAILED);
     }
   if(!LswValidateInputs())
      return(INIT_PARAMETERS_INCORRECT);

   LswLoadConfig();
   LswCountersReset(g_cnt);
   ZeroMemory(g_risk);
   LswLevelCacheReset(g_cache);
   g_runtime_failed=false;
   g_pos_ticket=0;
   g_pos_direction=LSW_DIR_NONE;
   g_pos_open_price=0.0;
   g_pos_risk_distance=0.0;
   g_pos_bars_held=0;
   g_be_done=false;
   g_pending_family=LSW_FAM_NONE;
   g_pending_risk_distance=0.0;
   g_submit_bar_time=0;
   g_exit_bar=0;
   g_exit_attempts=0;

   g_atr_handle=iATR(_Symbol,PERIOD_M5,LSW_ATR_PERIOD);
   if(g_atr_handle==INVALID_HANDLE)
     {
      PrintFormat("LSW001_INIT_REJECT reason=atr_handle error=%d",GetLastError());
      { /*hg*/ if(g_atr_handle!=INVALID_HANDLE)IndicatorRelease(g_atr_handle); /*hg*/return(INIT_FAILED); }
     }

   g_trade.SetExpertMagicNumber(g_cfg.magic);
   g_trade.SetDeviationInPoints(g_cfg.slippage_points);
   g_trade.SetMarginMode();
   g_trade.SetTypeFillingBySymbol(_Symbol);

   if(!LswResetKernel())
     {
      Print("LSW001_INIT_REJECT reason=kernel_configure");
      { /*hg*/ if(g_atr_handle!=INVALID_HANDLE)IndicatorRelease(g_atr_handle); /*hg*/return(INIT_FAILED); }
     }

   LswLogClockDiag(g_cfg.server_gmt_offset_hours,g_cfg.server_dst_us_rule);

   //--- Warm-up: never decide on the bar that was already forming at attach.
   g_last_bar_time=iTime(_Symbol,PERIOD_M5,0);
   LswSyncPosition();
   if(!AfTele_OnInit("EA_LiquiditySweep",InpHypothesisId,InpEnableTelemetry))
      { /*hg*/ if(g_atr_handle!=INVALID_HANDLE)IndicatorRelease(g_atr_handle); /*hg*/return(INIT_FAILED); }
   return(INIT_SUCCEEDED);
  }

void OnDeinit(const int reason)
  {
   AfTele_OnDeinit();
   LswSummary(g_cnt,reason,g_runtime_failed);
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
   LswSyncPosition();

   LswClock clk;
   if(!LswClockRead(server_now,g_cfg,clk))
     {
      g_cnt.data_fail++;
      return;
     }

   //--- Closed-bar edge. iTime(...,0) is only a TIMESTAMP read: no price from
   //--- the forming bar ever reaches a decision. The bar counter is advanced
   //--- BEFORE exits run so the time stop fires on the correct bar.
   const datetime bar0=iTime(_Symbol,PERIOD_M5,0);
   const bool new_bar=(bar0>0 && bar0!=g_last_bar_time);
   if(new_bar)
     {
      g_last_bar_time=bar0;
      g_cnt.closed_bars++;
      if(g_pos_ticket!=0)
         g_pos_bars_held++;
     }

   //--- Exits run on every tick: break-even, time stop and the hard flats.
   LswManageOpenPosition(clk);

   if(!new_bar)
      return;
   //--- A latched runtime failure stops NEW risk but never stops the exits
   //--- above: getting flat must always remain possible.
   if(g_runtime_failed)
      return;

   LswMaybeRecycleKernel(bar0);

   //--- The clock used for the entry filters is the confirmation bar's CLOSE,
   //--- which is exactly the forming bar's open time.
   LswClock clk_decision;
   if(!LswClockRead(bar0,g_cfg,clk_decision))
     {
      g_cnt.data_fail++;
      return;
     }
   LswDecide(bar0,clk_decision);
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
   LswLogDeal(g_active_sid,trans.deal,(int)entry,volume,price,net);

   if(entry==DEAL_ENTRY_IN)
     {
      g_cnt.entries_filled++;
      const int family=(int)g_pending_family;
      if(family>0 && family<LSW_FAMILY_COUNT)
         g_cnt.trades_by_family[family]++;
      g_pos_risk_distance=g_pending_risk_distance;
      g_pos_bars_held=0;
      g_be_done=false;
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
