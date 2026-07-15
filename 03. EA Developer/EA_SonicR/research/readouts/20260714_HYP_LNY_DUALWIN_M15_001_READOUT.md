# Readout — HYP-LNY-DUALWIN-M15-001 Model 0

Date: 2026-07-14 ~20:11 ICT  
EA: `EA_M15LNYDualWin`  
Run: `20260714_201038`  
Verdict: `KILLED_AT_MODEL_0` (cadence + N; thick PF not enough)

## Metrics (USDJPY M15 2021–2025, Deposit=100000, Model 0)

| Metric | Value |
|---|---:|
| Trades | **69** |
| PF | **1.42** |
| Net | +$2863 |
| Expectancy | **+$41.49**/trade |
| tpw (elapsed) | **~0.26** |
| Max DD | ~1.70% |

Session split: Europe 61 / NY 8 — second window under-fired; structural dual-window did **not** expand cadence vs LondonNY ref ~0.29/wk.

Cost: `UNVERIFIED_TESTER_DEFAULT`. Terminal stop identity flake after report; report recovered from AlphaRuns and analyzed.

## Gate

| Gate | Result |
|---|---|
| PF ≥ 1.00 | PASS |
| N ≥ 80 | **FAIL** (69) |
| tpw ∈ [1,6] | **FAIL** (~0.26) |
| Research HIT PF>1.30 ∧ 2–5/wk | **FAIL** |
| Cost-stress $12 haircut (diagnostic) | x1.5 PF **1.222** (<1.25); x2 PF **1.161** (≥1.00) → friction better than MaxKZ/RR2 but **not** GOAL stress PASS |

Artifact: `preflight/20260714_COSTSTRESS_LNY_DUALWIN_201038.json`

## Compare vs parked GOAL-near books

| Book | PF | tpw | x1.5 friction |
|---|---:|---:|---|
| RR2 `194221` | 1.38 | ~2.01 | FAIL (~0.92 loss×) |
| MaxKZ2 `192304` | 1.33 | ~2.09 | FAIL |
| LNY DualWin `201038` | 1.42 | ~0.26 | near-miss 1.22 |

Near GOAL for joint PF+cadence remains **RR2 / MaxKZ2** (friction-dead). DualWin is thick/sparse — not sole GOAL book; **no Spark compose** (failed research bar; cadence expand failed).

## Banned

No Mon veto (Mon PF 0.43 is post-hoc); no day-skip densify; no RR/window retune from readout.
