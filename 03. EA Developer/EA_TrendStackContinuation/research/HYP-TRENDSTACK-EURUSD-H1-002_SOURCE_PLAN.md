# SOURCE + PROBE PLAN — HYP-TRENDSTACK-EURUSD-H1-002

Status: FROZEN 2026-07-28 before any HYP-002 source acquisition, feature
packet, M1 outcome, PnL, or economic metric. This successor repairs only the
physically-invalid HYP-001 data-access contract. The market mechanism, clocks,
lookback, splits, controls, costs and gates are unchanged. This file becomes
immutable when its SHA256 is bound into the registry `probe` row.

## 1. Identity and parent failure

- `hypothesis_id`: `HYP-TRENDSTACK-EURUSD-H1-002`
- Package: `EA_TrendStackContinuation`; research-only. No `.mq5`, Model 0,
  paper, live, or promotion authority exists.
- Parent: `HYP-TRENDSTACK-EURUSD-H1-001`, parked
  `ENGINEERING_INVALID_NO_MARKET_VERDICT`.
- Parent plan SHA256:
  `891291042FB326EF67411A0763015B4E3E68654F59E4B323C2217F1E8015B6F0`.
- Parent failure: the only historical H1 parquet has one 71,785-row row group.
  Arrow filtering and one-row batches limited yielded rows but still decoded or
  prefetched future OHLC. HYP-001 opened no M1, PnL, economic metric, validation
  outcome or holdout; the mechanism remains untested.
- HYP-002 changes only the source plane to physically isolated source-only
  decision packets. It must not use HYP-001 counts as authority.

## 2. Unchanged hypothesis and failure radius

- Instrument / decision TF: FivePercent `EURUSD`, H1 decision features.
- `M252` is the core directional signal. `M6` is a same-direction qualification
  gate; the claim is that agreement improves standalone M252 and M6.
- `M252 = sign(valid_daily_closes[-1] / valid_daily_closes[-253] - 1)` using
  only valid UTC dates strictly before decision date `d`. A valid date has
  finite positive unique OHLC and at least 20 distinct H1 UTC opens; daily close
  is its latest H1 close. Require 253 accepted closes. Snapshot at 06:00 UTC.
- Require exactly the closed H1 bars with UTC opens 06:00 through 11:00 on `d`.
  `M6 = sign(close_11:00 / open_06:00 - 1)`. Equality is no signal.
- Decision cutoff is 12:00 UTC. Maximum one opportunity per UTC date.
- `ATR20_mt5` is the SMA of H1 True Range through the closed 11:00 bar,
  equivalent to MT5 iATR H1 period 20, CopyBuffer shift 1 at 12:00. Wilder ATR
  is forbidden. Stop multiple remains exactly `1.0 × ATR20`.
- Four arms and total trial count remain exactly four:
  `CONTROL_M252_ONLY`, `CONTROL_M6_ONLY`, `CHALLENGER_STACK`, and
  `NEGATIVE_DISAGREE` (direction M6 on disagreement days).
- No grid or change to 252, 06/12/18 UTC, ATR, symbol, TF, direction, cost,
  split, weekday/year/session, exit, or gates. Any such change after HYP-001
  counts is post-hoc rescue and requires a different mechanism/ID.

## 3. Frozen splits and cadence denominators

- Feature-only WARMUP: 2015-01-02 through 2016-01-03; never scored.
- DESIGN: `[2016-01-04T00:00:00Z, 2021-01-01T00:00:00Z)` = 1,824 elapsed
  days / 260.571428571 weeks.
- VALIDATION_FEATURE_ONLY for Stage 0:
  `[2021-01-01T00:00:00Z, 2023-01-01T00:00:00Z)` = 730 elapsed days /
  104.285714286 weeks. Validation M1 outcomes remain unavailable until DESIGN
  passes every economic gate.
- HOLDOUT: all timestamps `>=2023-01-01T00:00:00Z`. No HYP-002 request,
  returned row, shard, packet, path, aggregate or outcome may touch holdout.
- Stage-0 challenger count gates are unchanged: DESIGN 522..1302 inclusive;
  VALIDATION 209..521 inclusive; each split at least 50 LONG and 50 SHORT.

## 4. Physically sealed source acquisition

### Process boundary

- Only `prepare_trendstack_002_source.py` may import the MetaTrader5 package or
  read H1 raw bars. It accepts an explicit local terminal executable argument;
  no machine path is hardcoded into a source file intended for Git.
