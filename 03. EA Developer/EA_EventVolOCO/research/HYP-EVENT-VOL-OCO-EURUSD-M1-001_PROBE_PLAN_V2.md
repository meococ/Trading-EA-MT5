# HYP-EVENT-VOL-OCO-EURUSD-M1-001 — Frozen Probe Plan V2

Status: `FROZEN_PENDING_INDEPENDENT_REVIEW_AND_REGISTRY`  
Package: `EA_EventVolOCO`  
Symbol / timeframe: `EURUSD / M1`  
DESIGN window: `2019-01-01T00:00:00Z <= T < 2021-01-01T00:00:00Z`  
Evidence class for this run: `OUTCOME_BLIND_SOURCE_AND_GEOMETRY_FEASIBILITY_ONLY`

Amendment chain: this create-new V2 supersedes immutable V1 before any source or
economic run. V1 remains preserved at
`HYP-EVENT-VOL-OCO-EURUSD-M1-001_PROBE_PLAN.md` with SHA256
`AA940E556D741625AEBF219565B9667965D7D6F9122C9E790350A78AA6E3510A`.
No source-feasibility run occurred under V1 and its temporary invalid registry
row was removed, restoring the prior registry SHA and validator state. The later
execution-fidelity correction below is the only contract change. The registry
must bind both this V2 SHA and the superseded V1 SHA before execution. This plan
alone grants no run authority: an independent pre-run review and a matching
valid pre-source registry row are required first.

## 1. Decision objective and evidence boundary

This ID asks only whether a clean scheduled-event clock and the public EURUSD
DESIGN corpus can support the frozen pre-event OCO geometry at sufficient
coverage, cadence and planned-risk scale. The authorized run may read pre-event
OHLC only for the frozen box and ATR inputs. At and after `T`, it may read only
`time_utc` to prove timestamp coverage.

This run must not read or calculate future/post-`T` OHLC, spread, volume,
direction, return, PnL, MFE, MAE, win rate, profit factor, trade outcome or any
economic statistic. It must not open validation, holdout or private/sealed
custody; launch MT5; create MQL5; make network or paid calls; optimize; or make a
promotion claim. A PASS is diagnostic source feasibility only and grants no
additional authority.

The Forex Factory clock is source rank C. That rank caps this exact ID at
diagnostic kill/park even if all later DESIGN economics were to pass.

## 2. Market thesis frozen for a later, separately authorized test

Scheduled high-impact point releases may produce realized-volatility expansion.
A symmetric pre-event OCO may capture magnitude without forecasting direction,
but it must beat a matched non-event OCO after conservative event costs.

Primary mechanism priors:

- Federal Reserve IFDP 2007-903, *Trading Activity and Exchange Rates in
  High-Frequency EBS Data*: scheduled announcements coincide with sharp trading
  activity, and the documented price/volume response can be staged rather than
  a single directional drift. <https://www.federalreserve.gov/pubs/ifdp/2007/903/ifdp903.htm>
- Federal Reserve IFDP 2004-823, *The High-Frequency Effects of U.S.
  Macroeconomic Data Releases on Prices and Trading Activity in the Global
  Interdealer Foreign Exchange Market*: announcement windows show sharp FX
  volatility and volume elevation, with persistence varying by release.
  <https://www.federalreserve.gov/pubs/ifdp/2004/823/ifdp823.htm>

These papers are priors, not evidence that the frozen retail OCO is profitable.

## 3. De-duplication and failure radius

- `EA_NewsMomentum` and the standalone event-drift probes were post-release
  directional objects. They are closed and do not authorize another directional
  or pre/post-window grid.
- `EA_EventCLOBPersistence` derives direction from paid CME 6E order-book state.
  This object is non-directional and uses no order book.
- ECRS is session ER/compression plus directional range breakout. It is not a
  scheduled-event symmetric straddle.
- Unicorn event lanes are XAU sweep/FVG structures, not a symmetric macro OCO.

Hard same-ID prohibition: never use post-release price direction. After any
output exists, do not change or grid the buffer, box, expiry, TP, SL, event name,
hour, weekday, year, session, cost, observation window or hold window; do not
filter the just-read ledger; do not rescue by renaming the same object.

## 4. Immutable authority inputs

All paths are workspace-relative and must be regular, non-symlink,
non-reparse, single-link files under the exact public roots.

