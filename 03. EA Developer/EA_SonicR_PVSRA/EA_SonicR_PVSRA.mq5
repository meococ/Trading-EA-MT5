//+------------------------------------------------------------------+
//| EA_SonicR_PVSRA.mq5                                              |
//| HYP-SONICR-PVSRA-CLASSIC-XAUUSD-M15-001                          |
//| Classic closed-bar Sonic R + PVSRA qualifier. Tester-only.       |
//+------------------------------------------------------------------+
#property copyright "EA_SonicR_PVSRA"
#property link      "https://www.mql5.com"
#property version   "1.00"
#property strict
#property description "Classic Sonic R + reconstructed PVSRA qualifier. Closed-bar. No Scout. Tester-only."

#include <Trade/Trade.mqh>
#include "Include/SNR_Types.mqh"
#include "Include/SNR_Dragon.mqh"
#include "Include/SNR_Trend.mqh"
#include "Include/SNR_Wave.mqh"
#include "Include/SNR_PVSRA.mqh"
#include "Include/SNR_SRLevels.mqh"
#include "Include/SNR_Session.mqh"
#include "Include/SNR_Signal.mqh"
#include "Include/SNR_Risk.mqh"
#include "Include/SNR_Execution.mqh"
#include "Include/SNR_Telemetry.mqh"

input group "--- Frozen research authority ---"
input bool   InpResearchAutoMode=false;
input bool   InpEnableTelemetry=true;
input string InpHypothesisId="HYP-SONICR-PVSRA-CLASSIC-XAUUSD-M15-001";
input string InpVariantTag="SONICR_PVSRA_CLASSIC";

input group "--- Execution ---"
input long   InpMagic=16081601;
input bool   InpKillSwitch=false;
input int    InpDeviationPoints=40;
input int    InpMaxSpreadPoints=120;
input bool   InpUseHardStops=true;

input group "--- Classic Sonic R ---"
input int    InpLookback=120;
input int    InpDragonPeriod=34;
input int    InpTrendPeriod=89;
input int    InpATRPeriod=14;
input int    InpDragonSlopeBars=3;
input int    InpTrendSlopeBars=3;
input double InpDragonMinSlopeAtr=0.06;
input int    InpSwingStrength=2;
input int    InpWaveLookback=40;
input int    InpMaxPullbackAge=12;
input double InpMaxOverlapRatio=0.55;
input double InpDragonTouchAtr=0.10;

input group "--- PVSRA qualifier (reconstructed, not original Ian numbers) ---"
input bool   InpRequirePvsraSupport=false;
input int    InpVolAvgBars=10;
input double InpVolRisingMult=1.5;
input double InpVolClimaxMult=2.0;

input group "--- Round-number S/R ---"
input double InpRoundWhole=10.0;
input double InpSrRunwayAtr=0.25;

input group "--- Session (TimeGMT + UK DST, reconstructed) ---"
input int    InpLondonStartHour=7;
input int    InpLondonEndHour=10;
input int    InpNyStartHour=12;
input int    InpNyEndHour=16;
input int    InpFridayFlattenHour=20;

input group "--- Risk ---"
input double InpRiskPercent=0.25;
input double InpMaxDailyLossPct=3.5;
input double InpMaxAccountDrawdownPct=8.0;
input int    InpMaxTradesPerDay=3;
input double InpTargetR=1.0;
input double InpSlBufferAtr=0.10;
input double InpMinSlAtr=0.50;
input double InpMaxSlAtr=3.00;
input double InpMinSlSpreadMult=3.0;
input int    InpTimeStopBars=16;

