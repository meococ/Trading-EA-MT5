#ifndef EA_ICTFVG_HUMAN_CONTEXT_ENGINE_MQH
#define EA_ICTFVG_HUMAN_CONTEXT_ENGINE_MQH

// HYP-015 is an observation surface only. None of these states may gate,
// resize, redirect or otherwise alter a trade under this hypothesis.
enum ENUM_HUMAN_CONTEXT_STATE
  {
   HUMAN_CONTEXT_INCOMPLETE=0,
   HUMAN_CONTEXT_NO_DIRECTIONAL_TARGET=1,
   HUMAN_CONTEXT_DIRECTIONAL_EXHAUSTION=2,
   HUMAN_CONTEXT_STRUCTURE_CONFLICT=3,
   HUMAN_CONTEXT_EXTERNAL_SWEEP_WITH_ROOM=4,
   HUMAN_CONTEXT_INTERNAL_SWEEP_WITH_ROOM=5,
   HUMAN_CONTEXT_INSUFFICIENT_ROOM=6
  };

struct HumanContextSnapshot
  {
   bool valid;
   ENUM_HUMAN_CONTEXT_STATE state;
   double h1_range_low;
   double h1_range_high;
   double h1_range_location;
   double h4_range_low;
   double h4_range_high;
   double h4_range_location;
   int h1_structure;
   int h4_structure;
   bool h1_aligned;
   bool h4_aligned;
   double h1_pivot_high;
   double h1_pivot_low;
   double h4_pivot_high;
   double h4_pivot_low;
   double previous_day_high;
   double previous_day_low;
   double previous_week_high;
   double previous_week_low;
   double asia_high;
   double asia_low;
   string nearest_pool_type;
   double nearest_pool_price;
   double nearest_pool_pips;
   int directional_pool_count;
   double room_r;
   bool room_to_target;
   bool external_sweep;
   int external_swept_count;
   double partial_h1_body_atr;
   double partial_h4_body_atr;
   double confirmation_body_atr;
   int directional_run_bars;
   double h1_extension_atr;
   double h4_extension_atr;
   double spread_to_risk;
  };

void ResetHumanContext(HumanContextSnapshot &context)
  {
   ZeroMemory(context);
   context.state=HUMAN_CONTEXT_INCOMPLETE;
   context.nearest_pool_type="NONE";
  }

string HumanContextStateName(const ENUM_HUMAN_CONTEXT_STATE state)
  {
   if(state==HUMAN_CONTEXT_NO_DIRECTIONAL_TARGET)
      return "NO_DIRECTIONAL_TARGET";
   if(state==HUMAN_CONTEXT_DIRECTIONAL_EXHAUSTION)
      return "DIRECTIONAL_EXHAUSTION";
   if(state==HUMAN_CONTEXT_STRUCTURE_CONFLICT)
      return "STRUCTURE_CONFLICT";
   if(state==HUMAN_CONTEXT_EXTERNAL_SWEEP_WITH_ROOM)
      return "EXTERNAL_SWEEP_WITH_ROOM";
   if(state==HUMAN_CONTEXT_INTERNAL_SWEEP_WITH_ROOM)
      return "INTERNAL_SWEEP_WITH_ROOM";
   if(state==HUMAN_CONTEXT_INSUFFICIENT_ROOM)
      return "INSUFFICIENT_ROOM";
   return "INCOMPLETE";
  }

bool HumanRateRange(const MqlRates &rates[],const int bars,
                    double &range_low,double &range_high)
  {
   if(ArraySize(rates)<bars || bars<1)
      return false;
   range_low=rates[0].low;
   range_high=rates[0].high;
   for(int index=1;index<bars;index++)
     {
      range_low=MathMin(range_low,rates[index].low);
      range_high=MathMax(range_high,rates[index].high);
     }
   return range_high-range_low>=_Point;
  }

double HumanAtrFromRates(const MqlRates &rates[],const int period)
  {
   if(ArraySize(rates)<period+1 || period<1)
      return 0.0;
   double total=0.0;
   for(int index=0;index<period;index++)
     {
      double true_range=rates[index].high-rates[index].low;
      true_range=MathMax(true_range,MathAbs(rates[index].high-rates[index+1].close));
      true_range=MathMax(true_range,MathAbs(rates[index].low-rates[index+1].close));
      total+=true_range;
     }
   return total/(double)period;
  }

