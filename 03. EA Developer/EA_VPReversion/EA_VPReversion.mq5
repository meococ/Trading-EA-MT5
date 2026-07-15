//+------------------------------------------------------------------+
//| EA_VPReversion.mq5 — Volume Profile POC Mean Reversion           |
//| Symbol: Any (default XAUUSD+)  |  Period: M15  |  Style: MR      |
//|                                                                   |
//| EDGE HYPOTHESIS:                                                  |
//| Previous session's Point of Control (POC = price with highest     |
//| tick volume) acts as fair-value magnet. When price deviates       |
//| beyond threshold, fade back toward POC.                           |
//|                                                                   |
//| STRUCTURAL REASON:                                                |
//| - POC = price where most volume transacted = institutional fair   |
//|   value anchor. Lo et al. (2004): VWAP reversion significant.    |
//| - Large order flow anchors around VWAP/POC for execution.         |
//| - Deviation from POC = short-term dislocation; mean reversion     |
//|   occurs as institutions defend value area.                       |
//|                                                                   |
//| DESIGN:                                                           |
//| - Calc previous session volume profile: POC + Value Area (VA)     |
//| - Entry: price beyond VA + stochastic extreme + mean reversion    |
//| - SL: ATR-based beyond deviation extreme                         |
//| - TP: POC (fair value target)                                     |
//| - Session: London-NY overlap only (best volume quality)           |
//|                                                                   |
//| SIGNALS ON BAR[1] ONLY — no repaint, no lookahead.                |
//| Max | 2026-04-12 | v1.0                                          |
//+------------------------------------------------------------------+
#property copyright "Max — EA_VPReversion v1.0"
#property link      ""
#property version   "1.00"
#property strict

//+------------------------------------------------------------------+
//| Input Parameters                                                  |
//+------------------------------------------------------------------+
input group "=== General ==="
input ulong    InpMagic         = 207001;     // Magic Number
input int      InpDeviation     = 30;         // Max Slippage (pts)
input bool     InpKillSwitch    = false;      // Kill Switch

input group "=== Volume Profile ==="
input int      InpProfileBars   = 96;         // Bars for profile (96 = 24h on M15)
input int      InpBuckets       = 50;         // Price buckets for volume distribution
input double   InpVA_Pct        = 70.0;       // Value Area percentage (70% standard)

input group "=== Entry ==="
input double   InpDevATR_Mult   = 1.5;        // Min deviation from POC (ATR multiples)
input int      InpATR_Period    = 14;         // ATR period
input int      InpDirection     = 2;          // 0=Sell only, 1=Buy only, 2=Both
input bool     InpUseStoch      = true;       // Require stochastic extreme
input int      InpStochK        = 14;         // Stochastic %K
input int      InpStochD        = 3;          // Stochastic %D
input int      InpStochSlowing  = 3;          // Stochastic Slowing
input double   InpStochOB       = 80.0;       // Overbought (sell trigger)
input double   InpStochOS       = 20.0;       // Oversold (buy trigger)

input group "=== Risk Management ==="
input double   InpRiskPct       = 0.50;       // Risk per trade (% balance)
input double   InpMaxLot        = 1.0;        // Max lot per trade
input int      InpMaxPerDay     = 4;          // Max trades per day
input double   InpDailyDD       = 4.0;        // Daily DD Limit (%)
input double   InpSL_ATR_Mult   = 2.0;        // SL distance (ATR multiples)
input int      InpMinSLPoints   = 50;         // Min SL distance (points)
input int      InpMaxSLPoints   = 500;        // Max SL distance (points)

input group "=== Session Filter ==="
input bool     InpSessionFilter = true;       // Enable session filter
input int      InpSessionStart  = 8;          // Session start hour (server)
input int      InpSessionEnd    = 20;         // Session end hour (server)

//+------------------------------------------------------------------+
//| Globals                                                           |
//+------------------------------------------------------------------+
int      g_hStoch = INVALID_HANDLE;
int      g_hATR   = INVALID_HANDLE;
datetime g_lastBar = 0;
int      g_tradesToday = 0;
int      g_lastTradeDay = -1;
double   g_dayStartBalance = 0;

