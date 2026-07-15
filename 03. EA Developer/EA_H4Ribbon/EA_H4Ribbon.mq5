//+------------------------------------------------------------------+
//| EA_H4Ribbon.mq5                                                  |
//| H4 EMA Ribbon Swing Strategy                                     |
//| Copyright 2026, Max & Ngai Meo Coc                                |
//|                                                                    |
//| EDGE HYPOTHESIS:                                                  |
//| On H4, price pulling back to EMA34/EMA89 zone in a trending      |
//| market creates a swing entry. Documented PF ~1.3, 40-80t/yr.     |
//| Hold 1-3 days with trailing SL below last H4 swing low.          |
//|                                                                    |
//| MECHANISM: EMA34 > EMA89 = uptrend. Price pulls back to touch    |
//| EMA34-EMA89 zone. RSI(14) confirms not overbought/oversold.      |
//| Enter on first H4 close back above EMA34. SL = swing low.        |
//| Trail SL to each new higher low. Time exit after MaxBars.        |
//|                                                                    |
//| Type: #107 (H4 EMA ribbon swing)                                  |
//| Max | 2026-04-14 | v1.0                                          |
//+------------------------------------------------------------------+
#property copyright "Max & Ngai Meo Coc"
#property version   "1.00"
#property strict

#include <Trade\Trade.mqh>
#include <Trade\PositionInfo.mqh>
#include <Trade\SymbolInfo.mqh>

input group "=== Core ==="
input bool   InpEnabled     = true;
input double InpRiskPct     = 0.5;
input double InpMaxLot      = 1.00;
input int    InpMagic       = 20260417;

input group "=== Signal ==="
input int    InpEMA_Fast    = 34;
input int    InpEMA_Slow    = 89;
input int    InpRSI_Period  = 14;
input double InpRSI_OB     = 70.0;     // RSI overbought (skip buy above)
input double InpRSI_OS     = 30.0;     // RSI oversold (skip sell below)
input int    InpSwingLookback = 10;    // Bars to find swing low/high for SL

input group "=== Trade Management ==="
input int    InpMaxBars     = 48;       // Max hold in H4 bars (48 = 8 days)
input bool   InpUseTrailSL  = true;     // Trail SL to swing lows/highs
input int    InpTrailLookback = 5;      // Bars for trailing swing detection
input double InpMinRR       = 1.5;      // Minimum risk:reward before entry

input group "=== Filters ==="
input int    InpMaxPerWeek  = 2;
input double InpDailyDD     = 4.0;
input bool   InpTradeMon    = true;
input bool   InpTradeTue    = true;
input bool   InpTradeWed    = true;
input bool   InpTradeThu    = true;
input bool   InpTradeFri    = true;

CTrade trade;
CPositionInfo pos;
CSymbolInfo sym;
int hEmaFast, hEmaSlow, hRSI, hATR;
double initialBalance;
int weekTradeCount;
int lastWeek;
int barsInTrade;
datetime lastBar;

int OnInit()
{
   if(!InpEnabled) return INIT_SUCCEEDED;
   trade.SetExpertMagicNumber(InpMagic);
   trade.SetDeviationInPoints(50);
   sym.Name(_Symbol);

   hEmaFast = iMA(_Symbol, PERIOD_H4, InpEMA_Fast, 0, MODE_EMA, PRICE_CLOSE);
   hEmaSlow = iMA(_Symbol, PERIOD_H4, InpEMA_Slow, 0, MODE_EMA, PRICE_CLOSE);
   hRSI     = iRSI(_Symbol, PERIOD_H4, InpRSI_Period, PRICE_CLOSE);
   hATR     = iATR(_Symbol, PERIOD_D1, 14);

   if(hEmaFast == INVALID_HANDLE || hEmaSlow == INVALID_HANDLE ||
      hRSI == INVALID_HANDLE || hATR == INVALID_HANDLE)
      return INIT_FAILED;

   initialBalance = AccountInfoDouble(ACCOUNT_BALANCE);
   weekTradeCount = 0;
   lastWeek = -1;
   barsInTrade = 0;
   lastBar = 0;

   Print("EA_H4Ribbon v1.0: ", _Symbol, " EMA ", InpEMA_Fast, "/", InpEMA_Slow);
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   if(hEmaFast != INVALID_HANDLE) IndicatorRelease(hEmaFast);
   if(hEmaSlow != INVALID_HANDLE) IndicatorRelease(hEmaSlow);
   if(hRSI != INVALID_HANDLE) IndicatorRelease(hRSI);
   if(hATR != INVALID_HANDLE) IndicatorRelease(hATR);
}

