//+------------------------------------------------------------------+
//| EA_Spark.mq5                                                      |
//| Session Breakout Scalp v1.3 — Validated GBPUSD NY Wed/Thu        |
//| Edge: Asian range -> NY breakout, 1.5R TP, BE at 1R              |
//| Validated: PF 1.73, 130t/7yr, DD 4%, WFA 3/5 OOS, MC-P95 14%   |
//| Regime-dependent. Weak on Mon/Tue. Skip Friday.                   |
//+------------------------------------------------------------------+
#property copyright "AlphaFactory Research"
#property version   "1.30"
#property description "Session Breakout Scalp v1.3 — GBPUSD M15 NY (validated)"

#include <Trade\Trade.mqh>
#include <Trade\PositionInfo.mqh>
#include <ExecQualityLog.mqh>
#include <HolidayCalendar.mqh>
#include <PartialClose.mqh>
#include "Include/SPK_Datalog.mqh"

//=== INPUTS ===

//--- Session Timing (server hours)
input int    InpAsianStart    = 0;       // Asian range start hour
input int    InpAsianEnd      = 8;       // Asian range end hour (locks)
input int    InpLdnStart      = 9;       // London session window start
input int    InpLdnEnd        = 13;      // London session window end
input bool   InpNYEnabled     = true;    // Enable NY continuation window
input int    InpNYStart       = 15;      // NY overlap window start
input int    InpNYEnd         = 18;      // NY overlap window end
input int    InpFlatHour      = 21;      // Close all by this hour

//--- Day Filter
input bool   InpSkipMon       = true;    // Skip Monday
input bool   InpSkipTue       = false;   // Skip Tuesday
input bool   InpSkipWed       = false;   // Skip Wednesday
input bool   InpSkipThu       = true;    // Skip Thursday
input bool   InpSkipFri       = true;    // Skip Friday (rollover/low vol)

//--- Signal
input double InpBrkBufferATR  = 0.15;    // Breakout buffer (ATR multiple)
input double InpBodyRatio     = 0.35;    // Min body/range for entry bar
input int    InpEMAPeriod     = 50;      // D1 EMA period for trend
input bool   InpUseTrendFilter= true;    // Enable D1 trend filter
input int    InpATRPeriod     = 14;      // ATR period (bars)
input double InpRangeMinATR   = 0.8;     // Min Asian range (xATR)
input double InpRangeMaxATR   = 8.0;     // Max Asian range (xATR)

//--- Risk Management
input double InpRiskPct       = 1.0;     // Risk per trade (% equity)
input double InpDailyLossPct  = 3.0;     // Max daily loss (% equity)
input int    InpMaxConsecLoss = 3;       // Consecutive losses -> lock
input int    InpMaxTradesDay  = 3;       // Max trades per day

//--- Execution
input double InpTPRatio       = 2.00;    // TP as R:R multiplier
input double InpSLBufferATR   = 0.20;    // SL buffer beyond range (xATR)
input bool   InpBEEnabled     = true;    // Enable breakeven
input double InpBERatio       = 1.0;     // Move to BE at this R profit
input int    InpMaxHoldBars   = 24;      // Max hold (bars, 24x15m=6h)
input int    InpMaxSpread     = 50;      // Max spread (points, ~5 pips 5-digit)
input int    InpDeviation     = 20;      // Max slippage (points)
input long   InpMagic         = 20260321;// Magic number

//--- Logging
input bool   InpEnableLog     = true;    // Enable print logging
input bool   InpChartComment  = true;    // Show chart comment
input bool   InpKillSwitch    = false;   // Kill Switch - disable new trades

input group "=== Partial Close ==="
input bool   InpPartialClose  = false;   // Enable partial close at N×R
input double InpPCL_TriggerR  = 1.0;     // Partial close trigger (R multiple)
input double InpPCL_ClosePct  = 0.50;    // Fraction to close (0.50 = 50%)

//=== GLOBALS ===
CTrade         g_trade;
CPositionInfo  g_pos;

int    g_hATR      = INVALID_HANDLE;
int    g_hEMA_D1   = INVALID_HANDLE;
double g_point     = 0;
int    g_digits    = 0;
string g_tradeCsvFile = "";
bool   g_tradeCsvHeaderWritten = false;

//--- Asian range

//--- Asian range
double g_asianHi   = 0;
double g_asianLo   = 99999.0;
bool   g_rangeLocked  = false;
bool   g_rangeValid   = false;

//--- Daily state
int    g_lastDayHash    = -1;
int    g_tradesDay      = 0;
int    g_consecLosses   = 0;
double g_dayStartEquity = 0;
bool   g_dayLocked      = false;

