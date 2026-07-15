//+------------------------------------------------------------------+
//| EA_HOLO.mq5                                                       |
//| Highest Open / Lowest Open — Mean Reversion Scalper               |
//| Copyright 2026, Max & Ngai Meo Coc                                |
//|                                                                    |
//| EDGE HYPOTHESIS:                                                   |
//| Intraday H1 opens form psychological S/R levels. When price       |
//| exceeds the highest H1 open of the day and reverses, breakout     |
//| traders are trapped → mean reversion short. Vice versa for longs. |
//|                                                                    |
//| Rules (from ForexFactory HOLO thread, 20,991 replies):            |
//| 1. Track highest & lowest H1 open prices of current trading day   |
//| 2. SHORT: price crosses above highest H1 open, then closes back   |
//|    below → sell. SL = daily high + buffer                          |
//| 3. LONG: price crosses below lowest H1 open, then closes back     |
//|    above → buy. SL = daily low - buffer                            |
//| 4. TP = 1:1 RR (original), configurable                           |
//| 5. BE management + trailing stop                                   |
//| 6. NY session focus (broker h15-21)                                |
//|                                                                    |
//| Source: forexfactory.com/thread/1357382                            |
//| S560 | Max | 2026-04-12 | v1.0                                    |
//+------------------------------------------------------------------+
#property copyright "Max & Ngai Meo Coc"
#property link      ""
#property version   "1.00"
#property strict

#include <Trade\Trade.mqh>
#include <Trade\PositionInfo.mqh>
#include <Trade\SymbolInfo.mqh>
#include <HolidayCalendar.mqh>

//+------------------------------------------------------------------+
//| INPUTS                                                             |
//+------------------------------------------------------------------+
input group "=== Core ==="
input bool   InpEnabled        = true;
input double InpRiskPct        = 1.0;       // Risk % per trade
input double InpMaxLot         = 2.00;      // Max lot
input int    InpMagic          = 20260412;
input string InpComment        = "HOLO";

// --- Session ---
input group "=== Session Window ==="
input int    InpSessionStartH  = 15;        // NY entry start (broker time)
input int    InpSessionStartM  = 0;
input int    InpSessionEndH    = 21;        // NY entry end
input int    InpSessionEndM    = 0;
input bool   InpCloseEOD       = true;      // Close all at session end
input int    InpCloseH         = 21;        // EOD close hour
input int    InpCloseM         = 30;        // EOD close minute

// --- HOLO Levels ---
input group "=== HOLO Levels ==="
input int    InpMinH1Bars      = 3;         // Min H1 bars before trading (enough data)
input double InpMinRangePts    = 0;         // Min high-low open range (0=auto via ATR)
input double InpATR_RangeMult  = 0.15;      // Min range as ATR multiple if auto
input bool   InpSkipYestBreak  = false;     // Skip if price breaks yesterday high/low

// --- Entry ---
input group "=== Entry ==="
input bool   InpAllowLong      = true;      // Allow long trades
input bool   InpAllowShort     = true;      // Allow short trades
input int    InpMaxSpreadPts   = 0;         // Max spread filter (0=off)
input double InpEntryBuffer    = 0.0;       // Buffer beyond HOLO level (points)

// --- Risk ---
input group "=== Risk Management ==="
input double InpRR_Ratio       = 1.0;       // Risk:Reward ratio
input double InpSL_Buffer      = 100;       // SL buffer above daily H/L (points)
input double InpMinSL_Pts      = 200;       // Min SL distance (points)
input double InpMaxSL_Pts      = 5000;      // Max SL distance (points)
input int    InpMaxTradesDay   = 4;         // Max trades per day
input double InpMaxDDPct       = 10.0;      // Max DD kill switch %

// --- Trade Management ---
input group "=== BE & Trailing ==="
input bool   InpUseBE          = true;
input double InpBE_Activate    = 500;       // BE activation (points profit)
input double InpBE_Lock        = 100;       // BE lock (points above entry)
input bool   InpUseTrail       = true;
input double InpTrailActivate  = 1000;      // Trail activation (points)
input double InpTrailStep      = 300;       // Trail step (points)

// --- Day Filter ---
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

int            handleATR_D1;
double         initialBalance;

// Daily state
datetime       lastTradeDay;
int            tradesToday;
bool           crossedAboveHigh;  // Price crossed above highest H1 open
bool           crossedBelowLow;   // Price crossed below lowest H1 open
bool           shortEnteredToday;
bool           longEnteredToday;

