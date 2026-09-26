//+------------------------------------------------------------------+
//| EA_RollReversion.mq5                                             |
//| RollReversion (RG) - daily-roll reopen gap reversion.            |
//| Frozen spec: research/HYP-RGR-CHF-M1-001_FROZEN_PREREG.md.       |
//| Do not change behaviour without a new hypothesis ID.             |
//|                                                                  |
//| Mechanism: the server-00:00 day boundary is the 5pm-ET FX roll.  |
//| The day reopens away from fair value; a gap <= -gap_long_pips    |
//| (price reopening too LOW) is faded LONG inside the entry         |
//| window [entry_min_min, entry_max_min] server minutes-of-day.     |
//| Mirror leg: gap >= +gap_short_pips faded SHORT (USDCHF only,     |
//| per the deep-history evidence).                                  |
//|                                                                  |
//| Timing model: ALL gates are SERVER wall-clock minutes-of-day.    |
//| No GMT conversion in the signal path, and the shared session     |
//| rollover/flatten filters are bypassed for the ENTRY gate - the   |
//| mechanism IS the rollover window. clk.flatten / clk.friday_flat  |
//| still own hard exits of any open position.                       |
//|                                                                  |
//| Gap definition (server time):                                    |
//|   prev_close = close of the last M1 bar of the previous day      |
//|   open0      = open  of the first M1 bar of the new day (00:00)  |
//|   gap_pips   = (open0 - prev_close) / pip_size                   |
//| Entry: market order at the first new M1 bar inside the window,   |
//| one attempt per leg per day. SL = sl_pips fixed, TP = tp_r x     |
//| risk (non-binding). Exit: SL, time-stop at time_stop_min of      |
//| position age, or the shared hard flats.                          |
//+------------------------------------------------------------------+
#property strict
#property version   "1.00"
#property description "RollReversion - daily-roll reopen gap reversion"

#define AF_EXEC_EXPERIMENTAL_MUTATION_ENABLED 1
#include "../_Shared/Execution/AF_ExecutionKernel.mqh"

#include <Trade/Trade.mqh>

#include "../EA_LiquiditySweep/Include/LSW_Types.mqh"
#include "../EA_LiquiditySweep/Include/LSW_Session.mqh"
#include "../EA_LiquiditySweep/Include/LSW_Signal.mqh"
#include "../EA_LiquiditySweep/Include/LSW_Risk.mqh"
#include "Include/RG_Types.mqh"
#include "Include/RG_Telemetry.mqh"
#include "../_Shared/Telemetry/AF_LifecycleTelemetry.mqh"

#define RG_STRATEGY_ID              "RG"
#define RG_MAX_EXIT_ATTEMPTS_PER_BAR 5
#define RG_SEC_PER_M1               60

//+------------------------------------------------------------------+
//| Inputs                                                           |
//+------------------------------------------------------------------+
input group "=== Identity and execution ==="
input ulong  InpMagic                   = 26451901;    // Magic number
input ulong  InpSlippagePoints          = 20;          // Max deviation (points)

input group "=== Clock ==="
input int    InpServerGmtOffsetHours    = 2;           // Server offset from GMT, winter
input bool   InpServerDstUsRule         = true;        // Server adds +1h on US DST
input int    InpFlattenHourServer       = 22;          // Hard flat at this server hour
input int    InpFridayFlattenHourServer = 20;          // Friday hard flat, server hour

input group "=== RollReversion mechanism (frozen) ==="
input bool   InpUseLong                 = true;        // LONG leg: fade gap-down
input bool   InpUseShort                = true;        // SHORT leg: fade gap-up
input double InpGapLongPips             = 1.5;         // Arm LONG when gap <= -x pips
input double InpGapShortPips            = 2.0;         // Arm SHORT when gap >= +x pips
input double InpGapMaxPips              = 50.0;        // Skip |gap| beyond this (bad data)
input int    InpEntryMinMin             = 4;           // First entry minute of server day
input int    InpEntryMaxMin             = 8;           // Last entry minute of server day
input double InpSlPips                  = 15.0;        // Fixed stop loss, pips
input double InpTpR                     = 10.0;        // TP in R of risk (non-binding)
input int    InpTimeStopMin             = 120;         // Exit after N minutes of age

