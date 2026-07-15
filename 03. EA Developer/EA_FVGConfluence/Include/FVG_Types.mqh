//+------------------------------------------------------------------+
//| FVG_Types.mqh — shared types / symbol packs                        |
//+------------------------------------------------------------------+
#ifndef FVG_TYPES_MQH
#define FVG_TYPES_MQH

enum ENUM_FVG_DIR
{
   FVG_DIR_NONE  = 0,
   FVG_DIR_BULL  = 1,
   FVG_DIR_BEAR  = -1
};

enum ENUM_ENTRY_MODE
{
   ENTRY_REJECTION = 0,   // pin / engulf / strong close into FVG
   ENTRY_MID_GAP   = 1,   // closed bar traded 40-60% gap depth
   ENTRY_EITHER    = 2
};

enum ENUM_SYMBOL_PACK
{
   PACK_AUTO   = 0,
   PACK_EURUSD = 1,
   PACK_GBPUSD = 2,
   PACK_XAUUSD = 3
};

enum ENUM_HTF_PERIOD
{
   HTF_H1 = 0,
   HTF_H4 = 1
};

struct SFVGZone
{
   ENUM_FVG_DIR dir;
   datetime     formed_time;
   int          formed_shift;   // chart shift at detection (relative)
   double       top;            // gap top (higher of the two gap edges)
   double       bottom;         // gap bottom
   double       mid;
   double       impulse_high;
   double       impulse_low;
   bool         valid;
   bool         fully_mitigated;
};

struct SConfluence
{
   bool htf_aligned;
   bool order_block;
   bool premium_discount;
   bool liquidity_sweep;
   bool session_ok;
   int  score;
};

struct SSymbolPack
{
   string name;
   double min_gap_pips;
   double sl_buffer_pips;
   bool   use_atr_min_gap;   // XAU: ATR-based floor
   double atr_min_gap_mult;
};

struct STradePlan
{
   ENUM_FVG_DIR dir;
   double       entry;
   double       sl;
   double       tp;
   double       risk_points;
   SFVGZone     zone;
   SConfluence  confl;
   string       reason;
};

#endif
