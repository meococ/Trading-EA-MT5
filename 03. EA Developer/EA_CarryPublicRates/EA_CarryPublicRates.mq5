//+------------------------------------------------------------------+
//| EA_CarryPublicRates.mq5 — D1 G3 carry rank (public rates)        |
//| Symbols: EURUSD, GBPUSD, USDJPY | TF: D1 | Magic: 880801         |
//|                                                                   |
//| Closed-bar[1] only. Rates CSV (date,usd,eur,gbp,jpy) with        |
//| ~24h lag: use latest row with date <= bar1_date - 1 calendar day.|
//| Rank FX differentials; long max / short min if spread >= 0.25.   |
//| ATR(14) SL 1.5 / TP 2.0. Friday flat (weekend risk).             |
//|                                                                   |
//| Hypothesis: HYP_CARRY_PUBLIC_RATES_D1_001                         |
//| Scaffold under Owner unlimited-GOAL authority 2026-07-13.        |
//+------------------------------------------------------------------+
#property copyright "SonicR / EA_CarryPublicRates"
#property version   "1.00"
#property strict

#include <Trade\Trade.mqh>

input group "=== General ==="
input ulong    InpMagic           = 880801;
input int      InpDeviation       = 30;
input bool     InpKillSwitch      = false;

input group "=== Universe ==="
input string   InpSymEURUSD       = "EURUSD";
input string   InpSymGBPUSD       = "GBPUSD";
input string   InpSymUSDJPY       = "USDJPY";

input group "=== Rates CSV ==="
input string   InpRatesFile       = "carry_rates_d1.csv";  // FILE_COMMON then terminal Files
input int      InpRateLagDays     = 1;                     // calendar-day lag vs bar[1] date

input group "=== Signal ==="
input double   InpMinSpreadPct    = 0.25;                  // max_diff - min_diff (percentage points)
input int      InpATRPeriod       = 14;
input double   InpSL_ATR          = 1.5;
input double   InpTP_ATR          = 2.0;

input group "=== Risk ==="
input double   InpRiskPct         = 0.50;
input double   InpMaxLot          = 1.0;
input bool     InpFridayFlat      = true;

#define MAX_RATE_ROWS 12000
#define N_PAIRS 3

struct RateRow
{
   datetime day;   // 00:00 of observation date
   double   usd;
   double   eur;
   double   gbp;
   double   jpy;
};

struct PairState
{
   string   symbol;
   int      hATR;
   datetime lastBar;
};

CTrade   g_trade;
RateRow  g_rates[];
int      g_rateCount = 0;
PairState g_pairs[N_PAIRS];
bool     g_ratesLoaded = false;

//+------------------------------------------------------------------+
datetime DateOnly(datetime t)
{
   MqlDateTime dt;
   TimeToStruct(t, dt);
   dt.hour = 0;
   dt.min  = 0;
   dt.sec  = 0;
   return StructToTime(dt);
}

//+------------------------------------------------------------------+
datetime ParseYmd(const string s)
{
   // Accept YYYY-MM-DD or YYYY.MM.DD
   string t = s;
   StringReplace(t, ".", "-");
   StringTrimLeft(t);
   StringTrimRight(t);
   if(StringLen(t) < 10)
      return 0;
   int y = (int)StringToInteger(StringSubstr(t, 0, 4));
   int m = (int)StringToInteger(StringSubstr(t, 5, 2));
   int d = (int)StringToInteger(StringSubstr(t, 8, 2));
   if(y < 1970 || m < 1 || m > 12 || d < 1 || d > 31)
      return 0;
   MqlDateTime dt;
   dt.year = y;
   dt.mon  = m;
   dt.day  = d;
   dt.hour = 0;
   dt.min  = 0;
   dt.sec  = 0;
   return StructToTime(dt);
}

//+------------------------------------------------------------------+
bool OpenRatesHandle(const string name, int &handle, bool &usedCommon)
{
   handle = FileOpen(name, FILE_READ | FILE_CSV | FILE_ANSI | FILE_COMMON, ',');
   if(handle != INVALID_HANDLE)
   {
      usedCommon = true;
      return true;
   }
   handle = FileOpen(name, FILE_READ | FILE_CSV | FILE_ANSI, ',');
   if(handle != INVALID_HANDLE)
   {
      usedCommon = false;
      return true;
   }
   return false;
}

