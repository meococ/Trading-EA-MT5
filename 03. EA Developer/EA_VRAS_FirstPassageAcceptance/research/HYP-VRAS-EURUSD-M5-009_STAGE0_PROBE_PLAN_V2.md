# HYP-VRAS-EURUSD-M5-009 — Frozen Stage-0 Probe Plan V2 Amendment

Status: **FROZEN PRE-IMPLEMENTATION / PRE-PROBE / PRE-SOURCE / PRE-ECONOMIC-OUTCOME**  
Frozen: 2026-07-22 UTC  
Base contract: `HYP-VRAS-EURUSD-M5-009_STAGE0_PROBE_PLAN.md`, SHA256 `3B0D7206513245180CBA6951098DE09593F218F75357546F8314157DD7B5AC95`.

This V2 is a narrow pre-outcome amendment. Every V1 rule remains binding except the parity sample named in Stage-0 gate 3, which is replaced below. No Stage-0 count, event ledger, cadence, overlap, P/L or economic outcome was opened before this amendment.

## Reason for amendment

The V1 phrase “frozen HYP008 random-100 accepted-entry telemetry” would require mapping random position IDs through a case/lifecycle artifact that contains outcome fields. That is unnecessary contamination for an outcome-blind Stage-0 probe.

V2 binds parity directly to decision telemetry, which contains only decision-time state and no trade result.

## Added bound input

- HYP008 challenger decision telemetry: `02. AlphaFactory/runs/EA_VRAS_VolatilityNormalizedStop/20260722_233420/analysis/logs/EURUSD_DecisionTelemetry_HYP-VRAS-EURUSD-M5-008.csv`, SHA256 `C510692DB20D710D92FCDE52C8628B158D98AAFE00BD3211E5E36E74254EDF66`.

If the exact filename on disk differs only by the AlphaFactory timestamp suffix, the probe must locate exactly one `*_DecisionTelemetry_*.csv` in that bound run log directory and verify the frozen SHA before reading. Zero or multiple matches fail closed.

## Replacement Stage-0 parity gate 3

Select the first 100 `ORDER_ACCEPTED` telemetry rows after sorting by parsed broker `server_time`, then direction, preserving stable file order for any exact tie. Reconstruct the indicators from bound M1/H1 bars using only information available at each decision.

Required parity: 100/100 direction/gate pass and absolute deltas for H1 close, H1 EMA200, VWAP48 and ATR14 `<=5.1e-6` because telemetry is rounded to five decimals.

The probe implementation and tests must reject any path or schema containing lifecycle, report, casebook, random-sample, entry outcome, exit, net, P/L, return, MFE, MAE, SL/TP or other post-decision fields. The decision telemetry is the only HYP008 run log it may read.

## Authority

For HYP009 Stage-0, the effective contract is V1 plus this V2 amendment, with V2 controlling on conflict. V2 does not authorize MQL5, compilation, Model-0 or performance analysis.

