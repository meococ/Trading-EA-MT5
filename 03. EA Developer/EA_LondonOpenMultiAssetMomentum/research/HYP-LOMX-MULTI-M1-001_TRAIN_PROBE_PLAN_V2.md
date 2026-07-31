# HYP-LOMX-MULTI-M1-001 — Frozen TRAIN Probe Plan V2

Status: **FROZEN BEFORE ANY SOURCE OR ECONOMIC OUTPUT**  
Freeze date: 2026-07-30  
Supersedes only the implementation-binding section of V1.  Every market rule,
symbol, split, timestamp, polarity, arm, cost, multiplicity rule, gate,
selection priority, terminal decision, and prohibition in V1 remains unchanged.

## Bound base plan

- Base plan path:
  `03. EA Developer/EA_LondonOpenMultiAssetMomentum/research/HYP-LOMX-MULTI-M1-001_TRAIN_PROBE_PLAN.md`
- Base plan SHA-256:
  `D9D17ACF5823145FC87F5ED6166039359FF562A144E754D4EE23CA669ED190D9`

The full economic contract is the bound V1 content plus the narrow authority
correction below.  V1 must not be edited after this amendment.

## Sole amendment: research-script authority binding

The generic registry validator reserves root `source_path`/`source_hash` for a
canonical `03. EA Developer/<EA>/<EA>.mq5` or a terminal source snapshot.  This
campaign has not earned authority to build an EA.  Therefore the V1 proposal to
place research Python paths in root `source_path` is invalid and is replaced as
follows:

- root `source_path = null` and `source_hash = null` for every HYP-LOMX row;
- source-export authority is bound by
  `validation.reviewed_source_exporter_path` and
  `validation.reviewed_source_exporter_sha256`;
- TRAIN-evaluation authority is bound by
  `validation.reviewed_evaluator_path` and
  `validation.reviewed_evaluator_sha256`;
- the source manifest/parquet are later bound by exact path/SHA fields in
  `validation` before economics can be authorized;
- MQL5, Model 0, validation, holdout, promotion, paper, and live authority stay
  false.

This correction changes no data or economic behavior and was made after static
registry-contract review, before source export and before PnL access.

## Frozen V2 implementation hashes

- `export_lomx_001_train_source.py`:
  `5C8CB799352AE178322FD389A5AFFA2F332101E09F43043CCBE7C98E15609DC3`
- `evaluate_lomx_001_train.py`:
  `A5245A1C32C747DB69B782F515A523FF536CAC897359980520E29FDBA8FA9BD2`
- `tests/test_export_lomx_001_train_source.py`:
  `7DC533E01A1EBEB73FEC0130841255BA067914272B5850A282492DA233E8EDAC`
- `tests/test_evaluate_lomx_001_train.py`:
  `0192622BE0B3E2DA035FD6DBEF2AE9AC84EB62D048F4201161E48916926E20CF`

Focused V2 test result before freeze: **11 passed**.  Both production entrypoints
remain disarmed without explicit flags and a matching latest registry-row SHA.