const string EA_NAME="EA_SonicR_PVSRA";
const string EXPECTED_HYPOTHESIS="HYP-SONICR-PVSRA-CLASSIC-XAUUSD-M15-001";
const string EXPECTED_VARIANT="SONICR_PVSRA_CLASSIC";

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
          InpDragonMinSlopeAtr>0.0 &&
          InpSwingStrength>=1 &&
          InpWaveLookback>=10 &&
          InpMaxPullbackAge>=InpSwingStrength &&
          InpMaxOverlapRatio>0.0 && InpMaxOverlapRatio<1.0 &&
          InpVolAvgBars>=5 &&
          InpVolRisingMult>=1.0 &&
          InpVolClimaxMult>=InpVolRisingMult &&
          InpRoundWhole>0.0 &&
          InpSrRunwayAtr>=0.0 &&
          InpLondonStartHour>=0 && InpLondonStartHour<=23 &&
          InpLondonEndHour>=0 && InpLondonEndHour<=23 &&
          InpNyStartHour>=0 && InpNyStartHour<=23 &&
          InpNyEndHour>=0 && InpNyEndHour<=23 &&
          InpFridayFlattenHour>=0 && InpFridayFlattenHour<=23 &&
          InpRiskPercent>0.0 &&
          InpMaxDailyLossPct>0.0 &&
          InpMaxAccountDrawdownPct>0.0 &&
          InpMaxTradesPerDay>=1 &&
          InpTargetR>0.0 &&
          InpMinSlSpreadMult>=1.0 &&
          InpMaxSlAtr>=InpMinSlAtr &&
          InpTimeStopBars>=0 &&
          InpDeviationPoints>=0 &&
          InpMaxSpreadPoints>0 &&
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

double StructuralStop(const SnrSignalDecision &sig)
  {
   if(sig.direction>0)
     {
      double sl=sig.dragon.low;
      if(sig.wave.valid && sig.wave.pullback_price>0.0)
         sl=MathMin(sl,sig.wave.pullback_price);
      sl=MathMin(sl,sig.signal_low);
      return(sl);
     }
   double sl=sig.dragon.high;
   if(sig.wave.valid && sig.wave.pullback_price>0.0)
      sl=MathMax(sl,sig.wave.pullback_price);
   sl=MathMax(sl,sig.signal_high);
   return(sl);
  }

bool FlattenIfNeeded(const datetime current_bar_open)
  {
   ulong ticket=0;
   const int scan=SnrScanOwnedPosition(InpMagic,ticket);
   if(scan==SNR_SCAN_FAIL || scan==SNR_SCAN_MULTI)
     {
      g_runtime_failed=true;
      return(false);
     }
   if(scan!=SNR_SCAN_OWNED)
      return(true);

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
   else if(InpTimeStopBars>0)
     {
      datetime entry_time=g_entry_time;
      if(entry_time<=0 && PositionSelectByTicket(ticket))
         entry_time=(datetime)PositionGetInteger(POSITION_TIME);
      if(entry_time>0)
        {
         const int held=iBarShift(_Symbol,PERIOD_M15,entry_time,false);
         if(held>=InpTimeStopBars)
            reason="TIME_STOP";
        }
     }
   if(reason=="")
      return(true);
   if(reason=="TIME_STOP" && g_last_close_attempt_bar==current_bar_open)
      return(true);
   g_last_close_attempt_bar=current_bar_open;
   g_pending_exit_reason=reason;
   return(SnrCloseOwned(g_trade,InpMagic,InpDeviationPoints,reason,g_tel));
  }

void ManageVirtualExits()
  {
   if(InpUseHardStops)
      return;
   ulong ticket=0;
   const int scan=SnrScanOwnedPosition(InpMagic,ticket);
   if(scan==SNR_SCAN_FAIL || scan==SNR_SCAN_MULTI)
     {
      g_runtime_failed=true;
      return;
     }
   if(scan!=SNR_SCAN_OWNED || !PositionSelectByTicket(ticket))
      return;
   if(g_initial_sl<=0.0 && g_initial_tp<=0.0)
      return;
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick) || !SnrFinite(tick.bid) || !SnrFinite(tick.ask))
      return;
   const bool is_long=(PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_BUY);
   string reason="";
   if(is_long)
     {
      if(g_initial_sl>0.0 && tick.bid<=g_initial_sl)
         reason="SL";
      else if(g_initial_tp>0.0 && tick.bid>=g_initial_tp)
         reason="TP";
     }
   else
     {
      if(g_initial_sl>0.0 && tick.ask>=g_initial_sl)
         reason="SL";
      else if(g_initial_tp>0.0 && tick.ask<=g_initial_tp)
         reason="TP";
     }
   if(reason=="")
      return;
   g_pending_exit_reason=reason;
   SnrCloseOwned(g_trade,InpMagic,InpDeviationPoints,reason,g_tel);
  }

