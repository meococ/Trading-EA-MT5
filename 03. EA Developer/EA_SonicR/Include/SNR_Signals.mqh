#ifndef SNR_SIGNALS_MQH
#define SNR_SIGNALS_MQH

double SNR_HighestHigh(const MqlRates &rates[], const int from_idx, const int to_idx)
{
   double value = -DBL_MAX;
   for(int i = from_idx; i <= to_idx; i++)
      value = MathMax(value, rates[i].high);
   return value;
}

double SNR_LowestLow(const MqlRates &rates[], const int from_idx, const int to_idx)
{
   double value = DBL_MAX;
   for(int i = from_idx; i <= to_idx; i++)
      value = MathMin(value, rates[i].low);
   return value;
}

bool SNR_HasSetupVolumeClimax(const MqlRates &rates[], const int count, const int lookback_bars)
{
   int limit = MathMin(count, lookback_bars);
   if(limit <= 0)
      return false;
      
   double vol_sum = 0.0;
   int vol_count = 0;
   int start_idx = limit;
   for(int i = start_idx; i < start_idx + 20 && i < count; i++)
   {
      vol_sum += (double)rates[i].tick_volume;
      vol_count++;
   }
   double vol_avg = (vol_count > 0) ? (vol_sum / vol_count) : 1.0;
   if(vol_avg <= 0.0)
      vol_avg = 1.0;
      
   for(int i = 0; i < limit; i++)
   {
      double ratio = (double)rates[i].tick_volume / vol_avg;
      if(ratio >= 2.0)
         return true;
   }
   return false;
}

string SNR_BuildWaveId(const datetime t, const string label, const int direction)
{
   MqlDateTime dt;
   TimeToStruct(t, dt);
   return StringFormat("%s_%s_%04d%02d%02d_%02d%02d",
                       label,
                       SNR_DirectionName(direction),
                       dt.year, dt.mon, dt.day,
                       dt.hour, dt.min);
}

void SNR_ResetSignal(SnrSignal &signal, const SnrMode mode, const int direction)
{
   signal.valid = false;
   signal.mode = mode;
   signal.direction = direction;
   signal.reason = "";
   signal.wave_id = "";
   signal.archetype = "";
   signal.setup_state = "OBSERVE";
   signal.invalidate_reason = "";
   signal.trigger_price = 0.0;
   signal.stop_price = 0.0;
   signal.target_rr = 0.0;
   signal.quality_score = -9999.0;
   signal.pullback_depth_atr = 0.0;
}

bool SNR_ClassicBodyOk(const SnrContext &ctx, const int pvsra_grade)
{
   if(ctx.body_ratio >= g_minBodyRatio)
      return true;
   if(!g_useClassicSourceCore || ctx.body_ratio < 0.25)
      return false;
   return (ctx.bar_range_atr >= 0.85 ||
           pvsra_grade >= g_minPvsraGradeClassic ||
           ctx.pvsra_event == "CLIMAX" ||
           ctx.pvsra_event == "RISING_ACTIVITY" ||
           ctx.level_zone != "NONE");
}

bool SNR_AllowClassicBlockedPvsraRoute(const SnrContext &ctx, const int direction)
{
   if(!g_useNy16ShortClimaxQuarterRoute)
      return false;
   return (direction < 0 &&
           ctx.session_bucket == "NEWYORK" &&
           ctx.hour_server == 16 &&
           ctx.pvsra_event == "CLIMAX" &&
           ctx.level_zone == "QUARTER");
}

bool SNR_ClassicLevelZoneBlocked(const SnrContext &ctx)
{
   if(ctx.level_zone == "" || ctx.level_zone == "NONE")
      return false;
   return SNR_ListContainsToken(g_blockedClassicLevelZones, ctx.level_zone);
}

bool SNR_FindClassicSignal(const SnrContext &ctx,
                           const int direction,
                           const int dragon_high_handle,
                           const int dragon_mid_handle,
                           const int dragon_low_handle,
                           const int atr_handle,
                           SnrSignal &signal)
{
   SNR_ResetSignal(signal, SNR_MODE_CLASSIC, direction);
   const double pip_size = SNR_CurrentPipSize();

   MqlRates rates[];
   double dragon_high[];
   double dragon_mid[];
   double dragon_low[];
   double atr[];

   const int bars_needed = MathMax(35, g_waveLookbackBars + 4);
   if(!SNR_CopyClosedRates(bars_needed, rates) ||
      !SNR_CopyClosedBuffer(dragon_high_handle, bars_needed, dragon_high) ||
      !SNR_CopyClosedBuffer(dragon_mid_handle, bars_needed, dragon_mid) ||
      !SNR_CopyClosedBuffer(dragon_low_handle, bars_needed, dragon_low) ||
      !SNR_CopyClosedBuffer(atr_handle, bars_needed, atr))
   {
      signal.reason = "DATA_UNAVAILABLE";
      return false;
   }

   if(g_requirePvsraVolume)
   {
      if(!SNR_HasSetupVolumeClimax(rates, bars_needed, g_volumeLookback))
      {
         signal.reason = "NO_SETUP_VOLUME_CLIMAX";
         return false;
      }
   }

   // Runway Validation check dynamic scaled by ATR to support M5/M15 timeframe adaptively
   double min_runway = 0.0;
   double atr_pips = (pip_size > 0.0) ? (ctx.atr / pip_size) : 0.0;
   if(StringFind(_Symbol, "XAU") >= 0)
   {
      double scale = (atr_pips > 0.0) ? (atr_pips / 15.0) : 1.0;
      min_runway = g_xauClassicMinRunwayPips * scale;
   }
   else
   {
      double scale = (atr_pips > 0.0) ? (atr_pips / 5.0) : 1.0;
      min_runway = g_fxClassicMinRunwayPips * scale;
   }

   if(min_runway > 0.0 && ctx.source_sr_runway_pips < min_runway)
   {
      if(ctx.source_sr_level_kind == "WHOLE" || ctx.source_sr_level_kind == "HALF")
      {
         signal.reason = "NOT_ENOUGH_RUNWAY";
         return false;
      }
   }

   // Dynamic Compression & Flat slope filter to prevent false breakouts in choppy ranges
   if(g_useDragonExpansionFilter)
   {
      if(ctx.dragon_dynamic_expansion_roc < 0.90 && MathAbs(ctx.dragon_slope_atr) < 0.08)
      {
         signal.reason = "DRAGON_COMPRESSED_FLAT";
         return false;
      }
   }

   // Volatility Squeeze Filter (coil activation condition: require squeeze within prior 10 bars)
   if(g_useVolatilitySqueeze)
   {
      bool had_squeeze = false;
      for(int i = 1; i <= 10 && i < bars_needed; i++)
      {
         double sd_i = SNR_StdDev(rates, 20, i);
         double bw_i = 4.0 * sd_i;
         double kw_i = 3.0 * atr[i];
         if(kw_i > 0.0 && (bw_i / kw_i) < 1.0)
         {
            had_squeeze = true;
            break;
         }
      }
      if(!had_squeeze)
      {
         signal.reason = "NO_PRIOR_SQUEEZE_COIL";
         return false;
      }
   }

   int base_pvsra_grade = SNR_DirectionalPvsraGrade(ctx, direction);
   int pvsra_grade = SNR_PvsraSrAdjustedClassicGrade(ctx, base_pvsra_grade, g_minPvsraGradeClassic, atr[0]);
   double breakout_buffer = g_minBreakoutDistanceATR * atr[0];
   bool blocked_event_route = SNR_AllowClassicBlockedPvsraRoute(ctx, direction);

   if(SNR_ListContainsToken(g_blockedClassicPvsraEvents, ctx.pvsra_event) && !blocked_event_route)
   {
      signal.reason = "CLASSIC_PVSRA_EVENT_BLOCK";
      return false;
   }
   if(SNR_ClassicLevelZoneBlocked(ctx))
   {
      signal.reason = "CLASSIC_LEVEL_ZONE_BLOCK";
      return false;
   }

   if(direction > 0)
   {
      if(!ctx.allow_long)
      {
         signal.reason = "LONG_CONTEXT_FAIL";
         return false;
      }
      if(!g_useClassicSourceCore && g_usePvsraParity && pvsra_grade < g_minPvsraGradeClassic)
      {
         signal.reason = "CLASSIC_PVSRA_WEAK";
         return false;
      }
      if(!SNR_ClassicBodyOk(ctx, pvsra_grade))
      {
         signal.reason = "WEAK_BODY";
         return false;
      }
      
      // Use dynamic SMC structure high if enabled, else fallback to static lookback swing high
      double prior_high = g_useDynamicSMCStructure ? ctx.market_structure_high : SNR_HighestHigh(rates, 1, g_breakoutLookbackBars);
      signal.trigger_price = MathMax(prior_high, dragon_high[0] + breakout_buffer);

      if(rates[0].close <= dragon_high[0] + breakout_buffer)
      {
         signal.reason = "NO_DRAGON_BREAK";
         return false;
      }
      if(rates[0].close <= prior_high)
      {
         signal.reason = "NO_SWING_BREAK";
         return false;
      }
      if(g_maxClassicBreakoutExtensionATR > 0.0 &&
         (rates[0].close - signal.trigger_price) / atr[0] > g_maxClassicBreakoutExtensionATR)
      {
         signal.reason = "CLASSIC_CHASE_EXTENSION";
         return false;
      }

      int touch_idx = -1;
      for(int i = 1; i <= g_waveLookbackBars; i++)
      {
         bool touched_dragon = (rates[i].low <= dragon_mid[i] + 0.15 * atr[i]);
         if(g_useClassicSourceCore)
            touched_dragon = (rates[i].low <= dragon_high[i] + 0.10 * atr[i]);
         if(touched_dragon)
         {
            touch_idx = i;
            break;
         }
      }
      
      // Sweep boost checks
      bool is_sweep_boost = (g_useLiquiditySweep && ctx.liquidity_sweep_active && ctx.liquidity_sweep_direction == 1);
      if(touch_idx < 0 && !is_sweep_boost)
      {
         signal.reason = "NO_PULLBACK_TOUCH";
         return false;
      }

      double pullback_low = (touch_idx >= 0) ? SNR_LowestLow(rates, 0, touch_idx) : rates[0].low;
      signal.pullback_depth_atr = (rates[0].close - pullback_low) / atr[0];
      if(signal.pullback_depth_atr > g_maxPullbackDepthATR)
      {
         signal.reason = "PULLBACK_TOO_DEEP";
         return false;
      }

      signal.stop_price = MathMin(pullback_low, dragon_low[0]) - g_stopAtrBuffer * atr[0];
      signal.target_rr = g_classicTargetRR;
      signal.valid = true;
      signal.wave_id = SNR_BuildWaveId((touch_idx >= 0 ? rates[touch_idx].time : rates[0].time), "CLASSIC", direction);
      signal.archetype = (blocked_event_route ? "ClassicPvsraEventRoute" : "ClassicTrend");
      signal.setup_state = "TRIGGER";
      signal.quality_score = ctx.context_score +
                             ctx.body_ratio +
                             signal.pullback_depth_atr * 0.25 +
                             0.35 * pvsra_grade +
                             (is_sweep_boost ? 1.50 : 0.0);
      return true;
   }

   if(!ctx.allow_short)
   {
      signal.reason = "SHORT_CONTEXT_FAIL";
      return false;
   }
   if(!g_useClassicSourceCore && g_usePvsraParity && pvsra_grade < g_minPvsraGradeClassic)
   {
      signal.reason = "CLASSIC_PVSRA_WEAK";
      return false;
   }
   if(!SNR_ClassicBodyOk(ctx, pvsra_grade))
   {
      signal.reason = "WEAK_BODY";
      return false;
   }
   
   // Use dynamic SMC structure low if enabled, else fallback to static lookback swing low
   double prior_low = g_useDynamicSMCStructure ? ctx.market_structure_low : SNR_LowestLow(rates, 1, g_breakoutLookbackBars);
   signal.trigger_price = MathMin(prior_low, dragon_low[0] - breakout_buffer);

   if(rates[0].close >= dragon_low[0] - breakout_buffer)
   {
      signal.reason = "NO_DRAGON_BREAK";
      return false;
   }
   if(rates[0].close >= prior_low)
   {
      signal.reason = "NO_SWING_BREAK";
      return false;
   }
   if(g_maxClassicBreakoutExtensionATR > 0.0 &&
      (signal.trigger_price - rates[0].close) / atr[0] > g_maxClassicBreakoutExtensionATR)
   {
      signal.reason = "CLASSIC_CHASE_EXTENSION";
      return false;
   }

   int touch_idx = -1;
   for(int i = 1; i <= g_waveLookbackBars; i++)
   {
      bool touched_dragon = (rates[i].high >= dragon_mid[i] - 0.15 * atr[i]);
      if(g_useClassicSourceCore)
         touched_dragon = (rates[i].high >= dragon_low[i] - 0.10 * atr[i]);
      if(touched_dragon)
      {
         touch_idx = i;
         break;
      }
   }
   
   // Sweep boost checks
   bool is_sweep_boost = (g_useLiquiditySweep && ctx.liquidity_sweep_active && ctx.liquidity_sweep_direction == -1);
   if(touch_idx < 0 && !is_sweep_boost)
   {
      signal.reason = "NO_PULLBACK_TOUCH";
      return false;
   }

   double pullback_high = (touch_idx >= 0) ? SNR_HighestHigh(rates, 0, touch_idx) : rates[0].high;
   signal.pullback_depth_atr = (pullback_high - rates[0].close) / atr[0];
   if(signal.pullback_depth_atr > g_maxPullbackDepthATR)
   {
      signal.reason = "PULLBACK_TOO_DEEP";
      return false;
   }

   signal.stop_price = MathMax(pullback_high, dragon_high[0]) + g_stopAtrBuffer * atr[0];
   signal.target_rr = g_classicTargetRR;
   signal.valid = true;
   signal.wave_id = SNR_BuildWaveId((touch_idx >= 0 ? rates[touch_idx].time : rates[0].time), "CLASSIC", direction);
   signal.archetype = (blocked_event_route ? "ClassicPvsraEventRoute" : "ClassicTrend");
   signal.setup_state = "TRIGGER";
   signal.quality_score = ctx.context_score +
                          ctx.body_ratio +
                          signal.pullback_depth_atr * 0.25 +
                          0.35 * pvsra_grade +
                          (is_sweep_boost ? 1.50 : 0.0);
   return true;
}

