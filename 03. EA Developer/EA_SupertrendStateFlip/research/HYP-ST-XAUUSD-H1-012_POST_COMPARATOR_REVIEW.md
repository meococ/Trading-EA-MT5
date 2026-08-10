# Independent post-comparator review — HYP-ST-XAUUSD-H1-012

Verdict: `PASS_CLOSE`

An independent sub-agent re-hashed the complete ST012 evidence root, checked
the terminal-to-receipt-to-start/report chain and independently reconciled the
oracle and MQL5 ledgers.

## Findings

- The authority row SHA and registry snapshot SHA in the start and receipt are
  exact and unchanged for the sole attempt.
- The terminal binds the receipt, reports `COMPLETE`, preserves the exact
  engineering verdict and forbids same-ID retry.
- Both ledgers contain `29,460` unique increasing rows with zero exact-field or
  server-clock mismatch.
- All four numeric series have maximum absolute error `0.0`.
- Counts independently reconcile to raw `690`, executable `683`, gaps `7`,
  LONG `339` and SHORT `344`.
- The evidence contains indicator, event and timing data only. Every order,
  trade, PnL, profit-factor, return and economics counter is zero.

## Scope

This review ratifies direct MQL5/MT5 correctness only. It authorizes closing
HYP012 as engineering-valid and opening a separately preregistered economic
child. It does not authorize an edge claim, performance selection,
optimization, validation, holdout, paper trading or live deployment.

