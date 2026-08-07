//+------------------------------------------------------------------+
//|             Volatility_Regime_Classifier_QuantRegime.mq5        |
//| Volatility Regime Classifier [QuantRegime] - MT5 single file.    |
//| Pine v6 specification © wernert95, supplied by workspace owner.  |
//| Licensed under Mozilla Public License 2.0.                       |
//|                                                                  |
//| Public iCustom buffer contract:                                  |
//|   0..4   colored candle OHLC/color index                         |
//|   5..7   volatility fill upper/lower/color index                 |
//|   8/9    upper band / color index                                |
//|   10/11  lower band / color index                                |
//|   12/13  EMA21 basis / color index                               |
//|   14     smoothed Hurst       15 ADX                             |
//|   16     DI+                  17 DI-                             |
//|   18     Choppiness Index     19 ATR percentile [0..100]        |
//|   20     ATR                  21 composite score                 |
//|   22     direction            23 regime numeric                  |
//|   24     regime changed       25 previous regime                 |
//|   26     high-vol flag        27 low-vol flag                    |
//|   28     EMA21                29 EMA55                           |
//|   30     ROC(10)              31 stable/full-lookback valid      |
//|   32/33/34 trend/chop/Hurst component scores                     |
//|   35     raw Hurst                                              |
//|                                                                  |
//| Regimes preserve the Pine values:                                |
//|  -1 strong bear, 0 bear, 1 weak bear, 2 mean reverting,         |
//|   3 ranging, 4 weak bull, 5 bull, 6 strong bull, 7 compression. |
//| For non-repainting EA decisions, consume shift >= 1.             |
//+------------------------------------------------------------------+
#property copyright   "© wernert95; MQL5 port for workspace owner"
#property link        "https://mozilla.org/MPL/2.0/"
#property version     "1.00"
#property description "Nine-state Hurst/ADX/CHOP/ATR-percentile volatility regime classifier"
#property description "Single-file overlay with candles, bands, labels, dashboard and closed-bar alerts"

#property indicator_chart_window
#property indicator_buffers 44
#property indicator_plots   27

enum ENUM_VRC_DASH_POSITION
  {
   VRC_TOP_LEFT=0,     // Top Left
   VRC_TOP_RIGHT=1,    // Top Right
   VRC_BOTTOM_LEFT=2,  // Bottom Left
   VRC_BOTTOM_RIGHT=3, // Bottom Right
   VRC_MIDDLE_RIGHT=4  // Middle Right
  };

enum ENUM_VRC_DASH_SIZE
  {
   VRC_SIZE_SMALL=0,  // Small
   VRC_SIZE_NORMAL=1, // Normal
   VRC_SIZE_LARGE=2   // Large
  };

//--- Regime values from the supplied Pine specification.
const int VRC_REGIME_STRONG_BEAR=-1;
const int VRC_REGIME_BEAR=0;
const int VRC_REGIME_WEAK_BEAR=1;
const int VRC_REGIME_MEAN_REV=2;
const int VRC_REGIME_RANGING=3;
const int VRC_REGIME_WEAK_BULL=4;
const int VRC_REGIME_BULL=5;
const int VRC_REGIME_STRONG_BULL=6;
const int VRC_REGIME_COMPRESSION=7;

// Stable primitive ABI for Expert Advisors. Empty preserves chart inputs.
// Format: RSF1|hurst|adx|adxSmooth|chop|atr|volRank|adxTrend|adxStrong|
// chopRange|hurstTrend|hurstMR|volHigh|volLow.
input string InpEaContract=""; // EA contract (leave empty for chart use)

//--- Regime Detection Engine
input group "Regime Detection Engine"
input int InpHurstLength=100;             // Hurst Estimation Lookback (20..500)
input int InpAdxLength=14;                // ADX Length (5..50)
input int InpAdxSmoothing=14;             // ADX Smoothing (5..50)
input int InpChopLength=14;               // Choppiness Index Length (5..50)
input int InpVolatilityLength=20;         // Volatility Lookback ATR (5..100)
input int InpVolPercentileLength=100;     // Volatility Percentile Lookback (20..500)

//--- Regime Thresholds
input group "Regime Thresholds"
input double InpAdxTrendThreshold=25.0;   // ADX Trend Threshold
input double InpAdxStrongThreshold=40.0;  // ADX Strong Trend Threshold
input double InpChopRangeThreshold=61.8;  // Choppiness Range Threshold
input double InpHurstTrendThreshold=0.55; // Hurst Trending Threshold
input double InpHurstMrThreshold=0.45;    // Hurst Mean-Reversion Threshold
input double InpVolHighPercentile=80.0;   // High Volatility Percentile
input double InpVolLowPercentile=20.0;    // Low Volatility Percentile

//--- Visual Settings
input group "Visual Settings"
input bool InpShowCandleColor=true;             // Color Candles by Regime
input bool InpShowBackground=false;             // Color Background by Regime
input bool InpShowDashboard=true;               // Show Dashboard
input ENUM_VRC_DASH_POSITION InpDashPosition=VRC_TOP_RIGHT;
input ENUM_VRC_DASH_SIZE InpDashSize=VRC_SIZE_NORMAL;
input bool InpShowRegimeLabels=true;             // Show Regime Change Labels
input bool InpShowVolatilityBands=true;          // Show Volatility Bands
input double InpBandMultiplier=2.0;              // Volatility Band Multiplier

//--- Colors
input group "Colors"
input color InpStrongBullColor=C'0,200,83';      // Strong Bull Trend
input color InpWeakBullColor=C'129,199,132';     // Weak Bull Trend
input color InpStrongBearColor=C'255,23,68';     // Strong Bear Trend
input color InpWeakBearColor=C'229,115,115';     // Weak Bear Trend
input color InpRangingColor=C'255,214,0';        // Ranging / Choppy
input color InpMeanReversionColor=C'124,77,255'; // Mean Reverting
input color InpCompressionColor=C'0,188,212';    // Low Vol Compression

//--- Alerts. Pine alert toggles are honored and evaluated on closed bars.
input group "Closed-Bar Alerts"
input bool InpAlertRegimeChange=true;       // Alert on Regime Change
input bool InpAlertVolatilitySpike=true;    // Alert on Volatility Spike
input bool InpAlertCompression=true;        // Alert on Compression
input bool InpEnablePopupAlert=true;        // MT5 popup/sound
input bool InpEnablePushNotification=false; // Mobile push

int g_cfgHurstLength=0,g_cfgAdxLength=0,g_cfgAdxSmoothing=0,g_cfgChopLength=0;
int g_cfgVolatilityLength=0,g_cfgVolPercentileLength=0;
double g_cfgAdxTrendThreshold=0.0,g_cfgAdxStrongThreshold=0.0,g_cfgChopRangeThreshold=0.0;
double g_cfgHurstTrendThreshold=0.0,g_cfgHurstMrThreshold=0.0;
double g_cfgVolHighPercentile=0.0,g_cfgVolLowPercentile=0.0;

bool ResolveEaEngineContract()
  {
   if(StringLen(InpEaContract)==0)
     {
      g_cfgHurstLength=InpHurstLength; g_cfgAdxLength=InpAdxLength;
      g_cfgAdxSmoothing=InpAdxSmoothing; g_cfgChopLength=InpChopLength;
      g_cfgVolatilityLength=InpVolatilityLength; g_cfgVolPercentileLength=InpVolPercentileLength;
      g_cfgAdxTrendThreshold=InpAdxTrendThreshold; g_cfgAdxStrongThreshold=InpAdxStrongThreshold;
      g_cfgChopRangeThreshold=InpChopRangeThreshold; g_cfgHurstTrendThreshold=InpHurstTrendThreshold;
      g_cfgHurstMrThreshold=InpHurstMrThreshold; g_cfgVolHighPercentile=InpVolHighPercentile;
      g_cfgVolLowPercentile=InpVolLowPercentile;
      return(true);
     }
   string p[];
   if(StringSplit(InpEaContract,StringGetCharacter("|",0),p)!=14 || p[0]!="RSF1")
      return(false);
   g_cfgHurstLength=(int)StringToInteger(p[1]); g_cfgAdxLength=(int)StringToInteger(p[2]);
   g_cfgAdxSmoothing=(int)StringToInteger(p[3]); g_cfgChopLength=(int)StringToInteger(p[4]);
   g_cfgVolatilityLength=(int)StringToInteger(p[5]); g_cfgVolPercentileLength=(int)StringToInteger(p[6]);
   g_cfgAdxTrendThreshold=StringToDouble(p[7]); g_cfgAdxStrongThreshold=StringToDouble(p[8]);
   g_cfgChopRangeThreshold=StringToDouble(p[9]); g_cfgHurstTrendThreshold=StringToDouble(p[10]);
   g_cfgHurstMrThreshold=StringToDouble(p[11]); g_cfgVolHighPercentile=StringToDouble(p[12]);
   g_cfgVolLowPercentile=StringToDouble(p[13]);
   return(true);
  }

