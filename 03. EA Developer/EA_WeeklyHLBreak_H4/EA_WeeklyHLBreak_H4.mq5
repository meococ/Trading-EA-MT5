//+------------------------------------------------------------------+
//| EA_WeeklyHLBreak_H4.mq5 — Prior W1 HL H4 close break (RR=3)      |
//| Symbol: USDJPY | Period: H4 | Magic: 880992                       |
//| Hypothesis: HYP-WEEKLY-HL-BREAK-H4-001                             |
//| Closed-bar[1] only. Mon–Thu; weekend flat; risk 0.5%; RR=3.0.     |
//| Not PDH/PDL. Cadence path if sparse: multi-symbol stub (prereg).  |
//+------------------------------------------------------------------+
#property copyright "SonicR / EA_WeeklyHLBreak_H4"
#property version   "1.00"
#property strict

#include <Trade\Trade.mqh>

input group "=== General ==="
input ulong    InpMagic         = 880992;
input int      InpDeviation     = 30;
input bool     InpKillSwitch    = false;

input group "=== Weekly break ==="
input double   InpSL_WeekFrac   = 0.35;   // SL = fraction of prior week range

input group "=== Session ==="
input int      InpFlatHour      = 22;
input bool     InpTradeMon      = true;
input bool     InpTradeTue      = true;
input bool     InpTradeWed      = true;
input bool     InpTradeThu      = true;
input bool     InpTradeFri      = false;

input group "=== Risk ==="
input double   InpRiskPct       = 0.50;
input double   InpMaxLot        = 1.0;
input double   InpTP_Ratio      = 3.00;
input int      InpMinSLPoints   = 150;
input int      InpMaxSLPoints   = 8000;
input int      InpMaxPerDay     = 1;
input double   InpDailyDD       = 4.0;
input int      InpMaxHoldBars   = 40;
input int      InpMaxSpreadPts  = 80;

CTrade   g_trade;
datetime g_lastBar = 0;
int      g_tradesToday = 0;
int      g_lastTradeDay = -1;
double   g_dayStartBalance = 0;
int      g_holdBars = 0;
int      g_weekKey = -1;
bool     g_brokeHigh = false;
bool     g_brokeLow = false;

int OnInit()
{
   if(Period() != PERIOD_H4)
   {
      Print("[W1HL] FAIL — chart must be H4");
      return INIT_FAILED;
   }
   g_trade.SetExpertMagicNumber((long)InpMagic);
   g_trade.SetDeviationInPoints(InpDeviation);
   g_dayStartBalance = AccountInfoDouble(ACCOUNT_BALANCE);
   Print("[W1HL] HYP-WEEKLY-HL-BREAK-H4-001 RR=", InpTP_Ratio);
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason) {}

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
                        "W1HL|" + reason, res);
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

// Detect FIRST close break this week: require prior closed H4 still inside.
bool DetectWeeklyBreak(bool &isBuy, double &weekHigh, double &weekLow, double &weekRange)
{
   isBuy = false;
   weekHigh = iHigh(_Symbol, PERIOD_W1, 1);
   weekLow  = iLow(_Symbol, PERIOD_W1, 1);
   weekRange = weekHigh - weekLow;
   if(weekRange <= 0.0)
      return false;

   double c1 = iClose(_Symbol, PERIOD_H4, 1);
   double c2 = iClose(_Symbol, PERIOD_H4, 2);

   // Long: first closed H4 beyond prior week high
   if(!g_brokeHigh && c1 > weekHigh && c2 <= weekHigh)
   {
      isBuy = true;
      return true;
   }
   // Short: first closed H4 beyond prior week low
   if(!g_brokeLow && c1 < weekLow && c2 >= weekLow)
   {
      isBuy = false;
      return true;
   }
   return false;
}

void OnTick()
{
   if(InpKillSwitch)
      return;

   datetime barTime = iTime(_Symbol, PERIOD_H4, 0);
   if(barTime == 0 || barTime == g_lastBar)
      return;
   g_lastBar = barTime;

   datetime bar1Time = iTime(_Symbol, PERIOD_H4, 1);
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

   // Reset week flags on new W1 open without using future breaks incorrectly:
   // compute week key from W1[0] open time, then evaluate first-break using c2.
   datetime w0 = iTime(_Symbol, PERIOD_W1, 0);
   if(w0 != 0)
   {
      MqlDateTime wt;
      TimeToStruct(w0, wt);
      int key = wt.year * 100 + wt.day_of_year;
      if(key != g_weekKey)
      {
         g_weekKey = key;
         g_brokeHigh = false;
         g_brokeLow = false;
      }
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

   bool isBuy = false;
   double wh = 0.0, wl = 0.0, wr = 0.0;
   if(!DetectWeeklyBreak(isBuy, wh, wl, wr))
   {
      // Update break flags from closed bar after miss (so we don't re-fire)
      double c1 = iClose(_Symbol, PERIOD_H4, 1);
      if(c1 > wh) g_brokeHigh = true;
      if(c1 < wl) g_brokeLow = true;
      return;
   }

   double entry = (isBuy ? SymbolInfoDouble(_Symbol, SYMBOL_ASK)
                         : SymbolInfoDouble(_Symbol, SYMBOL_BID));
   double slDist = wr * InpSL_WeekFrac;
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
   if(!SendDealWithRetry(isBuy ? ORDER_TYPE_BUY : ORDER_TYPE_SELL, lot, sl, tp, 0, "W1HL|brk", res))
      return;
   if(IsSuccessfulRetcode(res.retcode))
   {
      g_tradesToday++;
      g_holdBars = 0;
      if(isBuy) g_brokeHigh = true;
      else      g_brokeLow = true;
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
