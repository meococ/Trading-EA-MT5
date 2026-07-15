//+------------------------------------------------------------------+
//| EA_SMIMomentum.mq5 — Stochastic Momentum Index Trend              |
//| Symbol: USDJPY+  |  Period: M15                                   |
//|                                                                   |
//| PARADIGM: Double-smoothed midpoint momentum                        |
//| SMI measures where the close is relative to the midpoint of the  |
//| high-low range, then double-smoothes it. Unlike standard          |
//| Stochastic (close vs low), SMI uses close vs MIDPOINT.           |
//| This gives a fundamentally different momentum reading:            |
//| - Standard Stoch: how high are we vs the low? (range position)   |
//| - SMI: how far from the center? (momentum displacement)          |
//|                                                                   |
//| Signal: SMI crosses above/below signal line with momentum bias.  |
//| Uses CI filter from ChopRegime for regime gating.                |
//|                                                                   |
//| Novelty: Type #93 — Stochastic Momentum Index + CI regime         |
//| SIGNALS ON BAR[1] ONLY — no repaint.                              |
//| Max | 2026-04-13 | v1.0                                          |
//+------------------------------------------------------------------+
#property copyright "Max — EA_SMIMomentum v1.0"
#property version   "1.00"
#property strict

input group "=== General ==="
input ulong    InpMagic         = 226001;
input int      InpDeviation     = 30;

input group "=== SMI ==="
input int      InpSMIPeriod     = 13;            // Lookback for high-low range
input int      InpSMISmooth1    = 25;            // First EMA smoothing
input int      InpSMISmooth2    = 2;             // Second EMA smoothing (double smooth)
input int      InpSMISignal     = 9;             // Signal line EMA
input double   InpSMIThresh     = 0.0;           // SMI threshold for signal (0 = center cross)

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
datetime g_lastBar = 0;
int      g_tradesToday = 0;
int      g_lastTradeDay = -1;
double   g_dayStartBalance = 0;

// SMI state (computed manually since MT5 has no built-in SMI)
double   g_smiLine = 0;
double   g_smiSignal = 0;
double   g_prevSmiLine = 0;
double   g_prevSmiSignal = 0;

// EMA helpers
double   g_ds1 = 0, g_hl1 = 0;  // First smooth of D and HL
double   g_ds2 = 0, g_hl2 = 0;  // Second smooth
bool     g_smiInit = false;
int      g_warmup = 0;