#define InpHurstLength            g_cfgHurstLength
#define InpAdxLength              g_cfgAdxLength
#define InpAdxSmoothing           g_cfgAdxSmoothing
#define InpChopLength             g_cfgChopLength
#define InpVolatilityLength       g_cfgVolatilityLength
#define InpVolPercentileLength    g_cfgVolPercentileLength
#define InpAdxTrendThreshold      g_cfgAdxTrendThreshold
#define InpAdxStrongThreshold     g_cfgAdxStrongThreshold
#define InpChopRangeThreshold     g_cfgChopRangeThreshold
#define InpHurstTrendThreshold    g_cfgHurstTrendThreshold
#define InpHurstMrThreshold       g_cfgHurstMrThreshold
#define InpVolHighPercentile      g_cfgVolHighPercentile
#define InpVolLowPercentile       g_cfgVolLowPercentile

const color VRC_PANEL_BG=C'26,26,46';
const color VRC_PANEL_ALT=C'15,52,96';
const color VRC_PANEL_BORDER=C'70,75,90';
const color VRC_LABEL_COLOR=C'155,160,170';
const color VRC_VALUE_COLOR=C'238,240,245';
const int   VRC_MAX_OBJECTS=500;

//--- Visible plot buffers 0..13.
double ExtCandleOpen[];
double ExtCandleHigh[];
double ExtCandleLow[];
double ExtCandleClose[];
double ExtCandleColor[];
double ExtFillUpper[];
double ExtFillLower[];
double ExtFillColor[];
double ExtUpperBand[];
double ExtUpperColor[];
double ExtLowerBand[];
double ExtLowerColor[];
double ExtBasis[];
double ExtBasisColor[];

//--- Public calculation buffers 14..35.
double ExtHurst[];
double ExtAdx[];
double ExtDiPlus[];
double ExtDiMinus[];
double ExtChop[];
double ExtVolPercentile[];
double ExtAtr[];
double ExtComposite[];
double ExtDirection[];
double ExtRegime[];
double ExtRegimeChanged[];
double ExtPreviousRegime[];
double ExtHighVol[];
double ExtLowVol[];
double ExtEmaFast[];
double ExtEmaSlow[];
double ExtRoc[];
double ExtValid[];
double ExtTrendScore[];
double ExtChopScore[];
double ExtHurstScore[];
double ExtHurstRaw[];

//--- Internal deterministic buffers 36..43.
double ExtLogReturn[];
double ExtTrueRange[];
double ExtPlusDm[];
double ExtMinusDm[];
double ExtDmiSmoothedTr[];
double ExtDmiSmoothedPlus[];
double ExtDmiSmoothedMinus[];
double ExtDx[];

string   g_objectPrefix="";
datetime g_lastLiveBarTime=0;
datetime g_lastVisualBarTime=0;
int      g_lastVisualRegime=999;
int      g_lastCalculatedIndex=-1;

//+------------------------------------------------------------------+
//| Numeric helpers.                                                 |
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
   return((int)MathMin(MathMax(value,minimum),maximum));
  }

color ChartBackground()
  {
   long raw=0;
   if(ChartGetInteger(0,CHART_COLOR_BACKGROUND,0,raw))
      return((color)raw);
   return(clrWhite);
  }

color BlendColor(const color foreground,const color background,const double strength)
  {
   const double weight=ClampDouble(strength,0.0,1.0);
   const int fr=(int)(foreground&0xFF);
   const int fg=(int)((foreground>>8)&0xFF);
   const int fb=(int)((foreground>>16)&0xFF);
   const int br=(int)(background&0xFF);
   const int bg=(int)((background>>8)&0xFF);
   const int bb=(int)((background>>16)&0xFF);
   const int red=(int)MathRound(br+(fr-br)*weight);
   const int green=(int)MathRound(bg+(fg-bg)*weight);
   const int blue=(int)MathRound(bb+(fb-bb)*weight);
   return((color)(red|(green<<8)|(blue<<16)));
  }

int RegimeColorIndex(const int regime)
  {
   return(ClampInt(regime+1,0,8));
  }

color RegimeColor(const int regime)
  {
   if(regime==VRC_REGIME_STRONG_BULL || regime==VRC_REGIME_BULL) return(InpStrongBullColor);
   if(regime==VRC_REGIME_WEAK_BULL) return(InpWeakBullColor);
   if(regime==VRC_REGIME_STRONG_BEAR || regime==VRC_REGIME_BEAR) return(InpStrongBearColor);
   if(regime==VRC_REGIME_WEAK_BEAR) return(InpWeakBearColor);
   if(regime==VRC_REGIME_MEAN_REV) return(InpMeanReversionColor);
   if(regime==VRC_REGIME_COMPRESSION) return(InpCompressionColor);
   return(InpRangingColor);
  }

string RegimeName(const int regime)
  {
   if(regime==VRC_REGIME_STRONG_BULL) return("Strong Bull Trend");
   if(regime==VRC_REGIME_BULL) return("Bull Trend");
   if(regime==VRC_REGIME_WEAK_BULL) return("Weak Bull");
   if(regime==VRC_REGIME_WEAK_BEAR) return("Weak Bear");
   if(regime==VRC_REGIME_BEAR) return("Bear Trend");
   if(regime==VRC_REGIME_STRONG_BEAR) return("Strong Bear Trend");
   if(regime==VRC_REGIME_MEAN_REV) return("Mean Reverting");
   if(regime==VRC_REGIME_COMPRESSION) return("Compression");
   return("Ranging");
  }

string RegimeIcon(const int regime)
  {
   if(regime==VRC_REGIME_STRONG_BULL) return("▲🔥");
   if(regime==VRC_REGIME_BULL) return("▲");
   if(regime==VRC_REGIME_WEAK_BULL) return("△");
   if(regime==VRC_REGIME_WEAK_BEAR) return("▽");
   if(regime==VRC_REGIME_BEAR) return("▼");
   if(regime==VRC_REGIME_STRONG_BEAR) return("▼🔥");
   if(regime==VRC_REGIME_MEAN_REV) return("↩");
   if(regime==VRC_REGIME_COMPRESSION) return("◌");
   return("↔");
  }

string StrategySuggestion(const int regime)
  {
   if(regime==VRC_REGIME_STRONG_BULL) return("Trend follow long, trail stops");
   if(regime==VRC_REGIME_BULL) return("Look for pullback longs");
   if(regime==VRC_REGIME_WEAK_BULL) return("Small longs, tight stops");
   if(regime==VRC_REGIME_WEAK_BEAR) return("Small shorts, tight stops");
   if(regime==VRC_REGIME_BEAR) return("Look for pullback shorts");
   if(regime==VRC_REGIME_STRONG_BEAR) return("Trend follow short, trail stops");
   if(regime==VRC_REGIME_MEAN_REV) return("Fade extremes, RSI reversals");
   if(regime==VRC_REGIME_COMPRESSION) return("Breakout may follow compression");
   return("Range trade support / resistance");
  }

//+------------------------------------------------------------------+
//| Calculation primitives matching Pine EMA/RMA conventions.       |
//+------------------------------------------------------------------+
double EmaAt(const double source,const double previous,const int period,const int index)
  {
   if(index<=0 || !IsValue(previous))
      return(source);
   const double alpha=2.0/(period+1.0);
   return(previous+alpha*(source-previous));
  }

