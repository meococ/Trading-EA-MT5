#ifndef SNR_WAVE_MQH
#define SNR_WAVE_MQH

#include "SNR_Types.mqh"

bool SnrIsSwingHigh(const MqlRates &rates[],const int index,const int strength)
  {
   const int n=ArraySize(rates);
   if(strength<1 || index<strength || index+strength>=n)
      return(false);
   for(int k=1;k<=strength;k++)
     {
      if(rates[index].high<=rates[index-k].high || rates[index].high<=rates[index+k].high)
         return(false);
     }
   return(true);
  }

bool SnrIsSwingLow(const MqlRates &rates[],const int index,const int strength)
  {
   const int n=ArraySize(rates);
   if(strength<1 || index<strength || index+strength>=n)
      return(false);
   for(int k=1;k<=strength;k++)
     {
      if(rates[index].low>=rates[index-k].low || rates[index].low>=rates[index+k].low)
         return(false);
     }
   return(true);
  }

bool SnrWaveReadClosed(const MqlRates &rates[],const double &dragon_high[],
                       const double &dragon_mid[],const double &dragon_low[],
                       const double &atr[],const int direction,
                       const SnrClassicCfg &cfg,SnrWaveSnap &out)
  {
   ZeroMemory(out);
   const int n=ArraySize(rates);
   const int scan=MathMin(n-cfg.swing_strength-1,cfg.wave_lookback);
   if(cfg.swing_strength<1 || scan<=cfg.swing_strength || n<cfg.swing_strength*4+2 ||
      ArraySize(dragon_high)<n || ArraySize(dragon_mid)<n || ArraySize(dragon_low)<n ||
      ArraySize(atr)<n || direction==SNR_DIR_NONE)
      return(true);
   if(!SnrFinite(atr[0]) || atr[0]<=0.0 || !SnrFinite(dragon_mid[0]))
      return(false);

   int s1=-1;
   int x1=-1;
   int s2=-1;
   int x2=-1;
   for(int i=cfg.swing_strength;i<=scan;i++)
     {
      if(direction>0)
        {
         if(s1<0 && SnrIsSwingLow(rates,i,cfg.swing_strength))
            s1=i;
         else if(s1>=0 && x1<0 && i>s1 && SnrIsSwingHigh(rates,i,cfg.swing_strength))
            x1=i;
         else if(x1>=0 && s2<0 && i>x1 && SnrIsSwingLow(rates,i,cfg.swing_strength))
            s2=i;
         else if(s2>=0 && x2<0 && i>s2 && SnrIsSwingHigh(rates,i,cfg.swing_strength))
            x2=i;
        }
      else
        {
         if(s1<0 && SnrIsSwingHigh(rates,i,cfg.swing_strength))
            s1=i;
         else if(s1>=0 && x1<0 && i>s1 && SnrIsSwingLow(rates,i,cfg.swing_strength))
            x1=i;
         else if(x1>=0 && s2<0 && i>x1 && SnrIsSwingHigh(rates,i,cfg.swing_strength))
            s2=i;
         else if(s2>=0 && x2<0 && i>s2 && SnrIsSwingLow(rates,i,cfg.swing_strength))
            x2=i;
        }
      if(s1>=0 && x1>=0 && s2>=0)
         break;
     }
   if(s1<0 || x1<0 || s2<0 || s1>cfg.max_pullback_age)
      return(true);
   if(!SnrFinite(atr[s1]) || atr[s1]<=0.0 ||
      !SnrFinite(dragon_high[s1]) || !SnrFinite(dragon_low[s1]) ||
      !SnrFinite(dragon_high[0]) || !SnrFinite(dragon_low[0]) || !SnrFinite(dragon_mid[0]))
      return(false);

   const double touch=cfg.dragon_touch_atr*atr[s1];
   bool into_dragon=false;
   bool left_band=false;
   bool structure_ok=false;
   double pullback=0.0;
   double impulse=0.0;
   double prior=0.0;
   double overlap=1.0;
   if(direction>0)
     {
      pullback=rates[s1].low;
      impulse=rates[x1].high;
      prior=rates[s2].low;
      into_dragon=(pullback<=dragon_high[s1]+touch && pullback>=dragon_low[s1]-touch);
      left_band=(impulse>=dragon_high[x1]-touch);
      structure_ok=(pullback>=prior-0.10*atr[0]);
      const double imp_len=impulse-prior;
      if(!SnrFinite(imp_len) || imp_len<=0.0)
         return(true);
      if(x2>=0)
        {
         const double prev_hi=rates[x2].high;
         const double prev_lo=rates[s2].low;
         const double prev_len=prev_hi-prev_lo;
         const double inter=MathMin(prev_hi,impulse)-MathMax(prev_lo,prior);
         const double denom=MathMin(MathMax(prev_len,0.0),imp_len);
         overlap=(denom>0.0 && inter>0.0 ? inter/denom : 0.0);
        }
      else
         overlap=(impulse-pullback)/imp_len;
     }
   else
     {
      pullback=rates[s1].high;
      impulse=rates[x1].low;
      prior=rates[s2].high;
      into_dragon=(pullback>=dragon_low[s1]-touch && pullback<=dragon_high[s1]+touch);
      left_band=(impulse<=dragon_low[x1]+touch);
      structure_ok=(pullback<=prior+0.10*atr[0]);
      const double imp_len=prior-impulse;
      if(!SnrFinite(imp_len) || imp_len<=0.0)
         return(true);
      if(x2>=0)
        {
         const double prev_hi=rates[s2].high;
         const double prev_lo=rates[x2].low;
         const double prev_len=prev_hi-prev_lo;
         const double inter=MathMin(prev_hi,prior)-MathMax(prev_lo,impulse);
         const double denom=MathMin(MathMax(prev_len,0.0),imp_len);
         overlap=(denom>0.0 && inter>0.0 ? inter/denom : 0.0);
        }
      else
         overlap=(pullback-impulse)/imp_len;
     }
   if(!SnrFinite(overlap) || overlap<0.0)
      overlap=1.0;

   const double buf0=cfg.dragon_touch_atr*atr[0];
   bool broke=false;
   bool reject=false;
   if(direction>0)
     {
      broke=(rates[0].close>impulse);
      reject=(rates[0].low<=dragon_high[0]+buf0 && rates[0].close>dragon_mid[0] &&
              rates[0].close>rates[0].open);
     }
   else
     {
      broke=(rates[0].close<impulse);
      reject=(rates[0].high>=dragon_low[0]-buf0 && rates[0].close<dragon_mid[0] &&
              rates[0].close<rates[0].open);
     }
   const bool directional_close=((direction>0 && rates[0].close>rates[0].open) ||
                                 (direction<0 && rates[0].close<rates[0].open));
   const bool choppy=(!structure_ok || overlap>cfg.max_overlap_ratio || !left_band);
   out.valid=true;
   out.direction=direction;
   out.overlap_ratio=overlap;
   out.pullback_price=pullback;
   out.impulse_extreme=impulse;
   out.structure_swing=prior;
   out.pullback_index=s1;
   out.into_dragon=into_dragon;
   out.break_or_reject=(directional_close && (broke || reject));
   out.quality=((!choppy && into_dragon && out.break_or_reject) ? SNR_WAVE_CLEAN : SNR_WAVE_CHOPPY);
   return(true);
  }

#endif
