//+------------------------------------------------------------------+
//| EA_WVFScalp.mq5 — Williams Vix Fix Scalping (Short Only)        |
//| Period: M5 (original) / M15  |  Style: Mean-Reversion Scalp     |
//|                                                                   |
//| SOURCE: ForexFactory thread #1357382 by colbster (Aug 2025)      |
//| https://www.forexfactory.com/thread/1357382                      |
//|                                                                   |
//| EDGE HYPOTHESIS:                                                  |
//| Williams Vix Fix (inverted) detects potential market TOPS.        |
//| Low WVF reading = price near recent highs = potential reversal.  |
//| Combined with Stochastic overbought + resistance confluence,     |
//| we sell the reversal from overbought into resistance.            |
//|                                                                   |
//| MECHANISM:                                                        |
//| 1. WVF threshold adaptive (minimum of recent "green" peaks)      |
//| 2. WVF drops below threshold (near top detected)                 |
//| 3. Wait for WVF to start rising (exhaustion signal)              |
//| 4. Stochastic %K above 80 crossed back below %D (overbought)    |
//| 5. Price near resistance (prev session high, 3-day high, VWAP)   |
//| 6. SELL at market, SL above swing high, TP = 1:1                |
//|                                                                   |
//| DIRECTION: Short only (original method)                          |
//|                                                                   |
//| Max | 2026-04-12 | v1.0                                         |
//+------------------------------------------------------------------+
#property copyright "Max - EA_WVFScalp v1.0"
#property version   "1.00"
#property strict

#include <Trade\Trade.mqh>

//+------------------------------------------------------------------+
//| Input Parameters                                                  |
//+------------------------------------------------------------------+
input group "=== General ==="
input ulong    InpMagic         = 701201;    // Magic Number
input int      InpDeviation     = 30;        // Max Slippage (pts)
input bool     InpKillSwitch    = false;     // Kill Switch

input group "=== Williams Vix Fix ==="
input int      InpWVFPeriod     = 22;        // WVF Lookback Period
input int      InpBBPeriod      = 20;        // BB Period (for green bar detection)
input double   InpBBMult        = 2.0;       // BB Multiplier
input int      InpThreshLookback= 100;       // Lookback bars for adaptive threshold

input group "=== Stochastic ==="
input int      InpStochK        = 14;        // Stochastic %K Period
input int      InpStochD        = 3;         // Stochastic %D Smoothing
input int      InpStochSlow     = 3;         // Stochastic Slowing
input double   InpStochOB       = 80;        // Overbought Level
input double   InpStochSkip     = 50;        // Skip if Stoch below this before entry

input group "=== Resistance Detection ==="
input int      InpResistLookbackD = 3;       // Days lookback for resistance high
input int      InpSessionLookbackD= 1;       // Previous session lookback
input double   InpNearPct       = 0.3;       // "Near" resistance = within X% of ATR
input int      InpATRPeriod     = 14;        // ATR Period for "near" detection
input bool     InpUseVWAP       = true;      // Use session VWAP as resistance

input group "=== Entry / Exit ==="
input double   InpMinSLPoints   = 60;        // Minimum SL distance (points)
input double   InpMaxSLPoints   = 500;       // Maximum SL distance (points)
input double   InpRRRatio       = 1.0;       // TP = SL x this (1.0 = 1:1)
input int      InpMaxBarsInTrade= 20;        // Max bars before time exit

input group "=== Day Filters ==="
input bool     InpMon           = true;      // Trade Monday
input bool     InpTue           = true;      // Trade Tuesday
input bool     InpWed           = true;      // Trade Wednesday
input bool     InpThu           = true;      // Trade Thursday
input bool     InpFri           = true;      // Trade Friday

input group "=== Session Filter ==="
input int      InpSessionStartH = 0;         // Session start hour (server time)
input int      InpSessionEndH   = 23;        // Session end hour (server time)

input group "=== Risk Management ==="
input double   InpRiskPct       = 0.50;      // Risk per trade (%)
input double   InpMaxLot        = 0.50;      // Max lot
input int      InpMaxPerDay     = 3;         // Max trades per day
input double   InpDailyDDPct    = 4.0;       // Daily DD kill (%)

input group "=== Datalog ==="
input bool     InpDatalog       = true;      // Enable CSV signal log

