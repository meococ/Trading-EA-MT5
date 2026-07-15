//+------------------------------------------------------------------+
//| EA_GoldRound.mq5 — Gold Round Number Reaction (M15)              |
//| Symbol: XAUUSD  |  Period: M15  |  Style: Level reaction         |
//|                                                                   |
//| EDGE HYPOTHESIS (v1.0):                                           |
//| Institutional orders cluster at round $50 levels on gold          |
//| (e.g. $2600, $2650, $2700). Price reacts at these levels:        |
//| rejection = mean reversion trade, breakout = momentum trade.      |
//|                                                                   |
//| MECHANISM:                                                        |
//| Pension funds, ETFs use round numbers as order thresholds.        |
//| Market makers defend these levels with limit orders.              |
//| Retail stop clusters above/below round numbers create liquidity.  |
//|                                                                   |
//| SOURCE: TraderViet, institutional flow literature                 |
//|                                                                   |
//| Max | 2026-04-05 | v1.0                                         |
//+------------------------------------------------------------------+
#property copyright "Max — EA_GoldRound v1.0"
#property version   "1.00"
#property strict

#include <Trade\Trade.mqh>

//+------------------------------------------------------------------+
input group "=== General ==="
input ulong    InpMagic         = 902601;    // Magic Number
input int      InpDeviation     = 50;        // Max Slippage (pts)
input bool     InpKillSwitch    = false;     // Kill Switch

input group "=== Round Number Settings ==="
input double   InpLevelStep     = 50.0;      // Level step ($50 = 500 pts)
input double   InpZonePoints    = 300.0;     // Zone size (points from level, 300=3.00)
input int      InpMode          = 0;         // 0=Rejection(mean-rev) 1=Break(momentum)

input group "=== Rejection Detection (Mode 0) ==="
input double   InpWickRatio     = 0.55;      // Min wick ratio (wick / total range)
input double   InpMinBodyPts    = 30.0;      // Min body size (points)
input int      InpLookback      = 3;         // Lookback bars to confirm approach

input group "=== Breakout Detection (Mode 1) ==="
input double   InpBrkBodyRatio  = 0.55;      // Min body ratio for breakout candle
input double   InpBrkATRMult    = 0.8;       // Min body as ATR multiple

input group "=== Session Filter (Server Time) ==="
input int      InpStartHour     = 9;         // Entry start hour (London)
input int      InpEndHour       = 18;        // Entry end hour

input group "=== Day Filters ==="
input bool     InpMonday        = true;      // Trade Monday
input bool     InpTuesday       = true;      // Trade Tuesday
input bool     InpWednesday     = true;      // Trade Wednesday
input bool     InpThursday      = true;      // Trade Thursday
input bool     InpFriday        = false;     // Trade Friday

input group "=== Risk Management ==="
input double   InpRiskPct       = 0.40;      // Risk per trade (%)
input double   InpMaxLot        = 0.50;      // Max lot
input double   InpATRMultSL     = 1.5;       // SL = ATR x this
input int      InpATRPeriod     = 14;        // ATR Period
input double   InpRR            = 2.0;       // Reward:Risk
input bool     InpUseBE         = true;      // Move SL to BE at 1R
input int      InpMaxPerDay     = 1;         // Max trades per day
input double   InpDailyDDPct    = 3.0;       // Daily DD kill (%)

input group "=== Datalog ==="
input bool     InpDatalog       = true;      // Enable CSV signal log

//+------------------------------------------------------------------+
CTrade         g_trade;
int            g_hATR;
datetime       g_lastBar;
int            g_todayTrades;
datetime       g_todayDate;
double         g_dayStartBal;
int            g_logHandle;

