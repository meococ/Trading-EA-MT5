//+------------------------------------------------------------------+
//| EA_EqCloseFlow.mq5                                               |
//| Equity-Close Rebalancing Flow Strategy                            |
//| Copyright 2026, Max & Ngai Meo Coc                                |
//|                                                                    |
//| EDGE HYPOTHESIS:                                                  |
//| After US equity market closes (~21:00 GMT), balanced/pension      |
//| funds rebalance FX exposure back to target allocation. This       |
//| creates a short directional drift on carry-trade pairs like       |
//| USDJPY. Direction depends on whether equities rose (sell JPY →    |
//| long USDJPY) or fell (buy JPY → short USDJPY) during session.    |
//|                                                                    |
//| MECHANISM: At US equity close, measure the D1 bar direction so   |
//| far. If positive → buy USDJPY (rebal = sell JPY). If negative    |
//| → sell USDJPY. Hold for 30-60 min. Time exit.                    |
//|                                                                    |
//| Type: #104 (Equity-close rebalancing flow)                        |
//| Target: USDJPY+ M15                                              |
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
input bool   InpEnabled        = true;
input double InpRiskPct        = 0.5;
input double InpMaxLot         = 0.50;
input int    InpMagic          = 20260414;

input group "=== Timing (Broker Time UTC+2) ==="
input int    InpEntryH         = 23;         // Entry hour (broker) — ~21:00 GMT on UTC+2
input int    InpEntryM         = 0;          // Entry minute
input int    InpHoldBars       = 4;          // Hold time in M15 bars (4 = 60 min)

input group "=== Signal ==="
input int    InpLookbackBars   = 40;         // Lookback for session direction (40 M15 bars = 10h)
input double InpMinMoveATR     = 0.3;        // Min session move (ATR fraction) to trigger
input bool   InpUseTrendFilter = false;      // D1 EMA trend filter
input int    InpEMA_Period     = 50;

input group "=== Risk Management ==="
input double InpSL_ATR_Mult    = 1.0;        // SL in ATR multiples (D1)
input int    InpMaxPerDay      = 1;
input double InpDailyDD        = 4.0;        // DD kill switch %

input group "=== Day Filter ==="
input bool   InpTradeMon       = true;
input bool   InpTradeTue       = true;
input bool   InpTradeWed       = true;
input bool   InpTradeThu       = true;
input bool   InpTradeFri       = true;

//+------------------------------------------------------------------+
//| GLOBALS                                                            |
//+------------------------------------------------------------------+
CTrade         trade;
CPositionInfo  pos;
CSymbolInfo    sym;

int            handleATR;
int            handleEMA;
double         initialBalance;
int            todayTradeCount;
datetime       lastTradeDay;
int            barsHeld;
double         pipSize;

//+------------------------------------------------------------------+
int OnInit()
{
   if(!InpEnabled) return INIT_SUCCEEDED;

   trade.SetExpertMagicNumber(InpMagic);
   trade.SetDeviationInPoints(30);
   sym.Name(_Symbol);

   pipSize = sym.Point() * 10.0;
   if(StringFind(_Symbol, "JPY") >= 0)
      pipSize = sym.Point() * 100.0;

   handleATR = iATR(_Symbol, PERIOD_D1, 14);
   handleEMA = iMA(_Symbol, PERIOD_D1, InpEMA_Period, 0, MODE_EMA, PRICE_CLOSE);

   if(handleATR == INVALID_HANDLE || handleEMA == INVALID_HANDLE)
   {
      Print("ERROR: Failed to create indicator handles");
      return INIT_FAILED;
   }

   initialBalance = AccountInfoDouble(ACCOUNT_BALANCE);
   todayTradeCount = 0;
   lastTradeDay = 0;
   barsHeld = 0;

   Print("EA_EqCloseFlow v1.0 initialized. Symbol=", _Symbol,
         " EntryH=", InpEntryH, " HoldBars=", InpHoldBars);

   return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   if(handleATR != INVALID_HANDLE) IndicatorRelease(handleATR);
   if(handleEMA != INVALID_HANDLE) IndicatorRelease(handleEMA);
}

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
bool IsEntryTime()
{
   MqlDateTime dt;
   TimeToStruct(TimeCurrent(), dt);
   return (dt.hour == InpEntryH && dt.min >= InpEntryM && dt.min < InpEntryM + 15);
}

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
//| Measure session direction over lookback                            |
//+------------------------------------------------------------------+
double GetSessionMove()
{
   // Get close of bar N bars ago vs current close (shift=1, closed bar)
   double priceNow  = iClose(_Symbol, PERIOD_M15, 1);
   double pricePast = iClose(_Symbol, PERIOD_M15, InpLookbackBars + 1);

   if(priceNow <= 0 || pricePast <= 0) return 0;

   return priceNow - pricePast;
}

