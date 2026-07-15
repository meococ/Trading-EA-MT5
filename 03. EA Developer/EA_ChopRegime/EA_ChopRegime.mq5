//+------------------------------------------------------------------+
//| EA_ChopRegime.mq5 — Choppiness Index Regime Classifier           |
//| Symbol: XAUUSD+ / USDJPY+  |  Period: M15                        |
//|                                                                   |
//| PARADIGM SHIFT: Regime Classification                             |
//| Instead of "always on" trading, this EA stays SILENT when the     |
//| market is choppy (random walk) and only activates during          |
//| confirmed trending regimes.                                       |
//|                                                                   |
//| Choppiness Index: CI = 100 * LOG10(SUM(ATR,N) / Range(N)) / LOG10(N)
//| CI > 61.8 → choppy/ranging → NO TRADE                           |
//| CI < 38.2 → trending → trade momentum with EMA                   |
//| 38.2 < CI < 61.8 → transitional → cautious                      |
//|                                                                   |
//| Direction: EMA fast/slow crossover, confirmed by Choppiness.      |
//|                                                                   |
//| Novelty: Type #82 — Choppiness regime + conditional momentum     |
//| SIGNALS ON BAR[1] ONLY — no repaint.                              |
//| Max | 2026-04-13 | v1.0                                          |
//+------------------------------------------------------------------+
#property copyright "Max — EA_ChopRegime v1.0"
#property version   "1.00"
#property strict

input group "=== General ==="
input ulong    InpMagic         = 215001;
input int      InpDeviation     = 30;

input group "=== Choppiness Index ==="
input int      InpChopPeriod    = 14;            // Choppiness lookback
input double   InpChopLow       = 38.2;          // Below = trending
input double   InpChopHigh      = 50.0;          // Above = choppy (relaxed from 61.8)

input group "=== Trend Detection ==="
input int      InpFastEMA       = 8;
input int      InpSlowEMA       = 21;
input int      InpTrendEMA      = 50;            // Higher TF trend bias

input group "=== Session ==="
input int      InpStartHour     = 10;
input int      InpEndHour       = 20;
input int      InpExitHour      = 22;
input bool     InpSkipMon       = true;
input bool     InpSkipTue       = false;
input bool     InpSkipWed       = false;
input bool     InpSkipThu       = false;
input bool     InpSkipFri       = true;

input group "=== Risk ==="
input double   InpRiskPct       = 0.50;
input double   InpMaxLot        = 1.0;
input double   InpSL_ATR_Mult   = 1.5;
input int      InpMinSLPoints   = 100;
input int      InpMaxSLPoints   = 1000;
input double   InpTP_Ratio      = 1.5;
input int      InpMaxPerDay     = 2;
input double   InpDailyDD       = 4.0;

int      g_hATR14 = INVALID_HANDLE;
int      g_hATR1  = INVALID_HANDLE;    // ATR(1) for Choppiness calculation
int      g_hFast  = INVALID_HANDLE;
int      g_hSlow  = INVALID_HANDLE;
int      g_hTrend = INVALID_HANDLE;
datetime g_lastBar = 0;
int      g_tradesToday = 0;
int      g_lastTradeDay = -1;
double   g_dayStartBalance = 0;

int OnInit()
{
   g_hATR14 = iATR(_Symbol, PERIOD_CURRENT, 14);
   g_hATR1  = iATR(_Symbol, PERIOD_CURRENT, 1);
   g_hFast  = iMA(_Symbol, PERIOD_CURRENT, InpFastEMA, 0, MODE_EMA, PRICE_CLOSE);
   g_hSlow  = iMA(_Symbol, PERIOD_CURRENT, InpSlowEMA, 0, MODE_EMA, PRICE_CLOSE);
   g_hTrend = iMA(_Symbol, PERIOD_CURRENT, InpTrendEMA, 0, MODE_EMA, PRICE_CLOSE);
   if(g_hATR14==INVALID_HANDLE||g_hATR1==INVALID_HANDLE||g_hFast==INVALID_HANDLE
      ||g_hSlow==INVALID_HANDLE||g_hTrend==INVALID_HANDLE) return INIT_FAILED;
   g_dayStartBalance = AccountInfoDouble(ACCOUNT_BALANCE);
   PrintFormat("[CHOP] v1.00 | ChopPeriod=%d Low=%.1f High=%.1f | EMA %d/%d/%d",
               InpChopPeriod, InpChopLow, InpChopHigh, InpFastEMA, InpSlowEMA, InpTrendEMA);
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   if(g_hATR14!=INVALID_HANDLE) IndicatorRelease(g_hATR14);
   if(g_hATR1!=INVALID_HANDLE)  IndicatorRelease(g_hATR1);
   if(g_hFast!=INVALID_HANDLE)  IndicatorRelease(g_hFast);
   if(g_hSlow!=INVALID_HANDLE)  IndicatorRelease(g_hSlow);
   if(g_hTrend!=INVALID_HANDLE) IndicatorRelease(g_hTrend);
}

