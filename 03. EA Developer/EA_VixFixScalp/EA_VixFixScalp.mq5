//+------------------------------------------------------------------+
//| EA_VixFixScalp.mq5 — Williams Vix Fix Scalper (Short-Only)       |
//| Based on ForexFactory thread by colbster                          |
//| Symbol: Any (default XAUUSD+)  |  Period: M5  |  Style: Scalp    |
//|                                                                   |
//| EDGE HYPOTHESIS:                                                  |
//| Williams Vix Fix identifies local tops (low WVF = price near      |
//| recent highs). When WVF crosses below adaptive threshold after    |
//| a spike, then starts rising = price pulling back from recovery.   |
//| Combined with Stochastic overbought reversal + resistance         |
//| confluence = short entry at potential exhaustion point.            |
//|                                                                   |
//| MECHANISM:                                                        |
//| 1. WVF = (Highest(Close,22) - Low) / Highest(Close,22) * 100     |
//| 2. Bollinger Band on WVF identifies "green bars" (spikes)         |
//| 3. Adaptive threshold = min peak of green bars over lookback      |
//| 4. Entry: WVF crosses below threshold -> first rising WVF bar     |
//| 5. Confirmation: Stoch %K was >80, now crossed below %D           |
//| 6. Confluence: Price near resistance (3-day high, prev day high,  |
//|    or session VWAP)                                                |
//| 7. SL: 1 tick above swing high since WVF spike                    |
//| 8. TP: 1:1 RR                                                     |
//|                                                                   |
//| SIGNALS ON BAR[1] ONLY — no repaint, no lookahead.                |
//| Max | 2026-04-12 | v1.0                                          |
//+------------------------------------------------------------------+
#property copyright "Max — EA_VixFixScalp v1.0"
#property link      ""
#property version   "1.00"
#property strict

//+------------------------------------------------------------------+
//| Input Parameters                                                  |
//+------------------------------------------------------------------+
input group "=== General ==="
input ulong    InpMagic         = 206001;     // Magic Number
input int      InpDeviation     = 30;         // Max Slippage (pts)
input bool     InpKillSwitch    = false;      // Kill Switch (disable all)
input int      InpDirection     = 0;          // Direction: 0=Sell, 1=Buy, 2=Both

input group "=== Williams Vix Fix ==="
input int      InpWVF_Period    = 22;         // WVF Lookback (highest close)
input int      InpBB_Period     = 20;         // BB Period on WVF
input double   InpBB_Mult       = 2.0;        // BB StdDev Multiplier
input int      InpThreshLookback= 200;        // Bars to scan for adaptive threshold
input int      InpSignalLookback= 15;         // Bars to scan for fresh cross

input group "=== Stochastic ==="
input int      InpStochK        = 14;         // Stochastic %K Period
input int      InpStochD        = 3;          // Stochastic %D Period
input int      InpStochSlowing  = 3;          // Stochastic Slowing
input double   InpStochOB       = 80.0;       // Overbought Level
input int      InpStochOBLook   = 10;         // Bars to check recent OB cross
input double   InpStochMidLine  = 50.0;       // Skip if %K below this at entry

input group "=== Resistance Levels ==="
input bool     InpUseResistance = true;       // Require resistance confluence
input int      InpNearPoints    = 100;        // "Near" distance (points)
input int      InpLevelDays     = 3;          // Days for high/low range

input group "=== VWAP ==="
input bool     InpUseVWAP       = true;       // Use session VWAP as level
input int      InpVWAP_NearPts  = 80;         // VWAP proximity (points)

input group "=== Risk Management ==="
input double   InpRiskPct       = 0.50;       // Risk per trade (% of balance)
input double   InpMaxLot        = 1.0;        // Max lot per trade
input int      InpMaxPerDay     = 4;          // Max trades per day
input double   InpDailyDD       = 4.0;        // Daily DD Limit (%)
input int      InpMinSLPoints   = 60;         // Min SL distance (points)
input int      InpMaxSLPoints   = 500;        // Max SL distance (points)

