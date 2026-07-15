//+------------------------------------------------------------------+
//| EA_EODRevert.mq5 — End-of-Day Mean Reversion                     |
//| Symbol: NSDQ+, SP+, DOW+ (index CFDs)                           |
//| Period: M15  |  Style: Mean Reversion (last-hour intraday)       |
//|                                                                   |
//| EDGE HYPOTHESIS (v1.0):                                           |
//| When equity indices decline >0.5% intraday by 3:00 PM ET,       |
//| there is a statistically significant reversal in the last hour    |
//| of trading (3:00-4:00 PM ET). The effect is driven by:           |
//| 1. Market-on-Close (MOC) buy imbalances from passive rebalancing |
//| 2. Short-covering before overnight risk                           |
//| 3. Portfolio manager day-end rebalancing                          |
//|                                                                   |
//| COUNTERPARTY: Intraday momentum traders who pushed price down    |
//| beyond fair value; they cover before close.                       |
//|                                                                   |
//| MECHANISM (NY Fed 2024): Last-hour flow is 3.41x predictive      |
//| ratio vs rest-of-day on S&P500.                                   |
//|                                                                   |
//| Max | 2026-04-11 | v1.0                                         |
//+------------------------------------------------------------------+
#property copyright "Max — EA_EODRevert v1.0"
#property version   "1.00"
#property strict

#include <Trade\Trade.mqh>

//+------------------------------------------------------------------+
//| Inputs                                                            |
//+------------------------------------------------------------------+
input group "=== General ==="
input ulong    InpMagic         = 401102;    // Magic Number
input int      InpDeviation     = 50;        // Max Slippage (pts)
input bool     InpKillSwitch    = false;     // Kill Switch

input group "=== Intraday Decline Detection ==="
input double   InpMinDeclinePct = 0.50;      // Min intraday decline (%) to trigger
input double   InpMaxDeclinePct = 3.00;      // Max decline (skip crash days)
input bool     InpFadeDownOnly  = true;      // Only fade down-days (BUY)
input bool     InpFadeUpOnly    = false;     // Also fade up-days (SELL for overextension)

input group "=== Session Timing (Server UTC+2/+3) ==="
input int      InpUSOpenH       = 16;        // US market open hour (~9:30 AM ET = h16 server)
input int      InpUSOpenM       = 30;        // US market open minute
input int      InpMeasureH      = 21;        // Measure decline at this hour (~3PM ET)
input int      InpMeasureM      = 0;
input int      InpEntryH        = 21;        // Entry hour (~3:00 PM ET)
input int      InpEntryM        = 15;        // Entry minute
input int      InpExitH         = 22;        // Exit hour (~4:00 PM ET close)
input int      InpExitM         = 55;        // Exit minute (5 min before close)

input group "=== Risk Management ==="
input double   InpRiskPct       = 0.50;      // Risk per trade (%)
input double   InpMaxLot        = 1.00;      // Max lot
input double   InpSL_Pct        = 0.30;      // SL as % of price (below entry)
input double   InpTP_Mode       = 0;         // 0=time exit (close at ExitH), 1=fixed R:R
input double   InpRR            = 1.5;       // Fixed R:R (if mode 1)
input double   InpDailyDDPct    = 3.0;       // Daily DD kill

input group "=== Volatility Filter ==="
input bool     InpUseVolFilter  = false;     // Enable ATR filter
input int      InpATRPeriod     = 14;        // ATR period
input double   InpMinATRMult    = 0.8;       // Min ATR vs 20-day avg (skip very quiet days)
input double   InpMaxATRMult    = 2.5;       // Max ATR (skip crash days)

input group "=== Day Filters ==="
input bool     InpTradeMon      = true;
input bool     InpTradeTue      = true;
input bool     InpTradeWed      = true;
input bool     InpTradeThu      = true;
input bool     InpTradeFri      = false;     // Skip Friday

input group "=== Datalog ==="
input bool     InpDatalog       = true;

//+------------------------------------------------------------------+
//| Globals                                                           |
//+------------------------------------------------------------------+
CTrade         g_trade;
int            g_hATR_D1;
datetime       g_lastBar;
datetime       g_todayDate;
double         g_dayStartBal;
bool           g_tradedToday;
double         g_dayOpenPrice;      // Today's session open
bool           g_dayOpenCaptured;
int            g_logHandle;

