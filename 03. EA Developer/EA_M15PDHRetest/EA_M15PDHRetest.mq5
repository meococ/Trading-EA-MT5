//+------------------------------------------------------------------+
//| EA_M15PDHRetest.mq5 — PDH/PDL break then retest continuation     |
//| Symbol: USDJPY | Period: M15 | Magic: 880981                     |
//|                                                                   |
//| Hypothesis: HYP-PDH-RETEST-M15-001                                 |
//| Independent of HYP-PDH-BREAK (immediate break entry). After a     |
//| closed-bar break of D1 shift>=1 PDH/PDL, wait for a closed M15   |
//| retest+reject of the broken level, then continue. Not LiqSweep   |
//| fade. Closed-bar[1] only. Mon–Thu; weekend flat; risk 0.5%.      |
//+------------------------------------------------------------------+
#property copyright "SonicR / EA_M15PDHRetest"
#property version   "1.00"
#property strict

#include <Trade\Trade.mqh>

input group "=== General ==="
input ulong    InpMagic         = 880981;
input int      InpDeviation     = 30;
input bool     InpKillSwitch    = false;

input group "=== PDH/PDL Break+Retest ==="
input double   InpBrkBufferATR  = 0.10;
input double   InpBodyRatio     = 0.40;
input double   InpRetestATR     = 0.25;   // how close retest must approach level
input double   InpRejectATR     = 0.10;   // close beyond level after touch
input int      InpEMAPeriod     = 50;
input bool     InpUseTrendFilter= true;
input int      InpRetestMaxBars = 24;     // M15 bars after break to allow retest

input group "=== Session (server hours) ==="
input int      InpTradeStart    = 9;
input int      InpTradeEnd      = 17;
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
input double   InpTP_Ratio      = 1.50;
input int      InpMinSLPoints   = 50;
input int      InpMaxSLPoints   = 1200;
input int      InpMaxPerDay     = 1;
input double   InpDailyDD       = 4.0;
input int      InpMaxHoldBars   = 32;
input int      InpMaxSpreadPts  = 50;

CTrade   g_trade;
int      g_hATR  = INVALID_HANDLE;
int      g_hEMA  = INVALID_HANDLE;
datetime g_lastBar = 0;
int      g_tradesToday = 0;
int      g_lastTradeDay = -1;
double   g_dayStartBalance = 0;
int      g_holdBars = 0;

// Break→retest state (reset each calendar day)
int      g_brkDir = 0;          // +1 broke PDH, -1 broke PDL
double   g_brkLevel = 0.0;
int      g_barsSinceBrk = 0;
bool     g_tradedAfterBrk = false;

int OnInit()
{
   g_trade.SetExpertMagicNumber((long)InpMagic);
   g_trade.SetDeviationInPoints(InpDeviation);
   g_hATR = iATR(_Symbol, PERIOD_CURRENT, 14);
   if(InpUseTrendFilter)
      g_hEMA = iMA(_Symbol, PERIOD_D1, InpEMAPeriod, 0, MODE_EMA, PRICE_CLOSE);
   if(g_hATR == INVALID_HANDLE)
      return INIT_FAILED;
   if(InpUseTrendFilter && g_hEMA == INVALID_HANDLE)
      return INIT_FAILED;
   g_dayStartBalance = AccountInfoDouble(ACCOUNT_BALANCE);
   Print("[PDHR] HYP-PDH-RETEST-M15-001");
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
                        "PDHR|" + reason, res);
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

void TryArmBreak(const double atr)
{
   if(g_brkDir != 0 || g_tradedAfterBrk)
      return;

   double pdh = iHigh(_Symbol, PERIOD_D1, 1);
   double pdl = iLow(_Symbol, PERIOD_D1, 1);
   if(pdh <= 0.0 || pdl <= 0.0 || pdh <= pdl)
      return;

   double bO = iOpen(_Symbol, PERIOD_CURRENT, 1);
   double bH = iHigh(_Symbol, PERIOD_CURRENT, 1);
   double bL = iLow(_Symbol, PERIOD_CURRENT, 1);
   double bC = iClose(_Symbol, PERIOD_CURRENT, 1);
   double range1 = bH - bL;
   if(range1 <= 0.0)
      return;
   if(MathAbs(bC - bO) / range1 < InpBodyRatio)
      return;

   double buf = atr * InpBrkBufferATR;
   int dir = 0;
   double lvl = 0.0;
   if(bC > pdh + buf)
   {
      dir = +1;
      lvl = pdh;
   }
   else if(bC < pdl - buf)
   {
      dir = -1;
      lvl = pdl;
   }
   else
      return;

   if(InpUseTrendFilter)
   {
      double ema[];
      ArraySetAsSeries(ema, true);
      if(CopyBuffer(g_hEMA, 0, 1, 1, ema) < 1)
         return;
      if(dir > 0 && bC < ema[0])
         return;
      if(dir < 0 && bC > ema[0])
         return;
   }

   g_brkDir = dir;
   g_brkLevel = lvl;
   g_barsSinceBrk = 0;
}

int GetRetestSignal(const double atr)
{
   if(g_brkDir == 0 || g_tradedAfterBrk)
      return 0;
   // Retest must be a later bar than the break arm (not same-bar continuation).
   if(g_barsSinceBrk < 1)
      return 0;
   if(g_barsSinceBrk > InpRetestMaxBars)
   {
      g_brkDir = 0;
      g_brkLevel = 0.0;
      return 0;
   }

   double bH = iHigh(_Symbol, PERIOD_CURRENT, 1);
   double bL = iLow(_Symbol, PERIOD_CURRENT, 1);
   double bC = iClose(_Symbol, PERIOD_CURRENT, 1);
   double touch = atr * InpRetestATR;
   double reject = atr * InpRejectATR;

   if(g_brkDir > 0)
   {
      // Retest of broken PDH from above: wick/low touches near level, close holds above
      if(bL <= g_brkLevel + touch && bC >= g_brkLevel + reject)
         return +1;
   }
   else if(g_brkDir < 0)
   {
      if(bH >= g_brkLevel - touch && bC <= g_brkLevel - reject)
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
      g_brkDir = 0;
      g_brkLevel = 0.0;
      g_barsSinceBrk = 0;
      g_tradedAfterBrk = false;
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
   if(g_tradesToday >= InpMaxPerDay || IsDDExceeded())
      return;
   if(SymbolInfoInteger(_Symbol, SYMBOL_SPREAD) > InpMaxSpreadPts)
      return;
   if(dt.hour < InpTradeStart || dt.hour >= InpTradeEnd)
      return;

   double atr[];
   ArraySetAsSeries(atr, true);
   if(CopyBuffer(g_hATR, 0, 1, 1, atr) < 1 || atr[0] <= 0.0)
      return;

   if(g_brkDir == 0)
      TryArmBreak(atr[0]);
   else
      g_barsSinceBrk++;

   int signal = GetRetestSignal(atr[0]);
   if(signal == 0)
      return;

   bool isBuy = (signal == +1);
   double entry = (isBuy ? SymbolInfoDouble(_Symbol, SYMBOL_ASK)
                         : SymbolInfoDouble(_Symbol, SYMBOL_BID));
   double slRaw = (isBuy ? g_brkLevel - atr[0] * InpSL_BufferATR
                         : g_brkLevel + atr[0] * InpSL_BufferATR);
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
                         "PDHR|rt", res))
      return;
   if(IsSuccessfulRetcode(res.retcode))
   {
      g_tradesToday++;
      g_tradedAfterBrk = true;
      g_brkDir = 0;
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
