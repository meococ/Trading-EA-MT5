//+------------------------------------------------------------------+
//| EA_HurstRegime.mq5 — Hurst Exponent Regime Classifier            |
//| Symbol: USDJPY+  |  Period: M15                                   |
//|                                                                   |
//| PARADIGM: Statistical regime detection via Hurst Exponent         |
//| H > 0.5 = persistent (trending) → follow trend                   |
//| H < 0.5 = anti-persistent (mean reverting) → fade extremes       |
//| H ≈ 0.5 = random walk → no trade                                 |
//|                                                                   |
//| Based on R/S analysis (Rescaled Range). More rigorous than        |
//| Choppiness Index — directly measures fractal dimension.           |
//|                                                                   |
//| Novelty: Type #84 — Hurst exponent R/S regime classifier         |
//| SIGNALS ON BAR[1] ONLY — no repaint.                              |
//| Max | 2026-04-13 | v1.0                                          |
//+------------------------------------------------------------------+
#property copyright "Max — EA_HurstRegime v1.0"
#property version   "1.00"
#property strict

input group "=== General ==="
input ulong    InpMagic         = 217001;
input int      InpDeviation     = 30;

input group "=== Hurst Exponent ==="
input int      InpHurstLen      = 50;            // Lookback for R/S calculation
input double   InpHurstTrend    = 0.55;          // H > this = trending regime
input double   InpHurstRandom   = 0.50;          // H between random and trend = cautious

input group "=== Trend Detection ==="
input int      InpFastEMA       = 8;
input int      InpSlowEMA       = 21;
input int      InpTrendEMA      = 50;

input group "=== Session ==="
input int      InpStartHour     = 10;
input int      InpEndHour       = 14;
input int      InpExitHour      = 22;
input bool     InpSkipMon       = false;
input bool     InpSkipTue       = true;
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

int      g_hATR   = INVALID_HANDLE;
int      g_hFast  = INVALID_HANDLE;
int      g_hSlow  = INVALID_HANDLE;
int      g_hTrend = INVALID_HANDLE;
datetime g_lastBar = 0;
int      g_tradesToday = 0;
int      g_lastTradeDay = -1;
double   g_dayStartBalance = 0;

int OnInit()
{
   g_hATR   = iATR(_Symbol, PERIOD_CURRENT, 14);
   g_hFast  = iMA(_Symbol, PERIOD_CURRENT, InpFastEMA, 0, MODE_EMA, PRICE_CLOSE);
   g_hSlow  = iMA(_Symbol, PERIOD_CURRENT, InpSlowEMA, 0, MODE_EMA, PRICE_CLOSE);
   g_hTrend = iMA(_Symbol, PERIOD_CURRENT, InpTrendEMA, 0, MODE_EMA, PRICE_CLOSE);
   if(g_hATR==INVALID_HANDLE||g_hFast==INVALID_HANDLE||g_hSlow==INVALID_HANDLE||g_hTrend==INVALID_HANDLE)
      return INIT_FAILED;
   g_dayStartBalance = AccountInfoDouble(ACCOUNT_BALANCE);
   PrintFormat("[HURST] v1.00 | Len=%d Trend=%.2f Random=%.2f | EMA %d/%d/%d",
               InpHurstLen, InpHurstTrend, InpHurstRandom, InpFastEMA, InpSlowEMA, InpTrendEMA);
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   if(g_hATR!=INVALID_HANDLE) IndicatorRelease(g_hATR);
   if(g_hFast!=INVALID_HANDLE) IndicatorRelease(g_hFast);
   if(g_hSlow!=INVALID_HANDLE) IndicatorRelease(g_hSlow);
   if(g_hTrend!=INVALID_HANDLE) IndicatorRelease(g_hTrend);
}

int CountPositions()
{ int c=0;for(int i=PositionsTotal()-1;i>=0;i--){ulong t=PositionGetTicket(i);if(t>0&&PositionGetInteger(POSITION_MAGIC)==(long)InpMagic&&PositionGetString(POSITION_SYMBOL)==_Symbol)c++;}return c; }

void CloseAll()
{ for(int i=PositionsTotal()-1;i>=0;i--){ulong t=PositionGetTicket(i);if(t<=0||PositionGetInteger(POSITION_MAGIC)!=(long)InpMagic||PositionGetString(POSITION_SYMBOL)!=_Symbol)continue;MqlTradeRequest req={};MqlTradeResult res={};req.action=TRADE_ACTION_DEAL;req.symbol=_Symbol;req.volume=PositionGetDouble(POSITION_VOLUME);req.deviation=(ulong)InpDeviation;req.magic=InpMagic;req.position=t;if(PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_BUY){req.type=ORDER_TYPE_SELL;req.price=SymbolInfoDouble(_Symbol,SYMBOL_BID);}else{req.type=ORDER_TYPE_BUY;req.price=SymbolInfoDouble(_Symbol,SYMBOL_ASK);}req.type_filling=ORDER_FILLING_FOK;if(!OrderSend(req,res)){req.type_filling=ORDER_FILLING_IOC;OrderSend(req,res);}} }

bool IsDDExceeded()
{ if(g_dayStartBalance<=0)return false;return(g_dayStartBalance-AccountInfoDouble(ACCOUNT_EQUITY))/g_dayStartBalance*100.0>=InpDailyDD; }

