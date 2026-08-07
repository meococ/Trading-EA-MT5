# HYP-RSF-EURUSD-M5-NATIVE-OUTCOME-003 — frozen diagnostic preregistration

Frozen before implementation and before the first replay.

## Purpose

Produce seven admissible post-exit screenshots from the real portable MT5
Strategy Tester Visual Mode window. The frozen cases, timestamps, entry/exit,
SL/TP and native indicator stack are identical to OUTCOME-002.

## Authorized display and transport changes

- Hold each external capture flag for 30,000 milliseconds.
- Set `CHART_AUTOSCROLL=true`, `CHART_SHIFT=false`, `CHART_SCALE=1`, navigate to
  `CHART_END` with zero shift, then call `ChartRedraw`.
- Capture the complete native tester window through Windows Graphics Capture.
- If the capture API returns JPEG bytes, decode and re-encode the same complete
  pixels as PNG. No crop, scaling, compositing, annotation or synthetic render
  is permitted.
- Verify PNG signature, non-zero dimensions and one-to-one case filename before
  AlphaFactory import.

No signal, indicator buffer, route, session, order, stop, target, risk or
position-management value may change. Model 1 remains visual-only. Its economic
metrics are inadmissible.

## Acceptance

Every imported PNG must visibly contain the frozen exit bar and all of:

1. entry arrow and entry level;
2. exit arrow and exit label;
3. SL and TP levels;
4. native MBB and TB-SMC overlays;
5. exactly one native QQE pane;
6. price bars through at least one completed M5 bar after exit.

Any image failing any item is rejected rather than interpreted.
