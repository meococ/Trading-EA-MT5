//+------------------------------------------------------------------+
//| EA_FVGConfluence.mq5                                               |
//| FVG Scalping + Confluence (M5, HTF H1/H4) — closed-bar only        |
//| Owner Path-C override build 2026-07-15 — NOT promotion-ready       |
//+------------------------------------------------------------------+
#property copyright "Owner Path-C override / research scaffold"
#property version   "1.00"
#property strict
#property description "M5 FVG + confluence. Closed-bar decisions (shift>=1)."
#property description "Owner override build — news filter stub; not promotion-ready."

#include <Trade\Trade.mqh>
#include <Trade\PositionInfo.mqh>

#include "Include/FVG_Types.mqh"
#include "Include/FVG_Detect.mqh"
#include "Include/FVG_HTF.mqh"
#include "Include/FVG_OrderBlock.mqh"
#include "Include/FVG_PremiumDiscount.mqh"
#include "Include/FVG_Session.mqh"
#include "Include/FVG_Risk.mqh"
#include "Include/FVG_Execution.mqh"

//+------------------------------------------------------------------+
input group "=== Core ==="
input bool              InpEnabled            = true;
input bool              InpKillSwitch         = false;   // block new entries
input long              InpMagic              = 26071501;
input string            InpComment            = "FVGConfl";
input ENUM_SYMBOL_PACK  InpSymbolPack         = PACK_AUTO;

input group "=== Risk ==="
input double            InpRiskPct            = 0.25;    // challenge default
input double            InpRiskPctLive        = 0.15;    // live preset reference
input bool              InpUseLiveRisk        = false;   // if true use InpRiskPctLive
input double            InpMaxLot             = 2.0;
input double            InpDailyLossLimitPct  = 2.0;
input int               InpMaxTradesPerDay    = 3;
input int               InpMaxConcurrent      = 1;
input bool              InpOnePositionSymbol  = true;
input double            InpMaxSpreadPips      = 2.5;

input group "=== FVG Detect ==="
input int               InpFVGLookback        = 30;
input double            InpMinBodyATR         = 0.80;    // impulse body vs ATR
input double            InpMinBodyRange       = 0.55;    // or body/range
input double            InpMaxFillPct         = 0.50;    // prefer unmitigated / partial
input double            InpMinGapPipsOverride = 0.0;     // 0 = use symbol pack
input double            InpSLBufferPipsOverride = 0.0;   // 0 = use symbol pack

input group "=== Confluence ==="
input int               InpMinConfluence      = 3;
input bool              InpSessionHardFilter  = true;    // London/NY required to trade
input bool              InpCountSessionInScore = true;   // also count as confluence factor
input int               InpOBSearchBars       = 8;
input double            InpOBMaxDistATR       = 0.75;
input int               InpPDLookback         = 40;
input int               InpPivotLR            = 2;
input int               InpSweepLookback      = 12;

input group "=== HTF ==="
input ENUM_HTF_PERIOD   InpHTFPeriod          = HTF_H1;  // optional H4
input int               InpHTFLookback        = 40;
input int               InpHTFPivotLR         = 2;

input group "=== Entry ==="
input ENUM_ENTRY_MODE   InpEntryMode          = ENTRY_EITHER;
input double            InpEntryDepthMin      = 0.40;    // mid-gap 40-60%
input double            InpEntryDepthMax      = 0.60;

input group "=== Exits ==="
input double            InpMinRR              = 2.0;
input bool              InpUseStructureTP     = false;   // optional swing TP if >= min RR
input bool              InpUsePartial         = true;
input double            InpPartialPct         = 0.50;
input bool              InpUseBreakEven       = true;
input double            InpBETriggerR         = 1.0;
input bool              InpUseTrail           = true;
input double            InpTrailStartR        = 1.5;
input double            InpTrailStepR         = 0.80;

input group "=== Session (broker-server + offsets) ==="
input int               InpTimeHourOffset     = 0;
input int               InpTimeMinuteOffset   = 0;
input bool              InpUseLondon          = true;
input int               InpLondonStartHour    = 8;
input int               InpLondonStartMin     = 0;
input int               InpLondonEndHour      = 12;
input int               InpLondonEndMin       = 0;
input bool              InpUseNewYork         = true;
input int               InpNYStartHour        = 13;
input int               InpNYStartMin         = 0;
input int               InpNYEndHour          = 17;
input int               InpNYEndMin           = 0;

input group "=== News (STUB) ==="
input bool              InpUseNewsFilter      = false;   // STUB: no calendar feed; manual windows only
input string            InpNewsBlockWindows   = "";      // e.g. "12:30-14:00;18:00-19:00"

