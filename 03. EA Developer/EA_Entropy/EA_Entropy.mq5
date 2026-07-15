//+------------------------------------------------------------------+
//| EA_Entropy.mq5 — Sample Entropy Predictability Filter             |
//| Symbol: XAUUSD+ / USDJPY+  |  Period: M15                        |
//|                                                                   |
//| PARADIGM SHIFT: Information Theory                                |
//| Sample Entropy (SampEn) measures the complexity/predictability    |
//| of a time series. LOW entropy = more structured/predictable =    |
//| better to trade. HIGH entropy = random walk = stay out.           |
//|                                                                   |
//| When SampEn drops below threshold → market entering structured   |
//| regime → detect direction via price slope → trade the structure. |
//|                                                                   |
//| This is fundamentally different from volatility-based filters:   |
//| - Low vol can be random (flat chop) or structured (tight trend)  |
//| - Low entropy specifically identifies STRUCTURE, not just low vol |
//|                                                                   |
//| Novelty: Type #83 — Information-theoretic predictability filter   |
//| SIGNALS ON BAR[1] ONLY — no repaint.                              |
//| Max | 2026-04-13 | v1.0                                          |
//+------------------------------------------------------------------+
#property copyright "Max — EA_Entropy v1.0"
#property version   "1.00"
#property strict

input group "=== General ==="
input ulong    InpMagic         = 216001;
input int      InpDeviation     = 30;

input group "=== Entropy Settings ==="
input int      InpEntropyLen    = 30;            // Window for entropy calculation
input int      InpEmbedDim      = 2;             // Embedding dimension (m)
input double   InpTolerance     = 0.2;           // Tolerance factor (r * stddev)
input double   InpEntropyMax    = 1.0;           // Max entropy to trade (lower = stricter)

input group "=== Direction ==="
input int      InpSlopePeriod   = 5;             // Bars for slope direction
input double   InpMinSlope      = 0.02;          // Min slope % to confirm direction

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

int      g_hATR = INVALID_HANDLE;
datetime g_lastBar = 0;
int      g_tradesToday = 0;
int      g_lastTradeDay = -1;
double   g_dayStartBalance = 0;

int OnInit()
{
   g_hATR = iATR(_Symbol, PERIOD_CURRENT, 14);
   if(g_hATR == INVALID_HANDLE) return INIT_FAILED;
   g_dayStartBalance = AccountInfoDouble(ACCOUNT_BALANCE);
   PrintFormat("[ENTROPY] v1.00 | Len=%d Dim=%d Tol=%.2f MaxEnt=%.2f",
               InpEntropyLen, InpEmbedDim, InpTolerance, InpEntropyMax);
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason) { if(g_hATR != INVALID_HANDLE) IndicatorRelease(g_hATR); }

int CountPositions()
{ int c=0;for(int i=PositionsTotal()-1;i>=0;i--){ulong t=PositionGetTicket(i);if(t>0&&PositionGetInteger(POSITION_MAGIC)==(long)InpMagic&&PositionGetString(POSITION_SYMBOL)==_Symbol)c++;}return c; }

void CloseAll()
{ for(int i=PositionsTotal()-1;i>=0;i--){ulong t=PositionGetTicket(i);if(t<=0||PositionGetInteger(POSITION_MAGIC)!=(long)InpMagic||PositionGetString(POSITION_SYMBOL)!=_Symbol)continue;MqlTradeRequest req={};MqlTradeResult res={};req.action=TRADE_ACTION_DEAL;req.symbol=_Symbol;req.volume=PositionGetDouble(POSITION_VOLUME);req.deviation=(ulong)InpDeviation;req.magic=InpMagic;req.position=t;if(PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_BUY){req.type=ORDER_TYPE_SELL;req.price=SymbolInfoDouble(_Symbol,SYMBOL_BID);}else{req.type=ORDER_TYPE_BUY;req.price=SymbolInfoDouble(_Symbol,SYMBOL_ASK);}req.type_filling=ORDER_FILLING_FOK;if(!OrderSend(req,res)){req.type_filling=ORDER_FILLING_IOC;OrderSend(req,res);}} }

bool IsDDExceeded()
{ if(g_dayStartBalance<=0)return false;return(g_dayStartBalance-AccountInfoDouble(ACCOUNT_EQUITY))/g_dayStartBalance*100.0>=InpDailyDD; }

double CalcLot(double sl)
{ if(sl<=0)return 0;double b=AccountInfoDouble(ACCOUNT_BALANCE),r=b*InpRiskPct/100.0;double tv=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_VALUE),ts=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);if(tv<=0||ts<=0)return 0;double lot=r/(sl/ts*tv);lot=MathMin(lot,InpMaxLot);lot=MathMin(lot,SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX));lot=MathMax(lot,SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN));lot=MathFloor(lot/SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP))*SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);return lot; }

