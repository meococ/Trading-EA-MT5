# HYP-LOMX-MULTI-M1-001 — Frozen TRAIN Probe Plan

Status: **FROZEN BEFORE ANY ECONOMIC OUTPUT**  
Freeze date: 2026-07-30  
Owner scope: multi-instrument London-open research, backtest, logs, and charts; no live trading.  
Decision split opened by this plan: **TRAIN 2016-01-01 through 2020-12-31 only**.

## 1. Decision and mechanism

Test whether the sign of the exact London 08:00-to-08:30 broker-Bid move carries
directional information into one of three predeclared same-day exits.  This is a
transportability probe, not an optimization.  No indicator, volatility filter,
weekday filter, regime rule, formation threshold, stop, target, or parameter
search is permitted.

The external research prior is the abstract of Daniel Seeck, *London Opening
Price Momentum: A Systematic Intraday Trading Strategy* (SSRN 7008318, 2026),
which reports five of six instruments with same-sign behavior, GBPUSD with the
opposite sign, JPY amplification, and only USDJPY remaining profitable after
the author's stated cost assumptions.  The paper body was unavailable to the
team, so its detailed rules and results are not treated as reproduced facts.

Primary polarity is fixed before outcomes:

- EURUSD, EURJPY, USDJPY: continuation (`+1`).
- GBPUSD: paper-directed reversal (`-1`).
- XAUUSD: continuation external null only; it can never be selected.

## 2. Prior-failure radius and exclusions

Two prior exact USDJPY cells are terminal and cannot be rescued here:

- London formation -> 16:30 close (LOJM): gross PF 0.9077, cost-x1 PF 0.7930.
- London pre-fix sign -> 15:30/16:00 cell (LOFIX): gross PF 0.9606,
  cost-x1 PF 0.5945.

Therefore USDJPY is eligible only for `MIDDAY`.  USDJPY `LATE_FIX` and
`FULL_SESSION` are excluded before data access.  Asian-range/ORB families are
also outside this mechanism.  GBPJPY is excluded because broker coverage does
not span the requested 2016 start.  These exclusions are availability and
failure-radius decisions, not post-outcome vetoes.

## 3. Data and split firewall

- Broker/runtime: FivePercentOnline-Real, D-side portable MT5, trading disabled.
- Source: broker Bid M1 bars, exact IANA `Europe/London` local timestamps.
- Required opens per complete weekday: 08:00, 08:30, 12:00, 15:30, 16:00,
  16:30 London time.  No nearest-bar substitution or forward/back fill.
- Symbols requested by the source run: EURUSD, GBPUSD, USDJPY, EURJPY, XAUUSD.
- TRAIN: 2016-2020.  Only this split may be exported and evaluated now.
- Research validation: 2021-2024, sealed.  A fresh ID/plan/registry row is
  required before access and only a TRAIN survivor can open it.
- Holdout: every year 2025 through the then-current date, sealed.  A separate
  authorization is required after validation.
- Missing complete timestamp days are skipped, not imputed.
- Source gate per symbol: complete-date coverage >= 95% of calendar weekdays
  and positive historical-spread coverage >= 95%.
- Source and evidence must remain on `D:`.  `FILE_COMMON` is forbidden.

## 4. Causal rule and fixed sets

Formation sign is `sign(log(open_0830 / open_0800))`.  Exact zero formations are
skipped.  Positions use a next-decision-bar open and exit at a later exact open:

| Set | Entry | Exit |
|---|---:|---:|
| MIDDAY | 08:30 open | 12:00 open |
| LATE_FIX | 15:30 open | 16:00 open |
| FULL_SESSION | 08:30 open | 16:30 open |

Direction is `primary_polarity * formation_sign`.  One unit of simple price
return is recorded per complete day.  No overlapping position exists within an
arm.  There is no risk sizing or drawdown promotion claim at this probe stage.

## 5. Frozen arm matrix and multiplicity

Selectable primaries (`m=10` Holm family):

1. EURUSD x MIDDAY, LATE_FIX, FULL_SESSION.
2. GBPUSD x MIDDAY, LATE_FIX, FULL_SESSION.
3. EURJPY x MIDDAY, LATE_FIX, FULL_SESSION.
4. USDJPY x MIDDAY only.

Non-selectable but fully counted trials:

- XAUUSD continuation x all three sets: 3 external nulls.
- Exact polarity-reverse diagnostic for every selectable primary: 10 controls.

Total executed arms used by Deflated Sharpe Ratio: **23**.  Cost tiers are
stress levels, not extra trials.  Every arm, including failed controls/nulls,
stays in the accounting.

