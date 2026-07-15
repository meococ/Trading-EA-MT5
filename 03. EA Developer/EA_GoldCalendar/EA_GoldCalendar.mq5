//+------------------------------------------------------------------+
//| EA_GoldCalendar.mq5 — Gold Calendar Anomaly Composite            |
//| Symbol: XAUUSD  |  Period: M15  |  Style: Calendar + Momentum    |
//|                                                                   |
//| EDGE HYPOTHESIS (v1.0):                                           |
//| Gold exhibits measurable Day-of-Week bias (Friday +55.85%         |
//| upward probability, 17yr data, OOS confirming) AND Turn-of-Month  |
//| effect (Day -1/0/+1 avg +0.34%) driven by:                       |
//|   1. Institutional position squaring pre-weekend (Friday)         |
//|   2. Pension/ETF new-month capital deployment (ToM)               |
//|                                                                   |
//| MECHANISM:                                                        |
//| Institutional rebalancing + hedging is MANDATORY and              |
//| price-insensitive. Retail traders on the other side provide       |
//| counterparty (panic Mon, FOMO Fri). We join institutional flow    |
//| direction during London-NY overlap for maximum liquidity.         |
//|                                                                   |
//| COUNTERPARTY: Retail Monday sellers (fear), retail stop-outs      |
//|                                                                   |
//| DESIGN:                                                           |
//| - Signals on bar[1] ONLY (no repaint)                            |
//| - LONG bias only (structural gold upward drift filtered by DoW)  |
//| - Entry: London-NY overlap, Wed/Thu/Fri + ToM days               |
//| - EMA(50) trend confirm (bar[1] above EMA = uptrend)             |
//| - Hard SL: 2xATR below entry                                     |
//| - TP: 2.5R (reward:risk) or next session close                   |
//| - Break-even at 1R                                                |
//| - Max 1 trade per day                                             |
//|                                                                   |
//| Max | 2026-04-05 | v1.0                                         |
//+------------------------------------------------------------------+
#property copyright "Max — EA_GoldCalendar v1.0"
#property version   "1.00"
#property strict

#include <Trade\Trade.mqh>

//+------------------------------------------------------------------+
//| Input Parameters                                                  |
//+------------------------------------------------------------------+
input group "=== General ==="
input ulong    InpMagic         = 402601;    // Magic Number
input int      InpDeviation     = 30;        // Max Slippage (pts)
input bool     InpKillSwitch    = false;     // Kill Switch

input group "=== Calendar Filters ==="
input bool     InpMonday        = false;     // Trade Monday
input bool     InpTuesday       = false;     // Trade Tuesday
input bool     InpWednesday     = true;      // Trade Wednesday
input bool     InpThursday      = true;      // Trade Thursday
input bool     InpFriday        = true;      // Trade Friday
input bool     InpUseToM        = true;      // Enable Turn-of-Month boost
input int      InpToMDaysBefore = 1;         // ToM: trade N days before month end
input int      InpToMDaysAfter  = 2;         // ToM: trade N days after month start

input group "=== Session Filter (Server Time) ==="
input int      InpEntryStart    = 10;        // Entry window start (server hr)
input int      InpEntryEnd      = 17;        // Entry window end (server hr)

input group "=== Trend Filter ==="
input int      InpEMAPeriod     = 50;        // EMA trend filter period
input bool     InpRequireUptrend= true;      // Require price above EMA (long only)

input group "=== Entry Trigger ==="
input int      InpRSIPeriod     = 14;        // RSI for entry timing
input int      InpRSIEntry      = 55;        // RSI below this = dip entry (pullback in uptrend)

input group "=== Risk Management ==="
input double   InpRiskPct       = 0.50;      // Risk per trade (%)
input double   InpMaxLot        = 0.50;      // Max lot
input int      InpMaxPerDay     = 1;         // Max trades per day
input double   InpATRMultSL     = 2.0;       // SL = ATR x this
input int      InpATRPeriod     = 14;        // ATR Period
input double   InpRR            = 2.5;       // Reward:Risk ratio for TP
input bool     InpUseBE         = true;      // Move SL to BE at 1R
input double   InpDailyDDPct    = 3.0;       // Daily DD kill (%)

input group "=== Position Management ==="
input int      InpFridayClose   = 20;        // Friday close-all hour (server)
input bool     InpCloseEOD      = false;     // Close at end of entry window

input group "=== Datalog ==="
input bool     InpDatalog       = true;      // Enable CSV signal log

