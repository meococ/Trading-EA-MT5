# DATASET-FIVEPERCENT-EURUSD-H1-SPLITVAULT-001 — COLLECTION PLAN

Status: `FROZEN_PRE_DECODE_PRE_OUTCOME`

## 1. Purpose and authority boundary

- Collection ID: `DATASET-FIVEPERCENT-EURUSD-H1-SPLITVAULT-001`.
- Consumer hypothesis: `HYP-TRENDSTACK-EURUSD-H1-005`.
- This is a fresh H1 outcome contract. It is not a retry, repair, resume or
  substitute result for HYP-004.
- The only authorized purpose is to create an engineering-valid physical
  DESIGN H1 capability for a later separate HYP-005 DESIGN economic packet.
- The generic custodian may decode the complete immutable H1 corpus but may not
  receive signal directions, arms, ATR, stops, PnL, gates or performance code.

## 2. Immutable source

- Source path:
  `02. AlphaFactory/data/fivepercent/EURUSD/EURUSD_H1_2015_now.parquet`.
- Source SHA256:
  `71860016AF1BD1B17353B043AFF799233A787E9DF3F587913FCD2F5328BB1E08`.
- Source bytes: `2,781,897`.
- Source rows from Parquet footer metadata: `71,785`.
- Source row groups: `1`; direct strategy-process access is forbidden because
  the row group spans DESIGN, VALIDATION and HOLDOUT.
- Footer length: `5,392` bytes from little-endian `payload[-8:-4]`.
- Footer start: `2,776,497 = file_bytes - 8 - footer_length`.
- Footer digest range: exact `payload[footer_start:file_bytes]`.
- Footer SHA256:
  `01C090CF494A45AC99603E8A4BBE3447884253DEF3828964AE5555086FF91E3B`.
- Root manifest SHA256:
  `2CD996FD4416B1E888BF1C9D272BF49056DB3A4CE477CF74FA4E31D474A41B54`.
- Clock model SHA256:
  `A7F179935102B57BA3B629345209F6B0D668D1F7FD828A5ED6003207F41A2F52`.

Only non-price metadata above was inspected before freeze. No post-decision H1
row, return, strategy outcome or performance metric was opened for HYP-005.

## 3. Physical split contract

The generic custodian must create a new immutable vault at
`02. AlphaFactory/data/fivepercent/EURUSD/h1_splitvault_001` using UTC time:

- `PRE_DESIGN`: `time_utc < 2016-01-04T00:00:00Z`, private custody only;
- `DESIGN`: `2016-01-04T00:00:00Z <= time_utc < 2021-01-01T00:00:00Z`,
  public DESIGN capability;
- `VALIDATION`: `2021-01-01T00:00:00Z <= time_utc < 2023-01-01T00:00:00Z`,
  sealed and unavailable to research;
- `HOLDOUT`: `time_utc >= 2023-01-01T00:00:00Z`, sealed and unavailable to
  research.

Each source row must be assigned exactly once. Every UTC date becomes one
regular, one-row-group Parquet shard with a canonical manifest row binding
date, split, relative path, rows, bytes and SHA256. Duplicate or ambiguous UTC
opens, invalid schema/types, non-finite or non-positive OHLC, invalid OHLC
geometry, server/UTC/offset mismatch, row loss, row duplication, hardlink,
reparse point or identity replacement invalidates the attempt.

The public receipt may expose only aggregate DESIGN custody metadata. It must
state that VALIDATION and HOLDOUT research access did not occur. Private and
sealed paths, identities, dates, counts and aggregates may not reach the HYP-005
builder or evaluator.

## 4. HYP-005 DESIGN projection contract

The trusted source builder receives only:

- the accepted HYP-002 Stage-0 physical projection of exactly `1,297` frozen
  DESIGN opportunity dates, date-set SHA256
  `4F30B5E09C8C21C3FCB63F4D5A016EB514D689710589077427464B92CD99A06A`;
- the public DESIGN H1 capability produced by this collection.

For each frozen date require exactly one finite valid H1 row at every UTC open
`12:00`, `13:00`, `14:00`, `15:00`, `16:00`, `17:00`, `18:00`. The source
output therefore requires exactly `7` H1 rows per date and `9,079` total rows.
Missing, duplicate or ambiguous required H1 opens invalidate the source attempt.
No fill, interpolation, resampling, date drop, alternate source or partial PASS
is legal.

Fresh output identities:

- final output:
  `02. AlphaFactory/data/fivepercent/EURUSD/trendstack_005_design_h1`;
- attempt stage:
  `02. AlphaFactory/data/fivepercent/EURUSD/.trendstack_005_design_h1.attempt-<attempt-id>`;
- evidence:
  `03. EA Developer/EA_TrendStackContinuation/research/evidence/HYP-TRENDSTACK-EURUSD-H1-005_SOURCE_ATTEMPTS/<attempt-id>`.

## 5. One-shot and routing

Before any source-content decode, a canonical run packet must bind the frozen
plans, registry row, exact source/footer/manifest/clock, all tool and test
hashes, fresh paths and an independent reviewed packet SHA. The supervisor is
disarmed by default and may be armed for exactly one reviewed attempt.

The durable attempt marker must exist before the generic custodian opens source
content. Any failure after the marker consumes the attempt. No same-ID retry,
resume, output reuse or widening is allowed.

- Integrity/custody/projection/schema/completeness/validator failure: park
  engineering-invalid with no market verdict.
- Independent source PASS may emit only
  `SOURCE_READY_FOR_SEPARATE_DESIGN_ECONOMIC_RUN_PACKET`.
- Source PASS grants no economics, EA, MQL5, Model 0, validation outcome,
  holdout, promotion, paper, live or deployment authority.