//--- Position state
int    g_holdBars       = 0;
double g_posOpenPrice   = 0;
bool   g_beMoved        = false;

//--- Bar tracking
datetime g_lastBarTime  = 0;

//--- GlobalVariable prefix for crash recovery
string g_gvPrefix = "";

//+------------------------------------------------------------------+
//| Save Asian range to GlobalVariables                               |
//+------------------------------------------------------------------+
void SPK_SaveRangeGV()
{
   if(g_gvPrefix == "") return;
   GlobalVariableSet(g_gvPrefix + "Hi",   g_asianHi);
   GlobalVariableSet(g_gvPrefix + "Lo",   g_asianLo);
   GlobalVariableSet(g_gvPrefix + "Lock", g_rangeLocked ? 1.0 : 0.0);
   GlobalVariableSet(g_gvPrefix + "Val",  g_rangeValid  ? 1.0 : 0.0);
   GlobalVariableSet(g_gvPrefix + "Day",  (double)g_lastDayHash);
}

//+------------------------------------------------------------------+
//| Restore Asian range from GlobalVariables (same-day only)          |
//+------------------------------------------------------------------+
bool SPK_RestoreRangeGV()
{
   if(g_gvPrefix == "") return false;
   if(!GlobalVariableCheck(g_gvPrefix + "Day")) return false;

   int savedDay = (int)GlobalVariableGet(g_gvPrefix + "Day");
   MqlDateTime dt;
   TimeCurrent(dt);
   int today = dt.year * 400 + dt.day_of_year;

   if(savedDay != today) return false;   // stale — different day

   g_asianHi    = GlobalVariableGet(g_gvPrefix + "Hi");
   g_asianLo    = GlobalVariableGet(g_gvPrefix + "Lo");
   g_rangeLocked = (GlobalVariableGet(g_gvPrefix + "Lock") > 0.5);
   g_rangeValid  = (GlobalVariableGet(g_gvPrefix + "Val")  > 0.5);

   PrintFormat("[SPK] Restored Asian range from GV: Hi=%.5f Lo=%.5f Locked=%s Valid=%s",
               g_asianHi, g_asianLo,
               (g_rangeLocked ? "Y" : "N"), (g_rangeValid ? "Y" : "N"));
   return true;
}

//+------------------------------------------------------------------+
//| Clean up GlobalVariables on deliberate removal                    |
//+------------------------------------------------------------------+
void SPK_CleanGV()
{
   if(g_gvPrefix == "") return;
   GlobalVariableDel(g_gvPrefix + "Hi");
   GlobalVariableDel(g_gvPrefix + "Lo");
   GlobalVariableDel(g_gvPrefix + "Lock");
   GlobalVariableDel(g_gvPrefix + "Val");
   GlobalVariableDel(g_gvPrefix + "Day");
}

//+------------------------------------------------------------------+
//| Expert initialization                                             |
//+------------------------------------------------------------------+
int OnInit()
{
   //--- Validate symbol properties
   g_point  = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   g_digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);

   if(g_point <= 0)
   {
      Print("[SPK] FATAL: Symbol point <= 0");
      return INIT_FAILED;
   }

   //--- Timeframe check
   if(Period() != PERIOD_M15)
      PrintFormat("[SPK] NOTE: Designed for M15, running on %s",
                  EnumToString(Period()));

   //--- Initialize CTrade
   g_trade.SetExpertMagicNumber(InpMagic);
   g_trade.SetDeviationInPoints(InpDeviation);

   //--- Detect fill mode
   long fillFlags = SymbolInfoInteger(_Symbol, SYMBOL_FILLING_MODE);
   if((fillFlags & SYMBOL_FILLING_FOK) != 0)
      g_trade.SetTypeFilling(ORDER_FILLING_FOK);
   else if((fillFlags & SYMBOL_FILLING_IOC) != 0)
      g_trade.SetTypeFilling(ORDER_FILLING_IOC);
   else
      g_trade.SetTypeFilling(ORDER_FILLING_RETURN);

   //--- Create ATR indicator
   g_hATR = iATR(_Symbol, PERIOD_CURRENT, InpATRPeriod);
   if(g_hATR == INVALID_HANDLE)
   {
      Print("[SPK] FATAL: Cannot create ATR handle");
      return INIT_FAILED;
   }

   //--- Create D1 EMA indicator (optional)
   if(InpUseTrendFilter)
   {
      g_hEMA_D1 = iMA(_Symbol, PERIOD_D1, InpEMAPeriod, 0, MODE_EMA, PRICE_CLOSE);
      if(g_hEMA_D1 == INVALID_HANDLE)
         PrintFormat("[SPK] WARNING: Cannot create D1 EMA, trend filter disabled");
   }

   //--- Init GlobalVariable prefix for crash recovery
   g_gvPrefix = "SPK_" + _Symbol + "_" + IntegerToString((int)InpMagic) + "_";

   //--- Init daily state
   g_dayStartEquity = AccountInfoDouble(ACCOUNT_EQUITY);
   g_lastBarTime    = 0;
   g_lastDayHash    = -1;

   //--- Try to restore Asian range from GlobalVariables (crash recovery)
   if(SPK_RestoreRangeGV())
      PrintFormat("[SPK] Crash recovery: Asian range restored for today");

   SPK_InitTradeCsv();
   SPK_OpenLogs(InpEnableLog, InpMagic);
   double spkPipSize = (g_digits == 3 || g_digits == 5) ? g_point * 10 : g_point;
   EQL_Init("EA_Spark", InpMagic, "SPK", spkPipSize, true);

   PrintFormat("[SPK] Init OK | %s | Magic=%I64d | BrkBuf=%.2fATR | TP=%.2fR | Spread<=%d | Kill=%s",
               _Symbol, InpMagic, InpBrkBufferATR, InpTPRatio, InpMaxSpread,
               (InpKillSwitch ? "ON" : "OFF"));

   return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
