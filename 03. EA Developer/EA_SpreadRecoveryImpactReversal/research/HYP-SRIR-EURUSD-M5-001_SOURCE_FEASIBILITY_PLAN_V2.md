# HYP-SRIR-EURUSD-M5-001 — Source-Feasibility Plan V2

Status: `FROZEN_PRE_OUTCOME_SOURCE_CONTRACT_V2`

V2 supersedes V1 before any Parquet payload, spread value, signal count or
outcome was opened. Public manifest scheduling metadata showed partial Sunday
shards, so V1's baseline set of every manifest date would be structurally
unavailable in the Monday-Friday decision domain. V2 changes only the baseline
calendar set and its burn-in label: prior eligible Monday-Friday manifest dates
replace prior manifest dates. Every market threshold, gate and prohibition is
unchanged.

## 1. Identity and purpose

- Hypothesis: `HYP-SRIR-EURUSD-M5-001`
- Package: `EA_SpreadRecoveryImpactReversal`
- Feature family: `bar-spread-shock-recovery-price-impact-reversal`
- Symbol / decision timeframe: `EURUSD / M5`
- DESIGN window: `2016-01-04` through `2020-12-31`, public FivePercent
  splitvault_002 only.
- First task: one outcome-blind source-feasibility attempt. No return, trade,
  post-entry price, economics, validation, holdout, MQL5 or MT5 access.

The market thesis is that a transient liquidity withdrawal can widen the
reported spread while price moves directionally. If the reported spread then
normalizes promptly and the completed price bar starts retracing without making
a new shock extreme, part of the price impact may reflect temporary inventory
or liquidity pressure rather than permanent information. TRUE fades the shock;
a timestamp-matched FOLLOW_CONTROL continues it.

This is a falsifiable measurement prior, not a profitability claim. BIS work on
FX order flow and dealer inventory distinguishes transitory inventory/liquidity
effects from permanent information effects and links wider spreads to inventory
and volatility risk. MQL5 exposes historical bar spread in points via MqlRates,
CopyRates and iSpread. These references justify measuring spread state only:

- https://www.bis.org/publ/bppdf/bispap52.pdf?noframes=1
- https://www.bis.org/publ/work93.htm
- https://www.bis.org/publ/qtrpdf/r_qt1503y.htm
- https://www.mql5.com/en/docs/series/ispread
- https://www.mql5.com/en/docs/matrix/matrix_initialization/matrix_copyrates

## 2. Material information delta and de-dup

- Unlike LVOR, this object does not use low tick activity, outer-close
  efficiency or a fixed five-M1 counter-body confirmation. Its primary state is
  a same-slot historical spread shock followed by spread normalization.
- Unlike QuoteTickAcceptance / VRAS, it does not use forward quote imbalance,
  VWAP reclaim or online tick acceptance. It uses only completed historical M1
  bar spread and OHLC aggregated into exact UTC M5 blocks.
- Unlike VCEX, it does not use tick-volume half-mass timing or early/late
  volume-clock exhaustion.
- Unlike JCDR, it does not use standardized M1 jump arrival clusters or a
  post-cluster no-jump state.
- Unlike ARUC and DFR, it has no tick-activity rank, response ratio or diurnal
  price residual.

The new decision surface is the joint transition `spread shock + directional
price impact -> spread recovery + partial price retracement`.

## 3. Immutable data bindings

- Manifest:
  `02. AlphaFactory/data/fivepercent/EURUSD/splitvault_002/public/design_manifest.jsonl`
  SHA-256 `A8A091DA8365602CB1D02BA571E96B4FB00B50621A73166B8CEDDBC1A7EED8C7`.
- Receipt:
  `02. AlphaFactory/data/fivepercent/EURUSD/splitvault_002/public/design_receipt.json`
  SHA-256 `8109B11B6054517B9904FB4ACEF25EB7C6BD2485487CA9D69340DDC7E7D27FF8`.
- Public M1 source SHA-256:
  `2959C555DB6690FD6EFD6CFB3B4C6323698E590C9B2D71E1E55F1902F724235A`.
- Price side: BID producer OHLC. Allowed source features are timestamp, OHLC
  and the producer `spread` field only. `tick_volume`, `real_volume` and every
  post-decision price are forbidden.
