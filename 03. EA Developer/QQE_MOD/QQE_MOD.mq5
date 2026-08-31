//+------------------------------------------------------------------+
//|                                                      QQE_MOD.mq5 |
//| Pine v6 QQE MOD port for MetaTrader 5                            |
//| Source specification supplied by the workspace owner.            |
//|                                                                  |
//| Public iCustom buffer contract:                                  |
//|   0  Secondary RSI histogram (EMPTY_VALUE inside neutral zone)   |
//|   1  Histogram color index (0 gray, 1 cyan, 2 magenta)           |
//|   2  Secondary QQE trend line, centered at zero                  |
//|   3  Primary smoothed RSI, centered at zero                      |
//|   4  Secondary smoothed RSI, centered at zero                    |
//|   5  Primary QQE trend line, centered at zero                    |
//|   6  Primary QQE Bollinger upper band                            |
//|   7  Primary QQE Bollinger lower band                            |
//|   8  Composite state: +1 up, -1 down, 0 neutral                  |
//|   9  Primary zero-cross event: +1 up, -1 down, 0 none            |
//|                                                                  |
//| For non-repainting EA decisions, consume buffer shift >= 1.      |
//+------------------------------------------------------------------+
#property copyright   "Workspace owner"
#property version     "1.00"
#property description "QQE MOD dual-QQE oscillator with Pine-compatible stateful bands"
#property description "Single-file implementation; no external includes or indicator handles"

#property indicator_separate_window
#property indicator_buffers 24
#property indicator_plots   9

//--- Visible plot 1: secondary RSI histogram with TradingView colors
#property indicator_type1   DRAW_COLOR_HISTOGRAM
#property indicator_color1  C'112,112,112',C'0,195,255',C'255,0,98'
#property indicator_style1  STYLE_SOLID
#property indicator_width1  2
#property indicator_label1  "Secondary RSI Histogram"

//--- Visible plot 2: secondary QQE trend line
#property indicator_type2   DRAW_LINE
#property indicator_color2  clrBlack
#property indicator_style2  STYLE_SOLID
#property indicator_width2  2
#property indicator_label2  "Secondary QQE Trend Line"

//--- Hidden plots keep a stable iCustom/Data Window contract
#property indicator_type3   DRAW_NONE
#property indicator_label3  "Primary Smoothed RSI"
#property indicator_type4   DRAW_NONE
#property indicator_label4  "Secondary Smoothed RSI"
#property indicator_type5   DRAW_NONE
#property indicator_label5  "Primary QQE Trend Line"
#property indicator_type6   DRAW_NONE
#property indicator_label6  "Bollinger Upper"
#property indicator_type7   DRAW_NONE
#property indicator_label7  "Bollinger Lower"
#property indicator_type8   DRAW_NONE
#property indicator_label8  "Composite State"
#property indicator_type9   DRAW_NONE
#property indicator_label9  "Primary Zero Cross"

#property indicator_level1      0.0
#property indicator_levelcolor  C'130,130,130'
#property indicator_levelstyle  STYLE_DOT
#property indicator_levelwidth  1

//--- Primary QQE inputs
input group "Primary QQE Settings"
input int                InpPrimaryRSILength     = 6;           // RSI Length
input int                InpPrimaryRSISmoothing  = 5;           // RSI Smoothing
input double             InpPrimaryQQEFactor     = 3.0;         // QQE Factor
input double             InpPrimaryThreshold     = 3.0;         // TV parity only (original plot does not use it)
input ENUM_APPLIED_PRICE InpPrimarySource        = PRICE_CLOSE; // RSI Source

//--- Secondary QQE inputs
input group "Secondary QQE Settings"
input int                InpSecondaryRSILength    = 6;           // RSI Length
input int                InpSecondaryRSISmoothing = 5;           // RSI Smoothing
input double             InpSecondaryQQEFactor    = 1.61;        // QQE Factor
input double             InpSecondaryThreshold    = 3.0;         // Threshold
input ENUM_APPLIED_PRICE InpSecondarySource       = PRICE_CLOSE; // RSI Source

//--- Bollinger inputs
input group "Bollinger Bands Settings"
input int                InpBollingerLength       = 50;          // Length
input double             InpBollingerMultiplier   = 0.35;        // Multiplier

//--- Visual inputs
input group "Visual Settings"
input bool               InpAutoContrastTrendLine = true;              // Auto black/white for chart theme
input color              InpTrendLineColor        = clrBlack;          // Manual line color when auto is off
input color              InpNeutralColor          = C'112,112,112';    // Neutral histogram
input color              InpUpColor               = C'0,195,255';      // Up histogram
input color              InpDownColor             = C'255,0,98';       // Down histogram
input color              InpZeroLineColor         = C'130,130,130';    // Zero line
input int                InpHistogramWidth         = 2;                 // Histogram width (1..5)
input int                InpTrendLineWidth         = 2;                 // Trend line width (1..5)

