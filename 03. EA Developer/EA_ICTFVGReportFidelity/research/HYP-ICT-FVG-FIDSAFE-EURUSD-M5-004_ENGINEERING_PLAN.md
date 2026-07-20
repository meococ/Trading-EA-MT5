# HYP-ICT-FVG-FIDSAFE-EURUSD-M5-004 - final fail-safe binding plan

Status: **FROZEN BEFORE FINAL IDENTITY/COMPILE/RECEIPT; NO PRICE OUTCOME**

## Lineage

- Parent `HYP-ICT-FVG-FIDEXEC-EURUSD-M5-003` is terminal parked at source SHA
  `75EA4B7D8394CCEC6BA5E13643A4340CFAA594BA7934250EC7C5C6D92B3D6541`.
- During the post-build completion audit, one residual recovery assumption was
  rejected before any price outcome: inferring initial risk from TP after fill
  slippage is approximate rather than provenance-exact.
- An unbound draft of that fail-safe edit exists at freeze time. This plan is
  frozen before assigning the new hypothesis identity, final compilation,
  non-repaint audit, source/binary receipt or any economic execution.

## Frozen delta

- Signal, sessions, news calendar, every threshold, entry, original SL, fixed
  TP and normal management behavior remain unchanged from `-003`.
- On restart, an owned position may resume only when persisted state binds the
  exact losslessly stored `POSITION_IDENTIFIER`, original stop and positive
  planned money-risk budget.
- If any of those bindings is missing or inconsistent, latch an emergency
  close and retry until the position is absent. Do not infer initial risk from
  TP, current breakeven stop or current equity.
- No optimization, backtest, holdout access, promotion or live attachment.

## Acceptance

- Package tests include a red/green receipt binding and explicit unknown-risk
  fail-close assertion.
- AlphaFactory compile has zero errors and zero warnings.
- Final source/include/EX5/log receipt is fully hash-bound.
- Exact-source non-repaint audit has zero findings.
- Terminal verdict remains `PARKED_PRE_MODEL0_COST_PROVENANCE_FAILED` with
  `model0_authorized=false` and `promotion_eligible=false`.
