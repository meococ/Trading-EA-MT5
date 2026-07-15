//+------------------------------------------------------------------+
//| EA_SBSparkBook.mq5 — Dual-sleeve research book                   |
//| Sleeve A: SilverBullet A1 (002505 weekend-flat binding)          |
//| Sleeve B: Spark Asian M15 (002614 defaults)                      |
//| Hypothesis: HYP-PORTFOLIO-SB-SPARK-RUNNER-001                     |
//|                                                                  |
//| Distinct magics; closed-bar sleeves; no Cobra/ITSM/LNY/IB.       |
//| Attach to USDJPY M15.                                            |
//+------------------------------------------------------------------+
#property copyright "SonicR / EA_SBSparkBook"
#property version   "1.00"
#property strict

#include "Modules\SB_A1_Module.mqh"
#include "Modules\SparkAsian_Module.mqh"

input group "=== Book Master ==="
input bool     InpEnabled          = true;
input int      InpDeviation        = 30;
input string   InpSymbol           = "USDJPY";

input group "=== Sleeve A — SilverBullet A1 (002505) ==="
input bool     InpEnable_SB        = true;
input ulong    InpMagic_SB         = 20260325;
input double   InpRisk_SB          = 1.0;
input double   InpMaxLot_SB        = 0.50;

input group "=== Sleeve B — Spark Asian (002614) ==="
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

   PrintFormat("[BOOK] EA_SBSparkBook | HYP-PORTFOLIO-SB-SPARK-RUNNER-001 | SB=%s magic=%I64u | SPK=%s magic=%I64u",
               InpEnable_SB ? "ON" : "OFF", InpMagic_SB,
               InpEnable_SPK ? "ON" : "OFF", InpMagic_SPK);
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

   if(InpEnable_SB)
      SB_OnTick(InpSymbol, InpMagic_SB, InpRisk_SB, InpMaxLot_SB);
   if(InpEnable_SPK)
      SPK_OnTick(InpSymbol, InpMagic_SPK, InpRisk_SPK, InpMaxLot_SPK);
}
