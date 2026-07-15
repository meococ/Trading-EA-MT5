//+------------------------------------------------------------------+
//| EA_AutoCorr.mq5 — Serial Autocorrelation Momentum                 |
//| Symbol: USDJPY+  |  Period: M15                                   |
//|                                                                   |
//| PARADIGM: Statistical autocorrelation in returns                   |
//| When lag-1 autocorrelation is significantly positive, returns      |
//| are persistent → follow the recent direction.                      |
//| When lag-1 AC ≈ 0, market is random walk → no trade.              |
//|                                                                   |
//| This is theoretically the PUREST momentum signal:                  |
//| - No indicator lag (operates on raw returns)                       |
//| - Mathematical foundation (Lo & MacKinlay 1988 variance ratio)    |
//| - Directly measures return persistence, not price level            |
//|                                                                   |
//| Novelty: Type #85 — Return autocorrelation momentum               |
//| SIGNALS ON BAR[1] ONLY — no repaint.                              |
//| Max | 2026-04-13 | v1.0                                          |
//+------------------------------------------------------------------+
#property copyright "Max — EA_AutoCorr v1.0"
#property version   "1.00"
#property strict

input group "=== General ==="
input ulong    InpMagic         = 218001;
input int      InpDeviation     = 30;

input group "=== Autocorrelation ==="
input int      InpACLen         = 20;            // Lookback for AC calculation
input double   InpACThresh      = 0.20;          // Min AC(1) to consider persistent
input int      InpMomentumBars  = 5;             // Bars to measure recent direction

input group "=== Trend ==="
input int      InpTrendEMA      = 50;            // Trend bias filter

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
int      g_hTrend = INVALID_HANDLE;
datetime g_lastBar = 0;
int      g_tradesToday = 0;
int      g_lastTradeDay = -1;
double   g_dayStartBalance = 0;

int OnInit()
{
   g_hATR   = iATR(_Symbol, PERIOD_CURRENT, 14);
   g_hTrend = iMA(_Symbol, PERIOD_CURRENT, InpTrendEMA, 0, MODE_EMA, PRICE_CLOSE);
   if(g_hATR==INVALID_HANDLE||g_hTrend==INVALID_HANDLE) return INIT_FAILED;
   g_dayStartBalance = AccountInfoDouble(ACCOUNT_BALANCE);
   PrintFormat("[AC] v1.00 | Len=%d Thresh=%.2f MomBars=%d", InpACLen, InpACThresh, InpMomentumBars);
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   if(g_hATR!=INVALID_HANDLE) IndicatorRelease(g_hATR);
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
//| Compute lag-1 autocorrelation of returns                          |
//| Returns: AC(1) value [-1, +1]                                    |
//| Positive = persistent (momentum). Negative = mean-reverting.     |
//+------------------------------------------------------------------+
double ComputeAC1(int shift)
{
   int N = InpACLen;
   double returns[];
   ArrayResize(returns, N);

   // Log returns from bar[shift] backwards
   for(int i = 0; i < N; i++)
   {
      double c1 = iClose(_Symbol, PERIOD_CURRENT, shift + i);
      double c2 = iClose(_Symbol, PERIOD_CURRENT, shift + i + 1);
      if(c2 <= 0) return 0;
      returns[i] = MathLog(c1 / c2);
   }

   // Mean
   double mean = 0;
   for(int i = 0; i < N; i++) mean += returns[i];
   mean /= N;

   // AC(1) = Cov(r_t, r_{t-1}) / Var(r_t)
   double cov = 0, var = 0;
   for(int i = 0; i < N - 1; i++)
   {
      cov += (returns[i] - mean) * (returns[i+1] - mean);
      var += (returns[i] - mean) * (returns[i] - mean);
   }
   // Last variance term
   var += (returns[N-1] - mean) * (returns[N-1] - mean);

   if(var <= 0) return 0;
   return cov / var;  // AC(1)
}

int GetSignal()
{
   double ac = ComputeAC1(1);

   // Only trade when returns are PERSISTENT
   if(ac < InpACThresh) return 0;

   // Recent momentum direction
   double momentum = iClose(_Symbol, PERIOD_CURRENT, 1) - iClose(_Symbol, PERIOD_CURRENT, 1 + InpMomentumBars);

   // Trend bias
   double trend[];
   ArraySetAsSeries(trend, true);
   if(CopyBuffer(g_hTrend, 0, 1, 1, trend) < 1) return 0;
   double close1 = iClose(_Symbol, PERIOD_CURRENT, 1);

   bool upTrend = (close1 > trend[0]);
   bool downTrend = (close1 < trend[0]);

   if(momentum > 0 && upTrend) return +1;
   if(momentum < 0 && downTrend) return -1;
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
   req.comment=StringFormat("AC|ac=%.3f",ComputeAC1(1));
   req.type_filling=ORDER_FILLING_FOK;
   if(!OrderSend(req,res)){req.type_filling=ORDER_FILLING_IOC;if(!OrderSend(req,res))return;}
   if(res.retcode==TRADE_RETCODE_DONE||res.retcode==TRADE_RETCODE_PLACED)
   { g_tradesToday++; PrintFormat("[AC] %s %.2f @ %.2f AC=%.3f",isBuy?"BUY":"SELL",lot,res.price,ComputeAC1(1)); }
}

double OnTester()
{ double pf=TesterStatistics(STAT_PROFIT_FACTOR),n=TesterStatistics(STAT_TRADES); if(n<20) return 0; return pf*MathSqrt(n); }