//--- Alert inputs. All alerts are deliberately evaluated on closed bars.
input group "Closed-Bar Alerts"
input bool               InpEnableZeroCrossAlerts = true;  // Primary RSI zero-cross alerts
input bool               InpEnableSignalAlerts    = true;  // Composite QQE up/down alerts
input bool               InpEnablePopupAlert      = true;  // MT5 popup/sound
input bool               InpEnablePushNotification= false; // Mobile push

//--- Public data buffers (0..9)
double ExtHistogramBuffer[];
double ExtHistogramColorBuffer[];
double ExtSecondaryQQEBuffer[];
double ExtPrimaryRSIBuffer[];
double ExtSecondaryRSIBuffer[];
double ExtPrimaryQQEBuffer[];
double ExtBollingerUpperBuffer[];
double ExtBollingerLowerBuffer[];
double ExtCompositeStateBuffer[];
double ExtPrimaryCrossBuffer[];

//--- Internal calculation buffers for the primary lane (10..16)
double ExtPrimarySourceBuffer[];
double ExtPrimaryAvgGainBuffer[];
double ExtPrimaryAvgLossBuffer[];
double ExtPrimarySmoothedAtrBuffer[];
double ExtPrimaryLongBandBuffer[];
double ExtPrimaryShortBandBuffer[];
double ExtPrimaryTrendBuffer[];

//--- Internal calculation buffers for the secondary lane (17..23)
double ExtSecondarySourceBuffer[];
double ExtSecondaryAvgGainBuffer[];
double ExtSecondaryAvgLossBuffer[];
double ExtSecondarySmoothedAtrBuffer[];
double ExtSecondaryLongBandBuffer[];
double ExtSecondaryShortBandBuffer[];
double ExtSecondaryTrendBuffer[];

datetime g_lastLiveBarTime=0;

//+------------------------------------------------------------------+
//| Compact numeric text for the TradingView-like short name.        |
//+------------------------------------------------------------------+
string CompactNumber(const double value,const int digits=2)
  {
   string text=DoubleToString(value,digits);
   while(StringLen(text)>0 && StringSubstr(text,StringLen(text)-1,1)=="0")
      text=StringSubstr(text,0,StringLen(text)-1);
   if(StringLen(text)>0 && StringSubstr(text,StringLen(text)-1,1)==".")
      text=StringSubstr(text,0,StringLen(text)-1);
   return(text);
  }

//+------------------------------------------------------------------+
//| Apply colors and widths; auto-contrast keeps the line readable.  |
//+------------------------------------------------------------------+
void ApplyVisualStyle()
  {
   color trendColor=InpTrendLineColor;
   if(InpAutoContrastTrendLine)
     {
      long backgroundValue=0;
      if(ChartGetInteger(0,CHART_COLOR_BACKGROUND,0,backgroundValue))
        {
         const int red=(int)(backgroundValue&0xFF);
         const int green=(int)((backgroundValue>>8)&0xFF);
         const int blue=(int)((backgroundValue>>16)&0xFF);
         const int luminance=(299*red+587*green+114*blue)/1000;
         trendColor=(luminance<128 ? clrWhite : clrBlack);
        }
     }

   PlotIndexSetInteger(0,PLOT_LINE_COLOR,0,InpNeutralColor);
   PlotIndexSetInteger(0,PLOT_LINE_COLOR,1,InpUpColor);
   PlotIndexSetInteger(0,PLOT_LINE_COLOR,2,InpDownColor);
   PlotIndexSetInteger(0,PLOT_LINE_WIDTH,InpHistogramWidth);
   PlotIndexSetInteger(1,PLOT_LINE_COLOR,trendColor);
   PlotIndexSetInteger(1,PLOT_LINE_WIDTH,InpTrendLineWidth);
   IndicatorSetInteger(INDICATOR_LEVELCOLOR,0,InpZeroLineColor);
  }

//+------------------------------------------------------------------+
//| Return true only for a usable calculated value.                  |
//+------------------------------------------------------------------+
bool IsUsableValue(const double value)
  {
   return(value!=EMPTY_VALUE && MathIsValidNumber(value));
  }

