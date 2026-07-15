#ifndef SNR_TELEMETRY_MQH
#define SNR_TELEMETRY_MQH

string g_snrRunId = "";
string g_snrSignalLogFile = "";
string g_snrTradeLogFile = "";
string g_snrRunMetaFile = "";
string g_snrPx6ExecLogFile = "";
string g_snrPx6TradeLogFile = "";
string g_snrPvsraSrLogFile = "";
string g_snrOpportunityLogFile = "";
string g_snrRegimeLogFile = "";
string g_snrStateTelemetryLogFile = "";
string g_snrFxV2aDiagnosticLogFile = "";
string g_snrFxClassicNearMissLogFile = "";
string g_snrGoldRegimeLogFile = "";
string g_snrLastRegimeLogKey = "";
int g_snrMagic = 0;

double SNR_CurrentPipSize();
bool SNR_BuildPvsraSrFields(const double pip_size,
                            const double atr,
                            SnrPvsraSrFields &fields);
void SNR_AnnotateSourceClassicFields(const SnrContext &ctx,
                                     const int direction,
                                     SnrPvsraSrFields &fields);
void SNR_AnnotateSonicTraderState(const SnrContext &ctx,
                                  const int direction,
                                  SnrPvsraSrFields &fields);

int g_snrClosedTrades = 0;
int g_snrModifyRequests = 0;
int g_snrModifyApplied = 0;
int g_snrModifyFailed = 0;
int g_snrCloseRequests = 0;
int g_snrCloseFailed = 0;
int g_snrCloseDeals = 0;

string SNR_JsonEscape(string value)
{
   StringReplace(value, "\\", "\\\\");
   StringReplace(value, "\"", "\\\"");
   StringReplace(value, "\r", "");
   StringReplace(value, "\n", " ");
   return value;
}

string SNR_BuildRunId()
{
   MqlDateTime dt;
   TimeToStruct(TimeCurrent(), dt);
   
   MathSrand((uint)GetMicrosecondCount());
   int rand_id = MathRand();
   
   return StringFormat("%04d%02d%02d_%02d%02d%02d_M%d_R%d_%I64u",
                       dt.year, dt.mon, dt.day,
                       dt.hour, dt.min, dt.sec,
                       g_snrMagic,
                       rand_id,
                       GetMicrosecondCount());
}

int SNR_OpenAppendCsv(const string file_name)
{
   int handle = FileOpen(file_name, FILE_COMMON | FILE_READ | FILE_WRITE | FILE_CSV | FILE_ANSI, ',');
   if(handle != INVALID_HANDLE)
      FileSeek(handle, 0, SEEK_END);
   return handle;
}

string SNR_FxNearMissCsvCell(string value)
{
   StringReplace(value, "\"", "\"\"");
   return "\"" + value + "\"";
}

void SNR_FxNearMissAppend(string &line, const string value)
{
   if(line != "")
      line += ",";
   line += SNR_FxNearMissCsvCell(value);
}

string SNR_ModeReasonKey(const SnrMode mode)
{
   switch(mode)
   {
      case SNR_MODE_CLASSIC: return "classic_wave_break";
      case SNR_MODE_REENTRY: return "reentry_break";
      case SNR_MODE_SCOUT2:  return "scout2_reclaim";
      case SNR_MODE_CONTINUATION: return "continuation_pullback";
      case SNR_MODE_XAU_ACTIVE_CLASSIC: return "xau_t1_active_classic";
      case SNR_MODE_XAU_RANGE_ABSORPTION: return "xau_r1_range_absorption";
      case SNR_MODE_EUR_TREND_CLASSIC: return "eur_t1_classic";
      case SNR_MODE_EUR_ASIAN_BOX_RETEST: return "eur_b1_asian_box_retest";
      case SNR_MODE_XAU_SWEEP_RECLAIM_SCAN: return "xau_s1_sweep_reclaim_scan";
      case SNR_MODE_XAU_SWEEP_RECLAIM: return "xau_s1_sweep_reclaim";
      default:               return "blocked";
   }
}

string SNR_DecisionReasonKey(const SnrDecision &decision)
{
   if(decision.archetype == "DragonPullbackEntry")
      return "dragon_pullback_entry";
   if(decision.archetype == "EurLondonShortCleanRoute")
      return "eur_london_short_clean";
   return SNR_ModeReasonKey(decision.mode);
}

string SNR_OrderTypeName(const int direction)
{
   return (direction > 0 ? "BUY" : "SELL");
}

string SNR_WeekdayTag(const datetime server_time)
{
   MqlDateTime dt;
   TimeToStruct(server_time, dt);
   switch(dt.day_of_week)
   {
      case 1: return "Monday";
      case 2: return "Tuesday";
      case 3: return "Wednesday";
      case 4: return "Thursday";
      case 5: return "Friday";
      case 6: return "Saturday";
      default: return "Sunday";
   }
}

