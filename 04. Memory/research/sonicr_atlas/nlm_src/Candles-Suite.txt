//+-------------------------------------------------------------------------------------------+
//|                                                                                           |
//|                                      Candles Suite.mq4                                    |
//|                                                      				                         |
//+-------------------------------------------------------------------------------------------+
#property copyright "Copyright @ 2015 traderathome and qFish"
#property link      "email: traderathome@msn.com"

/*---------------------------------------------------------------------------------------------
User Notes:

This indicator is coded to run on MT4 Build 600+.  It draws PVA (Price-Volume Analysis) bars
and candlesticks, as well as standard bars, candlesticks and Heiken-Ashi candles.  In the PVA
mode, an alert option signals when a "Climax" situation exists. Specific details follow.

PVA Bars & Candlesticks -
   The PVA bars and PVA candlesticks are used together with PVA volume for easy recognition of
   when special price and volume situations occur.  The special situations, or requirements for
   the colors used are as follows.

   Situation "Climax"
   Bars with volume >= 200% of the average volume of the 10 previous chart TFs, and bars
   where the product of candle spread x candle volume is >= the highest for the 10 previous
   chart time TFs.
   Default Colors:  Bull bars are green and bear bars are red.

   Situation "Volume Rising Above Average"
   Bars with volume >= 150% of the average volume of the 10 previous chart TFs.
   Default Colors:  Bull bars are blue and bear are blue-violet.

   PVA Color Options -
   There are three PVA color options provided....
     1. Simple:  Use this option for a simple PVA two color display based on Climax only
        situations (an option allows you to include "Rising" volume).  You can change any
        color.  To start, a shade of blue/red are input for the PVA bull/bear bars.
     2. Standard:  Use this option for the 4-color PVA display where you can change any
        color. To start, the traditional PVA colors are input.
     3. Default:  There are no inputs.  The traditional PVA four color display is
        hard coded.  You can easily return to this display anytime while preserving
        those changes you have made to the Simple and the Standard display options.

Selecting the Type of PVA Price Display -
   To display PVA set "__PVA_BAR_STD_HA_1234" to "1".  You can then choose a variety of
   PVA displays with the next input "__PVA_Bars_Candles_Bodies_123".  Input "1" to show a
   PVA bar chart.  Input "2" to show a PVA candlestick chart.  These bar and candlestick
   display on top of the solid color Price Band.  Input "3" to show only the PVA colored
   bodies as overlays on top of a standard MT4 bar or candlestick chart.  These bar and
   candlesticks will not be on top of the solid color Price Band.  Use one of the line
   Price Band options with them.  For these MT4 price draws select chart Properties, on the
   "Colors" tab give a color to "Line graph" and on the "Common" tab uncheck "Line chart"
   and check "Bar chart" or "Candlesticks".  If you make these changes to chart Properties,
   standard bars and candles produced by "__PVA_BAR_STD_HA_1234" equals "2" or "3" will
   still properly display, however, the HA candles produced by "__PVA_BAR_STD_HA_1234"
   equals "4" will not properly display.

The Alert -
   When displaying PVA Candles, this indicator includes a sound-text alert that triggers
   once per TF at the first qualification of the TF bar as a "Climax" situation.  Set both
   "Show_Alert_Label" and "Alert_On" inputs to "true" to operate the alert, and enter your
   "Broker_Name_In_Alert" to avoid confusion if simultaneously using multiple platforms.
   However, "Show_Alert_Label" and "Alert_On", should be set to "false" if also using the
   Volumes Suite indicator, which provides the same alert and is the one to use.

STD Bars, Candlesticks and HA Candles -
   Standard bars, candlesticks and Heiken-Ashi candles (modified to show price gaps) can be
   displayd.  Set "__PVA_BAR_STD_HA_1234" to "2" for bars.  Set "__PVA_BAR_STD_HA_1234"
   to "3" for standard candlesticks.  Set "__PVA_BAR_STD_HA_1234" to "4" for HA candles.
   Chart Properties should be set so no color is assigned to "Line chart" and so that
   "Line chart" is selected.  This prevents any MT4 price draw and allows this indicator
   to produce the various price draws.  If you change from this in order to use MT4 drawn
   prices (see PVA section above) the HA candles will not properly display.  To select colors
   for standard and HA candles and wicks use the input "Non_PVA_Color_Options_1_2_3_4_5".
   These selections color the up/down wicks a shade darker than the bull/bear candle colors,
   which improves the esthetics of the price display.  If you want monochromatic wicks, you
   can simply make "Apply_Wicks_OverRide_Color" be "true" and input the monochromatic color
   you desire at "__Wicks_OverRide_Color_Up" and "__Wicks_OverRide_Color_Dn".  These two
   inputs are the colors used to display standard bars.

                                                                    - Traderathome, 05-30-2015
-----------------------------------------------------------------------------------------------
Acknowledgements:
BetterVolume.mq4 - for initial "climax" candle code definition (BetterVolume_v1.4).

----------------------------------------------------------------------------------------------
Suggested Colors            White Chart        Black Chart        Remarks

indicator_color1            C'006,000,079'     C'140,140,140'     Candlewicks Up
indicator_color2            C'006,000,079''    C'140,140,140'     Candlewicks Dn
indicator_color3            C'159,160,162'     C'159,160,162'     Bull STD Candle
indicator_color4            C'106,106,117'     C'106,106,117'     Bear STD Candle
indicator_color5            C'067,100,214'     C'017,136,255'     Bull Rising
indicator_color6            C'154,038,232'     C'173,051,255'     Bear Rising
indicator_color7            C'000,166,100'     C'031,192,071'     Bull Climax
indicator_color8            C'214,012,083'     C'224,001,006'     Bear Climax

Note: Suggested colors coincide with the colors of the Volumes Suite indicator.
---------------------------------------------------------------------------------------------*/