| Artifact | Path | SHA256 |
|---|---|---|
| Forex Factory raw JSON | `02. AlphaFactory/data/forexfactory/EURUSD/news_events/forexfactory_high_impact_eurusd_2019_2022.weekly.raw.json` | `78CB2656A27278B1DA04B2C594A2C73BB1877DBA3AB52BCCFAC36A215945EA8F` |
| Forex Factory normalized CSV | `02. AlphaFactory/data/forexfactory/EURUSD/news_events/forexfactory_high_impact_eurusd_2019_2022.csv` | `80B9DE46517B42F8B1D9A3ACCEFA6CC6D3DCB4DD06CAE357F16DE46228C64307` |
| Forex Factory manifest | `02. AlphaFactory/data/forexfactory/EURUSD/news_events/manifest.json` | `79C40AE0C7DFF7CF44539D00FD108E6D038648694EABD7AA44E234ACC00EF5B1` |
| Public DESIGN manifest | `02. AlphaFactory/data/fivepercent/EURUSD/splitvault_002/public/design_manifest.jsonl` | `A8A091DA8365602CB1D02BA571E96B4FB00B50621A73166B8CEDDBC1A7EED8C7` |
| Public DESIGN receipt | `02. AlphaFactory/data/fivepercent/EURUSD/splitvault_002/public/design_receipt.json` | `8109B11B6054517B9904FB4ACEF25EB7C6BD2485487CA9D69340DDC7E7D27FF8` |

The receipt must bind M1 source SHA
`2959C555DB6690FD6EFD6CFB3B4C6323698E590C9B2D71E1E55F1902F724235A`
and state `research_validation_opened=false` and
`research_holdout_opened=false`. The public data root is exactly
`02. AlphaFactory/data/fivepercent/EURUSD/splitvault_002/public/DESIGN`.
Private, sealed, validation, holdout, path-escape and alias paths are forbidden.

The Forex Factory manifest must state source rank C, promotion false, coverage
2019-01-01 through 2022-12-31, the exact raw/CSV paths and hashes, and its
published limitations. No source limitation may be weakened.

## 5. Clean clock transform

1. Reconcile every normalized CSV row independently to exactly one raw `events`
   row by unique `event_id` and exact identity/source fields: UTC time, currency,
   impact, event name, local date, source week and source URL.
2. Recompute UTC from `event_date_local + time_local_text` using fixed `GMT+7`;
   require exact equality with both raw and normalized `event_time_utc`.
3. `actual`, `forecast` and `previous` are prohibited from every output,
   selection predicate and aggregate. No news surprise is constructed.
4. Group all reconciled rows by exact UTC timestamp before semantic-name
   filtering.
5. Keep only clusters in the DESIGN window whose members are EUR or USD, exact
   impact `High Impact Expected`, timezone-aware, second/microsecond zero and
   unique by `event_id`.
6. Reject the entire cluster if any member name matches case-insensitive
   `speaks?|speech(?:es)?|testif(?:y|ies|ied)|testimony|press conferences?|hearings?`.
   Keep point publications including FOMC/ECB statements, meeting
   minutes/accounts and rate decisions.
7. Sort by UTC. One timestamp cluster is one event. Expected clean cardinality is
   319 clusters and 505 source member rows. A different observed cardinality is
   fatal; it must not be silently forced.

Deterministic durable outputs:

- `research/source/clean_point_release_clocks_2019_2020.csv`
- `research/source/clean_point_release_clock_manifest.json`

The clock CSV contains identity/source fields and `all_member_clean=true`, but
never actual/forecast/previous. The manifest binds every source/output hash,
rank C, promotion false, group-before-filter counts, and explicit zero
price/outcome/economics counters.

## 6. Frozen later strategy contract — not executable in this run

- Box: completed M1 BID bars `T-16` through `T-2` inclusive (15 bars).
- H1 ATR20: MT5-parity simple mean of 20 true ranges, shift 1, built from 21
  complete UTC H1 buckets ending before `floor(T, 1h)`.
- At the first tick in minute `T-1`, arm buy-stop = `box_high + buffer` and
  sell-stop = `box_low - buffer`.
- `buffer = max(2.0 pips, 0.05 * ATR20_pips)`.
- Planned `1R = box_width + 2 * buffer`.
- Pending expiry: `T+10m`.
- First fill cancels the opposite order immediately via `OnTradeTransaction`.
  A second/double fill is flattened immediately and violation-logged.
- SL crosses the opposite box edge plus buffer; TP = `1.0R`; time exit `T+30m`.
- Risk = 0.10% of balance; maximum one event exposure; skip any new event while
  pending or positioned; no break-even, trail or partial exit.
