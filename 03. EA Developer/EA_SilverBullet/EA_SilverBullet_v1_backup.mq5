//+------------------------------------------------------------------+
//| EA_SilverBullet_v1.mq5                                          |
//| Copyright 2026, Max & Ngai Meo Coc                                |
//| Strategy: ICT-Inspired Kill Zone + Displacement + FVG Entry      |
//|                                                                    |
//| STRUCTURAL THESIS (not indicator-based):                          |
//| During specific institutional time windows (kill zones),          |
//| large players create DISPLACEMENT — strong directional candles    |
//| that leave Fair Value Gaps (price imbalances). Price has a        |
//| statistical tendency to retrace into the FVG before continuing.   |
//| Entry at FVG fill = high probability with tight SL.              |
//|                                                                    |
//| Kill Zones (EST / Broker GMT+2):                                  |
//|   London: 02:00-05:00 EST = 09:00-12:00 broker                   |
//|   NY AM:  09:30-11:00 EST = 16:30-18:00 broker                   |
//|   NY PM:  13:30-15:00 EST = 20:30-22:00 broker                   |
//|                                                                    |
//| Different from everything tested before:                          |
//| - NOT EMA/RSI/BB based                                            |
//| - NOT session range breakout (Spark approach)                     |
//| - Based on displacement + imbalance fill + time                   |
//+------------------------------------------------------------------+
#property copyright "Max & Ngai Meo Coc"
#property link      "https://github.com"
#property version   "1.00"
#property strict

#include <Trade\Trade.mqh>
#include <Trade\PositionInfo.mqh>
#include <Trade\SymbolInfo.mqh>

//+------------------------------------------------------------------+
//| INPUTS                                                             |
//+------------------------------------------------------------------+
input group "=== Core Settings ==="
input double InpRiskPct       = 1.0;        // Risk % per trade
input double InpMaxLot        = 0.50;       // Max lot size
input int    InpMagic         = 20260325;   // Magic number
input string InpComment       = "SB1";      // Trade comment

// --- Kill Zones (Broker Time GMT+2) ---
input group "=== Kill Zones (Broker Time) ==="
input bool   InpUseLDN        = true;       // Use London Kill Zone
input int    InpLDN_Start     = 11;         // London KZ start hour (skip noisy 9-10)
input int    InpLDN_End       = 12;         // London KZ end hour
input bool   InpUseNYAM       = true;       // Use NY AM Kill Zone
input int    InpNYAM_Start    = 16;         // NY AM KZ start hour
input int    InpNYAM_End      = 18;         // NY AM KZ end hour
input bool   InpUseNYPM       = false;      // Use NY PM Kill Zone (off by default)
input int    InpNYPM_Start    = 20;         // NY PM KZ start hour
input int    InpNYPM_End      = 22;         // NY PM KZ end hour

// --- Displacement Detection ---
input group "=== Displacement (Strong Candle) ==="
input double InpDispBodyATR   = 0.40;       // Min displacement body size (ATR multiples)
input double InpDispBodyRatio = 0.70;       // Min body/range ratio (directional strength)
input int    InpATR_Period    = 14;         // ATR period (H1)

// --- FVG (Fair Value Gap) ---
input group "=== FVG Entry ==="
input int    InpFVG_MaxWait   = 8;          // Max bars to wait for FVG fill (M15 = 2h)
input double InpFVG_MinSize   = 0.10;       // Min FVG size (ATR multiples)

// --- SL / TP ---
input group "=== SL/TP ==="
input double InpSL_ATR        = 1.50;       // SL in ATR multiples (beyond displacement)
input double InpTP_RR         = 2.00;       // TP as R:R ratio (default fallback)
input double InpTP_RR_LDN     = 2.50;       // TP R:R London KZ (higher continuation)
input double InpTP_RR_NY      = 1.50;       // TP R:R NY KZ (capped upside)
input double InpMinSL_Pips    = 8.0;        // Min SL in pips
input double InpMaxSL_Pips    = 60.0;       // Max SL in pips

// --- Bias / Higher Timeframe ---
input group "=== HTF Bias ==="
input bool   InpUseHTFBias    = true;       // Use H4 bias for direction filter
input int    InpHTF_EMA       = 50;         // H4 EMA period for bias