//+------------------------------------------------------------------+
bool LoadRatesCsv()
{
   int handle = INVALID_HANDLE;
   bool usedCommon = false;
   if(!OpenRatesHandle(InpRatesFile, handle, usedCommon))
   {
      PrintFormat("[CARRY] FATAL: rates CSV missing: '%s' (tried FILE_COMMON then terminal Files). Err=%d",
                  InpRatesFile, GetLastError());
      Print("[CARRY] Place carry_rates_d1.csv under Common\\Files or MQL5\\Files, or run build_carry_rates_d1.py");
      return false;
   }

   // Skip header: date,usd,eur,gbp,jpy
   if(!FileIsEnding(handle))
   {
      FileReadString(handle);
      FileReadString(handle);
      FileReadString(handle);
      FileReadString(handle);
      FileReadString(handle);
   }

   ArrayResize(g_rates, 0, 1024);
   g_rateCount = 0;
   while(!FileIsEnding(handle) && g_rateCount < MAX_RATE_ROWS)
   {
      string ds = FileReadString(handle);
      if(StringLen(ds) == 0)
         break;
      string us = FileReadString(handle);
      string es = FileReadString(handle);
      string gs = FileReadString(handle);
      string js = FileReadString(handle);

      datetime day = ParseYmd(ds);
      if(day == 0)
         continue;
      double usd = StringToDouble(us);
      double eur = StringToDouble(es);
      double gbp = StringToDouble(gs);
      double jpy = StringToDouble(js);
      if(usd == 0.0 && eur == 0.0 && gbp == 0.0 && jpy == 0.0)
         continue;

      int n = g_rateCount;
      ArrayResize(g_rates, n + 1, 1024);
      g_rates[n].day = day;
      g_rates[n].usd = usd;
      g_rates[n].eur = eur;
      g_rates[n].gbp = gbp;
      g_rates[n].jpy = jpy;
      g_rateCount++;
   }
   FileClose(handle);

   if(g_rateCount < 10)
   {
      PrintFormat("[CARRY] FATAL: rates CSV loaded only %d rows from '%s'", g_rateCount, InpRatesFile);
      return false;
   }

   // Ensure ascending by day for binary-ish scan
   for(int i = 1; i < g_rateCount; i++)
   {
      RateRow key = g_rates[i];
      int j = i - 1;
      while(j >= 0 && g_rates[j].day > key.day)
      {
         g_rates[j + 1] = g_rates[j];
         j--;
      }
      g_rates[j + 1] = key;
   }

   PrintFormat("[CARRY] Loaded %d rate rows from '%s' (%s)",
               g_rateCount, InpRatesFile, usedCommon ? "FILE_COMMON" : "terminal Files");
   return true;
}

//+------------------------------------------------------------------+
bool FindLaggedRates(const datetime bar1Time, RateRow &outRow)
{
   datetime barDay = DateOnly(bar1Time);
   datetime cutoff = barDay - (datetime)(InpRateLagDays * 86400);
   // Latest row with date <= cutoff
   int lo = 0;
   int hi = g_rateCount - 1;
   int best = -1;
   while(lo <= hi)
   {
      int mid = (lo + hi) / 2;
      if(g_rates[mid].day <= cutoff)
      {
         best = mid;
         lo = mid + 1;
      }
      else
         hi = mid - 1;
   }
   if(best < 0)
      return false;
   outRow = g_rates[best];
   return true;
}

//+------------------------------------------------------------------+
double PairDifferential(const string symbol, const RateRow &r)
{
   // Carry differential in percentage points (base funding - quote funding proxy).
   if(symbol == InpSymEURUSD)
      return r.eur - r.usd;
   if(symbol == InpSymGBPUSD)
      return r.gbp - r.usd;
   if(symbol == InpSymUSDJPY)
      return r.usd - r.jpy;
   return 0.0;
}

