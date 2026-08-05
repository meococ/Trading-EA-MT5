//+------------------------------------------------------------------+
//|                               Modern_Bollinger_Bands_GBB.mq5     |
//| Modern Bollinger Bands [GBB] - single-file MetaTrader 5 port     |
//| Source specification supplied by the workspace owner (Pine v6).  |
//|                                                                  |
//| Public iCustom buffer contract:                                  |
//|   0/1  fill upper/lower       2 fill color index                 |
//|   3/5  upper/lower bands      4/6 band color indices             |
//|   7    basis                  8 basis color index                |
//|   9..14 visual S1L/S1S/S2L/S2S/S3L/S3S marker prices            |
//|   15   dc (smoothed dominant cycle period)                       |
//|   16   dc_valid              17 adaptive/fixed length            |
//|   18   KER                   19 KER percentile rank              |
//|   20   regime: 0 range, 1 trend, EMPTY during warm-up            |
//|   21   bandwidth             22 squeeze score                    |
//|   23   squeeze state         24 release                          |
//|   25..30 raw S1L/S1S/S2L/S2S/S3L/S3S flags                      |
//|   31   priority signal code: +/-1 S1, +/-2 S2, +/-3 S3           |
//|                                                                  |
//| For non-repainting EA decisions, consume buffer shift >= 1.      |
//+------------------------------------------------------------------+
#property copyright   "Workspace owner"
#property version     "1.00"
#property description "Adaptive KAMA/robust Bollinger Bands with regime, squeeze and S1/S2/S3 signals"
#property description "Single-file implementation; no external includes or indicator handles"

#property indicator_chart_window
#property indicator_buffers 48
#property indicator_plots   27

//--- Input enums keep the MT5 settings compact and explicit.
enum ENUM_MBB_LENGTH_MODE
  {
   MBB_LENGTH_ADAPTIVE=0, // Adaptive
   MBB_LENGTH_FIXED=1     // Fixed
  };

enum ENUM_MBB_BASIS_MODE
  {
   MBB_BASIS_KAMA=0, // KAMA
   MBB_BASIS_SMA=1   // SMA
  };

enum ENUM_MBB_BAND_MODE
  {
   MBB_BANDS_ROBUST=0, // Robust
   MBB_BANDS_STDEV=1   // Stdev
  };

//--- Adaptive length inputs
input group "Adaptive length"
input ENUM_MBB_LENGTH_MODE InpLengthMode        = MBB_LENGTH_ADAPTIVE; // Length mode
input int                  InpFixedLength       = 20;                  // Fixed length (>=2)

//--- Basis and band inputs
input group "Basis / bands"
input ENUM_MBB_BASIS_MODE  InpBasisMode         = MBB_BASIS_KAMA;      // Basis
input ENUM_MBB_BAND_MODE   InpBandMode          = MBB_BANDS_ROBUST;    // Bands
input double               InpStdevMultiplier   = 2.0;                 // Stdev multiplier
input double               InpRobustUpperPct    = 97.5;                // Robust upper percentile
input double               InpRobustLowerPct    = 2.5;                 // Robust lower percentile
input int                  InpRobustWindowMult  = 4;                   // Robust window multiplier
input int                  InpRobustWindowFloor = 80;                  // Robust window floor
input int                  InpKamaFast          = 2;                   // KAMA fast
input int                  InpKamaSlow          = 30;                  // KAMA slow

//--- Regime and squeeze inputs
input group "Regime / squeeze"
input int                  InpKerLength         = 20;   // KER length
input int                  InpRankLength        = 252;  // Percentile rank window
input double               InpTrendEnter        = 70.0; // TREND enter: KER pct >=
input double               InpTrendExit         = 55.0; // TREND exit: KER pct <=
input double               InpSqueezeThreshold  = 20.0; // Squeeze threshold: score <
input int                  InpSqueezeMinBars    = 5;    // Min bars before release

//--- Signal inputs
input group "Signals"
input double               InpBasisTouchFraction= 0.25; // S2 basis-touch fraction of halfwidth

//--- Display inputs
input group "Display"
input bool                 InpCleanMode         = false; // Clean display preset
input bool                 InpShowHud           = false; // HUD panel
input bool                 InpShowSignals       = true;  // Signal markers
input bool                 InpShowSqueezeHeat   = true;  // Squeeze heat on fill
input int                  InpS2Debounce        = 5;     // S2 marker debounce (bars; 0=all)
input color                InpRangeColor        = C'61,165,232';
input color                InpTrendColor        = C'232,163,61';
input color                InpS3LongColor       = C'125,220,130';
input color                InpS3ShortColor      = C'220,125,125';

//--- Alert inputs
input group "Closed-bar alerts"
input bool                 InpEnableAlerts      = true;  // Dynamic priority alert
input bool                 InpEnablePopupAlert  = true;  // MT5 popup/sound
input bool                 InpEnablePush        = false; // Mobile push

//--- Parity inputs
input group "Parity"
input bool                 InpUseStart          = false;                  // Gate computation at start time
input datetime             InpStartTime         = D'2023.01.01 00:00';    // UTC-equivalent data time

//--- Canonical constants from the supplied EACO v2.1 specification.
const int    MBB_LEN_MIN=10;
const int    MBB_LEN_MAX=50;
const int    MBB_DC_WARMUP=40;
const double MBB_MAX_PERIOD=50.0;
const double MBB_TWO_PI=6.283185307179586476925286766559;

//--- Visible plot buffers (0..14)
double ExtFillUpperBuffer[];
double ExtFillLowerBuffer[];
double ExtFillColorBuffer[];
double ExtUpperBandBuffer[];
double ExtUpperColorBuffer[];
double ExtLowerBandBuffer[];
double ExtLowerColorBuffer[];
double ExtBasisBuffer[];
double ExtBasisColorBuffer[];
double ExtS1LongMarkerBuffer[];
double ExtS1ShortMarkerBuffer[];
double ExtS2LongMarkerBuffer[];
double ExtS2ShortMarkerBuffer[];
double ExtS3LongMarkerBuffer[];
double ExtS3ShortMarkerBuffer[];

//--- Public parity/integration buffers (15..31)
double ExtDcBuffer[];
double ExtDcValidBuffer[];
double ExtLengthBuffer[];
double ExtKerBuffer[];
double ExtKerPctBuffer[];
double ExtRegimeBuffer[];
double ExtBandwidthBuffer[];
double ExtSqueezeScoreBuffer[];
double ExtSqueezeStateBuffer[];
double ExtReleaseBuffer[];
double ExtS1LongBuffer[];
double ExtS1ShortBuffer[];
double ExtS2LongBuffer[];
double ExtS2ShortBuffer[];
double ExtS3LongBuffer[];
double ExtS3ShortBuffer[];
double ExtSignalCodeBuffer[];

//--- Homodyne/internal state buffers (32..47)
double ExtSmoothBuffer[];
double ExtDetrenderBuffer[];
double ExtI1Buffer[];
double ExtQ1Buffer[];
double ExtI2Buffer[];
double ExtQ2Buffer[];
double ExtReBuffer[];
double ExtImBuffer[];
double ExtPeriodBuffer[];
double ExtBasisStartNBuffer[];
double ExtKamaPreviousBuffer[];
double ExtDeviationBuffer[];
double ExtSqueezeRunBuffer[];
double ExtLastS2LongIndexBuffer[];
double ExtLastS2ShortIndexBuffer[];
double ExtCycleValidBuffer[];

datetime g_lastLiveBarTime=0;
int      g_activeStartIndex=-1;
int      g_lastCalculatedIndex=-1;
string   g_lastSignal="—";
string   g_hudPrefix="";

//+------------------------------------------------------------------+
//| Value helpers.                                                   |
//+------------------------------------------------------------------+
bool IsUsableValue(const double value)
  {
   return(value!=EMPTY_VALUE && MathIsValidNumber(value));
  }

