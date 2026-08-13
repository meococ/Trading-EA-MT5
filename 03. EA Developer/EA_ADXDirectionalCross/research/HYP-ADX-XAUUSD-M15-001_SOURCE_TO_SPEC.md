# HYP-ADX-XAUUSD-M15-001 — source-to-spec mapping

- Native `iADX(...,14)` buffers follow the official MT5 contract: `0=ADX`, `1=+DI`, `2=-DI`.
- Every decision uses `CopyBuffer` at shift 1 for the prior/current completed M15 bars; no current-bar indicator value is used.
- A signal requires a strict DI polarity cross, current ADX at least 25 and current ADX strictly above prior ADX.
- Only the exact next M15 open may execute the event. One accepted entry per calendar day bounds repeated crosses.
- The generic closed-bar structural stop, target, time exit, account locks, sizing and broker-reference geometry are unchanged from the last engineering-valid execution engine.
- The old KVO helper is dead compile-isolated code; `OnTick` calls only `ProcessAdxClosedBar`.
