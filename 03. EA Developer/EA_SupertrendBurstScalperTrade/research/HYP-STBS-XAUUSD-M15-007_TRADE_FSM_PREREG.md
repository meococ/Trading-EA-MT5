# HYP-STBS-XAUUSD-M15-007 — Trade-enabled lifecycle engineering preregistration

Preregistered at: `2026-08-09T06:55:00Z`

## Scope

Build a fresh trade-enabled child of engineering-valid HYP006 without changing its market mapping: native H1 Supertrend10x3 state flip, exact following native M15 open, prior completed M15 ATR14, 1.00 ATR outward-normalized stop, 1.50R outward-normalized target, 0.25% requested equity risk, one position, no pyramid/trailing/breakeven, and exit after eight completed M15 bars or the next opposite flip.

Full 2004 prehistory advances recursive Supertrend state, but signal emission/trading is strictly limited to `[2018-01-01 02:00 server, 2023-01-01 02:00 server)`. No prehistory trade is legal. Friday new entries stop at 18:00 UTC; Friday after 20:00 UTC and any Saturday/Sunday exposure require flattening.

This stage authorizes source implementation, focused tests, non-repaint/static review and compile only. It authorizes no MT5 performance run, outcomes, PF, economics, optimization, validation, holdout, paper or live trading.

## Lifecycle contract

- Explicit states: `FLAT`, `ENTRY_PENDING`, `OPEN`, `EXIT_PENDING`, `MANAGE_ONLY`.
- Enumerate all owned positions and active orders by exact symbol/magic; block new entry unless fully flat and reject duplicate/ambiguous exposure.
- `OrderSend` acceptance, including DONE/PARTIAL/PLACED, means request tracking only. Entry/close counters change only after reconciled position/flat state.
- Before `OPEN`, confirm exactly one actual position with expected direction, full expected volume and exact nonzero protective SL/TP within half volume/tick step.
- Persist expected position geometry, entry M15 clock, same-bar entry barrier, broker request/order/deal identity, reverse intent, exit intent, peak equity, UTC day key and day-start equity in two-slot terminal Global Variable snapshots. Each snapshot uses a monotonically increasing generation, payload hash and last-written commit marker followed by `GlobalVariablesFlush`; partial/mixed snapshots fail closed. A slot containing a generation newer than the commit marker is crash residue and also fails closed rather than rolling back silently.
- An accepted entry request remains `ENTRY_PENDING` through transient broker visibility gaps. It is never treated as flat/re-enterable; absence lasting more than 60 server seconds becomes permanent manage-only/runtime-fault for the run.
- Missing/corrupt state with prior owned history or exposure enters manage-only and drains owned orders/positions; without exposure it fails initialization.
- Exit intent persists through partial/placed/rejected close and retries on later ticks. Pending orders are canceled under exit/runtime intent. A missed Friday close remains flatten-required during the weekend.
- Runtime fault never calls `ExpertRemove`; while exposure/order remains, the EA stays in manage-only mode and continues close/cancel reconciliation.
- Opposite flip persists close-then-reverse intent and may reverse only after confirmed flat within the same decision M15 bar. Otherwise it is consumed and rejected once.
- Lifecycle management runs before new H1 flip consumption on each tick. Therefore a max-hold, Friday/DESIGN, protection or runtime exit already due on that tick persists a no-entry barrier through the end of the current M15 bar; the later opposite flip is consumed without reversal even if the close completes synchronously.
- Ticket/order/position enumeration is fail-closed: any read/select failure is a runtime fault, never evidence of a flat account.
- Every exit intent, including Friday/weekend, DESIGN end, protection failure and runtime failure, cancels residual owned orders before closing every residual owned position over tick-by-tick confirmed-flat retries.
- The 1.50% daily-loss and 8.00% peak-equity drawdown gates are entry locks only, not emergency liquidation triggers. Existing exposure remains governed by its broker SL/TP, opposite flip, eight-bar timeout, Friday/weekend and runtime-protection exits.
- This engineering child is tester-only and rejects optimization or non-Tester execution before any trade path. Any eventual paper/live source must be a separately reviewed promotion child.

## Frozen constants

- Hypothesis `HYP-STBS-XAUUSD-M15-007`; variant `STBS_H1_FLIP_M15_BURST_TRADE_FSM_V1`; magic `5604107`.
- Symbol/timeframe `XAUUSD/M15`; `InpAuditOnly=false`; telemetry false; Tester true; optimization false.
- Risk 0.25%; stop ATR 1.00; target R 1.50; max hold 8; daily loss 1.50%; account drawdown 8.00%; Friday 18:00/20:00 UTC; deviation 20 points.

Any logic/parameter change after performance observation requires a fresh hypothesis. This source cannot be promoted until compile/non-repaint/lifecycle tests pass and a later separately authorized costed TRAIN baseline proves PF greater than 1.30 after spread, commission and observed/calibrated dynamic slippage.
