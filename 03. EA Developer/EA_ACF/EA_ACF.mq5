//+------------------------------------------------------------------+
//| EA_ACF.mq5                                                        |
//| Autocorrelation Regime Switcher — XAUUSD/USDJPY M15               |
//|                                                                    |
//| Hypothesis: Bar return autocorrelation (lag-1) detects regime:     |
//|   ACF < -0.15 → mean-reversion mode → fade last bar direction     |
//|   ACF > +0.10 → momentum mode → follow last bar direction         |
//|   Otherwise → dead zone, no trade                                  |
//|                                                                    |
//| Source: Toth et al. (2023) Quantitative Finance,                   |
//|         Fractal Market Hypothesis (Peters 1991, Mandelbrot 2004)   |
//|                                                                    |
//| Counterparty: Traders using static indicators in wrong regime.     |
//| Zero indicator lag — signal from raw return statistics.            |
//+------------------------------------------------------------------+
#property copyright "Max — AlphaFactory Research"
#property version   "1.0"
#property strict

//--- Input parameters
input int    InpACFPeriod     = 20;    // Rolling window for ACF calculation
input double InpACFBearish    = -0.15; // ACF threshold for mean-reversion mode
input double InpACFBullish    = 0.10;  // ACF threshold for momentum mode
input double InpRiskPct       = 0.50;  // Risk per trade (%)
input double InpRR            = 1.5;   // Risk:Reward ratio
input double InpSL_ATR_Mult   = 1.5;  // SL = X * ATR(14)
input int    InpMaxBars       = 20;    // Max bars to hold trade
input int    InpMagic         = 778001;// Magic number

//--- Session filter
input int    InpSessionStart  = 9;     // Session start (broker hour)
input int    InpSessionEnd    = 22;    // Session end (broker hour)
input bool   InpSkipFriday    = true;  // Skip Friday entries

//--- Indicator
int g_atrHandle = INVALID_HANDLE;
double g_point = 0.0;

//--- State
int g_barsHeld = 0;
int g_fileHandle = INVALID_HANDLE;

//+------------------------------------------------------------------+
int OnInit()
{
   g_point = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   if(g_point == 0.0) g_point = 0.00001;

   g_atrHandle = iATR(_Symbol, PERIOD_CURRENT, 14);
   if(g_atrHandle == INVALID_HANDLE)
   {
      Print("[ACF] FAIL: iATR");
      return INIT_FAILED;
   }

   string logFile = "ACF_datalog_" + _Symbol + ".csv";
   g_fileHandle = FileOpen(logFile, FILE_WRITE|FILE_CSV|FILE_COMMON, ',');
   if(g_fileHandle != INVALID_HANDLE)
      FileWrite(g_fileHandle, "time","action","price","sl","tp","lot","acf1","regime","magic");

   Print("[ACF] Init OK. Period=", InpACFPeriod,
         " RevThresh=", InpACFBearish, " MomThresh=", InpACFBullish);
   return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   if(g_atrHandle != INVALID_HANDLE)
   { IndicatorRelease(g_atrHandle); g_atrHandle = INVALID_HANDLE; }
   if(g_fileHandle != INVALID_HANDLE)
   { FileClose(g_fileHandle); g_fileHandle = INVALID_HANDLE; }
}

