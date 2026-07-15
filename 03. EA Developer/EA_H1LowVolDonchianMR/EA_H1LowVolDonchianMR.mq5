//+------------------------------------------------------------------+
//| EA_H1LowVolDonchianMR.mq5 — H1 low-vol Donchian mean-reversion    |
//| Symbol: USDJPY | Period: H1 | Magic: 880960                        |
//|                                                                    |
//| Hypothesis: HYP-H1-LOWVOL-DONCHIAN-MR-001                           |
//| When ATR14 / SMA50(ATR) <= 0.85, fade Donchian(20) extremes toward |
//| midline on closed H1 bar[1]. Opposite of HYP-H1-ATR-REGIME-MOM-001.|
//| Mon–Thu a priori; weekend flat; risk 0.5%. No threshold mining.   |
//+------------------------------------------------------------------+
#property copyright "SonicR / EA_H1LowVolDonchianMR"
#property version   "1.00"
#property strict

#include <Trade\Trade.mqh>

input group "=== General ==="
input ulong    InpMagic         = 880960;
input int      InpDeviation     = 30;
input bool     InpKillSwitch    = false;

input group "=== Low-vol Donchian ==="
input int      InpATRPeriod     = 14;
input int      InpATRSlow       = 50;
input double   InpATRRatioMax   = 0.85;   // compressed-vol gate (frozen)
input int      InpDonchianLen   = 20;
input double   InpSLBufferATR   = 0.20;

input group "=== Session (server hours) ==="
input int      InpTradeStart    = 1;
input int      InpTradeEnd      = 21;
input int      InpFlatHour      = 22;
input bool     InpTradeMon      = true;
input bool     InpTradeTue      = true;
input bool     InpTradeWed      = true;
input bool     InpTradeThu      = true;
input bool     InpTradeFri      = false;

input group "=== Risk ==="
input double   InpRiskPct       = 0.50;
input double   InpMaxLot        = 1.0;
input double   InpMinTP_R       = 1.0;    // floor if midline closer than SL
input int      InpMinSLPoints   = 80;
input int      InpMaxSLPoints   = 2500;
input int      InpMaxPerDay     = 1;
input double   InpDailyDD       = 4.0;
input int      InpMaxHoldBars   = 24;
input int      InpMaxSpreadPts  = 50;

CTrade   g_trade;
int      g_hATR  = INVALID_HANDLE;
datetime g_lastBar = 0;
int      g_tradesToday = 0;
int      g_lastTradeDay = -1;
double   g_dayStartBalance = 0;
int      g_holdBars = 0;

int OnInit()
{
   if(Period() != PERIOD_H1)
   {
      Print("[H1DCH] FAIL — chart must be H1");
      return INIT_FAILED;
   }
   g_trade.SetExpertMagicNumber((long)InpMagic);
   g_trade.SetDeviationInPoints(InpDeviation);
   g_hATR = iATR(_Symbol, PERIOD_H1, InpATRPeriod);
   if(g_hATR == INVALID_HANDLE)
      return INIT_FAILED;
   g_dayStartBalance = AccountInfoDouble(ACCOUNT_BALANCE);
   PrintFormat("[H1DCH] HYP-H1-LOWVOL-DONCHIAN-MR-001 | ATRRatio<=%.2f Donch=%d risk=%.2f%%",
               InpATRRatioMax, InpDonchianLen, InpRiskPct);
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   if(g_hATR != INVALID_HANDLE) IndicatorRelease(g_hATR);
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
         double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
         double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
         MqlTradeRequest req = {};
         MqlTradeResult tmp = {};
         req.action   = TRADE_ACTION_DEAL;
         req.symbol   = _Symbol;
         req.volume   = volume;
         req.type     = type;
         req.price    = (type == ORDER_TYPE_BUY ? ask : bid);
         req.sl       = sl;
         req.tp       = tp;
         req.deviation = (ulong)InpDeviation;
         req.magic    = InpMagic;
         req.position = position;
         req.comment  = comment;
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
                        "H1DCH|" + reason, res);
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