void SNR_InitTelemetry(const int magic)
{
   g_snrMagic = magic;
   g_snrRunId = SNR_BuildRunId();
   g_snrSignalLogFile  = StringFormat("%s_%d_Signals_%s.csv", _Symbol, magic, g_snrRunId);
   g_snrTradeLogFile   = StringFormat("%s_%d_Trades_%s.csv", _Symbol, magic, g_snrRunId);
   g_snrRunMetaFile    = StringFormat("%s_%d_RunMeta_%s.json", _Symbol, magic, g_snrRunId);
   g_snrPx6ExecLogFile = StringFormat("%s_%d_PX6_Exec_%s.csv", _Symbol, magic, g_snrRunId);
   g_snrPx6TradeLogFile= StringFormat("%s_%d_PX6_Trades_%s.csv", _Symbol, magic, g_snrRunId);
   g_snrPvsraSrLogFile = StringFormat("%s_%d_PVSRA_SR_Fields_%s.csv", _Symbol, magic, g_snrRunId);
   g_snrOpportunityLogFile = StringFormat("%s_%d_Opportunities_%s.csv", _Symbol, magic, g_snrRunId);
   g_snrRegimeLogFile = StringFormat("%s_%d_Regime_%s.csv", _Symbol, magic, g_snrRunId);
   g_snrStateTelemetryLogFile = StringFormat("%s_%d_StateTelemetry_%s.csv", _Symbol, magic, g_snrRunId);
   g_snrFxV2aDiagnosticLogFile = StringFormat("%s_%d_StateTelemetry_V2A_%s.csv", _Symbol, magic, g_snrRunId);
   g_snrFxClassicNearMissLogFile = StringFormat("%s_%d_FxClassicNearMiss_%s.csv", _Symbol, magic, g_snrRunId);
   g_snrGoldRegimeLogFile = StringFormat("%s_%d_GoldRegimeContext_%s.csv", _Symbol, magic, g_snrRunId);
   g_snrLastRegimeLogKey = "";

   g_snrClosedTrades = 0;
   g_snrModifyRequests = 0;
   g_snrModifyApplied = 0;
   g_snrModifyFailed = 0;
   g_snrCloseRequests = 0;
   g_snrCloseFailed = 0;
   g_snrCloseDeals = 0;

   if(!g_enableTelemetry)
      return;

   int handle = FileOpen(g_snrSignalLogFile, FILE_COMMON | FILE_WRITE | FILE_CSV | FILE_ANSI, ',');
   if(handle != INVALID_HANDLE)
   {
      FileWrite(handle,
                "run_id","server_ts","utc_ts","symbol","timeframe","engine_name","engine_variant",
                "archetype","setup_state","dragon_angle_class","pvsra_bias","pvsra_event",
                "level_kind","level_distance_pips","htf_bias_score","invalidate_reason",
                "session_bucket","direction","blocked_or_fired","block_reason","parent_trade_id",
                "entry_reason","risk_multiplier","wave_id","context_score","quality_score",
                "pvsra_grade","level_zone","news_distance_min","minutes_to_forced_flat",
                "spread_pips","spread_regime","dragon_slope_atr","trend_slope_atr",
                "tick_volume_pct","recent_accum_bias","body_ratio","range_atr","h1_bias",
                "h4_bias","active_layers","state_reason");
      FileClose(handle);
   }

   handle = FileOpen(g_snrTradeLogFile, FILE_COMMON | FILE_WRITE | FILE_CSV | FILE_ANSI, ',');
   if(handle != INVALID_HANDLE)
   {
      FileWrite(handle,
                "run_id","engine_name","engine_variant","entry_server_ts","entry_utc_ts",
                "exit_server_ts","exit_utc_ts","hold_minutes","entry_reason","exit_reason",
                 "direction","entry_price","exit_price","stop_loss","target_price","initial_r_points","initial_risk_account",
                 "realized_r","pnl_gross","commission","swap","fee","pnl_net","initial_volume",
                "remaining_volume","news_proximity_min","session_tag","weekday_tag","parent_trade_id",
                "close_source","is_final_close");
      FileClose(handle);
   }

   handle = FileOpen(g_snrPx6ExecLogFile, FILE_COMMON | FILE_WRITE | FILE_CSV | FILE_ANSI, ',');
   if(handle != INVALID_HANDLE)
   {
      FileWrite(handle,
                "event_time","phase","state","tag","order_type","volume","request_price","fill_price",
                "sl","tp","reason","retcode","deal","order","slippage_pts","symbol");
      FileClose(handle);
   }

   handle = FileOpen(g_snrPx6TradeLogFile, FILE_COMMON | FILE_WRITE | FILE_CSV | FILE_ANSI, ',');
   if(handle != INVALID_HANDLE)
   {
      FileWrite(handle,
                "event_time","tag","action","order_type","volume","price","sl","tp","reason","retcode",
                 "deal","order","symbol","position_id","entry_price","initial_sl","initial_tp","risk_pts","initial_risk_account",
                "close_source","deal_reason","achievedr","deal_profit","deal_commission","deal_swap",
                "deal_fee","deal_net","is_final_close");
      FileClose(handle);
   }

   handle = FileOpen(g_snrPvsraSrLogFile, FILE_COMMON | FILE_WRITE | FILE_CSV | FILE_ANSI, ',');
   if(handle != INVALID_HANDLE)
   {
      string header =
         "run_id,server_ts,utc_ts,symbol,timeframe,blocked_or_fired,block_reason,direction,entry_reason,wave_id,data_status," +
         "bar_time,bar_open,bar_high,bar_low,bar_close,bar_tick_volume,bar_real_volume,bar_spread,bar_body_pips," +
         "bar_range_pips,upper_wick_pips,lower_wick_pips,bar_direction,close_location_0_1,vol_avg_20,vol_max_20,vol_rank_20," +
         "vol_vs_avg_20,vol_vs_prev_1,vol_vs_prev_2,candidate_pva_rising_150,candidate_pva_climax_200," +
         "candidate_pva_highest_20,source_pva_avg_10,source_pva_spread_volume,source_pva_highest_spread_volume_10," +
         "source_pva_rising_150,source_pva_climax_200_or_highest_sv,source_pva_event,source_pva_grade," +
         "source_mtf_pva_status,source_mtf_pva_h4_state,source_mtf_pva_h1_state,source_mtf_pva_m15_state," +
         "source_mtf_pva_stop_volume_near_whq,source_mtf_pva_direction_agreement,source_mtf_pva_notes," +
         "source_sr_level_kind,source_sr_interaction,source_sr_rejection_side,source_sr_runway_pips,source_sr_grade," +
         "source_classic_wave_state,source_classic_wave_smoothness,source_classic_dragon_state,source_classic_dragon_expansion," +
         "source_classic_dragon_edge_distance_pips,source_h4_target_runway_pips,source_h4_target_kind," +
         "source_h4_target_price,source_h4_target_status," +
         "source_classic_trigger_state,source_classic_chase_risk,source_classic_session_runway,source_classic_run_mode_proxy," +
         "sonic_story_state,sonic_mm_mode_proxy,sonic_wave_quality,sonic_dragon_momentum,sonic_level_story," +
         "sonic_session_momentum,sonic_entry_timing_risk,sonic_trade_management_context," +
         "sonic_replay_20_close_delta_pips,sonic_replay_20_range_atr,sonic_replay_60_range_atr," +
         "sonic_replay_20_pva_count,sonic_replay_20_whq_touch_count," +
         "nearest_whole_price,nearest_half_price,nearest_quarter_price,dist_close_to_whole_pips," +
         "dist_close_to_half_pips,dist_close_to_quarter_pips,dist_high_to_whole_pips,dist_high_to_half_pips," +
         "dist_high_to_quarter_pips,dist_low_to_whole_pips,dist_low_to_half_pips,dist_low_to_quarter_pips," +
         "whole_inside_candle_range,half_inside_candle_range,quarter_inside_candle_range,whole_inside_body,half_inside_body," +
         "quarter_inside_body,whole_upper_wick_touched,whole_lower_wick_touched,half_upper_wick_touched," +
         "half_lower_wick_touched,quarter_upper_wick_touched,quarter_lower_wick_touched,whole_rejection_side," +
         "half_rejection_side,quarter_rejection_side,prior_swing_high_20,prior_swing_low_20," +
         "dist_high_to_prior_swing_high_pips,dist_low_to_prior_swing_low_pips,breaks_prior_swing_high,breaks_prior_swing_low," +
         "closes_above_prior_swing_high,closes_below_prior_swing_low,seq_5_bull_count,seq_5_bear_count," +
         "seq_5_high_volume_count,seq_5_climax_count,seq_5_net_range_atr,seq_5_close_delta_pips,seq_context_candidate";
      FileWriteString(handle, header + "\r\n");
      FileClose(handle);
   }

   if(g_enableOpportunityLogger)
   {
      handle = FileOpen(g_snrOpportunityLogFile, FILE_COMMON | FILE_WRITE | FILE_CSV | FILE_ANSI, ',');
      if(handle != INVALID_HANDLE)
      {
         FileWrite(handle,
                   "run_id","candidate_id","server_ts","utc_ts","symbol","timeframe","bar_time",
                   "variant","setup_type","direction","outcome","block_reason","wave_id",
                   "session_bucket","weekday","hour_server","spread_pips","entry_ref_price",
                   "stop_ref_price","target_rr","risk_points","dragon_slope_atr","trend_slope_atr",
                   "h1_bias","h4_bias","pvsra_bias","pvsra_event","pvsra_grade","level_zone",
                   "level_distance_pips","quality_score","context_score","classic_setup_score",
                   "reentry_setup_score","scalp_opportunity_score","narrative_id");
         FileClose(handle);
      }
   }

   if(g_enableStateTelemetry)
   {
      handle = FileOpen(g_snrStateTelemetryLogFile, FILE_COMMON | FILE_WRITE | FILE_CSV | FILE_ANSI, ',');
      if(handle != INVALID_HANDLE)
      {
         FileWrite(handle,
                   "run_id","candidate_id","server_ts","utc_ts","symbol","timeframe","bar_time",
                   "variant","setup_type","mode","direction","wave_id","score_gate_enabled",
                   "pre_score_should_trade","post_score_should_trade","min_score","score_delta",
                   "structure_score","htf_score","pvsra_score","level_score","time_safety_score",
                   "spread_news_penalty","scalp_opportunity_score","classic_setup_score",
                   "reentry_setup_score","pre_block_reason","post_block_reason",
                   "extension_from_dragon_atr","extension_from_break_atr","sr_runway_pips",
                   "retest_dragon_ok","sweep_reclaim_side","wave_smoothness","overlap_ratio",
                   "sonic_story_state","sonic_mm_mode_proxy","sonic_wave_quality","sonic_dragon_momentum",
                   "sonic_level_story","sonic_session_momentum","sonic_entry_timing_risk",
                   "sonic_trade_management_context");
         FileClose(handle);
      }
   }

   if(g_useFxChaseTrapV2ADiagnostic)
   {
      handle = FileOpen(g_snrFxV2aDiagnosticLogFile, FILE_COMMON | FILE_WRITE | FILE_CSV | FILE_ANSI, ',');
      if(handle != INVALID_HANDLE)
      {
         FileWrite(handle,
                   "run_id","candidate_id","server_ts","utc_ts","symbol","period","bar_time",
                   "direction","session_bucket","variant_tag","research_lane_tag","source_signal_state",
                   "entry_layer","old_state_gate_reason","old_late_chase_trap_reason","v2a_enabled",
                   "v2a_decision","v2a_reason_codes","v2a_final_action","order_send_attempted",
                   "order_send_result","wave_state","wave_smoothness","dragon_state","dragon_expansion",
                   "dragon_extension_atr","dragon_overlap_ratio","sr_runway_pips","sr_interaction",
                   "level_distance_pips","chase_risk","run_mode_proxy","session_runway",
                   "trend_htf_state","h1_bias","h4_bias","seq_5_close_delta_pips",
                   "seq_5_net_range_atr","source_pva_event","pvsra_event","spread_regime",
                   "minutes_to_forced_flat","planned_entry","planned_sl","planned_tp",
                   "initial_risk_points","initial_risk_pips","min_stop_check","lot_sizing_mode",
                   "fail_closed_reason");
         FileClose(handle);
      }
   }

   if(g_enableFxClassicNearMissTelemetry)
   {
      handle = FileOpen(g_snrFxClassicNearMissLogFile, FILE_COMMON | FILE_WRITE | FILE_CSV | FILE_ANSI, ',');
      if(handle != INVALID_HANDLE)
      {
         string header =
            "run_id,server_ts,utc_ts,symbol,timeframe,variant_tag,research_lane_tag," +
            "stage,mode,direction,valid,reason,archetype,setup_state,invalidate_reason," +
            "trigger_price,stop_price,target_rr,quality_score,pullback_depth_atr," +
            "session_bucket,hour_server,day_of_week,minutes_to_forced_flat,spread_pips,spread_regime," +
            "allow_long,allow_short,h1_bias,h4_bias,htf_bias_score,dragon_angle_class," +
            "dragon_slope_atr,trend_slope_atr,body_ratio,bar_range_atr," +
            "pvsra_event,pvsra_bias,pvsra_grade,source_pva_event,source_pva_grade," +
            "level_zone,level_distance_pips,source_sr_interaction,source_sr_rejection_side," +
            "source_sr_runway_pips,source_sr_grade,source_classic_wave_state," +
            "source_classic_dragon_state,source_classic_trigger_state,source_classic_chase_risk," +
            "source_classic_session_runway,source_classic_run_mode_proxy," +
            "source_h4_target_runway_pips,source_h4_target_kind,source_h4_target_status," +
            "sonic_story_state,sonic_mm_mode_proxy,sonic_wave_quality,sonic_dragon_momentum," +
            "sonic_level_story,sonic_session_momentum,sonic_entry_timing_risk," +
            "sonic_trade_management_context";
         FileWriteString(handle, header + "\r\n");
         FileClose(handle);
      }
   }

   if(g_enableGoldRegimeTelemetry)
   {
      handle = FileOpen(g_snrGoldRegimeLogFile, FILE_COMMON | FILE_WRITE | FILE_CSV | FILE_ANSI, ',');
      if(handle != INVALID_HANDLE)
      {
         string header =
            "run_id,server_ts,utc_ts,symbol,timeframe,bar_time,variant,mode,direction,outcome,entry_reason,wave_id," +
            "session_bucket,weekday,hour_server,flow_regime,flow_alignment_5d,flow_alignment_20d,atr20_pips," +
            "atr20_percentile_5d,vol_regime,delta_atr_3h,trend_bucket_3h,efficiency_3h,efficiency_bucket_3h," +
            "range_width_atr_3h,range_bucket_3h,delta_atr_8h,trend_bucket_8h,efficiency_8h,efficiency_bucket_8h," +
            "range_width_atr_8h,range_bucket_8h,delta_atr_1d,trend_bucket_1d,efficiency_1d,efficiency_bucket_1d," +
            "range_width_atr_1d,range_bucket_1d,delta_atr_5d,trend_bucket_5d,efficiency_5d,efficiency_bucket_5d," +
            "range_width_atr_5d,range_bucket_5d,delta_atr_10d,trend_bucket_10d,efficiency_10d,efficiency_bucket_10d," +
            "range_width_atr_10d,range_bucket_10d,delta_atr_20d,trend_bucket_20d,efficiency_20d,efficiency_bucket_20d," +
            "range_width_atr_20d,range_bucket_20d,price_position_20d,drawdown_from_20d_high_atr,reclaim_from_20d_low_atr," +
            "dragon_slope_atr,trend_slope_atr,h1_bias,h4_bias,pvsra_event,pvsra_grade,level_zone,block_reason";
         FileWriteString(handle, header + "\r\n");
         FileClose(handle);
      }
   }

   if(g_useRegimeRouter)
   {
      handle = FileOpen(g_snrRegimeLogFile, FILE_COMMON | FILE_WRITE | FILE_CSV | FILE_ANSI, ',');
      if(handle != INVALID_HANDLE)
      {
         FileWrite(handle,
                   "run_id","server_ts","utc_ts","symbol","timeframe","bar_time",
                   "regime_state","regime_reason","regime_bias","range_high","range_low",
                   "range_mid","range_width_atr","dragon_cross_count","dragon_slope_atr",
                   "trend_slope_atr","session_bucket","spread_pips","pvsra_event",
                   "pvsra_grade","level_zone","log_reason");
         FileClose(handle);
      }
   }
}

