#ifndef SNR_TYPES_MQH
#define SNR_TYPES_MQH

enum SnrMode
{
   SNR_MODE_BLOCKED = 0,
   SNR_MODE_CLASSIC = 1,
   SNR_MODE_REENTRY = 2,
   SNR_MODE_SCOUT2  = 3,
   SNR_MODE_CONTINUATION = 4,
   SNR_MODE_XAU_ACTIVE_CLASSIC = 5,
   SNR_MODE_XAU_RANGE_ABSORPTION = 6,
   SNR_MODE_EUR_TREND_CLASSIC = 7,
   SNR_MODE_EUR_ASIAN_BOX_RETEST = 8,
   SNR_MODE_XAU_SWEEP_RECLAIM_SCAN = 9,
   SNR_MODE_XAU_SWEEP_RECLAIM = 10
};

enum SnrDirection
{
   SNR_DIR_SHORT = -1,
   SNR_DIR_NONE  = 0,
   SNR_DIR_LONG  = 1
};

enum SnrRegimeState
{
   SNR_REGIME_UNKNOWN = 0,
   SNR_REGIME_TREND = 1,
   SNR_REGIME_RANGE = 2,
   SNR_REGIME_TRANSITION = 3,
   SNR_REGIME_TRENDING_STRONG = 4,
   SNR_REGIME_SIDEWAY_NARROW = 5,
   SNR_REGIME_SIDEWAY_WIDE = 6
};

enum SnrShadowNarrativeState
{
   SNR_SHADOW_OBSERVE = 0,
   SNR_SHADOW_ARM = 1,
   SNR_SHADOW_TRIGGER = 2,
   SNR_SHADOW_MANAGE = 3,
   SNR_SHADOW_INVALIDATE = 4
};

struct SnrCalendarMeta
{
   bool   loaded;
   bool   used_legacy_fallback;
   string snapshot_id;
   string snapshot_hash;
   string snapshot_coverage_from;
   string snapshot_coverage_to;
   string included_event_classes;
   string source_provenance;
   string source_file;
   int    total_events;
};

struct SnrNewsEvent
{
   string   event_id;
   datetime utc_time;
   string   event_class;
   string   currency;
   string   title;
};

struct SnrPvsraSrFields
{
   bool     data_available;
   string   data_status;
   datetime bar_time;
   double   bar_open;
   double   bar_high;
   double   bar_low;
   double   bar_close;
   long     bar_tick_volume;
   long     bar_real_volume;
   int      bar_spread;
   double   bar_body_pips;
   double   bar_range_pips;
   double   upper_wick_pips;
   double   lower_wick_pips;
   string   bar_direction;
   double   close_location_0_1;
   double   vol_avg_20;
   long     vol_max_20;
   int      vol_rank_20;
   double   vol_vs_avg_20;
   double   vol_vs_prev_1;
   double   vol_vs_prev_2;
   bool     candidate_pva_rising_150;
   bool     candidate_pva_climax_200;
   bool     candidate_pva_highest_20;
   double   source_pva_avg_10;
   double   source_pva_spread_volume;
   double   source_pva_highest_spread_volume_10;
   bool     source_pva_rising_150;
   bool     source_pva_climax_200_or_highest_sv;
   string   source_pva_event;
   int      source_pva_grade;
   string   source_sr_level_kind;
   string   source_sr_interaction;
   string   source_sr_rejection_side;
   double   source_sr_runway_pips;
   int      source_sr_grade;
   string   source_classic_wave_state;
   double   source_classic_wave_smoothness;
   string   source_classic_dragon_state;
   double   source_classic_dragon_expansion;
   string   source_classic_trigger_state;
   string   source_classic_chase_risk;
   string   source_classic_session_runway;
   string   source_classic_run_mode_proxy;
   string   sonic_story_state;
   string   sonic_mm_mode_proxy;
   string   sonic_wave_quality;
   string   sonic_dragon_momentum;
   string   sonic_level_story;
   string   sonic_session_momentum;
   string   sonic_entry_timing_risk;
   string   sonic_trade_management_context;
   double   sonic_replay_20_close_delta_pips;
   double   sonic_replay_20_range_atr;
   double   sonic_replay_60_range_atr;
   int      sonic_replay_20_pva_count;
   int      sonic_replay_20_whq_touch_count;
   double   nearest_whole_price;
   double   nearest_half_price;
   double   nearest_quarter_price;
   double   dist_close_to_whole_pips;
   double   dist_close_to_half_pips;
   double   dist_close_to_quarter_pips;
   double   dist_high_to_whole_pips;
   double   dist_high_to_half_pips;
   double   dist_high_to_quarter_pips;
   double   dist_low_to_whole_pips;
   double   dist_low_to_half_pips;
   double   dist_low_to_quarter_pips;
   bool     whole_inside_candle_range;
   bool     half_inside_candle_range;
   bool     quarter_inside_candle_range;
   bool     whole_inside_body;
   bool     half_inside_body;
   bool     quarter_inside_body;
   bool     whole_upper_wick_touched;
   bool     whole_lower_wick_touched;
   bool     half_upper_wick_touched;
   bool     half_lower_wick_touched;
   bool     quarter_upper_wick_touched;
   bool     quarter_lower_wick_touched;
   string   whole_rejection_side;
   string   half_rejection_side;
   string   quarter_rejection_side;
   double   prior_swing_high_20;
   double   prior_swing_low_20;
   double   dist_high_to_prior_swing_high_pips;
   double   dist_low_to_prior_swing_low_pips;
   bool     breaks_prior_swing_high;
   bool     breaks_prior_swing_low;
   bool     closes_above_prior_swing_high;
   bool     closes_below_prior_swing_low;
   int      seq_5_bull_count;
   int      seq_5_bear_count;
   int      seq_5_high_volume_count;
   int      seq_5_climax_count;
   double   seq_5_net_range_atr;
   double   seq_5_close_delta_pips;
   string   seq_context_candidate;
   