- Sort clocks and reserve `[T-1, T+30]`; greedily skip every later clock whose
  arming time overlaps the prior accepted reservation, independent of fill.
- Matched control is exactly `T-7` calendar days, only when no clean event exists
  within plus/minus two hours. It uses identical schedule, box, buffer, OCO,
  exit and risk. Later economics may use only one-to-one matched pairs.
- Trials = 2. Any later economics must use MT5 `Model=4`, `Every tick based on real ticks`. MT5 Model 0 is generated from M1 bars and is insufficient for pending-order OCO fill ordering, double-fill, rejection and slippage economics; it is prohibited for that later stage.
- Round-trip cost ladder = 3.0 / 4.5 / 6.0 pips.
- Later gates: PF >= 1.30 / 1.15 / 1.00 by cost tier; mean R > 0; total R > 0;
  both 2019 and 2020 positive; primary minus control PF >= 0.10 and mean R >=
  0.03; DD <= 6%; Monte Carlo P95 DD <= 6%; DSR >= 0.95; double-fill <= 0.5%;
  pending reject <= 2%; P95 adverse slippage <= 6 pips; history quality >= 99%.
- Any execution reconciliation failure invalidates the later run. Source C still
  forbids promotion.

## 7. Authorized source and geometry feasibility run

For each primary and eligible control clock:

- Require exact M1 timestamps `T-16` through `T+30`, inclusive. No fill,
  interpolation, resampling, deduplication, row drop or date substitution.
- The `T..T+30` timestamp-coverage read projects `time_utc` only. Tests must fail
  if post-`T` OHLC, spread or volume is requested or returned.
- Pre-`T` OHLC projection is limited to `T-16..T-2` plus the 21 prior complete
  UTC H1 buckets. No post-event feature is computed.
- Aggregate each prior H1 bucket only when all 60 exact minutes exist. Calculate
  box width, H1 ATR20, buffer and planned risk; never simulate an order or read
  an outcome.
- Clean raw cadence uses frozen elapsed weeks `104.42857142857143` and must be
  within 2–5/week.
- Complete clean clusters must be at least `ceil(0.99 * observed_clean_clusters)`.
- Matched source-feasible pairs must be >= 209 and pair cadence must be 2–5/week.
- Primary planned-risk median must be >= 8 pips and P25 >= 5 pips.
- Record `6.0 / median_planned_risk_pips`; it must be <= 0.75.

No gate may change after output.

## 8. Evidence, verdicts and failure policy

Attempt ID: `HYP001-SOURCE-PREFLIGHT-001`  
Evidence root:
`03. EA Developer/EA_EventVolOCO/research/evidence/HYP-EVENT-VOL-OCO-EURUSD-M1-001_SOURCE_FEASIBILITY/HYP001-SOURCE-PREFLIGHT-001`

Successful engineering execution writes deterministic create-new files:

- `attempt_started.json`
- `event_vol_oco_source_ledger.jsonl`
- `event_vol_oco_source_report.json`
- `attempt_terminal.json`
- `source_feasibility_receipt.json`

Only two market-neutral terminal verdicts are legal:

- `PASS_SOURCE_FEASIBILITY_DIAGNOSTIC_ONLY`
- `PARK_SOURCE_FEASIBILITY_FAILED`

The ledger/report/receipt must contain no post-`T` OHLC or outcome fields.
Manifest/hash/schema/timezone/cardinality/path/shard-hash/output-conflict errors
are fail-closed engineering errors. If the output root and attempt-started file
were established safely, an unexpected runtime exception must still create a
terminal with null market verdict and zero economic counters. An output conflict
must never overwrite or append.

## 9. Authority matrix

| Capability | Authorized now |
|---|---:|
| Source/test implementation | yes |
| One exact source-feasibility run | no — only after independent review plus a matching valid pre-source registry row |
| Public DESIGN pre-`T` OHLC geometry | yes, frozen bounds only |
| Post-`T` `time_utc` coverage | yes |
| Post-`T` price/spread/volume | no |
| Performance/economics/trades | no |
| Validation/holdout/private/sealed | no |
| MQL5/MT5/Model 4 economics | no; Model 4 is frozen for any separately authorized later stage, and Model 0 is prohibited |
| Network/paid source | no |
| Optimization/promotion/live | no |

Acceptance contract retained for any future economic stage: PF 1.30, cadence
2–5/week, DD 6%, cost-stress PF x1.5 >= 1.25, PF x2 >= 1.00, Monte Carlo P95
DD 6%. These thresholds are registry/governance constraints, not metrics
authorized in the current source-only run.