input group "=== Execution ==="
input int               InpDeviation          = 30;
input int               InpATRPeriod          = 14;

//+------------------------------------------------------------------+
CTrade         g_trade;
CPositionInfo  g_pos;
SRiskState     g_risk;
SPosManage     g_manage;
SSymbolPack    g_pack;
int            g_hATR = INVALID_HANDLE;
datetime       g_lastBarTime = 0;

//+------------------------------------------------------------------+
ENUM_TIMEFRAMES HTF_TF()
{
   return (InpHTFPeriod == HTF_H4) ? PERIOD_H4 : PERIOD_H1;
}

double ATR_Closed(const int shift = 1)
{
   if(g_hATR == INVALID_HANDLE)
      return 0.0;
   double buf[];
   if(CopyBuffer(g_hATR, 0, shift, 1, buf) != 1)
      return 0.0;
   return buf[0];
}

bool SpreadOK()
{
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double spread_pips = FVG_PriceToPips(ask - bid);
   return (spread_pips <= InpMaxSpreadPips);
}

bool SessionOK()
{
   return FVG_InLondonOrNY(InpTimeHourOffset, InpTimeMinuteOffset,
                           InpUseLondon, InpLondonStartHour, InpLondonStartMin,
                           InpLondonEndHour, InpLondonEndMin,
                           InpUseNewYork, InpNYStartHour, InpNYStartMin,
                           InpNYEndHour, InpNYEndMin);
}

SConfluence ScoreConfluence(const SFVGZone &zone)
{
   SConfluence c;
   ZeroMemory(c);
   ENUM_TIMEFRAMES tf = HTF_TF();

   c.htf_aligned = FVG_HTF_Aligned(zone.dir, tf, InpHTFLookback, InpHTFPivotLR);

   double atr = ATR_Closed(1);
   double ob_dist = (atr > 0.0) ? atr * InpOBMaxDistATR : FVG_PipsToPrice(10.0);
   c.order_block = FVG_HasNearbyOB(zone, InpOBSearchBars, ob_dist);

   c.premium_discount = FVG_PD_Aligned(zone.dir, InpPDLookback, InpPivotLR);
   c.liquidity_sweep = FVG_LiquiditySweepPrior(zone.dir, InpPDLookback, InpPivotLR, InpSweepLookback);
   c.session_ok = SessionOK();

   int score = 0;
   if(c.htf_aligned) score++;
   if(c.order_block) score++;
   if(c.premium_discount) score++;
   if(c.liquidity_sweep) score++;
   if(InpCountSessionInScore && c.session_ok) score++;
   c.score = score;
   return c;
}

bool EntrySignalOK(const SFVGZone &zone)
{
   // Interaction on closed bar shift=1 only
   if(!FVG_PriceInteractsZone(zone, 1))
      return false;

   bool rej = FVG_IsRejectionCandle(1, zone.dir);
   double depth = FVG_EntryDepthPct(zone, 1);
   bool mid = (depth >= InpEntryDepthMin && depth <= InpEntryDepthMax);

   if(InpEntryMode == ENTRY_REJECTION)
      return rej;
   if(InpEntryMode == ENTRY_MID_GAP)
      return mid;
   return (rej || mid);
}

bool BuildPlan(const SFVGZone &zone, const SConfluence &confl, STradePlan &plan)
{
   ZeroMemory(plan);
   plan.zone = zone;
   plan.confl = confl;
   plan.dir = zone.dir;

   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   bool is_buy = (zone.dir == FVG_DIR_BULL);
   plan.entry = is_buy ? ask : bid;

   double buf_pips = (InpSLBufferPipsOverride > 0.0) ? InpSLBufferPipsOverride : g_pack.sl_buffer_pips;
   double buf = FVG_PipsToPrice(buf_pips);

   if(is_buy)
      plan.sl = zone.bottom - buf;
   else
      plan.sl = zone.top + buf;

   plan.risk_points = MathAbs(plan.entry - plan.sl);
   if(plan.risk_points <= 0.0)
      return false;

   double tp_rr = plan.entry;
   if(is_buy)
      tp_rr = plan.entry + plan.risk_points * InpMinRR;
   else
      tp_rr = plan.entry - plan.risk_points * InpMinRR;

   plan.tp = tp_rr;

   if(InpUseStructureTP)
   {
      double sh, slv;
      datetime th, tl;
      if(FVG_LastSwingHL(PERIOD_CURRENT, InpPDLookback, InpPivotLR, sh, th, slv, tl))
      {
         if(is_buy && sh > plan.entry)
         {
            double rr = (sh - plan.entry) / plan.risk_points;
            if(rr >= InpMinRR)
               plan.tp = sh;
         }
         else if(!is_buy && slv < plan.entry)
         {
            double rr = (plan.entry - slv) / plan.risk_points;
            if(rr >= InpMinRR)
               plan.tp = slv;
         }
      }
   }

   plan.reason = StringFormat("FVG %s score=%d",
                              (is_buy ? "BULL" : "BEAR"), confl.score);
   return true;
}

