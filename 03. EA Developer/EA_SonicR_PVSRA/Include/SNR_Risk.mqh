#ifndef SNR_RISK_MQH
#define SNR_RISK_MQH

#include "SNR_Types.mqh"

int SnrVolumeDigits(const double step)
  {
   int digits=0;
   double scaled=step;
   while(digits<8 && MathAbs(scaled-MathRound(scaled))>1e-9)
     {
      scaled*=10.0;
      digits++;
     }
   return(digits);
  }

double SnrNormalizeVolumeDown(const string symbol,const double volume)
  {
   const double vmin=SymbolInfoDouble(symbol,SYMBOL_VOLUME_MIN);
   const double vmax=SymbolInfoDouble(symbol,SYMBOL_VOLUME_MAX);
   const double step=SymbolInfoDouble(symbol,SYMBOL_VOLUME_STEP);
   if(!SnrFinite(vmin) || !SnrFinite(vmax) || !SnrFinite(step) ||
      vmin<=0.0 || vmax<vmin || step<=0.0 || volume<vmin)
      return(0.0);
   const double bounded=MathMin(volume,vmax);
   const double units=MathFloor((bounded-vmin+1e-12)/step);
   return(NormalizeDouble(vmin+units*step,SnrVolumeDigits(step)));
  }

double SnrFloorToTick(const double price,const double tick_size)
  {
   return(MathFloor(price/tick_size+1e-10)*tick_size);
  }

double SnrCeilToTick(const double price,const double tick_size)
  {
   return(MathCeil(price/tick_size-1e-10)*tick_size);
  }

int SnrDayKey(const datetime stamp)
  {
   MqlDateTime p;
   TimeToStruct(stamp,p);
   return(p.year*10000+p.mon*100+p.day);
  }

void SnrRiskRefresh(SnrRiskState &state,const datetime server_now,
                    const double max_daily_loss_pct,const double max_dd_pct)
  {
   const double equity=AccountInfoDouble(ACCOUNT_EQUITY);
   const int day=SnrDayKey(server_now);
   if(state.day_key!=day)
     {
      state.day_key=day;
      state.day_start_equity=equity;
      state.day_locked=false;
      state.daily_entries=0;
     }
   if(state.peak_equity<=0.0 || equity>state.peak_equity)
      state.peak_equity=equity;
   if(state.day_start_equity>0.0 &&
      equity<=state.day_start_equity*(1.0-max_daily_loss_pct/100.0))
      state.day_locked=true;
   if(state.peak_equity>0.0 &&
      equity<=state.peak_equity*(1.0-max_dd_pct/100.0))
      state.dd_locked=true;
  }

bool SnrRiskEntryBlocked(const SnrRiskState &state,const int max_trades_per_day)
  {
   return(state.day_locked || state.dd_locked ||
          (max_trades_per_day>0 && state.daily_entries>=max_trades_per_day));
  }