double RmaAt(const double &source[],const double &output[],const int index,const int length,const int firstValidIndex)
  {
   const int seedIndex=firstValidIndex+length-1;
   if(index<seedIndex)
      return(EMPTY_VALUE);
   if(index==seedIndex)
     {
      double sum=0.0;
      for(int i=firstValidIndex;i<=seedIndex;i++)
        {
         if(!IsValue(source[i])) return(EMPTY_VALUE);
         sum+=source[i];
        }
      return(sum/length);
     }
   if(!IsValue(output[index-1]) || !IsValue(source[index]))
      return(EMPTY_VALUE);
   return((output[index-1]*(length-1)+source[index])/length);
  }

double HurstAt(const int index,const int length)
  {
   // Pine returns its neutral fallback until a full log-return window exists.
   if(index<length)
      return(0.5);

   double mean=0.0;
   for(int offset=0;offset<length;offset++)
     {
      const double value=ExtLogReturn[index-offset];
      if(!IsValue(value)) return(0.5);
      mean+=value;
     }
   mean/=length;

   double cumulative=0.0;
   double maximum=0.0;
   double minimum=0.0;
   double variance=0.0;
   for(int offset=0;offset<length;offset++)
     {
      const double deviation=ExtLogReturn[index-offset]-mean;
      cumulative+=deviation;
      maximum=MathMax(maximum,cumulative);
      minimum=MathMin(minimum,cumulative);
      variance+=deviation*deviation;
     }
   const double range=maximum-minimum;
   const double stdev=MathSqrt(variance/length); // Pine ta.stdev default: population
   const double rs=(stdev>0.0 ? range/stdev : 0.0);
   const double hurst=(rs>0.0 && length>1 ? MathLog(rs)/MathLog((double)length) : 0.5);
   return(ClampDouble(hurst,0.0,1.0));
  }

double ChoppinessAt(const int index,const int length,const double &high[],const double &low[])
  {
   if(index<length-1)
      return(EMPTY_VALUE);
   double sumTr=0.0;
   double highest=high[index];
   double lowest=low[index];
   for(int offset=0;offset<length;offset++)
     {
      const int position=index-offset;
      if(!IsValue(ExtTrueRange[position])) return(EMPTY_VALUE);
      sumTr+=ExtTrueRange[position];
      highest=MathMax(highest,high[position]);
      lowest=MathMin(lowest,low[position]);
     }
   const double priceRange=highest-lowest;
   if(priceRange<=0.0)
      return(50.0);
   const double ratio=sumTr/priceRange;
   if(ratio<=0.0)
      return(50.0);
   return(100.0*MathLog(ratio)/MathLog((double)length));
  }

double PercentileRankAt(const int index,const int length)
  {
   if(!IsValue(ExtAtr[index]))
      return(EMPTY_VALUE);
   int count=0;
   for(int offset=1;offset<=length;offset++)
     {
      const int position=index-offset;
      if(position>=0 && IsValue(ExtAtr[position]) && ExtAtr[position]<ExtAtr[index])
         count++;
     }
   // The supplied Pine function always divides by the requested length.
   return(100.0*count/length);
  }

//+------------------------------------------------------------------+
//| Object and dashboard helpers.                                   |
//+------------------------------------------------------------------+
void DeleteObjectsByPrefix(const string prefix)
  {
   // OnInit can fail before this instance receives its unique prefix.  Never
   // let a failed initialization interpret an empty prefix as "all objects".
   if(prefix=="")
      return;
   for(int i=ObjectsTotal(0)-1;i>=0;i--)
     {
      const string name=ObjectName(0,i);
      if(StringFind(name,prefix)==0)
         ObjectDelete(0,name);
     }
  }

ENUM_BASE_CORNER DashboardCorner()
  {
   if(InpDashPosition==VRC_TOP_LEFT) return(CORNER_LEFT_UPPER);
   if(InpDashPosition==VRC_BOTTOM_LEFT) return(CORNER_LEFT_LOWER);
   if(InpDashPosition==VRC_BOTTOM_RIGHT) return(CORNER_RIGHT_LOWER);
   return(CORNER_RIGHT_UPPER);
  }

bool DashboardOnRight()
  {
   return(InpDashPosition==VRC_TOP_RIGHT || InpDashPosition==VRC_BOTTOM_RIGHT || InpDashPosition==VRC_MIDDLE_RIGHT);
  }

bool DashboardOnBottom()
  {
   return(InpDashPosition==VRC_BOTTOM_LEFT || InpDashPosition==VRC_BOTTOM_RIGHT);
  }

int DashboardFontSize()
  {
   if(InpDashSize==VRC_SIZE_SMALL) return(7);
   if(InpDashSize==VRC_SIZE_LARGE) return(10);
   return(8);
  }

void EnsureDashboardLabel(const string suffix,const int x,const int y,const string text,const color textColor,const bool rightAnchor,const int fontSize)
  {
   const string name=g_objectPrefix+"HUD_"+suffix;
   if(text=="")
     {
      ObjectDelete(0,name);
      return;
     }
   if(ObjectFind(0,name)<0)
      ObjectCreate(0,name,OBJ_LABEL,0,0,0);
   const bool bottom=DashboardOnBottom();
   ENUM_ANCHOR_POINT anchor;
   if(rightAnchor)
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
   ObjectSetInteger(0,name,OBJPROP_ZORDER,2);
   ObjectSetString(0,name,OBJPROP_FONT,"Consolas");
   ObjectSetString(0,name,OBJPROP_TEXT,text);
  }

