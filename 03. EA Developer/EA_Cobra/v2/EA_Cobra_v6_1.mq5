//+------------------------------------------------------------------+
//| EA_Cobra_v2.mq5 — Level-Based Kill Zone Scalper                  |
//| Symbol: XAUUSD  |  Period: M15  |  Style: Intraday Scalp         |
//|                                                                   |
//| EDGE HYPOTHESIS (v2):                                             |
//| Price interaction with structural levels (Asian Range H/L,        |
//| Previous Day H/L) in high-liquidity kill zones predicts           |
//| continuation (breakout) or rejection (bounce).                    |
//|                                                                   |
//| v1 FAILED because: Pure momentum in kill zone has NO edge.        |
//| Time × Momentum = ~50/50. Adding PRICE LEVEL creates the edge:   |
//| Time × Price_Level × Momentum = Statistical edge (like Phoenix). |
//|                                                                   |
//| KEY DIFFERENCES from Phoenix v6:                                  |
//| + Multiple level types (Asian + PrevDay, not just Asian)          |
//| + Bounce entries (not just breakout)                               |
//| + Kill zone focus (not full session windows)                       |
//| + SL anchored to level (structural) not just ATR                  |
//| + Modular architecture (easy to add new level types)              |
//|                                                                   |
//| DESIGN PRINCIPLES:                                                |
//| - Signals on bar[1] ONLY (no lookahead, no repaint)              |
//| - Hard SL on every trade (structural + ATR bounded)               |
//| - Session-aware R:R (London 3.0, NY 2.5, NYC 2.0)               |
//| - Break-even at 1.0R profit                                       |
//| - Friday flatten at 17:00                                         |
//| - Day risk multipliers (Mon 0.85, Wed 0.70)                      |
//| - Max 2 trades per kill zone, 6 per day                          |
//| - Daily DD kill at 4.0%                                           |
//|                                                                   |
//| Max | 2026-03-19 | v2.0                                         |
//+------------------------------------------------------------------+
#property copyright "Max — EA_Cobra v2"
#property link      ""
#property version   "2.00"
#property strict

//--- Include modules
#include "Include\CBR_Config.mqh"
#include "Include\CBR_Types.mqh"
#include "Include\CBR_SessionTime.mqh"
#include "Include\CBR_Indicators.mqh"
#include "Include\CBR_SignalEngine.mqh"
#include <ExecQualityLog.mqh>
#include <HolidayCalendar.mqh>
#include <PartialClose.mqh>
#include "Include\CBR_NewsFilter.mqh"
#include "Include\CBR_RiskExec.mqh"
#include "Include\CBR_Datalog.mqh"

//+------------------------------------------------------------------+
//| Input Parameters                                                  |
//+------------------------------------------------------------------+
input group "═══ General ═══"
input ulong    InpMagic         = 202604;    // Magic Number
input int      InpDeviation     = 30;        // Max Slippage (pts)
input bool     InpKillSwitch    = false;     // Kill Switch (disable all)

input group "═══ Kill Zone Windows (Server Time) ═══"
input int      InpKzLdnStart    = 99;        // v2.4: DISABLED (PF 1.01 = no edge)
input int      InpKzLdnEnd      = 99;        // v2.4: DISABLED
input int      InpKzNyStart     = 13;        // NY KZ Start Hour
input int      InpKzNyEnd       = 15;        // NY KZ End Hour
input int      InpKzNycStart    = 16;        // NY Close KZ Start Hour
input int      InpKzNycEnd      = 17;        // NY Close KZ End Hour

input group "═══ Asian Range (Level Building) ═══"
input int      InpAsianStartH   = 0;         // Asian Range Start Hour
input int      InpAsianEndH     = 7;         // Asian Range End Hour

input group "═══ Risk Management ═══"
input double   InpRiskPct       = 0.50;      // v2.3: was 0.75, reduced for DD control
input double   InpMaxLot        = 0.50;      // Max lot per trade
input int      InpMaxOpen       = 3;         // Max simultaneous positions
input int      InpMaxPerDay     = 6;         // Max trades per day
input int      InpMaxPerKZ      = 2;         // Max trades per kill zone
input double   InpDailyDD       = 4.0;       // Daily DD Limit (%)

