//+------------------------------------------------------------------+
//| EA_NAS100MR.mq5 — NAS100 Mean Reversion Scalper                 |
//| Symbol: USTEC (NAS100)  |  Period: M15  |  Style: Mean Reversion |
//|                                                                   |
//| EDGE HYPOTHESIS (v1.0):                                           |
//| NAS100 exhibits strong mean-reversion during non-trending         |
//| regimes. Entry when price deviates >2 sigma from mean, confirmed  |
//| by RSI extreme + ADX below threshold (no trend).                  |
//|                                                                   |
//| MECHANISM:                                                        |
//| Retail traders panic during intraday dips/spikes. Institutions    |
//| provide liquidity at extremes and fade the move. We join the      |
//| institutional side when statistical extremes align with trend     |
//| absence (ADX filter).                                             |
//|                                                                   |
//| COUNTERPARTY: Panic retail + momentum algo stop-outs              |
//|                                                                   |
//| DESIGN:                                                           |
//| - Signals on bar[1] ONLY (no repaint)                            |
//| - Hard SL on every trade (2xATR or fixed pts)                    |
//| - BB(30,2) + RSI(13) confirmation                                |
//| - ADX(14) < 25 filter (suppress trend periods)                   |
//| - NY session only (15:30-21:00 server = 9:30-15:00 ET)           |
//| - TP at middle BB (mean reversion target)                         |
//| - Max 2 trades per day                                            |
//|                                                                   |
//| Max | 2026-04-05 | v1.0                                         |
//+------------------------------------------------------------------+
#property copyright "Max — EA_NAS100MR v1.0"
#property version   "1.00"
#property strict

#include <Trade\Trade.mqh>
#include <Trade\PositionInfo.mqh>

//+------------------------------------------------------------------+
//| Input Parameters                                                  |
//+------------------------------------------------------------------+
input group "=== General ==="
input ulong    InpMagic         = 302601;    // Magic Number
input int      InpDeviation     = 50;        // Max Slippage (pts)
input bool     InpKillSwitch    = false;     // Kill Switch

input group "=== Session Filter (Server Time) ==="
input int      InpSessionStart  = 15;        // NY Session Start (server hr)
input int      InpSessionEnd    = 21;        // NY Session End (server hr)
input bool     InpSkipFriday    = true;      // Skip Friday (avoid weekend gap)

input group "=== Mean Reversion Parameters ==="
input int      InpBBPeriod      = 20;        // Bollinger Band Period
input double   InpBBDev         = 2.0;       // BB Deviation Multiplier
input int      InpRSIPeriod     = 14;        // RSI Period
input int      InpRSIOversold   = 30;        // RSI Oversold threshold (long)
input int      InpRSIOverbought = 70;        // RSI Overbought threshold (short)
input int      InpADXPeriod     = 14;        // ADX Period
input int      InpADXThreshold  = 30;        // ADX Max (above = trending, skip)

input group "=== Risk Management ==="
input double   InpRiskPct       = 0.50;      // Risk per trade (%)
input double   InpMaxLot        = 1.00;      // Max lot
input int      InpMaxPerDay     = 4;         // Max trades per day
input int      InpMaxOpen       = 1;         // Max simultaneous positions
input double   InpATRMultSL     = 2.0;       // SL = ATR x this
input int      InpATRPeriod     = 14;        // ATR Period
input double   InpDailyDDPct    = 3.0;       // Daily DD kill (%)

input group "=== Exit ==="
input bool     InpUseBBExit     = true;      // Exit at middle BB (mean)
input double   InpFixedRR       = 0.0;       // Fixed R:R (0=use BB exit)
input bool     InpUseBE         = true;      // Move SL to BE at 1R
input int      InpFridayClose   = 20;        // Friday close-all hour

input group "=== Datalog ==="
input bool     InpDatalog       = true;      // Enable CSV signal log

//+------------------------------------------------------------------+
//| Globals                                                           |
//+------------------------------------------------------------------+
CTrade         g_trade;
int            g_hBB;           // Bollinger Bands handle
int            g_hRSI;          // RSI handle
int            g_hADX;          // ADX handle
int            g_hATR;          // ATR handle
datetime       g_lastBar;       // Last processed bar
int            g_todayTrades;   // Trades taken today
datetime       g_todayDate;     // Current day tracker
double         g_dayStartBal;   // Balance at day start
int            g_logHandle;     // Datalog file handle

