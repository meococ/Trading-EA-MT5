# HYP-RSF-USDJPY-M15-BARRIER-ACCEPTANCE-016 - frozen preregistration

Frozen before any first-hit label or outcome calculation.

## Mechanism and distinction

STATE-MODEL-014/015 proved that five-indicator fixed-horizon close regression
is not a net edge on USDJPY M5 or M15. This ID changes the target, not a
parameter. It asks whether a candidate direction reaches an ATR expansion
barrier before its symmetric ATR invalidation barrier within eight completed
M15 bars.

Every decision bar creates a long and short candidate from the same closed-bar
state. AIRD/VRC supply regime context, MBB supplies location/compression,
TB SMC supplies structural geometry, and QQE supplies momentum/timing. The
model receives the full state plus direction-conditioned alignment features;
the indicators are not counted as five votes.

## Bound data and labels

- Parent census: USDJPY M15 run `20260808_012351`, SHA256
  `1FFA026BF50C431C87EC9EC9CE5DD7D17ABB26DBDB179680B8E75C5421642D2A`.
- Discovery only: 2018-01-01 through 2022-12-31. 2023+ stays sealed.
- Decision uses shift-1-or-older state; theoretical entry is next M15 open.
- TB ATR at the decision bar freezes all barrier geometry.
- Maximum path is eight M15 bars (120 minutes).
- If target and stop occur inside the same M15 bar, stop wins conservatively.
- If neither barrier is hit, exit at the eighth-bar close.
- Dynamic cost is observed spread at point 0.001 times
  `1.5 + 0.15 * (1 + VRC volatility percentile / 100)` and is subtracted from
  every realized R outcome.

## Fixed six-cell discovery

Barrier cells are target/stop ATR = `0.75/1.00`, `1.00/1.00`, and
`1.25/1.00`, each with:

- standardized Logistic Regression (`C=0.1`); or
- shallow HistGradientBoosting classifier (7 leaves, 500 minimum samples,
  L2=10, 100 iterations).

The classifier target is `target hit first`. Train/test splitting is by whole
decision timestamp, so long/short twins never cross a fold boundary. For each
bar the higher long/short probability is the only eligible direction. A
train-only probability threshold targets 2.5, 3.5 or 4.5 non-overlapping
trades/week; the 3.5 path is primary and adjacent paths are stability checks.

Expanding-year folds train only on prior years and test 2019, 2020, 2021 and
2022 with an eight-bar purge/embargo. No indicator family, direction, year,
hour, weekday or barrier cell may be removed after outcomes.

## Gates

A cell survives only if all are true:

1. at least three yearly folds produce 2-5 trades/week;
2. every cadence-valid fold has net R > 0 and PF > 1.0;
3. median yearly PF >= 1.20 and pooled PF >= 1.20;
4. no year contributes more than 40% of positive gross return;
5. pooled PF at both adjacent train-only thresholds is > 1.05;
6. all six cells and 72 threshold-fold evaluations count toward multiplicity.

No survivor closes this barrier-acceptance surface. A survivor freezes one
cell; it does not authorize parameter tuning or trading implementation.

## Sealed validation

Only one frozen survivor may open 2023-2024 validation. The 2025-current
holdout, EA build, optimization, paper, live and promotion lanes remain sealed.
