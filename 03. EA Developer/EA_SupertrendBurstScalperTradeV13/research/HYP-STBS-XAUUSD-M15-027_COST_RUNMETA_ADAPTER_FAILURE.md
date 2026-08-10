# HYP027 Cost RunMeta Adapter Failure

- Verdict: `KILL_COMPARATOR_COST_RUNMETA_SEMANTIC_FIELD_ADAPTER_MISMATCH_NO_ECONOMIC_VERDICT`
- Attempt: `STBS027-COMPARATOR-001`
- Status: `FAILED`; same-ID retry is forbidden.

## Exact failure radius

The sole comparator-only attempt durably claimed its evidence root, captured and hash-verified the terminal HYP026 registry/run/cost lineage, produced a PASS runtime non-repaint audit, and produced a complete verified research-proxy cost artifact. It then failed in the HYP027 wrapper before unified validation because the wrapper looked for `run_meta_evidence.semantic`, while the frozen cost builder emits the validated block as `run_meta_evidence.semantic_validation`.

The emitted `semantic_validation` block is internally positive and reconciled:

- `runtime_failed=false`
- `declared_lifecycle_rows=928`
- `actual_lifecycle_rows=928`
- `row_count_reconciled=true`

This is an exact comparator adapter-field defect. It is not a runtime failure, lifecycle mismatch, strategy change or economic result. Unified validation was not invoked, no admissible PF/expectancy verdict was created, and no optimization, validation, holdout, paper or live stage opened.

## Immutable evidence

- Authorized HYP027 raw row SHA256: `F3DB9F70D36A2016FB91F20046BE0B892BBD5C4B174E08090B5E5A44924B23DF`
- Attempt start SHA256: `293C6125CA13EF47F69CB9460B8AEF41144553454A387B734FC51A4BC5EF4324`
- Failed terminal SHA256: `A94C59ABE091962944F66B6ED0C0E0EFA0709D4AB6C9ACBA450543CF6F46348F`
- Runtime non-repaint audit SHA256: `FFD938A910792867BCDD7D1E642DBCB1A011CB327897E368F234B34CD1B471D0`
- Verified cost artifact SHA256: `FDCC562F6C034DEE1F6F9785074F236B241B29ECE0F2C1FCD5148D7709C67A2C`
- Derived cost manifest SHA256: `A58C135B9D7CAD02798B592E536D102CB287F32FD281F0BF715114A0B1D75A38`
- Derived sealed run manifest SHA256: `7574C68AAB54875AD0BFC7E104AB080CF24793405ADC2B255E5731F4FB902982`
- Registry snapshot at claim SHA256: `B19A099CCFE8D2FBD85D6A0E7F01C67F67FADD31231BFC1E3A84CD806644EA70`

The failed terminal inventories every created attempt artifact. It explicitly records `mt5_launched=false`, `compile_executed=false`, `source_market_data_opened=false`, `new_orders_or_fills_created=0`, `economic_verdict_created=false`, and `same_id_retry_authorized=false`.

## Safest next lane

A fresh HYP028 comparator-only child may reuse the unchanged sealed HYP026 run and frozen toolchain, change only the RunMeta evidence accessor from `semantic` to the documented emitted `semantic_validation`, and then continue through the same fail-closed unified gate reconciliation. It must use a fresh preregistration, comparator source, tests, review, authority row and one-shot attempt ID. No MT5 rerun, compile, source scan or strategy change is justified.
