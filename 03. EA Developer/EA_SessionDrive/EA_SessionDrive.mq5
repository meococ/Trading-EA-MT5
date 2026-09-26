//+------------------------------------------------------------------+
//| EA_SessionDrive.mq5                                              |
//| Session Drive (SD) - M5 closed-bar opening-range continuation.   |
//|                                                                  |
//| Each of the three GMT liquidity sessions (Asia 00-07, London     |
//| 07-16, New York 12-20) opens with a directional drive: the first |
//| or_bars closed M5 bars define the opening range, and the first   |
//| later close beyond an OR extreme is traded as continuation of    |
//| that session's drive. The complementary hypothesis to the        |
//| killed LSW sweep-fade family: where LSW bet on penetration       |
//| reversion, SD bets on penetration persistence.                   |
//|                                                                  |
//| Shared substrate: clock/DST/news from LSW_Session.mqh, sizing    |
//| and broker geometry from LSW_Risk.mqh (via the LswSweep          |
//| adapter), execution kernel and lifecycle telemetry from _Shared. |
//|                                                                  |
//| Frozen spec: research/CONTRACT.md. Do not change behaviour here  |
//| without a new hypothesis ID.                                     |
//+------------------------------------------------------------------+
#property strict
#property version   "1.00"
#property description "Session Drive - M5 closed-bar opening-range continuation"

//--- The shared kernel is fail-closed by default; an adopting EA must opt in
//--- explicitly. This define MUST precede the include.
#define AF_EXEC_EXPERIMENTAL_MUTATION_ENABLED 1
#include "../_Shared/Execution/AF_ExecutionKernel.mqh"

#include <Trade/Trade.mqh>

#include "../EA_LiquiditySweep/Include/LSW_Types.mqh"
#include "../EA_LiquiditySweep/Include/LSW_Session.mqh"
#include "../EA_LiquiditySweep/Include/LSW_Signal.mqh"
#include "../EA_LiquiditySweep/Include/LSW_Risk.mqh"
#include "Include/SD_Types.mqh"
#include "Include/SD_Signal.mqh"
#include "Include/SD_Telemetry.mqh"
#include "../_Shared/Telemetry/AF_LifecycleTelemetry.mqh"

#define SD_STRATEGY_ID              "SD"
#define SD_MAX_EXIT_ATTEMPTS_PER_BAR 5

//+------------------------------------------------------------------+
//| Inputs                                                           |
//+------------------------------------------------------------------+
input group "=== Identity and execution ==="
input ulong  InpMagic                   = 26451823;    // Magic number
input ulong  InpSlippagePoints          = 20;          // Max deviation (points)

input group "=== Clock and sessions ==="
input int    InpServerGmtOffsetHours    = 2;           // Server offset from GMT, winter
input bool   InpServerDstUsRule         = true;        // Server adds +1h on US DST
input bool   InpUseAsia                 = true;        // Asia session 00-07 GMT
input bool   InpUseLondon               = true;        // London session 07-16 GMT
input bool   InpUseNewYork              = true;        // New York session 12-20 GMT
input int    InpFlattenHourServer       = 22;          // Hard flat at this server hour
input int    InpFridayFlattenHourServer = 20;          // Friday hard flat, server hour

input group "=== Opening range ==="
input int    InpOrBars                  = 4;           // Opening-range length, M5 bars
input double InpOrMinAtr                = 0.5;         // OR range floor, xATR14
input double InpOrMaxAtr                = 6.0;         // OR range cap, xATR14
input int    InpBreakBars               = 48;          // Bars after OR a break may fire

input group "=== Exit ==="
input double InpSlBufferAtr             = 0.10;        // SL beyond OR midpoint, xATR
input double InpMinSlSpreadMult         = 4.0;         // SL floor as a multiple of spread
input double InpTpR                     = 1.30;        // Take profit in R
input int    InpMaxHoldBars             = 24;          // Time stop, M5 bars
input double InpBeAtR                   = 0.70;        // Break-even trigger in R, 0=off

