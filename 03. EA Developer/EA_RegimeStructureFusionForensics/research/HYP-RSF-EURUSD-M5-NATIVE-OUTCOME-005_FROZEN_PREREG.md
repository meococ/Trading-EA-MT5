# HYP-RSF-EURUSD-M5-NATIVE-OUTCOME-005 — frozen async native capture

Frozen before implementation and before any case replay.

## Mechanism

The seven case identities, prices, exits and short visual windows remain exactly
those frozen in OUTCOME-004. The only authorized change is screenshot lifecycle:

1. draw entry, exit, SL and TP at the post-exit bar;
2. queue metadata on that tick without force verification;
3. retain all reference objects;
4. issue `ChartScreenShot` on a later tester tick;
5. poll file existence/size for up to the frozen verify-tick budget;
6. write `screenshot_ok=1` only after the native PNG is readable;
7. clean objects only after evidence has been collected or at deinit.

The chart remains native MT5 Visual Mode with MBB/TB overlays and one QQE pane.
Each case is isolated in its own Model-1 diagnostic window with more than 500 M5
warm-up bars. No external WGC frame is admissible while Skip-to fast-forward is
active.

## Acceptance

Each case must yield one unique `RSFV_*.png`, PNG signature, non-zero dimensions
and a VisualShots row with `request_ok=1`, `file_verified=1`,
`screenshot_ok=1`, the correct case ID and exact frozen event time. Visual pixel
review must then confirm bars through the exit, entry/exit/SL/TP objects, MBB/TB
overlays and exactly one QQE pane.

No signal, order, stop, target, indicator input, risk or economic parameter may
change. All Model-1 economic outputs are inadmissible.
