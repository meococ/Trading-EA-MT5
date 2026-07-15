//+------------------------------------------------------------------+
//| EA_Gotobi.mq5                                                    |
//| Tokyo Fix Gotobi Calendar Strategy                                |
//| Copyright 2026, Max & Ngai Meo Coc                                |
//|                                                                    |
//| EDGE HYPOTHESIS:                                                  |
//| Japanese importers buy USD on "Gotobi" days (5/10/15/20/25/30)   |
//| to settle international payments. This creates predictable        |
//| USDJPY upward pressure from early Tokyo → 9:55 JST fix.          |
//| Academic validation: arXiv:2301.13204, p < 0.05                   |
//|                                                                    |
//| STRATEGY A: Buy early Tokyo morning, exit before 9:55 JST fix.   |
//| STRATEGY B: Fade post-fix reversal (short after 9:55 JST).       |
//|                                                                    |
//| Target: USDJPY M15. ~72 trades/year (6/month × 12).              |
//| Max | 2026-03-30 | v1.0                                          |
//+------------------------------------------------------------------+
#property copyright "Max & Ngai Meo Coc"
#property link      ""
#property version   "1.00"
#property strict

#include <Trade\Trade.mqh>
#include <Trade\PositionInfo.mqh>
#include <Trade\SymbolInfo.mqh>
#include <ExecQualityLog.mqh>
#include <HolidayCalendar.mqh>

//+------------------------------------------------------------------+
//| INPUTS                                                             |
//+------------------------------------------------------------------+
input group "=== Core Settings ==="
input bool   InpEnabled        = true;       // EA Enabled
input double InpRiskPct        = 1.0;        // Risk % per trade
input double InpMaxLot         = 1.00;       // Max lot size
input int    InpMagic          = 20260401;   // Magic number
input string InpComment        = "Gotobi";   // Trade comment

// --- Strategy Mode ---
input group "=== Strategy Mode ==="
input bool   InpModeA          = true;       // Strategy A: Buy approach to fix
input bool   InpModeB          = false;      // Strategy B: Fade post-fix reversal

// --- Gotobi Calendar ---
input group "=== Gotobi Calendar ==="
input bool   InpGotobi5        = true;       // Trade on 5th
input bool   InpGotobi10       = true;       // Trade on 10th
input bool   InpGotobi15       = true;       // Trade on 15th
input bool   InpGotobi20       = true;       // Trade on 20th
input bool   InpGotobi25       = true;       // Trade on 25th
input bool   InpGotobi30       = true;       // Trade on 30th (EOM)
input bool   InpShiftWeekend   = true;       // If Gotobi falls on weekend → shift to Friday

// --- Timing (Broker time — will be converted from JST) ---
input group "=== Timing (Broker Time) ==="
input int    InpJST_Offset     = 7;          // JST offset from broker time (JST = broker + offset)
                                              // MetaQuotes UTC+2: offset=7, UTC+3(DST): offset=6
// Strategy A timing
input int    InpEntryA_H       = 20;         // Strategy A entry hour (broker, ~3AM JST)
input int    InpEntryA_M       = 0;          // Strategy A entry minute
input int    InpExitA_H        = 1;          // Strategy A exit hour (broker, ~8:55-9:55 JST)
input int    InpExitA_M        = 0;          // Strategy A exit minute (0:55 broker = 7:55 JST for UTC+2)
// Strategy B timing
input int    InpEntryB_H       = 1;          // Strategy B entry hour (broker, ~10:00 JST = 1:00 UTC+2)
input int    InpEntryB_M       = 5;          // Strategy B entry minute (5 min after fix)
input int    InpExitB_H        = 2;          // Strategy B exit hour (max hold 60 min)
input int    InpExitB_M        = 5;          // Strategy B exit minute

