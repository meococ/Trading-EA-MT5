//+------------------------------------------------------------------+
//| SB_Module.mqh                                                    |
//| Self-contained SilverBullet v2 module for EA_Portfolio           |
//|                                                                  |
//| Extracted from EA_SilverBullet_v2.mq5 (2026-04-01)              |
//| Strategy: ICT Kill Zone + Displacement + FVG Entry               |
//| Symbol  : USDJPY (M15), passed from master at runtime            |
//|                                                                  |
//| Interface:                                                       |
//|   bool SB_Init(string symbol, ulong magic, int deviation)        |
//|   void SB_Deinit()                                               |
//|   void SB_OnTick(string symbol, ulong magic,                     |
//|                  double riskPct, double maxLot)                  |
//|                                                                  |
//| Removed from standalone EA:                                      |
//|   - input declarations (all become #defines)                     |
//|   - ChartComment / UpdateChartComment                            |
//|   - EQL_ calls (ExecQualityLog — external dep)                   |
//|   - PCL_ calls (PartialClose — off by default, stub preserved)   |
//|   - IsMarketHoliday() (HolidayCalendar — external dep)           |
//|   - Trade CSV export (paper-deploy only, not needed in portfolio) |
//|   - OnTradeTransaction / OnTester / OnDeinit event wrappers      |
//|   - _Symbol references -> explicit symbol parameter              |
//|                                                                  |
//| All state variables prefixed g_sb to avoid master EA collisions. |
//+------------------------------------------------------------------+
#ifndef SB_MODULE_MQH
#define SB_MODULE_MQH

#include <Trade\Trade.mqh>
#include <Trade\PositionInfo.mqh>
#include <Trade\SymbolInfo.mqh>

//+------------------------------------------------------------------+
//| SIGNAL / FILTER CONSTANTS (replaces input block)                 |
//+------------------------------------------------------------------+

// Kill Zones — broker time GMT+2
#define SB_LDN_START        11      // London KZ start hour
#define SB_LDN_END          12      // London KZ end hour
#define SB_NYAM_START       16      // NY AM KZ start hour
#define SB_NYAM_END         18      // NY AM KZ end hour
#define SB_USE_LDN          true
#define SB_USE_NYAM         true
#define SB_USE_NYPM         false   // NY PM off (default in v2)
#define SB_NYPM_START       20
#define SB_NYPM_END         22

// Displacement
#define SB_DISP_BODY_ATR    0.40    // Min displacement body (ATR multiples)
#define SB_DISP_BODY_RATIO  0.70    // Min body/range ratio
#define SB_ATR_PERIOD       14      // H1 ATR period

// FVG
#define SB_FVG_MAX_WAIT     8       // Max bars to wait for FVG fill
#define SB_FVG_MIN_SIZE     0.10    // Min FVG size (ATR multiples)

// SL / TP
#define SB_SL_ATR           1.50    // SL in ATR multiples beyond FVG
#define SB_TP_RR_LDN        1.50    // R:R London
#define SB_TP_RR_NY         1.50    // R:R NY AM
#define SB_TP_RR_DEFAULT    1.50    // Fallback
#define SB_MIN_SL_PIPS      8.0
#define SB_MAX_SL_PIPS      60.0

// HTF Bias
#define SB_USE_HTF_BIAS     true
#define SB_HTF_EMA_PERIOD   50      // H4 EMA period

// Volatility Regime — D1 ATR
#define SB_USE_VOL_REGIME   true
#define SB_VOL_ATR_PERIOD   20      // D1 ATR period
#define SB_VOL_ATR_MIN      0.70    // Min ratio (was 0.50, tightened S124)
#define SB_VOL_ATR_MAX      1.80    // Max ratio (was 2.50, tightened S124)

// Session / Day
#define SB_SKIP_FRIDAY      true

// Risk Management
#define SB_MAX_TRADES_DAY   3
#define SB_MAX_TRADES_KZ    1
#define SB_MAX_SPREAD_PIPS  5.0
#define SB_MAX_DAILY_DD     3.0     // % daily DD limit
#define SB_MAX_TOTAL_DD     10.0    // % total DD from peak

// Execution
#define SB_RETRY_COUNT      3
#define SB_RETRY_DELAY_MS   500
#define SB_TRADE_COMMENT    "SB2"

