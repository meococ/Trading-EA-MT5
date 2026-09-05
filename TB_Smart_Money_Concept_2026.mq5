//+------------------------------------------------------------------+
//|                    TB_Smart_Money_Concept_2026.mq5               |
//| TB Smart Money Concept 2026 - single-file MT5 port.              |
//| Original Pine Script v6 by TBalgo, version 2026.2.0.             |
//| Licensed under Mozilla Public License 2.0.                       |
//| Source: https://www.tradingview.com/script/IM2GxnOK-             |
//|         TB-Smart-Money-Concept-2026/                             |
//|                                                                  |
//| Public iCustom buffer contract v2.3 (consume shift >= 1):        |
//|   0/1   Sweep High/Low marker price                              |
//|   2     Bias: -1 bear, 0 flat, +1 bull                           |
//|   3/4   BOS Up / MSS Up flags (close-through + impulse;          |
//|         impulse may confirm on a later closed bar)               |
//|   5/6   BOS Down / MSS Down flags (same; FLAT first break = BOS) |
//|   7/8   Sweep High / Sweep Low flags (live swing required)        |
//|   9/10  Bull Void / Bear Void flags                              |
//|   11/12 Every impulse candle (body>=ATR*disp). Not "displacement |
//|         of the BOS bar". Same index as 2.2.                      |
//|   13/14 Latest confirmed swing high / low                        |
//|   15/16 Swing high / low live flags (0 after any close-through)  |
//|   17/18 Running-extreme trail high / low (not protected swings)  |
//|   19/20/21 Newest surviving Origin Cell top/bottom/side          |
//|         (not an Order Block; not necessarily this bar's BOS)     |
//|   22/23/24/25 Newest active Void top/bottom/CE/side              |
//|         (CE only while a half is alive; fill = half-span)        |
//|   26    ClosedBarValid (closed + ATR + required swing state)      |
//|   27    Structure event: +1 BOS up, +2 MSS up, -1 BOS down,      |
//|         -2 MSS down. Coupled to 3-6: same close-through+impulse. |
//|   28    ATR(14)                                                  |
//|   29    Broken structure level on an event bar                   |
//|   30/31 Newest Void upper/lower half active flags                |
//|   32/33 Newest Void active top/bottom after partial fill         |
//|   34/35 Newest Cell/Void age in completed bars                   |
//|   36    Impulse body / ATR(14) ratio                             |
//|   37/38 Newest Void/Cell height in ATR units                     |
//|   39    EA ready-mask (bits documented below)                    |
//|   40/41/42 Effective Swing/Impulse/Sweep parameters              |
//|   43    Buffer contract version (= 2.3)                           |
//|                                                                  |
//| BOS/MSS = close through the SNAPSHOT swing + same-direction      |
//| displacement. A weak close-through (no impulse) sets Live=0 and  |
//| a BROKEN_UNCONFIRMED pending (not an Order Block). A later       |
//| same-direction impulse still beyond that level confirms BOS/MSS  |
//| at the original swing, without a fresh close[i-1] cross.         |
//| Reclaim or a new pivot on that side cancels pending.             |
//| Origin Cell lookback is TB_ORIGIN_LOOKBACK bars before AND       |
//| inclusive of the break (index-k). Cell is not an Order Block.    |
//| Void fill requires a candle that spans a whole half; touching CE |
//| does not mitigate. When both halves are dead the CE is deleted.  |
//| Sweeps require a live swing (consumed BOS level is not swept).   |
//| Events exist only on the last closed bar (rates_total-2).        |
//| NEVER request shift 0 for event buffers. Forming bar: flags 0.   |
//|                                                                  |
//| Safety extension over the visual Pine script: all event buffers  |
//| are closed-bar only. The forming bar carries no trade event.     |
//| Raw events are structural facts, NOT entry signals. An EA must   |
//| require buffer 26 == 1, read shift >= 1, and apply its own risk,  |
//| execution, session, spread and portfolio controls.               |
//|                                                                  |
//| Honest iCustom = same map as a dropped-on-chart TV instance.     |
//| Do NOT pass EA_CUSTOM + size/age filters unless you want a       |
//| different map. This terminal treats each `input group` as a      |
//| positional slot (value 0). Skip that slot and InpEngineProfile   |
//| receives the next arg (swing length 5) → OnInit invalid inputs.  |
//| Defaults, or group-0 + the 17 engine values, match TV 2.3:       |
//|   handle=iCustom(_Symbol,_Period,"TB_Smart_Money_Concept_2026"); |
//|   handle=iCustom(_Symbol,_Period,                                 |
//|      "TB_Smart_Money_Concept_2026",                              |
//|      0, /* input group slot */                                  |
//|      0,5,0.45,3,4,0.05,0.0,0.0,0,0,                             |
//|      true,true,true,true,true,true,0);                            |
//|   CopyBuffer(handle,26,1,1,ready); // NEVER request shift 0       |
//| Profile 0 = TV honest 2.3 (sweep-live, half-span, no size/age).  |
//| iCustom hosts that must not litter set InpDrawObjects=false.     |
//| An EA should also verify buffer 43 >= 2.3 before consuming.      |
//| Visual 2.38: crop zone fills to origin; no 2099 rectangle walls. |
//| Buffer 44 stays ExtTrueRange. No public HTF buffers.             |
//+------------------------------------------------------------------+
#property copyright   "TBalgo; MQL5 port for workspace owner"
#property link        "https://www.tradingview.com/script/IM2GxnOK-TB-Smart-Money-Concept-2026/"
#property version     "2.42"
#property description "Closed-bar TB SMC 2026: BOS/MSS+impulse, origin cells, voids/CE, sweeps"
#property description "Contract 2.3: live-swing sweeps, no orphan CE, Trail not Protected, CELL≠OB"
#property description "Visual 2.42: H4 inset hides overlapping LTF objects via OBJ_NO_PERIODS"

#property indicator_chart_window
#property indicator_buffers 45
#property indicator_plots   44

//--- Parameter profile controls whether the engine is frozen to the public
//--- Pine defaults or accepts a separately optimizable EA parameter surface.
//--- EA_CUSTOM values are intentionally NOT labelled profitable/optimal here:
//--- optimization belongs to a preregistered per-symbol/timeframe EA backtest.
enum ENUM_TB_ENGINE_PROFILE
  {
   TB_PROFILE_TV_2026_2_0=0, // Exact public Pine defaults; EA custom filters disabled
   TB_PROFILE_EA_CUSTOM=1    // Use every InpEa* value below
  };

//--- Void retention is independently controllable in EA_CUSTOM mode.
enum ENUM_TB_VOID_RETENTION
  {
   TB_VOID_TV_HALF_PARITY=0, // Cap individual half-boxes like Pine voidBox
   TB_VOID_EA_WHOLE_ZONE=1   // Keep/remove both halves as one coherent EA zone
  };

//--- EA engine inputs stay first after the group header. A host that passes
//--- only engine values must prefix that group slot with 0; later chart/alert
//--- inputs then keep their defaults. Skipping the group slot shifts profile.
input group "EA Engine Contract - iCustom inputs first"
input ENUM_TB_ENGINE_PROFILE InpEngineProfile=TB_PROFILE_TV_2026_2_0; // TV parity or EA custom
input int    InpEaSwingLength=5;                 // EA_CUSTOM: pivot left/right bars (2..50)
input double InpEaDisplacementAtr=0.45;          // EA_CUSTOM: min candle body / ATR (0.10..5.00)
input int    InpEaCellsKept=3;                   // EA_CUSTOM: newest Origin Cells retained (1..32)
input int    InpEaVoidsKept=4;                   // EA_CUSTOM: Void retention budget (1..32)
input double InpEaSweepReclaimAtr=0.05;          // EA_CUSTOM: close-back distance / ATR (0..1)
input double InpEaMinimumVoidAtr=0.0;             // EA_CUSTOM: reject Void height below ATR ratio (0=off)
input double InpEaMinimumCellAtr=0.0;             // EA_CUSTOM: reject Origin Cell height below ATR ratio (0=off)
input int    InpEaMaximumCellAgeBars=0;           // EA_CUSTOM: expire Cell after N closed bars (0=off)
input int    InpEaMaximumVoidAgeBars=0;           // EA_CUSTOM: expire Void after N closed bars (0=off)
input bool   InpEaSweepsRequireLiveSwing=true;    // EA_CUSTOM: require live swing (false = old TV dead-sweep)
input bool   InpEaRequireBothSwings=true;         // EA_CUSTOM: buffer 26 requires both confirmed swing sides
input bool   InpEaEnableStructure=true;            // EA_CUSTOM: calculate BOS/MSS independently of display
input bool   InpEaEnableCells=true;                // EA_CUSTOM: Origin Cells; requires Structure=true
input bool   InpEaEnableVoids=true;                // EA_CUSTOM: calculate Void/CE independently of display
input bool   InpEaEnableSweeps=true;               // EA_CUSTOM: calculate sweeps independently of display
input ENUM_TB_VOID_RETENTION InpEaVoidRetention=TB_VOID_TV_HALF_PARITY; // Half parity or whole zone

//--- Optimization discipline for the future EA:
//--- 1) bind one symbol/timeframe/data manifest and freeze the entry/exit rule;
//--- 2) tune cadence (Swing Length), then impulse/sweep quality, then zone
//---    size/age filters; never sweep the full Cartesian product at once;
//--- 3) select on purged/embargoed OOS evidence after spread + slippage, not
//---    on chart appearance or in-sample net profit. The values above are
//---    parity-oriented baselines, not a claim of economic optimality.

//--- Theme
input group "TB SMC 2026 - Look"
input color InpBullColor=C'45,212,191';       // Bull  TV #2DD4BF
input color InpBearColor=C'251,113,133';      // Bear  TV #FB7185
input color InpAccentColor=C'129,140,248';    // Accent TV #818CF8
input color InpMuteColor=C'100,116,139';      // Mute  TV #64748B
input bool  InpFocusMode=true;                // Cap BOS/MSS labels; nearest live SMC rays, older cropped
input int   InpFocusLastN=10;                 // Last N BOS/MSS marks when Focus is on (1..150)

//--- Modules
input group "TB SMC 2026 - Map"
input bool InpShowStructure=true;             // Structure (BOS / MSS)
input bool InpShowCells=true;                 // Origin Cells (not Order Blocks)
input bool InpShowVoids=true;                 // Price Voids + CE (fill = half-span)
input bool InpShowSweeps=true;                // Liquidity Sweeps (live swing only)
input bool InpShowTrail=true;                 // Running extremes (Trail H/L, not protected)
input bool InpShowHud=true;                   // Bias HUD

//--- Closed-bar alerts.
input group "Closed-Bar Alerts"
input bool InpEnableAlerts=true;              // Enable alerts
input bool InpEnablePopupAlert=true;          // MT5 popup/sound
input bool InpEnablePushNotification=false;   // Mobile push

input group "Chart Objects"
input bool InpDrawObjects=true;               // Draw objects; iCustom hosts should set false

input group "HTF Context Panel"
input bool            InpShowHtfPanel=false;             // Off: TV has no LTF H4 box; use a real H4 chart
input ENUM_TIMEFRAMES InpHtfPeriod=PERIOD_H4;             // Child iCustom TF; no handle if == chart
input ENUM_BASE_CORNER InpHtfCorner=CORNER_LEFT_LOWER;    // H4 overlay: left, above volume
input int             InpHtfOffsetX=10;                   // Pixel offset from corner
input int             InpHtfOffsetY=0;                    // 0 = auto (top: below HUD; bottom: 10px)
input int             InpHtfSparkBars=8;                  // Closed HTF candles (clamp 4..12)
input bool            InpShowHtfBreakOnChart=false;       // One H4 BOS/MSS level on LTF

input group "HTF Inset Chart"
input bool InpShowHtfInset=true;          // M5/M15: large H4 chart, bottom-left
input int  InpHtfInsetWidthPct=42;        // Width percent of parent (38..45)
input int  InpHtfInsetHeightPct=36;       // Height percent of parent (32..40)
input int  InpHtfInsetScale=3;            // Nested candle scale 0..5

const string TB_VERSION="2026.2.0";
const double TB_CONTRACT_VERSION=2.3;
const int    TB_ATR_LENGTH=14;
const int    TB_ORIGIN_LOOKBACK=8;
const int    TB_MAX_STRUCTURE_OBJECTS=150;
const int    TB_HTF_EVENT_SCAN=64;
const int    TB_HTF_SPARK_MAX=12;
const int    TB_HTF_PANEL_WIDTH=220;
const int    TB_HUD_PANEL_HEIGHT=78;
const int    TB_HTF_PANEL_HEIGHT=110;
const int    TB_HTF_INSET_MIN_WIDTH=380;
const int    TB_HTF_INSET_MIN_HEIGHT=220;
const int    TB_HTF_INSET_PAD_X=10;
const int    TB_HTF_INSET_PAD_Y=24;
const int    TB_PANEL_PAD=12;
const double TB_ZONE_FILL_MIN_ATR=0.20;
const double TB_ZONE_FILL_MAX_ATR=6.00;
const int    TB_CELL_BOX_PAD_BARS=2;
const color  TB_PANEL_BG=C'15,23,42';
const color  TB_PANEL_TEXT=C'226,232,240';
const color  TB_PANEL_KEY_COLOR=C'100,116,139';
const color  TB_PANEL_BORDER=C'51,65,85';
const color  TB_SPARK_WELL=C'247,247,247';
const color  TB_SPARK_UP=C'45,212,191';
const color  TB_SPARK_DN=C'251,113,133';
const color  TB_SPARK_WICK_UP=C'16,185,129';
const color  TB_SPARK_WICK_DN=C'244,63,94';

//--- Ready-mask bits published in buffer 39. Multiple bits may be set.
//--- Example: 15 = closed + ATR + swing-high + swing-low ready.
enum ENUM_TB_READY_BITS
  {
   TB_READY_CLOSED=1,
   TB_READY_ATR=2,
   TB_READY_SWING_HIGH=4,
   TB_READY_SWING_LOW=8,
   TB_READY_CELL=16,
   TB_READY_VOID=32
  };

//--- Visible marker buffers 0..1.
double ExtSweepHighMarker[];
double ExtSweepLowMarker[];

//--- Backward-compatible public EA buffers 2..29.
double ExtBias[];
double ExtBosUp[];
double ExtMssUp[];
double ExtBosDown[];
double ExtMssDown[];
double ExtSweepHigh[];
double ExtSweepLow[];
double ExtBullVoid[];
double ExtBearVoid[];
double ExtImpulseUp[];
double ExtImpulseDown[];
double ExtSwingHigh[];
double ExtSwingLow[];
double ExtSwingHighLive[];
double ExtSwingLowLive[];
double ExtTrailHigh[];
double ExtTrailLow[];
double ExtCellTop[];
double ExtCellBottom[];
double ExtCellSide[];
double ExtVoidTop[];
double ExtVoidBottom[];
double ExtVoidCe[];
double ExtVoidSide[];
double ExtClosedBarValid[];
double ExtStructureEvent[];
double ExtAtr[];
double ExtBreakLevel[];

//--- EA contract v2 buffers 30..43. These expose state required to consume
//--- partially-filled zones without guessing from chart objects.
double ExtVoidUpperActive[];
double ExtVoidLowerActive[];
double ExtVoidActiveTop[];
double ExtVoidActiveBottom[];
double ExtCellAgeBars[];
double ExtVoidAgeBars[];
double ExtDisplacementRatio[];
double ExtVoidSizeAtr[];
double ExtCellSizeAtr[];
double ExtEaReadyMask[];
double ExtEffectiveSwingLength[];
double ExtEffectiveDisplacementAtr[];
double ExtEffectiveSweepReclaimAtr[];
double ExtContractVersion[];

//--- Internal deterministic calculation buffer 44.
double ExtTrueRange[];

struct OriginCell
  {
   int      startIndex;
   int      eventIndex;
   double   top;
   double   bottom;
   int      side;
  };

struct PriceVoid
  {
   int      startIndex;
   int      eventIndex;
   double   top;
   double   bottom;
   double   ce;
   int      side;
   bool     upperActive;
   bool     lowerActive;
  };

//--- CE midlines follow the living halves. When both halves are filled or
//--- trimmed dead the CE is deleted so it cannot be read as an active void.
struct VoidMidline
  {
   int      startIndex;
   int      eventIndex;
   double   ce;
   int      side;
  };

OriginCell g_cells[];
PriceVoid  g_voids[];
VoidMidline g_voidMids[];
int        g_breakOrigin[];
int        g_trailHighOrigin[];
int        g_trailLowOrigin[];

string   g_prefix="";
string   g_shortName="";
datetime g_cachedTime[];
int      g_cachedRates=0;
datetime g_lastBarTime=0;
datetime g_firstBarTime=0;
datetime g_lastAlertedClosedBar=0;
int      g_lastClosedIndex=-1;

