# DESIGN ECONOMICS PLAN - HYP-ROUND-CASCADE-EURUSD-M5-009

Status: FROZEN PRE-OUTCOME on 2026-07-29. This is a **fresh pre-outcome DESIGN
economics child** enabled by the outcome-blind HYP008 execution-source PASS. It
is **not** a post-hoc market rescue of HYP005, HYP004, or any prior economic
object. HYP005 remains a separate engineering-invalid all-source mapping object
and must not be rerun, retuned, or reopened under this ID.

An engineering-valid gate failure under this plan **kills exactly HYP009**. No
same-ID tuning of session, weekday, year, direction, threshold, lattice, stop,
horizon, cost, symbol, timeframe, source reselection, or entry delay is
permitted.

## 1. Identity and failure radius

- `hypothesis_id`: `HYP-ROUND-CASCADE-EURUSD-M5-009`
- `parent_candidate`: `HYP-ROUND-CASCADE-EURUSD-M5-008` (PASS execution-source)
- `source_signal_hypothesis_id`: `HYP-ROUND-CASCADE-EURUSD-M5-002`
- `ea_name`: `EA_RoundNumberCascade`
- Symbol / decision timeframe: EURUSD M5 from immutable public DESIGN M1 BID bars.
- Attempt: `HYP009-DESIGN-ECON-001` (limit exactly one).
- Fresh evidence root:
  `03. EA Developer/EA_RoundNumberCascade/research/evidence/HYP-ROUND-CASCADE-EURUSD-M5-009_DESIGN_ECONOMICS/HYP009-DESIGN-ECON-001`.

Parent HYP008 terminal path/SHA:

- `03. EA Developer/EA_RoundNumberCascade/research/evidence/HYP-ROUND-CASCADE-EURUSD-M5-008_EXECUTION_SOURCE/HYP008-EXEC-SOURCE-001/attempt_terminal.json`
- SHA256 `9EFA0811D46286A2B5FCBBADB814785BA5EC24EC83A90DC73CD998394EBD8E10`
- Status/verdict: `PASS_EXECUTION_SOURCE_MAY_DRAFT_HYP009_DESIGN_ECONOMICS`
- `hyp009_drafting_authorized`: true

HYP005 is the reviewed economics evaluator/test **template only**. Its invalid
all-source mapping (`TRUE_0050=1229`, `SHIFTED_0025=1220` with delay/next-bar
entry) is **replaced**, not rescued. Unchanged from HYP005 economics object:

- signal mechanism / directions / ATR stop geometry
- twelve complete observed UTC-aligned M5 bars
- BID entry / stop / exit and adverse stop precedence
- DESIGN years 2016-2020; elapsed calendar weeks `260.5714285714`
- cost tiers exactly `1.50` / `2.25` / `3.00` pips
- risk fraction `0.0025`
- DSR with exactly two trials (TRUE and SHIFTED; cost tiers are not trials)
- all eleven HYP005 gates and exact PASS / KILL / ENGINEERING_INVALID meanings
- public DESIGN producer / schema / path / hardlink / manifest validation
- one-shot durability
- sealed prohibitions: no validation / holdout / private / MQL5 / MT5 / network /
  paid / promotion / live

## 2. Frozen HYP008 eligible execution-source population

Bind and validate **before any DESIGN price access**:

| Artifact | Relative path under HYP008 evidence root | SHA256 |
|---|---|---|
| Eligible ledger | `round_cascade_008_eligible_source_ledger.jsonl` | `B84EF3925B5CC998A88D224BCF8B4A66D5A6076DFED87C4287325F369AAFF16B` |
| Report | `round_cascade_008_execution_source_report.json` | `5F74F6A33FA66D05D131D5727CC6CC31929C748A8B223A820986FD62CD180EEA` |
| Receipt | `execution_source_receipt.json` | `A06E602222E20C7B1800F3E92FFA51679A6DDB06D9DE81FC41CF737C9D0B8DF9` |
| Terminal | `attempt_terminal.json` | `9EFA0811D46286A2B5FCBBADB814785BA5EC24EC83A90DC73CD998394EBD8E10` |

Evidence root:

`03. EA Developer/EA_RoundNumberCascade/research/evidence/HYP-ROUND-CASCADE-EURUSD-M5-008_EXECUTION_SOURCE/HYP008-EXEC-SOURCE-001`

Exact eligible counts (fatal acceptance constants for HYP009 economics):

