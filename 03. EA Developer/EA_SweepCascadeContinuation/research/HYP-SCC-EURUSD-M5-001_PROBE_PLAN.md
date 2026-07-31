# HYP-SCC-EURUSD-M5-001 — Frozen outcome-blind Stage-0 probe plan

Status: **FROZEN PRE-IMPLEMENTATION / PRE-COUNT / PRE-OUTCOME / PRE-SOURCE**  
Frozen: `2026-07-25T13:03:45Z`  
Package if and only if every Stage-0 gate passes:
`EA_SweepCascadeContinuation`

This V1 plan is immutable once its SHA256 is appended to the canonical
registry. A pre-outcome correction requires `_V2.md` and a new legal transition.
Any change after Stage-0 counts requires a new hypothesis ID.

## 1. Identity and falsifiable claim

- Hypothesis: `HYP-SCC-EURUSD-M5-001`
- Symbol/timeframe: `EURUSD` / closed `M5`
- Feature family:
  `confirmed-fractal-close-break-hold-retest-first-passage-continuation`
- Question: can the first confirmed swing-level close-break of a UTC day retain
  enough accepted retest events, directional balance and cost-feasible initial
  geometry to justify one matched economic build?
- Causal prior: documented FX stop-loss positive feedback can propagate trends
  for hours:
  <https://www.newyorkfed.org/research/staff_reports/sr150.html>.
- Proxy limitation: OHLC cannot observe dealer stops, signed order flow or a
  centralized FX book. A PASS would establish operational feasibility only.

Stage-0 may not load, calculate, join, display or retain any trade outcome,
future return, MFE, MAE, exit, target/stop hit, PnL, PF, win rate, expectancy,
balance, equity or drawdown.

## 2. De-dup and adverse priors

Canonical legality memo:
`04. Memory/research/20260725_SCC_DEDUP_READOUT.md`.

- `HYP-ASRS-EURUSD-M5-001`: opposite fade direction plus volume/session/ADX;
  SCC requires accepted breakaway continuation.
- `HYP-ICT-FVG-CONTEXT-STATE-EURUSD-M5-012` and
  `HYP-ICT-FVG-HUMAN-CONTEXT-POLICY-EURUSD-M5-017`: reclaim-reversal context
  failed; SCC cannot import their subgroups or use their failure as evidence.
- `HYP-VRAS-EURUSD-M5-004`: one-bar rolling-VWAP path confirmation failed;
  SCC uses consumed confirmed-pivot BREAK→HOLD→RETEST state.
- `HYP-VRAS-EURUSD-M5-011`: similar categorical first passage but a different
  rolling-VWAP reclaim object; no thresholds or identities are reused.
- `HYP-ECRS-EURUSD-M5-002`: compression-release object was cadence-infeasible;
  SCC contains no compression, ER, volume, session or bias gate.

Adverse prior is strong. Default verdict is PARK. No result from another family
is treated as SCC edge evidence.

## 3. Exact hash-bound data and seal

- Manifest:
  `02. AlphaFactory/data/fivepercent/EURUSD/manifest.json`
  - SHA256:
    `2CD996FD4416B1E888BF1C9D272BF49056DB3A4CE477CF74FA4E31D474A41B54`
- Closed bid M1:
  `02. AlphaFactory/data/fivepercent/EURUSD/EURUSD_M1_2015_now.parquet`
  - SHA256:
    `2959C555DB6690FD6EFD6CFB3B4C6323698E590C9B2D71E1E55F1902F724235A`
- Server clock:
  `02. AlphaFactory/tools/research/fivepercent_server_clock.py`
  - SHA256:
    `A7F179935102B57BA3B629345209F6B0D668D1F7FD828A5ED6003207F41A2F52`
- Broker: `FivePercentOnline-Real (demo, read-only pull)`
- Design rows: UTC `2019-01-01 00:00:00` inclusive through
  `2023-01-01 00:00:00` exclusive.
- Holdout: UTC `2023-01-01` onward, sealed at parquet read; required
  `holdout_bars_loaded=0`.
