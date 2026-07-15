//+------------------------------------------------------------------+
//| EA_H1OpenBreak.mq5 — H1 Candle Open Breakout                     |
//| Symbol: USDJPY+  |  Period: M5                                    |
//|                                                                   |
//| PARADIGM: Intrabar minute-level microstructure                     |
//| At the start of each H1 candle, there is a brief consolidation   |
//| followed by a directional push as pending orders fire.             |
//| This EA enters on a breakout of the first 2 M5 bars' range       |
//| (first 10 minutes) of each H1 candle.                            |
//|                                                                   |
//| HYPOTHESIS: The first 10 minutes of each H1 candle establish     |
//| initial direction. A breakout of this range within the hour       |
//| tends to continue due to stop cascades and momentum.              |
//|                                                                   |
//| SIGNAL: Calculate high/low of M5 bars 0-1 at start of each H1.  |
//| If price breaks above + CI trending + EMA50 up → BUY             |
//| If price breaks below + CI trending + EMA50 down → SELL          |
//|                                                                   |
//| NOTE: This MUST run on M5 to detect the 10-min range.            |
//|                                                                   |
//| Novelty: Type #102 — Intrabar H1 open breakout                   |
//| SIGNALS ON BAR[1] ONLY — no repaint.                              |
//| Max | 2026-04-13 | v1.0                                          |
//+------------------------------------------------------------------+
#property copyright "Max — EA_H1OpenBreak v1.0"
#property version   "1.00"
#property strict

input group "=== General ==="
input ulong    InpMagic         = 235001;
input int      InpDeviation     = 30;

input group "=== H1 Open Range ==="
input int      InpRangeBars     = 2;              // Number of M5 bars for range (2 = 10 min)
input double   InpBreakATRMult  = 0.3;            // Breakout buffer in ATR units

input group "=== Choppiness Filter (on H1) ==="
input int      InpChopPeriod    = 14;
input double   InpChopMax       = 50.0;

input group "=== Trend (on H1) ==="
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

int      g_hATR14_H1 = INVALID_HANDLE;
int      g_hTrend_H1 = INVALID_HANDLE;
int      g_hATR1_H1  = INVALID_HANDLE;
datetime g_lastBar = 0;
int      g_tradesToday = 0;
int      g_lastTradeDay = -1;
double   g_dayStartBalance = 0;

// H1 open range tracking
double   g_rangeHigh = 0;
double   g_rangeLow  = 0;
int      g_rangeBarCount = 0;
datetime g_currentH1Bar = 0;
bool     g_rangeComplete = false;
bool     g_tradedThisHour = false;

int OnInit()
{
   g_hATR14_H1 = iATR(_Symbol, PERIOD_H1, 14);
   g_hTrend_H1 = iMA(_Symbol, PERIOD_H1, InpTrendEMA, 0, MODE_EMA, PRICE_CLOSE);
   g_hATR1_H1  = iATR(_Symbol, PERIOD_H1, 1);
   if(g_hATR14_H1==INVALID_HANDLE||g_hTrend_H1==INVALID_HANDLE||g_hATR1_H1==INVALID_HANDLE)
      return INIT_FAILED;
   g_dayStartBalance = AccountInfoDouble(ACCOUNT_BALANCE);
   PrintFormat("[H1OB] v1.0 | RangeBars=%d BreakBuf=%.1f", InpRangeBars, InpBreakATRMult);
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   if(g_hATR14_H1!=INVALID_HANDLE) IndicatorRelease(g_hATR14_H1);
   if(g_hTrend_H1!=INVALID_HANDLE) IndicatorRelease(g_hTrend_H1);
   if(g_hATR1_H1!=INVALID_HANDLE)  IndicatorRelease(g_hATR1_H1);
}

int CountPositions()
{ int c=0;for(int i=PositionsTotal()-1;i>=0;i--){ulong t=PositionGetTicket(i);if(t>0&&PositionGetInteger(POSITION_MAGIC)==(long)InpMagic&&PositionGetString(POSITION_SYMBOL)==_Symbol)c++;}return c; }

bool IsSuccessfulRetcode(const uint retcode)
{ return(retcode==TRADE_RETCODE_DONE||retcode==TRADE_RETCODE_PLACED||retcode==TRADE_RETCODE_DONE_PARTIAL); }

bool IsRetryableRetcode(const uint retcode)
{ return(retcode==TRADE_RETCODE_REQUOTE||retcode==TRADE_RETCODE_PRICE_CHANGED||retcode==TRADE_RETCODE_PRICE_OFF||retcode==TRADE_RETCODE_CONNECTION||retcode==TRADE_RETCODE_TIMEOUT||retcode==TRADE_RETCODE_TOO_MANY_REQUESTS||retcode==TRADE_RETCODE_LOCKED); }