- `TRUE_0050 = 1220`
- `SHIFTED_0025 = 1214`

Every eligible row status must be `ELIGIBLE_EXACT_ENTRY_NONOVERLAP` with
`complete_m5_starts = 12`. The population is already arm-local non-overlap from
HYP008; HYP009 must **re-assert** arm-local non-overlap after mapping/simulation.

## 3. Exact join to HYP002 detail ledger

HYP002 detail ledger path/SHA:

- `03. EA Developer/EA_RoundNumberCascade/research/evidence/HYP-ROUND-CASCADE-EURUSD-M5-002_SOURCE_FEASIBILITY/HYP002-SOURCE-PREFLIGHT-001/round_cascade_source_ledger.jsonl`
- SHA256 `8172CB237B74CDA6DED53E5BCECB7DD80163A6BE506750FF1567C65CC31B9FBE`
- Full source populations remain `TRUE_0050=1229`, `SHIFTED_0025=1220` on the
  detail ledger (not the economics trade population).

Join contract:

1. Recompute **every** HYP002 canonical LF-row hash as
   `SHA256(raw_jsonl_line + LF)` without mutating row bytes or field values.
2. Join each HYP008 eligible row **exactly once** to one HYP002 detail row using
   the composite key:
   `arm + planned_entry_time_utc + source_lf_row_sha256`.
3. Forbid missing joins, duplicate eligible identities, fan-out (one eligible to
   many detail), reverse fan-out, and any mutation of detail fields after join.
4. Economics simulation uses only the joined eligible population
   (`1220 + 1214`). No drop, replacement, re-selection, signal-time shift, or
   silent filtering is permitted.

## 4. Exact-entry observed-M5 mapping (replaces HYP005 delay mapping)

Build the observed market index once before signal simulation (same complete-M5
definition as HYP005): UTC-aligned bins with minutes divisible by five and
exactly five M1 timestamps at offsets `0,1,2,3,4`; incomplete bins excluded;
gaps allowed; no fill/synthesis.

For each joined eligible signal:

1. `planned_entry_time_utc` is unchanged from the HYP002 detail row and eligible
   ledger.
2. Entry is the complete observed M5 bar whose start equals
   `planned_entry_time_utc` **exactly**. No delay and no next-bar fallback.
3. Missing exact complete entry bar is engineering-invalid.
4. Horizon is exactly twelve complete observed M5 bars by chronological index,
   including the entry bar. Fewer than twelve remaining bars is right-censored
   and engineering-invalid.
5. Recomputed `reserved_exit_time_utc` must equal
   `twelfth_complete_m5_start + 5 minutes` and must match the eligible ledger
   value exactly.
6. Entry BID is the entry bar open. Non-stop exit is the twelfth observed bar
   close at `twelfth_bar_start + 5 minutes`.
7. Stop distance is exactly `atr20_pips * 0.0001`; long stop = entry − distance;
   short stop = entry + distance.
8. Inspect all twelve bars in order. Long stops when `low <= stop`; short stops
   when `high >= stop`. Stop touch keeps adverse precedence, including on the
   twelfth bar, and returns exact `gross_R = -1`.
9. Otherwise `gross_R = direction_sign * (exit_bid - entry_bid) / stop_distance`.

Mapping is all-or-nothing before economics: exactly 1,220 TRUE and 1,214 SHIFTED
trades must map. Any mapping/join/overlap invariant failure terminates
`ENGINEERING_INVALID_NO_MARKET_VERDICT` before `evaluate_gates`, DSR, performance
metrics, or success economics artifacts.

## 5. Frozen economics and gates (unchanged meanings)

- DESIGN years: 2016-2020; elapsed calendar weeks: `260.5714285714`.
- Round-trip cost stresses: exactly `1.50`, `2.25`, and `3.00` pips,
  `UNVERIFIED_PROXY_KILL_ONLY`.
- `cost_R = cost_pips / atr20_pips`; `net_R = gross_R - cost_R`.
- Drawdown: chronological TRUE 1.50-pip net-R, equity starts 1.0,
  `equity *= 1 + 0.0025 * net_R`.
- DSR: per-trade 1.50-pip net-R; TRUE and SHIFTED are exactly two trials;
  `n_trials = 2`; **`n_obs = 1220`** (actual TRUE eligible count). Cost tiers are
  not extra trials.

All eleven gates (identical thresholds/meanings to HYP005):