void UpdateDashboard(const int index)
  {
   if(!InpShowDashboard || index<0)
     {
      DeleteObjectsByPrefix(g_objectPrefix+"HUD_");
      return;
     }

   const int fontSize=DashboardFontSize();
   const int smallSize=MathMax(fontSize-1,7);
   const int rowHeight=fontSize+10;
   const int panelWidth=(InpDashSize==VRC_SIZE_SMALL ? 320 : InpDashSize==VRC_SIZE_LARGE ? 440 : 380);
   const int panelHeight=10*rowHeight+12;
   const int margin=10;
   const bool right=DashboardOnRight();
   const bool bottom=DashboardOnBottom();
   long chartHeightRaw=0;
   ChartGetInteger(0,CHART_HEIGHT_IN_PIXELS,0,chartHeightRaw);
   const int chartHeight=(int)MathMax(chartHeightRaw,panelHeight+20);
   const int middleY=(InpDashPosition==VRC_MIDDLE_RIGHT ? MathMax((chartHeight-panelHeight)/2,4) : margin);

   const string backgroundName=g_objectPrefix+"HUD_BACKGROUND";
   if(ObjectFind(0,backgroundName)<0)
      ObjectCreate(0,backgroundName,OBJ_RECTANGLE_LABEL,0,0,0);
   ObjectSetInteger(0,backgroundName,OBJPROP_CORNER,DashboardCorner());
   ObjectSetInteger(0,backgroundName,OBJPROP_XDISTANCE,(right ? panelWidth+margin : margin));
   ObjectSetInteger(0,backgroundName,OBJPROP_YDISTANCE,(bottom ? panelHeight+margin : middleY));
   ObjectSetInteger(0,backgroundName,OBJPROP_XSIZE,panelWidth);
   ObjectSetInteger(0,backgroundName,OBJPROP_YSIZE,panelHeight);
   ObjectSetInteger(0,backgroundName,OBJPROP_BGCOLOR,VRC_PANEL_BG);
   ObjectSetInteger(0,backgroundName,OBJPROP_BORDER_COLOR,VRC_PANEL_BORDER);
   ObjectSetInteger(0,backgroundName,OBJPROP_SELECTABLE,false);
   ObjectSetInteger(0,backgroundName,OBJPROP_HIDDEN,true);
   ObjectSetInteger(0,backgroundName,OBJPROP_BACK,false);
   ObjectSetInteger(0,backgroundName,OBJPROP_ZORDER,1);

   string left[10],middle[10],rightText[10];
   color leftColor[10],middleColor[10],rightColor[10];
   for(int row=0;row<10;row++)
     {
      left[row]=""; middle[row]=""; rightText[row]="";
      leftColor[row]=VRC_LABEL_COLOR; middleColor[row]=VRC_VALUE_COLOR; rightColor[row]=VRC_VALUE_COLOR;
     }

   const int regime=(int)MathRound(ExtRegime[index]);
   const bool stable=ExtValid[index]>0.5;
   const color regimeColor=RegimeColor(regime);
   left[0]="REGIME CLASSIFIER"; middle[0]=(stable ? RegimeIcon(regime)+" "+RegimeName(regime) : "WARM-UP"); leftColor[0]=clrWhite; middleColor[0]=(stable ? regimeColor : VRC_LABEL_COLOR);
   left[1]="REGIME"; middle[1]=RegimeName(regime); middleColor[1]=regimeColor;
   left[2]="Hurst"; middle[2]=DoubleToString(ExtHurst[index],3); rightText[2]=(ExtHurst[index]>=InpHurstTrendThreshold ? "Trending" : ExtHurst[index]<=InpHurstMrThreshold ? "Mean-Rev" : "Random"); middleColor[2]=(ExtHurst[index]>=InpHurstTrendThreshold ? InpStrongBullColor : ExtHurst[index]<=InpHurstMrThreshold ? InpMeanReversionColor : InpRangingColor); rightColor[2]=middleColor[2];
   left[3]="ADX"; middle[3]=(IsValue(ExtAdx[index]) ? DoubleToString(ExtAdx[index],1) : "—"); rightText[3]=(!IsValue(ExtAdx[index]) ? "Warm-up" : ExtAdx[index]>=InpAdxStrongThreshold ? "Strong" : ExtAdx[index]>=InpAdxTrendThreshold ? "Trend" : "Weak"); middleColor[3]=(IsValue(ExtAdx[index]) && ExtAdx[index]>=InpAdxStrongThreshold ? InpStrongBullColor : IsValue(ExtAdx[index]) && ExtAdx[index]>=InpAdxTrendThreshold ? InpWeakBullColor : InpRangingColor); rightColor[3]=middleColor[3];
   left[4]="CHOP"; middle[4]=(IsValue(ExtChop[index]) ? DoubleToString(ExtChop[index],1) : "—"); rightText[4]=(!IsValue(ExtChop[index]) ? "Warm-up" : ExtChop[index]>=InpChopRangeThreshold ? "Choppy" : ExtChop[index]<=38.2 ? "Trending" : "Normal"); middleColor[4]=(IsValue(ExtChop[index]) && ExtChop[index]>=InpChopRangeThreshold ? InpRangingColor : InpWeakBullColor); rightColor[4]=middleColor[4];
   left[5]="Vol%"; middle[5]=(IsValue(ExtVolPercentile[index]) ? DoubleToString(ExtVolPercentile[index],1)+"%" : "—"); rightText[5]=(ExtHighVol[index]>0.5 ? "HIGH" : ExtLowVol[index]>0.5 ? "LOW" : "Normal"); middleColor[5]=(ExtHighVol[index]>0.5 ? InpStrongBearColor : ExtLowVol[index]>0.5 ? InpCompressionColor : InpWeakBullColor); rightColor[5]=middleColor[5];
   left[6]="Direction"; middle[6]=(ExtDirection[index]>0.5 ? "▲ Bullish" : ExtDirection[index]>0.0 ? "△ Lean Bull" : ExtDirection[index]<-0.5 ? "▼ Bearish" : ExtDirection[index]<0.0 ? "▽ Lean Bear" : "◆ Neutral"); middleColor[6]=(ExtDirection[index]>0.0 ? InpStrongBullColor : ExtDirection[index]<0.0 ? InpStrongBearColor : InpRangingColor);
   left[7]="ATR"; middle[7]=(IsValue(ExtAtr[index]) ? DoubleToString(ExtAtr[index],_Digits) : "—");
   left[8]="Score"; middle[8]=(IsValue(ExtComposite[index]) ? DoubleToString(ExtComposite[index],0) : "—"); rightText[8]=(!IsValue(ExtComposite[index]) ? "Warm-up" : ExtComposite[index]>=5.0 ? "Strong" : ExtComposite[index]>=3.0 ? "Moderate" : ExtComposite[index]>=0.0 ? "Weak" : "Counter"); middleColor[8]=(IsValue(ExtComposite[index]) && ExtComposite[index]>=5.0 ? InpStrongBullColor : IsValue(ExtComposite[index]) && ExtComposite[index]>=3.0 ? InpWeakBullColor : IsValue(ExtComposite[index]) && ExtComposite[index]>=0.0 ? InpRangingColor : InpMeanReversionColor); rightColor[8]=middleColor[8];
   left[9]="IDEA"; middle[9]=StrategySuggestion(regime); middleColor[9]=BlendColor(clrWhite,VRC_PANEL_BG,0.85);

   for(int row=0;row<10;row++)
     {
      const int visualRow=(bottom ? 9-row : row);
      const int baseY=(InpDashPosition==VRC_MIDDLE_RIGHT ? middleY : margin);
      const int y=baseY+6+visualRow*rowHeight;
      const int leftX=(right ? panelWidth-12 : margin+12);
      const int middleX=(right ? panelWidth/2+25 : panelWidth/2-25);
      const int rightX=(right ? margin+12 : panelWidth-12);
      EnsureDashboardLabel("L"+IntegerToString(row),leftX,y,left[row],leftColor[row],false,(row==0 ? fontSize : smallSize));
      EnsureDashboardLabel("M"+IntegerToString(row),middleX,y,middle[row],middleColor[row],right,(row==0 ? fontSize : fontSize));
      EnsureDashboardLabel("R"+IntegerToString(row),rightX,y,rightText[row],rightColor[row],true,smallSize);
     }
  }

bool MainChartBounds(double &minimum,double &maximum)
  {
   minimum=0.0; maximum=0.0;
   return(ChartGetDouble(0,CHART_PRICE_MIN,0,minimum) && ChartGetDouble(0,CHART_PRICE_MAX,0,maximum) && maximum>minimum);
  }

void CreateBackgroundSegment(const int id,const datetime startTime,const datetime endTime,const int regime,const double minimum,const double maximum)
  {
   const string name=g_objectPrefix+"BG_"+IntegerToString(id);
   if(!ObjectCreate(0,name,OBJ_RECTANGLE,0,startTime,maximum,endTime,minimum))
      return;
   ObjectSetInteger(0,name,OBJPROP_COLOR,BlendColor(RegimeColor(regime),ChartBackground(),0.12));
   ObjectSetInteger(0,name,OBJPROP_FILL,true);
   ObjectSetInteger(0,name,OBJPROP_BACK,true);
   ObjectSetInteger(0,name,OBJPROP_SELECTABLE,false);
   ObjectSetInteger(0,name,OBJPROP_HIDDEN,true);
   ObjectSetInteger(0,name,OBJPROP_ZORDER,0);
  }

void RebuildBackground(const int ratesTotal,const datetime &time[])
  {
   DeleteObjectsByPrefix(g_objectPrefix+"BG_");
   if(!InpShowBackground || ratesTotal<=0)
      return;
   double minimum,maximum;
   if(!MainChartBounds(minimum,maximum))
      return;
   const int seconds=MathMax(PeriodSeconds(_Period),1);
   const int earliest=MathMax(0,ratesTotal-5000);
   int end=ratesTotal-1;
   int segment=0;
   while(end>=earliest && segment<VRC_MAX_OBJECTS)
     {
      const int regime=(int)MathRound(ExtRegime[end]);
      int start=end;
      while(start>earliest && (int)MathRound(ExtRegime[start-1])==regime)
         start--;
      CreateBackgroundSegment(segment,time[start],time[end]+seconds,regime,minimum,maximum);
      segment++;
      end=start-1;
     }
  }

