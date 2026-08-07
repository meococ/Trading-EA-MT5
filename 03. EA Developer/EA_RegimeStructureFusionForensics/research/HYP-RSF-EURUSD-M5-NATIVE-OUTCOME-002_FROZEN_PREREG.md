# HYP-RSF-EURUSD-M5-NATIVE-OUTCOME-002 — frozen diagnostic preregistration

Frozen before implementation and before the first replay.

## Purpose

Repair the native MT5 visual-evidence lane so each screenshot proves the actual
failed trade anatomy instead of only the pre-entry context. The seven cases,
their entry/exit timestamps, prices, SL/TP and outcome labels remain identical
to `FROZEN_7_LOSERS_V1`.

## Authorized display-only change

- Add schedule identity `FROZEN_7_LOSER_OUTCOMES_V1`.
- Wait until the frozen trade exit plus one M5 bar.
- Draw the frozen entry, exit, SL and TP as native MT5 chart objects.
- Enable chart auto-scroll, navigate to `CHART_END`, use a wide zoom and redraw
  before both `ChartScreenShot` and external native-window capture.
- Emit `REFERENCE_OUTCOME` telemetry and a capture flag tied to the frozen case.

No signal, indicator buffer, route, session, order, stop, target, risk or
position-management value may change. Model 1 is authorized only for visual
price/indicator anatomy. No economic metric from this replay may be consumed.

## Acceptance

Each imported PNG must be a genuine MT5 Strategy Tester Visual Mode window and
must visibly contain:

1. the entry arrow and entry level;
2. the exit arrow after the failed trade;
3. SL and TP levels;
4. native MBB and TB-SMC overlays;
5. one native QQE pane;
6. price bars through at least the frozen exit.

If any item is absent, that image is context-only and cannot support an outcome
claim. The lane remains diagnostic-only and cannot make an economic or
promotion claim.
