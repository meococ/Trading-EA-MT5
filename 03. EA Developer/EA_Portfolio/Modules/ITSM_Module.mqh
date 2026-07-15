//+------------------------------------------------------------------+
//| ITSM_Module.mqh                                                   |
//| Intraday Trend Scalp Momentum — Sonic R Wave Pullback             |
//| Self-contained module extracted from EA_ITSM v3.0                 |
//| for use inside EA_Portfolio master EA.                            |
//|                                                                    |
//| Interface:                                                         |
//|   ITSM_Init(symbol, magic, deviation)  -> bool                    |
//|   ITSM_Deinit()                                                   |
//|   ITSM_OnTick(symbol, magic, riskPct, maxLot)                    |
//|                                                                    |
//| All state variables prefixed g_itsm_.                             |
//| No external dependencies: no EQL_, no PCL_, no HolidayCalendar.  |
//| PERIOD_M15 is hardcoded; _Symbol replaced by explicit parameter.  |
//|                                                                    |
//| Max & Ngai Meo Coc | 2026-04-01 | extracted from EA_ITSM v3.0   |
//+------------------------------------------------------------------+
#ifndef ITSM_MODULE_MQH
#define ITSM_MODULE_MQH

#include <Trade\Trade.mqh>
#include <Trade\PositionInfo.mqh>
#include <Trade\SymbolInfo.mqh>

//+------------------------------------------------------------------+
//| COMPILE-TIME DEFAULTS (all overridable at portfolio level)        |
//+------------------------------------------------------------------+

// EMA periods — Sonic R wave
#define ITSM_EMA_FAST1        5
#define ITSM_EMA_FAST2        13
#define ITSM_EMA_ZONE_UPPER   34
#define ITSM_EMA_ZONE_LOWER   89

// ATR
#define ITSM_ATR_PERIOD       14

// Kill zones (broker hours)
#define ITSM_KZ1_START_H      9
#define ITSM_KZ1_START_M      0
#define ITSM_KZ1_END_H        12
#define ITSM_KZ1_END_M        0
#define ITSM_KZ2_START_H      15
#define ITSM_KZ2_START_M      0
#define ITSM_KZ2_END_H        18
#define ITSM_KZ2_END_M        0

// SL / TP
#define ITSM_SL_ATR_MULT      0.5
#define ITSM_RR_RATIO         1.5

// Time exit
#define ITSM_EXIT_HOUR        20
#define ITSM_EXIT_MINUTE      0

// Max trades per day
#define ITSM_MAX_TRADES_DAY   1

// Pullback lookback bars
#define ITSM_LOOKBACK         5

// Min bounce body (ATR multiples)
#define ITSM_MIN_BODY_ATR     0.3

// DD kill (portfolio guard will override externally; kept for standalone safety)
#define ITSM_MAX_DD_PCT       50.0

// Optional confluence defaults — matching EA_ITSM v3 input defaults
#define ITSM_USE_MACD         false
#define ITSM_MACD_FAST        12
#define ITSM_MACD_SLOW        26
#define ITSM_MACD_SIGNAL      9

#define ITSM_USE_RSI          false
#define ITSM_RSI_PERIOD       14
#define ITSM_RSI_OB           75.0
#define ITSM_RSI_OS           25.0

#define ITSM_USE_ADX          false
#define ITSM_ADX_PERIOD       14
#define ITSM_ADX_MIN          20.0

#define ITSM_USE_HTF_BIAS     false
#define ITSM_HTF_EMA          50

#define ITSM_USE_ZONE_WIDTH   false
#define ITSM_ZONE_WIDTH_MIN   0.2
#define ITSM_ZONE_WIDTH_MAX   2.0

#define ITSM_USE_VOL_REGIME   false
#define ITSM_VOL_ATR_MIN_PCT  30.0
#define ITSM_VOL_ATR_LOOKBACK 100

#define ITSM_USE_EMA_SLOPE    false
#define ITSM_EMA_SLOPE_MIN    0.0

#define ITSM_USE_TRAIL        false
#define ITSM_TRAIL_ATR        1.0
#define ITSM_TRAIL_START      1.0

#define ITSM_USE_BE           false
#define ITSM_BE_TRIGGER       1.0

#define ITSM_STRICT_ALIGN     false
#define ITSM_REQUIRE_TOUCH    true
#define ITSM_ZONE_BUFFER_ATR  0.0
#define ITSM_BOUNCE_CLOSE_DIR true
#define ITSM_USE_KZ2          true
#define ITSM_USE_TIME_EXIT    true

// Day filter defaults
#define ITSM_TRADE_MON        true
#define ITSM_TRADE_TUE        true
#define ITSM_TRADE_WED        true
#define ITSM_TRADE_THU        true
#define ITSM_TRADE_FRI        false

// Execution
#define ITSM_MAX_RETRIES      3

