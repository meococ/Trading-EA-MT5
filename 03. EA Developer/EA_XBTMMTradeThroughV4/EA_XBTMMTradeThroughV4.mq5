//+------------------------------------------------------------------+
//| EA_XBTMMTradeThroughV4.mq5                                       |
//| HYP-XBT-MM-TRADETHROUGH-004 - digest-bound virtual engine        |
//+------------------------------------------------------------------+
#property copyright "AlphaFactory research"
#property version   "4.00"
#property strict
#property description "BitMEX XBTUSD passive trade-through market-making simulator"

input bool   InpResearchAutoMode=true;
input bool   InpEconomicUseForbidden=true;
input string InpIndexFile="xbtmm\\pilot_v4_20180101_20180101_index.csv";
input string InpOutputPrefix="xbtmm\\outputs\\XBTMM004_20180101";

const string HYPOTHESIS_ID="HYP-XBT-MM-TRADETHROUGH-004";
const string EXPECTED_SYMBOL="EURUSD";
const double PRICE_TICK=0.5;
const long   QUOTE_SIZE=100;
const long   SOFT_INVENTORY=200;
const long   HARD_INVENTORY=400;
const long   VENUE_LOT_CHANGE_US=1623126600000000;
const long   VENUE_LOT_BEFORE=1;
const long   VENUE_LOT_AFTER=100;
const ulong  FNV64_OFFSET=0xCBF29CE484222325;
const ulong  FNV64_PRIME=0x100000001B3;
const long   ORDER_LATENCY_US=400000;
const long   ACTION_INTERVAL_US=2000000;
const long   MAX_QUOTE_AGE_US=2000000;
const long   MAX_HOLD_US=2700000000;
const long   FUNDING_INTERVAL_US=28800000000;
const long   FUNDING_BLACKOUT_LEAD_US=900000000;
const long   FUNDING_QUIET_LEAD_US=4400000;
const long   FUNDING_FIRST_CANCEL_LEAD_US=2400000;
const long   FUNDING_SECOND_CANCEL_LEAD_US=400000;
const double TAKER_FEE_RATE=0.00075;
const double STARTING_EQUITY_XBT=1.0;
const int    EVENT_QUOTE=1;
const int    EVENT_TRADE=2;
const int    SIDE_BUY=1;
const int    SIDE_SELL=-1;
const int    ACTION_NONE=0;
const int    ACTION_PLACE=1;
const int    ACTION_AMEND=2;
const int    ACTION_CANCEL=3;
const int    MAX_FIFO_LOTS=8;

struct VirtualOrder
  {
   bool   active;
   double price;
   long   expiry_us;
   int    pending_action;
   double pending_price;
   long   pending_decision_us;
   long   pending_effective_us;
   long   pending_expiry_us;
  };

struct InventoryLot
  {
   int    side;
   long   quantity;
   double price;
   long   open_us;
  };

struct EngineState
  {
   string id;
   bool   candidate;
   VirtualOrder bid_order;
   VirtualOrder ask_order;
   long   inventory;
   double average_entry;
   InventoryLot lots[8];
   int    lot_count;
   double realized_xbt;
   double taker_fees_xbt;
   double gross_profit_xbt;
   double gross_loss_xbt;
   double peak_equity_xbt;
   double max_drawdown_xbt_pct;
   double peak_equity_usd;
   double max_collateral_usd_drawdown_pct;
   long   maker_fills;
   long   forced_flattens;
   long   closed_fragments;
   long   quote_actions;
   long   action_interval_violations;
   long   hard_cap_violations;
   long   venue_lot_violations;
   long   touch_ignored;
   long   exact_ignored;
   long   quote_expiries;
   long   pending_action_latency_violations;
   long   funding_live_after_blackout;
   long   max_age_matched_after_expiry;
   long   fifo_accounting_violations;
   long   pending_action_fill_races;
   long   last_action_us;
   long   action_hour_key;
   long   actions_this_hour;
   long   max_actions_per_hour;
   bool   prefer_bid;
   bool   risk_flatten_pending;
   string risk_flatten_reason;
  };

EngineState g_candidate;
EngineState g_null;
int    g_fill_handle=INVALID_HANDLE;
bool   g_simulation_done=false;
double g_best_bid=0.0;
double g_best_ask=0.0;
long   g_bid_size=0;
long   g_ask_size=0;
long   g_last_quote_us=0;
long   g_last_event_us=0;
double g_last_mid=0.0;
long   g_records=0;
long   g_quote_records=0;
long   g_trade_records=0;
long   g_crossed_records=0;
long   g_stale_quote_pauses=0;
long   g_timestamp_regressions=0;
long   g_touch_fill_attempts=0;
long   g_exact_fill_attempts=0;
long   g_index_days=0;
long   g_index_expected_records=0;
long   g_index_expected_quotes=0;
long   g_index_expected_trades=0;
long   g_first_event_us=0;

void ResetOrder(VirtualOrder &order)
  {
   order.active=false;
   order.price=0.0;
   order.expiry_us=0;
   order.pending_action=ACTION_NONE;
   order.pending_price=0.0;
   order.pending_decision_us=0;
   order.pending_effective_us=0;
   order.pending_expiry_us=0;
  }

void InitEngine(EngineState &state,const string id,const bool candidate)
  {
   state.id=id;
   state.candidate=candidate;
   ResetOrder(state.bid_order);
   ResetOrder(state.ask_order);
   state.inventory=0;
   state.average_entry=0.0;
   state.lot_count=0;
   for(int lot_index=0;lot_index<MAX_FIFO_LOTS;lot_index++)
     {
      state.lots[lot_index].side=0;
      state.lots[lot_index].quantity=0;
      state.lots[lot_index].price=0.0;
      state.lots[lot_index].open_us=0;
     }
   state.realized_xbt=0.0;
   state.taker_fees_xbt=0.0;
   state.gross_profit_xbt=0.0;
   state.gross_loss_xbt=0.0;
   state.peak_equity_xbt=STARTING_EQUITY_XBT;
   state.max_drawdown_xbt_pct=0.0;
   state.peak_equity_usd=0.0;
   state.max_collateral_usd_drawdown_pct=0.0;
   state.maker_fills=0;
   state.forced_flattens=0;
   state.closed_fragments=0;
   state.quote_actions=0;
   state.action_interval_violations=0;
   state.hard_cap_violations=0;
   state.venue_lot_violations=0;
   state.touch_ignored=0;
   state.exact_ignored=0;
   state.quote_expiries=0;
   state.pending_action_latency_violations=0;
   state.funding_live_after_blackout=0;
   state.max_age_matched_after_expiry=0;
   state.fifo_accounting_violations=0;
   state.pending_action_fill_races=0;
   state.last_action_us=0;
   state.action_hour_key=-1;
   state.actions_this_hour=0;
   state.max_actions_per_hour=0;
   state.prefer_bid=true;
   state.risk_flatten_pending=false;
   state.risk_flatten_reason="";
  }