input group "=== Filters and risk ==="
input double InpMaxSpreadAtr            = 0.0;         // Max spread as xATR (0=off)
input double InpMinAtrPoints            = 0.0;         // Volatility floor, points (0=off)
input int    InpNewsBlackoutMin         = 20;          // News blackout +/- minutes, 0=off
input double InpRiskPercent             = 0.35;        // Risk per trade, % of equity
input int    InpMaxTradesPerDay         = 2;           // Max entries per server day
input int    InpMaxConsecutiveLosses    = 4;           // Streak lock, 0=off
input double InpMaxDailyLossPct         = 2.0;         // Daily loss lock, %
input double InpMaxAccountDdPct         = 0.0;         // Account DD lock, % (0=off)

input group "=== Telemetry ==="
input bool   InpVerboseLog              = true;        // Per-decision signal/reject lines
input bool   InpEnableTelemetry         = true;        // AlphaFactory lifecycle telemetry
input string InpHypothesisId            = "HYP-RGR-CHF-M1-001";

//+------------------------------------------------------------------+
//| Globals                                                          |
//+------------------------------------------------------------------+
LswConfig           g_cfg;
RgParams            g_p;
LswCounters         g_cnt;
LswRiskState        g_risk;
RgDayState          g_day;
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
int                 g_pos_leg=RG_LEG_NONE;
datetime            g_pos_open_time=0;

//--- Per-leg attribution (RG_LEG_* indexed).
long                g_leg_signals[RG_LEG_COUNT];
long                g_leg_trades[RG_LEG_COUNT];

//--- Carried from the submitted plan to the fill.
int                 g_pending_leg=RG_LEG_NONE;
double              g_pending_risk_distance=0.0;

//--- Exit-attempt throttle so a permanently failing close cannot spam.
datetime            g_exit_bar=0;
int                 g_exit_attempts=0;

//+------------------------------------------------------------------+
//| Ownership scans. All fail-closed.                                |
//+------------------------------------------------------------------+
int RgFindOwnedPosition(ulong &ticket)
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

int RgCountSymbolPositions()
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

int RgCountOwnedOrders()
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
bool RgResetKernel()
  {
   if(CheckPointer(g_exec)!=POINTER_INVALID)
     {
      delete g_exec;
      g_exec=NULL;
     }
   g_exec=new CAFExecutionKernel();
   if(CheckPointer(g_exec)==POINTER_INVALID)
      return(false);
   if(!g_exec.Configure(_Symbol,g_cfg.magic,RG_STRATEGY_ID))
      return(false);
   g_exec.Reconcile();
   return(true);
  }

void RgMaybeRecycleKernel(const datetime bar_time)
  {
   if(CheckPointer(g_exec)==POINTER_INVALID)
      return;
   const AF_EXEC_STATE state=g_exec.State();
   if(state==AF_EXEC_IDLE)
      return;
   if(g_submit_bar_time!=0 && bar_time==g_submit_bar_time)
      return;                                   // never recycle on the submit bar
   ulong owned_ticket=0;
   if(RgFindOwnedPosition(owned_ticket)!=0)
      return;
   if(RgCountOwnedOrders()!=0)
      return;

   if(state==AF_EXEC_PENDING_NEW || state==AF_EXEC_ORDER_PLACED ||
      state==AF_EXEC_PARTIALLY_FILLED)
      g_cnt.entry_timeouts++;
   if(state==AF_EXEC_RECOVERING_AMBIGUOUS)
      g_cnt.kernel_ambiguous++;
   if(RgResetKernel())
      g_cnt.kernel_recycles++;
   else
      g_runtime_failed=true;
  }

//+------------------------------------------------------------------+
//| Position mirror and exits                                        |
//+------------------------------------------------------------------+
void RgSyncPosition()
  {
   ulong ticket=0;
   const int owned=RgFindOwnedPosition(ticket);
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
         g_pos_leg=RG_LEG_NONE;
         g_pos_open_time=0;
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
   g_pos_open_time=(datetime)PositionGetInteger(POSITION_TIME);

   double money_per_lot=0.0;
   double realized_risk=0.0;
   if(g_pos_risk_distance>0.0 && position_sl>0.0 &&
      LswMoneyRiskPerLot(_Symbol,g_pos_direction,g_pos_open_price,position_sl,
                         g_pos_risk_distance,money_per_lot))
      realized_risk=money_per_lot*volume;
   RgLogPosition(g_active_sid,g_pos_ticket,volume,g_pos_open_price,
                 position_sl,position_tp,realized_risk);
  }

