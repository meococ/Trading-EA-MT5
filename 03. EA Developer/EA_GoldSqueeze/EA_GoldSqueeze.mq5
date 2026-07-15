//+------------------------------------------------------------------+
//| EA_GoldSqueeze.mq5 — Gold Volatility Squeeze Breakout (M15)      |
//| Symbol: XAUUSD  |  Period: M15  |  Style: Squeeze→Expansion     |
//|                                                                   |
//| EDGE HYPOTHESIS (v1.0):                                           |
//| Gold alternates quiet/volatile regimes. When Bollinger Bands      |
//| contract INSIDE Keltner Channel (squeeze), volatility is          |
//| compressed. First breakout outside both = expansion trade.        |
//|                                                                   |
//| MECHANISM:                                                        |
//| Squeeze = market indecision, stops clustering outside range.      |
//| Breakout triggers stops, creating momentum cascade.               |
//| Gold's volatility clustering makes squeezes predictive.           |
//|                                                                   |
//| SOURCE: MQL5 quant community, John Carter TTM Squeeze concept    |
//|                                                                   |
//| Max | 2026-04-05 | v1.0                                         |
//+------------------------------------------------------------------+
#property copyright "Max — EA_GoldSqueeze v1.0"
#property version   "1.00"
#property strict

#include <Trade\Trade.mqh>

//+------------------------------------------------------------------+
input group "=== General ==="
input ulong    InpMagic         = 802601;    // Magic Number
input int      InpDeviation     = 50;        // Max Slippage (pts)
input bool     InpKillSwitch    = false;     // Kill Switch

input group "=== Bollinger Bands ==="
input int      InpBBPeriod      = 20;        // BB Period
input double   InpBBDev         = 2.0;       // BB Deviation

input group "=== Keltner Channel ==="
input int      InpKCPeriod      = 20;        // KC Period (EMA)
input double   InpKCMult        = 1.5;       // KC ATR Multiplier
input int      InpKCATRPeriod   = 14;        // KC ATR Period

input group "=== Squeeze Detection ==="
input int      InpMinSqueezeBars= 4;         // Min bars in squeeze (4 = 1 hour)
input int      InpMaxSqueezeBars= 40;        // Max bars in squeeze (40 = 10 hours)

input group "=== Session Filter (Server Time) ==="
input int      InpStartHour     = 9;         // Entry start hour (London open)
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
input int      InpATRPeriod     = 14;        // ATR Period for SL
input double   InpRR            = 2.0;       // Reward:Risk
input bool     InpUseBE         = true;      // Move SL to BE at 1R
input int      InpMaxPerDay     = 2;         // Max trades per day
input double   InpDailyDDPct    = 3.0;       // Daily DD kill (%)

input group "=== Datalog ==="
input bool     InpDatalog       = true;      // Enable CSV signal log

//+------------------------------------------------------------------+
CTrade         g_trade;
int            g_hBBUpper, g_hBBLower, g_hBBMid;
int            g_hKCEMA;
int            g_hKCATR;
int            g_hATR;
datetime       g_lastBar;
int            g_squeezeBars;  // consecutive bars in squeeze
bool           g_wasSqueeze;   // previous bar was in squeeze
int            g_todayTrades;
datetime       g_todayDate;
double         g_dayStartBal;
int            g_logHandle;

