//+------------------------------------------------------------------+
//| EA_ITSM.mq5                                                      |
//| Intraday Trend Scalp Momentum — Sonic R Wave Pullback             |
//| Copyright 2026, Max & Ngai Meo Coc                                |
//|                                                                    |
//| EDGE HYPOTHESIS (v3 — Sonic R + confluence filters):              |
//| v2 found USDJPY NY-only PF 1.22 (S509).                           |
//| v3 adds optional confluence filters to boost selectivity:          |
//|  - MACD histogram momentum confirmation                            |
//|  - RSI hidden divergence at zone (continuation signal)             |
//|  - ADX trend strength gate (skip weak trends)                      |
//|  - Zone width filter (skip consolidation/too narrow)               |
//|  - H4 EMA directional bias (multi-timeframe)                      |
//|  - ATR volatility regime filter (skip dead days)                   |
//|  - Trailing stop alternative to fixed R:R                          |
//|  - EMA slope momentum filter (gradient-based trend quality)        |
//|                                                                    |
//| SIGNAL (closed bar only, shift=1):                                |
//| - Trend confirmed by EMA alignment                                 |
//| - Previous bar(s) touched or entered EMA zone                     |
//| - Current closed bar exits zone in trend direction                 |
//| - Optional: MACD confirms, RSI no divergence, ADX strong           |
//|                                                                    |
//| Targets: USDJPY M15 NY session (primary edge)                     |
//| Max | 2026-03-30 | v3.0                                          |
//+------------------------------------------------------------------+
#property copyright "Max & Ngai Meo Coc"
#property link      ""
#property version   "3.00"
#property strict

#include <Trade\Trade.mqh>
#include <Trade\PositionInfo.mqh>
#include <Trade\SymbolInfo.mqh>
#include <ExecQualityLog.mqh>
#include <HolidayCalendar.mqh>

//+------------------------------------------------------------------+
//| INPUTS                                                             |
//+------------------------------------------------------------------+
input group "=== Core Settings ==="
input bool   InpEnabled        = true;       // EA Enabled (kill switch)
input double InpRiskPct        = 1.0;        // Risk % per trade
input double InpMaxLot         = 1.00;       // Max lot size
input int    InpMagic          = 20260331;   // Magic number
input string InpComment        = "ITSM";     // Trade comment

// --- EMA Wave Settings ---
input group "=== EMA Wave (Sonic R) ==="
input int    InpEMA_Fast1      = 5;          // EMA Fast 1 period
input int    InpEMA_Fast2      = 13;         // EMA Fast 2 period
input int    InpEMA_ZoneUpper  = 34;         // EMA Zone Upper (wave midline)
input int    InpEMA_ZoneLower  = 89;         // EMA Zone Lower (wave baseline)
input bool   InpStrictAlign    = false;      // Require strict 4-EMA alignment (loose = just zone direction)

// --- Pullback Detection ---
input group "=== Pullback Settings ==="
input int    InpLookback       = 5;          // Max bars to look back for zone touch
input bool   InpRequireTouch   = true;       // Require price actually touched/entered zone (not just near)
input double InpZoneBufferATR  = 0.0;        // Zone buffer (ATR multiples, 0 = exact zone)

// --- Kill Zone / Session ---
input group "=== Kill Zone ==="
input int    InpKZ1_StartH     = 9;          // KZ1 start hour (broker time, London)
input int    InpKZ1_StartM     = 0;          // KZ1 start minute
input int    InpKZ1_EndH       = 12;         // KZ1 end hour (broker time)
input int    InpKZ1_EndM       = 0;          // KZ1 end minute
input int    InpKZ2_StartH     = 15;         // KZ2 start hour (broker time, NY AM)
input int    InpKZ2_StartM     = 0;          // KZ2 start minute
input int    InpKZ2_EndH       = 18;         // KZ2 end hour (broker time)
input int    InpKZ2_EndM       = 0;          // KZ2 end minute
input bool   InpUseKZ2         = true;       // Enable KZ2 (NY session)

// --- SL / TP ---
input group "=== SL/TP ==="
input double InpSL_ATR_Mult    = 0.5;        // SL = zone edge + ATR × this
input double InpRR_Ratio       = 1.5;        // Risk:Reward ratio for TP
input int    InpATR_Period     = 14;         // ATR period
input bool   InpUseTimeExit    = true;       // Use time-based exit
input int    InpExitHour       = 20;         // Exit hour (broker time)
input int    InpExitMinute     = 0;          // Exit minute
input bool   InpUseBE          = false;      // Use break-even stop
input double InpBE_Trigger     = 1.0;        // BE trigger (R multiples)

