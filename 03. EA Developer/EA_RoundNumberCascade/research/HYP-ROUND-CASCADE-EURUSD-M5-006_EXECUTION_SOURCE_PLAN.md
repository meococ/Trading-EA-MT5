# HYP-ROUND-CASCADE-EURUSD-M5-006 — Execution-Source Plan

Status: `FROZEN_PRE_OUTCOME_IMPLEMENTATION_CHILD`

## 1. Identity and exact failure radius

- Hypothesis: `HYP-ROUND-CASCADE-EURUSD-M5-006`.
- Parent: terminal `HYP-ROUND-CASCADE-EURUSD-M5-005` attempt
  `HYP005-DESIGN-ECON-001`.
- Attempt: `HYP006-EXEC-SOURCE-001`, limit exactly one.
- Source signal parent: `HYP-ROUND-CASCADE-EURUSD-M5-002`.
- Package: `EA_RoundNumberCascade`.
- Scope: public-DESIGN timestamp-only execution eligibility. This is not an
  economic run and cannot authorize price access, trade simulation or an EA.

The exact HYP005 terminal path is
`03. EA Developer/EA_RoundNumberCascade/research/evidence/HYP-ROUND-CASCADE-EURUSD-M5-005_DESIGN_ECONOMICS/HYP005-DESIGN-ECON-001/attempt_terminal.json`,
SHA256 `857C73EA9631D4BF8288E536A556BABDF083D2EBC67CA2C502DE647F00993830`.
It contains only the started-artifact binding, status
`ENGINEERING_INVALID_NO_MARKET_VERDICT` and reason
`entry delay exceeds 60 minutes`; no outcome, trade or metric exists.

HYP006 changes the decision surface from “every fixed source row must become an
economic trade” to a fresh, outcome-blind execution-source population. No
source signal is deleted, mutated, delayed, reselected or assigned a price.
Every input row persists exactly once in either the eligible or diagnostic
ineligible ledger under its original `(arm, planned_entry_time_utc)` identity.

## 2. Exact immutable source and public data

- HYP002 source ledger:
  `03. EA Developer/EA_RoundNumberCascade/research/evidence/HYP-ROUND-CASCADE-EURUSD-M5-002_SOURCE_FEASIBILITY/HYP002-SOURCE-PREFLIGHT-001/round_cascade_source_ledger.jsonl`
  with SHA256
  `8172CB237B74CDA6DED53E5BCECB7DD80163A6BE506750FF1567C65CC31B9FBE`.
- Exact inputs: `TRUE_0050=1229`, `SHIFTED_0025=1220`; every source identity
  must be unique and the ledger must be canonical LF-only JSONL.
- Public DESIGN M1 manifest:
  `02. AlphaFactory/data/fivepercent/EURUSD/splitvault_002/public/design_manifest.jsonl`,
  SHA256 `A8A091DA8365602CB1D02BA571E96B4FB00B50621A73166B8CEDDBC1A7EED8C7`.
- Public DESIGN M1 receipt:
  `02. AlphaFactory/data/fivepercent/EURUSD/splitvault_002/public/design_receipt.json`,
  SHA256 `8109B11B6054517B9904FB4ACEF25EB7C6BD2485487CA9D69340DDC7E7D27FF8`.
- Immutable public M1 source SHA256:
  `2959C555DB6690FD6EFD6CFB3B4C6323698E590C9B2D71E1E55F1902F724235A`.
- DESIGN is exactly 1,555 ordered manifest dates from `2016-01-04` through
  `2020-12-31`, 1,859,820 rows and one row group per shard.

The physical Parquet producer schema remains the exact reviewed ten-column
public schema, but HYP006 may request and decode only `columns=['time_utc']`.
Every decoded row must be exactly `{'time_utc': naive timestamp[ns]}` before UTC
attachment. Reading or emitting open/high/low/close, spread, tick volume, real
volume, direction, price, outcome or economic fields is fatal.

## 3. Frozen deterministic arm-local classifier

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
   exact calendar-minute delay, or literal null if none. It reserves nothing.
3. Otherwise, if `T` is strictly before the current arm-local reserved exit,
   classify `REFRACTORY_INELIGIBLE`. Persist the blocking eligible identity,
   reserved exit and overlap minutes. Equality with reserved exit is allowed.
4. Otherwise, select the first twelve complete observed M5 starts `>=T`.
   Fewer than twelve is engineering-invalid, not a silent ineligible row.
5. The row is `ELIGIBLE_EXACT_ENTRY_NONOVERLAP` and reserves from `T` through
   `twelfth_complete_m5_start + 5 minutes`. This reserved-exit timestamp is
   diagnostic only and is not an economic exit.

Classification must complete for all 2,449 source rows before persistence.
Eligible rows must be pairwise non-overlapping per arm under the conservative
reservation. The two output ledgers together must reproduce every original
source identity exactly once.

## 4. Pre-outcome timestamp expectations, not count gates

Independent timestamp-only pre-freeze forensics established expectations that
the production implementation must recompute from the exact source and public
DESIGN bytes:

- Expected replay readout: eligible `TRUE_0050=1220`,
  `SHIFTED_0025=1214`; refractory eight TRUE and six SHIFTED. These eligible
  and refractory counts are diagnostics, not fatal acceptance constants.