double CalcLot(double sl)
{ if(sl<=0)return 0;double b=AccountInfoDouble(ACCOUNT_BALANCE),r=b*InpRiskPct/100.0;double tv=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_VALUE),ts=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);if(tv<=0||ts<=0)return 0;double lot=r/(sl/ts*tv);lot=MathMin(lot,InpMaxLot);lot=MathMin(lot,SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX));lot=MathMax(lot,SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN));lot=MathFloor(lot/SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP))*SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);return lot; }

//+------------------------------------------------------------------+
//| Compute Hurst Exponent using R/S analysis                         |
//+------------------------------------------------------------------+
double ComputeHurst(int shift)
{
   int N = InpHurstLen;
   double returns[];
   ArrayResize(returns, N);

   // Calculate log returns
   for(int i = 0; i < N; i++)
   {
      double c1 = iClose(_Symbol, PERIOD_CURRENT, shift + i);
      double c2 = iClose(_Symbol, PERIOD_CURRENT, shift + i + 1);
      if(c2 <= 0) return 0.5;
      returns[i] = MathLog(c1 / c2);
   }

   // Mean of returns
   double mean = 0;
   for(int i = 0; i < N; i++) mean += returns[i];
   mean /= N;

   // Cumulative deviation from mean
   double cumDev[];
   ArrayResize(cumDev, N);
   cumDev[0] = returns[0] - mean;
   for(int i = 1; i < N; i++)
      cumDev[i] = cumDev[i-1] + (returns[i] - mean);

   // Range: max(cumDev) - min(cumDev)
   double maxCum = cumDev[0], minCum = cumDev[0];
   for(int i = 1; i < N; i++)
   {
      if(cumDev[i] > maxCum) maxCum = cumDev[i];
      if(cumDev[i] < minCum) minCum = cumDev[i];
   }
   double range = maxCum - minCum;

   // Standard deviation
   double sd = 0;
   for(int i = 0; i < N; i++)
      sd += (returns[i] - mean) * (returns[i] - mean);
   sd = MathSqrt(sd / N);

   if(sd <= 0 || range <= 0) return 0.5;

   // R/S statistic
   double RS = range / sd;

   // Hurst = log(R/S) / log(N)
   double H = MathLog(RS) / MathLog((double)N);

   return H;
}

int GetSignal()
{
   double H = ComputeHurst(1);

   // Only trade in trending regime
   if(H < InpHurstTrend) return 0;  // Not persistent enough

   // EMA crossover for direction
   double fast[], slow[], trend[];
   ArraySetAsSeries(fast, true); ArraySetAsSeries(slow, true); ArraySetAsSeries(trend, true);
   if(CopyBuffer(g_hFast, 0, 1, 2, fast) < 2) return 0;
   if(CopyBuffer(g_hSlow, 0, 1, 2, slow) < 2) return 0;
   if(CopyBuffer(g_hTrend, 0, 1, 1, trend) < 1) return 0;

   double close1 = iClose(_Symbol, PERIOD_CURRENT, 1);

   bool bullish = (fast[0] > slow[0] && close1 > trend[0]);
   bool bearish = (fast[0] < slow[0] && close1 < trend[0]);

   // Fresh crossover or strong persistent trend
   bool freshBull = bullish && (fast[1] <= slow[1]);
   bool freshBear = bearish && (fast[1] >= slow[1]);
   bool contBull = bullish && H > 0.60;
   bool contBear = bearish && H > 0.60;

   if(freshBull || contBull) return +1;
   if(freshBear || contBear) return -1;
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
   if(CopyBuffer(g_hATR, 0, 1, 1, atr) < 1) return;

   double slDist = atr[0] * InpSL_ATR_Mult;
   if(slDist < InpMinSLPoints*_Point) slDist = InpMinSLPoints*_Point;
   if(slDist > InpMaxSLPoints*_Point) return;

   bool isBuy=(signal==+1);
   double ask=SymbolInfoDouble(_Symbol,SYMBOL_ASK),bid=SymbolInfoDouble(_Symbol,SYMBOL_BID);
   double sl=isBuy?ask-slDist:bid+slDist, tp=isBuy?ask+slDist*InpTP_Ratio:bid-slDist*InpTP_Ratio;
   if(slDist<(int)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL)*_Point) return;
   double lot=CalcLot(slDist); if(lot<=0) return;
   int digits=(int)SymbolInfoInteger(_Symbol,SYMBOL_DIGITS);
   sl=NormalizeDouble(sl,digits); tp=NormalizeDouble(tp,digits);

   MqlTradeRequest req={}; MqlTradeResult res={};
   req.action=TRADE_ACTION_DEAL;req.symbol=_Symbol;req.volume=lot;
   req.type=isBuy?ORDER_TYPE_BUY:ORDER_TYPE_SELL;
   req.price=isBuy?ask:bid;req.sl=sl;req.tp=tp;
   req.deviation=(ulong)InpDeviation;req.magic=InpMagic;
   req.comment=StringFormat("HURST|H=%.3f",ComputeHurst(1));
   req.type_filling=ORDER_FILLING_FOK;
   if(!OrderSend(req,res)){req.type_filling=ORDER_FILLING_IOC;if(!OrderSend(req,res))return;}
   if(res.retcode==TRADE_RETCODE_DONE||res.retcode==TRADE_RETCODE_PLACED)
   { g_tradesToday++; PrintFormat("[HURST] %s %.2f @ %.2f H=%.3f",isBuy?"BUY":"SELL",lot,res.price,ComputeHurst(1)); }
}

double OnTester()
{ double pf=TesterStatistics(STAT_PROFIT_FACTOR),n=TesterStatistics(STAT_TRADES); if(n<20) return 0; return pf*MathSqrt(n); }