//+------------------------------------------------------------------+
void OnTick()
{
   if(!InpEnabled) return;

   sym.RefreshRates();
   CheckDayReset();

   // --- Manage existing: time exit ---
   if(CountPositions() > 0)
   {
      barsHeld++;
      // Each OnTick can fire multiple times per bar, so count properly
      // Use bar-based counting via iTime
      static datetime lastBar = 0;
      datetime currentBar = iTime(_Symbol, PERIOD_M15, 0);
      if(currentBar != lastBar)
      {
         lastBar = currentBar;
         barsHeld++;
      }

      if(barsHeld >= InpHoldBars)
      {
         CloseAllPositions("TimeExit");
         barsHeld = 0;
      }
      return; // No new entries while holding
   }

   // DD kill switch
   double equity = AccountInfoDouble(ACCOUNT_EQUITY);
   if(initialBalance > 0 && equity < initialBalance * (1.0 - InpDailyDD / 100.0)) return;

   if(todayTradeCount >= InpMaxPerDay) return;
   if(!IsTradingDay()) return;
   if(!IsEntryTime()) return;

   // === CORE SIGNAL ===

   // 1. Get session move
   double sessionMove = GetSessionMove();
   if(sessionMove == 0) return;

   // 2. Get ATR for threshold and SL
   double atrArr[];
   if(CopyBuffer(handleATR, 0, 1, 1, atrArr) < 1) return;
   double atr = atrArr[0];
   if(atr <= 0) return;

   // 3. Check minimum move threshold
   if(MathAbs(sessionMove) < atr * InpMinMoveATR) return;

   // 4. Trend filter (optional)
   if(InpUseTrendFilter)
   {
      double emaArr[];
      if(CopyBuffer(handleEMA, 0, 1, 1, emaArr) < 1) return;
      double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
      // Only long if above EMA, only short if below
      if(sessionMove > 0 && bid < emaArr[0]) return;
      if(sessionMove < 0 && bid > emaArr[0]) return;
   }

   // 5. Calculate SL
   double slDistance = atr * InpSL_ATR_Mult;

   int stopLevel = (int)SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL);
   double minDist = stopLevel * sym.Point();

   // 6. Entry
   if(sessionMove > 0)
   {
      // Equities rose → rebalancing sells JPY → long USDJPY
      double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
      double slPrice = ask - slDistance;
      if(ask - slPrice < minDist) slPrice = ask - minDist - sym.Point();

      double lots = CalcLotSize(slDistance);

      bool filled = false;
      for(int attempt = 1; attempt <= 3; attempt++)
      {
         if(trade.Buy(lots, _Symbol, ask, slPrice, 0,
                       StringFormat("EqCl_B_%.0f", sessionMove / pipSize)))
         {
            filled = true;
            break;
         }
         if(attempt < 3) Sleep(200 * (int)MathPow(2, attempt - 1));
      }

      if(filled)
      {
         Print("EQ CLOSE BUY: move=", DoubleToString(sessionMove / pipSize, 1),
               " pips, ATR=", DoubleToString(atr / pipSize, 1), " lots=", lots);
         todayTradeCount++;
         barsHeld = 0;
      }
   }
   else
   {
      // Equities fell → rebalancing buys JPY → short USDJPY
      double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
      double slPrice = bid + slDistance;
      if(slPrice - bid < minDist) slPrice = bid + minDist + sym.Point();

      double lots = CalcLotSize(slDistance);

      bool filled = false;
      for(int attempt = 1; attempt <= 3; attempt++)
      {
         if(trade.Sell(lots, _Symbol, bid, slPrice, 0,
                        StringFormat("EqCl_S_%.0f", sessionMove / pipSize)))
         {
            filled = true;
            break;
         }
         if(attempt < 3) Sleep(200 * (int)MathPow(2, attempt - 1));
      }

      if(filled)
      {
         Print("EQ CLOSE SELL: move=", DoubleToString(sessionMove / pipSize, 1),
               " pips, ATR=", DoubleToString(atr / pipSize, 1), " lots=", lots);
         todayTradeCount++;
         barsHeld = 0;
      }
   }
}
//+------------------------------------------------------------------+