//--- Resolved engine parameters. TV profile writes canonical Pine values;
//--- EA_CUSTOM copies the InpEa* inputs after fail-closed validation.
int    g_swingLength=5;
double g_displacementAtr=0.45;
int    g_cellsKept=3;
int    g_voidsKept=4;
double g_sweepReclaimAtr=0.05;
double g_minimumVoidAtr=0.0;
double g_minimumCellAtr=0.0;
int    g_maximumCellAgeBars=0;
int    g_maximumVoidAgeBars=0;
bool   g_sweepsRequireLiveSwing=true;
bool   g_requireBothSwings=true;
bool   g_enableStructure=true;
bool   g_enableCells=true;
bool   g_enableVoids=true;
bool   g_enableSweeps=true;
ENUM_TB_VOID_RETENTION g_voidRetention=TB_VOID_TV_HALF_PARITY;

//--- Persistent closed-bar engine state. The first calculation performs a
//--- deterministic full replay. Later bars process only newly-closed candles,
//--- removing the old O(history) cost while preserving attach/rebuild parity.
double g_swingHigh=EMPTY_VALUE;
double g_swingLow=EMPTY_VALUE;
double g_previousSwingHigh=EMPTY_VALUE;
double g_previousSwingLow=EMPTY_VALUE;
bool   g_swingHighLive=false;
bool   g_swingLowLive=false;
int    g_swingHighIndex=-1;
int    g_swingLowIndex=-1;
int    g_bias=0;
double g_trailHigh=EMPTY_VALUE;
double g_trailLow=EMPTY_VALUE;
int    g_trailHighIndex=-1;
int    g_trailLowIndex=-1;
int    g_lastProcessedClosedIndex=-1;

//--- BROKEN_UNCONFIRMED: close already through a live swing without
//--- displacement. Not an Order Block. Live=0 on that side until reclaim
//--- (swing intact again), a new pivot replaces the side, or BOS/MSS confirms.
bool   g_pendingHighActive=false;
double g_pendingHighLevel=EMPTY_VALUE;
int    g_pendingHighOrigin=-1;
bool   g_pendingLowActive=false;
double g_pendingLowLevel=EMPTY_VALUE;
int    g_pendingLowOrigin=-1;

//--- Headless child iCustom on InpHtfPeriod. No public HTF buffers.
int      g_htfHandle=INVALID_HANDLE;
bool     g_htfUnavailable=false;
bool     g_htfSameAsChart=false;
bool     g_htfReady=false;
datetime g_htfLastClosedTime=0;
datetime g_htfClockStamp=0;
double   g_htfBias=0.0;
double   g_htfClosedValid=0.0;
int      g_htfLastEvent=0;
double   g_htfLastLevel=EMPTY_VALUE;
double   g_htfOpen=0.0;
double   g_htfHigh=0.0;
double   g_htfLow=0.0;
double   g_htfClose=0.0;
double   g_htfSparkOpen[];
double   g_htfSparkHigh[];
double   g_htfSparkLow[];
double   g_htfSparkClose[];
int      g_htfSparkCount=0;
int      g_htfInsetHandle=INVALID_HANDLE;
long     g_htfInsetChartId=0;
bool     g_htfInsetAttached=false;
bool     g_htfInsetTplSaved=false;
bool     g_htfInsetApplyTried=false;
int      g_htfInsetStage=0;
bool     g_htfInsetFgSaved=false;
long     g_htfInsetPrevFg=0;

//+------------------------------------------------------------------+
//| Basic helpers.                                                   |
//+------------------------------------------------------------------+
bool IsValue(const double value)
  {
   return(value!=EMPTY_VALUE && MathIsValidNumber(value));
  }

double Clamp(const double value,const double minimum,const double maximum)
  {
   return(MathMax(minimum,MathMin(maximum,value)));
  }

color BlendColor(const color foreground,const color background,const double strength)
  {
   const double weight=Clamp(strength,0.0,1.0);
   const int fr=(int)(foreground & 0xFF);
   const int fg=(int)((foreground>>8) & 0xFF);
   const int fb=(int)((foreground>>16) & 0xFF);
   const int br=(int)(background & 0xFF);
   const int bg=(int)((background>>8) & 0xFF);
   const int bb=(int)((background>>16) & 0xFF);
   return((color)((int)MathRound(br+(fr-br)*weight)
                  | ((int)MathRound(bg+(fg-bg)*weight)<<8)
                  | ((int)MathRound(bb+(fb-bb)*weight)<<16)));
  }

color ChartBackground()
  {
   long raw=0;
   if(!ChartGetInteger(0,CHART_COLOR_BACKGROUND,0,raw))
      return(C'13,17,23');
   return((color)raw);
  }

color ZoneWash(const color accent,const double strength)
  {
   const color bg=ChartBackground();
   const int luma=((int)(bg & 0xFF)*299
                   +((int)((bg>>8) & 0xFF))*587
                   +((int)((bg>>16) & 0xFF))*114)/1000;
   double amt=Clamp(strength,0.06,0.28);
   if(luma<48)
      amt=MathMax(amt,0.24);
   return(BlendColor(accent,bg,amt));
  }

bool IsVisualInstanceOnChart()
  {
   // Draw only when attached to a chart whose symbol/TF match this instance.
   // Unattached iCustom (H4 child of M15) inherits the host ChartPeriod and
   // would otherwise ObjectCreate onto the parent.
   if(!InpDrawObjects)
      return(false);
   if((ENUM_TIMEFRAMES)ChartPeriod()!=(ENUM_TIMEFRAMES)_Period)
      return(false);
   if(ChartSymbol()!=_Symbol)
      return(false);
   return(true);
  }

void DeleteObjectsByPrefix(const string prefix)
  {
   for(int index=ObjectsTotal(0)-1;index>=0;index--)
     {
      const string name=ObjectName(0,index);
      if(StringFind(name,prefix)==0)
         ObjectDelete(0,name);
     }
  }

//+------------------------------------------------------------------+
//| Resolve the active parameter surface.                            |
//| TV profile is immutable by design. EA_CUSTOM is the only profile |
//| an optimizer should vary, so chart parity and EA experiments do  |
//| not silently share or overwrite each other's meaning.            |
//+------------------------------------------------------------------+
void ResolveEngineParameters()
  {
   if(InpEngineProfile==TB_PROFILE_TV_2026_2_0)
     {
      g_swingLength=5;
      g_displacementAtr=0.45;
      g_cellsKept=3;
      g_voidsKept=4;
      g_sweepReclaimAtr=0.05;
      g_minimumVoidAtr=0.0;
      g_minimumCellAtr=0.0;
      g_maximumCellAgeBars=0;
      g_maximumVoidAgeBars=0;
      g_sweepsRequireLiveSwing=true; // Honest default: no sweep on a consumed swing
      g_requireBothSwings=true;
      // TV profile always calculates. InpShow* only hides drawings/plots.
      g_enableStructure=true;
      g_enableCells=true;
      g_enableVoids=true;
      g_enableSweeps=true;
      g_voidRetention=TB_VOID_TV_HALF_PARITY;
      return;
     }

   g_swingLength=InpEaSwingLength;
   g_displacementAtr=InpEaDisplacementAtr;
   g_cellsKept=InpEaCellsKept;
   g_voidsKept=InpEaVoidsKept;
   g_sweepReclaimAtr=InpEaSweepReclaimAtr;
   g_minimumVoidAtr=InpEaMinimumVoidAtr;
   g_minimumCellAtr=InpEaMinimumCellAtr;
   g_maximumCellAgeBars=InpEaMaximumCellAgeBars;
   g_maximumVoidAgeBars=InpEaMaximumVoidAgeBars;
   g_sweepsRequireLiveSwing=InpEaSweepsRequireLiveSwing;
   g_requireBothSwings=InpEaRequireBothSwings;
   g_enableStructure=InpEaEnableStructure;
   g_enableCells=InpEaEnableCells;
   g_enableVoids=InpEaEnableVoids;
   g_enableSweeps=InpEaEnableSweeps;
   g_voidRetention=InpEaVoidRetention;
  }

//+------------------------------------------------------------------+
//| Reset persistent engine state before a full deterministic replay. |
//+------------------------------------------------------------------+
void ResetEngineState()
  {
   ArrayResize(g_cells,0);
   ArrayResize(g_voids,0);
   ArrayResize(g_voidMids,0);
   g_swingHigh=EMPTY_VALUE;
   g_swingLow=EMPTY_VALUE;
   g_previousSwingHigh=EMPTY_VALUE;
   g_previousSwingLow=EMPTY_VALUE;
   g_swingHighLive=false;
   g_swingLowLive=false;
   g_swingHighIndex=-1;
   g_swingLowIndex=-1;
   g_bias=0;
   g_trailHigh=EMPTY_VALUE;
   g_trailLow=EMPTY_VALUE;
   g_trailHighIndex=-1;
   g_trailLowIndex=-1;
   g_lastProcessedClosedIndex=-1;
   g_pendingHighActive=false;
   g_pendingHighLevel=EMPTY_VALUE;
   g_pendingHighOrigin=-1;
   g_pendingLowActive=false;
   g_pendingLowLevel=EMPTY_VALUE;
   g_pendingLowOrigin=-1;
  }

//+------------------------------------------------------------------+
//| Zone array helpers.                                              |
//+------------------------------------------------------------------+
void RemoveCell(const int index)
  {
   const int count=ArraySize(g_cells);
   if(index<0 || index>=count)
      return;
   for(int i=index;i<count-1;i++)
      g_cells[i]=g_cells[i+1];
   ArrayResize(g_cells,count-1);
  }

void PushCellFront(const OriginCell &cell)
  {
   int count=ArraySize(g_cells);
   ArrayResize(g_cells,count+1);
   for(int i=count;i>0;i--)
      g_cells[i]=g_cells[i-1];
   g_cells[0]=cell;
   while(ArraySize(g_cells)>g_cellsKept)
      ArrayResize(g_cells,ArraySize(g_cells)-1);
  }

void RemoveVoidMidByEvent(const int eventIndex)
  {
   for(int i=ArraySize(g_voidMids)-1;i>=0;i--)
     {
      if(g_voidMids[i].eventIndex!=eventIndex)
         continue;
      const int count=ArraySize(g_voidMids);
      for(int j=i;j<count-1;j++)
         g_voidMids[j]=g_voidMids[j+1];
      ArrayResize(g_voidMids,count-1);
     }
  }

void RemoveVoid(const int index,const bool removeMidline)
  {
   const int count=ArraySize(g_voids);
   if(index<0 || index>=count)
      return;
   const int eventIndex=g_voids[index].eventIndex;
   for(int i=index;i<count-1;i++)
      g_voids[i]=g_voids[i+1];
   ArrayResize(g_voids,count-1);
   if(removeMidline)
      RemoveVoidMidByEvent(eventIndex);
  }

int ActiveVoidHalfCount()
  {
   int active=0;
   for(int i=0;i<ArraySize(g_voids);i++)
     {
      if(g_voids[i].upperActive) active++;
      if(g_voids[i].lowerActive) active++;
     }
   return(active);
  }

void PushVoidMidFront(const PriceVoid &zone)
  {
   VoidMidline mid;
   mid.startIndex=zone.startIndex;
   mid.eventIndex=zone.eventIndex;
   mid.ce=zone.ce;
   mid.side=zone.side;
   int count=ArraySize(g_voidMids);
   ArrayResize(g_voidMids,count+1);
   for(int i=count;i>0;i--)
      g_voidMids[i]=g_voidMids[i-1];
   g_voidMids[0]=mid;
   while(ArraySize(g_voidMids)>g_voidsKept)
      ArrayResize(g_voidMids,ArraySize(g_voidMids)-1);
  }

//--- Pine pushes lower then upper half at the array front; therefore its
//--- oldest pop removes the upper half of the oldest zone first. This helper
//--- preserves that exact half-box retention order without forcing the EA to
//--- infer it from chart objects.
void TrimVoidHalvesLikePine()
  {
   const int limit=g_voidsKept*2;
   while(ActiveVoidHalfCount()>limit)
     {
      bool removed=false;
      for(int i=ArraySize(g_voids)-1;i>=0;i--)
        {
         if(g_voids[i].upperActive)
           {
            g_voids[i].upperActive=false;
            removed=true;
           }
         else if(g_voids[i].lowerActive)
           {
            g_voids[i].lowerActive=false;
            removed=true;
           }
         if(removed)
           {
            if(!g_voids[i].upperActive && !g_voids[i].lowerActive)
               RemoveVoid(i,true); // Both halves dead → delete CE with the zone.
            break;
           }
        }
      if(!removed)
         break;
     }
  }

void PushVoidFront(const PriceVoid &zone)
  {
   int count=ArraySize(g_voids);
   ArrayResize(g_voids,count+1);
   for(int i=count;i>0;i--)
      g_voids[i]=g_voids[i-1];
   g_voids[0]=zone;
   PushVoidMidFront(zone);

   if(g_voidRetention==TB_VOID_TV_HALF_PARITY)
      TrimVoidHalvesLikePine();
   else
     {
      while(ArraySize(g_voids)>g_voidsKept)
         RemoveVoid(ArraySize(g_voids)-1,true);
     }
  }

//+------------------------------------------------------------------+
//| Wilder ATR matching ta.atr(14).                                  |
//+------------------------------------------------------------------+
double AtrAt(const int index)
  {
   if(index<TB_ATR_LENGTH-1)
      return(EMPTY_VALUE);
   if(index==TB_ATR_LENGTH-1)
     {
      double sum=0.0;
      for(int i=0;i<TB_ATR_LENGTH;i++)
         sum+=ExtTrueRange[i];
      return(sum/TB_ATR_LENGTH);
     }
   if(!IsValue(ExtAtr[index-1]))
      return(EMPTY_VALUE);
   return((ExtAtr[index-1]*(TB_ATR_LENGTH-1)+ExtTrueRange[index])/TB_ATR_LENGTH);
  }

//+------------------------------------------------------------------+
//| Confirmed pivot helpers. Candidate is index-swingLen.             |
//+------------------------------------------------------------------+
bool IsPivotHigh(const int index,const double &high[],double &value,int &pivotIndex)
  {
   pivotIndex=index-g_swingLength;
   if(pivotIndex<g_swingLength)
      return(false);
   value=high[pivotIndex];
   for(int offset=1;offset<=g_swingLength;offset++)
     {
      if(high[pivotIndex-offset]>value || high[pivotIndex+offset]>value)
         return(false);
     }
   return(true);
  }

bool IsPivotLow(const int index,const double &low[],double &value,int &pivotIndex)
  {
   pivotIndex=index-g_swingLength;
   if(pivotIndex<g_swingLength)
      return(false);
   value=low[pivotIndex];
   for(int offset=1;offset<=g_swingLength;offset++)
     {
      if(low[pivotIndex-offset]<value || low[pivotIndex+offset]<value)
         return(false);
     }
   return(true);
  }

//+------------------------------------------------------------------+
//| Buffer initialization.                                           |
//+------------------------------------------------------------------+
void InitializeBufferAt(const int index)
  {
   ExtSweepHighMarker[index]=EMPTY_VALUE;
   ExtSweepLowMarker[index]=EMPTY_VALUE;
   ExtBias[index]=0.0;
   ExtBosUp[index]=0.0;
   ExtMssUp[index]=0.0;
   ExtBosDown[index]=0.0;
   ExtMssDown[index]=0.0;
   ExtSweepHigh[index]=0.0;
   ExtSweepLow[index]=0.0;
   ExtBullVoid[index]=0.0;
   ExtBearVoid[index]=0.0;
   ExtImpulseUp[index]=0.0;
   ExtImpulseDown[index]=0.0;
   ExtSwingHigh[index]=EMPTY_VALUE;
   ExtSwingLow[index]=EMPTY_VALUE;
   ExtSwingHighLive[index]=0.0;
   ExtSwingLowLive[index]=0.0;
   ExtTrailHigh[index]=EMPTY_VALUE;
   ExtTrailLow[index]=EMPTY_VALUE;
   ExtCellTop[index]=EMPTY_VALUE;
   ExtCellBottom[index]=EMPTY_VALUE;
   ExtCellSide[index]=0.0;
   ExtVoidTop[index]=EMPTY_VALUE;
   ExtVoidBottom[index]=EMPTY_VALUE;
   ExtVoidCe[index]=EMPTY_VALUE;
   ExtVoidSide[index]=0.0;
   ExtClosedBarValid[index]=0.0;
   ExtStructureEvent[index]=0.0;
   ExtAtr[index]=EMPTY_VALUE;
   ExtBreakLevel[index]=EMPTY_VALUE;
   ExtVoidUpperActive[index]=0.0;
   ExtVoidLowerActive[index]=0.0;
   ExtVoidActiveTop[index]=EMPTY_VALUE;
   ExtVoidActiveBottom[index]=EMPTY_VALUE;
   ExtCellAgeBars[index]=EMPTY_VALUE;
   ExtVoidAgeBars[index]=EMPTY_VALUE;
   ExtDisplacementRatio[index]=EMPTY_VALUE;
   ExtVoidSizeAtr[index]=EMPTY_VALUE;
   ExtCellSizeAtr[index]=EMPTY_VALUE;
   ExtEaReadyMask[index]=0.0;
   ExtEffectiveSwingLength[index]=(double)g_swingLength;
   ExtEffectiveDisplacementAtr[index]=g_displacementAtr;
   ExtEffectiveSweepReclaimAtr[index]=g_sweepReclaimAtr;
   ExtContractVersion[index]=TB_CONTRACT_VERSION;
   ExtTrueRange[index]=0.0;
  }