double FloorToTick(const double value)
  {
   return MathFloor(value/PRICE_TICK+1e-12)*PRICE_TICK;
  }

double CeilToTick(const double value)
  {
   return MathCeil(value/PRICE_TICK-1e-12)*PRICE_TICK;
  }

ulong DigestMix(const ulong digest,const long value)
  {
   return (digest^(ulong)value)*FNV64_PRIME;
  }

ulong UpdateEventDigest(ulong digest,const long time_us,const int kind,
                        const double bid,const double ask,const long bid_size,
                        const long ask_size,const double trade_price,
                        const long trade_size,const int side)
  {
   digest=DigestMix(digest,time_us);
   digest=DigestMix(digest,(long)kind);
   digest=DigestMix(digest,(long)MathRound(bid/PRICE_TICK));
   digest=DigestMix(digest,(long)MathRound(ask/PRICE_TICK));
   digest=DigestMix(digest,bid_size);
   digest=DigestMix(digest,ask_size);
   digest=DigestMix(digest,(long)MathRound(trade_price/PRICE_TICK));
   digest=DigestMix(digest,trade_size);
   digest=DigestMix(digest,(long)side);
   return digest;
  }

bool ValidBook()
  {
   return g_best_bid>0.0 && g_best_ask>g_best_bid && g_bid_size>0 && g_ask_size>0;
  }

double MidPrice()
  {
   return ValidBook() ? (g_best_bid+g_best_ask)*0.5 : g_last_mid;
  }

double UnrealizedXbt(const EngineState &state,const double mark)
  {
   if(state.inventory==0 || state.average_entry<=0.0 || mark<=0.0)
      return 0.0;
   return (double)state.inventory*(1.0/state.average_entry-1.0/mark);
  }

void UpdateEquity(EngineState &state,const double mark)
  {
   if(mark<=0.0)
      return;
   const double equity_xbt=STARTING_EQUITY_XBT+state.realized_xbt+UnrealizedXbt(state,mark);
   if(equity_xbt>state.peak_equity_xbt)
      state.peak_equity_xbt=equity_xbt;
   if(state.peak_equity_xbt>0.0)
     {
      const double xbt_drawdown=100.0*(state.peak_equity_xbt-equity_xbt)/state.peak_equity_xbt;
      if(xbt_drawdown>state.max_drawdown_xbt_pct)
         state.max_drawdown_xbt_pct=xbt_drawdown;
     }
   const double equity_usd=equity_xbt*mark;
   if(state.peak_equity_usd<=0.0 || equity_usd>state.peak_equity_usd)
      state.peak_equity_usd=equity_usd;
   if(state.peak_equity_usd>0.0)
     {
      const double drawdown=100.0*(state.peak_equity_usd-equity_usd)/state.peak_equity_usd;
      if(drawdown>state.max_collateral_usd_drawdown_pct)
         state.max_collateral_usd_drawdown_pct=drawdown;
     }
  }

void LogFill(const EngineState &state,const long time_us,const string type,
             const int side,const long quantity,const double price,
             const double realized_delta,const double fee_xbt,const string reason)
  {
   if(g_fill_handle==INVALID_HANDLE)
      return;
   FileWrite(g_fill_handle,state.id,time_us,type,(side>0 ? "BUY" : "SELL"),
             quantity,DoubleToString(price,1),state.inventory,
             DoubleToString(state.average_entry,8),
             DoubleToString(realized_delta,12),DoubleToString(fee_xbt,12),
             DoubleToString(state.realized_xbt,12),reason);
  }

void ClearLot(InventoryLot &lot)
  {
   lot.side=0;
   lot.quantity=0;
   lot.price=0.0;
   lot.open_us=0;
  }

void RemoveFirstLot(EngineState &state)
  {
   if(state.lot_count<=0)
      return;
   for(int i=1;i<state.lot_count;i++)
      state.lots[i-1]=state.lots[i];
   state.lot_count--;
   ClearLot(state.lots[state.lot_count]);
  }

bool AppendLot(EngineState &state,const int side,const long quantity,
               const double price,const long open_us)
  {
   if(quantity<=0)
      return true;
   if(state.lot_count>=MAX_FIFO_LOTS)
     {
      state.fifo_accounting_violations++;
      return false;
     }
   state.lots[state.lot_count].side=side;
   state.lots[state.lot_count].quantity=quantity;
   state.lots[state.lot_count].price=price;
   state.lots[state.lot_count].open_us=open_us;
   state.lot_count++;
   return true;
  }

void RecomputeInventory(EngineState &state)
  {
   state.inventory=0;
   state.average_entry=0.0;
   double reciprocal_sum=0.0;
   int common_side=0;
   long absolute_quantity=0;
   for(int i=0;i<state.lot_count;i++)
     {
      const InventoryLot lot=state.lots[i];
      if(lot.quantity<=0 || lot.price<=0.0 ||
         (lot.side!=SIDE_BUY && lot.side!=SIDE_SELL))
        {
         state.fifo_accounting_violations++;
         continue;
        }
      if(common_side==0)
         common_side=lot.side;
      else if(common_side!=lot.side)
         state.fifo_accounting_violations++;
      state.inventory+=(long)lot.side*lot.quantity;
      absolute_quantity+=lot.quantity;
      reciprocal_sum+=(double)lot.quantity/lot.price;
     }
   if(absolute_quantity>0 && reciprocal_sum>0.0)
      state.average_entry=(double)absolute_quantity/reciprocal_sum;
  }

