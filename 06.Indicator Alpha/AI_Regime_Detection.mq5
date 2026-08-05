//+------------------------------------------------------------------+
//|                                      AI_Regime_Detection.mq5     |
//| Four-state Markov regime-switching indicator for MetaTrader 5.   |
//| Single-file port of the Pine v6 specification supplied by owner. |
//|                                                                  |
//| Public iCustom buffer contract:                                  |
//|   0/1/2  pane regime background top/bottom/color                 |
//|   3/4    confidence area/value color                             |
//|   5/6    confidence line/value color                            |
//|   7..10  P(Bull/Bear/Range/HighVol), percent                    |
//|   11     valid (0/1)          12 held regime (0..3)              |
//|   13     confirmed change     14 raw argmax regime               |
//|   15     raw argmax prob      16 trend correlation               |
//|   17     RSI momentum         18 vol percentile [0,1]            |
//|   19     normalized drift     20 realized volatility             |
//|   21     vol percentile [0,100]                                  |
//|   22     regime age           23 switch count                    |
//|   24     next likely regime   25 next probability                |
//|   26..41 transition A row-major                                  |
//|   42..57 emission means MU row-major                             |
//|   58..61 bars in regime; 62..65 episodes; 66..69 cumulative ret |
//|                                                                  |
//| Regimes: 0 Bull, 1 Bear, 2 Ranging, 3 High Volatility.           |
//| For non-repainting EA decisions, consume shift >= 1.             |
//+------------------------------------------------------------------+
#property copyright   "Workspace owner"
#property version     "1.00"
#property description "Four-state Hamilton filter with online EM and jump-penalty decoding"
#property description "Single-file deterministic replay; no external includes or indicator handles"

#property indicator_separate_window
#property indicator_minimum 0.0
#property indicator_maximum 100.0
#property indicator_buffers 82
#property indicator_plots   22

enum ENUM_AIRD_KERNEL
  {
   AIRD_KERNEL_LORENTZIAN=0, // Lorentzian (robust)
   AIRD_KERNEL_GAUSSIAN=1    // Gaussian
  };

enum ENUM_AIRD_DASH_POSITION
  {
   AIRD_TOP_RIGHT=0,    // Top right
   AIRD_TOP_LEFT=1,     // Top left
   AIRD_BOTTOM_RIGHT=2, // Bottom right
   AIRD_BOTTOM_LEFT=3   // Bottom left
  };

enum ENUM_AIRD_TEXT_SIZE
  {
   AIRD_TEXT_TINY=0,   // Tiny
   AIRD_TEXT_SMALL=1,  // Small
   AIRD_TEXT_NORMAL=2  // Normal
  };

input group "Model - Markov Regime Switching"
input double                  InpPersistence       = 0.92;  // Regime persistence (prior)
input double                  InpTransitionRate    = 0.010; // Learning rate - transition matrix
input double                  InpEmissionRate      = 0.010; // Learning rate - emission
input bool                    InpAdaptive          = true;  // Online learning (adaptive)
input ENUM_AIRD_KERNEL        InpKernel            = AIRD_KERNEL_LORENTZIAN;
input double                  InpSwitchMargin      = 0.05;  // Jump penalty - switch margin
input int                     InpConfirmBars       = 1;     // Jump penalty - confirm bars
input double                  InpTemperature       = 2.0;   // Likelihood tempering

input group "Features"
input int                     InpCorrelationLength = 50;  // Trend correlation length
input int                     InpRsiLength         = 14;  // RSI momentum length
input int                     InpVolatilityLength  = 20;  // Realized volatility length
input int                     InpVolRankLength     = 300; // Volatility percentile window
input int                     InpDriftLength       = 14;  // Drift smoothing length

input group "Appearance"
input bool                    InpShowBackground    = true; // Regime background color
input bool                    InpShowDashboard     = true; // Statistics dashboard
input bool                    InpShowPane          = true; // Confidence pane
input bool                    InpShowLabels        = true; // Label on confirmed regime change
input bool                    InpShowMatrix        = true; // Show transition matrix
input ENUM_AIRD_DASH_POSITION InpDashboardPosition= AIRD_TOP_RIGHT;
input ENUM_AIRD_TEXT_SIZE     InpTextSize          = AIRD_TEXT_SMALL;
input color                   InpBullColor         = C'0,230,118';
input color                   InpBearColor         = C'255,23,68';
input color                   InpRangeColor        = C'68,138,255';
input color                   InpHighVolColor      = C'255,179,0';

input group "Closed-bar alerts"
input bool                    InpEnableAlerts      = false; // Dynamic JSON regime-change alert
input bool                    InpEnablePopup       = true;  // Popup/sound when enabled
input bool                    InpEnablePush        = false; // Mobile push when enabled

const double AIRD_PI=3.1415926535897932384626433832795;
const color  AIRD_PANEL_BG=C'13,17,23';
const color  AIRD_PANEL_BORDER=C'31,41,55';
const color  AIRD_LABEL_COLOR=C'139,148,158';
const color  AIRD_VALUE_COLOR=C'230,237,243';
const color  AIRD_ACCENT_COLOR=C'0,229,255';

//--- Visible buffers 0..10.
double ExtBackgroundTop[];
double ExtBackgroundBottom[];
double ExtBackgroundColor[];
double ExtConfidenceArea[];
double ExtConfidenceAreaColor[];
double ExtConfidence[];
double ExtConfidenceColor[];
double ExtBullProbability[];
double ExtBearProbability[];
double ExtRangeProbability[];
double ExtHighVolProbability[];

//--- Public model/features/state buffers 11..69.
double ExtValid[];
double ExtRegime[];
double ExtChanged[];
double ExtRawRegime[];
double ExtRawProbability[];
double ExtTrendFeature[];
double ExtMomentumFeature[];
double ExtVolatilityFeature[];
double ExtDriftFeature[];
double ExtRealizedVolatility[];
double ExtVolatilityPercentile[];
double ExtRegimeAge[];
double ExtSwitches[];
double ExtNextRegime[];
double ExtNextProbability[];

double ExtA00[],ExtA01[],ExtA02[],ExtA03[];
double ExtA10[],ExtA11[],ExtA12[],ExtA13[];
double ExtA20[],ExtA21[],ExtA22[],ExtA23[];
double ExtA30[],ExtA31[],ExtA32[],ExtA33[];

double ExtMu00[],ExtMu01[],ExtMu02[],ExtMu03[];
double ExtMu10[],ExtMu11[],ExtMu12[],ExtMu13[];
double ExtMu20[],ExtMu21[],ExtMu22[],ExtMu23[];
double ExtMu30[],ExtMu31[],ExtMu32[],ExtMu33[];

double ExtBarsBull[],ExtBarsBear[],ExtBarsRange[],ExtBarsHighVol[];
double ExtEpisodesBull[],ExtEpisodesBear[],ExtEpisodesRange[],ExtEpisodesHighVol[];
double ExtReturnBull[],ExtReturnBear[],ExtReturnRange[],ExtReturnHighVol[];

//--- Internal deterministic replay buffers 70..81.
double ExtReturn[];
double ExtAverageGain[];
double ExtAverageLoss[];
double ExtEmaReturn[];
double ExtHeldRegime[];
double ExtCandidateRegime[];
double ExtCandidateCount[];
double ExtStatisticsStarted[];
double ExtAlphaBull[];
double ExtAlphaBear[];
double ExtAlphaRange[];
double ExtAlphaHighVol[];

double   g_muAnchor[16];
double   g_emissionScale[16];
string   g_objectPrefix="";
datetime g_lastLiveBarTime=0;
datetime g_lastVisualBarTime=0;
int      g_lastVisualRegime=-1;
int      g_lastVisualConfidenceBin=-1;
int      g_lastCalculatedIndex=-1;

//+------------------------------------------------------------------+
//| Numeric and display helpers.                                     |
//+------------------------------------------------------------------+
bool IsValue(const double value)
  {
   return(value!=EMPTY_VALUE && MathIsValidNumber(value));
  }

double ClampDouble(const double value,const double minimum,const double maximum)
  {
   return(MathMin(MathMax(value,minimum),maximum));
  }

int ClampInt(const int value,const int minimum,const int maximum)
  {
   return(MathMin(MathMax(value,minimum),maximum));
  }

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
   return(MakeColor((int)MathRound(ColorRed(background)+(ColorRed(foreground)-ColorRed(background))*weight),
                    (int)MathRound(ColorGreen(background)+(ColorGreen(foreground)-ColorGreen(background))*weight),
                    (int)MathRound(ColorBlue(background)+(ColorBlue(foreground)-ColorBlue(background))*weight)));
  }

color ChartBackground()
  {
   long packed=0;
   if(ChartGetInteger(0,CHART_COLOR_BACKGROUND,0,packed))
      return((color)packed);
   return(clrBlack);
  }