input group "=== Session Filter ==="
input bool     InpSessionFilter = false;      // Enable session time filter
input int      InpSessionStart  = 8;          // Session start hour (server)
input int      InpSessionEnd    = 20;         // Session end hour (server)
input string   InpKillZoneHours = "";         // Kill zone hours CSV (e.g. "6,7,12,13,18") - overrides session range

input group "=== Daily Bias Filter ==="
input bool     InpDailyBias     = false;      // Enable D1 VixFix bias filter
input double   InpDailyWVFMax   = 0.5;        // Max D1 WVF for short bias (lower=nearer top)

//+------------------------------------------------------------------+
//| Globals                                                           |
//+------------------------------------------------------------------+
int      g_hStoch = INVALID_HANDLE;
datetime g_lastBar = 0;
int      g_tradesToday = 0;
int      g_lastTradeDay = -1;
double   g_dayStartBalance = 0;

//+------------------------------------------------------------------+
//| Expert initialization                                             |
//+------------------------------------------------------------------+
int OnInit()
{
   g_hStoch = iStochastic(_Symbol, PERIOD_CURRENT,
                           InpStochK, InpStochD, InpStochSlowing,
                           MODE_SMA, STO_LOWHIGH);
   if(g_hStoch == INVALID_HANDLE)
   {
      Print("[VFS] FATAL: Stochastic init failed");
      return INIT_FAILED;
   }

   g_dayStartBalance = AccountInfoDouble(ACCOUNT_BALANCE);

   PrintFormat("[VFS] EA_VixFixScalp v1.00 | Symbol=%s | TF=%s | Magic=%d",
               _Symbol, EnumToString(_Period), InpMagic);
   PrintFormat("[VFS] WVF=%d | BB=%d/%.1f | ThreshLB=%d | SignalLB=%d",
               InpWVF_Period, InpBB_Period, InpBB_Mult,
               InpThreshLookback, InpSignalLookback);
   PrintFormat("[VFS] Stoch=%d/%d/%d | OB=%.0f | Risk=%.2f%% | MaxDay=%d",
               InpStochK, InpStochD, InpStochSlowing,
               InpStochOB, InpRiskPct, InpMaxPerDay);

   return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
//| Expert deinitialization                                           |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   if(g_hStoch != INVALID_HANDLE)
      IndicatorRelease(g_hStoch);
}

//+------------------------------------------------------------------+
//| Calc Williams Vix Fix for a given shift                           |
//| WVF = (Highest(Close, pd) - Low[shift]) / Highest(Close, pd) *100|
//+------------------------------------------------------------------+
double CalcWVF(int shift)
{
   double hc = 0;
   for(int i = shift; i < shift + InpWVF_Period; i++)
   {
      double c = iClose(_Symbol, PERIOD_CURRENT, i);
      if(c > hc) hc = c;
   }
   if(hc <= 0) return 0;
   double low = iLow(_Symbol, PERIOD_CURRENT, shift);
   return (hc - low) / hc * 100.0;
}

//+------------------------------------------------------------------+
//| Build WVF array for bars [1..count]                               |
//| wvf[0] = bar[1], wvf[1] = bar[2], etc.                           |
//+------------------------------------------------------------------+
bool BuildWVF(double &wvf[], int count)
{
   ArrayResize(wvf, count);
   for(int i = 0; i < count; i++)
      wvf[i] = CalcWVF(i + 1);  // shift = i+1 (bar[1] onwards)
   return true;
}

//+------------------------------------------------------------------+
//| Calc adaptive threshold: min peak among "green bars"              |
//| Green bar = WVF >= BB_Upper                                       |
//+------------------------------------------------------------------+
double CalcAdaptiveThreshold(double &wvf[], int count)
{
   if(count < InpBB_Period) return -1;

   double minPeak = DBL_MAX;
   bool   foundGreen = false;

   for(int i = 0; i < count - InpBB_Period; i++)
   {
      // Calc BB on WVF centered at position i
      double sum = 0, sum2 = 0;
      for(int j = i; j < i + InpBB_Period; j++)
      {
         sum  += wvf[j];
         sum2 += wvf[j] * wvf[j];
      }
      double mean = sum / InpBB_Period;
      double var  = sum2 / InpBB_Period - mean * mean;
      double sd   = (var > 0) ? MathSqrt(var) : 0;
      double bbUp = mean + InpBB_Mult * sd;

      // Is this bar "green"? (WVF >= BB_Upper)
      if(wvf[i] >= bbUp)
      {
         foundGreen = true;
         if(wvf[i] < minPeak)
            minPeak = wvf[i];
      }
   }

   if(!foundGreen) return -1;
   return minPeak;
}