//+------------------------------------------------------------------+
//| Init                                                               |
//+------------------------------------------------------------------+
int OnInit()
{
   if(!InpEnabled) return INIT_SUCCEEDED;

   trade.SetExpertMagicNumber(InpMagic);
   sym.Name(_Symbol);

   // Detect fill type
   long fillFlags = SymbolInfoInteger(_Symbol, SYMBOL_FILLING_MODE);
   if((fillFlags & SYMBOL_FILLING_FOK) != 0)
      trade.SetTypeFilling(ORDER_FILLING_FOK);
   else if((fillFlags & SYMBOL_FILLING_IOC) != 0)
      trade.SetTypeFilling(ORDER_FILLING_IOC);
   else
      trade.SetTypeFilling(ORDER_FILLING_RETURN);

   handleATR_D1 = iATR(_Symbol, PERIOD_D1, 14);
   if(handleATR_D1 == INVALID_HANDLE)
   {
      Print("ERROR: ATR handle creation failed");
      return INIT_FAILED;
   }

   initialBalance = AccountInfoDouble(ACCOUNT_BALANCE);
   lastTradeDay = 0;
   tradesToday = 0;
   crossedAboveHigh = false;
   crossedBelowLow = false;
   shortEnteredToday = false;
   longEnteredToday = false;

   Print("EA_HOLO v1.0 initialized on ", _Symbol, " ", EnumToString(_Period));
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   if(handleATR_D1 != INVALID_HANDLE) IndicatorRelease(handleATR_D1);
}

//+------------------------------------------------------------------+
//| Helpers                                                            |
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

int CountMyPositions()
{
   int c = 0;
   for(int i = PositionsTotal()-1; i >= 0; i--)
      if(pos.SelectByIndex(i) && pos.Magic() == InpMagic && pos.Symbol() == _Symbol) c++;
   return c;
}

void CloseAll(string reason)
{
   for(int i = PositionsTotal()-1; i >= 0; i--)
   {
      if(pos.SelectByIndex(i) && pos.Magic() == InpMagic && pos.Symbol() == _Symbol)
      {
         trade.PositionClose(pos.Ticket());
         Print("CLOSE [", reason, "] ticket=", pos.Ticket(), " profit=", pos.Profit());
      }
   }
}

double CalcLotSize(double slPoints)
{
   sym.RefreshRates();
   double riskMoney = AccountInfoDouble(ACCOUNT_BALANCE) * InpRiskPct / 100.0;
   double tickVal   = sym.TickValue();
   double tickSize  = sym.TickSize();
   if(tickVal <= 0 || tickSize <= 0) return sym.LotsMin();

   double slMoney = slPoints * sym.Point() * tickVal / tickSize;
   if(slMoney <= 0) return sym.LotsMin();

   double lots = riskMoney / slMoney;
   lots = MathMin(lots, InpMaxLot);
   lots = MathMax(lots, sym.LotsMin());
   lots = NormalizeDouble(MathFloor(lots / sym.LotsStep()) * sym.LotsStep(), 2);
   return lots;
}

//+------------------------------------------------------------------+
//| Calculate HOLO levels: highest & lowest H1 opens today            |
//+------------------------------------------------------------------+
bool CalcHOLO(double &highestOpen, double &lowestOpen, int &barCount)
{
   MqlDateTime dtNow;
   TimeToStruct(TimeCurrent(), dtNow);
   int todayDOY = dtNow.day_of_year;

   highestOpen = -DBL_MAX;
   lowestOpen  =  DBL_MAX;
   barCount    = 0;

   // Scan H1 bars from today
   for(int i = 0; i < 50; i++)
   {
      datetime barTime = iTime(_Symbol, PERIOD_H1, i);
      if(barTime == 0) break;

      MqlDateTime dtBar;
      TimeToStruct(barTime, dtBar);
      if(dtBar.day_of_year != todayDOY || dtBar.year != dtNow.year) break;

      double openPrice = iOpen(_Symbol, PERIOD_H1, i);
      if(openPrice > highestOpen) highestOpen = openPrice;
      if(openPrice < lowestOpen)  lowestOpen  = openPrice;
      barCount++;
   }

   return (barCount >= InpMinH1Bars && highestOpen > lowestOpen);
}

//+------------------------------------------------------------------+
//| Check cross above/below with lookback on M15 bars today           |
//+------------------------------------------------------------------+
bool CheckCrossAbove(double level)
{
   // Check if any M15 bar today closed above the level
   MqlDateTime dtNow;
   TimeToStruct(TimeCurrent(), dtNow);
   int todayDOY = dtNow.day_of_year;

   for(int i = 1; i < 100; i++)
   {
      datetime barTime = iTime(_Symbol, _Period, i);
      if(barTime == 0) break;

      MqlDateTime dtBar;
      TimeToStruct(barTime, dtBar);
      if(dtBar.day_of_year != todayDOY || dtBar.year != dtNow.year) break;

      if(iClose(_Symbol, _Period, i) > level + InpEntryBuffer)
         return true;
   }
   return false;
}

