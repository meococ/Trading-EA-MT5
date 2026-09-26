//+------------------------------------------------------------------+
//| LSW_Telemetry.mqh                                                |
//| The audit trail: signal -> request -> order -> deal -> position   |
//| -> exit, plus the OnDeinit counter block.                         |
//|                                                                  |
//| Every line carries sid= (signal id). Only one trade is ever in    |
//| flight, so sid joins the whole chain without needing the kernel's |
//| internal order comment.                                           |
//| Prices are printed with 5 decimals for every symbol so a single   |
//| parser handles XAUUSD (2 digits) and EURUSD (5) identically.      |
//+------------------------------------------------------------------+
#ifndef LSW_TELEMETRY_MQH
#define LSW_TELEMETRY_MQH

#include "LSW_Types.mqh"

void LswCountersReset(LswCounters &cnt)
  {
   ZeroMemory(cnt);
  }

void LswLogSignal(const long sid,const LswSweep &s,const LswClock &clk,const bool verbose)
  {
   if(!verbose)
      return;
   PrintFormat("LSW001_SIGNAL sid=%I64d bar=%s gmt_h=%d dir=%d fam=%s level=%.5f "
               "extreme=%.5f pen=%.5f atr=%.5f close=%.5f",
               sid,TimeToString(s.bar_time,TIME_DATE|TIME_MINUTES),clk.gmt_hour,
               s.direction,LswFamilyName(s.family),s.level,s.extreme,
               s.penetration,s.atr,s.close_price);
  }

void LswLogReject(const long sid,const string stage,const string reason,const bool verbose)
  {
   if(!verbose)
      return;
   PrintFormat("LSW001_REJECT sid=%I64d stage=%s reason=%s",sid,stage,reason);
  }

void LswLogRequest(const long sid,const LswPlan &p,const LswSweep &s,
                   const double risk_percent)
  {
   PrintFormat("LSW001_REQUEST sid=%I64d dir=%d fam=%s vol=%.2f entry=%.5f sl=%.5f "
               "tp=%.5f risk_dist=%.5f money_per_lot=%.2f risk_pct=%.3f",
               sid,p.direction,LswFamilyName(s.family),p.volume,p.entry,p.sl,p.tp,
               p.risk_distance,p.money_per_lot,risk_percent);
  }

void LswLogOrder(const long sid,const bool submitted,const int state,
                 const uint request_id,const ulong ticket,const uint retcode)
  {
   PrintFormat("LSW001_ORDER sid=%I64d submitted=%s state=%d request_id=%u "
               "ticket=%I64u retcode=%u",
               sid,(submitted ? "true" : "false"),state,request_id,ticket,retcode);
  }

void LswLogDeal(const long sid,const ulong deal,const int entry_kind,
                const double volume,const double price,const double net_profit)
  {
   PrintFormat("LSW001_DEAL sid=%I64d deal=%I64u entry=%d vol=%.2f price=%.5f net=%.2f",
               sid,deal,entry_kind,volume,price,net_profit);
  }

void LswLogPosition(const long sid,const ulong ticket,const double volume,
                    const double open_price,const double sl,const double tp,
                    const double realized_risk_money)
  {
   PrintFormat("LSW001_POSITION sid=%I64d ticket=%I64u vol=%.2f open=%.5f sl=%.5f "
               "tp=%.5f realized_risk=%.2f",
               sid,ticket,volume,open_price,sl,tp,realized_risk_money);
  }

void LswLogExit(const long sid,const string reason,const ulong ticket,
                const bool ok,const uint retcode)
  {
   PrintFormat("LSW001_EXIT sid=%I64d reason=%s ticket=%I64u ok=%s retcode=%u",
               sid,reason,ticket,(ok ? "true" : "false"),retcode);
  }

void LswLogBreakEven(const long sid,const ulong ticket,const double new_sl,
                     const bool ok,const uint retcode)
  {
   PrintFormat("LSW001_BE sid=%I64d ticket=%I64u new_sl=%.5f ok=%s retcode=%u",
               sid,ticket,new_sl,(ok ? "true" : "false"),retcode);
  }

