//+------------------------------------------------------------------+
//| CBR_RiskExec.mqh — Execution, Risk, Position Management (v2)     |
//| Mostly same as v1, minor logging updates for level info          |
//+------------------------------------------------------------------+
#ifndef CBR_RISKEXEC_MQH
#define CBR_RISKEXEC_MQH

#include "CBR_Config.mqh"
#include "CBR_Types.mqh"
#include "CBR_SessionTime.mqh"
#include <Trade\Trade.mqh>
#include <Trade\PositionInfo.mqh>
#include <Trade\SymbolInfo.mqh>

CTrade         g_cbrTrade;
CPositionInfo  g_cbrPos;
CSymbolInfo    g_cbrSym;

CBR_DayState   g_cbrDay;

//+------------------------------------------------------------------+
void CBR_InitExec(ulong magic, int deviation, string symbol)
{
   g_cbrTrade.SetExpertMagicNumber(magic);
   g_cbrTrade.SetDeviationInPoints(deviation);

   //--- v2.5.1: Dynamic fill mode detection
   long fillMode = SymbolInfoInteger(symbol, SYMBOL_FILLING_MODE);
   if((fillMode & SYMBOL_FILLING_FOK) != 0)
      g_cbrTrade.SetTypeFilling(ORDER_FILLING_FOK);
   else if((fillMode & SYMBOL_FILLING_IOC) != 0)
      g_cbrTrade.SetTypeFilling(ORDER_FILLING_IOC);
   else
      g_cbrTrade.SetTypeFilling(ORDER_FILLING_RETURN);

   g_cbrTrade.SetMarginMode();
   g_cbrTrade.LogLevel(LOG_LEVEL_ERRORS);

   g_cbrSym.Name(symbol);

   ZeroMemory(g_cbrDay);
   g_cbrDay.eqStart = AccountInfoDouble(ACCOUNT_EQUITY);
   g_cbrDay.eqPeak  = g_cbrDay.eqStart;
}

//+------------------------------------------------------------------+
void CBR_DailyReset()
{
   MqlDateTime now;
   TimeCurrent(now);
   datetime today = (datetime)StringToTime(IntegerToString(now.year) + "." +
                                           IntegerToString(now.mon) + "." +
                                           IntegerToString(now.day));

   if(today != g_cbrDay.dayStart)
   {
      g_cbrDay.dayStart    = today;
      g_cbrDay.tradeCount  = 0;
      g_cbrDay.lossCount   = 0;
      g_cbrDay.kzLdnTrades = 0;
      g_cbrDay.kzNyTrades  = 0;
      g_cbrDay.kzNycTrades = 0;
      g_cbrDay.eqStart     = AccountInfoDouble(ACCOUNT_EQUITY);
   }

   double eq = AccountInfoDouble(ACCOUNT_EQUITY);
   if(eq > g_cbrDay.eqPeak) g_cbrDay.eqPeak = eq;
}

//+------------------------------------------------------------------+
string CBR_GetBlockReason(double dailyDDPct, int maxPerDay, int maxOpen,
                           bool killSwitch, ENUM_CBR_KILLZONE kz, int maxPerKZ)
{
   if(killSwitch)
      return "KILL_SWITCH";

   double eq = AccountInfoDouble(ACCOUNT_EQUITY);
   if(g_cbrDay.eqStart > 0.0)
   {
      double ddPct = (g_cbrDay.eqStart - eq) / g_cbrDay.eqStart * 100.0;
      if(ddPct >= dailyDDPct)
         return "DAILY_DD_" + DoubleToString(ddPct, 1);
   }

   if(g_cbrDay.tradeCount >= maxPerDay)
      return "MAX_DAY_" + IntegerToString(g_cbrDay.tradeCount);

   int openCount = CBR_CountPositions(_Symbol, g_cbrTrade.RequestMagic());
   if(openCount >= maxOpen)
      return "MAX_OPEN_" + IntegerToString(openCount);

   if(kz == CBR_KZ_LDN && g_cbrDay.kzLdnTrades >= maxPerKZ)
      return "KZ_LDN_MAX";
   if(kz == CBR_KZ_NY && g_cbrDay.kzNyTrades >= maxPerKZ)
      return "KZ_NY_MAX";
   if(kz == CBR_KZ_NYC && g_cbrDay.kzNycTrades >= maxPerKZ)
      return "KZ_NYC_MAX";

   return "";
}

//+------------------------------------------------------------------+
int CBR_CountPositions(string symbol, ulong magic)
{
   int count = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      if(g_cbrPos.SelectByIndex(i))
      {
         if(g_cbrPos.Symbol() == symbol && g_cbrPos.Magic() == magic)
            count++;
      }
   }
   return count;
}

