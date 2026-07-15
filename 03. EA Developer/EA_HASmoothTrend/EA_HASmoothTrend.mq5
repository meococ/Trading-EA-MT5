//+------------------------------------------------------------------+
//| EA_HASmoothTrend.mq5 — Heiken Ashi Smoothed Color Flip + CI      |
//| Symbol: USDJPY+  |  Period: M15                                   |
//|                                                                   |
//| PARADIGM: Smoothed candle color transition as trend signal         |
//| Heiken Ashi Smoothed applies EMA to OHLC BEFORE computing HA.    |
//| This double-smoothing creates a very clean trend signal.          |
//| A color flip (green->red or red->green) at bar[1] = trend change.|
//|                                                                   |
//| Key difference from EMA crossover:                                |
//| - EMA cross uses 2 moving averages of close only                 |
//| - HA-Smooth uses 4-component (OHLC) smoothed candle structure    |
//| - The "flip" captures body/wick relationship, not just price vs MA|
//|                                                                   |
//| Combined with CI < threshold for regime gating.                   |
//|                                                                   |
//| Novelty: Type #94 — HA-Smoothed color flip + CI regime            |
//| SIGNALS ON BAR[1] ONLY — no repaint.                              |
//| Max | 2026-04-13 | v1.0                                          |
//+------------------------------------------------------------------+
#property copyright "Max — EA_HASmoothTrend v1.0"
#property version   "1.00"
#property strict

input group "=== General ==="
input ulong    InpMagic         = 227001;
input int      InpDeviation     = 30;

input group "=== HA Smoothed ==="
input int      InpHAPeriod      = 20;            // EMA period for smoothing OHLC before HA calc
input int      InpHAPeriod2     = 10;            // Second smoothing of HA values

input group "=== Choppiness Filter ==="
input int      InpChopPeriod    = 14;
input double   InpChopMax       = 50.0;
input bool     InpUseChop       = true;

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
// EMA handles for OHLC smoothing (first stage)
int      g_hEmaO  = INVALID_HANDLE;
int      g_hEmaH  = INVALID_HANDLE;
int      g_hEmaL  = INVALID_HANDLE;
int      g_hEmaC  = INVALID_HANDLE;

datetime g_lastBar = 0;
int      g_tradesToday = 0;
int      g_lastTradeDay = -1;
double   g_dayStartBalance = 0;

// HA Smoothed state (second stage EMA applied to HA values)
double   g_haOpen2  = 0;
double   g_haClose2 = 0;
double   g_prevHaOpen2  = 0;
double   g_prevHaClose2 = 0;
bool     g_haInit = false;
int      g_warmup = 0;