//+------------------------------------------------------------------+
//| Calculate autocorrelation of returns at lag 1                     |
//| Uses closed bars only (shift >= 1)                                |
//+------------------------------------------------------------------+
double CalcACF1(int period)
{
   if(period < 4) return 0.0;

   // Need period+2 closes to compute period+1 returns and lag-1 ACF
   double closes[];
   ArraySetAsSeries(closes, true);
   int needed = period + 2;
   if(CopyClose(_Symbol, PERIOD_CURRENT, 1, needed, closes) != needed)
      return 0.0;

   // Compute returns: r[i] = close[i] - close[i+1] (series order: 0=newest)
   double returns[];
   ArrayResize(returns, period + 1);
   for(int i = 0; i < period + 1; i++)
      returns[i] = closes[i] - closes[i + 1];

   // Mean of returns[0..period-1] (the "current" set)
   double mean1 = 0.0;
   for(int i = 0; i < period; i++)
      mean1 += returns[i];
   mean1 /= period;

   // Mean of returns[1..period] (the "lagged" set)
   double mean2 = 0.0;
   for(int i = 1; i <= period; i++)
      mean2 += returns[i];
   mean2 /= period;

   // Covariance and variances
   double cov = 0.0, var1 = 0.0, var2 = 0.0;
   for(int i = 0; i < period; i++)
   {
      double d1 = returns[i] - mean1;
      double d2 = returns[i + 1] - mean2;
      cov  += d1 * d2;
      var1 += d1 * d1;
      var2 += d2 * d2;
   }

   double denom = MathSqrt(var1 * var2);
   if(denom == 0.0) return 0.0;

   return cov / denom;
}

//+------------------------------------------------------------------+
bool HasPosition()
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0) continue;
      if(PositionGetInteger(POSITION_MAGIC) == InpMagic &&
         PositionGetString(POSITION_SYMBOL) == _Symbol)
         return true;
   }
   return false;
}

//+------------------------------------------------------------------+
void CloseAllPositions()
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0) continue;
      if(PositionGetInteger(POSITION_MAGIC) != InpMagic) continue;
      if(PositionGetString(POSITION_SYMBOL) != _Symbol) continue;

      long posType = PositionGetInteger(POSITION_TYPE);
      double volume = PositionGetDouble(POSITION_VOLUME);

      MqlTradeRequest req = {};
      MqlTradeResult  res = {};
      req.action    = TRADE_ACTION_DEAL;
      req.position  = ticket;
      req.symbol    = _Symbol;
      req.volume    = volume;
      req.type      = (posType == POSITION_TYPE_BUY) ? ORDER_TYPE_SELL : ORDER_TYPE_BUY;
      req.price     = (posType == POSITION_TYPE_BUY) ?
                      SymbolInfoDouble(_Symbol, SYMBOL_BID) :
                      SymbolInfoDouble(_Symbol, SYMBOL_ASK);
      req.deviation = 20;
      req.magic     = InpMagic;

      if(!OrderSend(req, res))
         Print("[ACF] Close failed: ", res.comment);
   }
}

//+------------------------------------------------------------------+
double CalcLots(double slDistance)
{
   if(slDistance <= 0) return 0.0;
   double equity = AccountInfoDouble(ACCOUNT_EQUITY);
   double riskMoney = equity * InpRiskPct / 100.0;
   double tickValue = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
   double tickSize  = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   if(tickValue == 0.0 || tickSize == 0.0) return 0.0;

   double lots = riskMoney / (slDistance / tickSize * tickValue);
   double minLot  = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double maxLot  = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   double lotStep = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);

   lots = MathMin(lots, 1.0);
   lots = MathMin(lots, maxLot);
   lots = MathMax(lots, minLot);
   lots = MathFloor(lots / lotStep) * lotStep;
   return lots;
}

//+------------------------------------------------------------------+
double GetATR()
{
   double buf[1];
   if(CopyBuffer(g_atrHandle, 0, 1, 1, buf) != 1) return 0.0;
   return buf[0];
}

//+------------------------------------------------------------------+
bool SessionOK()
{
   MqlDateTime dt;
   TimeToStruct(TimeCurrent(), dt);

   if(InpSkipFriday && dt.day_of_week == 5) return false;
   if(dt.day_of_week == 6 || dt.day_of_week == 0) return false;

   return (dt.hour >= InpSessionStart && dt.hour < InpSessionEnd);
}

//+------------------------------------------------------------------+
bool IsNewBar()
{
   static datetime lastBar = 0;
   datetime curBar = iTime(_Symbol, PERIOD_CURRENT, 0);
   if(curBar == lastBar) return false;
   lastBar = curBar;
   return true;
}

