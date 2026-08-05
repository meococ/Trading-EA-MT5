# AIRQMB EURUSD SCREEN-004 - Aborted Per-Tick Calculation Smoke

- Model/date cell: EURUSD M5, Model 4 (real ticks), `2023.01.02-2024.12.31`
- Stop: approximately 3 minutes, before report generation and before any performance outcome read
- Economic trials consumed: `0`

The parameterless `iCustom` repair passed: all three indicators initialized without `INIT_PARAMETERS_INCORRECT`. Runtime profiling then showed the remaining bottleneck was mathematical recalculation on every quote. The EA is closed-bar only, but MT5 still invoked AIRD percentile/HMM work, MBB percentile sorting and QQE updates on every real tick.

The successor adds a tester-only same-bar return path to each indicator. The first tick of every new bar still recalculates the just-closed bar from final OHLC, so all buffers read by the EA at shift 1/2 remain identical. Live indicator behavior is unchanged. SCREEN-004 is superseded across all nine cells with no report and no economic verdict.
