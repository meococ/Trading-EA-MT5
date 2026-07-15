//+------------------------------------------------------------------+
//| EA_VolCluster.mq5 — Volatility Clustering Breakout                |
//| Symbol: USDJPY+/XAUUSD+  |  Period: M15                          |
//|                                                                   |
//| PARADIGM: GARCH volatility clustering                              |
//| High volatility clusters → after a quiet period, the first        |
//| significant move is likely to continue (vol expansion breakout).  |
//| After a volatile period, fade extremes (vol contraction revert).  |
//|                                                                   |
//| Uses realized volatility ratio: RV(short)/RV(long) to detect     |
//| vol expansion/contraction transitions.                            |
//|                                                                   |
//| Novelty: Type #86 — Volatility ratio regime + directional breakout|
//| SIGNALS ON BAR[1] ONLY — no repaint.                              |
//| Max | 2026-04-13 | v1.0                                          |
//+------------------------------------------------------------------+
#property copyright "Max — EA_VolCluster v1.0"
#property version   "1.00"
#property strict

input group "=== General ==="
input ulong    InpMagic         = 219001;
input int      InpDeviation     = 30;

input group "=== Volatility Clustering ==="
input int      InpRVShort       = 5;             // Short-term RV window
input int      InpRVLong        = 20;            // Long-term RV window
input double   InpExpansionMult = 1.50;          // RV ratio > this = vol expansion
input double   InpContractionMult = 0.60;        // RV ratio < this = vol contraction (quiet)
input int      InpBreakoutBars  = 3;             // Bars to confirm breakout direction

input group "=== Trend ==="
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
   PrintFormat("[VOLC] v1.00 | RVShort=%d RVLong=%d ExpMult=%.2f ContrMult=%.2f",
               InpRVShort, InpRVLong, InpExpansionMult, InpContractionMult);
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
//| Compute Realized Volatility (std dev of returns)                  |
//+------------------------------------------------------------------+
double ComputeRV(int shift, int window)
{
   double returns[];
   ArrayResize(returns, window);

   for(int i = 0; i < window; i++)
   {
      double c1 = iClose(_Symbol, PERIOD_CURRENT, shift + i);
      double c2 = iClose(_Symbol, PERIOD_CURRENT, shift + i + 1);
      if(c2 <= 0) return 0;
      returns[i] = MathLog(c1 / c2);
   }

   double mean = 0;
   for(int i = 0; i < window; i++) mean += returns[i];
   mean /= window;

   double var = 0;
   for(int i = 0; i < window; i++)
      var += (returns[i] - mean) * (returns[i] - mean);

   return MathSqrt(var / window);
}

int GetSignal()
{
   double rvShort = ComputeRV(1, InpRVShort);
   double rvLong  = ComputeRV(1, InpRVLong);

   if(rvLong <= 0) return 0;
   double ratio = rvShort / rvLong;

   // Vol EXPANSION: recent vol > long-term vol → breakout mode
   // Trade in direction of recent move
   if(ratio < InpExpansionMult) return 0;  // Not expanding enough

   // Breakout direction: sum of recent bar moves
   double moveSum = 0;
   for(int i = 1; i <= InpBreakoutBars; i++)
      moveSum += iClose(_Symbol, PERIOD_CURRENT, i) - iOpen(_Symbol, PERIOD_CURRENT, i);

   // Trend bias
   double trend[];
   ArraySetAsSeries(trend, true);
   if(CopyBuffer(g_hTrend, 0, 1, 1, trend) < 1) return 0;
   double close1 = iClose(_Symbol, PERIOD_CURRENT, 1);

   bool upTrend = (close1 > trend[0]);
   bool downTrend = (close1 < trend[0]);

   if(moveSum > 0 && upTrend) return +1;
   if(moveSum < 0 && downTrend) return -1;
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
   req.comment=StringFormat("VOLC|r=%.2f",ComputeRV(1,InpRVShort)/MathMax(ComputeRV(1,InpRVLong),0.00001));
   req.type_filling=ORDER_FILLING_FOK;
   if(!OrderSend(req,res)){req.type_filling=ORDER_FILLING_IOC;if(!OrderSend(req,res))return;}
   if(res.retcode==TRADE_RETCODE_DONE||res.retcode==TRADE_RETCODE_PLACED)
   { g_tradesToday++; PrintFormat("[VOLC] %s %.2f @ %.2f ratio=%.2f",isBuy?"BUY":"SELL",lot,res.price,ComputeRV(1,InpRVShort)/MathMax(ComputeRV(1,InpRVLong),0.00001)); }
}

double OnTester()
{ double pf=TesterStatistics(STAT_PROFIT_FACTOR),n=TesterStatistics(STAT_TRADES); if(n<20) return 0; return pf*MathSqrt(n); }
