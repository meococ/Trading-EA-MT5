# HYP-RSF-EURUSD-M5-NATIVE-OUTCOME-004 — frozen native-chart preregistration

Frozen before implementation and before any case replay.

## Purpose

Capture the seven frozen losing trades directly through MT5 `ChartScreenShot`
on the first completed M5 bar after each frozen exit. This is the real Strategy
Tester chart with the compiled MQL indicators, not a Python or HTML render.

## Frozen capture design

- Add `InpForensicNativeCaseIndex` (`1..7`) to select exactly one frozen case.
- Run seven independent Model-1 visual replays so no multi-year UI fast-forward
  frame can contaminate another case.
- Each replay starts at least ten trading days before its case, which exceeds
  the largest 500-bar visual/indicator warm-up requirement.
- Draw entry, exit, SL and TP; set auto-scroll, no chart shift, scale 1, navigate
  to `CHART_END`; redraw; then request a uniquely named native PNG immediately.
- Force screenshot verification before deleting the frozen chart objects.
- External WGC frames may be viewed for operator confirmation, but they are not
  evidence when MT5 is in fast-forward mode.

## Frozen cases and windows

| Index | Case | From | To |
|---:|---|---|---|
| 1 | BREAKOUT_LONG | 2019.05.20 | 2019.06.06 |
| 2 | TREND_LONG | 2019.09.25 | 2019.10.11 |
| 3 | RANGE_LONG | 2019.11.15 | 2019.12.02 |
| 4 | TREND_SHORT | 2020.04.06 | 2020.04.22 |
| 5 | BREAKOUT_SHORT | 2020.10.01 | 2020.10.19 |
| 6 | RANGE_SHORT | 2020.12.01 | 2020.12.18 |
| 7 | EXTREME_LOSS | 2022.05.30 | 2022.06.15 |

## Acceptance

Each case must produce exactly one unique `RSFV_*.png`, a VisualShots row with
`screenshot_ok=1`, PNG signature, non-zero dimensions, frozen case ID, and
visible bars through the exit plus one completed M5 bar. The chart must show the
entry/exit objects, SL/TP, MBB/TB overlays and one QQE pane.

No strategy parameter, signal, risk or management value may change. Model-1
reports are diagnostic-only and cannot support an economic claim.
