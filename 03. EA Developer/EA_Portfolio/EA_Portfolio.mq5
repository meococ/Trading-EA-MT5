//+------------------------------------------------------------------+
//| EA_Portfolio.mq5 — Master Multi-Strategy Portfolio EA             |
//| 5 EAs, 6 instances, 3 symbols, 2 timeframes                     |
//|                                                                   |
//| Strategies:                                                       |
//|   CBR  — Cobra v2.5.1      XAUUSD M15  Level+KZ hour16          |
//|   SB   — SilverBullet v2   USDJPY M15  FVG+Displacement         |
//|   ITSM — ITSM v3           USDJPY M15  Sonic R Wave Pullback    |
//|   LNY  — LondonNY v1       USDJPY M15  London→NY Continuation   |
//|   IB   — InsideBar H1      USDJPY H1   Inside Bar Breakout      |
//|   IB   — InsideBar H1      GBPUSD H1   Inside Bar Breakout      |
//|                                                                   |
//| Attach to ANY chart. Trades multi-symbol automatically.           |
//|                                                                   |
//| Max & Ngai Meo Coc | 2026-04-05 | v1.0                          |
//+------------------------------------------------------------------+
#property copyright "Max & Ngai Meo Coc — EA_Portfolio v1.0"
#property version   "1.00"
#property strict

//--- Standard includes
#include <Trade\Trade.mqh>

//--- Module includes
#include "Modules\Portfolio_Risk.mqh"
#include "Modules\CBR_Module.mqh"
#include "Modules\SB_Module.mqh"
#include "Modules\ITSM_Module.mqh"
#include "Modules\LNY_Module.mqh"
#include "Modules\IB_Module.mqh"

//+------------------------------------------------------------------+
//| Input Parameters                                                  |
//+------------------------------------------------------------------+
input group "═══ PORTFOLIO MASTER ═══"
input ulong    InpBaseMagic       = 250000;    // Base Magic Number
input int      InpDeviation       = 30;        // Max Slippage (pts)
input double   InpPortfolioMaxDD  = 25.0;      // Portfolio DD Kill (%)
input double   InpDailyMaxDD      = 8.0;       // Daily DD Kill (%)

input group "═══ STRATEGY TOGGLES ═══"
input bool     InpEnable_CBR      = true;      // Enable Cobra (XAUUSD)
input bool     InpEnable_SB       = true;      // Enable SilverBullet (USDJPY)
input bool     InpEnable_ITSM     = true;      // Enable ITSM (USDJPY)
input bool     InpEnable_LNY      = true;      // Enable LondonNY (USDJPY)
input bool     InpEnable_IB_UJ    = true;      // Enable InsideBar (USDJPY)
input bool     InpEnable_IB_GU    = true;      // Enable InsideBar (GBPUSD)

input group "═══ RISK PER STRATEGY (%) ═══"
input double   InpRisk_CBR        = 0.42;      // Cobra risk %
input double   InpRisk_SB         = 0.36;      // SilverBullet risk %
input double   InpRisk_ITSM       = 0.26;      // ITSM risk %
input double   InpRisk_LNY        = 0.36;      // LondonNY risk %
input double   InpRisk_IB_UJ      = 0.29;      // InsideBar USDJPY risk %
input double   InpRisk_IB_GU      = 0.42;      // InsideBar GBPUSD risk %

input group "═══ MAX LOT PER STRATEGY ═══"
input double   InpMaxLot_CBR      = 0.50;      // Cobra max lot
input double   InpMaxLot_SB       = 0.50;      // SilverBullet max lot
input double   InpMaxLot_ITSM     = 1.00;      // ITSM max lot
input double   InpMaxLot_LNY      = 1.00;      // LondonNY max lot
input double   InpMaxLot_IB       = 1.00;      // InsideBar max lot

input group "═══ SYMBOLS ═══"
input string   InpSymbol_CBR      = "XAUUSD";  // Cobra symbol
input string   InpSymbol_SB       = "USDJPY";  // SilverBullet symbol
input string   InpSymbol_ITSM     = "USDJPY";  // ITSM symbol
input string   InpSymbol_LNY      = "USDJPY";  // LondonNY symbol
input string   InpSymbol_IB_UJ    = "USDJPY";  // InsideBar symbol 1
input string   InpSymbol_IB_GU    = "GBPUSD";  // InsideBar symbol 2

input group "═══ DATALOG ═══"
input bool     InpDatalog          = false;     // Enable CSV signal logging

//+------------------------------------------------------------------+
//| Magic Number Offsets                                              |
//+------------------------------------------------------------------+
#define MAGIC_CBR_OFFSET    1
#define MAGIC_SB_OFFSET     2
#define MAGIC_ITSM_OFFSET   3
#define MAGIC_LNY_OFFSET    4
#define MAGIC_IB_UJ_OFFSET  5
#define MAGIC_IB_GU_OFFSET  6
#define NUM_MODULES          6

