# HYP-SR-FX-CROSS-SECTIONAL-USD-FACTOR-001 Preregistration

Date: 2026-07-11

State: `IDEA / COST-DATA BLOCKED`

This is an offline synchronized-M15 probe only. It does not authorize an EA
source patch, compile, MT5 backtest, demo, prop, or live execution.

## Identity And Thesis

- Hypothesis ID: `HYP-SR-FX-CROSS-SECTIONAL-USD-FACTOR-001`
- Feature family: contemporaneous common-USD regime, strongest-pair routing,
  and fixed pullback continuation.
- Universe: unsuffixed `EURUSD`, `GBPUSD`, and `USDJPY` only.
- Train half-open UTC window: `[2021-01-01T00:00:00Z, 2024-01-01T00:00:00Z)`
  (`1095` elapsed calendar days).
- One-time holdout half-open UTC window:
  `[2024-01-01T00:00:00Z, 2026-01-01T00:00:00Z)` (`731` elapsed calendar
  days).
- Source provenance: local de-duplication against the canonical Sonic registry
  and `STRATEGY_LOG.md` S555, S618, and S670.

The thesis is that a synchronous common-USD regime may be tradable through the
pair already expressing that regime most strongly, but only after that pair
completes its own closed-M15 pullback-break. This is not predictive lead-lag:

- every constituent ends at the same completed M15 timestamp;
- the traded pair participates in the factor;
- the traded pair must already be the strongest aligned pair;
- entry waits for that pair's own confirmation;
- no condition assumes that an unconfirmed pair will catch up.

`AUDUSD` is excluded because it was not verified in the current data preflight.
Adding any symbol requires a new hypothesis.

## Locked Data Contract

- Use same-broker historical quote ticks containing both bid and ask for all
  symbols. Aggregate M15 bid and ask OHLC deterministically from those ticks;
  a scalar M15 spread field is not sufficient for barrier outcomes.
- A timestamp is eligible only when all three symbols have exactly the same
  completed-bar timestamp.
- No forward fill, stale substitution, mixed broker, suffix substitution, or
  bar-zero read is allowed.
- Require at least `99%` synchronized completed-M15 coverage separately in
  train and holdout.
- Freeze eligible episode IDs from bid-side signal data before any outcome is
  read. Every eligible episode must then have a complete bid/ask tick path from
  all required lookback bars through its forced-exit bar. If any eligible
  episode lacks a required quote or cost observation, invalidate the entire
  train or holdout split; never delete that episode and continue on the rest.
- Calculate factor, ATR, ranking, pullback, and breakout values from completed
  bars only.

## Exact Factor

For pair `i` at completed bar `t`, define orientation:

```text
s_EURUSD = -1
s_GBPUSD = -1
s_USDJPY = +1
```

The signed volatility-normalized USD move is:

```text
u_i,t = s_i * ln(C_i,t / C_i,t-4) / (ATR14_i,t / C_i,t)
```

`ATR14` is standard Wilder ATR from completed M15 bars. Positive `u` means USD
strength and negative `u` means USD weakness.

```text
F_t = median(u_EURUSD,t, u_GBPUSD,t, u_USDJPY,t)
```

The frozen factor threshold is `theta = 0.50`. An episode starts only when
`abs(F_t) >= 0.50` and either `abs(F_{t-1}) < 0.50` or
`sign(F_t) != sign(F_{t-1})`. Direction `D = sign(F_t)`, where `+1` is USD
strength. A zero previous factor has sign `0`, so a zero-to-nonzero transition
qualifies through the explicit sign-change clause.

## Pair Ranking

At episode start `t0`:

```text
score_i,t0 = D * u_i,t0
```

Rank descending and freeze the highest-scoring pair for the full episode.
Exact numerical ties use `EURUSD`, `GBPUSD`, `USDJPY` order. Desired pair-price
direction is `P_i = s_i * D`, where `+1` means long and `-1` means short. No
re-ranking is allowed after episode start.

## Episode Arbitration And Cooldown

Each of the challenger, S555, S618, and S670 is evaluated as an independent
state machine; positions or arms in one role never suppress another role.