//+------------------------------------------------------------------+
//| Check Stochastic condition (direction-aware):                     |
//| dir=0 (Sell): %K was >OB, crossed below %D, still >midline       |
//| dir=1 (Buy):  %K was <OS, crossed above %D, still <midline_inv   |
//+------------------------------------------------------------------+
bool CheckStochastic(int dir)
{
   double K[], D[];
   ArraySetAsSeries(K, true);
   ArraySetAsSeries(D, true);

   int need = InpStochOBLook + 2;
   if(CopyBuffer(g_hStoch, 0, 1, need, K) < need) return false;
   if(CopyBuffer(g_hStoch, 1, 1, need, D) < need) return false;

   if(dir == 0) // SELL
   {
      if(K[0] >= D[0]) return false;           // %K below %D (bearish)
      if(K[0] < InpStochMidLine) return false;  // not already oversold
      bool wasOB = false;
      for(int i = 1; i < need; i++)
         if(K[i] >= InpStochOB) { wasOB = true; break; }
      return wasOB;
   }
   else // BUY
   {
      double osLevel = 100.0 - InpStochOB;      // e.g. 20
      double midInv  = 100.0 - InpStochMidLine;  // e.g. 50
      if(K[0] <= D[0]) return false;             // %K above %D (bullish)
      if(K[0] > midInv) return false;            // not already overbought
      bool wasOS = false;
      for(int i = 1; i < need; i++)
         if(K[i] <= osLevel) { wasOS = true; break; }
      return wasOS;
   }
}

//+------------------------------------------------------------------+
//| Get resistance levels: N-day high, prev-day high                  |
//+------------------------------------------------------------------+
bool GetResistanceLevels(double &levels[], int &count)
{
   count = 0;
   ArrayResize(levels, 4);

   MqlDateTime dt;
   datetime now = iTime(_Symbol, PERIOD_CURRENT, 1);
   TimeToStruct(now, dt);

   // Find start of today (server time)
   dt.hour = 0; dt.min = 0; dt.sec = 0;
   datetime todayStart = StructToTime(dt);

   // Previous day high (yesterday's RTH)
   datetime yesterdayStart = todayStart - 86400;
   int barYestStart = iBarShift(_Symbol, PERIOD_CURRENT, yesterdayStart, false);
   int barTodayStart = iBarShift(_Symbol, PERIOD_CURRENT, todayStart, false);

   if(barYestStart > 0 && barTodayStart > 0 && barYestStart > barTodayStart)
   {
      double prevDayHigh = 0;
      for(int i = barTodayStart; i <= barYestStart; i++)
      {
         double h = iHigh(_Symbol, PERIOD_CURRENT, i);
         if(h > prevDayHigh) prevDayHigh = h;
      }
      if(prevDayHigh > 0)
         levels[count++] = prevDayHigh;
   }

   // N-day high
   datetime nDayStart = todayStart - InpLevelDays * 86400;
   int barNDay = iBarShift(_Symbol, PERIOD_CURRENT, nDayStart, false);
   if(barNDay > 0)
   {
      double nDayHigh = 0;
      for(int i = 1; i <= barNDay; i++)
      {
         double h = iHigh(_Symbol, PERIOD_CURRENT, i);
         if(h > nDayHigh) nDayHigh = h;
      }
      if(nDayHigh > 0)
         levels[count++] = nDayHigh;
   }

   return count > 0;
}

