#ifndef SNR_OPPORTUNITY_MQH
#define SNR_OPPORTUNITY_MQH

void SNR_ResetShadowNarrative(SnrShadowNarrative &shadow)
{
   shadow.active = false;
   shadow.direction = SNR_DIR_NONE;
   shadow.state = SNR_SHADOW_OBSERVE;
   shadow.seeded_at = 0;
   shadow.last_seen_at = 0;
   shadow.expires_at = 0;
   shadow.narrative_id = "";
   shadow.wave_id = "";
   shadow.invalidation_reason = "";
   shadow.classic_setup_score = 0.0;
   shadow.reentry_setup_score = 0.0;
   shadow.trigger_count = 0;
}

string SNR_ShadowStateName(const SnrShadowNarrativeState state)
{
   switch(state)
   {
      case SNR_SHADOW_ARM:        return "ARM";
      case SNR_SHADOW_TRIGGER:    return "TRIGGER";
      case SNR_SHADOW_MANAGE:     return "MANAGE";
      case SNR_SHADOW_INVALIDATE: return "INVALIDATE";
      default:                    return "OBSERVE";
   }
}

datetime SNR_OpportunityClosedBarTime(const SnrContext &ctx)
{
   datetime closed_bar = iTime(_Symbol, PERIOD_CURRENT, 1);
   return (closed_bar > 0 ? closed_bar : ctx.decision_time_server);
}

string SNR_OpportunitySetupType(const SnrMode mode, const SnrContext &ctx)
{
   if(mode == SNR_MODE_REENTRY)
      return "REENTRY";
   if(mode == SNR_MODE_SCOUT2)
      return "SCOUT2";
   if(mode == SNR_MODE_CONTINUATION)
      return "CONTINUATION";
   if(mode == SNR_MODE_XAU_ACTIVE_CLASSIC)
      return "XAU_T1_ACTIVE_CLASSIC";
   if(mode == SNR_MODE_XAU_RANGE_ABSORPTION)
      return "XAU_R1_RANGE_ABSORPTION";
   if(mode == SNR_MODE_XAU_SWEEP_RECLAIM_SCAN)
      return "XAU_S1_SWEEP_RECLAIM_SCAN";
   if(mode == SNR_MODE_XAU_SWEEP_RECLAIM)
      return "XAU_S1_SWEEP_RECLAIM";
   if(mode == SNR_MODE_EUR_TREND_CLASSIC)
      return "EUR_T1_CLASSIC";
   if(mode == SNR_MODE_EUR_ASIAN_BOX_RETEST)
      return "EUR_B1_ASIAN_BOX_RETEST";
   if(mode == SNR_MODE_CLASSIC)
      return "CLASSIC";
   if(g_useRegimeRouter)
      return "REGIME_ROUTER";
   return (ctx.active_layers > 0 ? "REENTRY" : "CLASSIC");
}

string SNR_OpportunityOutcomeName(const string outcome)
{
   string upper = SNR_ToUpper(outcome);
   if(upper == "ORDER_REJECT")
      return "ORDER_REJECTED";
   if(upper == "FIRED" || upper == "BLOCKED" || upper == "SCANNER_ONLY")
      return upper;
   return upper;
}

string SNR_OpportunityBlockReason(const SnrContext &ctx, const SnrDecision &decision)
{
   if(decision.block_reason != "")
      return decision.block_reason;
   if(ctx.block_reason != "")
      return ctx.block_reason;
   if(ctx.force_flat_now)
      return "FORCE_FLAT_WINDOW";
   if(ctx.entry_blocked)
      return "ENTRY_BLOCKED";
   return "";
}

bool SNR_OpportunityHardBlocked(const SnrContext &ctx, const string block_reason)
{
   if(ctx.force_flat_now || ctx.entry_blocked)
      return true;
   string reason = SNR_ToUpper(block_reason);
   return (reason == "CALENDAR_UNAVAILABLE" ||
           reason == "NEWS_BLOCK" ||
           reason == "NEWS_FORCE_FLAT" ||
           reason == "FORCE_FLAT_WINDOW" ||
           reason == "OFF_SESSION" ||
           reason == "WEEKEND" ||
           reason == "FRIDAY_ENTRY_BLOCK" ||
           reason == "SPREAD_HARD" ||
           reason == "DAILY_TRADE_LIMIT" ||
           reason == "RISK_BUDGET_BLOCK" ||
           reason == "EQUITY_DD_LOCK" ||
           reason == "DAILY_LOSS_LOCK" ||
           reason == "STALE_NARRATIVE");
}

double SNR_OpportunityHtfScore(const SnrContext &ctx, const int direction)
{
   int aligned = 0;
   if(direction > 0)
   {
      if(ctx.h1_bias > 0) aligned++;
      if(ctx.h4_bias > 0) aligned++;
      if(ctx.h1_bias < 0) aligned--;
      if(ctx.h4_bias < 0) aligned--;
   }
   else
   {
      if(ctx.h1_bias < 0) aligned++;
      if(ctx.h4_bias < 0) aligned++;
      if(ctx.h1_bias > 0) aligned--;
      if(ctx.h4_bias > 0) aligned--;
   }

   if(aligned >= 2)
      return 20.0;
   if(aligned == 1)
      return 14.0;
   if(aligned == 0)
      return 8.0;
   if(aligned == -1)
      return 3.0;
   return 0.0;
}

double SNR_OpportunityStructureScore(const SnrContext &ctx, const int direction)
{
   double score = 0.0;
   bool dragon_aligned = (direction > 0 ? ctx.dragon_slope_atr > 0.0 : ctx.dragon_slope_atr < 0.0);
   bool trend_aligned = (direction > 0 ? ctx.trend_slope_atr > 0.0 : ctx.trend_slope_atr < 0.0);
   if(dragon_aligned)
      score += MathMin(14.0, MathAbs(ctx.dragon_slope_atr) * 28.0);
   if(trend_aligned)
      score += MathMin(8.0, MathAbs(ctx.trend_slope_atr) * 18.0);
   if((direction > 0 && ctx.allow_long) || (direction < 0 && ctx.allow_short))
      score += 7.0;
   score += MathMin(4.0, ctx.body_ratio * 5.0);
   score += MathMin(2.0, ctx.bar_range_atr * 2.0);
   return SNR_Clamp(score, 0.0, 35.0);
}

double SNR_OpportunityPvsraScore(const SnrContext &ctx, const int direction)
{
   double score = MathMin(10.0, (double)ctx.pvsra_grade * 2.0);
   if(ctx.pvsra_event == "CLIMAX")
      score += 3.0;
   else if(ctx.pvsra_event == "RISING_ACTIVITY")
      score += 2.0;
   else if(ctx.pvsra_event == "WIDE_BODY")
      score += 1.0;

   if(direction > 0 && ctx.pvsra_bias == "BULLISH")
      score += 2.0;
   if(direction < 0 && ctx.pvsra_bias == "BEARISH")
      score += 2.0;
   return SNR_Clamp(score, 0.0, 15.0);
}

double SNR_OpportunityLevelScore(const SnrContext &ctx)
{
   if(ctx.level_zone == "NONE")
      return 0.0;
   double score = 6.0;
   if(ctx.level_zone == "WHOLE")
      score += 4.0;
   else if(ctx.level_zone == "HALF")
      score += 3.0;
   else
      score += 2.0;
   if(ctx.level_distance_pips <= g_halfLevelRadiusPips)
      score += 1.0;
   return SNR_Clamp(score, 0.0, 10.0);
}

double SNR_OpportunityTimeSafetyScore(const SnrContext &ctx)
{
   double score = 0.0;
   if(ctx.session_bucket == "LONDON" || ctx.session_bucket == "NEWYORK")
      score += 8.0;
   else if(ctx.session_bucket != "OFF")
      score += 4.0;
   if(ctx.minutes_to_forced_flat >= g_minMinutesToNewTrade * 2)
      score += 5.0;
   else if(ctx.minutes_to_forced_flat >= g_minMinutesToNewTrade)
      score += 3.0;
   if(ctx.day_of_week >= 1 && ctx.day_of_week <= 4)
      score += 2.0;
   return SNR_Clamp(score, 0.0, 15.0);
}

