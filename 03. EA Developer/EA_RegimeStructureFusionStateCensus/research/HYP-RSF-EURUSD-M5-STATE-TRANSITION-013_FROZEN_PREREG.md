# HYP-RSF-EURUSD-M5-STATE-TRANSITION-013 — frozen preregistration

Frozen after STATE-MODEL-012 was closed and before any transition-model outcome
was calculated. It reuses the same 2018–2022 Model-0 census and does not open
2023+.

## New causal object

STATE-MODEL-012 rejected simultaneous indicator levels. This hypothesis tests
whether information exists only when an indicator changes state. The event
clock is the union of all five families, fixed before outcomes:

- AIRD: held regime changes;
- VRC: regime changes;
- MBB: release or any S1/S2/S3 event is present;
- TB SMC: structure, displacement or sweep event, or bias/cell/void side changes;
- QQE: state change or primary/secondary zero crossing.

No event family may be removed after results are seen.

## Features and labels

Use the STATE-MODEL-012 level features plus fixed one-bar and three-bar changes
for AIRD posterior/confidence, VRC direction/volatility, MBB location/squeeze,
TB bias/normalized geometry and QQE level/slope. Add capped bars-since-event
ages for AIRD, VRC, MBB, TB and QQE. Current and older bars only.

The six fixed cells remain Ridge and shallow HistGradientBoosting at 3, 6 and
12 completed M5 bars. Expanding-year walk-forward folds test 2019, 2020, 2021
and 2022. The train-only score threshold targets 2.5/3.5/4.5 non-overlapping
signals per elapsed week. Costs remain:

`observed spread * (1.5 + 0.15 * (1 + VRC volatility percentile / 100))`.

## Survival gates

At the 3.5 target cadence:

1. at least three yearly folds must achieve 2–5 trades/week;
2. every cadence-valid fold must have positive net R and PF > 1.0;
3. median yearly PF and pooled PF must each be >= 1.20;
4. no year may exceed 40% of positive gross return;
5. the adjacent 2.5 and 4.5 cadence surfaces must each have pooled PF > 1.05.

All six new model cells, 24 model fits and 72 threshold-fold evaluations count
toward trial debt. Cumulative campaign debt after this test is 12 model cells,
48 fits and 144 threshold-fold evaluations.

No threshold/session/year/direction rescue, no MT5 strategy build and no
2023+ validation are authorized unless a cell passes every gate.

