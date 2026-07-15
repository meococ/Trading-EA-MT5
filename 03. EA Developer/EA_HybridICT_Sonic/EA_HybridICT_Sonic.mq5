//+------------------------------------------------------------------+
//| EA_HybridICT_Sonic.mq5                                            |
//| Active hyp surface: HYP-HIS-SL-SIGATR-M15-EUR-001 (Owner)           |
//| DIAG parent: HYP-HIS-DIAG-GATECOUNT-M15-EUR-001                     |
//| Empty parent: HYP-HYBRID-ICT-SONIC-M15-EURGBP-001                   |
//| Closed-bar only (shift>=1). Not promotion-ready.                  |
//+------------------------------------------------------------------+
#property copyright "Owner Path-C / Hybrid ICT-Sonic"
#property version   "1.02"
#property strict

#include <Trade\Trade.mqh>
#include "Include/HIS_Helpers.mqh"

input group "=== Engine ==="
input bool     InpEnabled              = true;
input ulong    InpMagic                = 20260715;
input string   InpComment              = "HIS";
input bool     InpKillSwitch           = false;
input int      InpDeviation            = 30;
input bool     InpDiagGateLog          = true;   // DIAG: Print counters OnDeinit

input group "=== Dragon / Structure ==="
input int      InpDragonPeriod         = 34;
input int      InpATRPeriod            = 14;
input int      InpSwingStrength        = 2;
input int      InpH4Lookback           = 80;
input int      InpM15Lookback          = 80;
input int      InpFvgMaxAgeH4          = 60;
input double   InpLevelTouchATR        = 0.50;   // proximity to FVG/liq/OB

input group "=== Wave / PVSRA / Confirm ==="
input int      InpWaveLookback         = 40;
input bool     InpRequireWave          = true;
input bool     InpRequirePvsraClimax   = true;
input int      InpVolAvgBars           = 20;
input double   InpVolClimaxMult        = 1.5;
input bool     InpRequireMacdSlope     = false;  // report: optional confirm
input int      InpMacdFast             = 12;
input int      InpMacdSlow             = 26;
input int      InpMacdSignal           = 9;

input group "=== Entry / Exit ==="
input double   InpPendingOffsetPips    = 4.0;
input int      InpPendingTtlBars       = 4;
input double   InpTargetRR             = 2.5;
input bool     InpUseLevelSl           = false;  // SIGATR hyp: false = signal±ATR only
input double   InpSlAtrMult            = 1.0;    // SL beyond signal extreme by this×ATR
input bool     InpUseDragonSlFloor     = false;  // never with SIGATR; kept for ablation
input double   InpDragonSlBufferPips   = 40.0;
input double   InpSlAtrBuffer          = 0.10;   // legacy extra when UseLevelSl
input double   InpMaxSlAtrMult         = 2.50;   // hard skip if SL wider than this×ATR
input bool     InpUseBreakEven         = true;
input double   InpBeTriggerPips        = 50.0;
input int      InpMaxHoldHours         = 24;

input group "=== Session / Filters ==="
input int      InpSessionStartHour     = 7;      // with GMT flag: wall UTC; else broker server
input int      InpSessionEndHour       = 20;
input bool     InpUseGmtSession        = true;
input double   InpMaxSpreadPips        = 4.0;    // majors; tester "current" can exceed 2.5
input bool     InpUseAtrRegime         = true;
input int      InpAtrMaPeriod          = 50;
input double   InpMinAtrRatio          = 0.70;
input double   InpMaxAtrRatio          = 3.00;

input group "=== Risk (prop) ==="
input double   InpRiskPct              = 0.25;
input double   InpMaxLot               = 1.0;
input double   InpDailyLossPct         = 2.0;
input int      InpMaxTradesPerDay      = 5;
input int      InpMaxPositions         = 1;

//--- handles
int g_hDragonHigh = INVALID_HANDLE;
int g_hDragonMid  = INVALID_HANDLE;
int g_hDragonLow  = INVALID_HANDLE;
int g_hATR        = INVALID_HANDLE;
int g_hAtrMa      = INVALID_HANDLE;
int g_hMACD       = INVALID_HANDLE;

CTrade   g_trade;
datetime g_lastBarTime = 0;
int      g_tradesToday = 0;
int      g_lastTradeDay = -1;
double   g_dayStartEquity = 0.0;