void RebuildRegimeLabels(const int ratesTotal,const datetime &time[],const double &high[],const double &low[])
  {
   DeleteObjectsByPrefix(g_objectPrefix+"LBL_");
   if(!InpShowRegimeLabels || ratesTotal<2)
      return;
   int created=0;
   for(int index=ratesTotal-1;index>=1 && created<VRC_MAX_OBJECTS;index--)
     {
      if(ExtRegimeChanged[index]<0.5)
         continue;
      const int regime=(int)MathRound(ExtRegime[index]);
      const bool bullish=(regime==VRC_REGIME_STRONG_BULL || regime==VRC_REGIME_BULL || regime==VRC_REGIME_WEAK_BULL);
      const bool bearish=(regime==VRC_REGIME_STRONG_BEAR || regime==VRC_REGIME_BEAR || regime==VRC_REGIME_WEAK_BEAR);
      const double offset=(IsValue(ExtAtr[index]) ? 0.35*ExtAtr[index] : MathMax(high[index]-low[index],_Point*20));
      const double price=(bullish ? low[index]-offset : high[index]+offset);
      const string name=g_objectPrefix+"LBL_"+IntegerToString(created);
      if(ObjectCreate(0,name,OBJ_TEXT,0,time[index],price))
        {
         ObjectSetString(0,name,OBJPROP_TEXT,RegimeIcon(regime)+" "+RegimeName(regime));
         ObjectSetString(0,name,OBJPROP_FONT,"Segoe UI Semibold");
         ObjectSetInteger(0,name,OBJPROP_FONTSIZE,8);
         ObjectSetInteger(0,name,OBJPROP_COLOR,RegimeColor(regime));
         ObjectSetInteger(0,name,OBJPROP_ANCHOR,(bullish ? ANCHOR_UPPER : bearish ? ANCHOR_LOWER : ANCHOR_LOWER));
         ObjectSetInteger(0,name,OBJPROP_BACK,false);
         ObjectSetInteger(0,name,OBJPROP_SELECTABLE,false);
         ObjectSetInteger(0,name,OBJPROP_HIDDEN,true);
         ObjectSetInteger(0,name,OBJPROP_ZORDER,3);
        }
      created++;
     }
  }

void UpdateBackgroundBounds()
  {
   if(!InpShowBackground)
      return;
   double minimum,maximum;
   if(!MainChartBounds(minimum,maximum))
      return;
   for(int i=ObjectsTotal(0,0,OBJ_RECTANGLE)-1;i>=0;i--)
     {
      const string name=ObjectName(0,i,0,OBJ_RECTANGLE);
      if(StringFind(name,g_objectPrefix+"BG_")!=0)
         continue;
      ObjectSetDouble(0,name,OBJPROP_PRICE,0,maximum);
      ObjectSetDouble(0,name,OBJPROP_PRICE,1,minimum);
     }
  }

//+------------------------------------------------------------------+
//| Plot configuration and buffer initialization.                   |
//+------------------------------------------------------------------+
void ConfigureColors()
  {
   const color background=ChartBackground();
   for(int index=0;index<9;index++)
     {
      const int regime=index-1;
      const color base=RegimeColor(regime);
      PlotIndexSetInteger(0,PLOT_LINE_COLOR,index,base);
      PlotIndexSetInteger(1,PLOT_LINE_COLOR,index,(InpShowVolatilityBands ? BlendColor(base,background,0.08) : clrNONE));
      PlotIndexSetInteger(2,PLOT_LINE_COLOR,index,(InpShowVolatilityBands ? BlendColor(base,background,0.38) : clrNONE));
      PlotIndexSetInteger(3,PLOT_LINE_COLOR,index,(InpShowVolatilityBands ? BlendColor(base,background,0.38) : clrNONE));
      PlotIndexSetInteger(4,PLOT_LINE_COLOR,index,(InpShowVolatilityBands ? BlendColor(base,background,0.72) : clrNONE));
     }
  }

void ConfigurePlots()
  {
   PlotIndexSetInteger(0,PLOT_DRAW_TYPE,DRAW_COLOR_CANDLES);
   PlotIndexSetInteger(0,PLOT_COLOR_INDEXES,9);
   PlotIndexSetString(0,PLOT_LABEL,"Regime Candles");

   PlotIndexSetInteger(1,PLOT_DRAW_TYPE,DRAW_COLOR_HISTOGRAM2);
   PlotIndexSetInteger(1,PLOT_COLOR_INDEXES,9);
   PlotIndexSetInteger(1,PLOT_LINE_WIDTH,5);
   PlotIndexSetString(1,PLOT_LABEL,"Vol Band Fill");

   for(int plot=2;plot<=4;plot++)
     {
      PlotIndexSetInteger(plot,PLOT_DRAW_TYPE,DRAW_COLOR_LINE);
      PlotIndexSetInteger(plot,PLOT_COLOR_INDEXES,9);
      PlotIndexSetInteger(plot,PLOT_LINE_WIDTH,(plot==4 ? 2 : 1));
     }
   PlotIndexSetString(2,PLOT_LABEL,"Upper Vol Band");
   PlotIndexSetString(3,PLOT_LABEL,"Lower Vol Band");
   PlotIndexSetString(4,PLOT_LABEL,"Basis");

   string hiddenLabels[22]={"Hurst Exponent","ADX","DI+","DI-","Choppiness Index","Volatility Percentile","ATR","Composite Score","Direction","Regime (numeric)","Regime Changed","Previous Regime","High Volatility","Low Volatility","EMA Fast 21","EMA Slow 55","ROC 10","Stable Valid","Trend Score","Chop Score","Hurst Score","Raw Hurst"};
   for(int plot=5;plot<27;plot++)
     {
      PlotIndexSetInteger(plot,PLOT_DRAW_TYPE,DRAW_NONE);
      PlotIndexSetInteger(plot,PLOT_SHOW_DATA,true);
      PlotIndexSetString(plot,PLOT_LABEL,hiddenLabels[plot-5]);
     }
   PlotIndexSetInteger(0,PLOT_SHOW_DATA,false);
   PlotIndexSetInteger(1,PLOT_SHOW_DATA,false);
   for(int plot=0;plot<27;plot++)
      PlotIndexSetDouble(plot,PLOT_EMPTY_VALUE,EMPTY_VALUE);
   ConfigureColors();
  }

void InitializeBuffers()
  {
   ArrayInitialize(ExtCandleOpen,EMPTY_VALUE); ArrayInitialize(ExtCandleHigh,EMPTY_VALUE); ArrayInitialize(ExtCandleLow,EMPTY_VALUE); ArrayInitialize(ExtCandleClose,EMPTY_VALUE); ArrayInitialize(ExtCandleColor,EMPTY_VALUE);
   ArrayInitialize(ExtFillUpper,EMPTY_VALUE); ArrayInitialize(ExtFillLower,EMPTY_VALUE); ArrayInitialize(ExtFillColor,EMPTY_VALUE);
   ArrayInitialize(ExtUpperBand,EMPTY_VALUE); ArrayInitialize(ExtUpperColor,EMPTY_VALUE); ArrayInitialize(ExtLowerBand,EMPTY_VALUE); ArrayInitialize(ExtLowerColor,EMPTY_VALUE); ArrayInitialize(ExtBasis,EMPTY_VALUE); ArrayInitialize(ExtBasisColor,EMPTY_VALUE);
   ArrayInitialize(ExtHurst,EMPTY_VALUE); ArrayInitialize(ExtAdx,EMPTY_VALUE); ArrayInitialize(ExtDiPlus,EMPTY_VALUE); ArrayInitialize(ExtDiMinus,EMPTY_VALUE); ArrayInitialize(ExtChop,EMPTY_VALUE); ArrayInitialize(ExtVolPercentile,EMPTY_VALUE); ArrayInitialize(ExtAtr,EMPTY_VALUE); ArrayInitialize(ExtComposite,EMPTY_VALUE); ArrayInitialize(ExtDirection,EMPTY_VALUE); ArrayInitialize(ExtRegime,EMPTY_VALUE); ArrayInitialize(ExtRegimeChanged,0.0); ArrayInitialize(ExtPreviousRegime,EMPTY_VALUE); ArrayInitialize(ExtHighVol,0.0); ArrayInitialize(ExtLowVol,0.0); ArrayInitialize(ExtEmaFast,EMPTY_VALUE); ArrayInitialize(ExtEmaSlow,EMPTY_VALUE); ArrayInitialize(ExtRoc,EMPTY_VALUE); ArrayInitialize(ExtValid,0.0); ArrayInitialize(ExtTrendScore,EMPTY_VALUE); ArrayInitialize(ExtChopScore,EMPTY_VALUE); ArrayInitialize(ExtHurstScore,EMPTY_VALUE); ArrayInitialize(ExtHurstRaw,EMPTY_VALUE);
   ArrayInitialize(ExtLogReturn,EMPTY_VALUE); ArrayInitialize(ExtTrueRange,EMPTY_VALUE); ArrayInitialize(ExtPlusDm,EMPTY_VALUE); ArrayInitialize(ExtMinusDm,EMPTY_VALUE); ArrayInitialize(ExtDmiSmoothedTr,EMPTY_VALUE); ArrayInitialize(ExtDmiSmoothedPlus,EMPTY_VALUE); ArrayInitialize(ExtDmiSmoothedMinus,EMPTY_VALUE); ArrayInitialize(ExtDx,EMPTY_VALUE);
  }

