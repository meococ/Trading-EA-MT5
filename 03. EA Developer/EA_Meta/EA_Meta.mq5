//+------------------------------------------------------------------+
//| EA_Meta.mq5 — Multi-Strategy Portfolio EA                         |
//| Cobra (XAUUSD+) + ITSM (USDJPY+) + LondonNY (USDJPY+)          |
//| Single-chart deployment, unified risk, prop-firm compliant        |
//| Max & Ngai Meo Coc | 2026-04-11 | v1.0                           |
//+------------------------------------------------------------------+
#property copyright "Max & Ngai Meo Coc"
#property version   "1.00"
#property strict

#include <Trade\Trade.mqh>
#include <Trade\PositionInfo.mqh>
#include <Trade\SymbolInfo.mqh>
#include <HolidayCalendar.mqh>

//+------------------------------------------------------------------+
//| INPUTS — GLOBAL                                                    |
//+------------------------------------------------------------------+
input group "=== GLOBAL RISK ==="
input double InpGlobal_MaxDDPct   = 3.0;     // Combined daily DD kill (%)
input int    InpGlobal_MaxUJPos   = 1;        // Max concurrent USDJPY+ positions (anti-overlap)
input int    InpGlobal_MaxRetries = 3;        // Order retry count
input int    InpGlobal_MaxSlip    = 30;       // Max slippage (points)

//+------------------------------------------------------------------+
//| INPUTS — COBRA (XAUUSD+)                                          |
//+------------------------------------------------------------------+
input group "=== COBRA — XAUUSD+ Level KZ ==="
input bool   InpCBR_Enabled     = true;
input string InpCBR_Symbol      = "XAUUSD+";
input double InpCBR_RiskPct     = 0.10;
input double InpCBR_MaxLot      = 10.0;
input int    InpCBR_Magic       = 300001;
input int    InpCBR_KzStart     = 16;         // NYC KZ start hour
input int    InpCBR_KzEnd       = 17;         // NYC KZ end hour
input double InpCBR_RR          = 1.8;        // Risk:Reward
input bool   InpCBR_SkipWed     = true;
input bool   InpCBR_SkipThu     = false;
input int    InpCBR_MaxPerDay   = 6;
input int    InpCBR_MaxPerKZ    = 2;
input int    InpCBR_MaxOpen     = 3;

//+------------------------------------------------------------------+
//| INPUTS — ITSM (USDJPY+)                                           |
//+------------------------------------------------------------------+
input group "=== ITSM — USDJPY+ EMA Pullback ==="
input bool   InpITSM_Enabled    = true;
input string InpITSM_Symbol     = "USDJPY+";
input double InpITSM_RiskPct    = 0.70;
input double InpITSM_MaxLot     = 10.0;
input int    InpITSM_Magic      = 300002;
input int    InpITSM_KzStart    = 15;         // NY KZ start
input int    InpITSM_KzEnd      = 17;         // NY KZ end
input double InpITSM_RR         = 1.5;
input bool   InpITSM_SkipTue    = true;       // E8: skip Tue
input bool   InpITSM_SkipFri    = true;       // E8: skip Fri

//+------------------------------------------------------------------+
//| INPUTS — LONDONNNY (USDJPY+)                                       |
//+------------------------------------------------------------------+
input group "=== LONDNNY — USDJPY+ LDN→NY Momentum ==="
input bool   InpLDNY_Enabled    = true;
input string InpLDNY_Symbol     = "USDJPY+";
input double InpLDNY_RiskPct    = 0.70;
input double InpLDNY_MaxLot     = 10.0;
input int    InpLDNY_Magic      = 300003;
input double InpLDNY_RR         = 2.0;
input bool   InpLDNY_SkipMon    = true;       // E8: skip Mon
input bool   InpLDNY_SkipWed    = true;       // E8: skip Wed

//+------------------------------------------------------------------+
//| BAKED CONSTANTS (validated — do NOT change)                        |
//+------------------------------------------------------------------+
// Cobra
#define CBR_ATR_PERIOD     14
#define CBR_BB_PERIOD      20
#define CBR_BB_DEV         2.0
#define CBR_EMA_FAST       21
#define CBR_EMA_SLOW       55
#define CBR_ASIAN_START    0
#define CBR_ASIAN_END      7
#define CBR_BODY_RATIO     0.55
#define CBR_CLOSE_LOC      0.65
#define CBR_BAR_MIN_ATR    0.40
#define CBR_BAR_MAX_ATR    3.00
#define CBR_LEVEL_ZONE     150   // points tolerance
#define CBR_SL_MIN         400   // points min SL
#define CBR_SL_MAX         5000  // points max SL
#define CBR_SL_ATR_MULT    1.5
#define CBR_BE_TRIGGER     1.0   // R for break-even