//+------------------------------------------------------------------+
//| Calculate session VWAP (anchored to day start)                    |
//+------------------------------------------------------------------+
double CalcSessionVWAP()
{
   MqlDateTime dt;
   datetime barTime = iTime(_Symbol, PERIOD_CURRENT, 1);
   TimeToStruct(barTime, dt);
   dt.hour = 0; dt.min = 0; dt.sec = 0;
   datetime dayStart = StructToTime(dt);

   int barStart = iBarShift(_Symbol, PERIOD_CURRENT, dayStart, false);
   if(barStart <= 1) return 0;

   double cumPV = 0, cumVol = 0;
   for(int i = barStart; i >= 1; i--)
   {
      double tp  = (iHigh(_Symbol, PERIOD_CURRENT, i)
                   + iLow(_Symbol, PERIOD_CURRENT, i)
                   + iClose(_Symbol, PERIOD_CURRENT, i)) / 3.0;
      double vol = (double)iVolume(_Symbol, PERIOD_CURRENT, i);
      if(vol <= 0) vol = 1;
      cumPV  += tp * vol;
      cumVol += vol;
   }

   if(cumVol <= 0) return 0;
   return cumPV / cumVol;
}

//+------------------------------------------------------------------+
//| Check if price is near any resistance level                       |
//+------------------------------------------------------------------+
bool IsNearResistance(double price, string &resType)
{
   double pt = _Point;
   double nearDist = InpNearPoints * pt;

   // Check structural resistance levels
   if(InpUseResistance)
   {
      double levels[];
      int cnt = 0;
      if(GetResistanceLevels(levels, cnt))
      {
         for(int i = 0; i < cnt; i++)
         {
            if(levels[i] > 0 && MathAbs(price - levels[i]) <= nearDist)
            {
               resType = (i == 0) ? "PrevDayH" : "NDayH";
               return true;
            }
         }
      }
   }

   // Check VWAP
   if(InpUseVWAP)
   {
      double vwap = CalcSessionVWAP();
      if(vwap > 0 && MathAbs(price - vwap) <= InpVWAP_NearPts * pt)
      {
         resType = "VWAP";
         return true;
      }
   }

   return false;
}

//+------------------------------------------------------------------+
//| Check if price is near any support level (for BUY)                |
//+------------------------------------------------------------------+
bool IsNearSupport(double price, string &resType)
{
   double pt = _Point;
   double nearDist = InpNearPoints * pt;

   if(InpUseResistance)
   {
      double levels[];
      int cnt = 0;
      if(GetResistanceLevels(levels, cnt))
      {
         // Get support levels: use same function but look for lows
         MqlDateTime dts;
         datetime now = iTime(_Symbol, PERIOD_CURRENT, 1);
         TimeToStruct(now, dts);
         dts.hour = 0; dts.min = 0; dts.sec = 0;
         datetime todayStart = StructToTime(dts);

         // Previous day low
         datetime yesterdayStart = todayStart - 86400;
         int barYS = iBarShift(_Symbol, PERIOD_CURRENT, yesterdayStart, false);
         int barTS = iBarShift(_Symbol, PERIOD_CURRENT, todayStart, false);
         if(barYS > 0 && barTS > 0 && barYS > barTS)
         {
            double prevDayLow = DBL_MAX;
            for(int i = barTS; i <= barYS; i++)
            {
               double lo = iLow(_Symbol, PERIOD_CURRENT, i);
               if(lo < prevDayLow) prevDayLow = lo;
            }
            if(prevDayLow < DBL_MAX && MathAbs(price - prevDayLow) <= nearDist)
            {
               resType = "PrevDayL";
               return true;
            }
         }

         // N-day low
         datetime nDayStart = todayStart - InpLevelDays * 86400;
         int barND = iBarShift(_Symbol, PERIOD_CURRENT, nDayStart, false);
         if(barND > 0)
         {
            double nDayLow = DBL_MAX;
            for(int i = 1; i <= barND; i++)
            {
               double lo = iLow(_Symbol, PERIOD_CURRENT, i);
               if(lo < nDayLow) nDayLow = lo;
            }
            if(nDayLow < DBL_MAX && MathAbs(price - nDayLow) <= nearDist)
            {
               resType = "NDayL";
               return true;
            }
         }
      }
   }

   // VWAP (same for both directions - mean reversion)
   if(InpUseVWAP)
   {
      double vwap = CalcSessionVWAP();
      if(vwap > 0 && MathAbs(price - vwap) <= InpVWAP_NearPts * pt)
      {
         resType = "VWAP";
         return true;
      }
   }

   return false;
}

