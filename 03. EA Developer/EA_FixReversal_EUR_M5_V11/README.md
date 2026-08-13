# EA_FixReversal_EUR_M5_V11

Active `HYP-WMRR-EURUSD-M5-001`: EURUSD M5 reversal after the LSEG WMR London 16:00 fixing window. The FivePercent clock mapping is hash-bound to the accepted `HYP-FIXCLK-EURUSD-M5-001` preflight: 18:00 server normally and 19:00 during UK-US DST mismatch intervals.

Baseline run `20260812_025214` completed the full 2018-2021 window at HQ100: 314 trades, PF `0.7447`, net `-$5,912.55`, expectancy `-$18.83/trade`, max DD `7.6858%`. Verdict: `KILL_NEGATIVE_FIX_REVERSAL_FULL_SAMPLE_NO_CONTROL_NO_OOS`. See `research/HYP-WMRR-EURUSD-M5-001_BASELINE_RESULT.md` and the machine-readable failure packet.