string RegimeName(const int regime)
  {
   if(regime==0) return("BULL TREND");
   if(regime==1) return("BEAR TREND");
   if(regime==2) return("RANGING");
   return("HIGH VOLATILITY");
  }

string RegimeIcon(const int regime)
  {
   if(regime==0) return("▲");
   if(regime==1) return("▼");
   if(regime==2) return("◆");
   return("⚡");
  }

color RegimeColor(const int regime)
  {
   if(regime==0) return(InpBullColor);
   if(regime==1) return(InpBearColor);
   if(regime==2) return(InpRangeColor);
   return(InpHighVolColor);
  }

string ProbabilityBar(const double probability)
  {
   const int filled=ClampInt((int)MathRound(ClampDouble(probability,0.0,1.0)*10.0),0,10);
   string result="";
   for(int slot=1; slot<=10; slot++)
      result+=(slot<=filled ? "▰" : "▱");
   return(result);
  }

double EmaStep(const double value,const double previous,const int length)
  {
   if(!IsValue(value))
      return(EMPTY_VALUE);
   if(!IsValue(previous))
      return(value);
   const double alpha=2.0/(length+1.0);
   return(alpha*value+(1.0-alpha)*previous);
  }

double LogPdf(const double value,const double mean,const double scale)
  {
   const double z=(value-mean)/scale;
   if(InpKernel==AIRD_KERNEL_LORENTZIAN)
      return(-MathLog(AIRD_PI*scale*(1.0+z*z)));
   return(-0.5*z*z-MathLog(scale*2.5066282746310005024));
  }

//+------------------------------------------------------------------+
//| Feature calculations use chronological (oldest-to-newest) arrays.|
//+------------------------------------------------------------------+
double PearsonCloseTime(const int index,const int length,const double &close[])
  {
   if(length<2 || index-length+1<0)
      return(EMPTY_VALUE);

   double meanClose=0.0;
   double meanTime=0.0;
   for(int offset=0; offset<length; offset++)
     {
      meanClose+=close[index-offset];
      meanTime+=(double)(index-offset);
     }
   meanClose/=length;
   meanTime/=length;

   double covariance=0.0;
   double varianceClose=0.0;
   double varianceTime=0.0;
   for(int offset=0; offset<length; offset++)
     {
      const double dx=close[index-offset]-meanClose;
      const double dy=(double)(index-offset)-meanTime;
      covariance+=dx*dy;
      varianceClose+=dx*dx;
      varianceTime+=dy*dy;
     }
   const double denominator=MathSqrt(varianceClose*varianceTime);
   return(denominator>0.0 ? covariance/denominator : EMPTY_VALUE);
  }

double PopulationStdev(const int index,const int length,const double &source[])
  {
   if(length<1 || index-length+1<0)
      return(EMPTY_VALUE);
   double mean=0.0;
   for(int offset=0; offset<length; offset++)
     {
      const double value=source[index-offset];
      if(!IsValue(value))
         return(EMPTY_VALUE);
      mean+=value;
     }
   mean/=length;
   double squared=0.0;
   for(int offset=0; offset<length; offset++)
     {
      const double delta=source[index-offset]-mean;
      squared+=delta*delta;
     }
   return(MathSqrt(MathMax(squared/length,0.0)));
  }

// TradingView ta.percentrank ranks the current observation inside its rolling
// window. Ties count as <=, preserving the source feature's 0..100 scale.
double PercentRankInclusive(const int index,const int length,const double &source[])
  {
   if(length<1 || index-length+1<0 || !IsValue(source[index]))
      return(EMPTY_VALUE);
   int count=0;
   for(int offset=0; offset<length; offset++)
     {
      const double value=source[index-offset];
      if(!IsValue(value))
         return(EMPTY_VALUE);
      if(value<=source[index])
         count++;
     }
   return(100.0*(double)count/(double)length);
  }

void CalculateRsi(const int index,const double &close[],double &averageGain,double &averageLoss,double &rsi)
  {
   averageGain=EMPTY_VALUE;
   averageLoss=EMPTY_VALUE;
   rsi=EMPTY_VALUE;
   if(index<InpRsiLength)
      return;

   if(index==InpRsiLength)
     {
      double gains=0.0;
      double losses=0.0;
      for(int cursor=1; cursor<=InpRsiLength; cursor++)
        {
         const double change=close[cursor]-close[cursor-1];
         gains+=MathMax(change,0.0);
         losses+=MathMax(-change,0.0);
        }
      averageGain=gains/InpRsiLength;
      averageLoss=losses/InpRsiLength;
     }
   else if(IsValue(ExtAverageGain[index-1]) && IsValue(ExtAverageLoss[index-1]))
     {
      const double change=close[index]-close[index-1];
      averageGain=(ExtAverageGain[index-1]*(InpRsiLength-1)+MathMax(change,0.0))/InpRsiLength;
      averageLoss=(ExtAverageLoss[index-1]*(InpRsiLength-1)+MathMax(-change,0.0))/InpRsiLength;
     }

   if(!IsValue(averageGain) || !IsValue(averageLoss))
      return;
   if(averageLoss==0.0)
      rsi=100.0;
   else if(averageGain==0.0)
      rsi=0.0;
   else
      rsi=100.0-100.0/(1.0+averageGain/averageLoss);
  }

//+------------------------------------------------------------------+
//| Matrix/bucket buffer loading and storage.                        |
//+------------------------------------------------------------------+
void InitializeModel(double &transition[],double &means[],double &alpha[])
  {
   for(int row=0; row<4; row++)
      for(int column=0; column<4; column++)
         transition[row*4+column]=(row==column ? InpPersistence : (1.0-InpPersistence)/3.0);
   for(int item=0; item<16; item++)
      means[item]=g_muAnchor[item];
   for(int regime=0; regime<4; regime++)
      alpha[regime]=0.25;
  }

void LoadTransition(const int index,double &values[])
  {
   values[0]=ExtA00[index]; values[1]=ExtA01[index]; values[2]=ExtA02[index]; values[3]=ExtA03[index];
   values[4]=ExtA10[index]; values[5]=ExtA11[index]; values[6]=ExtA12[index]; values[7]=ExtA13[index];
   values[8]=ExtA20[index]; values[9]=ExtA21[index]; values[10]=ExtA22[index]; values[11]=ExtA23[index];
   values[12]=ExtA30[index]; values[13]=ExtA31[index]; values[14]=ExtA32[index]; values[15]=ExtA33[index];
  }

void StoreTransition(const int index,const double &values[])
  {
   ExtA00[index]=values[0]; ExtA01[index]=values[1]; ExtA02[index]=values[2]; ExtA03[index]=values[3];
   ExtA10[index]=values[4]; ExtA11[index]=values[5]; ExtA12[index]=values[6]; ExtA13[index]=values[7];
   ExtA20[index]=values[8]; ExtA21[index]=values[9]; ExtA22[index]=values[10]; ExtA23[index]=values[11];
   ExtA30[index]=values[12]; ExtA31[index]=values[13]; ExtA32[index]=values[14]; ExtA33[index]=values[15];
  }

void LoadMeans(const int index,double &values[])
  {
   values[0]=ExtMu00[index]; values[1]=ExtMu01[index]; values[2]=ExtMu02[index]; values[3]=ExtMu03[index];
   values[4]=ExtMu10[index]; values[5]=ExtMu11[index]; values[6]=ExtMu12[index]; values[7]=ExtMu13[index];
   values[8]=ExtMu20[index]; values[9]=ExtMu21[index]; values[10]=ExtMu22[index]; values[11]=ExtMu23[index];
   values[12]=ExtMu30[index]; values[13]=ExtMu31[index]; values[14]=ExtMu32[index]; values[15]=ExtMu33[index];
  }

void StoreMeans(const int index,const double &values[])
  {
   ExtMu00[index]=values[0]; ExtMu01[index]=values[1]; ExtMu02[index]=values[2]; ExtMu03[index]=values[3];
   ExtMu10[index]=values[4]; ExtMu11[index]=values[5]; ExtMu12[index]=values[6]; ExtMu13[index]=values[7];
   ExtMu20[index]=values[8]; ExtMu21[index]=values[9]; ExtMu22[index]=values[10]; ExtMu23[index]=values[11];
   ExtMu30[index]=values[12]; ExtMu31[index]=values[13]; ExtMu32[index]=values[14]; ExtMu33[index]=values[15];
  }

void LoadAlpha(const int index,double &alpha[])
  {
   alpha[0]=ExtAlphaBull[index];
   alpha[1]=ExtAlphaBear[index];
   alpha[2]=ExtAlphaRange[index];
   alpha[3]=ExtAlphaHighVol[index];
  }

void StoreAlpha(const int index,const double &alpha[])
  {
   ExtAlphaBull[index]=alpha[0];
   ExtAlphaBear[index]=alpha[1];
   ExtAlphaRange[index]=alpha[2];
   ExtAlphaHighVol[index]=alpha[3];
  }

