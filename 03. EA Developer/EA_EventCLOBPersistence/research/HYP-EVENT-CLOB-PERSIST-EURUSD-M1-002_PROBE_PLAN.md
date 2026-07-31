# PROBE PLAN — HYP-EVENT-CLOB-PERSIST-EURUSD-M1-002

Status: FROZEN 2026-07-28 before any paid CME time-series request, DBN file,
EURUSD price outcome, PnL, MFE, MAE, PF, expectancy, `.mq5` or MT5 run for this
hypothesis.

This is a pre-outcome engineering successor to
`HYP-EVENT-CLOB-PERSIST-EURUSD-M1-001`, which remains parked for payment
authority with no market verdict. The market mechanism, feature formulas,
matched control, risk model, cost tiers, economic gates, trial count and
holdout discipline are identical to the parent plan at SHA-256
`D47615E32F1E374D3CBFB23EA2DD9ABF594A85F2E22BF1C3CD5B08D60B6F5011`.
The new identity exists because the canonical registry correctly forbids
changing a frozen source/data contract after the parent left `idea`.

No parent outcome exists to rescue. Parent V1 and immutable
`FREE_QUOTE_F8CC5869` evidence stay byte-exact historical records and grant no
paid authority.

## 1. Mechanism and falsifiable claim

Scheduled point releases can create a short-lived disagreement between the
first EURUSD event-bar direction and persistent late CME 6E top-five book
imbalance. The challenger trades only when late imbalance and its change from
the pre-event baseline have the same finite nonzero sign. It must beat the
matched first-event-bar direction control after frozen event-cost proxies.

This plan deliberately avoids indicator voting. CME 6E MBP-10 imbalance is the
only signal. EURUSD ATR30 is risk-only. Calendar time supplies the event clock.

## 2. Frozen clock and design-only source contract

- Clock file: `research/source/point_release_clocks_2019_2022.csv`.
- Clock SHA-256:
  `5C30F99FF0E1341D680C2747315E2FF4DFF99C5FBE01C2C5C4036BC101375E7B`.
- Design selection: exactly the 329 clocks with UTC year 2019 or 2020.
- Elapsed design weeks: `104.428571`; raw cadence:
  `329 / 104.428571 = 3.15048` events/week.
- For each event clock `T`, request exactly two half-open ranges:
  1. `PRE`: `[T-60s,T-15s)` (45 seconds);
  2. `LATE`: `[T+45s,T+60s)` (15 seconds).
- Exactly 658 request identities, keyed by `(event_clock_id, segment)`.
- Total requested duration: exactly 19,740 seconds.
- Dataset: Databento `GLBX.MDP3`; schema `mbp-10`; symbol `6E.v.0`;
  `stype_in=continuous`; `stype_out=instrument_id`.
- Storage root:
  `02. AlphaFactory/data/databento/cme_6e_event_clob_design_segments/`.
- Filenames must encode event ID, segment and exact UTC bounds.
- Do not request `[T-15s,T+45s)`, any 2021–2022 source, any 2023+ row or any
  EURUSD price/outcome in the source acquisition lane.

The old full-window quote, billable sizes and per-window costs are forbidden
from feature construction, sampling, thresholds, gates or outcome inference.
They are historical operational evidence only.

## 3. Frozen feature and signal

For each causal MBP-10 record:

`I5=(sum(bid_sz_00..04)-sum(ask_sz_00..04)) /
(sum(bid_sz_00..04)+sum(ask_sz_00..04))`.

- `I5_pre = median(I5)` over PRE.
- `I5_late = median(I5)` over LATE.
- `delta_I5 = I5_late - I5_pre`.
- Challenger direction is eligible only when `sign(I5_late)` equals
  `sign(delta_I5)` and both values are finite and nonzero.

Each segment independently requires at least 30 records, finite nonzero
denominators, monotonic `ts_event`, known exact instrument mapping, final-record
staleness no more than one second, and maximum consecutive gap no more than one
second. LATE median spread must be no more than two 6E ticks. No middle-window
field or statistic is allowed.

## 4. Frozen EURUSD execution, control and risk

