//+------------------------------------------------------------------+
//| EA_GammaPin.mq5 — COMEX Options Expiry Gamma Pinning             |
//| Symbol: XAUUSD+  |  Period: M15  |  Style: Mean-Reversion Scalp  |
//|                                                                   |
//| EDGE HYPOTHESIS:                                                  |
//| COMEX gold options expire on the 3rd Friday of each month.        |
//| Market-makers who sold options must delta-hedge: buy when price    |
//| approaches strike from below, sell when above. This creates       |
//| mechanical mean-reversion pressure toward "max pain" strike.      |
//|                                                                   |
//| Since we don't have COMEX OI data in MT5, we approximate          |
//| max pain as the nearest $25 round number level (major strikes     |
//| cluster at $25 intervals: 2375, 2400, 2425, etc.)                |
//|                                                                   |
//| Academic basis:                                                   |
//| - Ni, Pearson & Poteshman (2005) JFE: price clustering at        |
//|   option strikes on expiry dates                                  |
//| - SSRN #3520933: COMEX gold settlement manipulation               |
//|                                                                   |
//| ENTRY:                                                            |
//| - D-3 to D-0 before COMEX monthly options expiry (3rd Friday)     |
//| - Price > max_pain_proxy + buffer → SELL toward max_pain          |
//| - Price < max_pain_proxy - buffer → BUY toward max_pain           |
//| - Only during NY session (h14-h21 server time)                    |
//| - ATR filter: only trade if ATR > minimum (enough vol)            |
//|                                                                   |
//| EXIT: TP at max_pain level, SL at buffer * RR_mult               |
//|                                                                   |
//| SIGNALS ON BAR[1] ONLY — no repaint, no lookahead.               |
//| Max | 2026-04-12 | v1.0                                          |
//+------------------------------------------------------------------+
#property copyright "Max — EA_GammaPin v1.0"
#property link      ""
#property version   "1.00"
#property strict

//+------------------------------------------------------------------+
//| Input Parameters                                                  |
//+------------------------------------------------------------------+
input group "=== General ==="
input ulong    InpMagic          = 206501;     // Magic Number
input int      InpDeviation      = 30;         // Max Slippage (pts)

input group "=== Gamma Pinning ==="
input int      InpDaysBefore     = 3;          // Days before expiry to start
input double   InpStrikeInterval = 25.0;       // Strike interval ($25 for gold)
input double   InpEntryBuffer    = 8.0;        // Min distance from max_pain ($)
input double   InpMaxDistance    = 40.0;        // Max distance from max_pain ($)

input group "=== Session Filter ==="
input int      InpSessionStart   = 14;         // NY session start (server hour)
input int      InpSessionEnd     = 21;         // NY session end (server hour)
input bool     InpSkipH16        = false;      // Skip hour 16 (NY open momentum)

input group "=== ATR Filter ==="
input int      InpATR_Period     = 14;         // ATR period
input double   InpATR_MinPips    = 3.0;        // Min ATR ($) to trade

input group "=== Risk Management ==="
input double   InpRiskPct        = 0.50;       // Risk per trade (% balance)
input double   InpMaxLot         = 1.0;        // Max lot
input double   InpSL_Dollars     = 15.0;       // SL distance ($)
input double   InpRR             = 1.5;        // Risk:Reward (TP = entry_dist or RR*SL)
input int      InpMaxPerDay      = 2;          // Max trades per day
input int      InpMaxPerCycle    = 4;          // Max trades per expiry cycle
input double   InpDailyDD        = 4.0;        // Daily DD limit (%)

//+------------------------------------------------------------------+
//| Globals                                                           |
//+------------------------------------------------------------------+
int      g_hATR = INVALID_HANDLE;
datetime g_lastBar = 0;
int      g_tradesToday = 0;
int      g_tradesThisCycle = 0;
int      g_lastTradeDay = -1;
int      g_lastExpiryMonth = -1;
double   g_dayStartBalance = 0;

