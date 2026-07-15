//+------------------------------------------------------------------+
//| EA_SBSparkBook.mq5 — Clean-book dual-sleeve research runner      |
//| Sleeve A: SilverBullet RR2/MaxKZ2 (authority 20260714_194548)    |
//| Sleeve B: Spark Asian M15 (authority 20260714_193358 defaults)   |
//| Hypothesis: HYP-BOOK-CLEAN-APRIORI-RR2SPARK-001                   |
//|                                                                  |
//| Frozen a priori caps (clean-book freeze):                        |
//|   heat=1 concurrent open sleeve; priority A > B                  |
//|   equal 1:1 risk weight (0.5% each)                              |
//| Distinct magics; closed-bar sleeves; no densify.                 |
//| Attach to USDJPY M15.                                            |
//|                                                                  |
//| Prior killed runner HYP-PORTFOLIO-SB-SPARK-RUNNER-001 (A1+Spark   |
//| 20260714_224302) remains archived — this is RR2 clean-book path. |
//+------------------------------------------------------------------+
#property copyright "SonicR / EA_SBSparkBook"
#property version   "1.10"
#property strict

#include "Modules\SB_A1_Module.mqh"
#include "Modules\SparkAsian_Module.mqh"

input group "=== Book Master ==="
input bool     InpEnabled          = true;
input int      InpDeviation        = 30;
input string   InpSymbol           = "USDJPY";
input bool     InpHeatCap1         = true;   // Max concurrent open sleeves = 1

input group "=== Sleeve A — SB RR2 MaxKZ2 (194548) ==="
input bool     InpEnable_SB        = true;
input ulong    InpMagic_SB         = 20260715;  // distinct from killed A1 book
input double   InpRisk_SB          = 0.5;       // equal 1:1 with Spark
input double   InpMaxLot_SB        = 0.50;

input group "=== Sleeve B — Spark Asian (193358) ==="
input bool     InpEnable_SPK       = true;
input ulong    InpMagic_SPK        = 880930;
input double   InpRisk_SPK         = 0.50;
input double   InpMaxLot_SPK       = 1.0;

int OnInit()
{
   if(!InpEnabled)
      return INIT_SUCCEEDED;

   SymbolSelect(InpSymbol, true);
   iTime(InpSymbol, PERIOD_M15, 0);

   if(InpEnable_SB)
   {
      if(!SB_Init(InpSymbol, InpMagic_SB, InpDeviation))
      {
         Print("[BOOK] FATAL: SB_Init failed");
         return INIT_FAILED;
      }
   }
   if(InpEnable_SPK)
   {
      if(!SPK_Init(InpSymbol, InpMagic_SPK, InpDeviation))
      {
         Print("[BOOK] FATAL: SPK_Init failed");
         return INIT_FAILED;
      }
   }

   PrintFormat("[BOOK] EA_SBSparkBook v1.10 | HYP-BOOK-CLEAN-APRIORI-RR2SPARK-001 | "
               "SB_RR2=%s magic=%I64u risk=%.2f | SPK=%s magic=%I64u risk=%.2f | heat1=%s",
               InpEnable_SB ? "ON" : "OFF", InpMagic_SB, InpRisk_SB,
               InpEnable_SPK ? "ON" : "OFF", InpMagic_SPK, InpRisk_SPK,
               InpHeatCap1 ? "ON" : "OFF");
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   if(InpEnable_SB)  SB_Deinit();
   if(InpEnable_SPK) SPK_Deinit();
}

void OnTick()
{
   if(!InpEnabled)
      return;

   // Heat=1 + priority A>B (clean-book freeze):
   // - Process SB first.
   // - Allow a sleeve to run if it already has a position (manage exits)
   //   OR the other sleeve has no open position (may enter).
   // - After SB, Spark may enter only if SB still flat.
   const bool heat = InpHeatCap1;

   int sbPos  = InpEnable_SB  ? SB_CountMyPositions() : 0;
   int spkPos = InpEnable_SPK ? SPK_CountPositions(InpMagic_SPK, InpSymbol) : 0;

   if(InpEnable_SB)
   {
      if(!heat || sbPos > 0 || spkPos == 0)
         SB_OnTick(InpSymbol, InpMagic_SB, InpRisk_SB, InpMaxLot_SB);
   }

   sbPos = InpEnable_SB ? SB_CountMyPositions() : 0;
   spkPos = InpEnable_SPK ? SPK_CountPositions(InpMagic_SPK, InpSymbol) : 0;

   if(InpEnable_SPK)
   {
      if(!heat || spkPos > 0 || sbPos == 0)
         SPK_OnTick(InpSymbol, InpMagic_SPK, InpRisk_SPK, InpMaxLot_SPK);
   }
}