For the challenger, define `active_t = (abs(F_t) >= 0.50)`. A raw episode event
exists when `active_t` and either `active_{t-1}` is false or
`sign(F_t) != sign(F_{t-1})`. Accept that event only while the challenger state
is idle. Once accepted, freeze `t0`, `D`, and the target pair until its arm
expires or its trade exits. Any threshold or sign event arriving while the arm
or trade is active is ignored and never replayed later.

After an accepted episode ends, enter cooldown. Cooldown ends only after one
completed bar with `abs(F_t) < 0.50`; a still-active factor cannot immediately
start another episode. At the beginning of each split, the state is idle and a
raw event is accepted only if the preceding completed bar is present and
inactive. The controls use the same idle/active/cooldown rules with their own
conditions defined below.

## Fixed Pullback-Break And Outcome Rule

1. Search only the next four completed M15 bars after `t0`.
2. The first bar `p` satisfying
   `P_i * (C_i,p - C_i,p-1) < 0` is the single pullback bar.
3. Only `b = p + 1` may trigger: long when `C_i,b > H_i,p`; short when
   `C_i,b < L_i,p`.
4. At `b`, require `D * F_b >= 0.50`.
5. Bar `b` is a completed signal bar only. Its close and `F_b` may not be used
   as a fill. Enter on the first valid quote tick `e` in the immediate next M15
   bucket after `b` closes; long uses stressed ask at `e`, short uses bid at
   `e`. If that next bucket has no valid tick, invalidate the split rather than
   filling at the historical close or silently deleting the episode.
6. Expire if no pullback appears within four bars, the next bar does not break
   the pullback extreme, or the factor loses sign/threshold.
7. Allow one basket position and one trade per episode.

Outcome model:

- MT5/CSV bar timestamps are UTC bar-open timestamps and each M15 bucket is the
  half-open interval `[open, open + 15 minutes)`. The entry timestamp and entry
  UTC date come from actual execution tick `e`, never from `timestamp_b`;
- for each quote tick `j`, require `ask_j >= bid_j` and define observed spread
  `spread_j = ask_j - bid_j`. For each multiplier `x`, construct the stressed
  ask tick `ask_j^(x) = bid_j + x * spread_j`, then aggregate those stressed
  ticks into M15 ask open/high/low/close. At `x=1`, this is the actual historical
  ask path, not a bar-level synthetic approximation. Bind the tick source plus
  per-symbol `digits`, `point`, and `pip_size` in the cost manifest;
- long entry is `ask_e^(x)`, long stop is `bid_low_p`, and long target is
  `entry + 1.5 * (entry - stop)`. Long stop/target/time exits execute on bid;
- short entry is `bid_e`, short stop is `ask_high_p^(x)`, and short target
  is `entry - 1.5 * (stop - entry)`. Short stop/target/time exits execute on
  ask. Any non-positive initial risk indicates a data/implementation
  inconsistency and invalidates the entire split; it may not be deleted as one
  episode;
- start outcome evaluation at the first valid quote tick strictly after `e`.
  Process quote ticks in the frozen order below. Long stop triggers when bid is
  at/below stop and target when bid is at/above target; short stop triggers when
  stressed ask is at/above stop and target when stressed ask is at/below target.
  If both predicates are true on one tick, score stop first. A stop exits at the
  triggering executable quote; a target exits at the fixed target price;
- define the horizon cutoff as the end of the eighth complete M15 bucket after
  `b`, and the day cutoff as the next `00:00:00Z` after execution tick `e`.
  If no barrier fires, exit on the last valid quote tick strictly before the
  earlier cutoff, using bid for a long and stressed ask for a short. No such
  post-entry quote invalidates the split as incomplete data;
- define `GrossR_x` from the executable entry and exit prices divided by that
  multiplier's executable initial-risk distance;
- no break-even, trail, partial, scale-in, DCA, averaging, or management change.

### Tick Ordering And Aggregation

- Parse timestamps as UTC integer milliseconds and assign ticks to half-open
  M15 buckets `[k, k + 900000)` anchored at Unix epoch multiples of `900000`.
