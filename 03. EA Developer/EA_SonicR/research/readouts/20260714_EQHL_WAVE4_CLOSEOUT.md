# Closeout — EQHL intake-kill + Wave4 offline board

Date: 2026-07-14 ~22:40 ICT  
Authority: Owner CONTINUE `HYP-H1-EQHL-SWEEP-RECLAIM-001`  
GPT: waived · Grok · no-Git · cost honesty  
Status: **`EQHL_KILL_INTAKE__WAVE4_PROBES_DONE__MODEL0_BLOCKED_REAL__GOAL_UNMET`**

## Board

| Hypothesis | Stage | N | PF | tpw | x1.5 | Verdict |
|---|---|---:|---:|---:|---:|---|
| `HYP-H1-EQHL-SWEEP-RECLAIM-001` | intake | — | — | — | — | **KILL_AT_INTAKE** vs ASR+SFP |
| `HYP-M15-IB-OVERLAP-BREAK-001` | offline | 990 | 1.203 | 3.80 | 1.111 | **PROBE_OK / Model0 queued** |
| `HYP-H1-RV-COMPRESS-BREAK-001` | offline | 94 | 1.421 | 0.36 | 1.337 | **KILL_PROBE** cadence |
| `HYP-GBPJPY-LEAD-USDJPY-H1-001` | offline | 1284 | 1.147 | 4.92 | 1.062 | **PROBE_OK / Model0 queued** |
| `HYP-H1-EMA-STACK-PB-001` | offline | 1634 | 1.022 | 6.27 | — | **KILL_PROBE** |
| `HYP-H1-LONDON-OPEN-DRIVE-001` | offline | 104 | 1.349 | 0.40 | 1.267 | **KILL_PROBE** cadence (thick note) |

## Why EQHL died at intake

Equal-HL sweep→reclaim is the same liquidity-grab archetype as killed
`HYP-ASIAN-SWEEP-RECLAIM-M15-001` and `HYP-H1-SWING-FAILURE-001` (SFP). Swapping
the level constructor is densify, not a new thick edge. AsianTail is independent
but not sufficient to clear. Doc:
`readouts/20260714_H1_EQHL_SWEEP_RECLAIM_DEDUP_INTAKE_KILL.md`.

## Model 0 blocker (infra, not discovery stall)

Compile IB OK. `alpha.ps1 backtest` fail-closed:
`Unrelated terminal64 process already running (PID 27628)` —
account **26451822** / server **`FivePercentOnline-Real`**. Agent did **not**
kill Real. Queued Model 0: IB-Overlap → GBPJPY-Lead when exclusive tester free.

Optimistic offline already shows both queued IDs **below** research HIT screen
(PF>1.30 ∧ x1.5≥1.25). Model 0 remains lawful confirmation, expected PARK/KILL.

## vs GOAL

Unmet. Best Demo shelf unchanged: RR2 `20260714_194548` PF **1.378** / ~**2.01**/wk
(a priori +$12 x1.5 FAIL). MaxKZ2 Real-P50 FAIL. Thick-sparse notes (RV /
London-open-drive / LondonNY) survive friction but cannot be sole GOAL book.

## Explicit bans

EQHL retune; ASR/SFP rescue; PIN/ThreeBar/Outside/Engulf densify; MaxKZ/RR spam;
USBILL; IB/RV/GBPJPY/EMA/London-hour mine from probes.

## Next auto

1. **Preferred (infra):** Owner closes Real until `Get-Process terminal64`=0 →
   Model 0 IB then GBPJPY (contracts frozen).
2. **Discovery stub prepared:** `HYP-H1-ATR-PCTILE-BREAK-001`
   (`readouts/20260714_H1_ATR_PCTILE_BREAK_STUB.md`) — de-dup freeze before code.
3. Do **not** headline QFSI-wait as R&D stop; Real close is only for exclusive
   Model 0 slot of queued survivors.
