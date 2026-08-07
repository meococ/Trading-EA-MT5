# HYP-JCDR-EURUSD-M5-002 — Source-Feasibility Plan

Status: `FROZEN_PRE_OUTCOME_SOURCE_CONTRACT`

## 1. Identity and decision question

- Hypothesis: `HYP-JCDR-EURUSD-M5-002`
- Package: `EA_JumpClusterDecayReversal`
- Symbol / decision timeframe: `EURUSD / M5`
- DESIGN window: `2016-01-04` through `2020-12-31`, public FivePercent
  `splitvault_002` only.
- One authorized first task: determine whether an exact-complete M5
  jump-cluster/decay/re-entry population exists at usable cadence and geometry.
- This task is outcome blind. It may not read post-entry OHLC, calculate a
  return, simulate a trade, invoke MT5/MQL5, open validation/holdout/private
  data, or optimize a threshold.

The causal object is the transition from a self-exciting cluster of
standardized closed-bar jumps to a causally observed decay state and range
re-entry. Hawkes jump-intensity decay is a mechanism prior, not proof of price
mean reversion. Osler's FX cascade evidence also permits continuation, so the
future economic stage—if separately authorized—must preserve exact matched
`TRUE_REVERSAL` and `FOLLOW_CONTROL` arms. No arm may be selected from this
source result.

## 2. Why this is not a rescue of JCDR001 or RSF

- `HYP-JCDR-EURUSD-M1-001` is terminal under its exact M1 prior-240,
  15-M1 formation and full-period formation-denominator contract. Its outcome
  plane was never opened.
- This successor changes the decision and information surface to exact UTC M5
  bars, a prior-48 M5 scale, 15-M5 cluster state, 10-M5 decay state, and an
  exact-five-constituent construction contract. It has a fresh ID, attempt,
  preregistration and evidence root.
- It is not `HYP-RSF-EURUSD-M5-LIQUIDITY-POOL-ECON-010`: TB SMC swings,
  BOS/MSS, unconsumed objectives and structural continuation are forbidden as
  source inputs.
- It is not a session/fixing, diurnal residual, volume-clock, cross-pair lag or
  indicator-voting strategy.

## 3. Immutable source binding

- Manifest:
  `02. AlphaFactory/data/fivepercent/EURUSD/splitvault_002/public/design_manifest.jsonl`
  SHA-256 `A8A091DA8365602CB1D02BA571E96B4FB00B50621A73166B8CEDDBC1A7EED8C7`.
- Receipt:
  `02. AlphaFactory/data/fivepercent/EURUSD/splitvault_002/public/design_receipt.json`
  SHA-256 `8109B11B6054517B9904FB4ACEF25EB7C6BD2485487CA9D69340DDC7E7D27FF8`.
- Public M1 source SHA-256:
  `2959C555DB6690FD6EFD6CFB3B4C6323698E590C9B2D71E1E55F1902F724235A`.
- Price side: producer BID OHLC. `tick_volume`, `spread` and `real_volume` may
  be schema-validated and must then be discarded. They are forbidden as
  feature, filter, cost or target inputs.
- Every opened shard must be the exact manifest-bound regular, single-link
  public DESIGN file. Network and paid requests are forbidden.

## 4. Exact-complete M5 construction

All timestamps are UTC. M1 timestamps denote bar opens.

1. Floor every observed M1 timestamp to an aligned five-minute UTC start `g`.
2. A nonempty group is `M5_CONSTRUCTION_COMPLETE` only when it contains exactly
   the five unique starts `g+0m ... g+4m` and all OHLC values are finite and
   ordered. Its M5 OHLC is first open, maximum high, minimum low, last close.
3. Its internal decision stamp is `g+4m`, the last constituent start. Therefore
   a signal using that completed bar becomes available only at `g+5m`, the next
   M5 open. This convention prevents same-bar execution.
4. Any missing, duplicate, misaligned or incomplete group is excluded and
   resets formation state. Consecutive constructed M5 bars must have decision
   stamps exactly five minutes apart.
5. Frozen construction completeness is:
   `complete exact-five M5 groups / all nonempty aligned M5 groups` across the
   manifest-bound DESIGN source. This is a constituent-quality gate, not the
   JCDR001 full-row/lookback denominator and not an eligible-signal denominator.

## 5. Closed-bar event construction

For every fully constructed M5 bar `t` inside an exact contiguous M5 segment:

1. `r_t_pips = (close_t - close_{t-1}) / 0.0001`.
2. Robust scale is the median of `abs(r)` over the exact 48 contiguous M5
   returns ending at `t-1`; the current return is excluded.
3. Jump threshold is `max(1.20 pips, 3.0 * robust_scale_t)` with finite-only,
   four-ULP inclusive comparisons.
