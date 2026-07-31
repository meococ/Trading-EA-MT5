# HYP-LVOR-EURUSD-M15-001 — Source Feasibility Plan

Status: `FROZEN_PRE_OUTCOME_SOURCE_ONLY`

## Identity and research boundary

- Hypothesis: `HYP-LVOR-EURUSD-M15-001`
- Parent candidate: none; this is a fresh mechanism and identity.
- Attempt: `LVOR001-SOURCE-ATTEMPT-001`, limit exactly one.
- Family: `liquidity-vacuum-overshoot-reversal`.
- Symbol/timeframe: FivePercent public DESIGN `EURUSD`; M15 decision bars,
  M5 confirmation and H1 BID volatility.
- DESIGN interval: `2016-01-04` through `2020-12-31` inclusive. Only public
  DESIGN shards may be opened. Validation, holdout, private and sealed paths
  remain forbidden.

This Stage-0 probe asks whether a low-activity, high-efficiency intraday price
overshoot followed immediately by rejection occurs often and broadly enough to
justify a separately preregistered economic test. It does not read future
prices, simulate a trade, calculate returns or authorize MQL5/MT5.

## Research basis and calibration limits

The mechanism is plausible but unvalidated. Berger et al. report that FX price
sensitivity can be highest in lower-volume conditions while leaving temporary
versus permanent impact ambiguous; Ito and Hashimoto support intraday/same-slot
seasonality; the BIS sterling flash-event study documents thin participation,
depth gaps, spread widening and partial retracement. Cont et al. tie short-run
price changes more directly to order-flow imbalance and depth, warning against
equating low volume with low liquidity. Hartmann also cautions that tick
frequency is a proxy, not transaction volume.

Primary references:

- https://www.federalreserve.gov/pubs/ifdp/2005/830/revision/ifdp830.htm
- https://www.nber.org/papers/w12413
- https://www.bis.org/publ/mktc09.pdf
- https://arxiv.org/abs/1011.6402
- https://eprints.lse.ac.uk/119148/1/dp265.pdf

Accordingly, FivePercent broker `tick_volume` is declared only as an activity
proxy. The exact `A <= 0.85`, range/ATR `0.50..1.25`, efficiency `>=0.70` and
outer-20% thresholds have no direct literature calibration; they are frozen
falsification priors chosen before the source read. A source PASS would prove
only adequate causal-source/cadence geometry under this proxy and cannot be
described as market edge, causality or profitability.

## Frozen causal mechanism

Every decision is UTC. Eligible M15 starts are Monday-Friday, `>=06:00` and
`<18:00`, at an exact quarter-hour. A decision M15 exists only when all 15
minute-aligned M1 rows are observed consecutively. Its confirmation is the
immediately following UTC-aligned M5 bin and exists only when all five M1 rows
are observed consecutively. The decision/availability timestamp is the close
of that confirmation M5. No incomplete bin or fallback is legal.

H1 volatility is Wilder ATR20 over exact public H1 BID bars. At a decision,
only the latest ATR whose H1 bar has already closed may be used; this is
closed shift-1 access with no lookahead.

For an eligible M15 at UTC slot `s` on business date `d`, activity is:

`A(d,s) = M15_tick_volume(d,s) / median(M15_tick_volume(d-20..d-1,s))`

The denominator uses exactly the same UTC slot on the previous 20 ordered
Monday-Friday manifest dates. The business-date sequence and `date -> ordinal`
mapping are immutable and precomputed once.

The frozen price/rejection surface requires all of:

1. `0.50 <= M15_range / H1_ATR20 <= 1.25`;
2. `abs(M15_close - M15_open) / M15_range >= 0.70`;
3. a bullish impulse closes in the upper outer 20%, or a bearish impulse in
   the lower outer 20%, of its M15 range;
4. the following M5 body is opposite the impulse and its close crosses beyond
   the midpoint of the M15 body.

PRIMARY additionally requires `A <= 0.85`. Direction is opposite the M15
impulse. Only the first qualifying PRIMARY candidate per UTC business date is
kept.

## Frozen diagnostic controls

