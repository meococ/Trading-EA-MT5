//+------------------------------------------------------------------+
//| CBR_Module.mqh — EA_Cobra v2.5.1 Self-Contained Module           |
//| Inlined from: CBR_Config, CBR_Types, CBR_SessionTime,            |
//|               CBR_Indicators, CBR_SignalEngine,                   |
//|               CBR_RiskExec (simplified), CBR_Datalog (simplified) |
//|                                                                   |
//| Adaptations for EA_Portfolio master:                             |
//|  - All _Symbol replaced with explicit symbol parameter            |
//|  - All PERIOD_CURRENT replaced with PERIOD_M15                    |
//|  - Magic number passed in, not hardcoded                          |
//|  - Risk % passed in, not hardcoded                                |
//|  - EQL_* calls removed (no ExecQualityLog dependency)            |
//|  - PCL_* partial close calls removed (BE-only)                   |
//|  - IsMarketHoliday() call removed (master handles holidays)       |
//|  - All globals prefixed g_cbr to avoid collisions                 |
//|  - Own CTrade object (g_cbrTrade) to avoid magic conflicts        |
//|                                                                   |
//| Interface:                                                        |
//|   bool CBR_Init(string symbol, ulong magic, int deviation)        |
//|   void CBR_Deinit()                                               |
//|   void CBR_OnTick(string symbol, ulong magic, double riskPct,     |
//|                   double maxLot, bool datalog)                    |
//|                                                                   |
//| Max | 2026-04-01 | Portfolio port of v2.5.1                      |
//+------------------------------------------------------------------+
#ifndef CBR_MODULE_MQH
#define CBR_MODULE_MQH

#include <Trade\Trade.mqh>
#include <Trade\PositionInfo.mqh>
#include <Trade\SymbolInfo.mqh>

//+------------------------------------------------------------------+
//| SECTION 1: CONFIG DEFINES (from CBR_Config.mqh)                  |
//+------------------------------------------------------------------+

#define CBR_VERSION          "2.5.1"
#define CBR_EA_NAME          "EA_Cobra_v2.5.1"

//--- Kill Zone Windows (Server Time UTC+2/+3 typical)
#define CBR_KZ_LDN_START_H   99     // v2.4: DISABLED London (PF 1.01 = no edge)
#define CBR_KZ_LDN_END_H     99     // v2.4: DISABLED
#define CBR_KZ_NY_START_H    13     // NY Kill Zone 13:00
#define CBR_KZ_NY_END_H      15     // NY Kill Zone ends 15:00
#define CBR_KZ_NYC_START_H   16     // NY Close Kill Zone 16:00
#define CBR_KZ_NYC_END_H     17     // NY Close Kill Zone ends 17:00

//--- Asian Range Session (for level building)
#define CBR_ASIAN_START_H    0      // Asian range starts 00:00 server
#define CBR_ASIAN_END_H      7      // Asian range ends 07:00 (before LDN KZ)
#define CBR_ASIAN_RANGE_MIN  300    // Min Asian range (pts) to be valid
#define CBR_ASIAN_RANGE_MAX  8000   // Max Asian range (pts) — skip extreme days

//--- Level Interaction Zone
#define CBR_LEVEL_ZONE_PTS   150    // Zone around level for interaction (+-150 pts)
#define CBR_LEVEL_BREAK_PTS  50     // How far past level = confirmed breakout

//--- Signal: Momentum Bar Detection (v2.1: tighter filters for quality)
#define CBR_BODY_RATIO_MIN   0.55   // v2.1: was 0.45, tightened for quality
#define CBR_CLOSE_LOC_MIN    0.65   // v2.1: was 0.55, tightened
#define CBR_ATR_RANGE_MIN    0.40   // v2.1: was 0.35, slightly tighter
#define CBR_ATR_RANGE_MAX    3.00   // v2.1: was 3.50, tighter

//--- Signal: Trend Confirmation
#define CBR_EMA_FAST         21     // Fast EMA period (H1)
#define CBR_EMA_SLOW         55     // Slow EMA period (H1)
#define CBR_TREND_MIN_DIST   50     // Min pts from EMA cluster for bias

//--- Signal: Volatility/Regime
#define CBR_ATR_PERIOD       14     // ATR period
#define CBR_BB_PERIOD        20     // BB period for squeeze detection
#define CBR_BB_DEV           2.0    // BB deviation
#define CBR_BBW_LOOKBACK     100    // Periods to calc BB width percentile

//--- Risk Management
#define CBR_SL_ATR_MULT      1.5    // v2.5: OPTIMAL
#define CBR_SL_MIN_PTS       400    // Min SL points
#define CBR_SL_MAX_PTS       5000   // Max SL points
#define CBR_TP_RR_LDN        2.5    // v2.3: was 3.0
#define CBR_TP_RR_NY         2.0    // v2.3: was 2.5
#define CBR_TP_RR_NYC        1.8    // v2.5: OPTIMAL
#define CBR_BE_AT_R          1.0    // v2.5: KEEP (BE helps Cobra)

//--- Level Distance Filter (v2.1 NEW)
#define CBR_MAX_LEVEL_DIST_ATR  2.0   // v2.5: OPTIMAL

//--- Position Management
#define CBR_MAX_SPREAD_PTS   50.0   // Max spread to enter
#define CBR_FRIDAY_CLOSE_H   17     // Friday flatten hour (server time)

//--- Day Filters
#define CBR_WED_SKIP         true    // v2.2: Skip Wednesday entirely
#define CBR_WED_RISK_MULT    0.00   // v2.2: 0 = skip
#define CBR_MON_RISK_MULT    1.00   // v2.5: Monday PF 2.49 NYC-only = STRONGEST day

//--- Position limits (master may also enforce these, but CBR enforces its own)
#define CBR_MAX_OPEN         3      // Max simultaneous positions for this module
#define CBR_MAX_PER_DAY      6      // Max trades per day for this module
#define CBR_MAX_PER_KZ       2      // Max trades per kill zone
#define CBR_DAILY_DD_PCT     4.0    // Daily DD kill at 4.0%

//+------------------------------------------------------------------+
//| SECTION 2: TYPES / ENUMS (from CBR_Types.mqh)                    |
//+------------------------------------------------------------------+

enum ENUM_CBR_KILLZONE
{
   CBR_KZ_NONE   = 0,   // Outside all kill zones
   CBR_KZ_LDN    = 1,   // London Open (07:00-09:00)
   CBR_KZ_NY     = 2,   // NY Open (13:00-15:00)
   CBR_KZ_NYC    = 3    // NY Close (16:00-17:00)
};

enum ENUM_CBR_ENTRY_MODE
{
   CBR_ENTRY_NONE     = 0,   // No valid interaction
   CBR_ENTRY_BREAKOUT = 1,   // Price broke through level with momentum
   CBR_ENTRY_BOUNCE   = 2    // Price bounced off level (touch + rejection)
};

enum ENUM_CBR_LEVEL_TYPE
{
   CBR_LVL_NONE       = 0,
   CBR_LVL_ASIAN_HI   = 1,   // Asian session high
   CBR_LVL_ASIAN_LO   = 2,   // Asian session low
   CBR_LVL_PREV_HI    = 3,   // Previous day high
   CBR_LVL_PREV_LO    = 4    // Previous day low
};

