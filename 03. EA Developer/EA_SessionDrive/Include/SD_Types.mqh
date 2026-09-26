//+------------------------------------------------------------------+
//| SD_Types.mqh                                                     |
//| Session Drive - per-session FSM state and signal types.          |
//|                                                                  |
//| Shared substrate: this package reuses the LSW_* modules          |
//| (clock/DST/news/sizing/plan) via relative include. The LswConfig |
//| / LswClock / LswRiskState / LswSweep / LswPlan / LswCounters     |
//| types are generic wire containers; LSW was simply the first      |
//| consumer. Only the session FSM, signal adapter and telemetry     |
//| are SD-specific.                                                 |
//+------------------------------------------------------------------+
#ifndef SD_TYPES_MQH
#define SD_TYPES_MQH

//--- Session identifiers. A GMT day carries three independent opening-drive
//--- windows. LDN and NY overlap 12:00-16:00 GMT: the FSMs run in parallel,
//--- each tracking its own opening range.
#define SD_SESS_NONE   0
#define SD_SESS_ASIA   1
#define SD_SESS_LDN    2
#define SD_SESS_NY     3
#define SD_SESS_COUNT  4

#define SD_ASIA_OPEN_GMT   0
#define SD_ASIA_CLOSE_GMT  7
#define SD_LDN_OPEN_GMT    7
#define SD_LDN_CLOSE_GMT   16
#define SD_NY_OPEN_GMT     12
#define SD_NY_CLOSE_GMT    20

//--- Per-session finite state machine. One struct per session id.
struct SdSession
  {
   bool              seen;         // this session occurrence exists today
   bool              forming;      // inside the opening-range window
   bool              armed;        // OR complete and valid: watching for break
   bool              traded;       // entry already fired this session
   bool              dead;         // rejected (gap/range bound): skip to close
   int               or_count;     // closed bars accumulated into the OR
   double            orh;
   double            orl;
   datetime          last_bar;     // last OR bar fed (contiguity check)
   int               day_key;      // GMT day this occurrence belongs to
  };

//--- SD-specific mechanism parameters (not part of the shared LswConfig).
struct SdParams
  {
   int               or_bars;        // opening-range length, M5 bars
   double            or_min_atr;     // OR range floor, xATR14
   double            or_max_atr;     // OR range cap, xATR14
   int               break_bars;     // bars after OR where a break may fire
   bool              use_asia;
   bool              use_london;
   bool              use_newyork;
  };

//--- Detected drive signal on a closed bar (ORB continuation).
struct SdDrive
  {
   bool              valid;
   int               direction;    // LSW_DIR_LONG / LSW_DIR_SHORT
   int               session;      // SD_SESS_*
   double            orh;
   double            orl;
   double            or_mid;       // structural SL anchor
   double            atr;
   double            close_price;  // break-bar close = intended entry ref
   datetime          bar_time;     // open time of the break bar (server)
   string            reject;       // last geometry reject tag, "" when valid
  };

string SdSessionName(const int sess)
  {
   switch(sess)
     {
      case SD_SESS_ASIA: return("ASIA");
      case SD_SESS_LDN:  return("LDN");
      case SD_SESS_NY:   return("NY");
      default:           break;
     }
   return("NONE");
  }

#endif