void LoadBuckets(const int index,double &barsIn[],double &episodes[],double &returns[])
  {
   barsIn[0]=ExtBarsBull[index]; barsIn[1]=ExtBarsBear[index]; barsIn[2]=ExtBarsRange[index]; barsIn[3]=ExtBarsHighVol[index];
   episodes[0]=ExtEpisodesBull[index]; episodes[1]=ExtEpisodesBear[index]; episodes[2]=ExtEpisodesRange[index]; episodes[3]=ExtEpisodesHighVol[index];
   returns[0]=ExtReturnBull[index]; returns[1]=ExtReturnBear[index]; returns[2]=ExtReturnRange[index]; returns[3]=ExtReturnHighVol[index];
  }

void StoreBuckets(const int index,const double &barsIn[],const double &episodes[],const double &returns[])
  {
   ExtBarsBull[index]=barsIn[0]; ExtBarsBear[index]=barsIn[1]; ExtBarsRange[index]=barsIn[2]; ExtBarsHighVol[index]=barsIn[3];
   ExtEpisodesBull[index]=episodes[0]; ExtEpisodesBear[index]=episodes[1]; ExtEpisodesRange[index]=episodes[2]; ExtEpisodesHighVol[index]=episodes[3];
   ExtReturnBull[index]=returns[0]; ExtReturnBear[index]=returns[1]; ExtReturnRange[index]=returns[2]; ExtReturnHighVol[index]=returns[3];
  }

//+------------------------------------------------------------------+
//| Plot configuration and theme-aware palettes.                     |
//+------------------------------------------------------------------+
void ApplyPlotColors()
  {
   const color background=ChartBackground();
   for(int regime=0; regime<4; regime++)
     {
      PlotIndexSetInteger(0,PLOT_LINE_COLOR,regime,(InpShowPane ? BlendColor(RegimeColor(regime),background,0.065) : clrNONE));
      PlotIndexSetInteger(1,PLOT_LINE_COLOR,regime,(InpShowPane ? BlendColor(RegimeColor(regime),background,0.28) : clrNONE));
      PlotIndexSetInteger(2,PLOT_LINE_COLOR,regime,(InpShowPane ? RegimeColor(regime) : clrNONE));
     }
   PlotIndexSetInteger(3,PLOT_LINE_COLOR,(InpShowPane ? InpBullColor : clrNONE));
   PlotIndexSetInteger(4,PLOT_LINE_COLOR,(InpShowPane ? InpBearColor : clrNONE));
   PlotIndexSetInteger(5,PLOT_LINE_COLOR,(InpShowPane ? InpRangeColor : clrNONE));
   PlotIndexSetInteger(6,PLOT_LINE_COLOR,(InpShowPane ? InpHighVolColor : clrNONE));
   IndicatorSetInteger(INDICATOR_LEVELCOLOR,0,(InpShowPane ? BlendColor(AIRD_ACCENT_COLOR,background,0.50) : clrNONE));
   IndicatorSetInteger(INDICATOR_LEVELCOLOR,1,(InpShowPane ? BlendColor(clrGray,background,0.45) : clrNONE));
   IndicatorSetInteger(INDICATOR_LEVELCOLOR,2,(InpShowPane ? BlendColor(clrGray,background,0.30) : clrNONE));
  }

void ConfigurePlots()
  {
   // Draw topology stays constant so public buffer numbering never changes
   // when appearance toggles are edited. Empty data/colors perform hiding.
   PlotIndexSetInteger(0,PLOT_DRAW_TYPE,DRAW_COLOR_HISTOGRAM2);
   PlotIndexSetInteger(0,PLOT_COLOR_INDEXES,4);
   PlotIndexSetInteger(0,PLOT_LINE_WIDTH,5);
   PlotIndexSetString(0,PLOT_LABEL,"Regime background");

   PlotIndexSetInteger(1,PLOT_DRAW_TYPE,DRAW_COLOR_HISTOGRAM);
   PlotIndexSetInteger(1,PLOT_COLOR_INDEXES,4);
   PlotIndexSetInteger(1,PLOT_LINE_WIDTH,4);
   PlotIndexSetString(1,PLOT_LABEL,"Confidence area");

   PlotIndexSetInteger(2,PLOT_DRAW_TYPE,DRAW_COLOR_LINE);
   PlotIndexSetInteger(2,PLOT_COLOR_INDEXES,4);
   PlotIndexSetInteger(2,PLOT_LINE_WIDTH,2);
   PlotIndexSetString(2,PLOT_LABEL,"Confidence");

   for(int plot=3; plot<=6; plot++)
     {
      PlotIndexSetInteger(plot,PLOT_DRAW_TYPE,DRAW_LINE);
      PlotIndexSetInteger(plot,PLOT_LINE_WIDTH,1);
     }
   PlotIndexSetString(3,PLOT_LABEL,"P(Bull)");
   PlotIndexSetString(4,PLOT_LABEL,"P(Bear)");
   PlotIndexSetString(5,PLOT_LABEL,"P(Ranging)");
   PlotIndexSetString(6,PLOT_LABEL,"P(HighVol)");

   string hiddenLabels[15]={"valid","regime","changed","raw_regime","raw_probability","trend","momentum","vol_percentile","drift","realized_volatility","vol_percentile_100","regime_age","switches","next_regime","next_probability"};
   for(int plot=7; plot<22; plot++)
     {
      PlotIndexSetInteger(plot,PLOT_DRAW_TYPE,DRAW_NONE);
      PlotIndexSetInteger(plot,PLOT_SHOW_DATA,true);
      PlotIndexSetString(plot,PLOT_LABEL,hiddenLabels[plot-7]);
     }

   PlotIndexSetInteger(0,PLOT_SHOW_DATA,false);
   PlotIndexSetInteger(1,PLOT_SHOW_DATA,false);
   for(int plot=0; plot<22; plot++)
      PlotIndexSetDouble(plot,PLOT_EMPTY_VALUE,EMPTY_VALUE);

   IndicatorSetInteger(INDICATOR_LEVELS,3);
   IndicatorSetDouble(INDICATOR_LEVELVALUE,0,80.0);
   IndicatorSetDouble(INDICATOR_LEVELVALUE,1,50.0);
   IndicatorSetDouble(INDICATOR_LEVELVALUE,2,25.0);
   IndicatorSetInteger(INDICATOR_LEVELSTYLE,0,STYLE_DOT);
   IndicatorSetInteger(INDICATOR_LEVELSTYLE,1,STYLE_DOT);
   IndicatorSetInteger(INDICATOR_LEVELSTYLE,2,STYLE_DOT);
   ApplyPlotColors();
  }

//+------------------------------------------------------------------+
//| Owned chart-object helpers.                                      |
//+------------------------------------------------------------------+
void DeleteObjectsByPrefix(const string prefix)
  {
   for(int position=ObjectsTotal(0,-1,-1)-1; position>=0; position--)
     {
      const string name=ObjectName(0,position,-1,-1);
      if(StringFind(name,prefix)==0)
         ObjectDelete(0,name);
     }
  }

string HudName(const string suffix)
  {
   return(g_objectPrefix+"HUD_"+suffix);
  }

ENUM_BASE_CORNER DashboardCorner()
  {
   if(InpDashboardPosition==AIRD_TOP_LEFT) return(CORNER_LEFT_UPPER);
   if(InpDashboardPosition==AIRD_BOTTOM_RIGHT) return(CORNER_RIGHT_LOWER);
   if(InpDashboardPosition==AIRD_BOTTOM_LEFT) return(CORNER_LEFT_LOWER);
   return(CORNER_RIGHT_UPPER);
  }

bool DashboardOnRight()
  {
   return(InpDashboardPosition==AIRD_TOP_RIGHT || InpDashboardPosition==AIRD_BOTTOM_RIGHT);
  }

bool DashboardOnBottom()
  {
   return(InpDashboardPosition==AIRD_BOTTOM_RIGHT || InpDashboardPosition==AIRD_BOTTOM_LEFT);
  }

int DashboardFontSize()
  {
   if(InpTextSize==AIRD_TEXT_TINY) return(6);
   if(InpTextSize==AIRD_TEXT_NORMAL) return(8);
   return(7);
  }