struct CBR_LevelSet
{
   double   asianHi;
   double   asianLo;
   double   asianRange;
   bool     asianValid;
   datetime asianBuildDay;

   double   prevDayHi;
   double   prevDayLo;
   bool     prevDayValid;
   datetime prevDayDate;
};

struct CBR_Signal
{
   bool              valid;
   ENUM_ORDER_TYPE   type;
   ENUM_CBR_KILLZONE killZone;
   ENUM_CBR_ENTRY_MODE entryMode;
   ENUM_CBR_LEVEL_TYPE levelType;

   double            levelPrice;
   double            levelDist;

   double            atr;
   double            bodyRatio;
   double            closeLoc;
   double            barRangeAtr;
   double            bbwPctile;
   int               bias;
   double            emaFast;
   double            emaSlow;

   double            slPrice;
   double            tpPrice;
   double            slPts;
   double            rrRatio;

   string            rejectReason;
};

struct CBR_DayState
{
   datetime          dayStart;
   double            eqStart;
   double            eqPeak;
   int               tradeCount;
   int               lossCount;
   int               kzLdnTrades;
   int               kzNyTrades;
   int               kzNycTrades;
};

//+------------------------------------------------------------------+
//| SECTION 3: MODULE-LEVEL GLOBALS (all g_cbr prefix)               |
//+------------------------------------------------------------------+

//--- Indicator handles
int    g_cbrATR    = INVALID_HANDLE;
int    g_cbrBB     = INVALID_HANDLE;
int    g_cbrEmaF   = INVALID_HANDLE;
int    g_cbrEmaS   = INVALID_HANDLE;
int    g_cbrEmaD1  = INVALID_HANDLE;
double g_cbrPt     = 0.0;

//--- Level set
CBR_LevelSet g_cbrLevels;

//--- Trade objects
CTrade        g_cbrTrade;
CPositionInfo g_cbrPos;
CSymbolInfo   g_cbrSym;

//--- Daily state
CBR_DayState  g_cbrDay;

//--- New-bar gate
datetime g_cbrLastBar = 0;

//--- Datalog
int    g_cbrLogHandle         = INVALID_HANDLE;
string g_cbrTradeCsvFile      = "";
bool   g_cbrTradeCsvHdrWritten = false;

//+------------------------------------------------------------------+
//| SECTION 4: SESSION / TIME FUNCTIONS (from CBR_SessionTime.mqh)   |
//+------------------------------------------------------------------+

ENUM_CBR_KILLZONE CBR_GetKillZone(int hour, int ldnStart, int ldnEnd,
                                   int nyStart, int nyEnd,
                                   int nycStart, int nycEnd)
{
   if(hour >= ldnStart && hour < ldnEnd)
      return CBR_KZ_LDN;
   if(hour >= nyStart && hour < nyEnd)
      return CBR_KZ_NY;
   if(hour >= nycStart && hour < nycEnd)
      return CBR_KZ_NYC;
   return CBR_KZ_NONE;
}

string CBR_KillZoneName(ENUM_CBR_KILLZONE kz)
{
   switch(kz)
   {
      case CBR_KZ_LDN:  return "LDN";
      case CBR_KZ_NY:   return "NY";
      case CBR_KZ_NYC:  return "NYC";
      default:          return "NONE";
   }
}

string CBR_EntryModeName(ENUM_CBR_ENTRY_MODE mode)
{
   switch(mode)
   {
      case CBR_ENTRY_BREAKOUT: return "BREAK";
      case CBR_ENTRY_BOUNCE:   return "BOUNCE";
      default:                 return "NONE";
   }
}

string CBR_LevelTypeName(ENUM_CBR_LEVEL_TYPE lvl)
{
   switch(lvl)
   {
      case CBR_LVL_ASIAN_HI: return "ASIA_HI";
      case CBR_LVL_ASIAN_LO: return "ASIA_LO";
      case CBR_LVL_PREV_HI:  return "PREV_HI";
      case CBR_LVL_PREV_LO:  return "PREV_LO";
      default:               return "NONE";
   }
}

double CBR_GetRR(ENUM_CBR_KILLZONE kz)
{
   switch(kz)
   {
      case CBR_KZ_LDN:  return CBR_TP_RR_LDN;
      case CBR_KZ_NY:   return CBR_TP_RR_NY;
      case CBR_KZ_NYC:  return CBR_TP_RR_NYC;
      default:          return 2.0;
   }
}

double CBR_GetDayRiskMult(int dow)
{
   switch(dow)
   {
      case 1:  return CBR_MON_RISK_MULT;
      case 3:  return CBR_WED_RISK_MULT;
      default: return 1.0;
   }
}

bool CBR_IsFridayFlatten(int dow, int hour)
{
   return (dow == 5 && hour >= CBR_FRIDAY_CLOSE_H);
}

bool CBR_IsWeekend(int dow)
{
   return (dow == 0 || dow == 6);
}

void CBR_BuildAsianRange(string symbol, int asianStartH, int asianEndH, double pt)
{
   MqlDateTime now;
   TimeToStruct(TimeCurrent(), now);
   datetime today = StringToTime(IntegerToString(now.year) + "." +
                                  IntegerToString(now.mon) + "." +
                                  IntegerToString(now.day));

   if(g_cbrLevels.asianBuildDay == today)
      return;

   double hi = -999999.0;
   double lo =  999999.0;
   int barCount = 0;

   for(int i = 1; i <= 200; i++)
   {
      datetime barT = iTime(symbol, PERIOD_M15, i);
      if(barT == 0) break;

      MqlDateTime bt;
      TimeToStruct(barT, bt);

      datetime barDay = StringToTime(IntegerToString(bt.year) + "." +
                                      IntegerToString(bt.mon) + "." +
                                      IntegerToString(bt.day));

      if(barDay != today) break;

      if(bt.hour >= asianStartH && bt.hour < asianEndH)
      {
         double h = iHigh(symbol, PERIOD_M15, i);
         double l = iLow(symbol, PERIOD_M15, i);
         if(h > hi) hi = h;
         if(l < lo) lo = l;
         barCount++;
      }
   }

   if(barCount >= 4 && hi > lo)
   {
      g_cbrLevels.asianHi    = hi;
      g_cbrLevels.asianLo    = lo;
      g_cbrLevels.asianRange = (hi - lo) / pt;
      g_cbrLevels.asianValid = (g_cbrLevels.asianRange >= CBR_ASIAN_RANGE_MIN &&
                                 g_cbrLevels.asianRange <= CBR_ASIAN_RANGE_MAX);
      g_cbrLevels.asianBuildDay = today;

      PrintFormat("[CBR] ASIAN RANGE BUILT: Hi=%.5f Lo=%.5f Range=%.0f pts Valid=%s",
                  hi, lo, g_cbrLevels.asianRange,
                  g_cbrLevels.asianValid ? "YES" : "NO");
   }
   else
   {
      g_cbrLevels.asianValid    = false;
      g_cbrLevels.asianBuildDay = today;
      PrintFormat("[CBR] ASIAN RANGE SKIP: bars=%d (need >=4)", barCount);
   }
}