- Reject the split on a non-finite/non-positive bid or ask, `ask < bid`, a
  timestamp outside the declared window, or a source row that cannot be parsed.
- Preserve the hashed source row index and stable-sort by
  `(time_msc, source_row_index)`. Exact duplicate rows may be de-duplicated only
  before hashing; equal timestamps with different quotes remain in source order.
- For bid or stressed ask, open is the first tick, high/low are extrema, and
  close is the last tick in the bucket. Never forward-fill, interpolate, or
  carry a prior quote into an empty bucket.
- Signal calculations use only completed bid buckets. Outcome barriers use the
  chronological ticks, while aggregated ask OHLC is retained as an audit check.

## Parameter Budget

Exactly six numeric constants are locked:

1. return lookback: `4` bars;
2. Wilder ATR period: `14`;
3. factor threshold: `0.50`;
4. pullback arm life: `4` bars;
5. target: `1.5R`;
6. maximum hold: `8` bars.

Maximum tunable parameters: `0`. No grid, alternate weighting, pair-set
change, threshold sweep, or post-result edit is permitted.

## Broker-Cost Blocker

No train outcome may be read until a frozen same-broker cost manifest provides:

- hash-pinned historical bid/ask quote ticks covering every required bar of
  every eligible episode, with broker/server/account/data fingerprints;
- either at least `30` same-symbol closed trade lifecycles proving commission,
  or a hash-pinned broker contract that states the exact tested account and
  symbol commission in account currency per lot;
- at least `100` same-broker, same-symbol fills with an independent pre-fill
  executable quote reference, including at least `30` buys and `30` sells.
  For a buy, adverse slippage is `max(0, fill_price - prefill_ask)`; for a sell,
  it is `max(0, prefill_bid - fill_price)`. A bid, mid, or opposite-side quote
  is forbidden because it embeds spread and would double-count it;
- side-specific P90 adverse slippage, with frozen round-turn value
  `slippage_rt_p90_pips = P90_buy + P90_sell`, plus all source hashes, sample
  counts, time windows, and symbol applicability.

Convert commission separately for every eligible trade at execution tick `e`:

```text
pip_value_account_per_lot_e
  = contract_size_i * pip_size_i * quote_to_account_rate_e
commission_rt_pips_e
  = commission_rt_account_per_lot / pip_value_account_per_lot_e
```

For this USD account, `quote_to_account_rate_e = 1` for EURUSD and GBPUSD. For
USDJPY it is `1 / mid_USDJPY,e`, where
`mid_USDJPY,e = (bid_e + ask_e) / 2`. Any future cross whose quote currency is
not the account currency must provide a same-timestamp, same-broker conversion
tick path and hash. Store the entry quote, conversion rate, pip value, and
per-trade commission pips in the outcome artifact. A current/static tick-value
snapshot is forbidden.

Because the locked OHLC is bid data, spread is not a post-hoc scalar charge.
For each `x in {1.0, 1.5, 2.0}`, rebuild the ask path, entry, short-side
barriers, target, initial risk, and `GrossR_x` exactly as specified above. Then
charge only the non-spread round-turn costs post hoc:

```text
nonspread_rt_pips_x = x * (commission_rt_pips_e + slippage_rt_p90_pips)
NetR_x              = GrossR_x
                      - nonspread_rt_pips_x / initial_risk_pips_x
```

This avoids both undercharging shorts and double-counting spread. Zero cost, a
generic hardcoded spread, a current spread snapshot, bar-level synthetic ask,
another pair's cost, slippage measured from bid/mid for buys, or using bid
barriers for buy-to-cover exits is forbidden. Missing provenance, insufficient
commission/slippage sample counts, or any missing quote/cost observation on an
eligible episode invalidates that entire split and kills the probe before any
outcome summary; episode-wise deletion is forbidden.

## Locked De-Dup Controls

All controls use the same synchronized data, pullback-break, stop, target,
time exit, same-day rule, and cost model.

### CTRL-S555-LEAD

