//+------------------------------------------------------------------+
//| EA_SonicR_PVSRA.mq5                                              |
//| HYP-SONICR-XAU-M15-PULL-002                                      |
//| Dragon mid fresh-tag + reclaim. Whole $20 TP. Tester-only.       |
//+------------------------------------------------------------------+
#property copyright "EA_SonicR_PVSRA"
#property link      "https://www.mql5.com"
#property version   "1.24"
#property strict
#property description "Sonic R XAUUSD M15 Dragon pull. Pair-specific. Tester-only."

#include <Trade/Trade.mqh>
#include "Include/SNR_Types.mqh"
#include "Include/SNR_Dragon.mqh"
#include "Include/SNR_Trend.mqh"
#include "Include/SNR_ClassicWave.mqh"
#include "Include/SNR_PVSRA.mqh"
#include "Include/SNR_SRLevels.mqh"
#include "Include/SNR_Session.mqh"
#include "Include/SNR_Signal.mqh"
#include "Include/SNR_Risk.mqh"
#include "Include/SNR_Discipline.mqh"
#include "Include/SNR_ContextScan.mqh"
#include "Include/SNR_Execution.mqh"
#include "Include/SNR_Telemetry.mqh"

#ifndef SNR_DECISION_CSV
#define SNR_DECISION_CSV 0
#endif
#ifndef SNR_OVERLAY_CSV
#define SNR_OVERLAY_CSV 0
#endif

input group "--- Frozen research authority ---"
input bool   InpResearchAutoMode=false;
input bool   InpEnableTelemetry=false;
input bool   InpEnableOverlay=false;
input string InpHypothesisId="HYP-SONICR-XAU-M15-PULL-002";
input string InpVariantTag="XAU_PULL_W4";

input group "--- Execution ---"
input long   InpMagic=16081703;
input bool   InpKillSwitch=false;
input int    InpDeviationPoints=40;
input int    InpMaxSpreadPoints=500;
input bool   InpUseHardStops=true;
input int    InpOffsetPoints=50;
input int    InpPendingTtlBars=4;

input group "--- Classic Sonic R ---"
input int    InpLookback=120;
input int    InpDragonPeriod=34;
input int    InpTrendPeriod=89;
input int    InpATRPeriod=14;
input int    InpDragonSlopeBars=3;
input int    InpTrendSlopeBars=3;
input double InpDragonMinSlopeAtr=0.0;
input int    InpSwingStrength=2;
input int    InpWaveLookback=40;
input int    InpMaxPullbackAge=4;
input double InpMaxOverlapRatio=0.55;
input double InpDragonTouchAtr=0.10;

input group "--- PVSRA labels only ---"
input bool   InpRequirePvsraSupport=false;
input int    InpVolAvgBars=10;
input double InpVolRisingMult=1.5;
input double InpVolClimaxMult=2.0;

input group "--- Round-number S/R ---"
input double InpRoundWhole=10.0;
input double InpSrRunwayAtr=0.0;
input double InpMinTpPips=2000.0;
input double InpPipSize=0.01;

input group "--- Session (TimeGMT + UK DST) ---"
input int    InpLondonStartHour=8;
input int    InpLondonEndHour=16;
input bool   InpUseNySession=true;
input int    InpNyStartHour=12;
input int    InpNyEndHour=17;
input int    InpFridayFlattenHour=20;

input group "--- Risk ---"
input double InpRiskPercent=0.25;
input double InpMaxDailyLossPct=3.5;
input double InpMaxAccountDrawdownPct=8.0;
input int    InpMaxTradesPerDay=2;
input int    InpMaxTradesPerWeek=3;
input double InpSlBufferAtr=0.15;
input double InpSlCapPips=2000.0;
input double InpMinSlSpreadMult=3.0;

const string EA_NAME="EA_SonicR_PVSRA";
const string EXPECTED_HYPOTHESIS="HYP-SONICR-XAU-M15-PULL-002";
const string EXPECTED_VARIANT="XAU_PULL_W4";

