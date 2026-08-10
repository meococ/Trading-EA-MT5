# HYP027 Independent Post-Failure Review

- Verdict: `PASS_KILL`
- Terminal verdict: `KILL_VERIFIED_COST_RUNMETA_SEMANTIC_VALIDATION_ADAPTER_FIELD_MISMATCH_BEFORE_UNIFIED_NO_ECONOMIC_VERDICT`
- Same-ID retry: forbidden.

## Independent reconciliation

The frozen cost builder emits the RunMeta verification block at `run_meta_evidence.semantic_validation`. The captured HYP027 comparator instead reads `run_meta_evidence.semantic`. The exact emitted block is `{runtime_failed:false, declared_lifecycle_rows:928, actual_lifecycle_rows:928, row_count_reconciled:true}`. The failure is therefore limited to the comparator adapter field name.

- Attempt start SHA256: `293C6125CA13EF47F69CB9460B8AEF41144553454A387B734FC51A4BC5EF4324`
- Failed terminal SHA256: `A94C59ABE091962944F66B6ED0C0E0EFA0709D4AB6C9ACBA450543CF6F46348F`
- Terminal inventory: `45/45` files rehashed, zero mismatches.
- Runtime non-repaint PASS SHA256: `FFD938A910792867BCDD7D1E642DBCB1A011CB327897E368F234B34CD1B471D0`
- Verified cost artifact SHA256: `FDCC562F6C034DEE1F6F9785074F236B241B29ECE0F2C1FCD5148D7709C67A2C`
- Derived run manifest SHA256: `7574C68AAB54875AD0BFC7E104AB080CF24793405ADC2B255E5731F4FB902982`
- Derived cost manifest SHA256: `A58C135B9D7CAD02798B592E536D102CB287F32FD281F0BF715114A0B1D75A38`

No `validation_a`, `validation_b`, comparison result or comparison receipt exists. Unified validation and PF classification did not run. The attempt launched no MT5, performed no compile or source-data scan, and created no new order/fill. It cannot support an economic PASS or FAIL.

## Fresh-lane boundary

A fresh HYP028 comparator-only child is lawful. It may change only the accessor to the exact `semantic_validation` dict and must reject a missing field, legacy `semantic` only, dual-field ambiguity or any value mismatch. It must bind this terminal HYP027 chain, retain the HYP027 false-pass protections and all frozen HYP026 run/cost/tool hashes, and keep MT5, compile, optimization, validation, holdout, promotion, paper and live permissions false.