//+------------------------------------------------------------------+
//| Count open positions with our magic                               |
//+------------------------------------------------------------------+
int CountPositions()
{
   int cnt = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket > 0 && PositionGetInteger(POSITION_MAGIC) == (long)InpMagic
         && PositionGetString(POSITION_SYMBOL) == _Symbol)
         cnt++;
   }
   return cnt;
}

//+------------------------------------------------------------------+
//| Check daily drawdown                                              |
//+------------------------------------------------------------------+
bool IsDailyDDExceeded()
{
   if(g_dayStartBalance <= 0) return false;
   double equity = AccountInfoDouble(ACCOUNT_EQUITY);
   double dd = (g_dayStartBalance - equity) / g_dayStartBalance * 100.0;
   return dd >= InpDailyDD;
}

//+------------------------------------------------------------------+
//| Calculate lot size based on risk and SL distance                  |
//+------------------------------------------------------------------+
double CalcLot(double slDist)
{
   if(slDist <= 0) return 0;

   double balance   = AccountInfoDouble(ACCOUNT_BALANCE);
   double riskMoney = balance * InpRiskPct / 100.0;
   double tickValue = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
   double tickSize  = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   if(tickValue <= 0 || tickSize <= 0) return 0;

   double lot = riskMoney / (slDist / tickSize * tickValue);

   double minLot  = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double maxLot  = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   double lotStep = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);

   lot = MathMin(lot, InpMaxLot);
   lot = MathMin(lot, maxLot);
   lot = MathMax(lot, minLot);
   lot = MathFloor(lot / lotStep) * lotStep;

   return lot;
}

