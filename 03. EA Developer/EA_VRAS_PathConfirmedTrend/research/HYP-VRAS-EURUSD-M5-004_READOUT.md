# HYP-004 matched-pair readout

Verdict: **KILL_PATH_CONFIRMATION_NO_INDEPENDENT_EDGE**.

| Metric | Control | Challenger | Frozen gate |
|---|---:|---:|---:|
| Trades | 261 | 252 | >=350 |
| Trades / elapsed week | 1.434 | 1.385 | 2.0-5.0 |
| Profit factor | 0.8927 | 0.8996 | >=1.30 |
| Net USD | -3429.27 | -2677.24 | positive |
| Mean realized R | -0.0487 | -0.0422 | lift >=0.10R |
| Stop-exit share | 48.66% | 40.08% | reduction >=10pp |
| Max DD | 5.96% | 4.49% | <=6% |
| Cost x1.5 PF proxy | 0.7662 | 0.7547 | >=1.25 |
| Cost x2 PF proxy | 0.6598 | 0.6352 | >=1.00 |

The treatment armed 1940 raw Trend candidates,
passed 639 (32.94%),
and opened 224 Trend positions
(11.55% raw-to-open). It reduced
drawdown and dollar loss, but PF lift was only 0.0069,
mean-R lift +0.0065R, and stop-share reduction
+8.58pp. All three relative gates failed.

The challenger also failed the necessary absolute trade-count, cadence, PF,
expectancy, cost-stress and Monte-Carlo P95 DD gates. Robustness passed
1/7;
diagnostic fixed-parameter OOS slices were profitable in
1/5 windows.

Control report/lifecycle reconciliation: PASS_EXACT.
Challenger report/lifecycle reconciliation: PASS_EXACT.
Both arms remain diagnostic-only because news, cost and independent execution
provenance are not promotion-grade.

## Chart evidence

- `research/evidence/HYP-VRAS-EURUSD-M5-004_DELIVERY_ASOF/cases_manifest.json`:
  four decision-time images with future and outcome hidden.
- `research/evidence/HYP-VRAS-EURUSD-M5-004_DELIVERY_ANATOMY/cases_manifest.json`:
  the same two wins and two losses with entry/SL/TP/exit and M15 context.
- `research/evidence/HYP-VRAS-EURUSD-M5-004_CHARTS/indicator_rich_casebook_manifest.json`:
  one accepted path trade and one rejected path candidate with the full active
  VWAP/SD, AVWAP, ADX14, ATR14, RSI14 and M15 bias surface.

Both indicator-rich exact decision snapshots pass 9/9 reconstruction parity
against MT5 telemetry. The rejected case receives no counterfactual PnL; all
post-decision regions are labeled outcome-aware anatomy.