//+------------------------------------------------------------------+
void OnTick()
{
   if(!IsNewBar()) return;

   bool hasPos = HasPosition();

   //=== EXIT: Max bars held ===
   if(hasPos)
   {
      g_barsHeld++;
      if(g_barsHeld >= InpMaxBars)
      {
         CloseAllPositions();
         g_barsHeld = 0;
      }
      return; // No new entries while in position
   }

   //=== ENTRY LOGIC ===
   if(!SessionOK()) return;

   // Calculate ACF(1)
   double acf1 = CalcACF1(InpACFPeriod);
   if(acf1 == 0.0) return;

   // Determine regime and signal
   int signal = 0; // +1 = buy, -1 = sell
   string regime = "DEAD";

   double lastReturn = iClose(_Symbol, PERIOD_CURRENT, 1) - iClose(_Symbol, PERIOD_CURRENT, 2);

   if(acf1 < InpACFBearish)
   {
      // Mean-reversion mode: FADE last bar direction
      regime = "REVERT";
      signal = (lastReturn > 0) ? -1 : +1;
   }
   else if(acf1 > InpACFBullish)
   {
      // Momentum mode: FOLLOW last bar direction
      regime = "MOMENTUM";
      signal = (lastReturn > 0) ? +1 : -1;
   }

   if(signal == 0) return;

   // Get ATR for SL
   double atr = GetATR();
   if(atr == 0.0) return;

   double slDist = atr * InpSL_ATR_Mult;
   double tpDist = slDist * InpRR;
   double lots = CalcLots(slDist);
   if(lots <= 0.0) return;

   // Spread check
   double spread = SymbolInfoInteger(_Symbol, SYMBOL_SPREAD) * g_point;
   if(spread > atr * 0.15) return; // Spread > 15% of ATR = skip

   // Place order
   MqlTradeRequest req = {};
   MqlTradeResult  res = {};
   req.action   = TRADE_ACTION_DEAL;
   req.symbol   = _Symbol;
   req.volume   = lots;
   req.deviation = 20;
   req.magic    = InpMagic;

   if(signal > 0) // BUY
   {
      req.type  = ORDER_TYPE_BUY;
      req.price = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
      req.sl    = req.price - slDist;
      req.tp    = req.price + tpDist;
      req.comment = "ACF_" + regime;
   }
   else // SELL
   {
      req.type  = ORDER_TYPE_SELL;
      req.price = SymbolInfoDouble(_Symbol, SYMBOL_BID);
      req.sl    = req.price + slDist;
      req.tp    = req.price - tpDist;
      req.comment = "ACF_" + regime;
   }

   if(!OrderSend(req, res))
   {
      Print("[ACF] Entry failed: ", res.comment, " retcode=", res.retcode);
   }
   else
   {
      g_barsHeld = 0;
      Print("[ACF] ", (signal > 0 ? "BUY" : "SELL"), " @ ", req.price,
            " SL=", req.sl, " TP=", req.tp,
            " ACF1=", DoubleToString(acf1, 4), " regime=", regime);

      if(g_fileHandle != INVALID_HANDLE)
      {
         int digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
         FileWrite(g_fileHandle, TimeToString(TimeCurrent()),
                   (signal > 0 ? "BUY" : "SELL"),
                   DoubleToString(req.price, digits),
                   DoubleToString(req.sl, digits),
                   DoubleToString(req.tp, digits),
                   DoubleToString(lots, 2),
                   DoubleToString(acf1, 4),
                   regime, IntegerToString(InpMagic));
      }
   }
}

//+------------------------------------------------------------------+
double OnTester()
{
   double profit = TesterStatistics(STAT_PROFIT);
   double trades = TesterStatistics(STAT_TRADES);
   double dd     = TesterStatistics(STAT_EQUITY_DDREL_PERCENT);
   if(dd == 0.0) dd = 1.0;
   if(trades < 50) return 0.0;
   return profit * MathSqrt(trades) / (1.0 + dd);
}
//+------------------------------------------------------------------+