//+------------------------------------------------------------------+
//| ENUMS                                                            |
//+------------------------------------------------------------------+
enum ENUM_SB_KZ_TYPE { SB_KZ_NONE, SB_KZ_LONDON, SB_KZ_NY_AM, SB_KZ_NY_PM };

//+------------------------------------------------------------------+
//| STRUCTS                                                          |
//+------------------------------------------------------------------+
struct SB_FVGZone
{
   double          upper;
   double          lower;
   bool            isBullish;
   datetime        createTime;
   int             barAge;
   bool            active;
   ENUM_SB_KZ_TYPE sourceKZ;
};

//+------------------------------------------------------------------+
//| MODULE GLOBALS — all prefixed g_sb                               |
//+------------------------------------------------------------------+
CTrade        g_sbTrade;
CPositionInfo g_sbPos;
CSymbolInfo   g_sbSym;

int    g_sbHatrH1       = INVALID_HANDLE;
int    g_sbHhtfEma      = INVALID_HANDLE;
int    g_sbHatrD1Regime = INVALID_HANDLE;

double g_sbPt       = 0;
double g_sbPipSize  = 0;

// Daily tracking
int             g_sbTradesToday  = 0;
int             g_sbTradesThisKZ = 0;
datetime        g_sbLastTradeDay = 0;
double          g_sbDayStartEq  = 0;
ENUM_SB_KZ_TYPE g_sbLastKZ      = SB_KZ_NONE;

// Total DD tracking
double g_sbPeakEquity = 0;

// FVG state — persists across bars
SB_FVGZone g_sbFVG;

// Trailing SL anchor (unused by default — SB_USE_TRAIL false in v2)
double g_sbInitialSLDist = 0;

// Last bar processed
datetime g_sbLastBar = 0;

// GV prefix for crash recovery (module-scoped)
string g_sbGvPrefix = "";

// Symbol cached (set at SB_Init, passed at SB_OnTick)
string g_sbSymbol = "";

// Magic cached
ulong g_sbMagic = 0;

//+------------------------------------------------------------------+
//| Forward declarations                                             |
//+------------------------------------------------------------------+
void   SB_ResetFVG();
void   SB_SaveFVGState();
bool   SB_RestoreFVGState();
void   SB_CleanFVGState();
ENUM_SB_KZ_TYPE SB_GetCurrentKZ(int hour);
void   SB_ScanForDisplacementFVG(double atr, ENUM_SB_KZ_TYPE kz,
                                  double riskPct, double maxLot);
void   SB_TryFVGEntry(double atr, double riskPct, double maxLot);
int    SB_CountMyPositions();
void   SB_CloseAllPositions();
ENUM_ORDER_TYPE_FILLING SB_DetectFillMode(string symbol);