//+------------------------------------------------------------------+
//| MODULE STATE — all variables prefixed g_itsm_                    |
//+------------------------------------------------------------------+
static CTrade         g_itsm_trade;
static CPositionInfo  g_itsm_pos;
static CSymbolInfo    g_itsm_sym;

static int  g_itsm_atrHandle    = INVALID_HANDLE;
static int  g_itsm_emaF1Handle  = INVALID_HANDLE;
static int  g_itsm_emaF2Handle  = INVALID_HANDLE;
static int  g_itsm_emaZUHandle  = INVALID_HANDLE;
static int  g_itsm_emaZLHandle  = INVALID_HANDLE;
static int  g_itsm_macdHandle   = INVALID_HANDLE;
static int  g_itsm_rsiHandle    = INVALID_HANDLE;
static int  g_itsm_adxHandle    = INVALID_HANDLE;
static int  g_itsm_htfEmaHandle = INVALID_HANDLE;

static double g_itsm_atrBuf[];
static double g_itsm_emaF1Buf[];
static double g_itsm_emaF2Buf[];
static double g_itsm_emaZUBuf[];
static double g_itsm_emaZLBuf[];
static double g_itsm_macdMainBuf[];
static double g_itsm_rsiBuf[];
static double g_itsm_adxBuf[];
static double g_itsm_htfEmaBuf[];

static datetime g_itsm_lastTradeDate  = 0;
static datetime g_itsm_lastBar        = 0;
static double   g_itsm_peakEquity     = 0.0;
static bool     g_itsm_ddKillTriggered = false;
static ulong    g_itsm_magic          = 0;

//+------------------------------------------------------------------+
//| Forward declarations                                              |
//+------------------------------------------------------------------+
int    ITSM_GetTrendDirection(int shift);
bool   ITSM_InKillZone(const MqlDateTime &dt);
bool   ITSM_IsTradingDay(int dow);
bool   ITSM_HasPositionOpen(string symbol, ulong magic);
void   ITSM_CheckTimeExit(string symbol, ulong magic);
void   ITSM_ManageBreakEven(string symbol, ulong magic);
void   ITSM_ManageTrailingStop(string symbol, ulong magic);
void   ITSM_CheckDDKill(string symbol, ulong magic);
double ITSM_CalcLotSize(string symbol, double riskPoints, double riskPct, double maxLot);

//+------------------------------------------------------------------+
//| ITSM_Init                                                         |
//| Call from EA OnInit(). Returns false on failure.                  |
//+------------------------------------------------------------------+
bool ITSM_Init(string symbol, ulong magic, int deviation)
{
   g_itsm_magic          = magic;
   g_itsm_ddKillTriggered = false;
   g_itsm_lastTradeDate  = 0;
   g_itsm_lastBar        = 0;

   if(!g_itsm_sym.Name(symbol))
   {
      Print("[ITSM] Symbol init failed: ", symbol);
      return false;
   }
   g_itsm_sym.Refresh();

   g_itsm_trade.SetExpertMagicNumber(magic);
   g_itsm_trade.SetDeviationInPoints(deviation);

   // Adaptive fill mode
   ENUM_ORDER_TYPE_FILLING fillMode = ORDER_FILLING_FOK;
   uint filling = (uint)SymbolInfoInteger(symbol, SYMBOL_FILLING_MODE);
   if((filling & SYMBOL_FILLING_IOC) != 0)
      fillMode = ORDER_FILLING_IOC;
   g_itsm_trade.SetTypeFilling(fillMode);

   // Core indicator handles — all on PERIOD_M15, explicit symbol
   g_itsm_atrHandle   = iATR(symbol, PERIOD_M15, ITSM_ATR_PERIOD);
   g_itsm_emaF1Handle = iMA(symbol, PERIOD_M15, ITSM_EMA_FAST1,      0, MODE_EMA, PRICE_CLOSE);
   g_itsm_emaF2Handle = iMA(symbol, PERIOD_M15, ITSM_EMA_FAST2,      0, MODE_EMA, PRICE_CLOSE);
   g_itsm_emaZUHandle = iMA(symbol, PERIOD_M15, ITSM_EMA_ZONE_UPPER, 0, MODE_EMA, PRICE_CLOSE);
   g_itsm_emaZLHandle = iMA(symbol, PERIOD_M15, ITSM_EMA_ZONE_LOWER, 0, MODE_EMA, PRICE_CLOSE);

   if(g_itsm_atrHandle   == INVALID_HANDLE ||
      g_itsm_emaF1Handle == INVALID_HANDLE ||
      g_itsm_emaF2Handle == INVALID_HANDLE ||
      g_itsm_emaZUHandle == INVALID_HANDLE ||
      g_itsm_emaZLHandle == INVALID_HANDLE)
   {
      Print("[ITSM] Core indicator handle creation failed for ", symbol);
      return false;
   }

   ArraySetAsSeries(g_itsm_atrBuf,   true);
   ArraySetAsSeries(g_itsm_emaF1Buf, true);
   ArraySetAsSeries(g_itsm_emaF2Buf, true);
   ArraySetAsSeries(g_itsm_emaZUBuf, true);
   ArraySetAsSeries(g_itsm_emaZLBuf, true);

   // Optional confluence handles
   if(ITSM_USE_MACD)
   {
      g_itsm_macdHandle = iMACD(symbol, PERIOD_M15, ITSM_MACD_FAST, ITSM_MACD_SLOW, ITSM_MACD_SIGNAL, PRICE_CLOSE);
      if(g_itsm_macdHandle == INVALID_HANDLE) { Print("[ITSM] MACD handle failed"); return false; }
      ArraySetAsSeries(g_itsm_macdMainBuf, true);
   }
   if(ITSM_USE_RSI)
   {
      g_itsm_rsiHandle = iRSI(symbol, PERIOD_M15, ITSM_RSI_PERIOD, PRICE_CLOSE);
      if(g_itsm_rsiHandle == INVALID_HANDLE) { Print("[ITSM] RSI handle failed"); return false; }
      ArraySetAsSeries(g_itsm_rsiBuf, true);
   }
   if(ITSM_USE_ADX)
   {
      g_itsm_adxHandle = iADX(symbol, PERIOD_M15, ITSM_ADX_PERIOD);
      if(g_itsm_adxHandle == INVALID_HANDLE) { Print("[ITSM] ADX handle failed"); return false; }
      ArraySetAsSeries(g_itsm_adxBuf, true);
   }
   if(ITSM_USE_HTF_BIAS)
   {
      // H4 EMA for higher-timeframe directional bias — no repaint concern: shift=1 used on read
      g_itsm_htfEmaHandle = iMA(symbol, PERIOD_H4, ITSM_HTF_EMA, 0, MODE_EMA, PRICE_CLOSE);
      if(g_itsm_htfEmaHandle == INVALID_HANDLE) { Print("[ITSM] H4 EMA handle failed"); return false; }
      ArraySetAsSeries(g_itsm_htfEmaBuf, true);
   }

   g_itsm_peakEquity = AccountInfoDouble(ACCOUNT_EQUITY);

   Print("[ITSM] v3.0 Module initialized | Symbol=", symbol,
         " | M15 | EMAs: ", ITSM_EMA_FAST1, "/", ITSM_EMA_FAST2, "/",
         ITSM_EMA_ZONE_UPPER, "/", ITSM_EMA_ZONE_LOWER,
         " | KZ1: ", ITSM_KZ1_START_H, ":00-", ITSM_KZ1_END_H, ":00",
         " | KZ2: ", ITSM_KZ2_START_H, ":00-", ITSM_KZ2_END_H, ":00",
         " | R:R ", ITSM_RR_RATIO,
         " | Magic: ", magic);

   return true;
}

