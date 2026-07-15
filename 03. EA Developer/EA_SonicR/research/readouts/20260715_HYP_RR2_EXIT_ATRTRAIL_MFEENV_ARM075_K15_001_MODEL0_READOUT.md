# Model 0 readout — HYP-RR2-EXIT-ATRTRAIL-MFEENV-ARM075-K15-001

Date: 2026-07-15  
Authority: Owner free Model 0 + brief Real pause; native ATR-trail confirmation  
Cost label: **`UNVERIFIED_TESTER_DEFAULT`** (Real paused for tester; missing commission/slip ≠ 0)

## Identity

| Field | Value |
|---|---|
| Hypothesis | `HYP-RR2-EXIT-ATRTRAIL-MFEENV-ARM075-K15-001` |
| Parent / shelf | `HYP-SB-MAXKZ2-RR2-FRICTION-001` / `20260714_194548` |
| run_id | **`20260715_081213`** |
| EA | `EA_SilverBullet` (`EA_SilverBullet_v2` every-tick M15 ATR trail; `InpTrailBE=0`) |
| Symbol / TF / window | USDJPY M15 · 2021.01.01–2025.12.31 · Model **0** |
| Role | challenger vs matched control `194548` |
| Overrides (frozen) | `InpFridayFlatHour=21;InpFridayFlatMinute=45;InpMaxTradesPerKZ=2;InpPartialClose=0;InpRiskPct=0.5;InpTP_RR_LDN=2.0;InpTP_RR_NY=2.0;InpTrailActivateR=0.75;InpTrailATR_Mul=1.5;InpTrailBE=0;InpUseTrail=1;InpUseWeekendFlat=1` |
| Receipt | `preflight/atrtrail_mfeenv/contracts/20260715_HYP_RR2_EXIT_ATRTRAIL_MFEENV_ARM075_K15_001_CONTRACT_RECEIPT.json` |
| Pause | `preflight/20260715_ATRTRAIL_MODEL0_QFSI_PAUSE_RECEIPT.json` (PID 19984 → resume 52000) |

## Metrics (tester report / enhanced_summary)

| Metric | Native Model 0 | Offline MFE-envelope proxy | RR2 shelf `194548` |
|---|---:|---:|---:|
| N | **548** | 524 | 524 |
| PF | **1.100** | 2.5323 | 1.378 |
| Net | **+$1,892.77** | +$26,891.88 | +$9,828.35 |
| Exp / trade | **+$3.45** | +$51.32 | +$18.76 |
| WR | 53.3% | — | 42.7% |
| MaxDD | 1.38% | — | 0.96% |
| tpw (elapsed calendar weeks ≈260.86) | **≈2.10** | 2.01 | 2.01 |

## Cost-stress (a priori +$12 round-turn; report-only proxy)

Artifact: `runs/EA_SilverBullet/20260715_081213/analysis/sonic_cost_stress_base12_x15.json`

| Scenario | PF | Net |
|---|---:|---:|
| base_report | 1.100 | +$1,892.77 |
| +$12 ×1.0 | 0.788 | −$4,683 |
| **+$12 ×1.5** | **0.666** | **−$7,971** |
| +$12 ×2.0 | 0.563 | −$11,259 |

## Prereg gates → **KILL**

| Gate | Rule | Observed | Pass? |
|---|---|---|---|
| N | ≥80 | 548 | yes |
| tpw | ∈[1.5, 6] | ≈2.10 | yes |
| PF | >1.20 | **1.100** | **NO** |
| +$12 ×1.5 PF | ≥1.15 | **0.666** | **NO** |
| Lift vs RR2 ×1.5 | improve on ~1.013 | **0.666** (worse) | **NO** |

## Honesty

- Offline envelope SURVIVOR (PF 2.53 / ×1.5 1.81) **did not survive** native every-tick ATR trail.
- Envelope was optimistic vs tester path (peak-then-exit ≠ tick trail + early SL / giveback).
- Native trail **underperforms** fixed-RR shelf `194548` on PF, net, expectancy, and cost-stress.
- Cost label is tester/Demo-path honest — **not** research-grade Real QFSI freeze. Do not invent zeros.
- Do **not** densify arm/k from this fail. Do **not** claim GOAL. Do **not** treat offline proxy as deployable.

## Verdict

**`KILLED_AT_MODEL0`** — research bar fail (PF≤1.20) + stress fail (+$12×1.5 PF≪1.15) + no lift vs RR2 shelf.

Best shelf remains RR2 `194548`. Alt ARM100/K20 is a priori sibling (not densify); optional Model 0 if launched separately.

## Banned follow-ups

- Densify `InpTrailActivateR` / `InpTrailATR_Mul` / BE flag from this readout  
- Revive BE@1R / MFE stall / scale-out / timebox / vol-regime-R  
- Claim GOAL or deploy from offline envelope PF  
- Invent cost freeze from partial QFSI  