void SNR_LogFxClassicNearMissTelemetry(const SnrContext &ctx,
                                       const SnrSignal &signal,
                                       const string stage)
{
   if(!g_enableTelemetry || !g_enableFxClassicNearMissTelemetry)
      return;
   if(_Period != PERIOD_M15)
      return;
   if(_Symbol != "EURUSD" && _Symbol != "GBPUSD")
      return;

   int handle = SNR_OpenAppendCsv(g_snrFxClassicNearMissLogFile);
   if(handle == INVALID_HANDLE)
      return;

   SnrPvsraSrFields direction_fields;
   bool direction_fields_ok = false;
   double pip_size = SNR_CurrentPipSize();
   if(pip_size > 0.0 && ctx.atr > 0.0 &&
      SNR_BuildPvsraSrFields(pip_size, ctx.atr, direction_fields) &&
      direction_fields.data_available)
   {
      SNR_AnnotateSourceClassicFields(ctx, signal.direction, direction_fields);
      SNR_AnnotateSonicTraderState(ctx, signal.direction, direction_fields);
      direction_fields_ok = true;
   }

   string line = "";
   SNR_FxNearMissAppend(line, g_snrRunId);
   SNR_FxNearMissAppend(line, TimeToString(ctx.decision_time_server, TIME_DATE | TIME_MINUTES | TIME_SECONDS));
   SNR_FxNearMissAppend(line, TimeToString(ctx.decision_time_utc, TIME_DATE | TIME_MINUTES | TIME_SECONDS));
   SNR_FxNearMissAppend(line, _Symbol);
   SNR_FxNearMissAppend(line, EnumToString(_Period));
   SNR_FxNearMissAppend(line, SNR_CleanTesterString(g_variantTag));
   SNR_FxNearMissAppend(line, SNR_CleanTesterString(g_researchLaneTag));
   SNR_FxNearMissAppend(line, stage);
   SNR_FxNearMissAppend(line, SNR_ModeName(signal.mode));
   SNR_FxNearMissAppend(line, SNR_DirectionName(signal.direction));
   SNR_FxNearMissAppend(line, SNR_BoolLabel(signal.valid));
   SNR_FxNearMissAppend(line, signal.reason);
   SNR_FxNearMissAppend(line, signal.archetype);
   SNR_FxNearMissAppend(line, signal.setup_state);
   SNR_FxNearMissAppend(line, signal.invalidate_reason);
   SNR_FxNearMissAppend(line, DoubleToString(signal.trigger_price, _Digits));
   SNR_FxNearMissAppend(line, DoubleToString(signal.stop_price, _Digits));
   SNR_FxNearMissAppend(line, DoubleToString(signal.target_rr, 2));
   SNR_FxNearMissAppend(line, DoubleToString(signal.quality_score, 4));
   SNR_FxNearMissAppend(line, DoubleToString(signal.pullback_depth_atr, 4));
   SNR_FxNearMissAppend(line, ctx.session_bucket);
   SNR_FxNearMissAppend(line, IntegerToString(ctx.hour_server));
   SNR_FxNearMissAppend(line, IntegerToString(ctx.day_of_week));
   SNR_FxNearMissAppend(line, IntegerToString(ctx.minutes_to_forced_flat));
   SNR_FxNearMissAppend(line, DoubleToString(ctx.spread_pips, 2));
   SNR_FxNearMissAppend(line, ctx.spread_regime);
   SNR_FxNearMissAppend(line, SNR_BoolLabel(ctx.allow_long));
   SNR_FxNearMissAppend(line, SNR_BoolLabel(ctx.allow_short));
   SNR_FxNearMissAppend(line, IntegerToString(ctx.h1_bias));
   SNR_FxNearMissAppend(line, IntegerToString(ctx.h4_bias));
   SNR_FxNearMissAppend(line, IntegerToString(ctx.htf_bias_score));
   SNR_FxNearMissAppend(line, ctx.dragon_angle_class);
   SNR_FxNearMissAppend(line, DoubleToString(ctx.dragon_slope_atr, 4));
   SNR_FxNearMissAppend(line, DoubleToString(ctx.trend_slope_atr, 4));
   SNR_FxNearMissAppend(line, DoubleToString(ctx.body_ratio, 4));
   SNR_FxNearMissAppend(line, DoubleToString(ctx.bar_range_atr, 4));
   SNR_FxNearMissAppend(line, ctx.pvsra_event);
   SNR_FxNearMissAppend(line, ctx.pvsra_bias);
   SNR_FxNearMissAppend(line, IntegerToString(ctx.pvsra_grade));
   SNR_FxNearMissAppend(line, (direction_fields_ok ? direction_fields.source_pva_event : ctx.source_pva_event));
   SNR_FxNearMissAppend(line, IntegerToString(direction_fields_ok ? direction_fields.source_pva_grade : ctx.source_pva_grade));
   SNR_FxNearMissAppend(line, ctx.level_zone);
   SNR_FxNearMissAppend(line, DoubleToString(ctx.level_distance_pips, 2));
   SNR_FxNearMissAppend(line, (direction_fields_ok ? direction_fields.source_sr_interaction : ctx.source_sr_interaction));
   SNR_FxNearMissAppend(line, (direction_fields_ok ? direction_fields.source_sr_rejection_side : ctx.source_sr_rejection_side));
   SNR_FxNearMissAppend(line, DoubleToString((direction_fields_ok ? direction_fields.source_sr_runway_pips : ctx.source_sr_runway_pips), 2));
   SNR_FxNearMissAppend(line, IntegerToString(direction_fields_ok ? direction_fields.source_sr_grade : ctx.source_sr_grade));
   SNR_FxNearMissAppend(line, (direction_fields_ok ? direction_fields.source_classic_wave_state : ctx.source_classic_wave_state));
   SNR_FxNearMissAppend(line, (direction_fields_ok ? direction_fields.source_classic_dragon_state : ctx.source_classic_dragon_state));
   SNR_FxNearMissAppend(line, (direction_fields_ok ? direction_fields.source_classic_trigger_state : ctx.source_classic_trigger_state));
   SNR_FxNearMissAppend(line, (direction_fields_ok ? direction_fields.source_classic_chase_risk : ctx.source_classic_chase_risk));
   SNR_FxNearMissAppend(line, (direction_fields_ok ? direction_fields.source_classic_session_runway : ctx.source_classic_session_runway));
   SNR_FxNearMissAppend(line, (direction_fields_ok ? direction_fields.source_classic_run_mode_proxy : ctx.source_classic_run_mode_proxy));
   SNR_FxNearMissAppend(line, DoubleToString((direction_fields_ok ? direction_fields.source_h4_target_runway_pips : ctx.source_h4_target_runway_pips), 2));
   SNR_FxNearMissAppend(line, (direction_fields_ok ? direction_fields.source_h4_target_kind : ctx.source_h4_target_kind));
   SNR_FxNearMissAppend(line, (direction_fields_ok ? direction_fields.source_h4_target_status : ctx.source_h4_target_status));
   SNR_FxNearMissAppend(line, (direction_fields_ok ? direction_fields.sonic_story_state : ctx.sonic_story_state));
   SNR_FxNearMissAppend(line, (direction_fields_ok ? direction_fields.sonic_mm_mode_proxy : ctx.sonic_mm_mode_proxy));
   SNR_FxNearMissAppend(line, (direction_fields_ok ? direction_fields.sonic_wave_quality : ctx.sonic_wave_quality));
   SNR_FxNearMissAppend(line, (direction_fields_ok ? direction_fields.sonic_dragon_momentum : ctx.sonic_dragon_momentum));
   SNR_FxNearMissAppend(line, (direction_fields_ok ? direction_fields.sonic_level_story : ctx.sonic_level_story));
   SNR_FxNearMissAppend(line, (direction_fields_ok ? direction_fields.sonic_session_momentum : ctx.sonic_session_momentum));
   SNR_FxNearMissAppend(line, (direction_fields_ok ? direction_fields.sonic_entry_timing_risk : ctx.sonic_entry_timing_risk));
   SNR_FxNearMissAppend(line, (direction_fields_ok ? direction_fields.sonic_trade_management_context : ctx.sonic_trade_management_context));
   FileWriteString(handle, line + "\r\n");
   FileClose(handle);
}