void CBR_BuildPrevDayLevels(string symbol)
{
   MqlDateTime now;
   TimeToStruct(TimeCurrent(), now);
   datetime today = StringToTime(IntegerToString(now.year) + "." +
                                  IntegerToString(now.mon) + "." +
                                  IntegerToString(now.day));

   if(g_cbrLevels.prevDayDate == today)
      return;

   double prevH = iHigh(symbol, PERIOD_D1, 1);
   double prevL = iLow(symbol, PERIOD_D1, 1);

   if(prevH > 0.0 && prevL > 0.0 && prevH > prevL)
   {
      g_cbrLevels.prevDayHi    = prevH;
      g_cbrLevels.prevDayLo    = prevL;
      g_cbrLevels.prevDayValid = true;
      g_cbrLevels.prevDayDate  = today;

      PrintFormat("[CBR] PREV DAY LEVELS: Hi=%.5f Lo=%.5f", prevH, prevL);
   }
   else
   {
      g_cbrLevels.prevDayValid = false;
      g_cbrLevels.prevDayDate  = today;
   }
}

void CBR_InitLevels()
{
   ZeroMemory(g_cbrLevels);
   g_cbrLevels.asianValid   = false;
   g_cbrLevels.prevDayValid = false;
}

//+------------------------------------------------------------------+
//| SECTION 5: INDICATORS (from CBR_Indicators.mqh)                  |
//+------------------------------------------------------------------+

bool CBR_InitIndicators(string symbol)
{
   g_cbrPt = SymbolInfoDouble(symbol, SYMBOL_POINT);
   if(g_cbrPt == 0.0) g_cbrPt = 0.00001;

   g_cbrATR = iATR(symbol, PERIOD_M15, CBR_ATR_PERIOD);
   if(g_cbrATR == INVALID_HANDLE)
   { Print("[CBR] FAIL: iATR"); return false; }

   g_cbrBB = iBands(symbol, PERIOD_M15, CBR_BB_PERIOD, 0, CBR_BB_DEV, PRICE_CLOSE);
   if(g_cbrBB == INVALID_HANDLE)
   { Print("[CBR] FAIL: iBands"); return false; }

   g_cbrEmaF = iMA(symbol, PERIOD_H1, CBR_EMA_FAST, 0, MODE_EMA, PRICE_CLOSE);
   if(g_cbrEmaF == INVALID_HANDLE)
   { Print("[CBR] FAIL: iMA fast"); return false; }

   g_cbrEmaS = iMA(symbol, PERIOD_H1, CBR_EMA_SLOW, 0, MODE_EMA, PRICE_CLOSE);
   if(g_cbrEmaS == INVALID_HANDLE)
   { Print("[CBR] FAIL: iMA slow"); return false; }

   g_cbrEmaD1 = iMA(symbol, PERIOD_D1, 50, 0, MODE_EMA, PRICE_CLOSE);
   if(g_cbrEmaD1 == INVALID_HANDLE)
      Print("[CBR] WARN: iMA D1 50 unavailable — regime filter disabled");

   return true;
}

void CBR_DeinitIndicators()
{
   if(g_cbrATR   != INVALID_HANDLE) { IndicatorRelease(g_cbrATR);   g_cbrATR   = INVALID_HANDLE; }
   if(g_cbrBB    != INVALID_HANDLE) { IndicatorRelease(g_cbrBB);    g_cbrBB    = INVALID_HANDLE; }
   if(g_cbrEmaF  != INVALID_HANDLE) { IndicatorRelease(g_cbrEmaF);  g_cbrEmaF  = INVALID_HANDLE; }
   if(g_cbrEmaS  != INVALID_HANDLE) { IndicatorRelease(g_cbrEmaS);  g_cbrEmaS  = INVALID_HANDLE; }
   if(g_cbrEmaD1 != INVALID_HANDLE) { IndicatorRelease(g_cbrEmaD1); g_cbrEmaD1 = INVALID_HANDLE; }
}

double CBR_GetATR(int shift)
{
   double buf[1];
   if(CopyBuffer(g_cbrATR, 0, shift, 1, buf) != 1) return 0.0;
   return buf[0];
}

bool CBR_GetBB(int shift, double &upper, double &middle, double &lower)
{
   double bU[1], bM[1], bL[1];
   if(CopyBuffer(g_cbrBB, 1, shift, 1, bU) != 1) return false;
   if(CopyBuffer(g_cbrBB, 0, shift, 1, bM) != 1) return false;
   if(CopyBuffer(g_cbrBB, 2, shift, 1, bL) != 1) return false;
   upper  = bU[0];
   middle = bM[0];
   lower  = bL[0];
   return true;
}

double CBR_CalcBBWPercentile(string symbol)
{
   double upperArr[], middleArr[], lowerArr[];
   int lookback = CBR_BBW_LOOKBACK;

   ArrayResize(upperArr,  lookback);
   ArrayResize(middleArr, lookback);
   ArrayResize(lowerArr,  lookback);

   if(CopyBuffer(g_cbrBB, 1, 1, lookback, upperArr)  != lookback) return 50.0;
   if(CopyBuffer(g_cbrBB, 0, 1, lookback, middleArr) != lookback) return 50.0;
   if(CopyBuffer(g_cbrBB, 2, 1, lookback, lowerArr)  != lookback) return 50.0;

   double widths[];
   ArrayResize(widths, lookback);
   for(int i = 0; i < lookback; i++)
   {
      double mid = middleArr[i];
      if(mid > 0.0)
         widths[i] = (upperArr[i] - lowerArr[i]) / mid * 100.0;
      else
         widths[i] = 0.0;
   }

   double currentWidth = widths[0];
   int below = 0;
   for(int i = 1; i < lookback; i++)
   {
      if(widths[i] < currentWidth)
         below++;
   }

   return (double)below / (double)(lookback - 1) * 100.0;
}

bool CBR_GetEMA(double &fast, double &slow)
{
   double fBuf[1], sBuf[1];
   if(CopyBuffer(g_cbrEmaF, 0, 1, 1, fBuf) != 1) return false;  // shift=1 (closed bar, non-repaint)
   if(CopyBuffer(g_cbrEmaS, 0, 1, 1, sBuf) != 1) return false;  // shift=1 (closed bar, non-repaint)
   fast = fBuf[0];
   slow = sBuf[0];
   return true;
}

int CBR_GetBias(string symbol)
{
   double emaF, emaS;
   if(!CBR_GetEMA(emaF, emaS)) return 0;

   double price = iClose(symbol, PERIOD_H1, 1);  // shift=1 (closed bar, non-repaint)
   double dist  = MathAbs(price - (emaF + emaS) / 2.0) / g_cbrPt;

   if(price > emaF && emaF > emaS && dist >= CBR_TREND_MIN_DIST)
      return 1;
   if(price < emaF && emaF < emaS && dist >= CBR_TREND_MIN_DIST)
      return -1;

   return 0;
}

double CBR_GetD1RegimeMult()
{
   double ema[6];
   if(CopyBuffer(g_cbrEmaD1, 0, 1, 6, ema) != 6)
      return 1.0;

   double slope = (ema[5] - ema[0]) / 5.0;

   if(MathAbs(slope) >= 2.0)
      return 1.0;
   else
      return 0.5;
}

//+------------------------------------------------------------------+
//| SECTION 6: SIGNAL ENGINE (from CBR_SignalEngine.mqh)             |
//+------------------------------------------------------------------+