// ITSM
#define ITSM_EMA_F1        5
#define ITSM_EMA_F2        13
#define ITSM_EMA_ZU        34
#define ITSM_EMA_ZL        89
#define ITSM_ATR_PERIOD    14
#define ITSM_LOOKBACK      5
#define ITSM_BODY_ATR      0.3
#define ITSM_SL_ATR_MULT   0.5
#define ITSM_EXIT_HOUR     20

// LondonNY
#define LDNY_LDN_START_H   9
#define LDNY_LDN_MEASURE_H 12
#define LDNY_NY_START_H    15
#define LDNY_NY_END_H      18
#define LDNY_ATR_PERIOD    14
#define LDNY_TREND_ATR     0.50
#define LDNY_PB_MIN_ATR    0.15
#define LDNY_PB_MAX_ATR    0.60
#define LDNY_PB_LOOKBACK   3
#define LDNY_SL_ATR_MULT   0.5
#define LDNY_EXIT_HOUR     20

//+------------------------------------------------------------------+
//| GLOBALS                                                            |
//+------------------------------------------------------------------+
CTrade         g_trade;
CPositionInfo  g_pos;

// Indicator handles — COBRA (XAUUSD+)
int g_cbr_atr, g_cbr_bb, g_cbr_emaF, g_cbr_emaS;
// Indicator handles — ITSM (USDJPY+)
int g_itsm_atr, g_itsm_f1, g_itsm_f2, g_itsm_zu, g_itsm_zl;
// Indicator handles — LondonNY (USDJPY+)
int g_ldny_atrD1, g_ldny_ema;

// Unified state
double g_dayStartEquity;
datetime g_lastDayReset;

// Cobra state
double g_cbr_asianHi, g_cbr_asianLo, g_cbr_pdH, g_cbr_pdL;
bool   g_cbr_asianBuilt;
int    g_cbr_todayTrades, g_cbr_kzTrades;
datetime g_cbr_lastBar, g_cbr_lastDay;

// ITSM state
datetime g_itsm_lastTradeDate, g_itsm_lastBar;

// LondonNY state
double   g_ldny_londonOpen, g_ldny_direction;
bool     g_ldny_biasSet, g_ldny_traded;
datetime g_ldny_lastBar, g_ldny_lastDay;

