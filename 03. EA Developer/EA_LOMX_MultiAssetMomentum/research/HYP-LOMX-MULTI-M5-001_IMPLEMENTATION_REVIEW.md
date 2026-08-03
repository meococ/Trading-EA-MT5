# HYP-LOMX-MULTI-M5-001 Implementation Review

Status: `REJECT_AS_ECONOMIC_AUTHORITY__OWNER_BUILD_FIRST_ENGINEERING_REWORK_ALLOWED`

## Outcome first

The supplied implementation plan is useful research input, but it is not a
valid AlphaFactory run contract. The existing untracked draft compiled with
zero reported errors/warnings but implemented only the Asian-range sweep arm,
used broker-server time while claiming UTC, had unsafe cross-symbol sizing and
did not emit the lifecycle-v3 evidence declared by its capability contract.
No MT5 backtest or economic outcome exists for this draft.

The exact ID `HYP-LOMX-MULTI-M5-001` will not be retroactively registered or
used for an economic run. Its preserved receipt is
`research/evidence/HYP-LOMX-MULTI-M5-001_UNREGISTERED_DRAFT/UNREGISTERED_DRAFT_RECEIPT.json`.

## Material plan corrections

1. Treat the two engines as separately attributable arms before any combined
   run. A combined PF cannot rescue a losing sleeve or hide a cadence failure.
2. Rename the plan's generic "Volman" arm to
   `BAR_RANGE_COMPRESSION_BREAKOUT`; it does not implement the frozen T2
   three-touch/ordered-pressure Volman grammar.
3. Use the canonical FivePercent server-to-UTC era-hybrid clock. Session and
   Asian-range identity must not use raw `TimeCurrent()` hour fields.
4. Run an outcome-blind density/geometry probe before Model 0. No PnL, future
   return, MFE/MAE, PF, validation or holdout is readable at this stage.
5. Use one task packet, cost contract and run per symbol. XAUUSD and EURUSD
   results are never pooled to satisfy a symbol gate.
6. Use synchronous, receipt-bound execution for the research scaffold. The
   shared async mutation kernel is experimental and disabled; claiming async
   behavior without callback/restart/partial-fill fixtures would reduce
   fidelity.
7. Promotion still requires verified same-symbol spread, commission and
   independent fill/slippage evidence plus report/lifecycle reconciliation.

## Prior-family separation

- The old LOMX M1 family tested a London 08:00-to-08:30 opening-sign matrix; it
  is not the same decision surface, but its zero-survivor result is an adverse
  prior.
- The sweep arm is adjacent to terminal PO3/Unicorn controls and the parked
  ASRS EURUSD M5 outcome-blind screen. Novelty is limited to a fixed same-day
  Asian boundary plus direct ATR-depth reclaim and z-scored tick-volume proxy.
- The compression arm is adjacent to the parked ECRS frequency frontier. Its
  proposed delta is a much simpler bar-range contraction and 15-bar box break,
  without Kaufman-ER or EMA bias. It is not allowed to inherit the T2 Volman
  label or T2 authority.

## Lawful successor route

`HYP-LOMX-DESIGN-M5-002` is an outcome-blind four-cell design probe over
XAUUSD/EURUSD x sweep/compression. Only a passing cell may open a fresh,
symbol-specific economic hypothesis and frozen Model-0 control. The package may
be hardened and compiled under the Owner's explicit build-first request, with
trading default-off, but compile success is engineering evidence only.

## Successor closeout

The build-first implementation is now engineering-valid. The corrected source
contains both separable engines, exact closed-bar M5 handling, UTC/DST session
conversion, symbol+magic scoping, daily/account drawdown locks, downward-only
broker stop-out-aware sizing, and lifecycle-v3 reconciliation. Shipped defaults
remain fail-closed.

Outcome-blind Stage 0 passed each atomic cell but rejected the combined object:
EURUSD sweep 4.1531 candidates/week and EURUSD breakout 4.5111/week already
exceed the 5/week ceiling when combined, and six of twelve sampled same-bar
collisions were directionally opposed.

The EURUSD sweep successor HYP-003 completed a full run under mismatched
preregistered account/data identities. Its PF0.5278 observation is retained as
a strong adverse prior only. The distinct preordered compression-breakout
`HYP-CBRK-EURUSD-M5-001` then ran once under exact tester identity and was
economically killed: N402, PF0.7467, net -$7,061.46, expectancy
-$17.57/trade, cadence1.1027/week and DD7.77%. It failed the frozen PF1.30 and
2/week base gates before cost stress. XAUUSD remains unproven because its
full-population data/cost identity was invalid; no XAU economic claim is made.

The complete terminal packet is
`research/HYP-CBRK-EURUSD-M5-001_FAILURE_PACKET.json`. No optimization,
validation, holdout, promotion, paper or live route is open for this plan.
