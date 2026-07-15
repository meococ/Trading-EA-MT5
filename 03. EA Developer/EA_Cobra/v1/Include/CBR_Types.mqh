//+------------------------------------------------------------------+
//| CBR_Types.mqh — EA_Cobra v1 Types & Structures                   |
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

//--- Trend Bias
enum ENUM_CBR_BIAS
{
   CBR_BIAS_NONE  = 0,
   CBR_BIAS_BULL  = 1,
   CBR_BIAS_BEAR  = -1
};

//--- Signal Structure (unified)
struct CBR_Signal
{
   // Core decision
   bool              valid;
   ENUM_ORDER_TYPE   type;           // BUY or SELL
   ENUM_CBR_KILLZONE killZone;       // Which KZ triggered

   // Bar diagnostics (for logging)
   double            atr;            // Current ATR(14) value
   double            bodyRatio;      // |close-open| / (high-low)
   double            closeLoc;       // Close location (0=low extreme, 1=high extreme)
   double            barRangeAtr;    // Bar range as multiple of ATR
   double            bbwPctile;      // BB width percentile (0-100)
   int               bias;           // +1/-1/0
   double            emaFast;        // EMA21 value
   double            emaSlow;        // EMA55 value

   // Execution levels
   double            slPrice;        // Hard SL price
   double            tpPrice;        // TP price
   double            slPts;          // SL in points
   double            rrRatio;        // R:R ratio

   // Rejection
   string            rejectReason;   // Why signal rejected
};

//--- Daily State Tracking
struct CBR_DayState
{
   datetime          dayStart;       // Current day start
   double            eqStart;        // Equity at day start
   double            eqPeak;         // Peak equity today
   int               tradeCount;     // Trades taken today
   int               lossCount;      // Losses today (consecutive)
   int               kzLdnTrades;    // London KZ trades today
   int               kzNyTrades;     // NY KZ trades today
   int               kzNycTrades;    // NYC KZ trades today
};

//--- Position Tracking (for cascade)
struct CBR_PosInfo
{
   ulong             ticket;
   double            openPrice;
   double            slPrice;
   double            tpPrice;
   int               cascadeCount;   // How many cascades added
   bool              beMoved;        // Break-even applied?
};

#endif // CBR_TYPES_MQH