void ApplyFill(EngineState &state,const long time_us,const int side,
               const long quantity,const double price,const bool passive,
               const string reason)
  {
   if(quantity<=0 || price<=0.0 || (side!=SIDE_BUY && side!=SIDE_SELL))
      return;
   long remaining=quantity;
   double realized_delta=0.0;

   while(remaining>0 && state.lot_count>0 && state.lots[0].side!=side)
     {
      const long close_quantity=(long)MathMin((double)remaining,
                                              (double)state.lots[0].quantity);
      realized_delta+=(double)(state.lots[0].side*close_quantity)*
                      (1.0/state.lots[0].price-1.0/price);
      state.lots[0].quantity-=close_quantity;
      remaining-=close_quantity;
      state.closed_fragments++;
      if(state.lots[0].quantity==0)
         RemoveFirstLot(state);
     }
   if(remaining>0 && !AppendLot(state,side,remaining,price,time_us))
      return;
   RecomputeInventory(state);

   const double fee_xbt=(passive ? 0.0 : (double)quantity/price*TAKER_FEE_RATE);
   realized_delta-=fee_xbt;
   state.realized_xbt+=realized_delta;
   state.taker_fees_xbt+=fee_xbt;
   if(realized_delta>0.0)
      state.gross_profit_xbt+=realized_delta;
   else if(realized_delta<0.0)
      state.gross_loss_xbt+=-realized_delta;
   if(passive)
      state.maker_fills++;
   LogFill(state,time_us,(passive ? "MAKER_FILL" : "TAKER_FLATTEN"),
           side,quantity,price,realized_delta,fee_xbt,reason);
  }

void CountQuoteAction(EngineState &state,const long time_us)
  {
   if(state.last_action_us>0 && time_us-state.last_action_us<ACTION_INTERVAL_US)
      state.action_interval_violations++;
   state.last_action_us=time_us;
   state.quote_actions++;
   const long hour_key=time_us/3600000000;
   if(hour_key!=state.action_hour_key)
     {
      state.action_hour_key=hour_key;
      state.actions_this_hour=0;
     }
   state.actions_this_hour++;
   if(state.actions_this_hour>state.max_actions_per_hour)
      state.max_actions_per_hour=state.actions_this_hour;
  }

bool ActionReady(const EngineState &state,const long time_us)
  {
   return state.last_action_us==0 || time_us-state.last_action_us>=ACTION_INTERVAL_US;
  }

void ClearPendingAction(VirtualOrder &order)
  {
   order.pending_action=ACTION_NONE;
   order.pending_price=0.0;
   order.pending_decision_us=0;
   order.pending_effective_us=0;
   order.pending_expiry_us=0;
  }

bool ScheduleOrderAction(EngineState &state,VirtualOrder &order,
                         const long decision_us,const int action,
                         const double target_price)
  {
   if(order.pending_action!=ACTION_NONE || !ActionReady(state,decision_us))
      return false;
   if(action==ACTION_CANCEL && !order.active)
      return false;
   if(action==ACTION_PLACE && order.active)
      return false;
   if(action==ACTION_AMEND && !order.active)
      return false;
   order.pending_action=action;
   order.pending_price=target_price;
   order.pending_decision_us=decision_us;
   order.pending_effective_us=decision_us+ORDER_LATENCY_US;
   order.pending_expiry_us=(action==ACTION_CANCEL ? order.expiry_us :
                            g_last_quote_us+MAX_QUOTE_AGE_US);
   CountQuoteAction(state,decision_us);
   return true;
  }

void ApplyPendingAction(EngineState &state,VirtualOrder &order)
  {
   if(order.pending_action==ACTION_NONE)
      return;
   if(order.pending_effective_us-order.pending_decision_us!=ORDER_LATENCY_US)
      state.pending_action_latency_violations++;
   if(order.pending_action==ACTION_CANCEL)
     {
      order.active=false;
      order.price=0.0;
      order.expiry_us=0;
     }
   else
     {
      order.active=true;
      order.price=order.pending_price;
      order.expiry_us=order.pending_expiry_us;
     }
   ClearPendingAction(order);
  }

void ApplyPendingBeforeMarketEvent(EngineState &state,const long time_us)
  {
   // PLACE is adverse at the exact boundary: it is live before the trade.
   if(state.bid_order.pending_action==ACTION_PLACE &&
      state.bid_order.pending_effective_us<=time_us)
      ApplyPendingAction(state,state.bid_order);
   if(state.ask_order.pending_action==ACTION_PLACE &&
      state.ask_order.pending_effective_us<=time_us)
      ApplyPendingAction(state,state.ask_order);
   // CANCEL/AMEND strictly before this event already changed the book.
   if(state.bid_order.pending_action!=ACTION_NONE &&
      state.bid_order.pending_action!=ACTION_PLACE &&
      state.bid_order.pending_effective_us<time_us)
      ApplyPendingAction(state,state.bid_order);
   if(state.ask_order.pending_action!=ACTION_NONE &&
      state.ask_order.pending_action!=ACTION_PLACE &&
      state.ask_order.pending_effective_us<time_us)
      ApplyPendingAction(state,state.ask_order);
  }

void ApplyPendingAfterTrade(EngineState &state,const long time_us)
  {
   // At an equal timestamp the old order sees the trade before cancel/amend.
   if(state.bid_order.pending_action!=ACTION_NONE &&
      state.bid_order.pending_action!=ACTION_PLACE &&
      state.bid_order.pending_effective_us<=time_us)
      ApplyPendingAction(state,state.bid_order);
   if(state.ask_order.pending_action!=ACTION_NONE &&
      state.ask_order.pending_action!=ACTION_PLACE &&
      state.ask_order.pending_effective_us<=time_us)
      ApplyPendingAction(state,state.ask_order);
  }