//+-------------------------------------------------------------------------------------------+
//| Indicator Global Inputs                                                                   |
//+-------------------------------------------------------------------------------------------+
#property indicator_chart_window
#property indicator_buffers 8

#property indicator_color1  C'006,000,079'
#property indicator_color2  C'006,000,079'
#property indicator_color3  C'159,160,162'
#property indicator_color4  C'106,106,117'
#property indicator_color5  C'067,100,214'
#property indicator_color6  C'154,038,232'
#property indicator_color7  C'000,166,100'
#property indicator_color8  C'214,012,083'

//Global External Inputs
extern bool   Indicator_On                               = true;

extern string Select_Price_Style_to_Dispay               = "";
extern int    __PVA_BAR_STD_HA_1234                      = 1;

extern string For_PVA_Select_Style_and_Coloring          = "";
extern int    __PVA_Bars_Candles_Bodies_123              = 2;
extern int    __PVA_Color_Simple_Standard_Default_123    = 3;

extern string PVA_Simple_________________                = "";
extern color  __Simple_Wicks                             = C'006,000,079';
extern color  __Simple_Bull                              = C'159,160,162';
extern color  __Simple_Bear                              = C'106,106,117';
extern color  __Simple_PVA_Bull                          = C'067,100,214';
extern color  __Simple_PVA_Bear                          = C'214,012,083';
extern bool   __Include_Rising_Volume                    = false;

extern string PVA_Standard_______________                = "";
extern color  __Standard_Wicks                           = C'006,000,079';
extern color  __Standard_Bull                            = C'159,160,162';
extern color  __Standard_Bear                            = C'106,106,117';
extern color  __Standard_Bull_Rising                     = C'067,100,214';
extern color  __Standard_Bear_Rising                     = C'154,038,232';
extern color  __Standard_Bull_Climax                     = C'000,166,100';
extern color  __Standard_Bear_Climax                     = C'214,012,083';

extern string Alert_______________________               = "";
extern bool   Show_Alert_Label                           = false;
extern bool   Alert_On                                   = false;
extern string Broker_Name_In_Alert                       = "";

extern string Non_PVA_Bars______________                 = "";
extern color  __Bars_Color                               = C'006,000,079';