// --- Bounce Quality ---
input group "=== Bounce Quality ==="
input double InpMinBodyATR     = 0.3;        // Min bounce bar body (ATR multiple)
input bool   InpBounceCloseDir = true;        // Bounce bar must close in trend direction (close > open for buy)
input int    InpMaxTradesDay   = 1;           // Max trades per day (1 = default)

// --- Confluence Filters (v3) ---
input group "=== Confluence Filters ==="
input bool   InpUseMACD        = false;       // MACD histogram must agree with trend
input int    InpMACD_Fast      = 12;          // MACD fast EMA
input int    InpMACD_Slow      = 26;          // MACD slow EMA
input int    InpMACD_Signal    = 9;           // MACD signal period
input bool   InpUseRSI         = false;       // RSI filter (skip overbought buys / oversold sells)
input int    InpRSI_Period     = 14;          // RSI period
input double InpRSI_OB        = 75.0;        // RSI overbought level (skip buy above)
input double InpRSI_OS        = 25.0;        // RSI oversold level (skip sell below)
input bool   InpUseADX         = false;       // ADX trend strength filter
input int    InpADX_Period     = 14;          // ADX period
input double InpADX_Min        = 20.0;       // Min ADX for trending market
input bool   InpUseHTF_Bias    = false;       // H4 EMA directional bias filter
input int    InpHTF_EMA        = 50;          // H4 EMA period for bias
input bool   InpUseZoneWidth   = false;       // Zone width filter
input double InpZoneWidthMin   = 0.2;        // Min zone width (ATR multiples)
input double InpZoneWidthMax   = 2.0;        // Max zone width (ATR multiples)
input bool   InpUseVolRegime   = false;       // Volatility regime filter (skip dead days)
input double InpVolATR_MinPct  = 30.0;        // Min ATR percentile (skip below)
input int    InpVolATR_Lookback = 100;        // ATR lookback bars for percentile
input bool   InpUseEMASlope    = false;       // EMA 89 slope filter (trend quality)
input double InpEMASlopeMin    = 0.0;         // Min EMA89 slope (pips/bar)
input bool   InpUseTrail       = false;       // Use trailing stop instead of fixed TP
input double InpTrailATR       = 1.0;         // Trail distance (ATR multiples)
input double InpTrailStart     = 1.0;         // Trail activation (R multiples)

// --- Day Filter ---
input group "=== Day Filter ==="
input bool   InpTradeMon       = true;       // Trade Monday
input bool   InpTradeTue       = true;       // Trade Tuesday
input bool   InpTradeWed       = true;       // Trade Wednesday
input bool   InpTradeThu       = true;       // Trade Thursday
input bool   InpTradeFri       = false;      // Trade Friday

// --- Safety ---
input group "=== Safety ==="
input double InpMaxDDPct       = 50.0;       // Max account DD % (kill switch, high for research)
input int    InpMaxRetries     = 3;          // Max order send retries
input int    InpMaxSlippage    = 30;         // Max slippage points

//+------------------------------------------------------------------+
//| GLOBALS                                                            |
//+------------------------------------------------------------------+
CTrade         m_trade;
CPositionInfo  m_pos;
CSymbolInfo    m_sym;

int            g_atrHandle   = INVALID_HANDLE;
int            g_emaF1Handle = INVALID_HANDLE;
int            g_emaF2Handle = INVALID_HANDLE;
int            g_emaZUHandle = INVALID_HANDLE;
int            g_emaZLHandle = INVALID_HANDLE;
int            g_macdHandle  = INVALID_HANDLE;
int            g_rsiHandle   = INVALID_HANDLE;
int            g_adxHandle   = INVALID_HANDLE;
int            g_htfEmaHandle = INVALID_HANDLE;

double         g_atrBuf[];
double         g_emaF1Buf[];
double         g_emaF2Buf[];
double         g_emaZUBuf[];
double         g_emaZLBuf[];
double         g_macdMainBuf[];
double         g_rsiBuf[];
double         g_adxBuf[];
double         g_htfEmaBuf[];

datetime       g_lastTradeDate = 0;
double         g_peakEquity = 0;
bool           g_ddKillTriggered = false;

