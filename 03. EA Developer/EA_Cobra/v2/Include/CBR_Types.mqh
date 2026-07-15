//+------------------------------------------------------------------+
//| CBR_Types.mqh — EA_Cobra v2 Types & Structures                   |
//+------------------------------------------------------------------+
#ifndef CBR_TYPES_MQH
#define CBR_TYPES_MQH

//--- Kill Zone Enum
enum ENUM_CBR_KILLZONE
{
   CBR_KZ_NONE   = 0,   // Outside all kill zones
   CBR_KZ_LDN    = 1,   // London Open (07:00-09:00)
   CBR_KZ_NY     = 2,   // NY Open (13:00-15:00)
   CBR_KZ_NYC    = 3    // NY Close (16:00-17:00)
};

//--- Entry Mode (how price interacts with level)
enum ENUM_CBR_ENTRY_MODE
{
   CBR_ENTRY_NONE     = 0,   // No valid interaction
   CBR_ENTRY_BREAKOUT = 1,   // Price broke through level with momentum
   CBR_ENTRY_BOUNCE   = 2    // Price bounced off level (touch + rejection)
};

//--- Level Type
enum ENUM_CBR_LEVEL_TYPE
{
   CBR_LVL_NONE       = 0,
   CBR_LVL_ASIAN_HI   = 1,   // Asian session high
   CBR_LVL_ASIAN_LO   = 2,   // Asian session low
   CBR_LVL_PREV_HI    = 3,   // Previous day high
   CBR_LVL_PREV_LO    = 4    // Previous day low
};

//--- Session Level Set (built each day)
struct CBR_LevelSet
{
   // Asian Range
   double   asianHi;        // Asian session high
   double   asianLo;        // Asian session low
   double   asianRange;     // Asian range in points
   bool     asianValid;     // Range within min-max bounds
   datetime asianBuildDay;  // Day this was built

   // Previous Day H/L
   double   prevDayHi;      // Previous trading day high
   double   prevDayLo;      // Previous trading day low
   bool     prevDayValid;   // Successfully extracted
   datetime prevDayDate;    // Date of prev day
};

//--- Signal Structure (v2: level-enriched)
struct CBR_Signal
{
   // Core decision
   bool              valid;
   ENUM_ORDER_TYPE   type;           // BUY or SELL
   ENUM_CBR_KILLZONE killZone;       // Which KZ triggered
   ENUM_CBR_ENTRY_MODE entryMode;    // Breakout or Bounce
   ENUM_CBR_LEVEL_TYPE levelType;    // Which level triggered

   // Level diagnostics
   double            levelPrice;     // The reference level price
   double            levelDist;      // Distance from level (pts)

   // Bar diagnostics
   double            atr;
   double            bodyRatio;
   double            closeLoc;
   double            barRangeAtr;
   double            bbwPctile;
   int               bias;
   double            emaFast;
   double            emaSlow;

   // Execution levels
   double            slPrice;        // Hard SL price (anchored to level)
   double            tpPrice;        // TP price
   double            slPts;          // SL in points
   double            rrRatio;        // R:R ratio

   // Rejection
   string            rejectReason;
};

//--- Daily State Tracking
struct CBR_DayState
{
   datetime          dayStart;
   double            eqStart;
   double            eqPeak;
   int               tradeCount;
   int               lossCount;
   int               kzLdnTrades;
   int               kzNyTrades;
   int               kzNycTrades;
};

#endif // CBR_TYPES_MQH