void InitializeBuffers(const int ratesTotal)
  {
   for(int index=0;index<ratesTotal;index++)
      InitializeBufferAt(index);
  }

//+------------------------------------------------------------------+
//| Plot configuration.                                              |
//+------------------------------------------------------------------+
void ConfigurePlots()
  {
   PlotIndexSetInteger(0,PLOT_DRAW_TYPE,(InpShowSweeps ? DRAW_ARROW : DRAW_NONE));
   PlotIndexSetInteger(0,PLOT_ARROW,251);
   PlotIndexSetInteger(0,PLOT_LINE_WIDTH,1);
   PlotIndexSetInteger(0,PLOT_LINE_COLOR,InpAccentColor);
   PlotIndexSetString(0,PLOT_LABEL,"Sweep High Marker");

   PlotIndexSetInteger(1,PLOT_DRAW_TYPE,(InpShowSweeps ? DRAW_ARROW : DRAW_NONE));
   PlotIndexSetInteger(1,PLOT_ARROW,251);
   PlotIndexSetInteger(1,PLOT_LINE_WIDTH,1);
   PlotIndexSetInteger(1,PLOT_LINE_COLOR,InpAccentColor);
   PlotIndexSetString(1,PLOT_LABEL,"Sweep Low Marker");

   const string labels[42]=
     {
      "Bias","BOS Up","MSS Up","BOS Down","MSS Down",
      "Sweep High","Sweep Low","Bull Void","Bear Void",
      "Impulse Candle Up","Impulse Candle Down","Swing High","Swing Low",
      "Swing High Live","Swing Low Live","Trail High","Trail Low",
      "Origin Cell Top","Origin Cell Bottom","Origin Cell Side",
      "Void Top","Void Bottom","Void CE","Void Side",
      "Closed Bar Valid","Structure Event","ATR(14)","Break Level",
      "Void Upper Active","Void Lower Active","Void Active Top","Void Active Bottom",
      "Cell Age Bars","Void Age Bars","Impulse Body/ATR","Void Size ATR",
      "Cell Size ATR","EA Ready Mask","Effective Swing Length",
      "Effective Displacement ATR","Effective Sweep Reclaim ATR","Contract Version"
     };
   for(int plot=2;plot<44;plot++)
     {
      PlotIndexSetInteger(plot,PLOT_DRAW_TYPE,DRAW_NONE);
      PlotIndexSetInteger(plot,PLOT_SHOW_DATA,true);
      PlotIndexSetString(plot,PLOT_LABEL,labels[plot-2]);
     }
   PlotIndexSetDouble(0,PLOT_EMPTY_VALUE,EMPTY_VALUE);
   PlotIndexSetDouble(1,PLOT_EMPTY_VALUE,EMPTY_VALUE);
  }

//+------------------------------------------------------------------+
//| Chart-object helpers.                                            |
void CreateTrendObject(const string name,const datetime time1,const double price1,
                       const datetime time2,const double price2,const color lineColor,
                       const ENUM_LINE_STYLE style,const int width,
                       const bool rayRight=false)
  {
   datetime t1=time1;
   datetime t2=time2;
   if(t1==t2)
     {
      const int sec=PeriodSeconds();
      t1=(sec>0 ? t2-(datetime)sec : t2-60);
     }
   if(!ObjectCreate(0,name,OBJ_TREND,0,t1,price1,t2,price2))
      return;
   ObjectSetInteger(0,name,OBJPROP_RAY_RIGHT,rayRight);
   ObjectSetInteger(0,name,OBJPROP_COLOR,lineColor);
   ObjectSetInteger(0,name,OBJPROP_STYLE,style);
   ObjectSetInteger(0,name,OBJPROP_WIDTH,width);
   ObjectSetInteger(0,name,OBJPROP_SELECTABLE,false);
   ObjectSetInteger(0,name,OBJPROP_HIDDEN,false);
   ObjectSetInteger(0,name,OBJPROP_ZORDER,2);
  }

void CreateTextObject(const string name,const datetime atTime,const double atPrice,
                      const string text,const color textColor,const ENUM_ANCHOR_POINT anchor,
                      const int fontSize)
  {
   if(!ObjectCreate(0,name,OBJ_TEXT,0,atTime,atPrice))
      return;
   ObjectSetString(0,name,OBJPROP_TEXT,text);
   ObjectSetString(0,name,OBJPROP_FONT,"Segoe UI Semibold");
   ObjectSetInteger(0,name,OBJPROP_FONTSIZE,fontSize);
   ObjectSetInteger(0,name,OBJPROP_COLOR,textColor);
   ObjectSetInteger(0,name,OBJPROP_ANCHOR,anchor);
   ObjectSetInteger(0,name,OBJPROP_SELECTABLE,false);
   ObjectSetInteger(0,name,OBJPROP_HIDDEN,false);
   ObjectSetInteger(0,name,OBJPROP_ZORDER,3);
  }

bool ZoneTooSmall(const double top,const double bottom,const double atr)
  {
   if(atr<=0.0)
      return(false);
   return(MathAbs(top-bottom)/atr<TB_ZONE_FILL_MIN_ATR);
  }

bool ZoneFillAllowed(const double top,const double bottom,const double atr)
  {
   if(ZoneTooSmall(top,bottom,atr))
      return(false);
   if(atr<=0.0)
      return(true);
   return(MathAbs(top-bottom)/atr<=TB_ZONE_FILL_MAX_ATR);
  }

datetime ZoneBoxRight(const datetime &time[],const int ratesTotal,
                      const int startIndex,const int eventIndex,const int padBars)
  {
   const int right=ClampBarIndex(MathMax(startIndex,eventIndex)+MathMax(0,padBars),
                                 g_lastClosedIndex);
   return(BarRightTime(time,ratesTotal,right));
  }

void CreateZoneBox(const string name,const datetime time1,const double top,
                   const datetime time2,const double bottom,
                   const color fillColor,const color edgeColor,const bool filled)
  {
   datetime t1=time1;
   datetime t2=time2;
   if(t2<=t1)
     {
      const int sec=PeriodSeconds();
      t2=t1+(datetime)(sec>0 ? sec : 60);
     }
   if(filled)
     {
      if(ObjectCreate(0,name,OBJ_RECTANGLE,0,t1,top,t2,bottom))
        {
         ObjectSetInteger(0,name,OBJPROP_COLOR,fillColor);
         ObjectSetInteger(0,name,OBJPROP_STYLE,STYLE_SOLID);
         ObjectSetInteger(0,name,OBJPROP_WIDTH,1);
         ObjectSetInteger(0,name,OBJPROP_FILL,true);
         ObjectSetInteger(0,name,OBJPROP_BACK,true);
         ObjectSetInteger(0,name,OBJPROP_SELECTABLE,false);
         ObjectSetInteger(0,name,OBJPROP_HIDDEN,false);
         ObjectSetInteger(0,name,OBJPROP_ZORDER,1);
         ObjectSetInteger(0,name,OBJPROP_RAY_RIGHT,false);
        }
     }
   const string edge=name+"_EG";
   if(!ObjectCreate(0,edge,OBJ_RECTANGLE,0,t1,top,t2,bottom))
      return;
   ObjectSetInteger(0,edge,OBJPROP_COLOR,edgeColor);
   ObjectSetInteger(0,edge,OBJPROP_STYLE,STYLE_SOLID);
   ObjectSetInteger(0,edge,OBJPROP_WIDTH,1);
   ObjectSetInteger(0,edge,OBJPROP_FILL,false);
   ObjectSetInteger(0,edge,OBJPROP_BACK,false);
   ObjectSetInteger(0,edge,OBJPROP_SELECTABLE,false);
   ObjectSetInteger(0,edge,OBJPROP_HIDDEN,false);
   ObjectSetInteger(0,edge,OBJPROP_ZORDER,2);
   ObjectSetInteger(0,edge,OBJPROP_RAY_RIGHT,false);
  }

int ClampBarIndex(const int index,const int lastClosed)
  {
   if(index<0)
      return(0);
   if(index>lastClosed)
      return(lastClosed);
   return(index);
  }

datetime BarRightTime(const datetime &time[],const int ratesTotal,const int index)
  {
   if(index<0 || ratesTotal<=0)
      return(0);
   if(index+1<ratesTotal)
      return(time[index+1]);
   const int sec=PeriodSeconds();
   return(sec>0 ? time[index]+(datetime)sec : time[index]);
  }


void EnsureHudLabel(const string objectPrefix,const string suffix,const int x,const int y,
                    const string text,const color textColor,const ENUM_ANCHOR_POINT anchor,
                    const int fontSize,const ENUM_BASE_CORNER corner)
  {
   const string name=objectPrefix+suffix;
   if(ObjectFind(0,name)<0)
      ObjectCreate(0,name,OBJ_LABEL,0,0,0);
   ObjectSetInteger(0,name,OBJPROP_CORNER,corner);
   ObjectSetInteger(0,name,OBJPROP_ANCHOR,anchor);
   ObjectSetInteger(0,name,OBJPROP_XDISTANCE,x);
   ObjectSetInteger(0,name,OBJPROP_YDISTANCE,y);
   ObjectSetInteger(0,name,OBJPROP_COLOR,textColor);
   ObjectSetInteger(0,name,OBJPROP_FONTSIZE,fontSize);
   ObjectSetString(0,name,OBJPROP_FONT,"Arial");
   ObjectSetString(0,name,OBJPROP_TEXT,text);
   ObjectSetInteger(0,name,OBJPROP_BACK,false);
   ObjectSetInteger(0,name,OBJPROP_SELECTABLE,false);
   ObjectSetInteger(0,name,OBJPROP_HIDDEN,false);
   ObjectSetInteger(0,name,OBJPROP_ZORDER,7);
  }

void EnsureHudLabel(const string suffix,const int x,const int y,const string text,
                    const color textColor,const ENUM_ANCHOR_POINT anchor,const int fontSize)
  {
   EnsureHudLabel(g_prefix+"HUD_",suffix,x,y,text,textColor,anchor,fontSize,CORNER_LEFT_UPPER);
  }

void EnsureRectLabel(const string name,const int x,const int y,const int width,const int height,
                     const color bg,const color border,const ENUM_BASE_CORNER corner,
                     const ENUM_ANCHOR_POINT anchor,const int zorder)
  {
   if(ObjectFind(0,name)>=0
      && (ENUM_OBJECT)ObjectGetInteger(0,name,OBJPROP_TYPE)!=OBJ_RECTANGLE_LABEL)
      ObjectDelete(0,name);
   if(ObjectFind(0,name)<0)
      ObjectCreate(0,name,OBJ_RECTANGLE_LABEL,0,0,0);
   ObjectSetInteger(0,name,OBJPROP_CORNER,corner);
   ObjectSetInteger(0,name,OBJPROP_ANCHOR,anchor);
   ObjectSetInteger(0,name,OBJPROP_XDISTANCE,x);
   ObjectSetInteger(0,name,OBJPROP_YDISTANCE,y);
   ObjectSetInteger(0,name,OBJPROP_XSIZE,MathMax(1,width));
   ObjectSetInteger(0,name,OBJPROP_YSIZE,MathMax(1,height));
   ObjectSetInteger(0,name,OBJPROP_BGCOLOR,bg);
   ObjectSetInteger(0,name,OBJPROP_COLOR,border);
   ObjectSetInteger(0,name,OBJPROP_BORDER_COLOR,border);
   ObjectSetInteger(0,name,OBJPROP_BORDER_TYPE,BORDER_FLAT);
   ObjectSetInteger(0,name,OBJPROP_STYLE,STYLE_SOLID);
   ObjectSetInteger(0,name,OBJPROP_WIDTH,1);
   ObjectSetInteger(0,name,OBJPROP_BACK,false);
   ObjectSetInteger(0,name,OBJPROP_SELECTABLE,false);
   ObjectSetInteger(0,name,OBJPROP_HIDDEN,false);
   ObjectSetInteger(0,name,OBJPROP_ZORDER,zorder);
  }

void PanelRowLayout(const bool fromRight,const bool fromTop,
                    const int offsetX,const int panelWidth,
                    int &keyX,int &valX,
                    ENUM_ANCHOR_POINT &keyAnchor,ENUM_ANCHOR_POINT &valAnchor)
  {
   if(fromRight)
     {
      keyX=offsetX+panelWidth-TB_PANEL_PAD;
      valX=offsetX+TB_PANEL_PAD;
     }
   else
     {
      keyX=offsetX+TB_PANEL_PAD;
      valX=offsetX+panelWidth-TB_PANEL_PAD;
     }
   keyAnchor=(fromTop ? ANCHOR_LEFT_UPPER : ANCHOR_LEFT_LOWER);
   valAnchor=(fromTop ? ANCHOR_RIGHT_UPPER : ANCHOR_RIGHT_LOWER);
  }

string CompactPrice(const double price)
  {
   if(!IsValue(price))
      return("");
   if(MathAbs(price)>=100.0)
      return(DoubleToString(price,2));
   return(DoubleToString(price,_Digits));
  }

string CompactBarTime(const datetime barTime)
  {
   if(barTime<=0)
      return("");
   MqlDateTime dt;
   TimeToStruct(barTime,dt);
   return(StringFormat("%02d.%02d %02d:%02d",dt.mon,dt.day,dt.hour,dt.min));
  }

string StructureEventLabel(const int event)
  {
   if(event==1)
      return("BOS↑");
   if(event==2)
      return("MSS↑");
   if(event==-1)
      return("BOS↓");
   if(event==-2)
      return("MSS↓");
   return("");
  }

string ClosedBarLastEventText(const int index)
  {
   if(index<0)
      return("—");
   const int oldest=MathMax(0,index-TB_HTF_EVENT_SCAN+1);
   for(int i=index;i>=oldest;i--)
     {
      const int event=(int)MathRound(ExtStructureEvent[i]);
      if(event==0)
         continue;
      const string ev=StructureEventLabel(event);
      if(IsValue(ExtBreakLevel[i]))
         return(ev+" "+CompactPrice(ExtBreakLevel[i]));
      return(ev);
     }
   for(int i=index;i>=oldest;i--)
     {
      if(ExtSweepHigh[i]>0.5)
         return("SwpH");
      if(ExtSweepLow[i]>0.5)
         return("SwpL");
      if(ExtBullVoid[i]>0.5)
         return("Void↑");
      if(ExtBearVoid[i]>0.5)
         return("Void↓");
     }
   return("—");
  }

void UpdateHud(const int index)
  {
   DeleteObjectsByPrefix(g_prefix+"HUD_");
   if(index<0)
      return;
   // Nested H4 (OBJ_CHART) must not draw a second HUD. Do not use
   // CHART_IS_OBJECT on the host — some builds report true once an
   // OBJ_CHART exists, which would also kill the parent HUD.
   if(!InpShowHud)
      return;
   if(InpShowHtfInset)
     {
      const ENUM_TIMEFRAMES htf=(InpHtfPeriod==PERIOD_CURRENT
                                 ?(ENUM_TIMEFRAMES)_Period:InpHtfPeriod);
      if((ENUM_TIMEFRAMES)_Period==htf)
        {
         long isObj=0;
         if(ChartGetInteger(ChartID(),CHART_IS_OBJECT,0,isObj) && isObj!=0)
            return;
        }
     }

   const int panelWidth=200;
   const int panelHeight=88;
   const int margin=10;
   EnsureRectLabel(g_prefix+"HUD_BACKGROUND",margin,margin,panelWidth,panelHeight,
                   TB_PANEL_BG,TB_PANEL_BORDER,CORNER_LEFT_UPPER,ANCHOR_LEFT_UPPER,8);

   const int bias=(int)MathRound(ExtBias[index]);
   const string biasText=(bias>0 ? "BULL" : bias<0 ? "BEAR" : "FLAT");
   const color biasColor=(bias>0 ? InpBullColor : bias<0 ? InpBearColor : InpMuteColor);
   int keyX=0;
   int valX=0;
   ENUM_ANCHOR_POINT keyAnchor=ANCHOR_LEFT_UPPER;
   ENUM_ANCHOR_POINT valAnchor=ANCHOR_RIGHT_UPPER;
   PanelRowLayout(false,true,margin,panelWidth,keyX,valX,keyAnchor,valAnchor);
   EnsureHudLabel("L0",keyX,12,"TB SMC 2026",TB_PANEL_TEXT,keyAnchor,8);
   EnsureHudLabel("R0",valX,12,TB_VERSION,InpAccentColor,valAnchor,8);
   EnsureHudLabel("L1",keyX,32,"Bias",TB_PANEL_KEY_COLOR,keyAnchor,8);
   EnsureHudLabel("R1",valX,32,biasText,biasColor,valAnchor,9);
   EnsureHudLabel("L2",keyX,50,"Swing",TB_PANEL_KEY_COLOR,keyAnchor,8);
   EnsureHudLabel("R2",valX,50,IntegerToString(g_swingLength),TB_PANEL_TEXT,valAnchor,8);
   EnsureHudLabel("L3",keyX,68,"Edge",TB_PANEL_KEY_COLOR,keyAnchor,8);
   EnsureHudLabel("R3",valX,68,(InpFocusMode ? "FOCUS" : "FULL"),InpAccentColor,valAnchor,8);
  }