//+------------------------------------------------------------------+
//| Expert initialization function                                     |
//+------------------------------------------------------------------+
int OnInit()
{
   if(!InpEnabled)
   {
      Print("[ITSM] EA DISABLED by kill switch");
      return INIT_SUCCEEDED;
   }

   if(!m_sym.Name(_Symbol))
   {
      Print("[ITSM] Symbol init failed: ", _Symbol);
      return INIT_FAILED;
   }
   m_sym.Refresh();

   m_trade.SetExpertMagicNumber(InpMagic);
   m_trade.SetDeviationInPoints(InpMaxSlippage);

   // Adaptive fill mode
   ENUM_ORDER_TYPE_FILLING fillMode = ORDER_FILLING_FOK;
   uint filling = (uint)SymbolInfoInteger(_Symbol, SYMBOL_FILLING_MODE);
   if((filling & SYMBOL_FILLING_IOC) != 0)
      fillMode = ORDER_FILLING_IOC;
   m_trade.SetTypeFilling(fillMode);

   // Indicator handles
   g_atrHandle   = iATR(_Symbol, PERIOD_CURRENT, InpATR_Period);
   g_emaF1Handle = iMA(_Symbol, PERIOD_CURRENT, InpEMA_Fast1, 0, MODE_EMA, PRICE_CLOSE);
   g_emaF2Handle = iMA(_Symbol, PERIOD_CURRENT, InpEMA_Fast2, 0, MODE_EMA, PRICE_CLOSE);
   g_emaZUHandle = iMA(_Symbol, PERIOD_CURRENT, InpEMA_ZoneUpper, 0, MODE_EMA, PRICE_CLOSE);
   g_emaZLHandle = iMA(_Symbol, PERIOD_CURRENT, InpEMA_ZoneLower, 0, MODE_EMA, PRICE_CLOSE);

   if(g_atrHandle == INVALID_HANDLE || g_emaF1Handle == INVALID_HANDLE ||
      g_emaF2Handle == INVALID_HANDLE || g_emaZUHandle == INVALID_HANDLE ||
      g_emaZLHandle == INVALID_HANDLE)
   {
      Print("[ITSM] Indicator handle creation failed");
      return INIT_FAILED;
   }

   ArraySetAsSeries(g_atrBuf, true);
   ArraySetAsSeries(g_emaF1Buf, true);
   ArraySetAsSeries(g_emaF2Buf, true);
   ArraySetAsSeries(g_emaZUBuf, true);
   ArraySetAsSeries(g_emaZLBuf, true);

   // Optional confluence indicator handles
   if(InpUseMACD)
   {
      g_macdHandle = iMACD(_Symbol, PERIOD_CURRENT, InpMACD_Fast, InpMACD_Slow, InpMACD_Signal, PRICE_CLOSE);
      if(g_macdHandle == INVALID_HANDLE) { Print("[ITSM] MACD handle failed"); return INIT_FAILED; }
      ArraySetAsSeries(g_macdMainBuf, true);
   }
   if(InpUseRSI)
   {
      g_rsiHandle = iRSI(_Symbol, PERIOD_CURRENT, InpRSI_Period, PRICE_CLOSE);
      if(g_rsiHandle == INVALID_HANDLE) { Print("[ITSM] RSI handle failed"); return INIT_FAILED; }
      ArraySetAsSeries(g_rsiBuf, true);
   }
   if(InpUseADX)
   {
      g_adxHandle = iADX(_Symbol, PERIOD_CURRENT, InpADX_Period);
      if(g_adxHandle == INVALID_HANDLE) { Print("[ITSM] ADX handle failed"); return INIT_FAILED; }
      ArraySetAsSeries(g_adxBuf, true);
   }
   if(InpUseHTF_Bias)
   {
      g_htfEmaHandle = iMA(_Symbol, PERIOD_H4, InpHTF_EMA, 0, MODE_EMA, PRICE_CLOSE);
      if(g_htfEmaHandle == INVALID_HANDLE) { Print("[ITSM] H4 EMA handle failed"); return INIT_FAILED; }
      ArraySetAsSeries(g_htfEmaBuf, true);
   }

   g_peakEquity = AccountInfoDouble(ACCOUNT_EQUITY);

   Print("[ITSM] v3.0 Sonic R Wave + Confluence initialized on ", _Symbol, " ", EnumToString(Period()),
         " | EMAs: ", InpEMA_Fast1, "/", InpEMA_Fast2, "/", InpEMA_ZoneUpper, "/", InpEMA_ZoneLower,
         " | KZ1: ", InpKZ1_StartH, ":", StringFormat("%02d", InpKZ1_StartM),
         "-", InpKZ1_EndH, ":", StringFormat("%02d", InpKZ1_EndM),
         " | R:R ", InpRR_Ratio,
         " | Magic: ", InpMagic);

   // Execution quality logging
   double itsmPipSize = m_sym.Point() * 10.0;
   if(StringFind(_Symbol, "JPY") >= 0) itsmPipSize = m_sym.Point() * 100.0;
   EQL_Init("EA_ITSM", InpMagic, "ITSM", itsmPipSize, true);

   return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
//| Expert deinitialization                                            |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   if(g_atrHandle != INVALID_HANDLE)   IndicatorRelease(g_atrHandle);
   if(g_emaF1Handle != INVALID_HANDLE) IndicatorRelease(g_emaF1Handle);
   if(g_emaF2Handle != INVALID_HANDLE) IndicatorRelease(g_emaF2Handle);
   if(g_emaZUHandle != INVALID_HANDLE) IndicatorRelease(g_emaZUHandle);
   if(g_emaZLHandle != INVALID_HANDLE) IndicatorRelease(g_emaZLHandle);
   if(g_macdHandle != INVALID_HANDLE)  IndicatorRelease(g_macdHandle);
   if(g_rsiHandle != INVALID_HANDLE)   IndicatorRelease(g_rsiHandle);
   if(g_adxHandle != INVALID_HANDLE)   IndicatorRelease(g_adxHandle);
   if(g_htfEmaHandle != INVALID_HANDLE) IndicatorRelease(g_htfEmaHandle);
}

