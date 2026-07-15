//+------------------------------------------------------------------+
//| EA_OpeningMomentum.mq5                                            |
//| Intraday Momentum: Opening Hour → Closing Hour Continuation       |
//| Academic: Gao et al. (2018, SSRN 2552752), Lou & Polk (LSE)      |
//|                                                                    |
//| EDGE HYPOTHESIS:                                                  |
//| First-hour return predicts last-hour return same day.             |
//| If opening bar closes strongly up/down, market continues          |
//| into the close. R² 1.2% OOS (Gao et al.).                        |
//|                                                                    |
//| Counterparty: Retail dip-buyers at close, short-seller covering.  |
//| Half-life: 5-8 years (behavioral, not statistical).               |
//|                                                                    |
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
//| INPUTS                                                             |
//+------------------------------------------------------------------+
input group "=== Core ==="
input bool   InpEnabled       = true;
input double InpRiskPct       = 1.0;
input double InpMaxLot        = 10.0;
input int    InpMagic         = 20260411;
input string InpComment       = "OMom";

input group "=== Session Timing (Broker UTC+2/+3) ==="
input int    InpOpenBarH      = 16;    // Opening bar hour (US open ~16:30 broker)
input int    InpEntryBarH     = 17;    // Entry bar hour (after opening bar closes)
input int    InpExitH         = 22;    // Exit hour (US close ~22:00 broker)
input int    InpExitM         = 0;

input group "=== Signal ==="
input double InpMinReturnPct  = 0.15;  // Min opening bar return % for signal
input int    InpATR_Period    = 14;    // ATR period (H1)
input double InpSL_ATR_Mult  = 1.5;   // SL = ATR × this

input group "=== Filters ==="
input bool   InpUseVolFilter  = true;  // Require volume > avg
input double InpVolMult       = 1.2;   // Volume must be > avg × this
input int    InpVolLookback   = 20;    // Volume average lookback (bars)
input bool   InpUseATRRegime  = true;  // ATR regime filter (VIX proxy)
input double InpATR_Short     = 10;    // Short ATR period (daily)
input double InpATR_Long      = 60;    // Long ATR period (daily)

input group "=== Day Filter ==="
input bool   InpTradeMon      = true;
input bool   InpTradeTue      = true;
input bool   InpTradeWed      = true;
input bool   InpTradeThu      = true;
input bool   InpTradeFri      = true;

input group "=== Safety ==="
input double InpMaxDDPct      = 3.0;   // Daily DD kill (%)
input int    InpMaxRetries    = 3;

//+------------------------------------------------------------------+
//| GLOBALS                                                            |
//+------------------------------------------------------------------+
CTrade         g_trade;
CPositionInfo  g_pos;
CSymbolInfo    g_sym;

int    g_atrH1;         // ATR on H1
int    g_atrD1_short;   // Short ATR on D1 (regime filter)
int    g_atrD1_long;    // Long ATR on D1 (regime filter)

double g_dayStartEquity;
datetime g_lastDayReset;
datetime g_lastSignalDay;   // Separate tracker for signal state reset
datetime g_lastBar;
bool   g_tradeToday;
double g_openBarClose;    // Close of opening bar
double g_prevDayClose;    // Previous day close for return calc
bool   g_signalReady;
int    g_signalDir;       // +1 long, -1 short

//+------------------------------------------------------------------+
//| Init                                                               |
//+------------------------------------------------------------------+
int OnInit()
{
   if(!InpEnabled) return INIT_SUCCEEDED;

   g_trade.SetExpertMagicNumber(InpMagic);
   g_trade.SetDeviationInPoints(30);
   g_sym.Name(_Symbol);

   g_atrH1 = iATR(_Symbol, PERIOD_H1, InpATR_Period);
   if(g_atrH1 == INVALID_HANDLE) { Print("ATR H1 init failed"); return INIT_FAILED; }

   if(InpUseATRRegime)
   {
      g_atrD1_short = iATR(_Symbol, PERIOD_D1, (int)InpATR_Short);
      g_atrD1_long  = iATR(_Symbol, PERIOD_D1, (int)InpATR_Long);
      if(g_atrD1_short == INVALID_HANDLE || g_atrD1_long == INVALID_HANDLE)
      { Print("ATR D1 regime init failed"); return INIT_FAILED; }
   }

   g_dayStartEquity = AccountInfoDouble(ACCOUNT_EQUITY);
   g_lastDayReset = 0;
   g_lastSignalDay = 0;
   g_lastBar = 0;
   g_tradeToday = false;
   g_openBarClose = 0;
   g_prevDayClose = 0;
   g_signalReady = false;
   g_signalDir = 0;

   Print("EA_OpeningMomentum v1.0 | Symbol=", _Symbol);
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   if(g_atrH1 != INVALID_HANDLE) IndicatorRelease(g_atrH1);
   if(InpUseATRRegime)
   {
      if(g_atrD1_short != INVALID_HANDLE) IndicatorRelease(g_atrD1_short);
      if(g_atrD1_long != INVALID_HANDLE) IndicatorRelease(g_atrD1_long);
   }
}