//+------------------------------------------------------------------+
double CBR_CalcLots(string symbol, double riskPct, double slPts,
                     double maxLot, double dayRiskMult)
{
   double equity    = AccountInfoDouble(ACCOUNT_EQUITY);
   double riskMoney = equity * riskPct / 100.0 * dayRiskMult;

   double tickValue = SymbolInfoDouble(symbol, SYMBOL_TRADE_TICK_VALUE);
   double tickSize  = SymbolInfoDouble(symbol, SYMBOL_TRADE_TICK_SIZE);

   if(tickValue <= 0.0 || tickSize <= 0.0) return 0.0;

   double slMoney = slPts * g_cbrPt * tickValue / tickSize;
   if(slMoney <= 0.0) return 0.0;

   double lots = riskMoney / slMoney;

   double minLot  = SymbolInfoDouble(symbol, SYMBOL_VOLUME_MIN);
   double lotStep = SymbolInfoDouble(symbol, SYMBOL_VOLUME_STEP);

   lots = MathFloor(lots / lotStep) * lotStep;
   if(lots < minLot) lots = minLot;
   if(lots > maxLot) lots = maxLot;

   return NormalizeDouble(lots, 2);
}

//+------------------------------------------------------------------+
bool CBR_ExecuteSignal(string symbol, CBR_Signal &sig,
                        double riskPct, double maxLot,
                        double dayRiskMult, ulong magic)
{
   if(!sig.valid) return false;

   g_cbrSym.RefreshRates();

   double lots = CBR_CalcLots(symbol, riskPct, sig.slPts, maxLot, dayRiskMult);
   if(lots <= 0.0) return false;

   int digits = (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS);
   double sl = NormalizeDouble(sig.slPrice, digits);
   double tp = NormalizeDouble(sig.tpPrice, digits);

   //--- v2.5.1: Stop level check (broker minimum distance from current price)
   long stopLevel = SymbolInfoInteger(symbol, SYMBOL_TRADE_STOPS_LEVEL);
   double stopDist = stopLevel * g_cbrPt;
   if(sig.type == ORDER_TYPE_BUY)
   {
      double ask = SymbolInfoDouble(symbol, SYMBOL_ASK);
      if(MathAbs(ask - sl) < stopDist || MathAbs(tp - ask) < stopDist)
      {
         PrintFormat("[CBR] SKIP: stop level violation. ask=%.5f sl=%.5f tp=%.5f stopDist=%.5f",
                     ask, sl, tp, stopDist);
         return false;
      }
   }
   else
   {
      double bid = SymbolInfoDouble(symbol, SYMBOL_BID);
      if(MathAbs(sl - bid) < stopDist || MathAbs(bid - tp) < stopDist)
      {
         PrintFormat("[CBR] SKIP: stop level violation. bid=%.5f sl=%.5f tp=%.5f stopDist=%.5f",
                     bid, sl, tp, stopDist);
         return false;
      }
   }

   bool result = false;
   // v2: comment includes level type + entry mode
   string comment = CBR_EA_NAME + "_" + CBR_KillZoneName(sig.killZone) +
                    "_" + CBR_EntryModeName(sig.entryMode) +
                    "_" + CBR_LevelTypeName(sig.levelType);

   //--- EQL: capture intended price + spread before OrderSend
   double cbrIntendedPx = (sig.type == ORDER_TYPE_BUY)
                        ? SymbolInfoDouble(symbol, SYMBOL_ASK)
                        : SymbolInfoDouble(symbol, SYMBOL_BID);
   int cbrSpreadPts = (int)SymbolInfoInteger(symbol, SYMBOL_SPREAD);
   EQL_SetContext(cbrIntendedPx, cbrSpreadPts * g_cbrPt, CBR_KillZoneName(sig.killZone));

   if(sig.type == ORDER_TYPE_BUY)
   {
      double ask = SymbolInfoDouble(symbol, SYMBOL_ASK);
      result = g_cbrTrade.Buy(lots, symbol, ask, sl, tp, comment);
   }
   else
   {
      double bid = SymbolInfoDouble(symbol, SYMBOL_BID);
      result = g_cbrTrade.Sell(lots, symbol, bid, sl, tp, comment);
   }

   if(result)
   {
      uint retcode = g_cbrTrade.ResultRetcode();
      if(retcode == TRADE_RETCODE_DONE || retcode == TRADE_RETCODE_PLACED)
      {
         EQL_RecordFill(retcode);
         g_cbrDay.tradeCount++;

         if(sig.killZone == CBR_KZ_LDN)  g_cbrDay.kzLdnTrades++;
         if(sig.killZone == CBR_KZ_NY)   g_cbrDay.kzNyTrades++;
         if(sig.killZone == CBR_KZ_NYC)  g_cbrDay.kzNycTrades++;

         PrintFormat("[CBR] TRADE %s | KZ=%s | Mode=%s | Level=%s@%.2f | Lots=%.2f | SL=%.2f | TP=%.2f | RR=%.1f | Body=%.2f | Bias=%d",
                     (sig.type == ORDER_TYPE_BUY ? "BUY" : "SELL"),
                     CBR_KillZoneName(sig.killZone),
                     CBR_EntryModeName(sig.entryMode),
                     CBR_LevelTypeName(sig.levelType),
                     sig.levelPrice,
                     lots, sl, tp, sig.rrRatio,
                     sig.bodyRatio, sig.bias);
         return true;
      }
      else
      {
         PrintFormat("[CBR] ORDER FAIL: retcode=%u, comment=%s",
                     retcode, g_cbrTrade.ResultComment());
      }
   }

   return false;
}

