//+------------------------------------------------------------------+
//| SparkAsian_Module.mqh                                            |
//| Sleeve B for EA_SBSparkBook — extracted from EA_M15SparkAsian    |
//| Binding: run 20260714_002614 defaults (Model0 screen)            |
//|                                                                  |
//| Interface:                                                       |
//|   bool SPK_Init(string symbol, ulong magic, int deviation)       |
//|   void SPK_Deinit()                                              |
//|   void SPK_OnTick(string symbol, ulong magic,                    |
//|                   double riskPct, double maxLot)                 |
//|                                                                  |
//| Closed-bar[1] only; D1 EMA uses shift>=1.                        |
//+------------------------------------------------------------------+
#ifndef SPARK_ASIAN_MODULE_MQH
#define SPARK_ASIAN_MODULE_MQH

#include <Trade\Trade.mqh>

// Frozen defaults matching EA_M15SparkAsian / 20260714_002614
#define SPK_ASIAN_START     0
#define SPK_ASIAN_END       8
#define SPK_BRK_BUF_ATR     0.15
#define SPK_BODY_RATIO      0.35
#define SPK_RANGE_MIN_ATR   0.80
#define SPK_RANGE_MAX_ATR   8.00
#define SPK_ATR_PERIOD      14
#define SPK_EMA_PERIOD      50
#define SPK_USE_TREND       true
#define SPK_LDN_START       9
#define SPK_LDN_END         13
#define SPK_NY_ENABLED      true
#define SPK_NY_START        15
#define SPK_NY_END          18
#define SPK_FLAT_HOUR       21
#define SPK_TRADE_MON       false
#define SPK_TRADE_TUE       true
#define SPK_TRADE_WED       true
#define SPK_TRADE_THU       false
#define SPK_TRADE_FRI       false
#define SPK_TP_RATIO        1.50
#define SPK_SL_BUF_ATR      0.20
#define SPK_BE_ENABLED      true
#define SPK_BE_RATIO        1.0
#define SPK_MAX_HOLD_BARS   24
#define SPK_MAX_SPREAD      50
#define SPK_MAX_PER_DAY     2
#define SPK_DAILY_DD        4.0
#define SPK_COMMENT         "SPKA"

CTrade   g_spkTrade;
int      g_spkHatr    = INVALID_HANDLE;
int      g_spkHemaD1  = INVALID_HANDLE;
datetime g_spkLastBar = 0;
int      g_spkTradesToday = 0;
int      g_spkLastTradeDay = -1;
double   g_spkDayStartBal = 0;
int      g_spkHoldBars = 0;
bool     g_spkBeMoved = false;
double   g_spkAsianHi = 0;
double   g_spkAsianLo = 99999.0;
bool     g_spkRangeLocked = false;
bool     g_spkRangeValid  = false;
string   g_spkSymbol = "";
int      g_spkDeviation = 30;

int  SPK_CountPositions(ulong magic, string symbol);
bool SPK_IsSuccessfulRetcode(const uint retcode);
bool SPK_IsRetryableRetcode(const uint retcode);
int  SPK_ResolveFillModes(string symbol, ENUM_ORDER_TYPE_FILLING &primary,
                          ENUM_ORDER_TYPE_FILLING &secondary);
bool SPK_ValidateStops(string symbol, const bool isBuy, const double entryPrice,
                       const double sl, const double tp);
bool SPK_SendDealWithRetry(string symbol, ulong magic, const ENUM_ORDER_TYPE type,
                           const double volume, const double sl, const double tp,
                           const ulong position, const string comment,
                           MqlTradeResult &res);
void SPK_CloseAll(string symbol, ulong magic, const string reason);
bool SPK_IsDDExceeded();
double SPK_CalcLot(string symbol, double riskPct, double maxLot, const double slDist);
bool SPK_IsTradeDay(const int dow);
double SPK_GetATR1();
int  SPK_GetTrendBias(string symbol);
void SPK_ResetDay();
void SPK_LockRange(const double atr);
void SPK_ManageOpen(string symbol, ulong magic, const int hour);
int  SPK_GetBreakoutSignal(string symbol, const double atr);
void SPK_TryEntry(string symbol, ulong magic, double riskPct, double maxLot,
                  const double atr, const string session);

