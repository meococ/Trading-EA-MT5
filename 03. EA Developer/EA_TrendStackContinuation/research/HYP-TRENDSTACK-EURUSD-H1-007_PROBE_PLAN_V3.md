# HYP-TRENDSTACK-EURUSD-H1-007 - PROBE PLAN V3

Status: `FROZEN_IDEA_AMENDMENT_PRE_SOURCE_PRE_ECONOMICS`

This create-new amendment supersedes V2 SHA256
`B20671C2D57014CC605CF956A368352519D179381310919306B489AC5182571E`.
V1 and V2 remain immutable evidence. Every V1/V2 clause remains binding except
where V3 explicitly replaces or narrows it. No HYP007 public shard, OHLC,
return, PnL, performance metric, VALIDATION, or HOLDOUT payload was opened
before this V3 freeze.

## 1. Independent lineage correction

The active source contract is the ordered pair:

1. `HYP-TRENDSTACK-EURUSD-H1-007_SOURCE_PROJECTION_CONTRACT_V2.json` SHA256
   `8E1B3A909F9B87C045EC2A5B25D6E5F22F853F021B04148C72D6F6AB7977D6A4`;
2. `HYP-TRENDSTACK-EURUSD-H1-007_SOURCE_PROJECTION_CONTRACT_V3.json`, applied as
   the exact JSON-pointer overlay it defines.

V3 grants the independent validator one metadata-only read each of the public
receipt, public manifest, and selection manifest. It must independently derive
all 1,297 selected date-to-input path/bytes/rows/SHA mappings and compare them
to the staged request and lineage trace. It still has zero authority to open an
upstream public Parquet shard, raw source, sealed data, features, or economics.

## 2. Hash membership and evidence lifecycle

The data-tree hash contains exactly the 1,297 output Parquet shards and no
metadata file. Manifest, trace, reconciliation, projector receipt, validation
receipt, attempt-started, and attempt-terminal hashes bind one another only in
the acyclic order frozen by V3. No artifact may include its own hash.

The supervisor must resolve the workspace root from its reviewed location and
the task packet. A literal machine-specific root is not authority. All packet
paths remain normalized workspace-relative POSIX paths and must resolve inside
that reviewed root.

The validation receipt is written outside the stage in the attempt evidence
root after independent PASS. Atomic no-replace publish is allowed only after
the supervisor rehashes that receipt and verifies every bound upstream and
stage hash. Post-publish readback may `lstat` exactly 1,297 final output shards
and rehash the six final metadata files, but may not decode or reopen final
Parquet payloads.

V1/V2 economic object, metric truth tables, twelve gates, high adverse prior,
and no-rescue rules remain unchanged. V3 grants source-tool implementation only
after independent review and a legal registry `idea -> probe`; it grants no
source run or economic access.