//+------------------------------------------------------------------+
//| INITIALIZATION                                                     |
//+------------------------------------------------------------------+
int OnInit()
{
   g_trade.SetDeviationInPoints(InpGlobal_MaxSlip);
   g_dayStartEquity = AccountInfoDouble(ACCOUNT_EQUITY);
   g_lastDayReset = 0;

   // --- COBRA handles ---
   if(InpCBR_Enabled)
   {
      g_cbr_atr  = iATR(InpCBR_Symbol, PERIOD_M15, CBR_ATR_PERIOD);
      g_cbr_bb   = iBands(InpCBR_Symbol, PERIOD_M15, CBR_BB_PERIOD, 0, CBR_BB_DEV, PRICE_CLOSE);
      g_cbr_emaF = iMA(InpCBR_Symbol, PERIOD_H1, CBR_EMA_FAST, 0, MODE_EMA, PRICE_CLOSE);
      g_cbr_emaS = iMA(InpCBR_Symbol, PERIOD_H1, CBR_EMA_SLOW, 0, MODE_EMA, PRICE_CLOSE);
      if(g_cbr_atr==INVALID_HANDLE || g_cbr_bb==INVALID_HANDLE ||
         g_cbr_emaF==INVALID_HANDLE || g_cbr_emaS==INVALID_HANDLE)
      { Print("COBRA: indicator init FAILED"); return INIT_FAILED; }
      g_cbr_asianBuilt = false;
      g_cbr_todayTrades = 0; g_cbr_kzTrades = 0;
      g_cbr_lastBar = 0; g_cbr_lastDay = 0;
   }

   // --- ITSM handles ---
   if(InpITSM_Enabled)
   {
      g_itsm_atr = iATR(InpITSM_Symbol, PERIOD_M15, ITSM_ATR_PERIOD);
      g_itsm_f1  = iMA(InpITSM_Symbol, PERIOD_M15, ITSM_EMA_F1, 0, MODE_EMA, PRICE_CLOSE);
      g_itsm_f2  = iMA(InpITSM_Symbol, PERIOD_M15, ITSM_EMA_F2, 0, MODE_EMA, PRICE_CLOSE);
      g_itsm_zu  = iMA(InpITSM_Symbol, PERIOD_M15, ITSM_EMA_ZU, 0, MODE_EMA, PRICE_CLOSE);
      g_itsm_zl  = iMA(InpITSM_Symbol, PERIOD_M15, ITSM_EMA_ZL, 0, MODE_EMA, PRICE_CLOSE);
      if(g_itsm_atr==INVALID_HANDLE || g_itsm_f1==INVALID_HANDLE ||
         g_itsm_f2==INVALID_HANDLE || g_itsm_zu==INVALID_HANDLE ||
         g_itsm_zl==INVALID_HANDLE)
      { Print("ITSM: indicator init FAILED"); return INIT_FAILED; }
      g_itsm_lastTradeDate = 0; g_itsm_lastBar = 0;
   }

   // --- LONDONNNY handles ---
   if(InpLDNY_Enabled)
   {
      g_ldny_atrD1 = iATR(InpLDNY_Symbol, PERIOD_D1, LDNY_ATR_PERIOD);
      g_ldny_ema   = iMA(InpLDNY_Symbol, PERIOD_M15, 50, 0, MODE_EMA, PRICE_CLOSE);
      if(g_ldny_atrD1==INVALID_HANDLE || g_ldny_ema==INVALID_HANDLE)
      { Print("LDNY: indicator init FAILED"); return INIT_FAILED; }
      g_ldny_londonOpen = 0; g_ldny_direction = 0;
      g_ldny_biasSet = false; g_ldny_traded = false;
      g_ldny_lastBar = 0; g_ldny_lastDay = 0;
   }

   Print("EA_Meta v1.0 | CBR=", InpCBR_Enabled, " ITSM=", InpITSM_Enabled,
         " LDNY=", InpLDNY_Enabled);
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   if(InpCBR_Enabled)
   { IndicatorRelease(g_cbr_atr); IndicatorRelease(g_cbr_bb);
     IndicatorRelease(g_cbr_emaF); IndicatorRelease(g_cbr_emaS); }
   if(InpITSM_Enabled)
   { IndicatorRelease(g_itsm_atr); IndicatorRelease(g_itsm_f1);
     IndicatorRelease(g_itsm_f2); IndicatorRelease(g_itsm_zu); IndicatorRelease(g_itsm_zl); }
   if(InpLDNY_Enabled)
   { IndicatorRelease(g_ldny_atrD1); IndicatorRelease(g_ldny_ema); }
}

//+------------------------------------------------------------------+
//| SHARED HELPERS                                                     |
//+------------------------------------------------------------------+
int GetHour(string sym)
{
   datetime t = (sym == _Symbol) ? TimeCurrent() :
                iTime(sym, PERIOD_M15, 0) + PeriodSeconds(PERIOD_M15);
   MqlDateTime dt; TimeToStruct(t, dt);
   return dt.hour;
}

int GetDOW()
{
   MqlDateTime dt; TimeToStruct(TimeCurrent(), dt);
   return dt.day_of_week;
}

datetime GetToday()
{
   MqlDateTime dt; TimeToStruct(TimeCurrent(), dt);
   return StringToTime(StringFormat("%04d.%02d.%02d", dt.year, dt.mon, dt.day));
}

int CountPos(int magic, string sym)
{
   int c = 0;
   for(int i = PositionsTotal()-1; i >= 0; i--)
   {
      if(g_pos.SelectByIndex(i) && g_pos.Magic() == magic && g_pos.Symbol() == sym) c++;
   }
   return c;
}

int CountPosSymbol(string sym)
{
   int c = 0;
   for(int i = PositionsTotal()-1; i >= 0; i--)
   {
      if(g_pos.SelectByIndex(i) && g_pos.Symbol() == sym) c++;
   }
   return c;
}

void CloseAll(int magic, string sym, string reason)
{
   for(int i = PositionsTotal()-1; i >= 0; i--)
   {
      if(g_pos.SelectByIndex(i) && g_pos.Magic() == magic && g_pos.Symbol() == sym)
      {
         g_trade.SetExpertMagicNumber(magic);
         g_trade.PositionClose(g_pos.Ticket());
         Print("META CLOSE [", reason, "] ", sym, " ticket=", g_pos.Ticket());
      }
   }
}