datetime g_pendingTime = 0;
int      g_pendingDir = 0;
int      g_pendingBarsLeft = 0;

// DIAG gate counters (closed-bar EvaluateSignal path)
long g_cnt_eval = 0;
long g_cnt_atr = 0;
long g_cnt_bias = 0;
long g_cnt_level_obj = 0;
long g_cnt_near = 0;
long g_cnt_wave = 0;
long g_cnt_dragon = 0;
long g_cnt_pvsra = 0;
long g_cnt_sl_fail = 0;
long g_cnt_sl_ok = 0;
long g_cnt_pending_ok = 0;
long g_cnt_pending_fail = 0;

//+------------------------------------------------------------------+
int OnInit()
{
   g_trade.SetExpertMagicNumber((long)InpMagic);
   g_trade.SetDeviationInPoints(InpDeviation);
   g_trade.SetTypeFillingBySymbol(_Symbol);

   g_hDragonHigh = iMA(_Symbol, PERIOD_M15, InpDragonPeriod, 0, MODE_EMA, PRICE_HIGH);
   g_hDragonMid  = iMA(_Symbol, PERIOD_M15, InpDragonPeriod, 0, MODE_EMA, PRICE_CLOSE);
   g_hDragonLow  = iMA(_Symbol, PERIOD_M15, InpDragonPeriod, 0, MODE_EMA, PRICE_LOW);
   g_hATR        = iATR(_Symbol, PERIOD_M15, InpATRPeriod);
   g_hAtrMa      = iMA(_Symbol, PERIOD_M15, InpAtrMaPeriod, 0, MODE_SMA, PRICE_CLOSE); // placeholder; regime uses ATR series
   g_hMACD       = iMACD(_Symbol, PERIOD_M15, InpMacdFast, InpMacdSlow, InpMacdSignal, PRICE_CLOSE);

   if(g_hDragonHigh == INVALID_HANDLE || g_hDragonMid == INVALID_HANDLE ||
      g_hDragonLow == INVALID_HANDLE || g_hATR == INVALID_HANDLE ||
      g_hMACD == INVALID_HANDLE)
   {
      Print("[HIS] indicator init failed");
      return INIT_FAILED;
   }

   // ATR MA via separate ATR buffer average in code; release unused handle
   if(g_hAtrMa != INVALID_HANDLE)
   {
      IndicatorRelease(g_hAtrMa);
      g_hAtrMa = INVALID_HANDLE;
   }

   g_dayStartEquity = AccountInfoDouble(ACCOUNT_EQUITY);
   Print("[HIS] HYP-HIS-SL-SIGATR-M15-EUR-001 init OK UseLevelSl=",
         InpUseLevelSl, " SlAtrMult=", InpSlAtrMult,
         " DragonSlFloor=", InpUseDragonSlFloor);
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   if(InpDiagGateLog)
   {
      Print("[HIS][DIAG] eval=", g_cnt_eval,
            " atr=", g_cnt_atr,
            " bias=", g_cnt_bias,
            " levelObj=", g_cnt_level_obj,
            " near=", g_cnt_near,
            " wave=", g_cnt_wave,
            " dragon=", g_cnt_dragon,
            " pvsra=", g_cnt_pvsra,
            " slFail=", g_cnt_sl_fail,
            " slOk=", g_cnt_sl_ok,
            " pendingOk=", g_cnt_pending_ok,
            " pendingFail=", g_cnt_pending_fail);
   }
   if(g_hDragonHigh != INVALID_HANDLE) IndicatorRelease(g_hDragonHigh);
   if(g_hDragonMid  != INVALID_HANDLE) IndicatorRelease(g_hDragonMid);
   if(g_hDragonLow  != INVALID_HANDLE) IndicatorRelease(g_hDragonLow);
   if(g_hATR        != INVALID_HANDLE) IndicatorRelease(g_hATR);
   if(g_hMACD       != INVALID_HANDLE) IndicatorRelease(g_hMACD);
}

//+------------------------------------------------------------------+
int CountOurPositions()
{
   int c = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0)
         continue;
      if(PositionGetInteger(POSITION_MAGIC) == (long)InpMagic &&
         PositionGetString(POSITION_SYMBOL) == _Symbol)
         c++;
   }
   return c;
}

