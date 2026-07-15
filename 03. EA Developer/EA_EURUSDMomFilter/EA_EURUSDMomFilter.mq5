//+------------------------------------------------------------------+
//| EA_EURUSDMomFilter.mq5 — EURUSD Momentum as USDJPY Filter        |
//| Symbol: USDJPY+  |  Period: M15                                   |
//|                                                                   |
//| PARADIGM: Cross-currency USD strength signal                       |
//| EURUSD is 57% of DXY. When EURUSD drops, USD strengthens.        |
//| This USD strength flows to USDJPY (USD/JPY → USD up = pair up).  |
//|                                                                   |
//| HYPOTHESIS: EURUSD M15 momentum can act as a DIRECTIONAL FILTER  |
//| for USDJPY entries. Only buy USDJPY when EURUSD is falling        |
//| (USD strengthening). Only sell when EURUSD is rising.             |
//| Combined with EMA cross for timing + CI for regime.               |
//|                                                                   |
//| Key difference from GoldJPYInverse: that uses gold as SIGNAL.    |
//| This uses EURUSD as FILTER (confirmation, not trigger).           |
//| The trigger is still EMA cross on USDJPY itself.                  |
//|                                                                   |
//| Novelty: Type #100 — Cross-currency filter (EURUSD→USDJPY)       |
//| SIGNALS ON BAR[1] ONLY — no repaint.                              |
//| Max | 2026-04-13 | v1.0                                          |
//+------------------------------------------------------------------+
#property copyright "Max — EA_EURUSDMomFilter v1.0"
#property version   "1.00"
#property strict

input group "=== General ==="
input ulong    InpMagic         = 233001;
input int      InpDeviation     = 30;

input group "=== EURUSD Filter ==="
input string   InpFilterSymbol  = "EURUSD+";    // Filter pair
input int      InpFilterMomBars = 5;             // Momentum lookback on filter pair

input group "=== Signal: EMA Cross on USDJPY ==="
input int      InpEMAFast       = 8;
input int      InpEMASlow       = 21;

input group "=== Choppiness Filter ==="
input int      InpChopPeriod    = 14;
input double   InpChopMax       = 50.0;

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

int      g_hATR14 = INVALID_HANDLE;
int      g_hATR1  = INVALID_HANDLE;
int      g_hTrend = INVALID_HANDLE;
int      g_hEMAF  = INVALID_HANDLE;
int      g_hEMAS  = INVALID_HANDLE;
datetime g_lastBar = 0;
int      g_tradesToday = 0;
int      g_lastTradeDay = -1;
double   g_dayStartBalance = 0;

int OnInit()
{
   g_hATR14 = iATR(_Symbol, PERIOD_CURRENT, 14);
   g_hATR1  = iATR(_Symbol, PERIOD_CURRENT, 1);
   g_hTrend = iMA(_Symbol, PERIOD_CURRENT, InpTrendEMA, 0, MODE_EMA, PRICE_CLOSE);
   g_hEMAF  = iMA(_Symbol, PERIOD_CURRENT, InpEMAFast, 0, MODE_EMA, PRICE_CLOSE);
   g_hEMAS  = iMA(_Symbol, PERIOD_CURRENT, InpEMASlow, 0, MODE_EMA, PRICE_CLOSE);
   if(g_hATR14==INVALID_HANDLE||g_hATR1==INVALID_HANDLE||g_hTrend==INVALID_HANDLE||
      g_hEMAF==INVALID_HANDLE||g_hEMAS==INVALID_HANDLE)
      return INIT_FAILED;

   double testClose = iClose(InpFilterSymbol, PERIOD_CURRENT, 1);
   if(testClose <= 0)
   {
      PrintFormat("[EURF] INIT FAILED — symbol %s not available", InpFilterSymbol);
      return INIT_FAILED;
   }

   g_dayStartBalance = AccountInfoDouble(ACCOUNT_BALANCE);
   PrintFormat("[EURF] v1.0 | Filter=%s MomBars=%d", InpFilterSymbol, InpFilterMomBars);
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   if(g_hATR14!=INVALID_HANDLE) IndicatorRelease(g_hATR14);
   if(g_hATR1!=INVALID_HANDLE)  IndicatorRelease(g_hATR1);
   if(g_hTrend!=INVALID_HANDLE) IndicatorRelease(g_hTrend);
   if(g_hEMAF!=INVALID_HANDLE)  IndicatorRelease(g_hEMAF);
   if(g_hEMAS!=INVALID_HANDLE)  IndicatorRelease(g_hEMAS);
}

int CountPositions()
{ int c=0;for(int i=PositionsTotal()-1;i>=0;i--){ulong t=PositionGetTicket(i);if(t>0&&PositionGetInteger(POSITION_MAGIC)==(long)InpMagic&&PositionGetString(POSITION_SYMBOL)==_Symbol)c++;}return c; }

