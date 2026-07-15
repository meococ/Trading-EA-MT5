#ifndef SNR_GOLD_REGIME_MQH
#define SNR_GOLD_REGIME_MQH

struct SnrGoldWindowMetrics
{
   bool   ok;
   double delta_atr;
   string trend_bucket;
   double efficiency;
   string efficiency_bucket;
   double range_width_atr;
   string range_bucket;
};

void SNR_GoldResetMetrics(SnrGoldWindowMetrics &metrics)
{
   metrics.ok = false;
   metrics.delta_atr = 0.0;
   metrics.trend_bucket = "UNKNOWN";
   metrics.efficiency = 0.0;
   metrics.efficiency_bucket = "UNKNOWN";
   metrics.range_width_atr = 0.0;
   metrics.range_bucket = "UNKNOWN";
}

string SNR_GoldTrendBucket(const double delta_atr)
{
   if(delta_atr >= 5.0)
      return "STRONG_UP";
   if(delta_atr >= 2.0)
      return "UP";
   if(delta_atr <= -5.0)
      return "STRONG_DOWN";
   if(delta_atr <= -2.0)
      return "DOWN";
   return "FLAT";
}

string SNR_GoldEfficiencyBucket(const double efficiency)
{
   if(efficiency >= 0.42)
      return "EFFICIENT_TREND";
   if(efficiency <= 0.18)
      return "CHOPPY";
   return "MIXED";
}

string SNR_GoldRangeBucket(const double width_atr)
{
   if(width_atr <= 3.0)
      return "COMPRESSED";
   if(width_atr <= 6.0)
      return "BALANCED";
   return "EXPANDED";
}

string SNR_GoldVolRegime(const double percentile)
{
   if(percentile >= 80.0)
      return "HIGH_VOL";
   if(percentile <= 25.0)
      return "LOW_VOL";
   return "NORMAL_VOL";
}

string SNR_GoldMetricDouble(const bool ok, const double value, const int digits)
{
   return (ok ? DoubleToString(value, digits) : "");
}

double SNR_GoldMeanRange(const MqlRates &rates[], const int copied, const int bars)
{
   int count = MathMin(copied, bars);
   if(count <= 0)
      return 0.0;

   double total = 0.0;
   for(int i = 0; i < count; i++)
      total += MathMax(0.0, rates[i].high - rates[i].low);
   return total / (double)count;
}

double SNR_GoldRangePercentile(const MqlRates &rates[], const int copied, const double current_range, const int lookback)
{
   int count = MathMin(copied, lookback);
   if(count <= 0 || current_range <= 0.0)
      return 0.0;

   int less_or_equal = 0;
   for(int i = 0; i < count; i++)
   {
      double range = MathMax(0.0, rates[i].high - rates[i].low);
      if(range <= current_range)
         less_or_equal++;
   }
   return 100.0 * (double)less_or_equal / (double)count;
}

void SNR_GoldBuildWindowMetrics(const MqlRates &rates[],
                                const int copied,
                                const int bars,
                                const double atr,
                                SnrGoldWindowMetrics &metrics)
{
   SNR_GoldResetMetrics(metrics);
   if(copied < bars || bars < 2 || atr <= 0.0)
      return;

   double high_value = -DBL_MAX;
   double low_value = DBL_MAX;
   for(int i = 0; i < bars; i++)
   {
      high_value = MathMax(high_value, rates[i].high);
      low_value = MathMin(low_value, rates[i].low);
   }

   double path = 0.0;
   for(int i = 0; i < bars - 1; i++)
      path += MathAbs(rates[i].close - rates[i + 1].close);

   double delta = rates[0].close - rates[bars - 1].close;
   metrics.ok = true;
   metrics.delta_atr = delta / atr;
   metrics.trend_bucket = SNR_GoldTrendBucket(metrics.delta_atr);
   metrics.range_width_atr = (high_value - low_value) / atr;
   metrics.range_bucket = SNR_GoldRangeBucket(metrics.range_width_atr);
   metrics.efficiency = (path > 0.0 ? MathAbs(delta) / path : 0.0);
   metrics.efficiency_bucket = SNR_GoldEfficiencyBucket(metrics.efficiency);
}

