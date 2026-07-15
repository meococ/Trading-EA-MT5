//+------------------------------------------------------------------+
//| EA_EhlersFisher.mq5 — Ehlers Fisher Transform Reversal           |
//| Symbol: XAUUSD+ / USDJPY+  |  Period: M15                        |
//|                                                                   |
//| PARADIGM SHIFT: Digital Signal Processing                         |
//| John Ehlers (2004): Fisher Transform normalizes any oscillator   |
//| into Gaussian distribution → sharp turning points → clear         |
//| reversal signals that are statistically superior to RSI/Stoch.   |
//|                                                                   |
//| The Fisher Transform: F = 0.5 * ln((1+x)/(1-x))                 |
//| where x = normalized price in [-1,+1] range.                     |
//| Buy: F crosses above signal AND direction confirms                |
//| Sell: F crosses below signal AND direction confirms               |
//|                                                                   |
//| DISTINCT FROM everything tested: DSP theory, not TA patterns.    |
//| Novelty: Type #81 — Ehlers Fisher Transform reversal             |
//| SIGNALS ON BAR[1] ONLY — no repaint.                              |
//| Max | 2026-04-13 | v1.0                                          |
//+------------------------------------------------------------------+
#property copyright "Max — EA_EhlersFisher v1.0"
#property version   "1.00"
#property strict

input group "=== General ==="
input ulong    InpMagic         = 214001;
input int      InpDeviation     = 30;

input group "=== Fisher Transform ==="
input int      InpFisherPeriod  = 10;            // Lookback for normalized price
input double   InpFisherThresh  = 1.5;           // Threshold for extreme (typical: 1.5-2.5)
input bool     InpUseTrendBias  = true;          // Require EMA trend alignment
input int      InpTrendPeriod   = 50;            // EMA period for trend bias

input group "=== Session ==="
input int      InpStartHour     = 10;
input int      InpEndHour       = 20;
input int      InpExitHour      = 22;
input bool     InpSkipMon       = true;
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

//--- internal state
int      g_hATR = INVALID_HANDLE;
int      g_hEMA = INVALID_HANDLE;
datetime g_lastBar = 0;
int      g_tradesToday = 0;
int      g_lastTradeDay = -1;
double   g_dayStartBalance = 0;

// Fisher Transform values (circular buffer)
double   g_fisher1 = 0;    // bar[1]
double   g_fisher2 = 0;    // bar[2]

int OnInit()
{
   g_hATR = iATR(_Symbol, PERIOD_CURRENT, 14);
   if(InpUseTrendBias)
      g_hEMA = iMA(_Symbol, PERIOD_CURRENT, InpTrendPeriod, 0, MODE_EMA, PRICE_CLOSE);
   if(g_hATR == INVALID_HANDLE) return INIT_FAILED;
   g_dayStartBalance = AccountInfoDouble(ACCOUNT_BALANCE);
   PrintFormat("[FISHER] v1.00 | Period=%d Threshold=%.1f TrendBias=%s",
               InpFisherPeriod, InpFisherThresh, InpUseTrendBias?"ON":"OFF");
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   if(g_hATR != INVALID_HANDLE) IndicatorRelease(g_hATR);
   if(g_hEMA != INVALID_HANDLE) IndicatorRelease(g_hEMA);
}

//--- Standard helpers (same as other EAs)
int CountPositions()
{
   int cnt = 0;
   for(int i = PositionsTotal()-1; i >= 0; i--)
   { ulong t=PositionGetTicket(i); if(t>0 && PositionGetInteger(POSITION_MAGIC)==(long)InpMagic && PositionGetString(POSITION_SYMBOL)==_Symbol) cnt++; }
   return cnt;
}

void CloseAll()
{
   for(int i = PositionsTotal()-1; i >= 0; i--)
   {
      ulong t=PositionGetTicket(i);
      if(t<=0||PositionGetInteger(POSITION_MAGIC)!=(long)InpMagic||PositionGetString(POSITION_SYMBOL)!=_Symbol) continue;
      MqlTradeRequest req={}; MqlTradeResult res={};
      req.action=TRADE_ACTION_DEAL; req.symbol=_Symbol;
      req.volume=PositionGetDouble(POSITION_VOLUME);
      req.deviation=(ulong)InpDeviation; req.magic=InpMagic; req.position=t;
      if(PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_BUY)
         {req.type=ORDER_TYPE_SELL; req.price=SymbolInfoDouble(_Symbol,SYMBOL_BID);}
      else
         {req.type=ORDER_TYPE_BUY; req.price=SymbolInfoDouble(_Symbol,SYMBOL_ASK);}
      req.type_filling=ORDER_FILLING_FOK;
      if(!OrderSend(req,res)){req.type_filling=ORDER_FILLING_IOC; OrderSend(req,res);}
   }
}

bool IsDDExceeded()
{ if(g_dayStartBalance<=0) return false; return (g_dayStartBalance-AccountInfoDouble(ACCOUNT_EQUITY))/g_dayStartBalance*100.0>=InpDailyDD; }

double CalcLot(double sl)
{
   if(sl<=0) return 0;
   double b=AccountInfoDouble(ACCOUNT_BALANCE), r=b*InpRiskPct/100.0;
   double tv=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_VALUE), ts=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);
   if(tv<=0||ts<=0) return 0;
   double lot=r/(sl/ts*tv);
   lot=MathMin(lot,InpMaxLot); lot=MathMin(lot,SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX));
   lot=MathMax(lot,SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN));
   lot=MathFloor(lot/SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP))*SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);
   return lot;
}