bool SPK_Init(string symbol, ulong magic, int deviation)
{
   g_spkSymbol = symbol;
   g_spkDeviation = deviation;
   g_spkTrade.SetExpertMagicNumber((long)magic);
   g_spkTrade.SetDeviationInPoints(deviation);

   g_spkHatr = iATR(symbol, PERIOD_CURRENT, SPK_ATR_PERIOD);
   if(SPK_USE_TREND)
      g_spkHemaD1 = iMA(symbol, PERIOD_D1, SPK_EMA_PERIOD, 0, MODE_EMA, PRICE_CLOSE);

   if(g_spkHatr == INVALID_HANDLE)
      return false;
   if(SPK_USE_TREND && g_spkHemaD1 == INVALID_HANDLE)
      return false;

   g_spkDayStartBal = AccountInfoDouble(ACCOUNT_BALANCE);
   g_spkLastBar = 0;
   g_spkTradesToday = 0;
   g_spkLastTradeDay = -1;
   g_spkHoldBars = 0;
   g_spkBeMoved = false;
   g_spkAsianHi = 0;
   g_spkAsianLo = 99999.0;
   g_spkRangeLocked = false;
   g_spkRangeValid = false;

   PrintFormat("[SPKA] sleeve init | Asian[%d,%d) TP=%.2fR magic=%I64u",
               SPK_ASIAN_START, SPK_ASIAN_END, SPK_TP_RATIO, magic);
   return true;
}

void SPK_Deinit()
{
   if(g_spkHatr != INVALID_HANDLE) { IndicatorRelease(g_spkHatr); g_spkHatr = INVALID_HANDLE; }
   if(g_spkHemaD1 != INVALID_HANDLE) { IndicatorRelease(g_spkHemaD1); g_spkHemaD1 = INVALID_HANDLE; }
}

int SPK_CountPositions(ulong magic, string symbol)
{
   int c = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong t = PositionGetTicket(i);
      if(t > 0 &&
         PositionGetInteger(POSITION_MAGIC) == (long)magic &&
         PositionGetString(POSITION_SYMBOL) == symbol)
         c++;
   }
   return c;
}

bool SPK_IsSuccessfulRetcode(const uint retcode)
{
   return(retcode == TRADE_RETCODE_DONE ||
          retcode == TRADE_RETCODE_PLACED ||
          retcode == TRADE_RETCODE_DONE_PARTIAL);
}

bool SPK_IsRetryableRetcode(const uint retcode)
{
   return(retcode == TRADE_RETCODE_REQUOTE ||
          retcode == TRADE_RETCODE_PRICE_CHANGED ||
          retcode == TRADE_RETCODE_PRICE_OFF ||
          retcode == TRADE_RETCODE_CONNECTION ||
          retcode == TRADE_RETCODE_TIMEOUT ||
          retcode == TRADE_RETCODE_TOO_MANY_REQUESTS ||
          retcode == TRADE_RETCODE_LOCKED);
}