// Cached volume profile
double   g_poc = 0;         // Point of Control price
double   g_vaHigh = 0;      // Value Area High
double   g_vaLow = 0;       // Value Area Low
datetime g_profileCalcTime = 0;  // When profile was last calculated

//+------------------------------------------------------------------+
//| Expert initialization                                             |
//+------------------------------------------------------------------+
int OnInit()
{
   g_hStoch = iStochastic(_Symbol, PERIOD_CURRENT,
                           InpStochK, InpStochD, InpStochSlowing,
                           MODE_SMA, STO_LOWHIGH);
   g_hATR = iATR(_Symbol, PERIOD_CURRENT, InpATR_Period);

   if(g_hStoch == INVALID_HANDLE || g_hATR == INVALID_HANDLE)
   {
      Print("[VPR] FATAL: Indicator init failed");
      return INIT_FAILED;
   }

   g_dayStartBalance = AccountInfoDouble(ACCOUNT_BALANCE);

   PrintFormat("[VPR] EA_VPReversion v1.00 | Symbol=%s | TF=%s | Magic=%d",
               _Symbol, EnumToString(_Period), InpMagic);
   PrintFormat("[VPR] Profile=%d bars | Buckets=%d | VA=%.0f%% | DevATR=%.1f",
               InpProfileBars, InpBuckets, InpVA_Pct, InpDevATR_Mult);

   return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
//| Expert deinitialization                                           |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   if(g_hStoch != INVALID_HANDLE) IndicatorRelease(g_hStoch);
   if(g_hATR   != INVALID_HANDLE) IndicatorRelease(g_hATR);
}

//+------------------------------------------------------------------+
//| Calculate Volume Profile: POC, VA High, VA Low                    |
//| Uses tick volume as proxy for real volume                         |
//+------------------------------------------------------------------+
bool CalcVolumeProfile()
{
   // Recalculate once per session (every profileBars interval)
   datetime barTime = iTime(_Symbol, PERIOD_CURRENT, 1);
   if(g_profileCalcTime > 0 && (barTime - g_profileCalcTime) < InpProfileBars * PeriodSeconds())
      return (g_poc > 0);

   int shift_start = 1;                          // Start from bar[1]
   int shift_end   = shift_start + InpProfileBars - 1;

   // Safety
   int barsAvail = Bars(_Symbol, PERIOD_CURRENT);
   if(barsAvail < shift_end + 1) return false;

   // Find price range
   double rangeHigh = 0, rangeLow = DBL_MAX;
   for(int i = shift_start; i <= shift_end; i++)
   {
      double h = iHigh(_Symbol, PERIOD_CURRENT, i);
      double l = iLow(_Symbol, PERIOD_CURRENT, i);
      if(h > rangeHigh) rangeHigh = h;
      if(l < rangeLow)  rangeLow = l;
   }

   if(rangeHigh <= rangeLow) return false;

   double bucketSize = (rangeHigh - rangeLow) / InpBuckets;
   if(bucketSize <= 0) return false;

   // Build volume distribution
   double volProfile[];
   ArrayResize(volProfile, InpBuckets);
   ArrayInitialize(volProfile, 0);

   double totalVol = 0;
   for(int i = shift_start; i <= shift_end; i++)
   {
      double h   = iHigh(_Symbol, PERIOD_CURRENT, i);
      double l   = iLow(_Symbol, PERIOD_CURRENT, i);
      long   vol = iVolume(_Symbol, PERIOD_CURRENT, i);
      if(vol <= 0) vol = 1;

      // Distribute volume across buckets this bar touches
      int bucketLow  = (int)MathFloor((l - rangeLow) / bucketSize);
      int bucketHigh = (int)MathFloor((h - rangeLow) / bucketSize);
      bucketLow  = MathMax(0, MathMin(InpBuckets - 1, bucketLow));
      bucketHigh = MathMax(0, MathMin(InpBuckets - 1, bucketHigh));

      int span = bucketHigh - bucketLow + 1;
      double perBucket = (double)vol / span;

      for(int b = bucketLow; b <= bucketHigh; b++)
      {
         volProfile[b] += perBucket;
         totalVol += perBucket;
      }
   }

   if(totalVol <= 0) return false;

   // Find POC (bucket with highest volume)
   int pocBucket = 0;
   double maxVol = 0;
   for(int b = 0; b < InpBuckets; b++)
   {
      if(volProfile[b] > maxVol)
      {
         maxVol = volProfile[b];
         pocBucket = b;
      }
   }

   g_poc = rangeLow + (pocBucket + 0.5) * bucketSize;

   // Calculate Value Area (expand from POC until VA% of volume captured)
   double vaTarget = totalVol * InpVA_Pct / 100.0;
   double vaCumVol = volProfile[pocBucket];
   int vaLowBkt = pocBucket, vaHighBkt = pocBucket;

   while(vaCumVol < vaTarget && (vaLowBkt > 0 || vaHighBkt < InpBuckets - 1))
   {
      double addLow = (vaLowBkt > 0) ? volProfile[vaLowBkt - 1] : 0;
      double addHigh = (vaHighBkt < InpBuckets - 1) ? volProfile[vaHighBkt + 1] : 0;

      if(addLow >= addHigh && vaLowBkt > 0)
      {
         vaLowBkt--;
         vaCumVol += volProfile[vaLowBkt];
      }
      else if(vaHighBkt < InpBuckets - 1)
      {
         vaHighBkt++;
         vaCumVol += volProfile[vaHighBkt];
      }
      else if(vaLowBkt > 0)
      {
         vaLowBkt--;
         vaCumVol += volProfile[vaLowBkt];
      }
      else break;
   }

   g_vaLow  = rangeLow + vaLowBkt * bucketSize;
   g_vaHigh = rangeLow + (vaHighBkt + 1) * bucketSize;

   g_profileCalcTime = barTime;

   return true;
}