- The fatal missing-entry expectation is exactly one TRUE and zero SHIFTED
  `NO_EXACT_ENTRY`. No horizon-incomplete row is permitted.
- The sole no-exact identity is
  `TRUE_0050|2017-03-31T21:00:00Z`, LF-row SHA256
  `E814CE2D8038F94965A7B7C78C459D82C029C43A10D04CAEF5377529C3F43FD4`.
  Its next observed M1 must be `2017-04-02T21:00:00Z`, delay 2,880 minutes.

The exact refractory identities and blockers are:

| Arm | Ineligible planned T | Blocking eligible planned T | Reserved exit |
|---|---|---|---|
| TRUE | 2016-06-20T00:00Z | 2016-06-19T23:55Z | 2016-06-20T00:55Z |
| TRUE | 2017-06-12T00:00Z | 2017-06-11T23:45Z | 2017-06-12T00:45Z |
| TRUE | 2017-10-30T00:05Z | 2017-10-29T23:15Z | 2017-10-30T00:15Z |
| TRUE | 2018-01-22T00:20Z | 2018-01-21T23:45Z | 2018-01-22T00:45Z |
| TRUE | 2018-02-05T00:25Z | 2018-02-04T23:45Z | 2018-02-05T00:45Z |
| TRUE | 2018-12-10T00:05Z | 2018-12-09T23:20Z | 2018-12-10T00:20Z |
| TRUE | 2020-08-17T00:05Z | 2020-08-16T23:55Z | 2020-08-17T00:55Z |
| TRUE | 2020-12-28T00:05Z | 2020-12-27T23:30Z | 2020-12-28T00:30Z |
| SHIFTED | 2016-02-15T00:15Z | 2016-02-14T23:40Z | 2016-02-15T00:40Z |
| SHIFTED | 2017-05-15T00:00Z | 2017-05-14T23:25Z | 2017-05-15T00:25Z |
| SHIFTED | 2018-01-29T00:15Z | 2018-01-28T23:50Z | 2018-01-29T00:50Z |
| SHIFTED | 2018-03-05T00:15Z | 2018-03-04T23:20Z | 2018-03-05T00:20Z |
| SHIFTED | 2018-04-23T00:25Z | 2018-04-22T23:55Z | 2018-04-23T00:55Z |
| SHIFTED | 2020-03-30T00:05Z | 2020-03-29T23:45Z | 2020-03-30T00:45Z |

The table is a review aid for the expected deterministic replay; production
does not compare eligible or refractory counts or identities against this
table. Runtime truth comes from the exact source/data bytes and frozen state
machine. It must canonical-hash the complete classification, independently
replay it and require the second canonical hash to equal the first. HYP007 must
bind the actual eligible-ledger hash and actual eligible observation count.
These remain source-execution facts, not trade selection based on an economic
result.

## 5. PASS meaning and sealed permissions

`PASS_EXECUTION_SOURCE_MAY_DRAFT_HYP007_DESIGN_ECONOMICS` requires exact parent,
source, data and authority contracts plus all frozen Stage-0 gates:

1. input counts `TRUE_0050=1229`, `SHIFTED_0025=1220`;
2. every source identity appears exactly once across eligible/ineligible;
3. `NO_EXACT_ENTRY` is exactly one TRUE and zero SHIFTED;
4. every eligible row has an exact observed M1 at planned T and twelve complete
   observed M5 bars;
5. arm-local eligible reservations do not overlap; equality is allowed;
6. no `HORIZON_INCOMPLETE` classification exists;
7. independent deterministic replay produces the identical canonical
   classification SHA256;
8. timestamp-only decoder/output and all sealed zero counters pass.

Eligible and refractory counts are reported actuals, not Stage-0 thresholds.
PASS authorizes only drafting a separately reviewed and frozen HYP007
DESIGN-economics plan. It does not authorize price access, economics, MQL5,
MT5, promotion, paper or live trading.

Validation, holdout, private custody, monolithic source, H1, OHLC, spread,
tick/real volume, post-decision prices, direction-based filtering, trade,
return, PnL, PF, DSR, optimization, economics, network and paid access remain
literal false. No chart or economic metric may be emitted.

## 6. Authority, durability and current implementation scope

The sentinel remains exactly
`REVIEWED_REGISTRY_ROW_SHA256: str | None = None`. A future execution requires
an explicit run switch; the exact latest canonical registry row; zero errors
from the hash-bound canonical registry validator/schema; exact plan, normalized
builder, tests and independent review receipt bindings; and strict validation
of the exact HYP005 terminal before source ledger or DESIGN metadata access.

After authority validation, reserve the one-use evidence root atomically and
persist `attempt_started.json` before any public DESIGN metadata or shard. The
success order is eligible ledger, ineligible ledger, report, receipt and
terminal. Every artifact is create-new, fsync'd, read back and SHA-bound. Any
exception after reservation must create an engineering-invalid terminal with
the hashes of all already durable artifacts. Replay, overwrite, deletion and
same-ID rerun are forbidden.

This implementation task owns exactly:

1. this plan;
2. `build_round_cascade_006_execution_source.py`;
3. `tests/test_build_round_cascade_006_execution_source.py`.

It does not create a review receipt, registry row, run packet, evidence root or
production artifact and does not arm or execute the probe.