- Historical spread is not cost truth: 24.5553% of 2019–2022 M1 rows report
  zero spread. Stage-0 uses declared round-trip cost geometry only:
  `0.5 / 1.5 / 2.25 / 3.0` pips, status `UNVERIFIED_PROXY`.

## 4. M1→M5 and indicator contract

1. UTC M1 timestamps must be unique, minute-aligned and sorted.
2. An M5 bucket is left-labelled at minute `00|05|...` and is valid only with
   exactly five unique offsets `0,1,2,3,4`. Partial/duplicate/misaligned bins
   are discarded and counted.
3. Any consecutive retained M5 opens not exactly five minutes apart are a gap.
   A gap kills active state before the next bar is evaluated; the first bar
   after a gap cannot BREAK because its predecessor is not contiguous.
4. OHLC aggregation: first open, maximum high, minimum low, last close; tick
   volume is summed but never used by SCC.
5. `ATR14_MT5` uses `tools/research/indicators.py::atr_mt5`, the parity-proven
   simple mean of true range. Retest geometry uses ATR on the completed RETEST
   decision bar; it is known at that close and maps to MQL5 `iATR` shift 1 when
   the next bar begins.

## 5. Confirmed pivot stream

Classic strict Williams-style N=2 pivots on completed M5:

- pivot high at `p`: `high[p]` is strictly greater than highs at
  `p-2,p-1,p+1,p+2`;
- pivot low mirrors with strictly lower lows;
- the level may be used by BREAK bar `b` only when it was known before `b`
  opened: `p <= b-3`;
- latest confirmed pivot high is eligible only for LONG close-break;
- latest confirmed pivot low is eligible only for SHORT close-break.

Pivot identity contains side, extreme index/time, price, confirmation
index/time, BREAK arm index/time and terminal reason. A pivot is consumed at its
first BREAK arm attempt regardless of HOLD/RETEST result and is never reused.
A newly confirmed pivot may replace an older unconsumed same-side pivot before
arm. No pivot changes after a candidate arms.

## 6. Frozen SCC state machine

Long/short mirror exactly. Only one candidate may be active. Only the first
valid BREAK arm attempt of each UTC date is allowed; after that arm, no later
pivot may arm that date regardless of accept/reject/expire.

### WAIT → BREAK

Using a level known before the BREAK bar opened:

- LONG: previous contiguous completed close `<= pivot_high` and current
  completed close `> pivot_high`;
- SHORT: previous close `>= pivot_low` and current close `< pivot_low`;
- wick-only crossing without the required close does not arm;
- if long and short conditions somehow both occur, reject the bar as ambiguous
  and consume neither pivot;
- freeze pivot and BREAK OHLC/ATR identity; consume the pivot; mark the UTC date
  as attempted.

### BREAK → HOLD

The immediately next retained M5 bar must:

- open exactly five minutes after BREAK;
- share the BREAK UTC date;
- close strictly beyond the pivot in the continuation direction.

Failure yields `REJECT_HOLD`, closes state and ends that UTC date's opportunity.
HOLD cannot enter.

### HOLD → RETEST first passage

Evaluate the next at most 12 contiguous completed M5 bars, with passage lag
`1..12`. Before price logic:

1. non-contiguous open time → `REJECT_GAP`;
2. UTC date differs from BREAK UTC date → `REJECT_DAY_BOUNDARY`.

For each otherwise valid passage bar, freeze this exact priority:

1. LONG close `<= pivot_high` or SHORT close `>= pivot_low`
   → `REJECT_CLOSE_INSIDE`;
2. else LONG low `<= pivot_high` and close `> pivot_high`, or SHORT high
   `>= pivot_low` and close `< pivot_low`
   → `ACCEPT_RETEST`;
3. else if this is passage lag 12 → `EXPIRE_12`;
4. else remain active.

No bar can receive two labels. An accepted decision timestamp is the RETEST
bar's close. Any future EA order may occur no earlier than the next M5
open/first tick.

