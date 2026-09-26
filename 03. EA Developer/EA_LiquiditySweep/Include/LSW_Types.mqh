//+------------------------------------------------------------------+
//| LSW_Types.mqh                                                    |
//| Liquidity Sweep Reversion - shared types and tiny helpers.       |
//| Standalone: this package depends on no SNR_* file.               |
//+------------------------------------------------------------------+
#ifndef LSW_TYPES_MQH
#define LSW_TYPES_MQH

#define LSW_ATR_PERIOD      14      // pinned by CONTRACT.md §5
#define LSW_MAX_LEVELS      8       // PDH/PDL, AsiaH/L, ORH/L, RoundUp/Dn
#define LSW_DIR_LONG        1
#define LSW_DIR_NONE        0
#define LSW_DIR_SHORT      (-1)
#define LSW_SEC_PER_M5      300
#define LSW_SEC_PER_HOUR    3600
#define LSW_SEC_PER_DAY     86400

//--- Level provenance. Used for per-family telemetry attribution.
enum LSW_FAMILY
  {
   LSW_FAM_NONE=0,
   LSW_FAM_PREV_DAY=1,
   LSW_FAM_ASIA=2,
   LSW_FAM_OPEN_RANGE=3,
   LSW_FAM_ROUND=4
  };
#define LSW_FAMILY_COUNT 5

//--- Which liquidity sessions are tradable.
enum LSW_SESSION_MODE
  {
   LSW_SESS_LONDON_ONLY=0,
   LSW_SESS_NY_ONLY=1,
   LSW_SESS_BOTH=2
  };

//--- One reference level. `is_high` marks the side stops are expected to rest on.
struct LswLevel
  {
   double            price;
   LSW_FAMILY        family;
   bool              is_high;      // true: level above, stops beyond it are buy-stops
  };

struct LswLevelSet
  {
   LswLevel          items[LSW_MAX_LEVELS];
   int               count;
  };

//--- Frozen decision-clock snapshot, derived from a closed bar's server time.
struct LswClock
  {
   bool              valid;
   datetime          server_time;
   datetime          gmt_time;
   int               gmt_hour;
   int               gmt_day_of_week;   // 0=Sunday .. 6=Saturday
   datetime          gmt_day_start;
   int               server_hour;
   int               server_day_of_week;
   bool              weekend;
   bool              in_london;
   bool              in_newyork;
   bool              rollover;          // broker rollover hours, entries blocked
   bool              flatten;           // hard-flat window (server clock)
   bool              friday_flatten;
   bool              entry_window;      // session open AND not rollover AND not flatten
   datetime          session_open_gmt;  // open of the active session, 0 when none
  };

//--- Detected sweep on a closed bar.
struct LswSweep
  {
   bool              valid;
   int               direction;         // LSW_DIR_LONG / LSW_DIR_SHORT
   double            level;
   LSW_FAMILY        family;
   double            extreme;           // the swept high (short) or low (long)
   double            close_price;       // confirmation close = intended entry ref
   double            penetration;       // price units beyond the level
   double            atr;
   datetime          bar_time;          // open time of the sweep bar (server)
   string            reject;            // last geometry reject tag, "" when valid
  };

//--- Sized, geometry-checked order plan.
struct LswPlan
  {
   bool              valid;
   int               direction;
   double            entry;
   double            sl;
   double            tp;
   double            volume;
   double            risk_distance;
   double            money_per_lot;
   string            reject;
  };

//--- Account-level safety state. Rebuilt from live account data every tick,
//--- so it is restart-safe except for the intraday counters noted in README.
struct LswRiskState
  {
   int               day_key;           // yyyymmdd on the SERVER clock
   double            day_start_equity;
   double            peak_equity;
   bool              day_locked;
   bool              dd_locked;
   bool              streak_locked;
   int               daily_entries;
   int               consecutive_losses;
  };

