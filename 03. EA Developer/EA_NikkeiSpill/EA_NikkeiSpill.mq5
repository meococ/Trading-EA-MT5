//+------------------------------------------------------------------+
//| EA_NikkeiSpill.mq5 — Nikkei Gap → USDJPY Momentum Spillover     |
//| Symbol: USDJPY+  |  Period: M15  |  Style: Intraday Momentum     |
//|                                                                   |
//| EDGE HYPOTHESIS:                                                  |
//| Nikkei225 opens at 9:00 JST (00:00 UTC) after absorbing          |
//| overnight NY session news. Gap > threshold in Nikkei correlates   |
//| +0.80-0.94 with USDJPY direction. Momentum persists for 60-90    |
//| minutes into Tokyo session as retail traders lag the adjustment.   |
//|                                                                   |
//| IMPLEMENTATION (no Nikkei data needed):                           |
//| Since Nikkei-USDJPY are highly correlated, we proxy the gap      |
//| using USDJPY's own move from NY close to Tokyo open.              |
//| - Measure USDJPY move: bar[TokyoOpen] vs bar[NYClose]            |
//| - If gap > threshold: enter momentum direction                    |
//| - Hold for N bars (60-90 min) or until SL/TP hit                 |
//|                                                                   |
//| COUNTERPARTY: Retail USDJPY traders who haven't adjusted          |
//| positions for overnight Nikkei/equity sentiment shift.            |
//|                                                                   |
//| ACADEMIC: "Decoding Momentum Spillover Effects" — JFQA 2024      |
//| Monthly excess returns 0.95-1.01% for connected-firm strategies.  |
//|                                                                   |
//| SIGNALS ON BAR[1] ONLY — no repaint, no lookahead.               |
//| Max | 2026-04-12 | v1.0                                          |
//+------------------------------------------------------------------+
#property copyright "Max — EA_NikkeiSpill v1.0"
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

input group "=== Gap Detection ==="
input int      InpNYCloseHour   = 21;         // NY Close reference hour (UTC/server)
input int      InpTokyoOpenHour = 0;          // Tokyo open hour (UTC/server)
input int      InpGapBars       = 4;          // Bars after Tokyo open to measure gap
input double   InpMinGapPips    = 8.0;        // Min gap size (pips) to trigger
input double   InpMaxGapPips    = 80.0;       // Max gap size (pips) - skip extreme

input group "=== Trade Management ==="
input int      InpHoldBars      = 6;          // Max bars to hold (6 x M15 = 90min)
input double   InpSLPips        = 15.0;       // Stop loss (pips)
input double   InpTPMultiple    = 1.5;        // TP = SL x multiple (asymmetric)
input bool     InpUseBE         = true;       // Move SL to BE at 1.0R profit
input int      InpMaxPerDay     = 1;          // Max trades per day (1 opp/day)

input group "=== Risk ==="
input double   InpRiskPct       = 0.50;       // Risk per trade (% balance)
input double   InpMaxLot        = 1.0;        // Max lot
input double   InpDailyDD       = 4.0;        // Daily DD kill (%)

input group "=== Day Filters ==="
input bool     InpSkipMon       = false;      // Skip Monday (weekend gap noise)
input bool     InpSkipFri       = true;       // Skip Friday (position risk)

//+------------------------------------------------------------------+
//| Globals                                                           |
//+------------------------------------------------------------------+
datetime g_lastBar        = 0;
int      g_tradesToday    = 0;
int      g_lastTradeDay   = -1;
double   g_dayStartBal    = 0;
datetime g_entryBarTime   = 0;     // Track when we entered
int      g_barsHeld       = 0;     // Count bars since entry
double   g_entryPrice     = 0;     // Entry price for BE logic
double   g_entrySL        = 0;     // Original SL for R calc

