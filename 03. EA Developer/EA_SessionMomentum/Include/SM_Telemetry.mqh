//+------------------------------------------------------------------+
//| SM_Telemetry.mqh                                                 |
//| Audit trail for SessionMomentum: signal -> request -> order ->   |
//| deal -> position -> exit, plus the OnDeinit counter block.       |
//|                                                                  |
//| Mirrors BE_Telemetry format with the SM001_ prefix and per-LEG   |
//| attribution (LDN/NY). Every line carries sid= so the whole chain |
//| joins on one id.                                                 |
//+------------------------------------------------------------------+
#ifndef SM_TELEMETRY_MQH
#define SM_TELEMETRY_MQH

#include "SM_Types.mqh"
#include "../../EA_LiquiditySweep/Include/LSW_Types.mqh"

void SmLogSignal(const long sid,const SmSignal &s,const LswClock &clk,
                 const bool verbose)
  {
   if(!verbose)
      return;
   PrintFormat("SM001_SIGNAL sid=%I64d bar=%s gmt_h=%d leg=%s dir=%d "
               "lh=%.5f ll=%.5f atr=%.5f",
               sid,TimeToString(s.ref_bar_time,TIME_DATE|TIME_MINUTES),
               clk.gmt_hour,SmLegName(s.leg),s.direction,s.level_high,
               s.level_low,s.atr);
  }

void SmLogReject(const long sid,const string stage,const string reason,
                 const bool verbose)
  {
   if(!verbose)
      return;
   PrintFormat("SM001_REJECT sid=%I64d stage=%s reason=%s",sid,stage,reason);
  }

void SmLogRequest(const long sid,const LswPlan &p,const SmSignal &s,
                  const double risk_percent)
  {
   PrintFormat("SM001_REQUEST sid=%I64d dir=%d leg=%s vol=%.2f entry=%.5f "
               "sl=%.5f tp=%.5f risk_dist=%.5f money_per_lot=%.2f risk_pct=%.3f",
               sid,p.direction,SmLegName(s.leg),p.volume,p.entry,p.sl,
               p.tp,p.risk_distance,p.money_per_lot,risk_percent);
  }

void SmLogOrder(const long sid,const bool submitted,const int state,
                const uint request_id,const ulong ticket,const uint retcode)
  {
   PrintFormat("SM001_ORDER sid=%I64d submitted=%s state=%d request_id=%u "
               "ticket=%I64u retcode=%u",
               sid,(submitted ? "true" : "false"),state,request_id,ticket,
               retcode);
  }

void SmLogDeal(const long sid,const ulong deal,const int entry_kind,
               const double volume,const double price,const double net_profit)
  {
   PrintFormat("SM001_DEAL sid=%I64d deal=%I64u entry=%d vol=%.2f price=%.5f "
               "net=%.2f",sid,deal,entry_kind,volume,price,net_profit);
  }

void SmLogPosition(const long sid,const ulong ticket,const double volume,
                   const double open_price,const double sl,const double tp,
                   const double realized_risk_money)
  {
   PrintFormat("SM001_POSITION sid=%I64d ticket=%I64u vol=%.2f open=%.5f "
               "sl=%.5f tp=%.5f realized_risk=%.2f",
               sid,ticket,volume,open_price,sl,tp,realized_risk_money);
  }

void SmLogExit(const long sid,const string reason,const ulong ticket,
               const bool ok,const uint retcode)
  {
   PrintFormat("SM001_EXIT sid=%I64d reason=%s ticket=%I64u ok=%s retcode=%u",
               sid,reason,ticket,(ok ? "true" : "false"),retcode);
  }

void SmLogClockDiag(const int configured_offset_hours,const bool dst_rule)
  {
   const long measured=(long)TimeGMT()-(long)TimeTradeServer();
   PrintFormat("SM001_CLOCK_DIAG configured_offset_h=%d dst_us_rule=%s "
               "measured_gmt_minus_server_sec=%I64d measured_h=%.2f",
               configured_offset_hours,(dst_rule ? "true" : "false"),
               measured,(double)measured/3600.0);
  }

//--- geom_* field repurpose map (shared LswCounters wire type):
//---   geom_no_level      = session level unreadable (gap/bad bars)
//---   geom_pen_small     = trigger bar inside window but level flat
void SmSummary(const LswCounters &cnt,const long &leg_signals[],
               const long &leg_trades[],const int deinit_reason,
               const bool runtime_failed)
  {
   PrintFormat("SM001_SUMMARY_FLOW reason=%d failed=%s closed_bars=%I64d "
               "decisions=%I64d signals=%I64d long=%I64d short=%I64d "
               "submitted=%I64d filled=%I64d timeouts=%I64d",
               deinit_reason,(runtime_failed ? "true" : "false"),
               cnt.closed_bars,cnt.decisions,cnt.signals_seen,
               cnt.signals_long,cnt.signals_short,cnt.entries_submitted,
               cnt.entries_filled,cnt.entry_timeouts);

   PrintFormat("SM001_SUMMARY_GEOM level_unread=%I64d level_flat=%I64d",
               cnt.geom_no_level,cnt.geom_pen_small);

   PrintFormat("SM001_SUMMARY_FILTER session=%I64d rollover=%I64d flatten=%I64d "
               "spread=%I64d atr_floor=%I64d news=%I64d max_trades=%I64d "
               "streak_lock=%I64d daily_lock=%I64d dd_lock=%I64d "
               "position_open=%I64d exec_busy=%I64d bar_gap=%I64d",
               cnt.filt_session,cnt.filt_rollover,cnt.filt_flatten,
               cnt.filt_spread,cnt.filt_atr_floor,cnt.filt_news,
               cnt.filt_max_trades,cnt.filt_streak_lock,cnt.filt_daily_lock,
               cnt.filt_dd_lock,cnt.filt_position_open,cnt.filt_exec_busy,
               cnt.filt_bar_gap);

   PrintFormat("SM001_SUMMARY_EXEC entry_rej_plan=%I64d entry_rej_sizing=%I64d "
               "entry_rej_geometry=%I64d entry_rej_submit=%I64d exit_time=%I64d "
               "exit_daily=%I64d exit_friday=%I64d exit_rej=%I64d "
               "be_moves=%I64d be_rej=%I64d deals_out=%I64d deals_out_loss=%I64d",
               cnt.entry_reject_plan,cnt.entry_reject_sizing,
               cnt.entry_reject_geometry,cnt.entry_reject_submit,
               cnt.exit_time_stop,cnt.exit_daily_flat,cnt.exit_friday_flat,
               cnt.exit_reject,cnt.be_moves,cnt.be_rejects,cnt.deals_out,
               cnt.deals_out_loss);

   PrintFormat("SM001_SUMMARY_HEALTH data_fail=%I64d news_query_empty=%I64d "
               "kernel_recycles=%I64d kernel_ambiguous=%I64d",
               cnt.data_fail,cnt.news_query_empty,cnt.kernel_recycles,
               cnt.kernel_ambiguous);

   for(int s=SM_LEG_LDN;s<=SM_LEG_NY;s++)
      PrintFormat("SM001_SUMMARY_LEG leg=%s signals=%I64d trades=%I64d",
                  SmLegName(s),leg_signals[s],leg_trades[s]);
  }

#endif
