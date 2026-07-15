//+------------------------------------------------------------------+
//| EA_AsianTailFade.mq5 — Asian Session Tail Liquidation Fade       |
//| Symbol: XAUUSD+  |  Period: M15  |  Style: Mean Reversion        |
//|                                                                   |
//| EDGE HYPOTHESIS:                                                  |
//| In the last 2-4 hours of Asian session, Tokyo/Singapore desks    |
//| flatten directional positions built during early Asia before     |
//| London open. If gold moved significantly in one direction        |
//| during early Asia (h0-h3 server), the accumulated move reverts   |
//| partially during the tail window (h4-h8 server) as desks        |
//| liquidate. This creates a mean-reversion opportunity.            |
//|                                                                   |
//| STRUCTURAL REASON:                                                |
//| - Institutional inventory management: desks must flatten before  |
//|   handoff to London. Risk limits require position reduction.     |
//| - Not behavioral (not "pattern trading") — it's mechanical       |
//|   position management driven by compliance/risk mandates.        |
//| - Triggers ONLY when early Asia had directional accumulation,    |
//|   not on random days.                                             |
//|                                                                   |
//| KEY DIFFERENCE FROM TESTED STRATEGIES:                            |
//| - Not session breakout (not trading the break of a range)        |
//| - Not H1-open MR (not fading overnight vs open)                  |
//| - Not AM Fix (not timing around LBMA auction)                    |
//| - This fades accumulated INTRADAY move within ONE session        |
//|                                                                   |
//| SIGNALS ON BAR[1] ONLY — no repaint, no lookahead.               |
//| Max | 2026-04-12 | v1.0                                         |
//+------------------------------------------------------------------+
#property copyright "Max - EA_AsianTailFade v1.0"
#property version   "1.00"
#property strict

#include <Trade\Trade.mqh>

//+------------------------------------------------------------------+
input group "=== General ==="
input ulong    InpMagic         = 803001;
input int      InpDeviation     = 30;
input bool     InpKillSwitch    = false;

input group "=== Asia Early Window (measure move) ==="
input int      InpAsiaEarlyStart = 0;        // Early Asia start hour (server)
input int      InpAsiaEarlyEnd   = 3;        // Early Asia end hour (server)

input group "=== Fade Window (trade) ==="
input int      InpFadeStart     = 4;         // Fade window start hour (server)
input int      InpFadeEnd       = 8;         // Fade window end hour (server)
input int      InpForceCloseH   = 9;         // Force close hour (before London)

input group "=== Displacement Threshold ==="
input double   InpMinMovePts    = 80;        // Min early-Asia move (points) to trigger
input double   InpMaxMovePts    = 800;       // Max move (skip extreme days)
input int      InpATRPeriod     = 14;
input bool     InpUseATRFilter  = true;      // Use ATR-based threshold instead of fixed
input double   InpMinMoveATR    = 0.5;       // Min move in ATR multiples

input group "=== Risk ==="
input double   InpRiskPct       = 0.50;
input double   InpMaxLot        = 0.50;
input int      InpMaxPerDay     = 2;
input double   InpDailyDDPct    = 4.0;
input double   InpSL_ATRMult    = 1.5;       // SL = ATR * this
input double   InpTP_Revert     = 0.50;      // TP = this fraction of early move

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
double   g_asiaEarlyOpen;    // Price at start of early Asia
double   g_asiaEarlyClose;   // Price at end of early Asia
double   g_asiaEarlyHigh;
double   g_asiaEarlyLow;
double   g_earlyMove;        // Signed: close - open of early Asia
bool     g_earlyMeasured;
bool     g_tradedToday;
int      g_tradesToday;

