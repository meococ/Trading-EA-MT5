# HYP-STBS-XAUUSD-M15-028 — Semantic-Validation Adapter Recovery

## Frozen hypothesis

HYP028 is a fresh comparator-only child of terminal HYP027. It tests whether the unchanged sealed HYP026 run can reach the frozen unified economic gates after correcting exactly one wrapper-schema defect: the verified cost builder emits `run_meta_evidence.semantic_validation`, while HYP027 incorrectly required `run_meta_evidence.semantic`.

No strategy, signal, order, position-sizing, stop/target, holding-period, data, cost, time-window or acceptance threshold changes are allowed. No MT5 run, compile, source-data access, optimization, validation, holdout, paper or live action is authorized.

## Exact parent and run

- Parent: `HYP-STBS-XAUUSD-M15-027`
- Parent terminal raw-row SHA256: `020AA793BB63BA4003F3555F627ADA3C07BB61DCAECAA95BE5E839343885D68E`
- Parent terminal verdict: `KILL_VERIFIED_COST_RUNMETA_SEMANTIC_VALIDATION_ADAPTER_FIELD_MISMATCH_BEFORE_UNIFIED_NO_ECONOMIC_VERDICT`
- Parent comparator authority raw SHA256: `F3DB9F70D36A2016FB91F20046BE0B892BBD5C4B174E08090B5E5A44924B23DF`
- Parent attempt start SHA256: `293C6125CA13EF47F69CB9460B8AEF41144553454A387B734FC51A4BC5EF4324`
- Parent failed terminal SHA256: `A94C59ABE091962944F66B6ED0C0E0EFA0709D4AB6C9ACBA450543CF6F46348F`
- Target evidence run: `HYP-STBS-XAUUSD-M15-026` / `20260810_073648`
- Source SHA256: `F60A9469D1A6FE2D62F5E83DECB953862C68AF9E3D154EA0AE488C072B4A4DA4`
- Report SHA256: `706AE950D20C84DD24364722E613BF5C7C7105C5A2DAB0598E2FE89847E976C5`
- Lifecycle SHA256: `0F3B393D7BFB764DD69BC670ABA68E7B8D1E36CBB743BC6D6A1AD33D1A171FDA`
- RunMeta SHA256: `EFF1941719BBA3478680FFC639E87B60506AE237C416429B9EE27947AE46A25D`
- Data fingerprint: `B326D511C805C7998DF1C2FC540770B6EC3054D0D4BCBB41A5A4E3C2E4239D25`

HYP028 must additionally bind and rehash the HYP027 runtime non-repaint artifact `FFD938A910792867BCDD7D1E642DBCB1A011CB327897E368F234B34CD1B471D0`, verified cost artifact `FDCC562F6C034DEE1F6F9785074F236B241B29ECE0F2C1FCD5148D7709C67A2C`, derived run manifest `7574C68AAB54875AD0BFC7E104AB080CF24793405ADC2B255E5731F4FB902982` and derived cost manifest `A58C135B9D7CAD02798B592E536D102CB287F32FD281F0BF715114A0B1D75A38` as parent evidence. HYP028 may regenerate equivalent child artifacts only from the unchanged sealed inputs and frozen tool hashes.

## Exact adapter rule

The verified cost artifact must contain exactly one RunMeta semantic block named `semantic_validation`; a sibling/legacy `semantic` field is forbidden. Its value must be exactly:

```json
{"runtime_failed":false,"declared_lifecycle_rows":928,"actual_lifecycle_rows":928,"row_count_reconciled":true}
```

Missing, additional, renamed, non-boolean, non-integer or mismatched values fail the sole attempt. No fallback or alias is allowed.

## Frozen economic contract

- Window: inclusive `2018.01.02` through `2022.12.30`
- Minimum PF after x1 research-proxy costs: `1.30`
- Cadence: `2–5` completed positions/week
- Maximum drawdown: `8%`
- Cost stress: x1.5 PF `>=1.25`; x2 PF `>=1.00`
- Minimum completed trades: `500`
- Minimum each direction: `30%`
- Maximum one-year trade concentration: `30%`
- Positive x1 mean net R and every calendar year positive
- Monte Carlo p95 drawdown `<=8%`

Any non-passing engineering prerequisite or blocked economic gate produces an engineering KILL with no economic verdict. Economic FAIL is legal only after every engineering prerequisite passes. Economic PASS remains research-proxy/non-promotable and does not authorize optimization, OOS, holdout or deployment.

## One-shot authority

- Hypothesis: `HYP-STBS-XAUUSD-M15-028`
- Attempt: `STBS028-COMPARATOR-001`
- Limit: `1`; same-ID retry forbidden.
- Claim must be exclusive and fsynced before registry or artifact reads.
- Success/failure terminal must bind the start, exact authority row, registry snapshot, all captured parent/run/tool inputs and every created artifact.

Before authority, tests must cover the exact golden `semantic_validation` block, missing/wrong values, legacy-only `semantic`, dual-field ambiguity, claim-before-read, HYP027 chain mutations, overall/baseline/exit-code reconciliation and prior economic false-pass cases.