double NzAt(const double &buffer[],const int index)
  {
   if(index<0 || !IsUsableValue(buffer[index]))
      return(0.0);
   return(buffer[index]);
  }

int ClampInt(const int value,const int minimum,const int maximum)
  {
   return(MathMin(MathMax(value,minimum),maximum));
  }

double ClampDouble(const double value,const double minimum,const double maximum)
  {
   return(MathMin(MathMax(value,minimum),maximum));
  }

string SignalName(const int code)
  {
   switch(code)
     {
      case 1:  return("S1_LONG");
      case -1: return("S1_SHORT");
      case 2:  return("S2_LONG");
      case -2: return("S2_SHORT");
      case 3:  return("S3_LONG");
      case -3: return("S3_SHORT");
      default: return("—");
     }
  }

//+------------------------------------------------------------------+
//| Color helpers use MT5's BGR-packed color representation.         |
//+------------------------------------------------------------------+
int ColorRed(const color value)   { return((int)(((long)value)&0xFF)); }
int ColorGreen(const color value) { return((int)((((long)value)>>8)&0xFF)); }
int ColorBlue(const color value)  { return((int)((((long)value)>>16)&0xFF)); }

color MakeColor(const int red,const int green,const int blue)
  {
   return((color)(ClampInt(red,0,255) |
                  (ClampInt(green,0,255)<<8) |
                  (ClampInt(blue,0,255)<<16)));
  }

color BlendColor(const color foreground,const color background,const double strength)
  {
   const double weight=ClampDouble(strength,0.0,1.0);
   const int red=(int)MathRound(ColorRed(background)+(ColorRed(foreground)-ColorRed(background))*weight);
   const int green=(int)MathRound(ColorGreen(background)+(ColorGreen(foreground)-ColorGreen(background))*weight);
   const int blue=(int)MathRound(ColorBlue(background)+(ColorBlue(foreground)-ColorBlue(background))*weight);
   return(MakeColor(red,green,blue));
  }

color ChartBackgroundColor()
  {
   long value=0;
   if(ChartGetInteger(0,CHART_COLOR_BACKGROUND,0,value))
      return((color)value);
   return(clrBlack);
  }

color ChartTextColor()
  {
   const color background=ChartBackgroundColor();
   const int luminance=(299*ColorRed(background)+587*ColorGreen(background)+114*ColorBlue(background))/1000;
   return(luminance<128 ? clrWhite : clrBlack);
  }

//+------------------------------------------------------------------+
//| Configure dynamic plot colors for the active light/dark theme.   |
//+------------------------------------------------------------------+
void ApplyVisualStyle()
  {
   const color background=ChartBackgroundColor();
   const color neutral=C'128,128,128';

   //--- Fill palette: five squeeze-depth levels for warm-up/range/trend.
   PlotIndexSetInteger(0,PLOT_COLOR_INDEXES,15);
   for(int bin=0; bin<5; bin++)
     {
      const double strength=0.10+0.045*bin;
      PlotIndexSetInteger(0,PLOT_LINE_COLOR,bin,BlendColor(neutral,background,strength));
      PlotIndexSetInteger(0,PLOT_LINE_COLOR,5+bin,BlendColor(InpRangeColor,background,strength));
      PlotIndexSetInteger(0,PLOT_LINE_COLOR,10+bin,BlendColor(InpTrendColor,background,strength));
     }

   //--- Upper/lower lines are softer than the basis.
   for(int plot=1; plot<=2; plot++)
     {
      PlotIndexSetInteger(plot,PLOT_COLOR_INDEXES,3);
      PlotIndexSetInteger(plot,PLOT_LINE_COLOR,0,BlendColor(neutral,background,0.55));
      PlotIndexSetInteger(plot,PLOT_LINE_COLOR,1,BlendColor(InpRangeColor,background,0.62));
      PlotIndexSetInteger(plot,PLOT_LINE_COLOR,2,BlendColor(InpTrendColor,background,0.62));
     }

   PlotIndexSetInteger(3,PLOT_COLOR_INDEXES,3);
   PlotIndexSetInteger(3,PLOT_LINE_COLOR,0,neutral);
   PlotIndexSetInteger(3,PLOT_LINE_COLOR,1,InpRangeColor);
   PlotIndexSetInteger(3,PLOT_LINE_COLOR,2,InpTrendColor);

   PlotIndexSetInteger(4,PLOT_LINE_COLOR,InpRangeColor);
   PlotIndexSetInteger(5,PLOT_LINE_COLOR,InpRangeColor);
   PlotIndexSetInteger(6,PLOT_LINE_COLOR,InpTrendColor);
   PlotIndexSetInteger(7,PLOT_LINE_COLOR,InpTrendColor);
   PlotIndexSetInteger(8,PLOT_LINE_COLOR,InpS3LongColor);
   PlotIndexSetInteger(9,PLOT_LINE_COLOR,InpS3ShortColor);
  }

//+------------------------------------------------------------------+
//| Prior-window percentile rank: current bar excluded.              |
//+------------------------------------------------------------------+
bool PercentRankAt(const int index,
                   const double current,
                   const int length,
                   const double &source[],
                   double &result)
  {
   result=EMPTY_VALUE;
   if(!IsUsableValue(current) || index-length<0)
      return(false);

   int count=0;
   for(int offset=1; offset<=length; offset++)
     {
      const double previous=source[index-offset];
      if(!IsUsableValue(previous))
         return(false);
      if(previous<=current)
         count++;
     }

   result=100.0*(double)count/(double)length;
   return(true);
  }

//+------------------------------------------------------------------+
//| SMA of close over a dynamic chronological window.                |
//+------------------------------------------------------------------+
double CloseSMA(const int index,const int length,const double &close[])
  {
   if(length<1 || index-length+1<0)
      return(EMPTY_VALUE);
   double sum=0.0;
   for(int offset=0; offset<length; offset++)
      sum+=close[index-offset];
   return(sum/(double)length);
  }

//+------------------------------------------------------------------+
//| Nearest-rank robust percentile bands of close-basis deviations.  |
//+------------------------------------------------------------------+
bool RobustBandsAt(const int index,
                   const int length,
                   const double basis,
                   const double &deviation[],
                   double &upper,
                   double &lower)
  {
   const int windowLength=MathMax(InpRobustWindowMult*length,InpRobustWindowFloor);
   if(windowLength<1 || index-windowLength+1<0)
      return(false);

   double sorted[];
   if(ArrayResize(sorted,windowLength)!=windowLength)
      return(false);

   for(int offset=0; offset<windowLength; offset++)
     {
      const double value=deviation[index-offset];
      if(!IsUsableValue(value))
         return(false);
      sorted[offset]=value;
     }

   ArraySort(sorted);
   const int rankHigh=ClampInt((int)MathCeil(InpRobustUpperPct/100.0*windowLength),1,windowLength);
   const int rankLow=ClampInt((int)MathCeil(InpRobustLowerPct/100.0*windowLength),1,windowLength);
   upper=basis+sorted[rankHigh-1];
   lower=basis+sorted[rankLow-1];
   return(true);
  }

//+------------------------------------------------------------------+
//| Population standard-deviation bands.                             |
//+------------------------------------------------------------------+
bool StdevBandsAt(const int index,
                  const int length,
                  const double basis,
                  const double &close[],
                  double &upper,
                  double &lower)
  {
   const double mean=CloseSMA(index,length,close);
   if(!IsUsableValue(mean))
      return(false);

   double squaredSum=0.0;
   for(int offset=0; offset<length; offset++)
     {
      const double delta=close[index-offset]-mean;
      squaredSum+=delta*delta;
     }

   const double standardDeviation=MathSqrt(MathMax(squaredSum/(double)length,0.0));
   upper=basis+InpStdevMultiplier*standardDeviation;
   lower=basis-InpStdevMultiplier*standardDeviation;
   return(true);
  }