//+------------------------------------------------------------------+
//| Globals                                                           |
//+------------------------------------------------------------------+
IB_State g_ibStateUJ;
IB_State g_ibStateGU;
CTrade   g_pfTrade;     // For portfolio-level close-all

//+------------------------------------------------------------------+
//| Expert initialization                                             |
//+------------------------------------------------------------------+
int OnInit()
{
   PrintFormat("[PORTFOLIO] EA_Portfolio v1.0 initializing | BaseMagic=%d", InpBaseMagic);

   //--- Register symbols only for enabled modules (reduces tester overhead)
   if(InpEnable_CBR)   { SymbolSelect(InpSymbol_CBR, true);   iTime(InpSymbol_CBR, PERIOD_M15, 0); }
   if(InpEnable_SB)    { SymbolSelect(InpSymbol_SB, true);    iTime(InpSymbol_SB, PERIOD_M15, 0); }
   if(InpEnable_ITSM)  { SymbolSelect(InpSymbol_ITSM, true);  iTime(InpSymbol_ITSM, PERIOD_M15, 0); }
   if(InpEnable_LNY)   { SymbolSelect(InpSymbol_LNY, true);   iTime(InpSymbol_LNY, PERIOD_M15, 0); }
   if(InpEnable_IB_UJ) { SymbolSelect(InpSymbol_IB_UJ, true); iTime(InpSymbol_IB_UJ, PERIOD_M15, 0); }
   if(InpEnable_IB_GU) { SymbolSelect(InpSymbol_IB_GU, true); iTime(InpSymbol_IB_GU, PERIOD_M15, 0); }

   // Setup portfolio-level trade object
   PF_SetupTrade(g_pfTrade, InpBaseMagic, _Symbol, InpDeviation);

   // Init risk tracking
   PF_RiskInit();

   // Init each enabled module
   bool ok = true;

   if(InpEnable_CBR)
   {
      if(!CBR_Init(InpSymbol_CBR, InpBaseMagic + MAGIC_CBR_OFFSET, InpDeviation))
      { Print("[PORTFOLIO] FATAL: CBR_Init failed"); ok = false; }
      else
         PrintFormat("[PORTFOLIO] CBR (Cobra) ON | %s | Magic=%d | Risk=%.2f%%",
                     InpSymbol_CBR, InpBaseMagic + MAGIC_CBR_OFFSET, InpRisk_CBR);
   }

   if(InpEnable_SB)
   {
      if(!SB_Init(InpSymbol_SB, InpBaseMagic + MAGIC_SB_OFFSET, InpDeviation))
      { Print("[PORTFOLIO] FATAL: SB_Init failed"); ok = false; }
      else
         PrintFormat("[PORTFOLIO] SB (SilverBullet) ON | %s | Magic=%d | Risk=%.2f%%",
                     InpSymbol_SB, InpBaseMagic + MAGIC_SB_OFFSET, InpRisk_SB);
   }

   if(InpEnable_ITSM)
   {
      if(!ITSM_Init(InpSymbol_ITSM, InpBaseMagic + MAGIC_ITSM_OFFSET, InpDeviation))
      { Print("[PORTFOLIO] FATAL: ITSM_Init failed"); ok = false; }
      else
         PrintFormat("[PORTFOLIO] ITSM ON | %s | Magic=%d | Risk=%.2f%%",
                     InpSymbol_ITSM, InpBaseMagic + MAGIC_ITSM_OFFSET, InpRisk_ITSM);
   }

   if(InpEnable_LNY)
   {
      if(!LNY_Init(InpSymbol_LNY, InpBaseMagic + MAGIC_LNY_OFFSET, InpDeviation))
      { Print("[PORTFOLIO] FATAL: LNY_Init failed"); ok = false; }
      else
         PrintFormat("[PORTFOLIO] LNY (LondonNY) ON | %s | Magic=%d | Risk=%.2f%%",
                     InpSymbol_LNY, InpBaseMagic + MAGIC_LNY_OFFSET, InpRisk_LNY);
   }

   if(InpEnable_IB_UJ)
   {
      if(!IB_Init(g_ibStateUJ, InpSymbol_IB_UJ, InpBaseMagic + MAGIC_IB_UJ_OFFSET, InpDeviation))
      { Print("[PORTFOLIO] FATAL: IB_Init USDJPY failed"); ok = false; }
      else
         PrintFormat("[PORTFOLIO] IB (USDJPY) ON | Magic=%d | Risk=%.2f%%",
                     InpBaseMagic + MAGIC_IB_UJ_OFFSET, InpRisk_IB_UJ);
   }

   if(InpEnable_IB_GU)
   {
      if(!IB_Init(g_ibStateGU, InpSymbol_IB_GU, InpBaseMagic + MAGIC_IB_GU_OFFSET, InpDeviation))
      { Print("[PORTFOLIO] FATAL: IB_Init GBPUSD failed"); ok = false; }
      else
         PrintFormat("[PORTFOLIO] IB (GBPUSD) ON | Magic=%d | Risk=%.2f%%",
                     InpBaseMagic + MAGIC_IB_GU_OFFSET, InpRisk_IB_GU);
   }

   if(!ok)
   {
      Print("[PORTFOLIO] One or more modules failed to init");
      return INIT_FAILED;
   }

   PrintFormat("[PORTFOLIO] All modules initialized. Total risk: %.2f%%",
               (InpEnable_CBR   ? InpRisk_CBR   : 0) +
               (InpEnable_SB    ? InpRisk_SB    : 0) +
               (InpEnable_ITSM  ? InpRisk_ITSM  : 0) +
               (InpEnable_LNY   ? InpRisk_LNY   : 0) +
               (InpEnable_IB_UJ ? InpRisk_IB_UJ : 0) +
               (InpEnable_IB_GU ? InpRisk_IB_GU : 0));

   return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
//| Expert deinitialization                                           |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   if(InpEnable_CBR)    CBR_Deinit();
   if(InpEnable_SB)     SB_Deinit();
   if(InpEnable_ITSM)   ITSM_Deinit();
   if(InpEnable_LNY)    LNY_Deinit();
   if(InpEnable_IB_UJ)  IB_Deinit(g_ibStateUJ);
   if(InpEnable_IB_GU)  IB_Deinit(g_ibStateGU);

   PrintFormat("[PORTFOLIO] EA_Portfolio deinitialized | reason=%d", reason);
}

