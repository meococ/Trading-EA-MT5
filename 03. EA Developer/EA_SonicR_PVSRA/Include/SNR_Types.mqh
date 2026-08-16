#ifndef SNR_TYPES_MQH
#define SNR_TYPES_MQH

#define SNR_DIR_NONE   0
#define SNR_DIR_LONG   1
#define SNR_DIR_SHORT -1

#define SNR_SCAN_FLAT  0
#define SNR_SCAN_OWNED 1
#define SNR_SCAN_FAIL  2
#define SNR_SCAN_MULTI 3

#define SNR_PVSRA_UNKNOWN 0
#define SNR_PVSRA_LOW     1
#define SNR_PVSRA_NORMAL  2
#define SNR_PVSRA_RISING  3
#define SNR_PVSRA_CLIMAX  4

#define SNR_WAVE_UNKNOWN 0
#define SNR_WAVE_CHOPPY  1
#define SNR_WAVE_CLEAN   2

#define SNR_SESS_NONE   0
#define SNR_SESS_LONDON 1
#define SNR_SESS_NY     2

#define SNR_SR_NONE    0
#define SNR_SR_WHOLE   1
#define SNR_SR_HALF    2
#define SNR_SR_QUARTER 4

#define SNR_SCOUT_ENABLED false

struct SnrHandles
  {
   int               dragon_high;
   int               dragon_mid;
   int               dragon_low;
   int               trend;
   int               atr;
  };

struct SnrClassicCfg
  {
   int               lookback;
   int               dragon_slope_bars;
   int               trend_slope_bars;
   double            dragon_min_slope_atr;
   int               swing_strength;
   int               wave_lookback;
   int               max_pullback_age;
   double            max_overlap_ratio;
   double            dragon_touch_atr;
   int               vol_avg_bars;
   double            vol_rising_mult;
   double            vol_climax_mult;
   double            round_whole;
   double            sr_runway_atr;
   int               london_start_hour;
   int               london_end_hour;
   int               ny_start_hour;
   int               ny_end_hour;
   int               friday_flatten_hour;
   bool              require_pvsra_support;
   bool              use_ny_session;
   int               offset_points;
   int               pending_ttl_bars;
   double            sl_cap;
   double            min_tp_runway;
   double            pip_size;
  };

struct SnrDragonSnap
  {
   bool              valid;
   double            high;
   double            mid;
   double            low;
   double            slope_atr;
   int               side;
   bool              angled;
  };

struct SnrTrendSnap
  {
   bool              valid;
   double            ema;
   double            slope;
   int               side;
  };

struct SnrWaveSnap
  {
   bool              valid;
   int               quality;
   int               direction;
   double            overlap_ratio;
   double            pullback_price;
   double            impulse_extreme;
   double            structure_swing;
   int               pullback_index;
   int               leg0_index;
   int               leg1_index;
   int               leg2_index;
   bool              into_dragon;
   bool              break_or_reject;
   bool              first_break;
   bool              leg1_thru_dragon;
  };

struct SnrPvsraSnap
  {
   bool              valid;
   int               cls;
   double            volume;
   double            average;
   bool              support;
   bool              veto;
  };

struct SnrSrSnap
  {
   bool              valid;
   bool              blocked;
   double            level;
   int               kind;
   double            distance;
  };

struct SnrSessionSnap
  {
   bool              valid;
   int               zone;
   bool              entry_allowed;
   bool              flatten;
   int               london_hour;
   int               london_dow;
   bool              uk_dst;
  };

struct SnrSignalDecision
  {
   bool              fired;
   bool              data_fail;
   datetime          decision_time;
   datetime          availability_time;
   int               direction;
   double            signal_high;
   double            signal_low;
   double            signal_close;
   double            atr;
   SnrDragonSnap     dragon;
   SnrTrendSnap      trend;
   SnrWaveSnap       wave;
   SnrPvsraSnap      pvsra;
   SnrSrSnap         sr;
   SnrSessionSnap    session;
   string            reject_reason;
  };

struct SnrRiskState
  {
   int               day_key;
   double            day_start_equity;
   double            peak_equity;
   bool              day_locked;
   bool              dd_locked;
   int               daily_entries;
   int               week_key;
   int               week_entries;
  };

struct SnrRiskPlan
  {
   bool              valid;
   double            entry;
   double            sl;
   double            tp;
   double            volume;
   double            risk_distance;
   double            one_lot_loss;
  };

struct SnrTelemetry
  {
   long              closed_bars;
   long              data_fails;
   long              signals;
   long              long_signals;
   long              short_signals;
   long              entries;
   long              entry_rejects;
   long              spread_rejects;
   long              risk_lock_skips;
   long              volume_rejects;
   long              window_skips;
   long              sr_blocks;
   long              wave_rejects;
   long              dragon_rejects;
   long              trend_rejects;
   long              pvsra_vetoes;
   long              pvsra_supports;
   long              close_attempts;
   long              close_rejects;
   long              closes;
   long              postfill_closes;
   int               csv_handle;
  };

bool SnrFinite(const double value)
  {
   return(value!=EMPTY_VALUE && MathIsValidNumber(value));
  }

void SnrHandlesReset(SnrHandles &h)
  {
   h.dragon_high=INVALID_HANDLE;
   h.dragon_mid=INVALID_HANDLE;
   h.dragon_low=INVALID_HANDLE;
   h.trend=INVALID_HANDLE;
   h.atr=INVALID_HANDLE;
  }

bool SnrHandlesReady(const SnrHandles &h)
  {
   return(h.dragon_high!=INVALID_HANDLE && h.dragon_mid!=INVALID_HANDLE &&
          h.dragon_low!=INVALID_HANDLE && h.trend!=INVALID_HANDLE &&
          h.atr!=INVALID_HANDLE);
  }

void SnrHandlesRelease(SnrHandles &h)
  {
   if(h.dragon_high!=INVALID_HANDLE)
      IndicatorRelease(h.dragon_high);
   if(h.dragon_mid!=INVALID_HANDLE)
      IndicatorRelease(h.dragon_mid);
   if(h.dragon_low!=INVALID_HANDLE)
      IndicatorRelease(h.dragon_low);
   if(h.trend!=INVALID_HANDLE)
      IndicatorRelease(h.trend);
   if(h.atr!=INVALID_HANDLE)
      IndicatorRelease(h.atr);
   SnrHandlesReset(h);
  }

bool SnrCopyClosedRates(const string symbol,const ENUM_TIMEFRAMES tf,
                        const int count,MqlRates &rates[])
  {
   ArraySetAsSeries(rates,true);
   if(count<=0)
      return(false);
   const int got=CopyRates(symbol,tf,1,count,rates);
   return(got>=count);
  }

bool SnrCopyClosedBuffer(const int handle,const int count,double &buf[])
  {
   if(handle==INVALID_HANDLE || count<=0)
      return(false);
   ArraySetAsSeries(buf,true);
   const int got=CopyBuffer(handle,0,1,count,buf);
   return(got>=count);
  }

int SnrHourInRange(const int hour,const int start_hour,const int end_hour)
  {
   if(start_hour==end_hour)
      return(0);
   if(start_hour<end_hour)
      return((hour>=start_hour && hour<end_hour) ? 1 : 0);
   return((hour>=start_hour || hour<end_hour) ? 1 : 0);
  }

#endif
