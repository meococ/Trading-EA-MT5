# PROBE PLAN — HYP-TRENDSTACK-EURUSD-H1-001

Status: FROZEN 2026-07-28 before any outcome or post-entry price path for this
object was loaded. This file is SHA256-bound into the registry `probe` row
before Stage 0 runs and is immutable thereafter. A pre-outcome amendment must
be a new `_V2` file bound at the next legal transition. Any change after an
outcome is opened requires a new hypothesis ID.

## 1. Identity and claim

- `hypothesis_id`: `HYP-TRENDSTACK-EURUSD-H1-001`
- Research package: `EA_TrendStackContinuation`; no `.mq5`, Model 0, paper, or
  live authority exists at probe freeze.
- Instrument / decision TF: FivePercent `EURUSD`, H1 decisions with M1
  kill-only execution proxy.
- Exact object: a 252-valid-day directional context (`M252`) qualified by the
  direction of the six closed H1 bars from 06:00 through 12:00 UTC (`M6`).
  `M252` is the core signal. The only incremental claim is that same-direction
  `M6` alignment improves `M252`; the two legs are not claimed to contribute
  symmetrically.
- Mechanism prior: slow information diffusion and persistent positioning can
  create time-series momentum, while same-day price continuation may identify
  days when that state is active. Moskowitz, Ooi and Pedersen study diversified
  monthly futures, not this single-pair intraday rule, so it is a prior rather
  than validation:
  https://w4.stern.nyu.edu/facdir/lpederse/papers/TimeSeriesMomentum.pdf
- Intraday FX momentum is market-structure dependent and transaction costs can
  remove technical returns; these are adverse priors, not support for the exact
  rule:
  https://biblio.ugent.be/publication/8060014
  https://biblio.ugent.be/publication/7190535

## 2. De-dup and failure radius

- The generic registry and `do_not_repeat_failures.md` were checked before
  freeze. The exact ID and exact conjunction are absent.
- This is not terminal `HYP-BR-SESSDRIFT`: direction is recomputed causally
  from a 252-valid-day state and qualified by same-day return, not fixed by a
  clock window.
- It does not reuse the MACD/EMA/ADX, compression, sweep/FVG, pivot/retest,
  VWAP, raw-BREAK, or external-book objects already killed.
- The 2026-07-17 pure-OHLC design-only screen named cross-TF momentum and
  early-to-late momentum as separate single-object rebrands, but ran no probe
  and explicitly left multi-factor, context-conditional conjunctions untested.
- Classification: `MATERIALLY_NEW_WITH_HIGH_ADVERSE_OHLC_PRIOR`.
- Failure radius is the exact conjunction, clocks, lookback, ATR geometry and
  exit below. If it fails, changing 252, 06/12/18 UTC, adding a volatility/day/
  year filter, removing either leg, flipping continuation to reversal, changing
  the stop, or tuning a threshold is forbidden post-hoc rescue.

## 3. Hash-bound data and sealed split

- Manifest: `02. AlphaFactory/data/fivepercent/EURUSD/manifest.json`.
- H1 closed-bid parquet SHA256:
  `71860016AF1BD1B17353B043AFF799233A787E9DF3F587913FCD2F5328BB1E08`.
- M1 closed-bid parquet SHA256:
  `2959C555DB6690FD6EFD6CFB3B4C6323698E590C9B2D71E1E55F1902F724235A`.
- Clock model:
  `02. AlphaFactory/tools/research/fivepercent_server_clock.py`; `time_utc` is
  the only decision clock. Duplicate or ambiguous UTC opens fail the day.
- The historical spread column is unusable as cost truth because 24.5553% of
  the audited M1 rows are zero. Fixed all-in round-trip costs below are
  `UNVERIFIED_PROXY` and may kill but cannot confirm or promote.
- Feature-only warm-up: `2015-01-02T00:00:00Z` through
  `2016-01-03T23:59:59Z`; no warm-up opportunity is scored.
- DESIGN scoring window: `[2016-01-04T00:00:00Z, 2021-01-01T00:00:00Z)`;
  1,824 elapsed calendar days / 260.571428571 weeks.
- Internal VALIDATION: `[2021-01-01T00:00:00Z, 2023-01-01T00:00:00Z)`;
  730 elapsed calendar days / 104.285714286 weeks.
- HOLDOUT: every row with `time_utc >= 2023-01-01T00:00:00Z`; the sealed loader
  must reject it. No holdout row, quote, aggregate, or outcome may be loaded.
