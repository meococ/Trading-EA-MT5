//+------------------------------------------------------------------+
//| LSW_Risk.mqh                                                     |
//| Stop geometry, position sizing and the safety locks.             |
//|                                                                  |
//| SIZING DOCTRINE (CONTRACT.md §7):                                |
//|  - Volume is derived from the ACTUAL stop distance, never from a  |
//|    fixed lot or a points constant.                                |
//|  - Money-per-lot is computed twice, by two independent routes,    |
//|    and the MORE CONSERVATIVE (larger) figure wins:                |
//|      a) (risk_distance / TICK_SIZE) * TICK_VALUE_LOSS             |
//|      b) |OrderCalcProfit(type, sym, 1.0, entry, sl)|              |
//|    Both are already denominated in the DEPOSIT currency, so the   |
//|    account-currency conversion is the terminal's, not a           |
//|    hand-rolled cross rate.                                        |
//|  - If both routes fail the trade is rejected. Nothing is guessed.  |
//+------------------------------------------------------------------+
#ifndef LSW_RISK_MQH
#define LSW_RISK_MQH

#include "LSW_Types.mqh"

double LswFloorToTick(const double price,const double tick_size)
  {
   return(MathFloor(price/tick_size+1e-10)*tick_size);
  }

double LswCeilToTick(const double price,const double tick_size)
  {
   return(MathCeil(price/tick_size-1e-10)*tick_size);
  }

//--- Round DOWN to a broker-legal volume. Returns 0.0 when nothing is legal.
double LswNormalizeVolumeDown(const string symbol,const double volume)
  {
   const double vmin=SymbolInfoDouble(symbol,SYMBOL_VOLUME_MIN);
   const double vmax=SymbolInfoDouble(symbol,SYMBOL_VOLUME_MAX);
   const double step=SymbolInfoDouble(symbol,SYMBOL_VOLUME_STEP);
   if(!LswFinite(vmin) || !LswFinite(vmax) || !LswFinite(step) ||
      vmin<=0.0 || vmax<vmin || step<=0.0 || volume<vmin)
      return(0.0);
   const double bounded=MathMin(volume,vmax);
   const double units=MathFloor((bounded-vmin+1e-12)/step);
   const double result=NormalizeDouble(vmin+units*step,LswVolumeDigits(step));
   if(result<vmin || result>vmax)
      return(0.0);
   return(result);
  }

//--- Loss in deposit currency for one lot over `risk_distance` price units.
bool LswMoneyRiskPerLot(const string symbol,const int direction,const double entry,
                        const double sl,const double risk_distance,double &money)
  {
   money=0.0;
   double by_tick=0.0;
   const double tick_size=SymbolInfoDouble(symbol,SYMBOL_TRADE_TICK_SIZE);
   double tick_value=SymbolInfoDouble(symbol,SYMBOL_TRADE_TICK_VALUE_LOSS);
   if(!LswFinite(tick_value) || tick_value<=0.0)
      tick_value=SymbolInfoDouble(symbol,SYMBOL_TRADE_TICK_VALUE);
   if(LswFinite(tick_size) && tick_size>0.0 && LswFinite(tick_value) && tick_value>0.0)
      by_tick=(risk_distance/tick_size)*tick_value;

   double by_calc=0.0;
   const ENUM_ORDER_TYPE order_type=(direction>0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL);
   double raw=0.0;
   if(OrderCalcProfit(order_type,symbol,1.0,entry,sl,raw) && LswFinite(raw) && raw<0.0)
      by_calc=MathAbs(raw);

   money=MathMax(by_tick,by_calc);
   return(LswFinite(money) && money>0.0);
  }