double SNR_OpportunityPenalty(const SnrContext &ctx, const string block_reason)
{
   double penalty = 0.0;
   if(ctx.spread_regime == "HARD")
      penalty += 18.0;
   else if(ctx.spread_regime == "ELEVATED")
      penalty += 6.0;
   if(ctx.news_distance_min >= 0 && ctx.news_distance_min <= g_newsBlockBeforeMin)
      penalty += 8.0;
   if(SNR_OpportunityHardBlocked(ctx, block_reason))
      penalty += 12.0;
   return penalty;
}

double SNR_CalcScalpOpportunityScore(const SnrContext &ctx,
                                     const int direction,
                                     const string block_reason)
{
   double score = 0.0;
   score += SNR_OpportunityStructureScore(ctx, direction);
   score += SNR_OpportunityHtfScore(ctx, direction);
   score += SNR_OpportunityPvsraScore(ctx, direction);
   score += SNR_OpportunityLevelScore(ctx);
   score += SNR_OpportunityTimeSafetyScore(ctx);
   score -= SNR_OpportunityPenalty(ctx, block_reason);
   return SNR_Clamp(score, 0.0, 100.0);
}

double SNR_ClassicOpportunityScore(const SnrContext &ctx,
                                   const int direction,
                                   const double scalp_score)
{
   double score = scalp_score;
   if((direction > 0 && ctx.allow_long) || (direction < 0 && ctx.allow_short))
      score += 8.0;
   if(MathAbs(ctx.dragon_slope_atr) >= g_minDragonSlopeATR)
      score += 5.0;
   return SNR_Clamp(score, 0.0, 100.0);
}

double SNR_ReentryOpportunityScore(const SnrContext &ctx,
                                  const int direction,
                                  const double scalp_score)
{
   double score = scalp_score;
   if(ctx.active_layers > 0 && ctx.narrative_direction == direction)
      score += 10.0;
   if(ctx.pvsra_grade >= g_reentryMinPvsraGrade)
      score += 5.0;
   return SNR_Clamp(score, 0.0, 100.0);
}

bool SNR_OpportunitySelectedDecision(const SnrDecision &decision)
{
   return (decision.direction != SNR_DIR_NONE &&
           (decision.mode == SNR_MODE_CLASSIC ||
            decision.mode == SNR_MODE_REENTRY ||
            decision.mode == SNR_MODE_SCOUT2 ||
            decision.mode == SNR_MODE_CONTINUATION ||
            decision.mode == SNR_MODE_XAU_ACTIVE_CLASSIC ||
            decision.mode == SNR_MODE_XAU_RANGE_ABSORPTION ||
            decision.mode == SNR_MODE_XAU_SWEEP_RECLAIM_SCAN ||
            decision.mode == SNR_MODE_XAU_SWEEP_RECLAIM ||
            decision.mode == SNR_MODE_EUR_TREND_CLASSIC ||
            decision.mode == SNR_MODE_EUR_ASIAN_BOX_RETEST) &&
           (decision.wave_id != "" || decision.setup_state == "ARM" || decision.setup_state == "TRIGGER"));
}

bool SNR_OpportunityScannerDirection(const SnrContext &ctx, const int direction)
{
   if(direction > 0)
      return (ctx.allow_long ||
              (ctx.dragon_slope_atr > 0.0 && ctx.htf_bias_score >= 0) ||
              (ctx.pvsra_bias == "BULLISH" && ctx.pvsra_grade >= 3));
   return (ctx.allow_short ||
           (ctx.dragon_slope_atr < 0.0 && ctx.htf_bias_score <= 0) ||
           (ctx.pvsra_bias == "BEARISH" && ctx.pvsra_grade >= 3));
}

bool SNR_OpportunityResearchWorthy(const SnrContext &ctx,
                                   const SnrDecision &decision,
                                   const int direction,
                                   const double scalp_score)
{
   if(SNR_OpportunitySelectedDecision(decision))
      return true;
   if(!SNR_OpportunityScannerDirection(ctx, direction))
      return false;
   if(scalp_score >= 50.0)
      return true;
   return (scalp_score >= 42.0 && (ctx.pvsra_grade >= 3 || ctx.level_zone != "NONE" || ctx.pvsra_event != "NONE"));
}

string SNR_OpportunityWaveId(const SnrContext &ctx,
                             const SnrDecision &decision,
                             const string setup_type,
                             const int direction)
{
   if(decision.wave_id != "")
      return decision.wave_id;
   return SNR_BuildWaveId(SNR_OpportunityClosedBarTime(ctx), setup_type + "_SCAN", direction);
}

string SNR_OpportunityCandidateId(const string run_id,
                                  const datetime bar_time,
                                  const string setup_type,
                                  const int direction,
                                  const string wave_id)
{
   return run_id + "|" + _Symbol + "|" + EnumToString(_Period) + "|" +
          TimeToString(bar_time, TIME_DATE | TIME_MINUTES | TIME_SECONDS) + "|" +
          setup_type + "|" + SNR_DirectionName(direction) + "|" + wave_id;
}

string SNR_UpdateShadowNarrative(const SnrContext &ctx,
                                 const string outcome,
                                 const string setup_type,
                                 const int direction,
                                 const string wave_id,
                                 const double classic_score,
                                 const double reentry_score,
                                 const string block_reason,
                                 SnrShadowNarrative &shadow)
{
   if(!g_enableShadowNarrative || direction == SNR_DIR_NONE)
      return "";

   int ttl_seconds = MathMax(PeriodSeconds(_Period), 60) * 6;
   if(shadow.active && shadow.expires_at > 0 && ctx.decision_time_server > shadow.expires_at)
   {
      shadow.state = SNR_SHADOW_INVALIDATE;
      shadow.invalidation_reason = "STALE_NARRATIVE";
      shadow.active = false;
   }

   bool hard_block = SNR_OpportunityHardBlocked(ctx, block_reason);
   if(hard_block && shadow.active)
   {
      shadow.state = SNR_SHADOW_INVALIDATE;
      shadow.invalidation_reason = (block_reason != "" ? block_reason : "HARD_BLOCK");
      shadow.active = false;
   }

   string mapped_outcome = SNR_OpportunityOutcomeName(outcome);
   if(mapped_outcome == "FIRED")
   {
      if(!shadow.active || shadow.direction != direction || shadow.wave_id != wave_id)
      {
         shadow.narrative_id = SNR_OpportunityCandidateId(g_snrRunId, SNR_OpportunityClosedBarTime(ctx), setup_type, direction, wave_id);
         shadow.seeded_at = ctx.decision_time_server;
         shadow.trigger_count = 0;
      }
      shadow.active = true;
      shadow.direction = direction;
      shadow.state = SNR_SHADOW_MANAGE;
      shadow.wave_id = wave_id;
      shadow.trigger_count++;
      shadow.invalidation_reason = "";
   }
   else if(!hard_block && mapped_outcome == "SCANNER_ONLY")
   {
      if(!shadow.active || shadow.direction != direction)
      {
         shadow.narrative_id = SNR_OpportunityCandidateId(g_snrRunId, SNR_OpportunityClosedBarTime(ctx), setup_type, direction, wave_id);
         shadow.seeded_at = ctx.decision_time_server;
      }
      shadow.active = true;
      shadow.direction = direction;
      shadow.state = (classic_score >= 65.0 || reentry_score >= 65.0 ? SNR_SHADOW_ARM : SNR_SHADOW_OBSERVE);
      shadow.wave_id = wave_id;
      shadow.invalidation_reason = "";
   }
   else if(!hard_block && mapped_outcome == "BLOCKED" && (classic_score >= 65.0 || reentry_score >= 65.0))
   {
      if(!shadow.active || shadow.direction != direction)
      {
         shadow.narrative_id = SNR_OpportunityCandidateId(g_snrRunId, SNR_OpportunityClosedBarTime(ctx), setup_type, direction, wave_id);
         shadow.seeded_at = ctx.decision_time_server;
      }
      shadow.active = true;
      shadow.direction = direction;
      shadow.state = SNR_SHADOW_ARM;
      shadow.wave_id = wave_id;
      shadow.invalidation_reason = "";
   }
   else if(mapped_outcome == "ORDER_REJECTED")
   {
      shadow.state = SNR_SHADOW_INVALIDATE;
      shadow.invalidation_reason = (block_reason != "" ? block_reason : "ORDER_REJECTED");
      shadow.active = false;
   }

   if(shadow.narrative_id == "")
      shadow.narrative_id = SNR_OpportunityCandidateId(g_snrRunId, SNR_OpportunityClosedBarTime(ctx), setup_type, direction, wave_id);
   shadow.last_seen_at = ctx.decision_time_server;
   shadow.expires_at = ctx.decision_time_server + ttl_seconds;
   shadow.classic_setup_score = classic_score;
   shadow.reentry_setup_score = reentry_score;
   return shadow.narrative_id + ":" + SNR_ShadowStateName(shadow.state);
}

