//+------------------------------------------------------------------+
//| EA_PostFixRevert.mq5 — WMR Post-Fix Mean Reversion               |
//| Symbol: XAUUSD+  |  Period: M15  |  Style: Mean Reversion        |
//|                                                                   |
//| EDGE HYPOTHESIS:                                                  |
//| At 15:00 London (17:00 server GMT+2), the LBMA PM Fix ends.     |
//| During the fix window (14:50-15:00), massive institutional       |
//| hedging orders create temporary price dislocation.               |
//| AFTER the fix, market snaps back to fair value.                  |
//|                                                                   |
//| This is the OPPOSITE of Cobra: Cobra rides WITH the fix flow.    |
//| PostFixRevert fades the fix displacement AFTER it ends.           |
//|                                                                   |
//| STRUCTURAL REASON:                                                |
//| - Fix orders are non-price-sensitive (mandatory hedging)         |
//| - Once hedgers finish, no more directional pressure              |
//| - Market makers who facilitated the fix unwind risk              |
//| - Academic evidence: "reversal in the minute after fix"          |
//|                                                                   |
//| Source: Panagiotou (EFMA 2017) "The WMR Fix and its Impact"      |
//|                                                                   |
//| SIGNALS ON BAR[1] ONLY — no repaint, no lookahead.               |
//| Max | 2026-04-12 | v1.0                                         |
//+------------------------------------------------------------------+
#property copyright "Max - EA_PostFixRevert v1.0"
#property version   "1.00"
#property strict

#include <Trade\Trade.mqh>

//+------------------------------------------------------------------+
input group "=== General ==="
input ulong    InpMagic         = 805001;
input int      InpDeviation     = 30;
input bool     InpKillSwitch    = false;

input group "=== Fix Timing (Server Time, GMT+2 winter) ==="
input int      InpPreFixH       = 16;        // Pre-fix reference hour (measure start)
input int      InpFixEndH       = 17;        // Fix end hour (entry hour)
input int      InpFixEndM       = 15;        // Fix end minute (entry after this)
input int      InpExitH         = 19;        // Force exit hour
input int      InpHoldBars      = 8;         // Max bars to hold (8 x M15 = 2h)

input group "=== Displacement ==="
input int      InpATRPeriod     = 14;
input double   InpMinDispATR    = 0.3;       // Min fix displacement as ATR multiple
input double   InpMaxDispATR    = 3.0;       // Max (skip extreme events)

input group "=== Risk ==="
input double   InpRiskPct       = 0.50;
input double   InpMaxLot        = 0.50;
input double   InpDailyDDPct    = 4.0;
input double   InpSL_ATRMult    = 1.2;       // SL = ATR * this
input double   InpTP_Revert     = 0.50;      // TP = fraction of fix move

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
double   g_preFixPrice;       // Price at pre-fix reference
double   g_fixEndPrice;       // Price at fix end
bool     g_preFixRecorded;
datetime g_posOpenTime;

//+------------------------------------------------------------------+
int OnInit()
{
   if(InpKillSwitch) return INIT_SUCCEEDED;

   g_trade.SetExpertMagicNumber(InpMagic);
   g_trade.SetDeviationInPoints(InpDeviation);
   g_trade.SetTypeFilling(ORDER_FILLING_FOK);

   g_hATR = iATR(_Symbol, PERIOD_CURRENT, InpATRPeriod);
   if(g_hATR == INVALID_HANDLE) { Print("[PFR] ATR init fail"); return INIT_FAILED; }

   g_lastBar = 0; g_todayDate = 0;
   g_preFixPrice = 0; g_fixEndPrice = 0;
   g_preFixRecorded = false; g_tradedToday = false;
   g_posOpenTime = 0;
   g_dayStartBal = AccountInfoDouble(ACCOUNT_BALANCE);

   PrintFormat("[PFR] PostFixRevert v1.0 | %s %s | PreFix h%d | FixEnd h%d:%02d | Exit h%d",
               _Symbol, EnumToString(_Period),
               InpPreFixH, InpFixEndH, InpFixEndM, InpExitH);
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
      g_preFixPrice = 0;
      g_fixEndPrice = 0;
      g_preFixRecorded = false;
      g_posOpenTime = 0;
      g_dayStartBal = AccountInfoDouble(ACCOUNT_BALANCE);
   }

   // Time-based exit
   if(CountPos() > 0)
   {
      if(dt.hour >= InpExitH)
      {
         CloseAll();
         g_posOpenTime = 0;
         return;
      }
      // Max bars hold
      if(g_posOpenTime > 0)
      {
         int barsHeld = iBarShift(_Symbol, PERIOD_CURRENT, g_posOpenTime, false);
         if(barsHeld >= InpHoldBars)
         {
            CloseAll();
            g_posOpenTime = 0;
         }
      }
      return;
   }

   //--- Phase 1: Record pre-fix price
   if(dt.hour == InpPreFixH && !g_preFixRecorded)
   {
      g_preFixPrice = iClose(_Symbol, PERIOD_CURRENT, 1);
      g_preFixRecorded = true;
      return;
   }

   //--- Phase 2: At fix end, measure displacement and trade
   if(g_tradedToday) return;
   if(!g_preFixRecorded || g_preFixPrice <= 0) return;
   if(!IsTradingDay(dt.day_of_week)) return;

   // Entry at fix end hour
   if(dt.hour != InpFixEndH) return;
   if(dt.min < InpFixEndM) return;

   // Daily DD check
   double ddPct = (g_dayStartBal > 0) ?
      (g_dayStartBal - AccountInfoDouble(ACCOUNT_EQUITY)) / g_dayStartBal * 100.0 : 0;
   if(ddPct >= InpDailyDDPct) return;

   // Measure fix displacement
   double closeNow = iClose(_Symbol, PERIOD_CURRENT, 1);
   double fixMove = closeNow - g_preFixPrice;
   double moveAbs = MathAbs(fixMove);

   // Read ATR
   double atr[];
   if(CopyBuffer(g_hATR, 0, 1, 1, atr) < 1) return;
   double atrVal = atr[0];
   if(atrVal <= 0) return;

   double dispATR = moveAbs / atrVal;
   if(dispATR < InpMinDispATR || dispATR > InpMaxDispATR) return;

   // FADE the fix move (reversal)
   double pt = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   bool isBuy = (fixMove < 0);   // Fix pushed price DOWN → buy (expect revert up)
   // fixMove > 0 → Fix pushed price UP → sell (expect revert down)

   int digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
   double slDist = atrVal * InpSL_ATRMult;
   double tpDist = moveAbs * InpTP_Revert;

   // Clamp TP
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

   string comment = StringFormat("PFR|%s|fix=%.0f|atr=%.1f",
                                 isBuy ? "BUY" : "SELL",
                                 moveAbs / pt, dispATR);

   bool ok = g_trade.PositionOpen(_Symbol,
               isBuy ? ORDER_TYPE_BUY : ORDER_TYPE_SELL,
               lot, price, sl, tp, comment);

   if(ok)
   {
      g_tradedToday = true;
      g_posOpenTime = barTime;
      PrintFormat("[PFR] %s %.2f @ %.2f | fixMove=%.0fpip | dispATR=%.2f",
                  isBuy ? "BUY" : "SELL", lot, price,
                  moveAbs / pt, dispATR);
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