int CountOurPending()
{
   int c = 0;
   for(int i = OrdersTotal() - 1; i >= 0; i--)
   {
      ulong ticket = OrderGetTicket(i);
      if(ticket == 0)
         continue;
      if(OrderGetInteger(ORDER_MAGIC) == (long)InpMagic &&
         OrderGetString(ORDER_SYMBOL) == _Symbol)
         c++;
   }
   return c;
}

void CancelOurPendings(const string reason)
{
   for(int i = OrdersTotal() - 1; i >= 0; i--)
   {
      ulong ticket = OrderGetTicket(i);
      if(ticket == 0)
         continue;
      if(OrderGetInteger(ORDER_MAGIC) != (long)InpMagic ||
         OrderGetString(ORDER_SYMBOL) != _Symbol)
         continue;
      if(!g_trade.OrderDelete(ticket))
         Print("[HIS] cancel pending fail ", ticket, " ", reason, " ", g_trade.ResultRetcode());
   }
   g_pendingDir = 0;
   g_pendingBarsLeft = 0;
}

void RollDayCounters()
{
   MqlDateTime dt;
   TimeToStruct(TimeCurrent(), dt);
   if(dt.day != g_lastTradeDay)
   {
      g_lastTradeDay = dt.day;
      g_tradesToday = 0;
      g_dayStartEquity = AccountInfoDouble(ACCOUNT_EQUITY);
   }
}

bool DailyLossHit()
{
   if(g_dayStartEquity <= 0.0)
      return false;
   double eq = AccountInfoDouble(ACCOUNT_EQUITY);
   double dd = (g_dayStartEquity - eq) / g_dayStartEquity * 100.0;
   return (dd >= InpDailyLossPct);
}

bool InSession()
{
   datetime t = InpUseGmtSession ? TimeGMT() : TimeCurrent();
   MqlDateTime dt;
   TimeToStruct(t, dt);
   int h = dt.hour;
   if(InpSessionStartHour <= InpSessionEndHour)
      return (h >= InpSessionStartHour && h < InpSessionEndHour);
   return (h >= InpSessionStartHour || h < InpSessionEndHour);
}

bool WeekendOrFridayLate()
{
   MqlDateTime dt;
   TimeToStruct(TimeCurrent(), dt);
   if(dt.day_of_week == 0 || dt.day_of_week == 6)
      return true;
   if(dt.day_of_week == 5 && dt.hour >= 20)
      return true;
   return false;
}

//+------------------------------------------------------------------+
int ComputeH4Bias(const MqlRates &h4[], const int n, double &obHigh, double &obLow, double &liqHigh, double &liqLow)
{
   obHigh = 0.0;
   obLow = 0.0;
   liqHigh = 0.0;
   liqLow = 0.0;

   // Collect recent swing indices (series: smaller index = newer)
   int sh[8];
   int sl[8];
   int nSh = 0, nSl = 0;
   int lim = MathMin(n - InpSwingStrength - 1, InpH4Lookback - 1);
   for(int i = InpSwingStrength; i <= lim; i++)
   {
      if(nSh < 8 && HIS_IsSwingHigh(h4, i, InpSwingStrength))
         sh[nSh++] = i;
      if(nSl < 8 && HIS_IsSwingLow(h4, i, InpSwingStrength))
         sl[nSl++] = i;
      if(nSh >= 8 && nSl >= 8)
         break;
   }
   if(nSh > 0)
      liqHigh = h4[sh[0]].high;
   if(nSl > 0)
      liqLow = h4[sl[0]].low;

   // Walk closed bars from older→newer; most recent BOS wins.
   int bias = 0;
   for(int i = lim; i >= 0; i--)
   {
      for(int s = 0; s < nSh; s++)
      {
         if(sh[s] <= i)
            continue; // swing must be older (larger index) than break bar
         if(h4[i].close > h4[sh[s]].high)
         {
            bias = 1;
            break;
         }
      }
      for(int s = 0; s < nSl; s++)
      {
         if(sl[s] <= i)
            continue;
         if(h4[i].close < h4[sl[s]].low)
         {
            bias = -1;
            break;
         }
      }
   }

   // If no historical BOS in window, fall back to HH/HL vs LH/LL structure
   if(bias == 0 && nSh >= 2 && nSl >= 2)
   {
      bool hh = (h4[sh[0]].high > h4[sh[1]].high);
      bool hl = (h4[sl[0]].low > h4[sl[1]].low);
      bool lh = (h4[sh[0]].high < h4[sh[1]].high);
      bool ll = (h4[sl[0]].low < h4[sl[1]].low);
      if(hh && hl)
         bias = 1;
      else if(lh && ll)
         bias = -1;
   }

   if(bias != 0)
   {
      for(int i = 1; i < MathMin(n, 30); i++)
      {
         if(bias > 0 && h4[i].close < h4[i].open)
         {
            obHigh = h4[i].high;
            obLow = h4[i].low;
            break;
         }
         if(bias < 0 && h4[i].close > h4[i].open)
         {
            obHigh = h4[i].high;
            obLow = h4[i].low;
            break;
         }
      }
   }
   return bias;
}

