//+-------------------------------------------------------------------------------------------+
//|                                                                                           |
//|                                SonicR Filled Dragon-Trend.mq4                             |
//|                                                                                           |
//+-------------------------------------------------------------------------------------------+ 
#property copyright "Copyright @ 2013 traderathome"
#property link      "email: traderathome@msn.com"

/*---------------------------------------------------------------------------------------------
Overview, _v1:

This indicator displays both the SonicR Dragon and the SonicR Trend.  The SonicR Dragon is 
color filled and is based upon 34 EMA averaging of close prices with high/low prices defining 
outer edges.  The SonicR Trend is based upon 89 EMA averaging of close prices. 

1. About color filling the Dragon -
   Histogram bars and MA Edge_Widths are used in the construction of the color fill.  Zooming  
   in on a chart requires these components be made wider to prevent spaces appearing between 
   them.  Zooming out on a chart requires these components be made narrower to prevent the 
   Dragon from being too wide.  Use the "Chart_Zoom_123456" inputs to control adjustments to 
   the Dragon as you zoom in/out on charts.  Apply "1" to "6" depending on the zoom setting
   the chart has been set to.  If the setting for "Chart_Zoom_123456" is not between 1-6 it
   defaults to "3". 
    
2. Setting the Zoom -  
   MT4 has six chart zoom settings, referred to in this indicator from narrowest bars to
   widest bars as number selections 1 thru 6.  Use the "Chart_Zoom_123456" input to set 
   the widths of the bars.  Use "1 or 2" for zoomed out charts (thinner bars).   Use "3" for 
   the Mt4 default chart chart zoom.  Use "4,5, or 6" for zoomed in charts (wider bars). 
      
   The proper sequence to follow is....
   A. First, enter the "Chart_Zoom_123456" input you want.
   B. Second, use the MT4 icons "+/-" to zoom the chart in/out, per the input you made.
   C. Switch chart TF once to reset the chart to your "Chart_Zoom_123456" input.
   
   You can slave the SonicR PVA Candles and SonicR PVA Volumes indicators to obey this 
   "Chart_Zoom_123456" input, so when you zoom in/out on a chart you only have to change 
   the zoom setting in this indicator, and not the other two also.  To accomplish slaving
   set "Chart_Zoom_0123456" to "0" in these other indicators.  The SonicR Filled Dragon 
   indicator does not have to be turned on to control indicators slaved to it, it only has 
   to be included in the chart list of indicators. 
   
   The SonicR Control Panel special Bid Line and Bid Dot use different hard code values
   that depend on the chart zoom setting, which this indicator provides.  
   
3. On/Off & Display Range-   
   The indicator can be turned on/off without having to remove it from the chart, thereby 
   preserving your chart settings.You can select a maximum TF for the display of this 
   indicator, so it automatically will not display on a chart TF that is higher.    

4. Set to Display Beneath Candles-
   Because the Dragon is solid it will obscure candles not properly set to the foreground.
   Therefore, be sure that chart Properties/Common tab/"Chart on foreground" is checked, so 
   that the price candles are displayed on top of the Solid Dragon.
   
Changes from Solid Dragon-Trend released 05-01-2012 to release 05-25-2013 of this new indy:   
01 - Removed the automatic zoom feature.
02 - Revised the manual zoom feature, which now can also control the bar width settings in 
     the SonicR PVA Candles and SonicR PVA Volumes indicators.  It also controls spacing of
     the special Bid Line and Bid Dot in the SonicR Control Panel.
03 - Removed ability to show M15 Dragon-Trend configurations on other TF charts.
04 - Added additonal Dragon center area line to backdrop & highlight the centerline.
05 - Removed Display_Min_TF feature (unnecessary).
                                 
                                                                   - Traderathome, 05-25-2013
----------------------------------------------------------------------------------------------
Suggested Colors             White Chart        Black Chart        Remarks  
 
indicator_color1-2           C'221,238,255'     C'030,032,072'     H/L Histo Fill
indicator_color3-4           C'210,233,255'     C'034,037,083'     H/L MA Fill
indicator_color5             C'240,249,255'     C'020,020,020'     Center Highlighter 
indicator_color6             C'032,143,255'     C'079,102,198'     Center Line
indicator_color7             CLR_NONE           CLR_NONE           Trend Line Highligher
indicator_color8             Black              MediumVioletRed    Trend Line                                                                                                     
---------------------------------------------------------------------------------------------*/


