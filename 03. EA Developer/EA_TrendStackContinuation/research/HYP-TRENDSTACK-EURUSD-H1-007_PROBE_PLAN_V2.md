# HYP-TRENDSTACK-EURUSD-H1-007 - PROBE PLAN V2

Status: `FROZEN_IDEA_AMENDMENT_PRE_SOURCE_PRE_ECONOMICS`

This create-new amendment supersedes V1 SHA256
`8A3BB9AC6BCC015972856A9EA9882A6DA64D961C35FFE3936FBF2DC21D082603`.
V1 remains immutable evidence. Every V1 clause remains binding except where V2
explicitly replaces or narrows it. No HYP007 public shard, OHLC, return, PnL,
performance metric, VALIDATION, or HOLDOUT payload was opened before this V2
freeze.

## 1. Source contract replacement

Replace V1 source contract SHA256
`552C38E9F3DD8087C8D0A3F04F0780449D819799982FCDF961DF1356E4C4E39A`
with `HYP-TRENDSTACK-EURUSD-H1-007_SOURCE_PROJECTION_CONTRACT_V2.json`.

V1 incorrectly named two physical Arrow fields and conflated physical nullable
metadata with the semantic no-null rule. V2 fixes the exact field names, order,
types, physical nullable flags, semantic validation, machine-enforceable
allowlist, clock and per-shard hash rules, actor-scoped access counters, exact
output schemas, independent validation, and validate-before-publish lifecycle.
No rule is relaxed and no source access is authorized by this amendment.

## 2. ATR and engineering validity

The joined pre-decision `ATR20` must be a finite IEEE-754 value strictly greater
than zero. Entry, OHLC, stop, exit, gross R, stop pips, cost R, and net R must
all be finite; OHLC must be strictly positive and satisfy
`low <= open <= high` and `low <= close <= high`. Any violation is engineering
invalid with no economic verdict. No row may be dropped or repaired.

## 3. Exact PF and relative-PF statuses

For an arm and cost tier, let `gain = sum(max(net_R,0))` and
`loss = abs(sum(min(net_R,0)))` over the exact frozen arm rows:

- `loss > 0`: PF status `FINITE`, numeric value `gain / loss` (including zero).
- `loss == 0 and gain > 0`: PF status `NO_LOSS`, value `null`; this passes an
  absolute PF threshold.
- `loss == 0 and gain == 0`: PF status `NO_WIN_NO_LOSS`, value `null`; this
  fails every absolute and relative PF gate.

For a challenger-minus-comparator PF delta at the exact 1.50-pip tier:

- both `FINITE`: status `FINITE`, numeric challenger value minus comparator;
- challenger `NO_LOSS`, comparator `FINITE`: status `POSITIVE_INFINITY`, value
  `null`, and the relative threshold passes;
- challenger `FINITE`, comparator `NO_LOSS`: status `NEGATIVE_INFINITY`, value
  `null`, and the relative threshold fails;
- both `NO_LOSS`: status `ZERO_BOTH_NO_LOSS`, numeric value `0.0`, and a positive
  relative threshold fails;
- any side `NO_WIN_NO_LOSS`: status `UNDEFINED`, value `null`, and the relative
  threshold fails.

The better standalone comparator is chosen separately for PF and mean net R.
For PF, `NO_LOSS` ranks above every `FINITE` value; two `NO_LOSS` standalone
arms are tied; `NO_WIN_NO_LOSS` is not a valid comparator and causes the gate
to fail unless the other standalone has a defined status. Numeric NaN and
Infinity are forbidden in every JSON artifact.

## 4. Exact mean, total, yearly, cadence, and DSR semantics

- Mean net R is the arithmetic mean over every exact arm row. Total net R is
  the arithmetic sum. No missing or zero-filled trade row is legal.
- Yearly net R at 1.50 pips is the sum by decision-date year for exactly the
  five calendar years 2016, 2017, 2018, 2019, and 2020. A year is positive only
  when its finite sum is strictly greater than zero. At least four of five must
  be positive.
- STACK cadence is exactly `661 / 260.571428571` completed trades per elapsed
  calendar week after all count/source/join gates pass. Active-week, trading-
  week, or observed-week denominators are forbidden.
- DSR uses per-trade 1.50-pip net-R arrays, not a zero-filled daily book. For
  each of exactly four arms, sample Sharpe is arithmetic mean divided by sample
  standard deviation (`n-1` denominator); zero deviation yields Sharpe `0.0`.
  Trial variance is sample variance across the four arm Sharpes. Challenger
  skew and non-excess kurtosis use population central moments; zero second
  moment yields `(skew=0.0, kurtosis=3.0)`. Call canonical
  `02. AlphaFactory/tools/research/dsr.py` SHA256
  `A0659CDCDB2EAB4F29F69A1FBF4222FE3EC12467FE4CC664E194173126A4CEEA`
  with challenger Sharpe, `n_obs=661`, challenger skew/kurtosis, the four-arm
  Sharpe variance, and `n_trials=4`. A non-finite or out-of-range result is
  engineering invalid; DSR must be finite in `[0,1]`.

These clauses replace V1's inherited metric shorthand and its daily-book DSR
sentence. V1's four arms, exact counts, one-bar execution, cost tiers, twelve
numerical gates, high adverse prior, sequential authority, and no-rescue rules
remain unchanged.