extern string Non_PVA_Candles___________                 = "";
extern int    Non_PVA_Color_Options_1_2_3_4_5            = 1;
extern bool   Apply_Wicks_OverRide_Color                 = false;
extern color  __Wicks_OverRide_Color_Up                  = C'006,000,079';
extern color  __Wicks_OverRide_Color_Dn                  = C'006,000,079';
extern color  __1_Wick_Up                                = C'054,071,139';
extern color  __1_Wick_Dn                                = C'149,000,074';
extern color  __1_Bull                                   = C'069,083,180';
extern color  __1_Bear                                   = C'204,036,095';
extern color  __2_Wick_Up                                = C'054,071,139';
extern color  __2_Wick_Dn                                = C'143,052,112';
extern color  __2_Bull                                   = C'069,083,180';
extern color  __2_Bear                                   = C'176,049,132';
extern color  __3_Wick_Up                                = C'046,118,089';
extern color  __3_Wick_Dn                                = C'149,000,074';
extern color  __3_Bull                                   = C'046,148,115';
extern color  __3_Bear                                   = C'204,036,095';
extern color  __4_Wick_Up                                = C'046,118,089';
extern color  __4_Wick_Dn                                = C'143,052,112';
extern color  __4_Bull                                   = C'046,148,115';
extern color  __4_Bear                                   = C'176,049,132';
extern color  __5_Wick_Up                                = C'006,000,079';
extern color  __5_Wick_Dn                                = C'006,000,079';
extern color  __5_Bull                                   = C'159,160,162';
extern color  __5_Bear                                   = C'106,106,117';

//Global Buffers and Variables
bool          Deinitialized;
color         Bull_Wick,Bear_Wick,Bull_Candle,Bear_Candle,
              Bull_Rising,Bear_Rising,Bull_Climax,Bear_Climax;
double        Bar1[],Candle1[],Bar2[],Candle2[],bodyHigh,bodyLow,
              RisingBull[],RisingBear[],ClimaxBull[],ClimaxBear[],
              av,Range,Value2,HiValue2,tempv2,high,low,open,close;
int           Chart_Scale,Bar_Width,va,i,j,counted_bars,limit,ExtCountedBars;
double        ExtMapBuffer1[], ExtMapBuffer2[], ExtMapBuffer3[], ExtMapBuffer4[];
double        haOpen, haHigh, haLow, haClose;

//Default PVA Colors
color         PVA_Normal_Wick  = C'006,000,079';
color         PVA_Normal_Bull  = C'159,160,162';
color         PVA_Normal_Bear  = C'106,106,117';
color         PVA_Bull_Rising  = C'067,100,214';
color         PVA_Bear_Rising  = C'154,038,232';
color         PVA_Bull_Climax  = C'000,166,100';
color         PVA_Bear_Climax  = C'214,012,083';

//Alert
bool          Alert_Allowed;
color         Alert_Color;
static bool   allow = true;
static bool   disallow = false;
string        text;
string        item1  = "[PVA Candles] Alert Box";
string        item2  = "[PVA Candles] Alert Text";
string        item3  = "[PVA Candles] Alert Dot1";
string        item4  = "[PVA Candles] Alert Dot2";

//+-------------------------------------------------------------------------------------------+
//| Custom indicator deinitialization function                                                |
//+-------------------------------------------------------------------------------------------+
int deinit()
  {
  int obj_total= ObjectsTotal();
  for(int k= obj_total; k>=0; k--)
    {
    string name= ObjectName(k);
    if(StringSubstr(name,0,12)=="[PVA Candles") {ObjectDelete(name);}
    }
  return(0);
  }

