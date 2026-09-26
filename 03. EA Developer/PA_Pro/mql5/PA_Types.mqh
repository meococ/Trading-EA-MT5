//+------------------------------------------------------------------+
//|                                                     PA_Types.mqh |
//|  PA-PRO EA lane - shared types and frozen constants.             |
//|                                                                  |
//|  Every constant here mirrors the frozen Python source of truth:  |
//|    PA_Pro/struct/zones/common.py      DEFAULTS (v0, pre-declared)|
//|    PA_Pro/struct/zones/<gen>.py       per-generator DEFAULTS     |
//|    PA_Pro/lib/pa_fill.py              order / flats spec         |
//|    PA_Pro/lib/pa_costs.py             c_rt p90 cost table        |
//|  Python file:line citations sit next to each value.              |
//|                                                                  |
//|  VISUAL / SIGNAL ONLY.  No order, position or trade call exists  |
//|  in this header.                                                 |
//+------------------------------------------------------------------+
#ifndef PA_TYPES_MQH
#define PA_TYPES_MQH

//--- bar dict = pa_data.resample("M5") return value, one closed bar
struct PaBar
  {
   long              t;        // bar OPEN time, server clock, unix seconds
   double            o;
   double            h;
   double            l;
   double            c;
   int               utc_min;  // UTC minute-of-day of the bar CLOSE (mod-1440 fix)
   int               srv_min;  // server minute-of-day of the bar CLOSE
   int               dow;      // weekday of the server CLOSE day, Monday=0
  };

//--- zone kind ids (string names identical to the Python generators so the
//--- parity CSVs diff cleanly: common.py / ref_zones.py / sd_base_zones.py)
enum ENUM_PA_ZK
  {
   PA_ZK_SWING = 0,      // "swing"      line1_cluster_zones.py
   PA_ZK_SWING_H1,       // "swing_h1"   fractal_zones.py
   PA_ZK_DENSITY,        // "density"    kde_swing_zones.py
   PA_ZK_PROFILE_POC,    // "profile_poc" profile_zones.py
   PA_ZK_DEMAND,         // "demand"     sd_base_zones.py
   PA_ZK_SUPPLY,         // "supply"     sd_base_zones.py
   PA_ZK_PDH,            // "pdh"        ref_zones.py
   PA_ZK_PDL,            // "pdl"
   PA_ZK_PDC,            // "pdc"
   PA_ZK_ASIA_HI,        // "asia_hi"
   PA_ZK_ASIA_LO,        // "asia_lo"
   PA_ZK_WK_HI,          // "wk_hi"
   PA_ZK_WK_LO,          // "wk_lo"
   PA_ZK_ROUND,          // "round"
   PA_ZK_COUNT
  };

string PaZoneKindName(const int k)
  {
   switch(k)
     {
      case PA_ZK_SWING:       return("swing");
      case PA_ZK_SWING_H1:    return("swing_h1");
      case PA_ZK_DENSITY:     return("density");
      case PA_ZK_PROFILE_POC: return("profile_poc");
      case PA_ZK_DEMAND:      return("demand");
      case PA_ZK_SUPPLY:      return("supply");
      case PA_ZK_PDH:         return("pdh");
      case PA_ZK_PDL:         return("pdl");
      case PA_ZK_PDC:         return("pdc");
      case PA_ZK_ASIA_HI:     return("asia_hi");
      case PA_ZK_ASIA_LO:     return("asia_lo");
      case PA_ZK_WK_HI:       return("wk_hi");
      case PA_ZK_WK_LO:       return("wk_lo");
      case PA_ZK_ROUND:       return("round");
     }
   return("?");
  }

//--- scale ids: {"micro","meso","macro"} (common.py _strength)
enum ENUM_PA_SCALE
  {
   PA_SC_MICRO = 0,
   PA_SC_MESO,
   PA_SC_MACRO
  };

double PaScaleScore(const int scale,const double micro,const double meso,
                    const double macro)
  {
   if(scale==PA_SC_MESO)
      return(meso);
   if(scale==PA_SC_MACRO)
      return(macro);
   return(micro);
  }

//--- generator ids, registry.py order (baseline first)
enum ENUM_PA_GEN
  {
   PA_GEN_LINE1 = 0,     // "line1_cluster"
   PA_GEN_FRACTAL,       // "fractal_h1"
   PA_GEN_KDE,           // "kde_swing"
   PA_GEN_PROFILE,       // "profile_va"
   PA_GEN_SD_BASE,       // "sd_base"
   PA_GEN_REFS,          // "ref_levels"
   PA_GEN_COUNT
  };

string PaGenName(const int g)
  {
   switch(g)
     {
      case PA_GEN_LINE1:    return("line1_cluster");
      case PA_GEN_FRACTAL:  return("fractal_h1");
      case PA_GEN_KDE:      return("kde_swing");
      case PA_GEN_PROFILE:  return("profile_va");
      case PA_GEN_SD_BASE:  return("sd_base");
      case PA_GEN_REFS:     return("ref_levels");
     }
   return("?");
  }

int PaGenByName(const string name)
  {
   for(int g=0;g<(int)PA_GEN_COUNT;g++)
      if(PaGenName(g)==name)
         return(g);
   return(-1);
  }