bool SNR_FindClassicArmCandidate(const SnrContext &ctx,
                                 const int direction,
                                 const int dragon_high_handle,
                                 const int dragon_mid_handle,
                                 const int dragon_low_handle,
                                 const int atr_handle,
                                 SnrSignal &signal)
{
   SNR_ResetSignal(signal, SNR_MODE_CLASSIC, direction);

   MqlRates rates[];
   double dragon_high[];
   double dragon_mid[];
   double dragon_low[];
   double atr[];

   const int bars_needed = MathMax(35, g_waveLookbackBars + 4);
   if(!SNR_CopyClosedRates(bars_needed, rates) ||
      !SNR_CopyClosedBuffer(dragon_high_handle, bars_needed, dragon_high) ||
      !SNR_CopyClosedBuffer(dragon_mid_handle, bars_needed, dragon_mid) ||
      !SNR_CopyClosedBuffer(dragon_low_handle, bars_needed, dragon_low) ||
      !SNR_CopyClosedBuffer(atr_handle, bars_needed, atr))
   {
      signal.reason = "DATA_UNAVAILABLE";
      return false;
   }

   if(g_requirePvsraVolume)
   {
      if(!SNR_HasSetupVolumeClimax(rates, bars_needed, g_volumeLookback))
      {
         signal.reason = "NO_SETUP_VOLUME_CLIMAX";
         return false;
      }
   }

   // Volatility Squeeze Filter (coil activation condition: require squeeze within prior 10 bars)
   if(g_useVolatilitySqueeze)
   {
      bool had_squeeze = false;
      for(int i = 1; i <= 10 && i < bars_needed; i++)
      {
         double sd_i = SNR_StdDev(rates, 20, i);
         double bw_i = 4.0 * sd_i;
         double kw_i = 3.0 * atr[i];
         if(kw_i > 0.0 && (bw_i / kw_i) < 1.0)
         {
            had_squeeze = true;
            break;
         }
      }
      if(!had_squeeze)
      {
         signal.reason = "NO_PRIOR_SQUEEZE_COIL";
         return false;
      }
   }

   int base_pvsra_grade = SNR_DirectionalPvsraGrade(ctx, direction);
   int pvsra_grade = SNR_PvsraSrAdjustedClassicGrade(ctx, base_pvsra_grade, g_minPvsraGradeClassic, atr[0]);
   double breakout_buffer = g_minBreakoutDistanceATR * atr[0];
   if(SNR_ClassicLevelZoneBlocked(ctx))
   {
      signal.reason = "ARM_LEVEL_ZONE_BLOCK";
      return false;
   }
   if(direction > 0)
   {
      if(!ctx.allow_long)
      {
         signal.reason = "LONG_CONTEXT_FAIL";
         return false;
      }
      if(g_usePvsraParity && pvsra_grade < g_minPvsraGradeClassic && ctx.level_zone == "NONE")
      {
         signal.reason = "ARM_PVSRA_LEVEL_WEAK";
         return false;
      }

      // Use dynamic SMC structure high if enabled, else fallback to static lookback swing high
      double prior_high = g_useDynamicSMCStructure ? ctx.market_structure_high : SNR_HighestHigh(rates, 1, g_breakoutLookbackBars);
      signal.trigger_price = MathMax(prior_high, dragon_high[0] + breakout_buffer);
      if(rates[0].close >= signal.trigger_price)
      {
         signal.reason = "BREAKOUT_ALREADY_CLOSED";
         return false;
      }

      int touch_idx = -1;
      for(int i = 0; i <= g_waveLookbackBars; i++)
      {
         if(rates[i].low <= dragon_mid[i] + 0.15 * atr[i])
         {
            touch_idx = i;
            break;
         }
      }
      if(touch_idx < 0)
      {
         signal.reason = "NO_PULLBACK_TOUCH";
         return false;
      }

      double pullback_low = SNR_LowestLow(rates, 0, touch_idx);
      signal.pullback_depth_atr = (signal.trigger_price - pullback_low) / atr[0];
      if(signal.pullback_depth_atr > g_maxPullbackDepthATR)
      {
         signal.reason = "PULLBACK_TOO_DEEP";
         return false;
      }

      signal.stop_price = MathMin(pullback_low, dragon_low[0]) - g_stopAtrBuffer * atr[0];
      signal.target_rr = g_classicTargetRR;
      signal.valid = true;
      signal.wave_id = SNR_BuildWaveId(rates[touch_idx].time, "CLASSIC_ARM", direction);
      signal.archetype = "ClassicTrendArmed";
      signal.setup_state = "ARM";
      signal.quality_score = ctx.context_score +
                             0.35 * pvsra_grade +
                             MathMin(0.75, ctx.body_ratio) +
                             0.15 * signal.pullback_depth_atr;
      return true;
   }

   if(!ctx.allow_short)
   {
      signal.reason = "SHORT_CONTEXT_FAIL";
      return false;
   }
   if(g_usePvsraParity && pvsra_grade < g_minPvsraGradeClassic && ctx.level_zone == "NONE")
   {
      signal.reason = "ARM_PVSRA_LEVEL_WEAK";
      return false;
   }

   // Use dynamic SMC structure low if enabled, else fallback to static lookback swing low
   double prior_low = g_useDynamicSMCStructure ? ctx.market_structure_low : SNR_LowestLow(rates, 1, g_breakoutLookbackBars);
   signal.trigger_price = MathMin(prior_low, dragon_low[0] - breakout_buffer);
   if(rates[0].close <= signal.trigger_price)
   {
      signal.reason = "BREAKOUT_ALREADY_CLOSED";
      return false;
   }

   int touch_idx = -1;
   for(int i = 0; i <= g_waveLookbackBars; i++)
   {
      if(rates[i].high >= dragon_mid[i] - 0.15 * atr[i])
      {
         touch_idx = i;
         break;
      }
   }
   if(touch_idx < 0)
   {
      signal.reason = "NO_PULLBACK_TOUCH";
      return false;
   }

   double pullback_high = SNR_HighestHigh(rates, 0, touch_idx);
   signal.pullback_depth_atr = (pullback_high - signal.trigger_price) / atr[0];
   if(signal.pullback_depth_atr > g_maxPullbackDepthATR)
   {
      signal.reason = "PULLBACK_TOO_DEEP";
      return false;
   }

   signal.stop_price = MathMax(pullback_high, dragon_high[0]) + g_stopAtrBuffer * atr[0];
   signal.target_rr = g_classicTargetRR;
   signal.valid = true;
   signal.wave_id = SNR_BuildWaveId(rates[touch_idx].time, "CLASSIC_ARM", direction);
   signal.archetype = "ClassicTrendArmed";
   signal.setup_state = "ARM";
   signal.quality_score = ctx.context_score +
                          0.35 * pvsra_grade +
                          MathMin(0.75, ctx.body_ratio) +
                          0.15 * signal.pullback_depth_atr;
   return true;
}

bool SNR_FindDragonPullbackEntrySignal(const SnrContext &ctx,
                                       const int direction,
                                       const int dragon_high_handle,
                                       const int dragon_mid_handle,
                                       const int dragon_low_handle,
                                       const int trend_handle,
                                       const int atr_handle,
                                       SnrSignal &signal)
{
   SNR_ResetSignal(signal, SNR_MODE_CLASSIC, direction);
   if(!g_useDragonPullbackEntry)
   {
      signal.reason = "DRAGON_PULLBACK_DISABLED";
      return false;
   }
   if(SNR_ListContainsToken(g_blockedClassicPvsraEvents, ctx.pvsra_event))
   {
      signal.reason = "DRAGON_PB_PVSRA_EVENT_BLOCK";
      return false;
   }
   if(SNR_ClassicLevelZoneBlocked(ctx))
   {
      signal.reason = "DRAGON_PB_LEVEL_ZONE_BLOCK";
      return false;
   }

   MqlRates rates[];
   double dragon_high[];
   double dragon_mid[];
   double dragon_low[];
   double trend[];
   double atr[];
   const int lookback = MathMax(3, g_dragonPullbackLookbackBars);
   const int bars_needed = MathMax(14, lookback + 5);
   if(!SNR_CopyClosedRates(bars_needed, rates) ||
      !SNR_CopyClosedBuffer(dragon_high_handle, bars_needed, dragon_high) ||
      !SNR_CopyClosedBuffer(dragon_mid_handle, bars_needed, dragon_mid) ||
      !SNR_CopyClosedBuffer(dragon_low_handle, bars_needed, dragon_low) ||
      !SNR_CopyClosedBuffer(trend_handle, bars_needed, trend) ||
      !SNR_CopyClosedBuffer(atr_handle, bars_needed, atr))
   {
      signal.reason = "DATA_UNAVAILABLE";
      return false;
   }

   if(g_requirePvsraVolume)
   {
      if(!SNR_HasSetupVolumeClimax(rates, bars_needed, g_volumeLookback))
      {
         signal.reason = "NO_SETUP_VOLUME_CLIMAX";
         return false;
      }
   }

   const double pip_size = SNR_CurrentPipSize();

   // Runway Validation check dynamic scaled by ATR to support M5/M15 timeframe adaptively
   if(g_dragonPvsraMinRunwayPips > 0.0)
   {
      double min_runway = 0.0;
      double atr_pips = (pip_size > 0.0) ? (ctx.atr / pip_size) : 0.0;
      if(StringFind(_Symbol, "XAU") >= 0)
      {
         double scale = (atr_pips > 0.0) ? (atr_pips / 15.0) : 1.0;
         min_runway = g_dragonPvsraMinRunwayPips * scale;
      }
      else
      {
         double scale = (atr_pips > 0.0) ? (atr_pips / 5.0) : 1.0;
         min_runway = g_dragonPvsraMinRunwayPips * scale;
      }

      if(ctx.source_sr_runway_pips < min_runway)
      {
         signal.reason = "DRAGON_PB_NOT_ENOUGH_RUNWAY";
         return false;
      }
   }

   // Dynamic Compression & Flat slope filter to prevent false breakouts in choppy ranges
   if(g_useDragonExpansionFilter)
   {
      if(ctx.dragon_dynamic_expansion_roc < 0.90 && MathAbs(ctx.dragon_slope_atr) < 0.08)
      {
         signal.reason = "DRAGON_COMPRESSED_FLAT";
         return false;
      }
   }

   int base_pvsra_grade = SNR_DirectionalPvsraGrade(ctx, direction);
   int pvsra_grade = SNR_PvsraSrAdjustedClassicGrade(ctx, base_pvsra_grade, g_minPvsraGradeClassic, atr[0]);
   if(g_usePvsraParity && pvsra_grade < g_minPvsraGradeClassic && ctx.level_zone == "NONE")
   {
      signal.reason = "DRAGON_PB_PVSRA_LEVEL_WEAK";
      return false;
   }
   if(!SNR_ClassicBodyOk(ctx, pvsra_grade))
   {
      signal.reason = "DRAGON_PB_WEAK_BODY";
      return false;
   }

   int last_idx = MathMin(lookback, bars_needed - 3);
   double slope_floor = MathMax(0.04, g_minDragonSlopeATR * 0.60);
   double max_pullback_atr = MathMax(0.35, g_dragonPullbackMaxDepthATR);
   double max_extension_atr = MathMax(0.10, g_dragonPullbackMaxExtensionATR);
   double level_bonus = (ctx.level_zone == "NONE" ? 0.0 : 0.25);

   if(direction > 0)
   {
      if(!ctx.allow_long)
      {
         signal.reason = "LONG_CONTEXT_FAIL";
         return false;
      }
      if(ctx.dragon_slope_atr < slope_floor || rates[0].close <= trend[0])
      {
         signal.reason = "DRAGON_PB_TREND_FAIL";
         return false;
      }

      int touch_idx = -1;
      for(int i = 1; i <= last_idx; i++)
      {
         if(rates[i].low <= dragon_mid[i] + 0.10 * atr[i] &&
            rates[i].close >= dragon_low[i] - 0.15 * atr[i])
         {
            touch_idx = i;
            break;
         }
      }
      if(touch_idx < 0)
      {
         signal.reason = "NO_DRAGON_PB_RETEST";
         return false;
      }

      bool prior_impulse = false;
      int impulse_end = MathMin(bars_needed - 1, last_idx + 2);
      for(int i = touch_idx + 1; i <= impulse_end; i++)
      {
         if(rates[i].close > dragon_high[i] + 0.05 * atr[i] && rates[i].close > trend[i])
         {
            prior_impulse = true;
            break;
         }
      }
      if(!prior_impulse)
      {
         signal.reason = "NO_DRAGON_PB_PRIOR_IMPULSE";
         return false;
      }

      double micro_high = SNR_HighestHigh(rates, 1, MathMin(3, last_idx));
      if(!(rates[0].close > rates[0].open &&
           rates[0].close > dragon_high[0] &&
           rates[0].close > MathMax(micro_high, dragon_mid[0])))
      {
         signal.reason = "NO_DRAGON_PB_CONFIRM";
         return false;
      }

      double pullback_low = SNR_LowestLow(rates, 0, touch_idx);
      signal.pullback_depth_atr = (rates[0].close - pullback_low) / atr[0];
      if(signal.pullback_depth_atr > max_pullback_atr)
      {
         signal.reason = "DRAGON_PB_TOO_DEEP";
         return false;
      }
      if((rates[0].close - dragon_mid[0]) / atr[0] > max_extension_atr)
      {
         signal.reason = "DRAGON_PB_CHASE_EXTENSION";
         return false;
      }

      signal.stop_price = MathMin(pullback_low, dragon_low[0]) - g_stopAtrBuffer * atr[0];
      signal.target_rr = g_dragonPullbackTargetRR;
      signal.valid = true;
      signal.wave_id = SNR_BuildWaveId(rates[touch_idx].time, "DRAGON_PB", direction);
      signal.archetype = "DragonPullbackEntry";
      signal.setup_state = "TRIGGER";
      signal.quality_score = ctx.context_score +
                             MathMin(0.75, ctx.body_ratio) +
                             0.35 * pvsra_grade +
                             level_bonus +
                             0.25 * (1.0 - MathMin(1.0, signal.pullback_depth_atr / max_pullback_atr));
      return true;
   }

   if(!ctx.allow_short)
   {
      signal.reason = "SHORT_CONTEXT_FAIL";
      return false;
   }
   if(ctx.dragon_slope_atr > -slope_floor || rates[0].close >= trend[0])
   {
      signal.reason = "DRAGON_PB_TREND_FAIL";
      return false;
   }

   int touch_idx = -1;
   for(int i = 1; i <= last_idx; i++)
   {
      if(rates[i].high >= dragon_mid[i] - 0.10 * atr[i] &&
         rates[i].close <= dragon_high[i] + 0.15 * atr[i])
      {
         touch_idx = i;
         break;
      }
   }
   if(touch_idx < 0)
   {
      signal.reason = "NO_DRAGON_PB_RETEST";
      return false;
   }

   bool prior_impulse = false;
   int impulse_end = MathMin(bars_needed - 1, last_idx + 2);
   for(int i = touch_idx + 1; i <= impulse_end; i++)
   {
      if(rates[i].close < dragon_low[i] - 0.05 * atr[i] && rates[i].close < trend[i])
      {
         prior_impulse = true;
         break;
      }
   }
   if(!prior_impulse)
   {
      signal.reason = "NO_DRAGON_PB_PRIOR_IMPULSE";
      return false;
   }

   double micro_low = SNR_LowestLow(rates, 1, MathMin(3, last_idx));
   if(!(rates[0].close < rates[0].open &&
        rates[0].close < dragon_low[0] &&
        rates[0].close < MathMin(micro_low, dragon_mid[0])))
   {
      signal.reason = "NO_DRAGON_PB_CONFIRM";
      return false;
   }

   double pullback_high = SNR_HighestHigh(rates, 0, touch_idx);
   signal.pullback_depth_atr = (pullback_high - rates[0].close) / atr[0];
   if(signal.pullback_depth_atr > max_pullback_atr)
   {
      signal.reason = "DRAGON_PB_TOO_DEEP";
      return false;
   }
   if((dragon_mid[0] - rates[0].close) / atr[0] > max_extension_atr)
   {
      signal.reason = "DRAGON_PB_CHASE_EXTENSION";
      return false;
   }

   signal.stop_price = MathMax(pullback_high, dragon_high[0]) + g_stopAtrBuffer * atr[0];
   signal.target_rr = g_dragonPullbackTargetRR;
   signal.valid = true;
   signal.wave_id = SNR_BuildWaveId(rates[touch_idx].time, "DRAGON_PB", direction);
   signal.archetype = "DragonPullbackEntry";
   signal.setup_state = "TRIGGER";
   signal.quality_score = ctx.context_score +
                          MathMin(0.75, ctx.body_ratio) +
                          0.35 * pvsra_grade +
                          level_bonus +
                          0.25 * (1.0 - MathMin(1.0, signal.pullback_depth_atr / max_pullback_atr));
   return true;
}

