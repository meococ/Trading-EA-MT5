//+------------------------------------------------------------------+
//| EA_MultiJPY.mq5 — Multi-JPY Alignment → USDJPY Signal            |
//| Symbol: USDJPY+  |  Period: M15  |  Style: Cross-asset momentum   |
//|                                                                   |
//| EDGE HYPOTHESIS:                                                  |
//| When EURJPY, GBPJPY, and AUDJPY all move in same direction       |
//| within one M15 bar, USDJPY follows 1-2 bars later. The           |
//| structural reason: information flows through liquid crosses       |
//| first (EURJPY/GBPJPY) before the USDJPY pair fully adjusts.     |
//| 3-pair consensus = stronger signal than 1-pair (S555 CrossLead). |
//|                                                                   |
//| Source: BIS Working Paper 836 (FX liquidity transmission)         |
//| Novelty: Type #71 — variant of CrossLead but multi-pair filter   |
//|                                                                   |
//| SIGNALS ON BAR[1] ONLY — no repaint.                              |
//| Max | 2026-04-13 | v1.0                                          |
//+------------------------------------------------------------------+
#property copyright "Max — EA_MultiJPY v1.0"
#property version   "1.00"
#property strict

//+------------------------------------------------------------------+
//| Inputs                                                            |
//+------------------------------------------------------------------+
input group "=== General ==="
input ulong    InpMagic         = 209001;
input int      InpDeviation     = 30;
input bool     InpKillSwitch    = false;

input group "=== Cross-Asset Settings ==="
input string   InpPair1         = "EURJPY+";     // Cross pair 1
input string   InpPair2         = "GBPJPY+";     // Cross pair 2
input string   InpPair3         = "AUDJPY+";     // Cross pair 3
input int      InpConfirmBars   = 1;             // Bars ago to read signal (1=last closed)
input double   InpMinMovePercent= 0.03;          // Min % move per pair to count

input group "=== Session Filter ==="
input int      InpStartHour     = 15;            // Trade start hour (server)
input int      InpEndHour       = 20;            // Trade end hour
input int      InpExitHour      = 22;            // Time stop hour

input group "=== Risk Management ==="
input double   InpRiskPct       = 0.50;
input double   InpMaxLot        = 1.0;
input double   InpSL_ATR_Mult   = 1.5;
input int      InpMinSLPoints   = 80;
input int      InpMaxSLPoints   = 600;
input double   InpTP_Ratio      = 1.0;
input int      InpMaxPerDay     = 2;
input double   InpDailyDD       = 4.0;

input group "=== Day Filters ==="
input bool     InpSkipMon       = true;
input bool     InpSkipFri       = true;

//+------------------------------------------------------------------+
//| Globals                                                           |
//+------------------------------------------------------------------+
int      g_hATR = INVALID_HANDLE;
datetime g_lastBar = 0;
int      g_tradesToday = 0;
int      g_lastTradeDay = -1;
double   g_dayStartBalance = 0;

int OnInit()
{
   g_hATR = iATR(_Symbol, PERIOD_CURRENT, 14);
   if(g_hATR == INVALID_HANDLE) { Print("[MJPY] ATR init fail"); return INIT_FAILED; }
   g_dayStartBalance = AccountInfoDouble(ACCOUNT_BALANCE);
   PrintFormat("[MJPY] EA_MultiJPY v1.00 | %s %s | Magic=%d", _Symbol, EnumToString(_Period), InpMagic);
   PrintFormat("[MJPY] Crosses: %s, %s, %s | MinMove=%.3f%%", InpPair1, InpPair2, InpPair3, InpMinMovePercent);
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
//| Get bar return for a symbol                                       |
//+------------------------------------------------------------------+
double GetBarReturn(string sym, int shift)
{
   double o = iOpen(sym, PERIOD_CURRENT, shift);
   double c = iClose(sym, PERIOD_CURRENT, shift);
   if(o <= 0) return 0;
   return (c - o) / o * 100.0;
}

//+------------------------------------------------------------------+
//| Check multi-JPY alignment                                         |
//| Returns: +1 = all JPY crosses up (JPY weakening, USDJPY should   |
//|               go UP), -1 = all down (JPY strengthening, USDJPY   |
//|               should go DOWN), 0 = no alignment                  |
//+------------------------------------------------------------------+
int CheckAlignment()
{
   int shift = InpConfirmBars;

   double r1 = GetBarReturn(InpPair1, shift);
   double r2 = GetBarReturn(InpPair2, shift);
   double r3 = GetBarReturn(InpPair3, shift);

   // All must exceed minimum threshold
   if(MathAbs(r1) < InpMinMovePercent) return 0;
   if(MathAbs(r2) < InpMinMovePercent) return 0;
   if(MathAbs(r3) < InpMinMovePercent) return 0;

   // All must agree on direction
   if(r1 > 0 && r2 > 0 && r3 > 0) return +1;  // all JPY crosses up = JPY weak = buy USDJPY
   if(r1 < 0 && r2 < 0 && r3 < 0) return -1;  // all JPY crosses down = JPY strong = sell USDJPY

   return 0;
}

//+------------------------------------------------------------------+
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

   int signal = CheckAlignment();
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
   sl = NormalizeDouble(sl, digits);
   tp = NormalizeDouble(tp, digits);

   MqlTradeRequest req = {}; MqlTradeResult res = {};
   req.action = TRADE_ACTION_DEAL; req.symbol = _Symbol;
   req.volume = lot;
   req.type = isBuy ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
   req.price = entry; req.sl = sl; req.tp = tp;
   req.deviation = (ulong)InpDeviation; req.magic = InpMagic;
   req.comment = StringFormat("MJPY|%s|r1=%.3f|r2=%.3f|r3=%.3f",
                              isBuy ? "BuyJPYweak" : "SellJPYstr",
                              GetBarReturn(InpPair1,InpConfirmBars),
                              GetBarReturn(InpPair2,InpConfirmBars),
                              GetBarReturn(InpPair3,InpConfirmBars));
   req.type_filling = ORDER_FILLING_FOK;
   if(!OrderSend(req, res))
   {
      req.type_filling = ORDER_FILLING_IOC;
      if(!OrderSend(req, res))
      {
         PrintFormat("[MJPY] OrderSend FAIL: err=%d retcode=%d", GetLastError(), res.retcode);
         return;
      }
   }
   if(res.retcode == TRADE_RETCODE_DONE || res.retcode == TRADE_RETCODE_PLACED)
   {
      g_tradesToday++;
      PrintFormat("[MJPY] %s %.2f @ %.5f | SL=%.5f TP=%.5f", isBuy?"BUY":"SELL", lot, res.price, sl, tp);
   }
}

double OnTester()
{
   double pf = TesterStatistics(STAT_PROFIT_FACTOR);
   double trades = TesterStatistics(STAT_TRADES);
   if(trades < 20) return 0;
   return pf * MathSqrt(trades);
}