void CheckWeekReset()
{
   MqlDateTime dt;
   TimeToStruct(TimeCurrent(), dt);
   int wk = dt.day_of_year / 7;
   if(wk != lastWeek) { lastWeek = wk; weekTradeCount = 0; }
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
      {
         trade.PositionClose(pos.Ticket());
         Print("CLOSE [", reason, "] pnl=", pos.Profit());
      }
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

double FindSwingLow(int startBar, int bars)
{
   double lowest = DBL_MAX;
   for(int i = startBar; i < startBar + bars; i++)
   {
      double lo = iLow(_Symbol, PERIOD_H4, i);
      if(lo > 0 && lo < lowest) lowest = lo;
   }
   return lowest;
}

double FindSwingHigh(int startBar, int bars)
{
   double highest = 0;
   for(int i = startBar; i < startBar + bars; i++)
   {
      double hi = iHigh(_Symbol, PERIOD_H4, i);
      if(hi > highest) highest = hi;
   }
   return highest;
}

void TrailStopLoss()
{
   for(int i = PositionsTotal()-1; i >= 0; i--)
   {
      if(!pos.SelectByIndex(i)) continue;
      if(pos.Magic() != InpMagic || pos.Symbol() != _Symbol) continue;

      if(pos.PositionType() == POSITION_TYPE_BUY)
      {
         double newSL = FindSwingLow(1, InpTrailLookback);
         if(newSL > pos.StopLoss() && newSL < SymbolInfoDouble(_Symbol, SYMBOL_BID))
            trade.PositionModify(pos.Ticket(), newSL, pos.TakeProfit());
      }
      else
      {
         double newSL = FindSwingHigh(1, InpTrailLookback);
         if(newSL < pos.StopLoss() && newSL > SymbolInfoDouble(_Symbol, SYMBOL_ASK))
            trade.PositionModify(pos.Ticket(), newSL, pos.TakeProfit());
      }
   }
}

void OnTick()
{
   if(!InpEnabled) return;

   // Only process on new H4 bar
   datetime currentBar = iTime(_Symbol, PERIOD_H4, 0);
   if(currentBar == lastBar) return;
   lastBar = currentBar;

   sym.RefreshRates();
   CheckWeekReset();

   // Manage existing position
   if(CountPos() > 0)
   {
      barsInTrade++;
      if(barsInTrade >= InpMaxBars) { CloseAll("MaxBars"); barsInTrade = 0; return; }
      if(InpUseTrailSL) TrailStopLoss();
      return;
   }

   // DD kill switch
   double equity = AccountInfoDouble(ACCOUNT_EQUITY);
   if(initialBalance > 0 && equity < initialBalance * (1.0 - InpDailyDD / 100.0)) return;
   if(weekTradeCount >= InpMaxPerWeek) return;
   if(!IsTradingDay()) return;

   // === SIGNAL: H4 EMA Ribbon Pullback ===
   double emaF[], emaS[], rsi[];
   if(CopyBuffer(hEmaFast, 0, 1, 3, emaF) < 3) return;
   if(CopyBuffer(hEmaSlow, 0, 1, 3, emaS) < 3) return;
   if(CopyBuffer(hRSI, 0, 1, 1, rsi) < 1) return;

   double atrArr[];
   if(CopyBuffer(hATR, 0, 1, 1, atrArr) < 1) return;
   double atr = atrArr[0];

   double close1 = iClose(_Symbol, PERIOD_H4, 1); // Last closed bar
   double close2 = iClose(_Symbol, PERIOD_H4, 2);
   double low1   = iLow(_Symbol, PERIOD_H4, 1);
   double high1  = iHigh(_Symbol, PERIOD_H4, 1);

   // BUY: EMA fast > slow (uptrend), price pulled back INTO zone, now closing above EMA fast
   if(emaF[2] > emaS[2] && emaF[1] > emaS[1]) // Trend confirmed on shift 1 and 2
   {
      // Price touched zone: low went into EMA34-89 band or below
      bool touchedZone = (low1 <= emaF[1] + atr * 0.1);
      // Close back above EMA fast
      bool closeAbove = (close1 > emaF[1]);
      // Previous bar was lower (actually pulled back)
      bool pulledBack = (close2 < emaF[0] || low1 < emaF[1]);

      if(touchedZone && closeAbove && pulledBack && rsi[0] < InpRSI_OB)
      {
         double sl = FindSwingLow(1, InpSwingLookback);
         double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
         double slDist = ask - sl;

         if(slDist > 0 && slDist < atr * 3.0) // SL reasonable
         {
            // Check min RR: potential target = recent swing high distance
            double recentHigh = FindSwingHigh(1, InpSwingLookback);
            double potential = recentHigh - ask;
            if(potential > 0 && potential / slDist >= InpMinRR)
            {
               int stopLevel = (int)SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL);
               double minD = stopLevel * sym.Point();
               if(slDist < minD) sl = ask - minD - sym.Point();

               double lots = CalcLots(slDist);
               if(trade.Buy(lots, _Symbol, ask, sl, 0, "H4Rib_B"))
               {
                  weekTradeCount++;
                  barsInTrade = 0;
                  Print("H4 RIBBON BUY: EMA34=", emaF[1], " sl=", sl, " lots=", lots);
               }
            }
         }
      }
   }

   // SELL: EMA fast < slow (downtrend), price pulled back up INTO zone, now closing below
   if(emaF[2] < emaS[2] && emaF[1] < emaS[1])
   {
      bool touchedZone = (high1 >= emaF[1] - atr * 0.1);
      bool closeBelow = (close1 < emaF[1]);
      bool pulledBack = (close2 > emaF[0] || high1 > emaF[1]);

      if(touchedZone && closeBelow && pulledBack && rsi[0] > InpRSI_OS)
      {
         double sl = FindSwingHigh(1, InpSwingLookback);
         double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
         double slDist = sl - bid;

         if(slDist > 0 && slDist < atr * 3.0)
         {
            double recentLow = FindSwingLow(1, InpSwingLookback);
            double potential = bid - recentLow;
            if(potential > 0 && potential / slDist >= InpMinRR)
            {
               int stopLevel = (int)SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL);
               double minD = stopLevel * sym.Point();
               if(slDist < minD) sl = bid + minD + sym.Point();

               double lots = CalcLots(slDist);
               if(trade.Sell(lots, _Symbol, bid, sl, 0, "H4Rib_S"))
               {
                  weekTradeCount++;
                  barsInTrade = 0;
                  Print("H4 RIBBON SELL: EMA34=", emaF[1], " sl=", sl, " lots=", lots);
               }
            }
         }
      }
   }
}
