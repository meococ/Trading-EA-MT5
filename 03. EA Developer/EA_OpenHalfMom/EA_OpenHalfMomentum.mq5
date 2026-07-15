//+------------------------------------------------------------------+
//| EA_OpenHalfMomentum.mq5 — Opening Half-Hour Momentum             |
//| Based on: "Intraday Time-Series Momentum" (Lancaster 2020)       |
//| Symbol: USDJPY+/XAUUSD+  |  Period: M15  |  Style: Intraday     |
//|                                                                   |
//| EDGE HYPOTHESIS:                                                  |
//| The return of the first 30 minutes of London session predicts    |
//| the return at session close. Institutional market-on-open         |
//| orders reveal initial direction; closing flows amplify it.       |
//| Academic evidence across 16 developed markets.                   |
//|                                                                   |
//| KEY DIFFERENCE FROM TESTED STRATEGIES:                            |
//| - Not momentum continuation (no MA/EMA used)                    |
//| - Not session breakout (no range measured)                       |
//| - Not trend following (entry at specific time, exit at time)     |
//| - Pure time-series: direction of first half-hour = trade dir    |
//|                                                                   |
//| SIGNALS ON BAR[1] ONLY — no repaint, no lookahead.               |
//| Max | 2026-04-12 | v1.0                                         |
//+------------------------------------------------------------------+
#property copyright "Max - EA_OpenHalfMomentum v1.0"
#property version   "1.00"
#property strict

#include <Trade\Trade.mqh>

//+------------------------------------------------------------------+
input group "=== General ==="
input ulong    InpMagic         = 804001;
input int      InpDeviation     = 30;
input bool     InpKillSwitch    = false;

input group "=== Session Timing (Server Time) ==="
input int      InpSessionOpenH  = 10;        // Session open hour (London ~08 GMT = 10 server)
input int      InpMeasureBars   = 2;         // Bars to measure opening return (2 x M15 = 30min)
input int      InpExitH         = 21;        // Force exit hour (NY close ~19 GMT = 21 server)

input group "=== Minimum Move ==="
input int      InpMinMovePts    = 20;        // Min opening move (points) to take signal
input int      InpATRPeriod     = 14;
input double   InpMinMoveATR    = 0.15;      // Min move as fraction of ATR

input group "=== Risk ==="
input double   InpRiskPct       = 0.50;
input double   InpMaxLot        = 0.50;
input double   InpDailyDDPct    = 4.0;
input double   InpSL_ATRMult    = 1.5;       // SL = ATR * this
input double   InpTP_ATRMult    = 2.0;       // TP = ATR * this

input group "=== Day Filters ==="
input bool     InpMon = true;
input bool     InpTue = true;
input bool     InpWed = true;
input bool     InpThu = true;
input bool     InpFri = true;

//+------------------------------------------------------------------+
CTrade   g_trade;
int      g_hATR;
datetime g_lastBar, g_todayDate;
double   g_dayStartBal;
bool     g_tradedToday;
double   g_sessionOpen;       // Price at session open
bool     g_sessionMeasured;   // Have we measured opening return?
double   g_openReturn;        // Signed return of first N bars

//+------------------------------------------------------------------+
int OnInit()
{
   if(InpKillSwitch) return INIT_SUCCEEDED;

   g_trade.SetExpertMagicNumber(InpMagic);
   g_trade.SetDeviationInPoints(InpDeviation);
   g_trade.SetTypeFilling(ORDER_FILLING_FOK);

   g_hATR = iATR(_Symbol, PERIOD_CURRENT, InpATRPeriod);
   if(g_hATR == INVALID_HANDLE) { Print("[OHM] ATR init fail"); return INIT_FAILED; }

   g_lastBar = 0; g_todayDate = 0;
   g_sessionOpen = 0; g_sessionMeasured = false;
   g_tradedToday = false; g_openReturn = 0;
   g_dayStartBal = AccountInfoDouble(ACCOUNT_BALANCE);

   PrintFormat("[OHM] OpenHalfMomentum v1.0 | %s %s | Open h%d | Exit h%d | Bars=%d",
               _Symbol, EnumToString(_Period),
               InpSessionOpenH, InpExitH, InpMeasureBars);
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   if(g_hATR != INVALID_HANDLE) IndicatorRelease(g_hATR);
}

//+------------------------------------------------------------------+
int CountPos()
{
   int n = 0;
   for(int i = PositionsTotal()-1; i >= 0; i--)
   {
      ulong t = PositionGetTicket(i);
      if(t > 0 && PositionGetInteger(POSITION_MAGIC) == (long)InpMagic &&
         PositionGetString(POSITION_SYMBOL) == _Symbol) n++;
   }
   return n;
}

void CloseAll()
{
   for(int i = PositionsTotal()-1; i >= 0; i--)
   {
      ulong t = PositionGetTicket(i);
      if(t > 0 && PositionGetInteger(POSITION_MAGIC) == (long)InpMagic &&
         PositionGetString(POSITION_SYMBOL) == _Symbol)
         g_trade.PositionClose(t);
   }
}

double CalcLot(double slPts)
{
   if(slPts <= 0) return 0;
   double bal  = AccountInfoDouble(ACCOUNT_BALANCE);
   double risk = bal * InpRiskPct / 100.0;
   double tSz  = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   double tVal = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
   double pt   = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   if(tSz == 0 || tVal == 0 || pt == 0) return 0;
   double ptVal = tVal * pt / tSz;
   double lot   = risk / (slPts * ptVal);
   double minL  = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double maxL  = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   double step  = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   lot = MathMax(lot, minL);
   lot = MathMin(lot, MathMin(InpMaxLot, maxL));
   if(step > 0) lot = MathFloor(lot / step) * step;
   return NormalizeDouble(lot, 2);
}

