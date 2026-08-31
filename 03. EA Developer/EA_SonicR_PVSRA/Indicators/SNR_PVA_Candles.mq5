//+------------------------------------------------------------------+
//| SNR_PVA_Candles.mq5                                              |
//| Reconstructed PVA colors (TAH: rising + climax). Not an entry.   |
//+------------------------------------------------------------------+
#property copyright "EA_SonicR_PVSRA"
#property link      "https://www.mql5.com"
#property version   "1.20"
#property indicator_chart_window
#property indicator_buffers 5
#property indicator_plots   1

#property indicator_label1  "PVA"
#property indicator_type1   DRAW_COLOR_CANDLES
#property indicator_color1  clrSilver,clrDodgerBlue,clrTomato,clrGold,clrOrchid
#property indicator_width1  1

#include "../Include/SNR_Types.mqh"
#include "../Include/SNR_PVSRA.mqh"

input int    InpVolAvgBars=10;
input double InpVolRisingMult=1.5;
input double InpVolClimaxMult=2.0;

double g_open[];
double g_high[];
double g_low[];
double g_close[];
double g_color[];

int OnInit()
  {
   if(InpVolAvgBars<2 || InpVolRisingMult<=0.0 || InpVolClimaxMult<InpVolRisingMult)
      return(INIT_PARAMETERS_INCORRECT);
   SetIndexBuffer(0,g_open,INDICATOR_DATA);
   SetIndexBuffer(1,g_high,INDICATOR_DATA);
   SetIndexBuffer(2,g_low,INDICATOR_DATA);
   SetIndexBuffer(3,g_close,INDICATOR_DATA);
   SetIndexBuffer(4,g_color,INDICATOR_COLOR_INDEX);
   ArraySetAsSeries(g_open,true);
   ArraySetAsSeries(g_high,true);
   ArraySetAsSeries(g_low,true);
   ArraySetAsSeries(g_close,true);
   ArraySetAsSeries(g_color,true);
   IndicatorSetString(INDICATOR_SHORTNAME,
                      StringFormat("SNR PVA avg%d (read-only)",InpVolAvgBars));
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
   if(rates_total<=InpVolAvgBars+1)
      return(0);
   ArraySetAsSeries(open,true);
   ArraySetAsSeries(high,true);
   ArraySetAsSeries(low,true);
   ArraySetAsSeries(close,true);
   ArraySetAsSeries(tick_volume,true);
   const int start=(prev_calculated>InpVolAvgBars ? rates_total-prev_calculated : rates_total-InpVolAvgBars-2);
   for(int i=start;i>=0;i--)
     {
      g_open[i]=open[i];
      g_high[i]=high[i];
      g_low[i]=low[i];
      g_close[i]=close[i];
      if(i+InpVolAvgBars>=rates_total)
        {
         g_color[i]=0.0;
         continue;
        }
      double sum=0.0;
      double max_sv=0.0;
      bool ok=true;
      for(int k=1;k<=InpVolAvgBars;k++)
        {
         const double vol=(double)tick_volume[i+k];
         const double sv=(high[i+k]-low[i+k])*vol;
         if(vol<0.0 || sv<0.0)
           {
            ok=false;
            break;
           }
         sum+=vol;
         if(sv>max_sv)
            max_sv=sv;
        }
      if(!ok || sum<=0.0)
        {
         g_color[i]=0.0;
         continue;
        }
      const double avg=sum/(double)InpVolAvgBars;
      const double vol0=(double)tick_volume[i];
      int cls=SnrClassifyVolume(vol0,avg,InpVolRisingMult,InpVolClimaxMult);
      const double sv0=(high[i]-low[i])*vol0;
      if(max_sv>0.0 && sv0>=max_sv)
         cls=SNR_PVSRA_CLIMAX;
      const bool bull=(close[i]>=open[i]);
      if(cls==SNR_PVSRA_CLIMAX)
         g_color[i]=(bull ? 3.0 : 4.0);
      else if(cls==SNR_PVSRA_RISING)
         g_color[i]=(bull ? 1.0 : 2.0);
      else
         g_color[i]=0.0;
     }
   return(rates_total);
  }
//+------------------------------------------------------------------+
