#ifndef SNR_CONTEXT_MQH

#define SNR_CONTEXT_MQH



double SNR_StdDev(const MqlRates &rates[], const int period, const int offset)

{

   if(period <= 0 || offset + period > ArraySize(rates))

      return 0.0;

   

   double sum = 0.0;

   for(int i = 0; i < period; i++)

      sum += rates[offset + i].close;

   double mean = sum / period;

   

   double sum_sq = 0.0;

   for(int i = 0; i < period; i++)

   {

      double diff = rates[offset + i].close - mean;

      sum_sq += diff * diff;

   }

   return MathSqrt(sum_sq / period);

}



void SNR_DetectMarketStructure(const MqlRates &rates[], const int count, const int lookback, const int offset, double &ms_high, double &ms_low)

{

   ms_high = -DBL_MAX;

   ms_low = DBL_MAX;

   

   int limit = MathMin(count - 2 - offset, lookback);

   if(limit < 3)

      limit = 3;

   

   // Quét tìm Swing High/Low cấu trúc SMC (cần có 2 nến 2 bên thấp/cao hơn nến trung tâm)

   double max_high = -DBL_MAX;

   for(int i = 2; i < limit; i++)

   {

      int idx = offset + i;

      if(idx + 2 < count && idx - 2 >= 0)

      {

         if(rates[idx].high > rates[idx+1].high && rates[idx].high > rates[idx+2].high &&

            rates[idx].high > rates[idx-1].high && rates[idx].high > rates[idx-2].high)

         {

            if(rates[idx].high > max_high)

               max_high = rates[idx].high;

         }

      }

   }

   if(max_high != -DBL_MAX)

      ms_high = max_high;

   

   double min_low = DBL_MAX;

   for(int i = 2; i < limit; i++)

   {

      int idx = offset + i;

      if(idx + 2 < count && idx - 2 >= 0)

      {

         if(rates[idx].low < rates[idx+1].low && rates[idx].low < rates[idx+2].low &&

            rates[idx].low < rates[idx-1].low && rates[idx].low < rates[idx-2].low)

         {

            if(rates[idx].low < min_low)

               min_low = rates[idx].low;

         }

      }

   }

   if(min_low != DBL_MAX)

      ms_low = min_low;

   

   // Fallback nếu không tìm thấy swing points theo cấu trúc

   if(ms_high == -DBL_MAX)

   {

      for(int i = 1; i < MathMin(20, count - offset); i++)

         ms_high = MathMax(ms_high, rates[offset + i].high);

   }

   if(ms_low == DBL_MAX)

   {

      for(int i = 1; i < MathMin(20, count - offset); i++)

         ms_low = MathMin(ms_low, rates[offset + i].low);

   }

}



void SNR_DetectLiquiditySweep(const MqlRates &rates[],

                             const SnrPvsraSrFields &fields,

                             const double pip_size,

                             const double ms_high,

                             const double ms_low,

                             bool &sweep_active,

                             int &sweep_direction)

{

   sweep_active = false;

   sweep_direction = 0;

   

   if(pip_size <= 0.0 || !fields.data_available)

      return;

      

   int lookback = g_sweepLookbackBars;

   if(lookback < 1)

      lookback = 1;

   if(lookback > 100)

      lookback = 100;

      

   for(int i = 0; i < lookback; i++)

   {

      double range = rates[i].high - rates[i].low;

      if(range <= 0.0)

         continue;

         

      double body = MathAbs(rates[i].close - rates[i].open);

      double upper_wick = rates[i].high - MathMax(rates[i].open, rates[i].close);

      double lower_wick = MathMin(rates[i].open, rates[i].close) - rates[i].low;

      

      // PVA Climax hoặc tick volume cao cục bộ

      double vol_sum = 0.0;

      int vol_count = 0;

      for(int k = i + 1; k < i + 21 && k < 300; k++)

      {

         vol_sum += (double)rates[k].tick_volume;

         vol_count++;

      }

      double vol_avg = (vol_count > 0) ? (vol_sum / vol_count) : 1.0;

      bool is_climax_i = ((double)rates[i].tick_volume > vol_avg * 1.5);

      

      if(i == 0)

         is_climax_i = is_climax_i || fields.source_pva_climax_200_or_highest_sv;

         

      double whole_level = fields.nearest_whole_price;

      double half_level = fields.nearest_half_price;

      

      // Tính toán ms_high và ms_low cục bộ loại trừ nến i hiện tại (quét từ i+1 trở đi)

      double local_ms_high = -DBL_MAX;

      double local_ms_low = DBL_MAX;

      SNR_DetectMarketStructure(rates, ArraySize(rates), g_smcStructureLookback, i + 1, local_ms_high, local_ms_low);

      

      // Bổ sung Quarter level sweep khi g_levelGridMode == 1

      double quarter_level = 0.0;

      double three_quarter_level = 0.0;

      if(g_levelGridMode == 1)

      {

         double quarter_step = 25.0 * pip_size;

         double base_level = MathFloor(rates[i].close / (100.0 * pip_size)) * (100.0 * pip_size);

         quarter_level = base_level + quarter_step;

         three_quarter_level = base_level + 3.0 * quarter_step;

      }

      

      // Bullish Liquidity Sweep

      bool swept_ms_low = (rates[i].low < local_ms_low && rates[i].close > local_ms_low);

      bool swept_whole = (rates[i].low < whole_level && rates[i].close > whole_level && MathAbs(local_ms_low - whole_level)/pip_size < 10.0);

      bool swept_half = (rates[i].low < half_level && rates[i].close > half_level && MathAbs(local_ms_low - half_level)/pip_size < 10.0);

      bool swept_quarter = false;

      bool swept_three_quarter = false;

      if(g_levelGridMode == 1)

      {

         swept_quarter = (rates[i].low < quarter_level && rates[i].close > quarter_level && MathAbs(local_ms_low - quarter_level)/pip_size < 10.0);

         swept_three_quarter = (rates[i].low < three_quarter_level && rates[i].close > three_quarter_level && MathAbs(local_ms_low - three_quarter_level)/pip_size < 10.0);

      }

      

      if((swept_ms_low || swept_whole || swept_half || swept_quarter || swept_three_quarter) && lower_wick > body * 1.2 && lower_wick > 0.4 * range && is_climax_i)

      {

         sweep_active = true;

         sweep_direction = 1; // Bullish sweep

         return;

      }

      

      // Bearish Liquidity Sweep

      bool swept_ms_high = (rates[i].high > local_ms_high && rates[i].close < local_ms_high);

      bool swept_whole_high = (rates[i].high > whole_level && rates[i].close < whole_level && MathAbs(local_ms_high - whole_level)/pip_size < 10.0);

      bool swept_half_high = (rates[i].high > half_level && rates[i].close < half_level && MathAbs(local_ms_high - half_level)/pip_size < 10.0);

      bool swept_quarter_high = false;

      bool swept_three_quarter_high = false;

      if(g_levelGridMode == 1)

      {

         swept_quarter_high = (rates[i].high > quarter_level && rates[i].close < quarter_level && MathAbs(local_ms_high - quarter_level)/pip_size < 10.0);

         swept_three_quarter_high = (rates[i].high > three_quarter_level && rates[i].close < three_quarter_level && MathAbs(local_ms_high - three_quarter_level)/pip_size < 10.0);

      }

      

      if((swept_ms_high || swept_whole_high || swept_half_high || swept_quarter_high || swept_three_quarter_high) && upper_wick > body * 1.2 && upper_wick > 0.4 * range && is_climax_i)

      {

         sweep_active = true;

         sweep_direction = -1; // Bearish sweep

         return;

      }

   }

}



bool SNR_CopyClosedRates(const int count, MqlRates &rates[])

{

   ArraySetAsSeries(rates, true);

   return (CopyRates(_Symbol, PERIOD_CURRENT, 1, count, rates) >= count);

}



bool SNR_CopyClosedBuffer(const int handle, const int count, double &buffer[])

{

   ArraySetAsSeries(buffer, true);

   return (CopyBuffer(handle, 0, 1, count, buffer) >= count);

}



double SNR_CalcVolumePercentile(const MqlRates &rates[], const int bars_count)

{

   if(bars_count <= 1)

      return 0.0;



   long current = (long)rates[0].tick_volume;

   int less_or_equal = 0;

   for(int i = 0; i < bars_count; i++)

   {

      if((long)rates[i].tick_volume <= current)

         less_or_equal++;

   }

   return 100.0 * (double)less_or_equal / (double)bars_count;

}



double SNR_CalcRecentAccumBias(const MqlRates &rates[],

                               const int bars_count,

                               const double &dragon_mid[],

                               const double &atr[])

{

   if(bars_count < 8)

      return 0.0;



   double bull_score = 0.0;

   double bear_score = 0.0;



   for(int i = 1; i < MathMin(bars_count, 7); i++)

   {

      double range = rates[i].high - rates[i].low;

      if(range <= 0.0)

         continue;



      double close_location = (rates[i].close - rates[i].low) / range;

      double vol_weight = (double)rates[i].tick_volume / MathMax(1.0, (double)rates[i + 1].tick_volume);



      bool near_lower = (rates[i].low <= dragon_mid[i] + 0.20 * atr[i]);

      bool near_upper = (rates[i].high >= dragon_mid[i] - 0.20 * atr[i]);



      if(near_lower && close_location >= 0.55)

         bull_score += vol_weight;

      if(near_upper && close_location <= 0.45)

         bear_score += vol_weight;

   }



   return bull_score - bear_score;

}



int SNR_IntensityPvsraGrade(const double tick_volume_percentile,

                            const double body_ratio,

                            const double bar_range_atr,

                            const string level_zone)

{

   int grade = 0;

   if(tick_volume_percentile >= 65.0)

      grade++;

   if(tick_volume_percentile >= 85.0)

      grade++;

   if(body_ratio >= 0.55)

      grade++;

   if(bar_range_atr >= 0.90)

      grade++;

   if(level_zone != "NONE")

      grade++;

   return grade;

}



string SNR_DragonAngleClass(const double slope_atr)

{

   double abs_slope = MathAbs(slope_atr);

   if(abs_slope >= 0.60)

      return "STEEP";

   if(abs_slope >= g_minDragonSlopeATR)

      return "ANGLED";

   return "FLAT";

}



string SNR_PvsraEventName(const double tick_volume_percentile,

                          const double body_ratio,

                          const double bar_range_atr)

{

   if(tick_volume_percentile >= 85.0 && bar_range_atr >= 0.90)

      return "CLIMAX";

   if(tick_volume_percentile >= 65.0)

      return "RISING_ACTIVITY";

   if(body_ratio >= 0.65 && bar_range_atr >= 0.80)

      return "WIDE_BODY";

   return "NONE";

}



string SNR_SourcePvaEventName(const bool source_climax,

                              const bool source_rising)

{

   if(source_climax)

      return "CLIMAX";

   if(source_rising)

      return "RISING_ACTIVITY";

   return "NONE";

}



int SNR_SourcePvaGrade(const bool source_climax,

                       const bool source_rising)

{

   if(source_climax)

      return 5;

   if(source_rising)

      return 3;

   return 0;

}



string SNR_PvsraBiasName(const double recent_accum_bias)

{

   if(recent_accum_bias > 0.40)

      return "BULLISH";

   if(recent_accum_bias < -0.40)

      return "BEARISH";

   return "NEUTRAL";

}



int SNR_DirectionalPvsraGrade(const SnrContext &ctx, const int direction)

{

   int grade = ctx.pvsra_grade;

   if(direction > 0 && ctx.recent_accum_bias > 0.40)

      grade++;

   if(direction < 0 && ctx.recent_accum_bias < -0.40)

      grade++;

   return MathMin(5, grade);

}



void SNR_DetectLevelZone(const double price,

                         const double pip_size,

                         string &zone,

                         double &distance_pips)

{

   double whole_step = 100.0 * pip_size;

   double half_step  = 50.0 * pip_size;



   double whole_ref = MathRound(price / whole_step) * whole_step;

   double half_ref  = MathRound(price / half_step) * half_step;



   double whole_dist = MathAbs(price - whole_ref) / pip_size;

   double half_dist  = MathAbs(price - half_ref) / pip_size;



   zone = "NONE";

   distance_pips = MathMin(whole_dist, half_dist);



   if(g_levelGridMode == 1)

   {

      double quarter_step = 25.0 * pip_size;

      int nearest_steps = (int)MathRound(price / quarter_step);

      double quarter_ref = (double)nearest_steps * quarter_step;

      double quarter_dist = MathAbs(price - quarter_ref) / pip_size;

      int mod = nearest_steps % 4;

      if(mod < 0)

         mod += 4;



      distance_pips = quarter_dist;

      if(mod == 0 && quarter_dist <= g_wholeLevelRadiusPips)

      {

         zone = "WHOLE";

         return;

      }

      if(quarter_dist <= g_halfLevelRadiusPips)

      {

         if(mod == 2)

            zone = "HALF";

         else if(mod == 1)

            zone = "QUARTER";

         else

            zone = "THREE_QUARTER";

         return;

      }



      zone = "NONE";

      return;

   }



   if(whole_dist <= g_wholeLevelRadiusPips)

   {

      zone = "WHOLE";

      distance_pips = whole_dist;

      return;

   }



   if(half_dist <= g_halfLevelRadiusPips)

   {

      zone = "HALF";

      distance_pips = half_dist;

   }

}



bool SNR_ValueInsideRange(const double value, const double a, const double b)

{

   return (value >= MathMin(a, b) && value <= MathMax(a, b));

}



string SNR_GridRejectionSide(const double level, const MqlRates &bar)

{

   double body_high = MathMax(bar.open, bar.close);

   double body_low = MathMin(bar.open, bar.close);

   if(SNR_ValueInsideRange(level, body_low, body_high))

      return "BODY";

   if(level > body_high && level <= bar.high)

      return "UPPER_WICK";

   if(level < body_low && level >= bar.low)

      return "LOWER_WICK";

   return (level >= bar.close ? "ABOVE_CLOSE" : "BELOW_CLOSE");

}



string SNR_SourceSrLevelKindFromStep(const int nearest_steps)

