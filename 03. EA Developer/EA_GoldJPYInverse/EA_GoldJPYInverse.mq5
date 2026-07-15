//+------------------------------------------------------------------+
//| EA_GoldJPYInverse.mq5 — XAUUSD move as USDJPY signal             |
//| Symbol: USDJPY+  |  Period: M15                                   |
//|                                                                   |
//| PARADIGM: Cross-asset risk sentiment signal                        |
//| Gold and JPY are both safe-haven assets. In risk-off episodes,   |
//| gold rises AND JPY strengthens (USDJPY falls). Conversely,        |
//| gold falling = risk-on = USDJPY rising.                           |
//|                                                                   |
//| HYPOTHESIS: A strong gold M15 bar can LEAD the USDJPY move by   |
//| 1-3 bars because institutional gold flow happens first (London    |
//| market), and FX adjusts slightly later.                           |
//|                                                                   |
//| SIGNAL: If XAUUSD+ close[1] dropped > threshold → BUY USDJPY+   |
//|         If XAUUSD+ close[1] rose > threshold → SELL USDJPY+      |
//| Combined with CI trending regime + EMA50 trend confirmation.      |
//|                                                                   |
//| Novelty: Type #98 — Cross-asset (gold→FX) intraday lead-lag      |
//| SIGNALS ON BAR[1] ONLY — no repaint.                              |
//| Max | 2026-04-13 | v1.0                                          |
//+------------------------------------------------------------------+
#property copyright "Max — EA_GoldJPYInverse v1.0"
#property version   "1.00"
#property strict

input group "=== General ==="
input ulong    InpMagic         = 231001;
input int      InpDeviation     = 30;

input group "=== Cross-Asset Signal ==="
input string   InpGoldSymbol    = "XAUUSD+";    // Gold symbol on broker
input double   InpGoldThreshATR = 0.8;           // Gold move threshold as fraction of gold ATR14
input int      InpGoldATRPeriod = 14;

input group "=== Choppiness Filter ==="
input int      InpChopPeriod    = 14;
input double   InpChopMax       = 50.0;
input bool     InpUseChop       = true;

input group "=== Trend (on USDJPY) ==="
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
input int      InpSkipHour      = -1;            // Skip this hour within session (-1=none)

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
int      g_hGoldATR = INVALID_HANDLE;
datetime g_lastBar = 0;
int      g_tradesToday = 0;
int      g_lastTradeDay = -1;
double   g_dayStartBalance = 0;

int OnInit()
{
   g_hATR14 = iATR(_Symbol, PERIOD_CURRENT, 14);
   g_hATR1  = iATR(_Symbol, PERIOD_CURRENT, 1);
   g_hTrend = iMA(_Symbol, PERIOD_CURRENT, InpTrendEMA, 0, MODE_EMA, PRICE_CLOSE);
   g_hGoldATR = iATR(InpGoldSymbol, PERIOD_CURRENT, InpGoldATRPeriod);

   if(g_hATR14==INVALID_HANDLE||g_hATR1==INVALID_HANDLE||g_hTrend==INVALID_HANDLE||g_hGoldATR==INVALID_HANDLE)
   {
      PrintFormat("[GoldJPY] INIT FAILED — check symbol %s exists", InpGoldSymbol);
      return INIT_FAILED;
   }
   g_dayStartBalance = AccountInfoDouble(ACCOUNT_BALANCE);
   PrintFormat("[GoldJPY] v1.0 | Gold=%s ThreshATR=%.1f", InpGoldSymbol, InpGoldThreshATR);
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   if(g_hATR14!=INVALID_HANDLE) IndicatorRelease(g_hATR14);
   if(g_hATR1!=INVALID_HANDLE)  IndicatorRelease(g_hATR1);
   if(g_hTrend!=INVALID_HANDLE) IndicatorRelease(g_hTrend);
   if(g_hGoldATR!=INVALID_HANDLE) IndicatorRelease(g_hGoldATR);
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
   // CI filter on USDJPY (the traded symbol)
   if(InpUseChop)
   {
      double ci = ComputeChoppiness(1);
      if(ci > InpChopMax) return 0;
   }

   // Cross-symbol timestamp sync check
   datetime goldBarTime = iTime(InpGoldSymbol, PERIOD_CURRENT, 1);
   datetime localBarTime = iTime(_Symbol, PERIOD_CURRENT, 1);
   if(MathAbs((long)(goldBarTime - localBarTime)) > PeriodSeconds(PERIOD_CURRENT))
      return 0;  // Bar mismatch — skip signal

   // Get gold bar[1] move
   double goldClose1 = iClose(InpGoldSymbol, PERIOD_CURRENT, 1);
   double goldClose2 = iClose(InpGoldSymbol, PERIOD_CURRENT, 2);
   if(goldClose1 <= 0 || goldClose2 <= 0) return 0;

   double goldMove = goldClose1 - goldClose2;

   // Get gold ATR for threshold
   double goldATR[];
   ArraySetAsSeries(goldATR, true);
   if(CopyBuffer(g_hGoldATR, 0, 1, 1, goldATR) < 1) return 0;
   if(goldATR[0] <= 0) return 0;

   double threshold = goldATR[0] * InpGoldThreshATR;

   // Gold fell strongly → risk-on → USDJPY should rise → BUY
   // Gold rose strongly → risk-off → USDJPY should fall → SELL
   int goldSignal = 0;
   if(goldMove < -threshold) goldSignal = +1;  // Gold down → buy USDJPY
   if(goldMove > +threshold) goldSignal = -1;  // Gold up → sell USDJPY

   if(goldSignal == 0) return 0;

   // Confirm with USDJPY trend
   double trend[];
   ArraySetAsSeries(trend, true);
   if(CopyBuffer(g_hTrend, 0, 1, 1, trend) < 1) return 0;
   double close1 = iClose(_Symbol, PERIOD_CURRENT, 1);

   if(goldSignal == +1 && close1 > trend[0]) return +1;
   if(goldSignal == -1 && close1 < trend[0]) return -1;

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
   if(InpSkipHour >= 0 && dt.hour == InpSkipHour) return;

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
   req.comment="GJPY|xasset";
   req.type_filling=ORDER_FILLING_FOK;
   if(!OrderSend(req,res)){req.type_filling=ORDER_FILLING_IOC;if(!OrderSend(req,res))return;}
   if(res.retcode==TRADE_RETCODE_DONE||res.retcode==TRADE_RETCODE_PLACED)
   { g_tradesToday++; PrintFormat("[GJPY] %s %.2f @ %.2f",isBuy?"BUY":"SELL",lot,res.price); }
}

double OnTester()
{ double pf=TesterStatistics(STAT_PROFIT_FACTOR),n=TesterStatistics(STAT_TRADES); if(n<20) return 0; return pf*MathSqrt(n); }
