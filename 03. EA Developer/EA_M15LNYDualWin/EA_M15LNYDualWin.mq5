//+------------------------------------------------------------------+
//| EA_M15LNYDualWin.mq5 — London bias + dual-window PB continuation |
//| Symbol: USDJPY | Period: M15 | Magic: 880983                     |
//|                                                                   |
//| Hypothesis: HYP-LNY-DUALWIN-M15-001                                |
//| Structural cadence expand of LondonNY-class thick edge: ONE       |
//| London directional bias (closed-bar measure), TWO a-priori entry  |
//| windows (late-London PB + NY PB), max 1 trade per window / 2 day.|
//| NOT day-mine / NOT Mon-Wed skip from S530. Not LNY sole reopen.   |
//| Closed-bar[1] only. Mon–Thu; weekend flat; risk 0.5%; RR=2.0.     |
//+------------------------------------------------------------------+
#property copyright "SonicR / EA_M15LNYDualWin"
#property version   "1.00"
#property strict

#include <Trade\Trade.mqh>

input group "=== General ==="
input ulong    InpMagic         = 880983;
input int      InpDeviation     = 30;
input bool     InpKillSwitch    = false;

input group "=== London Bias ==="
input int      InpLdnStartH     = 9;
input int      InpLdnMeasureH   = 12;     // measure at closed bar in this hour
input double   InpTrendATRMult  = 0.50;   // |London move| >= ATR_D1 * this
input int      InpATRD1Period   = 14;

input group "=== Dual Windows (structural) ==="
input int      InpWin1StartH    = 12;     // late-London PB
input int      InpWin1EndH      = 15;
input int      InpWin2StartH    = 15;     // NY AM PB
input int      InpWin2EndH      = 18;
input int      InpPBLookback    = 3;
input double   InpPBMinATR      = 0.15;
input double   InpPBMaxATR      = 0.60;

input group "=== Session ==="
input int      InpFlatHour      = 20;
input bool     InpTradeMon      = true;
input bool     InpTradeTue      = true;
input bool     InpTradeWed      = true;
input bool     InpTradeThu      = true;
input bool     InpTradeFri      = false;

input group "=== Risk ==="
input double   InpRiskPct       = 0.50;
input double   InpMaxLot        = 1.0;
input double   InpSL_ATR_Mult   = 0.50;   // beyond PB extreme
input double   InpTP_Ratio      = 2.00;   // thick-edge RR
input int      InpMinSLPoints   = 50;
input int      InpMaxSLPoints   = 2000;
input int      InpMaxPerDay     = 2;      // one per window
input double   InpDailyDD       = 4.0;
input int      InpMaxHoldBars   = 24;
input int      InpMaxSpreadPts  = 50;

CTrade   g_trade;
int      g_hATRD1 = INVALID_HANDLE;
datetime g_lastBar = 0;
int      g_tradesToday = 0;
int      g_lastTradeDay = -1;
double   g_dayStartBalance = 0;
int      g_holdBars = 0;

double   g_ldnOpen = 0.0;
int      g_bias = 0;            // +1 / -1 / 0
bool     g_biasSet = false;
bool     g_win1Taken = false;
bool     g_win2Taken = false;

int OnInit()
{
   g_trade.SetExpertMagicNumber((long)InpMagic);
   g_trade.SetDeviationInPoints(InpDeviation);
   g_hATRD1 = iATR(_Symbol, PERIOD_D1, InpATRD1Period);
   if(g_hATRD1 == INVALID_HANDLE)
      return INIT_FAILED;
   g_dayStartBalance = AccountInfoDouble(ACCOUNT_BALANCE);
   Print("[LNY2] HYP-LNY-DUALWIN-M15-001");
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   if(g_hATRD1 != INVALID_HANDLE) IndicatorRelease(g_hATRD1);
}

int CountPositions()
{
   int c = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong t = PositionGetTicket(i);
      if(t > 0 &&
         PositionGetInteger(POSITION_MAGIC) == (long)InpMagic &&
         PositionGetString(POSITION_SYMBOL) == _Symbol)
         c++;
   }
   return c;
}

