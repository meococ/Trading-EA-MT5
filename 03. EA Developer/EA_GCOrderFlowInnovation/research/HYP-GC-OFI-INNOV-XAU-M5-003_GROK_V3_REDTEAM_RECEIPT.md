# HYP-GC-OFI-INNOV-XAU-M5-003 — Grok v3 pre-source review receipt

- Session: `https://grok.com/c/b01a3ade-c805-45b9-807e-b7553d51dea2`.
- Command: `/deep-research-trading-meta5`.
- Verdict: `PASS_PRE_SOURCE_RESEARCH_V3`.
- No aggregate A/B count, event cadence, XAUUSD target price, return, PnL,
  optimization, validation or holdout was provided to Grok.

Grok accepted the single correction

`R = (mid_before_last_signed_trade - mid_before_first_signed_trade) / GC_tick`

inside one completed five-minute bin. Both midpoints are genuine TBBO BBOs
immediately before their respective trades, are known by bin close, and are
shared by challenger and paired null. All v2 sign, Markov, sigma, threshold and
paired-null rules remain unchanged.

Grok required raw-instrument/session identity, completed bins, positive finite
`bid < ask` first/last pre-trade BBOs, hard roll/session resets, and no inferred
post-trade quote.

Lead-quant correction: Grok suggested dropping an exact duplicate once. That
suggestion is rejected because the frozen source contract says duplicates fail
closed. HYP003 therefore treats any duplicate/correction ambiguity as fatal and
does not de-duplicate source rows.

Primary schema evidence: Databento documents TBBO as each trade plus the BBO
immediately before the trade's effect:
`https://databento.com/docs/schemas-and-data-formats/tbbo`.
