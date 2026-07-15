# Model 0 Backlog Wave2 Coordinator — 2026-07-14

Status: **MODEL0_COMPLETE** (GOAL unmet)

## Selection

| Candidate | Decision |
|---|---|
| InsideBar / Chop / VolExp / GoldJPY / TickVol / HourOpen | Banned (prior kills) |
| SB weekend-flat Friday mine | Banned (parked; no day-hour rescue) |
| USBILL | Parallel Model 0 **KILL** (control PF 1.05) — not Wave2 primary |
| **`HYP-SPARK-ASIAN-M15-001` / `EA_M15SparkAsian`** | **Executed** — S111 dual-filter near-miss (PF~1.26 / ~1.37/wk) |

## Result

| Field | Value |
|---|---|
| run_id | `20260714_002614` |
| PF | **1.31** |
| Trades | **325** |
| tpw elapsed | **~1.25** |
| Net | **+$1,099.38** |
| Expectancy | **+3.38** |
| Max equity DD | **3.41%** |

Survives prereg kill floor (PF≥1.00; tpw∈[1.0,6.0]; n≥80). Fails GOAL dual gate
(cadence < 2.0). Tester `current` cost only → **park / research near-miss**.

## Explicit non-claims

- GOAL **not** met.
- Tester PF ≠ verified after-cost PF.
- Missing cost ≠ zero.
- Do not mine Mon–Thu densification, range/body/hour, or sibling
  `EA_M15AsianRangeBreak` as a rescue re-screen of this ID.

## Paths

- Prereg: `preregs/20260714_H_SPARK_ASIAN_M15_001_PREREG.md`
- Contract: `preflight/spark_asian_m15/contracts/20260714_HYP_SPARK_ASIAN_M15_001_CONTRACT_RECEIPT.json`
- Receipt: `preflight/20260714_MODEL0_BACKLOG_WAVE2_RECEIPT.json`
- Readout: `readouts/20260714_HYP_SPARK_ASIAN_M15_001_READOUT.md`
- Run: `02. AlphaFactory/runs/EA_M15SparkAsian/20260714_002614/`

## Next agent-executable

Wave2 dual-filter near-miss shelf for Spark/SB/USBILL is closed (Spark park;
SB park; USBILL kill). Named independent next (not executed in Wave2):
`HYP-ITSM-PULLBACK-M15-001` / `EA_ITSM` (S509 denser EMA-zone; draft prereg
`preregs/20260714_H_ITSM_PULLBACK_M15_001_PREREG.md`) — freeze registry +
contract then Model 0. Not a Spark/SB rescue.

| Who | Action |
|---|---|
| **Agent-executable** | ITSM pullback Model 0 under frozen prereg/registry/contract |
| **Owner-physical** | `FivePercentOnline-Real` + QFSI for parked SB/Spark promotion-grade cost |

If ITSM also dies and no new independent thesis exists → fail-closed
`BLOCKED_NO_LEGAL` (do not spam compiles). Do not ChatGPT Deep Research.
