//+------------------------------------------------------------------+
//| EA_H4StructBreak_M15.mq5 — H4 swing BOS → M15 acceptance         |
//| Symbol: USDJPY | Period: M15 | Magic: 880982                     |
//|                                                                   |
//| Hypothesis: HYP-H4-STRUCT-BREAK-M15-001                            |
//| Independent of HYP-H1-BOS-M15-PB (H1 swing + EMA pullback KILL).  |
//| H4 closed-bar swing break (L=2) sets structure; M15 enters on     |
//| closed-bar[1] acceptance beyond the broken H4 swing (body), NOT   |
//| EMA densify. Mon–Thu; weekend flat; risk 0.5%.                    |
//+------------------------------------------------------------------+
#property copyright "SonicR / EA_H4StructBreak_M15"
#property version   "1.00"
#property strict

#include <Trade\Trade.mqh>

input group "=== General ==="
input ulong    InpMagic         = 880982;
input int      InpDeviation     = 30;
input bool     InpKillSwitch    = false;

input group "=== H4 Structure ==="
input int      InpSwingL        = 2;      // H4 pivot lookback each side
input int      InpBOSMaxAgeH4   = 12;     // max H4 bars since BOS
input double   InpBodyRatio     = 0.40;
input double   InpBrkBufferATR  = 0.05;   // M15 ATR buffer beyond swing

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
input double   InpSL_BufferATR  = 0.20;
input int      InpMinSLPoints   = 50;
input int      InpMaxSLPoints   = 1600;
input double   InpTP_Ratio      = 1.50;
input int      InpMaxPerDay     = 1;
input double   InpDailyDD       = 4.0;
input int      InpMaxHoldBars   = 32;
input int      InpMaxSpreadPts  = 50;
input int      InpATRPeriod     = 14;

CTrade   g_trade;
int      g_hATR = INVALID_HANDLE;
datetime g_lastBar = 0;
int      g_tradesToday = 0;
int      g_lastTradeDay = -1;
double   g_dayStartBalance = 0;
int      g_holdBars = 0;

int      g_bosDir = 0;
double   g_bosLevel = 0.0;
datetime g_bosH4Time = 0;
bool     g_enteredThisBOS = false;

int OnInit()
{
   g_trade.SetExpertMagicNumber((long)InpMagic);
   g_trade.SetDeviationInPoints(InpDeviation);
   g_hATR = iATR(_Symbol, PERIOD_CURRENT, InpATRPeriod);
   if(g_hATR == INVALID_HANDLE)
      return INIT_FAILED;
   g_dayStartBalance = AccountInfoDouble(ACCOUNT_BALANCE);
   Print("[H4SB] HYP-H4-STRUCT-BREAK-M15-001");
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
                        "H4SB|" + reason, res);
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

// Confirmed H4 swing high/low at pivot index (closed bars only).
bool IsH4SwingHigh(const int pivot)
{
   double ph = iHigh(_Symbol, PERIOD_H4, pivot);
   for(int k = 1; k <= InpSwingL; k++)
   {
      if(iHigh(_Symbol, PERIOD_H4, pivot + k) >= ph)
         return false;
      if(iHigh(_Symbol, PERIOD_H4, pivot - k) >= ph)
         return false;
   }
   return true;
}

bool IsH4SwingLow(const int pivot)
{
   double pl = iLow(_Symbol, PERIOD_H4, pivot);
   for(int k = 1; k <= InpSwingL; k++)
   {
      if(iLow(_Symbol, PERIOD_H4, pivot + k) <= pl)
         return false;
      if(iLow(_Symbol, PERIOD_H4, pivot - k) <= pl)
         return false;
   }
   return true;
}

bool FindLastH4SwingHigh(const int fromShift, double &level, datetime &t)
{
   // Need pivot-L confirmed: oldest searchable starts at fromShift+L
   int start = fromShift + InpSwingL;
   int end = start + 80;
   for(int i = start; i <= end; i++)
   {
      if(IsH4SwingHigh(i))
      {
         level = iHigh(_Symbol, PERIOD_H4, i);
         t = iTime(_Symbol, PERIOD_H4, i);
         return (level > 0.0 && t > 0);
      }
   }
   return false;
}

