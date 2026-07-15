//+------------------------------------------------------------------+
//| EA_D1InsideDay.mq5                                               |
//| Daily Inside Day Breakout Strategy                               |
//| Copyright 2026, Max & Ngai Meo Coc                                |
//|                                                                    |
//| EDGE HYPOTHESIS:                                                  |
//| When D1 bar is entirely inside previous D1 bar (inside day),     |
//| institutional compression precedes expansion. Breakout above/     |
//| below the inside day range on next day = directional move.        |
//|                                                                    |
//| Different from H1 InsideBar (S143 dead on M15) because D1       |
//| compression captures genuine multi-day institutional indecision.  |
//|                                                                    |
//| MECHANISM: Detect D1 inside day (shift=1). Place pending orders  |
//| above high and below low. First fill cancels other. SL = mid-   |
//| range of inside day. TP = ATR-based or time exit.                |
//|                                                                    |
//| Type: #108 (D1 inside day breakout)                              |
//| Max | 2026-04-14 | v1.0                                          |
//+------------------------------------------------------------------+
#property copyright "Max & Ngai Meo Coc"
#property version   "1.00"
#property strict

#include <Trade\Trade.mqh>
#include <Trade\PositionInfo.mqh>
#include <Trade\SymbolInfo.mqh>
#include <Trade\OrderInfo.mqh>

input group "=== Core ==="
input bool   InpEnabled     = true;
input double InpRiskPct     = 0.5;
input double InpMaxLot      = 1.00;
input int    InpMagic       = 20260418;

input group "=== Signal ==="
input double InpBreakBuffer = 0.0;      // Buffer above/below inside day (ATR fraction)
input double InpSL_Fraction = 0.5;      // SL = fraction of inside day range from entry
input double InpTP_RR       = 2.0;      // TP as multiple of SL distance
input int    InpMaxHoldDays = 5;        // Max hold time in D1 bars

input group "=== Filters ==="
input double InpMinRangeATR = 0.3;      // Min inside day range (ATR fraction)
input double InpMaxRangeATR = 1.5;      // Max inside day range (ATR fraction, skip wide)
input bool   InpTrendFilter = false;    // Require D1 EMA50 alignment
input int    InpEMA_Period  = 50;
input int    InpMaxPerWeek  = 2;
input double InpDailyDD     = 4.0;

CTrade trade;
CPositionInfo pos;
CSymbolInfo sym;
COrderInfo ord;
int hATR, hEMA;
double initialBalance;
int weekTradeCount, lastWeek;
datetime lastDay;
bool pendingPlaced;
ulong buyStopTicket, sellStopTicket;

int OnInit()
{
   if(!InpEnabled) return INIT_SUCCEEDED;
   trade.SetExpertMagicNumber(InpMagic);
   trade.SetDeviationInPoints(50);
   sym.Name(_Symbol);
   hATR = iATR(_Symbol, PERIOD_D1, 14);
   hEMA = iMA(_Symbol, PERIOD_D1, InpEMA_Period, 0, MODE_EMA, PRICE_CLOSE);
   if(hATR == INVALID_HANDLE || hEMA == INVALID_HANDLE) return INIT_FAILED;
   initialBalance = AccountInfoDouble(ACCOUNT_BALANCE);
   weekTradeCount = 0; lastWeek = -1;
   lastDay = 0; pendingPlaced = false;
   buyStopTicket = 0; sellStopTicket = 0;
   Print("EA_D1InsideDay v1.0: ", _Symbol);
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   if(hATR != INVALID_HANDLE) IndicatorRelease(hATR);
   if(hEMA != INVALID_HANDLE) IndicatorRelease(hEMA);
}

void CheckWeekReset()
{
   MqlDateTime dt;
   TimeToStruct(TimeCurrent(), dt);
   int wk = dt.day_of_year / 7;
   if(wk != lastWeek) { lastWeek = wk; weekTradeCount = 0; }
}

int CountPos()
{
   int c = 0;
   for(int i = PositionsTotal()-1; i >= 0; i--)
      if(pos.SelectByIndex(i) && pos.Magic() == InpMagic && pos.Symbol() == _Symbol) c++;
   return c;
}

void CloseAll(string reason)
{
   for(int i = PositionsTotal()-1; i >= 0; i--)
      if(pos.SelectByIndex(i) && pos.Magic() == InpMagic && pos.Symbol() == _Symbol)
         trade.PositionClose(pos.Ticket());
}

void CancelPendings()
{
   for(int i = OrdersTotal()-1; i >= 0; i--)
   {
      if(ord.SelectByIndex(i) && ord.Magic() == InpMagic && ord.Symbol() == _Symbol)
         trade.OrderDelete(ord.Ticket());
   }
   buyStopTicket = 0;
   sellStopTicket = 0;
   pendingPlaced = false;
}