//+------------------------------------------------------------------+
int OnInit()
{
   if(InpKillSwitch) { Print("[EODRevert] Kill switch ON"); return INIT_SUCCEEDED; }

   g_trade.SetExpertMagicNumber(InpMagic);
   g_trade.SetDeviationInPoints(InpDeviation);
   g_trade.SetTypeFilling(ORDER_FILLING_FOK);

   g_hATR_D1 = iATR(_Symbol, PERIOD_D1, InpATRPeriod);
   if(g_hATR_D1 == INVALID_HANDLE)
   { Print("[EODRevert] FATAL: ATR handle failed"); return INIT_FAILED; }

   g_lastBar        = 0;
   g_todayDate      = 0;
   g_dayStartBal    = AccountInfoDouble(ACCOUNT_BALANCE);
   g_tradedToday    = false;
   g_dayOpenPrice   = 0;
   g_dayOpenCaptured = false;

   if(InpDatalog)
   {
      string fname = "EODRevert_datalog_" + _Symbol + ".csv";
      g_logHandle = FileOpen(fname, FILE_WRITE|FILE_CSV|FILE_COMMON, ',');
      if(g_logHandle != INVALID_HANDLE)
         FileWrite(g_logHandle,
            "Date","Direction","DeclinePct","DayOpen","MeasurePrice",
            "Signal","EntryPrice","SL","TP","Lot","ATR","SkipReason");
   }

   PrintFormat("[EODRevert] Init OK: %s %s MinDecline=%.2f%% MaxDecline=%.2f%%",
               _Symbol, EnumToString(_Period), InpMinDeclinePct, InpMaxDeclinePct);
   return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   if(g_hATR_D1 != INVALID_HANDLE) IndicatorRelease(g_hATR_D1);
   if(g_logHandle != INVALID_HANDLE) FileClose(g_logHandle);
}

//+------------------------------------------------------------------+
bool IsTradingDay(int dow)
{
   switch(dow)
   {
      case 1: return InpTradeMon; case 2: return InpTradeTue;
      case 3: return InpTradeWed; case 4: return InpTradeThu;
      case 5: return InpTradeFri; default: return false;
   }
}