//+------------------------------------------------------------------+
//| HTF context panel — iCustom same EX5, headless, closed bars.     |
//+------------------------------------------------------------------+
ENUM_TIMEFRAMES HtfResolvedPeriod()
  {
   if(InpHtfPeriod==PERIOD_CURRENT)
      return((ENUM_TIMEFRAMES)_Period);
   return(InpHtfPeriod);
  }

int HtfSparkCount()
  {
   return(MathMax(4,MathMin(TB_HTF_SPARK_MAX,InpHtfSparkBars)));
  }

int HtfPanelOffsetY()
  {
   if(InpHtfOffsetY!=0)
      return(InpHtfOffsetY);
   if(HtfCornerFromTop())
     {
      if(InpShowHud)
         return(10+TB_HUD_PANEL_HEIGHT+8);
      return(10);
     }
   return(10);
  }

bool HtfCornerFromRight()
  {
   return(InpHtfCorner==CORNER_RIGHT_UPPER || InpHtfCorner==CORNER_RIGHT_LOWER);
  }

bool HtfCornerFromTop()
  {
   return(InpHtfCorner==CORNER_RIGHT_UPPER || InpHtfCorner==CORNER_LEFT_UPPER);
  }

ENUM_ANCHOR_POINT HtfCornerAnchor()
  {
   if(InpHtfCorner==CORNER_LEFT_UPPER)
      return(ANCHOR_LEFT_UPPER);
   if(InpHtfCorner==CORNER_LEFT_LOWER)
      return(ANCHOR_LEFT_LOWER);
   if(InpHtfCorner==CORNER_RIGHT_LOWER)
      return(ANCHOR_RIGHT_LOWER);
   return(ANCHOR_RIGHT_UPPER);
  }

string HtfTimeframeLabel()
  {
   string raw=EnumToString(HtfResolvedPeriod());
   StringReplace(raw,"PERIOD_","");
   return(raw);
  }

string SelfIndicatorRelPath()
  {
   const string full=MQLInfoString(MQL_PROGRAM_PATH);
   string key="\\Indicators\\";
   int pos=StringFind(full,key);
   if(pos<0)
     {
      key="/Indicators/";
      pos=StringFind(full,key);
     }
   if(pos<0)
      return(MQLInfoString(MQL_PROGRAM_NAME));
   string rel=StringSubstr(full,pos+StringLen(key));
   const int ext=StringFind(rel,".ex5");
   if(ext>=0)
      rel=StringSubstr(rel,0,ext);
   const int extUpper=StringFind(rel,".EX5");
   if(extUpper>=0)
      rel=StringSubstr(rel,0,extUpper);
   return(rel);
  }

int CreateHtfChildHandle(const string indicatorName,const ENUM_TIMEFRAMES htf,
                         const bool drawObjects,const bool showHud,
                         const bool showHtfPanel,const bool showHtfInset)
  {
   // 51 positional slots: 7 `input group` headers (value 0) + 44 real inputs.
   // First 46 slots stay binary-compatible with 2.38 callers. New inset
   // group is appended; omitted trailing args keep compiled defaults.
   return(iCustom(_Symbol,htf,indicatorName,
                  0, // group "EA Engine Contract - iCustom inputs first"
                  InpEngineProfile,
                  InpEaSwingLength,
                  InpEaDisplacementAtr,
                  InpEaCellsKept,
                  InpEaVoidsKept,
                  InpEaSweepReclaimAtr,
                  InpEaMinimumVoidAtr,
                  InpEaMinimumCellAtr,
                  InpEaMaximumCellAgeBars,
                  InpEaMaximumVoidAgeBars,
                  InpEaSweepsRequireLiveSwing,
                  InpEaRequireBothSwings,
                  InpEaEnableStructure,
                  InpEaEnableCells,
                  InpEaEnableVoids,
                  InpEaEnableSweeps,
                  InpEaVoidRetention,
                  0, // group "TB SMC 2026 - Look"
                  InpBullColor,
                  InpBearColor,
                  InpAccentColor,
                  InpMuteColor,
                  InpFocusMode,
                  InpFocusLastN,
                  0, // group "TB SMC 2026 - Map"
                  InpShowStructure,
                  InpShowCells,
                  InpShowVoids,
                  InpShowSweeps,
                  InpShowTrail,
                  showHud,
                  0, // group "Closed-Bar Alerts"
                  false,   // InpEnableAlerts
                  false,   // InpEnablePopupAlert
                  false,   // InpEnablePushNotification
                  0, // group "Chart Objects"
                  drawObjects,
                  0, // group "HTF Context Panel"
                  showHtfPanel,
                  htf,     // child's InpHtfPeriod == child's _Period
                  InpHtfCorner,
                  InpHtfOffsetX,
                  InpHtfOffsetY,
                  InpHtfSparkBars,
                  false,   // InpShowHtfBreakOnChart
                  0,       // group "HTF Inset Chart"
                  showHtfInset,
                  InpHtfInsetWidthPct,
                  InpHtfInsetHeightPct,
                  InpHtfInsetScale));
  }

void InitHtfHandle()
  {
   g_htfHandle=INVALID_HANDLE;
   g_htfUnavailable=false;
   g_htfSameAsChart=false;
   g_htfReady=false;
   g_htfLastClosedTime=0;
   g_htfClockStamp=0;
   g_htfSparkCount=0;
   g_htfLastEvent=0;
   g_htfLastLevel=EMPTY_VALUE;

   if(!InpDrawObjects)
      return;
   if(InpShowHtfInset && !InpShowHtfBreakOnChart)
     {
      if(HtfResolvedPeriod()==(ENUM_TIMEFRAMES)_Period)
         g_htfSameAsChart=true;
      return;
     }
   if(!InpShowHtfPanel && !InpShowHtfBreakOnChart)
      return;

   const ENUM_TIMEFRAMES htf=HtfResolvedPeriod();
   if(htf==(ENUM_TIMEFRAMES)_Period)
     {
      g_htfSameAsChart=true;
      return;
     }

   g_htfHandle=CreateHtfChildHandle(SelfIndicatorRelPath(),htf,false,false,false,false);
   if(g_htfHandle==INVALID_HANDLE)
      g_htfHandle=CreateHtfChildHandle(MQLInfoString(MQL_PROGRAM_NAME),htf,false,false,false,false);
   if(g_htfHandle==INVALID_HANDLE)
      g_htfUnavailable=true;
  }

void ReleaseHtfHandle()
  {
   if(g_htfHandle!=INVALID_HANDLE)
     {
      IndicatorRelease(g_htfHandle);
      g_htfHandle=INVALID_HANDLE;
     }
  }

string HtfInsetObjectName()
  {
   return(g_prefix+"INSET_CHART");
  }

bool HtfInsetAllowed()
  {
   if(!InpDrawObjects || !InpShowHtfInset)
      return(false);
   if((bool)MQLInfoInteger(MQL_TESTER) && !(bool)MQLInfoInteger(MQL_VISUAL_MODE))
      return(false);
   if(HtfResolvedPeriod()==(ENUM_TIMEFRAMES)_Period)
      return(false);
   return(true);
  }

void HtfInsetGeometry(int &width,int &height,int &xDist,int &yDist)
  {
   const int chartW=MathMax(1,(int)ChartGetInteger(0,CHART_WIDTH_IN_PIXELS));
   const int chartH=MathMax(1,(int)ChartGetInteger(0,CHART_HEIGHT_IN_PIXELS));
   const int pctW=(int)MathRound(Clamp((double)InpHtfInsetWidthPct,38.0,45.0));
   const int pctH=(int)MathRound(Clamp((double)InpHtfInsetHeightPct,32.0,40.0));
   width=chartW*pctW/100;
   height=chartH*pctH/100;
   if(width<TB_HTF_INSET_MIN_WIDTH)
      width=(int)MathMin(TB_HTF_INSET_MIN_WIDTH,MathMax(220,chartW-20));
   if(height<TB_HTF_INSET_MIN_HEIGHT)
      height=(int)MathMin(TB_HTF_INSET_MIN_HEIGHT,MathMax(160,chartH-40));
   width=MathMin(width,chartW-TB_HTF_INSET_PAD_X-8);
   height=MathMin(height,chartH-TB_HTF_INSET_PAD_Y-8);
   width=MathMax(80,width);
   height=MathMax(80,height);
   // OBJ_CHART has no ANCHOR: X/Y is the top-left, size grows right/down.
   // LEFT_LOWER would push the 220px box off the bottom of the pane.
   xDist=TB_HTF_INSET_PAD_X;
   const int hudClear=(InpShowHud ? 10+88+10 : 8);
   yDist=chartH-height-TB_HTF_INSET_PAD_Y;
   if(yDist<hudClear)
     {
      height=MathMax(80,chartH-hudClear-TB_HTF_INSET_PAD_Y);
      yDist=hudClear;
     }
  }

void ApplyHtfInsetTheme(const long insetId)
  {
   ChartSetInteger(insetId,CHART_MODE,CHART_CANDLES);
   ChartSetInteger(insetId,CHART_AUTOSCROLL,true);
   ChartSetInteger(insetId,CHART_SHIFT,true);
   ChartSetInteger(insetId,CHART_SHOW_GRID,ChartGetInteger(0,CHART_SHOW_GRID));
   ChartSetInteger(insetId,CHART_SHOW_VOLUMES,CHART_VOLUME_HIDE);
   ChartSetInteger(insetId,CHART_SHOW_OHLC,false);
   ChartSetInteger(insetId,CHART_SHOW_ASK_LINE,false);
   ChartSetInteger(insetId,CHART_SHOW_BID_LINE,false);
   ChartSetInteger(insetId,CHART_SHOW_LAST_LINE,false);
   ChartSetInteger(insetId,CHART_SHOW_PERIOD_SEP,false);
   ChartSetInteger(insetId,CHART_SHOW_TRADE_LEVELS,false);
   ChartSetInteger(insetId,CHART_SHOW_ONE_CLICK,false);
   ChartSetInteger(insetId,CHART_COLOR_BACKGROUND,ChartGetInteger(0,CHART_COLOR_BACKGROUND));
   ChartSetInteger(insetId,CHART_COLOR_FOREGROUND,ChartGetInteger(0,CHART_COLOR_FOREGROUND));
   ChartSetInteger(insetId,CHART_COLOR_GRID,ChartGetInteger(0,CHART_COLOR_GRID));
   ChartSetInteger(insetId,CHART_COLOR_CHART_UP,ChartGetInteger(0,CHART_COLOR_CHART_UP));
   ChartSetInteger(insetId,CHART_COLOR_CHART_DOWN,ChartGetInteger(0,CHART_COLOR_CHART_DOWN));
   ChartSetInteger(insetId,CHART_COLOR_CANDLE_BULL,ChartGetInteger(0,CHART_COLOR_CANDLE_BULL));
   ChartSetInteger(insetId,CHART_COLOR_CANDLE_BEAR,ChartGetInteger(0,CHART_COLOR_CANDLE_BEAR));
   ChartSetInteger(insetId,CHART_COLOR_CHART_LINE,ChartGetInteger(0,CHART_COLOR_CHART_LINE));
   ChartSetInteger(insetId,CHART_COLOR_VOLUME,ChartGetInteger(0,CHART_COLOR_VOLUME));
   ChartSetString(insetId,CHART_COMMENT,HtfTimeframeLabel());
   ChartRedraw(insetId);
  }

bool HtfInsetHasSmc(const long insetId)
  {
   const int total=ChartIndicatorsTotal(insetId,0);
   for(int i=0;i<total;i++)
     {
      const string nm=ChartIndicatorName(insetId,0,i);
      if(StringFind(nm,"TB SMC 2026")==0)
         return(true);
     }
   return(false);
  }

void ReleaseHtfInset()
  {
   if(g_htfInsetChartId>0)
     {
      for(int i=ChartIndicatorsTotal(g_htfInsetChartId,0)-1;i>=0;i--)
        {
         const string nm=ChartIndicatorName(g_htfInsetChartId,0,i);
         if(StringFind(nm,"TB SMC 2026")==0)
            ChartIndicatorDelete(g_htfInsetChartId,0,nm);
        }
     }
   if(g_htfInsetHandle!=INVALID_HANDLE)
     {
      IndicatorRelease(g_htfInsetHandle);
      g_htfInsetHandle=INVALID_HANDLE;
     }
   g_htfInsetChartId=0;
   g_htfInsetAttached=false;
   g_htfInsetTplSaved=false;
   g_htfInsetApplyTried=false;
   g_htfInsetStage=0;
   if(g_htfInsetFgSaved)
     {
      ChartSetInteger(ChartID(),CHART_FOREGROUND,g_htfInsetPrevFg);
      g_htfInsetFgSaved=false;
     }
   if(g_prefix!="")
      ObjectDelete(0,HtfInsetObjectName());
  }

void LayoutHtfInsetObject(const string name,const int width,const int height,
                          const int xDist,const int yDist,const ENUM_TIMEFRAMES htf,
                          const int scale)
  {
   const long chart=ChartID();
   ObjectSetInteger(chart,name,OBJPROP_CORNER,CORNER_LEFT_UPPER);
   ObjectSetInteger(chart,name,OBJPROP_XDISTANCE,xDist);
   ObjectSetInteger(chart,name,OBJPROP_YDISTANCE,yDist);
   ObjectSetInteger(chart,name,OBJPROP_XSIZE,width);
   ObjectSetInteger(chart,name,OBJPROP_YSIZE,height);
   ObjectSetString(chart,name,OBJPROP_SYMBOL,_Symbol);
   ObjectSetInteger(chart,name,OBJPROP_PERIOD,htf);
   ObjectSetInteger(chart,name,OBJPROP_CHART_SCALE,scale);
   ObjectSetInteger(chart,name,OBJPROP_DATE_SCALE,true);
   ObjectSetInteger(chart,name,OBJPROP_PRICE_SCALE,true);
   ObjectSetInteger(chart,name,OBJPROP_SELECTABLE,false);
   ObjectSetInteger(chart,name,OBJPROP_HIDDEN,false);
   ObjectSetInteger(chart,name,OBJPROP_BACK,false);
   ObjectSetInteger(chart,name,OBJPROP_ZORDER,1000);
   ObjectSetInteger(chart,name,OBJPROP_COLOR,InpAccentColor);
   ObjectSetInteger(chart,name,OBJPROP_TIMEFRAMES,OBJ_ALL_PERIODS);
  }

bool InsetHitRect(const int x,const int y,const int x0,const int y0,
                  const int width,const int height,const int pad)
  {
   return(x>=x0-pad && x<=x0+width+pad && y>=y0-pad && y<=y0+height+pad);
  }

bool InsetHitBox(const int left,const int top,const int right,const int bottom,
                 const int x0,const int y0,const int width,const int height,const int pad)
  {
   return(right>=x0-pad && left<=x0+width+pad && bottom>=y0-pad && top<=y0+height+pad);
  }