{

   int mod = nearest_steps % 4;

   if(mod < 0)

      mod += 4;



   if(mod == 0)

      return "WHOLE";

   if(mod == 2)

      return "HALF";

   if(mod == 1)

      return "QUARTER";

   return "THREE_QUARTER";

}



bool SNR_SourceSrNearestLevel(const double price,

                              const double pip_size,

                              string &level_kind,

                              double &level_price,

                              double &distance_pips)

{

   level_kind = "UNKNOWN";

   level_price = 0.0;

   distance_pips = 0.0;

   if(pip_size <= 0.0)

      return false;



   const double quarter_step = 25.0 * pip_size;

   if(quarter_step <= 0.0)

      return false;



   int nearest_steps = (int)MathRound(price / quarter_step);

   level_price = (double)nearest_steps * quarter_step;

   distance_pips = MathAbs(price - level_price) / pip_size;

   level_kind = SNR_SourceSrLevelKindFromStep(nearest_steps);

   return true;

}



double SNR_SourceSrRunwayPips(const MqlRates &bar, const double pip_size)

{

   if(pip_size <= 0.0)

      return 0.0;



   const double quarter_step = 25.0 * pip_size;

   if(quarter_step <= 0.0)

      return 0.0;



   double steps = bar.close / quarter_step;

   double next_above = MathCeil(steps) * quarter_step;

   if(next_above <= bar.close)

      next_above += quarter_step;



   double next_below = MathFloor(steps) * quarter_step;

   if(next_below >= bar.close)

      next_below -= quarter_step;



   double up_pips = MathAbs(next_above - bar.close) / pip_size;

   double down_pips = MathAbs(bar.close - next_below) / pip_size;



   if(bar.close > bar.open)

      return up_pips;

   if(bar.close < bar.open)

      return down_pips;

   return MathMin(up_pips, down_pips);

}



int SNR_SourceSrGrade(const string level_kind,

                      const string interaction,

                      const double runway_pips)

{

   int grade = 0;

   if(level_kind == "WHOLE")

      grade = 3;

   else if(level_kind == "HALF")

      grade = 2;

   else if(level_kind == "QUARTER" || level_kind == "THREE_QUARTER")

      grade = 1;



   if(interaction == "BODY_CROSS")

      grade += 2;

   else if(interaction == "REJECTION" || interaction == "TOUCH")

      grade += 1;

   else if(interaction == "NEAR" && runway_pips <= 5.0)

      grade += 1;



   return MathMin(5, grade);

}



void SNR_CalcSourceSrInteraction(const MqlRates &bar,

                                 const double pip_size,

                                 string &level_kind,

                                 string &interaction,

                                 string &rejection_side,

                                 double &runway_pips,

                                 int &grade)

{

   level_kind = "UNKNOWN";

   interaction = "DATA_UNAVAILABLE";

   rejection_side = "NONE";

   runway_pips = 0.0;

   grade = 0;



   double level_price = 0.0;

   double distance_pips = 0.0;

   if(!SNR_SourceSrNearestLevel(bar.close, pip_size, level_kind, level_price, distance_pips))

      return;



   double body_high = MathMax(bar.open, bar.close);

   double body_low = MathMin(bar.open, bar.close);

   bool inside_body = SNR_ValueInsideRange(level_price, body_low, body_high);

   bool inside_range = SNR_ValueInsideRange(level_price, bar.low, bar.high);



   if(inside_body)

      interaction = "BODY_CROSS";

   else if(inside_range)

   {

      if((level_price > body_high && level_price <= bar.high) ||

         (level_price < body_low && level_price >= bar.low))

         interaction = "REJECTION";

      else

         interaction = "TOUCH";

   }

   else if(distance_pips <= MathMax(g_wholeLevelRadiusPips, g_halfLevelRadiusPips))

      interaction = "NEAR";

   else

      interaction = "RUNWAY";



   if(interaction == "BODY_CROSS" || interaction == "REJECTION" || interaction == "TOUCH")

      rejection_side = SNR_GridRejectionSide(level_price, bar);

   else if(interaction == "NEAR")

      rejection_side = (level_price >= bar.close ? "ABOVE_CLOSE" : "BELOW_CLOSE");



   runway_pips = SNR_SourceSrRunwayPips(bar, pip_size);

   grade = SNR_SourceSrGrade(level_kind, interaction, runway_pips);

}



int SNR_SourceClassicEffectiveDirection(const int direction,

                                        const SnrPvsraSrFields &fields)

{

   if(direction != SNR_DIR_NONE)

      return direction;

   if(fields.seq_5_close_delta_pips > 0.0)

      return SNR_DIR_LONG;

   if(fields.seq_5_close_delta_pips < 0.0)

      return SNR_DIR_SHORT;

   if(fields.bar_close > fields.bar_open)

      return SNR_DIR_LONG;

   if(fields.bar_close < fields.bar_open)

      return SNR_DIR_SHORT;

   return SNR_DIR_NONE;

}



void SNR_ResetSourceClassicFields(SnrPvsraSrFields &fields)

{

   fields.source_classic_wave_state = "unknown";

   fields.source_classic_wave_smoothness = 0.0;

   fields.source_classic_dragon_state = "unknown";

   fields.source_classic_dragon_expansion = 0.0;

   fields.source_classic_dragon_edge_distance_pips = 0.0;

   fields.source_h4_target_runway_pips = 0.0;

   fields.source_h4_target_kind = "NONE";

   fields.source_h4_target_price = 0.0;

   fields.source_h4_target_status = "disabled";

   fields.source_mtf_pva_status = "disabled";

   fields.source_mtf_pva_h4_state = "disabled";

   fields.source_mtf_pva_h1_state = "disabled";

   fields.source_mtf_pva_m15_state = "disabled";

   fields.source_mtf_pva_stop_volume_near_whq = "disabled";

   fields.source_mtf_pva_direction_agreement = "disabled";

   fields.source_mtf_pva_notes = "";

   fields.source_classic_trigger_state = "unknown";

   fields.source_classic_chase_risk = "unknown";

   fields.source_classic_session_runway = "unknown";

   fields.source_classic_run_mode_proxy = "unknown";

}



void SNR_ResetSonicTraderStateFields(SnrPvsraSrFields &fields)

{

   fields.sonic_story_state = "observe";

   fields.sonic_mm_mode_proxy = "unknown";

   fields.sonic_wave_quality = "unclear";

   fields.sonic_dragon_momentum = "unknown";

   fields.sonic_level_story = "unknown";

   fields.sonic_session_momentum = "unknown";

   fields.sonic_entry_timing_risk = "unknown";

   fields.sonic_trade_management_context = "unknown";

   fields.sonic_replay_20_close_delta_pips = 0.0;

   fields.sonic_replay_20_range_atr = 0.0;

   fields.sonic_replay_60_range_atr = 0.0;

   fields.sonic_replay_20_pva_count = 0;

   fields.sonic_replay_20_whq_touch_count = 0;

}



void SNR_CopySourceClassicFieldsToContext(const SnrPvsraSrFields &fields,

                                          SnrContext &ctx)

{

   ctx.source_classic_wave_state = fields.source_classic_wave_state;

   ctx.source_classic_wave_smoothness = fields.source_classic_wave_smoothness;

   ctx.source_classic_dragon_state = fields.source_classic_dragon_state;

   ctx.source_classic_dragon_expansion = fields.source_classic_dragon_expansion;

   ctx.source_classic_dragon_edge_distance_pips = fields.source_classic_dragon_edge_distance_pips;

   ctx.source_h4_target_runway_pips = fields.source_h4_target_runway_pips;

   ctx.source_h4_target_kind = fields.source_h4_target_kind;

   ctx.source_h4_target_price = fields.source_h4_target_price;

   ctx.source_h4_target_status = fields.source_h4_target_status;

   ctx.source_mtf_pva_status = fields.source_mtf_pva_status;

   ctx.source_mtf_pva_h4_state = fields.source_mtf_pva_h4_state;

   ctx.source_mtf_pva_h1_state = fields.source_mtf_pva_h1_state;

   ctx.source_mtf_pva_m15_state = fields.source_mtf_pva_m15_state;

   ctx.source_mtf_pva_stop_volume_near_whq = fields.source_mtf_pva_stop_volume_near_whq;

   ctx.source_mtf_pva_direction_agreement = fields.source_mtf_pva_direction_agreement;

   ctx.source_mtf_pva_notes = fields.source_mtf_pva_notes;

   ctx.source_classic_trigger_state = fields.source_classic_trigger_state;

   ctx.source_classic_chase_risk = fields.source_classic_chase_risk;

   ctx.source_classic_session_runway = fields.source_classic_session_runway;

   ctx.source_classic_run_mode_proxy = fields.source_classic_run_mode_proxy;

}



void SNR_CopySonicTraderStateFieldsToContext(const SnrPvsraSrFields &fields,

                                             SnrContext &ctx)

{

   ctx.sonic_story_state = fields.sonic_story_state;

   ctx.sonic_mm_mode_proxy = fields.sonic_mm_mode_proxy;

   ctx.sonic_wave_quality = fields.sonic_wave_quality;

   ctx.sonic_dragon_momentum = fields.sonic_dragon_momentum;

   ctx.sonic_level_story = fields.sonic_level_story;

   ctx.sonic_session_momentum = fields.sonic_session_momentum;

   ctx.sonic_entry_timing_risk = fields.sonic_entry_timing_risk;

   ctx.sonic_trade_management_context = fields.sonic_trade_management_context;

}



void SNR_AnnotateSourceH4TargetRunwayFields(const int direction,

                                            const double pip_size,

                                            SnrPvsraSrFields &fields)

{

   fields.source_h4_target_runway_pips = 0.0;

   fields.source_h4_target_kind = "NONE";

   fields.source_h4_target_price = 0.0;

   fields.source_h4_target_status = "DATA_UNAVAILABLE";



   if(!fields.data_available)

      return;

   if(direction == SNR_DIR_NONE)

   {

      fields.source_h4_target_status = "NO_DIRECTION";

      return;

   }

   if(pip_size <= 0.0 || fields.bar_close <= 0.0)

   {

      fields.source_h4_target_status = "BAD_INPUT";

      return;

   }



   const int h4_lookback = 40;

   MqlRates h4_rates[];

   ArraySetAsSeries(h4_rates, true);

   int copied = CopyRates(_Symbol, PERIOD_H4, 1, h4_lookback, h4_rates);

   if(copied < 10)

   {

      fields.source_h4_target_status = "H4_DATA_UNAVAILABLE";

      return;

   }



   bool found = false;

   double best_price = 0.0;

   double best_distance_pips = DBL_MAX;

   for(int i = 0; i < copied; i++)

   {

      double candidate_price = (direction > 0 ? h4_rates[i].high : h4_rates[i].low);

      double distance_pips = 0.0;

      if(direction > 0 && candidate_price > fields.bar_close)

         distance_pips = (candidate_price - fields.bar_close) / pip_size;

      else if(direction < 0 && candidate_price < fields.bar_close)

         distance_pips = (fields.bar_close - candidate_price) / pip_size;

      else

         continue;



      if(distance_pips > 0.0 && distance_pips < best_distance_pips)

      {

         best_distance_pips = distance_pips;

         best_price = candidate_price;

         found = true;

      }

   }



   if(!found)

   {

      fields.source_h4_target_status = (direction > 0 ? "NO_H4_RESISTANCE_AHEAD" : "NO_H4_SUPPORT_AHEAD");

      return;

   }



   fields.source_h4_target_runway_pips = best_distance_pips;

   fields.source_h4_target_kind = (direction > 0 ? "H4_SWING_HIGH_40" : "H4_SWING_LOW_40");

   fields.source_h4_target_price = NormalizeDouble(best_price, _Digits);

   fields.source_h4_target_status = (copied >= h4_lookback ? "OK" : "OK_PARTIAL_H4_LOOKBACK");

}



double SNR_QuarterGridDistancePips(const double price, const double pip_size)

{

   if(price <= 0.0 || pip_size <= 0.0)

      return DBL_MAX;



   double quarter_step = 25.0 * pip_size;

   if(quarter_step <= 0.0)

      return DBL_MAX;



   double nearest_quarter = MathRound(price / quarter_step) * quarter_step;

   return MathAbs(price - nearest_quarter) / pip_size;

}



bool SNR_SourcePvaNotableAtOffset(const MqlRates &rates[],

                                  const int copied,

                                  const int offset)

{

   if(offset < 0 || offset + 10 >= copied)

      return false;



   double current_volume = (double)rates[offset].tick_volume;

   double current_spread_volume = current_volume * MathMax(0.0, rates[offset].high - rates[offset].low);

   double volume_sum = 0.0;

   double highest_spread_volume = 0.0;



   for(int i = offset + 1; i <= offset + 10; i++)

   {

      double historical_volume = (double)rates[i].tick_volume;

      volume_sum += historical_volume;

      double historical_spread_volume = historical_volume * MathMax(0.0, rates[i].high - rates[i].low);

      highest_spread_volume = MathMax(highest_spread_volume, historical_spread_volume);

   }



   double avg_10 = volume_sum / 10.0;

   return ((avg_10 > 0.0 && current_volume >= avg_10 * 1.50) ||

           (highest_spread_volume > 0.0 && current_spread_volume >= highest_spread_volume));

}



bool SNR_SourcePvaNearWhqAtOffset(const MqlRates &rates[],

                                  const int copied,

                                  const int offset,

                                  const double pip_size)

{

   if(!SNR_SourcePvaNotableAtOffset(rates, copied, offset))

      return false;



   double min_dist = SNR_QuarterGridDistancePips(rates[offset].close, pip_size);

   min_dist = MathMin(min_dist, SNR_QuarterGridDistancePips(rates[offset].high, pip_size));

   min_dist = MathMin(min_dist, SNR_QuarterGridDistancePips(rates[offset].low, pip_size));

   return (min_dist <= 5.0);

}



string SNR_MtfPvaWeakeningState(const MqlRates &rates[],

                                const int copied,

                                const int lookback,

                                const int direction)