//+------------------------------------------------------------------+
//| Globals                                                           |
//+------------------------------------------------------------------+
CTrade         g_trade;
int            g_hStoch;
int            g_hATR;
datetime       g_lastBar;
datetime       g_todayDate;
double         g_dayStartBal;
int            g_tradesToday;
int            g_logHandle;
int            g_barsHeld;

// WVF State Machine
bool           g_wasAboveThresh;  // WVF was above threshold
bool           g_crossedBelow;    // WVF crossed below threshold (fresh cross)
double         g_swingHigh;       // Swing high during sub-threshold zone
bool           g_stochWasOB;      // Stochastic was overbought recently
bool           g_stochCrossedDown;// Stochastic K crossed below D after OB

// VWAP tracking
datetime       g_vwapSessionStart;
double         g_vwapCumPV;       // cumulative price*volume
double         g_vwapCumVol;      // cumulative volume

//+------------------------------------------------------------------+
int OnInit()
{
   if(InpKillSwitch) { Print("[WVF] Kill switch ON"); return INIT_SUCCEEDED; }

   g_trade.SetExpertMagicNumber(InpMagic);
   g_trade.SetDeviationInPoints(InpDeviation);
   g_trade.SetTypeFilling(ORDER_FILLING_FOK);

   g_hStoch = iStochastic(_Symbol, PERIOD_CURRENT, InpStochK, InpStochD, InpStochSlow, MODE_SMA, STO_LOWHIGH);
   g_hATR   = iATR(_Symbol, PERIOD_CURRENT, InpATRPeriod);

   if(g_hStoch == INVALID_HANDLE || g_hATR == INVALID_HANDLE)
   { Print("[WVF] FATAL: Indicator init failed"); return INIT_FAILED; }

   g_lastBar        = 0;
   g_todayDate      = 0;
   g_dayStartBal    = AccountInfoDouble(ACCOUNT_BALANCE);
   g_tradesToday    = 0;
   g_barsHeld       = 0;
   g_wasAboveThresh = false;
   g_crossedBelow   = false;
   g_swingHigh      = 0;
   g_stochWasOB     = false;
   g_stochCrossedDown = false;
   g_vwapSessionStart = 0;
   g_vwapCumPV      = 0;
   g_vwapCumVol     = 0;

   if(InpDatalog)
   {
      string fname = "WVFScalp_datalog_" + _Symbol + ".csv";
      g_logHandle = FileOpen(fname, FILE_WRITE|FILE_CSV|FILE_COMMON, ',');
      if(g_logHandle != INVALID_HANDLE)
         FileWrite(g_logHandle,
            "Time","Signal","Price","WVF","Threshold","StochK","StochD",
            "SwingHigh","NearResist","SL","TP","Lot","DoW","Reason");
   }

   PrintFormat("[WVF] Init OK: %s %s Magic=%d WVFPer=%d BB=%d/%.1f StochK=%d",
               _Symbol, EnumToString(_Period), InpMagic,
               InpWVFPeriod, InpBBPeriod, InpBBMult, InpStochK);
   return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   if(g_hStoch != INVALID_HANDLE) IndicatorRelease(g_hStoch);
   if(g_hATR   != INVALID_HANDLE) IndicatorRelease(g_hATR);
   if(g_logHandle != INVALID_HANDLE) FileClose(g_logHandle);
}

//+------------------------------------------------------------------+
bool IsTradingDay(int dow)
{
   switch(dow)
   {
      case 1: return InpMon;
      case 2: return InpTue;
      case 3: return InpWed;
      case 4: return InpThu;
      case 5: return InpFri;
      default: return false;
   }
}

//+------------------------------------------------------------------+
int CountMyPositions()
{
   int count = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0) continue;
      if(PositionGetInteger(POSITION_MAGIC) == (long)InpMagic &&
         PositionGetString(POSITION_SYMBOL) == _Symbol)
         count++;
   }
   return count;
}

//+------------------------------------------------------------------+
double CalcLotSize(double slPoints)
{
   if(slPoints <= 0) return 0;
   double balance  = AccountInfoDouble(ACCOUNT_BALANCE);
   double riskAmt  = balance * InpRiskPct / 100.0;
   double tickSize = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   double tickVal  = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
   double point    = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   if(tickSize == 0 || tickVal == 0 || point == 0) return 0;
   double pointVal = tickVal * point / tickSize;
   double lot = riskAmt / (slPoints * pointVal);
   double minLot  = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double maxLot  = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   double lotStep = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   lot = MathMax(lot, minLot);
   lot = MathMin(lot, InpMaxLot);
   lot = MathMin(lot, maxLot);
   if(lotStep > 0) lot = MathFloor(lot / lotStep) * lotStep;
   return NormalizeDouble(lot, 2);
}

