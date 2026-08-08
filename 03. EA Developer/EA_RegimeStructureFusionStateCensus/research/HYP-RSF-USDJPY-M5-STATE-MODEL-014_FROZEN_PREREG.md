# HYP-RSF-USDJPY-M5-STATE-MODEL-014 - frozen preregistration

Frozen before the USDJPY census or any USDJPY discovery-label calculation.

## Why this is a new object

STATE-MODEL-012 and STATE-TRANSITION-013 terminally rejected their exact
EURUSD M5 decision surfaces. They are not retuned. This ID performs a
cross-symbol falsification on USDJPY M5 because pair behavior, quote geometry,
spread in ATR units and active-session structure are different causal inputs.
It uses all five indicators: AIRD, VRC, MBB, TB SMC and QQE.

No hour/day filter from any older USDJPY strategy is imported. UTC hour and
weekday enter only as continuous cyclical features so each expanding-year
training fold can learn, and the next unseen year can falsify, timezone
dependence. A session can be promoted later only if the same fixed cell first
survives all discovery gates and the effect is stable across years.

## Stage A - one zero-trade census

- Symbol/timeframe: USDJPY M5.
- Discovery window: 2018-01-01 through 2022-12-31 only.
- Quote geometry: 3 digits, point 0.001, pip 0.01.
- Export one row per completed M5 bar after all five indicators are ready.
- MQL output contains current/older OHLC and shift-1-or-older indicator state;
  it contains no future price, label, chosen direction or trade.
- All entry and path-management modes are disabled. Expected orders/trades: 0.
- Exactly one Model-0 census attempt is authorized.

## Stage B - fixed pair-specific discovery

The candidate set remains six cells so the pair comparison is honest:

- horizons: 3, 6 and 12 completed M5 bars;
- models: Ridge regression and shallow HistGradientBoosting regression;
- target: signed next-open-to-horizon-close return divided by decision-bar TB
  ATR;
- features: the same five indicator families and causal UTC cyclical terms as
  STATE-MODEL-012;
- cost: observed USDJPY spread converted with point 0.001, stressed by
  `1.5 + 0.15 * (1 + VRC volatility percentile / 100)`;
- folds: train on prior calendar years, test the next year, with horizon purge
  and embargo;
- threshold: chosen on training data only to target 2-5 non-overlapping
  signals per elapsed calendar week.

No indicator family, direction, year, hour or weekday may be removed after
outcomes are seen. Missing/non-finite rows are rejected.

Discovery survival requires all of:

1. at least three yearly folds at 2-5 trades/week;
2. positive net return and PF > 1.0 in every cadence-valid fold;
3. median yearly PF >= 1.20 and pooled PF >= 1.20 after dynamic cost;
4. no year contributes more than 40% of positive gross return;
5. adjacent train-only cadence thresholds remain stable;
6. all six cells and every tested threshold count toward multiplicity.

If no cell survives, this exact USDJPY M5 state surface is terminal. It may not
be rescued by mining Tokyo/London/New York hours.

## Stage C - sealed

Only a discovery survivor may open one frozen 2023-2024 validation. The
2025-current holdout, EA trading implementation, optimization, paper, live and
promotion lanes remain sealed.

