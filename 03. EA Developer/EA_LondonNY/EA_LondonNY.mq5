//+------------------------------------------------------------------+
//| EA_LondonNY.mq5                                                   |
//| London → NY Momentum Continuation                                  |
//| Copyright 2026, Max & Ngai Meo Coc                                |
//|                                                                    |
//| EDGE HYPOTHESIS:                                                  |
//| If London session creates a clear directional trend (> 0.5 ATR    |
//| in first 3 hours), NY AM session continues that direction         |
//| 58-64% of the time. This is NOT a breakout strategy — it uses     |
//| London's established direction as a BIAS for NY session entries.  |
//|                                                                    |
//| Rules:                                                            |
//| 1. Measure London direction: Close of 3h bar - Open of London     |
//| 2. IF |move| > ATR(14) × threshold → directional bias confirmed   |
//| 3. Wait for NY AM pullback to enter in London's direction          |
//| 4. Entry on pullback bounce (shift=1, closed bar)                 |
//| 5. SL below pullback low (buy) / above pullback high (sell)       |
//| 6. TP = fixed R:R or time exit                                    |
//|                                                                    |
//| Different from S105/S113 (session breakout FAILED):               |
//| - S105 was range breakout → random on EURUSD                     |
//| - This is TREND CONTINUATION with pullback entry                  |
//|                                                                    |
//| Target: EURUSD/GBPUSD M15 NY session.                            |
//| Max | 2026-03-31 | v1.0                                          |
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
input bool   InpEnabled        = true;
input double InpRiskPct        = 1.0;
input double InpMaxLot         = 1.00;
input int    InpMagic          = 20260403;
input string InpComment        = "LdnNY";

// --- London Trend Measurement ---
input group "=== London Trend ==="
input int    InpLdn_StartH     = 9;          // London start hour (broker time)
input int    InpLdn_StartM     = 0;
input int    InpLdn_MeasureH   = 12;         // London trend measured at (3h after open)
input int    InpLdn_MeasureM   = 0;
input double InpTrendATR_Mult  = 0.50;       // Min London move as ATR multiple (0.5 = 50%)
input int    InpATR_Period     = 14;         // ATR period (D1)

// --- NY Entry ---
input group "=== NY Pullback Entry ==="
input int    InpNY_StartH      = 15;         // NY entry window start (broker)
input int    InpNY_StartM      = 0;
input int    InpNY_EndH        = 18;         // NY entry window end
input int    InpNY_EndM        = 0;
input int    InpPB_Lookback    = 3;          // Max bars to find pullback
input double InpPB_MinATR      = 0.15;       // Min pullback depth (ATR multiples)
input double InpPB_MaxATR      = 0.60;       // Max pullback depth (not too deep)

// --- SL/TP ---
input group "=== Risk Management ==="
input double InpSL_ATR_Mult    = 0.5;        // SL = pullback extreme + ATR × this
input double InpRR_Ratio       = 2.0;        // Risk:Reward
input bool   InpUseTimeExit    = true;
input int    InpExitH          = 20;
input int    InpExitM          = 0;
input bool   InpUseBE          = false;
input double InpBE_Trigger     = 1.0;
input double InpMaxDDPct       = 99.0;

// --- EMA Filter ---
input group "=== Trend Filter ==="
input bool   InpUseEMA         = false;      // EMA direction must confirm
input int    InpEMA_Period     = 50;         // EMA period (M15)

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
int            handleEMA_M15;
double         initialBalance;

// Daily state
double         londonDirection;    // +1 = bullish, -1 = bearish, 0 = no trend
double         londonOpen;
double         londonMeasureClose;
bool           biasSet;
bool           tradeEnteredToday;
datetime       lastTradeDay;

