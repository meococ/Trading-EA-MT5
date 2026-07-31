# HYP-ROUND-CASCADE-EURUSD-M5-010 — Execution-Source Exact-Complete-M5 Plan

Status: `FROZEN_PRE_OUTCOME_IMPLEMENTATION_SOURCE_CONTRACT_REFINEMENT_CHILD`

## 0. Scope declaration (implementation / source-contract refinement, not market rescue)

This hypothesis is a **timestamp-only execution-source refinement** child of the
engineering-invalid HYP009 DESIGN-economics attempt. It does **not** rescue a
market outcome, retune thresholds, delete source identities, reorder arms, open
price/OHLC, simulate trades, or authorize MT5/MQL5.

HYP009 emitted **no trades and no economics**. Its terminal status is
`ENGINEERING_INVALID_NO_MARKET_VERDICT` with reason
`no exact complete observed M5 entry at planned_entry_time_utc` and exact SHA256
`5F13B1F51CD7B5A2266640AF17633531F9B16E5D43FB8345DF90B5144A1EC7C7`. That failure
is an implementation/source-contract mismatch after HYP008 classified eligibility
on exact observed M1 plus any twelve complete M5 starts `>= planned`, without
requiring that **planned itself** be a complete UTC-aligned M5 start.

HYP010 therefore changes **only** the deterministic time-only classifier
prerequisite order over the **complete original HYP002 population**:

1. missing exact observed M1 at planned → `NO_EXACT_ENTRY` (never reserves);
2. planned is not itself a complete observed UTC-aligned M5 start →
   `NO_COMPLETE_M5_AT_PLANNED` (never reserves); right-edge fewer than twelve
   complete observed M5 starts **from** a planned that is a complete M5 start is
   fail-closed `ContractError` / engineering-invalid (not a silent ineligible);
3. if prerequisites pass but `planned <` current arm `reserved_exit` →
   `REFRACTORY_INELIGIBLE` (never reserves a new exit);
4. otherwise `ELIGIBLE_EXACT_COMPLETE_M5_NONOVERLAP` and reserve exit at the
   close of the 12th complete observed M5 (`twelfth_complete_m5_start + 5m`).
   Equality at the reserved exit is allowed (`planned == reserved_exit` may
   become eligible).

Failed prerequisite rows never reserve state. Production must re-run the greedy
arm-local state machine from the **full** HYP002 source ledger rather than
delete the three known forensic offenders from HYP008 output.

Known time-only diagnosis on HYP008 eligible ledgers found three eligible rows
without complete M5 at planned (TRUE 2, SHIFTED 1, next complete +5m). Those
counts are a **forensic expectation / review aid only**, not a fatal hardcoded
production gate. Runtime truth is recomputed from exact source + public DESIGN
timestamp bytes and the frozen state machine.

No post-hoc market rescue, Stage-0 economic loosening, receipt rebinding to
different corpora, source reselection, or permission expansion is permitted.

## 1. Identity and exact failure radius

- Hypothesis: `HYP-ROUND-CASCADE-EURUSD-M5-010`.
- Parent terminal: `HYP-ROUND-CASCADE-EURUSD-M5-009` attempt
  `HYP009-DESIGN-ECON-001`.
- Attempt: `HYP010-EXEC-SOURCE-001`, limit exactly one.
- Source signal parent (unchanged): `HYP-ROUND-CASCADE-EURUSD-M5-002`.
- Package: `EA_RoundNumberCascade`.
- Scope: public-DESIGN timestamp-only execution eligibility. This is not an
  economic run and cannot authorize price access, trade simulation or an EA.

Exact HYP009 terminal path:
`03. EA Developer/EA_RoundNumberCascade/research/evidence/HYP-ROUND-CASCADE-EURUSD-M5-009_DESIGN_ECONOMICS/HYP009-DESIGN-ECON-001/attempt_terminal.json`,
SHA256 `5F13B1F51CD7B5A2266640AF17633531F9B16E5D43FB8345DF90B5144A1EC7C7`.

HYP009 parent object binds only:

| Field | Value |
|---|---|
| `attempt_id` | `HYP009-DESIGN-ECON-001` |
| `hypothesis_id` | `HYP-ROUND-CASCADE-EURUSD-M5-009` |
| `status` | `ENGINEERING_INVALID_NO_MARKET_VERDICT` |
| `reason` | `no exact complete observed M5 entry at planned_entry_time_utc` |
| `execution_evidence_class` | `BROKER_OBSERVED_M1_PROXY_KILL_ONLY` |
| `promotion_evidence` | `false` |
| `artifact_sha256.attempt_started.json` | `7692DF408BE6D52A201904D6DB895E5E7387FD99EDAA519D128CE2566DED720D` |

No outcome, trade or metric exists on HYP009.

## 2. Exact HYP008 PASS chain (must bind; do not re-open as production truth)

HYP010 preserves and SHA-binds the exact successful HYP008 execution-source
PASS chain as the prior timestamp-only population that HYP009 attempted to
consume economically:

| Artifact | Path under `.../HYP-ROUND-CASCADE-EURUSD-M5-008_EXECUTION_SOURCE/HYP008-EXEC-SOURCE-001/` | SHA256 |
|---|---|---|
| Attempt terminal | `attempt_terminal.json` | `9EFA0811D46286A2B5FCBBADB814785BA5EC24EC83A90DC73CD998394EBD8E10` |
| Execution receipt | `execution_source_receipt.json` | `A06E602222E20C7B1800F3E92FFA51679A6DDB06D9DE81FC41CF737C9D0B8DF9` |
| Report | `round_cascade_008_execution_source_report.json` | `5F74F6A33FA66D05D131D5727CC6CC31929C748A8B223A820986FD62CD180EEA` |
| Eligible ledger | `round_cascade_008_eligible_source_ledger.jsonl` | `B84EF3925B5CC998A88D224BCF8B4A66D5A6076DFED87C4287325F369AAFF16B` |
| Ineligible ledger | `round_cascade_008_ineligible_source_ledger.jsonl` | `9C48A22BAEF82998038D9D24472A61863AD9DD8BBFF9BD9D52C5C0E66C2E6680` |
| Classification digest | (inside terminal/report) | `97D0CB0FF8E471C961032206B11BC4B6E9ACB0DD13B99ECBED655C064D28F82D` |

HYP008 terminal status:
`PASS_EXECUTION_SOURCE_MAY_DRAFT_HYP009_DESIGN_ECONOMICS` with
`hyp009_drafting_authorized=true`. HYP008 actual counts (forensic only):
eligible TRUE=1220 / SHIFTED=1214; refractory TRUE=8 / SHIFTED=6;
`NO_EXACT_ENTRY` TRUE=1 / SHIFTED=0. HYP010 must **not** hard-delete the three
incomplete-at-planned offenders from those ledgers; it must reclassify the full
HYP002 source under the refined prerequisite order.

## 3. Exact immutable source and public data (unchanged)

- HYP002 source ledger:
  `03. EA Developer/EA_RoundNumberCascade/research/evidence/HYP-ROUND-CASCADE-EURUSD-M5-002_SOURCE_FEASIBILITY/HYP002-SOURCE-PREFLIGHT-001/round_cascade_source_ledger.jsonl`
  SHA256 `8172CB237B74CDA6DED53E5BCECB7DD80163A6BE506750FF1567C65CC31B9FBE`.
- Exact inputs: `TRUE_0050=1229`, `SHIFTED_0025=1220`; every source identity
  unique; ledger canonical LF-only JSONL with per-row LF SHA binding.
- Public DESIGN M1 manifest:
  `02. AlphaFactory/data/fivepercent/EURUSD/splitvault_002/public/design_manifest.jsonl`,
  SHA256 `A8A091DA8365602CB1D02BA571E96B4FB00B50621A73166B8CEDDBC1A7EED8C7`
  (**canonical LF JSONL + exact SHA-bound**).
- Public DESIGN M1 receipt dual-bound:
  path `.../public/design_receipt.json`,
  raw SHA256 `8109B11B6054517B9904FB4ACEF25EB7C6BD2485487CA9D69340DDC7E7D27FF8`,
  semantic object SHA256
  `06AA44C3FB7E42BEDB781CD64826036F43CFFD806E2516F15886E848DAE1AD75`
  (`sha256(canonical_json(parsed_object))`). No raw-canonical-byte requirement.
  Machine-local fields (e.g. `stage_path`) bind only through the frozen object
  hash.
