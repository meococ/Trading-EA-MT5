//+------------------------------------------------------------------+
//| LNY_Module.mqh — London→NY Momentum Continuation                 |
//| Self-contained module extracted from EA_LondonNY v1.0            |
//| For use inside EA_Portfolio master EA only.                       |
//|                                                                   |
//| EDGE: If London session creates a directional move > 0.5 × D1    |
//| ATR in first 3 hours, NY AM session continues that direction      |
//| ~58-64% of time.  Entry on NY pullback bounce (closed-bar).       |
//|                                                                   |
//| Interface:                                                        |
//|   bool LNY_Init(string symbol, ulong magic, int deviation)        |
//|   void LNY_Deinit()                                               |
//|   void LNY_OnTick(string symbol, ulong magic,                     |
//|                   double riskPct, double maxLot)                  |
//|                                                                   |
//| Max | 2026-04-01 | extracted from EA_LondonNY v1.0               |
//+------------------------------------------------------------------+
#ifndef LNY_MODULE_MQH
#define LNY_MODULE_MQH

#include "Portfolio_Common.mqh"

//+------------------------------------------------------------------+
//| COMPILE-TIME PARAMETERS (mirrors EA_LondonNY v1.0 inputs)        |
//+------------------------------------------------------------------+

// London trend measurement
#define LNY_LDN_START_H       9       // London open capture hour (broker)
#define LNY_LDN_START_M       0
#define LNY_LDN_MEASURE_H     12      // Trend measured at this hour (3h after open)
#define LNY_LDN_MEASURE_M     0
#define LNY_TREND_ATR_MULT    0.50    // Min London move as D1-ATR multiple
#define LNY_ATR_PERIOD        14      // ATR period on D1

// NY pullback entry window
#define LNY_NY_START_H        15      // NY entry window open (broker)
#define LNY_NY_START_M        0
#define LNY_NY_END_H          18      // NY entry window close
#define LNY_NY_END_M          0

// Pullback geometry
#define LNY_PB_LOOKBACK       3       // Max bars to scan for pullback extreme
#define LNY_PB_MIN_ATR        0.15    // Pullback must be >= this × D1 ATR
#define LNY_PB_MAX_ATR        0.60    // Pullback must be <= this × D1 ATR

// Stop-loss and reward
#define LNY_SL_ATR_MULT       0.5     // SL = pullback extreme ± ATR × this
#define LNY_RR_RATIO          2.0     // Risk : Reward

// Time exit
#define LNY_EXIT_H            20      // Force-close all positions at this hour
#define LNY_EXIT_M            0

// Break-even (disabled by default — portfolio guard overrides)
#define LNY_USE_BE            false
#define LNY_BE_TRIGGER        1.0     // Trigger in R multiples

// EMA trend filter (disabled by default)
#define LNY_USE_EMA           false
#define LNY_EMA_PERIOD        50      // EMA period on M15

// Day filter — all days enabled
#define LNY_TRADE_MON         true
#define LNY_TRADE_TUE         true
#define LNY_TRADE_WED         true
#define LNY_TRADE_THU         true
#define LNY_TRADE_FRI         true

// DD kill (research guard — portfolio-level guard takes priority in master)
#define LNY_MAX_DD_PCT        99.0

// Trade comment prefix
#define LNY_COMMENT           "LdnNY"

//+------------------------------------------------------------------+
//| MODULE GLOBALS (all prefixed g_lny)                              |
//+------------------------------------------------------------------+
CTrade    g_lnyTrade;

int       g_lnyHandleATR_D1  = INVALID_HANDLE;
int       g_lnyHandleEMA_M15 = INVALID_HANDLE;
double    g_lnyInitialBalance = 0;

// Daily state — must persist across bars within the same calendar day
double    g_lnyLondonOpen         = 0;     // Captured at LDN_START_H:00
double    g_lnyLondonDirection    = 0;     // +1 bullish, -1 bearish, 0 none
bool      g_lnyBiasSet            = false; // true once measurement window passed
bool      g_lnyTradeEnteredToday  = false; // max 1 trade per day
datetime  g_lnyLastTradeDay       = 0;     // which day the state above belongs to

