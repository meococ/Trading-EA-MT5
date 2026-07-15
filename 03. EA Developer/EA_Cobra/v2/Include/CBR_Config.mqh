//+------------------------------------------------------------------+
//| CBR_Config.mqh — EA_Cobra v2 Configuration                       |
//| Level-Based Kill Zone Scalper — XAUUSD M15                       |
//| Max (2026-03-19)                                                  |
//+------------------------------------------------------------------+
#ifndef CBR_CONFIG_MQH
#define CBR_CONFIG_MQH

#define CBR_VERSION          "2.5.1"
#define CBR_EA_NAME          "EA_Cobra_v2.5.1"

//--- Kill Zone Windows (Server Time UTC+2/+3 typical)
#define CBR_KZ_LDN_START_H   99     // v2.4: DISABLED London (PF 1.01 = no edge)
#define CBR_KZ_LDN_END_H     99     // v2.4: DISABLED
#define CBR_KZ_NY_START_H     13     // NY Kill Zone 13:00
#define CBR_KZ_NY_END_H       15     // NY Kill Zone ends 15:00
#define CBR_KZ_NYC_START_H    16     // NY Close Kill Zone 16:00
#define CBR_KZ_NYC_END_H      17     // NY Close Kill Zone ends 17:00

//--- Asian Range Session (for level building)
#define CBR_ASIAN_START_H     0      // Asian range starts 00:00 server
#define CBR_ASIAN_END_H       7      // Asian range ends 07:00 (before LDN KZ)
#define CBR_ASIAN_RANGE_MIN   300    // Min Asian range (pts) to be valid
#define CBR_ASIAN_RANGE_MAX   8000   // Max Asian range (pts) — skip extreme days

//--- Level Interaction Zone
#define CBR_LEVEL_ZONE_PTS    150    // Zone around level for interaction (±150 pts)
#define CBR_LEVEL_BREAK_PTS   50     // How far past level = confirmed breakout

//--- Signal: Momentum Bar Detection (v2.1: tighter filters for quality)
#define CBR_BODY_RATIO_MIN    0.55   // v2.1: was 0.45, tightened for quality
#define CBR_CLOSE_LOC_MIN     0.65   // v2.1: was 0.55, tightened
#define CBR_ATR_RANGE_MIN     0.40   // v2.1: was 0.35, slightly tighter
#define CBR_ATR_RANGE_MAX     3.00   // v2.1: was 3.50, tighter

//--- Signal: Trend Confirmation
#define CBR_EMA_FAST          21     // Fast EMA period (H1)
#define CBR_EMA_SLOW          55     // Slow EMA period (H1)
#define CBR_TREND_MIN_DIST    50     // Min pts from EMA cluster for bias

//--- Signal: Volatility/Regime
#define CBR_ATR_PERIOD        14     // ATR period
#define CBR_BB_PERIOD         20     // BB period for squeeze detection
#define CBR_BB_DEV            2.0    // BB deviation
#define CBR_BBW_LOOKBACK      100    // Periods to calc BB width percentile

//--- Risk Management
#define CBR_SL_ATR_MULT       1.5    // v2.5: OPTIMAL (tested 1.2 = PF 1.61, DD 12.1% — worse)
#define CBR_SL_MIN_PTS        400    // Min SL points
#define CBR_SL_MAX_PTS        5000   // Max SL points
#define CBR_TP_RR_LDN         2.5    // v2.3: was 3.0, lower for higher WR
#define CBR_TP_RR_NY          2.0    // v2.3: was 2.5
#define CBR_TP_RR_NYC         1.8    // v2.5: OPTIMAL (tested 1.5, 2.0 — 1.8 = best DD)
#define CBR_BE_AT_R            1.0   // v2.5: KEEP (tested off = PF 1.63, DD 12.8% — BE helps Cobra)

//--- Level Distance Filter (v2.1 NEW)
#define CBR_MAX_LEVEL_DIST_ATR 2.0   // v2.5: OPTIMAL (2.5 = PF 1.56, DD 19% = dilutive)

//--- Position Management
#define CBR_MAX_SPREAD_PTS    50.0   // Max spread to enter
#define CBR_FRIDAY_CLOSE_H    17     // Friday flatten hour (server time)

//--- Day Filters
#define CBR_WED_SKIP          true    // v2.2: Skip Wednesday entirely (was 0.70 risk, still PF 0.87)
#define CBR_WED_RISK_MULT     0.00   // v2.2: 0 = skip (was 0.70)
#define CBR_MON_RISK_MULT     1.00   // v2.5: was 0.85, Monday PF 2.49 NYC-only = STRONGEST day

#endif // CBR_CONFIG_MQH
