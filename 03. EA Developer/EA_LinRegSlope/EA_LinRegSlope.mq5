//+------------------------------------------------------------------+
//| EA_LinRegSlope.mq5 — Linear Regression Slope Momentum             |
//| Symbol: USDJPY+  |  Period: M15                                   |
//|                                                                   |
//| PARADIGM: Direct statistical trend measurement                     |
//| Instead of lagging indicators, use OLS linear regression slope    |
//| of recent N bars as the PUREST trend measure. When slope is       |
//| statistically significant (t-stat > threshold), the trend is      |
//| confirmed mathematically, not just by indicator crossover.        |
//|                                                                   |
//| Also uses R-squared of the regression: high R² = clean trend,    |
//| low R² = noisy/ranging. This acts as a built-in regime filter.   |
//|                                                                   |
//| Novelty: Type #88 — OLS linear regression slope + R² filter      |
//| SIGNALS ON BAR[1] ONLY — no repaint.                              |
//| Max | 2026-04-13 | v1.0                                          |
//+------------------------------------------------------------------+
#property copyright "Max — EA_LinRegSlope v1.0"
#property version   "1.00"
#property strict

input group "=== General ==="
input ulong    InpMagic         = 221001;
input int      InpDeviation     = 30;

input group "=== Linear Regression ==="
input int      InpRegLen        = 20;            // Regression lookback
input double   InpMinR2         = 0.30;          // Min R² for trend confirmation
input double   InpMinTStat      = 2.0;           // Min t-statistic for slope significance
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
   PrintFormat("[LINREG] v1.00 | Len=%d MinR2=%.2f MinTStat=%.1f", InpRegLen, InpMinR2, InpMinTStat);
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
//| OLS Linear Regression with R² and t-stat                          |
//| Returns: slope, r_squared, t_stat via reference parameters       |
//+------------------------------------------------------------------+
void ComputeLinReg(int shift, double &slope, double &r2, double &tstat)
{
   int N = InpRegLen;
   double sumX = 0, sumY = 0, sumXY = 0, sumX2 = 0, sumY2 = 0;

   for(int i = 0; i < N; i++)
   {
      double x = (double)i;
      double y = iClose(_Symbol, PERIOD_CURRENT, shift + N - 1 - i);  // oldest to newest
      sumX += x;
      sumY += y;
      sumXY += x * y;
      sumX2 += x * x;
      sumY2 += y * y;
   }

   double xMean = sumX / N;
   double yMean = sumY / N;
   double ssXX = sumX2 - N * xMean * xMean;
   double ssYY = sumY2 - N * yMean * yMean;
   double ssXY = sumXY - N * xMean * yMean;

   if(ssXX <= 0 || ssYY <= 0)
   {
      slope = 0; r2 = 0; tstat = 0;
      return;
   }

   slope = ssXY / ssXX;
   r2 = (ssXY * ssXY) / (ssXX * ssYY);

   // t-statistic for slope significance
   double sse = ssYY * (1.0 - r2);
   double mse = sse / (N - 2);
   double seBeta = MathSqrt(mse / ssXX);
   tstat = (seBeta > 0) ? MathAbs(slope) / seBeta : 0;
}

int GetSignal()
{
   double slope = 0, r2 = 0, tstat = 0;
   ComputeLinReg(1, slope, r2, tstat);

   // Require statistically significant trend with clean fit
   if(r2 < InpMinR2) return 0;      // Too noisy, no clean trend
   if(tstat < InpMinTStat) return 0; // Slope not significant

   // Trend bias
   double trend[];
   ArraySetAsSeries(trend, true);
   if(CopyBuffer(g_hTrend, 0, 1, 1, trend) < 1) return 0;
   double close1 = iClose(_Symbol, PERIOD_CURRENT, 1);

   if(slope > 0 && close1 > trend[0]) return +1;
   if(slope < 0 && close1 < trend[0]) return -1;
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
   double sl2=0, r22=0, ts2=0; ComputeLinReg(1,sl2,r22,ts2);
   req.comment=StringFormat("LR|s=%.5f r2=%.2f",sl2,r22);
   req.type_filling=ORDER_FILLING_FOK;
   if(!OrderSend(req,res)){req.type_filling=ORDER_FILLING_IOC;if(!OrderSend(req,res))return;}
   if(res.retcode==TRADE_RETCODE_DONE||res.retcode==TRADE_RETCODE_PLACED)
   { g_tradesToday++; PrintFormat("[LINREG] %s %.2f @ %.2f slope=%.6f R2=%.3f t=%.1f",isBuy?"BUY":"SELL",lot,res.price,sl2,r22,ts2); }
}

double OnTester()
{ double pf=TesterStatistics(STAT_PROFIT_FACTOR),n=TesterStatistics(STAT_TRADES); if(n<20) return 0; return pf*MathSqrt(n); }
