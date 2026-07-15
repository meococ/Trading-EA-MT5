//+------------------------------------------------------------------+
//| EA_Cobra_v1.mq5 — Kill Zone Momentum Cascade                    |
//| Symbol: XAUUSD  |  Period: M15  |  Style: Intraday Scalp        |
//|                                                                   |
//| EDGE HYPOTHESIS:                                                  |
//| Strong momentum bars in high-liquidity kill zones (London Open,  |
//| NY Open, NY Close) predict continuation. Filter by H1 trend      |
//| alignment, bar quality (body ratio + close location), and ATR    |
//| context. Kill zone timing = highest liquidity = lowest noise.    |
//|                                                                   |
//| DESIGN PRINCIPLES:                                                |
//| - Signals on bar[1] ONLY (no lookahead, no repaint)              |
//| - Hard SL on every trade (1.2 * ATR, clamped 400-4000 pts)      |
//| - Session-aware R:R (London 3.0, NY 2.5, NYC 2.0)               |
//| - Break-even at 1.0R profit                                      |
//| - Friday flatten at 17:00                                         |
//| - Day risk multipliers (Mon 0.85, Wed 0.70)                      |
//| - Max 2 trades per kill zone, 6 per day                          |
//| - Daily DD kill at 4.0%                                           |
//|                                                                   |
//| Max | 2026-03-19 | v1.0                                         |
//+------------------------------------------------------------------+
#property copyright "Max — EA_Cobra v1"
#property link      ""
#property version   "1.00"
#property strict

//--- Include modules
#include "Include\CBR_Config.mqh"
#include "Include\CBR_Types.mqh"
#include "Include\CBR_SessionTime.mqh"
#include "Include\CBR_Indicators.mqh"
#include "Include\CBR_SignalEngine.mqh"
#include "Include\CBR_RiskExec.mqh"
#include "Include\CBR_Datalog.mqh"

//+------------------------------------------------------------------+
//| Input Parameters                                                  |
//+------------------------------------------------------------------+
input group "═══ General ═══"
input ulong    InpMagic         = 202603;    // Magic Number
input int      InpDeviation     = 30;        // Max Slippage (pts)
input bool     InpKillSwitch    = false;     // Kill Switch (disable all)

input group "═══ Kill Zone Windows (Server Time) ═══"
input int      InpKzLdnStart    = 7;         // London KZ Start Hour
input int      InpKzLdnEnd      = 9;         // London KZ End Hour
input int      InpKzNyStart     = 13;        // NY KZ Start Hour
input int      InpKzNyEnd       = 15;        // NY KZ End Hour
input int      InpKzNycStart    = 16;        // NY Close KZ Start Hour
input int      InpKzNycEnd      = 17;        // NY Close KZ End Hour

input group "═══ Risk Management ═══"
input double   InpRiskPct       = 0.75;      // Risk % per trade
input double   InpMaxLot        = 0.50;      // Max lot per trade
input int      InpMaxOpen       = 3;         // Max simultaneous positions
input int      InpMaxPerDay     = 6;         // Max trades per day
input int      InpMaxPerKZ      = 2;         // Max trades per kill zone
input double   InpDailyDD       = 4.0;       // Daily DD Limit (%)

input group "═══ Datalog ═══"
input bool     InpDatalog       = true;      // Enable CSV signal log

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

   // Init datalog
   if(InpDatalog)
      CBR_InitDatalog(_Symbol);

   PrintFormat("[CBR] EA_Cobra v%s initialized | Symbol=%s | TF=%s | Magic=%d",
               CBR_VERSION, _Symbol, EnumToString(_Period), InpMagic);
   PrintFormat("[CBR] Kill Zones: LDN=%d:00-%d:00 | NY=%d:00-%d:00 | NYC=%d:00-%d:00",
               InpKzLdnStart, InpKzLdnEnd, InpKzNyStart, InpKzNyEnd,
               InpKzNycStart, InpKzNycEnd);
   PrintFormat("[CBR] Risk: %.2f%% | MaxLot=%.2f | MaxOpen=%d | MaxDay=%d | MaxKZ=%d | DailyDD=%.1f%%",
               InpRiskPct, InpMaxLot, InpMaxOpen, InpMaxPerDay, InpMaxPerKZ, InpDailyDD);

   return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
//| Expert deinitialization                                           |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   CBR_DeinitIndicators();
   CBR_DeinitDatalog();
   PrintFormat("[CBR] EA_Cobra v%s deinitialized | reason=%d", CBR_VERSION, reason);
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

   //=== 4. Kill zone detection ===
   ENUM_CBR_KILLZONE kz = CBR_GetKillZone(now.hour,
                              InpKzLdnStart, InpKzLdnEnd,
                              InpKzNyStart, InpKzNyEnd,
                              InpKzNycStart, InpKzNycEnd);

   //=== 5. Position management (ALWAYS runs) ===
   CBR_ManagePositions(_Symbol, InpMagic, now.day_of_week, now.hour);

   //=== 6. Skip if outside kill zones ===
   if(kz == CBR_KZ_NONE) return;

   //=== 7. Skip weekends ===
   if(CBR_IsWeekend(now.day_of_week)) return;

   //=== 8. Friday flatten (no new trades, close existing) ===
   if(CBR_IsFridayFlatten(now.day_of_week, now.hour))
   {
      CBR_CloseAll(_Symbol, InpMagic);
      return;
   }

   //=== 9. Check block reasons ===
   string blockReason = CBR_GetBlockReason(InpDailyDD, InpMaxPerDay, InpMaxOpen,
                                            InpKillSwitch, kz, InpMaxPerKZ);
   if(blockReason != "")
   {
      // Don't spam — only log once per bar
      return;
   }

   //=== 10. Generate signal ===
   CBR_Signal sig;
   CBR_CheckMomentumSignal(_Symbol, kz, CBR_MAX_SPREAD_PTS, sig);

   //=== 11. Log signal (if datalog enabled) ===
   if(InpDatalog && sig.rejectReason != "no_killzone")
      CBR_LogSignal(sig, false);  // Will update to true if executed

   //=== 12. Execute if valid ===
   if(sig.valid)
   {
      double dayRiskMult = CBR_GetDayRiskMult(now.day_of_week);
      bool executed = CBR_ExecuteSignal(_Symbol, sig, InpRiskPct, InpMaxLot,
                                         dayRiskMult, InpMagic);

      // Update log with execution result
      if(InpDatalog)
         CBR_LogSignal(sig, executed);
   }
}

//+------------------------------------------------------------------+
//| Tester function (for optimization)                                |
//+------------------------------------------------------------------+
double OnTester()
{
   // Custom criterion: Balance * sqrt(trades) / (1 + max_dd%)
   // Rewards: high profit, many trades, low drawdown
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