//+------------------------------------------------------------------+
int CountMyPositions()
{
   int count = 0;
   for(int i = PositionsTotal()-1; i >= 0; i--)
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
void OnTick()
{
   if(InpKillSwitch) return;

   datetime barTime = iTime(_Symbol, PERIOD_CURRENT, 0);
   if(barTime == g_lastBar) return;
   g_lastBar = barTime;

   MqlDateTime dt;
   TimeToStruct(barTime, dt);
   int nowMins = dt.hour * 60 + dt.min;
   datetime today = StringToTime(StringFormat("%04d.%02d.%02d", dt.year, dt.mon, dt.day));

   //--- Day reset
   if(today != g_todayDate)
   {
      g_todayDate      = today;
      g_tradedToday    = false;
      g_dayStartBal    = AccountInfoDouble(ACCOUNT_BALANCE);
      g_dayOpenPrice   = 0;
      g_dayOpenCaptured = false;
   }

   //--- Capture US market open price (at InpUSOpenH:InpUSOpenM, NOT D1 midnight open)
   if(!g_dayOpenCaptured)
   {
      int usOpenMins = InpUSOpenH * 60 + InpUSOpenM;
      if(nowMins >= usOpenMins && nowMins < usOpenMins + 15)
      {
         double openPrice = iClose(_Symbol, PERIOD_CURRENT, 1); // closed bar at US open
         if(openPrice > 0)
         {
            g_dayOpenPrice = openPrice;
            g_dayOpenCaptured = true;
         }
      }
   }

   //--- Time exit on existing positions
   if(CountMyPositions() > 0)
   {
      if(dt.hour >= InpExitH && dt.min >= InpExitM)
      {
         for(int i = PositionsTotal()-1; i >= 0; i--)
         {
            ulong ticket = PositionGetTicket(i);
            if(ticket == 0) continue;
            if(PositionGetInteger(POSITION_MAGIC) != InpMagic) continue;
            if(PositionGetString(POSITION_SYMBOL) != _Symbol) continue;
            g_trade.PositionClose(ticket);
            Print("[EODRevert] Time exit");
         }
      }
      return;
   }

   if(g_tradedToday) return;
   if(g_dayOpenPrice <= 0) return;
   if(!IsTradingDay(dt.day_of_week)) return;

   //--- Check if it's measure time
   int measureMins = InpMeasureH * 60 + InpMeasureM;
   int entryMins = InpEntryH * 60 + InpEntryM;
   if(nowMins < entryMins || nowMins > entryMins + 15) return;

   //--- Measure intraday change
   double currentPrice = iClose(_Symbol, PERIOD_CURRENT, 1); // Closed bar
   double changePct = (currentPrice - g_dayOpenPrice) / g_dayOpenPrice * 100.0;

   //--- Determine signal
   int signal = 0;
   double absPct = MathAbs(changePct);

   if(changePct < -InpMinDeclinePct && changePct > -InpMaxDeclinePct && InpFadeDownOnly)
   {
      signal = 1; // BUY the dip (fade down-day)
   }
   else if(changePct > InpMinDeclinePct && changePct < InpMaxDeclinePct && InpFadeUpOnly)
   {
      signal = -1; // SELL the rip (fade up-day)
   }

   if(signal == 0) return;

   //--- Daily DD kill
   double ddPct = (g_dayStartBal > 0)
                  ? (g_dayStartBal - AccountInfoDouble(ACCOUNT_EQUITY)) / g_dayStartBal * 100.0
                  : 0;
   if(ddPct >= InpDailyDDPct)
   {
      LogData(today, signal, changePct, "SKIP", 0, 0, 0, 0, 0, "DD_KILL");
      g_tradedToday = true;
      return;
   }

   //--- Volatility filter
   if(InpUseVolFilter)
   {
      double atrArr[20];
      if(CopyBuffer(g_hATR_D1, 0, 1, 20, atrArr) < 20) return;

      double todayATR = atrArr[0];
      double avgATR = 0;
      for(int i = 0; i < 20; i++) avgATR += atrArr[i];
      avgATR /= 20.0;

      if(avgATR > 0)
      {
         double atrRatio = todayATR / avgATR;
         if(atrRatio < InpMinATRMult)
         {
            LogData(today, signal, changePct, "SKIP", 0, 0, 0, 0, todayATR, "LOW_VOL");
            g_tradedToday = true;
            return;
         }
         if(atrRatio > InpMaxATRMult)
         {
            LogData(today, signal, changePct, "SKIP", 0, 0, 0, 0, todayATR, "HIGH_VOL");
            g_tradedToday = true;
            return;
         }
      }
   }

   //--- Calculate SL/TP
   int digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
   double point = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   double price, sl, tp;

   if(signal == 1) // BUY
   {
      price = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
      sl = NormalizeDouble(price * (1.0 - InpSL_Pct / 100.0), digits);

      if(InpTP_Mode == 0)
         tp = 0; // Time exit — no TP
      else
         tp = NormalizeDouble(price + MathAbs(price - sl) * InpRR, digits);
   }
   else // SELL
   {
      price = SymbolInfoDouble(_Symbol, SYMBOL_BID);
      sl = NormalizeDouble(price * (1.0 + InpSL_Pct / 100.0), digits);

      if(InpTP_Mode == 0)
         tp = 0;
      else
         tp = NormalizeDouble(price - MathAbs(sl - price) * InpRR, digits);
   }

   double slPoints = MathAbs(price - sl) / point;
   double lot = CalcLotSize(slPoints);
   if(lot <= 0)
   {
      LogData(today, signal, changePct, "SKIP", price, sl, tp, 0, 0, "LOT_ZERO");
      g_tradedToday = true;
      return;
   }

   //--- Execute
   ENUM_ORDER_TYPE orderType = (signal == 1) ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
   string comment = StringFormat("EODRev|%.1f%%|%s", changePct, signal > 0 ? "BUY_DIP" : "SELL_RIP");

   bool ok = g_trade.PositionOpen(_Symbol, orderType, lot, price, sl, tp, comment);
   if(ok)
   {
      g_tradedToday = true;
      PrintFormat("[EODRevert] %s %.2f @ %.2f SL=%.2f Change=%.2f%%",
                  signal > 0 ? "BUY" : "SELL", lot, price, sl, changePct);
      LogData(today, signal, changePct, signal > 0 ? "BUY" : "SELL",
              price, sl, tp, lot, 0, "EXECUTED");
   }
}

//+------------------------------------------------------------------+
void LogData(datetime date, int dir, double pct, string sig,
             double price, double sl, double tp, double lot,
             double atr, string reason)
{
   if(!InpDatalog || g_logHandle == INVALID_HANDLE) return;
   FileWrite(g_logHandle,
      TimeToString(date, TIME_DATE),
      dir > 0 ? "UP_FADE" : "DN_FADE",
      DoubleToString(pct, 3),
      DoubleToString(g_dayOpenPrice, 2),
      DoubleToString(iClose(_Symbol, PERIOD_CURRENT, 0), 2),
      sig,
      DoubleToString(price, 2),
      DoubleToString(sl, 2),
      DoubleToString(tp, 2),
      DoubleToString(lot, 2),
      DoubleToString(atr, 2),
      reason);
   FileFlush(g_logHandle);
}
//+------------------------------------------------------------------+
