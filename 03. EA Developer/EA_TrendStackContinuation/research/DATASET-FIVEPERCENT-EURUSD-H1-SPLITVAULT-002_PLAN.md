# DATASET-FIVEPERCENT-EURUSD-H1-SPLITVAULT-002 — COLLECTION PLAN

Status: `FROZEN_IDEA_PRE_DECODE_PRE_OUTCOME`

## 1. Identity and legal parentage

- Collection ID: `DATASET-FIVEPERCENT-EURUSD-H1-SPLITVAULT-002`.
- Consumer: `HYP-TRENDSTACK-EURUSD-H1-006`.
- HYP-005 is parked
  `PARK_PREREG_INVALID_BEFORE_SOURCE_NO_MARKET_VERDICT`; failure manifest SHA256
  `4141AE86C6BD58270DA1D833252E3738C13B0BF298636A998E61DF2C4A4715B0`.
- HYP-002 row 272, SHA256
  `6D228F1275D082D439C680AC762960A6BAA855989883D3105DD4438CE1100DD9`,
  proves the terminal M1 object returned 356/360 rows on 2016-03-11 and omitted
  16:40 through 16:43 UTC. Its failure-manifest SHA256 is
  `3016A46FC3952046FD90439D5D666426BB02E2E43F2149D1EB82B7C595BC5FF2`.

This collection is for a materially new H1 OHLC execution object. It cannot
repair, retry, fill, drop or reinterpret any M1 object. The generic custodian
may split the immutable H1 source but cannot receive directions, arms, ATR,
stops, costs, PnL, gates or performance code.

## 2. Immutable source and exact schema

- Source:
  `02. AlphaFactory/data/fivepercent/EURUSD/EURUSD_H1_2015_now.parquet`.
- Whole-file SHA256:
  `71860016AF1BD1B17353B043AFF799233A787E9DF3F587913FCD2F5328BB1E08`.
- Bytes: `2,781,897`; footer-metadata rows: `71,785`; row groups: `1`.
- Footer length: `5,392` from little-endian `payload[-8:-4]`.
- Footer start: `2,776,497 = file_bytes - 8 - footer_length`.
- Exact footer digest range: `payload[footer_start:file_bytes]`.
- Footer SHA256:
  `01C090CF494A45AC99603E8A4BBE3447884253DEF3828964AE5555086FF91E3B`.
- Root manifest:
  `02. AlphaFactory/data/fivepercent/EURUSD/manifest.json`, SHA256
  `2CD996FD4416B1E888BF1C9D272BF49056DB3A4CE477CF74FA4E31D474A41B54`.
- The bound manifest states broker `FivePercentOnline-Real (demo, read-only
  pull)`, symbol `EURUSD`, coverage `2015-01-02 .. 2026-07-17`, and `H1/H4/M1,
  closed bars, bid`. Therefore every H1 OHLC field in this contract is a closed
  BID bar; no ask or mid-price interpretation is legal.
- Clock:
  `02. AlphaFactory/tools/research/fivepercent_server_clock.py`, SHA256
  `A7F179935102B57BA3B629345209F6B0D668D1F7FD828A5ED6003207F41A2F52`.

Exact Arrow schema, with no extra/missing/reordered fields:

```text
time_server: timestamp[ns]  # timezone-naive broker-server open
time_utc: timestamp[ns]     # timezone-naive canonical UTC open
utc_offset_h: int8
open: float64               # bid
high: float64               # bid
low: float64                # bid
close: float64              # bid
tick_volume: uint64
spread: int32
real_volume: uint64
```

Require `time_server == server_from_utc(time_utc)` and exact integer
`utc_offset_h == (time_server - time_utc) / 1 hour` under the bound clock.
Duplicate or ambiguous UTC opens, nulls, non-finite/non-positive OHLC or invalid
`low <= min(open,close) <= max(open,close) <= high` invalidate the attempt.
`spread` is retained only as source data; it is forbidden as cost truth.

Only footer/schema/manifest metadata was inspected before freeze. No source
price row or HYP-006 outcome was opened.

## 3. Physical custody split

Fresh final vault:
`02. AlphaFactory/data/fivepercent/EURUSD/h1_splitvault_002`.

- `PRE_DESIGN`: `time_utc < 2016-01-04T00:00:00Z`, private;
- `DESIGN`: `[2016-01-04T00:00:00Z, 2021-01-01T00:00:00Z)`, public;
- `VALIDATION`: `[2021-01-01T00:00:00Z, 2023-01-01T00:00:00Z)`, sealed;
- `HOLDOUT`: `time_utc >= 2023-01-01T00:00:00Z`, sealed.