//+------------------------------------------------------------------+
int OnInit()
{
   if(InpKillSwitch) { Print("[GoldSqueeze] Kill switch ON"); return INIT_SUCCEEDED; }

   g_trade.SetExpertMagicNumber(InpMagic);
   g_trade.SetDeviationInPoints(InpDeviation);
   g_trade.SetTypeFilling(ORDER_FILLING_FOK);

   // Bollinger Bands
   g_hBBUpper = iBands(_Symbol, PERIOD_CURRENT, InpBBPeriod, 0, InpBBDev, PRICE_CLOSE);
   // Keltner Channel: EMA + ATR
   g_hKCEMA = iMA(_Symbol, PERIOD_CURRENT, InpKCPeriod, 0, MODE_EMA, PRICE_CLOSE);
   g_hKCATR = iATR(_Symbol, PERIOD_CURRENT, InpKCATRPeriod);
   // ATR for SL
   g_hATR = iATR(_Symbol, PERIOD_CURRENT, InpATRPeriod);

   if(g_hBBUpper == INVALID_HANDLE || g_hKCEMA == INVALID_HANDLE ||
      g_hKCATR == INVALID_HANDLE || g_hATR == INVALID_HANDLE)
   { Print("[GoldSqueeze] FATAL: Indicator init failed"); return INIT_FAILED; }

   g_lastBar      = 0;
   g_squeezeBars  = 0;
   g_wasSqueeze   = false;
   g_todayTrades  = 0;
   g_todayDate    = 0;
   g_dayStartBal  = AccountInfoDouble(ACCOUNT_BALANCE);

   if(InpDatalog)
   {
      string fname = "GoldSqueeze_datalog_" + _Symbol + ".csv";
      g_logHandle = FileOpen(fname, FILE_WRITE|FILE_CSV|FILE_COMMON, ',');
      if(g_logHandle != INVALID_HANDLE)
         FileWrite(g_logHandle,
            "Time","Signal","Price","BBUpper","BBLower","KCUpper","KCLower",
            "SqueezeBars","ATR","SL","TP","Lot","SkipReason");
   }

   PrintFormat("[GoldSqueeze] Init OK: %s BB(%d,%.1f) KC(%d,%.1f)",
               _Symbol, InpBBPeriod, InpBBDev, InpKCPeriod, InpKCMult);
   return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   if(g_hBBUpper != INVALID_HANDLE) IndicatorRelease(g_hBBUpper);
   if(g_hKCEMA != INVALID_HANDLE)   IndicatorRelease(g_hKCEMA);
   if(g_hKCATR != INVALID_HANDLE)   IndicatorRelease(g_hKCATR);
   if(g_hATR != INVALID_HANDLE)     IndicatorRelease(g_hATR);
   if(g_logHandle != INVALID_HANDLE) FileClose(g_logHandle);
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

   // Read indicators on bar[1] (non-repaint)
   double bbUpper[], bbLower[];
   double kcEMA[], kcATR[];
   double atr[];

   // BB: buffer 1 = upper, buffer 2 = lower
   if(CopyBuffer(g_hBBUpper, 1, 1, 1, bbUpper) < 1) return;
   if(CopyBuffer(g_hBBUpper, 2, 1, 1, bbLower) < 1) return;
   if(CopyBuffer(g_hKCEMA, 0, 1, 1, kcEMA) < 1) return;
   if(CopyBuffer(g_hKCATR, 0, 1, 1, kcATR) < 1) return;
   if(CopyBuffer(g_hATR, 0, 1, 1, atr) < 1) return;

   // Keltner Channel boundaries
   double kcUpper = kcEMA[0] + InpKCMult * kcATR[0];
   double kcLower = kcEMA[0] - InpKCMult * kcATR[0];

   // Squeeze detection: BB inside KC
   bool isSqueeze = (bbUpper[0] < kcUpper && bbLower[0] > kcLower);

   if(isSqueeze)
   {
      g_squeezeBars++;
   }
   else
   {
      // Was in squeeze, now released → potential signal
      if(g_wasSqueeze && g_squeezeBars >= InpMinSqueezeBars
         && g_squeezeBars <= InpMaxSqueezeBars)
      {
         // Squeeze released! Check for breakout on bar[1]
         double close1 = iClose(_Symbol, PERIOD_CURRENT, 1);
         int    digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
         double point  = SymbolInfoDouble(_Symbol, SYMBOL_POINT);

         // Session + day filter
         if(!IsTradingDay(dt.day_of_week) ||
            dt.hour < InpStartHour || dt.hour >= InpEndHour ||
            g_todayTrades >= InpMaxPerDay)
         {
            LogSignal(barTime, "SKIP", close1, bbUpper[0], bbLower[0],
                      kcUpper, kcLower, g_squeezeBars, atr[0], 0, 0, 0, "SESSION_FILTER");
            g_squeezeBars = 0;
            g_wasSqueeze  = false;
            return;
         }

         // Daily DD kill
         double ddPct = (g_dayStartBal > 0)
                        ? (g_dayStartBal - AccountInfoDouble(ACCOUNT_EQUITY)) / g_dayStartBal * 100.0
                        : 0;
         if(ddPct >= InpDailyDDPct)
         {
            g_squeezeBars = 0;
            g_wasSqueeze  = false;
            return;
         }

         // Determine direction: where did price close relative to KC center?
         int signal = 0;
         if(close1 > kcUpper) signal = 1;       // Breakout UP
         else if(close1 < kcLower) signal = -1;  // Breakout DOWN

         if(signal != 0)
         {
            double price, sl, tp;
            double slDist = atr[0] * InpATRMultSL;

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
            if(lot <= 0)
            {
               LogSignal(barTime, "SKIP", close1, bbUpper[0], bbLower[0],
                         kcUpper, kcLower, g_squeezeBars, atr[0], sl, tp, 0, "LOT_ZERO");
               g_squeezeBars = 0;
               g_wasSqueeze  = false;
               return;
            }

            ENUM_ORDER_TYPE orderType = (signal == 1) ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
            string comment = StringFormat("SQZ|bars=%d|dir=%d", g_squeezeBars, signal);

            bool ok = g_trade.PositionOpen(_Symbol, orderType, lot, price, sl, tp, comment);
            if(ok)
            {
               g_todayTrades++;
               PrintFormat("[GoldSqueeze] %s %.2f @ %.2f SL=%.2f TP=%.2f SqueezeBars=%d",
                           signal == 1 ? "BUY" : "SELL", lot, price, sl, tp, g_squeezeBars);
               LogSignal(barTime, signal == 1 ? "BUY" : "SELL", close1,
                         bbUpper[0], bbLower[0], kcUpper, kcLower,
                         g_squeezeBars, atr[0], sl, tp, lot, "EXECUTED");
            }
         }
      }
      g_squeezeBars = 0;
   }

   g_wasSqueeze = isSqueeze;
}

//+------------------------------------------------------------------+
void LogSignal(datetime time, string sig, double price,
               double bbU, double bbL, double kcU, double kcL,
               int sqzBars, double atr, double sl, double tp,
               double lot, string reason)
{
   if(!InpDatalog || g_logHandle == INVALID_HANDLE) return;
   FileWrite(g_logHandle,
      TimeToString(time, TIME_DATE|TIME_MINUTES),
      sig, DoubleToString(price, 2),
      DoubleToString(bbU, 2), DoubleToString(bbL, 2),
      DoubleToString(kcU, 2), DoubleToString(kcL, 2),
      IntegerToString(sqzBars), DoubleToString(atr, 2),
      DoubleToString(sl, 2), DoubleToString(tp, 2),
      DoubleToString(lot, 2), reason);
   FileFlush(g_logHandle);
}
//+------------------------------------------------------------------+
