# HYP-LOMX-MULTI-M1-002 — Frozen Exact Data-Contract Successor

Status: **FROZEN BEFORE HYP002 SOURCE OR ECONOMIC OUTPUT**  
Freeze date: 2026-07-30  
Parent: `HYP-LOMX-MULTI-M1-001` (engineering-invalid, no economics).

## 1. Bound parent contract

HYP002 preserves every market and decision rule in the following bound plans:

- HYP001 full plan:
  `03. EA Developer/EA_LondonOpenMultiAssetMomentum/research/HYP-LOMX-MULTI-M1-001_TRAIN_PROBE_PLAN.md`,
  SHA-256 `D9D17ACF5823145FC87F5ED6166039359FF562A144E754D4EE23CA669ED190D9`.
- HYP001 authority amendment:
  `03. EA Developer/EA_LondonOpenMultiAssetMomentum/research/HYP-LOMX-MULTI-M1-001_TRAIN_PROBE_PLAN_V2.md`,
  SHA-256 `B642B26DA2CE72A1EE5576DAE04D1957A35CEEB597D92EE7953DD40CF08F87A2`.
- HYP001 invalid terminal:
  `03. EA Developer/EA_LondonOpenMultiAssetMomentum/research/evidence/HYP-LOMX-MULTI-M1-001/LOMX001-TRAIN-SOURCE-001/source_invalid_terminal.json`,
  SHA-256 `F2BB8FD4915807A8BF08981ABDB7E21B596A5503B76C13581AF6DEF7BF267D9C`.

HYP001 stopped during outcome-blind source summarization because EURUSD raw
positive historical-spread coverage was 0.926275 versus the frozen 0.95 gate.
It produced no parquet, return, trade, PF, expectancy, DSR, chart, validation,
or holdout result.  Therefore HYP002 is a legal engineering/data-contract
successor, not a post-hoc economic rescue.

## 2. Sole successor delta: missing historical spread fields

All signal, polarity, symbol, set, timestamp, split, cost multiplier, arm,
multiplicity, gate, survivor-priority, and terminal rules remain exactly as
specified by the bound HYP001 plans.  The sole delta is:

1. For each symbol, compute raw positive coverage across all five frozen
   entry/exit spread endpoint fields in TRAIN.
2. Raw positive coverage must be >= 80%; otherwise source is invalid again.
3. From that symbol's strictly positive TRAIN spread endpoints, compute the
   deterministic 95th percentile using the `higher` quantile method.
4. Replace only nonpositive/missing endpoint spread values with that same-symbol
   q95 number of points.  Positive observations are never changed.
5. Persist raw coverage, raw missing count, imputed count, q95 rule, and q95
   value for every symbol in the source manifest.
6. After imputation every endpoint must be positive; otherwise fail.

This uses no return/PnL field and is frozen before HYP002 data access.  The
economic cost formula remains:

`cost_x1_price = 1.25 * max(entry_spread_points, exit_spread_points) * point`

with x1/x1.5/x2 stress tiers.  It remains an unverified research proxy without
commission/slippage and cannot support promotion or live claims.

## 3. Split and terminal firewall

- Only broker Bid M1 TRAIN 2016-2020 may be exported/evaluated.
- Validation 2021-2024 and holdout 2025-current remain sealed.
- HYP002 gets one source attempt and, only after manifest/parquet hash review,
  one TRAIN economic attempt.
- No TRAIN survivor -> kill HYP002, no later-year read, MQL5, or Model 0.
- A survivor still requires a fresh validation hypothesis and verified
  commission/slippage cost manifest.
- Root registry `source_path`/`source_hash` remain null; the reviewed research
  wrappers and their immutable HYP001 bases are hash-bound in `validation`.

## 4. Frozen implementation hashes

- HYP001 source base `export_lomx_001_train_source.py`:
  `5C8CB799352AE178322FD389A5AFFA2F332101E09F43043CCBE7C98E15609DC3`
- HYP001 evaluator base `evaluate_lomx_001_train.py`:
  `A5245A1C32C747DB69B782F515A523FF536CAC897359980520E29FDBA8FA9BD2`
- HYP002 source wrapper `export_lomx_002_train_source.py`:
  `A800528A1C1E965E94518ADEDAF173CDEF38AEF5B3F588DF1D9E41AC017712DB`
- HYP002 evaluator wrapper `evaluate_lomx_002_train.py`:
  `E057557B2D39327832E587D6E7D22353E534CD27A81E474AF1972F838E0B6568`
- HYP002 spread-contract test `tests/test_export_lomx_002_train_source.py`:
  `32BEE3F8DF09789BE2852AB7EF4D4F6032F6303342303B6EE0F9B007EEF96E94`
- HYP001 source test:
  `7DC533E01A1EBEB73FEC0130841255BA067914272B5850A282492DA233E8EDAC`
- HYP001 evaluator test:
  `0192622BE0B3E2DA035FD6DBEF2AE9AC84EB62D048F4201161E48916926E20CF`
- Canonical DSR:
  `A0659CDCDB2EAB4F29F69A1FBF4222FE3EC12467FE4CC664E194173126A4CEEA`

Focused family tests before freeze: **14 passed**; both production entrypoints
are disarmed without an explicit production flag and matching latest registry
row SHA.