void SNR_WriteRunMetaJson()
{
   if(!g_enableTelemetry)
      return;

   int handle = FileOpen(g_snrRunMetaFile, FILE_COMMON | FILE_WRITE | FILE_TXT | FILE_ANSI);
   if(handle == INVALID_HANDLE)
      return;

   ENUM_TIMEFRAMES htf_fast_tf = PERIOD_H1;
   ENUM_TIMEFRAMES htf_slow_tf = PERIOD_H4;
   SNR_SelectHtfBiasTimeframes(htf_fast_tf, htf_slow_tf);

   string json =
       "{\n" +
       StringFormat("  \"telemetry_schema_version\": \"%s\",\n", "sonic_telemetry.v3") +
       StringFormat("  \"run_id\": \"%s\",\n", SNR_JsonEscape(g_snrRunId)) +
      StringFormat("  \"magic\": %d,\n", g_snrMagic) +
      StringFormat("  \"ea_name\": \"%s\",\n", "EA_SonicR") +
      StringFormat("  \"symbol\": \"%s\",\n", _Symbol) +
      StringFormat("  \"timeframe\": \"%s\",\n", EnumToString(_Period)) +
      StringFormat("  \"variant_tag\": \"%s\",\n", SNR_JsonEscape(SNR_CleanTesterString(g_variantTag))) +
      StringFormat("  \"research_lane\": \"%s\",\n", SNR_JsonEscape(SNR_CleanTesterString(g_researchLaneTag))) +
      StringFormat("  \"calendar_source_file\": \"%s\",\n", SNR_JsonEscape(g_snrCalendarMeta.source_file)) +
      StringFormat("  \"calendar_snapshot_id\": \"%s\",\n", SNR_JsonEscape(g_snrCalendarMeta.snapshot_id)) +
      StringFormat("  \"calendar_snapshot_hash\": \"%s\",\n", SNR_JsonEscape(g_snrCalendarMeta.snapshot_hash)) +
      StringFormat("  \"snapshot_coverage_from\": \"%s\",\n", SNR_JsonEscape(g_snrCalendarMeta.snapshot_coverage_from)) +
      StringFormat("  \"snapshot_coverage_to\": \"%s\",\n", SNR_JsonEscape(g_snrCalendarMeta.snapshot_coverage_to)) +
      StringFormat("  \"included_event_classes\": \"%s\",\n", SNR_JsonEscape(g_snrCalendarMeta.included_event_classes)) +
      StringFormat("  \"source_provenance\": \"%s\",\n", SNR_JsonEscape(g_snrCalendarMeta.source_provenance)) +
      StringFormat("  \"used_legacy_fallback\": %s,\n", SNR_BoolLabel(g_snrCalendarMeta.used_legacy_fallback)) +
      StringFormat("  \"calendar_total_events\": %d,\n", g_snrCalendarMeta.total_events) +
      StringFormat("  \"classic_risk_pct\": %.3f,\n", g_classicRiskPct) +
      StringFormat("  \"second_layer_risk_pct\": %.3f,\n", g_secondLayerRiskPct) +
      StringFormat("  \"max_narrative_risk_pct\": %.3f,\n", g_maxNarrativeRiskPct) +
      StringFormat("  \"use_order_calc_risk_sizing\": %s,\n", SNR_BoolLabel(g_useOrderCalcRiskSizing)) +
      StringFormat("  \"order_calc_risk_fail_closed\": %s,\n", SNR_BoolLabel(g_orderCalcRiskFailClosed)) +
      StringFormat("  \"max_layers\": %d,\n", g_maxLayers) +
      StringFormat("  \"min_sl_pips\": %.3f,\n", g_minSLPips) +
      StringFormat("  \"scalp_min_sl_pips\": %.3f,\n", g_scalpMinSLPips) +
      StringFormat("  \"use_classic_min_sl_floor\": %s,\n", SNR_BoolLabel(g_useClassicMinSLFloor)) +
      StringFormat("  \"continuation_min_sl_pips\": %.3f,\n", g_continuationMinSLPips) +
      StringFormat("  \"preserve_primary_exits_on_scale_in\": %s,\n", SNR_BoolLabel(g_preservePrimaryExitsOnScaleIn)) +
      StringFormat("  \"modify_all_positions_after_entry\": %s,\n", SNR_BoolLabel(g_modifyAllPositionsAfterEntry)) +
      StringFormat("  \"max_classic_breakout_extension_atr\": %.3f,\n", g_maxClassicBreakoutExtensionATR) +
      StringFormat("  \"use_classic_trend\": %s,\n", SNR_BoolLabel(g_useClassicTrend)) +
      StringFormat("  \"use_classic_source_core\": %s,\n", SNR_BoolLabel(g_useClassicSourceCore)) +
      StringFormat("  \"use_classic_reversal\": %s,\n", SNR_BoolLabel(g_useClassicReversal)) +
      StringFormat("  \"use_reentry\": %s,\n", SNR_BoolLabel(g_useReentry)) +
      StringFormat("  \"use_scout_probe\": %s,\n", SNR_BoolLabel(g_useScoutProbe)) +
      StringFormat("  \"use_continuation_pullback\": %s,\n", SNR_BoolLabel(g_useContinuationPullback)) +
      StringFormat("  \"use_dragon_pullback_entry\": %s,\n", SNR_BoolLabel(g_useDragonPullbackEntry)) +
      StringFormat("  \"use_eur_london_short_clean_route\": %s,\n", SNR_BoolLabel(g_useEurLondonShortCleanRoute)) +
      StringFormat("  \"dragon_pullback_lookback_bars\": %d,\n", g_dragonPullbackLookbackBars) +
      StringFormat("  \"dragon_pullback_max_depth_atr\": %.3f,\n", g_dragonPullbackMaxDepthATR) +
      StringFormat("  \"dragon_pullback_max_extension_atr\": %.3f,\n", g_dragonPullbackMaxExtensionATR) +
      StringFormat("  \"dragon_pullback_target_rr\": %.3f,\n", g_dragonPullbackTargetRR) +
      StringFormat("  \"eur_london_short_route_target_rr\": %.3f,\n", g_eurLondonShortRouteTargetRR) +
      StringFormat("  \"use_pvsra_parity\": %s,\n", SNR_BoolLabel(g_usePvsraParity)) +
      StringFormat("  \"use_source_pva_parity_v1\": %s,\n", SNR_BoolLabel(g_useSourcePvaParityV1)) +
      StringFormat("  \"use_pvsra_sr_context\": %s,\n", SNR_BoolLabel(g_usePvsraSrContext)) +
      StringFormat("  \"use_source_sr_interaction_v1\": %s,\n", SNR_BoolLabel(g_useSourceSrInteractionV1)) +
      StringFormat("  \"sonic_trader_state_reader_v1\": \"%s\",\n", "telemetry_only") +
      StringFormat("  \"use_regime_router\": %s,\n", SNR_BoolLabel(g_useRegimeRouter)) +
      StringFormat("  \"regime_router_legacy_fallback\": %s,\n", SNR_BoolLabel(g_regimeRouterLegacyFallback)) +
      StringFormat("  \"use_xau_active_classic\": %s,\n", SNR_BoolLabel(g_useXauActiveClassic)) +
      StringFormat("  \"use_xau_range_absorption\": %s,\n", SNR_BoolLabel(g_useXauRangeAbsorption)) +
      StringFormat("  \"xau_range_absorption_allow_inner_rotation\": %s,\n", SNR_BoolLabel(g_xauRangeAbsorptionAllowInnerRotation)) +
      StringFormat("  \"xau_range_absorption_min_target_rr\": %.3f,\n", g_xauRangeAbsorptionMinTargetRR) +
      StringFormat("  \"use_xau_sweep_reclaim_scanner\": %s,\n", SNR_BoolLabel(g_useXauSweepReclaimScanner)) +
      StringFormat("  \"use_xau_sweep_reclaim_execution\": %s,\n", SNR_BoolLabel(g_useXauSweepReclaimExecution)) +
      StringFormat("  \"xau_sweep_reclaim_direction_mode\": %d,\n", g_xauSweepReclaimDirectionMode) +
      StringFormat("  \"xau_sweep_reclaim_blocked_hours\": \"%s\",\n", SNR_JsonEscape(SNR_CleanTesterString(g_xauSweepReclaimBlockedHours))) +
      StringFormat("  \"xau_sweep_reclaim_blocked_weekdays\": \"%s\",\n", SNR_JsonEscape(SNR_CleanTesterString(g_xauSweepReclaimBlockedWeekdays))) +
      StringFormat("  \"xau_sweep_reclaim_blocked_long_hours\": \"%s\",\n", SNR_JsonEscape(SNR_CleanTesterString(g_xauSweepReclaimBlockedLongHours))) +
      StringFormat("  \"xau_sweep_reclaim_blocked_short_hours\": \"%s\",\n", SNR_JsonEscape(SNR_CleanTesterString(g_xauSweepReclaimBlockedShortHours))) +
      StringFormat("  \"xau_sweep_reclaim_blocked_long_weekdays\": \"%s\",\n", SNR_JsonEscape(SNR_CleanTesterString(g_xauSweepReclaimBlockedLongWeekdays))) +
      StringFormat("  \"xau_sweep_reclaim_blocked_short_weekdays\": \"%s\",\n", SNR_JsonEscape(SNR_CleanTesterString(g_xauSweepReclaimBlockedShortWeekdays))) +
      StringFormat("  \"xau_sweep_reclaim_min_target_rr\": %.3f,\n", g_xauSweepReclaimMinTargetRR) +
      StringFormat("  \"xau_sweep_reclaim_max_target_rr\": %.3f,\n", g_xauSweepReclaimMaxTargetRR) +
      StringFormat("  \"use_xau_s1_m15_atr_impulse_filter\": %s,\n", SNR_BoolLabel(g_useXauS1M15AtrImpulseFilter)) +
      StringFormat("  \"xau_s1_m15_atr_period\": %d,\n", g_xauS1M15AtrPeriod) +
      StringFormat("  \"xau_s1_m15_atr_ema_period\": %d,\n", g_xauS1M15AtrEmaPeriod) +
      StringFormat("  \"xau_s1_m15_atr_multiplier\": %.3f,\n", g_xauS1M15AtrMultiplier) +
      StringFormat("  \"use_xau_s1_m5_dragon_anchor_compression_filter\": %s,\n", SNR_BoolLabel(g_useXauS1M5DragonAnchorCompressionFilter)) +
      StringFormat("  \"xau_s1_m5_dragon_anchor_max_compression_atr\": %.3f,\n", g_xauS1M5DragonAnchorMaxCompressionAtr) +
      StringFormat("  \"use_xau_long_bias_core_gate\": %s,\n", SNR_BoolLabel(g_useXauLongBiasCoreGate)) +
      StringFormat("  \"use_eur_trend_classic\": %s,\n", SNR_BoolLabel(g_useEurTrendClassic)) +
      StringFormat("  \"use_eur_asian_box_retest\": %s,\n", SNR_BoolLabel(g_useEurAsianBoxRetest)) +
      StringFormat("  \"scalp_lane_risk_pct\": %.3f,\n", g_scalpLaneRiskPct) +
      StringFormat("  \"range_lane_risk_pct\": %.3f,\n", g_rangeLaneRiskPct) +
      StringFormat("  \"max_scalp_trades_per_day\": %d,\n", g_maxScalpTradesPerDay) +
      StringFormat("  \"max_lane_losses_per_session\": %d,\n", g_maxLaneLossesPerSession) +
      StringFormat("  \"blocked_classic_pvsra_events\": \"%s\",\n", SNR_JsonEscape(SNR_CleanTesterString(g_blockedClassicPvsraEvents))) +
      StringFormat("  \"use_ny16_short_climax_quarter_route\": %s,\n", SNR_BoolLabel(g_useNy16ShortClimaxQuarterRoute)) +
      StringFormat("  \"use_trend_hard_gate\": %s,\n", SNR_BoolLabel(g_useTrendHardGate)) +
      StringFormat("  \"use_soft_htf_bias\": %s,\n", SNR_BoolLabel(g_useSoftHtfBias)) +
      StringFormat("  \"htf_profile_mode\": %d,\n", g_htfProfileMode) +
      StringFormat("  \"source_core_keeps_htf_gate\": %s,\n", SNR_BoolLabel(g_sourceCoreKeepsHtfGate)) +
      StringFormat("  \"htf_fast_tf\": \"%s\",\n", SNR_HtfTimeframeName(htf_fast_tf)) +
      StringFormat("  \"htf_slow_tf\": \"%s\",\n", SNR_HtfTimeframeName(htf_slow_tf)) +
      StringFormat("  \"level_grid_mode\": %d,\n", g_levelGridMode) +
      StringFormat("  \"blocked_entry_hours\": \"%s\",\n", SNR_JsonEscape(SNR_CleanTesterString(g_blockedEntryHours))) +
      StringFormat("  \"blocked_entry_weekdays\": \"%s\",\n", SNR_JsonEscape(SNR_CleanTesterString(g_blockedEntryWeekdays))) +
      StringFormat("  \"news_block_before_min\": %d,\n", g_newsBlockBeforeMin) +
      StringFormat("  \"news_block_after_min\": %d,\n", g_newsBlockAfterMin) +
      StringFormat("  \"force_flat_before_news_min\": %d,\n", g_forceFlatBeforeNewsMin) +
      StringFormat("  \"is_tester\": %d,\n", (MQLInfoInteger(MQL_TESTER) ? 1 : 0)) +
      StringFormat("  \"enable_opportunity_logger\": %s,\n", SNR_BoolLabel(g_enableOpportunityLogger)) +
      StringFormat("  \"enable_shadow_narrative\": %s,\n", SNR_BoolLabel(g_enableShadowNarrative)) +
      StringFormat("  \"enable_state_telemetry\": %s,\n", SNR_BoolLabel(g_enableStateTelemetry)) +
      StringFormat("  \"enable_fx_classic_nearmiss_telemetry\": %s,\n", SNR_BoolLabel(g_enableFxClassicNearMissTelemetry)) +
      StringFormat("  \"enable_gold_regime_telemetry\": %s,\n", SNR_BoolLabel(g_enableGoldRegimeTelemetry)) +
      StringFormat("  \"enable_source_classic_dragon_edge_distance_telemetry\": %s,\n", SNR_BoolLabel(g_enableSourceClassicDragonEdgeDistanceTelemetry)) +
      StringFormat("  \"enable_source_h4_target_runway_telemetry\": %s,\n", SNR_BoolLabel(g_enableSourceH4TargetRunwayTelemetry)) +
      StringFormat("  \"enable_fx_m15_mtf_pva_weakening_telemetry\": %s,\n", SNR_BoolLabel(g_enableFxM15MtfPvaWeakeningTelemetry)) +
      StringFormat("  \"use_opportunity_score_gate\": %s,\n", SNR_BoolLabel(g_useOpportunityScoreGate)) +
      StringFormat("  \"min_classic_opportunity_score\": %d,\n", g_minClassicOpportunityScore) +
      StringFormat("  \"min_reentry_opportunity_score\": %d,\n", g_minReentryOpportunityScore) +
      StringFormat("  \"use_xau_classic_state_quality_gate\": %s,\n", SNR_BoolLabel(g_useXauClassicStateQualityGate)) +
      StringFormat("  \"xau_classic_state_min_warnings\": %d,\n", g_xauClassicStateMinWarnings) +
      StringFormat("  \"xau_classic_min_runway_pips\": %.2f,\n", g_xauClassicMinRunwayPips) +
      StringFormat("  \"xau_classic_max_dragon_extension_atr\": %.2f,\n", g_xauClassicMaxDragonExtensionAtr) +
      StringFormat("  \"xau_classic_max_overlap_ratio\": %.3f,\n", g_xauClassicMaxOverlapRatio) +
      StringFormat("  \"xau_classic_hour15_min_runway_pips\": %.2f,\n", g_xauClassicHour15MinRunwayPips) +
      StringFormat("  \"use_fx_classic_state_quality_gate\": %s,\n", SNR_BoolLabel(g_useFxClassicStateQualityGate)) +
      StringFormat("  \"fx_classic_min_runway_pips\": %.2f,\n", g_fxClassicMinRunwayPips) +
      StringFormat("  \"fx_classic_max_dragon_extension_atr\": %.2f,\n", g_fxClassicMaxDragonExtensionAtr) +
      StringFormat("  \"fx_classic_max_overlap_ratio\": %.3f,\n", g_fxClassicMaxOverlapRatio) +
      StringFormat("  \"fx_classic_require_clean_wave\": %s,\n", SNR_BoolLabel(g_fxClassicRequireCleanWave)) +
      StringFormat("  \"fx_classic_require_htf_alignment\": %s,\n", SNR_BoolLabel(g_fxClassicRequireHtfAlignment)) +
      StringFormat("  \"fx_classic_block_flat_dragon\": %s,\n", SNR_BoolLabel(g_fxClassicBlockFlatDragon)) +
      StringFormat("  \"fx_classic_block_late_chase\": %s,\n", SNR_BoolLabel(g_fxClassicBlockLateChase)) +
      StringFormat("  \"use_fx_chase_trap_v2a_diagnostic\": %s,\n", SNR_BoolLabel(g_useFxChaseTrapV2ADiagnostic)) +
      StringFormat("  \"use_xau_trap_management_router\": %s,\n", SNR_BoolLabel(g_useXauTrapManagementRouter)) +
      StringFormat("  \"xau_trap_manage_min_score\": %.1f,\n", g_xauTrapManageMinScore) +
      StringFormat("  \"xau_trap_manage_bars\": %d,\n", g_xauTrapManageBars) +
      StringFormat("  \"xau_trap_manage_min_mfe_r\": %.2f,\n", g_xauTrapManageMinMfeR) +
      StringFormat("  \"xau_trap_manage_late_hour\": %d,\n", g_xauTrapManageLateHour) +
      StringFormat("  \"xau_trap_manage_thursday_extension_atr\": %.2f,\n", g_xauTrapManageThursdayExtensionAtr) +
      StringFormat("  \"closed_trades\": %d,\n", g_snrClosedTrades) +
      "  \"tca\": {\n" +
      StringFormat("    \"modify_requests\": %d,\n", g_snrModifyRequests) +
      StringFormat("    \"modify_applied\": %d,\n", g_snrModifyApplied) +
      StringFormat("    \"modify_failed\": %d,\n", g_snrModifyFailed) +
      StringFormat("    \"close_requests\": %d,\n", g_snrCloseRequests) +
      StringFormat("    \"close_failed\": %d,\n", g_snrCloseFailed) +
      StringFormat("    \"close_deals\": %d\n", g_snrCloseDeals) +
      "  },\n" +
      StringFormat("  \"hard_flat_server\": \"%02d:%02d\",\n", g_hardFlatHour, g_hardFlatMinute) +
      StringFormat("  \"friday_flat_server\": \"%02d:%02d\"\n", g_fridayFlatHour, g_fridayFlatMinute) +
      "}\n";

   FileWriteString(handle, json);
   FileClose(handle);
}