- `PRICE_ONLY` removes only `A <= 0.85`; every price/rejection rule and its own
  first-per-date cap remains.
- `SHIFTED_ACTIVITY` applies to the current price/rejection surface the fully
  as-of activity ratio from the exact same UTC slot five ordered business dates
  earlier. That historical ratio was itself computed only from its own prior
  20 business dates. There is no fallback when it is unavailable. It has its
  own first-per-date cap.

Controls are diagnostic only. They cannot rescue a failed PRIMARY gate or
authorize economics.

## Frozen prospective risk and timestamp-only mapping

A future economic child, if separately authorized, must use actual future entry
with fixed SL exactly `1.0 * H1_ATR20`, risk `0.20%`, no TP, break-even,
trailing, partial exit or other management, and a time exit after six complete
observed M5 bars. This source stage never reads actual entry price or any
post-decision OHLC. Its cost-geometry proxy is frozen as
`1.50 pip / ATR20_pips`.

For source executability only, the ledger may map the first observed
minute-aligned M1 timestamp at or after decision/availability, with delay no
greater than 60 minutes, then the first six complete observed UTC-aligned M5
timestamps at or after that entry timestamp. The sixth close is timestamp-only
exit availability. The mapping contains no OHLC, return, PnL, win/loss, MFE,
MAE, target or stop field.

## Stage-0 gates

Only PRIMARY is judged. All gates must pass over exactly
`260.5714285714` elapsed calendar weeks:

- cadence inclusive `2.0..5.0` per elapsed week;
- LONG share and SHORT share each at least 25%, with at least 20 each;
- no calendar year contributes more than 30%;
- joint complete M15 plus immediately-following M5 formation ratio at least
  99% after the 20-date activity warmup;
- source-executable timestamp horizon ratio at least 99%;
- median `1.50 / ATR20_pips <= 0.25`.

All pass yields only `SOURCE_PASS_FUTURE_ECONOMICS_PREREG_ONLY`. Any failure
yields `SOURCE_FAIL_NO_ECONOMICS_AUTHORITY` and kills this exact hypothesis ID,
not the wider family. After the first source read there is no threshold,
session, direction, lookback, horizon, stop, cost or gate relaxation/tuning.

## Indexed implementation and authority

The production scan precomputes business dates/date ordinals, M15/M5 maps, H1
ATR availability, same-slot activity ratios, shifted activity ratios, observed
M1 timestamps and complete M5 starts once. Inner decision work is O(1) plus
bounded lookups. `Sequence.index` and a per-decision full scan/rebuild are
forbidden.

The exact latest canonical registry row for this ID is the sole future run
authority. Execution requires explicit run switch plus exact non-null
`REVIEWED_REGISTRY_ROW_SHA256`, normalized disarmed builder-base SHA, exact
plan/source/test/review-receipt bindings, exact latest raw registry-row SHA and
zero errors from the hash-bound canonical registry validator/schema before any
DESIGN metadata or shard opens.

- Builder: `03. EA Developer/EA_LiquidityVacuumOvershootReversal/research/build_lvor_001_source.py`
- Tests: `03. EA Developer/EA_LiquidityVacuumOvershootReversal/research/tests/test_build_lvor_001_source.py`
- Review receipt: `03. EA Developer/EA_LiquidityVacuumOvershootReversal/research/HYP-LVOR-EURUSD-M15-001_SOURCE_IMPLEMENTATION_REVIEW_RECEIPT.json`
- Evidence root: `03. EA Developer/EA_LiquidityVacuumOvershootReversal/research/evidence/HYP-LVOR-EURUSD-M15-001_SOURCE_FEASIBILITY_ATTEMPTS/LVOR001-SOURCE-ATTEMPT-001`

The builder sentinel remains exactly
`REVIEWED_REGISTRY_ROW_SHA256: str | None = None`. This implementation task
does not create the receipt, append registry authority, arm or run. Economics,
outcomes, performance metrics, validation/holdout/private/sealed access,
network/paid, charting, optimization, MQL5/MT5, promotion, paper and live
trading remain literal false.
