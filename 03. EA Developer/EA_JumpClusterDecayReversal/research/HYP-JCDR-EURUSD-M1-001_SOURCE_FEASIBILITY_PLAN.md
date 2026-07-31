# HYP-JCDR-EURUSD-M1-001 — Source-Feasibility Plan

Status: `FROZEN_PRE_OUTCOME_SOURCE_CONTRACT`

## 1. Identity and purpose

- Hypothesis: `HYP-JCDR-EURUSD-M1-001`
- Package: `EA_JumpClusterDecayReversal`
- Symbol / decision timeframe: `EURUSD / M1`
- DESIGN window: `2016-01-04` through `2020-12-31`, public FivePercent
  splitvault_002 only.
- First task: one outcome-blind source-feasibility attempt. No return, trade,
  post-entry price, economics, validation, holdout, MQL5 or MT5 access.

The market thesis is that short-horizon price jumps arrive in self-exciting
bursts when aggressive flow temporarily overwhelms displayed liquidity. A
reversal candidate exists only after the burst stops producing new jumps and
price causally re-enters the completed impulse range. This tests an event-arrival
state transition, not the direction or timing of tick volume.

## 2. Material information delta

- Unlike VCEX, this object does not use within-bar tick-volume timing, early/late
  volume-clock impulses, or exhaustion thresholds.
- Unlike ARUC, it does not rank aggregate signed activity against same-slot
  business dates or use an H1 response ratio.
- Unlike LVOR, it does not condition on low tick-volume activity, outer-close
  efficiency, or a fixed five-M1 counter-body confirmation.
- Unlike DFR, it has no diurnal residual or same-slot seasonal expectation.
- Unlike Round/TrendStack/session-drift objects, it is not anchored to a round
  level, fixed clock, external slow state, or moving-average stack.

The new information is the causal arrival pattern of standardized M1 jump
events plus a post-cluster decay/re-entry state.

## 3. Immutable data bindings

- Manifest:
  `02. AlphaFactory/data/fivepercent/EURUSD/splitvault_002/public/design_manifest.jsonl`
  SHA-256 `A8A091DA8365602CB1D02BA571E96B4FB00B50621A73166B8CEDDBC1A7EED8C7`.
- Receipt:
  `02. AlphaFactory/data/fivepercent/EURUSD/splitvault_002/public/design_receipt.json`
  SHA-256 `8109B11B6054517B9904FB4ACEF25EB7C6BD2485487CA9D69340DDC7E7D27FF8`.
- Public M1 source SHA-256:
  `2959C555DB6690FD6EFD6CFB3B4C6323698E590C9B2D71E1E55F1902F724235A`.
- Price side: BID producer OHLC. `tick_volume` and `spread` may be schema-
  validated but are forbidden as signal, filter, cost or target inputs.
- Private, validation and holdout paths are forbidden. Every opened shard must
  be the exact manifest-bound regular, single-link public DESIGN file.

## 4. Closed-bar event construction

All timestamps are UTC. Any missing, duplicate, non-minute-aligned or
non-contiguous M1 row resets formation state and cannot be bridged.

For each fully closed M1 bar `t`:

1. `r_t_pips = (close_t - close_{t-1}) / 0.0001`.
2. Robust pre-decision scale is the median of `abs(r)` over the exact 240
   contiguous closed M1 returns ending at `t-1`. The current return is excluded.
3. Jump threshold is `max(1.20 pips, 3.0 * robust_scale_t)`.
4. A jump event exists when `abs(r_t_pips)` is at least that threshold. Its sign
   is the sign of `r_t_pips`. All comparisons are finite-only with four-ULP
   inclusive boundary tolerance.
5. A cluster peak candidate must end on a jump bar and use the exact 15
   contiguous closed M1 bars ending at that bar. It requires:
   - at least three jump events;
   - at least 80% of jump events share the dominant sign;
   - the signed close displacement from the open of the first jump bar to the
     peak-bar close agrees with the dominant sign;
   - absolute signed displacement is at least 4.0 pips.
6. The cluster anchor is the open of the first jump bar. The cluster extreme is
   the maximum high for an up cluster or minimum low for a down cluster across
   the frozen 15-bar window.
