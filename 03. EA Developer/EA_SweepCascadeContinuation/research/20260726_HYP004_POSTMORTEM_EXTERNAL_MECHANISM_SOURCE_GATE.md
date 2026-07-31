# HYP004 Postmortem External-Mechanism Source Gate

Date: 2026-07-26

Status: `NO_NEW_HYPOTHESIS_YET_SOURCE_FEASIBILITY_ONLY`

This memo follows the terminal matched-pair result for
`HYP-SCC-MT5-REPLICATION-EURUSD-M5-004`. It does not amend HYP004, authorize
same-ID tuning, create a registry row, inspect a sealed OOS interval, change EA
source, or permit another Strategy Tester run.

## Bound evidence

- Corrected Random100/GFI readout:
  `research/evidence/HYP-SCC-MT5-REPLICATION-EURUSD-M5-004_PAIR_ANALYSIS/HYP004_RANDOM100_GFI_CLOCK_V2_READOUT.md`.
- Corrected chart verdict:
  `PASS_FOR_POSTMORTEM_PATH_FORENSICS_PARTIAL_FOR_SIGNAL_FIDELITY_NOT_VALID_FOR_OPTIMIZATION`.
- Matched-pair challenger: 261 trades, PF `0.6912782`, mean R
  `-0.23178969`, net `-587.30`, cadence `1.25137` trades per elapsed week.
- Random100 sample: 100 trades, 28 wins, 72 losses, PF `0.6035236575`,
  mean R `-0.311167`.
- Geometry priority: `ENTRY_SETUP_DISCRIMINATION`; exit changes are secondary.
- All anatomy labels disclose post-entry outcomes. They are descriptive
  postmortem evidence only and may not become decision-time filters.

## Deep Research provenance and bounded output

The strategy search was run in the ChatGPT browser with exact UI readback:

- model: `GPT-5.6 Sol`;
- mode: `Pro`;
- tool: `Nghiên cứu sâu`;
- completion: approximately eight minutes and 235 searches;
- conversation:
  `https://chatgpt.com/c/6a64fe96-aff8-83ec-b1bd-6feb2cbf9f54`.

The result proposed at most three materially external information sets:

1. EBS primary-spot order-book resilience: `OPEN_FOR_SOURCE_FEASIBILITY`.
2. Transatlantic front-end rates cojump: `OPEN_FOR_SOURCE_FEASIBILITY`.
3. FX Link implied-funding state: `PARK`.

These are idea inputs, not validated facts or trading hypotheses.

## Parent methodological corrections

### Geometry is outcome-bearing

`P(+0.25R before stop)`, `P(+0.50R before stop)`, `never +0.25R`, MFE, MAE
and time-to-MFE all read the path after entry. They are not outcome-blind even
when PnL and the final exit are omitted.

The legal sequence is:

1. source-feasibility only: schema, provenance, point-in-time timestamps,
   coverage, clock alignment, missingness and mechanical state/cadence shares;
2. freeze a fresh hypothesis ID, registry row, feature contract, DESIGN period,
   untouched OOS period and falsification gates;
3. only then join DESIGN entries to post-entry geometry;
4. never use OOS to select a threshold or rewrite the rule.

### Venue and history correction for the rates candidate

CME states that SOFR futures launched on 2018-05-07, so a CME SOFR design leg
can in principle cover 2019 onward. ICE Three Month Euribor is the appropriate
official euro STIR contract to investigate for the 2019--2022 design period.
The current Eurex three-month EURIBOR/Euro-STR route was not proven to provide
the claimed continuous 2019--2026 intraday history. Eurex states that its
Euro-STR futures launched on 2023-01-23, so that product cannot support the
frozen 2019--2022 design interval.

### No free-data or cost claim

CME describes EBS Spot FX as direct EBS Market data with one-second L1,
100-millisecond L2 and up to five or ten depth levels. CME also requires an
Information License Agreement and purchased/entitled DataMine access. No
public historical EBS sample, full-period entitlement or price was verified in
this session.

ICE describes its consolidated history as licensed tick-by-tick Level 1/2/3
history. No free 2019--2024 ICE Euribor entitlement or public price was
verified. A rates cojump lane therefore has a cross-vendor source and cost gate
unless a single licensed vendor is proven to carry both legs with the required
point-in-time fields.

