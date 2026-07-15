# Readout — HYP-PDH-BREAK-M15-001 Model 0

Date: 2026-07-14  
Run: `20260714_013818`  
EA: `EA_M15PDHBreak`  
Verdict: **PARKED** (GOAL unmet)

## Binding

| Item | Value |
|---|---|
| Symbol / TF | USDJPY M15 |
| Window | 2021.01.01 – 2025.12.31 |
| Model | 0 |
| Deposit / leverage | 10000 / 100 |
| Spread | tester `current` |
| Overrides | `` (frozen defaults) |
| Hypothesis | `HYP-PDH-BREAK-M15-001` |
| Role | control |

## Metrics (AlphaFactory `enhanced_summary.json` authoritative)

| Metric | Value |
|---|---|
| Trades | 440 |
| Profit factor | **1.027** |
| Net | **+$289.83** |
| Expectancy / trade | +0.66 |
| Max DD % | ~11.65% |
| Win rate | ~44.1% |
| Elapsed weeks | ~260.86 (calendar 2021-01-01→2025-12-31) |
| Trades / elapsed week | **~1.69** |

Cost: MetaQuotes-Demo / tester `current` only — **not** Real QFSI. Missing cost ≠ 0.

## Gate vs prereg

| Screen | Result |
|---|---|
| N ≥ 80 | PASS |
| tpw ∈ [1.0, 6.0] | PASS (~1.69) |
| PF ≥ 1.00 | PASS (barely) |
| PF > 1.30 and tpw ∈ [2.0, 5.0] | **FAIL** |
| GOAL joint | **FAIL** |

Survives kill floor → **park**. Near-breakeven edge; not a promotion seed.

## Artifacts

- Run folder: `02. AlphaFactory/runs/EA_M15PDHBreak/20260714_013818/`
- Report SHA256: `F4136110AD52B1F78CDA17735347FBA9034E3C2A8F1962B7A4E3D46E20E68A51`
- Receipt SHA256: `E182CFF9CA53D8C4E18E5F64932C3BCE2DF08AA76B6C3B972E6B176C005B4033`
- Prereg: `preregs/20260714_H_PDH_BREAK_M15_001_PREREG.md`
- De-dup: `readouts/20260714_PDH_BREAK_VS_LIQSWEEP_LONDONORB_DEDUP_CLEARANCE.md`
- Probe: `readouts/20260714_HYP_PDH_BREAK_M15_001_PROBE.md`

## Banned post-hoc (do not execute)

Weakness detector flagged NY session, 2023, hours [13,15], Thursday — **not** authorized to veto/mine. Do not flip to fade, do not transplant London ORB params, do not densify days.

## Note on VN report parse

Raw HTML snip once looked like net `10 965.12`; `alpha.ps1 analyze` / `enhanced_summary.json` give net **289.83**. Use analyze as source of truth.