CTrade         g_trade;
SnrHandles     g_handles;
SnrClassicCfg  g_cfg;
SnrRiskState   g_risk;
SnrTelemetry   g_tel;
datetime       g_last_bar_open=0;
datetime       g_last_decision_time=0;
datetime       g_entry_time=0;
datetime       g_last_close_attempt_bar=0;
double         g_entry_price=0.0;
double         g_initial_sl=0.0;
double         g_initial_tp=0.0;
int            g_entry_dir=SNR_DIR_NONE;
string         g_pending_exit_reason="";
bool           g_runtime_failed=false;
ulong          g_pending_ticket=0;
datetime       g_pending_signal_time=0;
int            g_pending_age=0;
int            g_overlay_handle=INVALID_HANDLE;

bool SymbolAllowed()
  {
   return(StringFind(_Symbol,"XAUUSD")==0);
  }

void LoadCfg()
  {
   ZeroMemory(g_cfg);
   g_cfg.lookback=InpLookback;
   g_cfg.dragon_slope_bars=InpDragonSlopeBars;
   g_cfg.trend_slope_bars=InpTrendSlopeBars;
   g_cfg.dragon_min_slope_atr=InpDragonMinSlopeAtr;
   g_cfg.swing_strength=InpSwingStrength;
   g_cfg.wave_lookback=InpWaveLookback;
   g_cfg.max_pullback_age=InpMaxPullbackAge;
   g_cfg.max_overlap_ratio=InpMaxOverlapRatio;
   g_cfg.dragon_touch_atr=InpDragonTouchAtr;
   g_cfg.vol_avg_bars=InpVolAvgBars;
   g_cfg.vol_rising_mult=InpVolRisingMult;
   g_cfg.vol_climax_mult=InpVolClimaxMult;
   g_cfg.round_whole=InpRoundWhole;
   g_cfg.sr_runway_atr=InpSrRunwayAtr;
   g_cfg.london_start_hour=InpLondonStartHour;
   g_cfg.london_end_hour=InpLondonEndHour;
   g_cfg.ny_start_hour=InpNyStartHour;
   g_cfg.ny_end_hour=InpNyEndHour;
   g_cfg.friday_flatten_hour=InpFridayFlattenHour;
   g_cfg.require_pvsra_support=InpRequirePvsraSupport;
   g_cfg.use_ny_session=InpUseNySession;
   g_cfg.offset_points=InpOffsetPoints;
   g_cfg.pending_ttl_bars=InpPendingTtlBars;
   g_cfg.pip_size=InpPipSize;
   g_cfg.sl_cap=InpSlCapPips*InpPipSize;
   g_cfg.min_tp_runway=InpMinTpPips*InpPipSize;
  }

bool InputsSane()
  {
   return(_Period==PERIOD_M15 && SymbolAllowed() &&
          InpHypothesisId==EXPECTED_HYPOTHESIS &&
          InpVariantTag==EXPECTED_VARIANT &&
          !InpResearchAutoMode &&
          InpLookback>=120 &&
          InpDragonPeriod==34 &&
          InpTrendPeriod==89 &&
          InpATRPeriod>=2 &&
          InpDragonSlopeBars>=1 &&
          InpTrendSlopeBars>=1 &&
          InpDragonMinSlopeAtr>=0.0 &&
          InpSwingStrength>=1 &&
          InpWaveLookback>=10 &&
          InpMaxPullbackAge>=InpSwingStrength &&
          InpVolAvgBars>=5 &&
          InpVolRisingMult>=1.0 &&
          InpVolClimaxMult>=InpVolRisingMult &&
          InpRoundWhole>0.0 &&
          InpPipSize>0.0 &&
          InpMinTpPips>0.0 &&
          InpSlCapPips>0.0 &&
          InpOffsetPoints>=0 &&
          InpPendingTtlBars>=1 &&
          InpLondonStartHour>=0 && InpLondonStartHour<=23 &&
          InpLondonEndHour>=0 && InpLondonEndHour<=23 &&
          InpFridayFlattenHour>=0 && InpFridayFlattenHour<=23 &&
          InpRiskPercent>0.0 &&
          InpMaxDailyLossPct>0.0 &&
          InpMaxAccountDrawdownPct>0.0 &&
          InpMaxTradesPerDay>=1 &&
          InpMaxTradesPerWeek>=1 && InpMaxTradesPerWeek<=SNR_MAX_TRADES_WEEK &&
          InpMinSlSpreadMult>=1.0 &&
          InpDeviationPoints>=0 &&
          InpMaxSpreadPoints>0 &&
          InpRoundWhole>=1.0 &&
          InpPipSize>=0.01 &&
          InpSlCapPips>=500.0 &&
          !InpRequirePvsraSupport &&
          !SNR_SCOUT_ENABLED);
  }

