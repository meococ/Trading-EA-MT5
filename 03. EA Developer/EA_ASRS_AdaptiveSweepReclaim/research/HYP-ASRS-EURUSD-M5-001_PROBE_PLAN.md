# PROBE PLAN — HYP-ASRS-EURUSD-M5-001

Status: FROZEN 2026-07-25 before any PnL, forward excursion, trade outcome, or
2023+ holdout bar of this object was read.

This file is immutable once its SHA256 is bound into the candidate registry.
Any pre-outcome correction must be a new `_V2.md` plus a corrective append. Any
change after Stage-0 counts are read requires a fresh hypothesis ID.

## 1. Identity and authority

- Hypothesis: `HYP-ASRS-EURUSD-M5-001`
- Research package: `EA_ASRS_AdaptiveSweepReclaim`
- Symbol / timeframe: FivePercent EURUSD M5
- Owner scope: review the 24-Jul-2026 ASRS report and begin development through
  the workspace process.
- Source report SHA256:
  `3F05A242323D0B9926AED5AC3B9B6A47A630D1B544F8F298DBAF1335B0A4FF54`
- Current authority: Stage-0 scanner implementation, tests, and one
  deterministic outcome-blind execution only.
- `.mq5`, compile, Model 0, economics, paper/live attach: not authorized unless
  Stage-0 survives every gate.

## 2. De-dup and adverse priors

Bound review:
`04. Memory/research/20260725_ASRS_DEDUP_READOUT.md`.

- `HYP-ICTVIS-EURUSD-M5-001` killed the price-only generous M5 sweep-reversion
  object: zero-cost PF `1.019`, median risk `4.5` pips, and cost domination.
- `HYP-ICT-FVG-FID-EURUSD-M5-001` already defines the adjacent high-recall
  sweep/reclaim baseline and is parked on cost/news provenance after a clean
  engineering build.
- NY sweep-reclaim and VRAS stop-geometry evidence are adverse priors; they do
  not blanket-veto a different entry geometry or information contract.
- Legal delta is joint and falsifiable: mandatory retest entry, materially
  wider ATR-buffered structural risk, and broker-bound tick-volume.
- ADX/session/HTF/RR/filter changes alone are forbidden rescues.

Default verdict is PARK/KILL unless the exact challenger proves both feasible
cadence and non-dead cost geometry without reading outcomes.

## 3. Hash-bound data and clock

- M1 bars:
  `02. AlphaFactory/data/fivepercent/EURUSD/EURUSD_M1_2015_now.parquet`
- Bars SHA256:
  `2959C555DB6690FD6EFD6CFB3B4C6323698E590C9B2D71E1E55F1902F724235A`
- Manifest SHA256:
  `2CD996FD4416B1E888BF1C9D272BF49056DB3A4CE477CF74FA4E31D474A41B54`
- Broker: `FivePercentOnline-Real (demo, read-only pull)`.
- Clock:
  `02. AlphaFactory/tools/research/fivepercent_server_clock.py`, SHA256
  `A7F179935102B57BA3B629345209F6B0D668D1F7FD828A5ED6003207F41A2F52`.
- Input is already normalized to `time_utc`; retain `time_server` and
  `utc_offset_h` in evidence.
- M1 development quality: 1,491,312 rows, 2019-01-02 through 2022-12-30,
  no duplicate UTC minute, tick volume nonzero on 100% of rows; `real_volume`
  is unusable.
- Historical spread is unusable as cost truth: 24.5553% zero rows.
- Development/design window: `2019-01-01 <= time_utc < 2023-01-01`.
- Holdout: `2023-01-01+`, sealed at parquet read time; required receipt
  `holdout_bars_loaded=0`.
- Resample M1 to UTC M5 with left-labelled, left-closed bins. Keep only bins
  with exactly five unique consecutive UTC minutes. Tick volume is summed.

## 4. Frozen Stage-0 decision surface

Indicator implementation:

- `atr_mt5(14)` and `adx_mt5(14)` from the neutral research SDK.
- Indicator SDK SHA256:
  `95EBEA3C2638E429136D189727097A201FF1ADE1164139161E857645E8EE1F1A`.
- Before any Model-0 survivor is trusted on the newly installed MT5 build 6061,
  indicator parity must be refreshed. Stage-0 remains a diagnostic screen.

Shared closed-bar swing and session rules:

- Bill Williams fractal strength `N=2`.
- A pivot at bar `p` becomes available only after bars `p+1` and `p+2` close.
  A sweep at `s` may use only a last confirmed pivot with `p <= s-3`.
- No pivot-age threshold.
- Long and short are symmetric.
- Reclaim may close inside on the sweep bar or exactly the next M5 bar.
- Session union by UTC decision-bar open: `07:00 <= hour < 21:00`.
- Friday entries at or after `16:00 UTC` are excluded as the report's frozen
  "Friday late" interpretation.