void CBR_InitSignal(CBR_Signal &sig)
{
   sig.valid        = false;
   sig.type         = ORDER_TYPE_BUY;
   sig.killZone     = CBR_KZ_NONE;
   sig.entryMode    = CBR_ENTRY_NONE;
   sig.levelType    = CBR_LVL_NONE;
   sig.levelPrice   = 0.0;
   sig.levelDist    = 0.0;
   sig.atr          = 0.0;
   sig.bodyRatio    = 0.0;
   sig.closeLoc     = 0.0;
   sig.barRangeAtr  = 0.0;
   sig.bbwPctile    = 0.0;
   sig.bias         = 0;
   sig.emaFast      = 0.0;
   sig.emaSlow      = 0.0;
   sig.slPrice      = 0.0;
   sig.tpPrice      = 0.0;
   sig.slPts        = 0.0;
   sig.rrRatio      = 0.0;
   sig.rejectReason = "";
}

double CBR_CalcCloseLoc(double open, double high, double low, double close)
{
   double range = high - low;
   if(range <= 0.0) return 0.0;
   if(close > open) return (close - low) / range;
   else             return (high - close) / range;
}

bool CBR_CheckBreakout(double c1, double o1, double h1, double l1,
                        double levelPrice, double pt,
                        bool isUpperLevel,
                        ENUM_ORDER_TYPE &direction)
{
   double breakPts = CBR_LEVEL_BREAK_PTS * pt;

   if(isUpperLevel)
   {
      if(c1 > levelPrice + breakPts && c1 > o1)
      {
         direction = ORDER_TYPE_BUY;
         return true;
      }
   }
   else
   {
      if(c1 < levelPrice - breakPts && c1 < o1)
      {
         direction = ORDER_TYPE_SELL;
         return true;
      }
   }

   return false;
}

bool CBR_CheckBounce(double c1, double o1, double h1, double l1,
                      double levelPrice, double pt,
                      bool isUpperLevel,
                      ENUM_ORDER_TYPE &direction)
{
   double zonePts = CBR_LEVEL_ZONE_PTS * pt;

   if(isUpperLevel)
   {
      // SELL bounce: wick touched level zone, closed below level, bearish bar
      if(h1 >= levelPrice - zonePts && c1 < levelPrice && c1 < o1)
      {
         direction = ORDER_TYPE_SELL;
         return true;
      }
   }
   else
   {
      // BUY bounce: wick touched level zone, closed above level, bullish bar
      if(l1 <= levelPrice + zonePts && c1 > levelPrice && c1 > o1)
      {
         direction = ORDER_TYPE_BUY;
         return true;
      }
   }

   return false;
}

bool CBR_FindLevelSignal(double c1, double o1, double h1, double l1,
                          double pt, int bias,
                          ENUM_ORDER_TYPE &direction,
                          ENUM_CBR_ENTRY_MODE &entryMode,
                          ENUM_CBR_LEVEL_TYPE &levelType,
                          double &levelPrice)
{
   //=== 1. Asian Range levels (strongest — daily structure) ===
   if(g_cbrLevels.asianValid)
   {
      // Asian Hi — breakout BUY or bounce SELL
      if(CBR_CheckBreakout(c1, o1, h1, l1, g_cbrLevels.asianHi, pt, true, direction))
      {
         if(bias == 1)
         {
            entryMode  = CBR_ENTRY_BREAKOUT;
            levelType  = CBR_LVL_ASIAN_HI;
            levelPrice = g_cbrLevels.asianHi;
            return true;
         }
      }
      if(CBR_CheckBounce(c1, o1, h1, l1, g_cbrLevels.asianHi, pt, true, direction))
      {
         if(bias == -1)
         {
            entryMode  = CBR_ENTRY_BOUNCE;
            levelType  = CBR_LVL_ASIAN_HI;
            levelPrice = g_cbrLevels.asianHi;
            return true;
         }
      }

      // Asian Lo — breakout SELL or bounce BUY
      if(CBR_CheckBreakout(c1, o1, h1, l1, g_cbrLevels.asianLo, pt, false, direction))
      {
         if(bias == -1)
         {
            entryMode  = CBR_ENTRY_BREAKOUT;
            levelType  = CBR_LVL_ASIAN_LO;
            levelPrice = g_cbrLevels.asianLo;
            return true;
         }
      }
      if(CBR_CheckBounce(c1, o1, h1, l1, g_cbrLevels.asianLo, pt, false, direction))
      {
         if(bias == 1)
         {
            entryMode  = CBR_ENTRY_BOUNCE;
            levelType  = CBR_LVL_ASIAN_LO;
            levelPrice = g_cbrLevels.asianLo;
            return true;
         }
      }
   }

   //=== 2. Previous Day levels (weaker — broader context) ===
   if(g_cbrLevels.prevDayValid)
   {
      // PrevDay Hi — breakout BUY or bounce SELL
      if(CBR_CheckBreakout(c1, o1, h1, l1, g_cbrLevels.prevDayHi, pt, true, direction))
      {
         if(bias == 1)
         {
            entryMode  = CBR_ENTRY_BREAKOUT;
            levelType  = CBR_LVL_PREV_HI;
            levelPrice = g_cbrLevels.prevDayHi;
            return true;
         }
      }
      if(CBR_CheckBounce(c1, o1, h1, l1, g_cbrLevels.prevDayHi, pt, true, direction))
      {
         if(bias == -1)
         {
            entryMode  = CBR_ENTRY_BOUNCE;
            levelType  = CBR_LVL_PREV_HI;
            levelPrice = g_cbrLevels.prevDayHi;
            return true;
         }
      }

      // PrevDay Lo — breakout SELL or bounce BUY
      if(CBR_CheckBreakout(c1, o1, h1, l1, g_cbrLevels.prevDayLo, pt, false, direction))
      {
         if(bias == -1)
         {
            entryMode  = CBR_ENTRY_BREAKOUT;
            levelType  = CBR_LVL_PREV_LO;
            levelPrice = g_cbrLevels.prevDayLo;
            return true;
         }
      }
      if(CBR_CheckBounce(c1, o1, h1, l1, g_cbrLevels.prevDayLo, pt, false, direction))
      {
         if(bias == 1)
         {
            entryMode  = CBR_ENTRY_BOUNCE;
            levelType  = CBR_LVL_PREV_LO;
            levelPrice = g_cbrLevels.prevDayLo;
            return true;
         }
      }
   }

   return false;
}