int ResolveFillModes(ENUM_ORDER_TYPE_FILLING &primary, ENUM_ORDER_TYPE_FILLING &secondary)
{
   long fillMask = 0;
   primary = ORDER_FILLING_FOK;
   secondary = ORDER_FILLING_IOC;
   if(!SymbolInfoInteger(_Symbol, SYMBOL_FILLING_MODE, fillMask))
      return 2;

   int count = 0;
   if((fillMask & SYMBOL_FILLING_FOK) == SYMBOL_FILLING_FOK)
   {
      primary = ORDER_FILLING_FOK;
      count++;
   }
   if((fillMask & SYMBOL_FILLING_IOC) == SYMBOL_FILLING_IOC)
   {
      if(count == 0) primary = ORDER_FILLING_IOC;
      else secondary = ORDER_FILLING_IOC;
      count++;
   }
   if(count == 0)
      return 1;
   return count;
}

bool ValidateStops(const bool isBuy, const double entryPrice, const double sl, const double tp)
{
   long stopsLevel = 0;
   long freezeLevel = 0;
   SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL, stopsLevel);
   SymbolInfoInteger(_Symbol, SYMBOL_TRADE_FREEZE_LEVEL, freezeLevel);
   double minDistance = (double)MathMax(stopsLevel, freezeLevel) * _Point;
   if(minDistance <= 0.0)
      return true;
   if(isBuy)
      return ((entryPrice - sl) >= minDistance && (tp - entryPrice) >= minDistance);
   return ((sl - entryPrice) >= minDistance && (entryPrice - tp) >= minDistance);
}

bool SendDealWithRetry(const ENUM_ORDER_TYPE type, const double volume, const double sl, const double tp, const ulong position, const string comment, MqlTradeResult &res)
{
   ENUM_ORDER_TYPE_FILLING primaryMode, secondaryMode;
   int modeCount = ResolveFillModes(primaryMode, secondaryMode);

   for(int modeIdx = 0; modeIdx < modeCount; modeIdx++)
   {
      ENUM_ORDER_TYPE_FILLING activeMode = (modeIdx == 0 ? primaryMode : secondaryMode);
      for(int attempt = 0; attempt < 3; attempt++)
      {
         double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
         double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
         MqlTradeRequest req = {};
         MqlTradeResult tmp = {};
         req.action = TRADE_ACTION_DEAL;
         req.symbol = _Symbol;
         req.volume = volume;
         req.type = type;
         req.price = (type == ORDER_TYPE_BUY ? ask : bid);
         req.sl = sl;
         req.tp = tp;
         req.deviation = (ulong)InpDeviation;
         req.magic = InpMagic;
         req.position = position;
         req.comment = comment;
         req.type_filling = activeMode;

         if(position == 0 && sl > 0.0 && tp > 0.0 && !ValidateStops(type == ORDER_TYPE_BUY, req.price, sl, tp))
            return false;

         ResetLastError();
         bool sent = OrderSend(req, tmp);
         int err = GetLastError();
         res = tmp;

         if(sent && IsSuccessfulRetcode(res.retcode))
            return true;
         if(sent && !IsRetryableRetcode(res.retcode))
            return false;
         if(!sent && attempt == 2)
            return false;

         Sleep(100 * (1 << attempt));
      }
   }
   return false;
}

void CloseAll()
{ for(int i=PositionsTotal()-1;i>=0;i--){ulong t=PositionGetTicket(i);if(t<=0||PositionGetInteger(POSITION_MAGIC)!=(long)InpMagic||PositionGetString(POSITION_SYMBOL)!=_Symbol)continue;bool isBuy=(PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_BUY);MqlTradeResult res={};if(!SendDealWithRetry(isBuy?ORDER_TYPE_SELL:ORDER_TYPE_BUY,PositionGetDouble(POSITION_VOLUME),0.0,0.0,t,"H1OB|exit",res))PrintFormat("[H1OB] Close failed ticket=%I64u retcode=%u",t,res.retcode);} }

bool IsDDExceeded()
{ if(g_dayStartBalance<=0)return false;return(g_dayStartBalance-AccountInfoDouble(ACCOUNT_EQUITY))/g_dayStartBalance*100.0>=InpDailyDD; }

double CalcLot(double sl)
{ if(sl<=0)return 0;double b=AccountInfoDouble(ACCOUNT_BALANCE),r=b*InpRiskPct/100.0;double tv=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_VALUE),ts=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);if(tv<=0||ts<=0)return 0;double lot=r/(sl/ts*tv);lot=MathMin(lot,InpMaxLot);lot=MathMin(lot,SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX));lot=MathMax(lot,SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN));lot=MathFloor(lot/SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP))*SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);return lot; }

