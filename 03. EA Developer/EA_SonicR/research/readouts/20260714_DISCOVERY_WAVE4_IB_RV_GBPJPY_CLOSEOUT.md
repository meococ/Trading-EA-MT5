# Discovery Wave4 closeout — IB / RV-compress / GBPJPY lead (2026-07-14)

Status: `WAVE4_EXECUTED_EMPTY / GOAL_STILL_UNMET`  
Authority: Owner mandate — R&D without Real/QFSI stall; joint thick post-cost $/trade **and** cadence 2–5/wk  
GPT: waived

## De-dup / ceremony

| Step | Artifact |
|---|---|
| De-dup | `readouts/20260714_DISCOVERY_WAVE4_DEDUP_CLEARANCE.md` |
| Registry boot | `preflight/20260714_DISCOVERY_WAVE4_BOOT_RECEIPT.json` |
| Contracts | `preflight/20260714_DISCOVERY_WAVE4_CONTRACTS.json` |
| Compile | All three EX5 OK (0 errors) |

## Board (Model 0)

| ID | Run | Verdict | PF | N | tpw | Exp $/t | +$12 stress |
|---|---|---|---:|---:|---:|---:|---|
| `HYP-M15-IB-OVERLAP-BREAK-001` | `20260714_223618` | **PARK** weak | 1.05 | 987 | ~3.79 | +5.66 | x1 **0.94 FAIL** (diag) |
| `HYP-H1-RV-COMPRESS-BREAK-001` | `20260714_223714` | **KILL** cadence | **1.61** | 84 | ~**0.32** | +**57.45** | x1.5 **1.38 PASS** / x2 **1.32 PASS** (diag only) |
| `HYP-GBPJPY-LEAD-USDJPY-H1-001` | `20260714_223748` | **PARK** weak | 1.10 | 1337 | ~5.13 | +9.45 | x1 **0.98 FAIL** (diag) |

No research HIT (none clears PF>1.30 ∧ tpw∈[2,5]).

Report SHA map: `preflight/20260714_WAVE4_REPORT_SHA.json`.

## Integrity

- Alpha finalize threw known empty `required_sidecars` null-coercion after report ready; metrics from report + `sonic_cost_stress`.
- Autoretry waited for exclusive tester (`terminal64=0`) then launched batch — mechanical slot, not a QFSI/login research gate.
- Parallel EQHL memo offline probes for the same IDs are **non-authoritative**; these Model 0 run_ids supersede them.
- Do **not** densify IB hours / compress ratio / lead ATR / RR / day from these readouts.

## Best GOAL distance (shelf unchanged)

| Book | Tester | Stress | Notes |
|---|---|---|---|
| RR2 `20260714_194548` | PF **1.378** / ~**2.01**/wk | a priori +$12 x1.5 **FAIL** | Still closest joint PF+cadence |
| RV Compress `223714` | PF **1.61** / ~0.32/wk | +$12 x1.5 **1.38 PASS** | Thick friction survivor; cadence dead |
| MaxKZ2 `192304` | PF 1.33 / ~2.09/wk | Real-P50 FAIL | No densify |

## Structural lesson

Wave4 reconfirmed the split: **thick-expectancy sleeves** (RV compress, prior DualWin/Engulf) can clear a priori +$12 x1.5 but sit below 1 trade/week; **cadence-band sleeves** (IB overlap, GBPJPY lead) clear 2–5/wk but die under +$12. Joint GOAL still unmet. Do not glue them post-hoc without a priori sleeve-compose freeze.

## Next R&D (no Owner login dependency)

1. New independent mechanisms aiming at **joint** thick $/trade **and** 2–5/wk — prefer regime×session microstructure or multi-sleeve a priori compose (exact frozen run IDs) over single-signal densify.
2. Optional: freeze Phase-0 portfolio compose contract for RR2 + Spark (exact universe already probed offline) before any combo PF claim — still blocked on contamination/Spark module gaps per prior prereg.
3. `DEMO_DISCOVERY_DIMINISHING_RETURNS = true` remains — cheap offline probe before next Model 0 batch when possible.
4. Real/QFSI accumulate in parallel only — never lane stop / never headline.