void CBR_CheckLevelSignal(string symbol, ENUM_CBR_KILLZONE kz,
                           double maxSpread, CBR_Signal &sig)
{
   CBR_InitSignal(sig);
   sig.killZone = kz;

   //=== Gate 1: Must be in a kill zone ===
   if(kz == CBR_KZ_NONE)
   { sig.rejectReason = "no_killzone"; return; }

   //=== Gate 2: Spread check ===
   double spreadPts = (double)SymbolInfoInteger(symbol, SYMBOL_SPREAD);
   if(spreadPts > maxSpread)
   { sig.rejectReason = "spread_" + DoubleToString(spreadPts, 0); return; }

   //=== Gate 3: ATR available ===
   sig.atr = CBR_GetATR(1);
   if(sig.atr <= 0.0)
   { sig.rejectReason = "atr_na"; return; }

   //=== Gate 4: At least one level set must be valid ===
   if(!g_cbrLevels.asianValid && !g_cbrLevels.prevDayValid)
   { sig.rejectReason = "no_levels"; return; }

   //=== Gate 5: OHLC bar[1] (closed bar — NO lookahead) ===
   double o1 = iOpen(symbol, PERIOD_M15, 1);
   double h1 = iHigh(symbol, PERIOD_M15, 1);
   double l1 = iLow(symbol, PERIOD_M15, 1);
   double c1 = iClose(symbol, PERIOD_M15, 1);

   double body  = MathAbs(c1 - o1);
   double range = h1 - l1;

   if(range <= 0.0)
   { sig.rejectReason = "doji"; return; }

   //=== Gate 6: Body Ratio ===
   sig.bodyRatio = body / range;
   if(sig.bodyRatio < CBR_BODY_RATIO_MIN)
   { sig.rejectReason = "body_" + DoubleToString(sig.bodyRatio, 2); return; }

   //=== Gate 7: Close Location ===
   sig.closeLoc = CBR_CalcCloseLoc(o1, h1, l1, c1);
   if(sig.closeLoc < CBR_CLOSE_LOC_MIN)
   { sig.rejectReason = "cloc_" + DoubleToString(sig.closeLoc, 2); return; }

   //=== Gate 8: Range vs ATR ===
   double atrPts   = sig.atr / g_cbrPt;
   double rangePts = range / g_cbrPt;
   sig.barRangeAtr = rangePts / atrPts;

   if(sig.barRangeAtr < CBR_ATR_RANGE_MIN)
   { sig.rejectReason = "range_small"; return; }
   if(sig.barRangeAtr > CBR_ATR_RANGE_MAX)
   { sig.rejectReason = "range_spike"; return; }

   //=== Gate 9: Trend bias ===
   sig.bias = CBR_GetBias(symbol);
   CBR_GetEMA(sig.emaFast, sig.emaSlow);

   //=== Gate 10: BBW context (logged, not a gate) ===
   sig.bbwPctile = CBR_CalcBBWPercentile(symbol);

   //=== Gate 10b: STRICT BIAS — must have directional bias ===
   if(sig.bias == 0)
   { sig.rejectReason = "no_bias"; return; }

   //=== Gate 11: LEVEL INTERACTION ===
   ENUM_ORDER_TYPE direction;
   ENUM_CBR_ENTRY_MODE entryMode;
   ENUM_CBR_LEVEL_TYPE levelType;
   double levelPrice;

   if(!CBR_FindLevelSignal(c1, o1, h1, l1, g_cbrPt, sig.bias,
                            direction, entryMode, levelType, levelPrice))
   {
      sig.rejectReason = "no_level_interaction";
      return;
   }

   sig.entryMode  = entryMode;
   sig.levelType  = levelType;
   sig.levelPrice = levelPrice;
   sig.levelDist  = MathAbs(c1 - levelPrice) / g_cbrPt;

   //=== Gate 11b: Level distance filter ===
   double levelDistAtr = sig.levelDist / atrPts;
   if(levelDistAtr > CBR_MAX_LEVEL_DIST_ATR)
   { sig.rejectReason = "level_too_far_" + DoubleToString(levelDistAtr, 1); return; }

   //=== All gates passed — Build execution levels ===

   double slAtrPts = atrPts * CBR_SL_ATR_MULT;

   double structuralSL = 0.0;

   if(entryMode == CBR_ENTRY_BREAKOUT)
   {
      if(direction == ORDER_TYPE_BUY)
         structuralSL = levelPrice - atrPts * 0.3 * g_cbrPt;
      else
         structuralSL = levelPrice + atrPts * 0.3 * g_cbrPt;
   }
   else // BOUNCE
   {
      if(direction == ORDER_TYPE_BUY)
         structuralSL = l1 - atrPts * 0.2 * g_cbrPt;
      else
         structuralSL = h1 + atrPts * 0.2 * g_cbrPt;
   }

   double atrSL = 0.0;
   if(direction == ORDER_TYPE_BUY)
      atrSL = c1 - slAtrPts * g_cbrPt;
   else
      atrSL = c1 + slAtrPts * g_cbrPt;

   double finalSL = 0.0;
   if(direction == ORDER_TYPE_BUY)
      finalSL = MathMin(structuralSL, atrSL);
   else
      finalSL = MathMax(structuralSL, atrSL);

   double slDist = MathAbs(c1 - finalSL) / g_cbrPt;
   if(slDist < CBR_SL_MIN_PTS)
   {
      if(direction == ORDER_TYPE_BUY)
         finalSL = c1 - CBR_SL_MIN_PTS * g_cbrPt;
      else
         finalSL = c1 + CBR_SL_MIN_PTS * g_cbrPt;
      slDist = CBR_SL_MIN_PTS;
   }
   if(slDist > CBR_SL_MAX_PTS)
   {
      sig.rejectReason = "sl_too_wide_" + DoubleToString(slDist, 0);
      return;
   }

   sig.slPts   = slDist;
   sig.rrRatio = CBR_GetRR(kz);
   sig.type    = direction;
   sig.valid   = true;

   if(direction == ORDER_TYPE_BUY)
   {
      sig.slPrice = finalSL;
      sig.tpPrice = c1 + slDist * sig.rrRatio * g_cbrPt;
   }
   else
   {
      sig.slPrice = finalSL;
      sig.tpPrice = c1 - slDist * sig.rrRatio * g_cbrPt;
   }
}

//+------------------------------------------------------------------+
//| SECTION 7: RISK / EXECUTION (from CBR_RiskExec.mqh, simplified)  |
//| Changes vs original:                                              |
//|  - EQL_SetContext / EQL_RecordFill removed                        |
//|  - PCL_CheckPartialClose / PCL_IsDone removed; BE-only            |
//|  - CBR_GetBlockReason uses explicit symbol parameter (not _Symbol) |
//+------------------------------------------------------------------+

void CBR_InitExec(ulong magic, int deviation, string symbol)
{
   g_cbrTrade.SetExpertMagicNumber(magic);
   g_cbrTrade.SetDeviationInPoints(deviation);

   //--- Dynamic fill mode detection
   long fillMode = SymbolInfoInteger(symbol, SYMBOL_FILLING_MODE);
   if((fillMode & SYMBOL_FILLING_FOK) != 0)
      g_cbrTrade.SetTypeFilling(ORDER_FILLING_FOK);
   else if((fillMode & SYMBOL_FILLING_IOC) != 0)
      g_cbrTrade.SetTypeFilling(ORDER_FILLING_IOC);
   else
      g_cbrTrade.SetTypeFilling(ORDER_FILLING_RETURN);

   g_cbrTrade.SetMarginMode();
   g_cbrTrade.LogLevel(LOG_LEVEL_ERRORS);

   g_cbrSym.Name(symbol);

   ZeroMemory(g_cbrDay);
   g_cbrDay.eqStart = AccountInfoDouble(ACCOUNT_EQUITY);
   g_cbrDay.eqPeak  = g_cbrDay.eqStart;
}