//+------------------------------------------------------------------+
//| Expert tick function                                               |
//+------------------------------------------------------------------+
void OnTick()
{
   if(!InpEnabled || g_ddKillTriggered) return;
   if(IsMarketHoliday()) return;

   if(Bars(_Symbol, Period()) < InpEMA_ZoneLower + 50) return;

   CheckDDKill();
   if(g_ddKillTriggered) return;

   // Time-based exit for open positions (every tick)
   if(InpUseTimeExit)
      CheckTimeExit();

   // Break-even management (every tick)
   if(InpUseBE)
      ManageBreakEven();

   // Trailing stop management (every tick)
   if(InpUseTrail)
      ManageTrailingStop();

   // Only process on new bar
   static datetime lastBar = 0;
   datetime curBar = iTime(_Symbol, Period(), 0);
   if(curBar == lastBar) return;
   lastBar = curBar;

   // Already have position?
   if(HasPositionOpen()) return;

   // Already traded today?
   MqlDateTime dt;
   TimeCurrent(dt);
   datetime today = StringToTime(StringFormat("%04d.%02d.%02d", dt.year, dt.mon, dt.day));
   if(g_lastTradeDate == today) return;

   // Day filter
   if(!IsTradingDay(dt.day_of_week)) return;

   // Kill Zone filter — must be within active session
   if(!InKillZone(dt)) return;

   // Copy indicator buffers (need lookback + current + 2 extra)
   int need = InpLookback + 3;
   if(CopyBuffer(g_atrHandle,   0, 1, need, g_atrBuf)   < need) return;
   if(CopyBuffer(g_emaF1Handle, 0, 1, need, g_emaF1Buf) < need) return;
   if(CopyBuffer(g_emaF2Handle, 0, 1, need, g_emaF2Buf) < need) return;
   if(CopyBuffer(g_emaZUHandle, 0, 1, need, g_emaZUBuf) < need) return;
   if(CopyBuffer(g_emaZLHandle, 0, 1, need, g_emaZLBuf) < need) return;

   double atr = g_atrBuf[0];
   if(atr < _Point * 10) return;

   // Determine zone boundaries at shift=1 (just-closed bar)
   double zoneTop    = MathMax(g_emaZUBuf[0], g_emaZLBuf[0]);
   double zoneBottom = MathMin(g_emaZUBuf[0], g_emaZLBuf[0]);
   double zoneBuffer = InpZoneBufferATR * atr;

   // Determine trend direction from EMA alignment at shift=1
   int trend = GetTrendDirection(0); // 0 = most recent closed bar
   if(trend == 0) return; // No trend

   // Check for Sonic R bounce signal
   double bounceClose = iClose(_Symbol, Period(), 1); // closed bar
   double bounceOpen  = iOpen(_Symbol, Period(), 1);
   double bounceHigh  = iHigh(_Symbol, Period(), 1);
   double bounceLow   = iLow(_Symbol, Period(), 1);
   double bodySize    = MathAbs(bounceClose - bounceOpen);
   bool isBuy = false;
   bool isSell = false;

   // Bounce quality: body must be large enough relative to ATR
   if(InpMinBodyATR > 0 && bodySize < InpMinBodyATR * atr) return;

   if(trend > 0) // Bullish trend
   {
      // Bounce bar must close in trend direction (bullish candle)
      if(InpBounceCloseDir && bounceClose <= bounceOpen) return;

      // Price must have bounced ABOVE zone
      if(bounceClose <= zoneTop) return; // Not above zone yet

      // Check if any of the lookback bars touched or entered the zone from above
      bool hadPullback = false;
      for(int i = 1; i <= InpLookback; i++)
      {
         double lo = iLow(_Symbol, Period(), 1 + i);
         double localZoneTop = MathMax(g_emaZUBuf[i], g_emaZLBuf[i]);
         double localZoneBot = MathMin(g_emaZUBuf[i], g_emaZLBuf[i]);

         if(InpRequireTouch)
         {
            // Low must have touched or penetrated into the zone
            if(lo <= localZoneTop + zoneBuffer)
            {
               hadPullback = true;
               break;
            }
         }
         else
         {
            // Close dropped toward zone (within 1 ATR)
            double cl = iClose(_Symbol, Period(), 1 + i);
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
      // Bounce bar must close in trend direction (bearish candle)
      if(InpBounceCloseDir && bounceClose >= bounceOpen) return;

      // Price must have bounced BELOW zone
      if(bounceClose >= zoneBottom) return;

      bool hadPullback = false;
      for(int i = 1; i <= InpLookback; i++)
      {
         double hi = iHigh(_Symbol, Period(), 1 + i);
         double localZoneTop = MathMax(g_emaZUBuf[i], g_emaZLBuf[i]);
         double localZoneBot = MathMin(g_emaZUBuf[i], g_emaZLBuf[i]);

         if(InpRequireTouch)
         {
            if(hi >= localZoneBot - zoneBuffer)
            {
               hadPullback = true;
               break;
            }
         }
         else
         {
            double cl = iClose(_Symbol, Period(), 1 + i);
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

   //--- v3 CONFLUENCE FILTERS (all on closed bar, shift=1) ---

   // 1. MACD histogram must agree with trend direction
   if(InpUseMACD)
   {
      double macdBuf[2];
      if(CopyBuffer(g_macdHandle, 0, 1, 2, macdBuf) < 2) return;
      // For buy: MACD main line > 0 OR histogram rising
      // For sell: MACD main line < 0 OR histogram falling
      if(isBuy && macdBuf[0] < 0) return;   // macdBuf[0] = shift=1 (latest closed bar)
      if(isSell && macdBuf[0] > 0) return;
   }

   // 2. RSI filter — skip overbought buys / oversold sells (exhaustion guard)
   if(InpUseRSI)
   {
      double rsiBuf[2];
      if(CopyBuffer(g_rsiHandle, 0, 1, 2, rsiBuf) < 2) return;
      double rsiVal = rsiBuf[0];  // shift=1 (latest closed bar)
      if(isBuy && rsiVal > InpRSI_OB) return;   // Already overbought, skip buy
      if(isSell && rsiVal < InpRSI_OS) return;   // Already oversold, skip sell
   }

   // 3. ADX trend strength — only trade in strong trends
   if(InpUseADX)
   {
      double adxBuf[2];
      if(CopyBuffer(g_adxHandle, 0, 1, 2, adxBuf) < 2) return;
      if(adxBuf[0] < InpADX_Min) return;  // Trend too weak (shift=1, closed bar)
   }

   // 4. H4 EMA directional bias — price must be on correct side of H4 EMA
   if(InpUseHTF_Bias)
   {
      double htfBuf[2];
      if(CopyBuffer(g_htfEmaHandle, 0, 1, 2, htfBuf) < 2) return;
      // htfBuf[0] = last closed H4 EMA value (shift=1, no repaint)
      if(isBuy && bounceClose < htfBuf[0]) return;   // Price below H4 EMA, skip buy
      if(isSell && bounceClose > htfBuf[0]) return;   // Price above H4 EMA, skip sell
   }

   // 5. Zone width filter — skip when zone is too wide (consolidation) or too narrow
   if(InpUseZoneWidth)
   {
      double zoneWidth = zoneTop - zoneBottom;
      if(zoneWidth < InpZoneWidthMin * atr) return;  // Zone too narrow
      if(zoneWidth > InpZoneWidthMax * atr) return;  // Zone too wide (choppy)
   }

   // 6. Volatility regime — skip low-vol days
   if(InpUseVolRegime)
   {
      double atrHistory[];
      ArraySetAsSeries(atrHistory, true);
      if(CopyBuffer(g_atrHandle, 0, 1, InpVolATR_Lookback, atrHistory) >= InpVolATR_Lookback)
      {
         // Count how many historical ATR values are below current ATR
         int countBelow = 0;
         for(int j = 1; j < InpVolATR_Lookback; j++)
         {
            if(atrHistory[j] < atr) countBelow++;
         }
         double percentile = (double)countBelow / (InpVolATR_Lookback - 1) * 100.0;
         if(percentile < InpVolATR_MinPct) return; // Current ATR is in bottom percentile = dead day
      }
   }

   // 7. EMA 89 slope filter — trend quality (strong trend = steep slope)
   if(InpUseEMASlope)
   {
      // Slope = (EMA89[0] - EMA89[3]) / 3 bars, in points
      if(g_emaZLBuf[0] != 0 && g_emaZLBuf[3] != 0)
      {
         double slope = (g_emaZLBuf[0] - g_emaZLBuf[3]) / 3.0 / _Point;
         if(isBuy && slope < InpEMASlopeMin) return;    // Uptrend too flat
         if(isSell && (-slope) < InpEMASlopeMin) return; // Downtrend too flat
      }
   }

   // Calculate SL and TP
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   if(ask <= 0 || bid <= 0) return;
   double spread = ask - bid;

   int stopLevel = (int)SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL);
   int freezeLevel = (int)SymbolInfoInteger(_Symbol, SYMBOL_TRADE_FREEZE_LEVEL);
   double minDist = MathMax(stopLevel, freezeLevel) * _Point + spread;

   double sl, tp, entry, slRisk;
   int digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);

   if(isBuy)
   {
      entry = ask;
      // SL below the zone bottom + ATR buffer
      sl = zoneBottom - InpSL_ATR_Mult * atr;
      slRisk = entry - sl;
      if(slRisk < minDist) slRisk = minDist;
      sl = NormalizeDouble(entry - slRisk, digits);
      tp = InpUseTrail ? 0 : NormalizeDouble(entry + slRisk * InpRR_Ratio, digits);
   }
   else
   {
      entry = bid;
      // SL above the zone top + ATR buffer
      sl = zoneTop + InpSL_ATR_Mult * atr;
      slRisk = sl - entry;
      if(slRisk < minDist) slRisk = minDist;
      sl = NormalizeDouble(entry + slRisk, digits);
      tp = InpUseTrail ? 0 : NormalizeDouble(entry - slRisk * InpRR_Ratio, digits);
   }

   slRisk = MathAbs(entry - sl);

   double lots = CalcLotSize(slRisk);
   if(lots <= 0) return;

   Print("[ITSM] SIGNAL: ", (isBuy ? "BUY" : "SELL"),
         " | trend=", trend,
         " | bounce=", DoubleToString(bounceClose, digits),
         " | zoneTop=", DoubleToString(zoneTop, digits),
         " | zoneBot=", DoubleToString(zoneBottom, digits),
         " | emaF1=", DoubleToString(g_emaF1Buf[0], digits),
         " | emaF2=", DoubleToString(g_emaF2Buf[0], digits),
         " | lots=", lots, " entry=", entry,
         " | SL=", sl, " TP=", tp);

   // Send order
   double pipSize = m_sym.Point() * 10.0;
   if(StringFind(_Symbol, "JPY") >= 0) pipSize = m_sym.Point() * 100.0;

   bool filled = false;
   uint retcode = 0;
   for(int attempt = 1; attempt <= InpMaxRetries; attempt++)
   {
      double curAsk = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
      double curBid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
      double spreadPips = (double)SymbolInfoInteger(_Symbol, SYMBOL_SPREAD) * m_sym.Point() / pipSize;

      if(isBuy)
      {
         EQL_SetContext(curAsk, spreadPips, "NY");
         if(m_trade.Buy(lots, _Symbol, curAsk, sl, tp, InpComment))
         {
            retcode = m_trade.ResultRetcode();
            EQL_RecordFill(retcode);
            if(retcode == TRADE_RETCODE_DONE)
            {
               filled = true;
               break;
            }
         }
         else
         {
            retcode = m_trade.ResultRetcode();
            EQL_RecordRetry(retcode);
         }
      }
      else
      {
         EQL_SetContext(curBid, spreadPips, "NY");
         if(m_trade.Sell(lots, _Symbol, curBid, sl, tp, InpComment))
         {
            retcode = m_trade.ResultRetcode();
            EQL_RecordFill(retcode);
            if(retcode == TRADE_RETCODE_DONE)
            {
               filled = true;
               break;
            }
         }
         else
         {
            retcode = m_trade.ResultRetcode();
            EQL_RecordRetry(retcode);
         }
      }

      if(retcode == TRADE_RETCODE_NO_MONEY) break;
      Print("[ITSM] Order attempt ", attempt, " failed: ", retcode);
      if(attempt < InpMaxRetries) Sleep(200 * (int)MathPow(2, attempt - 1));
   }

   if(filled)
   {
      g_lastTradeDate = today;
      Print("[ITSM] FILLED: ", (isBuy ? "BUY" : "SELL"), " ", lots, " lots",
            " | SL=", sl, " TP=", tp,
            " | ATR=", DoubleToString(atr / _Point, 0), " pts");
   }
}

//+------------------------------------------------------------------+
//| Determine trend direction from EMA alignment                       |
//| Returns: +1 = bullish, -1 = bearish, 0 = no clear trend          |
//+------------------------------------------------------------------+
int GetTrendDirection(int shift)
{
   double emaF1 = g_emaF1Buf[shift];
   double emaF2 = g_emaF2Buf[shift];
   double emaZU = g_emaZUBuf[shift]; // 34
   double emaZL = g_emaZLBuf[shift]; // 89

   double zoneTop = MathMax(emaZU, emaZL);
   double zoneBot = MathMin(emaZU, emaZL);

   if(InpStrictAlign)
   {
      // Strict: F1 > F2 > ZoneUpper > ZoneLower (or reverse)
      if(emaF1 > emaF2 && emaF2 > emaZU && emaZU > emaZL)
         return +1;
      if(emaF1 < emaF2 && emaF2 < emaZU && emaZU < emaZL)
         return -1;
      return 0;
   }
   else
   {
      // Loose: Fast EMAs above zone = bullish, below = bearish
      // Zone direction: emaZU(34) above emaZL(89) = bullish structure
      if(emaF1 > zoneTop && emaF2 > zoneTop && emaZU > emaZL)
         return +1;
      if(emaF1 < zoneBot && emaF2 < zoneBot && emaZU < emaZL)
         return -1;
      return 0;
   }
}

//+------------------------------------------------------------------+
//| Kill Zone check                                                    |
//+------------------------------------------------------------------+
bool InKillZone(const MqlDateTime &dt)
{
   int minutes = dt.hour * 60 + dt.min;
   int kz1Start = InpKZ1_StartH * 60 + InpKZ1_StartM;
   int kz1End   = InpKZ1_EndH * 60 + InpKZ1_EndM;

   if(minutes >= kz1Start && minutes < kz1End) return true;

   if(InpUseKZ2)
   {
      int kz2Start = InpKZ2_StartH * 60 + InpKZ2_StartM;
      int kz2End   = InpKZ2_EndH * 60 + InpKZ2_EndM;
      if(minutes >= kz2Start && minutes < kz2End) return true;
   }

   return false;
}

//+------------------------------------------------------------------+
//| Day filter                                                         |
//+------------------------------------------------------------------+
bool IsTradingDay(int dow)
{
   switch(dow)
   {
      case 1: return InpTradeMon;
      case 2: return InpTradeTue;
      case 3: return InpTradeWed;
      case 4: return InpTradeThu;
      case 5: return InpTradeFri;
      default: return false;
   }
}

//+------------------------------------------------------------------+
//| Check if we have an open position                                  |
//+------------------------------------------------------------------+
bool HasPositionOpen()
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      if(m_pos.SelectByIndex(i))
      {
         if(m_pos.Symbol() == _Symbol && m_pos.Magic() == InpMagic)
            return true;
      }
   }
   return false;
}

//+------------------------------------------------------------------+
//| Time-based exit                                                    |
//+------------------------------------------------------------------+
void CheckTimeExit()
{
   MqlDateTime dt;
   TimeCurrent(dt);
   int curMinutes = dt.hour * 60 + dt.min;
   int exitMinutes = InpExitHour * 60 + InpExitMinute;

   if(curMinutes < exitMinutes) return;

   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      if(m_pos.SelectByIndex(i))
      {
         if(m_pos.Symbol() == _Symbol && m_pos.Magic() == InpMagic)
         {
            m_trade.PositionClose(m_pos.Ticket());
            Print("[ITSM] Time exit at ", dt.hour, ":", StringFormat("%02d", dt.min));
         }
      }
   }
}