//| Expert deinitialization                                           |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   //--- Clean GV only on deliberate removal (preserve on crash for recovery)
   if(reason == REASON_REMOVE || reason == REASON_RECOMPILE)
      SPK_CleanGV();

   SPK_CloseTradeCsv();
   SPK_CloseLogs();
   if(g_hATR != INVALID_HANDLE)    { IndicatorRelease(g_hATR);    g_hATR = INVALID_HANDLE;    }
   if(g_hEMA_D1 != INVALID_HANDLE) { IndicatorRelease(g_hEMA_D1); g_hEMA_D1 = INVALID_HANDLE; }
   Comment("");
}

//+------------------------------------------------------------------+
//| Main tick handler                                                 |
//+------------------------------------------------------------------+
void OnTick()
{
   //--- New bar check
   datetime barTime = iTime(_Symbol, PERIOD_CURRENT, 0);
   if(barTime <= 0 || barTime == g_lastBarTime)
      return;
   g_lastBarTime = barTime;

   //--- Decompose bar time
   MqlDateTime dt;
   TimeToStruct(barTime, dt);
   int hour = dt.hour;
   int dow  = dt.day_of_week;

   //--- New day check
   int dayHash = dt.year * 400 + dt.day_of_year;
   if(dayHash != g_lastDayHash)
   {
      g_lastDayHash = dayHash;
      ResetDay();
   }

   //--- Day filter (still manage positions on filtered days)
   bool skipDay = (InpSkipMon && dow==1) || (InpSkipTue && dow==2) ||
                  (InpSkipWed && dow==3) || (InpSkipThu && dow==4) ||
                  (InpSkipFri && dow==5);

   //--- Get ATR (shift=1, completed bar only)
   double atr = GetATR();
   if(atr <= 0) return;

   //--- Check existing position
   bool hasPos = HasOurPosition();

   //--- Manage existing position (even on skip days)
   if(hasPos)
   {
      g_holdBars++;
      ManagePosition(hour);
      UpdateChartComment(hour, atr, hasPos);
      return;
   }

   //--- Skip day: don't open new trades
   if(skipDay)
   {
      UpdateChartComment(hour, atr, false);
      return;
   }

   //--- Asian range tracking (completed bar data)
   if(hour >= InpAsianStart && hour < InpAsianEnd)
   {
      double hi1 = iHigh(_Symbol, PERIOD_CURRENT, 1);
      double lo1 = iLow(_Symbol, PERIOD_CURRENT, 1);
      if(hi1 > g_asianHi)                     g_asianHi = hi1;
      if(lo1 < g_asianLo && lo1 > 0)          g_asianLo = lo1;
   }

   //--- Lock range at Asian end
   if(hour >= InpAsianEnd && !g_rangeLocked)
      LockRange(atr);

   //--- Kill switch: block new entries, allow position management
   if(InpKillSwitch)
   {
      UpdateChartComment(hour, atr, false);
      return;
   }

   //--- Holiday check (block entries, allow position mgmt above)
   if(IsMarketHoliday())
   {
      UpdateChartComment(hour, atr, false);
      return;
   }

   //--- Check entry conditions
   if(!g_rangeLocked || !g_rangeValid || g_dayLocked)
   {
      UpdateChartComment(hour, atr, false);
      return;
   }

   //--- Check daily limits
   CheckDailyLimits();
   if(g_dayLocked)
   {
      UpdateChartComment(hour, atr, false);
      return;
   }

   //--- Entry window check
   bool inLdn = (hour >= InpLdnStart && hour < InpLdnEnd);
   bool inNY  = InpNYEnabled && (hour >= InpNYStart && hour < InpNYEnd);
   if(!inLdn && !inNY)
   {
      UpdateChartComment(hour, atr, false);
      return;
   }

   //--- Flat time: don't open new trades near EOD
   if(hour >= InpFlatHour)
   {
      UpdateChartComment(hour, atr, false);
      return;
   }

   //--- Try entry
   TryEntry(atr, inLdn ? "LDN" : "NY");
   UpdateChartComment(hour, atr, HasOurPosition());
}