void CBR_DailyReset()
{
   MqlDateTime now;
   TimeCurrent(now);
   datetime today = (datetime)StringToTime(IntegerToString(now.year) + "." +
                                           IntegerToString(now.mon) + "." +
                                           IntegerToString(now.day));

   if(today != g_cbrDay.dayStart)
   {
      g_cbrDay.dayStart    = today;
      g_cbrDay.tradeCount  = 0;
      g_cbrDay.lossCount   = 0;
      g_cbrDay.kzLdnTrades = 0;
      g_cbrDay.kzNyTrades  = 0;
      g_cbrDay.kzNycTrades = 0;
      g_cbrDay.eqStart     = AccountInfoDouble(ACCOUNT_EQUITY);
   }

   double eq = AccountInfoDouble(ACCOUNT_EQUITY);
   if(eq > g_cbrDay.eqPeak) g_cbrDay.eqPeak = eq;
}

int CBR_CountPositions(string symbol, ulong magic)
{
   int count = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      if(g_cbrPos.SelectByIndex(i))
      {
         if(g_cbrPos.Symbol() == symbol && g_cbrPos.Magic() == magic)
            count++;
      }
   }
   return count;
}

string CBR_GetBlockReason(string symbol, ulong magic, double dailyDDPct,
                           int maxPerDay, int maxOpen,
                           bool killSwitch, ENUM_CBR_KILLZONE kz, int maxPerKZ)
{
   if(killSwitch)
      return "KILL_SWITCH";

   double eq = AccountInfoDouble(ACCOUNT_EQUITY);
   if(g_cbrDay.eqStart > 0.0)
   {
      double ddPct = (g_cbrDay.eqStart - eq) / g_cbrDay.eqStart * 100.0;
      if(ddPct >= dailyDDPct)
         return "DAILY_DD_" + DoubleToString(ddPct, 1);
   }

   if(g_cbrDay.tradeCount >= maxPerDay)
      return "MAX_DAY_" + IntegerToString(g_cbrDay.tradeCount);

   int openCount = CBR_CountPositions(symbol, magic);
   if(openCount >= maxOpen)
      return "MAX_OPEN_" + IntegerToString(openCount);

   if(kz == CBR_KZ_LDN && g_cbrDay.kzLdnTrades >= maxPerKZ)
      return "KZ_LDN_MAX";
   if(kz == CBR_KZ_NY && g_cbrDay.kzNyTrades >= maxPerKZ)
      return "KZ_NY_MAX";
   if(kz == CBR_KZ_NYC && g_cbrDay.kzNycTrades >= maxPerKZ)
      return "KZ_NYC_MAX";

   return "";
}

double CBR_CalcLots(string symbol, double riskPct, double slPts,
                     double maxLot, double dayRiskMult)
{
   double equity    = AccountInfoDouble(ACCOUNT_EQUITY);
   double riskMoney = equity * riskPct / 100.0 * dayRiskMult;

   double tickValue = SymbolInfoDouble(symbol, SYMBOL_TRADE_TICK_VALUE);
   double tickSize  = SymbolInfoDouble(symbol, SYMBOL_TRADE_TICK_SIZE);

   if(tickValue <= 0.0 || tickSize <= 0.0) return 0.0;

   double slMoney = slPts * g_cbrPt * tickValue / tickSize;
   if(slMoney <= 0.0) return 0.0;

   double lots = riskMoney / slMoney;

   double minLot  = SymbolInfoDouble(symbol, SYMBOL_VOLUME_MIN);
   double lotStep = SymbolInfoDouble(symbol, SYMBOL_VOLUME_STEP);

   lots = MathFloor(lots / lotStep) * lotStep;
   if(lots < minLot) lots = minLot;
   if(lots > maxLot) lots = maxLot;

   return NormalizeDouble(lots, 2);
}

bool CBR_ExecuteSignal(string symbol, CBR_Signal &sig,
                        double riskPct, double maxLot,
                        double dayRiskMult, ulong magic)
{
   if(!sig.valid) return false;

   g_cbrSym.RefreshRates();

   double lots = CBR_CalcLots(symbol, riskPct, sig.slPts, maxLot, dayRiskMult);
   if(lots <= 0.0) return false;

   int digits = (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS);
   double sl = NormalizeDouble(sig.slPrice, digits);
   double tp = NormalizeDouble(sig.tpPrice, digits);

   //--- Stop level check
   long stopLevel = SymbolInfoInteger(symbol, SYMBOL_TRADE_STOPS_LEVEL);
   double stopDist = stopLevel * g_cbrPt;
   if(sig.type == ORDER_TYPE_BUY)
   {
      double ask = SymbolInfoDouble(symbol, SYMBOL_ASK);
      if(MathAbs(ask - sl) < stopDist || MathAbs(tp - ask) < stopDist)
      {
         PrintFormat("[CBR] SKIP: stop level violation. ask=%.5f sl=%.5f tp=%.5f stopDist=%.5f",
                     ask, sl, tp, stopDist);
         return false;
      }
   }
   else
   {
      double bid = SymbolInfoDouble(symbol, SYMBOL_BID);
      if(MathAbs(sl - bid) < stopDist || MathAbs(bid - tp) < stopDist)
      {
         PrintFormat("[CBR] SKIP: stop level violation. bid=%.5f sl=%.5f tp=%.5f stopDist=%.5f",
                     bid, sl, tp, stopDist);
         return false;
      }
   }

   bool result = false;
   string comment = CBR_EA_NAME + "_" + CBR_KillZoneName(sig.killZone) +
                    "_" + CBR_EntryModeName(sig.entryMode) +
                    "_" + CBR_LevelTypeName(sig.levelType);

   if(sig.type == ORDER_TYPE_BUY)
   {
      double ask = SymbolInfoDouble(symbol, SYMBOL_ASK);
      result = g_cbrTrade.Buy(lots, symbol, ask, sl, tp, comment);
   }
   else
   {
      double bid = SymbolInfoDouble(symbol, SYMBOL_BID);
      result = g_cbrTrade.Sell(lots, symbol, bid, sl, tp, comment);
   }

   if(result)
   {
      uint retcode = g_cbrTrade.ResultRetcode();
      if(retcode == TRADE_RETCODE_DONE || retcode == TRADE_RETCODE_PLACED)
      {
         g_cbrDay.tradeCount++;

         if(sig.killZone == CBR_KZ_LDN)  g_cbrDay.kzLdnTrades++;
         if(sig.killZone == CBR_KZ_NY)   g_cbrDay.kzNyTrades++;
         if(sig.killZone == CBR_KZ_NYC)  g_cbrDay.kzNycTrades++;

         PrintFormat("[CBR] TRADE %s | KZ=%s | Mode=%s | Level=%s@%.2f | Lots=%.2f | SL=%.2f | TP=%.2f | RR=%.1f | Body=%.2f | Bias=%d",
                     (sig.type == ORDER_TYPE_BUY ? "BUY" : "SELL"),
                     CBR_KillZoneName(sig.killZone),
                     CBR_EntryModeName(sig.entryMode),
                     CBR_LevelTypeName(sig.levelType),
                     sig.levelPrice,
                     lots, sl, tp, sig.rrRatio,
                     sig.bodyRatio, sig.bias);
         return true;
      }
      else
      {
         PrintFormat("[CBR] ORDER FAIL: retcode=%u, comment=%s",
                     retcode, g_cbrTrade.ResultComment());
      }
   }

   return false;
}