//+------------------------------------------------------------------+
void CBR_ManagePositions(string symbol, ulong magic, int dow, int hour)
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      if(!g_cbrPos.SelectByIndex(i)) continue;
      if(g_cbrPos.Symbol() != symbol || g_cbrPos.Magic() != magic) continue;

      ulong ticket = g_cbrPos.Ticket();

      // Friday flatten
      if(CBR_IsFridayFlatten(dow, hour))
      {
         g_cbrTrade.PositionClose(ticket);
         PrintFormat("[CBR] FRIDAY FLATTEN: ticket=%d", ticket);
         continue;
      }

      // Break-even move
      double openPrice = g_cbrPos.PriceOpen();
      double sl        = g_cbrPos.StopLoss();
      double tp        = g_cbrPos.TakeProfit();
      double current   = g_cbrPos.PriceCurrent();

      double initialRisk = MathAbs(openPrice - sl);
      if(initialRisk <= 0.0) continue;

      double profitPts = 0.0;
      if(g_cbrPos.PositionType() == POSITION_TYPE_BUY)
         profitPts = current - openPrice;
      else
         profitPts = openPrice - current;

      //--- Partial close at N×R (if enabled)
      if(InpPartialClose)
      {
         bool isBuy = (g_cbrPos.PositionType() == POSITION_TYPE_BUY);
         PCL_CheckPartialClose(g_cbrTrade, ticket, isBuy, openPrice, sl, tp,
                               current, g_cbrPos.Volume(), symbol,
                               InpPCL_TriggerR, InpPCL_ClosePct, "[CBR]");
      }

      //--- Break-even move (only if partial close didn't already do BE)
      if(!PCL_IsDone(ticket) && profitPts >= CBR_BE_AT_R * initialRisk)
      {
         double newSL = 0.0;
         if(g_cbrPos.PositionType() == POSITION_TYPE_BUY)
            newSL = openPrice + g_cbrPt;
         else
            newSL = openPrice - g_cbrPt;

         int digits = (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS);
         newSL = NormalizeDouble(newSL, digits);

         bool shouldModify = false;
         if(g_cbrPos.PositionType() == POSITION_TYPE_BUY && newSL > sl)
            shouldModify = true;
         if(g_cbrPos.PositionType() == POSITION_TYPE_SELL && (newSL < sl || sl == 0.0))
            shouldModify = true;

         if(shouldModify)
         {
            //--- v2.5.1: Freeze level check before modifying
            long freezeLevel = SymbolInfoInteger(symbol, SYMBOL_TRADE_FREEZE_LEVEL);
            double freezeDist = freezeLevel * g_cbrPt;
            double distToSL = MathAbs(current - sl);
            double distToTP = MathAbs(tp - current);
            if(freezeLevel > 0 && (distToSL < freezeDist || distToTP < freezeDist))
            {
               // Position is in freeze zone — skip BE modify silently
            }
            else if(g_cbrTrade.PositionModify(ticket, newSL, tp))
               PrintFormat("[CBR] BE MOVE: ticket=%d, newSL=%.5f", ticket, newSL);
         }
      }
   }
}

//+------------------------------------------------------------------+
void CBR_CloseAll(string symbol, ulong magic)
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      if(!g_cbrPos.SelectByIndex(i)) continue;
      if(g_cbrPos.Symbol() != symbol || g_cbrPos.Magic() != magic) continue;
      g_cbrTrade.PositionClose(g_cbrPos.Ticket());
   }
}

#endif // CBR_RISKEXEC_MQH
