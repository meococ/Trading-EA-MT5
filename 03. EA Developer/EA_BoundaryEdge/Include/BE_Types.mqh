//+------------------------------------------------------------------+
//| BE_Types.mqh                                                     |
//| BoundaryEdge - leg identifiers, params and per-day state.        |
//|                                                                  |
//| Union sleeve of two confirmed session-boundary anomalies on one  |
//| chart symbol (frozen prereg: HYP-BEDGE-CHF-M5-001):              |
//|   LEG_FADE   - Asia first-2h close-pierce of the prior-hour      |
//|                extreme, faded to the 07:00 GMT session end.      |
//|   LEG_MONCH  - week-open drift: long at Monday 00:00 GMT, flat   |
//|                at 02:00 GMT.                                     |
//| Shared substrate: clock/DST/news/sizing/plan from LSW_* modules; |
//| execution kernel + lifecycle telemetry from _Shared.             |
//+------------------------------------------------------------------+
#ifndef BE_TYPES_MQH
#define BE_TYPES_MQH

#define BE_LEG_NONE   0
#define BE_LEG_FADE   1
#define BE_LEG_MONCH  2
#define BE_LEG_COUNT  3

#define BE_ASIA_OPEN_MIN   0      // first bar of the GMT day
#define BE_FADE_TRIG_END   120    // trigger window: first 2 hours
#define BE_FADE_LEVEL_BARS 12     // prior-hour extreme (23:00-24:00 GMT)
#define BE_ASIA_CLOSE_MIN  420    // 07:00 GMT session end
#define BE_MONCH_EXIT_MIN  120    // 02:00 GMT Monday chain exit
#define BE_SEC_PER_M5      300

//--- Mechanism parameters (not part of the shared LswConfig).
struct BeParams
  {
   bool              use_fade;       // LEG_FADE enabled
   bool              use_monch;      // LEG_MONCH enabled (symbol-dependent)
   int               fade_trig_end;  // trigger window end, GMT minute
   int               fade_level_bars;// bars before 00:00 forming the level
   int               asia_close_min; // fade time-exit, GMT minute
   int               monch_exit_min; // chain time-exit, GMT minute
   double            sl_atr;         // catastrophe stop, xATR14
  };

//--- Detected boundary signal on a closed bar (or a timed bar-open entry).
struct BeSignal
  {
   bool              valid;
   int               direction;    // LSW_DIR_LONG / LSW_DIR_SHORT
   int               leg;          // BE_LEG_*
   double            level_high;   // fade level context (telemetry)
   double            level_low;
   double            atr;
   datetime          ref_bar_time; // trigger bar (server time)
  };

//--- Per-GMT-day state: one fade entry per day, one chain per week.
struct BeDayState
  {
   int               fade_day_key; // GMT day the fade already fired on
   int               monch_day_key;// GMT day the chain already fired on
  };

string BeLegName(const int leg)
  {
   switch(leg)
     {
      case BE_LEG_FADE:  return("FADE");
      case BE_LEG_MONCH: return("MONCH");
      default:           break;
     }
   return("NONE");
  }

#endif