input group "=== Filters and risk ==="
input double InpMaxSpreadAtr            = 0.20;        // Max spread as xATR
input double InpMinAtrPoints            = 40.0;        // Volatility floor, points
input int    InpNewsBlackoutMin         = 20;          // News blackout +/- minutes, 0=off
input double InpRiskPercent             = 0.35;        // Risk per trade, % of equity
input int    InpMaxTradesPerDay         = 6;           // Max entries per server day
input int    InpMaxConsecutiveLosses    = 4;           // Streak lock, 0=off
input double InpMaxDailyLossPct         = 2.0;         // Daily loss lock, %
input double InpMaxAccountDdPct         = 10.0;        // Account drawdown lock, %

input group "=== Telemetry ==="
input bool   InpVerboseLog              = true;        // Per-decision signal/reject lines
input bool   InpEnableTelemetry         = true;        // AlphaFactory lifecycle telemetry
input string InpHypothesisId            = "HYP-SDRIVE-GBP-M5-001";

//+------------------------------------------------------------------+
//| Globals                                                          |
//+------------------------------------------------------------------+
LswConfig           g_cfg;
SdParams            g_p;
LswCounters         g_cnt;
LswRiskState        g_risk;
SdSession           g_sessions[SD_SESS_COUNT];
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

//--- Per-session attribution (SD_SESS_* indexed).
long                g_sess_signals[SD_SESS_COUNT];
long                g_sess_trades[SD_SESS_COUNT];

//--- Carried from the submitted plan to the fill.
int                 g_pending_session=SD_SESS_NONE;
double              g_pending_risk_distance=0.0;

//--- Exit-attempt throttle so a permanently failing close cannot spam.
datetime            g_exit_bar=0;
int                 g_exit_attempts=0;

//+------------------------------------------------------------------+
//| Ownership scans. All fail-closed: a scan that cannot be trusted   |
//| returns -1 and callers must refuse to trade.                      |
//+------------------------------------------------------------------+
int SdFindOwnedPosition(ulong &ticket)
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

int SdCountSymbolPositions()
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

int SdCountOwnedOrders()
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
//| Execution kernel lifecycle (same recycle doctrine as LSW)         |
//+------------------------------------------------------------------+
bool SdResetKernel()
  {
   if(CheckPointer(g_exec)!=POINTER_INVALID)
     {
      delete g_exec;
      g_exec=NULL;
     }
   g_exec=new CAFExecutionKernel();
   if(CheckPointer(g_exec)==POINTER_INVALID)
      return(false);
   if(!g_exec.Configure(_Symbol,g_cfg.magic,SD_STRATEGY_ID))
      return(false);
   g_exec.Reconcile();
   return(true);
  }

void SdMaybeRecycleKernel(const datetime bar_time)
  {
   if(CheckPointer(g_exec)==POINTER_INVALID)
      return;
   const AF_EXEC_STATE state=g_exec.State();
   if(state==AF_EXEC_IDLE)
      return;
   if(g_submit_bar_time!=0 && bar_time==g_submit_bar_time)
      return;                                   // never recycle on the submit bar
   ulong owned_ticket=0;
   if(SdFindOwnedPosition(owned_ticket)!=0)
      return;
   if(SdCountOwnedOrders()!=0)
      return;

   if(state==AF_EXEC_PENDING_NEW || state==AF_EXEC_ORDER_PLACED ||
      state==AF_EXEC_PARTIALLY_FILLED)
      g_cnt.entry_timeouts++;                   // sent, then vanished without a fill
   if(state==AF_EXEC_RECOVERING_AMBIGUOUS)
      g_cnt.kernel_ambiguous++;
   if(SdResetKernel())
      g_cnt.kernel_recycles++;
   else
      g_runtime_failed=true;
  }

//+------------------------------------------------------------------+
//| Position mirror and exits                                        |
//+------------------------------------------------------------------+
void SdSyncPosition()
  {
   ulong ticket=0;
   const int owned=SdFindOwnedPosition(ticket);
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
   SdLogPosition(g_active_sid,g_pos_ticket,volume,g_pos_open_price,
                 position_sl,position_tp,realized_risk);
  }