7. After a cluster peak, inspect at most the next ten fully closed M1 bars. The
   first causal decision bar must satisfy both:
   - the decision bar and its two predecessors contain no jump event under their
     own pre-decision thresholds;
   - price retracement from cluster extreme toward anchor is in `[0.25, 1.00]`
     of the frozen extreme-to-anchor distance.
8. A new gap or a new qualifying cluster peak before a decision cancels the old
   candidate and starts the new frozen candidate. No overlapping candidate is
   retained.
9. The first qualifying decision per UTC date is selected. All later candidates
   that date are classified `DAILY_REFRACTORY` and cannot reserve a horizon.

TRUE direction is opposite the cluster dominant sign. The matched
`FOLLOW_CONTROL` direction follows it. Both arms use the identical signal ID,
decision timestamp, next-minute entry timestamp, 60-minute source horizon and
stop distance.

## 5. Source-only entry/horizon/risk geometry

- Entry timestamp is exactly the next contiguous observed M1 open time after the
  closed decision bar. Source feasibility may use its timestamp, never its OHLC.
- Required source horizon is exactly 60 contiguous observed M1 timestamps from
  entry inclusive to exit exclusive. Missing or incomplete horizons are
  classified before any ledger arm is emitted.
- Frozen future stop distance is `max(6.0 pips, abs(cluster_extreme-anchor) +
  0.50 pips)`. It uses only completed formation prices.
- Future economic geometry, if separately authorized, is 1R target and 60-minute
  time exit with 1.50 / 2.25 / 3.00-pip round-turn cost tiers. This plan does not
  compute those outcomes.
- Source cost geometry uses only `1.50 / stop_distance_pips`.

## 6. One-shot source gates

All gates are fatal and frozen before any source count is opened:

1. Outcome-blind plane intact: zero post-decision OHLC reads, returns, trades,
   economic metrics, validation, holdout, MQL5, MT5, network or paid requests.
2. Exact TRUE/FOLLOW_CONTROL one-to-one match on every executable signal.
3. Formation-domain completeness at least `0.99`.
4. Source-executable 60-minute horizon ratio at least `0.99`.
5. TRUE cadence between `2.0` and `5.0` per elapsed calendar week.
6. TRUE long share at least `0.25`.
7. TRUE short share at least `0.25`.
8. Maximum calendar-year share at most `0.35`.
9. At least 20 executable TRUE signals per direction.
10. Median frozen stop distance at least `6.0` pips.
11. Median `1.50-pip / stop` ratio at most `0.25`.

Elapsed weeks are `(2020-12-31 - 2016-01-04).days / 7`; active weeks are
forbidden as denominator.

PASS verdict: `PASS_SOURCE_FEASIBILITY_FUTURE_ECONOMICS_PREREG_ONLY`.

FAIL verdict: `SOURCE_FAIL_NO_ECONOMICS_AUTHORITY`.

Engineering/data failures are `ENGINEERING_INVALID_NO_MARKET_VERDICT` and do
not count as market evidence.

## 7. Attempt and evidence contract

- Attempt ID: `JCDR001-SOURCE-001`.
- Evidence root:
  `03. EA Developer/EA_JumpClusterDecayReversal/research/evidence/HYP-JCDR-EURUSD-M1-001_SOURCE_FEASIBILITY/JCDR001-SOURCE-001`.
- Attempt limit: one. Evidence root must not exist before the authorized run.
- Required terminal chain: `attempt_started.json`, source classifications,
  matched source ledger, compact source report, non-terminal receipt, and
  `attempt_terminal.json` as sole authoritative completion.
- Import must be inert. Production requires an exact reviewed registry-row hash
  burned into a single sentinel and an explicit CLI flag. The sentinel is
  disarmed immediately after the single attempt and before interpretation.
- A separate deterministic replay must reconstruct classifications and the
  canonical ledger digest without reusing staged rows.

## 8. Forbidden rescue and authority

After any valid source result, do not change jump floor/multiple, scale lookback,
cluster length/count/coherence/displacement, decay length, retracement band,
daily refractory rule, horizon, stop, session, direction, year, or gate based on
the readout. Do not promote FOLLOW_CONTROL, a subgroup, or a shifted timestamp.
Any material successor needs a fresh mechanism/ID/preregistration.

This plan grants no source run by itself and grants no economics, validation,
holdout, private, MQL5, MT5, optimization, promotion, paper or live authority.