void ClipDrawObjectsUnderInset()
  {
   if(!HtfInsetAllowed())
      return;
   int width=0;
   int height=0;
   int x0=0;
   int y0=0;
   HtfInsetGeometry(width,height,x0,y0);
   const int pad=80;
   const string prefix=g_prefix+"DRAW_";
   const long chart=ChartID();
   const int chartW=(int)ChartGetInteger(chart,CHART_WIDTH_IN_PIXELS);
   for(int i=ObjectsTotal(chart)-1;i>=0;i--)
     {
      const string name=ObjectName(chart,i);
      if(StringFind(name,prefix)!=0)
         continue;
      const ENUM_OBJECT type=(ENUM_OBJECT)ObjectGetInteger(chart,name,OBJPROP_TYPE);
      bool hit=false;
      if(type==OBJ_TEXT || type==OBJ_ARROW || type==OBJ_ARROW_RIGHT_PRICE)
        {
         const datetime t=(datetime)ObjectGetInteger(chart,name,OBJPROP_TIME);
         const double p=ObjectGetDouble(chart,name,OBJPROP_PRICE);
         int x=0;
         int y=0;
         if(ChartTimePriceToXY(chart,0,t,p,x,y))
            hit=InsetHitRect(x,y,x0,y0,width,height,pad);
        }
      else if(type==OBJ_TREND || type==OBJ_RECTANGLE || type==OBJ_CHANNEL)
        {
         const datetime t1=(datetime)ObjectGetInteger(chart,name,OBJPROP_TIME);
         const datetime t2=(datetime)ObjectGetInteger(chart,name,OBJPROP_TIME,1);
         const double p1=ObjectGetDouble(chart,name,OBJPROP_PRICE);
         const double p2=ObjectGetDouble(chart,name,OBJPROP_PRICE,1);
         int x1=0;
         int y1=0;
         int x2=0;
         int y2=0;
         if(!ChartTimePriceToXY(chart,0,t1,p1,x1,y1))
            continue;
         if(!ChartTimePriceToXY(chart,0,t2,p2,x2,y2))
           {
            x2=x1;
            y2=y1;
           }
         if((bool)ObjectGetInteger(chart,name,OBJPROP_RAY_RIGHT))
            x2=MathMax(x2,chartW);
         hit=InsetHitBox(MathMin(x1,x2),MathMin(y1,y2),MathMax(x1,x2),MathMax(y1,y2),
                         x0,y0,width,height,pad);
        }
      // OBJPROP_HIDDEN only removes the name from Object List — the
      // object still paints. OBJ_NO_PERIODS is the actual chart hide.
      if(hit)
         ObjectSetInteger(chart,name,OBJPROP_TIMEFRAMES,OBJ_NO_PERIODS);
      else
         ObjectSetInteger(chart,name,OBJPROP_TIMEFRAMES,OBJ_ALL_PERIODS);
     }
  }

void EnsureHtfInset()
  {
   const string name=HtfInsetObjectName();
   const long chart=ChartID();
   if(!HtfInsetAllowed())
     {
      if(ObjectFind(chart,name)>=0 || g_htfInsetHandle!=INVALID_HANDLE)
         ReleaseHtfInset();
      return;
     }

   int width=0;
   int height=0;
   int xDist=0;
   int yDist=0;
   HtfInsetGeometry(width,height,xDist,yDist);
   const ENUM_TIMEFRAMES htf=HtfResolvedPeriod();
   const int scale=(int)MathRound(Clamp((double)InpHtfInsetScale,0.0,5.0));

   // Save host look+SMC once, before the inset object exists. A 4112
   // must not block ObjectCreate — reuse leftover tb_smc_inset.tpl.
   if(!g_htfInsetTplSaved)
     {
      ResetLastError();
      if(ChartSaveTemplate(0,"tb_smc_inset"))
         g_htfInsetStage=1;
      else
         Print("TB SMC 2026 ChartSaveTemplate failed err=",GetLastError());
      g_htfInsetTplSaved=true;
     }

   if(ObjectFind(chart,name)<0)
     {
      ResetLastError();
      if(!ObjectCreate(chart,name,OBJ_CHART,0,0,0,0,0))
        {
         Print("TB SMC 2026 OBJ_CHART create failed err=",GetLastError()," name=",name);
         return;
        }
      Print("TB SMC 2026 OBJ_CHART created ",width,"x",height,
            " at LEFT_UPPER ",xDist,",",yDist);
      g_htfInsetStage=2;
     }

   LayoutHtfInsetObject(name,width,height,xDist,yDist,htf,scale);
   if(!g_htfInsetFgSaved)
     {
      g_htfInsetPrevFg=ChartGetInteger(chart,CHART_FOREGROUND);
      g_htfInsetFgSaved=true;
     }
   ChartSetInteger(chart,CHART_FOREGROUND,false);
   ChartRedraw(chart);

   const long insetId=(long)ObjectGetInteger(chart,name,OBJPROP_CHART_ID);
   if(insetId<=0 || insetId==chart)
      return;
   g_htfInsetChartId=insetId;
   ApplyHtfInsetTheme(insetId);

   if(HtfInsetHasSmc(insetId))
     {
      g_htfInsetAttached=true;
      g_htfInsetStage=3;
      return;
     }
   if(g_htfInsetApplyTried)
      return;

   g_htfInsetApplyTried=true;
   ResetLastError();
   if(!ChartApplyTemplate(insetId,"tb_smc_inset.tpl"))
      Print("TB SMC 2026 ChartApplyTemplate H4 inset failed err=",GetLastError(),
            " insetId=",insetId);
   if((ENUM_TIMEFRAMES)ChartPeriod(insetId)!=htf || ChartSymbol(insetId)!=_Symbol)
      ChartSetSymbolPeriod(insetId,_Symbol,htf);
   ObjectSetInteger(chart,name,OBJPROP_PERIOD,htf);
   LayoutHtfInsetObject(name,width,height,xDist,yDist,htf,scale);
   ApplyHtfInsetTheme(insetId);
   if(HtfInsetHasSmc(insetId))
     {
      g_htfInsetAttached=true;
      g_htfInsetStage=3;
     }
  }

void StoreHtfSparkFromRates(const MqlRates &rates[],const int copied)
  {
   g_htfSparkCount=0;
   if(copied<=0)
      return;
   ArrayResize(g_htfSparkOpen,copied);
   ArrayResize(g_htfSparkHigh,copied);
   ArrayResize(g_htfSparkLow,copied);
   ArrayResize(g_htfSparkClose,copied);
   for(int i=0;i<copied;i++)
     {
      g_htfSparkOpen[i]=rates[i].open;
      g_htfSparkHigh[i]=rates[i].high;
      g_htfSparkLow[i]=rates[i].low;
      g_htfSparkClose[i]=rates[i].close;
     }
   g_htfSparkCount=copied;
   g_htfOpen=rates[copied-1].open;
   g_htfHigh=rates[copied-1].high;
   g_htfLow=rates[copied-1].low;
   g_htfClose=rates[copied-1].close;
  }

void RefreshHtfSnapshot(const bool force)
  {
   if(!InpDrawObjects || (!InpShowHtfPanel && !InpShowHtfBreakOnChart))
      return;
   if(g_htfUnavailable)
      return;

   const ENUM_TIMEFRAMES htf=HtfResolvedPeriod();
   const int sparkN=HtfSparkCount();

   if(g_htfSameAsChart)
     {
      if(g_lastClosedIndex<0)
         return;
      const datetime closed=(g_lastClosedIndex<g_cachedRates ? g_cachedTime[g_lastClosedIndex]
                                                            : iTime(_Symbol,htf,1));
      if(!force && g_htfReady && closed==g_htfLastClosedTime)
         return;
      g_htfLastClosedTime=closed;
      g_htfBias=ExtBias[g_lastClosedIndex];
      g_htfClosedValid=ExtClosedBarValid[g_lastClosedIndex];
      g_htfLastEvent=0;
      g_htfLastLevel=EMPTY_VALUE;
      const int oldest=MathMax(0,g_lastClosedIndex-TB_HTF_EVENT_SCAN+1);
      for(int i=g_lastClosedIndex;i>=oldest;i--)
        {
         const int event=(int)MathRound(ExtStructureEvent[i]);
         if(event!=0)
           {
            g_htfLastEvent=event;
            g_htfLastLevel=ExtBreakLevel[i];
            break;
           }
        }
      MqlRates rates[];
      ArraySetAsSeries(rates,false);
      const int copied=CopyRates(_Symbol,htf,1,sparkN,rates);
      StoreHtfSparkFromRates(rates,copied);
      g_htfReady=true;
      return;
     }

   if(g_htfHandle==INVALID_HANDLE)
     {
      g_htfUnavailable=true;
      return;
     }
   const int calculated=BarsCalculated(g_htfHandle);
   if(calculated<0)
      return;
   if(calculated<TB_ATR_LENGTH+g_swingLength*2+2)
      return;

   const datetime closed=iTime(_Symbol,htf,1);
   if(closed<=0)
      return;
   if(!force && g_htfReady && closed==g_htfLastClosedTime)
      return;

   double bias[];
   double valid[];
   if(CopyBuffer(g_htfHandle,2,1,1,bias)<1 || CopyBuffer(g_htfHandle,26,1,1,valid)<1)
      return;
   g_htfBias=bias[0];
   g_htfClosedValid=valid[0];

   const int scan=MathMin(TB_HTF_EVENT_SCAN,calculated-1);
   double events[];
   double levels[];
   ArraySetAsSeries(events,true);
   ArraySetAsSeries(levels,true);
   if(CopyBuffer(g_htfHandle,27,1,scan,events)<1 || CopyBuffer(g_htfHandle,29,1,scan,levels)<1)
      return;
   g_htfLastEvent=0;
   g_htfLastLevel=EMPTY_VALUE;
   const int evCount=ArraySize(events);
   for(int i=0;i<evCount;i++)
     {
      const int event=(int)MathRound(events[i]);
      if(event!=0)
        {
         g_htfLastEvent=event;
         if(i<ArraySize(levels))
            g_htfLastLevel=levels[i];
         break;
        }
     }

   MqlRates rates[];
   ArraySetAsSeries(rates,false);
   const int copied=CopyRates(_Symbol,htf,1,sparkN,rates);
   StoreHtfSparkFromRates(rates,copied);
   g_htfLastClosedTime=closed;
   g_htfReady=true;
  }

bool HtfChildRejected()
  {
   if(g_htfUnavailable)
      return(true);
   if(g_htfSameAsChart || g_htfHandle==INVALID_HANDLE)
      return(false);
   return(BarsCalculated(g_htfHandle)<0);
  }

string HtfCountdownText()
  {
   if(g_htfUnavailable)
      return("HTF n/a");
   const ENUM_TIMEFRAMES htf=HtfResolvedPeriod();
   const datetime forming=iTime(_Symbol,htf,0);
   const datetime closed=iTime(_Symbol,htf,1);
   if(forming<=0)
      return(closed>0 ? "closed "+CompactBarTime(closed) : "no H4");
   if((closed>0 && forming==closed) ||
      (g_htfLastClosedTime>0 && forming==g_htfLastClosedTime))
      return("closed "+CompactBarTime(closed>0 ? closed : g_htfLastClosedTime));

   const int periodSec=PeriodSeconds(htf);
   const datetime nextClose=forming+periodSec;
   const datetime now=TimeCurrent();
   if(now>nextClose+periodSec)
      return("closed "+CompactBarTime(closed>0 ? closed : forming));
   int remain=(int)(nextClose-now);
   if(remain<0)
      remain=0;
   const int hours=remain/3600;
   const int mins=(remain%3600)/60;
   const int secs=remain%60;
   if(hours>0)
      return(StringFormat("%d:%02d:%02d",hours,mins,secs));
   return(StringFormat("%d:%02d",mins,secs));
  }

string HtfBiasText()
  {
   if(HtfChildRejected())
      return("HTF n/a");
   if(!g_htfReady)
      return("…");
   if(g_htfClosedValid<0.5)
      return("—");
   const int bias=(int)MathRound(g_htfBias);
   if(bias>0)
      return("BULL");
   if(bias<0)
      return("BEAR");
   return("FLAT");
  }

string HtfLastEventText()
  {
   if(HtfChildRejected())
      return("HTF n/a");
   if(!g_htfReady || g_htfLastEvent==0)
      return("—");
   const string ev=StructureEventLabel(g_htfLastEvent);
   if(ev=="")
      return("—");
   if(IsValue(g_htfLastLevel))
      return(ev+" "+CompactPrice(g_htfLastLevel));
   return(ev);
  }

int HtfSparkPriceY(const double price,const double pmin,const double pmax,
                   const int top,const int height)
  {
   if(pmax<=pmin)
      return(top+height/2);
   const double t=(pmax-price)/(pmax-pmin);
   return(top+(int)MathRound(t*height));
  }

void UpdateHtfSpark(const int yBase)
  {
   const string prefix=g_prefix+"HTF_";
   const ENUM_ANCHOR_POINT panelAnchor=HtfCornerAnchor();
   const int wellInset=10;
   const int innerPad=5;
   const int wellH=42;
   const int wellW=TB_HTF_PANEL_WIDTH-wellInset*2;
   const int wellX=InpHtfOffsetX+wellInset;
   const int wellY=yBase+TB_HTF_PANEL_HEIGHT-wellInset-wellH;
   EnsureRectLabel(prefix+"SPK_WELL",wellX,wellY,wellW,wellH,
                   TB_SPARK_WELL,TB_PANEL_BORDER,InpHtfCorner,panelAnchor,5);

   for(int extra=0;extra<TB_HTF_SPARK_MAX;extra++)
     {
      ObjectDelete(0,prefix+"SPK_"+IntegerToString(extra));
      if(extra>=g_htfSparkCount)
        {
         ObjectDelete(0,prefix+"SPK_w"+IntegerToString(extra));
         ObjectDelete(0,prefix+"SPK_b"+IntegerToString(extra));
        }
     }

   if(g_htfSparkCount<=0)
      return;

   double pmin=g_htfSparkLow[0];
   double pmax=g_htfSparkHigh[0];
   for(int i=1;i<g_htfSparkCount;i++)
     {
      if(g_htfSparkLow[i]<pmin)
         pmin=g_htfSparkLow[i];
      if(g_htfSparkHigh[i]>pmax)
         pmax=g_htfSparkHigh[i];
     }
   if(pmax<=pmin)
     {
      pmax=pmin+1.0;
      pmin=pmin-1.0;
     }

   const int n=MathMax(1,g_htfSparkCount);
   const int areaW=wellW-innerPad*2;
   const int areaH=wellH-innerPad*2;
   const int slot=MathMax(6,areaW/n);
   const int bodyW=MathMax(3,MathMin(6,slot/2));
   const int wickW=1;
   const int chartW=(int)ChartGetInteger(0,CHART_WIDTH_IN_PIXELS);
   const int chartH=(int)ChartGetInteger(0,CHART_HEIGHT_IN_PIXELS);
   const bool absPixels=(chartW>2 && chartH>2);
   int areaLeft=wellX+innerPad;
   int areaTop=wellY+innerPad;
   if(absPixels)
     {
      if(HtfCornerFromRight())
         areaLeft=chartW-wellX-wellW+innerPad;
      if(!HtfCornerFromTop())
         areaTop=chartH-wellY-wellH+innerPad;
     }

   for(int i=0;i<g_htfSparkCount;i++)
     {
      const int slotLeft=areaLeft+i*slot;
      const int wickX=slotLeft+(slot-wickW)/2;
      const int bodyX=slotLeft+(slot-bodyW)/2;
      const int yHigh=HtfSparkPriceY(g_htfSparkHigh[i],pmin,pmax,areaTop,areaH);
      const int yLow=HtfSparkPriceY(g_htfSparkLow[i],pmin,pmax,areaTop,areaH);
      const int yOpen=HtfSparkPriceY(g_htfSparkOpen[i],pmin,pmax,areaTop,areaH);
      const int yClose=HtfSparkPriceY(g_htfSparkClose[i],pmin,pmax,areaTop,areaH);
      const int yMax=areaTop+areaH-1;
      const int wickTop=MathMax(areaTop,MathMin(yHigh,yLow));
      const int wickBot=MathMin(yMax,MathMax(yHigh,yLow));
      const int bodyTop=MathMax(areaTop,MathMin(yOpen,yClose));
      const int bodyBot=MathMin(yMax,MathMax(yOpen,yClose));
      const int wickH=MathMax(3,wickBot-wickTop);
      const int bodyH=MathMax(2,bodyBot-bodyTop);
      const bool up=(g_htfSparkClose[i]>=g_htfSparkOpen[i]);
      const color bodyColor=(up ? TB_SPARK_UP : TB_SPARK_DN);
      const color wickColor=(up ? TB_SPARK_WICK_UP : TB_SPARK_WICK_DN);
      const ENUM_BASE_CORNER sparkCorner=(absPixels ? CORNER_LEFT_UPPER : InpHtfCorner);
      const ENUM_ANCHOR_POINT sparkAnchor=(absPixels ? ANCHOR_LEFT_UPPER : panelAnchor);
      EnsureRectLabel(prefix+"SPK_w"+IntegerToString(i),wickX,wickTop,wickW,wickH,
                      wickColor,wickColor,sparkCorner,sparkAnchor,6);
      EnsureRectLabel(prefix+"SPK_b"+IntegerToString(i),bodyX,bodyTop,bodyW,bodyH,
                      bodyColor,bodyColor,sparkCorner,sparkAnchor,7);
     }
  }