bool SdClosePosition(const string reason)
  {
   if(g_pos_ticket==0)
      return(true);
   const datetime bar_time=iTime(_Symbol,PERIOD_M5,0);
   if(bar_time!=g_exit_bar)
     {
      g_exit_bar=bar_time;
      g_exit_attempts=0;
     }
   if(g_exit_attempts>=SD_MAX_EXIT_ATTEMPTS_PER_BAR)
      return(false);
   g_exit_attempts++;

   g_trade.SetExpertMagicNumber(g_cfg.magic);
   g_trade.SetDeviationInPoints(g_cfg.slippage_points);
   const ulong ticket=g_pos_ticket;
   const bool sent=g_trade.PositionClose(ticket,g_cfg.slippage_points);
   const uint retcode=g_trade.ResultRetcode();
   const bool ok=(sent && (retcode==TRADE_RETCODE_DONE ||
                           retcode==TRADE_RETCODE_DONE_PARTIAL));
   SdLogExit(g_active_sid,reason,ticket,ok,retcode);
   if(!ok)
      g_cnt.exit_reject++;
   return(ok);
  }

void SdTryBreakEven()
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
   SdLogBreakEven(g_active_sid,g_pos_ticket,new_sl,ok,retcode);
   if(ok)
     {
      g_be_done=true;
      g_cnt.be_moves++;
     }
   else
      g_cnt.be_rejects++;
  }

void SdManageOpenPosition(const LswClock &clk)
  {
   if(g_pos_ticket==0)
      return;
   //--- Hard flats first: the scalp holding contract (overnight == 0,
   //--- weekend == 0) is structural, not a preference.
   if(clk.friday_flatten)
     {
      if(SdClosePosition("FRIDAY_FLAT"))
         g_cnt.exit_friday_flat++;
      return;
     }
   if(clk.flatten)
     {
      if(SdClosePosition("DAILY_FLAT"))
         g_cnt.exit_daily_flat++;
      return;
     }
   if(g_cfg.max_hold_bars>0 && g_pos_bars_held>=g_cfg.max_hold_bars)
     {
      if(SdClosePosition("TIME_STOP"))
         g_cnt.exit_time_stop++;
      return;
     }
   SdTryBreakEven();
  }

