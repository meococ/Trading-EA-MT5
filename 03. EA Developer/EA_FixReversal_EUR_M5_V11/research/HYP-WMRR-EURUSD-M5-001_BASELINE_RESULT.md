# Baseline result - HYP-WMRR-EURUSD-M5-001

Verdict: `KILL_NEGATIVE_FIX_REVERSAL_FULL_SAMPLE_NO_CONTROL_NO_OOS`.

AlphaFactory run `20260812_025214`, EURUSD M5 Model 0, current broker spread, HQ100, full 2018-2021 window. Engineering passed: fresh compile `0 errors, 0 warnings`, static contract `18/18`, `runtime_failed=false`, 298,084 completed closed bars, one documented bar-contiguity failure, no order rejection, no stop cancellation, and maximum observed margin usage about `2.072%`.

The independent FivePercent broker-clock preflight `HYP-FIXCLK-EURUSD-M5-001` passed the US-DST/NY-close convention. The EA therefore evaluated the London 16:00 fixing window at server hour 18 normally and hour 19 during the UK-US DST mismatch intervals. Runtime counted 967 server-18 fixing days and 70 server-19 fixing days, so this is not a clock-mapping failure.

The run completed without stop-out and produced 314 trades; net `-$5,912.55`; PF `0.7447`; WR `41.1%`; expectancy `-$18.83/trade`; max DD `7.6858%`. Runtime observed 944 usable fixing moves, 2,422 confirmation checks, 318 confirmations, 626 expiries, 318 signals, 314 entries, one spread cancellation, and three exposure cancellations. Entry cadence was 292 trades at server hour 18 and 22 at hour 19.

Exit forensics show 157 time stops (`+$3,464.91`, average `+$22.07`), 30 take-profits (`+$8,192.03`, average `+$273.07`), 79 stop-losses (`-$15,344.13`, average `-$194.23`), and 48 Friday flats (`-$363.52`, average `-$7.57`). Logged price/exit PnL is `-$4,050.71`; the report is another `-$1,861.84` lower, about `-$5.93/trade`. Average holding time was 13.17 M5 bars. Average fixing move was 7.2 pips and average retracement fraction was 0.8728, so the signal-strength gate fired as designed but selected a negative reversal distribution.

The equity chart is a near-monotonic multi-year lower-high/lower-low path, with the worst loss expansion in 2020 and only a minor late-2021 recovery. There is no durable recovery regime or economic reason to open control, optimization, OOS, or holdout work.

Kill this exact post-WMR fixing-reversal object. Do not rescue it by selecting the apparently favorable weekday, excluding server hour 18 or 19, altering the confirmation/retracement thresholds, or tuning stop/target/time exits from this readout.

Evidence hashes: source `CDE9870094D79FB029F01CF52482A78A0BA253654BCA1F3E36BA500CA39E276E`; EX5 `0267AA592DC74FB274A6B71BBC2D03D946C8271FCE219E37351E99EF1209358C`; report `F6B94E66B1AFAB89E4B17F04ACF68307FA94A058CE8E02788C998EEA8B4D7ADE`; journal `25B089B284ADE70A5B8DD62AE53871A52187342E2D9443E4DD9DC03DE71C8312`; chart `0F3265D5E8C6DF2FF2F22FA87BB7F27365FD9A7D78A05A6071C72B6CF5E9C7E3`.