//+------------------------------------------------------------------+
//| Compute Sample Entropy of close prices                            |
//| Returns: lower = more structured, higher = more random           |
//+------------------------------------------------------------------+
double ComputeSampleEntropy(int shift)
{
   int N = InpEntropyLen;
   int m = InpEmbedDim;

   // Collect returns (close-to-close changes)
   double data[];
   ArrayResize(data, N);
   for(int i = 0; i < N; i++)
   {
      double c1 = iClose(_Symbol, PERIOD_CURRENT, shift + i);
      double c2 = iClose(_Symbol, PERIOD_CURRENT, shift + i + 1);
      if(c2 <= 0) return 99.0;
      data[i] = (c1 - c2) / c2;  // return
   }

   // Compute standard deviation
   double mean = 0;
   for(int i = 0; i < N; i++) mean += data[i];
   mean /= N;
   double sd = 0;
   for(int i = 0; i < N; i++) sd += (data[i] - mean) * (data[i] - mean);
   sd = MathSqrt(sd / N);
   if(sd <= 0) return 0;  // constant series = perfectly structured

   double r = InpTolerance * sd;  // tolerance threshold

   // Count template matches for dimension m and m+1
   int Bm = 0, Am = 0;
   int totalBm = 0, totalAm = 0;

   for(int i = 0; i < N - m; i++)
   {
      for(int j = i + 1; j < N - m; j++)
      {
         // Check m-length match
         bool match_m = true;
         for(int k = 0; k < m; k++)
         {
            if(MathAbs(data[i+k] - data[j+k]) > r) { match_m = false; break; }
         }
         if(match_m) Bm++;
         totalBm++;

         // Check (m+1)-length match
         if(i < N - m - 1 && j < N - m - 1)
         {
            bool match_m1 = match_m;
            if(match_m1 && MathAbs(data[i+m] - data[j+m]) > r) match_m1 = false;
            if(match_m1) Am++;
            totalAm++;
         }
      }
   }

   if(Bm == 0 || totalBm == 0 || totalAm == 0) return 99.0;

   double pB = (double)Bm / totalBm;
   double pA = (double)Am / totalAm;

   if(pA <= 0 || pB <= 0) return 99.0;

   double sampEn = -MathLog(pA / pB);
   return sampEn;
}

int GetSignal()
{
   double entropy = ComputeSampleEntropy(1);

   // Only trade when entropy is LOW (structured market)
   if(entropy > InpEntropyMax) return 0;

   // Determine direction via price slope
   double closeNow = iClose(_Symbol, PERIOD_CURRENT, 1);
   double closePast = iClose(_Symbol, PERIOD_CURRENT, 1 + InpSlopePeriod);
   if(closePast <= 0) return 0;

   double slope = (closeNow - closePast) / closePast * 100.0;

   if(MathAbs(slope) < InpMinSlope) return 0;  // No clear direction

   PrintFormat("[ENTROPY] SampEn=%.3f (<%.1f) slope=%.3f%% dir=%s",
               entropy, InpEntropyMax, slope, slope > 0 ? "BUY" : "SELL");

   return slope > 0 ? +1 : -1;
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

   bool isBuy=(signal==+1);
   double ask=SymbolInfoDouble(_Symbol,SYMBOL_ASK),bid=SymbolInfoDouble(_Symbol,SYMBOL_BID);
   double entry=isBuy?ask:bid;
   double sl=isBuy?ask-slDist:bid+slDist, tp=isBuy?ask+slDist*InpTP_Ratio:bid-slDist*InpTP_Ratio;
   if(slDist<(int)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL)*_Point) return;
   double lot=CalcLot(slDist); if(lot<=0) return;
   int digits=(int)SymbolInfoInteger(_Symbol,SYMBOL_DIGITS);
   sl=NormalizeDouble(sl,digits); tp=NormalizeDouble(tp,digits);

   MqlTradeRequest req={}; MqlTradeResult res={};
   req.action=TRADE_ACTION_DEAL;req.symbol=_Symbol;req.volume=lot;
   req.type=isBuy?ORDER_TYPE_BUY:ORDER_TYPE_SELL;
   req.price=entry;req.sl=sl;req.tp=tp;
   req.deviation=(ulong)InpDeviation;req.magic=InpMagic;
   req.comment=StringFormat("ENTR|%.2f",ComputeSampleEntropy(1));
   req.type_filling=ORDER_FILLING_FOK;
   if(!OrderSend(req,res)){req.type_filling=ORDER_FILLING_IOC;if(!OrderSend(req,res))return;}
   if(res.retcode==TRADE_RETCODE_DONE||res.retcode==TRADE_RETCODE_PLACED)
   { g_tradesToday++; PrintFormat("[ENTROPY] %s %.2f @ %.2f SampEn=%.3f",isBuy?"BUY":"SELL",lot,res.price,ComputeSampleEntropy(1)); }
}

double OnTester()
{ double pf=TesterStatistics(STAT_PROFIT_FACTOR),n=TesterStatistics(STAT_TRADES); if(n<20) return 0; return pf*MathSqrt(n); }
