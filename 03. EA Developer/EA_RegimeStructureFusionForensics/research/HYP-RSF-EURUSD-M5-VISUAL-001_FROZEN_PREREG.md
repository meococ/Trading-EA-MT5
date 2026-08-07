# HYP-RSF-EURUSD-M5-VISUAL-001 — Native visual evidence lane

Diagnostic-only replay to capture MT5 Strategy Tester native screenshots for
already-frozen RSF forensic cases. This hypothesis does not authorize parameter
tuning, outcome rescue, validation/holdout access, economic claims, or
promotion. The source logic remains the immutable parent RSF decision path; the
wrapper only adds chart screenshots and visual mapping telemetry.

## Bound case window

- Source population: terminal Cell 16 from `HYP-RSF-EURUSD-M5-BLOCK1-001`.
- Replay window: EURUSD M5, `2019.01.01` through `2019.06.05`. The early
  portion is indicator/model warm-up; screenshot capture remains limited to the
  frozen `FROZEN_13_V1` case windows.
- Capture token: `FROZEN_13_V1`.
- Visual mode: required via AlphaFactory `-Visual`, which must write
  `[Tester] Visual=1` into `config.ini`.
- Screenshot trigger: deal open/close events that fall inside frozen capture
  windows only.

## Pass/fail gates

- AlphaFactory config snapshot contains `Visual=1`.
- Run manifest contains `visual_mode=true`.
- Wrapper compile has 0 MetaEditor errors.
- At least one `*_VisualShots_*.csv` sidecar is collected.
- Any `RSFV_*.png` files are copied into the run `charts/` directory and
  hashed in `run_manifest.json`.
- If screenshot capture fails, the CSV must record `screenshot_ok=0` and
  `last_error`; no chart interpretation is allowed until fixed.

## Authority

This lane may improve visual/log evidence quality. It cannot override the
terminal Block-1 kill verdict or serve as an economic backtest.