// Closed H1 bar[1]: low-vol + fade Donchian extreme.
// Returns +1 fade-up (buy), -1 fade-down (sell), 0 none.
// Also fills upper/lower/mid via refs.
int GetSignal(double &upper, double &lower, double &mid, double &atr1)
{
   upper = lower = mid = atr1 = 0.0;
   int need = MathMax(InpATRSlow, InpDonchianLen) + 3;
   double atr[];
   ArraySetAsSeries(atr, true);
   if(CopyBuffer(g_hATR, 0, 1, need, atr) < need)
      return 0;
   if(atr[0] <= 0.0)
      return 0;
   atr1 = atr[0];

   double sum = 0.0;
   for(int i = 0; i < InpATRSlow; i++)
   {
      if(atr[i] <= 0.0)
         return 0;
      sum += atr[i];
   }
   double atrSlow = sum / (double)InpATRSlow;
   if(atrSlow <= 0.0)
      return 0;
   if((atr[0] / atrSlow) > InpATRRatioMax)
      return 0;

   // Donchian from closed bars [1..Len] — exclude forming bar[0]
   double hi = -1.0e100;
   double lo =  1.0e100;
   for(int i = 1; i <= InpDonchianLen; i++)
   {
      double h = iHigh(_Symbol, PERIOD_H1, i);
      double l = iLow(_Symbol, PERIOD_H1, i);
      if(h <= 0.0 || l <= 0.0)
         return 0;
      if(h > hi) hi = h;
      if(l < lo) lo = l;
   }
   if(hi <= lo)
      return 0;
   upper = hi;
   lower = lo;
   mid = 0.5 * (hi + lo);

   double bC = iClose(_Symbol, PERIOD_H1, 1);
   if(bC >= upper)
      return -1; // fade down
   if(bC <= lower)
      return +1; // fade up
   return 0;
}

void OnTick()
{
   if(InpKillSwitch)
      return;

   datetime barTime = iTime(_Symbol, PERIOD_H1, 0);
   if(barTime == 0 || barTime == g_lastBar)
      return;
   g_lastBar = barTime;

   datetime bar1Time = iTime(_Symbol, PERIOD_H1, 1);
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
   if(dt.hour < InpTradeStart || dt.hour >= InpTradeEnd)
      return;
   if(g_tradesToday >= InpMaxPerDay || IsDDExceeded())
      return;

   long spread = SymbolInfoInteger(_Symbol, SYMBOL_SPREAD);
   if(spread > InpMaxSpreadPts)
      return;

   double upper, lower, mid, atr1;
   int signal = GetSignal(upper, lower, mid, atr1);
   if(signal == 0 || atr1 <= 0.0)
      return;

   bool isBuy = (signal == +1);
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double entry = (isBuy ? ask : bid);

   double extreme = (isBuy ? lower : upper);
   double slDist = MathAbs(entry - extreme) + atr1 * InpSLBufferATR;
   if(slDist < InpMinSLPoints * _Point)
      slDist = InpMinSLPoints * _Point;
   if(slDist > InpMaxSLPoints * _Point)
      return;

   double sl = (isBuy ? entry - slDist : entry + slDist);
   double tpMidDist = MathAbs(mid - entry);
   double tpDist = tpMidDist;
   if(tpDist < slDist * InpMinTP_R)
      tpDist = slDist * InpMinTP_R;
   double tp = (isBuy ? entry + tpDist : entry - tpDist);

   int digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
   sl = NormalizeDouble(sl, digits);
   tp = NormalizeDouble(tp, digits);

   double lot = CalcLot(slDist);
   if(lot <= 0.0)
      return;

   MqlTradeResult res = {};
   if(!SendDealWithRetry(isBuy ? ORDER_TYPE_BUY : ORDER_TYPE_SELL, lot, sl, tp, 0,
                         "H1DCH|mr", res))
      return;

   if(IsSuccessfulRetcode(res.retcode))
   {
      g_tradesToday++;
      g_holdBars = 0;
      PrintFormat("[H1DCH] %s lot=%.2f @ %.5f mid=%.5f ATR=%.5f",
                  isBuy ? "BUY" : "SELL", lot, res.price, mid, atr1);
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