bool IsTradingDay(int dow)
{
   switch(dow)
   {
      case 1: return InpMon; case 2: return InpTue; case 3: return InpWed;
      case 4: return InpThu; case 5: return InpFri; default: return false;
   }
}

//+------------------------------------------------------------------+
void OnTick()
{
   if(InpKillSwitch) return;

   datetime barTime = iTime(_Symbol, PERIOD_CURRENT, 0);
   if(barTime == g_lastBar) return;
   g_lastBar = barTime;

   MqlDateTime dt;
   TimeToStruct(barTime, dt);
   datetime today = StringToTime(StringFormat("%04d.%02d.%02d", dt.year, dt.mon, dt.day));

   // Day reset
   if(today != g_todayDate)
   {
      g_todayDate = today;
      g_tradedToday = false;
      g_sessionOpen = 0;
      g_sessionMeasured = false;
      g_openReturn = 0;
      g_dayStartBal = AccountInfoDouble(ACCOUNT_BALANCE);
   }

   // Force exit at designated hour
   if(dt.hour >= InpExitH && CountPos() > 0)
   {
      CloseAll();
      return;
   }

   //--- Phase 1: Record session open price
   if(dt.hour == InpSessionOpenH && g_sessionOpen <= 0)
   {
      g_sessionOpen = iOpen(_Symbol, PERIOD_CURRENT, 0);
      return;
   }

   //--- Phase 2: After InpMeasureBars bars, measure the opening return
   if(!g_sessionMeasured && g_sessionOpen > 0)
   {
      // Calculate how many M15 bars since session open
      datetime sessionStart = today + InpSessionOpenH * 3600;
      int barsSinceOpen = iBarShift(_Symbol, PERIOD_CURRENT, sessionStart, false);

      if(barsSinceOpen >= InpMeasureBars)
      {
         // Measure: close of bar[1] vs session open
         double closeNow = iClose(_Symbol, PERIOD_CURRENT, 1);
         g_openReturn = closeNow - g_sessionOpen;
         g_sessionMeasured = true;
      }
      else
         return;
   }

   // Already measured but haven't traded yet
   if(!g_sessionMeasured) return;
   if(g_tradedToday) return;
   if(!IsTradingDay(dt.day_of_week)) return;
   if(CountPos() > 0) return;

   // Check entry window (trade within first few hours after measurement)
   int entryHour = InpSessionOpenH + (InpMeasureBars * 15) / 60;  // rough calc
   if(dt.hour < entryHour) return;
   if(dt.hour >= InpExitH - 2) return;  // Don't enter too late

   // Daily DD check
   double ddPct = (g_dayStartBal > 0) ?
      (g_dayStartBal - AccountInfoDouble(ACCOUNT_EQUITY)) / g_dayStartBal * 100.0 : 0;
   if(ddPct >= InpDailyDDPct) return;

   // Read ATR
   double atr[];
   if(CopyBuffer(g_hATR, 0, 1, 1, atr) < 1) return;
   double atrVal = atr[0];
   if(atrVal <= 0) return;

   double pt = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   double moveAbs = MathAbs(g_openReturn);

   // Minimum move filter
   if(moveAbs < InpMinMovePts * pt) return;
   if(moveAbs < atrVal * InpMinMoveATR) return;

   // Direction: follow the opening return
   bool isBuy = (g_openReturn > 0);

   int digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
   double slDist = atrVal * InpSL_ATRMult;
   double tpDist = atrVal * InpTP_ATRMult;
   double slPts  = slDist / pt;

   double stopLevel = (double)SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL) * pt;
   if(slDist < stopLevel || tpDist < stopLevel) return;

   double price, sl, tp;
   if(isBuy)
   {
      price = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
      sl = NormalizeDouble(price - slDist, digits);
      tp = NormalizeDouble(price + tpDist, digits);
   }
   else
   {
      price = SymbolInfoDouble(_Symbol, SYMBOL_BID);
      sl = NormalizeDouble(price + slDist, digits);
      tp = NormalizeDouble(price - tpDist, digits);
   }

   double lot = CalcLot(slPts);
   if(lot <= 0) return;

   string comment = StringFormat("OHM|h%d|ret=%.0fpip|%s",
                                 InpSessionOpenH, moveAbs / pt,
                                 isBuy ? "LONG" : "SHORT");

   bool ok = g_trade.PositionOpen(_Symbol,
               isBuy ? ORDER_TYPE_BUY : ORDER_TYPE_SELL,
               lot, price, sl, tp, comment);

   if(ok)
   {
      g_tradedToday = true;
      PrintFormat("[OHM] %s %.2f @ %.5f | openRet=%.0fpip | ATR=%.0f",
                  isBuy ? "BUY" : "SELL", lot, price,
                  moveAbs / pt, atrVal / pt);
   }
}

//+------------------------------------------------------------------+
double OnTester()
{
   double pf = TesterStatistics(STAT_PROFIT_FACTOR);
   double trades = TesterStatistics(STAT_TRADES);
   if(trades < 30) return 0;
   return pf * MathSqrt(trades);
}
//+------------------------------------------------------------------+