//+------------------------------------------------------------------+
//| TradingView/Pine crossover-or-crossunder semantics.              |
//+------------------------------------------------------------------+
bool Crosses(const double currentA,
             const double currentB,
             const double previousA,
             const double previousB)
  {
   if(!IsUsableValue(currentA) || !IsUsableValue(currentB) ||
      !IsUsableValue(previousA) || !IsUsableValue(previousB))
      return(false);

   return((currentA>currentB && previousA<=previousB) ||
          (currentA<currentB && previousA>=previousB));
  }

//+------------------------------------------------------------------+
//| Resolve an MT5 applied-price selection for one chronological bar.|
//+------------------------------------------------------------------+
double AppliedPriceAt(const int index,
                      const ENUM_APPLIED_PRICE appliedPrice,
                      const double &open[],
                      const double &high[],
                      const double &low[],
                      const double &close[])
  {
   switch(appliedPrice)
     {
      case PRICE_OPEN:     return(open[index]);
      case PRICE_HIGH:     return(high[index]);
      case PRICE_LOW:      return(low[index]);
      case PRICE_MEDIAN:   return((high[index]+low[index])*0.5);
      case PRICE_TYPICAL:  return((high[index]+low[index]+close[index])/3.0);
      case PRICE_WEIGHTED: return((high[index]+low[index]+close[index]*2.0)/4.0);
      case PRICE_CLOSE:
      default:             return(close[index]);
     }
  }

//+------------------------------------------------------------------+
//| Human-readable source name for the indicator short name.         |
//+------------------------------------------------------------------+
string AppliedPriceName(const ENUM_APPLIED_PRICE appliedPrice)
  {
   switch(appliedPrice)
     {
      case PRICE_OPEN:     return("open");
      case PRICE_HIGH:     return("high");
      case PRICE_LOW:      return("low");
      case PRICE_MEDIAN:   return("hl2");
      case PRICE_TYPICAL:  return("hlc3");
      case PRICE_WEIGHTED: return("ohlc4");
      case PRICE_CLOSE:
      default:             return("close");
     }
  }

//+------------------------------------------------------------------+
//| Pine-style RSI: Wilder RMA seeded by the first length changes.   |
//+------------------------------------------------------------------+
double CalculateRSI(const int index,
                    const int length,
                    const double &source[],
                    double &averageGain[],
                    double &averageLoss[])
  {
   if(index<=0 || index<length)
     {
      averageGain[index]=EMPTY_VALUE;
      averageLoss[index]=EMPTY_VALUE;
      return(EMPTY_VALUE);
     }

   const double change=source[index]-source[index-1];
   const double gain=MathMax(change,0.0);
   const double loss=MathMax(-change,0.0);

   if(index==length)
     {
      double gainSum=0.0;
      double lossSum=0.0;
      for(int cursor=1; cursor<=length; cursor++)
        {
         const double delta=source[cursor]-source[cursor-1];
         gainSum+=MathMax(delta,0.0);
         lossSum+=MathMax(-delta,0.0);
        }
      averageGain[index]=gainSum/(double)length;
      averageLoss[index]=lossSum/(double)length;
     }
   else
     {
      if(!IsUsableValue(averageGain[index-1]) ||
         !IsUsableValue(averageLoss[index-1]))
        {
         averageGain[index]=EMPTY_VALUE;
         averageLoss[index]=EMPTY_VALUE;
         return(EMPTY_VALUE);
        }

      averageGain[index]=(averageGain[index-1]*(length-1)+gain)/(double)length;
      averageLoss[index]=(averageLoss[index-1]*(length-1)+loss)/(double)length;
     }

   const double epsilon=1.0e-14;
   if(averageLoss[index]<=epsilon)
     {
      if(averageGain[index]<=epsilon)
         return(50.0);
      return(100.0);
     }
   if(averageGain[index]<=epsilon)
      return(0.0);

   const double relativeStrength=averageGain[index]/averageLoss[index];
   return(100.0-100.0/(1.0+relativeStrength));
  }

