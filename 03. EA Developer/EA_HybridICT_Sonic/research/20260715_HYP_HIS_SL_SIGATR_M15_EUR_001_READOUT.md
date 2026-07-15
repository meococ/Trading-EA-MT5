# HYP-HIS-SL-SIGATR-M15-EUR-001 — Model 0 readout

Date: 2026-07-15  
Cost: **UNVERIFIED**

## Contract

Entry: Hybrid confluence (unchanged).  
SL: signal extreme ± **1.0×ATR** (`InpUseLevelSl=false`, no Dragon floor).  
TP: RR 2.5.

## Run

| Field | Value |
|---|---|
| Run | `02. AlphaFactory/runs/EA_HybridICT_Sonic/20260715_170714` |
| Window | EURUSD M15 2020.01.01→2026.07.15 Model 0 |
| Receipt SHA | `8B00596A03037A65603E359AADBEB2D44241CC8DFC21B340825435AA3EB05E92` |

## Results

| Metric | Value | Gate |
|---|---|---|
| Trades | **76** | sample OK vs DIAG N=3 |
| PF | **0.98** | **KILL** (<1.30) |
| Net | **−$210.25** | fail |
| Max DD | 2.2% | within 10% toy |
| Expectancy | −$2.77/trade | fail |
| Elapsed tpw | ~0.22 (76 / ~338w) | **KILL** cadence |

## Verdict

`KILLED_AT_MODEL_0` — SL contract change **restored cadence** but **no edge** under tester cost (UNVERIFIED).  

**Do not** densify: disable Europe / hour-8 / weekday from analyzer suggestions — that would be post-hoc rescue. New idea only if Owner opens independent mechanism.

## Vs lineage

| Hyp | N | PF | Note |
|---|---:|---:|---|
| Parent Hybrid (Dragon±40 SL) | 0 | — | empty |
| DIAG (level SL, no Dragon floor) | 3 | toy | plumbing |
| **SIGATR (signal±1ATR)** | **76** | **0.98** | kill edge+cadence |
