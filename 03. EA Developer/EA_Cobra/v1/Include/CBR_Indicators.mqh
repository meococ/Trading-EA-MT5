//+------------------------------------------------------------------+
//| CBR_Indicators.mqh — Cached Indicator Access                     |
//+------------------------------------------------------------------+
#ifndef CBR_INDICATORS_MQH
#define CBR_INDICATORS_MQH

#include "CBR_Config.mqh"

//--- Indicator handles (global)
int g_cbrATR    = INVALID_HANDLE;
int g_cbrBB     = INVALID_HANDLE;
int g_cbrEmaF   = INVALID_HANDLE;   // Fast EMA on H1
int g_cbrEmaS   = INVALID_HANDLE;   // Slow EMA on H1
double g_cbrPt   = 0.0;             // Point value

//+------------------------------------------------------------------+
//| Init all indicators                                              |
//+------------------------------------------------------------------+
bool CBR_InitIndicators(string symbol)
{
   g_cbrPt = SymbolInfoDouble(symbol, SYMBOL_POINT);
   if(g_cbrPt == 0.0) g_cbrPt = 0.00001;

   // ATR(14) on M15
   g_cbrATR = iATR(symbol, PERIOD_M15, CBR_ATR_PERIOD);
   if(g_cbrATR == INVALID_HANDLE)
   { Print("[CBR] FAIL: iATR"); return false; }

   // BB(20,2.0) on M15
   g_cbrBB = iBands(symbol, PERIOD_M15, CBR_BB_PERIOD, 0, CBR_BB_DEV, PRICE_CLOSE);
   if(g_cbrBB == INVALID_HANDLE)
   { Print("[CBR] FAIL: iBands"); return false; }

   // EMA21 on H1 (trend)
   g_cbrEmaF = iMA(symbol, PERIOD_H1, CBR_EMA_FAST, 0, MODE_EMA, PRICE_CLOSE);
   if(g_cbrEmaF == INVALID_HANDLE)
   { Print("[CBR] FAIL: iMA fast"); return false; }

   // EMA55 on H1 (trend)
   g_cbrEmaS = iMA(symbol, PERIOD_H1, CBR_EMA_SLOW, 0, MODE_EMA, PRICE_CLOSE);
   if(g_cbrEmaS == INVALID_HANDLE)
   { Print("[CBR] FAIL: iMA slow"); return false; }

   return true;
}

//+------------------------------------------------------------------+
//| Release indicator handles                                        |
//+------------------------------------------------------------------+
void CBR_DeinitIndicators()
{
   if(g_cbrATR != INVALID_HANDLE)  { IndicatorRelease(g_cbrATR);  g_cbrATR  = INVALID_HANDLE; }
   if(g_cbrBB  != INVALID_HANDLE)  { IndicatorRelease(g_cbrBB);   g_cbrBB   = INVALID_HANDLE; }
   if(g_cbrEmaF != INVALID_HANDLE) { IndicatorRelease(g_cbrEmaF); g_cbrEmaF = INVALID_HANDLE; }
   if(g_cbrEmaS != INVALID_HANDLE) { IndicatorRelease(g_cbrEmaS); g_cbrEmaS = INVALID_HANDLE; }
}

//+------------------------------------------------------------------+
//| Get ATR value at shift                                           |
//+------------------------------------------------------------------+
double CBR_GetATR(int shift)
{
   double buf[1];
   if(CopyBuffer(g_cbrATR, 0, shift, 1, buf) != 1) return 0.0;
   return buf[0];
}

//+------------------------------------------------------------------+
//| Get BB values at shift                                           |
//+------------------------------------------------------------------+
bool CBR_GetBB(int shift, double &upper, double &middle, double &lower)
{
   double bU[1], bM[1], bL[1];
   if(CopyBuffer(g_cbrBB, 1, shift, 1, bU) != 1) return false;  // Upper
   if(CopyBuffer(g_cbrBB, 0, shift, 1, bM) != 1) return false;  // Middle
   if(CopyBuffer(g_cbrBB, 2, shift, 1, bL) != 1) return false;  // Lower
   upper  = bU[0];
   middle = bM[0];
   lower  = bL[0];
   return true;
}

//+------------------------------------------------------------------+
//| Calculate BB Width Percentile (squeeze detection)                |
//+------------------------------------------------------------------+
double CBR_CalcBBWPercentile(string symbol)
{
   double upperArr[], middleArr[], lowerArr[];
   int lookback = CBR_BBW_LOOKBACK;

   ArrayResize(upperArr, lookback);
   ArrayResize(middleArr, lookback);
   ArrayResize(lowerArr, lookback);

   if(CopyBuffer(g_cbrBB, 1, 1, lookback, upperArr) != lookback) return 50.0;
   if(CopyBuffer(g_cbrBB, 0, 1, lookback, middleArr) != lookback) return 50.0;
   if(CopyBuffer(g_cbrBB, 2, 1, lookback, lowerArr) != lookback) return 50.0;

   // Calculate BB width for each bar
   double widths[];
   ArrayResize(widths, lookback);
   for(int i = 0; i < lookback; i++)
   {
      double mid = middleArr[i];
      if(mid > 0.0)
         widths[i] = (upperArr[i] - lowerArr[i]) / mid * 100.0;
      else
         widths[i] = 0.0;
   }

   // Current BB width (bar[1])
   double currentWidth = widths[0];

   // Percentile: how many values are BELOW current
   int below = 0;
   for(int i = 1; i < lookback; i++)
   {
      if(widths[i] < currentWidth)
         below++;
   }

   return (double)below / (double)(lookback - 1) * 100.0;
}

//+------------------------------------------------------------------+
//| Get EMA values at current bar (H1)                               |
//+------------------------------------------------------------------+
bool CBR_GetEMA(double &fast, double &slow)
{
   double fBuf[1], sBuf[1];
   if(CopyBuffer(g_cbrEmaF, 0, 0, 1, fBuf) != 1) return false;
   if(CopyBuffer(g_cbrEmaS, 0, 0, 1, sBuf) != 1) return false;
   fast = fBuf[0];
   slow = sBuf[0];
   return true;
}

//+------------------------------------------------------------------+
//| Get trend bias from EMA alignment                                |
//+------------------------------------------------------------------+
int CBR_GetBias(string symbol)
{
   double emaF, emaS;
   if(!CBR_GetEMA(emaF, emaS)) return 0;

   double price = iClose(symbol, PERIOD_H1, 0);
   double dist  = MathAbs(price - (emaF + emaS) / 2.0) / g_cbrPt;

   // Price above both EMAs + EMAs aligned = BULL
   if(price > emaF && emaF > emaS && dist >= CBR_TREND_MIN_DIST)
      return 1;

   // Price below both EMAs + EMAs aligned = BEAR
   if(price < emaF && emaF < emaS && dist >= CBR_TREND_MIN_DIST)
      return -1;

   return 0;   // No clear bias
}

#endif // CBR_INDICATORS_MQH
