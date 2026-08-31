#ifndef HIS_HELPERS_MQH
#define HIS_HELPERS_MQH

double HIS_PipSize()
{
   double point = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   int digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
   if(digits == 3 || digits == 5)
      return point * 10.0;
   return point;
}

double HIS_SpreadPips()
{
   long spreadPts = 0;
   if(SymbolInfoInteger(_Symbol, SYMBOL_SPREAD, spreadPts) && spreadPts > 0)
   {
      int digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
      double ptsPerPip = (digits == 3 || digits == 5) ? 10.0 : 1.0;
      return (double)spreadPts / ptsPerPip;
   }
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double pip = HIS_PipSize();
   if(pip <= 0.0)
      return 999.0;
   return (ask - bid) / pip;
}

bool HIS_CopyClosedRates(const ENUM_TIMEFRAMES tf, const int count, MqlRates &rates[])
{
   ArraySetAsSeries(rates, true);
   int got = CopyRates(_Symbol, tf, 1, count, rates); // shift>=1 closed bars
   return (got >= count);
}

bool HIS_CopyClosedBuffer(const int handle, const int count, double &buf[])
{
   if(handle == INVALID_HANDLE)
      return false;
   ArraySetAsSeries(buf, true);
   int got = CopyBuffer(handle, 0, 1, count, buf);
   return (got >= count);
}

bool HIS_IsSwingHigh(const MqlRates &rates[], const int i, const int strength)
{
   if(i < strength)
      return false;
   for(int k = 1; k <= strength; k++)
   {
      if(rates[i].high <= rates[i - k].high || rates[i].high <= rates[i + k].high)
         return false;
   }
   return true;
}

bool HIS_IsSwingLow(const MqlRates &rates[], const int i, const int strength)
{
   if(i < strength)
      return false;
   for(int k = 1; k <= strength; k++)
   {
      if(rates[i].low >= rates[i - k].low || rates[i].low >= rates[i + k].low)
         return false;
   }
   return true;
}

double HIS_NormalizeLot(const double lots)
{
   double minLot = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double maxLot = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   double step = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   if(step <= 0.0)
      step = 0.01;
   double v = MathFloor(lots / step) * step;
   if(v < minLot)
      v = 0.0;
   if(v > maxLot)
      v = maxLot;
   return NormalizeDouble(v, 2);
}

double HIS_LotsForRisk(const double riskPct, const double slDistancePrice, const double maxLot)
{
   if(slDistancePrice <= 0.0 || riskPct <= 0.0)
      return 0.0;
   double equity = AccountInfoDouble(ACCOUNT_EQUITY);
   double riskMoney = equity * riskPct / 100.0;
   double tickSize = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   double tickValue = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
   if(tickSize <= 0.0 || tickValue <= 0.0)
      return 0.0;
   double lossPerLot = (slDistancePrice / tickSize) * tickValue;
   if(lossPerLot <= 0.0)
      return 0.0;
   double lots = riskMoney / lossPerLot;
   if(lots > maxLot)
      lots = maxLot;
   return HIS_NormalizeLot(lots);
}

#endif