//+------------------------------------------------------------------+
//| Reset daily state                                                 |
//+------------------------------------------------------------------+
void ResetDay()
{
   g_asianHi        = 0;
   g_asianLo        = 99999.0;
   g_rangeLocked    = false;
   g_rangeValid     = false;
   g_tradesDay      = 0;
   g_consecLosses   = 0;
   g_dayLocked      = false;
   g_dayStartEquity = AccountInfoDouble(ACCOUNT_EQUITY);
   g_holdBars       = 0;
   g_beMoved        = false;

   if(InpEnableLog)
      PrintFormat("[SPK] New day reset | Equity=%.2f", g_dayStartEquity);
}

//+------------------------------------------------------------------+
//| Lock Asian range and validate                                     |
//+------------------------------------------------------------------+
void LockRange(double atr)
{
   g_rangeLocked = true;

   if(g_asianHi <= 0 || g_asianLo >= 99999.0 || g_asianHi <= g_asianLo)
   {
      g_rangeValid = false;
      if(InpEnableLog)
         Print("[SPK] Range INVALID: no data or inverted");
      return;
   }

   double rangeSize = g_asianHi - g_asianLo;
   double ratio = (atr > 0) ? rangeSize / atr : 0;

   if(ratio >= InpRangeMinATR && ratio <= InpRangeMaxATR)
   {
      g_rangeValid = true;
      SPK_SaveRangeGV();
      if(InpEnableLog)
         PrintFormat("[SPK] Range LOCKED: Hi=%.5f Lo=%.5f | %.0f pts | %.2f xATR",
                     g_asianHi, g_asianLo, rangeSize / g_point, ratio);
   }
   else
   {
      g_rangeValid = false;
      SPK_SaveRangeGV();
      if(InpEnableLog)
         PrintFormat("[SPK] Range SKIPPED: %.2f xATR (need %.2f-%.2f)",
                     ratio, InpRangeMinATR, InpRangeMaxATR);
   }
}

