//+------------------------------------------------------------------+
//| EA_ADRExhaust.mq5                                                |
//| Average Daily Range Exhaustion — Mean Reversion                  |
//| Copyright 2026, Max & Ngai Meo Coc                                |
//|                                                                    |
//| EDGE HYPOTHESIS:                                                  |
//| Daily ranges have statistical limits. When the current day's      |
//| range reaches a high percentage of the Average Daily Range        |
//| (ADR), the probability of further expansion decreases and mean    |
//| reversion toward VWAP/midpoint increases. This is structural:     |
//| liquidity providers widen spreads and absorb flow at extremes.    |
//|                                                                    |
//| MECHANISM: When today's high-low range >= ADR_Threshold * ADR,   |
//| and price is at an extreme (near today's high → short, near       |
//| today's low → long), enter a mean reversion trade targeting       |
//| the midpoint of the day's range.                                  |
//|                                                                    |
//| Type: #103 (ADR Exhaustion)                                       |
//| Target: XAUUSD+, USDJPY+ M15. Kill Zone: NY session only.       |
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
//| INPUTS                                                             |
//+------------------------------------------------------------------+
input group "=== Core Settings ==="
input bool   InpEnabled        = true;       // EA Enabled
input double InpRiskPct        = 0.5;        // Risk % per trade
input double InpMaxLot         = 0.50;       // Max lot size
input int    InpMagic          = 20260413;   // Magic number

input group "=== ADR Settings ==="
input int    InpADR_Period     = 14;         // ADR lookback (days)
input double InpADR_Threshold  = 1.0;        // Min ADR% to trigger (1.0 = 100% of ADR)
input double InpExtremePct     = 0.15;       // Price must be within X% of day's extreme

input group "=== Timing (Broker Time) ==="
input int    InpStartH         = 10;         // Earliest entry hour
input int    InpEndH           = 20;         // Latest entry hour
input int    InpExitH          = 23;         // Force exit hour

input group "=== Risk Management ==="
input double InpSL_ATR_Mult    = 1.5;        // SL in ATR multiples
input double InpTP_Mode        = 0;          // TP mode: 0=midpoint, 1=opposite extreme
input int    InpMaxPerDay      = 2;          // Max trades per day
input double InpDailyDD        = 4.0;        // Daily DD kill switch (%)
input bool   InpUseBE          = true;       // Break-even after 1R

input group "=== Day Filter ==="
input bool   InpTradeMon       = true;       // Monday
input bool   InpTradeTue       = true;       // Tuesday
input bool   InpTradeWed       = true;       // Wednesday
input bool   InpTradeThu       = true;       // Thursday
input bool   InpTradeFri       = true;       // Friday

//+------------------------------------------------------------------+
//| GLOBALS                                                            |
//+------------------------------------------------------------------+
CTrade         trade;
CPositionInfo  pos;
CSymbolInfo    sym;

int            handleATR;
double         initialBalance;
int            todayTradeCount;
datetime       lastTradeDay;
double         pipSize;

//+------------------------------------------------------------------+
//| Expert initialization                                              |
//+------------------------------------------------------------------+
int OnInit()
{
   if(!InpEnabled) return INIT_SUCCEEDED;

   trade.SetExpertMagicNumber(InpMagic);
   trade.SetDeviationInPoints(30);
   sym.Name(_Symbol);

   // pip size
   pipSize = sym.Point() * 10.0;
   if(StringFind(_Symbol, "JPY") >= 0)
      pipSize = sym.Point() * 100.0;

   // ATR for SL sizing
   handleATR = iATR(_Symbol, PERIOD_D1, InpADR_Period);
   if(handleATR == INVALID_HANDLE)
   {
      Print("ERROR: Failed to create ATR handle");
      return INIT_FAILED;
   }

   initialBalance = AccountInfoDouble(ACCOUNT_BALANCE);
   todayTradeCount = 0;
   lastTradeDay = 0;

   Print("EA_ADRExhaust v1.0 initialized. Symbol=", _Symbol,
         " ADR_Period=", InpADR_Period,
         " ADR_Threshold=", InpADR_Threshold,
         " ExtremePct=", InpExtremePct);

   return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   if(handleATR != INVALID_HANDLE) IndicatorRelease(handleATR);
}

//+------------------------------------------------------------------+
//| Calculate Average Daily Range (last N days)                        |
//+------------------------------------------------------------------+
double CalcADR()
{
   double totalRange = 0;
   int counted = 0;

   for(int i = 1; i <= InpADR_Period + 5; i++) // +5 for weekends
   {
      double hi = iHigh(_Symbol, PERIOD_D1, i);
      double lo = iLow(_Symbol, PERIOD_D1, i);
      if(hi <= 0 || lo <= 0) continue;

      totalRange += (hi - lo);
      counted++;

      if(counted >= InpADR_Period) break;
   }

   if(counted == 0) return 0;
   return totalRange / counted;
}

