//+------------------------------------------------------------------+
//| EA_CVDDivergence.mq5 — Proxy CVD Exhaustion Reversal             |
//| Symbol: XAUUSD+  |  Period: M15  |  Style: Mean Reversion         |
//|                                                                   |
//| EDGE HYPOTHESIS:                                                  |
//| Cumulative Volume Delta (CVD) measures net buying vs selling      |
//| pressure. When price makes new highs but CVD fails to confirm    |
//| (divergence), institutional selling is absorbing retail buying    |
//| → exhaustion → reversal imminent.                                |
//|                                                                   |
//| CVD PROXY (no L2 data needed):                                   |
//| delta[i] = (close - open) / (high - low) * tick_volume           |
//| This estimates directional conviction per bar using candle body   |
//| relative to range, weighted by activity (tick volume).            |
//|                                                                   |
//| Source: arxiv 2410.08744, Kyle 1985, Glosten-Milgrom 1985        |
//| Novelty: Type #70 — never tested in 599 prior strategies         |
//|                                                                   |
//| SIGNALS ON BAR[1] ONLY — no repaint, no lookahead.               |
//| Max | 2026-04-13 | v1.0                                          |
//+------------------------------------------------------------------+
#property copyright "Max — EA_CVDDivergence v1.0"
#property link      ""
#property version   "1.00"
#property strict

//+------------------------------------------------------------------+
//| Input Parameters                                                  |
//+------------------------------------------------------------------+
input group "=== General ==="
input ulong    InpMagic         = 208001;     // Magic Number
input int      InpDeviation     = 30;         // Max Slippage (pts)
input bool     InpKillSwitch    = false;      // Kill Switch

input group "=== CVD Divergence Settings ==="
input int      InpLookback      = 30;         // Divergence lookback (bars)
input int      InpSwingBars     = 5;          // Swing detection half-width
input double   InpDivThreshold  = 0.15;       // CVD divergence threshold (0.15 = CVD 15% below peak)

input group "=== Session Filter ==="
input int      InpStartHour     = 10;         // Trade start hour (server)
input int      InpEndHour       = 20;         // Trade end hour (server)
input int      InpExitHour      = 22;         // Time stop hour (server)

input group "=== Risk Management ==="
input double   InpRiskPct       = 0.50;       // Risk per trade (%)
input double   InpMaxLot        = 1.0;        // Max lot
input double   InpSL_ATR_Mult   = 1.5;        // SL = N x ATR(14) M15
input int      InpMinSLPoints   = 100;        // Min SL (points)
input int      InpMaxSLPoints   = 1000;       // Max SL (points)
input double   InpTP_Ratio      = 1.0;        // TP ratio (1.0 = 1:1 RR)
input int      InpMaxPerDay     = 2;          // Max trades per day
input double   InpDailyDD       = 4.0;        // Daily DD Limit (%)

input group "=== Day Filters ==="
input bool     InpSkipMon       = false;      // Skip Monday
input bool     InpSkipFri       = true;       // Skip Friday

//+------------------------------------------------------------------+
//| Globals                                                           |
//+------------------------------------------------------------------+
int      g_hATR = INVALID_HANDLE;
datetime g_lastBar = 0;
int      g_tradesToday = 0;
int      g_lastTradeDay = -1;
double   g_dayStartBalance = 0;

//+------------------------------------------------------------------+
//| Expert initialization                                             |
//+------------------------------------------------------------------+
int OnInit()
{
   g_hATR = iATR(_Symbol, PERIOD_CURRENT, 14);
   if(g_hATR == INVALID_HANDLE)
   {
      Print("[CVD] FATAL: ATR init failed");
      return INIT_FAILED;
   }

   g_dayStartBalance = AccountInfoDouble(ACCOUNT_BALANCE);

   PrintFormat("[CVD] EA_CVDDivergence v1.00 | %s %s | Magic=%d",
               _Symbol, EnumToString(_Period), InpMagic);
   PrintFormat("[CVD] Lookback=%d | SwingBars=%d | DivThresh=%.2f",
               InpLookback, InpSwingBars, InpDivThreshold);
   PrintFormat("[CVD] Session h%d-h%d | Exit h%d | SL=%.1f ATR | TP=%.1f:1",
               InpStartHour, InpEndHour, InpExitHour,
               InpSL_ATR_Mult, InpTP_Ratio);

   return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   if(g_hATR != INVALID_HANDLE) IndicatorRelease(g_hATR);
}