//+------------------------------------------------------------------+
int OnInit()
{
   if(InpKillSwitch) { Print("[GoldRound] Kill switch ON"); return INIT_SUCCEEDED; }

   g_trade.SetExpertMagicNumber(InpMagic);
   g_trade.SetDeviationInPoints(InpDeviation);
   g_trade.SetTypeFilling(ORDER_FILLING_FOK);

   g_hATR = iATR(_Symbol, PERIOD_CURRENT, InpATRPeriod);
   if(g_hATR == INVALID_HANDLE)
   { Print("[GoldRound] FATAL: ATR init failed"); return INIT_FAILED; }

   g_lastBar      = 0;
   g_todayTrades  = 0;
   g_todayDate    = 0;
   g_dayStartBal  = AccountInfoDouble(ACCOUNT_BALANCE);

   if(InpDatalog)
   {
      string fname = "GoldRound_datalog_" + _Symbol + ".csv";
      g_logHandle = FileOpen(fname, FILE_WRITE|FILE_CSV|FILE_COMMON, ',');
      if(g_logHandle != INVALID_HANDLE)
         FileWrite(g_logHandle,
            "Time","Signal","Price","NearestLevel","DistToLevel",
            "WickRatio","Body","ATR","SL","TP","Lot","SkipReason");
   }

   PrintFormat("[GoldRound] Init OK: %s LevelStep=$%.0f Zone=%.0f pts Mode=%d",
               _Symbol, InpLevelStep, InpZonePoints, InpMode);
   return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   if(g_hATR != INVALID_HANDLE) IndicatorRelease(g_hATR);
   if(g_logHandle != INVALID_HANDLE) FileClose(g_logHandle);
}

//+------------------------------------------------------------------+
double NearestRoundLevel(double price)
{
   // Find nearest $50 level: e.g. for gold at 2637 → 2650
   // Gold prices: 1 point = $0.01, so $50 = 5000 points (for 2-digit)
   // But MT5 gold has varying digits. Use actual price.
   double levelStep = InpLevelStep;
   return MathRound(price / levelStep) * levelStep;
}