//+------------------------------------------------------------------+
//| Try breakout entry (with signal logging + retry)                  |
//+------------------------------------------------------------------+
void TryEntry(double atr, string session)
{
   datetime barTime = iTime(_Symbol, PERIOD_CURRENT, 0);
   double rangePts = (g_asianHi > 0 && g_asianLo < 99999.0)
                     ? (g_asianHi - g_asianLo) / g_point : 0;
   int direction = 0;
   double bodyRatio = 0;
   int trendBias = 0;

   //--- Spread check
   int spread = (int)SymbolInfoInteger(_Symbol, SYMBOL_SPREAD);
   if(spread > InpMaxSpread)
   {
      if(InpEnableLog)
         PrintFormat("[SPK] SKIP spread=%d > max=%d", spread, InpMaxSpread);
      SPK_LogSignal(barTime, session, false, "spread",
                    0, g_asianHi, g_asianLo, rangePts, atr, spread, 0, 0);
      return;
   }

   //--- Get completed bar OHLC (shift=1)
   double open1  = iOpen(_Symbol, PERIOD_CURRENT, 1);
   double close1 = iClose(_Symbol, PERIOD_CURRENT, 1);
   double high1  = iHigh(_Symbol, PERIOD_CURRENT, 1);
   double low1   = iLow(_Symbol, PERIOD_CURRENT, 1);

   if(high1 <= low1)
   {
      SPK_LogSignal(barTime, session, false, "bad_ohlc",
                    0, g_asianHi, g_asianLo, rangePts, atr, spread, 0, 0);
      return;
   }
   double barRange = high1 - low1;
   double barBody  = MathAbs(close1 - open1);
   bodyRatio = barBody / barRange;

   //--- Body ratio filter
   if(bodyRatio < InpBodyRatio)
   {
      SPK_LogSignal(barTime, session, false, "body_ratio",
                    0, g_asianHi, g_asianLo, rangePts, atr, spread, bodyRatio, 0);
      return;
   }

   //--- Breakout detection
   double buffer = atr * InpBrkBufferATR;

   if(close1 > g_asianHi + buffer && close1 > open1)
      direction = 1;   // BUY breakout
   else if(close1 < g_asianLo - buffer && close1 < open1)
      direction = -1;  // SELL breakout

   if(direction == 0)
   {
      SPK_LogSignal(barTime, session, false, "no_breakout",
                    0, g_asianHi, g_asianLo, rangePts, atr, spread, bodyRatio, 0);
      return;
   }

   //--- Trend filter (D1 EMA, shift=1 = no lookahead)
   if(InpUseTrendFilter && g_hEMA_D1 != INVALID_HANDLE)
   {
      trendBias = GetTrendBias();
      if((direction == 1 && trendBias == -1) || (direction == -1 && trendBias == 1))
      {
         SPK_LogSignal(barTime, session, false, "trend_filter",
                       direction, g_asianHi, g_asianLo, rangePts, atr, spread, bodyRatio, trendBias);
         return;
      }
   }

   //--- Calculate SL and TP
   double slBuffer = atr * InpSLBufferATR;
   double entry = 0, sl = 0, tp = 0, slDist = 0;

   if(direction == 1) // BUY
   {
      entry  = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
      sl     = g_asianLo - slBuffer;
      slDist = entry - sl;
      tp     = entry + slDist * InpTPRatio;
   }
   else // SELL
   {
      entry  = SymbolInfoDouble(_Symbol, SYMBOL_BID);
      sl     = g_asianHi + slBuffer;
      slDist = sl - entry;
      tp     = entry - slDist * InpTPRatio;
   }

   if(slDist <= 0)
   {
      if(InpEnableLog) Print("[SPK] SKIP: slDist <= 0");
      SPK_LogSignal(barTime, session, false, "sl_dist",
                    direction, g_asianHi, g_asianLo, rangePts, atr, spread, bodyRatio, trendBias);
      return;
   }

   //--- Check broker stop level
   long stopLevel = SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL);
   if(stopLevel > 0)
   {
      double minDist = stopLevel * g_point;
      if(slDist < minDist || slDist * InpTPRatio < minDist)
      {
         if(InpEnableLog)
            PrintFormat("[SPK] SKIP: stop level violation (need %.0f pts, have SL=%.0f TP=%.0f)",
                        (double)stopLevel, slDist/g_point, slDist*InpTPRatio/g_point);
         SPK_LogSignal(barTime, session, false, "stop_level",
                       direction, g_asianHi, g_asianLo, rangePts, atr, spread, bodyRatio, trendBias);
         return;
      }
   }

   //--- Calculate lot size
   double lots = CalcLotSize(slDist);
   if(lots <= 0)
   {
      if(InpEnableLog) Print("[SPK] SKIP: lot size = 0");
      SPK_LogSignal(barTime, session, false, "lot_zero",
                    direction, g_asianHi, g_asianLo, rangePts, atr, spread, bodyRatio, trendBias);
      return;
   }

   //--- Normalize prices
   sl = NormalizeDouble(sl, g_digits);
   tp = NormalizeDouble(tp, g_digits);

   //--- Execute trade with retry (3 attempts, exponential backoff)
   string comment = StringFormat("SPK_%s", session);
   double intendedPx = (direction == 1) ? SymbolInfoDouble(_Symbol, SYMBOL_ASK)
                                        : SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double spkSpreadPips = SymbolInfoInteger(_Symbol, SYMBOL_SPREAD) * g_point
                        / ((g_digits == 3 || g_digits == 5) ? g_point * 10 : g_point);
   EQL_SetContext(intendedPx, spkSpreadPips, session);
   bool filled = false;
   uint retcode = 0;
   int maxRetries = 3;

   for(int attempt = 1; attempt <= maxRetries; attempt++)
   {
      bool ok = false;
      if(direction == 1)
         ok = g_trade.Buy(lots, _Symbol, 0, sl, tp, comment);
      else
         ok = g_trade.Sell(lots, _Symbol, 0, sl, tp, comment);

      retcode = g_trade.ResultRetcode();

      if(ok && (retcode == TRADE_RETCODE_DONE || retcode == TRADE_RETCODE_PLACED))
      {
         EQL_RecordFill(retcode);
         filled = true;
         break;
      }

      //--- Non-transient error: stop retrying
      if(retcode != TRADE_RETCODE_REQUOTE &&
         retcode != TRADE_RETCODE_PRICE_OFF &&
         retcode != TRADE_RETCODE_TIMEOUT &&
         retcode != TRADE_RETCODE_CONNECTION)
      {
         PrintFormat("[SPK] ORDER REJECTED attempt %d/%d — err=%d %s (non-transient)",
                     attempt, maxRetries, retcode, g_trade.ResultRetcodeDescription());
         break;
      }

      PrintFormat("[SPK] RETRY %d/%d — err=%d %s",
                  attempt, maxRetries, retcode, g_trade.ResultRetcodeDescription());
      EQL_RecordRetry(retcode);
      if(attempt < maxRetries)
         Sleep(200 * (int)MathPow(2, attempt - 1));  // 200ms, 400ms
   }

   if(filled)
   {
      g_tradesDay++;
      g_holdBars     = 0;
      g_beMoved      = false;
      g_posOpenPrice = g_trade.ResultPrice();

      PrintFormat("[SPK] ENTRY %s %s | lots=%.2f | price=%.5f | SL=%.5f | TP=%.5f | slDist=%.0f pts",
                  (direction==1 ? "BUY" : "SELL"), session,
                  lots, g_trade.ResultPrice(), sl, tp, slDist/g_point);
      SPK_LogSignal(barTime, session, true, "",
                    direction, g_asianHi, g_asianLo, rangePts, atr, spread, bodyRatio, trendBias);
   }
   else
   {
      PrintFormat("[SPK] ORDER FAILED FINAL — retcode=%d %s",
                  retcode, g_trade.ResultRetcodeDescription());
      SPK_LogSignal(barTime, session, false, "exec_fail",
                    direction, g_asianHi, g_asianLo, rangePts, atr, spread, bodyRatio, trendBias);
   }
}