bool RgClosePosition(const string reason)
  {
   if(g_pos_ticket==0)
      return(true);
   const datetime bar_time=iTime(_Symbol,PERIOD_M1,0);
   if(bar_time!=g_exit_bar)
     {
      g_exit_bar=bar_time;
      g_exit_attempts=0;
     }
   if(g_exit_attempts>=RG_MAX_EXIT_ATTEMPTS_PER_BAR)
      return(false);
   g_exit_attempts++;

   g_trade.SetExpertMagicNumber(g_cfg.magic);
   g_trade.SetDeviationInPoints(g_cfg.slippage_points);
   const ulong ticket=g_pos_ticket;
   const bool sent=g_trade.PositionClose(ticket,g_cfg.slippage_points);
   const uint retcode=g_trade.ResultRetcode();
   const bool ok=(sent && (retcode==TRADE_RETCODE_DONE ||
                           retcode==TRADE_RETCODE_DONE_PARTIAL));
   RgLogExit(g_active_sid,reason,ticket,ok,retcode);
   if(!ok)
      g_cnt.exit_reject++;
   return(ok);
  }

double RgPipSize()
  {
   const int digits=(int)SymbolInfoInteger(_Symbol,SYMBOL_DIGITS);
   const double point=SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   return((digits==3 || digits==5) ? point*10.0 : point);
  }

void RgManageOpenPosition(const LswClock &clk_now)
  {
   if(g_pos_ticket==0)
      return;
   //--- Hard flats first: structural, not a preference.
   if(clk_now.friday_flatten)
     {
      if(RgClosePosition("FRIDAY_FLAT"))
         g_cnt.exit_friday_flat++;
      return;
     }
   if(clk_now.flatten)
     {
      if(RgClosePosition("DAILY_FLAT"))
         g_cnt.exit_daily_flat++;
      return;
     }
   //--- Frozen exit: position-age time-stop. No BE, no trail - the
   //--- mechanism is a fixed-horizon reversion; the probe measured the
   //--- raw horizon return.
   const int age_sec=(int)(TimeCurrent()-g_pos_open_time);
   if(age_sec>=g_p.time_stop_min*60)
     {
      if(RgClosePosition("TIME_STOP"))
         g_cnt.exit_time_stop++;
      return;
     }
  }