bool HumanConfirmedPivotStructure(const MqlRates &rates[],const int strength,
                                  int &structure,double &latest_high,
                                  double &latest_low)
  {
   structure=0;
   latest_high=0.0;
   latest_low=0.0;
   double previous_high=0.0;
   double previous_low=0.0;
   int highs=0;
   int lows=0;
   int count=ArraySize(rates);
   for(int center=strength;center<count-strength && (highs<2 || lows<2);center++)
     {
      bool pivot_high=true;
      bool pivot_low=true;
      for(int distance=1;distance<=strength;distance++)
        {
         if(rates[center].high<=rates[center-distance].high ||
            rates[center].high<rates[center+distance].high)
            pivot_high=false;
         if(rates[center].low>=rates[center-distance].low ||
            rates[center].low>rates[center+distance].low)
            pivot_low=false;
        }
      if(pivot_high && highs<2)
        {
         if(highs==0)
            latest_high=rates[center].high;
         else
            previous_high=rates[center].high;
         highs++;
        }
      if(pivot_low && lows<2)
        {
         if(lows==0)
            latest_low=rates[center].low;
         else
            previous_low=rates[center].low;
         lows++;
        }
     }
   if(highs<2 || lows<2)
      return false;
   if(latest_high>previous_high && latest_low>previous_low)
      structure=1;
   else if(latest_high<previous_high && latest_low<previous_low)
      structure=-1;
   return true;
  }

int HumanUtcDateKey(const datetime server_time)
  {
   MqlDateTime parts;
   TimeToStruct(ServerToUtc(server_time),parts);
   return parts.year*10000+parts.mon*100+parts.day;
  }

bool HumanAsiaRange(const datetime decision_server_time,
                    double &asia_low,double &asia_high)
  {
   MqlRates m5[];
   ArraySetAsSeries(m5,true);
   int copied=CopyRates(_Symbol,PERIOD_M5,1,420,m5);
   if(copied<1)
      return false;
   int decision_key=HumanUtcDateKey(decision_server_time);
   bool found=false;
   for(int index=0;index<copied;index++)
     {
      datetime utc=ServerToUtc(m5[index].time);
      MqlDateTime parts;
      TimeToStruct(utc,parts);
      int key=parts.year*10000+parts.mon*100+parts.day;
      int minute=parts.hour*60+parts.min;
      if(key!=decision_key || minute<0 || minute>=7*60)
         continue;
      if(!found)
        {
         asia_low=m5[index].low;
         asia_high=m5[index].high;
         found=true;
        }
      else
        {
         asia_low=MathMin(asia_low,m5[index].low);
         asia_high=MathMax(asia_high,m5[index].high);
        }
     }
   return found && asia_high-asia_low>=_Point;
  }

bool BuildPartialHtfFromClosedM5(const ENUM_TIMEFRAMES timeframe,
                                 const datetime decision_server_time,
                                 double &partial_open,double &partial_high,
                                 double &partial_low,double &partial_close)
  {
   int seconds=PeriodSeconds(timeframe);
   int bars_required=seconds/PeriodSeconds(PERIOD_M5)+2;
   if(seconds<=0 || bars_required<2)
      return false;
   if((long)decision_server_time%seconds==0)
     {
      partial_open=0.0;
      partial_high=0.0;
      partial_low=0.0;
      partial_close=0.0;
      return true;
     }
   MqlRates m5[];
   ArraySetAsSeries(m5,true);
   int copied=CopyRates(_Symbol,PERIOD_M5,1,bars_required,m5);
   if(copied<1)
      return false;
   datetime bucket_start=(datetime)(((long)decision_server_time/seconds)*seconds);
   bool found=false;
   for(int index=copied-1;index>=0;index--)
     {
      if(m5[index].time<bucket_start ||
         m5[index].time+PeriodSeconds(PERIOD_M5)>decision_server_time)
         continue;
      if(!found)
        {
         partial_open=m5[index].open;
         partial_high=m5[index].high;
         partial_low=m5[index].low;
         found=true;
        }
      else
        {
         partial_high=MathMax(partial_high,m5[index].high);
         partial_low=MathMin(partial_low,m5[index].low);
        }
      partial_close=m5[index].close;
     }
   return found;
  }

void HumanAddDirectionalPool(const int direction,const double entry,
                             const double price,const string pool_type,
                             double &nearest_distance,double &nearest_price,
                             string &nearest_type,int &pool_count)
  {
   if(price<=0.0)
      return;
   double signed_distance=(double)direction*(price-entry);
   if(signed_distance<=_Point)
      return;
   pool_count++;
   if(nearest_distance<=0.0 || signed_distance<nearest_distance)
     {
      nearest_distance=signed_distance;
      nearest_price=price;
      nearest_type=pool_type;
     }
  }

void HumanCountSweptPool(const int direction,const double sweep_high,
                         const double sweep_low,const double sweep_close,
                         const double pool_price,int &count)
  {
   if(pool_price<=0.0)
      return;
   if(direction>0 && sweep_low<pool_price && sweep_close>pool_price)
      count++;
   else if(direction<0 && sweep_high>pool_price && sweep_close<pool_price)
      count++;
  }