//+------------------------------------------------------------------+
//| SB_Init — call from master OnInit                                |
//+------------------------------------------------------------------+
bool SB_Init(string symbol, ulong magic, int deviation)
{
   g_sbSymbol = symbol;
   g_sbMagic  = magic;

   g_sbSym.Name(symbol);
   g_sbPt = SymbolInfoDouble(symbol, SYMBOL_POINT);
   if(g_sbPt <= 0)
   {
      PrintFormat("[SB] ERROR: invalid point for %s", symbol);
      return false;
   }

   // Pip size detection
   int digits = (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS);
   if(digits <= 2)
      g_sbPipSize = g_sbPt * 100.0;      // Gold/Silver
   else if(digits == 3 || digits == 5)
      g_sbPipSize = g_sbPt * 10.0;       // Standard forex (USDJPY = 3)
   else
      g_sbPipSize = g_sbPt;

   // Indicators
   g_sbHatrH1 = iATR(symbol, PERIOD_H1, SB_ATR_PERIOD);
   if(g_sbHatrH1 == INVALID_HANDLE)
   {
      PrintFormat("[SB] ERROR: H1 ATR handle failed for %s", symbol);
      return false;
   }

   if(SB_USE_HTF_BIAS)
   {
      g_sbHhtfEma = iMA(symbol, PERIOD_H4, SB_HTF_EMA_PERIOD, 0, MODE_EMA, PRICE_CLOSE);
      if(g_sbHhtfEma == INVALID_HANDLE)
      {
         PrintFormat("[SB] ERROR: H4 EMA handle failed for %s", symbol);
         return false;
      }
   }

   if(SB_USE_VOL_REGIME)
   {
      g_sbHatrD1Regime = iATR(symbol, PERIOD_D1, SB_VOL_ATR_PERIOD);
      if(g_sbHatrD1Regime == INVALID_HANDLE)
      {
         PrintFormat("[SB] ERROR: D1 ATR regime handle failed for %s", symbol);
         return false;
      }
   }

   // Trade object
   g_sbTrade.SetExpertMagicNumber(magic);
   g_sbTrade.SetTypeFilling(SB_DetectFillMode(symbol));
   g_sbTrade.SetDeviationInPoints(deviation);
   g_sbTrade.LogLevel(LOG_LEVEL_ERRORS);

   // Reset state
   g_sbTradesToday   = 0;
   g_sbTradesThisKZ  = 0;
   g_sbLastTradeDay  = 0;
   g_sbLastKZ        = SB_KZ_NONE;
   g_sbDayStartEq    = AccountInfoDouble(ACCOUNT_EQUITY);
   g_sbPeakEquity    = AccountInfoDouble(ACCOUNT_EQUITY);
   g_sbLastBar       = 0;
   g_sbInitialSLDist = 0;
   g_sbGvPrefix      = "SB2_" + symbol + "_" + IntegerToString((long)magic) + "_";
   SB_ResetFVG();

   // Attempt crash recovery from GlobalVariables
   if(SB_RestoreFVGState())
      PrintFormat("[SB] Crash recovery: pending FVG restored for %s", symbol);

   PrintFormat("[SB] SB_Module initialized: sym=%s magic=%I64u dev=%d fill=%s",
               symbol, magic, deviation,
               EnumToString(SB_DetectFillMode(symbol)));
   return true;
}

//+------------------------------------------------------------------+
//| SB_Deinit — call from master OnDeinit                           |
//+------------------------------------------------------------------+
void SB_Deinit()
{
   if(g_sbHatrH1       != INVALID_HANDLE) { IndicatorRelease(g_sbHatrH1);       g_sbHatrH1 = INVALID_HANDLE; }
   if(g_sbHhtfEma      != INVALID_HANDLE) { IndicatorRelease(g_sbHhtfEma);      g_sbHhtfEma = INVALID_HANDLE; }
   if(g_sbHatrD1Regime != INVALID_HANDLE) { IndicatorRelease(g_sbHatrD1Regime); g_sbHatrD1Regime = INVALID_HANDLE; }
   SB_CleanFVGState();
   PrintFormat("[SB] SB_Module deinitialized: %s", g_sbSymbol);
}