//+------------------------------------------------------------------+
//| Expert tick function                                              |
//+------------------------------------------------------------------+
void OnTick()
{
   if(InpKillSwitch) return;

   // New bar check
   datetime barTime = iTime(_Symbol, PERIOD_CURRENT, 0);
   if(barTime == g_lastBar) return;
   g_lastBar = barTime;

   // Day reset
   MqlDateTime dt;
   TimeToStruct(barTime, dt);
   if(dt.day_of_year != g_lastTradeDay)
   {
      g_lastTradeDay = dt.day_of_year;
      g_tradesToday = 0;
      g_dayStartBalance = AccountInfoDouble(ACCOUNT_BALANCE);
   }

   // Pre-flight checks
   if(g_tradesToday >= InpMaxPerDay) return;
   if(CountPositions() > 0) return;  // One at a time
   if(IsDailyDDExceeded()) return;

   // Session filter
   if(StringLen(InpKillZoneHours) > 0)
   {
      // Kill zone mode: only trade at specific hours
      bool hourAllowed = false;
      string parts[];
      int n = StringSplit(InpKillZoneHours, ',', parts);
      for(int i = 0; i < n; i++)
      {
         string p = parts[i];
         StringTrimLeft(p);
         StringTrimRight(p);
         if((int)StringToInteger(p) == dt.hour)
         { hourAllowed = true; break; }
      }
      if(!hourAllowed) return;
   }
   else if(InpSessionFilter)
   {
      if(dt.hour < InpSessionStart || dt.hour >= InpSessionEnd)
         return;
   }

   // Daily bias filter: D1 WVF must be low (price near top on daily)
   if(InpDailyBias)
   {
      // Calc WVF on D1 bar[1]
      double d1hc = 0;
      int d1bars = Bars(_Symbol, PERIOD_D1);
      if(d1bars < InpWVF_Period + 2) return;
      for(int i = 1; i <= InpWVF_Period; i++)
      {
         double c = iClose(_Symbol, PERIOD_D1, i);
         if(c > d1hc) d1hc = c;
      }
      if(d1hc <= 0) return;
      double d1low = iLow(_Symbol, PERIOD_D1, 1);
      double d1wvf = (d1hc - d1low) / d1hc * 100.0;
      // For shorts: low D1 WVF = price near daily high = bearish bias
      // For buys: high D1 WVF = price far from daily high = bullish bias
      if(InpDirection == 0 && d1wvf > InpDailyWVFMax) return;       // sell: need low WVF
      if(InpDirection == 1 && d1wvf < (3.0 - InpDailyWVFMax)) return; // buy: need high WVF
      // Both: skip filter (trade both sides)
   }

   //--- Build WVF array
   int wvfCount = InpThreshLookback + InpBB_Period + 10;
   int barsAvail = Bars(_Symbol, PERIOD_CURRENT);
   if(barsAvail < wvfCount + InpWVF_Period + 10) return;

   double wvf[];
   if(!BuildWVF(wvf, wvfCount)) return;

   //--- Calc adaptive threshold
   double threshold = CalcAdaptiveThreshold(wvf, wvfCount);
   if(threshold < 0) return;  // No green bars found

   //--- Try each enabled direction
   //    dir=0: SELL (original logic: WVF cross down, first rising bar)
   //    dir=1: BUY  (inverted:  WVF cross up into green, first falling bar)
   for(int dir = 0; dir <= 1; dir++)
   {
      // Skip disabled directions
      if(InpDirection == 0 && dir == 1) continue;  // sell only
      if(InpDirection == 1 && dir == 0) continue;  // buy only
      // InpDirection == 2: both

      //--- Find fresh cross (direction-specific)
      int crossIdx = -1;
      for(int i = 0; i < InpSignalLookback - 1; i++)
      {
         if(dir == 0) // SELL: WVF crosses from above to below threshold
         {
            if(wvf[i] < threshold && wvf[i + 1] >= threshold)
            { crossIdx = i; break; }
         }
         else // BUY: WVF crosses from below to above threshold (green bar starts)
         {
            if(wvf[i] >= threshold && wvf[i + 1] < threshold)
            { crossIdx = i; break; }
         }
      }
      if(crossIdx < 0) continue;

      //--- Check: first rising/falling WVF bar after cross
      if(crossIdx == 0) continue;  // Cross just happened, wait one more bar

      bool isSignal = false;
      if(dir == 0) // SELL: first rising WVF bar (price pulling back down)
      {
         if(wvf[0] > wvf[1])
         {
            bool priorRise = false;
            for(int i = 1; i < crossIdx; i++)
               if(wvf[i] > wvf[i + 1]) { priorRise = true; break; }
            if(!priorRise) isSignal = true;
         }
      }
      else // BUY: first falling WVF bar (price recovering from bottom)
      {
         if(wvf[0] < wvf[1])
         {
            bool priorFall = false;
            for(int i = 1; i < crossIdx; i++)
               if(wvf[i] < wvf[i + 1]) { priorFall = true; break; }
            if(!priorFall) isSignal = true;
         }
      }
      if(!isSignal) continue;

      //--- Check bars from cross to now stay on correct side of threshold
      for(int i = 0; i < crossIdx; i++)
      {
         if(dir == 0 && wvf[i] >= threshold) { isSignal = false; break; }
         if(dir == 1 && wvf[i] <  threshold) { isSignal = false; break; }
      }
      if(!isSignal) continue;

      //--- Stochastic confirmation (direction-aware)
      if(!CheckStochastic(dir)) continue;

      //--- Price and level check
      double closeBar1 = iClose(_Symbol, PERIOD_CURRENT, 1);
      double highBar1  = iHigh(_Symbol, PERIOD_CURRENT, 1);
      double lowBar1   = iLow(_Symbol, PERIOD_CURRENT, 1);

      string resType = "";
      if(InpUseResistance || InpUseVWAP)
      {
         if(dir == 0 && !IsNearResistance(closeBar1, resType)) continue;
         if(dir == 1 && !IsNearSupport(closeBar1, resType))    continue;
      }

      //--- Calculate SL
      double sl = 0, slDist = 0;
      double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
      double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
      double slBuffer = 2 * _Point;

      if(dir == 0) // SELL: SL above swing high
      {
         double swingHigh = 0;
         for(int i = 1; i <= crossIdx + 2; i++)
         {
            double h = iHigh(_Symbol, PERIOD_CURRENT, i);
            if(h > swingHigh) swingHigh = h;
         }
         // False signal filter
         if(highBar1 >= swingHigh) continue;
         sl = swingHigh + slBuffer;
         slDist = sl - bid;
         if(slDist < InpMinSLPoints * _Point)
         { sl = bid + InpMinSLPoints * _Point; slDist = sl - bid; }
      }
      else // BUY: SL below swing low
      {
         double swingLow = DBL_MAX;
         for(int i = 1; i <= crossIdx + 2; i++)
         {
            double lo = iLow(_Symbol, PERIOD_CURRENT, i);
            if(lo < swingLow) swingLow = lo;
         }
         // False signal filter
         if(lowBar1 <= swingLow) continue;
         sl = swingLow - slBuffer;
         slDist = ask - sl;
         if(slDist < InpMinSLPoints * _Point)
         { sl = ask - InpMinSLPoints * _Point; slDist = ask - sl; }
      }

      if(slDist > InpMaxSLPoints * _Point) continue;
      if(slDist <= 0) continue;

      //--- TP at 1:1 RR
      double tp = (dir == 0) ? (bid - slDist) : (ask + slDist);

      //--- Check stop level
      int stopLevel = (int)SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL);
      double minDist = stopLevel * _Point;
      double entryPrice = (dir == 0) ? bid : ask;
      if(slDist < minDist || MathAbs(entryPrice - tp) < minDist) continue;

      //--- Lot sizing
      double lot = CalcLot(slDist);
      if(lot <= 0) continue;

      //--- Normalize prices
      int digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
      sl = NormalizeDouble(sl, digits);
      tp = NormalizeDouble(tp, digits);

      //--- Execute order
      MqlTradeRequest req = {};
      MqlTradeResult  res = {};

      req.action    = TRADE_ACTION_DEAL;
      req.symbol    = _Symbol;
      req.volume    = lot;
      req.type      = (dir == 0) ? ORDER_TYPE_SELL : ORDER_TYPE_BUY;
      req.price     = entryPrice;
      req.sl        = sl;
      req.tp        = tp;
      req.deviation = (ulong)InpDeviation;
      req.magic     = InpMagic;
      req.comment   = StringFormat("VFS|%s|%s|WVF=%.2f",
                                   (dir == 0) ? "S" : "B", resType, wvf[0]);
      req.type_filling = ORDER_FILLING_FOK;

      if(!OrderSend(req, res))
      {
         req.type_filling = ORDER_FILLING_IOC;
         if(!OrderSend(req, res))
         {
            PrintFormat("[VFS] OrderSend FAIL: err=%d retcode=%d",
                        GetLastError(), res.retcode);
            continue;
         }
      }

      if(res.retcode == TRADE_RETCODE_DONE || res.retcode == TRADE_RETCODE_PLACED)
      {
         g_tradesToday++;
         PrintFormat("[VFS] %s %.2f @ %.5f | SL=%.5f TP=%.5f | %s | WVF=%.2f/Thr=%.2f",
                     (dir == 0) ? "SELL" : "BUY",
                     lot, res.price, sl, tp, resType, wvf[0], threshold);
         break;  // One trade per bar
      }
      else
      {
         PrintFormat("[VFS] Order retcode=%d deal=%d", res.retcode, res.deal);
      }
   } // end direction loop
}

//+------------------------------------------------------------------+
//| Tester event for optimization stats                               |
//+------------------------------------------------------------------+
double OnTester()
{
   double pf = TesterStatistics(STAT_PROFIT_FACTOR);
   double trades = TesterStatistics(STAT_TRADES);
   if(trades < 30) return 0;
   return pf * MathSqrt(trades);
}
//+------------------------------------------------------------------+
