//+------------------------------------------------------------------+
//| EA_LondonSweep.mq5                                               |
//| S698: Asia Range Sweep Fakeout Reversal — London Open             |
//|                                                                    |
//| Hypothesis: During London open, price sweeps Asia range extremes   |
//| to trigger stops. When the sweep is a fakeout (closes back inside),|
//| a reversal entry captures the mean-reversion move.                 |
//|                                                                    |
//| Prior art: S537 (XAUUSD M15 Asian sweep) PF 0.99 at 571 trades.   |
//| Differentiation: requires close-back-inside confirmation           |
//| (filters out genuine breakouts that killed S537).                  |
//+------------------------------------------------------------------+
#property copyright "AlphaFactory"
#property version   "1.00"
#property description "S698: Asia range sweep fakeout — London open baseline"

#include <Trade\Trade.mqh>
#include <Trade\SymbolInfo.mqh>

//--- Session timing (broker server time)
input group "=== Session (Broker Time) ==="
input int    InpAsiaStartH      = 2;      // Asia range start hour
input int    InpAsiaEndH        = 10;     // Asia range end hour
input int    InpLdnStartH       = 10;     // London sweep window start
input int    InpLdnEndH         = 14;     // London sweep window end

//--- Signal thresholds (ATR multiples)
input group "=== Signal ==="
input double InpSweepATR        = 0.5;    // Min sweep beyond Asia extreme (xATR)
input double InpBufferATR       = 0.3;    // SL buffer beyond sweep (xATR)
input int    InpATRPeriod       = 14;     // ATR period
input double InpMinRangePips    = 50;     // Min Asia range (points, gold: 50=$0.50)
input bool   InpSkipMonday      = false;  // Skip Monday
input bool   InpSkipFriday      = true;   // Skip Friday

//--- Risk
input group "=== Risk ==="
input double InpRiskPct         = 0.5;    // Risk per trade (% balance)
input double InpRR              = 1.5;    // Reward:Risk
input int    InpMaxTradesDay    = 1;      // Max trades/day
input double InpMaxDDPct        = 4.0;    // Daily DD kill (%)

//--- EA config
input group "=== Config ==="
input int    InpMagic           = 698001; // Magic number
input double InpMaxSpreadATR    = 0.15;   // Max spread (xATR)

//+------------------------------------------------------------------+
CTrade      m_trade;
CSymbolInfo m_sym;

int    g_atrHandle;
double g_asiaHigh, g_asiaLow;
bool   g_asiaOK;
int    g_tradesToday, g_lastDay;
double g_dayBal;

//+------------------------------------------------------------------+
int OnInit()
{
   m_trade.SetExpertMagicNumber(InpMagic);
   m_trade.SetDeviationInPoints(30);
   if(!m_sym.Name(_Symbol)) return INIT_FAILED;

   // Fill mode
   long fm = SymbolInfoInteger(_Symbol, SYMBOL_FILLING_MODE);
   if(fm & SYMBOL_FILLING_FOK)       m_trade.SetTypeFilling(ORDER_FILLING_FOK);
   else if(fm & SYMBOL_FILLING_IOC)  m_trade.SetTypeFilling(ORDER_FILLING_IOC);
   else                              m_trade.SetTypeFilling(ORDER_FILLING_RETURN);

   g_atrHandle = iATR(_Symbol, PERIOD_M15, InpATRPeriod);
   if(g_atrHandle == INVALID_HANDLE) return INIT_FAILED;

   ResetDay();
   return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   if(g_atrHandle != INVALID_HANDLE)
      IndicatorRelease(g_atrHandle);
}

//+------------------------------------------------------------------+
void OnTick()
{
   // New M15 bar gate
   static datetime s_bar = 0;
   datetime bar0 = iTime(_Symbol, PERIOD_M15, 0);
   if(bar0 == s_bar) return;
   s_bar = bar0;

   m_sym.RefreshRates();

   MqlDateTime dt;
   TimeToStruct(TimeTradeServer(), dt);
   int h = dt.hour;

   // Daily reset
   if(dt.day != g_lastDay)
   {
      ResetDay();
      g_lastDay = dt.day;
   }

   // DD kill
   double eq = AccountInfoDouble(ACCOUNT_EQUITY);
   if(g_dayBal > 0 && (g_dayBal - eq) / g_dayBal * 100.0 >= InpMaxDDPct)
      return;

   // Day filters
   if(dt.day_of_week <= 0 || dt.day_of_week >= 6) return;
   if(InpSkipMonday && dt.day_of_week == 1) return;
   if(InpSkipFriday && dt.day_of_week == 5) return;

   // London session: check for sweeps
   if(h >= InpLdnStartH && h < InpLdnEndH)
   {
      if(!g_asiaOK)
         BuildAsiaRange(dt);

      if(g_asiaOK && g_tradesToday < InpMaxTradesDay && !HasPos())
         CheckSweep();
   }
}