// --- SL/TP ---
input group "=== Risk Management ==="
input double InpSL_Pips        = 20.0;       // Stop Loss (pips)
input double InpTP_Pips        = 30.0;       // Take Profit (pips) for Strategy A
input double InpTP_B_Pips      = 15.0;       // Take Profit (pips) for Strategy B
input double InpMinMovePips    = 15.0;       // Strategy B: Min morning rise to trigger fade (pips)
input bool   InpUseBE          = false;      // Use break-even stop
input double InpBE_Trigger     = 1.0;        // BE trigger (R multiples)

// --- Filters ---
input group "=== Filters ==="
input bool   InpUseATRFilter   = false;      // ATR filter (skip low-vol days)
input int    InpATR_Period     = 14;         // ATR period
input double InpATR_MinPips    = 40.0;       // Min D1 ATR to trade (pips)
input bool   InpUseEMAFilter   = false;      // D1 EMA bias (buy only above EMA)
input int    InpEMA_Period     = 50;         // D1 EMA period
input double InpMaxDDPct       = 99.0;       // Max DD% kill switch

// --- Day Filter ---
input group "=== Day Filter ==="
input bool   InpTradeMon       = true;       // Trade Monday
input bool   InpTradeTue       = true;       // Trade Tuesday
input bool   InpTradeWed       = true;       // Trade Wednesday
input bool   InpTradeThu       = true;       // Trade Thursday
input bool   InpTradeFri       = true;       // Trade Friday

//+------------------------------------------------------------------+
//| GLOBALS                                                            |
//+------------------------------------------------------------------+
CTrade         trade;
CPositionInfo  pos;
CSymbolInfo    sym;

int            handleATR_D1;
int            handleEMA_D1;
double         initialBalance;
int            todayTradeCount;
datetime       lastTradeDay;
bool           entryDoneA;
bool           entryDoneB;

//+------------------------------------------------------------------+
//| Expert initialization                                              |
//+------------------------------------------------------------------+
int OnInit()
{
   if(!InpEnabled) return INIT_SUCCEEDED;

   trade.SetExpertMagicNumber(InpMagic);
   sym.Name(_Symbol);

   // Indicator handles
   handleATR_D1 = iATR(_Symbol, PERIOD_D1, InpATR_Period);
   handleEMA_D1 = iMA(_Symbol, PERIOD_D1, InpEMA_Period, 0, MODE_EMA, PRICE_CLOSE);

   if(handleATR_D1 == INVALID_HANDLE || handleEMA_D1 == INVALID_HANDLE)
   {
      Print("ERROR: Failed to create indicator handles");
      return INIT_FAILED;
   }

   initialBalance = AccountInfoDouble(ACCOUNT_BALANCE);
   todayTradeCount = 0;
   lastTradeDay = 0;
   entryDoneA = false;
   entryDoneB = false;

   double gotPipSize = sym.Point() * 10.0;
   if(StringFind(_Symbol, "JPY") >= 0) gotPipSize = sym.Point() * 100.0;
   EQL_Init("EA_Gotobi", InpMagic, "GOT", gotPipSize, true);

   Print("EA_Gotobi v1.0 initialized. Symbol=", _Symbol,
         " ModeA=", InpModeA, " ModeB=", InpModeB,
         " JST_Offset=", InpJST_Offset);

   return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
//| Expert deinitialization                                            |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   if(handleATR_D1 != INVALID_HANDLE) IndicatorRelease(handleATR_D1);
   if(handleEMA_D1 != INVALID_HANDLE) IndicatorRelease(handleEMA_D1);
}