//+------------------------------------------------------------------+
// Calculate Williams Vix Fix for bar[shift]
// WVF = (Highest(Close, N) - Low[shift]) / Highest(Close, N) * 100
double CalcWVF(int shift)
{
   // Get highest close over N bars ending at shift
   double highestClose = 0;
   for(int i = shift; i < shift + InpWVFPeriod; i++)
   {
      double c = iClose(_Symbol, PERIOD_CURRENT, i);
      if(c > highestClose) highestClose = c;
   }
   if(highestClose <= 0) return 0;

   double low = iLow(_Symbol, PERIOD_CURRENT, shift);
   return (highestClose - low) / highestClose * 100.0;
}

//+------------------------------------------------------------------+
// Calculate adaptive threshold: find minimum peak of WVF values
// that exceeded the BB upper band ("green bars")
double CalcAdaptiveThreshold()
{
   // First, compute WVF values and find "green bar" peaks
   int lookback = InpThreshLookback;
   if(lookback > Bars(_Symbol, PERIOD_CURRENT) - InpWVFPeriod - InpBBPeriod)
      lookback = Bars(_Symbol, PERIOD_CURRENT) - InpWVFPeriod - InpBBPeriod - 1;
   if(lookback < InpBBPeriod + 1) return 0;

   // Calculate WVF array
   double wvfArr[];
   ArrayResize(wvfArr, lookback);
   for(int i = 0; i < lookback; i++)
      wvfArr[i] = CalcWVF(i + 1); // shift by 1 for non-repaint

   // Calculate BB of WVF: mean and stddev over BB period
   // We scan for "green bars" = WVF > BB upper band
   double minGreenPeak = DBL_MAX;
   bool   foundGreen   = false;

   for(int i = InpBBPeriod; i < lookback; i++)
   {
      // BB of WVF at position i
      double sum = 0, sumSq = 0;
      for(int j = i - InpBBPeriod; j < i; j++)
      {
         sum   += wvfArr[j];
         sumSq += wvfArr[j] * wvfArr[j];
      }
      double mean = sum / InpBBPeriod;
      double var  = sumSq / InpBBPeriod - mean * mean;
      double std  = (var > 0) ? MathSqrt(var) : 0;
      double bbUpper = mean + InpBBMult * std;

      // Is this bar "green"? WVF > BB upper
      if(wvfArr[i] > bbUpper)
      {
         // Check if it's a local peak (higher than neighbors)
         bool isPeak = true;
         if(i > 0 && wvfArr[i - 1] > wvfArr[i]) isPeak = false;
         if(i < lookback - 1 && wvfArr[i + 1] > wvfArr[i]) isPeak = false;

         if(isPeak || !foundGreen) // Take any green bar if no peak found
         {
            if(wvfArr[i] < minGreenPeak)
            {
               minGreenPeak = wvfArr[i];
               foundGreen   = true;
            }
         }
      }
   }

   // If no green bars found, use a percentile-based fallback
   if(!foundGreen)
   {
      // Use 75th percentile of WVF as threshold
      double sorted[];
      ArrayCopy(sorted, wvfArr);
      ArraySort(sorted);
      int idx75 = (int)(lookback * 0.75);
      if(idx75 >= lookback) idx75 = lookback - 1;
      return sorted[idx75];
   }

   return minGreenPeak;
}

//+------------------------------------------------------------------+
// Get 3-day and previous session high as resistance levels
// Returns the highest of: 3-day high, previous session high
double GetResistanceHigh()
{
   // 3-day high on current timeframe
   int barsPerDay = 0;
   int period = PeriodSeconds(PERIOD_CURRENT);
   if(period > 0) barsPerDay = 86400 / period;
   if(barsPerDay <= 0) barsPerDay = 288; // M5 default

   int lookbackBars = barsPerDay * InpResistLookbackD;
   if(lookbackBars > Bars(_Symbol, PERIOD_CURRENT) - 1)
      lookbackBars = Bars(_Symbol, PERIOD_CURRENT) - 1;

   double high3d = 0;
   for(int i = 1; i <= lookbackBars; i++)
   {
      double h = iHigh(_Symbol, PERIOD_CURRENT, i);
      if(h > high3d) high3d = h;
   }

   // Previous session high (use D1 bar[1])
   double prevDayHigh = iHigh(_Symbol, PERIOD_D1, 1);

   return MathMax(high3d, prevDayHigh);
}