bool FindAlignedH4Fvg(const MqlRates &h4[], const int n, const int bias,
                      double &zTop, double &zBot)
{
   zTop = 0.0;
   zBot = 0.0;
   int maxAge = MathMin(n - 3, InpFvgMaxAgeH4);
   for(int i = 1; i <= maxAge; i++)
   {
      // rates series: 0 newest closed
      if(i + 2 >= n)
         break;
      if(bias > 0)
      {
         // bullish FVG: low[i] > high[i+2]
         if(h4[i].low > h4[i + 2].high)
         {
            double top = h4[i].low;
            double bot = h4[i + 2].high;
            bool mitigated = false;
            for(int j = 0; j < i; j++)
            {
               if(h4[j].close <= bot)
               {
                  mitigated = true;
                  break;
               }
            }
            if(!mitigated)
            {
               zTop = top;
               zBot = bot;
               return true;
            }
         }
      }
      else if(bias < 0)
      {
         if(h4[i].high < h4[i + 2].low)
         {
            double top = h4[i + 2].low;
            double bot = h4[i].high;
            bool mitigated = false;
            for(int j = 0; j < i; j++)
            {
               if(h4[j].close >= top)
               {
                  mitigated = true;
                  break;
               }
            }
            if(!mitigated)
            {
               zTop = top;
               zBot = bot;
               return true;
            }
         }
      }
   }
   return false;
}

bool NearLevel(const double low, const double high, const double atr,
               const double zTop, const double zBot,
               const double obHigh, const double obLow,
               const double liqHigh, const double liqLow,
               const int bias)
{
   double tol = InpLevelTouchATR * atr;
   // FVG touch
   if(zTop > zBot && low <= zTop + tol && high >= zBot - tol)
      return true;
   // OB touch
   if(obHigh > obLow && low <= obHigh + tol && high >= obLow - tol)
      return true;
   // Liquidity pool (swing)
   if(bias > 0 && liqLow > 0.0 && MathAbs(low - liqLow) <= tol)
      return true;
   if(bias < 0 && liqHigh > 0.0 && MathAbs(high - liqHigh) <= tol)
      return true;
   return false;
}

bool WaveConfirmLong(const MqlRates &r[], const int n)
{
   // Approximate L-H-HL → seeking HH: last swing low higher than prior swing low,
   // and last swing high higher than prior swing high (structure advancing).
   int sh1 = -1, sh2 = -1, sl1 = -1, sl2 = -1;
   for(int i = InpSwingStrength; i < MathMin(n - InpSwingStrength, InpWaveLookback); i++)
   {
      if(sh1 < 0 && HIS_IsSwingHigh(r, i, InpSwingStrength))
         sh1 = i;
      else if(sh1 >= 0 && sh2 < 0 && HIS_IsSwingHigh(r, i, InpSwingStrength) && i > sh1 + InpSwingStrength)
         sh2 = i;
      if(sl1 < 0 && HIS_IsSwingLow(r, i, InpSwingStrength))
         sl1 = i;
      else if(sl1 >= 0 && sl2 < 0 && HIS_IsSwingLow(r, i, InpSwingStrength) && i > sl1 + InpSwingStrength)
         sl2 = i;
      if(sh1 >= 0 && sh2 >= 0 && sl1 >= 0 && sl2 >= 0)
         break;
   }
   if(sh1 < 0 || sl1 < 0 || sl2 < 0)
      return false;
   // HL: newer swing low (smaller index) > older swing low
   bool hl = (r[sl1].low > r[sl2].low);
   bool risingHigh = (sh2 < 0) ? true : (r[sh1].high > r[sh2].high);
   return (hl && risingHigh);
}

