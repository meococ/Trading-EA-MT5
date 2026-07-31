# PROBE PLAN — HYP-EVENT-CLOB-PERSIST-EURUSD-M1-001

Status: FROZEN 2026-07-28, before any CME event-window download, feature
extraction, EURUSD forward return, PnL, MFE, MAE, PF or expectancy of this
object was computed. This file is immutable after its SHA-256 is entered in
the candidate registry. Any pre-outcome amendment requires `_V2`; any
post-outcome change requires a new hypothesis ID.

## 1. Identity

- Hypothesis ID: `HYP-EVENT-CLOB-PERSIST-EURUSD-M1-001`.
- Research package: `EA_EventCLOBPersistence`; no `.mq5`, compile, Model 0 or
  trading action is authorized at this stage.
- Owner scope: 2026-07-28 request to form a Codex-only research/build team and
  pursue a new or old mechanism end to end. Paid source acquisition still
  requires a separate explicit USD ceiling.
- Instrument / decision frame: CME Globex Euro FX futures `6E` MBP-10 as the
  source venue; FivePercent `EURUSD` M1 as the later execution venue.
- Thesis: scheduled point releases create a short price-discovery interval. A
  late, persistent top-five 6E book imbalance that agrees with its pre/post
  change may contain direction information not present in the first EURUSD M1
  return alone. This is a falsifiable mechanism prior, not an edge claim.
- Primary evidence prior:
  - Federal Reserve research finds a strong high-frequency association between
    FX order flow and returns, weaker at longer horizons:
    https://www.federalreserve.gov/pubs/ifdp/2005/830/default.htm
  - A Federal Reserve EBS study documents an immediate price jump followed by
    a surge in trading volume roughly 15 seconds after a large release:
    https://www.federalreserve.gov/pubs/ifdp/2007/903/ifdp903.htm
  - CME states MBP consolidates quantity/order count at no more than the top 10
    price levels and does not reveal individual queue position:
    https://www.cmegroup.com/articles/faqs/market-by-order-mbo.html
  - Databento documents MBP-10 as every trade/book update at the top 10 levels,
    including aggregate depth, not individual queue position:
    https://databento.com/docs/schemas-and-data-formats/cmbp-1

## 2. De-dup and adverse priors

- Checked `04. Memory/do_not_repeat_failures.md`, the full candidate registry,
  the active shelf and current `hot.md`.
- Distinct from terminal post-news price momentum: challenger direction comes
  only from decision-time 6E book persistence; first-M1 price direction is the
  matched control and can never become the challenger.
- Distinct from killed raw-BREAK book lanes: population identity is the frozen
  external point-release clock, not a price-break event; no score percentile,
  management edit, old outcome subgroup or prior raw-BREAK DBN file is reused.
- Distinct from ECRS: there is no ER/ATR-compression/range-breakout/EMA stack or
  session rescue. The ECRS off-session opening is rejected before this freeze:
  only 94 core events at 22:00–00:00 UTC over 208.7143 weeks (0.4504/week),
  below the 2/week goal floor without reading outcomes.
- Adverse priors: public information may be fully absorbed before the next M1
  open; aggregate depth can be canceled/spoofed; CME futures and retail spot
  may desynchronize; release-time spread/slippage can dominate; source-rank C
  calendar clocks cannot support promotion.

## 3. Hash-bound data and source boundary

- Source-C diagnostic calendar:
  `02. AlphaFactory/data/forexfactory/EURUSD/news_events/forexfactory_high_impact_eurusd_2019_2022.csv`,
  SHA-256 `80B9DE46517B42F8B1D9A3ACCEFA6CC6D3DCB4DD06CAE357F16DE46228C64307`.
- Outcome-blind event clock:
  `03. EA Developer/EA_EventCLOBPersistence/research/source/point_release_clocks_2019_2022.csv`,
  SHA-256 `5C30F99FF0E1341D680C2747315E2FF4DFF99C5FBE01C2C5C4036BC101375E7B`.
- Clock manifest:
  `03. EA Developer/EA_EventCLOBPersistence/research/source/point_release_clock_manifest.json`,
  SHA-256 `B61CDFA6DCAE82308E4CD2A60DAFF195C297FD8523D41CDCA0788694657AC636`.
