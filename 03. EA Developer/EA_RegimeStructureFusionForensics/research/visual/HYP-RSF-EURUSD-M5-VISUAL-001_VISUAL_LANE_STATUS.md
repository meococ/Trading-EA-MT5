# HYP-RSF-EURUSD-M5-VISUAL-001 — native visual lane status

Generated: 2026-08-07

## Superseded by native screenshot lane

The zero-data `/config` limitation documented below was later bypassed with a
real interactive Strategy Tester Visual Mode lane. Eight native MT5 screenshots
with compiled MBB, QQE and TB indicators plus actual trade markers now exist at
`native_structural_event_005/`. Their SHA256 manifest and pairwise price-action
analysis are recorded in `native_structural_event_005/NATIVE_MT5_SE005_CASEBOOK.md`.

This resolves the chart-evidence engineering blocker. It does not change the
economic verdict: HYP-010 is terminally killed at PF 0.714519 and may not be
rescued from outcome-derived chart patterns.

## Result

The AlphaFactory `/config` visual replay lane is not usable as chart evidence on the current MT5 portable environment.

Observed evidence:

- MT5 journal reports visual testing for `EA_RegimeStructureFusionForensics` on `EURUSD,M5`.
- The exported MT5 report is created, but its tester metrics are zero-data:
  - `Bars=0`
  - `Ticks=0`
  - `Symbols=0`
- No EA telemetry sidecars are written for the visual run.
- No `RSFV_*.png` native screenshots are produced.

AlphaFactory now fails this condition explicitly:

```text
Visual replay produced a zero-data MT5 report (bars=0 ticks=0). This is not acceptable chart evidence; use a real local visual tester lane before strategy forensics.
```

## Commands verified

```powershell
python -m pytest '02. AlphaFactory\tests\test_large_log_reader.py' '02. AlphaFactory\tests\test_visual_replay_contract.py' -q
```

Result: `7 passed`.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File '02. AlphaFactory\alpha.ps1' compile 'EA_RegimeStructureFusionForensics'
```

Result: compile success, MetaEditor log `0 errors`.

## Next required lane

Do not use Python-rendered/simulated casebook charts as the strategy-forensics source.

Build a native chart-evidence lane that uses a real MT5 chart with compiled AlphaFactory indicators and trade sidecars:

1. Load the exact symbol/timeframe/date window on a local MT5 chart.
2. Attach the compiled indicator bundle:
   - AI Regime Detection
   - Volatility Regime Classifier
   - Modern Bollinger Bands
   - TB Smart Money Concept
   - QQE MOD
3. Draw real trade entry/exit objects from AlphaFactory lifecycle/forensic CSV.
4. Capture `ChartScreenShot` PNG evidence from MT5.
5. Bind every screenshot to sidecar row IDs and run manifest SHA.

Only after this native chart-evidence packet exists should RSF strategy logic be reworked.