//+------------------------------------------------------------------+
//| Close position with retry (3 attempts)                            |
//+------------------------------------------------------------------+
bool SPK_CloseWithRetry(ulong ticket, string reason)
{
   for(int attempt = 1; attempt <= 3; attempt++)
   {
      if(g_trade.PositionClose(ticket))
      {
         uint rc = g_trade.ResultRetcode();
         if(rc == TRADE_RETCODE_DONE || rc == TRADE_RETCODE_PLACED)
         {
            PrintFormat("[SPK] %s close #%I64u OK", reason, ticket);
            return true;
         }
      }
      PrintFormat("[SPK] CLOSE RETRY %d/3 #%I64u (%s) — err=%d %s",
                  attempt, ticket, reason,
                  g_trade.ResultRetcode(), g_trade.ResultRetcodeDescription());
      if(attempt < 3) Sleep(200);
   }
   PrintFormat("[SPK] CLOSE FAILED #%I64u (%s) after 3 attempts", ticket, reason);
   return false;
}

//+------------------------------------------------------------------+
//| Manage existing position (BE, time exit, flat time)               |
//+------------------------------------------------------------------+
void ManagePosition(int hour)
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      if(!g_pos.SelectByIndex(i)) continue;
      if(g_pos.Symbol() != _Symbol)  continue;
      if(g_pos.Magic() != InpMagic) continue;

      ulong ticket    = g_pos.Ticket();
      double openPx   = g_pos.PriceOpen();
      double currSL   = g_pos.StopLoss();
      double currTP   = g_pos.TakeProfit();
      bool   isBuy    = (g_pos.PositionType() == POSITION_TYPE_BUY);

      //--- 1) Flat time exit
      if(hour >= InpFlatHour)
      {
         SPK_CloseWithRetry(ticket, "FLAT");
         return;
      }

      //--- 2) Max hold time exit
      if(g_holdBars >= InpMaxHoldBars)
      {
         SPK_CloseWithRetry(ticket, "MAX_HOLD");
         return;
      }

      //--- 3) Partial close at N×R (if enabled, before BE)
      if(InpPartialClose && !g_beMoved && currSL > 0)
      {
         double curPx = isBuy ? SymbolInfoDouble(_Symbol, SYMBOL_BID)
                               : SymbolInfoDouble(_Symbol, SYMBOL_ASK);
         if(PCL_CheckPartialClose(g_trade, ticket, isBuy, openPx, currSL, currTP,
                                  curPx, g_pos.Volume(), _Symbol,
                                  InpPCL_TriggerR, InpPCL_ClosePct, "[SPK]"))
         {
            g_beMoved = true;  // PCL already moved SL to BE
         }
      }

      //--- 4) Breakeven (skip if partial close already did BE)
      if(InpBEEnabled && !g_beMoved && currSL > 0)
      {
         double slDist = MathAbs(openPx - currSL);
         double beTarget = slDist * InpBERatio;
         double curPrice = isBuy ? SymbolInfoDouble(_Symbol, SYMBOL_BID)
                                 : SymbolInfoDouble(_Symbol, SYMBOL_ASK);
         double profit = isBuy ? (curPrice - openPx) : (openPx - curPrice);

         if(profit >= beTarget && beTarget > 0)
         {
            double newSL = NormalizeDouble(
               isBuy ? openPx + g_point : openPx - g_point, g_digits);

            // Check stop level
            double dist = MathAbs(curPrice - newSL);
            long stopLvl = SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL);
            if(dist >= stopLvl * g_point)
            {
               if(g_trade.PositionModify(ticket, newSL, currTP))
               {
                  g_beMoved = true;
                  if(InpEnableLog)
                     PrintFormat("[SPK] BE #%I64u newSL=%.5f", ticket, newSL);
               }
            }
         }
      }

      break; // manage only our first position
   }
}