{

   if(direction == SNR_DIR_NONE)

      return "no_direction";

   if(copied < 12 || lookback < 2)

      return "data_unavailable";



   bool target_bull = (direction < 0);

   int limit = (lookback < copied ? lookback : copied);

   int seen = 0;

   double latest_volume = 0.0;

   double previous_volume = 0.0;



   for(int i = 0; i < limit; i++)

   {

      bool bull_bar = (rates[i].close > rates[i].open);

      bool bear_bar = (rates[i].close < rates[i].open);

      bool target_bar = (target_bull ? bull_bar : bear_bar);

      if(!target_bar)

         continue;



      if(seen == 0)

         latest_volume = (double)rates[i].tick_volume;

      else if(seen == 1)

      {

         previous_volume = (double)rates[i].tick_volume;

         break;

      }

      seen++;

   }



   if(seen < 1 || previous_volume <= 0.0)

      return "insufficient_target_bars";

   if(latest_volume < previous_volume)

      return "weakening";

   if(latest_volume > previous_volume)

      return "strengthening";

   return "flat";

}



bool SNR_MtfPvaHasStopVolumeNearWhq(const MqlRates &rates[],

                                    const int copied,

                                    const int lookback,

                                    const double pip_size)

{

   if(copied < 12 || pip_size <= 0.0)

      return false;



   int limit = (lookback < copied ? lookback : copied);

   for(int i = 0; i < limit; i++)

   {

      if(SNR_SourcePvaNearWhqAtOffset(rates, copied, i, pip_size))

         return true;

   }

   return false;

}



void SNR_AnnotateFxM15MtfPvaWeakeningFields(const int direction,

                                            const double pip_size,

                                            SnrPvsraSrFields &fields)

{

   fields.source_mtf_pva_status = "DATA_UNAVAILABLE";

   fields.source_mtf_pva_h4_state = "data_unavailable";

   fields.source_mtf_pva_h1_state = "data_unavailable";

   fields.source_mtf_pva_m15_state = "data_unavailable";

   fields.source_mtf_pva_stop_volume_near_whq = "none";

   fields.source_mtf_pva_direction_agreement = "unknown";

   fields.source_mtf_pva_notes = "";



   if(direction == SNR_DIR_NONE)

   {

      fields.source_mtf_pva_status = "NO_DIRECTION";

      fields.source_mtf_pva_direction_agreement = "no_direction";

      return;

   }

   if(pip_size <= 0.0)

   {

      fields.source_mtf_pva_status = "BAD_INPUT";

      return;

   }



   MqlRates h4_rates[];

   MqlRates h1_rates[];

   MqlRates m15_rates[];

   ArraySetAsSeries(h4_rates, true);

   ArraySetAsSeries(h1_rates, true);

   ArraySetAsSeries(m15_rates, true);



   int h4_copied = CopyRates(_Symbol, PERIOD_H4, 1, 20, h4_rates);

   int h1_copied = CopyRates(_Symbol, PERIOD_H1, 1, 24, h1_rates);

   int m15_copied = CopyRates(_Symbol, PERIOD_M15, 1, 32, m15_rates);



   fields.source_mtf_pva_h4_state = SNR_MtfPvaWeakeningState(h4_rates, h4_copied, 3, direction);

   fields.source_mtf_pva_h1_state = SNR_MtfPvaWeakeningState(h1_rates, h1_copied, 5, direction);

   fields.source_mtf_pva_m15_state = SNR_MtfPvaWeakeningState(m15_rates, m15_copied, 8, direction);



   bool h4_stop = SNR_MtfPvaHasStopVolumeNearWhq(h4_rates, h4_copied, 3, pip_size);

   bool h1_stop = SNR_MtfPvaHasStopVolumeNearWhq(h1_rates, h1_copied, 5, pip_size);

   if(h4_stop && h1_stop)

      fields.source_mtf_pva_stop_volume_near_whq = "h4_h1";

   else if(h4_stop)

      fields.source_mtf_pva_stop_volume_near_whq = "h4";

   else if(h1_stop)

      fields.source_mtf_pva_stop_volume_near_whq = "h1";



   int weakening_count = 0;

   int strengthening_count = 0;

   if(fields.source_mtf_pva_h4_state == "weakening") weakening_count++;

   if(fields.source_mtf_pva_h1_state == "weakening") weakening_count++;

   if(fields.source_mtf_pva_m15_state == "weakening") weakening_count++;

   if(fields.source_mtf_pva_h4_state == "strengthening") strengthening_count++;

   if(fields.source_mtf_pva_h1_state == "strengthening") strengthening_count++;

   if(fields.source_mtf_pva_m15_state == "strengthening") strengthening_count++;



   if(weakening_count >= 2)

      fields.source_mtf_pva_direction_agreement = "weakening_agreement";

   else if(weakening_count == 1 && strengthening_count == 0)

      fields.source_mtf_pva_direction_agreement = "weakening_partial";

   else if(strengthening_count >= 2)

      fields.source_mtf_pva_direction_agreement = "strengthening_conflict";

   else

      fields.source_mtf_pva_direction_agreement = "mixed";



   fields.source_mtf_pva_status = ((h4_copied >= 12 && h1_copied >= 12 && m15_copied >= 12) ? "OK" : "PARTIAL_DATA");

   fields.source_mtf_pva_notes = StringFormat("dir=%s;weak=%d;strong=%d;stop=%s",

                                              SNR_DirectionName(direction),

                                              weakening_count,

                                              strengthening_count,

                                              fields.source_mtf_pva_stop_volume_near_whq);

}



void SNR_AnnotateSourceClassicFields(const SnrContext &ctx,

                                     const int direction,

                                     SnrPvsraSrFields &fields)

{

   SNR_ResetSourceClassicFields(fields);

   if(!fields.data_available || ctx.atr <= 0.0)

      return;



   const int effective_direction = SNR_SourceClassicEffectiveDirection(direction, fields);

   const bool long_side = (effective_direction > 0);

   const bool short_side = (effective_direction < 0);

    MqlRates rates[];

    if(SNR_CopyClosedRates(15, rates))

    {

       int same_side_count_15 = 0;

       for(int i = 0; i < 15; i++)

       {

          if(long_side && rates[i].close > rates[i].open)

             same_side_count_15++;

          else if(short_side && rates[i].close < rates[i].open)

             same_side_count_15++;

       }

       fields.source_classic_wave_smoothness = SNR_Clamp((double)same_side_count_15 / 15.0, 0.0, 1.0);

    }

    else

    {

       const double same_side_count = (long_side ? (double)fields.seq_5_bull_count :

                                      (short_side ? (double)fields.seq_5_bear_count : 0.0));

       fields.source_classic_wave_smoothness = SNR_Clamp(same_side_count / 5.0, 0.0, 1.0);

    }



   const bool aligned_delta = ((long_side && fields.seq_5_close_delta_pips > 0.0) ||

                               (short_side && fields.seq_5_close_delta_pips < 0.0));

   const bool two_sided = (fields.seq_5_bull_count >= 2 && fields.seq_5_bear_count >= 2);

   if(fields.source_classic_wave_smoothness >= 0.60 && aligned_delta && fields.seq_5_net_range_atr >= 0.70)

      fields.source_classic_wave_state = "clean_classic";

   else if(two_sided && fields.seq_5_net_range_atr <= 1.40)

      fields.source_classic_wave_state = "choppy_cross";

   else if(fields.seq_5_net_range_atr <= 0.45)

      fields.source_classic_wave_state = "overlap";

   else

      fields.source_classic_wave_state = "unclear";



   fields.source_classic_dragon_expansion = MathAbs(ctx.dragon_high - ctx.dragon_low) / ctx.atr;

   const double abs_dragon_slope = MathAbs(ctx.dragon_slope_atr);

   if(abs_dragon_slope < 0.08)

      fields.source_classic_dragon_state = "dragon_flat";

   else if(fields.source_classic_dragon_expansion < 0.25)

      fields.source_classic_dragon_state = "dragon_compressed";

   else if(abs_dragon_slope >= g_minDragonSlopeATR && fields.source_classic_dragon_expansion >= 0.35)

      fields.source_classic_dragon_state = "dragon_expanding";

   else

      fields.source_classic_dragon_state = "dragon_angled";



   const double pip_size = SNR_CurrentPipSize();

   if(g_enableSourceClassicDragonEdgeDistanceTelemetry && pip_size > 0.0)

   {

      if(long_side)

         fields.source_classic_dragon_edge_distance_pips = (fields.bar_close - ctx.dragon_high) / pip_size;

      else if(short_side)

         fields.source_classic_dragon_edge_distance_pips = (ctx.dragon_low - fields.bar_close) / pip_size;

   }



   if(g_enableSourceH4TargetRunwayTelemetry)

      SNR_AnnotateSourceH4TargetRunwayFields(effective_direction, pip_size, fields);



   if(g_enableFxM15MtfPvaWeakeningTelemetry)

      SNR_AnnotateFxM15MtfPvaWeakeningFields(effective_direction, pip_size, fields);



   const bool dragon_break = ((long_side && fields.bar_close > ctx.dragon_high) ||

                              (short_side && fields.bar_close < ctx.dragon_low));

   const bool swing_break = ((long_side && fields.closes_above_prior_swing_high) ||

                             (short_side && fields.closes_below_prior_swing_low));

   if(dragon_break && swing_break)

      fields.source_classic_trigger_state = "dragon_and_swing_break";

   else if(dragon_break)

      fields.source_classic_trigger_state = "dragon_break";

   else if(swing_break)

      fields.source_classic_trigger_state = "swing_break";

   else

      fields.source_classic_trigger_state = "no_trigger";



   double extension_from_dragon_atr = 0.0;

   if(long_side)

      extension_from_dragon_atr = (fields.bar_close - ctx.dragon_mid) / ctx.atr;

   else if(short_side)

      extension_from_dragon_atr = (ctx.dragon_mid - fields.bar_close) / ctx.atr;



   if(!dragon_break && !swing_break)

      fields.source_classic_chase_risk = "unknown";

   else if(extension_from_dragon_atr <= 0.25)

      fields.source_classic_chase_risk = "early";

   else if(extension_from_dragon_atr <= 1.00)

      fields.source_classic_chase_risk = "mature";

   else

      fields.source_classic_chase_risk = "late_chase";



   if(ctx.session_bucket == "OFF")

      fields.source_classic_session_runway = "off_session";

   else if(ctx.minutes_to_forced_flat < g_minMinutesToNewTrade)

      fields.source_classic_session_runway = "blocked";

   else if(ctx.minutes_to_forced_flat < g_minMinutesToNewTrade * 2)

      fields.source_classic_session_runway = "limited";

   else

      fields.source_classic_session_runway = "clear";



   const bool pva_notable = (fields.source_pva_event == "CLIMAX" ||

                             fields.source_pva_event == "RISING_ACTIVITY");

   const bool sr_blocked = (fields.source_sr_interaction == "NEAR" ||

                            fields.source_sr_interaction == "REJECTION" ||

                            fields.source_sr_interaction == "BODY_CROSS" ||

                            fields.source_sr_interaction == "TOUCH" ||

                            fields.source_sr_runway_pips < 5.0);

   const bool dragon_ready = (fields.source_classic_dragon_state == "dragon_expanding" ||

                              fields.source_classic_dragon_state == "dragon_angled");

   const bool runway_ok = (fields.source_sr_interaction == "RUNWAY" &&

                           fields.source_sr_runway_pips >= 15.0);

   if(fields.source_classic_chase_risk == "late_chase" && pva_notable)

      fields.source_classic_run_mode_proxy = "trap_risk";

   else if(sr_blocked && pva_notable && !aligned_delta)

      fields.source_classic_run_mode_proxy = "position_building_proxy";

   else if(runway_ok && aligned_delta && dragon_ready && fields.source_classic_chase_risk != "late_chase")

      fields.source_classic_run_mode_proxy = "run_for_profits_proxy";

   else

      fields.source_classic_run_mode_proxy = "unknown";

}



void SNR_AnnotateSonicTraderState(const SnrContext &ctx,

                                  const int direction,

                                  SnrPvsraSrFields &fields)