//+------------------------------------------------------------------+
// Simple session VWAP calculation
double GetVWAP()
{
   if(g_vwapCumVol <= 0) return 0;
   return g_vwapCumPV / g_vwapCumVol;
}

//+------------------------------------------------------------------+
// Update VWAP with new bar data
void UpdateVWAP(int shift)
{
   MqlDateTime dt;
   TimeToStruct(iTime(_Symbol, PERIOD_CURRENT, shift), dt);
   datetime barDate = StringToTime(StringFormat("%04d.%02d.%02d", dt.year, dt.mon, dt.day));

   // Reset VWAP at session start (new day)
   if(barDate != g_vwapSessionStart)
   {
      g_vwapSessionStart = barDate;
      g_vwapCumPV  = 0;
      g_vwapCumVol = 0;
   }

   double typPrice = (iHigh(_Symbol, PERIOD_CURRENT, shift) +
                      iLow(_Symbol, PERIOD_CURRENT, shift) +
                      iClose(_Symbol, PERIOD_CURRENT, shift)) / 3.0;
   long vol = iTickVolume(_Symbol, PERIOD_CURRENT, shift);
   if(vol <= 0) vol = 1;

   g_vwapCumPV  += typPrice * vol;
   g_vwapCumVol += vol;
}

//+------------------------------------------------------------------+
// Check if price is "near" any resistance level
bool IsNearResistance(double price, double atr)
{
   double nearDist = atr * InpNearPct;

   // 3-day high + previous session high
   double resistHigh = GetResistanceHigh();
   if(resistHigh > 0 && MathAbs(price - resistHigh) <= nearDist)
      return true;

   // VWAP
   if(InpUseVWAP)
   {
      double vwap = GetVWAP();
      if(vwap > 0 && MathAbs(price - vwap) <= nearDist)
         return true;
   }

   // Previous day high specifically
   double prevDayH = iHigh(_Symbol, PERIOD_D1, 1);
   if(prevDayH > 0 && MathAbs(price - prevDayH) <= nearDist)
      return true;

   return false;
}

//+------------------------------------------------------------------+
void CloseAllPositions()
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0) continue;
      if(PositionGetInteger(POSITION_MAGIC) == (long)InpMagic &&
         PositionGetString(POSITION_SYMBOL) == _Symbol)
      {
         g_trade.PositionClose(ticket);
      }
   }
   g_barsHeld = 0;
}

