# HYP-RSF-EURUSD-M5-VISUAL-007 — Native Window Import + QQE Zero-Empty Smoke

Status: `PREREGISTERED_DIAGNOSTIC_ONLY`

## Frozen delta

VISUAL-006 showed live QQE values in CSV but no histogram in native Visual Mode.
This follow-up tests one renderer-contract repair and one evidence-timing repair:

1. QQE histogram and its three display mirrors use `0.0` as the non-drawn value,
   as specified by MetaQuotes for `DRAW_COLOR_HISTOGRAM`. Calculations and
   EA-consumed buffers `3` (primary), `4` (secondary) and `8` (state) are unchanged.
2. AlphaFactory waits at most 120 seconds for the one explicitly named current-run
   native PNG before failing. All path, timestamp, signature, size and Visual Mode
   guards remain mandatory.

No trading rule, mask, risk, parameter or parent decision handle may change.

## Frozen execution

- EA: `EA_RegimeStructureFusionForensics`
- symbol/timeframe: `EURUSD M5`
- interval: `2019.06.03` through `2019.06.05`
- Model 0; no artificial delay; current spread
- deposit/leverage: `100000 USD`, `1:100`
- Visual Mode required
- smoke timestamp: `1559642100`
- native target: `NATIVE_MT5_VISUAL007_EURUSD_M5.png`

## Acceptance and stop rule

Pass requires zero-error/zero-warning compile, direct inspection of the actual MT5
Visual Mode window, visible gray/cyan/magenta QQE columns, legible one-cell/one-void
TB context, and successful SHA-256-bound import of the current-run native PNG into
the run `charts` manifest. Internal `ChartScreenShot` failure remains separately
truthful and is not required to pass this external-capture lane.

If either native import or QQE rendering fails, kill this ID. This diagnostic cannot
authorize economic claims, optimization, holdout access or promotion.