//+------------------------------------------------------------------+
//| Expert initialization                                             |
//+------------------------------------------------------------------+
int OnInit()
{
   if(InpKillSwitch)
   {
      Print("[NAS100MR] Kill switch ON — disabled");
      return INIT_SUCCEEDED;
   }

   // Init trade object
   g_trade.SetExpertMagicNumber(InpMagic);
   g_trade.SetDeviationInPoints(InpDeviation);
   g_trade.SetTypeFilling(ORDER_FILLING_FOK);

   // Create indicator handles
   g_hBB  = iBands(_Symbol, PERIOD_CURRENT, InpBBPeriod, 0, InpBBDev, PRICE_CLOSE);
   g_hRSI = iRSI(_Symbol, PERIOD_CURRENT, InpRSIPeriod, PRICE_CLOSE);
   g_hADX = iADX(_Symbol, PERIOD_CURRENT, InpADXPeriod);
   g_hATR = iATR(_Symbol, PERIOD_CURRENT, InpATRPeriod);

   if(g_hBB == INVALID_HANDLE || g_hRSI == INVALID_HANDLE ||
      g_hADX == INVALID_HANDLE || g_hATR == INVALID_HANDLE)
   {
      Print("[NAS100MR] FATAL: Indicator creation failed");
      return INIT_FAILED;
   }

   g_lastBar      = 0;
   g_todayTrades  = 0;
   g_todayDate    = 0;
   g_dayStartBal  = AccountInfoDouble(ACCOUNT_BALANCE);

   // Init datalog
   if(InpDatalog)
   {
      string fname = "NAS100MR_datalog_" + _Symbol + ".csv";
      g_logHandle = FileOpen(fname, FILE_WRITE|FILE_CSV|FILE_COMMON, ',');
      if(g_logHandle != INVALID_HANDLE)
      {
         FileWrite(g_logHandle,
            "Time","Signal","Price","BB_Upper","BB_Mid","BB_Lower",
            "RSI","ADX","ATR","SL","TP","Lot","SkipReason");
      }
   }

   PrintFormat("[NAS100MR] Init OK on %s %s, Magic=%d",
               _Symbol, EnumToString(_Period), InpMagic);
   return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
//| Expert deinitialization                                           |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   if(g_hBB  != INVALID_HANDLE) IndicatorRelease(g_hBB);
   if(g_hRSI != INVALID_HANDLE) IndicatorRelease(g_hRSI);
   if(g_hADX != INVALID_HANDLE) IndicatorRelease(g_hADX);
   if(g_hATR != INVALID_HANDLE) IndicatorRelease(g_hATR);
   if(g_logHandle != INVALID_HANDLE) FileClose(g_logHandle);
}