//+------------------------------------------------------------------+
//| ITSM_Deinit                                                       |
//| Call from EA OnDeinit(). Releases all indicator handles.          |
//+------------------------------------------------------------------+
void ITSM_Deinit()
{
   if(g_itsm_atrHandle    != INVALID_HANDLE) { IndicatorRelease(g_itsm_atrHandle);    g_itsm_atrHandle    = INVALID_HANDLE; }
   if(g_itsm_emaF1Handle  != INVALID_HANDLE) { IndicatorRelease(g_itsm_emaF1Handle);  g_itsm_emaF1Handle  = INVALID_HANDLE; }
   if(g_itsm_emaF2Handle  != INVALID_HANDLE) { IndicatorRelease(g_itsm_emaF2Handle);  g_itsm_emaF2Handle  = INVALID_HANDLE; }
   if(g_itsm_emaZUHandle  != INVALID_HANDLE) { IndicatorRelease(g_itsm_emaZUHandle);  g_itsm_emaZUHandle  = INVALID_HANDLE; }
   if(g_itsm_emaZLHandle  != INVALID_HANDLE) { IndicatorRelease(g_itsm_emaZLHandle);  g_itsm_emaZLHandle  = INVALID_HANDLE; }
   if(g_itsm_macdHandle   != INVALID_HANDLE) { IndicatorRelease(g_itsm_macdHandle);   g_itsm_macdHandle   = INVALID_HANDLE; }
   if(g_itsm_rsiHandle    != INVALID_HANDLE) { IndicatorRelease(g_itsm_rsiHandle);    g_itsm_rsiHandle    = INVALID_HANDLE; }
   if(g_itsm_adxHandle    != INVALID_HANDLE) { IndicatorRelease(g_itsm_adxHandle);    g_itsm_adxHandle    = INVALID_HANDLE; }
   if(g_itsm_htfEmaHandle != INVALID_HANDLE) { IndicatorRelease(g_itsm_htfEmaHandle); g_itsm_htfEmaHandle = INVALID_HANDLE; }

   Print("[ITSM] Module deinitialized");
}