//+------------------------------------------------------------------+
//| Calculate one chronological bar of one QQE lane.                 |
//| All RSI/band values are centered by 50 after RSI calculation.    |
//+------------------------------------------------------------------+
void CalculateQQEBar(const int index,
                     const int rsiLength,
                     const int smoothingLength,
                     const double qqeFactor,
                     const double &source[],
                     double &averageGain[],
                     double &averageLoss[],
                     double &smoothedRSICentered[],
                     double &smoothedAtrRSI[],
                     double &longBand[],
                     double &shortBand[],
                     double &trendDirection[],
                     double &qqeTrendLineCentered[])
  {
   smoothedRSICentered[index]=EMPTY_VALUE;
   smoothedAtrRSI[index]=EMPTY_VALUE;
   longBand[index]=EMPTY_VALUE;
   shortBand[index]=EMPTY_VALUE;
   trendDirection[index]=0.0;
   qqeTrendLineCentered[index]=EMPTY_VALUE;

   const double rawRSI=CalculateRSI(index,rsiLength,source,averageGain,averageLoss);
   if(!IsUsableValue(rawRSI))
      return;

   const double previousSmoothed=(index>0 ? smoothedRSICentered[index-1] : EMPTY_VALUE);
   if(IsUsableValue(previousSmoothed))
     {
      const double alphaRSI=2.0/(smoothingLength+1.0);
      smoothedRSICentered[index]=alphaRSI*(rawRSI-50.0)+(1.0-alphaRSI)*previousSmoothed;
     }
   else
      smoothedRSICentered[index]=rawRSI-50.0;

   if(!IsUsableValue(previousSmoothed))
      return;

   const double atrRSI=MathAbs(smoothedRSICentered[index]-previousSmoothed);
   const int wildersLength=rsiLength*2-1;
   const double previousSmoothedAtr=(index>0 ? smoothedAtrRSI[index-1] : EMPTY_VALUE);
   if(IsUsableValue(previousSmoothedAtr))
     {
      const double alphaAtr=2.0/(wildersLength+1.0);
      smoothedAtrRSI[index]=alphaAtr*atrRSI+(1.0-alphaAtr)*previousSmoothedAtr;
     }
   else
      smoothedAtrRSI[index]=atrRSI;

   const double atrDelta=smoothedAtrRSI[index]*qqeFactor;
   const double newLongBand=smoothedRSICentered[index]-atrDelta;
   const double newShortBand=smoothedRSICentered[index]+atrDelta;
   const double previousLong=(index>0 ? longBand[index-1] : EMPTY_VALUE);
   const double previousShort=(index>0 ? shortBand[index-1] : EMPTY_VALUE);

   if(IsUsableValue(previousLong) &&
      previousSmoothed>previousLong &&
      smoothedRSICentered[index]>previousLong)
      longBand[index]=MathMax(previousLong,newLongBand);
   else
      longBand[index]=newLongBand;

   if(IsUsableValue(previousShort) &&
      previousSmoothed<previousShort &&
      smoothedRSICentered[index]<previousShort)
      shortBand[index]=MathMin(previousShort,newShortBand);
   else
      shortBand[index]=newShortBand;

   int direction=0;
   if(index>0 && IsUsableValue(trendDirection[index-1]))
      direction=(int)trendDirection[index-1];

   bool shortBandCross=false;
   bool longBandCross=false;
   if(index>=2)
     {
      // Pine: ta.cross(smoothedRsi, shortBand[1])
      shortBandCross=Crosses(smoothedRSICentered[index],
                             shortBand[index-1],
                             smoothedRSICentered[index-1],
                             shortBand[index-2]);

      // Pine: ta.cross(longBand[1], smoothedRsi)
      longBandCross=Crosses(longBand[index-1],
                            smoothedRSICentered[index],
                            longBand[index-2],
                            smoothedRSICentered[index-1]);
     }

   if(shortBandCross)
      direction=1;
   else if(longBandCross)
      direction=-1;

   trendDirection[index]=(double)direction;
   qqeTrendLineCentered[index]=(direction==1 ? longBand[index] : shortBand[index]);
  }

//+------------------------------------------------------------------+
//| Population Bollinger band matching ta.stdev(..., biased=true).   |
//+------------------------------------------------------------------+
bool CalculateBollingerAt(const int index,
                          const int length,
                          const double multiplier,
                          const double &source[],
                          double &upper,
                          double &lower)
  {
   if(index<length-1)
      return(false);

   const int first=index-length+1;
   double sum=0.0;
   for(int cursor=first; cursor<=index; cursor++)
     {
      if(!IsUsableValue(source[cursor]))
         return(false);
      sum+=source[cursor];
     }

   const double basis=sum/(double)length;
   double squaredSum=0.0;
   for(int cursor=first; cursor<=index; cursor++)
     {
      const double deviation=source[cursor]-basis;
      squaredSum+=deviation*deviation;
     }

   const double variance=MathMax(squaredSum/(double)length,0.0);
   const double bandDeviation=multiplier*MathSqrt(variance);
   upper=basis+bandDeviation;
   lower=basis-bandDeviation;
   return(true);
  }