void EnsureHudLabel(const string name,const int x,const int y,const string text,const color textColor,const bool valueColumn,const int fontSize)
  {
   if(text=="")
     {
      ObjectDelete(0,name);
      return;
     }
   if(ObjectFind(0,name)<0)
      ObjectCreate(0,name,OBJ_LABEL,0,0,0);
   const bool right=DashboardOnRight();
   const bool bottom=DashboardOnBottom();
   ENUM_ANCHOR_POINT anchor=ANCHOR_LEFT_UPPER;
   if(valueColumn)
      anchor=(bottom ? ANCHOR_RIGHT_LOWER : ANCHOR_RIGHT_UPPER);
   else
      anchor=(bottom ? ANCHOR_LEFT_LOWER : ANCHOR_LEFT_UPPER);
   ObjectSetInteger(0,name,OBJPROP_CORNER,DashboardCorner());
   ObjectSetInteger(0,name,OBJPROP_ANCHOR,anchor);
   ObjectSetInteger(0,name,OBJPROP_XDISTANCE,x);
   ObjectSetInteger(0,name,OBJPROP_YDISTANCE,y);
   ObjectSetInteger(0,name,OBJPROP_COLOR,textColor);
   ObjectSetInteger(0,name,OBJPROP_FONTSIZE,fontSize);
   ObjectSetInteger(0,name,OBJPROP_SELECTABLE,false);
   ObjectSetInteger(0,name,OBJPROP_HIDDEN,true);
   ObjectSetInteger(0,name,OBJPROP_ZORDER,1);
   ObjectSetString(0,name,OBJPROP_FONT,"Consolas");
   ObjectSetString(0,name,OBJPROP_TEXT,text);
  }

void StationaryDistribution(const double &transition[],double &distribution[])
  {
   for(int regime=0; regime<4; regime++)
      distribution[regime]=0.25;
   for(int iteration=0; iteration<40; iteration++)
     {
      double next[4]={0.0,0.0,0.0,0.0};
      for(int column=0; column<4; column++)
         for(int row=0; row<4; row++)
            next[column]+=distribution[row]*transition[row*4+column];
      for(int regime=0; regime<4; regime++)
         distribution[regime]=next[regime];
     }
  }

void UpdateDashboard(const int index)
  {
   if(!InpShowDashboard || index<0)
     {
      DeleteObjectsByPrefix(g_objectPrefix+"HUD_");
      return;
     }

   const int fontSize=DashboardFontSize();
   const int smallSize=MathMax(fontSize-1,6);
   long chartHeightRaw=0;
   ChartGetInteger(0,CHART_HEIGHT_IN_PIXELS,0,chartHeightRaw);
   const int chartHeight=(int)MathMax(chartHeightRaw,160);
   const int rowHeight=ClampInt((chartHeight-12)/24,fontSize+2,fontSize+5);
   const int panelWidth=(InpTextSize==AIRD_TEXT_NORMAL ? 400 : 360);
   const int panelHeight=24*rowHeight+8;
   const int marginX=10;
   const int marginY=4;
   const bool right=DashboardOnRight();
   const bool bottom=DashboardOnBottom();

   const string backgroundName=HudName("BACKGROUND");
   if(ObjectFind(0,backgroundName)<0)
      ObjectCreate(0,backgroundName,OBJ_RECTANGLE_LABEL,0,0,0);
   ObjectSetInteger(0,backgroundName,OBJPROP_CORNER,DashboardCorner());
   // OBJ_RECTANGLE_LABEL keeps an upper-left geometry even when its base
   // corner is right/lower, unlike OBJ_LABEL anchors. Offset by its own size.
   ObjectSetInteger(0,backgroundName,OBJPROP_XDISTANCE,(right ? panelWidth+marginX : marginX));
   ObjectSetInteger(0,backgroundName,OBJPROP_YDISTANCE,(bottom ? panelHeight+marginY : marginY));
   ObjectSetInteger(0,backgroundName,OBJPROP_XSIZE,panelWidth);
   ObjectSetInteger(0,backgroundName,OBJPROP_YSIZE,panelHeight);
   ObjectSetInteger(0,backgroundName,OBJPROP_BGCOLOR,AIRD_PANEL_BG);
   ObjectSetInteger(0,backgroundName,OBJPROP_BORDER_COLOR,AIRD_PANEL_BORDER);
   ObjectSetInteger(0,backgroundName,OBJPROP_SELECTABLE,false);
   ObjectSetInteger(0,backgroundName,OBJPROP_HIDDEN,true);
   ObjectSetInteger(0,backgroundName,OBJPROP_BACK,false);
   ObjectSetInteger(0,backgroundName,OBJPROP_ZORDER,0);

   string left[24];
   string rightText[24];
   color leftColor[24];
   color rightColor[24];
   for(int row=0; row<24; row++)
     {
      left[row]="";
      rightText[row]="";
      leftColor[row]=AIRD_LABEL_COLOR;
      rightColor[row]=AIRD_VALUE_COLOR;
     }

   const bool valid=(ExtValid[index]>0.5);
   const int regime=ClampInt((int)ExtRegime[index],0,3);
   const double confidence=(valid && IsValue(ExtConfidence[index]) ? ExtConfidence[index]/100.0 : 0.25);
   double transition[16];
   LoadTransition(index,transition);
   double stationary[4];
   StationaryDistribution(transition,stationary);
   double barsIn[4],episodes[4],returns[4];
   LoadBuckets(index,barsIn,episodes,returns);
   double probabilities[4]={ExtAlphaBull[index],ExtAlphaBear[index],ExtAlphaRange[index],ExtAlphaHighVol[index]};

   const double totalBars=barsIn[0]+barsIn[1]+barsIn[2]+barsIn[3];
   const double averageDuration=barsIn[regime]/MathMax(episodes[regime],1.0);
   const double averageBps=(barsIn[regime]>0.0 ? returns[regime]/barsIn[regime]*10000.0 : 0.0);

   left[0]="AI REGIME DETECTION"; rightText[0]=(InpAdaptive ? "ONLINE EM" : "FIXED MODEL");
   leftColor[0]=AIRD_ACCENT_COLOR; rightColor[0]=AIRD_ACCENT_COLOR;
   left[1]="REGIME"; rightText[1]=(valid ? RegimeIcon(regime)+" "+RegimeName(regime) : "WARM-UP"); rightColor[1]=(valid ? RegimeColor(regime) : AIRD_LABEL_COLOR);
   left[2]="CONFIDENCE"; rightText[2]=ProbabilityBar(confidence)+" "+DoubleToString(confidence*100.0,0)+"%";
   rightColor[2]=(confidence>0.70 ? InpBullColor : confidence>0.45 ? C'255,213,79' : C'255,138,101');
   left[3]="── PROBABILITIES ──"; leftColor[3]=BlendColor(AIRD_ACCENT_COLOR,AIRD_PANEL_BG,0.65);
   for(int state=0; state<4; state++)
     {
      left[4+state]=RegimeIcon(state)+" "+RegimeName(state);
      rightText[4+state]=ProbabilityBar(probabilities[state])+" "+DoubleToString(probabilities[state]*100.0,1)+"%";
      rightColor[4+state]=(state==regime ? RegimeColor(state) : BlendColor(RegimeColor(state),AIRD_PANEL_BG,0.65));
     }
   left[8]="── STATISTICS ──"; leftColor[8]=BlendColor(AIRD_ACCENT_COLOR,AIRD_PANEL_BG,0.65);
   left[9]="VOLATILITY"; rightText[9]=(IsValue(ExtRealizedVolatility[index]) ? DoubleToString(ExtRealizedVolatility[index]*100.0,2)+"%  P"+DoubleToString(ExtVolatilityPercentile[index],0) : "—");
   if(IsValue(ExtVolatilityPercentile[index]) && ExtVolatilityPercentile[index]>80.0) rightColor[9]=InpHighVolColor;
   left[10]="TREND CORR"; rightText[10]=(IsValue(ExtTrendFeature[index]) ? (ExtTrendFeature[index]>=0.0 ? "+" : "")+DoubleToString(ExtTrendFeature[index],2) : "—");
   rightColor[10]=(IsValue(ExtTrendFeature[index]) && ExtTrendFeature[index]>0.3 ? InpBullColor : IsValue(ExtTrendFeature[index]) && ExtTrendFeature[index]<-0.3 ? InpBearColor : AIRD_VALUE_COLOR);
   left[11]="REGIME AGE"; rightText[11]=IntegerToString((int)ExtRegimeAge[index])+" bars";
   left[12]="AVG DURATION"; rightText[12]=DoubleToString(averageDuration,1)+" bars";
   left[13]="AVG RET/BAR"; rightText[13]=(averageBps>=0.0 ? "+" : "")+DoubleToString(averageBps,1)+" bps"; rightColor[13]=(averageBps>=0.0 ? InpBullColor : InpBearColor);
   left[14]="SWITCHES"; rightText[14]=IntegerToString((int)ExtSwitches[index]);
   const int nextRegime=(int)ExtNextRegime[index];
   left[15]="NEXT LIKELY"; rightText[15]=(nextRegime>=0 ? RegimeIcon(nextRegime)+" "+RegimeName(nextRegime)+"  "+DoubleToString(ExtNextProbability[index]*100.0,1)+"%" : "—"); rightColor[15]=(nextRegime>=0 ? RegimeColor(nextRegime) : AIRD_VALUE_COLOR);
   left[16]="TIME DIST";
   left[17]="LONG-RUN PI";
   for(int state=0; state<4; state++)
     {
      rightText[16]+=RegimeIcon(state)+DoubleToString(totalBars>0.0 ? 100.0*barsIn[state]/totalBars : 0.0,0)+" ";
      rightText[17]+=RegimeIcon(state)+DoubleToString(stationary[state]*100.0,0)+" ";
     }
   rightText[16]+="%"; rightText[17]+="%";
   left[18]=(InpShowMatrix ? "── TRANSITION MATRIX ──" : "── MATRIX HIDDEN ──"); leftColor[18]=BlendColor(AIRD_ACCENT_COLOR,AIRD_PANEL_BG,0.65);
   if(InpShowMatrix)
      for(int state=0; state<4; state++)
        {
         left[19+state]=RegimeIcon(state)+" →";
         rightText[19+state]=DoubleToString(transition[state*4],2)+"  "+DoubleToString(transition[state*4+1],2)+"  "+DoubleToString(transition[state*4+2],2)+"  "+DoubleToString(transition[state*4+3],2);
         rightColor[19+state]=(state==regime ? RegimeColor(state) : AIRD_LABEL_COLOR);
        }
   left[23]="MARKOV HMM";
   rightText[23]=(InpKernel==AIRD_KERNEL_LORENTZIAN ? "LORENTZIAN" : "GAUSSIAN")+(InpAdaptive ? " · ONLINE EM" : " · FIXED");
   leftColor[23]=AIRD_LABEL_COLOR; rightColor[23]=AIRD_LABEL_COLOR;

   for(int row=0; row<24; row++)
     {
      const int visualRow=(bottom ? 23-row : row);
      const int y=marginY+4+visualRow*rowHeight;
      const int keyX=(right ? panelWidth-12 : marginX+12);
      const int valueX=(right ? marginX+12 : panelWidth-12);
      EnsureHudLabel(HudName("L"+IntegerToString(row)),keyX,y,left[row],leftColor[row],false,(row==0 ? fontSize : smallSize));
      EnsureHudLabel(HudName("R"+IntegerToString(row)),valueX,y,rightText[row],rightColor[row],true,(row==0 ? smallSize : fontSize));
     }
  }

