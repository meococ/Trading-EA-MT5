//+------------------------------------------------------------------+
//| EA_TickVolAccel.mq5 — Tick Volume Acceleration Signal             |
//| Symbol: USDJPY+  |  Period: M15                                   |
//|                                                                   |
//| PARADIGM: Volume-price divergence / microstructure                 |
//| Uses tick volume (number of price changes per bar) as a proxy for |
//| market activity. Key signals:                                      |
//| 1. Volume spike + large body = momentum (follow)                  |
//| 2. Volume spike + small body = absorption (fade)                  |
//|                                                                   |
//| This EA uses pattern 1: high tick volume bars that close strongly |
//| in one direction = institutional flow pushing price.               |
//|                                                                   |
//| SIGNAL: If bar[1] tick_volume > InpVolMultiplier * avg_vol AND   |
//| bar[1] body > InpBodyATRMult * ATR → enter in direction of body  |
//| Combined with CI trending regime + EMA50 trend.                   |
//|                                                                   |
//| Novelty: Type #101 — Tick volume acceleration (microstructure)    |
//| SIGNALS ON BAR[1] ONLY — no repaint.                              |
//| Max | 2026-04-13 | v1.0                                          |
//+------------------------------------------------------------------+
#property copyright "Max — EA_TickVolAccel v1.0"
#property version   "1.00"
#property strict

input group "=== General ==="
input ulong    InpMagic         = 234001;
input int      InpDeviation     = 30;

input group "=== Volume Signal ==="
input int      InpVolPeriod     = 20;             // Lookback for average volume
input double   InpVolMultiplier = 1.8;            // Volume must exceed avg * this
input double   InpBodyATRMult   = 0.5;            // Body must exceed ATR14 * this

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
datetime g_lastBar = 0;
int      g_tradesToday = 0;
int      g_lastTradeDay = -1;
double   g_dayStartBalance = 0;

int OnInit()
{
   g_hATR14 = iATR(_Symbol, PERIOD_CURRENT, 14);
   g_hATR1  = iATR(_Symbol, PERIOD_CURRENT, 1);
   g_hTrend = iMA(_Symbol, PERIOD_CURRENT, InpTrendEMA, 0, MODE_EMA, PRICE_CLOSE);
   if(g_hATR14==INVALID_HANDLE||g_hATR1==INVALID_HANDLE||g_hTrend==INVALID_HANDLE)
      return INIT_FAILED;
   g_dayStartBalance = AccountInfoDouble(ACCOUNT_BALANCE);
   PrintFormat("[TVOL] v1.0 | VolPer=%d VolMult=%.1f BodyATR=%.1f", InpVolPeriod, InpVolMultiplier, InpBodyATRMult);
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   if(g_hATR14!=INVALID_HANDLE) IndicatorRelease(g_hATR14);
   if(g_hATR1!=INVALID_HANDLE)  IndicatorRelease(g_hATR1);
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
   // CI filter
   double ci = ComputeChoppiness(1);
   if(ci > InpChopMax) return 0;

   // Get bar[1] tick volume and average volume
   long vol1 = iVolume(_Symbol, PERIOD_CURRENT, 1);
   if(vol1 <= 0) return 0;

   // Calculate average tick volume over lookback
   long avgVol = 0;
   for(int i = 2; i <= InpVolPeriod + 1; i++)
   {
      avgVol += iVolume(_Symbol, PERIOD_CURRENT, i);
   }
   avgVol /= InpVolPeriod;
   if(avgVol <= 0) return 0;

   // Volume spike check
   if(vol1 < (long)(avgVol * InpVolMultiplier)) return 0;

   // Bar[1] body size
   double open1 = iOpen(_Symbol, PERIOD_CURRENT, 1);
   double close1 = iClose(_Symbol, PERIOD_CURRENT, 1);
   double body = MathAbs(close1 - open1);

   // ATR threshold for body
   double atr[];
   ArraySetAsSeries(atr, true);
   if(CopyBuffer(g_hATR14, 0, 1, 1, atr) < 1) return 0;
   if(body < atr[0] * InpBodyATRMult) return 0;

   // Determine direction from body
   bool bullBody = (close1 > open1);
   bool bearBody = (close1 < open1);

   // Trend confirmation
   double trend[];
   ArraySetAsSeries(trend, true);
   if(CopyBuffer(g_hTrend, 0, 1, 1, trend) < 1) return 0;

   // BUY: bullish volume spike + trend up
   if(bullBody && close1 > trend[0]) return +1;
   // SELL: bearish volume spike + trend down
   if(bearBody && close1 < trend[0]) return -1;

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
   req.comment="TVOL|spike";
   req.type_filling=ORDER_FILLING_FOK;
   if(!OrderSend(req,res)){req.type_filling=ORDER_FILLING_IOC;if(!OrderSend(req,res))return;}
   if(res.retcode==TRADE_RETCODE_DONE||res.retcode==TRADE_RETCODE_PLACED)
   { g_tradesToday++; PrintFormat("[TVOL] %s %.2f @ %.2f vol=%d avgVol=%d",isBuy?"BUY":"SELL",lot,res.price,iVolume(_Symbol,PERIOD_CURRENT,1),0); }
}

double OnTester()
{ double pf=TesterStatistics(STAT_PROFIT_FACTOR),n=TesterStatistics(STAT_TRADES); if(n<20) return 0; return pf*MathSqrt(n); }