void LswLogClockDiag(const int configured_offset_hours,const bool dst_rule)
  {
   // DIAGNOSTIC ONLY. This value never feeds a decision branch, so tester and
   // live take the identical code path (WORKFLOW.md §3). It exists so the
   // correct server offset can be read off the journal and pinned.
   const long measured=(long)TimeGMT()-(long)TimeTradeServer();
   PrintFormat("LSW001_CLOCK_DIAG configured_offset_h=%d dst_us_rule=%s "
               "measured_gmt_minus_server_sec=%I64d measured_h=%.2f",
               configured_offset_hours,(dst_rule ? "true" : "false"),
               measured,(double)measured/3600.0);
  }

void LswSummary(const LswCounters &cnt,const int deinit_reason,const bool runtime_failed)
  {
   PrintFormat("LSW001_SUMMARY_FLOW reason=%d failed=%s closed_bars=%I64d "
               "decisions=%I64d signals=%I64d long=%I64d short=%I64d "
               "submitted=%I64d filled=%I64d timeouts=%I64d",
               deinit_reason,(runtime_failed ? "true" : "false"),
               cnt.closed_bars,cnt.decisions,cnt.signals_seen,
               cnt.signals_long,cnt.signals_short,
               cnt.entries_submitted,cnt.entries_filled,cnt.entry_timeouts);

   PrintFormat("LSW001_SUMMARY_GEOM no_level=%I64d pen_small=%I64d pen_large=%I64d "
               "no_close_back=%I64d bad_approach=%I64d hold_failed=%I64d conflict=%I64d",
               cnt.geom_no_level,cnt.geom_pen_small,cnt.geom_pen_large,
               cnt.geom_no_close_back,cnt.geom_bad_approach,cnt.geom_hold_failed,
               cnt.geom_conflict);

   PrintFormat("LSW001_SUMMARY_FILTER session=%I64d rollover=%I64d flatten=%I64d "
               "spread=%I64d atr_floor=%I64d news=%I64d max_trades=%I64d "
               "streak_lock=%I64d daily_lock=%I64d dd_lock=%I64d position_open=%I64d "
               "exec_busy=%I64d bar_gap=%I64d",
               cnt.filt_session,cnt.filt_rollover,cnt.filt_flatten,
               cnt.filt_spread,cnt.filt_atr_floor,cnt.filt_news,cnt.filt_max_trades,
               cnt.filt_streak_lock,cnt.filt_daily_lock,cnt.filt_dd_lock,
               cnt.filt_position_open,cnt.filt_exec_busy,cnt.filt_bar_gap);

   PrintFormat("LSW001_SUMMARY_EXEC entry_rej_plan=%I64d entry_rej_sizing=%I64d "
               "entry_rej_geometry=%I64d entry_rej_submit=%I64d exit_time=%I64d "
               "exit_daily=%I64d exit_friday=%I64d exit_rej=%I64d be_moves=%I64d "
               "be_rej=%I64d deals_out=%I64d deals_out_loss=%I64d",
               cnt.entry_reject_plan,cnt.entry_reject_sizing,
               cnt.entry_reject_geometry,cnt.entry_reject_submit,
               cnt.exit_time_stop,cnt.exit_daily_flat,cnt.exit_friday_flat,
               cnt.exit_reject,cnt.be_moves,cnt.be_rejects,
               cnt.deals_out,cnt.deals_out_loss);

   PrintFormat("LSW001_SUMMARY_HEALTH data_fail=%I64d news_query_empty=%I64d "
               "kernel_recycles=%I64d kernel_ambiguous=%I64d",
               cnt.data_fail,cnt.news_query_empty,cnt.kernel_recycles,
               cnt.kernel_ambiguous);

   for(int f=1;f<LSW_FAMILY_COUNT;f++)
      PrintFormat("LSW001_SUMMARY_FAMILY family=%s signals=%I64d trades=%I64d",
                  LswFamilyName((LSW_FAMILY)f),cnt.signals_by_family[f],
                  cnt.trades_by_family[f]);
  }

#endif