//+------------------------------------------------------------------+
//| ITSM_OnTick                                                       |
//| Call from EA OnTick(). riskPct and maxLot come from master.       |
//+------------------------------------------------------------------+
void ITSM_OnTick(string symbol, ulong magic, double riskPct, double maxLot)
{
   if(g_itsm_ddKillTriggered) return;

   // Minimum bars guard
   if(Bars(symbol, PERIOD_M15) < ITSM_EMA_ZONE_LOWER + 50) return;

   // DD check — uses portfolio equity; will close ITSM positions if triggered
   ITSM_CheckDDKill(symbol, magic);
   if(g_itsm_ddKillTriggered) return;

   // Per-tick position management — before new-bar gate
   if(ITSM_USE_TIME_EXIT)
      ITSM_CheckTimeExit(symbol, magic);

   if(ITSM_USE_BE)
      ITSM_ManageBreakEven(symbol, magic);

   if(ITSM_USE_TRAIL)
      ITSM_ManageTrailingStop(symbol, magic);

   // New-bar gate — all signal logic runs on closed bar (shift=1)
   datetime curBar = iTime(symbol, PERIOD_M15, 0);
   if(curBar == g_itsm_lastBar) return;
   g_itsm_lastBar = curBar;

   // Position already open?
   if(ITSM_HasPositionOpen(symbol, magic)) return;

   // Already traded today?
   MqlDateTime dt;
   TimeCurrent(dt);
   datetime today = StringToTime(StringFormat("%04d.%02d.%02d", dt.year, dt.mon, dt.day));
   if(g_itsm_lastTradeDate == today) return;

   // Day filter
   if(!ITSM_IsTradingDay(dt.day_of_week)) return;

   // Kill Zone filter
   if(!ITSM_InKillZone(dt)) return;

   // Copy core indicator buffers (shift=1..lookback+2, so need lookback+3 values starting at shift=1)
   int need = ITSM_LOOKBACK + 3;
   if(CopyBuffer(g_itsm_atrHandle,   0, 1, need, g_itsm_atrBuf)   < need) return;
   if(CopyBuffer(g_itsm_emaF1Handle, 0, 1, need, g_itsm_emaF1Buf) < need) return;
   if(CopyBuffer(g_itsm_emaF2Handle, 0, 1, need, g_itsm_emaF2Buf) < need) return;
   if(CopyBuffer(g_itsm_emaZUHandle, 0, 1, need, g_itsm_emaZUBuf) < need) return;
   if(CopyBuffer(g_itsm_emaZLHandle, 0, 1, need, g_itsm_emaZLBuf) < need) return;

   double atr = g_itsm_atrBuf[0];    // ATR at shift=1 (closed bar)
   double pt  = SymbolInfoDouble(symbol, SYMBOL_POINT);
   if(atr < pt * 10) return;

   // Zone boundaries at shift=1 (closed bar EMA values)
   double zoneTop    = MathMax(g_itsm_emaZUBuf[0], g_itsm_emaZLBuf[0]);
   double zoneBottom = MathMin(g_itsm_emaZUBuf[0], g_itsm_emaZLBuf[0]);
   double zoneBuffer = ITSM_ZONE_BUFFER_ATR * atr;

   // Trend direction from EMA alignment at shift=1
   int trend = ITSM_GetTrendDirection(0);  // index 0 = shift=1 in as-series buffers
   if(trend == 0) return;

   // Closed bar OHLC (shift=1)
   double bounceClose = iClose(symbol, PERIOD_M15, 1);
   double bounceOpen  = iOpen(symbol,  PERIOD_M15, 1);
   double bounceHigh  = iHigh(symbol,  PERIOD_M15, 1);
   double bounceLow   = iLow(symbol,   PERIOD_M15, 1);
   double bodySize    = MathAbs(bounceClose - bounceOpen);

   // Bounce body quality gate
   if(ITSM_MIN_BODY_ATR > 0 && bodySize < ITSM_MIN_BODY_ATR * atr) return;

   bool isBuy  = false;
   bool isSell = false;

   if(trend > 0) // Bullish trend
   {
      // Bounce candle must be bullish
      if(ITSM_BOUNCE_CLOSE_DIR && bounceClose <= bounceOpen) return;

      // Bounce bar must close ABOVE zone top
      if(bounceClose <= zoneTop) return;

      // Look back for pullback into zone from above (shift=2..LOOKBACK+1)
      bool hadPullback = false;
      for(int i = 1; i <= ITSM_LOOKBACK; i++)
      {
         double lo           = iLow(symbol, PERIOD_M15, 1 + i);
         double localZoneTop = MathMax(g_itsm_emaZUBuf[i], g_itsm_emaZLBuf[i]);
         double localZoneBot = MathMin(g_itsm_emaZUBuf[i], g_itsm_emaZLBuf[i]);

         if(ITSM_REQUIRE_TOUCH)
         {
            if(lo <= localZoneTop + zoneBuffer)
            {
               hadPullback = true;
               break;
            }
         }
         else
         {
            double cl = iClose(symbol, PERIOD_M15, 1 + i);
            if(cl <= localZoneTop + atr)
            {
               hadPullback = true;
               break;
            }
         }
      }
      if(!hadPullback) return;
      isBuy = true;
   }
   else // Bearish trend
   {
      // Bounce candle must be bearish
      if(ITSM_BOUNCE_CLOSE_DIR && bounceClose >= bounceOpen) return;

      // Bounce bar must close BELOW zone bottom
      if(bounceClose >= zoneBottom) return;

      bool hadPullback = false;
      for(int i = 1; i <= ITSM_LOOKBACK; i++)
      {
         double hi           = iHigh(symbol, PERIOD_M15, 1 + i);
         double localZoneTop = MathMax(g_itsm_emaZUBuf[i], g_itsm_emaZLBuf[i]);
         double localZoneBot = MathMin(g_itsm_emaZUBuf[i], g_itsm_emaZLBuf[i]);

         if(ITSM_REQUIRE_TOUCH)
         {
            if(hi >= localZoneBot - zoneBuffer)
            {
               hadPullback = true;
               break;
            }
         }
         else
         {
            double cl = iClose(symbol, PERIOD_M15, 1 + i);
            if(cl >= localZoneBot - atr)
            {
               hadPullback = true;
               break;
            }
         }
      }
      if(!hadPullback) return;
      isSell = true;
   }

   if(!isBuy && !isSell) return;

   //--- v3 CONFLUENCE FILTERS (all on closed bar, shift=1, no repaint) ---

   // 1. MACD histogram direction agrees with trend
   if(ITSM_USE_MACD)
   {
      double macdBuf[2];
      if(CopyBuffer(g_itsm_macdHandle, 0, 1, 2, macdBuf) < 2) return;
      if(isBuy  && macdBuf[0] < 0) return;
      if(isSell && macdBuf[0] > 0) return;
   }

   // 2. RSI exhaustion guard
   if(ITSM_USE_RSI)
   {
      double rsiBuf[2];
      if(CopyBuffer(g_itsm_rsiHandle, 0, 1, 2, rsiBuf) < 2) return;
      double rsiVal = rsiBuf[0];
      if(isBuy  && rsiVal > ITSM_RSI_OB) return;
      if(isSell && rsiVal < ITSM_RSI_OS) return;
   }

   // 3. ADX trend strength
   if(ITSM_USE_ADX)
   {
      double adxBuf[2];
      if(CopyBuffer(g_itsm_adxHandle, 0, 1, 2, adxBuf) < 2) return;
      if(adxBuf[0] < ITSM_ADX_MIN) return;
   }

   // 4. H4 EMA directional bias (shift=1 on H4 = no repaint)
   if(ITSM_USE_HTF_BIAS)
   {
      double htfBuf[2];
      if(CopyBuffer(g_itsm_htfEmaHandle, 0, 1, 2, htfBuf) < 2) return;
      if(isBuy  && bounceClose < htfBuf[0]) return;
      if(isSell && bounceClose > htfBuf[0]) return;
   }

   // 5. Zone width filter
   if(ITSM_USE_ZONE_WIDTH)
   {
      double zoneWidth = zoneTop - zoneBottom;
      if(zoneWidth < ITSM_ZONE_WIDTH_MIN * atr) return;
      if(zoneWidth > ITSM_ZONE_WIDTH_MAX * atr) return;
   }

   // 6. Volatility regime filter
   if(ITSM_USE_VOL_REGIME)
   {
      double atrHistory[];
      ArraySetAsSeries(atrHistory, true);
      if(CopyBuffer(g_itsm_atrHandle, 0, 1, ITSM_VOL_ATR_LOOKBACK, atrHistory) >= ITSM_VOL_ATR_LOOKBACK)
      {
         int countBelow = 0;
         for(int j = 1; j < ITSM_VOL_ATR_LOOKBACK; j++)
         {
            if(atrHistory[j] < atr) countBelow++;
         }
         double percentile = (double)countBelow / (ITSM_VOL_ATR_LOOKBACK - 1) * 100.0;
         if(percentile < ITSM_VOL_ATR_MIN_PCT) return;
      }
   }

   // 7. EMA89 slope filter (trend gradient quality)
   if(ITSM_USE_EMA_SLOPE)
   {
      if(g_itsm_emaZLBuf[0] != 0 && g_itsm_emaZLBuf[3] != 0)
      {
         double slope = (g_itsm_emaZLBuf[0] - g_itsm_emaZLBuf[3]) / 3.0 / pt;
         if(isBuy  && slope < ITSM_EMA_SLOPE_MIN)  return;
         if(isSell && (-slope) < ITSM_EMA_SLOPE_MIN) return;
      }
   }

   //--- SL / TP / ENTRY CALCULATION ---

   double ask = SymbolInfoDouble(symbol, SYMBOL_ASK);
   double bid = SymbolInfoDouble(symbol, SYMBOL_BID);
   if(ask <= 0 || bid <= 0) return;
   double spread = ask - bid;

   int    stopLevel  = (int)SymbolInfoInteger(symbol, SYMBOL_TRADE_STOPS_LEVEL);
   int    freezeLevel= (int)SymbolInfoInteger(symbol, SYMBOL_TRADE_FREEZE_LEVEL);
   double minDist    = MathMax(stopLevel, freezeLevel) * pt + spread;
   int    digits     = (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS);

   double sl, tp, entry, slRisk;

   if(isBuy)
   {
      entry   = ask;
      sl      = zoneBottom - ITSM_SL_ATR_MULT * atr;
      slRisk  = entry - sl;
      if(slRisk < minDist) slRisk = minDist;
      sl      = NormalizeDouble(entry - slRisk, digits);
      tp      = ITSM_USE_TRAIL ? 0 : NormalizeDouble(entry + slRisk * ITSM_RR_RATIO, digits);
   }
   else
   {
      entry   = bid;
      sl      = zoneTop + ITSM_SL_ATR_MULT * atr;
      slRisk  = sl - entry;
      if(slRisk < minDist) slRisk = minDist;
      sl      = NormalizeDouble(entry + slRisk, digits);
      tp      = ITSM_USE_TRAIL ? 0 : NormalizeDouble(entry - slRisk * ITSM_RR_RATIO, digits);
   }

   slRisk = MathAbs(entry - sl);

   double lots = ITSM_CalcLotSize(symbol, slRisk, riskPct, maxLot);
   if(lots <= 0) return;

   Print("[ITSM] SIGNAL: ", (isBuy ? "BUY" : "SELL"),
         " | trend=", trend,
         " | bounceClose=", DoubleToString(bounceClose, digits),
         " | zoneTop=", DoubleToString(zoneTop, digits),
         " | zoneBot=", DoubleToString(zoneBottom, digits),
         " | EMA5=", DoubleToString(g_itsm_emaF1Buf[0], digits),
         " | EMA13=", DoubleToString(g_itsm_emaF2Buf[0], digits),
         " | lots=", lots,
         " | entry=", entry,
         " | SL=", sl, " TP=", tp);

   //--- ORDER EXECUTION with retry ---

   bool filled  = false;
   uint retcode = 0;

   for(int attempt = 1; attempt <= ITSM_MAX_RETRIES; attempt++)
   {
      double curAsk = SymbolInfoDouble(symbol, SYMBOL_ASK);
      double curBid = SymbolInfoDouble(symbol, SYMBOL_BID);

      if(isBuy)
      {
         if(g_itsm_trade.Buy(lots, symbol, curAsk, sl, tp, "ITSM"))
         {
            retcode = g_itsm_trade.ResultRetcode();
            if(retcode == TRADE_RETCODE_DONE)
            {
               filled = true;
               break;
            }
         }
         else
            retcode = g_itsm_trade.ResultRetcode();
      }
      else
      {
         if(g_itsm_trade.Sell(lots, symbol, curBid, sl, tp, "ITSM"))
         {
            retcode = g_itsm_trade.ResultRetcode();
            if(retcode == TRADE_RETCODE_DONE)
            {
               filled = true;
               break;
            }
         }
         else
            retcode = g_itsm_trade.ResultRetcode();
      }

      if(retcode == TRADE_RETCODE_NO_MONEY) break;
      Print("[ITSM] Order attempt ", attempt, " failed: ", retcode);
      if(attempt < ITSM_MAX_RETRIES) Sleep(200 * (int)MathPow(2, attempt - 1));
   }

   if(filled)
   {
      g_itsm_lastTradeDate = today;
      Print("[ITSM] FILLED: ", (isBuy ? "BUY" : "SELL"), " ", lots, " lots",
            " | SL=", sl, " TP=", tp,
            " | ATR=", DoubleToString(atr / pt, 0), " pts");
   }
   else
   {
      Print("[ITSM] Order FAILED after ", ITSM_MAX_RETRIES, " attempts | last retcode=", retcode);
   }
}