   // H4 Target Runway Telemetry
   double   source_h4_target_runway_pips;
   string   source_h4_target_kind;
   double   source_h4_target_price;
   string   source_h4_target_status;
   
   // MTF PVA Weakening Telemetry
   string   source_mtf_pva_status;
   string   source_mtf_pva_h4_state;
   string   source_mtf_pva_h1_state;
   string   source_mtf_pva_m15_state;
   string   source_mtf_pva_stop_volume_near_whq;
   string   source_mtf_pva_direction_agreement;
   string   source_mtf_pva_notes;
   
   double   source_classic_dragon_edge_distance_pips;
};

struct SnrContext
{
   datetime decision_time_server;
   datetime decision_time_utc;
   string   session_bucket;
   int      minutes_to_forced_flat;
   int      news_distance_min;
   bool     entry_blocked;
   bool     force_flat_now;
   string   block_reason;
   double   spread_pips;
   string   spread_regime;
   double   dragon_high;
   double   dragon_mid;
   double   dragon_low;
   double   trend;
   double   atr;
   double   dragon_slope_atr;
   double   trend_slope_atr;
   SnrRegimeState regime_state;
   string   regime_reason;
   int      regime_bias;
   double   range_high;
   double   range_low;
   double   range_mid;
   double   range_width_atr;
   int      dragon_cross_count;
   string   dragon_angle_class;
   int      h1_bias;
   int      h4_bias;
   int      htf_bias_score;
   double   body_ratio;
   double   bar_range_atr;
   double   tick_volume_percentile;
   double   recent_accum_bias;
   string   level_zone;
   double   level_distance_pips;
   int      pvsra_grade;
   string   pvsra_bias;
   string   pvsra_event;
   string   source_pva_event;
   int      source_pva_grade;
   string   source_sr_level_kind;
   string   source_sr_interaction;
   string   source_sr_rejection_side;
   double   source_sr_runway_pips;
   int      source_sr_grade;
   string   source_classic_wave_state;
   double   source_classic_wave_smoothness;
   string   source_classic_dragon_state;
   double   source_classic_dragon_expansion;
   string   source_classic_trigger_state;
   string   source_classic_chase_risk;
   string   source_classic_session_runway;
   string   source_classic_run_mode_proxy;
   string   sonic_story_state;
   string   sonic_mm_mode_proxy;
   string   sonic_wave_quality;
   string   sonic_dragon_momentum;
   string   sonic_level_story;
   string   sonic_session_momentum;
   string   sonic_entry_timing_risk;
   string   sonic_trade_management_context;
   double   context_score;
   bool     allow_long;
   bool     allow_short;
   int      day_of_week;
   int      hour_server;
   int      active_layers;
   int      narrative_direction;
   
   // H4 Target Runway Context
   double   source_h4_target_runway_pips;
   string   source_h4_target_kind;
   double   source_h4_target_price;
   string   source_h4_target_status;
   
   // MTF PVA Weakening Context
   string   source_mtf_pva_status;
   string   source_mtf_pva_h4_state;
   string   source_mtf_pva_h1_state;
   string   source_mtf_pva_m15_state;
   string   source_mtf_pva_stop_volume_near_whq;
   string   source_mtf_pva_direction_agreement;
   string   source_mtf_pva_notes;
   
   // SMC structure
   double   market_structure_low;
   double   market_structure_high;
   double   dragon_dynamic_expansion_roc;
   bool     liquidity_sweep_active;
   int      liquidity_sweep_direction;
   