double CalcLot(string sym, double riskPct, double maxLot, double slPoints)
{
   if(slPoints <= 0) return SymbolInfoDouble(sym, SYMBOL_VOLUME_MIN);
   double riskMoney = AccountInfoDouble(ACCOUNT_BALANCE) * riskPct / 100.0;
   double tickVal  = SymbolInfoDouble(sym, SYMBOL_TRADE_TICK_VALUE);
   double tickSize = SymbolInfoDouble(sym, SYMBOL_TRADE_TICK_SIZE);
   if(tickVal <= 0 || tickSize <= 0) return SymbolInfoDouble(sym, SYMBOL_VOLUME_MIN);
   double lotPerPoint = tickVal / tickSize;
   if(lotPerPoint <= 0) return SymbolInfoDouble(sym, SYMBOL_VOLUME_MIN);
   double lots = riskMoney / (slPoints * lotPerPoint);
   lots = MathMin(lots, maxLot);
   double minLot  = SymbolInfoDouble(sym, SYMBOL_VOLUME_MIN);
   double lotStep = SymbolInfoDouble(sym, SYMBOL_VOLUME_STEP);
   lots = MathMax(lots, minLot);
   lots = NormalizeDouble(MathFloor(lots / lotStep) * lotStep, 2);
   return lots;
}

bool CheckDDKill()
{
   datetime today = GetToday();
   if(today != g_lastDayReset)
   {
      g_lastDayReset = today;
      g_dayStartEquity = AccountInfoDouble(ACCOUNT_EQUITY);
   }
   double eq = AccountInfoDouble(ACCOUNT_EQUITY);
   if(g_dayStartEquity > 0 && (g_dayStartEquity - eq) / g_dayStartEquity * 100.0 >= InpGlobal_MaxDDPct)
      return true;
   return false;
}

bool SendOrder(string sym, int magic, bool isBuy, double lots, double sl, double tp, string comment)
{
   g_trade.SetExpertMagicNumber(magic);
   double price = isBuy ? SymbolInfoDouble(sym, SYMBOL_ASK) : SymbolInfoDouble(sym, SYMBOL_BID);
   bool ok = false;
   for(int att = 1; att <= InpGlobal_MaxRetries; att++)
   {
      if(isBuy) ok = g_trade.Buy(lots, sym, price, sl, tp, comment);
      else      ok = g_trade.Sell(lots, sym, price, sl, tp, comment);
      if(ok && g_trade.ResultRetcode() == 10009) break;
      if(att < InpGlobal_MaxRetries) Sleep(200 * att);
      price = isBuy ? SymbolInfoDouble(sym, SYMBOL_ASK) : SymbolInfoDouble(sym, SYMBOL_BID);
   }
   return ok;
}

void ManageBE(int magic, string sym, double beR)
{
   double pt = SymbolInfoDouble(sym, SYMBOL_POINT);
   for(int i = PositionsTotal()-1; i >= 0; i--)
   {
      if(!g_pos.SelectByIndex(i) || g_pos.Magic() != magic || g_pos.Symbol() != sym) continue;
      double open = g_pos.PriceOpen(), sl = g_pos.StopLoss(), tp = g_pos.TakeProfit();
      double risk = MathAbs(open - sl);
      if(risk <= 0) continue;
      double cur = g_pos.PriceCurrent();
      bool isBuy = (g_pos.PositionType() == POSITION_TYPE_BUY);

      if(isBuy && sl < open - pt)
      {
         if(cur - open >= risk * beR)
         {
            g_trade.SetExpertMagicNumber(magic);
            g_trade.PositionModify(g_pos.Ticket(), open + pt, tp);
         }
      }
      else if(!isBuy && (sl > open + pt || sl == 0))
      {
         if(open - cur >= risk * beR)
         {
            g_trade.SetExpertMagicNumber(magic);
            g_trade.PositionModify(g_pos.Ticket(), open - pt, tp);
         }
      }
   }
}

double Buf1(int handle, int buf, int shift)
{
   double v[]; if(CopyBuffer(handle, buf, shift, 1, v) < 1) return 0; return v[0];
}