//+------------------------------------------------------------------+
//| Globals                                                           |
//+------------------------------------------------------------------+
CTrade         g_trade;
int            g_hEMA;
int            g_hRSI;
int            g_hATR;
datetime       g_lastBar;
int            g_todayTrades;
datetime       g_todayDate;
double         g_dayStartBal;
int            g_logHandle;

//+------------------------------------------------------------------+
//| Expert initialization                                             |
//+------------------------------------------------------------------+
int OnInit()
{
   if(InpKillSwitch)
   {
      Print("[GoldCal] Kill switch ON");
      return INIT_SUCCEEDED;
   }

   g_trade.SetExpertMagicNumber(InpMagic);
   g_trade.SetDeviationInPoints(InpDeviation);
   g_trade.SetTypeFilling(ORDER_FILLING_FOK);

   g_hEMA = iMA(_Symbol, PERIOD_CURRENT, InpEMAPeriod, 0, MODE_EMA, PRICE_CLOSE);
   g_hRSI = iRSI(_Symbol, PERIOD_CURRENT, InpRSIPeriod, PRICE_CLOSE);
   g_hATR = iATR(_Symbol, PERIOD_CURRENT, InpATRPeriod);

   if(g_hEMA == INVALID_HANDLE || g_hRSI == INVALID_HANDLE || g_hATR == INVALID_HANDLE)
   {
      Print("[GoldCal] FATAL: Indicator init failed");
      return INIT_FAILED;
   }

   g_lastBar     = 0;
   g_todayTrades = 0;
   g_todayDate   = 0;
   g_dayStartBal = AccountInfoDouble(ACCOUNT_BALANCE);

   if(InpDatalog)
   {
      string fname = "GoldCalendar_datalog_" + _Symbol + ".csv";
      g_logHandle = FileOpen(fname, FILE_WRITE|FILE_CSV|FILE_COMMON, ',');
      if(g_logHandle != INVALID_HANDLE)
         FileWrite(g_logHandle,
            "Time","Signal","Price","EMA","RSI","ATR","SL","TP","Lot",
            "DoW","IsToM","SkipReason");
   }

   PrintFormat("[GoldCal] Init OK: %s %s Magic=%d", _Symbol, EnumToString(_Period), InpMagic);
   return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   if(g_hEMA != INVALID_HANDLE) IndicatorRelease(g_hEMA);
   if(g_hRSI != INVALID_HANDLE) IndicatorRelease(g_hRSI);
   if(g_hATR != INVALID_HANDLE) IndicatorRelease(g_hATR);
   if(g_logHandle != INVALID_HANDLE) FileClose(g_logHandle);
}

//+------------------------------------------------------------------+
//| Check if today is a Turn-of-Month day                            |
//+------------------------------------------------------------------+
bool IsToMDay(const MqlDateTime &dt)
{
   if(!InpUseToM) return false;

   // Days after month start
   if(dt.day <= InpToMDaysAfter) return true;

   // Days before month end — need to know last day of month
   int daysInMonth = 31;
   if(dt.mon == 2)
      daysInMonth = (dt.year % 4 == 0 && (dt.year % 100 != 0 || dt.year % 400 == 0)) ? 29 : 28;
   else if(dt.mon == 4 || dt.mon == 6 || dt.mon == 9 || dt.mon == 11)
      daysInMonth = 30;

   if(dt.day >= daysInMonth - InpToMDaysBefore) return true;

   return false;
}

