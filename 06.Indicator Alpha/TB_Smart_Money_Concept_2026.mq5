//+------------------------------------------------------------------+
//|                    TB_Smart_Money_Concept_2026.mq5               |
//| TB Smart Money Concept 2026 - single-file MT5 port.              |
//| Original Pine Script v6 by TBalgo, version 2026.2.0.             |
//| Licensed under Mozilla Public License 2.0.                       |
//| Source: https://www.tradingview.com/script/IM2GxnOK-             |
//|         TB-Smart-Money-Concept-2026/                             |
//|                                                                  |
//| Public iCustom buffer contract v3 (consume shift >= 1):          |
//|   0/1   Sweep High/Low marker price                              |
//|   2     Bias: -1 bear, 0 flat, +1 bull                           |
//|   3/4   BOS Up / MSS Up flags                                    |
//|   5/6   BOS Down / MSS Down flags                                |
//|   7/8   Sweep High / Sweep Low flags                             |
//|   9/10  Bull Void / Bear Void flags                              |
//|   11/12 Bull / Bear displacement flags                           |
//|   13/14 Latest confirmed swing high / low                        |
//|   15/16 Swing high / low live flags                              |
//|   17/18 Active range trail high / low                            |
//|   19/20/21 Newest active Origin Cell top/bottom/side             |
//|   22/23/24/25 Newest active Void top/bottom/CE/side              |
//|   26    ClosedBarValid (closed + ATR + required swing state)      |
//|   27    Structure event: +1 BOS up, +2 MSS up, -1 BOS down,      |
//|         -2 MSS down                                              |
//|   28    ATR(14)                                                  |
//|   29    Broken structure level on an event bar                   |
//|   30/31 Newest Void upper/lower half active flags                |
//|   32/33 Newest Void active top/bottom after partial fill         |
//|   34/35 Newest Cell/Void age in completed bars                   |
//|   36    Displacement ratio = candle body / ATR(14)               |
//|   37/38 Newest Void/Cell height in ATR units                     |
//|   39    EA ready-mask (bits documented below)                    |
//|   40/41/42 Effective Swing/Displacement/Sweep parameters         |
//|   43    Buffer contract version (= 3.0)                           |
//|   44/45 Nearest unconsumed liquidity high above / low below      |
//|   46/47 Liquidity high / low available flags                     |
//|                                                                  |
//| Safety extension over the visual Pine script: all event buffers  |
//| are closed-bar only. The forming bar carries no trade event.     |
//| Raw events are structural facts, NOT entry signals. An EA must   |
//| require buffer 26 == 1, read shift >= 1, and apply its own risk,  |
//| execution, session, spread and portfolio controls.               |
//|                                                                  |
//| EA integration example (all values after the file name are the   |
//| engine inputs below, in their declared order):                    |
//|   handle=iCustom(_Symbol,_Period,                                 |
//|      "TB_Smart_Money_Concept_2026",                              |
//|      1,5,0.45,3,4,0.05,0.10,0.20,120,80,                        |
//|      true,true,true,true,true,true,1);                            |
//|   CopyBuffer(handle,26,1,1,ready); // NEVER request shift 0       |
//| Profile 1 = EA_CUSTOM; final 1 = whole-zone void retention.       |
//| An EA should also verify buffer 43 >= 2.0 before trading.         |
//+------------------------------------------------------------------+
#property copyright   "TBalgo; MQL5 port for workspace owner"
#property link        "https://www.tradingview.com/script/IM2GxnOK-TB-Smart-Money-Concept-2026/"
#property version     "3.00"
#property description "Closed-bar SMC structure map: BOS/MSS, origin cells, voids/CE and sweeps"
#property description "Single-file Pine 2026.2.0 port with a fail-closed EA buffer contract"

#property indicator_chart_window
#property indicator_buffers 49
#property indicator_plots   48

//--- Parameter profile controls whether the engine is frozen to the public
//--- Pine defaults or accepts a separately optimizable EA parameter surface.
//--- EA_CUSTOM values are intentionally NOT labelled profitable/optimal here:
//--- optimization belongs to a preregistered per-symbol/timeframe EA backtest.
enum ENUM_TB_ENGINE_PROFILE
  {
   TB_PROFILE_TV_2026_2_0=0, // Exact public Pine defaults; EA custom filters disabled
   TB_PROFILE_EA_CUSTOM=1    // Use every InpEa* value below
  };

//--- FVG retention is independently controllable in EA_CUSTOM mode.
enum ENUM_TB_VOID_RETENTION
  {
   TB_VOID_TV_HALF_PARITY=0, // Cap individual half-boxes like Pine voidBox
   TB_VOID_EA_WHOLE_ZONE=1   // Keep/remove both halves as one coherent EA zone
  };

