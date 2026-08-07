# HYP-RSF-EURUSD-M5-NATIVE-OUTCOME-006 — frozen live-window capture

Frozen before any replay.

## Mechanism

- Reuse the seven independent short windows and frozen cases from OUTCOME-004.
- Run the real portable MT5 Strategy Tester in normal Visual Mode at maximum
  speed; do not activate `Skip to`.
- At the exact post-exit bar, draw entry/exit/SL/TP, navigate to `CHART_END`,
  redraw, publish the case flag and hold the live chart for 30 seconds.
- Capture the complete portable tester window through Windows Graphics Capture.
- Losslessly decode/re-encode the unchanged full frame as PNG only because the
  capture API transports JPEG. No crop, scale, annotation or synthetic render.
- Verify PNG signature, dimensions, filename-to-case mapping and visible event
  coverage before AlphaFactory imports it as native chart evidence.

The native `ChartScreenShot` request may remain as diagnostic telemetry, but its
file is not required because the portable environment failed to materialize it
after 200 ticks in OUTCOME-005.

## Acceptance

Each case produces one complete-window `NATIVE_MT5_OUTCOME006_*.png` that visibly
contains bars through exit plus one M5 bar, entry/exit/SL/TP objects, MBB/TB
overlays and exactly one QQE pane. The flag content, screenshot timestamp and
case filename must join one-to-one. Any stale or ambiguous frame is rejected.

Model-1 performance is diagnostic-only. No signal, risk, exit or indicator
parameter may change.