bool IsSuccessfulRetcode(const uint retcode)
{
   return(retcode == TRADE_RETCODE_DONE ||
          retcode == TRADE_RETCODE_PLACED ||
          retcode == TRADE_RETCODE_DONE_PARTIAL);
}

bool IsRetryableRetcode(const uint retcode)
{
   return(retcode == TRADE_RETCODE_REQUOTE ||
          retcode == TRADE_RETCODE_PRICE_CHANGED ||
          retcode == TRADE_RETCODE_PRICE_OFF ||
          retcode == TRADE_RETCODE_CONNECTION ||
          retcode == TRADE_RETCODE_TIMEOUT ||
          retcode == TRADE_RETCODE_TOO_MANY_REQUESTS ||
          retcode == TRADE_RETCODE_LOCKED);
}

int ResolveFillModes(ENUM_ORDER_TYPE_FILLING &primary, ENUM_ORDER_TYPE_FILLING &secondary)
{
   long fillMask = 0;
   primary = ORDER_FILLING_FOK;
   secondary = ORDER_FILLING_IOC;
   if(!SymbolInfoInteger(_Symbol, SYMBOL_FILLING_MODE, fillMask))
      return 2;
   int count = 0;
   if((fillMask & SYMBOL_FILLING_FOK) == SYMBOL_FILLING_FOK)
   {
      primary = ORDER_FILLING_FOK;
      count++;
   }
   if((fillMask & SYMBOL_FILLING_IOC) == SYMBOL_FILLING_IOC)
   {
      if(count == 0) primary = ORDER_FILLING_IOC;
      else secondary = ORDER_FILLING_IOC;
      count++;
   }
   if(count == 0)
      return 1;
   return count;
}

bool ValidateStops(const bool isBuy, const double entryPrice, const double sl, const double tp)
{
   long stopsLevel = 0;
   long freezeLevel = 0;
   SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL, stopsLevel);
   SymbolInfoInteger(_Symbol, SYMBOL_TRADE_FREEZE_LEVEL, freezeLevel);
   double minDistance = (double)MathMax(stopsLevel, freezeLevel) * _Point;
   if(minDistance <= 0.0)
      return true;
   if(isBuy)
      return ((entryPrice - sl) >= minDistance && (tp - entryPrice) >= minDistance);
   return ((sl - entryPrice) >= minDistance && (entryPrice - tp) >= minDistance);
}

bool SendDealWithRetry(const ENUM_ORDER_TYPE type, const double volume,
                       const double sl, const double tp, const ulong position,
                       const string comment, MqlTradeResult &res)
{
   ENUM_ORDER_TYPE_FILLING primaryMode, secondaryMode;
   int modeCount = ResolveFillModes(primaryMode, secondaryMode);
   for(int modeIdx = 0; modeIdx < modeCount; modeIdx++)
   {
      ENUM_ORDER_TYPE_FILLING activeMode = (modeIdx == 0 ? primaryMode : secondaryMode);
      for(int attempt = 0; attempt < 3; attempt++)
      {
         MqlTradeRequest req = {};
         MqlTradeResult tmp = {};
         req.action = TRADE_ACTION_DEAL;
         req.symbol = _Symbol;
         req.volume = volume;
         req.type = type;
         req.price = (type == ORDER_TYPE_BUY ? SymbolInfoDouble(_Symbol, SYMBOL_ASK)
                                             : SymbolInfoDouble(_Symbol, SYMBOL_BID));
         req.sl = sl;
         req.tp = tp;
         req.deviation = (ulong)InpDeviation;
         req.magic = InpMagic;
         req.position = position;
         req.comment = comment;
         req.type_filling = activeMode;
         if(position == 0 && sl > 0.0 && tp > 0.0 &&
            !ValidateStops(type == ORDER_TYPE_BUY, req.price, sl, tp))
            return false;
         ResetLastError();
         bool sent = OrderSend(req, tmp);
         res = tmp;
         if(sent && IsSuccessfulRetcode(res.retcode))
            return true;
         if(sent && !IsRetryableRetcode(res.retcode))
            return false;
         if(!sent && attempt == 2)
            return false;
         Sleep(100 * (1 << attempt));
      }
   }
   return false;
}

