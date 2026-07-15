//+------------------------------------------------------------------+
//| EA_KalmanTrend.mq5 — Kalman Filter Trend Follower                 |
//| Symbol: USDJPY+  |  Period: M15                                   |
//|                                                                   |
//| PARADIGM: Optimal state estimation via Kalman Filter               |
//| Unlike EMA (fixed exponential decay), Kalman adapts its gain      |
//| based on prediction error — when prediction is good, trust the    |
//| model more; when prediction diverges from reality, increase       |
//| responsiveness. This is the OPTIMAL linear filter for noisy data. |
//|                                                                   |
//| Signal: Kalman slope (velocity estimate) + trend bias             |
//| When Kalman velocity is strongly positive/negative AND price      |
//| confirms trend → enter momentum trade.                            |
//|                                                                   |
//| Novelty: Type #87 — Kalman filter state-space trend estimation    |
//| SIGNALS ON BAR[1] ONLY — no repaint.                              |
//| Max | 2026-04-13 | v1.0                                          |
//+------------------------------------------------------------------+
#property copyright "Max — EA_KalmanTrend v1.0"
#property version   "1.00"
#property strict

input group "=== General ==="
input ulong    InpMagic         = 220001;
input int      InpDeviation     = 30;

input group "=== Kalman Filter ==="
input double   InpProcessNoise  = 0.01;          // Q: process noise (higher = more responsive)
input double   InpMeasureNoise  = 1.0;            // R: measurement noise (higher = smoother)
input double   InpVelocityThresh = 0.0001;        // Min Kalman velocity for signal
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

// Kalman state variables
double   g_kState    = 0;      // Estimated price level
double   g_kVelocity = 0;      // Estimated price velocity (slope)
double   g_kP[4];              // Error covariance matrix (2x2 flattened)
bool     g_kInit     = false;
double   g_prevVelocity = 0;   // Previous bar's velocity for crossover

int OnInit()
{
   g_hATR   = iATR(_Symbol, PERIOD_CURRENT, 14);
   g_hTrend = iMA(_Symbol, PERIOD_CURRENT, InpTrendEMA, 0, MODE_EMA, PRICE_CLOSE);
   if(g_hATR==INVALID_HANDLE||g_hTrend==INVALID_HANDLE) return INIT_FAILED;
   g_dayStartBalance = AccountInfoDouble(ACCOUNT_BALANCE);
   g_kInit = false;
   // Initialize P matrix
   g_kP[0] = 1.0; g_kP[1] = 0.0; g_kP[2] = 0.0; g_kP[3] = 1.0;
   PrintFormat("[KALMAN] v1.00 | Q=%.4f R=%.2f VelThresh=%.5f", InpProcessNoise, InpMeasureNoise, InpVelocityThresh);
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
//| Kalman Filter Update — Constant Velocity Model                    |
//| State: [price, velocity]                                          |
//| Transition: price(t+1) = price(t) + velocity(t)                  |
//|             velocity(t+1) = velocity(t)                           |
//| Measurement: observed close price                                 |
//+------------------------------------------------------------------+
void KalmanUpdate(double measurement)
{
   if(!g_kInit)
   {
      g_kState = measurement;
      g_kVelocity = 0;
      g_kP[0] = 1.0; g_kP[1] = 0.0; g_kP[2] = 0.0; g_kP[3] = 1.0;
      g_kInit = true;
      return;
   }

   // --- PREDICT ---
   // State prediction: x_pred = F * x
   double predState = g_kState + g_kVelocity;    // price + velocity
   double predVel   = g_kVelocity;                // velocity constant

   // Covariance prediction: P_pred = F * P * F' + Q
   // F = [[1,1],[0,1]]
   double pP00 = g_kP[0] + g_kP[2] + g_kP[1] + g_kP[3] + InpProcessNoise;
   double pP01 = g_kP[1] + g_kP[3];
   double pP10 = g_kP[2] + g_kP[3];
   double pP11 = g_kP[3] + InpProcessNoise;

   // --- UPDATE ---
   // Innovation: y = z - H * x_pred (H = [1, 0])
   double innovation = measurement - predState;

   // Innovation covariance: S = H * P_pred * H' + R
   double S = pP00 + InpMeasureNoise;
   if(MathAbs(S) < 1e-12) S = 1e-12;

   // Kalman gain: K = P_pred * H' / S
   double K0 = pP00 / S;
   double K1 = pP10 / S;

   // State update: x = x_pred + K * innovation
   g_prevVelocity = g_kVelocity;
   g_kState    = predState + K0 * innovation;
   g_kVelocity = predVel   + K1 * innovation;

   // Covariance update: P = (I - K*H) * P_pred
   g_kP[0] = pP00 - K0 * pP00;
   g_kP[1] = pP01 - K0 * pP01;
   g_kP[2] = pP10 - K1 * pP00;
   g_kP[3] = pP11 - K1 * pP01;
}

int GetSignal()
{
   // Kalman velocity = trend direction and strength
   double vel = g_kVelocity;

   // Need minimum velocity for signal
   if(MathAbs(vel) < InpVelocityThresh) return 0;

   // Fresh velocity signal: just crossed threshold or changed sign
   bool freshBull = (vel > InpVelocityThresh && g_prevVelocity <= InpVelocityThresh);
   bool freshBear = (vel < -InpVelocityThresh && g_prevVelocity >= -InpVelocityThresh);

   // Strong continuation: velocity increasing
   bool contBull = (vel > InpVelocityThresh * 2.0);
   bool contBear = (vel < -InpVelocityThresh * 2.0);

   // Trend bias
   double trend[];
   ArraySetAsSeries(trend, true);
   if(CopyBuffer(g_hTrend, 0, 1, 1, trend) < 1) return 0;
   double close1 = iClose(_Symbol, PERIOD_CURRENT, 1);

   if((freshBull || contBull) && close1 > trend[0]) return +1;
   if((freshBear || contBear) && close1 < trend[0]) return -1;
   return 0;
}

void OnTick()
{
   datetime barTime = iTime(_Symbol, PERIOD_CURRENT, 0);
   if(barTime == g_lastBar) return;
   g_lastBar = barTime;

   // Update Kalman with bar[1] close (closed bar only)
   double close1 = iClose(_Symbol, PERIOD_CURRENT, 1);
   if(close1 > 0) KalmanUpdate(close1);

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
   req.comment=StringFormat("KAL|v=%.5f",g_kVelocity);
   req.type_filling=ORDER_FILLING_FOK;
   if(!OrderSend(req,res)){req.type_filling=ORDER_FILLING_IOC;if(!OrderSend(req,res))return;}
   if(res.retcode==TRADE_RETCODE_DONE||res.retcode==TRADE_RETCODE_PLACED)
   { g_tradesToday++; PrintFormat("[KALMAN] %s %.2f @ %.2f vel=%.6f",isBuy?"BUY":"SELL",lot,res.price,g_kVelocity); }
}

double OnTester()
{ double pf=TesterStatistics(STAT_PROFIT_FACTOR),n=TesterStatistics(STAT_TRADES); if(n<20) return 0; return pf*MathSqrt(n); }