//+------------------------------------------------------------------+
//| ITSM_GetTrendDirection                                            |
//| Returns: +1 = bullish, -1 = bearish, 0 = no clear trend         |
//| shift here is an index into the as-series buffers (0 = shift=1) |
//+------------------------------------------------------------------+
int ITSM_GetTrendDirection(int shift)
{
   double emaF1 = g_itsm_emaF1Buf[shift];
   double emaF2 = g_itsm_emaF2Buf[shift];
   double emaZU = g_itsm_emaZUBuf[shift];  // EMA34
   double emaZL = g_itsm_emaZLBuf[shift];  // EMA89

   double zoneTop = MathMax(emaZU, emaZL);
   double zoneBot = MathMin(emaZU, emaZL);

   if(ITSM_STRICT_ALIGN)
   {
      // Strict: full Sonic R stack — EMA5 > EMA13 > EMA34 > EMA89 (bull) or reverse (bear)
      if(emaF1 > emaF2 && emaF2 > emaZU && emaZU > emaZL)
         return +1;
      if(emaF1 < emaF2 && emaF2 < emaZU && emaZU < emaZL)
         return -1;
      return 0;
   }
   else
   {
      // Loose: fast EMAs both outside zone in same direction as zone slope
      if(emaF1 > zoneTop && emaF2 > zoneTop && emaZU > emaZL)
         return +1;
      if(emaF1 < zoneBot && emaF2 < zoneBot && emaZU < emaZL)
         return -1;
      return 0;
   }
}

