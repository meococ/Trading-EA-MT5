//+------------------------------------------------------------------+
//| EA_XBTMMTradeThroughV1.mq5                                       |
//| HYP-XBT-MM-TRADETHROUGH-001 - strict virtual exchange simulator  |
//+------------------------------------------------------------------+
#property copyright "AlphaFactory research"
#property version   "1.00"
#property strict
#property description "BitMEX XBTUSD passive trade-through market-making simulator"

input bool   InpResearchAutoMode=true;
input bool   InpEconomicUseForbidden=true;
input string InpEventFile="xbtmm\\events\\20180101.xbtmm";
input string InpOutputPrefix="XBTMM001_20180101";

const string HYPOTHESIS_ID="HYP-XBT-MM-TRADETHROUGH-001";
const string EXPECTED_SYMBOL="EURUSD";
const double PRICE_TICK=0.5;
const long   QUOTE_SIZE=20;
const long   SOFT_INVENTORY=40;
const long   HARD_INVENTORY=80;
const long   ORDER_LATENCY_US=400000;
const long   ACTION_INTERVAL_US=2000000;
const long   MAX_QUOTE_AGE_US=2000000;
const long   MAX_HOLD_US=2700000000;
const double TAKER_FEE_RATE=0.00075;
const double STARTING_EQUITY_XBT=1.0;
const int    EVENT_QUOTE=1;
const int    EVENT_TRADE=2;
const int    SIDE_BUY=1;
const int    SIDE_SELL=-1;

struct VirtualOrder
  {
   bool   active;
   double price;
   long   decision_us;
   long   live_us;
   long   expiry_us;
  };