- Stage 0 loads H1 only and may compute pre-entry features/counts. It must not
  load M1 or any price at/after 12:01 UTC on a scored day.
- Economic access is sequential: DESIGN only. VALIDATION may be opened exactly
  once only after DESIGN passes every frozen absolute, relative, DSR and
  integrity gate. HOLDOUT remains sealed in all cases.

## 4. Frozen chronology and decision surface

### Valid daily close sequence and `M252`

- Aggregate H1 rows by UTC calendar date. A valid UTC day has finite, positive,
  unique OHLC and at least 20 distinct H1 UTC opens; dates with fewer bars are
  excluded as partial days. Its daily close is the close of the latest H1 bar
  on that UTC date.
- For decision date `d`, use only valid daily closes from UTC dates `< d`.
  Let `C[k]` be the last accepted close and require 253 accepted closes.
  `M252 = sign(C[k] / C[k-252] - 1)`, equivalently
  `sign(valid_closes[-1] / valid_closes[-253] - 1)`.
- Snapshot `M252` at 06:00 UTC. It cannot be recomputed at 12:00. Equality,
  non-finite data, or insufficient history produces a frozen exclusion reason.

### Six-hour qualifier and opportunity identity

- Require exactly one H1 bar at each UTC open 06:00, 07:00, 08:00, 09:00,
  10:00 and 11:00 on `d`, with finite positive OHLC. Missing or duplicate bars
  exclude the base day.
- `M6 = sign(close_of_11:00_bar / open_of_06:00_bar - 1)`. Equality is a
  qualifier rejection. `alignment = (M6 == M252)`.
- Decision cutoff is 12:00:00 UTC after the 11:00 bar closes. Maximum one entry
  per UTC date. Immutable `opportunity_id = YYYY-MM-DD` is retained for every
  base day; a challenger rejection is recorded, never deleted.

### Arms and trial accounting

Exactly four arms are frozen; `N_trials = 4`. Cost tiers are not trials.

1. `CONTROL_M252_ONLY`: every complete base day; direction `M252`.
2. `CONTROL_M6_ONLY`: every complete base day with nonzero `M6`; direction
   `M6`.
3. `CHALLENGER_STACK`: aligned base days only; direction `M252` (which equals
   `M6`).
4. `NEGATIVE_DISAGREE`: disagreement base days only; direction `M6` (which is
   opposite `M252`).

The two controls test the standalone legs; the disagreement arm tests whether
agreement selects a materially better state rather than merely reducing
exposure. No parameter grid, optimizer, sequential threshold look, polarity
flip, or fifth arm is authorized. DSR uses all four executed arms, per-trade
SR, PSR with skew and non-excess kurtosis, variance across arms, and a floor of
0.95 using
`02. AlphaFactory/tools/research/dsr.py`.

### ATR, M1 proxy entry, stop and exit

- `ATR20_mt5` is the simple moving average of True Range from
  `tools/research/indicators.py`, evaluated on the closed H1 bar with UTC open
  11:00 at the 12:00 decision. This is equivalent to MT5 `iATR(PERIOD_H1,20)`
  `CopyBuffer` shift 1 at 12:00. Wilder ATR is forbidden.
- A future survivor requires `parity_harness.py` PASS on identity-proven H1
  rows including DST and holiday boundaries before EA authority.
- Economic probe contract is `M1_PROXY_KILL_ONLY`. Entry is the bid open of the
  M1 bar at exactly 12:01 UTC, never the 12:00 open. Missing 12:01 data makes
  that post-decision day engineering-invalid, not silently excludable.
- Initial stop distance is the frozen ATR20. Long stop is entry minus ATR;
  short stop is entry plus ATR. There is no TP.
- Scan M1 bars chronologically from 12:01 through 17:59 UTC. If a later bar
  opens beyond the stop, exit at that adverse open; otherwise a low/high stop
  touch exits at the exact stop. With one stop and no target, no same-bar
  target/stop ambiguity exists. Missing path rows after entry invalidate the
  run.
- If no stop occurs, exit at the 18:00 M1 bid open. Missing 18:00 invalidates
  the run. Friday uses the same exit and never carries to Monday.
- Proxy gross R is `direction * (exit_bid - entry_bid) / ATR20`. Net R subtracts
  `round_trip_cost_pips / initial_stop_pips`. Bid/ask side fidelity, slippage,
  broker stop/freeze levels, lot sizing and margin are not represented; this is
  why a survivor cannot advance without a new frozen tick/MT5 parity contract.
- Round-trip all-in proxy tiers: x1 = 1.50 pips, x1.5 = 2.25 pips, x2 = 3.00
  pips. Pip size is 0.0001. Missing cost is never interpreted as zero.