void ClearEntryState()
  {
   g_entry_time=0;
   g_entry_price=0.0;
   g_initial_sl=0.0;
   g_initial_tp=0.0;
   g_entry_dir=SNR_DIR_NONE;
   g_pending_exit_reason="";
  }

void ClearPendingState()
  {
   g_pending_ticket=0;
   g_pending_signal_time=0;
   g_pending_age=0;
  }

bool FlattenIfNeeded(const datetime current_bar_open)
  {
   SnrSessionSnap session;
   if(!SnrSessionRead(TimeGMT(),g_cfg,session))
      return(false);

   string reason="";
   if(InpKillSwitch)
      reason="KILL_SWITCH";
   else if(session.flatten)
      reason="SESSION_FLAT";
   else if(g_risk.dd_locked)
      reason="DD_LOCK";
   if(reason=="")
      return(true);
   if(!SnrCancelOwnedPendings(g_trade,InpMagic,reason))
      return(false);
   ClearPendingState();

   ulong ticket=0;
   const int scan=SnrScanOwnedPosition(InpMagic,ticket);
   if(scan==SNR_SCAN_FAIL || scan==SNR_SCAN_MULTI)
     {
      g_runtime_failed=true;
      return(false);
     }
   if(scan!=SNR_SCAN_OWNED)
      return(true);
   g_last_close_attempt_bar=current_bar_open;
   g_pending_exit_reason=reason;
   return(SnrCloseOwned(g_trade,InpMagic,InpDeviationPoints,reason,g_tel));
  }

bool AgePendings()
  {
   ulong ticket=0;
   int count=0;
   const int scan=SnrScanOwnedPendings(InpMagic,ticket,count);
   if(scan==SNR_SCAN_FAIL)
     {
      g_runtime_failed=true;
      return(false);
     }
   if(scan==SNR_SCAN_FLAT)
     {
      ClearPendingState();
      return(true);
     }
   if(g_pending_ticket==0)
      g_pending_ticket=ticket;
   g_pending_age++;
   if(g_pending_age>=InpPendingTtlBars || scan==SNR_SCAN_MULTI)
     {
      if(!SnrCancelOwnedPendings(g_trade,InpMagic,"TTL"))
         return(false);
      ClearPendingState();
     }
   return(true);
  }