//+------------------------------------------------------------------+
//| Expert tick function                                              |
//+------------------------------------------------------------------+
void OnTick()
{
   if(InpKillSwitch) return;

   //--- New bar detection (bar[1] only — no repaint)
   datetime barTime = iTime(_Symbol, PERIOD_CURRENT, 0);
   if(barTime == g_lastBar) return;
   g_lastBar = barTime;

   //--- Day tracking
   MqlDateTime dt;
   TimeToStruct(barTime, dt);
   datetime today = StringToTime(StringFormat("%04d.%02d.%02d", dt.year, dt.mon, dt.day));
   if(today != g_todayDate)
   {
      g_todayDate    = today;
      g_todayTrades  = 0;
      g_dayStartBal  = AccountInfoDouble(ACCOUNT_BALANCE);
   }

   //--- Manage existing positions (BE, BB exit, Friday close)
   ManagePositions(dt);

   //--- Daily DD kill
   double curBal = AccountInfoDouble(ACCOUNT_BALANCE);
   double curEq  = AccountInfoDouble(ACCOUNT_EQUITY);
   double ddPct  = (g_dayStartBal > 0) ? (g_dayStartBal - curEq) / g_dayStartBal * 100.0 : 0;
   if(ddPct >= InpDailyDDPct)
   {
      // Already hit daily DD limit — no new trades
      return;
   }

   //--- Skip Friday if configured
   if(InpSkipFriday && dt.day_of_week == 5) return;

   //--- Session filter
   if(dt.hour < InpSessionStart || dt.hour >= InpSessionEnd) return;

   //--- Max trades per day
   if(g_todayTrades >= InpMaxPerDay) return;

   //--- Max open positions
   if(CountMyPositions() >= InpMaxOpen) return;

   //--- Read indicators on bar[1]
   double bbUpper[], bbMid[], bbLower[], rsi[], adxMain[], atr[];
   if(CopyBuffer(g_hBB,  1, 1, 1, bbUpper)  < 1) return;  // Upper band
   if(CopyBuffer(g_hBB,  0, 1, 1, bbMid)    < 1) return;  // Middle band
   if(CopyBuffer(g_hBB,  2, 1, 1, bbLower)  < 1) return;  // Lower band
   if(CopyBuffer(g_hRSI, 0, 1, 1, rsi)      < 1) return;
   if(CopyBuffer(g_hADX, 0, 1, 1, adxMain)  < 1) return;  // Main ADX line
   if(CopyBuffer(g_hATR, 0, 1, 1, atr)      < 1) return;

   double close1 = iClose(_Symbol, PERIOD_CURRENT, 1);

   //--- ADX filter: skip if trending
   string skipReason = "";
   if(adxMain[0] >= InpADXThreshold)
   {
      skipReason = "ADX_TRENDING";
      LogSignal(barTime, "SKIP", close1, bbUpper[0], bbMid[0], bbLower[0],
                rsi[0], adxMain[0], atr[0], 0, 0, 0, skipReason);
      return;
   }

   //--- Signal detection
   int signal = 0;  // 1=long, -1=short
   if(close1 < bbLower[0] && rsi[0] < InpRSIOversold)
      signal = 1;   // Price below lower BB + RSI oversold → BUY
   else if(close1 > bbUpper[0] && rsi[0] > InpRSIOverbought)
      signal = -1;  // Price above upper BB + RSI overbought → SELL

   if(signal == 0) return;  // No signal

   //--- Calculate SL/TP
   double atrVal   = atr[0];
   double point    = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   int    digits   = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
   double tickSize = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   double tickVal  = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);

   double slDist = atrVal * InpATRMultSL;
   double sl, tp;
   double price;

   if(signal == 1) // LONG
   {
      price = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
      sl    = NormalizeDouble(price - slDist, digits);
      tp    = InpUseBBExit ? NormalizeDouble(bbMid[0], digits)
                           : (InpFixedRR > 0 ? NormalizeDouble(price + slDist * InpFixedRR, digits) : 0);
   }
   else // SHORT
   {
      price = SymbolInfoDouble(_Symbol, SYMBOL_BID);
      sl    = NormalizeDouble(price + slDist, digits);
      tp    = InpUseBBExit ? NormalizeDouble(bbMid[0], digits)
                           : (InpFixedRR > 0 ? NormalizeDouble(price - slDist * InpFixedRR, digits) : 0);
   }

   //--- Validate TP makes sense (TP must be in profit direction)
   if(signal == 1 && tp > 0 && tp <= price)
   {
      skipReason = "TP_BELOW_ENTRY";
      LogSignal(barTime, "SKIP_LONG", close1, bbUpper[0], bbMid[0], bbLower[0],
                rsi[0], adxMain[0], atrVal, sl, tp, 0, skipReason);
      return;
   }
   if(signal == -1 && tp > 0 && tp >= price)
   {
      skipReason = "TP_ABOVE_ENTRY";
      LogSignal(barTime, "SKIP_SHORT", close1, bbUpper[0], bbMid[0], bbLower[0],
                rsi[0], adxMain[0], atrVal, sl, tp, 0, skipReason);
      return;
   }

   //--- Calculate lot size
   double slPoints = MathAbs(price - sl) / point;
   double lot = CalcLotSize(slPoints);
   if(lot <= 0)
   {
      skipReason = "LOT_ZERO";
      LogSignal(barTime, signal > 0 ? "SKIP_LONG" : "SKIP_SHORT", close1,
                bbUpper[0], bbMid[0], bbLower[0], rsi[0], adxMain[0], atrVal,
                sl, tp, 0, skipReason);
      return;
   }

   //--- Execute trade
   ENUM_ORDER_TYPE orderType = (signal == 1) ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
   string comment = StringFormat("NAS100MR|RSI=%.0f|ADX=%.0f", rsi[0], adxMain[0]);

   bool ok = g_trade.PositionOpen(_Symbol, orderType, lot, price, sl, tp, comment);
   if(ok)
   {
      g_todayTrades++;
      PrintFormat("[NAS100MR] %s %.2f lots @ %.2f SL=%.2f TP=%.2f RSI=%.1f ADX=%.1f",
                  signal > 0 ? "BUY" : "SELL", lot, price, sl, tp, rsi[0], adxMain[0]);
      LogSignal(barTime, signal > 0 ? "BUY" : "SELL", price,
                bbUpper[0], bbMid[0], bbLower[0], rsi[0], adxMain[0], atrVal,
                sl, tp, lot, "EXECUTED");
   }
   else
   {
      PrintFormat("[NAS100MR] Order failed: %d", GetLastError());
   }
}

