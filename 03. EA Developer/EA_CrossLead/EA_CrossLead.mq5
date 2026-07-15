//+------------------------------------------------------------------+
//| EA_CrossLead.mq5 — EURJPY→USDJPY Lead-Lag Signal                |
//| Symbol: USDJPY  |  Period: M15  |  Style: Cross-pair momentum   |
//|                                                                   |
//| EDGE HYPOTHESIS (v1.0):                                           |
//| When EURJPY breaks down (European institutions unwind carry),     |
//| USDJPY follows with 1-3 bar delay. We sell USDJPY on EURJPY      |
//| breakdown signal before USDJPY confirms.                          |
//|                                                                   |
//| MECHANISM:                                                        |
//| European banks adjust JPY exposure via EURJPY first (direct       |
//| flow), then USD/JPY adjusts as cross-rate effect propagates.     |
//| For upside: EURJPY breakout → USDJPY follows up.                |
//|                                                                   |
//| COUNTERPARTY: Slow arbitrageurs who wait for correlation to       |
//| catch up.                                                         |
//|                                                                   |
//| Max | 2026-04-05 | v1.0                                         |
//+------------------------------------------------------------------+
#property copyright "Max — EA_CrossLead v1.0"
#property version   "1.00"
#property strict

#include <Trade\Trade.mqh>

//+------------------------------------------------------------------+
input group "=== General ==="
input ulong    InpMagic         = 602601;    // Magic Number
input int      InpDeviation     = 30;        // Max Slippage (pts)
input bool     InpKillSwitch    = false;     // Kill Switch

input group "=== Lead Symbol ==="
input string   InpLeadSymbol    = "EURJPY";  // Lead symbol (checked for breakout)
input int      InpLookback      = 20;        // Lookback for High/Low range (bars)

input group "=== Session Filter (Server Time) ==="
input int      InpStartHour     = 9;         // Entry start hour (London open)
input int      InpEndHour       = 18;        // Entry end hour
input bool     InpMonday        = true;      // Trade Monday
input bool     InpTuesday       = true;      // Trade Tuesday
input bool     InpWednesday     = true;      // Trade Wednesday
input bool     InpThursday      = true;      // Trade Thursday
input bool     InpFriday        = false;     // Trade Friday

input group "=== Risk Management ==="
input double   InpRiskPct       = 0.40;      // Risk per trade (%)
input double   InpMaxLot        = 0.50;      // Max lot
input double   InpATRMultSL     = 2.0;       // SL = ATR x this
input int      InpATRPeriod     = 14;        // ATR Period
input double   InpRR            = 2.0;       // Reward:Risk ratio
input int      InpMaxPerDay     = 1;         // Max trades per day
input double   InpDailyDDPct    = 2.0;       // Daily DD kill (%)
input bool     InpUseBE         = true;      // Move SL to BE at 1R

input group "=== Confirmation ==="
input bool     InpRequireNoBreak= true;      // Require USDJPY NOT yet broken (lag confirmation)

input group "=== Datalog ==="
input bool     InpDatalog       = true;      // Enable CSV signal log

//+------------------------------------------------------------------+
CTrade         g_trade;
int            g_hATR;
int            g_hATR_lead;
datetime       g_lastBar;
int            g_todayTrades;
datetime       g_todayDate;
double         g_dayStartBal;
int            g_logHandle;

