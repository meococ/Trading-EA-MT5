//+------------------------------------------------------------------+
//| EA_IntervalMom.mq5                                               |
//| Intraday Interval Momentum (Gao et al. 2018)                    |
//| Copyright 2026, Max & Ngai Meo Coc                                |
//|                                                                    |
//| EDGE HYPOTHESIS:                                                  |
//| Returns at the same time-of-day interval exhibit cross-day       |
//| persistence. If price rose during h15-16 yesterday, it tends     |
//| to rise during h15-16 today. Attributed to institutional TWAP    |
//| order patterns that repeat daily.                                 |
//|                                                                    |
//| MECHANISM: At InpEntryH, check the return of the SAME hour      |
//| yesterday (shift by ~96 M15 bars for 1 day). If yesterday's     |
//| return at this hour was positive → buy. If negative → sell.      |
//| Use lookback of N days for robustness.                           |
//|                                                                    |
//| Type: #106 (Cross-day interval momentum)                         |
//| Target: XAUUSD+, USDJPY+ M15                                    |
//| Max | 2026-04-14 | v1.0                                          |
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
input int    InpMagic       = 20260416;

input group "=== Signal ==="
input int    InpEntryH      = 15;         // Entry hour (broker time)
input int    InpLookbackDays = 5;         // How many past days to average
input double InpMinBias     = 0.6;        // Min fraction of days with same direction
input int    InpHoldBars    = 4;          // Hold time in M15 bars

input group "=== Risk ==="
input double InpSL_ATR      = 1.5;        // SL in D1 ATR multiples
input int    InpMaxPerDay   = 1;
input double InpDailyDD     = 4.0;

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
   Print("EA_IntervalMom v1.0: ", _Symbol, " H=", InpEntryH,
         " LookbackDays=", InpLookbackDays, " MinBias=", InpMinBias);
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
//| Calculate interval direction over past N days at same hour        |
//+------------------------------------------------------------------+
int GetIntervalBias()
{
   int upDays = 0;
   int downDays = 0;
   int barsPerDay = 96; // 24h * 4 bars/h on M15

   for(int d = 1; d <= InpLookbackDays + 2; d++) // +2 for weekends
   {
      // Find the bar at same hour, d days ago
      int shift = d * barsPerDay;

      // Verify the bar exists and is at the right hour
      datetime barTime = iTime(_Symbol, PERIOD_M15, shift);
      if(barTime <= 0) continue;

      MqlDateTime dt;
      TimeToStruct(barTime, dt);

      // Skip if not the target hour (due to weekends/holidays)
      if(dt.hour != InpEntryH) continue;

      // Get return over that hour (4 M15 bars = 1 hour)
      double openPrice = iOpen(_Symbol, PERIOD_M15, shift);
      double closePrice = iClose(_Symbol, PERIOD_M15, MathMax(1, shift - 3));

      if(openPrice <= 0 || closePrice <= 0) continue;

      double ret = closePrice - openPrice;

      if(ret > 0) upDays++;
      else if(ret < 0) downDays++;

      if(upDays + downDays >= InpLookbackDays) break;
   }

   int total = upDays + downDays;
   if(total == 0) return 0;

   double upFrac = (double)upDays / total;
   double downFrac = (double)downDays / total;

   if(upFrac >= InpMinBias) return 1;    // Buy bias
   if(downFrac >= InpMinBias) return -1;  // Sell bias
   return 0; // No clear bias
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

   // DD kill switch
   double equity = AccountInfoDouble(ACCOUNT_EQUITY);
   if(initialBalance > 0 && equity < initialBalance * (1.0 - InpDailyDD / 100.0)) return;

   if(todayTradeCount >= InpMaxPerDay) return;
   if(!IsTradingDay()) return;

   MqlDateTime dt;
   TimeToStruct(TimeCurrent(), dt);
   if(dt.hour != InpEntryH) return;
   if(dt.min >= 15) return; // First M15 bar only

   // === CORE SIGNAL: Cross-day interval momentum ===
   int bias = GetIntervalBias();
   if(bias == 0) return;

   // ATR for SL
   double atrArr[];
   if(CopyBuffer(handleATR, 0, 1, 1, atrArr) < 1) return;
   double sl = atrArr[0] * InpSL_ATR;

   int stopLevel = (int)SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL);
   double minDist = stopLevel * sym.Point();
   double lots = CalcLots(sl);

   if(bias > 0)
   {
      double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
      double slP = ask - sl;
      if(ask - slP < minDist) slP = ask - minDist - sym.Point();
      for(int a = 1; a <= 3; a++)
      {
         if(trade.Buy(lots, _Symbol, ask, slP, 0,
                       StringFormat("IntMom_B_%dd", InpLookbackDays))) break;
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
         if(trade.Sell(lots, _Symbol, bid, slP, 0,
                        StringFormat("IntMom_S_%dd", InpLookbackDays))) break;
         if(a < 3) Sleep(200 * (int)MathPow(2, a-1));
      }
   }

   todayTradeCount++;
   barsHeld = 0;
   lastCountedBar = 0;
}
//+------------------------------------------------------------------+