   double   source_classic_dragon_edge_distance_pips;
   double   bollinger_keltner_ratio;
   bool     keltner_squeeze;
};

struct SnrSignal
{
   bool     valid;
   SnrMode  mode;
   int      direction;
   string   reason;
   string   wave_id;
   string   archetype;
   string   setup_state;
   string   invalidate_reason;
   double   trigger_price;
   double   stop_price;
   double   target_rr;
   double   quality_score;
   double   pullback_depth_atr;
   
   // Fx Chase Trap V2A Diagnostic
   bool     fx_v2a_evaluated;
   string   fx_v2a_old_state_gate_reason;
   string   fx_v2a_old_late_chase_trap_reason;
   string   fx_v2a_decision;
   string   fx_v2a_reason_codes;
   string   fx_v2a_final_action;
};

struct SnrDecision
{
   bool     should_trade;
   SnrMode  mode;
   int      direction;
   string   block_reason;
   string   wave_id;
   string   archetype;
   string   setup_state;
   string   invalidate_reason;
   double   context_score;
   int      pvsra_grade;
   string   level_zone;
   double   stop_price;
   double   target_rr;
   double   quality_score;
   double   pullback_depth_atr;
   
   // Fx Chase Trap V2A Diagnostic
   bool     fx_v2a_evaluated;
   string   fx_v2a_old_state_gate_reason;
   string   fx_v2a_old_late_chase_trap_reason;
   string   fx_v2a_decision;
   string   fx_v2a_reason_codes;
   string   fx_v2a_final_action;
};

struct SnrNarrative
{
   bool     active;
   bool     classic_seeded;
   int      direction;
   int      layers_opened;
   datetime seeded_at;
   datetime last_entry_time;
   double   last_entry_price;
   double   anchor_stop;
   double   anchor_target;
   string   wave_id;
};

struct SnrOpenTrade
{
   bool     active;
   ulong    position_id;
   ulong    entry_deal;
   ulong    order_ticket;
   datetime entry_server_ts;
   datetime entry_utc_ts;
   int      direction;
   SnrMode  mode;
   string   wave_id;
   string   entry_reason;
   string   archetype;
   string   level_zone;
   string   session_bucket;
   int      news_distance_min;
   int      pvsra_grade;
   double   context_score;
   double   quality_score;
   double   volume;
   double   entry_price;
   double   stop_loss;
   double   take_profit;
   double   risk_points;
   double   initial_risk_account;
   double   max_favorable_r;
   bool     trap_manage;
   int      trap_manage_bars;
   double   trap_manage_min_mfe_r;
   string   pending_close_reason;
   
   // Fx Chase Trap V2A Diagnostic & modify tracking
   bool     fx_v2a_evaluated;
   string   fx_v2a_old_state_gate_reason;
   string   fx_v2a_old_late_chase_trap_reason;
   string   fx_v2a_decision;
   string   fx_v2a_reason_codes;
   string   fx_v2a_final_action;
   datetime last_modify_time;
};

struct SnrClassicArm
{
   bool     active;
   int      direction;
   datetime armed_at;
   datetime expires_at;
   string   wave_id;
   string   archetype;
   string   setup_state;
   string   level_zone;
   int      pvsra_grade;
   double   context_score;
   double   quality_score;
   double   pullback_depth_atr;
   double   trigger_price;
   double   stop_price;
   double   target_rr;
};

struct SnrShadowNarrative
{
   bool     active;
   int      direction;
   SnrShadowNarrativeState state;
   datetime seeded_at;
   datetime last_seen_at;
   datetime expires_at;
   string   narrative_id;
   string   wave_id;
   string   invalidation_reason;
   double   classic_setup_score;
   double   reentry_setup_score;
   int      trigger_count;
};

struct SnrOpportunityRecord
{
   string   run_id;
   string   candidate_id;
   datetime server_ts;
   datetime utc_ts;
   string   symbol;
   string   timeframe;
   datetime bar_time;
   string   variant;
   string   setup_type;
   string   direction;
   string   outcome;
   string   block_reason;
   string   wave_id;
   string   session_bucket;
   string   weekday;
   int      hour_server;
   double   spread_pips;
   double   entry_ref_price;
   double   stop_ref_price;
   double   target_rr;
   double   risk_points;
   double   dragon_slope_atr;
   double   trend_slope_atr;
   int      h1_bias;
   int      h4_bias;
   string   pvsra_bias;
   string   pvsra_event;
   int      pvsra_grade;
   string   level_zone;
   double   level_distance_pips;
   double   quality_score;
   double   context_score;
   double   classic_setup_score;
   double   reentry_setup_score;
   double   scalp_opportunity_score;
   string   narrative_id;
};