bool SubmitEntry(const SnrSignalDecision &sig)
  {
   int pos_count=0;
   int pend_count=0;
   if(SnrScanSymbolPositions(pos_count)==SNR_SCAN_FAIL ||
      SnrScanSymbolPendings(pend_count)==SNR_SCAN_FAIL)
     {
      g_runtime_failed=true;
      return(false);
     }
   if(pos_count>0 || pend_count>0)
      return(false);
   if(SnrRiskEntryBlocked(g_risk,InpMaxTradesPerDay))
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

   const double entry=(sig.direction>0 ? tick.ask : tick.bid);
   SnrRiskPlan plan;
   if(!SnrPlanTrade(_Symbol,sig.direction,entry,StructuralStop(sig),sig.atr,
                    InpSlBufferAtr,InpMinSlAtr,InpMaxSlAtr,InpMinSlSpreadMult,
                    InpTargetR,InpRiskPercent,tick.ask,tick.bid,plan))
     {
      g_tel.volume_rejects++;
      return(false);
     }

   uint retcode=0;
   if(!SnrSendMarket(g_trade,InpMagic,InpDeviationPoints,sig.direction,plan,
                     InpUseHardStops,InpVariantTag,retcode))
     {
      g_tel.entry_rejects++;
      PrintFormat("SNR001_ENTRY_REJECT dir=%s vol=%.2f entry=%.5f sl=%.5f tp=%.5f retcode=%u",
                  (sig.direction>0 ? "LONG" : "SHORT"),plan.volume,plan.entry,plan.sl,plan.tp,retcode);
      return(false);
     }

   const double fill=(g_trade.ResultPrice()>0.0 ? g_trade.ResultPrice() : plan.entry);
   g_tel.entries++;
   g_risk.daily_entries++;
   g_entry_time=sig.availability_time;
   g_entry_price=fill;
   g_initial_sl=plan.sl;
   g_initial_tp=plan.tp;
   g_entry_dir=sig.direction;
   PrintFormat("SNR001_ENTRY decision=%I64d dir=%s vol=%.2f entry=%.5f sl=%.5f tp=%.5f retcode=%u",
               (long)sig.decision_time,(sig.direction>0 ? "LONG" : "SHORT"),
               plan.volume,fill,plan.sl,plan.tp,retcode);

   if(SnrRealizedRiskOverBudget(_Symbol,sig.direction,fill,plan.sl,plan.volume,
                                InpRiskPercent,0.05))
     {
      g_pending_exit_reason="POSTFILL_RISK";
      if(SnrCloseOwned(g_trade,InpMagic,InpDeviationPoints,"POSTFILL_RISK",g_tel))
         g_tel.postfill_closes++;
     }
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
      const double fill=HistoryDealGetDouble(trans.deal,DEAL_PRICE);
      const double volume=HistoryDealGetDouble(trans.deal,DEAL_VOLUME);
      ulong ticket=0;
      if(SnrScanOwnedPosition(InpMagic,ticket)==SNR_SCAN_OWNED && PositionSelectByTicket(ticket))
        {
         const double sl=PositionGetDouble(POSITION_SL);
         const int dir=(PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_BUY ? SNR_DIR_LONG : SNR_DIR_SHORT);
         if(sl>0.0 && SnrRealizedRiskOverBudget(_Symbol,dir,fill,sl,volume,InpRiskPercent,0.05))
           {
            g_pending_exit_reason="POSTFILL_RISK";
            if(SnrCloseOwned(g_trade,InpMagic,InpDeviationPoints,"POSTFILL_RISK",g_tel))
               g_tel.postfill_closes++;
           }
        }
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
   g_risk.day_key=SnrDayKey(now);
   g_risk.day_start_equity=equity;
   g_risk.peak_equity=equity;
   SnrTelemetryOpenCsv(g_tel,InpEnableTelemetry);

   ulong ticket=0;
   const int scan=SnrScanOwnedPosition(InpMagic,ticket);
   if(scan==SNR_SCAN_FAIL || scan==SNR_SCAN_MULTI)
     {
      SnrHandlesRelease(g_handles);
      SnrTelemetryCloseCsv(g_tel);
      return(INIT_FAILED);
     }
   if(scan==SNR_SCAN_OWNED)
     {
      if(!InpUseHardStops)
        {
         g_pending_exit_reason="RESTART_VIRTUAL_UNSAFE";
         SnrCloseOwned(g_trade,InpMagic,InpDeviationPoints,"RESTART_VIRTUAL_UNSAFE",g_tel);
        }
      else if(PositionSelectByTicket(ticket))
        {
         g_entry_time=(datetime)PositionGetInteger(POSITION_TIME);
         g_entry_price=PositionGetDouble(POSITION_PRICE_OPEN);
         g_initial_sl=PositionGetDouble(POSITION_SL);
         g_initial_tp=PositionGetDouble(POSITION_TP);
         g_entry_dir=(PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_BUY ? SNR_DIR_LONG : SNR_DIR_SHORT);
        }
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
   SnrTelemetrySummary(g_tel,reason,g_runtime_failed);
   SnrTelemetryCloseCsv(g_tel);
   SnrHandlesRelease(g_handles);
  }

void OnTick()
  {
   if(g_runtime_failed)
      return;
   const datetime server_now=TimeCurrent();
   SnrRiskRefresh(g_risk,server_now,InpMaxDailyLossPct,InpMaxAccountDrawdownPct);
   ManageVirtualExits();

   const datetime current_bar_open=iTime(_Symbol,PERIOD_M15,0);
   if(current_bar_open<=0)
      return;
   FlattenIfNeeded(current_bar_open);
   if(current_bar_open==g_last_bar_open)
      return;
   g_last_bar_open=current_bar_open;
   if(g_runtime_failed || InpKillSwitch)
      return;

   ulong owned=0;
   const int owned_scan=SnrScanOwnedPosition(InpMagic,owned);
   if(owned_scan==SNR_SCAN_FAIL || owned_scan==SNR_SCAN_MULTI)
     {
      g_runtime_failed=true;
      return;
     }
   if(owned_scan==SNR_SCAN_OWNED)
      return;

   SnrSignalDecision sig;
   if(!SnrBuildClassicSignal(_Symbol,PERIOD_M15,g_handles,g_cfg,current_bar_open,sig))
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
   SnrTelemetryWriteDecision(g_tel,InpEnableTelemetry,sig,spread);

   if(!sig.fired)
     {
      SnrNoteReject(g_tel,sig);
      return;
     }
   g_tel.signals++;
   if(sig.direction>0)
      g_tel.long_signals++;
   else
      g_tel.short_signals++;
   if(InpEnableTelemetry)
      PrintFormat("SNR001_SIGNAL decision=%I64d dir=%s close=%.5f ema89=%.5f dragon_mid=%.5f slope_atr=%.4f overlap=%.3f pvsra=%d vol=%.0f avg=%.1f",
                  (long)sig.decision_time,(sig.direction>0 ? "LONG" : "SHORT"),
                  sig.signal_close,sig.trend.ema,sig.dragon.mid,sig.dragon.slope_atr,
                  sig.wave.overlap_ratio,sig.pvsra.cls,sig.pvsra.volume,sig.pvsra.average);
   SubmitEntry(sig);
  }
//+------------------------------------------------------------------+