//+------------------------------------------------------------------+
//| Expert initialization                                             |
//+------------------------------------------------------------------+
int OnInit()
{
   g_hATR = iATR(_Symbol, PERIOD_CURRENT, InpATR_Period);
   if(g_hATR == INVALID_HANDLE)
   {
      Print("[GPIN] FATAL: ATR init failed");
      return INIT_FAILED;
   }

   g_dayStartBalance = AccountInfoDouble(ACCOUNT_BALANCE);

   PrintFormat("[GPIN] EA_GammaPin v1.00 | %s %s | Magic=%d",
               _Symbol, EnumToString(_Period), InpMagic);
   PrintFormat("[GPIN] Strike=$%.0f | Buffer=$%.1f | MaxDist=$%.1f | SL=$%.1f | RR=%.1f",
               InpStrikeInterval, InpEntryBuffer, InpMaxDistance,
               InpSL_Dollars, InpRR);
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   if(g_hATR != INVALID_HANDLE) IndicatorRelease(g_hATR);
}

//+------------------------------------------------------------------+
//| Find 3rd Friday of given month/year                               |
//| COMEX gold options expiry = 3rd Friday (not Wednesday as some     |
//| sources state; CME clarified this for GC options)                 |
//+------------------------------------------------------------------+
datetime ThirdFriday(int year, int month)
{
   MqlDateTime dt = {};
   dt.year = year;
   dt.mon  = month;
   dt.day  = 1;
   dt.hour = 12;

   datetime firstDay = StructToTime(dt);
   TimeToStruct(firstDay, dt);

   // day_of_week: 0=Sun, 5=Fri
   int dow = dt.day_of_week;
   int firstFriday = (dow <= 5) ? (6 - dow) : (6 - dow + 7);
   if(firstFriday == 0) firstFriday = 7;
   // Actually: if day 1 is Sun(0), first Fri = day 6
   //           if day 1 is Mon(1), first Fri = day 5
   //           if day 1 is Fri(5), first Fri = day 1
   //           if day 1 is Sat(6), first Fri = day 7
   firstFriday = 1 + ((5 - dow + 7) % 7);

   int thirdFriday = firstFriday + 14;

   dt.day = thirdFriday;
   return StructToTime(dt);
}

//+------------------------------------------------------------------+
//| Check if current date is within expiry window                     |
//| Returns days to expiry (0 = expiry day, -1 = outside window)      |
//+------------------------------------------------------------------+
int DaysToExpiry(datetime barTime)
{
   MqlDateTime dt;
   TimeToStruct(barTime, dt);

   // Current month expiry
   datetime expiry = ThirdFriday(dt.year, dt.mon);

   // If expiry already passed this month, use next month
   if(barTime > expiry + 86400)
   {
      int nextMon = dt.mon + 1;
      int nextYear = dt.year;
      if(nextMon > 12) { nextMon = 1; nextYear++; }
      expiry = ThirdFriday(nextYear, nextMon);
   }

   // Calendar days to expiry
   int daysDiff = (int)((expiry - barTime) / 86400);
   if(daysDiff < 0) daysDiff = 0;

   if(daysDiff <= InpDaysBefore)
      return daysDiff;

   return -1;  // Outside window
}

//+------------------------------------------------------------------+
//| Calculate max pain proxy: nearest strike interval level           |
//+------------------------------------------------------------------+
double CalcMaxPainProxy(double currentPrice)
{
   return MathRound(currentPrice / InpStrikeInterval) * InpStrikeInterval;
}

