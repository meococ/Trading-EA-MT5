# HYP-CRSI-XAUUSD-H1-001 — Independent Post-source Review

Verdict: `PASS_PARK`

The exact artifact chain is internally consistent. The receipt rehashes every bound file, the terminal binds the receipt and verdict, and the 1,092-row ledger independently reconciles with the report.

## Independent reconciliation

- Unique strictly ordered executable rows: `1,092`
- LONG / SHORT: `526 / 566`
- Decision-year counts 2018–2022: `229 / 206 / 209 / 222 / 226`
- Ledger allowlist, finite values, exact one-hour decision clock and frozen threshold predicates: zero violations
- Receipt binding mismatches: `0`
- Terminal-to-receipt mismatch: `0`

The only failed gate is exact-next coverage: `1,092 / 1,137 = 96.042216%`, below `97%`. Passing required at least `1,103` executable events, so the exact mapping is short by `11`; 45 raw events were consumed by gaps.

The exact failure radius is limited to FivePercent XAUUSD native H1, CRSI `(3,2,100)`, frozen extreme-reentry predicates, full-inception state, 2018–2022 scoring and immediate-next-H1 execution. It is not an economic no-edge result.

No gate reduction, late-next-bar substitution, threshold/session/cooldown rescue, same-ID retry or MQL5 build is authorized.

Reviewed closeout:

- Source result SHA256: `CECC21CEE44DEFC3BDB087CF3DEC7D53B7F29F24F244AC7267926738ED087CE6`
- Failure packet SHA256: `38A763BD762DA68EA5A172FE7A2E3069B067BB209C045DD12935F2F0E697AC1A`