//+------------------------------------------------------------------+
//| Check if today is a Gotobi day                                     |
//+------------------------------------------------------------------+
bool IsGotobiDay()
{
   MqlDateTime dt;
   TimeToStruct(TimeCurrent(), dt);

   int dom = dt.day;        // day of month
   int dow = dt.day_of_week; // 0=Sun, 1=Mon, ..., 6=Sat

   // Direct Gotobi day check
   bool isGotobi = false;
   if(dom == 5  && InpGotobi5)  isGotobi = true;
   if(dom == 10 && InpGotobi10) isGotobi = true;
   if(dom == 15 && InpGotobi15) isGotobi = true;
   if(dom == 20 && InpGotobi20) isGotobi = true;
   if(dom == 25 && InpGotobi25) isGotobi = true;
   if(dom == 30 && InpGotobi30) isGotobi = true;

   // Weekend shift: if Gotobi falls on Sat/Sun → Friday before is the effective day
   if(InpShiftWeekend && !isGotobi)
   {
      // Today is Friday (dow=5), check if tomorrow (Sat) or day-after (Sun) is Gotobi
      if(dow == 5)
      {
         int tomorrow = dom + 1;
         int dayAfter = dom + 2;

         // Handle month overflow (approximate — exact last-day varies by month)
         if((tomorrow == 5  && InpGotobi5)  || (dayAfter == 5  && InpGotobi5))  isGotobi = true;
         if((tomorrow == 10 && InpGotobi10) || (dayAfter == 10 && InpGotobi10)) isGotobi = true;
         if((tomorrow == 15 && InpGotobi15) || (dayAfter == 15 && InpGotobi15)) isGotobi = true;
         if((tomorrow == 20 && InpGotobi20) || (dayAfter == 20 && InpGotobi20)) isGotobi = true;
         if((tomorrow == 25 && InpGotobi25) || (dayAfter == 25 && InpGotobi25)) isGotobi = true;
         if((tomorrow == 30 && InpGotobi30) || (dayAfter == 30 && InpGotobi30)) isGotobi = true;
      }
   }

   return isGotobi;
}

//+------------------------------------------------------------------+
//| Check day-of-week filter                                           |
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
//| Get current broker hour and minute                                 |
//+------------------------------------------------------------------+
void GetBrokerTime(int &hour, int &minute)
{
   MqlDateTime dt;
   TimeToStruct(TimeCurrent(), dt);
   hour = dt.hour;
   minute = dt.min;
}

//+------------------------------------------------------------------+
//| Check time window                                                  |
//+------------------------------------------------------------------+
bool InTimeWindow(int startH, int startM, int endH, int endM)
{
   int h, m;
   GetBrokerTime(h, m);

   int now   = h * 60 + m;
   int start = startH * 60 + startM;
   int end   = endH * 60 + endM;

   // Handle overnight (e.g., entry at 20:00, exit at 01:00)
   if(start > end)
      return (now >= start || now < end);
   else
      return (now >= start && now < end);
}

//+------------------------------------------------------------------+
//| Check if we should enter Strategy A (at entry time)                |
//+------------------------------------------------------------------+
bool IsEntryTimeA()
{
   int h, m;
   GetBrokerTime(h, m);

   // Check if we're at entry hour/minute (first bar of the hour)
   return (h == InpEntryA_H && m >= InpEntryA_M && m < InpEntryA_M + 15);
}

//+------------------------------------------------------------------+
//| Check if we should exit Strategy A (at exit time)                  |
//+------------------------------------------------------------------+
bool IsExitTimeA()
{
   int h, m;
   GetBrokerTime(h, m);
   return (h == InpExitA_H && m >= InpExitA_M);
}

//+------------------------------------------------------------------+
//| Check if we should enter Strategy B (post-fix fade)                |
//+------------------------------------------------------------------+
bool IsEntryTimeB()
{
   int h, m;
   GetBrokerTime(h, m);
   return (h == InpEntryB_H && m >= InpEntryB_M && m < InpEntryB_M + 15);
}

//+------------------------------------------------------------------+
//| Check if we should exit Strategy B                                 |
//+------------------------------------------------------------------+
bool IsExitTimeB()
{
   int h, m;
   GetBrokerTime(h, m);
   return (h >= InpExitB_H && m >= InpExitB_M);
}