bool MainChartBounds(double &minimum,double &maximum)
  {
   minimum=0.0;
   maximum=0.0;
   return(ChartGetDouble(0,CHART_PRICE_MIN,0,minimum) && ChartGetDouble(0,CHART_PRICE_MAX,0,maximum) && maximum>minimum);
  }

void CreateBackgroundSegment(const int id,const datetime firstTime,const datetime lastTime,const int regime,const double confidence,const double minimum,const double maximum)
  {
   const string name=g_objectPrefix+"BG_"+IntegerToString(id);
   if(!ObjectCreate(0,name,OBJ_RECTANGLE,0,firstTime,maximum,lastTime,minimum))
      return;
   const double strength=0.015+0.045*ClampDouble(confidence,0.0,1.0);
   ObjectSetInteger(0,name,OBJPROP_COLOR,BlendColor(RegimeColor(regime),ChartBackground(),strength));
   ObjectSetInteger(0,name,OBJPROP_FILL,true);
   ObjectSetInteger(0,name,OBJPROP_BACK,true);
   ObjectSetInteger(0,name,OBJPROP_SELECTABLE,false);
   ObjectSetInteger(0,name,OBJPROP_HIDDEN,true);
   ObjectSetInteger(0,name,OBJPROP_ZORDER,0);
  }

void RebuildOverlayObjects(const int ratesTotal,const datetime &time[],const double &high[],const double &low[])
  {
   DeleteObjectsByPrefix(g_objectPrefix+"BG_");
   DeleteObjectsByPrefix(g_objectPrefix+"LBL_");
   if(ratesTotal<2)
      return;

   const int first=MathMax(0,ratesTotal-500);
   double minimum=0.0,maximum=0.0;
   const bool haveBounds=MainChartBounds(minimum,maximum);
   const int seconds=MathMax(PeriodSeconds((ENUM_TIMEFRAMES)_Period),1);

   if(InpShowBackground && haveBounds)
     {
      int segmentStart=-1;
      int segmentRegime=-1;
      double confidenceSum=0.0;
      int confidenceCount=0;
      int segmentId=0;
      for(int index=first; index<ratesTotal; index++)
        {
         const bool valid=(ExtValid[index]>0.5);
         const int regime=(valid ? (int)ExtRegime[index] : -1);
         if(segmentStart>=0 && (!valid || regime!=segmentRegime))
           {
            CreateBackgroundSegment(segmentId++,time[segmentStart],time[index],segmentRegime,confidenceSum/MathMax(confidenceCount,1),minimum,maximum);
            segmentStart=-1;
            confidenceSum=0.0;
            confidenceCount=0;
           }
         if(valid)
           {
            if(segmentStart<0)
              {
               segmentStart=index;
               segmentRegime=regime;
              }
            confidenceSum+=ExtConfidence[index]/100.0;
            confidenceCount++;
           }
        }
      if(segmentStart>=0)
         CreateBackgroundSegment(segmentId,time[segmentStart],time[ratesTotal-1]+seconds,segmentRegime,confidenceSum/MathMax(confidenceCount,1),minimum,maximum);
     }

   if(InpShowLabels && haveBounds)
     {
      const double offset=(maximum-minimum)*0.012;
      for(int index=MathMax(first,1); index<ratesTotal-1; index++)
        {
         if(ExtChanged[index]<0.5 || ExtValid[index]<0.5)
            continue;
         const int regime=(int)ExtRegime[index];
         const bool below=(regime==1);
         const string name=g_objectPrefix+"LBL_"+StringFormat("%I64d",(long)time[index]);
         const double price=(below ? low[index]-offset : high[index]+offset);
         if(!ObjectCreate(0,name,OBJ_TEXT,0,time[index],price))
            continue;
         string shortName=(regime==0 ? "BULL" : regime==1 ? "BEAR" : regime==2 ? "RANGE" : "HIGH VOL");
         if(!ObjectSetString(0,name,OBJPROP_TEXT,RegimeIcon(regime)+" "+shortName+" "+DoubleToString(ExtConfidence[index],0)+"%"))
           {
            ObjectDelete(0,name);
            continue;
           }
         ObjectSetString(0,name,OBJPROP_FONT,"Segoe UI Semibold");
         ObjectSetInteger(0,name,OBJPROP_FONTSIZE,7);
         ObjectSetInteger(0,name,OBJPROP_COLOR,RegimeColor(regime));
         ObjectSetInteger(0,name,OBJPROP_ANCHOR,(below ? ANCHOR_UPPER : ANCHOR_LOWER));
         ObjectSetInteger(0,name,OBJPROP_BACK,false);
         ObjectSetInteger(0,name,OBJPROP_SELECTABLE,false);
         ObjectSetInteger(0,name,OBJPROP_HIDDEN,true);
         ObjectSetInteger(0,name,OBJPROP_ZORDER,2);
        }
     }
  }

void UpdateBackgroundBounds()
  {
   double minimum=0.0,maximum=0.0;
   if(!MainChartBounds(minimum,maximum))
      return;
   const string prefix=g_objectPrefix+"BG_";
   for(int position=ObjectsTotal(0,0,OBJ_RECTANGLE)-1; position>=0; position--)
     {
      const string name=ObjectName(0,position,0,OBJ_RECTANGLE);
      if(StringFind(name,prefix)!=0)
         continue;
      ObjectSetDouble(0,name,OBJPROP_PRICE,0,maximum);
      ObjectSetDouble(0,name,OBJPROP_PRICE,1,minimum);
     }
  }

//+------------------------------------------------------------------+
//| Closed-bar alert.                                                |
//+------------------------------------------------------------------+
void ProcessAlert(const int ratesTotal,const datetime &time[])
  {
   if(ratesTotal<3)
      return;
   const datetime liveBar=time[ratesTotal-1];
   if(g_lastLiveBarTime==0)
     {
      g_lastLiveBarTime=liveBar;
      return;
     }
   if(liveBar==g_lastLiveBarTime)
      return;
   g_lastLiveBarTime=liveBar;
   if(!InpEnableAlerts)
      return;

   const int closed=ratesTotal-2;
   if(ExtChanged[closed]<0.5 || ExtValid[closed]<0.5)
      return;
   const int regime=(int)ExtRegime[closed];
   const string payload=StringFormat("{\"indicator\":\"AI_REGIME\",\"symbol\":\"%s\",\"tf\":\"%s\",\"regime\":%d,\"name\":\"%s\",\"confidence\":%.2f,\"p_bull\":%.2f,\"p_bear\":%.2f,\"p_range\":%.2f,\"p_highvol\":%.2f,\"next_regime\":%d,\"next_probability\":%.4f}",
                                     _Symbol,EnumToString((ENUM_TIMEFRAMES)_Period),regime,RegimeName(regime),ExtConfidence[closed],
                                     ExtBullProbability[closed],ExtBearProbability[closed],ExtRangeProbability[closed],ExtHighVolProbability[closed],
                                     (int)ExtNextRegime[closed],ExtNextProbability[closed]);
   Print(payload);
   if(InpEnablePopup)
      Alert(payload);
   if(InpEnablePush && !MQLInfoInteger(MQL_TESTER) && TerminalInfoInteger(TERMINAL_NOTIFICATIONS_ENABLED))
      SendNotification(payload);
  }