// --- Volatility Regime Filter ---
input group "=== Volatility Regime ==="
input bool   InpUseVolRegime  = true;       // Use D1 ATR regime filter
input int    InpVolATR_Period = 20;         // D1 ATR period for regime
input double InpVolATR_MinMul = 0.50;       // Min ATR multiple (skip ultra-low vol)
input double InpVolATR_MaxMul = 2.50;       // Max ATR multiple (skip crisis vol)

// --- Risk Management ---
input group "=== Risk Management ==="
input int    InpMaxTradesPerDay = 3;        // Max trades per day
input int    InpMaxTradesPerKZ  = 1;        // Max trades per kill zone
input double InpMaxSpreadPips   = 5.0;      // Max spread (pips) — set higher for gold
input double InpMaxDailyDD_Pct  = 3.0;      // Max daily DD %
input bool   InpSkipFriday      = true;     // Skip Friday

//+------------------------------------------------------------------+
//| ENUMS                                                              |
//+------------------------------------------------------------------+
enum ENUM_KZ_TYPE { KZ_NONE, KZ_LONDON, KZ_NY_AM, KZ_NY_PM };

//+------------------------------------------------------------------+
//| STRUCTS                                                            |
//+------------------------------------------------------------------+
struct FVGZone
{
   double   upper;       // Upper boundary
   double   lower;       // Lower boundary
   bool     isBullish;   // Bullish FVG (gap below) = buy entry
   datetime createTime;  // When the FVG was created
   int      barAge;      // Bars since creation
   bool     active;      // Still waiting for fill?
   ENUM_KZ_TYPE sourceKZ; // Which kill zone created this FVG
};

//+------------------------------------------------------------------+
//| GLOBALS                                                            |
//+------------------------------------------------------------------+
CTrade        g_trade;
CPositionInfo g_pos;
CSymbolInfo   g_sym;

int    g_hATR_H1;
int    g_hHTF_EMA;
int    g_hATR_D1_Regime;  // D1 ATR for volatility regime filter
double g_pt;
double g_pipSize;

// Daily tracking
int    g_tradesToday;
int    g_tradesThisKZ;
datetime g_lastTradeDay;
double g_dayStartEquity;
ENUM_KZ_TYPE g_lastKZ;

// FVG tracking
FVGZone g_pendingFVG;

//+------------------------------------------------------------------+
//| Expert initialization                                              |
//+------------------------------------------------------------------+
int OnInit()
{
   g_sym.Name(_Symbol);
   g_pt = g_sym.Point();
   if(g_pt <= 0) { Print("[SB] ERROR: Invalid point"); return INIT_FAILED; }

   // Pip size detection
   int digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
   if(digits <= 2)
      g_pipSize = g_pt * 100.0;      // Gold/Silver
   else if(digits == 3 || digits == 5)
      g_pipSize = g_pt * 10.0;       // Standard forex
   else
      g_pipSize = g_pt;

   // Indicators
   g_hATR_H1 = iATR(_Symbol, PERIOD_H1, InpATR_Period);
   if(g_hATR_H1 == INVALID_HANDLE)
   { Print("[SB] ERROR: ATR handle failed"); return INIT_FAILED; }

   g_hHTF_EMA = INVALID_HANDLE;
   if(InpUseHTFBias)
   {
      g_hHTF_EMA = iMA(_Symbol, PERIOD_H4, InpHTF_EMA, 0, MODE_EMA, PRICE_CLOSE);
      if(g_hHTF_EMA == INVALID_HANDLE)
      { Print("[SB] ERROR: H4 EMA handle failed"); return INIT_FAILED; }
   }

   // D1 ATR for volatility regime filter
   g_hATR_D1_Regime = INVALID_HANDLE;
   if(InpUseVolRegime)
   {
      g_hATR_D1_Regime = iATR(_Symbol, PERIOD_D1, InpVolATR_Period);
      if(g_hATR_D1_Regime == INVALID_HANDLE)
      { Print("[SB] ERROR: D1 ATR regime handle failed"); return INIT_FAILED; }
   }

   // Trade setup
   g_trade.SetExpertMagicNumber(InpMagic);
   g_trade.SetTypeFilling(ORDER_FILLING_FOK);
   g_trade.SetDeviationInPoints(30);

   // Reset
   g_tradesToday    = 0;
   g_tradesThisKZ   = 0;
   g_lastTradeDay   = 0;
   g_lastKZ         = KZ_NONE;
   g_dayStartEquity = AccountInfoDouble(ACCOUNT_EQUITY);
   ResetFVG();

   Print("[SB] EA_SilverBullet v1.0 initialized on ", _Symbol,
         " | LDN=", InpUseLDN, " NYAM=", InpUseNYAM, " NYPM=", InpUseNYPM);
   return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
//| Expert deinitialization                                            |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   if(g_hATR_H1  != INVALID_HANDLE) IndicatorRelease(g_hATR_H1);
   if(g_hHTF_EMA != INVALID_HANDLE) IndicatorRelease(g_hHTF_EMA);
   if(g_hATR_D1_Regime != INVALID_HANDLE) IndicatorRelease(g_hATR_D1_Regime);
}