//+------------------------------------------------------------------+
//| Count positions                                                   |
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
//| Calculate lot size                                                |
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

   // Pre-flight
   if(g_tradesToday >= InpMaxPerDay) return;
   if(CountPositions() > 0) return;
   if(IsDailyDDExceeded()) return;

   // Session filter
   if(InpSessionFilter)
   {
      if(dt.hour < InpSessionStart || dt.hour >= InpSessionEnd)
         return;
   }

   //--- Calculate volume profile
   if(!CalcVolumeProfile()) return;
   if(g_poc <= 0 || g_vaHigh <= g_vaLow) return;

   //--- Get ATR
   double atr[];
   ArraySetAsSeries(atr, true);
   if(CopyBuffer(g_hATR, 0, 1, 1, atr) < 1) return;
   if(atr[0] <= 0) return;

   double deviationThresh = InpDevATR_Mult * atr[0];

   //--- Bar[1] price
   double close1 = iClose(_Symbol, PERIOD_CURRENT, 1);
   double high1  = iHigh(_Symbol, PERIOD_CURRENT, 1);
   double low1   = iLow(_Symbol, PERIOD_CURRENT, 1);

   //--- Check deviation from POC
   double devFromPOC = close1 - g_poc;

   int signal = 0;  // 0=none, 1=buy, -1=sell

   // Price ABOVE POC + threshold → SELL back to POC
   if(devFromPOC > deviationThresh && close1 > g_vaHigh)
   {
      if(InpDirection == 0 || InpDirection == 2)
         signal = -1;
   }
   // Price BELOW POC - threshold → BUY back to POC
   else if(devFromPOC < -deviationThresh && close1 < g_vaLow)
   {
      if(InpDirection == 1 || InpDirection == 2)
         signal = 1;
   }

   if(signal == 0) return;

   //--- Stochastic confirmation
   if(InpUseStoch)
   {
      double K[], D[];
      ArraySetAsSeries(K, true);
      ArraySetAsSeries(D, true);
      if(CopyBuffer(g_hStoch, 0, 1, 3, K) < 3) return;
      if(CopyBuffer(g_hStoch, 1, 1, 3, D) < 3) return;

      if(signal == -1)
      {
         // Sell: want overbought condition
         if(K[0] < InpStochOB && K[1] < InpStochOB) return;
         // Prefer %K crossing below %D
         if(K[0] >= D[0]) return;
      }
      else
      {
         // Buy: want oversold condition
         if(K[0] > InpStochOS && K[1] > InpStochOS) return;
         // Prefer %K crossing above %D
         if(K[0] <= D[0]) return;
      }
   }

   //--- Calculate SL and TP
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double slDist = InpSL_ATR_Mult * atr[0];
   int digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);

   // Enforce min/max SL
   slDist = MathMax(slDist, InpMinSLPoints * _Point);
   if(slDist > InpMaxSLPoints * _Point) return;

   double entryPrice, sl, tp;

   if(signal == -1) // SELL
   {
      entryPrice = bid;
      sl = NormalizeDouble(entryPrice + slDist, digits);
      tp = NormalizeDouble(g_poc, digits);  // Target = POC
      // Ensure TP is below entry
      if(tp >= entryPrice) return;
   }
   else // BUY
   {
      entryPrice = ask;
      sl = NormalizeDouble(entryPrice - slDist, digits);
      tp = NormalizeDouble(g_poc, digits);  // Target = POC
      // Ensure TP is above entry
      if(tp <= entryPrice) return;
   }

   //--- Stop level check
   int stopLevel = (int)SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL);
   double minDist = stopLevel * _Point;
   if(signal == -1)
   {
      if((sl - bid) < minDist || (bid - tp) < minDist) return;
   }
   else
   {
      if((ask - sl) < minDist || (tp - ask) < minDist) return;
   }

   //--- Lot sizing
   double lot = CalcLot(slDist);
   if(lot <= 0) return;

   //--- Execute order
   MqlTradeRequest req = {};
   MqlTradeResult  res = {};

   req.action    = TRADE_ACTION_DEAL;
   req.symbol    = _Symbol;
   req.volume    = lot;
   req.type      = (signal == -1) ? ORDER_TYPE_SELL : ORDER_TYPE_BUY;
   req.price     = entryPrice;
   req.sl        = sl;
   req.tp        = tp;
   req.deviation = (ulong)InpDeviation;
   req.magic     = InpMagic;
   req.comment   = StringFormat("VPR|POC=%.2f|VA=%.2f-%.2f|Dev=%.1f",
                                g_poc, g_vaLow, g_vaHigh, devFromPOC / atr[0]);
   req.type_filling = ORDER_FILLING_FOK;

   if(!OrderSend(req, res))
   {
      req.type_filling = ORDER_FILLING_IOC;
      if(!OrderSend(req, res))
      {
         PrintFormat("[VPR] OrderSend FAIL: err=%d retcode=%d",
                     GetLastError(), res.retcode);
         return;
      }
   }

   if(res.retcode == TRADE_RETCODE_DONE || res.retcode == TRADE_RETCODE_PLACED)
   {
      g_tradesToday++;
      string dir = (signal == -1) ? "SELL" : "BUY";
      PrintFormat("[VPR] %s %.2f @ %.5f | SL=%.5f TP=%.5f(POC) | Dev=%.1fATR",
                  dir, lot, res.price, sl, tp, MathAbs(devFromPOC) / atr[0]);
   }
   else
   {
      PrintFormat("[VPR] Order retcode=%d", res.retcode);
   }
}

//+------------------------------------------------------------------+
//| Tester stat                                                       |
//+------------------------------------------------------------------+
double OnTester()
{
   double pf = TesterStatistics(STAT_PROFIT_FACTOR);
   double trades = TesterStatistics(STAT_TRADES);
   if(trades < 30) return 0;
   return pf * MathSqrt(trades);
}
//+------------------------------------------------------------------+