int OnInit()
{
   g_hATR14 = iATR(_Symbol, PERIOD_CURRENT, 14);
   g_hATR1  = iATR(_Symbol, PERIOD_CURRENT, 1);
   g_hTrend = iMA(_Symbol, PERIOD_CURRENT, InpTrendEMA, 0, MODE_EMA, PRICE_CLOSE);
   // First stage: EMA of OHLC
   g_hEmaO = iMA(_Symbol, PERIOD_CURRENT, InpHAPeriod, 0, MODE_EMA, PRICE_OPEN);
   g_hEmaH = iMA(_Symbol, PERIOD_CURRENT, InpHAPeriod, 0, MODE_EMA, PRICE_HIGH);
   g_hEmaL = iMA(_Symbol, PERIOD_CURRENT, InpHAPeriod, 0, MODE_EMA, PRICE_LOW);
   g_hEmaC = iMA(_Symbol, PERIOD_CURRENT, InpHAPeriod, 0, MODE_EMA, PRICE_CLOSE);

   if(g_hATR14==INVALID_HANDLE||g_hATR1==INVALID_HANDLE||g_hTrend==INVALID_HANDLE||
      g_hEmaO==INVALID_HANDLE||g_hEmaH==INVALID_HANDLE||g_hEmaL==INVALID_HANDLE||g_hEmaC==INVALID_HANDLE)
      return INIT_FAILED;

   g_dayStartBalance = AccountInfoDouble(ACCOUNT_BALANCE);
   g_haInit = false;
   g_warmup = 0;
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   if(g_hATR14!=INVALID_HANDLE) IndicatorRelease(g_hATR14);
   if(g_hATR1!=INVALID_HANDLE)  IndicatorRelease(g_hATR1);
   if(g_hTrend!=INVALID_HANDLE) IndicatorRelease(g_hTrend);
   if(g_hEmaO!=INVALID_HANDLE)  IndicatorRelease(g_hEmaO);
   if(g_hEmaH!=INVALID_HANDLE)  IndicatorRelease(g_hEmaH);
   if(g_hEmaL!=INVALID_HANDLE)  IndicatorRelease(g_hEmaL);
   if(g_hEmaC!=INVALID_HANDLE)  IndicatorRelease(g_hEmaC);
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

//+------------------------------------------------------------------+
//| Update HA-Smoothed calculation                                    |
//| Step 1: EMA-smooth the OHLC (first stage — done by MT5 iMA)     |
//| Step 2: Compute HA from smoothed OHLC                            |
//| Step 3: Apply second EMA to HA values                            |
//+------------------------------------------------------------------+
void UpdateHA()
{
   g_warmup++;

   // Step 1: Get smoothed OHLC at bar[1]
   double sO[], sH[], sL[], sC[];
   ArraySetAsSeries(sO, true);
   ArraySetAsSeries(sH, true);
   ArraySetAsSeries(sL, true);
   ArraySetAsSeries(sC, true);
   if(CopyBuffer(g_hEmaO, 0, 1, 1, sO) < 1) return;
   if(CopyBuffer(g_hEmaH, 0, 1, 1, sH) < 1) return;
   if(CopyBuffer(g_hEmaL, 0, 1, 1, sL) < 1) return;
   if(CopyBuffer(g_hEmaC, 0, 1, 1, sC) < 1) return;

   // Step 2: Compute HA candle from smoothed OHLC
   double haClose1 = (sO[0] + sH[0] + sL[0] + sC[0]) / 4.0;
   double haOpen1;

   if(!g_haInit)
   {
      haOpen1 = (sO[0] + sC[0]) / 2.0;
      g_haOpen2 = haOpen1;
      g_haClose2 = haClose1;
      g_prevHaOpen2 = haOpen1;
      g_prevHaClose2 = haClose1;
      g_haInit = true;
      return;
   }

   // Previous HA open for recursive calc
   haOpen1 = (g_prevHaOpen2 + g_prevHaClose2) / 2.0;

   // Step 3: Second stage EMA smoothing
   g_prevHaOpen2 = g_haOpen2;
   g_prevHaClose2 = g_haClose2;

   double k2 = 2.0 / (InpHAPeriod2 + 1);
   g_haOpen2  = g_haOpen2  + k2 * (haOpen1  - g_haOpen2);
   g_haClose2 = g_haClose2 + k2 * (haClose1 - g_haClose2);
}

int GetSignal()
{
   if(g_warmup < InpHAPeriod + InpHAPeriod2 + 5) return 0;

   // CI filter
   if(InpUseChop)
   {
      double ci = ComputeChoppiness(1);
      if(ci > InpChopMax) return 0;
   }

   // HA-Smoothed color: close > open = green (bullish), close < open = red (bearish)
   bool currBull = (g_haClose2 > g_haOpen2);
   bool prevBull = (g_prevHaClose2 > g_prevHaOpen2);

   // Color FLIP detection
   bool flipBull = (!prevBull && currBull);   // Red -> Green
   bool flipBear = (prevBull && !currBull);   // Green -> Red

   if(!flipBull && !flipBear) return 0;

   // Trend bias
   double trend[];
   ArraySetAsSeries(trend, true);
   if(CopyBuffer(g_hTrend, 0, 1, 1, trend) < 1) return 0;
   double close1 = iClose(_Symbol, PERIOD_CURRENT, 1);

   if(flipBull && close1 > trend[0]) return +1;
   if(flipBear && close1 < trend[0]) return -1;

   return 0;
}

void OnTick()
{
   datetime barTime = iTime(_Symbol, PERIOD_CURRENT, 0);
   if(barTime == g_lastBar) return;
   g_lastBar = barTime;

   UpdateHA();

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
   req.comment="HAS|flip";
   req.type_filling=ORDER_FILLING_FOK;
   if(!OrderSend(req,res)){req.type_filling=ORDER_FILLING_IOC;if(!OrderSend(req,res))return;}
   if(res.retcode==TRADE_RETCODE_DONE||res.retcode==TRADE_RETCODE_PLACED)
   { g_tradesToday++; PrintFormat("[HAS] %s %.2f @ %.2f",isBuy?"BUY":"SELL",lot,res.price); }
}

double OnTester()
{ double pf=TesterStatistics(STAT_PROFIT_FACTOR),n=TesterStatistics(STAT_TRADES); if(n<20) return 0; return pf*MathSqrt(n); }
