//+------------------------------------------------------------------+
//| SNR_Dragon.mq5                                                   |
//| EMA34 high / close / low band. Visual overlay.                   |
//+------------------------------------------------------------------+
#property copyright "EA_SonicR_PVSRA"
#property link      "https://www.mql5.com"
#property version   "1.00"
#property indicator_chart_window
#property indicator_buffers 3
#property indicator_plots   3

#property indicator_label1  "Dragon High"
#property indicator_type1   DRAW_LINE
#property indicator_color1  clrSeaGreen
#property indicator_style1  STYLE_SOLID
#property indicator_width1  1

#property indicator_label2  "Dragon Mid"
#property indicator_type2   DRAW_LINE
#property indicator_color2  clrGoldenrod
#property indicator_style2  STYLE_SOLID
#property indicator_width2  2

#property indicator_label3  "Dragon Low"
#property indicator_type3   DRAW_LINE
#property indicator_color3  clrIndianRed
#property indicator_style3  STYLE_SOLID
#property indicator_width3  1

input int InpDragonPeriod=34;

double g_high[];
double g_mid[];
double g_low[];
int    g_h_high=INVALID_HANDLE;
int    g_h_mid=INVALID_HANDLE;
int    g_h_low=INVALID_HANDLE;

int OnInit()
  {
   if(InpDragonPeriod<2)
      return(INIT_PARAMETERS_INCORRECT);
   SetIndexBuffer(0,g_high,INDICATOR_DATA);
   SetIndexBuffer(1,g_mid,INDICATOR_DATA);
   SetIndexBuffer(2,g_low,INDICATOR_DATA);
   ArraySetAsSeries(g_high,true);
   ArraySetAsSeries(g_mid,true);
   ArraySetAsSeries(g_low,true);
   PlotIndexSetDouble(0,PLOT_EMPTY_VALUE,EMPTY_VALUE);
   PlotIndexSetDouble(1,PLOT_EMPTY_VALUE,EMPTY_VALUE);
   PlotIndexSetDouble(2,PLOT_EMPTY_VALUE,EMPTY_VALUE);
   IndicatorSetString(INDICATOR_SHORTNAME,"SNR Dragon EMA"+IntegerToString(InpDragonPeriod));
   g_h_high=iMA(_Symbol,_Period,InpDragonPeriod,0,MODE_EMA,PRICE_HIGH);
   g_h_mid=iMA(_Symbol,_Period,InpDragonPeriod,0,MODE_EMA,PRICE_CLOSE);
   g_h_low=iMA(_Symbol,_Period,InpDragonPeriod,0,MODE_EMA,PRICE_LOW);
   if(g_h_high==INVALID_HANDLE || g_h_mid==INVALID_HANDLE || g_h_low==INVALID_HANDLE)
      return(INIT_FAILED);
   return(INIT_SUCCEEDED);
  }

void OnDeinit(const int reason)
  {
   if(g_h_high!=INVALID_HANDLE)
      IndicatorRelease(g_h_high);
   if(g_h_mid!=INVALID_HANDLE)
      IndicatorRelease(g_h_mid);
   if(g_h_low!=INVALID_HANDLE)
      IndicatorRelease(g_h_low);
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
   if(rates_total<InpDragonPeriod || g_h_high==INVALID_HANDLE ||
      g_h_mid==INVALID_HANDLE || g_h_low==INVALID_HANDLE)
      return(0);
   const int to_copy=(prev_calculated>0 ? rates_total-prev_calculated+1 : rates_total);
   if(CopyBuffer(g_h_high,0,0,to_copy,g_high)<to_copy)
      return(0);
   if(CopyBuffer(g_h_mid,0,0,to_copy,g_mid)<to_copy)
      return(0);
   if(CopyBuffer(g_h_low,0,0,to_copy,g_low)<to_copy)
      return(0);
   return(rates_total);
  }
//+------------------------------------------------------------------+