//+------------------------------------------------------------------+
//| SB_OnTick — call from master OnTick                             |
//| Master passes symbol, magic, riskPct, maxLot each tick          |
//+------------------------------------------------------------------+
void SB_OnTick(string symbol, ulong magic, double riskPct, double maxLot)
{
   // --- New bar detection (M15 closed-bar logic) ---
   datetime barTime = iTime(symbol, PERIOD_M15, 0);
   if(barTime == g_sbLastBar) return;
   g_sbLastBar = barTime;

   // --- Sufficient bars guard ---
   if(Bars(symbol, PERIOD_M15) < 50) return;

   // --- Time info ---
   MqlDateTime dt;
   TimeToStruct(TimeCurrent(), dt);
   int hour = dt.hour;
   int dow  = dt.day_of_week;

   // --- Kill zone ---
   ENUM_SB_KZ_TYPE currentKZ = SB_GetCurrentKZ(hour);

   // --- Day reset ---
   datetime today = StringToTime(StringFormat("%04d.%02d.%02d", dt.year, dt.mon, dt.day));
   if(today != g_sbLastTradeDay)
   {
      g_sbLastTradeDay  = today;
      g_sbTradesToday   = 0;
      g_sbTradesThisKZ  = 0;
      g_sbLastKZ        = SB_KZ_NONE;
      g_sbDayStartEq    = AccountInfoDouble(ACCOUNT_EQUITY);
      SB_ResetFVG();
   }

   // --- Peak equity tracking ---
   double equity = AccountInfoDouble(ACCOUNT_EQUITY);
   if(equity > g_sbPeakEquity) g_sbPeakEquity = equity;

   // --- Day filter ---
   if(dow == 0 || dow == 6) return;
   if(SB_SKIP_FRIDAY && dow == 5) return;

   // --- Daily DD guard ---
   if(g_sbDayStartEq > 0 &&
      (g_sbDayStartEq - equity) / g_sbDayStartEq * 100.0 > SB_MAX_DAILY_DD)
   {
      SB_CloseAllPositions();
      PrintFormat("[SB] DAILY DD LIMIT HIT — all positions closed (%s)", symbol);
      return;
   }

   // --- Total DD guard (from peak equity) ---
   if(g_sbPeakEquity > 0 &&
      (g_sbPeakEquity - equity) / g_sbPeakEquity * 100.0 > SB_MAX_TOTAL_DD)
   {
      SB_CloseAllPositions();
      PrintFormat("[SB] TOTAL DD LIMIT HIT — all positions closed (%s)", symbol);
      return;
   }

   // --- Volatility Regime Filter (D1 ATR) ---
   if(SB_USE_VOL_REGIME && g_sbHatrD1Regime != INVALID_HANDLE)
   {
      double d1Atr[];
      if(CopyBuffer(g_sbHatrD1Regime, 0, 1, 2, d1Atr) < 2) return;
      double currentATR = d1Atr[1];

      // Long-period average (2x the ATR period)
      int lookback = SB_VOL_ATR_PERIOD * 2;
      double d1AtrLong[];
      double avgATR = (d1Atr[0] + currentATR) / 2.0;   // fallback
      if(CopyBuffer(g_sbHatrD1Regime, 0, 1, lookback, d1AtrLong) >= lookback)
      {
         double sum = 0;
         for(int i = 0; i < lookback; i++) sum += d1AtrLong[i];
         avgATR = sum / lookback;
      }

      if(avgATR > 0)
      {
         double ratio = currentATR / avgATR;
         if(ratio < SB_VOL_ATR_MIN || ratio > SB_VOL_ATR_MAX)
            return;
      }
   }

   // --- KZ switch: reset per-KZ counter; expire FVG when leaving KZ ---
   if(currentKZ != g_sbLastKZ)
   {
      g_sbTradesThisKZ = 0;
      g_sbLastKZ       = currentKZ;
      if(g_sbFVG.active && currentKZ == SB_KZ_NONE)
         SB_ResetFVG();
   }

   // --- H1 ATR ---
   double atrBuf[];
   if(CopyBuffer(g_sbHatrH1, 0, 1, 1, atrBuf) < 1) return;
   double atr = atrBuf[0];
   if(atr <= 0) return;

   // --- PHASE 1: Inside a kill zone — scan for displacement + FVG ---
   if(currentKZ != SB_KZ_NONE && !g_sbFVG.active)
      SB_ScanForDisplacementFVG(atr, currentKZ, riskPct, maxLot);

   // --- PHASE 2: Have a pending FVG — track age and attempt entry ---
   if(g_sbFVG.active)
   {
      g_sbFVG.barAge++;
      GlobalVariableSet(g_sbGvPrefix + "FVG_Age", (double)g_sbFVG.barAge);

      if(g_sbFVG.barAge > SB_FVG_MAX_WAIT)
      {
         PrintFormat("[SB] FVG expired after %d bars (%s)", SB_FVG_MAX_WAIT, symbol);
         SB_ResetFVG();
         return;
      }

      SB_TryFVGEntry(atr, riskPct, maxLot);
   }
}

//+------------------------------------------------------------------+
//| Get current kill zone from broker hour                           |
//+------------------------------------------------------------------+
ENUM_SB_KZ_TYPE SB_GetCurrentKZ(int hour)
{
   if(SB_USE_LDN  && hour >= SB_LDN_START  && hour < SB_LDN_END)  return SB_KZ_LONDON;
   if(SB_USE_NYAM && hour >= SB_NYAM_START && hour < SB_NYAM_END) return SB_KZ_NY_AM;
   if(SB_USE_NYPM && hour >= SB_NYPM_START && hour < SB_NYPM_END) return SB_KZ_NY_PM;
   return SB_KZ_NONE;
}