void SNR_LogDecision(const SnrContext &ctx, const SnrDecision &decision, const string outcome)
{
   if(!g_enableTelemetry)
      return;

   int handle = SNR_OpenAppendCsv(g_snrSignalLogFile);
   if(handle == INVALID_HANDLE)
      return;

   double mode_risk_pct = g_secondLayerRiskPct;
   if(decision.mode == SNR_MODE_CLASSIC)
      mode_risk_pct = g_classicRiskPct;
   else if(decision.mode == SNR_MODE_XAU_RANGE_ABSORPTION)
      mode_risk_pct = g_rangeLaneRiskPct;
   else if(decision.mode == SNR_MODE_XAU_ACTIVE_CLASSIC ||
           decision.mode == SNR_MODE_XAU_SWEEP_RECLAIM ||
           decision.mode == SNR_MODE_EUR_TREND_CLASSIC ||
           decision.mode == SNR_MODE_EUR_ASIAN_BOX_RETEST)
      mode_risk_pct = g_scalpLaneRiskPct;

   double risk_multiplier = (g_classicRiskPct > 0.0 ? mode_risk_pct / g_classicRiskPct : 1.0);
   if(decision.mode == SNR_MODE_BLOCKED)
      risk_multiplier = 0.0;

   FileWrite(handle,
             g_snrRunId,
             TimeToString(ctx.decision_time_server, TIME_DATE | TIME_MINUTES | TIME_SECONDS),
             TimeToString(ctx.decision_time_utc, TIME_DATE | TIME_MINUTES | TIME_SECONDS),
             _Symbol,
             EnumToString(_Period),
             "SonicR",
             SNR_ModeName(decision.mode),
             decision.archetype,
             decision.setup_state,
             ctx.dragon_angle_class,
             ctx.pvsra_bias,
             ctx.pvsra_event,
             ctx.level_zone,
             DoubleToString(ctx.level_distance_pips, 2),
             ctx.htf_bias_score,
             decision.invalidate_reason,
             ctx.session_bucket,
             SNR_DirectionName(decision.direction),
             SNR_ToUpper(outcome),
             decision.block_reason,
             "",
             SNR_DecisionReasonKey(decision),
             DoubleToString(risk_multiplier, 3),
             decision.wave_id,
             DoubleToString(decision.context_score, 3),
             DoubleToString(decision.quality_score, 3),
             decision.pvsra_grade,
             decision.level_zone,
             ctx.news_distance_min,
             ctx.minutes_to_forced_flat,
             DoubleToString(ctx.spread_pips, 2),
             ctx.spread_regime,
             DoubleToString(ctx.dragon_slope_atr, 3),
             DoubleToString(ctx.trend_slope_atr, 3),
             DoubleToString(ctx.tick_volume_percentile, 2),
             DoubleToString(ctx.recent_accum_bias, 3),
             DoubleToString(ctx.body_ratio, 3),
             DoubleToString(ctx.bar_range_atr, 3),
             ctx.h1_bias,
             ctx.h4_bias,
             ctx.active_layers,
             decision.block_reason);
   FileClose(handle);
}