//+------------------------------------------------------------------+
//| HUD helpers.                                                     |
//+------------------------------------------------------------------+
string HudObjectName(const string suffix)
  {
   return(g_hudPrefix+suffix);
  }

void DeleteHud()
  {
   ObjectDelete(0,HudObjectName("BG"));
   for(int row=0; row<5; row++)
     {
      ObjectDelete(0,HudObjectName("K"+IntegerToString(row)));
      ObjectDelete(0,HudObjectName("V"+IntegerToString(row)));
     }
  }

void EnsureHudLabel(const string name,
                    const int x,
                    const int y,
                    const string text,
                    const color textColor,
                    const int fontSize=8)
  {
   if(ObjectFind(0,name)<0)
      ObjectCreate(0,name,OBJ_LABEL,0,0,0);
   ObjectSetInteger(0,name,OBJPROP_CORNER,CORNER_RIGHT_UPPER);
   ObjectSetInteger(0,name,OBJPROP_ANCHOR,ANCHOR_RIGHT_UPPER);
   ObjectSetInteger(0,name,OBJPROP_XDISTANCE,x);
   ObjectSetInteger(0,name,OBJPROP_YDISTANCE,y);
   ObjectSetInteger(0,name,OBJPROP_COLOR,textColor);
   ObjectSetInteger(0,name,OBJPROP_FONTSIZE,fontSize);
   ObjectSetInteger(0,name,OBJPROP_SELECTABLE,false);
   ObjectSetInteger(0,name,OBJPROP_HIDDEN,true);
   ObjectSetInteger(0,name,OBJPROP_ZORDER,0);
   ObjectSetString(0,name,OBJPROP_FONT,"Segoe UI");
   ObjectSetString(0,name,OBJPROP_TEXT,text);
  }

void UpdateHud(const int index)
  {
   if(InpCleanMode || !InpShowHud || index<0)
     {
      DeleteHud();
      return;
     }

   const color background=ChartBackgroundColor();
   const color textColor=ChartTextColor();
   const color muted=BlendColor(textColor,background,0.55);
   const string backgroundName=HudObjectName("BG");
   if(ObjectFind(0,backgroundName)<0)
      ObjectCreate(0,backgroundName,OBJ_RECTANGLE_LABEL,0,0,0);
   ObjectSetInteger(0,backgroundName,OBJPROP_CORNER,CORNER_RIGHT_UPPER);
   ObjectSetInteger(0,backgroundName,OBJPROP_XDISTANCE,10);
   ObjectSetInteger(0,backgroundName,OBJPROP_YDISTANCE,24);
   ObjectSetInteger(0,backgroundName,OBJPROP_XSIZE,210);
   ObjectSetInteger(0,backgroundName,OBJPROP_YSIZE,112);
   ObjectSetInteger(0,backgroundName,OBJPROP_BGCOLOR,BlendColor(textColor,background,0.10));
   ObjectSetInteger(0,backgroundName,OBJPROP_BORDER_COLOR,BlendColor(textColor,background,0.28));
   ObjectSetInteger(0,backgroundName,OBJPROP_SELECTABLE,false);
   ObjectSetInteger(0,backgroundName,OBJPROP_HIDDEN,true);
   ObjectSetInteger(0,backgroundName,OBJPROP_BACK,false);

   string keys[5]={"Regime","KER pct","Adaptive len","Squeeze","Last signal"};
   string values[5];
   color valueColors[5];

   if(!IsUsableValue(ExtRegimeBuffer[index]))
     {
      values[0]="warm-up";
      valueColors[0]=muted;
     }
   else if((int)ExtRegimeBuffer[index]==1)
     {
      values[0]="TREND";
      valueColors[0]=InpTrendColor;
     }
   else
     {
      values[0]="RANGE";
      valueColors[0]=InpRangeColor;
     }

   values[1]=IsUsableValue(ExtKerPctBuffer[index]) ? DoubleToString(ExtKerPctBuffer[index],1) : "—";
   valueColors[1]=textColor;

   if(IsUsableValue(ExtLengthBuffer[index]))
      values[2]=IntegerToString((int)ExtLengthBuffer[index])+(((int)ExtCycleValidBuffer[index])==1 ? "" : " (frozen)");
   else
      values[2]="—";
   valueColors[2]=textColor;

   values[3]=IsUsableValue(ExtSqueezeScoreBuffer[index]) ? DoubleToString(ExtSqueezeScoreBuffer[index],1) : "—";
   if(ExtSqueezeStateBuffer[index]>0.5)
      values[3]+="  ●";
   valueColors[3]=(ExtSqueezeStateBuffer[index]>0.5 ? InpS3LongColor : textColor);

   values[4]=g_lastSignal;
   valueColors[4]=textColor;

   for(int row=0; row<5; row++)
     {
      const int y=32+row*20;
      EnsureHudLabel(HudObjectName("K"+IntegerToString(row)),205,y,keys[row],muted,8);
      EnsureHudLabel(HudObjectName("V"+IntegerToString(row)),18,y,values[row],valueColors[row],8);
     }
  }

//+------------------------------------------------------------------+
//| Alert helpers.                                                   |
//+------------------------------------------------------------------+
void EmitMbbAlert(const string message)
  {
   Print(message);
   if(InpEnablePopupAlert)
      Alert(message);
   if(InpEnablePush &&
      !MQLInfoInteger(MQL_TESTER) &&
      TerminalInfoInteger(TERMINAL_NOTIFICATIONS_ENABLED))
      SendNotification(message);
  }

void ProcessClosedBarAlert(const int ratesTotal,const datetime &time[])
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
   if(!InpEnableAlerts)
      return;

   const int closedBar=ratesTotal-2;
   const int code=(int)ExtSignalCodeBuffer[closedBar];
   if(code==0)
      return;

   const string squeezeText=IsUsableValue(ExtSqueezeScoreBuffer[closedBar]) ?
                            DoubleToString(ExtSqueezeScoreBuffer[closedBar],2) : "null";
   const int regime=IsUsableValue(ExtRegimeBuffer[closedBar]) ? (int)ExtRegimeBuffer[closedBar] : -1;
   const string payload=StringFormat("{\"indicator\":\"GBB\",\"symbol\":\"%s\",\"tf\":\"%s\",\"signal\":\"%s\",\"regime\":%d,\"squeeze_score\":%s,\"upper\":%s,\"basis\":%s,\"lower\":%s}",
                                     _Symbol,
                                     EnumToString((ENUM_TIMEFRAMES)_Period),
                                     SignalName(code),
                                     regime,
                                     squeezeText,
                                     DoubleToString(ExtUpperBandBuffer[closedBar],_Digits),
                                     DoubleToString(ExtBasisBuffer[closedBar],_Digits),
                                     DoubleToString(ExtLowerBandBuffer[closedBar],_Digits));
   EmitMbbAlert(payload);
  }