//+------------------------------------------------------------------+
//| COBRA MODULE — Level KZ Scalper (XAUUSD+)                        |
//+------------------------------------------------------------------+
void CBR_DayReset(int h)
{
   datetime today = GetToday();
   if(today != g_cbr_lastDay)
   {
      g_cbr_lastDay = today;
      g_cbr_todayTrades = 0; g_cbr_kzTrades = 0;
      g_cbr_asianBuilt = false;
      g_cbr_asianHi = -99999; g_cbr_asianLo = 99999;
      // Capture prev day H/L
      g_cbr_pdH = iHigh(InpCBR_Symbol, PERIOD_D1, 1);
      g_cbr_pdL = iLow(InpCBR_Symbol, PERIOD_D1, 1);
   }
   // KZ reset: beginning of KZ
   if(h == InpCBR_KzStart) g_cbr_kzTrades = 0;
}

void CBR_BuildAsian(int h)
{
   if(g_cbr_asianBuilt) return;
   if(h >= CBR_ASIAN_START && h < CBR_ASIAN_END)
   {
      double hi = iHigh(InpCBR_Symbol, PERIOD_M15, 1);
      double lo = iLow(InpCBR_Symbol, PERIOD_M15, 1);
      if(hi > g_cbr_asianHi) g_cbr_asianHi = hi;
      if(lo < g_cbr_asianLo) g_cbr_asianLo = lo;
   }
   if(h >= CBR_ASIAN_END) g_cbr_asianBuilt = true;
}

int CBR_CheckSignal()
{
   // Returns: +1 BUY, -1 SELL, 0 no signal
   string sym = InpCBR_Symbol;
   double pt = SymbolInfoDouble(sym, SYMBOL_POINT);
   double close1 = iClose(sym, PERIOD_M15, 1);
   double open1  = iOpen(sym, PERIOD_M15, 1);
   double high1  = iHigh(sym, PERIOD_M15, 1);
   double low1   = iLow(sym, PERIOD_M15, 1);
   double atr    = Buf1(g_cbr_atr, 0, 1);
   if(atr <= 0) return 0;

   double range = high1 - low1;
   if(range <= 0) return 0;
   double body = MathAbs(close1 - open1);
   double bodyRatio = body / range;
   double closeLoc = (close1 > open1) ? (close1 - low1) / range : (high1 - close1) / range;

   // Momentum bar filter
   if(bodyRatio < CBR_BODY_RATIO) return 0;
   if(closeLoc < CBR_CLOSE_LOC) return 0;
   if(range < atr * CBR_BAR_MIN_ATR || range > atr * CBR_BAR_MAX_ATR) return 0;

   // Check each level: AsianHi, AsianLo, PDH, PDL
   double levels[4];
   levels[0] = g_cbr_asianHi; levels[1] = g_cbr_asianLo;
   levels[2] = g_cbr_pdH;     levels[3] = g_cbr_pdL;

   double zoneSize = CBR_LEVEL_ZONE * pt;

   for(int lv = 0; lv < 4; lv++)
   {
      double level = levels[lv];
      if(level <= 0) continue;

      // BREAKOUT above level
      if(close1 > open1 && close1 > level + zoneSize && open1 < level + zoneSize)
         return 1;
      // BREAKOUT below level
      if(close1 < open1 && close1 < level - zoneSize && open1 > level - zoneSize)
         return -1;
      // BOUNCE off level (wick into zone, close back out)
      if(close1 > open1 && low1 < level + zoneSize && low1 > level - zoneSize && close1 > level + zoneSize)
         return 1;
      if(close1 < open1 && high1 > level - zoneSize && high1 < level + zoneSize && close1 < level - zoneSize)
         return -1;
   }
   return 0;
}

