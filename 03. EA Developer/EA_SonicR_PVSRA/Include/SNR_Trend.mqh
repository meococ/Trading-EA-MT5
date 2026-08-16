#ifndef SNR_TREND_MQH
#define SNR_TREND_MQH

#include "SNR_Types.mqh"

bool SnrTrendCreate(SnrHandles &h,const string symbol,const ENUM_TIMEFRAMES tf,
                    const int trend_period)
  {
   h.trend=iMA(symbol,tf,trend_period,0,MODE_EMA,PRICE_CLOSE);
   return(h.trend!=INVALID_HANDLE);
  }

bool SnrTrendReadClosed(const double &ema[],const double close_price,
                        const int slope_bars,SnrTrendSnap &out)
  {
   ZeroMemory(out);
   const int n=ArraySize(ema);
   if(slope_bars<1 || n<slope_bars+1 || !SnrFinite(close_price) ||
      !SnrFinite(ema[0]) || !SnrFinite(ema[slope_bars]))
      return(false);
   const double slope=ema[0]-ema[slope_bars];
   if(!SnrFinite(slope))
      return(false);
   out.valid=true;
   out.ema=ema[0];
   out.slope=slope;
   if(close_price>ema[0])
      out.side=SNR_DIR_LONG;
   else if(close_price<ema[0])
      out.side=SNR_DIR_SHORT;
   else
      out.side=SNR_DIR_NONE;
   return(true);
  }

bool SnrTrendAligned(const SnrTrendSnap &trend,const int direction)
  {
   if(!trend.valid || direction==SNR_DIR_NONE)
      return(false);
   if(direction>0)
      return(trend.side==SNR_DIR_LONG && trend.slope>0.0);
   return(trend.side==SNR_DIR_SHORT && trend.slope<0.0);
  }

#endif