1. TRUE cadence `2.0 <= x <= 5.0` per elapsed week.
2. TRUE PF at 1.50 pips `> 1.30`.
3. TRUE PF at 2.25 pips `>= 1.25`.
4. TRUE PF at 3.00 pips `>= 1.00`.
5. TRUE mean net R at 1.50 pips `>= 0.08`.
6. TRUE total net R at 1.50 pips `> 0`.
7. TRUE positive DESIGN years at 1.50 pips `>= 4 of 5`.
8. TRUE max compounding DD `<= 6.0%`.
9. TRUE DSR at 1.50 pips `>= 0.95`.
10. TRUE PF minus SHIFTED PF at 1.50 pips `>= 0.15`.
11. TRUE mean net R minus SHIFTED mean net R at 1.50 pips `>= 0.05`.

Verdicts:

- Engineering-valid and all gates pass: `PASS_DESIGN_ECONOMICS_MAY_BUILD_EA`
  (DESIGN survivor only).
- Engineering-valid but any gate fails: `KILL_DESIGN_ECONOMICS_NO_EDGE` for this
  exact object; no same-ID rescue.
- Any engineering/join/mapping invariant fails:
  `ENGINEERING_INVALID_NO_MARKET_VERDICT`; no economic claim.

## 6. Public DESIGN producer boundary (unchanged)

- DESIGN manifest path/SHA:
  `02. AlphaFactory/data/fivepercent/EURUSD/splitvault_002/public/design_manifest.jsonl` /
  `A8A091DA8365602CB1D02BA571E96B4FB00B50621A73166B8CEDDBC1A7EED8C7`.
- DESIGN receipt path/SHA:
  `02. AlphaFactory/data/fivepercent/EURUSD/splitvault_002/public/design_receipt.json` /
  `8109B11B6054517B9904FB4ACEF25EB7C6BD2485487CA9D69340DDC7E7D27FF8`.
- Public M1 source SHA:
  `2959C555DB6690FD6EFD6CFB3B4C6323698E590C9B2D71E1E55F1902F724235A`.
- Collection plan / custodian / DSR bindings remain the HYP005 public-DESIGN
  producer contract (one row group; exact ordered Arrow schema; no schema
  metadata; exact manifest path/date/SHA/bytes/rows; naive-Arrow-UTC attachment;
  no hardlinks/symlinks; JSONL/CSV/generic timestamp paths strict).

## 7. One-use authority and prohibitions

- Evaluator:
  `03. EA Developer/EA_RoundNumberCascade/research/evaluate_round_cascade_009_design_economics.py`
- Tests:
  `03. EA Developer/EA_RoundNumberCascade/research/tests/test_evaluate_round_cascade_009_design_economics.py`
- Run packet (not created by this implementation task):
  `03. EA Developer/EA_RoundNumberCascade/research/HYP-ROUND-CASCADE-EURUSD-M5-009_DESIGN_ECONOMICS_RUN_PACKET.json`
- Review receipt name (not created by this implementation task):
  `03. EA Developer/EA_RoundNumberCascade/research/HYP-ROUND-CASCADE-EURUSD-M5-009_DESIGN_ECONOMICS_IMPLEMENTATION_REVIEW_RECEIPT.json`
- Attempt ID: `HYP009-DESIGN-ECON-001`
- `REVIEWED_RUN_PACKET_SHA256` sentinel remains `None` / disarmed until independent
  review arms a reviewed packet SHA.
- Attempt limit is one. Evidence root must be absent before authority and created
  atomically. No overwrite, deletion, reuse, or same-ID rerun.
- Plan alone grants no run authority. A reviewed evaluator/test hash pair,
  independent review receipt, exact run packet, and latest registry authority
  row must bind one another before the sentinel is armed.
- Forbidden throughout HYP009: validation, holdout, private custody, monolithic
  source, MQL5, MT5, Model 0/4, optimization, network, paid calls, promotion,
  paper trading, and live trading.

Required success artifacts (production only, not this task):

`attempt_started.json`, `design_economics_trade_ledger.jsonl`,
`design_arm_cost_metrics.json`, `design_yearly_metrics.json`,
`design_drawdown_metrics.json`, `design_dsr_inputs.json`,
`design_gate_report.json`, `design_economics_receipt.json`,
`attempt_terminal.json`.

## 8. Implementation-task boundary

This plan freezes the economics object and join/entry contract. The builder may
create only the plan, one-shot evaluator, and focused tests. It must not create
a run packet, review receipt, registry row, evidence root, arm the sentinel,
open parquet production data, or execute production.