- Calendar transform excludes names matching
  `(speaks|testifies|press conference)` and groups remaining rows by exact UTC
  timestamp. Result: 630 point-release clocks; 329 in 2019–2020 and 301 in
  2021–2022; raw clock supply 3.01848/week. No price/outcome was opened.
- Required paid source: fresh Databento `GLBX.MDP3`, schema `mbp-10`, continuous
  symbol `6E.v.0`, one `[-60s,+60s)` window for each of the 630 frozen clocks,
  persisted only under `02. AlphaFactory/data/databento/cme_6e_event_clob/`.
  Metadata/symbology/cost quotes are free; time-series download is prohibited
  until Owner supplies an explicit ceiling. Databento documents metadata access
  and `metadata.get_cost` as free:
  https://databento.com/docs/api-reference-historical/basics/authentication
- Existing raw-BREAK DBN corpora may be opened only by tests that prove schema
  decoding; they are forbidden from feature, economics or outcome rows here.
- EURUSD bars: canonical FivePercent M1 parquet, design only 2019-01-01 through
  2022-12-31. The 2023+ holdout stays sealed with zero bars loaded.
- Historical spread has 24.5553% zero rows and is not verified cost truth.
  Any offline economics is diagnostic-only under the fixed proxy below.

## 4. Frozen decision surface

One challenger, one matched control, no parameter grid and no optimization.

### Challenger: EVENT_CLOB_PERSISTENCE

- For event clock `T`, decode MBP-10 by matching-engine `ts_event`.
- At every book record, calculate top-five aggregate imbalance
  `I5=(sum(bid_sz_00..04)-sum(ask_sz_00..04)) /
  (sum(bid_sz_00..04)+sum(ask_sz_00..04))`.
- `I5_pre = median(I5)` over `[T-60s,T-15s)`.
- `I5_late = median(I5)` over `[T+45s,T+60s)`.
- `delta_I5 = I5_late - I5_pre`.
- Source-quality qualifiers, fixed before outcomes:
  - at least 30 causal MBP records in each pre and late segment;
  - last record in each segment no more than 1.0 second from its segment end;
  - no gap between consecutive records in either segment exceeds 1.0 second;
  - median late best-ask minus best-bid is at most two 6E ticks;
  - finite nonzero depth denominator in every record used;
  - `sign(I5_late) == sign(delta_I5)` and neither value is zero.
- Direction: long EURUSD if the common sign is positive; short if negative.
- Closed-bar execution: compute only after `[T,T+60s)` is complete; enter at
  the first EURUSD M1 open at or after `T+60s`. Equal-clock fill is allowed only
  when the source window is already complete and persisted.
- Risk reference: `ATR30` uses the 30 fully closed EURUSD M1 bars ending before
  `T`; no indicator is a direction filter. Long SL is event-bar low minus
  `0.25*ATR30`; short SL is event-bar high plus `0.25*ATR30`.
- No TP, break-even, trailing, scale-in or scale-out. Exit at the first quote at
  or after 15 elapsed minutes, or earlier at the hard SL. One position per
  event clock; overlapping clocks are grouped and never create multiple trades.
- Research risk for later Model 0: 0.10% of balance per trade, daily loss stop
  0.50%, account DD stop 6%, no overnight/weekend holding.

### Matched control

- Same exact eligible event population, entry time, risk geometry, cost tiers
  and exits. Direction is `sign(close[T,T+60)-open[T,T+60))` of the first
  completed EURUSD M1 event bar. Zero-return clocks are skipped in both arms.
- The control is a benchmark only; it cannot be selected as a survivor or used
  to reopen the terminal standalone post-news momentum family.

### Cost and fill boundary

- Offline proxy x1: 3.0 pips round trip; x1.5: 4.5 pips; x2: 6.0 pips.
  Status is `UNVERIFIED_EVENT_PROXY`; it is never described as broker truth.
- Entry/SL/time-exit uses conservative M1 path ordering; if SL and time exit are
  both reachable without tick order, SL is first. Model 0 direct ticks are
  mandatory for any later survivor.

## 5. Trial accounting and deflation

- Full trial universe N=2: one matched price control plus one CLOB challenger.
  Cost tiers are not separate trials. No other threshold/session/exit arm may
  be run under this ID.