bool WaveConfirmShort(const MqlRates &r[], const int n)
{
   int sh1 = -1, sh2 = -1, sl1 = -1, sl2 = -1;
   for(int i = InpSwingStrength; i < MathMin(n - InpSwingStrength, InpWaveLookback); i++)
   {
      if(sh1 < 0 && HIS_IsSwingHigh(r, i, InpSwingStrength))
         sh1 = i;
      else if(sh1 >= 0 && sh2 < 0 && HIS_IsSwingHigh(r, i, InpSwingStrength) && i > sh1 + InpSwingStrength)
         sh2 = i;
      if(sl1 < 0 && HIS_IsSwingLow(r, i, InpSwingStrength))
         sl1 = i;
      else if(sl1 >= 0 && sl2 < 0 && HIS_IsSwingLow(r, i, InpSwingStrength) && i > sl1 + InpSwingStrength)
         sl2 = i;
      if(sh1 >= 0 && sh2 >= 0 && sl1 >= 0 && sl2 >= 0)
         break;
   }
   if(sl1 < 0 || sh1 < 0 || sh2 < 0)
      return false;
   bool lh = (r[sh1].high < r[sh2].high);
   bool fallingLow = (sl2 < 0) ? true : (r[sl1].low < r[sl2].low);
   return (lh && fallingLow);
}

bool PvsraClimax(const MqlRates &r[], const int n)
{
   if(n < InpVolAvgBars + 2)
      return false;
   double sum = 0.0;
   for(int i = 1; i <= InpVolAvgBars; i++)
      sum += (double)r[i].tick_volume;
   double avg = sum / InpVolAvgBars;
   if(avg <= 0.0)
      return false;
   return ((double)r[0].tick_volume >= avg * InpVolClimaxMult);
}

bool MacdSlopeOk(const int dir)
{
   double main[], sig[];
   ArraySetAsSeries(main, true);
   ArraySetAsSeries(sig, true);
   if(CopyBuffer(g_hMACD, 0, 1, 3, main) < 3)
      return false;
   if(CopyBuffer(g_hMACD, 1, 1, 3, sig) < 3)
      return false;
   if(dir > 0)
      return (main[0] > main[1] && main[0] >= sig[0]);
   return (main[0] < main[1] && main[0] <= sig[0]);
}

bool AtrRegimeOk(const double &atr[], const int n)
{
   if(!InpUseAtrRegime)
      return true;
   if(n < InpAtrMaPeriod + 1)
      return false;
   double sum = 0.0;
   for(int i = 0; i < InpAtrMaPeriod; i++)
      sum += atr[i];
   double ma = sum / InpAtrMaPeriod;
   if(ma <= 0.0)
      return false;
   double ratio = atr[0] / ma;
   return (ratio >= InpMinAtrRatio && ratio <= InpMaxAtrRatio);
}

//+------------------------------------------------------------------+
bool ValidateStops(const bool isBuy, const double entry, const double sl, const double tp)
{
   long stopsLevel = 0, freezeLevel = 0;
   SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL, stopsLevel);
   SymbolInfoInteger(_Symbol, SYMBOL_TRADE_FREEZE_LEVEL, freezeLevel);
   double minDist = (double)MathMax(stopsLevel, freezeLevel) * _Point;
   if(minDist <= 0.0)
      return true;
   if(isBuy)
      return ((entry - sl) >= minDist && (tp - entry) >= minDist);
   return ((sl - entry) >= minDist && (entry - tp) >= minDist);
}

void ManageBreakEven()
{
   if(!InpUseBreakEven)
      return;
   double pip = HIS_PipSize();
   double trigger = InpBeTriggerPips * pip;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0)
         continue;
      if(PositionGetInteger(POSITION_MAGIC) != (long)InpMagic ||
         PositionGetString(POSITION_SYMBOL) != _Symbol)
         continue;
      double open = PositionGetDouble(POSITION_PRICE_OPEN);
      double sl = PositionGetDouble(POSITION_SL);
      double tp = PositionGetDouble(POSITION_TP);
      long typ = PositionGetInteger(POSITION_TYPE);
      double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
      double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
      if(typ == POSITION_TYPE_BUY)
      {
         if(bid - open >= trigger && (sl < open || sl == 0.0))
            g_trade.PositionModify(ticket, open, tp);
      }
      else if(typ == POSITION_TYPE_SELL)
      {
         if(open - ask >= trigger && (sl > open || sl == 0.0))
            g_trade.PositionModify(ticket, open, tp);
      }
   }
}