void SNR_BuildOpportunityRecord(const SnrContext &ctx,
                                const SnrDecision &decision,
                                const string outcome,
                                const string setup_type,
                                const int direction,
                                const double scalp_score,
                                const double classic_score,
                                const double reentry_score,
                                const string narrative_id,
                                SnrOpportunityRecord &record)
{
   string block_reason = SNR_OpportunityBlockReason(ctx, decision);
   string wave_id = SNR_OpportunityWaveId(ctx, decision, setup_type, direction);
   datetime closed_bar = SNR_OpportunityClosedBarTime(ctx);
   double entry_ref_price = (direction > 0 ? SymbolInfoDouble(_Symbol, SYMBOL_ASK) : SymbolInfoDouble(_Symbol, SYMBOL_BID));
   double stop_ref_price = (SNR_OpportunitySelectedDecision(decision) ? decision.stop_price : 0.0);
   if(stop_ref_price <= 0.0 && entry_ref_price > 0.0 && ctx.atr > 0.0)
   {
      double min_stop_price_distance = g_minSLPips * SNR_CurrentPipSize();
      double research_stop_distance = MathMax(min_stop_price_distance, ctx.atr * 0.75);
      stop_ref_price = (direction > 0 ? entry_ref_price - research_stop_distance : entry_ref_price + research_stop_distance);
   }
   double risk_points = 0.0;
   if(entry_ref_price > 0.0 && stop_ref_price > 0.0)
      risk_points = MathAbs(entry_ref_price - stop_ref_price) / _Point;

   record.run_id = g_snrRunId;
   record.candidate_id = SNR_OpportunityCandidateId(g_snrRunId, closed_bar, setup_type, direction, wave_id);
   record.server_ts = ctx.decision_time_server;
   record.utc_ts = ctx.decision_time_utc;
   record.symbol = _Symbol;
   record.timeframe = EnumToString(_Period);
   record.bar_time = closed_bar;
   record.variant = SNR_CleanTesterString(g_variantTag);
   record.setup_type = setup_type;
   record.direction = SNR_DirectionName(direction);
   record.outcome = SNR_OpportunityOutcomeName(outcome);
   record.block_reason = block_reason;
   record.wave_id = wave_id;
   record.session_bucket = ctx.session_bucket;
   record.weekday = SNR_WeekdayTag(ctx.decision_time_server);
   record.hour_server = ctx.hour_server;
   record.spread_pips = ctx.spread_pips;
   record.entry_ref_price = entry_ref_price;
   record.stop_ref_price = stop_ref_price;
   record.target_rr = (SNR_OpportunitySelectedDecision(decision) ? decision.target_rr : (setup_type == "REENTRY" ? g_reentryTargetRR : g_classicTargetRR));
   record.risk_points = risk_points;
   record.dragon_slope_atr = ctx.dragon_slope_atr;
   record.trend_slope_atr = ctx.trend_slope_atr;
   record.h1_bias = ctx.h1_bias;
   record.h4_bias = ctx.h4_bias;
   record.pvsra_bias = ctx.pvsra_bias;
   record.pvsra_event = ctx.pvsra_event;
   record.pvsra_grade = ctx.pvsra_grade;
   record.level_zone = ctx.level_zone;
   record.level_distance_pips = ctx.level_distance_pips;
   record.quality_score = (SNR_OpportunitySelectedDecision(decision) ? decision.quality_score : 0.0);
   record.context_score = ctx.context_score;
   record.classic_setup_score = classic_score;
   record.reentry_setup_score = reentry_score;
   record.scalp_opportunity_score = scalp_score;
   record.narrative_id = narrative_id;
}

void SNR_LogOneOpportunity(const SnrContext &ctx,
                           const SnrDecision &decision,
                           const string outcome,
                           const string setup_type,
                           const int direction,
                           SnrShadowNarrative &shadow)
{
   string block_reason = SNR_OpportunityBlockReason(ctx, decision);
   double scalp_score = SNR_CalcScalpOpportunityScore(ctx, direction, block_reason);
   if(!SNR_OpportunityResearchWorthy(ctx, decision, direction, scalp_score))
      return;

   double classic_score = SNR_ClassicOpportunityScore(ctx, direction, scalp_score);
   double reentry_score = SNR_ReentryOpportunityScore(ctx, direction, scalp_score);
   string wave_id = SNR_OpportunityWaveId(ctx, decision, setup_type, direction);
   string narrative_id = SNR_UpdateShadowNarrative(ctx, outcome, setup_type, direction, wave_id,
                                                   classic_score, reentry_score, block_reason, shadow);

   SnrOpportunityRecord record;
   SNR_BuildOpportunityRecord(ctx, decision, outcome, setup_type, direction,
                              scalp_score, classic_score, reentry_score, narrative_id, record);
   SNR_LogOpportunityRecord(record);
}

void SNR_LogOpportunityBundle(const SnrContext &ctx,
                              const SnrDecision &decision,
                              const string outcome,
                              SnrShadowNarrative &shadow_long,
                              SnrShadowNarrative &shadow_short)
{
   if(!g_enableOpportunityLogger)
      return;

   if(SNR_OpportunitySelectedDecision(decision))
   {
      string setup_type = SNR_OpportunitySetupType(decision.mode, ctx);
      string selected_outcome = (decision.mode == SNR_MODE_XAU_SWEEP_RECLAIM_SCAN ? "SCANNER_ONLY" : outcome);
      if(decision.direction > 0)
         SNR_LogOneOpportunity(ctx, decision, selected_outcome, setup_type, SNR_DIR_LONG, shadow_long);
      else if(decision.direction < 0)
         SNR_LogOneOpportunity(ctx, decision, selected_outcome, setup_type, SNR_DIR_SHORT, shadow_short);
      return;
   }

   string scanner_outcome = (SNR_OpportunityHardBlocked(ctx, SNR_OpportunityBlockReason(ctx, decision)) ? "BLOCKED" : "SCANNER_ONLY");
   string setup_type = SNR_OpportunitySetupType(decision.mode, ctx);
   if(SNR_OpportunityScannerDirection(ctx, SNR_DIR_LONG))
      SNR_LogOneOpportunity(ctx, decision, scanner_outcome, setup_type, SNR_DIR_LONG, shadow_long);
   if(SNR_OpportunityScannerDirection(ctx, SNR_DIR_SHORT))
      SNR_LogOneOpportunity(ctx, decision, scanner_outcome, setup_type, SNR_DIR_SHORT, shadow_short);
}

bool SNR_OpportunityScoreGateMode(const SnrMode mode)
{
   return (mode == SNR_MODE_CLASSIC ||
           mode == SNR_MODE_REENTRY ||
           mode == SNR_MODE_CONTINUATION ||
           mode == SNR_MODE_XAU_SWEEP_RECLAIM);
}