int OnInit()
{
   g_hATR14 = iATR(_Symbol, PERIOD_CURRENT, 14);
   g_hATR1  = iATR(_Symbol, PERIOD_CURRENT, 1);
   g_hTrend = iMA(_Symbol, PERIOD_CURRENT, InpTrendEMA, 0, MODE_EMA, PRICE_CLOSE);
   if(g_hATR14==INVALID_HANDLE||g_hATR1==INVALID_HANDLE||g_hTrend==INVALID_HANDLE)
      return INIT_FAILED;
   g_dayStartBalance = AccountInfoDouble(ACCOUNT_BALANCE);
   g_smiInit = false;
   g_warmup = 0;
   PrintFormat("[SMI] v1.00 | Period=%d Smooth1=%d Smooth2=%d Signal=%d",
               InpSMIPeriod, InpSMISmooth1, InpSMISmooth2, InpSMISignal);
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

//+------------------------------------------------------------------+
//| Update SMI calculation using bar[1] data (closed bar)             |
//| SMI = 100 * EMA(EMA(close - midpoint)) / (0.5 * EMA(EMA(HL)))  |
//+------------------------------------------------------------------+
void UpdateSMI()
{
   // Find highest high and lowest low over InpSMIPeriod bars starting at bar[1]
   double hh = -999999, ll = 999999;
   for(int i = 1; i <= InpSMIPeriod; i++)
   {
      double h = iHigh(_Symbol, PERIOD_CURRENT, i);
      double l = iLow(_Symbol, PERIOD_CURRENT, i);
      if(h > hh) hh = h;
      if(l < ll) ll = l;
   }

   double close1 = iClose(_Symbol, PERIOD_CURRENT, 1);
   double midpoint = (hh + ll) / 2.0;
   double D = close1 - midpoint;          // Distance from midpoint
   double HL = hh - ll;                   // Range

   g_warmup++;

   if(!g_smiInit)
   {
      g_ds1 = D;
      g_ds2 = D;
      g_hl1 = HL;
      g_hl2 = HL;
      g_smiLine = (g_hl2 != 0) ? 100.0 * g_ds2 / (0.5 * g_hl2) : 0;
      g_smiSignal = g_smiLine;
      g_prevSmiLine = g_smiLine;
      g_prevSmiSignal = g_smiSignal;
      g_smiInit = true;
      return;
   }

   // Save previous values for crossover detection
   g_prevSmiLine = g_smiLine;
   g_prevSmiSignal = g_smiSignal;

   // Double EMA smoothing of D
   double k1 = 2.0 / (InpSMISmooth1 + 1);
   double k2 = 2.0 / (InpSMISmooth2 + 1);
   g_ds1 = g_ds1 + k1 * (D - g_ds1);       // First smooth
   g_ds2 = g_ds2 + k2 * (g_ds1 - g_ds2);   // Second smooth

   // Double EMA smoothing of HL
   g_hl1 = g_hl1 + k1 * (HL - g_hl1);
   g_hl2 = g_hl2 + k2 * (g_hl1 - g_hl2);

   // SMI line
   if(g_hl2 > 0)
      g_smiLine = 100.0 * g_ds2 / (0.5 * g_hl2);
   else
      g_smiLine = 0;

   // Clamp to ±100
   if(g_smiLine > 100) g_smiLine = 100;
   if(g_smiLine < -100) g_smiLine = -100;

   // Signal line (EMA of SMI)
   double ks = 2.0 / (InpSMISignal + 1);
   g_smiSignal = g_smiSignal + ks * (g_smiLine - g_smiSignal);
}

int GetSignal()
{
   if(g_warmup < InpSMIPeriod + InpSMISmooth1 + InpSMISmooth2 + InpSMISignal)
      return 0;  // Not enough data yet

   // CI filter
   if(InpUseChop)
   {
      double ci = ComputeChoppiness(1);
      if(ci > InpChopMax) return 0;
   }

   // SMI crossover signal
   bool bullCross = (g_prevSmiLine <= g_prevSmiSignal && g_smiLine > g_smiSignal);
   bool bearCross = (g_prevSmiLine >= g_prevSmiSignal && g_smiLine < g_smiSignal);

   // Trend bias
   double trend[];
   ArraySetAsSeries(trend, true);
   if(CopyBuffer(g_hTrend, 0, 1, 1, trend) < 1) return 0;
   double close1 = iClose(_Symbol, PERIOD_CURRENT, 1);

   if(bullCross && g_smiLine > InpSMIThresh && close1 > trend[0]) return +1;
   if(bearCross && g_smiLine < -InpSMIThresh && close1 < trend[0]) return -1;

   return 0;
}

void OnTick()
{
   datetime barTime = iTime(_Symbol, PERIOD_CURRENT, 0);
   if(barTime == g_lastBar) return;
   g_lastBar = barTime;

   // Update SMI on every new bar
   UpdateSMI();

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
   req.comment=StringFormat("SMI|%.0f",g_smiLine);
   req.type_filling=ORDER_FILLING_FOK;
   if(!OrderSend(req,res)){req.type_filling=ORDER_FILLING_IOC;if(!OrderSend(req,res))return;}
   if(res.retcode==TRADE_RETCODE_DONE||res.retcode==TRADE_RETCODE_PLACED)
   { g_tradesToday++; PrintFormat("[SMI] %s %.2f @ %.2f smi=%.1f",isBuy?"BUY":"SELL",lot,res.price,g_smiLine); }
}

double OnTester()
{ double pf=TesterStatistics(STAT_PROFIT_FACTOR),n=TesterStatistics(STAT_TRADES); if(n<20) return 0; return pf*MathSqrt(n); }