void CloseAll(const string reason)
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong t = PositionGetTicket(i);
      if(t <= 0 ||
         PositionGetInteger(POSITION_MAGIC) != (long)InpMagic ||
         PositionGetString(POSITION_SYMBOL) != _Symbol)
         continue;
      bool isBuy = (PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY);
      MqlTradeResult res = {};
      SendDealWithRetry(isBuy ? ORDER_TYPE_SELL : ORDER_TYPE_BUY,
                        PositionGetDouble(POSITION_VOLUME), 0.0, 0.0, t,
                        "LNY2|" + reason, res);
   }
}

bool IsDDExceeded()
{
   if(g_dayStartBalance <= 0.0)
      return false;
   return ((g_dayStartBalance - AccountInfoDouble(ACCOUNT_EQUITY)) /
           g_dayStartBalance * 100.0) >= InpDailyDD;
}

bool IsTradeDay(const int dow)
{
   if(dow == 1) return InpTradeMon;
   if(dow == 2) return InpTradeTue;
   if(dow == 3) return InpTradeWed;
   if(dow == 4) return InpTradeThu;
   if(dow == 5) return InpTradeFri;
   return false;
}

double CalcLot(const double slDist)
{
   if(slDist <= 0.0)
      return 0.0;
   double bal = AccountInfoDouble(ACCOUNT_BALANCE);
   double riskCash = bal * InpRiskPct / 100.0;
   double tv = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
   double ts = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   if(tv <= 0.0 || ts <= 0.0)
      return 0.0;
   double lot = riskCash / (slDist / ts * tv);
   lot = MathMin(lot, InpMaxLot);
   lot = MathMin(lot, SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX));
   lot = MathMax(lot, SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN));
   double step = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   if(step > 0.0)
      lot = MathFloor(lot / step) * step;
   return lot;
}

void CaptureLondonOpen(const int hour)
{
   if(g_ldnOpen > 0.0)
      return;
   // First closed bar whose hour is London start (bar[1] hour == start).
   if(hour == InpLdnStartH)
      g_ldnOpen = iOpen(_Symbol, PERIOD_CURRENT, 1);
}

void MeasureLondonBias(const int hour)
{
   if(g_biasSet || g_ldnOpen <= 0.0)
      return;
   if(hour != InpLdnMeasureH)
      return;

   double atr[];
   ArraySetAsSeries(atr, true);
   if(CopyBuffer(g_hATRD1, 0, 1, 1, atr) < 1 || atr[0] <= 0.0)
      return;

   double close1 = iClose(_Symbol, PERIOD_CURRENT, 1);
   double move = close1 - g_ldnOpen;
   double thr = atr[0] * InpTrendATRMult;
   g_biasSet = true;
   if(move > thr)
      g_bias = +1;
   else if(move < -thr)
      g_bias = -1;
   else
      g_bias = 0;
}

int ActiveWindow(const int hour)
{
   if(hour >= InpWin1StartH && hour < InpWin1EndH)
      return 1;
   if(hour >= InpWin2StartH && hour < InpWin2EndH)
      return 2;
   return 0;
}

bool WindowAvailable(const int win)
{
   if(win == 1) return !g_win1Taken;
   if(win == 2) return !g_win2Taken;
   return false;
}

bool FindPullback(const double atrD1, double &pbExtreme)
{
   pbExtreme = 0.0;
   double close1 = iClose(_Symbol, PERIOD_CURRENT, 1);
   double open1  = iOpen(_Symbol, PERIOD_CURRENT, 1);
   double recentHigh = -1.0e100;
   double recentLow  =  1.0e100;
   for(int i = 1; i <= InpPBLookback; i++)
   {
      double hi = iHigh(_Symbol, PERIOD_CURRENT, i);
      double lo = iLow(_Symbol, PERIOD_CURRENT, i);
      if(hi > recentHigh) recentHigh = hi;
      if(lo < recentLow)  recentLow = lo;
   }
   double depth = recentHigh - recentLow;
   if(depth < atrD1 * InpPBMinATR || depth > atrD1 * InpPBMaxATR)
      return false;

   if(g_bias > 0)
   {
      if(close1 > open1)
      {
         pbExtreme = recentLow;
         return true;
      }
   }
   else if(g_bias < 0)
   {
      if(close1 < open1)
      {
         pbExtreme = recentHigh;
         return true;
      }
   }
   return false;
}

