//+------------------------------------------------------------------+
//| CBR_RiskExec.mqh — Execution, Risk, Position Management          |
//+------------------------------------------------------------------+
#ifndef CBR_RISKEXEC_MQH
#define CBR_RISKEXEC_MQH

#include "CBR_Config.mqh"
#include "CBR_Types.mqh"
#include <Trade\Trade.mqh>
#include <Trade\PositionInfo.mqh>
#include <Trade\SymbolInfo.mqh>

//--- Global objects
CTrade         g_cbrTrade;
CPositionInfo  g_cbrPos;
CSymbolInfo    g_cbrSym;

//--- Day state
CBR_DayState   g_cbrDay;

//+------------------------------------------------------------------+
//| Init execution objects                                           |
//+------------------------------------------------------------------+
void CBR_InitExec(ulong magic, int deviation, string symbol)
{
   g_cbrTrade.SetExpertMagicNumber(magic);
   g_cbrTrade.SetDeviationInPoints(deviation);
   g_cbrTrade.SetTypeFilling(ORDER_FILLING_FOK);
   g_cbrTrade.SetMarginMode();
   g_cbrTrade.LogLevel(LOG_LEVEL_ERRORS);

   g_cbrSym.Name(symbol);

   // Init day state
   ZeroMemory(g_cbrDay);
   g_cbrDay.eqStart = AccountInfoDouble(ACCOUNT_EQUITY);
   g_cbrDay.eqPeak  = g_cbrDay.eqStart;
}

//+------------------------------------------------------------------+
//| Daily reset — call on each new bar                               |
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
//| Check block reasons (DD, max trades, kill switch)                |
//+------------------------------------------------------------------+
string CBR_GetBlockReason(double dailyDDPct, int maxPerDay, int maxOpen,
                           bool killSwitch, ENUM_CBR_KILLZONE kz, int maxPerKZ)
{
   if(killSwitch)
      return "KILL_SWITCH";

   // Daily DD check
   double eq = AccountInfoDouble(ACCOUNT_EQUITY);
   if(g_cbrDay.eqStart > 0.0)
   {
      double ddPct = (g_cbrDay.eqStart - eq) / g_cbrDay.eqStart * 100.0;
      if(ddPct >= dailyDDPct)
         return "DAILY_DD_" + DoubleToString(ddPct, 1);
   }

   // Max trades per day
   if(g_cbrDay.tradeCount >= maxPerDay)
      return "MAX_DAY_" + IntegerToString(g_cbrDay.tradeCount);

   // Max open positions
   int openCount = CBR_CountPositions(_Symbol, g_cbrTrade.RequestMagic());
   if(openCount >= maxOpen)
      return "MAX_OPEN_" + IntegerToString(openCount);

   // Max trades per kill zone (prevent overtrading in one KZ)
   if(kz == CBR_KZ_LDN && g_cbrDay.kzLdnTrades >= maxPerKZ)
      return "KZ_LDN_MAX";
   if(kz == CBR_KZ_NY && g_cbrDay.kzNyTrades >= maxPerKZ)
      return "KZ_NY_MAX";
   if(kz == CBR_KZ_NYC && g_cbrDay.kzNycTrades >= maxPerKZ)
      return "KZ_NYC_MAX";

   return "";
}

