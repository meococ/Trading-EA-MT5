//+------------------------------------------------------------------+
//| CBR_Config.mqh — EA_Cobra v1 Configuration                       |
//| Kill Zone Momentum Cascade — XAUUSD M15                          |
//| Max (2026-03-19)                                                  |
//+------------------------------------------------------------------+
#ifndef CBR_CONFIG_MQH
#define CBR_CONFIG_MQH

#define CBR_VERSION          "1.0"
#define CBR_EA_NAME          "EA_Cobra_v1"

//--- Kill Zone Windows (Server Time UTC+2/+3 typical)
//    Adjustable via inputs, these are defaults
#define CBR_KZ_LDN_START_H   7      // London Kill Zone 07:00
#define CBR_KZ_LDN_END_H     9      // London Kill Zone ends 09:00 (2 hours)
#define CBR_KZ_NY_START_H     13     // NY Kill Zone 13:00
#define CBR_KZ_NY_END_H       15     // NY Kill Zone ends 15:00 (2 hours)
#define CBR_KZ_NYC_START_H    16     // NY Close Kill Zone 16:00
#define CBR_KZ_NYC_END_H      17     // NY Close Kill Zone ends 17:00 (1 hour)

//--- Signal: Momentum Bar Detection
#define CBR_BODY_RATIO_MIN    0.55   // Min body/range (strong candle)
#define CBR_CLOSE_LOC_MIN     0.60   // Close location value (how close to extreme)
#define CBR_ATR_RANGE_MIN     0.45   // Bar range >= X * ATR (meaningful move)
#define CBR_ATR_RANGE_MAX     3.00   // Bar range <= X * ATR (not spike)

//--- Signal: Trend Confirmation
#define CBR_EMA_FAST          21     // Fast EMA period (H1)
#define CBR_EMA_SLOW          55     // Slow EMA period (H1)
#define CBR_TREND_MIN_DIST    50     // Min pts from EMA cluster for bias

//--- Signal: Volatility/Regime
#define CBR_ATR_PERIOD        14     // ATR period
#define CBR_BB_PERIOD         20     // BB period for squeeze detection
#define CBR_BB_DEV            2.0    // BB deviation
#define CBR_BBW_LOOKBACK      100    // Periods to calc BB width percentile
#define CBR_SQUEEZE_PCT       60     // BBW percentile threshold (higher = tighter squeeze)

//--- Risk Management
#define CBR_SL_ATR_MULT       1.2    // SL = X * ATR (tighter than Phoenix's 1.5)
#define CBR_SL_MIN_PTS        400    // Min SL points
#define CBR_SL_MAX_PTS        4000   // Max SL points
#define CBR_TP_RR_LDN         3.0    // London R:R target
#define CBR_TP_RR_NY          2.5    // NY R:R target
#define CBR_TP_RR_NYC         2.0    // NY Close R:R target (shorter window)
#define CBR_BE_AT_R            1.0   // Move to BE at X*R profit

//--- Position Management
#define CBR_MAX_SPREAD_PTS    50.0   // Max spread to enter
#define CBR_FRIDAY_CLOSE_H    17     // Friday flatten hour (server time)

//--- Day Filters
#define CBR_WED_RISK_MULT     0.70   // Wednesday risk reduction
#define CBR_MON_RISK_MULT     0.85   // Monday risk reduction (pre-London choppy)

//--- Cascade (add-on)
#define CBR_CASCADE_ENABLED   true   // Allow cascade (add-on) entries
#define CBR_CASCADE_MIN_PIPS  100    // Min profit (pts) before cascade
#define CBR_CASCADE_RISK_MULT 0.50   // Cascade uses 50% of base risk
#define CBR_CASCADE_MAX       2      // Max cascade entries per trade

#endif // CBR_CONFIG_MQH