void ApplyPendingWithoutMarketEvent(EngineState &state,const long time_us)
  {
   if(state.bid_order.pending_action!=ACTION_NONE &&
      state.bid_order.pending_effective_us<=time_us)
      ApplyPendingAction(state,state.bid_order);
   if(state.ask_order.pending_action!=ACTION_NONE &&
      state.ask_order.pending_effective_us<=time_us)
      ApplyPendingAction(state,state.ask_order);
  }

void ExpireStaleOrders(EngineState &state,const long time_us)
  {
   const bool bid_expired=((state.bid_order.active && state.bid_order.expiry_us>0 &&
                            time_us>=state.bid_order.expiry_us) ||
                           (state.bid_order.pending_action!=ACTION_NONE &&
                            state.bid_order.pending_expiry_us>0 &&
                            time_us>=state.bid_order.pending_expiry_us));
   if(bid_expired)
     {
      ResetOrder(state.bid_order);
      state.quote_expiries++;
     }
   const bool ask_expired=((state.ask_order.active && state.ask_order.expiry_us>0 &&
                            time_us>=state.ask_order.expiry_us) ||
                           (state.ask_order.pending_action!=ACTION_NONE &&
                            state.ask_order.pending_expiry_us>0 &&
                            time_us>=state.ask_order.pending_expiry_us));
   if(ask_expired)
     {
      ResetOrder(state.ask_order);
      state.quote_expiries++;
     }
  }

long NextFundingTime(const long time_us)
  {
   return (time_us/FUNDING_INTERVAL_US+1)*FUNDING_INTERVAL_US;
  }

bool FundingBlackout(const long time_us)
  {
   const long funding_time=NextFundingTime(time_us);
   const long blackout_start=funding_time-FUNDING_BLACKOUT_LEAD_US;
   return time_us>=blackout_start && time_us<funding_time;
  }

bool FundingRetirementQuiet(const long time_us)
  {
   const long funding_time=NextFundingTime(time_us);
   const long quiet_start=funding_time-FUNDING_BLACKOUT_LEAD_US-FUNDING_QUIET_LEAD_US;
   return time_us>=quiet_start && time_us<funding_time;
  }

void ForceFlatten(EngineState &state,const long time_us,const string reason)
  {
   if(state.inventory==0)
     {
      state.risk_flatten_pending=false;
      state.risk_flatten_reason="";
      return;
     }
   if(!ValidBook())
      return;
   const int side=(state.inventory>0 ? SIDE_SELL : SIDE_BUY);
   const long quantity=(long)MathAbs((double)state.inventory);
   const double price=(side==SIDE_SELL ? g_best_bid : g_best_ask);
   ApplyFill(state,time_us,side,quantity,price,false,reason);
   state.forced_flattens++;
   state.risk_flatten_pending=false;
   state.risk_flatten_reason="";
  }

bool FreshBookAt(const long time_us)
  {
   return ValidBook() && g_last_quote_us>0 &&
          time_us-g_last_quote_us<=MAX_QUOTE_AGE_US;
  }

void RequestRiskFlatten(EngineState &state,const long time_us,const string reason)
  {
   state.risk_flatten_pending=true;
   state.risk_flatten_reason=reason;
   ResetOrder(state.bid_order);
   ResetOrder(state.ask_order);
   if(FreshBookAt(time_us))
      ForceFlatten(state,time_us,reason);
  }

bool OldestLotExpired(const EngineState &state,const long time_us)
  {
   return state.lot_count>0 && state.lots[0].open_us>0 &&
          time_us>=state.lots[0].open_us+MAX_HOLD_US;
  }

bool RiskBlockBeforeTrade(EngineState &state,const long time_us)
  {
   bool blocked=false;
   if(FundingBlackout(time_us))
     {
      const long blackout_start=NextFundingTime(time_us)-FUNDING_BLACKOUT_LEAD_US;
      // At exact B maker matching is blocked, then the B-effective cancel is
      // applied after the skipped trade and before the risk-state assertion.
      if(time_us>blackout_start)
        {
         if(state.bid_order.active || state.ask_order.active ||
            state.bid_order.pending_action!=ACTION_NONE ||
            state.ask_order.pending_action!=ACTION_NONE)
            state.funding_live_after_blackout++;
         RequestRiskFlatten(state,time_us,"FUNDING_BLACKOUT");
        }
      blocked=true;
     }
   else if(OldestLotExpired(state,time_us))
     {
      RequestRiskFlatten(state,time_us,"MAX_HOLD_45M");
      blocked=true;
     }
   return blocked;
  }

void RiskAfterQuote(EngineState &state,const long time_us)
  {
   if(FundingBlackout(time_us))
     {
      if(state.bid_order.active || state.ask_order.active ||
         state.bid_order.pending_action!=ACTION_NONE ||
         state.ask_order.pending_action!=ACTION_NONE)
         state.funding_live_after_blackout++;
      RequestRiskFlatten(state,time_us,"FUNDING_BLACKOUT");
     }
   if(state.risk_flatten_pending && FreshBookAt(time_us))
      ForceFlatten(state,time_us,state.risk_flatten_reason);
  }

void HandleFundingDecisionAtEvent(EngineState &state,const long time_us)
  {
   const long funding_time=NextFundingTime(time_us);
   const long blackout_start=funding_time-FUNDING_BLACKOUT_LEAD_US;
   const long first_cancel=blackout_start-FUNDING_FIRST_CANCEL_LEAD_US;
   const long second_cancel=blackout_start-FUNDING_SECOND_CANCEL_LEAD_US;
   if(time_us==first_cancel &&
      (state.bid_order.active || state.bid_order.pending_action!=ACTION_NONE) &&
      !ScheduleCancelSide(state,time_us,true))
      state.action_interval_violations++;
   if(time_us==second_cancel &&
      (state.ask_order.active || state.ask_order.pending_action!=ACTION_NONE) &&
      !ScheduleCancelSide(state,time_us,false))
      state.action_interval_violations++;
  }

bool ScheduleCancelSide(EngineState &state,const long time_us,const bool bid_side)
  {
   if(bid_side)
      return ScheduleOrderAction(state,state.bid_order,time_us,ACTION_CANCEL,0.0);
   return ScheduleOrderAction(state,state.ask_order,time_us,ACTION_CANCEL,0.0);
  }