- Source point is `0.00001`; one pip is `0.0001`. One producer spread point is
  therefore `0.1` pip. Spread is a signal-state measurement here, not accepted
  execution-cost truth.
- Private, validation and holdout paths are forbidden. Every opened shard must
  be the exact manifest-bound regular, single-link public DESIGN file.

## 4. Exact UTC M5 construction and frozen baselines

All timestamps are UTC. A completed M5 block contains exactly the five
minute-aligned M1 rows at offsets 0 through 4 from its M5 open. Missing,
duplicate, non-minute-aligned or non-contiguous M1 rows make that block
incomplete and reset causal formation state.

For every complete M5 block:

1. `open`, `high`, `low` and `close` are the standard aggregation of its five
   completed BID M1 bars.
2. `block_spread_points` is the maximum finite producer spread value across the
   same five M1 rows. Any non-finite or non-positive component makes spread
   unavailable for that block.
3. `TR` is the standard true range using the previous contiguous completed M5
   close. Wilder ATR20 is updated only across contiguous completed M5 blocks.
   Shock block `t` uses the closed ATR value at `t-1`; current TR is excluded.
4. Eligible baseline dates are the exact chronologically ordered Monday-through-
   Friday dates in the bound manifest. Sunday and Saturday shards are never in
   the baseline calendar. The first 20 eligible baseline dates are immutable
   burn-in and are excluded from every formation, spread-availability and
   cadence numerator; the full DESIGN elapsed-week cadence denominator remains
   unchanged.
5. For eligible source date `d` and exact UTC M5 slot `s`, the frozen baseline
   is the median of `block_spread_points` for slot `s` on exactly the prior 20
   eligible Monday-through-Friday manifest dates. Current-date, weekend and
   future values are excluded. If any of those 20 prior eligible-date blocks is
   incomplete or spread-unavailable, the baseline is unavailable; it is never
   filled from an older or later date.

The shock scan domain is Monday through Friday and exact M5 opens from `07:00`
through `15:40` UTC inclusive after the 20-eligible-date burn-in. The latest
three-bar recovery therefore closes no later than `16:00` UTC.

## 5. Closed-bar shock and recovery state machine

All comparisons are finite-only with four-ULP inclusive boundary tolerance.

A completed scan-domain M5 bar `t` is a qualifying shock only when all are true:

1. Its frozen same-slot baseline is available and strictly positive.
2. `block_spread_points_t >= 2.0 * baseline_t`.
3. `block_spread_points_t - baseline_t >= 5` producer points (`0.5` pip).
4. Absolute body is at least `max(4.0 pips, 0.50 * ATR20_{t-1})`.
5. Bar range is positive and `abs(body) / range >= 0.65`.
6. An up shock closes in the upper 20% of its range; a down shock closes in the
   lower 20%. Shock sign is the sign of `close - open`.

After a shock, inspect only the next three exact contiguous completed M5 blocks.
The first block `r` is a recovery decision only when all are true:

1. `block_spread_points_r <= 1.25 * baseline_t`, using the shock's frozen
   same-slot baseline rather than a newly selected threshold.
2. The recovery body is non-zero and opposite the shock sign.
3. For an up shock, `close_r <= close_t - 0.25 * abs(close_t-open_t)`; for a
   down shock, `close_r >= close_t + 0.25 * abs(close_t-open_t)`.
4. No M5 block from `t+1` through `r` makes a new shock-direction extreme: all
   highs are at most `high_t` after an up shock and all lows are at least
   `low_t` after a down shock.

A new qualifying shock before recovery cancels and replaces the pending shock.
A gap, incomplete M5 block, unavailable recovery spread, or expiry after three
blocks cancels it. No overlapping pending candidate survives. The first
qualifying recovery decision per UTC date is selected; later ones are classified
`DAILY_REFRACTORY` and cannot reserve a horizon.

TRUE direction is opposite the shock sign. `FOLLOW_CONTROL` direction follows
the shock sign. Both arms use the identical signal ID, decision timestamp,
entry timestamp, 60-minute source horizon and planned stop distance.

## 6. Source-only entry, horizon and risk geometry