//--- EA engine inputs are deliberately first in the input list. This keeps
//--- the iCustom call stable and lets an EA pass only engine values while all
//--- later chart/alert inputs use defaults.
//--- A versioned string is placed first because custom enum identity is not
//--- portable across separately compiled EX5 modules. Empty preserves the
//--- original chart-facing inputs below.
input string InpEaContract=""; // RSF1|profile|swing|...|retention
input group "EA Engine Contract - iCustom inputs first"
input ENUM_TB_ENGINE_PROFILE InpEngineProfile=TB_PROFILE_TV_2026_2_0; // TV parity or EA custom
input int    InpEaSwingLength=5;                 // EA_CUSTOM: pivot left/right bars (2..50)
input double InpEaDisplacementAtr=0.45;          // EA_CUSTOM: min candle body / ATR (0.10..5.00)
input int    InpEaCellsKept=3;                   // EA_CUSTOM: newest Origin Cells retained (1..32)
input int    InpEaVoidsKept=4;                   // EA_CUSTOM: FVG retention budget (1..32)
input double InpEaSweepReclaimAtr=0.05;          // EA_CUSTOM: close-back distance / ATR (0..1)
input double InpEaMinimumVoidAtr=0.0;             // EA_CUSTOM: reject FVG height below ATR ratio (0=off)
input double InpEaMinimumCellAtr=0.0;             // EA_CUSTOM: reject Origin Cell height below ATR ratio (0=off)
input int    InpEaMaximumCellAgeBars=0;           // EA_CUSTOM: expire Cell after N closed bars (0=off)
input int    InpEaMaximumVoidAgeBars=0;           // EA_CUSTOM: expire FVG after N closed bars (0=off)
input bool   InpEaSweepsRequireLiveSwing=false;   // EA_CUSTOM: suppress repeated sweeps after structure consumed
input bool   InpEaRequireBothSwings=true;         // EA_CUSTOM: buffer 26 requires both confirmed swing sides
input bool   InpEaEnableStructure=true;            // EA_CUSTOM: calculate BOS/MSS independently of display
input bool   InpEaEnableCells=true;                // EA_CUSTOM: Origin Cells; requires Structure=true
input bool   InpEaEnableVoids=true;                // EA_CUSTOM: calculate FVG/CE independently of display
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
input color InpBullColor=C'45,212,191';       // Bull
input color InpBearColor=C'251,113,133';      // Bear
input color InpAccentColor=C'129,140,248';    // Accent
input color InpMuteColor=C'100,116,139';      // Mute
input bool  InpFocusMode=true;                // Focus Mode (latest structure only)

//--- Modules
input group "TB SMC 2026 - Map"
input bool InpShowStructure=true;             // Structure (BOS / MSS)
input bool InpShowCells=true;                 // Origin Cells
input bool InpShowVoids=true;                 // Price Voids + CE
input bool InpShowSweeps=true;                // Liquidity Sweeps
input bool InpShowTrail=true;                 // Active Range Extremes
input bool InpShowHud=true;                   // Bias HUD

//--- Closed-bar alerts.
input group "Closed-Bar Alerts"
input bool InpEnableAlerts=true;              // Enable alerts
input bool InpEnablePopupAlert=true;          // MT5 popup/sound
input bool InpEnablePushNotification=false;   // Mobile push

const string TB_VERSION="2026.2.0";
const double TB_CONTRACT_VERSION=3.0;
const int    TB_ATR_LENGTH=14;
const int    TB_ORIGIN_LOOKBACK=8;
const int    TB_MAX_STRUCTURE_OBJECTS=150;
const int    TB_MAX_LIQUIDITY_LEVELS=64;

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

//--- EA contract v3 buffers 44..47. These are a causal liquidity map,
//--- not hindsight labels: pivots enter only after right-side confirmation
//--- and leave only after a completed candle closes through them.
double ExtLiquidityHigh[];
double ExtLiquidityLow[];
double ExtLiquidityHighLive[];
double ExtLiquidityLowLive[];

//--- Internal deterministic calculation buffer 48.
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

//--- Pine stores CE midlines separately from half-boxes. Keeping a separate
//--- midline array reproduces that lifecycle in TV parity mode, including a
//--- CE line that can outlive filled halves until the independent cap trims it.
struct VoidMidline
  {
   int      startIndex;
   int      eventIndex;
   double   ce;
   int      side;
  };

struct SwingLiquidity
  {
   int      pivotIndex;
   double   price;
  };

OriginCell g_cells[];
PriceVoid  g_voids[];
VoidMidline g_voidMids[];
SwingLiquidity g_highLiquidity[];
SwingLiquidity g_lowLiquidity[];
int        g_breakOrigin[];
int        g_trailHighOrigin[];
int        g_trailLowOrigin[];

string   g_prefix="";
datetime g_lastBarTime=0;
datetime g_firstBarTime=0;
datetime g_lastAlertedClosedBar=0;
int      g_lastClosedIndex=-1;

//--- Resolved engine parameters. TV profile writes canonical Pine values;
//--- EA_CUSTOM copies the InpEa* inputs after fail-closed validation.
int    g_engineProfile=TB_PROFILE_TV_2026_2_0;
int    g_swingLength=5;
double g_displacementAtr=0.45;
int    g_cellsKept=3;
int    g_voidsKept=4;
double g_sweepReclaimAtr=0.05;
double g_minimumVoidAtr=0.0;
double g_minimumCellAtr=0.0;
int    g_maximumCellAgeBars=0;
int    g_maximumVoidAgeBars=0;
bool   g_sweepsRequireLiveSwing=false;
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

