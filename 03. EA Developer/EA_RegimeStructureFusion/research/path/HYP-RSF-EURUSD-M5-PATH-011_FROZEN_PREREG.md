# HYP-RSF-EURUSD-M5-PATH-011 — frozen path-management preregistration

Frozen on 2026-08-07 after the Owner requested chart-and-indicator-driven
logic improvement and before PATH-011 source implementation or any PATH-011
Strategy Tester outcome.

## Hypothesis

The Structural-Event-004 entry population loses partly because a fixed
SL / 1.5R TP / 48-bar hold keeps positions alive after the closed-bar thesis
has visibly failed. Keeping the entry clock and initial trade geometry fixed,
one conservative profit-protection rule plus one multi-indicator invalidation
rule can improve net expectancy without selecting hours, directions, engines,
years or chart-derived numeric thresholds.

## Frozen entry contract

- EA: `EA_RegimeStructureFusion`.
- Symbol/timeframe: EURUSD / M5.
- Entry mechanism: the exact Structural-Event-004 closed displacement
  BOS/MSS -> later retest/reclaim sequence.
- Sessions: London plus overlap (`InpManualSessionMask=6`).
- Modes: trend plus breakout (`InpManualModeMask=6`).
- AIRD/VRC context veto, MBB location veto, QQE opposite-acceleration veto,
  structural SL, fixed 1.5R TP and all indicator parameters remain unchanged.
- Live-objective and liquidity-pool target gates remain disabled so PATH-011
  changes path management, not entry membership.
- No direction, route, weekday, hour, year or timezone pruning.
- After an early PATH exit, a non-trading shadow retains the original control
  slot until the control SL, TP, Friday flatten or 48-bar maximum hold would
  have released it. This prevents early exits from creating extra entry bars.

## Frozen challenger path rules

All decisions use completed M5 bars only.

1. **Profit protection:** after a completed bar reaches at least `+1.0R`
   using the original entry and initial SL distance, move SL once to the
   original entry price. No trailing, partial close or threshold sweep.
2. **Hard structural invalidation:** close at the first tick of a new bar when
   the just-completed bar exposes a TB BOS/MSS event opposite the position.
3. **Composite momentum/location invalidation:** after at least three completed
   M5 bars in the position, close when both conditions are true on the same
   completed bar:
   - close is beyond the MBB basis against the position; and
   - QQE primary is on the adverse side of zero and accelerating farther
     against the position.
4. Friday flatten and the 48-bar maximum hold retain priority. Initial SL and
   TP are never widened.

The values `1.0R`, three bars and zero/basis sign boundaries are frozen design
constants. They are not optimized from the eight native screenshots or from
the reported `+0.5R then loss` statistic.

## Development and OOS protocol

- Development: EURUSD M5, 2018-01-01 through 2022-12-31, Model 0, current
  spread, one run only.
- OOS: EURUSD M5, 2023-01-01 through 2024-12-31, Model 0, one run only and
  opened only if all development gates pass.
- No optimizer, sensitivity grid, session mining or same-ID rescue.
- Trial denominator: one development trial plus at most one OOS trial.

## Development gates

- 100% history quality and exact lifecycle reconciliation.
- Same entry mechanism and initial SL/TP contract as Structural-Event-004.
- At least 100 completed trades and at least 2.0 trades per elapsed week.
- Profit factor at least 1.30, positive expectancy and positive mean achieved R.
- Maximum drawdown no more than 8%.
- No year may have PF below 0.80; at least four active years must have positive
  expectancy.
- Every break-even modification must tighten rather than widen risk.
- Every path exit must be attributable to an explicit telemetry reason.

Failure of any economic gate kills PATH-011 and keeps OOS sealed. Passing the
development gate authorizes only the single frozen OOS run, not promotion.

## OOS gates

- Profit factor at least 1.20, positive expectancy and positive mean achieved R.
- Maximum drawdown no more than 8%.
- No lifecycle mismatch, lookahead, repaint or path-action invariant failure.

Promotion remains forbidden until dynamic cost stress, WFA/CPCV/DSR,
sensitivity and Monte Carlo gates pass.

Governance correction before any PATH-011 tester launch: the workspace registry
schema requires a minimum cadence gate of 2.0 trades/week. The original 1.5
clerical value was raised to 2.0; no strategy rule or market threshold changed.

Engineering correction before any completed PATH-011 tester run: an aborted
launch was stopped before its result was inspected when independent review
identified that early exits could free the single-position slot. Shadow control
occupancy and trade-request readback were then added; the aborted artifact has
no economic authority and does not consume the frozen development trial.