//+-------------------------------------------------------------------------------------------+
//| Indicator Global Inputs                                                                   |                                                        
//+-------------------------------------------------------------------------------------------+ 
#property indicator_chart_window
#property indicator_buffers  8

//Dragon-
#property indicator_color1   C'221,238,255'   //high histo fill
#property indicator_color2   C'221,238,255'   //low histo fill
#property indicator_color3   C'210,233,255'   //high ma fill    
#property indicator_color4   C'210,233,255'   //low ma fill
#property indicator_color5   C'240,249,255'   //center area
#property indicator_color6   C'032,143,255'   //center line

#property indicator_style1   STYLE_SOLID
#property indicator_style2   STYLE_SOLID
#property indicator_style3   STYLE_SOLID
#property indicator_style4   STYLE_SOLID 
#property indicator_style5   STYLE_SOLID 
#property indicator_style6   STYLE_SOLID 

#property indicator_width1   3
#property indicator_width2   3
#property indicator_width3   3
#property indicator_width4   3  
#property indicator_width5   5
#property indicator_width6   1

//Trend-
#property indicator_color7   CLR_NONE 
#property indicator_color8   Black           
#property indicator_width7   1
#property indicator_width8   1
#property indicator_style7   STYLE_SOLID       
#property indicator_style8   STYLE_SOLID 
 
//global external inputs
extern bool   Indicator_On                    = true;
extern int    Chart_Zoom_123456               = 3;
extern bool   Trend_On                        = true;
extern int    Display_Max_TF                  = 43200;
extern string TF_Choices_H1_H4_D_W_M          = "60   240  1440  10080  43200";

//Global Buffers and Variables
bool   Deinitialized;
int    i,BarShift,counted_bars,limit;
string ShortName;

//Dragon-
int    Bar_Width,Bands;
double DragonHigh[],DragonLow[],DragonTop[],DragonBot[],DragonCntrArea[],DragonCntrLine[];
string Dragontype                      = "ema";
int    Dragon_Period                   = 34;
int    Dragon_Type                     = 1;

//Trend-
double Trend1[],Trend2[];
string Trendtype                       = "ema";
int    Trend_Off_Std_Dragon_012        = 1;
int    Trend_Period                    = 89;   
int    Trend_Type                      = 1;

//Global Variable Controlling Bar Widths 
string Zoom = "Zoom_Setting";
double B;
string Bar = "Bar_Setting";

/*General notes:
MAType  = 0=SMA,1=EMA,2=SMMA,3=LWMA
MAPrice = 0=CLOSE,1=OPEN,2=HIGH,3=LOW,4=MEDIAN,5=PP,6=WEIGHT
*/
//+-------------------------------------------------------------------------------------------+
//| Indicator Initialization                                                                  |                                                        
//+-------------------------------------------------------------------------------------------+      
int init()
  {
  Deinitialized = false;

  //Manually Adjust Width   
    {                
    if(Chart_Zoom_123456 < 1 || Chart_Zoom_123456 >6) {Chart_Zoom_123456 = 3;}                  
          if(Chart_Zoom_123456 == 1) {Bar_Width = 1; Bands = 1; B = 1;}           
    else {if(Chart_Zoom_123456 == 2) {Bar_Width = 2; Bands = 1; B = 2;}      
    else {if(Chart_Zoom_123456 == 3) {Bar_Width = 3; Bands = 3; B = 2;}
    else {if(Chart_Zoom_123456 == 4) {Bar_Width = 5; Bands = 7; B = 3;}
    else {if(Chart_Zoom_123456 == 5) {Bar_Width = 9; Bands = 14; B = 6;}
    else {if(Chart_Zoom_123456 == 6) {Bar_Width = 17; Bands = 26; B = 13;} }}}}}
    }
    
  //Set bar widths for candles and volume as a GV
  GlobalVariableSet(Zoom, Chart_Zoom_123456);
  GlobalVariableSet(Bar, B);
       
  //Indicators- Dragon           
  //Area fill either side of center              
  SetIndexBuffer(0, DragonHigh);
  SetIndexStyle(0, DRAW_HISTOGRAM, 0, Bar_Width);
  SetIndexBuffer(1, DragonLow);
  SetIndexStyle(1, DRAW_HISTOGRAM, 0, Bar_Width);   
  //Area fill top and bottom
  SetIndexBuffer(2, DragonTop);
  SetIndexStyle(2, DRAW_LINE, 0, Bands);
  SetIndexBuffer(3, DragonBot);
  SetIndexStyle(3, DRAW_LINE, 0, Bands);   
  //Center line Area    
  SetIndexBuffer(4, DragonCntrArea); 
  SetIndexStyle(4, DRAW_LINE); 
  //Center line    
  SetIndexBuffer(5, DragonCntrLine); 
  SetIndexStyle(5, DRAW_LINE);
         
  //Indicators- Trend
  if(Trend_On)
    {                                                  
    SetIndexBuffer(6, Trend1);                     
    SetIndexStyle(6, DRAW_LINE);
    SetIndexBuffer(7, Trend2);                     
    SetIndexStyle(7, DRAW_LINE);             
    }
      
  //Indicator ShortName
  ShortName = "SonicR Filled Dragon";
  if(!Trend_On)
    {
    ShortName = ShortName + " ["+Dragon_Period+Dragontype
    +" - Trend is off]  ";              
    }                  
  else
    {
    ShortName = ShortName + " ["+Dragon_Period+Dragontype
    +" - "+Trend_Period+Trendtype+"]  ";
    }      
  IndicatorShortName (ShortName);
                                                                                              
  return(0);
  }

