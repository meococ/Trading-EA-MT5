#ifndef SNR_DRAGON_MQH
#define SNR_DRAGON_MQH

#include "SNR_Types.mqh"

bool SnrDragonCreate(SnrHandles &h,const string symbol,const ENUM_TIMEFRAMES tf,
                     const int dragon_period,const int atr_period)
  {
   h.dragon_high=iMA(symbol,tf,dragon_period,0,MODE_EMA,PRICE_HIGH);
   h.dragon_mid=iMA(symbol,tf,dragon_period,0,MODE_EMA,PRICE_CLOSE);
   h.dragon_low=iMA(symbol,tf,dragon_period,0,MODE_EMA,PRICE_LOW);
   h.atr=iATR(symbol,tf,atr_period);
   return(h.dragon_high!=INVALID_HANDLE && h.dragon_mid!=INVALID_HANDLE &&
          h.dragon_low!=INVALID_HANDLE && h.atr!=INVALID_HANDLE);
  }

bool SnrH1Create(SnrHandles &h,const string symbol,
                 const int dragon_period,const int trend_period,const int atr_period)
  {
   h.h1_dragon_high=iMA(symbol,PERIOD_H1,dragon_period,0,MODE_EMA,PRICE_HIGH);
   h.h1_dragon_mid=iMA(symbol,PERIOD_H1,dragon_period,0,MODE_EMA,PRICE_CLOSE);
   h.h1_dragon_low=iMA(symbol,PERIOD_H1,dragon_period,0,MODE_EMA,PRICE_LOW);
   h.h1_trend=iMA(symbol,PERIOD_H1,trend_period,0,MODE_EMA,PRICE_CLOSE);
   h.h1_atr=iATR(symbol,PERIOD_H1,atr_period);
   return(h.h1_dragon_high!=INVALID_HANDLE && h.h1_dragon_mid!=INVALID_HANDLE &&
          h.h1_dragon_low!=INVALID_HANDLE && h.h1_trend!=INVALID_HANDLE &&
          h.h1_atr!=INVALID_HANDLE);
  }

bool SnrDragonReadClosed(const double &high[],const double &mid[],const double &low[],
                         const double &atr[],const int slope_bars,
                         const double min_slope_atr,SnrDragonSnap &out)
  {
   ZeroMemory(out);
   const int n=ArraySize(mid);
   if(slope_bars<1 || ArraySize(high)<slope_bars+1 || n<slope_bars+1 ||
      ArraySize(low)<slope_bars+1 || ArraySize(atr)<1)
      return(false);
   if(!SnrFinite(high[0]) || !SnrFinite(mid[0]) || !SnrFinite(low[0]) ||
      !SnrFinite(atr[0]) || atr[0]<=0.0)
      return(false);
   if(high[0]<low[0] || mid[0]>high[0] || mid[0]<low[0])
      return(false);
   if(!SnrFinite(mid[slope_bars]))
      return(false);
   const double slope_atr=(mid[0]-mid[slope_bars])/((double)slope_bars*atr[0]);
   if(!SnrFinite(slope_atr))
      return(false);
   out.valid=true;
   out.high=high[0];
   out.mid=mid[0];
   out.low=low[0];
   out.slope_atr=slope_atr;
   if(slope_atr>0.0)
      out.side=SNR_DIR_LONG;
   else if(slope_atr<0.0)
      out.side=SNR_DIR_SHORT;
   else
      out.side=SNR_DIR_NONE;
   out.angled=(MathAbs(slope_atr)>=min_slope_atr && out.side!=SNR_DIR_NONE);
   return(true);
  }

#endif
