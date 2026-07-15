//+------------------------------------------------------------------+
//| EA_UsBillSlopeBasket.mq5 — lagged US bill-slope → USD basket     |
//| Chart host: EURUSD | Period: D1 | Magic: 880920                  |
//| Legs: EURUSD, GBPUSD, USDJPY (equal-weight USD direction)        |
//|                                                                   |
//| Hypothesis: HYP-SR-FX-USBILL-SLOPE-USD-BASKET-001                  |
//| Probe: V8_USBILL_SLOPE_USD_BASKET_V1 (PROBE_SURVIVOR)             |
//|                                                                   |
//| Closed-bar[1] only. CSV z already lagged (obs+1d).                |
//| Candidate: sign from bill-slope z (±0.75).                        |
//| Control: same |z| gate; direction from 20d USD spot proxy.        |
//| Stop 1.5×ATR14_D1; time-stop 5 D1 bars; Friday flat.              |
//+------------------------------------------------------------------+
#property copyright "SonicR / EA_UsBillSlopeBasket"
#property version   "1.00"
#property strict

#include <Trade\Trade.mqh>

input group "=== General ==="
input ulong    InpMagic           = 880920;
input int      InpDeviation       = 30;
input bool     InpKillSwitch      = false;

input group "=== Mode ==="
input int      InpMode            = 1;   // 1=candidate (bill z sign), 0=control (spot proxy sign)

input group "=== Universe ==="
input string   InpSymEURUSD       = "EURUSD";
input string   InpSymGBPUSD       = "GBPUSD";
input string   InpSymUSDJPY       = "USDJPY";

input group "=== Slope CSV ==="
input string   InpSlopeFile       = "usbill_slope_z_d1.csv";
input int      InpMaxGapDays      = 3;

input group "=== Signal (frozen) ==="
input double   InpZThresh         = 0.75;
input int      InpMomLookback     = 20;
input int      InpATRPeriod       = 14;
input double   InpSL_ATR          = 1.5;
input int      InpTimeStopBars    = 5;
input bool     InpFridayFlat      = true;

input group "=== Risk ==="
input double   InpRiskPct         = 0.50;  // risk per leg
input double   InpMaxLot          = 1.0;

#define MAX_Z_ROWS 12000
#define N_PAIRS 3

struct SlopeRow
{
   datetime available_at;  // already lagged obs+1d at 00:00
   double   z;
};

struct PairState
{
   string   symbol;
   int      hATR;
   int      leg_dir;       // +1 buy / -1 sell / 0 flat target
};

CTrade    g_trade;
SlopeRow  g_rows[];
int       g_rowCount = 0;
bool      g_loaded = false;
PairState g_pairs[N_PAIRS];
datetime  g_lastChartBar = 0;
datetime  g_entryBarTime = 0;
int       g_barsHeld = 0;
int       g_posUsdDir = 0;  // +1 USD strength / -1 weakness / 0 flat

//+------------------------------------------------------------------+
datetime DateOnly(const datetime t)
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
   dt.year = y; dt.mon = m; dt.day = d;
   dt.hour = 0; dt.min = 0; dt.sec = 0;
   return StructToTime(dt);
}

//+------------------------------------------------------------------+
bool OpenCsv(const string name, int &handle, bool &usedCommon)
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
bool LoadSlopeCsv()
{
   int handle = INVALID_HANDLE;
   bool usedCommon = false;
   if(!OpenCsv(InpSlopeFile, handle, usedCommon))
   {
      PrintFormat("[USBILL] FATAL: CSV missing '%s' (Common\\Files then MQL5\\Files). err=%d",
                  InpSlopeFile, GetLastError());
      return false;
   }

   // Header: available_at,obs_date,slope,z,abs_z_gate
   if(!FileIsEnding(handle))
   {
      FileReadString(handle);
      FileReadString(handle);
      FileReadString(handle);
      FileReadString(handle);
      FileReadString(handle);
   }

   ArrayResize(g_rows, 0, 1024);
   g_rowCount = 0;
   while(!FileIsEnding(handle) && g_rowCount < MAX_Z_ROWS)
   {
      string availS = FileReadString(handle);
      if(StringLen(availS) == 0)
         break;
      string obsS = FileReadString(handle);
      string slopeS = FileReadString(handle);
      string zS = FileReadString(handle);
      string gateS = FileReadString(handle);
      datetime avail = ParseYmd(availS);
      if(avail == 0)
         continue;
      double z = StringToDouble(zS);
      if(!MathIsValidNumber(z))
         continue;

      int n = g_rowCount;
      ArrayResize(g_rows, n + 1, 1024);
      g_rows[n].available_at = avail;
      g_rows[n].z = z;
      g_rowCount++;
      // silence unused
      if(StringLen(obsS) == 0 && StringLen(slopeS) == 0 && StringLen(gateS) == 0) { }
   }
   FileClose(handle);

   if(g_rowCount < 40)
   {
      PrintFormat("[USBILL] FATAL: only %d z rows", g_rowCount);
      return false;
   }

   // Ascending sort by available_at
   for(int i = 1; i < g_rowCount; i++)
   {
      SlopeRow key = g_rows[i];
      int j = i - 1;
      while(j >= 0 && g_rows[j].available_at > key.available_at)
      {
         g_rows[j + 1] = g_rows[j];
         j--;
      }
      g_rows[j + 1] = key;
   }

   PrintFormat("[USBILL] Loaded %d z rows from '%s' (%s)",
               g_rowCount, InpSlopeFile, usedCommon ? "FILE_COMMON" : "terminal Files");
   return true;
}