bool SNR_XauClassicStateQualityMode(const SnrMode mode)
{
   return (mode == SNR_MODE_CLASSIC ||
           mode == SNR_MODE_XAU_ACTIVE_CLASSIC);
}

bool SNR_XauClassicStateQualitySymbol()
{
   return (StringFind(_Symbol, "XAUUSD") == 0);
}

bool SNR_FxClassicStateQualityMode(const SnrMode mode)
{
   return (mode == SNR_MODE_CLASSIC ||
           mode == SNR_MODE_EUR_TREND_CLASSIC);
}

bool SNR_FxClassicStateQualitySymbol()
{
   return (StringFind(_Symbol, "EURUSD") == 0 ||
           StringFind(_Symbol, "GBPUSD") == 0);
}

double SNR_FxV2AAlignedDelta(const SnrPvsraSrFields &fields, const int direction)
{
   if(direction > 0)
      return fields.seq_5_close_delta_pips;
   if(direction < 0)
      return -fields.seq_5_close_delta_pips;
   return 0.0;
}

string SNR_FxV2AWaveState(const SnrPvsraSrFields &fields)
{
   string state = SNR_ToUpper(fields.source_classic_wave_state);
   string quality = SNR_ToUpper(fields.sonic_wave_quality);
   if(state == "CHOPPY" || state == "CHOPPY_CROSS" || state == "OVERLAP" || quality == "CHOPPY")
      return "choppy";
   if((state == "CLEAN" || state == "CLEAN_CLASSIC") && fields.source_classic_wave_smoothness >= 0.55)
      return "clean";
   return "unclear";
}

string SNR_FxV2ATrendHtfState(const SnrContext &ctx, const int direction)
{
   if(direction == SNR_DIR_NONE || (ctx.h1_bias == 0 && ctx.h4_bias == 0))
      return "unknown";
   int aligned = 0;
   int opposed = 0;
   if(ctx.h1_bias * direction > 0)
      aligned++;
   if(ctx.h4_bias * direction > 0)
      aligned++;
   if(ctx.h1_bias * direction < 0)
      opposed++;
   if(ctx.h4_bias * direction < 0)
      opposed++;
   if(aligned == 2)
      return "aligned";
   if(opposed == 2)
      return "hard_conflict";
   return "soft_conflict";
}

string SNR_FxV2ASrRunway(const SnrContext &ctx,
                         const SnrPvsraSrFields &fields,
                         const int direction,
                         const double pip_size,
                         const string old_block_reason)
{
   double runway_pips = SNR_StateTelemetrySrRunwayPips(fields, direction, pip_size);
   string interaction = SNR_ToUpper(fields.source_sr_interaction);
   string story = SNR_ToUpper(fields.sonic_level_story);
   string session_runway = SNR_ToUpper(fields.source_classic_session_runway);
   string block_reason = SNR_ToUpper(old_block_reason);
   double distance = MathMin(MathAbs(fields.dist_close_to_whole_pips),
                    MathMin(MathAbs(fields.dist_close_to_half_pips), MathAbs(fields.dist_close_to_quarter_pips)));
   if(distance < 0.0 || distance > 900.0)
      distance = 999.0;

   // Scale runway thresholds dynamically on M5 to resolve static runway bottleneck
   double limit_blocked = 4.0;
   double limit_blocked_prev = 5.0;
   double limit_clear_hwhq = 12.0;
   double limit_clear_session = 8.0;

   if(_Period == PERIOD_M5 || _Period == PERIOD_M15)
   {
      double atr_pips = (pip_size > 0.0) ? (ctx.atr / pip_size) : 0.0;
      double base_atr = (_Period == PERIOD_M15) ? 12.0 : 5.0;
      double scale = (atr_pips > 0.0) ? (atr_pips / base_atr) : 1.0;
      limit_blocked = 4.0 * scale;
      limit_blocked_prev = 5.0 * scale;
      limit_clear_hwhq = 12.0 * scale;
      limit_clear_session = 8.0 * scale;
   }

   if(runway_pips < 0.0)
      return "unknown";
   if(runway_pips < limit_blocked || (block_reason == "FX_CLASSIC_RUNWAY_LOW" && runway_pips < limit_blocked_prev))
      return "blocked";
   if(interaction == "NEAR" || story == "NEAR_WHQ" || story == "REPEATED_WHQ_WORK" || distance <= 5.0)
      return "near_whole_half_quarter";
   if(runway_pips >= limit_clear_hwhq &&
      (interaction == "RUNWAY" || interaction == "BODY_CROSS" || interaction == "REJECTION"))
      return "clear";
   if(session_runway == "CLEAR" && runway_pips >= limit_clear_session)
      return "clear";
   return "unknown";
}

void SNR_FxV2AAppendReason(string &reasons, const string reason)
{
   if(reason == "")
      return;
   if(reasons != "")
      reasons += "|";
   reasons += reason;
}

int SNR_FxV2APublicRiskScoreEx(const SnrContext &ctx,
                               const SnrPvsraSrFields &fields,
                               const string runway,
                               const string trend,
                               const string wave,
                               const int direction,
                               string &reasons)
{
   reasons = "";
   int score = 0;
   double aligned_delta = SNR_FxV2AAlignedDelta(fields, direction);
   string source_pva = SNR_ToUpper(fields.source_pva_event);
   string pvsra_event = SNR_ToUpper(ctx.pvsra_event);
   string source_run_mode = SNR_ToUpper(fields.source_classic_run_mode_proxy);
   string sr_interaction = SNR_ToUpper(fields.source_sr_interaction);

   if(runway == "blocked")
   {
      score += 2;
      SNR_FxV2AAppendReason(reasons, "blocked_runway");
   }
   else if(runway == "near_whole_half_quarter")
   {
      score += 1;
      SNR_FxV2AAppendReason(reasons, "near_whq");
   }

   if(trend == "hard_conflict")
   {
      score += 2;
      SNR_FxV2AAppendReason(reasons, "htf_hard_conflict");
   }
   else if(trend == "soft_conflict")
   {
      score += 1;
      SNR_FxV2AAppendReason(reasons, "htf_soft_conflict");
   }

   if(wave != "clean")
   {
      score += 1;
      SNR_FxV2AAppendReason(reasons, "wave_not_clean");
   }

   if(source_pva == "CLIMAX" || source_pva == "RISING_ACTIVITY" ||
      pvsra_event == "CLIMAX" || pvsra_event == "RISING_ACTIVITY" || pvsra_event == "WIDE_BODY")
   {
      score += 1;
      SNR_FxV2AAppendReason(reasons, "pva_activity");
   }

   if(source_run_mode == "TRAP_RISK")
   {
      score += 2;
      SNR_FxV2AAppendReason(reasons, "source_trap_proxy");
   }

   if(aligned_delta > 12.0 || fields.seq_5_net_range_atr > 3.0)
   {
      score += 1;
      SNR_FxV2AAppendReason(reasons, "extended_sequence");
   }

   if(fields.source_classic_dragon_expansion > 1.05)
   {
      score += 1;
      SNR_FxV2AAppendReason(reasons, "dragon_overextended");
   }

   if(sr_interaction == "REJECTION")
   {
      score += 1;
      SNR_FxV2AAppendReason(reasons, "level_rejection");
   }

   return score;
}

int SNR_FxV2APublicRiskScore(const SnrContext &ctx,
                             const SnrPvsraSrFields &fields,
                             const string runway,
                             const string trend,
                             const string wave,
                             const int direction)
{
   string reasons = "";
   return SNR_FxV2APublicRiskScoreEx(ctx, fields, runway, trend, wave, direction, reasons);
}