void SNR_LogRegimeState(const SnrContext &ctx, const string log_reason)
{
   if(!g_enableTelemetry || !g_useRegimeRouter)
      return;

   string regime_key = SNR_RegimeName(ctx.regime_state) + "|" +
                       IntegerToString(ctx.regime_bias) + "|" +
                       ctx.regime_reason;
   if(log_reason == "REGIME_CHANGE" && regime_key == g_snrLastRegimeLogKey)
      return;
   if(log_reason == "REGIME_CHANGE")
      g_snrLastRegimeLogKey = regime_key;

   int handle = SNR_OpenAppendCsv(g_snrRegimeLogFile);
   if(handle == INVALID_HANDLE)
      return;

   datetime closed_bar = iTime(_Symbol, PERIOD_CURRENT, 1);
   if(closed_bar <= 0)
      closed_bar = ctx.decision_time_server;

   FileWrite(handle,
             g_snrRunId,
             TimeToString(ctx.decision_time_server, TIME_DATE | TIME_MINUTES | TIME_SECONDS),
             TimeToString(ctx.decision_time_utc, TIME_DATE | TIME_MINUTES | TIME_SECONDS),
             _Symbol,
             EnumToString(_Period),
             TimeToString(closed_bar, TIME_DATE | TIME_MINUTES | TIME_SECONDS),
             SNR_RegimeName(ctx.regime_state),
             ctx.regime_reason,
             SNR_DirectionName(ctx.regime_bias),
             DoubleToString(ctx.range_high, _Digits),
             DoubleToString(ctx.range_low, _Digits),
             DoubleToString(ctx.range_mid, _Digits),
             DoubleToString(ctx.range_width_atr, 3),
             ctx.dragon_cross_count,
             DoubleToString(ctx.dragon_slope_atr, 3),
             DoubleToString(ctx.trend_slope_atr, 3),
             ctx.session_bucket,
             DoubleToString(ctx.spread_pips, 2),
             ctx.pvsra_event,
             ctx.pvsra_grade,
             ctx.level_zone,
             log_reason);
   FileClose(handle);
}

void SNR_LogOpportunityRecord(const SnrOpportunityRecord &record)
{
   if(!g_enableTelemetry || !g_enableOpportunityLogger)
      return;

   int handle = SNR_OpenAppendCsv(g_snrOpportunityLogFile);
   if(handle == INVALID_HANDLE)
      return;

   FileWrite(handle,
             record.run_id,
             record.candidate_id,
             TimeToString(record.server_ts, TIME_DATE | TIME_MINUTES | TIME_SECONDS),
             TimeToString(record.utc_ts, TIME_DATE | TIME_MINUTES | TIME_SECONDS),
             record.symbol,
             record.timeframe,
             TimeToString(record.bar_time, TIME_DATE | TIME_MINUTES | TIME_SECONDS),
             record.variant,
             record.setup_type,
             record.direction,
             record.outcome,
             record.block_reason,
             record.wave_id,
             record.session_bucket,
             record.weekday,
             record.hour_server,
             DoubleToString(record.spread_pips, 2),
             DoubleToString(record.entry_ref_price, _Digits),
             DoubleToString(record.stop_ref_price, _Digits),
             DoubleToString(record.target_rr, 2),
             DoubleToString(record.risk_points, 1),
             DoubleToString(record.dragon_slope_atr, 3),
             DoubleToString(record.trend_slope_atr, 3),
             record.h1_bias,
             record.h4_bias,
             record.pvsra_bias,
             record.pvsra_event,
             record.pvsra_grade,
             record.level_zone,
             DoubleToString(record.level_distance_pips, 2),
             DoubleToString(record.quality_score, 3),
             DoubleToString(record.context_score, 3),
             DoubleToString(record.classic_setup_score, 1),
             DoubleToString(record.reentry_setup_score, 1),
             DoubleToString(record.scalp_opportunity_score, 1),
             record.narrative_id);
   FileClose(handle);
}

string SNR_PvsraSrDouble(const SnrPvsraSrFields &fields, const double value, const int digits)
{
   return (fields.data_available ? DoubleToString(value, digits) : fields.data_status);
}

string SNR_PvsraSrLong(const SnrPvsraSrFields &fields, const long value)
{
   return (fields.data_available ? IntegerToString(value) : fields.data_status);
}

string SNR_PvsraSrInt(const SnrPvsraSrFields &fields, const int value)
{
   return (fields.data_available ? IntegerToString(value) : fields.data_status);
}

string SNR_PvsraSrBool(const SnrPvsraSrFields &fields, const bool value)
{
   return (fields.data_available ? SNR_BoolLabel(value) : fields.data_status);
}

string SNR_PvsraSrTime(const SnrPvsraSrFields &fields, const datetime value)
{
   return (fields.data_available ? TimeToString(value, TIME_DATE | TIME_MINUTES | TIME_SECONDS) : fields.data_status);
}

string SNR_PvsraSrString(const SnrPvsraSrFields &fields, const string value)
{
   return (fields.data_available ? value : fields.data_status);
}

string SNR_PvsraSrCsvCell(string value)
{
   bool quote = (StringFind(value, ",") >= 0 || StringFind(value, "\"") >= 0 || StringFind(value, "\r") >= 0 || StringFind(value, "\n") >= 0);
   StringReplace(value, "\"", "\"\"");
   return (quote ? "\"" + value + "\"" : value);
}

void SNR_PvsraSrAppend(string &line, const string value)
{
   if(line != "")
      line += ",";
   line += SNR_PvsraSrCsvCell(value);
}

