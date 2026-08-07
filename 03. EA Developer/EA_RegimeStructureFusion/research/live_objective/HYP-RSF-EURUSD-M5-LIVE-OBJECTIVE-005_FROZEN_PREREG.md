# HYP-RSF-EURUSD-M5-LIVE-OBJECTIVE-005 — Frozen preregistration

Frozen before implementation and before the single authorized economic trial.

## Parent evidence

- Terminal parent: `HYP-RSF-EURUSD-M5-STRUCTURAL-EVENT-004`.
- Parent run: `02. AlphaFactory/runs/EA_RegimeStructureFusion/20260807_080936`.
- Parent result: 520 trades, PF 0.8365347125, mean achieved R -0.110009, net -5253.23; terminal economic kill.
- Native visual diagnostic: `HYP-RSF-EURUSD-M5-STRUCTURAL-EVENT-VISUAL-005`, eight symmetrically selected best/worst cases, 8/8 native 1906x1025 PNGs imported and hash-bound by AlphaFactory.
- Pre-change EA source SHA-256: `904019E9651285AF0C1AC96C0D97A6A151CBCE56BDD2B6AF4BA66E1E3711FB07`.
- Visual prereg SHA-256: `AED8095FF5EF2A760FAE58D36FCAFC48B8E813EB0162C6AFDE15584F89E8A1B2`.

## Failure mechanism

The parent intended to reject a structural retest when the opposing liquidity objective did not leave enough runway. Instead, `BuildStructuralGeometry()` replaced a missing live objective with the fixed 1.5R target before evaluating runway. This made the runway gate non-discriminating: the parent run reported zero runway rejects from 5,292 structural arms. Native charts show the corresponding location failure: several losing retests were accepted below nearby supply, into demand, or after the impulse had already collapsed into compression.

## Single causal change

Add an opt-in `InpStructuralRequireLiveObjective` gate, default `false` for backward compatibility. When enabled:

1. A structural event may arm only when the relevant opposing confirmed swing is live and lies beyond the broken structure level.
2. Missing/stale/wrong-side objective fails closed; it is never replaced with a synthetic "open air" objective.
3. At entry, objective runway must remain at least the already-frozen `InpStructuralMinObjectiveR = 1.25` after the actual executable entry and protected-stop risk are known.
4. Target remains the nearer of the fixed 1.5R target and the live structural objective.
5. AIRD/VRC, MBB, QQE, session, risk and execution rules remain unchanged.

This is a mechanism repair, not a search over objective thresholds, sessions, engines or indicator parameters.

## Measurement change (no entry authority)

When telemetry is enabled, emit one `EntryContext` row for every successful entry. It must include the arm time, structural event type, broken level, protected level, live objective, objective-room R, TB swing/cell/void state, MBB state, QQE state, AIRD posterior and VRC regime. This sidecar observes the frozen decision; it cannot create or veto a trade.

## Fixed experiment contract

- EA: `EA_RegimeStructureFusion`.
- Symbol/timeframe: EURUSD M5 only.
- Development window: 2018-01-01 through 2022-12-31.
- MT5 model: 0 (`Every tick based on real ticks` lane used by AlphaFactory contract).
- Execution mode: no-delay development control; current spread request.
- Deposit/leverage: 100,000 / 1:100.
- Route mask: breakout + trend; range disabled.
- Session mask: Europe + New York, unchanged from parent.
- Exactly one economic development trial is authorized.
- Optimization, session rescue, engine rescue, year rescue and threshold sweeps are forbidden under this hypothesis ID.

## Decision gates

- Engineering: 0 compile errors; targeted tests pass; non-repaint audit passes; `EntryContext` sidecar is present and row-count equals successful entries.
- Immediate economic kill: PF <= 1.00 or mean achieved R <= 0, or fewer than 100 trades.
- Eligible for robustness work only if PF > 1.00, mean achieved R > 0, at least 100 trades, and max drawdown <= 8%.
- Promotion is not authorized by this trial. Cost stress, WFA/CPCV-style OOS evidence, DSR with total trial count, Monte Carlo and per-symbol/timezone campaigns remain mandatory later.

## Interpretation boundary

- The eight charts are mechanism evidence, not a training set for visual curve fitting.
- TradingView account-level Pine overlay comparison is not claimed unless a logged-in TradingView session is available and the actual Pine indicators are visible on the requested historical bars.
- If the single trial fails, this hypothesis is terminal. Reusing the same ID for parameter rescue is forbidden.