bool SNR_FindEurLondonShortCleanRouteSignal(const SnrContext &ctx,
                                            const int dragon_high_handle,
                                            const int dragon_mid_handle,
                                            const int dragon_low_handle,
                                            const int trend_handle,
                                            const int atr_handle,
                                            SnrSignal &signal)
{
   SNR_ResetSignal(signal, SNR_MODE_CLASSIC, SNR_DIR_SHORT);
   if(!g_useEurLondonShortCleanRoute)
   {
      signal.reason = "EUR_LDN_SHORT_DISABLED";
      return false;
   }
   if(StringFind(_Symbol, "EURUSD") != 0)
   {
      signal.reason = "EUR_LDN_SHORT_SYMBOL_SCOPE";
      return false;
   }
   if(_Period != PERIOD_M5)
   {
      signal.reason = "EUR_LDN_SHORT_TIMEFRAME_SCOPE";
      return false;
   }
   if(ctx.session_bucket != "LONDON" || ctx.hour_server != 11)
   {
      signal.reason = "EUR_LDN_SHORT_SESSION_SCOPE";
      return false;
   }
   if(ctx.pvsra_event != "NONE" || ctx.level_zone != "NONE" || ctx.pvsra_grade > 2)
   {
      signal.reason = "EUR_LDN_SHORT_NOT_CLEAN";
      return false;
   }
   if(!ctx.allow_short || ctx.h1_bias != -1 || ctx.h4_bias != -1)
   {
      signal.reason = "EUR_LDN_SHORT_CONTEXT_FAIL";
      return false;
   }

   MqlRates rates[];
   double dragon_high[];
   double dragon_mid[];
   double dragon_low[];
   double trend[];
   double atr[];
   const int lookback = 4;
   const int bars_needed = 10;
   if(!SNR_CopyClosedRates(bars_needed, rates) ||
      !SNR_CopyClosedBuffer(dragon_high_handle, bars_needed, dragon_high) ||
      !SNR_CopyClosedBuffer(dragon_mid_handle, bars_needed, dragon_mid) ||
      !SNR_CopyClosedBuffer(dragon_low_handle, bars_needed, dragon_low) ||
      !SNR_CopyClosedBuffer(trend_handle, bars_needed, trend) ||
      !SNR_CopyClosedBuffer(atr_handle, bars_needed, atr))
   {
      signal.reason = "DATA_UNAVAILABLE";
      return false;
   }

   const double dragon_floor = MathMax(0.25, g_minDragonSlopeATR * 2.0);
   if(ctx.dragon_slope_atr > -dragon_floor || ctx.trend_slope_atr > -0.10 || rates[0].close >= trend[0])
   {
      signal.reason = "EUR_LDN_SHORT_TREND_FAIL";
      return false;
   }

   int last_idx = MathMin(lookback, bars_needed - 2);
   bool retested_dragon = false;
   for(int i = 1; i <= last_idx; i++)
   {
      if(rates[i].high >= dragon_low[i] - 0.10 * atr[i] &&
         rates[i].close <= dragon_high[i] + 0.20 * atr[i])
      {
         retested_dragon = true;
         break;
      }
   }
   if(!retested_dragon)
   {
      signal.reason = "EUR_LDN_SHORT_NO_RETEST";
      return false;
   }

   double micro_low = SNR_LowestLow(rates, 1, MathMin(2, last_idx));
   if(!(rates[0].close < rates[0].open &&
        rates[0].close < dragon_mid[0] &&
        (rates[0].close < dragon_low[0] || rates[0].close < micro_low)))
   {
      signal.reason = "EUR_LDN_SHORT_NO_CONFIRM";
      return false;
   }
   if((dragon_mid[0] - rates[0].close) / atr[0] > 0.75)
   {
      signal.reason = "EUR_LDN_SHORT_CHASE_EXTENSION";
      return false;
   }

   double pullback_high = SNR_HighestHigh(rates, 0, last_idx);
   signal.pullback_depth_atr = (pullback_high - rates[0].close) / atr[0];
   if(signal.pullback_depth_atr > 1.20)
   {
      signal.reason = "EUR_LDN_SHORT_TOO_DEEP";
      return false;
   }

   signal.stop_price = MathMax(pullback_high, dragon_high[0]) + g_stopAtrBuffer * atr[0];
   signal.target_rr = g_eurLondonShortRouteTargetRR;
   signal.valid = true;
   signal.wave_id = SNR_BuildWaveId(rates[0].time, "EUR_LDN_SHORT", SNR_DIR_SHORT);
   signal.archetype = "EurLondonShortCleanRoute";
   signal.setup_state = "TRIGGER";
   signal.quality_score = ctx.context_score +
                          MathMin(0.75, ctx.body_ratio) +
                          0.35 * (1.0 - MathMin(1.0, signal.pullback_depth_atr / 1.20));
   return true;
}

bool SNR_FindClassicReversalSignal(const SnrContext &ctx,
                                   const int direction,
                                   const int dragon_high_handle,
                                   const int dragon_mid_handle,
                                   const int dragon_low_handle,
                                   const int atr_handle,
                                   SnrSignal &signal)
{
   SNR_ResetSignal(signal, SNR_MODE_CLASSIC, direction);
   if(!g_useClassicReversal)
   {
      signal.reason = "REVERSAL_DISABLED";
      return false;
   }
   if(!g_usePvsraParity || ctx.pvsra_grade < g_minPvsraGradeReversal || ctx.level_zone == "NONE")
   {
      signal.reason = "REVERSAL_CONTEXT_WEAK";
      return false;
   }

   MqlRates rates[];
   double dragon_high[];
   double dragon_mid[];
   double dragon_low[];
   double atr[];
   const int bars_needed = MathMax(8, g_waveLookbackBars + 2);
   if(!SNR_CopyClosedRates(bars_needed, rates) ||
      !SNR_CopyClosedBuffer(dragon_high_handle, bars_needed, dragon_high) ||
      !SNR_CopyClosedBuffer(dragon_mid_handle, bars_needed, dragon_mid) ||
      !SNR_CopyClosedBuffer(dragon_low_handle, bars_needed, dragon_low) ||
      !SNR_CopyClosedBuffer(atr_handle, bars_needed, atr))
   {
      signal.reason = "DATA_UNAVAILABLE";
      return false;
   }

   if(g_requirePvsraVolume)
   {
      if(!SNR_HasSetupVolumeClimax(rates, bars_needed, g_volumeLookback))
      {
         signal.reason = "NO_SETUP_VOLUME_CLIMAX";
         return false;
      }
   }

   if(ctx.body_ratio < g_minBodyRatio || ctx.bar_range_atr < 0.80)
   {
      signal.reason = "REVERSAL_PA_WEAK";
      return false;
   }

   if(direction > 0)
   {
      if(ctx.pvsra_bias != "BULLISH" || ctx.htf_bias_score < -1)
      {
         signal.reason = "REVERSAL_BIAS_FAIL";
         return false;
      }
      if(!(rates[1].close < dragon_mid[1] && rates[0].close > dragon_mid[0] && rates[0].close > rates[0].open))
      {
         signal.reason = "NO_REVERSAL_RECLAIM";
         return false;
      }
      double pullback_low = SNR_LowestLow(rates, 0, MathMin(3, bars_needed - 1));
      signal.stop_price = MathMin(pullback_low, dragon_low[0]) - g_stopAtrBuffer * atr[0];
      signal.pullback_depth_atr = (rates[0].close - pullback_low) / atr[0];
   }
   else
   {
      if(ctx.pvsra_bias != "BEARISH" || ctx.htf_bias_score > 1)
      {
         signal.reason = "REVERSAL_BIAS_FAIL";
         return false;
      }
      if(!(rates[1].close > dragon_mid[1] && rates[0].close < dragon_mid[0] && rates[0].close < rates[0].open))
      {
         signal.reason = "NO_REVERSAL_REJECT";
         return false;
      }
      double pullback_high = SNR_HighestHigh(rates, 0, MathMin(3, bars_needed - 1));
      signal.stop_price = MathMax(pullback_high, dragon_high[0]) + g_stopAtrBuffer * atr[0];
      signal.pullback_depth_atr = (pullback_high - rates[0].close) / atr[0];
   }

   signal.valid = true;
   signal.target_rr = g_reentryTargetRR;
   signal.wave_id = SNR_BuildWaveId(rates[0].time, "REVERSAL", direction);
   signal.archetype = "ClassicReversal";
   signal.setup_state = "TRIGGER";
   signal.quality_score = ctx.context_score + 0.45 * ctx.pvsra_grade + (ctx.level_zone == "WHOLE" ? 0.50 : 0.25);
   return true;
}

bool SNR_FindContinuationPullbackSignal(const SnrContext &ctx,
                                        const SnrNarrative &narrative,
                                        const int dragon_high_handle,
                                        const int dragon_mid_handle,
                                        const int dragon_low_handle,
                                        const int trend_handle,
                                        const int atr_handle,
                                        SnrSignal &signal)
{
   SNR_ResetSignal(signal, SNR_MODE_CONTINUATION, narrative.direction);
   if(!g_useContinuationPullback)
   {
      signal.reason = "CONTINUATION_DISABLED";
      return false;
   }
   if(!narrative.active || !narrative.classic_seeded)
   {
      signal.reason = "NO_NARRATIVE";
      return false;
   }
   if(narrative.layers_opened >= g_maxLayers)
   {
      signal.reason = "MAX_LAYERS";
      return false;
   }

   MqlRates rates[];
   double dragon_high[];
   double dragon_mid[];
   double dragon_low[];
   double trend[];
   double atr[];
   const int lookback = MathMax(2, g_continuationLookbackBars);
   const int bars_needed = MathMax(10, lookback + 4);
   if(!SNR_CopyClosedRates(bars_needed, rates) ||
      !SNR_CopyClosedBuffer(dragon_high_handle, bars_needed, dragon_high) ||
      !SNR_CopyClosedBuffer(dragon_mid_handle, bars_needed, dragon_mid) ||
      !SNR_CopyClosedBuffer(dragon_low_handle, bars_needed, dragon_low) ||
      !SNR_CopyClosedBuffer(trend_handle, bars_needed, trend) ||
      !SNR_CopyClosedBuffer(atr_handle, bars_needed, atr))
   {
      signal.reason = "DATA_UNAVAILABLE";
      return false;
   }

   if(g_requirePvsraVolume)
   {
      if(!SNR_HasSetupVolumeClimax(rates, bars_needed, g_volumeLookback))
      {
         signal.reason = "NO_SETUP_VOLUME_CLIMAX";
         return false;
      }
   }

   int direction = narrative.direction;
   int pvsra_grade = SNR_DirectionalPvsraGrade(ctx, direction);
   if(g_usePvsraParity && pvsra_grade < g_reentryMinPvsraGrade && ctx.level_zone == "NONE")
   {
      signal.reason = "CONTINUATION_PVSRA_LEVEL_WEAK";
      return false;
   }

   int last_idx = MathMin(lookback, bars_needed - 2);
   double slope_floor = MathMax(0.02, g_minDragonSlopeATR * 0.50);
   double level_bonus = (ctx.level_zone == "NONE" ? 0.0 : 0.25);
   double max_pullback_atr = MathMax(0.25, g_continuationMaxPullbackATR);
   double max_extension_atr = MathMax(0.10, g_continuationMaxExtensionATR);

   if(direction > 0)
   {
      if(!ctx.allow_long)
      {
         signal.reason = "LONG_CONTEXT_FAIL";
         return false;
      }
      if(ctx.dragon_slope_atr < slope_floor || rates[0].close <= trend[0])
      {
         signal.reason = "CONTINUATION_TREND_FAIL";
         return false;
      }

      bool touched_dragon = false;
      for(int i = 0; i <= last_idx; i++)
      {
         if(rates[i].low <= dragon_high[i] + 0.10 * atr[i])
         {
            touched_dragon = true;
            break;
         }
      }
      if(!touched_dragon)
      {
         signal.reason = "NO_CONTINUATION_PULLBACK";
         return false;
      }
      if(!(rates[0].close > rates[0].open && rates[0].close > dragon_high[0] && rates[0].close > dragon_mid[0]))
      {
         signal.reason = "NO_CONTINUATION_CONFIRM";
         return false;
      }

      double pullback_low = SNR_LowestLow(rates, 0, last_idx);
      signal.pullback_depth_atr = (rates[0].close - pullback_low) / atr[0];
      if(signal.pullback_depth_atr > max_pullback_atr)
      {
         signal.reason = "CONTINUATION_PULLBACK_TOO_DEEP";
         return false;
      }
      if((rates[0].close - dragon_mid[0]) / atr[0] > max_extension_atr)
      {
         signal.reason = "CONTINUATION_CHASE_EXTENSION";
         return false;
      }

      signal.stop_price = MathMin(pullback_low, dragon_low[0]) - g_stopAtrBuffer * atr[0];
      signal.target_rr = g_continuationTargetRR;
      signal.valid = true;
      signal.wave_id = narrative.wave_id + "_CPB";
      signal.archetype = "ContinuationPullback";
      signal.setup_state = "TRIGGER";
      signal.quality_score = ctx.context_score +
                             0.35 * pvsra_grade +
                             MathMin(0.75, ctx.body_ratio) +
                             level_bonus +
                             0.35 * (1.0 - MathMin(1.0, signal.pullback_depth_atr / max_pullback_atr));
      return true;
   }

   if(!ctx.allow_short)
   {
      signal.reason = "SHORT_CONTEXT_FAIL";
      return false;
   }
   if(ctx.dragon_slope_atr > -slope_floor || rates[0].close >= trend[0])
   {
      signal.reason = "CONTINUATION_TREND_FAIL";
      return false;
   }

   bool touched_dragon = false;
   for(int i = 0; i <= last_idx; i++)
   {
      if(rates[i].high >= dragon_low[i] - 0.10 * atr[i])
      {
         touched_dragon = true;
         break;
      }
   }
   if(!touched_dragon)
   {
      signal.reason = "NO_CONTINUATION_PULLBACK";
      return false;
   }
   if(!(rates[0].close < rates[0].open && rates[0].close < dragon_low[0] && rates[0].close < dragon_mid[0]))
   {
      signal.reason = "NO_CONTINUATION_CONFIRM";
      return false;
   }

   double pullback_high = SNR_HighestHigh(rates, 0, last_idx);
   signal.pullback_depth_atr = (pullback_high - rates[0].close) / atr[0];
   if(signal.pullback_depth_atr > max_pullback_atr)
   {
      signal.reason = "CONTINUATION_PULLBACK_TOO_DEEP";
      return false;
   }
   if((dragon_mid[0] - rates[0].close) / atr[0] > max_extension_atr)
   {
      signal.reason = "CONTINUATION_CHASE_EXTENSION";
      return false;
   }

   signal.stop_price = MathMax(pullback_high, dragon_high[0]) + g_stopAtrBuffer * atr[0];
   signal.target_rr = g_continuationTargetRR;
   signal.valid = true;
   signal.wave_id = narrative.wave_id + "_CPB";
   signal.archetype = "ContinuationPullback";
   signal.setup_state = "TRIGGER";
   signal.quality_score = ctx.context_score +
                          0.35 * pvsra_grade +
                          MathMin(0.75, ctx.body_ratio) +
                          level_bonus +
                          0.35 * (1.0 - MathMin(1.0, signal.pullback_depth_atr / max_pullback_atr));
   return true;
}