void SNR_LogPvsraSrFields(const SnrContext &ctx,
                          const SnrDecision &decision,
                          const string outcome,
                          const SnrPvsraSrFields &fields)
{
   if(!g_enableTelemetry)
      return;

   int handle = SNR_OpenAppendCsv(g_snrPvsraSrLogFile);
   if(handle == INVALID_HANDLE)
      return;

   string line = "";
   SNR_PvsraSrAppend(line, g_snrRunId);
   SNR_PvsraSrAppend(line, TimeToString(ctx.decision_time_server, TIME_DATE | TIME_MINUTES | TIME_SECONDS));
   SNR_PvsraSrAppend(line, TimeToString(ctx.decision_time_utc, TIME_DATE | TIME_MINUTES | TIME_SECONDS));
   SNR_PvsraSrAppend(line, _Symbol);
   SNR_PvsraSrAppend(line, EnumToString(_Period));
   SNR_PvsraSrAppend(line, SNR_ToUpper(outcome));
   SNR_PvsraSrAppend(line, decision.block_reason);
   SNR_PvsraSrAppend(line, SNR_DirectionName(decision.direction));
   SNR_PvsraSrAppend(line, SNR_DecisionReasonKey(decision));
   SNR_PvsraSrAppend(line, decision.wave_id);
   SNR_PvsraSrAppend(line, fields.data_status);
   SNR_PvsraSrAppend(line, SNR_PvsraSrTime(fields, fields.bar_time));
   SNR_PvsraSrAppend(line, SNR_PvsraSrDouble(fields, fields.bar_open, _Digits));
   SNR_PvsraSrAppend(line, SNR_PvsraSrDouble(fields, fields.bar_high, _Digits));
   SNR_PvsraSrAppend(line, SNR_PvsraSrDouble(fields, fields.bar_low, _Digits));
   SNR_PvsraSrAppend(line, SNR_PvsraSrDouble(fields, fields.bar_close, _Digits));
   SNR_PvsraSrAppend(line, SNR_PvsraSrLong(fields, fields.bar_tick_volume));
   SNR_PvsraSrAppend(line, SNR_PvsraSrLong(fields, fields.bar_real_volume));
   SNR_PvsraSrAppend(line, SNR_PvsraSrInt(fields, fields.bar_spread));
   SNR_PvsraSrAppend(line, SNR_PvsraSrDouble(fields, fields.bar_body_pips, 2));
   SNR_PvsraSrAppend(line, SNR_PvsraSrDouble(fields, fields.bar_range_pips, 2));
   SNR_PvsraSrAppend(line, SNR_PvsraSrDouble(fields, fields.upper_wick_pips, 2));
   SNR_PvsraSrAppend(line, SNR_PvsraSrDouble(fields, fields.lower_wick_pips, 2));
   SNR_PvsraSrAppend(line, SNR_PvsraSrString(fields, fields.bar_direction));
   SNR_PvsraSrAppend(line, SNR_PvsraSrDouble(fields, fields.close_location_0_1, 4));
   SNR_PvsraSrAppend(line, SNR_PvsraSrDouble(fields, fields.vol_avg_20, 2));
   SNR_PvsraSrAppend(line, SNR_PvsraSrLong(fields, fields.vol_max_20));
   SNR_PvsraSrAppend(line, SNR_PvsraSrInt(fields, fields.vol_rank_20));
   SNR_PvsraSrAppend(line, SNR_PvsraSrDouble(fields, fields.vol_vs_avg_20, 4));
   SNR_PvsraSrAppend(line, SNR_PvsraSrDouble(fields, fields.vol_vs_prev_1, 4));
   SNR_PvsraSrAppend(line, SNR_PvsraSrDouble(fields, fields.vol_vs_prev_2, 4));
   SNR_PvsraSrAppend(line, SNR_PvsraSrBool(fields, fields.candidate_pva_rising_150));
   SNR_PvsraSrAppend(line, SNR_PvsraSrBool(fields, fields.candidate_pva_climax_200));
   SNR_PvsraSrAppend(line, SNR_PvsraSrBool(fields, fields.candidate_pva_highest_20));
   SNR_PvsraSrAppend(line, SNR_PvsraSrDouble(fields, fields.source_pva_avg_10, 2));
   SNR_PvsraSrAppend(line, SNR_PvsraSrDouble(fields, fields.source_pva_spread_volume, 4));
   SNR_PvsraSrAppend(line, SNR_PvsraSrDouble(fields, fields.source_pva_highest_spread_volume_10, 4));
   SNR_PvsraSrAppend(line, SNR_PvsraSrBool(fields, fields.source_pva_rising_150));
   SNR_PvsraSrAppend(line, SNR_PvsraSrBool(fields, fields.source_pva_climax_200_or_highest_sv));
   SNR_PvsraSrAppend(line, SNR_PvsraSrString(fields, fields.source_pva_event));
   SNR_PvsraSrAppend(line, SNR_PvsraSrInt(fields, fields.source_pva_grade));
   SNR_PvsraSrAppend(line, (g_enableFxM15MtfPvaWeakeningTelemetry ?
                            SNR_PvsraSrString(fields, fields.source_mtf_pva_status) : ""));
   SNR_PvsraSrAppend(line, (g_enableFxM15MtfPvaWeakeningTelemetry ?
                            SNR_PvsraSrString(fields, fields.source_mtf_pva_h4_state) : ""));
   SNR_PvsraSrAppend(line, (g_enableFxM15MtfPvaWeakeningTelemetry ?
                            SNR_PvsraSrString(fields, fields.source_mtf_pva_h1_state) : ""));
   SNR_PvsraSrAppend(line, (g_enableFxM15MtfPvaWeakeningTelemetry ?
                            SNR_PvsraSrString(fields, fields.source_mtf_pva_m15_state) : ""));
   SNR_PvsraSrAppend(line, (g_enableFxM15MtfPvaWeakeningTelemetry ?
                            SNR_PvsraSrString(fields, fields.source_mtf_pva_stop_volume_near_whq) : ""));
   SNR_PvsraSrAppend(line, (g_enableFxM15MtfPvaWeakeningTelemetry ?
                            SNR_PvsraSrString(fields, fields.source_mtf_pva_direction_agreement) : ""));
   SNR_PvsraSrAppend(line, (g_enableFxM15MtfPvaWeakeningTelemetry ?
                            SNR_PvsraSrString(fields, fields.source_mtf_pva_notes) : ""));
   SNR_PvsraSrAppend(line, SNR_PvsraSrString(fields, fields.source_sr_level_kind));
   SNR_PvsraSrAppend(line, SNR_PvsraSrString(fields, fields.source_sr_interaction));
   SNR_PvsraSrAppend(line, SNR_PvsraSrString(fields, fields.source_sr_rejection_side));
   SNR_PvsraSrAppend(line, SNR_PvsraSrDouble(fields, fields.source_sr_runway_pips, 2));
   SNR_PvsraSrAppend(line, SNR_PvsraSrInt(fields, fields.source_sr_grade));
   SNR_PvsraSrAppend(line, SNR_PvsraSrString(fields, fields.source_classic_wave_state));
   SNR_PvsraSrAppend(line, SNR_PvsraSrDouble(fields, fields.source_classic_wave_smoothness, 4));
   SNR_PvsraSrAppend(line, SNR_PvsraSrString(fields, fields.source_classic_dragon_state));
   SNR_PvsraSrAppend(line, SNR_PvsraSrDouble(fields, fields.source_classic_dragon_expansion, 4));
   SNR_PvsraSrAppend(line, (g_enableSourceClassicDragonEdgeDistanceTelemetry ?
                            SNR_PvsraSrDouble(fields, fields.source_classic_dragon_edge_distance_pips, 2) : ""));
   SNR_PvsraSrAppend(line, (g_enableSourceH4TargetRunwayTelemetry ?
                            SNR_PvsraSrDouble(fields, fields.source_h4_target_runway_pips, 2) : ""));
   SNR_PvsraSrAppend(line, (g_enableSourceH4TargetRunwayTelemetry ?
                            SNR_PvsraSrString(fields, fields.source_h4_target_kind) : ""));
   SNR_PvsraSrAppend(line, (g_enableSourceH4TargetRunwayTelemetry ?
                            SNR_PvsraSrDouble(fields, fields.source_h4_target_price, _Digits) : ""));
   SNR_PvsraSrAppend(line, (g_enableSourceH4TargetRunwayTelemetry ?
                            SNR_PvsraSrString(fields, fields.source_h4_target_status) : ""));
   SNR_PvsraSrAppend(line, SNR_PvsraSrString(fields, fields.source_classic_trigger_state));
   SNR_PvsraSrAppend(line, SNR_PvsraSrString(fields, fields.source_classic_chase_risk));
   SNR_PvsraSrAppend(line, SNR_PvsraSrString(fields, fields.source_classic_session_runway));
   SNR_PvsraSrAppend(line, SNR_PvsraSrString(fields, fields.source_classic_run_mode_proxy));
   SNR_PvsraSrAppend(line, SNR_PvsraSrString(fields, fields.sonic_story_state));
   SNR_PvsraSrAppend(line, SNR_PvsraSrString(fields, fields.sonic_mm_mode_proxy));
   SNR_PvsraSrAppend(line, SNR_PvsraSrString(fields, fields.sonic_wave_quality));
   SNR_PvsraSrAppend(line, SNR_PvsraSrString(fields, fields.sonic_dragon_momentum));
   SNR_PvsraSrAppend(line, SNR_PvsraSrString(fields, fields.sonic_level_story));
   SNR_PvsraSrAppend(line, SNR_PvsraSrString(fields, fields.sonic_session_momentum));
   SNR_PvsraSrAppend(line, SNR_PvsraSrString(fields, fields.sonic_entry_timing_risk));
   SNR_PvsraSrAppend(line, SNR_PvsraSrString(fields, fields.sonic_trade_management_context));
   SNR_PvsraSrAppend(line, SNR_PvsraSrDouble(fields, fields.sonic_replay_20_close_delta_pips, 2));
   SNR_PvsraSrAppend(line, SNR_PvsraSrDouble(fields, fields.sonic_replay_20_range_atr, 4));
   SNR_PvsraSrAppend(line, SNR_PvsraSrDouble(fields, fields.sonic_replay_60_range_atr, 4));
   SNR_PvsraSrAppend(line, SNR_PvsraSrInt(fields, fields.sonic_replay_20_pva_count));
   SNR_PvsraSrAppend(line, SNR_PvsraSrInt(fields, fields.sonic_replay_20_whq_touch_count));
   SNR_PvsraSrAppend(line, SNR_PvsraSrDouble(fields, fields.nearest_whole_price, _Digits));
   SNR_PvsraSrAppend(line, SNR_PvsraSrDouble(fields, fields.nearest_half_price, _Digits));
   SNR_PvsraSrAppend(line, SNR_PvsraSrDouble(fields, fields.nearest_quarter_price, _Digits));
   SNR_PvsraSrAppend(line, SNR_PvsraSrDouble(fields, fields.dist_close_to_whole_pips, 2));
   SNR_PvsraSrAppend(line, SNR_PvsraSrDouble(fields, fields.dist_close_to_half_pips, 2));
   SNR_PvsraSrAppend(line, SNR_PvsraSrDouble(fields, fields.dist_close_to_quarter_pips, 2));
   SNR_PvsraSrAppend(line, SNR_PvsraSrDouble(fields, fields.dist_high_to_whole_pips, 2));
   SNR_PvsraSrAppend(line, SNR_PvsraSrDouble(fields, fields.dist_high_to_half_pips, 2));
   SNR_PvsraSrAppend(line, SNR_PvsraSrDouble(fields, fields.dist_high_to_quarter_pips, 2));
   SNR_PvsraSrAppend(line, SNR_PvsraSrDouble(fields, fields.dist_low_to_whole_pips, 2));
   SNR_PvsraSrAppend(line, SNR_PvsraSrDouble(fields, fields.dist_low_to_half_pips, 2));
   SNR_PvsraSrAppend(line, SNR_PvsraSrDouble(fields, fields.dist_low_to_quarter_pips, 2));
   SNR_PvsraSrAppend(line, SNR_PvsraSrBool(fields, fields.whole_inside_candle_range));
   SNR_PvsraSrAppend(line, SNR_PvsraSrBool(fields, fields.half_inside_candle_range));
   SNR_PvsraSrAppend(line, SNR_PvsraSrBool(fields, fields.quarter_inside_candle_range));
   SNR_PvsraSrAppend(line, SNR_PvsraSrBool(fields, fields.whole_inside_body));
   SNR_PvsraSrAppend(line, SNR_PvsraSrBool(fields, fields.half_inside_body));
   SNR_PvsraSrAppend(line, SNR_PvsraSrBool(fields, fields.quarter_inside_body));
   SNR_PvsraSrAppend(line, SNR_PvsraSrBool(fields, fields.whole_upper_wick_touched));
   SNR_PvsraSrAppend(line, SNR_PvsraSrBool(fields, fields.whole_lower_wick_touched));
   SNR_PvsraSrAppend(line, SNR_PvsraSrBool(fields, fields.half_upper_wick_touched));
   SNR_PvsraSrAppend(line, SNR_PvsraSrBool(fields, fields.half_lower_wick_touched));
   SNR_PvsraSrAppend(line, SNR_PvsraSrBool(fields, fields.quarter_upper_wick_touched));
   SNR_PvsraSrAppend(line, SNR_PvsraSrBool(fields, fields.quarter_lower_wick_touched));
   SNR_PvsraSrAppend(line, SNR_PvsraSrString(fields, fields.whole_rejection_side));
   SNR_PvsraSrAppend(line, SNR_PvsraSrString(fields, fields.half_rejection_side));
   SNR_PvsraSrAppend(line, SNR_PvsraSrString(fields, fields.quarter_rejection_side));
   SNR_PvsraSrAppend(line, SNR_PvsraSrDouble(fields, fields.prior_swing_high_20, _Digits));
   SNR_PvsraSrAppend(line, SNR_PvsraSrDouble(fields, fields.prior_swing_low_20, _Digits));
   SNR_PvsraSrAppend(line, SNR_PvsraSrDouble(fields, fields.dist_high_to_prior_swing_high_pips, 2));
   SNR_PvsraSrAppend(line, SNR_PvsraSrDouble(fields, fields.dist_low_to_prior_swing_low_pips, 2));
   SNR_PvsraSrAppend(line, SNR_PvsraSrBool(fields, fields.breaks_prior_swing_high));
   SNR_PvsraSrAppend(line, SNR_PvsraSrBool(fields, fields.breaks_prior_swing_low));
   SNR_PvsraSrAppend(line, SNR_PvsraSrBool(fields, fields.closes_above_prior_swing_high));
   SNR_PvsraSrAppend(line, SNR_PvsraSrBool(fields, fields.closes_below_prior_swing_low));
   SNR_PvsraSrAppend(line, SNR_PvsraSrInt(fields, fields.seq_5_bull_count));
   SNR_PvsraSrAppend(line, SNR_PvsraSrInt(fields, fields.seq_5_bear_count));
   SNR_PvsraSrAppend(line, SNR_PvsraSrInt(fields, fields.seq_5_high_volume_count));
   SNR_PvsraSrAppend(line, SNR_PvsraSrInt(fields, fields.seq_5_climax_count));
   SNR_PvsraSrAppend(line, SNR_PvsraSrDouble(fields, fields.seq_5_net_range_atr, 4));
   SNR_PvsraSrAppend(line, SNR_PvsraSrDouble(fields, fields.seq_5_close_delta_pips, 2));
   SNR_PvsraSrAppend(line, SNR_PvsraSrString(fields, fields.seq_context_candidate));
   FileWriteString(handle, line + "\r\n");
   FileClose(handle);
}