//+------------------------------------------------------------------+
//| Initialize buffers for a full rebuild.                           |
//+------------------------------------------------------------------+
void InitializeBuffers()
  {
   ArrayInitialize(ExtFillUpperBuffer,EMPTY_VALUE);
   ArrayInitialize(ExtFillLowerBuffer,EMPTY_VALUE);
   ArrayInitialize(ExtFillColorBuffer,0.0);
   ArrayInitialize(ExtUpperBandBuffer,EMPTY_VALUE);
   ArrayInitialize(ExtUpperColorBuffer,0.0);
   ArrayInitialize(ExtLowerBandBuffer,EMPTY_VALUE);
   ArrayInitialize(ExtLowerColorBuffer,0.0);
   ArrayInitialize(ExtBasisBuffer,EMPTY_VALUE);
   ArrayInitialize(ExtBasisColorBuffer,0.0);
   ArrayInitialize(ExtS1LongMarkerBuffer,EMPTY_VALUE);
   ArrayInitialize(ExtS1ShortMarkerBuffer,EMPTY_VALUE);
   ArrayInitialize(ExtS2LongMarkerBuffer,EMPTY_VALUE);
   ArrayInitialize(ExtS2ShortMarkerBuffer,EMPTY_VALUE);
   ArrayInitialize(ExtS3LongMarkerBuffer,EMPTY_VALUE);
   ArrayInitialize(ExtS3ShortMarkerBuffer,EMPTY_VALUE);

   ArrayInitialize(ExtDcBuffer,0.0);
   ArrayInitialize(ExtDcValidBuffer,0.0);
   ArrayInitialize(ExtLengthBuffer,EMPTY_VALUE);
   ArrayInitialize(ExtKerBuffer,EMPTY_VALUE);
   ArrayInitialize(ExtKerPctBuffer,EMPTY_VALUE);
   ArrayInitialize(ExtRegimeBuffer,EMPTY_VALUE);
   ArrayInitialize(ExtBandwidthBuffer,EMPTY_VALUE);
   ArrayInitialize(ExtSqueezeScoreBuffer,EMPTY_VALUE);
   ArrayInitialize(ExtSqueezeStateBuffer,0.0);
   ArrayInitialize(ExtReleaseBuffer,0.0);
   ArrayInitialize(ExtS1LongBuffer,0.0);
   ArrayInitialize(ExtS1ShortBuffer,0.0);
   ArrayInitialize(ExtS2LongBuffer,0.0);
   ArrayInitialize(ExtS2ShortBuffer,0.0);
   ArrayInitialize(ExtS3LongBuffer,0.0);
   ArrayInitialize(ExtS3ShortBuffer,0.0);
   ArrayInitialize(ExtSignalCodeBuffer,0.0);

   ArrayInitialize(ExtSmoothBuffer,0.0);
   ArrayInitialize(ExtDetrenderBuffer,0.0);
   ArrayInitialize(ExtI1Buffer,0.0);
   ArrayInitialize(ExtQ1Buffer,0.0);
   ArrayInitialize(ExtI2Buffer,0.0);
   ArrayInitialize(ExtQ2Buffer,0.0);
   ArrayInitialize(ExtReBuffer,0.0);
   ArrayInitialize(ExtImBuffer,0.0);
   ArrayInitialize(ExtPeriodBuffer,0.0);
   ArrayInitialize(ExtBasisStartNBuffer,EMPTY_VALUE);
   ArrayInitialize(ExtKamaPreviousBuffer,EMPTY_VALUE);
   ArrayInitialize(ExtDeviationBuffer,EMPTY_VALUE);
   ArrayInitialize(ExtSqueezeRunBuffer,0.0);
   ArrayInitialize(ExtLastS2LongIndexBuffer,EMPTY_VALUE);
   ArrayInitialize(ExtLastS2ShortIndexBuffer,EMPTY_VALUE);
   ArrayInitialize(ExtCycleValidBuffer,0.0);
  }

//+------------------------------------------------------------------+
//| Plot setup.                                                      |
//+------------------------------------------------------------------+
void ConfigurePlots()
  {
   //--- 0: dynamic band fill (two values + color index)
   PlotIndexSetInteger(0,PLOT_DRAW_TYPE,DRAW_COLOR_HISTOGRAM2);
   PlotIndexSetInteger(0,PLOT_LINE_WIDTH,5);
   PlotIndexSetString(0,PLOT_LABEL,"Band fill");

   //--- 1/2/3: upper, lower and basis
   PlotIndexSetInteger(1,PLOT_DRAW_TYPE,DRAW_COLOR_LINE);
   PlotIndexSetInteger(1,PLOT_LINE_WIDTH,1);
   PlotIndexSetString(1,PLOT_LABEL,"Upper band");
   PlotIndexSetInteger(2,PLOT_DRAW_TYPE,DRAW_COLOR_LINE);
   PlotIndexSetInteger(2,PLOT_LINE_WIDTH,1);
   PlotIndexSetString(2,PLOT_LABEL,"Lower band");
   PlotIndexSetInteger(3,PLOT_DRAW_TYPE,DRAW_COLOR_LINE);
   PlotIndexSetInteger(3,PLOT_LINE_WIDTH,2);
   PlotIndexSetString(3,PLOT_LABEL,"Basis");

   //--- 4..9: signal markers
   for(int plot=4; plot<=9; plot++)
     {
      PlotIndexSetInteger(plot,PLOT_DRAW_TYPE,DRAW_ARROW);
      PlotIndexSetInteger(plot,PLOT_LINE_WIDTH,(plot>=8 ? 2 : 1));
     }
   PlotIndexSetInteger(4,PLOT_ARROW,241);
   PlotIndexSetInteger(5,PLOT_ARROW,242);
   PlotIndexSetInteger(6,PLOT_ARROW,159);
   PlotIndexSetInteger(7,PLOT_ARROW,159);
   PlotIndexSetInteger(8,PLOT_ARROW,117);
   PlotIndexSetInteger(9,PLOT_ARROW,117);
   PlotIndexSetString(4,PLOT_LABEL,"S1 long");
   PlotIndexSetString(5,PLOT_LABEL,"S1 short");
   PlotIndexSetString(6,PLOT_LABEL,"S2 long");
   PlotIndexSetString(7,PLOT_LABEL,"S2 short");
   PlotIndexSetString(8,PLOT_LABEL,"S3 long");
   PlotIndexSetString(9,PLOT_LABEL,"S3 short");

   string parityLabels[17]={"dc","dc_valid","len_adaptive","ker","ker_pct","regime","bw","squeeze_score","squeeze_state","release","s1_long","s1_short","s2_long","s2_short","s3_long","s3_short","signal_code"};
   for(int hidden=10; hidden<27; hidden++)
     {
      PlotIndexSetInteger(hidden,PLOT_DRAW_TYPE,DRAW_NONE);
      PlotIndexSetString(hidden,PLOT_LABEL,parityLabels[hidden-10]);
      PlotIndexSetInteger(hidden,PLOT_SHOW_DATA,InpUseStart);
     }

   // Pine uses display.pane for visible lines: keep MT5's status line clean.
   for(int visible=0; visible<10; visible++)
      PlotIndexSetInteger(visible,PLOT_SHOW_DATA,false);

   for(int plot=0; plot<27; plot++)
      PlotIndexSetDouble(plot,PLOT_EMPTY_VALUE,EMPTY_VALUE);

   ApplyVisualStyle();
  }

