//+------------------------------------------------------------------+
//| RG_Telemetry.mqh                                                 |
//| Audit trail for RollReversion: signal -> request -> order ->     |
//| deal -> position -> exit, plus the OnDeinit counter block.       |
//| Mirrors SM_Telemetry format with the RG001_ prefix; every line   |
//| carries sid= so the whole chain joins on one id.                 |
//+------------------------------------------------------------------+
#ifndef RG_TELEMETRY_MQH
#define RG_TELEMETRY_MQH

#include "RG_Types.mqh"
#include "../../EA_LiquiditySweep/Include/LSW_Types.mqh"

void RgLogSignal(const long sid,const RgSignal &s,const bool verbose)
  {
   if(!verbose)
      return;
   PrintFormat("RG001_SIGNAL sid=%I64d day_bar=%s leg=%s dir=%d gap=%.2fp",
               sid,TimeToString(s.day_bar_time,TIME_DATE|TIME_MINUTES),
               RgLegName(s.leg),s.direction,s.gap_pips);
  }

void RgLogReject(const long sid,const string stage,const string reason,
                 const bool verbose)
  {
   if(!verbose)
      return;
   PrintFormat("RG001_REJECT sid=%I64d stage=%s reason=%s",sid,stage,reason);
  }

void RgLogRequest(const long sid,const LswPlan &p,const RgSignal &s,
                  const double risk_percent)
  {
   PrintFormat("RG001_REQUEST sid=%I64d dir=%d leg=%s vol=%.2f entry=%.5f "
               "sl=%.5f tp=%.5f risk_dist=%.5f money_per_lot=%.2f risk_pct=%.3f",
               sid,p.direction,RgLegName(s.leg),p.volume,p.entry,p.sl,
               p.tp,p.risk_distance,p.money_per_lot,risk_percent);
  }

void RgLogOrder(const long sid,const bool submitted,const int state,
                const uint request_id,const ulong ticket,const uint retcode)
  {
   PrintFormat("RG001_ORDER sid=%I64d submitted=%s state=%d request_id=%u "
               "ticket=%I64u retcode=%u",
               sid,(submitted ? "true" : "false"),state,request_id,ticket,
               retcode);
  }

void RgLogDeal(const long sid,const ulong deal,const int entry_kind,
               const double volume,const double price,const double net_profit)
  {
   PrintFormat("RG001_DEAL sid=%I64d deal=%I64u entry=%d vol=%.2f price=%.5f "
               "net=%.2f",sid,deal,entry_kind,volume,price,net_profit);
  }

void RgLogPosition(const long sid,const ulong ticket,const double volume,
                   const double open_price,const double sl,const double tp,
                   const double realized_risk_money)
  {
   PrintFormat("RG001_POSITION sid=%I64d ticket=%I64u vol=%.2f open=%.5f "
               "sl=%.5f tp=%.5f realized_risk=%.2f",
               sid,ticket,volume,open_price,sl,tp,realized_risk_money);
  }

void RgLogExit(const long sid,const string reason,const ulong ticket,
               const bool ok,const uint retcode)
  {
   PrintFormat("RG001_EXIT sid=%I64d reason=%s ticket=%I64u ok=%s retcode=%u",
               sid,reason,ticket,(ok ? "true" : "false"),retcode);
  }

void RgLogClockDiag(const int configured_offset_hours,const bool dst_rule)
  {
   const long measured=(long)TimeGMT()-(long)TimeTradeServer();
   PrintFormat("RG001_CLOCK_DIAG configured_offset_h=%d dst_us_rule=%s "
               "measured_gmt_minus_server_sec=%I64d measured_h=%.2f",
               configured_offset_hours,(dst_rule ? "true" : "false"),
               measured,(double)measured/3600.0);
  }

void RgSummary(const LswCounters &cnt,const long &leg_signals[],
               const long &leg_trades[],const int deinit_reason,
               const bool runtime_failed)
  {
   PrintFormat("RG001_SUMMARY_FLOW reason=%d failed=%s closed_bars=%I64d "
               "decisions=%I64d signals=%I64d long=%I64d short=%I64d "
               "submitted=%I64d filled=%I64d timeouts=%I64d",
               deinit_reason,(runtime_failed ? "true" : "false"),
               cnt.closed_bars,cnt.decisions,cnt.signals_seen,
               cnt.signals_long,cnt.signals_short,cnt.entries_submitted,
               cnt.entries_filled,cnt.entry_timeouts);

   PrintFormat("RG001_SUMMARY_FILTER session=%I64d rollover=%I64d flatten=%I64d "
               "spread=%I64d atr_floor=%I64d news=%I64d max_trades=%I64d "
               "streak_lock=%I64d daily_lock=%I64d dd_lock=%I64d "
               "position_open=%I64d exec_busy=%I64d bar_gap=%I64d",
               cnt.filt_session,cnt.filt_rollover,cnt.filt_flatten,
               cnt.filt_spread,cnt.filt_atr_floor,cnt.filt_news,
               cnt.filt_max_trades,cnt.filt_streak_lock,cnt.filt_daily_lock,
               cnt.filt_dd_lock,cnt.filt_position_open,cnt.filt_exec_busy,
               cnt.filt_bar_gap);

   PrintFormat("RG001_SUMMARY_EXEC entry_rej_plan=%I64d entry_rej_sizing=%I64d "
               "entry_rej_geometry=%I64d entry_rej_submit=%I64d exit_time=%I64d "
               "exit_daily=%I64d exit_friday=%I64d exit_rej=%I64d "
               "be_moves=%I64d be_rej=%I64d deals_out=%I64d deals_out_loss=%I64d",
               cnt.entry_reject_plan,cnt.entry_reject_sizing,
               cnt.entry_reject_geometry,cnt.entry_reject_submit,
               cnt.exit_time_stop,cnt.exit_daily_flat,cnt.exit_friday_flat,
               cnt.exit_reject,cnt.be_moves,cnt.be_rejects,cnt.deals_out,
               cnt.deals_out_loss);

   PrintFormat("RG001_SUMMARY_HEALTH data_fail=%I64d news_query_empty=%I64d "
               "kernel_recycles=%I64d kernel_ambiguous=%I64d",
               cnt.data_fail,cnt.news_query_empty,cnt.kernel_recycles,
               cnt.kernel_ambiguous);

   for(int s=RG_LEG_LONG;s<=RG_LEG_SHORT;s++)
      PrintFormat("RG001_SUMMARY_LEG leg=%s signals=%I64d trades=%I64d",
                  RgLegName(s),leg_signals[s],leg_trades[s]);
  }

#endif