int SPK_ResolveFillModes(string symbol, ENUM_ORDER_TYPE_FILLING &primary,
                         ENUM_ORDER_TYPE_FILLING &secondary)
{
   long fillMask = 0;
   primary = ORDER_FILLING_FOK;
   secondary = ORDER_FILLING_IOC;
   if(!SymbolInfoInteger(symbol, SYMBOL_FILLING_MODE, fillMask))
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

bool SPK_ValidateStops(string symbol, const bool isBuy, const double entryPrice,
                       const double sl, const double tp)
{
   long stopsLevel = 0;
   long freezeLevel = 0;
   SymbolInfoInteger(symbol, SYMBOL_TRADE_STOPS_LEVEL, stopsLevel);
   SymbolInfoInteger(symbol, SYMBOL_TRADE_FREEZE_LEVEL, freezeLevel);
   double point = SymbolInfoDouble(symbol, SYMBOL_POINT);
   double minDistance = (double)MathMax(stopsLevel, freezeLevel) * point;
   if(minDistance <= 0.0)
      return true;
   if(isBuy)
      return ((entryPrice - sl) >= minDistance && (tp - entryPrice) >= minDistance);
   return ((sl - entryPrice) >= minDistance && (entryPrice - tp) >= minDistance);
}

bool SPK_SendDealWithRetry(string symbol, ulong magic, const ENUM_ORDER_TYPE type,
                           const double volume, const double sl, const double tp,
                           const ulong position, const string comment,
                           MqlTradeResult &res)
{
   ENUM_ORDER_TYPE_FILLING primaryMode, secondaryMode;
   int modeCount = SPK_ResolveFillModes(symbol, primaryMode, secondaryMode);
   int digits = (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS);

   for(int modeIdx = 0; modeIdx < modeCount; modeIdx++)
   {
      ENUM_ORDER_TYPE_FILLING activeMode = (modeIdx == 0 ? primaryMode : secondaryMode);
      for(int attempt = 0; attempt < 3; attempt++)
      {
         double ask = SymbolInfoDouble(symbol, SYMBOL_ASK);
         double bid = SymbolInfoDouble(symbol, SYMBOL_BID);
         MqlTradeRequest req = {};
         MqlTradeResult tmp = {};
         req.action    = TRADE_ACTION_DEAL;
         req.symbol    = symbol;
         req.volume    = volume;
         req.type      = type;
         req.price     = (type == ORDER_TYPE_BUY ? ask : bid);
         req.sl        = NormalizeDouble(sl, digits);
         req.tp        = NormalizeDouble(tp, digits);
         req.deviation = (ulong)g_spkDeviation;
         req.magic     = magic;
         req.position  = position;
         req.comment   = comment;
         req.type_filling = activeMode;

         if(position == 0 && sl > 0.0 && tp > 0.0 &&
            !SPK_ValidateStops(symbol, type == ORDER_TYPE_BUY, req.price, sl, tp))
            return false;

         ResetLastError();
         bool sent = OrderSend(req, tmp);
         res = tmp;

         if(sent && SPK_IsSuccessfulRetcode(res.retcode))
            return true;
         if(sent && !SPK_IsRetryableRetcode(res.retcode))
            return false;
         if(!sent && attempt == 2)
            return false;

         Sleep(100 * (1 << attempt));
      }
   }
   return false;
}

void SPK_CloseAll(string symbol, ulong magic, const string reason)
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong t = PositionGetTicket(i);
      if(t <= 0 ||
         PositionGetInteger(POSITION_MAGIC) != (long)magic ||
         PositionGetString(POSITION_SYMBOL) != symbol)
         continue;
      bool isBuy = (PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY);
      MqlTradeResult res = {};
      if(!SPK_SendDealWithRetry(symbol, magic,
                                isBuy ? ORDER_TYPE_SELL : ORDER_TYPE_BUY,
                                PositionGetDouble(POSITION_VOLUME), 0.0, 0.0, t,
                                SPK_COMMENT "|" + reason, res))
         PrintFormat("[SPKA] Close failed ticket=%I64u retcode=%u", t, res.retcode);
   }
}

bool SPK_IsDDExceeded()
{
   if(g_spkDayStartBal <= 0) return false;
   return (g_spkDayStartBal - AccountInfoDouble(ACCOUNT_EQUITY)) / g_spkDayStartBal * 100.0
          >= SPK_DAILY_DD;
}

double SPK_CalcLot(string symbol, double riskPct, double maxLot, const double slDist)
{
   if(slDist <= 0) return 0;
   double bal = AccountInfoDouble(ACCOUNT_BALANCE);
   double riskCash = bal * riskPct / 100.0;
   double tv = SymbolInfoDouble(symbol, SYMBOL_TRADE_TICK_VALUE);
   double ts = SymbolInfoDouble(symbol, SYMBOL_TRADE_TICK_SIZE);
   if(tv <= 0 || ts <= 0) return 0;
   double lot = riskCash / (slDist / ts * tv);
   lot = MathMin(lot, maxLot);
   lot = MathMin(lot, SymbolInfoDouble(symbol, SYMBOL_VOLUME_MAX));
   lot = MathMax(lot, SymbolInfoDouble(symbol, SYMBOL_VOLUME_MIN));
   double step = SymbolInfoDouble(symbol, SYMBOL_VOLUME_STEP);
   if(step > 0)
      lot = MathFloor(lot / step) * step;
   return lot;
}

bool SPK_IsTradeDay(const int dow)
{
   if(dow == 1) return SPK_TRADE_MON;
   if(dow == 2) return SPK_TRADE_TUE;
   if(dow == 3) return SPK_TRADE_WED;
   if(dow == 4) return SPK_TRADE_THU;
   if(dow == 5) return SPK_TRADE_FRI;
   return false;
}

double SPK_GetATR1()
{
   double buf[];
   ArraySetAsSeries(buf, true);
   if(CopyBuffer(g_spkHatr, 0, 1, 1, buf) < 1)
      return 0;
   return buf[0];
}