## 5. Stage-0 observation gates before any outcome

- DESIGN challenger opportunities must be 522 through 1,302 inclusive
  (`2..5 × 260.571428571` elapsed weeks, integer-rounded inward).
- VALIDATION challenger opportunities must be 209 through 521 inclusive
  (`2..5 × 104.285714286` elapsed weeks, integer-rounded inward).
- Each split must contain at least 50 LONG and 50 SHORT challenger
  opportunities. Otherwise `PARK_INSUFFICIENT_DIRECTION_COVERAGE`.
- Count pre-broker opportunity cadence and completed-entry cadence separately;
  completed entries must also be 2..5 per elapsed week.
- Any chronology, hash, warm-up, clock, or causality fault is `INVALID`. Any
  observation/cadence fault is `PARK` before PnL. Do not change the rule.

## 6. Frozen economic gates — all required

The gates apply independently to each opened split unless explicitly marked.
`PF` is calculated from net-R winners and losers after the stated proxy tier.

| # | Gate | Threshold |
|---|---|---|
| 1 | Challenger completed cadence | `2.0..5.0` per elapsed calendar week |
| 2 | Challenger PF x1 | `> 1.30` |
| 3 | Challenger PF x1.5 | `>= 1.25` |
| 4 | Challenger PF x2 | `>= 1.00` |
| 5 | Challenger mean net R x1 | `>= 0.08 R/trade` |
| 6 | Challenger total net R x1 | `> 0` |
| 7 | Positive years | DESIGN `>=4/5`; VALIDATION `2/2` |
| 8 | Challenger DSR across four arms | `>=0.95` |
| 9 | Stack PF x1 delta vs better standalone control | `>= +0.15` |
| 10 | Stack mean net R x1 delta vs better standalone control | `>= +0.05 R/trade` |
| 11 | Stack PF x1 delta vs negative disagreement | `>= +0.15` |
| 12 | Stack mean net R x1 delta vs negative disagreement | `>= +0.05 R/trade` |

The research book acceptance contract also remains binding for any later EA:
PF `>1.30`, 2–5 trades/week, max DD 6%, PF x1.5 `>=1.25`, PF x2 `>=1.00`,
and Monte Carlo P95 DD `<=6%`. DD/Monte Carlo are not promotion evidence at
this offline proxy stage and must be validated later if the probe survives.

## 7. Routing and prohibitions

- `INVALID`: data hash, sealed-loader, clock, index, causality, ATR, path, or
  reconciliation fault. Repair engineering under the same frozen plan; do not
  make a market verdict.
- `PARK`: Stage-0 cadence or direction coverage fails. Do not open outcomes.
- `KILL`: DESIGN fails any economic/relative/DSR gate; do not open VALIDATION.
  If DESIGN passes but VALIDATION fails any gate, kill the exact object.
- `PROBE_SURVIVOR`: both splits pass every gate. This authorizes only a new
  frozen source-build/prereg contract; it is not economic confirmation,
  Model-0 authority, deploy readiness, paper authority, or live authority.
- Forbidden: post-hoc hour/day/year/session/symbol/TF/lookback/ATR/cost edits;
  dropping losing arms or trades; outcome-conditioned exclusions; using 2023+
  holdout; interpreting the unusable spread field as zero cost; building an EA
  after PARK/KILL; or calling a proxy survivor confirmed.

## 8. Required artifacts and reconciliation

- Red-first unit tests for daily indexing, off-by-one behavior, six-bar
  chronology, sealed cutoff, ATR shift, M1 gap/stop/exit handling, cost R,
  cadence denominators and missing-data invalidation.
- Stage-0 JSON with data hashes, plan SHA, exclusion counts, immutable
  opportunity ledger hash, split/direction counts, and `outcomes_opened=false`.
- Economic `probe_result.json`, joined trade ledger CSV, reconciliation receipt,
  and append-only `research/trials/trial_log.jsonl`; every row includes the
  hypothesis ID and frozen plan SHA. Report both per-trade results and a common
  UTC daily book with no-trade days explicitly represented as zero so exposure
  reduction cannot masquerade as incremental signal quality.
- Readout plus exactly one terminal/survivor registry transition. On a terminal
  result, update `hot.md` and `do_not_repeat_failures.md`. No chart anatomy is
  required for a fatal preregistered offline probe kill; a survivor must proceed
  through the source, compile, non-repaint, Model-0, log/chart-forensics and
  Heavy-Delivery gates under a separately frozen contract.