//+------------------------------------------------------------------+
bool IsTradingDay(int dow)
{
   switch(dow)
   {
      case 1: return InpMonday;
      case 2: return InpTuesday;
      case 3: return InpWednesday;
      case 4: return InpThursday;
      case 5: return InpFriday;
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
      if(PositionGetInteger(POSITION_MAGIC) == InpMagic &&
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
void ManagePositions()
{
   if(!InpUseBE) return;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0) continue;
      if(PositionGetInteger(POSITION_MAGIC) != InpMagic) continue;
      if(PositionGetString(POSITION_SYMBOL) != _Symbol) continue;

      double openPrice = PositionGetDouble(POSITION_PRICE_OPEN);
      double sl        = PositionGetDouble(POSITION_SL);
      double tp        = PositionGetDouble(POSITION_TP);
      long   posType   = PositionGetInteger(POSITION_TYPE);
      double bid       = SymbolInfoDouble(_Symbol, SYMBOL_BID);
      double ask       = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
      double pt        = SymbolInfoDouble(_Symbol, SYMBOL_POINT);

      double slDist = MathAbs(openPrice - sl);
      if(posType == POSITION_TYPE_BUY)
      {
         if(bid >= openPrice + slDist && sl < openPrice)
            g_trade.PositionModify(ticket, openPrice + pt, tp);
      }
      else
      {
         if(ask <= openPrice - slDist && sl > openPrice)
            g_trade.PositionModify(ticket, openPrice - pt, tp);
      }
   }
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

   if(today != g_todayDate)
   {
      g_todayDate   = today;
      g_todayTrades = 0;
      g_dayStartBal = AccountInfoDouble(ACCOUNT_BALANCE);
   }

   // Manage existing
   if(CountMyPositions() > 0)
   {
      ManagePositions();
      return;
   }

   // Filters
   if(g_todayTrades >= InpMaxPerDay) return;
   if(!IsTradingDay(dt.day_of_week)) return;
   if(dt.hour < InpStartHour || dt.hour >= InpEndHour) return;

   double ddPct = (g_dayStartBal > 0)
                  ? (g_dayStartBal - AccountInfoDouble(ACCOUNT_EQUITY)) / g_dayStartBal * 100.0
                  : 0;
   if(ddPct >= InpDailyDDPct) return;

   // Read bar[1] data (non-repaint)
   double open1  = iOpen(_Symbol, PERIOD_CURRENT, 1);
   double close1 = iClose(_Symbol, PERIOD_CURRENT, 1);
   double high1  = iHigh(_Symbol, PERIOD_CURRENT, 1);
   double low1   = iLow(_Symbol, PERIOD_CURRENT, 1);
   int    digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
   double point  = SymbolInfoDouble(_Symbol, SYMBOL_POINT);

   // ATR
   double atr[];
   if(CopyBuffer(g_hATR, 0, 1, 1, atr) < 1) return;

   double body     = MathAbs(close1 - open1);
   double barRange = high1 - low1;
   if(barRange <= 0) return;

   // Find nearest round level
   double level = NearestRoundLevel(close1);
   double distToLevel = MathAbs(close1 - level) / point;

   // Must be near a round level
   if(distToLevel > InpZonePoints) return;

   int signal = 0;

   if(InpMode == 0)  // REJECTION mode (mean reversion)
   {
      // Detect rejection candle near level
      double upperWick = high1 - MathMax(open1, close1);
      double lowerWick = MathMin(open1, close1) - low1;

      // Price approached from below, rejected → SELL
      // Pin bar: upper wick long, body small, close near low
      double upperWickRatio = upperWick / barRange;
      double lowerWickRatio = lowerWick / barRange;

      // Check approach direction using lookback
      bool approachFromBelow = true;
      bool approachFromAbove = true;
      for(int i = 2; i <= InpLookback + 1; i++)
      {
         if(iClose(_Symbol, PERIOD_CURRENT, i) > level)
            approachFromBelow = false;
         if(iClose(_Symbol, PERIOD_CURRENT, i) < level)
            approachFromAbove = false;
      }

      // Rejection from above level → SELL (touched/exceeded level, closed back below)
      if(high1 >= level && close1 < level && upperWickRatio >= InpWickRatio
         && body >= InpMinBodyPts * point && approachFromBelow)
      {
         signal = -1;
      }
      // Rejection from below level → BUY (touched/went below level, closed back above)
      else if(low1 <= level && close1 > level && lowerWickRatio >= InpWickRatio
              && body >= InpMinBodyPts * point && approachFromAbove)
      {
         signal = 1;
      }
   }
   else  // BREAKOUT mode (momentum)
   {
      double bodyRatio = body / barRange;

      // Strong close above level → BUY momentum
      if(close1 > level && open1 < level && bodyRatio >= InpBrkBodyRatio
         && body >= atr[0] * InpBrkATRMult)
      {
         signal = 1;
      }
      // Strong close below level → SELL momentum
      else if(close1 < level && open1 > level && bodyRatio >= InpBrkBodyRatio
              && body >= atr[0] * InpBrkATRMult)
      {
         signal = -1;
      }
   }

   if(signal == 0) return;

   // Calculate SL/TP
   double slDist = atr[0] * InpATRMultSL;
   double price, sl, tp;

   if(signal == 1)
   {
      price = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
      sl    = NormalizeDouble(price - slDist, digits);
      tp    = NormalizeDouble(price + slDist * InpRR, digits);
   }
   else
   {
      price = SymbolInfoDouble(_Symbol, SYMBOL_BID);
      sl    = NormalizeDouble(price + slDist, digits);
      tp    = NormalizeDouble(price - slDist * InpRR, digits);
   }

   double slPoints = MathAbs(price - sl) / point;
   double lot = CalcLotSize(slPoints);
   if(lot <= 0) return;

   ENUM_ORDER_TYPE orderType = (signal == 1) ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
   string comment = StringFormat("RND|lvl=%.0f|d=%.0f|mode=%d", level, distToLevel, InpMode);

   bool ok = g_trade.PositionOpen(_Symbol, orderType, lot, price, sl, tp, comment);
   if(ok)
   {
      g_todayTrades++;
      PrintFormat("[GoldRound] %s %.2f @ %.2f SL=%.2f TP=%.2f Level=$%.0f Dist=%.0f",
                  signal == 1 ? "BUY" : "SELL", lot, price, sl, tp, level, distToLevel);
      LogSignal(barTime, signal == 1 ? "BUY" : "SELL", price, level, distToLevel,
                (InpMode == 0) ? MathMax(high1-MathMax(open1,close1), MathMin(open1,close1)-low1)/barRange : body/barRange,
                body, atr[0], sl, tp, lot, "EXECUTED");
   }
}

//+------------------------------------------------------------------+
void LogSignal(datetime time, string sig, double price, double level,
               double dist, double wickOrBodyRatio, double body,
               double atr, double sl, double tp, double lot, string reason)
{
   if(!InpDatalog || g_logHandle == INVALID_HANDLE) return;
   FileWrite(g_logHandle,
      TimeToString(time, TIME_DATE|TIME_MINUTES),
      sig, DoubleToString(price, 2),
      DoubleToString(level, 0), DoubleToString(dist, 0),
      DoubleToString(wickOrBodyRatio, 3), DoubleToString(body, 2),
      DoubleToString(atr, 2), DoubleToString(sl, 2), DoubleToString(tp, 2),
      DoubleToString(lot, 2), reason);
   FileFlush(g_logHandle);
}
//+------------------------------------------------------------------+
