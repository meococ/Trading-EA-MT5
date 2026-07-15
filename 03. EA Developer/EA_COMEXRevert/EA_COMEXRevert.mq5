//+------------------------------------------------------------------+
//| EA_COMEXRevert.mq5 — COMEX Open Gap Reversion                    |
//| Symbol: XAUUSD+  |  Period: M15  |  Style: Mean Reversion         |
//|                                                                   |
//| EDGE HYPOTHESIS:                                                  |
//| When overnight London session creates a large move in gold,       |
//| COMEX open (08:20 ET / 13:20 GMT) often reverses that move as    |
//| physical arbitrage flows close the LBMA-COMEX premium spread.    |
//| Amplified in tariff-era 2025 when premiums spiked $20-50/oz.    |
//|                                                                   |
//| PROXY: Measure return from Asian close (h09 server) to current   |
//| bar. If move exceeds threshold, fade it at COMEX open window.    |
//|                                                                   |
//| Source: COMEX-LBMA arbitrage flows, tariff-era premium data       |
//| Novelty: Type #78 — COMEX open reversion (distinct from AM Fix)  |
//|                                                                   |
//| SIGNALS ON BAR[1] ONLY — no repaint.                              |
//| Max | 2026-04-13 | v1.0                                          |
//+------------------------------------------------------------------+
#property copyright "Max — EA_COMEXRevert v1.0"
#property version   "1.00"
#property strict

input group "=== General ==="
input ulong    InpMagic         = 211001;
input int      InpDeviation     = 30;
input bool     InpKillSwitch    = false;

input group "=== COMEX Reversion Settings ==="
input int      InpBaseHour      = 9;             // Overnight base hour (server) — end of Asian
input int      InpEntryStart    = 15;            // COMEX open window start (server)
input int      InpEntryEnd      = 17;            // COMEX open window end (server)
input double   InpGapThreshold  = 0.20;          // Min overnight gap % to trigger (0.20 = 0.2%)
input double   InpMaxGap        = 1.50;          // Max gap % (too large = news event, skip)

input group "=== Session & Day Filters ==="
input int      InpExitHour      = 22;
input bool     InpSkipMon       = true;
input bool     InpSkipFri       = true;

input group "=== Risk Management ==="
input double   InpRiskPct       = 0.50;
input double   InpMaxLot        = 1.0;
input double   InpSL_ATR_Mult   = 1.5;
input int      InpMinSLPoints   = 100;
input int      InpMaxSLPoints   = 1000;
input double   InpTP_Ratio      = 1.0;           // 1:1 RR
input int      InpMaxPerDay     = 1;             // Only 1 trade per day
input double   InpDailyDD       = 4.0;

//+------------------------------------------------------------------+
int      g_hATR = INVALID_HANDLE;
datetime g_lastBar = 0;
int      g_tradesToday = 0;
int      g_lastTradeDay = -1;
double   g_dayStartBalance = 0;
double   g_basePrice = 0;               // Price at base hour
int      g_baseDayOfYear = -1;

