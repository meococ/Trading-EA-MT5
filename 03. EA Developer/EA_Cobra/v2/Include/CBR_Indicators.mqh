//+------------------------------------------------------------------+
//| CBR_Indicators.mqh — Cached Indicator Access (v2)                |
//| Same as v1 — no changes needed                                   |
//+------------------------------------------------------------------+
#ifndef CBR_INDICATORS_MQH
#define CBR_INDICATORS_MQH

#include "CBR_Config.mqh"

//--- Indicator handles (global)
int g_cbrATR    = INVALID_HANDLE;
int g_cbrBB     = INVALID_HANDLE;
int g_cbrEmaF   = INVALID_HANDLE;
int g_cbrEmaS   = INVALID_HANDLE;
int g_cbrEmaD1  = INVALID_HANDLE;
double g_cbrPt   = 0.0;

//+------------------------------------------------------------------+
//| Init all indicators                                              |
//+------------------------------------------------------------------+
bool CBR_InitIndicators(string symbol)
{
   g_cbrPt = SymbolInfoDouble(symbol, SYMBOL_POINT);
   if(g_cbrPt == 0.0) g_cbrPt = 0.00001;

   g_cbrATR = iATR(symbol, PERIOD_M15, CBR_ATR_PERIOD);
   if(g_cbrATR == INVALID_HANDLE)
   { Print("[CBR] FAIL: iATR"); return false; }

   g_cbrBB = iBands(symbol, PERIOD_M15, CBR_BB_PERIOD, 0, CBR_BB_DEV, PRICE_CLOSE);
   if(g_cbrBB == INVALID_HANDLE)
   { Print("[CBR] FAIL: iBands"); return false; }

   g_cbrEmaF = iMA(symbol, PERIOD_H1, CBR_EMA_FAST, 0, MODE_EMA, PRICE_CLOSE);
   if(g_cbrEmaF == INVALID_HANDLE)
   { Print("[CBR] FAIL: iMA fast"); return false; }

   g_cbrEmaS = iMA(symbol, PERIOD_H1, CBR_EMA_SLOW, 0, MODE_EMA, PRICE_CLOSE);
   if(g_cbrEmaS == INVALID_HANDLE)
   { Print("[CBR] FAIL: iMA slow"); return false; }

   g_cbrEmaD1 = iMA(symbol, PERIOD_D1, 50, 0, MODE_EMA, PRICE_CLOSE);
   if(g_cbrEmaD1 == INVALID_HANDLE)
      Print("[CBR] WARN: iMA D1 50 unavailable — regime filter disabled");

   return true;
}

void CBR_DeinitIndicators()
{
   if(g_cbrATR != INVALID_HANDLE)  { IndicatorRelease(g_cbrATR);  g_cbrATR  = INVALID_HANDLE; }
   if(g_cbrBB  != INVALID_HANDLE)  { IndicatorRelease(g_cbrBB);   g_cbrBB   = INVALID_HANDLE; }
   if(g_cbrEmaF != INVALID_HANDLE) { IndicatorRelease(g_cbrEmaF); g_cbrEmaF = INVALID_HANDLE; }
   if(g_cbrEmaS != INVALID_HANDLE) { IndicatorRelease(g_cbrEmaS); g_cbrEmaS = INVALID_HANDLE; }
   if(g_cbrEmaD1 != INVALID_HANDLE) { IndicatorRelease(g_cbrEmaD1); g_cbrEmaD1 = INVALID_HANDLE; }
}

double CBR_GetATR(int shift)
{
   double buf[1];
   if(CopyBuffer(g_cbrATR, 0, shift, 1, buf) != 1) return 0.0;
   return buf[0];
}

bool CBR_GetBB(int shift, double &upper, double &middle, double &lower)
{
   double bU[1], bM[1], bL[1];
   if(CopyBuffer(g_cbrBB, 1, shift, 1, bU) != 1) return false;
   if(CopyBuffer(g_cbrBB, 0, shift, 1, bM) != 1) return false;
   if(CopyBuffer(g_cbrBB, 2, shift, 1, bL) != 1) return false;
   upper  = bU[0];
   middle = bM[0];
   lower  = bL[0];
   return true;
}

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

   double currentWidth = widths[0];
   int below = 0;
   for(int i = 1; i < lookback; i++)
   {
      if(widths[i] < currentWidth)
         below++;
   }

   return (double)below / (double)(lookback - 1) * 100.0;
}

bool CBR_GetEMA(double &fast, double &slow)
{
   double fBuf[1], sBuf[1];
   if(CopyBuffer(g_cbrEmaF, 0, 1, 1, fBuf) != 1) return false;  // v2.5.1: shift=1 (closed bar, non-repaint)
   if(CopyBuffer(g_cbrEmaS, 0, 1, 1, sBuf) != 1) return false;  // v2.5.1: shift=1 (closed bar, non-repaint)
   fast = fBuf[0];
   slow = sBuf[0];
   return true;
}

int CBR_GetBias(string symbol)
{
   double emaF, emaS;
   if(!CBR_GetEMA(emaF, emaS)) return 0;

   double price = iClose(symbol, PERIOD_H1, 1);  // v2.5.1: shift=1 (closed bar, non-repaint)
   double dist  = MathAbs(price - (emaF + emaS) / 2.0) / g_cbrPt;

   if(price > emaF && emaF > emaS && dist >= CBR_TREND_MIN_DIST)
      return 1;
   if(price < emaF && emaF < emaS && dist >= CBR_TREND_MIN_DIST)
      return -1;

   return 0;
}

//+------------------------------------------------------------------+
//| D1 regime multiplier: 1.0 trending, 0.5 sideways                 |
//| Uses D1 EMA(50) slope over 5 bars (1 week). Non-repaint: shift≥2 |
//+------------------------------------------------------------------+
double CBR_GetD1RegimeMult()
{
   double ema[6];
   if(CopyBuffer(g_cbrEmaD1, 0, 1, 6, ema) != 6)
      return 1.0;  // safe default: full size if data unavailable

   // slope = average daily change over last 5 D1 bars
   double slope = (ema[5] - ema[0]) / 5.0;

   // threshold: 2.0 USD/day for gold (adjust if needed)
   if(MathAbs(slope) >= 2.0)
      return 1.0;   // trending → full size
   else
      return 0.5;   // sideways → half size
}

#endif // CBR_INDICATORS_MQH