//+------------------------------------------------------------------+
//| Break-even management                                              |
//+------------------------------------------------------------------+
void ManageBreakEven()
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      if(!m_pos.SelectByIndex(i)) continue;
      if(m_pos.Symbol() != _Symbol || m_pos.Magic() != InpMagic) continue;

      double openPrice = m_pos.PriceOpen();
      double sl = m_pos.StopLoss();
      double tp = m_pos.TakeProfit();
      double risk = MathAbs(openPrice - sl);
      if(risk < _Point) continue;

      double beTrigger = risk * InpBE_Trigger;

      if(m_pos.PositionType() == POSITION_TYPE_BUY)
      {
         if(sl >= openPrice) continue;
         double profit = SymbolInfoDouble(_Symbol, SYMBOL_BID) - openPrice;
         if(profit >= beTrigger)
         {
            double newSL = NormalizeDouble(openPrice + _Point, (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS));
            m_trade.PositionModify(m_pos.Ticket(), newSL, tp);
            Print("[ITSM] BE moved to ", newSL);
         }
      }
      else
      {
         if(sl <= openPrice && sl > 0) continue;
         double profit = openPrice - SymbolInfoDouble(_Symbol, SYMBOL_ASK);
         if(profit >= beTrigger)
         {
            double newSL = NormalizeDouble(openPrice - _Point, (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS));
            m_trade.PositionModify(m_pos.Ticket(), newSL, tp);
            Print("[ITSM] BE moved to ", newSL);
         }
      }
   }
}