void ProcessFundingTimersBetween(EngineState &state,const long previous_us,
                                 const long current_us)
  {
   if(previous_us<=0 || current_us<=previous_us)
      return;
   const long base_funding=(previous_us/FUNDING_INTERVAL_US)*FUNDING_INTERVAL_US;
   for(int offset=0;offset<3;offset++)
     {
      const long funding_time=base_funding+(long)offset*FUNDING_INTERVAL_US;
      if(funding_time<=0)
         continue;
      const long blackout_start=funding_time-FUNDING_BLACKOUT_LEAD_US;
      const long first_cancel=blackout_start-FUNDING_FIRST_CANCEL_LEAD_US;
      const long second_cancel=blackout_start-FUNDING_SECOND_CANCEL_LEAD_US;
      if(first_cancel>previous_us && first_cancel<current_us)
        {
         ApplyPendingWithoutMarketEvent(state,first_cancel);
         if((state.bid_order.active || state.bid_order.pending_action!=ACTION_NONE) &&
            !ScheduleCancelSide(state,first_cancel,true))
            state.action_interval_violations++;
        }
      if(second_cancel>previous_us && second_cancel<current_us)
        {
         ApplyPendingWithoutMarketEvent(state,second_cancel);
         if((state.ask_order.active || state.ask_order.pending_action!=ACTION_NONE) &&
            !ScheduleCancelSide(state,second_cancel,false))
            state.action_interval_violations++;
        }
      if(blackout_start>previous_us && blackout_start<current_us)
        {
         ApplyPendingWithoutMarketEvent(state,blackout_start);
         if(state.bid_order.active || state.ask_order.active ||
            state.bid_order.pending_action!=ACTION_NONE ||
            state.ask_order.pending_action!=ACTION_NONE)
            state.funding_live_after_blackout++;
         RequestRiskFlatten(state,blackout_start,"FUNDING_BLACKOUT");
        }
     }
   // Any normal pending action that became effective between market events.
   ApplyPendingBeforeMarketEvent(state,current_us);
  }

void DesiredPrices(const EngineState &state,double &bid_target,double &ask_target)
  {
   bid_target=g_best_bid;
   ask_target=g_best_ask;
   if(state.candidate)
     {
      const double denominator=(double)(g_bid_size+g_ask_size);
      const double microprice=(denominator>0.0 ?
                               ((double)g_bid_size*g_best_ask+
                                (double)g_ask_size*g_best_bid)/denominator : MidPrice());
      bid_target=MathMin(g_best_bid,FloorToTick(microprice-PRICE_TICK));
      ask_target=MathMax(g_best_ask,CeilToTick(microprice+PRICE_TICK));
      if(state.inventory>SOFT_INVENTORY)
         bid_target-=PRICE_TICK;
      else if(state.inventory<-SOFT_INVENTORY)
         ask_target+=PRICE_TICK;
     }
  }

bool ActOnOrder(EngineState &state,VirtualOrder &order,const long time_us,
                const bool allowed,const double target)
  {
   if(order.pending_action!=ACTION_NONE)
      return false;
   if(!allowed)
     {
      if(order.active)
         return ScheduleOrderAction(state,order,time_us,ACTION_CANCEL,0.0);
      return false;
     }
   if(!order.active)
      return ScheduleOrderAction(state,order,time_us,ACTION_PLACE,target);
   if(MathAbs(order.price-target)>=2.0*PRICE_TICK-1e-9)
      return ScheduleOrderAction(state,order,time_us,ACTION_AMEND,target);
   return false;
  }

bool ActOnSide(EngineState &state,const long time_us,const bool bid_side,
               const double target)
  {
   const long venue_lot=(time_us<VENUE_LOT_CHANGE_US ?
                         VENUE_LOT_BEFORE : VENUE_LOT_AFTER);
   if(venue_lot<=0 || QUOTE_SIZE%venue_lot!=0)
     {
      state.venue_lot_violations++;
      return false;
     }
   if(bid_side)
      return ActOnOrder(state,state.bid_order,time_us,
                        state.inventory+QUOTE_SIZE<=HARD_INVENTORY,target);
   return ActOnOrder(state,state.ask_order,time_us,
                     state.inventory-QUOTE_SIZE>=-HARD_INVENTORY,target);
  }

void QuoteMaintenance(EngineState &state,const long time_us)
  {
   if(FundingRetirementQuiet(time_us) || state.risk_flatten_pending ||
      !ValidBook() || g_last_quote_us<=0 ||
      time_us-g_last_quote_us>=MAX_QUOTE_AGE_US ||
      !ActionReady(state,time_us))
      return;
   double bid_target=0.0,ask_target=0.0;
   DesiredPrices(state,bid_target,ask_target);
   bool acted=false;
   if(state.prefer_bid)
     {
      acted=ActOnSide(state,time_us,true,bid_target);
      if(!acted)
         acted=ActOnSide(state,time_us,false,ask_target);
     }
   else
     {
      acted=ActOnSide(state,time_us,false,ask_target);
      if(!acted)
         acted=ActOnSide(state,time_us,true,bid_target);
     }
   if(acted)
      state.prefer_bid=!state.prefer_bid;
  }