{

   const double replay_20_close_delta_pips = fields.sonic_replay_20_close_delta_pips;

   const double replay_20_range_atr = fields.sonic_replay_20_range_atr;

   const double replay_60_range_atr = fields.sonic_replay_60_range_atr;

   const int replay_20_pva_count = fields.sonic_replay_20_pva_count;

   const int replay_20_whq_touch_count = fields.sonic_replay_20_whq_touch_count;

   SNR_ResetSonicTraderStateFields(fields);

   fields.sonic_replay_20_close_delta_pips = replay_20_close_delta_pips;

   fields.sonic_replay_20_range_atr = replay_20_range_atr;

   fields.sonic_replay_60_range_atr = replay_60_range_atr;

   fields.sonic_replay_20_pva_count = replay_20_pva_count;

   fields.sonic_replay_20_whq_touch_count = replay_20_whq_touch_count;

   if(!fields.data_available || ctx.atr <= 0.0)

      return;



   const int effective_direction = SNR_SourceClassicEffectiveDirection(direction, fields);

   const bool directional_candidate = (direction != SNR_DIR_NONE);

   const bool long_side = (effective_direction > 0);

   const bool short_side = (effective_direction < 0);

   const bool aligned_replay = ((long_side && fields.sonic_replay_20_close_delta_pips > 0.0) ||

                                (short_side && fields.sonic_replay_20_close_delta_pips < 0.0));

   const bool pva_notable = (fields.source_pva_event == "CLIMAX" ||

                             fields.source_pva_event == "RISING_ACTIVITY" ||

                             fields.sonic_replay_20_pva_count >= 3);

   const bool dragon_ready = (fields.source_classic_dragon_state == "dragon_expanding" ||

                              fields.source_classic_dragon_state == "dragon_angled");

   const bool clean_wave = (fields.source_classic_wave_state == "clean_classic" &&

                            fields.source_classic_wave_smoothness >= 0.60);

   const bool trigger_break = (StringFind(fields.source_classic_trigger_state, "break") >= 0);

   const bool clear_runway = (fields.source_sr_interaction == "RUNWAY" &&

                              fields.source_sr_runway_pips >= 15.0);

   const bool near_or_through_level = (fields.source_sr_interaction == "NEAR" ||

                                      fields.source_sr_interaction == "TOUCH" ||

                                      fields.source_sr_interaction == "REJECTION" ||

                                      fields.source_sr_interaction == "BODY_CROSS" ||

                                      fields.sonic_replay_20_whq_touch_count >= 3);



   if(fields.source_classic_wave_state == "clean_classic")

      fields.sonic_wave_quality = "clean";

   else if(fields.source_classic_wave_state == "choppy_cross")

      fields.sonic_wave_quality = "choppy";

   else if(fields.source_classic_wave_state == "overlap")

      fields.sonic_wave_quality = "overlap";

   else

      fields.sonic_wave_quality = "unclear";



   if(fields.source_classic_dragon_state == "dragon_expanding")

      fields.sonic_dragon_momentum = "expanding";

   else if(fields.source_classic_dragon_state == "dragon_angled")

      fields.sonic_dragon_momentum = "angled";

   else if(fields.source_classic_dragon_state == "dragon_compressed")

      fields.sonic_dragon_momentum = "compressed";

   else if(fields.source_classic_dragon_state == "dragon_flat")

      fields.sonic_dragon_momentum = "flat";

   else

      fields.sonic_dragon_momentum = "unknown";



   if(fields.source_sr_interaction == "RUNWAY" && fields.source_sr_runway_pips >= 15.0)

      fields.sonic_level_story = "clear_runway";

   else if(fields.source_sr_interaction == "BODY_CROSS")

      fields.sonic_level_story = "breakout_through_whq";

   else if(fields.source_sr_interaction == "REJECTION")

      fields.sonic_level_story = "rejection_at_whq";

   else if(fields.source_sr_interaction == "TOUCH" || fields.source_sr_interaction == "NEAR")

      fields.sonic_level_story = "near_whq";

   else if(fields.sonic_replay_20_whq_touch_count >= 5)

      fields.sonic_level_story = "repeated_whq_work";

   else

      fields.sonic_level_story = "unknown";



   if(ctx.session_bucket == "OFF")

      fields.sonic_session_momentum = "off_session";

   else if(ctx.minutes_to_forced_flat < g_minMinutesToNewTrade)

      fields.sonic_session_momentum = "forced_flat_near";

   else if(ctx.session_bucket == "LONDON" || ctx.session_bucket == "LONDON_NY")

      fields.sonic_session_momentum = "london_runway";

   else if(ctx.session_bucket == "NEWYORK")

      fields.sonic_session_momentum = "ny_runway";

   else

      fields.sonic_session_momentum = "active_runway";



   if(ctx.entry_blocked || ctx.force_flat_now || ctx.spread_regime == "HARD")

      fields.sonic_entry_timing_risk = "blocked";

   else if(fields.source_classic_chase_risk == "late_chase")

      fields.sonic_entry_timing_risk = "late_chase";

   else if(!trigger_break)

      fields.sonic_entry_timing_risk = "early_observe";

   else if(fields.source_classic_chase_risk == "mature")

      fields.sonic_entry_timing_risk = "mature";

   else if(fields.source_classic_chase_risk == "early")

      fields.sonic_entry_timing_risk = "early";

   else

      fields.sonic_entry_timing_risk = "unknown";



   if(!directional_candidate)

      fields.sonic_mm_mode_proxy = "unknown";

   else if(fields.source_classic_run_mode_proxy == "run_for_profits_proxy")

      fields.sonic_mm_mode_proxy = "run_for_profits";

   else if(fields.source_classic_run_mode_proxy == "position_building_proxy")

      fields.sonic_mm_mode_proxy = "position_building";

   else if(fields.source_classic_run_mode_proxy == "trap_risk")

      fields.sonic_mm_mode_proxy = "trap_risk";

   else if(clear_runway && aligned_replay && dragon_ready && fields.sonic_entry_timing_risk != "late_chase")

      fields.sonic_mm_mode_proxy = "run_for_profits";

   else if(near_or_through_level && pva_notable && !aligned_replay)

      fields.sonic_mm_mode_proxy = "position_building";

   else if((fields.sonic_entry_timing_risk == "late_chase" && pva_notable) ||

           (near_or_through_level && fields.source_classic_chase_risk == "late_chase"))

      fields.sonic_mm_mode_proxy = "trap_risk";

   else

      fields.sonic_mm_mode_proxy = "unknown";



   if(!directional_candidate)

      fields.sonic_story_state = "observe";

   else if(fields.sonic_mm_mode_proxy == "trap_risk")

      fields.sonic_story_state = "invalidate";

   else if(fields.sonic_mm_mode_proxy == "position_building")

      fields.sonic_story_state = "build";

   else if(clean_wave && dragon_ready && trigger_break && clear_runway && fields.sonic_entry_timing_risk != "late_chase")

      fields.sonic_story_state = "trigger_ready";

   else if(clean_wave && dragon_ready)

      fields.sonic_story_state = "classic_arming";

   else if(ctx.entry_blocked || ctx.force_flat_now || ctx.session_bucket == "OFF")

      fields.sonic_story_state = "invalidate";

   else

      fields.sonic_story_state = "observe";



   if(!directional_candidate)

      fields.sonic_trade_management_context = "observe_no_management_edge";

   else if(fields.sonic_story_state == "trigger_ready" && clear_runway)

      fields.sonic_trade_management_context = "runway_tp_with_dragon_invalidation";

   else if(fields.sonic_mm_mode_proxy == "trap_risk")

      fields.sonic_trade_management_context = "cut_red_or_no_chase";

   else if(fields.sonic_mm_mode_proxy == "position_building")

      fields.sonic_trade_management_context = "scanner_only_wait_for_run";

   else if(!clear_runway && near_or_through_level)

      fields.sonic_trade_management_context = "tight_runway_require_invalidation";

   else

      fields.sonic_trade_management_context = "observe_no_management_edge";

}



double SNR_CurrentPipSize()

{

   double point = SymbolInfoDouble(_Symbol, SYMBOL_POINT);

   int digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);

   if(point <= 0.0)

      return 0.0;

   if(digits <= 2)

      return point * 100.0;

   if(digits == 3 || digits == 5)

      return point * 10.0;

   return point;

}



bool SNR_CalcSourcePvaParity(const MqlRates &rates[],

                             const int bars_count,

                             double &avg_10,

                             double &spread_volume,

                             double &highest_spread_volume_10,

                             bool &rising_150,

                             bool &climax_200_or_highest_sv,

                             string &source_event,

                             int &source_grade)

{

   avg_10 = 0.0;

   spread_volume = 0.0;

   highest_spread_volume_10 = 0.0;

   rising_150 = false;

   climax_200_or_highest_sv = false;

   source_event = "NONE";

   source_grade = 0;



   if(bars_count < 11)

      return false;



   const double current_volume = (double)rates[0].tick_volume;

   spread_volume = current_volume * MathMax(0.0, rates[0].high - rates[0].low);



   double volume_sum = 0.0;

   for(int i = 1; i <= 10; i++)

   {

      double historical_volume = (double)rates[i].tick_volume;

      volume_sum += historical_volume;

      double historical_spread_volume = historical_volume * MathMax(0.0, rates[i].high - rates[i].low);

      highest_spread_volume_10 = MathMax(highest_spread_volume_10, historical_spread_volume);

   }



   avg_10 = volume_sum / 10.0;

   rising_150 = (avg_10 > 0.0 && current_volume >= avg_10 * 1.50);

   climax_200_or_highest_sv = ((avg_10 > 0.0 && current_volume >= avg_10 * 2.00) ||

                               (highest_spread_volume_10 > 0.0 && spread_volume >= highest_spread_volume_10));

   source_event = SNR_SourcePvaEventName(climax_200_or_highest_sv, rising_150);

   source_grade = SNR_SourcePvaGrade(climax_200_or_highest_sv, rising_150);

   return true;

}



void SNR_ResetPvsraSrFields(SnrPvsraSrFields &fields, const string status)

{

   fields.data_available = false;

   fields.data_status = status;

   fields.bar_time = 0;

   fields.source_sr_level_kind = "UNKNOWN";

   fields.source_sr_interaction = "DATA_UNAVAILABLE";

   fields.source_sr_rejection_side = "NONE";

   fields.source_sr_runway_pips = 0.0;

   fields.source_sr_grade = 0;

   SNR_ResetSourceClassicFields(fields);

   SNR_ResetSonicTraderStateFields(fields);

}



bool SNR_BuildPvsraSrFields(const double pip_size,

                            const double atr,

                            SnrPvsraSrFields &fields)