//+------------------------------------------------------------------+
void ResetDay()
{
   g_asiaHigh = 0;
   g_asiaLow  = DBL_MAX;
   g_asiaOK   = false;
   g_tradesToday = 0;
   g_dayBal   = AccountInfoDouble(ACCOUNT_BALANCE);
}

//+------------------------------------------------------------------+
void BuildAsiaRange(const MqlDateTime &now)
{
   g_asiaHigh = 0;
   g_asiaLow  = DBL_MAX;

   for(int i = 1; i <= 96; i++)
   {
      datetime bt = iTime(_Symbol, PERIOD_M15, i);
      if(bt == 0) break;

      MqlDateTime bd;
      TimeToStruct(bt, bd);

      // Only today's bars
      if(bd.day != now.day || bd.mon != now.mon || bd.year != now.year)
         continue;

      // Asia session hours
      if(bd.hour >= InpAsiaStartH && bd.hour < InpAsiaEndH)
      {
         double bh = iHigh(_Symbol, PERIOD_M15, i);
         double bl = iLow(_Symbol, PERIOD_M15, i);
         if(bh > g_asiaHigh) g_asiaHigh = bh;
         if(bl < g_asiaLow)  g_asiaLow  = bl;
      }
   }

   if(g_asiaHigh > 0 && g_asiaLow < DBL_MAX
      && (g_asiaHigh - g_asiaLow) >= InpMinRangePips * m_sym.Point())
   {
      g_asiaOK = true;
   }
}

//+------------------------------------------------------------------+
void CheckSweep()
{
   // Closed bar analysis only (shift=1, non-repaint)
   double h1 = iHigh(_Symbol, PERIOD_M15, 1);
   double l1 = iLow(_Symbol, PERIOD_M15, 1);
   double c1 = iClose(_Symbol, PERIOD_M15, 1);

   double atr[1];
   if(CopyBuffer(g_atrHandle, 0, 1, 1, atr) != 1 || atr[0] <= 0) return;

   double sweepMin = InpSweepATR * atr[0];
   double buffer   = InpBufferATR * atr[0];
   double spread   = m_sym.Ask() - m_sym.Bid();
   if(spread > InpMaxSpreadATR * atr[0]) return;

   // === SWEEP UP: bar swept above Asia high, closed back inside → SHORT ===
   if(h1 >= g_asiaHigh + sweepMin && c1 < g_asiaHigh)
   {
      double entry = m_sym.Bid();
      double sl    = NormalizeDouble(h1 + buffer, m_sym.Digits());
      double slD   = sl - entry;
      if(slD <= 0) return;

      double tp = NormalizeDouble(entry - slD * InpRR, m_sym.Digits());
      if(!CheckStopLevel(slD, entry - tp)) return;

      double lots = CalcLots(slD);
      if(lots <= 0) return;

      if(m_trade.Sell(lots, _Symbol, entry, sl, tp, "LdnSwp_S"))
         g_tradesToday++;
   }

   // === SWEEP DOWN: bar swept below Asia low, closed back inside → LONG ===
   if(l1 <= g_asiaLow - sweepMin && c1 > g_asiaLow)
   {
      double entry = m_sym.Ask();
      double sl    = NormalizeDouble(l1 - buffer, m_sym.Digits());
      double slD   = entry - sl;
      if(slD <= 0) return;

      double tp = NormalizeDouble(entry + slD * InpRR, m_sym.Digits());
      if(!CheckStopLevel(slD, tp - entry)) return;

      double lots = CalcLots(slD);
      if(lots <= 0) return;

      if(m_trade.Buy(lots, _Symbol, entry, sl, tp, "LdnSwp_L"))
         g_tradesToday++;
   }
}

//+------------------------------------------------------------------+
bool CheckStopLevel(double slDist, double tpDist)
{
   double stopLvl = m_sym.StopsLevel() * m_sym.Point();
   return (slDist >= stopLvl && tpDist >= stopLvl);
}

//+------------------------------------------------------------------+
double CalcLots(double slDist)
{
   if(slDist <= 0) return 0;

   double bal  = AccountInfoDouble(ACCOUNT_BALANCE);
   double risk = bal * InpRiskPct / 100.0;
   double tv   = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
   double ts   = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   if(tv <= 0 || ts <= 0) return 0;

   double lots = risk / (slDist / ts * tv);

   double mn = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double mx = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   double st = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   if(st <= 0) return 0;

   lots = MathFloor(lots / st) * st;
   return MathMax(mn, MathMin(mx, lots));
}

//+------------------------------------------------------------------+
bool HasPos()
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong t = PositionGetTicket(i);
      if(t > 0 && PositionGetInteger(POSITION_MAGIC) == InpMagic
         && PositionGetString(POSITION_SYMBOL) == _Symbol)
         return true;
   }
   return false;
}
//+------------------------------------------------------------------+