string SNR_FxV2ATrapBuildRun(const SnrContext &ctx,
                             const SnrPvsraSrFields &fields,
                             const string runway,
                             const string trend,
                             const string wave,
                             const int score,
                             const int direction)
{
   double aligned_delta = SNR_FxV2AAlignedDelta(fields, direction);
   string source_pva = SNR_ToUpper(fields.source_pva_event);
   string sr_interaction = SNR_ToUpper(fields.source_sr_interaction);
   string sonic_mode = SNR_ToUpper(fields.sonic_mm_mode_proxy);
   string source_mode = SNR_ToUpper(fields.source_classic_run_mode_proxy);

   bool clean_run = (runway == "clear" &&
                     trend == "aligned" &&
                     wave == "clean" &&
                     aligned_delta >= -2.0 &&
                     aligned_delta <= 9.0 &&
                     fields.seq_5_net_range_atr <= 2.4 &&
                     fields.source_classic_dragon_expansion < 1.02 &&
                     source_pva == "NONE" &&
                     source_mode != "TRAP_RISK");
   if(clean_run)
      return "run_for_profits";

   bool build_signal = (sonic_mode == "POSITION_BUILDING" ||
                        ((source_pva == "CLIMAX" || source_pva == "RISING_ACTIVITY") &&
                         (sr_interaction == "NEAR" || sr_interaction == "REJECTION" || sr_interaction == "BODY_CROSS") &&
                         score < 4));
   if(build_signal)
      return "build";

   if(source_mode == "TRAP_RISK" || score >= 4 || (sonic_mode == "TRAP_RISK" && score >= 3))
      return "trap_risk";
   return "unclear";
}

string SNR_FxV2AChaseRisk(const SnrContext &ctx,
                          const SnrPvsraSrFields &fields,
                          const string runway,
                          const string trend,
                          const string wave,
                          const int score,
                          const int direction)
{
   double aligned_delta = SNR_FxV2AAlignedDelta(fields, direction);
   string old_chase = SNR_ToUpper(fields.source_classic_chase_risk);

   if(wave != "clean" || trend == "unknown" || runway == "unknown")
      return "unclear";

   // Scale aligned delta thresholds dynamically on M5
   double limit_delta_mature = 4.0;
   double limit_delta_late = 12.0;
   if(_Period == PERIOD_M5 || _Period == PERIOD_M15)
   {
      double pip_size = SNR_CurrentPipSize();
      double atr_pips = (pip_size > 0.0) ? (ctx.atr / pip_size) : 0.0;
      double base_atr = (_Period == PERIOD_M15) ? 12.0 : 5.0;
      double scale = (atr_pips > 0.0) ? (atr_pips / base_atr) : 1.0;
      limit_delta_mature = 4.0 * scale;
      limit_delta_late = 12.0 * scale;
   }

   if(runway == "clear" &&
      trend == "aligned" &&
      old_chase == "MATURE" &&
      aligned_delta <= limit_delta_mature &&
      fields.seq_5_net_range_atr <= 2.2 &&
      fields.source_classic_dragon_expansion < 0.98)
      return "early_continuation";

   if(score >= 4 ||
      (old_chase == "LATE_CHASE" && score >= 3) ||
      (old_chase == "LATE_CHASE" &&
       (aligned_delta > limit_delta_late || fields.seq_5_net_range_atr > 3.0 || fields.source_classic_dragon_expansion > 1.05)))
      return "late_extension";

   if(runway == "clear" && (trend == "aligned" || trend == "soft_conflict") && score <= 3)
      return "mature_continuation";
   if(old_chase == "MATURE" && score <= 3)
      return "mature_continuation";
   if(old_chase == "LATE_CHASE" && (runway == "blocked" || runway == "near_whole_half_quarter") && score >= 2)
      return "late_extension";
   return "unclear";
}

void SNR_ClassifyFxChaseTrapV2A(const SnrContext &ctx,
                                const SnrPvsraSrFields &fields,
                                const int direction,
                                const double pip_size,
                                const string old_block_reason,
                                string &decision,
                                string &reason_codes)
{
   string runway = SNR_FxV2ASrRunway(ctx, fields, direction, pip_size, old_block_reason);
   string trend = SNR_FxV2ATrendHtfState(ctx, direction);
   string wave = SNR_FxV2AWaveState(fields);
   string risk_reasons = "";
   int score = SNR_FxV2APublicRiskScoreEx(ctx, fields, runway, trend, wave, direction, risk_reasons);
   string trap = SNR_FxV2ATrapBuildRun(ctx, fields, runway, trend, wave, score, direction);
   string chase = SNR_FxV2AChaseRisk(ctx, fields, runway, trend, wave, score, direction);

   if(trap == "run_for_profits" && runway == "clear" && wave == "clean" && trend != "hard_conflict")
      decision = "proxy_keep_run_for_profits";
   else if(runway == "blocked")
      decision = "proxy_block_low_or_unknown_runway";
   else if(runway == "clear" && trap != "run_for_profits")
      decision = "proxy_block_clear_but_no_run_confirm";
   else if((runway != "unknown") && (chase == "unclear" || trap == "unclear"))
      decision = "proxy_block_unclear_chase_or_run";
   else
      decision = "proxy_neutral_diagnostic";

   reason_codes = StringFormat("runway=%s;trend_htf_state=%s;wave_state=%s;trap_build_run=%s;chase_risk=%s;risk_score=%d",
                               runway, trend, wave, trap, chase, score);
   if(risk_reasons != "")
      reason_codes += ";risk_reasons=" + risk_reasons;
}

bool SNR_DragonPvsraEntryProxyMode(const SnrMode mode)
{
   return (mode == SNR_MODE_CLASSIC ||
           mode == SNR_MODE_CONTINUATION ||
           mode == SNR_MODE_XAU_ACTIVE_CLASSIC ||
           mode == SNR_MODE_EUR_TREND_CLASSIC);
}

string SNR_StateTelemetryDouble(const bool ok, const double value, const int digits)
{
   return (ok ? DoubleToString(value, digits) : "");
}

string SNR_StateTelemetryBool(const bool ok, const bool value)
{
   return (ok ? SNR_BoolLabel(value) : "");
}

double SNR_StateTelemetryExtensionFromDragonAtr(const SnrContext &ctx,
                                                const SnrPvsraSrFields &fields,
                                                const int direction)
{
   if(ctx.atr <= 0.0 || !fields.data_available)
      return 0.0;
   if(direction > 0)
      return (fields.bar_close - ctx.dragon_mid) / ctx.atr;
   return (ctx.dragon_mid - fields.bar_close) / ctx.atr;
}

double SNR_StateTelemetryExtensionFromBreakAtr(const SnrContext &ctx,
                                               const SnrPvsraSrFields &fields,
                                               const int direction)
{
   if(ctx.atr <= 0.0 || !fields.data_available)
      return 0.0;
   if(direction > 0)
      return (fields.bar_close - fields.prior_swing_high_20) / ctx.atr;
   return (fields.prior_swing_low_20 - fields.bar_close) / ctx.atr;
}

double SNR_StateTelemetryGridRunwayPips(const double price,
                                        const int direction,
                                        const double pip_size)
{
   if(pip_size <= 0.0)
      return 0.0;

   double grid_pips = (g_levelGridMode == 1 ? 25.0 : 50.0);
   double step = grid_pips * pip_size;
   if(step <= 0.0)
      return 0.0;

   double base = MathFloor(price / step) * step;
   double next_level = (direction > 0 ? base + step : base);
   if(direction < 0 && MathAbs(price - base) < _Point * 0.5)
      next_level = base - step;
   return MathAbs(next_level - price) / pip_size;
}

double SNR_StateTelemetrySrRunwayPips(const SnrPvsraSrFields &fields,
                                      const int direction,
                                      const double pip_size)
{
   if(!fields.data_available || pip_size <= 0.0)
      return 0.0;

   double runway = SNR_StateTelemetryGridRunwayPips(fields.bar_close, direction, pip_size);
   if(direction > 0 && fields.prior_swing_high_20 > fields.bar_close)
      runway = MathMin(runway, (fields.prior_swing_high_20 - fields.bar_close) / pip_size);
   else if(direction < 0 && fields.prior_swing_low_20 < fields.bar_close)
      runway = MathMin(runway, (fields.bar_close - fields.prior_swing_low_20) / pip_size);
   return MathMax(0.0, runway);
}