//+------------------------------------------------------------------+
//| Scan for displacement candle + FVG (bars 1/2/3, closed-bar)     |
//| FVG pattern: bar[2] is displacement candle                       |
//|   Bullish: gap between bar[3].high and bar[1].low                |
//|   Bearish: gap between bar[3].low  and bar[1].high               |
//+------------------------------------------------------------------+
void SB_ScanForDisplacementFVG(double atr, ENUM_SB_KZ_TYPE kz,
                                double riskPct, double maxLot)
{
   // --- Displacement candle is bar[2] ---
   double open2  = iOpen(g_sbSymbol,  PERIOD_M15, 2);
   double close2 = iClose(g_sbSymbol, PERIOD_M15, 2);
   double high2  = iHigh(g_sbSymbol,  PERIOD_M15, 2);
   double low2   = iLow(g_sbSymbol,   PERIOD_M15, 2);
   double range2 = high2 - low2;
   if(range2 <= 0) return;

   double body2 = MathAbs(close2 - open2);
   if(body2 < SB_DISP_BODY_ATR * atr)   return;
   if(body2 / range2 < SB_DISP_BODY_RATIO) return;

   bool isBullDisp = (close2 > open2);

   double high3 = iHigh(g_sbSymbol, PERIOD_M15, 3);
   double low3  = iLow(g_sbSymbol,  PERIOD_M15, 3);
   double high1 = iHigh(g_sbSymbol, PERIOD_M15, 1);
   double low1  = iLow(g_sbSymbol,  PERIOD_M15, 1);

   double fvgUpper = 0, fvgLower = 0;
   bool hasFVG    = false;
   bool fvgBull   = false;

   if(isBullDisp)
   {
      // Gap: bar[3].high to bar[1].low (price jumped up leaving a void)
      fvgLower = high3;
      fvgUpper = low1;
      if(fvgUpper > fvgLower)
      {
         double fvgSize = fvgUpper - fvgLower;
         if(fvgSize >= SB_FVG_MIN_SIZE * atr)
         {
            hasFVG  = true;
            fvgBull = true;
         }
      }
   }
   else
   {
      // Gap: bar[3].low to bar[1].high (price dropped leaving a void)
      fvgUpper = low3;
      fvgLower = high1;
      if(fvgUpper > fvgLower)
      {
         double fvgSize = fvgUpper - fvgLower;
         if(fvgSize >= SB_FVG_MIN_SIZE * atr)
         {
            hasFVG  = true;
            fvgBull = false;
         }
      }
   }

   if(!hasFVG) return;

   // --- HTF Bias: price must be on correct side of H4 EMA ---
   if(SB_USE_HTF_BIAS && g_sbHhtfEma != INVALID_HANDLE)
   {
      double emaBuf[];
      if(CopyBuffer(g_sbHhtfEma, 0, 1, 1, emaBuf) < 1) return;
      double h4ema  = emaBuf[0];
      double price1 = iClose(g_sbSymbol, PERIOD_M15, 1);

      if(fvgBull && price1 < h4ema)
      {
         PrintFormat("[SB] Skip: Bullish FVG but price below H4 EMA (%.5f < %.5f)",
                     price1, h4ema);
         return;
      }
      if(!fvgBull && price1 > h4ema)
      {
         PrintFormat("[SB] Skip: Bearish FVG but price above H4 EMA (%.5f > %.5f)",
                     price1, h4ema);
         return;
      }
   }

   // --- Store pending FVG ---
   g_sbFVG.upper      = fvgUpper;
   g_sbFVG.lower      = fvgLower;
   g_sbFVG.isBullish  = fvgBull;
   g_sbFVG.createTime = TimeCurrent();
   g_sbFVG.barAge     = 0;
   g_sbFVG.active     = true;
   g_sbFVG.sourceKZ   = kz;
   SB_SaveFVGState();

   string kzName = (kz == SB_KZ_LONDON) ? "London"
                 : (kz == SB_KZ_NY_AM)  ? "NY_AM"
                 :                          "NY_PM";

   int dig = (int)SymbolInfoInteger(g_sbSymbol, SYMBOL_DIGITS);
   PrintFormat("[SB] FVG detected: %s | Zone: %.5f-%.5f | KZ: %s | DispBody: %.2fATR",
               fvgBull ? "BULLISH" : "BEARISH",
               DoubleToString(fvgLower, dig),
               DoubleToString(fvgUpper, dig),
               kzName,
               body2 / atr);
}

