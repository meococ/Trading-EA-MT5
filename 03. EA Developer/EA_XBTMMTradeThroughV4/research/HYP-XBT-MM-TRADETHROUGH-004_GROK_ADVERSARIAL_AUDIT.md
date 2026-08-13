# HYP-XBT-MM-TRADETHROUGH-004 — Grok adversarial audit

Date: 2026-08-12  
Mode: Grok `/deep-research-trading-meta5`, challenged and consolidated by Lead Quant  
Outcome use: forbidden; the full DESIGN run had not occurred.

Status: superseded by the later source/expiry failure in
`HYP-XBT-MM-TRADETHROUGH-004_SOURCE_GATE_RESULT.md`. The provisional proceed
verdict below never authorized an economic run.

## Initial Grok verdict

Grok initially returned `REVISE_BEFORE_ECONOMICS`. Its material objections were
partial fills under hidden/iceberg liquidity, a hard decision-to-live adverse
move gate, a wider null, and a doubled forced-flatten cost stress.

## Lead-Quant review

Two objections were rejected as mechanically wrong or unmatched:

1. A print strictly through a displayed resting price exhausts executable
   displayed liquidity at that better price under BitMEX price-time priority.
   The final through-price print size does not cap the quantity executed at the
   better resting price. Grok withdrew its partial-fill proposal.
2. A 2–3 tick wider null changes the opportunity set. The same-latency,
   same-size, same-risk best-touch null is the matched comparator for isolating
   the microprice retreat/skew rule. Grok withdrew the wider-null proposal.

The engine already activates the original order after 400 ms while replaying
every intervening event, so latency adverse selection is already reflected in
fills and PnL. A decision-to-live distribution may be explanatory, but an
arbitrary 0.5-tick pass/fail threshold is not authorized.

## Material issue retained

The original 1 XBT NAV denominator makes the V4 DD threshold weak relative to a
100-contract quote and 400-contract hard cap. Grok first proposed observed
margin plus an unspecified buffer; Lead Quant rejected that as outcome-dependent.

The final accepted contract uses a fixed 400 USD risk-capital denominator, 15%
minimum annualized base return, positive annualized return at 15 bps forced
taker cost, daily DD/recovery on the 400 USD NAV, and a metrics-only V5 intraday
risk replay for any DESIGN survivor. The executable specification is frozen in
`HYP-XBT-MM-TRADETHROUGH-004_ANALYZER_CAPITAL_ADDENDUM.md`.

## Consolidated verdict

`PROCEED_WITH_V4_PLUS_ANALYZER_STRESSES` (provisional, later revoked)

This is authority to continue engineering and, after an explicit economic task
is frozen, evaluate DESIGN. It is not evidence of edge and does not authorize
validation or holdout access.