void SNR_LogExecEvent(const datetime server_ts,
                      const string phase,
                      const int direction,
                      const double volume,
                      const double request_price,
                      const double fill_price,
                      const double stop_loss,
                      const double take_profit,
                      const string reason,
                      const uint retcode,
                      const ulong deal_ticket,
                      const ulong order_ticket)
{
   if(!g_enableTelemetry)
      return;

   int handle = SNR_OpenAppendCsv(g_snrPx6ExecLogFile);
   if(handle == INVALID_HANDLE)
      return;

   double slippage_pts = 0.0;
   if(request_price > 0.0 && fill_price > 0.0)
      slippage_pts = (fill_price - request_price) / _Point;
   if(direction < 0)
      slippage_pts *= -1.0;

   FileWrite(handle,
             TimeToString(server_ts, TIME_DATE | TIME_MINUTES | TIME_SECONDS),
             phase,
             "DONE",
             reason,
             SNR_OrderTypeName(direction),
             DoubleToString(volume, 2),
             DoubleToString(request_price, _Digits),
             DoubleToString(fill_price, _Digits),
             DoubleToString(stop_loss, _Digits),
             DoubleToString(take_profit, _Digits),
             reason,
             (int)retcode,
             (long)deal_ticket,
             (long)order_ticket,
             DoubleToString(slippage_pts, 1),
             _Symbol);
   FileClose(handle);
}

void SNR_LogPx6TradeOpen(const SnrOpenTrade &trade)
{
   if(!g_enableTelemetry)
      return;

   int handle = SNR_OpenAppendCsv(g_snrPx6TradeLogFile);
   if(handle == INVALID_HANDLE)
      return;

   double deal_profit = 0.0;
   double deal_commission = 0.0;
   double deal_swap = 0.0;
   double deal_fee = 0.0;
   if(trade.entry_deal > 0 && HistoryDealSelect(trade.entry_deal))
   {
      deal_profit = HistoryDealGetDouble(trade.entry_deal, DEAL_PROFIT);
      deal_commission = HistoryDealGetDouble(trade.entry_deal, DEAL_COMMISSION);
      deal_swap = HistoryDealGetDouble(trade.entry_deal, DEAL_SWAP);
      deal_fee = HistoryDealGetDouble(trade.entry_deal, DEAL_FEE);
   }
   double deal_net = deal_profit + deal_commission + deal_swap + deal_fee;

   FileWrite(handle,
             TimeToString(trade.entry_server_ts, TIME_DATE | TIME_MINUTES | TIME_SECONDS),
             trade.wave_id,
             "OPEN",
             SNR_OrderTypeName(trade.direction),
             DoubleToString(trade.volume, 2),
             DoubleToString(trade.entry_price, _Digits),
             DoubleToString(trade.stop_loss, _Digits),
             DoubleToString(trade.take_profit, _Digits),
             trade.entry_reason,
             0,
             (long)trade.entry_deal,
             (long)trade.order_ticket,
             _Symbol,
             (long)trade.position_id,
             DoubleToString(trade.entry_price, _Digits),
             DoubleToString(trade.stop_loss, _Digits),
             DoubleToString(trade.take_profit, _Digits),
             DoubleToString(trade.risk_points, 1),
             DoubleToString(trade.initial_risk_account, 2),
             "",
             trade.entry_reason,
             "",
             DoubleToString(deal_profit, 2),
             DoubleToString(deal_commission, 2),
             DoubleToString(deal_swap, 2),
             DoubleToString(deal_fee, 2),
             DoubleToString(deal_net, 2),
             "0");
   FileClose(handle);
}

void SNR_LogTradeClose(const SnrOpenTrade &trade,
                       const ulong deal_ticket,
                       const ulong order_ticket,
                       const datetime close_server_ts,
                       const datetime close_utc_ts,
                       const double close_price,
                       const double volume,
                       const double deal_profit,
                       const double commission,
                       const double swap,
                       const double fee,
                       const string exit_reason,
                       const string close_source,
                       const bool is_final_close)
{
   if(!g_enableTelemetry)
      return;

   double hold_minutes = (double)(close_server_ts - trade.entry_server_ts) / 60.0;
   double realized_r = 0.0;
   if(trade.risk_points > 0.0)
   {
      double move_points = (trade.direction > 0 ? (close_price - trade.entry_price) : (trade.entry_price - close_price)) / _Point;
      realized_r = move_points / trade.risk_points;
   }

   int handle = SNR_OpenAppendCsv(g_snrTradeLogFile);
   if(handle != INVALID_HANDLE)
   {
      FileWrite(handle,
                g_snrRunId,
                "SonicR",
                SNR_ModeName(trade.mode),
                TimeToString(trade.entry_server_ts, TIME_DATE | TIME_MINUTES | TIME_SECONDS),
                TimeToString(trade.entry_utc_ts, TIME_DATE | TIME_MINUTES | TIME_SECONDS),
                TimeToString(close_server_ts, TIME_DATE | TIME_MINUTES | TIME_SECONDS),
                TimeToString(close_utc_ts, TIME_DATE | TIME_MINUTES | TIME_SECONDS),
                DoubleToString(hold_minutes, 1),
                trade.entry_reason,
                exit_reason,
                SNR_DirectionName(trade.direction),
                DoubleToString(trade.entry_price, _Digits),
                DoubleToString(close_price, _Digits),
                DoubleToString(trade.stop_loss, _Digits),
                DoubleToString(trade.take_profit, _Digits),
                DoubleToString(trade.risk_points, 1),
                DoubleToString(trade.initial_risk_account, 2),
                DoubleToString(realized_r, 4),
                DoubleToString(deal_profit, 2),
                DoubleToString(commission, 2),
                DoubleToString(swap, 2),
                DoubleToString(fee, 2),
                DoubleToString(deal_profit + commission + swap + fee, 2),
                DoubleToString(trade.volume, 2),
                DoubleToString(0.0, 2),
                trade.news_distance_min,
                trade.session_bucket,
                SNR_WeekdayTag(trade.entry_server_ts),
                (long)trade.position_id,
                close_source,
                (is_final_close ? "1" : "0"));
      FileClose(handle);
   }

   handle = SNR_OpenAppendCsv(g_snrPx6TradeLogFile);
   if(handle != INVALID_HANDLE)
   {
      FileWrite(handle,
                TimeToString(close_server_ts, TIME_DATE | TIME_MINUTES | TIME_SECONDS),
                trade.wave_id,
                (is_final_close ? "CLOSE" : "CLOSE_PARTIAL"),
                SNR_OrderTypeName(trade.direction),
                DoubleToString(volume, 2),
                DoubleToString(close_price, _Digits),
                DoubleToString(trade.stop_loss, _Digits),
                DoubleToString(trade.take_profit, _Digits),
                exit_reason,
                0,
                (long)deal_ticket,
                (long)order_ticket,
                _Symbol,
                (long)trade.position_id,
                DoubleToString(trade.entry_price, _Digits),
                DoubleToString(trade.stop_loss, _Digits),
                DoubleToString(trade.take_profit, _Digits),
                DoubleToString(trade.risk_points, 1),
                DoubleToString(trade.initial_risk_account, 2),
                close_source,
                exit_reason,
                DoubleToString(realized_r, 4),
                DoubleToString(deal_profit, 2),
                DoubleToString(commission, 2),
                DoubleToString(swap, 2),
                DoubleToString(fee, 2),
                DoubleToString(deal_profit + commission + swap + fee, 2),
                (is_final_close ? "1" : "0"));
      FileClose(handle);
   }

   g_snrClosedTrades++;
   g_snrCloseDeals++;
}

void SNR_NoteModify(const bool success)
{
   g_snrModifyRequests++;
   if(success)
      g_snrModifyApplied++;
   else
      g_snrModifyFailed++;
}

void SNR_NoteCloseRequest(const bool success)
{
   g_snrCloseRequests++;
   if(!success)
      g_snrCloseFailed++;
}

#endif
