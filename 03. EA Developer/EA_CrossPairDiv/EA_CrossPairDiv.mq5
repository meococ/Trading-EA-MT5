//+------------------------------------------------------------------+
//| EA_CrossPairDiv.mq5 — EURJPY/USDJPY Divergence Signal             |
//| Symbol: USDJPY+  |  Period: M15                                   |
//|                                                                   |
//| PARADIGM: Cross-pair cointegration divergence                      |
//| EURJPY ≈ EURUSD × USDJPY. When EURJPY and USDJPY diverge       |
//| beyond their normal spread, they tend to reconverge.              |
//| This is a mean-reversion signal on the JPY component SPREAD.     |
//|                                                                   |
//| HYPOTHESIS: If EURJPY rises faster than USDJPY over N bars,     |
//| this means EUR strengthened vs JPY more than USD did.             |
//| Historically, USDJPY tends to catch up (both driven by JPY).     |
//|                                                                   |
//| SIGNAL: Compare normalized returns of EURJPY and USDJPY over     |
//| lookback period. If divergence exceeds threshold, trade the       |
//| lagging pair's expected catch-up direction.                       |
//|                                                                   |
//| SAFETY: This is counter-trend so we use LOOSE CI (allow chop)    |
//| and tighter stops. NOT combined with trend EMA.                   |
//|                                                                   |
//| Novelty: Type #99 — Cross-pair divergence (EURJPY/USDJPY)        |
//| SIGNALS ON BAR[1] ONLY — no repaint.                              |
//| Max | 2026-04-13 | v1.0                                          |
//+------------------------------------------------------------------+
#property copyright "Max — EA_CrossPairDiv v1.0"
#property version   "1.00"
#property strict

input group "=== General ==="
input ulong    InpMagic         = 232001;
input int      InpDeviation     = 30;

input group "=== Cross-Pair Signal ==="
input string   InpPairB         = "EURJPY+";     // Reference pair
input int      InpLookback      = 20;             // Bars for divergence calculation
input double   InpDivThreshold  = 1.5;            // Divergence threshold in ATR units

input group "=== Regime Filter ==="
input int      InpChopPeriod    = 14;
input double   InpChopMax       = 55.0;           // Looser CI for mean-reversion (allow some chop)
input bool     InpUseChop       = true;

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
datetime g_lastBar = 0;
int      g_tradesToday = 0;
int      g_lastTradeDay = -1;
double   g_dayStartBalance = 0;

int OnInit()
{
   g_hATR14 = iATR(_Symbol, PERIOD_CURRENT, 14);
   g_hATR1  = iATR(_Symbol, PERIOD_CURRENT, 1);

   if(g_hATR14==INVALID_HANDLE||g_hATR1==INVALID_HANDLE)
      return INIT_FAILED;

   // Verify cross-pair symbol exists
   double testClose = iClose(InpPairB, PERIOD_CURRENT, 1);
   if(testClose <= 0)
   {
      PrintFormat("[XDIV] INIT FAILED — symbol %s not available", InpPairB);
      return INIT_FAILED;
   }

   g_dayStartBalance = AccountInfoDouble(ACCOUNT_BALANCE);
   PrintFormat("[XDIV] v1.0 | PairB=%s Lookback=%d ThreshATR=%.1f", InpPairB, InpLookback, InpDivThreshold);
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   if(g_hATR14!=INVALID_HANDLE) IndicatorRelease(g_hATR14);
   if(g_hATR1!=INVALID_HANDLE)  IndicatorRelease(g_hATR1);
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
   if(InpUseChop)
   {
      double ci = ComputeChoppiness(1);
      if(ci > InpChopMax) return 0;
   }

   // Get returns for both pairs over lookback
   double closeA1 = iClose(_Symbol, PERIOD_CURRENT, 1);
   double closeAN = iClose(_Symbol, PERIOD_CURRENT, 1 + InpLookback);
   double closeB1 = iClose(InpPairB, PERIOD_CURRENT, 1);
   double closeBN = iClose(InpPairB, PERIOD_CURRENT, 1 + InpLookback);

   if(closeA1<=0 || closeAN<=0 || closeB1<=0 || closeBN<=0) return 0;

   // Normalized returns (percentage)
   double retA = (closeA1 - closeAN) / closeAN * 100.0;  // USDJPY return
   double retB = (closeB1 - closeBN) / closeBN * 100.0;  // EURJPY return

   // Divergence: how much USDJPY lags behind EURJPY (JPY-centric)
   // If EURJPY rose more than USDJPY → USDJPY should catch up (buy)
   // If EURJPY fell more than USDJPY → USDJPY should catch down (sell)
   double divergence = retB - retA;

   // ATR-based threshold (USDJPY ATR)
   double atr[];
   ArraySetAsSeries(atr, true);
   if(CopyBuffer(g_hATR14, 0, 1, 1, atr) < 1) return 0;

   // Normalize divergence by what's normal for this pair
   // Convert ATR to percentage of price
   double atrPct = atr[0] / closeA1 * 100.0;
   if(atrPct <= 0) return 0;

   double divNorm = divergence / atrPct;

   // USDJPY lagging behind EURJPY → expect catch-up
   if(divNorm > InpDivThreshold) return +1;   // EURJPY ahead → BUY USDJPY (catch up)
   if(divNorm < -InpDivThreshold) return -1;  // EURJPY behind → SELL USDJPY (catch down)

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
   req.comment="XDIV|div";
   req.type_filling=ORDER_FILLING_FOK;
   if(!OrderSend(req,res)){req.type_filling=ORDER_FILLING_IOC;if(!OrderSend(req,res))return;}
   if(res.retcode==TRADE_RETCODE_DONE||res.retcode==TRADE_RETCODE_PLACED)
   { g_tradesToday++; PrintFormat("[XDIV] %s %.2f @ %.2f",isBuy?"BUY":"SELL",lot,res.price); }
}

double OnTester()
{ double pf=TesterStatistics(STAT_PROFIT_FACTOR),n=TesterStatistics(STAT_TRADES); if(n<20) return 0; return pf*MathSqrt(n); }