bool SnrPlanTrade(const string symbol,const int direction,const double entry,
                  const double structural_sl,const double atr,
                  const double sl_buffer_atr,const double min_sl_atr,
                  const double max_sl_atr,const double min_sl_spread_mult,
                  const double target_r,const double risk_percent,
                  const double ask,const double bid,SnrRiskPlan &plan)
  {
   ZeroMemory(plan);
   const double point=SymbolInfoDouble(symbol,SYMBOL_POINT);
   const double tick_size=SymbolInfoDouble(symbol,SYMBOL_TRADE_TICK_SIZE);
   if(!SnrFinite(entry) || !SnrFinite(structural_sl) || !SnrFinite(atr) ||
      !SnrFinite(ask) || !SnrFinite(bid) || atr<=0.0 || point<=0.0 ||
      tick_size<=0.0 || direction==SNR_DIR_NONE || ask<=bid)
      return(false);

   double raw_sl=structural_sl;
   if(direction>0)
      raw_sl=MathMin(structural_sl,entry)-sl_buffer_atr*atr;
   else
      raw_sl=MathMax(structural_sl,entry)+sl_buffer_atr*atr;

   double risk_distance=(direction>0 ? entry-raw_sl : raw_sl-entry);
   const double spread=ask-bid;
   const double min_from_spread=min_sl_spread_mult*spread;
   const double min_from_atr=min_sl_atr*atr;
   risk_distance=MathMax(risk_distance,MathMax(min_from_spread,min_from_atr));
   if(max_sl_atr>0.0 && risk_distance>max_sl_atr*atr)
      return(false);
   if(!SnrFinite(risk_distance) || risk_distance<=0.0)
      return(false);

   const double sl_raw=entry-direction*risk_distance;
   const double tp_raw=entry+direction*target_r*risk_distance;
   const double sl=(direction>0 ? SnrFloorToTick(sl_raw,tick_size) : SnrCeilToTick(sl_raw,tick_size));
   const double tp=(direction>0 ? SnrCeilToTick(tp_raw,tick_size) : SnrFloorToTick(tp_raw,tick_size));
   const double min_dist=(double)MathMax(MathMax(SymbolInfoInteger(symbol,SYMBOL_TRADE_STOPS_LEVEL),
                                                 SymbolInfoInteger(symbol,SYMBOL_TRADE_FREEZE_LEVEL)),0)*point;
   if(MathAbs(entry-sl)<min_dist || (target_r>0.0 && MathAbs(tp-entry)<min_dist))
      return(false);
   if((direction>0 && (sl>=entry || tp<=entry)) ||
      (direction<0 && (sl<=entry || tp>=entry)))
      return(false);

   const ENUM_ORDER_TYPE order_type=(direction>0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL);
   double one_lot_loss=0.0;
   if(!OrderCalcProfit(order_type,symbol,1.0,entry,sl,one_lot_loss) ||
      !SnrFinite(one_lot_loss) || one_lot_loss>=0.0)
      return(false);
   const double equity=AccountInfoDouble(ACCOUNT_EQUITY);
   if(!SnrFinite(equity) || equity<=0.0 || risk_percent<=0.0)
      return(false);
   double volume=SnrNormalizeVolumeDown(symbol,equity*(risk_percent/100.0)/MathAbs(one_lot_loss));
   if(volume<=0.0)
      return(false);
   const double contract=SymbolInfoDouble(symbol,SYMBOL_TRADE_CONTRACT_SIZE);
   const double hist_px=MathMax(entry,MathMax(bid,ask));
   if(!SnrFinite(contract) || !SnrFinite(hist_px) || contract<=0.0 || hist_px<=0.0)
      return(false);
   const double max_volume=SnrNormalizeVolumeDown(symbol,equity*0.50/(contract*hist_px));
   if(max_volume<=0.0)
      return(false);
   if(volume>max_volume)
      volume=max_volume;
   double margin=0.0;
   if(!OrderCalcMargin(order_type,symbol,volume,entry,margin) || !SnrFinite(margin) ||
      margin>AccountInfoDouble(ACCOUNT_MARGIN_FREE))
      return(false);

   plan.valid=true;
   plan.entry=entry;
   plan.sl=sl;
   plan.tp=tp;
   plan.volume=volume;
   plan.risk_distance=risk_distance;
   plan.one_lot_loss=one_lot_loss;
   return(true);
  }