//+------------------------------------------------------------------+
int CountMagicPositions(const string symbol)
{
   int cnt = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0)
         continue;
      if(PositionGetInteger(POSITION_MAGIC) != (long)InpMagic)
         continue;
      if(PositionGetString(POSITION_SYMBOL) != symbol)
         continue;
      cnt++;
   }
   return cnt;
}

//+------------------------------------------------------------------+
void CloseMagicPositions(const string symbol)
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0)
         continue;
      if(PositionGetInteger(POSITION_MAGIC) != (long)InpMagic)
         continue;
      if(PositionGetString(POSITION_SYMBOL) != symbol)
         continue;
      if(!g_trade.PositionClose(ticket))
         PrintFormat("[CARRY] Close fail %s ticket=%s err=%d", symbol, IntegerToString(ticket), GetLastError());
   }
}

//+------------------------------------------------------------------+
void CloseAllMagic()
{
   for(int p = 0; p < N_PAIRS; p++)
      CloseMagicPositions(g_pairs[p].symbol);
}

//+------------------------------------------------------------------+
double CalcLots(const string symbol, const double slDistance)
{
   if(slDistance <= 0.0)
      return 0.0;
   double balance = AccountInfoDouble(ACCOUNT_BALANCE);
   double riskCash = balance * (InpRiskPct / 100.0);
   double tickSize = SymbolInfoDouble(symbol, SYMBOL_TRADE_TICK_SIZE);
   double tickValue = SymbolInfoDouble(symbol, SYMBOL_TRADE_TICK_VALUE);
   double step = SymbolInfoDouble(symbol, SYMBOL_VOLUME_STEP);
   double vmin = SymbolInfoDouble(symbol, SYMBOL_VOLUME_MIN);
   double vmax = SymbolInfoDouble(symbol, SYMBOL_VOLUME_MAX);
   if(tickSize <= 0.0 || tickValue <= 0.0 || step <= 0.0)
      return 0.0;
   double moneyPerLot = (slDistance / tickSize) * tickValue;
   if(moneyPerLot <= 0.0)
      return 0.0;
   double lots = riskCash / moneyPerLot;
   lots = MathFloor(lots / step) * step;
   if(lots < vmin)
      lots = 0.0;
   if(lots > vmax)
      lots = vmax;
   if(lots > InpMaxLot)
      lots = MathFloor(InpMaxLot / step) * step;
   return lots;
}

//+------------------------------------------------------------------+
bool OpenDirectional(const string symbol, const int dir, const double atr)
{
   if(dir == 0 || atr <= 0.0)
      return false;
   if(CountMagicPositions(symbol) > 0)
      CloseMagicPositions(symbol);

   double point = SymbolInfoDouble(symbol, SYMBOL_POINT);
   int digits = (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS);
   double slDist = InpSL_ATR * atr;
   double tpDist = InpTP_ATR * atr;
   if(slDist < 10.0 * point)
      slDist = 10.0 * point;

   double lots = CalcLots(symbol, slDist);
   if(lots <= 0.0)
   {
      PrintFormat("[CARRY] Skip %s: lot calc zero (atr=%.5f)", symbol, atr);
      return false;
   }

   double ask = SymbolInfoDouble(symbol, SYMBOL_ASK);
   double bid = SymbolInfoDouble(symbol, SYMBOL_BID);
   double price = (dir > 0) ? ask : bid;
   double sl = (dir > 0) ? (price - slDist) : (price + slDist);
   double tp = (dir > 0) ? (price + tpDist) : (price - tpDist);
   sl = NormalizeDouble(sl, digits);
   tp = NormalizeDouble(tp, digits);

   g_trade.SetExpertMagicNumber(InpMagic);
   g_trade.SetDeviationInPoints(InpDeviation);
   g_trade.SetTypeFillingBySymbol(symbol);

   bool ok = (dir > 0)
             ? g_trade.Buy(lots, symbol, 0.0, sl, tp, "carry_long")
             : g_trade.Sell(lots, symbol, 0.0, sl, tp, "carry_short");
   if(!ok)
      PrintFormat("[CARRY] Order fail %s dir=%d ret=%u", symbol, dir, g_trade.ResultRetcode());
   return ok;
}