//+------------------------------------------------------------------+
//| Reset pending FVG                                                  |
//+------------------------------------------------------------------+
void ResetFVG()
{
   g_pendingFVG.active     = false;
   g_pendingFVG.upper      = 0;
   g_pendingFVG.lower      = 0;
   g_pendingFVG.isBullish  = false;
   g_pendingFVG.createTime = 0;
   g_pendingFVG.barAge     = 0;
   g_pendingFVG.sourceKZ   = KZ_NONE;
}

//+------------------------------------------------------------------+
//| Expert tick function                                               |
//+------------------------------------------------------------------+
void OnTick()
{
   // --- New bar detection (M15) ---
   static datetime lastBar = 0;
   datetime barTime = iTime(_Symbol, PERIOD_M15, 0);
   if(barTime == lastBar) return;
   lastBar = barTime;

   // --- Time info ---
   MqlDateTime dt;
   TimeCurrent(dt);
   int hour = dt.hour;
   int dow  = dt.day_of_week;

   // --- Day reset ---
   datetime today = StringToTime(StringFormat("%04d.%02d.%02d", dt.year, dt.mon, dt.day));
   if(today != g_lastTradeDay)
   {
      g_lastTradeDay   = today;
      g_tradesToday    = 0;
      g_tradesThisKZ   = 0;
      g_lastKZ         = KZ_NONE;
      g_dayStartEquity = AccountInfoDouble(ACCOUNT_EQUITY);
      ResetFVG();
   }

   // --- Day filter ---
   if(dow == 0 || dow == 6) return;
   if(InpSkipFriday && dow == 5) return;

   // --- Daily DD guard ---
   double equity = AccountInfoDouble(ACCOUNT_EQUITY);
   if(g_dayStartEquity > 0 && (g_dayStartEquity - equity) / g_dayStartEquity * 100.0 > InpMaxDailyDD_Pct)
   {
      CloseAllPositions();
      return;
   }

   // --- Volatility Regime Filter (D1 ATR) ---
   // Skip trading when volatility is abnormally low or high
   // Low vol = no displacement possible, High vol (crisis) = FVG fills unreliable
   if(InpUseVolRegime && g_hATR_D1_Regime != INVALID_HANDLE)
   {
      double d1Atr[], d1AtrSlow[];
      // Current D1 ATR vs longer-term average (use shift 1 = closed bar)
      if(CopyBuffer(g_hATR_D1_Regime, 0, 1, 2, d1Atr) < 2) return;
      double currentATR = d1Atr[1];  // Most recent closed D1 bar
      double prevATR    = d1Atr[0];  // One bar before
      double avgATR     = (currentATR + prevATR) / 2.0;  // Simple 2-bar average as baseline

      // Use the full ATR buffer average as baseline (approx via 2x period lookback)
      double d1AtrLong[];
      int lookback = InpVolATR_Period * 2;
      if(CopyBuffer(g_hATR_D1_Regime, 0, 1, lookback, d1AtrLong) >= lookback)
      {
         double sum = 0;
         for(int i = 0; i < lookback; i++) sum += d1AtrLong[i];
         avgATR = sum / lookback;
      }

      if(avgATR > 0)
      {
         double ratio = currentATR / avgATR;
         if(ratio < InpVolATR_MinMul || ratio > InpVolATR_MaxMul)
            return;  // Skip: volatility outside normal regime
      }
   }

   // --- Determine current kill zone ---
   ENUM_KZ_TYPE currentKZ = GetCurrentKZ(hour);

   // Reset KZ trade count when switching zones
   if(currentKZ != g_lastKZ)
   {
      g_tradesThisKZ = 0;
      g_lastKZ = currentKZ;
      // Don't carry FVG across kill zones
      if(g_pendingFVG.active && currentKZ == KZ_NONE)
         ResetFVG();
   }

   // --- Get ATR ---
   double atrBuf[];
   if(CopyBuffer(g_hATR_H1, 0, 1, 1, atrBuf) < 1) return;
   double atr = atrBuf[0];
   if(atr <= 0) return;

   // --- PHASE 1: Inside a kill zone — scan for displacement + FVG ---
   if(currentKZ != KZ_NONE && !g_pendingFVG.active)
   {
      ScanForDisplacementFVG(atr, currentKZ);
   }

   // --- PHASE 2: Have a pending FVG — check for fill entry ---
   if(g_pendingFVG.active)
   {
      g_pendingFVG.barAge++;

      // Expire if too old
      if(g_pendingFVG.barAge > InpFVG_MaxWait)
      {
         Print("[SB] FVG expired after ", InpFVG_MaxWait, " bars");
         ResetFVG();
         return;
      }

      TryFVGEntry(atr);
   }
}

