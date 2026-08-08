# HYP-RSF-USDJPY-M15-STATE-MODEL-015 - frozen preregistration

Frozen before any USDJPY M15 census or outcome calculation.

## New causal object

USDJPY M5 STATE-MODEL-014 had gross PF 1.3276 but no net edge because dynamic
friction exceeded the gross return. This ID does not filter or retune that M5
book. It recomputes AIRD, VRC, MBB, TB SMC and QQE natively on M15, changing
their warm-up, state transitions, structural geometry and spread/ATR ratio.
M15 state cannot be reconstructed by aggregating the M5 census.

Workspace evidence predating this ID also identifies M15 as the minimum useful
regime resolution for USDJPY, while M5 variants were degraded by noise. No
profitable hour/day window or parameter from those older strategies is copied.

## Stage A - one zero-trade census

- Symbol/timeframe: USDJPY M15.
- Discovery window: 2018-01-01 through 2022-12-31 only.
- Quote geometry: 3 digits, point 0.001, pip 0.01.
- One row per completed M15 bar after all five indicators are ready.
- Every indicator read is shift 1 or older. Output contains no future price,
  label, direction selection or trade.
- All entry, sequence and path-management routes are disabled.
- Exactly one Model-0 census attempt; expected orders/trades: zero.

## Stage B - fixed M15 discovery

Six cells are fixed before data:

- horizons: 2, 4 and 8 completed M15 bars (30, 60 and 120 minutes);
- models: Ridge regression and shallow HistGradientBoosting regression;
- target: signed next-open-to-horizon-close return divided by decision-bar TB
  ATR;
- features: all five indicator families plus causal UTC hour/weekday cyclical
  terms; no discrete session/day filter;
- cost: observed USDJPY spread at point 0.001 times
  `1.5 + 0.15 * (1 + VRC volatility percentile / 100)`;
- folds: prior calendar years train, next year tests, with horizon purge and
  embargo;
- threshold: train-only targeting 2-5 non-overlapping trades per elapsed week.

No family, direction, year, hour or weekday may be removed. Discovery survival
requires all of:

1. at least three yearly folds at 2-5 trades/week;
2. positive net return and PF > 1.0 in every cadence-valid fold;
3. median yearly PF >= 1.20 and pooled PF >= 1.20 after dynamic cost;
4. no year supplies more than 40% of positive gross return;
5. adjacent train-only cadence thresholds both remain above PF 1.05;
6. all six cells and every threshold are counted in multiplicity.

No survivor means this exact M15 state-regression surface is terminal; no
session rescue is allowed.

## Stage C - sealed

Only one frozen discovery survivor may open 2023-2024 validation. The
2025-current holdout, trading EA implementation, optimization, paper, live and
promotion lanes remain sealed.

