//+------------------------------------------------------------------+
//| Portfolio_Common.mqh — Shared Utilities for EA_Portfolio          |
//| Lot sizing, position counting, session helpers                    |
//| Max | 2026-04-05                                                 |
//+------------------------------------------------------------------+
#ifndef PORTFOLIO_COMMON_MQH
#define PORTFOLIO_COMMON_MQH

#include <Trade\Trade.mqh>
#include <Trade\PositionInfo.mqh>
#include <Trade\SymbolInfo.mqh>

//--- Shared trade object
CTrade         PF_Trade;
CPositionInfo  PF_Pos;

//+------------------------------------------------------------------+
//| Lot sizing — symbol-aware                                        |
//+------------------------------------------------------------------+
double PF_CalcLotSize(string symbol, double riskPct, double slPoints, double maxLot)
{
   if(slPoints <= 0) return 0;
   double balance  = AccountInfoDouble(ACCOUNT_BALANCE);
   double riskAmt  = balance * riskPct / 100.0;
   double tickSize = SymbolInfoDouble(symbol, SYMBOL_TRADE_TICK_SIZE);
   double tickVal  = SymbolInfoDouble(symbol, SYMBOL_TRADE_TICK_VALUE);
   double point    = SymbolInfoDouble(symbol, SYMBOL_POINT);
   if(tickSize <= 0 || tickVal <= 0 || point <= 0) return 0;
   double pointVal = tickVal * point / tickSize;
   double lot = riskAmt / (slPoints * pointVal);
   double minLot  = SymbolInfoDouble(symbol, SYMBOL_VOLUME_MIN);
   double maxLotS = SymbolInfoDouble(symbol, SYMBOL_VOLUME_MAX);
   double lotStep = SymbolInfoDouble(symbol, SYMBOL_VOLUME_STEP);
   lot = MathMax(lot, minLot);
   lot = MathMin(lot, maxLot);
   lot = MathMin(lot, maxLotS);
   if(lotStep > 0) lot = MathFloor(lot / lotStep) * lotStep;
   return NormalizeDouble(lot, 2);
}

//+------------------------------------------------------------------+
//| Count positions by magic + symbol                                |
//+------------------------------------------------------------------+
int PF_CountPositions(ulong magic, string symbol = "")
{
   int count = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0) continue;
      if(PositionGetInteger(POSITION_MAGIC) != (long)magic) continue;
      if(symbol != "" && PositionGetString(POSITION_SYMBOL) != symbol) continue;
      count++;
   }
   return count;
}

//+------------------------------------------------------------------+
//| Close all positions by magic (optionally filter by symbol)       |
//+------------------------------------------------------------------+
void PF_CloseAll(CTrade &trade, ulong magic, string symbol = "")
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0) continue;
      if(PositionGetInteger(POSITION_MAGIC) != (long)magic) continue;
      if(symbol != "" && PositionGetString(POSITION_SYMBOL) != symbol) continue;
      trade.PositionClose(ticket);
   }
}

//+------------------------------------------------------------------+
//| Session check                                                     |
//+------------------------------------------------------------------+
bool PF_IsInSession(int hour, int startH, int endH)
{
   return (hour >= startH && hour < endH);
}

//+------------------------------------------------------------------+
//| Day filter                                                        |
//+------------------------------------------------------------------+
bool PF_IsTradingDay(int dow, bool mon, bool tue, bool wed, bool thu, bool fri)
{
   if(dow == 0 || dow == 6) return false;
   switch(dow)
   {
      case 1: return mon;
      case 2: return tue;
      case 3: return wed;
      case 4: return thu;
      case 5: return fri;
      default: return false;
   }
}

//+------------------------------------------------------------------+
//| Break-even management (generic)                                  |
//+------------------------------------------------------------------+
void PF_ManageBE(CTrade &trade, ulong magic, string symbol, double beAtR)
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0) continue;
      if(PositionGetInteger(POSITION_MAGIC) != (long)magic) continue;
      if(PositionGetString(POSITION_SYMBOL) != symbol) continue;

      double openPrice = PositionGetDouble(POSITION_PRICE_OPEN);
      double sl        = PositionGetDouble(POSITION_SL);
      double tp        = PositionGetDouble(POSITION_TP);
      long   posType   = PositionGetInteger(POSITION_TYPE);
      double bid       = SymbolInfoDouble(symbol, SYMBOL_BID);
      double ask       = SymbolInfoDouble(symbol, SYMBOL_ASK);
      double pt        = SymbolInfoDouble(symbol, SYMBOL_POINT);

      double initialRisk = MathAbs(openPrice - sl);
      if(initialRisk <= 0) continue;

      double profit = 0;
      if(posType == POSITION_TYPE_BUY)
         profit = bid - openPrice;
      else
         profit = openPrice - ask;

      if(profit >= beAtR * initialRisk)
      {
         double newSL = 0;
         if(posType == POSITION_TYPE_BUY && sl < openPrice)
            newSL = openPrice + pt;
         else if(posType == POSITION_TYPE_SELL && sl > openPrice)
            newSL = openPrice - pt;
         else continue;

         int digits = (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS);
         newSL = NormalizeDouble(newSL, digits);
         trade.PositionModify(ticket, newSL, tp);
      }
   }
}

//+------------------------------------------------------------------+
//| Setup trade object for a symbol                                  |
//+------------------------------------------------------------------+
void PF_SetupTrade(CTrade &trade, ulong magic, string symbol, int deviation)
{
   trade.SetExpertMagicNumber(magic);
   trade.SetDeviationInPoints(deviation);
   long fillMode = SymbolInfoInteger(symbol, SYMBOL_FILLING_MODE);
   if((fillMode & SYMBOL_FILLING_FOK) != 0)
      trade.SetTypeFilling(ORDER_FILLING_FOK);
   else if((fillMode & SYMBOL_FILLING_IOC) != 0)
      trade.SetTypeFilling(ORDER_FILLING_IOC);
   else
      trade.SetTypeFilling(ORDER_FILLING_RETURN);
   trade.LogLevel(LOG_LEVEL_ERRORS);
}

#endif // PORTFOLIO_COMMON_MQH