bool SNR_FindReentrySignal(const SnrContext &ctx,
                           const SnrNarrative &narrative,
                           const int dragon_high_handle,
                           const int dragon_mid_handle,
                           const int dragon_low_handle,
                           const int trend_handle,
                           const int atr_handle,
                           SnrSignal &signal)
{
   SNR_ResetSignal(signal, SNR_MODE_REENTRY, narrative.direction);
   if(!g_useReentry)
   {
      signal.reason = "REENTRY_DISABLED";
      return false;
   }
   if(!narrative.active || !narrative.classic_seeded)
   {
      signal.reason = "NO_NARRATIVE";
      return false;
   }
   if(narrative.layers_opened >= g_maxLayers)
   {
      signal.reason = "MAX_LAYERS";
      return false;
   }

   MqlRates rates[];
   double dragon_high[];
   double dragon_mid[];
   double dragon_low[];
   double trend[];
   double atr[];
   const int bars_needed = 10;
   if(!SNR_CopyClosedRates(bars_needed, rates) ||
      !SNR_CopyClosedBuffer(dragon_high_handle, bars_needed, dragon_high) ||
      !SNR_CopyClosedBuffer(dragon_mid_handle, bars_needed, dragon_mid) ||
      !SNR_CopyClosedBuffer(dragon_low_handle, bars_needed, dragon_low) ||
      !SNR_CopyClosedBuffer(trend_handle, bars_needed, trend) ||
      !SNR_CopyClosedBuffer(atr_handle, bars_needed, atr))
   {
      signal.reason = "DATA_UNAVAILABLE";
      return false;
   }

   if(g_requirePvsraVolume)
   {
      if(!SNR_HasSetupVolumeClimax(rates, bars_needed, g_volumeLookback))
      {
         signal.reason = "NO_SETUP_VOLUME_CLIMAX";
         return false;
      }
   }

   int direction = narrative.direction;
   int pvsra_grade = SNR_DirectionalPvsraGrade(ctx, direction);
   if(pvsra_grade < g_reentryMinPvsraGrade)
   {
      signal.reason = "PVSRA_TOO_WEAK";
      return false;
   }

   if(direction > 0)
   {
      double retrace_low = SNR_LowestLow(rates, 1, g_reentryLookbackBars);
      if(retrace_low < trend[1])
      {
         signal.reason = "RETRACE_UNDER_TREND";
         return false;
      }

      double trigger = SNR_HighestHigh(rates, 1, g_reentryLookbackBars);
      if(rates[0].close <= MathMax(trigger, dragon_high[0]))
      {
         signal.reason = "NO_REENTRY_BREAK";
         return false;
      }

      signal.stop_price = MathMin(retrace_low, dragon_low[0]) - g_stopAtrBuffer * atr[0];
      signal.pullback_depth_atr = (rates[0].close - retrace_low) / atr[0];
      signal.target_rr = g_reentryTargetRR;
      signal.valid = true;
      signal.wave_id = narrative.wave_id + "_R2";
      signal.archetype = "Reentry";
      signal.setup_state = "TRIGGER";
      signal.quality_score = ctx.context_score + 0.40 * pvsra_grade + 0.50;
      return true;
   }

   double retrace_high = SNR_HighestHigh(rates, 1, g_reentryLookbackBars);
   if(retrace_high > trend[1])
   {
      signal.reason = "RETRACE_OVER_TREND";
      return false;
   }

   double trigger = SNR_LowestLow(rates, 1, g_reentryLookbackBars);
   if(rates[0].close >= MathMin(trigger, dragon_low[0]))
   {
      signal.reason = "NO_REENTRY_BREAK";
      return false;
   }

   signal.stop_price = MathMax(retrace_high, dragon_high[0]) + g_stopAtrBuffer * atr[0];
   signal.pullback_depth_atr = (retrace_high - rates[0].close) / atr[0];
   signal.target_rr = g_reentryTargetRR;
   signal.valid = true;
   signal.wave_id = narrative.wave_id + "_R2";
   signal.archetype = "Reentry";
   signal.setup_state = "TRIGGER";
   signal.quality_score = ctx.context_score + 0.40 * pvsra_grade + 0.50;
   return true;
}

bool SNR_FindScout2Signal(const SnrContext &ctx,
                          const SnrNarrative &narrative,
                          const int dragon_mid_handle,
                          const int dragon_low_handle,
                          const int dragon_high_handle,
                          const int atr_handle,
                          SnrSignal &signal)
{
   SNR_ResetSignal(signal, SNR_MODE_SCOUT2, narrative.direction);
   if(!g_useScoutProbe)
   {
      signal.reason = "SCOUT_DISABLED";
      return false;
   }
   if(!narrative.active || !narrative.classic_seeded)
   {
      signal.reason = "NO_NARRATIVE";
      return false;
   }
   if(narrative.layers_opened >= g_maxLayers)
   {
      signal.reason = "MAX_LAYERS";
      return false;
   }

   MqlRates rates[];
   double dragon_mid[];
   double dragon_low[];
   double dragon_high[];
   double atr[];
   const int bars_needed = 8;
   if(!SNR_CopyClosedRates(bars_needed, rates) ||
      !SNR_CopyClosedBuffer(dragon_mid_handle, bars_needed, dragon_mid) ||
      !SNR_CopyClosedBuffer(dragon_low_handle, bars_needed, dragon_low) ||
      !SNR_CopyClosedBuffer(dragon_high_handle, bars_needed, dragon_high) ||
      !SNR_CopyClosedBuffer(atr_handle, bars_needed, atr))
   {
      signal.reason = "DATA_UNAVAILABLE";
      return false;
   }

   int direction = narrative.direction;
   int pvsra_grade = SNR_DirectionalPvsraGrade(ctx, direction);
   if(pvsra_grade < MathMax(g_scoutMinPvsraGrade, g_minPvsraGradeScout))
   {
      signal.reason = "SCOUT_PVSRA_WEAK";
      return false;
   }

   bool near_level = (ctx.level_zone != "NONE");
   if(direction > 0)
   {
      bool reclaim_dragon = (rates[0].low <= dragon_mid[0] + 0.10 * atr[0] &&
                             rates[0].close > dragon_mid[0] &&
                             rates[0].close > rates[0].open);
      if(!near_level && !reclaim_dragon)
      {
         signal.reason = "NO_SCOUT_LOCATION";
         return false;
      }

      signal.stop_price = MathMin(SNR_LowestLow(rates, 0, 2), dragon_low[0]) - g_stopAtrBuffer * atr[0];
      signal.pullback_depth_atr = (rates[0].close - SNR_LowestLow(rates, 0, 2)) / atr[0];
      signal.target_rr = g_scout2TargetRR;
      signal.valid = true;
      signal.wave_id = narrative.wave_id + "_SC2";
      signal.archetype = "ScoutProbe";
      signal.setup_state = "TRIGGER";
      signal.quality_score = ctx.context_score + 0.50 * pvsra_grade + (near_level ? 0.35 : 0.10);
      return true;
   }

   bool reject_dragon = (rates[0].high >= dragon_mid[0] - 0.10 * atr[0] &&
                         rates[0].close < dragon_mid[0] &&
                         rates[0].close < rates[0].open);
   if(!near_level && !reject_dragon)
   {
      signal.reason = "NO_SCOUT_LOCATION";
      return false;
   }

   signal.stop_price = MathMax(SNR_HighestHigh(rates, 0, 2), dragon_high[0]) + g_stopAtrBuffer * atr[0];
   signal.pullback_depth_atr = (SNR_HighestHigh(rates, 0, 2) - rates[0].close) / atr[0];
   signal.target_rr = g_scout2TargetRR;
   signal.valid = true;
   signal.wave_id = narrative.wave_id + "_SC2";
   signal.archetype = "ScoutProbe";
   signal.setup_state = "TRIGGER";
   signal.quality_score = ctx.context_score + 0.50 * pvsra_grade + (near_level ? 0.35 : 0.10);
   return true;
}

bool SNR_IsScalpSymbol(const string expected)
{
   return (_Symbol == expected);
}

bool SNR_IsLondonOrNewYork(const SnrContext &ctx)
{
   return (ctx.session_bucket == "LONDON" || ctx.session_bucket == "NEWYORK");
}

double SNR_BarBodyRatio(const MqlRates &bar)
{
   double range = bar.high - bar.low;
   if(range <= 0.0)
      return 0.0;
   return MathAbs(bar.close - bar.open) / range;
}

bool SNR_FindXauActiveClassicSignal(const SnrContext &ctx,
                                    const int dragon_high_handle,
                                    const int dragon_mid_handle,
                                    const int dragon_low_handle,
                                    const int atr_handle,
                                    SnrSignal &signal)
{
   SNR_ResetSignal(signal, SNR_MODE_XAU_ACTIVE_CLASSIC, ctx.regime_bias);
   if(!g_useRegimeRouter || !g_useXauActiveClassic)
   {
      signal.reason = "XAU_T1_DISABLED";
      return false;
   }
   if(!SNR_IsScalpSymbol("XAUUSD") || _Period != PERIOD_M5)
   {
      signal.reason = "XAU_T1_SYMBOL_TF";
      return false;
   }
   if((ctx.regime_state != SNR_REGIME_TREND && ctx.regime_state != SNR_REGIME_TRENDING_STRONG) || ctx.regime_bias == SNR_DIR_NONE)
   {
      signal.reason = "XAU_T1_NOT_TREND";
      return false;
   }
   if(!SNR_IsLondonOrNewYork(ctx))
   {
      signal.reason = "XAU_T1_SESSION";
      return false;
   }

   MqlRates rates[];
   double dragon_high[];
   double dragon_mid[];
   double dragon_low[];
   double atr[];
   const int bars_needed = 10;
   if(!SNR_CopyClosedRates(bars_needed, rates) ||
      !SNR_CopyClosedBuffer(dragon_high_handle, bars_needed, dragon_high) ||
      !SNR_CopyClosedBuffer(dragon_mid_handle, bars_needed, dragon_mid) ||
      !SNR_CopyClosedBuffer(dragon_low_handle, bars_needed, dragon_low) ||
      !SNR_CopyClosedBuffer(atr_handle, bars_needed, atr))
   {
      signal.reason = "DATA_UNAVAILABLE";
      return false;
   }
   if(atr[0] <= 0.0)
   {
      signal.reason = "ATR_INVALID";
      return false;
   }

   int direction = ctx.regime_bias;
   signal.direction = direction;
   if(SNR_BarBodyRatio(rates[0]) < 0.45)
   {
      signal.reason = "XAU_T1_BODY_WEAK";
      return false;
   }

   int touch_idx = -1;
   for(int i = 1; i <= 5; i++)
   {
      bool touched = (direction > 0 ?
                      rates[i].low <= dragon_high[i] + 0.05 * atr[i] :
                      rates[i].high >= dragon_low[i] - 0.05 * atr[i]);
      if(touched)
      {
         touch_idx = i;
         break;
      }
   }
   if(touch_idx < 1)
   {
      signal.reason = "XAU_T1_NO_RECENT_DRAGON_TOUCH";
      return false;
   }

   if(direction > 0)
   {
      if(rates[0].close <= SNR_HighestHigh(rates, 1, 4))
      {
         signal.reason = "XAU_T1_NO_MICRO_BREAK";
         return false;
      }
      if((rates[0].close - dragon_mid[0]) / atr[0] > 0.80)
      {
         signal.reason = "XAU_T1_CHASE_EXTENSION";
         return false;
      }

      double pullback_low = SNR_LowestLow(rates, 0, touch_idx);
      signal.stop_price = MathMin(pullback_low, dragon_low[0]) - 0.25 * atr[0];
      signal.pullback_depth_atr = (rates[0].close - pullback_low) / atr[0];
   }
   else
   {
      if(rates[0].close >= SNR_LowestLow(rates, 1, 4))
      {
         signal.reason = "XAU_T1_NO_MICRO_BREAK";
         return false;
      }
      if((dragon_mid[0] - rates[0].close) / atr[0] > 0.80)
      {
         signal.reason = "XAU_T1_CHASE_EXTENSION";
         return false;
      }

      double pullback_high = SNR_HighestHigh(rates, 0, touch_idx);
      signal.stop_price = MathMax(pullback_high, dragon_high[0]) + 0.25 * atr[0];
      signal.pullback_depth_atr = (pullback_high - rates[0].close) / atr[0];
   }

   signal.valid = true;
   signal.target_rr = 1.20;
   signal.wave_id = SNR_BuildWaveId(rates[touch_idx].time, "XAU_T1", direction);
   signal.archetype = "XAU_T1_ACTIVE_CLASSIC";
   signal.setup_state = "TRIGGER";
   signal.quality_score = ctx.context_score +
                          MathMin(0.75, SNR_BarBodyRatio(rates[0])) +
                          0.35 * MathAbs(ctx.dragon_slope_atr) +
                          0.20 * ctx.pvsra_grade;
   return true;
}

bool SNR_FindXauActiveClassicArmCandidate(const SnrContext &ctx,
                                          const int dragon_high_handle,
                                          const int dragon_mid_handle,
                                          const int dragon_low_handle,
                                          const int atr_handle,
                                          SnrSignal &signal)
{
   SNR_ResetSignal(signal, SNR_MODE_XAU_ACTIVE_CLASSIC, ctx.regime_bias);
   if(!g_useRegimeRouter || !g_useXauActiveClassic)
   {
      signal.reason = "XAU_T1_DISABLED";
      return false;
   }
   if(!SNR_IsScalpSymbol("XAUUSD") || _Period != PERIOD_M5)
   {
      signal.reason = "XAU_T1_SYMBOL_TF";
      return false;
   }
   if((ctx.regime_state != SNR_REGIME_TREND && ctx.regime_state != SNR_REGIME_TRENDING_STRONG) || ctx.regime_bias == SNR_DIR_NONE)
   {
      signal.reason = "XAU_T1_NOT_TREND";
      return false;
   }
   if(!SNR_IsLondonOrNewYork(ctx))
   {
      signal.reason = "XAU_T1_SESSION";
      return false;
   }

   MqlRates rates[];
   double dragon_high[];
   double dragon_mid[];
   double dragon_low[];
   double atr[];
   const int bars_needed = 10;
   if(!SNR_CopyClosedRates(bars_needed, rates) ||
      !SNR_CopyClosedBuffer(dragon_high_handle, bars_needed, dragon_high) ||
      !SNR_CopyClosedBuffer(dragon_mid_handle, bars_needed, dragon_mid) ||
      !SNR_CopyClosedBuffer(dragon_low_handle, bars_needed, dragon_low) ||
      !SNR_CopyClosedBuffer(atr_handle, bars_needed, atr))
   {
      signal.reason = "DATA_UNAVAILABLE";
      return false;
   }
   if(atr[0] <= 0.0)
   {
      signal.reason = "ATR_INVALID";
      return false;
   }

   int direction = ctx.regime_bias;
   signal.direction = direction;
   int touch_idx = -1;
   for(int i = 0; i <= 5; i++)
   {
      bool touched = (direction > 0 ?
                      rates[i].low <= dragon_high[i] + 0.08 * atr[i] :
                      rates[i].high >= dragon_low[i] - 0.08 * atr[i]);
      if(touched)
      {
         touch_idx = i;
         break;
      }
   }
   if(touch_idx < 0)
   {
      signal.reason = "XAU_T1_NO_PULLBACK_ARM";
      return false;
   }

   if(direction > 0)
   {
      if((rates[0].close - dragon_mid[0]) / atr[0] > 0.80)
      {
         signal.reason = "XAU_T1_ARM_CHASE_EXTENSION";
         return false;
      }
      signal.trigger_price = SNR_HighestHigh(rates, 0, 4);
      double pullback_low = SNR_LowestLow(rates, 0, MathMax(1, touch_idx));
      signal.stop_price = MathMin(pullback_low, dragon_low[0]) - 0.25 * atr[0];
      signal.pullback_depth_atr = (rates[0].close - pullback_low) / atr[0];
   }
   else
   {
      if((dragon_mid[0] - rates[0].close) / atr[0] > 0.80)
      {
         signal.reason = "XAU_T1_ARM_CHASE_EXTENSION";
         return false;
      }
      signal.trigger_price = SNR_LowestLow(rates, 0, 4);
      double pullback_high = SNR_HighestHigh(rates, 0, MathMax(1, touch_idx));
      signal.stop_price = MathMax(pullback_high, dragon_high[0]) + 0.25 * atr[0];
      signal.pullback_depth_atr = (pullback_high - rates[0].close) / atr[0];
   }

   signal.valid = true;
   signal.target_rr = 1.20;
   signal.wave_id = SNR_BuildWaveId(rates[MathMax(0, touch_idx)].time, "XAU_T1", direction);
   signal.archetype = "XAU_T1_ACTIVE_CLASSIC";
   signal.setup_state = "ARM";
   signal.quality_score = ctx.context_score +
                          0.35 * MathAbs(ctx.dragon_slope_atr) +
                          0.20 * ctx.pvsra_grade;
   return true;
}