//+------------------------------------------------------------------+
//| ITSM_InKillZone                                                   |
//+------------------------------------------------------------------+
bool ITSM_InKillZone(const MqlDateTime &dt)
{
   int minutes  = dt.hour * 60 + dt.min;
   int kz1Start = ITSM_KZ1_START_H * 60 + ITSM_KZ1_START_M;
   int kz1End   = ITSM_KZ1_END_H   * 60 + ITSM_KZ1_END_M;

   if(minutes >= kz1Start && minutes < kz1End) return true;

   if(ITSM_USE_KZ2)
   {
      int kz2Start = ITSM_KZ2_START_H * 60 + ITSM_KZ2_START_M;
      int kz2End   = ITSM_KZ2_END_H   * 60 + ITSM_KZ2_END_M;
      if(minutes >= kz2Start && minutes < kz2End) return true;
   }

   return false;
}

//+------------------------------------------------------------------+
//| ITSM_IsTradingDay                                                 |
//| dow: 0=Sun 1=Mon 2=Tue 3=Wed 4=Thu 5=Fri 6=Sat                  |
//+------------------------------------------------------------------+
bool ITSM_IsTradingDay(int dow)
{
   switch(dow)
   {
      case 1: return ITSM_TRADE_MON;
      case 2: return ITSM_TRADE_TUE;
      case 3: return ITSM_TRADE_WED;
      case 4: return ITSM_TRADE_THU;
      case 5: return ITSM_TRADE_FRI;
      default: return false;
   }
}