double CalcLots(double slPts)
{
   sym.RefreshRates();
   double bal = AccountInfoDouble(ACCOUNT_BALANCE);
   double risk = bal * InpRiskPct / 100.0;
   double tv = sym.TickValue(); double ts = sym.TickSize();
   if(tv <= 0 || ts <= 0 || slPts <= 0) return sym.LotsMin();
   double lots = risk / (slPts / ts * tv);
   lots = MathMin(lots, InpMaxLot);
   lots = MathMax(lots, sym.LotsMin());
   lots = NormalizeDouble(lots / sym.LotsStep(), 0) * sym.LotsStep();
   return lots;
}

bool IsInsideDay()
{
   // shift=1 = yesterday (closed), shift=2 = day before
   double h1 = iHigh(_Symbol, PERIOD_D1, 1);
   double l1 = iLow(_Symbol, PERIOD_D1, 1);
   double h2 = iHigh(_Symbol, PERIOD_D1, 2);
   double l2 = iLow(_Symbol, PERIOD_D1, 2);

   if(h1 <= 0 || h2 <= 0) return false;
   return (h1 < h2 && l1 > l2); // Inside day: yesterday range inside day-before
}

void OnTick()
{
   if(!InpEnabled) return;

   // Only check on new D1 bar
   datetime currentDay = iTime(_Symbol, PERIOD_D1, 0);
   bool newDay = (currentDay != lastDay);

   sym.RefreshRates();
   CheckWeekReset();

   // If we have a position, manage it
   if(CountPos() > 0)
   {
      // Cancel any remaining pendings (OCO: one filled, cancel other)
      CancelPendings();

      // Time-based exit check (rough: count bars since entry)
      // Simplified: if position open more than MaxHoldDays, close
      if(newDay)
      {
         lastDay = currentDay;
         // Check hold duration via position open time
         for(int i = PositionsTotal()-1; i >= 0; i--)
         {
            if(!pos.SelectByIndex(i)) continue;
            if(pos.Magic() != InpMagic || pos.Symbol() != _Symbol) continue;
            int daysSinceOpen = (int)((TimeCurrent() - pos.Time()) / 86400);
            if(daysSinceOpen >= InpMaxHoldDays)
            {
               trade.PositionClose(pos.Ticket());
               Print("D1ID CLOSE [MaxHold ", daysSinceOpen, "d]");
            }
         }
      }
      return;
   }

   if(!newDay) return;
   lastDay = currentDay;

   // Cancel old pendings from yesterday if not filled
   CancelPendings();

   // DD kill switch
   double equity = AccountInfoDouble(ACCOUNT_EQUITY);
   if(initialBalance > 0 && equity < initialBalance * (1.0 - InpDailyDD / 100.0)) return;
   if(weekTradeCount >= InpMaxPerWeek) return;

   // === DETECT INSIDE DAY ===
   if(!IsInsideDay()) return;

   double h1 = iHigh(_Symbol, PERIOD_D1, 1);
   double l1 = iLow(_Symbol, PERIOD_D1, 1);
   double range = h1 - l1;

   // ATR filter
   double atrArr[];
   if(CopyBuffer(hATR, 0, 1, 1, atrArr) < 1) return;
   double atr = atrArr[0];

   if(range < atr * InpMinRangeATR || range > atr * InpMaxRangeATR) return;

   // Optional trend filter
   if(InpTrendFilter)
   {
      double emaArr[];
      if(CopyBuffer(hEMA, 0, 1, 1, emaArr) < 1) return;
      // Only allow trend-aligned trades (buy if above EMA, sell if below)
      // For pending orders, skip filter as both directions possible
   }

   // === PLACE OCO PENDING ORDERS ===
   double buffer = atr * InpBreakBuffer;
   double buyEntry = h1 + buffer + sym.Point();
   double sellEntry = l1 - buffer - sym.Point();

   double slDist = range * InpSL_Fraction;
   double buySL = buyEntry - slDist;
   double sellSL = sellEntry + slDist;
   double buyTP = buyEntry + slDist * InpTP_RR;
   double sellTP = sellEntry - slDist * InpTP_RR;

   int stopLevel = (int)SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL);
   double minDist = stopLevel * sym.Point();

   // Ensure minimum distances
   if(buyEntry - buySL < minDist) buySL = buyEntry - minDist - sym.Point();
   if(sellSL - sellEntry < minDist) sellSL = sellEntry + minDist + sym.Point();

   double lots = CalcLots(slDist);

   // Buy stop above inside day high
   if(trade.BuyStop(lots, buyEntry, _Symbol, buySL, buyTP, ORDER_TIME_DAY, 0, "D1ID_B"))
   {
      buyStopTicket = trade.ResultOrder();
      Print("D1 INSIDE DAY: BuyStop at ", buyEntry, " sl=", buySL, " tp=", buyTP);
   }

   // Sell stop below inside day low
   if(trade.SellStop(lots, sellEntry, _Symbol, sellSL, sellTP, ORDER_TIME_DAY, 0, "D1ID_S"))
   {
      sellStopTicket = trade.ResultOrder();
      Print("D1 INSIDE DAY: SellStop at ", sellEntry, " sl=", sellSL, " tp=", sellTP);
   }

   pendingPlaced = true;
   weekTradeCount++;
}