//+------------------------------------------------------------------+
//| Emit one user-facing alert through enabled channels.             |
//+------------------------------------------------------------------+
void EmitQQEAlert(const string message)
  {
   Print(message);
   if(InpEnablePopupAlert)
      Alert(message);
   if(InpEnablePushNotification &&
      !MQLInfoInteger(MQL_TESTER) &&
      TerminalInfoInteger(TERMINAL_NOTIFICATIONS_ENABLED))
      SendNotification(message);
  }

//+------------------------------------------------------------------+
//| Evaluate alerts once when a new live bar opens.                  |
//+------------------------------------------------------------------+
void ProcessClosedBarAlerts(const int ratesTotal,const datetime &time[])
  {
   if(ratesTotal<3)
      return;

   const datetime currentLiveBar=time[ratesTotal-1];
   if(g_lastLiveBarTime==0)
     {
      g_lastLiveBarTime=currentLiveBar;
      return;
     }

   if(currentLiveBar==g_lastLiveBarTime)
      return;

   g_lastLiveBarTime=currentLiveBar;
   const int closedBar=ratesTotal-2;
   const int previousBar=ratesTotal-3;
   const string context=StringFormat("%s %s @ %s",
                                     _Symbol,
                                     EnumToString((ENUM_TIMEFRAMES)_Period),
                                     TimeToString(time[closedBar],TIME_DATE|TIME_MINUTES));

   if(InpEnableZeroCrossAlerts)
     {
      if(ExtPrimaryCrossBuffer[closedBar]>0.5)
         EmitQQEAlert("QQE MOD: Primary RSI crossed above zero | "+context);
      else if(ExtPrimaryCrossBuffer[closedBar]<-0.5)
         EmitQQEAlert("QQE MOD: Primary RSI crossed below zero | "+context);
     }

   if(InpEnableSignalAlerts)
     {
      const int state=(int)ExtCompositeStateBuffer[closedBar];
      const int previousState=(int)ExtCompositeStateBuffer[previousBar];
      if(state==1 && previousState!=1)
         EmitQQEAlert("QQE MOD: UP signal confirmed | "+context);
      else if(state==-1 && previousState!=-1)
         EmitQQEAlert("QQE MOD: DOWN signal confirmed | "+context);
     }
  }

//+------------------------------------------------------------------+
//| Initialize all buffers for a full history rebuild.               |
//+------------------------------------------------------------------+
void InitializeBuffers()
  {
   ArrayInitialize(ExtHistogramBuffer,EMPTY_VALUE);
   ArrayInitialize(ExtHistogramColorBuffer,0.0);
   ArrayInitialize(ExtSecondaryQQEBuffer,EMPTY_VALUE);
   ArrayInitialize(ExtPrimaryRSIBuffer,EMPTY_VALUE);
   ArrayInitialize(ExtSecondaryRSIBuffer,EMPTY_VALUE);
   ArrayInitialize(ExtPrimaryQQEBuffer,EMPTY_VALUE);
   ArrayInitialize(ExtBollingerUpperBuffer,EMPTY_VALUE);
   ArrayInitialize(ExtBollingerLowerBuffer,EMPTY_VALUE);
   ArrayInitialize(ExtCompositeStateBuffer,0.0);
   ArrayInitialize(ExtPrimaryCrossBuffer,0.0);

   ArrayInitialize(ExtPrimarySourceBuffer,EMPTY_VALUE);
   ArrayInitialize(ExtPrimaryAvgGainBuffer,EMPTY_VALUE);
   ArrayInitialize(ExtPrimaryAvgLossBuffer,EMPTY_VALUE);
   ArrayInitialize(ExtPrimarySmoothedAtrBuffer,EMPTY_VALUE);
   ArrayInitialize(ExtPrimaryLongBandBuffer,EMPTY_VALUE);
   ArrayInitialize(ExtPrimaryShortBandBuffer,EMPTY_VALUE);
   ArrayInitialize(ExtPrimaryTrendBuffer,0.0);

   ArrayInitialize(ExtSecondarySourceBuffer,EMPTY_VALUE);
   ArrayInitialize(ExtSecondaryAvgGainBuffer,EMPTY_VALUE);
   ArrayInitialize(ExtSecondaryAvgLossBuffer,EMPTY_VALUE);
   ArrayInitialize(ExtSecondarySmoothedAtrBuffer,EMPTY_VALUE);
   ArrayInitialize(ExtSecondaryLongBandBuffer,EMPTY_VALUE);
   ArrayInitialize(ExtSecondaryShortBandBuffer,EMPTY_VALUE);
   ArrayInitialize(ExtSecondaryTrendBuffer,0.0);
  }

