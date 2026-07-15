//+------------------------------------------------------------------+
//| EA_SilverBullet_v2_Index.mq5                                     |
//| Copyright 2026, Max & Ngai Meo Coc                                |
//| Strategy: ICT Kill Zone + Displacement + FVG — INDEX variant      |
//|                                                                    |
//| Index changes from v2 (forex):                                     |
//| - London KZ disabled (pre-market noise for US indices)             |
//| - NY AM KZ extended to 16-19 (9-12 AM ET = full NYSE morning)     |
//| - NY PM KZ enabled 21-23 (2-4 PM ET = power hour / close)         |
//| - MaxSL_Pips widened to 300 (indices need wider stops)             |
//| - MinSL_Pips raised to 20 (too-tight SL = noise)                  |
//| - MaxSpreadPips raised to 15 (index CFD spreads wider)             |
//+------------------------------------------------------------------+
#property copyright "Max & Ngai Meo Coc"
#property link      "https://github.com"
#property version   "2.00"
#property strict

#include <Trade\Trade.mqh>
#include <Trade\PositionInfo.mqh>
#include <Trade\SymbolInfo.mqh>

//+------------------------------------------------------------------+
//| INPUTS                                                             |
//+------------------------------------------------------------------+
input group "=== Core Settings ==="
input bool   InpEnabled        = true;       // EA Enabled (kill switch)
input double InpRiskPct        = 1.0;        // Risk % per trade
input double InpMaxLot         = 0.50;       // Max lot size
input int    InpMagic          = 20260326;   // Magic number (index variant)
input string InpComment        = "SB2";      // Trade comment

// --- Kill Zones (Broker Time GMT+2) ---
input group "=== Kill Zones (Broker Time) ==="
input bool   InpUseLDN        = false;      // Use London Kill Zone (disabled: pre-market noise for US indices)
input int    InpLDN_Start     = 11;         // London KZ start hour (skip noisy 9-10)
input int    InpLDN_End       = 12;         // London KZ end hour
input bool   InpUseNYAM       = true;       // Use NY AM Kill Zone
input int    InpNYAM_Start    = 16;         // NY AM KZ start hour
input int    InpNYAM_End      = 19;         // NY AM KZ end hour (extended: 9-12 AM ET full NYSE morning)
input bool   InpUseNYPM       = true;       // Use NY PM Kill Zone (enabled: 2-4 PM ET power hour)
input int    InpNYPM_Start    = 21;         // NY PM KZ start hour (2 PM ET = 21 GMT+3)
input int    InpNYPM_End      = 23;         // NY PM KZ end hour (4 PM ET = 23 GMT+3)

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
input double InpTP_RR         = 1.50;       // TP as R:R ratio (default fallback)
input double InpTP_RR_LDN     = 1.50;       // TP R:R London KZ (uniform — session R:R 2.5 HURT DD)
input double InpTP_RR_NY      = 1.50;       // TP R:R NY KZ (uniform — tested S124)
input double InpMinSL_Pips    = 20.0;       // Min SL in pips (index: wider than forex)
input double InpMaxSL_Pips    = 300.0;      // Max SL in pips (index: ATR 30-80 pts, SL up to 120)

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
input double InpMaxSpreadPips   = 15.0;     // Max spread (pips) — index CFDs wider than forex
input double InpMaxDailyDD_Pct  = 3.0;      // Max daily DD %
input double InpMaxTotalDD_Pct  = 10.0;     // Max total equity DD % (from peak)
input bool   InpSkipFriday      = true;     // Skip Friday
input int    InpDeviation       = 30;       // Max deviation/slippage (points)
input int    InpRetryCount      = 3;        // Order retry attempts
input int    InpRetryDelayMs    = 500;      // Retry delay (ms)

//+------------------------------------------------------------------+
//| ENUMS                                                              |
//+------------------------------------------------------------------+
enum ENUM_KZ_TYPE { KZ_NONE, KZ_LONDON, KZ_NY_AM, KZ_NY_PM };

//+------------------------------------------------------------------+
//| STRUCTS                                                            |
//+------------------------------------------------------------------+
struct FVGZone
{
   double   upper;
   double   lower;
   bool     isBullish;
   datetime createTime;
   int      barAge;
   bool     active;
   ENUM_KZ_TYPE sourceKZ;
};

