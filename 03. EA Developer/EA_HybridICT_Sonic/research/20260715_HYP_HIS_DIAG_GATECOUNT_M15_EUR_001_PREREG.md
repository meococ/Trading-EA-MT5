# HYP-HIS-DIAG-GATECOUNT-M15-EUR-001 — Prereg (Owner B)

**Status:** Owner-authorized DIAG after offline gate-count A.  
**Parent:** `HYP-HYBRID-ICT-SONIC-M15-EURGBP-001` = `KILL_AT_MODEL0_EMPTY`  
**Role:** diagnostic telemetry / SL-antagonism fix — **not** promotion / not live.

| Field | Frozen value |
|---|---|
| hypothesis_id | `HYP-HIS-DIAG-GATECOUNT-M15-EUR-001` |
| package | `EA_HybridICT_Sonic` |
| symbol / TF | EURUSD M15 |
| window | 2020.01.01 → 2026.07.15 |
| model | 0 |
| run_role | control |
| deposit | 100000 |
| decision surface | `InpUseDragonSlFloor=false` (level SL only) + gate counters OnDeinit |
| Dragon period | 34 (frozen — no 30–38 densify) |
| RR | 2.5 |
| MaxSl ATR mult | 2.5 |
| Wave / PVSRA | ON (same as offline stack that produced 1372 pre-SL survivors) |

## Evidence that authorized this DIAG

Offline A: `preflight/20260715_HIS_OFFLINE_GATECOUNT_EURUSD_M15.json`  
SHA `FDCB7258A7385C97833D619209C03C25E40D8B12FE0DCF58F455857E6523D006`  
Finding: N7 PVSRA=1372 → N8 SL OK=0 (100% fail on Dragon±40 vs MaxSl).

## Kill / stop rules

- This DIAG may show N>0 after SL fix — **does not** clear PF/GOAL gates.
- Cost UNVERIFIED → no “PF≥1.65 after slip” claim.
- Forbidden: densify FVG%, Dragon 30–38, post-hoc hour/day veto from readout.
- If N still 0 with DragonSlFloor=false → deeper gate/exec bug; new packet.

## Success of DIAG (not edge)

1. Tester shows N>0 **or** OnDeinit counters show N8_sl_ok>0 path reached PlacePending.
2. Gate counter print matches offline ranking order (approx).
