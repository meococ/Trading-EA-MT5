# HYP-LASR-XAUUSD-M5-001 - Frozen Cost Acquisition Plan

Status: `FROZEN_OUTCOME_BLIND_DATA_ACQUISITION_ONLY`

This plan authorizes one read-only historical spread acquisition. It does not
authorize an EA backtest, order, performance read, parameter change, or economic
claim.

## Identity

- Candidate: `HYP-LASR-XAUUSD-M5-001`
- Symbol/timeframe: `XAUUSD M5`
- Requested window: `2016.01.04` through `2024.12.31`
- Broker/company: `FivePercentOnline-Real` / `Five Percent Online Ltd`
- Terminal: `02. AlphaFactory/runtime/mt5-portable-fivepercent/terminal64.exe`
- Frozen terminal SHA-256: `20DFEFD944AE482781AC1E83A736A976ECF0315661E54B5771E327F1FFB2B35C`
- Geometry: digits `2`, point/pip size `0.01`

## Authorized acquisition

Run `export_mt5_tick_spread_evidence.py` once with the exact identity above,
30-day chunks and minimum synchronized-M5 population coverage `0.99`. Write:

- `research/evidence/HYP-LASR-XAUUSD-M5-001/COST_SOURCE/XAUUSD_M5_RAW_TICK_SPREAD.csv`
- `research/evidence/HYP-LASR-XAUUSD-M5-001/COST_SOURCE/XAUUSD_M5_RAW_TICK_SPREAD_RECEIPT.json`

The exporter may start the frozen portable terminal only to call read-only MT5
history APIs. It may not place or simulate trades. If the broker has no raw-tick
coverage for part of the requested window, preserve the actual returned bounds;
do not synthesize or silently backfill spread history.

## Downstream restriction

The spread receipt may support a `RESEARCH_PROXY` cost manifest only. Existing
same-symbol tester commission and executable-quote latency samples may be copied
with hashes and explicit lineage, but neither is an observed live-fill sample.
Therefore `promotion_eligible=false` remains mandatory regardless of Model-0
results.