## 7. Stage-0 geometry and structural control

For an accepted RETEST only:

- hypothetical next-bar entry reference: next contiguous M5 open, provided it
  shares the UTC date; otherwise label `ENTRY_REFERENCE_UNAVAILABLE` and fail
  the corresponding integrity gate;
- LONG stop reference:
  `min(BREAK.low,HOLD.low,RETEST.low) - 0.25*ATR14_MT5(RETEST)`;
- SHORT stop reference:
  `max(BREAK.high,HOLD.high,RETEST.high) + 0.25*ATR14_MT5(RETEST)`;
- record initial distance in pips and cost-in-R at the four declared proxy
  costs. This is decision-time geometry, not a simulated trade.

Structural control is the exact first BREAK arm attempt of each UTC day from the
same pivot/data stream. Treatment must be a strict subset of those control
origin IDs. Control stores no hypothetical exit or outcome.

## 8. Mandatory Stage-0 outputs

- exact plan/manifest/M1/clock/scanner/test hashes and seal receipt;
- M1/M5 completeness/gap counts;
- confirmed pivot highs/lows, superseded/armed/consumed/reused counts;
- raw BREAK, HOLD pass/fail, RETEST accept, close-inside, expiry, gap and
  day-boundary counts;
- control and accepted event ledger with decision-time fields only;
- pooled and per-year elapsed-calendar-week cadence;
- long/short counts, passage-lag distribution and blocked-by-daily-cap counts;
- initial-risk and declared cost-in-R distributions;
- deterministic replay SHA: a second internal scan must emit byte-identical
  retained ledger bytes;
- forbidden-outcome-column/token audit.

## 9. Necessary Stage-0 gates — all must pass

1. Every declared hash matches; holdout rows loaded `=0`.
2. Deterministic replay ledgers are byte-identical.
3. No pivot is used before confirmation or more than once; ambiguous labels
   `=0`; treatment origin IDs are a strict subset of control arm IDs.
4. Accepted events `>=418`.
5. Accepted cadence is `2.00..5.00` per elapsed calendar week pooled and
   separately in 2019, 2020, 2021 and 2022.
6. LONG and SHORT accepted counts are each `>=100`.
7. Maximum single-year accepted-event share `<=35%`.
8. At least `20%` of accepted events resolve at passage lag `>=2`, proving the
   contest is not only a fixed immediate-retest rewrite.
9. Median initial risk `>=7.50` pips and p25 risk `>=5.00` pips.
10. At 1.5-pip RT proxy, median cost-in-R `<=0.20R` and p75 `<=0.30R`.
11. Accepted next-bar entry references are contiguous, same-date and available
    for `100%` of accepted rows.
12. Forbidden outcome columns/tokens `=0`; no price bar after the entry
    reference is read.

Any failure yields
`PARK_STAGE0_REQUIRED_GATE_FAIL_NO_OUTCOME_READ`. No `.mq5`, compile, Model 0,
economics or V1 amendment is authorized.

## 10. Conditional boundary after a complete PASS

A complete PASS authorizes only:

1. a separate frozen economic preregistration and logic-to-code matrix;
2. red-first MQL5 tests, exact-source non-repaint audit and compile;
3. one matched Model-0 control/challenger pair only after registry authorization.

The 2019–2022 window is discovery-tainted by prior workspace research.
Historical SCC economics would remain diagnostic and
`promotion_eligible=false`; independent promotion requires untouched future or
independent data. No paper/live attachment is authorized.

## 11. Hard exclusions

- No change to N=2, 12 bars, one arm/day, direction, gap/day rule, priority,
  pivot consumption, 0.25 ATR buffer, cost proxies or gates after counts.
- No ADX, volume, session, news, HTF, FVG, weekday/hour, score, RR, stop or
  symbol/timeframe rescue.
- No ASRS fade fallback and no subgroup veto from this readout.
- No grid/optimization. Trial universe is one Stage-0 scanner configuration;
  structural control is identity-only and does not receive an outcome.