//+------------------------------------------------------------------+
int OnInit()
{
   g_trade.SetExpertMagicNumber(InpMagic);
   g_trade.SetDeviationInPoints(InpDeviation);

   g_pairs[0].symbol = InpSymEURUSD;
   g_pairs[1].symbol = InpSymGBPUSD;
   g_pairs[2].symbol = InpSymUSDJPY;

   for(int i = 0; i < N_PAIRS; i++)
   {
      string sym = g_pairs[i].symbol;
      if(!SymbolSelect(sym, true))
      {
         PrintFormat("[CARRY] FATAL: SymbolSelect failed for %s", sym);
         return INIT_FAILED;
      }
      g_pairs[i].hATR = iATR(sym, PERIOD_D1, InpATRPeriod);
      if(g_pairs[i].hATR == INVALID_HANDLE)
      {
         PrintFormat("[CARRY] FATAL: iATR init failed for %s", sym);
         return INIT_FAILED;
      }
      g_pairs[i].lastBar = 0;
   }

   g_ratesLoaded = LoadRatesCsv();
   if(!g_ratesLoaded)
      return INIT_FAILED;

   PrintFormat("[CARRY] EA_CarryPublicRates v1.00 | magic=%d | minSpread=%.2f | SL=%.1fATR TP=%.1fATR | lagDays=%d",
               InpMagic, InpMinSpreadPct, InpSL_ATR, InpTP_ATR, InpRateLagDays);
   return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   for(int i = 0; i < N_PAIRS; i++)
   {
      if(g_pairs[i].hATR != INVALID_HANDLE)
         IndicatorRelease(g_pairs[i].hATR);
   }
}

//+------------------------------------------------------------------+
void OnTick()
{
   if(InpKillSwitch || !g_ratesLoaded)
      return;

   // Drive off chart D1 new-bar; still evaluate all three pairs on closed bar[1].
   datetime chartBar0 = iTime(_Symbol, PERIOD_D1, 0);
   if(chartBar0 == 0)
      return;
   static datetime s_lastChartBar = 0;
   if(chartBar0 == s_lastChartBar)
      return;
   s_lastChartBar = chartBar0;

   datetime bar1 = iTime(_Symbol, PERIOD_D1, 1);
   if(bar1 == 0)
      return;

   MqlDateTime bar1dt;
   TimeToStruct(bar1, bar1dt);

   // Friday flat: close all and skip new entries (weekend risk).
   if(InpFridayFlat && bar1dt.day_of_week == 5)
   {
      CloseAllMagic();
      return;
   }

   RateRow rates;
   if(!FindLaggedRates(bar1, rates))
   {
      PrintFormat("[CARRY] No lagged rate row for bar1=%s (lag=%d)",
                  TimeToString(bar1, TIME_DATE), InpRateLagDays);
      return;
   }

   double diffs[N_PAIRS];
   double atrs[N_PAIRS];
   for(int i = 0; i < N_PAIRS; i++)
   {
      string sym = g_pairs[i].symbol;
      diffs[i] = PairDifferential(sym, rates);
      double atrBuf[];
      if(CopyBuffer(g_pairs[i].hATR, 0, 1, 1, atrBuf) != 1 || atrBuf[0] <= 0.0)
      {
         PrintFormat("[CARRY] ATR missing for %s on bar1", sym);
         return;
      }
      atrs[i] = atrBuf[0];
   }

   int iMax = 0;
   int iMin = 0;
   for(int i = 1; i < N_PAIRS; i++)
   {
      if(diffs[i] > diffs[iMax]) iMax = i;
      if(diffs[i] < diffs[iMin]) iMin = i;
   }

   double spread = diffs[iMax] - diffs[iMin];
   if(spread < InpMinSpreadPct || iMax == iMin)
   {
      // Flat when rank edge is too thin.
      CloseAllMagic();
      return;
   }

   // Long highest carry differential, short lowest.
   for(int i = 0; i < N_PAIRS; i++)
   {
      string sym = g_pairs[i].symbol;
      if(i == iMax)
         OpenDirectional(sym, +1, atrs[i]);
      else if(i == iMin)
         OpenDirectional(sym, -1, atrs[i]);
      else
         CloseMagicPositions(sym);
   }
}
//+------------------------------------------------------------------+