//+------------------------------------------------------------------+
bool FindZAsOf(const datetime bar1Day, double &outZ)
{
   datetime cutoff = DateOnly(bar1Day);
   int lo = 0;
   int hi = g_rowCount - 1;
   int best = -1;
   while(lo <= hi)
   {
      int mid = (lo + hi) / 2;
      if(g_rows[mid].available_at <= cutoff)
      {
         best = mid;
         lo = mid + 1;
      }
      else
         hi = mid - 1;
   }
   if(best < 0)
      return false;
   int gapDays = (int)((cutoff - g_rows[best].available_at) / 86400);
   if(gapDays > InpMaxGapDays)
      return false;
   outZ = g_rows[best].z;
   return true;
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
         PrintFormat("[USBILL] Close fail %s ticket=%s err=%d",
                     symbol, IntegerToString((long)ticket), GetLastError());
   }
}

//+------------------------------------------------------------------+
void CloseAllMagic()
{
   for(int p = 0; p < N_PAIRS; p++)
      CloseMagicPositions(g_pairs[p].symbol);
   g_posUsdDir = 0;
   g_entryBarTime = 0;
   g_barsHeld = 0;
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
   if(slDist < 10.0 * point)
      slDist = 10.0 * point;

   double lots = CalcLots(symbol, slDist);
   if(lots <= 0.0)
   {
      PrintFormat("[USBILL] Skip %s: lot=0 atr=%.5f", symbol, atr);
      return false;
   }

   double ask = SymbolInfoDouble(symbol, SYMBOL_ASK);
   double bid = SymbolInfoDouble(symbol, SYMBOL_BID);
   double price = (dir > 0) ? ask : bid;
   double sl = (dir > 0) ? (price - slDist) : (price + slDist);
   sl = NormalizeDouble(sl, digits);

   g_trade.SetExpertMagicNumber((long)InpMagic);
   g_trade.SetDeviationInPoints(InpDeviation);
   g_trade.SetTypeFillingBySymbol(symbol);

   bool ok = (dir > 0)
             ? g_trade.Buy(lots, symbol, 0.0, sl, 0.0, "usbill_long")
             : g_trade.Sell(lots, symbol, 0.0, sl, 0.0, "usbill_short");
   if(!ok)
      PrintFormat("[USBILL] Order fail %s dir=%d ret=%u", symbol, dir, g_trade.ResultRetcode());
   return ok;
}

//+------------------------------------------------------------------+
int UsdProxySign(const datetime bar1)
{
   // USD proxy = (-ret_EUR - ret_GBP + ret_JPY) / 3 over InpMomLookback closed D1.
   // Uses closed bars ending at shift=1 (bar1).
   double rets[3];
   string syms[3];
   double signs[3];
   syms[0] = InpSymEURUSD; signs[0] = -1.0;
   syms[1] = InpSymGBPUSD; signs[1] = -1.0;
   syms[2] = InpSymUSDJPY; signs[2] = 1.0;

   for(int i = 0; i < 3; i++)
   {
      int shift1 = iBarShift(syms[i], PERIOD_D1, bar1, true);
      if(shift1 < 0)
         return 0;
      int shift0 = shift1 + InpMomLookback;
      if(Bars(syms[i], PERIOD_D1) <= shift0)
         return 0;
      double c1 = iClose(syms[i], PERIOD_D1, shift1);
      double c0 = iClose(syms[i], PERIOD_D1, shift0);
      if(c0 <= 0.0 || c1 <= 0.0)
         return 0;
      rets[i] = signs[i] * ((c1 / c0) - 1.0);
   }
   double proxy = (rets[0] + rets[1] + rets[2]) / 3.0;
   if(proxy > 0.0) return 1;
   if(proxy < 0.0) return -1;
   return 0;
}

//+------------------------------------------------------------------+
int ResolveUsdDirection(const datetime bar1, const double z)
{
   if(MathAbs(z) < InpZThresh)
      return 0;

   if(InpMode == 0)
   {
      // Control: |z| gate only; direction from spot proxy.
      return UsdProxySign(bar1);
   }

   // Candidate: sign from bill-slope z.
   if(z >= InpZThresh) return 1;
   if(z <= -InpZThresh) return -1;
   return 0;
}