//+------------------------------------------------------------------+
//| Get today's high and low (completed bars only)                     |
//+------------------------------------------------------------------+
void GetTodayRange(double &todayHigh, double &todayLow)
{
   MqlDateTime dt;
   TimeToStruct(TimeCurrent(), dt);
   datetime todayStart = StringToTime(StringFormat("%04d.%02d.%02d 00:00", dt.year, dt.mon, dt.day));

   int barsToday = Bars(_Symbol, PERIOD_M15, todayStart, TimeCurrent());
   if(barsToday < 2)
   {
      todayHigh = iHigh(_Symbol, PERIOD_D1, 0);
      todayLow  = iLow(_Symbol, PERIOD_D1, 0);
      return;
   }

   // Use shift >= 1 (closed bars only — non-repaint)
   todayHigh = 0;
   todayLow  = 999999;

   for(int i = 1; i < barsToday; i++)
   {
      double h = iHigh(_Symbol, PERIOD_M15, i);
      double l = iLow(_Symbol, PERIOD_M15, i);

      // Verify bar is from today
      datetime barTime = iTime(_Symbol, PERIOD_M15, i);
      if(barTime < todayStart) break;

      if(h > todayHigh) todayHigh = h;
      if(l < todayLow)  todayLow  = l;
   }
}

//+------------------------------------------------------------------+
//| Day reset                                                          |
//+------------------------------------------------------------------+
void CheckDayReset()
{
   MqlDateTime dt;
   TimeToStruct(TimeCurrent(), dt);
   datetime today = StringToTime(StringFormat("%04d.%02d.%02d", dt.year, dt.mon, dt.day));

   if(today != lastTradeDay)
   {
      lastTradeDay = today;
      todayTradeCount = 0;
   }
}

//+------------------------------------------------------------------+
//| Day filter                                                         |
//+------------------------------------------------------------------+
bool IsTradingDay()
{
   MqlDateTime dt;
   TimeToStruct(TimeCurrent(), dt);
   switch(dt.day_of_week)
   {
      case 1: return InpTradeMon;
      case 2: return InpTradeTue;
      case 3: return InpTradeWed;
      case 4: return InpTradeThu;
      case 5: return InpTradeFri;
      default: return false;
   }
}

//+------------------------------------------------------------------+
//| Time window check                                                  |
//+------------------------------------------------------------------+
bool InEntryWindow()
{
   MqlDateTime dt;
   TimeToStruct(TimeCurrent(), dt);
   return (dt.hour >= InpStartH && dt.hour < InpEndH);
}

bool IsExitTime()
{
   MqlDateTime dt;
   TimeToStruct(TimeCurrent(), dt);
   return (dt.hour >= InpExitH);
}

//+------------------------------------------------------------------+
//| DD kill switch                                                     |
//+------------------------------------------------------------------+
bool DDKillSwitch()
{
   double equity = AccountInfoDouble(ACCOUNT_EQUITY);
   if(initialBalance > 0 && equity < initialBalance * (1.0 - InpDailyDD / 100.0))
   {
      return true;
   }
   return false;
}

//+------------------------------------------------------------------+
//| Count positions                                                    |
//+------------------------------------------------------------------+
int CountPositions()
{
   int count = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      if(pos.SelectByIndex(i))
      {
         if(pos.Magic() == InpMagic && pos.Symbol() == _Symbol)
            count++;
      }
   }
   return count;
}

//+------------------------------------------------------------------+
//| Close all positions                                                |
//+------------------------------------------------------------------+
void CloseAllPositions(string reason)
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      if(pos.SelectByIndex(i))
      {
         if(pos.Magic() == InpMagic && pos.Symbol() == _Symbol)
         {
            trade.PositionClose(pos.Ticket());
            Print("CLOSE [", reason, "] ticket=", pos.Ticket(), " profit=", pos.Profit());
         }
      }
   }
}

//+------------------------------------------------------------------+
//| Lot sizing                                                         |
//+------------------------------------------------------------------+
double CalcLotSize(double slPoints)
{
   sym.RefreshRates();
   double balance = AccountInfoDouble(ACCOUNT_BALANCE);
   double riskMoney = balance * InpRiskPct / 100.0;

   double tickVal  = sym.TickValue();
   double tickSize = sym.TickSize();

   if(tickVal <= 0 || tickSize <= 0 || slPoints <= 0) return sym.LotsMin();

   double lots = riskMoney / (slPoints / tickSize * tickVal);
   lots = MathMin(lots, InpMaxLot);
   lots = MathMax(lots, sym.LotsMin());
   lots = NormalizeDouble(lots / sym.LotsStep(), 0) * sym.LotsStep();

   return lots;
}

//+------------------------------------------------------------------+
//| Break-even management                                              |
//+------------------------------------------------------------------+
void ManageBE()
{
   if(!InpUseBE) return;

   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      if(!pos.SelectByIndex(i)) continue;
      if(pos.Magic() != InpMagic || pos.Symbol() != _Symbol) continue;

      double openPrice = pos.PriceOpen();
      double sl = pos.StopLoss();
      double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
      double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);

      double slDist = MathAbs(openPrice - sl);
      if(slDist <= 0) continue;

      if(pos.PositionType() == POSITION_TYPE_BUY)
      {
         double profit = bid - openPrice;
         if(profit >= slDist && sl < openPrice)
         {
            double newSL = openPrice + sym.Spread() * sym.Point();
            trade.PositionModify(pos.Ticket(), newSL, pos.TakeProfit());
         }
      }
      else if(pos.PositionType() == POSITION_TYPE_SELL)
      {
         double profit = openPrice - ask;
         if(profit >= slDist && (sl == 0 || sl > openPrice))
         {
            double newSL = openPrice - sym.Spread() * sym.Point();
            trade.PositionModify(pos.Ticket(), newSL, pos.TakeProfit());
         }
      }
   }
}