- It must initialize in read-only mode, require terminal-side trading disabled,
  a demo account, exact FivePercent server/company, and EURUSD digits/point.
  `mt5.shutdown()` is mandatory in `finally`.
- Capture at runtime: terminal build and executable SHA, Python executable SHA,
  MetaTrader5 version and native-module SHA, clock-tool SHA, extractor SHA,
  this plan SHA, account mode/server/company, and symbol geometry. Do not store
  credentials or account secrets.
- H1 acquisition uses bounded `copy_rates_range` month chunks only. Every
  request and response must end strictly before `2023-01-01T00:00:00Z`.
  Returned out-of-range/holdout rows, duplicate/non-monotonic UTC opens, clock
  ambiguity, broker mismatch, trading enabled, or hash drift invalidates the
  whole acquisition; never filter an illegal response and continue.
- Do not read or compare the parent one-row-group parquet during acquisition.
  It is historical provenance only, not HYP-002 source authority.

### Physical layout

All persisted data stays on D under:

`02. AlphaFactory/data/fivepercent/EURUSD/trendstack_002/`

Required layout:

```text
raw_h1/<split>/<YYYY-MM-DD>/pre12.parquet
raw_h1/<split>/<YYYY-MM-DD>/post12.parquet
source_manifest.jsonl
source_validation_receipt.json
decision_packets/<split>/<YYYY-MM-DD>.json
decision_packet_manifest.jsonl
decision_packet_receipt.json
```

- Each daily `pre12` and `post12` is a separate physical file with a single
  small row group. `pre12` contains UTC opens `<12:00`; `post12` contains opens
  `>=12:00`. No file mixes the segments. No 2023+ directory/file is allowed.
- Raw shards exist only for source audit/reproduction. The Stage-0 strategy
  process receives no raw-root capability and cannot import parquet tooling.
- Raw files are immutable create-new artifacts. Existing paths or hash drift
  fail closed; no overwrite. A failed source attempt must be quarantined under
  a new run ID, not silently replaced.

### Source-only feature packets

The source process builds one immutable JSON packet per scored UTC date, in
chronological order. It may use completed prior-day `post12` shards only to
finalize a daily close for a later decision. For current date `d`, its maximum
source timestamp is the H1 open 11:00 and is strictly before decision cutoff.

Each packet contains only:

- hypothesis ID, opportunity ID/date, split, decision cutoff;
- M252 and M6 direction, alignment, ATR20, four eligibility flags and exclusion
  reason;
- valid-prior-close count, maximum source timestamp;
- exact source-shard chain hashes, extractor SHA, source-plan SHA and packet
  SHA.

Forbidden packet fields include raw open/high/low/close, any timestamp at/after
12:00 on `d`, return/PnL/exit/MFE/MAE/future-price fields, M1 data, credentials,
or holdout identity. A schema and explicit forbidden-field scan fail closed.

`source_manifest.jsonl` records request ID/range, response first/last server and
UTC timestamps, shard path/split/segment/rows/bytes/SHA, canonical row-content
SHA, runtime/tool hashes, duplicate/gap/geometry checks, and
`holdout_rows_received=0`.

`source_validation_receipt.json` hash-binds the manifest and every shard; states
file/row counts, maximum UTC timestamp, terminal/account guards, no 2023+
request/row/file, `m1_opened=false`, `outcomes_opened=false`, and
`physical_partition_status=PASS`.

`decision_packet_manifest.jsonl` binds every opportunity ID, packet SHA, source
chain, source max time, extractor/plan hashes, forbidden-field result and split.
`decision_packet_receipt.json` binds both manifests/receipts, proves unique IDs,
no 2023+ packet/outcome field, deterministic rebuild, and
`strategy_process_raw_source_access=false`.

## 5. Stage-0 physical access protocol

- `stage0_trendstack_002_worker.py` must not import MetaTrader5, pyarrow, pandas,
  parquet readers, or contain/enumerate a raw-source/packet-root path. It accepts
  exactly one explicit packet path and expected SHA, schema-validates it, emits
  one eligibility row, then exits.
- A supervisor enumerates only the packet manifest, copies or hardlinks exactly
  one verified packet into a per-decision temporary input directory, spawns a
  fresh worker, hash-appends/finalizes the result row, removes the temporary
  input, then releases the next packet. The worker cannot see future packets.