bool SubmitPending(const SnrSignalDecision &sig)
  {
   int pos_count=0;
   int pend_count=0;
   ulong owned_pending=0;
   if(SnrScanSymbolPositions(pos_count)==SNR_SCAN_FAIL ||
      SnrScanOwnedPendings(InpMagic,owned_pending,pend_count)==SNR_SCAN_FAIL)
     {
      g_runtime_failed=true;
      return(false);
     }
   if(pos_count>0 || pend_count>0)
      return(false);
   string disc_reason="";
   if(!SnrDisciplineAllowNewRisk(g_risk,InpMaxTradesPerDay,InpMaxTradesPerWeek,disc_reason))
     {
      g_tel.risk_lock_skips++;
      return(false);
     }

   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick) || !SnrFinite(tick.ask) || !SnrFinite(tick.bid) ||
      tick.ask<=tick.bid || tick.bid<=0.0)
      return(false);
   const double point=SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   if(point<=0.0)
      return(false);
   const double spread_points=(tick.ask-tick.bid)/point;
   if(!SnrFinite(spread_points) || spread_points>InpMaxSpreadPoints)
     {
      g_tel.spread_rejects++;
      return(false);
     }

   const double offset=(double)InpOffsetPoints*point;
   const double pending=(sig.direction>0 ? sig.signal_high+offset : sig.signal_low-offset);
   double tp=0.0;
   if(!SnrFirstWholeTarget(pending,sig.direction,InpRoundWhole,g_cfg.min_tp_runway,tp))
     {
      g_tel.sr_blocks++;
      return(false);
     }

   SnrRiskPlan plan;
   if(!SnrPlanPendingLevels(_Symbol,sig.direction,pending,sig.wave.structure_swing,tp,
                            sig.atr,InpSlBufferAtr,g_cfg.sl_cap,InpMinSlSpreadMult,
                            InpRiskPercent,tick.ask,tick.bid,plan))
     {
      g_tel.volume_rejects++;
      return(false);
     }

   uint retcode=0;
   if(!SnrSendStop(g_trade,InpMagic,InpDeviationPoints,sig.direction,plan,
                   InpUseHardStops,InpVariantTag,retcode))
     {
      g_tel.entry_rejects++;
      PrintFormat("SNR001_PENDING_REJECT dir=%s vol=%.2f px=%.5f sl=%.5f tp=%.5f retcode=%u",
                  (sig.direction>0 ? "LONG" : "SHORT"),plan.volume,plan.entry,plan.sl,plan.tp,retcode);
      return(false);
     }

   g_tel.entries++;
   SnrDisciplineNoteEntry(g_risk,InpMagic);
   g_pending_ticket=g_trade.ResultOrder();
   g_pending_signal_time=sig.decision_time;
   g_pending_age=0;
   g_entry_dir=sig.direction;
   g_initial_sl=plan.sl;
   g_initial_tp=plan.tp;
   PrintFormat("SNR001_PENDING decision=%I64d dir=%s vol=%.2f px=%.5f sl=%.5f tp=%.5f retcode=%u",
               (long)sig.decision_time,(sig.direction>0 ? "LONG" : "SHORT"),
               plan.volume,plan.entry,plan.sl,plan.tp,retcode);
   return(true);
  }

string ExitReasonName(const long reason)
  {
   if(reason==DEAL_REASON_SL)
      return("SL");
   if(reason==DEAL_REASON_TP)
      return("TP");
   if(reason==DEAL_REASON_EXPERT && g_pending_exit_reason!="")
      return(g_pending_exit_reason);
   return(StringFormat("DEAL_REASON_%d",(int)reason));
  }

void OnTradeTransaction(const MqlTradeTransaction &trans,
                        const MqlTradeRequest &request,
                        const MqlTradeResult &result)
  {
   if(request.magic!=0 && (long)request.magic!=InpMagic &&
      result.order==0 && trans.deal==0)
      return;
   if(trans.type!=TRADE_TRANSACTION_DEAL_ADD || trans.deal==0 || !SnrDealOwned(trans.deal,InpMagic))
      return;
   const long entry_kind=HistoryDealGetInteger(trans.deal,DEAL_ENTRY);
   if(entry_kind==DEAL_ENTRY_IN)
     {
      ClearPendingState();
      g_entry_time=(datetime)HistoryDealGetInteger(trans.deal,DEAL_TIME);
      g_entry_price=HistoryDealGetDouble(trans.deal,DEAL_PRICE);
      return;
     }
   if(entry_kind!=DEAL_ENTRY_OUT && entry_kind!=DEAL_ENTRY_OUT_BY)
      return;
   PrintFormat("SNR001_EXIT deal=%I64u reason=%s profit=%.2f commission=%.2f swap=%.2f",
               trans.deal,ExitReasonName(HistoryDealGetInteger(trans.deal,DEAL_REASON)),
               HistoryDealGetDouble(trans.deal,DEAL_PROFIT),
               HistoryDealGetDouble(trans.deal,DEAL_COMMISSION),
               HistoryDealGetDouble(trans.deal,DEAL_SWAP));
   ulong owned=0;
   const int scan=SnrScanOwnedPosition(InpMagic,owned);
   if(scan==SNR_SCAN_FLAT)
      ClearEntryState();
   else if(scan==SNR_SCAN_FAIL || scan==SNR_SCAN_MULTI)
      g_runtime_failed=true;
  }