//+------------------------------------------------------------------+
//| Attempt entry when current bar fills the pending FVG             |
//+------------------------------------------------------------------+
void SB_TryFVGEntry(double atr, double riskPct, double maxLot)
{
   if(g_sbTradesToday  >= SB_MAX_TRADES_DAY) return;
   if(g_sbTradesThisKZ >= SB_MAX_TRADES_KZ)  return;
   if(SB_CountMyPositions() > 0) return;

   double close1 = iClose(g_sbSymbol, PERIOD_M15, 1);
   double low1   = iLow(g_sbSymbol,   PERIOD_M15, 1);
   double high1  = iHigh(g_sbSymbol,  PERIOD_M15, 1);

   bool filled = false;
   if(g_sbFVG.isBullish)
   {
      // Bar[1] wicked into the FVG and closed above its lower edge
      if(low1 <= g_sbFVG.upper && close1 >= g_sbFVG.lower)
         filled = true;
   }
   else
   {
      // Bar[1] wicked into the FVG and closed below its upper edge
      if(high1 >= g_sbFVG.lower && close1 <= g_sbFVG.upper)
         filled = true;
   }
   if(!filled) return;

   // --- Spread check ---
   g_sbSym.Name(g_sbSymbol);
   g_sbSym.RefreshRates();
   double spreadPips = (double)g_sbSym.Spread() * g_sbPt / g_sbPipSize;
   if(spreadPips > SB_MAX_SPREAD_PIPS)
   {
      PrintFormat("[SB] Skip: spread %.1f pips > max %.1f", spreadPips, SB_MAX_SPREAD_PIPS);
      return;
   }

   // --- Entry price ---
   bool   isBuy     = g_sbFVG.isBullish;
   double entryPrice = isBuy ? g_sbSym.Ask() : g_sbSym.Bid();

   // --- SL distance: FVG edge + 20% ATR buffer ---
   double slDist;
   if(isBuy)
      slDist = entryPrice - g_sbFVG.lower + SB_SL_ATR * atr * 0.2;
   else
      slDist = g_sbFVG.upper - entryPrice + SB_SL_ATR * atr * 0.2;

   // Clamp SL to pip range
   double slPips = slDist / g_sbPipSize;
   if(slPips < SB_MIN_SL_PIPS)
      slDist = SB_MIN_SL_PIPS * g_sbPipSize;
   if(slPips > SB_MAX_SL_PIPS)
   {
      PrintFormat("[SB] Skip: SL %.1f pips > max %.1f", slPips, SB_MAX_SL_PIPS);
      SB_ResetFVG();
      return;
   }

   // --- Session-specific R:R ---
   double rrRatio = SB_TP_RR_DEFAULT;
   if(g_sbFVG.sourceKZ == SB_KZ_LONDON)
      rrRatio = SB_TP_RR_LDN;
   else if(g_sbFVG.sourceKZ == SB_KZ_NY_AM || g_sbFVG.sourceKZ == SB_KZ_NY_PM)
      rrRatio = SB_TP_RR_NY;

   double tpDist = slDist * rrRatio;

   // --- SL / TP prices ---
   int    dig = (int)SymbolInfoInteger(g_sbSymbol, SYMBOL_DIGITS);
   double sl, tp;
   if(isBuy)
   {
      sl = NormalizeDouble(entryPrice - slDist, dig);
      tp = NormalizeDouble(entryPrice + tpDist, dig);
   }
   else
   {
      sl = NormalizeDouble(entryPrice + slDist, dig);
      tp = NormalizeDouble(entryPrice - tpDist, dig);
   }

   // --- Broker stop/freeze level check ---
   long   stopLvlPts  = SymbolInfoInteger(g_sbSymbol, SYMBOL_TRADE_STOPS_LEVEL);
   long   freezeLvlPts = SymbolInfoInteger(g_sbSymbol, SYMBOL_TRADE_FREEZE_LEVEL);
   double minStopDist = MathMax((double)stopLvlPts, (double)freezeLvlPts) * g_sbPt;

   if(MathAbs(entryPrice - sl) < minStopDist)
   {
      PrintFormat("[SB] Skip: SL too close for broker (stopLevel=%I64d freezeLevel=%I64d)",
                  stopLvlPts, freezeLvlPts);
      SB_ResetFVG();
      return;
   }
   if(MathAbs(tp - entryPrice) < minStopDist)
   {
      PrintFormat("[SB] Skip: TP too close for broker");
      SB_ResetFVG();
      return;
   }

   // --- Position sizing (equity-based, symbol-aware) ---
   double tickValue = SymbolInfoDouble(g_sbSymbol, SYMBOL_TRADE_TICK_VALUE);
   double tickSize  = SymbolInfoDouble(g_sbSymbol, SYMBOL_TRADE_TICK_SIZE);
   if(tickValue <= 0 || tickSize <= 0)
   {
      Print("[SB] Skip: invalid tick value/size");
      return;
   }

   double riskMoney = AccountInfoDouble(ACCOUNT_EQUITY) * riskPct / 100.0;
   double lotRaw    = riskMoney / (slDist / tickSize * tickValue);

   double lotMin  = SymbolInfoDouble(g_sbSymbol, SYMBOL_VOLUME_MIN);
   double lotMax  = SymbolInfoDouble(g_sbSymbol, SYMBOL_VOLUME_MAX);
   double lotStep = SymbolInfoDouble(g_sbSymbol, SYMBOL_VOLUME_STEP);

   double lots = MathFloor(lotRaw / lotStep) * lotStep;
   lots = MathMax(lots, lotMin);
   lots = MathMin(lots, MathMin(lotMax, maxLot));
   if(lots < lotMin)
   {
      Print("[SB] Skip: lot below minimum");
      return;
   }

   // --- Execute with bounded retry + backoff ---
   PrintFormat("[SB] ENTRY: %s | lots=%.2f | SL=%.5f | TP=%.5f | RR=%.1f | FVG=%.5f-%.5f",
               isBuy ? "BUY" : "SELL", lots, sl, tp, rrRatio,
               g_sbFVG.lower, g_sbFVG.upper);

   for(int attempt = 1; attempt <= SB_RETRY_COUNT; attempt++)
   {
      g_sbSym.RefreshRates();
      // Refresh entry price on each retry
      entryPrice = isBuy ? g_sbSym.Ask() : g_sbSym.Bid();

      bool ok;
      if(isBuy)
         ok = g_sbTrade.Buy(lots, g_sbSymbol, 0, sl, tp, SB_TRADE_COMMENT);
      else
         ok = g_sbTrade.Sell(lots, g_sbSymbol, 0, sl, tp, SB_TRADE_COMMENT);

      uint retcode = g_sbTrade.ResultRetcode();

      if(ok && retcode == TRADE_RETCODE_DONE)
      {
         g_sbTradesToday++;
         g_sbTradesThisKZ++;
         g_sbInitialSLDist = slDist;
         PrintFormat("[SB] Order done: ticket=%I64u attempt=%d",
                     g_sbTrade.ResultOrder(), attempt);
         SB_ResetFVG();
         return;
      }

      // Transient — worth retrying
      if(retcode == TRADE_RETCODE_REQUOTE    ||
         retcode == TRADE_RETCODE_PRICE_OFF  ||
         retcode == TRADE_RETCODE_CONNECTION ||
         retcode == TRADE_RETCODE_TIMEOUT)
      {
         PrintFormat("[SB] Retry %d/%d retcode=%u comment=%s",
                     attempt, SB_RETRY_COUNT, retcode, g_sbTrade.ResultComment());
         if(attempt < SB_RETRY_COUNT)
            Sleep(SB_RETRY_DELAY_MS * attempt);
         continue;
      }

      // Non-transient — abort
      PrintFormat("[SB] Order FAILED (non-transient) retcode=%u comment=%s",
                  retcode, g_sbTrade.ResultComment());
      break;
   }

   // On any failure path, expire FVG to avoid re-triggering
   SB_ResetFVG();
}

