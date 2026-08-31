//+------------------------------------------------------------------+
//| SNR_Trend.mq5                                                    |
//| EMA89 close with slope-colored line. Visual overlay.             |
//+------------------------------------------------------------------+
#property copyright "EA_SonicR_PVSRA"
#property link      "https://www.mql5.com"
#property version   "1.00"
#property indicator_chart_window
#property indicator_buffers 2
#property indicator_plots   1

#property indicator_label1  "Trend EMA89"
#property indicator_type1   DRAW_COLOR_LINE
#property indicator_color1  clrDodgerBlue,clrTomato,clrSilver
#property indicator_style1  STYLE_SOLID
#property indicator_width1  2

input int InpTrendPeriod=89;
input int InpSlopeBars=3;

double g_ema[];
double g_color[];
int    g_handle=INVALID_HANDLE;

int OnInit()
  {
   if(InpTrendPeriod<2 || InpSlopeBars<1)
      return(INIT_PARAMETERS_INCORRECT);
   SetIndexBuffer(0,g_ema,INDICATOR_DATA);
   SetIndexBuffer(1,g_color,INDICATOR_COLOR_INDEX);
   ArraySetAsSeries(g_ema,true);
   ArraySetAsSeries(g_color,true);
   PlotIndexSetDouble(0,PLOT_EMPTY_VALUE,EMPTY_VALUE);
   IndicatorSetString(INDICATOR_SHORTNAME,"SNR Trend EMA"+IntegerToString(InpTrendPeriod));
   g_handle=iMA(_Symbol,_Period,InpTrendPeriod,0,MODE_EMA,PRICE_CLOSE);
   if(g_handle==INVALID_HANDLE)
      return(INIT_FAILED);
   return(INIT_SUCCEEDED);
  }

void OnDeinit(const int reason)
  {
   if(g_handle!=INVALID_HANDLE)
      IndicatorRelease(g_handle);
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
   if(rates_total<InpTrendPeriod+InpSlopeBars || g_handle==INVALID_HANDLE)
      return(0);
   if(CopyBuffer(g_handle,0,0,rates_total,g_ema)<rates_total)
      return(0);
   const int limit=(prev_calculated>0 ? rates_total-prev_calculated+1 : rates_total-InpSlopeBars);
   for(int i=0;i<limit;i++)
     {
      if(i+InpSlopeBars>=rates_total || g_ema[i]==EMPTY_VALUE || g_ema[i+InpSlopeBars]==EMPTY_VALUE)
        {
         g_color[i]=2.0;
         continue;
        }
      const double slope=g_ema[i]-g_ema[i+InpSlopeBars];
      if(slope>0.0)
         g_color[i]=0.0;
      else if(slope<0.0)
         g_color[i]=1.0;
      else
         g_color[i]=2.0;
     }
   return(rates_total);
  }
//+------------------------------------------------------------------+