//+------------------------------------------------------------------+
//| Custom indicator initialization.                                |
//+------------------------------------------------------------------+
int OnInit()
  {
   if(InpPrimaryRSILength<1 || InpPrimaryRSISmoothing<1 ||
      InpSecondaryRSILength<1 || InpSecondaryRSISmoothing<1 ||
      InpPrimaryQQEFactor<=0.0 || InpSecondaryQQEFactor<=0.0 ||
      InpPrimaryThreshold<0.0 || InpSecondaryThreshold<0.0 ||
      InpBollingerLength<1 || InpBollingerMultiplier<=0.0 ||
      InpHistogramWidth<1 || InpHistogramWidth>5 ||
      InpTrendLineWidth<1 || InpTrendLineWidth>5)
     {
      Print("QQE MOD: invalid input parameters.");
      return(INIT_PARAMETERS_INCORRECT);
     }

   //--- Public buffers
   SetIndexBuffer(0,ExtHistogramBuffer,INDICATOR_DATA);
   SetIndexBuffer(1,ExtHistogramColorBuffer,INDICATOR_COLOR_INDEX);
   SetIndexBuffer(2,ExtSecondaryQQEBuffer,INDICATOR_DATA);
   SetIndexBuffer(3,ExtPrimaryRSIBuffer,INDICATOR_DATA);
   SetIndexBuffer(4,ExtSecondaryRSIBuffer,INDICATOR_DATA);
   SetIndexBuffer(5,ExtPrimaryQQEBuffer,INDICATOR_DATA);
   SetIndexBuffer(6,ExtBollingerUpperBuffer,INDICATOR_DATA);
   SetIndexBuffer(7,ExtBollingerLowerBuffer,INDICATOR_DATA);
   SetIndexBuffer(8,ExtCompositeStateBuffer,INDICATOR_DATA);
   SetIndexBuffer(9,ExtPrimaryCrossBuffer,INDICATOR_DATA);

   //--- Primary calculation buffers
   SetIndexBuffer(10,ExtPrimarySourceBuffer,INDICATOR_CALCULATIONS);
   SetIndexBuffer(11,ExtPrimaryAvgGainBuffer,INDICATOR_CALCULATIONS);
   SetIndexBuffer(12,ExtPrimaryAvgLossBuffer,INDICATOR_CALCULATIONS);
   SetIndexBuffer(13,ExtPrimarySmoothedAtrBuffer,INDICATOR_CALCULATIONS);
   SetIndexBuffer(14,ExtPrimaryLongBandBuffer,INDICATOR_CALCULATIONS);
   SetIndexBuffer(15,ExtPrimaryShortBandBuffer,INDICATOR_CALCULATIONS);
   SetIndexBuffer(16,ExtPrimaryTrendBuffer,INDICATOR_CALCULATIONS);

   //--- Secondary calculation buffers
   SetIndexBuffer(17,ExtSecondarySourceBuffer,INDICATOR_CALCULATIONS);
   SetIndexBuffer(18,ExtSecondaryAvgGainBuffer,INDICATOR_CALCULATIONS);
   SetIndexBuffer(19,ExtSecondaryAvgLossBuffer,INDICATOR_CALCULATIONS);
   SetIndexBuffer(20,ExtSecondarySmoothedAtrBuffer,INDICATOR_CALCULATIONS);
   SetIndexBuffer(21,ExtSecondaryLongBandBuffer,INDICATOR_CALCULATIONS);
   SetIndexBuffer(22,ExtSecondaryShortBandBuffer,INDICATOR_CALCULATIONS);
   SetIndexBuffer(23,ExtSecondaryTrendBuffer,INDICATOR_CALCULATIONS);

   //--- Force chronological indexing: oldest bar = 0, newest bar = rates_total-1.
   ArraySetAsSeries(ExtHistogramBuffer,false);
   ArraySetAsSeries(ExtHistogramColorBuffer,false);
   ArraySetAsSeries(ExtSecondaryQQEBuffer,false);
   ArraySetAsSeries(ExtPrimaryRSIBuffer,false);
   ArraySetAsSeries(ExtSecondaryRSIBuffer,false);
   ArraySetAsSeries(ExtPrimaryQQEBuffer,false);
   ArraySetAsSeries(ExtBollingerUpperBuffer,false);
   ArraySetAsSeries(ExtBollingerLowerBuffer,false);
   ArraySetAsSeries(ExtCompositeStateBuffer,false);
   ArraySetAsSeries(ExtPrimaryCrossBuffer,false);
   ArraySetAsSeries(ExtPrimarySourceBuffer,false);
   ArraySetAsSeries(ExtPrimaryAvgGainBuffer,false);
   ArraySetAsSeries(ExtPrimaryAvgLossBuffer,false);
   ArraySetAsSeries(ExtPrimarySmoothedAtrBuffer,false);
   ArraySetAsSeries(ExtPrimaryLongBandBuffer,false);
   ArraySetAsSeries(ExtPrimaryShortBandBuffer,false);
   ArraySetAsSeries(ExtPrimaryTrendBuffer,false);
   ArraySetAsSeries(ExtSecondarySourceBuffer,false);
   ArraySetAsSeries(ExtSecondaryAvgGainBuffer,false);
   ArraySetAsSeries(ExtSecondaryAvgLossBuffer,false);
   ArraySetAsSeries(ExtSecondarySmoothedAtrBuffer,false);
   ArraySetAsSeries(ExtSecondaryLongBandBuffer,false);
   ArraySetAsSeries(ExtSecondaryShortBandBuffer,false);
   ArraySetAsSeries(ExtSecondaryTrendBuffer,false);

   //--- TradingView-like visual defaults, still editable via Inputs.
   ApplyVisualStyle();

   for(int plot=0; plot<9; plot++)
      PlotIndexSetDouble(plot,PLOT_EMPTY_VALUE,EMPTY_VALUE);

   //--- Keep the pane header clean while preserving all iCustom buffers.
   for(int hiddenPlot=2; hiddenPlot<9; hiddenPlot++)
      PlotIndexSetInteger(hiddenPlot,PLOT_SHOW_DATA,false);

   const int secondaryDrawBegin=InpSecondaryRSILength+1;
   PlotIndexSetInteger(0,PLOT_DRAW_BEGIN,secondaryDrawBegin);
   PlotIndexSetInteger(1,PLOT_DRAW_BEGIN,secondaryDrawBegin);

   IndicatorSetInteger(INDICATOR_DIGITS,2);
   IndicatorSetInteger(INDICATOR_LEVELSTYLE,0,STYLE_DOT);
   IndicatorSetInteger(INDICATOR_LEVELWIDTH,0,1);

   const string shortName=StringFormat("QQE MOD %d %d %s %s %s %d %d %s %s %s %d %s",
                                        InpPrimaryRSILength,
                                        InpPrimaryRSISmoothing,
                                        CompactNumber(InpPrimaryQQEFactor),
                                        CompactNumber(InpPrimaryThreshold),
                                        AppliedPriceName(InpPrimarySource),
                                        InpSecondaryRSILength,
                                        InpSecondaryRSISmoothing,
                                        CompactNumber(InpSecondaryQQEFactor),
                                        CompactNumber(InpSecondaryThreshold),
                                        AppliedPriceName(InpSecondarySource),
                                        InpBollingerLength,
                                        CompactNumber(InpBollingerMultiplier));
   IndicatorSetString(INDICATOR_SHORTNAME,shortName);
   g_lastLiveBarTime=0;
   return(INIT_SUCCEEDED);
  }