void CBR_OnTick()
{
   if(!InpCBR_Enabled) return;
   string sym = InpCBR_Symbol;

   // New bar check
   datetime bar = iTime(sym, PERIOD_M15, 0);
   if(bar == g_cbr_lastBar) return;
   g_cbr_lastBar = bar;

   int h = GetHour(sym);
   int dow = GetDOW();

   CBR_DayReset(h);
   CBR_BuildAsian(h);

   // Manage BE on existing positions
   ManageBE(InpCBR_Magic, sym, CBR_BE_TRIGGER);

   // Day filter
   if(dow == 0 || dow == 6) return;
   if(InpCBR_SkipWed && dow == 3) return;
   if(InpCBR_SkipThu && dow == 4) return;

   // Friday flatten
   if(dow == 5 && h >= 17) { CloseAll(InpCBR_Magic, sym, "FriFlatten"); return; }

   // Kill zone check
   if(h < InpCBR_KzStart || h >= InpCBR_KzEnd) return;
   if(!g_cbr_asianBuilt) return;

   // Capacity
   if(g_cbr_todayTrades >= InpCBR_MaxPerDay) return;
   if(g_cbr_kzTrades >= InpCBR_MaxPerKZ) return;
   if(CountPos(InpCBR_Magic, sym) >= InpCBR_MaxOpen) return;

   int sig = CBR_CheckSignal();
   if(sig == 0) return;

   // Calculate SL/TP
   double pt = SymbolInfoDouble(sym, SYMBOL_POINT);
   double atr = Buf1(g_cbr_atr, 0, 1);
   double price, sl, tp;
   bool isBuy = (sig > 0);

   if(isBuy)
   {
      price = SymbolInfoDouble(sym, SYMBOL_ASK);
      sl = price - atr * CBR_SL_ATR_MULT;
      double slDist = (price - sl) / pt;
      if(slDist < CBR_SL_MIN) sl = price - CBR_SL_MIN * pt;
      if(slDist > CBR_SL_MAX) sl = price - CBR_SL_MAX * pt;
      tp = price + MathAbs(price - sl) * InpCBR_RR;
   }
   else
   {
      price = SymbolInfoDouble(sym, SYMBOL_BID);
      sl = price + atr * CBR_SL_ATR_MULT;
      double slDist = (sl - price) / pt;
      if(slDist < CBR_SL_MIN) sl = price + CBR_SL_MIN * pt;
      if(slDist > CBR_SL_MAX) sl = price + CBR_SL_MAX * pt;
      tp = price - MathAbs(sl - price) * InpCBR_RR;
   }

   double slPts = MathAbs(price - sl);
   double lots = CalcLot(sym, InpCBR_RiskPct, InpCBR_MaxLot, slPts);
   string cmt = "META_CBR";

   if(SendOrder(sym, InpCBR_Magic, isBuy, lots, sl, tp, cmt))
   {
      g_cbr_todayTrades++; g_cbr_kzTrades++;
      Print("COBRA ", (isBuy?"BUY":"SELL"), " lots=", lots, " sl=", sl, " tp=", tp);
   }
}

//+------------------------------------------------------------------+
//| ITSM MODULE — Sonic R EMA Pullback (USDJPY+)                     |
//+------------------------------------------------------------------+
int ITSM_GetTrend()
{
   double f1 = Buf1(g_itsm_f1, 0, 1), f2 = Buf1(g_itsm_f2, 0, 1);
   double zu = Buf1(g_itsm_zu, 0, 1), zl = Buf1(g_itsm_zl, 0, 1);
   double zTop = MathMax(zu, zl), zBot = MathMin(zu, zl);

   if(f1 > zTop && f2 > zTop && zu > zl) return 1;   // Bullish
   if(f1 < zBot && f2 < zBot && zu < zl) return -1;  // Bearish
   return 0;
}

int ITSM_CheckSignal()
{
   string sym = InpITSM_Symbol;
   int trend = ITSM_GetTrend();
   if(trend == 0) return 0;

   double atr = Buf1(g_itsm_atr, 0, 1);
   if(atr <= 0) return 0;
   double zu = Buf1(g_itsm_zu, 0, 1), zl = Buf1(g_itsm_zl, 0, 1);
   double zTop = MathMax(zu, zl), zBot = MathMin(zu, zl);

   double close1 = iClose(sym, PERIOD_M15, 1);
   double open1  = iOpen(sym, PERIOD_M15, 1);
   double body   = MathAbs(close1 - open1);

   // Body quality filter
   if(body < atr * ITSM_BODY_ATR) return 0;

   // Bounce direction
   if(trend > 0 && close1 <= open1) return 0;  // Need bullish bar
   if(trend < 0 && close1 >= open1) return 0;  // Need bearish bar

   // Bar must close above zone (buy) or below zone (sell)
   if(trend > 0 && close1 < zTop) return 0;
   if(trend < 0 && close1 > zBot) return 0;

   // Check zone touch in lookback
   bool touched = false;
   for(int i = 1; i <= ITSM_LOOKBACK; i++)
   {
      double lo = iLow(sym, PERIOD_M15, i);
      double hi = iHigh(sym, PERIOD_M15, i);
      if(trend > 0 && lo <= zTop) touched = true;
      if(trend < 0 && hi >= zBot) touched = true;
   }
   if(!touched) return 0;

   return trend;
}