//+------------------------------------------------------------------+
//| Closed-bar decision                                              |
//+------------------------------------------------------------------+
void SdDecide(const datetime bar0_time,const LswClock &clk_now)
  {
   g_signal_id++;
   g_cnt.decisions++;
   const long sid=g_signal_id;

   //--- Bar selection. shift 0 is the forming bar and is NEVER read.
   MqlRates bar;
   ZeroMemory(bar);
   if(!LswBarAt(_Symbol,1,bar))
     {
      g_cnt.data_fail++;
      return;
     }
   if((long)bar0_time-(long)bar.time!=LSW_SEC_PER_M5)
     {
      g_cnt.filt_bar_gap++;
      return;
     }

   double atr=0.0;
   if(!LswAtrAt(g_atr_handle,1,atr))
     {
      g_cnt.data_fail++;
      return;
     }

   //--- Session membership is judged on the CLOSED bar's own GMT stamp.
   LswClock clk_bar;
   if(!LswClockRead(bar.time,g_cfg,clk_bar))
     {
      g_cnt.data_fail++;
      return;
     }
   MqlDateTime gb;
   TimeToStruct(clk_bar.gmt_time,gb);
   const int gmt_min=gb.hour*60+gb.min;

   //--- Feed every enabled session FSM; at most one drive per bar.
   SdDrive drive;
   if(!SdDetectDrive(g_sessions,bar,clk_bar.gmt_time,gmt_min,atr,
                     g_p,g_cnt,drive))
      return;                                       // forming/armed/dead: no signal

   g_cnt.signals_seen++;
   if(drive.direction>0)
      g_cnt.signals_long++;
   else
      g_cnt.signals_short++;
   if(drive.session>SD_SESS_NONE && drive.session<SD_SESS_COUNT)
      g_sess_signals[drive.session]++;
   SdLogSignal(sid,drive,clk_now,g_cfg.verbose);

   //--- Entry filters, one counter per reject.
   if(clk_now.weekend || clk_now.rollover || clk_now.flatten)
     {
      if(clk_now.rollover)
         g_cnt.filt_rollover++;
      else if(clk_now.flatten)
         g_cnt.filt_flatten++;
      else
         g_cnt.filt_session++;
      SdLogReject(sid,"FILTER","SESSION",g_cfg.verbose);
      return;
     }
   const int symbol_positions=SdCountSymbolPositions();
   const int owned_orders=SdCountOwnedOrders();
   if(symbol_positions<0 || owned_orders<0)
     {
      g_cnt.data_fail++;                        // a scan we cannot trust: fail closed
      SdLogReject(sid,"FILTER","SCAN_FAIL",g_cfg.verbose);
      return;
     }
   if(symbol_positions!=0)
     {
      g_cnt.filt_position_open++;
      SdLogReject(sid,"FILTER","POSITION_OPEN",g_cfg.verbose);
      return;
     }
   if(CheckPointer(g_exec)==POINTER_INVALID || g_exec.State()!=AF_EXEC_IDLE ||
      owned_orders!=0)
     {
      g_cnt.filt_exec_busy++;
      SdLogReject(sid,"FILTER","EXEC_BUSY",g_cfg.verbose);
      return;
     }
   if(LswRiskBlocked(g_risk,g_cfg,g_cnt))
     {
      SdLogReject(sid,"FILTER","RISK_LOCK",g_cfg.verbose);
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
      SdLogReject(sid,"FILTER","ATR_FLOOR",g_cfg.verbose);
      return;
     }
   if(tick.ask-tick.bid>g_cfg.max_spread_atr*atr)
     {
      g_cnt.filt_spread++;
      SdLogReject(sid,"FILTER","SPREAD",g_cfg.verbose);
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
      SdLogReject(sid,"FILTER","NEWS",g_cfg.verbose);
      return;
     }

   //--- Plan via the shared LswBuildPlan path (OR midpoint = stop anchor).
   LswSweep sweep;
   SdDriveToSweep(drive,sweep);
   LswPlan plan;
   if(!LswBuildPlan(_Symbol,sweep,g_cfg,tick.ask,tick.bid,plan))
     {
      if(plan.reject=="SIZING" || plan.reject=="VOLUME" || plan.reject=="MARGIN")
         g_cnt.entry_reject_sizing++;
      else if(plan.reject=="STOPS_LEVEL" || plan.reject=="BAD_GEOMETRY")
         g_cnt.entry_reject_geometry++;
      else
         g_cnt.entry_reject_plan++;
      SdLogReject(sid,"PLAN",plan.reject,g_cfg.verbose);
      return;
     }
   SdLogRequest(sid,plan,drive,g_cfg.risk_percent);

   const ENUM_ORDER_TYPE order_type=(plan.direction>0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL);
   const bool submitted=g_exec.SubmitMarket(order_type,plan.volume,plan.sl,plan.tp,
                                            g_cfg.slippage_points);
   SdLogOrder(sid,submitted,(int)g_exec.State(),g_exec.RequestId(),
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
   g_pending_session=drive.session;
   g_pending_risk_distance=plan.risk_distance;
   AfTele_SetPlannedRisk(plan.risk_distance/point,
                         AccountInfoDouble(ACCOUNT_EQUITY)*g_cfg.risk_percent/100.0);
  }

//+------------------------------------------------------------------+
//| Input validation. Fail closed at init rather than at runtime.    |
//+------------------------------------------------------------------+
bool SdValidateInputs()
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
   else if(!InpUseAsia && !InpUseLondon && !InpUseNewYork)
      bad="no session enabled";
   else if(InpOrBars<1 || InpOrBars>60)                   bad="InpOrBars";
   else if(InpOrMinAtr<=0.0 || InpOrMinAtr>10.0)          bad="InpOrMinAtr";
   else if(InpOrMaxAtr<=InpOrMinAtr || InpOrMaxAtr>50.0)  bad="InpOrMaxAtr";
   else if(InpBreakBars<1 || InpBreakBars>200)            bad="InpBreakBars";
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
   if(StringLen(bad)==0)
      return(true);
   PrintFormat("SD001_INIT_REJECT input=%s",bad);
   return(false);
  }

