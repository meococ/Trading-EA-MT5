# DATA CUSTODY PLAN — DATASET-FIVEPERCENT-EURUSD-M1-SPLITVAULT-001

Status: **FROZEN before any price-row read by this collection lane** on
2026-07-28. This is a `DATA_ACQUISITION_ONLY` infrastructure contract. It is
not a trading hypothesis, does not consume an economic trial, and grants no
evaluation, MQL5, Model 0, promotion, paper, live, or deployment authority.

## 1. Purpose and epistemic boundary

The canonical local EURUSD M1 parquet contains row groups that cross the
DESIGN, VALIDATION, and HOLDOUT boundaries. Direct predicate filtering is not
a physical seal. One privileged, deterministic, strategy-blind custodian may
decode the complete immutable corpus exactly once and create disjoint physical
vaults. Research and evaluator processes receive only the DESIGN capability.

The accurate attestations are:

- `custodian_full_corpus_decoded=true` after a successful production run;
- `research_validation_opened=false`;
- `research_holdout_opened=false`;
- `evaluator_validation_capability=false`;
- `evaluator_holdout_capability=false`.

Infrastructure decode is not a human/research opening of future outcomes. Any
future value, statistic, manifest, path capability, or content-conditioned
decision exposed outside the custodian invalidates the seal.

## 2. Frozen input identity

- Input path:
  `02. AlphaFactory/data/fivepercent/EURUSD/EURUSD_M1_2015_now.parquet`
- Bytes: `104965845`
- SHA256:
  `2959C555DB6690FD6EFD6CFB3B4C6323698E590C9B2D71E1E55F1902F724235A`
- Root manifest:
  `02. AlphaFactory/data/fivepercent/EURUSD/manifest.json`
- Root manifest SHA256:
  `2CD996FD4416B1E888BF1C9D272BF49056DB3A4CE477CF74FA4E31D474A41B54`
- Footer SHA256:
  `92E8403266EF971ED2F4C05523ECB6C10AE5B5723F0F7504E09694663A779727`
- Producer: `parquet-cpp-arrow version 23.0.0`
- Metadata: `4,293,917` rows, `10` columns, `5` row groups.
- Clock model:
  `02. AlphaFactory/tools/research/fivepercent_server_clock.py`
- Clock model SHA256:
  `A7F179935102B57BA3B629345209F6B0D668D1F7FD828A5ED6003207F41A2F52`

Exact schema and types:

```text
time_server timestamp[ns]
time_utc timestamp[ns]
utc_offset_h int8
open double
high double
low double
close double
tick_volume uint64
spread int32
real_volume uint64
```

The input must be a stable regular file with link count one and no symlink,
junction, mount point, reparse point, alias, hardlink, or identity replacement.
Path, size, full SHA, manifest SHA, footer SHA, schema, row count, row-group
count, and clock SHA are recomputed immediately before decode.

## 3. Frozen calendar routing

Routing uses `time_utc` and only these constants:

- `PRE_DESIGN`: `< 2016-01-04T00:00:00Z`
- `DESIGN`: `>= 2016-01-04T00:00:00Z` and `< 2021-01-01T00:00:00Z`
- `VALIDATION`: `>= 2021-01-01T00:00:00Z` and `< 2023-01-01T00:00:00Z`
- `HOLDOUT`: `>= 2023-01-01T00:00:00Z`

Every input row routes to exactly one split. The routing code may not receive a
hypothesis ID, feature, opportunity date, direction, ATR, arm, entry, stop,
exit, cost, return, PnL, performance gate, report, or evaluator module.

## 4. Capability and output contract

Production output is create-new on D: under:

```text
02. AlphaFactory/data/fivepercent/EURUSD/splitvault_001/
  public/DESIGN/YYYY-MM-DD/m1.parquet
  sealed/PRE_DESIGN/...
  sealed/VALIDATION/...
  sealed/HOLDOUT/...
  private/custody_manifest.jsonl
  private/custody_receipt.json
  public/design_manifest.jsonl
  public/design_receipt.json
  quarantine/<attempt_id>/...
```

Each daily file is a regular immutable parquet with one row group. No split may
share a file, inode/file identity, cache, temporary file, or parent capability
with another split. The DESIGN consumer receives only the exact public DESIGN
root, public DESIGN manifest, and public DESIGN receipt. It must not enumerate
the source parent, original parquet, private receipt, sealed roots, quarantine,
or siblings. The supervising process must enforce a path allowlist and audit
all opens, stats, directory enumeration, subprocess, network, and reparse/
hardlink attempts.

The public receipt may expose only frozen source/plan/tool identities,
boundaries, an exactly-once PASS, and the DESIGN manifest/set digest. It may not
expose future paths, future file names, future counts, future timestamp extrema,
price extrema, distributions, missing-date lists, returns, or any future
content-derived statistic. Future manifests and receipts remain private; only
an opaque custody digest may be public.

## 5. Mechanical validation and reconciliation

The custodian may perform only fail-closed mechanical checks:

- exact schema and runtime types;
- finite positive OHLC with `low <= open/close <= high`;
- strictly increasing, unique `time_utc` and exact M1 grid;
- `time_server <-> time_utc <-> utc_offset_h` round-trip using the bound clock;
- every input row assigned exactly once to one split;
- no duplicate, drop, fill, dedupe, interpolation, resample, or mutation;
- input row count equals the private union of all physical output rows;
- reopened output files reproduce their hashes and split membership;
- no temporary or partial artifact published before the final receipt.

Errors visible outside the custodian use a constant class and do not echo a
future value, date, path, count, or statistic. Any failure quarantines the
entire attempt and publishes no successful public receipt.

## 6. Implementation, review, and run authority

Implementation is red-first. Tests must prove at minimum:

- cross-boundary sentinel routing and exact-once reconciliation;
- create-new and no-overwrite behavior;
- regular-file, hardlink, junction, reparse, path-escape, and identity-swap
  rejection;
- strategy/evaluator import and forbidden-field rejection;
- no network, terminal, mutation, subprocess, or content-derived public log;
- public consumer denial of source, parent, private, validation, holdout, and
  quarantine capabilities;
- crash/partial publication quarantine;
- stable canonical manifest and receipt bytes.

No production decode is authorized until an independently reviewed create-new
run packet binds this plan SHA, exact source/manifest/footer/clock hashes, final
custodian and supervisor hashes, complete test hashes, output root, and flags
`performance_metrics_authorized=false`, `trading_mutation=false`,
`network_allowed=false`, and `model0_authorized=false`.

## 7. Failure routing

- Identity, schema, tool, plan, clock, path, routing, capability, or
  reconciliation drift: `INVALID_ENGINEERING`; quarantine; no source receipt.
- Future capability/value/statistic exposure: `INVALID_SEAL`; the consumer
  hypothesis may not use this attempt.
- Successful custody: `COLLECTION_ENGINEERING_VALID_DESIGN_CAPABILITY_ONLY`.
  This does not authorize economic evaluation.