//+------------------------------------------------------------------+
int OnInit()
{
   if(InpKillSwitch) { Print("[CrossLead] Kill switch ON"); return INIT_SUCCEEDED; }

   g_trade.SetExpertMagicNumber(InpMagic);
   g_trade.SetDeviationInPoints(InpDeviation);
   g_trade.SetTypeFilling(ORDER_FILLING_FOK);

   g_hATR = iATR(_Symbol, PERIOD_CURRENT, InpATRPeriod);
   g_hATR_lead = iATR(InpLeadSymbol, PERIOD_CURRENT, InpATRPeriod);

   if(g_hATR == INVALID_HANDLE || g_hATR_lead == INVALID_HANDLE)
   { Print("[CrossLead] FATAL: ATR init failed"); return INIT_FAILED; }

   g_lastBar     = 0;
   g_todayTrades = 0;
   g_todayDate   = 0;
   g_dayStartBal = AccountInfoDouble(ACCOUNT_BALANCE);

   if(InpDatalog)
   {
      string fname = "CrossLead_datalog_" + _Symbol + ".csv";
      g_logHandle = FileOpen(fname, FILE_WRITE|FILE_CSV|FILE_COMMON, ',');
      if(g_logHandle != INVALID_HANDLE)
         FileWrite(g_logHandle,
            "Time","Signal","Price","LeadHigh","LeadLow","LeadClose",
            "TargetHigh","TargetLow","ATR","SL","TP","Lot","SkipReason");
   }

   PrintFormat("[CrossLead] Init OK: %s lead=%s lookback=%d", _Symbol, InpLeadSymbol, InpLookback);
   return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   if(g_hATR != INVALID_HANDLE) IndicatorRelease(g_hATR);
   if(g_hATR_lead != INVALID_HANDLE) IndicatorRelease(g_hATR_lead);
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

   // Manage existing: BE logic
   ManagePositions();

   // Already at max?
   if(g_todayTrades >= InpMaxPerDay) return;
   if(CountMyPositions() > 0) return;

   // Daily DD kill
   double ddPct = (g_dayStartBal > 0)
                  ? (g_dayStartBal - AccountInfoDouble(ACCOUNT_EQUITY)) / g_dayStartBal * 100.0
                  : 0;
   if(ddPct >= InpDailyDDPct) return;

   // Session + day filter
   if(!IsTradingDay(dt.day_of_week)) return;
   if(dt.hour < InpStartHour || dt.hour >= InpEndHour) return;

   // Get lead symbol data (EURJPY)
   double leadClose1 = iClose(InpLeadSymbol, PERIOD_CURRENT, 1);
   double leadHigh = 0, leadLow = 999999;
   for(int i = 2; i <= InpLookback + 1; i++)
   {
      double h = iHigh(InpLeadSymbol, PERIOD_CURRENT, i);
      double l = iLow(InpLeadSymbol, PERIOD_CURRENT, i);
      if(h > leadHigh) leadHigh = h;
      if(l < leadLow)  leadLow  = l;
   }

   // Get target symbol (USDJPY) range for "not yet broken" check
   double targetClose1 = iClose(_Symbol, PERIOD_CURRENT, 1);
   double targetHigh = 0, targetLow = 999999;
   for(int i = 2; i <= InpLookback + 1; i++)
   {
      double h = iHigh(_Symbol, PERIOD_CURRENT, i);
      double l = iLow(_Symbol, PERIOD_CURRENT, i);
      if(h > targetHigh) targetHigh = h;
      if(l < targetLow)  targetLow  = l;
   }

   // ATR
   double atr[];
   if(CopyBuffer(g_hATR, 0, 1, 1, atr) < 1) return;

   int    digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
   double point  = SymbolInfoDouble(_Symbol, SYMBOL_POINT);

   // SIGNAL LOGIC: Lead breakout + target NOT yet broken
   int signal = 0; // 0=none, 1=buy, -1=sell

   // Lead EURJPY breakout UP → USDJPY should follow UP
   if(leadClose1 > leadHigh)
   {
      if(!InpRequireNoBreak || targetClose1 <= targetHigh)
         signal = 1; // Buy USDJPY
   }
   // Lead EURJPY breakout DOWN → USDJPY should follow DOWN
   else if(leadClose1 < leadLow)
   {
      if(!InpRequireNoBreak || targetClose1 >= targetLow)
         signal = -1; // Sell USDJPY
   }

   if(signal == 0) return;

   // Calculate SL/TP
   double slDist = atr[0] * InpATRMultSL;
   double price, sl, tp;

   if(signal == 1) // BUY
   {
      price = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
      sl    = NormalizeDouble(price - slDist, digits);
      tp    = NormalizeDouble(price + slDist * InpRR, digits);
   }
   else // SELL
   {
      price = SymbolInfoDouble(_Symbol, SYMBOL_BID);
      sl    = NormalizeDouble(price + slDist, digits);
      tp    = NormalizeDouble(price - slDist * InpRR, digits);
   }

   double slPoints = MathAbs(price - sl) / point;
   double lot = CalcLotSize(slPoints);
   if(lot <= 0) return;

   ENUM_ORDER_TYPE orderType = (signal == 1) ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
   string comment = StringFormat("XLead|%s|dir=%d", InpLeadSymbol, signal);

   bool ok = g_trade.PositionOpen(_Symbol, orderType, lot, price, sl, tp, comment);
   if(ok)
   {
      g_todayTrades++;
      PrintFormat("[CrossLead] %s %.2f @ %.5f SL=%.5f TP=%.5f Lead=%s broke %s",
                  signal == 1 ? "BUY" : "SELL", lot, price, sl, tp,
                  InpLeadSymbol, signal == 1 ? "HIGH" : "LOW");
      LogSignal(barTime, signal == 1 ? "BUY" : "SELL", price,
                leadHigh, leadLow, leadClose1, targetHigh, targetLow,
                atr[0], sl, tp, lot, "EXECUTED");
   }
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

      double slDist = MathAbs(openPrice - sl);
      double pt     = SymbolInfoDouble(_Symbol, SYMBOL_POINT);

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
void LogSignal(datetime time, string sig, double price,
               double leadH, double leadL, double leadC,
               double targH, double targL,
               double atr, double sl, double tp, double lot, string reason)
{
   if(!InpDatalog || g_logHandle == INVALID_HANDLE) return;
   FileWrite(g_logHandle,
      TimeToString(time, TIME_DATE|TIME_MINUTES),
      sig, DoubleToString(price, 5),
      DoubleToString(leadH, 3), DoubleToString(leadL, 3), DoubleToString(leadC, 3),
      DoubleToString(targH, 5), DoubleToString(targL, 5),
      DoubleToString(atr, 5), DoubleToString(sl, 5), DoubleToString(tp, 5),
      DoubleToString(lot, 2), reason);
   FileFlush(g_logHandle);
}
//+------------------------------------------------------------------+
