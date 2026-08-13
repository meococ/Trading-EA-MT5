# HYP-DPMO-XAUUSD-M5-001 — source feasibility result

Verdict: `PASS_SOURCE_FEASIBILITY_UNCHANGED_MQL5_BASELINE_AUTHORIZED`

The frozen source scan passed every preregistered outcome-blind gate on the
existing FivePercent XAUUSD M5 data. No paid data, return, PnL, trade cost or
post-16:00 price was opened.

## Observed source facts

- DESIGN rows: `351303`.
- Exact complete UTC sessions: `1276 / 1305` (`97.7778%`).
- Raw/executable signals: `599 / 599`; exact-next coverage `100%`.
- Calendar cadence: `2.296276` signals/week.
- LONG/SHORT: `301 / 298` (`50.25% / 49.75%`).
- Decision-year counts 2018–2022: `96 / 118 / 129 / 123 / 133`.
- Decision-year cadence: `1.8411 / 2.2630 / 2.4672 / 2.3589 / 2.5507` per week.
- Maximum year concentration: `22.2037%`.
- Deterministic replay and all frozen source gates: PASS.

## Immutable evidence

- attempt start: `E24301028FD6C85228987168EECE3D746AF9A356FE2B7550632B7B3BC61A28D3`
- source report: `24863FC3447C215B537C225EFAA1278BBE9035855F8BDF7CCC6EEF904AEF5934`
- source ledger: `920428A3CF0BAA465C1CCC53799A75ECC6F7D8437B69D16980997D6539FB4AA0`
- attempt receipt: `17529FBE5383AAD1D377579BF88B45AD4269375D1D4DD99DD7C4E767C8F050BC`
- terminal: `BC1AB1477215ED7AF517093AFC46C92436A09F0FE8C847CF01D5A8C7EEFB24DA`

This result authorizes only an unchanged MQL5 implementation, signal-parity
checks, compile/non-repaint verification, and one separately frozen untuned
Model-0 baseline. It is not an economic, validation, promotion or live claim.

