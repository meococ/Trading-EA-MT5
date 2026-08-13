# HYP-DOL-UI-SEASONAL-RESIDUAL-EURUSD-H1-001 — terminal TRAIN verdict

## Verdict

`KILL_FROZEN_MAPPING`.

The official DOL weekly seasonal-residual object was engineered and executed
correctly, but the frozen direct continuation mapping does not have sufficient
after-cost edge on FivePercent EURUSD H1. Validation (2023-2024), holdout
(2025-current), optimization, paper and live remain sealed.

## Engineering evidence

- Source attempt `DOLUI001-SOURCE-002`: 441 official releases, 439 usable, two
  frozen unavailable/FLAT rows, source cost USD 0.
- EA compile: zero errors, zero warnings; static non-repaint audit PASS.
- TRAIN primary and reverse: 260/260 events accounted, 258 completed trades,
  two source-flat events, zero missed/bar-mismatch/weekend/overlap/reject rows,
  maximum concurrency one, runtime failure false.
- Strategy Tester report History Quality: 100% for both runs.
- Primary run: `20260813_094716`; reverse run: `20260813_094909`.
- Primary FILE_COMMON artifacts were recovered without rerunning the strategy.
  Reverse artifacts were collected normally; its later AlphaFactory failure was
  a warm-cache D0 journal-proof gap, not a strategy/runtime failure. See the
  hash-bound run-recovery receipt.

## Frozen economic readout

| Metric | Primary | Reverse |
|---|---:|---:|
| Completed trades | 258 | 258 |
| Base net | USD 220.32 | USD -3,086.01 |
| Base PF | 1.0118 | 0.8447 |
| Base expectancy | USD 0.85 | USD -11.96 |
| x1.5 cost PF | 0.9743 | 0.8139 |
| x2 cost PF | 0.9381 | 0.7843 |
| x2 expectancy | USD -4.63 | USD -17.27 |
| Native maximum drawdown | 3.61% | 5.72% |

The primary passed event accounting, cadence, three-of-five positive years,
drawdown, concentration, and reverse-inferiority gates. It failed the four
decisive expectancy gates: base PF, x1.5 PF, x2 PF and x2 expectancy.

## Interpretation and boundary

The worse reverse comparator suggests the source sign contains some directional
information, but the magnitude is too weak to survive the frozen cost contract.
That is not an edge claim and does not authorize mining this readout for a
residual threshold, Wednesday filter, 2022 exclusion, different hold, session,
direction, stop/target or sizing. Any next candidate must use a genuinely new
economic mechanism and a fresh preregistration.