double SNR_GoldPricePosition(const MqlRates &rates[], const int copied, const int bars)
{
   if(copied < bars || bars < 2)
      return 0.0;

   double high_value = -DBL_MAX;
   double low_value = DBL_MAX;
   for(int i = 0; i < bars; i++)
   {
      high_value = MathMax(high_value, rates[i].high);
      low_value = MathMin(low_value, rates[i].low);
   }

   double width = high_value - low_value;
   if(width <= 0.0)
      return 0.5;
   return SNR_Clamp((rates[0].close - low_value) / width, 0.0, 1.0);
}

double SNR_GoldDrawdownFromHighAtr(const MqlRates &rates[], const int copied, const int bars, const double atr)
{
   if(copied < bars || bars < 2 || atr <= 0.0)
      return 0.0;

   double high_value = -DBL_MAX;
   for(int i = 0; i < bars; i++)
      high_value = MathMax(high_value, rates[i].high);
   return MathMax(0.0, (high_value - rates[0].close) / atr);
}

double SNR_GoldReclaimFromLowAtr(const MqlRates &rates[], const int copied, const int bars, const double atr)
{
   if(copied < bars || bars < 2 || atr <= 0.0)
      return 0.0;

   double low_value = DBL_MAX;
   for(int i = 0; i < bars; i++)
      low_value = MathMin(low_value, rates[i].low);
   return MathMax(0.0, (rates[0].close - low_value) / atr);
}

string SNR_GoldFlowAlignment(const int direction, const SnrGoldWindowMetrics &metrics)
{
   if(!metrics.ok || direction == SNR_DIR_NONE)
      return "UNKNOWN";
   if(MathAbs(metrics.delta_atr) < 2.0)
      return "FLAT";
   bool aligned = (direction > 0 ? metrics.delta_atr > 0.0 : metrics.delta_atr < 0.0);
   return (aligned ? "ALIGNED" : "AGAINST");
}

string SNR_GoldFlowRegime(const SnrGoldWindowMetrics &m5d,
                          const SnrGoldWindowMetrics &m20d,
                          const double atr_percentile)
{
   if(!m5d.ok)
      return "DATA_UNAVAILABLE";

   bool up_flow = (m5d.trend_bucket == "UP" || m5d.trend_bucket == "STRONG_UP");
   bool down_flow = (m5d.trend_bucket == "DOWN" || m5d.trend_bucket == "STRONG_DOWN");
   bool long_up_flow = (m20d.ok && (m20d.trend_bucket == "UP" || m20d.trend_bucket == "STRONG_UP"));
   bool long_down_flow = (m20d.ok && (m20d.trend_bucket == "DOWN" || m20d.trend_bucket == "STRONG_DOWN"));

   string prefix = "RANGE";
   if(up_flow && long_up_flow)
      prefix = "UP_FLOW";
   else if(down_flow && long_down_flow)
      prefix = "DOWN_FLOW";
   else if(up_flow || down_flow)
      prefix = "MIXED_FLOW";

   string texture = m5d.efficiency_bucket;
   string vol = SNR_GoldVolRegime(atr_percentile);
   return prefix + "_" + texture + "_" + vol;
}