//+------------------------------------------------------------------+
//| Count open positions belonging to this module                    |
//+------------------------------------------------------------------+
int SB_CountMyPositions()
{
   int count = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      if(!g_sbPos.SelectByIndex(i)) continue;
      if(g_sbPos.Magic()  == g_sbMagic &&
         g_sbPos.Symbol() == g_sbSymbol)
         count++;
   }
   return count;
}

//+------------------------------------------------------------------+
//| Close all positions belonging to this module                     |
//+------------------------------------------------------------------+
void SB_CloseAllPositions()
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      if(!g_sbPos.SelectByIndex(i)) continue;
      if(g_sbPos.Magic()  == g_sbMagic &&
         g_sbPos.Symbol() == g_sbSymbol)
         g_sbTrade.PositionClose(g_sbPos.Ticket());
   }
}

//+------------------------------------------------------------------+
//| Detect best fill mode for symbol                                 |
//+------------------------------------------------------------------+
ENUM_ORDER_TYPE_FILLING SB_DetectFillMode(string symbol)
{
   long modes = SymbolInfoInteger(symbol, SYMBOL_FILLING_MODE);
   if((modes & SYMBOL_FILLING_FOK) != 0) return ORDER_FILLING_FOK;
   if((modes & SYMBOL_FILLING_IOC) != 0) return ORDER_FILLING_IOC;
   return ORDER_FILLING_RETURN;
}

