# HYP-JCDR-EURUSD-M5-006 source-to-spec matrix

This matrix is a pre-outcome correctness checkpoint. It does not authorize an economic or promotion claim.

| Frozen requirement | MQL5 implementation | Focused evidence |
|---|---|---|
| Completed M5 bars only | `ProcessClosedBar()` reads OHLC at shift 1; shift 0 is scheduling only | `test_closed_bar_clock_and_gap_fail_closed` |
| Prior-48 median scale | `PriorMedianAbs48()` excludes the current return | exact constants/static source test |
| 15-bar coherent jump cluster | `TryFormCluster()` preserves HYP002 ordering and inclusive thresholds | parameter/boundary test |
| New cluster replaces pending | replacement branch returns before decay evaluation | replacement-order test |
| Three non-jumps plus 25%-100% retrace | `ThreeClosedBarsNoJump()` and `RetracementFraction()` | inclusive-boundary test |
| One decision per broker-server date | `DateKey(bar.time)` is consumed before execution gates | daily refractory test |
| Opposite-direction reversal | signal direction is negative dominant cluster sign | direction test |
| 6-pip/cluster stop and 1.5R target | outward tick normalization in `SubmitEntry()` | geometry test plus compile |
| 0.25% downward risk sizing | `OrderCalcProfit`, volume-step floor, margin and `OrderCheck` | risk/order fail-closed test |
| 12 completed-bar exit | `iBarShift` against position open time; retry on every tick | time-exit source test |
| One position, no partial/BE/trailing | owned position/order gates; full-volume close only | source scan |
| No weekend hold | Friday 20:00 broker-server flatten and weekend guard | design/weekend boundary test |
| No indicator router/session filter | no `iCustom`, `CopyBuffer`, AIRD/VRC/MBB/QQE/TB or intraday entry window | identity/source scan |
| Untuned baseline only | all strategy parameters are runtime-validated to exact prereg values | contract and frozen-input tests |

Economic truth begins only after an AlphaFactory Model-0 report passes engineering, cost and lifecycle checks.