//+-------------------------------------------------------------------------------------------+
//| Indicator De-initialization                                                               |                                                        
//+-------------------------------------------------------------------------------------------+      
int deinit()
  {         
  return(0);
  }

//+-------------------------------------------------------------------------------------------+
//| Indicator Start                                                                           |                                                        
//+-------------------------------------------------------------------------------------------+     
int start()
  {
  //If indicator is "Off" or chart TF is out of range deinitialize only once, not every tick.  
  if((!Indicator_On) || (Period() > Display_Max_TF))    
    {
    if (!Deinitialized) {deinit(); Deinitialized = true;}
    return(0);
    }

  //Otherwise indicator is "On" & chart TF is in display range, so proceed.      
  Deinitialized = false;
  
  //Confirm range of chart bars for calculations   
  //check for possible errors
  counted_bars = IndicatorCounted();
  if(counted_bars < 0)  return(-1);     
  //last counted bar will be recounted
  if(counted_bars > 0) counted_bars--;    
  limit = Bars - counted_bars;
  
  //Begin the loop of calculations for the range of chart bars. 
  for(i = limit - 1; i >= 0; i--)                        
    {
    //Dragon        
    BarShift = iBarShift(NULL,NULL,Time[i],true); 
    DragonHigh[i] = iMA(NULL,NULL,Dragon_Period,0,Dragon_Type,PRICE_HIGH,BarShift);   
    DragonLow[i]  = iMA(NULL,NULL,Dragon_Period,0,Dragon_Type,PRICE_LOW,BarShift);                    
    DragonTop[i]  = iMA(NULL,NULL,Dragon_Period,0,Dragon_Type,PRICE_HIGH,BarShift);                           
    DragonBot[i]  = iMA(NULL,NULL,Dragon_Period,0,Dragon_Type,PRICE_LOW,BarShift);     
    DragonCntrArea[i] = iMA(NULL,NULL,Dragon_Period,0,Dragon_Type,PRICE_CLOSE,BarShift);
    DragonCntrLine[i] = iMA(NULL,NULL,Dragon_Period,0,Dragon_Type,PRICE_CLOSE,BarShift);         
    //Trend                      
    if(Trend_On)
      { 
      BarShift = iBarShift(NULL,NULL,Time[i],true);                 
       Trend1[i]= iMA(NULL,NULL,Trend_Period,0,Trend_Type,PRICE_CLOSE,BarShift);
      Trend2[i]= iMA(NULL,NULL,Trend_Period,0,Trend_Type,PRICE_CLOSE,BarShift);            
      }                                                                                    
    }
                                                                                                                    
  return(0);
  }

//+-------------------------------------------------------------------------------------------+
//| Indicator End                                                                             |                                                        
//+-------------------------------------------------------------------------------------------+       