//+-------------------------------------------------------------------------------------------+
//| Custom indicator initialization function                                                  |
//+-------------------------------------------------------------------------------------------+
int init()
  {
  Deinitialized = false;

  //Determine the current chart scale (chart scale number should be 0-5)
  Chart_Scale = ChartScaleGet();

  //Set bar widths
        if(Chart_Scale == 0) {Bar_Width = 1;}
  else {if(Chart_Scale == 1) {Bar_Width = 2;}
  else {if(Chart_Scale == 2) {Bar_Width = 2;}
  else {if(Chart_Scale == 3) {Bar_Width = 3;}
  else {if(Chart_Scale == 4) {Bar_Width = 6;}
  else {Bar_Width = 13;} }}}}

  //Colors Selection for PVA
  if(__PVA_BAR_STD_HA_1234==1)
    {
    if(__PVA_Color_Simple_Standard_Default_123==1)
      {
      Bull_Wick   = __Simple_Wicks;
      Bear_Wick   = __Simple_Wicks;
      Bull_Candle = __Simple_Bull;
      Bear_Candle = __Simple_Bear;
      Bull_Rising = __Simple_PVA_Bull;
      Bear_Rising = __Simple_PVA_Bear;
      Bull_Climax = __Simple_PVA_Bull;
      Bear_Climax = __Simple_PVA_Bear;
      }
    else {if(__PVA_Color_Simple_Standard_Default_123==2)
      {
      Bull_Wick   = __Standard_Wicks;
      Bear_Wick   = __Standard_Wicks;
      Bull_Candle = __Standard_Bull;
      Bear_Candle = __Standard_Bear;
      Bull_Rising = __Standard_Bull_Rising;
      Bear_Rising = __Standard_Bear_Rising;
      Bull_Climax = __Standard_Bull_Climax;
      Bear_Climax = __Standard_Bear_Climax;
      }
    else {if(__PVA_Color_Simple_Standard_Default_123==3)
      {
      Bull_Wick   = PVA_Normal_Wick;
      Bear_Wick   = PVA_Normal_Wick;
      Bull_Candle = PVA_Normal_Bull;
      Bear_Candle = PVA_Normal_Bear;
      Bull_Rising = PVA_Bull_Rising;
      Bear_Rising = PVA_Bear_Rising;
      Bull_Climax = PVA_Bull_Climax;
      Bear_Climax = PVA_Bear_Climax;
      }}}

    //PVA Bars
    if(__PVA_Bars_Candles_Bodies_123==1)
      {
      //PVA: Wicks
      SetIndexBuffer(0,Bar1);
      SetIndexStyle(0,DRAW_HISTOGRAM, 0, 1, Bull_Wick);
      SetIndexBuffer(1,Bar2);
      SetIndexStyle(1,DRAW_HISTOGRAM, 0, 1, Bear_Wick);
      //PVA: simple Rising Volume Candles
      SetIndexBuffer(2,RisingBull);
      SetIndexStyle(2,DRAW_HISTOGRAM, 0, Bar_Width, Bull_Rising);
      SetIndexBuffer(3,RisingBear);
      SetIndexStyle(3,DRAW_HISTOGRAM, 0, Bar_Width, Bear_Rising);
      //PVA: Simple Climax Volume Candles
      SetIndexBuffer(4,ClimaxBull);
      SetIndexStyle(4,DRAW_HISTOGRAM, 0, Bar_Width, Bull_Climax);
      SetIndexBuffer(5,ClimaxBear);
      SetIndexStyle(5,DRAW_HISTOGRAM, 0, Bar_Width, Bear_Climax);
      }

    //PVA Candlesticks
    else if(__PVA_Bars_Candles_Bodies_123==2)
      {
      //PVA: Simple Wicks
      SetIndexBuffer(0,Bar1);
      SetIndexStyle(0,DRAW_HISTOGRAM, 0, 1, Bull_Wick);
      SetIndexBuffer(1,Bar2);
      SetIndexStyle(1,DRAW_HISTOGRAM, 0, 1, Bear_Wick);
      //PVA: Simple Normal Candles
      SetIndexBuffer(2,Candle1);
      SetIndexStyle(2,DRAW_HISTOGRAM, 0, Bar_Width, Bull_Candle);
      SetIndexBuffer(3,Candle2);
      SetIndexStyle(3,DRAW_HISTOGRAM, 0, Bar_Width, Bear_Candle);
      //PVA: Simple Rising Volume Candles
      SetIndexBuffer(4,RisingBull);
      SetIndexStyle(4,DRAW_HISTOGRAM, 0, Bar_Width, Bull_Rising);
      SetIndexBuffer(5,RisingBear);
      SetIndexStyle(5,DRAW_HISTOGRAM, 0, Bar_Width, Bear_Rising);
      //PVA: Simple Climax Volume Candles
      SetIndexBuffer(6,ClimaxBull);
      SetIndexStyle(6,DRAW_HISTOGRAM, 0, Bar_Width, Bull_Climax);
      SetIndexBuffer(7,ClimaxBear);
      SetIndexStyle(7,DRAW_HISTOGRAM, 0, Bar_Width, Bear_Climax);
      }

    //PVA Bodies Only
    else if(__PVA_Bars_Candles_Bodies_123==3)
      {
      //PVA: Simple Rising Volume Candles
      SetIndexBuffer(0,RisingBull);
      SetIndexStyle(0,DRAW_HISTOGRAM, 0, Bar_Width, Bull_Rising);
      SetIndexBuffer(1,RisingBear);
      SetIndexStyle(1,DRAW_HISTOGRAM, 0, Bar_Width, Bear_Rising);
      //PVA: Simple Climax Volume Candles
      SetIndexBuffer(2,ClimaxBull);
      SetIndexStyle(2,DRAW_HISTOGRAM, 0, Bar_Width, Bull_Climax);
      SetIndexBuffer(3,ClimaxBear);
      SetIndexStyle(3,DRAW_HISTOGRAM, 0, Bar_Width, Bear_Climax);
      }
    }

  //Non-PVA Bar Only
  else if(__PVA_BAR_STD_HA_1234 == 2)
    {
    //Default Wicks
    SetIndexBuffer(0,Bar1);
    SetIndexStyle(0,DRAW_HISTOGRAM, 0, 1, __Bars_Color);
    SetIndexBuffer(1,Bar2);
    SetIndexStyle(1,DRAW_HISTOGRAM, 0, 1, __Bars_Color);
    }

  //Non-PVA STD or HA
  else if(__PVA_BAR_STD_HA_1234 > 2)
    {
    //Colors Selection for STD and HA Candles
    if(Non_PVA_Color_Options_1_2_3_4_5 == 1)
      {
      Bull_Wick = __1_Wick_Up;
      Bear_Wick = __1_Wick_Dn;
      Bull_Candle = __1_Bull;
      Bear_Candle = __1_Bear;
      }
    else {if(Non_PVA_Color_Options_1_2_3_4_5 == 2)
      {
      Bull_Wick = __2_Wick_Up;
      Bear_Wick = __2_Wick_Dn;
      Bull_Candle = __2_Bull;
      Bear_Candle = __2_Bear;
      }
    else {if(Non_PVA_Color_Options_1_2_3_4_5 == 3)
      {
      Bull_Wick = __3_Wick_Up;
      Bear_Wick = __3_Wick_Dn;
      Bull_Candle = __3_Bull;
      Bear_Candle = __3_Bear;
      }
    else {if(Non_PVA_Color_Options_1_2_3_4_5 == 4)
      {
      Bull_Wick = __4_Wick_Up;
      Bear_Wick = __4_Wick_Dn;
      Bull_Candle = __4_Bull;
      Bear_Candle = __4_Bear;
      }
    else {if(Non_PVA_Color_Options_1_2_3_4_5 == 5)
      {
      Bull_Wick = __5_Wick_Up;
      Bear_Wick = __5_Wick_Dn;
      Bull_Candle = __5_Bull;
      Bear_Candle = __5_Bear;
      }}}}}
    if(Apply_Wicks_OverRide_Color)
      {
      Bull_Wick = __Wicks_OverRide_Color_Up;
      Bear_Wick = __Wicks_OverRide_Color_Dn;
      }
    //STD
    if(__PVA_BAR_STD_HA_1234==3)
      {
      //STD: Wicks
      SetIndexBuffer(0,Bar1);
      SetIndexStyle(0,DRAW_HISTOGRAM, 0, 1, Bull_Wick);
      SetIndexBuffer(1,Bar2);
      SetIndexStyle(1,DRAW_HISTOGRAM, 0, 1, Bear_Wick);
      //STD: Bodies
      SetIndexBuffer(2,Candle1);
      SetIndexStyle(2,DRAW_HISTOGRAM, 0, Bar_Width, Bull_Candle);
      SetIndexBuffer(3,Candle2);
      SetIndexStyle(3,DRAW_HISTOGRAM, 0, Bar_Width, Bear_Candle);
      }
    //Heiken Ashi
    else
      {
      //HA: Wicks
      SetIndexBuffer(0,ExtMapBuffer1);
      SetIndexStyle(0,DRAW_HISTOGRAM, 0, 1, Bear_Wick);
      SetIndexBuffer(1,ExtMapBuffer2);
      SetIndexStyle(1,DRAW_HISTOGRAM, 0, 1, Bull_Wick);
      //HA: Bodies
      SetIndexBuffer(2,ExtMapBuffer3);
      SetIndexStyle(2,DRAW_HISTOGRAM, 0, Bar_Width, Bull_Candle);
      SetIndexBuffer(3,ExtMapBuffer4);
      SetIndexStyle(3,DRAW_HISTOGRAM, 0, Bar_Width, Bear_Candle);
	   }
	 }

  //Indicator ShortName
  IndicatorShortName("Candles Suite");

  //Alert
  if(Show_Alert_Label && __PVA_BAR_STD_HA_1234 == 1)
    {
    text = "PVA";
    if(Alert_On == true)
      {
      Alert_Allowed = true;
      Alert_Color = Lime;
      }
    else
      {
      Alert_Allowed = false;
      Alert_Color = Red;
      }
    }

  return(0);
  }