//+------------------------------------------------------------------+
//| Trailing stop management                                           |
//+------------------------------------------------------------------+
void ManageTrailingStop()
{
   double atrVal[1];
   if(CopyBuffer(g_atrHandle, 0, 1, 1, atrVal) < 1) return;  // shift=1 (closed bar ATR)
   double trailDist = InpTrailATR * atrVal[0];

   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      if(!m_pos.SelectByIndex(i)) continue;
      if(m_pos.Symbol() != _Symbol || m_pos.Magic() != InpMagic) continue;

      double openPrice = m_pos.PriceOpen();
      double sl = m_pos.StopLoss();
      double tp = m_pos.TakeProfit();
      double risk = MathAbs(openPrice - sl);
      if(risk < _Point) continue;

      double trailActivate = risk * InpTrailStart;
      int digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);

      if(m_pos.PositionType() == POSITION_TYPE_BUY)
      {
         double curPrice = SymbolInfoDouble(_Symbol, SYMBOL_BID);
         double profit = curPrice - openPrice;
         if(profit < trailActivate) continue;

         double newSL = NormalizeDouble(curPrice - trailDist, digits);
         if(newSL > sl + _Point)
         {
            m_trade.PositionModify(m_pos.Ticket(), newSL, tp);
         }
      }
      else
      {
         double curPrice = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
         double profit = openPrice - curPrice;
         if(profit < trailActivate) continue;

         double newSL = NormalizeDouble(curPrice + trailDist, digits);
         if(newSL < sl - _Point || sl == 0)
         {
            m_trade.PositionModify(m_pos.Ticket(), newSL, tp);
         }
      }
   }
}