int OnInit()
  {
   LoadCfg();
   SnrTelemetryReset(g_tel);
   SnrHandlesReset(g_handles);
   ZeroMemory(g_risk);
   SnrDisciplineLoad(g_risk,InpMagic);
   if(!InputsSane())
      return(INIT_PARAMETERS_INCORRECT);
   if(!SnrDragonCreate(g_handles,_Symbol,PERIOD_M15,InpDragonPeriod,InpATRPeriod) ||
      !SnrTrendCreate(g_handles,_Symbol,PERIOD_M15,InpTrendPeriod) ||
      !SnrHandlesReady(g_handles))
     {
      Print("SNR001_FATAL reason=INDICATOR_HANDLE");
      SnrHandlesRelease(g_handles);
      return(INIT_FAILED);
     }

   g_trade.SetExpertMagicNumber(InpMagic);
   g_trade.SetDeviationInPoints(InpDeviationPoints);
   g_trade.SetTypeFillingBySymbol(_Symbol);
   const datetime now=TimeCurrent();
   const double equity=AccountInfoDouble(ACCOUNT_EQUITY);
   if(g_risk.day_key==0)
      g_risk.day_key=SnrDayKey(now);
   if(g_risk.day_start_equity<=0.0)
      g_risk.day_start_equity=equity;
   if(g_risk.peak_equity<=0.0)
      g_risk.peak_equity=equity;
   SnrTelemetryOpenCsv(g_tel,(SNR_DECISION_CSV!=0 && InpEnableTelemetry));
   g_overlay_handle=SnrContextOpenCsv((SNR_OVERLAY_CSV!=0 && InpEnableOverlay));

   ulong ticket=0;
   const int scan=SnrScanOwnedPosition(InpMagic,ticket);
   if(scan==SNR_SCAN_FAIL || scan==SNR_SCAN_MULTI)
     {
      SnrHandlesRelease(g_handles);
      SnrTelemetryCloseCsv(g_tel);
      return(INIT_FAILED);
     }
   if(scan==SNR_SCAN_OWNED && PositionSelectByTicket(ticket))
     {
      g_entry_time=(datetime)PositionGetInteger(POSITION_TIME);
      g_entry_price=PositionGetDouble(POSITION_PRICE_OPEN);
      g_initial_sl=PositionGetDouble(POSITION_SL);
      g_initial_tp=PositionGetDouble(POSITION_TP);
      g_entry_dir=(PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_BUY ? SNR_DIR_LONG : SNR_DIR_SHORT);
     }

   ulong pending=0;
   int pend_count=0;
   if(SnrScanOwnedPendings(InpMagic,pending,pend_count)==SNR_SCAN_FAIL)
     {
      SnrHandlesRelease(g_handles);
      SnrTelemetryCloseCsv(g_tel);
      return(INIT_FAILED);
     }
   if(pend_count>0)
     {
      if(!SnrCancelOwnedPendings(g_trade,InpMagic,"RESTART_PENDING_UNSAFE"))
        {
         SnrHandlesRelease(g_handles);
         SnrTelemetryCloseCsv(g_tel);
         return(INIT_FAILED);
        }
      ClearPendingState();
     }

   g_last_bar_open=iTime(_Symbol,PERIOD_M15,0);
   if(g_last_bar_open<=0)
     {
      SnrHandlesRelease(g_handles);
      SnrTelemetryCloseCsv(g_tel);
      return(INIT_FAILED);
     }
   PrintFormat("SNR001_INIT ea=%s hyp=%s symbol=%s tf=M15 server=tester-only",
               EA_NAME,InpHypothesisId,_Symbol);
   return(INIT_SUCCEEDED);
  }