For each possible target `i`, let the other pairs be `j,k`. A target-specific
lead condition exists only when `sign(u_j,t) = sign(u_k,t) = D_i` with nonzero
`D_i`, `D_i*u_j,t >= 0.50`, `D_i*u_k,t >= 0.50`, and the target is numerically
unconfirmed: `D_i*u_i,t < 0.50`. Its raw event is the false-to-true transition
of that full condition or a change of `D_i` from the preceding completed bar.
If multiple target events occur together, select the smallest `D_i*u_i,t`
(least confirmed), breaking exact ties `EURUSD`, `GBPUSD`, `USDJPY`. Freeze the
target and direction. At completed trigger bar `b`, both leaders must still
meet `D_i*u >= 0.50` and the target must now meet `D_i*u_i,b >= 0.50`; otherwise
expire. Apply the common pullback, next-tick entry, outcome, arbitration, and
cooldown rules. S555 cooldown resets only after one completed bar on which no
target-specific lead condition is true. This is the explicit lead-lag baseline.

### CTRL-S618-CONSENSUS

Define consensus condition `Q_D,t` when one nonzero direction `D` satisfies all
three `D*u_i,t >= 0.50`. A raw event is `Q` false-to-true or a direction change
from the preceding completed bar. Freeze `USDJPY` as target and require the same
consensus at trigger bar `b`; otherwise expire. Apply the common pullback,
next-tick entry, outcome, arbitration, and neutral-reset rules, using consensus
false as its cooldown reset. This is hard consensus into a fixed target.

### CTRL-S670-DIVERGENCE

Mirror every accepted challenger factor episode `t0`, but independently select
`argmin_i(D * u_i,t0)` and freeze that laggard; exact ties use
`EURUSD`, `GBPUSD`, `USDJPY`. Apply the same factor-at-`b`, pullback,
next-tick entry, outcome, arbitration, and neutral-reset rules. This is
catch-up/divergence.

Each role's accepted `t0`, ignored overlapping raw events, arm expiry, entry,
exit, and cooldown-reset timestamp must be written to its pre-outcome audit.

The candidate is killed unless, in both train and holdout, it exceeds every
control by at least `+0.15` cost PF x1 and `+0.05R/trade` mean net expectancy.

Cost PF is `sum(positive NetR) / abs(sum(negative NetR))`. Zero trades, zero
loss denominator, missing/non-finite NetR, or a missing/non-finite PF for either
challenger or control makes that split/control comparison fail closed; never
substitute infinity, zero, or a sentinel value to pass the margin.

## Test Sequence And Gates

1. Freeze and hash analyzer code and cost-source manifest.
2. Run train only.
3. Kill immediately if train misses any gate.
4. Reveal the holdout exactly once only after a complete train pass.
5. Do not inspect holdout subgroups or reuse it for redesign.

Required separately on train and holdout:

- `trades / ((to_date - from_date).days / 7.0)` is between `2.0` and `5.0`;
- cost PF x1 is strictly greater than `1.30`;
- cost PF x1.5 is at least `1.25`;
- cost PF x2 is at least `1.00`;
- net R at x1.5 is positive;
- superiority over each locked control is at least PF `+0.15` and
  expectancy `+0.05R/trade`;
- no pair contributes more than `60%` of trades;
- every pair contributes at least `15%` of trades.

Stability requires at least `2/3` positive train calendar years at x1.5 cost,
and both `2024` and `2025` positive in holdout at x1.5 cost.

## Kill Rules And Banned Rescues

Kill immediately on missing synchronized/cost data, any train or holdout gate
failure, fixed-target concentration, or failure to beat S555/S618/S670 by the
locked margins.

No post-result pair exclusion, pair threshold, session/hour/day/month/year/news
filter, direction filter, parameter change, factor reweighting, median-to-mean
change, symbol addition, broker/suffix substitution, spread cutoff, control
removal, or holdout rerun is allowed. Any such observation becomes a separate
new idea and cannot rescue this hypothesis.

## Promotion Boundary

Passing train and holdout authorizes only a source/casebook review, a separate
default-off EA-patch preregistration, and a multi-symbol non-repaint/timestamp
audit. It does not establish Sonic source parity or deploy readiness.