//--- Everything OnDeinit prints. All plain counters; no allocation.
struct LswCounters
  {
   long              closed_bars;
   long              decisions;
   long              signals_seen;
   long              signals_long;
   long              signals_short;
   //--- geometry
   long              geom_no_level;
   long              geom_pen_small;
   long              geom_pen_large;
   long              geom_no_close_back;
   long              geom_bad_approach;
   long              geom_hold_failed;
   long              geom_conflict;
   //--- filters (one counter per filter, per WORKFLOW §3)
   long              filt_session;
   long              filt_rollover;
   long              filt_flatten;
   long              filt_spread;
   long              filt_atr_floor;
   long              filt_news;
   long              filt_max_trades;
   long              filt_streak_lock;
   long              filt_daily_lock;
   long              filt_dd_lock;
   long              filt_position_open;
   long              filt_exec_busy;
   long              filt_bar_gap;      // non-contiguous M5 bars (weekend/holiday seam)
   //--- entry
   long              entry_reject_plan;
   long              entry_reject_sizing;
   long              entry_reject_geometry;
   long              entry_reject_submit;
   long              entries_submitted;
   long              entries_filled;
   long              entry_timeouts;
   //--- exit
   long              exit_time_stop;
   long              exit_daily_flat;
   long              exit_friday_flat;
   long              exit_reject;
   long              be_moves;
   long              be_rejects;
   long              deals_out;
   long              deals_out_loss;
   //--- data integrity
   long              data_fail;
   long              news_query_empty;
   long              kernel_recycles;
   long              kernel_ambiguous;
   //--- attribution
   long              trades_by_family[LSW_FAMILY_COUNT];
   long              signals_by_family[LSW_FAMILY_COUNT];
  };

//--- Immutable per-run configuration, filled once from the EA inputs.
struct LswConfig
  {
   //--- clock / session
   int               server_gmt_offset_hours;
   bool              server_dst_us_rule;
   LSW_SESSION_MODE  session_mode;
   int               flatten_hour_server;
   int               friday_flatten_hour_server;
   //--- levels
   bool              use_prev_day;
   bool              use_asia;
   bool              use_open_range;
   double            round_step;
   int               or_bars;
   //--- sweep geometry
   double            sweep_min_atr;
   double            sweep_max_atr;
   bool              require_next_bar_hold;
   //--- exit
   double            sl_buffer_atr;
   double            min_sl_spread_mult;
   double            tp_r;
   int               max_hold_bars;
   double            be_at_r;
   //--- filters / risk
   double            max_spread_atr;
   double            min_atr_points;
   int               news_blackout_min;
   double            risk_percent;
   int               max_trades_per_day;
   int               max_consecutive_losses;
   double            max_daily_loss_pct;
   double            max_account_dd_pct;
   //--- execution
   ulong             magic;
   ulong             slippage_points;
   bool              verbose;
  };

bool LswFinite(const double v)
  {
   return(MathIsValidNumber(v));
  }

int LswDayKey(const datetime stamp)
  {
   MqlDateTime p;
   TimeToStruct(stamp,p);
   return(p.year*10000+p.mon*100+p.day);
  }

//--- Truncate a timestamp to the start of its calendar day.
datetime LswDayStart(const datetime stamp)
  {
   return((datetime)((long)stamp-(long)stamp%LSW_SEC_PER_DAY));
  }

int LswVolumeDigits(const double step)
  {
   int digits=0;
   double scaled=step;
   while(digits<8 && MathAbs(scaled-MathRound(scaled))>1e-9)
     {
      scaled*=10.0;
      digits++;
     }
   return(digits);
  }

string LswFamilyName(const LSW_FAMILY family)
  {
   switch(family)
     {
      case LSW_FAM_PREV_DAY:   return("PREV_DAY");
      case LSW_FAM_ASIA:       return("ASIA");
      case LSW_FAM_OPEN_RANGE: return("OPEN_RANGE");
      case LSW_FAM_ROUND:      return("ROUND");
      default:                 break;
     }
   return("NONE");
  }

#endif