void OnDeinit(const int reason)
  {
   SnrDisciplineSave(g_risk,InpMagic);
   SnrTelemetrySummary(g_tel,reason,g_runtime_failed);
   SnrTelemetryCloseCsv(g_tel);
   if(g_overlay_handle!=INVALID_HANDLE)
     {
      FileClose(g_overlay_handle);
      g_overlay_handle=INVALID_HANDLE;
     }
   SnrHandlesRelease(g_handles);
  }

void OnTick()
  {
   if(g_runtime_failed)
      return;
   const datetime server_now=TimeCurrent();
   SnrDisciplineRefresh(g_risk,TimeGMT(),server_now,InpMaxDailyLossPct,InpMaxAccountDrawdownPct);
   if(g_risk.dd_locked)
      SnrDisciplineSave(g_risk,InpMagic);

   const datetime current_bar_open=iTime(_Symbol,PERIOD_M15,0);
   if(current_bar_open<=0)
      return;
   FlattenIfNeeded(current_bar_open);
   if(current_bar_open==g_last_bar_open)
      return;
   g_last_bar_open=current_bar_open;
   if(g_runtime_failed || InpKillSwitch)
      return;
   if(!AgePendings())
      return;

   ulong owned=0;
   const int owned_scan=SnrScanOwnedPosition(InpMagic,owned);
   if(owned_scan==SNR_SCAN_FAIL || owned_scan==SNR_SCAN_MULTI)
     {
      g_runtime_failed=true;
      return;
     }
   ulong pending=0;
   int pend_count=0;
   if(SnrScanOwnedPendings(InpMagic,pending,pend_count)==SNR_SCAN_FAIL)
     {
      g_runtime_failed=true;
      return;
     }

   SnrSignalDecision sig;
   if(!SnrBuildPullSignal(_Symbol,PERIOD_M15,g_handles,g_cfg,current_bar_open,sig))
     {
      g_tel.data_fails++;
      return;
     }
   if(sig.decision_time<=0 || sig.decision_time==g_last_decision_time)
      return;
   g_last_decision_time=sig.decision_time;
   g_tel.closed_bars++;
   if(sig.pvsra.support)
      g_tel.pvsra_supports++;

   MqlTick tick;
   const double spread=(SymbolInfoTick(_Symbol,tick) && tick.ask>tick.bid ? tick.ask-tick.bid : 0.0);
   SnrTelemetryWriteDecision(g_tel,(SNR_DECISION_CSV!=0 && InpEnableTelemetry),sig,spread);
   if(SNR_OVERLAY_CSV!=0)
      SnrContextWrite(g_overlay_handle,sig,g_cfg);

   if(!sig.fired)
     {
      SnrNoteReject(g_tel,sig);
      return;
     }
   if(owned_scan==SNR_SCAN_OWNED || pend_count>0)
      return;
   g_tel.signals++;
   if(sig.direction>0)
      g_tel.long_signals++;
   else
      g_tel.short_signals++;
   if(SNR_DECISION_CSV!=0 && InpEnableTelemetry)
      PrintFormat("SNR001_SIGNAL decision=%I64d dir=%s close=%.5f ema89=%.5f dragon=%.5f/%.5f legs=%d/%d/%d first=%d",
                  (long)sig.decision_time,(sig.direction>0 ? "LONG" : "SHORT"),
                  sig.signal_close,sig.trend.ema,sig.dragon.high,sig.dragon.low,
                  sig.wave.leg0_index,sig.wave.leg1_index,sig.wave.leg2_index,
                  (sig.wave.first_break ? 1 : 0));
   SubmitPending(sig);
  }
//+------------------------------------------------------------------+
