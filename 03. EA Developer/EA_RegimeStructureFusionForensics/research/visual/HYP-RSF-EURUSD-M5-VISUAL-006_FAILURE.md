# HYP-RSF-EURUSD-M5-VISUAL-006 — Failure Packet

Status: `KILLED_ENGINEERING_DIAGNOSTIC`

## What was proven

- Wrapper and QQE compiled with zero errors and zero warnings.
- Native Strategy Tester Visual Mode was inspected directly on `EURUSD M5`.
- The native frame was captured as a real PNG (`504575` bytes) from the MT5
  window; it was not a Python/synthetic price rendering.
- TB display retention was materially cleaner: one active demand zone and one
  active supply zone kept price legible.
- The forensic CSV proved QQE calculation data was live. Examples include
  secondary values `21.85338598`, `35.92669299`, `-28.51832675` and
  `10.74083662`.

## Why this ID is killed

1. Neither the original color histogram nor the three ordinary mirror plots
   painted in the native QQE pane; only the white QQE trend line appeared.
2. The external PNG was encoded after AlphaFactory had already attempted its
   import, so this run did not hash-bind the otherwise valid native capture.

No economic conclusion is authorized. The follow-up must use MQL5's documented
zero empty value for `DRAW_COLOR_HISTOGRAM`, retain EA-consumed buffers `3`, `4`
and `8`, and allow a bounded wait for the explicit external capture path. The
repairs require a fresh diagnostic hypothesis ID.