Official sources:

- https://www.cmegroup.com/market-data/browse-data/catalog/ebs-spot-fx.html
- https://www.cmegroup.com/datamine.html
- https://www.cmegroup.com/datamine/datamine-api.html
- https://www.cmegroup.com/media-room/press-releases/2018/3/01/cme_group_announcesnewsofrfutureslaunchdateandcontractspecificat.html
- https://www.ice.com/products/38527986/three-month-euribor-futures
- https://developer.ice.com/fixed-income-data-services/catalog/ice-futures-europe
- https://www.eurex.com/ex-en/find/news-center/news/Eurex-launches-new-futures-referencing-STR-3319912

## De-duplication against the local frontier

| Candidate | Existing nearby lineage | Failure-radius decision |
|---|---|---|
| EBS primary CLOB | HYP018 broker-tick initiation; HYP020--026 broker-price/level paths; prior DRAT frontier named EBS/CME 6E as a missing external set | Materially distinct only if the raw input is primary EBS point-in-time book/trade state. Broker ticks, reconstructed OHLC or an EBS-branded daily dashboard are not substitutes. |
| Front-end rates cojump | HYP-CME-OI-CONT-H1-FX-001 daily futures OI continuation; terminal V8 D1 lagged SOFR-minus-EuroSTR level probe; generic H1/session/trend filters | Materially distinct only if it is synchronized intraday relative repricing from listed STIR markets. Daily rate levels, daily OI, release labels or price trend proxies are not substitutes. |
| FX Link funding state | Existing daily/public parity and slow-regime frontier | Causal story is distinct, but the cheapest prior-day/T+1 form is too slow for the M5 decision surface and risks becoming a generic daily regime filter. Keep parked. |

The existing Databento CME EUR/USD options acquisition route is a separate
information set. It does not provide EBS cash-spot CLOB data or ICE Euribor
ticks and cannot satisfy either new source contract by itself.

### Exact daily-rates sibling boundary discovered during parent QC

The archived V8 contract and readout remain available in Git commit `b709309`:

- `03. EA Developer/EA_SonicR/research/preflight/v8_exogenous/20260713_V8_OIS_SOFR_ESTR_DIFF_EURUSD_PROBE_CONTRACT_V1.md`;
- `03. EA Developer/EA_SonicR/research/readouts/20260713_V8_OIS_SOFR_ESTR_DIFF_EURUSD_OFFLINE_PROBE_READOUT.md`.

That frozen D1 candidate used the lagged daily SOFR-minus-EuroSTR level,
60-day z-score, `|z| >= 0.75`, D1 entries and a five-D1-bar time stop. On
2019--2022 DESIGN it produced 159 trades, `0.762` trades/week and
PF `1.0026606830` at the 1.5-pip stress, failing its absolute `1.05` PF gate.
It was killed before registry, EA or Model 0 and explicitly prohibited
same-surface threshold or tenor rescue.

Therefore the new rates candidate is legal only as a different information
surface: simultaneous intraday changes in two listed STIR order/trade streams
at the M5 decision clock. Any fallback to lagged daily SOFR/EuroSTR/Euribor
levels, z-scores, slow funding regimes or tenor/threshold variants is inside
the killed V8 failure radius and must stop.

## Candidate source contracts before any outcome join

### Candidate A — EBS order-book resilience

Required source-feasibility evidence:

- EUR/USD EBS primary-market identity and legal internal-research license;
- exchange/event timestamps, price, size and side for trades or a frozen,
  causally computable aggressor rule;
- top-of-book bid/ask price and size plus at least three depth levels on both
  sides;
- documented timestamp precision, engine/session boundaries and missing-file
  semantics;
- immutable D-side raw files, manifest and SHA-256 hashes;
- mechanical 2019--2022 DESIGN and 2023--2024 untouched-OOS coverage inventory;
- feature availability no later than the candidate M5 decision instant.

Pre-outcome source stop:
`SOURCE_GATE_PENDING_CME_EBS_QUOTE_LICENSE_SAMPLE`.

### Candidate B — front-end rates cojump

Required source-feasibility evidence:

- CME Three-Month SOFR and ICE Three Month Euribor point-in-time intraday
  records, or a proven single-vendor equivalent carrying both official
  contracts;
- trade and/or quote timestamps, prices, sizes, contract IDs, expiries,
  calendars and correction/cancel semantics;
- deterministic prior-day contract selection and no intraday look-ahead roll;
- explicit no-trade/stale-bar handling;
- immutable D-side raw files, manifest and hashes;
- continuous 2019--2022 DESIGN coverage and sealed 2023--2024 OOS inventory.

Pre-outcome source stop:
`SOURCE_GATE_PENDING_CROSS_VENDOR_COVERAGE_COST`.

## Independent Grok review and parent QC

The initial bounded read-only forensic review passed its process and structured
output gates:

- run ID: `20260725T183728925608Z-47032`;
- elapsed: `139.265` seconds; four turns;
- schema validation: `PASS`;
- response SHA-256:
  `3BFC156809A7179FA414B1165DD6B724B264F538B1F15C46D87958F37AC00AAB`;
- summary SHA-256:
  `ADBEB55289A881E904F207EB8F4369A7D9A1F5539DCFCE12B24449439A8109B5`;
- local response:
  `.context/scc-postmortem-external-mechanisms/run/grok-response.json`.

Grok independently confirmed:

- HYP004 remains terminal;
- every MFE/MAE/+R path statistic is `OUTCOME_BEARING`;
- EBS is the only `OPEN_FOR_SOURCE_FEASIBILITY` candidate;
- intraday SOFR/Euribor cojump remains `PARK`;
- prior-day/T+1 FX Link funding remains `PARK`;
- no candidate has verified local 2019--2024 point-in-time coverage;
- source feasibility does not authorize a hypothesis, outcome join, EA,
  optimization, backtest, promotion or live action.

Parent QC then found the omitted archived V8 daily SOFR-minus-EuroSTR sibling.
One narrowly bounded correction review was permitted because this was an
acceptance gap, not a new task. It also passed:

- run ID: `20260725T184103057167Z-564`;
- elapsed: `58.031` seconds; two turns; web disabled;
- schema validation: `PASS`;
- response SHA-256:
  `16AA022C85F3B62D0781F8365D64E0BBDA0EB403B932F76396BEAD80BF396CAD`;
- summary SHA-256:
  `A1435929A7576A0064C5906678865F66FF34F1662A58EC8A8894C7B6BF80E008`;
- local response:
  `.context/scc-postmortem-rates-dedup-correction/run/grok-response.json`.

The correction verified the V8 metrics from Git and retained `PARK` for the
intraday listed-futures cojump. It remains materially distinct only while it
uses synchronized event-time STIR repricing at the M5 decision clock. EBS
priority did not change.

## No-charge EBS source-feasibility result

The free official documentation establishes only the product and access path:

- EBS Ultra is historical, high-granularity, SBE data sourced from the primary
  CLOB with near-continuous order-book and trade information;
- current EBS Spot documentation advertises one-second L1, 100-millisecond L2
  and up to five or ten book levels;
- CME requires an Information License Agreement and purchased/entitled
  DataMine access;
- current EBS Ultra has separate New York and London conflated channels, and
  current technical notices show that conflation and message semantics change
  over time.

The free surface does **not** establish:

- historical EUR/USD availability dates for each requested product/feed;
- a downloadable sample with the exact historical SBE templates and fields;
- whether the historical product includes a causal trade-side/aggressor field;
- pre/post-2022 engine/channel merge rules;
- event, receive and publication timestamp definitions by era;
- cancel/correct, gap, reset, session and missing-file semantics;
- 2019--2022 plus 2023--2024 continuous coverage;
- price, ILA terms or redistribution/internal-research limits.

Local inventory found no EBS, SOFR-futures or ICE Euribor intraday corpus. The
only nearby local executable is the old D1 SOFR-minus-EuroSTR probe and cannot
satisfy the new information contract.

This exhausts the no-charge public source-feasibility step. A complete quote,
license and one-day schema sample now require CME Data Sales/authorized
DataMine access. No contact form was submitted and no purchase was made.

## Current decision

Priority remains EBS because it attacks the observed microstructure failure
through a new primary-venue state and requires only one market-data owner.
However, it is not open for a geometry probe or EA implementation yet.