void ManageTimeStop()
{
   datetime now = TimeCurrent();
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0)
         continue;
      if(PositionGetInteger(POSITION_MAGIC) != (long)InpMagic ||
         PositionGetString(POSITION_SYMBOL) != _Symbol)
         continue;
      datetime openTime = (datetime)PositionGetInteger(POSITION_TIME);
      if(now - openTime >= InpMaxHoldHours * 3600)
         g_trade.PositionClose(ticket);
   }
}

//+------------------------------------------------------------------+
bool PlacePending(const int dir, const MqlRates &sig, const double sl, const double tp)
{
   double pip = HIS_PipSize();
   double offset = InpPendingOffsetPips * pip;
   double entry = (dir > 0) ? (sig.high + offset) : (sig.low - offset);
   entry = NormalizeDouble(entry, _Digits);
   double slN = NormalizeDouble(sl, _Digits);
   double tpN = NormalizeDouble(tp, _Digits);
   double dist = MathAbs(entry - slN);
   if(dist <= 0.0)
      return false;
   double lots = HIS_LotsForRisk(InpRiskPct, dist, InpMaxLot);
   if(lots <= 0.0)
      return false;
   if(!ValidateStops(dir > 0, entry, slN, tpN))
      return false;

   CancelOurPendings("replace");
   bool ok = false;
   if(dir > 0)
      ok = g_trade.BuyStop(lots, entry, _Symbol, slN, tpN, ORDER_TIME_GTC, 0, InpComment);
   else
      ok = g_trade.SellStop(lots, entry, _Symbol, slN, tpN, ORDER_TIME_GTC, 0, InpComment);

   if(ok)
   {
      g_pendingDir = dir;
      g_pendingBarsLeft = InpPendingTtlBars;
      g_pendingTime = TimeCurrent();
      g_tradesToday++;
      g_cnt_pending_ok++;
      Print("[HIS] pending ", (dir > 0 ? "BUYSTOP" : "SELLSTOP"),
            " @", entry, " SL=", slN, " TP=", tpN, " lot=", lots);
   }
   else
   {
      g_cnt_pending_fail++;
      Print("[HIS] pending fail ret=", g_trade.ResultRetcode());
   }
   return ok;
}

void AgePendingOnNewBar()
{
   if(CountOurPending() <= 0)
   {
      g_pendingDir = 0;
      g_pendingBarsLeft = 0;
      return;
   }
   if(g_pendingBarsLeft > 0)
   {
      g_pendingBarsLeft--;
      if(g_pendingBarsLeft <= 0)
         CancelOurPendings("ttl");
   }
}

