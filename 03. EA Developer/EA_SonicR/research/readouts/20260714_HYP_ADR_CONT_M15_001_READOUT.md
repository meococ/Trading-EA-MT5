# Readout — HYP-ADR-CONT-M15-001 Model 0

Date: 2026-07-14  
Run: `20260714_031538`  
EA: `EA_M15ADRCont`  
Verdict: **KILLED_AT_MODEL_0**

## Binding

USDJPY M15 2021.01.01–2025.12.31 Model 0 Deposit=10000 overrides=``  
Hypothesis `HYP-ADR-CONT-M15-001` control. Tester `current` only.

## Metrics (`enhanced_summary.json`)

| Metric | Value |
|---|---|
| Trades | 146 |
| PF | **0.887** |
| Net | **−$510.65** |
| Expectancy | −3.50 |
| Max DD % | ~6.95% |
| tpw elapsed | **~0.56** (146 / 260.71) |

## Gate

| Screen | Result |
|---|---|
| N ≥ 80 | PASS |
| tpw ∈ [1.0, 6.0] | **FAIL** (~0.56) |
| PF ≥ 1.00 | **FAIL** (0.887) |

**Kill.** S681 qualitative “continuation favored” does **not** survive as a tradable EA under frozen ADR100% + extreme-band continuation.

## Artifacts

- Report SHA256: `63FF90F1195EBEBBAF6658C9E844D63A2485FA4A6BD132E6D99887CECA2C6F64`
- Receipt SHA256: `A5B506CB9B327AAC8C950BB416AF263A0B96E64C0FD221ACABE868C8B0C26D2E`
- Alpha closeout `includes_sha256` mismatch after report ready — artifacts kept.

## Banned

No ADR thresh / extreme% / day / hour mining; no flip to fade; no PDH transplant.
