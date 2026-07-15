# Discovery Wave3 closeout — Outside / Engulf / Pin (2026-07-14)

Status: `WAVE3_EXECUTED_EMPTY / GOAL_STILL_UNMET`  
Authority: Owner mandate — R&D without Real/QFSI stall; no MaxKZ/RR/VWAP/BOS/ATF clones

## Intake

| ID | Action |
|---|---|
| `HYP-ITSM-NYONLY-RR3-THICK-001` | **KILLED_AT_INTAKE** (RR spam of parked ITSM) |
| `HYP-SB-MAXKZ2-PARTIAL-R1-001` | **KILLED_AT_INTAKE** (MaxKZ family clone) |
| De-dup | `readouts/20260714_DISCOVERY_WAVE3_DEDUP_CLEARANCE.md` |

## Board (Model 0)

| ID | Run | Verdict | PF | N | tpw | Exp $/t | Cost-stress (+$12) |
|---|---|---|---:|---:|---:|---:|---|
| `HYP-H4-OUTSIDE-REV-001` | `20260714_221504` (twin `221328`) | **KILL** | 0.773 | 25 | ~0.10 | −45.47 | x1.5 **0.70** / x2 **0.68** (diag) |
| `HYP-H4-ENGULF-REV-001` | `20260714_221546` | **KILL** cadence+PF | 1.131 | 202 | ~0.77 | +24.19 | x1.5 **~1.03 FAIL** / x2 **~1.00** |
| `HYP-H1-PIN-PDLEVEL-001` | `20260714_221912` | **KILL** | 0.667 | 20 | ~0.08 | −28.36 | skipped PF&lt;1.20 |

No research HIT (none clears PF>1.30 ∧ tpw∈[2,5]).

Sibling partial closeouts (same Outside/Engulf evidence):  
`readouts/20260714_THICK_EDGE_OUTSIDE_ENGULF_CLOSEOUT.md`.

## Best GOAL distance (unchanged shelf)

| Book | Tester | Stress | Distance |
|---|---|---|---|
| RR2 `20260714_194548` | PF **1.378** / ~**2.01**/wk | a priori +$12 x1.5 **FAIL** | Still closest research HIT; GOAL unmet |
| MaxKZ2 `192304` | PF 1.33 / ~2.09/wk | Real-P50 FAIL | No densify |
| Engulf `221546` | PF 1.13 / ~0.77/wk | x1.5 ~1.03 FAIL | Thick-ish $/t but cadence dead |
| NR7 `201923` | PF 1.28 / ~1.45/wk | n/a | Parked near-miss |

## Integrity

- Ceremony: de-dup → registry → frozen prereg → ContractReceipt → Model 0 → readout.
- Engulf authority = `221546`. Race run `221759` (N=0 after source overwrite) discarded; source restored from `221546` snapshot.
- Alpha finalize may throw on empty `required_sidecars` null-coercion after report ready; kill metrics from report+analyze.
- QFSI/Real = parallel hygiene only — not headline next move.
- Do not mine WR/engulf body/wick%/PD buffer/hour/day from these kills.

## Next R&D (no Owner login)

1. Independent mechanisms with **joint** thick post-cost $/trade **and** 2–5/wk cadence — H4 sparse fades exhausted this wave.
2. Optional: a priori sleeve compose freeze before any combo PF (RR2+Spark offline only).
3. `DEMO_DISCOVERY_DIMINISHING_RETURNS = true` — cheap offline probe before next Model 0 batch.
4. Real/QFSI accumulate when available — never lane stop.