bool SnrPlanPendingLevels(const string symbol,const int direction,
                          const double pending_price,const double structural_sl,
                          const double tp_price,const double atr,
                          const double sl_buffer_atr,const double sl_cap,
                          const double min_sl_spread_mult,const double risk_percent,
                          const double ask,const double bid,SnrRiskPlan &plan)
  {
   ZeroMemory(plan);
   const double point=SymbolInfoDouble(symbol,SYMBOL_POINT);
   const double tick_size=SymbolInfoDouble(symbol,SYMBOL_TRADE_TICK_SIZE);
   if(!SnrFinite(pending_price) || !SnrFinite(structural_sl) || !SnrFinite(tp_price) ||
      !SnrFinite(atr) || !SnrFinite(ask) || !SnrFinite(bid) || atr<=0.0 ||
      point<=0.0 || tick_size<=0.0 || direction==SNR_DIR_NONE || ask<=bid)
      return(false);

   double sl_raw=structural_sl;
   if(direction>0)
      sl_raw=MathMin(structural_sl,pending_price)-sl_buffer_atr*atr;
   else
      sl_raw=MathMax(structural_sl,pending_price)+sl_buffer_atr*atr;

   double risk_distance=(direction>0 ? pending_price-sl_raw : sl_raw-pending_price);
   const double spread=ask-bid;
   risk_distance=MathMax(risk_distance,min_sl_spread_mult*spread);
   if(!SnrFinite(risk_distance) || risk_distance<=0.0)
      return(false);
   if(sl_cap>0.0 && risk_distance>sl_cap)
      return(false);

   const double sl_adj=pending_price-direction*risk_distance;
   const double sl=(direction>0 ? SnrFloorToTick(sl_adj,tick_size) : SnrCeilToTick(sl_adj,tick_size));
   const double tp=(direction>0 ? SnrCeilToTick(tp_price,tick_size) : SnrFloorToTick(tp_price,tick_size));
   const double min_dist=(double)MathMax(MathMax(SymbolInfoInteger(symbol,SYMBOL_TRADE_STOPS_LEVEL),
                                                 SymbolInfoInteger(symbol,SYMBOL_TRADE_FREEZE_LEVEL)),0)*point;
   if(MathAbs(pending_price-sl)<min_dist || MathAbs(tp-pending_price)<min_dist)
      return(false);
   if((direction>0 && (sl>=pending_price || tp<=pending_price || pending_price<=ask)) ||
      (direction<0 && (sl<=pending_price || tp>=pending_price || pending_price>=bid)))
      return(false);

   const ENUM_ORDER_TYPE order_type=(direction>0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL);
   double one_lot_loss=0.0;
   if(!OrderCalcProfit(order_type,symbol,1.0,pending_price,sl,one_lot_loss) ||
      !SnrFinite(one_lot_loss) || one_lot_loss>=0.0)
      return(false);
   const double equity=AccountInfoDouble(ACCOUNT_EQUITY);
   if(!SnrFinite(equity) || equity<=0.0 || risk_percent<=0.0)
      return(false);
   double volume=SnrNormalizeVolumeDown(symbol,equity*(risk_percent/100.0)/MathAbs(one_lot_loss));
   if(volume<=0.0)
      return(false);
   double margin=0.0;
   if(!OrderCalcMargin(order_type,symbol,volume,pending_price,margin) || !SnrFinite(margin) ||
      margin>AccountInfoDouble(ACCOUNT_MARGIN_FREE))
      return(false);

   plan.valid=true;
   plan.entry=pending_price;
   plan.sl=sl;
   plan.tp=tp;
   plan.volume=volume;
   plan.risk_distance=risk_distance;
   plan.one_lot_loss=one_lot_loss;
   return(true);
  }

bool SnrRealizedRiskOverBudget(const string symbol,const int direction,
                               const double fill_price,const double sl,
                               const double volume,const double risk_percent,
                               const double tolerance)
  {
   if(!SnrFinite(fill_price) || !SnrFinite(sl) || !SnrFinite(volume) ||
      volume<=0.0 || direction==SNR_DIR_NONE)
      return(true);
   const ENUM_ORDER_TYPE order_type=(direction>0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL);
   double money=0.0;
   if(!OrderCalcProfit(order_type,symbol,volume,fill_price,sl,money) ||
      !SnrFinite(money) || money>=0.0)
      return(true);
   const double equity=AccountInfoDouble(ACCOUNT_EQUITY);
   const double budget=equity*(risk_percent/100.0)*(1.0+MathMax(tolerance,0.0));
   return(MathAbs(money)>budget);
  }

#endif