//+------------------------------------------------------------------+
//| Expert tick function                                               |
//+------------------------------------------------------------------+
void OnTick()
{
   if(!InpEnabled) return;

   sym.RefreshRates();
   CheckDayReset();

   // Manage existing positions
   ManageBE();

   // Force exit at end of day
   if(IsExitTime() && CountPositions() > 0)
   {
      CloseAllPositions("TimeExit_EOD");
      return;
   }

   // DD kill switch
   if(DDKillSwitch()) return;

   // No new entries if position open or max trades reached
   if(CountPositions() > 0) return;
   if(todayTradeCount >= InpMaxPerDay) return;

   // Day filter
   if(!IsTradingDay()) return;

   // Time window
   if(!InEntryWindow()) return;

   // === CORE LOGIC: ADR Exhaustion ===

   // 1. Calculate ADR
   double adr = CalcADR();
   if(adr <= 0) return;

   // 2. Get today's range (closed bars only)
   double todayHigh, todayLow;
   GetTodayRange(todayHigh, todayLow);
   if(todayHigh <= 0 || todayLow >= 999999) return;

   double todayRange = todayHigh - todayLow;

   // 3. Check if today's range has reached ADR threshold
   double rangeRatio = todayRange / adr;
   if(rangeRatio < InpADR_Threshold) return; // Not exhausted yet

   // 4. Determine if price is at extreme
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double midpoint = (todayHigh + todayLow) / 2.0;

   double distFromHigh = todayHigh - bid;
   double distFromLow  = bid - todayLow;

   bool atUpperExtreme = (distFromHigh <= todayRange * InpExtremePct);
   bool atLowerExtreme = (distFromLow  <= todayRange * InpExtremePct);

   // 5. Get ATR for SL sizing
   double atrArr[];
   if(CopyBuffer(handleATR, 0, 1, 1, atrArr) < 1) return;
   double slDistance = atrArr[0] * InpSL_ATR_Mult;

   // Check stop level
   int stopLevel = (int)SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL);
   double minDist = stopLevel * sym.Point();

   // 6. Enter trade
   if(atUpperExtreme)
   {
      // SELL — price at top of exhausted range, expect reversion to midpoint
      double slPrice = bid + slDistance;
      double tpPrice = (InpTP_Mode == 0) ? midpoint : todayLow;

      if(slPrice - bid < minDist) slPrice = bid + minDist + sym.Point();
      if(bid - tpPrice < minDist) tpPrice = bid - minDist - sym.Point();

      double lots = CalcLotSize(slDistance);

      bool filled = false;
      for(int attempt = 1; attempt <= 3; attempt++)
      {
         if(trade.Sell(lots, _Symbol, bid, slPrice, tpPrice,
                        StringFormat("ADR_S_%.0f%%", rangeRatio * 100)))
         {
            filled = true;
            break;
         }
         if(attempt < 3) Sleep(200 * (int)MathPow(2, attempt - 1));
      }

      if(filled)
      {
         Print("ADR EXHAUST SELL: range=", DoubleToString(todayRange / pipSize, 1),
               " pips, ADR=", DoubleToString(adr / pipSize, 1),
               " ratio=", DoubleToString(rangeRatio, 2),
               " lots=", lots);
         todayTradeCount++;
      }
   }
   else if(atLowerExtreme)
   {
      // BUY — price at bottom of exhausted range, expect reversion to midpoint
      double slPrice = ask - slDistance;
      double tpPrice = (InpTP_Mode == 0) ? midpoint : todayHigh;

      if(ask - slPrice < minDist) slPrice = ask - minDist - sym.Point();
      if(tpPrice - ask < minDist) tpPrice = ask + minDist + sym.Point();

      double lots = CalcLotSize(slDistance);

      bool filled = false;
      for(int attempt = 1; attempt <= 3; attempt++)
      {
         if(trade.Buy(lots, _Symbol, ask, slPrice, tpPrice,
                       StringFormat("ADR_B_%.0f%%", rangeRatio * 100)))
         {
            filled = true;
            break;
         }
         if(attempt < 3) Sleep(200 * (int)MathPow(2, attempt - 1));
      }

      if(filled)
      {
         Print("ADR EXHAUST BUY: range=", DoubleToString(todayRange / pipSize, 1),
               " pips, ADR=", DoubleToString(adr / pipSize, 1),
               " ratio=", DoubleToString(rangeRatio, 2),
               " lots=", lots);
         todayTradeCount++;
      }
   }
}
//+------------------------------------------------------------------+