//+------------------------------------------------------------------+
//| Expert tick function                                              |
//+------------------------------------------------------------------+
void OnTick()
{
   //=== 1. Portfolio risk guard ===
   PF_RiskDailyReset();

   if(PF_IsPortfolioDDBreached(InpPortfolioMaxDD))
   {
      PF_CloseAllPortfolio(g_pfTrade, InpBaseMagic, NUM_MODULES);
      return;
   }

   if(PF_IsDailyDDBreached(InpDailyMaxDD))
      return;

   //=== 2. Call each enabled module ===

   if(InpEnable_CBR)
      CBR_OnTick(InpSymbol_CBR, InpBaseMagic + MAGIC_CBR_OFFSET,
                 InpRisk_CBR, InpMaxLot_CBR, InpDatalog);

   if(InpEnable_SB)
      SB_OnTick(InpSymbol_SB, InpBaseMagic + MAGIC_SB_OFFSET,
                InpRisk_SB, InpMaxLot_SB);

   if(InpEnable_ITSM)
      ITSM_OnTick(InpSymbol_ITSM, InpBaseMagic + MAGIC_ITSM_OFFSET,
                  InpRisk_ITSM, InpMaxLot_ITSM);

   if(InpEnable_LNY)
      LNY_OnTick(InpSymbol_LNY, InpBaseMagic + MAGIC_LNY_OFFSET,
                 InpRisk_LNY, InpMaxLot_LNY);

   // InsideBar: USDJPY (skip nothing) + GBPUSD (skip Mon+Wed)
   if(InpEnable_IB_UJ)
      IB_OnTick(g_ibStateUJ, InpSymbol_IB_UJ, InpBaseMagic + MAGIC_IB_UJ_OFFSET,
                InpRisk_IB_UJ, InpMaxLot_IB, false, false);

   if(InpEnable_IB_GU)
      IB_OnTick(g_ibStateGU, InpSymbol_IB_GU, InpBaseMagic + MAGIC_IB_GU_OFFSET,
                InpRisk_IB_GU, InpMaxLot_IB, true, true);
}

//+------------------------------------------------------------------+
//| Trade transaction handler — route to Cobra for trade CSV         |
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

   // Route to Cobra for trade CSV logging
   if(InpEnable_CBR && magic == (long)(InpBaseMagic + MAGIC_CBR_OFFSET))
      CBR_OnDealAdd(deal, InpBaseMagic + MAGIC_CBR_OFFSET, InpSymbol_CBR);
}

//+------------------------------------------------------------------+
//| Tester function (custom optimization criterion)                   |
//+------------------------------------------------------------------+
double OnTester()
{
   double balance = TesterStatistics(STAT_PROFIT);
   double trades  = TesterStatistics(STAT_TRADES);
   double maxDD   = TesterStatistics(STAT_EQUITY_DDREL_PERCENT);
   double pf      = TesterStatistics(STAT_PROFIT_FACTOR);

   if(trades < 50 || maxDD <= 0.0 || pf <= 0.0)
      return -10000.0;

   return balance * MathSqrt(trades) / (1.0 + maxDD);
}
//+------------------------------------------------------------------+