int CountPositions()
{ int c=0; for(int i=PositionsTotal()-1;i>=0;i--){ulong t=PositionGetTicket(i);if(t>0&&PositionGetInteger(POSITION_MAGIC)==(long)InpMagic&&PositionGetString(POSITION_SYMBOL)==_Symbol)c++;} return c; }

void CloseAll()
{ for(int i=PositionsTotal()-1;i>=0;i--){ulong t=PositionGetTicket(i);if(t<=0||PositionGetInteger(POSITION_MAGIC)!=(long)InpMagic||PositionGetString(POSITION_SYMBOL)!=_Symbol)continue;MqlTradeRequest req={};MqlTradeResult res={};req.action=TRADE_ACTION_DEAL;req.symbol=_Symbol;req.volume=PositionGetDouble(POSITION_VOLUME);req.deviation=(ulong)InpDeviation;req.magic=InpMagic;req.position=t;if(PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_BUY){req.type=ORDER_TYPE_SELL;req.price=SymbolInfoDouble(_Symbol,SYMBOL_BID);}else{req.type=ORDER_TYPE_BUY;req.price=SymbolInfoDouble(_Symbol,SYMBOL_ASK);}req.type_filling=ORDER_FILLING_FOK;if(!OrderSend(req,res)){req.type_filling=ORDER_FILLING_IOC;OrderSend(req,res);}} }

bool IsDDExceeded()
{ if(g_dayStartBalance<=0)return false; return(g_dayStartBalance-AccountInfoDouble(ACCOUNT_EQUITY))/g_dayStartBalance*100.0>=InpDailyDD; }

double CalcLot(double sl)
{ if(sl<=0)return 0;double b=AccountInfoDouble(ACCOUNT_BALANCE),r=b*InpRiskPct/100.0;double tv=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_VALUE),ts=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);if(tv<=0||ts<=0)return 0;double lot=r/(sl/ts*tv);lot=MathMin(lot,InpMaxLot);lot=MathMin(lot,SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX));lot=MathMax(lot,SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN));lot=MathFloor(lot/SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP))*SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);return lot; }

//+------------------------------------------------------------------+
//| Compute Choppiness Index for bar[shift]                           |
//+------------------------------------------------------------------+
double ComputeChoppiness(int shift)
{
   // Sum of ATR(1) over period
   double atrSum = 0;
   double atr1[];
   ArraySetAsSeries(atr1, true);
   if(CopyBuffer(g_hATR1, 0, shift, InpChopPeriod, atr1) < InpChopPeriod) return 50.0;

   for(int i = 0; i < InpChopPeriod; i++)
      atrSum += atr1[i];

   // Highest high - lowest low over period
   double hh = -999999, ll = 999999;
   for(int i = shift; i < shift + InpChopPeriod; i++)
   {
      double h = iHigh(_Symbol, PERIOD_CURRENT, i);
      double l = iLow(_Symbol, PERIOD_CURRENT, i);
      if(h > hh) hh = h;
      if(l < ll) ll = l;
   }

   double range = hh - ll;
   if(range <= 0 || atrSum <= 0) return 50.0;

   double ci = 100.0 * MathLog10(atrSum / range) / MathLog10((double)InpChopPeriod);
   return ci;
}