double ComputeChoppiness_H1(int shift)
{
   double atrSum = 0;
   double atr1[];
   ArraySetAsSeries(atr1, true);
   if(CopyBuffer(g_hATR1_H1, 0, shift, InpChopPeriod, atr1) < InpChopPeriod) return 50.0;
   for(int i = 0; i < InpChopPeriod; i++) atrSum += atr1[i];
   double hh = -999999, ll = 999999;
   for(int i = shift; i < shift + InpChopPeriod; i++)
   {
      double h = iHigh(_Symbol, PERIOD_H1, i);
      double l = iLow(_Symbol, PERIOD_H1, i);
      if(h > hh) hh = h;
      if(l < ll) ll = l;
   }
   double range = hh - ll;
   if(range <= 0 || atrSum <= 0) return 50.0;
   return 100.0 * MathLog10(atrSum / range) / MathLog10((double)InpChopPeriod);
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
   if(InpSkipMon && dt.day_of_week == 1) return;
   if(InpSkipTue && dt.day_of_week == 2) return;
   if(InpSkipWed && dt.day_of_week == 3) return;
   if(InpSkipThu && dt.day_of_week == 4) return;
   if(InpSkipFri && dt.day_of_week == 5) return;

   // Detect H1 candle boundary
   datetime h1BarTime = iTime(_Symbol, PERIOD_H1, 0);
   if(h1BarTime != g_currentH1Bar)
   {
      // New H1 candle — reset range
      g_currentH1Bar = h1BarTime;
      g_rangeBarCount = 0;
      g_rangeHigh = 0;
      g_rangeLow = 999999;
      g_rangeComplete = false;
      g_tradedThisHour = false;
   }

   // Build range from completed M5 bars
   if(!g_rangeComplete)
   {
      // Use bar[1] data (completed bar)
      double h1 = iHigh(_Symbol, PERIOD_CURRENT, 1);
      double l1 = iLow(_Symbol, PERIOD_CURRENT, 1);

      // Check if bar[1] belongs to current H1
      datetime bar1Time = iTime(_Symbol, PERIOD_CURRENT, 1);
      if(bar1Time >= g_currentH1Bar)
      {
         if(h1 > g_rangeHigh) g_rangeHigh = h1;
         if(l1 < g_rangeLow)  g_rangeLow = l1;
         g_rangeBarCount++;
      }

      if(g_rangeBarCount >= InpRangeBars)
         g_rangeComplete = true;

      return;  // Don't trade during range formation
   }

   // Range is set — look for breakout
   if(g_tradedThisHour || g_tradesToday >= InpMaxPerDay || CountPositions() > 0 || IsDDExceeded()) return;

   double close1 = iClose(_Symbol, PERIOD_CURRENT, 1);
   double rangeSize = g_rangeHigh - g_rangeLow;
   if(rangeSize <= 0) return;

   // ATR buffer
   double atrH1[];
   ArraySetAsSeries(atrH1, true);
   if(CopyBuffer(g_hATR14_H1, 0, 1, 1, atrH1) < 1) return;
   double buffer = atrH1[0] * InpBreakATRMult;

   bool breakUp   = (close1 > g_rangeHigh + buffer);
   bool breakDown = (close1 < g_rangeLow - buffer);
   if(!breakUp && !breakDown) return;

   // CI filter on H1
   double ci = ComputeChoppiness_H1(1);
   if(ci > InpChopMax) return;

   // Trend on H1
   double trend[];
   ArraySetAsSeries(trend, true);
   if(CopyBuffer(g_hTrend_H1, 0, 1, 1, trend) < 1) return;

   int signal = 0;
   if(breakUp && close1 > trend[0]) signal = +1;
   if(breakDown && close1 < trend[0]) signal = -1;
   if(signal == 0) return;

   double slDist = atrH1[0] * InpSL_ATR_Mult;
   if(slDist < InpMinSLPoints*_Point) slDist = InpMinSLPoints*_Point;
   if(slDist > InpMaxSLPoints*_Point) return;

   bool isBuy=(signal==+1);
   double ask=SymbolInfoDouble(_Symbol,SYMBOL_ASK),bid=SymbolInfoDouble(_Symbol,SYMBOL_BID);
   double sl=isBuy?ask-slDist:bid+slDist, tp=isBuy?ask+slDist*InpTP_Ratio:bid-slDist*InpTP_Ratio;
   if(slDist<(int)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL)*_Point) return;
   double lot=CalcLot(slDist); if(lot<=0) return;
   int digits=(int)SymbolInfoInteger(_Symbol,SYMBOL_DIGITS);
   sl=NormalizeDouble(sl,digits); tp=NormalizeDouble(tp,digits);

   MqlTradeResult res={};
   if(!SendDealWithRetry(isBuy?ORDER_TYPE_BUY:ORDER_TYPE_SELL,lot,sl,tp,0,"H1OB|brk",res))
      return;
   if(IsSuccessfulRetcode(res.retcode))
   { g_tradesToday++; g_tradedThisHour=true; PrintFormat("[H1OB] %s %.2f @ %.2f range=[%.5f-%.5f]",isBuy?"BUY":"SELL",lot,res.price,g_rangeLow,g_rangeHigh); }
}

double OnTester()
{ double pf=TesterStatistics(STAT_PROFIT_FACTOR),n=TesterStatistics(STAT_TRADES); if(n<20) return 0; return pf*MathSqrt(n); }
