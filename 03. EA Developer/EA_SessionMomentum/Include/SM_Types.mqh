//+------------------------------------------------------------------+
//| SM_Types.mqh                                                     |
//| SessionMomentum - leg identifiers, params and per-day state.     |
//|                                                                  |
//| With-trend continuation sleeve on one chart symbol (frozen       |
//| prereg: HYP-SMOM-JPY-M5-001):                                    |
//|   LEG_LDN - first-2h wick pierce of the prior ASIA full-session  |
//|             extreme (00:00-07:00 GMT), entered WITH direction,   |
//|             held to the 16:00 GMT London close.                  |
//|   LEG_NY  - first-2h wick pierce of the prior LDN partial        |
//|             extreme (07:00-12:00 GMT), entered WITH direction,   |
//|             held to the 20:00 GMT NY close.                      |
//| Shared substrate: clock/DST/news/sizing/plan from LSW_* modules; |
//| execution kernel + lifecycle telemetry from _Shared.             |
//+------------------------------------------------------------------+
#ifndef SM_TYPES_MQH
#define SM_TYPES_MQH

#define SM_LEG_NONE   0
#define SM_LEG_LDN    1
#define SM_LEG_NY     2
#define SM_LEG_COUNT  3

#define SM_SEC_PER_M5 300

//--- Per-leg session geometry, GMT minutes past midnight.
struct SmLegGeom
  {
   int               open_min;     // session open (first trigger bar)
   int               trig_end;     // trigger window end (exclusive)
   int               prior_start;  // level window start, same GMT day
   int               prior_end;    // level window end (exclusive)
   int               exit_min;     // leg time-stop
  };

//--- Mechanism parameters (not part of the shared LswConfig).
struct SmParams
  {
   bool              use_ldn;
   bool              use_ny;
   SmLegGeom         ldn;          // {420, 540, 0, 420, 960}
   SmLegGeom         ny;           // {720, 840, 420, 720, 1200}
   double            sl_atr;       // catastrophe stop, xATR14
  };

//--- Detected continuation signal on a closed bar.
struct SmSignal
  {
   bool              valid;
   int               direction;    // LSW_DIR_LONG / LSW_DIR_SHORT
   int               leg;          // SM_LEG_*
   double            level_high;   // level context (telemetry)
   double            level_low;
   double            atr;
   datetime          ref_bar_time; // trigger bar (server time)
  };

//--- Per-GMT-day state: one entry per leg per day.
struct SmDayState
  {
   int               ldn_day_key;
   int               ny_day_key;
  };

string SmLegName(const int leg)
  {
   switch(leg)
     {
      case SM_LEG_LDN: return("LDN");
      case SM_LEG_NY:  return("NY");
      default:         break;
     }
   return("NONE");
  }

#endif
