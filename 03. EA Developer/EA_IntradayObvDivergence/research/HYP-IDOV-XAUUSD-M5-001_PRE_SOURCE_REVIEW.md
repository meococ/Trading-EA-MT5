# HYP-IDOV-XAUUSD-M5-001 — pre-source review

Verdict: `PASS_PRE_SOURCE`

- Formula is causal and uses only completed bars inside the current session.
- Exact-next validation reads timestamp only; ledger has no post-decision price,
  return, cost, trade or PnL field.
- The atomic information set is session price direction versus accumulated
  signed tick volume, materially distinct from total participation, return-sign
  entropy, autocorrelation and quote-update polarity.
- One source attempt only. Gate failure parks the mapping without parameter or
  direction rescue.