//+------------------------------------------------------------------+
//| Bind buffers and initialize the indicator.                       |
//+------------------------------------------------------------------+
int OnInit()
  {
   if(InpPersistence<0.50 || InpPersistence>0.99 ||
      InpTransitionRate<0.0 || InpTransitionRate>0.10 ||
      InpEmissionRate<0.0 || InpEmissionRate>0.10 ||
      InpSwitchMargin<0.0 || InpSwitchMargin>0.50 ||
      InpConfirmBars<1 || InpConfirmBars>10 ||
      InpTemperature<1.0 || InpTemperature>5.0 ||
      InpCorrelationLength<10 || InpRsiLength<2 ||
      InpVolatilityLength<5 || InpVolRankLength<50 || InpDriftLength<5)
     {
      Print("AI Regime Detection: invalid input parameters.");
      return(INIT_PARAMETERS_INCORRECT);
     }

   double muInit[16]={0.65,0.35,0.45,1.00, -0.65,-0.35,0.55,-1.00, 0.00,0.00,0.25,0.00, 0.00,0.00,0.90,0.00};
   double sdInit[16]={0.30,0.50,0.25,0.90, 0.30,0.50,0.25,0.90, 0.35,0.40,0.20,0.60, 0.60,0.80,0.12,1.50};
   ArrayCopy(g_muAnchor,muInit);
   ArrayCopy(g_emissionScale,sdInit);

   SetIndexBuffer(0,ExtBackgroundTop,INDICATOR_DATA);
   SetIndexBuffer(1,ExtBackgroundBottom,INDICATOR_DATA);
   SetIndexBuffer(2,ExtBackgroundColor,INDICATOR_COLOR_INDEX);
   SetIndexBuffer(3,ExtConfidenceArea,INDICATOR_DATA);
   SetIndexBuffer(4,ExtConfidenceAreaColor,INDICATOR_COLOR_INDEX);
   SetIndexBuffer(5,ExtConfidence,INDICATOR_DATA);
   SetIndexBuffer(6,ExtConfidenceColor,INDICATOR_COLOR_INDEX);
   SetIndexBuffer(7,ExtBullProbability,INDICATOR_DATA);
   SetIndexBuffer(8,ExtBearProbability,INDICATOR_DATA);
   SetIndexBuffer(9,ExtRangeProbability,INDICATOR_DATA);
   SetIndexBuffer(10,ExtHighVolProbability,INDICATOR_DATA);
   SetIndexBuffer(11,ExtValid,INDICATOR_DATA);
   SetIndexBuffer(12,ExtRegime,INDICATOR_DATA);
   SetIndexBuffer(13,ExtChanged,INDICATOR_DATA);
   SetIndexBuffer(14,ExtRawRegime,INDICATOR_DATA);
   SetIndexBuffer(15,ExtRawProbability,INDICATOR_DATA);
   SetIndexBuffer(16,ExtTrendFeature,INDICATOR_DATA);
   SetIndexBuffer(17,ExtMomentumFeature,INDICATOR_DATA);
   SetIndexBuffer(18,ExtVolatilityFeature,INDICATOR_DATA);
   SetIndexBuffer(19,ExtDriftFeature,INDICATOR_DATA);
   SetIndexBuffer(20,ExtRealizedVolatility,INDICATOR_DATA);
   SetIndexBuffer(21,ExtVolatilityPercentile,INDICATOR_DATA);
   SetIndexBuffer(22,ExtRegimeAge,INDICATOR_DATA);
   SetIndexBuffer(23,ExtSwitches,INDICATOR_DATA);
   SetIndexBuffer(24,ExtNextRegime,INDICATOR_DATA);
   SetIndexBuffer(25,ExtNextProbability,INDICATOR_DATA);
   SetIndexBuffer(26,ExtA00,INDICATOR_DATA); SetIndexBuffer(27,ExtA01,INDICATOR_DATA); SetIndexBuffer(28,ExtA02,INDICATOR_DATA); SetIndexBuffer(29,ExtA03,INDICATOR_DATA);
   SetIndexBuffer(30,ExtA10,INDICATOR_DATA); SetIndexBuffer(31,ExtA11,INDICATOR_DATA); SetIndexBuffer(32,ExtA12,INDICATOR_DATA); SetIndexBuffer(33,ExtA13,INDICATOR_DATA);
   SetIndexBuffer(34,ExtA20,INDICATOR_DATA); SetIndexBuffer(35,ExtA21,INDICATOR_DATA); SetIndexBuffer(36,ExtA22,INDICATOR_DATA); SetIndexBuffer(37,ExtA23,INDICATOR_DATA);
   SetIndexBuffer(38,ExtA30,INDICATOR_DATA); SetIndexBuffer(39,ExtA31,INDICATOR_DATA); SetIndexBuffer(40,ExtA32,INDICATOR_DATA); SetIndexBuffer(41,ExtA33,INDICATOR_DATA);
   SetIndexBuffer(42,ExtMu00,INDICATOR_DATA); SetIndexBuffer(43,ExtMu01,INDICATOR_DATA); SetIndexBuffer(44,ExtMu02,INDICATOR_DATA); SetIndexBuffer(45,ExtMu03,INDICATOR_DATA);
   SetIndexBuffer(46,ExtMu10,INDICATOR_DATA); SetIndexBuffer(47,ExtMu11,INDICATOR_DATA); SetIndexBuffer(48,ExtMu12,INDICATOR_DATA); SetIndexBuffer(49,ExtMu13,INDICATOR_DATA);
   SetIndexBuffer(50,ExtMu20,INDICATOR_DATA); SetIndexBuffer(51,ExtMu21,INDICATOR_DATA); SetIndexBuffer(52,ExtMu22,INDICATOR_DATA); SetIndexBuffer(53,ExtMu23,INDICATOR_DATA);
   SetIndexBuffer(54,ExtMu30,INDICATOR_DATA); SetIndexBuffer(55,ExtMu31,INDICATOR_DATA); SetIndexBuffer(56,ExtMu32,INDICATOR_DATA); SetIndexBuffer(57,ExtMu33,INDICATOR_DATA);
   SetIndexBuffer(58,ExtBarsBull,INDICATOR_DATA); SetIndexBuffer(59,ExtBarsBear,INDICATOR_DATA); SetIndexBuffer(60,ExtBarsRange,INDICATOR_DATA); SetIndexBuffer(61,ExtBarsHighVol,INDICATOR_DATA);
   SetIndexBuffer(62,ExtEpisodesBull,INDICATOR_DATA); SetIndexBuffer(63,ExtEpisodesBear,INDICATOR_DATA); SetIndexBuffer(64,ExtEpisodesRange,INDICATOR_DATA); SetIndexBuffer(65,ExtEpisodesHighVol,INDICATOR_DATA);
   SetIndexBuffer(66,ExtReturnBull,INDICATOR_DATA); SetIndexBuffer(67,ExtReturnBear,INDICATOR_DATA); SetIndexBuffer(68,ExtReturnRange,INDICATOR_DATA); SetIndexBuffer(69,ExtReturnHighVol,INDICATOR_DATA);
   SetIndexBuffer(70,ExtReturn,INDICATOR_CALCULATIONS);
   SetIndexBuffer(71,ExtAverageGain,INDICATOR_CALCULATIONS);
   SetIndexBuffer(72,ExtAverageLoss,INDICATOR_CALCULATIONS);
   SetIndexBuffer(73,ExtEmaReturn,INDICATOR_CALCULATIONS);
   SetIndexBuffer(74,ExtHeldRegime,INDICATOR_CALCULATIONS);
   SetIndexBuffer(75,ExtCandidateRegime,INDICATOR_CALCULATIONS);
   SetIndexBuffer(76,ExtCandidateCount,INDICATOR_CALCULATIONS);
   SetIndexBuffer(77,ExtStatisticsStarted,INDICATOR_CALCULATIONS);
   SetIndexBuffer(78,ExtAlphaBull,INDICATOR_CALCULATIONS);
   SetIndexBuffer(79,ExtAlphaBear,INDICATOR_CALCULATIONS);
   SetIndexBuffer(80,ExtAlphaRange,INDICATOR_CALCULATIONS);
   SetIndexBuffer(81,ExtAlphaHighVol,INDICATOR_CALCULATIONS);

   ArraySetAsSeries(ExtBackgroundTop,false); ArraySetAsSeries(ExtBackgroundBottom,false); ArraySetAsSeries(ExtBackgroundColor,false);
   ArraySetAsSeries(ExtConfidenceArea,false); ArraySetAsSeries(ExtConfidenceAreaColor,false); ArraySetAsSeries(ExtConfidence,false); ArraySetAsSeries(ExtConfidenceColor,false);
   ArraySetAsSeries(ExtBullProbability,false); ArraySetAsSeries(ExtBearProbability,false); ArraySetAsSeries(ExtRangeProbability,false); ArraySetAsSeries(ExtHighVolProbability,false);
   ArraySetAsSeries(ExtValid,false); ArraySetAsSeries(ExtRegime,false); ArraySetAsSeries(ExtChanged,false); ArraySetAsSeries(ExtRawRegime,false); ArraySetAsSeries(ExtRawProbability,false);
   ArraySetAsSeries(ExtTrendFeature,false); ArraySetAsSeries(ExtMomentumFeature,false); ArraySetAsSeries(ExtVolatilityFeature,false); ArraySetAsSeries(ExtDriftFeature,false);
   ArraySetAsSeries(ExtRealizedVolatility,false); ArraySetAsSeries(ExtVolatilityPercentile,false); ArraySetAsSeries(ExtRegimeAge,false); ArraySetAsSeries(ExtSwitches,false); ArraySetAsSeries(ExtNextRegime,false); ArraySetAsSeries(ExtNextProbability,false);
   ArraySetAsSeries(ExtA00,false); ArraySetAsSeries(ExtA01,false); ArraySetAsSeries(ExtA02,false); ArraySetAsSeries(ExtA03,false); ArraySetAsSeries(ExtA10,false); ArraySetAsSeries(ExtA11,false); ArraySetAsSeries(ExtA12,false); ArraySetAsSeries(ExtA13,false);
   ArraySetAsSeries(ExtA20,false); ArraySetAsSeries(ExtA21,false); ArraySetAsSeries(ExtA22,false); ArraySetAsSeries(ExtA23,false); ArraySetAsSeries(ExtA30,false); ArraySetAsSeries(ExtA31,false); ArraySetAsSeries(ExtA32,false); ArraySetAsSeries(ExtA33,false);
   ArraySetAsSeries(ExtMu00,false); ArraySetAsSeries(ExtMu01,false); ArraySetAsSeries(ExtMu02,false); ArraySetAsSeries(ExtMu03,false); ArraySetAsSeries(ExtMu10,false); ArraySetAsSeries(ExtMu11,false); ArraySetAsSeries(ExtMu12,false); ArraySetAsSeries(ExtMu13,false);
   ArraySetAsSeries(ExtMu20,false); ArraySetAsSeries(ExtMu21,false); ArraySetAsSeries(ExtMu22,false); ArraySetAsSeries(ExtMu23,false); ArraySetAsSeries(ExtMu30,false); ArraySetAsSeries(ExtMu31,false); ArraySetAsSeries(ExtMu32,false); ArraySetAsSeries(ExtMu33,false);
   ArraySetAsSeries(ExtBarsBull,false); ArraySetAsSeries(ExtBarsBear,false); ArraySetAsSeries(ExtBarsRange,false); ArraySetAsSeries(ExtBarsHighVol,false);
   ArraySetAsSeries(ExtEpisodesBull,false); ArraySetAsSeries(ExtEpisodesBear,false); ArraySetAsSeries(ExtEpisodesRange,false); ArraySetAsSeries(ExtEpisodesHighVol,false);
   ArraySetAsSeries(ExtReturnBull,false); ArraySetAsSeries(ExtReturnBear,false); ArraySetAsSeries(ExtReturnRange,false); ArraySetAsSeries(ExtReturnHighVol,false);
   ArraySetAsSeries(ExtReturn,false); ArraySetAsSeries(ExtAverageGain,false); ArraySetAsSeries(ExtAverageLoss,false); ArraySetAsSeries(ExtEmaReturn,false);
   ArraySetAsSeries(ExtHeldRegime,false); ArraySetAsSeries(ExtCandidateRegime,false); ArraySetAsSeries(ExtCandidateCount,false); ArraySetAsSeries(ExtStatisticsStarted,false);
   ArraySetAsSeries(ExtAlphaBull,false); ArraySetAsSeries(ExtAlphaBear,false); ArraySetAsSeries(ExtAlphaRange,false); ArraySetAsSeries(ExtAlphaHighVol,false);

   ConfigurePlots();
   IndicatorSetString(INDICATOR_SHORTNAME,"AI Regime Detection");
   IndicatorSetInteger(INDICATOR_DIGITS,2);
   g_objectPrefix="AIRD_"+StringFormat("%I64d",ChartID())+"_"+IntegerToString((int)GetTickCount())+"_";
   g_lastLiveBarTime=0;
   g_lastVisualBarTime=0;
   g_lastVisualRegime=-1;
   g_lastVisualConfidenceBin=-1;
   g_lastCalculatedIndex=-1;
   return(INIT_SUCCEEDED);
  }