//+------------------------------------------------------------------+
//| GLOBALS                                                            |
//+------------------------------------------------------------------+
CTrade        g_trade;
CPositionInfo g_pos;
CSymbolInfo   g_sym;

int    g_hATR_H1;
int    g_hHTF_EMA;
int    g_hATR_D1_Regime;
double g_pt;
double g_pipSize;

// Daily tracking
int    g_tradesToday;
int    g_tradesThisKZ;
datetime g_lastTradeDay;
double g_dayStartEquity;
ENUM_KZ_TYPE g_lastKZ;

// Total DD tracking
double g_peakEquity;

// FVG tracking
FVGZone g_pendingFVG;

// Stats for chart
int    g_totalTrades;
int    g_totalWins;
string g_lastSignal;

//+------------------------------------------------------------------+
//| Detect best fill mode for symbol                                   |
//+------------------------------------------------------------------+
ENUM_ORDER_TYPE_FILLING DetectFillMode()
{
   long modes = SymbolInfoInteger(_Symbol, SYMBOL_FILLING_MODE);
   if((modes & SYMBOL_FILLING_FOK) != 0)  return ORDER_FILLING_FOK;
   if((modes & SYMBOL_FILLING_IOC) != 0)  return ORDER_FILLING_IOC;
   return ORDER_FILLING_RETURN;
}