void TryEnter()
{
   if(!InpEnabled || InpKillSwitch)
      return;
   if(FVG_DailyLossHit(g_risk, InpDailyLossLimitPct))
      return;
   if(g_risk.trades_today >= InpMaxTradesPerDay)
      return;
   if(FVG_CountOpenPositions(InpMagic, InpOnePositionSymbol) >= InpMaxConcurrent)
      return;
   if(!SpreadOK())
      return;

   if(InpSessionHardFilter && !SessionOK())
      return;

   if(FVG_NewsBlocksEntry(InpUseNewsFilter, InpNewsBlockWindows,
                          InpTimeHourOffset, InpTimeMinuteOffset))
      return;

   double atr = ATR_Closed(1);
   if(atr <= 0.0)
      return;

   double min_gap = FVG_MinGapPrice(g_pack, atr);
   if(InpMinGapPipsOverride > 0.0)
      min_gap = FVG_PipsToPrice(InpMinGapPipsOverride);

   SFVGZone zone;
   if(!FVG_FindLatestZone(InpFVGLookback, atr, min_gap,
                          InpMinBodyATR, InpMinBodyRange, InpMaxFillPct, zone))
      return;

   if(!EntrySignalOK(zone))
      return;

   SConfluence confl = ScoreConfluence(zone);
   if(confl.score < InpMinConfluence)
      return;

   STradePlan plan;
   if(!BuildPlan(zone, confl, plan))
      return;

   double risk = InpUseLiveRisk ? InpRiskPctLive : InpRiskPct;
   double lots = FVG_LotsForRisk(risk, plan.entry, plan.sl, InpMaxLot);
   if(lots <= 0.0)
   {
      Print("FVG: lot sizing failed");
      return;
   }

   bool is_buy = (plan.dir == FVG_DIR_BULL);
   if(FVG_OpenTrade(g_trade, is_buy, lots, plan.sl, plan.tp,
                    InpMagic, InpComment, InpDeviation))
   {
      g_risk.trades_today++;
      Print("FVG: opened ", plan.reason,
            " lots=", lots, " SL=", plan.sl, " TP=", plan.tp,
            " pack=", g_pack.name);
   }
}

//+------------------------------------------------------------------+
int OnInit()
{
   FVG_ResolvePack(InpSymbolPack, g_pack);
   g_hATR = iATR(_Symbol, PERIOD_CURRENT, InpATRPeriod);
   if(g_hATR == INVALID_HANDLE)
   {
      Print("FVG: ATR handle failed");
      return INIT_FAILED;
   }

   ZeroMemory(g_risk);
   ZeroMemory(g_manage);
   g_risk.day_start_equity = AccountInfoDouble(ACCOUNT_EQUITY);
   g_risk.peak_equity = g_risk.day_start_equity;
   g_risk.day_key = FVG_DayOfYear(FVG_BrokerNow());

   g_trade.SetExpertMagicNumber(InpMagic);
   g_trade.SetDeviationInPoints(InpDeviation);
   g_trade.SetTypeFillingBySymbol(_Symbol);

   Print("EA_FVGConfluence init pack=", g_pack.name,
         " minGapPips=", g_pack.min_gap_pips,
         " slBufPips=", g_pack.sl_buffer_pips,
         " magic=", InpMagic,
         " newsStub=", (InpUseNewsFilter ? "on-manual-windows" : "off"));
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   if(g_hATR != INVALID_HANDLE)
   {
      IndicatorRelease(g_hATR);
      g_hATR = INVALID_HANDLE;
   }
}

void OnTick()
{
   FVG_RiskResetDay(g_risk);

   // Manage open positions every tick
   FVG_ManageOpen(g_trade, g_pos, g_manage, InpMagic,
                  InpUsePartial, InpPartialPct,
                  InpUseBreakEven, InpBETriggerR,
                  InpUseTrail, InpTrailStartR, InpTrailStepR);

   // Signal decisions only on new closed bar
   datetime t1 = iTime(_Symbol, PERIOD_CURRENT, 1);
   if(t1 == 0 || t1 == g_lastBarTime)
      return;
   g_lastBarTime = t1;

   TryEnter();
}

//+------------------------------------------------------------------+
