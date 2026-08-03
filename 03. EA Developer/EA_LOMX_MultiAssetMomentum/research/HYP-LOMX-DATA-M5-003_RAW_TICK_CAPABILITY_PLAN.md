# HYP-LOMX-DATA-M5-003 - Outcome-Blind Raw-Tick Capability Plan

Status: `FROZEN_DATA_CAPABILITY_ONLY_NO_ECONOMICS`

This plan is frozen after the invalid HYP-LASR-XAUUSD-M5-001 execution exposed
that the MT5 tester had only 7,144 XAUUSD M5 bars for the requested 2018-2022
window. It authorizes read-only market-history calls only. It does not authorize
an EA launch, simulated trade, PnL/PF/cadence read, parameter change, new
economic hypothesis, optimization, validation, holdout, paper, or live access.

## Fixed scope

- Parent design: `HYP-LOMX-DESIGN-M5-002`
- Remaining target with unmeasured tester capability: `EURUSD M5`
- Requested window: `2016.01.04` through `2024.12.31`
- Terminal: `02. AlphaFactory/runtime/mt5-portable-fivepercent/terminal64.exe`
- Terminal SHA-256:
  `20DFEFD944AE482781AC1E83A736A976ECF0315661E54B5771E327F1FFB2B35C`
- Broker/server: `Five Percent Online Ltd` / `FivePercentOnline-Real`
- Geometry: digits `5`, point `0.00001`, pip size `0.0001`
- Exporter: `02. AlphaFactory/tools/export_mt5_tick_spread_evidence.py`
- Chunk size: `30` days
- Required synchronized-M5 raw-tick coverage: `>= 0.99`

## Outputs

On success only:

- `research/evidence/HYP-LOMX-DATA-M5-003/EURUSD_M5_RAW_TICK_SPREAD.csv`
- `research/evidence/HYP-LOMX-DATA-M5-003/EURUSD_M5_RAW_TICK_SPREAD_RECEIPT.json`

On failure, preserve a failure receipt containing the exact exception, terminal
identity, requested window, zero orders/positions/outcomes, and bounded
diagnostic readback. Do not synthesize ticks or treat M1 BID/ASK bars as raw
ticks.

## Decision rule

- If coverage is at least 0.99, a fresh atomic EURUSD successor may proceed to
  its own preregistration and one Model-0 control.
- If coverage is lower, no LOMX atomic sleeve may enter Model 0 on this terminal
  until an outcome-blind data-population repair is completed and independently
  fingerprinted. Python/M1 proxy performance must not be relabeled as MT5
  Model 0 or promotion-grade evidence.