//+------------------------------------------------------------------+
//| DD kill switch                                                     |
//+------------------------------------------------------------------+
void CheckDDKill()
{
   double equity = AccountInfoDouble(ACCOUNT_EQUITY);
   if(equity > g_peakEquity) g_peakEquity = equity;

   if(g_peakEquity > 0)
   {
      double dd = (g_peakEquity - equity) / g_peakEquity * 100.0;
      if(dd >= InpMaxDDPct)
      {
         g_ddKillTriggered = true;
         Print("[ITSM] DD KILL SWITCH: DD=", DoubleToString(dd, 1), "% >= ", InpMaxDDPct, "%");
         for(int i = PositionsTotal() - 1; i >= 0; i--)
         {
            if(m_pos.SelectByIndex(i))
            {
               if(m_pos.Symbol() == _Symbol && m_pos.Magic() == InpMagic)
                  m_trade.PositionClose(m_pos.Ticket());
            }
         }
      }
   }
}

//+------------------------------------------------------------------+
//| Calculate lot size from risk                                       |
//+------------------------------------------------------------------+
double CalcLotSize(double riskPoints)
{
   if(riskPoints <= 0) return 0;

   double balance = AccountInfoDouble(ACCOUNT_BALANCE);
   double riskMoney = balance * InpRiskPct / 100.0;

   double tickValue = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
   double tickSize  = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);

   if(tickValue <= 0 || tickSize <= 0) return 0;

   double lots = riskMoney / (riskPoints / tickSize * tickValue);

   double minLot  = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double maxLot  = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   double stepLot = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);

   if(lots < minLot) return 0;
   if(lots > InpMaxLot) lots = InpMaxLot;
   if(lots > maxLot) lots = maxLot;

   lots = MathFloor(lots / stepLot) * stepLot;

   return NormalizeDouble(lots, 2);
}
//+------------------------------------------------------------------+
//| Trade transaction handler — feeds EQL deal capture               |
//+------------------------------------------------------------------+
void OnTradeTransaction(const MqlTradeTransaction& trans,
                        const MqlTradeRequest& request,
                        const MqlTradeResult& result)
{
   if(trans.type != TRADE_TRANSACTION_DEAL_ADD) return;
   if(trans.deal == 0) return;
   if(!HistoryDealSelect(trans.deal)) return;
   if((long)HistoryDealGetInteger(trans.deal, DEAL_MAGIC) != InpMagic) return;
   EQL_OnDeal(trans.deal);
}
//+------------------------------------------------------------------+