//+------------------------------------------------------------------+
void EvaluateSignal()
{
   MqlRates m15[], h4[];
   double dHigh[], dMid[], dLow[], atr[];
   g_cnt_eval++;

   if(!HIS_CopyClosedRates(PERIOD_M15, InpM15Lookback, m15))
      return;
   if(!HIS_CopyClosedRates(PERIOD_H4, InpH4Lookback, h4))
      return;
   if(!HIS_CopyClosedBuffer(g_hDragonHigh, InpM15Lookback, dHigh))
      return;
   if(!HIS_CopyClosedBuffer(g_hDragonMid, InpM15Lookback, dMid))
      return;
   if(!HIS_CopyClosedBuffer(g_hDragonLow, InpM15Lookback, dLow))
      return;
   if(!HIS_CopyClosedBuffer(g_hATR, InpM15Lookback, atr))
      return;

   int n15 = ArraySize(m15);
   int n4 = ArraySize(h4);
   if(n15 < 40 || n4 < 20)
      return;
   if(!AtrRegimeOk(atr, n15))
      return;
   g_cnt_atr++;

   double obH, obL, liqH, liqL;
   int bias = ComputeH4Bias(h4, n4, obH, obL, liqH, liqL);
   if(bias == 0)
      return;
   g_cnt_bias++;

   double fvgTop, fvgBot;
   bool hasFvg = FindAlignedH4Fvg(h4, n4, bias, fvgTop, fvgBot);
   // Allow OB/liq if FVG missing
   if(!hasFvg && obH <= obL && liqH <= 0.0 && liqL <= 0.0)
      return;
   g_cnt_level_obj++;

   if(!NearLevel(m15[0].low, m15[0].high, atr[0],
                 hasFvg ? fvgTop : 0.0, hasFvg ? fvgBot : 0.0,
                 obH, obL, liqH, liqL, bias))
      return;
   g_cnt_near++;

   if(InpRequireWave)
   {
      if(bias > 0 && !WaveConfirmLong(m15, n15))
         return;
      if(bias < 0 && !WaveConfirmShort(m15, n15))
         return;
   }
   g_cnt_wave++;

   // Dragon trigger: outer-band break OR mid reclaim in bias direction
   bool dragonTrigger = false;
   if(bias > 0)
   {
      bool outerBreak = (m15[0].close > dHigh[0]);
      bool midReclaim = (m15[0].close > dMid[0] && m15[1].close <= dMid[1]);
      dragonTrigger = (outerBreak || midReclaim);
   }
   else
   {
      bool outerBreak = (m15[0].close < dLow[0]);
      bool midReclaim = (m15[0].close < dMid[0] && m15[1].close >= dMid[1]);
      dragonTrigger = (outerBreak || midReclaim);
   }
   if(!dragonTrigger)
      return;
   g_cnt_dragon++;

   if(InpRequirePvsraClimax && !PvsraClimax(m15, n15))
      return;
   g_cnt_pvsra++;
   if(InpRequireMacdSlope && !MacdSlopeOk(bias))
      return;

   // SL / TP — SIGATR: signal extreme ± InpSlAtrMult×ATR (levels = entry only)
   double pip = HIS_PipSize();
   double sl = 0.0;
   if(!InpUseLevelSl)
   {
      if(bias > 0)
         sl = m15[0].low - InpSlAtrMult * atr[0];
      else
         sl = m15[0].high + InpSlAtrMult * atr[0];
   }
   else if(bias > 0)
   {
      sl = m15[0].low;
      if(hasFvg)
         sl = MathMin(sl, fvgBot);
      if(obL > 0.0)
         sl = MathMin(sl, obL);
      if(liqL > 0.0)
         sl = MathMin(sl, liqL);
      sl -= InpSlAtrBuffer * atr[0];
      if(InpUseDragonSlFloor)
      {
         double dragonSl = dLow[0] - InpDragonSlBufferPips * pip;
         sl = MathMin(sl, dragonSl);
      }
   }
   else
   {
      sl = m15[0].high;
      if(hasFvg)
         sl = MathMax(sl, fvgTop);
      if(obH > 0.0)
         sl = MathMax(sl, obH);
      if(liqH > 0.0)
         sl = MathMax(sl, liqH);
      sl += InpSlAtrBuffer * atr[0];
      if(InpUseDragonSlFloor)
      {
         double dragonSl = dHigh[0] + InpDragonSlBufferPips * pip;
         sl = MathMax(sl, dragonSl);
      }
   }

   double entryApprox = (bias > 0) ? (m15[0].high + InpPendingOffsetPips * pip)
                                   : (m15[0].low - InpPendingOffsetPips * pip);
   double risk = MathAbs(entryApprox - sl);
   if(risk <= 0.0)
      return;
   if(risk > InpMaxSlAtrMult * atr[0])
   {
      g_cnt_sl_fail++;
      return;
   }
   g_cnt_sl_ok++;

   double tp = (bias > 0) ? (entryApprox + risk * InpTargetRR)
                          : (entryApprox - risk * InpTargetRR);

   PlacePending(bias, m15[0], sl, tp);
}

//+------------------------------------------------------------------+
void OnTick()
{
   if(!InpEnabled || InpKillSwitch)
      return;

   RollDayCounters();
   ManageBreakEven();

   datetime barTime = iTime(_Symbol, PERIOD_M15, 0);
   if(barTime == 0 || barTime == g_lastBarTime)
      return;
   g_lastBarTime = barTime;

   // new M15 bar
   AgePendingOnNewBar();
   ManageTimeStop();

   if(WeekendOrFridayLate())
   {
      CancelOurPendings("weekend");
      return;
   }
   if(DailyLossHit())
   {
      CancelOurPendings("daily_loss");
      return;
   }
   if(!InSession())
      return;
   if(HIS_SpreadPips() > InpMaxSpreadPips)
      return;
   if(CountOurPositions() >= InpMaxPositions)
      return;
   if(CountOurPending() > 0)
      return;
   if(g_tradesToday >= InpMaxTradesPerDay)
      return;

   EvaluateSignal();
}
//+------------------------------------------------------------------+
