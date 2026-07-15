# Readout — HYP-ASIAN-SWEEP-RECLAIM-M15-001

Date: 2026-07-14  
Run: `20260714_193808`  
EA: `EA_M15AsianSweepReclaim`  
Verdict: **`KILLED_AT_MODEL_0`** (N=0 / no trades)

## Metrics

| Metric | Value |
|---|---|
| Trades | **0** |
| Window | USDJPY M15 2021-2025 Deposit=100000 Model 0 |

Alpha closeout hit known `includes_sha256` flake after report ready; report kept
(empty trade set). Analyzer: "No trades found".

## Decision

Kill — no sample. Do **not** retune Asia/London windows, body ATR, or day filters
from this null result. Mechanism may be too strict (sweep+reclaim same-day chain).

## Cost

`UNVERIFIED_TESTER_DEFAULT`. Not confirmed.