//+------------------------------------------------------------------+
//| ITSM_HasPositionOpen                                              |
//+------------------------------------------------------------------+
bool ITSM_HasPositionOpen(string symbol, ulong magic)
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      if(g_itsm_pos.SelectByIndex(i))
      {
         if(g_itsm_pos.Symbol() == symbol && g_itsm_pos.Magic() == magic)
            return true;
      }
   }
   return false;
}

//+------------------------------------------------------------------+
//| ITSM_CheckTimeExit                                                |
//| Closes all ITSM positions at or after ITSM_EXIT_HOUR:MINUTE.     |
//+------------------------------------------------------------------+
void ITSM_CheckTimeExit(string symbol, ulong magic)
{
   MqlDateTime dt;
   TimeCurrent(dt);
   int curMinutes  = dt.hour * 60 + dt.min;
   int exitMinutes = ITSM_EXIT_HOUR * 60 + ITSM_EXIT_MINUTE;

   if(curMinutes < exitMinutes) return;

   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      if(g_itsm_pos.SelectByIndex(i))
      {
         if(g_itsm_pos.Symbol() == symbol && g_itsm_pos.Magic() == magic)
         {
            g_itsm_trade.PositionClose(g_itsm_pos.Ticket());
            Print("[ITSM] Time exit at ", dt.hour, ":", StringFormat("%02d", dt.min));
         }
      }
   }
}

//+------------------------------------------------------------------+
//| ITSM_ManageBreakEven                                              |
//+------------------------------------------------------------------+
void ITSM_ManageBreakEven(string symbol, ulong magic)
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      if(!g_itsm_pos.SelectByIndex(i)) continue;
      if(g_itsm_pos.Symbol() != symbol || g_itsm_pos.Magic() != magic) continue;

      double openPrice = g_itsm_pos.PriceOpen();
      double sl        = g_itsm_pos.StopLoss();
      double tp        = g_itsm_pos.TakeProfit();
      double risk      = MathAbs(openPrice - sl);
      double pt        = SymbolInfoDouble(symbol, SYMBOL_POINT);
      int    digits    = (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS);

      if(risk < pt) continue;

      double beTrigger = risk * ITSM_BE_TRIGGER;

      if(g_itsm_pos.PositionType() == POSITION_TYPE_BUY)
      {
         if(sl >= openPrice) continue;
         double profit = SymbolInfoDouble(symbol, SYMBOL_BID) - openPrice;
         if(profit >= beTrigger)
         {
            double newSL = NormalizeDouble(openPrice + pt, digits);
            g_itsm_trade.PositionModify(g_itsm_pos.Ticket(), newSL, tp);
            Print("[ITSM] BE moved to ", newSL);
         }
      }
      else
      {
         if(sl <= openPrice && sl > 0) continue;
         double profit = openPrice - SymbolInfoDouble(symbol, SYMBOL_ASK);
         if(profit >= beTrigger)
         {
            double newSL = NormalizeDouble(openPrice - pt, digits);
            g_itsm_trade.PositionModify(g_itsm_pos.Ticket(), newSL, tp);
            Print("[ITSM] BE moved to ", newSL);
         }
      }
   }
}