//+------------------------------------------------------------------+
void OnTick()
{
   if(InpKillSwitch) return;

   datetime barTime = iTime(_Symbol, PERIOD_CURRENT, 0);
   if(barTime == g_lastBar) return;
   g_lastBar = barTime;

   MqlDateTime dt;
   TimeToStruct(barTime, dt);
   datetime today = StringToTime(StringFormat("%04d.%02d.%02d", dt.year, dt.mon, dt.day));

   // Day reset
   if(today != g_todayDate)
   {
      g_todayDate      = today;
      g_tradesToday    = 0;
      g_dayStartBal    = AccountInfoDouble(ACCOUNT_BALANCE);
      g_wasAboveThresh = false;
      g_crossedBelow   = false;
      g_swingHigh      = 0;
      g_stochWasOB     = false;
      g_stochCrossedDown = false;
   }

   // Update VWAP
   UpdateVWAP(1); // Update with bar[1] (closed bar)

   //=== Manage existing positions ===
   if(CountMyPositions() > 0)
   {
      g_barsHeld++;
      if(g_barsHeld >= InpMaxBarsInTrade)
      {
         PrintFormat("[WVF] Time exit after %d bars", g_barsHeld);
         CloseAllPositions();
      }
      return;
   }

   //=== Entry logic (all on bar[1] for non-repaint) ===

   // Basic filters
   if(!IsTradingDay(dt.day_of_week)) return;
   if(dt.hour < InpSessionStartH || dt.hour >= InpSessionEndH) return;
   if(g_tradesToday >= InpMaxPerDay) return;

   // Daily DD kill
   double ddPct = (g_dayStartBal > 0)
                  ? (g_dayStartBal - AccountInfoDouble(ACCOUNT_EQUITY)) / g_dayStartBal * 100.0
                  : 0;
   if(ddPct >= InpDailyDDPct) return;

   // Need enough bars
   int minBars = InpWVFPeriod + InpThreshLookback + 10;
   if(Bars(_Symbol, PERIOD_CURRENT) < minBars) return;

   // Read ATR
   double atr[];
   if(CopyBuffer(g_hATR, 0, 1, 1, atr) < 1) return;
   if(atr[0] <= 0) return;

   // Read Stochastic
   double stochK[], stochD[];
   if(CopyBuffer(g_hStoch, 0, 1, 3, stochK) < 3) return; // K line, bars 1-3
   if(CopyBuffer(g_hStoch, 1, 1, 3, stochD) < 3) return; // D line, bars 1-3

   // Calculate WVF for bar[1] and bar[2]
   double wvf1 = CalcWVF(1);
   double wvf2 = CalcWVF(2);

   // Calculate adaptive threshold
   double threshold = CalcAdaptiveThreshold();
   if(threshold <= 0) return;

   double close1 = iClose(_Symbol, PERIOD_CURRENT, 1);
   double high1  = iHigh(_Symbol, PERIOD_CURRENT, 1);
   double point  = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   int    digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);

   //=== State machine: track WVF threshold crossings ===

   // Was WVF above threshold on bar[2]?
   if(wvf2 > threshold)
   {
      g_wasAboveThresh = true;
      g_crossedBelow   = false;
      g_swingHigh      = 0; // Reset swing high
   }

   // Fresh cross below threshold on bar[1]?
   if(g_wasAboveThresh && wvf1 <= threshold && wvf2 > threshold)
   {
      g_crossedBelow = true;
      g_swingHigh    = high1; // Start tracking swing high
   }

   // Update swing high while below threshold
   if(g_crossedBelow && wvf1 <= threshold)
   {
      if(high1 > g_swingHigh)
         g_swingHigh = high1;
   }

   // If WVF goes back above threshold, reset
   if(g_crossedBelow && wvf1 > threshold)
   {
      g_crossedBelow = false;
      g_wasAboveThresh = true; // Ready for next fresh cross
      g_swingHigh = 0;
   }

   //=== Stochastic state machine ===
   // Check if Stoch K was recently above OB level
   if(stochK[2] > InpStochOB || stochK[1] > InpStochOB)
      g_stochWasOB = true;

   // Check if K crossed below D after being OB
   // stochK[0] = bar[1], stochK[1] = bar[2]
   g_stochCrossedDown = false;
   if(g_stochWasOB)
   {
      // K was above D on bar[2], now below D on bar[1]
      if(stochK[1] >= stochD[1] && stochK[0] < stochD[0])
         g_stochCrossedDown = true;
      // Or K already below D and was recently OB
      if(stochK[0] < stochD[0] && stochK[0] < InpStochOB)
         g_stochCrossedDown = true;
   }

   // Reset stoch OB flag if K drops below skip level
   if(stochK[0] < InpStochSkip)
   {
      g_stochWasOB = false;
      g_stochCrossedDown = false;
   }

   //=== Entry signal check ===
   // Conditions:
   // 1. g_crossedBelow = true (WVF crossed below threshold = fresh cross)
   // 2. wvf1 > wvf2 (WVF rising = first rising bar after cross below)
   // 3. g_stochCrossedDown = true (Stochastic confirmed overbought)
   // 4. Price near resistance

   bool wvfRising    = (wvf1 > wvf2) && g_crossedBelow;
   bool stochOK      = g_stochCrossedDown;
   bool nearResist   = IsNearResistance(close1, atr[0]);

   // Log signal state for debugging
   string reason = "";

   if(!g_crossedBelow)         { reason = "NO_FRESH_CROSS"; }
   else if(!wvfRising)         { reason = "WVF_NOT_RISING"; }
   else if(!stochOK)           { reason = "STOCH_NOT_CONFIRMED"; }
   else if(!nearResist)        { reason = "NOT_NEAR_RESIST"; }
   else
   {
      // All conditions met — check false signal filter
      // If bar[1]'s high >= swing high, this is a false signal
      if(g_swingHigh > 0 && high1 >= g_swingHigh)
      {
         reason = "FALSE_SIGNAL_HIGH_REACHED";
         LogSignal(barTime, "SKIP", close1, wvf1, threshold, stochK[0], stochD[0],
                   g_swingHigh, nearResist, 0, 0, 0, dt.day_of_week, reason);
         return;
      }

      // Calculate SL and TP
      double slPrice = g_swingHigh + point; // 1 tick above swing high
      double slDist  = slPrice - SymbolInfoDouble(_Symbol, SYMBOL_BID);

      // Check SL distance bounds
      if(slDist / point < InpMinSLPoints)
      {
         reason = "SL_TOO_SMALL";
         LogSignal(barTime, "SKIP", close1, wvf1, threshold, stochK[0], stochD[0],
                   g_swingHigh, nearResist, slPrice, 0, 0, dt.day_of_week, reason);
         return;
      }
      if(slDist / point > InpMaxSLPoints)
      {
         reason = "SL_TOO_LARGE";
         LogSignal(barTime, "SKIP", close1, wvf1, threshold, stochK[0], stochD[0],
                   g_swingHigh, nearResist, slPrice, 0, 0, dt.day_of_week, reason);
         return;
      }

      // Check stop level
      double stopLevel = SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL) * point;
      double price = SymbolInfoDouble(_Symbol, SYMBOL_BID);
      if(slDist < stopLevel)
         slPrice = NormalizeDouble(price + stopLevel + point, digits);

      // TP = 1:1
      slDist = slPrice - price; // recalc after adjustment
      double tpPrice = NormalizeDouble(price - slDist * InpRRRatio, digits);
      slPrice = NormalizeDouble(slPrice, digits);

      // Lot size
      double slPoints = slDist / point;
      double lot = CalcLotSize(slPoints);
      if(lot <= 0)
      {
         reason = "LOT_ZERO";
         LogSignal(barTime, "SKIP", price, wvf1, threshold, stochK[0], stochD[0],
                   g_swingHigh, nearResist, slPrice, tpPrice, 0, dt.day_of_week, reason);
         return;
      }

      // SELL
      string comment = StringFormat("WVF|T=%.2f|SK=%.0f|SH=%.1f",
                                    threshold, stochK[0], g_swingHigh);

      bool ok = g_trade.PositionOpen(_Symbol, ORDER_TYPE_SELL, lot, price,
                                      slPrice, tpPrice, comment);
      if(ok)
      {
         g_tradesToday++;
         g_barsHeld       = 0;
         g_crossedBelow   = false; // Reset for next signal
         g_wasAboveThresh = false;
         g_stochWasOB     = false;
         g_stochCrossedDown = false;

         PrintFormat("[WVF] SELL %.2f @ %.5f SL=%.5f TP=%.5f WVF=%.2f Thresh=%.2f StochK=%.0f",
                     lot, price, slPrice, tpPrice, wvf1, threshold, stochK[0]);
         LogSignal(barTime, "SELL", price, wvf1, threshold, stochK[0], stochD[0],
                   g_swingHigh, nearResist, slPrice, tpPrice, lot, dt.day_of_week, "EXECUTED");
      }
      return;
   }

   // Log skipped signals (only when WVF is below threshold and conditions partially met)
   if(g_crossedBelow && wvfRising)
   {
      LogSignal(barTime, "SKIP", close1, wvf1, threshold, stochK[0], stochD[0],
                g_swingHigh, nearResist, 0, 0, 0, dt.day_of_week, reason);
   }
}

//+------------------------------------------------------------------+
void LogSignal(datetime time, string sig, double price, double wvf,
               double threshold, double stochK, double stochD,
               double swingH, bool nearR, double sl, double tp,
               double lot, int dow, string reason)
{
   if(!InpDatalog || g_logHandle == INVALID_HANDLE) return;
   int digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
   FileWrite(g_logHandle,
      TimeToString(time, TIME_DATE|TIME_MINUTES),
      sig, DoubleToString(price, digits),
      DoubleToString(wvf, 4), DoubleToString(threshold, 4),
      DoubleToString(stochK, 1), DoubleToString(stochD, 1),
      DoubleToString(swingH, digits), nearR ? "YES" : "NO",
      DoubleToString(sl, digits), DoubleToString(tp, digits),
      DoubleToString(lot, 2),
      IntegerToString(dow), reason);
   FileFlush(g_logHandle);
}
//+------------------------------------------------------------------+
