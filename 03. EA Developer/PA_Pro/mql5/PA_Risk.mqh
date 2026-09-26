//+------------------------------------------------------------------+
//|                                                      PA_Risk.mqh |
//|  PA-PRO EA lane - risk governor.                                 |
//|                                                                  |
//|  Sizing: lots = risk_frac * equity / (stop distance in ticks *   |
//|  tick_value), normalised to the symbol's lot step and clamped to |
//|  [min_lot, max_lot].                                             |
//|  Locks (both default ON, inputs):                                |
//|   - daily-loss lock: server-day closed PnL <= -4% of day-start   |
//|     equity  -> no new signals for the rest of the day;           |
//|   - max-drawdown lock: equity <= (1 - 8%) x peak equity          |
//|     -> no new signals until the Owner resets.                    |
//|                                                                  |
//|  No order, position or trade call exists in this header.         |
//+------------------------------------------------------------------+
#ifndef PA_RISK_MQH
#define PA_RISK_MQH

#include "PA_Types.mqh"

//+------------------------------------------------------------------+
//| CPaRisk - stateless sizing + stateful lock tracking              |
//+------------------------------------------------------------------+
class CPaRisk
  {
public:
   double            risk_frac;      // 0.005 = 0.5% per trade
   double            daily_lock;     // 0.04  = -4% of day-start equity
   double            dd_lock;        // 0.08  = -8% of peak equity
   //--- tracked state
   double            peak_equity;
   double            day_start_eq;
   long              day_cur;
   bool              locked_dd;
   bool              locked_day;

                     CPaRisk(void)
     {
      risk_frac=0.005;
      daily_lock=0.04;
      dd_lock=0.08;
      peak_equity=0.0;
      day_start_eq=0.0;
      day_cur=-1;
      locked_dd=false;
      locked_day=false;
     }

   //--- roll the per-day / peak bookkeeping on each new bar
   void Roll(const long bar_t,const double equity)
     {
      if(equity>peak_equity)
         peak_equity=equity;
      long day=bar_t/PA_DAY_SEC;
      if(day!=day_cur)
        {
         day_cur=day;
         day_start_eq=equity;
         locked_day=false;
        }
      if(peak_equity>0.0 && equity<=(1.0-dd_lock)*peak_equity)
         locked_dd=true;
      if(day_start_eq>0.0 && equity<=(1.0-daily_lock)*day_start_eq)
         locked_day=true;
     }

   bool Locked() const { return(locked_dd || locked_day); }

   string LockReason() const
     {
      if(locked_dd)
         return("DD_LOCK");
      if(locked_day)
         return("DAILY_LOCK");
      return("");
     }

   //--- position size for a stop distance (price units); returns 0 when
   //--- the distance or the symbol data is degenerate
   double Lots(const string sym,const double sl_dist,const double equity) const
     {
      if(sl_dist<=0.0 || equity<=0.0)
         return(0.0);
      double tick_val=SymbolInfoDouble(sym,SYMBOL_TRADE_TICK_VALUE);
      double tick_sz =SymbolInfoDouble(sym,SYMBOL_TRADE_TICK_SIZE);
      if(tick_val<=0.0 || tick_sz<=0.0)
         return(0.0);
      double risk_money=risk_frac*equity;
      double loss_per_lot=(sl_dist/tick_sz)*tick_val;
      if(loss_per_lot<=0.0)
         return(0.0);
      double lots=risk_money/loss_per_lot;
      double vmin=SymbolInfoDouble(sym,SYMBOL_VOLUME_MIN);
      double vmax=SymbolInfoDouble(sym,SYMBOL_VOLUME_MAX);
      double step=SymbolInfoDouble(sym,SYMBOL_VOLUME_STEP);
      if(step>0.0)
         lots=MathFloor(lots/step)*step;
      if(vmax>0.0)
         lots=MathMin(lots,vmax);
      if(lots<vmin)
         return(0.0);                 // risk too small for one minimum lot
      return(NormalizeDouble(lots,8));
     }
  };

#endif // PA_RISK_MQH
