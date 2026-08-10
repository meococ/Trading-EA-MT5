# HYP-ST-XAUUSD-H1-010 - zero-trade report-validator failure

Status: `KILL_EXACT_BALANCE_ROW_FALSE_POSITIVE`

Timestamp: `2026-08-09T00:43:23Z`

## Exact failure

The sole `ST010-COMPARATOR-001` attempt claimed durably and passed the frozen
authority, post-claim bindings, oracle-chain, non-repaint and sealed HYP009
collection checks. It then stopped inside the inherited HYP009
`validate_alpha_run()` before reading the 29,460-row oracle/audit payloads for
comparison.

The inherited validator used:

`if parse_deals_from_html_report(report): fail`

The HYP008 zero-trade MT5 report contains one mandatory account-funding row in
the Deals table:

`Deal(time=2005-01-01 00:00:00, deal_id=1, symbol='', side='balance',`
`direction='', volume=0.0, price=0.0, order_id=None, commission=0.0,`
`swap=0.0, profit=10000.0, balance=10000.0, comment='')`

There are no BUY/SELL trade deals. Treating any parsed Deals-table row as a
trade is therefore a validator false positive, not evidence that the EA traded.
The exact exception was `ValueError: zero-trade HYP008 report contains deals`.

## Evidence boundary

- Attempt start SHA256:
  `42A53DCF431951558EB25706F8E6621A9EADF1CBDE3B55BD4FE7AB9628976F6D`.
- Failed terminal SHA256:
  `3E890897AEEBF902449B4A3726516254A8AB10BAACECA708F83F35C180C17233`.
- No parity report or receipt was created.
- Oracle/audit row comparison, deterministic replay, outcomes, returns, PF and
  economics did not run.
- No collection, MT5 or compilation repeated.

## Verdict and next legal lane

Same-ID retry is forbidden. Terminally close HYP010 with comparator consumed
once. A fresh comparator-only HYP011 may reuse the same sealed inputs and frozen
engine, changing only zero-trade report validation to require exactly the one
frozen balance-funding row and reject every other deal or order-like row. It
must retain claim-before-artifact-read ordering and all zero-economic gates.