void CBR_ManagePositions(string symbol, ulong magic, int dow, int hour)
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      if(!g_cbrPos.SelectByIndex(i)) continue;
      if(g_cbrPos.Symbol() != symbol || g_cbrPos.Magic() != magic) continue;

      ulong ticket = g_cbrPos.Ticket();

      // Friday flatten
      if(CBR_IsFridayFlatten(dow, hour))
      {
         g_cbrTrade.PositionClose(ticket);
         PrintFormat("[CBR] FRIDAY FLATTEN: ticket=%d", ticket);
         continue;
      }

      // Break-even move (BE-only; partial close removed for portfolio module)
      double openPrice = g_cbrPos.PriceOpen();
      double sl        = g_cbrPos.StopLoss();
      double tp        = g_cbrPos.TakeProfit();
      double current   = g_cbrPos.PriceCurrent();

      double initialRisk = MathAbs(openPrice - sl);
      if(initialRisk <= 0.0) continue;

      double profitPts = 0.0;
      if(g_cbrPos.PositionType() == POSITION_TYPE_BUY)
         profitPts = current - openPrice;
      else
         profitPts = openPrice - current;

      if(profitPts >= CBR_BE_AT_R * initialRisk)
      {
         double newSL = 0.0;
         if(g_cbrPos.PositionType() == POSITION_TYPE_BUY)
            newSL = openPrice + g_cbrPt;
         else
            newSL = openPrice - g_cbrPt;

         int digits = (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS);
         newSL = NormalizeDouble(newSL, digits);

         bool shouldModify = false;
         if(g_cbrPos.PositionType() == POSITION_TYPE_BUY && newSL > sl)
            shouldModify = true;
         if(g_cbrPos.PositionType() == POSITION_TYPE_SELL && (newSL < sl || sl == 0.0))
            shouldModify = true;

         if(shouldModify)
         {
            //--- Freeze level check before modifying
            long freezeLevel = SymbolInfoInteger(symbol, SYMBOL_TRADE_FREEZE_LEVEL);
            double freezeDist = freezeLevel * g_cbrPt;
            double distToSL = MathAbs(current - sl);
            double distToTP = MathAbs(tp - current);
            if(freezeLevel > 0 && (distToSL < freezeDist || distToTP < freezeDist))
            {
               // Position is in freeze zone — skip BE modify silently
            }
            else if(g_cbrTrade.PositionModify(ticket, newSL, tp))
               PrintFormat("[CBR] BE MOVE: ticket=%d, newSL=%.5f", ticket, newSL);
         }
      }
   }
}

void CBR_CloseAll(string symbol, ulong magic)
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      if(!g_cbrPos.SelectByIndex(i)) continue;
      if(g_cbrPos.Symbol() != symbol || g_cbrPos.Magic() != magic) continue;
      g_cbrTrade.PositionClose(g_cbrPos.Ticket());
   }
}

//+------------------------------------------------------------------+
//| SECTION 8: DATALOG (from CBR_Datalog.mqh, simplified)            |
//| Change: CBR_LogSignal uses explicit symbol param, not _Symbol     |
//+------------------------------------------------------------------+

void CBR_InitTradeCsv(ulong magic)
{
   g_cbrTradeCsvFile      = "PaperDeploy/EA_Cobra/trades_" + IntegerToString((int)magic) + ".csv";
   g_cbrTradeCsvHdrWritten = FileIsExist(g_cbrTradeCsvFile, FILE_COMMON);
}

void CBR_AppendTradeCsv(ulong deal, ulong magic, string symbol)
{
   if(!HistoryDealSelect(deal)) return;
   if((ulong)HistoryDealGetInteger(deal, DEAL_MAGIC) != magic) return;
   if(HistoryDealGetString(deal, DEAL_SYMBOL) != symbol) return;

   ENUM_DEAL_ENTRY entry = (ENUM_DEAL_ENTRY)HistoryDealGetInteger(deal, DEAL_ENTRY);
   if(entry != DEAL_ENTRY_OUT && entry != DEAL_ENTRY_INOUT) return;

   int handle = FileOpen(g_cbrTradeCsvFile,
                         FILE_READ|FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_SHARE_READ|FILE_SHARE_WRITE|FILE_COMMON,
                         ',');
   if(handle == INVALID_HANDLE) return;

   if(!g_cbrTradeCsvHdrWritten)
   {
      FileWrite(handle, "timestamp", "symbol", "magic", "direction", "profit", "comment");
      g_cbrTradeCsvHdrWritten = true;
   }
   FileSeek(handle, 0, SEEK_END);

   long dealType = HistoryDealGetInteger(deal, DEAL_TYPE);
   string direction = (dealType == DEAL_TYPE_BUY || dealType == DEAL_TYPE_BUY_CANCELED) ? "buy" : "sell";
   double profit = HistoryDealGetDouble(deal, DEAL_PROFIT)
                 + HistoryDealGetDouble(deal, DEAL_SWAP)
                 + HistoryDealGetDouble(deal, DEAL_COMMISSION);
   string comment = HistoryDealGetString(deal, DEAL_COMMENT);
   datetime t = (datetime)HistoryDealGetInteger(deal, DEAL_TIME);

   FileWrite(handle,
             TimeToString(t, TIME_DATE|TIME_MINUTES|TIME_SECONDS),
             symbol,
             IntegerToString((int)magic),
             direction,
             DoubleToString(profit, 2),
             comment);
   FileClose(handle);
}

void CBR_CloseTradeCsv()
{
   g_cbrTradeCsvFile      = "";
   g_cbrTradeCsvHdrWritten = false;
}

bool CBR_InitDatalog(string symbol)
{
   string fname = CBR_EA_NAME + "_" + symbol + "_signals.csv";
   g_cbrLogHandle = FileOpen(fname, FILE_WRITE | FILE_CSV | FILE_ANSI, '\t');
   if(g_cbrLogHandle == INVALID_HANDLE)
   {
      PrintFormat("[CBR] WARN: Cannot open log file: %s", fname);
      return false;
   }

   FileWrite(g_cbrLogHandle,
      "DateTime", "BarTime", "KillZone", "EntryMode", "LevelType",
      "LevelPrice", "LevelDist", "Direction",
      "BodyRatio", "CloseLoc", "BarRangeATR", "BBW_Pct",
      "Bias", "EMA_Fast", "EMA_Slow", "ATR",
      "SL_Pts", "RR", "Result", "RejectReason");

   return true;
}

void CBR_LogSignal(string symbol, CBR_Signal &sig, bool executed)
{
   if(g_cbrLogHandle == INVALID_HANDLE) return;

   string dir = "NONE";
   if(sig.valid)
      dir = (sig.type == ORDER_TYPE_BUY) ? "BUY" : "SELL";

   string result = "REJECT";
   if(sig.valid && executed)  result = "EXECUTED";
   if(sig.valid && !executed) result = "BLOCKED";

   FileWrite(g_cbrLogHandle,
      TimeToString(TimeCurrent(), TIME_DATE | TIME_MINUTES),
      TimeToString(iTime(symbol, PERIOD_M15, 1), TIME_DATE | TIME_MINUTES),
      CBR_KillZoneName(sig.killZone),
      CBR_EntryModeName(sig.entryMode),
      CBR_LevelTypeName(sig.levelType),
      DoubleToString(sig.levelPrice, 2),
      DoubleToString(sig.levelDist, 0),
      dir,
      DoubleToString(sig.bodyRatio, 3),
      DoubleToString(sig.closeLoc, 3),
      DoubleToString(sig.barRangeAtr, 3),
      DoubleToString(sig.bbwPctile, 1),
      IntegerToString(sig.bias),
      DoubleToString(sig.emaFast, 2),
      DoubleToString(sig.emaSlow, 2),
      DoubleToString(sig.atr / g_cbrPt, 1),
      DoubleToString(sig.slPts, 0),
      DoubleToString(sig.rrRatio, 1),
      result,
      sig.rejectReason);
}

