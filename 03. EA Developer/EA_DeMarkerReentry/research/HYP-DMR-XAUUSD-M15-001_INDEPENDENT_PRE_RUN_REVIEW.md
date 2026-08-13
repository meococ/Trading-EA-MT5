# HYP-DMR-XAUUSD-M15-001 — independent pre-run review

Verdict: `PASS_BASELINE`.

- Reviewed source SHA256: `6664BA3C441799ED89DB48CAB19126D6012C74F834FAD5DAD0634F65A5B1659E`.
- Native DeMarker14 buffer mapping is exact: `CopyBuffer(shift1,count2)` yields shift2 then shift1 in physical order; 0.30/0.70 re-entry predicates match the preregistration.
- Exact-next is `+900` seconds. Stop uses exactly five completed bars plus `0.20*ATR14`; target is 1.5R and time exit is 12 bars.
- Deferred warmup re-anchors then returns. Design bounds, inventory, margin sizing and execution failures are fail-closed.
- KVO helpers remain unreachable; the active path calls only `PreloadDeMarkerState` and `ProcessDeMarkerClosedBar`.

No fatal blocker was found before one untuned Model-0 baseline. This review opened no market data or outcomes.