int OnInit()
{
   g_hATR = iATR(_Symbol, PERIOD_CURRENT, 14);
   if(g_hATR == INVALID_HANDLE) { Print("[COMEX] ATR init fail"); return INIT_FAILED; }
   g_dayStartBalance = AccountInfoDouble(ACCOUNT_BALANCE);
   PrintFormat("[COMEX] v1.00 | %s %s | Magic=%d", _Symbol, EnumToString(_Period), InpMagic);
   PrintFormat("[COMEX] BaseHour=%d | Entry h%d-h%d | Gap=%.2f%%-%.2f%%",
               InpBaseHour, InpEntryStart, InpEntryEnd, InpGapThreshold, InpMaxGap);
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
   double bal   = AccountInfoDouble(ACCOUNT_BALANCE);
   double risk  = bal * InpRiskPct / 100.0;
   double tv    = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
   double ts    = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
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
//| Capture base price at start of London session                     |
//+------------------------------------------------------------------+
void CaptureBasePrice(const MqlDateTime &dt)
{
   if(dt.hour == InpBaseHour && g_baseDayOfYear != dt.day_of_year)
   {
      g_basePrice = iClose(_Symbol, PERIOD_CURRENT, 1);
      g_baseDayOfYear = dt.day_of_year;
      if(g_basePrice > 0)
         PrintFormat("[COMEX] Base price captured: %.2f at h%d day %d",
                     g_basePrice, InpBaseHour, dt.day_of_year);
   }
}

//+------------------------------------------------------------------+
//| Detect overnight gap for COMEX reversion                          |
//| +1 = price dropped overnight → BUY (mean revert up)              |
//| -1 = price rallied overnight → SELL (mean revert down)           |
//|  0 = no signal                                                    |
//+------------------------------------------------------------------+
int DetectGap()
{
   if(g_basePrice <= 0) return 0;

   double currentClose = iClose(_Symbol, PERIOD_CURRENT, 1);
   if(currentClose <= 0) return 0;

   double gapPct = (currentClose - g_basePrice) / g_basePrice * 100.0;

   // Gap must exceed threshold but not be too large (news event)
   if(MathAbs(gapPct) < InpGapThreshold) return 0;
   if(MathAbs(gapPct) > InpMaxGap) return 0;

   PrintFormat("[COMEX] Gap detected: %.3f%% (base=%.2f, now=%.2f)",
               gapPct, g_basePrice, currentClose);

   // FADE the gap: if price went up, sell; if price went down, buy
   if(gapPct > 0) return -1;   // rallied overnight → sell (revert down)
   if(gapPct < 0) return +1;   // dropped overnight → buy (revert up)

   return 0;
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

   // Capture base price at start of London session
   CaptureBasePrice(dt);

   // Time stop
   if(dt.hour >= InpExitHour && CountPositions() > 0) { CloseAllPositions(); return; }

   // Entry window filter
   if(dt.hour < InpEntryStart || dt.hour >= InpEntryEnd) return;

   // Pre-flight
   if(g_tradesToday >= InpMaxPerDay) return;
   if(CountPositions() > 0) return;
   if(IsDailyDDExceeded()) return;
   if(InpSkipMon && dt.day_of_week == 1) return;
   if(InpSkipFri && dt.day_of_week == 5) return;

   int signal = DetectGap();
   if(signal == 0) return;

   double atr[];
   ArraySetAsSeries(atr, true);
   if(CopyBuffer(g_hATR, 0, 1, 1, atr) < 1) return;

   double slDist = atr[0] * InpSL_ATR_Mult;
   if(slDist < InpMinSLPoints * _Point) slDist = InpMinSLPoints * _Point;
   if(slDist > InpMaxSLPoints * _Point) return;

   bool isBuy = (signal == +1);
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
   req.comment = StringFormat("COMEX|%s|gap=%.2f%%",
                              isBuy ? "FadeDrop" : "FadeRally",
                              (iClose(_Symbol,PERIOD_CURRENT,1)-g_basePrice)/g_basePrice*100);
   req.type_filling = ORDER_FILLING_FOK;
   if(!OrderSend(req, res))
   {
      req.type_filling = ORDER_FILLING_IOC;
      if(!OrderSend(req, res))
      { PrintFormat("[COMEX] FAIL: err=%d", GetLastError()); return; }
   }
   if(res.retcode == TRADE_RETCODE_DONE || res.retcode == TRADE_RETCODE_PLACED)
   {
      g_tradesToday++;
      PrintFormat("[COMEX] %s %.2f @ %.2f | SL=%.2f TP=%.2f | gap=%.2f%%",
                  isBuy?"BUY":"SELL", lot, res.price, sl, tp,
                  (iClose(_Symbol,PERIOD_CURRENT,1)-g_basePrice)/g_basePrice*100);
   }
}

double OnTester()
{
   double pf = TesterStatistics(STAT_PROFIT_FACTOR);
   double n  = TesterStatistics(STAT_TRADES);
   if(n < 20) return 0;
   return pf * MathSqrt(n);
}
