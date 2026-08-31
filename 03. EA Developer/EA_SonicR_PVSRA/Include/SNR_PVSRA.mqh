#ifndef SNR_PVSRA_MQH
#define SNR_PVSRA_MQH

#include "SNR_Types.mqh"

int SnrClassifyVolume(const double volume,const double average,
                      const double rising_mult,const double climax_mult)
  {
   if(!SnrFinite(volume) || !SnrFinite(average) || average<=0.0 ||
      volume<0.0 || rising_mult<=0.0 || climax_mult<rising_mult)
      return(SNR_PVSRA_UNKNOWN);
   if(volume>=average*climax_mult)
      return(SNR_PVSRA_CLIMAX);
   if(volume>=average*rising_mult)
      return(SNR_PVSRA_RISING);
   if(volume<average)
      return(SNR_PVSRA_LOW);
   return(SNR_PVSRA_NORMAL);
  }

bool SnrVolumeAveragePrior(const MqlRates &rates[],const int avg_bars,double &average)
  {
   average=0.0;
   const int n=ArraySize(rates);
   if(avg_bars<1 || n<avg_bars+1)
      return(false);
   double sum=0.0;
   for(int i=1;i<=avg_bars;i++)
     {
      const double vol=(double)rates[i].tick_volume;
      if(!SnrFinite(vol) || vol<0.0)
         return(false);
      sum+=vol;
     }
   average=sum/(double)avg_bars;
   return(SnrFinite(average) && average>0.0);
  }

bool SnrSpreadVolumeMaxPrior(const MqlRates &rates[],const int avg_bars,double &max_sv)
  {
   max_sv=0.0;
   const int n=ArraySize(rates);
   if(avg_bars<1 || n<avg_bars+1)
      return(false);
   for(int i=1;i<=avg_bars;i++)
     {
      const double sv=(rates[i].high-rates[i].low)*(double)rates[i].tick_volume;
      if(!SnrFinite(sv) || sv<0.0)
         return(false);
      if(sv>max_sv)
         max_sv=sv;
     }
   return(true);
  }

int SnrClassifyPvaBar(const MqlRates &bar,const double average,
                      const double rising_mult,const double climax_mult,
                      const double max_prior_sv)
  {
   const double volume=(double)bar.tick_volume;
   int cls=SnrClassifyVolume(volume,average,rising_mult,climax_mult);
   if(cls==SNR_PVSRA_UNKNOWN)
      return(SNR_PVSRA_UNKNOWN);
   const double sv=(bar.high-bar.low)*volume;
   if(SnrFinite(sv) && max_prior_sv>0.0 && sv>=max_prior_sv && cls!=SNR_PVSRA_CLIMAX)
      cls=SNR_PVSRA_CLIMAX;
   return(cls);
  }

bool SnrPvsraReadClosed(const MqlRates &rates[],const int direction,
                        const int avg_bars,const double rising_mult,
                        const double climax_mult,SnrPvsraSnap &out)
  {
   ZeroMemory(out);
   if(ArraySize(rates)<2)
      return(false);
   double average=0.0;
   double max_sv=0.0;
   if(!SnrVolumeAveragePrior(rates,avg_bars,average) ||
      !SnrSpreadVolumeMaxPrior(rates,avg_bars,max_sv))
      return(false);
   const double volume=(double)rates[0].tick_volume;
   const int cls=SnrClassifyPvaBar(rates[0],average,rising_mult,climax_mult,max_sv);
   if(cls==SNR_PVSRA_UNKNOWN)
      return(false);
   const bool bull=(rates[0].close>rates[0].open);
   const bool bear=(rates[0].close<rates[0].open);
   const bool with_dir=((direction>0 && bull) || (direction<0 && bear));
   const bool against=((direction>0 && bear) || (direction<0 && bull));
   const bool rising_or_climax=(cls==SNR_PVSRA_RISING || cls==SNR_PVSRA_CLIMAX);
   out.valid=true;
   out.cls=cls;
   out.volume=volume;
   out.average=average;
   out.support=(rising_or_climax && with_dir);
   out.veto=(cls==SNR_PVSRA_CLIMAX && against);
   return(true);
  }

#endif