void ProcessTradeForEngine(EngineState &state,const long time_us,
                           const int aggressor_side,const double trade_price)
  {
   if(OldestLotExpired(state,time_us))
     {
      state.max_age_matched_after_expiry++;
      return;
     }
   if(state.bid_order.active && aggressor_side==SIDE_SELL)
     {
      if(trade_price<state.bid_order.price)
        {
         const double price=state.bid_order.price;
         if(state.bid_order.pending_action!=ACTION_NONE)
            state.pending_action_fill_races++;
         ResetOrder(state.bid_order);
         ApplyFill(state,time_us,SIDE_BUY,QUOTE_SIZE,price,true,"STRICT_TRADE_THROUGH");
        }
      else if(MathAbs(trade_price-state.bid_order.price)<1e-9)
        {
         state.exact_ignored++;
         g_exact_fill_attempts++;
        }
      else if(trade_price<=state.bid_order.price+PRICE_TICK)
        {
         state.touch_ignored++;
         g_touch_fill_attempts++;
        }
     }
   if(state.ask_order.active && aggressor_side==SIDE_BUY)
     {
      if(trade_price>state.ask_order.price)
        {
         const double price=state.ask_order.price;
         if(state.ask_order.pending_action!=ACTION_NONE)
            state.pending_action_fill_races++;
         ResetOrder(state.ask_order);
         ApplyFill(state,time_us,SIDE_SELL,QUOTE_SIZE,price,true,"STRICT_TRADE_THROUGH");
        }
      else if(MathAbs(trade_price-state.ask_order.price)<1e-9)
        {
         state.exact_ignored++;
         g_exact_fill_attempts++;
        }
      else if(trade_price>=state.ask_order.price-PRICE_TICK)
        {
         state.touch_ignored++;
         g_touch_fill_attempts++;
        }
     }
   if(MathAbs((double)state.inventory)>HARD_INVENTORY)
      state.hard_cap_violations++;
  }

bool ReadMagic(const int handle)
  {
   string value="";
   for(int i=0;i<8;i++)
     {
      const int byte=FileReadInteger(handle,CHAR_VALUE);
      if(i<7)
         value+=CharToString((uchar)byte);
     }
   return value=="XBTMM01";
  }

bool ProcessEventFile(const string utc_day,const datetime day_time,
                      const string event_file,const string event_sha256,
                      const string index_digest64,
                      const long index_bytes,const long index_records,
                      const long index_quotes,const long index_trades,
                      const long index_first_us,const long index_last_us)
  {
   const int handle=FileOpen(event_file,FILE_READ|FILE_BIN|FILE_COMMON);
   if(handle==INVALID_HANDLE)
     {
      PrintFormat("XBTMM_FILE_OPEN_FAIL day=%s file=%s error=%d",
                  utc_day,event_file,GetLastError());
      return false;
     }
   const ulong actual_bytes=FileSize(handle);
   if(!ReadMagic(handle))
     {
      PrintFormat("XBTMM_HEADER_FAIL day=%s field=magic",utc_day);
      FileClose(handle);
      return false;
     }
   const int schema=FileReadInteger(handle,INT_VALUE);
   const int record_size=FileReadInteger(handle,INT_VALUE);
   const long expected_records=FileReadLong(handle);
   const long first_time_us=FileReadLong(handle);
   const long last_time_us=FileReadLong(handle);
   const long expected_quotes=FileReadLong(handle);
   const long expected_trades=FileReadLong(handle);
   const ulong expected_digest64=(ulong)FileReadLong(handle);
   const string header_digest64=StringFormat("%016I64X",expected_digest64);
   if(schema!=2 || record_size!=58 || expected_records<=0 ||
      actual_bytes!=(ulong)index_bytes || expected_records!=index_records ||
      expected_quotes!=index_quotes || expected_trades!=index_trades ||
      first_time_us!=index_first_us || last_time_us!=index_last_us ||
      header_digest64!=index_digest64)
     {
      PrintFormat("XBTMM_HEADER_FAIL day=%s schema=%d record_size=%d bytes=%I64u index_bytes=%I64d records=%I64d index_records=%I64d quotes=%I64d index_quotes=%I64d trades=%I64d index_trades=%I64d header_digest=%s index_digest=%s",
                  utc_day,schema,record_size,actual_bytes,index_bytes,
                  expected_records,index_records,expected_quotes,index_quotes,
                  expected_trades,index_trades,header_digest64,index_digest64);
      FileClose(handle);
      return false;
     }
   const long day_start_us=(long)day_time*1000000;
   const long day_end_us=day_start_us+86400000000;
   if(first_time_us<day_start_us || last_time_us>=day_end_us ||
      (g_last_event_us>0 && first_time_us<g_last_event_us))
     {
      PrintFormat("XBTMM_DAY_BOUNDARY_FAIL day=%s first_us=%I64d last_us=%I64d previous_us=%I64d",
                  utc_day,first_time_us,last_time_us,g_last_event_us);
      FileClose(handle);
      return false;
     }

   long local_records=0;
   long local_quotes=0;
   long local_trades=0;
   ulong payload_digest64=FNV64_OFFSET;
   while(!FileIsEnding(handle) && local_records<expected_records)
     {
      const long time_us=FileReadLong(handle);
      const int kind=FileReadInteger(handle,CHAR_VALUE);
      const double bid=FileReadDouble(handle);
      const double ask=FileReadDouble(handle);
      const long bid_size=FileReadLong(handle);
      const long ask_size=FileReadLong(handle);
      const double trade_price=FileReadDouble(handle);
      const long trade_size=FileReadLong(handle);
      int trade_side=FileReadInteger(handle,CHAR_VALUE);
      if(trade_side>127)
         trade_side-=256;
      payload_digest64=UpdateEventDigest(payload_digest64,time_us,kind,bid,ask,
                                         bid_size,ask_size,trade_price,
                                         trade_size,trade_side);
      if(g_last_event_us>0 && time_us<g_last_event_us)
         g_timestamp_regressions++;

      ProcessFundingTimersBetween(g_candidate,g_last_event_us,time_us);
      ProcessFundingTimersBetween(g_null,g_last_event_us,time_us);
      ApplyPendingBeforeMarketEvent(g_candidate,time_us);
      ApplyPendingBeforeMarketEvent(g_null,time_us);

      // Quote-age expiry is a local pre-scheduled safety boundary.  It runs
      // before matching and is not an outbound cancel/QVR action.
      ExpireStaleOrders(g_candidate,time_us);
      ExpireStaleOrders(g_null,time_us);
      const bool candidate_risk_blocked=RiskBlockBeforeTrade(g_candidate,time_us);
      const bool null_risk_blocked=RiskBlockBeforeTrade(g_null,time_us);
      if(g_last_quote_us<=0 || time_us-g_last_quote_us>=MAX_QUOTE_AGE_US)
         g_stale_quote_pauses++;

      // Stream builder guarantees trade-before-quote at identical timestamp.
      if(kind==EVENT_TRADE)
        {
         g_trade_records++;
         local_trades++;
         if(trade_size>0 && trade_price>0.0)
           {
            if(!candidate_risk_blocked)
               ProcessTradeForEngine(g_candidate,time_us,trade_side,trade_price);
            if(!null_risk_blocked)
               ProcessTradeForEngine(g_null,time_us,trade_side,trade_price);
           }
        }
      ApplyPendingAfterTrade(g_candidate,time_us);
      ApplyPendingAfterTrade(g_null,time_us);

      if(kind==EVENT_QUOTE)
        {
         g_quote_records++;
         local_quotes++;
         g_best_bid=bid;
         g_best_ask=ask;
         g_bid_size=bid_size;
         g_ask_size=ask_size;
         g_last_quote_us=time_us;
         if(bid>=ask)
            g_crossed_records++;
         else
            g_last_mid=(bid+ask)*0.5;
        }

      RiskAfterQuote(g_candidate,time_us);
      RiskAfterQuote(g_null,time_us);
      HandleFundingDecisionAtEvent(g_candidate,time_us);
      HandleFundingDecisionAtEvent(g_null,time_us);
      if(!candidate_risk_blocked)
         QuoteMaintenance(g_candidate,time_us);
      if(!null_risk_blocked)
         QuoteMaintenance(g_null,time_us);
      UpdateEquity(g_candidate,MidPrice());
      UpdateEquity(g_null,MidPrice());
      g_records++;
      local_records++;
      if(g_first_event_us==0)
         g_first_event_us=time_us;
      g_last_event_us=time_us;
     }
   FileClose(handle);
   const bool day_ok=(local_records==expected_records &&
                      local_quotes==expected_quotes &&
                      local_trades==expected_trades &&
                      payload_digest64==expected_digest64);
   PrintFormat("XBTMM_DAY_SUMMARY hypothesis_id=%s day=%s file=%s event_sha256=%s event_digest64=%016I64X records=%I64d expected=%I64d quotes=%I64d expected_quotes=%I64d trades=%I64d expected_trades=%I64d first_us=%I64d last_us=%I64d day_gate_pass=%s economic_use_forbidden=%s",
               HYPOTHESIS_ID,utc_day,event_file,event_sha256,payload_digest64,local_records,
               expected_records,local_quotes,expected_quotes,local_trades,
               expected_trades,first_time_us,last_time_us,(string)day_ok,
               (string)InpEconomicUseForbidden);
   return day_ok;
  }