void SNR_ResetNarrative(SnrNarrative &narrative)
{
   narrative.active = false;
   narrative.classic_seeded = false;
   narrative.direction = SNR_DIR_NONE;
   narrative.layers_opened = 0;
   narrative.seeded_at = 0;
   narrative.last_entry_time = 0;
   narrative.last_entry_price = 0.0;
   narrative.anchor_stop = 0.0;
   narrative.anchor_target = 0.0;
   narrative.wave_id = "";
}

void SNR_ResetClassicArm(SnrClassicArm &arm)
{
   arm.active = false;
   arm.direction = SNR_DIR_NONE;
   arm.armed_at = 0;
   arm.expires_at = 0;
   arm.wave_id = "";
   arm.archetype = "";
   arm.setup_state = "";
   arm.level_zone = "";
   arm.pvsra_grade = 0;
   arm.context_score = 0.0;
   arm.quality_score = -9999.0;
   arm.pullback_depth_atr = 0.0;
   arm.trigger_price = 0.0;
   arm.stop_price = 0.0;
   arm.target_rr = 0.0;
}

string SNR_ModeName(const SnrMode mode)
{
   switch(mode)
   {
      case SNR_MODE_CLASSIC: return "CLASSIC";
      case SNR_MODE_REENTRY: return "REENTRY";
      case SNR_MODE_SCOUT2:  return "SCOUT2";
      case SNR_MODE_CONTINUATION: return "CONTINUATION";
      case SNR_MODE_XAU_ACTIVE_CLASSIC: return "XAU_T1_ACTIVE_CLASSIC";
      case SNR_MODE_XAU_RANGE_ABSORPTION: return "XAU_R1_RANGE_ABSORPTION";
      case SNR_MODE_EUR_TREND_CLASSIC: return "EUR_T1_CLASSIC";
      case SNR_MODE_EUR_ASIAN_BOX_RETEST: return "EUR_B1_ASIAN_BOX_RETEST";
      case SNR_MODE_XAU_SWEEP_RECLAIM_SCAN: return "XAU_S1_SWEEP_RECLAIM_SCAN";
      case SNR_MODE_XAU_SWEEP_RECLAIM: return "XAU_S1_SWEEP_RECLAIM";
      default:               return "BLOCKED";
   }
}

string SNR_RegimeName(const SnrRegimeState state)
{
   switch(state)
   {
      case SNR_REGIME_TREND:      return "TREND";
      case SNR_REGIME_RANGE:      return "RANGE";
      case SNR_REGIME_TRANSITION: return "TRANSITION";
      case SNR_REGIME_TRENDING_STRONG: return "TRENDING_STRONG";
      case SNR_REGIME_SIDEWAY_NARROW: return "SIDEWAY_NARROW";
      case SNR_REGIME_SIDEWAY_WIDE: return "SIDEWAY_WIDE";
      default:                    return "UNKNOWN";
   }
}

string SNR_DirectionName(const int direction)
{
   if(direction > 0)
      return "LONG";
   if(direction < 0)
      return "SHORT";
   return "NONE";
}

string SNR_BoolLabel(const bool value)
{
   return value ? "true" : "false";
}

double SNR_Clamp(const double value, const double min_value, const double max_value)
{
   return MathMax(min_value, MathMin(max_value, value));
}

double SNR_AbsMax(const double a, const double b)
{
   return MathAbs(a) > MathAbs(b) ? a : b;
}

void SNR_ResetFxChaseTrapV2ADiagnostic(SnrDecision &decision)
{
   decision.fx_v2a_evaluated = false;
   decision.fx_v2a_old_state_gate_reason = "";
   decision.fx_v2a_old_late_chase_trap_reason = "";
   decision.fx_v2a_decision = "";
   decision.fx_v2a_reason_codes = "";
   decision.fx_v2a_final_action = "";
}

void SNR_ResetFxChaseTrapV2ADiagnostic(SnrSignal &signal)
{
   signal.fx_v2a_evaluated = false;
   signal.fx_v2a_old_state_gate_reason = "";
   signal.fx_v2a_old_late_chase_trap_reason = "";
   signal.fx_v2a_decision = "";
   signal.fx_v2a_reason_codes = "";
   signal.fx_v2a_final_action = "";
}

void SNR_ResetFxChaseTrapV2ADiagnostic(SnrOpenTrade &trade)
{
   trade.fx_v2a_evaluated = false;
   trade.fx_v2a_old_state_gate_reason = "";
   trade.fx_v2a_old_late_chase_trap_reason = "";
   trade.fx_v2a_decision = "";
   trade.fx_v2a_reason_codes = "";
   trade.fx_v2a_final_action = "";
   trade.last_modify_time = 0;
}

#endif