- Immutable public M1 source SHA256:
  `2959C555DB6690FD6EFD6CFB3B4C6323698E590C9B2D71E1E55F1902F724235A`.
- DESIGN is exactly 1,555 ordered manifest dates from `2016-01-04` through
  `2020-12-31`, 1,859,820 rows and one row group per shard.

Physical Parquet producer schema remains the reviewed ten-column public schema,
but HYP010 may request and decode only `columns=['time_utc']`. Every decoded
row must be exactly `{'time_utc': naive timestamp[ns]}` before UTC attachment.
Reading or emitting open/high/low/close, spread, tick volume, real volume,
direction, price, outcome or economic fields is fatal.

## 4. Frozen deterministic arm-local classifier (refined prerequisite order)

Build one immutable chronological timestamp index without sorting away source
faults. Reject a duplicate or any timestamp not strictly greater than its
predecessor. A complete observed M5 start is UTC aligned and has exactly the
five observed timestamps at offsets 0, 1, 2, 3 and 4. Gaps are never filled or
synthesized. Complexity must be O(M1 rows + source rows), with no
`Sequence.index`, per-signal full scan or second full timestamp dictionary.

Process the original HYP002 rows chronologically and independently per arm:

1. Preserve the original source identity and planned timestamp.
2. If no observed public-DESIGN M1 timestamp exists exactly at planned `T`,
   classify `NO_EXACT_ENTRY`. Persist the first later observed timestamp and
   exact calendar-minute delay, or literal null if none. **Reserves nothing.**
3. Else if `T` is **not** itself a member of `complete_m5_starts`, classify
   `NO_COMPLETE_M5_AT_PLANNED`. Persist the first later complete M5 start and
   delay minutes when present. **Reserves nothing.**
4. Else require the first twelve complete observed M5 starts `>= T` with the
   first equal to `T`. If fewer than twelve remain (true right edge), raise
   fail-closed engineering-invalid `ContractError` — not a silent ineligible.
5. Else if `T` is strictly before the current arm-local reserved exit, classify
   `REFRACTORY_INELIGIBLE`. Persist blocking eligible identity, reserved exit
   and overlap minutes. Equality with reserved exit is allowed.
6. Else the row is `ELIGIBLE_EXACT_COMPLETE_M5_NONOVERLAP` and reserves from
   `T` through `twelfth_complete_m5_start + 5 minutes`. The reserved-exit
   timestamp is diagnostic only and is not an economic exit.

Classification must complete for all 2,449 source rows before persistence.
Eligible rows must be pairwise non-overlapping per arm under the conservative
reservation. The two output ledgers together must reproduce every original
source identity exactly once. Independent random-access replay must
canonical-hash equal the streaming classification.

### Forensic note (not a production gate)

Independent timestamp-only diagnosis of HYP008 PASS eligible ledgers found
exactly three rows that would fail prerequisite (2) under HYP010
(`TRUE_0050=2`, `SHIFTED_0025=1`, next complete M5 typically +5 minutes). Treat
those counts as forensic expectation for review. Production must recompute
`NO_COMPLETE_M5_AT_PLANNED` from bytes; it must not hardcode
`NO_COMPLETE == {TRUE:2, SHIFTED:1}` as a fatal acceptance constant. Because
those rows no longer reserve, later same-arm rows may become eligible that were
refractory under HYP008 — that is intended source-contract refinement, not
market rescue.

## 5. Safe timestamp diagnostics and outcome-blind guard (preserved from HYP008)

After a successful timestamp-only DESIGN decode, the builder may report exactly
these three diagnostic counters and no others for that readout:

| Key | Meaning |
|---|---|
| `design_shards_read` | number of SHA-bound public DESIGN shards decoded |
| `design_timestamp_rows_read` | number of decoded `time_utc` rows |
| `design_bytes_read` | total raw shard bytes read under the manifest |

The outcome-blind visitor must:

1. accept only those three exact keys as the safe-diagnostic allowlist;
2. require each value to be a nonnegative plain integer
   (`type(value) is int`, not `bool`, and `value >= 0`);
3. reject wrong types (float/bool/str/None), negative values, and nested
   or renamed variants;