//+------------------------------------------------------------------+
//| Signal -> filters -> plan -> submit                              |
//+------------------------------------------------------------------+
void RgTryEnter(RgSignal &sig,const datetime bar0_time,const double atr)
  {
   const long sid=++g_signal_id;
   g_cnt.signals_seen++;
   if(sig.direction>0)
      g_cnt.signals_long++;
   else
      g_cnt.signals_short++;
   if(sig.leg>RG_LEG_NONE && sig.leg<RG_LEG_COUNT)
      g_leg_signals[sig.leg]++;
   RgLogSignal(sid,sig,g_cfg.verbose);

   //--- Entry filters, one counter per reject. The session/rollover
   //--- gate is intentionally ABSENT: the entry window lives inside
   //--- the rollover hour by design. Weekend and scan integrity stay.
   const int symbol_positions=RgCountSymbolPositions();
   const int owned_orders=RgCountOwnedOrders();
   if(symbol_positions<0 || owned_orders<0)
     {
      g_cnt.data_fail++;
      RgLogReject(sid,"FILTER","SCAN_FAIL",g_cfg.verbose);
      return;
     }
   if(symbol_positions!=0)
     {
      g_cnt.filt_position_open++;
      RgLogReject(sid,"FILTER","POSITION_OPEN",g_cfg.verbose);
      return;
     }
   if(CheckPointer(g_exec)==POINTER_INVALID || g_exec.State()!=AF_EXEC_IDLE ||
      owned_orders!=0)
     {
      g_cnt.filt_exec_busy++;
      RgLogReject(sid,"FILTER","EXEC_BUSY",g_cfg.verbose);
      return;
     }
   if(LswRiskBlocked(g_risk,g_cfg,g_cnt))
     {
      RgLogReject(sid,"FILTER","RISK_LOCK",g_cfg.verbose);
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
      RgLogReject(sid,"FILTER","ATR_FLOOR",g_cfg.verbose);
      return;
     }
   if(g_cfg.max_spread_atr>0.0 && tick.ask-tick.bid>g_cfg.max_spread_atr*atr)
     {
      g_cnt.filt_spread++;
      RgLogReject(sid,"FILTER","SPREAD",g_cfg.verbose);
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
      RgLogReject(sid,"FILTER","NEWS",g_cfg.verbose);
      return;
     }

   //--- Synthetic sweep adapter: fixed SL = sl_pips below/above entry,
   //--- TP = tp_r x risk (never binds; the time-stop is the exit).
   LswSweep sweep;
   ZeroMemory(sweep);
   sweep.valid=true;
   sweep.direction=sig.direction;
   sweep.atr=atr;
   const double entry_ref=(sig.direction>0 ? tick.ask : tick.bid);
   sweep.extreme=entry_ref-sig.direction*g_p.sl_pips*RgPipSize();
   LswPlan plan;
   if(!LswBuildPlan(_Symbol,sweep,g_cfg,tick.ask,tick.bid,plan))
     {
      if(plan.reject=="SIZING" || plan.reject=="VOLUME" || plan.reject=="MARGIN")
         g_cnt.entry_reject_sizing++;
      else if(plan.reject=="STOPS_LEVEL" || plan.reject=="BAD_GEOMETRY")
         g_cnt.entry_reject_geometry++;
      else
         g_cnt.entry_reject_plan++;
      RgLogReject(sid,"PLAN",plan.reject,g_cfg.verbose);
      return;
     }
   RgLogRequest(sid,plan,sig,g_cfg.risk_percent);

   const ENUM_ORDER_TYPE order_type=(plan.direction>0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL);
   const bool submitted=g_exec.SubmitMarket(order_type,plan.volume,plan.sl,plan.tp,
                                            g_cfg.slippage_points);
   RgLogOrder(sid,submitted,(int)g_exec.State(),g_exec.RequestId(),
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
//| Gap measurement at the day boundary (server clock)               |
//+------------------------------------------------------------------+
//--- Once per new server day: measure prev-day close -> 00:00 open.
//--- prev_close comes from the last M1 bar of the previous trading day;
//--- a gap in the bar series (weekend, holiday) makes the span > 24h,
//--- which is fine: the weekend gap IS the Monday signal, unchanged.
void RgMeasureGap(const datetime day_start,const double pip)
  {
   g_day.gap_measured=false;
   g_day.gap_pips=0.0;

   MqlRates bars[];
   ArraySetAsSeries(bars,true);
   //--- Range around the boundary: prev-day tail + the first hours of the
   //--- new day. A day's first bar need not print at exactly 00:00
   //--- (illiquid roll, Monday open), so a two-sided window is required.
   const int got=CopyRates(_Symbol,PERIOD_M1,day_start-86400,day_start+3600,bars);
   if(got<2)
     {
      g_cnt.data_fail++;
      return;
     }
   //--- As-series (newest first). The new day's first bar is the OLDEST
   //--- bar with time >= day_start; prev_close is the newest bar before it.
   int first_new=-1;
   for(int i=got-1;i>=0;i--)
     {
      if(bars[i].time>=day_start)
        {
         first_new=i;
         break;
        }
     }
   if(first_new<0 || first_new+1>=got)
      return;                                    // no prev bar in range yet
   //--- Adjacency bound (probe semantics): the boundary gap is the roll
   //--- REOPEN versus the previous session's close. A prev bar older than
   //--- one hour means a weekend, holiday, or history hole - not the roll.
   if((long)bars[first_new].time-(long)bars[first_new+1].time>3600)
      return;
   const double prev_close=bars[first_new+1].close;
   const double open0=bars[first_new].open;
   g_day.gap_pips=(open0-prev_close)/pip;
   g_day.gap_measured=true;
   if(g_cfg.verbose)
      PrintFormat("RG001_GAP day=%s prev_bar=%s prev_close=%.5f open_bar=%s open0=%.5f "
                  "gap=%.2fp",TimeToString(day_start,TIME_DATE),
                  TimeToString(bars[first_new+1].time,TIME_DATE|TIME_MINUTES),
                  prev_close,TimeToString(bars[first_new].time,TIME_MINUTES),
                  open0,g_day.gap_pips);
  }

//+------------------------------------------------------------------+
//| Closed-bar decision (M1)                                         |
//+------------------------------------------------------------------+
void RgDecide(const datetime bar0_time)
  {
   g_cnt.decisions++;

   const double pip=RgPipSize();
   if(pip<=0.0)
     {
      g_cnt.data_fail++;
      return;
     }

   //--- Server-time day key and minute-of-day of the just-closed bar's
   //--- open (= the forming bar's open minus one minute... we use the
   //--- forming bar's open time directly: bar0_time is that open).
   MqlDateTime sb;
   TimeToStruct(bar0_time,sb);
   const int day_key=sb.year*10000+sb.mon*100+sb.day;
   const int server_min=sb.hour*60+sb.min;

   //--- New server day: reset per-day state and measure the boundary gap.
   if(day_key!=g_day.day_key)
     {
      g_day.day_key=day_key;
      g_day.long_used=0;
      g_day.short_used=0;
      RgMeasureGap(LswDayStart(bar0_time),pip);
     }
   if(!g_day.gap_measured)
      return;

   //--- Entry window gate (server minutes-of-day). No rollover/session
   //--- filter: the window IS the rollover window.
   if(server_min<g_p.entry_min_min || server_min>g_p.entry_max_min)
      return;

   //--- Arm at most one leg per direction per day.
   RgSignal sig;
   ZeroMemory(sig);
   if(g_p.use_long && g_day.long_used==0 &&
      g_day.gap_pips<=-g_p.gap_long_pips &&
      g_day.gap_pips>=-g_p.gap_max_pips)
     {
      sig.valid=true;
      sig.direction=LSW_DIR_LONG;
      sig.leg=RG_LEG_LONG;
      sig.gap_pips=g_day.gap_pips;
      sig.day_bar_time=LswDayStart(bar0_time);
      g_day.long_used=1;
      double atr=0.0;
      if(!LswAtrAt(g_atr_handle,1,atr))
         atr=0.0;                               // ATR optional: filters off at 0
      RgTryEnter(sig,bar0_time,atr);
      return;                                   // one entry per bar
     }
   if(g_p.use_short && g_day.short_used==0 &&
      g_day.gap_pips>=g_p.gap_short_pips &&
      g_day.gap_pips<=g_p.gap_max_pips)
     {
      sig.valid=true;
      sig.direction=LSW_DIR_SHORT;
      sig.leg=RG_LEG_SHORT;
      sig.gap_pips=g_day.gap_pips;
      sig.day_bar_time=LswDayStart(bar0_time);
      g_day.short_used=1;
      double atr=0.0;
      if(!LswAtrAt(g_atr_handle,1,atr))
         atr=0.0;
      RgTryEnter(sig,bar0_time,atr);
     }
  }

//+------------------------------------------------------------------+
//| Input validation. Fail closed at init.                           |
//+------------------------------------------------------------------+
bool RgValidateInputs()
  {
   string bad="";
   if(InpMagic==0)
      bad="InpMagic";
   else if(InpGapLongPips<0.1 || InpGapLongPips>50.0)
      bad="InpGapLongPips";
   else if(InpGapShortPips<0.1 || InpGapShortPips>50.0)
      bad="InpGapShortPips";
   else if(InpGapMaxPips<1.0 || InpGapMaxPips>500.0)
      bad="InpGapMaxPips";
   else if(InpEntryMinMin<0 || InpEntryMinMin>1439)
      bad="InpEntryMinMin";
   else if(InpEntryMaxMin<=InpEntryMinMin || InpEntryMaxMin>1439)
      bad="InpEntryMaxMin";
   else if(InpSlPips<1.0 || InpSlPips>200.0)
      bad="InpSlPips";
   else if(InpTpR<1.0 || InpTpR>100.0)
      bad="InpTpR";
   else if(InpTimeStopMin<5 || InpTimeStopMin>1440)
      bad="InpTimeStopMin";
   else if(InpMaxSpreadAtr<0.0 || InpMaxSpreadAtr>1.0)
      bad="InpMaxSpreadAtr";
   else if(InpMinAtrPoints<0.0)
      bad="InpMinAtrPoints";
   else if(InpRiskPercent<=0.0 || InpRiskPercent>5.0)
      bad="InpRiskPercent";
   else if(InpMaxTradesPerDay<1 || InpMaxTradesPerDay>10)
      bad="InpMaxTradesPerDay";
   else if(!InpUseLong && !InpUseShort)
      bad="InpUseLong|InpUseShort";
   if(bad!="")
     {
      PrintFormat("RG001_INIT_FAIL bad_input=%s",bad);
      return(false);
     }
   return(true);
  }

//+------------------------------------------------------------------+
//| Config                                                           |
//+------------------------------------------------------------------+
void RgConfigure()
  {
   ZeroMemory(g_cfg);
   g_cfg.server_gmt_offset_hours=InpServerGmtOffsetHours;
   g_cfg.server_dst_us_rule=InpServerDstUsRule;
   g_cfg.session_mode=LSW_SESS_BOTH;            // exits use flats only
   g_cfg.flatten_hour_server=InpFlattenHourServer;
   g_cfg.friday_flatten_hour_server=InpFridayFlattenHourServer;
   g_cfg.sl_buffer_atr=0.0;                     // SL exactly at synthetic extreme
   g_cfg.min_sl_spread_mult=0.0;                // fixed-pip stop, no spread floor
   g_cfg.tp_r=InpTpR;
   g_cfg.max_hold_bars=0;                       // position-age stop owns the exit
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
   g_p.use_long=InpUseLong;
   g_p.use_short=InpUseShort;
   g_p.gap_long_pips=InpGapLongPips;
   g_p.gap_short_pips=InpGapShortPips;
   g_p.gap_max_pips=InpGapMaxPips;
   g_p.entry_min_min=InpEntryMinMin;
   g_p.entry_max_min=InpEntryMaxMin;
   g_p.sl_pips=InpSlPips;
   g_p.tp_r=InpTpR;
   g_p.time_stop_min=InpTimeStopMin;
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
   //--- Wire contract: the governed post-run validator parses fixed field
   //--- names where m5_* denotes the EA's decision-timeframe series (M1 for
   //--- this EA) and m1_* denotes the terminal's M1 history bounds. For an
   //--- M1 decision series both groups read PERIOD_M1.
   long series_synchronized=0;
   long series_first_epoch=0;
   long series_terminal_first_epoch=0;
   long m1_server_first_epoch=0;
   long m1_terminal_first_epoch=0;
   long series_bars=0;
   if(!ReadSeriesInteger(PERIOD_M1,SERIES_SYNCHRONIZED,series_synchronized) ||
      !ReadSeriesInteger(PERIOD_M1,SERIES_FIRSTDATE,series_first_epoch) ||
      !ReadSeriesInteger(PERIOD_M1,SERIES_TERMINAL_FIRSTDATE,series_terminal_first_epoch) ||
      !ReadSeriesInteger(PERIOD_M1,SERIES_SERVER_FIRSTDATE,m1_server_first_epoch) ||
      !ReadSeriesInteger(PERIOD_M1,SERIES_TERMINAL_FIRSTDATE,m1_terminal_first_epoch) ||
      !ReadSeriesInteger(PERIOD_M1,SERIES_BARS_COUNT,series_bars))
      return(false);

   ResetLastError();
   const long terminal_maxbars=TerminalInfoInteger(TERMINAL_MAXBARS);
   const int terminal_error=GetLastError();
   datetime copytime_values[];
   ArraySetAsSeries(copytime_values,false);
   const datetime copytime_from=(datetime)series_first_epoch;
   ResetLastError();
   const int copytime_result=CopyTime(_Symbol,PERIOD_M1,copytime_from,1,copytime_values);
   const int copytime_error=GetLastError();
   const long copytime_first_epoch=(copytime_result==1 ? (long)copytime_values[0] : 0);

   PrintFormat("DATA_EPOCH_D0_SERIES_PROOF symbol=%s m5_synchronized=%I64d m5_first_epoch=%I64d m5_terminal_first_epoch=%I64d m1_server_first_epoch=%I64d m1_terminal_first_epoch=%I64d m5_bars=%I64d terminal_maxbars=%I64d copytime_from_epoch=%I64d copytime_count=1 copytime_result=%d copytime_first_epoch=%I64d copytime_last_error=%d",
               _Symbol,series_synchronized,series_first_epoch,series_terminal_first_epoch,
               m1_server_first_epoch,m1_terminal_first_epoch,series_bars,terminal_maxbars,
               (long)copytime_from,copytime_result,copytime_first_epoch,copytime_error);
   if(series_synchronized!=1 || series_first_epoch<=0 || series_terminal_first_epoch<=0 ||
      m1_server_first_epoch<=0 || m1_terminal_first_epoch<=0 || series_bars<=0 ||
      terminal_maxbars<=0 || terminal_error!=0 || copytime_result!=1 ||
      copytime_first_epoch!=series_first_epoch || copytime_error!=0)
      return(false);
   return(true);
  }

int OnInit()
  {
   if(!EmitD0SeriesProof())
     {
      Print("RG_FATAL reason=D0_SERIES_PROOF");
      return(INIT_FAILED);
     }
   if(!RgValidateInputs())
      return(INIT_PARAMETERS_INCORRECT);

   RgConfigure();
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
   g_pos_leg=RG_LEG_NONE;
   g_pos_open_time=0;
   g_pending_leg=RG_LEG_NONE;
   g_pending_risk_distance=0.0;
   g_submit_bar_time=0;
   g_exit_bar=0;
   g_exit_attempts=0;

   g_atr_handle=iATR(_Symbol,PERIOD_M1,14);
   if(g_atr_handle==INVALID_HANDLE)
     {
      PrintFormat("RG001_INIT_REJECT reason=atr_handle error=%d",GetLastError());
      return(INIT_FAILED);
     }

   g_trade.SetExpertMagicNumber(g_cfg.magic);
   g_trade.SetDeviationInPoints(g_cfg.slippage_points);
   g_trade.SetMarginMode();
   g_trade.SetTypeFillingBySymbol(_Symbol);

   if(!RgResetKernel())
     {
      Print("RG001_INIT_REJECT reason=kernel_configure");
      if(g_atr_handle!=INVALID_HANDLE)IndicatorRelease(g_atr_handle);
      return(INIT_FAILED);
     }

   RgLogClockDiag(g_cfg.server_gmt_offset_hours,g_cfg.server_dst_us_rule);

   //--- Warm-up: never decide on the bar that was already forming at attach.
   g_last_bar_time=iTime(_Symbol,PERIOD_M1,0);
   RgSyncPosition();
   if(!AfTele_OnInit("EA_RollReversion",InpHypothesisId,InpEnableTelemetry))
      { if(g_atr_handle!=INVALID_HANDLE)IndicatorRelease(g_atr_handle); return(INIT_FAILED); }
   return(INIT_SUCCEEDED);
  }

void OnDeinit(const int reason)
  {
   AfTele_OnDeinit();
   RgSummary(g_cnt,g_leg_signals,g_leg_trades,reason,g_runtime_failed);
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
   RgSyncPosition();

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
     }

   //--- Exits run on every tick: age time-stop and the hard flats.
   RgManageOpenPosition(clk);

   if(!new_bar)
      return;
   //--- A latched runtime failure stops NEW risk but never stops the exits.
   if(g_runtime_failed)
      return;

   RgMaybeRecycleKernel(bar0);
   RgDecide(bar0);
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
   RgLogDeal(g_active_sid,trans.deal,(int)entry,volume,price,net);

   if(entry==DEAL_ENTRY_IN)
     {
      g_cnt.entries_filled++;
      if(g_pending_leg>RG_LEG_NONE && g_pending_leg<RG_LEG_COUNT)
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
