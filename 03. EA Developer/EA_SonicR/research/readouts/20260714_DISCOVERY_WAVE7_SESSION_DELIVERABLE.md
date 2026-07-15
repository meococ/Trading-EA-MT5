# Deliverable — Discovery Wave7 (new price objects + thick compose)

Date: 2026-07-14 ~23:40 ICT  
Authority: Owner CONTINUE Wave7 after `WAVE6_EXECUTED_EMPTY`  
GPT: waived · Grok · free MT · no-Git · cost honesty

## Verdict

**`WAVE7_EXECUTED_EMPTY` / zero Model 0.** Sáu ID mới (5 price-lawful +
1 a-priori thick compose) — **0 HIT** vs joint screen
PF>1.30 ∧ tpw∈[2,5] ∧ x1.5≥1.25 ∧ x2≥1.00. GOAL unmet.

## Board (SHA `EA4D74FB…B85F3`)

| ID | N | PF | tpw | x1.5 | x2 | Verdict |
|---|---:|---:|---:|---:|---:|---|
| `HYP-NZDUSD-H1-ASIA-RANGE-LONDON-BREAK-001` | 587 | 1.04 | **2.25** | 0.92 | 0.89 | **KILL** stress |
| `HYP-W1-OPEN-H1-ACCEPT-CONT-001` | 233 | 1.20 | 0.89 | 1.08 | 1.05 | **KILL** cadence+stress |
| `HYP-H1-LONDON-MID-RECLAIM-CONT-001` | 371 | 1.14 | 1.42 | 1.09 | 1.07 | **KILL** stress |
| `HYP-AUDUSD-LEAD-EURUSD-H1-001` | 919 | 0.83 | **3.52** | 0.77 | 0.76 | **KILL** pf+stress |
| `HYP-EURUSD-H1-WEEKEND-GAP-FILL-001` | 123 | 1.12 | 0.47 | 1.06 | 1.04 | **KILL** cadence+stress |
| `HYP-BOOK-COMPOSE-3DAY-LONDONDRIVE-001` | 570 | 1.11 | **2.19** | **1.03** | 1.00 | **KILL** stress |

Server probe: `FivePercentOnline-Real` / `26451822` (hygiene; not Model 0).  
Cost grade: `UNVERIFIED_OFFLINE_PROXY`.

## Compose diagnostic (lawful, not densify)

A priori equal-join of Wave6B PARK `THREE-DAY-HL` (N=265 re-sim match) +
London-open-drive thick park:

| Measure | Value |
|---|---|
| Same-day overlap | **72** |
| Exact entry-ts overlap | **2** |
| Pooled tpw | **2.19** (cadence band OK) |
| Pooled PF / x1.5 | **1.11 / 1.03** (thickness **destroyed**) |

Note: London-drive sleeve re-sim on current Real history produced N=305
(vs historical offline park N=104) — even under that denser join, stress
fails; joining does **not** preserve 3-day x1.5≈1.41. Same thick↔cadence
tradeoff as Wave6 FX3. **Do not densify** either sleeve.

## HARD_EMPTY (extended)

Missing property unchanged after Wave7 unused-object sweep:

> Simultaneous thick post-cost expectancy **and** 2–5/wk cadence **and**
> PF>1.30 on one frozen independent object (or a priori compose that keeps
> x1.5≥1.25).

Fragments still split: cadence without thickness (NZD/AUD-lead/compose) vs
thickness without cadence (3-day PARK; historical RR2 shelf friction-fragile).

## QFSI / Real

`terminal64` PID **29076** + capture PID **35892** left running — parallel
hygiene only. No Model 0; no densify RR2/MaxKZ. Full QFSI still
`STOP_DATA_FRONTIER` until quote-days/commission/slip complete.

## Explicit bans (carry forward)

No densify Wave6/V1–V8 / RR2 / SB-Spark / USBILL / IB/GBPJPY/ATR /
PIN/Outside / Wave7 NZD·W1open·mid·AUDlead·gap·compose params.

## Files

- Dedup: `readouts/20260714_DISCOVERY_WAVE7_DEDUP_CLEARANCE.md`
- Probes: `preflight/20260714_DISCOVERY_WAVE7_OFFLINE_PROBES.{py,json,md}`
- Preregs: `preregs/20260714_H_*` for each of 6 IDs
- HARD_EMPTY: `readouts/20260714_DISCOVERY_WAVE7_HARD_EMPTY.md`
- Registry lane: `discovery_wave7_20260714`

## Next auto (honest frontier)

1. **Local price shelf ROI is now near-zero** for bar-only FX objects
   outside the killboard — further mono price twins expected empty.
2. **Account path:** keep Real QFSI accumulate for RR2/SB/Spark cost truth
   (parallel; not headline stop).
3. **Data-gate (Owner/source):** lagged COT with a priori lag contract, or
   tick-synced cross-sectional USD factor — not bar-only fake.
4. Best shelf unchanged: RR2 `194548` (historical); current Model 0 `231750`
   PARK_MISS.
