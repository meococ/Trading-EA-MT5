//+------------------------------------------------------------------+
//| SNR_PVSRA.mq5                                                    |
//| Tick-volume vs recent average. Rising/climax colors reconstructed.|
//+------------------------------------------------------------------+
#property copyright "EA_SonicR_PVSRA"
#property link      "https://www.mql5.com"
#property version   "1.00"
#property indicator_separate_window
#property indicator_buffers 2
#property indicator_plots   1
#property indicator_minimum 0

#property indicator_label1  "Tick volume"
#property indicator_type1   DRAW_COLOR_HISTOGRAM
#property indicator_color1  clrSilver,clrDodgerBlue,clrGold,clrTomato
#property indicator_style1  STYLE_SOLID
#property indicator_width1  2

#include "../Include/SNR_Types.mqh"
#include "../Include/SNR_PVSRA.mqh"

input int    InpVolAvgBars=10;
input double InpVolRisingMult=1.5;
input double InpVolClimaxMult=2.0;

double g_vol[];
double g_color[];

int OnInit()
  {
   if(InpVolAvgBars<2 || InpVolRisingMult<=0.0 || InpVolClimaxMult<InpVolRisingMult)
      return(INIT_PARAMETERS_INCORRECT);
   SetIndexBuffer(0,g_vol,INDICATOR_DATA);
   SetIndexBuffer(1,g_color,INDICATOR_COLOR_INDEX);
   ArraySetAsSeries(g_vol,true);
   ArraySetAsSeries(g_color,true);
   PlotIndexSetDouble(0,PLOT_EMPTY_VALUE,EMPTY_VALUE);
   IndicatorSetString(INDICATOR_SHORTNAME,
                      StringFormat("SNR PVSRA avg%d rise%.1f clim%.1f",
                                   InpVolAvgBars,InpVolRisingMult,InpVolClimaxMult));
   IndicatorSetInteger(INDICATOR_DIGITS,0);
   return(INIT_SUCCEEDED);
  }

int OnCalculate(const int rates_total,
                const int prev_calculated,
                const datetime &time[],
                const double &open[],
                const double &high[],
                const double &low[],
                const double &close[],
                const long &tick_volume[],
                const long &volume[],
                const int &spread[])
  {
   if(rates_total<=InpVolAvgBars)
      return(0);
   ArraySetAsSeries(tick_volume,true);
   const int start=(prev_calculated>InpVolAvgBars ? rates_total-prev_calculated : rates_total-InpVolAvgBars-1);
   for(int i=start;i>=0;i--)
     {
      if(i+InpVolAvgBars>=rates_total)
        {
         g_vol[i]=EMPTY_VALUE;
         g_color[i]=0.0;
         continue;
        }
      double sum=0.0;
      bool ok=true;
      for(int k=1;k<=InpVolAvgBars;k++)
        {
         const double prior=(double)tick_volume[i+k];
         if(prior<0.0)
           {
            ok=false;
            break;
           }
         sum+=prior;
        }
      const double avg=(ok ? sum/(double)InpVolAvgBars : 0.0);
      const double vol=(double)tick_volume[i];
      g_vol[i]=vol;
      const int cls=SnrClassifyVolume(vol,avg,InpVolRisingMult,InpVolClimaxMult);
      if(cls==SNR_PVSRA_CLIMAX)
         g_color[i]=2.0;
      else if(cls==SNR_PVSRA_RISING)
         g_color[i]=1.0;
      else if(cls==SNR_PVSRA_LOW)
         g_color[i]=3.0;
      else
         g_color[i]=0.0;
     }
   return(rates_total);
  }
//+------------------------------------------------------------------+
