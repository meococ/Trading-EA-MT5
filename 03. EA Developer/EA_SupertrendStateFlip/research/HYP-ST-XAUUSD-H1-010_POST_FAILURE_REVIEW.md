# HYP-ST-XAUUSD-H1-010 - post-failure review

Status: `PASS_KILL_HYP010`

Review whether the sole parsed `balance` funding row is a zero-trade report
validator false positive, confirm ST010 stopped before full row comparison, and
decide whether fresh HYP011 may change only this validator to accept the exact
funding row while rejecting every trade deal. Do not execute comparator, oracle,
audit, MT5, compilation or economics during review.

Independent verdict: exact HYP010 kill is warranted. ST010 consumed once and
created only start/failed-terminal artifacts; no parity report/receipt or
economics exists. Fresh comparator-only HYP011 is legal.

HYP011 must freeze `len(deals) == 1` and exact dataclass equality for the sole
funding row: timestamp `2005-01-01 00:00:00`, deal ID 1, side `balance`, empty
symbol/direction/comment, zero volume/price/commission/swap, `order_id=None`,
and profit/balance 10000. It must bind the exact report and quant-analyzer hashes
and reject every deviation or extra row; generic parser semantics stay frozen.
