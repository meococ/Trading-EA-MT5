# Session closeout — PWHL + H4 balance offline (2026-07-14)

Status: `COMPLETE`  
GPT: waived  
Model 0 launched: **0**

## Context

Parallel lane owns structural **V4** five-pack (OB / D1-inside / London-fail /
Asia-fail / break-pause — all KILL). This closeout covers a **sibling** batch
with collision-safe paths (`STRUCTURAL_PWHL_H4BAL_*`).

## Board

| Thesis | Metrics | Verdict |
|---|---|---|
| E `HYP-W1-PWHL-SWEEP-RECLAIM-H1-001` | N=**180** PF **0.85** tpw **0.69** x1.5 **0.79** | **KILL** |
| F `HYP-H4-BALANCE-BREAK-H1-ACCEPT-001` | N=**75** PF **1.67** tpw **0.29** x1.5 **1.53** | **KILL** (thick; cadence starve) |

Receipt SHA: `DA1A43A294ACF5F93DC0FA51DC0EC63E74D97CA44D9748C5BE530237C6EF07D9`  
JSON: `preflight/20260714_STRUCTURAL_PWHL_H4BAL_OFFLINE_PROBES.json`  
MD: `readouts/20260714_STRUCTURAL_PWHL_H4BAL_OFFLINE_PROBES.md`  
De-dup: `readouts/20260714_STRUCTURAL_PWHL_H4BAL_DEDUP_CLEARANCE.md`

## Honest read (no retune)

- **E** negative edge — do not mine reclaim bars/hours/RR.
- **F** thick PF + stress PASS diagnostically but N/cadence fail joint screen —
  do not loosen BAL_LEN/ATR from this kill.
- Combined with parallel V4 five-pack: still **zero** offline survivors →
  **zero Model 0**. Best shelf RR2 `194548` unchanged.
- Phase-0 compose still `BLOCKED_REQUIRES_CLEAN_FUTURE_FREEZE_REVIEW`.

## Next

1. New structural object outside V4 five-pack + E/F + all prior kills.
2. Optional Owner Phase-0 clear (not discovery headline).
3. QFSI/Real = parallel hygiene only.
