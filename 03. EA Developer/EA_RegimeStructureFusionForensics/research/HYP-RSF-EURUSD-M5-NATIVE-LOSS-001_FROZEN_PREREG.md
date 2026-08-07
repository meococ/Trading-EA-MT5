# HYP-RSF-EURUSD-M5-NATIVE-LOSS-001 — Seven Native Losing-Trade Charts

Status: `PREREGISTERED_DIAGNOSTIC_ONLY`

## Purpose

Replace the prior synthetic casebook as decision evidence with seven screenshots
captured from the real MT5 Strategy Tester Visualization window.  Cases were
selected and frozen before native chart inspection by
`HYP-RSF-EURUSD-M5-FORENSICS-001`:

1. `RSF-C16-BREAKOUT-LONG-L` — 2019.06.04 09:55 server
2. `RSF-C16-TREND-LONG-L` — 2019.10.09 11:20 server
3. `RSF-C16-RANGE-LONG-L` — 2019.11.29 11:05 server
4. `RSF-C16-TREND-SHORT-L` — 2020.04.20 15:05 server
5. `RSF-C16-BREAKOUT-SHORT-L` — 2020.10.16 09:25 server
6. `RSF-C16-RANGE-SHORT-L` — 2020.12.16 10:25 server
7. `RSF-C16-EXTREME-LOSS` — 2022.06.13 10:00 server

## Frozen visual contract

- EURUSD M5, `2018.01.01` through `2022.06.14`.
- MT5 Model 1 (one-minute OHLC) is used only to advance the native chart and
  closed-bar indicators efficiently.  No trade path, P/L, execution outcome or
  economic statistic from this batch may be consumed.
- Correct grouped-iCustom QQE/MBB/TB transport from VISUAL-009 is mandatory.
- Clean preset shows MBB, TB BOS/MSS/sweeps and QQE.  TB cell/void/trail values
  remain in forensic CSV but do not cover price candles.
- At each frozen timestamp, native objects mark the original entry, SL and TP;
  the EA writes one explicit capture flag and pauses at most 12 seconds.
- AlphaFactory must import exactly seven explicitly named current-run PNGs.  No
  directory search, stale file or synthetic renderer is permitted.

Expected image names:

- `NATIVE_MT5_LOSS001_BREAKOUT_LONG.png`
- `NATIVE_MT5_LOSS001_TREND_LONG.png`
- `NATIVE_MT5_LOSS001_RANGE_LONG.png`
- `NATIVE_MT5_LOSS001_TREND_SHORT.png`
- `NATIVE_MT5_LOSS001_BREAKOUT_SHORT.png`
- `NATIVE_MT5_LOSS001_RANGE_SHORT.png`
- `NATIVE_MT5_LOSS001_EXTREME_SHORT.png`

## Acceptance and stop rule

Pass requires zero-error compile, seven unique PNGs imported and SHA-bound to
one completed Visual Mode run, seven `REFERENCE_ENTRY` CSV rows with valid QQE
probe masks, and direct visual inspection confirming readable price, markers,
MBB/TB structure and QQE.  The screenshots may support failure-mechanism design
only; they cannot justify a fitted threshold or rehabilitate Cell 16.

Any missing image, stale timestamp, invalid PNG, sidecar mismatch or unreadable
chart kills the batch.  Economic, optimization, validation, holdout and
promotion authority are all false.