//+------------------------------------------------------------------+
//| Count our positions                                               |
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
//| Close all our positions                                           |
//+------------------------------------------------------------------+
void CloseAllPositions()
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket <= 0) continue;
      if(PositionGetInteger(POSITION_MAGIC) != (long)InpMagic) continue;
      if(PositionGetString(POSITION_SYMBOL) != _Symbol) continue;

      MqlTradeRequest req = {};
      MqlTradeResult  res = {};
      req.action    = TRADE_ACTION_DEAL;
      req.symbol    = _Symbol;
      req.volume    = PositionGetDouble(POSITION_VOLUME);
      req.deviation = (ulong)InpDeviation;
      req.magic     = InpMagic;
      req.position  = ticket;

      if(PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY)
      {
         req.type  = ORDER_TYPE_SELL;
         req.price = SymbolInfoDouble(_Symbol, SYMBOL_BID);
      }
      else
      {
         req.type  = ORDER_TYPE_BUY;
         req.price = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
      }
      req.type_filling = ORDER_FILLING_FOK;
      if(!OrderSend(req, res))
      {
         req.type_filling = ORDER_FILLING_IOC;
         OrderSend(req, res);
      }
   }
}

//+------------------------------------------------------------------+
//| Daily DD check                                                    |
//+------------------------------------------------------------------+
bool IsDailyDDExceeded()
{
   if(g_dayStartBalance <= 0) return false;
   double eq = AccountInfoDouble(ACCOUNT_EQUITY);
   return (g_dayStartBalance - eq) / g_dayStartBalance * 100.0 >= InpDailyDD;
}

//+------------------------------------------------------------------+
//| Lot sizing                                                        |
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
//| Calculate proxy CVD delta for one bar                             |
//| delta = (close - open) / (high - low) * tick_volume               |
//| Positive = net buying pressure, Negative = net selling            |
//+------------------------------------------------------------------+
double CalcBarDelta(int shift)
{
   double o = iOpen(_Symbol, PERIOD_CURRENT, shift);
   double h = iHigh(_Symbol, PERIOD_CURRENT, shift);
   double l = iLow(_Symbol, PERIOD_CURRENT, shift);
   double c = iClose(_Symbol, PERIOD_CURRENT, shift);
   long   v = iTickVolume(_Symbol, PERIOD_CURRENT, shift);

   double range = h - l;
   if(range < _Point) return 0;  // doji or no range

   double bodyRatio = (c - o) / range;  // [-1, +1]
   return bodyRatio * (double)v;
}

