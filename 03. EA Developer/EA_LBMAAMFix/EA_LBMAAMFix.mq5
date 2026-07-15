//+------------------------------------------------------------------+
//| EA_LBMAAMFix.mq5 — LBMA AM Fix Overnight Mean Reversion          |
//| Symbol: XAUUSD+  |  Period: M15  |  Style: Intraday MR            |
//|                                                                   |
//| EDGE HYPOTHESIS:                                                  |
//| Asian session overnight positions are unwound at LBMA AM Fix      |
//| (10:30 London = ~09:30 UTC summer / 10:30 UTC winter).            |
//| When gold moves significantly overnight (PM Fix → AM Fix),        |
//| institutional exit pressure at AM Fix creates mean reversion.     |
//|                                                                   |
//| 50yr LBMA data (Robin Haupt) shows ALL gold gains happen          |
//| overnight. AM-to-PM holding = near-zero/negative returns.         |
//| This implies AM Fix = institutional EXIT point from overnight     |
//| positions, creating counter-trend pressure post-AM Fix.           |
//|                                                                   |
//| DIFFERENT FROM COBRA:                                              |
//| - Cobra = PM Fix (15:00 UTC, h16-17 server), NYSE close flow     |
//| - This EA = AM Fix (09:30 UTC, h11-12 server), Asian unwind      |
//| - Different counterparty, different time, different mechanism     |
//| - Expected correlation with Cobra: near zero                      |
//|                                                                   |
//| SIGNALS ON BAR[1] ONLY — no repaint, no lookahead.                |
//| Max | 2026-04-12 | v1.0                                          |
//+------------------------------------------------------------------+
#property copyright "Max — EA_LBMAAMFix v1.0"
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

input group "=== AM Fix Timing (Server Time) ==="
input int      InpAMFixHour     = 12;         // AM Fix hour (server, ~09:30-10:30 UTC)
input int      InpPMFixHour     = 17;         // PM Fix hour (server, ~15:00 UTC)
input int      InpExitHour      = 16;         // Time stop hour (server, before PM Fix)

input group "=== Overnight Move Threshold ==="
input int      InpMinMovePoints = 500;        // Min overnight move (points, e.g. 500 = $5)
input bool     InpUseATR        = true;       // Use ATR-based threshold instead
input double   InpATR_Mult      = 0.5;        // ATR multiplier for threshold (Daily ATR)
input int      InpATR_Period    = 14;         // ATR period (Daily)

input group "=== Risk Management ==="
input double   InpRiskPct       = 0.50;       // Risk per trade (%)
input double   InpMaxLot        = 1.0;        // Max lot
input double   InpSL_ATR_Mult   = 1.0;        // SL = N x ATR(14) on M15
input int      InpMinSLPoints   = 100;        // Min SL (points)
input int      InpMaxSLPoints   = 800;        // Max SL (points)
input double   InpTP_Ratio      = 1.0;        // TP ratio (1.0 = 1:1 RR)
input int      InpMaxPerDay     = 1;          // Max trades per day
input double   InpDailyDD       = 4.0;        // Daily DD Limit (%)

input group "=== Day Filters ==="
input bool     InpSkipMon       = false;      // Skip Monday
input bool     InpSkipFri       = true;       // Skip Friday (weekend risk)

//+------------------------------------------------------------------+
//| Globals                                                           |
//+------------------------------------------------------------------+
int      g_hATR_D1  = INVALID_HANDLE;  // Daily ATR for threshold
int      g_hATR_M15 = INVALID_HANDLE;  // M15 ATR for SL
datetime g_lastBar = 0;
int      g_tradesToday = 0;
int      g_lastTradeDay = -1;
double   g_dayStartBalance = 0;
double   g_pmFixPrice = 0;         // Yesterday's PM Fix reference price
datetime g_pmFixDate = 0;          // Date of stored PM Fix
bool     g_tradedAMFix = false;    // Already traded this AM Fix?