input group "═══ Datalog ═══"
input bool     InpDatalog       = true;      // Enable CSV signal log
input bool     InpSkipThu       = false;     // v2.5: Skip Thursday (PF 1.08 NYC-only)

input group "═══ Partial Close ═══"
input bool     InpPartialClose  = false;     // Enable partial close at N×R
input double   InpPCL_TriggerR  = 1.0;       // Partial close trigger (R multiple)
input double   InpPCL_ClosePct  = 0.50;      // Fraction to close (0.50 = 50%)

input group "═══ News Filter ═══"
input bool     InpNewsFilter    = true;      // Enable News Filter (block during events)
input int      InpNewsBeforeMin = 5;         // Block N minutes BEFORE event
input int      InpNewsAfterMin  = 5;         // Block N minutes AFTER event

//+------------------------------------------------------------------+
//| Globals                                                           |
//+------------------------------------------------------------------+
datetime g_cbrLastBar = 0;

//+------------------------------------------------------------------+
//| Expert initialization                                             |
//+------------------------------------------------------------------+
int OnInit()
{
   // Validate symbol
   if(StringFind(_Symbol, "XAU") < 0 && StringFind(_Symbol, "GOLD") < 0)
      PrintFormat("[CBR] WARNING: Designed for XAUUSD, running on %s", _Symbol);

   // Validate timeframe
   if(_Period != PERIOD_M15)
      PrintFormat("[CBR] WARNING: Designed for M15, running on %s",
                  EnumToString(_Period));

   // Init indicators
   if(!CBR_InitIndicators(_Symbol))
   {
      Print("[CBR] FATAL: Indicator init failed");
      return INIT_FAILED;
   }

   // Init execution
   CBR_InitExec(InpMagic, InpDeviation, _Symbol);

   // Init levels
   CBR_InitLevels();

   // Init news filter
   if(InpNewsFilter)
      CBR_InitNews(_Symbol);

   // Init datalog
   if(InpDatalog)
      CBR_InitDatalog(_Symbol);
   CBR_InitTradeCsv(InpMagic);
   EQL_Init("EA_Cobra", InpMagic, "CBR", g_cbrPt, true);

   PrintFormat("[CBR] EA_Cobra v%s initialized | Symbol=%s | TF=%s | Magic=%d",
               CBR_VERSION, _Symbol, EnumToString(_Period), InpMagic);
   PrintFormat("[CBR] Kill Zones: LDN=%d:00-%d:00 | NY=%d:00-%d:00 | NYC=%d:00-%d:00",
               InpKzLdnStart, InpKzLdnEnd, InpKzNyStart, InpKzNyEnd,
               InpKzNycStart, InpKzNycEnd);
   PrintFormat("[CBR] Asian Range: %d:00-%d:00 | Levels: Asian H/L + PrevDay H/L",
               InpAsianStartH, InpAsianEndH);
   PrintFormat("[CBR] Risk: %.2f%% | MaxLot=%.2f | MaxOpen=%d | MaxDay=%d | DailyDD=%.1f%%",
               InpRiskPct, InpMaxLot, InpMaxOpen, InpMaxPerDay, InpDailyDD);

   return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
//| Expert deinitialization                                           |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   CBR_DeinitIndicators();
   CBR_DeinitNews();
   CBR_DeinitDatalog();
   PrintFormat("[CBR] EA_Cobra v%s deinitialized | reason=%d", CBR_VERSION, reason);
}

//+------------------------------------------------------------------+
//| Trade transaction handler — EQL + trade CSV                       |
//+------------------------------------------------------------------+
void OnTradeTransaction(const MqlTradeTransaction &trans,
                        const MqlTradeRequest &request,
                        const MqlTradeResult &result)
{
   if(trans.type != TRADE_TRANSACTION_DEAL_ADD) return;
   ulong deal = trans.deal;
   if(deal == 0) return;
   if(!HistoryDealSelect(deal)) return;

   long magic = HistoryDealGetInteger(deal, DEAL_MAGIC);
   if(magic != InpMagic) return;

   EQL_OnDeal(deal);

   ENUM_DEAL_ENTRY entry = (ENUM_DEAL_ENTRY)HistoryDealGetInteger(deal, DEAL_ENTRY);
   if(entry == DEAL_ENTRY_OUT || entry == DEAL_ENTRY_INOUT)
      CBR_AppendTradeCsv(deal, InpMagic, _Symbol);
}