//+------------------------------------------------------------------+
//| ITSM_ManageTrailingStop                                           |
//+------------------------------------------------------------------+
void ITSM_ManageTrailingStop(string symbol, ulong magic)
{
   double atrVal[1];
   // shift=1 to avoid live-bar ATR (non-repaint safe)
   if(CopyBuffer(g_itsm_atrHandle, 0, 1, 1, atrVal) < 1) return;
   double trailDist = ITSM_TRAIL_ATR * atrVal[0];

   int    digits = (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS);
   double pt     = SymbolInfoDouble(symbol, SYMBOL_POINT);

   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      if(!g_itsm_pos.SelectByIndex(i)) continue;
      if(g_itsm_pos.Symbol() != symbol || g_itsm_pos.Magic() != magic) continue;

      double openPrice     = g_itsm_pos.PriceOpen();
      double sl            = g_itsm_pos.StopLoss();
      double tp            = g_itsm_pos.TakeProfit();
      double risk          = MathAbs(openPrice - sl);
      if(risk < pt) continue;

      double trailActivate = risk * ITSM_TRAIL_START;

      if(g_itsm_pos.PositionType() == POSITION_TYPE_BUY)
      {
         double curPrice = SymbolInfoDouble(symbol, SYMBOL_BID);
         double profit   = curPrice - openPrice;
         if(profit < trailActivate) continue;

         double newSL = NormalizeDouble(curPrice - trailDist, digits);
         if(newSL > sl + pt)
            g_itsm_trade.PositionModify(g_itsm_pos.Ticket(), newSL, tp);
      }
      else
      {
         double curPrice = SymbolInfoDouble(symbol, SYMBOL_ASK);
         double profit   = openPrice - curPrice;
         if(profit < trailActivate) continue;

         double newSL = NormalizeDouble(curPrice + trailDist, digits);
         if(newSL < sl - pt || sl == 0)
            g_itsm_trade.PositionModify(g_itsm_pos.Ticket(), newSL, tp);
      }
   }
}

//+------------------------------------------------------------------+
//| ITSM_CheckDDKill                                                  |
//| Uses portfolio equity. Set ITSM_MAX_DD_PCT high (50%) so the     |
//| portfolio-level guard fires first in normal operation.            |
//+------------------------------------------------------------------+
void ITSM_CheckDDKill(string symbol, ulong magic)
{
   double equity = AccountInfoDouble(ACCOUNT_EQUITY);
   if(equity > g_itsm_peakEquity) g_itsm_peakEquity = equity;

   if(g_itsm_peakEquity > 0)
   {
      double dd = (g_itsm_peakEquity - equity) / g_itsm_peakEquity * 100.0;
      if(dd >= ITSM_MAX_DD_PCT)
      {
         g_itsm_ddKillTriggered = true;
         Print("[ITSM] DD KILL: DD=", DoubleToString(dd, 1), "% >= ", ITSM_MAX_DD_PCT, "%");
         for(int i = PositionsTotal() - 1; i >= 0; i--)
         {
            if(g_itsm_pos.SelectByIndex(i))
            {
               if(g_itsm_pos.Symbol() == symbol && g_itsm_pos.Magic() == magic)
                  g_itsm_trade.PositionClose(g_itsm_pos.Ticket());
            }
         }
      }
   }
}

//+------------------------------------------------------------------+
//| ITSM_CalcLotSize                                                  |
//| riskPoints: distance from entry to SL in price units.            |
//| riskPct / maxLot: provided by master EA at call time.            |
//+------------------------------------------------------------------+
double ITSM_CalcLotSize(string symbol, double riskPoints, double riskPct, double maxLot)
{
   if(riskPoints <= 0) return 0;

   double balance   = AccountInfoDouble(ACCOUNT_BALANCE);
   double riskMoney = balance * riskPct / 100.0;

   double tickValue = SymbolInfoDouble(symbol, SYMBOL_TRADE_TICK_VALUE);
   double tickSize  = SymbolInfoDouble(symbol, SYMBOL_TRADE_TICK_SIZE);
   if(tickValue <= 0 || tickSize <= 0) return 0;

   double lots = riskMoney / (riskPoints / tickSize * tickValue);

   double minLot  = SymbolInfoDouble(symbol, SYMBOL_VOLUME_MIN);
   double maxSymLot = SymbolInfoDouble(symbol, SYMBOL_VOLUME_MAX);
   double stepLot = SymbolInfoDouble(symbol, SYMBOL_VOLUME_STEP);

   if(lots < minLot) return 0;
   if(lots > maxLot)    lots = maxLot;
   if(lots > maxSymLot) lots = maxSymLot;

   lots = MathFloor(lots / stepLot) * stepLot;
   return NormalizeDouble(lots, 2);
}

#endif // ITSM_MODULE_MQH
//+------------------------------------------------------------------+
