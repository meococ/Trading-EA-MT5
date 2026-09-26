# 2026-09-12 - HYP-GBB-S3-XAU-M15-001 control screen: KILL

## Verdict

`HYP-GBB-S3-XAU-M15-001` (EA_GbbSqueeze, XAUUSD M15, GBB S3 squeeze-release +
H4 EMA50 bias, TP 2R) killed at Model 0, registry row updated. Fourth
hypothesis through the complete governed chain.

Run `20260912_032825` (governed, portable isolate, MetaQuotes-Demo):

| Metric | Value |
|---|---|
| Window | all-available; history 2004.06.11 to 2026.09.10 |
| Trades | 408 (~0.97/week - FAIL, structurally rare) |
| Report PF | 1.00 (net -0.18 USD, breakeven) |
| Max DD | 2.5% PASS; MC p95 DD 3.5% PASS |
| History Quality | 98% |
| Cost-bound PF | 0.75 @x1.0 / 0.65 @x1.5 / 0.57 @x2.0 |
| Robustness | 14.3%; equity audit REJECT; overnight/weekend FAIL (2/1) |
| Unified verdict | REVIEW - 8 FAIL / 2 BLOCKED / 4 PASS of 14 gates |

First mechanism that is NOT directionally adverse: gross PF ~1.00 means the
S3 release signal carries roughly zero edge (not negative). But cadence is
structurally ~1/week - 10x below the band - and any positive residue is eaten
by cost repricing. Kill is cadence+economics, not data quality.

## Cell notes

- `deploy_indicators.ps1` extended: iCustom deps under the `Trading-EA-MT5\`
  prefix but WITHOUT the `IND_` name (e.g. `Modern_Bollinger_Bands_GBB`) were
  silently skipped; regex now covers both shapes. Deploy receipt bound.
- The orphan-terminal leak found its source: `trade_chart_capture.py` used
  `mt5.initialize(path=<isolate>)` which LAUNCHES the isolate, then
  `mt5.shutdown()` only detaches. Fixed: capture now diffs isolate PIDs
  around initialize and reaps the terminal it spawned (Owner-GUI-safe:
  Win32_Process path match, only PIDs absent before connect are stopped).