bool ValidateInputs()
  {
   return(InpHurstLength>=20 && InpHurstLength<=500 &&
          InpAdxLength>=5 && InpAdxLength<=50 && InpAdxSmoothing>=5 && InpAdxSmoothing<=50 &&
          InpChopLength>=5 && InpChopLength<=50 && InpVolatilityLength>=5 && InpVolatilityLength<=100 &&
          InpVolPercentileLength>=20 && InpVolPercentileLength<=500 &&
          InpAdxTrendThreshold>=10.0 && InpAdxTrendThreshold<=50.0 &&
          InpAdxStrongThreshold>=25.0 && InpAdxStrongThreshold<=60.0 && InpAdxStrongThreshold>=InpAdxTrendThreshold &&
          InpChopRangeThreshold>=50.0 && InpChopRangeThreshold<=80.0 &&
          InpHurstTrendThreshold>=0.50 && InpHurstTrendThreshold<=0.80 &&
          InpHurstMrThreshold>=0.20 && InpHurstMrThreshold<=0.50 && InpHurstMrThreshold<=InpHurstTrendThreshold &&
          InpVolHighPercentile>=50.0 && InpVolHighPercentile<=99.0 &&
          InpVolLowPercentile>=1.0 && InpVolLowPercentile<=50.0 && InpVolLowPercentile<InpVolHighPercentile &&
          InpBandMultiplier>=0.5 && InpBandMultiplier<=5.0);
  }

//+------------------------------------------------------------------+
//| Alerts are confirmed on the completed bar only.                 |
//+------------------------------------------------------------------+
void EmitAlert(const string message)
  {
   Print(message);
   if(InpEnablePopupAlert)
      Alert(message);
   if(InpEnablePushNotification && !MQLInfoInteger(MQL_TESTER) && TerminalInfoInteger(TERMINAL_NOTIFICATIONS_ENABLED))
      SendNotification(message);
  }

void ProcessClosedBarAlerts(const int ratesTotal,const datetime &time[])
  {
   if(ratesTotal<3)
      return;
   const datetime liveBar=time[ratesTotal-1];
   if(liveBar==g_lastLiveBarTime)
      return;
   g_lastLiveBarTime=liveBar;
   const int closed=ratesTotal-2;
   const int previous=closed-1;
   const int regime=(int)MathRound(ExtRegime[closed]);
   const string prefix="VRC "+_Symbol+" "+EnumToString((ENUM_TIMEFRAMES)_Period)+": ";

   if(InpAlertRegimeChange && ExtRegimeChanged[closed]>0.5)
      EmitAlert(prefix+"regime changed to "+RegimeName(regime));
   if(InpAlertVolatilitySpike && ExtHighVol[closed]>0.5 && ExtHighVol[previous]<0.5)
      EmitAlert(prefix+"volatility spike, ATR percentile "+DoubleToString(ExtVolPercentile[closed],1)+"%");
   if(InpAlertCompression && ExtLowVol[closed]>0.5 && ExtLowVol[previous]<0.5)
      EmitAlert(prefix+"volatility compression, ATR percentile "+DoubleToString(ExtVolPercentile[closed],1)+"%");
  }

//+------------------------------------------------------------------+
//| Indicator initialization.                                       |
//+------------------------------------------------------------------+
int OnInit()
  {
   if(!ResolveEaEngineContract())
     {
      Print("VRC invalid EA engine contract.");
      return(INIT_PARAMETERS_INCORRECT);
     }
   if(!ValidateInputs())
     {
      Print("VRC invalid inputs: check lookbacks, threshold ordering and band multiplier.");
      return(INIT_PARAMETERS_INCORRECT);
     }

   SetIndexBuffer(0,ExtCandleOpen,INDICATOR_DATA); SetIndexBuffer(1,ExtCandleHigh,INDICATOR_DATA); SetIndexBuffer(2,ExtCandleLow,INDICATOR_DATA); SetIndexBuffer(3,ExtCandleClose,INDICATOR_DATA); SetIndexBuffer(4,ExtCandleColor,INDICATOR_COLOR_INDEX);
   SetIndexBuffer(5,ExtFillUpper,INDICATOR_DATA); SetIndexBuffer(6,ExtFillLower,INDICATOR_DATA); SetIndexBuffer(7,ExtFillColor,INDICATOR_COLOR_INDEX);
   SetIndexBuffer(8,ExtUpperBand,INDICATOR_DATA); SetIndexBuffer(9,ExtUpperColor,INDICATOR_COLOR_INDEX); SetIndexBuffer(10,ExtLowerBand,INDICATOR_DATA); SetIndexBuffer(11,ExtLowerColor,INDICATOR_COLOR_INDEX); SetIndexBuffer(12,ExtBasis,INDICATOR_DATA); SetIndexBuffer(13,ExtBasisColor,INDICATOR_COLOR_INDEX);
   SetIndexBuffer(14,ExtHurst,INDICATOR_DATA); SetIndexBuffer(15,ExtAdx,INDICATOR_DATA); SetIndexBuffer(16,ExtDiPlus,INDICATOR_DATA); SetIndexBuffer(17,ExtDiMinus,INDICATOR_DATA); SetIndexBuffer(18,ExtChop,INDICATOR_DATA); SetIndexBuffer(19,ExtVolPercentile,INDICATOR_DATA); SetIndexBuffer(20,ExtAtr,INDICATOR_DATA); SetIndexBuffer(21,ExtComposite,INDICATOR_DATA); SetIndexBuffer(22,ExtDirection,INDICATOR_DATA); SetIndexBuffer(23,ExtRegime,INDICATOR_DATA); SetIndexBuffer(24,ExtRegimeChanged,INDICATOR_DATA); SetIndexBuffer(25,ExtPreviousRegime,INDICATOR_DATA); SetIndexBuffer(26,ExtHighVol,INDICATOR_DATA); SetIndexBuffer(27,ExtLowVol,INDICATOR_DATA); SetIndexBuffer(28,ExtEmaFast,INDICATOR_DATA); SetIndexBuffer(29,ExtEmaSlow,INDICATOR_DATA); SetIndexBuffer(30,ExtRoc,INDICATOR_DATA); SetIndexBuffer(31,ExtValid,INDICATOR_DATA); SetIndexBuffer(32,ExtTrendScore,INDICATOR_DATA); SetIndexBuffer(33,ExtChopScore,INDICATOR_DATA); SetIndexBuffer(34,ExtHurstScore,INDICATOR_DATA); SetIndexBuffer(35,ExtHurstRaw,INDICATOR_DATA);
   SetIndexBuffer(36,ExtLogReturn,INDICATOR_CALCULATIONS); SetIndexBuffer(37,ExtTrueRange,INDICATOR_CALCULATIONS); SetIndexBuffer(38,ExtPlusDm,INDICATOR_CALCULATIONS); SetIndexBuffer(39,ExtMinusDm,INDICATOR_CALCULATIONS); SetIndexBuffer(40,ExtDmiSmoothedTr,INDICATOR_CALCULATIONS); SetIndexBuffer(41,ExtDmiSmoothedPlus,INDICATOR_CALCULATIONS); SetIndexBuffer(42,ExtDmiSmoothedMinus,INDICATOR_CALCULATIONS); SetIndexBuffer(43,ExtDx,INDICATOR_CALCULATIONS);

   ArraySetAsSeries(ExtCandleOpen,false); ArraySetAsSeries(ExtCandleHigh,false); ArraySetAsSeries(ExtCandleLow,false); ArraySetAsSeries(ExtCandleClose,false); ArraySetAsSeries(ExtCandleColor,false);
   ArraySetAsSeries(ExtFillUpper,false); ArraySetAsSeries(ExtFillLower,false); ArraySetAsSeries(ExtFillColor,false); ArraySetAsSeries(ExtUpperBand,false); ArraySetAsSeries(ExtUpperColor,false); ArraySetAsSeries(ExtLowerBand,false); ArraySetAsSeries(ExtLowerColor,false); ArraySetAsSeries(ExtBasis,false); ArraySetAsSeries(ExtBasisColor,false);
   ArraySetAsSeries(ExtHurst,false); ArraySetAsSeries(ExtAdx,false); ArraySetAsSeries(ExtDiPlus,false); ArraySetAsSeries(ExtDiMinus,false); ArraySetAsSeries(ExtChop,false); ArraySetAsSeries(ExtVolPercentile,false); ArraySetAsSeries(ExtAtr,false); ArraySetAsSeries(ExtComposite,false); ArraySetAsSeries(ExtDirection,false); ArraySetAsSeries(ExtRegime,false); ArraySetAsSeries(ExtRegimeChanged,false); ArraySetAsSeries(ExtPreviousRegime,false); ArraySetAsSeries(ExtHighVol,false); ArraySetAsSeries(ExtLowVol,false); ArraySetAsSeries(ExtEmaFast,false); ArraySetAsSeries(ExtEmaSlow,false); ArraySetAsSeries(ExtRoc,false); ArraySetAsSeries(ExtValid,false); ArraySetAsSeries(ExtTrendScore,false); ArraySetAsSeries(ExtChopScore,false); ArraySetAsSeries(ExtHurstScore,false); ArraySetAsSeries(ExtHurstRaw,false);
   ArraySetAsSeries(ExtLogReturn,false); ArraySetAsSeries(ExtTrueRange,false); ArraySetAsSeries(ExtPlusDm,false); ArraySetAsSeries(ExtMinusDm,false); ArraySetAsSeries(ExtDmiSmoothedTr,false); ArraySetAsSeries(ExtDmiSmoothedPlus,false); ArraySetAsSeries(ExtDmiSmoothedMinus,false); ArraySetAsSeries(ExtDx,false);

   ConfigurePlots();
   IndicatorSetString(INDICATOR_SHORTNAME,"VRC ("+IntegerToString(InpHurstLength)+","+IntegerToString(InpAdxLength)+","+IntegerToString(InpChopLength)+","+IntegerToString(InpVolatilityLength)+")");
   IndicatorSetInteger(INDICATOR_DIGITS,_Digits);
   g_objectPrefix="VRC_"+StringFormat("%I64d",ChartID())+"_"+IntegerToString((int)GetTickCount())+"_";
   g_lastLiveBarTime=0;
   g_lastVisualBarTime=0;
   g_lastVisualRegime=999;
   g_lastCalculatedIndex=-1;
   return(INIT_SUCCEEDED);
  }