//+------------------------------------------------------------------+
//| Determine which kill zone we're in                                 |
//+------------------------------------------------------------------+
ENUM_KZ_TYPE GetCurrentKZ(int hour)
{
   if(InpUseLDN  && hour >= InpLDN_Start  && hour < InpLDN_End)  return KZ_LONDON;
   if(InpUseNYAM && hour >= InpNYAM_Start && hour < InpNYAM_End) return KZ_NY_AM;
   if(InpUseNYPM && hour >= InpNYPM_Start && hour < InpNYPM_End) return KZ_NY_PM;
   return KZ_NONE;
}

//+------------------------------------------------------------------+
//| Scan for displacement candle + FVG formation                       |
//| Uses closed bars: shift 1 (newest), 2 (middle), 3 (oldest)       |
//| Bullish FVG: bar3_high < bar1_low (gap below bar2)               |
//| Bearish FVG: bar3_low > bar1_high (gap above bar2)               |
//+------------------------------------------------------------------+
void ScanForDisplacementFVG(double atr, ENUM_KZ_TYPE kz)
{
   // Bar 2 is the displacement candle (middle of the 3-bar pattern)
   double open2  = iOpen(_Symbol, PERIOD_M15, 2);
   double close2 = iClose(_Symbol, PERIOD_M15, 2);
   double high2  = iHigh(_Symbol, PERIOD_M15, 2);
   double low2   = iLow(_Symbol, PERIOD_M15, 2);
   double range2 = high2 - low2;
   if(range2 <= 0) return;

   double body2 = MathAbs(close2 - open2);

   // Check displacement criteria
   if(body2 < InpDispBodyATR * atr) return;        // Body not big enough
   if(body2 / range2 < InpDispBodyRatio) return;   // Not directional enough

   bool isBullDisp = (close2 > open2);  // Bullish displacement

   // Now check for FVG using 3-bar pattern (bars 3, 2, 1)
   double high3 = iHigh(_Symbol, PERIOD_M15, 3);
   double low3  = iLow(_Symbol, PERIOD_M15, 3);
   double high1 = iHigh(_Symbol, PERIOD_M15, 1);
   double low1  = iLow(_Symbol, PERIOD_M15, 1);

   double fvgUpper = 0, fvgLower = 0;
   bool hasFVG = false;
   bool fvgBullish = false;

   if(isBullDisp)
   {
      // Bullish FVG: gap between bar3's high and bar1's low
      // (price jumped up, leaving a gap)
      fvgLower = high3;   // Top of bar before displacement
      fvgUpper = low1;    // Bottom of bar after displacement
      if(fvgUpper > fvgLower)
      {
         double fvgSize = fvgUpper - fvgLower;
         if(fvgSize >= InpFVG_MinSize * atr)
         {
            hasFVG = true;
            fvgBullish = true;
         }
      }
   }
   else
   {
      // Bearish FVG: gap between bar3's low and bar1's high
      fvgUpper = low3;    // Bottom of bar before displacement
      fvgLower = high1;   // Top of bar after displacement
      if(fvgUpper > fvgLower)
      {
         double fvgSize = fvgUpper - fvgLower;
         if(fvgSize >= InpFVG_MinSize * atr)
         {
            hasFVG = true;
            fvgBullish = false;
         }
      }
   }

   if(!hasFVG) return;

   // --- HTF Bias Check ---
   if(InpUseHTFBias && g_hHTF_EMA != INVALID_HANDLE)
   {
      double emaBuf[];
      if(CopyBuffer(g_hHTF_EMA, 0, 1, 1, emaBuf) < 1) return;
      double h4ema = emaBuf[0];
      double price = iClose(_Symbol, PERIOD_M15, 1);

      // Only take bullish FVG when price above H4 EMA (uptrend)
      // Only take bearish FVG when price below H4 EMA (downtrend)
      if(fvgBullish && price < h4ema)
      {
         Print("[SB] Skip: Bullish FVG but price below H4 EMA (counter-trend)");
         return;
      }
      if(!fvgBullish && price > h4ema)
      {
         Print("[SB] Skip: Bearish FVG but price above H4 EMA (counter-trend)");
         return;
      }
   }

   // --- Store pending FVG ---
   g_pendingFVG.upper     = fvgUpper;
   g_pendingFVG.lower     = fvgLower;
   g_pendingFVG.isBullish = fvgBullish;
   g_pendingFVG.createTime = TimeCurrent();
   g_pendingFVG.barAge    = 0;
   g_pendingFVG.active    = true;
   g_pendingFVG.sourceKZ  = kz;

   string kzName = (kz == KZ_LONDON) ? "London" : (kz == KZ_NY_AM) ? "NY_AM" : "NY_PM";
   Print("[SB] FVG detected: ", (fvgBullish ? "BULLISH" : "BEARISH"),
         " | Zone: ", DoubleToString(fvgLower, (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS)),
         "-", DoubleToString(fvgUpper, (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS)),
         " | KZ: ", kzName,
         " | DispBody: ", DoubleToString(body2/atr, 2), "ATR");
}