datetime FutureTime(const datetime base,const int bars)
  {
   return(base+(datetime)(MathMax(PeriodSeconds(_Period),1)*bars));
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
bool ResolveEngineParameters()
  {
   if(StringLen(InpEaContract)>0)
     {
      string p[];
      if(StringSplit(InpEaContract,StringGetCharacter("|",0),p)!=18 || p[0]!="RSF1")
         return(false);
      for(int i=11;i<=16;i++)
         if(p[i]!="0" && p[i]!="1") return(false);
      g_engineProfile=(int)StringToInteger(p[1]);
      g_swingLength=(int)StringToInteger(p[2]);
      g_displacementAtr=StringToDouble(p[3]);
      g_cellsKept=(int)StringToInteger(p[4]);
      g_voidsKept=(int)StringToInteger(p[5]);
      g_sweepReclaimAtr=StringToDouble(p[6]);
      g_minimumVoidAtr=StringToDouble(p[7]);
      g_minimumCellAtr=StringToDouble(p[8]);
      g_maximumCellAgeBars=(int)StringToInteger(p[9]);
      g_maximumVoidAgeBars=(int)StringToInteger(p[10]);
      g_sweepsRequireLiveSwing=(p[11]=="1");
      g_requireBothSwings=(p[12]=="1");
      g_enableStructure=(p[13]=="1");
      g_enableCells=(p[14]=="1");
      g_enableVoids=(p[15]=="1");
      g_enableSweeps=(p[16]=="1");
      g_voidRetention=(ENUM_TB_VOID_RETENTION)StringToInteger(p[17]);
      return(g_engineProfile==TB_PROFILE_EA_CUSTOM);
     }

   g_engineProfile=(int)InpEngineProfile;
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
      g_sweepsRequireLiveSwing=false;
      g_requireBothSwings=true;
      // TV profile intentionally couples calculations to the Pine display
      // toggles; these resolved flags are unused in that profile.
      g_enableStructure=true;
      g_enableCells=true;
      g_enableVoids=true;
      g_enableSweeps=true;
      g_voidRetention=TB_VOID_TV_HALF_PARITY;
      return(true);
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
   return(true);
  }

//+------------------------------------------------------------------+
//| Reset persistent engine state before a full deterministic replay. |
//+------------------------------------------------------------------+
void ResetEngineState()
  {
   ArrayResize(g_cells,0);
   ArrayResize(g_voids,0);
   ArrayResize(g_voidMids,0);
   ArrayResize(g_highLiquidity,0);
   ArrayResize(g_lowLiquidity,0);
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
  }

//+------------------------------------------------------------------+
//| Causal swing-liquidity pool helpers.                              |
//| A pivot is known only after the existing left/right confirmation. |
//| Levels are bounded engineering state, never optimized parameters. |
//+------------------------------------------------------------------+
void RemoveLiquidityAt(SwingLiquidity &pool[],const int index)
  {
   const int count=ArraySize(pool);
   if(index<0 || index>=count)
      return;
   for(int i=index;i<count-1;i++)
      pool[i]=pool[i+1];
   ArrayResize(pool,count-1);
  }

void PushLiquidityFront(SwingLiquidity &pool[],const double price,const int pivotIndex)
  {
   if(!IsValue(price) || pivotIndex<0)
      return;
   // Recalculation and equal-price pivots must not create duplicate state.
   for(int i=ArraySize(pool)-1;i>=0;i--)
     {
      if(pool[i].pivotIndex==pivotIndex)
         return;
     }
   const int count=ArraySize(pool);
   ArrayResize(pool,count+1);
   for(int i=count;i>0;i--)
      pool[i]=pool[i-1];
   pool[0].pivotIndex=pivotIndex;
   pool[0].price=price;
   while(ArraySize(pool)>TB_MAX_LIQUIDITY_LEVELS)
      ArrayResize(pool,ArraySize(pool)-1);
  }

void ConsumeClosedLiquidity(const double closedPrice)
  {
   for(int i=ArraySize(g_highLiquidity)-1;i>=0;i--)
     {
      if(closedPrice>g_highLiquidity[i].price)
         RemoveLiquidityAt(g_highLiquidity,i);
     }
   for(int i=ArraySize(g_lowLiquidity)-1;i>=0;i--)
     {
      if(closedPrice<g_lowLiquidity[i].price)
         RemoveLiquidityAt(g_lowLiquidity,i);
     }
  }

double NearestLiquidityHighAbove(const double referencePrice)
  {
   double nearest=EMPTY_VALUE;
   for(int i=0;i<ArraySize(g_highLiquidity);i++)
     {
      const double level=g_highLiquidity[i].price;
      if(level<=referencePrice)
         continue;
      if(!IsValue(nearest) || level<nearest)
         nearest=level;
     }
   return(nearest);
  }

double NearestLiquidityLowBelow(const double referencePrice)
  {
   double nearest=EMPTY_VALUE;
   for(int i=0;i<ArraySize(g_lowLiquidity);i++)
     {
      const double level=g_lowLiquidity[i].price;
      if(level>=referencePrice)
         continue;
      if(!IsValue(nearest) || level>nearest)
         nearest=level;
     }
   return(nearest);
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
               RemoveVoid(i,false); // Pine midline has its own independent cap.
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
   if(pivotIndex<g_swingLength || index<pivotIndex+g_swingLength)
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
   if(pivotIndex<g_swingLength || index<pivotIndex+g_swingLength)
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
   ExtLiquidityHigh[index]=EMPTY_VALUE;
   ExtLiquidityLow[index]=EMPTY_VALUE;
   ExtLiquidityHighLive[index]=0.0;
   ExtLiquidityLowLive[index]=0.0;
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

   const string labels[46]=
     {
      "Bias","BOS Up","MSS Up","BOS Down","MSS Down",
      "Sweep High","Sweep Low","Bull Void","Bear Void",
      "Impulse Up","Impulse Down","Swing High","Swing Low",
      "Swing High Live","Swing Low Live","Trail High","Trail Low",
      "Origin Cell Top","Origin Cell Bottom","Origin Cell Side",
      "Void Top","Void Bottom","Void CE","Void Side",
      "Closed Bar Valid","Structure Event","ATR(14)","Break Level",
      "Void Upper Active","Void Lower Active","Void Active Top","Void Active Bottom",
      "Cell Age Bars","Void Age Bars","Displacement Ratio","Void Size ATR",
      "Cell Size ATR","EA Ready Mask","Effective Swing Length",
      "Effective Displacement ATR","Effective Sweep Reclaim ATR","Contract Version",
      "Nearest Liquidity High","Nearest Liquidity Low",
      "Liquidity High Available","Liquidity Low Available"
     };
   for(int plot=2;plot<48;plot++)
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
//+------------------------------------------------------------------+
void CreateTrendObject(const string name,const datetime time1,const double price1,
                       const datetime time2,const double price2,const color lineColor,
                       const ENUM_LINE_STYLE style,const int width)
  {
   if(!ObjectCreate(0,name,OBJ_TREND,0,time1,price1,time2,price2))
      return;
   ObjectSetInteger(0,name,OBJPROP_RAY_RIGHT,false);
   ObjectSetInteger(0,name,OBJPROP_COLOR,lineColor);
   ObjectSetInteger(0,name,OBJPROP_STYLE,style);
   ObjectSetInteger(0,name,OBJPROP_WIDTH,width);
   ObjectSetInteger(0,name,OBJPROP_SELECTABLE,false);
   ObjectSetInteger(0,name,OBJPROP_HIDDEN,true);
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
   ObjectSetInteger(0,name,OBJPROP_HIDDEN,true);
   ObjectSetInteger(0,name,OBJPROP_ZORDER,3);
  }

void CreateRectangleObject(const string name,const datetime time1,const double top,
                           const datetime time2,const double bottom,const color zoneColor)
  {
   if(!ObjectCreate(0,name,OBJ_RECTANGLE,0,time1,top,time2,bottom))
      return;
   ObjectSetInteger(0,name,OBJPROP_COLOR,zoneColor);
   ObjectSetInteger(0,name,OBJPROP_FILL,true);
   ObjectSetInteger(0,name,OBJPROP_BACK,true);
   ObjectSetInteger(0,name,OBJPROP_SELECTABLE,false);
   ObjectSetInteger(0,name,OBJPROP_HIDDEN,true);
   ObjectSetInteger(0,name,OBJPROP_ZORDER,1);
  }

void EnsureHudLabel(const string suffix,const int x,const int y,const string text,
                    const color textColor,const ENUM_ANCHOR_POINT anchor,const int fontSize)
  {
   const string name=g_prefix+"HUD_"+suffix;
   if(ObjectFind(0,name)<0)
      ObjectCreate(0,name,OBJ_LABEL,0,0,0);
   ObjectSetInteger(0,name,OBJPROP_CORNER,CORNER_RIGHT_UPPER);
   ObjectSetInteger(0,name,OBJPROP_ANCHOR,anchor);
   ObjectSetInteger(0,name,OBJPROP_XDISTANCE,x);
   ObjectSetInteger(0,name,OBJPROP_YDISTANCE,y);
   ObjectSetInteger(0,name,OBJPROP_COLOR,textColor);
   ObjectSetInteger(0,name,OBJPROP_FONTSIZE,fontSize);
   ObjectSetString(0,name,OBJPROP_FONT,"Consolas");
   ObjectSetString(0,name,OBJPROP_TEXT,text);
   ObjectSetInteger(0,name,OBJPROP_SELECTABLE,false);
   ObjectSetInteger(0,name,OBJPROP_HIDDEN,true);
   ObjectSetInteger(0,name,OBJPROP_ZORDER,5);
  }

void UpdateHud(const int index)
  {
   if(!InpShowHud || index<0)
     {
      DeleteObjectsByPrefix(g_prefix+"HUD_");
      return;
     }

   const int panelWidth=226;
   const int panelHeight=82;
   const int margin=10;
   const string background=g_prefix+"HUD_BACKGROUND";
   if(ObjectFind(0,background)<0)
      ObjectCreate(0,background,OBJ_RECTANGLE_LABEL,0,0,0);
   ObjectSetInteger(0,background,OBJPROP_CORNER,CORNER_RIGHT_UPPER);
   ObjectSetInteger(0,background,OBJPROP_ANCHOR,ANCHOR_RIGHT_UPPER);
   ObjectSetInteger(0,background,OBJPROP_XDISTANCE,margin);
   ObjectSetInteger(0,background,OBJPROP_YDISTANCE,margin);
   ObjectSetInteger(0,background,OBJPROP_XSIZE,panelWidth);
   ObjectSetInteger(0,background,OBJPROP_YSIZE,panelHeight);
   ObjectSetInteger(0,background,OBJPROP_BGCOLOR,C'15,23,42');
   ObjectSetInteger(0,background,OBJPROP_BORDER_COLOR,C'51,65,85');
   ObjectSetInteger(0,background,OBJPROP_SELECTABLE,false);
   ObjectSetInteger(0,background,OBJPROP_HIDDEN,true);
   ObjectSetInteger(0,background,OBJPROP_ZORDER,4);

   const int bias=(int)MathRound(ExtBias[index]);
   const string biasText=(bias>0 ? "BULL" : bias<0 ? "BEAR" : "FLAT");
   const color biasColor=(bias>0 ? InpBullColor : bias<0 ? InpBearColor : InpMuteColor);
   const string profile=(g_engineProfile==TB_PROFILE_TV_2026_2_0 ? "TV" : "EA");
   const string edge=(InpFocusMode ? "FOCUS / " : "FULL / ")+profile;
   const int leftX=panelWidth;
   const int rightX=margin+12;
   EnsureHudLabel("L0",leftX,17,"TB SMC 2026",C'226,232,240',ANCHOR_RIGHT_UPPER,9);
   EnsureHudLabel("R0",rightX,17,TB_VERSION,InpAccentColor,ANCHOR_LEFT_UPPER,7);
   EnsureHudLabel("L1",leftX,36,"Bias",InpMuteColor,ANCHOR_RIGHT_UPPER,7);
   EnsureHudLabel("R1",rightX,36,biasText,biasColor,ANCHOR_LEFT_UPPER,9);
   EnsureHudLabel("L2",leftX,54,"Swing",InpMuteColor,ANCHOR_RIGHT_UPPER,7);
   EnsureHudLabel("R2",rightX,54,IntegerToString(g_swingLength),C'226,232,240',ANCHOR_LEFT_UPPER,8);
   EnsureHudLabel("L3",leftX,70,"Edge",InpMuteColor,ANCHOR_RIGHT_UPPER,7);
   EnsureHudLabel("R3",rightX,70,edge,InpAccentColor,ANCHOR_LEFT_UPPER,7);
  }

//+------------------------------------------------------------------+
//| Rebuild all owned visual objects from deterministic buffers.      |
//+------------------------------------------------------------------+
void RebuildVisuals(const int ratesTotal,const datetime &time[])
  {
   DeleteObjectsByPrefix(g_prefix+"DRAW_");
   if(g_lastClosedIndex<0)
      return;

   const color background=ChartBackground();
   const color bullCellColor=BlendColor(InpBullColor,background,0.20);
   const color bearCellColor=BlendColor(InpBearColor,background,0.20);
   const color bullVoidStrong=BlendColor(InpBullColor,background,0.28);
   const color bullVoidSoft=BlendColor(InpBullColor,background,0.16);
   const color bearVoidStrong=BlendColor(InpBearColor,background,0.28);
   const color bearVoidSoft=BlendColor(InpBearColor,background,0.16);

   if(InpShowStructure)
     {
      int created=0;
      for(int index=g_lastClosedIndex;index>=0 && created<TB_MAX_STRUCTURE_OBJECTS;index--)
        {
         const int event=(int)MathRound(ExtStructureEvent[index]);
         if(event==0 || !IsValue(ExtBreakLevel[index]))
            continue;
         int pivot=(index<ArraySize(g_breakOrigin) ? g_breakOrigin[index] : index);
         const double level=ExtBreakLevel[index];
         pivot=MathMax(0,MathMin(index,pivot));
         const bool mss=(MathAbs(event)==2);
         const color eventColor=(event>0 ? InpBullColor : InpBearColor);
         const string base=g_prefix+"DRAW_STRUCT_"+IntegerToString(index);
          CreateTrendObject(base+"_LN",time[pivot],level,time[index],level,eventColor,
                            (mss ? STYLE_SOLID : STYLE_DASH),(mss ? 2 : 1));
          CreateTextObject(base+"_LB",time[index],level,(mss ? "MSS" : "BOS"),eventColor,
                           (event>0 ? ANCHOR_LOWER : ANCHOR_UPPER),9);
         created++;
         if(InpFocusMode)
            break;
        }
     }

   if(InpShowCells)
     {
      const datetime endTime=FutureTime(time[g_lastClosedIndex],2);
      for(int i=0;i<ArraySize(g_cells);i++)
        {
         const string name=g_prefix+"DRAW_CELL_"+IntegerToString(i);
         CreateRectangleObject(name,time[g_cells[i].startIndex],g_cells[i].top,endTime,g_cells[i].bottom,
                               (g_cells[i].side>0 ? bullCellColor : bearCellColor));
        }
     }

   if(InpShowVoids)
     {
      const datetime endTime=FutureTime(time[g_lastClosedIndex],1);
      for(int i=0;i<ArraySize(g_voids);i++)
        {
         const string base=g_prefix+"DRAW_VOID_"+IntegerToString(i);
         const color strong=(g_voids[i].side>0 ? bullVoidStrong : bearVoidStrong);
         const color soft=(g_voids[i].side>0 ? bullVoidSoft : bearVoidSoft);
         if(g_voids[i].upperActive)
            CreateRectangleObject(base+"_U",time[g_voids[i].startIndex],g_voids[i].top,endTime,g_voids[i].ce,strong);
          if(g_voids[i].lowerActive)
             CreateRectangleObject(base+"_L",time[g_voids[i].startIndex],g_voids[i].ce,endTime,g_voids[i].bottom,soft);
        }
      // Pine's CE line list has an independent retention cap. TV mode keeps
      // that exact lifecycle; EA whole-zone mode removes the matching midline
      // whenever the zone is removed or expires.
      for(int i=0;i<ArraySize(g_voidMids);i++)
        {
         const string name=g_prefix+"DRAW_VOID_MID_"+IntegerToString(i);
         CreateTrendObject(name,time[g_voidMids[i].startIndex],g_voidMids[i].ce,endTime,g_voidMids[i].ce,
                           BlendColor((g_voidMids[i].side>0 ? InpBullColor : InpBearColor),background,0.65),STYLE_DOT,1);
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
      const datetime endTime=FutureTime(time[g_lastClosedIndex],4);
      CreateTrendObject(g_prefix+"DRAW_TRAIL_H",time[highStart],highLevel,endTime,highLevel,InpBearColor,STYLE_DOT,1);
      CreateTrendObject(g_prefix+"DRAW_TRAIL_L",time[lowStart],lowLevel,endTime,lowLevel,InpBullColor,STYLE_DOT,1);
      const int bias=(int)MathRound(ExtBias[g_lastClosedIndex]);
      CreateTextObject(g_prefix+"DRAW_TRAIL_HL",endTime,highLevel,(bias<0 ? "Protected H" : "Soft H"),InpBearColor,ANCHOR_LEFT,8);
      CreateTextObject(g_prefix+"DRAW_TRAIL_LL",endTime,lowLevel,(bias>0 ? "Protected L" : "Soft L"),InpBullColor,ANCHOR_LEFT,8);
     }

   UpdateHud(g_lastClosedIndex);
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
   if(g_engineProfile!=TB_PROFILE_TV_2026_2_0 && g_engineProfile!=TB_PROFILE_EA_CUSTOM)
      return(false);
   if(g_engineProfile==TB_PROFILE_TV_2026_2_0)
      return(true);
   return(g_swingLength>=2 && g_swingLength<=50
          && g_displacementAtr>=0.10 && g_displacementAtr<=5.00
          && g_cellsKept>=1 && g_cellsKept<=32
          && g_voidsKept>=1 && g_voidsKept<=32
          && g_sweepReclaimAtr>=0.0 && g_sweepReclaimAtr<=1.00
          && g_minimumVoidAtr>=0.0 && g_minimumVoidAtr<=5.00
          && g_minimumCellAtr>=0.0 && g_minimumCellAtr<=10.00
          && g_maximumCellAgeBars>=0 && g_maximumCellAgeBars<=100000
          && g_maximumVoidAgeBars>=0 && g_maximumVoidAgeBars<=100000
          && (!g_enableCells || g_enableStructure)
          && (g_voidRetention==TB_VOID_TV_HALF_PARITY
              || g_voidRetention==TB_VOID_EA_WHOLE_ZONE));
  }

//+------------------------------------------------------------------+
//| Indicator initialization.                                        |
//+------------------------------------------------------------------+
int OnInit()
  {
   if(!ResolveEngineParameters())
     {
      Print("TB SMC 2026 invalid EA engine contract.");
      return(INIT_PARAMETERS_INCORRECT);
     }
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
   SetIndexBuffer(44,ExtLiquidityHigh,INDICATOR_DATA);
   SetIndexBuffer(45,ExtLiquidityLow,INDICATOR_DATA);
   SetIndexBuffer(46,ExtLiquidityHighLive,INDICATOR_DATA);
   SetIndexBuffer(47,ExtLiquidityLowLive,INDICATOR_DATA);
   SetIndexBuffer(48,ExtTrueRange,INDICATOR_CALCULATIONS);

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
   ArraySetAsSeries(ExtLiquidityHigh,false); ArraySetAsSeries(ExtLiquidityLow,false);
   ArraySetAsSeries(ExtLiquidityHighLive,false); ArraySetAsSeries(ExtLiquidityLowLive,false);
   ArraySetAsSeries(ExtTrueRange,false);

   ConfigurePlots();
   const string profile=(g_engineProfile==TB_PROFILE_TV_2026_2_0 ? "TV" : "EA");
   IndicatorSetString(INDICATOR_SHORTNAME,"TB SMC 2026 "+profile+" ("
                      +IntegerToString(g_swingLength)+","+DoubleToString(g_displacementAtr,2)+","
                      +IntegerToString(g_cellsKept)+","+IntegerToString(g_voidsKept)+","
                      +DoubleToString(g_sweepReclaimAtr,2)+")");
   IndicatorSetInteger(INDICATOR_DIGITS,_Digits);
   g_prefix="TB_SMC_"+StringFormat("%I64d",ChartID())+"_"+IntegerToString((int)GetTickCount())+"_";
   g_lastBarTime=0;
   g_firstBarTime=0;
   g_lastAlertedClosedBar=0;
   g_lastClosedIndex=-1;
   ResetEngineState();
   return(INIT_SUCCEEDED);
  }

//+------------------------------------------------------------------+
//| Publish state and quality metrics for one bar.                    |
//| The same routine writes a closed bar or the forming-bar snapshot. |
//| Only a closed bar may set bit 0 or ClosedBarValid.                |
//+------------------------------------------------------------------+
void PublishEngineState(const int index,const bool closed,const double referencePrice)
  {
   const bool atrValid=IsValue(ExtAtr[index]) && ExtAtr[index]>0.0;
   ExtBias[index]=g_bias;
   ExtSwingHigh[index]=g_swingHigh;
   ExtSwingLow[index]=g_swingLow;
   ExtSwingHighLive[index]=(g_swingHighLive ? 1.0 : 0.0);
   ExtSwingLowLive[index]=(g_swingLowLive ? 1.0 : 0.0);
   ExtTrailHigh[index]=g_trailHigh;
   ExtTrailLow[index]=g_trailLow;
   const double liquidityHigh=NearestLiquidityHighAbove(referencePrice);
   const double liquidityLow=NearestLiquidityLowBelow(referencePrice);
   ExtLiquidityHigh[index]=liquidityHigh;
   ExtLiquidityLow[index]=liquidityLow;
   ExtLiquidityHighLive[index]=(IsValue(liquidityHigh) ? 1.0 : 0.0);
   ExtLiquidityLowLive[index]=(IsValue(liquidityLow) ? 1.0 : 0.0);

   int readyMask=(closed ? TB_READY_CLOSED : 0);
   if(atrValid) readyMask|=TB_READY_ATR;
   if(IsValue(g_swingHigh)) readyMask|=TB_READY_SWING_HIGH;
   if(IsValue(g_swingLow)) readyMask|=TB_READY_SWING_LOW;

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
   g_previousSwingHigh=g_swingHigh;
   g_previousSwingLow=g_swingLow;

   double pivotValue=EMPTY_VALUE;
   int pivotIndex=-1;
   if(IsPivotHigh(index,high,pivotValue,pivotIndex))
     {
      g_swingHigh=pivotValue;
      g_swingHighIndex=pivotIndex;
      g_swingHighLive=true;
      g_trailHigh=pivotValue;
      g_trailHighIndex=pivotIndex;
      PushLiquidityFront(g_highLiquidity,pivotValue,pivotIndex);
     }
   if(IsPivotLow(index,low,pivotValue,pivotIndex))
     {
      g_swingLow=pivotValue;
      g_swingLowIndex=pivotIndex;
      g_swingLowLive=true;
      g_trailLow=pivotValue;
      g_trailLowIndex=pivotIndex;
      PushLiquidityFront(g_lowLiquidity,pivotValue,pivotIndex);
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

   const bool atrValid=IsValue(ExtAtr[index]) && ExtAtr[index]>0.0;
   const double body=MathAbs(close[index]-open[index]);
   if(atrValid)
      ExtDisplacementRatio[index]=body/ExtAtr[index];
   const bool impulseUp=(atrValid && close[index]>open[index] && body>=ExtAtr[index]*g_displacementAtr);
   const bool impulseDown=(atrValid && close[index]<open[index] && body>=ExtAtr[index]*g_displacementAtr);
   ExtImpulseUp[index]=(impulseUp ? 1.0 : 0.0);
   ExtImpulseDown[index]=(impulseDown ? 1.0 : 0.0);

   // TV parity preserves Pine's display-driven module gates. EA_CUSTOM uses
   // dedicated engine switches, so chart cosmetics can never disable a feed.
   const bool tvProfile=(g_engineProfile==TB_PROFILE_TV_2026_2_0);
   const bool calculateStructure=(tvProfile ? InpShowStructure : g_enableStructure);
   const bool calculateCells=(tvProfile ? InpShowCells : g_enableCells);
   const bool calculateVoids=(tvProfile ? InpShowVoids : g_enableVoids);
   const bool calculateSweeps=(tvProfile ? InpShowSweeps : g_enableSweeps);
   const bool crossUp=(index>0 && IsValue(g_swingHigh) && IsValue(g_previousSwingHigh)
                       && close[index]>g_swingHigh && close[index-1]<=g_previousSwingHigh);
   const bool crossDown=(index>0 && IsValue(g_swingLow) && IsValue(g_previousSwingLow)
                         && close[index]<g_swingLow && close[index-1]>=g_previousSwingLow);
   const bool bullBreak=(calculateStructure && g_swingHighLive && crossUp && impulseUp);
   const bool bearBreak=(calculateStructure && g_swingLowLive && crossDown && impulseDown);

   if(bullBreak)
     {
      const bool isMss=(g_bias<0);
      ExtMssUp[index]=(isMss ? 1.0 : 0.0);
      ExtBosUp[index]=(isMss ? 0.0 : 1.0);
      ExtStructureEvent[index]=(isMss ? 2.0 : 1.0);
      ExtBreakLevel[index]=g_swingHigh;
      g_breakOrigin[index]=g_swingHighIndex;
      g_bias=1;
      g_swingHighLive=false;

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
      ExtBreakLevel[index]=g_swingLow;
      g_breakOrigin[index]=g_swingLowIndex;
      g_bias=-1;
      g_swingLowLive=false;

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

   // Each half is filled independently. TV mode leaves the independently
   // retained CE midline; EA whole-zone mode removes it with the final half.
   for(int i=ArraySize(g_voids)-1;i>=0;i--)
     {
      if(g_voids[i].upperActive && low[index]<g_voids[i].ce && high[index]>g_voids[i].top)
         g_voids[i].upperActive=false;
      if(g_voids[i].lowerActive && low[index]<g_voids[i].bottom && high[index]>g_voids[i].ce)
         g_voids[i].lowerActive=false;
      const bool expired=(g_maximumVoidAgeBars>0
                          && index-g_voids[i].eventIndex>g_maximumVoidAgeBars);
      if(expired)
         RemoveVoid(i,true);
      else if(!g_voids[i].upperActive && !g_voids[i].lowerActive)
         RemoveVoid(i,g_voidRetention==TB_VOID_EA_WHOLE_ZONE);
     }

   const bool highSweepState=(!g_sweepsRequireLiveSwing || g_swingHighLive);
   const bool lowSweepState=(!g_sweepsRequireLiveSwing || g_swingLowLive);
   const bool sweepHigh=(calculateSweeps && IsValue(g_swingHigh) && atrValid && highSweepState
                         && high[index]>g_swingHigh
                         && close[index]<g_swingHigh-ExtAtr[index]*g_sweepReclaimAtr);
   const bool sweepLow=(calculateSweeps && IsValue(g_swingLow) && atrValid && lowSweepState
                        && low[index]<g_swingLow
                        && close[index]>g_swingLow+ExtAtr[index]*g_sweepReclaimAtr);
   ExtSweepHigh[index]=(sweepHigh ? 1.0 : 0.0);
   ExtSweepLow[index]=(sweepLow ? 1.0 : 0.0);
   if(sweepHigh)
      ExtSweepHighMarker[index]=high[index]+ExtAtr[index]*0.12;
   if(sweepLow)
      ExtSweepLowMarker[index]=low[index]-ExtAtr[index]*0.12;

   // Remove only on a completed close through the level. This occurs after
   // event detection so the just-consumed BOS/MSS level cannot be published
   // as a forward objective on the same decision bar.
   ConsumeClosedLiquidity(close[index]);

   g_trailHighOrigin[index]=g_trailHighIndex;
   g_trailLowOrigin[index]=g_trailLowIndex;
   PublishEngineState(index,true,close[index]);
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
      return(rates_total);
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
   PublishEngineState(forming,false,close[forming]);

   const bool renderObjects=(!(bool)MQLInfoInteger(MQL_TESTER) || (bool)MQLInfoInteger(MQL_VISUAL_MODE));
   if(renderObjects)
     {
      RebuildVisuals(rates_total,time);
      if(fullRebuild)
         g_lastAlertedClosedBar=time[g_lastClosedIndex];
      else if(!MQLInfoInteger(MQL_TESTER))
         // Visual testing must render native objects without emitting an
         // Alert/Print storm on every historical BOS, sweep and void.  Engine
         // buffers and live-chart alert behavior are unchanged.
         ProcessClosedBarAlerts(time);
     }
   return(rates_total);
  }

//+------------------------------------------------------------------+
//| Keep the HUD/colors aligned after chart changes.                  |
//+------------------------------------------------------------------+
void OnChartEvent(const int id,const long &lparam,const double &dparam,const string &sparam)
  {
   if(id!=CHARTEVENT_CHART_CHANGE || g_lastClosedIndex<0)
      return;
   ConfigurePlots();
   UpdateHud(g_lastClosedIndex);
   ChartRedraw();
  }

//+------------------------------------------------------------------+
//| Remove only objects owned by this indicator instance.             |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
  {
   DeleteObjectsByPrefix(g_prefix);
  }
//+------------------------------------------------------------------+