//+------------------------------------------------------------------+
//| Helpers                                                            |
//+------------------------------------------------------------------+
int GetHour()
{
   MqlDateTime dt; TimeToStruct(TimeCurrent(), dt);
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

int CountPos()
{
   int c = 0;
   for(int i = PositionsTotal()-1; i >= 0; i--)
      if(g_pos.SelectByIndex(i) && g_pos.Magic() == InpMagic && g_pos.Symbol() == _Symbol) c++;
   return c;
}

void CloseAll(string reason)
{
   for(int i = PositionsTotal()-1; i >= 0; i--)
   {
      if(g_pos.SelectByIndex(i) && g_pos.Magic() == InpMagic && g_pos.Symbol() == _Symbol)
      {
         g_trade.PositionClose(g_pos.Ticket());
         Print("CLOSE [", reason, "] ticket=", g_pos.Ticket(), " P/L=", g_pos.Profit());
      }
   }
}

double Buf1(int handle, int buf, int shift)
{
   double v[]; if(CopyBuffer(handle, buf, shift, 1, v) < 1) return 0; return v[0];
}

double CalcLot(double slPts)
{
   if(slPts <= 0) return g_sym.LotsMin();
   double risk = AccountInfoDouble(ACCOUNT_BALANCE) * InpRiskPct / 100.0;
   double tv = g_sym.TickValue(), ts = g_sym.TickSize();
   if(tv <= 0 || ts <= 0) return g_sym.LotsMin();
   double lotPerPt = tv / ts;
   double lots = risk / (slPts * lotPerPt);
   lots = MathMin(lots, InpMaxLot);
   lots = MathMax(lots, g_sym.LotsMin());
   lots = NormalizeDouble(MathFloor(lots / g_sym.LotsStep()) * g_sym.LotsStep(), 2);
   return lots;
}

bool IsTradingDay()
{
   int dow = GetDOW();
   switch(dow)
   {
      case 1: return InpTradeMon; case 2: return InpTradeTue;
      case 3: return InpTradeWed; case 4: return InpTradeThu;
      case 5: return InpTradeFri; default: return false;
   }
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
   if(g_dayStartEquity > 0 && (g_dayStartEquity - eq) / g_dayStartEquity * 100.0 >= InpMaxDDPct)
      return true;
   return false;
}

//+------------------------------------------------------------------+
//| Volume filter                                                      |
//+------------------------------------------------------------------+
bool PassVolFilter()
{
   if(!InpUseVolFilter) return true;
   long vol0 = iVolume(_Symbol, PERIOD_H1, 1);
   if(vol0 <= 0) return true; // No volume data → pass

   double sum = 0;
   int cnt = 0;
   for(int i = 2; i <= InpVolLookback + 1; i++)
   {
      long v = iVolume(_Symbol, PERIOD_H1, i);
      if(v > 0) { sum += (double)v; cnt++; }
   }
   if(cnt == 0) return true;
   double avg = sum / cnt;
   return ((double)vol0 >= avg * InpVolMult);
}

//+------------------------------------------------------------------+
//| ATR regime filter (VIX proxy)                                      |
//+------------------------------------------------------------------+
int GetATRRegime()
{
   // Returns: +1 = contango proxy (vol declining, long bias)
   //          -1 = backwardation proxy (vol rising, short bias)
   //           0 = neutral
   if(!InpUseATRRegime) return 0;
   double atrS = Buf1(g_atrD1_short, 0, 1);
   double atrL = Buf1(g_atrD1_long, 0, 1);
   if(atrL <= 0) return 0;
   double ratio = atrS / atrL;
   if(ratio < 0.85) return 1;   // Contango: vol declining → long bias
   if(ratio > 1.15) return -1;  // Backwardation: vol rising → short/reduce
   return 0;
}

//+------------------------------------------------------------------+
//| OnTick                                                             |
//+------------------------------------------------------------------+
void OnTick()
{
   if(!InpEnabled) return;
   if(IsMarketHoliday()) return;
   if(CheckDDKill())
   {
      if(CountPos() > 0) CloseAll("DD_KILL");
      return;
   }

   g_sym.RefreshRates();

   // New bar detection (H1)
   datetime curBar = iTime(_Symbol, PERIOD_H1, 0);
   if(curBar == g_lastBar) return;
   g_lastBar = curBar;

   int h = GetHour();

   // Day reset (uses separate tracker from DD kill)
   datetime today = GetToday();
   if(today != g_lastSignalDay)
   {
      g_lastSignalDay = today;
      g_tradeToday = false;
      g_openBarClose = 0;
      g_signalReady = false;
      g_signalDir = 0;
      // Get previous day close for return calculation
      g_prevDayClose = iClose(_Symbol, PERIOD_D1, 1);
      Print("DAY RESET: prevClose=", g_prevDayClose, " date=", TimeToString(today, TIME_DATE));
   }

   // --- Time Exit ---
   if(CountPos() > 0 && h >= InpExitH)
   {
      CloseAll("TimeExit");
      return;
   }

   if(!IsTradingDay()) return;
   if(g_tradeToday) return;

   // --- Phase 1: Capture opening bar close ---
   // When hour AFTER opening bar starts, the opening bar is bar[1]
   if(g_openBarClose == 0 && h == InpEntryBarH)
   {
      g_openBarClose = iClose(_Symbol, PERIOD_H1, 1);
      double openBarOpen = iOpen(_Symbol, PERIOD_H1, 1);

      Print("PHASE1: h=", h, " openBarClose=", g_openBarClose,
            " openBarOpen=", openBarOpen, " prevDayClose=", g_prevDayClose);

      if(g_prevDayClose <= 0 || g_openBarClose <= 0)
      {
         Print("PHASE1: SKIP — prevDayClose or openBarClose is 0");
         return;
      }

      // Calculate return of opening bar vs previous day close
      double ret = (g_openBarClose - g_prevDayClose) / g_prevDayClose * 100.0;

      if(ret > InpMinReturnPct)
      {
         g_signalDir = 1; // Long
         g_signalReady = true;
         Print("OPENING MOMENTUM: LONG signal. Return=", DoubleToString(ret, 3), "%");
      }
      else if(ret < -InpMinReturnPct)
      {
         g_signalDir = -1; // Short
         g_signalReady = true;
         Print("OPENING MOMENTUM: SHORT signal. Return=", DoubleToString(ret, 3), "%");
      }
      else
      {
         Print("OPENING MOMENTUM: No signal. Return=", DoubleToString(ret, 3), "% < threshold");
      }
   }

   // --- Phase 2: Entry ---
   if(g_signalReady && h == InpEntryBarH && CountPos() == 0)
   {
      // Volume filter
      if(!PassVolFilter())
      {
         Print("OMOM: Volume filter BLOCKED");
         g_signalReady = false;
         return;
      }

      // ATR regime filter
      int regime = GetATRRegime();
      if(regime == 1 && g_signalDir == -1)
      {
         Print("OMOM: Regime CONTANGO blocks SHORT");
         g_signalReady = false;
         return;
      }
      if(regime == -1 && g_signalDir == 1)
      {
         Print("OMOM: Regime BACKWARDATION blocks LONG");
         g_signalReady = false;
         return;
      }

      // Calculate SL
      double atr = Buf1(g_atrH1, 0, 1);
      if(atr <= 0) return;
      double slDist = atr * InpSL_ATR_Mult;

      bool isBuy = (g_signalDir > 0);
      double price = isBuy ? g_sym.Ask() : g_sym.Bid();
      double sl, tp;

      if(isBuy)
      {
         sl = price - slDist;
         tp = 0; // Time exit only — no fixed TP
      }
      else
      {
         sl = price + slDist;
         tp = 0;
      }

      // Enforce stop level
      int stopLvl = (int)SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL);
      double minDist = stopLvl * g_sym.Point();
      if(MathAbs(price - sl) < minDist)
         sl = isBuy ? price - minDist - g_sym.Point() : price + minDist + g_sym.Point();

      double lots = CalcLot(slDist);

      bool ok = false;
      for(int att = 1; att <= InpMaxRetries; att++)
      {
         if(isBuy) ok = g_trade.Buy(lots, _Symbol, price, sl, tp, InpComment);
         else      ok = g_trade.Sell(lots, _Symbol, price, sl, tp, InpComment);
         if(ok && g_trade.ResultRetcode() == 10009) break;
         if(att < InpMaxRetries) Sleep(200 * att);
         price = isBuy ? g_sym.Ask() : g_sym.Bid();
      }

      if(ok)
      {
         g_tradeToday = true;
         g_signalReady = false;
         Print("OMOM ", (isBuy?"BUY":"SELL"), " lots=", lots, " sl=", sl, " regime=", regime);
      }
   }
}
//+------------------------------------------------------------------+