bool SNR_StateTelemetryRetestDragonOk(const SnrContext &ctx,
                                      const SnrPvsraSrFields &fields,
                                      const int direction)
{
   if(ctx.atr <= 0.0 || !fields.data_available)
      return false;
   if(direction > 0)
      return (fields.bar_low <= ctx.dragon_high + 0.10 * ctx.atr &&
              fields.bar_close > ctx.dragon_mid);
   return (fields.bar_high >= ctx.dragon_low - 0.10 * ctx.atr &&
           fields.bar_close < ctx.dragon_mid);
}

string SNR_StateTelemetrySweepReclaimSide(const SnrPvsraSrFields &fields)
{
   if(!fields.data_available)
      return "UNKNOWN";

   bool bull = (fields.breaks_prior_swing_low && fields.bar_close > fields.prior_swing_low_20);
   bool bear = (fields.breaks_prior_swing_high && fields.bar_close < fields.prior_swing_high_20);
   if(bull && bear)
      return "BOTH";
   if(bull)
      return "BULL";
   if(bear)
      return "BEAR";
   return "NONE";
}

double SNR_StateTelemetryWaveSmoothness(const SnrPvsraSrFields &fields,
                                        const int direction)
{
   if(!fields.data_available)
      return 0.0;
   if(direction > 0)
      return SNR_Clamp((double)fields.seq_5_bull_count / 5.0, 0.0, 1.0);
   return SNR_Clamp((double)fields.seq_5_bear_count / 5.0, 0.0, 1.0);
}

double SNR_StateTelemetryDragonOverlapRatio(const SnrContext &ctx,
                                            const SnrPvsraSrFields &fields)
{
   if(!fields.data_available)
      return 0.0;

   double bar_range = fields.bar_high - fields.bar_low;
   if(bar_range <= 0.0)
      return 0.0;

   double dragon_low = MathMin(ctx.dragon_low, ctx.dragon_high);
   double dragon_high = MathMax(ctx.dragon_low, ctx.dragon_high);
   double overlap_low = MathMax(fields.bar_low, dragon_low);
   double overlap_high = MathMin(fields.bar_high, dragon_high);
   double overlap = MathMax(0.0, overlap_high - overlap_low);
   return SNR_Clamp(overlap / bar_range, 0.0, 1.0);
}

bool SNR_ApplyXauClassicStateQualityGate(const SnrContext &ctx,
                                         SnrDecision &decision)
{
   if(!g_useXauClassicStateQualityGate)
      return false;
   if(!decision.should_trade || decision.direction == SNR_DIR_NONE)
      return false;
   if(!SNR_XauClassicStateQualityMode(decision.mode))
      return false;
   if(!SNR_XauClassicStateQualitySymbol() || _Period != PERIOD_M5)
      return false;
   if(ctx.atr <= 0.0)
      return false;

   double pip_size = SNR_CurrentPipSize();
   if(pip_size <= 0.0)
      return false;

   SnrPvsraSrFields fields;
   bool fields_ok = SNR_BuildPvsraSrFields(pip_size, ctx.atr, fields);
   if(!fields_ok || !fields.data_available)
      return false;

   double extension_from_dragon_atr = SNR_StateTelemetryExtensionFromDragonAtr(ctx, fields, decision.direction);
   double sr_runway_pips = SNR_StateTelemetrySrRunwayPips(fields, decision.direction, pip_size);
   double overlap_ratio = SNR_StateTelemetryDragonOverlapRatio(ctx, fields);

   double min_runway = g_xauClassicMinRunwayPips;
   double min_hour15_runway = g_xauClassicHour15MinRunwayPips;
   if(_Period == PERIOD_M5)
   {
      double atr_pips = (pip_size > 0.0) ? (ctx.atr / pip_size) : 0.0;
      double scale = (atr_pips > 0.0) ? (atr_pips / 15.0) : 1.0;
      min_runway = g_xauClassicMinRunwayPips * scale;
      min_hour15_runway = g_xauClassicHour15MinRunwayPips * scale;
   }

   int warnings = 0;
   if(min_runway > 0.0 && sr_runway_pips < min_runway)
      warnings++;
   if(g_xauClassicMaxOverlapRatio > 0.0 && overlap_ratio > g_xauClassicMaxOverlapRatio)
      warnings++;

   MqlDateTime dt;
   TimeToStruct(ctx.decision_time_server, dt);
   if(dt.hour == 15 &&
      g_xauClassicMaxDragonExtensionAtr > 0.0 &&
      extension_from_dragon_atr > g_xauClassicMaxDragonExtensionAtr)
      warnings++;
   if(dt.hour == 15 &&
      min_hour15_runway > 0.0 &&
      sr_runway_pips < min_hour15_runway)
      warnings++;

   int min_warnings = g_xauClassicStateMinWarnings;
   if(min_warnings < 1)
      min_warnings = 1;
   if(warnings < min_warnings)
      return false;

   decision.should_trade = false;
   decision.block_reason = "CLASSIC_STATE_QUALITY_LOW";
   decision.invalidate_reason = "CLASSIC_STATE_QUALITY_LOW";
   decision.setup_state = "INVALIDATE";
   return true;
}