- Historical high-impact news gate is `UNMET` and OFF. Evidence must state this;
  no promotion can infer that news was filtered.

Matched control (geometry baseline):

- Sweep any distance beyond the last confirmed pivot and close back inside on
  the same bar.
- No ATR-depth, ADX, tick-volume, or retest gate.
- Entry proxy is the next complete M5 open.
- Initial stop is sweep extreme plus/minus a fixed `1.5`-pip buffer.
- No TP, MFE, MAE, return, label, or PnL is computed at Stage-0.

ASRS challenger:

- Sweep extreme exceeds the last confirmed pivot by at least
  `0.25 * ATR(14)` measured on the completed sweep bar.
- Reclaim closes inside on the sweep bar or exactly the next M5 bar.
- Sweep-bar tick volume is at least `1.50 * mean(tick_volume of the prior 20
  completed M5 bars)`; the sweep bar is not included in its baseline.
- `ADX(14) <= 25` on the completed reclaim decision bar.
- The immediately following complete M5 bar must retest the swept level and
  reject in the reversal direction:
  - Long: `low <= pivot`, `close > pivot`, and `close > open`.
  - Short: `high >= pivot`, `close < pivot`, and `close < open`.
- Entry proxy is the next complete M5 open after the retest decision.
- Initial stop is beyond the original sweep extreme by `0.30 * ATR(14)` from
  the completed sweep bar.
- Optional H1 bias is OFF. TP/RR, time stop, daily guard, trade risk, outcomes,
  and economics do not exist in Stage-0.

## 5. Trial accounting

- One deterministic Stage-0 configuration.
- Two funnel arms: matched tight control and full ASRS challenger.
- No parameter grid, symbol transfer, stochastic control, optimization, or
  alternative indicator formula.
- Diagnostic cost tiers are not trials: `0.5`, `1.5`, `2.25`, and `3.0` pip
  round-trip, all `UNVERIFIED_PROXY`.

## 6. Required funnel and geometry outputs

- M1 rows; complete/incomplete M5 bins; elapsed calendar weeks.
- Confirmed fractal highs/lows.
- Control same-bar sweep/reclaims and in-session entries.
- Challenger depth sweeps.
- Same/next-bar reclaims.
- ADX/session eligible count.
- Tick-volume eligible count and retention fraction.
- Mandatory retest/rejection entries.
- Candidates per elapsed calendar week at every stage.
- Initial risk in pips: count/min/p25/median/p75/max.
- Implied `cost_R = round_trip_pips / initial_risk_pips` at each proxy tier.
- Candidate counts by calendar year for concentration only; no outcomes.
- Exact attestations: no future-return/PnL/outcome columns, no holdout bars,
  no report/MT5 run, `promotion_eligible=false`.

## 7. Stage-0 gates

All must pass for `SURVIVE_STAGE0`:

1. Closed-bar, confirmed-fractal, prior-volume-baseline, and holdout-seal tests
   pass; `holdout_bars_loaded=0`.
2. Challenger has at least `1.0` final candidate per elapsed calendar week and
   at least `200` final candidates over the development window. This is only a
   Stage-0 floor; later registry promotion remains `2.0-5.0` trades/week.
3. Challenger median initial risk is at least `6.75` pips (1.5x the killed
   4.5-pip prior).
4. Challenger median `cost_R` at 1.5-pip round-trip is at most `0.20R`, and
   P75 `cost_R` is at most `0.30R`.
5. Tick-volume gate removes at least `20%` of pre-volume candidates. Its
   retained candidates must not be concentrated predominantly outside the
   frozen session (the full funnel computes the all-hours diagnostic before
   applying session).
6. No single calendar year supplies more than `40%` of final candidates.

Failing cadence is `PARK_STAGE0_CADENCE_INFEASIBLE_NO_OUTCOME_READ`. Failing
geometry is `KILL_STAGE0_COST_GEOMETRY_NOT_MATERIALLY_NEW`. Failing data/parity
is PARK/INVALID, not an economic verdict. "Almost passed" is fail.

## 8. Hard exclusions

- No PnL, PF, win rate, expectancy, MFE/MAE, forward label, outcome chart, or
  subgroup-return analysis.
- No 2023+ bar read.
- No N=3, ATR/sweep/volume/ADX/retest/RR/session/hour/day/year/direction tweak.
- No aggressive reclaim-close challenger, optional H1 bias, news fiction, or
  multi-symbol expansion.
- No MQL5, Model 0, promotion, paper/live attach, or schedule.

## 9. Required artifacts

- Synthetic red-first tests and passing test receipt.
- Package-specific Stage-0 scanner source hash.
- Hash-bound Stage-0 JSON and candidates CSV containing decision/geometry only.
- Trial log row carrying `hypothesis_id` and this plan SHA256.
- Readout and one terminal/probe registry transition after results.
- `hot.md`, `do_not_repeat_failures.md`, package README, shelf README, and INDEX
  updated only after the evidence verdict.

