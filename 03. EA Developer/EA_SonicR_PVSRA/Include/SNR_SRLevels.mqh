#ifndef SNR_SRLEVELS_MQH
#define SNR_SRLEVELS_MQH

#include "SNR_Types.mqh"

double SnrRoundStep(const double whole,const int kind)
  {
   if(whole<=0.0)
      return(0.0);
   if(kind==SNR_SR_WHOLE)
      return(whole);
   if(kind==SNR_SR_HALF)
      return(whole*0.5);
   if(kind==SNR_SR_QUARTER)
      return(whole*0.25);
   return(0.0);
  }

int SnrRoundKind(const double price,const double whole)
  {
   if(!SnrFinite(price) || whole<=0.0)
      return(SNR_SR_NONE);
   const double q=whole*0.25;
   const double units=price/q;
   if(MathAbs(units-MathRound(units))>1e-8)
      return(SNR_SR_NONE);
   const int step=(int)MathRound(MathAbs(units));
   if(step%4==0)
      return(SNR_SR_WHOLE);
   if(step%2==0)
      return(SNR_SR_HALF);
   return(SNR_SR_QUARTER);
  }

bool SnrNearestDirectionalLevel(const double close_price,const int direction,
                                const double whole,double &level,int &kind)
  {
   level=0.0;
   kind=SNR_SR_NONE;
   const double half=SnrRoundStep(whole,SNR_SR_HALF);
   if(!SnrFinite(close_price) || half<=0.0 || direction==SNR_DIR_NONE)
      return(false);
   if(direction>0)
     {
      level=MathCeil(close_price/half)*half;
      if(level<=close_price)
         level+=half;
     }
   else
     {
      level=MathFloor(close_price/half)*half;
      if(level>=close_price)
         level-=half;
     }
   if(!SnrFinite(level))
      return(false);
   kind=SnrRoundKind(level,whole);
   if(kind!=SNR_SR_WHOLE && kind!=SNR_SR_HALF)
      kind=SNR_SR_HALF;
   return(true);
  }

int SnrCollectVisibleLevels(const double anchor,const double whole,const int each_side,
                            const bool include_quarter,double &levels[],int &kinds[])
  {
   ArrayResize(levels,0);
   ArrayResize(kinds,0);
   const double step=(include_quarter ? SnrRoundStep(whole,SNR_SR_QUARTER) : SnrRoundStep(whole,SNR_SR_HALF));
   if(!SnrFinite(anchor) || step<=0.0 || each_side<1)
      return(0);
   const double center=MathRound(anchor/step)*step;
   const int count=each_side*2+1;
   ArrayResize(levels,count);
   ArrayResize(kinds,count);
   int written=0;
   for(int i=-each_side;i<=each_side;i++)
     {
      const double price=center+i*step;
      const int kind=SnrRoundKind(price,whole);
      if(kind==SNR_SR_NONE)
         continue;
      if(!include_quarter && kind==SNR_SR_QUARTER)
         continue;
      levels[written]=price;
      kinds[written]=kind;
      written++;
     }
   ArrayResize(levels,written);
   ArrayResize(kinds,written);
   return(written);
  }

bool SnrSrReadClosed(const double close_price,const int direction,const double atr,
                     const double whole,const double runway_atr,SnrSrSnap &out)
  {
   ZeroMemory(out);
   if(!SnrFinite(close_price) || !SnrFinite(atr) || atr<=0.0 || whole<=0.0 ||
      runway_atr<0.0 || direction==SNR_DIR_NONE)
      return(false);
   const double half=SnrRoundStep(whole,SNR_SR_HALF);
   if(half<=0.0)
      return(false);
   const double snapped=MathRound(close_price/half)*half;
   if(MathAbs(close_price-snapped)<=1e-8)
     {
      out.valid=true;
      out.level=snapped;
      out.kind=SnrRoundKind(snapped,whole);
      if(out.kind!=SNR_SR_WHOLE && out.kind!=SNR_SR_HALF)
         out.kind=SNR_SR_HALF;
      out.distance=0.0;
      out.blocked=true;
      return(true);
     }
   double level=0.0;
   int kind=SNR_SR_NONE;
   if(!SnrNearestDirectionalLevel(close_price,direction,whole,level,kind))
      return(false);
   const double distance=MathAbs(level-close_price);
   const double limit=runway_atr*atr;
   out.valid=true;
   out.level=level;
   out.kind=kind;
   out.distance=distance;
   out.blocked=(distance<=limit);
   return(true);
  }

bool SnrFirstWhqTarget(const double entry,const int direction,const double whole,
                       const double min_runway,double &tp)
  {
   tp=0.0;
   if(!SnrFinite(entry) || !SnrFinite(whole) || whole<=0.0 ||
      !SnrFinite(min_runway) || min_runway<=0.0 || direction==SNR_DIR_NONE)
      return(false);
   const double half=SnrRoundStep(whole,SNR_SR_HALF);
   if(half<=0.0)
      return(false);
   double level=0.0;
   int kind=SNR_SR_NONE;
   if(!SnrNearestDirectionalLevel(entry,direction,whole,level,kind))
      return(false);
   for(int i=0;i<8;i++)
     {
      if(MathAbs(level-entry)>=min_runway)
        {
         tp=level;
         return(true);
        }
      level+=(direction>0 ? half : -half);
     }
   return(false);
  }

#endif