//+------------------------------------------------------------------+
//| Detect CVD Divergence                                             |
//| Returns: +1 = bullish divergence (sell exhaustion → buy)          |
//|          -1 = bearish divergence (buy exhaustion → sell)          |
//|           0 = no divergence                                       |
//+------------------------------------------------------------------+
int DetectDivergence()
{
   int total = InpLookback + InpSwingBars + 2;

   // Build CVD array over lookback
   double cvd[];
   ArrayResize(cvd, total);
   cvd[total - 1] = CalcBarDelta(total - 1);
   for(int i = total - 2; i >= 1; i--)
      cvd[i] = cvd[i + 1] + CalcBarDelta(i);

   // Find swing highs and lows in price within lookback
   // A swing high at bar[i] means high[i] > high[i-k] and high[i] > high[i+k] for k=1..SwingBars
   // We search bar[1+SwingBars] through bar[lookback-SwingBars] for swings

   int startBar = 1 + InpSwingBars;
   int endBar   = InpLookback;

   // Collect swing highs (for bearish divergence detection)
   int    swHighBars[];
   double swHighPrices[];
   double swHighCVD[];

   // Collect swing lows (for bullish divergence detection)
   int    swLowBars[];
   double swLowPrices[];
   double swLowCVD[];

   for(int i = startBar; i <= endBar; i++)
   {
      double hi = iHigh(_Symbol, PERIOD_CURRENT, i);
      double lo = iLow(_Symbol, PERIOD_CURRENT, i);

      // Check swing high
      bool isSwHigh = true;
      for(int k = 1; k <= InpSwingBars; k++)
      {
         if(iHigh(_Symbol, PERIOD_CURRENT, i - k) >= hi ||
            iHigh(_Symbol, PERIOD_CURRENT, i + k) >= hi)
         {
            isSwHigh = false;
            break;
         }
      }
      if(isSwHigh)
      {
         int sz = ArraySize(swHighBars);
         ArrayResize(swHighBars, sz + 1);
         ArrayResize(swHighPrices, sz + 1);
         ArrayResize(swHighCVD, sz + 1);
         swHighBars[sz]   = i;
         swHighPrices[sz] = hi;
         swHighCVD[sz]    = (i < total) ? cvd[i] : 0;
      }

      // Check swing low
      bool isSwLow = true;
      for(int k = 1; k <= InpSwingBars; k++)
      {
         if(iLow(_Symbol, PERIOD_CURRENT, i - k) <= lo ||
            iLow(_Symbol, PERIOD_CURRENT, i + k) <= lo)
         {
            isSwLow = false;
            break;
         }
      }
      if(isSwLow)
      {
         int sz = ArraySize(swLowBars);
         ArrayResize(swLowBars, sz + 1);
         ArrayResize(swLowPrices, sz + 1);
         ArrayResize(swLowCVD, sz + 1);
         swLowBars[sz]   = i;
         swLowPrices[sz] = lo;
         swLowCVD[sz]    = (i < total) ? cvd[i] : 0;
      }
   }

   // Bearish divergence: price swing high HIGHER but CVD at that swing LOWER
   // Compare most recent two swing highs (index 0 = most recent, 1 = older)
   if(ArraySize(swHighBars) >= 2)
   {
      // swHighBars[0] is closest to bar[1], swHighBars[1] is further back
      if(swHighPrices[0] > swHighPrices[1])  // price made higher high
      {
         if(swHighCVD[0] < swHighCVD[1])     // but CVD didn't confirm
         {
            // Check threshold: CVD drop must be significant
            double cvdDrop = (swHighCVD[1] - swHighCVD[0]) /
                             MathMax(MathAbs(swHighCVD[1]), 1.0);
            if(cvdDrop >= InpDivThreshold)
            {
               PrintFormat("[CVD] BEARISH DIV: Price %.2f>%.2f but CVD %.0f<%.0f (drop %.1f%%)",
                           swHighPrices[0], swHighPrices[1],
                           swHighCVD[0], swHighCVD[1], cvdDrop * 100);
               return -1;
            }
         }
      }
   }

   // Bullish divergence: price swing low LOWER but CVD at that swing HIGHER
   if(ArraySize(swLowBars) >= 2)
   {
      if(swLowPrices[0] < swLowPrices[1])   // price made lower low
      {
         if(swLowCVD[0] > swLowCVD[1])      // but CVD didn't confirm
         {
            double cvdRise = (swLowCVD[0] - swLowCVD[1]) /
                             MathMax(MathAbs(swLowCVD[1]), 1.0);
            if(cvdRise >= InpDivThreshold)
            {
               PrintFormat("[CVD] BULLISH DIV: Price %.2f<%.2f but CVD %.0f>%.0f (rise %.1f%%)",
                           swLowPrices[0], swLowPrices[1],
                           swLowCVD[0], swLowCVD[1], cvdRise * 100);
               return +1;
            }
         }
      }
   }

   return 0;
}

