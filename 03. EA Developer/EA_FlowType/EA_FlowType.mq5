//+------------------------------------------------------------------+
//| EA_FlowType.mq5 — M1 Bar Count Microstructure Proxy              |
//| Symbol: XAUUSD+  |  Period: M15  |  Style: Flow classification    |
//|                                                                   |
//| EDGE HYPOTHESIS:                                                  |
//| Institutional execution creates smooth distributed orders across  |
//| all M1 bars within an M15 bar. Retail/algo spikes concentrate    |
//| the move in 1-2 M1 bars. By counting how many M1 bars have      |
//| directional body (close > open for bull), we can distinguish     |
//| "institutional flow" bars (high M1 agreement) from "spike" bars. |
//|                                                                   |
//| Signal: When 11+ of 15 M1 bars agree on direction AND the M15   |
//| bar has a meaningful body → trade in that direction on next bar. |
//|                                                                   |
//| DISTINCT FROM:                                                    |
//| - CVD Divergence: used close-open/high-low ratio as CVD proxy   |
//| - All indicator-based entries: no indicators used here            |
//| - Session breakout: not using session range boundaries            |
//|                                                                   |
//| Novelty: Type #80 — M1 microstructure flow classification        |
//| SIGNALS ON BAR[1] ONLY — no repaint.                              |
//| Max | 2026-04-13 | v1.0                                          |
//+------------------------------------------------------------------+
#property copyright "Max — EA_FlowType v1.0"
#property version   "1.00"
#property strict

input group "=== General ==="
input ulong    InpMagic         = 213001;
input int      InpDeviation     = 30;
input bool     InpKillSwitch    = false;

input group "=== Flow Detection ==="
input int      InpMinAgreement  = 11;            // Min M1 bars agreeing on direction (of 15)
input double   InpMinBodyPct    = 0.40;          // Min M15 body % of range to qualify
input double   InpMinRangePct   = 0.03;          // Min M15 range as % of price

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
   if(g_hATR == INVALID_HANDLE) { Print("[FLOW] ATR init fail"); return INIT_FAILED; }
   g_dayStartBalance = AccountInfoDouble(ACCOUNT_BALANCE);
   PrintFormat("[FLOW] v1.00 | %s %s | Magic=%d", _Symbol, EnumToString(_Period), InpMagic);
   PrintFormat("[FLOW] MinAgreement=%d/15 | MinBody=%.1f%% | MinRange=%.2f%%",
               InpMinAgreement, InpMinBodyPct * 100, InpMinRangePct);
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
//| Analyze M1 bars within the last completed M15 bar                 |
//| Returns: +1 institutional buy, -1 institutional sell, 0 none     |
//+------------------------------------------------------------------+
int AnalyzeFlowType()
{
   // Get the M15 bar[1] properties
   double m15Open  = iOpen(_Symbol, PERIOD_M15, 1);
   double m15Close = iClose(_Symbol, PERIOD_M15, 1);
   double m15High  = iHigh(_Symbol, PERIOD_M15, 1);
   double m15Low   = iLow(_Symbol, PERIOD_M15, 1);

   if(m15High <= m15Low || m15Open <= 0) return 0;

   double m15Range = m15High - m15Low;
   double m15Body  = MathAbs(m15Close - m15Open);

   // Check minimum range (avoid tiny bars)
   if(m15Range / m15Open * 100.0 < InpMinRangePct) return 0;

   // Check minimum body ratio
   if(m15Body / m15Range < InpMinBodyPct) return 0;

   // Now read M1 bars that compose this M15 bar
   datetime m15Time = iTime(_Symbol, PERIOD_M15, 1);

   // Count M1 bars with directional agreement
   int bullBars = 0;
   int bearBars = 0;
   int totalM1 = 0;

   for(int i = 0; i < 20; i++)  // search up to 20 M1 bars to find the 15 within our M15
   {
      datetime m1Time = iTime(_Symbol, PERIOD_M1, i);
      if(m1Time < m15Time) break;          // past our M15 bar
      if(m1Time >= m15Time + 15 * 60) continue;  // ahead of our M15 bar

      double m1Open  = iOpen(_Symbol, PERIOD_M1, i);
      double m1Close = iClose(_Symbol, PERIOD_M1, i);
      if(m1Open <= 0) continue;

      totalM1++;
      if(m1Close > m1Open) bullBars++;
      else if(m1Close < m1Open) bearBars++;
   }

   if(totalM1 < 10) return 0;  // not enough M1 data

   // Check for strong agreement
   bool m15IsBull = (m15Close > m15Open);

   if(m15IsBull && bullBars >= InpMinAgreement)
   {
      PrintFormat("[FLOW] INSTITUTIONAL BUY: %d/%d M1 bars bullish, M15 body=%.1f%% of range",
                  bullBars, totalM1, m15Body / m15Range * 100);
      return +1;
   }

   if(!m15IsBull && bearBars >= InpMinAgreement)
   {
      PrintFormat("[FLOW] INSTITUTIONAL SELL: %d/%d M1 bars bearish, M15 body=%.1f%% of range",
                  bearBars, totalM1, m15Body / m15Range * 100);
      return -1;
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

   int signal = AnalyzeFlowType();
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
   req.comment = StringFormat("FLOW|%s|inst", isBuy ? "BuyFlow" : "SellFlow");
   req.type_filling = ORDER_FILLING_FOK;
   if(!OrderSend(req, res))
   {
      req.type_filling = ORDER_FILLING_IOC;
      if(!OrderSend(req, res))
      { PrintFormat("[FLOW] FAIL: err=%d", GetLastError()); return; }
   }
   if(res.retcode == TRADE_RETCODE_DONE || res.retcode == TRADE_RETCODE_PLACED)
   {
      g_tradesToday++;
      PrintFormat("[FLOW] %s %.2f @ %.2f | SL=%.2f TP=%.2f",
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