//+------------------------------------------------------------------+
//| Calculate morning rise (for Strategy B filter)                     |
//+------------------------------------------------------------------+
double CalcMorningRise()
{
   // Calculate price rise from entry A time to now
   // Look back to find the bar at entry A time
   double pipSize = sym.Point() * 10.0;  // For 5-digit pairs
   if(StringFind(_Symbol, "JPY") >= 0)
      pipSize = sym.Point() * 100.0;     // JPY pairs

   // Get current price and price at start of session
   double currentBid = SymbolInfoDouble(_Symbol, SYMBOL_BID);

   // Find price at approximately entry A time (look back several bars)
   int barsBack = (int)MathCeil((double)(InpEntryB_H * 60 + InpEntryB_M - InpEntryA_H * 60 - InpEntryA_M) / PeriodSeconds() * 60);
   if(barsBack < 1) barsBack = 20; // fallback for overnight
   if(barsBack > 100) barsBack = 100;

   double openPrice = iOpen(_Symbol, PERIOD_M15, barsBack);

   double risePips = (currentBid - openPrice) / pipSize;
   return risePips;
}

//+------------------------------------------------------------------+
//| Position sizing                                                    |
//+------------------------------------------------------------------+
double CalcLotSize(double slPips)
{
   sym.RefreshRates();

   double balance = AccountInfoDouble(ACCOUNT_BALANCE);
   double riskMoney = balance * InpRiskPct / 100.0;

   double tickVal  = sym.TickValue();
   double tickSize = sym.TickSize();
   double point    = sym.Point();

   if(tickVal <= 0 || tickSize <= 0) return sym.LotsMin();

   double pipValue = tickVal / tickSize * point * 10.0;
   if(StringFind(_Symbol, "JPY") >= 0)
      pipValue = tickVal / tickSize * point * 100.0;

   if(pipValue <= 0) return sym.LotsMin();

   double lots = riskMoney / (slPips * pipValue);
   lots = MathMin(lots, InpMaxLot);
   lots = MathMax(lots, sym.LotsMin());
   lots = NormalizeDouble(lots / sym.LotsStep(), 0) * sym.LotsStep();

   return lots;
}

//+------------------------------------------------------------------+
//| Check filters                                                      |
//+------------------------------------------------------------------+
bool PassFilters()
{
   // DD Kill switch
   double balance = AccountInfoDouble(ACCOUNT_BALANCE);
   double equity  = AccountInfoDouble(ACCOUNT_EQUITY);
   if(initialBalance > 0 && equity < initialBalance * (1.0 - InpMaxDDPct / 100.0))
   {
      Print("KILL SWITCH: DD exceeded ", InpMaxDDPct, "%");
      return false;
   }

   // ATR filter
   if(InpUseATRFilter)
   {
      double atr[];
      if(CopyBuffer(handleATR_D1, 0, 1, 1, atr) < 1) return false;

      double pipSize = sym.Point() * 10.0;
      if(StringFind(_Symbol, "JPY") >= 0) pipSize = sym.Point() * 100.0;

      double atrPips = atr[0] / pipSize;
      if(atrPips < InpATR_MinPips)
      {
         return false;
      }
   }

   // EMA filter (D1 — buy only above EMA for Strategy A)
   if(InpUseEMAFilter && InpModeA)
   {
      double ema[];
      if(CopyBuffer(handleEMA_D1, 0, 1, 1, ema) < 1) return false;

      double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
      if(bid < ema[0])
      {
         return false; // Don't buy below D1 EMA
      }
   }

   return true;
}

//+------------------------------------------------------------------+
//| Count open positions with our magic                                |
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
//| Close all positions with our magic                                 |
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
            Print("CLOSE [", reason, "] ticket=", pos.Ticket(),
                  " profit=", pos.Profit());
         }
      }
   }
}

