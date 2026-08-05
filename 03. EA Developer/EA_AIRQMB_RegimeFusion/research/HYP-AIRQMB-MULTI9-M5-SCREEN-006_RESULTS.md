# AIRQMB Multi-9 M5 SCREEN-006 - Real-Tick Results

All nine independent cells compiled and produced reconciled lifecycle-v3 reports on the frozen setup. No symbol reached the preregistered PF/expectancy/DD screen; therefore the per-symbol parameter grid remained locked.

| Symbol | Trades | Trades/wk | PF | Net USD | Exp/trade | DD % | Win % | Screen |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| EURUSD | 416 | 3.99 | 0.951 | -2976.87 | -7.16 | 8.03 | 42.1 | KILL |
| USDJPY | 282 | 2.71 | 0.826 | -7277.69 | -25.81 | 7.91 | 39.4 | KILL |
| GBPUSD | 540 | 5.19 | 0.966 | -2592.49 | -4.80 | 8.20 | 43.0 | KILL |
| USDCHF | 259 | 2.49 | 0.810 | -7304.62 | -28.20 | 8.10 | 38.2 | KILL |
| USDCAD | 295 | 2.83 | 0.886 | -4980.09 | -16.88 | 8.04 | 41.4 | KILL |
| AUDUSD | 231 | 2.22 | 0.778 | -7708.63 | -33.37 | 8.13 | 38.5 | KILL |
| NZDUSD | 117 | 1.12 | 0.637 | -6593.51 | -56.35 | 8.05 | 35.9 | KILL |
| XAUUSD | 227 | 2.18 | 0.832 | -5505.36 | -24.25 | 8.06 | 35.7 | KILL |
| BTCUSD | 109 | 1.05 | 0.559 | -7673.33 | -70.40 | 8.02 | 33.9 | KILL |

## Failure radius by semantic lane

| Lane | Trades | PF | Net USD | Win % |
|---|---:|---:|---:|---:|
| S1_RANGE_LONG | 42 | 0.518 | -3790.52 | 28.6 |
| S1_RANGE_SHORT | 53 | 0.643 | -3254.00 | 34.0 |
| S2_TREND_LONG | 1100 | 0.875 | -19658.88 | 40.4 |
| S2_TREND_SHORT | 1193 | 0.860 | -24432.85 | 40.2 |
| S3_BREAKOUT_LONG | 39 | 0.956 | -266.21 | 41.0 |
| S3_BREAKOUT_SHORT | 49 | 0.847 | -1210.13 | 38.8 |

## Decision

`KILL_NO_SCREEN_SURVIVORS_NO_PARAMETER_GRID`

The failure is broad, not isolated to one pair or one semantic branch: aggregate S1 range-fade, S2 trend-continuation and S3 squeeze-breakout lanes are all below PF 1.0. Every symbol reached or approached the 8% account lock during 2023 and then stopped taking risk. Confidence/RR grid search is not authorized because it would optimize a losing mechanism after observing the outcome.

Engineering status is PASS (0/0 compile, indicator initialization, OrderCheck/OrderSend, final-close reconciliation). Economic status is FAIL. Promotion-ready is FAIL. The reusable asset is the one-file EA/risk/lifecycle integration; any trading retry requires a fresh mechanism and hypothesis ID.