void SNR_ArmXauT1Setup(const SnrContext &ctx,
                       const SnrSignal &candidate,
                       SnrClassicArm &arm)
{
   if(!candidate.valid)
      return;

   int arm_seconds = MathMax(3, g_classicArmBars) * PeriodSeconds(PERIOD_CURRENT);
   if(arm_seconds <= 0)
      arm_seconds = MathMax(3, g_classicArmBars) * 300;

   arm.active = true;
   arm.direction = candidate.direction;
   arm.armed_at = ctx.decision_time_server;
   arm.expires_at = ctx.decision_time_server + arm_seconds;
   arm.wave_id = candidate.wave_id;
   arm.archetype = candidate.archetype;
   arm.setup_state = "ARM";
   arm.level_zone = ctx.level_zone;
   arm.pvsra_grade = SNR_DirectionalPvsraGrade(ctx, candidate.direction);
   arm.context_score = ctx.context_score;
   arm.quality_score = candidate.quality_score;
   arm.pullback_depth_atr = candidate.pullback_depth_atr;
   arm.trigger_price = candidate.trigger_price;
   arm.stop_price = candidate.stop_price;
   arm.target_rr = candidate.target_rr;
}

bool SNR_BuildXauActiveClassicArmedSignal(const SnrContext &ctx,
                                          const int dragon_mid_handle,
                                          const int atr_handle,
                                          SnrClassicArm &arm,
                                          SnrSignal &signal)
{
   SNR_ResetSignal(signal, SNR_MODE_XAU_ACTIVE_CLASSIC, arm.direction);
   if(!arm.active)
   {
      signal.reason = "XAU_T1_ARM_EMPTY";
      return false;
   }
   if(ctx.decision_time_server > arm.expires_at || ctx.force_flat_now || ctx.session_bucket == "OFF")
   {
      SNR_ResetClassicArm(arm);
      signal.reason = "XAU_T1_ARM_EXPIRED";
      return false;
   }
   if((ctx.regime_state != SNR_REGIME_TREND && ctx.regime_state != SNR_REGIME_TRENDING_STRONG) || ctx.regime_bias != arm.direction)
   {
      SNR_ResetClassicArm(arm);
      signal.reason = "XAU_T1_ARM_CONTEXT_LOST";
      return false;
   }

   MqlRates rates[];
   double dragon_mid[];
   double atr[];
   const int bars_needed = 2;
   if(!SNR_CopyClosedRates(bars_needed, rates) ||
      !SNR_CopyClosedBuffer(dragon_mid_handle, bars_needed, dragon_mid) ||
      !SNR_CopyClosedBuffer(atr_handle, bars_needed, atr))
   {
      signal.reason = "DATA_UNAVAILABLE";
      return false;
   }
   if(atr[0] <= 0.0)
   {
      signal.reason = "ATR_INVALID";
      return false;
   }

   if(SNR_BarBodyRatio(rates[0]) < 0.45)
   {
      signal.reason = "XAU_T1_ARM_BODY_WAIT";
      return false;
   }

   bool triggered = false;
   if(arm.direction > 0)
   {
      triggered = (rates[0].close > arm.trigger_price);
      if((rates[0].close - dragon_mid[0]) / atr[0] > 0.80)
      {
         signal.reason = "XAU_T1_ARM_CHASE_EXTENSION";
         return false;
      }
   }
   else
   {
      triggered = (rates[0].close < arm.trigger_price);
      if((dragon_mid[0] - rates[0].close) / atr[0] > 0.80)
      {
         signal.reason = "XAU_T1_ARM_CHASE_EXTENSION";
         return false;
      }
   }

   if(!triggered)
   {
      signal.reason = "XAU_T1_ARM_WAIT";
      return false;
   }

   signal.valid = true;
   signal.direction = arm.direction;
   signal.wave_id = arm.wave_id;
   signal.archetype = arm.archetype;
   signal.setup_state = "TRIGGER";
   signal.invalidate_reason = "";
   signal.trigger_price = arm.trigger_price;
   signal.stop_price = arm.stop_price;
   signal.target_rr = arm.target_rr;
   signal.quality_score = arm.quality_score + MathMin(0.75, SNR_BarBodyRatio(rates[0]));
   signal.pullback_depth_atr = arm.pullback_depth_atr;
   SNR_ResetClassicArm(arm);
   return true;
}

bool SNR_FindXauRangeAbsorptionSignal(const SnrContext &ctx,
                                      const int dragon_mid_handle,
                                      const int atr_handle,
                                      SnrSignal &signal)
{
   SNR_ResetSignal(signal, SNR_MODE_XAU_RANGE_ABSORPTION, SNR_DIR_NONE);
   if(!g_useRegimeRouter || !g_useXauRangeAbsorption)
   {
      signal.reason = "XAU_R1_DISABLED";
      return false;
   }
   if(!SNR_IsScalpSymbol("XAUUSD") || _Period != PERIOD_M5)
   {
      signal.reason = "XAU_R1_SYMBOL_TF";
      return false;
   }
   if(!SNR_IsLondonOrNewYork(ctx))
   {
      signal.reason = "XAU_R1_SESSION";
      return false;
   }
   if(ctx.pvsra_grade < 3 && ctx.pvsra_event == "NONE")
   {
      signal.reason = "XAU_R1_PVSRA_WEAK";
      return false;
   }

   MqlRates rates[];
   double dragon_mid[];
   double atr[];
   const int bars_needed = 44;
   if(!SNR_CopyClosedRates(bars_needed, rates) ||
      !SNR_CopyClosedBuffer(dragon_mid_handle, bars_needed, dragon_mid) ||
      !SNR_CopyClosedBuffer(atr_handle, bars_needed, atr))
   {
      signal.reason = "DATA_UNAVAILABLE";
      return false;
   }
   if(atr[0] <= 0.0)
   {
      signal.reason = "XAU_R1_RANGE_INVALID";
      return false;
   }

   const int range_lookback = 36;
   double range_high = SNR_HighestHigh(rates, 1, range_lookback);
   double range_low = SNR_LowestLow(rates, 1, range_lookback);
   double range_width = range_high - range_low;
   double range_width_atr = range_width / atr[0];
   int cross_count = SNR_DragonCrossCount(rates, dragon_mid, 1, range_lookback);
   bool range_like = (range_width_atr >= 0.80 &&
                      range_width_atr <= 3.20 &&
                      MathAbs(ctx.dragon_slope_atr) < 0.12 &&
                      MathAbs(ctx.trend_slope_atr) < 0.06 &&
                      cross_count >= 3);
   if(!range_like)
   {
      signal.reason = "XAU_R1_NOT_PRIOR_RANGE";
      return false;
   }

   double range_mid = (range_high + range_low) * 0.5;
   double lower_quartile = range_low + 0.25 * range_width;
   double upper_quartile = range_high - 0.25 * range_width;
   double body_high = MathMax(rates[0].open, rates[0].close);
   double body_low = MathMin(rates[0].open, rates[0].close);
   double body = MathAbs(rates[0].close - rates[0].open);
   double lower_wick = body_low - rates[0].low;
   double upper_wick = rates[0].high - body_high;

    bool long_reclaim = (rates[0].low < range_low &&
                         rates[0].close > range_low &&
                         rates[0].close <= lower_quartile &&
                         rates[0].close > rates[0].open &&
                         lower_wick >= MathMax(0.10 * atr[0], 0.80 * body));
    bool short_reclaim = (rates[0].high > range_high &&
                          rates[0].close < range_high &&
                          rates[0].close >= upper_quartile &&
                          rates[0].close < rates[0].open &&
                          upper_wick >= MathMax(0.10 * atr[0], 0.80 * body));
   bool long_inner_rejection = (g_xauRangeAbsorptionAllowInnerRotation &&
                                rates[0].low <= lower_quartile &&
                                rates[0].close > lower_quartile &&
                                rates[0].close <= range_mid &&
                                rates[0].close > rates[0].open &&
                                lower_wick >= MathMax(0.08 * atr[0], 0.60 * body));
   bool short_inner_rejection = (g_xauRangeAbsorptionAllowInnerRotation &&
                                 rates[0].high >= upper_quartile &&
                                 rates[0].close < upper_quartile &&
                                 rates[0].close >= range_mid &&
                                 rates[0].close < rates[0].open &&
                                 upper_wick >= MathMax(0.08 * atr[0], 0.60 * body));
   double min_target_rr = MathMax(0.0, g_xauRangeAbsorptionMinTargetRR);

   if(long_reclaim || long_inner_rejection)
   {
      double entry_ref = rates[0].close;
      signal.direction = SNR_DIR_LONG;
      bool inner_rotation = (!long_reclaim && long_inner_rejection);
      signal.stop_price = (inner_rotation ? rates[0].low : MathMin(rates[0].low, range_low)) - 0.25 * atr[0];
      double risk = entry_ref - signal.stop_price;
      double reward = range_mid - entry_ref;
      if(risk <= 0.0 || reward / risk < min_target_rr)
      {
         signal.reason = "XAU_R1_RR_WEAK";
         return false;
      }
      signal.valid = true;
      signal.archetype = (inner_rotation ? "XAU_R1_RANGE_INNER_REJECTION" : "XAU_R1_RANGE_ABSORPTION");
   }
   else if(short_reclaim || short_inner_rejection)
   {
      double entry_ref = rates[0].close;
      signal.direction = SNR_DIR_SHORT;
      bool inner_rotation = (!short_reclaim && short_inner_rejection);
      signal.stop_price = (inner_rotation ? rates[0].high : MathMax(rates[0].high, range_high)) + 0.25 * atr[0];
      double risk = signal.stop_price - entry_ref;
      double reward = entry_ref - range_mid;
      if(risk <= 0.0 || reward / risk < min_target_rr)
      {
         signal.reason = "XAU_R1_RR_WEAK";
         return false;
      }
      signal.valid = true;
      signal.archetype = (inner_rotation ? "XAU_R1_RANGE_INNER_REJECTION" : "XAU_R1_RANGE_ABSORPTION");
   }
   else
   {
      signal.reason = "XAU_R1_NO_SWEEP_RECLAIM";
      return false;
   }

    signal.target_rr = (signal.direction > 0 ?
                        (range_mid - rates[0].close) / MathMax(_Point, rates[0].close - signal.stop_price) :
                        (rates[0].close - range_mid) / MathMax(_Point, signal.stop_price - rates[0].close));
    signal.wave_id = SNR_BuildWaveId(rates[0].time, "XAU_R1", signal.direction);
   if(signal.archetype == "")
      signal.archetype = "XAU_R1_RANGE_ABSORPTION";
   signal.setup_state = "TRIGGER";
   signal.pullback_depth_atr = range_width_atr;
   signal.quality_score = ctx.context_score +
                          0.45 * ctx.pvsra_grade +
                          MathMin(0.75, MathMax(lower_wick, upper_wick) / MathMax(_Point, body + _Point));
   return true;
}

bool SNR_SessionBox(const MqlRates &rates[],
                    const int bars_count,
                    const int start_min,
                    const int end_min,
                    const datetime reference_day,
                    double &box_high,
                    double &box_low)
{
   box_high = -DBL_MAX;
   box_low = DBL_MAX;
   int count = 0;
   MqlDateTime ref_dt;
   TimeToStruct(reference_day, ref_dt);

   for(int i = 0; i < bars_count; i++)
   {
      MqlDateTime dt;
      TimeToStruct(rates[i].time, dt);
      if(dt.year != ref_dt.year || dt.mon != ref_dt.mon || dt.day != ref_dt.day)
         continue;
      int minutes = SNR_MinutesOfDay(dt.hour, dt.min);
      if(minutes < start_min || minutes >= end_min)
         continue;
      box_high = MathMax(box_high, rates[i].high);
      box_low = MathMin(box_low, rates[i].low);
      count++;
   }
   return (count >= 6 && box_high > box_low);
}

bool SNR_XauS1BlockedHourValue(const datetime server_time, const string raw_value)
{
   string value = SNR_CleanTesterString(raw_value);
   if(value == "")
      return false;

   MqlDateTime dt;
   TimeToStruct(server_time, dt);

   string parts[];
   int count = StringSplit(value, ',', parts);
   for(int i = 0; i < count; i++)
   {
      string item = SNR_Trim(parts[i]);
      if(item == "")
         continue;
      if((int)StringToInteger(item) == dt.hour)
         return true;
   }
   return false;
}

bool SNR_XauS1BlockedHour(const datetime server_time)
{
   return SNR_XauS1BlockedHourValue(server_time, g_xauSweepReclaimBlockedHours);
}

bool SNR_XauS1BlockedWeekdayValue(const datetime server_time, const string raw_value)
{
   string value = SNR_CleanTesterString(raw_value);
   if(value == "")
      return false;

   MqlDateTime dt;
   TimeToStruct(server_time, dt);

   string parts[];
   int count = StringSplit(value, ',', parts);
   for(int i = 0; i < count; i++)
   {
      string item = SNR_Trim(parts[i]);
      if(item == "")
         continue;
      if(SNR_WeekdayNumberFromName(item) == dt.day_of_week)
         return true;
   }
   return false;
}

bool SNR_XauS1BlockedWeekday(const datetime server_time)
{
   return SNR_XauS1BlockedWeekdayValue(server_time, g_xauSweepReclaimBlockedWeekdays);
}

bool SNR_XauS1DirectionalTimeBlocked(const datetime server_time, const int direction)
{
   if(direction == SNR_DIR_LONG)
   {
      return (SNR_XauS1BlockedHourValue(server_time, g_xauSweepReclaimBlockedLongHours) ||
              SNR_XauS1BlockedWeekdayValue(server_time, g_xauSweepReclaimBlockedLongWeekdays));
   }
   if(direction == SNR_DIR_SHORT)
   {
      return (SNR_XauS1BlockedHourValue(server_time, g_xauSweepReclaimBlockedShortHours) ||
              SNR_XauS1BlockedWeekdayValue(server_time, g_xauSweepReclaimBlockedShortWeekdays));
   }
   return false;
}