//+------------------------------------------------------------------+
//| Initialization                                                     |
//+------------------------------------------------------------------+
int OnInit()
{
   if(!InpEnabled) return INIT_SUCCEEDED;

   trade.SetExpertMagicNumber(InpMagic);
   sym.Name(_Symbol);

   handleATR_D1  = iATR(_Symbol, PERIOD_D1, InpATR_Period);
   handleEMA_M15 = iMA(_Symbol, _Period, InpEMA_Period, 0, MODE_EMA, PRICE_CLOSE);

   if(handleATR_D1 == INVALID_HANDLE || handleEMA_M15 == INVALID_HANDLE)
   {
      Print("ERROR: indicator handle failed");
      return INIT_FAILED;
   }

   initialBalance = AccountInfoDouble(ACCOUNT_BALANCE);
   londonDirection = 0;
   biasSet = false;
   tradeEnteredToday = false;
   lastTradeDay = 0;

   Print("EA_LondonNY v1.0 initialized. Symbol=", _Symbol);

   double ldnnyPipSize = sym.Point() * 10.0;
   if(StringFind(_Symbol, "JPY") >= 0) ldnnyPipSize = sym.Point() * 100.0;
   EQL_Init("EA_LondonNY", InpMagic, "LDNY", ldnnyPipSize, true);

   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   if(handleATR_D1 != INVALID_HANDLE) IndicatorRelease(handleATR_D1);
   if(handleEMA_M15 != INVALID_HANDLE) IndicatorRelease(handleEMA_M15);
}

//+------------------------------------------------------------------+
//| Helpers                                                            |
//+------------------------------------------------------------------+
void GetBrokerTime(int &h, int &m) {
   MqlDateTime dt; TimeToStruct(TimeCurrent(), dt); h = dt.hour; m = dt.min;
}

bool IsTradingDay() {
   MqlDateTime dt; TimeToStruct(TimeCurrent(), dt);
   switch(dt.day_of_week) {
      case 1: return InpTradeMon; case 2: return InpTradeTue;
      case 3: return InpTradeWed; case 4: return InpTradeThu;
      case 5: return InpTradeFri; default: return false;
   }
}

int CountPositions() {
   int c = 0;
   for(int i = PositionsTotal()-1; i >= 0; i--) {
      if(pos.SelectByIndex(i) && pos.Magic() == InpMagic && pos.Symbol() == _Symbol) c++;
   }
   return c;
}

void CloseAllPositions(string reason) {
   for(int i = PositionsTotal()-1; i >= 0; i--) {
      if(pos.SelectByIndex(i) && pos.Magic() == InpMagic && pos.Symbol() == _Symbol) {
         trade.PositionClose(pos.Ticket());
         Print("CLOSE [", reason, "] ticket=", pos.Ticket(), " profit=", pos.Profit());
      }
   }
}

