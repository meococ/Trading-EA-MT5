# Supertrend Burst Scalper — Preimplementation execution review

Status: `FAIL_FOR_TRADE_ENABLEMENT`. This does not affect the hard audit-only HYP001/HYP002 correctness lane.

## Fatal blockers before a child may trade

1. Trade-enabled mode is not DESIGN-bounded. The current code advances the recursive H1 state over the required 2005 prehistory, but when `InpAuditOnly=false` it also calls `ConsumeFlipEvent` for bars outside `[2018-01-01, 2023-01-01)`. That would turn prehistory into 2005-2017 trades and contaminate TRAIN cadence, PF and costs. A child must always advance state over the full frozen prehistory while emitting/trading only inside its separately frozen scoring window.
2. Risk anchors are not restart-safe. `UpdateRiskAnchors` initializes peak/day equity from current equity and `OnInit` calls it directly, so restart can re-enable entries after the frozen 1.5% daily or 8% account lock.
3. Request acceptance is treated as execution. `AcceptedRetcode` accepts `PLACED` and `DONE_PARTIAL`; entry/close counters and holding clock update immediately, while `OnTradeTransaction` only logs. Official MQL5 documentation states that `OrderSend()==true` is not proof of execution and transaction events may arrive afterward.
4. Exposure reconciliation is incomplete. Only one arbitrary owned position is returned; pending orders, duplicate owned positions, actual direction/volume/SL/TP and delayed fills are not reconciled. Failed entry-clock recovery silently disables the time exit.
5. Exit intent is not durable. Time exit retries only on the next M15 bar, opposite-flip events are consumed after an accepted partial/placed close, and a failed Friday close has no explicit Saturday/Sunday recovery state.
6. Runtime failure calls `ExpertRemove()` even if exposure or pending orders exist, removing Friday/time management and leaving broker protection as the only guard.
7. A filled position is never verified to exist with the expected direction, magic, volume and nonzero protective SL/TP.

## Required child architecture

Use a fresh hypothesis/source guard and an explicit `FLAT -> ENTRY_PENDING -> OPEN -> EXIT_PENDING -> MANAGE_ONLY` state machine keyed by request, order, deal and position identifiers. Separate full-prehistory indicator-state advancement from frozen-window event emission. Block new requests while any owned order/position exists; persist or reconstruct peak/day anchors and entry bar fail-closed; confirm position protection before `OPEN`; persist exit intent and retry on later ticks without resurrecting a consumed flip; treat Friday after 20:00 UTC or any weekend exposure as flatten-required; never remove the EA while exposure remains.

Preserve the outcome-blind mapping already frozen: exact H1 Supertrend10x3 flip, exact native M15 decision open, prior completed M15 ATR14, 1.00 ATR stop, 1.50R target, 8 completed M15 bars maximum, 0.25% requested risk, no additional signal/session/direction filters and no parameter search. Current code correctly computes outward tick-normalized 1ATR/1.5R geometry and closes at the ninth M15 open after 8 completed bars for the normal fully-filled path.

Required tests include bars immediately before/at DESIGN start and immediately before/at DESIGN end; DONE/PARTIAL/PLACED/reject sequences; delayed fill plus later flip; duplicate position/order states; restart with valid/missing/corrupt anchors and entry clock; actual SL/TP/direction/volume verification; failed time close followed by next-tick retry; Friday failure followed by weekend recovery; runtime fault with exposure; shift 7/8 boundary; and daily/peak lock persistence.

Primary references:

- https://www.mql5.com/en/docs/trading/ordersend
- https://www.mql5.com/en/docs/constants/tradingconstants/orderproperties
- https://www.mql5.com/en/docs/constants/errorswarnings/enum_trade_return_codes

Frozen design choices that remain economic rather than correctness questions: no trailing/breakeven, conservative stops/freeze rejection, signal consumption without later retry, 18:00/20:00 UTC cutoffs and 20-point deviation.