//+------------------------------------------------------------------+
//| Get ATR value at shift=1                                          |
//+------------------------------------------------------------------+
double GetATR()
{
   if(g_hATR == INVALID_HANDLE) return 0;
   double buf[];
   ArraySetAsSeries(buf, true);
   if(CopyBuffer(g_hATR, 0, 1, 1, buf) < 1) return 0;
   return buf[0];
}

//+------------------------------------------------------------------+
//| Get D1 trend bias: 1=bull, -1=bear, 0=flat                       |
//+------------------------------------------------------------------+
int GetTrendBias()
{
   if(g_hEMA_D1 == INVALID_HANDLE) return 0;

   double ema[];
   ArraySetAsSeries(ema, true);
   if(CopyBuffer(g_hEMA_D1, 0, 1, 1, ema) < 1) return 0;

   double d1c[];
   ArraySetAsSeries(d1c, true);
   if(CopyClose(_Symbol, PERIOD_D1, 1, 1, d1c) < 1) return 0;

   if(d1c[0] > ema[0]) return  1;  // Bull
   if(d1c[0] < ema[0]) return -1;  // Bear
   return 0;
}

//+------------------------------------------------------------------+
//| Calculate lot size from risk percentage                           |
//+------------------------------------------------------------------+
double CalcLotSize(double slDistance)
{
   double tickVal  = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
   double tickSize = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   if(tickVal <= 0 || tickSize <= 0 || slDistance <= 0)
      return 0;

   double equity    = AccountInfoDouble(ACCOUNT_EQUITY);
   double riskMoney = equity * InpRiskPct / 100.0;
   double lossPerLot = (slDistance / tickSize) * tickVal;
   if(lossPerLot <= 0) return 0;

   double lots = riskMoney / lossPerLot;

   //--- Volume constraints
   double minVol  = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double maxVol  = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   double stepVol = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   if(stepVol <= 0) stepVol = 0.01;

   lots = MathFloor(lots / stepVol) * stepVol;
   if(lots < minVol) lots = minVol;
   if(lots > maxVol) lots = maxVol;

   return NormalizeDouble(lots, 2);
}

//+------------------------------------------------------------------+
//| Check if we have an open position                                 |
//+------------------------------------------------------------------+
bool HasOurPosition()
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      if(!g_pos.SelectByIndex(i)) continue;
      if(g_pos.Symbol() == _Symbol && g_pos.Magic() == InpMagic)
         return true;
   }
   return false;
}

//+------------------------------------------------------------------+
//| Check daily limits                                                |
//+------------------------------------------------------------------+
void CheckDailyLimits()
{
   if(g_dayLocked) return;

   //--- Max trades per day
   if(g_tradesDay >= InpMaxTradesDay)
   {
      g_dayLocked = true;
      if(InpEnableLog) Print("[SPK] DAY LOCKED: max trades reached");
      return;
   }

   //--- Consecutive losses
   if(g_consecLosses >= InpMaxConsecLoss)
   {
      g_dayLocked = true;
      if(InpEnableLog) PrintFormat("[SPK] DAY LOCKED: %d consecutive losses", g_consecLosses);
      return;
   }

   //--- Daily P&L
   if(g_dayStartEquity > 0)
   {
      double equity = AccountInfoDouble(ACCOUNT_EQUITY);
      double pnlPct = (equity - g_dayStartEquity) / g_dayStartEquity * 100.0;
      if(pnlPct <= -InpDailyLossPct)
      {
         g_dayLocked = true;
         if(InpEnableLog) PrintFormat("[SPK] DAY LOCKED: daily loss %.2f%%", pnlPct);
      }
   }
}