//+------------------------------------------------------------------+
//| LNY_Init                                                          |
//| Creates indicator handles and configures the module trade object. |
//| symbol   : target symbol (e.g. "USDJPY")                         |
//| magic    : unique magic number assigned by master EA              |
//| deviation: slippage in points                                     |
//+------------------------------------------------------------------+
bool LNY_Init(string symbol, ulong magic, int deviation)
{
   // Indicator handles
   g_lnyHandleATR_D1  = iATR(symbol, PERIOD_D1, LNY_ATR_PERIOD);
   g_lnyHandleEMA_M15 = iMA(symbol, PERIOD_M15, LNY_EMA_PERIOD, 0, MODE_EMA, PRICE_CLOSE);

   if(g_lnyHandleATR_D1 == INVALID_HANDLE || g_lnyHandleEMA_M15 == INVALID_HANDLE)
   {
      PrintFormat("[LNY] ERROR: indicator handle failed for %s", symbol);
      return false;
   }

   // Configure trade object
   PF_SetupTrade(g_lnyTrade, magic, symbol, deviation);

   // Capture baseline balance for local DD guard
   g_lnyInitialBalance = AccountInfoDouble(ACCOUNT_BALANCE);

   // Reset daily state
   g_lnyLondonOpen        = 0;
   g_lnyLondonDirection   = 0;
   g_lnyBiasSet           = false;
   g_lnyTradeEnteredToday = false;
   g_lnyLastTradeDay      = 0;

   PrintFormat("[LNY] Initialized. symbol=%s magic=%I64u", symbol, magic);
   return true;
}

//+------------------------------------------------------------------+
//| LNY_Deinit                                                        |
//| Releases indicator handles.                                       |
//+------------------------------------------------------------------+
void LNY_Deinit()
{
   if(g_lnyHandleATR_D1  != INVALID_HANDLE) { IndicatorRelease(g_lnyHandleATR_D1);  g_lnyHandleATR_D1  = INVALID_HANDLE; }
   if(g_lnyHandleEMA_M15 != INVALID_HANDLE) { IndicatorRelease(g_lnyHandleEMA_M15); g_lnyHandleEMA_M15 = INVALID_HANDLE; }
}

//+------------------------------------------------------------------+
//| LNY_IsTradingDay — internal helper                               |
//+------------------------------------------------------------------+
bool LNY_IsTradingDay()
{
   MqlDateTime dt;
   TimeToStruct(TimeCurrent(), dt);
   return PF_IsTradingDay(dt.day_of_week,
                          LNY_TRADE_MON, LNY_TRADE_TUE, LNY_TRADE_WED,
                          LNY_TRADE_THU, LNY_TRADE_FRI);
}

//+------------------------------------------------------------------+
//| LNY_PipSize — symbol-aware pip size                              |
//+------------------------------------------------------------------+
double LNY_PipSize(string symbol)
{
   double pt = SymbolInfoDouble(symbol, SYMBOL_POINT);
   if(StringFind(symbol, "JPY") >= 0) return pt * 100.0;
   return pt * 10.0;
}