bool FindLastH4SwingLow(const int fromShift, double &level, datetime &t)
{
   int start = fromShift + InpSwingL;
   int end = start + 80;
   for(int i = start; i <= end; i++)
   {
      if(IsH4SwingLow(i))
      {
         level = iLow(_Symbol, PERIOD_H4, i);
         t = iTime(_Symbol, PERIOD_H4, i);
         return (level > 0.0 && t > 0);
      }
   }
   return false;
}

void UpdateH4BOS()
{
   // Closed H4 bar[1] vs last confirmed swing (swing pivot >= 1+L so fully closed).
   double sh = 0.0, sl = 0.0;
   datetime th = 0, tl = 0;
   if(!FindLastH4SwingHigh(1, sh, th) || !FindLastH4SwingLow(1, sl, tl))
      return;

   double c1 = iClose(_Symbol, PERIOD_H4, 1);
   datetime t1 = iTime(_Symbol, PERIOD_H4, 1);
   if(c1 <= 0.0 || t1 <= 0)
      return;

   // Bullish BOS: H4 close above last swing high
   if(c1 > sh && (g_bosDir != +1 || g_bosLevel != sh || g_bosH4Time != t1))
   {
      g_bosDir = +1;
      g_bosLevel = sh;
      g_bosH4Time = t1;
      g_enteredThisBOS = false;
   }
   // Bearish BOS: H4 close below last swing low
   else if(c1 < sl && (g_bosDir != -1 || g_bosLevel != sl || g_bosH4Time != t1))
   {
      g_bosDir = -1;
      g_bosLevel = sl;
      g_bosH4Time = t1;
      g_enteredThisBOS = false;
   }
}

bool BOSStillValid()
{
   if(g_bosDir == 0 || g_bosH4Time <= 0)
      return false;
   int shift = iBarShift(_Symbol, PERIOD_H4, g_bosH4Time, true);
   if(shift < 0)
      return false;
   return (shift <= InpBOSMaxAgeH4);
}

int GetAcceptSignal(const double atr)
{
   if(g_bosDir == 0 || g_enteredThisBOS || !BOSStillValid())
      return 0;

   double bO = iOpen(_Symbol, PERIOD_CURRENT, 1);
   double bH = iHigh(_Symbol, PERIOD_CURRENT, 1);
   double bL = iLow(_Symbol, PERIOD_CURRENT, 1);
   double bC = iClose(_Symbol, PERIOD_CURRENT, 1);
   double range1 = bH - bL;
   if(range1 <= 0.0)
      return 0;
   if(MathAbs(bC - bO) / range1 < InpBodyRatio)
      return 0;

   double buf = atr * InpBrkBufferATR;
   if(g_bosDir > 0 && bC > g_bosLevel + buf)
      return +1;
   if(g_bosDir < 0 && bC < g_bosLevel - buf)
      return -1;
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

   UpdateH4BOS();

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
   if(g_tradesToday >= InpMaxPerDay || IsDDExceeded())
      return;
   if(SymbolInfoInteger(_Symbol, SYMBOL_SPREAD) > InpMaxSpreadPts)
      return;
   if(dt.hour < InpStartHour || dt.hour >= InpEndHour)
      return;

   double atr[];
   ArraySetAsSeries(atr, true);
   if(CopyBuffer(g_hATR, 0, 1, 1, atr) < 1 || atr[0] <= 0.0)
      return;

   int signal = GetAcceptSignal(atr[0]);
   if(signal == 0)
      return;

   bool isBuy = (signal == +1);
   double entry = (isBuy ? SymbolInfoDouble(_Symbol, SYMBOL_ASK)
                         : SymbolInfoDouble(_Symbol, SYMBOL_BID));
   // Invalidation = reclaim of broken H4 swing.
   double slRaw = (isBuy ? g_bosLevel - atr[0] * InpSL_BufferATR
                         : g_bosLevel + atr[0] * InpSL_BufferATR);
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

   MqlTradeResult res = {};
   if(!SendDealWithRetry(isBuy ? ORDER_TYPE_BUY : ORDER_TYPE_SELL, lot, sl, tp, 0,
                         "H4SB|acc", res))
      return;
   if(IsSuccessfulRetcode(res.retcode))
   {
      g_tradesToday++;
      g_enteredThisBOS = true;
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