//+------------------------------------------------------------------+
int OnInit()
{
   if(InpKillSwitch) return INIT_SUCCEEDED;
   g_trade.SetExpertMagicNumber(InpMagic);
   g_trade.SetDeviationInPoints(InpDeviation);
   g_trade.SetTypeFilling(ORDER_FILLING_FOK);

   g_hATR = iATR(_Symbol, PERIOD_CURRENT, InpATRPeriod);
   if(g_hATR == INVALID_HANDLE) { Print("[ATF] ATR init fail"); return INIT_FAILED; }

   g_lastBar = 0; g_todayDate = 0; g_tradesToday = 0;
   g_asiaEarlyOpen = 0; g_asiaEarlyClose = 0;
   g_earlyMove = 0; g_earlyMeasured = false; g_tradedToday = false;
   g_asiaEarlyHigh = 0; g_asiaEarlyLow = DBL_MAX;
   g_dayStartBal = AccountInfoDouble(ACCOUNT_BALANCE);

   PrintFormat("[ATF] AsianTailFade v1.0 | %s %s | Magic=%d",
               _Symbol, EnumToString(_Period), InpMagic);
   PrintFormat("[ATF] Early Asia: h%d-h%d | Fade: h%d-h%d | Close: h%d",
               InpAsiaEarlyStart, InpAsiaEarlyEnd,
               InpFadeStart, InpFadeEnd, InpForceCloseH);
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
      g_tradesToday = 0;
      g_tradedToday = false;
      g_earlyMeasured = false;
      g_asiaEarlyOpen = 0;
      g_asiaEarlyClose = 0;
      g_asiaEarlyHigh = 0;
      g_asiaEarlyLow = DBL_MAX;
      g_earlyMove = 0;
      g_dayStartBal = AccountInfoDouble(ACCOUNT_BALANCE);
   }

   //--- Phase 1: Measure early Asia move
   if(dt.hour >= InpAsiaEarlyStart && dt.hour < InpAsiaEarlyEnd)
   {
      // Track the early Asia window
      double close1 = iClose(_Symbol, PERIOD_CURRENT, 1);
      double high1  = iHigh(_Symbol, PERIOD_CURRENT, 1);
      double low1   = iLow(_Symbol, PERIOD_CURRENT, 1);

      if(g_asiaEarlyOpen <= 0)
         g_asiaEarlyOpen = iOpen(_Symbol, PERIOD_CURRENT, 1);

      g_asiaEarlyClose = close1;
      if(high1 > g_asiaEarlyHigh) g_asiaEarlyHigh = high1;
      if(low1 < g_asiaEarlyLow)   g_asiaEarlyLow  = low1;
      return;
   }

   //--- Phase 1b: Finalize early Asia measurement
   if(dt.hour == InpAsiaEarlyEnd && !g_earlyMeasured)
   {
      if(g_asiaEarlyOpen > 0 && g_asiaEarlyClose > 0)
      {
         g_earlyMove = g_asiaEarlyClose - g_asiaEarlyOpen;
         g_earlyMeasured = true;
      }
   }

   //--- Force close before London
   if(CountPos() > 0 && dt.hour >= InpForceCloseH)
   {
      CloseAll();
      return;
   }

   //--- Phase 2: Trade in fade window
   if(!g_earlyMeasured) return;
   if(dt.hour < InpFadeStart || dt.hour >= InpFadeEnd) return;
   if(!IsTradingDay(dt.day_of_week)) return;
   if(g_tradesToday >= InpMaxPerDay) return;
   if(CountPos() > 0) return;

   double ddPct = (g_dayStartBal > 0) ?
      (g_dayStartBal - AccountInfoDouble(ACCOUNT_EQUITY)) / g_dayStartBal * 100.0 : 0;
   if(ddPct >= InpDailyDDPct) return;

   // Check displacement threshold
   double pt = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   double moveAbs = MathAbs(g_earlyMove);
   double movePts = moveAbs / pt;

   if(movePts < InpMinMovePts || movePts > InpMaxMovePts) return;

   // ATR filter
   double atr[];
   if(CopyBuffer(g_hATR, 0, 1, 1, atr) < 1) return;
   double atrVal = atr[0];
   if(atrVal <= 0) return;

   if(InpUseATRFilter && (moveAbs < atrVal * InpMinMoveATR)) return;

   // Check if price has already reverted significantly
   double close1 = iClose(_Symbol, PERIOD_CURRENT, 1);
   double currentReversion = 0;
   if(g_earlyMove > 0)
      currentReversion = (g_asiaEarlyClose - close1) / g_earlyMove;
   else if(g_earlyMove < 0)
      currentReversion = (g_asiaEarlyClose - close1) / g_earlyMove;

   // If already reverted > 50%, opportunity may be gone
   if(currentReversion > 0.6) return;

   // FADE the early Asia move
   bool isBuy = (g_earlyMove < 0);  // Asia dropped → buy
   // g_earlyMove > 0 → Asia rallied → sell

   int digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
   double slDist = atrVal * InpSL_ATRMult;
   double tpDist = moveAbs * InpTP_Revert;  // Target partial reversion

   // Clamp TP to reasonable range
   if(tpDist < 30 * pt) tpDist = 30 * pt;
   if(tpDist > 500 * pt) tpDist = 500 * pt;

   double slPts = slDist / pt;
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

   string comment = StringFormat("ATF|%s|mv=%.0f|rev=%.0f%%",
                                 isBuy ? "BUY" : "SELL",
                                 movePts, currentReversion * 100);

   bool ok = g_trade.PositionOpen(_Symbol,
               isBuy ? ORDER_TYPE_BUY : ORDER_TYPE_SELL,
               lot, price, sl, tp, comment);

   if(ok)
   {
      g_tradesToday++;
      PrintFormat("[ATF] %s %.2f @ %.2f | earlyMove=%.0fpip | rev=%.0f%%",
                  isBuy ? "BUY" : "SELL", lot, price,
                  movePts, currentReversion * 100);
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