//+------------------------------------------------------------------+
//| Custom indicator initialization.                                |
//+------------------------------------------------------------------+
int OnInit()
  {
   if(InpFixedLength<2 ||
      InpStdevMultiplier<=0.0 ||
      InpRobustUpperPct<=0.0 || InpRobustUpperPct>100.0 ||
      InpRobustLowerPct<0.0 || InpRobustLowerPct>=100.0 ||
      InpRobustLowerPct>=InpRobustUpperPct ||
      InpRobustWindowMult<1 || InpRobustWindowFloor<1 ||
      InpKamaFast<1 || InpKamaSlow<1 || InpKamaFast>=InpKamaSlow ||
      InpKerLength<1 || InpRankLength<2 ||
      InpTrendEnter<0.0 || InpTrendEnter>100.0 ||
      InpTrendExit<0.0 || InpTrendExit>100.0 || InpTrendExit>=InpTrendEnter ||
      InpSqueezeThreshold<0.0 || InpSqueezeThreshold>100.0 ||
       InpSqueezeMinBars<0 || InpBasisTouchFraction<0.0 ||
      InpS2Debounce<0)
     {
      Print("Modern Bollinger Bands [GBB]: invalid input parameters.");
      return(INIT_PARAMETERS_INCORRECT);
     }

   //--- Visible plots
   SetIndexBuffer(0,ExtFillUpperBuffer,INDICATOR_DATA);
   SetIndexBuffer(1,ExtFillLowerBuffer,INDICATOR_DATA);
   SetIndexBuffer(2,ExtFillColorBuffer,INDICATOR_COLOR_INDEX);
   SetIndexBuffer(3,ExtUpperBandBuffer,INDICATOR_DATA);
   SetIndexBuffer(4,ExtUpperColorBuffer,INDICATOR_COLOR_INDEX);
   SetIndexBuffer(5,ExtLowerBandBuffer,INDICATOR_DATA);
   SetIndexBuffer(6,ExtLowerColorBuffer,INDICATOR_COLOR_INDEX);
   SetIndexBuffer(7,ExtBasisBuffer,INDICATOR_DATA);
   SetIndexBuffer(8,ExtBasisColorBuffer,INDICATOR_COLOR_INDEX);
   SetIndexBuffer(9,ExtS1LongMarkerBuffer,INDICATOR_DATA);
   SetIndexBuffer(10,ExtS1ShortMarkerBuffer,INDICATOR_DATA);
   SetIndexBuffer(11,ExtS2LongMarkerBuffer,INDICATOR_DATA);
   SetIndexBuffer(12,ExtS2ShortMarkerBuffer,INDICATOR_DATA);
   SetIndexBuffer(13,ExtS3LongMarkerBuffer,INDICATOR_DATA);
   SetIndexBuffer(14,ExtS3ShortMarkerBuffer,INDICATOR_DATA);

   //--- Public hidden plots
   SetIndexBuffer(15,ExtDcBuffer,INDICATOR_DATA);
   SetIndexBuffer(16,ExtDcValidBuffer,INDICATOR_DATA);
   SetIndexBuffer(17,ExtLengthBuffer,INDICATOR_DATA);
   SetIndexBuffer(18,ExtKerBuffer,INDICATOR_DATA);
   SetIndexBuffer(19,ExtKerPctBuffer,INDICATOR_DATA);
   SetIndexBuffer(20,ExtRegimeBuffer,INDICATOR_DATA);
   SetIndexBuffer(21,ExtBandwidthBuffer,INDICATOR_DATA);
   SetIndexBuffer(22,ExtSqueezeScoreBuffer,INDICATOR_DATA);
   SetIndexBuffer(23,ExtSqueezeStateBuffer,INDICATOR_DATA);
   SetIndexBuffer(24,ExtReleaseBuffer,INDICATOR_DATA);
   SetIndexBuffer(25,ExtS1LongBuffer,INDICATOR_DATA);
   SetIndexBuffer(26,ExtS1ShortBuffer,INDICATOR_DATA);
   SetIndexBuffer(27,ExtS2LongBuffer,INDICATOR_DATA);
   SetIndexBuffer(28,ExtS2ShortBuffer,INDICATOR_DATA);
   SetIndexBuffer(29,ExtS3LongBuffer,INDICATOR_DATA);
   SetIndexBuffer(30,ExtS3ShortBuffer,INDICATOR_DATA);
   SetIndexBuffer(31,ExtSignalCodeBuffer,INDICATOR_DATA);

   //--- Internal state
   SetIndexBuffer(32,ExtSmoothBuffer,INDICATOR_CALCULATIONS);
   SetIndexBuffer(33,ExtDetrenderBuffer,INDICATOR_CALCULATIONS);
   SetIndexBuffer(34,ExtI1Buffer,INDICATOR_CALCULATIONS);
   SetIndexBuffer(35,ExtQ1Buffer,INDICATOR_CALCULATIONS);
   SetIndexBuffer(36,ExtI2Buffer,INDICATOR_CALCULATIONS);
   SetIndexBuffer(37,ExtQ2Buffer,INDICATOR_CALCULATIONS);
   SetIndexBuffer(38,ExtReBuffer,INDICATOR_CALCULATIONS);
   SetIndexBuffer(39,ExtImBuffer,INDICATOR_CALCULATIONS);
   SetIndexBuffer(40,ExtPeriodBuffer,INDICATOR_CALCULATIONS);
   SetIndexBuffer(41,ExtBasisStartNBuffer,INDICATOR_CALCULATIONS);
   SetIndexBuffer(42,ExtKamaPreviousBuffer,INDICATOR_CALCULATIONS);
   SetIndexBuffer(43,ExtDeviationBuffer,INDICATOR_CALCULATIONS);
   SetIndexBuffer(44,ExtSqueezeRunBuffer,INDICATOR_CALCULATIONS);
   SetIndexBuffer(45,ExtLastS2LongIndexBuffer,INDICATOR_CALCULATIONS);
   SetIndexBuffer(46,ExtLastS2ShortIndexBuffer,INDICATOR_CALCULATIONS);
   SetIndexBuffer(47,ExtCycleValidBuffer,INDICATOR_CALCULATIONS);

   //--- All calculations use chronological indexing.
   ArraySetAsSeries(ExtFillUpperBuffer,false);
   ArraySetAsSeries(ExtFillLowerBuffer,false);
   ArraySetAsSeries(ExtFillColorBuffer,false);
   ArraySetAsSeries(ExtUpperBandBuffer,false);
   ArraySetAsSeries(ExtUpperColorBuffer,false);
   ArraySetAsSeries(ExtLowerBandBuffer,false);
   ArraySetAsSeries(ExtLowerColorBuffer,false);
   ArraySetAsSeries(ExtBasisBuffer,false);
   ArraySetAsSeries(ExtBasisColorBuffer,false);
   ArraySetAsSeries(ExtS1LongMarkerBuffer,false);
   ArraySetAsSeries(ExtS1ShortMarkerBuffer,false);
   ArraySetAsSeries(ExtS2LongMarkerBuffer,false);
   ArraySetAsSeries(ExtS2ShortMarkerBuffer,false);
   ArraySetAsSeries(ExtS3LongMarkerBuffer,false);
   ArraySetAsSeries(ExtS3ShortMarkerBuffer,false);
   ArraySetAsSeries(ExtDcBuffer,false);
   ArraySetAsSeries(ExtDcValidBuffer,false);
   ArraySetAsSeries(ExtLengthBuffer,false);
   ArraySetAsSeries(ExtKerBuffer,false);
   ArraySetAsSeries(ExtKerPctBuffer,false);
   ArraySetAsSeries(ExtRegimeBuffer,false);
   ArraySetAsSeries(ExtBandwidthBuffer,false);
   ArraySetAsSeries(ExtSqueezeScoreBuffer,false);
   ArraySetAsSeries(ExtSqueezeStateBuffer,false);
   ArraySetAsSeries(ExtReleaseBuffer,false);
   ArraySetAsSeries(ExtS1LongBuffer,false);
   ArraySetAsSeries(ExtS1ShortBuffer,false);
   ArraySetAsSeries(ExtS2LongBuffer,false);
   ArraySetAsSeries(ExtS2ShortBuffer,false);
   ArraySetAsSeries(ExtS3LongBuffer,false);
   ArraySetAsSeries(ExtS3ShortBuffer,false);
   ArraySetAsSeries(ExtSignalCodeBuffer,false);
   ArraySetAsSeries(ExtSmoothBuffer,false);
   ArraySetAsSeries(ExtDetrenderBuffer,false);
   ArraySetAsSeries(ExtI1Buffer,false);
   ArraySetAsSeries(ExtQ1Buffer,false);
   ArraySetAsSeries(ExtI2Buffer,false);
   ArraySetAsSeries(ExtQ2Buffer,false);
   ArraySetAsSeries(ExtReBuffer,false);
   ArraySetAsSeries(ExtImBuffer,false);
   ArraySetAsSeries(ExtPeriodBuffer,false);
   ArraySetAsSeries(ExtBasisStartNBuffer,false);
   ArraySetAsSeries(ExtKamaPreviousBuffer,false);
   ArraySetAsSeries(ExtDeviationBuffer,false);
   ArraySetAsSeries(ExtSqueezeRunBuffer,false);
   ArraySetAsSeries(ExtLastS2LongIndexBuffer,false);
   ArraySetAsSeries(ExtLastS2ShortIndexBuffer,false);
   ArraySetAsSeries(ExtCycleValidBuffer,false);

   ConfigurePlots();
   IndicatorSetString(INDICATOR_SHORTNAME,"MBB");
   IndicatorSetInteger(INDICATOR_DIGITS,_Digits);

   g_hudPrefix="MBB_GBB_"+StringFormat("%I64d",ChartID())+"_";
   g_lastLiveBarTime=0;
   g_activeStartIndex=-1;
   g_lastCalculatedIndex=-1;
   g_lastSignal="—";
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
   // Short histories can still produce fixed/SMA/Stdev outputs before the
   // regime percentile has warmed up, just as the Pine specification does.
   if(rates_total<2)
      return(0);

   ArraySetAsSeries(time,false);
   ArraySetAsSeries(open,false);
   ArraySetAsSeries(high,false);
   ArraySetAsSeries(low,false);
   ArraySetAsSeries(close,false);

   int start=0;
   if(prev_calculated<=0 || prev_calculated>rates_total)
     {
      InitializeBuffers();
      g_activeStartIndex=-1;
      g_lastSignal="—";
      start=0;
     }
   else
      start=MathMax(prev_calculated-1,0);

   if(g_activeStartIndex<0)
     {
      if(!InpUseStart)
         g_activeStartIndex=0;
      else
         {
          for(int cursor=0; cursor<rates_total; cursor++)
            {
             if(time[cursor]>=InpStartTime)
               {
               g_activeStartIndex=cursor;
               break;
              }
           }
        }
     }

   for(int index=start; index<rates_total && !IsStopped(); index++)
     {
      //--- Reset current-bar outputs before deterministic recalculation.
      ExtFillUpperBuffer[index]=EMPTY_VALUE;
      ExtFillLowerBuffer[index]=EMPTY_VALUE;
      ExtFillColorBuffer[index]=0.0;
      ExtUpperBandBuffer[index]=EMPTY_VALUE;
      ExtUpperColorBuffer[index]=0.0;
      ExtLowerBandBuffer[index]=EMPTY_VALUE;
      ExtLowerColorBuffer[index]=0.0;
      ExtBasisBuffer[index]=EMPTY_VALUE;
      ExtBasisColorBuffer[index]=0.0;
      ExtS1LongMarkerBuffer[index]=EMPTY_VALUE;
      ExtS1ShortMarkerBuffer[index]=EMPTY_VALUE;
      ExtS2LongMarkerBuffer[index]=EMPTY_VALUE;
      ExtS2ShortMarkerBuffer[index]=EMPTY_VALUE;
      ExtS3LongMarkerBuffer[index]=EMPTY_VALUE;
      ExtS3ShortMarkerBuffer[index]=EMPTY_VALUE;
      ExtDcBuffer[index]=0.0;
      ExtDcValidBuffer[index]=0.0;
      ExtLengthBuffer[index]=EMPTY_VALUE;
      ExtKerBuffer[index]=EMPTY_VALUE;
      ExtKerPctBuffer[index]=EMPTY_VALUE;
      ExtRegimeBuffer[index]=(index>0 ? ExtRegimeBuffer[index-1] : EMPTY_VALUE);
      ExtBandwidthBuffer[index]=EMPTY_VALUE;
      ExtSqueezeScoreBuffer[index]=EMPTY_VALUE;
      ExtSqueezeStateBuffer[index]=0.0;
      ExtReleaseBuffer[index]=0.0;
      ExtS1LongBuffer[index]=0.0;
      ExtS1ShortBuffer[index]=0.0;
      ExtS2LongBuffer[index]=0.0;
      ExtS2ShortBuffer[index]=0.0;
      ExtS3LongBuffer[index]=0.0;
      ExtS3ShortBuffer[index]=0.0;
      ExtSignalCodeBuffer[index]=0.0;
      ExtSmoothBuffer[index]=0.0;
      ExtDetrenderBuffer[index]=0.0;
      ExtI1Buffer[index]=0.0;
      ExtQ1Buffer[index]=0.0;
      ExtI2Buffer[index]=0.0;
      ExtQ2Buffer[index]=0.0;
      ExtReBuffer[index]=0.0;
      ExtImBuffer[index]=0.0;
      ExtPeriodBuffer[index]=0.0;
      ExtBasisStartNBuffer[index]=(index>0 ? ExtBasisStartNBuffer[index-1] : EMPTY_VALUE);
      ExtKamaPreviousBuffer[index]=(index>0 ? ExtKamaPreviousBuffer[index-1] : EMPTY_VALUE);
      ExtDeviationBuffer[index]=EMPTY_VALUE;
      ExtSqueezeRunBuffer[index]=(index>0 ? ExtSqueezeRunBuffer[index-1] : 0.0);
      ExtLastS2LongIndexBuffer[index]=(index>0 ? ExtLastS2LongIndexBuffer[index-1] : EMPTY_VALUE);
      ExtLastS2ShortIndexBuffer[index]=(index>0 ? ExtLastS2ShortIndexBuffer[index-1] : EMPTY_VALUE);
      ExtCycleValidBuffer[index]=0.0;

      const bool active=(!InpUseStart || time[index]>=InpStartTime) && index>=g_activeStartIndex;
      const int nsb=(active ? index-g_activeStartIndex : -1);

      //--- Homodyne Discriminator (canonical operation order).
      if(nsb>=6)
        {
         const double hl2Current=(high[index]+low[index])*0.5;
         const double hl2Prev1=(high[index-1]+low[index-1])*0.5;
         const double hl2Prev2=(high[index-2]+low[index-2])*0.5;
         const double hl2Prev3=(high[index-3]+low[index-3])*0.5;
         ExtSmoothBuffer[index]=(4.0*hl2Current+3.0*hl2Prev1+2.0*hl2Prev2+hl2Prev3)/10.0;

         const double previousPeriod=NzAt(ExtPeriodBuffer,index-1);
         const double multiplier=0.075*previousPeriod+0.54;
         ExtDetrenderBuffer[index]=(0.0962*ExtSmoothBuffer[index]+
                                    0.5769*NzAt(ExtSmoothBuffer,index-2)-
                                    0.5769*NzAt(ExtSmoothBuffer,index-4)-
                                    0.0962*NzAt(ExtSmoothBuffer,index-6))*multiplier;
         ExtQ1Buffer[index]=(0.0962*ExtDetrenderBuffer[index]+
                             0.5769*NzAt(ExtDetrenderBuffer,index-2)-
                             0.5769*NzAt(ExtDetrenderBuffer,index-4)-
                             0.0962*NzAt(ExtDetrenderBuffer,index-6))*multiplier;
         ExtI1Buffer[index]=NzAt(ExtDetrenderBuffer,index-3);

         const double jI=(0.0962*ExtI1Buffer[index]+
                           0.5769*NzAt(ExtI1Buffer,index-2)-
                           0.5769*NzAt(ExtI1Buffer,index-4)-
                           0.0962*NzAt(ExtI1Buffer,index-6))*multiplier;
         const double jQ=(0.0962*ExtQ1Buffer[index]+
                           0.5769*NzAt(ExtQ1Buffer,index-2)-
                           0.5769*NzAt(ExtQ1Buffer,index-4)-
                           0.0962*NzAt(ExtQ1Buffer,index-6))*multiplier;

         ExtI2Buffer[index]=0.2*(ExtI1Buffer[index]-jQ)+0.8*NzAt(ExtI2Buffer,index-1);
         ExtQ2Buffer[index]=0.2*(ExtQ1Buffer[index]+jI)+0.8*NzAt(ExtQ2Buffer,index-1);
         ExtReBuffer[index]=0.2*(ExtI2Buffer[index]*NzAt(ExtI2Buffer,index-1)+
                                  ExtQ2Buffer[index]*NzAt(ExtQ2Buffer,index-1))+
                                  0.8*NzAt(ExtReBuffer,index-1);
         ExtImBuffer[index]=0.2*(ExtI2Buffer[index]*NzAt(ExtQ2Buffer,index-1)-
                                  ExtQ2Buffer[index]*NzAt(ExtI2Buffer,index-1))+
                                  0.8*NzAt(ExtImBuffer,index-1);

         double rawPeriod=previousPeriod;
         if(ExtImBuffer[index]!=0.0 && ExtReBuffer[index]!=0.0)
            rawPeriod=MBB_TWO_PI/MathArctan(ExtImBuffer[index]/ExtReBuffer[index]);

         // Rate limits FIRST, hard clamp SECOND (EACO v2.1 canon).
         if(rawPeriod>1.5*previousPeriod)
            rawPeriod=1.5*previousPeriod;
         if(rawPeriod<0.67*previousPeriod)
            rawPeriod=0.67*previousPeriod;
         rawPeriod=ClampDouble(rawPeriod,6.0,MBB_MAX_PERIOD);

         ExtPeriodBuffer[index]=0.2*rawPeriod+0.8*previousPeriod;
         ExtDcBuffer[index]=0.33*ExtPeriodBuffer[index]+0.67*NzAt(ExtDcBuffer,index-1);
        }

      const bool cycleValid=(nsb>=MBB_DC_WARMUP && ExtDcBuffer[index]<MBB_MAX_PERIOD*0.85);
      ExtCycleValidBuffer[index]=(cycleValid ? 1.0 : 0.0);
      ExtDcValidBuffer[index]=(cycleValid ? 1.0 : 0.0);

      if(InpLengthMode==MBB_LENGTH_FIXED)
         ExtLengthBuffer[index]=(double)InpFixedLength;
      else if(cycleValid)
         ExtLengthBuffer[index]=(double)ClampInt((int)MathRound(ExtDcBuffer[index]/2.0),MBB_LEN_MIN,MBB_LEN_MAX);
      else if(index>0 && IsUsableValue(ExtLengthBuffer[index-1]))
         ExtLengthBuffer[index]=ExtLengthBuffer[index-1];

      //--- Basis start and KAMA/SMA basis.
      if(!IsUsableValue(ExtBasisStartNBuffer[index]) &&
         IsUsableValue(ExtLengthBuffer[index]) &&
         nsb>=(int)ExtLengthBuffer[index])
         ExtBasisStartNBuffer[index]=(double)nsb;

      if(IsUsableValue(ExtBasisStartNBuffer[index]) &&
         IsUsableValue(ExtLengthBuffer[index]) &&
         nsb>=(int)ExtLengthBuffer[index])
        {
         const int adaptiveLength=(int)ExtLengthBuffer[index];
         if(InpBasisMode==MBB_BASIS_SMA)
            ExtBasisBuffer[index]=CloseSMA(index,adaptiveLength,close);
         else
           {
            double kamaPrevious=(index>0 ? ExtKamaPreviousBuffer[index-1] : EMPTY_VALUE);
            if(nsb==(int)ExtBasisStartNBuffer[index])
               kamaPrevious=CloseSMA(index,adaptiveLength,close);

            if(IsUsableValue(kamaPrevious) && index-adaptiveLength>=0)
              {
               const double change=MathAbs(close[index]-close[index-adaptiveLength]);
               double volatility=0.0;
               for(int offset=0; offset<adaptiveLength; offset++)
                  volatility+=MathAbs(close[index-offset]-close[index-offset-1]);
               const double efficiencyRatio=(volatility>0.0 ? change/volatility : 0.0);
               const double fastSc=2.0/(InpKamaFast+1.0);
               const double slowSc=2.0/(InpKamaSlow+1.0);
               const double smoothingConstant=MathPow(efficiencyRatio*(fastSc-slowSc)+slowSc,2.0);
               ExtKamaPreviousBuffer[index]=kamaPrevious+smoothingConstant*(close[index]-kamaPrevious);
               ExtBasisBuffer[index]=ExtKamaPreviousBuffer[index];
              }
           }
        }

      //--- Bands.
      if(IsUsableValue(ExtBasisBuffer[index]))
        {
         ExtDeviationBuffer[index]=close[index]-ExtBasisBuffer[index];
         const int adaptiveLength=(int)ExtLengthBuffer[index];
         double upper=EMPTY_VALUE;
         double lower=EMPTY_VALUE;
         bool bandsCalculated=false;

         if(InpBandMode==MBB_BANDS_STDEV)
            bandsCalculated=StdevBandsAt(index,adaptiveLength,ExtBasisBuffer[index],close,upper,lower);
         else
           {
            const int fixedValidity=MathMax(InpRobustWindowMult*MBB_LEN_MAX,InpRobustWindowFloor);
            if(nsb-(int)ExtBasisStartNBuffer[index]+1>=fixedValidity)
               bandsCalculated=RobustBandsAt(index,adaptiveLength,ExtBasisBuffer[index],ExtDeviationBuffer,upper,lower);
           }

         if(bandsCalculated)
           {
            ExtUpperBandBuffer[index]=upper;
            ExtLowerBandBuffer[index]=lower;
           }
        }

      //--- KER and hysteretic regime gate.
      if(nsb>=InpKerLength && index-InpKerLength>=0)
        {
         const double change=MathAbs(close[index]-close[index-InpKerLength]);
         double volatility=0.0;
         for(int offset=0; offset<InpKerLength; offset++)
            volatility+=MathAbs(close[index-offset]-close[index-offset-1]);
         ExtKerBuffer[index]=(volatility>0.0 ? change/volatility : 0.0);
        }

      double kerPercentile=EMPTY_VALUE;
      if(PercentRankAt(index,ExtKerBuffer[index],InpRankLength,ExtKerBuffer,kerPercentile))
        {
         ExtKerPctBuffer[index]=kerPercentile;
         int regime=IsUsableValue(ExtRegimeBuffer[index]) ? (int)ExtRegimeBuffer[index] : 0;
         if(regime==0 && kerPercentile>=InpTrendEnter)
            regime=1;
         else if(regime==1 && kerPercentile<=InpTrendExit)
            regime=0;
         ExtRegimeBuffer[index]=(double)regime;
        }

      //--- Bandwidth and squeeze state.
      if(IsUsableValue(ExtUpperBandBuffer[index]) &&
         IsUsableValue(ExtLowerBandBuffer[index]) &&
         IsUsableValue(ExtBasisBuffer[index]) &&
         ExtBasisBuffer[index]!=0.0)
         ExtBandwidthBuffer[index]=(ExtUpperBandBuffer[index]-ExtLowerBandBuffer[index])/ExtBasisBuffer[index];

      double squeezePercentile=EMPTY_VALUE;
      if(PercentRankAt(index,ExtBandwidthBuffer[index],InpRankLength,ExtBandwidthBuffer,squeezePercentile))
        {
         ExtSqueezeScoreBuffer[index]=squeezePercentile;
         const bool inSqueeze=(squeezePercentile<InpSqueezeThreshold);
         const double previousRun=(index>0 ? ExtSqueezeRunBuffer[index-1] : 0.0);
         const bool release=(squeezePercentile>InpSqueezeThreshold &&
                             index>0 && IsUsableValue(ExtSqueezeScoreBuffer[index-1]) &&
                             ExtSqueezeScoreBuffer[index-1]<=InpSqueezeThreshold &&
                             previousRun>=InpSqueezeMinBars);
         ExtSqueezeStateBuffer[index]=(inSqueeze ? 1.0 : 0.0);
         ExtReleaseBuffer[index]=(release ? 1.0 : 0.0);
         ExtSqueezeRunBuffer[index]=(inSqueeze ? previousRun+1.0 : 0.0);
        }

      //--- Exact two-bar signal definitions.
      const bool bandsOk=(index>0 &&
                          IsUsableValue(ExtUpperBandBuffer[index]) &&
                          IsUsableValue(ExtUpperBandBuffer[index-1]) &&
                          IsUsableValue(ExtLowerBandBuffer[index]) &&
                          IsUsableValue(ExtRegimeBuffer[index]));
      const bool insideNow=(bandsOk && close[index]>=ExtLowerBandBuffer[index] && close[index]<=ExtUpperBandBuffer[index]);
      const bool s1Long=(bandsOk && (int)ExtRegimeBuffer[index]==0 && close[index-1]<ExtLowerBandBuffer[index-1] && insideNow);
      const bool s1Short=(bandsOk && (int)ExtRegimeBuffer[index]==0 && close[index-1]>ExtUpperBandBuffer[index-1] && insideNow);

      int trendDirection=0;
      bool s2Base=false;
      double previousHalfWidth=EMPTY_VALUE;
      if(bandsOk && nsb>=5 && index>=5 && IsUsableValue(ExtBasisBuffer[index-5]) &&
         IsUsableValue(ExtBasisBuffer[index-1]) && IsUsableValue(ExtLowerBandBuffer[index-1]))
        {
         trendDirection=(ExtBasisBuffer[index]>ExtBasisBuffer[index-5] ? 1 :
                         ExtBasisBuffer[index]<ExtBasisBuffer[index-5] ? -1 : 0);
         previousHalfWidth=(ExtUpperBandBuffer[index-1]-ExtLowerBandBuffer[index-1])*0.5;
         s2Base=((int)ExtRegimeBuffer[index]==1);
        }

      const bool s2Long=(s2Base && trendDirection==1 &&
                         low[index-1]<=ExtBasisBuffer[index-1]+InpBasisTouchFraction*previousHalfWidth &&
                         close[index-1]>=ExtBasisBuffer[index-1]-InpBasisTouchFraction*previousHalfWidth &&
                         close[index]>ExtBasisBuffer[index] && close[index]>close[index-1]);
      const bool s2Short=(s2Base && trendDirection==-1 &&
                          high[index-1]>=ExtBasisBuffer[index-1]-InpBasisTouchFraction*previousHalfWidth &&
                          close[index-1]<=ExtBasisBuffer[index-1]+InpBasisTouchFraction*previousHalfWidth &&
                          close[index]<ExtBasisBuffer[index] && close[index]<close[index-1]);
      const bool s3Long=(ExtReleaseBuffer[index]>0.5 && bandsOk && close[index]>ExtUpperBandBuffer[index]);
      const bool s3Short=(ExtReleaseBuffer[index]>0.5 && bandsOk && close[index]<ExtLowerBandBuffer[index]);

      ExtS1LongBuffer[index]=(s1Long ? 1.0 : 0.0);
      ExtS1ShortBuffer[index]=(s1Short ? 1.0 : 0.0);
      ExtS2LongBuffer[index]=(s2Long ? 1.0 : 0.0);
      ExtS2ShortBuffer[index]=(s2Short ? 1.0 : 0.0);
      ExtS3LongBuffer[index]=(s3Long ? 1.0 : 0.0);
      ExtS3ShortBuffer[index]=(s3Short ? 1.0 : 0.0);

      int signalCode=0;
      if(s1Long)         signalCode=1;
      else if(s1Short)   signalCode=-1;
      else if(s2Long)    signalCode=2;
      else if(s2Short)   signalCode=-2;
      else if(s3Long)    signalCode=3;
      else if(s3Short)   signalCode=-3;
      ExtSignalCodeBuffer[index]=(double)signalCode;

      //--- Display-only S2 debounce; raw buffers and alerts remain unchanged.
      const double previousLastS2Long=(index>0 ? ExtLastS2LongIndexBuffer[index-1] : EMPTY_VALUE);
      const double previousLastS2Short=(index>0 ? ExtLastS2ShortIndexBuffer[index-1] : EMPTY_VALUE);
      const bool s2LongMark=(s2Long && (InpS2Debounce==0 || !IsUsableValue(previousLastS2Long) || index-(int)previousLastS2Long>InpS2Debounce));
      const bool s2ShortMark=(s2Short && (InpS2Debounce==0 || !IsUsableValue(previousLastS2Short) || index-(int)previousLastS2Short>InpS2Debounce));
      ExtLastS2LongIndexBuffer[index]=(s2Long ? (double)index : previousLastS2Long);
      ExtLastS2ShortIndexBuffer[index]=(s2Short ? (double)index : previousLastS2Short);

      //--- Regime colors and dynamic squeeze-depth fill.
      int regimeColor=0;
      if(IsUsableValue(ExtRegimeBuffer[index]))
         regimeColor=((int)ExtRegimeBuffer[index]==1 ? 2 : 1);
      ExtUpperColorBuffer[index]=(double)regimeColor;
      ExtLowerColorBuffer[index]=(double)regimeColor;
      ExtBasisColorBuffer[index]=(double)regimeColor;

      if(!InpCleanMode && IsUsableValue(ExtUpperBandBuffer[index]) && IsUsableValue(ExtLowerBandBuffer[index]))
        {
         int heatBin=0;
         if(InpShowSqueezeHeat && IsUsableValue(ExtSqueezeScoreBuffer[index]))
            heatBin=ClampInt((int)MathFloor((100.0-ExtSqueezeScoreBuffer[index])/20.0),0,4);
         const int paletteBase=(regimeColor==2 ? 10 : regimeColor==1 ? 5 : 0);
         ExtFillUpperBuffer[index]=ExtUpperBandBuffer[index];
         ExtFillLowerBuffer[index]=ExtLowerBandBuffer[index];
         ExtFillColorBuffer[index]=(double)(paletteBase+heatBin);
        }

      //--- Marker prices are offset to avoid covering candles or each other.
      if(InpShowSignals && !InpCleanMode && bandsOk)
        {
         const double bandWidth=ExtUpperBandBuffer[index]-ExtLowerBandBuffer[index];
         const double barRange=MathMax(high[index]-low[index],10.0*_Point);
         const double gap=MathMax(bandWidth*0.08,barRange*0.25);
         if(s1Long)      ExtS1LongMarkerBuffer[index]=low[index]-gap;
         if(s1Short)     ExtS1ShortMarkerBuffer[index]=high[index]+gap;
         if(s2LongMark)  ExtS2LongMarkerBuffer[index]=low[index]-1.45*gap;
         if(s2ShortMark) ExtS2ShortMarkerBuffer[index]=high[index]+1.45*gap;
         if(s3Long)      ExtS3LongMarkerBuffer[index]=low[index]-1.90*gap;
         if(s3Short)     ExtS3ShortMarkerBuffer[index]=high[index]+1.90*gap;
        }

      if(index<rates_total-1 && signalCode!=0)
         g_lastSignal=SignalName(signalCode);
     }

   g_lastCalculatedIndex=rates_total-1;
   UpdateHud(g_lastCalculatedIndex);
   ProcessClosedBarAlert(rates_total,time);
   return(rates_total);
  }

//+------------------------------------------------------------------+
//| Chart events keep theme-aware colors and HUD placement current.  |
//+------------------------------------------------------------------+
void OnChartEvent(const int id,
                  const long &lparam,
                  const double &dparam,
                  const string &sparam)
  {
   if(id==CHARTEVENT_CHART_CHANGE)
     {
      ApplyVisualStyle();
      UpdateHud(g_lastCalculatedIndex);
     }
  }

//+------------------------------------------------------------------+
//| Remove only objects owned by this indicator instance.            |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
  {
   DeleteHud();
  }
//+------------------------------------------------------------------+
