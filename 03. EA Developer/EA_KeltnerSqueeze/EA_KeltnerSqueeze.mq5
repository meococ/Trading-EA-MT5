//+------------------------------------------------------------------+
//| EA_KeltnerSqueeze.mq5 — Keltner Channel Squeeze Breakout         |
//| Symbol: USDJPY+  |  Period: M15                                   |
//|                                                                   |
//| PARADIGM: Volatility compression → expansion breakout             |
//| When Bollinger Bands contract INSIDE Keltner Channels, vol is     |
//| extremely compressed. When BB expands back outside KC, a          |
//| directional breakout is imminent. Trade the first M15 bar that   |
//| exits the squeeze.                                                |
//|                                                                   |
//| John Carter concept (TTM Squeeze) — never tested in this repo.   |
//| Different from VolCluster: VolCluster uses realized vol ratio,   |
//| this uses BB/KC relationship (implied vol compression).          |
//|                                                                   |
//| Novelty: Type #91 — Keltner squeeze (BB inside KC) breakout      |
//| SIGNALS ON BAR[1] ONLY — no repaint.                              |
//| Max | 2026-04-13 | v1.0                                          |
//+------------------------------------------------------------------+
#property copyright "Max — EA_KeltnerSqueeze v1.0"
#property version   "1.00"
#property strict

input group "=== General ==="
input ulong    InpMagic         = 224001;
input int      InpDeviation     = 30;

input group "=== Squeeze Detection ==="
input int      InpBBPeriod      = 20;
input double   InpBBDev         = 2.0;
input int      InpKCPeriod      = 20;
input double   InpKCMult        = 1.5;           // KC width = ATR * mult
input int      InpSqueezeMinBars = 3;            // Min bars in squeeze before breakout

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
int      g_hATRkc = INVALID_HANDLE;
int      g_hBB    = INVALID_HANDLE;
int      g_hKCma  = INVALID_HANDLE;
int      g_hTrend = INVALID_HANDLE;
datetime g_lastBar = 0;
int      g_tradesToday = 0;
int      g_lastTradeDay = -1;
double   g_dayStartBalance = 0;
int      g_squeezeCount = 0;  // How many consecutive bars in squeeze

int OnInit()
{
   g_hATR14 = iATR(_Symbol, PERIOD_CURRENT, 14);
   g_hATRkc = iATR(_Symbol, PERIOD_CURRENT, InpKCPeriod);
   g_hBB    = iBands(_Symbol, PERIOD_CURRENT, InpBBPeriod, 0, InpBBDev, PRICE_CLOSE);
   g_hKCma  = iMA(_Symbol, PERIOD_CURRENT, InpKCPeriod, 0, MODE_EMA, PRICE_CLOSE);
   g_hTrend = iMA(_Symbol, PERIOD_CURRENT, InpTrendEMA, 0, MODE_EMA, PRICE_CLOSE);
   if(g_hATR14==INVALID_HANDLE||g_hATRkc==INVALID_HANDLE||g_hBB==INVALID_HANDLE||
      g_hKCma==INVALID_HANDLE||g_hTrend==INVALID_HANDLE)
      return INIT_FAILED;
   g_dayStartBalance = AccountInfoDouble(ACCOUNT_BALANCE);
   g_squeezeCount = 0;
   PrintFormat("[SQUEEZE] v1.00 | BB=%d/%.1f KC=%d/%.1f MinBars=%d",
               InpBBPeriod, InpBBDev, InpKCPeriod, InpKCMult, InpSqueezeMinBars);
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   if(g_hATR14!=INVALID_HANDLE) IndicatorRelease(g_hATR14);
   if(g_hATRkc!=INVALID_HANDLE) IndicatorRelease(g_hATRkc);
   if(g_hBB!=INVALID_HANDLE)    IndicatorRelease(g_hBB);
   if(g_hKCma!=INVALID_HANDLE)  IndicatorRelease(g_hKCma);
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
//| Check if BB is inside KC (squeeze condition)                       |
//| BB upper < KC upper AND BB lower > KC lower = SQUEEZE            |
//+------------------------------------------------------------------+
bool IsInSqueeze(int shift)
{
   // BB bands
   double bbUpper[], bbLower[];
   ArraySetAsSeries(bbUpper, true);
   ArraySetAsSeries(bbLower, true);
   if(CopyBuffer(g_hBB, 1, shift, 1, bbUpper) < 1) return false;  // Upper band
   if(CopyBuffer(g_hBB, 2, shift, 1, bbLower) < 1) return false;  // Lower band

   // KC bands = EMA ± ATR * mult
   double kcMa[], kcAtr[];
   ArraySetAsSeries(kcMa, true);
   ArraySetAsSeries(kcAtr, true);
   if(CopyBuffer(g_hKCma, 0, shift, 1, kcMa) < 1) return false;
   if(CopyBuffer(g_hATRkc, 0, shift, 1, kcAtr) < 1) return false;

   double kcUpper = kcMa[0] + kcAtr[0] * InpKCMult;
   double kcLower = kcMa[0] - kcAtr[0] * InpKCMult;

   return (bbUpper[0] < kcUpper && bbLower[0] > kcLower);
}

int GetSignal()
{
   bool squeezePrev = IsInSqueeze(2);  // Bar[2] was in squeeze
   bool squeezeCurr = IsInSqueeze(1);  // Bar[1] is in/out of squeeze

   // Update squeeze counter
   if(squeezeCurr)
   {
      g_squeezeCount++;
      return 0;  // Still in squeeze — wait
   }
   else if(squeezePrev && !squeezeCurr && g_squeezeCount >= InpSqueezeMinBars)
   {
      // BREAKOUT! Was in squeeze, now released
      g_squeezeCount = 0;

      // Direction from momentum: bar[1] close vs bar[1] open
      double close1 = iClose(_Symbol, PERIOD_CURRENT, 1);
      double open1  = iOpen(_Symbol, PERIOD_CURRENT, 1);

      // Trend bias
      double trend[];
      ArraySetAsSeries(trend, true);
      if(CopyBuffer(g_hTrend, 0, 1, 1, trend) < 1) return 0;

      if(close1 > open1 && close1 > trend[0]) return +1;   // Bullish breakout
      if(close1 < open1 && close1 < trend[0]) return -1;   // Bearish breakout
   }
   else
   {
      g_squeezeCount = 0;  // Not in squeeze, reset
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
   req.comment="SQZ|breakout";
   req.type_filling=ORDER_FILLING_FOK;
   if(!OrderSend(req,res)){req.type_filling=ORDER_FILLING_IOC;if(!OrderSend(req,res))return;}
   if(res.retcode==TRADE_RETCODE_DONE||res.retcode==TRADE_RETCODE_PLACED)
   { g_tradesToday++; PrintFormat("[SQUEEZE] %s %.2f @ %.2f",isBuy?"BUY":"SELL",lot,res.price); }
}

double OnTester()
{ double pf=TesterStatistics(STAT_PROFIT_FACTOR),n=TesterStatistics(STAT_TRADES); if(n<20) return 0; return pf*MathSqrt(n); }