struct EngineState
  {
   string id;
   bool   candidate;
   VirtualOrder bid_order;
   VirtualOrder ask_order;
   long   inventory;
   double average_entry;
   long   position_open_us;
   double realized_xbt;
   double taker_fees_xbt;
   double gross_profit_xbt;
   double gross_loss_xbt;
   double peak_equity_usd;
   double max_drawdown_pct;
   long   maker_fills;
   long   forced_flattens;
   long   closed_fragments;
   long   quote_actions;
   long   action_interval_violations;
   long   hard_cap_violations;
   long   touch_ignored;
   long   exact_ignored;
   long   quote_expiries;
   long   last_action_us;
   long   action_hour_key;
   long   actions_this_hour;
   long   max_actions_per_hour;
   bool   prefer_bid;
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

void ResetOrder(VirtualOrder &order)
  {
   order.active=false;
   order.price=0.0;
   order.decision_us=0;
   order.live_us=0;
   order.expiry_us=0;
  }

void InitEngine(EngineState &state,const string id,const bool candidate)
  {
   state.id=id;
   state.candidate=candidate;
   ResetOrder(state.bid_order);
   ResetOrder(state.ask_order);
   state.inventory=0;
   state.average_entry=0.0;
   state.position_open_us=0;
   state.realized_xbt=0.0;
   state.taker_fees_xbt=0.0;
   state.gross_profit_xbt=0.0;
   state.gross_loss_xbt=0.0;
   state.peak_equity_usd=0.0;
   state.max_drawdown_pct=0.0;
   state.maker_fills=0;
   state.forced_flattens=0;
   state.closed_fragments=0;
   state.quote_actions=0;
   state.action_interval_violations=0;
   state.hard_cap_violations=0;
   state.touch_ignored=0;
   state.exact_ignored=0;
   state.quote_expiries=0;
   state.last_action_us=0;
   state.action_hour_key=-1;
   state.actions_this_hour=0;
   state.max_actions_per_hour=0;
   state.prefer_bid=true;
  }

double FloorToTick(const double value)
  {
   return MathFloor(value/PRICE_TICK+1e-12)*PRICE_TICK;
  }

double CeilToTick(const double value)
  {
   return MathCeil(value/PRICE_TICK-1e-12)*PRICE_TICK;
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
   const double equity_usd=equity_xbt*mark;
   if(state.peak_equity_usd<=0.0 || equity_usd>state.peak_equity_usd)
      state.peak_equity_usd=equity_usd;
   if(state.peak_equity_usd>0.0)
     {
      const double drawdown=100.0*(state.peak_equity_usd-equity_usd)/state.peak_equity_usd;
      if(drawdown>state.max_drawdown_pct)
         state.max_drawdown_pct=drawdown;
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

void ApplyFill(EngineState &state,const long time_us,const int side,
               const long quantity,const double price,const bool passive,
               const string reason)
  {
   if(quantity<=0 || price<=0.0 || (side!=SIDE_BUY && side!=SIDE_SELL))
      return;
   const long signed_quantity=(long)side*quantity;
   const long before=state.inventory;
   double realized_delta=0.0;

   if(before==0 || (before>0 && side>0) || (before<0 && side<0))
     {
      const long before_abs=(long)MathAbs((double)before);
      const long after_abs=before_abs+quantity;
      const double reciprocal=(before_abs>0 && state.average_entry>0.0 ?
                               (double)before_abs/state.average_entry : 0.0)+
                              (double)quantity/price;
      state.average_entry=(reciprocal>0.0 ? (double)after_abs/reciprocal : price);
      state.inventory=before+signed_quantity;
      if(before==0)
         state.position_open_us=time_us;
     }
   else
     {
      const long close_quantity=(long)MathMin((double)MathAbs((double)before),(double)quantity);
      const int position_sign=(before>0 ? 1 : -1);
      realized_delta=(double)(position_sign*close_quantity)*
                     (1.0/state.average_entry-1.0/price);
      state.inventory=before+signed_quantity;
      state.closed_fragments++;
      if(state.inventory==0)
        {
         state.average_entry=0.0;
         state.position_open_us=0;
        }
      else if((before>0 && state.inventory<0) || (before<0 && state.inventory>0))
        {
         state.average_entry=price;
         state.position_open_us=time_us;
        }
     }

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

bool CancelOne(EngineState &state,const long time_us)
  {
   if(!ActionReady(state,time_us))
      return false;
   if(state.bid_order.active)
     {
      ResetOrder(state.bid_order);
      CountQuoteAction(state,time_us);
      return true;
     }
   if(state.ask_order.active)
     {
      ResetOrder(state.ask_order);
      CountQuoteAction(state,time_us);
      return true;
     }
   return false;
  }

void ExpireStaleOrders(EngineState &state,const long time_us)
  {
   if(state.bid_order.active && time_us>=state.bid_order.expiry_us)
     {
      ResetOrder(state.bid_order);
      state.quote_expiries++;
     }
   if(state.ask_order.active && time_us>=state.ask_order.expiry_us)
     {
      ResetOrder(state.ask_order);
      state.quote_expiries++;
     }
  }

bool FundingBlackout(const long time_us)
  {
   const long second_of_day=(time_us/1000000)%86400;
   const long funding[3]={0,28800,57600};
   for(int i=0;i<3;i++)
     {
      long start=funding[i]-900;
      if(start<0)
         start+=86400;
      if(funding[i]==0)
        {
         if(second_of_day>=start)
            return true;
        }
      else if(second_of_day>=start && second_of_day<funding[i])
         return true;
     }
   return false;
  }

void ForceFlatten(EngineState &state,const long time_us,const string reason)
  {
   if(state.inventory==0 || !ValidBook())
      return;
   const int side=(state.inventory>0 ? SIDE_SELL : SIDE_BUY);
   const long quantity=(long)MathAbs((double)state.inventory);
   const double price=(side==SIDE_SELL ? g_best_bid : g_best_ask);
   ApplyFill(state,time_us,side,quantity,price,false,reason);
   state.forced_flattens++;
  }

void RiskMaintenance(EngineState &state,const long time_us)
  {
   const bool stale=(g_last_quote_us<=0 || time_us-g_last_quote_us>MAX_QUOTE_AGE_US);
   const bool blocked=FundingBlackout(time_us) || stale || !ValidBook();
   if(stale)
      g_stale_quote_pauses++;
   if(blocked)
     {
      CancelOne(state,time_us);
      if(!state.bid_order.active && !state.ask_order.active && FundingBlackout(time_us))
         ForceFlatten(state,time_us,"FUNDING_BLACKOUT");
      return;
     }
   if(state.inventory!=0 && state.position_open_us>0 &&
      time_us-state.position_open_us>=MAX_HOLD_US)
     {
      CancelOne(state,time_us);
      if(!state.bid_order.active && !state.ask_order.active)
         ForceFlatten(state,time_us,"MAX_HOLD_45M");
     }
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
   if(!allowed)
     {
      if(order.active)
        {
         ResetOrder(order);
         CountQuoteAction(state,time_us);
         return true;
        }
      return false;
     }
   if(!order.active || MathAbs(order.price-target)>=2.0*PRICE_TICK-1e-9)
     {
      order.active=true;
      order.price=target;
      order.decision_us=time_us;
      order.live_us=time_us+ORDER_LATENCY_US;
      order.expiry_us=g_last_quote_us+MAX_QUOTE_AGE_US;
      CountQuoteAction(state,time_us);
      return true;
     }
   return false;
  }

bool ActOnSide(EngineState &state,const long time_us,const bool bid_side,
               const double target)
  {
   if(bid_side)
      return ActOnOrder(state,state.bid_order,time_us,
                        state.inventory+QUOTE_SIZE<=HARD_INVENTORY,target);
   return ActOnOrder(state,state.ask_order,time_us,
                     state.inventory-QUOTE_SIZE>=-HARD_INVENTORY,target);
  }

void QuoteMaintenance(EngineState &state,const long time_us)
  {
   if(FundingBlackout(time_us) || !ValidBook() ||
      g_last_quote_us<=0 || time_us-g_last_quote_us>MAX_QUOTE_AGE_US ||
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
   if(state.bid_order.active && time_us>=state.bid_order.live_us && aggressor_side==SIDE_SELL)
     {
      if(trade_price<state.bid_order.price)
        {
         const double price=state.bid_order.price;
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
   if(state.ask_order.active && time_us>=state.ask_order.live_us && aggressor_side==SIDE_BUY)
     {
      if(trade_price>state.ask_order.price)
        {
         const double price=state.ask_order.price;
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

bool RunSimulation()
  {
   const int handle=FileOpen(InpEventFile,FILE_READ|FILE_BIN|FILE_COMMON);
   if(handle==INVALID_HANDLE)
     {
      PrintFormat("XBTMM_FILE_OPEN_FAIL file=%s error=%d",InpEventFile,GetLastError());
      return false;
     }
   if(!ReadMagic(handle))
     {
      Print("XBTMM_HEADER_FAIL magic");
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
   if(schema!=1 || record_size!=58 || expected_records<=0)
     {
      PrintFormat("XBTMM_HEADER_FAIL schema=%d record_size=%d records=%I64d",
                  schema,record_size,expected_records);
      FileClose(handle);
      return false;
     }

   g_fill_handle=FileOpen(InpOutputPrefix+"_fills.csv",
                          FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',');
   if(g_fill_handle!=INVALID_HANDLE)
      FileWrite(g_fill_handle,"engine","time_us","type","side","quantity",
                "price","inventory","average_entry","realized_delta_xbt",
                "fee_xbt","cumulative_realized_xbt","reason");

   while(!FileIsEnding(handle) && g_records<expected_records)
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
      if(g_last_event_us>0 && time_us<g_last_event_us)
         g_timestamp_regressions++;

      // Quote-age expiry is a local pre-scheduled safety boundary.  It runs
      // before matching and is not an outbound cancel/QVR action.
      ExpireStaleOrders(g_candidate,time_us);
      ExpireStaleOrders(g_null,time_us);

      // Stream builder guarantees trade-before-quote at identical timestamp.
      if(kind==EVENT_TRADE)
        {
         g_trade_records++;
         if(trade_size>0 && trade_price>0.0)
           {
            ProcessTradeForEngine(g_candidate,time_us,trade_side,trade_price);
            ProcessTradeForEngine(g_null,time_us,trade_side,trade_price);
           }
        }
      else if(kind==EVENT_QUOTE)
        {
         g_quote_records++;
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

      RiskMaintenance(g_candidate,time_us);
      RiskMaintenance(g_null,time_us);
      QuoteMaintenance(g_candidate,time_us);
      QuoteMaintenance(g_null,time_us);
      UpdateEquity(g_candidate,MidPrice());
      UpdateEquity(g_null,MidPrice());
      g_records++;
      g_last_event_us=time_us;
     }
   FileClose(handle);

   // Design end is a forced taker liquidation, never a favorable mark-only exit.
   ForceFlatten(g_candidate,g_last_event_us,"END_OF_STREAM");
   ForceFlatten(g_null,g_last_event_us,"END_OF_STREAM");
   if(g_fill_handle!=INVALID_HANDLE)
     {
      FileFlush(g_fill_handle);
      FileClose(g_fill_handle);
      g_fill_handle=INVALID_HANDLE;
     }

   const bool source_ok=(g_records==expected_records &&
                         g_quote_records==expected_quotes &&
                         g_trade_records==expected_trades &&
                         g_timestamp_regressions==0 && g_crossed_records==0 &&
                         first_time_us>0 && last_time_us>=first_time_us);
   PrintFormat("XBTMM_SOURCE_SUMMARY hypothesis_id=%s file=%s records=%I64d expected=%I64d quotes=%I64d expected_quotes=%I64d trades=%I64d expected_trades=%I64d first_us=%I64d last_us=%I64d regressions=%I64d crossed=%I64d source_gate_pass=%s economic_use_forbidden=%s",
               HYPOTHESIS_ID,InpEventFile,g_records,expected_records,g_quote_records,
               expected_quotes,g_trade_records,expected_trades,first_time_us,last_time_us,
               g_timestamp_regressions,g_crossed_records,(string)source_ok,
               (string)InpEconomicUseForbidden);
   return source_ok;
  }

void PrintEngineSummary(const EngineState &state)
  {
   const double pf=(state.gross_loss_xbt>0.0 ?
                    state.gross_profit_xbt/state.gross_loss_xbt : 0.0);
   PrintFormat("XBTMM_ENGINE_SUMMARY hypothesis_id=%s engine=%s maker_fills=%I64d forced_flattens=%I64d closed_fragments=%I64d inventory=%I64d realized_xbt=%.12f taker_fees_xbt=%.12f gross_profit_xbt=%.12f gross_loss_xbt=%.12f pf=%.8f max_dd_usd_pct=%.8f quote_actions=%I64d max_actions_hour=%I64d action_interval_violations=%I64d hard_cap_violations=%I64d touch_ignored=%I64d exact_ignored=%I64d quote_expiries=%I64d economic_use_forbidden=%s",
               HYPOTHESIS_ID,state.id,state.maker_fills,state.forced_flattens,
               state.closed_fragments,state.inventory,state.realized_xbt,
               state.taker_fees_xbt,state.gross_profit_xbt,state.gross_loss_xbt,pf,
               state.max_drawdown_pct,state.quote_actions,state.max_actions_per_hour,
               state.action_interval_violations,state.hard_cap_violations,
               state.touch_ignored,state.exact_ignored,state.quote_expiries,
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
   PrintFormat("XBTMM_DEINIT hypothesis_id=%s reason=%d simulation_done=%s records=%I64d stale_pauses=%I64d touch_attempts=%I64d exact_attempts=%I64d",
               HYPOTHESIS_ID,reason,(string)g_simulation_done,g_records,
               g_stale_quote_pauses,g_touch_fill_attempts,g_exact_fill_attempts);
  }
//+------------------------------------------------------------------+