bool RunSimulation()
  {
   const int index_handle=FileOpen(InpIndexFile,
                                   FILE_READ|FILE_CSV|FILE_ANSI|FILE_COMMON,',');
   if(index_handle==INVALID_HANDLE)
     {
      PrintFormat("XBTMM_INDEX_OPEN_FAIL file=%s error=%d",InpIndexFile,GetLastError());
      return false;
     }

   const bool header_ok=(FileReadString(index_handle)=="utc_day" &&
                         FileReadString(index_handle)=="event_file_common" &&
                         FileReadString(index_handle)=="event_sha256" &&
                         FileReadString(index_handle)=="event_digest64" &&
                         FileReadString(index_handle)=="event_bytes" &&
                         FileReadString(index_handle)=="records" &&
                         FileReadString(index_handle)=="quote_records" &&
                         FileReadString(index_handle)=="trade_records" &&
                         FileReadString(index_handle)=="first_time_us" &&
                         FileReadString(index_handle)=="last_time_us" &&
                         FileReadString(index_handle)=="tick_size");
   if(!header_ok)
     {
      Print("XBTMM_INDEX_HEADER_FAIL");
      FileClose(index_handle);
      return false;
     }

   g_fill_handle=FileOpen(InpOutputPrefix+"_fills.csv",
                          FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',');
   if(g_fill_handle!=INVALID_HANDLE)
      FileWrite(g_fill_handle,"engine","time_us","type","side","quantity",
                "price","inventory","average_entry","realized_delta_xbt",
                "fee_xbt","cumulative_realized_xbt","reason");

   bool index_ok=true;
   datetime previous_day=0;
   while(!FileIsEnding(index_handle))
     {
      const string utc_day=FileReadString(index_handle);
      if(StringLen(utc_day)==0)
         break;
      const string event_file=FileReadString(index_handle);
      const string event_sha256=FileReadString(index_handle);
      const string event_digest64=FileReadString(index_handle);
      const long event_bytes=(long)StringToInteger(FileReadString(index_handle));
      const long expected_records=(long)StringToInteger(FileReadString(index_handle));
      const long expected_quotes=(long)StringToInteger(FileReadString(index_handle));
      const long expected_trades=(long)StringToInteger(FileReadString(index_handle));
      const long first_time_us=(long)StringToInteger(FileReadString(index_handle));
      const long last_time_us=(long)StringToInteger(FileReadString(index_handle));
      const double tick_size=StringToDouble(FileReadString(index_handle));
      if(StringLen(utc_day)!=8 || StringLen(event_sha256)!=64 ||
         StringLen(event_digest64)!=16 ||
         MathAbs(tick_size-PRICE_TICK)>1e-9)
        {
         PrintFormat("XBTMM_INDEX_ROW_FAIL day=%s tick=%.8f",utc_day,tick_size);
         index_ok=false;
         break;
        }
      const string day_text=StringSubstr(utc_day,0,4)+"."+
                            StringSubstr(utc_day,4,2)+"."+
                            StringSubstr(utc_day,6,2);
      const datetime day_time=StringToTime(day_text);
      if(day_time<=0 || (previous_day>0 && day_time!=previous_day+86400))
        {
         PrintFormat("XBTMM_INDEX_CONTINUITY_FAIL day=%s previous=%I64d current=%I64d",
                     utc_day,(long)previous_day,(long)day_time);
         index_ok=false;
         break;
        }
      if(!ProcessEventFile(utc_day,day_time,event_file,event_sha256,
                           event_digest64,event_bytes,
                           expected_records,expected_quotes,expected_trades,
                           first_time_us,last_time_us))
        {
         index_ok=false;
         break;
        }
      g_index_days++;
      g_index_expected_records+=expected_records;
      g_index_expected_quotes+=expected_quotes;
      g_index_expected_trades+=expected_trades;
      previous_day=day_time;
     }
   FileClose(index_handle);

   // Only the end of the complete indexed population forces liquidation.
   ForceFlatten(g_candidate,g_last_event_us,"END_OF_STREAM");
   ForceFlatten(g_null,g_last_event_us,"END_OF_STREAM");
   UpdateEquity(g_candidate,MidPrice());
   UpdateEquity(g_null,MidPrice());
   if(g_fill_handle!=INVALID_HANDLE)
     {
      FileFlush(g_fill_handle);
      FileClose(g_fill_handle);
      g_fill_handle=INVALID_HANDLE;
     }

   const bool source_ok=(index_ok && g_index_days>0 &&
                         g_records==g_index_expected_records &&
                         g_quote_records==g_index_expected_quotes &&
                         g_trade_records==g_index_expected_trades &&
                         g_timestamp_regressions==0 &&
                         g_first_event_us>0 && g_last_event_us>=g_first_event_us);
   PrintFormat("XBTMM_SOURCE_SUMMARY hypothesis_id=%s index=%s days=%I64d records=%I64d expected=%I64d quotes=%I64d expected_quotes=%I64d trades=%I64d expected_trades=%I64d first_us=%I64d last_us=%I64d regressions=%I64d crossed_records=%I64d source_gate_pass=%s economic_use_forbidden=%s",
               HYPOTHESIS_ID,InpIndexFile,g_index_days,g_records,
               g_index_expected_records,g_quote_records,g_index_expected_quotes,
               g_trade_records,g_index_expected_trades,g_first_event_us,
               g_last_event_us,g_timestamp_regressions,g_crossed_records,
               (string)source_ok,(string)InpEconomicUseForbidden);
   return source_ok;
  }