string SNR_FxClassicStateQualityBlockReason(const SnrContext &ctx,
                                            SnrDecision &decision)
{
   double pip_size = SNR_CurrentPipSize();
   if(pip_size <= 0.0 || ctx.atr <= 0.0)
      return "FX_CLASSIC_STATE_DATA";

   SnrPvsraSrFields fields;
   bool fields_ok = SNR_BuildPvsraSrFields(pip_size, ctx.atr, fields);
   if(!fields_ok || !fields.data_available)
      return "FX_CLASSIC_STATE_DATA";

   SNR_AnnotateSourceClassicFields(ctx, decision.direction, fields);
   SNR_AnnotateSonicTraderState(ctx, decision.direction, fields);

   if(g_fxClassicRequireHtfAlignment)
   {
      if(decision.direction > 0 && ctx.htf_bias_score < 0)
         return "FX_CLASSIC_HTF_MISALIGN";
      if(decision.direction < 0 && ctx.htf_bias_score > 0)
         return "FX_CLASSIC_HTF_MISALIGN";
   }

   bool flat_dragon = (fields.sonic_dragon_momentum == "flat" ||
                       fields.sonic_dragon_momentum == "compressed" ||
                       fields.source_classic_dragon_state == "dragon_flat" ||
                       fields.source_classic_dragon_state == "dragon_compressed");
   if(g_fxClassicBlockFlatDragon && flat_dragon)
      return "FX_CLASSIC_FLAT_DRAGON";

   bool late_or_trap = (fields.sonic_entry_timing_risk == "late_chase" ||
                       fields.sonic_mm_mode_proxy == "trap_risk" ||
                       fields.source_classic_run_mode_proxy == "trap_risk");
   bool v2a_diagnostic_active = (g_fxClassicBlockLateChase && g_useFxChaseTrapV2ADiagnostic);
   if(v2a_diagnostic_active)
   {
      string v2a_decision = "";
      string v2a_reasons = "";
      string v2a_gate_reason = (late_or_trap ? "FX_CLASSIC_CHASE_TRAP" : "FX_CLASSIC_NO_CHASE_TRAP");
      SNR_ClassifyFxChaseTrapV2A(ctx, fields, decision.direction, pip_size,
                                 v2a_gate_reason, v2a_decision, v2a_reasons);
      decision.fx_v2a_evaluated = true;
      decision.fx_v2a_old_state_gate_reason = v2a_gate_reason;
      decision.fx_v2a_old_late_chase_trap_reason = v2a_gate_reason;
      decision.fx_v2a_decision = v2a_decision;
      decision.fx_v2a_reason_codes = v2a_reasons;

      if(!late_or_trap)
         decision.fx_v2a_final_action = "diagnostic_only_no_chase_trap";
      else if(v2a_decision == "proxy_keep_run_for_profits")
         decision.fx_v2a_final_action = "allow_v2a_keep_then_existing_gate";
      else if(v2a_decision == "proxy_neutral_diagnostic")
         decision.fx_v2a_final_action = "allow_v2a_neutral_then_existing_gate";
      else
      {
         decision.fx_v2a_final_action = "block_v2a";
         return v2a_decision;
      }
   }
   else if(g_fxClassicBlockLateChase && late_or_trap)
      return "FX_CLASSIC_CHASE_TRAP";

   if(g_fxClassicRequireCleanWave && fields.sonic_wave_quality != "clean")
   {
      if(decision.fx_v2a_evaluated)
         decision.fx_v2a_final_action += ":FX_CLASSIC_WAVE_NOT_CLEAN";
      return "FX_CLASSIC_WAVE_NOT_CLEAN";
   }

   double min_runway = g_fxClassicMinRunwayPips;
   if(_Period == PERIOD_M5 || _Period == PERIOD_M15)
   {
      double atr_pips = (pip_size > 0.0) ? (ctx.atr / pip_size) : 0.0;
      double base_atr = (_Period == PERIOD_M15) ? 12.0 : 5.0;
      double scale = (atr_pips > 0.0) ? (atr_pips / base_atr) : 1.0;
      min_runway = g_fxClassicMinRunwayPips * scale;
   }
   double sr_runway_pips = SNR_StateTelemetrySrRunwayPips(fields, decision.direction, pip_size);
   if(min_runway > 0.0 && sr_runway_pips < min_runway)
   {
      if(decision.fx_v2a_evaluated)
         decision.fx_v2a_final_action += ":FX_CLASSIC_RUNWAY_LOW";
      return "FX_CLASSIC_RUNWAY_LOW";
   }

   double extension_from_dragon_atr = SNR_StateTelemetryExtensionFromDragonAtr(ctx, fields, decision.direction);
   if(g_fxClassicMaxDragonExtensionAtr > 0.0 &&
      extension_from_dragon_atr > g_fxClassicMaxDragonExtensionAtr)
   {
      if(decision.fx_v2a_evaluated)
         decision.fx_v2a_final_action += ":FX_CLASSIC_CHASE_EXTENSION";
      return "FX_CLASSIC_CHASE_EXTENSION";
   }

   double overlap_ratio = SNR_StateTelemetryDragonOverlapRatio(ctx, fields);
   if(g_fxClassicMaxOverlapRatio > 0.0 && overlap_ratio > g_fxClassicMaxOverlapRatio)
   {
      if(decision.fx_v2a_evaluated)
         decision.fx_v2a_final_action += ":FX_CLASSIC_DRAGON_OVERLAP";
      return "FX_CLASSIC_DRAGON_OVERLAP";
   }

   if(decision.fx_v2a_evaluated)
      decision.fx_v2a_final_action += ":order_path";
   return "";
}

bool SNR_ApplyFxClassicStateQualityGate(const SnrContext &ctx,
                                        SnrDecision &decision)
{
   if(!g_useFxClassicStateQualityGate)
      return false;
   if(!decision.should_trade || decision.direction == SNR_DIR_NONE)
      return false;
   if(!SNR_FxClassicStateQualityMode(decision.mode))
      return false;
   if(!SNR_FxClassicStateQualitySymbol() || (_Period != PERIOD_M5 && _Period != PERIOD_M15))
      return false;

   string reason = SNR_FxClassicStateQualityBlockReason(ctx, decision);
   if(reason == "")
      return false;

   decision.should_trade = false;
   decision.block_reason = reason;
   decision.invalidate_reason = reason;
   decision.setup_state = "INVALIDATE";
   return true;
}

string SNR_DragonPvsraEntryProxyBlockReason(const SnrContext &ctx,
                                            const SnrDecision &decision)
{
   double pip_size = SNR_CurrentPipSize();
   if(pip_size <= 0.0 || ctx.atr <= 0.0)
      return "DP_ENTRY_DATA_UNAVAILABLE";

   SnrPvsraSrFields fields;
   bool fields_ok = SNR_BuildPvsraSrFields(pip_size, ctx.atr, fields);
   if(!fields_ok || !fields.data_available)
      return "DP_ENTRY_DATA_UNAVAILABLE";

   SNR_AnnotateSourceClassicFields(ctx, decision.direction, fields);
   SNR_AnnotateSonicTraderState(ctx, decision.direction, fields);

   bool flat_dragon = (fields.sonic_dragon_momentum == "flat" ||
                       fields.sonic_dragon_momentum == "compressed" ||
                       fields.source_classic_dragon_state == "dragon_flat" ||
                       fields.source_classic_dragon_state == "dragon_compressed");
   if(g_dragonPvsraBlockFlatDragon && flat_dragon)
      return "DP_ENTRY_FLAT_DRAGON";

   bool late_or_trap = (fields.sonic_entry_timing_risk == "late_chase" ||
                       fields.sonic_mm_mode_proxy == "trap_risk" ||
                       fields.source_classic_run_mode_proxy == "trap_risk");
   if(g_dragonPvsraBlockLateChase && late_or_trap)
      return "DP_ENTRY_CHASE_TRAP";

   if(g_dragonPvsraRequirePvsraAlignment)
   {
      bool aligned = ((decision.direction > 0 && ctx.pvsra_bias == "BULLISH") ||
                      (decision.direction < 0 && ctx.pvsra_bias == "BEARISH"));
      if(!aligned)
         return "DP_ENTRY_PVSRA_MISALIGN";
   }

   double min_runway = g_dragonPvsraMinRunwayPips;
   if(_Period == PERIOD_M5 || _Period == PERIOD_M15)
   {
      double atr_pips = (pip_size > 0.0) ? (ctx.atr / pip_size) : 0.0;
      double base_atr = (_Period == PERIOD_M15) ? 12.0 : 5.0;
      double scale = (atr_pips > 0.0) ? (atr_pips / base_atr) : 1.0;
      min_runway = g_dragonPvsraMinRunwayPips * scale;
   }
   double sr_runway_pips = SNR_StateTelemetrySrRunwayPips(fields, decision.direction, pip_size);
   if(min_runway > 0.0 && sr_runway_pips < min_runway)
      return "DP_ENTRY_RUNWAY_LOW";

   if(g_dragonPvsraRequireTrendPullback)
   {
      bool dragon_ready = (fields.sonic_dragon_momentum == "expanding" ||
                           fields.sonic_dragon_momentum == "angled");
      bool trigger_break = (StringFind(fields.source_classic_trigger_state, "break") >= 0);
      bool trend_pullback = ((fields.sonic_story_state == "trigger_ready" ||
                              fields.sonic_mm_mode_proxy == "run_for_profits") &&
                             fields.sonic_wave_quality == "clean" &&
                             dragon_ready &&
                             trigger_break &&
                             fields.sonic_entry_timing_risk != "late_chase");
      if(!trend_pullback)
         return "DP_ENTRY_NOT_TREND_PULLBACK";
   }

   return "";
}

bool SNR_ApplyDragonPvsraEntryProxyGate(const SnrContext &ctx,
                                        SnrDecision &decision)
{
   if(!g_useDragonPvsraEntryProxyGate)
      return false;
   if(!decision.should_trade || decision.direction == SNR_DIR_NONE)
      return false;
   if(!SNR_DragonPvsraEntryProxyMode(decision.mode))
      return false;

   string reason = SNR_DragonPvsraEntryProxyBlockReason(ctx, decision);
   if(reason == "")
      return false;

   decision.should_trade = false;
   decision.block_reason = reason;
   decision.invalidate_reason = reason;
   decision.setup_state = "INVALIDATE";
   return true;
}

