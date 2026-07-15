//+------------------------------------------------------------------+
//| EA_SessionDrift.mq5 — London Return → NY Continuation             |
//| Symbol: XAUUSD+ / USDJPY+  |  Period: M15                        |
//|                                                                   |
//| EDGE HYPOTHESIS:                                                  |
//| When London session (h09-14 server) produces a strong directional |
//| move (cumulative return exceeds threshold), that direction         |
//| persists into NY session (h15-19). The structural reason:         |
//| institutional order flow initiated in London continues as US      |
//| participants validate/amplify the same fundamental information.   |
//|                                                                   |
//| DISTINCT FROM:                                                    |
//| - LondonNY EA: uses EMA pullback signal, not raw session return  |
//| - GoldMomo S599: tested M5 bar-to-bar persistence, not           |
//|   multi-hour session-to-session                                   |
//| - Session breakout: uses HIGH/LOW range, not cumulative RETURN    |
//|                                                                   |
//| Novelty: Type #79 — session return persistence                    |
//| SIGNALS ON BAR[1] ONLY — no repaint.                              |
//| Max | 2026-04-13 | v1.0                                          |
//+------------------------------------------------------------------+
#property copyright "Max — EA_SessionDrift v1.0"
#property version   "1.00"
#property strict

input group "=== General ==="
input ulong    InpMagic         = 212001;
input int      InpDeviation     = 30;
input bool     InpKillSwitch    = false;

input group "=== Session Drift Settings ==="
input int      InpLondonStart   = 9;             // London session start (server time)
input int      InpLondonEnd     = 14;            // London session end — measure return over this
input int      InpEntryStart    = 15;            // NY entry window start
input int      InpEntryEnd      = 18;            // NY entry window end (only enter first bar if triggered)
input double   InpMinDrift      = 0.15;          // Min London return % to trigger (0.15 = 0.15%)
input double   InpMaxDrift      = 1.50;          // Max return % — too large = news event, skip
input bool     InpConfirmFirst  = true;          // Also require first NY bar confirms direction

input group "=== Risk Management ==="
input double   InpRiskPct       = 0.50;
input double   InpMaxLot        = 1.0;
input double   InpSL_ATR_Mult   = 1.5;
input int      InpMinSLPoints   = 100;
input int      InpMaxSLPoints   = 1000;
input double   InpTP_Ratio      = 1.0;
input int      InpMaxPerDay     = 1;
input double   InpDailyDD       = 4.0;
input int      InpExitHour      = 22;

input group "=== Day Filters ==="
input bool     InpSkipMon       = true;
input bool     InpSkipFri       = true;

//+------------------------------------------------------------------+
int      g_hATR = INVALID_HANDLE;
datetime g_lastBar = 0;
int      g_tradesToday = 0;
int      g_lastTradeDay = -1;
double   g_dayStartBalance = 0;
double   g_londonOpen = 0;
double   g_londonClose = 0;
int      g_londonDay = -1;
bool     g_londonMeasured = false;
int      g_londonSignal = 0;   // +1 buy, -1 sell, 0 none

int OnInit()
{
   g_hATR = iATR(_Symbol, PERIOD_CURRENT, 14);
   if(g_hATR == INVALID_HANDLE) { Print("[DRIFT] ATR init fail"); return INIT_FAILED; }
   g_dayStartBalance = AccountInfoDouble(ACCOUNT_BALANCE);
   PrintFormat("[DRIFT] v1.00 | %s %s | Magic=%d", _Symbol, EnumToString(_Period), InpMagic);
   PrintFormat("[DRIFT] London h%d-h%d → NY h%d-h%d | Drift %.2f%%-%.2f%%",
               InpLondonStart, InpLondonEnd, InpEntryStart, InpEntryEnd,
               InpMinDrift, InpMaxDrift);
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason) { if(g_hATR != INVALID_HANDLE) IndicatorRelease(g_hATR); }

