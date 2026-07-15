//+------------------------------------------------------------------+
//| EA_H1BOS_M15Pullback.mq5 — H1 BOS then M15 EMA pullback          |
//| Symbol: USDJPY | Period: M15 | Magic: 880972                     |
//|                                                                   |
//| Hypothesis: HYP-H1-BOS-M15-PB-001                                  |
//| H1 closed-bar swing break (L=3) sets bias; M15 entry on pullback  |
//| to EMA20 in bias direction. Not ITSM FVG/OB, not SB KZ, not ORB. |
//| Closed-bar[1] only. Mon–Thu a priori.                             |
//+------------------------------------------------------------------+
#property copyright "SonicR / EA_H1BOS_M15Pullback"
#property version   "1.00"
#property strict

#include <Trade\Trade.mqh>

input group "=== General ==="
input ulong    InpMagic         = 880972;
input int      InpDeviation     = 30;
input bool     InpKillSwitch    = false;

input group "=== H1 BOS ==="
input int      InpSwingL        = 3;      // H1 pivot lookback each side
input int      InpBOSMaxAgeH1   = 24;     // max H1 bars since BOS

input group "=== M15 Pullback ==="
input int      InpEMAPeriod     = 20;
input double   InpTouchATR      = 0.35;   // |close-EMA| / ATR max for touch
input double   InpBounceATR     = 0.15;   // closed reclaim away from EMA

input group "=== Session ==="
input int      InpStartHour     = 7;
input int      InpEndHour       = 18;
input int      InpFlatHour      = 21;
input bool     InpTradeMon      = true;
input bool     InpTradeTue      = true;
input bool     InpTradeWed      = true;
input bool     InpTradeThu      = true;
input bool     InpTradeFri      = false;

input group "=== Risk ==="
input double   InpRiskPct       = 0.50;
input double   InpMaxLot        = 1.0;
input double   InpSL_ATR_Mult   = 1.50;
input int      InpMinSLPoints   = 50;
input int      InpMaxSLPoints   = 1200;
input double   InpTP_Ratio      = 1.50;
input int      InpMaxPerDay     = 2;
input double   InpDailyDD       = 4.0;
input int      InpMaxHoldBars   = 32;
input int      InpMaxSpreadPts  = 50;
input int      InpATRPeriod     = 14;

CTrade   g_trade;
int      g_hATR = INVALID_HANDLE;
int      g_hEMA = INVALID_HANDLE;
datetime g_lastBar = 0;
int      g_tradesToday = 0;
int      g_lastTradeDay = -1;
double   g_dayStartBalance = 0;
int      g_holdBars = 0;

int      g_bosDir = 0;       // +1 bullish BOS, -1 bearish
datetime g_bosH1Time = 0;

int OnInit()
{
   g_trade.SetExpertMagicNumber((long)InpMagic);
   g_trade.SetDeviationInPoints(InpDeviation);
   g_hATR = iATR(_Symbol, PERIOD_CURRENT, InpATRPeriod);
   g_hEMA = iMA(_Symbol, PERIOD_CURRENT, InpEMAPeriod, 0, MODE_EMA, PRICE_CLOSE);
   if(g_hATR == INVALID_HANDLE || g_hEMA == INVALID_HANDLE)
      return INIT_FAILED;
   g_dayStartBalance = AccountInfoDouble(ACCOUNT_BALANCE);
   Print("[HBOS] HYP-H1-BOS-M15-PB-001");
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   if(g_hATR != INVALID_HANDLE) IndicatorRelease(g_hATR);
   if(g_hEMA != INVALID_HANDLE) IndicatorRelease(g_hEMA);
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
                        "HBOS|" + reason, res);
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

bool IsH1SwingHigh(const int shift)
{
   // pivot confirmed at closed H1 bar `shift` with L bars each side (all closed)
   int L = InpSwingL;
   double mid = iHigh(_Symbol, PERIOD_H1, shift);
   for(int i = 1; i <= L; i++)
   {
      if(iHigh(_Symbol, PERIOD_H1, shift + i) >= mid)
         return false;
      if(iHigh(_Symbol, PERIOD_H1, shift - i) > mid)
         return false;
   }
   return true;
}

bool IsH1SwingLow(const int shift)
{
   int L = InpSwingL;
   double mid = iLow(_Symbol, PERIOD_H1, shift);
   for(int i = 1; i <= L; i++)
   {
      if(iLow(_Symbol, PERIOD_H1, shift + i) <= mid)
         return false;
      if(iLow(_Symbol, PERIOD_H1, shift - i) < mid)
         return false;
   }
   return true;
}