double SNR_XauS1M15TrueRangeAt(const MqlRates &rates[], const int index)
{
   double direct_range = rates[index].high - rates[index].low;
   double previous_close = rates[index + 1].close;
   double high_gap = MathAbs(rates[index].high - previous_close);
   double low_gap = MathAbs(rates[index].low - previous_close);
   return MathMax(direct_range, MathMax(high_gap, low_gap));
}

double SNR_XauS1M15AtrAt(const MqlRates &rates[], const int offset, const int period)
{
   if(period <= 0)
      return 0.0;

   double sum = 0.0;
   for(int i = offset; i < offset + period; i++)
      sum += SNR_XauS1M15TrueRangeAt(rates, i);
   return sum / period;
}

bool SNR_XauS1M15AtrImpulsePass(string &reason)
{
   reason = "";
   if(!g_useXauS1M15AtrImpulseFilter)
      return true;

   if(g_xauS1M15AtrPeriod <= 0 ||
      g_xauS1M15AtrEmaPeriod <= 0 ||
      g_xauS1M15AtrMultiplier <= 0.0)
   {
      reason = "XAU_S1_M15_ATR_PARAM";
      return false;
   }

   const int atr_period = g_xauS1M15AtrPeriod;
   const int ema_period = g_xauS1M15AtrEmaPeriod;
   const int bars_needed = atr_period + ema_period + 2;

   MqlRates m15_rates[];
   ArraySetAsSeries(m15_rates, true);
   int copied = CopyRates(_Symbol, PERIOD_M15, 1, bars_needed, m15_rates);
   if(copied < bars_needed)
   {
      reason = "XAU_S1_M15_ATR_DATA";
      return false;
   }

   double ema_atr = SNR_XauS1M15AtrAt(m15_rates, ema_period - 1, atr_period);
   if(ema_atr <= 0.0)
   {
      reason = "XAU_S1_M15_ATR_DATA";
      return false;
   }

   const double alpha = 2.0 / ((double)ema_period + 1.0);
   for(int offset = ema_period - 2; offset >= 0; offset--)
   {
      double atr_value = SNR_XauS1M15AtrAt(m15_rates, offset, atr_period);
      if(atr_value <= 0.0)
      {
         reason = "XAU_S1_M15_ATR_DATA";
         return false;
      }
      ema_atr = alpha * atr_value + (1.0 - alpha) * ema_atr;
   }

   double current_atr = SNR_XauS1M15AtrAt(m15_rates, 0, atr_period);
   if(current_atr <= 0.0 || ema_atr <= 0.0)
   {
      reason = "XAU_S1_M15_ATR_DATA";
      return false;
   }

   if(current_atr < g_xauS1M15AtrMultiplier * ema_atr)
   {
      reason = "XAU_S1_M15_ATR_IMPULSE_WEAK";
      return false;
   }

   return true;
}

bool SNR_XauS1M5DragonAnchorCompressionPass(const SnrContext &ctx, string &reason)
{
   reason = "";
   if(!g_useXauS1M5DragonAnchorCompressionFilter)
      return true;

   if(g_xauS1M5DragonAnchorMaxCompressionAtr <= 0.0)
   {
      reason = "XAU_S1_M5_DRAGON_COMPRESSION_PARAM";
      return false;
   }

   if(ctx.atr <= 0.0 || ctx.dragon_mid <= 0.0 || ctx.trend <= 0.0)
   {
      reason = "XAU_S1_M5_DRAGON_COMPRESSION_DATA";
      return false;
   }

   double compression_atr = MathAbs(ctx.dragon_mid - ctx.trend) / ctx.atr;
   if(compression_atr > g_xauS1M5DragonAnchorMaxCompressionAtr)
   {
      reason = "XAU_S1_M5_DRAGON_ANCHOR_EXTENDED";
      return false;
   }

   return true;
}

bool SNR_FindXauSweepReclaimScanner(const SnrContext &ctx,
                                    const int atr_handle,
                                    SnrSignal &signal)
{
   SNR_ResetSignal(signal, SNR_MODE_XAU_SWEEP_RECLAIM_SCAN, SNR_DIR_NONE);
   if(!g_useXauSweepReclaimScanner && !g_useXauSweepReclaimExecution)
   {
      signal.reason = "XAU_S1_DISABLED";
      return false;
   }
   if(!g_useRegimeRouter && !g_useXauSweepReclaimExecution)
   {
      signal.reason = "XAU_S1_DISABLED";
      return false;
   }
   if(!SNR_IsScalpSymbol("XAUUSD") || _Period != PERIOD_M5)
   {
      signal.reason = "XAU_S1_SYMBOL_TF";
      return false;
   }

   MqlRates rates[];
   double atr[];
   const int bars_needed = 160;
   if(!SNR_CopyClosedRates(bars_needed, rates) ||
      !SNR_CopyClosedBuffer(atr_handle, bars_needed, atr))
   {
      signal.reason = "DATA_UNAVAILABLE";
      return false;
   }
   if(atr[0] <= 0.0)
   {
      signal.reason = "ATR_INVALID";
      return false;
   }

   double box_high = 0.0;
   double box_low = 0.0;
   int now_min = SNR_ServerMinutesOfDay(ctx.decision_time_server);
   bool has_box = false;
   if(now_min >= SNR_MinutesOfDay(12, 0))
      has_box = SNR_SessionBox(rates, bars_needed, SNR_MinutesOfDay(8, 0), SNR_MinutesOfDay(12, 0), ctx.decision_time_server, box_high, box_low);
   if(!has_box && now_min >= SNR_MinutesOfDay(8, 0))
      has_box = SNR_SessionBox(rates, bars_needed, SNR_MinutesOfDay(0, 0), SNR_MinutesOfDay(8, 0), ctx.decision_time_server, box_high, box_low);
   if(!has_box)
   {
      signal.reason = "XAU_S1_NO_LOCKED_BOX";
      return false;
   }

   double box_mid = (box_high + box_low) * 0.5;
   double body_high = MathMax(rates[0].open, rates[0].close);
   double body_low = MathMin(rates[0].open, rates[0].close);
   double body = MathAbs(rates[0].close - rates[0].open);
   double lower_wick = body_low - rates[0].low;
   double upper_wick = rates[0].high - body_high;
   bool pvsra_ok = (ctx.pvsra_grade >= g_goldS1MinPvsraGrade || ctx.pvsra_event != "NONE");

   if(rates[0].low < box_low && rates[0].close > box_low)
      signal.direction = SNR_DIR_LONG;
   else if(rates[0].high > box_high && rates[0].close < box_high)
      signal.direction = SNR_DIR_SHORT;
   else
   {
      signal.reason = "XAU_S1_NO_SWEEP_RECLAIM";
      return false;
   }

   if(g_useXauSweepReclaimExecution)
   {
      if(SNR_XauS1BlockedHour(ctx.decision_time_server) ||
         SNR_XauS1BlockedWeekday(ctx.decision_time_server))
      {
         signal.reason = "XAU_S1_TIME_BLOCK";
         return false;
      }
      if((g_xauSweepReclaimDirectionMode == 1 && signal.direction != SNR_DIR_LONG) ||
         (g_xauSweepReclaimDirectionMode == 2 && signal.direction != SNR_DIR_SHORT))
      {
         signal.reason = "XAU_S1_DIRECTION_BLOCK";
         return false;
      }
      if(SNR_XauS1DirectionalTimeBlocked(ctx.decision_time_server, signal.direction))
      {
         signal.reason = "XAU_S1_DIRECTION_TIME_BLOCK";
         return false;
      }
      if(!pvsra_ok)
      {
         signal.reason = "XAU_S1_PVSRA_WEAK";
         return false;
      }
      if(signal.direction > 0)
      {
         if(rates[0].close >= box_mid ||
            lower_wick < MathMax(0.08 * atr[0], 0.60 * body))
         {
            signal.reason = "XAU_S1_REJECTION_WEAK";
            return false;
         }
         signal.stop_price = MathMin(rates[0].low, box_low) - 0.25 * atr[0];
          double risk = rates[0].close - signal.stop_price;
          double reward = box_mid - rates[0].close;
          double rr = (risk > 0.0 ? reward / risk : 0.0);
          double min_rr = MathMax(0.0, g_xauSweepReclaimMinTargetRR);
          double max_rr = g_xauSweepReclaimMaxTargetRR;
          if(risk <= 0.0 || rr < min_rr)
          {
             signal.reason = "XAU_S1_RR_WEAK";
             return false;
          }
          if(max_rr > 0.0 && rr > max_rr)
          {
             signal.reason = "XAU_S1_RR_TOO_HIGH";
             return false;
          }
          signal.target_rr = rr;
      }
      else
      {
         if(rates[0].close <= box_mid ||
            upper_wick < MathMax(0.08 * atr[0], 0.60 * body))
         {
            signal.reason = "XAU_S1_REJECTION_WEAK";
            return false;
         }
         signal.stop_price = MathMax(rates[0].high, box_high) + 0.25 * atr[0];
          double risk = signal.stop_price - rates[0].close;
          double reward = rates[0].close - box_mid;
          double rr = (risk > 0.0 ? reward / risk : 0.0);
          double min_rr = MathMax(0.0, g_xauSweepReclaimMinTargetRR);
          double max_rr = g_xauSweepReclaimMaxTargetRR;
          if(risk <= 0.0 || rr < min_rr)
          {
             signal.reason = "XAU_S1_RR_WEAK";
             return false;
          }
          if(max_rr > 0.0 && rr > max_rr)
          {
             signal.reason = "XAU_S1_RR_TOO_HIGH";
             return false;
          }
          signal.target_rr = rr;
      }

      signal.mode = SNR_MODE_XAU_SWEEP_RECLAIM;
      signal.setup_state = "TRIGGER";
      signal.archetype = "XAU_S1_SWEEP_RECLAIM";
      signal.quality_score = ctx.context_score +
                             0.45 * ctx.pvsra_grade +
                             MathMin(0.75, MathMax(lower_wick, upper_wick) / MathMax(_Point, body + _Point));
   }
   else
   {
      signal.target_rr = 0.0;
      signal.setup_state = "OBSERVE";
      signal.archetype = "XAU_S1_SWEEP_RECLAIM_SCAN";
      signal.quality_score = ctx.context_score + 0.30 * ctx.pvsra_grade;
   }

   signal.valid = true;
   signal.wave_id = SNR_BuildWaveId(rates[0].time, "XAU_S1_SCAN", signal.direction);
   if(signal.mode == SNR_MODE_XAU_SWEEP_RECLAIM)
      signal.wave_id = SNR_BuildWaveId(rates[0].time, "XAU_S1", signal.direction);

   if(signal.mode == SNR_MODE_XAU_SWEEP_RECLAIM)
   {
      string m15_atr_reason = "";
      if(!SNR_XauS1M15AtrImpulsePass(m15_atr_reason))
      {
         signal.valid = false;
         signal.reason = m15_atr_reason;
         return false;
      }
   }

   if(signal.mode == SNR_MODE_XAU_SWEEP_RECLAIM)
   {
      string dragon_compression_reason = "";
      if(!SNR_XauS1M5DragonAnchorCompressionPass(ctx, dragon_compression_reason))
      {
         signal.valid = false;
         signal.reason = dragon_compression_reason;
         return false;
      }
   }

   // IMPULSE S1 False Positive Veto (default OFF)
   // Prereg: SONICR-P2-IMPULSE-S1-FP-EA-PATCH-20260507-C
   if(g_enableImpulseS1FPVeto && signal.mode == SNR_MODE_XAU_SWEEP_RECLAIM)
   {
      // Only check IMPULSE phases (STEEP/ANGLED + TREND regime)
      if(ctx.regime_state == SNR_REGIME_TREND || ctx.regime_state == SNR_REGIME_TRENDING_STRONG)
      {
         string angle = ctx.dragon_angle_class;
         if(angle == "STEEP" || angle == "ANGLED")
         {
            // Check STEEP + clean
            bool is_steep = (MathAbs(ctx.dragon_slope_atr) > 0.5);
            bool is_clean = (ctx.dragon_cross_count <= 5);
            
            if(is_steep && is_clean)
            {
               // Check HTF hard conflict
               bool htf_hard_conflict = false;
               if(signal.direction == SNR_DIR_LONG && ctx.h1_bias < 0 && ctx.h4_bias < 0)
                  htf_hard_conflict = true;
               if(signal.direction == SNR_DIR_SHORT && ctx.h1_bias > 0 && ctx.h4_bias > 0)
                  htf_hard_conflict = true;
               
               if(htf_hard_conflict)
               {
                  // Determine IMPULSE direction from dragon slope
                  int impulse_dir = (ctx.dragon_slope_atr > 0.0) ? SNR_DIR_LONG : SNR_DIR_SHORT;
                  
                  // Check PVSRA not OPPOSITE to impulse direction
                  bool pvsra_not_opposite = false;
                  if(impulse_dir == SNR_DIR_LONG && signal.direction == SNR_DIR_SHORT && ctx.pvsra_bias != "BEARISH")
                     pvsra_not_opposite = true;
                  if(impulse_dir == SNR_DIR_SHORT && signal.direction == SNR_DIR_LONG && ctx.pvsra_bias != "BULLISH")
                     pvsra_not_opposite = true;
                  
                  if(pvsra_not_opposite)
                  {
                     // Check weak CLIMAX (grade < 3 OR volume < 150 percentile)
                     bool weak_climax = (ctx.pvsra_grade < 3 || ctx.tick_volume_percentile < 150.0);
                     
                     if(weak_climax)
                     {
                        // All conditions met = false positive, veto this signal
                        signal.valid = false;
                        signal.reason = "XAU_S1_IMPULSE_FP_VETO";
                        return false;
                     }
                  }
               }
            }
         }
      }
   }
   
   return true;
}

bool SNR_XauLongBiasCoreGatePass(const SnrContext &ctx,
                                 const SnrMode mode,
                                 const int direction,
                                 string &reason)
{
   reason = "";
   if(!g_useXauLongBiasCoreGate)
      return true;
   if(StringFind(_Symbol, "XAUUSD") != 0 || _Period != PERIOD_M5)
      return true;
   if(mode != SNR_MODE_CLASSIC && mode != SNR_MODE_XAU_SWEEP_RECLAIM)
      return true;

   if(direction != SNR_DIR_LONG)
   {
      reason = "XAU_LONG_BIAS_DIRECTION";
      return false;
   }
   if(ctx.pvsra_bias != "BULLISH")
   {
      reason = "XAU_LONG_BIAS_PVSRA";
      return false;
   }
   if(ctx.atr <= 0.0)
   {
      reason = "XAU_LONG_BIAS_ATR";
      return false;
   }

   MqlRates rates[];
   ArraySetAsSeries(rates, true);
   const int bars_needed = 288;
   int copied = CopyRates(_Symbol, PERIOD_CURRENT, 1, bars_needed, rates);
   if(copied < bars_needed)
   {
      reason = "XAU_LONG_BIAS_DATA";
      return false;
   }

   SnrGoldWindowMetrics m1d;
   SNR_GoldBuildWindowMetrics(rates, copied, bars_needed, ctx.atr, m1d);
   if(!m1d.ok)
   {
      reason = "XAU_LONG_BIAS_DATA";
      return false;
   }

   if(mode == SNR_MODE_CLASSIC)
   {
      if(m1d.trend_bucket != "UP" && m1d.trend_bucket != "STRONG_UP")
      {
         reason = "XAU_LONG_BIAS_CLASSIC_1D";
         return false;
      }
      return true;
   }

   if(m1d.trend_bucket == "STRONG_DOWN")
   {
      reason = "XAU_LONG_BIAS_S1_STRONG_DOWN";
      return false;
   }
   return true;
}