//+------------------------------------------------------------------+
//| Count positions with our magic                                    |
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
//| Check daily DD                                                    |
//+------------------------------------------------------------------+
bool IsDailyDDExceeded()
{
   if(g_dayStartBalance <= 0) return false;
   double eq = AccountInfoDouble(ACCOUNT_EQUITY);
   return ((g_dayStartBalance - eq) / g_dayStartBalance * 100.0) >= InpDailyDD;
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
//| Expert tick function                                              |
//+------------------------------------------------------------------+
void OnTick()
{
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

   // Expiry cycle reset
   if(dt.mon != g_lastExpiryMonth)
   {
      g_lastExpiryMonth = dt.mon;
      g_tradesThisCycle = 0;
   }

   // Pre-flight
   if(g_tradesToday >= InpMaxPerDay) return;
   if(g_tradesThisCycle >= InpMaxPerCycle) return;
   if(CountPositions() > 0) return;
   if(IsDailyDDExceeded()) return;

   // Session filter (server time)
   if(dt.hour < InpSessionStart || dt.hour >= InpSessionEnd) return;
   if(InpSkipH16 && dt.hour == 16) return;

   // Expiry window check
   int daysToExp = DaysToExpiry(barTime);
   if(daysToExp < 0) return;  // Not in expiry window

   // ATR filter (bar[1])
   double atr[];
   ArraySetAsSeries(atr, true);
   if(CopyBuffer(g_hATR, 0, 1, 1, atr) < 1) return;
   if(atr[0] < InpATR_MinPips) return;

   // Get bar[1] data (closed bar — no repaint)
   double close1 = iClose(_Symbol, PERIOD_CURRENT, 1);

   // Calculate max pain proxy
   double maxPain = CalcMaxPainProxy(close1);
   double dist = close1 - maxPain;  // Positive = above max_pain
   double absDist = MathAbs(dist);

   // Check distance thresholds
   if(absDist < InpEntryBuffer) return;   // Too close, no edge
   if(absDist > InpMaxDistance) return;    // Too far, max pain pull too weak

   // Determine direction
   ENUM_ORDER_TYPE orderType;
   double price, sl, tp;
   int digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
   double pt = _Point;

   double slDist = InpSL_Dollars / pt;  // Convert $ to points
   slDist = slDist * pt;                // Back to price distance

   // Actually: for XAUUSD, 1 point = $0.01, so $15 SL = 1500 points = $15.00
   // Simpler: just use dollar values directly since XAUUSD is quoted in $/oz
   double slPrice = InpSL_Dollars;
   double tpPrice = MathMin(absDist, InpRR * slPrice);  // TP = distance to max_pain or RR*SL

   if(dist > 0)
   {
      // Price ABOVE max pain → SELL (gamma pulls price down)
      double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
      price = bid;
      sl = NormalizeDouble(price + slPrice, digits);
      tp = NormalizeDouble(price - tpPrice, digits);
      orderType = ORDER_TYPE_SELL;
   }
   else
   {
      // Price BELOW max pain → BUY (gamma pulls price up)
      double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
      price = ask;
      sl = NormalizeDouble(price - slPrice, digits);
      tp = NormalizeDouble(price + tpPrice, digits);
      orderType = ORDER_TYPE_BUY;
   }

   // Stop level check
   int stopLevel = (int)SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL);
   double minDist = stopLevel * pt;
   if(MathAbs(price - sl) < minDist || MathAbs(price - tp) < minDist)
      return;

   // Lot sizing
   double lot = CalcLot(MathAbs(price - sl));
   if(lot <= 0) return;

   // Execute order
   MqlTradeRequest req = {};
   MqlTradeResult  res = {};

   req.action    = TRADE_ACTION_DEAL;
   req.symbol    = _Symbol;
   req.volume    = lot;
   req.type      = orderType;
   req.price     = price;
   req.sl        = sl;
   req.tp        = tp;
   req.deviation = (ulong)InpDeviation;
   req.magic     = InpMagic;
   req.comment   = StringFormat("GPIN|D-%d|MP=%.0f|dist=%.1f",
                                daysToExp, maxPain, dist);
   req.type_filling = ORDER_FILLING_FOK;

   if(!OrderSend(req, res))
   {
      req.type_filling = ORDER_FILLING_IOC;
      if(!OrderSend(req, res))
      {
         PrintFormat("[GPIN] OrderSend FAIL: err=%d ret=%d",
                     GetLastError(), res.retcode);
         return;
      }
   }

   if(res.retcode == TRADE_RETCODE_DONE || res.retcode == TRADE_RETCODE_PLACED)
   {
      g_tradesToday++;
      g_tradesThisCycle++;
      PrintFormat("[GPIN] %s %.2f @ %.2f | SL=%.2f TP=%.2f | MP=%.0f D-%d",
                  (orderType == ORDER_TYPE_SELL) ? "SELL" : "BUY",
                  lot, res.price, sl, tp, maxPain, daysToExp);
   }
}

//+------------------------------------------------------------------+
//| Tester optimization criterion                                     |
//+------------------------------------------------------------------+
double OnTester()
{
   double pf = TesterStatistics(STAT_PROFIT_FACTOR);
   double trades = TesterStatistics(STAT_TRADES);
   if(trades < 20) return 0;
   return pf * MathSqrt(trades);
}
//+------------------------------------------------------------------+
