# PROBE_PLAN — HYP-VRAS-EURUSD-M5-004

Frozen before source creation and before any 2023+ HYP-004 outcome.

## Object

- EA: `EA_VRAS_PathConfirmedTrend`
- Symbol/timeframe/model: `EURUSD / M5 / Model 0`
- Window: `2023.01.03–2026.06.30`
- Pair order: control first, challenger second, serial under the global MT5 lane
- Economic sample: executed positions only; rejects never receive counterfactual PnL

## Arm difference

| Arm | Variant | Path confirmation |
|---|---|---|
| Control | `CONTROL_IMMEDIATE_TREND` | false |
| Challenger | `CHALLENGER_PATH_CONFIRM` | true |

All other overrides are byte-for-byte identical except the variant label.

## Required evidence

Source/EX5/compile hashes, pytest receipt, non-repaint receipt, run manifests,
tester reports, lifecycle/RunMeta/decision telemetry, report↔lifecycle
reconciliation, elapsed-week cadence, branch/direction/exit buckets, cost and
execution limitations, robustness/equity/Monte-Carlo outputs when sample size
permits, and indicator-rich chart anatomy for accepted/rejected path cases.

## Terminal routing

- Engineering mismatch or identity failure: `PARK_INVALID_ENGINEERING`.
- Valid pair but any necessary absolute or relative gate fails:
  `KILL_PATH_CONFIRMATION_NO_INDEPENDENT_EDGE`.
- All gates pass: `SCREENED_REQUIRES_VERIFIED_COST_AND_INDEPENDENT_CONFIRMATION`;
  never promotion/live because news and cost provenance are unverified.