//+------------------------------------------------------------------+
//| Hamilton filter, online EM, decoder, statistics and visuals.     |
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
   if(rates_total<2)
      return(0);
   ArraySetAsSeries(time,false); ArraySetAsSeries(open,false); ArraySetAsSeries(high,false); ArraySetAsSeries(low,false); ArraySetAsSeries(close,false);

   int start=(prev_calculated<=0 || prev_calculated>rates_total ? 0 : MathMax(prev_calculated-1,0));
   if(start==0)
     {
      DeleteObjectsByPrefix(g_objectPrefix+"BG_");
      DeleteObjectsByPrefix(g_objectPrefix+"LBL_");
      g_lastLiveBarTime=0;
     }

   for(int index=start; index<rates_total && !IsStopped(); index++)
     {
      ExtBackgroundTop[index]=EMPTY_VALUE; ExtBackgroundBottom[index]=EMPTY_VALUE; ExtBackgroundColor[index]=0.0;
      ExtConfidenceArea[index]=EMPTY_VALUE; ExtConfidenceAreaColor[index]=0.0; ExtConfidence[index]=EMPTY_VALUE; ExtConfidenceColor[index]=0.0;
      ExtBullProbability[index]=EMPTY_VALUE; ExtBearProbability[index]=EMPTY_VALUE; ExtRangeProbability[index]=EMPTY_VALUE; ExtHighVolProbability[index]=EMPTY_VALUE;
      ExtValid[index]=0.0; ExtChanged[index]=0.0; ExtRawRegime[index]=0.0; ExtRawProbability[index]=0.25;
      ExtTrendFeature[index]=EMPTY_VALUE; ExtMomentumFeature[index]=EMPTY_VALUE; ExtVolatilityFeature[index]=EMPTY_VALUE; ExtDriftFeature[index]=0.0;
      ExtRealizedVolatility[index]=EMPTY_VALUE; ExtVolatilityPercentile[index]=EMPTY_VALUE;
      ExtReturn[index]=EMPTY_VALUE; ExtAverageGain[index]=EMPTY_VALUE; ExtAverageLoss[index]=EMPTY_VALUE; ExtEmaReturn[index]=EMPTY_VALUE;

      double transition[16],means[16],alpha[4];
      double barsIn[4]={0.0,0.0,0.0,0.0};
      double episodes[4]={0.0,0.0,0.0,0.0};
      double returns[4]={0.0,0.0,0.0,0.0};
      int held=-1;
      int candidate=-1;
      int candidateCount=0;
      bool statisticsStarted=false;
      int regimeAge=0;
      int switchCount=0;

      if(index==0)
         InitializeModel(transition,means,alpha);
      else
        {
         LoadTransition(index-1,transition);
         LoadMeans(index-1,means);
         LoadAlpha(index-1,alpha);
         LoadBuckets(index-1,barsIn,episodes,returns);
         held=(int)ExtHeldRegime[index-1];
         candidate=(int)ExtCandidateRegime[index-1];
         candidateCount=(int)ExtCandidateCount[index-1];
         statisticsStarted=(ExtStatisticsStarted[index-1]>0.5);
         regimeAge=(int)ExtRegimeAge[index-1];
         switchCount=(int)ExtSwitches[index-1];
        }

      if(index>0 && close[index]>0.0 && close[index-1]>0.0)
         ExtReturn[index]=MathLog(close[index]/close[index-1]);

      const double trendRaw=PearsonCloseTime(index,InpCorrelationLength,close);
      ExtTrendFeature[index]=EmaStep(trendRaw,(index>0 ? ExtTrendFeature[index-1] : EMPTY_VALUE),3);

      double averageGain=EMPTY_VALUE,averageLoss=EMPTY_VALUE,rsi=EMPTY_VALUE;
      CalculateRsi(index,close,averageGain,averageLoss,rsi);
      ExtAverageGain[index]=averageGain;
      ExtAverageLoss[index]=averageLoss;
      const double momentumRaw=(IsValue(rsi) ? (rsi-50.0)/25.0 : EMPTY_VALUE);
      ExtMomentumFeature[index]=EmaStep(momentumRaw,(index>0 ? ExtMomentumFeature[index-1] : EMPTY_VALUE),3);

      ExtRealizedVolatility[index]=PopulationStdev(index,InpVolatilityLength,ExtReturn);
      ExtVolatilityPercentile[index]=PercentRankInclusive(index,InpVolRankLength,ExtRealizedVolatility);
      if(IsValue(ExtVolatilityPercentile[index]))
         ExtVolatilityFeature[index]=ExtVolatilityPercentile[index]/100.0;

      ExtEmaReturn[index]=EmaStep(ExtReturn[index],(index>0 ? ExtEmaReturn[index-1] : EMPTY_VALUE),InpDriftLength);
      if(IsValue(ExtRealizedVolatility[index]) && ExtRealizedVolatility[index]>0.0 && IsValue(ExtEmaReturn[index]))
         ExtDriftFeature[index]=ClampDouble(10.0*ExtEmaReturn[index]/ExtRealizedVolatility[index],-25.0,25.0);

      const bool valid=(index>InpVolRankLength && IsValue(ExtTrendFeature[index]) && IsValue(ExtMomentumFeature[index]) && IsValue(ExtVolatilityFeature[index]) && IsValue(ExtDriftFeature[index]));
      ExtValid[index]=(valid ? 1.0 : 0.0);

      if(valid)
        {
         double features[4]={ExtTrendFeature[index],ExtMomentumFeature[index],ExtVolatilityFeature[index],ExtDriftFeature[index]};
         double logLikelihood[4];
         double likelihood[4];
         double maximumLog=-1.0e308;
         for(int state=0; state<4; state++)
           {
            double value=0.0;
            for(int feature=0; feature<4; feature++)
               value+=LogPdf(features[feature],means[state*4+feature],g_emissionScale[state*4+feature]);
            value/=InpTemperature;
            logLikelihood[state]=value;
            maximumLog=MathMax(maximumLog,value);
           }
         for(int state=0; state<4; state++)
            likelihood[state]=MathMax(MathExp(logLikelihood[state]-maximumLog),1.0e-10);

         double previousAlpha[4];
         for(int state=0; state<4; state++) previousAlpha[state]=alpha[state];
         double total=0.0;
         for(int column=0; column<4; column++)
           {
            double prediction=0.0;
            for(int row=0; row<4; row++)
               prediction+=previousAlpha[row]*transition[row*4+column];
            alpha[column]=prediction*likelihood[column];
            total+=alpha[column];
           }
         if(total>0.0 && MathIsValidNumber(total))
            for(int state=0; state<4; state++) alpha[state]/=total;
         else
            for(int state=0; state<4; state++) alpha[state]=0.25;

         if(InpAdaptive && InpTransitionRate>0.0)
           {
            for(int row=0; row<4; row++)
              {
               double rowPosterior[4];
               double rowTotal=0.0;
               for(int column=0; column<4; column++)
                 {
                  rowPosterior[column]=transition[row*4+column]*likelihood[column];
                  rowTotal+=rowPosterior[column];
                 }
               if(rowTotal>0.0)
                 {
                  const double weight=InpTransitionRate*previousAlpha[row];
                  for(int column=0; column<4; column++)
                     transition[row*4+column]=(1.0-weight)*transition[row*4+column]+weight*rowPosterior[column]/rowTotal;
                 }
              }
            for(int row=0; row<4; row++)
              {
               if(transition[row*4+row]>0.98)
                  transition[row*4+row]=0.98;
               double rowSum=0.0;
               for(int column=0; column<4; column++)
                 {
                  transition[row*4+column]=MathMax(transition[row*4+column],0.004);
                  rowSum+=transition[row*4+column];
                 }
               for(int column=0; column<4; column++)
                  transition[row*4+column]/=rowSum;
              }
           }

         if(InpAdaptive && InpEmissionRate>0.0)
            for(int state=0; state<4; state++)
              {
               const double responsibility=alpha[state];
               for(int feature=0; feature<4; feature++)
                 {
                  const int position=state*4+feature;
                  double mean=means[position];
                  mean+=InpEmissionRate*responsibility*(features[feature]-mean);
                  mean+=InpEmissionRate*0.5*(g_muAnchor[position]-mean);
                  means[position]=mean;
                 }
              }
        }

      int rawRegime=0;
      double rawProbability=alpha[0];
      for(int state=1; state<4; state++)
         if(alpha[state]>rawProbability)
           {
            rawProbability=alpha[state];
            rawRegime=state;
           }
      ExtRawRegime[index]=(double)rawRegime;
      ExtRawProbability[index]=rawProbability;

      if(valid)
        {
         if(held==-1)
            held=rawRegime;
         else if(rawRegime!=held && rawProbability>alpha[held]+InpSwitchMargin)
           {
            if(rawRegime==candidate)
               candidateCount++;
            else
              {
               candidate=rawRegime;
               candidateCount=1;
              }
            if(candidateCount>=InpConfirmBars)
              {
               held=rawRegime;
               candidate=-1;
               candidateCount=0;
              }
           }
         else
           {
            candidate=-1;
            candidateCount=0;
           }
        }

      const int regime=(held==-1 ? rawRegime : held);
      const double confidence=alpha[regime];
      bool changed=false;
      if(valid)
        {
         if(!statisticsStarted)
           {
            statisticsStarted=true;
            episodes[regime]+=1.0;
           }
         else if(index>0 && regime!=(int)ExtRegime[index-1])
           {
            changed=true;
            switchCount++;
            regimeAge=0;
            episodes[regime]+=1.0;
           }
         else
            regimeAge++;
         barsIn[regime]+=1.0;
         if(IsValue(ExtReturn[index]))
            returns[regime]+=ExtReturn[index];
        }

      int nextRegime=-1;
      double nextProbability=-1.0;
      for(int state=0; state<4; state++)
         if(state!=regime && transition[regime*4+state]>nextProbability)
           {
            nextProbability=transition[regime*4+state];
            nextRegime=state;
           }

      ExtRegime[index]=(double)regime;
      ExtChanged[index]=(changed ? 1.0 : 0.0);
      ExtRegimeAge[index]=(double)regimeAge;
      ExtSwitches[index]=(double)switchCount;
      ExtNextRegime[index]=(double)nextRegime;
      ExtNextProbability[index]=nextProbability;
      ExtHeldRegime[index]=(double)held;
      ExtCandidateRegime[index]=(double)candidate;
      ExtCandidateCount[index]=(double)candidateCount;
      ExtStatisticsStarted[index]=(statisticsStarted ? 1.0 : 0.0);
      StoreTransition(index,transition);
      StoreMeans(index,means);
      StoreAlpha(index,alpha);
      StoreBuckets(index,barsIn,episodes,returns);

      if(valid)
        {
         ExtConfidence[index]=confidence*100.0;
         ExtBullProbability[index]=alpha[0]*100.0;
         ExtBearProbability[index]=alpha[1]*100.0;
         ExtRangeProbability[index]=alpha[2]*100.0;
         ExtHighVolProbability[index]=alpha[3]*100.0;
         ExtConfidenceColor[index]=(double)regime;
         ExtConfidenceAreaColor[index]=(double)regime;
         if(InpShowPane)
           {
            ExtConfidenceArea[index]=ExtConfidence[index];
            if(InpShowBackground)
              {
               ExtBackgroundTop[index]=100.0;
               ExtBackgroundBottom[index]=0.0;
               ExtBackgroundColor[index]=(double)regime;
              }
           }
        }
     }

   g_lastCalculatedIndex=rates_total-1;
   UpdateDashboard(g_lastCalculatedIndex);

   const int currentRegime=(ExtValid[g_lastCalculatedIndex]>0.5 ? (int)ExtRegime[g_lastCalculatedIndex] : -1);
   const int confidenceBin=(ExtValid[g_lastCalculatedIndex]>0.5 ? ClampInt((int)MathFloor(ExtConfidence[g_lastCalculatedIndex]/10.0),0,10) : -1);
   if(prev_calculated<=0 || time[rates_total-1]!=g_lastVisualBarTime || currentRegime!=g_lastVisualRegime || confidenceBin!=g_lastVisualConfidenceBin)
     {
      RebuildOverlayObjects(rates_total,time,high,low);
      g_lastVisualBarTime=time[rates_total-1];
      g_lastVisualRegime=currentRegime;
      g_lastVisualConfidenceBin=confidenceBin;
     }

   ProcessAlert(rates_total,time);
   return(rates_total);
  }

//+------------------------------------------------------------------+
//| Keep theme, dashboard, and overlay bounds current.               |
//+------------------------------------------------------------------+
void OnChartEvent(const int id,const long &lparam,const double &dparam,const string &sparam)
  {
   if(id==CHARTEVENT_CHART_CHANGE)
     {
      ApplyPlotColors();
      UpdateDashboard(g_lastCalculatedIndex);
      UpdateBackgroundBounds();
     }
  }

void OnDeinit(const int reason)
  {
   DeleteObjectsByPrefix(g_objectPrefix);
  }
//+------------------------------------------------------------------+