void PrintEngineSummary(const EngineState &state)
  {
   const double pf=(state.gross_loss_xbt>0.0 ?
                    state.gross_profit_xbt/state.gross_loss_xbt : 0.0);
   const bool engineering_ok=(state.action_interval_violations==0 &&
                              state.pending_action_latency_violations==0 &&
                              state.funding_live_after_blackout==0 &&
                              state.max_age_matched_after_expiry==0 &&
                              state.fifo_accounting_violations==0 &&
                              state.hard_cap_violations==0 &&
                              state.venue_lot_violations==0 &&
                              state.max_actions_per_hour<=3600);
   PrintFormat("XBTMM_ENGINE_SUMMARY hypothesis_id=%s engine=%s maker_fills=%I64d forced_flattens=%I64d closed_fragments=%I64d inventory=%I64d fifo_lots=%d realized_xbt=%.12f taker_fees_xbt=%.12f gross_profit_xbt=%.12f gross_loss_xbt=%.12f pf=%.8f max_dd_xbt_pct=%.8f collateral_usd_dd_pct=%.8f quote_actions=%I64d max_actions_hour=%I64d action_interval_violations=%I64d pending_latency_violations=%I64d funding_live_after_blackout=%I64d max_age_matched_after_expiry=%I64d fifo_violations=%I64d hard_cap_violations=%I64d venue_lot_violations=%I64d pending_fill_races=%I64d touch_ignored=%I64d exact_ignored=%I64d quote_expiries=%I64d engineering_gate_pass=%s economic_use_forbidden=%s",
               HYPOTHESIS_ID,state.id,state.maker_fills,state.forced_flattens,
               state.closed_fragments,state.inventory,state.lot_count,state.realized_xbt,
               state.taker_fees_xbt,state.gross_profit_xbt,state.gross_loss_xbt,pf,
               state.max_drawdown_xbt_pct,state.max_collateral_usd_drawdown_pct,
               state.quote_actions,state.max_actions_per_hour,
               state.action_interval_violations,state.pending_action_latency_violations,
               state.funding_live_after_blackout,state.max_age_matched_after_expiry,
               state.fifo_accounting_violations,state.hard_cap_violations,
               state.venue_lot_violations,state.pending_action_fill_races,
               state.touch_ignored,state.exact_ignored,
               state.quote_expiries,(string)engineering_ok,
               (string)InpEconomicUseForbidden);
  }

bool ReadSeriesInteger(const ENUM_TIMEFRAMES timeframe,
                       const ENUM_SERIES_INFO_INTEGER property,long &value)
  {
   value=0;
   ResetLastError();
   if(!SeriesInfoInteger(_Symbol,timeframe,property,value))
      return false;
   return GetLastError()==0;
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
      return false;
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
      return false;
   return true;
  }

int OnInit()
  {
   if(_Symbol!=EXPECTED_SYMBOL || _Period!=PERIOD_H1 || !InpResearchAutoMode)
     {
      PrintFormat("XBTMM_IDENTITY_FAIL symbol=%s period=%d",_Symbol,(int)_Period);
      return INIT_FAILED;
     }
   if(!EmitD0SeriesProof())
     {
      Print("XBTMM_D0_SERIES_PROOF_FAIL");
      return INIT_FAILED;
     }
   InitEngine(g_candidate,"candidate",true);
   InitEngine(g_null,"matched_null",false);
   const bool ok=RunSimulation();
   g_simulation_done=true;
   PrintEngineSummary(g_candidate);
   PrintEngineSummary(g_null);
   return ok ? INIT_SUCCEEDED : INIT_FAILED;
  }

void OnTick()
  {
   // The hash-bound external event stream is processed once in OnInit.
  }

double OnTester()
  {
   return g_candidate.realized_xbt;
  }

void OnDeinit(const int reason)
  {
   if(g_fill_handle!=INVALID_HANDLE)
      FileClose(g_fill_handle);
   PrintFormat("XBTMM_DEINIT hypothesis_id=%s reason=%d simulation_done=%s index_days=%I64d records=%I64d stale_pauses=%I64d touch_attempts=%I64d exact_attempts=%I64d",
               HYPOTHESIS_ID,reason,(string)g_simulation_done,g_index_days,
               g_records,g_stale_quote_pauses,g_touch_fill_attempts,
               g_exact_fill_attempts);
  }
//+------------------------------------------------------------------+