void UpdateHtfPanel()
  {
   const string prefix=g_prefix+"HTF_";
   DeleteObjectsByPrefix(prefix);
   if(!InpDrawObjects || !InpShowHtfPanel || g_htfSameAsChart)
      return;

   const int panelWidth=TB_HTF_PANEL_WIDTH;
   const int panelHeight=TB_HTF_PANEL_HEIGHT;
   const int yBase=HtfPanelOffsetY();
   const ENUM_ANCHOR_POINT boxAnchor=HtfCornerAnchor();
   EnsureRectLabel(prefix+"BACKGROUND",InpHtfOffsetX,yBase,panelWidth,panelHeight,
                   TB_PANEL_BG,TB_PANEL_BORDER,InpHtfCorner,boxAnchor,4);

   const bool fromRight=HtfCornerFromRight();
   const bool fromTop=HtfCornerFromTop();
   int keyX=0;
   int valX=0;
   ENUM_ANCHOR_POINT keyAnchor=ANCHOR_LEFT_UPPER;
   ENUM_ANCHOR_POINT valAnchor=ANCHOR_RIGHT_UPPER;
   PanelRowLayout(fromRight,fromTop,InpHtfOffsetX,panelWidth,keyX,valX,keyAnchor,valAnchor);
   const int y0=yBase+7;
   const int y1=yBase+24;
   const int y2=yBase+41;
   const int y3=yBase+58;
   const int y4=yBase+75;

   string title=HtfTimeframeLabel();
   string titleRight="";
   if(g_htfUnavailable || (HtfChildRejected() && g_htfLastClosedTime<=0))
      titleRight="HTF n/a";
   else if(g_htfSameAsChart)
      title="HTF = chart";
   if(g_htfLastClosedTime>0 && !g_htfUnavailable)
      titleRight=CompactBarTime(g_htfLastClosedTime);

   const int bias=(int)MathRound(g_htfBias);
   const color biasColor=(g_htfClosedValid<0.5 ? InpMuteColor
                          : (bias>0 ? InpBullColor : bias<0 ? InpBearColor : InpMuteColor));
   string closeText="—";
   if(HtfChildRejected())
      closeText="HTF n/a";
   else if(g_htfReady && g_htfSparkCount>0)
      closeText=CompactPrice(g_htfClose);

   EnsureHudLabel(prefix,"L0",keyX,y0,title,TB_PANEL_TEXT,keyAnchor,9,InpHtfCorner);
   EnsureHudLabel(prefix,"R0",valX,y0,titleRight,InpAccentColor,valAnchor,8,InpHtfCorner);
   EnsureHudLabel(prefix,"L1",keyX,y1,"Clock",TB_PANEL_KEY_COLOR,keyAnchor,8,InpHtfCorner);
   EnsureHudLabel(prefix,"R1",valX,y1,HtfCountdownText(),TB_PANEL_TEXT,valAnchor,8,InpHtfCorner);
   EnsureHudLabel(prefix,"L2",keyX,y2,"Bias",TB_PANEL_KEY_COLOR,keyAnchor,8,InpHtfCorner);
   EnsureHudLabel(prefix,"R2",valX,y2,HtfBiasText(),biasColor,valAnchor,9,InpHtfCorner);
   EnsureHudLabel(prefix,"L3",keyX,y3,"Last",TB_PANEL_KEY_COLOR,keyAnchor,8,InpHtfCorner);
   EnsureHudLabel(prefix,"R3",valX,y3,HtfLastEventText(),TB_PANEL_TEXT,valAnchor,8,InpHtfCorner);
   EnsureHudLabel(prefix,"L4",keyX,y4,"Close",TB_PANEL_KEY_COLOR,keyAnchor,8,InpHtfCorner);
   EnsureHudLabel(prefix,"R4",valX,y4,closeText,TB_PANEL_TEXT,valAnchor,8,InpHtfCorner);
   UpdateHtfSpark(yBase);
  }

void UpdateHtfBreakLevel()
  {
   const string line=g_prefix+"DRAW_HTF_LVL";
   const string label=g_prefix+"DRAW_HTF_LVL_LB";
   ObjectDelete(0,line);
   ObjectDelete(0,label);
   if(!InpDrawObjects || !InpShowHtfBreakOnChart)
      return;
   if(g_lastClosedIndex<0 || g_cachedRates<=0)
      return;
   if(g_htfLastEvent==0 || !IsValue(g_htfLastLevel))
      return;

   int start=g_lastClosedIndex-50;
   if(start<0)
      start=0;
   const datetime t1=g_cachedTime[start];
   const datetime t2=g_cachedTime[g_lastClosedIndex];
   const color eventColor=(g_htfLastEvent>0 ? InpBullColor : InpBearColor);
   const string text=HtfTimeframeLabel()+" "+StructureEventLabel(g_htfLastEvent);
   CreateTrendObject(line,t1,g_htfLastLevel,t2,g_htfLastLevel,eventColor,STYLE_DASH,1);
   CreateTextObject(label,t2,g_htfLastLevel,text,eventColor,
                    (g_htfLastEvent>0 ? ANCHOR_LOWER : ANCHOR_UPPER),8);
  }

void UpdateHtfClock()
  {
   if(!InpDrawObjects)
      return;
   if((bool)MQLInfoInteger(MQL_TESTER) && !(bool)MQLInfoInteger(MQL_VISUAL_MODE))
      return;
   if(!InpShowHtfPanel)
      return;

   const datetime now=TimeCurrent();
   if(g_htfClockStamp!=0 && now==g_htfClockStamp && g_htfReady)
      return;
   g_htfClockStamp=now;

   if(!g_htfSameAsChart && g_htfHandle!=INVALID_HANDLE)
     {
      const datetime closed=iTime(_Symbol,HtfResolvedPeriod(),1);
      if((!g_htfReady && !g_htfUnavailable) || (closed>0 && closed!=g_htfLastClosedTime))
        {
         RefreshHtfSnapshot(false);
         UpdateHtfPanel();
         UpdateHtfBreakLevel();
         ChartRedraw();
         return;
        }
     }

   if(ObjectFind(0,g_prefix+"HTF_R1")<0)
     {
      UpdateHtfPanel();
      ChartRedraw();
      return;
     }

   const bool fromRight=HtfCornerFromRight();
   const bool fromTop=HtfCornerFromTop();
   const int valX=(fromRight ? InpHtfOffsetX+TB_PANEL_PAD
                             : InpHtfOffsetX+TB_HTF_PANEL_WIDTH-TB_PANEL_PAD);
   const ENUM_ANCHOR_POINT valAnchor=(fromTop ? ANCHOR_RIGHT_UPPER : ANCHOR_RIGHT_LOWER);
   EnsureHudLabel(g_prefix+"HTF_","R1",valX,HtfPanelOffsetY()+24,HtfCountdownText(),
                  TB_PANEL_TEXT,valAnchor,8,InpHtfCorner);
   ChartRedraw();
  }

//+------------------------------------------------------------------+
//| Rebuild all owned visual objects from deterministic buffers.      |
//| CELL/void fills stay at the origin/gap. Never 2099 time2.         |
//| Live edges/CE/Trail are OBJ_TREND + RAY_RIGHT.                    |
//+------------------------------------------------------------------+
void RebuildVisuals(const int ratesTotal,const datetime &time[])
  {
   DeleteObjectsByPrefix(g_prefix+"DRAW_");
   for(int leftover=ObjectsTotal(0)-1;leftover>=0;leftover--)
     {
      const string leftoverName=ObjectName(0,leftover);
      if(StringFind(leftoverName,g_prefix)==0 && StringFind(leftoverName,"_LIVE")>=0)
         ObjectDelete(0,leftoverName);
     }
   if(HtfInsetAllowed())
      EnsureHtfInset();
   if(g_lastClosedIndex<0)
      return;

   const color background=ChartBackground();
   const color bullCellFill=ZoneWash(InpBullColor,0.10);
   const color bearCellFill=ZoneWash(InpBearColor,0.10);
   const color bullVoidStrong=ZoneWash(InpBullColor,0.16);
   const color bullVoidSoft=ZoneWash(InpBullColor,0.10);
   const color bearVoidStrong=ZoneWash(InpBearColor,0.16);
   const color bearVoidSoft=ZoneWash(InpBearColor,0.10);
   const datetime lastClosedTime=time[g_lastClosedIndex];
   const int newestVoidEvent=(ArraySize(g_voids)>0 ? g_voids[0].eventIndex : -1);
   const int structureCap=(InpFocusMode
                           ? MathMax(1,MathMin(TB_MAX_STRUCTURE_OBJECTS,InpFocusLastN))
                           : TB_MAX_STRUCTURE_OBJECTS);
   const double atrNow=(IsValue(ExtAtr[g_lastClosedIndex]) ? ExtAtr[g_lastClosedIndex] : 0.0);

   if(InpShowStructure)
     {
      int created=0;
      for(int index=g_lastClosedIndex;index>=0 && created<structureCap;index--)
        {
         const int event=(int)MathRound(ExtStructureEvent[index]);
         if(event==0 || !IsValue(ExtBreakLevel[index]))
            continue;
         int pivot=(index<ArraySize(g_breakOrigin) ? g_breakOrigin[index] : index);
         const double level=ExtBreakLevel[index];
         pivot=MathMax(0,MathMin(index,pivot));
         const bool mss=(MathAbs(event)==2);
         const bool nearest=(created==0);
         const color eventColor=(event>0 ? InpBullColor : InpBearColor);
         const string base=g_prefix+"DRAW_STRUCT_"+IntegerToString(index);
         const datetime structRight=(nearest ? lastClosedTime : time[index]);
         CreateTrendObject(base+"_LN",time[pivot],level,structRight,level,eventColor,
                           (mss ? STYLE_SOLID : STYLE_DASH),(mss ? 2 : 1),nearest);
         const double labelPrice=(atrNow>0.0
                                  ? (event>0 ? level+atrNow*0.06 : level-atrNow*0.06)
                                  : level);
         CreateTextObject(base+"_LB",time[index],labelPrice,(mss ? "MSS" : "BOS"),
                          eventColor,(event>0 ? ANCHOR_LOWER : ANCHOR_UPPER),8);
         created++;
        }
     }

   if(InpShowCells)
     {
      for(int i=0;i<ArraySize(g_cells);i++)
        {
         const int start=ClampBarIndex(g_cells[i].startIndex,g_lastClosedIndex);
         const int eventIdx=ClampBarIndex(g_cells[i].eventIndex,g_lastClosedIndex);
         const bool nearest=(i==0);
         const datetime left=time[start];
         const datetime boxRight=ZoneBoxRight(time,ratesTotal,start,eventIdx,TB_CELL_BOX_PAD_BARS);
         const string name=g_prefix+"DRAW_CELL_"+IntegerToString(i);
         const color edge=(g_cells[i].side>0 ? InpBullColor : InpBearColor);
         const color fill=(g_cells[i].side>0 ? bullCellFill : bearCellFill);
         if(!ZoneTooSmall(g_cells[i].top,g_cells[i].bottom,atrNow))
            CreateZoneBox(name,left,g_cells[i].top,boxRight,g_cells[i].bottom,fill,edge,
                          ZoneFillAllowed(g_cells[i].top,g_cells[i].bottom,atrNow));
         if(nearest)
           {
            CreateTrendObject(name+"_TH",left,g_cells[i].top,lastClosedTime,g_cells[i].top,edge,STYLE_DOT,1,true);
            CreateTrendObject(name+"_BH",left,g_cells[i].bottom,lastClosedTime,g_cells[i].bottom,edge,STYLE_DOT,1,true);
            CreateTextObject(name+"_LB",left,g_cells[i].top,"CELL",edge,ANCHOR_RIGHT_UPPER,7);
           }
        }
     }

   if(InpShowVoids)
     {
      for(int i=0;i<ArraySize(g_voids);i++)
        {
         const int vStart=ClampBarIndex(g_voids[i].startIndex,g_lastClosedIndex);
         const int vEvent=MathMax(vStart,ClampBarIndex(g_voids[i].eventIndex,g_lastClosedIndex));
         const bool nearest=(i==0);
         const datetime left=time[vStart];
         const datetime boxRight=ZoneBoxRight(time,ratesTotal,vStart,vEvent,0);
         const string base=g_prefix+"DRAW_VOID_"+IntegerToString(i);
         const color strong=(g_voids[i].side>0 ? bullVoidStrong : bearVoidStrong);
         const color soft=(g_voids[i].side>0 ? bullVoidSoft : bearVoidSoft);
         const color edge=(g_voids[i].side>0 ? InpBullColor : InpBearColor);
         const bool tooSmall=ZoneTooSmall(g_voids[i].top,g_voids[i].bottom,atrNow);
         const bool filled=(!tooSmall && ZoneFillAllowed(g_voids[i].top,g_voids[i].bottom,atrNow));
         if(g_voids[i].upperActive)
           {
            if(!tooSmall)
               CreateZoneBox(base+"_U",left,g_voids[i].top,boxRight,g_voids[i].ce,strong,edge,filled);
            if(nearest)
               CreateTrendObject(base+"_UH",left,g_voids[i].top,lastClosedTime,g_voids[i].top,edge,STYLE_SOLID,1,true);
           }
         if(g_voids[i].lowerActive)
           {
            if(!tooSmall)
               CreateZoneBox(base+"_L",left,g_voids[i].ce,boxRight,g_voids[i].bottom,soft,edge,filled);
            if(nearest)
               CreateTrendObject(base+"_LH",left,g_voids[i].bottom,lastClosedTime,g_voids[i].bottom,edge,STYLE_SOLID,1,true);
           }
        }
      // Draw CE only while a matching half is still alive. Both-halves-dead
      // already removed the midline; this filter is belt-and-suspenders.
      for(int i=0;i<ArraySize(g_voidMids);i++)
        {
         bool living=false;
         for(int v=0;v<ArraySize(g_voids);v++)
           {
            if(g_voids[v].eventIndex==g_voidMids[i].eventIndex
               && (g_voids[v].upperActive || g_voids[v].lowerActive))
              {
               living=true;
               break;
              }
           }
         if(!living)
            continue;
         const int midStart=ClampBarIndex(g_voidMids[i].startIndex,g_lastClosedIndex);
         const bool nearestMid=(g_voidMids[i].eventIndex==newestVoidEvent);
         const datetime midRight=(nearestMid ? lastClosedTime : BarRightTime(time,ratesTotal,
                                 MathMax(midStart,ClampBarIndex(g_voidMids[i].eventIndex,g_lastClosedIndex))));
         const string name=g_prefix+"DRAW_VOID_MID_"+IntegerToString(i);
         CreateTrendObject(name,time[midStart],g_voidMids[i].ce,midRight,g_voidMids[i].ce,
                           BlendColor((g_voidMids[i].side>0 ? InpBullColor : InpBearColor),background,0.65),
                           STYLE_DOT,1,nearestMid);
        }
     }

   if(InpShowTrail && IsValue(ExtTrailHigh[g_lastClosedIndex]) && IsValue(ExtTrailLow[g_lastClosedIndex]))
     {
      int highStart=(g_lastClosedIndex<ArraySize(g_trailHighOrigin) ? g_trailHighOrigin[g_lastClosedIndex] : g_lastClosedIndex);
      int lowStart=(g_lastClosedIndex<ArraySize(g_trailLowOrigin) ? g_trailLowOrigin[g_lastClosedIndex] : g_lastClosedIndex);
      const double highLevel=ExtTrailHigh[g_lastClosedIndex];
      const double lowLevel=ExtTrailLow[g_lastClosedIndex];
      highStart=MathMax(0,MathMin(g_lastClosedIndex,highStart));
      lowStart=MathMax(0,MathMin(g_lastClosedIndex,lowStart));
      CreateTrendObject(g_prefix+"DRAW_TRAIL_H",time[highStart],highLevel,lastClosedTime,highLevel,InpBearColor,STYLE_DOT,1,true);
      CreateTrendObject(g_prefix+"DRAW_TRAIL_L",time[lowStart],lowLevel,lastClosedTime,lowLevel,InpBullColor,STYLE_DOT,1,true);
      const int trailBias=(int)MathRound(ExtBias[g_lastClosedIndex]);
      CreateTextObject(g_prefix+"DRAW_TRAIL_HL",lastClosedTime,highLevel,
                       (trailBias<0 ? "Protected H" : "Soft H"),InpBearColor,ANCHOR_RIGHT,8);
      CreateTextObject(g_prefix+"DRAW_TRAIL_LL",lastClosedTime,lowLevel,
                       (trailBias>0 ? "Protected L" : "Soft L"),InpBullColor,ANCHOR_RIGHT,8);
     }

   UpdateHud(g_lastClosedIndex);
   if(HtfInsetAllowed())
      DeleteObjectsByPrefix(g_prefix+"HTF_");
   else
      UpdateHtfPanel();
   UpdateHtfBreakLevel();
   if(HtfInsetAllowed())
     {
      ClipDrawObjectsUnderInset();
      EnsureHtfInset();
     }
   ChartRedraw();
  }

