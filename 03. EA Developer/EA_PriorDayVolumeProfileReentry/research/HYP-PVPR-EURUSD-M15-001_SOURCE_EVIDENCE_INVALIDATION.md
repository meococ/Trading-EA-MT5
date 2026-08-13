# HYP-PVPR-EURUSD-M15-001 — Source evidence invalidation

Verdict: `INVALID_SOURCE_PASS_FLOAT_BOUNDARY_PARITY_NO_ECONOMIC_VERDICT`

- The sole source attempt completed mechanically with 946 serialized events and
  no outcome/economic read, but ledger row 169 records LONG with
  `source_open == VAL == 1.0612`.
- The frozen rule required strict `source_open < VAL`. The analyzer compared raw
  binary floats and rounded only when writing evidence, so `bin * 0.0001` could
  sit microscopically above an equal five-digit broker price.
- This is a cross-platform formula/parity defect. The HYP001 report cannot
  authorize MQL5 even though removing the one ambiguous row would not change its
  coarse cadence gates.
- Preserve the exact HYP001 attempt unchanged. Same-ID retry is forbidden.
- A fresh HYP002 may change only price-boundary representation to integer
  five-digit broker points, add equality boundary tests and rerun the unchanged
  source gates. No signal threshold, profile, session, direction or outcome
  decision is authorized.

Independent post-source review verdict: `FAIL_MQL_BUILD_AUTHORIZATION` until the
integer boundary contract is frozen and rerun.