void CBR_DeinitDatalog()
{
   if(g_cbrLogHandle != INVALID_HANDLE)
   {
      FileClose(g_cbrLogHandle);
      g_cbrLogHandle = INVALID_HANDLE;
   }
}

//+------------------------------------------------------------------+
//| SECTION 9: PUBLIC MODULE INTERFACE                               |
//+------------------------------------------------------------------+

//+------------------------------------------------------------------+
//| CBR_Init — call from master OnInit()                             |
//+------------------------------------------------------------------+
bool CBR_Init(string symbol, ulong magic, int deviation)
{
   // Validate symbol
   if(StringFind(symbol, "XAU") < 0 && StringFind(symbol, "GOLD") < 0)
      PrintFormat("[CBR] WARNING: Designed for XAUUSD, running on %s", symbol);

   // Init indicators
   if(!CBR_InitIndicators(symbol))
   {
      Print("[CBR] FATAL: Indicator init failed");
      return false;
   }

   // Init execution (CTrade + day state)
   CBR_InitExec(magic, deviation, symbol);

   // Init level state
   CBR_InitLevels();

   // Init trade CSV (always; signal datalog opened in CBR_OnTick if datalog=true)
   CBR_InitTradeCsv(magic);

   PrintFormat("[CBR] Module v%s initialized | Symbol=%s | Magic=%llu | Dev=%d",
               CBR_VERSION, symbol, magic, deviation);
   PrintFormat("[CBR] KZ: NY=%d:00-%d:00, NYC=%d:00-%d:00 | Asian=%d:00-%d:00",
               CBR_KZ_NY_START_H, CBR_KZ_NY_END_H,
               CBR_KZ_NYC_START_H, CBR_KZ_NYC_END_H,
               CBR_ASIAN_START_H, CBR_ASIAN_END_H);

   return true;
}

//+------------------------------------------------------------------+
//| CBR_Deinit — call from master OnDeinit()                         |
//+------------------------------------------------------------------+
void CBR_Deinit()
{
   CBR_DeinitIndicators();
   CBR_DeinitDatalog();
   CBR_CloseTradeCsv();
   PrintFormat("[CBR] Module v%s deinitialized", CBR_VERSION);
}

//+------------------------------------------------------------------+
//| CBR_OnTick — call from master OnTick() every tick                |
//| symbol   : target symbol (e.g. "XAUUSD+")                        |
//| magic    : this module's magic number                             |
//| riskPct  : risk per trade in percent (e.g. 0.50)                 |
//| maxLot   : maximum lot size                                       |
//| datalog  : enable CSV signal logging                              |
//+------------------------------------------------------------------+
void CBR_OnTick(string symbol, ulong magic, double riskPct,
                double maxLot, bool datalog)
{
   //=== 1. New bar gate (M15) ===
   datetime barTime = iTime(symbol, PERIOD_M15, 0);
   if(barTime == g_cbrLastBar) return;
   g_cbrLastBar = barTime;

   //=== 2. Lazy datalog init (first tick after init if requested) ===
   if(datalog && g_cbrLogHandle == INVALID_HANDLE)
      CBR_InitDatalog(symbol);

   //=== 3. Daily reset ===
   CBR_DailyReset();

   //=== 4. Current time ===
   MqlDateTime now;
   TimeToStruct(TimeCurrent(), now);

   //=== 5. Build levels once per day when hour >= AsianEndH ===
   if(now.hour >= CBR_ASIAN_END_H)
   {
      CBR_BuildAsianRange(symbol, CBR_ASIAN_START_H, CBR_ASIAN_END_H, g_cbrPt);
      CBR_BuildPrevDayLevels(symbol);
   }

   //=== 6. Kill zone detection ===
   ENUM_CBR_KILLZONE kz = CBR_GetKillZone(now.hour,
                              CBR_KZ_LDN_START_H, CBR_KZ_LDN_END_H,
                              CBR_KZ_NY_START_H,  CBR_KZ_NY_END_H,
                              CBR_KZ_NYC_START_H, CBR_KZ_NYC_END_H);

   //=== 7. Position management (ALWAYS runs) ===
   CBR_ManagePositions(symbol, magic, now.day_of_week, now.hour);

   //=== 8. Skip if outside kill zones ===
   if(kz == CBR_KZ_NONE) return;

   //=== 9. Skip weekends ===
   if(CBR_IsWeekend(now.day_of_week)) return;

   //=== 10. Skip Wednesday (v2.2: PF 0.87 — no edge) ===
   #ifdef CBR_WED_SKIP
   if(now.day_of_week == 3) return;
   #endif

   //=== 11. Friday flatten ===
   if(CBR_IsFridayFlatten(now.day_of_week, now.hour))
   {
      CBR_CloseAll(symbol, magic);
      return;
   }

   //=== 12. Check block reasons (holiday guard delegated to master) ===
   string blockReason = CBR_GetBlockReason(symbol, magic,
                                            CBR_DAILY_DD_PCT, CBR_MAX_PER_DAY,
                                            CBR_MAX_OPEN, false, kz, CBR_MAX_PER_KZ);
   if(blockReason != "")
      return;

   //=== 13. Generate level-based signal ===
   CBR_Signal sig;
   CBR_CheckLevelSignal(symbol, kz, CBR_MAX_SPREAD_PTS, sig);

   //=== 14. Log signal ===
   if(datalog && sig.rejectReason != "no_killzone")
      CBR_LogSignal(symbol, sig, false);

   //=== 15. Execute if valid ===
   if(sig.valid)
   {
      double dayRiskMult   = CBR_GetDayRiskMult(now.day_of_week);
      double d1RegimeMult  = CBR_GetD1RegimeMult();
      bool executed = CBR_ExecuteSignal(symbol, sig, riskPct, maxLot,
                                         dayRiskMult * d1RegimeMult, magic);

      if(datalog)
         CBR_LogSignal(symbol, sig, executed);
   }
}

//+------------------------------------------------------------------+
//| CBR_OnDealAdd — call from master OnTradeTransaction()            |
//| Only needed when master routes deal events per-module.           |
//| Appends closed trade to the module's trade CSV.                  |
//+------------------------------------------------------------------+
void CBR_OnDealAdd(ulong deal, ulong magic, string symbol)
{
   if(!HistoryDealSelect(deal)) return;
   long dealMagic = HistoryDealGetInteger(deal, DEAL_MAGIC);
   if((ulong)dealMagic != magic) return;

   ENUM_DEAL_ENTRY entry = (ENUM_DEAL_ENTRY)HistoryDealGetInteger(deal, DEAL_ENTRY);
   if(entry == DEAL_ENTRY_OUT || entry == DEAL_ENTRY_INOUT)
      CBR_AppendTradeCsv(deal, magic, symbol);
}

#endif // CBR_MODULE_MQH