Next actions:

1. obtain a CME EBS quote plus a no-charge one-day historical schema sample
   for EUR/USD primary-CLOB book/trade data, covering all historical feed-era
   changes needed for 2019--2024;
2. build a reproducible D-side order/coverage/cost plan without reading an EA
   outcome;
3. request an explicit Owner USD ceiling only after that plan exists;
4. if the source gate passes, open one fresh hypothesis and preregister before
   reading any post-entry geometry.

Until then: no parameter optimization, no setup/entry/exit rewrite, no MT5
rerun and no profitability claim.

## 2026-07-26 amendment — bounded CME 6E MBP-10 alternative

A metadata-only Databento feasibility pass tested a materially different,
legally accessible source without submitting a paid request. It did **not**
silently substitute futures data for EBS:

- source identity: `GLBX.MDP3` / `mbp-10` / continuous `6E.v.0`, whose rank-0
  contract is chosen from previous-day volume;
- event population: all 261 HYP004 challenger decision timestamps, using only
  `position_id`, server `decision_time` and frozen direction; outcome fields,
  exits and PnL were not used;
- canonical server-to-UTC clock SHA:
  `A7F179935102B57BA3B629345209F6B0D668D1F7FD828A5ED6003207F41A2F52`;
- fixed request window: `[decision_time_utc-120s, decision_time_utc)`;
- exact metadata estimate: USD `0.254399180414`; internal two-times ceiling
  USD `0.508798360828`; recommended Owner ceiling USD `1.00`;
- exact billable size: `546,318,080` bytes across 259 non-empty windows;
- two source-empty windows fail closed before any outcome join: PID `26` at
  `2019-04-19T00:55:00Z` and PID `80` at `2019-09-01T21:25:00Z`;
- the rejected continuous 2019--2025 request would cost about USD `471.8785`
  and bill about `1.013 TB`, so it is outside the cheap-probe contract.

Durable plan:
`research/evidence/HYP-SCC-MT5-REPLICATION-EURUSD-M5-004_PAIR_ANALYSIS/CME6E_MBP10_SOURCE_FEASIBILITY_PLAN.json`.

One bounded Grok forensic review then passed `EndTurn`, useful-output and JSON
schema gates in one turn. Response SHA is
`F909742F2EEA92B8135CEC651926AB698E48DA440E9671BA2954A93DC3FE242D`;
summary SHA is
`6471C1AE701BA820F077BB02643DC26098379DF6B78F1DFA419C4DBD88F07F90`.
Grok returned `NEW_CANDIDATE_REQUIRED` with high confidence: CME 6E top-ten
book state may support a new futures-book hypothesis, but it cannot be called
an EBS/spot-CLOB test and cannot reopen HYP004.

The narrow causal feature surface is limited to decision-time variables fully
observable inside the frozen 120-second window: terminal L1 ratio, terminal
top-ten normalized depth imbalance, L1--L3 same-side depth change, trade
aggression relative to resting depth, update intensity and terminal spread.
Multi-session baselines, rolling ATR/volatility, EBS-trained resilience,
multi-week roll history and all post-decision variables are unavailable under
this contract. Every feature remains continuous until a fresh prereg freezes
the DESIGN-only transformation and sealed OOS decision rule.

This creates a practical alternative gate while preserving the EBS boundary:

1. EBS remains the primary-spot mechanism and stays
   `SOURCE_GATE_PENDING_CME_EBS_QUOTE_LICENSE_SAMPLE`;
2. CME 6E is a separate candidate at
   `SOURCE_FEASIBLE_PENDING_OWNER_USD1_CEILING_AND_FRESH_PREREG`;
3. after explicit Owner approval, freeze a collection manifest, acquire only
   the 261 bounded windows to the D-side data shelf and validate 259/261
   non-empty coverage before any label join;
4. only after source/hash validation, open a fresh hypothesis/registry row and
   preregister DESIGN/OOS handling before reading feature-versus-outcome
   relationships.

No paid request, download, hypothesis, outcome join, EA change, MT5 run,
optimization, promotion or live action occurred in this amendment.

## Acquisition implementation readiness

The bounded source route is now executable immediately after explicit Owner
approval, without changing the candidate or writing to `C:`:

