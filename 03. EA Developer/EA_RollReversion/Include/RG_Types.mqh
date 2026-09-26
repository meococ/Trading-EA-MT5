//+------------------------------------------------------------------+
//| RG_Types.mqh                                                     |
//| RollReversion - params, signal, per-day state.                   |
//|                                                                  |
//| Mechanism (frozen prereg HYP-RGR-CHF-M1-001): the server-00:00   |
//| day reopen (5pm-ET roll) gaps down vs fair value; fade the gap.  |
//| All gates are SERVER time - no GMT conversion in the signal path.|
//+------------------------------------------------------------------+
#ifndef RG_TYPES_MQH
#define RG_TYPES_MQH

#define RG_LEG_NONE   0
#define RG_LEG_LONG   1
#define RG_LEG_SHORT  2
#define RG_LEG_COUNT  3

//--- Mechanism parameters (not part of the shared LswConfig).
struct RgParams
  {
   bool              use_long;        // gap-down -> LONG
   bool              use_short;       // gap-up   -> SHORT (USDCHF side only)
   double            gap_long_pips;   // arm LONG when gap <= -x pips
   double            gap_short_pips;  // arm SHORT when gap >= +x pips
   double            gap_max_pips;    // sanity cap: skip absurd gaps
   int               entry_min_min;   // first entry minute of server day
   int               entry_max_min;   // last entry minute of server day
   double            sl_pips;         // fixed stop, pips
   double            tp_r;            // TP in R of risk (non-binding)
   int               time_stop_min;   // position age exit, minutes
  };

//--- Armed signal once the day-boundary gap is measured.
struct RgSignal
  {
   bool              valid;
   int               direction;    // LSW_DIR_LONG / LSW_DIR_SHORT
   int               leg;          // RG_LEG_*
   double            gap_pips;
   datetime          day_bar_time; // first bar of the new server day
  };

//--- Per-server-day state.
struct RgDayState
  {
   int               day_key;        // yyyymmdd
   bool              gap_measured;
   double            gap_pips;
   int               long_used;
   int               short_used;
  };

string RgLegName(const int leg)
  {
   switch(leg)
     {
      case RG_LEG_LONG:  return("LONG");
      case RG_LEG_SHORT: return("SHORT");
      default:           break;
     }
   return("NONE");
  }

#endif
