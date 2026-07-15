# Prereg — HYP-BOOK-CORRCAP-RR2-SPARK-001

Date: 2026-07-14  
State on freeze: `preregistered`  
Authority: Owner dichotomy-break mandate; GPT waived; no densify

## Identity

- Hypothesis ID: `HYP-BOOK-CORRCAP-RR2-SPARK-001`
- Sleeves: RR2 `20260714_194548` + Spark `20260714_193358`
- Class: multi-sleeve **CorrCap** (max concurrent = 1)
- Panel: `readouts/20260714_DICHOTOMY_BREAK_3CRITIC_MERGE_MEMO.md`
- De-dup: `readouts/20260714_DICHOTOMY_BREAK_DEDUP_CLEARANCE.md`

## Thesis

Equal-join RR2+Spark piles overlapping risk and does not thicken
friction edge. A priori max-concurrent=1 rejects overlapping opens
(greedy by open_time). Offline diagnostic only — **not** Phase-0
compose ceremony (contamination still blocked).

## Locked Design

| Item | Frozen |
|---|---|
| RR2 run | `20260714_194548` |
| Spark run | `20260714_193358` |
| Cap | max concurrent positions = 1 across sleeves |
| Accept rule | greedy chronological; reject if open overlaps any accepted |
| Window | 2021.01.01–2025.12.31 |
| Ceremony | Phase-0 still `BLOCKED_REQUIRES_CLEAN_FUTURE_FREEZE_REVIEW` |

## De-dup

- Not Phase-0 equal-join ceremony / metrics claim
- Not SBSparkBook scaffold Model 0 (`224302` KILL)
- Not V6/V7 multi-symbol price clones

## Kill / Park / HIT (offline probe)

| Gate | Rule |
|---|---|
| KILL | N&lt;80 OR tpw∉[1.0,6.5] OR PF&lt;1.05 OR +$12 x1.5 PF&lt;1.10 OR book PF &lt; best sleeve − 0.02 |
| PROBE_SURVIVOR | PF&gt;1.20 ∧ tpw∈[1.5,6] ∧ x1.5 PF≥1.15 |
| Model 0 | only if PROBE_SURVIVOR; still not Phase-0 compose claim |

## Banned

- Reopening Phase-0 without Owner contamination clear
- Mining overlap windows from readout
- Densify MaxKZ/RR/Spark MaxPerDay