//+------------------------------------------------------------------+
//| Main deterministic calculation.                                 |
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
   const int required=MathMax(MathMax(InpHurstLength+1,InpAdxLength+InpAdxSmoothing),MathMax(InpChopLength,InpVolatilityLength));
   if(rates_total<required)
      return(0);

   ArraySetAsSeries(time,false); ArraySetAsSeries(open,false); ArraySetAsSeries(high,false); ArraySetAsSeries(low,false); ArraySetAsSeries(close,false);

   // Same-bar tester calls cannot alter any admissible closed-bar decision.
   const bool testerMode=(bool)MQLInfoInteger(MQL_TESTER);
   static datetime lastTesterBarTime=0;
   if(testerMode && prev_calculated>0 && lastTesterBarTime==time[rates_total-1])
      return(rates_total);
   if(testerMode)
      lastTesterBarTime=time[rates_total-1];

   int start=(prev_calculated<=0 || prev_calculated>rates_total ? 0 : MathMax(prev_calculated-1,0));
   if(start==0)
      InitializeBuffers();

   const int dmiSeed=InpAdxLength-1;
   const int adxSeed=dmiSeed+InpAdxSmoothing-1;
   const int stableIndex=MathMax(MathMax(InpHurstLength,adxSeed),MathMax(InpChopLength-1,InpVolatilityLength-1+InpVolPercentileLength));

   for(int index=start;index<rates_total;index++)
     {
      // Log returns, true range and directional movement.
      if(index==0)
        {
         ExtLogReturn[index]=EMPTY_VALUE;
         ExtTrueRange[index]=high[index]-low[index];
         ExtPlusDm[index]=0.0;
         ExtMinusDm[index]=0.0;
        }
      else
        {
         ExtLogReturn[index]=(close[index]>0.0 && close[index-1]>0.0 ? MathLog(close[index]/close[index-1]) : EMPTY_VALUE);
         ExtTrueRange[index]=MathMax(high[index]-low[index],MathMax(MathAbs(high[index]-close[index-1]),MathAbs(low[index]-close[index-1])));
         const double upward=high[index]-high[index-1];
         const double downward=low[index-1]-low[index];
         ExtPlusDm[index]=(upward>downward && upward>0.0 ? upward : 0.0);
         ExtMinusDm[index]=(downward>upward && downward>0.0 ? downward : 0.0);
        }

      // EMA context and ATR.
      ExtEmaFast[index]=EmaAt(close[index],(index>0 ? ExtEmaFast[index-1] : EMPTY_VALUE),21,index);
      ExtEmaSlow[index]=EmaAt(close[index],(index>0 ? ExtEmaSlow[index-1] : EMPTY_VALUE),55,index);
      ExtBasis[index]=ExtEmaFast[index];
      ExtAtr[index]=RmaAt(ExtTrueRange,ExtAtr,index,InpVolatilityLength,0);

      // DMI/ADX, using Wilder RMA seeds.
      ExtDmiSmoothedTr[index]=RmaAt(ExtTrueRange,ExtDmiSmoothedTr,index,InpAdxLength,0);
      ExtDmiSmoothedPlus[index]=RmaAt(ExtPlusDm,ExtDmiSmoothedPlus,index,InpAdxLength,0);
      ExtDmiSmoothedMinus[index]=RmaAt(ExtMinusDm,ExtDmiSmoothedMinus,index,InpAdxLength,0);
      if(IsValue(ExtDmiSmoothedTr[index]) && ExtDmiSmoothedTr[index]>0.0)
        {
         ExtDiPlus[index]=100.0*ExtDmiSmoothedPlus[index]/ExtDmiSmoothedTr[index];
         ExtDiMinus[index]=100.0*ExtDmiSmoothedMinus[index]/ExtDmiSmoothedTr[index];
         const double denominator=ExtDiPlus[index]+ExtDiMinus[index];
         ExtDx[index]=(denominator>0.0 ? 100.0*MathAbs(ExtDiPlus[index]-ExtDiMinus[index])/denominator : 0.0);
        }
      else
        {
         ExtDiPlus[index]=EMPTY_VALUE;
         ExtDiMinus[index]=EMPTY_VALUE;
         ExtDx[index]=EMPTY_VALUE;
        }

      if(index<adxSeed)
         ExtAdx[index]=EMPTY_VALUE;
      else if(index==adxSeed)
        {
         double sumDx=0.0;
         bool ok=true;
         for(int position=dmiSeed;position<=adxSeed;position++)
           {
            if(!IsValue(ExtDx[position])) { ok=false; break; }
            sumDx+=ExtDx[position];
           }
         ExtAdx[index]=(ok ? sumDx/InpAdxSmoothing : EMPTY_VALUE);
        }
      else
         ExtAdx[index]=(IsValue(ExtAdx[index-1]) && IsValue(ExtDx[index]) ? (ExtAdx[index-1]*(InpAdxSmoothing-1)+ExtDx[index])/InpAdxSmoothing : EMPTY_VALUE);

      // Hurst, CHOP, ATR percentile and ROC.
      ExtHurstRaw[index]=HurstAt(index,InpHurstLength);
      ExtHurst[index]=EmaAt(ExtHurstRaw[index],(index>0 ? ExtHurst[index-1] : EMPTY_VALUE),5,index);
      ExtChop[index]=ChoppinessAt(index,InpChopLength,high,low);
      ExtVolPercentile[index]=PercentileRankAt(index,InpVolPercentileLength);
      ExtRoc[index]=(index>=10 && close[index-10]!=0.0 ? 100.0*(close[index]/close[index-10]-1.0) : EMPTY_VALUE);

      const bool highVol=(IsValue(ExtVolPercentile[index]) && ExtVolPercentile[index]>=InpVolHighPercentile);
      const bool lowVol=(IsValue(ExtVolPercentile[index]) && ExtVolPercentile[index]<=InpVolLowPercentile);
      ExtHighVol[index]=(highVol ? 1.0 : 0.0);
      ExtLowVol[index]=(lowVol ? 1.0 : 0.0);

      const bool dmiValid=IsValue(ExtAdx[index]) && IsValue(ExtDiPlus[index]) && IsValue(ExtDiMinus[index]);
      const bool componentValid=dmiValid && IsValue(ExtChop[index]) && IsValue(ExtHurst[index]);
      const bool trendBullish=(dmiValid && ExtDiPlus[index]>ExtDiMinus[index]);
      const bool trendBearish=(dmiValid && ExtDiMinus[index]>ExtDiPlus[index]);
      const bool emaBullish=ExtEmaFast[index]>ExtEmaSlow[index];
      const bool emaBearish=ExtEmaFast[index]<ExtEmaSlow[index];
      double direction=0.0;
      if(emaBullish && trendBullish) direction=1.0;
      else if(emaBearish && trendBearish) direction=-1.0;
      else if(emaBullish || trendBullish) direction=0.5;
      else if(emaBearish || trendBearish) direction=-0.5;
      ExtDirection[index]=direction;

      int regime=VRC_REGIME_RANGING;
      if(componentValid)
        {
         const int trendScore=(ExtAdx[index]>=InpAdxStrongThreshold ? 3 : ExtAdx[index]>=InpAdxTrendThreshold ? 2 : ExtAdx[index]>=15.0 ? 1 : 0);
         const int chopScore=(ExtChop[index]>=InpChopRangeThreshold ? -2 : ExtChop[index]>=50.0 ? -1 : ExtChop[index]>=38.2 ? 1 : 2);
         const int hurstScore=(ExtHurst[index]>=InpHurstTrendThreshold ? 2 : ExtHurst[index]>=0.5 ? 1 : ExtHurst[index]>=InpHurstMrThreshold ? -1 : -2);
         const int composite=trendScore+chopScore+hurstScore;
         ExtTrendScore[index]=trendScore;
         ExtChopScore[index]=chopScore;
         ExtHurstScore[index]=hurstScore;
         ExtComposite[index]=composite;

         if(lowVol && ExtChop[index]>=InpChopRangeThreshold) regime=VRC_REGIME_COMPRESSION;
         else if(ExtHurst[index]<InpHurstMrThreshold && ExtAdx[index]<InpAdxTrendThreshold) regime=VRC_REGIME_MEAN_REV;
         else if(composite>=5 && direction>0.0) regime=VRC_REGIME_STRONG_BULL;
         else if(composite>=3 && direction>0.0) regime=VRC_REGIME_BULL;
         else if(composite>=1 && direction>0.0) regime=VRC_REGIME_WEAK_BULL;
         else if(composite>=5 && direction<0.0) regime=VRC_REGIME_STRONG_BEAR;
         else if(composite>=3 && direction<0.0) regime=VRC_REGIME_BEAR;
         else if(composite>=1 && direction<0.0) regime=VRC_REGIME_WEAK_BEAR;
         else regime=VRC_REGIME_RANGING;
        }
      else
        {
         ExtTrendScore[index]=EMPTY_VALUE;
         ExtChopScore[index]=EMPTY_VALUE;
         ExtHurstScore[index]=EMPTY_VALUE;
         ExtComposite[index]=EMPTY_VALUE;
        }

      const int previousRegime=(index>0 && IsValue(ExtRegime[index-1]) ? (int)MathRound(ExtRegime[index-1]) : VRC_REGIME_RANGING);
      ExtRegime[index]=regime;
      ExtPreviousRegime[index]=previousRegime;
      ExtRegimeChanged[index]=(index>0 && regime!=previousRegime ? 1.0 : 0.0);
      ExtValid[index]=(index>=stableIndex && componentValid && IsValue(ExtVolPercentile[index]) ? 1.0 : 0.0);

      const int colorIndex=RegimeColorIndex(regime);
      if(InpShowCandleColor)
        {
         ExtCandleOpen[index]=open[index]; ExtCandleHigh[index]=high[index]; ExtCandleLow[index]=low[index]; ExtCandleClose[index]=close[index]; ExtCandleColor[index]=colorIndex;
        }
      else
        {
         ExtCandleOpen[index]=EMPTY_VALUE; ExtCandleHigh[index]=EMPTY_VALUE; ExtCandleLow[index]=EMPTY_VALUE; ExtCandleClose[index]=EMPTY_VALUE; ExtCandleColor[index]=EMPTY_VALUE;
        }

      if(IsValue(ExtAtr[index]))
        {
         ExtUpperBand[index]=ExtBasis[index]+ExtAtr[index]*InpBandMultiplier;
         ExtLowerBand[index]=ExtBasis[index]-ExtAtr[index]*InpBandMultiplier;
         ExtFillUpper[index]=ExtUpperBand[index];
         ExtFillLower[index]=ExtLowerBand[index];
         ExtFillColor[index]=colorIndex;
         ExtUpperColor[index]=colorIndex;
         ExtLowerColor[index]=colorIndex;
         ExtBasisColor[index]=colorIndex;
        }
      else
        {
         ExtUpperBand[index]=EMPTY_VALUE; ExtLowerBand[index]=EMPTY_VALUE; ExtFillUpper[index]=EMPTY_VALUE; ExtFillLower[index]=EMPTY_VALUE; ExtFillColor[index]=EMPTY_VALUE; ExtUpperColor[index]=EMPTY_VALUE; ExtLowerColor[index]=EMPTY_VALUE; ExtBasisColor[index]=EMPTY_VALUE;
        }
     }

   g_lastCalculatedIndex=rates_total-1;
   if(!testerMode)
     {
      UpdateDashboard(g_lastCalculatedIndex);
      const int currentRegime=(int)MathRound(ExtRegime[g_lastCalculatedIndex]);
      if(prev_calculated<=0 || time[rates_total-1]!=g_lastVisualBarTime || currentRegime!=g_lastVisualRegime)
        {
         RebuildBackground(rates_total,time);
         RebuildRegimeLabels(rates_total,time,high,low);
         g_lastVisualBarTime=time[rates_total-1];
         g_lastVisualRegime=currentRegime;
        }
      ProcessClosedBarAlerts(rates_total,time);
     }
   return(rates_total);
  }

//+------------------------------------------------------------------+
//| Keep colors/dashboard/background aligned with chart changes.     |
//+------------------------------------------------------------------+
void OnChartEvent(const int id,const long &lparam,const double &dparam,const string &sparam)
  {
   if(MQLInfoInteger(MQL_TESTER) || id!=CHARTEVENT_CHART_CHANGE)
      return;
   ConfigureColors();
   UpdateDashboard(g_lastCalculatedIndex);
   UpdateBackgroundBounds();
   ChartRedraw();
  }

//+------------------------------------------------------------------+
//| Remove only objects owned by this indicator instance.            |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
  {
   DeleteObjectsByPrefix(g_objectPrefix);
  }
//+------------------------------------------------------------------+