//+------------------------------------------------------------------+
//| Manage break-even                                                  |
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
      double currentPrice = (pos.PositionType() == POSITION_TYPE_BUY) ?
                             SymbolInfoDouble(_Symbol, SYMBOL_BID) :
                             SymbolInfoDouble(_Symbol, SYMBOL_ASK);

      double slDist = MathAbs(openPrice - sl);
      double profit = (pos.PositionType() == POSITION_TYPE_BUY) ?
                       (currentPrice - openPrice) : (openPrice - currentPrice);

      // Move to BE if profit >= trigger × SL distance
      if(profit >= slDist * InpBE_Trigger && sl != openPrice)
      {
         double newSL = openPrice + sym.Spread() * sym.Point(); // BE + spread
         if(pos.PositionType() == POSITION_TYPE_BUY && newSL > sl)
            trade.PositionModify(pos.Ticket(), newSL, pos.TakeProfit());
         else if(pos.PositionType() == POSITION_TYPE_SELL && (sl == 0 || newSL < sl))
            trade.PositionModify(pos.Ticket(), newSL, pos.TakeProfit());
      }
   }
}

//+------------------------------------------------------------------+
//| Reset daily flags                                                  |
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
      entryDoneA = false;
      entryDoneB = false;
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

   if(IsMarketHoliday()) return;

   // Manage existing positions
   ManageBE();

   // Check if today is Gotobi day
   if(!IsGotobiDay()) return;

   // Check day-of-week filter
   if(!IsTradingDay()) return;

   // --- Strategy A: Buy approach to fix ---
   if(InpModeA && !entryDoneA)
   {
      // Time to enter?
      if(IsEntryTimeA() && CountPositions() == 0)
      {
         if(!PassFilters()) return;

         double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);

         double pipSize = sym.Point() * 10.0;
         if(StringFind(_Symbol, "JPY") >= 0) pipSize = sym.Point() * 100.0;

         double slPrice = ask - InpSL_Pips * pipSize;
         double tpPrice = ask + InpTP_Pips * pipSize;

         // Check stop/freeze level
         int stopLevel = (int)SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL);
         double minDist = stopLevel * sym.Point();
         if(MathAbs(ask - slPrice) < minDist) slPrice = ask - minDist - sym.Point();
         if(MathAbs(tpPrice - ask) < minDist) tpPrice = ask + minDist + sym.Point();

         double lots = CalcLotSize(InpSL_Pips);

         double spreadPips = (sym.Ask() - sym.Bid()) / (sym.Point() * 10.0);
         if(StringFind(_Symbol, "JPY") >= 0) spreadPips = (sym.Ask() - sym.Bid()) / (sym.Point() * 100.0);
         EQL_SetContext(ask, spreadPips, "TOKYO");

         bool filled = false;
         uint retcode = 0;
         for(int attempt = 1; attempt <= 3; attempt++)
         {
            if(trade.Buy(lots, _Symbol, ask, slPrice, tpPrice,
                          InpComment + "_A_" + IntegerToString(MqlDateTime().day)))
            {
               retcode = trade.ResultRetcode();
               EQL_RecordFill(retcode);
               filled = true;
               break;
            }
            retcode = trade.ResultRetcode();
            EQL_RecordRetry(retcode);
            if(attempt < 3) Sleep(200 * (int)MathPow(2, attempt - 1));
         }

         if(filled)
         {
            Print("GOTOBI BUY [Strategy A] lots=", lots,
                  " price=", ask, " sl=", slPrice, " tp=", tpPrice,
                  " day=", TimeToString(TimeCurrent(), TIME_DATE));
            entryDoneA = true;
            todayTradeCount++;
         }
      }
   }

   // Time-based exit for Strategy A
   if(InpModeA && CountPositions() > 0 && IsExitTimeA())
   {
      // Check if position is from Strategy A
      for(int i = PositionsTotal() - 1; i >= 0; i--)
      {
         if(!pos.SelectByIndex(i)) continue;
         if(pos.Magic() != InpMagic || pos.Symbol() != _Symbol) continue;
         if(StringFind(pos.Comment(), "_A_") >= 0)
         {
            CloseAllPositions("TimeExit_A_Fix");
            break;
         }
      }
   }

   // --- Strategy B: Fade post-fix reversal ---
   if(InpModeB && !entryDoneB)
   {
      if(IsEntryTimeB() && CountPositions() == 0)
      {
         if(!PassFilters()) return;

         // Check morning rise requirement
         double morningRise = CalcMorningRise();
         if(morningRise < InpMinMovePips)
         {
            return; // Not enough upward pressure → no fade
         }

         double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);

         double pipSize = sym.Point() * 10.0;
         if(StringFind(_Symbol, "JPY") >= 0) pipSize = sym.Point() * 100.0;

         double slPrice = bid + InpSL_Pips * pipSize;
         double tpPrice = bid - InpTP_B_Pips * pipSize;

         // Check stop/freeze level
         int stopLevel = (int)SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL);
         double minDist = stopLevel * sym.Point();
         if(MathAbs(slPrice - bid) < minDist) slPrice = bid + minDist + sym.Point();
         if(MathAbs(bid - tpPrice) < minDist) tpPrice = bid - minDist - sym.Point();

         double lots = CalcLotSize(InpSL_Pips);

         double spreadPipsB = (sym.Ask() - sym.Bid()) / (sym.Point() * 10.0);
         if(StringFind(_Symbol, "JPY") >= 0) spreadPipsB = (sym.Ask() - sym.Bid()) / (sym.Point() * 100.0);
         EQL_SetContext(bid, spreadPipsB, "TOKYO");

         bool filledB = false;
         uint retcodeB = 0;
         for(int attempt = 1; attempt <= 3; attempt++)
         {
            if(trade.Sell(lots, _Symbol, bid, slPrice, tpPrice,
                           InpComment + "_B_" + IntegerToString(MqlDateTime().day)))
            {
               retcodeB = trade.ResultRetcode();
               EQL_RecordFill(retcodeB);
               filledB = true;
               break;
            }
            retcodeB = trade.ResultRetcode();
            EQL_RecordRetry(retcodeB);
            if(attempt < 3) Sleep(200 * (int)MathPow(2, attempt - 1));
         }

         if(filledB)
         {
            Print("GOTOBI SELL [Strategy B: Fade Fix] lots=", lots,
                  " price=", bid, " sl=", slPrice, " tp=", tpPrice,
                  " morningRise=", morningRise, " pips",
                  " day=", TimeToString(TimeCurrent(), TIME_DATE));
            entryDoneB = true;
            todayTradeCount++;
         }
      }
   }

   // Time-based exit for Strategy B
   if(InpModeB && CountPositions() > 0 && IsExitTimeB())
   {
      for(int i = PositionsTotal() - 1; i >= 0; i--)
      {
         if(!pos.SelectByIndex(i)) continue;
         if(pos.Magic() != InpMagic || pos.Symbol() != _Symbol) continue;
         if(StringFind(pos.Comment(), "_B_") >= 0)
         {
            CloseAllPositions("TimeExit_B_PostFix");
            break;
         }
      }
   }
}

//+------------------------------------------------------------------+
//| MqlDateTime helper — get day field                                 |
//+------------------------------------------------------------------+
int MqlDateTimeDay()
{
   MqlDateTime dt;
   TimeToStruct(TimeCurrent(), dt);
   return dt.day;
}

//+------------------------------------------------------------------+
//| Trade transaction handler — EQL deal capture                      |
//+------------------------------------------------------------------+
void OnTradeTransaction(const MqlTradeTransaction& trans,
                        const MqlTradeRequest& request,
                        const MqlTradeResult& result)
{
   if(trans.type != TRADE_TRANSACTION_DEAL_ADD) return;
   if(trans.deal == 0) return;
   if(!HistoryDealSelect(trans.deal)) return;
   if((long)HistoryDealGetInteger(trans.deal, DEAL_MAGIC) != InpMagic) return;
   EQL_OnDeal(trans.deal);
}
//+------------------------------------------------------------------+