void UpdateH1BOS()
{
   // Need enough H1 history: pivot at shift=L+1 confirmed using bars through shift=1
   int L = InpSwingL;
   int pivotShift = L + 1;
   if(Bars(_Symbol, PERIOD_H1) < pivotShift + L + 5)
      return;

   double c1 = iClose(_Symbol, PERIOD_H1, 1);
   datetime t1 = iTime(_Symbol, PERIOD_H1, 1);

   // Find most recent confirmed swing high/low older than bar[1]
   double lastSH = 0.0;
   double lastSL = 0.0;
   datetime shTime = 0;
   datetime slTime = 0;
   for(int s = pivotShift; s < pivotShift + 40; s++)
   {
      if(lastSH <= 0.0 && IsH1SwingHigh(s))
      {
         lastSH = iHigh(_Symbol, PERIOD_H1, s);
         shTime = iTime(_Symbol, PERIOD_H1, s);
      }
      if(lastSL <= 0.0 && IsH1SwingLow(s))
      {
         lastSL = iLow(_Symbol, PERIOD_H1, s);
         slTime = iTime(_Symbol, PERIOD_H1, s);
      }
      if(lastSH > 0.0 && lastSL > 0.0)
         break;
   }

   // BOS: closed H1[1] breaks last swing in that direction
   if(lastSH > 0.0 && c1 > lastSH)
   {
      g_bosDir = +1;
      g_bosH1Time = t1;
   }
   else if(lastSL > 0.0 && c1 < lastSL)
   {
      g_bosDir = -1;
      g_bosH1Time = t1;
   }

   // Age out
   if(g_bosDir != 0 && g_bosH1Time > 0)
   {
      int age = iBarShift(_Symbol, PERIOD_H1, g_bosH1Time, true);
      if(age < 0 || age > InpBOSMaxAgeH1)
      {
         g_bosDir = 0;
         g_bosH1Time = 0;
      }
   }
}

int GetSignal()
{
   if(g_bosDir == 0)
      return 0;

   double atr[], ema[];
   ArraySetAsSeries(atr, true);
   ArraySetAsSeries(ema, true);
   if(CopyBuffer(g_hATR, 0, 1, 1, atr) < 1 || atr[0] <= 0.0)
      return 0;
   if(CopyBuffer(g_hEMA, 0, 1, 2, ema) < 2)
      return 0;

   double c1 = iClose(_Symbol, PERIOD_CURRENT, 1);
   double c2 = iClose(_Symbol, PERIOD_CURRENT, 2);
   double dist1 = MathAbs(c1 - ema[0]) / atr[0];
   double dist2 = MathAbs(c2 - ema[1]) / atr[0];

   // Pullback: prior bar near EMA, current closes away in BOS direction
   if(g_bosDir > 0)
   {
      if(dist2 <= InpTouchATR && c2 <= ema[1] + InpTouchATR * atr[0] &&
         c1 > ema[0] + InpBounceATR * atr[0] && c1 > c2)
         return +1;
   }
   else if(g_bosDir < 0)
   {
      if(dist2 <= InpTouchATR && c2 >= ema[1] - InpTouchATR * atr[0] &&
         c1 < ema[0] - InpBounceATR * atr[0] && c1 < c2)
         return -1;
   }
   return 0;
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
   }

   UpdateH1BOS();

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
   if(dt.hour < InpStartHour || dt.hour >= InpEndHour)
      return;
   if(!IsTradeDay(dt.day_of_week))
      return;
   if(g_tradesToday >= InpMaxPerDay || IsDDExceeded())
      return;
   if(SymbolInfoInteger(_Symbol, SYMBOL_SPREAD) > InpMaxSpreadPts)
      return;

   int signal = GetSignal();
   if(signal == 0)
      return;

   double atr[];
   ArraySetAsSeries(atr, true);
   if(CopyBuffer(g_hATR, 0, 1, 1, atr) < 1)
      return;

   double slDist = atr[0] * InpSL_ATR_Mult;
   if(slDist < InpMinSLPoints * _Point)
      slDist = InpMinSLPoints * _Point;
   if(slDist > InpMaxSLPoints * _Point)
      return;

   bool isBuy = (signal == +1);
   double entry = (isBuy ? SymbolInfoDouble(_Symbol, SYMBOL_ASK)
                         : SymbolInfoDouble(_Symbol, SYMBOL_BID));
   double sl = (isBuy ? entry - slDist : entry + slDist);
   double tp = (isBuy ? entry + slDist * InpTP_Ratio : entry - slDist * InpTP_Ratio);
   int digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
   sl = NormalizeDouble(sl, digits);
   tp = NormalizeDouble(tp, digits);
   double lot = CalcLot(slDist);
   if(lot <= 0.0)
      return;

   MqlTradeResult res = {};
   if(!SendDealWithRetry(isBuy ? ORDER_TYPE_BUY : ORDER_TYPE_SELL, lot, sl, tp, 0,
                         "HBOS|pb", res))
      return;
   if(IsSuccessfulRetcode(res.retcode))
   {
      g_tradesToday++;
      g_holdBars = 0;
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