void ITSM_OnTick()
{
   if(!InpITSM_Enabled) return;
   string sym = InpITSM_Symbol;

   datetime bar = iTime(sym, PERIOD_M15, 0);
   if(bar == g_itsm_lastBar) return;
   g_itsm_lastBar = bar;

   int h = GetHour(sym);
   int dow = GetDOW();

   // Time exit
   if(CountPos(InpITSM_Magic, sym) > 0 && h >= ITSM_EXIT_HOUR)
   {
      CloseAll(InpITSM_Magic, sym, "TimeExit");
      return;
   }

   // Day filter
   if(dow == 0 || dow == 6) return;
   if(InpITSM_SkipTue && dow == 2) return;
   if(InpITSM_SkipFri && dow == 5) return;

   // KZ check
   if(h < InpITSM_KzStart || h >= InpITSM_KzEnd) return;

   // 1 trade/day
   datetime today = GetToday();
   if(g_itsm_lastTradeDate == today) return;

   // Anti-overlap: max USDJPY+ positions
   if(CountPosSymbol(sym) >= InpGlobal_MaxUJPos) return;
   if(CountPos(InpITSM_Magic, sym) > 0) return;

   int sig = ITSM_CheckSignal();
   if(sig == 0) return;

   double atr = Buf1(g_itsm_atr, 0, 1);
   double zu = Buf1(g_itsm_zu, 0, 1), zl = Buf1(g_itsm_zl, 0, 1);
   double zTop = MathMax(zu, zl), zBot = MathMin(zu, zl);
   double pt = SymbolInfoDouble(sym, SYMBOL_POINT);
   bool isBuy = (sig > 0);
   double price, sl, tp;

   if(isBuy)
   {
      price = SymbolInfoDouble(sym, SYMBOL_ASK);
      sl = zBot - atr * ITSM_SL_ATR_MULT;
      tp = price + MathAbs(price - sl) * InpITSM_RR;
   }
   else
   {
      price = SymbolInfoDouble(sym, SYMBOL_BID);
      sl = zTop + atr * ITSM_SL_ATR_MULT;
      tp = price - MathAbs(sl - price) * InpITSM_RR;
   }

   // Enforce stop level
   int stopLvl = (int)SymbolInfoInteger(sym, SYMBOL_TRADE_STOPS_LEVEL);
   double minDist = stopLvl * pt;
   if(MathAbs(price - sl) < minDist) sl = isBuy ? price - minDist - pt : price + minDist + pt;
   if(MathAbs(tp - price) < minDist) tp = isBuy ? price + minDist + pt : price - minDist - pt;

   double lots = CalcLot(sym, InpITSM_RiskPct, InpITSM_MaxLot, MathAbs(price - sl));
   if(SendOrder(sym, InpITSM_Magic, isBuy, lots, sl, tp, "META_ITSM"))
   {
      g_itsm_lastTradeDate = today;
      Print("ITSM ", (isBuy?"BUY":"SELL"), " lots=", lots);
   }
}

//+------------------------------------------------------------------+
//| LONDONNNY MODULE — London→NY Momentum (USDJPY+)                   |
//+------------------------------------------------------------------+
void LDNY_DayReset()
{
   datetime today = GetToday();
   if(today != g_ldny_lastDay)
   {
      g_ldny_lastDay = today;
      g_ldny_londonOpen = 0; g_ldny_direction = 0;
      g_ldny_biasSet = false; g_ldny_traded = false;
   }
}

