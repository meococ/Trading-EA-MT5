//+------------------------------------------------------------------+
//| EA_DXYGold.mq5 — Dollar Weakness → Gold Buy (Cross-Asset)        |
//| Symbol: XAUUSD+  |  Period: M15  |  Style: Cross-asset lead-lag   |
//|                                                                   |
//| EDGE HYPOTHESIS:                                                  |
//| When EURUSD spikes up (dollar weakens) but XAUUSD hasn't moved   |
//| yet, gold should catch up. Correlation DXY-gold -0.5 to -0.8.    |
//| EURUSD = 57.6% of DXY weight = best single proxy.                |
//|                                                                   |
//| The lag exists because FX markets (most liquid) adjust first,     |
//| gold (physical + futures + ETF + CFD chain) adjusts slower.      |
//|                                                                   |
//| CRITICAL: DXY-gold correlation breaks in crisis (2020, 2023-24). |
//| This is expected to show regime-dependence.                       |
//|                                                                   |
//| Source: Academic DXY-gold correlation literature                  |
//| Novelty: Type #72 — cross-asset directional divergence           |
//|                                                                   |
//| SIGNALS ON BAR[1] ONLY — no repaint.                              |
//| Max | 2026-04-13 | v1.0                                          |
//+------------------------------------------------------------------+
#property copyright "Max — EA_DXYGold v1.0"
#property version   "1.00"
#property strict

//+------------------------------------------------------------------+
input group "=== General ==="
input ulong    InpMagic         = 210001;
input int      InpDeviation     = 30;
input bool     InpKillSwitch    = false;

input group "=== Cross-Asset Settings ==="
input string   InpDXYProxy      = "EURUSD+";     // DXY proxy (inverse)
input int      InpReturnBars    = 4;             // Bars to measure return
input double   InpDXYThreshold  = 0.10;          // Min EURUSD move % to trigger
input double   InpGoldMaxMove   = 0.05;          // Max gold move % (hasn't caught up)
input double   InpDivergence    = 0.05;          // Min divergence (EURUSD move - gold move)

input group "=== Session Filter ==="
input int      InpStartHour     = 10;
input int      InpEndHour       = 20;
input int      InpExitHour      = 22;

input group "=== Risk Management ==="
input double   InpRiskPct       = 0.50;
input double   InpMaxLot        = 1.0;
input double   InpSL_ATR_Mult   = 1.5;
input int      InpMinSLPoints   = 100;
input int      InpMaxSLPoints   = 1000;
input double   InpTP_Ratio      = 1.0;
input int      InpMaxPerDay     = 2;
input double   InpDailyDD       = 4.0;

input group "=== Day Filters ==="
input bool     InpSkipMon       = true;
input bool     InpSkipFri       = true;

//+------------------------------------------------------------------+
int      g_hATR = INVALID_HANDLE;
datetime g_lastBar = 0;
int      g_tradesToday = 0;
int      g_lastTradeDay = -1;
double   g_dayStartBalance = 0;

int OnInit()
{
   g_hATR = iATR(_Symbol, PERIOD_CURRENT, 14);
   if(g_hATR == INVALID_HANDLE) { Print("[DXYGold] ATR init fail"); return INIT_FAILED; }
   g_dayStartBalance = AccountInfoDouble(ACCOUNT_BALANCE);
   PrintFormat("[DXYGold] v1.00 | %s %s | Magic=%d", _Symbol, EnumToString(_Period), InpMagic);
   PrintFormat("[DXYGold] DXY proxy: %s | RetBars=%d | Thresh=%.3f%%",
               InpDXYProxy, InpReturnBars, InpDXYThreshold);
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
//| Detect DXY-Gold divergence                                        |
//| +1 = EURUSD up (USD weak) but gold flat → BUY gold               |
//| -1 = EURUSD down (USD strong) but gold flat → SELL gold           |
//|  0 = no divergence                                                |
//+------------------------------------------------------------------+
int DetectDivergence()
{
   // EURUSD return over N bars
   double euO = iOpen(InpDXYProxy, PERIOD_CURRENT, InpReturnBars);
   double euC = iClose(InpDXYProxy, PERIOD_CURRENT, 1);
   if(euO <= 0) return 0;
   double euReturn = (euC - euO) / euO * 100.0;

   // Gold return over same N bars
   double auO = iOpen(_Symbol, PERIOD_CURRENT, InpReturnBars);
   double auC = iClose(_Symbol, PERIOD_CURRENT, 1);
   if(auO <= 0) return 0;
   double auReturn = (auC - auO) / auO * 100.0;

   // EURUSD up significantly but gold hasn't moved → buy gold
   if(euReturn >= InpDXYThreshold && auReturn <= InpGoldMaxMove)
   {
      double div = euReturn - auReturn;
      if(div >= InpDivergence)
      {
         PrintFormat("[DXYGold] BUY signal: EURUSD +%.3f%% but Gold %.3f%% (div=%.3f%%)",
                     euReturn, auReturn, div);
         return +1;
      }
   }

   // EURUSD down significantly but gold hasn't dropped → sell gold
   if(euReturn <= -InpDXYThreshold && auReturn >= -InpGoldMaxMove)
   {
      double div = MathAbs(euReturn) - MathAbs(auReturn);
      if(div >= InpDivergence)
      {
         PrintFormat("[DXYGold] SELL signal: EURUSD %.3f%% but Gold %.3f%% (div=%.3f%%)",
                     euReturn, auReturn, div);
         return -1;
      }
   }

   return 0;
}

void OnTick()
{
   if(InpKillSwitch) return;
   datetime barTime = iTime(_Symbol, PERIOD_CURRENT, 0);
   if(barTime == g_lastBar) return;
   g_lastBar = barTime;

   MqlDateTime dt; TimeToStruct(barTime, dt);

   if(dt.day_of_year != g_lastTradeDay)
   {
      g_lastTradeDay = dt.day_of_year;
      g_tradesToday = 0;
      g_dayStartBalance = AccountInfoDouble(ACCOUNT_BALANCE);
   }

   if(dt.hour >= InpExitHour && CountPositions() > 0) { CloseAllPositions(); return; }
   if(dt.hour < InpStartHour || dt.hour >= InpEndHour) return;
   if(g_tradesToday >= InpMaxPerDay) return;
   if(CountPositions() > 0) return;
   if(IsDailyDDExceeded()) return;
   if(InpSkipMon && dt.day_of_week == 1) return;
   if(InpSkipFri && dt.day_of_week == 5) return;

   int signal = DetectDivergence();
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
   req.comment = StringFormat("DXYGold|%s", isBuy ? "USD_weak" : "USD_strong");
   req.type_filling = ORDER_FILLING_FOK;
   if(!OrderSend(req, res))
   {
      req.type_filling = ORDER_FILLING_IOC;
      if(!OrderSend(req, res))
      { PrintFormat("[DXYGold] FAIL: err=%d", GetLastError()); return; }
   }
   if(res.retcode == TRADE_RETCODE_DONE || res.retcode == TRADE_RETCODE_PLACED)
   {
      g_tradesToday++;
      PrintFormat("[DXYGold] %s %.2f @ %.2f | SL=%.2f TP=%.2f", isBuy?"BUY":"SELL", lot, res.price, sl, tp);
   }
}

double OnTester()
{
   double pf = TesterStatistics(STAT_PROFIT_FACTOR);
   double n  = TesterStatistics(STAT_TRADES);
   if(n < 20) return 0;
   return pf * MathSqrt(n);
}