void CloseAll()
{ for(int i=PositionsTotal()-1;i>=0;i--){ulong t=PositionGetTicket(i);if(t<=0||PositionGetInteger(POSITION_MAGIC)!=(long)InpMagic||PositionGetString(POSITION_SYMBOL)!=_Symbol)continue;MqlTradeRequest req={};MqlTradeResult res={};req.action=TRADE_ACTION_DEAL;req.symbol=_Symbol;req.volume=PositionGetDouble(POSITION_VOLUME);req.deviation=(ulong)InpDeviation;req.magic=InpMagic;req.position=t;if(PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_BUY){req.type=ORDER_TYPE_SELL;req.price=SymbolInfoDouble(_Symbol,SYMBOL_BID);}else{req.type=ORDER_TYPE_BUY;req.price=SymbolInfoDouble(_Symbol,SYMBOL_ASK);}req.type_filling=ORDER_FILLING_FOK;if(!OrderSend(req,res)){req.type_filling=ORDER_FILLING_IOC;OrderSend(req,res);}} }

bool IsDDExceeded()
{ if(g_dayStartBalance<=0)return false;return(g_dayStartBalance-AccountInfoDouble(ACCOUNT_EQUITY))/g_dayStartBalance*100.0>=InpDailyDD; }

double CalcLot(double sl)
{ if(sl<=0)return 0;double b=AccountInfoDouble(ACCOUNT_BALANCE),r=b*InpRiskPct/100.0;double tv=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_VALUE),ts=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);if(tv<=0||ts<=0)return 0;double lot=r/(sl/ts*tv);lot=MathMin(lot,InpMaxLot);lot=MathMin(lot,SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX));lot=MathMax(lot,SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN));lot=MathFloor(lot/SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP))*SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);return lot; }

double ComputeChoppiness(int shift)
{
   double atrSum = 0;
   double atr1[];
   ArraySetAsSeries(atr1, true);
   if(CopyBuffer(g_hATR1, 0, shift, InpChopPeriod, atr1) < InpChopPeriod) return 50.0;
   for(int i = 0; i < InpChopPeriod; i++) atrSum += atr1[i];
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
   return 100.0 * MathLog10(atrSum / range) / MathLog10((double)InpChopPeriod);
}

int GetSignal()
{
   // CI filter on USDJPY
   double ci = ComputeChoppiness(1);
   if(ci > InpChopMax) return 0;

   // EMA cross signal on USDJPY
   double emaF[], emaS[], emaF2[], emaS2[];
   ArraySetAsSeries(emaF, true); ArraySetAsSeries(emaS, true);
   ArraySetAsSeries(emaF2, true); ArraySetAsSeries(emaS2, true);
   if(CopyBuffer(g_hEMAF,0,1,1,emaF)<1 || CopyBuffer(g_hEMAS,0,1,1,emaS)<1 ||
      CopyBuffer(g_hEMAF,0,2,1,emaF2)<1 || CopyBuffer(g_hEMAS,0,2,1,emaS2)<1)
      return 0;

   bool crossBull = (emaF2[0] <= emaS2[0] && emaF[0] > emaS[0]);
   bool crossBear = (emaF2[0] >= emaS2[0] && emaF[0] < emaS[0]);
   if(!crossBull && !crossBear) return 0;

   // Trend bias
   double trend[];
   ArraySetAsSeries(trend, true);
   if(CopyBuffer(g_hTrend, 0, 1, 1, trend) < 1) return 0;
   double close1 = iClose(_Symbol, PERIOD_CURRENT, 1);

   // EURUSD momentum filter
   // Read EURUSD close[1] and close[1+N]
   double eurClose1 = iClose(InpFilterSymbol, PERIOD_CURRENT, 1);
   double eurCloseN = iClose(InpFilterSymbol, PERIOD_CURRENT, 1 + InpFilterMomBars);
   if(eurClose1 <= 0 || eurCloseN <= 0) return 0;

   bool eurFalling = (eurClose1 < eurCloseN);  // USD strengthening
   bool eurRising  = (eurClose1 > eurCloseN);  // USD weakening

   // BUY USDJPY: EMA cross up + trend up + EURUSD falling (USD strong)
   if(crossBull && close1 > trend[0] && eurFalling) return +1;

   // SELL USDJPY: EMA cross down + trend down + EURUSD rising (USD weak)
   if(crossBear && close1 < trend[0] && eurRising) return -1;

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
   req.comment="EURF|mom";
   req.type_filling=ORDER_FILLING_FOK;
   if(!OrderSend(req,res)){req.type_filling=ORDER_FILLING_IOC;if(!OrderSend(req,res))return;}
   if(res.retcode==TRADE_RETCODE_DONE||res.retcode==TRADE_RETCODE_PLACED)
   { g_tradesToday++; PrintFormat("[EURF] %s %.2f @ %.2f",isBuy?"BUY":"SELL",lot,res.price); }
}

double OnTester()
{ double pf=TesterStatistics(STAT_PROFIT_FACTOR),n=TesterStatistics(STAT_TRADES); if(n<20) return 0; return pf*MathSqrt(n); }
