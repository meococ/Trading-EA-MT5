# Deliverable — Owner refine/rebuild wave (2026-07-14 ~19:09 auth)

Authority: Owner tear-down + iterate near GOAL; override
`DEMO_DISCOVERY_DIMINISHING_RETURNS`; GPT waived; Grok lane.  
Cost grade: tester `current` / MetaQuotes-Demo — **not Real QFSI**.

## 1) Options tried (matrix) vs SB A1 baseline

Baseline **SB A1** `20260714_002505`: PF **1.34** / 520 / **~1.99**/wk / net +7875.

| Option | hypothesis_id | run_id | PF | tpw | Net | vs A1 |
|---|---|---|---:|---:|---:|---|
| MaxHold A2 | `HYP-SB-MAXHOLD-A2-001` | `20260714_191628` | 1.33 | 1.998 | 7541 | ~null / slightly worse |
| NYPM KZ | `HYP-SB-NYPM-KZ-001` | `20260714_192203` | **1.27** | **2.44** | 7654 | cadence↑ PF↓ below 1.30 |
| MaxKZ=2 densify | `HYP-SB-MAXKZ2-DENSITY-002` | `20260714_192304` | **1.33** | **2.09** | 8123 | **clears PF+cadence research bar** |
| Spark GBPUSD | `HYP-SPARK-ASIAN-GBPUSD-001` | `20260714_191507` | 1.07 | 1.66 | 3503 | park / weak |
| ITSM NY-only | `HYP-ITSM-NYONLY-STRICTALIGN-002` | `20260714_191955` | 1.22 | 2.07 | 2431 | park |
| ITSM London-only | `HYP-ITSM-LONDON-ONLY-STRICTALIGN-002` | `20260714_192116` | 1.12 | 1.85 | 1641 | park |
| H1 Donchian MR | `HYP-H1-LOWVOL-DONCHIAN-MR-001` | `20260714_191727` | 0.40 | 0.05 | −267 | **KILL** |
| Compose A1+Spark | offline prior | — | 1.339 | 3.24 | 8975 | near GOAL / cost open |
| Compose MaxKZ2+Spark | offline `…MAXKZ2…V1` | — | **1.330** | **3.34** | 9222 | near GOAL / cost open |

`HYP-SPARK-CAPACITY-3PD-001` (MaxPerDay 2→3): prereg+receipt ready; Model 0
blocked this turn by concurrent lock / matched-control ceremony — queued.

## 2) What actually improved profit / cadence

- **Best SB structural win:** MaxKZ2 — first single-sleeve SB child to clear
  **PF>1.30 and tpw≥2.0** on elapsed weeks (tester only). Risk also set to 0.5%
  in that freeze (vs A1 1.0%) — treat net $ as secondary.
- **NYPM:** cadence OK, PF regresses → not a profit improvement.
- **A2 max-hold:** no material gain.
- **Compose MaxKZ2+Spark:** pooled cadence **3.34**/wk with PF **1.33** —
  still the closest book shape to GOAL on Demo cost.
- Parallel ITSM/Spark-GBP/H1 paths did **not** beat SB family.

## 3) Rebuilds coded (EA path)

| Path | Role |
|---|---|
| `03. EA Developer/EA_H1LowVolDonchianMR/EA_H1LowVolDonchianMR.mq5` | New greenfield H1 MR — **killed** at Model 0 |
| No new portfolio EA coded | Compose remains offline probe (Phase 0 freeze still blocked) |
| SB/Spark/ITSM | Existing EAs; child hyps via frozen overrides only |

## 4) Distance to GOAL

| Gate | Status |
|---|---|
| Research PF>1.30 + 2–5/wk (tester) | **Met by MaxKZ2 alone** and by MaxKZ2+Spark pool |
| After verified Real cost (x1 / x1.5 / x2) | **Open** — `BLOCKED_NO_FIVEPERCENTONLINE_REAL_LOGIN` |
| Confirmed suite / holdout | Not started |
| Phase 0 portfolio freeze | Still contaminated / not READY |

Honest gap: **cost provenance + promotion ceremony**, not Demo PF discovery.

## 5) Next — agent vs Owner

**Agent can keep iterating (self):**
1. Finish `HYP-SPARK-CAPACITY-3PD-001` Model 0 when lock free.
2. Optional: MaxKZ2 × Spark portfolio scaffold EA **only** as research sleeve
   after Owner allows Phase-0-exception or clean freeze.
3. Do **not** mine NYPM hours / MaxKZ / Fri cutoff from tonight’s readouts.

**Owner-only (highest EV):**
1. Login `FivePercentOnline-Real` + QFSI.
2. Reprice **MaxKZ2** `20260714_192304` (and Spark `002821`) under Real cost.
3. Decide Phase 0 contamination clearance if compose EA is desired.

## 6) hot.md updated?

Yes — Active Truth rewritten for this wave (MaxKZ2 research-bar hit; diminishing-
returns pause overridden by Owner; H1 Donchian kill; compose MaxKZ2+Spark note).