- Entry: next EURUSD M1 open at or after `T+60s`.
- Challenger direction: the eligible persistent 6E imbalance sign.
- Matched control: direction of the first completed EURUSD M1 event bar.
- ATR30: pre-event closed bars only; risk sizing and stop geometry only.
- Stop: event extreme plus `0.25 * ATR30` buffer.
- Exit: 15-minute time exit; no TP, break-even or trailing stop.
- Research risk: 0.10% per trade.
- Frozen round-trip cost proxies: 3.0, 4.5 and 6.0 pips; these are event-cost
  proxies, not verified broker costs.
- Trials: exactly two, challenger and matched control. No grid, optimization,
  subgroup rescue or post-outcome threshold change.

## 5. Stage 0B-D — design source gate

No EURUSD outcome may be opened until all conditions pass:

- a free quote covers all 658 canonical request identities and reconciles
  plan, receipt, hashes and every actual free metadata attempt;
- a positive Owner-approved USD ceiling is bound to the exact quoted plan and
  a live re-quote is not above that ceiling before download;
- every event has both identities represented by a validated nonempty full-DBN
  file or explicit charged/source-empty evidence;
- PRE nonempty coverage >=99%, LATE nonempty coverage >=99%, and paired
  nonempty-event coverage >=99%;
- paired source-quality eligible events >=209;
- eligible cadence is 2.0–5.0 per 104.428571 elapsed weeks;
- no duplicate identity, noncanonical bound, unknown instrument, nonmonotonic
  `ts_event`, unmanifested file, hash mismatch, unresolved paid request,
  2021–2022 source row or EURUSD outcome read exists.

Failure verdict: `PARK_STAGE0B_DESIGN_SOURCE_OR_CADENCE`. This is not a market
no-edge verdict. No source-quality threshold, segment bound or population
subgroup may change under this ID.

## 6. Stage 1 design economics

After Stage 0B-D PASS, freeze the design feature ledger without outcomes. Only
then may the 2019–2020 EURUSD outcomes be opened.

The unchanged gates are:

- at least 209 eligible trades and elapsed cadence 2.0–5.0 trades/week;
- challenger profit factor >=1.30 at 3.0 pips;
- challenger profit factor >=1.25 at 4.5 pips and >=1.00 at 6.0 pips;
- positive mean net R at all three cost tiers;
- max drawdown <=6%;
- calendar-week block-bootstrap one-sided 95% upper confidence bound of mean
  net R must be >=0 after N>=209; below zero is a frozen fatal kill;
- challenger must improve on the matched control in mean net R and cost
  resilience without relying on one event family or one calendar block;
- DSR and regime/execution diagnostics must not reveal trial-selection or
  concentration failure.

Stage-1 failure is a terminal design KILL. Do not buy validation source and do
not rescue the candidate under this ID.

## 7. Validation and holdout sequencing

Only a full Stage-1 survivor may freeze a new pre-outcome validation-source
packet for the 301 clocks in 2021–2022 using the same PRE/LATE request contract.
Validation source unavailability, unacceptable price or source-gate failure is
`PARK_SOURCE_VALIDATION_UNAVAILABLE`, not a survivor and not permission to tune
design. Stage 2 uses the same frozen feature, execution, control, risk, costs
and gates. Data from 2023 onward remains sealed until all earlier gates pass.

No `.mq5`, compile, Model 0, chart campaign, promotion, paper or live trading is
authorized until both design and validation economics survive their gates.

## 8. Current authority

This plan authorizes only deterministic offline planning, source-tool/test
work, and a free metadata quote for the 658 design requests. It authorizes no
paid time-series request, no EURUSD outcome access and no Git action.

Before any paid request, require:

- a canonical registry transition binding this exact file and hash;
- a source task packet with hashes, write-set and remote allow/deny list;
- a deterministic 658-identity acquisition plan;
- a validated free quote receipt counting every actual free attempt;
- an immutable predownload storage assessment; and
- an explicit Owner ceiling bound to that exact plan.

A later paid tool must retain exclusive lock, exact-once `in_flight` journal,
no automatic paid retry, full DBN/hash/resume validation, canonical registry
validation and immutable evidence snapshots from the parent V9 controls.