//+------------------------------------------------------------------+
//| Expert initialization                                             |
//+------------------------------------------------------------------+
int OnInit()
{
   if(StringFind(_Symbol, "JPY") < 0)
      PrintFormat("[NKS] WARNING: Designed for USDJPY, running on %s", _Symbol);

   g_dayStartBal = AccountInfoDouble(ACCOUNT_BALANCE);

   PrintFormat("[NKS] EA_NikkeiSpill v1.00 | Symbol=%s | TF=%s | Magic=%d",
               _Symbol, EnumToString(_Period), InpMagic);
   PrintFormat("[NKS] Gap: NYClose=h%d TokyoOpen=h%d MinGap=%.1f MaxGap=%.1f pips",
               InpNYCloseHour, InpTokyoOpenHour, InpMinGapPips, InpMaxGapPips);
   PrintFormat("[NKS] Trade: SL=%.1f TP=%.1fx Hold=%d bars Risk=%.2f%%",
               InpSLPips, InpTPMultiple, InpHoldBars, InpRiskPct);
   return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
void OnDeinit(const int reason) { }

//+------------------------------------------------------------------+
//| Pip value helper                                                  |
//+------------------------------------------------------------------+
double PipSize()
{
   return (_Digits == 3 || _Digits == 5) ? _Point * 10 : _Point;
}

//+------------------------------------------------------------------+
//| Get close price at a specific hour on previous day                |
//| Scans backward to find bar with matching hour                     |
//+------------------------------------------------------------------+
double GetPriceAtHour(int targetHour, int daysBack)
{
   datetime now = iTime(_Symbol, PERIOD_CURRENT, 1);
   MqlDateTime dt;
   TimeToStruct(now, dt);
   dt.hour = targetHour;
   dt.min = 0;
   dt.sec = 0;

   // Go back N days
   datetime target = StructToTime(dt) - daysBack * 86400;

   int bar = iBarShift(_Symbol, PERIOD_CURRENT, target, false);
   if(bar <= 0) return 0;

   return iClose(_Symbol, PERIOD_CURRENT, bar);
}

//+------------------------------------------------------------------+
//| Measure gap: USDJPY at Tokyo open vs NY close                    |
//| Returns gap in pips (positive = moved up, negative = down)        |
//+------------------------------------------------------------------+
double MeasureGap()
{
   // Find NY close price (previous day's InpNYCloseHour)
   // and Tokyo open price (today's InpTokyoOpenHour + InpGapBars)
   datetime barTime = iTime(_Symbol, PERIOD_CURRENT, 1);
   MqlDateTime dtNow;
   TimeToStruct(barTime, dtNow);

   // We only trigger shortly after Tokyo open
   // Current bar[1] should be near InpTokyoOpenHour + InpGapBars * period_minutes
   int curHour = dtNow.hour;
   int periodMin = PeriodSeconds() / 60;
   int targetMin = InpTokyoOpenHour * 60 + InpGapBars * periodMin;
   int curMin = curHour * 60 + dtNow.min;

   // Allow 1-bar tolerance
   if(MathAbs(curMin - targetMin) > periodMin) return 0;

   // Tokyo open bar: find bar at InpTokyoOpenHour:00 today
   MqlDateTime dtTokyo;
   dtTokyo = dtNow;
   dtTokyo.hour = InpTokyoOpenHour;
   dtTokyo.min = 0;
   dtTokyo.sec = 0;
   datetime tokyoTime = StructToTime(dtTokyo);
   int barTokyo = iBarShift(_Symbol, PERIOD_CURRENT, tokyoTime, false);
   if(barTokyo <= 0) return 0;

   double tokyoOpen = iOpen(_Symbol, PERIOD_CURRENT, barTokyo);

   // NY close: previous day at InpNYCloseHour
   // If Tokyo open is at hour 0, NY close was yesterday
   MqlDateTime dtNY;
   dtNY = dtNow;
   if(InpTokyoOpenHour <= InpNYCloseHour)
   {
      // NY close was yesterday
      datetime yesterday = tokyoTime - 86400;
      TimeToStruct(yesterday, dtNY);
   }
   dtNY.hour = InpNYCloseHour;
   dtNY.min = 0;
   dtNY.sec = 0;
   datetime nyTime = StructToTime(dtNY);
   int barNY = iBarShift(_Symbol, PERIOD_CURRENT, nyTime, false);
   if(barNY <= 0 || barNY <= barTokyo) return 0;

   double nyClose = iClose(_Symbol, PERIOD_CURRENT, barNY);

   if(nyClose <= 0 || tokyoOpen <= 0) return 0;

   // Current price vs NY close (gap direction)
   double curClose = iClose(_Symbol, PERIOD_CURRENT, 1);
   double gapPips = (curClose - nyClose) / PipSize();

   return gapPips;
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
//| Manage open position: time exit + break-even                      |
//+------------------------------------------------------------------+
void ManagePosition()
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0) continue;
      if(PositionGetInteger(POSITION_MAGIC) != (long)InpMagic) continue;
      if(PositionGetString(POSITION_SYMBOL) != _Symbol) continue;

      datetime openTime = (datetime)PositionGetInteger(POSITION_TIME);
      double   openPrice = PositionGetDouble(POSITION_PRICE_OPEN);
      double   curSL     = PositionGetDouble(POSITION_SL);
      long     posType   = PositionGetInteger(POSITION_TYPE);
      double   profit    = PositionGetDouble(POSITION_PROFIT);

      // Count bars since entry
      int barsSinceEntry = iBarShift(_Symbol, PERIOD_CURRENT, openTime, false);

      // Time exit: close after InpHoldBars
      if(barsSinceEntry >= InpHoldBars)
      {
         MqlTradeRequest req = {};
         MqlTradeResult  res = {};
         req.action   = TRADE_ACTION_DEAL;
         req.symbol   = _Symbol;
         req.volume   = PositionGetDouble(POSITION_VOLUME);
         req.type     = (posType == POSITION_TYPE_BUY) ? ORDER_TYPE_SELL : ORDER_TYPE_BUY;
         req.price    = (posType == POSITION_TYPE_BUY) ?
                        SymbolInfoDouble(_Symbol, SYMBOL_BID) :
                        SymbolInfoDouble(_Symbol, SYMBOL_ASK);
         req.deviation = (ulong)InpDeviation;
         req.magic     = InpMagic;
         req.position  = ticket;
         req.comment   = "NKS|TimeExit";
         req.type_filling = ORDER_FILLING_FOK;

         if(!OrderSend(req, res))
         {
            req.type_filling = ORDER_FILLING_IOC;
            OrderSend(req, res);
         }

         if(res.retcode == TRADE_RETCODE_DONE || res.retcode == TRADE_RETCODE_PLACED)
            PrintFormat("[NKS] TIME EXIT | bars=%d | profit=%.2f", barsSinceEntry, profit);
         return;
      }

      // Break-even logic
      if(InpUseBE && curSL != 0)
      {
         double slDist = MathAbs(openPrice - curSL);
         double curPrice = (posType == POSITION_TYPE_BUY) ?
                           SymbolInfoDouble(_Symbol, SYMBOL_BID) :
                           SymbolInfoDouble(_Symbol, SYMBOL_ASK);
         double profitDist = (posType == POSITION_TYPE_BUY) ?
                             (curPrice - openPrice) : (openPrice - curPrice);

         // Move SL to BE when profit >= 1.0R
         if(profitDist >= slDist)
         {
            double newSL = openPrice;  // BE
            int digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
            newSL = NormalizeDouble(newSL, digits);

            // Only move SL if it improves
            bool shouldMove = (posType == POSITION_TYPE_BUY) ?
                              (newSL > curSL) : (newSL < curSL);

            if(shouldMove)
            {
               MqlTradeRequest req = {};
               MqlTradeResult  res = {};
               req.action   = TRADE_ACTION_SLTP;
               req.symbol   = _Symbol;
               req.position = ticket;
               req.sl       = newSL;
               req.tp       = PositionGetDouble(POSITION_TP);

               if(OrderSend(req, res))
                  PrintFormat("[NKS] BE moved | SL=%.5f->%.5f", curSL, newSL);
            }
         }
      }
   }
}