//+------------------------------------------------------------------+
//| Expert initialization                                             |
//+------------------------------------------------------------------+
int OnInit()
{
   g_hATR_D1 = iATR(_Symbol, PERIOD_D1, InpATR_Period);
   g_hATR_M15 = iATR(_Symbol, PERIOD_M15, 14);

   if(g_hATR_D1 == INVALID_HANDLE || g_hATR_M15 == INVALID_HANDLE)
   {
      Print("[AMF] FATAL: ATR indicator init failed");
      return INIT_FAILED;
   }

   g_dayStartBalance = AccountInfoDouble(ACCOUNT_BALANCE);

   PrintFormat("[AMF] EA_LBMAAMFix v1.00 | Symbol=%s | TF=%s | Magic=%d",
               _Symbol, EnumToString(_Period), InpMagic);
   PrintFormat("[AMF] AM Fix=%d:00 | PM Fix=%d:00 | Exit=%d:00 server time",
               InpAMFixHour, InpPMFixHour, InpExitHour);
   PrintFormat("[AMF] Threshold: %s | SL=%.1f ATR(M15) | TP=%.1f:1",
               InpUseATR ? StringFormat("%.1fx Daily ATR(%d)", InpATR_Mult, InpATR_Period)
                         : StringFormat("%d pts fixed", InpMinMovePoints),
               InpSL_ATR_Mult, InpTP_Ratio);

   return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
//| Expert deinitialization                                           |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   if(g_hATR_D1 != INVALID_HANDLE)  IndicatorRelease(g_hATR_D1);
   if(g_hATR_M15 != INVALID_HANDLE) IndicatorRelease(g_hATR_M15);
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
//| Close all positions with our magic (time stop)                    |
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
      req.position = ticket;
      req.type_filling = ORDER_FILLING_FOK;

      if(!OrderSend(req, res))
      {
         req.type_filling = ORDER_FILLING_IOC;
         OrderSend(req, res);
      }

      if(res.retcode == TRADE_RETCODE_DONE)
         PrintFormat("[AMF] Time stop: closed ticket %d", ticket);
   }
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

   // New bar check (M15)
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
      g_tradedAMFix = false;
      g_dayStartBalance = AccountInfoDouble(ACCOUNT_BALANCE);
   }

   //--- Time stop: close positions at exit hour
   if(dt.hour >= InpExitHour && CountPositions() > 0)
   {
      CloseAllPositions();
      return;
   }

   //--- Capture PM Fix reference price each day
   //    Store close of the bar at PM Fix hour as reference
   if(dt.hour == InpPMFixHour && dt.min == 0)
   {
      // Use close of bar[1] (the bar that just closed at PM Fix hour)
      g_pmFixPrice = iClose(_Symbol, PERIOD_CURRENT, 1);
      g_pmFixDate = barTime;
      PrintFormat("[AMF] PM Fix ref captured: %.2f at %s",
                  g_pmFixPrice, TimeToString(barTime));
   }

   //--- AM Fix entry logic
   //    Only trade at the AM Fix hour
   if(dt.hour != InpAMFixHour || dt.min != 0) return;
   if(g_tradedAMFix) return;

   // Pre-flight
   if(g_tradesToday >= InpMaxPerDay) return;
   if(CountPositions() > 0) return;
   if(IsDailyDDExceeded()) return;

   // Day filters
   if(InpSkipMon && dt.day_of_week == 1) return;
   if(InpSkipFri && dt.day_of_week == 5) return;

   // Need valid PM Fix reference from yesterday
   if(g_pmFixPrice <= 0) return;

   // Check PM Fix was from yesterday (not today or stale)
   MqlDateTime pmDt;
   TimeToStruct(g_pmFixDate, pmDt);
   // PM Fix should be from previous trading day
   // Allow 1-3 days gap (weekend)
   double daysDiff = (double)(barTime - g_pmFixDate) / 86400.0;
   if(daysDiff < 0.3 || daysDiff > 4.0) return;  // Stale or same-day

   //--- Calculate overnight move
   double amPrice = iClose(_Symbol, PERIOD_CURRENT, 1);  // bar[1] close at AM Fix
   double overnightMove = amPrice - g_pmFixPrice;         // positive = gold rallied overnight

   //--- Get threshold
   double threshold = InpMinMovePoints * _Point;
   if(InpUseATR)
   {
      double atrD1[];
      ArraySetAsSeries(atrD1, true);
      if(CopyBuffer(g_hATR_D1, 0, 1, 1, atrD1) < 1) return;
      threshold = atrD1[0] * InpATR_Mult;
   }

   // Check if move is significant enough
   if(MathAbs(overnightMove) < threshold) return;

   //--- Get M15 ATR for SL
   double atrM15[];
   ArraySetAsSeries(atrM15, true);
   if(CopyBuffer(g_hATR_M15, 0, 1, 1, atrM15) < 1) return;

   double slDist = atrM15[0] * InpSL_ATR_Mult;

   // Clamp SL
   if(slDist < InpMinSLPoints * _Point)
      slDist = InpMinSLPoints * _Point;
   if(slDist > InpMaxSLPoints * _Point)
      return;

   //--- Direction: COUNTER to overnight move (mean reversion)
   //    Gold rallied overnight → SELL (AM Fix exit pressure)
   //    Gold dropped overnight → BUY  (dip buying at AM Fix)
   bool isSell = (overnightMove > 0);

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

   //--- Check stop level
   int stopLevel = (int)SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL);
   double minDist = stopLevel * _Point;
   if(slDist < minDist) return;

   //--- Lot sizing
   double lot = CalcLot(slDist);
   if(lot <= 0) return;

   //--- Normalize prices
   int digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
   sl = NormalizeDouble(sl, digits);
   tp = NormalizeDouble(tp, digits);

   //--- Execute trade
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
   req.comment   = StringFormat("AMF|%s|ON=%.0f|Thr=%.0f",
                                isSell ? "S" : "B",
                                overnightMove / _Point,
                                threshold / _Point);
   req.type_filling = ORDER_FILLING_FOK;

   if(!OrderSend(req, res))
   {
      req.type_filling = ORDER_FILLING_IOC;
      if(!OrderSend(req, res))
      {
         PrintFormat("[AMF] OrderSend FAIL: err=%d retcode=%d",
                     GetLastError(), res.retcode);
         return;
      }
   }

   if(res.retcode == TRADE_RETCODE_DONE || res.retcode == TRADE_RETCODE_PLACED)
   {
      g_tradesToday++;
      g_tradedAMFix = true;
      PrintFormat("[AMF] %s %.2f @ %.2f | SL=%.2f TP=%.2f | ON=%.0fpts PM=%.2f AM=%.2f",
                  isSell ? "SELL" : "BUY", lot, res.price, sl, tp,
                  overnightMove / _Point, g_pmFixPrice, amPrice);
   }
   else
   {
      PrintFormat("[AMF] Order retcode=%d deal=%d", res.retcode, res.deal);
   }
}

//+------------------------------------------------------------------+
//| Tester event                                                      |
//+------------------------------------------------------------------+
double OnTester()
{
   double pf = TesterStatistics(STAT_PROFIT_FACTOR);
   double trades = TesterStatistics(STAT_TRADES);
   if(trades < 20) return 0;
   return pf * MathSqrt(trades);
}
//+------------------------------------------------------------------+