bool CheckCrossBelowLevel(double level)
{
   MqlDateTime dtNow;
   TimeToStruct(TimeCurrent(), dtNow);
   int todayDOY = dtNow.day_of_year;

   for(int i = 1; i < 100; i++)
   {
      datetime barTime = iTime(_Symbol, _Period, i);
      if(barTime == 0) break;

      MqlDateTime dtBar;
      TimeToStruct(barTime, dtBar);
      if(dtBar.day_of_year != todayDOY || dtBar.year != dtNow.year) break;

      if(iClose(_Symbol, _Period, i) < level - InpEntryBuffer)
         return true;
   }
   return false;
}

//+------------------------------------------------------------------+
//| Manage open positions: BE + Trail                                  |
//+------------------------------------------------------------------+
void ManagePositions()
{
   for(int i = PositionsTotal()-1; i >= 0; i--)
   {
      if(!pos.SelectByIndex(i)) continue;
      if(pos.Magic() != InpMagic || pos.Symbol() != _Symbol) continue;

      double openPrice = pos.PriceOpen();
      double curSL     = pos.StopLoss();
      double curTP     = pos.TakeProfit();
      double point     = sym.Point();

      if(pos.PositionType() == POSITION_TYPE_BUY)
      {
         double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
         double profitPts = (bid - openPrice) / point;

         // BE
         if(InpUseBE && profitPts >= InpBE_Activate)
         {
            double beSL = openPrice + InpBE_Lock * point;
            if(curSL < beSL)
               trade.PositionModify(pos.Ticket(), beSL, curTP);
         }

         // Trail
         if(InpUseTrail && profitPts >= InpTrailActivate)
         {
            double trailSL = bid - InpTrailStep * point;
            if(trailSL > curSL)
               trade.PositionModify(pos.Ticket(), trailSL, curTP);
         }
      }
      else // SELL
      {
         double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
         double profitPts = (openPrice - ask) / point;

         // BE
         if(InpUseBE && profitPts >= InpBE_Activate)
         {
            double beSL = openPrice - InpBE_Lock * point;
            if(curSL == 0 || curSL > beSL)
               trade.PositionModify(pos.Ticket(), beSL, curTP);
         }

         // Trail
         if(InpUseTrail && profitPts >= InpTrailActivate)
         {
            double trailSL = ask + InpTrailStep * point;
            if(curSL == 0 || trailSL < curSL)
               trade.PositionModify(pos.Ticket(), trailSL, curTP);
         }
      }
   }
}