int SPK_GetTrendBias(string symbol)
{
   if(!SPK_USE_TREND || g_spkHemaD1 == INVALID_HANDLE)
      return 0;
   double ema[];
   ArraySetAsSeries(ema, true);
   if(CopyBuffer(g_spkHemaD1, 0, 1, 1, ema) < 1)
      return 0;
   double d1c[];
   ArraySetAsSeries(d1c, true);
   if(CopyClose(symbol, PERIOD_D1, 1, 1, d1c) < 1)
      return 0;
   if(d1c[0] > ema[0]) return 1;
   if(d1c[0] < ema[0]) return -1;
   return 0;
}

void SPK_ResetDay()
{
   g_spkAsianHi = 0;
   g_spkAsianLo = 99999.0;
   g_spkRangeLocked = false;
   g_spkRangeValid = false;
   g_spkTradesToday = 0;
   g_spkHoldBars = 0;
   g_spkBeMoved = false;
   g_spkDayStartBal = AccountInfoDouble(ACCOUNT_BALANCE);
}

void SPK_LockRange(const double atr)
{
   g_spkRangeLocked = true;
   if(g_spkAsianHi <= 0 || g_spkAsianLo >= 99999.0 || g_spkAsianHi <= g_spkAsianLo)
   {
      g_spkRangeValid = false;
      return;
   }
   double rangeSize = g_spkAsianHi - g_spkAsianLo;
   double ratio = (atr > 0) ? rangeSize / atr : 0;
   g_spkRangeValid = (ratio >= SPK_RANGE_MIN_ATR && ratio <= SPK_RANGE_MAX_ATR);
}

void SPK_ManageOpen(string symbol, ulong magic, const int hour)
{
   if(SPK_CountPositions(magic, symbol) <= 0)
      return;

   g_spkHoldBars++;

   if(hour >= SPK_FLAT_HOUR)
   {
      SPK_CloseAll(symbol, magic, "FLAT");
      return;
   }
   if(g_spkHoldBars >= SPK_MAX_HOLD_BARS)
   {
      SPK_CloseAll(symbol, magic, "MAX_HOLD");
      return;
   }

   if(!SPK_BE_ENABLED || g_spkBeMoved)
      return;

   int digits = (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS);
   double point = SymbolInfoDouble(symbol, SYMBOL_POINT);

   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong t = PositionGetTicket(i);
      if(t <= 0 ||
         PositionGetInteger(POSITION_MAGIC) != (long)magic ||
         PositionGetString(POSITION_SYMBOL) != symbol)
         continue;

      bool isBuy = (PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY);
      double openPx = PositionGetDouble(POSITION_PRICE_OPEN);
      double currSL = PositionGetDouble(POSITION_SL);
      double currTP = PositionGetDouble(POSITION_TP);
      if(currSL <= 0)
         break;

      double slDist = MathAbs(openPx - currSL);
      double beTarget = slDist * SPK_BE_RATIO;
      double curPrice = isBuy ? SymbolInfoDouble(symbol, SYMBOL_BID)
                              : SymbolInfoDouble(symbol, SYMBOL_ASK);
      double profit = isBuy ? (curPrice - openPx) : (openPx - curPrice);
      if(profit < beTarget || beTarget <= 0)
         break;

      double newSL = NormalizeDouble(isBuy ? openPx + point : openPx - point, digits);
      long stopLvl = 0;
      SymbolInfoInteger(symbol, SYMBOL_TRADE_STOPS_LEVEL, stopLvl);
      if(MathAbs(curPrice - newSL) < stopLvl * point)
         break;

      if(g_spkTrade.PositionModify(t, newSL, currTP))
         g_spkBeMoved = true;
      break;
   }
}

int SPK_GetBreakoutSignal(string symbol, const double atr)
{
   if(atr <= 0 || !g_spkRangeLocked || !g_spkRangeValid)
      return 0;

   int spread = (int)SymbolInfoInteger(symbol, SYMBOL_SPREAD);
   if(spread > SPK_MAX_SPREAD)
      return 0;

   double open1  = iOpen(symbol, PERIOD_CURRENT, 1);
   double close1 = iClose(symbol, PERIOD_CURRENT, 1);
   double high1  = iHigh(symbol, PERIOD_CURRENT, 1);
   double low1   = iLow(symbol, PERIOD_CURRENT, 1);
   if(high1 <= low1)
      return 0;

   double barRange = high1 - low1;
   double bodyRatio = MathAbs(close1 - open1) / barRange;
   if(bodyRatio < SPK_BODY_RATIO)
      return 0;

   double buffer = atr * SPK_BRK_BUF_ATR;
   int direction = 0;
   if(close1 > g_spkAsianHi + buffer && close1 > open1)
      direction = 1;
   else if(close1 < g_spkAsianLo - buffer && close1 < open1)
      direction = -1;
   if(direction == 0)
      return 0;

   if(SPK_USE_TREND)
   {
      int bias = SPK_GetTrendBias(symbol);
      if((direction == 1 && bias == -1) || (direction == -1 && bias == 1))
         return 0;
   }
   return direction;
}

