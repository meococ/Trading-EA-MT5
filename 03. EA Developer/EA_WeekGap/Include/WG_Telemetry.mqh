//+------------------------------------------------------------------+
//| WG_Telemetry.mqh                                                 |
//| Audit trail for WeekGap: signal -> request -> order -> deal ->   |
//| position -> exit, plus the OnDeinit counter block.               |
//| Mirrors SD_Telemetry format with the WG002_ prefix.              |
//+------------------------------------------------------------------+
#ifndef WG_TELEMETRY_MQH
#define WG_TELEMETRY_MQH

#include "../../EA_LiquiditySweep/Include/LSW_Types.mqh"

void WgLogSignal(const long sid,const datetime bar_time,const double gap_pips,
                 const bool verbose)
  {
   if(!verbose)
      return;
   PrintFormat("WG002_SIGNAL sid=%I64d bar=%s gap_pips=%.2f",
               sid,TimeToString(bar_time,TIME_DATE|TIME_MINUTES),gap_pips);
  }

void WgLogReject(const long sid,const string stage,const string reason,
                 const bool verbose)
  {
   if(!verbose)
      return;
   PrintFormat("WG002_REJECT sid=%I64d stage=%s reason=%s",sid,stage,reason);
  }

void WgLogRequest(const long sid,const LswPlan &p,const double gap_pips,
                  const double risk_percent)
  {
   PrintFormat("WG002_REQUEST sid=%I64d dir=%d vol=%.2f entry=%.5f "
               "sl=%.5f tp=%.5f risk_dist=%.5f money_per_lot=%.2f "
               "risk_pct=%.3f gap=%.2f",
               sid,p.direction,p.volume,p.entry,p.sl,p.tp,
               p.risk_distance,p.money_per_lot,risk_percent,gap_pips);
  }

void WgLogOrder(const long sid,const bool submitted,const int state,
                const uint request_id,const ulong ticket,const uint retcode)
  {
   PrintFormat("WG002_ORDER sid=%I64d submitted=%s state=%d request_id=%u "
               "ticket=%I64u retcode=%u",
               sid,(submitted ? "true" : "false"),state,request_id,ticket,
               retcode);
  }

void WgLogDeal(const long sid,const ulong deal,const int entry_kind,
               const double volume,const double price,const double net_profit)
  {
   PrintFormat("WG002_DEAL sid=%I64d deal=%I64u entry=%d vol=%.2f price=%.5f "
               "net=%.2f",sid,deal,entry_kind,volume,price,net_profit);
  }

void WgLogPosition(const long sid,const ulong ticket,const double volume,
                   const double open_price,const double sl,const double tp,
                   const double realized_risk_money)
  {
   PrintFormat("WG002_POSITION sid=%I64d ticket=%I64u vol=%.2f open=%.5f "
               "sl=%.5f tp=%.5f realized_risk=%.2f",
               sid,ticket,volume,open_price,sl,tp,realized_risk_money);
  }

void WgLogExit(const long sid,const string reason,const ulong ticket,
               const bool ok,const uint retcode)
  {
   PrintFormat("WG002_EXIT sid=%I64d reason=%s ticket=%I64u ok=%s retcode=%u",
               sid,reason,ticket,(ok ? "true" : "false"),retcode);
  }

void WgLogClockDiag(const int configured_offset_hours,const bool dst_rule)
  {
   const long measured=(long)TimeGMT()-(long)TimeTradeServer();
   PrintFormat("WG002_CLOCK_DIAG configured_offset_h=%d dst_us_rule=%s "
               "measured_gmt_minus_server_sec=%I64d measured_h=%.2f",
               configured_offset_hours,(dst_rule ? "true" : "false"),
               measured,(double)measured/3600.0);
  }

//--- geom_* field repurpose map (shared LswCounters wire type):
//---   geom_no_level      = gap legs unreadable (no week boundary found)
//---   geom_pen_small     = gap not deep enough (|gap| <= threshold)
//---   geom_pen_large     = gap wrong direction (gap >= 0)
//---   geom_bad_approach  = signal bar not Monday 01:00 (non-slot decisions)
void WgSummary(const LswCounters &cnt,const int deinit_reason,
               const bool runtime_failed)
  {
   PrintFormat("WG002_SUMMARY_FLOW reason=%d failed=%s closed_bars=%I64d "
               "decisions=%I64d signals=%I64d long=%I64d short=%I64d "
               "submitted=%I64d filled=%I64d timeouts=%I64d",
               deinit_reason,(runtime_failed ? "true" : "false"),
               cnt.closed_bars,cnt.decisions,cnt.signals_seen,
               cnt.signals_long,cnt.signals_short,cnt.entries_submitted,
               cnt.entries_filled,cnt.entry_timeouts);

   PrintFormat("WG002_SUMMARY_GEOM gap_unread=%I64d gap_shallow=%I64d "
               "gap_wrongdir=%I64d non_slot=%I64d",
               cnt.geom_no_level,cnt.geom_pen_small,cnt.geom_pen_large,
               cnt.geom_bad_approach);

   PrintFormat("WG002_SUMMARY_FILTER session=%I64d rollover=%I64d flatten=%I64d "
               "spread=%I64d atr_floor=%I64d news=%I64d max_trades=%I64d "
               "streak_lock=%I64d daily_lock=%I64d dd_lock=%I64d "
               "position_open=%I64d exec_busy=%I64d bar_gap=%I64d",
               cnt.filt_session,cnt.filt_rollover,cnt.filt_flatten,
               cnt.filt_spread,cnt.filt_atr_floor,cnt.filt_news,
               cnt.filt_max_trades,cnt.filt_streak_lock,cnt.filt_daily_lock,
               cnt.filt_dd_lock,cnt.filt_position_open,cnt.filt_exec_busy,
               cnt.filt_bar_gap);

   PrintFormat("WG002_SUMMARY_EXEC entry_rej_plan=%I64d entry_rej_sizing=%I64d "
               "entry_rej_geometry=%I64d entry_rej_submit=%I64d exit_time=%I64d "
               "exit_daily=%I64d exit_friday=%I64d exit_rej=%I64d "
               "deals_out=%I64d deals_out_loss=%I64d",
               cnt.entry_reject_plan,cnt.entry_reject_sizing,
               cnt.entry_reject_geometry,cnt.entry_reject_submit,
               cnt.exit_time_stop,cnt.exit_daily_flat,cnt.exit_friday_flat,
               cnt.exit_reject,cnt.deals_out,cnt.deals_out_loss);

   PrintFormat("WG002_SUMMARY_HEALTH data_fail=%I64d news_query_empty=%I64d "
               "kernel_recycles=%I64d kernel_ambiguous=%I64d",
               cnt.data_fail,cnt.news_query_empty,cnt.kernel_recycles,
               cnt.kernel_ambiguous);
  }

#endif