int HumanDirectionalRunBars(const MqlRates &m5[],const int direction)
  {
   int run=0;
   for(int index=0;index<ArraySize(m5);index++)
     {
      bool directional=(direction>0 ? m5[index].close>m5[index].open
                                     : m5[index].close<m5[index].open);
      if(!directional)
         break;
      run++;
     }
   return run;
  }

bool BuildHumanContextSnapshot(const int direction,
                               const datetime decision_server_time,
                               const double sweep_high,const double sweep_low,
                               const double sweep_close,
                               const MqlRates &confirmation_bar,
                               const double entry,const double stop,
                               const double spread,
                               HumanContextSnapshot &context)
  {
   ResetHumanContext(context);
   int requested=MathMax(InpHumanPivotLookback,
                         MathMax(InpHumanRangeBars,InpHumanAtrPeriod+1))+
                 2*InpHumanPivotStrength+2;
   MqlRates h1[];
   MqlRates h4[];
   MqlRates m5[];
   MqlRates daily[];
   MqlRates weekly[];
   ArraySetAsSeries(h1,true);
   ArraySetAsSeries(h4,true);
   ArraySetAsSeries(m5,true);
   ArraySetAsSeries(daily,true);
   ArraySetAsSeries(weekly,true);
   int h1_count=CopyRates(_Symbol,PERIOD_H1,1,requested,h1);
   int h4_count=CopyRates(_Symbol,PERIOD_H4,1,requested,h4);
   int m5_count=CopyRates(_Symbol,PERIOD_M5,1,MathMax(32,InpHumanAtrPeriod+2),m5);
   int day_count=CopyRates(_Symbol,PERIOD_D1,1,1,daily);
   int week_count=CopyRates(_Symbol,PERIOD_W1,1,1,weekly);
   if(h1_count<requested || h4_count<requested ||
      m5_count<InpHumanAtrPeriod+1 || day_count!=1 || week_count!=1)
      return false;

   if(!HumanRateRange(h1,InpHumanRangeBars,context.h1_range_low,
                     context.h1_range_high) ||
      !HumanRateRange(h4,InpHumanRangeBars,context.h4_range_low,
                     context.h4_range_high))
      return false;
   if(!HumanConfirmedPivotStructure(h1,InpHumanPivotStrength,
                                    context.h1_structure,
                                    context.h1_pivot_high,
                                    context.h1_pivot_low) ||
      !HumanConfirmedPivotStructure(h4,InpHumanPivotStrength,
                                    context.h4_structure,
                                    context.h4_pivot_high,
                                    context.h4_pivot_low))
      return false;
   double h1_atr=HumanAtrFromRates(h1,InpHumanAtrPeriod);
   double h4_atr=HumanAtrFromRates(h4,InpHumanAtrPeriod);
   double m5_atr=HumanAtrFromRates(m5,InpHumanAtrPeriod);
   if(h1_atr<=0.0 || h4_atr<=0.0 || m5_atr<=0.0)
      return false;

   context.h1_range_location=(entry-context.h1_range_low)/
                             (context.h1_range_high-context.h1_range_low);
   context.h4_range_location=(entry-context.h4_range_low)/
                             (context.h4_range_high-context.h4_range_low);
   context.h1_aligned=(context.h1_structure*direction>0);
   context.h4_aligned=(context.h4_structure*direction>0);
   context.previous_day_high=daily[0].high;
   context.previous_day_low=daily[0].low;
   context.previous_week_high=weekly[0].high;
   context.previous_week_low=weekly[0].low;
   if(!HumanAsiaRange(decision_server_time,context.asia_low,context.asia_high))
      return false;

   double partial_open=0.0;
   double partial_high=0.0;
   double partial_low=0.0;
   double partial_close=0.0;
   if(!BuildPartialHtfFromClosedM5(PERIOD_H1,decision_server_time,
                                   partial_open,partial_high,partial_low,
                                   partial_close))
      return false;
   context.partial_h1_body_atr=MathAbs(partial_close-partial_open)/h1_atr;
   if(!BuildPartialHtfFromClosedM5(PERIOD_H4,decision_server_time,
                                   partial_open,partial_high,partial_low,
                                   partial_close))
      return false;
   context.partial_h4_body_atr=MathAbs(partial_close-partial_open)/h4_atr;
   context.confirmation_body_atr=
      MathAbs(confirmation_bar.close-confirmation_bar.open)/m5_atr;
   context.directional_run_bars=HumanDirectionalRunBars(m5,direction);
   context.h1_extension_atr=(direction>0 ?
      MathMax(0.0,entry-context.h1_range_high)/h1_atr :
      MathMax(0.0,context.h1_range_low-entry)/h1_atr);
   context.h4_extension_atr=(direction>0 ?
      MathMax(0.0,entry-context.h4_range_high)/h4_atr :
      MathMax(0.0,context.h4_range_low-entry)/h4_atr);

   double nearest_distance=0.0;
   HumanAddDirectionalPool(direction,entry,context.previous_day_high,"PDH",
                           nearest_distance,context.nearest_pool_price,
                           context.nearest_pool_type,context.directional_pool_count);
   HumanAddDirectionalPool(direction,entry,context.previous_day_low,"PDL",
                           nearest_distance,context.nearest_pool_price,
                           context.nearest_pool_type,context.directional_pool_count);
   HumanAddDirectionalPool(direction,entry,context.previous_week_high,"PWH",
                           nearest_distance,context.nearest_pool_price,
                           context.nearest_pool_type,context.directional_pool_count);
   HumanAddDirectionalPool(direction,entry,context.previous_week_low,"PWL",
                           nearest_distance,context.nearest_pool_price,
                           context.nearest_pool_type,context.directional_pool_count);
   HumanAddDirectionalPool(direction,entry,context.asia_high,"ASIA_HIGH",
                           nearest_distance,context.nearest_pool_price,
                           context.nearest_pool_type,context.directional_pool_count);
   HumanAddDirectionalPool(direction,entry,context.asia_low,"ASIA_LOW",
                           nearest_distance,context.nearest_pool_price,
                           context.nearest_pool_type,context.directional_pool_count);
   HumanAddDirectionalPool(direction,entry,context.h1_pivot_high,"H1_PIVOT_HIGH",
                           nearest_distance,context.nearest_pool_price,
                           context.nearest_pool_type,context.directional_pool_count);
   HumanAddDirectionalPool(direction,entry,context.h1_pivot_low,"H1_PIVOT_LOW",
                           nearest_distance,context.nearest_pool_price,
                           context.nearest_pool_type,context.directional_pool_count);
   HumanAddDirectionalPool(direction,entry,context.h4_pivot_high,"H4_PIVOT_HIGH",
                           nearest_distance,context.nearest_pool_price,
                           context.nearest_pool_type,context.directional_pool_count);
   HumanAddDirectionalPool(direction,entry,context.h4_pivot_low,"H4_PIVOT_LOW",
                           nearest_distance,context.nearest_pool_price,
                           context.nearest_pool_type,context.directional_pool_count);

   double risk=MathAbs(entry-stop);
   if(risk<=_Point)
      return false;
   context.nearest_pool_pips=nearest_distance/PipSize();
   context.room_r=nearest_distance/risk;
   context.room_to_target=(nearest_distance>0.0 && context.room_r>=InpTargetRR);
   context.spread_to_risk=spread/risk;

   HumanCountSweptPool(direction,sweep_high,sweep_low,sweep_close,
                       context.previous_day_high,context.external_swept_count);
   HumanCountSweptPool(direction,sweep_high,sweep_low,sweep_close,
                       context.previous_day_low,context.external_swept_count);
   HumanCountSweptPool(direction,sweep_high,sweep_low,sweep_close,
                       context.previous_week_high,context.external_swept_count);
   HumanCountSweptPool(direction,sweep_high,sweep_low,sweep_close,
                       context.previous_week_low,context.external_swept_count);
   HumanCountSweptPool(direction,sweep_high,sweep_low,sweep_close,
                       context.asia_high,context.external_swept_count);
   HumanCountSweptPool(direction,sweep_high,sweep_low,sweep_close,
                       context.asia_low,context.external_swept_count);
   HumanCountSweptPool(direction,sweep_high,sweep_low,sweep_close,
                       context.h1_pivot_high,context.external_swept_count);
   HumanCountSweptPool(direction,sweep_high,sweep_low,sweep_close,
                       context.h1_pivot_low,context.external_swept_count);
   HumanCountSweptPool(direction,sweep_high,sweep_low,sweep_close,
                       context.h4_pivot_high,context.external_swept_count);
   HumanCountSweptPool(direction,sweep_high,sweep_low,sweep_close,
                       context.h4_pivot_low,context.external_swept_count);
   context.external_sweep=(context.external_swept_count>0);

   if(context.directional_pool_count==0)
      context.state=HUMAN_CONTEXT_NO_DIRECTIONAL_TARGET;
   else if(context.h1_extension_atr>0.0 || context.h4_extension_atr>0.0)
      context.state=HUMAN_CONTEXT_DIRECTIONAL_EXHAUSTION;
   else if(context.h1_structure*direction<0 && context.h4_structure*direction<0)
      context.state=HUMAN_CONTEXT_STRUCTURE_CONFLICT;
   else if(!context.room_to_target)
      context.state=HUMAN_CONTEXT_INSUFFICIENT_ROOM;
   else if(context.external_sweep)
      context.state=HUMAN_CONTEXT_EXTERNAL_SWEEP_WITH_ROOM;
   else
      context.state=HUMAN_CONTEXT_INTERNAL_SWEEP_WITH_ROOM;
   context.valid=true;
   return true;
  }

#endif