Assign every source row exactly once. Write one regular, one-row-group Parquet
shard per UTC date and a canonical manifest row binding date, split, relative
path, row count, bytes and SHA256. Reconcile source total rows and a deterministic
chain hash. Hardlinks, symlinks/reparse points, alternate data streams, identity
replacement, path overlap and non-create-new publication are forbidden.

The public DESIGN capability exposes only DESIGN data. The research process may
not stat, enumerate, read or receive any private, VALIDATION or HOLDOUT path,
date, count, identity, hash, aggregate or row. A public receipt must attest
`research_validation_opened=false` and `research_holdout_opened=false`.

## 4. DESIGN projection and output

The source builder receives only the public DESIGN capability plus the accepted
HYP-002 Stage-0 projection:

- ledger SHA256
  `3092A6FCFADE0DA23E4470C4BF3B1D7750190358CF6ED09A2BB942937A7CD3C7`;
- receipt SHA256
  `5AEA570736361EF22BF2F090A5C05EF2974F482B5CB34A1186F27D9B43AAF5CE`;
- exactly `1,297` sorted unique DESIGN dates, date-set SHA256
  `4F30B5E09C8C21C3FCB63F4D5A016EB514D689710589077427464B92CD99A06A`.

For each projected date require exactly one valid BID H1 row at each UTC open
`12:00`, `13:00`, `14:00`, `15:00`, `16:00`, `17:00`, `18:00`: exactly `7`
rows/date and `9,079` rows total. Preserve the exact source schema above. A
missing/duplicate/ambiguous required row invalidates the source attempt; no
fill, interpolation, resample, dedupe, date drop, alternate source, partial PASS
or selection after seeing outcomes is legal.

Fresh output:
`02. AlphaFactory/data/fivepercent/EURUSD/trendstack_006_design_h1`.
Fresh stage:
`02. AlphaFactory/data/fivepercent/EURUSD/.trendstack_006_design_h1.attempt-<attempt-id>`.
Fresh evidence:
`03. EA Developer/EA_TrendStackContinuation/research/evidence/HYP-TRENDSTACK-EURUSD-H1-006_SOURCE_ATTEMPTS/<attempt-id>`.

## 5. Non-circular one-shot protocol

The production supervisor is reviewed and hashed with exactly
`REVIEWED_RUN_PACKET_SHA256: str | None = None`; this is the immutable review
base SHA. A separate reviewer creates/verifies the canonical packet SHA. Only
then may the parent replace that exact line with the reviewed packet SHA for one
run. The attempt marker binds both review-base and armed-runtime supervisor
SHAs. The supervisor must be disarmed back to `None` immediately after terminal
success or failure.

Before any source-content open, verify all non-source bindings: plan/registry,
packet canonicality, source path metadata without content, footer/manifest/clock,
tool/test hashes, fresh evidence/stage/output paths, filesystem identities and
no forbidden processes. Create the evidence root and exclusive canonical
`attempt_started.json`; flush the file and directory. Marker fields include
hypothesis/collection/attempt IDs, packet SHA, registry row/index/hash, both plan
hashes, source whole/footer metadata, all tool/test SHAs, review-base/runtime
supervisor SHAs, fresh paths and `verdict=ATTEMPT_CONSUMED`.

Only after durable marker readback may the generic custodian open source content.
Any failure after marker consumes the attempt. Terminal evidence must record
the sanitized failure phase plus child return code and SHA256 of captured stderr
without exposing raw price rows. Same-ID retry/resume, stage reuse or authority
widening is forbidden.

## 6. Runtime prohibitions and routing

Forbidden runtime inputs include all M1 monoliths, HYP-002 quarantine shards and
packet, HYP-003/HYP-004 stages/packets, `splitvault_002`, all eight unfinished
HYP-005 candidate tool/test files, VALIDATION/HOLDOUT data, network, nested
subprocesses, MT5, MQL5 and external source substitution.

- Custody/projection/schema/completeness/identity/validator failure: park
  engineering-invalid, no market verdict, no same-ID retry.
- Independent source PASS may emit only
  `SOURCE_READY_FOR_SEPARATE_DESIGN_ECONOMIC_RUN_PACKET`.
- No collection/source result authorizes economics, EA, MQL5, Model 0,
  validation outcome, HOLDOUT, promotion, paper, live or deployment.