//+------------------------------------------------------------------+
//| Compute Fisher Transform value for bar[shift]                     |
//+------------------------------------------------------------------+
double ComputeFisher(int shift)
{
   // Find highest high and lowest low over period
   double hh = -999999, ll = 999999;
   for(int i = shift; i < shift + InpFisherPeriod; i++)
   {
      double h = iHigh(_Symbol, PERIOD_CURRENT, i);
      double l = iLow(_Symbol, PERIOD_CURRENT, i);
      if(h > hh) hh = h;
      if(l < ll) ll = l;
   }

   if(hh <= ll) return 0;

   // Normalize price to [-1, +1]
   double mid = (iHigh(_Symbol, PERIOD_CURRENT, shift) + iLow(_Symbol, PERIOD_CURRENT, shift)) / 2.0;
   double x = 2.0 * (mid - ll) / (hh - ll) - 1.0;

   // Clamp to avoid log(0) — Ehlers recommends 0.999
   if(x > 0.999) x = 0.999;
   if(x < -0.999) x = -0.999;

   // Fisher Transform
   double fisher = 0.5 * MathLog((1.0 + x) / (1.0 - x));

   return fisher;
}

//+------------------------------------------------------------------+
//| Generate signal: +1 buy, -1 sell, 0 none                         |
//+------------------------------------------------------------------+
int GetSignal()
{
   g_fisher1 = ComputeFisher(1);
   g_fisher2 = ComputeFisher(2);

   // Crossover detection with threshold
   // BUY: Fisher crosses UP through -threshold (reversal from oversold)
   // SELL: Fisher crosses DOWN through +threshold (reversal from overbought)
   bool buySignal  = (g_fisher2 < -InpFisherThresh && g_fisher1 > -InpFisherThresh);
   bool sellSignal = (g_fisher2 > InpFisherThresh && g_fisher1 < InpFisherThresh);

   // Alternative: momentum mode — trade WITH Fisher direction at extremes
   // Already strong directional Fisher = momentum continuation
   // Uncomment below for momentum mode instead of reversal mode:
   // buySignal  = (g_fisher1 > InpFisherThresh && g_fisher1 > g_fisher2);
   // sellSignal = (g_fisher1 < -InpFisherThresh && g_fisher1 < g_fisher2);

   if(!buySignal && !sellSignal) return 0;

   // Trend bias filter
   if(InpUseTrendBias && g_hEMA != INVALID_HANDLE)
   {
      double ema[];
      ArraySetAsSeries(ema, true);
      if(CopyBuffer(g_hEMA, 0, 1, 1, ema) < 1) return 0;
      double close1 = iClose(_Symbol, PERIOD_CURRENT, 1);

      if(buySignal && close1 < ema[0]) return 0;    // Don't buy below EMA
      if(sellSignal && close1 > ema[0]) return 0;   // Don't sell above EMA
   }

   if(buySignal) return +1;
   if(sellSignal) return -1;
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
   if(InpSkipFri && dt.day_of_week == 5) return;

   int signal = GetSignal();
   if(signal == 0) return;

   double atr[];
   ArraySetAsSeries(atr, true);
   if(CopyBuffer(g_hATR, 0, 1, 1, atr) < 1) return;

   double slDist = atr[0] * InpSL_ATR_Mult;
   if(slDist < InpMinSLPoints*_Point) slDist = InpMinSLPoints*_Point;
   if(slDist > InpMaxSLPoints*_Point) return;

   bool isBuy = (signal == +1);
   double ask=SymbolInfoDouble(_Symbol,SYMBOL_ASK), bid=SymbolInfoDouble(_Symbol,SYMBOL_BID);
   double entry=isBuy?ask:bid;
   double sl=isBuy?ask-slDist:bid+slDist;
   double tp=isBuy?ask+slDist*InpTP_Ratio:bid-slDist*InpTP_Ratio;

   if(slDist < (int)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL)*_Point) return;
   double lot = CalcLot(slDist);
   if(lot <= 0) return;

   int digits=(int)SymbolInfoInteger(_Symbol,SYMBOL_DIGITS);
   sl=NormalizeDouble(sl,digits); tp=NormalizeDouble(tp,digits);

   MqlTradeRequest req={}; MqlTradeResult res={};
   req.action=TRADE_ACTION_DEAL; req.symbol=_Symbol; req.volume=lot;
   req.type=isBuy?ORDER_TYPE_BUY:ORDER_TYPE_SELL;
   req.price=entry; req.sl=sl; req.tp=tp;
   req.deviation=(ulong)InpDeviation; req.magic=InpMagic;
   req.comment=StringFormat("FISHER|%.2f→%.2f", g_fisher2, g_fisher1);
   req.type_filling=ORDER_FILLING_FOK;
   if(!OrderSend(req,res)){req.type_filling=ORDER_FILLING_IOC; if(!OrderSend(req,res)) return;}
   if(res.retcode==TRADE_RETCODE_DONE||res.retcode==TRADE_RETCODE_PLACED)
   { g_tradesToday++; PrintFormat("[FISHER] %s %.2f @ %.2f F=%.2f→%.2f", isBuy?"BUY":"SELL",lot,res.price,g_fisher2,g_fisher1); }
}

double OnTester()
{ double pf=TesterStatistics(STAT_PROFIT_FACTOR), n=TesterStatistics(STAT_TRADES); if(n<20) return 0; return pf*MathSqrt(n); }
