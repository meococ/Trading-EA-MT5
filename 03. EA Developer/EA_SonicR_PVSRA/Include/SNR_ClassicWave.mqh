#ifndef SNR_CLASSIC_WAVE_MQH
#define SNR_CLASSIC_WAVE_MQH

#include "SNR_Types.mqh"

bool SnrClassicSwingHigh(const MqlRates &rates[],const int index,const int strength)
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

bool SnrClassicSwingLow(const MqlRates &rates[],const int index,const int strength)
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

bool SnrClassicPriorBreak(const MqlRates &rates[],const double &band[],
                          const int direction,const int newer_exclusive)
  {
   if(newer_exclusive<=1)
      return(false);
   const int last=MathMin(newer_exclusive-1,ArraySize(rates)-1);
   for(int k=1;k<=last;k++)
     {
      if(!SnrFinite(band[k]))
         continue;
      if(direction>0 && rates[k].close>band[k])
         return(true);
      if(direction<0 && rates[k].close<band[k])
         return(true);
     }
   return(false);
  }

bool SnrClassicWaveReadClosed(const MqlRates &rates[],const double &dragon_high[],
                              const double &dragon_low[],const int direction,
                              const SnrClassicCfg &cfg,SnrWaveSnap &out)
  {
   ZeroMemory(out);
   const int n=ArraySize(rates);
   const int scan=MathMin(n-cfg.swing_strength-1,cfg.wave_lookback);
   if(cfg.swing_strength<1 || scan<=cfg.swing_strength || n<cfg.swing_strength*4+2 ||
      ArraySize(dragon_high)<n || ArraySize(dragon_low)<n || direction==SNR_DIR_NONE)
      return(true);
   if(!SnrFinite(dragon_high[0]) || !SnrFinite(dragon_low[0]))
      return(false);

   int leg2=-1;
   int leg1=-1;
   int leg0=-1;
   for(int i=cfg.swing_strength;i<=scan;i++)
     {
      if(direction>0)
        {
         if(leg2<0 && SnrClassicSwingLow(rates,i,cfg.swing_strength))
            leg2=i;
         else if(leg2>=0 && leg1<0 && i>leg2 && SnrClassicSwingHigh(rates,i,cfg.swing_strength))
            leg1=i;
         else if(leg1>=0 && leg0<0 && i>leg1 && SnrClassicSwingLow(rates,i,cfg.swing_strength))
           {
            leg0=i;
            break;
           }
        }
      else
        {
         if(leg2<0 && SnrClassicSwingHigh(rates,i,cfg.swing_strength))
            leg2=i;
         else if(leg2>=0 && leg1<0 && i>leg2 && SnrClassicSwingLow(rates,i,cfg.swing_strength))
            leg1=i;
         else if(leg1>=0 && leg0<0 && i>leg1 && SnrClassicSwingHigh(rates,i,cfg.swing_strength))
           {
            leg0=i;
            break;
           }
        }
     }
   if(leg0<0 || leg1<0 || leg2<0 || leg2>cfg.max_pullback_age)
      return(true);
   if(!SnrFinite(dragon_high[leg0]) || !SnrFinite(dragon_low[leg0]) ||
      !SnrFinite(dragon_high[leg1]) || !SnrFinite(dragon_low[leg1]))
      return(false);

   bool structure_ok=false;
   bool start_outside=false;
   bool thru_dragon=false;
   if(direction>0)
     {
      structure_ok=(rates[leg2].low>rates[leg0].low);
      start_outside=(rates[leg0].low<dragon_low[leg0]);
      thru_dragon=(rates[leg0].high>dragon_high[leg0] || rates[leg1].low<dragon_low[leg1]);
     }
   else
     {
      structure_ok=(rates[leg2].high<rates[leg0].high);
      start_outside=(rates[leg0].high>dragon_high[leg0]);
      thru_dragon=(rates[leg0].low<dragon_low[leg0] || rates[leg1].high>dragon_high[leg1]);
     }
   if(!structure_ok || !start_outside)
      return(true);

   bool prior=false;
   if(direction>0)
      prior=SnrClassicPriorBreak(rates,dragon_high,direction,leg2);
   else
      prior=SnrClassicPriorBreak(rates,dragon_low,direction,leg2);
   bool trigger=false;
   if(direction>0)
      trigger=(rates[0].close>dragon_high[0] && rates[0].close>rates[0].open && !prior);
   else
      trigger=(rates[0].close<dragon_low[0] && rates[0].close<rates[0].open && !prior);

   out.valid=true;
   out.direction=direction;
   out.leg0_index=leg0;
   out.leg1_index=leg1;
   out.leg2_index=leg2;
   out.pullback_index=leg2;
   out.structure_swing=(direction>0 ? rates[leg0].low : rates[leg0].high);
   out.impulse_extreme=(direction>0 ? rates[leg1].high : rates[leg1].low);
   out.pullback_price=(direction>0 ? rates[leg2].low : rates[leg2].high);
   out.into_dragon=start_outside;
   out.leg1_thru_dragon=thru_dragon;
   out.first_break=(!prior);
   out.break_or_reject=trigger;
   out.quality=(trigger ? SNR_WAVE_CLEAN : SNR_WAVE_CHOPPY);
   return(true);
  }

#endif