//+------------------------------------------------------------------+
//| Closed-bar alert helpers.                                        |
//+------------------------------------------------------------------+
void EmitTbAlert(const string message)
  {
   Print(message);
   if(InpEnablePopupAlert)
      Alert(message);
   if(InpEnablePushNotification)
      SendNotification(message);
  }

void ProcessClosedBarAlerts(const datetime &time[])
  {
   if(!InpEnableAlerts || g_lastClosedIndex<0)
      return;
   if(PeriodSeconds(_Period)==PeriodSeconds(HtfResolvedPeriod()) && InpShowHtfInset)
     {
      long isObj=0;
      if(ChartGetInteger(ChartID(),CHART_IS_OBJECT,0,isObj) && isObj!=0)
         return;
     }
   const int index=g_lastClosedIndex;
   if(time[index]==g_lastAlertedClosedBar)
      return;
   g_lastAlertedClosedBar=time[index];

   const string prefix="TB SMC 2026 "+_Symbol+" "+EnumToString((ENUM_TIMEFRAMES)_Period)+": ";
   if(ExtBosUp[index]>0.5) EmitTbAlert(prefix+"bullish BOS");
   if(ExtMssUp[index]>0.5) EmitTbAlert(prefix+"bullish MSS");
   if(ExtBosDown[index]>0.5) EmitTbAlert(prefix+"bearish BOS");
   if(ExtMssDown[index]>0.5) EmitTbAlert(prefix+"bearish MSS");
   if(ExtSweepHigh[index]>0.5) EmitTbAlert(prefix+"high liquidity sweep");
   if(ExtSweepLow[index]>0.5) EmitTbAlert(prefix+"low liquidity sweep");
   if(ExtBullVoid[index]>0.5) EmitTbAlert(prefix+"bullish price void");
   if(ExtBearVoid[index]>0.5) EmitTbAlert(prefix+"bearish price void");
  }

//+------------------------------------------------------------------+
//| Input validation.                                                |
//+------------------------------------------------------------------+
bool ValidateInputs()
  {
   if(InpEngineProfile!=TB_PROFILE_TV_2026_2_0 && InpEngineProfile!=TB_PROFILE_EA_CUSTOM)
      return(false);
   if(InpEngineProfile==TB_PROFILE_TV_2026_2_0)
      return(true);
   return(InpEaSwingLength>=2 && InpEaSwingLength<=50
          && InpEaDisplacementAtr>=0.10 && InpEaDisplacementAtr<=5.00
          && InpEaCellsKept>=1 && InpEaCellsKept<=32
          && InpEaVoidsKept>=1 && InpEaVoidsKept<=32
          && InpEaSweepReclaimAtr>=0.0 && InpEaSweepReclaimAtr<=1.00
          && InpEaMinimumVoidAtr>=0.0 && InpEaMinimumVoidAtr<=5.00
          && InpEaMinimumCellAtr>=0.0 && InpEaMinimumCellAtr<=10.00
          && InpEaMaximumCellAgeBars>=0 && InpEaMaximumCellAgeBars<=100000
          && InpEaMaximumVoidAgeBars>=0 && InpEaMaximumVoidAgeBars<=100000
          && (!InpEaEnableCells || InpEaEnableStructure)
          && (InpEaVoidRetention==TB_VOID_TV_HALF_PARITY
              || InpEaVoidRetention==TB_VOID_EA_WHOLE_ZONE));
  }

//+------------------------------------------------------------------+
//| Indicator initialization.                                        |
//+------------------------------------------------------------------+
int OnInit()
  {
   ResolveEngineParameters();
   if(!ValidateInputs())
     {
      Print("TB SMC 2026 invalid inputs.");
      return(INIT_PARAMETERS_INCORRECT);
     }

   SetIndexBuffer(0,ExtSweepHighMarker,INDICATOR_DATA);
   SetIndexBuffer(1,ExtSweepLowMarker,INDICATOR_DATA);
   SetIndexBuffer(2,ExtBias,INDICATOR_DATA);
   SetIndexBuffer(3,ExtBosUp,INDICATOR_DATA);
   SetIndexBuffer(4,ExtMssUp,INDICATOR_DATA);
   SetIndexBuffer(5,ExtBosDown,INDICATOR_DATA);
   SetIndexBuffer(6,ExtMssDown,INDICATOR_DATA);
   SetIndexBuffer(7,ExtSweepHigh,INDICATOR_DATA);
   SetIndexBuffer(8,ExtSweepLow,INDICATOR_DATA);
   SetIndexBuffer(9,ExtBullVoid,INDICATOR_DATA);
   SetIndexBuffer(10,ExtBearVoid,INDICATOR_DATA);
   SetIndexBuffer(11,ExtImpulseUp,INDICATOR_DATA);
   SetIndexBuffer(12,ExtImpulseDown,INDICATOR_DATA);
   SetIndexBuffer(13,ExtSwingHigh,INDICATOR_DATA);
   SetIndexBuffer(14,ExtSwingLow,INDICATOR_DATA);
   SetIndexBuffer(15,ExtSwingHighLive,INDICATOR_DATA);
   SetIndexBuffer(16,ExtSwingLowLive,INDICATOR_DATA);
   SetIndexBuffer(17,ExtTrailHigh,INDICATOR_DATA);
   SetIndexBuffer(18,ExtTrailLow,INDICATOR_DATA);
   SetIndexBuffer(19,ExtCellTop,INDICATOR_DATA);
   SetIndexBuffer(20,ExtCellBottom,INDICATOR_DATA);
   SetIndexBuffer(21,ExtCellSide,INDICATOR_DATA);
   SetIndexBuffer(22,ExtVoidTop,INDICATOR_DATA);
   SetIndexBuffer(23,ExtVoidBottom,INDICATOR_DATA);
   SetIndexBuffer(24,ExtVoidCe,INDICATOR_DATA);
   SetIndexBuffer(25,ExtVoidSide,INDICATOR_DATA);
   SetIndexBuffer(26,ExtClosedBarValid,INDICATOR_DATA);
   SetIndexBuffer(27,ExtStructureEvent,INDICATOR_DATA);
   SetIndexBuffer(28,ExtAtr,INDICATOR_DATA);
   SetIndexBuffer(29,ExtBreakLevel,INDICATOR_DATA);
   SetIndexBuffer(30,ExtVoidUpperActive,INDICATOR_DATA);
   SetIndexBuffer(31,ExtVoidLowerActive,INDICATOR_DATA);
   SetIndexBuffer(32,ExtVoidActiveTop,INDICATOR_DATA);
   SetIndexBuffer(33,ExtVoidActiveBottom,INDICATOR_DATA);
   SetIndexBuffer(34,ExtCellAgeBars,INDICATOR_DATA);
   SetIndexBuffer(35,ExtVoidAgeBars,INDICATOR_DATA);
   SetIndexBuffer(36,ExtDisplacementRatio,INDICATOR_DATA);
   SetIndexBuffer(37,ExtVoidSizeAtr,INDICATOR_DATA);
   SetIndexBuffer(38,ExtCellSizeAtr,INDICATOR_DATA);
   SetIndexBuffer(39,ExtEaReadyMask,INDICATOR_DATA);
   SetIndexBuffer(40,ExtEffectiveSwingLength,INDICATOR_DATA);
   SetIndexBuffer(41,ExtEffectiveDisplacementAtr,INDICATOR_DATA);
   SetIndexBuffer(42,ExtEffectiveSweepReclaimAtr,INDICATOR_DATA);
   SetIndexBuffer(43,ExtContractVersion,INDICATOR_DATA);
   SetIndexBuffer(44,ExtTrueRange,INDICATOR_CALCULATIONS);

   ArraySetAsSeries(ExtSweepHighMarker,false); ArraySetAsSeries(ExtSweepLowMarker,false);
   ArraySetAsSeries(ExtBias,false); ArraySetAsSeries(ExtBosUp,false); ArraySetAsSeries(ExtMssUp,false);
   ArraySetAsSeries(ExtBosDown,false); ArraySetAsSeries(ExtMssDown,false);
   ArraySetAsSeries(ExtSweepHigh,false); ArraySetAsSeries(ExtSweepLow,false);
   ArraySetAsSeries(ExtBullVoid,false); ArraySetAsSeries(ExtBearVoid,false);
   ArraySetAsSeries(ExtImpulseUp,false); ArraySetAsSeries(ExtImpulseDown,false);
   ArraySetAsSeries(ExtSwingHigh,false); ArraySetAsSeries(ExtSwingLow,false);
   ArraySetAsSeries(ExtSwingHighLive,false); ArraySetAsSeries(ExtSwingLowLive,false);
   ArraySetAsSeries(ExtTrailHigh,false); ArraySetAsSeries(ExtTrailLow,false);
   ArraySetAsSeries(ExtCellTop,false); ArraySetAsSeries(ExtCellBottom,false); ArraySetAsSeries(ExtCellSide,false);
   ArraySetAsSeries(ExtVoidTop,false); ArraySetAsSeries(ExtVoidBottom,false); ArraySetAsSeries(ExtVoidCe,false); ArraySetAsSeries(ExtVoidSide,false);
   ArraySetAsSeries(ExtClosedBarValid,false); ArraySetAsSeries(ExtStructureEvent,false);
   ArraySetAsSeries(ExtAtr,false); ArraySetAsSeries(ExtBreakLevel,false);
   ArraySetAsSeries(ExtVoidUpperActive,false); ArraySetAsSeries(ExtVoidLowerActive,false);
   ArraySetAsSeries(ExtVoidActiveTop,false); ArraySetAsSeries(ExtVoidActiveBottom,false);
   ArraySetAsSeries(ExtCellAgeBars,false); ArraySetAsSeries(ExtVoidAgeBars,false);
   ArraySetAsSeries(ExtDisplacementRatio,false); ArraySetAsSeries(ExtVoidSizeAtr,false);
   ArraySetAsSeries(ExtCellSizeAtr,false); ArraySetAsSeries(ExtEaReadyMask,false);
   ArraySetAsSeries(ExtEffectiveSwingLength,false); ArraySetAsSeries(ExtEffectiveDisplacementAtr,false);
   ArraySetAsSeries(ExtEffectiveSweepReclaimAtr,false); ArraySetAsSeries(ExtContractVersion,false);
   ArraySetAsSeries(ExtTrueRange,false);

   ConfigurePlots();
   const string profile=(InpEngineProfile==TB_PROFILE_TV_2026_2_0 ? "TV" : "EA");
   g_shortName="TB SMC 2026 "+profile+" ("
               +IntegerToString(g_swingLength)+","+DoubleToString(g_displacementAtr,2)+","
               +IntegerToString(g_cellsKept)+","+IntegerToString(g_voidsKept)+","
               +DoubleToString(g_sweepReclaimAtr,2)+",swpLive="
               +(g_sweepsRequireLiveSwing ? "1" : "0")+")";
   IndicatorSetString(INDICATOR_SHORTNAME,g_shortName);
   IndicatorSetInteger(INDICATOR_DIGITS,_Digits);
   g_prefix="TB_SMC_"+StringFormat("%I64d",ChartID())+"_"+_Symbol+"_"+IntegerToString((int)_Period)+"_";
   DeleteObjectsByPrefix(g_prefix);
   g_lastBarTime=0;
   g_firstBarTime=0;
   g_lastAlertedClosedBar=0;
   g_lastClosedIndex=-1;
   g_cachedRates=0;
   ResetEngineState();
   InitHtfHandle();
   Print("TB SMC 2026 init ver=2.42 hud=",InpShowHud," draw=",InpDrawObjects,
         " inset=",InpShowHtfInset," period=",_Period," chart=",ChartID());
   if(HtfInsetAllowed())
      EventSetTimer(1);
   return(INIT_SUCCEEDED);
  }

//+------------------------------------------------------------------+
//| Publish state and quality metrics for one bar.                    |
//| The same routine writes a closed bar or the forming-bar snapshot. |
//| Only a closed bar may set bit 0 or ClosedBarValid.                |
//+------------------------------------------------------------------+
void PublishEngineState(const int index,const bool closed)
  {
   const bool atrValid=IsValue(ExtAtr[index]) && ExtAtr[index]>0.0;
   ExtBias[index]=g_bias;
   ExtSwingHigh[index]=g_swingHigh;
   ExtSwingLow[index]=g_swingLow;
   // Live=0 after any close-through. Pending BROKEN_UNCONFIRMED is not an OB.
   ExtSwingHighLive[index]=(g_swingHighLive ? 1.0 : 0.0);
   ExtSwingLowLive[index]=(g_swingLowLive ? 1.0 : 0.0);
   ExtTrailHigh[index]=g_trailHigh;
   ExtTrailLow[index]=g_trailLow;

   int readyMask=(closed ? TB_READY_CLOSED : 0);
   if(atrValid) readyMask|=TB_READY_ATR;
   if(IsValue(g_swingHigh)) readyMask|=TB_READY_SWING_HIGH;
   if(IsValue(g_swingLow)) readyMask|=TB_READY_SWING_LOW;

   // 19-21 = newest surviving cell, not necessarily the cell of this bar's BOS.
   if(ArraySize(g_cells)>0)
     {
      ExtCellTop[index]=g_cells[0].top;
      ExtCellBottom[index]=g_cells[0].bottom;
      ExtCellSide[index]=g_cells[0].side;
      ExtCellAgeBars[index]=(double)MathMax(index-g_cells[0].eventIndex,0);
      if(atrValid)
         ExtCellSizeAtr[index]=(g_cells[0].top-g_cells[0].bottom)/ExtAtr[index];
      readyMask|=TB_READY_CELL;
     }

   if(ArraySize(g_voids)>0)
     {
      const PriceVoid newest=g_voids[0];
      ExtVoidTop[index]=newest.top;
      ExtVoidBottom[index]=newest.bottom;
      ExtVoidCe[index]=newest.ce;
      ExtVoidSide[index]=newest.side;
      ExtVoidUpperActive[index]=(newest.upperActive ? 1.0 : 0.0);
      ExtVoidLowerActive[index]=(newest.lowerActive ? 1.0 : 0.0);
      ExtVoidActiveTop[index]=(newest.upperActive ? newest.top : newest.ce);
      ExtVoidActiveBottom[index]=(newest.lowerActive ? newest.bottom : newest.ce);
      ExtVoidAgeBars[index]=(double)MathMax(index-newest.eventIndex,0);
      if(atrValid)
         ExtVoidSizeAtr[index]=(newest.top-newest.bottom)/ExtAtr[index];
      readyMask|=TB_READY_VOID;
     }

   ExtEaReadyMask[index]=(double)readyMask;
   const bool swingReady=(g_requireBothSwings
                          ? (IsValue(g_swingHigh) && IsValue(g_swingLow))
                          : (IsValue(g_swingHigh) || IsValue(g_swingLow)));
   ExtClosedBarValid[index]=(closed && atrValid && swingReady ? 1.0 : 0.0);
  }

