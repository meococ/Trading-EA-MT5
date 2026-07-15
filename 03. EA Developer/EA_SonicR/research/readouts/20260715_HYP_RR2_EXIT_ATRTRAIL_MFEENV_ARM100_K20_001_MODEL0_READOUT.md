# Model 0 readout — HYP-RR2-EXIT-ATRTRAIL-MFEENV-ARM100-K20-001

Date: 2026-07-15  
Authority: Owner free Model 0; a priori sibling after primary ARM075/K15  
Cost label: **`UNVERIFIED_TESTER_DEFAULT`**

## Identity

| Field | Value |
|---|---|
| Hypothesis | `HYP-RR2-EXIT-ATRTRAIL-MFEENV-ARM100-K20-001` |
| run_id | **`20260715_082030`** |
| Overrides (frozen) | `InpFridayFlatHour=21;InpFridayFlatMinute=45;InpMaxTradesPerKZ=2;InpPartialClose=0;InpRiskPct=0.5;InpTP_RR_LDN=2.0;InpTP_RR_NY=2.0;InpTrailActivateR=1.0;InpTrailATR_Mul=2.0;InpTrailBE=0;InpUseTrail=1;InpUseWeekendFlat=1` |
| Note | Independent a priori formula — **not** densify from primary `20260715_081213` |

## Metrics

| Metric | Native Model 0 | Offline envelope | Primary ARM075 | RR2 `194548` |
|---|---:|---:|---:|---:|
| N | **538** | 524 | 548 | 524 |
| PF | **1.086** | 2.2173 | 1.100 | 1.378 |
| Net | **+$1,901.16** | +$23,341.89 | +$1,892.77 | +$9,828.35 |
| MaxDD | 1.49% | — | 1.38% | 0.96% |
| tpw (≈260.86 w) | **≈2.06** | 2.01 | ≈2.10 | 2.01 |

## Cost-stress (+$12 report-only)

Artifact: `runs/EA_SilverBullet/20260715_082030/analysis/sonic_cost_stress_base12_x15.json`

| Scenario | PF | Net |
|---|---:|---:|
| base_report | 1.086 | +$1,901.16 |
| +$12 ×1.0 | 0.821 | −$4,554.84 |
| **+$12 ×1.5** | **0.715** | **−$7,782.84** |
| +$12 ×2.0 | 0.622 | −$11,010.84 |

## Gates → **KILL**

- PF **1.086** ≤ 1.20  
- +$12 ×1.5 PF **0.715** ≪ 1.15  
- No lift vs RR2 shelf ×1.5≈1.013; not densify from primary fail  

## Verdict

**`kill`** at Model 0. Confirms native ATR-trail class underperforms fixed-RR shelf under tester cost. Do not densify arm/k. GOAL unmet.