{

   SNR_ResetPvsraSrFields(fields, "DATA_UNAVAILABLE");

   if(pip_size <= 0.0)

      return false;



   MqlRates rates[];

   int bars_needed = 65;

   if(!SNR_CopyClosedRates(bars_needed, rates))

   {

      bars_needed = 25;

      if(!SNR_CopyClosedRates(bars_needed, rates))

         return false;

   }



   fields.data_available = true;

   fields.data_status = "OK";

   fields.bar_time = rates[0].time;

   fields.bar_open = rates[0].open;

   fields.bar_high = rates[0].high;

   fields.bar_low = rates[0].low;

   fields.bar_close = rates[0].close;

   fields.bar_tick_volume = (long)rates[0].tick_volume;

   fields.bar_real_volume = (long)rates[0].real_volume;

   fields.bar_spread = (int)rates[0].spread;



   double body_high = MathMax(rates[0].open, rates[0].close);

   double body_low = MathMin(rates[0].open, rates[0].close);

   double body = MathAbs(rates[0].close - rates[0].open);

   double range = rates[0].high - rates[0].low;

   fields.bar_body_pips = body / pip_size;

   fields.bar_range_pips = range / pip_size;

   fields.upper_wick_pips = MathMax(0.0, rates[0].high - body_high) / pip_size;

   fields.lower_wick_pips = MathMax(0.0, body_low - rates[0].low) / pip_size;

   fields.bar_direction = (rates[0].close > rates[0].open ? "BULL" : (rates[0].close < rates[0].open ? "BEAR" : "DOJI"));

   fields.close_location_0_1 = (range > 0.0 ? (rates[0].close - rates[0].low) / range : 0.5);



   long current_volume = (long)rates[0].tick_volume;

   long prev1_volume = (long)rates[1].tick_volume;

   long prev2_volume = (long)rates[2].tick_volume;

   double vol_sum_20 = 0.0;

   fields.vol_max_20 = 0;

   int higher_count = 0;

   for(int i = 1; i <= 20; i++)

   {

      long vol = (long)rates[i].tick_volume;

      vol_sum_20 += (double)vol;

      fields.vol_max_20 = MathMax(fields.vol_max_20, vol);

      if(vol > current_volume)

         higher_count++;

   }

   fields.vol_avg_20 = vol_sum_20 / 20.0;

   fields.vol_rank_20 = higher_count + 1;

   fields.vol_vs_avg_20 = (fields.vol_avg_20 > 0.0 ? (double)current_volume / fields.vol_avg_20 : 0.0);

   fields.vol_vs_prev_1 = (prev1_volume > 0 ? (double)current_volume / (double)prev1_volume : 0.0);

   fields.vol_vs_prev_2 = (prev2_volume > 0 ? (double)current_volume / (double)prev2_volume : 0.0);

   fields.candidate_pva_rising_150 = (fields.vol_vs_avg_20 >= 1.50);

   fields.candidate_pva_climax_200 = (fields.vol_vs_avg_20 >= 2.00);

   fields.candidate_pva_highest_20 = (fields.vol_rank_20 == 1);

   SNR_CalcSourcePvaParity(rates,

                           bars_needed,

                           fields.source_pva_avg_10,

                           fields.source_pva_spread_volume,

                           fields.source_pva_highest_spread_volume_10,

                           fields.source_pva_rising_150,

                           fields.source_pva_climax_200_or_highest_sv,

                           fields.source_pva_event,

                           fields.source_pva_grade);



    double whole_step = 100.0 * pip_size;

    double quarter_step = 25.0 * pip_size;

    

    // 1. Mức Whole level (bội số của 100 pips)

    fields.nearest_whole_price = MathRound(rates[0].close / whole_step) * whole_step;

    

    // 2. Mức Half level (phải kết thúc bằng 50 pips và không trùng với Whole)

    double half_up = fields.nearest_whole_price + 50.0 * pip_size;

    double half_down = fields.nearest_whole_price - 50.0 * pip_size;

    if(MathAbs(rates[0].close - half_up) < MathAbs(rates[0].close - half_down))

       fields.nearest_half_price = half_up;

    else

       fields.nearest_half_price = half_down;

       

    // 3. Mức Quarter level (phải kết thúc bằng 25 hoặc 75 pips và không trùng với Whole/Half)

    double q1 = fields.nearest_whole_price + 25.0 * pip_size;

    double q2 = fields.nearest_whole_price - 25.0 * pip_size;

    double q3 = fields.nearest_whole_price + 75.0 * pip_size;

    double q4 = fields.nearest_whole_price - 75.0 * pip_size;

    

    double min_diff = MathAbs(rates[0].close - q1);

    fields.nearest_quarter_price = q1;

    

    double diff2 = MathAbs(rates[0].close - q2);

    if(diff2 < min_diff) { min_diff = diff2; fields.nearest_quarter_price = q2; }

    

    double diff3 = MathAbs(rates[0].close - q3);

    if(diff3 < min_diff) { min_diff = diff3; fields.nearest_quarter_price = q3; }

    

    double diff4 = MathAbs(rates[0].close - q4);

    if(diff4 < min_diff) { min_diff = diff4; fields.nearest_quarter_price = q4; }



   fields.dist_close_to_whole_pips = MathAbs(rates[0].close - fields.nearest_whole_price) / pip_size;

   fields.dist_close_to_half_pips = MathAbs(rates[0].close - fields.nearest_half_price) / pip_size;

   fields.dist_close_to_quarter_pips = MathAbs(rates[0].close - fields.nearest_quarter_price) / pip_size;

   fields.dist_high_to_whole_pips = MathAbs(rates[0].high - fields.nearest_whole_price) / pip_size;

   fields.dist_high_to_half_pips = MathAbs(rates[0].high - fields.nearest_half_price) / pip_size;

   fields.dist_high_to_quarter_pips = MathAbs(rates[0].high - fields.nearest_quarter_price) / pip_size;

   fields.dist_low_to_whole_pips = MathAbs(rates[0].low - fields.nearest_whole_price) / pip_size;

   fields.dist_low_to_half_pips = MathAbs(rates[0].low - fields.nearest_half_price) / pip_size;

   fields.dist_low_to_quarter_pips = MathAbs(rates[0].low - fields.nearest_quarter_price) / pip_size;



   fields.whole_inside_candle_range = SNR_ValueInsideRange(fields.nearest_whole_price, rates[0].low, rates[0].high);

   fields.half_inside_candle_range = SNR_ValueInsideRange(fields.nearest_half_price, rates[0].low, rates[0].high);

   fields.quarter_inside_candle_range = SNR_ValueInsideRange(fields.nearest_quarter_price, rates[0].low, rates[0].high);

   fields.whole_inside_body = SNR_ValueInsideRange(fields.nearest_whole_price, body_low, body_high);

   fields.half_inside_body = SNR_ValueInsideRange(fields.nearest_half_price, body_low, body_high);

   fields.quarter_inside_body = SNR_ValueInsideRange(fields.nearest_quarter_price, body_low, body_high);



   fields.whole_upper_wick_touched = (fields.nearest_whole_price > body_high && fields.nearest_whole_price <= rates[0].high);

   fields.whole_lower_wick_touched = (fields.nearest_whole_price < body_low && fields.nearest_whole_price >= rates[0].low);

   fields.half_upper_wick_touched = (fields.nearest_half_price > body_high && fields.nearest_half_price <= rates[0].high);

   fields.half_lower_wick_touched = (fields.nearest_half_price < body_low && fields.nearest_half_price >= rates[0].low);

   fields.quarter_upper_wick_touched = (fields.nearest_quarter_price > body_high && fields.nearest_quarter_price <= rates[0].high);

   fields.quarter_lower_wick_touched = (fields.nearest_quarter_price < body_low && fields.nearest_quarter_price >= rates[0].low);

   fields.whole_rejection_side = SNR_GridRejectionSide(fields.nearest_whole_price, rates[0]);

   fields.half_rejection_side = SNR_GridRejectionSide(fields.nearest_half_price, rates[0]);

   fields.quarter_rejection_side = SNR_GridRejectionSide(fields.nearest_quarter_price, rates[0]);

   SNR_CalcSourceSrInteraction(rates[0],

                               pip_size,

                               fields.source_sr_level_kind,

                               fields.source_sr_interaction,

                               fields.source_sr_rejection_side,

                               fields.source_sr_runway_pips,

                               fields.source_sr_grade);



   fields.prior_swing_high_20 = -DBL_MAX;

   fields.prior_swing_low_20 = DBL_MAX;

   for(int i = 1; i <= 20; i++)

   {

      fields.prior_swing_high_20 = MathMax(fields.prior_swing_high_20, rates[i].high);

      fields.prior_swing_low_20 = MathMin(fields.prior_swing_low_20, rates[i].low);

   }

   fields.dist_high_to_prior_swing_high_pips = MathAbs(rates[0].high - fields.prior_swing_high_20) / pip_size;

   fields.dist_low_to_prior_swing_low_pips = MathAbs(rates[0].low - fields.prior_swing_low_20) / pip_size;

   fields.breaks_prior_swing_high = (rates[0].high > fields.prior_swing_high_20);

   fields.breaks_prior_swing_low = (rates[0].low < fields.prior_swing_low_20);

   fields.closes_above_prior_swing_high = (rates[0].close > fields.prior_swing_high_20);

   fields.closes_below_prior_swing_low = (rates[0].close < fields.prior_swing_low_20);



   fields.seq_5_bull_count = 0;

   fields.seq_5_bear_count = 0;

   fields.seq_5_high_volume_count = 0;

   fields.seq_5_climax_count = 0;

   double seq_high = -DBL_MAX;

   double seq_low = DBL_MAX;

   for(int i = 0; i < 5; i++)

   {

      if(rates[i].close > rates[i].open)

         fields.seq_5_bull_count++;

      else if(rates[i].close < rates[i].open)

         fields.seq_5_bear_count++;

      if(fields.vol_avg_20 > 0.0 && (double)rates[i].tick_volume / fields.vol_avg_20 >= 1.50)

         fields.seq_5_high_volume_count++;

      if(fields.vol_avg_20 > 0.0 && (double)rates[i].tick_volume / fields.vol_avg_20 >= 2.00)

         fields.seq_5_climax_count++;

      seq_high = MathMax(seq_high, rates[i].high);

      seq_low = MathMin(seq_low, rates[i].low);

   }

   fields.seq_5_net_range_atr = (atr > 0.0 ? (seq_high - seq_low) / atr : 0.0);

   fields.seq_5_close_delta_pips = (rates[0].close - rates[4].close) / pip_size;

   double seq_20_high = -DBL_MAX;

   double seq_20_low = DBL_MAX;

   double seq_60_high = -DBL_MAX;

   double seq_60_low = DBL_MAX;

   const int replay_bars = MathMin(60, bars_needed);

   for(int i = 0; i < replay_bars; i++)

   {

      seq_60_high = MathMax(seq_60_high, rates[i].high);

      seq_60_low = MathMin(seq_60_low, rates[i].low);

      if(i < 20)

      {

         seq_20_high = MathMax(seq_20_high, rates[i].high);

         seq_20_low = MathMin(seq_20_low, rates[i].low);

         if(fields.vol_avg_20 > 0.0 && (double)rates[i].tick_volume / fields.vol_avg_20 >= 1.50)

            fields.sonic_replay_20_pva_count++;

         double local_quarter = MathRound(rates[i].close / quarter_step) * quarter_step;

         if(SNR_ValueInsideRange(local_quarter, rates[i].low, rates[i].high))

            fields.sonic_replay_20_whq_touch_count++;

      }

   }

   fields.sonic_replay_20_close_delta_pips = (rates[0].close - rates[19].close) / pip_size;

   fields.sonic_replay_20_range_atr = (atr > 0.0 ? (seq_20_high - seq_20_low) / atr : 0.0);

   fields.sonic_replay_60_range_atr = (replay_bars >= 60 && atr > 0.0 ? (seq_60_high - seq_60_low) / atr : 0.0);

   fields.seq_context_candidate = "PARTIAL_HEURISTIC";

   return true;

}



bool SNR_PvsraSrHasGridInteraction(const SnrPvsraSrFields &fields)

{

   if(!fields.data_available)

      return false;

   return (fields.whole_inside_candle_range ||

           fields.half_inside_candle_range ||

           fields.quarter_inside_candle_range ||

           fields.whole_inside_body ||

           fields.half_inside_body ||

           fields.quarter_inside_body ||

           fields.whole_upper_wick_touched ||

           fields.whole_lower_wick_touched ||

           fields.half_upper_wick_touched ||

           fields.half_lower_wick_touched ||

           fields.quarter_upper_wick_touched ||

           fields.quarter_lower_wick_touched);

}



bool SNR_PvsraSrHasPriorSrInteraction(const SnrPvsraSrFields &fields)

{

   if(!fields.data_available)

      return false;

   return (fields.breaks_prior_swing_high ||

           fields.breaks_prior_swing_low ||

           fields.closes_above_prior_swing_high ||

           fields.closes_below_prior_swing_low);

}



bool SNR_PvsraSrContextBoostAllowed(const SnrContext &ctx,

                                    const int base_grade,

                                    const int min_grade,

                                    const double atr)

{

   if(!g_usePvsraSrContext || min_grade <= 0)

      return false;

   if(ctx.level_zone != "NONE")

      return false;

   if(base_grade != min_grade - 1)

      return false;

   if(ctx.pvsra_event != "CLIMAX" && ctx.pvsra_event != "RISING_ACTIVITY")

      return false;



   SnrPvsraSrFields fields;

   if(!SNR_BuildPvsraSrFields(SNR_CurrentPipSize(), atr, fields))

      return false;



   return (SNR_PvsraSrHasGridInteraction(fields) ||

           SNR_PvsraSrHasPriorSrInteraction(fields));

}



int SNR_PvsraSrAdjustedClassicGrade(const SnrContext &ctx,

                                    const int base_grade,

                                    const int min_grade,

                                    const double atr)

{

   if(SNR_PvsraSrContextBoostAllowed(ctx, base_grade, min_grade, atr))

      return MathMin(5, base_grade + 1);

   return base_grade;

}



int SNR_DragonCrossCount(const MqlRates &rates[],

                         const double &dragon_mid[],

                         const int from_idx,

                         const int bars_count)

{

   int crosses = 0;

   int prev_sign = 0;

   for(int i = from_idx + bars_count - 1; i >= from_idx; i--)

   {

      int sign = 0;

      if(rates[i].close > dragon_mid[i])

         sign = 1;

      else if(rates[i].close < dragon_mid[i])

         sign = -1;



      if(sign == 0)

         continue;

      if(prev_sign != 0 && sign != prev_sign)

         crosses++;

      prev_sign = sign;

   }

   return crosses;

}



void SNR_UpdateRegimeState(SnrContext &ctx,

                           const MqlRates &rates[],

                           const double &dragon_mid[],

                           const double &trend[],

                           const double atr_value,

                           const int bars_count)

{

   ctx.regime_state = SNR_REGIME_UNKNOWN;

   ctx.regime_reason = "ROUTER_DISABLED";

   ctx.regime_bias = SNR_DIR_NONE;

   ctx.range_high = 0.0;

   ctx.range_low = 0.0;

   ctx.range_mid = 0.0;

   ctx.range_width_atr = 0.0;

   ctx.dragon_cross_count = 0;



   if(!g_useRegimeRouter)

      return;

   if(_Period != PERIOD_M5 && _Period != PERIOD_M15)

   {

      ctx.regime_reason = "NON_M5_M15";

      return;

   }

   int min_bars = (_Period == PERIOD_M15 ? 25 : 37);

   if(atr_value <= 0.0 || bars_count < min_bars)

   {

      ctx.regime_reason = "REGIME_DATA_UNAVAILABLE";

      return;

   }



   const int lookback = (_Period == PERIOD_M15 ? 24 : 36);

   double range_high = -DBL_MAX;

   double range_low = DBL_MAX;

   for(int i = 1; i <= lookback; i++)

   {

      range_high = MathMax(range_high, rates[i].high);

      range_low = MathMin(range_low, rates[i].low);

   }



   ctx.range_high = range_high;

   ctx.range_low = range_low;

   ctx.range_mid = (range_high + range_low) * 0.5;

   ctx.range_width_atr = (range_high - range_low) / atr_value;

   ctx.dragon_cross_count = SNR_DragonCrossCount(rates, dragon_mid, 1, lookback);



   double trend_dragon_slope = (_Period == PERIOD_M15 ? g_minDragonSlopeATR : 0.10);

   double trend_slope = (_Period == PERIOD_M15 ? g_regimeRouterMinTrendSlope : 0.03);



   bool trend_long = (MathAbs(ctx.dragon_slope_atr) >= trend_dragon_slope &&

                      MathAbs(ctx.trend_slope_atr) >= trend_slope &&

                      rates[0].close > dragon_mid[0] &&

                      rates[0].close > trend[0] &&

                      ctx.dragon_slope_atr > 0.0 &&

                      ctx.trend_slope_atr >= 0.0 &&

                      ctx.htf_bias_score >= 0);

   bool trend_short = (MathAbs(ctx.dragon_slope_atr) >= trend_dragon_slope &&

                       MathAbs(ctx.trend_slope_atr) >= trend_slope &&

                       rates[0].close < dragon_mid[0] &&

                       rates[0].close < trend[0] &&

                       ctx.dragon_slope_atr < 0.0 &&

                       ctx.trend_slope_atr <= 0.0 &&

                       ctx.htf_bias_score <= 0);



    if(trend_long || trend_short)

    {

       bool strong = (MathAbs(ctx.dragon_slope_atr) >= trend_dragon_slope * 1.5 && MathAbs(ctx.trend_slope_atr) >= trend_slope * 1.5);

       ctx.regime_state = (strong ? SNR_REGIME_TRENDING_STRONG : SNR_REGIME_TREND);

       ctx.regime_bias = (trend_long ? SNR_DIR_LONG : SNR_DIR_SHORT);

       ctx.regime_reason = (strong ? (trend_long ? "TREND_STRONG_LONG" : "TREND_STRONG_SHORT") : (trend_long ? "TREND_LONG" : "TREND_SHORT"));

       return;

    }

 

    double range_dragon_slope = (_Period == PERIOD_M15 ? g_minDragonSlopeATR : 0.08);

    double range_trend_slope = (_Period == PERIOD_M15 ? g_regimeRouterMinTrendSlope : 0.03);

    double min_range_atr = (_Period == PERIOD_M15 ? 1.00 : 0.80);

    double max_range_atr = (_Period == PERIOD_M15 ? 3.00 : 2.40);

    int min_crosses = (_Period == PERIOD_M15 ? 4 : 5);

 

    bool range_ok = (MathAbs(ctx.dragon_slope_atr) < range_dragon_slope &&

                     MathAbs(ctx.trend_slope_atr) < range_trend_slope &&

                     ctx.range_width_atr >= min_range_atr &&

                     ctx.range_width_atr <= max_range_atr &&

                     ctx.dragon_cross_count >= min_crosses);

    if(range_ok)

    {

       bool narrow = (ctx.range_width_atr < 1.50);

       ctx.regime_state = (narrow ? SNR_REGIME_SIDEWAY_NARROW : SNR_REGIME_SIDEWAY_WIDE);

       ctx.regime_reason = (narrow ? "SIDEWAY_NARROW_COMPRESSED" : "SIDEWAY_WIDE_CROSSING");

       return;

    }



   ctx.regime_state = SNR_REGIME_TRANSITION;

   ctx.regime_reason = "TRANSITION";

}