- Persist a canonical access trace sufficient for an independent verifier to
  recompute packet order, expected/actual SHA, worker invocation count, output
  row hash, prior-ledger prefix hash and cleanup result. Never hardcode an
  immutability boolean.
- Tests must statically and dynamically prove one-packet access, no raw/M1/
  parquet/MT5 capability, no future packet, no overwrite, unique opportunity
  IDs, exact four-arm partitions, Stage-0 cadence/direction gates, and false
  outcome/holdout/economic attestations.
- A Stage-0 data/hash/access failure is `INVALID_ENGINEERING`; a cadence or
  direction-coverage failure is `PARK` before outcomes. Only independently
  reviewed Stage-0 PASS may authorize separate DESIGN outcome acquisition.

## 6. Sequential M1 proxy outcome contract — not Stage 0

- Only after frozen DESIGN decision-ledger SHA and accepted Stage-0 PASS may a
  separate source-only process acquire DESIGN M1 outcome shards. It cannot
  contain decision logic or change eligibility/direction.
- Request exactly 12:01 through 18:00 UTC for frozen DESIGN opportunity dates.
  Entry is the 12:01 M1 bid open. Stop is entry ± frozen ATR20. Scan 12:01..17:59;
  an adverse gap exits at the later bar open, otherwise a stop touch exits at
  the exact stop. No TP. If untouched, exit at 18:00 bid open. Missing paths or
  18:00 invalidate, never delete, the day. Friday never carries.
- Gross R is `direction * (exit_bid-entry_bid)/ATR20`. Net R subtracts fixed
  all-in round-trip proxy cost divided by stop pips. Cost tiers remain exactly
  1.50 / 2.25 / 3.00 pips (`UNVERIFIED_PROXY_KILL_ONLY`).
- DESIGN outcomes open first. VALIDATION M1 cannot be requested unless DESIGN
  passes all frozen gates. HOLDOUT is never requested.
- Outcome acquisition/evaluator must be separate from decision-packet creation;
  join identity is the frozen opportunity ID and decision-ledger SHA only.

## 7. Frozen economic and relative gates

All gates apply independently to every opened split. Cost tiers are not trials;
all four arms count in DSR.

| # | Gate | Threshold |
|---|---|---|
| 1 | Challenger completed cadence | `2.0..5.0` per elapsed week |
| 2 | Challenger PF x1 | `>1.30` |
| 3 | Challenger PF x1.5 | `>=1.25` |
| 4 | Challenger PF x2 | `>=1.00` |
| 5 | Challenger mean net R x1 | `>=0.08 R/trade` |
| 6 | Challenger total net R x1 | `>0` |
| 7 | Positive years | DESIGN `>=4/5`; VALIDATION `2/2` |
| 8 | Challenger DSR across four arms | `>=0.95` |
| 9 | Stack PF x1 delta vs better standalone control | `>=+0.15` |
| 10 | Stack mean net R x1 delta vs better standalone control | `>=+0.05 R` |
| 11 | Stack PF x1 delta vs negative disagreement | `>=+0.15` |
| 12 | Stack mean net R x1 delta vs negative disagreement | `>=+0.05 R` |

Report per-trade results and a common UTC daily book with no-trade days as zero.
The research-book contract remains PF `>1.30`, 2–5 trades/week, max DD 6%, PF
x1.5 `>=1.25`, PF x2 `>=1.00`, and Monte Carlo P95 DD `<=6%`. Offline proxy
DD/MC are diagnostic only and cannot promote.

## 8. Verdict routing and required closeout

- Source, physical partition, packet, capability, access-trace, hash, clock,
  chronology, missing-path or reconciliation fault: `INVALID_ENGINEERING`, no
  market verdict; repair without changing the strategy contract.
- Stage-0 cadence/direction failure: `PARK`, no M1 acquisition.
- DESIGN economic/relative/DSR failure: `KILL`; do not acquire validation M1.
- DESIGN passes but VALIDATION fails: `KILL`.
- Both proxy splits pass: `PROBE_SURVIVOR`, authorizing only a separately frozen
  EA source/parity build contract. It is not confirmation or deploy readiness.
- Required artifacts are immutable manifests/receipts, source/tool hashes,
  decision packets, Stage-0 ledger/access trace/reconciliation, red-first tests,
  sequential outcome ledgers/results if authorized, trial log, readout, one
  registry transition and session docs. No commit/push unless Owner explicitly
  requests it in the current message.