//+-------------------------------------------------------------------------------------------+
//| Custom indicator iteration function                                                       |
//+-------------------------------------------------------------------------------------------+
int start()
  {
  //If Indicator is "Off" deinitialize only once, not every tick
  if (!Indicator_On)
    {
    if (!Deinitialized) {deinit(); Deinitialized = true;}
    return(0);
    }

  if(__PVA_BAR_STD_HA_1234 < 4)
  {
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
    //Define standard candle bodies & wicks
	 high    = iHigh(NULL,NULL,i);
    low     = iLow(NULL,NULL,i);
	 open    = iOpen(NULL,NULL,i);
	 close   = iClose(NULL,NULL,i);
	 bodyHigh= MathMax(open,close);
	 bodyLow = MathMin(open,close);
	 if(close>open)
		{
	   Bar1[i] = high;
	   Bar2[i] = low;
	   Candle1[i] = bodyHigh;
	   Candle2[i] = bodyLow;
		}
	 else if(close<open)
		{
	 	Bar1[i] = low;
		Bar2[i] = high;
		Candle1[i] = bodyLow;
		Candle2[i] = bodyHigh;
		}
	 else //(close==open)
	   {
		Bar1[i] = low;
		Bar2[i] = high;
		Candle1[i] = close;
		Candle2[i] = open-0.000001;
      }

    //PVA
    if(__PVA_BAR_STD_HA_1234 == 1)
      {
      //Clear buffers
      RisingBull[i] = 0;
      RisingBear[i] = 0;
      ClimaxBull[i] = 0;
      ClimaxBear[i] = 0;
      av            = 0;
      va            = 0;

      //Rising Volume
      for(j = i+1; j <= i+10; j++) {av = av + Volume[j];}
      av = av / 10;

      //Climax Volume
      Range = (High[i]-Low[i]);
      Value2 = Volume[i]*Range;
      HiValue2 = 0;
      for(j = i+1; j <= i+10; j++)
        {
        tempv2 = Volume[j]*((High[j]-Low[j]));
        if (tempv2 >= HiValue2) {HiValue2 = tempv2;}
        }
      if((Value2 >= HiValue2) || (Volume[i] >= av * 2)) {va = 1;}

      //Rising Volume
      if((va == 0) &&
        ((__PVA_Color_Simple_Standard_Default_123 > 1) ||
        ((__PVA_Color_Simple_Standard_Default_123 == 1) && (__Include_Rising_Volume))))
        {
        if(Volume[i] >= av * 1.5) {va= 2;}
        }

      //Apply Correct Color to PVA Candle
      if (va==1)
        {
        ClimaxBull[i]=iClose(NULL,NULL,i);
        ClimaxBear[i]=iOpen(NULL,NULL,i);
        if(iClose(NULL,NULL,i) == iOpen(NULL,NULL,i)) {ClimaxBear[i]=iOpen(NULL,NULL,i)+0.000001;}
        //Sound & Text Alert
        if(i == 0 && Alert_Allowed && Alert_On)
          {
          Alert_Allowed = false;
          Alert(Broker_Name_In_Alert,":  ",Symbol(),"-",Period(),"   PVA alert!");
          }
        }
      else if (va==2)
        {
        RisingBull[i]=iClose(NULL,NULL,i);
        RisingBear[i]=iOpen(NULL,NULL,i);
        if(iClose(NULL,NULL,i) == iOpen(NULL,NULL,i)) {RisingBear[i]=iOpen(NULL,NULL,i)+0.000001;}
        }
      }//End "if PVA"
    }//End "i" loop for PVA & STD Candles

  //PVA Alert
  ObjectDelete(item1);
  ObjectDelete(item2);
  ObjectDelete(item3);
  ObjectDelete(item4);
  if(Show_Alert_Label && __PVA_BAR_STD_HA_1234 == 1)
    {
    //PVA: Draw Alert Box
    ObjectDelete(item1);
    ObjectCreate(item1, OBJ_LABEL,0,0,0);
    ObjectSet(item1, OBJPROP_CORNER,1);
    ObjectSet(item1, OBJPROP_XDISTANCE,-8);
    ObjectSet(item1, OBJPROP_YDISTANCE,-4);
    ObjectSet(item1, OBJPROP_BACK, false);
    ObjectSet(item1, OBJPROP_COLOR, White);
    ObjectSetText(item1, "gggg",11, "Webdings");
    //PVA: Draw Alert Text
    ObjectDelete(item2);
    ObjectCreate(item2,OBJ_LABEL,0,0,0);
    ObjectSet(item2,OBJPROP_CORNER,1);
    ObjectSet(item2,OBJPROP_YDISTANCE,0);
    ObjectSet(item2,OBJPROP_XDISTANCE,18);
    ObjectSet(item2,OBJPROP_BACK,false);
    ObjectSetText(item2,text,7,"Verdana",MidnightBlue);
    //PVA: Draw Alert Dot1
    ObjectDelete(item3);
    ObjectCreate(item3,OBJ_LABEL,0,0,0);
    ObjectSet(item3,OBJPROP_CORNER,1);
    ObjectSet(item3,OBJPROP_YDISTANCE,-2);
    ObjectSet(item3,OBJPROP_XDISTANCE,5);
    ObjectSet(item3,OBJPROP_BACK,false);
    ObjectSetText(item3, "n",7, "Webdings",DarkSlateBlue);
    //PVA: Draw Alert Dot2
    ObjectDelete(item4);
    ObjectCreate(item4,OBJ_LABEL,0,0,0);
    ObjectSet(item4,OBJPROP_CORNER,1);
    ObjectSet(item4,OBJPROP_YDISTANCE,-2);
    ObjectSet(item4,OBJPROP_XDISTANCE,5);
    ObjectSet(item4,OBJPROP_BACK,false);
    ObjectSetText(item4, "=",7, "Webdings",Alert_Color);
    }//End PVA Climax Alert
  }//End show of PVA & STD

  //Heiken-Ashi (altered to display price gaps)
  else
    {
    if(Bars<=10) return(0);
    ExtCountedBars=IndicatorCounted();
    //---- check for possible errors
    if (ExtCountedBars<0) return(-1);
    //---- last counted bar will be recounted
    if (ExtCountedBars>0) ExtCountedBars--;
    int pos=Bars-ExtCountedBars-1;
    while(pos>=0)
      {
      if(Low[pos]> High[pos+1]) {haOpen=Low[pos];}
      else {if(High[pos]< Low[pos+1]) {haOpen=High[pos];}
      else {haOpen=(ExtMapBuffer3[pos+1]+ExtMapBuffer4[pos+1])/2;}}
      haClose=(Open[pos]+High[pos]+Low[pos]+Close[pos])/4;
      haHigh=MathMax(High[pos], MathMax(haOpen, haClose));
      haLow=MathMin(Low[pos], MathMin(haOpen, haClose));
      if(haOpen<haClose)
        {
        ExtMapBuffer1[pos]=haLow;
        ExtMapBuffer2[pos]=haHigh;
        }
      else
        {
        ExtMapBuffer1[pos]=haHigh;
        ExtMapBuffer2[pos]=haLow;
        }
      ExtMapBuffer3[pos]=haClose;
      ExtMapBuffer4[pos]=haOpen;
 	   pos--;
      }
    }//End Heiken Ashi candles loop

  return(0);
  }

//+-------------------------------------------------------------------------------------------+
//| Subroutine:  Set up to get the chart scale number                                         |
//+-------------------------------------------------------------------------------------------+
void OnChartEvent(const int id, const long &lparam, const double &dparam, const string &sparam)
  {
  Chart_Scale = ChartScaleGet();
  if(Alert_Allowed == allow)
    {
    init();
    Alert_Allowed = allow;
    }
  else
    {
    init();
    Alert_Allowed = disallow;
    }
  }

//+-------------------------------------------------------------------------------------------+
//| Subroutine:  Get the chart scale number                                                   |
//+-------------------------------------------------------------------------------------------+
int ChartScaleGet()
  {
  long result = -1;
  ChartGetInteger(0,CHART_SCALE,0,result);
  return((int)result);
  }

//+-------------------------------------------------------------------------------------------+
//|Custom indicator end                                                                       |
//+-------------------------------------------------------------------------------------------+
         