//+------------------------------------------------------------------+
//| FVG STATE — GlobalVariable persistence for crash recovery        |
//+------------------------------------------------------------------+
void SB_ResetFVG()
{
   g_sbFVG.active     = false;
   g_sbFVG.upper      = 0;
   g_sbFVG.lower      = 0;
   g_sbFVG.isBullish  = false;
   g_sbFVG.createTime = 0;
   g_sbFVG.barAge     = 0;
   g_sbFVG.sourceKZ   = SB_KZ_NONE;
   if(StringLen(g_sbGvPrefix) > 0)
      SB_CleanFVGState();
}

void SB_SaveFVGState()
{
   GlobalVariableSet(g_sbGvPrefix + "FVG_Active",  (double)g_sbFVG.active);
   GlobalVariableSet(g_sbGvPrefix + "FVG_Upper",   g_sbFVG.upper);
   GlobalVariableSet(g_sbGvPrefix + "FVG_Lower",   g_sbFVG.lower);
   GlobalVariableSet(g_sbGvPrefix + "FVG_IsBull",  (double)g_sbFVG.isBullish);
   GlobalVariableSet(g_sbGvPrefix + "FVG_Create",  (double)g_sbFVG.createTime);
   GlobalVariableSet(g_sbGvPrefix + "FVG_Age",     (double)g_sbFVG.barAge);
   GlobalVariableSet(g_sbGvPrefix + "FVG_KZ",      (double)g_sbFVG.sourceKZ);
}

bool SB_RestoreFVGState()
{
   if(!GlobalVariableCheck(g_sbGvPrefix + "FVG_Active"))
      return false;

   double active = GlobalVariableGet(g_sbGvPrefix + "FVG_Active");
   if(active < 0.5) return false;

   datetime savedCreate = (datetime)GlobalVariableGet(g_sbGvPrefix + "FVG_Create");
   datetime now         = TimeCurrent();

   // FVG older than 3 hours is stale — discard
   if(now - savedCreate > 3 * 3600)
   {
      PrintFormat("[SB] GV: Stale FVG discarded (age=%d sec)", (int)(now - savedCreate));
      SB_CleanFVGState();
      return false;
   }

   g_sbFVG.active     = true;
   g_sbFVG.upper      = GlobalVariableGet(g_sbGvPrefix + "FVG_Upper");
   g_sbFVG.lower      = GlobalVariableGet(g_sbGvPrefix + "FVG_Lower");
   g_sbFVG.isBullish  = (GlobalVariableGet(g_sbGvPrefix + "FVG_IsBull") > 0.5);
   g_sbFVG.createTime = savedCreate;
   g_sbFVG.barAge     = (int)GlobalVariableGet(g_sbGvPrefix + "FVG_Age");
   g_sbFVG.sourceKZ   = (ENUM_SB_KZ_TYPE)(int)GlobalVariableGet(g_sbGvPrefix + "FVG_KZ");

   PrintFormat("[SB] GV: FVG restored — %s zone %.5f-%.5f age=%d KZ=%d",
               g_sbFVG.isBullish ? "BULL" : "BEAR",
               g_sbFVG.lower, g_sbFVG.upper,
               g_sbFVG.barAge, (int)g_sbFVG.sourceKZ);
   return true;
}

void SB_CleanFVGState()
{
   GlobalVariableDel(g_sbGvPrefix + "FVG_Active");
   GlobalVariableDel(g_sbGvPrefix + "FVG_Upper");
   GlobalVariableDel(g_sbGvPrefix + "FVG_Lower");
   GlobalVariableDel(g_sbGvPrefix + "FVG_IsBull");
   GlobalVariableDel(g_sbGvPrefix + "FVG_Create");
   GlobalVariableDel(g_sbGvPrefix + "FVG_Age");
   GlobalVariableDel(g_sbGvPrefix + "FVG_KZ");
}

#endif // SB_MODULE_MQH