- Entry timestamp is exactly the next contiguous observed M1 open after the
  completed recovery M5 close. Source feasibility may use its timestamp, never
  its OHLC.
- Required source horizon is exactly 60 contiguous observed M1 timestamps from
  entry inclusive to exit exclusive. Missing or incomplete horizons are
  classified before any ledger arm is emitted.
- For an up shock / TRUE short, planned stop distance is
  `max(6.0 pips, (shock_high - recovery_close)/0.0001 + 0.50 pips)`.
- For a down shock / TRUE long, planned stop distance is
  `max(6.0 pips, (recovery_close - shock_low)/0.0001 + 0.50 pips)`.
- Future economic geometry, if separately authorized, is a 1R target and a
  60-minute time exit with `1.50 / 2.25 / 3.00`-pip round-turn cost tiers. This
  plan does not compute those outcomes.
- Source cost geometry uses only `1.50 / planned_stop_distance_pips`. Historical
  spread values are not substituted for execution cost.

## 7. One-shot source gates

All gates are fatal and frozen before any source count or spread value is
opened. Formation and spread gates are assessed only on the post-burn-in scan
domain declared in Section 4.

1. Outcome-blind plane intact: zero post-decision OHLC reads, returns, trades,
   economic metrics, validation, holdout, MQL5, MT5, network or paid requests.
2. Exact TRUE/FOLLOW_CONTROL one-to-one match on every executable signal.
3. Positive finite M1 spread ratio at least `0.99` in the observed post-burn-in
   scan-and-recovery domain.
4. Exact scheduled M1 formation completeness at least `0.99` in that domain.
5. Frozen prior-20-eligible-date baseline availability at least `0.99` among complete
   scan-domain M5 blocks.
6. Source-executable 60-minute horizon ratio at least `0.99`.
7. TRUE cadence between `2.0` and `5.0` per elapsed calendar week.
8. TRUE long share at least `0.25`.
9. TRUE short share at least `0.25`.
10. Maximum calendar-year share at most `0.35`.
11. At least 20 executable TRUE signals per direction.
12. Median planned stop distance at least `6.0` pips.
13. Median `1.50-pip / stop` ratio at most `0.25`.

Elapsed weeks are `(2020-12-31 - 2016-01-04).days / 7`; active weeks are
forbidden as denominator. The 20-eligible-date burn-in prevents structural warm-up from
deciding the completeness denominator but does not shorten the cadence
denominator.

PASS verdict: `PASS_SOURCE_FEASIBILITY_FUTURE_ECONOMICS_PREREG_ONLY`.

FAIL verdict: `SOURCE_FAIL_NO_ECONOMICS_AUTHORITY`.

Engineering/data failures are `ENGINEERING_INVALID_NO_MARKET_VERDICT` and do
not count as market evidence.

## 8. Attempt and evidence contract

- Attempt ID: `SRIR001-SOURCE-001`.
- Evidence root:
  `03. EA Developer/EA_SpreadRecoveryImpactReversal/research/evidence/HYP-SRIR-EURUSD-M5-001_SOURCE_FEASIBILITY/SRIR001-SOURCE-001`.
- Attempt limit: one. Evidence root must not exist before the authorized run.
- Required terminal chain: `attempt_started.json`, source classifications,
  matched source ledger, compact source report, non-terminal receipt and
  `attempt_terminal.json` as sole authoritative completion.
- Import must be inert. Production requires an exact reviewed registry-row hash
  burned into one sentinel and an explicit CLI flag. The sentinel is disarmed
  immediately after the single attempt and before interpretation.
- A separate deterministic replay must reconstruct classifications and the
  canonical ledger digest without reusing staged classification or ledger rows.

## 9. Forbidden rescue and authority

After any valid source result, do not change baseline lookback or estimator,
burn-in or denominator, shock ratio/point/body/ATR/efficiency/outer-close rules,
scan hours, recovery window/ratio/retracement/extreme rule, daily refractory,
horizon, stop, direction, year or gate based on the readout. Do not promote
FOLLOW_CONTROL, a subgroup, a different spread aggregation or a shifted
timestamp. Any material successor needs a fresh mechanism/ID/preregistration.

This plan grants no source run by itself and grants no economics, validation,
holdout, private, MQL5, MT5, optimization, promotion, paper or live authority.