If more than one primary passes, selection is not by best observed PF.  The
pre-frozen causal-prior order is:

`USDJPY_MIDDAY`, `EURJPY_MIDDAY`, `EURJPY_LATE_FIX`,
`EURJPY_FULL_SESSION`, `GBPUSD_MIDDAY`, `GBPUSD_LATE_FIX`,
`GBPUSD_FULL_SESSION`, `EURUSD_MIDDAY`, `EURUSD_LATE_FIX`,
`EURUSD_FULL_SESSION`.

Only the first passing arm may become the one validation candidate; all other
passing arms are parked pending fresh Owner scope.

## 6. Cost contract

This probe uses a deliberately conservative but still **unverified research
proxy**, not promotion-grade execution cost:

`cost_x1_price = 1.25 * max(entry_spread_points, exit_spread_points) * point`

Stress tiers apply `x1`, `x1.5`, and `x2` to that value.  Historical broker
spread fields must be positive on >=95% of sampled endpoints.  Commission and
slippage are not asserted to be included.  Any survivor must obtain a
same-broker commission/slippage manifest and repeat the relevant gates before
Model 0 or promotion.

## 7. Frozen gates — all required for a TRAIN survivor

Structural gates per selectable primary:

- trades >= 1,000;
- cadence between 2.0 and 5.0 trades per elapsed calendar week;
- at least 200 positive and 200 negative formation signs;
- source/schema/hash/split gates all pass.

Economic and robustness gates per selectable primary:

- PF after x1 cost > 1.30;
- PF after x1.5 cost >= 1.25;
- PF after x2 cost >= 1.00;
- expectancy after x1 cost > 0;
- at least 4 of 5 TRAIN calendar years have positive net return;
- largest positive year's share of all positive-year net return <= 25%;
- PF after x1 cost remains > 1.00 in every leave-one-calendar-year-out slice;
- one-sided deterministic 5,000-draw sign-flip p-value, Holm adjusted across
  all 10 selectable primaries, <= 0.05;
- canonical DSR >= 0.95, using variance of Sharpe across all 23 executed arms;
- beats its exact reverse control on both PF x1 and expectancy x1.

No single gate may be waived.  `PF=inf`/undefined, zero loss, missing year,
invalid source, missing spread, or insufficient observations is a failure, not
a pass.

## 8. Terminal decisions

- No primary passes every gate -> `TRAIN_KILL_NO_ELIGIBLE_ARM`; do not read
  2021+, do not build MQL5, do not run Model 0, and write the failure radius.
- At least one passes -> `TRAIN_PASS_ONE_VALIDATION_CANDIDATE`; choose exactly
  one by the frozen priority.  This is not economic validation, deployment, or
  completion.  Open 2021-2024 only through a fresh hypothesis ID and plan.
- XAUUSD or a reverse control can never become a survivor regardless of result.

The workspace goal remains UNMET until independent TRAIN, validation, and
holdout evidence satisfy the goal contract with verified costs.

## 9. Frozen implementation and evidence contract

Implementation hashes at freeze:

- `export_lomx_001_train_source.py`:
  `28084C487B89687B50F2583E893E09F7C13A678057C72E5D872C0C784A6FD31D`
- `evaluate_lomx_001_train.py`:
  `50B77CFE8B527A871FBE5C2AA04FACD1923215F2AB75887D786AD823D387AA35`
- `tests/test_export_lomx_001_train_source.py`:
  `7DC533E01A1EBEB73FEC0130841255BA067914272B5850A282492DA233E8EDAC`
- `tests/test_evaluate_lomx_001_train.py`:
  `0192622BE0B3E2DA035FD6DBEF2AE9AC84EB62D048F4201161E48916926E20CF`

Pre-freeze test command and result: focused `pytest`, **11 passed**.

The source run is outcome-blind and writes one hash-bound parquet/manifest plus
a receipt.  A later registry row must independently bind those hashes before it
can authorize economics.  The evaluator writes trades, metrics, a terminal
packet, a log, an artifact manifest, and five charts.  Both runs are one-shot;
an existing output directory is fatal.  Registry latest-row SHA is supplied at
runtime and must match the frozen authority row exactly.

Team review note: a bounded Grok forensic worker advised the multi-instrument
transportability framing, XAU external-null role, and exclusion of the two
killed USDJPY cells.  Its result packet did not pass the local result validator,
so it is advisory only; the Lead Quant independently rechecked and froze every
rule above.  No worker output is an execution authority.