//+------------------------------------------------------------------+
//| OnTick                                                             |
//+------------------------------------------------------------------+
void OnTick()
{
   if(!InpEnabled) return;
   if(IsMarketHoliday()) return;
   sym.RefreshRates();

   // Day reset
   MqlDateTime dt;
   TimeToStruct(TimeCurrent(), dt);
   datetime today = StringToTime(StringFormat("%04d.%02d.%02d", dt.year, dt.mon, dt.day));
   if(today != lastTradeDay)
   {
      lastTradeDay      = today;
      tradesToday       = 0;
      crossedAboveHigh  = false;
      crossedBelowLow   = false;
      shortEnteredToday = false;
      longEnteredToday  = false;
   }

   // New bar gate
   static datetime lastBar = 0;
   datetime curBar = iTime(_Symbol, _Period, 0);
   if(curBar == lastBar) return;
   lastBar = curBar;

   // Manage open positions (BE/Trail)
   if(CountMyPositions() > 0)
      ManagePositions();

   // EOD close
   int h = dt.hour, m = dt.min;
   int nowMins = h * 60 + m;
   if(InpCloseEOD && nowMins >= InpCloseH * 60 + InpCloseM)
   {
      if(CountMyPositions() > 0)
         CloseAll("EOD");
      return;
   }

   if(!IsTradingDay()) return;

   // DD kill switch
   double equity = AccountInfoDouble(ACCOUNT_EQUITY);
   if(initialBalance > 0 && equity < initialBalance * (1.0 - InpMaxDDPct / 100.0))
   {
      if(CountMyPositions() > 0) CloseAll("DD_Kill");
      return;
   }

   // Session window check
   int sessStart = InpSessionStartH * 60 + InpSessionStartM;
   int sessEnd   = InpSessionEndH * 60 + InpSessionEndM;
   if(nowMins < sessStart || nowMins >= sessEnd) return;

   // Max trades check
   if(tradesToday >= InpMaxTradesDay) return;
   if(CountMyPositions() > 0) return;

   // Spread check
   if(InpMaxSpreadPts > 0)
   {
      int curSpread = (int)SymbolInfoInteger(_Symbol, SYMBOL_SPREAD);
      if(curSpread > InpMaxSpreadPts) return;
   }

   // --- Calculate HOLO levels ---
   double highOpen, lowOpen;
   int h1Count;
   if(!CalcHOLO(highOpen, lowOpen, h1Count)) return;

   // Min range filter
   double atr[];
   if(CopyBuffer(handleATR_D1, 0, 1, 1, atr) < 1) return;
   double minRange = InpMinRangePts > 0 ? InpMinRangePts * sym.Point() : atr[0] * InpATR_RangeMult;
   if((highOpen - lowOpen) < minRange) return;

   // Get daily H/L for SL
   double dailyHigh = iHigh(_Symbol, PERIOD_D1, 0);
   double dailyLow  = iLow(_Symbol, PERIOD_D1, 0);

   // Yesterday's H/L for skip filter
   double yesterHigh = iHigh(_Symbol, PERIOD_D1, 1);
   double yesterLow  = iLow(_Symbol, PERIOD_D1, 1);

   double close1 = iClose(_Symbol, _Period, 1);
   double point  = sym.Point();

   // --- SHORT SETUP ---
   // Cross detected: any M15 bar today closed above highest H1 open
   // Entry: last closed M15 bar closes back below (or at) highest H1 open
   if(InpAllowShort && !shortEnteredToday)
   {
      bool hasCrossAbove = CheckCrossAbove(highOpen);

      if(hasCrossAbove && close1 <= highOpen)
      {
         // Skip if breaking yesterday high (optional breakout filter)
         if(InpSkipYestBreak && dailyHigh > yesterHigh) {
            Print("HOLO SKIP short: breaking yesterday high");
         }
         else
         {
            double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
            double sl  = dailyHigh + InpSL_Buffer * point;
            double slDist = (sl - bid) / point;

            if(slDist >= InpMinSL_Pts && slDist <= InpMaxSL_Pts)
            {
               // Stop level check
               int stopLevel = (int)SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL);
               double minDist = stopLevel * point;
               if((sl - bid) < minDist) sl = bid + minDist + 10 * point;

               double tp = bid - slDist * InpRR_Ratio * point;
               if((bid - tp) < minDist) tp = bid - minDist - 10 * point;

               double lots = CalcLotSize(slDist);

               Print("HOLO SHORT: highOpen=", highOpen, " close1=", close1,
                     " bid=", bid, " sl=", sl, " tp=", tp, " lot=", lots,
                     " H1bars=", h1Count);

               if(trade.Sell(lots, _Symbol, 0, sl, tp, InpComment + " S"))
               {
                  tradesToday++;
                  shortEnteredToday = true;
                  Print("HOLO SHORT FILLED ticket=", trade.ResultOrder());
               }
               else
                  Print("HOLO SHORT FAILED: ", trade.ResultRetcodeDescription());
            }
            else
               Print("HOLO SHORT SL out of range: ", slDist, " pts");
         }
      }
   }

   // --- LONG SETUP ---
   if(InpAllowLong && !longEnteredToday)
   {
      bool hasCrossBelow = CheckCrossBelowLevel(lowOpen);

      if(hasCrossBelow && close1 >= lowOpen)
      {
         if(InpSkipYestBreak && dailyLow < yesterLow) {
            Print("HOLO SKIP long: breaking yesterday low");
         }
         else
         {
            double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
            double sl  = dailyLow - InpSL_Buffer * point;
            double slDist = (ask - sl) / point;

            if(slDist >= InpMinSL_Pts && slDist <= InpMaxSL_Pts)
            {
               int stopLevel = (int)SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL);
               double minDist = stopLevel * point;
               if((ask - sl) < minDist) sl = ask - minDist - 10 * point;

               double tp = ask + slDist * InpRR_Ratio * point;
               if((tp - ask) < minDist) tp = ask + minDist + 10 * point;

               double lots = CalcLotSize(slDist);

               Print("HOLO LONG: lowOpen=", lowOpen, " close1=", close1,
                     " ask=", ask, " sl=", sl, " tp=", tp, " lot=", lots,
                     " H1bars=", h1Count);

               if(trade.Buy(lots, _Symbol, 0, sl, tp, InpComment + " L"))
               {
                  tradesToday++;
                  longEnteredToday = true;
                  Print("HOLO LONG FILLED ticket=", trade.ResultOrder());
               }
               else
                  Print("HOLO LONG FAILED: ", trade.ResultRetcodeDescription());
            }
            else
               Print("HOLO LONG SL out of range: ", slDist, " pts");
         }
      }
   }
}
//+------------------------------------------------------------------+