//+------------------------------------------------------------------+
//| Expert tick function                                              |
//+------------------------------------------------------------------+
void OnTick()
{
   //=== 1. New bar gate (M15) ===
   datetime barTime = iTime(_Symbol, PERIOD_CURRENT, 0);
   if(barTime == g_cbrLastBar) return;
   g_cbrLastBar = barTime;

   //=== 2. Daily reset ===
   CBR_DailyReset();

   //=== 3. Current time ===
   MqlDateTime now;
   TimeToStruct(TimeCurrent(), now);

   //=== 4. Build levels (once per day, when LDN KZ starts) ===
   // Asian range is built when hour >= AsianEndH
   if(now.hour >= InpAsianEndH)
   {
      CBR_BuildAsianRange(_Symbol, InpAsianStartH, InpAsianEndH, g_cbrPt);
      CBR_BuildPrevDayLevels(_Symbol);
   }

   //=== 5. Kill zone detection ===
   ENUM_CBR_KILLZONE kz = CBR_GetKillZone(now.hour,
                              InpKzLdnStart, InpKzLdnEnd,
                              InpKzNyStart, InpKzNyEnd,
                              InpKzNycStart, InpKzNycEnd);

   //=== 6. Position management (ALWAYS runs) ===
   CBR_ManagePositions(_Symbol, InpMagic, now.day_of_week, now.hour);

   //=== 7. Skip if outside kill zones ===
   if(kz == CBR_KZ_NONE) return;

   //=== 8. Skip weekends ===
   if(CBR_IsWeekend(now.day_of_week)) return;

   //=== 8b. v2.2: Skip Wednesday (PF 0.87 in v2.1 — no edge) ===
   #ifdef CBR_WED_SKIP
   if(now.day_of_week == 3) return;
   #endif

   //=== 8c. v2.5: Skip Thursday if enabled (PF 1.08 NYC-only — near breakeven) ===
   if(InpSkipThu && now.day_of_week == 4) return;

   //=== 9. Friday flatten ===
   if(CBR_IsFridayFlatten(now.day_of_week, now.hour))
   {
      CBR_CloseAll(_Symbol, InpMagic);
      return;
   }

   //=== 10. Check block reasons ===
   if(IsMarketHoliday()) return;
   string blockReason = CBR_GetBlockReason(InpDailyDD, InpMaxPerDay, InpMaxOpen,
                                            InpKillSwitch, kz, InpMaxPerKZ);
   if(blockReason != "")
      return;

   //=== 10b. News filter gate ===
   if(InpNewsFilter && CBR_IsNewsBlocked(_Symbol, InpNewsBeforeMin, InpNewsAfterMin))
      return;

   //=== 11. Generate LEVEL-BASED signal (v2 core change) ===
   CBR_Signal sig;
   CBR_CheckLevelSignal(_Symbol, kz, CBR_MAX_SPREAD_PTS, sig);

   //=== 12. Log signal ===
   if(InpDatalog && sig.rejectReason != "no_killzone")
      CBR_LogSignal(sig, false);

   //=== 13. Execute if valid ===
   if(sig.valid)
   {
      double dayRiskMult = CBR_GetDayRiskMult(now.day_of_week);
      double d1RegimeMult = CBR_GetD1RegimeMult();
      bool executed = CBR_ExecuteSignal(_Symbol, sig, InpRiskPct, InpMaxLot,
                                         dayRiskMult * d1RegimeMult, InpMagic);

      if(InpDatalog)
         CBR_LogSignal(sig, executed);
   }
}

//+------------------------------------------------------------------+
//| Tester function (custom optimization criterion)                   |
//+------------------------------------------------------------------+
double OnTester()
{
   // Custom criterion: Balance * sqrt(trades) / (1 + max_dd%)
   double balance     = TesterStatistics(STAT_PROFIT);
   double trades      = TesterStatistics(STAT_TRADES);
   double maxDD       = TesterStatistics(STAT_EQUITY_DDREL_PERCENT);
   double pf          = TesterStatistics(STAT_PROFIT_FACTOR);

   if(trades < 50 || maxDD <= 0.0 || pf <= 0.0)
      return -10000.0;

   double score = balance * MathSqrt(trades) / (1.0 + maxDD);
   return score;
}
//+------------------------------------------------------------------+