int CountPositions()
{
   int cnt = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong t = PositionGetTicket(i);
      if(t > 0 && PositionGetInteger(POSITION_MAGIC) == (long)InpMagic
         && PositionGetString(POSITION_SYMBOL) == _Symbol) cnt++;
   }
   return cnt;
}

void CloseAllPositions()
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong t = PositionGetTicket(i);
      if(t <= 0 || PositionGetInteger(POSITION_MAGIC) != (long)InpMagic
         || PositionGetString(POSITION_SYMBOL) != _Symbol) continue;
      MqlTradeRequest req = {}; MqlTradeResult res = {};
      req.action = TRADE_ACTION_DEAL; req.symbol = _Symbol;
      req.volume = PositionGetDouble(POSITION_VOLUME);
      req.deviation = (ulong)InpDeviation; req.magic = InpMagic; req.position = t;
      if(PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY)
         { req.type = ORDER_TYPE_SELL; req.price = SymbolInfoDouble(_Symbol, SYMBOL_BID); }
      else
         { req.type = ORDER_TYPE_BUY; req.price = SymbolInfoDouble(_Symbol, SYMBOL_ASK); }
      req.type_filling = ORDER_FILLING_FOK;
      if(!OrderSend(req, res)) { req.type_filling = ORDER_FILLING_IOC; OrderSend(req, res); }
   }
}

bool IsDailyDDExceeded()
{
   if(g_dayStartBalance <= 0) return false;
   return (g_dayStartBalance - AccountInfoDouble(ACCOUNT_EQUITY)) / g_dayStartBalance * 100.0 >= InpDailyDD;
}

double CalcLot(double slDist)
{
   if(slDist <= 0) return 0;
   double bal  = AccountInfoDouble(ACCOUNT_BALANCE);
   double risk = bal * InpRiskPct / 100.0;
   double tv   = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
   double ts   = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   if(tv <= 0 || ts <= 0) return 0;
   double lot = risk / (slDist / ts * tv);
   lot = MathMin(lot, InpMaxLot);
   lot = MathMin(lot, SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX));
   lot = MathMax(lot, SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN));
   lot = MathFloor(lot / SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP))
         * SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   return lot;
}

//+------------------------------------------------------------------+
//| Measure London session return and generate signal                  |
//+------------------------------------------------------------------+
void MeasureLondon(const MqlDateTime &dt)
{
   // Capture London open price
   if(dt.hour == InpLondonStart && g_londonDay != dt.day_of_year)
   {
      g_londonOpen = iClose(_Symbol, PERIOD_CURRENT, 1);
      g_londonDay = dt.day_of_year;
      g_londonMeasured = false;
      g_londonSignal = 0;
   }

   // Measure London close (at end of London session)
   if(dt.hour == InpLondonEnd && !g_londonMeasured && g_londonOpen > 0
      && g_londonDay == dt.day_of_year)
   {
      g_londonClose = iClose(_Symbol, PERIOD_CURRENT, 1);
      double drift = (g_londonClose - g_londonOpen) / g_londonOpen * 100.0;

      g_londonMeasured = true;

      if(MathAbs(drift) >= InpMinDrift && MathAbs(drift) <= InpMaxDrift)
      {
         g_londonSignal = drift > 0 ? +1 : -1;
         PrintFormat("[DRIFT] London h%d-h%d drift: %.3f%% → signal %s",
                     InpLondonStart, InpLondonEnd, drift,
                     g_londonSignal > 0 ? "BUY" : "SELL");
      }
      else
      {
         g_londonSignal = 0;
         if(MathAbs(drift) < InpMinDrift)
            PrintFormat("[DRIFT] London drift %.3f%% < threshold %.2f%% → NO SIGNAL", drift, InpMinDrift);
         else
            PrintFormat("[DRIFT] London drift %.3f%% > max %.2f%% → NEWS EVENT SKIP", drift, InpMaxDrift);
      }
   }
}