void SNR_ApplyXauLongBiasCoreGate(const SnrContext &ctx,
                                  SnrSignal &signal)
{
   if(!signal.valid)
      return;
   string reason = "";
   if(SNR_XauLongBiasCoreGatePass(ctx, signal.mode, signal.direction, reason))
      return;
   signal.valid = false;
   signal.reason = reason;
   signal.invalidate_reason = reason;
   signal.setup_state = "INVALIDATE";
}

bool SNR_IsFxRouteSymbol()
{
   return (_Symbol == "EURUSD" || _Symbol == "GBPUSD");
}

bool SNR_FxM15HtfClassicRoutePass(const SnrContext &ctx,
                                  const int direction,
                                  string &reason)
{
   reason = "";
   if(!g_useFxM15HtfClassicRoute)
      return true;
   if(!SNR_IsFxRouteSymbol())
      return true;
   if(_Period != PERIOD_M15)
   {
      reason = "FX_M15_ROUTE_TF";
      return false;
   }
   if(direction != SNR_DIR_LONG && direction != SNR_DIR_SHORT)
   {
      reason = "FX_M15_ROUTE_DIRECTION";
      return false;
   }

   if(g_fxM15RouteRequireH1H4Alignment && g_fxM15RouteHtfMode == 1)
   {
      if(ctx.h1_bias != direction)
      {
         reason = "FX_M15_ROUTE_H1";
         return false;
      }
      if(ctx.h4_bias == -direction)
      {
         reason = "FX_M15_ROUTE_H4_OPPOSITE";
         return false;
      }
   }
   else if(g_fxM15RouteRequireH1H4Alignment &&
           (ctx.h1_bias != direction || ctx.h4_bias != direction))
   {
       reason = "FX_M15_ROUTE_HTF";
       return false;
   }

   if(g_fxM15RouteRequireCleanWave &&
      ctx.source_classic_wave_state != "clean_classic" &&
      ctx.sonic_wave_quality != "clean")
   {
      reason = "FX_M15_ROUTE_WAVE";
      return false;
   }

   const bool dragon_ready = (ctx.source_classic_dragon_state == "dragon_expanding" ||
                              ctx.source_classic_dragon_state == "dragon_angled" ||
                              ctx.sonic_dragon_momentum == "expanding" ||
                              ctx.sonic_dragon_momentum == "angled");
   if(g_fxM15RouteRequireDragonExpansion && !dragon_ready)
   {
      reason = "FX_M15_ROUTE_DRAGON";
      return false;
   }

   if(g_fxM15RouteBlockLateChase &&
      (ctx.source_classic_chase_risk == "late_chase" ||
       ctx.sonic_entry_timing_risk == "late_chase"))
   {
      reason = "FX_M15_ROUTE_LATE_CHASE";
      return false;
   }

   const double min_runway_pips = MathMax(0.0, g_fxM15RouteMinSrRunwayPips);
   if(min_runway_pips > 0.0 && ctx.source_sr_runway_pips < min_runway_pips)
   {
      reason = "FX_M15_ROUTE_RUNWAY";
      return false;
   }

   if(direction == SNR_DIR_LONG && ctx.pvsra_bias == "BEARISH")
   {
      reason = "FX_M15_ROUTE_PVSRA_COUNTER";
      return false;
   }
   if(direction == SNR_DIR_SHORT && ctx.pvsra_bias == "BULLISH")
   {
      reason = "FX_M15_ROUTE_PVSRA_COUNTER";
      return false;
   }

   if(ctx.sonic_story_state == "invalidate")
   {
      reason = "FX_M15_ROUTE_STORY_INVALIDATE";
      return false;
   }

   return true;
}

void SNR_ApplyFxM15HtfClassicRoute(const SnrContext &ctx,
                                   SnrSignal &signal)
{
   if(!signal.valid || !g_useFxM15HtfClassicRoute)
      return;
   if(!SNR_IsFxRouteSymbol())
      return;
   if(signal.mode != SNR_MODE_CLASSIC)
      return;

   string reason = "";
   if(SNR_FxM15HtfClassicRoutePass(ctx, signal.direction, reason))
   {
      signal.archetype = "FxM15HtfClassic";
      signal.quality_score += 0.25;
      return;
   }

   signal.valid = false;
   signal.reason = reason;
   signal.invalidate_reason = reason;
   signal.setup_state = "INVALIDATE";
}

bool SNR_FindEurTrendClassicSignal(const SnrContext &ctx,
                                   const int dragon_high_handle,
                                   const int dragon_mid_handle,
                                   const int dragon_low_handle,
                                   const int atr_handle,
                                   SnrSignal &signal)
{
   SNR_ResetSignal(signal, SNR_MODE_EUR_TREND_CLASSIC, ctx.regime_bias);
   if(!g_useRegimeRouter || !g_useEurTrendClassic)
   {
      signal.reason = "EUR_T1_DISABLED";
      return false;
   }
   if(!SNR_IsScalpSymbol("EURUSD") || _Period != PERIOD_M5)
   {
      signal.reason = "EUR_T1_SYMBOL_TF";
      return false;
   }
   if((ctx.regime_state != SNR_REGIME_TREND && ctx.regime_state != SNR_REGIME_TRENDING_STRONG) || ctx.regime_bias == SNR_DIR_NONE)
   {
      signal.reason = "EUR_T1_NOT_TREND";
      return false;
   }
   if(ctx.session_bucket != "LONDON" && !(ctx.session_bucket == "NEWYORK" && ctx.hour_server <= 16))
   {
      signal.reason = "EUR_T1_SESSION";
      return false;
   }

   SnrSignal classic;
   if(!SNR_FindClassicSignal(ctx, ctx.regime_bias, dragon_high_handle, dragon_mid_handle, dragon_low_handle, atr_handle, classic))
   {
      signal.reason = classic.reason;
      return false;
   }

   signal = classic;
   signal.mode = SNR_MODE_EUR_TREND_CLASSIC;
   signal.archetype = "EUR_T1_CLASSIC";
   datetime closed_bar = iTime(_Symbol, PERIOD_CURRENT, 1);
   if(closed_bar <= 0)
      closed_bar = ctx.decision_time_server;
   signal.wave_id = SNR_BuildWaveId(closed_bar, "EUR_T1", signal.direction);
   return true;
}

bool SNR_FindEurAsianBoxRetestSignal(const SnrContext &ctx,
                                     const int atr_handle,
                                     SnrSignal &signal)
{
   SNR_ResetSignal(signal, SNR_MODE_EUR_ASIAN_BOX_RETEST, SNR_DIR_NONE);
   if(!g_useRegimeRouter || !g_useEurAsianBoxRetest)
   {
      signal.reason = "EUR_B1_DISABLED";
      return false;
   }
   if(!SNR_IsScalpSymbol("EURUSD") || _Period != PERIOD_M5)
   {
      signal.reason = "EUR_B1_SYMBOL_TF";
      return false;
   }
   if(ctx.session_bucket != "LONDON")
   {
      signal.reason = "EUR_B1_SESSION";
      return false;
   }

   MqlRates rates[];
   double atr[];
   const int bars_needed = 180;
   if(!SNR_CopyClosedRates(bars_needed, rates) ||
      !SNR_CopyClosedBuffer(atr_handle, bars_needed, atr))
   {
      signal.reason = "DATA_UNAVAILABLE";
      return false;
   }
   if(atr[0] <= 0.0)
   {
      signal.reason = "ATR_INVALID";
      return false;
   }

   double box_high = 0.0;
   double box_low = 0.0;
   if(!SNR_SessionBox(rates, bars_needed, SNR_MinutesOfDay(0, 0), SNR_MinutesOfDay(8, 0), ctx.decision_time_server, box_high, box_low))
   {
      signal.reason = "EUR_B1_NO_ASIAN_BOX";
      return false;
   }

   double box_width_atr = (box_high - box_low) / atr[0];
   if(box_width_atr < 0.50 || box_width_atr > 1.80)
   {
      signal.reason = "EUR_B1_BOX_WIDTH";
      return false;
   }

   bool broke_up = false;
   bool broke_down = false;
   int now_min = SNR_ServerMinutesOfDay(ctx.decision_time_server);
   MqlDateTime ref_dt;
   TimeToStruct(ctx.decision_time_server, ref_dt);
   for(int i = 1; i < bars_needed; i++)
   {
      MqlDateTime dt;
      TimeToStruct(rates[i].time, dt);
      if(dt.year != ref_dt.year || dt.mon != ref_dt.mon || dt.day != ref_dt.day)
         continue;
      int minutes = SNR_MinutesOfDay(dt.hour, dt.min);
      if(minutes < SNR_MinutesOfDay(8, 0) || minutes >= now_min)
         continue;
      if(rates[i].close > box_high)
         broke_up = true;
      if(rates[i].close < box_low)
         broke_down = true;
   }

   bool long_retest = (broke_up &&
                       rates[0].low <= box_high + 0.15 * atr[0] &&
                       rates[0].close > box_high &&
                       rates[0].close > rates[0].open);
   bool short_retest = (broke_down &&
                        rates[0].high >= box_low - 0.15 * atr[0] &&
                        rates[0].close < box_low &&
                        rates[0].close < rates[0].open);

   if(long_retest)
   {
      signal.direction = SNR_DIR_LONG;
      signal.stop_price = MathMin(rates[0].low, box_high - 0.15 * atr[0]) - 0.25 * atr[0];
   }
   else if(short_retest)
   {
      signal.direction = SNR_DIR_SHORT;
      signal.stop_price = MathMax(rates[0].high, box_low + 0.15 * atr[0]) + 0.25 * atr[0];
   }
   else
   {
      signal.reason = "EUR_B1_NO_RETEST";
      return false;
   }

   signal.valid = true;
   signal.target_rr = 1.00;
   signal.wave_id = SNR_BuildWaveId(rates[0].time, "EUR_B1", signal.direction);
   signal.archetype = "EUR_B1_ASIAN_BOX_RETEST";
   signal.setup_state = "TRIGGER";
   signal.pullback_depth_atr = box_width_atr;
   signal.quality_score = ctx.context_score +
                          MathMin(0.75, SNR_BarBodyRatio(rates[0])) +
                          0.20 * ctx.pvsra_grade;
   return true;
}

bool SNR_ChooseSignal(const SnrSignal &candidate, SnrSignal &best)
{
   if(!candidate.valid)
      return false;
   if(!best.valid || candidate.quality_score > best.quality_score)
   {
      best = candidate;
      return true;
   }
   return false;
}

void SNR_SetDecisionFromSignal(const SnrContext &ctx,
                               const SnrSignal &best,
                               SnrDecision &decision)
{
   decision.should_trade = true;
   decision.mode = best.mode;
   decision.direction = best.direction;
   decision.block_reason = "";
   decision.wave_id = best.wave_id;
   decision.archetype = best.archetype;
   decision.setup_state = best.setup_state;
   decision.invalidate_reason = best.invalidate_reason;
   decision.context_score = ctx.context_score;
   decision.pvsra_grade = SNR_DirectionalPvsraGrade(ctx, best.direction);
   decision.level_zone = ctx.level_zone;
   decision.stop_price = best.stop_price;
   decision.target_rr = best.target_rr;
   decision.quality_score = best.quality_score;
   decision.pullback_depth_atr = best.pullback_depth_atr;
   SNR_ResetFxChaseTrapV2ADiagnostic(decision);
}

void SNR_BuildRegimeDecision(const SnrContext &ctx,
                             const SnrNarrative &narrative,
                             const int dragon_high_handle,
                             const int dragon_mid_handle,
                             const int dragon_low_handle,
                             const int atr_handle,
                             SnrClassicArm &xau_t1_arm,
                             SnrDecision &decision)
{
   if(narrative.active || narrative.layers_opened > 0)
   {
      decision.block_reason = "ROUTER_POSITION_ACTIVE";
      decision.setup_state = "INVALIDATE";
      decision.invalidate_reason = "ROUTER_POSITION_ACTIVE";
      return;
   }

   if(ctx.regime_state == SNR_REGIME_UNKNOWN)
   {
      if(ctx.regime_reason == "NON_M5" || ctx.regime_reason == "REGIME_DATA_UNAVAILABLE")
      {
         decision.block_reason = ctx.regime_reason;
         decision.invalidate_reason = decision.block_reason;
         return;
      }
   }

   SnrSignal best;
   SNR_ResetSignal(best, SNR_MODE_BLOCKED, SNR_DIR_NONE);
   SnrSignal scanner;
   SNR_ResetSignal(scanner, SNR_MODE_XAU_SWEEP_RECLAIM_SCAN, SNR_DIR_NONE);
   string first_reason = "";

   if(SNR_IsScalpSymbol("XAUUSD"))
   {
      SnrSignal xau_t1, xau_t1_arm_candidate, xau_r1, xau_s1;
      SNR_ResetSignal(xau_t1_arm_candidate, SNR_MODE_XAU_ACTIVE_CLASSIC, SNR_DIR_NONE);
      SNR_BuildXauActiveClassicArmedSignal(ctx, dragon_mid_handle, atr_handle, xau_t1_arm, xau_t1);
      if(!xau_t1.valid && !xau_t1_arm.active)
      {
         SNR_FindXauActiveClassicArmCandidate(ctx, dragon_high_handle, dragon_mid_handle, dragon_low_handle, atr_handle, xau_t1_arm_candidate);
         if(xau_t1_arm_candidate.valid)
            SNR_ArmXauT1Setup(ctx, xau_t1_arm_candidate, xau_t1_arm);
      }
      SNR_FindXauRangeAbsorptionSignal(ctx, dragon_mid_handle, atr_handle, xau_r1);
      SNR_FindXauSweepReclaimScanner(ctx, atr_handle, xau_s1);

      SNR_ChooseSignal(xau_t1, best);
      SNR_ChooseSignal(xau_r1, best);
      if(xau_s1.valid && xau_s1.mode == SNR_MODE_XAU_SWEEP_RECLAIM)
         SNR_ChooseSignal(xau_s1, best);
      else if(xau_s1.valid && xau_s1.mode == SNR_MODE_XAU_SWEEP_RECLAIM_SCAN)
         scanner = xau_s1;
      if(xau_t1_arm_candidate.valid && !best.valid)
      {
         decision.should_trade = false;
         decision.mode = xau_t1_arm_candidate.mode;
         decision.direction = xau_t1_arm_candidate.direction;
         decision.block_reason = "XAU_T1_ARMED_WAIT";
         decision.wave_id = xau_t1_arm_candidate.wave_id;
         decision.archetype = xau_t1_arm_candidate.archetype;
         decision.setup_state = "ARM";
         decision.invalidate_reason = "";
         decision.context_score = ctx.context_score;
         decision.pvsra_grade = SNR_DirectionalPvsraGrade(ctx, xau_t1_arm_candidate.direction);
         decision.level_zone = ctx.level_zone;
         decision.stop_price = xau_t1_arm_candidate.stop_price;
         decision.target_rr = xau_t1_arm_candidate.target_rr;
         decision.quality_score = xau_t1_arm_candidate.quality_score;
         decision.pullback_depth_atr = xau_t1_arm_candidate.pullback_depth_atr;
         SNR_ResetFxChaseTrapV2ADiagnostic(decision);
         return;
      }
      first_reason = (xau_t1.reason != "" ? xau_t1.reason :
                      (xau_t1_arm_candidate.reason != "" ? xau_t1_arm_candidate.reason :
                      (xau_r1.reason != "" ? xau_r1.reason : xau_s1.reason)));
      decision.mode = (g_useXauActiveClassic ? SNR_MODE_XAU_ACTIVE_CLASSIC :
                       (g_useXauRangeAbsorption ? SNR_MODE_XAU_RANGE_ABSORPTION :
                       (g_useXauSweepReclaimExecution ? SNR_MODE_XAU_SWEEP_RECLAIM :
                       (g_useXauSweepReclaimScanner ? SNR_MODE_XAU_SWEEP_RECLAIM_SCAN : SNR_MODE_BLOCKED))));
   }
   else if(SNR_IsScalpSymbol("EURUSD") || SNR_IsScalpSymbol("GBPUSD"))
   {
      SnrSignal eur_t1, eur_b1;
      SNR_FindEurTrendClassicSignal(ctx, dragon_high_handle, dragon_mid_handle, dragon_low_handle, atr_handle, eur_t1);
      SNR_FindEurAsianBoxRetestSignal(ctx, atr_handle, eur_b1);

      SNR_ChooseSignal(eur_t1, best);
      SNR_ChooseSignal(eur_b1, best);
      first_reason = (eur_t1.reason != "" ? eur_t1.reason : eur_b1.reason);
      decision.mode = (g_useEurAsianBoxRetest ? SNR_MODE_EUR_ASIAN_BOX_RETEST :
                       (g_useEurTrendClassic ? SNR_MODE_EUR_TREND_CLASSIC : SNR_MODE_BLOCKED));
   }
   else
   {
      decision.block_reason = "ROUTER_SYMBOL_UNSUPPORTED";
      decision.invalidate_reason = "ROUTER_SYMBOL_UNSUPPORTED";
      return;
   }

   if(best.valid)
   {
      SNR_SetDecisionFromSignal(ctx, best, decision);
      return;
   }

   if(scanner.valid)
   {
      decision.should_trade = false;
      decision.mode = scanner.mode;
      decision.direction = scanner.direction;
      decision.block_reason = "SCANNER_ONLY";
      decision.wave_id = scanner.wave_id;
      decision.archetype = scanner.archetype;
      decision.setup_state = scanner.setup_state;
      decision.invalidate_reason = "";
      decision.context_score = ctx.context_score;
      decision.pvsra_grade = ctx.pvsra_grade;
      decision.level_zone = ctx.level_zone;
      decision.stop_price = 0.0;
      decision.target_rr = 0.0;
      decision.quality_score = scanner.quality_score;
      decision.pullback_depth_atr = 0.0;
      SNR_ResetFxChaseTrapV2ADiagnostic(decision);
      return;
   }

   decision.block_reason = (first_reason != "" ? first_reason : "ROUTER_NO_LANE_SIGNAL");
   decision.invalidate_reason = decision.block_reason;
}