bool SNR_BuildContext(const datetime decision_time_server,

                      const int dragon_high_handle,

                      const int dragon_mid_handle,

                      const int dragon_low_handle,

                      const int trend_handle,

                      const int atr_handle,

                      const int h1_bias_handle,

                      const int h4_bias_handle,

                      const double pip_size,

                      const SnrNarrative &narrative,

                      SnrContext &ctx)

{

   MqlRates rates[];

   double dragon_high[];

   double dragon_mid[];

   double dragon_low[];

   double trend[];

   double atr[];



   int min_regime_bars = 0;

   if(g_useRegimeRouter)

      min_regime_bars = (_Period == PERIOD_M15 ? 25 : 37);

   const int bars_needed = MathMax(MathMax(g_smcStructureLookback + 5, g_waveLookbackBars + 12), min_regime_bars);

   if(!SNR_CopyClosedRates(bars_needed, rates))

      return false;

   if(!SNR_CopyClosedBuffer(dragon_high_handle, bars_needed, dragon_high))

      return false;

   if(!SNR_CopyClosedBuffer(dragon_mid_handle, bars_needed, dragon_mid))

      return false;

   if(!SNR_CopyClosedBuffer(dragon_low_handle, bars_needed, dragon_low))

      return false;

   if(!SNR_CopyClosedBuffer(trend_handle, bars_needed, trend))

      return false;

   if(!SNR_CopyClosedBuffer(atr_handle, bars_needed, atr))

      return false;

   if(atr[0] <= 0.0)

      return false;



   ctx.decision_time_server = decision_time_server;

   ctx.decision_time_utc = SNR_ServerToUTC(decision_time_server);

   ctx.session_bucket = SNR_SessionBucket(decision_time_server);

   ctx.minutes_to_forced_flat = SNR_MinutesToForcedFlat(decision_time_server);

   ctx.entry_blocked = false;

   ctx.force_flat_now = false;

   ctx.block_reason = "";

   ctx.dragon_high = dragon_high[0];

   ctx.dragon_mid = dragon_mid[0];

   ctx.dragon_low = dragon_low[0];

   ctx.trend = trend[0];

   ctx.atr = atr[0];

   ctx.dragon_slope_atr = (dragon_mid[0] - dragon_mid[MathMin(g_slopeLookbackBars, bars_needed - 1)]) / atr[0];

   ctx.trend_slope_atr = (trend[0] - trend[MathMin(g_slopeLookbackBars, bars_needed - 1)]) / atr[0];



   // Dragon Dynamic Expansion rate-of-change logic

   double width_sum = 0.0;

   for(int i = 0; i < 20; i++)

   {

      width_sum += MathAbs(dragon_high[i] - dragon_low[i]);

   }

   double avg_width_20 = width_sum / 20.0;

   double current_width = MathAbs(dragon_high[0] - dragon_low[0]);

   ctx.dragon_dynamic_expansion_roc = (avg_width_20 > 0.0) ? (current_width / avg_width_20) : 1.0;

   ctx.regime_state = SNR_REGIME_UNKNOWN;

   ctx.regime_reason = "ROUTER_DISABLED";

   ctx.regime_bias = SNR_DIR_NONE;

   ctx.range_high = 0.0;

   ctx.range_low = 0.0;

   ctx.range_mid = 0.0;

   ctx.range_width_atr = 0.0;

   ctx.dragon_cross_count = 0;

   ctx.dragon_angle_class = SNR_DragonAngleClass(ctx.dragon_slope_atr);

   ctx.active_layers = narrative.layers_opened;

   ctx.narrative_direction = narrative.direction;



   double range = rates[0].high - rates[0].low;

   double body  = MathAbs(rates[0].close - rates[0].open);

   ctx.body_ratio = (range > 0.0 ? body / range : 0.0);

   ctx.bar_range_atr = range / atr[0];



   double spread_points = (double)SymbolInfoInteger(_Symbol, SYMBOL_SPREAD) * _Point;

   ctx.spread_pips = (pip_size > 0.0 ? spread_points / pip_size : 0.0);

   if(ctx.spread_pips <= g_spreadSoftPips)

      ctx.spread_regime = "NORMAL";

   else if(ctx.spread_pips <= g_spreadHardPips)

      ctx.spread_regime = "ELEVATED";

   else

      ctx.spread_regime = "HARD";



   string base_currency, quote_currency;

   SNR_DetectSymbolCurrencies(base_currency, quote_currency);

   string news_event_class = "";

   ctx.news_distance_min = SNR_FindNearestRelevantNewsMinutes(ctx.decision_time_utc,

                                                              base_currency,

                                                              quote_currency,

                                                              ctx.entry_blocked,

                                                              ctx.force_flat_now,

                                                              news_event_class);



   MqlDateTime dt;

   TimeToStruct(decision_time_server, dt);

   ctx.day_of_week = dt.day_of_week;

   ctx.hour_server = dt.hour;



   double h1_bias_value = 0.0;

   double h4_bias_value = 0.0;

   double tmp[];

   ctx.h1_bias = 0;

   ctx.h4_bias = 0;

   if(h1_bias_handle != INVALID_HANDLE && SNR_CopyClosedBuffer(h1_bias_handle, 2, tmp))

   {

      h1_bias_value = tmp[0];

      if(rates[0].close > h1_bias_value) ctx.h1_bias = 1;

      if(rates[0].close < h1_bias_value) ctx.h1_bias = -1;

   }

   if(h4_bias_handle != INVALID_HANDLE && SNR_CopyClosedBuffer(h4_bias_handle, 2, tmp))

   {

      h4_bias_value = tmp[0];

      if(rates[0].close > h4_bias_value) ctx.h4_bias = 1;

      if(rates[0].close < h4_bias_value) ctx.h4_bias = -1;

   }

   ctx.htf_bias_score = ctx.h1_bias + ctx.h4_bias;

   SNR_UpdateRegimeState(ctx, rates, dragon_mid, trend, atr[0], bars_needed);



   SNR_DetectLevelZone(rates[0].close, pip_size, ctx.level_zone, ctx.level_distance_pips);

   ctx.tick_volume_percentile = SNR_CalcVolumePercentile(rates, MathMin(20, bars_needed));

   ctx.recent_accum_bias = SNR_CalcRecentAccumBias(rates, bars_needed, dragon_mid, atr);

   ctx.pvsra_grade = SNR_IntensityPvsraGrade(ctx.tick_volume_percentile,

                                             ctx.body_ratio,

                                             ctx.bar_range_atr,

                                             ctx.level_zone);

   ctx.pvsra_bias = SNR_PvsraBiasName(ctx.recent_accum_bias);

   ctx.pvsra_event = SNR_PvsraEventName(ctx.tick_volume_percentile,

                                        ctx.body_ratio,

                                        ctx.bar_range_atr);

   double source_pva_avg_10 = 0.0;

   double source_pva_spread_volume = 0.0;

   double source_pva_highest_spread_volume_10 = 0.0;

   bool source_pva_rising_150 = false;

   bool source_pva_climax_200_or_highest_sv = false;

   if(SNR_CalcSourcePvaParity(rates,

                              bars_needed,

                              source_pva_avg_10,

                              source_pva_spread_volume,

                              source_pva_highest_spread_volume_10,

                              source_pva_rising_150,

                              source_pva_climax_200_or_highest_sv,

                              ctx.source_pva_event,

                              ctx.source_pva_grade) &&

      g_useSourcePvaParityV1)

   {

      ctx.pvsra_event = ctx.source_pva_event;

      ctx.pvsra_grade = ctx.source_pva_grade;

   }

   SNR_CalcSourceSrInteraction(rates[0],

                               pip_size,

                               ctx.source_sr_level_kind,

                               ctx.source_sr_interaction,

                               ctx.source_sr_rejection_side,

                               ctx.source_sr_runway_pips,

                               ctx.source_sr_grade);

   SnrPvsraSrFields source_classic_fields;

   SNR_ResetSourceClassicFields(source_classic_fields);

   SNR_CopySourceClassicFieldsToContext(source_classic_fields, ctx);

   SNR_ResetSonicTraderStateFields(source_classic_fields);

   SNR_CopySonicTraderStateFieldsToContext(source_classic_fields, ctx);

   if(SNR_BuildPvsraSrFields(pip_size, ctx.atr, source_classic_fields))

   {

      int source_classic_direction = SNR_SourceClassicEffectiveDirection(SNR_DIR_NONE, source_classic_fields);

      SNR_AnnotateSourceClassicFields(ctx, source_classic_direction, source_classic_fields);

      SNR_CopySourceClassicFieldsToContext(source_classic_fields, ctx);

      SNR_AnnotateSonicTraderState(ctx, source_classic_direction, source_classic_fields);

      SNR_CopySonicTraderStateFieldsToContext(source_classic_fields, ctx);

   }



   bool htf_long_ok = g_useSoftHtfBias ? (ctx.htf_bias_score >= -1) : (ctx.h1_bias >= 0 && ctx.h4_bias >= 0);

   bool htf_short_ok = g_useSoftHtfBias ? (ctx.htf_bias_score <= 1) : (ctx.h1_bias <= 0 && ctx.h4_bias <= 0);

   if(g_useClassicSourceCore && !g_sourceCoreKeepsHtfGate)

   {

      htf_long_ok = true;

      htf_short_ok = true;

   }

   bool trend_long_ok = (g_useClassicSourceCore || !g_useTrendHardGate || (ctx.trend_slope_atr > 0.0 && rates[0].close > ctx.trend));

   bool trend_short_ok = (g_useClassicSourceCore || !g_useTrendHardGate || (ctx.trend_slope_atr < 0.0 && rates[0].close < ctx.trend));



   ctx.allow_long  = (ctx.dragon_slope_atr >= g_minDragonSlopeATR &&

                      rates[0].close > ctx.dragon_mid &&

                      trend_long_ok &&

                      htf_long_ok);

   ctx.allow_short = (ctx.dragon_slope_atr <= -g_minDragonSlopeATR &&

                      rates[0].close < ctx.dragon_mid &&

                      trend_short_ok &&

                      htf_short_ok);



   // --- Dynamic Quant Framework Calculations ---

   double sdev = SNR_StdDev(rates, 20, 0);

   double b_width = 4.0 * sdev;

   double k_width = 3.0 * atr[0];

   ctx.bollinger_keltner_ratio = (k_width > 0.0) ? (b_width / k_width) : 1.0;

   ctx.keltner_squeeze = (ctx.bollinger_keltner_ratio < 1.0);



   SNR_DetectMarketStructure(rates, bars_needed, g_smcStructureLookback, 0, ctx.market_structure_high, ctx.market_structure_low);

   

   SNR_DetectLiquiditySweep(rates, source_classic_fields, pip_size, ctx.market_structure_high, ctx.market_structure_low, ctx.liquidity_sweep_active, ctx.liquidity_sweep_direction);

   // --------------------------------------------



   double score = 0.0;

   score += MathMin(2.0, MathAbs(ctx.dragon_slope_atr) * 4.0);

   score += MathMin(1.5, MathAbs(ctx.trend_slope_atr) * 3.0);

   score += (ctx.tick_volume_percentile / 100.0);

   score += (ctx.level_zone != "NONE" ? 0.35 : 0.0);

   score += (ctx.spread_regime == "NORMAL" ? 0.50 : (ctx.spread_regime == "ELEVATED" ? 0.10 : -1.00));

   score += (ctx.h1_bias == ctx.h4_bias && ctx.h1_bias != 0 ? 0.60 : 0.0);

   ctx.context_score = score;



   int now_min = SNR_ServerMinutesOfDay(decision_time_server);

   if(now_min < 300)

   {

      ctx.entry_blocked = true;

      ctx.block_reason = "ROLLOVER_ENTRY_LOCK";

   }

   else if(ctx.session_bucket == "OFF")

   {

      ctx.entry_blocked = true;

      ctx.block_reason = "OFF_SESSION";

   }

   else if(SNR_IsBlockedEntryHour(decision_time_server))

   {

      ctx.entry_blocked = true;

      ctx.block_reason = "ENTRY_HOUR_BLOCK";

   }

   else if(SNR_IsBlockedEntryWeekday(decision_time_server))

   {

      ctx.entry_blocked = true;

      ctx.block_reason = "ENTRY_WEEKDAY_BLOCK";

   }

   else if(g_useNewsFilter && !g_snrCalendarMeta.loaded)

   {

      ctx.entry_blocked = true;

      ctx.force_flat_now = true;

      ctx.block_reason = "CALENDAR_UNAVAILABLE";

   }

   else if(ctx.minutes_to_forced_flat < g_minMinutesToNewTrade)

   {

      ctx.entry_blocked = true;

      ctx.block_reason = "NOT_ENOUGH_SESSION_TIME";

   }

   else if(ctx.day_of_week == 0 || ctx.day_of_week == 6)

   {

      ctx.entry_blocked = true;

      ctx.force_flat_now = true;

      ctx.block_reason = "WEEKEND";

   }

   else if(g_skipFridayEntries && ctx.day_of_week == 5)

   {

      ctx.entry_blocked = true;

      if(SNR_ServerMinutesOfDay(decision_time_server) >= SNR_MinutesOfDay(g_fridayFlatHour, g_fridayFlatMinute))

         ctx.force_flat_now = true;

      ctx.block_reason = "FRIDAY_ENTRY_BLOCK";

   }

   else if(g_blockSidewayNarrow && ctx.regime_state == SNR_REGIME_SIDEWAY_NARROW)

   {

      ctx.entry_blocked = true;

      ctx.block_reason = "SIDEWAY_NARROW";

   }

   else if(ctx.spread_regime == "HARD")

   {

      ctx.entry_blocked = true;

      ctx.block_reason = "SPREAD_HARD";

   }

   else if(ctx.entry_blocked && ctx.block_reason == "")

   {

      ctx.block_reason = "NEWS_BLOCK";

   }



   return true;

}





void SNR_ApplyAutoSleeveConfig(string symbol)