void OnTick()
{
   if(InpKillSwitch) return;
   datetime barTime = iTime(_Symbol, PERIOD_CURRENT, 0);
   if(barTime == g_lastBar) return;
   g_lastBar = barTime;

   MqlDateTime dt; TimeToStruct(barTime, dt);

   // Day reset
   if(dt.day_of_year != g_lastTradeDay)
   {
      g_lastTradeDay = dt.day_of_year;
      g_tradesToday = 0;
      g_dayStartBalance = AccountInfoDouble(ACCOUNT_BALANCE);
   }

   // Measure London session
   MeasureLondon(dt);

   // Time stop
   if(dt.hour >= InpExitHour && CountPositions() > 0) { CloseAllPositions(); return; }

   // Entry window
   if(dt.hour < InpEntryStart || dt.hour >= InpEntryEnd) return;
   if(g_tradesToday >= InpMaxPerDay) return;
   if(CountPositions() > 0) return;
   if(IsDailyDDExceeded()) return;
   if(InpSkipMon && dt.day_of_week == 1) return;
   if(InpSkipFri && dt.day_of_week == 5) return;

   if(g_londonSignal == 0) return;

   // Optional: confirm first NY bar goes in same direction
   if(InpConfirmFirst && dt.hour == InpEntryStart)
   {
      double nyBar = iClose(_Symbol, PERIOD_CURRENT, 1) - iOpen(_Symbol, PERIOD_CURRENT, 1);
      if(g_londonSignal > 0 && nyBar <= 0) return;   // London up but first NY bar down → skip
      if(g_londonSignal < 0 && nyBar >= 0) return;   // London down but first NY bar up → skip
   }

   double atr[];
   ArraySetAsSeries(atr, true);
   if(CopyBuffer(g_hATR, 0, 1, 1, atr) < 1) return;

   double slDist = atr[0] * InpSL_ATR_Mult;
   if(slDist < InpMinSLPoints * _Point) slDist = InpMinSLPoints * _Point;
   if(slDist > InpMaxSLPoints * _Point) return;

   bool isBuy = (g_londonSignal == +1);
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double entry = isBuy ? ask : bid;
   double sl = isBuy ? ask - slDist : bid + slDist;
   double tp = isBuy ? ask + slDist * InpTP_Ratio : bid - slDist * InpTP_Ratio;

   int stopLevel = (int)SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL);
   if(slDist < stopLevel * _Point) return;

   double lot = CalcLot(slDist);
   if(lot <= 0) return;

   int digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
   sl = NormalizeDouble(sl, digits); tp = NormalizeDouble(tp, digits);

   MqlTradeRequest req = {}; MqlTradeResult res = {};
   req.action = TRADE_ACTION_DEAL; req.symbol = _Symbol;
   req.volume = lot; req.type = isBuy ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
   req.price = entry; req.sl = sl; req.tp = tp;
   req.deviation = (ulong)InpDeviation; req.magic = InpMagic;
   req.comment = StringFormat("DRIFT|%s|ldn=%.2f%%",
                              isBuy ? "LdnUp" : "LdnDn",
                              (g_londonClose - g_londonOpen) / g_londonOpen * 100);
   req.type_filling = ORDER_FILLING_FOK;
   if(!OrderSend(req, res))
   {
      req.type_filling = ORDER_FILLING_IOC;
      if(!OrderSend(req, res))
      { PrintFormat("[DRIFT] FAIL: err=%d", GetLastError()); return; }
   }
   if(res.retcode == TRADE_RETCODE_DONE || res.retcode == TRADE_RETCODE_PLACED)
   {
      g_tradesToday++;
      g_londonSignal = 0;   // consumed
      PrintFormat("[DRIFT] %s %.2f @ %.5f | SL=%.5f TP=%.5f",
                  isBuy?"BUY":"SELL", lot, res.price, sl, tp);
   }
}

double OnTester()
{
   double pf = TesterStatistics(STAT_PROFIT_FACTOR);
   double n  = TesterStatistics(STAT_TRADES);
   if(n < 20) return 0;
   return pf * MathSqrt(n);
}