//+------------------------------------------------------------------+
//| LNY_OnTick                                                        |
//| Main logic — call from master EA OnTick() for every tick.        |
//| symbol   : same symbol passed to LNY_Init                        |
//| magic    : same magic passed to LNY_Init                         |
//| riskPct  : per-trade risk as % of balance (from master)          |
//| maxLot   : hard lot ceiling (from master)                        |
//+------------------------------------------------------------------+
void LNY_OnTick(string symbol, ulong magic, double riskPct, double maxLot)
{
   // ── Closed-bar gate (must come FIRST to get bar time) ──────────
   static datetime s_lnyLastBar = 0;
   datetime curBar = iTime(symbol, PERIOD_M15, 0);
   if(curBar == s_lnyLastBar) return;
   s_lnyLastBar = curBar;

   // ── Daily state reset — derived from bar time, not TimeCurrent() ──
   MqlDateTime barDt;
   TimeToStruct(curBar, barDt);
   datetime today = StringToTime(StringFormat("%04d.%02d.%02d", barDt.year, barDt.mon, barDt.day));

   if(today != g_lnyLastTradeDay)
   {
      g_lnyLastTradeDay      = today;
      g_lnyLondonDirection   = 0;
      g_lnyBiasSet           = false;
      g_lnyTradeEnteredToday = false;
      g_lnyLondonOpen        = 0;
   }

   // ── Day filter (use bar time, not TimeCurrent) ──────────────────
   if(!PF_IsTradingDay(barDt.day_of_week,
                       LNY_TRADE_MON, LNY_TRADE_TUE, LNY_TRADE_WED,
                       LNY_TRADE_THU, LNY_TRADE_FRI))
      return;

   // ── Local DD guard (portfolio guard is the real gate in master) ─
   double equity = AccountInfoDouble(ACCOUNT_EQUITY);
   if(g_lnyInitialBalance > 0 && equity < g_lnyInitialBalance * (1.0 - LNY_MAX_DD_PCT / 100.0))
      return;

   // ── Time helpers — derived from the symbol's bar time, NOT TimeCurrent() ──
   // In multi-symbol tester, TimeCurrent() follows chart symbol ticks and
   // may skip narrow time windows for cross-symbols. Using the M15 bar's
   // open time guarantees we check each USDJPY bar exactly once.
   int h = barDt.hour;
   int m = barDt.min;
   int nowMins        = h * 60 + m;
   int ldnStartMins   = LNY_LDN_START_H   * 60 + LNY_LDN_START_M;
   int ldnMeasureMins = LNY_LDN_MEASURE_H * 60 + LNY_LDN_MEASURE_M;
   int nyStartMins    = LNY_NY_START_H    * 60 + LNY_NY_START_M;
   int nyEndMins      = LNY_NY_END_H      * 60 + LNY_NY_END_M;

   // ──────────────────────────────────────────────────────────────
   // Phase 1: Capture London open price at 09:00 bar
   // ──────────────────────────────────────────────────────────────
   if(g_lnyLondonOpen == 0 && nowMins >= ldnStartMins && nowMins < ldnStartMins + 15)
   {
      g_lnyLondonOpen = iOpen(symbol, PERIOD_M15, 0);
   }

   // ──────────────────────────────────────────────────────────────
   // Phase 2: Measure London trend at 12:00 bar
   //   close[1] vs londonOpen — use shift=1 (closed bar, no repaint)
   // ──────────────────────────────────────────────────────────────
   if(!g_lnyBiasSet && g_lnyLondonOpen > 0 &&
      nowMins >= ldnMeasureMins && nowMins < ldnMeasureMins + 15)
   {
      double close1 = iClose(symbol, PERIOD_M15, 1);
      double move   = close1 - g_lnyLondonOpen;

      double atr[];
      if(CopyBuffer(g_lnyHandleATR_D1, 0, 1, 1, atr) < 1) return;

      double threshold = atr[0] * LNY_TREND_ATR_MULT;

      if(move > threshold)
      {
         g_lnyLondonDirection = 1;
         g_lnyBiasSet         = true;
         PrintFormat("[LNY] BULLISH bias %s. move=%.5f threshold=%.5f",
                     symbol, move, threshold);
      }
      else if(move < -threshold)
      {
         g_lnyLondonDirection = -1;
         g_lnyBiasSet         = true;
         PrintFormat("[LNY] BEARISH bias %s. move=%.5f threshold=%.5f",
                     symbol, move, threshold);
      }
      else
      {
         g_lnyBiasSet = true;  // window passed, no usable bias today
         PrintFormat("[LNY] NO BIAS %s. move=%.5f < threshold=%.5f",
                     symbol, move, threshold);
      }
   }

   // ──────────────────────────────────────────────────────────────
   // Phase 3: NY pullback entry (15:00 – 18:00)
   //   Conditions:
   //     - London bias confirmed (direction != 0)
   //     - No trade yet today
   //     - No open position for this magic
   //     - Pullback depth within [PB_MIN_ATR, PB_MAX_ATR] × D1 ATR
   //     - Most recent closed bar bounces in bias direction
   // ──────────────────────────────────────────────────────────────
   if(g_lnyBiasSet && g_lnyLondonDirection != 0 && !g_lnyTradeEnteredToday &&
      nowMins >= nyStartMins && nowMins < nyEndMins &&
      PF_CountPositions(magic, symbol) == 0)
   {
      double atr[];
      if(CopyBuffer(g_lnyHandleATR_D1, 0, 1, 1, atr) < 1) return;

      double close1 = iClose(symbol, PERIOD_M15, 1);
      double open1  = iOpen(symbol, PERIOD_M15, 1);

      // Scan lookback bars for pullback extreme
      double recentHigh = -999999.0;
      double recentLow  =  999999.0;

      for(int i = 1; i <= LNY_PB_LOOKBACK; i++)
      {
         double hi = iHigh(symbol, PERIOD_M15, i);
         double lo = iLow(symbol,  PERIOD_M15, i);
         if(hi > recentHigh) recentHigh = hi;
         if(lo < recentLow)  recentLow  = lo;
      }

      double pullbackDepth = recentHigh - recentLow;
      bool   validPullback = false;
      double pbExtreme     = 0;

      if(g_lnyLondonDirection > 0)
      {
         // Bullish bias: expect dip then bounce up
         // Bounce confirmation: last closed bar is bullish (close > open)
         if(pullbackDepth >= atr[0] * LNY_PB_MIN_ATR &&
            pullbackDepth <= atr[0] * LNY_PB_MAX_ATR &&
            close1 > open1)
         {
            validPullback = true;
            pbExtreme     = recentLow;
         }
      }
      else // g_lnyLondonDirection < 0
      {
         // Bearish bias: expect bounce then rejection down
         // Rejection confirmation: last closed bar is bearish (close < open)
         if(pullbackDepth >= atr[0] * LNY_PB_MIN_ATR &&
            pullbackDepth <= atr[0] * LNY_PB_MAX_ATR &&
            close1 < open1)
         {
            validPullback = true;
            pbExtreme     = recentHigh;
         }
      }

      // Optional EMA filter (disabled by default per LNY_USE_EMA = false)
      if(validPullback && LNY_USE_EMA)
      {
         double ema[];
         if(CopyBuffer(g_lnyHandleEMA_M15, 0, 1, 1, ema) < 1) return;

         if(g_lnyLondonDirection > 0 && close1 < ema[0]) validPullback = false;
         if(g_lnyLondonDirection < 0 && close1 > ema[0]) validPullback = false;
      }

      // ── Execute entry ──────────────────────────────────────────
      if(validPullback)
      {
         double pipSize   = LNY_PipSize(symbol);
         double point     = SymbolInfoDouble(symbol, SYMBOL_POINT);
         int    stopLevel = (int)SymbolInfoInteger(symbol, SYMBOL_TRADE_STOPS_LEVEL);
         double minDist   = stopLevel * point;

         if(g_lnyLondonDirection > 0) // BUY
         {
            double ask   = SymbolInfoDouble(symbol, SYMBOL_ASK);
            double sl    = pbExtreme - atr[0] * LNY_SL_ATR_MULT;
            double slPips = (ask - sl) / pipSize;
            double tp    = ask + slPips * LNY_RR_RATIO * pipSize;

            // Enforce broker stop-level minimum
            if(MathAbs(ask - sl) < minDist) sl = ask - minDist - point;
            if(MathAbs(tp - ask) < minDist) tp = ask + minDist + point;

            if(slPips <= 0) return;
            double lots = PF_CalcLotSize(symbol, riskPct, ask - sl, maxLot);
            if(lots <= 0) return;

            bool filled = false;
            for(int attempt = 1; attempt <= 3; attempt++)
            {
               if(g_lnyTrade.Buy(lots, symbol, ask, sl, tp, LNY_COMMENT + "_BUY"))
               {
                  filled = true;
                  break;
               }
               if(attempt < 3) Sleep(200 * (int)MathPow(2, attempt - 1));
            }

            if(filled)
            {
               PrintFormat("[LNY] BUY %s lots=%.2f ask=%.5f sl=%.5f tp=%.5f",
                           symbol, lots, ask, sl, tp);
               g_lnyTradeEnteredToday = true;
            }
            else
            {
               PrintFormat("[LNY] BUY FAILED %s retcode=%d", symbol, g_lnyTrade.ResultRetcode());
            }
         }
         else // SELL
         {
            double bid   = SymbolInfoDouble(symbol, SYMBOL_BID);
            double sl    = pbExtreme + atr[0] * LNY_SL_ATR_MULT;
            double slPips = (sl - bid) / pipSize;
            double tp    = bid - slPips * LNY_RR_RATIO * pipSize;

            // Enforce broker stop-level minimum
            if(MathAbs(sl - bid) < minDist) sl = bid + minDist + point;
            if(MathAbs(bid - tp) < minDist) tp = bid - minDist - point;

            if(slPips <= 0) return;
            double lots = PF_CalcLotSize(symbol, riskPct, sl - bid, maxLot);
            if(lots <= 0) return;

            bool filled = false;
            for(int attempt = 1; attempt <= 3; attempt++)
            {
               if(g_lnyTrade.Sell(lots, symbol, bid, sl, tp, LNY_COMMENT + "_SELL"))
               {
                  filled = true;
                  break;
               }
               if(attempt < 3) Sleep(200 * (int)MathPow(2, attempt - 1));
            }

            if(filled)
            {
               PrintFormat("[LNY] SELL %s lots=%.2f bid=%.5f sl=%.5f tp=%.5f",
                           symbol, lots, bid, sl, tp);
               g_lnyTradeEnteredToday = true;
            }
            else
            {
               PrintFormat("[LNY] SELL FAILED %s retcode=%d", symbol, g_lnyTrade.ResultRetcode());
            }
         }
      } // validPullback
   } // Phase 3

   // ──────────────────────────────────────────────────────────────
   // Phase 4: Break-even management (disabled by default)
   // ──────────────────────────────────────────────────────────────
   if(LNY_USE_BE && PF_CountPositions(magic, symbol) > 0)
   {
      PF_ManageBE(g_lnyTrade, magic, symbol, LNY_BE_TRIGGER);
   }

   // ──────────────────────────────────────────────────────────────
   // Phase 5: Time exit — force-close all positions at LNY_EXIT_H
   // ──────────────────────────────────────────────────────────────
   if(PF_CountPositions(magic, symbol) > 0)
   {
      if(h >= LNY_EXIT_H && m >= LNY_EXIT_M)
      {
         PF_CloseAll(g_lnyTrade, magic, symbol);
         PrintFormat("[LNY] TimeExit %s at %02d:%02d", symbol, h, m);
      }
   }
}

#endif // LNY_MODULE_MQH
//+------------------------------------------------------------------+
