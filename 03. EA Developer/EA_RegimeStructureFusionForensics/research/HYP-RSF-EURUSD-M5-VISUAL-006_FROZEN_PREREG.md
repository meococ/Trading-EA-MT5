# HYP-RSF-EURUSD-M5-VISUAL-006 — Native Window Import + QQE Mirror Smoke

Status: `PREREGISTERED_DIAGNOSTIC_ONLY`

## Purpose and bounded engineering delta

VISUAL-005 proved that this tester build can return `ChartScreenShot=true` while
never creating a PNG. It also proved from the forensic CSV that QQE values exist,
although MT5 did not render the original color-column plot. VISUAL-006 validates
two evidence/display repairs only; it is not a strategy or parameter test.

The frozen delta is limited to:

1. AlphaFactory may import one PNG captured from the actual MT5 Strategy Tester
   Visual Mode window. The file must be workspace-local, current-run, named
   `NATIVE_MT5_*.png`, have a valid PNG signature and plausible size, and is
   hash-bound inside the run chart manifest.
2. QQE preserves public EA buffers `0..9` and all calculations. Three appended
   display-only `DRAW_HISTOGRAM` mirrors render neutral, up and down columns using
   the exact final Pine color conditions.
3. The display-only TB handle remains bounded to one cell and one void; the parent
   decision handle and all Cell-16 trading rules remain unchanged.
4. Internal screenshot telemetry remains truthful: queue acceptance without file
   verification remains a failed internal probe and is not counted as evidence.

## Frozen execution

- EA: `EA_RegimeStructureFusionForensics`
- symbol/timeframe: `EURUSD M5`
- interval: `2019.06.03` through `2019.06.05`
- Model 0, no artificial delay, current spread
- deposit/leverage: `100000 USD`, `1:100`
- Visual Mode required
- parent Cell-16 masks and decision engines unchanged
- smoke timestamp: `1559642100` (`2019.06.04 09:55` server-chart value)
- screenshot settle: 250 ms; internal verification timeout: 20 tester ticks
- external image target: `NATIVE_MT5_VISUAL006_EURUSD_M5.png`

## Acceptance and stop rule

Engineering pass requires all of the following:

- wrapper and QQE compile with zero errors and zero warnings;
- an actual MT5 Visual Mode window is inspected and captured during this run;
- the native PNG is imported into the run `charts` directory, has a SHA-256 entry
  in the completed manifest, and passes the PNG/current-run/path guards;
- direct native inspection shows QQE neutral/cyan/magenta histogram columns;
- price remains legible with at most one active display cell and one active void;
- internal `VisualShots` truth is retained even if `file_verified=0`;
- no indicator alert storm or tester error.

If the native image cannot be imported, or the QQE histogram remains absent, kill
this ID and repair only that evidence/display defect under a new diagnostic ID.
No Python price rendering, synthetic chart, economic claim, parameter selection,
holdout access or promotion is authorized by this smoke.