//+------------------------------------------------------------------+
//| OnTick                                                            |
//+------------------------------------------------------------------+
void OnTick()
{
   if(InpKillSwitch) return;

   datetime barTime = iTime(_Symbol, PERIOD_CURRENT, 0);
   if(barTime == g_lastBar) return;
   g_lastBar = barTime;

   MqlDateTime dt;
   TimeToStruct(barTime, dt);

   // Day reset
   if(dt.day_of_year != g_lastTradeDay)
   {
      g_lastTradeDay = dt.day_of_year;
      g_tradesToday = 0;
      g_dayStartBalance = AccountInfoDouble(ACCOUNT_BALANCE);
   }

   // Time stop
   if(dt.hour >= InpExitHour && CountPositions() > 0)
   {
      CloseAllPositions();
      return;
   }

   // Session filter
   if(dt.hour < InpStartHour || dt.hour >= InpEndHour) return;

   // Pre-flight
   if(g_tradesToday >= InpMaxPerDay) return;
   if(CountPositions() > 0) return;
   if(IsDailyDDExceeded()) return;

   // Day filters
   if(InpSkipMon && dt.day_of_week == 1) return;
   if(InpSkipFri && dt.day_of_week == 5) return;

   // Detect divergence
   int signal = DetectDivergence();
   if(signal == 0) return;

   // Get ATR for SL
   double atr[];
   ArraySetAsSeries(atr, true);
   if(CopyBuffer(g_hATR, 0, 1, 1, atr) < 1) return;

   double slDist = atr[0] * InpSL_ATR_Mult;
   if(slDist < InpMinSLPoints * _Point) slDist = InpMinSLPoints * _Point;
   if(slDist > InpMaxSLPoints * _Point) return;

   bool isSell = (signal == -1);

   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double entryPrice = isSell ? bid : ask;

   double sl, tp;
   if(isSell)
   {
      sl = bid + slDist;
      tp = bid - slDist * InpTP_Ratio;
   }
   else
   {
      sl = ask - slDist;
      tp = ask + slDist * InpTP_Ratio;
   }

   // Stop level check
   int stopLevel = (int)SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL);
   if(slDist < stopLevel * _Point) return;

   double lot = CalcLot(slDist);
   if(lot <= 0) return;

   int digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
   sl = NormalizeDouble(sl, digits);
   tp = NormalizeDouble(tp, digits);

   MqlTradeRequest req = {};
   MqlTradeResult  res = {};
   req.action    = TRADE_ACTION_DEAL;
   req.symbol    = _Symbol;
   req.volume    = lot;
   req.type      = isSell ? ORDER_TYPE_SELL : ORDER_TYPE_BUY;
   req.price     = entryPrice;
   req.sl        = sl;
   req.tp        = tp;
   req.deviation = (ulong)InpDeviation;
   req.magic     = InpMagic;
   req.comment   = StringFormat("CVD|%s|div=%.2f",
                                isSell ? "BearDiv" : "BullDiv",
                                InpDivThreshold);
   req.type_filling = ORDER_FILLING_FOK;

   if(!OrderSend(req, res))
   {
      req.type_filling = ORDER_FILLING_IOC;
      if(!OrderSend(req, res))
      {
         PrintFormat("[CVD] OrderSend FAIL: err=%d retcode=%d",
                     GetLastError(), res.retcode);
         return;
      }
   }

   if(res.retcode == TRADE_RETCODE_DONE || res.retcode == TRADE_RETCODE_PLACED)
   {
      g_tradesToday++;
      PrintFormat("[CVD] %s %.2f @ %.2f | SL=%.2f TP=%.2f",
                  isSell ? "SELL" : "BUY", lot, res.price, sl, tp);
   }
}

//+------------------------------------------------------------------+
//| Tester                                                            |
//+------------------------------------------------------------------+
double OnTester()
{
   double pf = TesterStatistics(STAT_PROFIT_FACTOR);
   double trades = TesterStatistics(STAT_TRADES);
   if(trades < 20) return 0;
   return pf * MathSqrt(trades);
}
//+------------------------------------------------------------------+