//+------------------------------------------------------------------+
//| Expert initialization                                              |
//+------------------------------------------------------------------+
int OnInit()
{
   g_sym.Name(_Symbol);
   g_pt = g_sym.Point();
   if(g_pt <= 0) { Print("[SB2] ERROR: Invalid point"); return INIT_FAILED; }

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
   { Print("[SB2] ERROR: ATR handle failed"); return INIT_FAILED; }

   g_hHTF_EMA = INVALID_HANDLE;
   if(InpUseHTFBias)
   {
      g_hHTF_EMA = iMA(_Symbol, PERIOD_H4, InpHTF_EMA, 0, MODE_EMA, PRICE_CLOSE);
      if(g_hHTF_EMA == INVALID_HANDLE)
      { Print("[SB2] ERROR: H4 EMA handle failed"); return INIT_FAILED; }
   }

   g_hATR_D1_Regime = INVALID_HANDLE;
   if(InpUseVolRegime)
   {
      g_hATR_D1_Regime = iATR(_Symbol, PERIOD_D1, InpVolATR_Period);
      if(g_hATR_D1_Regime == INVALID_HANDLE)
      { Print("[SB2] ERROR: D1 ATR regime handle failed"); return INIT_FAILED; }
   }

   // Trade setup — adaptive fill mode
   g_trade.SetExpertMagicNumber(InpMagic);
   g_trade.SetTypeFilling(DetectFillMode());
   g_trade.SetDeviationInPoints(InpDeviation);

   // Reset
   g_tradesToday    = 0;
   g_tradesThisKZ   = 0;
   g_lastTradeDay   = 0;
   g_lastKZ         = KZ_NONE;
   g_dayStartEquity = AccountInfoDouble(ACCOUNT_EQUITY);
   g_peakEquity     = AccountInfoDouble(ACCOUNT_EQUITY);
   g_totalTrades    = 0;
   g_totalWins      = 0;
   g_lastSignal     = "---";
   ResetFVG();

   Print("[SB2] EA_SilverBullet v2.0 initialized on ", _Symbol,
         " | LDN=", InpUseLDN, " NYAM=", InpUseNYAM, " NYPM=", InpUseNYPM,
         " | Fill=", EnumToString(DetectFillMode()),
         " | Kill=", InpEnabled);
   return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
//| Expert deinitialization                                            |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   Comment("");  // Clear chart comment
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
//| Update chart comment dashboard                                     |
//+------------------------------------------------------------------+
void UpdateChartComment(ENUM_KZ_TYPE kz)
{
   double equity = AccountInfoDouble(ACCOUNT_EQUITY);
   double dailyDD = (g_dayStartEquity > 0)
      ? (g_dayStartEquity - equity) / g_dayStartEquity * 100.0
      : 0.0;
   double totalDD = (g_peakEquity > 0)
      ? (g_peakEquity - equity) / g_peakEquity * 100.0
      : 0.0;

   string kzName = "OFF";
   if(kz == KZ_LONDON) kzName = "LONDON";
   else if(kz == KZ_NY_AM) kzName = "NY AM";
   else if(kz == KZ_NY_PM) kzName = "NY PM";

   string fvgStatus = g_pendingFVG.active
      ? StringFormat("PENDING %s [%.5f-%.5f] age=%d",
           g_pendingFVG.isBullish ? "BUY" : "SELL",
           g_pendingFVG.lower, g_pendingFVG.upper,
           g_pendingFVG.barAge)
      : "---";

   Comment(
      "═══ EA_SilverBullet v2.0 ═══\n",
      "Enabled: ", (InpEnabled ? "YES" : "!! DISABLED !!"), "\n",
      "Symbol: ", _Symbol, " | Equity: $", DoubleToString(equity, 2), "\n",
      "Kill Zone: ", kzName, "\n",
      "Trades Today: ", g_tradesToday, "/", InpMaxTradesPerDay, "\n",
      "Daily DD: ", DoubleToString(dailyDD, 2), "% / ", DoubleToString(InpMaxDailyDD_Pct, 1), "%\n",
      "Total DD: ", DoubleToString(totalDD, 2), "% / ", DoubleToString(InpMaxTotalDD_Pct, 1), "%\n",
      "Peak Equity: $", DoubleToString(g_peakEquity, 2), "\n",
      "FVG: ", fvgStatus, "\n",
      "Last: ", g_lastSignal, "\n",
      "═════════════════════════"
   );
}

//+------------------------------------------------------------------+
//| Expert tick function                                               |
//+------------------------------------------------------------------+
void OnTick()
{
   // --- Kill switch ---
   if(!InpEnabled) return;

   // --- New bar detection (M15) ---
   static datetime lastBar = 0;
   datetime barTime = iTime(_Symbol, PERIOD_M15, 0);
   if(barTime == lastBar) return;
   lastBar = barTime;

   // --- Sufficient bars guard ---
   if(Bars(_Symbol, PERIOD_M15) < 50) return;

   // --- Time info ---
   MqlDateTime dt;
   TimeCurrent(dt);
   int hour = dt.hour;
   int dow  = dt.day_of_week;

   // --- Determine current kill zone (for chart comment even on off-days) ---
   ENUM_KZ_TYPE currentKZ = GetCurrentKZ(hour);

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

   // --- Update peak equity ---
   double equity = AccountInfoDouble(ACCOUNT_EQUITY);
   if(equity > g_peakEquity) g_peakEquity = equity;

   // --- Update chart dashboard ---
   UpdateChartComment(currentKZ);

   // --- Day filter ---
   if(dow == 0 || dow == 6) return;
   if(InpSkipFriday && dow == 5) return;

   // --- Daily DD guard ---
   if(g_dayStartEquity > 0 && (g_dayStartEquity - equity) / g_dayStartEquity * 100.0 > InpMaxDailyDD_Pct)
   {
      CloseAllPositions();
      g_lastSignal = "DAILY DD LIMIT HIT";
      return;
   }

   // --- Total DD guard (from peak equity) ---
   if(g_peakEquity > 0 && (g_peakEquity - equity) / g_peakEquity * 100.0 > InpMaxTotalDD_Pct)
   {
      CloseAllPositions();
      g_lastSignal = "TOTAL DD LIMIT HIT";
      return;
   }

   // --- Volatility Regime Filter (D1 ATR) ---
   if(InpUseVolRegime && g_hATR_D1_Regime != INVALID_HANDLE)
   {
      double d1Atr[];
      if(CopyBuffer(g_hATR_D1_Regime, 0, 1, 2, d1Atr) < 2) return;
      double currentATR = d1Atr[1];
      double prevATR    = d1Atr[0];
      double avgATR     = (currentATR + prevATR) / 2.0;

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
            return;
      }
   }

   // Reset KZ trade count when switching zones
   if(currentKZ != g_lastKZ)
   {
      g_tradesThisKZ = 0;
      g_lastKZ = currentKZ;
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

      if(g_pendingFVG.barAge > InpFVG_MaxWait)
      {
         Print("[SB2] FVG expired after ", InpFVG_MaxWait, " bars");
         g_lastSignal = "FVG expired";
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
//+------------------------------------------------------------------+
void ScanForDisplacementFVG(double atr, ENUM_KZ_TYPE kz)
{
   double open2  = iOpen(_Symbol, PERIOD_M15, 2);
   double close2 = iClose(_Symbol, PERIOD_M15, 2);
   double high2  = iHigh(_Symbol, PERIOD_M15, 2);
   double low2   = iLow(_Symbol, PERIOD_M15, 2);
   double range2 = high2 - low2;
   if(range2 <= 0) return;

   double body2 = MathAbs(close2 - open2);

   if(body2 < InpDispBodyATR * atr) return;
   if(body2 / range2 < InpDispBodyRatio) return;

   bool isBullDisp = (close2 > open2);

   double high3 = iHigh(_Symbol, PERIOD_M15, 3);
   double low3  = iLow(_Symbol, PERIOD_M15, 3);
   double high1 = iHigh(_Symbol, PERIOD_M15, 1);
   double low1  = iLow(_Symbol, PERIOD_M15, 1);

   double fvgUpper = 0, fvgLower = 0;
   bool hasFVG = false;
   bool fvgBullish = false;

   if(isBullDisp)
   {
      fvgLower = high3;
      fvgUpper = low1;
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
      fvgUpper = low3;
      fvgLower = high1;
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

      if(fvgBullish && price < h4ema)
      {
         Print("[SB2] Skip: Bullish FVG but price below H4 EMA");
         return;
      }
      if(!fvgBullish && price > h4ema)
      {
         Print("[SB2] Skip: Bearish FVG but price above H4 EMA");
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
   g_lastSignal = StringFormat("%s FVG %s", kzName, fvgBullish ? "BUY" : "SELL");
   Print("[SB2] FVG detected: ", (fvgBullish ? "BULLISH" : "BEARISH"),
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
   if(CountMyPositions() > 0) return;

   double close1 = iClose(_Symbol, PERIOD_M15, 1);
   double low1   = iLow(_Symbol, PERIOD_M15, 1);
   double high1  = iHigh(_Symbol, PERIOD_M15, 1);

   bool filled = false;

   if(g_pendingFVG.isBullish)
   {
      if(low1 <= g_pendingFVG.upper && close1 >= g_pendingFVG.lower)
         filled = true;
   }
   else
   {
      if(high1 >= g_pendingFVG.lower && close1 <= g_pendingFVG.upper)
         filled = true;
   }

   if(!filled) return;

   // --- Spread check ---
   g_sym.RefreshRates();
   double spreadPips = g_sym.Spread() * g_pt / g_pipSize;
   if(spreadPips > InpMaxSpreadPips)
   {
      Print("[SB2] Skip: spread ", DoubleToString(spreadPips, 1), " > max");
      g_lastSignal = "SPREAD REJECT";
      return;
   }

   // --- Entry price ---
   bool isBuy = g_pendingFVG.isBullish;
   double entryPrice = isBuy ? g_sym.Ask() : g_sym.Bid();

   // --- SL distance ---
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
      Print("[SB2] Skip: SL ", DoubleToString(slPips, 1), " pips > max");
      g_lastSignal = "SL TOO WIDE";
      ResetFVG();
      return;
   }

   // --- TP: Session-specific R:R ---
   double rrRatio = InpTP_RR;
   if(g_pendingFVG.sourceKZ == KZ_LONDON)
      rrRatio = InpTP_RR_LDN;
   else if(g_pendingFVG.sourceKZ == KZ_NY_AM || g_pendingFVG.sourceKZ == KZ_NY_PM)
      rrRatio = InpTP_RR_NY;

   double tpDist = slDist * rrRatio;

   // --- Compute SL / TP prices ---
   int dig = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
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

   // --- Stop level / freeze level broker check ---
   long stopLevelPts = SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL);
   long freezeLevelPts = SymbolInfoInteger(_Symbol, SYMBOL_TRADE_FREEZE_LEVEL);
   double minStopDist = MathMax((double)stopLevelPts, (double)freezeLevelPts) * g_pt;

   if(MathAbs(entryPrice - sl) < minStopDist)
   {
      Print("[SB2] Skip: SL too close for broker (stopLevel=", stopLevelPts, " freezeLevel=", freezeLevelPts, ")");
      g_lastSignal = "BROKER STOP LEVEL";
      ResetFVG();
      return;
   }
   if(MathAbs(tp - entryPrice) < minStopDist)
   {
      Print("[SB2] Skip: TP too close for broker");
      g_lastSignal = "BROKER TP LEVEL";
      ResetFVG();
      return;
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

   // --- Execute with retry ---
   Print("[SB2] ENTRY: ", (isBuy ? "BUY" : "SELL"),
         " | Lots=", DoubleToString(lots, 2),
         " | SL=", DoubleToString(sl, dig),
         " | TP=", DoubleToString(tp, dig),
         " | RR=", DoubleToString(rrRatio, 1),
         " | FVG=", DoubleToString(g_pendingFVG.lower, dig),
         "-", DoubleToString(g_pendingFVG.upper, dig));

   bool executed = false;
   for(int attempt = 1; attempt <= InpRetryCount; attempt++)
   {
      g_sym.RefreshRates();
      entryPrice = isBuy ? g_sym.Ask() : g_sym.Bid();

      bool ok;
      if(isBuy)
         ok = g_trade.Buy(lots, _Symbol, 0, sl, tp, InpComment);
      else
         ok = g_trade.Sell(lots, _Symbol, 0, sl, tp, InpComment);

      uint retcode = g_trade.ResultRetcode();
      if(ok && retcode == TRADE_RETCODE_DONE)
      {
         g_tradesToday++;
         g_tradesThisKZ++;
         g_totalTrades++;
         g_lastSignal = StringFormat("%s %s @ %.5f", isBuy ? "BUY" : "SELL",
            (g_pendingFVG.sourceKZ == KZ_LONDON) ? "LDN" : "NY",
            entryPrice);
         Print("[SB2] Order executed: ticket=", g_trade.ResultOrder(), " attempt=", attempt);
         executed = true;
         break;
      }

      // Transient errors worth retrying
      if(retcode == TRADE_RETCODE_REQUOTE ||
         retcode == TRADE_RETCODE_PRICE_OFF ||
         retcode == TRADE_RETCODE_CONNECTION ||
         retcode == TRADE_RETCODE_TIMEOUT)
      {
         Print("[SB2] Retry ", attempt, "/", InpRetryCount,
               " retcode=", retcode, " comment=", g_trade.ResultComment());
         if(attempt < InpRetryCount) Sleep(InpRetryDelayMs * attempt);
         continue;
      }

      // Non-transient errors — stop retrying
      Print("[SB2] Order FAILED (non-transient): retcode=", retcode,
            " comment=", g_trade.ResultComment());
      g_lastSignal = StringFormat("FAILED rc=%d", retcode);
      break;
   }

   ResetFVG();
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
//| Trade transaction handler (track wins/losses)                      |
//+------------------------------------------------------------------+
void OnTradeTransaction(const MqlTradeTransaction &trans,
                        const MqlTradeRequest &request,
                        const MqlTradeResult &result)
{
   if(trans.type != TRADE_TRANSACTION_DEAL_ADD) return;

   ulong deal = trans.deal;
   if(deal == 0) return;

   if(HistoryDealSelect(deal))
   {
      long magic = HistoryDealGetInteger(deal, DEAL_MAGIC);
      if(magic != InpMagic) return;

      ENUM_DEAL_ENTRY entry = (ENUM_DEAL_ENTRY)HistoryDealGetInteger(deal, DEAL_ENTRY);
      if(entry == DEAL_ENTRY_OUT || entry == DEAL_ENTRY_INOUT)
      {
         double profit = HistoryDealGetDouble(deal, DEAL_PROFIT)
                       + HistoryDealGetDouble(deal, DEAL_SWAP)
                       + HistoryDealGetDouble(deal, DEAL_COMMISSION);
         if(profit > 0) g_totalWins++;
      }
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