//+------------------------------------------------------------------+
//| Process one completed candle.                                    |
//| All event buffers are reset by InitializeBufferAt before entry.   |
//+------------------------------------------------------------------+
void ProcessClosedEngineBar(const int index,const double &open[],const double &high[],
                            const double &low[],const double &close[])
  {
   const double snapHigh=g_swingHigh;
   const double snapLow=g_swingLow;
   const bool snapHighLive=g_swingHighLive;
   const bool snapLowLive=g_swingLowLive;
   const int snapHighIndex=g_swingHighIndex;
   const int snapLowIndex=g_swingLowIndex;
   g_previousSwingHigh=snapHigh;
   g_previousSwingLow=snapLow;

   const bool atrValid=IsValue(ExtAtr[index]) && ExtAtr[index]>0.0;
   const double body=MathAbs(close[index]-open[index]);
   if(atrValid)
      ExtDisplacementRatio[index]=body/ExtAtr[index];
   const bool impulseUp=(atrValid && close[index]>open[index] && body>=ExtAtr[index]*g_displacementAtr);
   const bool impulseDown=(atrValid && close[index]<open[index] && body>=ExtAtr[index]*g_displacementAtr);
   // Buffers 11/12: every impulse candle, not the displacement of a BOS bar.
   ExtImpulseUp[index]=(impulseUp ? 1.0 : 0.0);
   ExtImpulseDown[index]=(impulseDown ? 1.0 : 0.0);

   // InpShow* never gates calculation. TV profile already forces enable_* true.
   const bool calculateStructure=g_enableStructure;
   const bool calculateCells=g_enableCells;
   const bool calculateVoids=g_enableVoids;
   const bool calculateSweeps=g_enableSweeps;
   const bool crossUp=(index>0 && IsValue(snapHigh)
                       && close[index]>snapHigh && close[index-1]<=snapHigh);
   const bool crossDown=(index>0 && IsValue(snapLow)
                         && close[index]<snapLow && close[index-1]>=snapLow);

   // Immediate: live + fresh close-through + impulse (unchanged).
   // Deferred: pending BROKEN_UNCONFIRMED + same-direction impulse still
   // beyond the original level. Do not require a new close[i-1] cross.
   bool bullBreak=false;
   double bullBreakLevel=snapHigh;
   int bullBreakOrigin=snapHighIndex;
   bool bearBreak=false;
   double bearBreakLevel=snapLow;
   int bearBreakOrigin=snapLowIndex;

   if(calculateStructure)
     {
      if(snapHighLive && crossUp && impulseUp)
         bullBreak=true;
      else if(g_pendingHighActive && impulseUp && IsValue(g_pendingHighLevel)
              && close[index]>g_pendingHighLevel)
        {
         bullBreak=true;
         bullBreakLevel=g_pendingHighLevel;
         bullBreakOrigin=g_pendingHighOrigin;
        }
      else if(snapHighLive && crossUp)
        {
         g_swingHighLive=false;
         g_pendingHighActive=true;
         g_pendingHighLevel=snapHigh;
         g_pendingHighOrigin=snapHighIndex;
        }
      else if(g_pendingHighActive && IsValue(g_pendingHighLevel)
              && close[index]<=g_pendingHighLevel)
        {
         g_pendingHighActive=false;
         g_pendingHighLevel=EMPTY_VALUE;
         g_pendingHighOrigin=-1;
         g_swingHighLive=true;
        }

      if(snapLowLive && crossDown && impulseDown)
         bearBreak=true;
      else if(g_pendingLowActive && impulseDown && IsValue(g_pendingLowLevel)
              && close[index]<g_pendingLowLevel)
        {
         bearBreak=true;
         bearBreakLevel=g_pendingLowLevel;
         bearBreakOrigin=g_pendingLowOrigin;
        }
      else if(snapLowLive && crossDown)
        {
         g_swingLowLive=false;
         g_pendingLowActive=true;
         g_pendingLowLevel=snapLow;
         g_pendingLowOrigin=snapLowIndex;
        }
      else if(g_pendingLowActive && IsValue(g_pendingLowLevel)
              && close[index]>=g_pendingLowLevel)
        {
         g_pendingLowActive=false;
         g_pendingLowLevel=EMPTY_VALUE;
         g_pendingLowOrigin=-1;
         g_swingLowLive=true;
        }
     }

   if(bullBreak)
     {
      const bool isMss=(g_bias<0);
      ExtMssUp[index]=(isMss ? 1.0 : 0.0);
      ExtBosUp[index]=(isMss ? 0.0 : 1.0);
      ExtStructureEvent[index]=(isMss ? 2.0 : 1.0);
      ExtBreakLevel[index]=bullBreakLevel;
      g_breakOrigin[index]=bullBreakOrigin;
      g_bias=1;
      g_swingHighLive=false;
      g_pendingHighActive=false;
      g_pendingHighLevel=EMPTY_VALUE;
      g_pendingHighOrigin=-1;

      if(calculateCells)
        {
         OriginCell cell;
         cell.bottom=low[index];
         cell.top=high[index];
         cell.startIndex=index;
         cell.eventIndex=index;
         cell.side=1;
         const int lookback=MathMin(TB_ORIGIN_LOOKBACK,index);
         for(int k=1;k<=lookback;k++)
           {
            if(low[index-k]<=cell.bottom)
              {
               cell.bottom=low[index-k];
               cell.top=high[index-k];
               cell.startIndex=index-k;
              }
           }
         const double cellAtr=(atrValid ? (cell.top-cell.bottom)/ExtAtr[index] : 0.0);
         if(g_minimumCellAtr<=0.0 || cellAtr>=g_minimumCellAtr)
            PushCellFront(cell);
        }
     }

   if(bearBreak)
     {
      const bool isMss=(g_bias>0);
      ExtMssDown[index]=(isMss ? 1.0 : 0.0);
      ExtBosDown[index]=(isMss ? 0.0 : 1.0);
      ExtStructureEvent[index]=(isMss ? -2.0 : -1.0);
      ExtBreakLevel[index]=bearBreakLevel;
      g_breakOrigin[index]=bearBreakOrigin;
      g_bias=-1;
      g_swingLowLive=false;
      g_pendingLowActive=false;
      g_pendingLowLevel=EMPTY_VALUE;
      g_pendingLowOrigin=-1;

      if(calculateCells)
        {
         OriginCell cell;
         cell.top=high[index];
         cell.bottom=low[index];
         cell.startIndex=index;
         cell.eventIndex=index;
         cell.side=-1;
         const int lookback=MathMin(TB_ORIGIN_LOOKBACK,index);
         for(int k=1;k<=lookback;k++)
           {
            if(high[index-k]>=cell.top)
              {
               cell.top=high[index-k];
               cell.bottom=low[index-k];
               cell.startIndex=index-k;
              }
           }
         const double cellAtr=(atrValid ? (cell.top-cell.bottom)/ExtAtr[index] : 0.0);
         if(g_minimumCellAtr<=0.0 || cellAtr>=g_minimumCellAtr)
            PushCellFront(cell);
        }
     }

   // Invalidation and optional EA age expiry are closed-bar only. Expiry uses
   // event age rather than rectangle start, so optimizer values are stable
   // across cells whose origin candle is several bars before the break.
   for(int i=ArraySize(g_cells)-1;i>=0;i--)
     {
      const bool invalid=((g_cells[i].side>0 && low[index]<g_cells[i].bottom)
                          || (g_cells[i].side<0 && high[index]>g_cells[i].top));
      const bool expired=(g_maximumCellAgeBars>0
                          && index-g_cells[i].eventIndex>g_maximumCellAgeBars);
      if(invalid || expired)
         RemoveCell(i);
     }

   const bool bullVoidGeometry=(calculateVoids && index>=2
                                && low[index]>high[index-2] && close[index-1]>high[index-2]);
   const bool bearVoidGeometry=(calculateVoids && index>=2
                                && high[index]<low[index-2] && close[index-1]<low[index-2]);
   const double bullGap=(bullVoidGeometry ? low[index]-high[index-2] : 0.0);
   const double bearGap=(bearVoidGeometry ? low[index-2]-high[index] : 0.0);
   const bool bullVoid=(bullVoidGeometry && (g_minimumVoidAtr<=0.0
                                             || (atrValid && bullGap/ExtAtr[index]>=g_minimumVoidAtr)));
   const bool bearVoid=(bearVoidGeometry && (g_minimumVoidAtr<=0.0
                                             || (atrValid && bearGap/ExtAtr[index]>=g_minimumVoidAtr)));
   ExtBullVoid[index]=(bullVoid ? 1.0 : 0.0);
   ExtBearVoid[index]=(bearVoid ? 1.0 : 0.0);

   if(bullVoid)
     {
      PriceVoid zone;
      zone.startIndex=index-2;
      zone.eventIndex=index;
      zone.top=low[index];
      zone.bottom=high[index-2];
      zone.ce=0.5*(zone.top+zone.bottom);
      zone.side=1;
      zone.upperActive=true;
      zone.lowerActive=true;
      PushVoidFront(zone);
     }
   if(bearVoid)
     {
      PriceVoid zone;
      zone.startIndex=index-2;
      zone.eventIndex=index;
      zone.top=low[index-2];
      zone.bottom=high[index];
      zone.ce=0.5*(zone.top+zone.bottom);
      zone.side=-1;
      zone.upperActive=true;
      zone.lowerActive=true;
      PushVoidFront(zone);
     }

   // Each half is filled independently by a candle that spans the half.
   // Touching CE is not a fill. Birth bar cannot self-fill. When both
   // halves are dead the CE midline is deleted with the zone.
   for(int i=ArraySize(g_voids)-1;i>=0;i--)
     {
      if(g_voids[i].eventIndex==index)
         continue;
      if(g_voids[i].upperActive && low[index]<g_voids[i].ce && high[index]>g_voids[i].top)
         g_voids[i].upperActive=false;
      if(g_voids[i].lowerActive && low[index]<g_voids[i].bottom && high[index]>g_voids[i].ce)
         g_voids[i].lowerActive=false;
      const bool expired=(g_maximumVoidAgeBars>0
                          && index-g_voids[i].eventIndex>g_maximumVoidAgeBars);
      if(expired)
         RemoveVoid(i,true);
      else if(!g_voids[i].upperActive && !g_voids[i].lowerActive)
         RemoveVoid(i,true);
     }

   // Sweep uses the same snapshot swing as BOS. Close-through+impulse vs
   // wick+reclaim are mutually exclusive. Default requires a live swing:
   // a wick back to a level already consumed by BOS is not a real sweep.
   const bool highSweepState=(!g_sweepsRequireLiveSwing || snapHighLive);
   const bool lowSweepState=(!g_sweepsRequireLiveSwing || snapLowLive);
   const bool sweepHigh=(calculateSweeps && IsValue(snapHigh) && atrValid && highSweepState
                         && high[index]>snapHigh
                         && close[index]<snapHigh-ExtAtr[index]*g_sweepReclaimAtr);
   const bool sweepLow=(calculateSweeps && IsValue(snapLow) && atrValid && lowSweepState
                        && low[index]<snapLow
                        && close[index]>snapLow+ExtAtr[index]*g_sweepReclaimAtr);
   ExtSweepHigh[index]=(sweepHigh ? 1.0 : 0.0);
   ExtSweepLow[index]=(sweepLow ? 1.0 : 0.0);
   if(sweepHigh)
      ExtSweepHighMarker[index]=high[index]+ExtAtr[index]*0.12;
   if(sweepLow)
      ExtSweepLowMarker[index]=low[index]-ExtAtr[index]*0.12;

   double pivotValue=EMPTY_VALUE;
   int pivotIndex=-1;
   if(IsPivotHigh(index,high,pivotValue,pivotIndex))
     {
      g_swingHigh=pivotValue;
      g_swingHighIndex=pivotIndex;
      g_swingHighLive=true;
      g_trailHigh=pivotValue;
      g_trailHighIndex=pivotIndex;
      g_pendingHighActive=false;
      g_pendingHighLevel=EMPTY_VALUE;
      g_pendingHighOrigin=-1;
     }
   if(IsPivotLow(index,low,pivotValue,pivotIndex))
     {
      g_swingLow=pivotValue;
      g_swingLowIndex=pivotIndex;
      g_swingLowLive=true;
      g_trailLow=pivotValue;
      g_trailLowIndex=pivotIndex;
      g_pendingLowActive=false;
      g_pendingLowLevel=EMPTY_VALUE;
      g_pendingLowOrigin=-1;
     }

   // Pine updates the origin on equal extrema after math.max/min. >= and <=
   // are therefore intentional parity fixes, not a numerical tolerance hack.
   if(!IsValue(g_trailHigh) || high[index]>=g_trailHigh)
     {
      g_trailHigh=high[index];
      g_trailHighIndex=index;
     }
   if(!IsValue(g_trailLow) || low[index]<=g_trailLow)
     {
      g_trailLow=low[index];
      g_trailLowIndex=index;
     }

   g_trailHighOrigin[index]=g_trailHighIndex;
   g_trailLowOrigin[index]=g_trailLowIndex;
   PublishEngineState(index,true);
  }

//+------------------------------------------------------------------+
//| Deterministic initial replay + incremental closed-bar updates.    |
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
   const int required=MathMax(TB_ATR_LENGTH,g_swingLength*2+1);
   if(rates_total<required+1)
      return(0);

   ArraySetAsSeries(time,false); ArraySetAsSeries(open,false); ArraySetAsSeries(high,false);
   ArraySetAsSeries(low,false); ArraySetAsSeries(close,false);

   // Same-bar ticks never change EA buffers or closed structural state. The
   // rates_total and oldest-time checks deliberately prevent this fast path
   // when MT5 backfills/replaces history during the current candle.
   const bool historyChanged=(g_firstBarTime!=0 && g_firstBarTime!=time[0]);
   if(prev_calculated>0 && prev_calculated==rates_total && !historyChanged
      && g_lastBarTime==time[rates_total-1])
     {
      UpdateHtfClock();
      return(rates_total);
     }
   g_lastBarTime=time[rates_total-1];
   g_firstBarTime=time[0];
   g_lastClosedIndex=rates_total-2;

   const bool fullRebuild=(prev_calculated<=0 || historyChanged || g_lastProcessedClosedIndex<0
                           || g_lastProcessedClosedIndex>g_lastClosedIndex);
   int startIndex=0;
   if(fullRebuild)
     {
      InitializeBuffers(rates_total);
      ResetEngineState();
      ArrayResize(g_breakOrigin,rates_total);
      ArrayResize(g_trailHighOrigin,rates_total);
      ArrayResize(g_trailLowOrigin,rates_total);
      ArrayInitialize(g_breakOrigin,-1);
      ArrayInitialize(g_trailHighOrigin,-1);
      ArrayInitialize(g_trailLowOrigin,-1);
     }
   else
     {
      startIndex=g_lastProcessedClosedIndex+1;
      const int oldBreakSize=ArraySize(g_breakOrigin);
      const int oldHighSize=ArraySize(g_trailHighOrigin);
      const int oldLowSize=ArraySize(g_trailLowOrigin);
      ArrayResize(g_breakOrigin,rates_total);
      ArrayResize(g_trailHighOrigin,rates_total);
      ArrayResize(g_trailLowOrigin,rates_total);
      for(int i=oldBreakSize;i<rates_total;i++) g_breakOrigin[i]=-1;
      for(int i=oldHighSize;i<rates_total;i++) g_trailHighOrigin[i]=-1;
      for(int i=oldLowSize;i<rates_total;i++) g_trailLowOrigin[i]=-1;
     }

   for(int index=startIndex;index<=g_lastClosedIndex;index++)
     {
      InitializeBufferAt(index);
      ExtTrueRange[index]=(index==0 ? high[index]-low[index]
                              : MathMax(high[index]-low[index],
                                        MathMax(MathAbs(high[index]-close[index-1]),
                                                MathAbs(low[index]-close[index-1]))));
      ExtAtr[index]=AtrAt(index);
      ProcessClosedEngineBar(index,open,high,low,close);
     }
   g_lastProcessedClosedIndex=g_lastClosedIndex;

   // Publish a state-only forming bar. Event flags and ClosedBarValid stay 0.
   const int forming=rates_total-1;
   InitializeBufferAt(forming);
   ExtTrueRange[forming]=MathMax(high[forming]-low[forming],
                                MathMax(MathAbs(high[forming]-close[forming-1]),
                                        MathAbs(low[forming]-close[forming-1])));
   ExtAtr[forming]=AtrAt(forming);
   PublishEngineState(forming,false);

   ArrayResize(g_cachedTime,rates_total);
   for(int i=0;i<rates_total;i++)
      g_cachedTime[i]=time[i];
   g_cachedRates=rates_total;

   const bool renderObjects=(!(bool)MQLInfoInteger(MQL_TESTER) || (bool)MQLInfoInteger(MQL_VISUAL_MODE));
   if(renderObjects && IsVisualInstanceOnChart())
     {
      RefreshHtfSnapshot(fullRebuild);
      RebuildVisuals(rates_total,time);
      if(fullRebuild)
         g_lastAlertedClosedBar=time[g_lastClosedIndex];
      else
         ProcessClosedBarAlerts(time);
     }
   else
     {
      DeleteObjectsByPrefix(g_prefix);
     }
   return(rates_total);
  }

//+------------------------------------------------------------------+
//| Keep the HUD/colors aligned after chart changes.                  |
//+------------------------------------------------------------------+
void OnChartEvent(const int id,const long &lparam,const double &dparam,const string &sparam)
  {
   if(id==CHARTEVENT_CHART_CHANGE && HtfInsetAllowed())
      EnsureHtfInset();
   if(id!=CHARTEVENT_CHART_CHANGE || g_lastClosedIndex<0 || g_cachedRates<=0)
      return;
   ConfigurePlots();
   if(IsVisualInstanceOnChart())
      RebuildVisuals(g_cachedRates,g_cachedTime);
   else
      DeleteObjectsByPrefix(g_prefix);
   ChartRedraw();
  }

//+------------------------------------------------------------------+
//| Remove only objects owned by this indicator instance.             |
//+------------------------------------------------------------------+
void OnTimer()
  {
   if(!HtfInsetAllowed())
     {
      EventKillTimer();
      return;
     }
   EnsureHtfInset();
   ClipDrawObjectsUnderInset();
   if(g_htfInsetAttached)
      EventKillTimer();
  }

void OnDeinit(const int reason)
  {
   EventKillTimer();
   ReleaseHtfInset();
   ReleaseHtfHandle();
   DeleteObjectsByPrefix(g_prefix);
  }
//+------------------------------------------------------------------+