void SNR_LogGoldRegimeContext(const SnrContext &ctx,
                              const SnrDecision &decision,
                              const string outcome)
{
   if(!g_enableTelemetry || !g_enableGoldRegimeTelemetry)
      return;
   if(StringFind(_Symbol, "XAUUSD") != 0 || _Period != PERIOD_M5)
      return;
   if(decision.direction == SNR_DIR_NONE)
      return;
   if(decision.mode == SNR_MODE_BLOCKED && decision.wave_id == "" && outcome == "BLOCKED")
      return;

   MqlRates rates[];
   ArraySetAsSeries(rates, true);
   const int max_bars = 5760;
   int copied = CopyRates(_Symbol, PERIOD_CURRENT, 1, max_bars, rates);
   if(copied < 36 || ctx.atr <= 0.0)
      return;

   SnrGoldWindowMetrics m3h;
   SnrGoldWindowMetrics m8h;
   SnrGoldWindowMetrics m1d;
   SnrGoldWindowMetrics m5d;
   SnrGoldWindowMetrics m10d;
   SnrGoldWindowMetrics m20d;
   SNR_GoldBuildWindowMetrics(rates, copied, 36, ctx.atr, m3h);
   SNR_GoldBuildWindowMetrics(rates, copied, 96, ctx.atr, m8h);
   SNR_GoldBuildWindowMetrics(rates, copied, 288, ctx.atr, m1d);
   SNR_GoldBuildWindowMetrics(rates, copied, 1440, ctx.atr, m5d);
   SNR_GoldBuildWindowMetrics(rates, copied, 2880, ctx.atr, m10d);
   SNR_GoldBuildWindowMetrics(rates, copied, 5760, ctx.atr, m20d);

   double pip_size = SNR_CurrentPipSize();
   double atr20_price = SNR_GoldMeanRange(rates, copied, 20);
   double atr20_pips = (pip_size > 0.0 ? atr20_price / pip_size : 0.0);
   double atr20_percentile_5d = SNR_GoldRangePercentile(rates, copied, atr20_price, 1440);
   double price_position_20d = SNR_GoldPricePosition(rates, copied, 5760);
   double drawdown_20d = SNR_GoldDrawdownFromHighAtr(rates, copied, 5760, ctx.atr);
   double reclaim_20d = SNR_GoldReclaimFromLowAtr(rates, copied, 5760, ctx.atr);
   datetime closed_bar = iTime(_Symbol, PERIOD_CURRENT, 1);
   if(closed_bar <= 0)
      closed_bar = ctx.decision_time_server;

   string block_reason = (decision.block_reason != "" ? decision.block_reason : ctx.block_reason);
   int handle = SNR_OpenAppendCsv(g_snrGoldRegimeLogFile);
   if(handle == INVALID_HANDLE)
      return;

   string line = "";
   SNR_PvsraSrAppend(line, g_snrRunId);
   SNR_PvsraSrAppend(line, TimeToString(ctx.decision_time_server, TIME_DATE | TIME_MINUTES | TIME_SECONDS));
   SNR_PvsraSrAppend(line, TimeToString(ctx.decision_time_utc, TIME_DATE | TIME_MINUTES | TIME_SECONDS));
   SNR_PvsraSrAppend(line, _Symbol);
   SNR_PvsraSrAppend(line, EnumToString(_Period));
   SNR_PvsraSrAppend(line, TimeToString(closed_bar, TIME_DATE | TIME_MINUTES | TIME_SECONDS));
   SNR_PvsraSrAppend(line, SNR_CleanTesterString(g_variantTag));
   SNR_PvsraSrAppend(line, SNR_ModeName(decision.mode));
   SNR_PvsraSrAppend(line, SNR_DirectionName(decision.direction));
   SNR_PvsraSrAppend(line, SNR_ToUpper(outcome));
   SNR_PvsraSrAppend(line, SNR_DecisionReasonKey(decision));
   SNR_PvsraSrAppend(line, decision.wave_id);
   SNR_PvsraSrAppend(line, ctx.session_bucket);
   SNR_PvsraSrAppend(line, SNR_WeekdayTag(ctx.decision_time_server));
   SNR_PvsraSrAppend(line, IntegerToString(ctx.hour_server));
   SNR_PvsraSrAppend(line, SNR_GoldFlowRegime(m5d, m20d, atr20_percentile_5d));
   SNR_PvsraSrAppend(line, SNR_GoldFlowAlignment(decision.direction, m5d));
   SNR_PvsraSrAppend(line, SNR_GoldFlowAlignment(decision.direction, m20d));
   SNR_PvsraSrAppend(line, DoubleToString(atr20_pips, 2));
   SNR_PvsraSrAppend(line, DoubleToString(atr20_percentile_5d, 2));
   SNR_PvsraSrAppend(line, SNR_GoldVolRegime(atr20_percentile_5d));
   SNR_PvsraSrAppend(line, SNR_GoldMetricDouble(m3h.ok, m3h.delta_atr, 4));
   SNR_PvsraSrAppend(line, m3h.trend_bucket);
   SNR_PvsraSrAppend(line, SNR_GoldMetricDouble(m3h.ok, m3h.efficiency, 4));
   SNR_PvsraSrAppend(line, m3h.efficiency_bucket);
   SNR_PvsraSrAppend(line, SNR_GoldMetricDouble(m3h.ok, m3h.range_width_atr, 4));
   SNR_PvsraSrAppend(line, m3h.range_bucket);
   SNR_PvsraSrAppend(line, SNR_GoldMetricDouble(m8h.ok, m8h.delta_atr, 4));
   SNR_PvsraSrAppend(line, m8h.trend_bucket);
   SNR_PvsraSrAppend(line, SNR_GoldMetricDouble(m8h.ok, m8h.efficiency, 4));
   SNR_PvsraSrAppend(line, m8h.efficiency_bucket);
   SNR_PvsraSrAppend(line, SNR_GoldMetricDouble(m8h.ok, m8h.range_width_atr, 4));
   SNR_PvsraSrAppend(line, m8h.range_bucket);
   SNR_PvsraSrAppend(line, SNR_GoldMetricDouble(m1d.ok, m1d.delta_atr, 4));
   SNR_PvsraSrAppend(line, m1d.trend_bucket);
   SNR_PvsraSrAppend(line, SNR_GoldMetricDouble(m1d.ok, m1d.efficiency, 4));
   SNR_PvsraSrAppend(line, m1d.efficiency_bucket);
   SNR_PvsraSrAppend(line, SNR_GoldMetricDouble(m1d.ok, m1d.range_width_atr, 4));
   SNR_PvsraSrAppend(line, m1d.range_bucket);
   SNR_PvsraSrAppend(line, SNR_GoldMetricDouble(m5d.ok, m5d.delta_atr, 4));
   SNR_PvsraSrAppend(line, m5d.trend_bucket);
   SNR_PvsraSrAppend(line, SNR_GoldMetricDouble(m5d.ok, m5d.efficiency, 4));
   SNR_PvsraSrAppend(line, m5d.efficiency_bucket);
   SNR_PvsraSrAppend(line, SNR_GoldMetricDouble(m5d.ok, m5d.range_width_atr, 4));
   SNR_PvsraSrAppend(line, m5d.range_bucket);
   SNR_PvsraSrAppend(line, SNR_GoldMetricDouble(m10d.ok, m10d.delta_atr, 4));
   SNR_PvsraSrAppend(line, m10d.trend_bucket);
   SNR_PvsraSrAppend(line, SNR_GoldMetricDouble(m10d.ok, m10d.efficiency, 4));
   SNR_PvsraSrAppend(line, m10d.efficiency_bucket);
   SNR_PvsraSrAppend(line, SNR_GoldMetricDouble(m10d.ok, m10d.range_width_atr, 4));
   SNR_PvsraSrAppend(line, m10d.range_bucket);
   SNR_PvsraSrAppend(line, SNR_GoldMetricDouble(m20d.ok, m20d.delta_atr, 4));
   SNR_PvsraSrAppend(line, m20d.trend_bucket);
   SNR_PvsraSrAppend(line, SNR_GoldMetricDouble(m20d.ok, m20d.efficiency, 4));
   SNR_PvsraSrAppend(line, m20d.efficiency_bucket);
   SNR_PvsraSrAppend(line, SNR_GoldMetricDouble(m20d.ok, m20d.range_width_atr, 4));
   SNR_PvsraSrAppend(line, m20d.range_bucket);
   SNR_PvsraSrAppend(line, SNR_GoldMetricDouble(m20d.ok, price_position_20d, 4));
   SNR_PvsraSrAppend(line, SNR_GoldMetricDouble(m20d.ok, drawdown_20d, 4));
   SNR_PvsraSrAppend(line, SNR_GoldMetricDouble(m20d.ok, reclaim_20d, 4));
   SNR_PvsraSrAppend(line, DoubleToString(ctx.dragon_slope_atr, 4));
   SNR_PvsraSrAppend(line, DoubleToString(ctx.trend_slope_atr, 4));
   SNR_PvsraSrAppend(line, IntegerToString(ctx.h1_bias));
   SNR_PvsraSrAppend(line, IntegerToString(ctx.h4_bias));
   SNR_PvsraSrAppend(line, ctx.pvsra_event);
   SNR_PvsraSrAppend(line, IntegerToString(ctx.pvsra_grade));
   SNR_PvsraSrAppend(line, ctx.level_zone);
   SNR_PvsraSrAppend(line, block_reason);
   FileWriteString(handle, line + "\r\n");
   FileClose(handle);
}

#endif