//+------------------------------------------------------------------+
//| Calculate lot size                                                |
//+------------------------------------------------------------------+
double CalcLot(double slPips)
{
   if(slPips <= 0) return 0;

   double slDist   = slPips * PipSize();
   double balance  = AccountInfoDouble(ACCOUNT_BALANCE);
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
//| Check daily drawdown                                              |
//+------------------------------------------------------------------+
bool IsDailyDDExceeded()
{
   if(g_dayStartBal <= 0) return false;
   double eq = AccountInfoDouble(ACCOUNT_EQUITY);
   return ((g_dayStartBal - eq) / g_dayStartBal * 100.0) >= InpDailyDD;
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
      g_dayStartBal = AccountInfoDouble(ACCOUNT_BALANCE);
   }

   // Manage existing positions (time exit + BE)
   if(CountPositions() > 0)
   {
      ManagePosition();
      return;
   }

   // Pre-flight checks
   if(g_tradesToday >= InpMaxPerDay) return;
   if(IsDailyDDExceeded()) return;

   // Day filters
   if(InpSkipMon && dt.day_of_week == 1) return;
   if(InpSkipFri && dt.day_of_week == 5) return;

   //--- Measure gap
   double gapPips = MeasureGap();
   if(gapPips == 0) return;  // Not the right time or no data

   double absGap = MathAbs(gapPips);
   if(absGap < InpMinGapPips) return;    // Gap too small
   if(absGap > InpMaxGapPips) return;    // Gap too extreme (news/BoJ)

   //--- Determine direction: gap up = buy momentum, gap down = sell momentum
   bool isBuy = (gapPips > 0);

   double pip = PipSize();
   double sl_dist = InpSLPips * pip;
   double tp_dist = InpSLPips * InpTPMultiple * pip;

   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);

   double entryPrice, sl, tp;
   ENUM_ORDER_TYPE orderType;

   if(isBuy)
   {
      entryPrice = ask;
      sl = ask - sl_dist;
      tp = ask + tp_dist;
      orderType = ORDER_TYPE_BUY;
   }
   else
   {
      entryPrice = bid;
      sl = bid + sl_dist;
      tp = bid - tp_dist;
      orderType = ORDER_TYPE_SELL;
   }

   // Check stop level
   int stopLevel = (int)SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL);
   double minDist = stopLevel * _Point;
   if(sl_dist < minDist || tp_dist < minDist) return;

   // Lot sizing
   double lot = CalcLot(InpSLPips);
   if(lot <= 0) return;

   // Normalize
   int digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
   sl = NormalizeDouble(sl, digits);
   tp = NormalizeDouble(tp, digits);

   //--- Execute
   MqlTradeRequest req = {};
   MqlTradeResult  res = {};

   req.action    = TRADE_ACTION_DEAL;
   req.symbol    = _Symbol;
   req.volume    = lot;
   req.type      = orderType;
   req.price     = entryPrice;
   req.sl        = sl;
   req.tp        = tp;
   req.deviation = (ulong)InpDeviation;
   req.magic     = InpMagic;
   req.comment   = StringFormat("NKS|%s|Gap=%.1f",
                                isBuy ? "B" : "S", gapPips);
   req.type_filling = ORDER_FILLING_FOK;

   if(!OrderSend(req, res))
   {
      req.type_filling = ORDER_FILLING_IOC;
      if(!OrderSend(req, res))
      {
         PrintFormat("[NKS] OrderSend FAIL: err=%d retcode=%d",
                     GetLastError(), res.retcode);
         return;
      }
   }

   if(res.retcode == TRADE_RETCODE_DONE || res.retcode == TRADE_RETCODE_PLACED)
   {
      g_tradesToday++;
      g_entryPrice = entryPrice;
      g_entrySL = sl;
      PrintFormat("[NKS] %s %.2f @ %.5f | SL=%.5f TP=%.5f | Gap=%.1f pips",
                  isBuy ? "BUY" : "SELL", lot, res.price, sl, tp, gapPips);
   }
}

//+------------------------------------------------------------------+
double OnTester()
{
   double pf = TesterStatistics(STAT_PROFIT_FACTOR);
   double trades = TesterStatistics(STAT_TRADES);
   if(trades < 30) return 0;
   return pf * MathSqrt(trades);
}
//+------------------------------------------------------------------+