{

   string sym = symbol;

   StringToUpper(sym);



   // Khởi tạo mặc định cho tất cả biến toàn cục runtime từ Inp tĩnh

   g_useRegimeRouter = InpUseRegimeRouter;

   g_useClassicTrend = InpUseClassicTrend;

   g_useClassicReversal = InpUseClassicReversal;

   g_onlyNewYorkReversal = InpOnlyNewYorkReversal;

   g_useFxM15ReversalContextGate = InpUseFxM15ReversalContextGate;

   g_useDragonExpansionFilter = InpUseDragonExpansionFilter;

   g_dragonMaxExpansionRatio = InpDragonMaxExpansionRatio;

   g_useArmedClassic = InpUseArmedClassic;

   g_useDragonPullbackEntry = InpUseDragonPullbackEntry;

   g_regimeRouterMinDragonSlope = InpRegimeRouterMinDragonSlope;

   g_regimeRouterMinTrendSlope = InpRegimeRouterMinTrendSlope;

   g_minDragonSlopeATR = InpMinDragonSlopeATR;

   g_forceFlatOutsideSession = InpForceFlatOutsideSession;

   

   g_useReentry = InpUseReentry;

   g_useContinuationPullback = InpUseContinuationPullback;

   g_useScoutProbe = InpUseScoutProbe;

   g_useFxClassicStateQualityGate = InpUseFxClassicStateQualityGate;

   g_minPvsraGradeClassic = InpMinPvsraGradeClassic;

   g_minMinutesToNewTrade = InpMinMinutesToNewTrade;

   g_useDynamicSMCStructure = InpUseDynamicSMCStructure;

   g_useLiquiditySweep = InpUseLiquiditySweep;

   g_useStructuralTrailing = InpUseStructuralTrailing;

   g_useVolatilitySqueeze = InpUseVolatilitySqueeze;

   g_stopAtrBuffer = InpStopAtrBuffer;

   g_useLondon = InpUseLondon;

   g_useNewYork = InpUseNewYork;

   g_useXauActiveClassic = InpUseXauActiveClassic;

   g_useXauRangeAbsorption = InpUseXauRangeAbsorption;

   g_useXauSweepReclaimExecution = InpUseXauSweepReclaimExecution;

   

   g_waveLookbackBars = InpWaveLookbackBars;

   g_smcStructureLookback = InpSMCStructureLookback;

   g_maxClassicBreakoutExtensionATR = InpMaxClassicBreakoutExtensionATR;

   g_reentryMinPvsraGrade = InpReentryMinPvsraGrade;

   g_classicArmBars = InpClassicArmBars;

   g_useXauClassicStateQualityGate = InpUseXauClassicStateQualityGate;

   g_xauRangeAbsorptionMinTargetRR = InpXauRangeAbsorptionMinTargetRR;

   g_xauSweepReclaimMinTargetRR = InpXauSweepReclaimMinTargetRR;

   g_useXauS1M15AtrImpulseFilter = InpUseXauS1M15AtrImpulseFilter;

   g_xauS1M15AtrPeriod = InpXauS1M15AtrPeriod;

   g_xauS1M15AtrEmaPeriod = InpXauS1M15AtrEmaPeriod;

   g_xauS1M15AtrMultiplier = InpXauS1M15AtrMultiplier;

   g_useXauS1M5DragonAnchorCompressionFilter = InpUseXauS1M5DragonAnchorCompressionFilter;

   g_xauS1M5DragonAnchorMaxCompressionAtr = InpXauS1M5DragonAnchorMaxCompressionAtr;


   g_goldMinCompressionRatio = InpGoldMinCompressionRatio;

   g_goldS1MinPvsraGrade = InpGoldS1MinPvsraGrade;

   g_xauS1RequireWholeHalf = InpXauS1RequireWholeHalf;



   g_useClassicMinSLFloor = InpUseClassicMinSLFloor;

   g_classicRiskPct = InpClassicRiskPct;

   g_secondLayerRiskPct = InpSecondLayerRiskPct;

   g_maxNarrativeRiskPct = InpMaxNarrativeRiskPct;

   g_fxClassicMinRunwayPips = InpFxClassicMinRunwayPips;

   g_scalpMinSLPips = InpScalpMinSLPips;

   g_spreadSoftPips = InpSpreadSoftPips;

   g_blockedEntryWeekdays = InpBlockedEntryWeekdays;
   // Auto-generated default mappings for complete parameter synchronization




   // Auto-generated default mappings for complete parameter synchronization
   g_enabled = InpEnabled;
   g_magic = InpMagic;
   g_comment = InpComment;
   g_variantTag = InpVariantTag;
   g_researchLaneTag = InpResearchLaneTag;
   g_useOrderCalcRiskSizing = InpUseOrderCalcRiskSizing;
   g_orderCalcRiskFailClosed = InpOrderCalcRiskFailClosed;
   g_maxLot = InpMaxLot;
   g_dailyLossLockPct = InpDailyLossLockPct;
   g_maxEquityDrawdownPct = InpMaxEquityDrawdownPct;
   g_maxTradesPerDay = InpMaxTradesPerDay;
   g_dragonPeriod = InpDragonPeriod;
   g_trendPeriod = InpTrendPeriod;
   g_atrPeriod = InpATRPeriod;
   g_slopeLookbackBars = InpSlopeLookbackBars;
   g_useClassicSourceCore = InpUseClassicSourceCore;
   g_useEurLondonShortCleanRoute = InpUseEurLondonShortCleanRoute;
   g_eurLondonShortRouteTargetRR = InpEurLondonShortRouteTargetRR;
   g_useSourcePvaParityV1 = InpUseSourcePvaParityV1;
   g_usePvsraSrContext = InpUsePvsraSrContext;
   g_useSourceSrInteractionV1 = InpUseSourceSrInteractionV1;
   g_blockSidewayNarrow = InpBlockSidewayNarrow;
   g_maxChaseDistanceAtr = InpMaxChaseDistanceAtr;
   g_usePullbackEntry = InpUsePullbackEntry;
   g_requirePvsraVolume = InpRequirePvsraVolume;
   g_volumeLookback = InpVolumeLookback;
   g_volumeClimaxMultiplier = InpVolumeClimaxMultiplier;
   g_regimeRouterLegacyFallback = InpRegimeRouterLegacyFallback;
   g_xauRangeAbsorptionAllowInnerRotation = InpXauRangeAbsorptionAllowInnerRotation;
   g_useXauSweepReclaimScanner = InpUseXauSweepReclaimScanner;
   g_xauSweepReclaimDirectionMode = InpXauSweepReclaimDirectionMode;
   g_xauSweepReclaimBlockedHours = InpXauSweepReclaimBlockedHours;
   g_xauSweepReclaimBlockedWeekdays = InpXauSweepReclaimBlockedWeekdays;
   g_xauSweepReclaimBlockedLongHours = InpXauSweepReclaimBlockedLongHours;
   g_xauSweepReclaimBlockedShortHours = InpXauSweepReclaimBlockedShortHours;
   g_xauSweepReclaimBlockedLongWeekdays = InpXauSweepReclaimBlockedLongWeekdays;
   g_xauSweepReclaimBlockedShortWeekdays = InpXauSweepReclaimBlockedShortWeekdays;
   g_xauSweepReclaimMaxTargetRR = InpXauSweepReclaimMaxTargetRR;
   g_useXauLongBiasCoreGate = InpUseXauLongBiasCoreGate;
   g_enableImpulseS1FPVeto = InpEnableImpulseS1FPVeto;
   g_useXauS1M15AtrImpulseFilter = InpUseXauS1M15AtrImpulseFilter;
   g_xauS1M15AtrPeriod = InpXauS1M15AtrPeriod;
   g_xauS1M15AtrEmaPeriod = InpXauS1M15AtrEmaPeriod;
   g_xauS1M15AtrMultiplier = InpXauS1M15AtrMultiplier;
   g_useXauS1M5DragonAnchorCompressionFilter = InpUseXauS1M5DragonAnchorCompressionFilter;
   g_xauS1M5DragonAnchorMaxCompressionAtr = InpXauS1M5DragonAnchorMaxCompressionAtr;
   g_useEurTrendClassic = InpUseEurTrendClassic;
   g_useEurAsianBoxRetest = InpUseEurAsianBoxRetest;
   g_scalpLaneRiskPct = InpScalpLaneRiskPct;
   g_rangeLaneRiskPct = InpRangeLaneRiskPct;
   g_maxScalpTradesPerDay = InpMaxScalpTradesPerDay;
   g_maxLaneLossesPerSession = InpMaxLaneLossesPerSession;
   g_blockedClassicPvsraEvents = InpBlockedClassicPvsraEvents;
   g_blockedClassicLevelZones = InpBlockedClassicLevelZones;
   g_useNy16ShortClimaxQuarterRoute = InpUseNy16ShortClimaxQuarterRoute;
   g_minPvsraGradeReversal = InpMinPvsraGradeReversal;
   g_minPvsraGradeScout = InpMinPvsraGradeScout;
   g_scoutMinPvsraGrade = InpScoutMinPvsraGrade;
   g_sweepLookbackBars = InpSweepLookbackBars;
   g_useH1Bias = InpUseH1Bias;
   g_useH4Bias = InpUseH4Bias;
   g_htfProfileMode = InpHtfProfileMode;
   g_sourceCoreKeepsHtfGate = InpSourceCoreKeepsHtfGate;
   g_htfBiasPeriod = InpHtfBiasPeriod;
   g_wholeLevelRadiusPips = InpWholeLevelRadiusPips;
   g_halfLevelRadiusPips = InpHalfLevelRadiusPips;
   g_londonStartHour = InpLondonStartHour;
   g_londonStartMinute = InpLondonStartMinute;
   g_londonEndHour = InpLondonEndHour;
   g_londonEndMinute = InpLondonEndMinute;
   g_newYorkStartHour = InpNewYorkStartHour;
   g_newYorkStartMinute = InpNewYorkStartMinute;
   g_newYorkEndHour = InpNewYorkEndHour;
   g_newYorkEndMinute = InpNewYorkEndMinute;
   g_newYorkReversalStartHour = InpNewYorkReversalStartHour;
   g_newYorkReversalEndHour = InpNewYorkReversalEndHour;
   g_hardFlatHour = InpHardFlatHour;
   g_hardFlatMinute = InpHardFlatMinute;
   g_fridayFlatHour = InpFridayFlatHour;
   g_fridayFlatMinute = InpFridayFlatMinute;
   g_skipFridayEntries = InpSkipFridayEntries;
   g_blockedEntryHours = InpBlockedEntryHours;
   g_useNewsFilter = InpUseNewsFilter;
   g_calendarFile = InpCalendarFile;
   g_legacyCalendarMinImportance = InpLegacyCalendarMinImportance;
   g_newsBlockBeforeMin = InpNewsBlockBeforeMin;
   g_newsBlockAfterMin = InpNewsBlockAfterMin;
   g_forceFlatBeforeNewsMin = InpForceFlatBeforeNewsMin;
   g_timeProfileMode = InpTimeProfileMode;
   g_fixedUtcOffsetHours = InpFixedUtcOffsetHours;
   g_deviation = InpDeviation;
   g_retryCount = InpRetryCount;
   g_retryDelayMs = InpRetryDelayMs;
   g_minSLPips = InpMinSLPips;
   g_continuationMinSLPips = InpContinuationMinSLPips;
   g_maxSLPips = InpMaxSLPips;
   g_preservePrimaryExitsOnScaleIn = InpPreservePrimaryExitsOnScaleIn;
   g_modifyAllPositionsAfterEntry = InpModifyAllPositionsAfterEntry;
   g_useBreakEven = InpUseBreakEven;
   g_breakEvenTriggerR = InpBreakEvenTriggerR;
   g_enableTelemetry = InpEnableTelemetry;
   g_enableSourceClassicDragonEdgeDistanceTelemetry = InpEnableSourceClassicDragonEdgeDistanceTelemetry;
   g_enableSourceH4TargetRunwayTelemetry = InpEnableSourceH4TargetRunwayTelemetry;
   g_enableFxM15MtfPvaWeakeningTelemetry = InpEnableFxM15MtfPvaWeakeningTelemetry;
   g_enableOpportunityLogger = InpEnableOpportunityLogger;
   g_enableShadowNarrative = InpEnableShadowNarrative;
   g_enableStateTelemetry = InpEnableStateTelemetry;
   g_enableGoldRegimeTelemetry = InpEnableGoldRegimeTelemetry;
   g_useOpportunityScoreGate = InpUseOpportunityScoreGate;
   g_minClassicOpportunityScore = InpMinClassicOpportunityScore;
   g_minReentryOpportunityScore = InpMinReentryOpportunityScore;
   g_xauClassicStateMinWarnings = InpXauClassicStateMinWarnings;
   g_xauClassicMinRunwayPips = InpXauClassicMinRunwayPips;
   g_xauClassicMaxDragonExtensionAtr = InpXauClassicMaxDragonExtensionAtr;
   g_xauClassicMaxOverlapRatio = InpXauClassicMaxOverlapRatio;
   g_xauClassicHour15MinRunwayPips = InpXauClassicHour15MinRunwayPips;
   g_fxClassicMaxDragonExtensionAtr = InpFxClassicMaxDragonExtensionAtr;
   g_fxClassicMaxOverlapRatio = InpFxClassicMaxOverlapRatio;
   g_fxClassicRequireCleanWave = InpFxClassicRequireCleanWave;
   g_fxClassicRequireHtfAlignment = InpFxClassicRequireHtfAlignment;
   g_fxClassicBlockFlatDragon = InpFxClassicBlockFlatDragon;
   g_fxClassicBlockLateChase = InpFxClassicBlockLateChase;
   g_useFxChaseTrapV2ADiagnostic = InpUseFxChaseTrapV2ADiagnostic;
   g_enableFxClassicNearMissTelemetry = InpEnableFxClassicNearMissTelemetry;
   g_useFxM15HtfClassicRoute = InpUseFxM15HtfClassicRoute;
   g_fxM15RouteRequireH1H4Alignment = InpFxM15RouteRequireH1H4Alignment;
   g_fxM15RouteHtfMode = InpFxM15RouteHtfMode;
   g_fxM15RouteRequireCleanWave = InpFxM15RouteRequireCleanWave;
   g_fxM15RouteRequireDragonExpansion = InpFxM15RouteRequireDragonExpansion;
   g_fxM15RouteBlockLateChase = InpFxM15RouteBlockLateChase;
   g_fxM15RouteMinSrRunwayPips = InpFxM15RouteMinSrRunwayPips;
   g_useXauTrapManagementRouter = InpUseXauTrapManagementRouter;
   g_xauTrapManageMinScore = InpXauTrapManageMinScore;
   g_xauTrapManageBars = InpXauTrapManageBars;
   g_xauTrapManageMinMfeR = InpXauTrapManageMinMfeR;
   g_xauTrapManageLateHour = InpXauTrapManageLateHour;
   g_xauTrapManageThursdayExtensionAtr = InpXauTrapManageThursdayExtensionAtr;
   g_useDragonPvsraEntryProxyGate = InpUseDragonPvsraEntryProxyGate;
   g_dragonPvsraRequireTrendPullback = InpDragonPvsraRequireTrendPullback;
   g_dragonPvsraBlockFlatDragon = InpDragonPvsraBlockFlatDragon;
   g_dragonPvsraBlockLateChase = InpDragonPvsraBlockLateChase;
   g_dragonPvsraRequirePvsraAlignment = InpDragonPvsraRequirePvsraAlignment;
   g_dragonPvsraMinRunwayPips = InpDragonPvsraMinRunwayPips;

   // Initialize runtime defaults for the 22 new variables
   g_levelGridMode = InpLevelGridMode;
   g_usePvsraParity = InpUsePvsraParity;
   g_classicTargetRR = InpClassicTargetRR;
   g_dragonPullbackTargetRR = InpDragonPullbackTargetRR;
   g_continuationTargetRR = InpContinuationTargetRR;
   g_reentryTargetRR = InpReentryTargetRR;
   g_scout2TargetRR = InpScout2TargetRR;
   g_dragonPullbackMaxExtensionATR = InpDragonPullbackMaxExtensionATR;
   g_dragonPullbackMaxDepthATR = InpDragonPullbackMaxDepthATR;
   g_continuationMaxPullbackATR = InpContinuationMaxPullbackATR;
   g_continuationMaxExtensionATR = InpContinuationMaxExtensionATR;
   g_minBreakoutDistanceATR = InpMinBreakoutDistanceATR;
   g_maxPullbackDepthATR = InpMaxPullbackDepthATR;
   g_breakoutLookbackBars = InpBreakoutLookbackBars;
   g_reentryLookbackBars = InpReentryLookbackBars;
   g_continuationLookbackBars = InpContinuationLookbackBars;
   g_dragonPullbackLookbackBars = InpDragonPullbackLookbackBars;
   g_minBodyRatio = InpMinBodyRatio;
   g_maxLayers = InpMaxLayers;
   g_useSoftHtfBias = InpUseSoftHtfBias;
   g_useTrendHardGate = InpUseTrendHardGate;
   g_spreadHardPips = InpSpreadHardPips;

   if(InpUseAutoSleeveConfig)
   {
      if(StringFind(sym, "EURUSD") >= 0)
      {
         // General Settings for EURUSD
         g_useRegimeRouter = false;
         g_useClassicTrend = true;
         g_useClassicReversal = false;
         g_onlyNewYorkReversal = false;
         g_useFxM15ReversalContextGate = false;
         g_useDragonExpansionFilter = false;
         g_dragonMaxExpansionRatio = 0.95;
         g_useArmedClassic = false;
         g_useDragonPullbackEntry = true;
         g_regimeRouterMinDragonSlope = 0.08;
         g_regimeRouterMinTrendSlope = 0.02;
         g_minDragonSlopeATR = 0.08;
         g_forceFlatOutsideSession = true;
         
         // Multi-Sleeve logic based on g_magic
         if(g_magic == 20260701)
         {
            // Sleeve 1 (Cadence Optimization V2)
            g_useLondon = true;
            g_useNewYork = true;
            g_useReentry = true;
            g_useContinuationPullback = true;
            g_useScoutProbe = true;
            g_useFxClassicStateQualityGate = false;
            g_minPvsraGradeClassic = 0;
            g_minMinutesToNewTrade = 0;
            g_useDynamicSMCStructure = false;
            g_useLiquiditySweep = false;
            g_useStructuralTrailing = false;
            g_useVolatilitySqueeze = false;
            g_stopAtrBuffer = 0.25;
            g_waveLookbackBars = 15;
            g_smcStructureLookback = 120;
            g_maxClassicBreakoutExtensionATR = 1.50;
            g_reentryMinPvsraGrade = 0;
            g_classicArmBars = 3;
            g_useXauClassicStateQualityGate = false;
            g_xauRangeAbsorptionMinTargetRR = 0.80;
            g_xauSweepReclaimMinTargetRR = 0.80;
            g_useClassicMinSLFloor = true;
            g_classicRiskPct = 0.35;
            g_secondLayerRiskPct = 0.15;
            g_maxNarrativeRiskPct = 0.50;
            g_fxClassicMinRunwayPips = 0.0;
            g_levelGridMode = 1;
            g_usePvsraParity = true;
            g_classicTargetRR = 1.60;
            g_dragonPullbackTargetRR = 1.25;
            g_continuationTargetRR = 1.20;
            g_reentryTargetRR = 1.35;
            g_scout2TargetRR = 1.10;
            g_dragonPullbackMaxExtensionATR = 0.65;
            g_dragonPullbackMaxDepthATR = 1.20;
            g_continuationMaxPullbackATR = 1.10;
            g_continuationMaxExtensionATR = 0.80;
            g_minBreakoutDistanceATR = 0.10;
            g_maxPullbackDepthATR = 1.40;
            g_breakoutLookbackBars = 4;
            g_reentryLookbackBars = 3;
            g_continuationLookbackBars = 4;
            g_dragonPullbackLookbackBars = 8;
            g_minBodyRatio = 0.45;
            g_maxLayers = 2;
            g_useSoftHtfBias = true;
            g_useTrendHardGate = true;
            g_spreadHardPips = 3.50;
            Print("[SNR] Auto-Sleeve: Applied EURUSD Sleeve 1 (Cadence Optimization V2) configuration.");
         }
         else
         {
            // Sleeve 2 (Dynamic Quant V_D) - Default for EURUSD
            g_useLondon = true;
            g_useNewYork = false; // London only
            g_useReentry = true;
            g_useContinuationPullback = true;
            g_useScoutProbe = true;
            g_useFxClassicStateQualityGate = false;
            g_minPvsraGradeClassic = 0;
            g_minMinutesToNewTrade = 0;
            g_useDynamicSMCStructure = true;
            g_useLiquiditySweep = true;
            g_useStructuralTrailing = false;
            g_useVolatilitySqueeze = false;
            g_stopAtrBuffer = 0.25;
            g_waveLookbackBars = 15;
            g_smcStructureLookback = 30;
            g_maxClassicBreakoutExtensionATR = 1.50;
            g_reentryMinPvsraGrade = 0;
            g_classicArmBars = 3;
            g_useXauClassicStateQualityGate = false;
            g_xauRangeAbsorptionMinTargetRR = 0.80;
            g_xauSweepReclaimMinTargetRR = 0.80;
            g_useClassicMinSLFloor = true;
            g_classicRiskPct = 0.35;
            g_secondLayerRiskPct = 0.15;
            g_maxNarrativeRiskPct = 0.50;
            g_fxClassicMinRunwayPips = 0.0;
            g_levelGridMode = 1;
            g_usePvsraParity = true;
            g_classicTargetRR = 1.60;
            g_dragonPullbackTargetRR = 1.25;
            g_continuationTargetRR = 1.20;
            g_reentryTargetRR = 1.35;
            g_scout2TargetRR = 1.10;
            g_dragonPullbackMaxExtensionATR = 0.65;
            g_dragonPullbackMaxDepthATR = 1.20;
            g_continuationMaxPullbackATR = 1.10;
            g_continuationMaxExtensionATR = 0.80;
            g_minBreakoutDistanceATR = 0.10;
            g_maxPullbackDepthATR = 1.40;
            g_breakoutLookbackBars = 4;
            g_reentryLookbackBars = 3;
            g_continuationLookbackBars = 4;
            g_dragonPullbackLookbackBars = 8;
            g_minBodyRatio = 0.45;
            g_maxLayers = 2;
            g_useSoftHtfBias = true;
            g_useTrendHardGate = true;
            g_spreadHardPips = 3.50;
            Print("[SNR] Auto-Sleeve: Applied EURUSD Sleeve 2 (Dynamic Quant V_D) configuration.");
         }
      }
      else if(StringFind(sym, "XAUUSD") >= 0 || StringFind(sym, "GOLD") >= 0)

      {

         // Sleeve 3 (Dynamic SMC V11 C BE) - Default for XAUUSD

         g_useRegimeRouter = true;

         g_useLondon = true;

         g_useNewYork = false; // London only

         g_useXauActiveClassic = true;

         g_useXauRangeAbsorption = true;

         g_useXauSweepReclaimExecution = true;

         

         g_useClassicTrend = false;

         g_useClassicReversal = false;

         g_onlyNewYorkReversal = false;

         g_useFxM15ReversalContextGate = false;

         g_useDragonExpansionFilter = false;

         g_useArmedClassic = false;

         g_useDragonPullbackEntry = false;

         g_goldMinCompressionRatio = 0.40;

         g_goldS1MinPvsraGrade = 2; // confirmed config v11 uses grade 2

         g_xauS1RequireWholeHalf = false;

         g_regimeRouterMinDragonSlope = 0.08;

         g_regimeRouterMinTrendSlope = 0.01; // v11 uses 0.01

         g_minDragonSlopeATR = 0.08;

         g_forceFlatOutsideSession = false;

         

         g_useReentry = false;

         g_useContinuationPullback = false;

         g_useScoutProbe = false;

         g_useFxClassicStateQualityGate = false;

         g_minPvsraGradeClassic = 2;

         g_minMinutesToNewTrade = 30;

         g_useDynamicSMCStructure = true;

         g_useLiquiditySweep = true;

         g_useStructuralTrailing = true;

         g_useVolatilitySqueeze = false;

         g_stopAtrBuffer = 2.0;

         

         g_waveLookbackBars = 8;

         g_smcStructureLookback = 30;

         g_maxClassicBreakoutExtensionATR = 1.50;

         g_reentryMinPvsraGrade = 2;

         g_classicArmBars = 10;

         g_useXauClassicStateQualityGate = false;

         g_xauRangeAbsorptionMinTargetRR = 1.50;

         g_xauSweepReclaimMinTargetRR = 1.50;

         g_useClassicMinSLFloor = true;

         g_scalpMinSLPips = 20.0;

         g_spreadSoftPips = 2.5;

         g_blockedEntryWeekdays = "Thursday";

         Print("[SNR] Auto-Sleeve: Applied XAUUSD Sleeve 3 (Dynamic SMC V11 C BE) configuration.");

      }

      else if(StringFind(sym, "GBPUSD") >= 0)

      {

         g_useRegimeRouter = false;

         g_useClassicTrend = true;

         g_useClassicReversal = false;

         g_onlyNewYorkReversal = false;

         g_useFxM15ReversalContextGate = false;

         g_useDragonExpansionFilter = false;

         g_useArmedClassic = false;

         g_useDragonPullbackEntry = false;

         g_regimeRouterMinDragonSlope = 0.08;

         g_regimeRouterMinTrendSlope = 0.02;

         g_minDragonSlopeATR = 0.08;

         g_forceFlatOutsideSession = false;

         Print("[SNR] Auto-Sleeve: Applied GBPUSD Trend-only configuration.");

      }

      else if(StringFind(sym, "USDJPY") >= 0 ||

              StringFind(sym, "EURJPY") >= 0 ||

              StringFind(sym, "GBPJPY") >= 0)

      {

         g_useRegimeRouter = false;

         g_useClassicTrend = true;

         g_useClassicReversal = false;

         g_onlyNewYorkReversal = false;

         g_useFxM15ReversalContextGate = false;

         g_useDragonExpansionFilter = false;

         g_useArmedClassic = false;

         g_useDragonPullbackEntry = false;

         g_regimeRouterMinDragonSlope = 0.08;

         g_regimeRouterMinTrendSlope = 0.02;

         g_minDragonSlopeATR = 0.08;

         g_forceFlatOutsideSession = false;

         PrintFormat("[SNR] Auto-Sleeve: Applied %s JPY Classic Trend configuration.", symbol);

      }

      else if(StringFind(sym, "AUDUSD") >= 0 ||

              StringFind(sym, "NZDUSD") >= 0)

      {

         g_useRegimeRouter = false;

         g_useClassicTrend = true;

         g_useClassicReversal = false;

         g_onlyNewYorkReversal = false;

         g_useFxM15ReversalContextGate = false;

         g_useDragonExpansionFilter = false;

         g_useArmedClassic = false;

         g_useDragonPullbackEntry = false;

         g_regimeRouterMinDragonSlope = 0.08;

         g_regimeRouterMinTrendSlope = 0.02;

         g_minDragonSlopeATR = 0.08;

         g_forceFlatOutsideSession = false;

         PrintFormat("[SNR] Auto-Sleeve: Applied %s Commodity FX Classic Trend configuration.", symbol);

      }

      else if(StringFind(sym, "USDCAD") >= 0 ||

              StringFind(sym, "USDCHF") >= 0)

      {

         g_useRegimeRouter = false;

         g_useClassicTrend = true;

         g_useClassicReversal = false;

         g_onlyNewYorkReversal = false;

         g_useFxM15ReversalContextGate = false;

         g_useDragonExpansionFilter = false;

         g_useArmedClassic = false;

         g_useDragonPullbackEntry = false;

         g_regimeRouterMinDragonSlope = 0.08;

         g_regimeRouterMinTrendSlope = 0.02;

         g_minDragonSlopeATR = 0.08;

         g_forceFlatOutsideSession = false;

         PrintFormat("[SNR] Auto-Sleeve: Applied %s Americas/Safe-Haven Classic Trend configuration.", symbol);

      }

      else

      {

         PrintFormat("[SNR] Auto-Sleeve: Unsupported symbol %s. Fallback to manual inputs.", symbol);

      }

   }

   else

   {

      Print("[SNR] Auto-Sleeve: Disabled. Manual input overrides mapped to globals.");

   }

}



#endif