void SPK_TryEntry(string symbol, ulong magic, double riskPct, double maxLot,
                  const double atr, const string session)
{
   int direction = SPK_GetBreakoutSignal(symbol, atr);
   if(direction == 0)
      return;

   int digits = (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS);
   double slBuffer = atr * SPK_SL_BUF_ATR;
   double entry = 0, sl = 0, tp = 0, slDist = 0;
   if(direction == 1)
   {
      entry = SymbolInfoDouble(symbol, SYMBOL_ASK);
      sl = g_spkAsianLo - slBuffer;
      slDist = entry - sl;
      tp = entry + slDist * SPK_TP_RATIO;
   }
   else
   {
      entry = SymbolInfoDouble(symbol, SYMBOL_BID);
      sl = g_spkAsianHi + slBuffer;
      slDist = sl - entry;
      tp = entry - slDist * SPK_TP_RATIO;
   }
   if(slDist <= 0)
      return;

   sl = NormalizeDouble(sl, digits);
   tp = NormalizeDouble(tp, digits);
   double lots = SPK_CalcLot(symbol, riskPct, maxLot, slDist);
   if(lots <= 0)
      return;

   MqlTradeResult res = {};
   string comment = SPK_COMMENT "|" + session;
   bool ok = SPK_SendDealWithRetry(symbol, magic,
                                   direction == 1 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL,
                                   lots, sl, tp, 0, comment, res);
   if(ok)
   {
      g_spkTradesToday++;
      g_spkHoldBars = 0;
      g_spkBeMoved = false;
      PrintFormat("[SPKA] ENTRY %s %s lots=%.2f SL=%.5f TP=%.5f",
                  (direction == 1 ? "BUY" : "SELL"), session, lots, sl, tp);
   }
   else
      PrintFormat("[SPKA] ENTRY FAIL retcode=%u", res.retcode);
}

void SPK_OnTick(string symbol, ulong magic, double riskPct, double maxLot)
{
   datetime barTime = iTime(symbol, PERIOD_CURRENT, 0);
   if(barTime == 0 || barTime == g_spkLastBar)
      return;
   g_spkLastBar = barTime;

   MqlDateTime dt;
   TimeToStruct(barTime, dt);
   int hour = dt.hour;
   int dow = dt.day_of_week;
   int dayKey = dt.year * 400 + dt.day_of_year;
   if(dayKey != g_spkLastTradeDay)
   {
      g_spkLastTradeDay = dayKey;
      SPK_ResetDay();
   }

   double atr = SPK_GetATR1();
   if(atr <= 0)
      return;

   // Range tracking uses closed bar[1] only
   if(hour >= SPK_ASIAN_START && hour < SPK_ASIAN_END)
   {
      double hi1 = iHigh(symbol, PERIOD_CURRENT, 1);
      double lo1 = iLow(symbol, PERIOD_CURRENT, 1);
      if(hi1 > g_spkAsianHi) g_spkAsianHi = hi1;
      if(lo1 < g_spkAsianLo && lo1 > 0) g_spkAsianLo = lo1;
   }
   if(hour >= SPK_ASIAN_END && !g_spkRangeLocked)
      SPK_LockRange(atr);

   if(SPK_CountPositions(magic, symbol) > 0)
   {
      SPK_ManageOpen(symbol, magic, hour);
      return;
   }

   if(!SPK_IsTradeDay(dow) || SPK_IsDDExceeded())
      return;
   if(g_spkTradesToday >= SPK_MAX_PER_DAY)
      return;
   if(hour >= SPK_FLAT_HOUR)
      return;

   bool inLdn = (hour >= SPK_LDN_START && hour < SPK_LDN_END);
   bool inNY  = SPK_NY_ENABLED && (hour >= SPK_NY_START && hour < SPK_NY_END);
   if(!inLdn && !inNY)
      return;

   SPK_TryEntry(symbol, magic, riskPct, maxLot, atr, inLdn ? "LDN" : "NY");
}

#endif // SPARK_ASIAN_MODULE_MQH