//+------------------------------------------------------------------+
void ApplyLegDirections(const int usdDir)
{
   // USD strength (+1): short EURUSD, short GBPUSD, long USDJPY
   if(usdDir > 0)
   {
      g_pairs[0].leg_dir = -1;
      g_pairs[1].leg_dir = -1;
      g_pairs[2].leg_dir = 1;
   }
   else if(usdDir < 0)
   {
      g_pairs[0].leg_dir = 1;
      g_pairs[1].leg_dir = 1;
      g_pairs[2].leg_dir = -1;
   }
   else
   {
      g_pairs[0].leg_dir = 0;
      g_pairs[1].leg_dir = 0;
      g_pairs[2].leg_dir = 0;
   }
}

//+------------------------------------------------------------------+
bool AnyLegOpen()
{
   for(int i = 0; i < N_PAIRS; i++)
   {
      if(CountMagicPositions(g_pairs[i].symbol) > 0)
         return true;
   }
   return false;
}

//+------------------------------------------------------------------+
int OnInit()
{
   g_trade.SetExpertMagicNumber((long)InpMagic);
   g_trade.SetDeviationInPoints(InpDeviation);

   g_pairs[0].symbol = InpSymEURUSD;
   g_pairs[1].symbol = InpSymGBPUSD;
   g_pairs[2].symbol = InpSymUSDJPY;

   for(int i = 0; i < N_PAIRS; i++)
   {
      string sym = g_pairs[i].symbol;
      if(!SymbolSelect(sym, true))
      {
         PrintFormat("[USBILL] FATAL: SymbolSelect failed %s", sym);
         return INIT_FAILED;
      }
      g_pairs[i].hATR = iATR(sym, PERIOD_D1, InpATRPeriod);
      if(g_pairs[i].hATR == INVALID_HANDLE)
      {
         PrintFormat("[USBILL] FATAL: iATR failed %s", sym);
         return INIT_FAILED;
      }
      g_pairs[i].leg_dir = 0;
   }

   g_loaded = LoadSlopeCsv();
   if(!g_loaded)
      return INIT_FAILED;

   PrintFormat("[USBILL] HYP-SR-FX-USBILL-SLOPE-USD-BASKET-001 | mode=%s | z=%.2f | SL=%.1fATR | tstop=%d | FridayFlat=%d",
               (InpMode == 0 ? "CONTROL" : "CANDIDATE"),
               InpZThresh, InpSL_ATR, InpTimeStopBars, (int)InpFridayFlat);
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
   if(InpKillSwitch || !g_loaded)
      return;

   // Drive off host chart D1 new-bar; decisions use closed bar[1] only.
   datetime chartBar0 = iTime(_Symbol, PERIOD_D1, 0);
   if(chartBar0 == 0)
      return;
   if(chartBar0 == g_lastChartBar)
      return;
   g_lastChartBar = chartBar0;

   datetime bar1 = iTime(_Symbol, PERIOD_D1, 1);
   if(bar1 == 0)
      return;

   MqlDateTime bar1dt;
   TimeToStruct(bar1, bar1dt);

   // Time-stop: count completed D1 bars since entry.
   if(g_posUsdDir != 0 && AnyLegOpen())
   {
      g_barsHeld++;
      if(g_barsHeld >= InpTimeStopBars)
      {
         CloseAllMagic();
         PrintFormat("[USBILL] Time-stop after %d bars", InpTimeStopBars);
      }
   }

   // Friday flatten (weekend risk) — no new entries.
   if(InpFridayFlat && bar1dt.day_of_week == 5)
   {
      if(AnyLegOpen())
         CloseAllMagic();
      return;
   }

   double z = 0.0;
   if(!FindZAsOf(bar1, z))
      return;

   int usdDir = ResolveUsdDirection(bar1, z);

   if(usdDir == 0)
   {
      if(AnyLegOpen())
         CloseAllMagic();
      return;
   }

   if(usdDir == g_posUsdDir && AnyLegOpen())
      return;  // hold same basket

   // Rebalance / open
   ApplyLegDirections(usdDir);

   double atrs[N_PAIRS];
   for(int i = 0; i < N_PAIRS; i++)
   {
      double atrBuf[];
      // ATR on closed bar[1] of each leg (aligned by time via iBarShift would be
      // ideal; use shift=1 on each symbol's D1 — same calendar day for majors).
      if(CopyBuffer(g_pairs[i].hATR, 0, 1, 1, atrBuf) != 1 || atrBuf[0] <= 0.0)
      {
         PrintFormat("[USBILL] ATR missing %s", g_pairs[i].symbol);
         return;
      }
      atrs[i] = atrBuf[0];
   }

   // Close then open all legs for clean basket state.
   for(int i = 0; i < N_PAIRS; i++)
      CloseMagicPositions(g_pairs[i].symbol);

   bool anyOk = false;
   for(int i = 0; i < N_PAIRS; i++)
   {
      if(OpenDirectional(g_pairs[i].symbol, g_pairs[i].leg_dir, atrs[i]))
         anyOk = true;
   }

   if(anyOk)
   {
      g_posUsdDir = usdDir;
      g_entryBarTime = bar1;
      g_barsHeld = 0;
   }
   else
   {
      CloseAllMagic();
   }
}
//+------------------------------------------------------------------+