//+------------------------------------------------------------------+
//| Manage open positions: BE, BB exit, Friday flatten               |
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
      long   posType   = PositionGetInteger(POSITION_TYPE);
      double curPrice   = (posType == POSITION_TYPE_BUY)
                           ? SymbolInfoDouble(_Symbol, SYMBOL_BID)
                           : SymbolInfoDouble(_Symbol, SYMBOL_ASK);

      //--- Friday flatten
      if(dt.day_of_week == 5 && dt.hour >= InpFridayClose)
      {
         g_trade.PositionClose(ticket);
         Print("[NAS100MR] Friday flatten");
         continue;
      }

      //--- Break-even at 1R
      if(InpUseBE)
      {
         double slDist = MathAbs(openPrice - sl);
         if(posType == POSITION_TYPE_BUY && curPrice >= openPrice + slDist)
         {
            if(sl < openPrice)
            {
               double newSL = openPrice + SymbolInfoDouble(_Symbol, SYMBOL_POINT);
               g_trade.PositionModify(ticket, newSL, tp);
            }
         }
         else if(posType == POSITION_TYPE_SELL && curPrice <= openPrice - slDist)
         {
            if(sl > openPrice)
            {
               double newSL = openPrice - SymbolInfoDouble(_Symbol, SYMBOL_POINT);
               g_trade.PositionModify(ticket, newSL, tp);
            }
         }
      }

      //--- BB middle exit (dynamic TP update)
      if(InpUseBBExit)
      {
         double bbMidNow[];
         if(CopyBuffer(g_hBB, 0, 1, 1, bbMidNow) >= 1)
         {
            int digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
            double newTP = NormalizeDouble(bbMidNow[0], digits);
            // Update TP if it changed significantly (>10 points)
            if(MathAbs(newTP - tp) > 10 * SymbolInfoDouble(_Symbol, SYMBOL_POINT))
            {
               // Validate new TP is in profit direction
               bool valid = (posType == POSITION_TYPE_BUY && newTP > openPrice) ||
                           (posType == POSITION_TYPE_SELL && newTP < openPrice);
               if(valid)
                  g_trade.PositionModify(ticket, sl, newTP);
            }
         }
      }
   }
}

//+------------------------------------------------------------------+
//| Count my open positions                                           |
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
//| Calculate lot size based on risk percentage                       |
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
   double lot      = riskAmt / (slPoints * pointVal);

   // Apply limits
   double minLot  = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double maxLot  = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   double lotStep = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);

   lot = MathMax(lot, minLot);
   lot = MathMin(lot, InpMaxLot);
   lot = MathMin(lot, maxLot);

   // Round to lot step
   if(lotStep > 0)
      lot = MathFloor(lot / lotStep) * lotStep;

   return NormalizeDouble(lot, 2);
}

//+------------------------------------------------------------------+
//| Datalog writer                                                    |
//+------------------------------------------------------------------+
void LogSignal(datetime time, string signal, double price,
               double bbUp, double bbMid, double bbLow,
               double rsi, double adx, double atr,
               double sl, double tp, double lot, string reason)
{
   if(!InpDatalog || g_logHandle == INVALID_HANDLE) return;
   FileWrite(g_logHandle,
      TimeToString(time, TIME_DATE|TIME_MINUTES),
      signal, DoubleToString(price, 2),
      DoubleToString(bbUp, 2), DoubleToString(bbMid, 2), DoubleToString(bbLow, 2),
      DoubleToString(rsi, 1), DoubleToString(adx, 1), DoubleToString(atr, 2),
      DoubleToString(sl, 2), DoubleToString(tp, 2), DoubleToString(lot, 2),
      reason);
   FileFlush(g_logHandle);
}
//+------------------------------------------------------------------+