//+------------------------------------------------------------------+
//| Frozen constants (common.py DEFAULTS :74-106)                    |
//+------------------------------------------------------------------+
#define PA_WIDTH_ATR        0.25    // zone band width around the cluster
#define PA_MAX_WIDTH_ATR    0.60    // hard cap (addendum 1 item 1)
#define PA_BREAK_ATR        0.10    // close beyond band edge by > this = BREAK
#define PA_MIN_TOUCH_SEP    2       // bars between counted touch episodes
#define PA_RESP_MOVE_ATR    1.0     // respected test move, x ATR14(H1)
#define PA_RESP_WINDOW      48      // ... within 48 closed bars
#define PA_RECLAIM_BARS     96      // close back inside within this = BREAK_FAIL
#define PA_FRESH_BARS       24      // no touch in the last 24 bars = fresh
#define PA_MAX_AGE_BARS     2880    // retire 10 server days after birth
#define PA_BREAK_KEEP_BARS  192     // a broken zone stays 1 day for role flip
#define PA_ARM_NEAR_ATR     2.0     // only zones within +-2 x ATR14(H1)
#define PA_ARM_DEDUPE_ATR   0.25    // centers closer than this are one zone
#define PA_ARM_MAX          6       // at most 6 armed zones on the chart
//--- strength weights (sum 1.00)
#define PA_W_TOUCH          0.30
#define PA_W_RESP           0.20
#define PA_W_REC            0.15
#define PA_W_AGE            0.10
#define PA_W_SCALE          0.10
#define PA_W_ROLE           0.05
#define PA_W_REF            0.05
#define PA_W_QUAL           0.05
#define PA_TOUCH_FULL       4.0
#define PA_RESP_FULL        3.0
#define PA_REC_HALF_LIFE    288.0   // 1 server day
#define PA_AGE_FULL         288.0
#define PA_SCALE_MICRO      0.4
#define PA_SCALE_MESO       0.7
#define PA_SCALE_MACRO      1.0

//--- refs.py
#define PA_ROUND_GRID_PIPS  50.0
#define PA_ASIA_UTC_LO      0
#define PA_ASIA_UTC_HI      300

//--- generator DEFAULTS (per-file headers)
//--- line1_cluster_zones.py :37-43
#define PA_L1_PIVOT_LAG     3
#define PA_L1_SCAN_BARS     240
#define PA_L1_LINK_ATR      0.25
#define PA_L1_WIDTH_ATR     0.25
#define PA_L1_MAX_W_ATR     0.60
//--- fractal_zones.py :42-51
#define PA_FR_PIVOT_K       2
#define PA_FR_PROM_LOOK     12
#define PA_FR_PROM_ATR      0.40
#define PA_FR_SCAN_BARS     480
#define PA_FR_WIDTH_ATR     0.30
#define PA_FR_LINK_ATR      0.30
#define PA_FR_MAX_W_ATR     0.60
#define PA_FR_MAX_AGE       5760
//--- kde_swing_zones.py :51-67
#define PA_KD_PIV_M5        3
#define PA_KD_PIV_H1        2
#define PA_KD_PROM_M5       6
#define PA_KD_PROM_H1       12
#define PA_KD_W_LO          0.20
#define PA_KD_W_HI          1.50
#define PA_KD_REFRESH       24
#define PA_KD_WINDOW        1440
#define PA_KD_GRID_N        160
#define PA_KD_BW_ATR        0.20
#define PA_KD_PEAK_FRAC     0.50
#define PA_KD_MIN_W         0.20
#define PA_KD_MAX_W         0.60
#define PA_KD_LINK_ATR      0.25
#define PA_KD_MAX_AGE       2880
//--- profile_zones.py :48-56
#define PA_PF_WINDOW        1440
#define PA_PF_BIN_ATR       0.10
#define PA_PF_MAX_BINS      800
#define PA_PF_VA_FRAC       0.70
#define PA_PF_MIN_W         0.20
#define PA_PF_MAX_W         0.60
#define PA_PF_MAX_AGE       2880
//--- sd_base_zones.py :51-61
#define PA_SD_BASE_MAX      3
#define PA_SD_IMP_MAX       6
#define PA_SD_BASE_RANGE    0.35
#define PA_SD_IMP_MIN       1.2
#define PA_SD_PAD_ATR       0.05
#define PA_SD_MIN_W         0.20
#define PA_SD_MAX_W         0.60
#define PA_SD_DEDUPE        0.25
#define PA_SD_MAX_AGE       1440
//--- ref_zones.py :51-55
#define PA_RF_WIDTH_ATR     0.25
#define PA_RF_DEDUPE        0.25
#define PA_RF_MAX_AGE       2880

//--- pa_fill.py DEFAULT_SPEC :50-63 + cost table (pa_costs.py C_RT_P90)
#define PA_ORD_BUF_PIPS        1.0
#define PA_ORD_V_BARS          3
#define PA_ORD_TP_MULT         2.0
#define PA_ORD_S_PIPS          8.0
#define PA_DAILY_FLAT_HOUR     22    // server hour
#define PA_FRIDAY_FLAT_HOUR    20    // server hour

//--- pa_costs.py C_RT_P90 :40-57 (pips, all-in round-turn p90)
double PaCostRtPips(const string sym)
  {
   if(sym=="EURUSD") return(1.0);
   if(sym=="GBPUSD") return(1.1);
   if(sym=="USDJPY") return(1.4);
   if(sym=="USDCHF") return(1.1);
   if(sym=="AUDUSD" || sym=="USDCAD" || sym=="NZDUSD") return(1.4);  // proxy
   return(1.4);                                                     // proxy fallback
  }

double PaPipSize(const string sym)
  {
   int d=(int)SymbolInfoInteger(sym,SYMBOL_DIGITS);
   double pt=SymbolInfoDouble(sym,SYMBOL_POINT);
   return((d==3 || d==5) ? 10.0*pt : pt);   // VpaPipSize, VPA_Core.mqh:1643
  }

//--- "no value" sentinel: Python uses NaN + (a != a) checks; MQL5 uses a
//--- parallel *_ok flag everywhere instead (no NaN arithmetic).
#define PA_DAY_SEC  86400

#endif // PA_TYPES_MQH