void SdLoadConfig()
  {
   ZeroMemory(g_cfg);
   g_cfg.server_gmt_offset_hours=InpServerGmtOffsetHours;
   g_cfg.server_dst_us_rule=InpServerDstUsRule;
   g_cfg.session_mode=LSW_SESS_BOTH;                 // inert: SD has own sessions
   g_cfg.flatten_hour_server=InpFlattenHourServer;
   g_cfg.friday_flatten_hour_server=InpFridayFlattenHourServer;
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

   g_p.or_bars=InpOrBars;
   g_p.or_min_atr=InpOrMinAtr;
   g_p.or_max_atr=InpOrMaxAtr;
   g_p.break_bars=InpBreakBars;
   g_p.use_asia=InpUseAsia;
   g_p.use_london=InpUseLondon;
   g_p.use_newyork=InpUseNewYork;
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
      Print("SD_FATAL reason=D0_SERIES_PROOF");
      return(INIT_FAILED);
     }
   if(!SdValidateInputs())
      return(INIT_PARAMETERS_INCORRECT);

   SdLoadConfig();
   ZeroMemory(g_cnt);
   ZeroMemory(g_risk);
   for(int s=0;s<SD_SESS_COUNT;s++)
      ZeroMemory(g_sessions[s]);
   ArrayInitialize(g_sess_signals,0);
   ArrayInitialize(g_sess_trades,0);
   g_runtime_failed=false;
   g_pos_ticket=0;
   g_pos_direction=LSW_DIR_NONE;
   g_pos_open_price=0.0;
   g_pos_risk_distance=0.0;
   g_pos_bars_held=0;
   g_be_done=false;
   g_pending_session=SD_SESS_NONE;
   g_pending_risk_distance=0.0;
   g_submit_bar_time=0;
   g_exit_bar=0;
   g_exit_attempts=0;

   g_atr_handle=iATR(_Symbol,PERIOD_M5,LSW_ATR_PERIOD);
   if(g_atr_handle==INVALID_HANDLE)
     {
      PrintFormat("SD001_INIT_REJECT reason=atr_handle error=%d",GetLastError());
      return(INIT_FAILED);
     }

   g_trade.SetExpertMagicNumber(g_cfg.magic);
   g_trade.SetDeviationInPoints(g_cfg.slippage_points);
   g_trade.SetMarginMode();
   g_trade.SetTypeFillingBySymbol(_Symbol);

   if(!SdResetKernel())
     {
      Print("SD001_INIT_REJECT reason=kernel_configure");
      { /*hg*/ if(g_atr_handle!=INVALID_HANDLE)IndicatorRelease(g_atr_handle); /*hg*/return(INIT_FAILED); }
     }

   SdLogClockDiag(g_cfg.server_gmt_offset_hours,g_cfg.server_dst_us_rule);

   //--- Warm-up: never decide on the bar that was already forming at attach.
   g_last_bar_time=iTime(_Symbol,PERIOD_M5,0);
   SdSyncPosition();
   if(!AfTele_OnInit("EA_SessionDrive",InpHypothesisId,InpEnableTelemetry))
      { /*hg*/ if(g_atr_handle!=INVALID_HANDLE)IndicatorRelease(g_atr_handle); /*hg*/return(INIT_FAILED); }
   return(INIT_SUCCEEDED);
  }

void OnDeinit(const int reason)
  {
   AfTele_OnDeinit();
   SdSummary(g_cnt,g_sess_signals,g_sess_trades,reason,g_runtime_failed);
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
   SdSyncPosition();

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
   SdManageOpenPosition(clk);

   if(!new_bar)
      return;
   //--- A latched runtime failure stops NEW risk but never stops the exits
   //--- above: getting flat must always remain possible.
   if(g_runtime_failed)
      return;

   SdMaybeRecycleKernel(bar0);

   //--- The clock used for the entry filters is the confirmation bar's CLOSE,
   //--- which is exactly the forming bar's open time.
   LswClock clk_decision;
   if(!LswClockRead(bar0,g_cfg,clk_decision))
     {
      g_cnt.data_fail++;
      return;
     }
   SdDecide(bar0,clk_decision);
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
   SdLogDeal(g_active_sid,trans.deal,(int)entry,volume,price,net);

   if(entry==DEAL_ENTRY_IN)
     {
      g_cnt.entries_filled++;
      if(g_pending_session>SD_SESS_NONE && g_pending_session<SD_SESS_COUNT)
         g_sess_trades[g_pending_session]++;
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