double CalcLotSize(double slPips) {
   sym.RefreshRates();
   double riskMoney = AccountInfoDouble(ACCOUNT_BALANCE) * InpRiskPct / 100.0;
   double tickVal = sym.TickValue(), tickSize = sym.TickSize(), point = sym.Point();
   if(tickVal <= 0 || tickSize <= 0) return sym.LotsMin();
   double pipValue = tickVal / tickSize * point * 10.0;
   if(StringFind(_Symbol, "JPY") >= 0) pipValue = tickVal / tickSize * point * 100.0;
   if(pipValue <= 0) return sym.LotsMin();
   double lots = riskMoney / (slPips * pipValue);
   lots = MathMin(lots, InpMaxLot);
   lots = MathMax(lots, sym.LotsMin());
   return NormalizeDouble(lots / sym.LotsStep(), 0) * sym.LotsStep();
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
   if(today != lastTradeDay) {
      lastTradeDay = today;
      londonDirection = 0;
      biasSet = false;
      tradeEnteredToday = false;
      londonOpen = 0;
      londonMeasureClose = 0;
   }

   // New bar only
   static datetime lastBar = 0;
   datetime curBar = iTime(_Symbol, _Period, 0);
   if(curBar == lastBar) return;
   lastBar = curBar;

   if(!IsTradingDay()) return;

   // DD kill switch
   double equity = AccountInfoDouble(ACCOUNT_EQUITY);
   if(initialBalance > 0 && equity < initialBalance * (1.0 - InpMaxDDPct / 100.0)) return;

   int h, m;
   GetBrokerTime(h, m);
   int nowMins = h * 60 + m;
   int ldnStartMins = InpLdn_StartH * 60 + InpLdn_StartM;
   int ldnMeasureMins = InpLdn_MeasureH * 60 + InpLdn_MeasureM;
   int nyStartMins = InpNY_StartH * 60 + InpNY_StartM;
   int nyEndMins = InpNY_EndH * 60 + InpNY_EndM;

   // --- Phase 1: Capture London open price ---
   if(londonOpen == 0 && nowMins >= ldnStartMins && nowMins < ldnStartMins + 15)
   {
      londonOpen = iOpen(_Symbol, _Period, 0);
   }

   // --- Phase 2: Measure London trend ---
   if(!biasSet && londonOpen > 0 && nowMins >= ldnMeasureMins && nowMins < ldnMeasureMins + 15)
   {
      double close1 = iClose(_Symbol, _Period, 1);
      double move = close1 - londonOpen;

      // Get ATR
      double atr[];
      if(CopyBuffer(handleATR_D1, 0, 1, 1, atr) < 1) return;

      double threshold = atr[0] * InpTrendATR_Mult;

      if(move > threshold)
      {
         londonDirection = 1;  // Bullish
         biasSet = true;
         Print("LONDON BULLISH bias. Move=", move/sym.Point(), " pts, Threshold=",
               threshold/sym.Point(), " pts");
      }
      else if(move < -threshold)
      {
         londonDirection = -1; // Bearish
         biasSet = true;
         Print("LONDON BEARISH bias. Move=", move/sym.Point(), " pts");
      }
      else
      {
         biasSet = true; // Set but no direction
         Print("LONDON NO BIAS. Move=", move/sym.Point(), " pts < threshold");
      }
   }

   // --- Phase 3: NY pullback entry ---
   if(biasSet && londonDirection != 0 && !tradeEnteredToday &&
      nowMins >= nyStartMins && nowMins < nyEndMins && CountPositions() == 0)
   {
      // Look for pullback in last N bars
      double atr[];
      if(CopyBuffer(handleATR_D1, 0, 1, 1, atr) < 1) return;

      double close1 = iClose(_Symbol, _Period, 1);
      double open1  = iOpen(_Symbol, _Period, 1);

      // Find pullback extreme
      double pbExtreme = 0;
      double recentHigh = -999999, recentLow = 999999;

      for(int i = 1; i <= InpPB_Lookback; i++)
      {
         double hi = iHigh(_Symbol, _Period, i);
         double lo = iLow(_Symbol, _Period, i);
         if(hi > recentHigh) recentHigh = hi;
         if(lo < recentLow)  recentLow = lo;
      }

      bool validPullback = false;

      if(londonDirection > 0) // Bullish bias → look for pullback down
      {
         // Pullback = price dipped from session high
         // Current bar must bounce back up (close > open, close in trend direction)
         double pullbackDepth = recentHigh - recentLow;

         if(pullbackDepth >= atr[0] * InpPB_MinATR &&
            pullbackDepth <= atr[0] * InpPB_MaxATR &&
            close1 > open1) // Bullish bounce bar
         {
            validPullback = true;
            pbExtreme = recentLow;
         }
      }
      else if(londonDirection < 0) // Bearish bias
      {
         double pullbackDepth = recentHigh - recentLow;

         if(pullbackDepth >= atr[0] * InpPB_MinATR &&
            pullbackDepth <= atr[0] * InpPB_MaxATR &&
            close1 < open1) // Bearish bounce bar
         {
            validPullback = true;
            pbExtreme = recentHigh;
         }
      }

      // EMA filter
      if(validPullback && InpUseEMA)
      {
         double ema[];
         if(CopyBuffer(handleEMA_M15, 0, 1, 1, ema) < 1) return;

         if(londonDirection > 0 && close1 < ema[0]) validPullback = false;
         if(londonDirection < 0 && close1 > ema[0]) validPullback = false;
      }

      if(validPullback)
      {
         double pipSize = sym.Point() * 10.0;
         if(StringFind(_Symbol, "JPY") >= 0) pipSize = sym.Point() * 100.0;

         if(londonDirection > 0) // BUY
         {
            double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
            double sl  = pbExtreme - atr[0] * InpSL_ATR_Mult;
            double slPips = (ask - sl) / pipSize;
            double tp  = ask + slPips * InpRR_Ratio * pipSize;

            int stopLevel = (int)SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL);
            double minDist = stopLevel * sym.Point();
            if(MathAbs(ask - sl) < minDist) sl = ask - minDist - sym.Point();
            if(MathAbs(tp - ask) < minDist) tp = ask + minDist + sym.Point();

            double lots = CalcLotSize(slPips);
            double spreadPips = (double)SymbolInfoInteger(_Symbol, SYMBOL_SPREAD) * sym.Point() / pipSize;
            EQL_SetContext(ask, spreadPips, "NY");
            bool filled = false;
            uint retcode = 0;
            for(int attempt = 1; attempt <= 3; attempt++) {
               if(trade.Buy(lots, _Symbol, ask, sl, tp, InpComment + "_BUY")) {
                  retcode = trade.ResultRetcode();
                  EQL_RecordFill(retcode);
                  filled = true;
                  break;
               }
               retcode = trade.ResultRetcode();
               EQL_RecordRetry(retcode);
               if(attempt < 3) Sleep(200 * (int)MathPow(2, attempt - 1));
            }
            if(filled) {
               Print("LDN→NY BUY lots=", lots, " price=", ask, " sl=", sl, " tp=", tp);
               tradeEnteredToday = true;
            }
         }
         else // SELL
         {
            double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
            double sl  = pbExtreme + atr[0] * InpSL_ATR_Mult;
            double slPips = (sl - bid) / pipSize;
            double tp  = bid - slPips * InpRR_Ratio * pipSize;

            int stopLevel = (int)SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL);
            double minDist = stopLevel * sym.Point();
            if(MathAbs(sl - bid) < minDist) sl = bid + minDist + sym.Point();
            if(MathAbs(bid - tp) < minDist) tp = bid - minDist - sym.Point();

            double lots = CalcLotSize(slPips);
            double spreadPips = (double)SymbolInfoInteger(_Symbol, SYMBOL_SPREAD) * sym.Point() / pipSize;
            EQL_SetContext(bid, spreadPips, "NY");
            bool filled = false;
            uint retcode = 0;
            for(int attempt = 1; attempt <= 3; attempt++) {
               if(trade.Sell(lots, _Symbol, bid, sl, tp, InpComment + "_SELL")) {
                  retcode = trade.ResultRetcode();
                  EQL_RecordFill(retcode);
                  filled = true;
                  break;
               }
               retcode = trade.ResultRetcode();
               EQL_RecordRetry(retcode);
               if(attempt < 3) Sleep(200 * (int)MathPow(2, attempt - 1));
            }
            if(filled) {
               Print("LDN→NY SELL lots=", lots, " price=", bid, " sl=", sl, " tp=", tp);
               tradeEnteredToday = true;
            }
         }
      }
   }

   // --- Time exit ---
   if(CountPositions() > 0)
   {
      if(InpUseTimeExit && h >= InpExitH && m >= InpExitM)
         CloseAllPositions("TimeExit");
   }
}

//+------------------------------------------------------------------+
//| Trade transaction handler — feeds EQL deal capture               |
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