//+------------------------------------------------------------------+
//| Check if today's DoW is allowed for trading                      |
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
//| Count my positions                                                |
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
//| Lot sizing                                                        |
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

   // Manage existing positions
   ManagePositions(dt);

   // Daily DD kill
   double ddPct = (g_dayStartBal > 0)
                  ? (g_dayStartBal - AccountInfoDouble(ACCOUNT_EQUITY)) / g_dayStartBal * 100.0
                  : 0;
   if(ddPct >= InpDailyDDPct) return;

   // Already traded today?
   if(g_todayTrades >= InpMaxPerDay) return;

   // Already have position?
   if(CountMyPositions() > 0) return;

   // Session window
   if(dt.hour < InpEntryStart || dt.hour >= InpEntryEnd) return;

   // Calendar filter: DoW OR ToM
   bool isDowOk = IsTradingDay(dt.day_of_week);
   bool isTom   = IsToMDay(dt);

   if(!isDowOk && !isTom)
   {
      // Neither DoW nor ToM day — skip
      return;
   }

   // Read indicators bar[1]
   double ema[], rsi[], atr[];
   if(CopyBuffer(g_hEMA, 0, 1, 1, ema) < 1) return;
   if(CopyBuffer(g_hRSI, 0, 1, 1, rsi) < 1) return;
   if(CopyBuffer(g_hATR, 0, 1, 1, atr) < 1) return;

   double close1 = iClose(_Symbol, PERIOD_CURRENT, 1);
   int    digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
   double point  = SymbolInfoDouble(_Symbol, SYMBOL_POINT);

   // Trend filter: price above EMA (uptrend for long-only)
   string skipReason = "";
   if(InpRequireUptrend && close1 < ema[0])
   {
      skipReason = "DOWNTREND";
      LogSignal(barTime, "SKIP", close1, ema[0], rsi[0], atr[0], 0, 0, 0,
                dt.day_of_week, isTom, skipReason);
      return;
   }

   // Entry trigger: RSI dip in uptrend (buying the dip on institutional flow day)
   if(rsi[0] > InpRSIEntry)
   {
      // No dip yet — wait for pullback
      return;
   }

   // Calculate SL/TP
   double slDist = atr[0] * InpATRMultSL;
   double price  = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double sl     = NormalizeDouble(price - slDist, digits);
   double tp     = NormalizeDouble(price + slDist * InpRR, digits);

   // Lot size
   double slPoints = MathAbs(price - sl) / point;
   double lot = CalcLotSize(slPoints);
   if(lot <= 0)
   {
      LogSignal(barTime, "SKIP", close1, ema[0], rsi[0], atr[0], sl, tp, 0,
                dt.day_of_week, isTom, "LOT_ZERO");
      return;
   }

   // Execute BUY (long-only strategy)
   string comment = StringFormat("GCal|DoW=%d|ToM=%d|RSI=%.0f", dt.day_of_week, isTom ? 1 : 0, rsi[0]);
   bool ok = g_trade.PositionOpen(_Symbol, ORDER_TYPE_BUY, lot, price, sl, tp, comment);
   if(ok)
   {
      g_todayTrades++;
      PrintFormat("[GoldCal] BUY %.2f @ %.2f SL=%.2f TP=%.2f DoW=%d ToM=%s RSI=%.1f",
                  lot, price, sl, tp, dt.day_of_week, isTom ? "YES" : "no", rsi[0]);
      LogSignal(barTime, "BUY", price, ema[0], rsi[0], atr[0], sl, tp, lot,
                dt.day_of_week, isTom, "EXECUTED");
   }
}

//+------------------------------------------------------------------+
void ManagePositions(const MqlDateTime &dt)
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0) continue;
      if(PositionGetInteger(POSITION_MAGIC) != InpMagic) continue;
      if(PositionGetString(POSITION_SYMBOL) != _Symbol) continue;

      double openPrice = PositionGetDouble(POSITION_PRICE_OPEN);
      double sl        = PositionGetDouble(POSITION_SL);
      double tp        = PositionGetDouble(POSITION_TP);
      double bid       = SymbolInfoDouble(_Symbol, SYMBOL_BID);

      // Friday flatten
      if(dt.day_of_week == 5 && dt.hour >= InpFridayClose)
      {
         g_trade.PositionClose(ticket);
         continue;
      }

      // EOD close
      if(InpCloseEOD && dt.hour >= InpEntryEnd)
      {
         g_trade.PositionClose(ticket);
         continue;
      }

      // Break-even at 1R
      if(InpUseBE)
      {
         double slDist = MathAbs(openPrice - sl);
         if(bid >= openPrice + slDist && sl < openPrice)
         {
            double newSL = openPrice + SymbolInfoDouble(_Symbol, SYMBOL_POINT);
            g_trade.PositionModify(ticket, newSL, tp);
         }
      }
   }
}

//+------------------------------------------------------------------+
void LogSignal(datetime time, string signal, double price,
               double ema, double rsi, double atr,
               double sl, double tp, double lot,
               int dow, bool isTom, string reason)
{
   if(!InpDatalog || g_logHandle == INVALID_HANDLE) return;
   FileWrite(g_logHandle,
      TimeToString(time, TIME_DATE|TIME_MINUTES),
      signal, DoubleToString(price, 2),
      DoubleToString(ema, 2), DoubleToString(rsi, 1), DoubleToString(atr, 2),
      DoubleToString(sl, 2), DoubleToString(tp, 2), DoubleToString(lot, 2),
      IntegerToString(dow), isTom ? "1" : "0", reason);
   FileFlush(g_logHandle);
}
//+------------------------------------------------------------------+