void LDNY_OnTick()
{
   if(!InpLDNY_Enabled) return;
   string sym = InpLDNY_Symbol;

   datetime bar = iTime(sym, PERIOD_M15, 0);
   if(bar == g_ldny_lastBar) return;
   g_ldny_lastBar = bar;

   LDNY_DayReset();

   int h = GetHour(sym);
   int dow = GetDOW();

   // Time exit
   if(CountPos(InpLDNY_Magic, sym) > 0 && h >= LDNY_EXIT_HOUR)
   {
      CloseAll(InpLDNY_Magic, sym, "TimeExit");
      return;
   }

   // Day filter
   if(dow == 0 || dow == 6) return;
   if(InpLDNY_SkipMon && dow == 1) return;
   if(InpLDNY_SkipWed && dow == 3) return;

   // Phase 1: Capture London open
   if(g_ldny_londonOpen == 0 && h == LDNY_LDN_START_H)
      g_ldny_londonOpen = iOpen(sym, PERIOD_M15, 0);

   // Phase 2: Measure London trend
   if(!g_ldny_biasSet && g_ldny_londonOpen > 0 && h == LDNY_LDN_MEASURE_H)
   {
      double close1 = iClose(sym, PERIOD_M15, 1);
      double move = close1 - g_ldny_londonOpen;
      double atr = Buf1(g_ldny_atrD1, 0, 1);
      double threshold = atr * LDNY_TREND_ATR;

      g_ldny_biasSet = true;
      if(move > threshold) g_ldny_direction = 1;
      else if(move < -threshold) g_ldny_direction = -1;
      else g_ldny_direction = 0;
   }

   // Phase 3: NY pullback entry
   if(!g_ldny_biasSet || g_ldny_direction == 0 || g_ldny_traded) return;
   if(h < LDNY_NY_START_H || h >= LDNY_NY_END_H) return;
   if(CountPos(InpLDNY_Magic, sym) > 0) return;

   // Anti-overlap
   if(CountPosSymbol(sym) >= InpGlobal_MaxUJPos) return;

   // Find pullback
   double atr = Buf1(g_ldny_atrD1, 0, 1);
   if(atr <= 0) return;
   double close1 = iClose(sym, PERIOD_M15, 1);
   double open1  = iOpen(sym, PERIOD_M15, 1);

   double recentHi = -999999, recentLo = 999999;
   for(int i = 1; i <= LDNY_PB_LOOKBACK; i++)
   {
      double hi = iHigh(sym, PERIOD_M15, i);
      double lo = iLow(sym, PERIOD_M15, i);
      if(hi > recentHi) recentHi = hi;
      if(lo < recentLo) recentLo = lo;
   }

   double depth = recentHi - recentLo;
   if(depth < atr * LDNY_PB_MIN_ATR || depth > atr * LDNY_PB_MAX_ATR) return;

   bool isBuy = (g_ldny_direction > 0);
   // Bounce bar direction
   if(isBuy && close1 <= open1) return;
   if(!isBuy && close1 >= open1) return;

   double pt = SymbolInfoDouble(sym, SYMBOL_POINT);
   double price, sl, tp;
   double pbExtreme = isBuy ? recentLo : recentHi;

   if(isBuy)
   {
      price = SymbolInfoDouble(sym, SYMBOL_ASK);
      sl = pbExtreme - atr * LDNY_SL_ATR_MULT;
      tp = price + MathAbs(price - sl) * InpLDNY_RR;
   }
   else
   {
      price = SymbolInfoDouble(sym, SYMBOL_BID);
      sl = pbExtreme + atr * LDNY_SL_ATR_MULT;
      tp = price - MathAbs(sl - price) * InpLDNY_RR;
   }

   // Enforce stop level
   int stopLvl = (int)SymbolInfoInteger(sym, SYMBOL_TRADE_STOPS_LEVEL);
   double minDist = stopLvl * pt;
   if(MathAbs(price - sl) < minDist) sl = isBuy ? price - minDist - pt : price + minDist + pt;
   if(MathAbs(tp - price) < minDist) tp = isBuy ? price + minDist + pt : price - minDist - pt;

   double lots = CalcLot(sym, InpLDNY_RiskPct, InpLDNY_MaxLot, MathAbs(price - sl));
   if(SendOrder(sym, InpLDNY_Magic, isBuy, lots, sl, tp, "META_LDNY"))
   {
      g_ldny_traded = true;
      Print("LDNY ", (isBuy?"BUY":"SELL"), " lots=", lots);
   }
}

//+------------------------------------------------------------------+
//| MAIN TICK ROUTER                                                   |
//+------------------------------------------------------------------+
void OnTick()
{
   if(IsMarketHoliday()) return;
   if(CheckDDKill())
   {
      // Kill ALL positions across all strategies
      if(InpCBR_Enabled) CloseAll(InpCBR_Magic, InpCBR_Symbol, "DD_KILL");
      if(InpITSM_Enabled) CloseAll(InpITSM_Magic, InpITSM_Symbol, "DD_KILL");
      if(InpLDNY_Enabled) CloseAll(InpLDNY_Magic, InpLDNY_Symbol, "DD_KILL");
      return;
   }

   // Route to each module (each has its own new-bar detection)
   CBR_OnTick();
   ITSM_OnTick();
   LDNY_OnTick();

   // Manage BE for ITSM/LDNY (no built-in BE for these in E8 config, but available)
}
//+------------------------------------------------------------------+