4. **not** broadly weaken the guard: actual or nested
   open/high/low/close/price/spread/volume/direction/trade/return/PnL/profit/
   performance/economic/outcome fields must still fail; retired
   `design_shards_opened` / `design_bytes_opened` names must still fail.

## 6. Stage-0 gates (source execution only)

Fatal / hard gates:

- exact HYP002 source counts `TRUE_0050=1229`, `SHIFTED_0025=1220`;
- exact-once identity reconciliation across eligible + ineligible;
- fatal `NO_EXACT_ENTRY` expectation `TRUE_0050=1`, `SHIFTED_0025=0` (unchanged
  missing-entry identity surface from HYP002/HYP008);
- eligible rows must have exact observed M1 **and** complete M5 at planned
  with twelve-complete horizon and non-overlapping arm-local reservation;
- independent replay hash match;
- timestamp-only outcome-blind report;
- dual historical DESIGN receipt raw+object SHA + canonical manifest SHA;
- no horizon-incomplete silent status (right edge is engineering-invalid).

Non-fatal diagnostics only:

- eligible / refractory / `NO_COMPLETE_M5_AT_PLANNED` arm counts;
- the three-row forensic incomplete-at-planned expectation.

## 7. One-shot durability, authority, and sealed permissions

- Attempt id: `HYP010-EXEC-SOURCE-001` (exactly one).
- Fresh evidence root:
  `03. EA Developer/EA_RoundNumberCascade/research/evidence/HYP-ROUND-CASCADE-EURUSD-M5-010_EXECUTION_SOURCE/HYP010-EXEC-SOURCE-001`
  (create-new; replay forbidden if root exists).
- Fresh independent implementation review receipt path/schema:
  `HYP-ROUND-CASCADE-EURUSD-M5-010_EXECUTION_SOURCE_IMPLEMENTATION_REVIEW_RECEIPT.json`
  with schema `round_cascade_010_execution_source_implementation_review.v1`.
- Builder sentinel `REVIEWED_REGISTRY_ROW_SHA256` ships disarmed as `None`.
  Production read requires both `--execute-probe` and an independently reviewed
  canonical registry-row SHA in that sentinel.
- Generic registry surface (canonical validator + schema) with
  `source_run_authorized` / `execution_source_only` / `source_feasibility_only`
  true; all economics/price/MT5/MQL5/validation/holdout/private/promotion/
  network/paid permissions sealed false; source-only zero metrics.
- Create-new artifact writer; independent replay; exact-once reconciliation.

PASS verdict only:
`PASS_EXECUTION_SOURCE_MAY_DRAFT_HYP011_DESIGN_ECONOMICS`.

On PASS, the sole authorized next drafting step is a **fresh HYP011
DESIGN-economics plan** that consumes the exact-complete eligible ledger.
HYP011 drafting remains plan-only until separate registry/prereg ceremony; it
must state that HYP010 refined the source contract after a timestamp-only
mismatch (HYP009 emitted no trades/economics), not market rescue.

## 8. Explicit prohibitions

- No price/OHLC/volume decode; no trade simulation; no economics; no MT5/MQL5.
- No parquet production read from this pre-outcome builder task; no evidence
  root creation in this implementer task; no registry mutation.
- No post-hoc deletion of HYP008 eligible offenders; reclassify full source.
- No hardcoded fatal gate on the three forensic incomplete rows.
- No promotion / live / paper / holdout / validation / private custody.

## 9. Builder / test contract for this freeze

Artifacts to implement under this plan (pre-outcome, disarmed):

1. This plan (frozen text).
2. `build_round_cascade_010_execution_source.py` — inert on import; one-shot
   production path behind `--execute-probe` + armed sentinel.
3. `tests/test_build_round_cascade_010_execution_source.py` — focused unit
   coverage including: prerequisite-before-refractory, no state reservation by
   incomplete entries, re-eligibility of later rows after incomplete, equality
   at reserved exit, independent replay, parent HYP009 terminal binding, HYP008
   PASS chain constants, safe diagnostics int guard, sealed permissions, AST
   no `.index(` / no price columns, disarmed default execute.

DONE for the implementer task: exactly those three artifacts, focused tests
PASS, sentinel `None`, and SHA evidence of the three files.