void SNR_LogStateTelemetry(const SnrContext &ctx,
                           const SnrDecision &decision,
                           const string setup_type,
                           const string wave_id,
                           const string pre_block_reason,
                           const string post_block_reason,
                           const bool pre_should_trade,
                           const double structure_score,
                           const double htf_score,
                           const double pvsra_score,
                           const double level_score,
                           const double time_safety_score,
                           const double penalty,
                           const double scalp_score,
                           const double classic_score,
                           const double reentry_score,
                           const double min_score)
{
   if(!g_enableTelemetry || !g_enableStateTelemetry)
      return;

   datetime closed_bar = SNR_OpportunityClosedBarTime(ctx);
   string candidate_id = SNR_OpportunityCandidateId(g_snrRunId, closed_bar, setup_type, decision.direction, wave_id);
   int handle = SNR_OpenAppendCsv(g_snrStateTelemetryLogFile);
   if(handle == INVALID_HANDLE)
      return;

   SnrPvsraSrFields state_fields;
   bool state_fields_ok = SNR_BuildPvsraSrFields(SNR_CurrentPipSize(), ctx.atr, state_fields);
   if(state_fields_ok)
   {
      int sonic_direction = (decision.direction != SNR_DIR_NONE ? decision.direction :
                             SNR_SourceClassicEffectiveDirection(SNR_DIR_NONE, state_fields));
      SNR_AnnotateSourceClassicFields(ctx, sonic_direction, state_fields);
      SNR_AnnotateSonicTraderState(ctx, sonic_direction, state_fields);
   }
   double pip_size = SNR_CurrentPipSize();
   double extension_from_dragon_atr = SNR_StateTelemetryExtensionFromDragonAtr(ctx, state_fields, decision.direction);
   double extension_from_break_atr = SNR_StateTelemetryExtensionFromBreakAtr(ctx, state_fields, decision.direction);
   double sr_runway_pips = SNR_StateTelemetrySrRunwayPips(state_fields, decision.direction, pip_size);
   bool retest_dragon_ok = SNR_StateTelemetryRetestDragonOk(ctx, state_fields, decision.direction);
   string sweep_reclaim_side = SNR_StateTelemetrySweepReclaimSide(state_fields);
   double wave_smoothness = SNR_StateTelemetryWaveSmoothness(state_fields, decision.direction);
   double overlap_ratio = SNR_StateTelemetryDragonOverlapRatio(ctx, state_fields);

   FileWrite(handle,
             g_snrRunId,
             candidate_id,
             TimeToString(ctx.decision_time_server, TIME_DATE | TIME_MINUTES | TIME_SECONDS),
             TimeToString(ctx.decision_time_utc, TIME_DATE | TIME_MINUTES | TIME_SECONDS),
             _Symbol,
             EnumToString(_Period),
             TimeToString(closed_bar, TIME_DATE | TIME_MINUTES | TIME_SECONDS),
             SNR_CleanTesterString(g_variantTag),
             setup_type,
             SNR_ModeName(decision.mode),
             SNR_DirectionName(decision.direction),
             wave_id,
             SNR_BoolLabel(g_useOpportunityScoreGate),
             SNR_BoolLabel(pre_should_trade),
             SNR_BoolLabel(decision.should_trade),
             DoubleToString(min_score, 1),
             DoubleToString(scalp_score - min_score, 1),
             DoubleToString(structure_score, 1),
             DoubleToString(htf_score, 1),
             DoubleToString(pvsra_score, 1),
             DoubleToString(level_score, 1),
             DoubleToString(time_safety_score, 1),
             DoubleToString(penalty, 1),
             DoubleToString(scalp_score, 1),
             DoubleToString(classic_score, 1),
             DoubleToString(reentry_score, 1),
             pre_block_reason,
             post_block_reason,
             SNR_StateTelemetryDouble(state_fields_ok, extension_from_dragon_atr, 4),
             SNR_StateTelemetryDouble(state_fields_ok, extension_from_break_atr, 4),
             SNR_StateTelemetryDouble(state_fields_ok, sr_runway_pips, 2),
             SNR_StateTelemetryBool(state_fields_ok, retest_dragon_ok),
             sweep_reclaim_side,
             SNR_StateTelemetryDouble(state_fields_ok, wave_smoothness, 4),
             SNR_StateTelemetryDouble(state_fields_ok, overlap_ratio, 4),
             (state_fields_ok ? state_fields.sonic_story_state : ""),
             (state_fields_ok ? state_fields.sonic_mm_mode_proxy : ""),
             (state_fields_ok ? state_fields.sonic_wave_quality : ""),
             (state_fields_ok ? state_fields.sonic_dragon_momentum : ""),
             (state_fields_ok ? state_fields.sonic_level_story : ""),
             (state_fields_ok ? state_fields.sonic_session_momentum : ""),
             (state_fields_ok ? state_fields.sonic_entry_timing_risk : ""),
             (state_fields_ok ? state_fields.sonic_trade_management_context : ""));
   FileClose(handle);
}

void SNR_ApplyOpportunityScoreGate(const SnrContext &ctx, SnrDecision &decision)
{
   if(!decision.should_trade)
      return;
   if(!g_useOpportunityScoreGate && !g_enableStateTelemetry && !g_useXauClassicStateQualityGate && !g_useFxClassicStateQualityGate && !g_useDragonPvsraEntryProxyGate)
      return;
   if(decision.direction == SNR_DIR_NONE)
      return;
   if(!SNR_OpportunityScoreGateMode(decision.mode) &&
       !SNR_XauClassicStateQualityMode(decision.mode) &&
       !SNR_FxClassicStateQualityMode(decision.mode) &&
       !SNR_DragonPvsraEntryProxyMode(decision.mode))
      return;

   string block_reason = SNR_OpportunityBlockReason(ctx, decision);
   double structure_score = SNR_OpportunityStructureScore(ctx, decision.direction);
   double htf_score = SNR_OpportunityHtfScore(ctx, decision.direction);
   double pvsra_score = SNR_OpportunityPvsraScore(ctx, decision.direction);
   double level_score = SNR_OpportunityLevelScore(ctx);
   double time_safety_score = SNR_OpportunityTimeSafetyScore(ctx);
   double penalty = SNR_OpportunityPenalty(ctx, block_reason);
   double scalp_score = SNR_Clamp(structure_score + htf_score + pvsra_score + level_score + time_safety_score - penalty, 0.0, 100.0);
   double min_score = (decision.mode == SNR_MODE_REENTRY ? (double)g_minReentryOpportunityScore : (double)g_minClassicOpportunityScore);
   double classic_score = SNR_ClassicOpportunityScore(ctx, decision.direction, scalp_score);
   double reentry_score = SNR_ReentryOpportunityScore(ctx, decision.direction, scalp_score);
   string setup_type = SNR_OpportunitySetupType(decision.mode, ctx);
   string wave_id = SNR_OpportunityWaveId(ctx, decision, setup_type, decision.direction);
   bool pre_should_trade = decision.should_trade;

   if(g_useOpportunityScoreGate && scalp_score < min_score)
   {
      decision.should_trade = false;
      decision.block_reason = "OPPORTUNITY_SCORE_LOW";
      decision.invalidate_reason = "OPPORTUNITY_SCORE_LOW";
      decision.setup_state = "INVALIDATE";
   }

   if(decision.should_trade)
      SNR_ApplyXauClassicStateQualityGate(ctx, decision);
   if(decision.should_trade)
      SNR_ApplyFxClassicStateQualityGate(ctx, decision);
   if(decision.should_trade)
      SNR_ApplyDragonPvsraEntryProxyGate(ctx, decision);

   if(g_enableStateTelemetry)
   {
      SNR_LogStateTelemetry(ctx, decision, setup_type, wave_id, block_reason,
                            SNR_OpportunityBlockReason(ctx, decision), pre_should_trade,
                            structure_score, htf_score, pvsra_score, level_score,
                            time_safety_score, penalty, scalp_score, classic_score,
                            reentry_score, min_score);
   }

   if(!g_useOpportunityScoreGate || scalp_score >= min_score)
      return;
}

#endif