4. A cluster peak must end on a jump bar and use the exact 15 contiguous M5
   bars ending there. It requires at least three jumps, at least 80% dominant
   sign, dominant-signed close displacement from the first jump-bar open to
   peak close, and absolute displacement at least 4.0 pips.
5. The anchor is the first jump-bar open. The frozen extreme is the maximum
   high of an up cluster or minimum low of a down cluster over the 15-M5
   window.
6. Inspect at most the next ten complete M5 bars. The first decision bar must
   have no jump on itself or its two closed predecessors and must retrace from
   extreme toward anchor by a frozen fraction in `[0.25, 1.00]`.
7. A new gap or new qualifying cluster peak replaces/cancels the prior pending
   cluster. Only the first qualifying decision per UTC date is retained.

`TRUE_REVERSAL` direction is opposite the dominant cluster sign.
`FOLLOW_CONTROL` direction follows it. Both arms share the same signal ID,
decision timestamp, availability timestamp, source horizon and stop geometry.
The durable ledger label `TRUE` is the implementation name for the research
arm `TRUE_REVERSAL`; the report exposes this mapping explicitly. It is not a
third arm and cannot be reinterpreted after source readout.

## 6. Timestamp-only horizon and geometry

- Availability/entry timestamp is exactly the next M5 open (`decision stamp +
  1 minute`). The timestamp may be emitted; its OHLC may not be read.
- Required horizon is 60 exact contiguous observed M1 starts from availability
  inclusive to exit exclusive. Only membership/timestamps may be inspected.
- Frozen future stop distance is
  `max(6.0 pips, abs(cluster_extreme-anchor)/0.0001 + 0.50 pips)`.
- Source cost geometry is only `1.50 pips / stop_distance_pips`.
- A future economic plan, if authorized, must freeze 1R and 60-minute matched
  arms plus dynamic cost/slippage stresses before opening any outcome.

## 7. One-shot source gates

All eleven gates are fatal and frozen:

1. Outcome-blind plane intact.
2. Exact one-to-one `TRUE_REVERSAL` / `FOLLOW_CONTROL` rows.
3. Exact-five constituent M5 construction completeness at least `0.99`.
4. Timestamp-only 60-minute horizon executability at least `0.99`.
5. Executable TRUE cadence in `[2.0, 5.0]` per elapsed calendar week.
6. TRUE long share at least `0.25`.
7. TRUE short share at least `0.25`.
8. Maximum calendar-year share at most `0.35`.
9. At least 20 executable TRUE signals per direction.
10. Median frozen stop at least `6.0` pips.
11. Median `1.50-pip / stop` ratio at most `0.25`.

Whole empty M5 buckets and incomplete groups always reset state and their count
is reported. Gap rate is intentionally diagnostic rather than a twelfth gate:
the gate in item 3 measures constituent quality only, while fragmentation can
only reduce causal formations and fixed-elapsed-week cadence; it cannot be
bridged or imputed.

Elapsed weeks are `(2020-12-31 - 2016-01-04).days / 7`; active-week or
post-result denominators are forbidden.

PASS: `PASS_SOURCE_FEASIBILITY_FUTURE_ECONOMICS_PREREG_ONLY`.

FAIL: `SOURCE_FAIL_NO_ECONOMICS_AUTHORITY`.

An engineering/data-contract failure is
`ENGINEERING_INVALID_NO_MARKET_VERDICT` and does not count as market evidence.

## 8. Attempt, evidence and future indicator roles

- Attempt: `JCDR002-SOURCE-001`, one use only.
- Evidence root:
  `03. EA Developer/EA_JumpClusterDecayReversal/research/evidence/HYP-JCDR-EURUSD-M5-002_SOURCE_FEASIBILITY/JCDR002-SOURCE-001`.
- Required chain: started receipt, source classifications, matched source
  ledger, compact report, non-terminal receipt, authoritative terminal receipt,
  independent deterministic replay and hash readback.
- The production sentinel is disarmed by default and may be armed only with the
  exact latest reviewed registry-row SHA after tests and independent review.

If Stage 0 passes, a separate economic preregistration must freeze the four
indicator roles before outcomes:

- AIRD: state/risk permission only; never direction.
- VRC: risk/context veto for disorder/high chop; never direction.
- MBB: energy/location context; block flat compression, never standalone entry.
- QQE: timing veto against momentum still expanding with the original jump.
- TB SMC: stop/invalidation geometry only; no BOS/MSS entry or objective route.

No numeric indicator gate is authorized here. Source PASS is not edge evidence
and grants no economics, EA, MT5, validation, holdout, optimization, promotion,
paper or live authority.

## 9. No-rescue rule

After the one valid source result, do not change timeframe, 48-return scale,
jump floor/multiple, 15-bar cluster, jump count/coherence/displacement, ten-bar
decay, three-bar quiescence, retracement band, daily refractory, horizon,
stop/cost geometry, construction denominator, date/symbol or any gate based on
the readout. A terminal failure closes this exact successor.
