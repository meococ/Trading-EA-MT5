//+------------------------------------------------------------------+
//| EA_HourBias.mq5                                                  |
//| Pure Hour-of-Day Directional Bias                                |
//| Copyright 2026, Max & Ngai Meo Coc                                |
//|                                                                    |
//| EDGE HYPOTHESIS:                                                  |
//| Test if specific hours have persistent directional bias on        |
//| USDJPY+ or XAUUSD+. No indicators — pure time-of-day signal.    |
//| If bias exists at specific hours, it validates KZ windows.        |
//| If no bias, confirms indicators add real value.                   |
//|                                                                    |
//| MECHANISM: At InpEntryH, buy or sell based on InpDirection.       |
//| Hold for InpHoldBars M15 bars. Time exit only.                   |
//| SL = ATR-based safety net.                                        |
//|                                                                    |
//| Type: #105 (Pure hour-of-day directional bias)                    |
//| Max | 2026-04-13 | v1.0                                          |
//+------------------------------------------------------------------+
#property copyright "Max & Ngai Meo Coc"
#property link      ""
#property version   "1.00"
#property strict

#include <Trade\Trade.mqh>
#include <Trade\PositionInfo.mqh>
#include <Trade\SymbolInfo.mqh>

//+------------------------------------------------------------------+
input group "=== Core ==="
input bool   InpEnabled     = true;
input double InpRiskPct     = 0.5;
input double InpMaxLot      = 0.50;
input int    InpMagic       = 20260415;

input group "=== Signal ==="
input int    InpEntryH      = 15;         // Entry hour (broker time)
input int    InpDirection    = 1;          // 1=Buy, -1=Sell
input int    InpHoldBars    = 4;          // Hold time in M15 bars
input double InpSL_ATR      = 1.5;        // SL in D1 ATR multiples

input group "=== Day Filter ==="
input bool   InpTradeMon    = true;
input bool   InpTradeTue    = true;
input bool   InpTradeWed    = true;
input bool   InpTradeThu    = true;
input bool   InpTradeFri    = true;

//+------------------------------------------------------------------+
CTrade         trade;
CPositionInfo  pos;
CSymbolInfo    sym;
int            handleATR;
double         initialBalance;
int            todayTradeCount;
datetime       lastTradeDay;
int            barsHeld;
datetime       lastCountedBar;

//+------------------------------------------------------------------+
int OnInit()
{
   if(!InpEnabled) return INIT_SUCCEEDED;
   trade.SetExpertMagicNumber(InpMagic);
   trade.SetDeviationInPoints(30);
   sym.Name(_Symbol);
   handleATR = iATR(_Symbol, PERIOD_D1, 14);
   if(handleATR == INVALID_HANDLE) return INIT_FAILED;
   initialBalance = AccountInfoDouble(ACCOUNT_BALANCE);
   todayTradeCount = 0;
   lastTradeDay = 0;
   barsHeld = 0;
   lastCountedBar = 0;
   Print("EA_HourBias v1.0: ", _Symbol, " H=", InpEntryH, " Dir=", InpDirection);
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   if(handleATR != INVALID_HANDLE) IndicatorRelease(handleATR);
}

void CheckDayReset()
{
   MqlDateTime dt;
   TimeToStruct(TimeCurrent(), dt);
   datetime today = StringToTime(StringFormat("%04d.%02d.%02d", dt.year, dt.mon, dt.day));
   if(today != lastTradeDay) { lastTradeDay = today; todayTradeCount = 0; }
}

bool IsTradingDay()
{
   MqlDateTime dt;
   TimeToStruct(TimeCurrent(), dt);
   switch(dt.day_of_week)
   {
      case 1: return InpTradeMon; case 2: return InpTradeTue;
      case 3: return InpTradeWed; case 4: return InpTradeThu;
      case 5: return InpTradeFri; default: return false;
   }
}

int CountPositions()
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

//+------------------------------------------------------------------+
void OnTick()
{
   if(!InpEnabled) return;
   sym.RefreshRates();
   CheckDayReset();

   // Manage time exit
   if(CountPositions() > 0)
   {
      datetime currentBar = iTime(_Symbol, PERIOD_M15, 0);
      if(currentBar != lastCountedBar)
      {
         lastCountedBar = currentBar;
         barsHeld++;
      }
      if(barsHeld >= InpHoldBars)
      {
         CloseAll("TimeExit");
         barsHeld = 0;
      }
      return;
   }

   // Filters
   if(todayTradeCount >= 1) return;
   if(!IsTradingDay()) return;

   MqlDateTime dt;
   TimeToStruct(TimeCurrent(), dt);
   if(dt.hour != InpEntryH) return;
   if(dt.min >= 15) return; // First M15 bar of the hour only

   // ATR for SL
   double atrArr[];
   if(CopyBuffer(handleATR, 0, 1, 1, atrArr) < 1) return;
   double sl = atrArr[0] * InpSL_ATR;

   int stopLevel = (int)SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL);
   double minDist = stopLevel * sym.Point();

   double lots = CalcLots(sl);

   if(InpDirection > 0)
   {
      double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
      double slP = ask - sl;
      if(ask - slP < minDist) slP = ask - minDist - sym.Point();
      for(int a = 1; a <= 3; a++)
      {
         if(trade.Buy(lots, _Symbol, ask, slP, 0, "HBias_B")) break;
         if(a < 3) Sleep(200 * (int)MathPow(2, a-1));
      }
   }
   else
   {
      double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
      double slP = bid + sl;
      if(slP - bid < minDist) slP = bid + minDist + sym.Point();
      for(int a = 1; a <= 3; a++)
      {
         if(trade.Sell(lots, _Symbol, bid, slP, 0, "HBias_S")) break;
         if(a < 3) Sleep(200 * (int)MathPow(2, a-1));
      }
   }

   todayTradeCount++;
   barsHeld = 0;
   lastCountedBar = 0;
}
//+------------------------------------------------------------------+
