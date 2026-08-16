//+------------------------------------------------------------------+
//| SNR_SRLevels.mq5                                                 |
//| Whole / half / quarter round-number levels. Visual overlay.      |
//+------------------------------------------------------------------+
#property copyright "EA_SonicR_PVSRA"
#property link      "https://www.mql5.com"
#property version   "1.00"
#property indicator_chart_window
#property indicator_buffers 0
#property indicator_plots   0

#include "../Include/SNR_Types.mqh"
#include "../Include/SNR_SRLevels.mqh"

input double InpRoundWhole=10.0;
input int    InpLevelsEachSide=6;
input bool   InpDrawQuarters=true;

const string PREFIX="SNR_SR_";

void SnrSrDelete()
  {
   const int total=ObjectsTotal(0,0,-1);
   for(int i=total-1;i>=0;i--)
     {
      const string name=ObjectName(0,i,0,-1);
      if(StringFind(name,PREFIX)==0)
         ObjectDelete(0,name);
     }
  }

void SnrSrDraw(const double anchor)
  {
   double levels[];
   int kinds[];
   const int n=SnrCollectVisibleLevels(anchor,InpRoundWhole,InpLevelsEachSide,InpDrawQuarters,levels,kinds);
   SnrSrDelete();
   for(int i=0;i<n;i++)
     {
      const string name=PREFIX+IntegerToString(i);
      if(!ObjectCreate(0,name,OBJ_HLINE,0,0,levels[i]))
         continue;
      color clr=clrDimGray;
      ENUM_LINE_STYLE style=STYLE_DOT;
      int width=1;
      if(kinds[i]==SNR_SR_WHOLE)
        {
         clr=clrDarkOrange;
         style=STYLE_SOLID;
         width=2;
        }
      else if(kinds[i]==SNR_SR_HALF)
        {
         clr=clrSteelBlue;
         style=STYLE_DASH;
         width=1;
        }
      ObjectSetInteger(0,name,OBJPROP_COLOR,clr);
      ObjectSetInteger(0,name,OBJPROP_STYLE,style);
      ObjectSetInteger(0,name,OBJPROP_WIDTH,width);
      ObjectSetInteger(0,name,OBJPROP_BACK,true);
      ObjectSetInteger(0,name,OBJPROP_SELECTABLE,false);
      ObjectSetInteger(0,name,OBJPROP_HIDDEN,true);
     }
  }

int OnInit()
  {
   if(InpRoundWhole<=0.0 || InpLevelsEachSide<1)
      return(INIT_PARAMETERS_INCORRECT);
   IndicatorSetString(INDICATOR_SHORTNAME,
                      StringFormat("SNR S/R whole=%.2f",InpRoundWhole));
   return(INIT_SUCCEEDED);
  }

void OnDeinit(const int reason)
  {
   SnrSrDelete();
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
   if(rates_total<2)
      return(0);
   ArraySetAsSeries(close,true);
   const double anchor=(rates_total>1 ? close[1] : close[0]);
   if(anchor>0.0)
      SnrSrDraw(anchor);
   return(rates_total);
  }
//+------------------------------------------------------------------+