int GetSignal()
{
   double ci = ComputeChoppiness(1);

   // Only trade when market is TRENDING
   if(ci > InpChopHigh) return 0;  // Too choppy
   // ci < InpChopLow = strong trend, ci between low-high = moderate trend (both OK)

   // EMA crossover for direction
   double fast[], slow[], trend[];
   ArraySetAsSeries(fast, true); ArraySetAsSeries(slow, true); ArraySetAsSeries(trend, true);
   if(CopyBuffer(g_hFast, 0, 1, 2, fast) < 2) return 0;
   if(CopyBuffer(g_hSlow, 0, 1, 2, slow) < 2) return 0;
   if(CopyBuffer(g_hTrend, 0, 1, 1, trend) < 1) return 0;

   double close1 = iClose(_Symbol, PERIOD_CURRENT, 1);

   // Fast EMA above slow = bullish, AND price above trend EMA
   bool bullish = (fast[0] > slow[0] && close1 > trend[0]);
   bool bearish = (fast[0] < slow[0] && close1 < trend[0]);

   // Require fresh crossover (not just persistent state)
   bool freshBull = bullish && (fast[1] <= slow[1]);
   bool freshBear = bearish && (fast[1] >= slow[1]);

   // Or: strong trend continuation (already crossed, CI confirming)
   bool contBull = bullish && ci < InpChopLow;
   bool contBear = bearish && ci < InpChopLow;

   if(freshBull || contBull)
   {
      PrintFormat("[CHOP] BUY: CI=%.1f Fast=%.5f>Slow=%.5f fresh=%s cont=%s",
                  ci, fast[0], slow[0], freshBull?"Y":"N", contBull?"Y":"N");
      return +1;
   }
   if(freshBear || contBear)
   {
      PrintFormat("[CHOP] SELL: CI=%.1f Fast=%.5f<Slow=%.5f fresh=%s cont=%s",
                  ci, fast[0], slow[0], freshBear?"Y":"N", contBear?"Y":"N");
      return -1;
   }

   return 0;
}

void OnTick()
{
   datetime barTime = iTime(_Symbol, PERIOD_CURRENT, 0);
   if(barTime == g_lastBar) return;
   g_lastBar = barTime;

   MqlDateTime dt; TimeToStruct(barTime, dt);
   if(dt.day_of_year != g_lastTradeDay)
   { g_lastTradeDay=dt.day_of_year; g_tradesToday=0; g_dayStartBalance=AccountInfoDouble(ACCOUNT_BALANCE); }

   if(dt.hour >= InpExitHour && CountPositions() > 0) { CloseAll(); return; }
   if(dt.hour < InpStartHour || dt.hour >= InpEndHour) return;
   if(g_tradesToday >= InpMaxPerDay || CountPositions() > 0 || IsDDExceeded()) return;
   if(InpSkipMon && dt.day_of_week == 1) return;
   if(InpSkipTue && dt.day_of_week == 2) return;
   if(InpSkipWed && dt.day_of_week == 3) return;
   if(InpSkipThu && dt.day_of_week == 4) return;
   if(InpSkipFri && dt.day_of_week == 5) return;

   int signal = GetSignal();
   if(signal == 0) return;

   double atr[];
   ArraySetAsSeries(atr, true);
   if(CopyBuffer(g_hATR14, 0, 1, 1, atr) < 1) return;

   double slDist = atr[0] * InpSL_ATR_Mult;
   if(slDist < InpMinSLPoints*_Point) slDist = InpMinSLPoints*_Point;
   if(slDist > InpMaxSLPoints*_Point) return;

   bool isBuy=(signal==+1);
   double ask=SymbolInfoDouble(_Symbol,SYMBOL_ASK),bid=SymbolInfoDouble(_Symbol,SYMBOL_BID);
   double entry=isBuy?ask:bid;
   double sl=isBuy?ask-slDist:bid+slDist, tp=isBuy?ask+slDist*InpTP_Ratio:bid-slDist*InpTP_Ratio;
   if(slDist<(int)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL)*_Point) return;
   double lot=CalcLot(slDist); if(lot<=0) return;
   int digits=(int)SymbolInfoInteger(_Symbol,SYMBOL_DIGITS);
   sl=NormalizeDouble(sl,digits); tp=NormalizeDouble(tp,digits);

   MqlTradeRequest req={}; MqlTradeResult res={};
   req.action=TRADE_ACTION_DEAL;req.symbol=_Symbol;req.volume=lot;
   req.type=isBuy?ORDER_TYPE_BUY:ORDER_TYPE_SELL;
   req.price=entry;req.sl=sl;req.tp=tp;
   req.deviation=(ulong)InpDeviation;req.magic=InpMagic;
   req.comment=StringFormat("CHOP|CI=%.1f",ComputeChoppiness(1));
   req.type_filling=ORDER_FILLING_FOK;
   if(!OrderSend(req,res)){req.type_filling=ORDER_FILLING_IOC;if(!OrderSend(req,res))return;}
   if(res.retcode==TRADE_RETCODE_DONE||res.retcode==TRADE_RETCODE_PLACED)
   { g_tradesToday++; PrintFormat("[CHOP] %s %.2f @ %.2f CI=%.1f",isBuy?"BUY":"SELL",lot,res.price,ComputeChoppiness(1)); }
}

double OnTester()
{ double pf=TesterStatistics(STAT_PROFIT_FACTOR),n=TesterStatistics(STAT_TRADES); if(n<20) return 0; return pf*MathSqrt(n); }