//+------------------------------------------------------------------+
//| Main calculation loop.                                          |
//+------------------------------------------------------------------+
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
   const int minimumBars=MathMax(InpPrimaryRSILength+InpBollingerLength+2,
                                 InpSecondaryRSILength+2);
   if(rates_total<minimumBars)
      return(0);

   //--- Do not rely on terminal defaults for indexing direction.
   ArraySetAsSeries(time,false);
   ArraySetAsSeries(open,false);
   ArraySetAsSeries(high,false);
   ArraySetAsSeries(low,false);
   ArraySetAsSeries(close,false);

   // Closed-bar tester fast path.  Live chart behavior is unchanged; in the
   // tester the finalized bar is recalculated once when the next bar opens.
   static datetime lastTesterBarTime=0;
   if(MQLInfoInteger(MQL_TESTER) && prev_calculated>0 && lastTesterBarTime==time[rates_total-1])
      return(rates_total);
   if(MQLInfoInteger(MQL_TESTER))
      lastTesterBarTime=time[rates_total-1];

   int start=0;
   if(prev_calculated<=0 || prev_calculated>rates_total)
     {
      InitializeBuffers();
      start=0;
     }
   else
      start=MathMax(prev_calculated-1,0);

   for(int index=start; index<rates_total && !IsStopped(); index++)
     {
      ExtHistogramBuffer[index]=EMPTY_VALUE;
      ExtHistogramColorBuffer[index]=0.0;
      ExtSecondaryQQEBuffer[index]=EMPTY_VALUE;
      ExtBollingerUpperBuffer[index]=EMPTY_VALUE;
      ExtBollingerLowerBuffer[index]=EMPTY_VALUE;
      ExtCompositeStateBuffer[index]=0.0;
      ExtPrimaryCrossBuffer[index]=0.0;

      ExtPrimarySourceBuffer[index]=AppliedPriceAt(index,InpPrimarySource,open,high,low,close);
      ExtSecondarySourceBuffer[index]=AppliedPriceAt(index,InpSecondarySource,open,high,low,close);

      CalculateQQEBar(index,
                      InpPrimaryRSILength,
                      InpPrimaryRSISmoothing,
                      InpPrimaryQQEFactor,
                      ExtPrimarySourceBuffer,
                      ExtPrimaryAvgGainBuffer,
                      ExtPrimaryAvgLossBuffer,
                      ExtPrimaryRSIBuffer,
                      ExtPrimarySmoothedAtrBuffer,
                      ExtPrimaryLongBandBuffer,
                      ExtPrimaryShortBandBuffer,
                      ExtPrimaryTrendBuffer,
                      ExtPrimaryQQEBuffer);

      CalculateQQEBar(index,
                      InpSecondaryRSILength,
                      InpSecondaryRSISmoothing,
                      InpSecondaryQQEFactor,
                      ExtSecondarySourceBuffer,
                      ExtSecondaryAvgGainBuffer,
                      ExtSecondaryAvgLossBuffer,
                      ExtSecondaryRSIBuffer,
                      ExtSecondarySmoothedAtrBuffer,
                      ExtSecondaryLongBandBuffer,
                      ExtSecondaryShortBandBuffer,
                      ExtSecondaryTrendBuffer,
                      ExtSecondaryQQEBuffer);

      double upper=EMPTY_VALUE;
      double lower=EMPTY_VALUE;
      if(CalculateBollingerAt(index,
                              InpBollingerLength,
                              InpBollingerMultiplier,
                              ExtPrimaryQQEBuffer,
                              upper,
                              lower))
        {
         ExtBollingerUpperBuffer[index]=upper;
         ExtBollingerLowerBuffer[index]=lower;
        }

      //--- Primary RSI crossing its zero-centered level (raw RSI level 50).
      if(index>0 && IsUsableValue(ExtPrimaryRSIBuffer[index]) &&
         IsUsableValue(ExtPrimaryRSIBuffer[index-1]))
        {
         if(ExtPrimaryRSIBuffer[index]>0.0 && ExtPrimaryRSIBuffer[index-1]<=0.0)
            ExtPrimaryCrossBuffer[index]=1.0;
         else if(ExtPrimaryRSIBuffer[index]<0.0 && ExtPrimaryRSIBuffer[index-1]>=0.0)
            ExtPrimaryCrossBuffer[index]=-1.0;
        }

      //--- Preserve Pine plot ordering as one clean final-color histogram.
      if(IsUsableValue(ExtSecondaryRSIBuffer[index]))
        {
         const double secondaryValue=ExtSecondaryRSIBuffer[index];
         int state=0;

         if(secondaryValue>InpSecondaryThreshold)
           {
            ExtHistogramBuffer[index]=secondaryValue;
            ExtHistogramColorBuffer[index]=0.0;
            if(IsUsableValue(ExtPrimaryRSIBuffer[index]) &&
               IsUsableValue(ExtBollingerUpperBuffer[index]) &&
               ExtPrimaryRSIBuffer[index]>ExtBollingerUpperBuffer[index])
              {
               state=1;
               ExtHistogramColorBuffer[index]=1.0;
              }
           }
         else if(secondaryValue<-InpSecondaryThreshold)
           {
            ExtHistogramBuffer[index]=secondaryValue;
            ExtHistogramColorBuffer[index]=0.0;
            if(IsUsableValue(ExtPrimaryRSIBuffer[index]) &&
               IsUsableValue(ExtBollingerLowerBuffer[index]) &&
               ExtPrimaryRSIBuffer[index]<ExtBollingerLowerBuffer[index])
              {
               state=-1;
               ExtHistogramColorBuffer[index]=2.0;
              }
           }

         ExtCompositeStateBuffer[index]=(double)state;
        }
     }

   if(!MQLInfoInteger(MQL_TESTER))
      ProcessClosedBarAlerts(rates_total,time);
   return(rates_total);
  }

//+------------------------------------------------------------------+
//| Re-evaluate contrast when the user changes the chart theme.      |
//+------------------------------------------------------------------+
void OnChartEvent(const int id,
                  const long &lparam,
                  const double &dparam,
                  const string &sparam)
  {
   if(id==CHARTEVENT_CHART_CHANGE)
      ApplyVisualStyle();
  }
//+------------------------------------------------------------------+
