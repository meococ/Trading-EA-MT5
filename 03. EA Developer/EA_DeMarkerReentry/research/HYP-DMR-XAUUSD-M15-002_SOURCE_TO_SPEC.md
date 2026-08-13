# HYP-DMR-XAUUSD-M15-002 — source-to-spec mapping

- `iDeMarker(_Symbol, PERIOD_M15, 14)` and `iATR(_Symbol, PERIOD_M15, 14)` are native MT5 handles.
- `CopyBuffer(..., 1, 2, ...)` reads only the two completed DeMarker bars; the prior/current 0.30 and 0.70 re-entry predicates are unchanged from HYP001.
- Signal-bar OHLC and ATR are closed-bar values; execution is permitted only at the exact next M15 open.
- The five-bar extreme, 0.20 ATR buffer, 1.50R target, 12-bar exit, one-entry/day rule, sizing, margin limits and equity locks are unchanged.
- HYP002 adds only `stop_reference_distance` and `target_reference_distance` checks against BUY Bid / SELL Ask before `OrderCheck`. Invalid geometry increments a counter and consumes the signal; it does not move or retry SL/TP.
- `OrderCheck` remains fatal if broker validation still returns a nonzero retcode and logs the complete quote/SL/TP/distance context.

The authoritative HYP001 source is preserved in run `20260810_224300/snapshot/source/EA_DeMarkerReentry.mq5`; the current package is the fresh HYP002 revision.