- DSR uses per-trade net-R, skew, non-excess kurtosis and both arms; floor 0.95.
  A searched split is diagnostic; 2023+ is the only true sealed holdout.

## 6. Sequential stages and fatal gates

Every gate is required; “almost passed” is fail/park as declared.

### Stage 0A — outcome-blind clock supply (already executed)

| Gate | Threshold | Frozen result |
|---|---:|---:|
| Total point clocks | >=418 | 630 PASS |
| 2019–2020 clocks | >=209 | 329 PASS |
| 2021–2022 clocks | >=209 | 301 PASS |
| Raw clock cadence | 2.0–5.0/week | 3.01848 PASS |

### Stage 0B — fresh source coverage, before price outcomes

- Raw source files hash/DBN validation: 100% of requested windows represented
  by a nonempty file or an explicit metadata/source-empty receipt.
- Nonempty MBP coverage >=99% overall and in each two-year split.
- Final source-quality eligible population >=418 total, >=209 in each split and
  2.0–5.0 events per elapsed week overall and per split. Failure is
  `PARK_STAGE0_SOURCE_OR_CADENCE`; no EURUSD outcome is opened.
- Clock/window mismatch >1 second, unknown instrument mapping, duplicate event
  ID, non-monotonic `ts_event`, or any read of 2023+ is data-invalid, not no-edge.

### Stage 1 — design economics, 2019–2020 only

- Minimum observations: 209 completed eligible trades in each arm.
- Predeclared sequential fatal boundary: calendar-week block bootstrap,
  one-sided 95% upper confidence bound of challenger mean net-R at x1 cost. If
  UCB < 0 after N>=209, KILL immediately; validation remains unopened.
- Otherwise challenger must independently pass: net PF x1 >=1.30; PF x1.5
  >=1.25; PF x2 >=1.00; mean net-R >=+0.08/trade; positive net R; max DD <=6%;
  DSR >=0.95; and improve over control in both mean net-R and net-R/max-DD.

### Stage 2 — fixed validation, 2021–2022

- Same minimum N and every absolute/relative Stage-1 gate, unchanged. Both
  calendar years must have positive net R; no one month may contribute >20% of
  positive-month profit.
- Failure is terminal KILL for this exact object. No event-name, hour, currency,
  direction, spread, imbalance magnitude, stop or exit subgroup rescue.

### Stage 3 — build and Model 0 (survivor only)

- Require official point-in-time event clock provenance and verified
  same-broker event execution cost before promotion-eligible testing.
- Build source only after Stage 1+2 survive; then red-first contract tests,
  closed-bar/non-repaint audit, AlphaFactory compile, matched Model-0 control and
  challenger, log triage, report/lifecycle/RunMeta reconciliation, cost stress,
  WFA/robustness/Monte Carlo and Heavy-Delivery chart anatomy.
- 2023+ may be opened only once after all prior gates pass. Confirmed status
  still requires the workspace 84-month/14-half-year/7-year evidence surface;
  the current four-year diagnostic source can at most reach challenger status.

## 7. Hard exclusions

- No post-hoc event type, country, hour, weekday, year, direction, `I5` magnitude,
  percentile, spread, staleness, ATR, RR, TP, BE or holding-time edit.
- No old raw-BREAK outcome join, old DBN economics, same-ID management rescue,
  2023+ peek, optimization, live/paper trade or automatic data schedule.
- Aggregate MBP depth is not queue position, causal trade side or proof of
  spoof-free demand. Reports must retain this limitation.

## 8. Required artifacts

- Frozen plan and registry row with matching SHA-256.
- Hash-bound source clock CSV/manifest, acquisition plan, free quote receipt,
  Owner ceiling, raw download manifest and DBN validation.
- Stage-0 source feature manifest with no outcome fields.
- If authorized, separate outcome probe JSON, trade ledgers for both arms,
  `trials/trial_log.jsonl`, DSR/cost/regime outputs and readout.
- Terminal loser: Fast-Kill packet. Survivor: source/task/capability packet,
  compile/non-repaint receipts, Model-0 artifacts, log triage, decision-as-of and
  anatomy chart manifests, and Heavy-Delivery PASS.