- tool: `research/acquire_cme6e_mbp10_windows.py`;
- exact tool SHA:
  `D67D62295183AC1F809843D4869A7CF623FEE230564BD5C52C6B8BAAC8F8DB1C`;
- operational plan:
  `02. AlphaFactory/data/databento/cme_6e_mbp10_scc/acquisition_plan.json`;
- plan ID:
  `925232C794938E2EFA9113183002BF2EAFB53D5EAA57BC269B2872894F0B2D1F`;
- plan file SHA:
  `A0B51BF70D01B81415A768481487B256CEF3D96B389B60A57797D68733712670`;
- feasibility SHA:
  `2EBAC8602350EB69518CACBD8BAF309B49BCE60C98AD2AD5DAFF3AA22FAFAA8B`;
- action `plan` is offline and does not load the API key;
- action `download` requires exact plan ID plus numeric `--approve-max-usd`,
  validates D-side containment, source/clock/feasibility/tool hashes and SDK
  `0.54.0`, then obtains all free metadata quotes before the first paid call;
- cost mode is `historical-streaming`, matching `timeseries.get_range`; an
  exact 259-window re-quote confirmed the unchanged USD `0.254399180414`,
  USD `0.508798360828` two-times drift ceiling and `546,318,080` billable
  bytes with zero empty planned requests;
- paid calls are serial. An `in_flight` journal is checkpointed before each
  call; a complete partial/final DBN is fully decoded and adopted without a
  second paid request, while missing or incomplete in-flight output blocks
  automatic retry;
- DBN Zstandard signature, complete decode, non-zero record count, file bytes,
  SHA and manifest identity are fail-closed; foreign, duplicate, missing or
  mutated checkpoint entries are rejected.

Focused source-tool tests pass `12/12`, including no-approval/no-paid guards,
wrong-drive rejection, live-cost and zero-size rejection, two-times drift,
manifest tamper, foreign/duplicate/missing output, crash recovery without a
second call, missing in-flight refusal and full-DBN truncated-stream rejection.

Two independent Grok code-review attempts were **not accepted**: run
`20260725T192223113526Z-53996` stopped `Cancelled` at four turns and run
`20260725T192808618106Z-3492` stopped `Cancelled` at eight turns; neither
produced final structured output. Their partial text is not a review verdict.
Parent verification directly refuted the partial credential claim: both the
operational and feasibility JSON files contain no Databento key, client secret
or authorization header. No third retry was used to manufacture a PASS.

Current gate remains:
`SOURCE_FEASIBLE_PENDING_OWNER_USD1_CEILING_AND_FRESH_PREREG`.
The exact post-approval command must use the D-side Databento Python runtime;
system Python without SDK fails closed before any time-series request.

## 2026-07-27 amendment — acquisition completed, 261 population parked

Owner approved the exact USD1.00 ceiling. The bounded acquisition completed
under v2 plan ID
`9EB45071C233F31EF8EA348F2DBF8053A62ECF53CBD94D99DE32E51748213D38`.
Full decode/hash validation passed 259/259 response files: 258 nonempty, one
complete source-empty PID42 response, 257,009 market records and a live cost
estimate of USD0.254399180414. This estimate is not an invoice readback.

The source pass does not open the intended 261-event economic candidate. Over
208.714 elapsed weeks its absolute cadence ceiling is only 1.250515/week, below
the workspace 2/week minimum even before any book-state filter. The exact
population is therefore `SOURCE_VALID_261_POPULATION_PARK_CADENCE_CEILING`
without a feature/outcome join, hypothesis ID, registry row or EA.

A fresh raw first-close BREAK + CME 6E book-state source plan is separately
metadata-quoted for DESIGN 2019-2020 only. Plan
`1825DC77A35F2794051BD83E5A35ED87C8952049FB08B47BEA1AF34E1802D98F`
contains 541 billable of 547 decisions at USD0.339879676699 estimated cost and
a recommended USD0.68 ceiling. OOS 2021-2022 remains unquoted. This is a new
decision surface and requires explicit Owner approval before any paid request.
Readout:
`03. EA Developer/EA_CME6E_RawBreakBookState/research/20260727_SOURCE_GATE_AND_NEXT_DESIGN_PLAN.md`.