//+------------------------------------------------------------------+
//| Try to enter on FVG fill                                           |
//+------------------------------------------------------------------+
void TryFVGEntry(double atr)
{
   if(g_tradesToday >= InpMaxTradesPerDay) return;
   if(g_tradesThisKZ >= InpMaxTradesPerKZ) return;
   if(CountMyPositions() > 0) return;  // One position at a time

   double close1 = iClose(_Symbol, PERIOD_M15, 1);
   double low1   = iLow(_Symbol, PERIOD_M15, 1);
   double high1  = iHigh(_Symbol, PERIOD_M15, 1);

   bool filled = false;

   if(g_pendingFVG.isBullish)
   {
      // Bullish FVG: wait for price to dip INTO the FVG zone (pullback)
      // Entry when low of bar touches FVG zone but closes above it
      if(low1 <= g_pendingFVG.upper && close1 >= g_pendingFVG.lower)
         filled = true;
   }
   else
   {
      // Bearish FVG: wait for price to rally INTO the FVG zone
      if(high1 >= g_pendingFVG.lower && close1 <= g_pendingFVG.upper)
         filled = true;
   }

   if(!filled) return;

   // --- Spread check ---
   g_sym.RefreshRates();
   double spreadPips = g_sym.Spread() * g_pt / g_pipSize;
   if(spreadPips > InpMaxSpreadPips)
   {
      Print("[SB] Skip: spread ", DoubleToString(spreadPips, 1), " > max");
      return;
   }

   // --- Entry ---
   bool isBuy = g_pendingFVG.isBullish;
   double entryPrice = isBuy ? g_sym.Ask() : g_sym.Bid();

   // SL: beyond the FVG + buffer
   double slDist;
   if(isBuy)
      slDist = entryPrice - g_pendingFVG.lower + InpSL_ATR * atr * 0.2;
   else
      slDist = g_pendingFVG.upper - entryPrice + InpSL_ATR * atr * 0.2;

   // Clamp SL
   double slPips = slDist / g_pipSize;
   if(slPips < InpMinSL_Pips) slDist = InpMinSL_Pips * g_pipSize;
   if(slPips > InpMaxSL_Pips)
   {
      Print("[SB] Skip: SL ", DoubleToString(slPips, 1), " pips > max");
      ResetFVG();
      return;
   }

   // TP: Session-specific R:R (London has more continuation, NY is capped)
   double rrRatio = InpTP_RR;  // default fallback
   if(g_pendingFVG.sourceKZ == KZ_LONDON)
      rrRatio = InpTP_RR_LDN;
   else if(g_pendingFVG.sourceKZ == KZ_NY_AM || g_pendingFVG.sourceKZ == KZ_NY_PM)
      rrRatio = InpTP_RR_NY;

   double tpDist = slDist * rrRatio;

   double sl, tp;
   int dig = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
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

   // --- Position sizing ---
   double tickValue = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
   double tickSize  = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   if(tickValue <= 0 || tickSize <= 0) return;

   double riskMoney = AccountInfoDouble(ACCOUNT_EQUITY) * InpRiskPct / 100.0;
   double lotRaw = riskMoney / (slDist / tickSize * tickValue);

   double lotMin  = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double lotMax  = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   double lotStep = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);

   double lots = MathFloor(lotRaw / lotStep) * lotStep;
   lots = MathMax(lots, lotMin);
   lots = MathMin(lots, MathMin(lotMax, InpMaxLot));
   if(lots < lotMin) return;

   // --- Execute ---
   Print("[SB] ENTRY: ", (isBuy ? "BUY" : "SELL"),
         " | Lots=", DoubleToString(lots, 2),
         " | SL=", DoubleToString(sl, dig),
         " | TP=", DoubleToString(tp, dig),
         " | FVG=", DoubleToString(g_pendingFVG.lower, dig),
         "-", DoubleToString(g_pendingFVG.upper, dig));

   bool ok;
   if(isBuy)
      ok = g_trade.Buy(lots, _Symbol, 0, sl, tp, InpComment);
   else
      ok = g_trade.Sell(lots, _Symbol, 0, sl, tp, InpComment);

   if(ok && g_trade.ResultRetcode() == TRADE_RETCODE_DONE)
   {
      g_tradesToday++;
      g_tradesThisKZ++;
      Print("[SB] Order executed: ticket=", g_trade.ResultOrder());
   }
   else
   {
      Print("[SB] Order FAILED: retcode=", g_trade.ResultRetcode(),
            " comment=", g_trade.ResultComment());
   }

   ResetFVG();  // Done with this FVG regardless
}

//+------------------------------------------------------------------+
//| Count my positions                                                 |
//+------------------------------------------------------------------+
int CountMyPositions()
{
   int count = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      if(g_pos.SelectByIndex(i))
         if(g_pos.Magic() == InpMagic && g_pos.Symbol() == _Symbol)
            count++;
   }
   return count;
}

//+------------------------------------------------------------------+
//| Close all positions                                                |
//+------------------------------------------------------------------+
void CloseAllPositions()
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      if(g_pos.SelectByIndex(i))
         if(g_pos.Magic() == InpMagic && g_pos.Symbol() == _Symbol)
            g_trade.PositionClose(g_pos.Ticket());
   }
}

//+------------------------------------------------------------------+
//| Tester metrics                                                     |
//+------------------------------------------------------------------+
double OnTester()
{
   double pf     = TesterStatistics(STAT_PROFIT_FACTOR);
   double trades = TesterStatistics(STAT_TRADES);
   double dd     = TesterStatistics(STAT_EQUITY_DDREL_PERCENT);
   if(dd <= 0) dd = 0.01;
   if(trades <= 0) return 0;
   return pf * MathSqrt(trades) / (1.0 + dd / 100.0);
}
//+------------------------------------------------------------------+