void OnTick()
{
   if(InpKillSwitch)
      return;

   datetime barTime = iTime(_Symbol, PERIOD_CURRENT, 0);
   if(barTime == 0 || barTime == g_lastBar)
      return;
   g_lastBar = barTime;

   datetime bar1Time = iTime(_Symbol, PERIOD_CURRENT, 1);
   if(bar1Time == 0)
      return;

   MqlDateTime dt;
   TimeToStruct(bar1Time, dt);
   int dayKey = dt.year * 1000 + dt.day_of_year;
   if(dayKey != g_lastTradeDay)
   {
      g_lastTradeDay = dayKey;
      g_tradesToday = 0;
      g_dayStartBalance = AccountInfoDouble(ACCOUNT_BALANCE);
      g_ldnOpen = 0.0;
      g_bias = 0;
      g_biasSet = false;
      g_win1Taken = false;
      g_win2Taken = false;
   }

   if(CountPositions() > 0)
   {
      g_holdBars++;
      if(g_holdBars >= InpMaxHoldBars || dt.hour >= InpFlatHour ||
         dt.day_of_week == 5 || dt.day_of_week == 0 || dt.day_of_week == 6)
         CloseAll("flat");
      return;
   }
   g_holdBars = 0;

   if(dt.hour >= InpFlatHour || dt.day_of_week == 5 ||
      dt.day_of_week == 0 || dt.day_of_week == 6)
      return;
   if(!IsTradeDay(dt.day_of_week))
      return;

   CaptureLondonOpen(dt.hour);
   MeasureLondonBias(dt.hour);

   if(!g_biasSet || g_bias == 0)
      return;
   if(g_tradesToday >= InpMaxPerDay || IsDDExceeded())
      return;
   if(SymbolInfoInteger(_Symbol, SYMBOL_SPREAD) > InpMaxSpreadPts)
      return;

   int win = ActiveWindow(dt.hour);
   if(win == 0 || !WindowAvailable(win))
      return;

   double atr[];
   ArraySetAsSeries(atr, true);
   if(CopyBuffer(g_hATRD1, 0, 1, 1, atr) < 1 || atr[0] <= 0.0)
      return;

   double pbExtreme = 0.0;
   if(!FindPullback(atr[0], pbExtreme))
      return;

   bool isBuy = (g_bias > 0);
   double entry = (isBuy ? SymbolInfoDouble(_Symbol, SYMBOL_ASK)
                         : SymbolInfoDouble(_Symbol, SYMBOL_BID));
   double slRaw = (isBuy ? pbExtreme - atr[0] * InpSL_ATR_Mult
                         : pbExtreme + atr[0] * InpSL_ATR_Mult);
   double slDist = MathAbs(entry - slRaw);
   if(slDist < InpMinSLPoints * _Point)
      slDist = InpMinSLPoints * _Point;
   if(slDist > InpMaxSLPoints * _Point)
      return;

   double sl = (isBuy ? entry - slDist : entry + slDist);
   double tp = (isBuy ? entry + slDist * InpTP_Ratio : entry - slDist * InpTP_Ratio);
   int digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
   sl = NormalizeDouble(sl, digits);
   tp = NormalizeDouble(tp, digits);
   double lot = CalcLot(slDist);
   if(lot <= 0.0)
      return;

   string cmt = (win == 1 ? "LNY2|w1" : "LNY2|w2");
   MqlTradeResult res = {};
   if(!SendDealWithRetry(isBuy ? ORDER_TYPE_BUY : ORDER_TYPE_SELL, lot, sl, tp, 0, cmt, res))
      return;
   if(IsSuccessfulRetcode(res.retcode))
   {
      g_tradesToday++;
      g_holdBars = 0;
      if(win == 1) g_win1Taken = true;
      if(win == 2) g_win2Taken = true;
   }
}

double OnTester()
{
   double pf = TesterStatistics(STAT_PROFIT_FACTOR);
   double n  = TesterStatistics(STAT_TRADES);
   if(n < 20.0)
      return 0.0;
   return pf * MathSqrt(n);
}
//+------------------------------------------------------------------+