//+------------------------------------------------------------------+
//| Track trade closes for consecutive loss counting                  |
//+------------------------------------------------------------------+
void OnTradeTransaction(const MqlTradeTransaction& trans,
                        const MqlTradeRequest& request,
                        const MqlTradeResult& result)
{
   if(trans.type != TRADE_TRANSACTION_DEAL_ADD) return;

   if(!HistoryDealSelect(trans.deal)) return;

   long magic = HistoryDealGetInteger(trans.deal, DEAL_MAGIC);
   if(magic != InpMagic) return;

   EQL_OnDeal(trans.deal);

   ENUM_DEAL_ENTRY dealEntry = (ENUM_DEAL_ENTRY)HistoryDealGetInteger(trans.deal, DEAL_ENTRY);

   if(dealEntry == DEAL_ENTRY_OUT || dealEntry == DEAL_ENTRY_INOUT)
   {
      double profit = HistoryDealGetDouble(trans.deal, DEAL_PROFIT)
                    + HistoryDealGetDouble(trans.deal, DEAL_COMMISSION)
                    + HistoryDealGetDouble(trans.deal, DEAL_SWAP);

      SPK_AppendTradeCsv(trans.deal);

      if(profit < 0)
         g_consecLosses++;
      else
         g_consecLosses = 0;

      if(InpEnableLog)
         PrintFormat("[SPK] CLOSE deal=%I64u profit=%.2f consecLoss=%d",
                     trans.deal, profit, g_consecLosses);
   }
}

void SPK_InitTradeCsv()
{
   g_tradeCsvFile = "PaperDeploy/EA_Spark/trades_" + IntegerToString((int)InpMagic) + ".csv";
   g_tradeCsvHeaderWritten = FileIsExist(g_tradeCsvFile, FILE_COMMON);
}

void SPK_AppendTradeCsv(ulong deal)
{
   if(!HistoryDealSelect(deal)) return;
   if(HistoryDealGetInteger(deal, DEAL_MAGIC) != InpMagic) return;
   if(HistoryDealGetString(deal, DEAL_SYMBOL) != _Symbol) return;

   ENUM_DEAL_ENTRY dealEntry = (ENUM_DEAL_ENTRY)HistoryDealGetInteger(deal, DEAL_ENTRY);
   if(dealEntry != DEAL_ENTRY_OUT && dealEntry != DEAL_ENTRY_INOUT) return;

   int handle = FileOpen(g_tradeCsvFile,
                         FILE_READ|FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_SHARE_READ|FILE_SHARE_WRITE|FILE_COMMON,
                         ',');
   if(handle == INVALID_HANDLE) return;

   if(!g_tradeCsvHeaderWritten)
   {
      FileWrite(handle, "timestamp", "symbol", "magic", "direction", "profit", "comment");
      g_tradeCsvHeaderWritten = true;
   }
   FileSeek(handle, 0, SEEK_END);

   long dealType = HistoryDealGetInteger(deal, DEAL_TYPE);
   string direction = (dealType == DEAL_TYPE_BUY || dealType == DEAL_TYPE_BUY_CANCELED) ? "buy" : "sell";
   double profit = HistoryDealGetDouble(deal, DEAL_PROFIT)
                 + HistoryDealGetDouble(deal, DEAL_COMMISSION)
                 + HistoryDealGetDouble(deal, DEAL_SWAP);
   string comment = HistoryDealGetString(deal, DEAL_COMMENT);
   datetime t = (datetime)HistoryDealGetInteger(deal, DEAL_TIME);

   FileWrite(handle,
             TimeToString(t, TIME_DATE|TIME_MINUTES|TIME_SECONDS),
             _Symbol,
             IntegerToString((int)InpMagic),
             direction,
             DoubleToString(profit, 2),
             comment);
   FileClose(handle);
}

void SPK_CloseTradeCsv()
{
   g_tradeCsvFile = "";
   g_tradeCsvHeaderWritten = false;
}

//+------------------------------------------------------------------+
//| Update chart comment                                              |
//+------------------------------------------------------------------+
void UpdateChartComment(int hour, double atr, bool inPos)
{
   if(!InpChartComment) return;

   string rangeStatus = "Building";
   if(g_rangeLocked)
      rangeStatus = g_rangeValid ? "VALID" : "SKIPPED";

   string dayStatus = g_dayLocked ? "LOCKED" : "Active";

   Comment(StringFormat(
      "=== EA_Spark v1.1 ===\n"
      "Symbol: %s | Hour: %d\n"
      "Asian: %.5f - %.5f [%s]\n"
      "ATR: %.5f | Spread: %d\n"
      "Trades: %d/%d | ConsLoss: %d | %s\n"
      "Position: %s | Hold: %d bars\n",
      _Symbol, hour,
      g_asianLo < 99999 ? g_asianLo : 0.0, g_asianHi, rangeStatus,
      atr, (int)SymbolInfoInteger(_Symbol, SYMBOL_SPREAD),
      g_tradesDay, InpMaxTradesDay, g_consecLosses, dayStatus,
      inPos ? "OPEN" : "FLAT", g_holdBars));
}
//+------------------------------------------------------------------+
