# HYP-IDEM-XAUUSD-M5-001 — pre-source review

Verdict: `PASS_PRE_SOURCE`

- Formula is causal: current completed session plus 20 prior completed entropy
  values; current entropy is excluded from its reference median.
- Exact-next checks timestamp only. No outcome, price after decision, cost or
  PnL field is permitted in the ledger.
- Information family is intraday return-sign disorder, not DPMO activity,
  ISDS lag correlation, semivariance/CLV, breakout or indicator voting.
- One immutable source attempt only. Gate failure parks the exact mapping and
  cannot authorize parameter rescue.