//+------------------------------------------------------------------+
//| Count positions by symbol + magic                                |
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
//| Risk-based lot calculation                                       |
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
//| Execute a validated signal                                       |
//+------------------------------------------------------------------+
bool CBR_ExecuteSignal(string symbol, CBR_Signal &sig,
                        double riskPct, double maxLot,
                        double dayRiskMult, ulong magic)
{
   if(!sig.valid) return false;

   g_cbrSym.RefreshRates();

   double lots = CBR_CalcLots(symbol, riskPct, sig.slPts, maxLot, dayRiskMult);
   if(lots <= 0.0) return false;

   // Normalize prices
   int digits = (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS);
   double sl = NormalizeDouble(sig.slPrice, digits);
   double tp = NormalizeDouble(sig.tpPrice, digits);

   bool result = false;
   string comment = CBR_EA_NAME + "_" + CBR_KillZoneName(sig.killZone);

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

   // Retcode check
   if(result)
   {
      uint retcode = g_cbrTrade.ResultRetcode();
      if(retcode == TRADE_RETCODE_DONE || retcode == TRADE_RETCODE_PLACED)
      {
         g_cbrDay.tradeCount++;

         // Track per-KZ count
         if(sig.killZone == CBR_KZ_LDN)  g_cbrDay.kzLdnTrades++;
         if(sig.killZone == CBR_KZ_NY)   g_cbrDay.kzNyTrades++;
         if(sig.killZone == CBR_KZ_NYC)  g_cbrDay.kzNycTrades++;

         PrintFormat("[CBR] TRADE %s | KZ=%s | Lots=%.2f | SL=%.5f | TP=%.5f | RR=%.1f | Body=%.2f | CLoc=%.2f | ATR=%.1f | BBW=%.0f%%",
                     (sig.type == ORDER_TYPE_BUY ? "BUY" : "SELL"),
                     CBR_KillZoneName(sig.killZone),
                     lots, sl, tp, sig.rrRatio,
                     sig.bodyRatio, sig.closeLoc,
                     sig.atr / g_cbrPt, sig.bbwPctile);
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
//| Manage open positions (BE move, Friday flatten)                  |
//+------------------------------------------------------------------+
void CBR_ManagePositions(string symbol, ulong magic, int dow, int hour)
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      if(!g_cbrPos.SelectByIndex(i)) continue;
      if(g_cbrPos.Symbol() != symbol || g_cbrPos.Magic() != magic) continue;

      ulong ticket = g_cbrPos.Ticket();

      //--- Friday flatten
      if(CBR_IsFridayFlatten(dow, hour))
      {
         g_cbrTrade.PositionClose(ticket);
         PrintFormat("[CBR] FRIDAY FLATTEN: ticket=%d", ticket);
         continue;
      }

      //--- Break-even move
      double openPrice = g_cbrPos.PriceOpen();
      double sl        = g_cbrPos.StopLoss();
      double tp        = g_cbrPos.TakeProfit();
      double current   = g_cbrPos.PriceCurrent();

      // Calculate initial risk (distance from open to original SL)
      double initialRisk = MathAbs(openPrice - sl);
      if(initialRisk <= 0.0) continue;

      // Check if profit >= BE_AT_R * initial risk
      double profitPts = 0.0;
      if(g_cbrPos.PositionType() == POSITION_TYPE_BUY)
         profitPts = current - openPrice;
      else
         profitPts = openPrice - current;

      if(profitPts >= CBR_BE_AT_R * initialRisk)
      {
         // Move SL to break-even + 1 point (only if not already there)
         double newSL = 0.0;
         if(g_cbrPos.PositionType() == POSITION_TYPE_BUY)
            newSL = openPrice + g_cbrPt;  // BE + 1pt
         else
            newSL = openPrice - g_cbrPt;

         int digits = (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS);
         newSL = NormalizeDouble(newSL, digits);

         // Only modify if new SL is better than current
         bool shouldModify = false;
         if(g_cbrPos.PositionType() == POSITION_TYPE_BUY && newSL > sl)
            shouldModify = true;
         if(g_cbrPos.PositionType() == POSITION_TYPE_SELL && (newSL < sl || sl == 0.0))
            shouldModify = true;

         if(shouldModify)
         {
            if(g_cbrTrade.PositionModify(ticket, newSL, tp))
               PrintFormat("[CBR] BE MOVE: ticket=%d, newSL=%.5f", ticket, newSL);
         }
      }
   }
}

//+------------------------------------------------------------------+
//| Close all positions (kill switch or emergency)                   |
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
