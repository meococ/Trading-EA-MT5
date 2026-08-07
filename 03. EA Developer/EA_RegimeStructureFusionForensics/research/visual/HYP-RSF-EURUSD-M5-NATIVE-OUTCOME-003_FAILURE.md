# HYP-RSF-EURUSD-M5-NATIVE-OUTCOME-003 — visual failure packet

Status: `KILLED_FAST_FORWARD_FRAME_STALE`

The first frozen flag was emitted at `2019.06.04 10:04:59`, but Windows
Graphics Capture still showed the chart frame held by MT5's `Skip to` fast
forward mode (March 2018). Pausing released the UI only after the engine had
already advanced to June 11–14, so neither frame met the frozen exit timestamp.

The JPEG-to-PNG normalization itself passed: the rejected image has the correct
PNG signature and 1906x1025 full-window dimensions. It remains inadmissible
because temporal coverage is wrong. The run was aborted after the first case,
with no report and no economic trial.

## Failure radius

The defect is external-window frame freshness during tester fast-forward. It
does not affect price data, indicators, signals, orders or economic results.

## Successor boundary

Use MT5's own `ChartScreenShot` at the exact post-exit bar while frozen chart
objects still exist. Split the seven cases into independent short Model-1
windows with at least 500 M5 warm-up bars. Each unique native PNG must be
signature-verified and joined to the VisualShots sidecar before interpretation.