//--- Build the full order plan from a detected sweep.
//--- entry is the price the market order will actually transact at:
//--- ask for a long, bid for a short.
bool LswBuildPlan(const string symbol,const LswSweep &sweep,const LswConfig &cfg,
                  const double ask,const double bid,LswPlan &plan)
  {
   ZeroMemory(plan);
   plan.reject="NONE";

   const double point=SymbolInfoDouble(symbol,SYMBOL_POINT);
   const double tick_size=SymbolInfoDouble(symbol,SYMBOL_TRADE_TICK_SIZE);
   if(!sweep.valid || sweep.direction==LSW_DIR_NONE ||
      !LswFinite(ask) || !LswFinite(bid) || ask<=bid ||
      !LswFinite(point) || point<=0.0 || !LswFinite(tick_size) || tick_size<=0.0 ||
      !LswFinite(sweep.atr) || sweep.atr<=0.0)
     {
      plan.reject="BAD_INPUT";
      return(false);
     }

   const int direction=sweep.direction;
   const double entry=(direction>0 ? ask : bid);
   const double spread=ask-bid;

   //--- Structural stop: beyond the swept extreme, padded by ATR.
   double sl_raw=0.0;
   if(direction>0)
      sl_raw=MathMin(sweep.extreme,entry)-cfg.sl_buffer_atr*sweep.atr;
   else
      sl_raw=MathMax(sweep.extreme,entry)+cfg.sl_buffer_atr*sweep.atr;

   double risk_distance=(direction>0 ? entry-sl_raw : sl_raw-entry);
   // Spread floor. Bounded from above by the spread filter upstream
   // (spread <= max_spread_atr * atr), so this cannot explode the stop.
   risk_distance=MathMax(risk_distance,cfg.min_sl_spread_mult*spread);
   if(!LswFinite(risk_distance) || risk_distance<=0.0)
     {
      plan.reject="BAD_DISTANCE";
      return(false);
     }

   //--- Round SL and TP AWAY from entry, then re-derive the true risk distance
   //--- from the rounded stop so sizing matches what the broker will execute.
   const double sl_adj=entry-direction*risk_distance;
   const double sl=(direction>0 ? LswFloorToTick(sl_adj,tick_size)
                    : LswCeilToTick(sl_adj,tick_size));
   risk_distance=MathAbs(entry-sl);
   if(risk_distance<=0.0)
     {
      plan.reject="BAD_DISTANCE";
      return(false);
     }
   const double tp_raw=entry+direction*cfg.tp_r*risk_distance;
   const double tp=(direction>0 ? LswCeilToTick(tp_raw,tick_size)
                    : LswFloorToTick(tp_raw,tick_size));

   //--- Broker geometry: stops level and freeze level.
   const long stops_level=SymbolInfoInteger(symbol,SYMBOL_TRADE_STOPS_LEVEL);
   const long freeze_level=SymbolInfoInteger(symbol,SYMBOL_TRADE_FREEZE_LEVEL);
   // Explicit long comparison: MathMax is a double overload and would round-trip
   // these through a floating type for no reason.
   long broker_level=(stops_level>freeze_level ? stops_level : freeze_level);
   if(broker_level<0)
      broker_level=0;
   const double min_dist=(double)broker_level*point;
   if(MathAbs(entry-sl)<min_dist || MathAbs(tp-entry)<min_dist)
     {
      plan.reject="STOPS_LEVEL";
      return(false);
     }
   if((direction>0 && (sl>=entry || tp<=entry)) ||
      (direction<0 && (sl<=entry || tp>=entry)))
     {
      plan.reject="BAD_GEOMETRY";
      return(false);
     }

   //--- Sizing.
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

   //--- Margin: never commit more than half the free margin to one scalp.
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
   plan.tp=tp;
   plan.volume=volume;
   plan.risk_distance=risk_distance;
   plan.money_per_lot=money_per_lot;
   plan.reject="";
   return(true);
  }

//--- Refresh account-derived locks. Called every tick; cheap and idempotent.
void LswRiskRefresh(LswRiskState &st,const datetime server_now,const LswConfig &cfg)
  {
   const double equity=AccountInfoDouble(ACCOUNT_EQUITY);
   if(!LswFinite(equity) || equity<=0.0)
      return;
   const int day=LswDayKey(server_now);
   if(st.day_key!=day)
     {
      st.day_key=day;
      st.day_start_equity=equity;
      st.day_locked=false;
      st.streak_locked=false;
      st.daily_entries=0;
      st.consecutive_losses=0;
     }
   if(st.peak_equity<=0.0 || equity>st.peak_equity)
      st.peak_equity=equity;
   if(cfg.max_daily_loss_pct>0.0 && st.day_start_equity>0.0 &&
      equity<=st.day_start_equity*(1.0-cfg.max_daily_loss_pct/100.0))
      st.day_locked=true;
   if(cfg.max_account_dd_pct>0.0 && st.peak_equity>0.0 &&
      equity<=st.peak_equity*(1.0-cfg.max_account_dd_pct/100.0))
      st.dd_locked=true;
  }

//--- Fed from OnTradeTransaction when one of our positions closes.
void LswRegisterClosedDeal(LswRiskState &st,const LswConfig &cfg,const double net_profit)
  {
   if(net_profit<0.0)
     {
      st.consecutive_losses++;
      if(cfg.max_consecutive_losses>0 &&
         st.consecutive_losses>=cfg.max_consecutive_losses)
         st.streak_locked=true;
     }
   else
      st.consecutive_losses=0;
  }

//--- True when no new entry may be opened. Increments exactly one counter.
bool LswRiskBlocked(const LswRiskState &st,const LswConfig &cfg,LswCounters &cnt)
  {
   if(st.dd_locked)
     {
      cnt.filt_dd_lock++;
      return(true);
     }
   if(st.day_locked)
     {
      cnt.filt_daily_lock++;
      return(true);
     }
   if(st.streak_locked)
     {
      cnt.filt_streak_lock++;
      return(true);
     }
   if(cfg.max_trades_per_day>0 && st.daily_entries>=cfg.max_trades_per_day)
     {
      cnt.filt_max_trades++;
      return(true);
     }
   return(false);
  }

#endif