void SNR_BuildDecision(const SnrContext &ctx,
                       const SnrNarrative &narrative,
                       const int dragon_high_handle,
                       const int dragon_mid_handle,
                       const int dragon_low_handle,
                       const int trend_handle,
                       const int atr_handle,
                       SnrClassicArm &xau_t1_arm,
                       SnrDecision &decision)
{
   decision.should_trade = false;
   decision.mode = SNR_MODE_BLOCKED;
   decision.direction = SNR_DIR_NONE;
   decision.block_reason = ctx.block_reason;
   decision.wave_id = "";
   decision.archetype = "";
   decision.setup_state = "OBSERVE";
   decision.invalidate_reason = "";
   decision.context_score = ctx.context_score;
   decision.pvsra_grade = ctx.pvsra_grade;
   decision.level_zone = ctx.level_zone;
   decision.stop_price = 0.0;
   decision.target_rr = 0.0;
   decision.quality_score = -9999.0;
   decision.pullback_depth_atr = 0.0;
   SNR_ResetFxChaseTrapV2ADiagnostic(decision);

   if(ctx.force_flat_now)
   {
      if(decision.block_reason == "")
         decision.block_reason = "FORCE_FLAT_WINDOW";
      decision.setup_state = "INVALIDATE";
      decision.invalidate_reason = decision.block_reason;
      return;
   }

   if(ctx.entry_blocked)
   {
      if(decision.block_reason == "")
         decision.block_reason = "ENTRY_BLOCKED";
      decision.setup_state = "INVALIDATE";
      decision.invalidate_reason = decision.block_reason;
      return;
   }

   if(g_useRegimeRouter)
   {
      SNR_BuildRegimeDecision(ctx,
                              narrative,
                              dragon_high_handle,
                              dragon_mid_handle,
                              dragon_low_handle,
                              atr_handle,
                              xau_t1_arm,
                              decision);
      bool legacy_fallback_ok = (g_regimeRouterLegacyFallback &&
                                 !decision.should_trade &&
                                 decision.block_reason != "ROUTER_POSITION_ACTIVE" &&
                                 decision.block_reason != "ROUTER_SYMBOL_UNSUPPORTED" &&
                                 decision.block_reason != "REGIME_DATA_UNAVAILABLE" &&
                                 decision.block_reason != "NON_M5");
      if(decision.should_trade || !legacy_fallback_ok)
         return;

      decision.should_trade = false;
      decision.mode = SNR_MODE_BLOCKED;
      decision.direction = SNR_DIR_NONE;
      decision.block_reason = "";
      decision.wave_id = "";
      decision.archetype = "";
      decision.setup_state = "OBSERVE";
      decision.invalidate_reason = "";
      decision.context_score = ctx.context_score;
      decision.pvsra_grade = ctx.pvsra_grade;
      decision.level_zone = ctx.level_zone;
      decision.stop_price = 0.0;
      decision.target_rr = 0.0;
      decision.quality_score = -9999.0;
      decision.pullback_depth_atr = 0.0;
      SNR_ResetFxChaseTrapV2ADiagnostic(decision);
   }

   SnrSignal best;
   SNR_ResetSignal(best, SNR_MODE_BLOCKED, SNR_DIR_NONE);

   if(!narrative.active || narrative.layers_opened <= 0)
   {
      SnrSignal long_sig, short_sig, long_rev, short_rev, long_pb, short_pb, eur_london_short, xau_s1;
      SNR_ResetSignal(long_sig, SNR_MODE_CLASSIC, SNR_DIR_LONG);
      SNR_ResetSignal(short_sig, SNR_MODE_CLASSIC, SNR_DIR_SHORT);
      SNR_ResetSignal(long_rev, SNR_MODE_CLASSIC, SNR_DIR_LONG);
      SNR_ResetSignal(short_rev, SNR_MODE_CLASSIC, SNR_DIR_SHORT);
      SNR_ResetSignal(long_pb, SNR_MODE_CLASSIC, SNR_DIR_LONG);
      SNR_ResetSignal(short_pb, SNR_MODE_CLASSIC, SNR_DIR_SHORT);
      SNR_ResetSignal(eur_london_short, SNR_MODE_CLASSIC, SNR_DIR_SHORT);
      SNR_ResetSignal(xau_s1, SNR_MODE_XAU_SWEEP_RECLAIM, SNR_DIR_NONE);
      if(g_useClassicTrend && !g_useArmedClassic)
      {
         SNR_FindClassicSignal(ctx, SNR_DIR_LONG, dragon_high_handle, dragon_mid_handle, dragon_low_handle, atr_handle, long_sig);
         SNR_FindClassicSignal(ctx, SNR_DIR_SHORT, dragon_high_handle, dragon_mid_handle, dragon_low_handle, atr_handle, short_sig);
         SNR_LogFxClassicNearMissTelemetry(ctx, long_sig, "classic_raw");
         SNR_LogFxClassicNearMissTelemetry(ctx, short_sig, "classic_raw");
      }
      if(g_useDragonPullbackEntry)
      {
         SNR_FindDragonPullbackEntrySignal(ctx, SNR_DIR_LONG, dragon_high_handle, dragon_mid_handle, dragon_low_handle, trend_handle, atr_handle, long_pb);
         SNR_FindDragonPullbackEntrySignal(ctx, SNR_DIR_SHORT, dragon_high_handle, dragon_mid_handle, dragon_low_handle, trend_handle, atr_handle, short_pb);
      }
      if(g_useClassicReversal)
      {
         SNR_FindClassicReversalSignal(ctx, SNR_DIR_LONG, dragon_high_handle, dragon_mid_handle, dragon_low_handle, atr_handle, long_rev);
         SNR_FindClassicReversalSignal(ctx, SNR_DIR_SHORT, dragon_high_handle, dragon_mid_handle, dragon_low_handle, atr_handle, short_rev);
      }
      if(g_useEurLondonShortCleanRoute)
         SNR_FindEurLondonShortCleanRouteSignal(ctx, dragon_high_handle, dragon_mid_handle, dragon_low_handle, trend_handle, atr_handle, eur_london_short);
      if(g_useXauSweepReclaimExecution)
         SNR_FindXauSweepReclaimScanner(ctx, atr_handle, xau_s1);

      SNR_ApplyXauLongBiasCoreGate(ctx, long_sig);
      SNR_ApplyXauLongBiasCoreGate(ctx, short_sig);
      SNR_ApplyXauLongBiasCoreGate(ctx, long_rev);
      SNR_ApplyXauLongBiasCoreGate(ctx, short_rev);
      SNR_ApplyXauLongBiasCoreGate(ctx, long_pb);
      SNR_ApplyXauLongBiasCoreGate(ctx, short_pb);
      SNR_ApplyXauLongBiasCoreGate(ctx, xau_s1);
      SNR_ApplyFxM15HtfClassicRoute(ctx, long_sig);
      SNR_ApplyFxM15HtfClassicRoute(ctx, short_sig);
      if(g_useFxM15HtfClassicRoute)
      {
         SNR_LogFxClassicNearMissTelemetry(ctx, long_sig, "fx_route_post");
         SNR_LogFxClassicNearMissTelemetry(ctx, short_sig, "fx_route_post");
      }

      bool chose = false;
      chose = SNR_ChooseSignal(xau_s1, best) || chose;
      chose = SNR_ChooseSignal(long_sig, best) || chose;
      chose = SNR_ChooseSignal(short_sig, best) || chose;
      chose = SNR_ChooseSignal(long_pb, best) || chose;
      chose = SNR_ChooseSignal(short_pb, best) || chose;
      if(!chose)
         chose = SNR_ChooseSignal(eur_london_short, best) || chose;
      chose = SNR_ChooseSignal(long_rev, best) || chose;
      chose = SNR_ChooseSignal(short_rev, best) || chose;
      if(!chose)
      {
         decision.block_reason = (long_sig.reason != "" ? long_sig.reason :
                                  (short_sig.reason != "" ? short_sig.reason :
                                  (long_pb.reason != "" ? long_pb.reason :
                                  (short_pb.reason != "" ? short_pb.reason :
                                  (eur_london_short.reason != "" ? eur_london_short.reason :
                                  (xau_s1.reason != "" ? xau_s1.reason :
                                  (long_rev.reason != "" ? long_rev.reason : short_rev.reason)))))));
         decision.invalidate_reason = decision.block_reason;
         return;
      }
   }
   else
   {
      if(narrative.layers_opened >= g_maxLayers)
      {
         decision.block_reason = "MAX_LAYERS";
         decision.setup_state = "INVALIDATE";
         decision.invalidate_reason = "MAX_LAYERS";
         return;
      }

      SnrSignal reentry_sig, continuation_sig, scout_sig;
      SNR_FindReentrySignal(ctx, narrative, dragon_high_handle, dragon_mid_handle, dragon_low_handle, trend_handle, atr_handle, reentry_sig);
      SNR_FindContinuationPullbackSignal(ctx, narrative, dragon_high_handle, dragon_mid_handle, dragon_low_handle, trend_handle, atr_handle, continuation_sig);
      SNR_FindScout2Signal(ctx, narrative, dragon_mid_handle, dragon_low_handle, dragon_high_handle, atr_handle, scout_sig);

      bool chose = false;
      chose = SNR_ChooseSignal(reentry_sig, best) || chose;
      chose = SNR_ChooseSignal(scout_sig, best) || chose;
      if(!chose)
         chose = SNR_ChooseSignal(continuation_sig, best) || chose;
      if(!chose)
      {
         decision.block_reason = (reentry_sig.reason != "" ? reentry_sig.reason : (scout_sig.reason != "" ? scout_sig.reason : continuation_sig.reason));
         decision.invalidate_reason = decision.block_reason;
         return;
      }
   }

   decision.should_trade = true;
   decision.mode = best.mode;
   decision.direction = best.direction;
   decision.block_reason = "";
   decision.wave_id = best.wave_id;
   decision.archetype = best.archetype;
   decision.setup_state = best.setup_state;
   decision.invalidate_reason = best.invalidate_reason;
   decision.context_score = ctx.context_score;
   decision.pvsra_grade = SNR_DirectionalPvsraGrade(ctx, best.direction);
   decision.level_zone = ctx.level_zone;
   decision.stop_price = best.stop_price;
   decision.target_rr = best.target_rr;
   decision.quality_score = best.quality_score;
   decision.pullback_depth_atr = best.pullback_depth_atr;
   SNR_ResetFxChaseTrapV2ADiagnostic(decision);
}

bool SNR_BuildContinuationFallbackDecision(const SnrContext &ctx,
                                           const SnrNarrative &narrative,
                                           const int dragon_high_handle,
                                           const int dragon_mid_handle,
                                           const int dragon_low_handle,
                                           const int trend_handle,
                                           const int atr_handle,
                                           SnrDecision &decision)
{
   decision.should_trade = false;
   decision.mode = SNR_MODE_BLOCKED;
   decision.direction = SNR_DIR_NONE;
   decision.block_reason = "";
   decision.wave_id = "";
   decision.archetype = "";
   decision.setup_state = "OBSERVE";
   decision.invalidate_reason = "";
   decision.context_score = ctx.context_score;
   decision.pvsra_grade = ctx.pvsra_grade;
   decision.level_zone = ctx.level_zone;
   decision.stop_price = 0.0;
   decision.target_rr = 0.0;
   decision.quality_score = -9999.0;
   decision.pullback_depth_atr = 0.0;
   SNR_ResetFxChaseTrapV2ADiagnostic(decision);

   SnrSignal continuation_sig;
   SNR_FindContinuationPullbackSignal(ctx,
                                      narrative,
                                      dragon_high_handle,
                                      dragon_mid_handle,
                                      dragon_low_handle,
                                      trend_handle,
                                      atr_handle,
                                      continuation_sig);
   if(!continuation_sig.valid)
   {
      decision.block_reason = continuation_sig.reason;
      decision.invalidate_reason = continuation_sig.reason;
      return false;
   }

   decision.should_trade = true;
   decision.mode = continuation_sig.mode;
   decision.direction = continuation_sig.direction;
   decision.block_reason = "";
   decision.wave_id = continuation_sig.wave_id;
   decision.archetype = continuation_sig.archetype;
   decision.setup_state = continuation_sig.setup_state;
   decision.invalidate_reason = continuation_sig.invalidate_reason;
   decision.context_score = ctx.context_score;
   decision.pvsra_grade = SNR_DirectionalPvsraGrade(ctx, continuation_sig.direction);
   decision.level_zone = ctx.level_zone;
   decision.stop_price = continuation_sig.stop_price;
   decision.target_rr = continuation_sig.target_rr;
   decision.quality_score = continuation_sig.quality_score;
   decision.pullback_depth_atr = continuation_sig.pullback_depth_atr;
   SNR_ResetFxChaseTrapV2ADiagnostic(decision);
   return true;
}

#endif
